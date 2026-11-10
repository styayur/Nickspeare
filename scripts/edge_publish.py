#!/usr/bin/env python3
"""Upload and submit an existing Microsoft Edge Add-ons product update (API v1.1)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Set, Tuple

DEFAULT_ENDPOINT = "https://api.addons.microsoftedge.microsoft.com"
TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}
SUCCESS_STATUS = "Succeeded"
IN_PROGRESS_STATUS = "InProgress"
FAILED_STATUS = "Failed"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
SUBMISSION_ID_RE = re.compile(
    r"(?:submission(?:\s+with)?\s+id|submissionId)\s*[:=]?\s*([0-9a-zA-Z-]+)",
    re.I,
)


class EdgePublishError(RuntimeError):
    pass


@dataclass
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> dict:
        if not self.body:
            return {}
        try:
            value = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EdgePublishError("Edge Add-ons API returned invalid JSON") from error
        if not isinstance(value, dict):
            raise EdgePublishError("Edge Add-ons API returned a non-object JSON payload")
        return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def header(response: HttpResponse, name: str) -> str:
    lower = name.lower()
    for key, value in response.headers.items():
        if key.lower() == lower:
            return str(value)
    return ""


def operation_id_from_location(location: str) -> str:
    if not location:
        raise EdgePublishError("Edge API response omitted the operation Location header")
    parsed = urllib.parse.urlparse(location)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise EdgePublishError(f"Could not parse operation ID from Location: {location}")
    return parts[-1]


def urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    data: Optional[bytes],
    timeout: float,
) -> HttpResponse:
    request = urllib.request.Request(url, data=data, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResponse(response.status, dict(response.headers.items()), response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(error.code, dict(error.headers.items()), error.read())
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise EdgePublishError(
            f"Network failure calling Edge Add-ons API: {type(error).__name__}: {error}"
        ) from error


class EdgePublisher:
    def __init__(
        self,
        product_id: str,
        client_id: str,
        api_key: str,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        transport: Callable[..., HttpResponse] = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        timeout: float = 900,
        poll_interval: float = 10,
        max_retries: int = 5,
        request_timeout: float = 60,
    ):
        for label, value in (("product_id", product_id), ("client_id", client_id)):
            if not GUID_RE.fullmatch(value or ""):
                raise EdgePublishError(f"{label} must be a Microsoft product/client GUID")
        if not api_key.strip():
            raise EdgePublishError("Edge API key is empty")
        self.product_id = product_id
        self.client_id = client_id
        self.api_key = api_key.strip()
        self.endpoint = endpoint.rstrip("/")
        self.transport = transport
        self.sleep = sleep
        self.clock = clock
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_retries = max(1, max_retries)
        self.request_timeout = request_timeout

    def _headers(self, content_type: Optional[str] = None) -> dict:
        headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "X-ClientID": self.client_id,
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _retry_delay(self, attempt: int, response: Optional[HttpResponse]) -> float:
        if response is not None:
            raw = header(response, "Retry-After")
            if raw:
                try:
                    return min(60.0, max(1.0, float(raw)))
                except ValueError:
                    pass
        return min(30.0, 2.0 ** attempt)

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: Optional[bytes] = None,
        content_type: Optional[str] = None,
        expected: Set[int],
    ) -> HttpResponse:
        url = f"{self.endpoint}{path}"
        last_error: Optional[EdgePublishError] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.transport(
                    method, url, self._headers(content_type), data, self.request_timeout
                )
            except EdgePublishError as error:
                last_error = error
                if attempt >= self.max_retries:
                    raise
                self.sleep(self._retry_delay(attempt, None))
                continue
            if response.status in expected:
                return response
            body = response.body.decode("utf-8", errors="replace")[:2000]
            if response.status in TRANSIENT_STATUS and attempt < self.max_retries:
                self.sleep(self._retry_delay(attempt, response))
                continue
            raise EdgePublishError(
                f"Edge Add-ons API {method} {path} returned {response.status}: {body}"
            )
        raise last_error or EdgePublishError("Edge Add-ons API request failed")

    def _poll(self, path: str, operation_id: str) -> dict:
        deadline = self.clock() + self.timeout
        while True:
            response = self._request("GET", f"{path}/{operation_id}", expected={200})
            payload = response.json()
            status = str(payload.get("status") or "")
            if status == SUCCESS_STATUS:
                return payload
            if status == FAILED_STATUS:
                raise EdgePublishError(
                    f"Edge operation {operation_id} failed: "
                    f"{payload.get('message') or 'no message'}; "
                    f"errorCode={payload.get('errorCode')}; errors={payload.get('errors')}"
                )
            if status != IN_PROGRESS_STATUS:
                raise EdgePublishError(
                    f"Edge operation {operation_id} returned unexpected status: "
                    f"{status or 'missing'}"
                )
            if self.clock() >= deadline:
                raise EdgePublishError(f"Timed out waiting for Edge operation {operation_id}")
            self.sleep(self.poll_interval)

    def upload(self, package: Path) -> Tuple[str, dict]:
        if not package.is_file():
            raise EdgePublishError(f"Package does not exist: {package}")
        path = f"/v1/products/{self.product_id}/submissions/draft/package"
        response = self._request(
            "POST",
            path,
            data=package.read_bytes(),
            content_type="application/zip",
            expected={202},
        )
        operation_id = operation_id_from_location(header(response, "Location"))
        payload = self._poll(f"{path}/operations", operation_id)
        return operation_id, payload

    def publish(self, notes: str) -> Tuple[str, dict]:
        notes = notes.strip()
        if not notes:
            raise EdgePublishError("Certification notes must not be empty")
        path = f"/v1/products/{self.product_id}/submissions"
        body = json.dumps({"notes": notes}, ensure_ascii=False).encode("utf-8")
        response = self._request(
            "POST",
            path,
            data=body,
            content_type="application/json",
            expected={202},
        )
        operation_id = operation_id_from_location(header(response, "Location"))
        payload = self._poll(f"{path}/operations", operation_id)
        return operation_id, payload


def png_size(path: Path) -> Tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise EdgePublishError(f"Not a PNG: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        if handle.read(4) != b"IHDR" or length < 13:
            raise EdgePublishError(f"Missing PNG IHDR: {path}")
        width, height = struct.unpack(">II", handle.read(8))
        return width, height


def store_listing_status(root: Path, submission: dict) -> dict:
    blockers = []
    listings = submission.get("listing") or {}
    for language, raw_path in listings.items():
        path = root / str(raw_path)
        if not path.is_file():
            blockers.append(f"missing listing file for {language}: {raw_path}")
            continue
        length = len(path.read_text(encoding="utf-8"))
        if not 250 <= length <= 10000:
            blockers.append(f"listing length outside 250..10000 for {language}: {length}")
    if not listings:
        blockers.append("store listing languages are missing")
    for name, raw_path in (submission.get("documents") or {}).items():
        if not (root / str(raw_path)).is_file():
            blockers.append(f"missing store document {name}: {raw_path}")
    privacy_url = str(submission.get("privacyPolicyUrl") or "")
    if not privacy_url.lower().startswith("https://"):
        blockers.append("privacyPolicyUrl must be an HTTPS URL")
    screenshots = (submission.get("assets") or {}).get("screenshots") or []
    if not 3 <= len(screenshots) <= 6:
        blockers.append("the store listing must contain 3..6 screenshots")
    for raw_path in screenshots:
        image = root / str(raw_path)
        if not image.is_file():
            blockers.append(f"missing screenshot: {raw_path}")
            continue
        try:
            if png_size(image) not in {(1280, 800), (640, 480)}:
                blockers.append(f"screenshot must be 1280x800 or 640x480: {raw_path}")
        except (EdgePublishError, OSError) as error:
            blockers.append(str(error))
    icon_raw = (submission.get("assets") or {}).get("icon") or ""
    icon = root / str(icon_raw)
    if not icon_raw or not icon.is_file():
        blockers.append("store icon is missing")
    else:
        try:
            if png_size(icon) != (300, 300):
                blockers.append("store icon must be 300x300")
        except (EdgePublishError, OSError) as error:
            blockers.append(str(error))
    promo_raw = (submission.get("assets") or {}).get("optionalPromoTile")
    if promo_raw:
        promo = root / str(promo_raw)
        if not promo.is_file():
            blockers.append(f"optional promo tile is listed but missing: {promo_raw}")
        else:
            try:
                if png_size(promo) != (440, 280):
                    blockers.append("optional promo tile must be 440x280")
            except (EdgePublishError, OSError) as error:
                blockers.append(str(error))
    return {"status": "PASS" if not blockers else "FAIL", "blockers": blockers}


def load_notes(path: Path) -> str:
    notes = path.read_text(encoding="utf-8").strip()
    if not notes:
        raise EdgePublishError("Certification notes file is empty")
    return notes


def build_report(
    args,
    manifest_version: str,
    package_sha: str,
    extension_acceptance: dict,
    submission_report: dict,
) -> dict:
    root = Path(args.root).resolve()
    submission = json.loads((root / "store/edge/submission.json").read_text(encoding="utf-8"))
    listing = store_listing_status(root, submission)
    browser = extension_acceptance.get("compatibility") or {}
    browser_ok = all(
        (browser.get(name) or {}).get("status") == "PASS" for name in ("chromium", "msedge")
    )
    release_ready = bool(extension_acceptance.get("releaseReady"))
    blockers = []
    blockers.extend(listing.get("blockers") or [])
    if not browser_ok:
        blockers.append("Chromium and Edge acceptance must both pass")
    if not release_ready:
        blockers.append("GitHub extension acceptance is not release-ready")
    if submission_report.get("officialStatus") != "SUBMITTED":
        blockers.append("Edge submission did not reach SUBMITTED")
    return {
        "schemaVersion": 1,
        "project": "Nickspeare",
        "component": "browser-extension",
        "version": args.version,
        "manifestVersion": manifest_version,
        "githubCommit": extension_acceptance.get("commit"),
        "githubReleaseTag": args.github_release_tag,
        "githubReleaseUrl": args.github_release_url,
        "privacyPolicyUrl": args.privacy_policy_url,
        "productId": args.product_id,
        "package": {
            "file": Path(args.package).name,
            "sha256": package_sha,
            "bytes": Path(args.package).stat().st_size,
        },
        "packageValidation": {
            "status": (extension_acceptance.get("release") or {})
            .get("package", {})
            .get("status", "UNKNOWN"),
            "checks": (extension_acceptance.get("release") or {})
            .get("package", {})
            .get("checks", {}),
        },
        "browserAcceptance": {
            "status": "PASS" if browser_ok else "FAIL",
            "chromium": browser.get("chromium"),
            "msedge": browser.get("msedge"),
        },
        "storeListingCompleteness": listing,
        "submission": submission_report,
        "officialStoreStatus": submission_report.get("officialStatus"),
        "publicListingUrl": submission_report.get("publicListingUrl"),
        "blockers": blockers,
    }


def validate_evidence(args, extension_acceptance: dict, submission: dict) -> str:
    manifest = json.loads(
        (Path(args.root).resolve() / "extension" / "manifest.json").read_text(encoding="utf-8")
    )
    manifest_version = str(extension_acceptance.get("manifestVersion") or "")
    if not manifest_version:
        raise EdgePublishError("Extension acceptance omits manifestVersion")
    if extension_acceptance.get("version") != args.version:
        raise EdgePublishError("Requested version does not match extension acceptance")
    if submission.get("version") != args.version:
        raise EdgePublishError("Requested version does not match store submission metadata")
    if submission.get("manifestVersion") != manifest_version:
        raise EdgePublishError("Manifest version differs between acceptance and store metadata")
    if manifest.get("version") != manifest_version:
        raise EdgePublishError("Manifest version differs between repository and acceptance")
    if manifest.get("version_name") != args.version:
        raise EdgePublishError("Display version differs between repository and requested version")
    release = extension_acceptance.get("release") or {}
    if release.get("tag") != args.github_release_tag:
        raise EdgePublishError("Release tag differs between acceptance and requested tag")
    if release.get("archiveSha256") != sha256_file(args.package):
        raise EdgePublishError("Release acceptance SHA-256 differs from the uploaded package")
    if submission.get("privacyPolicyUrl") != args.privacy_policy_url:
        raise EdgePublishError("Privacy policy URL differs between CLI and store metadata")
    return manifest_version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--privacy-policy-url", required=True)
    parser.add_argument("--notes-file", type=Path, required=True)
    parser.add_argument("--extension-acceptance", type=Path, required=True)
    parser.add_argument("--github-release-tag", required=True)
    parser.add_argument("--github-release-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--max-retries", type=int, default=5)
    args = parser.parse_args()

    package_sha = sha256_file(args.package)
    if package_sha.lower() != args.expected_sha256.lower():
        raise EdgePublishError(
            f"Package SHA-256 mismatch: {package_sha} != {args.expected_sha256}"
        )
    extension_acceptance = json.loads(
        args.extension_acceptance.read_text(encoding="utf-8")
    )
    submission = json.loads(
        (Path(args.root) / "store/edge/submission.json").read_text(encoding="utf-8")
    )
    manifest_version = validate_evidence(args, extension_acceptance, submission)
    listing = store_listing_status(Path(args.root).resolve(), submission)
    if listing["status"] != "PASS":
        raise EdgePublishError(f"Store listing incomplete: {listing['blockers']}")
    api_key = os.environ.get("EDGE_API_KEY")
    if not api_key:
        raise EdgePublishError("EDGE_API_KEY is not configured")
    publisher = EdgePublisher(
        args.product_id,
        args.client_id,
        api_key,
        endpoint=args.endpoint,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        max_retries=args.max_retries,
    )
    upload_operation, upload_result = publisher.upload(args.package)
    publish_operation, publish_result = publisher.publish(load_notes(args.notes_file))
    publish_message = str(publish_result.get("message") or "")
    match = SUBMISSION_ID_RE.search(publish_message)
    submission_report = {
        "uploadOperationId": upload_operation,
        "uploadStatus": upload_result.get("status"),
        "uploadMessage": upload_result.get("message"),
        "operationId": publish_operation,
        "publishStatus": publish_result.get("status"),
        "publishMessage": publish_message,
        "submissionId": match.group(1) if match else None,
        "submittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "officialStatus": "SUBMITTED"
        if publish_result.get("status") == SUCCESS_STATUS
        else "FAILED",
        "certificationStatus": "NOT_YET_KNOWN",
        "publicListingUrl": None,
    }
    report = build_report(
        args,
        manifest_version,
        package_sha,
        extension_acceptance,
        submission_report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    sys.stdout.write(
        json.dumps(
            {
                "officialStoreStatus": report["officialStoreStatus"],
                "submissionId": submission_report["submissionId"],
                "operationId": publish_operation,
                "publicListingUrl": report["publicListingUrl"],
                "blockers": report["blockers"],
            },
            indent=2,
        )
        + "\n"
    )
    return 0 if not report["blockers"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EdgePublishError as error:
        sys.stderr.write(f"Edge publish error: {error}\n")
        raise SystemExit(1)
