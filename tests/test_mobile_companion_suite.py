"""
tests/test_mobile_companion_suite.py — Comprehensive Integration & Verification Suite
for Requirement R6: 24/7 Android Mobile Companion (Capacitor Native APK & Interactive Avatar)
---------------------------------------------------------------------------------------------
Verifies:
1. Capacitor Project Scaffolding & Configuration (package.json, capacitor.config.json, Android Manifest)
2. Cybernetic Avatar HUD, Web Audio Waveforms, and Bilingual Voice Interactions
3. Sub-50ms WebSocket Client Bridge & Real-Time Latency Telemetry
4. Android Companion APK Archive Generation & Binary Integrity (>20KB, ZIP valid)
5. Remote Command Execution, MT5 1-Click Orders, Clipboard Sync & Push Notifications
"""

import json
import os
import subprocess
import sys
import time
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

import mobile_control
from mobile_control import app, manager, ACCESS_TOKEN

BASE_DIR = Path(__file__).resolve().parent.parent
COMPANION_DIR = BASE_DIR / "mobile" / "jarvis-companion"
ANDROID_DIR = COMPANION_DIR / "android"
APP_DIR = ANDROID_DIR / "app"
WWW_DIR = COMPANION_DIR / "www"
OUTPUT_APK = APP_DIR / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"


class TestCapacitorProjectStructure(unittest.TestCase):
    """Verifies Capacitor configuration, manifests, Java bridge classes, and www assets."""

    def test_companion_directory_exists(self):
        """Verify mobile/jarvis-companion exists."""
        self.assertTrue(COMPANION_DIR.exists(), "mobile/jarvis-companion directory must exist")
        self.assertTrue(COMPANION_DIR.is_dir())

    def test_package_json_capacitor_dependencies(self):
        """Verify package.json contains @capacitor/core, @capacitor/cli, and @capacitor/android."""
        pkg_file = COMPANION_DIR / "package.json"
        self.assertTrue(pkg_file.exists(), "package.json must exist in mobile/jarvis-companion")

        with open(pkg_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("name"), "jarvis-companion")
        deps = data.get("dependencies", {})
        self.assertIn("@capacitor/core", deps)
        self.assertIn("@capacitor/cli", deps)
        self.assertIn("@capacitor/android", deps)

    def test_capacitor_config_json(self):
        """Verify capacitor.config.json has appId com.jarvis.companion, appName JARVIS Companion, webDir www."""
        config_file = COMPANION_DIR / "capacitor.config.json"
        self.assertTrue(config_file.exists(), "capacitor.config.json must exist")

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("appId"), "com.jarvis.companion")
        self.assertEqual(data.get("appName"), "JARVIS Companion")
        self.assertEqual(data.get("webDir"), "www")

    def test_android_manifest_permissions_and_components(self):
        """Verify AndroidManifest.xml contains foreground services, boot receivers, and permissions."""
        manifest_file = APP_DIR / "src" / "main" / "AndroidManifest.xml"
        self.assertTrue(manifest_file.exists(), "AndroidManifest.xml must exist")
        content = manifest_file.read_text(encoding="utf-8")

        self.assertIn('package="com.jarvis.companion"', content)
        self.assertIn("android.permission.INTERNET", content)
        self.assertIn("android.permission.ACCESS_NETWORK_STATE", content)
        self.assertIn("android.permission.FOREGROUND_SERVICE", content)
        self.assertIn("android.permission.POST_NOTIFICATIONS", content)
        self.assertIn("android.permission.WAKE_LOCK", content)
        self.assertIn("android.permission.RECEIVE_BOOT_COMPLETED", content)
        self.assertIn(".MainActivity", content)
        self.assertIn(".JarvisBridgeService", content)
        self.assertIn(".BootReceiver", content)
        self.assertIn("network_security_config", content)

    def test_android_java_bridge_sources(self):
        """Verify all Java bridge classes are in package com.jarvis.companion."""
        java_dir = APP_DIR / "src" / "main" / "java" / "com" / "jarvis" / "companion"
        self.assertTrue(java_dir.exists())

        required_classes = [
            "MainActivity.java",
            "JarvisBridgeInterface.java",
            "JarvisBridgeService.java",
            "WebSocketClientManager.java",
            "ClipboardSyncManager.java",
            "TelemetryReporter.java",
            "WakeOnLanManager.java",
            "BootReceiver.java"
        ]
        for cls_name in required_classes:
            cls_path = java_dir / cls_name
            self.assertTrue(cls_path.exists(), f"Missing Java bridge class: {cls_name}")
            content = cls_path.read_text(encoding="utf-8")
            self.assertIn("package com.jarvis.companion;", content)


class TestCyberneticAvatarAndWebAssets(unittest.TestCase):
    """Verifies www assets, avatar animation logic, bridge client, and controller."""

    def test_avatar_js_implementation(self):
        """Verify avatar.js implements JarvisAvatar with 4 states, rings, particles, and audio waves."""
        avatar_file = WWW_DIR / "avatar.js"
        self.assertTrue(avatar_file.exists())
        code = avatar_file.read_text(encoding="utf-8")

        self.assertIn("class JarvisAvatar", code)
        self.assertIn("setState", code)
        self.assertIn("setAudioLevel", code)
        self.assertIn("idle", code)
        self.assertIn("listening", code)
        self.assertIn("thinking", code)
        self.assertIn("speaking", code)
        self.assertIn("particles", code)
        self.assertIn("waveRadius", code)

    def test_bridge_client_js_implementation(self):
        """Verify bridge_client.js implements JarvisCompanionBridge with sub-50ms ping loop and handlers."""
        client_file = WWW_DIR / "bridge_client.js"
        self.assertTrue(client_file.exists())
        code = client_file.read_text(encoding="utf-8")

        self.assertIn("class JarvisCompanionBridge", code)
        self.assertIn("startPingLoop", code)
        self.assertIn("executeCommand", code)
        self.assertIn("dispatchTrade", code)
        self.assertIn("sendTelemetry", code)
        self.assertIn("pushClipboard", code)
        self.assertIn("wakeOnLan", code)
        self.assertIn("CMD_EXEC", code)
        self.assertIn("TRADE_ORDER", code)

    def test_app_js_implementation(self):
        """Verify app.js implements bilingual Roman Urdu & English voice commands and UI coordination."""
        app_file = WWW_DIR / "app.js"
        self.assertTrue(app_file.exists())
        code = app_file.read_text(encoding="utf-8")

        self.assertIn("class JarvisCompanionApp", code)
        self.assertIn("setupSpeechRecognition", code)
        self.assertIn("speakText", code)
        # Roman Urdu command patterns
        self.assertIn("computer kholo", code)
        self.assertIn("lock karo", code)
        self.assertIn("trading status", code)
        self.assertIn("gold buy", code)
        # Screen stream & terminal
        self.assertIn("updateScreenStream", code)
        self.assertIn("sendTerminalCommand", code)

    def test_index_html_ui_components(self):
        """Verify index.html renders avatar canvas, screen stream, terminal, and 1-click controls."""
        html_file = WWW_DIR / "index.html"
        self.assertTrue(html_file.exists())
        html = html_file.read_text(encoding="utf-8")

        self.assertIn('id="avatarCanvas"', html)
        self.assertIn('id="micBtn"', html)
        self.assertIn('id="screenStreamImg"', html)
        self.assertIn('id="termOutput"', html)
        self.assertIn('id="termInput"', html)
        self.assertIn('id="latencyBadge"', html)
        self.assertIn('WAKE / POWER ON PC', html)
        self.assertIn('BUY GOLD', html)


class TestAPKCompilationAndArchiveIntegrity(unittest.TestCase):
    """Verifies build_apk.py execution and compiled APK artifact integrity (>20KB)."""

    def test_build_apk_execution_and_artifact(self):
        """Execute build_apk.py and verify valid APK generated at outputs/apk/debug/app-debug.apk."""
        builder_script = COMPANION_DIR / "build_apk.py"
        self.assertTrue(builder_script.exists())

        res = subprocess.run(
            [sys.executable, str(builder_script), "--build", "--clean"],
            capture_output=True,
            text=True,
            timeout=25
        )
        self.assertEqual(res.returncode, 0, f"build_apk.py failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("ANDROID COMPANION APK BUILD COMPLETED SUCCESSFULLY", res.stdout)

        # Verify output artifact exists
        self.assertTrue(OUTPUT_APK.exists(), f"Target APK not found at {OUTPUT_APK}")
        apk_size = OUTPUT_APK.stat().st_size
        self.assertGreater(apk_size, 20000, f"APK file size {apk_size} is under 20KB threshold")

        # Verify ZIP structure
        with zipfile.ZipFile(OUTPUT_APK, "r") as zf:
            self.assertIsNone(zf.testzip(), "Corrupted zip entries detected in APK")
            namelist = zf.namelist()
            self.assertIn("AndroidManifest.xml", namelist)
            self.assertIn("assets/www/index.html", namelist)
            self.assertIn("assets/www/style.css", namelist)
            self.assertIn("assets/www/avatar.js", namelist)
            self.assertIn("assets/www/bridge_client.js", namelist)
            self.assertIn("assets/www/app.js", namelist)
            self.assertIn("META-INF/MANIFEST.MF", namelist)


class TestWebSocketSub50msLatencyAndBridge(unittest.TestCase):
    """Verifies sub-50ms WebSocket latency, auth handshake, and command execution."""

    def setUp(self):
        self.client = TestClient(app)
        self.auth_headers = {"X-Jarvis-Token": ACCESS_TOKEN}

    def test_websocket_auth_handshake(self):
        """Verify token handshake on /ws/mobile returns AUTH_OK."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            ws.send_json({
                "type": "AUTH",
                "id": "test_auth_1",
                "token": ACCESS_TOKEN,
                "device_info": {"model": "Capacitor Mobile", "version": "2.5.0"}
            })
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_OK")
            self.assertEqual(resp.get("status"), "authenticated")

    def test_websocket_ping_pong_sub50ms_latency(self):
        """Verify PING/PONG round-trip completes within sub-50ms."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            start_t = time.perf_counter()
            ws.send_json({
                "type": "PING",
                "id": "ping_perf_test",
                "timestamp": time.time()
            })
            pong = ws.receive_json()
            rtt_ms = (time.perf_counter() - start_t) * 1000.0

            self.assertEqual(pong.get("type"), "PONG")
            self.assertEqual(pong.get("id"), "ping_perf_test")
            self.assertIn("server_time", pong)
            self.assertLess(rtt_ms, 50.0, f"WebSocket latency was {rtt_ms:.2f}ms (target <50ms)")

    def test_websocket_cmd_exec_packet(self):
        """Verify CMD_EXEC returns CMD_RESULT with command stdout."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            ws.send_json({
                "type": "CMD_EXEC",
                "id": "cmd_test_1",
                "command": "Write-Output 'CAPACITOR_COMPANION_ALIVE'"
            })
            res = ws.receive_json()

            self.assertEqual(res.get("type"), "CMD_RESULT")
            self.assertEqual(res.get("id"), "cmd_test_1")
            self.assertTrue(res.get("ok"))
            self.assertIn("CAPACITOR_COMPANION_ALIVE", res.get("output", ""))

    def test_websocket_trade_order_packet(self):
        """Verify TRADE_ORDER returns TRADE_RESULT."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            ws.send_json({
                "type": "TRADE_ORDER",
                "id": "trade_test_1",
                "symbol": "XAUUSD",
                "action": "BUY",
                "lots": 0.01,
                "sl": 2720.0,
                "tp": 2735.0
            })
            res = ws.receive_json()

            self.assertEqual(res.get("type"), "TRADE_RESULT")
            self.assertEqual(res.get("id"), "trade_test_1")
            self.assertTrue(res.get("ok"))
            self.assertEqual(res["order"]["symbol"], "XAUUSD")

    def test_websocket_telemetry_ingestion_and_query(self):
        """Verify MOBILE_TELEMETRY payload is recorded and queryable with auth headers."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            telemetry = {
                "battery_level": 95,
                "is_charging": True,
                "network_type": "WIFI",
                "wifi_ssid": "JARVIS-SECURE-5G",
                "wifi_rssi_dbm": -38,
                "screen_on": True
            }
            ws.send_json({
                "type": "MOBILE_TELEMETRY",
                "id": "telem_suite_1",
                "payload": telemetry
            })
            ack = ws.receive_json()
            self.assertEqual(ack.get("type"), "TELEMETRY_ACK")

            # Verify GET /api/mobile/telemetry with required auth header
            resp = self.client.get("/api/mobile/telemetry", headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("ok"))
            self.assertEqual(data["telemetry"]["battery_level"], 95)
            self.assertEqual(data["telemetry"]["wifi_ssid"], "JARVIS-SECURE-5G")

    def test_pc_push_notification_broadcast(self):
        """Verify POST /api/mobile/notify with auth header broadcasts PUSH_NOTIFICATION."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            payload = {
                "title": "⚡ Institutional Confluence Detected",
                "body": "XAUUSD Sweep + Order Block retest. Risk 0.75% locked.",
                "priority": "HIGH"
            }
            resp = self.client.post("/api/mobile/notify", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json().get("ok"))

            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "PUSH_NOTIFICATION")
            self.assertEqual(packet.get("title"), "⚡ Institutional Confluence Detected")

    def test_pc_audio_alarm_broadcast(self):
        """Verify POST /api/mobile/alarm with auth header broadcasts AUDIO_ALARM."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            payload = {
                "tone": "defcon_siren",
                "duration_sec": 6,
                "volume": 0.9,
                "tts_message": "DEFCON 2 Escalation Alert"
            }
            resp = self.client.post("/api/mobile/alarm", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json().get("ok"))

            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "AUDIO_ALARM")
            self.assertEqual(packet.get("tts_message"), "DEFCON 2 Escalation Alert")

    def test_pc_clipboard_sync(self):
        """Verify POST /api/mobile/clipboard with auth header broadcasts CLIPBOARD_PUSH."""
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # AUTH_OK

            clip_text = "https://jarvis.quantum.ops/cockpit"
            resp = self.client.post("/api/mobile/clipboard", json={"content": clip_text}, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json().get("ok"))

            packet = ws.receive_json()
            self.assertEqual(packet.get("type"), "CLIPBOARD_PUSH")
            self.assertEqual(packet.get("content"), clip_text)


if __name__ == "__main__":
    unittest.main()
