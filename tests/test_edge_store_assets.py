import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store" / "edge"


def png_header(path: Path) -> tuple[int, int, int, int]:
    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise AssertionError(f"Not a PNG: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR" or length < 13:
            raise AssertionError(f"Missing PNG IHDR: {path}")
        width, height, bit_depth, color_type, _compression, _filter, _interlace = struct.unpack(
            ">IIBBBBB", handle.read(13)
        )
        return width, height, bit_depth, color_type


class EdgeStoreAssetTests(unittest.TestCase):
    def test_listing_metadata_and_versions_are_consistent(self):
        submission = json.loads((STORE / "submission.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(submission["version"], manifest["version_name"])
        self.assertEqual(submission["manifestVersion"], manifest["version"])
        self.assertEqual(submission["languages"], ["en-US", "zh-CN"])
        self.assertEqual(submission["permissions"], manifest["permissions"])
        self.assertEqual(submission["hostPermissions"], [])
        self.assertEqual(submission["optionalHostPermissions"], [])

    def test_listing_descriptions_meet_store_length(self):
        for name in ("listing.en-US.md", "listing.zh-CN.md"):
            text = (STORE / name).read_text(encoding="utf-8")
            self.assertGreaterEqual(len(text), 250, name)
            self.assertLessEqual(len(text), 10000, name)
            self.assertIn("privacy-policy.html", text)

    def test_icon_and_screenshots_have_required_dimensions(self):
        self.assertEqual(png_header(STORE / "assets" / "store-icon-300.png")[:2], (300, 300))
        for name in ("01-generate.png", "02-shape.png", "03-fill-field.png"):
            path = STORE / "screenshots" / name
            width, height, bit_depth, color_type = png_header(path)
            self.assertEqual((width, height), (1280, 800), name)
            self.assertEqual((bit_depth, color_type), (8, 2), name)

    def test_privacy_and_permission_materials_stay_factual(self):
        privacy = (ROOT / "docs" / "privacy-policy.html").read_text(encoding="utf-8").lower()
        for phrase in (
            "chrome.storage.local",
            "passwords",
            "cookies",
            "browsing history",
            "does not contact",
            "agpl-3.0-or-later",
            "cc by-nc 3.0",
        ):
            self.assertIn(phrase, privacy)
        permissions = (STORE / "permission-justifications.md").read_text(encoding="utf-8").lower()
        for permission in ("activetab", "scripting", "storage"):
            self.assertIn(permission, permissions)


if __name__ == "__main__":
    unittest.main()
