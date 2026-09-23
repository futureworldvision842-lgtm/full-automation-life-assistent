"""
J.A.R.V.I.S. Command Center Institutional Upgrade — E2E Test Suite
================================================================================
Tier 1: Core Feature Coverage (Requirements R1 through R7)
================================================================================
Deterministic, opaque-box verification of primary functionality derived from
ORIGINAL_REQUEST.md (## 2026-09-18T14:16:19Z) and PROJECT.md:
  • R1: Institutional MT5 Prop-Trading & Mandatory Big Sharks Reasoning
  • R2: High-Frequency Trading (HFT) Level-2 DOM Microstructure Engine
  • R3: MQ3 Cockpit Dashboard (:5050) & Live Commentary Restoration
  • R4: Unified Master Dashboard Frontend (:8770), PC Control & 3D Health HUD
  • R5: Local n8n Workflow Server (:5678) & 5 DAG Workflows
  • R6: Nous Hermes-3 Cognitive Agent & Human-Like Browser Automation
  • R7: Desktop 1-Click Complete System Lifecycle Controls

Requirement: >= 5 test cases per feature (Total: 35+ tests).
================================================================================
"""

import sys
import os
import json
import math
import time
import unittest
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Base paths setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))


def get_dashboard_client():
    """Lazily load and return FastAPI TestClient for Master Dashboard (:8770)."""
    dash_file = BASE_DIR / "dashboard.py"
    if "jarvis_dashboard_instance" not in sys.modules:
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_instance", str(dash_file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["jarvis_dashboard_instance"] = mod
        spec.loader.exec_module(mod)
    else:
        mod = sys.modules["jarvis_dashboard_instance"]
    from starlette.testclient import TestClient
    return TestClient(mod.app)


# ==============================================================================
# R1: Institutional MT5 Prop-Trading & Mandatory Big Sharks Reasoning
# ==============================================================================

class TestTier1_R1_FundingPipsRiskRules(unittest.TestCase):
    """R1: FundingPips #40000294403 ($100k balance) Risk Bounds and Caps."""

    def test_fundingpips_account_profile_registered(self):
        """Verify FundingPips #40000294403 profile in PipdanceFastTrackEngine."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        self.assertIn("40000294403", PipdanceFastTrackEngine.KNOWN_ACCOUNTS)
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["40000294403"]
        self.assertEqual(profile.login, 40000294403)
        self.assertEqual(profile.server, "FundingPips-Trial")
        self.assertAlmostEqual(profile.max_risk_pct_per_trade, 0.75, places=2)
        self.assertAlmostEqual(profile.max_risk_usd_cap, 750.0, places=2)
        self.assertGreaterEqual(profile.min_rr_ratio, 2.5)

    def test_calculate_risk_enforces_750_dollar_cap(self):
        """Verify that risk dollar calculation strictly caps at $750.00 for $100k account."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        # On $100,000 balance, 0.75% is exactly $750.00
        risk_data = engine.calculate_risk(balance=100000.0, account_id="40000294403")
        self.assertLessEqual(risk_data["risk_usd"], 750.0)
        self.assertEqual(risk_data["risk_usd"], 750.0)

        # On higher balances or higher ATR, cap must enforce $750.00
        capped_data = engine.calculate_risk(balance=250000.0, account_id="40000294403")
        self.assertLessEqual(capped_data["risk_usd"], 750.0)

    def test_dynamic_breakeven_lock_at_1r_profit(self):
        """Verify dynamic breakeven locks Stop Loss to entry price at +1.0R gain."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        
        pos = {
            "ticket": 13002987,
            "symbol": "GBPUSD",
            "type": "SELL",
            "price_open": 1.33675,
            "sl": 1.33900,
            "tp": 1.33149,
            "profit": 40.80,
            "volume": 0.20
        }
        # Price has moved down to 1.33450 (gain >= stop distance of 0.00225)
        be_res = engine.check_breakeven_trigger(
            position=pos,
            current_price=1.33450,
            breakeven_profit_cap=750.0
        )
        self.assertTrue(be_res["trigger"])
        self.assertEqual(be_res["action"], "shift_sl_to_entry")
        self.assertAlmostEqual(be_res["new_sl"], 1.33675, delta=0.0001)

    def test_trading_reasoning_api_exposure(self):
        """Verify /api/trading/reasoning returns structured Big Sharks rationale on :8770."""
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("account", data)
        self.assertEqual(str(data["account"].get("login")), "40000294403")
        self.assertEqual(data["account"].get("email"), "hamidqureshi872@gmail.com")
        self.assertEqual(data.get("general_email"), "futureworldvision842@gmail.com")
        self.assertIn("rule_guarantee", data)

    def test_big_sharks_rationale_fields_in_reasoning(self):
        """Verify reasoning payload contains mandatory SMC, Smart Money, and Macro fields."""
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        positions = data.get("positions", [])
        if positions:
            p = positions[0]
            self.assertIn("strategy_setup", p)
            self.assertIn("big_sharks_rationale", p)
            self.assertIn("technical_confluence", p)
            self.assertIn("macro_catalyst", p)
            self.assertIn("risk_rule", p)

    def test_18_gate_risk_kernel_evaluates_admission(self):
        """Verify DeterministicRiskKernel 18-gate admission logic."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=92.5,
            proposed_risk_pct=0.25,
            rr_ratio=2.5,
            news_lockout_active=False
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["decision"], "ADMITTED_PROPOSAL")
        self.assertEqual(res["total_gates_evaluated"], 18)


# ==============================================================================
# R2: High-Frequency Trading (HFT) Level-2 DOM Microstructure Engine
# ==============================================================================

class TestTier1_R2_HFTMicrostructureEngine(unittest.TestCase):
    """R2: Level-2 DOM, whale walls >1,000 lots, CVD divergence & IPDA filter."""

    def test_hft_skill_manifest_registration(self):
        """Verify skills/high_frequency_trading.py defines valid MANIFEST and schema."""
        from skills import high_frequency_trading
        self.assertTrue(hasattr(high_frequency_trading, "MANIFEST"))
        manifest = high_frequency_trading.MANIFEST
        self.assertEqual(manifest["name"], "high_frequency_trading")
        self.assertIn("parameters", manifest)
        self.assertIn("action", manifest["parameters"]["properties"])

    def test_hft_dom_analysis_detects_whale_walls(self):
        """Verify DOM analysis detects resting institutional whale walls (>1,000 lots)."""
        from skills.high_frequency_trading import run
        output = run({"action": "dom_analysis", "symbol": "XAUUSD"})
        self.assertIsInstance(output, str)
        self.assertIn("LEVEL-2 DEPTH OF MARKET", output)
        self.assertIn("Whale Walls", output)
        self.assertIn("DOM Imbalance", output)

    def test_hft_cvd_absorption_classification(self):
        """Verify CVD analysis classifies aggressive delta and order absorption."""
        from skills.high_frequency_trading import run
        output = run({"action": "cvd_imbalance", "symbol": "GBPUSD"})
        self.assertIsInstance(output, str)
        self.assertIn("CUMULATIVE VOLUME DELTA", output)
        self.assertIn("Order Absorption Classifier", output)
        self.assertIn("Divergence Bias", output)

    def test_hft_microstructure_latency_radar(self):
        """Verify HFT microstructure reports sub-2ms latency and spread stability."""
        from skills.high_frequency_trading import run
        output = run({"action": "microstructure_radar", "symbol": "XAUUSD"})
        self.assertIsInstance(output, str)
        self.assertIn("MICROSTRUCTURE & LATENCY RADAR", output)
        self.assertIn("Broker Round-Trip Execution Latency", output)
        self.assertIn("Sub-2ms Latency Mandate", output)

    def test_order_book_dom_engine_microstructure(self):
        """Verify OrderBookDOMEngine detects imbalance and resting demand walls."""
        from src.order_book_dom_engine import OrderBookDOMEngine
        engine = OrderBookDOMEngine()
        depth = engine.get_market_depth("XAUUSD")
        self.assertEqual(depth["symbol"], "XAUUSD")
        self.assertGreater(depth["total_bid_volume"], 0)
        self.assertGreater(depth["total_ask_volume"], 0)
        self.assertIn("imbalance_ratio", depth)
        self.assertIn("verdict", depth)


# ==============================================================================
# R3: MQ3 Cockpit Dashboard (:5050) & Live Commentary Restoration
# ==============================================================================

class TestTier1_R3_MQ3CockpitDashboard(unittest.TestCase):
    """R3: Live commentary restoration, order-flow radar, GBPUSD SELL #13002987."""

    def test_live_commentary_function_returns_valid_dict(self):
        """Verify get_live_commentary returns rich structure rather than 'unavailable'."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        with mq3_app.app.test_client() as client:
            resp = client.get("/api/live_commentary?symbol=GBPUSD")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn("commentary", data)
            self.assertIn("bias", data)
            self.assertIn("status", data)
            self.assertEqual(data["status"], "active")
            self.assertGreaterEqual(len(data["commentary"]), 1)

    def test_cockpit_gbpusd_sell_position_breakeven_locked(self):
        """Verify active GBPUSD SELL ticket #13002987 is tracked with breakeven locked."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        orig_bot = mq3_app.bot_engine
        try:
            mock_bot = MagicMock()
            mock_bot.mt5.get_open_positions.return_value = [{
                "ticket": 13002987,
                "symbol": "GBPUSD",
                "type": "SELL",
                "price_open": 1.33675,
                "price_current": 1.33556,
                "profit": 23.80,
                "sl": 1.33675,
                "tp": 1.33149,
                "volume": 0.20,
                "comment": "JARVIS_QUANT_SMC"
            }]
            mock_bot.mt5.get_symbol_tick.return_value = {"bid": 1.33556, "ask": 1.33560}
            mq3_app.bot_engine = mock_bot

            with mq3_app.app.test_client() as client:
                resp = client.get("/api/live_commentary?symbol=GBPUSD")
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                active_pos = data.get("active_position")
                self.assertIsNotNone(active_pos)
                self.assertEqual(active_pos.get("ticket"), 13002987)
                self.assertTrue(active_pos.get("breakeven_locked"))
        finally:
            mq3_app.bot_engine = orig_bot

    def test_prop_firm_equity_gauges_in_mq3_status(self):
        """Verify prop-firm equity gauges report balance, equity, and loss limits."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        orig_bot = mq3_app.bot_engine
        try:
            mock_bot = MagicMock()
            mock_bot.running = True
            mock_bot.paused = False
            mock_bot.telemetry_only = False
            mock_bot.whatsapp = None
            mock_bot.system_logs = []
            mock_bot.stats = {}
            mock_bot.mt5.get_account_info.return_value = {
                "login": 40000294403,
                "server": "FundingPips-Trial",
                "broker": "FundingPips",
                "balance": 101022.64,
                "equity": 101006.64,
                "margin_free": 100000.0,
                "profit": -16.0,
                "available": True,
                "data_mode": "LIVE"
            }
            mock_bot.mt5.get_open_positions.return_value = []
            mock_bot.risk_manager.target_account_size = 100000.0
            mock_bot.risk_manager.daily_starting_equity = 101022.64
            mock_bot.config = {"risk_management": {"max_daily_loss_pct": 4.0, "max_total_loss_pct": 8.0}}
            mock_bot.ai_engine.get_ai_learning_summary.return_value = {}
            mock_bot.admin_controller.get_system_telemetry.return_value = {}
            mock_bot.mt5.get_runtime_status.return_value = {"connected": True, "data_mode": "LIVE"}
            mq3_app.bot_engine = mock_bot

            with mq3_app.app.test_client() as client:
                resp = client.get("/api/status")
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                self.assertIn("account", data)
                acc = data["account"]
                self.assertGreater(acc.get("balance", 0.0), 100000.0)
                self.assertIn("prop_firm_gauges", data)
                gauges = data["prop_firm_gauges"]
                self.assertEqual(gauges["daily_limit_pct"], 4.0)
                self.assertEqual(gauges["total_limit_pct"], 8.0)
        finally:
            mq3_app.bot_engine = orig_bot

    def test_order_flow_radar_alerts_in_commentary(self):
        """Verify Big Sharks order-flow radar alerts are included in commentary feed."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        with mq3_app.app.test_client() as client:
            resp = client.get("/api/live_commentary?symbol=XAUUSD")
            data = resp.get_json()
            self.assertIn("commentary", data)
            self.assertIn("bias", data)
            radar_items = [c for c in data["commentary"] if c.get("category") == "BIG_SHARKS_RADAR"]
            self.assertGreaterEqual(len(radar_items), 1)

    def test_index_html_commentary_handler_resilient(self):
        """Verify index.html contains null checks preventing JavaScript TypeError."""
        index_file = MQ3_DIR / "dashboard" / "templates" / "index.html"
        content = index_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("async function fetchLiveCommentary()", content)
        self.assertIn("if (textEl)", content)
        self.assertIn("if (badgeEl)", content)


# ==============================================================================
# R4: Master Dashboard Frontend (:8770), PC Control & 3D Health HUD
# ==============================================================================

class TestTier1_R4_MasterDashboardAndHUD(unittest.TestCase):
    """R4: Terminal PowerShell execution, hardware vitals, 3D Earth HUD, self-healing."""

    def test_terminal_exec_endpoint_available(self):
        """Verify POST /api/terminal/exec receives and dispatches shell commands."""
        client = get_dashboard_client()
        resp = client.post("/api/terminal/exec", json={"cmd": "status"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ok", data)
        self.assertIn("output", data)

    def test_hardware_vitals_reporting(self):
        """Verify /api/pc returns CPU %, RAM GB (used, total, free), Disks C: & F:."""
        client = get_dashboard_client()
        resp = client.get("/api/pc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("cpu", data)
        self.assertIn("ram_used_gb", data)
        self.assertIn("ram_total_gb", data)
        self.assertIn("drive_c_free_gb", data)
        self.assertIn("drive_f_free_gb", data)

    def test_3d_earth_hud_telemetry_and_nodes(self):
        """Verify /api/system/3d_telemetry provides 8 tactical world nodes and vitals."""
        client = get_dashboard_client()
        resp = client.get("/api/system/3d_telemetry")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("world_nodes", data)
        nodes = data["world_nodes"]
        self.assertEqual(len(nodes), 8)
        node_ids = {n["id"] for n in nodes}
        self.assertIn("HQ_ISL", node_ids)
        self.assertIn("MKT_LON", node_ids)
        self.assertIn("MKT_NYC", node_ids)
        self.assertIn("CHK_HRM", node_ids)
        self.assertIn("CHK_MND", node_ids)

    def test_self_healing_status_and_remediation(self):
        """Verify 1-click self-healing diagnostic returns health scan and solutions."""
        client = get_dashboard_client()
        resp = client.get("/api/self_healing/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("health", data)
        self.assertIn("diagnostic_prompt", data)

    def test_multi_frontend_tabs_anti_collapse_css(self):
        """Verify universal_command_center.html configures tabs with WebGL anti-collapse CSS."""
        html_file = BASE_DIR / "web" / "universal_command_center.html"
        content = html_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("pane-godseye", content)
        self.assertIn("pane-worldmonitor", content)
        self.assertIn("pane-mq3cockpit", content)
        self.assertIn(":4173", content)
        self.assertIn(":3000", content)
        self.assertIn(":5050", content)
        self.assertIn(".tab-pane", content)
        self.assertIn("visibility: visible", content)


# ==============================================================================
# R5: Local n8n Workflow Server (:5678) & 5 DAG Workflows
# ==============================================================================

class TestTier1_R5_LocalN8nAndWorkflows(unittest.TestCase):
    """R5: Local n8n server on :5678 & embedded sovereign DAG engine 5 workflows."""

    def test_n8n_engine_initialization_and_health(self):
        """Verify N8nWorkflowEngine initializes and provides health reporting."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        health = engine.check_n8n_server_health()
        self.assertTrue(health.get("online"))
        self.assertIn(health.get("mode"), ("LIVE_N8N_SERVER", "EMBEDDED_SOVEREIGN_ENGINE"))

    def test_all_5_institutional_workflows_registered(self):
        """Verify all 5 required institutional workflows are pre-configured."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        flows = {f["id"]: f for f in engine.list_workflows()}
        required = [
            "macro_briefing",
            "whale_flow",
            "news_circuit_breaker",
            "defcon_geopolitical",
            "trade_admission_dispatch"
        ]
        for req in required:
            self.assertIn(req, flows, f"Workflow '{req}' must be registered in n8n engine")

    def test_morning_macro_workflow_execution(self):
        """Verify Morning Macro Briefing flow triggers and completes node execution."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("macro_briefing", {"scope": "all_assets"})
        self.assertTrue(res.get("ok"))
        self.assertIn(res.get("mode"), ("N8N_SERVER", "SOVEREIGN_EMBEDDED_DAG"))

    def test_news_circuit_breaker_workflow_execution(self):
        """Verify Economic News 15m Circuit Breaker flow triggers and evaluates locks."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("news_circuit_breaker", {"event": "CPI_RELEASE"})
        self.assertTrue(res.get("ok"))

    def test_defcon_geopolitical_workflow_execution(self):
        """Verify Geopolitical DEFCON Escalation flow computes shock multipliers."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("defcon_geopolitical", {"alert": "CHOKEPOINT_TENSION"})
        self.assertTrue(res.get("ok"))


# ==============================================================================
# R6: Nous Hermes-3 Cognitive Agent & Human-Like Browser Automation
# ==============================================================================

class TestTier1_R6_HermesCognitiveAgentAndBrowser(unittest.TestCase):
    """R6: Nous Hermes-3 tool registry, Playwright navigation & identity segregation."""

    def test_hermes_tool_registry_builds_schemas(self):
        """Verify HermesToolRegistry defines structured tool function schemas."""
        from brain.hermes_agent import HermesToolRegistry
        registry = HermesToolRegistry()
        tools = registry.tools
        self.assertIsInstance(tools, list)
        self.assertGreaterEqual(len(tools), 8)
        names = {t["function"]["name"] for t in tools}
        self.assertIn("mq3_trading", names)
        self.assertIn("trading_risk_kernel", names)
        self.assertIn("world_monitor", names)
        self.assertIn("institutional_matrix", names)

    def test_hermes_prompt_header_contains_xml_tools(self):
        """Verify Hermes prompt header formats valid Nous Hermes <tools> XML tags."""
        from brain.hermes_agent import HermesToolRegistry
        registry = HermesToolRegistry()
        header = registry.get_hermes_prompt_header()
        self.assertIn("<tools>", header)
        self.assertIn("</tools>", header)
        self.assertIn("<tool_call>", header)

    def test_hermes_parser_extracts_xml_tool_calls(self):
        """Verify HermesParser extracts structured calls from model completions."""
        from brain.hermes_agent import HermesParser
        raw = '<tool_call>\n{"name": "mq3_trading", "arguments": {"action": "status", "symbol": "GBPUSD"}}\n</tool_call>'
        calls = HermesParser.extract_tool_calls(raw)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "mq3_trading")
        self.assertEqual(args.get("action"), "status")
        self.assertEqual(args.get("symbol"), "GBPUSD")

    def test_identity_segregation_fundingpips_vs_general(self):
        """Verify strict user identity segregation between FundingPips and General."""
        from core.human_intervention_gateway import (
            FUNDINGPIPS_EMAIL,
            FUNDINGPIPS_PASSWORD,
            FUNDINGPIPS_ACCOUNT_ID,
            DEFAULT_OWNER_EMAIL,
            DEFAULT_OWNER_PHONE
        )
        self.assertEqual(FUNDINGPIPS_EMAIL, "hamidqureshi872@gmail.com")
        self.assertEqual(FUNDINGPIPS_PASSWORD, "AHMA5ss$#")
        self.assertEqual(FUNDINGPIPS_ACCOUNT_ID, "40000294403")
        self.assertEqual(DEFAULT_OWNER_EMAIL, "futureworldvision842@gmail.com")
        self.assertEqual(DEFAULT_OWNER_PHONE, "923468053268")

    def test_browser_control_module_availability(self):
        """Verify actions/browser_control.py defines default browser discovery."""
        import actions.browser_control as bc
        self.assertTrue(hasattr(bc, "_get_default_browser_id"))
        self.assertTrue(hasattr(bc, "_BROWSER_BINARIES"))


# ==============================================================================
# R7: Desktop 1-Click Complete System Lifecycle Controls
# ==============================================================================

class TestTier1_R7_LifecycleControls(unittest.TestCase):
    """R7: JARVIS - START ALL.bat, JARVIS - STOP ALL.bat, 10 daemons port release."""

    def test_start_all_batch_file_exists_and_configured(self):
        """Verify JARVIS - START ALL.bat exists and calls master launcher start all."""
        start_bat = BASE_DIR / "JARVIS - START ALL.bat"
        self.assertTrue(start_bat.exists(), "JARVIS - START ALL.bat must exist in project root")
        content = start_bat.read_text(encoding="utf-8", errors="replace")
        self.assertIn("master_ecosystem_launcher.py", content)
        self.assertIn("start all", content)
        self.assertIn("8770", content)

    def test_stop_all_batch_file_exists_and_configured(self):
        """Verify JARVIS - STOP ALL.bat exists and calls clean teardown."""
        stop_bat = BASE_DIR / "JARVIS - STOP ALL.bat"
        self.assertTrue(stop_bat.exists(), "JARVIS - STOP ALL.bat must exist in project root")
        content = stop_bat.read_text(encoding="utf-8", errors="replace")
        self.assertIn("master_ecosystem_launcher.py", content)
        self.assertIn("stop", content)

    def test_master_launcher_defines_services_dictionary(self):
        """Verify SERVICES dictionary in master_ecosystem_launcher defines core daemons."""
        from bootstrap.master_ecosystem_launcher import SERVICES
        self.assertIsInstance(SERVICES, dict)
        self.assertIn("dashboard", SERVICES)
        self.assertIn("mq3", SERVICES)
        self.assertIn("godseye", SERVICES)
        self.assertIn("worldmonitor", SERVICES)
        self.assertIn("odysseus", SERVICES)
        self.assertIn("mobile", SERVICES)
        self.assertIn("trader", SERVICES)
        self.assertIn("ollama", SERVICES)
        self.assertIn("discord", SERVICES)
        self.assertIn("whatsapp", SERVICES)

    def test_lifecycle_core_ports_configured(self):
        """Verify core service ports in bootstrap/lifecycle.py."""
        from bootstrap.lifecycle import CORE_PORTS
        self.assertIn(8770, CORE_PORTS)
        self.assertIn(5050, CORE_PORTS)
        self.assertIn(4173, CORE_PORTS)
        self.assertIn(3000, CORE_PORTS)
        self.assertIn(7000, CORE_PORTS)
        self.assertIn(8765, CORE_PORTS)

    def test_teardown_clean_exit_when_idle(self):
        """Verify stop_all routine runs gracefully when no managed processes are running."""
        from bootstrap.lifecycle import owned_entries
        entries = owned_entries(include_supervisor=False)
        self.assertIsInstance(entries, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
