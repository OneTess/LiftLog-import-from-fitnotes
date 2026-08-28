# scripts

To install dependencies:

```bash
bun install
```

This directory contains general scripts which LiftLog uses.

## LiveContainer IPA (personal devices)

Display version 4.22.0-personal-1, based on official tag 4.22.0 (`scripts/livecontainer-pin`). Does not git fetch/pull.

```bash
./scripts/build-ipa.sh
./scripts/serve-ipa.sh
```

Guide: [`docs/LiveContainer.md`](../docs/LiveContainer.md).

## iPhone 17e simulator

Boot the iPhone 17e simulator and launch the installed LiftLog app. Default is launch only — no rebuild.

```bash
./scripts/launch-sim-17e.sh              # open sim, launch existing install
./scripts/launch-sim-17e.sh --build      # incremental Debug build, install, launch
./scripts/launch-sim-17e.sh --clean-build
./scripts/launch-sim-17e.sh --clean-data # wipe app data, then launch
```

`--clean-build` does not wipe app data. Data is snapshotted under `.simulator-app-data/` and restored after install unless `--clean-data` is passed.

Debug installs are Expo development builds: the script starts Metro (`npx expo start --dev-client --localhost`) if needed and opens `exp+liftlog://expo-development-client/?url=...` so the sim does not sit on “Searching for development servers…”. It also pre-approves that URL scheme so iOS does not show “Open in LiftLog?”. Pass `--no-metro` to skip Metro.

## Collecting Screenshots For App Store

The collect screenshots script will start android and ios simulators and collect screenshots of various parts of the app. These can be used on the respective app stores.

Run:

```bash
bun run collect-screenshots.ts
```
