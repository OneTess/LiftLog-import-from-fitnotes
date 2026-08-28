#!/usr/bin/env python3
"""MagicDNS HTTPS URL + Tailscale Serve for this repo's LiveContainer IPA.

Talks to the Tailscale app's local API on this Mac. Does not import or invoke
anything from Superapp (or any other repo). Let's Encrypt on ``*.ts.net`` is
Tailscale Serve, not a self-signed cert.

This checkout owns ``https://<magicdns>/`` → ``http://127.0.0.1:<ipa-port>``.
A leftover ``/`` handler from another app on this Mac is replaced.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

GROUP_GLOB = "sameuserproof-*"
CONTAINER_GLOBS = [
    Path.home() / "Library/Group Containers",
]
ROOT_PATH = "/"


class ServeConflict(Exception):
    """Existing Tailscale Serve config would be overwritten incorrectly."""


def find_proof() -> tuple[int, str]:
    matches: list[Path] = []
    for root in CONTAINER_GLOBS:
        if not root.is_dir():
            continue
        matches.extend(root.glob(f"*/{GROUP_GLOB}"))
        matches.extend(root.glob(GROUP_GLOB))
    if not matches:
        raise SystemExit("Tailscale local API proof file not found (is Tailscale running?)")
    proof = max(matches, key=lambda p: p.stat().st_mtime)
    name = proof.name  # sameuserproof-<port>-<token>
    parts = name.split("-", 2)
    if len(parts) != 3:
        raise SystemExit(f"unexpected proof name: {name}")
    return int(parts[1]), parts[2]


def localapi(
    path: str,
    port: int,
    token: str,
    data: Optional[bytes] = None,
    etag: Optional[str] = None,
) -> tuple[int, dict[str, str], bytes]:
    url = f"http://127.0.0.1:{port}/localapi/v0/{path.lstrip('/')}"
    auth = base64.b64encode(b":" + token.encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if etag:
        headers["If-Match"] = etag
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, body
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        raise SystemExit(f"Tailscale local API {e.code} {path}: {err}") from e


def status(port: int, token: str) -> dict:
    _, _, body = localapi("status", port, token)
    return json.loads(body)


def dns_name(st: dict) -> str:
    name = (st.get("Self") or {}).get("DNSName") or ""
    name = name.rstrip(".")
    if not name:
        raise SystemExit("Tailscale DNSName missing — is MagicDNS on?")
    return name


def public_base_url(hostname: str) -> str:
    return f"https://{hostname}"


def public_ipa_url(hostname: str, filename: str) -> str:
    return f"{public_base_url(hostname)}/{filename.lstrip('/')}"


def _tcp_443(tcp: dict[str, Any]) -> Any:
    return tcp.get("443") or tcp.get(443)


def _handlers(web: dict[str, Any], host_key: str) -> dict[str, Any]:
    return dict((web.get(host_key) or {}).get("Handlers") or {})


def merge_liftlog_handler(cfg: dict[str, Any], hostname: str, backend_port: int) -> dict[str, Any]:
    """Return a serve-config that points / at this repo's IPA HTTP port."""
    want_proxy = f"http://127.0.0.1:{backend_port}"
    host_key = f"{hostname}:443"
    out = dict(cfg)
    tcp = dict(out.get("TCP") or {})
    web = dict(out.get("Web") or {})
    tcp_443 = _tcp_443(tcp)
    if tcp_443 and tcp_443 != {"HTTPS": True}:
        raise ServeConflict(f"Tailscale already uses TCP 443 for {tcp_443}; not overwriting")

    handlers = _handlers(web, host_key)
    tcp["443"] = {"HTTPS": True}
    handlers[ROOT_PATH] = {"Proxy": want_proxy}
    web[host_key] = {"Handlers": handlers}
    out["TCP"] = tcp
    out["Web"] = web
    return out


def liftlog_handler_ready(cfg: dict[str, Any], hostname: str, backend_port: int) -> bool:
    want_proxy = f"http://127.0.0.1:{backend_port}"
    host_key = f"{hostname}:443"
    tcp = cfg.get("TCP") or {}
    handlers = _handlers(cfg.get("Web") or {}, host_key)
    current = (handlers.get(ROOT_PATH) or {}).get("Proxy")
    return _tcp_443(tcp) == {"HTTPS": True} and current == want_proxy


def ensure_serve(port: int, token: str, hostname: str, backend_port: int) -> None:
    _, headers, body = localapi("serve-config", port, token)
    etag = headers.get("etag")
    cfg = json.loads(body) if body and body != b"null" else None
    if not isinstance(cfg, dict):
        cfg = {}
    want_proxy = f"http://127.0.0.1:{backend_port}"
    if liftlog_handler_ready(cfg, hostname, backend_port):
        print(
            f"Tailscale Serve already proxies https://{hostname}/ → {want_proxy}",
            file=sys.stderr,
        )
        return
    try:
        merged = merge_liftlog_handler(cfg, hostname, backend_port)
    except ServeConflict as exc:
        raise SystemExit(str(exc)) from exc
    payload = json.dumps(merged).encode()
    localapi("serve-config", port, token, data=payload, etag=etag)
    print(f"Tailscale Serve: https://{hostname}/ → {want_proxy}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        action="store_true",
        help="print https://<magicdns> (no trailing slash)",
    )
    parser.add_argument(
        "--ensure-serve",
        type=int,
        metavar="PORT",
        help="proxy https://<magicdns>/ to 127.0.0.1:PORT",
    )
    args = parser.parse_args()
    if not args.base_url and args.ensure_serve is None:
        parser.error("pass --base-url and/or --ensure-serve PORT")
    api_port, token = find_proof()
    st = status(api_port, token)
    host = dns_name(st)
    if args.ensure_serve is not None:
        ensure_serve(api_port, token, host, args.ensure_serve)
    if args.base_url:
        print(public_base_url(host))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
