"""
tests/test_mobile_pc_remote_panopticon.py — Test Suite for Bi-Directional Mobile & PC Remote Control
=====================================================================================================
Verifies:
1. Bi-Directional Screen Telemetry (PC desktop capture & dynamic Mobile SVG HUD mirror).
2. PC-to-Mobile Remote Control (touch tap, hardware keys, text typing, Wi-Fi ADB pairing).
3. Mobile-to-PC Remote Control (absolute desktop click_at, trackpad move, keyboard type/key).
4. CORS Middleware presence on Mobile Gateway (:8765).
5. Clean-room compliance and strict identity rule.
"""

import time
import pytest
from starlette.testclient import TestClient
from dashboard import app as dashboard_app
from mobile_control import app as mobile_app


def test_bi_directional_screen_telemetry():
    dash_client = TestClient(dashboard_app)
    mob_client = TestClient(mobile_app)

    # 1. Mobile sends live heartbeat
    heartbeat_resp = mob_client.post("/api/screen/mobile/heartbeat", json={
        "device_name": "Master Muhammad Sovereign Mobile",
        "active_tab": "tabPc",
        "battery_pct": 95,
        "charging": True,
        "orientation": "portrait",
        "resolution": "1080x2400",
        "last_touch_x": 540,
        "last_touch_y": 1200
    })
    assert heartbeat_resp.status_code == 200
    assert heartbeat_resp.json()["ok"] is True

    # 2. Check mobile status reflects heartbeat on dashboard
    status_resp = dash_client.get("/api/screen/mobile/status")
    assert status_resp.status_code == 200
    stat_data = status_resp.json()
    assert stat_data["ok"] is True
    assert stat_data["session"]["battery_pct"] == 95
    assert stat_data["session"]["charging"] is True

    # 3. Check dynamic SVG live screen mirror reflects battery and live state
    svg_resp = dash_client.get("/api/mobile/screen/live")
    assert svg_resp.status_code == 200
    assert svg_resp.headers["content-type"].startswith("image/svg+xml") or svg_resp.headers["content-type"].startswith("image/png")
    if "image/svg+xml" in svg_resp.headers["content-type"]:
        svg_text = svg_resp.text
        assert "95%" in svg_text
        assert "COMPANION PWA LIVE" in svg_text
        assert "Master: Muhammad Qureshi" in svg_text


def test_pc_to_mobile_remote_actions():
    client = TestClient(dashboard_app)

    # 1. Send touch tap
    tap_resp = client.post("/api/mobile/tap", json={"x": 540, "y": 1200})
    assert tap_resp.status_code == 200
    assert tap_resp.json()["ok"] is True
    assert tap_resp.json()["x"] == 540
    assert tap_resp.json()["y"] == 1200

    # 2. Send hardware key
    key_resp = client.post("/api/mobile/key", json={"key": "home"})
    assert key_resp.status_code == 200
    assert key_resp.json()["ok"] is True
    assert key_resp.json()["key"] == "home"

    # 3. Send text typing
    type_resp = client.post("/api/mobile/type", json={"text": "Hello Sovereign"})
    assert type_resp.status_code == 200
    assert type_resp.json()["ok"] is True
    assert type_resp.json()["text"] == "Hello Sovereign"

    # 4. Wi-Fi ADB pairing endpoint
    adb_resp = client.post("/api/mobile/adb/connect", json={"ip": "127.0.0.1", "port": 5555})
    assert adb_resp.status_code == 200
    assert "ok" in adb_resp.json()


def test_mobile_to_pc_remote_actions():
    client = TestClient(mobile_app)

    # 1. Desktop Click At (x, y)
    click_resp = client.post("/api/mouse/click_at", json={"x": 500, "y": 300, "button": "left"})
    assert click_resp.status_code == 200
    assert click_resp.json()["ok"] is True
    assert click_resp.json()["x"] == 500
    assert click_resp.json()["y"] == 300

    # 2. Touchpad Move
    move_resp = client.post("/api/mouse/move", json={"dx": 10, "dy": -5})
    assert move_resp.status_code == 200
    assert move_resp.json()["ok"] is True

    # 3. Keyboard Type
    type_resp = client.post("/api/keyboard/type", json={"text": "Test"})
    assert type_resp.status_code == 200

    # 4. Keyboard Key
    key_resp = client.post("/api/keyboard/key", json={"key": "shift"})
    assert key_resp.status_code == 200


def test_cors_headers_on_mobile_gateway():
    client = TestClient(mobile_app)
    # Check that OPTIONS / pre-flight or CORS header is enabled
    resp = client.get("/api/health", headers={"Origin": "http://127.0.0.1:8770"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_clean_room_invariance():
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent
    check_files = [
        base / "core" / "screen_mirror_router.py",
        base / "actions" / "android_automation.py",
        base / "dashboard.py",
        base / "mobile_control.py"
    ]
    prohibited = ["adeel" + chr(95) + "qureshi99", "adeel" + chr(45) + "qureshi99"]
    for f in check_files:
        if f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            for p in prohibited:
                assert p not in content, f"Prohibited token {p} found in {f.name}"
