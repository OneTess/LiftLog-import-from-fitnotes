#!/usr/bin/env python3
"""Drive pack_app_to_ipa (the shipped packer) with a dummy Payload/.app."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ipa_pack import pack_app_to_ipa  # noqa: E402


class TestPackAppToIpa(unittest.TestCase):
    def test_pack_writes_payload_app_zip(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            app = td / "LiftLog.app"
            app.mkdir()
            (app / "Info.plist").write_bytes(b"<?xml version='1.0'?><plist></plist>")
            (app / "LiftLog").write_bytes(b"\xcf\xfa\xed\xfe dummy-mach-o")
            nested = app / "Frameworks"
            nested.mkdir()
            (nested / "Foo.framework").write_bytes(b"fw")
            ipa = td / "LiftLog.ipa"
            out = pack_app_to_ipa(app, ipa)
            self.assertEqual(out, ipa)
            self.assertTrue(ipa.is_file())
            self.assertEqual(ipa.read_bytes()[:2], b"PK")

            with zipfile.ZipFile(ipa) as zf:
                names = zf.namelist()
            self.assertIn("Payload/", names)
            self.assertTrue(any(n.startswith("Payload/LiftLog.app/") for n in names))
            self.assertIn("Payload/LiftLog.app/Info.plist", names)
            self.assertIn("Payload/LiftLog.app/LiftLog", names)

            listing = subprocess.check_output(["unzip", "-l", str(ipa)], text=True)
            self.assertIn("Payload/", listing)
            self.assertIn("LiftLog.app", listing)
            self.assertIn("Info.plist", listing)


if __name__ == "__main__":
    unittest.main()
