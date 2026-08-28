# LiftLog-personal
_a personal fork of mine. Built on my machine and used on my personal devices._
Upstream: [LiftLog GitHub](https://github.com/LiamMorrow/LiftLog)

<p align="center">
  <img width="250" src="./assets/AppScreens-LiftLog-1782275372989.render/apple/English (en-US)/iPhones  6.9/01.png" alt="App home page screenshot">
  <img width="250" src="./assets/AppScreens-LiftLog-1782275372989.render/apple/English (en-US)/iPhones  6.9/02.png" alt="Workout page screenshot">
  <img width="250" src="./assets/AppScreens-LiftLog-1782275372989.render/apple/English (en-US)/iPhones  6.9/03.png" alt="Stats page screenshot">
</p>

## ⚡ Quickstart

### Prerequisites

1. **Node.js** (v18+): [Download here](https://nodejs.org/)
2. **Expo CLI**: `npm install -g expo-cli` ([Guide](https://docs.expo.dev/get-started/set-up-your-environment/))
3. **Android Studio** (for Android) ([Setup](https://reactnative.dev/docs/environment-setup))
4. **Xcode** (for iOS, macOS only) ([Setup](https://reactnative.dev/docs/environment-setup?os=macos&platform=ios))

### Personal iOS IPA (LiveContainer)

Unsigned `iphoneos` IPA for **LiveContainer → install from URL** over this Mac’s Tailscale Serve HTTPS URL (`https://<magicdns>/LiftLog.ipa`), no paid developer account. Display version **4.22.0-personal-1**, based on official tag **4.22.0**; this checkout will not pull newer upstream releases. See [docs/LiveContainer.md](./docs/LiveContainer.md).

```bash
./scripts/build-ipa.sh
./scripts/serve-ipa.sh
```

### Run the App in debug mode

Run an iPhone 17e simulator
```bash
./scripts/launch-sim-17e.sh
```

OR

```bash
cd app
npm install
npm run android   # For Android
npm run ios       # For iOS (macOS only)
```

### Run the Backend API

See [`backend/README.md`](./backend/README.md) for more information on running the backend.

---

## 🗂️ Project Structure

LiftLog is organized into several projects:

### Frontend ([app/](./app/))

- **Main React Native app** (Expo)
- **Components**: `components/` (layout, presentation, smart)
- **State**: `store/` (Redux Toolkit)
- **Services**: `services/` (API, business logic)
- **Hooks**: `hooks/` (custom React hooks)
- **Translations**: `i18n/` (Tolgee)
- **Navigation**: Expo Router

### Backend ([LiftLog.Api/](./backend/))

For documentation on running the backend for local development, see [the README](./backend/README.md)

- **Dotnet WebAPI** for feeds, AI plans, and secure data
- **End-to-end encrypted feeds** (AES)
- **Claude integration** for workout plans

### RevenueCat ([RevenueCat/](./backend/RevenueCat/))
_guarded to not interfere with the app running inside livecontainer. RevenueCat running without the guards/limitations breaks the app when it's run inside LiveContainer._

- **Client library** for in-app purchases/subscriptions

---

## 📊 Stats


<a href="https://www.star-history.com/?type=date&repos=LiamMorrow%2FLiftLog">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=LiamMorrow/LiftLog&type=date&theme=dark&legend=top-left&sealed_token=4B9Ugtb3Kc7qXvqb65ZwPsxrnDwQPgGjYfiEGm3y0xNgxLObO-TJGQ5DetyZbtH0rGUZ5fvEje57YH4ip5m1O0DmxI32HHOUPNzIaSYXpCA3nzMEhe1-M08DlvXm5CtQLXpbTgpVSdIssFhbmwbM0obLXqglZFXYNrz-skEA7FJgI-tkP0t3ez3gJHnp" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=LiamMorrow/LiftLog&type=date&legend=top-left&sealed_token=4B9Ugtb3Kc7qXvqb65ZwPsxrnDwQPgGjYfiEGm3y0xNgxLObO-TJGQ5DetyZbtH0rGUZ5fvEje57YH4ip5m1O0DmxI32HHOUPNzIaSYXpCA3nzMEhe1-M08DlvXm5CtQLXpbTgpVSdIssFhbmwbM0obLXqglZFXYNrz-skEA7FJgI-tkP0t3ez3gJHnp" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=LiamMorrow/LiftLog&type=date&legend=top-left&sealed_token=4B9Ugtb3Kc7qXvqb65ZwPsxrnDwQPgGjYfiEGm3y0xNgxLObO-TJGQ5DetyZbtH0rGUZ5fvEje57YH4ip5m1O0DmxI32HHOUPNzIaSYXpCA3nzMEhe1-M08DlvXm5CtQLXpbTgpVSdIssFhbmwbM0obLXqglZFXYNrz-skEA7FJgI-tkP0t3ez3gJHnp" />
 </picture>
</a>

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) (or open an issue/PR).

AI/LLM-assisted contributions are welcome, but issues and feature requests should be written in your own words - see the [AI Usage Policy](./CONTRIBUTING.md#ai-usage-policy).

## 📚 Documentation

- [Plan Files](./docs/PlanFileFormat.md) - Documents the `.liftlogplan` file format, and how to generate plans with an AI for import into the app.
- [Feed Process](./docs/FeedProcess.md) - Documents how the feed and sharing works, especially around e2e encryption.
- [Remote Backup](./docs/RemoteBackup.md) - Documents how to connect LiftLog to a remote backup server.
- [Plaintext Export](./docs/PlaintextExport.md) - Documents how to export your data as plaintext.
- [Workout Worker](./docs/WorkoutWorker.md) - Documents the WorkoutWorker, an event based bridge between native and JS which powers the Android persistent notifications.
- [Storage Migrations](./docs/Migrations.md) - Documents how on-device data is versioned and migrated, and what to do when changing a stored model.

---

> **Note:** LiftLog was rewritten from the ground up in React Native. The previous .NET MAUI Blazor implementation is in the `dotnet` branch.
