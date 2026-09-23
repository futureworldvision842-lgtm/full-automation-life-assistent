"""
tests/test_adversarial_m3_challenger2.py — Adversarial Stress Test Suite for Milestone M3.
===========================================================================================
Challenger 2 Empirical Verification:
1. Master Audio Volume & Pycaw 2.x Readback Stress Test:
   - Volume boundary inputs: 0%, 100%, -10%, 150%, float values, NaN handling.
   - Physical hardware readback verification via GetMasterVolumeLevelScalar() matching within 1%.
   - Rapid mute and unmute cycling (20 cycles) ensuring state coherence.
2. Hardware Vitals Payload Stress Test:
   - 50 iterations on get_system_vitals() and /api/pc.
   - Strict validation of ram_used_gb, ram_total_gb, ram_free_gb, drive_c_free_gb, drive_f_free_gb, cpu_percent.
   - Mathematical finiteness, positivity, and physical realism assertions.
3. Command Router Harmonization & Safe Power States:
   - Harmonization of 'volume' and 'system_vol' actions in handle_system_control_action.
   - Power state transitions (lock, sleep, restart, shutdown, cancel) with dry_run=True safety guards.
===========================================================================================
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path

# Setup paths
JARVIS_ROOT = Path(__file__).resolve().parent.parent
if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))

import actions.system_control as system_control
import actions.computer_settings as computer_settings
from core.command_router import get_command_router
from fastapi.testclient import TestClient
from dashboard import app


class TestMilestoneM3AdversarialChallenge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Store initial master volume and mute state to restore after test suite
        vol_info = system_control.get_volume()
        cls.orig_volume = vol_info.get("volume", 50)
        cls.orig_mute = vol_info.get("is_muted", False)
        cls.audio_endpoint = system_control._get_windows_audio_endpoint()

    @classmethod
    def tearDownClass(cls):
        # Cleanly restore host audio hardware state
        try:
            system_control.set_volume(cls.orig_volume)
            system_control.mute_volume(cls.orig_mute)
        except Exception:
            pass

    # =========================================================================
    # 1. MASTER AUDIO VOLUME & PYCAW 2.X READBACK STRESS TEST
    # =========================================================================

    def test_01_volume_boundary_clamping(self):
        """
        Tests volume boundary inputs: 0%, 100%, -10%, 150%, and float values.
        Asserts strict clamping to [0, 100].
        """
        boundary_cases = [
            (0, 0),
            (100, 100),
            (-10, 0),
            (-100, 0),
            (150, 100),
            (999, 100),
            (25.4, 25),
            (75.8, 75),
            (-0.1, 0),
            (100.9, 100),
        ]
        for inp, expected in boundary_cases:
            res = system_control.set_volume(inp)
            self.assertEqual(res.get("status"), "success", f"set_volume({inp}) failed")
            self.assertEqual(res.get("volume"), expected, f"Input {inp} expected clamped {expected}, got {res.get('volume')}")
            self.assertEqual(res.get("requested_volume"), expected)

            # Also verify actions.computer_settings.volume_set() clamping
            scalar = computer_settings.volume_set(inp)
            expected_scalar = expected / 100.0
            self.assertAlmostEqual(scalar, expected_scalar, delta=0.02, msg=f"computer_settings scalar mismatch for {inp}")

    def test_02_volume_nan_handling_adversarial(self):
        """
        Adversarial test: Tests passing NaN (math.nan / float('nan')) to set_volume.
        Empirically probes whether NaN is gracefully caught or raises ValueError.
        """
        # Probing system_control.set_volume with NaN
        nan_val = float("nan")
        try:
            res = system_control.set_volume(nan_val)
            # If implementation clamped or returned error dict:
            self.assertIn(res.get("volume"), (0, 50, 100))
        except ValueError as ex:
            # Documented empirical vulnerability: int(float('nan')) raises ValueError
            self.assertIn("cannot convert float NaN to integer", str(ex))

    def test_03_physical_hardware_readback_accuracy(self):
        """
        Tests physical hardware readback at discrete levels (25%, 50%, 75%).
        Directly queries Pycaw 2.x endpoint GetMasterVolumeLevelScalar() and
        asserts readback scalar matches within 1% (0.01).
        """
        if self.audio_endpoint is None:
            self.skipTest("No Windows CoreAudio endpoint available on host.")

        discrete_levels = [25, 50, 75]
        for level in discrete_levels:
            res = system_control.set_volume(level)
            self.assertEqual(res.get("status"), "success")
            self.assertTrue(res.get("verified"), f"Hardware verification failed for level {level}%")

            # Direct hardware query via pycaw endpoint
            hw_scalar = self.audio_endpoint.GetMasterVolumeLevelScalar()
            expected_scalar = level / 100.0
            diff = abs(hw_scalar - expected_scalar)
            self.assertLessEqual(
                diff,
                0.01,
                f"Physical hardware scalar {hw_scalar:.4f} deviated from expected {expected_scalar:.4f} by {diff:.4f} (> 1%)"
            )

    def test_04_rapid_mute_unmute_cycling(self):
        """
        Tests rapid mute and unmute cycling across 20 cycles.
        Asserts physical endpoint mute state and reported state remain 100% coherent.
        """
        for cycle in range(20):
            # 1. Mute
            res_mute = system_control.mute_audio()
            self.assertTrue(res_mute.get("is_muted"), f"Cycle {cycle}: mute_audio() did not set is_muted=True")
            self.assertTrue(res_mute.get("verified"))

            if self.audio_endpoint is not None:
                hw_mute = bool(self.audio_endpoint.GetMute())
                self.assertTrue(hw_mute, f"Cycle {cycle}: Physical hardware endpoint was not muted")

            query_mute = system_control.get_volume()
            self.assertTrue(query_mute.get("is_muted"))

            # 2. Unmute
            res_unmute = system_control.unmute_audio()
            self.assertFalse(res_unmute.get("is_muted"), f"Cycle {cycle}: unmute_audio() did not set is_muted=False")
            self.assertTrue(res_unmute.get("verified"))

            if self.audio_endpoint is not None:
                hw_unmute = bool(self.audio_endpoint.GetMute())
                self.assertFalse(hw_unmute, f"Cycle {cycle}: Physical hardware endpoint remained muted")

            query_unmute = system_control.get_volume()
            self.assertFalse(query_unmute.get("is_muted"))

    # =========================================================================
    # 2. HARDWARE VITALS PAYLOAD STRESS TEST
    # =========================================================================

    def test_05_hardware_vitals_payload_finiteness_and_realism(self):
        """
        Adversarially stress-tests get_system_vitals() and GET /api/pc across 50 iterations.
        Asserts presence, mathematical finiteness, positivity, and physical realism for:
        ram_used_gb, ram_total_gb, ram_free_gb, drive_c_free_gb, drive_f_free_gb, cpu_percent.
        """
        required_fields = [
            "ram_used_gb",
            "ram_total_gb",
            "ram_free_gb",
            "drive_c_free_gb",
            "drive_f_free_gb",
            "cpu_percent"
        ]

        for i in range(50):
            vitals_func = system_control.get_system_vitals()
            resp_api = self.client.get("/api/pc")
            self.assertEqual(resp_api.status_code, 200)
            vitals_api = resp_api.json()

            for source_name, payload in [("get_system_vitals()", vitals_func), ("/api/pc", vitals_api)]:
                for field in required_fields:
                    self.assertIn(field, payload, f"Iteration {i}: '{field}' missing from {source_name}")
                    val = payload[field]
                    self.assertIsInstance(val, (int, float), f"Iteration {i}: '{field}' is not numeric in {source_name}")
                    self.assertTrue(math.isfinite(val), f"Iteration {i}: '{field}' is not finite ({val}) in {source_name}")

                # Physical realism bounds
                self.assertGreater(payload["ram_total_gb"], 1.0, "Total RAM must be > 1.0 GB")
                self.assertGreater(payload["ram_used_gb"], 0.0, "Used RAM must be > 0.0 GB")
                self.assertGreaterEqual(payload["ram_free_gb"], 0.0, "Free RAM must be >= 0.0 GB")
                # Used RAM cannot exceed Total RAM (with 0.1 GB rounding allowance)
                self.assertLessEqual(
                    payload["ram_used_gb"],
                    payload["ram_total_gb"] + 0.1,
                    f"Used RAM ({payload['ram_used_gb']} GB) exceeds total ({payload['ram_total_gb']} GB)"
                )
                # Free disk space on C: and F:
                self.assertGreater(payload["drive_c_free_gb"], 0.0, "Drive C: free space must be > 0 GB")
                self.assertGreater(payload["drive_f_free_gb"], 0.0, "Drive F: free space must be > 0 GB")

                # CPU percentage bounds
                self.assertGreaterEqual(payload["cpu_percent"], 0.0, "CPU percent must be >= 0.0")
                self.assertLessEqual(payload["cpu_percent"], 100.0, "CPU percent must be <= 100.0")

    # =========================================================================
    # 3. COMMAND ROUTER HARMONIZATION & SAFE POWER STATES
    # =========================================================================

    def test_06_command_router_harmonization_volume_actions(self):
        """
        Tests handle_system_control_action with both 'volume' and 'system_vol' actions.
        Verifies mode='set', 'up', 'down', 'mute', and 'unmute'.
        """
        for act in ["volume", "system_vol"]:
            # Set
            r_set = system_control.handle_system_control_action(act, parameters={"mode": "set", "value": 44})
            self.assertEqual(r_set.get("status"), "success", f"Failed for action='{act}' mode='set'")
            self.assertAlmostEqual(r_set.get("volume"), 44, delta=1)

            # Up
            r_up = system_control.handle_system_control_action(act, parameters={"mode": "up", "step": 6})
            self.assertEqual(r_up.get("status"), "success", f"Failed for action='{act}' mode='up'")
            self.assertAlmostEqual(r_up.get("volume"), 50, delta=1)

            # Down
            r_down = system_control.handle_system_control_action(act, parameters={"mode": "down", "step": 10})
            self.assertEqual(r_down.get("status"), "success", f"Failed for action='{act}' mode='down'")
            self.assertAlmostEqual(r_down.get("volume"), 40, delta=1)

            # Mute
            r_mute = system_control.handle_system_control_action(act, parameters={"mode": "mute"})
            self.assertEqual(r_mute.get("status"), "success", f"Failed for action='{act}' mode='mute'")
            self.assertTrue(r_mute.get("is_muted"))

            # Unmute
            r_unmute = system_control.handle_system_control_action(act, parameters={"mode": "unmute"})
            self.assertEqual(r_unmute.get("status"), "success", f"Failed for action='{act}' mode='unmute'")
            self.assertFalse(r_unmute.get("is_muted"))

    def test_07_safe_power_states_gating_dry_run(self):
        """
        Tests safe power state commands ('lock', 'sleep', 'restart', 'shutdown', 'cancel')
        with dry_run=True, verifying safety guards prevent accidental reboot/shutdown during automated testing.
        """
        modes_to_test = ["lock", "sleep", "restart", "shutdown", "hibernate"]

        for mode in modes_to_test:
            # 1. Direct function call with dry_run=True
            if mode == "lock":
                res = system_control.lock_pc(dry_run=True)
            elif mode == "sleep":
                res = system_control.sleep_pc(dry_run=True)
            elif mode == "restart":
                res = system_control.restart_pc(delay_sec=10, dry_run=True)
            elif mode == "shutdown":
                res = system_control.shutdown_pc(delay_sec=15, dry_run=True)
            elif mode == "hibernate":
                res = system_control.hibernate_pc(dry_run=True)

            self.assertEqual(res.get("status"), "success", f"Power mode '{mode}' failed with dry_run=True")
            self.assertTrue(res.get("dry_run"), f"Power mode '{mode}' did not report dry_run=True")
            self.assertEqual(res.get("mode"), mode)

            # 2. Dispatcher handle_system_control_action call with dry_run=True
            disp_res = system_control.handle_system_control_action(
                "system_power",
                parameters={"mode": mode, "dry_run": True, "delay_sec": 10}
            )
            self.assertEqual(disp_res.get("status"), "success")
            self.assertTrue(disp_res.get("dry_run"))
            self.assertEqual(disp_res.get("mode"), mode)

        # 3. Default safety guard: Verify system_power defaults to dry_run=True when omitted
        default_res = system_control.handle_system_control_action(
            "system_power",
            parameters={"mode": "restart", "delay_sec": 10}
        )
        self.assertEqual(default_res.get("status"), "success")
        self.assertTrue(
            default_res.get("dry_run"),
            "CRITICAL: handle_system_control_action must default dry_run to True to prevent accidental OS reboot!"
        )

        # 4. Cancel shutdown operation
        cancel_res = system_control.cancel_shutdown()
        # When no shutdown is scheduled, Windows returns error 1116 (ERROR_SHUTDOWN_IS_NOT_IN_PROGRESS)
        # Verify cancel_shutdown handles or reports this cleanly
        self.assertIn("detail", cancel_res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
