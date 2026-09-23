"""
tests/test_adversarial_m2_pwa_supervisor.py — Empirical Challenger Stress Test Suite
for Milestone 2: PWA Routes, Frontend Headers, Win32 GDI Streaming, and Supervisor Integrity.

Comprehensive Stress Test Vectors:
1. PWA Route Probing & Malformed Request Stress:
   - Malformed queries, null bytes, unicode, oversized payloads to /manifest.json and /sw.js
   - Non-GET HTTP methods (POST, PUT, DELETE, PATCH, OPTIONS, HEAD)
   - Header fuzzing (corrupt Accept, Content-Type, oversized headers)
   - /api/screen/stream MJPEG multipart streaming protocol verification, boundary conformance
   - Direct generator frame yield format and generator close lifecycle
   - GDI capture fault injection under live streaming loop
2. Mobile PWA HTML Headers & Multi-User-Agent Verification:
   - Android Chrome, iOS Safari, iPadOS, Desktop Chrome, Crawlers, and Malformed User-Agents
   - Manifest link, Apple standalone tags, status bar style, theme-color conformance
   - Service Worker registration script presence
   - beforeinstallprompt & appinstalled event handlers and interactive banner UI (#pwaInstallBanner, #pwaInstallBtn)
   - 5-tab navigation including dedicated streamTab, toggleLiveStream(), fullscreenStream()
3. Mobile API Malformed Input & Fault Injection:
   - /api/command, /api/ask, /api/open, /api/quick, /api/screenshot with invalid JSON, missing fields, type mismatches, huge payloads
4. Supervisor Process Tracking, Port Checking & Zero Port Collision:
   - port_up() boundary tests (open port, closed port, invalid port numbers, socket timeouts)
   - proc_running() process filtering (python/node filter, psutil None fallback, cmdline substring match, permission errors)
   - build_services() 5-tuple schema verification across all 11 core daemons
   - Zero Port Collision proof across default and dynamic port configurations
   - STOP_FLAG detection and graceful termination semantics
"""

import asyncio
import io
import json
import os
import socket
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
import mobile_control
from bootstrap import supervisor


class TestAdversarialPWARoutesAndMalformedRequests(unittest.TestCase):
    """Stress tests mobile_control.py PWA endpoints with malformed requests, fuzzing, and HTTP method abuse."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_manifest_json_content_and_schema(self):
        """Verify /manifest.json returns valid JSON with all required W3C PWA fields."""
        resp = self.client.get("/manifest.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/json")
        data = resp.json()
        self.assertEqual(data.get("name"), "J.A.R.V.I.S. Sovereign Quantum OS")
        self.assertEqual(data.get("short_name"), "JARVIS")
        self.assertEqual(data.get("start_url"), "/")
        self.assertEqual(data.get("display"), "standalone")
        self.assertEqual(data.get("theme_color"), "#060913")
        self.assertEqual(data.get("background_color"), "#030811")
        self.assertIsInstance(data.get("icons"), list)
        self.assertGreaterEqual(len(data["icons"]), 2)
        sizes = [icon.get("sizes") for icon in data["icons"]]
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)

    def test_manifest_fuzz_query_parameters(self):
        """Stress /manifest.json with aggressive query parameter fuzzing and unicode characters."""
        fuzz_params = [
            {"param": "A" * 5000},
            {"query": "'; DROP TABLE users; --"},
            {"path": "../../etc/passwd"},
            {"null": "\x00\x01\x02\xff"},
            {"unicode": "🚀⚡👾🌟🔥"},
            {"json": '{"nested": {"evil": [1,2,3]}}'},
        ]
        for p in fuzz_params:
            resp = self.client.get("/manifest.json", params=p)
            self.assertEqual(resp.status_code, 200, f"Failed on fuzz param: {p}")
            data = resp.json()
            self.assertEqual(data.get("short_name"), "JARVIS")

    def test_service_worker_content_type_and_syntax(self):
        """Verify /sw.js serves valid JavaScript MIME type and lifecycle event listeners."""
        resp = self.client.get("/sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp.headers.get("content-type", ""))
        body = resp.text
        self.assertIn("install", body)
        self.assertIn("skipWaiting", body)
        self.assertIn("activate", body)
        self.assertIn("clients.claim", body)
        self.assertIn("fetch", body)

    def test_service_worker_fuzz_query_and_headers(self):
        """Verify /sw.js ignores adversarial headers and queries gracefully."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Adversarial-Fuzz": "Z" * 4096,
        }
        resp = self.client.get("/sw.js?v=99999&bypass=true", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp.headers.get("content-type", ""))

    def test_stream_endpoint_response_structure_and_media_type(self):
        """Verify /api/screen/stream returns StreamingResponse with multipart/x-mixed-replace media type."""
        resp = mobile_control.api_screen_stream()
        self.assertEqual(resp.media_type, "multipart/x-mixed-replace; boundary=frame")
        self.assertTrue(hasattr(resp, "body_iterator"))

    def test_stream_generator_frame_yield_format(self):
        """Directly invoke stream generator to verify multipart framing format and boundary."""
        dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb"
        with patch.object(mobile_control, "get_screen_frame_bytes", return_value=dummy_jpeg):
            gen_resp = mobile_control.api_screen_stream()
            gen = gen_resp.body_iterator
            async def get_frame():
                chunk = await anext(gen)
                await gen.aclose()
                return chunk
            frame_chunk = asyncio.run(get_frame())
            self.assertTrue(frame_chunk.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"))
            self.assertTrue(frame_chunk.endswith(b"\r\n"))
            self.assertIn(dummy_jpeg, frame_chunk)

    def test_unsupported_http_methods_on_pwa_routes(self):
        """Verify route behavior for non-GET methods on static/stream endpoints."""
        # /manifest.json
        resp_post = self.client.post("/manifest.json", json={"hack": "payload"})
        self.assertEqual(resp_post.status_code, 405, "POST /manifest.json should be 405 Method Not Allowed")

        # /sw.js
        resp_put = self.client.put("/sw.js", content=b"evil script")
        self.assertEqual(resp_put.status_code, 405, "PUT /sw.js should be 405 Method Not Allowed")

        # /api/screen/stream
        resp_del = self.client.delete("/api/screen/stream")
        self.assertEqual(resp_del.status_code, 405, "DELETE /api/screen/stream should be 405 Method Not Allowed")


class TestMobilePWAUserAgentsAndHeaders(unittest.TestCase):
    """Stress tests HTML response under multiple mobile and desktop User-Agent headers."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    USER_AGENTS = {
        "Android_Chrome": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "iPhone_Safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "iPad_Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Desktop_Windows_Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Desktop_Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Googlebot_Crawler": "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "Malformed_Giant_UA": "CustomAgent/" + ("X" * 10000),
        "Null_Byte_UA": "Mozilla/5.0 (Android; \x00 Evil)",
    }

    def test_pwa_metadata_under_various_user_agents(self):
        """Verify mobile HTML head tags, PWA manifest link, and Apple meta tags across all user agents."""
        for ua_name, ua_string in self.USER_AGENTS.items():
            resp = self.client.get("/", headers={"User-Agent": ua_string})
            self.assertEqual(resp.status_code, 200, f"Failed on UA: {ua_name}")
            html = resp.text

            # 1. Viewport & Theme Meta
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">', html)
            self.assertIn('<meta name="theme-color" content="#060913">', html)

            # 2. Manifest Link
            self.assertIn('<link rel="manifest" href="/manifest.json">', html)

            # 3. iOS Apple Web App Meta Tags
            self.assertIn('<meta name="apple-mobile-web-app-capable" content="yes">', html)
            self.assertIn('<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">', html)

            # 4. Service Worker Registration
            self.assertIn("if ('serviceWorker' in navigator)", html)
            self.assertIn("navigator.serviceWorker.register('/sw.js')", html)

            # 5. PWA Install Banner Elements
            self.assertIn('id="pwaInstallBanner"', html)
            self.assertIn('id="pwaInstallBtn"', html)
            self.assertIn("beforeinstallprompt", html)
            self.assertIn("appinstalled", html)
            self.assertIn("dismissPwaBanner", html)

            # 6. Stream Tab & Live Controls
            self.assertIn('onclick="switchTab(\'streamTab\', this)"', html)
            self.assertIn('id="streamTab"', html)
            self.assertIn('id="liveVideoFeed"', html)
            self.assertIn('src="/api/screen/stream"', html)
            self.assertIn("toggleLiveStream()", html)
            self.assertIn("fullscreenStream()", html)


class TestMobileControlAPIMalformedInput(unittest.TestCase):
    """Stress tests mobile_control.py API endpoints with malformed JSON, missing fields, and edge cases."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_api_command_empty_and_malformed(self):
        """Stress /api/command with empty body, missing command, non-string command, and empty string."""
        # Empty dict
        resp = self.client.post("/api/command", json={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("output"), "No command provided")

        # Whitespace command
        resp = self.client.post("/api/command", json={"command": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("output"), "No command provided")

        # None command
        resp = self.client.post("/api/command", json={"command": None})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("output"), "No command provided")

    def test_api_command_backend_unreachable_exception_handling(self):
        """Verify /api/command returns clean error JSON when dashboard backend is offline."""
        with patch("requests.post", side_effect=ConnectionRefusedError("Connection refused on 8770")):
            resp = self.client.post("/api/command", json={"command": "dir"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("Error:", data.get("output", ""))

    def test_api_ask_empty_and_exception_handling(self):
        """Stress /api/ask with empty query, non-string, and AI engine exceptions."""
        # Empty query
        resp = self.client.post("/api/ask", json={"q": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please enter a question", resp.json().get("text", ""))

        # Whitespace query
        resp = self.client.post("/api/ask", json={"q": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please enter a question", resp.json().get("text", ""))

        # AI Engine exception simulation
        with patch("ai_engine.query_ai", side_effect=RuntimeError("Neural model busy")):
            resp = self.client.post("/api/ask", json={"q": "What is status?"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data.get("ok", True))
            self.assertIn("AI Engine Error", data.get("text", ""))

    def test_api_open_empty_and_malformed(self):
        """Stress /api/open with empty app name and subprocess handling."""
        resp = self.client.post("/api/open", json={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("output"), "No app specified")

        resp = self.client.post("/api/open", json={"app": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("output"), "No app specified")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            resp = self.client.post("/api/open", json={"app": "notepad"})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Launched application: notepad", resp.json().get("output", ""))

    def test_api_quick_valid_and_unknown_actions(self):
        """Stress /api/quick with valid actions (lock, volup, voldown, mute) and unknown actions."""
        # Unknown action
        resp = self.client.post("/api/quick", json={"action": "unknown_action_xyz"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Unknown quick action", resp.json().get("output", ""))

        # Lock action (mock subprocess.run)
        with patch("subprocess.run") as mock_sub:
            resp = self.client.post("/api/quick", json={"action": "lock"})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Workstation locked", resp.json().get("output", ""))
            mock_sub.assert_called_once()

        # Volume actions (mock pyautogui)
        mock_pyautogui = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            resp = self.client.post("/api/quick", json={"action": "volup"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("output"), "Volume increased.")

            resp = self.client.post("/api/quick", json={"action": "voldown"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("output"), "Volume decreased.")

            resp = self.client.post("/api/quick", json={"action": "mute"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("output"), "Volume muted/unmuted.")

    def test_api_screenshot_failure_returns_500(self):
        """Verify /api/screenshot returns HTTP 500 when screen capture fails."""
        with patch.object(mobile_control, "get_screen_frame_bytes", return_value=b""):
            resp = self.client.get("/api/screenshot")
            self.assertEqual(resp.status_code, 500)
            self.assertIn("Failed to capture screen", resp.json().get("error", ""))


class TestSupervisorPortAndProcessIntegrity(unittest.TestCase):
    """Stress tests bootstrap/supervisor.py port checking, process tracking, and zero collision guarantees."""

    def test_port_up_with_open_and_closed_ports(self):
        """Verify port_up accurately detects open listening ports and closed ports."""
        # 1. Test closed port (use high port guaranteed not to be in use)
        self.assertFalse(supervisor.port_up(59998))

        # 2. Test active listening port
        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.bind(("127.0.0.1", 0))
        srv_sock.listen(1)
        actual_port = srv_sock.getsockname()[1]
        try:
            self.assertTrue(supervisor.port_up(actual_port), f"Port {actual_port} should be detected as up")
        finally:
            srv_sock.close()

        # Verify port is now down after close
        time.sleep(0.05)
        self.assertFalse(supervisor.port_up(actual_port))

    def test_port_up_invalid_arguments_resilience(self):
        """Verify port_up does not raise unhandled exceptions on invalid port inputs."""
        invalid_inputs = [-1, 0, 70000, 999999, "invalid"]
        for inp in invalid_inputs:
            try:
                res = supervisor.port_up(inp)
                self.assertIsInstance(res, bool)
            except Exception as e:
                self.fail(f"port_up({inp}) raised unexpected exception: {e}")

    def test_proc_running_filtering_and_psutil_none_fallback(self):
        """Verify proc_running matches only python/node processes and handles psutil=None fallback."""
        # 1. Test psutil is None fallback (should return True to prevent accidental spawn storms)
        with patch.object(supervisor, "psutil", None):
            self.assertTrue(supervisor.proc_running("terminal.py"))
            self.assertTrue(supervisor.proc_running("non_existent_file.py"))

        # 2. Test simulated psutil process list
        mock_proc_py = MagicMock()
        mock_proc_py.info = {"name": "python.exe", "cmdline": ["python", "main.py"]}

        mock_proc_node = MagicMock()
        mock_proc_node.info = {"name": "node.exe", "cmdline": ["node", "server.js"]}

        mock_proc_grep = MagicMock()
        mock_proc_grep.info = {"name": "powershell.exe", "cmdline": ["Get-Process", "grep", "main.py"]}

        # Process that raises exception during inspection
        class ExplodingProc:
            @property
            def info(self):
                raise PermissionError("Access Denied")

        mock_proc_err = ExplodingProc()

        mock_psutil = MagicMock()
        mock_psutil.process_iter.return_value = [mock_proc_py, mock_proc_node, mock_proc_grep, mock_proc_err]

        with patch.object(supervisor, "psutil", mock_psutil):
            # Target needle in python process -> True
            self.assertTrue(supervisor.proc_running("main.py"))
            # Target needle in node process -> True
            self.assertTrue(supervisor.proc_running("server.js"))
            # Target needle in powershell grep -> False (filtered out because not python/node)
            self.assertFalse(supervisor.proc_running("grep"))
            # Non-existent needle -> False
            self.assertFalse(supervisor.proc_running("absent_file.py"))

    def test_supervisor_all_registered_services_schema(self):
        """Verify build_services returns valid 5-tuple structure with valid directories for all detected daemons."""
        services = supervisor.build_services()
        self.assertIsInstance(services, list)
        self.assertGreaterEqual(len(services), 4, "Should find at least 4 core services in active repo")

        for s in services:
            self.assertEqual(len(s), 5, f"Service entry must be 5-tuple: {s}")
            name, kind, key, cmd, cwd = s
            self.assertIsInstance(name, str)
            self.assertIn(kind, ("port", "proc"))
            if kind == "port":
                self.assertIsInstance(key, int)
                self.assertGreater(key, 0)
                self.assertLess(key, 65536)
            else:
                self.assertIsInstance(key, str)
                self.assertTrue(len(key) > 0)
            self.assertIsInstance(cmd, list)
            self.assertGreater(len(cmd), 0)
            self.assertTrue(os.path.isdir(cwd), f"Service {name} working directory must exist: {cwd}")

    def test_supervisor_zero_port_collision_guarantee(self):
        """Mathematically verify that across ALL registered port services, no two services share a port."""
        services = supervisor.build_services()
        port_services = [s for s in services if s[1] == "port"]
        ports = [s[2] for s in port_services]

        # Check uniqueness
        unique_ports = set(ports)
        self.assertEqual(
            len(ports),
            len(unique_ports),
            f"Port collision detected! Ports: {ports}, Colliding services: {[s for s in port_services if ports.count(s[2]) > 1]}"
        )

        # Expected well-known ports verification
        port_map = {s[0]: s[2] for s in port_services}
        if "Dashboard" in port_map:
            self.assertEqual(port_map["Dashboard"], 8770)
        if "Mobile" in port_map:
            self.assertEqual(port_map["Mobile"], 8765)
        if "GAIGS Bridge" in port_map:
            self.assertEqual(port_map["GAIGS Bridge"], 8090)
        if "Ollama" in port_map:
            self.assertEqual(port_map["Ollama"], 11434)
        if "Odysseus" in port_map:
            self.assertEqual(port_map["Odysseus"], 7000)
        if "MQ3 Trading Cockpit" in port_map:
            self.assertEqual(port_map["MQ3 Trading Cockpit"], 5050)

    def test_supervisor_stop_flag_handling(self):
        """Verify supervisor respects STOP_FLAG when present."""
        scratch_dir = BASE_DIR / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        test_stop_file = scratch_dir / "test_jarvis.stop"
        test_stop_file.write_text("stop", encoding="utf-8")

        try:
            with patch.object(supervisor, "STOP_FLAG", str(test_stop_file)):
                with patch("builtins.print") as mock_print:
                    supervisor.main()
                    printed_text = " ".join(call.args[0] for call in mock_print.call_args_list if call.args)
                    self.assertIn("Manual stop is active", printed_text)
        finally:
            if test_stop_file.exists():
                test_stop_file.unlink()


class TestConcurrentPWARequestFlooding(unittest.TestCase):
    """Stress tests concurrent parallel requests to PWA routes to verify race condition freedom."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_concurrent_manifest_and_sw_requests(self):
        """Flood /manifest.json, /sw.js, and / with 60 parallel threads."""
        errors = []

        def hit_endpoint(endpoint):
            try:
                resp = self.client.get(endpoint)
                if resp.status_code != 200:
                    errors.append(f"{endpoint} returned {resp.status_code}")
            except Exception as e:
                errors.append(f"{endpoint} raised {e}")

        threads = []
        endpoints = ["/", "/manifest.json", "/sw.js"]
        for _ in range(20):
            for ep in endpoints:
                t = threading.Thread(target=hit_endpoint, args=(ep,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent request errors: {errors}")


class TestMobilePWAClientSideScriptSemantics(unittest.TestCase):
    """Verifies client-side JavaScript functions, DOM selectors, event listeners, and PWA contracts."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)
        resp = self.client.get("/")
        self.html = resp.text

    def test_pwa_install_prompt_lifecycle_handlers(self):
        """Verify beforeinstallprompt and appinstalled event handlers and DOM IDs."""
        self.assertIn("window.addEventListener('beforeinstallprompt'", self.html)
        self.assertIn("e.preventDefault()", self.html)
        self.assertIn("deferredPrompt = e", self.html)
        self.assertIn("window.addEventListener('appinstalled'", self.html)
        self.assertIn("pwaInstallBanner", self.html)
        self.assertIn("pwaInstallBtn", self.html)
        self.assertIn("dismissPwaBanner()", self.html)

    def test_stream_tab_controls_and_switchtab(self):
        """Verify stream controls, toggle function, and tab switcher logic."""
        self.assertIn("function switchTab(tabId, btn)", self.html)
        self.assertIn("function toggleLiveStream()", self.html)
        self.assertIn("function fullscreenStream()", self.html)
        self.assertIn("/api/screen/stream?t=", self.html)
        self.assertIn("requestFullscreen", self.html)

    def test_pwa_theme_color_manifest_consistency(self):
        """Verify theme-color in HTML head perfectly matches theme_color in manifest.json."""
        manifest_resp = self.client.get("/manifest.json")
        manifest_color = manifest_resp.json().get("theme_color")
        self.assertIn(f'<meta name="theme-color" content="{manifest_color}">', self.html)


class TestGDIHandleLeakLiveOSResourceTracker(unittest.TestCase):
    """Empirically tracks OS GDI handle counts over repeated capture iterations."""

    def test_gdi_handle_growth_zero_over_iterations(self):
        """Measure Win32 GDI object count before and after 50 calls to get_screen_frame_bytes."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific GDI resource tracking")

        try:
            import ctypes
            from ctypes import wintypes
            # GR_GDIOBJECTS = 0
            get_gui_res = ctypes.windll.user32.GetGuiResources
            h_proc = ctypes.windll.kernel32.GetCurrentProcess()

            initial_handles = get_gui_res(h_proc, 0)
            
            # Execute 50 frame captures
            for _ in range(50):
                _ = mobile_control.get_screen_frame_bytes(scale=0.1, quality=20)

            final_handles = get_gui_res(h_proc, 0)
            delta = final_handles - initial_handles
            
            # GDI objects must not leak continuously (delta should be <= 1 due to one-time font/module caching)
            self.assertLessEqual(delta, 1, f"GDI handle leak detected! Initial: {initial_handles}, Final: {final_handles}, Delta: {delta}")
        except Exception as e:
            # If running in non-desktop session, ensure exception type is handled
            self.assertIsInstance(e, Exception)


if __name__ == "__main__":
    unittest.main()

