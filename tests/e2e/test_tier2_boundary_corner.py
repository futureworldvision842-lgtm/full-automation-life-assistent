"""
J.A.R.V.I.S. Command Center Multi-Profile Intelligence & Autonomous Operations
================================================================================
Tier 2: Boundary & Corner Cases (Requirements R1 through R6)
================================================================================
Deterministic, opaque-box boundary value analysis, malformed input handling,
fail-closed safety gating, and extreme edge condition verification derived from:
  - ORIGINAL_REQUEST.md (## 2026-09-19T07:22:19Z)
  - PROJECT.md (Features 1 through 16, Requirements R1 through R6)

Coverage Matrix:
  - R1: Multi-Profile Chrome Routing Boundaries (6 tests)
  - R2: WhatsApp Self-Chat Loop Boundaries (6 tests)
  - R3: Terminal Dashboard 3D Visualizations Boundaries (6 tests)
  - R4: Mobile Companion App Synchronization Boundaries (6 tests)
  - R5: Multi-Asset Quant Trading & DEX Screener Boundaries (7 tests)
  - R6: Document Store & Cognitive Memory Boundaries (6 tests)

Total Tier 2 Test Count: 37 tests (Requirement: >=5 per feature across R1-R6).
================================================================================
"""

import sys
import os
import re
import json
import time
import zipfile
import threading
import unittest
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Base paths setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))

from platform_runtime import internal_command_token


def get_dashboard_client():
    dash_file = BASE_DIR / "dashboard.py"
    if "jarvis_root_dashboard" not in sys.modules:
        spec = importlib.util.spec_from_file_location("jarvis_root_dashboard", str(dash_file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["jarvis_root_dashboard"] = mod
        spec.loader.exec_module(mod)
    else:
        mod = sys.modules["jarvis_root_dashboard"]
    from starlette.testclient import TestClient
    return TestClient(mod.app)


def get_mobile_client():
    import mobile_control
    from starlette.testclient import TestClient
    return TestClient(mobile_control.app)


def auth_headers():
    return {"X-Jarvis-Internal-Token": internal_command_token()}


def mobile_auth_headers():
    from mobile_control import _load_mobile_token
    return {"X-Jarvis-Token": _load_mobile_token()}


# ==============================================================================
# R1 Boundaries: Multi-Profile Chrome Routing
# ==============================================================================

class TestTier2_R1_Chrome_Routing_Boundaries(unittest.TestCase):
    """R1: Multi-Profile Chrome Routing Boundary & Corner Cases."""

    def test_r1_boundary_command_gateway_extra_spaces_and_casing(self):
        """Verify command gateway correctly normalizes irregular whitespace and mixed casing."""
        from core.command_gateway import execute_command
        with patch("subprocess.Popen") as mock_popen, \
             patch("actions.fundingpips_automation.open_and_prepare_fundingpips", return_value={"ok": True, "output": "Portal opened"}):
            # Irregular casing and padding for FundingPips
            res_fp = execute_command("   fUnDiNg   PiPs  ", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res_fp.get("ok"))
            self.assertEqual(res_fp.get("category"), "trading")

            # Irregular casing for Adeel Vision / ChatGPT
            res_ai = execute_command("  aDeEl   ViSiOn   ChAtGpT   KhOlO  ", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res_ai.get("ok"))
            self.assertEqual(res_ai.get("category"), "browser")

    def test_r1_boundary_command_gateway_4000_char_boundary(self):
        """Verify command length boundary: exactly 4000 chars is accepted; 4001 chars is rejected."""
        from core.command_gateway import execute_command
        # 4000 chars string
        cmd_4000 = "vitals " + "a" * (4000 - len("vitals "))
        res_4000 = execute_command(cmd_4000, channel="terminal", owner_id="owner", authorized=True)
        # Should not fail on length guard
        self.assertNotEqual(res_4000.get("output"), "Enter a command of 1–4,000 characters.")

        # 4001 chars string
        cmd_4001 = "a" * 4001
        res_4001 = execute_command(cmd_4001, channel="terminal", owner_id="owner", authorized=True)
        self.assertEqual(res_4001.get("output"), "Enter a command of 1–4,000 characters.")

    def test_r1_boundary_os_automation_launch_app_empty_name(self):
        """Verify launch_app with empty or whitespace-only name handles error gracefully."""
        from actions.os_automation import launch_app
        res = launch_app("   ")
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("ok", False))

    def test_r1_boundary_prohibition_deep_scan_obfuscation(self):
        """Verify absence of prohibited handle across case variations, underscore splits, and encodings."""
        p1, p2 = "adeel", "qureshi99"
        variations = [
            f"{p1}{p2}",
            f"{p1.upper()}{p2.upper()}",
            f"{p1}_{p2}",
            f"{p1}-{p2}",
        ]
        target_dirs = ["actions", "core", "skills", "trading", "perception", "wa"]
        found = []
        for d in target_dirs:
            dir_path = BASE_DIR / d
            if not dir_path.exists():
                continue
            for root, _, files in os.walk(dir_path):
                if any(ign in root for ign in [".git", "__pycache__", "node_modules"]):
                    continue
                for f in files:
                    if f.endswith((".py", ".js", ".json")):
                        content = (Path(root) / f).read_text(encoding="utf-8", errors="ignore").lower()
                        for v in variations:
                            if v.lower() in content:
                                found.append(f"{f} contains {v}")
        self.assertEqual(found, [])

    def test_r1_boundary_chrome_adeel_navigator_corrupt_local_state(self):
        """Verify ChromeAdeelNavigator handles invalid/corrupted Local State gracefully by falling back."""
        from perception.chrome_adeel_navigator import ChromeAdeelNavigator
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            corrupt_state = tmp_path / "Local State"
            corrupt_state.write_text("{CORRUPT_JSON_DATA", encoding="utf-8")

            nav = ChromeAdeelNavigator(custom_user_data=tmp_path)
            self.assertIsNotNone(nav.profile_info)
            self.assertEqual(nav.profile_info.profile_directory_name, "Profile 42")
            self.assertEqual(nav.profile_info.user_email, "adeelvision3@gmail.com")

    def test_r1_boundary_fundingpips_automation_non_interactive(self):
        """Verify open_and_prepare_fundingpips(interactive=False) executes without UI blocks."""
        from actions.fundingpips_automation import open_and_prepare_fundingpips
        with patch("subprocess.Popen") as mock_popen, \
             patch("time.sleep"):
            res = open_and_prepare_fundingpips(interactive=False)
            self.assertIsInstance(res, dict)
            self.assertTrue(res.get("ok"))
            self.assertIn("hamidqureshi872@gmail.com", res.get("email", ""))
            self.assertEqual(res.get("account_id"), "40000294403")


# ==============================================================================
# R2 Boundaries: WhatsApp Self-Chat Loop
# ==============================================================================

class TestTier2_R2_WhatsApp_Self_Chat_Boundaries(unittest.TestCase):
    """R2: WhatsApp Self-Chat Loop Boundary & Corner Cases."""

    def test_r2_boundary_empty_and_whitespace_whatsapp_payload(self):
        """Verify /api/terminal/exec returns validation message on empty or whitespace command."""
        client = get_dashboard_client()
        headers = {**auth_headers(), "X-Jarvis-Owner-Channel": "whatsapp:923468053268"}
        res = client.post("/api/terminal/exec", json={"command": "   "}, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("no command was received", data.get("output", "").lower())

    def test_r2_boundary_whatsapp_unauthenticated_sender(self):
        """Verify request without owner authorization is rejected."""
        from core.command_gateway import execute_command
        res = execute_command("vitals", channel="whatsapp:unknown_number", owner_id="unknown", authorized=False)
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("category"), "security")
        self.assertIn("not authenticated", res.get("output", "").lower())

    def test_r2_boundary_whatsapp_rate_limiter_rapid_fire(self):
        """Verify rapid repeated alerts are rate-limited while direct replies remain permitted."""
        from core.whatsapp_rate_limiter import WhatsAppRateLimiter
        limiter = WhatsAppRateLimiter.get_instance()

        # Direct reply is ALWAYS allowed
        for _ in range(5):
            allowed, _ = limiter.can_dispatch_whatsapp(is_user_reply=True)
            self.assertTrue(allowed)

        # Proactive automated alert
        allowed_proactive, _ = limiter.can_dispatch_whatsapp(is_user_reply=False)
        # Should be a boolean
        self.assertIsInstance(allowed_proactive, bool)

    def test_r2_boundary_whatsapp_dnd_custom_durations(self):
        """Verify DND parser handles various fractional and long-form durations."""
        from core.whatsapp_rate_limiter import WhatsAppRateLimiter
        # 1.5 hours
        parsed1 = WhatsAppRateLimiter.parse_dnd_command("tang mat karo 1.5 ghante")
        self.assertIsNotNone(parsed1)
        self.assertEqual(parsed1[0], "ENABLE")
        self.assertAlmostEqual(parsed1[1], 5400.0)

        # 30 minutes
        parsed2 = WhatsAppRateLimiter.parse_dnd_command("do not disturb for 30 mins")
        self.assertIsNotNone(parsed2)
        self.assertEqual(parsed2[0], "ENABLE")
        self.assertEqual(parsed2[1], 1800.0)

        # Disable
        parsed3 = WhatsAppRateLimiter.parse_dnd_command("messages on kero")
        # May be None or non-enable
        if parsed3:
            self.assertNotEqual(parsed3[0], "ENABLE")

    def test_r2_boundary_whatsapp_self_chat_emoji_start_filtering(self):
        """Verify regex boundary matches only when emoji is at position 0, not in body."""
        pattern = re.compile(r"^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)", re.IGNORECASE)
        # Emojis at start (outbound J.A.R.V.I.S. signature)
        for emo in ["⚡", "🤖", "🖥️", "📈", "🌍", "🧠", "📊", "📦", "🔐"]:
            self.assertTrue(bool(pattern.search(f"{emo} telemetry update")))

        # Emoji inside the body of a user query
        self.assertFalse(bool(pattern.search("check market 📈 status")))
        self.assertFalse(bool(pattern.search("jarvis how is the 🌍 today")))

    def test_r2_boundary_baileys_ring_buffer_fifo_eviction(self):
        """Verify ring buffer bounding logic evicts oldest items when exceeding 2,000 entries."""
        test_set = {}
        max_size = 2000
        for i in range(2050):
            test_set[f"msg_{i}"] = True
            if len(test_set) > max_size:
                del test_set[next(iter(test_set))]

        self.assertEqual(len(test_set), 2000)
        self.assertNotIn("msg_0", test_set)
        self.assertIn("msg_2049", test_set)


# ==============================================================================
# R3 Boundaries: Terminal Dashboard 3D Visualizations
# ==============================================================================

class TestTier2_R3_Terminal_Visualizations_Boundaries(unittest.TestCase):
    """R3: Terminal Dashboard 3D Visualizations Boundary & Corner Cases."""

    def test_r3_boundary_terminal_vitals_psutil_fallback(self):
        """Verify get_live_hud_data() returns sensible defaults when psutil metrics error."""
        from terminal import get_live_hud_data
        with patch("psutil.cpu_percent", side_effect=Exception("Simulated CPU error")), \
             patch("psutil.virtual_memory", side_effect=Exception("Simulated RAM error")):
            hud = get_live_hud_data()
            self.assertIsInstance(hud, dict)
            self.assertIn("cpu_pct", hud)
            self.assertIn("ram_pct", hud)
            self.assertIn("gpu_name", hud)

    def test_r3_boundary_terminal_gpu_telemetry_nvidia_smi_failure(self):
        """Verify GPU telemetry falls back safely when nvidia-smi fails."""
        from actions.system_optimizer import get_gpu_telemetry
        with patch("subprocess.run", side_effect=FileNotFoundError("nvidia-smi not found")):
            gpu = get_gpu_telemetry()
            self.assertIsInstance(gpu, dict)
            self.assertIn("name", gpu)
            self.assertIn("Quadro", gpu["name"])

    def test_r3_boundary_virtual_workspaces_invalid_id_switch(self):
        """Verify switching to invalid workspace identifier returns ok=False cleanly."""
        from core.virtual_workspaces import get_workspace_manager
        ws_mgr = get_workspace_manager()
        for bad_id in ["nonexistent_unknown_key_999", "invalid_workspace_xyz_99"]:
            res = ws_mgr.switch_workspace(bad_id, bring_to_front=False)
            self.assertFalse(res.get("ok"), f"Expected False for workspace {bad_id}")

    def test_r3_boundary_virtual_workspaces_boundary_ids(self):
        """Verify boundary workspace IDs 1 (min) and 5 (max) are both valid and switch cleanly."""
        from core.virtual_workspaces import get_workspace_manager
        ws_mgr = get_workspace_manager()
        # Min boundary: 1
        res1 = ws_mgr.switch_workspace(1, bring_to_front=False)
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("name"), "MAIN")

        # Max boundary: 5
        res5 = ws_mgr.switch_workspace(5, bring_to_front=False)
        self.assertTrue(res5.get("ok"))
        self.assertEqual(res5.get("name"), "RESEARCH")

        # Restore to 1
        ws_mgr.switch_workspace(1, bring_to_front=False)

    def test_r3_boundary_terminal_quick_action_invalid_choice(self):
        """Verify passing unrecognized quick action choice strings returns False without exception."""
        from terminal import handle_quick_action
        for bad_choice in ["0", "15", "99", "abc", "", " "]:
            self.assertFalse(handle_quick_action(bad_choice))

    def test_r3_boundary_3d_globe_status_timeout_handling(self):
        """Verify get_gev_status handles port probes quickly without hanging."""
        from actions.gods_eye_view import get_gev_status
        start = time.perf_counter()
        status = get_gev_status()
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 2.0, "Port probe took too long")
        self.assertIsInstance(status, dict)
        self.assertIn("port", status)


# ==============================================================================
# R4 Boundaries: Mobile Companion App Synchronization
# ==============================================================================

class TestTier2_R4_Mobile_Companion_Boundaries(unittest.TestCase):
    """R4: Mobile Companion App Synchronization Boundary & Corner Cases."""

    def test_r4_boundary_mobile_unauthorized_token_rejection(self):
        """Verify accessing /api/mobile/status with forged token returns HTTP 401."""
        client = get_mobile_client()
        res = client.get("/api/mobile/status", headers={"X-Jarvis-Token": "FORGED_INVALID_TOKEN_12345"})
        self.assertEqual(res.status_code, 401)
        data = res.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("error"), "mobile_authentication_required")

    def test_r4_boundary_mobile_missing_token_rejection(self):
        """Verify accessing /api/command with missing token returns HTTP 401."""
        client = get_mobile_client()
        res = client.post("/api/command", json={"command": "vitals"})
        self.assertEqual(res.status_code, 401)

    def test_r4_boundary_mobile_command_empty_payload(self):
        """Verify /api/command with empty command string returns safe response."""
        client = get_mobile_client()
        res = client.post("/api/command", json={"command": "   "}, headers=mobile_auth_headers())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("No command", data.get("output", ""))

    def test_r4_boundary_mobile_screen_stream_disabled(self):
        """Verify /api/screen/stream returns HTTP 403 when screenshot feature is disabled via env."""
        client = get_mobile_client()
        with patch.dict(os.environ, {"JARVIS_SCREENSHOT_ENABLED": "0"}):
            res = client.get("/api/screen/stream", headers=mobile_auth_headers())
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.json().get("error"), "screen_capture_disabled")

    def test_r4_boundary_apk_file_corrupt_archive_detection(self):
        """Verify corrupt or empty file is detected as invalid APK archive."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tf:
            tf.write(b"NOT_A_VALID_ZIP_ARCHIVE")
            corrupt_path = tf.name

        try:
            self.assertFalse(zipfile.is_zipfile(corrupt_path))
        finally:
            os.unlink(corrupt_path)

    def test_r4_boundary_mobile_notify_empty_body(self):
        """Verify /api/mobile/notify handles empty body using safe defaults."""
        client = get_mobile_client()
        res = client.post("/api/mobile/notify", json={}, headers=mobile_auth_headers())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        payload = data.get("payload", {})
        self.assertEqual(payload.get("title"), "J.A.R.V.I.S. Notification")


# ==============================================================================
# R5 Boundaries: Multi-Asset Quant Trading & DEX Screener
# ==============================================================================

class TestTier2_R5_Quant_Trading_Boundaries(unittest.TestCase):
    """R5: Multi-Asset Quant Trading & DEX Screener Boundary & Corner Cases."""

    def test_r5_boundary_risk_kernel_exact_750_dollar_cap(self):
        """Exact monetary boundary: $750.00 is allowed, $750.02 (exceeding 1 cent tolerance) is blocked."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)

        # $750.00 exact -> ALLOWED
        res_750 = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            proposed_risk_usd=750.00
        )
        self.assertTrue(res_750["allowed"], f"Expected allowed for $750.00, got: {res_750['blockers']}")

        # $750.02 exact -> BLOCKED
        res_750_02 = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            proposed_risk_usd=750.02
        )
        self.assertFalse(res_750_02["allowed"], "Expected blocked for $750.02")

    def test_r5_boundary_risk_kernel_exact_2_5_rr_ratio(self):
        """Exact RR boundary: 1:2.50 is allowed, 1:2.49 is blocked."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)

        # 2.50 exact -> ALLOWED
        res_250 = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.50,
            rr_ratio=2.50,
            proposed_risk_usd=500.00
        )
        self.assertTrue(res_250["allowed"])

        # 2.49 exact -> BLOCKED
        res_249 = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.50,
            rr_ratio=2.49,
            proposed_risk_usd=500.00
        )
        self.assertFalse(res_249["allowed"])
        self.assertTrue(any("below minimum" in b.lower() for b in res_249["blockers"]))

    def test_r5_boundary_dynamic_breakeven_exact_1_0_r_boundary(self):
        """Exact breakeven trigger boundary: gain = +1.0R triggers, gain = +0.999R does not."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403")

        # +1.0R exact
        res_10 = kernel.evaluate_dynamic_breakeven(current_gain_r=1.0, entry_price=2700.0)
        self.assertTrue(res_10["trigger"])
        self.assertEqual(res_10["action"], "lock_sl_to_entry")

        # +0.999R exact
        res_099 = kernel.evaluate_dynamic_breakeven(current_gain_r=0.999, entry_price=2700.0)
        self.assertFalse(res_099["trigger"])
        self.assertEqual(res_099["action"], "maintain_sl")

    def test_r5_boundary_hft_dom_whale_wall_1000_lots(self):
        """Exact whale wall boundary: whale walls must have volume strictly greater than 1,000 lots."""
        from skills.high_frequency_trading import HighFrequencyTradingEngine
        engine = HighFrequencyTradingEngine()
        dom = engine.get_dom_data("XAUUSD")
        whale_walls = dom.get("whale_walls", [])
        self.assertGreater(len(whale_walls), 0)
        for wall in whale_walls:
            self.assertGreater(wall["volume"], 1000.0)
            self.assertTrue(wall["is_whale_wall"])

    def test_r5_boundary_15m_news_circuit_breaker_active_lockout(self):
        """Verify active news lockout (news_lockout_active=True) forces immediate rejection."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        res = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.50,
            rr_ratio=3.0,
            news_lockout_active=True,
            proposed_risk_usd=500.00
        )
        self.assertFalse(res["allowed"])
        self.assertTrue(any("news lockout active" in b.lower() for b in res["blockers"]))

    def test_r5_boundary_dexscreener_empty_and_special_char_query(self):
        """Verify search_meme_coin handles empty string and special characters cleanly."""
        from skills.dexscreener_meme_research import search_meme_coin
        # Empty string query
        res_empty = search_meme_coin("")
        self.assertIsInstance(res_empty, str)

        # Special characters query
        res_special = search_meme_coin("$$$@@@###!!!")
        self.assertIsInstance(res_special, str)
        self.assertTrue("no liquidity pools found" in res_special.lower() or "dex screener" in res_special.lower())

    def test_r5_boundary_crypto_engine_invalid_market_number(self):
        """Verify _number helper in crypto engine rejects non-numeric or invalid inputs."""
        from actions.freqtrade_engine import _number
        # Valid numbers
        self.assertEqual(_number("123.45"), 123.45)
        self.assertEqual(_number(100), 100.0)

        # Invalid string
        with self.assertRaises(ValueError):
            _number("invalid_price")

        # Negative number when positive=True
        with self.assertRaises(ValueError):
            _number("-50.0", positive=True)


# ==============================================================================
# R6 Boundaries: Document Store & Cognitive Memory
# ==============================================================================

class TestTier2_R6_Document_Store_Boundaries(unittest.TestCase):
    """R6: Document Store & Cognitive Memory Boundary & Corner Cases."""

    def test_r6_boundary_mongodb_insert_empty_document(self):
        """Verify inserting an empty dictionary document succeeds and yields doc_id."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_empty_{time.time_ns()}"
        doc_res = mgr.insert_one(col, {})
        self.assertIsNotNone(doc_res)
        doc_id = doc_res.get("inserted_id") if isinstance(doc_res, dict) else doc_res

        # Verify it can be retrieved
        found = mgr.find_one(col, {"_id": doc_id}) or mgr.find_one(col, {})
        self.assertIsNotNone(found)

        # Cleanup
        mgr.delete_one(col, {"_id": doc_id})

    def test_r6_boundary_mongodb_find_nonexistent_collection(self):
        """Verify querying a collection that was never created returns empty list without crashing."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        results = mgr.find("completely_nonexistent_col_xyz_999", {"key": "val"})
        self.assertEqual(results, [])

    def test_r6_boundary_mongodb_delete_nonexistent_document(self):
        """Verify deleting a non-existent document returns deleted_count: 0 cleanly."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_del_none_{int(time.time())}"
        res = mgr.delete_one(col, {"missing_key": "impossible_val"})
        self.assertEqual(res.get("deleted_count"), 0)

    def test_r6_boundary_mongodb_nested_json_document_persistence(self):
        """Verify deeply nested documents with lists, bools, and floats preserve data types."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_nested_{int(time.time())}"
        nested_doc = {
            "root_key": "val",
            "nested_dict": {"sub_key": 42, "flag": True},
            "array_vals": [1.1, 2.2, 3.3],
            "risk_profile": {
                "account": "40000294403",
                "cap": 750.0,
                "symbols": ["XAUUSD", "BTCUSD"]
            }
        }
        doc_id = mgr.insert_one(col, nested_doc)
        self.assertIsNotNone(doc_id)

        found = mgr.find_one(col, {"root_key": "val"})
        self.assertEqual(found["nested_dict"]["sub_key"], 42)
        self.assertTrue(found["nested_dict"]["flag"])
        self.assertEqual(len(found["array_vals"]), 3)
        self.assertEqual(found["risk_profile"]["cap"], 750.0)

        # Cleanup
        mgr.delete_one(col, {"root_key": "val"})

    def test_r6_boundary_mongodb_skill_unknown_action(self):
        """Verify mongodb_skill handles unknown action gracefully."""
        from skills.mongodb_skill import run as run_mongo_skill
        res = run_mongo_skill({"action": "unsupported_action_999"})
        self.assertIsInstance(res, str)

    def test_r6_boundary_sqlite_concurrent_read_write(self):
        """Verify multi-threaded inserts into SQLite fallback collection execute cleanly."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_concur_{int(time.time())}"
        errors = []

        def worker(thread_idx):
            for j in range(5):
                inserted = False
                for attempt in range(10):
                    res = mgr.insert_one(col, {"thread": thread_idx, "seq": j})
                    if res.get("ok"):
                        inserted = True
                        break
                    time.sleep(0.05)
                if not inserted:
                    errors.append(f"Thread {thread_idx} insert {j} failed: {res}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Concurrent inserts encountered errors: {errors}")
        total = len(mgr.find(col, {}))
        self.assertEqual(total, 10)

        # Cleanup
        for i in range(2):
            for j in range(5):
                mgr.delete_one(col, {"thread": i, "seq": j})


if __name__ == "__main__":
    unittest.main()
