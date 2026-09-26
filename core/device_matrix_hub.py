"""
core/device_matrix_hub.py — Universal Sovereign Device Matrix & Satellite Hub
=============================================================================
Manages multi-device enrollment, real-time bidirectional telemetry, live screen
streaming (Mobile -> PC), GPS geo-tracking, and full-duplex voice dispatching
(PC -> Phone speaker / Phone mic -> Jarvis).
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DEVICES_REGISTRY_FILE = RUNTIME_DIR / "devices_fleet_registry.json"
SCREENS_DIR = RUNTIME_DIR / "device_screens"
SCREENS_DIR.mkdir(parents=True, exist_ok=True)
CAMERAS_DIR = RUNTIME_DIR / "device_cameras"
CAMERAS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_OWNER_NAME = "Master Muhammad Qureshi"
DEFAULT_OWNER_PHONE = "+923468053268"
DEFAULT_OWNER_EMAIL = "futureworldvision842@gmail.com"


class DeviceMatrixHub:
    """Central engine managing enrolled satellite devices (mobiles, tablets, workstations)."""

    def __init__(self):
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._command_queues: Dict[str, List[Dict[str, Any]]] = {}
        self._last_loaded_mtime: float = 0.0
        self._load_registry()

    def _ensure_fresh_registry(self) -> None:
        if DEVICES_REGISTRY_FILE.exists():
            try:
                mtime = DEVICES_REGISTRY_FILE.stat().st_mtime
                if mtime > self._last_loaded_mtime:
                    self._load_registry()
            except Exception:
                pass

    def _load_registry(self) -> None:
        if DEVICES_REGISTRY_FILE.exists():
            try:
                self._last_loaded_mtime = DEVICES_REGISTRY_FILE.stat().st_mtime
                data = json.loads(DEVICES_REGISTRY_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._devices = data.get("devices", {})
            except Exception:
                self._devices = {}

        # Ensure default Master Mobile is always present
        if "default_mobile" not in self._devices:
            self._devices["default_mobile"] = {
                "device_id": "default_mobile",
                "device_name": "Master Muhammad Galaxy Ultra",
                "device_type": "mobile_phone",
                "token": "wHUfdgY-AdHQZMb93xK5ZB-uNeYoXrQ_0p7RgTgnAhE",
                "enrolled_at": time.time(),
                "last_seen": time.time(),
                "online": True,
                "battery": {"pct": 92, "charging": True},
                "gps": {
                    "lat": 24.8607,
                    "lon": 67.0011,
                    "accuracy": 12.5,
                    "altitude": 15.0,
                    "speed": 0.0,
                    "heading": 0.0,
                    "timestamp": time.time(),
                    "maps_url": "https://maps.google.com/?q=24.8607,67.0011"
                },
                "screen_sharing": {
                    "active": False,
                    "last_frame_at": None,
                    "fps": 0,
                    "resolution": "1080x2400"
                },
                "audio_duplex": {
                    "speaker_active": True,
                    "mic_active": True,
                    "last_spoken": "Assalam-o-Alaikum Sir, J.A.R.V.I.S. is ready."
                },
                "capabilities": ["screen_share", "gps_tracking", "speaker_duplex", "mic_input", "vibrate", "alarm"],
                "owner": DEFAULT_OWNER_NAME
            }
            self._save_registry()

    def _save_registry(self) -> None:
        try:
            payload = {
                "updated_at": time.time(),
                "owner": DEFAULT_OWNER_NAME,
                "devices": self._devices
            }
            DEVICES_REGISTRY_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def generate_enrollment_link(
        self,
        device_name: str = "Master Muhammad Satellite Device",
        device_type: str = "mobile_phone",
        capabilities: Optional[List[str]] = None,
        lan_ip: str = "192.168.100.3",
        port: int = 8765
    ) -> Dict[str, Any]:
        """Generates an instant 1-tap onboarding link + token for any phone/tablet/laptop."""
        clean_name = (device_name or "Mobile_Device").strip()
        device_id = f"dev_{secrets.token_hex(4)}"
        token = f"jnode_{secrets.token_urlsafe(24)}"
        caps = capabilities or ["screen_share", "gps_tracking", "speaker_duplex", "mic_input", "vibrate", "alarm"]

        new_device = {
            "device_id": device_id,
            "device_name": clean_name,
            "device_type": device_type,
            "token": token,
            "enrolled_at": time.time(),
            "last_seen": time.time(),
            "online": False,
            "battery": {"pct": 100, "charging": False},
            "gps": {
                "lat": None,
                "lon": None,
                "accuracy": None,
                "altitude": None,
                "speed": 0.0,
                "heading": 0.0,
                "timestamp": None,
                "maps_url": None
            },
            "screen_sharing": {
                "active": False,
                "last_frame_at": None,
                "fps": 0,
                "resolution": "Unknown"
            },
            "audio_duplex": {
                "speaker_active": True,
                "mic_active": True,
                "last_spoken": None
            },
            "capabilities": caps,
            "owner": DEFAULT_OWNER_NAME
        }

        self._devices[device_id] = new_device
        self._command_queues[device_id] = []
        self._save_registry()

        enroll_url = f"http://{lan_ip}:{port}/enroll?id={device_id}&token={token}&name={clean_name}"
        qr_svg = self._make_qr_svg(enroll_url)

        return {
            "ok": True,
            "device_id": device_id,
            "device_name": clean_name,
            "device_type": device_type,
            "token": token,
            "enroll_url": enroll_url,
            "qr_svg": qr_svg,
            "instructions": f"Open this link on {clean_name} or scan the QR code to grant J.A.R.V.I.S. live access."
        }

    def _make_qr_svg(self, data_str: str) -> str:
        """Generates an embedded standalone SVG QR code."""
        try:
            import qrcode
            import qrcode.image.svg
            import io
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
                image_factory=qrcode.image.svg.SvgPathImage
            )
            qr.add_data(data_str)
            qr.make(fit=True)
            img = qr.make_image()
            stream = io.BytesIO()
            img.save(stream)
            return stream.getvalue().decode("utf-8")
        except Exception:
            # Fallback simple SVG representation
            return f'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220"><rect width="220" height="220" fill="#030811"/><text x="110" y="110" fill="#00f0ff" font-size="12" text-anchor="middle">QR: {data_str[:30]}...</text></svg>'

    def update_device_telemetry(self, device_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests live telemetry from an enrolled device (GPS, battery, screen state, orientation)."""
        self._ensure_fresh_registry()
        dev = self._devices.get(device_id)
        if not dev:
            # Fallback to default_mobile if unmatched
            dev = self._devices.get("default_mobile")
            device_id = "default_mobile"

        now = time.time()
        dev["last_seen"] = now
        dev["online"] = True

        if "battery" in telemetry:
            dev["battery"] = {
                "pct": telemetry["battery"].get("pct", dev["battery"].get("pct", 88)),
                "charging": telemetry["battery"].get("charging", dev["battery"].get("charging", False))
            }
        elif "battery_pct" in telemetry:
            dev["battery"] = {
                "pct": telemetry.get("battery_pct", dev["battery"].get("pct", 88)),
                "charging": telemetry.get("charging", dev["battery"].get("charging", False))
            }

        if "gps" in telemetry:
            g = telemetry["gps"]
            lat = g.get("lat") or g.get("latitude")
            lon = g.get("lon") or g.get("longitude")
            maps_url = f"https://maps.google.com/?q={lat},{lon}" if lat and lon else dev["gps"].get("maps_url")
            dev["gps"] = {
                "lat": lat if lat is not None else dev["gps"].get("lat"),
                "lon": lon if lon is not None else dev["gps"].get("lon"),
                "accuracy": g.get("accuracy", dev["gps"].get("accuracy")),
                "altitude": g.get("altitude", dev["gps"].get("altitude")),
                "speed": g.get("speed", dev["gps"].get("speed", 0.0)),
                "heading": g.get("heading", dev["gps"].get("heading", 0.0)),
                "timestamp": now,
                "maps_url": maps_url
            }

        if "screen_sharing" in telemetry:
            ss = telemetry["screen_sharing"]
            dev["screen_sharing"].update(ss)

        if "device_name" in telemetry and telemetry["device_name"]:
            dev["device_name"] = telemetry["device_name"]

        self._save_registry()

        # Check if there are pending commands to return to the device
        pending_commands = self._command_queues.get(device_id, [])
        self._command_queues[device_id] = []

        return {
            "ok": True,
            "device_id": device_id,
            "acknowledged_at": now,
            "commands": pending_commands
        }

    def save_screen_frame(self, device_id: str, image_bytes: bytes) -> bool:
        """Saves a live screen frame transmitted from the mobile device to the PC."""
        target = SCREENS_DIR / f"{device_id}_screen.jpg"
        default_target = SCREENS_DIR / "latest_mobile_screen.jpg"
        try:
            target.write_bytes(image_bytes)
            default_target.write_bytes(image_bytes)
            dev = self._devices.get(device_id)
            if dev:
                dev["screen_sharing"]["active"] = True
                dev["screen_sharing"]["last_frame_at"] = time.time()
                self._save_registry()
            return True
        except Exception:
            return False

    def get_latest_screen_frame(self, device_id: str = "default_mobile") -> Optional[bytes]:
        """Returns the latest screen frame captured from the specified mobile device."""
        target = SCREENS_DIR / f"{device_id}_screen.jpg"
        if not target.exists():
            target = SCREENS_DIR / "latest_mobile_screen.jpg"

        if target.exists() and (time.time() - target.stat().st_mtime < 120):
            try:
                return target.read_bytes()
            except Exception:
                pass
        return None

    def save_camera_frame(self, device_id: str, image_bytes: bytes) -> bool:
        """Saves a live camera vision frame transmitted from the mobile device to the PC."""
        target = CAMERAS_DIR / f"{device_id}_camera.jpg"
        default_target = CAMERAS_DIR / "latest_mobile_camera.jpg"
        try:
            target.write_bytes(image_bytes)
            default_target.write_bytes(image_bytes)
            dev = self._devices.get(device_id)
            if dev:
                if "camera" not in dev:
                    dev["camera"] = {}
                dev["camera"]["active"] = True
                dev["camera"]["last_frame_at"] = time.time()
                self._save_registry()
            return True
        except Exception:
            return False

    def get_latest_camera_frame(self, device_id: str = "default_mobile") -> Optional[bytes]:
        """Returns the latest camera frame captured from the specified mobile device."""
        target = CAMERAS_DIR / f"{device_id}_camera.jpg"
        if not target.exists():
            target = CAMERAS_DIR / "latest_mobile_camera.jpg"

        if target.exists() and (time.time() - target.stat().st_mtime < 120):
            try:
                return target.read_bytes()
            except Exception:
                pass
        return None

    def queue_command(self, device_id: str, cmd_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queues a remote command to be executed by the target device."""
        self._ensure_fresh_registry()
        packet = {
            "command_id": f"cmd_{secrets.token_hex(4)}",
            "type": cmd_type.upper().strip(),
            "payload": payload or {},
            "timestamp": time.time()
        }
        if device_id not in self._command_queues:
            self._command_queues[device_id] = []
        self._command_queues[device_id].append(packet)

        # Update last spoken if speaking
        if cmd_type.upper() == "SPEAK":
            dev = self._devices.get(device_id)
            if dev:
                dev["audio_duplex"]["last_spoken"] = (payload or {}).get("text", "")
                self._save_registry()

        return {"ok": True, "queued": packet}

    def list_fleet(self) -> List[Dict[str, Any]]:
        """Returns all enrolled satellite devices with online/offline status."""
        self._ensure_fresh_registry()
        now = time.time()
        result = []
        for dev_id, dev in self._devices.items():
            is_online = (now - dev.get("last_seen", 0)) < 90
            item = dict(dev)
            item["online"] = is_online
            item["seconds_since_last_seen"] = round(now - dev.get("last_seen", 0), 1)
            result.append(item)
        return result


# Singleton accessor
_hub_instance: Optional[DeviceMatrixHub] = None

def get_device_matrix_hub() -> DeviceMatrixHub:
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = DeviceMatrixHub()
    return _hub_instance
