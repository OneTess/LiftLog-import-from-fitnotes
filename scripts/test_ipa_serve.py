#!/usr/bin/env python3
"""Drive the shipped HTTP serve helper: GET the printed IPA URL twice."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ipa_pack import pack_app_to_ipa  # noqa: E402
from ipa_serve import livecontainer_install_url, make_server  # noqa: E402


class TestServeIpa(unittest.TestCase):
    def test_curl_printed_url_returns_ipa_bytes_twice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            app = td / "LiftLog.app"
            app.mkdir()
            (app / "Info.plist").write_bytes(b"plist")
            (app / "LiftLog").write_bytes(b"\xcf\xfa\xed\xfe")
            ipa = td / "LiftLog.ipa"
            pack_app_to_ipa(app, ipa)
            expected = ipa.read_bytes()
            self.assertTrue(expected.startswith(b"PK"))

            httpd, url, lc_url = make_server(
                ipa, bind="127.0.0.1", port=0, advertise_host="127.0.0.1"
            )
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertTrue(url.startswith("http://127.0.0.1:"))
                self.assertTrue(url.endswith("/LiftLog.ipa"))
                self.assertEqual(lc_url, livecontainer_install_url(url))
                self.assertTrue(lc_url.startswith("livecontainer://install?url="))

                for _ in range(2):
                    proc = subprocess.run(
                        ["curl", "-fsS", "-D", "-", "-o", str(td / "got.ipa"), url],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.assertIn("200", proc.stdout.splitlines()[0])
                    self.assertIn("Content-Length:", proc.stdout)
                    got = (td / "got.ipa").read_bytes()
                    self.assertEqual(got[:2], b"PK")
                    self.assertEqual(got, expected)
                    self.assertGreater(len(got), 0)
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
