# J.A.R.V.I.S. Sovereign Android Mobile Companion

The 24/7 standalone mobile command hub for the J.A.R.V.I.S. Sovereign Fleet, packaged with Capacitor for Android.

## Architecture
- **Framework**: Capacitor 6.0 (`@capacitor/core`, `@capacitor/cli`, `@capacitor/android`).
- **Target App ID**: `com.jarvis.companion`
- **Native Android Project**: `mobile/jarvis-companion/android/`
- **Web Frontend**: `mobile/jarvis-companion/www/`
  - `avatar.js`: Interactive HTML5 Canvas cybernetic J.A.R.V.I.S. avatar / Arc Reactor HUD with 4 dynamic operational states (`idle`, `listening`, `thinking`, `speaking`), harmonic frequency waves, and particle constellation.
  - `bridge_client.js`: Sub-50ms WebSocket client connecting to `ws://<host>:8765/ws/mobile` with PING/PONG RTT telemetry, remote command dispatch, and push notification receiver.
  - `app.js`: Core controller managing bilingual Roman Urdu & English voice interaction (Web Speech API), real-time desktop screen stream viewer (`/api/screen/stream`), and PowerShell terminal emulator.
  - `style.css`: High-fidelity Iron Man / Palantir HUD aesthetic with glowing cyan/green accents and glassmorphism.

## Compilation & Packaging
To check project structure:
```bash
python mobile/jarvis-companion/build_apk.py --check-structure
```

To build and compile the Android APK:
```bash
python mobile/jarvis-companion/build_apk.py --build --clean
```

Generated APK Output:
`mobile/jarvis-companion/android/app/build/outputs/apk/debug/app-debug.apk`
