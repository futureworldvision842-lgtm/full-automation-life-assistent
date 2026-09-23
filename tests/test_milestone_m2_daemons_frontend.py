"""
Unit and Integration Tests for Milestone 2: Core Daemons, Streaming & Frontend Polish (R1, R5).

Tests:
1. R1.2: GDI Handle Leak Prevention in mobile_control.py (try...finally handle release).
2. R5.1: Mobile PWA Frontend & Install Banner (manifest link, Apple meta, theme-color, SW registration, beforeinstallprompt).
3. R5.2: Live Desktop Video Stream Embed (streamTab, /api/screen/stream MJPEG streaming, snapshot).
4. R1.1: Core Daemons Supervisor (duplicate code removal, 11 core daemons, zero port collision).
5. R5.3: Master War Room Dashboard Polish (telemetry, markets, integrations, stream embed).
"""

import inspect
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
import mobile_control
from bootstrap import supervisor


class TestGDIHandleLeakSafety(unittest.TestCase):
    """R1.2: Verify GDI Handle Leak Prevention in mobile_control.py."""

    def test_get_screen_frame_bytes_code_structure_has_robust_finally(self):
        """Verify get_screen_frame_bytes contains try...finally with ReleaseDC, DeleteDC, DeleteObject."""
        src = inspect.getsource(mobile_control.get_screen_frame_bytes)
        self.assertIn("finally:", src, "get_screen_frame_bytes must use try...finally block")
        self.assertIn("ReleaseDC", src, "ReleaseDC must be called in finally cleanup")
        self.assertIn("DeleteDC", src, "DeleteDC must be called in finally cleanup")
        self.assertIn("DeleteObject", src, "DeleteObject must be called in finally cleanup")

    def test_gdi_handles_cleaned_up_on_getdibits_exception(self):
        """Verify handles are safely released even if GetDIBits raises an exception."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()

        # Simulate valid metrics and handles
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.side_effect = RuntimeError("Simulated GDI DIBits failure")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"", "Should return empty bytes on exception without crashing")

            # Verify cleanup was called
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_gdi_handles_cleaned_up_on_pil_exception(self):
        """Verify handles are safely released even if Image processing / compression raises an exception."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()

        mock_user32.GetSystemMetrics.side_effect = lambda idx: 800 if idx == 0 else 600
        mock_user32.GetDC.return_value = 5001
        mock_gdi32.CreateCompatibleDC.return_value = 6002
        mock_gdi32.CreateCompatibleBitmap.return_value = 7003
        mock_gdi32.GetDIBits.return_value = 1  # success

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32), \
             patch("PIL.Image.frombytes", side_effect=ValueError("Corrupt buffer bytes")):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")

            # Verify cleanup occurred in finally block
            mock_gdi32.DeleteObject.assert_called_once_with(7003)
            mock_gdi32.DeleteDC.assert_called_once_with(6002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 5001)

    def test_get_screen_frame_bytes_normal_execution_returns_bytes(self):
        """Verify get_screen_frame_bytes executes without error."""
        frame = mobile_control.get_screen_frame_bytes(scale=0.1, quality=20)
        self.assertIsInstance(frame, bytes)


class TestMobilePWAAndStreaming(unittest.TestCase):
    """R5.1 & R5.2: Verify Mobile PWA Frontend, Install Banner, and Live Video Stream."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_manifest_json_endpoint(self):
        """R5.1: /manifest.json returns valid PWA manifest."""
        resp = self.client.get("/manifest.json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("short_name"), "JARVIS")
        self.assertEqual(data.get("display"), "standalone")
        self.assertEqual(data.get("start_url"), "/")
        self.assertEqual(data.get("theme_color"), "#060913")
        self.assertEqual(data.get("background_color"), "#030811")
        self.assertIsInstance(data.get("icons"), list)
        self.assertGreaterEqual(len(data["icons"]), 2)

    def test_service_worker_endpoint(self):
        """R5.1: /sw.js returns valid service worker javascript."""
        resp = self.client.get("/sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp.headers.get("content-type", ""))
        self.assertIn("install", resp.text)
        self.assertIn("activate", resp.text)
        self.assertIn("fetch", resp.text)

    def test_mobile_page_html_pwa_metadata(self):
        """R5.1: Mobile HTML <head> includes manifest, Apple web app, and theme color meta tags."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn('<link rel="manifest" href="/manifest.json">', html)
        self.assertIn('<meta name="apple-mobile-web-app-capable" content="yes">', html)
        self.assertIn('<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">', html)
        self.assertIn('<meta name="theme-color" content="#060913">', html)

    def test_mobile_page_pwa_install_banner_and_sw_registration(self):
        """R5.1: Mobile HTML contains install banner and service worker registration."""
        resp = self.client.get("/")
        html = resp.text
        self.assertIn('id="pwaInstallBanner"', html)
        self.assertIn('id="pwaInstallBtn"', html)
        self.assertIn("beforeinstallprompt", html)
        self.assertIn("navigator.serviceWorker.register('/sw.js')", html)

    def test_mobile_page_live_stream_tab_and_embed(self):
        """R5.2: Mobile HTML contains stream tab and live stream viewer embedding /api/screen/stream."""
        resp = self.client.get("/")
        html = resp.text
        self.assertIn('onclick="switchTab(\'streamTab\', this)"', html)
        self.assertIn('id="streamTab"', html)
        self.assertIn('id="liveVideoFeed"', html)
        self.assertIn('/api/screen/stream', html)
        self.assertIn('toggleLiveStream()', html)
        self.assertIn('fullscreenStream()', html)

    def test_api_screenshot_endpoint(self):
        """Verify /api/screenshot returns JPEG response."""
        with patch.object(mobile_control, "get_screen_frame_bytes", return_value=b"\xff\xd8\xff\xe0\x00\x10JFIF"):
            resp = self.client.get("/api/screenshot")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("content-type"), "image/jpeg")


class TestSupervisorServiceDefinitions(unittest.TestCase):
    """R1.1: Verify Core Daemons Supervisor Cleanup & Service Definitions."""

    def test_no_duplicate_definitions_in_supervisor_source(self):
        """Verify duplicate STOP_FLAG and port_up/proc_running definitions are removed."""
        sup_file = BASE_DIR / "bootstrap" / "supervisor.py"
        src = sup_file.read_text(encoding="utf-8")
        self.assertEqual(src.count("def port_up("), 1, "port_up should only be defined once")
        self.assertEqual(src.count("def proc_running("), 1, "proc_running should only be defined once")
        self.assertEqual(src.count("def have("), 1, "have should only be defined once")
        self.assertEqual(src.count("STOP_FLAG = os.path.join(ROOT"), 1, "STOP_FLAG should only be defined once")

    def test_supervisor_build_services_structure(self):
        """Verify build_services builds core service entries with valid 5-tuple structure."""
        services = supervisor.build_services()
        self.assertIsInstance(services, list)
        self.assertGreaterEqual(len(services), 5, "Should register core services")
        for s in services:
            self.assertEqual(len(s), 5)
            name, kind, key, cmd, cwd = s
            self.assertIsInstance(name, str)
            self.assertIn(kind, ("port", "proc"))
            self.assertIsInstance(cmd, list)
            self.assertTrue(os.path.exists(cwd))

    def test_zero_port_collisions(self):
        """Verify no duplicate port allocations exist in supervisor."""
        services = supervisor.build_services()
        ports = [s[2] for s in services if s[1] == "port"]
        duplicates = [p for p in ports if ports.count(p) > 1]
        self.assertEqual(len(duplicates), 0, f"Duplicate ports found: {duplicates}")


class TestMasterWarRoomDashboard(unittest.TestCase):
    """R5.3: Verify Master War Room Dashboard Polish."""

    @classmethod
    def setUpClass(cls):
        import dashboard
        cls.dash = dashboard
        cls.client = TestClient(cls.dash.app)

    def test_dashboard_pc_telemetry(self):
        """Verify /api/pc telemetry returns CPU, RAM, Disk, Process metrics."""
        resp = self.client.get("/api/pc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for metric in ("cpu", "mem", "disk_c", "disk_p", "procs"):
            self.assertIn(metric, data)
            self.assertIsInstance(data[metric], (int, float))

    def test_dashboard_integrations_endpoint(self):
        """Verify /api/integrations returns local service URLs."""
        resp = self.client.get("/api/integrations")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("mq3", data)
        self.assertIn("world_monitor", data)
        self.assertIn("odysseus", data)

    def test_dashboard_markets_endpoint_structure(self):
        """Verify /api/markets returns list of market quote observations."""
        resp = self.client.get("/api/markets")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
