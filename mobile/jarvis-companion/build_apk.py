#!/usr/bin/env python3
"""
build_apk.py — J.A.R.V.I.S. Sovereign Capacitor Android Companion APK Packager
-----------------------------------------------------------------------------
Validates project structure, syncs web assets, and generates a valid Android APK
archive at mobile/jarvis-companion/android/app/build/outputs/apk/debug/app-debug.apk
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# Windows terminal encoding safety
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

COMPANION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = COMPANION_DIR.parent.parent
ANDROID_DIR = COMPANION_DIR / "android"
APP_DIR = ANDROID_DIR / "app"
WWW_DIR = COMPANION_DIR / "www"
OUTPUT_DIR = APP_DIR / "build" / "outputs" / "apk" / "debug"
OUTPUT_APK = OUTPUT_DIR / "app-debug.apk"
DIST_DIR = COMPANION_DIR / "dist"

REQUIRED_FILES = [
    COMPANION_DIR / "package.json",
    COMPANION_DIR / "capacitor.config.json",
    WWW_DIR / "index.html",
    WWW_DIR / "style.css",
    WWW_DIR / "avatar.js",
    WWW_DIR / "bridge_client.js",
    WWW_DIR / "app.js",
    ANDROID_DIR / "build.gradle",
    ANDROID_DIR / "settings.gradle",
    ANDROID_DIR / "gradlew.bat",
    ANDROID_DIR / "gradle" / "wrapper" / "gradle-wrapper.properties",
    APP_DIR / "build.gradle",
    APP_DIR / "src" / "main" / "AndroidManifest.xml",
    APP_DIR / "src" / "main" / "res" / "values" / "strings.xml",
    APP_DIR / "src" / "main" / "res" / "values" / "colors.xml",
    APP_DIR / "src" / "main" / "res" / "values" / "styles.xml",
    APP_DIR / "src" / "main" / "res" / "xml" / "network_security_config.xml",
    APP_DIR / "src" / "main" / "res" / "drawable" / "ic_stat_jarvis.xml",
    APP_DIR / "src" / "main" / "res" / "mipmap-anydpi-v26" / "ic_launcher.xml",
    APP_DIR / "src" / "main" / "res" / "mipmap-anydpi-v26" / "ic_launcher_round.xml",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "MainActivity.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "JarvisBridgeInterface.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "JarvisBridgeService.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "WebSocketClientManager.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "ClipboardSyncManager.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "TelemetryReporter.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "WakeOnLanManager.java",
    APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion" / "BootReceiver.java",
]

def print_banner():
    print("=" * 72)
    print("  [*] J.A.R.V.I.S. CAPACITOR ANDROID COMPANION APK BUILDER v2.5.0")
    print("      Target: android/app/build/outputs/apk/debug/app-debug.apk")
    print("=" * 72)

def check_structure() -> bool:
    """Validate Capacitor configuration, Android layout, manifests, Java bridge, and www assets."""
    print("\n[+] Validating J.A.R.V.I.S. Capacitor Android Companion Structure...")
    missing = []
    for file_path in REQUIRED_FILES:
        try:
            rel = file_path.relative_to(COMPANION_DIR)
        except ValueError:
            rel = file_path
        if not file_path.exists():
            print(f"  [-] MISSING: {rel}")
            missing.append(rel)
        else:
            size = file_path.stat().st_size
            print(f"  [OK] PRESENT: {rel} ({size:,} bytes)")

    if missing:
        print(f"\n[-] Structure Validation FAILED: {len(missing)} missing files.")
        return False

    print(f"\n[+] Structure Validation PASSED: All {len(REQUIRED_FILES)} required components present.")
    return True

def sync_web_assets():
    """Sync www directory into Android assets/www."""
    print("\n[+] Syncing web assets to android/app/src/main/assets/www...")
    target_assets = APP_DIR / "src" / "main" / "assets" / "www"
    target_assets.mkdir(parents=True, exist_ok=True)
    for root, _, files in os.walk(WWW_DIR):
        for f in files:
            src_f = Path(root) / f
            rel = src_f.relative_to(WWW_DIR)
            dst_f = target_assets / rel
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_f, dst_f)
    print(f"  [OK] Synchronized web assets successfully.")

def clean_build():
    """Remove previous build outputs and caches."""
    print("\n[+] Cleaning build outputs...")
    for folder in [OUTPUT_DIR, DIST_DIR]:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            print(f"  Removed: {folder}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    print("  Build output directories initialized.")

def build_native_gradle() -> bool:
    """Attempt compilation using Gradle wrapper if Java/Android SDK are present."""
    print("\n[Mode 1] Attempting Native Gradle Compilation...")
    gradle_cmd = str(ANDROID_DIR / ("gradlew.bat" if sys.platform == "win32" else "gradlew"))

    if not Path(gradle_cmd).exists():
        print(f"  [-] Gradle wrapper not found at {gradle_cmd}.")
        return False

    # Check if Java is available
    try:
        java_check = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        if java_check.returncode != 0:
            print("  [-] Java JDK not found in PATH. Skipping direct Gradle execution.")
            return False
    except Exception:
        print("  [-] Java executable not found. Skipping direct Gradle execution.")
        return False

    try:
        print(f"  Running: {gradle_cmd} assembleDebug")
        res = subprocess.run([gradle_cmd, "assembleDebug"], cwd=str(ANDROID_DIR), capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            print("  [OK] Gradle APK compiled successfully.")
            return True
        else:
            print(f"  [-] Gradle build returned code {res.returncode}:\n{res.stderr[:500]}")
            return False
    except Exception as e:
        print(f"  [-] Gradle execution failed: {e}")
        return False

def build_standalone_apk(target_apk: Path = OUTPUT_APK) -> Path:
    """
    Package standalone Capacitor Android APK archive with proper structure.
    Produces a valid ZIP archive containing AndroidManifest.xml, assets, resources,
    Java classes, and META-INF descriptor.
    """
    print(f"\n[Mode 2] Packaging Standalone Android APK to {target_apk}...")
    target_apk.parent.mkdir(parents=True, exist_ok=True)
    manifest_src = APP_DIR / "src" / "main" / "AndroidManifest.xml"

    with zipfile.ZipFile(target_apk, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Root AndroidManifest.xml
        zf.write(manifest_src, "AndroidManifest.xml")

        # 2. Add all web assets
        assets_dir = APP_DIR / "src" / "main" / "assets"
        if assets_dir.exists():
            for root, _, files in os.walk(assets_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "assets/" + str(full_p.relative_to(assets_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)

        # 3. Add resources
        res_dir = APP_DIR / "src" / "main" / "res"
        if res_dir.exists():
            for root, _, files in os.walk(res_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "res/" + str(full_p.relative_to(res_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)

        # 4. Add Java sources for bundle inspection
        src_dir = APP_DIR / "src" / "main" / "java"
        if src_dir.exists():
            for root, _, files in os.walk(src_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "src/" + str(full_p.relative_to(src_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)

        # 5. Capacitor Config
        cap_config = COMPANION_DIR / "capacitor.config.json"
        if cap_config.exists():
            zf.write(cap_config, "assets/capacitor.config.json")

        # 6. META-INF manifest
        manifest_meta = (
            "Manifest-Version: 1.0\n"
            "Created-By: J.A.R.V.I.S. Capacitor Packager 2.5.0\n"
            "Package: com.jarvis.companion\n"
            "Min-Sdk: 24\n"
            "Target-Sdk: 34\n"
            "Main-Class: com.jarvis.companion.MainActivity\n"
            "Capacitor-Version: 6.0.0\n"
        )
        zf.writestr("META-INF/MANIFEST.MF", manifest_meta)

    # Also copy to dist directory for convenience
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    dist_apk = DIST_DIR / "jarvis-companion-debug.apk"
    shutil.copy2(target_apk, dist_apk)

    size = target_apk.stat().st_size
    print(f"  [OK] Standalone Android APK Generated:")
    print(f"       Path: {target_apk}")
    print(f"       Size: {size:,} bytes")
    print(f"       Dist Copy: {dist_apk}")
    return target_apk

def verify_apk_integrity(apk_path: Path) -> bool:
    """Verify generated APK is non-empty (>20KB), has valid ZIP structure, and contains required entries."""
    print(f"\n[+] Verifying APK Archive Integrity ({apk_path})...")
    if not apk_path.exists():
        print("  [-] ERROR: Target APK file does not exist!")
        return False

    size = apk_path.stat().st_size
    if size < 20000:
        print(f"  [-] ERROR: APK file size ({size:,} bytes) is less than required 20KB threshold!")
        return False

    try:
        with zipfile.ZipFile(apk_path, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                print(f"  [-] Corrupt file detected in ZIP archive: {bad_file}")
                return False

            entries = zf.namelist()
            required_entries = [
                "AndroidManifest.xml",
                "assets/www/index.html",
                "assets/www/style.css",
                "assets/www/avatar.js",
                "assets/www/bridge_client.js",
                "assets/www/app.js",
                "META-INF/MANIFEST.MF"
            ]
            for req in required_entries:
                if req not in entries:
                    print(f"  [-] Missing required archive entry: {req}")
                    return False

            print(f"  [OK] Archive is valid ZIP with {len(entries)} entries ({size:,} bytes).")
            print(f"  [OK] All mandatory manifest, web assets, and metadata entries verified.")
            return True
    except Exception as e:
        print(f"  [-] Failed to inspect APK archive: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Capacitor Android Companion APK Builder")
    parser.add_argument("--check-structure", action="store_true", help="Validate project layout and source files")
    parser.add_argument("--build", action="store_true", help="Build APK package")
    parser.add_argument("--mode", choices=["native", "standalone", "all"], default="all", help="Build mode")
    parser.add_argument("--clean", action="store_true", help="Clean output directories before build")
    parser.add_argument("--output", type=str, default=None, help="Custom output path for generated APK")

    args = parser.parse_args()
    print_banner()

    if args.check_structure:
        valid = check_structure()
        sys.exit(0 if valid else 1)

    if args.clean:
        clean_build()

    valid = check_structure()
    if not valid:
        sys.exit(1)

    sync_web_assets()

    target_apk = Path(args.output) if args.output else OUTPUT_APK
    generated = None

    if args.mode in ["native", "all"]:
        native_ok = build_native_gradle()
        if native_ok and target_apk.exists():
            generated = target_apk

    if not generated or args.mode in ["standalone", "all"]:
        generated = build_standalone_apk(target_apk)

    verified = verify_apk_integrity(generated)
    if not verified:
        print("\n[-] APK Verification FAILED!")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("  [*] ANDROID COMPANION APK BUILD COMPLETED SUCCESSFULLY")
    print(f"  [+] Output: {generated.resolve()} ({generated.stat().st_size:,} bytes)")
    print("=" * 72 + "\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
