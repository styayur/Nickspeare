#!/usr/bin/env python3
"""Create and verify the installable extension ZIP from the built runtime directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "dist" / "extension"
VERSION = "0.1.0-alpha.1"
ZIP_NAME = f"nickspeare-extension-chromium-v{VERSION}.zip"
FORBIDDEN_PARTS = {".git", "node_modules", "tests", "test", "coverage", "__pycache__", ".cache"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_inside(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(parent.resolve())
    except ValueError as error:
        raise RuntimeError(f"Refusing to operate outside {parent}: {resolved}") from error
    return resolved


def validate_entries(names: list[str], manifest: dict) -> list[str]:
    problems = []
    seen = set()
    for name in names:
        pure = PurePosixPath(name)
        if name in seen:
            problems.append(f"duplicate entry: {name}")
        seen.add(name)
        if pure.is_absolute() or ".." in pure.parts or name.startswith("/"):
            problems.append(f"unsafe path: {name}")
        if any(part.casefold() in FORBIDDEN_PARTS for part in pure.parts):
            problems.append(f"forbidden path: {name}")
    required = {
        "manifest.json",
        "popup/popup.html",
        "popup/popup.js",
        "popup/popup.css",
        "background/service-worker.js",
        "content/username-detector.js",
        "core/engine.js",
        "core/atlas.json",
        "licenses/LICENSE",
        "licenses/DATA_SOURCES.md",
        "SOURCE.md",
    }
    missing = sorted(required - seen)
    if missing:
        problems.append(f"missing runtime files: {', '.join(missing)}")
    for icon in (manifest.get("icons") or {}).values():
        if icon not in seen:
            problems.append(f"missing manifest icon: {icon}")
    return problems


def package(root: Path, output_dir: Path, extract_to: Path, release: bool, expected_commit: str) -> dict:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Built extension manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != "0.1.0" or manifest.get("version_name") != VERSION:
        raise RuntimeError("Unexpected extension version")
    provenance_path = root / "BUILD_PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8")) if provenance_path.is_file() else {}
    if release:
        if provenance.get("dirty"):
            raise RuntimeError("Release packaging refuses a dirty build")
        if expected_commit and provenance.get("commit") != expected_commit:
            raise RuntimeError("Build provenance commit does not match the requested release commit")
    output_dir.mkdir(parents=True, exist_ok=True)
    extract_to = safe_inside(extract_to, output_dir)
    if extract_to.exists():
        shutil.rmtree(extract_to)
    archive = output_dir / ZIP_NAME
    temporary = output_dir / f".{ZIP_NAME}.tmp"
    if temporary.exists():
        temporary.unlink()
    files = sorted(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in files:
            handle.write(path, path.relative_to(root).as_posix())
    temporary.replace(archive)

    with zipfile.ZipFile(archive) as handle:
        names = handle.namelist()
        problems = validate_entries(names, manifest)
        if problems:
            raise RuntimeError("; ".join(problems))
        extract_to.mkdir(parents=True, exist_ok=True)
        for name in names:
            target = safe_inside(extract_to / name, extract_to)
            target.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(name) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)

    source_hashes = {path.relative_to(root).as_posix(): sha256(path) for path in files}
    extracted_hashes = {path.relative_to(extract_to).as_posix(): sha256(path) for path in extract_to.rglob("*") if path.is_file()}
    if source_hashes != extracted_hashes:
        raise RuntimeError("Extracted ZIP does not match the built runtime byte-for-byte")

    report = {
        "schemaVersion": 1,
        "project": "Nickspeare",
        "component": "browser-extension",
        "version": VERSION,
        "manifestVersion": manifest["version"],
        "status": "PASS",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "archive": str(archive.relative_to(ROOT)).replace("\\", "/"),
        "archiveBytes": archive.stat().st_size,
        "sha256": sha256(archive),
        "entries": len(names),
        "extractedRoot": str(extract_to.relative_to(ROOT)).replace("\\", "/"),
        "manifestRoot": "manifest.json",
        "licensesIncluded": True,
        "provenance": provenance,
        "checks": {
            "structure": "PASS",
            "pathSafety": "PASS",
            "manifestResources": "PASS",
            "byteForByteExtraction": "PASS",
            "forbiddenFiles": "PASS",
        },
        "limitations": "This verifies archive structure and byte identity. Browser loading is separately tested from the extracted directory.",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--extract-to", type=Path, default=ROOT / "artifacts" / "extension-unpacked")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "extension-package.json")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--expected-commit", default="")
    args = parser.parse_args()
    try:
        report = package(args.root.resolve(), args.output_dir.resolve(), args.extract_to.resolve(), args.release, args.expected_commit)
        exit_code = 0
    except Exception as error:  # noqa: BLE001 - preserve machine-readable failure
        report = {
            "schemaVersion": 1,
            "project": "Nickspeare",
            "component": "browser-extension",
            "version": VERSION,
            "status": "FAIL",
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": f"{type(error).__name__}: {error}",
        }
        exit_code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
