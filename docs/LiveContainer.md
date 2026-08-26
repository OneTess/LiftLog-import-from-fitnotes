# Personal LiveContainer IPA (LiftLog 4.22.0)

Build an **unsigned** device IPA of this tree and install it on your own iPhones through **LiveContainer → install from URL**, using this Mac’s **Tailscale IPv4 HTTP URL**. No paid Apple Developer Program account, no App Store Connect, no EAS.

LiveContainer is already installed from **AltStore Classic**. This guide does not install or reconfigure AltStore or LiveContainer.

## What this is

- Source pin: official tag **`4.22.0`** (`d1808a86d075db8f681b634700c32d415431dc38`), newer than App Store LiftLog 4.19.
- The IPA is **unsigned**. In JIT-less mode LiveContainer re-signs the guest with the **AltStore certificate** you imported into LiveContainer. You do not sign with a paid team.
- Guest apps inside LiveContainer **do not consume extra Personal Team app slots**. AltStore + LiveContainer already use slots; LiftLog-as-guest does not install as a third home-screen app.
- **This tree does not update itself.** `scripts/build-ipa.sh` never `git fetch` or `git pull`. Stay on 4.22.0 until you explicitly change `scripts/livecontainer-pin` and check out a newer tag.

## One-time Mac setup

- Xcode (iOS device SDK), Node.js, CocoaPods (`pod`), Python 3.
- Tailscale app logged in on this Mac **and** on the iPhone (same tailnet).
- This Mac awake while you install; the phone GETs the IPA from here.

Confirm the Tailscale IPv4 (CGNAT `100.x`):

```bash
ifconfig | awk '/inet 100\./ { print $2 }'
```

If the CLI is on PATH: `tailscale ip -4`. Override with `TAILSCALE_IP=100.x.x.x` if discovery fails.

On the phone: LiveContainer → Settings → JIT-less diagnose. Import the **AltStore Classic certificate** if JIT-less signing is not already green. Official LiveContainer docs mention AltStore 2.2.1+ for cert export; Classic is what this setup uses. If import fails, that is on-device setup, not a reason to buy a developer account.

## Build

From the repo root (this directory is the LiftLog clone):

```bash
./scripts/build-ipa.sh
```

That runs `npm ci` → `expo prebuild --platform ios --no-install` → `pod install` → `xcodebuild` for `iphoneos` Release with signing disabled → zips `Payload/LiftLog.app` to `dist/LiftLog.ipa`.

The script keeps npm and CocoaPods caches inside this clone (`.npm-cache/`, `.cocoapods/`), sets `RCT_SKIP_CACHES=1` so Hermes tarballs land in `Pods/` instead of `~/Library/Caches/ReactNative`, and builds React Native from source. Override with `RCT_USE_PREBUILT_RNCORE=1` and `RCT_SKIP_CACHES=0` if that cache directory is writable on your Mac.

Expect several minutes. Do not commit `app/ios/` or `dist/`.

If `xcodebuild` fails with `AssetCatalogSimulatorAgent` / `CoreSimulator` “Operation not permitted”, the Mac (or the shell) cannot write `~/Library/Developer/CoreSimulator/Devices`. That is required for `actool` even for a device IPA. Run the same script in a normal Terminal.app session on this Mac — not a sandbox that blocks CoreSimulator.

## Serve and install

Keep this Mac on Tailscale. In the same repo:

```bash
./scripts/serve-ipa.sh
```

It prints:

```
IPA_URL=http://<tailscale-ipv4>:15009/LiftLog.ipa
LIVECONTAINER_URL=livecontainer://install?url=<urlencoded IPA_URL>
```

On the iPhone (Tailscale connected):

1. Open **LiveContainer**.
2. On **My Apps**, tap **+** and choose **install from URL**.
3. Paste `IPA_URL`.

Or open `LIVECONTAINER_URL` on the phone (Safari / Notes). That is the scheme from [LiveContainer 3.3.0 / issue 372](https://github.com/LiveContainer/LiveContainer/issues/372).

The HTTP URL is **`http://` + Tailscale IPv4**, not MagicDNS HTTPS. LiveContainer install-from-URL does not need a public CA.

Stop the server with Ctrl-C when finished. Re-run `./scripts/serve-ipa.sh` after a new `./scripts/build-ipa.sh` to ship a replacement IPA.

Port default is **15009** (`IPA_HTTP_PORT`) so it does not collide with other local HTTP servers on this Mac.

## Version pin (do not pull upstream)

`scripts/livecontainer-pin` records:

```
tag=4.22.0
sha=d1808a86d075db8f681b634700c32d415431dc38
```

`build-ipa.sh` checks that HEAD is that commit or a **descendant** (local script commits are fine). It will not pick up LiamMorrow/LiftLog `main` or a newer GitHub release.

To move the pin **on purpose**:

1. `git fetch upstream tag <new-tag>`
2. `git checkout -B feature/livecontainer-ipa <new-tag>` (replay or cherry-pick this LiveContainer scripts commit if needed)
3. Edit `scripts/livecontainer-pin` to the new tag and SHA
4. `./scripts/build-ipa.sh`

Until you do that, keep building 4.22.0.

`gh` fork was not created (GitHub token invalid). Remotes are `origin` and `upstream` → `https://github.com/LiamMorrow/LiftLog.git`. Product changes later can stay on `feature/livecontainer-ipa`.

## Tests

```bash
python3 scripts/test_ipa_pack.py
python3 scripts/test_ipa_serve.py
python3 scripts/test_ipa_pin.py
```

These pack a dummy `.app` and HTTP-GET the shipped server twice.

## Limits (free Apple ID)

- No App Store / TestFlight / EAS signing.
- RevenueCat / IAP will not work. The Release IPA has no App Store RevenueCat key; startup skips `Purchases.configure` so settings still hydrate.
- Push (`expo-notifications`) and Associated Domains may be stripped or inert after LiveContainer re-sign.
- HealthKit may or may not survive re-sign; logging still works on device.
- The Mac must be reachable on the tailnet while LiveContainer downloads the IPA.
