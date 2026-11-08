import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_extension
import generate_extension_acceptance
import package_extension


class ExtensionReleaseTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "licenses").mkdir()
        manifest = {
            "manifest_version": 3,
            "name": "Fixture",
            "version": "0.1.0",
            "version_name": "0.1.0-alpha.1",
            "permissions": ["activeTab", "scripting", "storage"],
            "action": {"default_popup": "popup.html"},
            "background": {"service_worker": "service-worker.js"},
            "content_security_policy": {"extension_pages": "script-src 'self'; object-src 'self';"},
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "popup.html").write_text("<script src=\"popup.js\"></script>", encoding="utf-8")
        (root / "popup.js").write_text(
            "chrome.storage.local; const SENSITIVE_HINTS='password email';"
            "if (sender.id !== chrome.runtime.id) throw Error('FIELD_NOT_EMPTY');"
            "const key='nickspeare.preferences.v1'; replaceExisting;",
            encoding="utf-8",
        )
        (root / "service-worker.js").write_text("chrome.runtime.id;\n", encoding="utf-8")
        (root / "licenses" / "LICENSE").write_text("AGPL-3.0-or-later\n", encoding="utf-8")
        (root / "SOURCE.md").write_text("https://github.com/styayur/Nickspeare\n", encoding="utf-8")
        (root / "licenses" / "DATA_SOURCES.md").write_text(
            "CC BY-NC 3.0 noncommercial attribution\n", encoding="utf-8"
        )
        return root

    def test_audit_passes_minimal_fixture_and_detects_host_permission(self):
        root = self.fixture()
        self.assertEqual(audit_extension.audit(root)["status"], "PASS")
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["host_permissions"] = ["https://example.com/*"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report = audit_extension.audit(root)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("noHostPermissions", report["blockers"][0])

    def test_zip_entry_validation_rejects_traversal_and_missing_runtime_files(self):
        manifest = {"icons": {"16": "icon.png"}}
        problems = package_extension.validate_entries(["manifest.json", "../private.txt", "icon.png"], manifest)
        self.assertTrue(any("unsafe path" in problem for problem in problems))
        self.assertTrue(any("missing runtime files" in problem for problem in problems))

    def test_coverage_and_node_logs_are_parsed_with_thresholds(self):
        node = "ℹ tests 10\nℹ pass 10\nℹ fail 0\n"
        self.assertEqual(generate_extension_acceptance.parse_node(node)["status"], "PASS")
        coverage = "all files | 85.00 | 80.00 | 90.00 |\n"
        self.assertEqual(generate_extension_acceptance.parse_coverage(coverage)["status"], "PASS")
        below = "all files | 50.00 | 50.00 | 50.00 |\n"
        self.assertEqual(generate_extension_acceptance.parse_coverage(below)["status"], "FAIL")

    def test_release_workflow_is_tag_scoped_prerelease_and_non_overwriting(self):
        workflow = (ROOT / ".github" / "workflows" / "extension-release.yml").read_text(encoding="utf-8")
        self.assertIn("tags: ['extension-v*.*.*']", workflow)
        self.assertIn("prerelease: true", workflow)
        self.assertIn("make_latest: false", workflow)
        self.assertIn("Refuse to overwrite an existing release", workflow)
        self.assertIn("collect_exact_checks.py", workflow)
        self.assertIn("extension-acceptance.json", workflow)
        self.assertNotIn("permissions: write-all", workflow)


if __name__ == "__main__":
    unittest.main()
