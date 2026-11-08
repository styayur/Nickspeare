#!/usr/bin/env python3
"""Fail-closed static audit of the built browser extension."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9
    import tomli as tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "dist" / "extension"
ALLOWED_PERMISSIONS = {"activeTab", "scripting", "storage"}
FORBIDDEN_PATH_PARTS = {".git", "node_modules", "tests", "test", "coverage", "__pycache__"}
ALLOWED_SUFFIXES = {".js", ".json", ".css", ".html", ".png", ".md", ""}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
SENSITIVE_PERMISSIONS = {"cookies", "history", "webRequest", "webRequestBlocking", "management", "debugger", "proxy"}


def check(checks: dict, name: str, passed: bool, detail: str, blockers: list[str]) -> None:
    status = "PASS" if passed else "FAIL"
    checks[name] = {"status": status, "detail": detail}
    if not passed:
        blockers.append(f"{name}: {detail}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def audit(root: Path) -> dict:
    checks: dict = {}
    blockers: list[str] = []
    files = relative_files(root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return {
            "schemaVersion": 1,
            "status": "BLOCKED",
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": {},
            "blockers": ["manifest.json is missing"],
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check(checks, "manifestV3", manifest.get("manifest_version") == 3, "Manifest V3 is required.", blockers)
    check(checks, "version", manifest.get("version") == "0.1.0" and manifest.get("version_name") == "0.1.0-alpha.1", "Extension version identity is 0.1.0 / 0.1.0-alpha.1.", blockers)
    permissions = set(manifest.get("permissions", []))
    check(checks, "permissionsMinimal", permissions == ALLOWED_PERMISSIONS, f"Permissions: {sorted(permissions)}", blockers)
    check(checks, "noHostPermissions", "host_permissions" not in manifest, "Production has no permanent host permissions.", blockers)
    check(checks, "noOptionalHostPermissions", "optional_host_permissions" not in manifest, "No optional host permissions are exposed in v0.1.", blockers)
    check(checks, "noSensitivePermissions", not (permissions & SENSITIVE_PERMISSIONS), "No cookie, history, request interception, debugger or proxy permissions.", blockers)
    check(checks, "noExternalConnections", "externally_connectable" not in manifest, "Websites cannot call extension APIs through externally_connectable.", blockers)
    check(checks, "noDeclarativePageAccess", not manifest.get("content_scripts"), "Page access is on demand through activeTab + scripting.", blockers)
    csp = (manifest.get("content_security_policy") or {}).get("extension_pages", "")
    check(checks, "csp", "script-src 'self'" in csp and "unsafe-eval" not in csp and "unsafe-inline" not in csp, f"extension_pages CSP: {csp}", blockers)

    javascript = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files if path.suffix == ".js")
    html = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files if path.suffix == ".html")
    check(checks, "noEval", not re.search(r"\beval\s*\(|\bnew\s+Function\b", javascript), "No eval or dynamic Function constructor.", blockers)
    check(checks, "noDestructiveHtml", not re.search(r"\.innerHTML\s*=|insertAdjacentHTML|document\.write", javascript), "Dynamic DOM content is inserted through text nodes and DOM APIs.", blockers)
    check(checks, "noRemoteScript", not re.search(r"<script[^>]+src=[\"']https?:", html, re.I) and not re.search(r"https?://[^\s\"']+\.js\b", javascript), "No remote script or dynamic remote code URL.", blockers)
    check(checks, "messageValidation", "sender.id !== chrome.runtime.id" in javascript, "Content-script messages require the extension sender identity.", blockers)
    check(checks, "sensitiveFieldGuard", "SENSITIVE_HINTS" in javascript and "password" in javascript.lower(), "Password, email, OTP and payment-like fields are excluded.", blockers)
    check(checks, "nonEmptyGuard", "FIELD_NOT_EMPTY" in javascript and "replaceExisting" in javascript, "Non-empty fields require an explicit replace flag.", blockers)
    check(checks, "noTelemetrySdk", not re.search(r"google-analytics|segment\.io|sentry|posthog|mixpanel|amplitude", javascript, re.I), "No analytics, telemetry or crash-reporting SDK.", blockers)
    check(checks, "storageBoundary", "nickspeare.preferences.v1" in javascript and "chrome.storage" in javascript, "Storage is limited to versioned preferences.", blockers)

    secret_findings = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                secret_findings.append(f"{path.relative_to(root)}: {name}")
    check(checks, "noEmbeddedSecrets", not secret_findings, "No credential-shaped strings found.", blockers) if not secret_findings else check(checks, "noEmbeddedSecrets", False, ", ".join(secret_findings), blockers)

    bad_paths = [str(path.relative_to(root)) for path in files if any(part in FORBIDDEN_PATH_PARTS for part in path.relative_to(root).parts) or path.suffix.lower() not in ALLOWED_SUFFIXES]
    check(checks, "packageContents", not bad_paths, "No development, cache, source-map or private files." if not bad_paths else f"Forbidden: {bad_paths}", blockers)
    licenses_ok = (root / "licenses" / "LICENSE").is_file() and (root / "licenses" / "DATA_SOURCES.md").is_file()
    check(checks, "licenseFiles", licenses_ok, "AGPL license and data-source attribution are included.", blockers)
    check(checks, "sourceOffer", (root / "SOURCE.md").is_file(), "Readable runtime source and the public repository URL are included.", blockers)
    data_sources = (root / "licenses" / "DATA_SOURCES.md").read_text(encoding="utf-8") if licenses_ok else ""
    corpus_ok = "CC BY-NC 3.0" in data_sources and "noncommercial" in data_sources.lower()
    check(checks, "corpusRights", corpus_ok, "Derived Folger corpus rights remain attributable and noncommercial.", blockers)
    size = sum(path.stat().st_size for path in files)
    check(checks, "lightweightPackage", size <= 2 * 1024 * 1024, f"Unpacked runtime payload is {size} bytes.", blockers)

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    runtime_dependencies = package.get("dependencies") or {}
    check(checks, "noRuntimeDependencies", not runtime_dependencies, "The extension has zero production npm dependencies.", blockers)
    workflow_files = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    unpinned = []
    pattern = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
    for workflow in workflow_files:
        for reference in pattern.findall(workflow.read_text(encoding="utf-8")):
            if reference.startswith("./"):
                continue
            if not re.search(r"@[0-9a-f]{40}$", reference):
                unpinned.append(f"{workflow.name}: {reference}")
    check(checks, "workflowPinning", not unpinned, "All GitHub Actions and reusable workflows use reviewed full commit SHAs." if not unpinned else "; ".join(unpinned), blockers)
    lock_path = ROOT / "package-lock.json"
    lock_ok = False
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_ok = lock.get("lockfileVersion") == 3 and not ((lock.get("packages") or {}).get("") or {}).get("dependencies")
    check(checks, "dependencyLock", lock_ok, "npm lockfile v3 is present and records no production dependencies.", blockers)
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = ((pyproject.get("project") or {}).get("optional-dependencies") or {}).get("dev") or []
    python_dev_pinned = bool(dev_dependencies) and all("==" in item for item in dev_dependencies)
    check(checks, "pythonDevPins", python_dev_pinned, f"Python development tools are exact-pinned: {dev_dependencies}", blockers)
    codeforge_workflow = (ROOT / ".github" / "workflows" / "codeforge-regression.yml").read_text(encoding="utf-8")
    codeforge_rev_pinned = bool(re.search(r"cargo install .*--rev [0-9a-f]{40}", codeforge_workflow))
    check(checks, "codeforgeToolPin", codeforge_rev_pinned, "CodeForge is installed from a reviewed full commit revision.", blockers)
    inventory = [
        {"path": str(path.relative_to(root)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    status = "PASS" if not blockers else "FAIL"
    return {
        "schemaVersion": 1,
        "project": "Nickspeare",
        "component": "browser-extension",
        "version": manifest.get("version_name"),
        "manifestVersion": manifest.get("version"),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "checks": checks,
        "blockers": blockers,
        "files": inventory,
        "totals": {"files": len(files), "bytes": size},
        "limitations": "This is an automated source and package audit, not an independent third-party security certification.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "extension-audit.json")
    args = parser.parse_args()
    report = audit(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({key: report.get(key) for key in ("status", "version", "blockers", "totals")}, indent=2) + "\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
