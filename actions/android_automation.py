"""
actions/android_automation.py — Mobile (Android APK & ADB) Automation Engine for J.A.R.V.I.S.
=============================================================================================
Provides full Android mobile automation via ADB / Android CLI toolchain and WebSocket bridge:
- Discovers connected Android devices (USB / Wi-Fi ADB).
- Launches mobile apps, sends taps/swipes, captures screenshots.
- Controls hardware keys (Volume, Power, Home, Back).
- Ingests battery, network, and device telemetry.
- Connects phone and PC into a single unified sovereign ecosystem ("Donoun Aik Houn").
"""

import os
import sys
import json
import subprocess
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional, Any

BASE = Path(__file__).resolve().parent.parent

COMMON_APP_PACKAGES = {
    "whatsapp": "com.whatsapp",
    "chrome": "com.android.chrome",
    "browser": "com.android.chrome",
    "camera": "com.android.camera",
    "youtube": "com.google.android.youtube",
    "settings": "com.android.settings",
    "gallery": "com.google.android.apps.photos",
    "photos": "com.google.android.apps.photos",
    "mt5": "net.metaquotes.metatrader5",
    "metatrader": "net.metaquotes.metatrader5",
    "binance": "com.binance.dev",
    "telegram": "org.telegram.messenger",
    "jarvis": "com.jarvis.companion",
    "gaigs": "com.gaigs.governance"
}

def get_adb_path() -> str:
    """Finds adb executable from system PATH or common Android SDK directories."""
    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb
    
    candidates = [
        Path("E:/GAIGS-Android-Tools/sdk/platform-tools/adb.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
        Path("C:/Android/sdk/platform-tools/adb.exe"),
        Path("D:/Android/sdk/platform-tools/adb.exe")
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "adb"

def list_connected_devices() -> List[str]:
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
        return []

def connect_wifi_adb(ip: str = "192.168.100.5", port: int = 5555) -> Dict[str, Any]:
    """Connects to an Android phone over Wi-Fi ADB without needing a USB cable."""
    adb = get_adb_path()
    target = f"{ip}:{port}"
    try:
        res = subprocess.run([adb, "connect", target], capture_output=True, text=True, timeout=8)
        out = res.stdout.strip()
        ok = "connected to" in out.lower()
        return {"ok": ok, "target": target, "output": out}
    except Exception as e:
        return {"ok": False, "target": target, "error": str(e)}

def open_mobile_app(package_or_alias: str) -> str:
    """Launches an app on connected Android phone by alias or package name."""
    pkg = COMMON_APP_PACKAGES.get(package_or_alias.lower(), package_or_alias)
    devices = list_connected_devices()
    if not devices:
        # Fallback to dispatching launch via Mobile Control WebSocket
        try:
            import requests
            r = requests.post("http://127.0.0.1:8765/api/mobile/launch-app", json={"package_name": pkg, "app": package_or_alias}, timeout=2)
            if r.status_code == 200:
                return f"Dispatched launch intent for {package_or_alias} ({pkg}) to mobile companion."
        except Exception:
            pass
        return f"No Android device connected via ADB. Please connect phone or launch companion app."
    
    adb = get_adb_path()
    dev = devices[0]
    cmd = [adb, "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
    if res.returncode == 0:
        return f"Successfully launched {pkg} on Android device {dev}."
    return f"Failed to launch {pkg}: {res.stderr.strip()}"

def tap_mobile_screen(x: int, y: int) -> str:
    """Taps specified screen coordinates on connected Android phone."""
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected."
    adb = get_adb_path()
    dev = devices[0]
    cmd = [adb, "-s", dev, "shell", "input", "tap", str(x), str(y)]
    subprocess.run(cmd, capture_output=True, timeout=5)
    return f"Tapped screen coordinates ({x}, {y}) on device {dev}."

def swipe_mobile_screen(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipes across screen coordinates on connected Android phone."""
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected."
    adb = get_adb_path()
    dev = devices[0]
    cmd = [adb, "-s", dev, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
    subprocess.run(cmd, capture_output=True, timeout=5)
    return f"Swiped from ({x1}, {y1}) to ({x2}, {y2}) on device {dev}."

def send_mobile_key(key_action: str) -> str:
    """Sends Android key event: home, back, volume_up, volume_down, power, wake."""
    key_map = {
        "home": "3",
        "back": "4",
        "volume_up": "24",
        "volume_down": "25",
        "power": "26",
        "camera": "27",
        "menu": "82",
        "wake": "224"
    }
    code = key_map.get(key_action.lower(), key_action)
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected via ADB."
    adb = get_adb_path()
    dev = devices[0]
    subprocess.run([adb, "-s", dev, "shell", "input", "keyevent", str(code)], capture_output=True, timeout=5)
    return f"Dispatched keyevent {key_action} ({code}) to device {dev}."

def type_mobile_text(text: str) -> str:
    """Types text directly into the focused field on connected Android phone."""
    devices = list_connected_devices()
    if not devices:
        return "No Android device connected via ADB."
    adb = get_adb_path()
    dev = devices[0]
    safe_text = text.replace(" ", "%s")
    subprocess.run([adb, "-s", dev, "shell", "input", "text", safe_text], capture_output=True, timeout=5)
    return f"Typed text into Android device {dev}."

def capture_mobile_screen(dest_path: Optional[Path] = None) -> Dict[str, Any]:
    """Captures phone screen using ADB and saves it to local disk."""
    devices = list_connected_devices()
    if not devices:
        return {"ok": False, "error": "No Android device connected via ADB."}
    
    if not dest_path:
        dest_path = BASE / "scratch" / "mobile_screen.png"
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    adb = get_adb_path()
    dev = devices[0]
    try:
        proc = subprocess.run([adb, "-s", dev, "exec-out", "screencap", "-p"], capture_output=True, timeout=6)
        if proc.returncode == 0 and proc.stdout:
            dest_path.write_bytes(proc.stdout)
            return {"ok": True, "path": str(dest_path), "bytes": len(proc.stdout)}
        return {"ok": False, "error": proc.stderr.decode("utf-8", errors="ignore")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_mobile_battery() -> Dict[str, Any]:
    """Retrieves live battery telemetry from connected Android device."""
    devices = list_connected_devices()
    if not devices:
        # Fallback to Gateway telemetry
        try:
            import requests
            r = requests.get("http://127.0.0.1:8765/api/mobile/telemetry", timeout=1.5)
            if r.status_code == 200:
                return r.json().get("telemetry", {"level": "unknown"})
        except Exception:
            pass
        return {"level": "unknown", "connected": False}
    
    adb = get_adb_path()
    dev = devices[0]
    try:
        res = subprocess.run([adb, "-s", dev, "shell", "dumpsys", "battery"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().splitlines()
        info = {"device": dev, "connected": True}
        for l in lines:
            if ":" in l:
                k, v = l.split(":", 1)
                info[k.strip().lower()] = v.strip()
        return info
    except Exception as e:
        return {"error": str(e), "connected": False}

def install_apk_on_device(apk_path: str) -> Dict[str, Any]:
    """Installs an APK directly onto connected phone via ADB."""
    devices = list_connected_devices()
    if not devices:
        return {"ok": False, "error": "No Android device connected via ADB."}
    adb = get_adb_path()
    dev = devices[0]
    try:
        res = subprocess.run([adb, "-s", dev, "install", "-r", apk_path], capture_output=True, text=True, timeout=45)
        return {"ok": "Success" in res.stdout, "output": res.stdout.strip() or res.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    print(f"ADB Executable: {get_adb_path()}")
    print(f"Connected Devices: {list_connected_devices()}")
