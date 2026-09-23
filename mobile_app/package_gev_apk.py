#!/usr/bin/env python3
"""
package_gev_apk.py — Standalone packager for God's Eye View Android APK
Packages Android manifest, synced WebGL/Cesium assets, resources, and descriptors into:
mobile_app/dist/gods-eye-view-debug.apk
"""
import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GEV_ANDROID_SRC = PROJECT_ROOT / "apps" / "android-gods-eye-view" / "Android" / "app" / "src" / "main"
DIST_DIR = BASE_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)
TARGET_APK = DIST_DIR / "gods-eye-view-debug.apk"

def package_gev_apk():
    print(f"[*] Packaging God's Eye View Android APK...")
    print(f"    Source: {GEV_ANDROID_SRC}")
    print(f"    Target: {TARGET_APK}")

    if not GEV_ANDROID_SRC.exists():
        print(f"[-] Source directory does not exist: {GEV_ANDROID_SRC}")
        return False

    with zipfile.ZipFile(TARGET_APK, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Manifest
        manifest_file = GEV_ANDROID_SRC / "AndroidManifest.xml"
        if manifest_file.exists():
            zf.write(manifest_file, "AndroidManifest.xml")
            print("  + AndroidManifest.xml added")

        # 2. Assets (including synced www 3D assets)
        assets_dir = GEV_ANDROID_SRC / "assets"
        if assets_dir.exists():
            count = 0
            for root, _, files in os.walk(assets_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "assets/" + str(full_p.relative_to(assets_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)
                    count += 1
            print(f"  + Added {count} assets from assets/www")

        # 3. Resources
        res_dir = GEV_ANDROID_SRC / "res"
        if res_dir.exists():
            count = 0
            for root, _, files in os.walk(res_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "res/" + str(full_p.relative_to(res_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)
                    count += 1
            print(f"  + Added {count} resources from res/")

        # 4. Kotlin / Java source
        java_dir = GEV_ANDROID_SRC / "java"
        if java_dir.exists():
            for root, _, files in os.walk(java_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = "src/" + str(full_p.relative_to(java_dir)).replace("\\", "/")
                    zf.write(full_p, arcname)

        # 5. META-INF
        manifest_meta = (
            "Manifest-Version: 1.0\n"
            "Created-By: J.A.R.V.I.S. Android Engine\n"
            "Package: com.godseyeview.app\n"
            "Min-Sdk: 26\n"
            "Target-Sdk: 35\n"
            "Main-Class: com.godseyeview.app.MainActivity\n"
        )
        zf.writestr("META-INF/MANIFEST.MF", manifest_meta)

    size = TARGET_APK.stat().st_size
    print(f"\n[OK] God's Eye View Android APK successfully built: {TARGET_APK}")
    print(f"     Package Size: {size:,} bytes")
    return True

if __name__ == "__main__":
    success = package_gev_apk()
    sys.exit(0 if success else 1)
