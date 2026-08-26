#!/usr/bin/env python3
"""Read the LiveContainer upstream pin and refuse a build that is older than it.

Build scripts must not git fetch or pull. Moving to a newer LiftLog tag is an
explicit operator edit of scripts/livecontainer-pin plus a checkout.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def pin_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "scripts" / "livecontainer-pin"


def read_pin(path: Optional[Path] = None) -> Dict[str, str]:
    path = path or pin_path()
    data: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid pin line in {path}: {raw!r}")
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    if "tag" not in data or "sha" not in data:
        raise ValueError(f"pin file {path} must set tag= and sha=")
    return data


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def assert_pinned(root: Optional[Path] = None, allow_unpinned: bool = False) -> Tuple[str, str, str]:
    """Return (tag, pin_sha, head). Require pin SHA to be HEAD or an ancestor of HEAD."""
    root = root or repo_root()
    pin = read_pin(pin_path(root))
    tag = pin["tag"]
    pin_sha = git(root, "rev-parse", pin["sha"])
    head = git(root, "rev-parse", "HEAD")
    if pin_sha == head:
        return tag, pin_sha, head
    check = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", pin_sha, "HEAD"],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        return tag, pin_sha, head
    msg = (
        f"HEAD {head} is not tag {tag} ({pin_sha}) or a descendant of it. "
        "This tree is frozen so new LiftLog releases are not picked up. "
        "Checkout the pin tag, or edit scripts/livecontainer-pin after an explicit upgrade, "
        "or set ALLOW_UNPINNED=1."
    )
    if allow_unpinned:
        print(f"ipa_pin: WARNING {msg}", file=sys.stderr)
        return tag, pin_sha, head
    raise SystemExit(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the LiveContainer LiftLog pin")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--allow-unpinned",
        action="store_true",
        help="warn instead of failing when HEAD is not a descendant of the pin",
    )
    args = parser.parse_args()
    tag, pin_sha, head = assert_pinned(root=args.root, allow_unpinned=args.allow_unpinned)
    print(f"pin tag={tag} sha={pin_sha} HEAD={head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
