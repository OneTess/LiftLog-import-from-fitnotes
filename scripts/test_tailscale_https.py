#!/usr/bin/env python3
"""Tests for pointing Tailscale Serve / at this repo's IPA HTTP port."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "tailscale_https_mod", Path(__file__).resolve().parent / "tailscale-https.py"
)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
sys.modules["tailscale_https_mod"] = _MOD

from tailscale_https_mod import (  # noqa: E402
    ROOT_PATH,
    ServeConflict,
    liftlog_handler_ready,
    merge_liftlog_handler,
    public_base_url,
    public_ipa_url,
)

HOST = "macbook-air.tailb6dcda.ts.net"
LIFTLOG = "http://127.0.0.1:15009"


class MergeTests(unittest.TestCase):
    def test_empty_config_owns_root(self) -> None:
        merged = merge_liftlog_handler({}, HOST, 15009)
        handlers = merged["Web"][f"{HOST}:443"]["Handlers"]
        self.assertEqual(handlers[ROOT_PATH], {"Proxy": LIFTLOG})
        self.assertEqual(merged["TCP"]["443"], {"HTTPS": True})
        self.assertTrue(liftlog_handler_ready(merged, HOST, 15009))

    def test_replaces_leftover_root_handler(self) -> None:
        cfg = {
            "TCP": {"443": {"HTTPS": True}},
            "Web": {
                f"{HOST}:443": {
                    "Handlers": {"/": {"Proxy": "http://127.0.0.1:15007"}}
                },
            },
        }
        merged = merge_liftlog_handler(cfg, HOST, 15009)
        handlers = merged["Web"][f"{HOST}:443"]["Handlers"]
        self.assertEqual(handlers["/"], {"Proxy": LIFTLOG})

    def test_conflict_on_tcp_443(self) -> None:
        cfg = {"TCP": {"443": {"TCPForward": "127.0.0.1:22"}}}
        with self.assertRaises(ServeConflict):
            merge_liftlog_handler(cfg, HOST, 15009)

    def test_idempotent_when_already_set(self) -> None:
        cfg = merge_liftlog_handler({}, HOST, 15009)
        again = merge_liftlog_handler(cfg, HOST, 15009)
        self.assertEqual(again["Web"][f"{HOST}:443"]["Handlers"]["/"], {"Proxy": LIFTLOG})
        self.assertTrue(liftlog_handler_ready(again, HOST, 15009))

    def test_preserves_unrelated_keys(self) -> None:
        cfg = {"AllowFunnel": {f"{HOST}:443": True}, "TCP": {}, "Web": {}}
        merged = merge_liftlog_handler(cfg, HOST, 15009)
        self.assertEqual(merged["AllowFunnel"], {f"{HOST}:443": True})

    def test_public_urls(self) -> None:
        self.assertEqual(public_base_url(HOST), f"https://{HOST}")
        self.assertEqual(
            public_ipa_url(HOST, "LiftLog.ipa"),
            f"https://{HOST}/LiftLog.ipa",
        )


if __name__ == "__main__":
    unittest.main()
