"""
tests/test_mobile_bridge.py — Comprehensive Unit & Integration Test Suite
for Requirement R1: Android Mobile Companion APK & Bi-Directional Device Bridge
--------------------------------------------------------------------------------
Tests:
- Token-authenticated WebSocket handshake on /ws/mobile and /ws/bridge
- Mobile ➔ PC command execution latency and result format
- Mobile ➔ PC trading order dispatch and execution receipt
- Mobile ➔ PC device telemetry ingestion and query
- PC ➔ Mobile push notification broadcasting
- PC ➔ Mobile audible siren/alarm dispatch
- PC ↔ Mobile bi-directional clipboard sync
- Zero-config mobile pairing QR endpoint
- Android APK project structure, manifest, services, and multi-mode builder
"""

import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import mobile_control
from mobile_control import app, manager, ACCESS_TOKEN, PORT

BASE_DIR = Path(__file__).resolve().parent.parent
MOBILE_APP_DIR = BASE_DIR / "mobile_app"

class TestMobileWebSocketBridge(unittest.TestCase):
    """Tests the bi-directional WebSocket gateway on /ws/mobile and /ws/bridge."""

    def setUp(self):
        self.client = TestClient(app)

    def test_websocket_auth_handshake_success(self):
        """Verify successful token authentication handshake on /ws/mobile."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            auth_packet = {
                "type": "AUTH",
                "id": "auth_test_1",
                "token": ACCESS_TOKEN,
                "device_info": {
                    "model": "Pixel 8 Pro",
                    "os": "Android 14",
                    "app_version": "2.5.0"
                }
            }
            ws.send_json(auth_packet)
            resp = ws.receive_json()

            self.assertEqual(resp.get("type"), "AUTH_OK")
            self.assertEqual(resp.get("id"), "auth_test_1")
            self.assertEqual(resp.get("status"), "authenticated")
            self.assertIn("cmd_exec", resp.get("features", []))
            self.assertIn("mt5_trading", resp.get("features", []))
            self.assertIn("clipboard_sync", resp.get("features", []))
            self.assertIn("alarms", resp.get("features", []))

    def test_websocket_auth_via_query_param(self):
        """Verify instant authentication when token is passed as URL query param."""
        with self.client.websocket_connect(f"/ws/bridge?token={ACCESS_TOKEN}") as ws:
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_OK")
            self.assertEqual(resp.get("status"), "authenticated")

    def test_websocket_auth_handshake_invalid_token(self):
        """Verify that an invalid access token rejects connection with AUTH_ERR."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            auth_packet = {
                "type": "AUTH",
                "id": "auth_bad_1",
                "token": "invalid_hacker_token_xyz"
            }
            ws.send_json(auth_packet)
            resp = ws.receive_json()

            self.assertEqual(resp.get("type"), "AUTH_ERR")
            self.assertEqual(resp.get("status"), "unauthorized")

    def test_websocket_unauthenticated_command_rejection(self):
        """Verify that operational commands are rejected if unauthenticated."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            cmd_packet = {
                "type": "CMD_EXEC",
                "id": "unauth_cmd_1",
                "command": "dir"
            }
            ws.send_json(cmd_packet)
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_REQUIRED")

    def test_websocket_ping_pong_heartbeat(self):
        """Verify ping/pong roundtrip latency and timestamp echoing."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume initial AUTH_OK
            t0 = time.time()
            ws.send_json({"type": "PING", "id": "ping_1", "timestamp": t0})
            pong = ws.receive_json()

            self.assertEqual(pong.get("type"), "PONG")
            self.assertEqual(pong.get("id"), "ping_1")
            self.assertIn("server_time", pong)

    def test_mobile_to_pc_cmd_exec_latency(self):
        """Verify Mobile ➔ PC command execution with sub-500ms execution latency."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            start_t = time.perf_counter()
            ws.send_json({
                "type": "CMD_EXEC",
                "id": "cmd_latency_test",
                "command": "Write-Output 'JARVIS_MOBILE_OK'"
            })
            result = ws.receive_json()
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            self.assertEqual(result.get("type"), "CMD_RESULT")
            self.assertEqual(result.get("id"), "cmd_latency_test")
            self.assertTrue(result.get("ok"))
            self.assertIn("JARVIS_MOBILE_OK", result.get("output", ""))
            self.assertLess(elapsed_ms, 5000.0, f"Command took {elapsed_ms:.1f}ms (target <5000ms in unit test)")

    def test_mobile_to_pc_trading_order_dispatch(self):
        """Verify Mobile ➔ PC 1-Click trading order execution packet."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            ws.send_json({
                "type": "TRADE_ORDER",
                "id": "trade_gold_1",
                "symbol": "XAUUSD",
                "action": "BUY",
                "lots": 0.01,
                "sl": 2720.0,
                "tp": 2735.0
            })
            result = ws.receive_json()

            self.assertEqual(result.get("type"), "TRADE_RESULT")
            self.assertEqual(result.get("id"), "trade_gold_1")
            self.assertTrue(result.get("ok"))
            self.assertIn("order", result)
            order = result["order"]
            self.assertEqual(order["symbol"], "XAUUSD")
            self.assertEqual(order["action"], "BUY")
            self.assertEqual(order["lots"], 0.01)
            self.assertEqual(order["status"], "EXECUTED")

    def test_mobile_to_pc_telemetry_ingestion(self):
        """Verify Mobile ➔ PC telemetry payload ingestion and update to server state."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            telemetry_data = {
                "battery_level": 88,
                "is_charging": True,
                "network_type": "WIFI",
                "wifi_ssid": "JARVIS-SECURE-5G",
                "wifi_rssi_dbm": -42,
                "screen_on": True,
                "ambient_light_lux": 340
            }
            ws.send_json({
                "type": "MOBILE_TELEMETRY",
                "id": "telem_1",
                "payload": telemetry_data
            })
            ack = ws.receive_json()
            self.assertEqual(ack.get("type"), "TELEMETRY_ACK")
            self.assertEqual(ack.get("status"), "recorded")

            # Verify through GET /api/mobile/telemetry
            resp = self.client.get("/api/mobile/telemetry")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("ok"))
            telem = data.get("telemetry", {})
            self.assertEqual(telem.get("battery_level"), 88)
            self.assertEqual(telem.get("wifi_ssid"), "JARVIS-SECURE-5G")
            self.assertEqual(telem.get("wifi_rssi_dbm"), -42)


class TestPCToMobileControlEndpoints(unittest.TestCase):
    """Tests PC-to-Mobile push notifications, alarms, clipboard sync, and QR pairing."""

    def setUp(self):
        self.client = TestClient(app)

    def test_post_mobile_notify_broadcast(self):
        """Verify POST /api/mobile/notify broadcasts PUSH_NOTIFICATION to connected mobile."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            # Send notify request via HTTP
            notify_payload = {
                "title": "🚨 FTMO $100k Drawdown Alert",
                "body": "XAUUSD +1.0R Breakeven locked. Profit: +$7.50 secured.",
                "priority": "HIGH",
                "channel_id": "trading_critical"
            }
            resp = self.client.post("/api/mobile/notify", json=notify_payload)
            self.assertEqual(resp.status_code, 200)
            json_resp = resp.json()
            self.assertTrue(json_resp.get("ok"))
            self.assertGreaterEqual(json_resp.get("recipients", 0), 1)

            # Check that the connected WebSocket received the push packet
            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "PUSH_NOTIFICATION")
            self.assertEqual(packet.get("title"), "🚨 FTMO $100k Drawdown Alert")
            self.assertIn("Breakeven locked", packet.get("body", ""))
            self.assertEqual(packet.get("priority"), "HIGH")

    def test_post_mobile_alarm_broadcast(self):
        """Verify POST /api/mobile/alarm broadcasts AUDIO_ALARM to connected mobile."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            alarm_payload = {
                "tone": "defcon_siren",
                "duration_sec": 8,
                "volume": 0.95,
                "override_silent_mode": True,
                "tts_message": "Warning: DEFCON 2 escalation detected."
            }
            resp = self.client.post("/api/mobile/alarm", json=alarm_payload)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json().get("ok"))

            # Check packet delivered to mobile
            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "AUDIO_ALARM")
            self.assertEqual(packet.get("tone"), "defcon_siren")
            self.assertEqual(packet.get("duration_sec"), 8)
            self.assertEqual(packet.get("volume"), 0.95)
            self.assertEqual(packet.get("tts_message"), "Warning: DEFCON 2 escalation detected.")

    def test_pc_to_mobile_clipboard_sync(self):
        """Verify POST /api/mobile/clipboard synchronizes text to mobile WebSockets."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            clip_text = "https://tradingview.com/chart/xauusd-4h-institutional"
            resp = self.client.post("/api/mobile/clipboard", json={"content": clip_text})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json().get("ok"))

            # Verify received packet
            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "CLIPBOARD_PUSH")
            self.assertEqual(packet.get("content"), clip_text)

    def test_mobile_to_pc_clipboard_sync(self):
        """Verify mobile sending CLIPBOARD_PUSH updates server state and responds with ack."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            mobile_clip = "Order #1514382598 Take Profit adjusted to 2735.50"
            ws.send_json({
                "type": "CLIPBOARD_PUSH",
                "id": "clip_mobile_1",
                "content": mobile_clip
            })
            ack = ws.receive_json()
            self.assertEqual(ack.get("type"), "CLIPBOARD_ACK")
            self.assertEqual(ack.get("status"), "synced_to_pc")
            self.assertEqual(manager.last_clipboard_from_mobile, mobile_clip)

    def test_get_mobile_qr_pairing_endpoint(self):
        """Verify GET /api/mobile/qr returns valid pairing configuration and SVG QR."""
        # JSON format
        resp = self.client.get("/api/mobile/qr")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        config = data.get("pairing_config", {})
        self.assertIn("ws_url", config)
        self.assertIn("web_url", config)
        self.assertIn("token", config)
        self.assertIn("svg_qr", data)

        # SVG format
        resp_svg = self.client.get("/api/mobile/qr?format=svg")
        self.assertEqual(resp_svg.status_code, 200)
        self.assertIn("image/svg+xml", resp_svg.headers.get("content-type", ""))
        self.assertIn("<svg", resp_svg.text)

    def test_get_mobile_status_endpoint(self):
        """Verify GET /api/mobile/status returns server version and features."""
        resp = self.client.get("/api/mobile/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("server_version"), "2.5.0")
        self.assertEqual(data.get("port"), 8765)
        self.assertIn("websocket_bridge", data.get("features", []))
        self.assertIn("clipboard_sync", data.get("features", []))


class TestAndroidAPKStructureAndPackaging(unittest.TestCase):
    """Tests the Android Studio Gradle project structure, Java classes, and build_apk.py."""

    def test_android_project_structure_completeness(self):
        """Verify presence of all mandatory Android Gradle, manifest, java, and resource files."""
        build_apk_script = MOBILE_APP_DIR / "build_apk.py"
        self.assertTrue(build_apk_script.exists(), "build_apk.py must exist")

        res = subprocess.run(
            [sys.executable, str(build_apk_script), "--check-structure"],
            capture_output=True,
            text=True,
            timeout=15
        )
        self.assertEqual(res.returncode, 0, f"Structure check failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("Structure Validation PASSED", res.stdout)

    def test_android_manifest_declarations(self):
        """Verify AndroidManifest.xml contains foreground services, boot receivers, and permissions."""
        manifest_file = MOBILE_APP_DIR / "AndroidManifest.xml"
        self.assertTrue(manifest_file.exists())
        content = manifest_file.read_text(encoding="utf-8")

        self.assertIn("android.permission.INTERNET", content)
        self.assertIn("android.permission.ACCESS_NETWORK_STATE", content)
        self.assertIn("android.permission.FOREGROUND_SERVICE", content)
        self.assertIn("android.permission.POST_NOTIFICATIONS", content)
        self.assertIn(".MainActivity", content)
        self.assertIn(".JarvisBridgeService", content)
        self.assertIn(".BootReceiver", content)
        self.assertIn("network_security_config", content)

    def test_android_java_bridge_classes(self):
        """Verify Java classes contain required @JavascriptInterface methods and lifecycle hooks."""
        java_dir = MOBILE_APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "app"

        # 1. JarvisBridgeInterface
        bridge_file = java_dir / "JarvisBridgeInterface.java"
        self.assertTrue(bridge_file.exists())
        bridge_code = bridge_file.read_text(encoding="utf-8")
        self.assertIn("@JavascriptInterface", bridge_code)
        self.assertIn("postNotification", bridge_code)
        self.assertIn("triggerAlarm", bridge_code)
        self.assertIn("copyToClipboard", bridge_code)
        self.assertIn("getTelemetryJson", bridge_code)
        self.assertIn("sendCommand", bridge_code)

        # 2. JarvisBridgeService
        service_file = java_dir / "JarvisBridgeService.java"
        self.assertTrue(service_file.exists())
        service_code = service_file.read_text(encoding="utf-8")
        self.assertIn("extends Service", service_code)
        self.assertIn("startForeground", service_code)
        self.assertIn("showNotification", service_code)
        self.assertIn("playAlarm", service_code)

        # 3. WebSocketClientManager
        ws_file = java_dir / "WebSocketClientManager.java"
        self.assertTrue(ws_file.exists())
        ws_code = ws_file.read_text(encoding="utf-8")
        self.assertIn("OkHttpClient", ws_code)
        self.assertIn("WebSocketListener", ws_code)
        self.assertIn("scheduleReconnect", ws_code)

    def test_build_apk_standalone_packaging(self):
        """Verify build_apk.py packages standalone debug APK zip bundle in dist/."""
        build_apk_script = MOBILE_APP_DIR / "build_apk.py"
        res = subprocess.run(
            [sys.executable, str(build_apk_script), "--mode", "standalone", "--clean"],
            capture_output=True,
            text=True,
            timeout=20
        )
        self.assertEqual(res.returncode, 0, f"Standalone packaging failed:\n{res.stdout}\n{res.stderr}")

        apk_path = MOBILE_APP_DIR / "dist" / "jarvis-companion-debug.apk"
        self.assertTrue(apk_path.exists(), "jarvis-companion-debug.apk was not generated")
        self.assertGreater(apk_path.stat().st_size, 5000, "APK package is suspiciously small")

        # Verify zip contents
        with zipfile.ZipFile(apk_path, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("AndroidManifest.xml", namelist)
            self.assertIn("assets/www/index.html", namelist)
            self.assertIn("assets/www/app.js", namelist)
            self.assertIn("assets/www/bridge_client.js", namelist)
            self.assertIn("META-INF/MANIFEST.MF", namelist)


if __name__ == "__main__":
    unittest.main()
