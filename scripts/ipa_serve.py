#!/usr/bin/env python3
"""Serve an IPA on localhost and advertise a Tailscale Serve HTTPS URL.

Prints:
  IPA_URL=https://<magicdns>/LiftLog.ipa
  LIVECONTAINER_URL=livecontainer://install?url=<urlencoded-ipa-url>

Python binds 127.0.0.1 only. Tailscale Serve (Let's Encrypt on *.ts.net)
proxies https://<this-mac>.<tailnet>.ts.net/ to that port. LiveContainer ATS
needs that public CA; a Tailscale IPv4 http:// URL is not enough.

Does not use Superapp or any other repo. SKIP_TAILSCALE_SERVE=1 prints the
localhost HTTP URL instead (tests / no Tailscale).
"""
from __future__ import annotations

import argparse
import errno
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import quote, urlparse


DEFAULT_PORT = 15009
DEFAULT_BIND = "127.0.0.1"
TAILSCALE_HTTPS = Path(__file__).resolve().with_name("tailscale-https.py")


def livecontainer_install_url(ipa_url: str) -> str:
    return "livecontainer://install?url=" + quote(ipa_url, safe="")


def ipa_http_url(host: str, port: int, filename: str) -> str:
    return f"http://{host}:{port}/{filename}"


def _path_is_ipa(request_path: str, filename: str) -> bool:
    path = urlparse(request_path).path.rstrip("/")
    return path in (f"/{filename}", f"/liftlog/{filename}")


def _handler_for(ipa_path: Path):
    ipa_path = ipa_path.resolve()
    name = ipa_path.name

    class IpaHandler(BaseHTTPRequestHandler):
        def _send_ipa_headers(self) -> Optional[int]:
            if not _path_is_ipa(self.path, name):
                self.send_error(404, "not found")
                return None
            if not ipa_path.is_file():
                self.send_error(404, "ipa missing")
                return None
            size = ipa_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.end_headers()
            return size

        def do_HEAD(self) -> None:  # noqa: N802
            self._send_ipa_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self._send_ipa_headers() is None:
                return
            with ipa_path.open("rb") as fh:
                shutil.copyfileobj(fh, self.wfile)

        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    return IpaHandler


def listener_pids(port: int) -> List[int]:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    pids: List[int] = []
    for line in out.split():
        if line.isdigit():
            pid = int(line)
            if pid != os.getpid() and pid not in pids:
                pids.append(pid)
    return pids


def existing_ipa_length(port: int, filename: str) -> Optional[int]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/{filename}", method="HEAD"
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            raw = resp.headers.get("Content-Length")
            return int(raw) if raw else 0
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def make_server(
    ipa_path: Path,
    bind: str = DEFAULT_BIND,
    port: int = DEFAULT_PORT,
    advertise_host: Optional[str] = None,
) -> Tuple[ThreadingHTTPServer, str, str]:
    ipa_path = Path(ipa_path)
    if not ipa_path.is_file():
        raise FileNotFoundError(f"IPA not found: {ipa_path}")
    httpd = ThreadingHTTPServer((bind, port), _handler_for(ipa_path))
    actual_port = httpd.server_address[1]
    host = advertise_host or "127.0.0.1"
    url = ipa_http_url(host, actual_port, ipa_path.name)
    return httpd, url, livecontainer_install_url(url)


def ensure_https_ipa_url(backend_port: int, filename: str) -> str:
    proc = subprocess.run(
        [
            sys.executable,
            str(TAILSCALE_HTTPS),
            "--base-url",
            "--ensure-serve",
            str(backend_port),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"tailscale-https.py failed: {err}")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        if not proc.stderr.endswith("\n"):
            sys.stderr.write("\n")
    base = ""
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("https://"):
            base = line
    if not base:
        raise RuntimeError("tailscale-https.py printed no https:// base URL")
    return f"{base.rstrip('/')}/{filename.lstrip('/')}"


def print_urls(ipa_url: str, lc_url: str) -> None:
    print(f"IPA_URL={ipa_url}")
    print(f"LIVECONTAINER_URL={lc_url}")
    print("Install in LiveContainer: plus button on My Apps → install from URL → paste IPA_URL")
    print(f"Or open: {lc_url}")
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HTTPS-serve an IPA for LiveContainer install-from-URL via Tailscale Serve"
    )
    parser.add_argument("ipa", type=Path, help="Path to the .ipa")
    parser.add_argument("--port", type=int, default=int(os.environ.get("IPA_HTTP_PORT", DEFAULT_PORT)))
    parser.add_argument("--bind", default=os.environ.get("IPA_HTTP_BIND", DEFAULT_BIND))
    parser.add_argument(
        "--host",
        default=None,
        help="Skip Tailscale Serve and print http://HOST:PORT/file (tests)",
    )
    args = parser.parse_args()
    skip = os.environ.get("SKIP_TAILSCALE_SERVE", "0") == "1" or args.host is not None
    advertise = args.host or "127.0.0.1"
    try:
        httpd, backend_url, _ = make_server(
            args.ipa, bind=args.bind, port=args.port, advertise_host=advertise
        )
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        pids = listener_pids(args.port)
        pid_s = ", ".join(str(p) for p in pids) or "unknown"
        have = existing_ipa_length(args.port, args.ipa.name)
        want = args.ipa.stat().st_size
        if have == want:
            print(
                f"ipa_serve: {args.bind}:{args.port} already serving this IPA "
                f"(pid {pid_s}, {want} bytes)",
                file=sys.stderr,
            )
            if skip:
                url = ipa_http_url(advertise, args.port, args.ipa.name)
            else:
                url = ensure_https_ipa_url(args.port, args.ipa.name)
            print_urls(url, livecontainer_install_url(url))
            print(
                f"Leave it running, or replace with: kill {pid_s} && ./scripts/serve-ipa.sh",
                file=sys.stderr,
            )
            return 0
        extra = f", HEAD Content-Length={have}" if have is not None else ", not this IPA"
        print(
            f"ipa_serve: {args.bind}:{args.port} already in use (pid {pid_s}){extra}",
            file=sys.stderr,
        )
        print(f"Stop it with: kill {pid_s}", file=sys.stderr)
        return 1
    actual_port = httpd.server_address[1]
    try:
        if skip:
            url = backend_url
        else:
            url = ensure_https_ipa_url(actual_port, args.ipa.name)
        print_urls(url, livecontainer_install_url(url))
        print(
            f"Serving {args.ipa} on {args.bind}:{actual_port} (Ctrl-C to stop)",
            file=sys.stderr,
        )
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    except Exception as exc:
        print(f"ipa_serve: {exc}", file=sys.stderr)
        return 1
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
