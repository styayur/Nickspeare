#!/usr/bin/env python3
"""Wait for trusted exact-commit GitHub Actions checks required by release acceptance."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

REQUIRED = {
    "build": "build",
    "browser": "browser",
    "python39": "python (3.9)",
    "python312": "python (3.12)",
    "python314": "python (3.14)",
    "codeforge": "CodeForge regression",
    "codeql": "CodeQL",
}


def api(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nickspeare-release-evidence",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def latest_runs(runs: list[dict]) -> dict[str, dict]:
    selected: dict[str, dict] = {}
    for run in runs:
        name = str(run.get("name") or "")
        if name not in REQUIRED.values():
            continue
        previous = selected.get(name)
        current_good = str(run.get("status") or "").upper() == "COMPLETED" and str(run.get("conclusion") or "").upper() == "SUCCESS"
        previous_good = bool(previous) and str(previous.get("status") or "").upper() == "COMPLETED" and str(previous.get("conclusion") or "").upper() == "SUCCESS"
        if name == "CodeQL" and previous_good and not current_good:
            continue
        if previous is None or str(run.get("started_at") or "") >= str(previous.get("started_at") or ""):
            selected[name] = run
    return selected


def collect(repo: str, sha: str, token: str, timeout: int, interval: int) -> dict:
    deadline = time.time() + timeout
    last = {}
    while True:
        data = api(f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100", token)
        last = latest_runs(data.get("check_runs") or [])
        summaries = {}
        pending = []
        for key, name in REQUIRED.items():
            run = last.get(name)
            if not run:
                summaries[key] = {"name": name, "status": "MISSING", "conclusion": None, "url": None}
                pending.append(name)
                continue
            status = str(run.get("status") or "").upper()
            conclusion = str(run.get("conclusion") or "").upper()
            app_slug = str((run.get("app") or {}).get("slug") or "")
            trusted = app_slug == "github-actions" or (name == "CodeQL" and app_slug == "github-advanced-security")
            ok = status == "COMPLETED" and conclusion == "SUCCESS" and trusted
            summaries[key] = {
                "name": name,
                "status": "PASS" if ok else ("FAIL" if status == "COMPLETED" else "PENDING"),
                "conclusion": conclusion or None,
                "source": app_slug or None,
                "url": run.get("html_url") or run.get("details_url"),
            }
            if not ok:
                pending.append(name)
        if not pending:
            return {
                "schemaVersion": 1,
                "repo": repo,
                "sha": sha,
                "status": "PASS",
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "checks": summaries,
                "codeqlUrl": summaries["codeql"]["url"],
                "codeforgeUrl": summaries["codeforge"]["url"],
            }
        failed = [item for item in summaries.values() if item["status"] == "FAIL"]
        if failed:
            return {
                "schemaVersion": 1,
                "repo": repo,
                "sha": sha,
                "status": "FAIL",
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "checks": summaries,
            }
        if time.time() >= deadline:
            return {
                "schemaVersion": 1,
                "repo": repo,
                "sha": sha,
                "status": "FAIL",
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "checks": summaries,
                "error": "Timed out waiting for required exact-commit checks",
            }
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--interval", type=int, default=20)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.stderr.write("GITHUB_TOKEN or GH_TOKEN is required\n")
        return 2
    report = collect(args.repo, args.sha, token, args.timeout, args.interval)
    output = __import__("pathlib").Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({key: report.get(key) for key in ("status", "sha", "error")}, indent=2) + "\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
