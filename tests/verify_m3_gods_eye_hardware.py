"""
verify_m3_gods_eye_hardware.py — Comprehensive Verification Suite for Milestone M3.
========================================================================================
Verifies Subsystems R3 (God's Eye Visual Workspace Intelligence) and R4 (OS Hardware Controls):
1. God's Eye & Visual Workspace Intelligence (R3):
   - Desktop screen capture execution in <500ms pinned to 1920x1080.
   - Non-empty PNG artifact persistence in runtime/latest_screen.png and assets/screenshots/.
   - Thread desktop attachment (_attach_input_desktop) before capture.
   - Foreground window focus, hwnd, active window title, and process name inspection.
2. Hardware Vitals Reporting (R4):
   - Hardware vitals payload containing explicit top-level fields:
     ram_used_gb, ram_total_gb, ram_free_gb, drive_c_free_gb, drive_f_free_gb, cpu_percent.
3. Master Audio Control & Hardware Readback (R4):
   - Pycaw 2.x breaking change fix (speakers.EndpointVolume).
   - Setting volume 0-100% with hardware readback verification.
   - Master mute and unmute controls.
4. Command Router Harmonization & Safe Power States (R4):
   - Harmonization of 'volume' action to 'system_vol' dispatcher.
   - Safe execution of power states (lock, sleep, restart, shutdown) with dry_run and cancel support.
5. Dashboard REST API Endpoints:
   - GET /api/pc returning explicit top-level GB vitals.
   - GET /api/desktop/inspect returning active window metadata and display metrics.
   - GET/POST /api/audio/volume and GET/POST /api/audio/mute endpoints.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from PIL import Image

# Setup paths
JARVIS_ROOT = Path(__file__).resolve().parent.parent
if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))

import actions.system_control as system_control
import perception.screen_capture as screen_capture
import actions.computer_settings as computer_settings
from core.command_router import get_command_router
from fastapi.testclient import TestClient
from dashboard import app


class TestMilestoneM3Verification(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Store original master volume to cleanly restore after test run
        vol_info = system_control.get_volume()
        cls.orig_volume = vol_info.get("volume", 50)
        cls.orig_mute = vol_info.get("is_muted", False)

    @classmethod
    def tearDownClass(cls):
        # Restore original system volume and mute state
        try:
            system_control.set_volume(cls.orig_volume)
            system_control.mute_volume(cls.orig_mute)
        except Exception:
            pass

    # ==========================================================================
    # 1. R3: GOD'S EYE & VISUAL WORKSPACE INTELLIGENCE
    # ==========================================================================

    def test_01_screen_capture_execution_latency_and_artifacts(self):
        """
        Verifies capture_screen() executes in <500ms, enforces 1920x1080 resolution,
        and persists non-empty PNG artifacts to both runtime/latest_screen.png and assets/screenshots/.
        """
        t0 = time.perf_counter()
        res = system_control.capture_screen()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.get("status"), "success", f"Capture failed: {res}")
        self.assertLess(res.get("elapsed_ms", 999.0), 500.0, f"Latency exceeded: {res.get('elapsed_ms')}ms >= 500ms")
        self.assertEqual(res.get("width"), 1920, f"Width must be 1920, got {res.get('width')}")
        self.assertEqual(res.get("height"), 1080, f"Height must be 1080, got {res.get('height')}")

        # Check runtime/latest_screen.png exists and is non-empty
        latest_file = JARVIS_ROOT / "runtime" / "latest_screen.png"
        self.assertTrue(latest_file.exists(), f"Runtime artifact missing: {latest_file}")
        file_sz = latest_file.stat().st_size
        self.assertGreater(file_sz, 10_000, f"Artifact file too small (blank/empty): {file_sz} bytes")

        # Verify image dimensions with Pillow
        with Image.open(latest_file) as img:
            self.assertEqual(img.size, (1920, 1080), f"Persisted PNG size mismatch: {img.size}")
            self.assertEqual(img.format, "PNG", f"Artifact format must be PNG, got {img.format}")

        # Check assets/screenshots/ artifact exists
        saved_file = Path(res.get("file_path", ""))
        self.assertTrue(saved_file.exists(), f"Saved archive file missing: {saved_file}")
        self.assertGreater(saved_file.stat().st_size, 10_000)

    def test_02_perception_screen_capture_display(self):
        """
        Verifies perception.screen_capture.capture_display() pins to 1920x1080
        in <500ms and returns required status, file path, width, height, and elapsed_ms.
        """
        res = screen_capture.capture_display()
        self.assertEqual(res.get("status"), "success", f"capture_display failed: {res}")
        self.assertEqual(res.get("width"), 1920)
        self.assertEqual(res.get("height"), 1080)
        self.assertLess(res.get("elapsed_ms", 999.0), 500.0)

        out_path = Path(res.get("file_path", res.get("file", "")))
        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 10_000)

    def test_03_foreground_window_and_hwnd_inspection(self):
        """
        Verifies retrieval of active window metadata: hwnd, title, and process name.
        """
        win_info = system_control.get_active_window_info()
        self.assertIsInstance(win_info, dict)
        self.assertIn("hwnd", win_info)
        self.assertIn("title", win_info)
        self.assertIn("process_name", win_info)
        self.assertIn("pid", win_info)

        self.assertIsInstance(win_info["hwnd"], int)
        self.assertIsInstance(win_info["title"], str)
        self.assertGreater(len(win_info["title"]), 0)
        self.assertIsInstance(win_info["process_name"], str)

        # Also verify inspect_foreground() alias
        alias_info = system_control.inspect_foreground()
        self.assertEqual(win_info["hwnd"], alias_info["hwnd"])
        self.assertEqual(win_info["title"], alias_info["title"])

    # ==========================================================================
    # 2. R4: HARDWARE VITALS REPORTING
    # ==========================================================================

    def test_04_hardware_vitals_payload_structure(self):
        """
        Verifies get_system_vitals() returns explicit top-level fields:
        ram_used_gb, ram_total_gb, ram_free_gb, drive_c_free_gb, drive_f_free_gb, cpu_percent.
        """
        vitals = system_control.get_system_vitals()
        self.assertEqual(vitals.get("status"), "HEALTHY")

        required_fields = [
            "ram_used_gb",
            "ram_total_gb",
            "ram_free_gb",
            "drive_c_free_gb",
            "drive_f_free_gb",
            "cpu_percent",
        ]
        for field in required_fields:
            self.assertIn(field, vitals, f"Missing required top-level field '{field}' in vitals")
            val = vitals[field]
            self.assertIsInstance(val, (int, float), f"Field '{field}' must be numeric, got {type(val)}")

        # Value bounds validation
        self.assertGreater(vitals["ram_total_gb"], 0.0)
        self.assertGreater(vitals["ram_used_gb"], 0.0)
        self.assertGreaterEqual(vitals["ram_free_gb"], 0.0)
        self.assertLessEqual(vitals["ram_used_gb"], vitals["ram_total_gb"] + 0.1)

        self.assertGreater(vitals["drive_c_free_gb"], 0.0, "Drive C: free space must be > 0 GB")
        self.assertGreater(vitals["drive_f_free_gb"], 0.0, "Drive F: free space must be > 0 GB")
        self.assertGreaterEqual(vitals["cpu_percent"], 0.0)
        self.assertLessEqual(vitals["cpu_percent"], 100.0)

    # ==========================================================================
    # 3. R4: MASTER AUDIO CONTROL & HARDWARE READBACK (PYCAW 2.X)
    # ==========================================================================

    def test_05_pycaw_master_volume_control_and_verification(self):
        """
        Verifies master volume setter, Pycaw 2.x endpoint resolution,
        and hardware readback verification.
        """
        # Test setting to 35%
        res_35 = system_control.set_volume(35)
        self.assertEqual(res_35.get("status"), "success")
        self.assertTrue(res_35.get("verified"), "set_volume(35) must report verified=True")
        self.assertEqual(res_35.get("requested_volume"), 35)
        self.assertAlmostEqual(res_35.get("volume"), 35, delta=1)

        # Direct readback verification
        cur_vol = system_control.get_volume()
        self.assertEqual(cur_vol.get("status"), "success")
        self.assertAlmostEqual(cur_vol.get("volume"), 35, delta=1)

        # Test setting to 55%
        res_55 = system_control.set_volume(55)
        self.assertEqual(res_55.get("status"), "success")
        self.assertTrue(res_55.get("verified"), "set_volume(55) must report verified=True")
        self.assertAlmostEqual(res_55.get("volume"), 55, delta=1)

    def test_06_master_audio_mute_and_unmute(self):
        """
        Verifies mute_audio(), unmute_audio(), and mute_volume() with verification readback.
        """
        # Mute
        mute_res = system_control.mute_audio()
        self.assertEqual(mute_res.get("status"), "success")
        self.assertTrue(mute_res.get("is_muted"))
        self.assertTrue(mute_res.get("verified"))

        # Verify query matches
        self.assertTrue(system_control.get_volume().get("is_muted"))

        # Unmute
        unmute_res = system_control.unmute_audio()
        self.assertEqual(unmute_res.get("status"), "success")
        self.assertFalse(unmute_res.get("is_muted"))
        self.assertTrue(unmute_res.get("verified"))

        # Verify query matches
        self.assertFalse(system_control.get_volume().get("is_muted"))

    def test_07_computer_settings_pycaw_volume_set(self):
        """
        Verifies actions.computer_settings.volume_set() operates cleanly without Pycaw 2.x AttributeError.
        """
        scalar = computer_settings.volume_set(42)
        self.assertIsNotNone(scalar)
        self.assertAlmostEqual(scalar, 0.42, delta=0.03)

    # ==========================================================================
    # 4. R4: COMMAND ROUTER HARMONIZATION & SAFE POWER STATES
    # ==========================================================================

    def test_08_command_router_volume_harmonization(self):
        """
        Verifies mapping of action 'volume' to 'system_vol' dispatcher in core.command_router.
        """
        router = get_command_router()

        # Test set volume via router NLP
        env = router.process_command(
            "volume 40",
            channel="terminal",
            sender_id="local_user",
            extra_context={"authenticated_ingress": True},
            synthesize_audio=False
        )
        self.assertTrue(env.ok, f"Volume command failed: {env.output_text}")
        self.assertIn("40", env.output_text)

        # Test dispatcher directly with action='volume'
        res = system_control.handle_system_control_action("volume", parameters={"mode": "set", "value": 46})
        self.assertEqual(res.get("status"), "success")
        self.assertAlmostEqual(res.get("volume"), 46, delta=1)

    def test_09_safe_power_states_gating_and_dry_run(self):
        """
        Verifies power state transitions (lock, sleep, restart, shutdown) operate safely
        with dry_run and proper gating.
        """
        # Lock dry run
        res_lock = system_control.lock_pc(dry_run=True)
        self.assertEqual(res_lock.get("status"), "success")
        self.assertTrue(res_lock.get("dry_run"))

        # Sleep dry run
        res_sleep = system_control.sleep_pc(dry_run=True)
        self.assertEqual(res_sleep.get("status"), "success")
        self.assertTrue(res_sleep.get("dry_run"))

        # Restart dry run
        res_restart = system_control.restart_pc(delay_sec=10, dry_run=True)
        self.assertEqual(res_restart.get("status"), "success")
        self.assertTrue(res_restart.get("dry_run"))

        # Shutdown dry run
        res_shutdown = system_control.shutdown_pc(delay_sec=15, dry_run=True)
        self.assertEqual(res_shutdown.get("status"), "success")
        self.assertTrue(res_shutdown.get("dry_run"))

        # Dispatcher system_power routing
        res_disp = system_control.handle_system_control_action(
            "system_power",
            parameters={"mode": "restart", "dry_run": True, "delay_sec": 5}
        )
        self.assertEqual(res_disp.get("status"), "success")
        self.assertTrue(res_disp.get("dry_run"))

    # ==========================================================================
    # 5. DASHBOARD REST API ENDPOINTS
    # ==========================================================================

    def test_10_dashboard_api_pc_vitals(self):
        """
        Verifies GET /api/pc returns explicit top-level GB vitals fields and disk metrics.
        """
        resp = self.client.get("/api/pc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        for field in ["ram_used_gb", "ram_total_gb", "ram_free_gb", "drive_c_free_gb", "drive_f_free_gb", "cpu_percent"]:
            self.assertIn(field, data, f"Missing '{field}' in /api/pc")
            self.assertIsInstance(data[field], (int, float))

        # Check legacy compatibility fields remain intact
        for field in ["cpu", "mem", "disk_c", "disk_f", "disks", "procs"]:
            self.assertIn(field, data, f"Missing legacy field '{field}' in /api/pc")

    def test_11_dashboard_api_desktop_inspect(self):
        """
        Verifies GET /api/desktop/inspect returns active window metadata and display metrics.
        """
        resp = self.client.get("/api/desktop/inspect")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data.get("ok"))
        self.assertIn("active_window", data)
        self.assertIn("display_metrics", data)

        disp = data["display_metrics"]
        self.assertEqual(disp.get("width"), 1920)
        self.assertEqual(disp.get("height"), 1080)
        self.assertGreaterEqual(disp.get("monitors", 0), 1)

        win = data["active_window"]
        self.assertIn("hwnd", win)
        self.assertIn("title", win)
        self.assertIn("process_name", win)

    def test_12_dashboard_api_audio_endpoints(self):
        """
        Verifies /api/audio/volume and /api/audio/mute endpoints.
        """
        # GET volume
        get_vol = self.client.get("/api/audio/volume")
        self.assertEqual(get_vol.status_code, 200)
        vol_data = get_vol.json()
        self.assertTrue(vol_data.get("ok"))
        self.assertIn("volume", vol_data)

        # POST volume set to 48
        post_vol = self.client.post("/api/audio/volume", json={"level": 48})
        self.assertEqual(post_vol.status_code, 200)
        p_data = post_vol.json()
        self.assertTrue(p_data.get("ok"))
        self.assertTrue(p_data.get("verified"))
        self.assertAlmostEqual(p_data.get("volume"), 48, delta=1)

        # GET mute
        get_mute = self.client.get("/api/audio/mute")
        self.assertEqual(get_mute.status_code, 200)
        m_data = get_mute.json()
        self.assertTrue(m_data.get("ok"))
        self.assertIn("is_muted", m_data)

        # POST mute True
        mute_res = self.client.post("/api/audio/mute", json={"mute": True})
        self.assertEqual(mute_res.status_code, 200)
        self.assertTrue(mute_res.json().get("is_muted"))

        # POST mute False
        unmute_res = self.client.post("/api/audio/mute", json={"mute": False})
        self.assertEqual(unmute_res.status_code, 200)
        self.assertFalse(unmute_res.json().get("is_muted"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
