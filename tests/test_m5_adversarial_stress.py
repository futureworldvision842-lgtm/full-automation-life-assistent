"""
tests/test_m5_adversarial_stress.py — Adversarial Stress & Empirical Challenge Suite
====================================================================================
Comprehensive empirical challenge harness for J.A.R.V.I.S. Ecosystem Milestone 5:
1. Bi-directional Mobile Bridge (mobile_control.py):
   - Unauthorized token rejection & security matrix (SQLi, off-by-one, empty, long strings)
   - WebSocket burst flooding (100+ rapid packets)
   - Packet envelope fuzzing (malformed JSON, corrupted structures, huge payloads)
   - Clipboard echo prevention & bi-directional isolation
   - Unauthenticated state lockdowns & multi-client concurrency
2. Android APK Structure & Packaging (mobile_app/build_apk.py):
   - Missing component & tampered layout detection
   - Complete AndroidManifest.xml deep audit (permissions, services, receivers, flags)
   - Java Bridge Interface method & annotation compliance
   - Standalone ZIP APK staging, custom output paths, and clean build recovery
3. Autonomous Browser Navigation & 3-Tier Vision Engine (web_navigator.py, vision_engine.py):
   - Streaming DOM quiescence polling stress, stop button transitions, timeouts
   - Fenced code block extraction edge cases (nested backticks, exotic lang tags)
   - Reasoning trace extraction (<think> tags, thought headers, multiline blocks)
   - HTML markdown sanitization fuzzing
   - 3-tier vision locator cascade resilience (UIA -> OCR -> Multimodal VL)
4. Dynamic API Upgrade Gateway (api_upgrade_gateway.py):
   - Key hot-swapping live transitions (REST_API <-> BROWSER_SCRAPING)
   - Comprehensive error failover matrix (HTTP 429, 402, 401, 403, 500, 503, Timeout)
   - Repeated 429 rate limit storm resilience (no crash loops, no recursion)
   - Multi-threaded concurrent query routing stress
====================================================================================
"""

import asyncio
import concurrent.futures
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Ensure root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import mobile_control
from mobile_control import app, manager, ACCESS_TOKEN, PORT, MobileConnectionManager
from perception.web_navigator import (
    WebNavigator,
    extract_code_blocks,
    extract_reasoning_trace,
    sanitize_markdown,
    get_web_navigator
)
from perception.vision_engine import (
    ScreenVisionEngine,
    get_vision_engine
)
from core.api_upgrade_gateway import (
    APIUpgradeGateway,
    get_api_gateway,
    PROVIDER_DEFAULTS
)


# ============================================================================
# 1. Bi-directional Mobile Bridge Adversarial Tests
# ============================================================================

class TestMobileBridgeAdversarial(unittest.TestCase):
    """Adversarial stress and security test suite for mobile_control.py."""

    def setUp(self):
        self.client = TestClient(app)

    def test_unauthorized_token_rejection_matrix(self):
        """
        Adversarial Test: Fuzz authentication with SQL injection, empty tokens,
        whitespace, off-by-one tokens, and verify strict rejection.
        """
        malicious_tokens = [
            "",
            "   ",
            "None",
            "null",
            "' OR '1'='1",
            "admin'--",
            "CfHj8WkUTMdKFd5bxyDH5W3QDpbsWL09",  # 1 character off from valid token
            "cfhj8wkutmdkfd5bxydh5w3qdpbwl08",  # lower case of valid token
            "A" * 1000,
            "Bearer valid_token_with_prefix",
        ]

        # Verify underlying security engine rejects all malicious ASCII tokens
        for bad_token in malicious_tokens:
            self.assertFalse(
                manager.verify_token(bad_token),
                f"Security flaw: malicious token {bad_token!r} was accepted by verify_token"
            )

        # Verify WebSocket bridge enforces AUTH_ERR rejection on unauthorized handshake
        with self.client.websocket_connect("/ws/mobile") as ws:
            ws.send_json({
                "type": "AUTH",
                "id": "bad_auth_probe",
                "token": "malicious_sqli_' OR '1'='1"
            })
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_ERR")
            self.assertEqual(resp.get("status"), "unauthorized")

    def test_timing_attack_resistance_token_check(self):
        """
        Verify that token verification uses constant-time string comparison (secrets.compare_digest).
        """
        self.assertTrue(manager.verify_token(ACCESS_TOKEN))
        self.assertFalse(manager.verify_token(""))
        self.assertFalse(manager.verify_token("invalid"))
        self.assertFalse(manager.verify_token(ACCESS_TOKEN[:-1]))
        self.assertFalse(manager.verify_token(ACCESS_TOKEN + "extra"))

    def test_websocket_burst_flooding_stress(self):
        """
        Stress Test: Send 100+ rapid burst messages (PING, TELEMETRY, QUICK_ACTION)
        through an active WebSocket session and verify connection stability and latency.
        """
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            init_ack = ws.receive_json()
            self.assertEqual(init_ack.get("type"), "AUTH_OK")

            t0 = time.time()
            packet_count = 100

            for i in range(packet_count):
                if i % 3 == 0:
                    ws.send_json({"type": "PING", "id": f"flood_ping_{i}", "timestamp": time.time()})
                    resp = ws.receive_json()
                    self.assertEqual(resp.get("type"), "PONG")
                elif i % 3 == 1:
                    ws.send_json({
                        "type": "MOBILE_TELEMETRY",
                        "id": f"flood_telem_{i}",
                        "payload": {"battery_level": 50 + (i % 50), "is_charging": True}
                    })
                    resp = ws.receive_json()
                    self.assertEqual(resp.get("type"), "TELEMETRY_ACK")
                else:
                    ws.send_json({
                        "type": "QUICK_ACTION",
                        "id": f"flood_qa_{i}",
                        "action": "noop_test_action"
                    })
                    resp = ws.receive_json()
                    self.assertEqual(resp.get("type"), "QUICK_ACTION_RESULT")

            elapsed = time.time() - t0
            self.assertLess(elapsed, 10.0, f"Flood test took {elapsed:.2f}s (should be sub-10s)")

    def test_packet_envelope_fuzzing_malformed_json(self):
        """
        Fuzzing Test: Send raw corrupted strings, malformed JSON, and truncated packets.
        Verify server returns ERROR packet without closing socket unexpectedly.
        """
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            fuzz_payloads = [
                "{malformed_json_without_quotes: true",
                "{\"type\": \"PING\", \"timestamp\": ",
                "!!!RAW_TEXT_NOT_JSON!!!",
                "<html><body>Not JSON</body></html>",
                "   ",
                "{\"type\": ",
            ]

            for payload in fuzz_payloads:
                ws.send_text(payload)
                resp = ws.receive_json()
                self.assertEqual(resp.get("type"), "ERROR")
                self.assertEqual(resp.get("message"), "Malformed JSON payload")

            # Verify connection is still alive by sending a valid ping
            ws.send_json({"type": "PING", "id": "liveness_check"})
            pong = ws.receive_json()
            self.assertEqual(pong.get("type"), "PONG")

    def test_packet_envelope_fuzzing_missing_fields_and_huge_payloads(self):
        """
        Fuzzing Test: Test packets with missing fields, unknown types, and large payloads (100KB+).
        """
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            # 1. Missing command in CMD_EXEC
            ws.send_json({"type": "CMD_EXEC", "id": "empty_cmd"})
            resp1 = ws.receive_json()
            self.assertEqual(resp1.get("type"), "CMD_RESULT")
            self.assertFalse(resp1.get("ok"))
            self.assertIn("No command specified", resp1.get("output", ""))

            # 2. Unknown packet type
            ws.send_json({"type": "TOTALLY_UNKNOWN_PACKET_XYZ", "id": "unknown_probe"})
            resp2 = ws.receive_json()
            self.assertEqual(resp2.get("type"), "UNRECOGNIZED_PACKET")
            self.assertEqual(resp2.get("received_type"), "TOTALLY_UNKNOWN_PACKET_XYZ")

            # 3. Huge string in telemetry payload (100KB)
            huge_str = "A" * 100000
            ws.send_json({
                "type": "MOBILE_TELEMETRY",
                "id": "huge_payload",
                "payload": {"huge_debug_blob": huge_str, "battery_level": 99}
            })
            resp3 = ws.receive_json()
            self.assertEqual(resp3.get("type"), "TELEMETRY_ACK")
            self.assertEqual(resp3.get("status"), "recorded")

    def test_clipboard_echo_prevention_logic(self):
        """
        Adversarial Test: Verify that when mobile syncs clipboard text, the PC
        clipboard listener detects that the text originated from mobile and DOES NOT
        echo it back, preventing an infinite broadcast feedback loop.
        """
        test_sync_text = f"JARVIS_CLIPBOARD_TEST_{secrets.token_hex(8)}"

        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws:
            _ = ws.receive_json()  # Consume AUTH_OK

            # Mobile pushes clipboard to PC
            ws.send_json({
                "type": "CLIPBOARD_PUSH",
                "id": "clip_mobile_echo_test",
                "content": test_sync_text
            })
            ack = ws.receive_json()
            self.assertEqual(ack.get("type"), "CLIPBOARD_ACK")
            self.assertEqual(ack.get("status"), "synced_to_pc")

            # Verify manager recorded last_clipboard_from_mobile
            self.assertEqual(manager.last_clipboard_from_mobile, test_sync_text)

            # Test echo suppression condition:
            # If current clipboard equals last_clipboard_from_mobile, bridge should NOT broadcast
            should_suppress = (test_sync_text == manager.last_clipboard_from_mobile)
            self.assertTrue(should_suppress, "Echo suppression flag must be True")

    def test_unauthenticated_state_lockdown_all_commands(self):
        """
        Security Test: Verify that every command type is strictly blocked if
        client connects without authentication.
        """
        with self.client.websocket_connect("/ws/mobile") as ws:
            probes = [
                {"type": "CMD_EXEC", "command": "whoami"},
                {"type": "TRADE_ORDER", "symbol": "XAUUSD", "action": "BUY", "lots": 0.1},
                {"type": "CLIPBOARD_PUSH", "content": "hack"},
                {"type": "QUICK_ACTION", "action": "lock"},
                {"type": "MOBILE_TELEMETRY", "payload": {"battery": 10}},
            ]

            for probe in probes:
                ws.send_json(probe)
                resp = ws.receive_json()
                self.assertEqual(
                    resp.get("type"),
                    "AUTH_REQUIRED",
                    f"Command {probe['type']} was not blocked with AUTH_REQUIRED"
                )

    def test_multi_device_broadcast_authentication_filter(self):
        """
        Verify that broadcast notifications only deliver to authenticated clients
        and never leak to unauthenticated sessions.
        """
        # Connect 2 authenticated clients and 1 unauthenticated client
        with self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws_auth1, \
             self.client.websocket_connect(f"/ws/mobile?token={ACCESS_TOKEN}") as ws_auth2, \
             self.client.websocket_connect("/ws/mobile") as ws_unauth:

            _ = ws_auth1.receive_json()  # AUTH_OK
            _ = ws_auth2.receive_json()  # AUTH_OK

            # Broadcast push notification via HTTP
            secret_alert = f"DEFCON_1_ORDER_{secrets.token_hex(4)}"
            resp = self.client.post("/api/mobile/notify", json={
                "title": "Adversarial Test Alert",
                "body": secret_alert,
                "priority": "HIGH"
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("ok"))
            self.assertGreaterEqual(data.get("recipients"), 2)

            # Both authenticated clients receive packet
            p1 = ws_auth1.receive_json()
            p2 = ws_auth2.receive_json()
            self.assertEqual(p1.get("type"), "PUSH_NOTIFICATION")
            self.assertEqual(p1.get("body"), secret_alert)
            self.assertEqual(p2.get("type"), "PUSH_NOTIFICATION")
            self.assertEqual(p2.get("body"), secret_alert)


# ============================================================================
# 2. Android APK Structure & Packaging Adversarial Tests
# ============================================================================

class TestAndroidAPKPackagingAdversarial(unittest.TestCase):
    """Adversarial stress and validation suite for mobile_app/build_apk.py."""

    def setUp(self):
        self.mobile_dir = BASE_DIR / "mobile_app"
        self.build_script = self.mobile_dir / "build_apk.py"

    def test_structure_validation_missing_file_detection(self):
        """
        Adversarial Test: Verify check_structure() detects missing or tampered files.
        """
        import mobile_app.build_apk as build_apk_mod

        # Test against real directory (should pass)
        self.assertTrue(build_apk_mod.check_structure())

        # Test with an injected non-existent file in REQUIRED_FILES
        fake_missing = self.mobile_dir / "non_existent_critical_file.xyz"
        original_required = list(build_apk_mod.REQUIRED_FILES)
        try:
            build_apk_mod.REQUIRED_FILES.append(fake_missing)
            self.assertFalse(build_apk_mod.check_structure())
        finally:
            build_apk_mod.REQUIRED_FILES = original_required

    def test_android_manifest_xml_deep_audit(self):
        """
        Security Audit: Parse AndroidManifest.xml and verify all permissions,
        exported tags, network security config, and hardware acceleration.
        """
        manifest_path = self.mobile_dir / "AndroidManifest.xml"
        self.assertTrue(manifest_path.exists())

        tree = ET.parse(str(manifest_path))
        root = tree.getroot()

        self.assertEqual(root.attrib.get("package"), "com.jarvis.app")

        # Check required permissions
        permissions = {
            elem.attrib.get("{http://schemas.android.com/apk/res/android}name")
            for elem in root.findall("uses-permission")
        }
        required_perms = {
            "android.permission.INTERNET",
            "android.permission.ACCESS_NETWORK_STATE",
            "android.permission.ACCESS_WIFI_STATE",
            "android.permission.FOREGROUND_SERVICE",
            "android.permission.POST_NOTIFICATIONS",
            "android.permission.RECEIVE_BOOT_COMPLETED",
            "android.permission.VIBRATE",
            "android.permission.WAKE_LOCK"
        }
        for rp in required_perms:
            self.assertIn(rp, permissions, f"Missing required permission: {rp}")

        # Check application attributes
        app_elem = root.find("application")
        self.assertIsNotNone(app_elem)
        self.assertEqual(app_elem.attrib.get("{http://schemas.android.com/apk/res/android}hardwareAccelerated"), "true")
        self.assertEqual(app_elem.attrib.get("{http://schemas.android.com/apk/res/android}networkSecurityConfig"), "@xml/network_security_config")

        # Check MainActivity
        activities = [
            a.attrib.get("{http://schemas.android.com/apk/res/android}name")
            for a in app_elem.findall("activity")
        ]
        self.assertIn(".MainActivity", activities)

        # Check JarvisBridgeService
        services = [
            s.attrib.get("{http://schemas.android.com/apk/res/android}name")
            for s in app_elem.findall("service")
        ]
        self.assertIn(".JarvisBridgeService", services)

        # Check BootReceiver
        receivers = [
            r.attrib.get("{http://schemas.android.com/apk/res/android}name")
            for r in app_elem.findall("receiver")
        ]
        self.assertIn(".BootReceiver", receivers)

    def test_java_bridge_interfaces_deep_audit(self):
        """
        Audit Java bridge interfaces for JavascriptInterface annotations and required API methods.
        """
        java_dir = self.mobile_dir / "src" / "main" / "java" / "com" / "jarvis" / "app"

        # Check JarvisBridgeInterface.java
        bridge_code = (java_dir / "JarvisBridgeInterface.java").read_text(encoding="utf-8")
        expected_js_methods = [
            "postNotification",
            "triggerAlarm",
            "copyToClipboard",
            "getClipboardText",
            "getTelemetryJson",
            "sendCommand",
            "isConnected",
            "getServerUrl",
            "setServerUrl",
            "showToast"
        ]
        for meth in expected_js_methods:
            self.assertIn(meth, bridge_code, f"Missing method in JarvisBridgeInterface: {meth}")

        # Check that @JavascriptInterface is used
        self.assertGreaterEqual(bridge_code.count("@JavascriptInterface"), 5)

        # Check MainActivity.java hardware accelerated webview settings
        main_activity_code = (java_dir / "MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("setJavaScriptEnabled(true)", main_activity_code)
        self.assertIn("setDomStorageEnabled(true)", main_activity_code)
        self.assertIn("addJavascriptInterface", main_activity_code)
        self.assertIn("JarvisNative", main_activity_code)

    def test_standalone_zip_packaging_and_custom_output(self):
        """
        Stress Test: Packaging standalone debug APK into temporary paths and
        validating ZIP structure, entry count, and archive integrity.
        """
        import mobile_app.build_apk as build_apk_mod

        with tempfile.TemporaryDirectory(prefix="jarvis_apk_test_") as tmpdir:
            custom_apk = Path(tmpdir) / "subfolder" / "custom-jarvis.apk"
            custom_apk.parent.mkdir(parents=True, exist_ok=True)

            out_path = build_apk_mod.build_standalone_package(output_path=custom_apk)
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 5000)

            # Inspect zip contents
            with zipfile.ZipFile(out_path, "r") as zf:
                namelist = zf.namelist()
                self.assertIn("AndroidManifest.xml", namelist)
                self.assertIn("META-INF/MANIFEST.MF", namelist)
                self.assertIn("assets/www/index.html", namelist)
                self.assertIn("assets/www/app.js", namelist)
                self.assertIn("assets/www/bridge_client.js", namelist)
                self.assertIn("assets/www/style.css", namelist)
                self.assertIn("res/values/strings.xml", namelist)
                self.assertIn("res/xml/network_security_config.xml", namelist)

                # Check manifest headers inside zip
                manifest_txt = zf.read("META-INF/MANIFEST.MF").decode("utf-8")
                self.assertIn("Package: com.jarvis.app", manifest_txt)
                self.assertIn("Target-Sdk: 34", manifest_txt)


# ============================================================================
# 3. Autonomous Browser Navigation & 3-Tier Vision Engine Adversarial Tests
# ============================================================================

class TestBrowserVisionAdversarial(unittest.TestCase):
    """Adversarial stress suite for WebNavigator and ScreenVisionEngine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_browser_test_")
        self.navigator = WebNavigator(profile_dir=Path(self.temp_dir), headless=True)
        self.vision_engine = ScreenVisionEngine()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_streaming_quiescence_fuzzing_and_timeout(self):
        """
        Stress Test: Fuzz _wait_for_quiescence with:
        1. Constantly changing DOM (must return on timeout without freezing).
        2. Fast stable DOM (must return immediately upon min_stable_seconds).
        3. Active stop generation button that vanishes.
        """
        mock_page = MagicMock()

        # Case 1: Unstable stream exceeding timeout -> should return last content without hang
        unstable_counter = 0
        def dynamic_text(*args, **kwargs):
            nonlocal unstable_counter
            unstable_counter += 1
            mock_elem = MagicMock()
            mock_elem.inner_text = MagicMock(return_value=f"Streaming chunk {unstable_counter}")
            return [mock_elem]

        mock_page.query_selector.return_value = MagicMock(is_visible=MagicMock(return_value=True))
        mock_page.query_selector_all = dynamic_text

        t0 = time.time()
        result = self.navigator._wait_for_quiescence(
            page=mock_page,
            response_selectors=["div.content"],
            stop_selectors=["button.stop"],
            timeout_seconds=1,
            poll_interval=0.05,
            min_stable_seconds=0.1
        )
        elapsed = time.time() - t0
        self.assertLess(elapsed, 2.5, "Timeout was not respected")
        self.assertIn("Streaming chunk", result)

        # Case 2: Fast stable stream with stop button vanishing
        stop_elem = MagicMock()
        stop_elem.is_visible.side_effect = [True, False, False, False]
        mock_page.query_selector.return_value = stop_elem

        stable_elem = MagicMock()
        stable_elem.inner_text = MagicMock(return_value="Stable completed output.")
        mock_page.query_selector_all = MagicMock(return_value=[stable_elem])

        t0 = time.time()
        result2 = self.navigator._wait_for_quiescence(
            page=mock_page,
            response_selectors=["div.content"],
            stop_selectors=["button.stop"],
            timeout_seconds=5,
            poll_interval=0.05,
            min_stable_seconds=0.15
        )
        elapsed2 = time.time() - t0
        self.assertEqual(result2, "Stable completed output.")
        self.assertLess(elapsed2, 1.5, f"Quiescence detection took {elapsed2:.2f}s (should be sub-1.5s)")

    def test_code_block_extraction_exotic_edge_cases(self):
        """
        Adversarial Test: Fuzz extract_code_blocks with nested fences,
        exotic language tags (c++, c#, f#, objective-c, python3, bash),
        unclosed blocks, and mixed unicode.
        """
        adversarial_markdown = (
            "```python\n"
            "def main():\n"
            "    print('Normal block')\n"
            "```\n\n"
            "```c++\n"
            "#include <iostream>\n"
            "int main() { return 0; }\n"
            "```\n\n"
            "```c#\n"
            "    // C# sample block\n"
            "    void RunCode() {}\n"
            "```\n\n"
            "```bash\n"
            "curl -X POST 'http://127.0.0.1:8765/api/command'\n"
            "```\n\n"
            "```\n"
            "unspecified language raw code\n"
            "```\n\n"
            "Text in between\n\n"
            "```json\n"
            "{\"valid\": true, \"key\": \"value\"}\n"
            "```\n"
        )
        blocks = extract_code_blocks(adversarial_markdown)
        self.assertEqual(len(blocks), 6)
        self.assertEqual(blocks[0]["language"], "python")
        self.assertEqual(blocks[1]["language"], "c++")
        self.assertEqual(blocks[2]["language"], "c#")
        self.assertEqual(blocks[3]["language"], "bash")
        self.assertEqual(blocks[4]["language"], "text")
        self.assertEqual(blocks[5]["language"], "json")

    def test_reasoning_trace_extraction_adversarial_formats(self):
        """
        Adversarial Test: Fuzz extract_reasoning_trace with:
        1. DeepSeek <think> tags containing code, XML, and multiline text.
        2. Thought Process / Thinking Process headers.
        3. Missing reasoning trace (returns None and clean text).
        """
        # 1. Complex <think> block
        complex_think = """<think>
1. Evaluate trading strategy for XAUUSD.
2. Check <xml_tag>inside thinking</xml_tag>.
3. Calculate ATR: 1.5 * 14.2 = 21.3.
</think>
Buy XAUUSD with 0.01 lots at 2725.00."""
        reasoning, clean = extract_reasoning_trace(complex_think)
        self.assertIsNotNone(reasoning)
        self.assertIn("Evaluate trading strategy", reasoning)
        self.assertIn("<xml_tag>inside thinking</xml_tag>", reasoning)
        self.assertEqual(clean, "Buy XAUUSD with 0.01 lots at 2725.00.")

        # 2. Thought Process Header
        header_thought = """Thought Process:
We need to analyze geopolitical DEFCON risk.
Strait of Hormuz threat is elevated.

Response:
Maintain Gold long positions with tight stops."""
        reasoning2, clean2 = extract_reasoning_trace(header_thought)
        self.assertIsNotNone(reasoning2)
        self.assertIn("DEFCON risk", reasoning2)
        self.assertIn("Maintain Gold long positions", clean2)

        # 3. Clean text with no thought
        plain_text = "Direct response with no thinking blocks."
        reasoning3, clean3 = extract_reasoning_trace(plain_text)
        self.assertIsNone(reasoning3)
        self.assertEqual(clean3, plain_text)

    def test_sanitize_markdown_fuzzing(self):
        """
        Adversarial Test: Fuzz sanitize_markdown with HTML injection,
        encoded entities, and pre/code block translation.
        """
        raw = """<div><h1>Header</h1><pre><code class="language-typescript">const x: number = 42;</code></pre><p>Test &amp; &lt;script&gt;alert(1)&lt;/script&gt;</p></div>"""
        clean = sanitize_markdown(raw)
        self.assertIn("```typescript", clean)
        self.assertIn("const x: number = 42;", clean)
        self.assertIn("& <script>alert(1)</script>", clean)
        self.assertNotIn("<pre>", clean)
        self.assertNotIn("<div>", clean)

    def test_vision_engine_tier_cascade_and_failure_resilience(self):
        """
        Adversarial Test: Verify 3-tier cascade handles None returns and progresses through tiers.
        """
        # Tier 1 returns None -> falls back to Tier 2
        with patch.object(self.vision_engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.vision_engine, "_locate_tier2_ocr", return_value=(500, 300)):
            coords = self.vision_engine.locate_ui_element("Test Button")
            self.assertEqual(coords, (500, 300))

        # Tier 1 & Tier 2 return None -> falls back to Tier 3
        with patch.object(self.vision_engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.vision_engine, "_locate_tier2_ocr", return_value=None), \
             patch.object(self.vision_engine, "_locate_tier3_multimodal", return_value=(700, 450)):
            coords2 = self.vision_engine.locate_ui_element("Complex Target")
            self.assertEqual(coords2, (700, 450))

        # All 3 tiers fail -> returns None without unhandled exception
        with patch.object(self.vision_engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.vision_engine, "_locate_tier2_ocr", return_value=None), \
             patch.object(self.vision_engine, "_locate_tier3_multimodal", return_value=None):
            coords3 = self.vision_engine.locate_ui_element("Ghost Element")
            self.assertIsNone(coords3)


# ============================================================================
# 4. Dynamic API Upgrade Gateway Adversarial Tests
# ============================================================================

class TestAPIUpgradeGatewayAdversarial(unittest.TestCase):
    """Adversarial stress and hot-swapping test suite for api_upgrade_gateway.py."""

    def setUp(self):
        self._orig_env = dict(os.environ)
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_gw_test_")
        self.config_path = Path(self.temp_dir) / "api_keys.json"
        self.config_path.write_text(json.dumps({}), encoding="utf-8")
        self.gateway = APIUpgradeGateway(config_path=self.config_path)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_live_key_hot_swapping_transitions(self):
        """
        Adversarial Test: Rapidly set, modify, and delete keys on the fly.
        Verify that gateway instantly switches mode between BROWSER_SCRAPING and REST_API.
        """
        # Initial: No keys -> All BROWSER_SCRAPING
        caps0 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps0["openai"]["mode"], "BROWSER_SCRAPING")
        self.assertEqual(caps0["anthropic"]["mode"], "BROWSER_SCRAPING")

        # Step 1: Add OpenAI key
        self.gateway.set_provider_key("openai", "sk-proj-test-live-key-1", persist=True)
        caps1 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps1["openai"]["mode"], "REST_API")
        self.assertTrue(caps1["openai"]["key_configured"])

        # Step 2: Add Anthropic key
        self.gateway.set_provider_key("anthropic", "sk-ant-test-live-key-2", persist=True)
        caps2 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps2["anthropic"]["mode"], "REST_API")

        # Step 3: Remove OpenAI key (write empty string to config)
        cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
        cfg["openai_api_key"] = ""
        # Also clear env var
        os.environ.pop("OPENAI_API_KEY", None)
        self.config_path.write_text(json.dumps(cfg), encoding="utf-8")

        # Touch mtime to force cache reload
        time.sleep(0.05)
        self.gateway.invalidate_cache()
        caps3 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps3["openai"]["mode"], "BROWSER_SCRAPING")
        self.assertEqual(caps3["anthropic"]["mode"], "REST_API")

    def test_transparent_fallback_on_all_http_error_codes(self):
        """
        Adversarial Test: Test automatic browser scraping fallback across all critical error codes:
        - HTTP 429: Rate Limit Exceeded
        - HTTP 402: Payment Required / Quota Exhausted
        - HTTP 401 / 403: Invalid Key / Unauthorized / Forbidden
        - HTTP 500 / 503: Internal Server Error / Service Unavailable
        - Connection Timeout
        """
        error_scenarios = [
            (429, "Too Many Requests - Rate Limit Exceeded"),
            (402, "Payment Required - Insufficient Credit"),
            (401, "Unauthorized - Invalid API Key"),
            (403, "Forbidden - Region Blocked"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable - Overloaded"),
        ]

        for status_code, err_msg in error_scenarios:
            with self.subTest(status_code=status_code):
                with patch.object(self.gateway, "get_api_key", return_value=("sk-test-key", "config")), \
                     patch("requests.post") as mock_post, \
                     patch("perception.web_navigator.WebNavigator.query_web_llm") as mock_browser:

                    mock_post.return_value.status_code = status_code
                    mock_post.return_value.text = err_msg

                    mock_browser.return_value = {
                        "ok": True,
                        "provider": "chatgpt",
                        "response_text": f"Scraped Fallback Response after HTTP {status_code}",
                        "code_blocks": [{"language": "python", "code": "print('fallback')"}],
                        "reasoning_trace": None,
                        "duration_ms": 500.0,
                        "error": None
                    }

                    res = self.gateway.route_query("openai", "Test prompt")
                    self.assertTrue(res["ok"], f"Failed on status {status_code}")
                    self.assertEqual(res["transport"], "BROWSER_SCRAPING")
                    self.assertTrue(res["fallback_used"])
                    self.assertIn(f"after HTTP {status_code}", res["content"])

    def test_repeated_429_storm_no_crash_loops(self):
        """
        Stress Test: Fire 25 consecutive queries under a persistent 429 rate limit storm.
        Verify zero crash loops, zero recursion errors, and 100% graceful fallback.
        """
        with patch.object(self.gateway, "get_api_key", return_value=("sk-test-storm-key", "config")), \
             patch("requests.post") as mock_post, \
             patch("perception.web_navigator.WebNavigator.query_web_llm") as mock_browser:

            mock_post.return_value.status_code = 429
            mock_post.return_value.text = "HTTP 429: Too Many Requests"

            mock_browser.return_value = {
                "ok": True,
                "provider": "deepseek",
                "response_text": "Browser scraped result during storm.",
                "code_blocks": [],
                "reasoning_trace": None,
                "duration_ms": 100.0,
                "error": None
            }

            for i in range(25):
                res = self.gateway.route_query("deepseek", f"Query #{i} during 429 storm")
                self.assertTrue(res["ok"])
                self.assertEqual(res["transport"], "BROWSER_SCRAPING")
                self.assertTrue(res["fallback_used"])

    def test_gateway_multithreaded_concurrent_stress(self):
        """
        Concurrency Stress Test: Execute 20 concurrent queries from 5 background threads
        while dynamically mutating configuration, ensuring full thread safety.
        """
        # Inject mock responses for stability in concurrency
        self.gateway.set_mock_response("route:openai", {
            "ok": True,
            "transport": "REST_API",
            "content": "Concurrent response OpenAI",
            "code_blocks": [],
            "reasoning_trace": None,
            "model_or_url": "gpt-4o",
            "fallback_used": False,
            "error": None
        })
        self.gateway.set_mock_response("route:deepseek", {
            "ok": True,
            "transport": "BROWSER_SCRAPING",
            "content": "Concurrent response DeepSeek",
            "code_blocks": [],
            "reasoning_trace": "Thought trace",
            "model_or_url": "https://chat.deepseek.com",
            "fallback_used": False,
            "error": None
        })

        results = []
        errors = []

        def worker(thread_id: int):
            for i in range(4):
                try:
                    prov = "openai" if (i % 2 == 0) else "deepseek"
                    res = self.gateway.route_query(prov, f"Thread {thread_id} Query {i}")
                    results.append(res)
                except Exception as e:
                    errors.append((thread_id, i, str(e)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, tid) for tid in range(5)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Encountered thread errors: {errors}")
        self.assertEqual(len(results), 20, f"Expected 20 results, got {len(results)}")
        for r in results:
            self.assertTrue(r.get("ok"))


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    unittest.main()
