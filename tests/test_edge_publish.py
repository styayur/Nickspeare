import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import edge_publish

PRODUCT_ID = "11111111-1111-4111-8111-111111111111"
CLIENT_ID = "22222222-2222-4222-8222-222222222222"
TAG = "extension-v0.1.0-alpha.2"
VERSION = "0.1.0-alpha.2"
MANIFEST_VERSION = "0.1.1"
PRIVACY_URL = "https://styayur.github.io/Nickspeare/privacy-policy.html"


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, data, timeout):
        self.calls.append((method, url, headers, data))
        if not self.responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(status, payload=None, location=None, headers=None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    response_headers = dict(headers or {})
    if location:
        response_headers["Location"] = location
    return edge_publish.HttpResponse(status, response_headers, body)


def publisher(transport):
    return edge_publish.EdgePublisher(
        PRODUCT_ID,
        CLIENT_ID,
        "secret-api-key",
        transport=transport,
        sleep=lambda _: None,
        timeout=10,
    )


class EdgePublishTests(unittest.TestCase):
    def test_operation_id_parsing(self):
        self.assertEqual(
            edge_publish.operation_id_from_location(
                "https://api.example/v1/operations/abc-123?x=1"
            ),
            "abc-123",
        )
        with self.assertRaises(edge_publish.EdgePublishError):
            edge_publish.operation_id_from_location("")

    def test_product_and_client_ids_must_be_guids(self):
        with self.assertRaises(edge_publish.EdgePublishError):
            edge_publish.EdgePublisher("product", CLIENT_ID, "key")
        with self.assertRaises(edge_publish.EdgePublishError):
            edge_publish.EdgePublisher(PRODUCT_ID, "client", "key")
        with self.assertRaises(edge_publish.EdgePublishError):
            edge_publish.EdgePublisher(PRODUCT_ID, CLIENT_ID, " ")

    def test_upload_and_publish_record_submitted_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"zip-package")
            transport = FakeTransport(
                [
                    response(
                        202,
                        location=(
                            "https://api.example/v1/products/"
                            f"{PRODUCT_ID}/submissions/draft/package/operations/upload-op"
                        ),
                    ),
                    response(200, {"status": "Succeeded", "message": "Package accepted"}),
                    response(
                        202,
                        location=(
                            "https://api.example/v1/products/"
                            f"{PRODUCT_ID}/submissions/operations/publish-op"
                        ),
                    ),
                    response(
                        200,
                        {
                            "status": "Succeeded",
                            "message": "Successfully created submission with ID sub-123",
                        },
                    ),
                ]
            )
            client = publisher(transport)
            upload_id, upload = client.upload(package)
            publish_id, publish = client.publish("review notes")
        self.assertEqual(upload_id, "upload-op")
        self.assertEqual(upload["status"], "Succeeded")
        self.assertEqual(publish_id, "publish-op")
        self.assertEqual(publish["status"], "Succeeded")
        self.assertEqual(len(transport.calls), 4)
        self.assertEqual(transport.calls[0][0], "POST")
        self.assertEqual(transport.calls[0][2]["Authorization"], "ApiKey secret-api-key")
        self.assertEqual(transport.calls[0][2]["X-ClientID"], CLIENT_ID)
        self.assertEqual(transport.calls[0][2]["Content-Type"], "application/zip")
        self.assertEqual(transport.calls[2][0], "POST")
        self.assertEqual(
            json.loads(transport.calls[2][3].decode("utf-8")),
            {"notes": "review notes"},
        )

    def test_transient_response_is_retried(self):
        transport = FakeTransport(
            [
                response(503, {"message": "temporary"}, headers={"Retry-After": "1"}),
                response(
                    202,
                    location=(
                        "https://api.example/v1/products/"
                        f"{PRODUCT_ID}/submissions/draft/package/operations/upload-op"
                    ),
                ),
                response(200, {"status": "Succeeded"}),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"zip")
            operation, result = publisher(transport).upload(package)
        self.assertEqual(operation, "upload-op")
        self.assertEqual(result["status"], "Succeeded")
        self.assertEqual(len(transport.calls), 3)

    def test_authorization_failure_is_not_retried(self):
        transport = FakeTransport([response(401, {"message": "invalid API key"})])
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"zip")
            with self.assertRaises(edge_publish.EdgePublishError):
                publisher(transport).upload(package)
        self.assertEqual(len(transport.calls), 1)

    def test_failed_poll_raises_without_claiming_publication(self):
        transport = FakeTransport(
            [
                response(
                    202,
                    location=(
                        "https://api.example/v1/products/"
                        f"{PRODUCT_ID}/submissions/draft/package/operations/upload-op"
                    ),
                ),
                response(
                    200,
                    {
                        "status": "Failed",
                        "message": "invalid package",
                        "errorCode": "BadZip",
                        "errors": ["bad"],
                    },
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"zip")
            with self.assertRaises(edge_publish.EdgePublishError):
                publisher(transport).upload(package)

    def test_store_listing_validation_passes_current_metadata(self):
        submission = json.loads(
            (ROOT / "store/edge/submission.json").read_text(encoding="utf-8")
        )
        result = edge_publish.store_listing_status(ROOT, submission)
        self.assertEqual(result, {"status": "PASS", "blockers": []})

    def test_store_listing_validation_rejects_non_https_privacy_url(self):
        submission = json.loads(
            (ROOT / "store/edge/submission.json").read_text(encoding="utf-8")
        )
        invalid = copy.deepcopy(submission)
        invalid["privacyPolicyUrl"] = "http://example.invalid/privacy"
        result = edge_publish.store_listing_status(ROOT, invalid)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("HTTPS" in blocker for blocker in result["blockers"]))

    def test_evidence_binding_matches_package_manifest_and_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"package")
            args = SimpleNamespace(
                root=ROOT,
                package=package,
                version=VERSION,
                github_release_tag=TAG,
                privacy_policy_url=PRIVACY_URL,
            )
            acceptance = {
                "version": VERSION,
                "manifestVersion": MANIFEST_VERSION,
                "release": {
                    "tag": TAG,
                    "archiveSha256": hashlib.sha256(b"package").hexdigest(),
                },
            }
            submission = json.loads(
                (ROOT / "store/edge/submission.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                edge_publish.validate_evidence(args, acceptance, submission),
                MANIFEST_VERSION,
            )
            acceptance["release"]["archiveSha256"] = "0" * 64
            with self.assertRaises(edge_publish.EdgePublishError):
                edge_publish.validate_evidence(args, acceptance, submission)

    def test_workflow_is_environment_protected_and_never_clobbers_release_assets(self):
        workflow = (ROOT / ".github/workflows/edge-publish.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:", workflow)
        self.assertIn("Release browser extension", workflow)
        self.assertIn("environment: edge-production", workflow)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", workflow)
        self.assertIn("actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", workflow)
        self.assertIn("edge-publish-intent.json", workflow)
        self.assertIn("edge-store-acceptance.json", workflow)
        self.assertIn("EDGE_API_KEY", workflow)
        self.assertIn("gh release upload", workflow)
        self.assertNotIn("--clobber", workflow)
        self.assertNotIn("--admin", workflow)
        self.assertNotIn("force-merge", workflow)
        self.assertIn("SUBMITTED", workflow)
        self.assertIn("does not mean Microsoft has approved or published", workflow)

    def test_submitted_report_never_claims_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "extension.zip"
            package.write_bytes(b"package")
            args = SimpleNamespace(
                root=ROOT,
                package=package,
                version=VERSION,
                github_release_tag=TAG,
                github_release_url="https://github.com/styayur/Nickspeare/releases/tag/" + TAG,
                privacy_policy_url=PRIVACY_URL,
                product_id=PRODUCT_ID,
            )
            acceptance = {
                "version": VERSION,
                "manifestVersion": MANIFEST_VERSION,
                "commit": "a" * 40,
                "releaseReady": True,
                "compatibility": {
                    "chromium": {"status": "PASS"},
                    "msedge": {"status": "PASS"},
                },
                "release": {"package": {"status": "PASS", "checks": {}}},
            }
            submission = {
                "officialStatus": "SUBMITTED",
                "submissionId": "sub-123",
                "operationId": "publish-op",
                "publicListingUrl": None,
            }
            report = edge_publish.build_report(
                args,
                MANIFEST_VERSION,
                hashlib.sha256(b"package").hexdigest(),
                acceptance,
                submission,
            )
        self.assertEqual(report["officialStoreStatus"], "SUBMITTED")
        self.assertIsNone(report["publicListingUrl"])
        self.assertNotEqual(report["officialStoreStatus"], "PUBLISHED")
        self.assertFalse(report["blockers"])


if __name__ == "__main__":
    unittest.main()
