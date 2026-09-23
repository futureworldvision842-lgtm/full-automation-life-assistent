"""
tests/test_os_automation_m2.py
===============================================================================
Comprehensive Unit, Boundary, and Adversarial Test Suite for Milestone M2:
OS Sovereign Computer Control & Bilingual Automation Suite.

Test Matrix:
- Section 1: Bilingual NLP Command Parser (Roman Urdu & English Linguistic Matrices)
- Section 2: Desktop Application Lifecycle (Launch, Switch, Inspect, Graceful Terminate)
- Section 3: System Operations (Volume, Screen Capture, Hardware Vitals, Power States)
- Section 4: File & Workspace Automation (Search, CRUD, Backup Engine with SHA-256, Scratch)
- Section 5: Unified Master Dispatcher Interface Contract, Execution Receipts & Security Guard
- Section 6: Adversarial Robustness & Concurrent Multi-Action Stress
===============================================================================
"""

import os
import sys
import json
import time
import shutil
import unittest
import concurrent.futures
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from actions.bilingual_parser import parse_bilingual_command, BilingualParser, APP_ALIASES_MAP
from actions.system_control import (
    get_volume, set_volume, volume_up, volume_down, mute_volume,
    lock_pc, sleep_pc, restart_pc, shutdown_pc, hibernate_pc,
    capture_screen, get_system_diagnostics, handle_system_control_action
)
from actions.workspace_tools import (
    search_workspace, create_workspace_file, read_workspace_file,
    edit_workspace_file, delete_workspace_file, backup_repository,
    create_scratch_workspace, organize_workspace, handle_workspace_action
)
from actions.os_automation import (
    execute_pc_action, launch_app, switch_app, inspect_apps, terminate_app
)


class TestBilingualParserMatrix(unittest.TestCase):
    """Deep linguistic and syntactic verification for Bilingual NLP Parser."""

    def setUp(self):
        self.parser = BilingualParser()

    def test_01_roman_urdu_language_detection_matrix(self):
        urdu_samples = [
            "Chrome band karo",
            "MT5 chalao",
            "awaz barhao",
            "repo backup banao",
            "screenshot lo",
            "system ki sehat check karo",
            "konsi apps chal rahi hain",
            "vs code khol do",
            "awaz kam kar do",
            "pc lock karo",
            "nayee file banao test.txt"
        ]
        for s in urdu_samples:
            self.assertEqual(self.parser.detect_language(s), "ur", f"Failed language detection for: '{s}'")

    def test_02_english_language_detection_matrix(self):
        english_samples = [
            "launch Google Chrome",
            "terminate MT5",
            "increase system volume",
            "backup workspace repository",
            "capture screen",
            "system diagnostics and vitals",
            "list running applications",
            "open visual studio code",
            "set volume to 80%",
            "lock pc screen",
            "create file notes.txt"
        ]
        for s in english_samples:
            self.assertEqual(self.parser.detect_language(s), "en", f"Failed language detection for: '{s}'")

    def test_03_app_entity_and_alias_mapping_matrix(self):
        test_cases = [
            ("mt5", "MetaTrader 5"),
            ("metatrader", "MetaTrader 5"),
            ("chrome", "Google Chrome"),
            ("google chrome", "Google Chrome"),
            ("vs code", "Visual Studio Code"),
            ("vscode", "Visual Studio Code"),
            ("code", "Visual Studio Code"),
            ("cursor", "Cursor"),
            ("discord", "Discord"),
            ("spotify", "Spotify"),
            ("notepad", "Notepad"),
            ("calc", "Calculator"),
            ("calculator", "Calculator"),
            ("task manager", "Task Manager"),
            ("terminal", "Terminal")
        ]
        for raw, canonical in test_cases:
            res = self.parser.extract_app_target(f"launch {raw} now")
            self.assertIsNotNone(res, f"Could not extract alias for '{raw}'")
            self.assertEqual(res[1], canonical)

    def test_04_volume_parameter_matrix(self):
        # Set exact
        p1 = self.parser.extract_volume_parameter("set volume to 85%")
        self.assertEqual(p1.get("mode"), "set")
        self.assertEqual(p1.get("value"), 85)

        # Set exact Roman Urdu
        p2 = self.parser.extract_volume_parameter("awaz 40 karo")
        self.assertEqual(p2.get("mode"), "set")
        self.assertEqual(p2.get("value"), 40)

        # Volume Up
        p3 = self.parser.extract_volume_parameter("awaz barhao 15 points")
        self.assertEqual(p3.get("mode"), "up")
        self.assertEqual(p3.get("step"), 15)

        # Volume Down
        p4 = self.parser.extract_volume_parameter("volume kam karo 10%")
        self.assertEqual(p4.get("mode"), "down")
        self.assertEqual(p4.get("step"), 10)

        # Mute / Unmute
        p5 = self.parser.extract_volume_parameter("volume mute karo")
        self.assertEqual(p5.get("mode"), "mute")

        p6 = self.parser.extract_volume_parameter("awaz kholo")
        self.assertEqual(p6.get("mode"), "unmute")

    def test_05_malformed_and_boundary_nlp_inputs(self):
        # Empty string
        res_empty = parse_bilingual_command("")
        self.assertIn("translated_intent", res_empty)
        self.assertEqual(res_empty["confidence"], 0.0)

        # None
        res_none = parse_bilingual_command(None)
        self.assertIn("translated_intent", res_none)

        # Random symbols
        res_sym = parse_bilingual_command("!@#$%^&*()_+=-~`")
        self.assertIn("action", res_sym)


class TestSystemOperations(unittest.TestCase):
    """Verifies hardware volume, screen capture, power state simulations, and diagnostics."""

    def test_01_volume_set_and_query_ranges(self):
        for lvl in [0, 25, 50, 75, 100]:
            res = set_volume(lvl)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["volume"], lvl)

        # Out-of-bounds clamp test
        res_under = set_volume(-50)
        self.assertEqual(res_under["volume"], 0)

        res_over = set_volume(150)
        self.assertEqual(res_over["volume"], 100)

    def test_02_volume_mute_and_unmute(self):
        m_on = mute_volume(True)
        self.assertEqual(m_on["status"], "success")
        self.assertTrue(m_on["is_muted"])

        m_off = mute_volume(False)
        self.assertEqual(m_off["status"], "success")
        self.assertFalse(m_off["is_muted"])

    def test_03_screen_capture_and_visual_stats(self):
        res = capture_screen()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "screen_capture")
        self.assertIsNotNone(res["file_path"])
        self.assertTrue(Path(res["file_path"]).exists())
        self.assertGreater(res["width"], 0)
        self.assertGreater(res["height"], 0)
        self.assertIn("stats", res)
        self.assertIn("mean_brightness", res["stats"])
        # Clean up
        try:
            Path(res["file_path"]).unlink()
        except Exception:
            pass

    def test_04_system_diagnostics_structure_and_health(self):
        diag = get_system_diagnostics(top_n_procs=5)
        self.assertIn(diag["status"], ["HEALTHY", "WARNING"])
        self.assertIn("cpu", diag)
        self.assertIn("memory", diag)
        self.assertIn("disks", diag)
        self.assertIn("processes", diag)
        self.assertIn("network", diag)

        # Verify ranges
        self.assertGreaterEqual(diag["cpu"]["usage_pct"], 0.0)
        self.assertLessEqual(diag["cpu"]["usage_pct"], 100.0)
        self.assertGreaterEqual(diag["memory"]["usage_pct"], 0.0)
        self.assertLessEqual(diag["memory"]["usage_pct"], 100.0)
        self.assertGreater(diag["processes"]["total_active"], 0)

    def test_05_power_state_dry_run_dispatch(self):
        for mode in ["lock", "sleep", "restart", "shutdown", "hibernate"]:
            res = handle_system_control_action(action="system_power", target=mode, parameters={"force": False})
            self.assertEqual(res["status"], "success", f"Failed for power mode '{mode}'")


class TestWorkspaceAutomation(unittest.TestCase):
    """Verifies file search, CRUD, repository backup engine with SHA-256, and scratch spaces."""

    def setUp(self):
        self.test_scratch = BASE_DIR / "scratch" / "unit_test_m2_adv"
        self.test_scratch.mkdir(parents=True, exist_ok=True)
        self.test_file = self.test_scratch / "adv_test_doc.txt"

    def tearDown(self):
        if self.test_scratch.exists():
            shutil.rmtree(str(self.test_scratch), ignore_errors=True)

    def test_01_workspace_search_filters(self):
        # Search all python files
        res_py = search_workspace(pattern="*.py", max_results=10)
        self.assertEqual(res_py["status"], "success")
        self.assertGreater(res_py["total_found"], 0)
        for m in res_py["matches"]:
            self.assertTrue(m["name"].endswith(".py") or m["is_dir"])

        # Search nonexistent pattern
        res_none = search_workspace(pattern="non_existent_file_pattern_xyz_12345.xyz")
        self.assertEqual(res_none["status"], "success")
        self.assertEqual(res_none["total_found"], 0)

    def test_02_file_crud_operations(self):
        # Create
        cf = create_workspace_file(self.test_file, "Line A\nKEYWORD_TO_REPLACE\nLine C", overwrite=True)
        self.assertEqual(cf["status"], "success")
        self.assertTrue(self.test_file.exists())

        # Overwrite=False safety
        cf_safe = create_workspace_file(self.test_file, "Duplicate", overwrite=False)
        self.assertEqual(cf_safe["status"], "error")

        # Read
        rf = read_workspace_file(self.test_file)
        self.assertEqual(rf["status"], "success")
        self.assertEqual(rf["total_lines"], 3)
        self.assertIn("KEYWORD_TO_REPLACE", rf["content"])

        # Edit
        ef = edit_workspace_file(self.test_file, "KEYWORD_TO_REPLACE", "SUCCESSFULLY_REPLACED")
        self.assertEqual(ef["status"], "success")
        self.assertEqual(ef["replacements_made"], 1)

        # Verify Edit
        rf2 = read_workspace_file(self.test_file)
        self.assertIn("SUCCESSFULLY_REPLACED", rf2["content"])
        self.assertNotIn("KEYWORD_TO_REPLACE", rf2["content"])

        # Delete
        df = delete_workspace_file(self.test_file, send_to_trash=False)
        self.assertEqual(df["status"], "success")
        self.assertFalse(self.test_file.exists())

    def test_03_root_directory_deletion_protection(self):
        # Safety guard: attempting to delete workspace root MUST be blocked
        df_root = delete_workspace_file(BASE_DIR)
        self.assertEqual(df_root["status"], "blocked")

    def test_04_repository_backup_engine_integrity(self):
        bk = backup_repository()
        self.assertEqual(bk["status"], "success")
        self.assertEqual(bk["action"], "backup_repo")
        self.assertIsNotNone(bk["archive_path"])
        self.assertTrue(Path(bk["archive_path"]).exists())
        self.assertGreater(bk["file_count"], 0)
        self.assertGreater(bk["archive_size_bytes"], 0)
        self.assertEqual(len(bk["sha256"]), 64)
        # Cleanup
        try:
            Path(bk["archive_path"]).unlink()
        except Exception:
            pass

    def test_05_scratch_workspace_lifecycle(self):
        sw = create_scratch_workspace(name="adv_experiment")
        self.assertEqual(sw["status"], "success")
        sw_path = Path(sw["workspace_path"])
        self.assertTrue(sw_path.exists())
        self.assertTrue((sw_path / "README.md").exists())
        shutil.rmtree(sw_path, ignore_errors=True)


class TestOSAutomationMasterSuite(unittest.TestCase):
    """Verifies execute_pc_action master dispatcher, application lifecycle, and authorization."""

    def test_01_execute_pc_action_interface_receipt_schema(self):
        res = execute_pc_action("system diagnostics", origin="cli", is_owner=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "diagnostics")
        self.assertIn("bilingual_translation", res)
        self.assertIn("execution_receipt", res)

        rcpt = res["execution_receipt"]
        self.assertTrue(rcpt["receipt_id"].startswith("rcpt_"))
        self.assertIn("timestamp", rcpt)
        self.assertEqual(rcpt["origin"], "cli")
        self.assertTrue(rcpt["is_owner"])
        self.assertGreaterEqual(rcpt["execution_time_ms"], 0.0)

    def test_02_execute_pc_action_bilingual_roman_urdu_receipts(self):
        urdu_tests = [
            ("repo backup banao", "file_op"),
            ("screenshot lo", "screen_capture"),
            ("awaz 65 karo", "system_vol"),
            ("system ki sehat check karo", "diagnostics")
        ]
        for cmd, expected_action in urdu_tests:
            res = execute_pc_action(cmd, origin="discord", is_owner=True)
            self.assertEqual(res["status"], "success", f"Failed for '{cmd}'")
            self.assertEqual(res["action"], expected_action)
            self.assertEqual(res["bilingual_translation"]["input_lang"], "ur")

    def test_03_security_authorization_guard(self):
        # 1. Privileged power state with is_owner=False -> MUST BE BLOCKED
        res_power = execute_pc_action("shutdown pc", origin="web", is_owner=False)
        self.assertEqual(res_power["status"], "blocked")
        self.assertEqual(res_power["action"], "system_power")
        self.assertEqual(res_power["execution_receipt"]["result"]["status"], "blocked")

        # 2. Privileged app termination with is_owner=False -> MUST BE BLOCKED
        res_kill = execute_pc_action("kill chrome", origin="discord", is_owner=False)
        self.assertEqual(res_kill["status"], "blocked")
        self.assertEqual(res_kill["action"], "app_kill")

        # 3. Non-privileged diagnostic with is_owner=False -> ALLOWED
        res_diag = execute_pc_action("system diagnostics", origin="web", is_owner=False)
        self.assertEqual(res_diag["status"], "success")

    def test_04_desktop_application_lifecycle(self):
        # 1. Launch Notepad
        launch_res = launch_app("Notepad")
        self.assertEqual(launch_res["status"], "success")

        # 2. Inspect active applications
        insp_res = inspect_apps(filter_name="Notepad")
        self.assertEqual(insp_res["status"], "success")

        # 3. Terminate Notepad
        term_res = terminate_app("Notepad", force=True)
        self.assertEqual(term_res["status"], "success")

    def test_05_concurrent_multi_action_stress(self):
        commands = [
            ("system diagnostics", "cli", True),
            ("awaz 55 karo", "cli", True),
            ("screenshot lo", "discord", True),
            ("list running apps", "cli", True),
            ("system diagnostics", "web", True)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(execute_pc_action, cmd, origin, is_owner) for cmd, origin, is_owner in commands]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), len(commands))
        for r in results:
            self.assertEqual(r["status"], "success")
            self.assertIn("execution_receipt", r)


if __name__ == "__main__":
    unittest.main()
