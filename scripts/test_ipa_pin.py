#!/usr/bin/env python3
"""Drive assert_pinned against a temp git repo using the shipped pin parser."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ipa_pin import assert_pinned, read_pin  # noqa: E402


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


class TestIpaPin(unittest.TestCase):
    def test_read_pin_file(self) -> None:
        root = Path(__file__).resolve().parent.parent
        pin = read_pin(root / "scripts" / "livecontainer-pin")
        self.assertEqual(pin["tag"], "4.22.0")
        self.assertTrue(len(pin["sha"]) >= 7)

    def test_assert_pinned_allows_descendant_not_ancestor_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "-C", str(repo), "config", "user.email", "t@t"])
            subprocess.check_call(["git", "-C", str(repo), "config", "user.name", "t"])
            (repo / "a").write_text("a")
            subprocess.check_call(["git", "-C", str(repo), "add", "a"])
            subprocess.check_call(["git", "-C", str(repo), "commit", "-m", "a"], stdout=subprocess.DEVNULL)
            sha = git(repo, "rev-parse", "HEAD")
            scripts = repo / "scripts"
            scripts.mkdir()
            (scripts / "livecontainer-pin").write_text(f"tag=4.22.0\nsha={sha}\n")
            (repo / "b").write_text("b")
            subprocess.check_call(["git", "-C", str(repo), "add", "b"])
            subprocess.check_call(["git", "-C", str(repo), "commit", "-m", "b"], stdout=subprocess.DEVNULL)
            tag, pin_sha, head = assert_pinned(root=repo)
            self.assertEqual(tag, "4.22.0")
            self.assertEqual(pin_sha, sha)
            self.assertNotEqual(head, sha)

            # Reset to an unrelated history so the pin is not an ancestor.
            subprocess.check_call(["git", "-C", str(repo), "checkout", "--orphan", "other"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.check_call(["git", "-C", str(repo), "rm", "-rf", "."], stdout=subprocess.DEVNULL)
            (repo / "c").write_text("c")
            scripts.mkdir(exist_ok=True)
            (scripts / "livecontainer-pin").write_text(f"tag=4.22.0\nsha={sha}\n")
            subprocess.check_call(["git", "-C", str(repo), "add", "c", "scripts/livecontainer-pin"])
            subprocess.check_call(["git", "-C", str(repo), "commit", "-m", "c"], stdout=subprocess.DEVNULL)
            with self.assertRaises(SystemExit):
                assert_pinned(root=repo)


if __name__ == "__main__":
    unittest.main()
