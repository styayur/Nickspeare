#!/usr/bin/env python3
"""Build the machine-readable extension acceptance record and checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_BROWSER_CHECKS = [
    "extensionLoad",
    "manifest",
    "popupGeneration",
    "copy",
    "offlineGeneration",
    "preferencePersistence",
    "storageBoundary",
    "keyboard",
    "narrowLayout",
    "accessibilityBasics",
    "permissionDenied",
    "noRemoteRuntime",
    "fieldDetection",
    "sensitiveFieldProtection",
    "nonEmptyProtection",
    "emptyFieldInsertion",
    "explicitReplacement",
    "reactControlledInput",
    "nonIntrusive",
    "restrictedPage",
]
CORE_COVERAGE_THRESHOLDS = {"lines": 80.0, "branches": 75.0, "functions": 85.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path | None) -> dict:
    if not path or not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_node(log: str) -> dict:
    tests = re.search(r"(?:ℹ|#)\s*tests\s+(\d+)", log)
    passed = re.search(r"(?:ℹ|#)\s*pass\s+(\d+)", log)
    failed = re.search(r"(?:ℹ|#)\s*fail\s+(\d+)", log)
    test_count = int(tests.group(1)) if tests else 0
    pass_count = int(passed.group(1)) if passed else 0
    fail_count = int(failed.group(1)) if failed else (test_count - pass_count if test_count else 0)
    return {
        "status": "PASS" if test_count and fail_count == 0 and pass_count == test_count else "FAIL",
        "tests": test_count,
        "passed": pass_count,
        "failed": fail_count,
        "passRate": round(pass_count / test_count * 100, 2) if test_count else 0.0,
    }


def parse_python(log: str) -> dict:
    ran = re.search(r"Ran (\d+) tests?", log)
    test_count = int(ran.group(1)) if ran else 0
    ok = bool(re.search(r"^OK$", log, re.M))
    return {
        "status": "PASS" if test_count and ok else "FAIL",
        "tests": test_count,
        "passed": test_count if ok else 0,
        "failed": 0 if ok else max(1, test_count),
        "passRate": 100.0 if test_count and ok else 0.0,
    }


def parse_coverage(log: str) -> dict:
    match = re.search(r"all files\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)", log)
    if not match:
        return {"status": "NOT_RUN", "lines": None, "branches": None, "functions": None}
    values = {
        "lines": float(match.group(1)),
        "branches": float(match.group(2)),
        "functions": float(match.group(3)),
    }
    passed = all(values[key] >= threshold for key, threshold in CORE_COVERAGE_THRESHOLDS.items())
    return {
        "status": "PASS" if passed else "FAIL",
        **values,
        "thresholds": CORE_COVERAGE_THRESHOLDS,
        "scope": "packages/core JavaScript executed by Node's built-in test coverage",
    }


def browser_result(path: Path | None) -> dict:
    report = read_json(path)
    checks = report.get("checks") or {}
    required = {name: (checks.get(name) or {}).get("status", "NOT_RUN") for name in REQUIRED_BROWSER_CHECKS}
    missing_or_failed = [name for name, status in required.items() if status != "PASS"]
    status = "PASS" if report.get("status") == "PASS" and not missing_or_failed else ("FAIL" if report else "NOT_RUN")
    user_agent = report.get("userAgent") or ""
    version = None
    match = re.search(r"(?:Edg|Chrome)/([0-9.]+)", user_agent)
    if match:
        version = match.group(1)
    return {
        "status": status,
        "browser": report.get("browser"),
        "version": version,
        "source": str(path.relative_to(ROOT)).replace("\\", "/") if path and path.is_file() else None,
        "passedChecks": sum(1 for value in required.values() if value == "PASS"),
        "requiredChecks": len(required),
        "failedOrMissingChecks": missing_or_failed,
        "verifiedAt": report.get("finishedAt"),
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def dimension(weight: float, earned: float, detail: str) -> dict:
    return {"weight": weight, "earned": round(earned, 2), "detail": detail}


def apply_exact_checks(args) -> None:
    if not getattr(args, "exact_checks", None) or not args.exact_checks.is_file():
        return
    exact = read_json(args.exact_checks)
    checks = exact.get("checks") or {}
    args.ci_status = "PASS" if exact.get("status") == "PASS" else "FAIL"
    args.codeql_status = (checks.get("codeql") or {}).get("status", "NOT_RUN")
    args.codeforge_status = (checks.get("codeforge") or {}).get("status", "NOT_RUN")
    args.codeql_url = exact.get("codeqlUrl") or args.codeql_url
    args.codeforge_url = exact.get("codeforgeUrl") or args.codeforge_url


def generate(args) -> dict:
    node = parse_node(args.node_log.read_text(encoding="utf-8") if args.node_log.is_file() else "")
    python = parse_python(args.python_log.read_text(encoding="utf-8") if args.python_log.is_file() else "")
    coverage = parse_coverage(args.coverage_log.read_text(encoding="utf-8") if args.coverage_log.is_file() else "")
    pages_text = args.pages_log.read_text(encoding="utf-8") if args.pages_log.is_file() else ""
    pages = {"status": "PASS" if "Browser checks passed:" in pages_text else "FAIL"}
    chromium = browser_result(args.chromium)
    edge = browser_result(args.edge)
    if not args.edge:
        edge = {"status": "NOT_RUN", "browser": "msedge", "version": None, "reason": "No Edge evidence supplied."}
    audit = read_json(args.audit)
    package = read_json(args.package)
    extension_version = str(package.get("version") or "")
    manifest_version = str(package.get("manifestVersion") or "")
    commit = args.commit or git_commit()
    blockers: list[str] = []
    manifest = read_json(ROOT / "extension" / "manifest.json")
    if not extension_version:
        blockers.append("Package evidence omits the extension version")
    if not manifest_version:
        blockers.append("Package evidence omits the manifest version")
    if extension_version and manifest.get("version_name") != extension_version:
        blockers.append("Package version does not match extension/manifest.json version_name")
    if manifest_version and manifest.get("version") != manifest_version:
        blockers.append("Package manifestVersion does not match extension/manifest.json version")

    if chromium.get("status") != "PASS":
        blockers.append("Chromium extension acceptance did not pass")
    if edge.get("status") == "FAIL":
        blockers.append("Edge compatibility failed")
    if node.get("status") != "PASS":
        blockers.append("Node regression suite failed or was not run")
    if python.get("status") != "PASS":
        blockers.append("Python regression suite failed or was not run")
    if pages.get("status") != "PASS":
        blockers.append("GitHub Pages regression suite failed or was not run")
    if coverage.get("status") != "PASS":
        blockers.append("Core coverage is below the recorded thresholds or was not measured")
    if audit.get("status") != "PASS":
        blockers.append("Extension security audit did not pass")
    if package.get("status") != "PASS":
        blockers.append("Extension packaging verification did not pass")
    for key, value in (("ci", args.ci_status), ("codeql", args.codeql_status), ("codeforge", args.codeforge_status)):
        if value != "PASS":
            blockers.append(f"Exact-commit {key} evidence is {value}")
    if args.governance_status != "PASS":
        blockers.append(f"Repository governance status is {args.governance_status}")

    archive_path = ROOT / package.get("archive", "") if package.get("archive") else None
    archive_ok = bool(archive_path and archive_path.is_file() and sha256(archive_path) == package.get("sha256"))
    if not archive_ok:
        blockers.append("Release archive checksum does not match the package evidence")

    provenance = package.get("provenance") or {}
    provenance_clean = provenance.get("dirty") is False
    provenance_matches = bool(commit and provenance.get("commit") == commit)
    if not provenance_clean:
        blockers.append("Release build provenance is dirty")
    if not provenance_matches:
        blockers.append("Release build provenance commit does not match the acceptance commit")

    audit_checks = audit.get("checks") or {}
    for required in ("permissionsMinimal", "noHostPermissions", "noEval", "noRemoteScript", "noEmbeddedSecrets", "workflowPinning", "noRuntimeDependencies", "pythonDevPins", "codeforgeToolPin", "corpusRights", "licenseFiles", "sourceOffer"):
        if (audit_checks.get(required) or {}).get("status") != "PASS":
            blockers.append(f"Security/license hard gate {required} is not PASS")

    unit_earned = 15 if node.get("status") == "PASS" else 0
    regression_earned = (10 if pages.get("status") == "PASS" else 0) + (5 if python.get("status") == "PASS" else 0)
    coverage_earned = 0.0
    if coverage.get("status") in {"PASS", "FAIL"}:
        for key, points in (("lines", 4), ("branches", 3), ("functions", 3)):
            if coverage.get(key) is not None and coverage[key] >= CORE_COVERAGE_THRESHOLDS[key]:
                coverage_earned += points
    functional_earned = 20 if chromium.get("status") == "PASS" else 20 * (chromium.get("passedChecks", 0) / max(1, chromium.get("requiredChecks", 1)))
    chromium_earned = 10 if chromium.get("status") == "PASS" else 0
    edge_earned = 10 if edge.get("status") == "PASS" else 0
    acc_status = "PASS" if all((read_json(args.chromium).get("checks") or {}).get(name, {}).get("status") == "PASS" for name in ("keyboard", "narrowLayout", "accessibilityBasics")) else "FAIL"
    accessibility_earned = 10 if acc_status == "PASS" else 0
    package_earned = 10 if package.get("status") == "PASS" and archive_ok else 0
    dimensions = {
        "unitTests": dimension(15, unit_earned, "Node unit/regression tests"),
        "regression": dimension(15, regression_earned, "Existing Pages browser regression and Python package tests"),
        "coreCoverage": dimension(10, coverage_earned, "Node built-in coverage for packages/core"),
        "functionalAcceptance": dimension(20, functional_earned, "Required extension checks in a real Chromium profile"),
        "chromiumCompatibility": dimension(10, chromium_earned, "Chromium MV3 load and runtime checks"),
        "edgeCompatibility": dimension(10, edge_earned, "Actual Microsoft Edge MV3 checks when available"),
        "accessibility": dimension(10, accessibility_earned, "Keyboard, narrow popup and named-control checks"),
        "releaseHygiene": dimension(10, package_earned, "ZIP structure, licenses, path safety and checksum"),
    }
    quality_score = round(sum(item["earned"] for item in dimensions.values()), 2)
    release_ready = not blockers and commit and chromium.get("status") == "PASS" and archive_ok and provenance_clean and provenance_matches and args.governance_status == "PASS"
    overall = "PASS" if release_ready else ("FAIL" if any("failed" in blocker.lower() or "does not match" in blocker.lower() for blocker in blockers) else "BLOCKED")
    security_status = "PASS" if all((audit_checks.get(name) or {}).get("status") == "PASS" for name in ("permissionsMinimal", "noHostPermissions", "noEval", "noRemoteScript", "noEmbeddedSecrets", "workflowPinning", "noRuntimeDependencies", "pythonDevPins", "codeforgeToolPin")) and args.codeql_status == "PASS" and args.codeforge_status == "PASS" else "FAIL"
    license_status = "PASS" if all((audit_checks.get(name) or {}).get("status") == "PASS" for name in ("licenseFiles", "corpusRights", "sourceOffer")) else "FAIL"

    return {
        "schemaVersion": 1,
        "project": "Nickspeare",
        "component": "browser-extension",
        "version": extension_version,
        "manifestVersion": manifest_version,
        "commit": commit or None,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overallStatus": overall,
        "qualityScore": quality_score,
        "scoring": {
            "scale": 100,
            "securityAndLicenseTreatment": "Hard gates; not compensated by the quality score.",
            "dimensions": dimensions,
        },
        "checks": {
            "node": node,
            "python": python,
            "pagesRegression": pages,
            "coreCoverage": coverage,
            "browserSuite": chromium,
        },
        "security": {
            "status": security_status,
            "audit": audit,
            "external": {
                "codeql": {"status": args.codeql_status, "url": args.codeql_url or None},
                "codeforge": {"status": args.codeforge_status, "url": args.codeforge_url or None},
                "governance": {"status": args.governance_status, "url": args.governance_url or None},
            },
        },
        "compatibility": {
            "chromium": chromium,
            "msedge": edge,
            "googleChromeBranded": {"status": "NOT_RUN", "reason": "Google Chrome branded builds block CLI extension loading; Chromium MV3 engine is verified instead."},
            "firefox": {"status": "NOT_APPLICABLE", "reason": f"Firefox retention is a design goal; {extension_version} targets Chromium and Edge."},
        },
        "licenses": {
            "status": license_status,
            "application": "AGPL-3.0-or-later",
            "corpusDerivatives": "CC BY-NC 3.0",
            "corpusAttributionIncluded": (audit_checks.get("corpusRights") or {}).get("status") == "PASS",
            "commercialUseClaimed": False,
            "notice": "Third-party Folger-derived evidence remains noncommercial; the AGPL code license does not relicense it.",
        },
        "release": {
            "tag": f"extension-v{extension_version}",
            "prerelease": True,
            "archive": package.get("archive"),
            "archiveSha256": package.get("sha256"),
            "archiveBytes": package.get("archiveBytes"),
            "checksumFile": "artifacts/SHA256SUMS",
            "package": package,
        },
        "releaseReady": release_ready,
        "blockers": blockers,
        "limitations": [
            "Automated scores are project-generated acceptance measurements, not third-party certification.",
            "Fields inside iframes and closed shadow roots are not accessed in v0.1.",
            "In-page suggestions and persistent per-site permissions are deferred; insertion is on demand.",
            "Username availability is not checked with any remote service.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="")
    parser.add_argument("--node-log", type=Path, required=True)
    parser.add_argument("--coverage-log", type=Path, required=True)
    parser.add_argument("--python-log", type=Path, required=True)
    parser.add_argument("--pages-log", type=Path, required=True)
    parser.add_argument("--chromium", type=Path, required=True)
    parser.add_argument("--edge", type=Path)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--exact-checks", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "extension-acceptance.json")
    parser.add_argument("--ci-status", choices=["PASS", "FAIL", "NOT_RUN"], default="NOT_RUN")
    parser.add_argument("--codeql-status", choices=["PASS", "FAIL", "NOT_RUN"], default="NOT_RUN")
    parser.add_argument("--codeforge-status", choices=["PASS", "FAIL", "NOT_RUN"], default="NOT_RUN")
    parser.add_argument("--codeql-url", default="")
    parser.add_argument("--codeforge-url", default="")
    parser.add_argument("--governance-status", choices=["PASS", "FAIL", "BLOCKED", "NOT_RUN"], default="NOT_RUN")
    parser.add_argument("--governance-url", default="")
    args = parser.parse_args()
    for attribute in ("node_log", "coverage_log", "python_log", "pages_log", "chromium", "edge", "audit", "package", "exact_checks", "output"):
        value = getattr(args, attribute, None)
        if value is not None:
            setattr(args, attribute, value.resolve())
    apply_exact_checks(args)
    report = generate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    archive = ROOT / report["release"]["archive"] if report["release"]["archive"] else None
    checksum_lines = []
    if archive and archive.is_file():
        checksum_lines.append(f"{sha256(archive)}  {archive.name}")
    checksum_lines.append(f"{sha256(args.output)}  {args.output.name}")
    checksum_path = args.output.parent / "SHA256SUMS"
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({
        "overallStatus": report["overallStatus"],
        "qualityScore": report["qualityScore"],
        "releaseReady": report["releaseReady"],
        "blockers": report["blockers"],
        "checksumFile": str(checksum_path),
    }, indent=2) + "\n")
    return 0 if report["releaseReady"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
