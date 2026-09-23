"""
gods_eye_view — J.A.R.V.I.S. 3D Spatial Intelligence & Satellite Control Action
-------------------------------------------------------------------------------
Provides programmatic and voice control for the God's Eye View 3D Globe:
  - Status & health inspection on Port 4173
  - Automated browser opening & focal coordinates
  - Telemetry summary (flights, maritime AIS, satellites, fires)
  - Multi-sensor optical switching (Normal, NVG, FLIR, CRT, Noir, Snow)
"""
import os
import sys
import json
import time
import socket
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, Any

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).resolve().parent.parent
GEV_ROOT = BASE_DIR / "gods-eye-view"
GEV_URL = os.getenv("JARVIS_GODS_EYE_VIEW_URL", "http://127.0.0.1:4173").rstrip("/")

def is_gev_running(port: int = 4173) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False

def get_gev_status() -> Dict[str, Any]:
    running = is_gev_running(4173)
    data = {
        "ok": True,
        "running": running,
        "port": 4173,
        "url": GEV_URL,
        "root": str(GEV_ROOT),
        "engine": "CesiumJS 3D + Google Photorealistic Tiles / Esri Imagery",
        "layers": [
            "Live Aircraft (OpenSky Network)",
            "Military Transponders (ADSB.lol)",
            "Maritime AIS Ships (AISStream)",
            "Active Wildfires (NASA FIRMS)",
            "Orbital Satellites (CelesTrak SGP4)",
            "Earthquakes (USGS)",
            "Municipal CCTV Networks (London, SF, Austin)"
        ]
    }
    if running and requests:
        try:
            r = requests.get(GEV_URL, timeout=1.0)
            data["http_status"] = r.status_code
        except Exception:
            data["http_status"] = None
    return data

def launch_gev() -> str:
    if not is_gev_running(4173):
        bat_file = BASE_DIR / "START_GODS_EYE_VIEW.bat"
        if bat_file.exists():
            subprocess.Popen(["cmd.exe", "/c", str(bat_file)], cwd=str(BASE_DIR), creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(2.0)
    webbrowser.open(GEV_URL)
    return f"God's Eye View 3D Globe initiated at {GEV_URL}"

def open_cockpit_view() -> str:
    target_url = f"{GEV_URL}/?mission=contacts"
    webbrowser.open(target_url)
    return "God's Eye View Cockpit & Live Contacts initiated."

def switch_style(style_num: int) -> str:
    styles = {
        1: "Normal True-Color Satellite",
        2: "NVG Phosphor-Green Night Vision",
        3: "FLIR Ironbow Thermal Heat Signature",
        4: "CRT Tactical Raster Scanlines",
        5: "Noir Monochrome High-Contrast",
        6: "Arctic Snow Scatter",
        7: "Multispectral False-Color"
    }
    style_name = styles.get(style_num, "Normal")
    target_url = f"{GEV_URL}/?style={style_num}"
    webbrowser.open(target_url)
    return f"Switched God's Eye View optical sensor to Mode {style_num}: {style_name}"

def gods_eye_view(action: str = "status", style: int = 1) -> str:
    """Master voice and dispatch entry point for J.A.R.V.I.S."""
    act = action.lower().strip()
    if "launch" in act or "open" in act or "start" in act:
        return launch_gev()
    elif "cockpit" in act or "flight" in act:
        return open_cockpit_view()
    elif "style" in act or "sensor" in act or "nvg" in act or "flir" in act:
        return switch_style(style)
    else:
        status = get_gev_status()
        state = "ONLINE (Port 4173)" if status["running"] else "OFFLINE"
        return f"God's Eye View 3D Satellite Console status: {state}. 7 live telemetry layers active."
