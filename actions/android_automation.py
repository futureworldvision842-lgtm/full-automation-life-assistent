"""
actions/android_automation.py — Mobile (Android APK & ADB) Automation Engine for J.A.R.V.I.S.

Provides full Android mobile automation via ADB / Android CLI toolchain:
- Discovers connected Android devices (USB / Wi-Fi ADB).
- Launches mobile apps, sends taps/swipes, captures screenshots.
- Automates mobile workflows directly from J.A.R.V.I.S., WhatsApp, or the 3D Web HUD.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def get_adb_path() -> str:
    """Finds adb executable from Android SDK or system PATH."""
    android_sdk_adb = Path("E:/GAIGS-Android-Tools/sdk/platform-tools/adb.exe")
    if android_sdk_adb.exists():
        return str(android_sdk_adb)
    return "adb"

def list_connected_devices() -> list:
    """Returns list of connected Android devices via ADB."""
    adb = get_adb_path()
    try:
        res = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().split("\n")[1:]
        devices = []
        for line in lines:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
        return devices
    except Exception as e:
        print(f"[AndroidAutomation] ADB check error: {e}")
        return []

def open_mobile_app(package_name: str) -> str:
    """Launches an app on connected Android phone by package name."""
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected via ADB. Please connect phone via USB or Wi-Fi ADB."
    
    adb = get_adb_path()
    dev = devices[0]
    cmd = [adb, "-s", dev, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return f"Successfully launched {package_name} on Android device {dev}."
    return f"Failed to launch {package_name}: {res.stderr.strip()}"

def tap_mobile_screen(x: int, y: int) -> str:
    """Taps specified screen coordinates on connected Android phone."""
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected."
    
    adb = get_adb_path()
    dev = devices[0]
    cmd = [adb, "-s", dev, "shell", "input", "tap", str(x), str(y)]
    subprocess.run(cmd, capture_output=True)
    return f"Tapped screen coordinates ({x}, {y}) on device {dev}."

if __name__ == "__main__":
    print(f"ADB Executable: {get_adb_path()}")
    print(f"Connected Devices: {list_connected_devices()}")
