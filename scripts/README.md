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

## Collecting Screenshots For App Store

The collect screenshots script will start android and ios simulators and collect screenshots of various parts of the app. These can be used on the respective app stores.

Run:

```bash
bun run collect-screenshots.ts
```
