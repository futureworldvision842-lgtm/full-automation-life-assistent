"""
J.A.R.V.I.S. Command Center Multi-Profile Intelligence & Autonomous Operations
================================================================================
Tier 1: Comprehensive Feature Coverage (Requirements R1 through R6)
================================================================================
Deterministic, opaque-box verification of primary functionality derived from:
  - ORIGINAL_REQUEST.md (## 2026-09-19T07:22:19Z)
  - PROJECT.md (Features 1 through 16, Requirements R1 through R6)

Coverage Matrix:
  - R1: Multi-Profile Chrome Routing (Features 1, 2, 3) — 7 tests
  - R2: WhatsApp Self-Chat Loop & Loop Prevention (Features 4, 5) — 6 tests
  - R3: Terminal Dashboard 3D Visualizations & Administrative Power (Features 6, 7, 8) — 6 tests
  - R4: Mobile Companion App & Host Synchronization (Features 9, 10, 11) — 6 tests
  - R5: Multi-Asset Quant Trading & DEX Screener Meme Coin Research (Features 12, 13, 14) — 7 tests
  - R6: Document Store & Sovereign Cognitive Memory (Feature 15) — 6 tests

Total Tier 1 Test Count: 38 tests (Requirement: >=5 per feature across R1-R6).
================================================================================
"""

import sys
import os
import re
import json
import time
import zipfile
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
    """Lazily loads root dashboard module via spec to avoid conflict with MQ3/dashboard."""
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
    """Lazily loads and returns FastAPI TestClient for Mobile Gateway (:8765)."""
    import mobile_control
    from starlette.testclient import TestClient
    return TestClient(mobile_control.app)


def auth_headers():
    return {"X-Jarvis-Internal-Token": internal_command_token()}


def mobile_auth_headers():
    from mobile_control import _load_mobile_token
    return {"X-Jarvis-Token": _load_mobile_token()}


# ==============================================================================
# R1: Multi-Profile Chrome Routing & Credential Routing
# ==============================================================================

class TestTier1_R1_Multi_Profile_Chrome_Routing(unittest.TestCase):
    """R1: Multi-Profile Chrome Intelligence & Credential Routing."""

    def test_r1_fundingpips_profile_2_specification(self):
        """Verify FundingPips automation specifies Chrome Profile 2 and hamidqureshi872@gmail.com."""
        from actions.fundingpips_automation import FUNDINGPIPS_EMAIL, FUNDINGPIPS_URL, FUNDINGPIPS_ACCOUNT
        self.assertEqual(FUNDINGPIPS_EMAIL, "hamidqureshi872@gmail.com")
        self.assertEqual(FUNDINGPIPS_ACCOUNT, "40000294403")
        self.assertIn("fundingpips.com", FUNDINGPIPS_URL)

        # Inspect open_and_prepare_fundingpips implementation logic for Profile 2
        import inspect
        from actions import fundingpips_automation
        src = inspect.getsource(fundingpips_automation.open_and_prepare_fundingpips)
        self.assertIn("Profile 2", src)
        self.assertIn("--profile-directory=", src)

    def test_r1_adeel_navigator_profile_42_specification(self):
        """Verify Chrome Adeel Navigator specifies Profile 42 and adeelvision3@gmail.com."""
        from perception.chrome_adeel_navigator import ChromeAdeelNavigator
        nav = ChromeAdeelNavigator()
        self.assertIsNotNone(nav.profile_info)
        self.assertEqual(nav.profile_info.profile_directory_name, "Profile 42")
        self.assertEqual(nav.profile_info.user_email, "adeelvision3@gmail.com")

    def test_r1_command_gateway_routes_fundingpips_to_profile_2(self):
        """Verify natural language command 'funding pips' routes to Profile 2 in command gateway."""
        from core.command_gateway import execute_command
        with patch("subprocess.Popen") as mock_popen, \
             patch("actions.fundingpips_automation.open_and_prepare_fundingpips", return_value={"ok": True, "output": "Portal opened"}):
            res = execute_command("funding pips", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("category"), "trading")
            data = res.get("data", {})
            self.assertEqual(data.get("profile_dir"), "Profile 2")

    def test_r1_command_gateway_routes_ai_to_profile_42(self):
        """Verify natural language command 'adeel vision chatgpt' routes to Profile 42 in command gateway."""
        from core.command_gateway import execute_command
        with patch("subprocess.Popen") as mock_popen:
            res = execute_command("adeel vision chatgpt kholo", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("category"), "browser")
            data = res.get("data", {})
            self.assertEqual(data.get("profile_dir"), "Profile 42")
            self.assertIn("chatgpt", data.get("destination", "").lower())

    def test_r1_os_automation_launch_app_profile_separation(self):
        """Verify launch_app cleanly branches between Profile 2 and Profile 42."""
        from actions.os_automation import launch_app
        with patch("subprocess.Popen") as mock_popen:
            # FundingPips launch
            res_fp = launch_app("funding pips")
            self.assertTrue(res_fp.get("ok"))
            self.assertEqual(res_fp.get("profile"), "Profile 2")

            # Adeel Vision launch
            res_av = launch_app("adeel vision chatgpt")
            self.assertTrue(res_av.get("ok"))
            self.assertEqual(res_av.get("profile"), "Profile 42")

    def test_r1_strict_prohibition_zero_mentions_in_codebase(self):
        """Forensic audit: verify 0 occurrences of prohibited user string across active codebase."""
        forbidden_prefix = "adeel"
        forbidden_suffix = "qureshi99"
        forbidden_term = forbidden_prefix + forbidden_suffix

        target_dirs = ["actions", "brain", "core", "database", "perception", "skills", "trading", "wa", "config"]
        matches = []
        for d in target_dirs:
            dir_path = BASE_DIR / d
            if not dir_path.exists():
                continue
            for root, _, files in os.walk(dir_path):
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", ".venv", "auth.archived", "auth.revoked"]):
                    continue
                for f in files:
                    if f.endswith((".py", ".js", ".json", ".sh", ".bat")):
                        fp = Path(root) / f
                        try:
                            content = fp.read_text(encoding="utf-8", errors="ignore")
                            if forbidden_term in content.lower():
                                matches.append(str(fp.relative_to(BASE_DIR)))
                        except Exception:
                            pass
        self.assertEqual(matches, [], f"Found forbidden term occurrences in: {matches}")

    def test_r1_credential_isolation_between_profiles(self):
        """Verify prop account credentials and AI profile subscriptions remain isolated."""
        from actions.fundingpips_automation import FUNDINGPIPS_EMAIL
        from perception.chrome_adeel_navigator import ChromeAdeelNavigator
        nav = ChromeAdeelNavigator()

        self.assertNotEqual(FUNDINGPIPS_EMAIL, nav.profile_info.user_email)
        self.assertIn("hamidqureshi872", FUNDINGPIPS_EMAIL)
        self.assertIn("adeelvision3", nav.profile_info.user_email)


# ==============================================================================
# R2: WhatsApp Self-Chat Command Loop ("Message Yourself" Support)
# ==============================================================================

class TestTier1_R2_WhatsApp_Self_Chat_Loop(unittest.TestCase):
    """R2: WhatsApp Self-Chat Command Loop & Loop Prevention."""

    def test_r2_baileys_source_supports_self_chat_detection(self):
        """Verify wa/jarvis_baileys.js contains logic recognizing fromMe === true for +923468053268."""
        baileys_file = BASE_DIR / "wa" / "jarvis_baileys.js"
        self.assertTrue(baileys_file.exists(), "wa/jarvis_baileys.js must exist")
        code = baileys_file.read_text(encoding="utf-8", errors="replace")

        # Verify self-chat identification
        self.assertIn("isSelfChat", code)
        self.assertIn("msg.key.fromMe", code)
        self.assertIn("923468053268", code)

    def test_r2_baileys_loop_mitigation_layers_exist(self):
        """Verify all 4 loop prevention layers exist in wa/jarvis_baileys.js."""
        code = (BASE_DIR / "wa" / "jarvis_baileys.js").read_text(encoding="utf-8", errors="replace")
        # Layer 1: Outbound message ID tracking
        self.assertIn("jarvisSentIds", code)
        # Layer 2: Inbound deduplication
        self.assertIn("seen", code)
        # Layer 3: Heuristic regex signature filter
        self.assertIn("/^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\\[J\\.A\\.R\\.V\\.I\\.S\\.)/i", code)
        # Layer 4: Scope check (module scope Set instances)
        self.assertTrue("const jarvisSentIds = new Set();" in code or "let jarvisSentIds = new Set();" in code)

    def test_r2_baileys_syntax_validation(self):
        """Verify wa/jarvis_baileys.js compiles with Node.js with exit code 0."""
        import subprocess
        baileys_file = BASE_DIR / "wa" / "jarvis_baileys.js"
        res = subprocess.run(["node", "-c", str(baileys_file)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax check failed: {res.stderr}")

    def test_r2_dashboard_terminal_exec_accepts_whatsapp_channel(self):
        """Verify /api/terminal/exec accepts authenticated WhatsApp requests for +923468053268."""
        client = get_dashboard_client()
        payload = {
            "command": "vitals",
            "channel": "whatsapp:923468053268",
            "owner_id": "923468053268"
        }
        headers = {
            **auth_headers(),
            "X-Jarvis-Owner-Channel": "whatsapp:923468053268"
        }
        res = client.post("/api/terminal/exec", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok") or data.get("executed"))
        self.assertIn("output", data)

    def test_r2_whatsapp_rate_limiter_governance(self):
        """Verify WhatsApp rate limiter allows authorized direct messages and parses DND commands."""
        from core.whatsapp_rate_limiter import WhatsAppRateLimiter
        limiter = WhatsAppRateLimiter.get_instance()
        # Direct reply must always be allowed
        allowed, reason = limiter.can_dispatch_whatsapp(is_user_reply=True)
        self.assertTrue(allowed)

        # DND command parsing
        parsed = WhatsAppRateLimiter.parse_dnd_command("tang mat kerna 2 ghantey")
        self.assertIsNotNone(parsed)
        action, duration = parsed
        self.assertEqual(action, "ENABLE")
        self.assertEqual(duration, 7200.0)

    def test_r2_self_chat_anti_loop_heuristic_regex_filter(self):
        """Verify regex signature matches J.A.R.V.I.S. formatted responses and spares user commands."""
        pattern = re.compile(r"^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)", re.IGNORECASE)
        # J.A.R.V.I.S. outputs
        self.assertTrue(bool(pattern.search("⚡ [J.A.R.V.I.S. WAKE-ON-MESSAGE ACTIVATED]")))
        self.assertTrue(bool(pattern.search("🤖 [J.A.R.V.I.S. COMMAND CENTER POWERS]")))
        self.assertTrue(bool(pattern.search("Sir, FundingPips portal desktop par khol diya hai.")))
        self.assertTrue(bool(pattern.search("[J.A.R.V.I.S.] Vitals are normal.")))

        # User commands
        self.assertFalse(bool(pattern.search("vitals batao")))
        self.assertFalse(bool(pattern.search("funding pips open karo")))
        self.assertFalse(bool(pattern.search("jarvis status")))


# ==============================================================================
# R3: Terminal Dashboard 3D Visualizations & Administrative Power
# ==============================================================================

class TestTier1_R3_Terminal_3D_Visualizations(unittest.TestCase):
    """R3: Terminal Dashboard 3D Visualizations & Administrative Power."""

    def test_r3_terminal_option_14_launches_3d_globe_and_world_monitor(self):
        """Verify command '3d globe' or option 14 routes to 3D Globe & World Monitor (:4173 & :3000)."""
        from core.command_gateway import execute_command
        res = execute_command("3d globe", channel="terminal", owner_id="owner", authorized=True)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("intent"), "gods_eye_3d")
        out = res.get("output", "")
        self.assertIn("4173", out)
        self.assertIn("3000", out)
        self.assertIn("CesiumJS", out)

    def test_r3_hardware_vitals_telemetry_fields(self):
        """Verify terminal get_live_hud_data() returns complete CPU, RAM, NVMe C:/F:, and GPU vitals."""
        from terminal import get_live_hud_data
        hud = get_live_hud_data()
        self.assertIn("cpu_pct", hud)
        self.assertIn("ram_pct", hud)
        self.assertIn("ram_used_gb", hud)
        self.assertIn("ram_total_gb", hud)
        self.assertIn("disk_c_free", hud)
        self.assertIn("disk_f_free", hud)
        self.assertIn("gpu_name", hud)
        self.assertIn("Quadro", hud["gpu_name"])
        self.assertIn("gpu_vram_used", hud)
        self.assertIn("gpu_vram_total", hud)

    def test_r3_virtual_workspaces_manager_5_screens(self):
        """Verify 5 Virtual Workspaces switcher registers all 5 sovereign workspaces."""
        from core.virtual_workspaces import get_workspace_manager
        ws_mgr = get_workspace_manager()
        all_ws = ws_mgr.list_all_workspaces()
        self.assertEqual(len(all_ws), 5)
        names = [w["name"] for w in all_ws]
        self.assertIn("MAIN", names)
        self.assertIn("TRADING", names)
        self.assertIn("WORLD", names)
        self.assertIn("DEV", names)
        self.assertIn("RESEARCH", names)

    def test_r3_virtual_workspaces_switching(self):
        """Verify switching between workspaces updates active workspace state."""
        from core.virtual_workspaces import get_workspace_manager
        ws_mgr = get_workspace_manager()
        res = ws_mgr.switch_workspace(2, bring_to_front=False)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("name"), "TRADING")
        self.assertEqual(ws_mgr.get_workspace(ws_mgr.active_workspace_id).name, "TRADING")

        # Switch back to MAIN
        res_main = ws_mgr.switch_workspace(1, bring_to_front=False)
        self.assertTrue(res_main.get("ok"))
        self.assertEqual(res_main.get("name"), "MAIN")

    def test_r3_virtual_workspaces_ascii_hud(self):
        """Verify format_hud_display() outputs ASCII grid containing all 5 workspaces."""
        from core.virtual_workspaces import get_workspace_manager
        hud = get_workspace_manager().format_hud_display()
        self.assertIn("5-SCREEN VIRTUAL WORKSPACES", hud)
        self.assertIn("WORKSPACE 1: MAIN", hud)
        self.assertIn("WORKSPACE 2: TRADING", hud)
        self.assertIn("WORKSPACE 3: WORLD", hud)
        self.assertIn("WORKSPACE 4: DEV", hud)
        self.assertIn("WORKSPACE 5: RESEARCH", hud)

    def test_r3_terminal_quick_action_dispatcher(self):
        """Verify terminal handle_quick_action handles choices 1, 11, 12, 14 without crashing."""
        from terminal import handle_quick_action
        with patch("actions.gods_eye_view.gods_eye_view", return_value="Launched"):
            self.assertTrue(handle_quick_action("1"))   # Vitals & Hardware
            self.assertTrue(handle_quick_action("11"))  # GPU Telemetry
            self.assertTrue(handle_quick_action("12"))  # 5 Virtual Screens
            self.assertTrue(handle_quick_action("14"))  # 3D World Globe


# ==============================================================================
# R4: Mobile Companion App & Host Synchronization
# ==============================================================================

class TestTier1_R4_Mobile_Companion_Sync(unittest.TestCase):
    """R4: Mobile Companion App & Host Synchronization."""

    def test_r4_mobile_remote_gateway_health_endpoint(self):
        """Verify Mobile Remote Gateway (:8765) responds to /api/health with authenticated_control: true."""
        client = get_mobile_client()
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("service"), "jarvis-mobile")
        self.assertTrue(data.get("authenticated_control"))

    def test_r4_standalone_apk_exists_and_is_valid_archive(self):
        """Verify JARVIS_MOBILE_COMPANION.apk exists on Desktop or project mirrors and is a valid zip/apk."""
        desktop_paths = [
            Path(os.environ.get("USERPROFILE", "C:\\Users\\user")) / "OneDrive" / "Desktop" / "JARVIS_MOBILE_COMPANION.apk",
            Path(os.environ.get("USERPROFILE", "C:\\Users\\user")) / "Desktop" / "JARVIS_MOBILE_COMPANION.apk",
            BASE_DIR / "mobile" / "jarvis-companion" / "dist" / "jarvis-companion-debug.apk",
            BASE_DIR / "mobile_app" / "dist" / "jarvis-companion-debug.apk",
        ]
        apk_path = next((p for p in desktop_paths if p.exists()), None)
        self.assertIsNotNone(apk_path, "JARVIS_MOBILE_COMPANION.apk must exist on Desktop or project path")
        self.assertGreater(apk_path.stat().st_size, 10000, "APK file size must be > 10 KB")

        # Verify it is a valid zip archive (APKs are zip format)
        self.assertTrue(zipfile.is_zipfile(apk_path), "APK must be a valid zip archive")

    def test_r4_mobile_avatar_hud_assets_and_states(self):
        """Verify interactive Arc Reactor avatar HUD states (idle, listening, thinking, speaking) exist."""
        avatar_file = BASE_DIR / "mobile" / "jarvis-companion" / "www" / "avatar.js"
        self.assertTrue(avatar_file.exists(), "avatar.js must exist in mobile companion www directory")
        content = avatar_file.read_text(encoding="utf-8")
        for state in ["idle", "listening", "thinking", "speaking"]:
            self.assertIn(state, content)

    def test_r4_mobile_screen_streaming_endpoint(self):
        """Verify /api/screen/stream is registered on Mobile Gateway."""
        client = get_mobile_client()
        routes = [r.path for r in client.app.routes]
        self.assertIn("/api/screen/stream", routes)

    def test_r4_mobile_terminal_remote_command_execution(self):
        """Verify mobile gateway /api/command runs administrative commands."""
        client = get_mobile_client()
        payload = {"command": "!Write-Output 'MOBILE_SYNC_OK'"}
        res = client.post("/api/command", json=payload, headers=mobile_auth_headers())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok") or data.get("success") or "output" in data)

    def test_r4_mobile_qr_pairing_and_local_ip_config(self):
        """Verify mobile gateway status endpoint provides valid local network IP config."""
        client = get_mobile_client()
        res = client.get("/api/mobile/status", headers=mobile_auth_headers())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("lan_ip", data)
        self.assertEqual(data.get("port"), 8765)


# ==============================================================================
# R5: Multi-Asset Quant Trading & DEX Screener Meme Coin Research
# ==============================================================================

class TestTier1_R5_Quant_Trading_And_DEX_Screener(unittest.TestCase):
    """R5: Multi-Asset Quant Trading & DEX Screener Meme Coin Research."""

    def test_r5_fundingpips_prop_risk_parameters(self):
        """Verify FundingPips #40000294403 enforces $750 max risk cap (0.75%) and 1:2.5 min RR."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        params = kernel.get_risk_parameters()
        self.assertEqual(params["account"], "40000294403")
        self.assertEqual(params["balance"], 100000.0)
        self.assertEqual(params["max_risk_cap"], 750.0)
        self.assertEqual(params["risk_pct"], 0.75)
        self.assertEqual(params["min_rr"], 2.5)

    def test_r5_risk_kernel_order_admission_evaluation(self):
        """Verify DeterministicRiskKernel accepts compliant trades and rejects high risk."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)

        # Compliant trade: $500 risk (< $750), 1:2.5 RR, 92 confluence
        res_good = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.50,
            rr_ratio=2.5,
            proposed_risk_usd=500.0
        )
        self.assertTrue(res_good.get("allowed"), f"Expected pass, got blockers: {res_good.get('blockers')}")
        self.assertEqual(res_good.get("decision"), "ADMITTED_PROPOSAL")

        # Non-compliant trade: $800 risk (> $750 ceiling)
        res_bad = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.80,
            rr_ratio=2.5,
            proposed_risk_usd=800.0
        )
        self.assertFalse(res_bad.get("allowed"))
        self.assertEqual(res_bad.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds" in b.lower() for b in res_bad.get("blockers", [])))

    def test_r5_dynamic_breakeven_lock_at_1r(self):
        """Verify dynamic breakeven locks stop-loss to entry price when gain reaches +1.0R."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel(account_id="40000294403")

        # +1.2R gain -> must trigger breakeven
        eval_be = kernel.evaluate_dynamic_breakeven(current_gain_r=1.2, entry_price=2700.0)
        self.assertTrue(eval_be["trigger"])
        self.assertEqual(eval_be["action"], "lock_sl_to_entry")
        self.assertEqual(eval_be["new_sl"], 2700.0)

        # +0.5R gain -> should not trigger
        eval_no_be = kernel.evaluate_dynamic_breakeven(current_gain_r=0.5, entry_price=2700.0)
        self.assertFalse(eval_no_be["trigger"])
        self.assertEqual(eval_no_be["action"], "maintain_sl")

    def test_r5_hft_dom_whale_wall_detection(self):
        """Verify HFT DOM microstructure engine detects institutional whale walls (>1,000 lots)."""
        from skills.high_frequency_trading import run as run_hft_skill
        # DOM test with 1,250 lots whale wall
        res = run_hft_skill({
            "action": "dom_depth",
            "symbol": "XAUUSD",
            "bids": [[2700.0, 1250.0], [2699.5, 400.0]],
            "asks": [[2700.5, 300.0], [2701.0, 450.0]]
        })
        self.assertIn("WHALE WALLS", res.upper())
        self.assertIn("1,000 LOTS", res.upper())

    def test_r5_hft_cvd_order_absorption(self):
        """Verify CVD engine evaluates order absorption divergence."""
        from skills.high_frequency_trading import run as run_hft_skill
        res = run_hft_skill({
            "action": "cvd_absorption",
            "symbol": "XAUUSD",
            "volume_delta": -5500.0,
            "price_delta": 4.5
        })
        self.assertIn("ABSORPTION", res)

    def test_r5_crypto_majors_ticker_support(self):
        """Verify crypto engine supports BTC, ETH, and SOL tickers."""
        from actions.freqtrade_engine import QuantitativeCryptoEngine, COINS
        self.assertIn("BTC", COINS)
        self.assertIn("ETH", COINS)
        self.assertIn("SOL", COINS)
        engine = QuantitativeCryptoEngine()
        self.assertIsNotNone(engine)

    def test_r5_dexscreener_meme_research_public_skill(self):
        """Verify free DEX Screener meme research skill provides top boosted, search, and deep research."""
        from skills.dexscreener_meme_research import MANIFEST, run as run_dex_skill
        self.assertEqual(MANIFEST["name"], "dexscreener_meme_research")

        # Test manifest actions
        actions = MANIFEST["parameters"]["properties"]["action"]["description"]
        self.assertIn("top_trending", actions)
        self.assertIn("search", actions)
        self.assertIn("deep_research", actions)

        # Test simulated run for top trending
        res = run_dex_skill({"action": "top_trending"})
        self.assertIsInstance(res, str)
        self.assertIn("DEX SCREENER", res)


# ==============================================================================
# R6: Document Store & Sovereign Cognitive Memory
# ==============================================================================

class TestTier1_R6_Document_Store_And_Memory(unittest.TestCase):
    """R6: Document Store & Sovereign Cognitive Memory."""

    def test_r6_mongodb_manager_initialization_and_fallback(self):
        """Verify MongoDBManager initializes and gracefully operates via SQLite fallback."""
        from database.mongodb_manager import MongoDBManager
        mgr = MongoDBManager()
        self.assertIn(mgr.mode, ["CONNECTED", "LOCAL_EMULATED"])
        status = mgr.status()
        self.assertTrue(status.get("ok"))
        self.assertIn("collections_count", status)

    def test_r6_document_insert_and_find(self):
        """Verify inserting and querying a JSON document persists correctly."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_e2e_col_{int(time.time())}"
        doc = {"ticker": "SOL", "risk_cap": 750.0, "status": "ACTIVE"}

        doc_id = mgr.insert_one(col, doc)
        self.assertIsNotNone(doc_id)

        # Find document
        found = mgr.find_one(col, {"ticker": "SOL"})
        self.assertIsNotNone(found)
        self.assertEqual(found.get("ticker"), "SOL")
        self.assertEqual(found.get("risk_cap"), 750.0)

        # Cleanup
        mgr.delete_one(col, {"ticker": "SOL"})

    def test_r6_document_find_multiple_and_limit(self):
        """Verify finding multiple documents obeys collection limits."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_multi_{int(time.time())}"

        for i in range(5):
            mgr.insert_one(col, {"item_id": i, "tag": "test_batch"})

        results = mgr.find(col, {"tag": "test_batch"}, limit=3)
        self.assertEqual(len(results), 3)

        # Clean up
        for i in range(5):
            mgr.delete_one(col, {"item_id": i})

    def test_r6_document_delete(self):
        """Verify document deletion removes record from document store."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"test_del_{int(time.time())}"
        doc_id = mgr.insert_one(col, {"key": "to_delete"})

        del_res = mgr.delete_one(col, {"key": "to_delete"})
        self.assertEqual(del_res.get("deleted_count"), 1)

        found_after = mgr.find_one(col, {"key": "to_delete"})
        self.assertIsNone(found_after)

    def test_r6_list_collections(self):
        """Verify list_collections returns newly created collection."""
        from database.mongodb_manager import get_mongodb_manager
        mgr = get_mongodb_manager()
        col = f"col_list_test_{int(time.time())}"
        mgr.insert_one(col, {"marker": "col_test"})

        cols = mgr.list_collections()
        self.assertIn(col, cols)

        # Clean up
        mgr.delete_one(col, {"marker": "col_test"})

    def test_r6_mongodb_skill_run_execution(self):
        """Verify skills/mongodb_skill.py parses actions and returns structured telemetry."""
        from skills.mongodb_skill import run as run_mongo_skill
        res_status = run_mongo_skill({"action": "status"})
        self.assertIn("DOCUMENT STORE STATUS", res_status)

        res_cols = run_mongo_skill({"action": "list_collections"})
        self.assertIn("collections", res_cols.lower())


if __name__ == "__main__":
    unittest.main()
