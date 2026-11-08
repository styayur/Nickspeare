#!/usr/bin/env python3
"""Render the bilingual extension release notes with final artifact metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=ROOT / ".github" / "extension-release-notes.md")
    parser.add_argument("--acceptance", type=Path, default=ROOT / "artifacts" / "extension-acceptance.json")
    parser.add_argument("--package", type=Path, default=ROOT / "artifacts" / "extension-package.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "release-notes.md")
    args = parser.parse_args()
    acceptance = json.loads(args.acceptance.read_text(encoding="utf-8"))
    package = json.loads(args.package.read_text(encoding="utf-8"))
    replacements = {
        "{{COMMIT}}": str(acceptance.get("commit") or "UNKNOWN"),
        "{{ZIP_SHA256}}": str(package.get("sha256") or "UNKNOWN"),
        "{{ACCEPTANCE_STATUS}}": str(acceptance.get("overallStatus") or "NOT_RUN"),
        "{{QUALITY_SCORE}}": str(acceptance.get("qualityScore") if acceptance.get("qualityScore") is not None else "NOT_RUN"),
        "{{CHROMIUM_VERSION}}": str((acceptance.get("compatibility") or {}).get("chromium", {}).get("version") or "NOT_RUN"),
        "{{EDGE_VERSION}}": str((acceptance.get("compatibility") or {}).get("msedge", {}).get("version") or "NOT_RUN"),
    }
    text = args.template.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(key, value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(json.dumps({"output": str(args.output), "replacements": replacements}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
