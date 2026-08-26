#!/usr/bin/env bash
# Serve dist/LiftLog.ipa over HTTP on this Mac's Tailscale IPv4.
# LiveContainer on the phone: plus button → install from URL, or open LIVECONTAINER_URL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
IPA="${1:-$ROOT/dist/LiftLog.ipa}"

[ -f "$IPA" ] || {
  printf 'serve-ipa: missing %s\n' "$IPA" >&2
  printf 'Run scripts/build-ipa.sh first.\n' >&2
  exit 1
}

exec python3 "$ROOT/scripts/ipa_serve.py" "$IPA"
