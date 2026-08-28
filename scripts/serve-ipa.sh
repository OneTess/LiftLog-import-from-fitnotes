#!/usr/bin/env bash
# Serve dist/LiftLog.ipa over Tailscale Serve HTTPS for LiveContainer.
# Python binds 127.0.0.1; Tailscale proxies https://<magicdns>/LiftLog.ipa
# with a Let's Encrypt cert. Independent of Superapp or any other repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
IPA="${1:-$ROOT/dist/LiftLog.ipa}"

[ -f "$IPA" ] || {
  printf 'serve-ipa: missing %s\n' "$IPA" >&2
  printf 'Run scripts/build-ipa.sh first.\n' >&2
  exit 1
}

exec python3 "$ROOT/scripts/ipa_serve.py" "$IPA"
