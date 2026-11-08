"""Load the built MV3 extension in Chromium/Edge and verify popup plus field insertion."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "dist" / "extension"
TEST_EXTENSION = ROOT / "dist" / "extension-test"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return


def result_template(browser_name: str) -> dict:
    return {
        "schemaVersion": 1,
        "component": "browser-extension",
        "browser": browser_name,
        "status": "NOT_RUN",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "finishedAt": None,
        "checks": {},
        "errors": [],
        "warnings": [],
        "screenshots": [],
    }


def mark(report: dict, name: str, status: str, detail: str = "") -> None:
    report["checks"][name] = {"status": status, "detail": detail}


def start_server():
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}", thread


def launch_context(playwright, browser_name: str, profile: str, extension_path: Path):
    common = {
        "headless": False,
        "viewport": {"width": 396, "height": 600},
        "args": [
            f"--disable-extensions-except={extension_path}",
            f"--load-extension={extension_path}",
            "--disable-component-update",
            "--disable-gpu",
            "--disable-dev-shm-usage",
        ],
    }
    if browser_name == "msedge":
        return playwright.chromium.launch_persistent_context(profile, channel="msedge", **common)
    if browser_name == "chrome":
        return playwright.chromium.launch_persistent_context(profile, channel="chrome", **common)
    return playwright.chromium.launch_persistent_context(profile, **common)


def wait_for_extension(context) -> str:
    if not context.service_workers:
        context.wait_for_event("serviceworker", timeout=15_000)
    if not context.service_workers:
        raise AssertionError("Extension service worker did not start")
    return context.service_workers[0].url.split("/")[2]


def popup_url(extension_id: str) -> str:
    return f"chrome-extension://{extension_id}/popup/popup.html"


def screenshot(report: dict, page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(path), full_page=False)
        report["screenshots"].append(str(path.relative_to(ROOT)))
    except PlaywrightError as error:
        report["warnings"].append(f"Screenshot unavailable: {error}")


def find_test_tab(popup, url_fragment: str) -> int:
    tabs = popup.evaluate("chrome.tabs.query({})")
    for tab in tabs:
        if url_fragment in (tab.get("url") or ""):
            return int(tab["id"])
    raise AssertionError(f"Test tab containing {url_fragment!r} was not found")


def other_tab_id(popup, excluded: set[int]) -> int:
    tabs = popup.evaluate("chrome.tabs.query({})")
    candidates = [int(tab["id"]) for tab in tabs if int(tab["id"]) not in excluded]
    if not candidates:
        raise AssertionError("No non-popup tab found for permission checks")
    return candidates[-1]


def check_popup_and_permission_denial(playwright, browser_name: str, base_url: str, report: dict, screenshots: Path):
    console_errors: list[str] = []
    remote_requests: list[str] = []
    with tempfile.TemporaryDirectory(prefix="nickspeare-popup-") as profile:
        context = launch_context(playwright, browser_name, profile, EXTENSION)
        try:
            extension_id = wait_for_extension(context)
            mark(report, "extensionLoad", "PASS", context.service_workers[0].url)

            manifest = json.loads(EXTENSION.joinpath("manifest.json").read_text(encoding="utf-8"))
            assert manifest["manifest_version"] == 3
            assert manifest["version"] == "0.1.0"
            assert manifest["version_name"] == "0.1.0-alpha.1"
            assert set(manifest.get("permissions", [])) == {"activeTab", "scripting", "storage"}
            assert "host_permissions" not in manifest
            assert "optional_host_permissions" not in manifest
            mark(report, "manifest", "PASS", "MV3; minimal permissions; no host permissions")

            context.grant_permissions(["clipboard-read", "clipboard-write"])
            web_page = context.pages[0] if context.pages else context.new_page()
            web_page.goto(f"{base_url}/tests/fixtures/forms.html", wait_until="load")
            page = context.new_page()
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http://", "https://")) else None)
            page.goto(popup_url(extension_id), wait_until="domcontentloaded")
            page.locator("#candidates .candidate").first.wait_for(timeout=10_000)
            assert page.locator("#candidates .candidate").count() == 5
            assert "5 names composed locally" in page.locator("#status").inner_text()
            mark(report, "popupGeneration", "PASS", "5 seeded candidates rendered")
            screenshot(report, page, screenshots / f"{browser_name}-popup.png")

            first_name = page.locator(".candidate-name").first.inner_text()
            page.locator(".candidate .copy").first.click()
            page.wait_for_timeout(250)
            copied = page.evaluate("navigator.clipboard.readText()")
            assert copied == first_name
            mark(report, "copy", "PASS", first_name)

            context.set_offline(True)
            page.reload(wait_until="domcontentloaded")
            page.locator("#candidates .candidate").first.wait_for(timeout=10_000)
            assert page.locator("#candidates .candidate").count() == 5
            mark(report, "offlineGeneration", "PASS", "Popup reloaded with network disabled")
            context.set_offline(False)

            page.locator("details.advanced summary").click()
            assert page.locator("#rule").is_visible()
            page.locator("#rule").select_option("quote_splice")
            page.locator("#suffix").select_option("none")
            page.locator("#candidateCount").select_option("4")
            page.locator("#seed").fill("23")
            page.locator("#generate").click()
            page.locator("#candidates .candidate").first.wait_for(timeout=10_000)
            assert page.locator("#candidates .candidate").count() == 4
            assert all(name.isalpha() for name in page.locator(".candidate-name").all_inner_texts())
            page.reload(wait_until="domcontentloaded")
            page.locator("#candidates .candidate").first.wait_for(timeout=10_000)
            assert page.locator("#rule").input_value() == "quote_splice"
            assert page.locator("#suffix").input_value() == "none"
            assert page.locator("#candidateCount").input_value() == "4"
            assert page.locator("#seed").input_value() == "23"
            mark(report, "preferencePersistence", "PASS", "Rule, suffix, count and seed survived reload")
            stored = page.evaluate("chrome.storage.local.get(null)")
            assert set(stored.keys()) == {"nickspeare.preferences.v1"}
            mark(report, "storageBoundary", "PASS", "Only versioned preferences are stored")

            page.locator("#seed").fill("24")
            page.locator("#generate").focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(250)
            assert page.locator(".candidate-name").first.inner_text()
            mark(report, "keyboard", "PASS", "Generate button is keyboard-activatable")

            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            mark(report, "narrowLayout", "PASS", "396px popup has no horizontal overflow")

            page.locator("details.advanced summary").click()
            assert page.locator("#reservedWords").is_visible()
            accessible = page.evaluate("""() => {
                const buttons = [...document.querySelectorAll('button')];
                return buttons.every((button) => button.textContent.trim() || button.getAttribute('aria-label'));
            }""")
            assert accessible
            mark(report, "accessibilityBasics", "PASS", "Native controls, visible labels and named buttons")

            popup_tab_id = page.evaluate("chrome.tabs.query({active:true,currentWindow:true})")[0]["id"]
            target_tab_id = other_tab_id(page, {int(popup_tab_id)})
            page.evaluate(f"chrome.tabs.update({target_tab_id}, {{active:true}})")
            page.evaluate("document.querySelector('.fill').click()")
            page.wait_for_timeout(500)
            context_text = page.locator("#field-context").inner_text()
            assert "not available" in context_text or "could not be inspected" in context_text, context_text
            assert page.locator(".field-choice").count() == 0
            mark(report, "permissionDenied", "PASS", context_text)

            assert not console_errors, console_errors
            assert not remote_requests, remote_requests
            mark(report, "noRemoteRuntime", "PASS", "No HTTP(S) runtime requests during popup checks")
        finally:
            context.close()


def check_field_insertion(playwright, browser_name: str, base_url: str, report: dict, screenshots: Path):
    popup_errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="nickspeare-fields-") as profile:
        context = launch_context(playwright, browser_name, profile, TEST_EXTENSION)
        try:
            extension_id = wait_for_extension(context)
            test_page = context.pages[0] if context.pages else context.new_page()
            console_errors: list[str] = []
            test_page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            test_page.on("pageerror", lambda error: console_errors.append(str(error)))
            test_page.goto(f"{base_url}/tests/fixtures/forms.html", wait_until="networkidle")
            test_page.locator("#react-value").wait_for(timeout=10_000)
            test_page.evaluate("(url) => { document.querySelector('#cross-frame').src = url; }", f"{base_url}/tests/fixtures/iframe.html")
            popup = context.new_page()
            popup.on("console", lambda message: popup_errors.append(message.text) if message.type == "error" else None)
            popup.on("pageerror", lambda error: popup_errors.append(str(error)))
            popup.goto(popup_url(extension_id), wait_until="domcontentloaded")
            popup.locator(".candidate").first.wait_for(timeout=10_000)
            candidate = popup.locator(".candidate-name").first.inner_text()
            test_tab_id = find_test_tab(popup, "forms.html")
            popup.evaluate(f"chrome.tabs.update({test_tab_id}, {{active:true}})")

            popup.evaluate("document.querySelector('.fill').click()")
            popup.locator(".field-choice").first.wait_for(timeout=10_000)
            fields = popup.locator(".field-choice")
            categories = fields.evaluate_all("(els) => els.map((el) => el.dataset.category)")
            expected = ["registration_username", "login_username", "display_name", "display_name", "other_text"]
            assert categories == expected, categories
            field_text = popup.locator("#field-list").inner_text()
            assert "Choose a username" in field_text
            assert "Username" in field_text
            assert "Display nickname" in field_text
            assert "Search this site" in field_text
            assert "Email address" not in field_text
            assert "Password" not in field_text
            assert popup.locator("#field-list img").count() == 0
            assert test_page.evaluate("window.__xss === undefined")
            assert "Username in frame" not in field_text
            screenshot(report, popup, screenshots / f"{browser_name}-field-panel.png")
            mark(report, "fieldDetection", "PASS", f"classified: {', '.join(categories)}")
            mark(report, "sensitiveFieldProtection", "PASS", "Email, password and hidden fields excluded")

            login_field = popup.locator('.field-choice[data-element-id="login-username"]')
            login_id = login_field.get_attribute("data-field-id")
            nonempty_error = popup.evaluate(
                """async ({tabId, fieldId, value}) => {
                    return await chrome.tabs.sendMessage(tabId, {
                        type: 'nickspeare.fill-field',
                        fieldId,
                        value,
                        replaceExisting: false,
                    });
                }""",
                {"tabId": test_tab_id, "fieldId": login_id, "value": candidate},
            )
            assert nonempty_error["errorCode"] == "FIELD_NOT_EMPTY"
            assert test_page.locator("#login-username").input_value() == "existing_user"
            mark(report, "nonEmptyProtection", "PASS", "Direct fill refused without replaceExisting=true")

            popup.locator('.field-choice[data-element-id="register-username"]').evaluate("(el) => el.click()")
            test_page.wait_for_function("document.querySelector('#register-username').value.length > 0")
            assert test_page.locator("#register-username").input_value() == candidate
            events = test_page.evaluate("window.fieldEvents")
            assert events == [
                {"type": "input", "id": "register-username", "value": candidate},
                {"type": "change", "id": "register-username", "value": candidate},
            ], events
            assert test_page.evaluate("window.submitEvents") == 0
            mark(report, "emptyFieldInsertion", "PASS", "Native setter plus input/change events")

            popup.evaluate("document.querySelector('.fill').click()")
            popup.locator(".field-choice").first.wait_for(timeout=10_000)
            assert "replace existing text" in popup.locator('.field-choice[data-element-id="login-username"]').inner_text().lower()
            popup.locator('.field-choice[data-element-id="login-username"]').evaluate("(el) => el.click()")
            test_page.wait_for_function("document.querySelector('#login-username').value !== 'existing_user'")
            assert test_page.locator("#login-username").input_value() == candidate
            mark(report, "explicitReplacement", "PASS", "Login field replaced only through an explicit replace action")

            popup.evaluate("document.querySelector('.fill').click()")
            popup.locator(".field-choice").first.wait_for(timeout=10_000)
            popup.locator('.field-choice[data-element-id="react-username"]').evaluate("(el) => el.click()")
            test_page.wait_for_function("window.reactUsernameState.length > 0")
            assert test_page.evaluate("window.reactUsernameState") == candidate
            assert candidate in test_page.locator("#react-value").inner_text()
            mark(report, "reactControlledInput", "PASS", "React state and native input stayed synchronized")

            assert test_page.locator("#register-email").input_value() == ""
            assert test_page.locator("#register-password").input_value() == ""
            assert test_page.locator("#hidden-username").input_value() == "hidden"
            assert test_page.evaluate("window.submitEvents") == 0
            mark(report, "nonIntrusive", "PASS", "No form submission and sensitive values untouched")

            restricted = context.new_page()
            restricted.goto("chrome://version", wait_until="domcontentloaded")
            popup_tab_id = popup.evaluate("chrome.tabs.query({active:true,currentWindow:true})")[0]["id"]
            restricted_id = other_tab_id(popup, {int(popup_tab_id), int(test_tab_id)})
            popup.evaluate(f"chrome.tabs.update({restricted_id}, {{active:true}})")
            popup.evaluate("document.querySelector('.fill').click()")
            popup.wait_for_timeout(400)
            restricted_text = popup.locator("#field-context").inner_text()
            assert "do not allow" in restricted_text or "not available" in restricted_text or "could not be inspected" in restricted_text, restricted_text
            mark(report, "restrictedPage", "PASS", restricted_text)

            assert not console_errors, console_errors
            assert not popup_errors, popup_errors
        finally:
            context.close()


def run(browser_name: str, output: Path) -> dict:
    report = result_template(browser_name)
    if not EXTENSION.joinpath("manifest.json").is_file() or not TEST_EXTENSION.joinpath("manifest.json").is_file():
        report["errors"].append("Extension builds are missing; run npm run build:extension and npm run build:extension:test first")
        return report
    output.parent.mkdir(parents=True, exist_ok=True)
    screenshots = output.parent / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    server, base_url, _thread = start_server()
    try:
        with sync_playwright() as playwright:
            try:
                check_popup_and_permission_denial(playwright, browser_name, base_url, report, screenshots)
                check_field_insertion(playwright, browser_name, base_url, report, screenshots)
                report["status"] = "PASS"
            except PlaywrightError as error:
                report["errors"].append(f"Browser/extension failure: {error}")
                report["status"] = "FAIL"
            except Exception as error:  # noqa: BLE001 - evidence must retain any failure
                report["errors"].append(f"{type(error).__name__}: {error}")
                report["status"] = "FAIL"
    finally:
        server.shutdown()
        server.server_close()
    report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=["chromium", "msedge", "chrome"], default="chromium")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "extension-test-results.json")
    args = parser.parse_args()
    report = run(args.browser, args.output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
