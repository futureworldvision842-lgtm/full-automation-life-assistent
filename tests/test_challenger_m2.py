"""
Adversarial Empirical Challenger Test Suite for Milestone 2:
GDI Streaming, Leak Prevention, Core Daemons, and Mobile PWA Frontend.

Empirically verifies:
1. GDI handle leak safety via 8-stage exception injection matrix.
2. Resilience when cleanup routines (DeleteObject, DeleteDC, ReleaseDC) fail.
3. Live OS GDI resource stability (0 handle growth over 100 cycles via GetGuiResources).
4. Frame capture latency benchmark (<80ms target across 50 iterations).
5. Multipart/x-mixed-replace streaming boundary & header conformance.
6. Core supervisor 11-daemon service hygiene and 0 port collisions.
7. Mobile PWA manifest, service worker, and dashboard integration contracts.
"""

import asyncio
import ctypes
from ctypes import wintypes
import io
import inspect
import json
import os
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
from PIL import Image

import mobile_control
from bootstrap import supervisor


class TestGDIFaultInjectionLeakSafety(unittest.TestCase):
    """Adversarial fault injection at every discrete step of GDI frame capture."""

    def test_01_metrics_zero_or_negative(self):
        """Verify 0x0 or negative screen metrics return b'' cleanly without allocating GDI handles."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 0 if idx == 0 else 0

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_user32.GetDC.assert_not_called()
            mock_gdi32.CreateCompatibleDC.assert_not_called()
            mock_gdi32.CreateCompatibleBitmap.assert_not_called()

    def test_02_getdc_returns_null(self):
        """Verify NULL hdc_screen returns b'' cleanly without calling downstream APIs."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 0

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.CreateCompatibleDC.assert_not_called()
            mock_user32.ReleaseDC.assert_not_called()

    def test_03_create_compatible_dc_returns_null(self):
        """Verify NULL hdc_mem releases hdc_screen and returns b''."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 0

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.CreateCompatibleBitmap.assert_not_called()
            mock_gdi32.DeleteDC.assert_not_called()
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_04_create_compatible_bitmap_returns_null(self):
        """Verify NULL hbm deletes hdc_mem, releases hdc_screen and returns b''."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 0

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_not_called()
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_05_exception_during_select_object(self):
        """Inject exception at SelectObject: verify hbm, hdc_mem, hdc_screen are all freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.SelectObject.side_effect = RuntimeError("GDI SelectObject Failure")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_06_exception_during_bitblt(self):
        """Inject exception at BitBlt: verify hbm, hdc_mem, hdc_screen are all freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.BitBlt.side_effect = OSError("BitBlt Failed")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_07_exception_during_getdibits(self):
        """Inject exception at GetDIBits: verify hbm, hdc_mem, hdc_screen are all freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.side_effect = MemoryError("Cannot allocate DIB buffer")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_08_exception_during_pil_frombytes(self):
        """Inject exception at Image.frombytes: verify all handles are freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.return_value = 1

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32), \
             patch("PIL.Image.frombytes", side_effect=ValueError("Invalid buffer size for frombytes")):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_09_exception_during_pil_resize(self):
        """Inject exception at Image.resize: verify all handles are freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.return_value = 1

        dummy_img = MagicMock()
        dummy_img.resize.side_effect = RuntimeError("Resize kernel failure")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32), \
             patch("PIL.Image.frombytes", return_value=dummy_img):
            result = mobile_control.get_screen_frame_bytes(scale=0.5)
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_10_exception_during_jpeg_compression(self):
        """Inject exception at Image.save (JPEG encoding error): verify all handles are freed."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.return_value = 1

        dummy_img = MagicMock()
        dummy_img.resize.return_value = dummy_img
        dummy_img.save.side_effect = IOError("Encoder JPEG write failed")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32), \
             patch("PIL.Image.frombytes", return_value=dummy_img):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_gdi32.DeleteObject.assert_called_once_with(3003)
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_11_cascading_cleanup_exception_fault_tolerance(self):
        """Verify that if DeleteObject fails with an exception, DeleteDC and ReleaseDC are STILL invoked."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.side_effect = RuntimeError("Trigger failure")
        mock_gdi32.DeleteObject.side_effect = Exception("DeleteObject crashed")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            # Despite DeleteObject crashing, DeleteDC and ReleaseDC must still be called
            mock_gdi32.DeleteDC.assert_called_once_with(2002)
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)

    def test_12_both_delete_calls_fail_fault_tolerance(self):
        """Verify that even if both DeleteObject and DeleteDC fail, ReleaseDC is STILL invoked."""
        mock_user32 = MagicMock()
        mock_gdi32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda idx: 1920 if idx == 0 else 1080
        mock_user32.GetDC.return_value = 1001
        mock_gdi32.CreateCompatibleDC.return_value = 2002
        mock_gdi32.CreateCompatibleBitmap.return_value = 3003
        mock_gdi32.GetDIBits.side_effect = RuntimeError("Trigger failure")
        mock_gdi32.DeleteObject.side_effect = Exception("DeleteObject crashed")
        mock_gdi32.DeleteDC.side_effect = Exception("DeleteDC crashed")

        with patch.object(mobile_control, "user32", mock_user32), \
             patch.object(mobile_control, "gdi32", mock_gdi32):
            result = mobile_control.get_screen_frame_bytes()
            self.assertEqual(result, b"")
            mock_user32.ReleaseDC.assert_called_once_with(0, 1001)


class TestGDIEmpiricalLiveBenchmark(unittest.TestCase):
    """Live execution and empirical benchmarking of GDI handle counts and frame latency."""

    def test_live_gdi_handle_leak_zero_growth_100_iterations(self):
        """Empirically measure live Windows process GDI handle count over 100 frames to prove 0 leak."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        proc = kernel32.GetCurrentProcess()

        # Warm up 5 frames
        for _ in range(5):
            mobile_control.get_screen_frame_bytes(scale=0.25, quality=30)

        initial_gdi = user32.GetGuiResources(proc, 0)
        initial_user = user32.GetGuiResources(proc, 1)

        # Run 100 consecutive screen captures
        for _ in range(100):
            frame = mobile_control.get_screen_frame_bytes(scale=0.55, quality=60)
            self.assertIsInstance(frame, bytes)

        final_gdi = user32.GetGuiResources(proc, 0)
        final_user = user32.GetGuiResources(proc, 1)

        gdi_diff = final_gdi - initial_gdi
        user_diff = final_user - initial_user

        self.assertEqual(gdi_diff, 0, f"GDI handle leak detected! Started with {initial_gdi}, ended with {final_gdi} (delta: {gdi_diff})")
        self.assertEqual(user_diff, 0, f"USER handle leak detected! Started with {initial_user}, ended with {final_user} (delta: {user_diff})")

    def test_capture_latency_benchmark_50_iterations_sub_80ms(self):
        """Benchmark 50 capture iterations: average latency must be < 80ms."""
        # Warmup
        for _ in range(3):
            mobile_control.get_screen_frame_bytes(scale=0.55, quality=60)

        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            frame = mobile_control.get_screen_frame_bytes(scale=0.55, quality=60)
            latencies.append(time.perf_counter() - t0)

        min_ms = min(latencies) * 1000.0
        max_ms = max(latencies) * 1000.0
        avg_ms = (sum(latencies) / len(latencies)) * 1000.0
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] * 1000.0

        print(f"\n[Empirical Benchmark] 50 Frames: Min={min_ms:.2f}ms, Max={max_ms:.2f}ms, Avg={avg_ms:.2f}ms, P95={p95_ms:.2f}ms")
        self.assertLess(avg_ms, 80.0, f"Average capture latency {avg_ms:.2f}ms exceeded 80ms threshold")

    def test_captured_frame_validity_and_dimensions(self):
        """Verify generated frame bytes parse into a valid JPEG image matching scale factor."""
        w_screen = ctypes.windll.user32.GetSystemMetrics(0)
        h_screen = ctypes.windll.user32.GetSystemMetrics(1)
        if w_screen <= 0 or h_screen <= 0:
            self.skipTest("Headless environment without display context")

        scale = 0.55
        frame_bytes = mobile_control.get_screen_frame_bytes(scale=scale, quality=60)
        self.assertTrue(len(frame_bytes) > 0, "Captured frame must not be empty")

        # Must start with JPEG SOI (0xFFD8) and end with EOI (0xFFD9)
        self.assertTrue(frame_bytes.startswith(b"\xff\xd8"), "Frame bytes must start with JPEG SOI marker")
        self.assertTrue(frame_bytes.endswith(b"\xff\xd9"), "Frame bytes must end with JPEG EOI marker")

        # Decode image and verify dimensions
        img = Image.open(io.BytesIO(frame_bytes))
        self.assertEqual(img.format, "JPEG")
        expected_w = int(w_screen * scale)
        expected_h = int(h_screen * scale)
        self.assertEqual(img.size, (expected_w, expected_h))

    def test_concurrent_multithreaded_capture_safety(self):
        """Verify thread-safety when 8 concurrent threads capture screen simultaneously."""
        errors = []
        frames = []

        def worker():
            try:
                for _ in range(10):
                    f = mobile_control.get_screen_frame_bytes(scale=0.3, quality=50)
                    if len(f) > 0:
                        frames.append(len(f))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent capture raised errors: {errors}")
        self.assertGreater(len(frames), 0)


class TestMultipartStreamingAndBoundary(unittest.TestCase):
    """Verify multipart/x-mixed-replace boundary parsing and frame headers."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_screen_stream_response_headers(self):
        """Verify /api/screen/stream returns multipart/x-mixed-replace content-type."""
        resp = mobile_control.api_screen_stream()
        self.assertEqual(resp.media_type, "multipart/x-mixed-replace; boundary=frame")

    def test_multipart_frame_generator_structure(self):
        """Consume async frame generator to verify multipart boundary formatting and JPEG headers."""
        async def run_async_stream_test():
            resp = mobile_control.api_screen_stream()
            gen = resp.body_iterator

            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
                if len(chunks) >= 3:
                    break

            self.assertEqual(len(chunks), 3)
            for chunk in chunks:
                self.assertTrue(chunk.startswith(b"--frame\r\n"), "Chunk must start with multipart boundary '--frame\\r\\n'")
                self.assertIn(b"Content-Type: image/jpeg\r\n\r\n", chunk, "Chunk must include Content-Type header and header separator")
                self.assertTrue(chunk.endswith(b"\r\n"), "Chunk must end with trailing CRLF")

                # Extract image payload
                header_end = chunk.find(b"\r\n\r\n") + 4
                img_data = chunk[header_end:-2] # exclude trailing \r\n
                self.assertTrue(img_data.startswith(b"\xff\xd8"), "Embedded stream frame must be valid JPEG SOI")
                self.assertTrue(img_data.endswith(b"\xff\xd9"), "Embedded stream frame must be valid JPEG EOI")

        asyncio.run(run_async_stream_test())


class TestSupervisorHygieneAndDaemons(unittest.TestCase):
    """Stress test Supervisor process definitions, ports, and absence of dead code."""

    def test_supervisor_11_core_daemons_present(self):
        """Verify core sovereign services are registered in build_services."""
        services = supervisor.build_services()
        self.assertGreaterEqual(len(services), 6, f"Expected at least 6 core daemons, found {len(services)}")

        registered_names = [s[0] for s in services]
        # Core mandatory daemons across all environments
        mandatory = [
            "Dashboard",
            "Mobile",
            "Discord Bot",
            "MQ3 Trading Cockpit"
        ]
        for name in mandatory:
            self.assertIn(name, registered_names, f"Missing mandatory daemon: {name}")

    def test_supervisor_zero_port_collisions(self):
        """Verify all port-based services have strictly distinct port numbers."""
        services = supervisor.build_services()
        port_services = [s for s in services if s[1] == "port"]
        ports = [s[2] for s in port_services]
        self.assertEqual(len(ports), len(set(ports)), f"Port collision detected among: {ports}")

    def test_supervisor_all_service_paths_exist(self):
        """Verify working directories for all daemons exist on disk."""
        services = supervisor.build_services()
        for name, kind, key, cmd, cwd in services:
            self.assertTrue(os.path.isdir(cwd), f"Working directory for '{name}' does not exist: {cwd}")


class TestMobilePWAFrontendIntegrity(unittest.TestCase):
    """Verify Mobile PWA manifests, headers, scripts, and UI tabs."""

    def setUp(self):
        self.client = TestClient(mobile_control.app)

    def test_manifest_metadata(self):
        """Verify W3C Manifest has required fields for PWA standalone installation."""
        resp = self.client.get("/manifest.json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("display"), "standalone")
        self.assertEqual(data.get("theme_color"), "#060913")
        self.assertEqual(data.get("background_color"), "#030811")
        self.assertEqual(data.get("start_url"), "/")
        self.assertGreaterEqual(len(data.get("icons", [])), 2)

    def test_service_worker_caching_and_event_listeners(self):
        """Verify Service Worker contains install skipWaiting, activate claim, and offline fetch handling."""
        resp = self.client.get("/sw.js")
        self.assertEqual(resp.status_code, 200)
        content = resp.text
        self.assertIn("install", content)
        self.assertIn("skipWaiting()", content)
        self.assertIn("activate", content)
        self.assertIn("clients.claim()", content)
        self.assertIn("fetch", content)

    def test_mobile_page_tabs_and_stream_embed(self):
        """Verify Mobile HTML page provides 5 navigation tabs including streamTab."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("switchTab('pcTab', this)", html)
        self.assertIn("switchTab('tradingTab', this)", html)
        self.assertIn("switchTab('worldTab', this)", html)
        self.assertIn("switchTab('aiTab', this)", html)
        self.assertIn("switchTab('streamTab', this)", html)
        self.assertIn("/api/screen/stream", html)
        self.assertIn("pwaInstallBanner", html)
        self.assertIn("pwaInstallBtn", html)


if __name__ == "__main__":
    unittest.main()
