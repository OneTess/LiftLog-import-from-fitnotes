#!/usr/bin/env bash
# Boot the iPhone 17e simulator and launch LiftLog.
#
# Default: open Simulator and launch the already-installed app (no rebuild).
# App data is snapshotted on the host and restored after install, so it
# survives xcodebuild / DerivedData wipes unless --clean-data is passed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
APP_DIR="$ROOT/app"
IOS_DIR="$APP_DIR/ios"
DERIVED="$ROOT/DerivedData-simulator"
BUNDLE="${BUNDLE_ID:-com.limajuice.liftlog}"
SIM_NAME="${SIM_NAME:-iPhone 17e}"
SCHEME="${SCHEME:-LiftLog}"
CONFIGURATION="${CONFIGURATION:-Debug}"
METRO_PORT="${METRO_PORT:-8081}"
DEV_CLIENT_SCHEME="${DEV_CLIENT_SCHEME:-exp+liftlog}"
DATA_BACKUP="$ROOT/.simulator-app-data/iphone-17e/$BUNDLE"

log() { printf '%s\n' "$*"; }
die() { printf 'launch-sim-17e: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
usage: $(basename "$0") [options]

Boot the $SIM_NAME simulator and launch LiftLog ($BUNDLE).

  -b, --build         Incremental $CONFIGURATION build, then install and launch
  -c, --clean-build   Delete simulator DerivedData products, rebuild, install, launch
  -d, --clean-data    Wipe the app's data (and the host snapshot) before launch
      --no-metro      Do not start Metro or deep-link the Expo dev client
  -h, --help          Show this help

Default (no flags): open the simulator and launch the already-installed app.
Debug builds include expo-dev-client, which only shows LiftLog after Metro is
up; the script starts Metro on 127.0.0.1:$METRO_PORT if needed and opens
$DEV_CLIENT_SCHEME://expo-development-client/?url=... so it does not sit on
"Searching for development servers...".

Does not uninstall or erase the simulator. --clean-build does not wipe app data.

Host snapshot: $DATA_BACKUP
Simulator DerivedData: $DERIVED

Override with SIM_NAME, BUNDLE_ID, SCHEME, CONFIGURATION, METRO_PORT.
EOF
}

DO_BUILD=0
DO_CLEAN_BUILD=0
DO_CLEAN_DATA=0
DO_METRO=1

while [ $# -gt 0 ]; do
  case "$1" in
    -b|--build) DO_BUILD=1 ;;
    -c|--clean-build) DO_CLEAN_BUILD=1; DO_BUILD=1 ;;
    -d|--clean-data) DO_CLEAN_DATA=1 ;;
    --no-metro) DO_METRO=0 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
  shift
done

if [ "$CONFIGURATION" != "Debug" ]; then
  DO_METRO=0
fi

command -v xcrun >/dev/null || die "xcrun not found (need Xcode)"
command -v ditto >/dev/null || die "ditto not found"

find_simulator() {
  xcrun simctl list devices available -j | python3 -c '
import json, sys
name = sys.argv[1]
data = json.load(sys.stdin)
booted = avail = None
for devices in data.get("devices", {}).values():
    for d in devices:
        if d.get("name") != name:
            continue
        rec = d["udid"]
        if d.get("state") == "Booted":
            booted = rec
        elif avail is None:
            avail = rec
print(booted or avail or "")
' "$SIM_NAME"
}

UDID="$(find_simulator)"
[ -n "$UDID" ] || die "no available simulator named $SIM_NAME
Install it in Xcode → Settings → Platforms / Components, then:
  xcrun simctl list devices available"

app_container() {
  # $1 = app | data | groups
  xcrun simctl get_app_container "$UDID" "$BUNDLE" "$1" 2>/dev/null || true
}

app_installed() {
  [ -n "$(app_container app)" ]
}

terminate_app() {
  xcrun simctl terminate "$UDID" "$BUNDLE" >/dev/null 2>&1 || true
}

snapshot_data() {
  local data
  data="$(app_container data)"
  [ -n "$data" ] && [ -d "$data" ] || return 0
  mkdir -p "$DATA_BACKUP"
  for dir in Documents Library tmp; do
    if [ -d "$data/$dir" ]; then
      rm -rf "$DATA_BACKUP/$dir"
      ditto "$data/$dir" "$DATA_BACKUP/$dir"
    fi
  done
  log "snapshotted app data → $DATA_BACKUP"
}

restore_data() {
  local data
  [ -d "$DATA_BACKUP" ] || return 0
  data="$(app_container data)"
  [ -n "$data" ] && [ -d "$data" ] || return 0
  terminate_app
  for dir in Documents Library tmp; do
    if [ -d "$DATA_BACKUP/$dir" ]; then
      rm -rf "$data/$dir"
      ditto "$DATA_BACKUP/$dir" "$data/$dir"
    fi
  done
  log "restored app data from $DATA_BACKUP"
}

wipe_live_data() {
  local data
  data="$(app_container data)"
  [ -n "$data" ] && [ -d "$data" ] || return 0
  terminate_app
  rm -rf "$data/Documents" "$data/Library" "$data/tmp"
  mkdir -p "$data/Documents" "$data/Library" "$data/tmp"
}

wipe_host_snapshot() {
  rm -rf "$DATA_BACKUP"
}

boot_simulator() {
  local state
  state="$(xcrun simctl list devices -j | python3 -c '
import json, sys
udid = sys.argv[1]
data = json.load(sys.stdin)
for devices in data.get("devices", {}).values():
    for d in devices:
        if d.get("udid") == udid:
            print(d.get("state", ""))
            raise SystemExit
' "$UDID")"
  if [ "$state" != "Booted" ]; then
    log "booting $SIM_NAME ($UDID)"
    xcrun simctl boot "$UDID"
  else
    log "$SIM_NAME already booted ($UDID)"
  fi
  xcrun simctl bootstatus "$UDID" -b >/dev/null
  # simctl boot is enough to run the app; opening Simulator.app is only for
  # the window. Ignore Launch Services failures (sandbox, already-open, etc.).
  open -a Simulator >/dev/null 2>&1 || true
}

build_app() {
  command -v xcodebuild >/dev/null || die "xcodebuild not found"
  [ -f "$IOS_DIR/LiftLog.xcworkspace/contents.xcworkspacedata" ] \
    || die "missing $IOS_DIR/LiftLog.xcworkspace (run expo prebuild --platform ios)"

  mkdir -p "$DERIVED/logs"
  local build_log
  build_log="$DERIVED/logs/sim-$(date '+%Y%m%d-%H%M%S').log"
  if [ "$DO_CLEAN_BUILD" -eq 1 ]; then
    log "clean build: removing $DERIVED/Build"
    rm -rf "$DERIVED/Build"
  fi
  log "xcodebuild $CONFIGURATION iphonesimulator (log: $build_log)"

  set +e
  (
    cd "$APP_DIR"
    xcodebuild \
      -workspace ios/LiftLog.xcworkspace \
      -scheme "$SCHEME" \
      -configuration "$CONFIGURATION" \
      -sdk iphonesimulator \
      -destination "platform=iOS Simulator,id=$UDID" \
      -derivedDataPath "$DERIVED" \
      COMPILER_INDEX_STORE_ENABLE=NO \
      ENABLE_USER_SCRIPT_SANDBOXING=NO \
      ONLY_ACTIVE_ARCH=YES \
      build
  ) 2>&1 | tee "$build_log"
  local status="${PIPESTATUS[0]}"
  set -e
  [ "$status" -eq 0 ] || die "xcodebuild failed — see $build_log"

  APP="$(find "$DERIVED/Build/Products/${CONFIGURATION}-iphonesimulator" -maxdepth 1 -name 'LiftLog.app' -print -quit || true)"
  [ -n "$APP" ] && [ -d "$APP" ] || die "LiftLog.app missing under $DERIVED/Build/Products/${CONFIGURATION}-iphonesimulator"
}

install_app() {
  [ -n "${APP:-}" ] && [ -d "$APP" ] || die "no .app to install"
  terminate_app
  log "installing $APP"
  xcrun simctl install "$UDID" "$APP"
}

metro_status() {
  curl -sf --max-time 1 "http://127.0.0.1:${METRO_PORT}/status" 2>/dev/null || true
}

metro_running() {
  printf '%s' "$(metro_status)" | grep -q 'packager-status:running'
}

dev_client_url() {
  python3 -c '
from urllib.parse import quote
import sys
port = sys.argv[1]
scheme = sys.argv[2]
manifest = "http://127.0.0.1:" + port
print(
    scheme
    + "://expo-development-client/?url="
    + quote(manifest, safe="")
    + "&disableOnboarding=1"
)
' "$METRO_PORT" "$DEV_CLIENT_SCHEME"
}

ensure_metro() {
  command -v curl >/dev/null || die "curl not found (needed to wait for Metro)"
  command -v npx >/dev/null || die "npx not found (needed to start Metro)"
  if metro_running; then
    log "Metro already running on 127.0.0.1:$METRO_PORT"
    return 0
  fi
  mkdir -p "$DERIVED/logs"
  local metro_log
  metro_log="$DERIVED/logs/metro.log"
  log "starting Metro on 127.0.0.1:$METRO_PORT (log: $metro_log)"
  nohup bash -c '
    cd "$0"
    export EXPO_NO_TELEMETRY=1
    exec npx expo start --dev-client --localhost --port "$1"
  ' "$APP_DIR" "$METRO_PORT" >>"$metro_log" 2>&1 &
  local i
  for i in $(seq 1 90); do
    if metro_running; then
      log "Metro ready"
      return 0
    fi
    sleep 1
  done
  die "Metro did not become ready on 127.0.0.1:$METRO_PORT — see $metro_log"
}

# iOS 18+ simctl openurl shows "Open in LiftLog?" unless the scheme is
# pre-approved on the simulator. Value is the bundle id, key is the URL scheme.
preapprove_dev_client_scheme() {
  xcrun simctl spawn "$UDID" defaults write com.apple.launchservices.schemeapproval \
    "com.apple.CoreSimulator.CoreSimulatorBridge-->${DEV_CLIENT_SCHEME}" \
    -string "$BUNDLE" >/dev/null
}

launch_app() {
  terminate_app
  if [ "$DO_METRO" -eq 1 ]; then
    local url
    url="$(dev_client_url)"
    preapprove_dev_client_scheme
    log "opening $url"
    xcrun simctl openurl "$UDID" "$url" >/dev/null
  else
    log "launching $BUNDLE"
    xcrun simctl launch "$UDID" "$BUNDLE" >/dev/null
  fi
}

cd "$ROOT"
boot_simulator
if [ "$DO_METRO" -eq 1 ]; then
  ensure_metro
fi

if [ "$DO_CLEAN_DATA" -eq 1 ]; then
  log "wiping app data"
  wipe_live_data
  wipe_host_snapshot
fi

if [ "$DO_BUILD" -eq 1 ]; then
  # Compile first so a long xcodebuild does not snapshot mid-session data
  # and then clobber whatever the user logged while waiting.
  build_app
  if [ "$DO_CLEAN_DATA" -eq 0 ] && app_installed; then
    snapshot_data
  fi
  install_app
  if [ "$DO_CLEAN_DATA" -eq 0 ]; then
    restore_data
  fi
else
  app_installed || die "LiftLog is not installed on $SIM_NAME. Re-run with --build."
  if [ "$DO_CLEAN_DATA" -eq 0 ]; then
    snapshot_data
  fi
fi

app_installed || die "LiftLog is not installed on $SIM_NAME after install"
launch_app
log "launched $BUNDLE on $SIM_NAME"
if [ "$DO_METRO" -eq 1 ]; then
  log "Metro: http://127.0.0.1:$METRO_PORT (leave that process running)"
fi
