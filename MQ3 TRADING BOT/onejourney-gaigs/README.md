# GAIGS / OneJourney

An Android-first, local-first civic operating-system prototype. It is intentionally honest about its state: the application runs as an **Interactive Demo** with persistent local data by default; no simulated balance is a real wallet and no demo governance result is a legal or sovereign decision.

The app demonstrates one connected journey: profile → community → issue → discussion → proposal → deterministic vote → sandbox allocation → project milestone → verification → reputation. It also includes an evidence-oriented Global Pulse, local services, emergency coordination, Humanity Lab, transparent audit history, a role-aware Community Hub, and the JARVIS intelligence layer.

## Run locally

1. Install Node.js 20+ and copy `.env.example` to `.env` if you want to configure provider adapters.
2. Double-click `RUN_GAIGS.cmd`. On first use it installs required packages, starts the local server, and opens the app automatically.

Alternatively, from this folder run `npm install` followed by `npm run dev:open`.

Use **Continue as demo member** on the sign-in screen, or create a locally persisted account. The account and all actions persist in browser storage. Use the reset action in the profile menu to restore the pilot world.

## Test and production build

```text
npm test
npm run build
```

The domain tests cover deterministic voting, duplicate-vote rejection, audit-chain integrity, membership authorization, and sandbox-treasury controls.

## Android wrapper

This repository includes a Capacitor Android project that packages the same responsive app:

```text
npm run android:sync
npx cap open android
```

`npm run android:add` is retained only for intentionally recreating the native wrapper after deleting `android/`. This workspace does not contain a Flutter, JDK, or Android SDK installation, so an APK cannot be compiled here. The app has been synced to the committed Android wrapper and is ready to build with Android Studio on a configured Android workstation. No binary is claimed as built unless Gradle completes there.

## Firebase deployment path

`firestore/firestore.rules` and `functions/` provide the production path. The Function layer owns privileged calculations (vote results, audit events, treasury entries and role checks). Set provider keys through Firebase Functions secret management; never place them in the client application.

```text
cd functions
npm install
npm run build
firebase deploy --only firestore,functions
```

See [architecture](docs/ARCHITECTURE.md) and [deployment](docs/DEPLOYMENT.md) for collection models, boundaries, and operational steps.

## Demo accounts

All demo accounts use fake credentials and all financial values are sandbox values.

| Role | Email | Password |
| --- | --- | --- |
| Member | amina.demo@onejourney.local | DemoMember2026! |
| Provider | farhan.provider@onejourney.local | DemoProvider2026! |
| Committee | sara.committee@onejourney.local | DemoCommittee2026! |
| Community admin | bilal.admin@onejourney.local | DemoAdmin2026! |
| Auditor | huda.audit@onejourney.local | DemoAuditor2026! |
| Founder demo | founder.demo@onejourney.local | DemoFounder2026! |

The local login intentionally allows the password pattern only in Demo mode. Replace it with Firebase Authentication / passkey flows before using real users.

## Trust boundaries

- JARVIS can summarize and draft, but never determines an election result or moves funds.
- Votes and balances are only sandbox interactions in the local demo.
- Exact residential addresses and beneficiary data are not seeded or displayed.
- Critical records are appended or superseded rather than silently deleted.
- Country-level activity is labelled participatory/advisory unless legal authority is verified.
