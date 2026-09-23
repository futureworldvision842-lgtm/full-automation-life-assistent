# Deployment checklist

1. Create Firebase projects for development, staging and production. Enable Authentication providers deliberately, Firestore, Storage, Functions, App Check, Crashlytics and FCM.
2. Configure email verification and password-recovery templates. Do not enable phone OTP until regional compliance, rate limits and abuse handling are in place.
3. Store `GEMINI_API_KEY`, Ethereum RPC credentials and any feed keys as Firebase Functions secrets. Set client Firebase configuration through build-time environment values only.
4. Deploy rules and functions with the Firebase CLI. Run emulator tests against Firestore before any production deployment.
5. Create Android project with `npm run android:add`, set signing configuration in Android Studio/CI secrets, then run `npm run android:sync` and Gradle tests. Do not commit signing keys.
6. Complete a privacy impact assessment, terms, community constitution templates, moderator escalation policy and jurisdiction-specific financial/payments review before moving anything beyond Sandbox.
7. Configure backups, audit checkpoint monitoring, error alerts and security-event response. Test restore and device-revocation flows before a live pilot.

The demo seed is not production data. It includes no legal proof of community verification, state authority, or funding custody.
