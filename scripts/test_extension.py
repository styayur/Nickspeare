"""Load the built MV3 extension in a real Chromium/Edge profile and verify its popup."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "dist" / "extension"


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
        "screenshots": [],
    }


def mark(report: dict, name: str, status: str, detail: str = "") -> None:
    report["checks"][name] = {"status": status, "detail": detail}


def launch_context(playwright, browser_name: str, profile: str):
    common = {
        "headless": False,
        "viewport": {"width": 396, "height": 600},
        "args": [
            f"--disable-extensions-except={EXTENSION}",
            f"--load-extension={EXTENSION}",
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


def run(browser_name: str, output: Path) -> dict:
    report = result_template(browser_name)
    if not EXTENSION.joinpath("manifest.json").is_file():
        report["errors"].append("dist/extension is missing; run npm run build:extension first")
        return report
    output.parent.mkdir(parents=True, exist_ok=True)
    screenshots = output.parent / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    remote_requests: list[str] = []

    with tempfile.TemporaryDirectory(prefix="nickspeare-extension-") as profile:
        with sync_playwright() as playwright:
            try:
                context = launch_context(playwright, browser_name, profile)
            except PlaywrightError as error:
                report["errors"].append(f"Browser could not load the extension: {error}")
                return report
            try:
                if not context.service_workers:
                    context.wait_for_event("serviceworker", timeout=15_000)
                if not context.service_workers:
                    raise AssertionError("Extension service worker did not start")
                extension_id = context.service_workers[0].url.split("/")[2]
                mark(report, "extensionLoad", "PASS", context.service_workers[0].url)

                manifest = json.loads(EXTENSION.joinpath("manifest.json").read_text(encoding="utf-8"))
                assert manifest["manifest_version"] == 3
                assert manifest["version"] == "0.1.0"
                assert manifest["version_name"] == "0.1.0-alpha.1"
                assert set(manifest.get("permissions", [])) == {"activeTab", "scripting", "storage"}
                assert "host_permissions" not in manifest
                mark(report, "manifest", "PASS", "MV3; minimal permissions; no host permissions")

                context.grant_permissions(["clipboard-read", "clipboard-write"])
                page = context.new_page()
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: console_errors.append(str(error)))
                page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith(("http://", "https://")) else None)
                popup_url = f"chrome-extension://{extension_id}/popup/popup.html"
                page.goto(popup_url, wait_until="domcontentloaded")
                page.locator("#candidates .candidate").first.wait_for(timeout=10_000)
                assert page.locator("#candidates .candidate").count() == 5
                assert "5 names composed locally" in page.locator("#status").inner_text()
                mark(report, "popupGeneration", "PASS", "5 seeded candidates rendered")
                screenshot = screenshots / f"{browser_name}-popup.png"
                page.screenshot(path=str(screenshot), full_page=True)
                report["screenshots"].append(str(screenshot.relative_to(ROOT)))

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

                assert not console_errors, console_errors
                assert not remote_requests, remote_requests
                mark(report, "noRemoteRuntime", "PASS", "No HTTP(S) runtime requests during popup checks")
                report["status"] = "PASS"
            except Exception as error:  # noqa: BLE001 - evidence must retain any failure
                report["errors"].append(f"{type(error).__name__}: {error}")
                report["status"] = "FAIL"
                try:
                    page.screenshot(path=str(screenshots / f"{browser_name}-failure.png"), full_page=True)
                    report["screenshots"].append(str((screenshots / f"{browser_name}-failure.png").relative_to(ROOT)))
                except Exception:
                    pass
            finally:
                context.close()

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
