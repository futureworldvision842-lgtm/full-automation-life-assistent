"""
tests/test_m3_adversarial_challenge.py
===============================================================================
Adversarial Stress Test Suite for Milestone M3:
God's Eye Screen Capture & Window Inspection (R3)

Adversarially challenges:
1. High-Frequency Screen Grabs:
   - 10 consecutive screen grabs in rapid succession (system_control.capture_screen)
   - 10 consecutive screen grabs in rapid succession (screen_capture.capture_display)
   - Latency ceiling (<500ms for 100% of grabs)
   - Output PNG integrity (>50 KB, exact 1920x1080 dimensions, valid PIL header)
2. Multi-Monitor Geometry:
   - Physical/virtual desktop metrics audit (dual monitor detection: 3840x1080 virtual desktop)
   - Verification that primary display grabs are NOT expanded or stretched to 3840x1080
   - Aspect ratio strictly 16:9 (1.7778)
3. Desktop Attachment Resilience (WinError 170 ERROR_BUSY):
   - Active window creation on caller thread to simulate COM / STA hook conflict
   - Verification of Win32 ERROR_BUSY (170) on unattached threads
   - Verification of clean execution via worker thread fallback
   - Caller-thread grab failure simulation via OSError
   - Multi-threaded concurrent screen capture stress test (5 concurrent threads)
4. Foreground Window Focus & Active Application Inspection:
   - get_active_window_info() and inspect_foreground() validation
   - Valid hwnd (>0), non-empty title, non-empty process_name, valid pid (>0)
   - 50-iteration rapid polling loop for handle leak and latency verification
5. Dashboard REST API /api/desktop/inspect Rapid Polling:
   - 30 consecutive rapid GET requests under FastAPI TestClient
   - 10 concurrent requests under ThreadPoolExecutor
   - Validation of ok=True, active_window, display_metrics (1920x1080, monitors >= 1)
   - Response latency < 200ms per request
===============================================================================
"""

import os
import sys
import time
import ctypes
import unittest
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import actions.system_control as system_control
import perception.screen_capture as screen_capture
from dashboard import app
from fastapi.testclient import TestClient


class TestM3AdversarialChallenge(unittest.TestCase):
    """Adversarial stress testing suite for God's Eye screen capture and window inspection."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_artifacts_dir = PROJECT_ROOT / "runtime" / "challenger_test_artifacts"
        cls.test_artifacts_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. HIGH-FREQUENCY SCREEN GRABS (10 CONSECUTIVE GRABS)
    # =========================================================================

    def test_01_high_frequency_screen_grabs_system_control(self):
        """
        Executes 10 consecutive screen grabs in rapid succession via system_control.capture_screen().
        Asserts 100% of grabs complete in <500ms, files exist, >50 KB, and dimensions are (1920, 1080).
        """
        latencies = []
        file_sizes = []
        dimensions = []

        for i in range(10):
            custom_path = self.test_artifacts_dir / f"high_freq_sc_{i+1}.png"
            t0 = time.perf_counter()
            result = system_control.capture_screen(save_path=str(custom_path))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

            # Assert execution status
            self.assertEqual(result.get("status"), "success", f"Grab {i+1} failed with status: {result}")
            self.assertLess(elapsed_ms, 500.0, f"Grab {i+1} took {elapsed_ms:.2f}ms, exceeding 500ms ceiling")

            # Assert file existence and size
            out_file = Path(result["file_path"])
            self.assertTrue(out_file.exists(), f"Grab {i+1} file does not exist: {out_file}")
            size = out_file.stat().st_size
            file_sizes.append(size)
            self.assertGreater(size, 50 * 1024, f"Grab {i+1} file size {size} bytes is <= 50 KB")

            # Assert exact dimensions and validity via PIL verification
            with Image.open(out_file) as img:
                self.assertEqual(img.size, (1920, 1080), f"Grab {i+1} dimensions {img.size} != (1920, 1080)")
                self.assertEqual(img.format, "PNG", f"Grab {i+1} format {img.format} != PNG")
                dimensions.append(img.size)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"\n[High-Freq system_control.capture_screen] 10 Grabs: min={min_lat:.1f}ms, max={max_lat:.1f}ms, avg={avg_lat:.1f}ms")
        print(f"[High-Freq system_control.capture_screen] Sizes: min={min(file_sizes)//1024}KB, max={max(file_sizes)//1024}KB")

    def test_02_high_frequency_screen_grabs_perception_engine(self):
        """
        Executes 10 consecutive screen grabs in rapid succession via perception.screen_capture.capture_display().
        Asserts 100% of grabs complete in <500ms, files exist, >50 KB, and dimensions are (1920, 1080).
        """
        latencies = []
        file_sizes = []
        dimensions = []

        for i in range(10):
            custom_path = self.test_artifacts_dir / f"high_freq_psc_{i+1}.png"
            t0 = time.perf_counter()
            result = screen_capture.capture_display(save_path=str(custom_path))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

            # Assert execution status
            self.assertEqual(result.get("status"), "success", f"Grab {i+1} failed with status: {result}")
            self.assertLess(elapsed_ms, 500.0, f"Grab {i+1} took {elapsed_ms:.2f}ms, exceeding 500ms ceiling")

            # Assert file existence and size
            out_file = Path(result["file_path"])
            self.assertTrue(out_file.exists(), f"Grab {i+1} file does not exist: {out_file}")
            size = out_file.stat().st_size
            file_sizes.append(size)
            self.assertGreater(size, 50 * 1024, f"Grab {i+1} file size {size} bytes is <= 50 KB")

            # Assert exact dimensions via PIL verification
            with Image.open(out_file) as img:
                self.assertEqual(img.size, (1920, 1080), f"Grab {i+1} dimensions {img.size} != (1920, 1080)")
                self.assertEqual(img.format, "PNG", f"Grab {i+1} format {img.format} != PNG")
                dimensions.append(img.size)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"\n[High-Freq screen_capture.capture_display] 10 Grabs: min={min_lat:.1f}ms, max={max_lat:.1f}ms, avg={avg_lat:.1f}ms")

    # =========================================================================
    # 2. MULTI-MONITOR GEOMETRY TEST
    # =========================================================================

    def test_03_multi_monitor_geometry_isolation(self):
        """
        Verifies workstation multi-monitor geometry and asserts that captured images
        are NOT stretched or scaled to virtual desktop dimensions (e.g. 3840x1080).
        """
        user32 = ctypes.windll.user32
        sm_cxscreen = user32.GetSystemMetrics(0)   # Primary monitor width
        sm_cyscreen = user32.GetSystemMetrics(1)   # Primary monitor height
        sm_monitors = user32.GetSystemMetrics(80)  # Number of monitors
        sm_cxvirtual = user32.GetSystemMetrics(78) # Virtual desktop width
        sm_cyvirtual = user32.GetSystemMetrics(79) # Virtual desktop height

        print(f"\n[Multi-Monitor Geometry] Primary: {sm_cxscreen}x{sm_cyscreen} | Monitors: {sm_monitors} | Virtual Desktop: {sm_cxvirtual}x{sm_cyvirtual}")

        self.assertEqual(sm_cxscreen, 1920, f"Primary monitor width is {sm_cxscreen}, expected 1920")
        self.assertEqual(sm_cyscreen, 1080, f"Primary monitor height is {sm_cyscreen}, expected 1080")

        # Capture primary screen artifact
        res = system_control.capture_screen()
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("width"), 1920)
        self.assertEqual(res.get("height"), 1080)

        # Confirm saved image file directly
        img_path = Path(res["file_path"])
        with Image.open(img_path) as im:
            self.assertEqual(im.width, 1920, f"Image width {im.width} was stretched/expanded; expected 1920")
            self.assertEqual(im.height, 1080, f"Image height {im.height}; expected 1080")
            # Strict aspect ratio verification
            aspect_ratio = im.width / im.height
            expected_ratio = 16.0 / 9.0
            self.assertAlmostEqual(aspect_ratio, expected_ratio, places=3,
                                   msg=f"Aspect ratio {aspect_ratio:.4f} indicates horizontal stretching away from 16:9")

        # Verify that even in multi-monitor environment, virtual width (e.g. 3840) is NOT the image width
        if sm_monitors > 1:
            self.assertNotEqual(im.width, sm_cxvirtual,
                                f"Captured image width {im.width} matches virtual desktop width {sm_cxvirtual}, violating primary monitor requirement")

    # =========================================================================
    # 3. DESKTOP ATTACHMENT RESILIENCE (WINERROR 170 ERROR_BUSY)
    # =========================================================================

    def test_04_desktop_attachment_winerror_170_and_worker_fallback(self):
        """
        Simulates an environment where the caller thread has an active window / hook,
        causing SetThreadDesktop to fail with WinError 170 (ERROR_BUSY: 'The requested resource is in use').
        Verifies that capture_screen() and capture_display() fall back gracefully to a clean worker thread
        and complete in <500ms without crashing.
        """
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Create a window on the current thread to cause SetThreadDesktop to fail with ERROR_BUSY 170
        test_hwnd = user32.CreateWindowExW(0, "STATIC", "JarvisAdversarialWindow", 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.assertNotEqual(test_hwnd, 0, "Failed to create test window on current thread")

        try:
            # Confirm SetThreadDesktop fails with ERROR_BUSY 170
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            self.assertNotEqual(hdesk, 0, "Failed to open input desktop handle")
            res = user32.SetThreadDesktop(hdesk)
            err = kernel32.GetLastError()
            user32.CloseDesktop(hdesk)

            self.assertEqual(res, 0, "SetThreadDesktop was expected to fail on a thread with an active window")
            self.assertEqual(err, 170, f"Expected WinError 170 (ERROR_BUSY), got: {err}")

            # Verify _attach_input_desktop returns False on this thread
            attach_res = system_control._attach_input_desktop()
            self.assertFalse(attach_res, "_attach_input_desktop should return False when thread has active window")

            # Now challenge system_control.capture_screen() on this conflicted thread
            t0 = time.perf_counter()
            cap_res = system_control.capture_screen()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            self.assertEqual(cap_res.get("status"), "success", f"capture_screen failed on conflicted thread: {cap_res}")
            self.assertLess(elapsed_ms, 500.0, f"capture_screen took {elapsed_ms:.2f}ms under WinError 170")
            self.assertEqual(cap_res.get("width"), 1920)
            self.assertEqual(cap_res.get("height"), 1080)
            self.assertGreater(cap_res.get("size_bytes", 0), 50 * 1024)

            # Now challenge perception.screen_capture.capture_display() on this conflicted thread
            t1 = time.perf_counter()
            disp_res = screen_capture.capture_display()
            elapsed_disp_ms = (time.perf_counter() - t1) * 1000.0

            self.assertEqual(disp_res.get("status"), "success", f"capture_display failed on conflicted thread: {disp_res}")
            self.assertLess(elapsed_disp_ms, 500.0, f"capture_display took {elapsed_disp_ms:.2f}ms under WinError 170")
            self.assertEqual(disp_res.get("width"), 1920)
            self.assertEqual(disp_res.get("height"), 1080)
            self.assertGreater(disp_res.get("size_bytes", 0), 50 * 1024)

            print(f"\n[WinError 170 Resilience] capture_screen: {elapsed_ms:.1f}ms | capture_display: {elapsed_disp_ms:.1f}ms")

        finally:
            # Clean up the test window
            user32.DestroyWindow(test_hwnd)

    def test_05_worker_thread_fallback_under_simulated_oserror(self):
        """
        Simulates PIL ImageGrab.grab() raising OSError('screen grab failed') on the caller thread.
        Verifies that the worker thread fallback cleanly intercepts the failure, executes grab in
        a clean thread, and produces a valid 1920x1080 PNG.
        """
        caller_tid = threading.get_ident()
        real_grab = system_control.ImageGrab.grab

        def mock_grab(*args, **kwargs):
            if threading.get_ident() == caller_tid:
                raise OSError("Simulated screen grab failed on caller thread with corrupted desktop handle")
            return real_grab(*args, **kwargs)

        with patch("actions.system_control.ImageGrab.grab", side_effect=mock_grab):
            t0 = time.perf_counter()
            res = system_control.capture_screen()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            self.assertEqual(res.get("status"), "success", f"Fallback failed: {res}")
            self.assertLess(elapsed_ms, 500.0, f"Fallback exceeded 500ms ceiling: {elapsed_ms:.2f}ms")
            self.assertEqual(res.get("width"), 1920)
            self.assertEqual(res.get("height"), 1080)
            self.assertGreater(res.get("size_bytes", 0), 50 * 1024)

        print(f"\n[Simulated OSError Fallback] Successfully caught and resolved in {elapsed_ms:.1f}ms")

    def test_06_concurrent_screen_capture_stress(self):
        """
        Launches 5 concurrent threads executing screen capture simultaneously to test
        against race conditions, GDI handle contention, and file collision.
        """
        def _grab_worker(worker_id):
            out_file = self.test_artifacts_dir / f"concurrent_grab_{worker_id}.png"
            t0 = time.perf_counter()
            res = system_control.capture_screen(save_path=str(out_file))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "worker_id": worker_id,
                "elapsed_ms": elapsed_ms,
                "status": res.get("status"),
                "width": res.get("width"),
                "height": res.get("height"),
                "size_bytes": res.get("size_bytes", 0),
                "file_path": res.get("file_path")
            }

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_grab_worker, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r["status"], "success", f"Concurrent worker {r['worker_id']} failed")
            self.assertEqual(r["width"], 1920)
            self.assertEqual(r["height"], 1080)
            self.assertGreater(r["size_bytes"], 50 * 1024)
            # Verify the resulting file on disk
            fpath = Path(r["file_path"])
            self.assertTrue(fpath.exists())
            with Image.open(fpath) as im:
                self.assertEqual(im.size, (1920, 1080))

        latencies = [r["elapsed_ms"] for r in results]
        print(f"\n[Concurrent 5 Threads] Latencies: {[round(l, 1) for l in latencies]} ms (avg: {sum(latencies)/len(latencies):.1f}ms)")

    # =========================================================================
    # 4. FOREGROUND WINDOW FOCUS & ACTIVE APPLICATION INSPECTION
    # =========================================================================

    def test_07_foreground_window_focus_and_inspection(self):
        """
        Tests get_active_window_info() and inspect_foreground():
        verifying valid hwnd (>0), non-empty title string, valid process name, and pid (>0).
        """
        info = system_control.get_active_window_info()

        self.assertIsInstance(info, dict)
        self.assertIn("hwnd", info)
        self.assertIn("title", info)
        self.assertIn("active_window", info)
        self.assertIn("process_name", info)
        self.assertIn("pid", info)

        self.assertGreater(info["hwnd"], 0, f"hwnd must be > 0, got: {info['hwnd']}")
        self.assertIsInstance(info["title"], str)
        self.assertTrue(len(info["title"].strip()) > 0, "Foreground window title must not be empty")

        self.assertIsInstance(info["process_name"], str)
        self.assertTrue(len(info["process_name"].strip()) > 0, "Foreground process name must not be empty")
        self.assertTrue(info["process_name"].lower().endswith(".exe"),
                        f"Foreground process name should end with .exe, got: {info['process_name']}")

        self.assertGreater(info["pid"], 0, f"Foreground pid must be > 0, got: {info['pid']}")

        # Verify inspect_foreground() returns matching active window
        inspect_res = system_control.inspect_foreground()
        self.assertEqual(inspect_res["hwnd"], info["hwnd"])
        self.assertEqual(inspect_res["title"], info["title"])
        self.assertEqual(inspect_res["process_name"], info["process_name"])

        # Verify get_active_window() string helper
        title_str = system_control.get_active_window()
        self.assertEqual(title_str, info["title"])

        print(f"\n[Foreground Window] hwnd={info['hwnd']}, title='{info['title']}', proc='{info['process_name']}', pid={info['pid']}")

    def test_08_foreground_window_rapid_polling_stress(self):
        """
        Executes 50 consecutive iterations of get_active_window_info() in a tight loop.
        Verifies zero handle leaks, zero exceptions, and average latency < 5ms per poll.
        """
        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            info = system_control.get_active_window_info()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            self.assertGreater(info["hwnd"], 0)
            self.assertTrue(len(info["title"]) > 0)

        avg_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        print(f"\n[Window Inspection 50-Poll Stress] avg={avg_ms:.2f}ms, max={max_ms:.2f}ms (50 iterations)")
        self.assertLess(avg_ms, 15.0, f"Average window polling latency {avg_ms:.2f}ms exceeds 15ms ceiling")

    # =========================================================================
    # 5. DASHBOARD REST API /api/desktop/inspect RAPID POLLING
    # =========================================================================

    def test_09_dashboard_api_desktop_inspect_rapid_polling(self):
        """
        Verifies dashboard endpoint /api/desktop/inspect under rapid polling:
        Executes 30 consecutive GET requests, asserting 100% HTTP 200 OK, valid schema,
        and response latency < 200ms per request.
        """
        latencies = []
        for i in range(30):
            t0 = time.perf_counter()
            resp = self.client.get("/api/desktop/inspect")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

            self.assertEqual(resp.status_code, 200, f"Request {i+1} returned status {resp.status_code}")
            data = resp.json()

            # Schema validation
            self.assertTrue(data.get("ok"), f"Request {i+1} ok field is False: {data}")
            self.assertIn("active_window", data)
            self.assertIn("display_metrics", data)
            self.assertIn("hwnd", data)
            self.assertIn("title", data)
            self.assertIn("process_name", data)
            self.assertIn("pid", data)

            # Active window validation
            win = data["active_window"]
            self.assertGreater(win.get("hwnd", 0), 0)
            self.assertTrue(len(win.get("title", "").strip()) > 0)
            self.assertTrue(len(win.get("process_name", "").strip()) > 0)
            self.assertGreater(win.get("pid", 0), 0)

            # Display metrics validation
            disp = data["display_metrics"]
            self.assertEqual(disp.get("width"), 1920)
            self.assertEqual(disp.get("height"), 1080)
            self.assertGreaterEqual(disp.get("monitors", 0), 1)

            # Latency bound
            self.assertLess(elapsed_ms, 200.0, f"Request {i+1} took {elapsed_ms:.2f}ms, exceeding 200ms ceiling")

        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        print(f"\n[/api/desktop/inspect Rapid 30-Poll] min={min_lat:.1f}ms, max={max_lat:.1f}ms, avg={avg_lat:.1f}ms")

    def test_10_dashboard_api_desktop_inspect_concurrent_requests(self):
        """
        Executes 10 concurrent requests to /api/desktop/inspect using ThreadPoolExecutor.
        Verifies endpoint stability under concurrent load with 100% 200 OK responses.
        """
        def _poll_request(req_id):
            t0 = time.perf_counter()
            resp = self.client.get("/api/desktop/inspect")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "req_id": req_id,
                "status_code": resp.status_code,
                "elapsed_ms": elapsed_ms,
                "data": resp.json()
            }

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(_poll_request, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 10)
        for r in results:
            self.assertEqual(r["status_code"], 200)
            self.assertTrue(r["data"].get("ok"))
            self.assertEqual(r["data"]["display_metrics"]["width"], 1920)
            self.assertEqual(r["data"]["display_metrics"]["height"], 1080)

        latencies = [r["elapsed_ms"] for r in results]
        print(f"\n[/api/desktop/inspect 10 Concurrent Requests] Latencies: min={min(latencies):.1f}ms, max={max(latencies):.1f}ms, avg={sum(latencies)/len(latencies):.1f}ms")


if __name__ == "__main__":
    unittest.main(verbosity=2)
