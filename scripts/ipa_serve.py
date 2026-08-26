#!/usr/bin/env python3
"""Serve an IPA over HTTP on this Mac's Tailscale IPv4 for LiveContainer.

Prints:
  IPA_URL=http://<tailscale-ipv4>:<port>/<filename>
  LIVECONTAINER_URL=livecontainer://install?url=<urlencoded-ipa-url>

Bind is 0.0.0.0 so the phone on the tailnet can GET the file. The printed
host is the Tailscale IPv4 (or TAILSCALE_IP), not MagicDNS HTTPS.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote, urlparse


DEFAULT_PORT = 15009
CGNAT = ipaddress.ip_network("100.64.0.0/10")


def discover_tailscale_ipv4() -> Optional[str]:
    env = os.environ.get("TAILSCALE_IP", "").strip()
    if env:
        return env
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                candidate = line.strip()
                if candidate:
                    return candidate
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    for raw in result.stdout.splitlines():
        parts = raw.split()
        if len(parts) >= 2 and parts[0] == "inet":
            addr = parts[1]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if ip in CGNAT:
                return addr
    return None


def ipa_http_url(host: str, port: int, filename: str) -> str:
    return f"http://{host}:{port}/{filename}"


def livecontainer_install_url(http_url: str) -> str:
    return "livecontainer://install?url=" + quote(http_url, safe="")


def _handler_for(ipa_path: Path):
    ipa_path = ipa_path.resolve()
    name = ipa_path.name

    class IpaHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path.rstrip("/") != f"/{name}":
                self.send_error(404, "not found")
                return
            if not ipa_path.is_file():
                self.send_error(404, "ipa missing")
                return
            size = ipa_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.end_headers()
            with ipa_path.open("rb") as fh:
                shutil.copyfileobj(fh, self.wfile)

        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    return IpaHandler


def make_server(
    ipa_path: Path,
    bind: str = "0.0.0.0",
    port: int = DEFAULT_PORT,
    advertise_host: Optional[str] = None,
) -> Tuple[ThreadingHTTPServer, str, str]:
    ipa_path = Path(ipa_path)
    if not ipa_path.is_file():
        raise FileNotFoundError(f"IPA not found: {ipa_path}")
    httpd = ThreadingHTTPServer((bind, port), _handler_for(ipa_path))
    actual_port = httpd.server_address[1]
    host = advertise_host or discover_tailscale_ipv4() or "127.0.0.1"
    url = ipa_http_url(host, actual_port, ipa_path.name)
    return httpd, url, livecontainer_install_url(url)


def print_urls(ipa_url: str, lc_url: str) -> None:
    print(f"IPA_URL={ipa_url}")
    print(f"LIVECONTAINER_URL={lc_url}")
    print("Install in LiveContainer: plus button on My Apps → install from URL → paste IPA_URL")
    print(f"Or open: {lc_url}")
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HTTP-serve an IPA for LiveContainer install-from-URL"
    )
    parser.add_argument("ipa", type=Path, help="Path to the .ipa")
    parser.add_argument("--port", type=int, default=int(os.environ.get("IPA_HTTP_PORT", DEFAULT_PORT)))
    parser.add_argument("--bind", default=os.environ.get("IPA_HTTP_BIND", "0.0.0.0"))
    parser.add_argument(
        "--host",
        default=None,
        help="Host printed in the URL (default: Tailscale IPv4 / TAILSCALE_IP)",
    )
    args = parser.parse_args()
    host = args.host or discover_tailscale_ipv4()
    if not host:
        print(
            "ipa_serve: no Tailscale IPv4 found. Set TAILSCALE_IP=100.x.x.x "
            "(this Mac's tailscale ip -4) or pass --host.",
            file=sys.stderr,
        )
        return 2
    httpd, url, lc_url = make_server(args.ipa, bind=args.bind, port=args.port, advertise_host=host)
    print_urls(url, lc_url)
    print(f"Serving {args.ipa} on {args.bind}:{httpd.server_address[1]} (Ctrl-C to stop)", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
