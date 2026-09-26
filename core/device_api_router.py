"""
core/device_api_router.py — FastAPI Router for Universal Multi-Device Enrollment & Telemetry
=============================================================================================
Provides:
1. /api/devices/generate-enroll-link: Create instant QR & onboarding links for any phone/tablet.
2. /api/devices/fleet: Full telemetry of all enrolled devices (GPS, battery, screen status).
3. /api/devices/{id}/telemetry: Ingest GPS location, battery, and orientation from devices.
4. /api/devices/{id}/screen-frame: Bidirectional mobile screen streaming (Phone -> PC).
5. /api/devices/{id}/speak: Speak text out loud through the phone's speaker.
6. /api/devices/{id}/command: Dispatch vibration, alarm, or open URL.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.device_matrix_hub import get_device_matrix_hub

device_router = APIRouter(prefix="/api/devices", tags=["device_matrix"])


class GenerateEnrollLinkRequest(BaseModel):
    device_name: Optional[str] = "Master Muhammad Satellite Phone"
    device_type: Optional[str] = "mobile_phone"
    capabilities: Optional[List[str]] = None
    lan_ip: Optional[str] = "192.168.100.3"
    port: Optional[int] = 8765


class DeviceTelemetryRequest(BaseModel):
    device_name: Optional[str] = None
    battery_pct: Optional[int] = None
    charging: Optional[bool] = None
    gps: Optional[Dict[str, Any]] = None
    screen_sharing: Optional[Dict[str, Any]] = None
    orientation: Optional[str] = None


class DeviceSpeakRequest(BaseModel):
    text: str = Field(..., description="Text for the phone speaker to pronounce in Roman Urdu or English")
    lang: Optional[str] = "ur"
    volume: Optional[float] = 1.0


class DeviceCommandRequest(BaseModel):
    command: str = Field(..., description="'SPEAK', 'VIBRATE', 'ALARM', 'OPEN_URL', 'NOTIFICATION'")
    payload: Optional[Dict[str, Any]] = None


@device_router.post("/generate-enroll-link")
async def api_generate_enroll_link(req: GenerateEnrollLinkRequest) -> Dict[str, Any]:
    """Generates an instant QR code and 1-tap onboarding URL for any mobile device."""
    hub = get_device_matrix_hub()
    res = hub.generate_enrollment_link(
        device_name=req.device_name or "Master Muhammad Satellite Device",
        device_type=req.device_type or "mobile_phone",
        capabilities=req.capabilities,
        lan_ip=req.lan_ip or "192.168.100.3",
        port=req.port or 8765
    )
    return res


@device_router.get("/fleet")
async def api_get_device_fleet() -> Dict[str, Any]:
    """Returns all active, paired, and satellite devices with live telemetry."""
    hub = get_device_matrix_hub()
    fleet = hub.list_fleet()
    online_count = sum(1 for d in fleet if d.get("online"))
    return {
        "ok": True,
        "total_devices": len(fleet),
        "online_count": online_count,
        "fleet": fleet
    }


@device_router.post("/{device_id}/telemetry")
async def api_post_device_telemetry(device_id: str, req: DeviceTelemetryRequest) -> Dict[str, Any]:
    """Ingests live GPS, battery, and status telemetry from a connected phone."""
    hub = get_device_matrix_hub()
    payload: Dict[str, Any] = {}
    if req.battery_pct is not None:
        payload["battery_pct"] = req.battery_pct
    if req.charging is not None:
        payload["charging"] = req.charging
    if req.gps is not None:
        payload["gps"] = req.gps
    if req.screen_sharing is not None:
        payload["screen_sharing"] = req.screen_sharing
    if req.device_name:
        payload["device_name"] = req.device_name

    return hub.update_device_telemetry(device_id, payload)


@device_router.post("/{device_id}/screen-frame")
async def api_upload_screen_frame(device_id: str, frame: UploadFile = File(...)) -> Dict[str, Any]:
    """Receives a live screen frame (JPEG/PNG) streamed from the mobile device to the PC."""
    hub = get_device_matrix_hub()
    data = await frame.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty frame data")
    ok = hub.save_screen_frame(device_id, data)
    return {"ok": ok, "device_id": device_id, "size_bytes": len(data), "timestamp": time.time()}


@device_router.post("/{device_id}/screen-frame/base64")
async def api_upload_screen_frame_b64(device_id: str, req: Dict[str, Any]) -> Dict[str, Any]:
    """Receives base64-encoded screen snapshot directly from phone Canvas/MediaStream."""
    hub = get_device_matrix_hub()
    b64_data = req.get("image") or req.get("data") or req.get("frame") or ""
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    try:
        raw_bytes = base64.b64decode(b64_data)
        if not raw_bytes:
            return {"ok": False, "error": "Empty payload"}
        ok = hub.save_screen_frame(device_id, raw_bytes)
        return {"ok": ok, "device_id": device_id, "size_bytes": len(raw_bytes), "timestamp": time.time()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@device_router.get("/{device_id}/screen-frame")
async def api_get_screen_frame(device_id: str) -> Response:
    """Returns the latest screen frame received from the phone so the PC Dashboard can display it."""
    hub = get_device_matrix_hub()
    frame_bytes = hub.get_latest_screen_frame(device_id)

    transparent_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    if not frame_bytes:
        return Response(content=transparent_png, media_type="image/png")

    # Determine image type
    if frame_bytes.startswith(b"\xff\xd8"):
        media_type = "image/jpeg"
    else:
        media_type = "image/png"

    return Response(
        content=frame_bytes,
        media_type=media_type,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@device_router.post("/{device_id}/speak")
async def api_device_speak(device_id: str, req: DeviceSpeakRequest) -> Dict[str, Any]:
    """Tells the target phone to speak text aloud through its speaker via TTS."""
    hub = get_device_matrix_hub()
    return hub.queue_command(device_id, "SPEAK", {
        "text": req.text,
        "lang": req.lang or "ur",
        "volume": req.volume or 1.0
    })


@device_router.post("/{device_id}/command")
async def api_device_command(device_id: str, req: DeviceCommandRequest) -> Dict[str, Any]:
    """Dispatches a remote command to the target phone (vibration, alarm, URL open)."""
    hub = get_device_matrix_hub()
    return hub.queue_command(device_id, req.command, req.payload or {})
