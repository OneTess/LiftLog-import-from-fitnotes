#!/usr/bin/env bash
# Build an unsigned iphoneos IPA of the pinned LiftLog tag for LiveContainer.
# Does not git fetch or pull. Does not use a paid Apple Developer account.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
APP_DIR="$ROOT/app"
DIST="$ROOT/dist"
DERIVED="$ROOT/DerivedData"
IPA="$DIST/LiftLog.ipa"
PORT="${IPA_HTTP_PORT:-15009}"

log() { printf '%s\n' "$*"; }
die() { printf 'build-ipa: %s\n' "$*" >&2; exit 1; }

cd "$ROOT"

if [ "${ALLOW_UNPINNED:-0}" = "1" ]; then
  python3 "$ROOT/scripts/ipa_pin.py" --root "$ROOT" --allow-unpinned
else
  python3 "$ROOT/scripts/ipa_pin.py" --root "$ROOT"
fi

# Intentionally no git fetch / git pull. Stay on the pin unless you edit
# scripts/livecontainer-pin after an explicit checkout of a newer tag.

command -v xcodebuild >/dev/null || die "xcodebuild not found"
command -v pod >/dev/null || die "CocoaPods (pod) not found"
command -v npm >/dev/null || die "npm not found"

VERSION="$(python3 -c '
import json, pathlib, sys
app = json.loads(pathlib.Path(sys.argv[1]).read_text())
print(app["expo"]["version"])
' "$APP_DIR/app.json")"
PIN_TAG="$(awk -F= '/^tag=/{print $2}' "$ROOT/scripts/livecontainer-pin")"
PIN_DISPLAY="$(awk -F= '/^display=/{print $2}' "$ROOT/scripts/livecontainer-pin")"
# Show the personal display version (or the frozen GitHub tag) in
# CFBundleShortVersionString when the Expo marketing field is still 1.0.0.
if [ "$VERSION" = "1.0.0" ]; then
  VERSION="${PIN_DISPLAY:-$PIN_TAG}"
fi
BUILD="$(git -C "$ROOT" rev-list --count HEAD)"
SHORT="$(git -C "$ROOT" rev-parse --short HEAD)"

mkdir -p "$DIST" "$DERIVED/logs"
BUILD_LOG="$DERIVED/logs/ipa-$(date '+%Y%m%d-%H%M%S').log"
log "Building unsigned iphoneos IPA version=$VERSION build=$BUILD rev=$SHORT"
log "Full xcodebuild log: $BUILD_LOG"

# Harness/sandbox (and some Macs) cannot mkdir ~/.npm/_cacache. Keep the
# npm cache inside the clone; it is gitignored.
NPM_CACHE="${NPM_CONFIG_CACHE:-$ROOT/.npm-cache}"
mkdir -p "$NPM_CACHE/logs"
export NPM_CONFIG_CACHE="$NPM_CACHE"
export NPM_CONFIG_LOGS_DIR="$NPM_CACHE/logs"
if [ "${SKIP_NPM_CI:-0}" != "1" ]; then
  log "npm ci (cache=$NPM_CACHE)"
  (cd "$APP_DIR" && npm ci --cache "$NPM_CACHE" --logs-dir "$NPM_CACHE/logs")
else
  log "skipping npm ci (SKIP_NPM_CI=1)"
fi

# CocoaPods must not write Spec_Lock under ~/.cocoapods (EPERM in some
# environments). Keep CP_HOME_DIR in-repo and reuse the user's trunk specs.
export CP_HOME_DIR="${CP_HOME_DIR:-$ROOT/.cocoapods}"
mkdir -p "$CP_HOME_DIR/repos"
# A symlink to ~/.cocoapods/repos/trunk is not writable (Spec_Lock / CDN
# index files). Use an in-repo CDN clone instead.
if [ -L "$CP_HOME_DIR/repos/trunk" ]; then
  rm -f "$CP_HOME_DIR/repos/trunk"
fi
if [ ! -d "$CP_HOME_DIR/repos/trunk" ]; then
  log "pod repo add-cdn trunk (into $CP_HOME_DIR)"
  pod repo add-cdn trunk https://cdn.cocoapods.org/
fi

# Prebuilt RNCore/Hermes default to ~/Library/Caches/ReactNative (often EPERM).
# Compile RN from source; RCT_SKIP_CACHES puts Hermes tarballs in Pods/.
export RCT_USE_PREBUILT_RNCORE="${RCT_USE_PREBUILT_RNCORE:-0}"
export RCT_USE_RN_DEP="${RCT_USE_RN_DEP:-0}"
export EXPO_USE_PRECOMPILED_MODULES="${EXPO_USE_PRECOMPILED_MODULES:-0}"
export RCT_SKIP_CACHES="${RCT_SKIP_CACHES:-1}"

if [ "${SKIP_PREBUILD:-0}" != "1" ]; then
  log "expo prebuild --platform ios --no-install"
  (
    cd "$APP_DIR"
    CI=1 EXPO_NO_TELEMETRY=1 npx expo prebuild --platform ios --no-install
  )
else
  log "skipping expo prebuild (SKIP_PREBUILD=1)"
fi

[ -d "$APP_DIR/ios" ] || die "expo prebuild did not create app/ios"
if [ "${SKIP_PODS:-0}" != "1" ]; then
  log "pod install (CP_HOME_DIR=$CP_HOME_DIR RCT_USE_PREBUILT_RNCORE=$RCT_USE_PREBUILT_RNCORE)"
  (
    cd "$APP_DIR/ios"
    pod install --no-repo-update
  )
else
  log "skipping pod install (SKIP_PODS=1)"
fi

[ -f "$APP_DIR/ios/LiftLog.xcworkspace/contents.xcworkspacedata" ] \
  || die "missing app/ios/LiftLog.xcworkspace"

# Optional: XCODE_HOME remaps HOME for xcodebuild only (actool writes
# CoreSimulator under $HOME). Leave unset on a normal Mac.
if [ -n "${XCODE_HOME:-}" ]; then
  mkdir -p "$XCODE_HOME/Library/Developer/CoreSimulator/Devices"
  mkdir -p "$XCODE_HOME/Library/Caches"
fi

set +e
(
  cd "$APP_DIR"
  if [ -n "${XCODE_HOME:-}" ]; then
    export HOME="$XCODE_HOME"
  fi
  xcodebuild \
    -workspace ios/LiftLog.xcworkspace \
    -scheme LiftLog \
    -configuration Release \
    -sdk iphoneos \
    -destination "generic/platform=iOS" \
    -derivedDataPath "$DERIVED" \
    COMPILER_INDEX_STORE_ENABLE=NO \
    ENABLE_USER_SCRIPT_SANDBOXING=NO \
    ENABLE_PREVIEWS=NO \
    APP_DISPLAY_VERSION="$VERSION" \
    APP_VERSION="$BUILD" \
    CODE_SIGNING_ALLOWED=NO \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGN_IDENTITY= \
    DEVELOPMENT_TEAM= \
    build
) 2>&1 | tee "$BUILD_LOG"
XCODE_STATUS="${PIPESTATUS[0]}"
set -e
[ "$XCODE_STATUS" -eq 0 ] || die "xcodebuild failed — see $BUILD_LOG"

APP="$(find "$DERIVED/Build/Products/Release-iphoneos" -maxdepth 1 -name 'LiftLog.app' -print -quit || true)"
[ -n "$APP" ] && [ -d "$APP" ] || die "Release-iphoneos LiftLog.app missing under $DERIVED"

if [ -x "$APP/LiftLog" ]; then
  ARCHS="$(lipo -archs "$APP/LiftLog" 2>/dev/null || true)"
  log "Binary archs: ${ARCHS:-unknown}"
  echo "$ARCHS" | grep -q arm64 || die "IPA binary is not arm64 ($ARCHS)"
fi

python3 "$ROOT/scripts/ipa_pack.py" "$APP" "$IPA"
unzip -t "$IPA" >/dev/null
# grep -q closes the pipe on first match; unzip then SIGPIPEs and pipefail
# treats the pipeline as failed even when Payload/*.app is present.
python3 -c '
import sys, zipfile
names = zipfile.ZipFile(sys.argv[1]).namelist()
if not any(n.startswith("Payload/") and ".app/" in n for n in names):
    sys.exit(1)
' "$IPA" || die "IPA missing Payload/*.app"

log "IPA $IPA ($(wc -c <"$IPA" | tr -d ' ') bytes)"
log "Next: $ROOT/scripts/serve-ipa.sh"
log "Then paste the printed IPA_URL into LiveContainer → plus → install from URL"
log "Default HTTP port $PORT (override with IPA_HTTP_PORT)"
