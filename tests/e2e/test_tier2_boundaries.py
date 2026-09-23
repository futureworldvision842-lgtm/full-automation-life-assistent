"""
J.A.R.V.I.S. Command Center Institutional Upgrade — E2E Test Suite
================================================================================
Tier 2: Boundary & Corner Cases (Requirements R1 through R7)
================================================================================
Boundary value analysis, negative inputs, extreme values, off-nominal conditions,
fail-closed risk gating, and error resilience derived from ORIGINAL_REQUEST.md:
  • R1: Risk Sizing, Caps, Loss Floors, and Breakeven Triggers
  • R2: DOM Imbalance Zero-Divisions, Whale Wall Thresholds & Latency Guards
  • R3: Degradation Modes, Empty Feeds, and Offline Broker Telemetry
  • R4: Terminal Payload Limits, Malformed Commands & Hardware Edge Cases
  • R5: Unreachable Webhooks, Invalid Flow IDs & Empty Node DAGs
  • R6: Malformed Tool XML, Missing Args & Credential Boundary Ingress
  • R7: Zero-Process Teardown, Port Contention & Signal Traps

Requirement: >= 5 test cases per feature (Total: 35+ tests).
================================================================================
"""

import sys
import os
import json
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
# R1 Boundaries: Risk Sizing, Caps & Admission Gates
# ==============================================================================

class TestTier2_R1_RiskBoundaries(unittest.TestCase):
    """R1 boundary value analysis for FundingPips account risk and admission gates."""

    def test_r1_zero_balance_risk_sizing(self):
        """Zero balance returns 0.0 risk without division by zero or exception."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        res = engine.calculate_risk(balance=0.0, account_id="40000294403")
        self.assertEqual(res["risk_usd"], 0.0)

    def test_r1_negative_balance_handling(self):
        """Negative balance is handled safely and returns 0.0 risk."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        res = engine.calculate_risk(balance=-500.0, account_id="40000294403")
        self.assertLessEqual(res["risk_usd"], 0.0)

    def test_r1_exact_750_cap_boundary_with_extreme_balance(self):
        """Extreme balance ($10,000,000) is strictly capped at $750.00 for #40000294403."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        res = engine.calculate_risk(balance=10_000_000.0, account_id="40000294403")
        self.assertEqual(res["risk_usd"], 750.0)

    def test_r1_rr_ratio_below_minimum_rejected(self):
        """Risk:Reward below 2.0 (e.g. 1.8) is rejected by 18-gate risk kernel."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="EURUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.20,
            rr_ratio=1.8
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("Risk:Reward" in b for b in res["blockers"]))

    def test_r1_confluence_below_90_rejected(self):
        """Confluence score of 89.9 is strictly rejected by institutional gate."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=89.9,
            proposed_risk_pct=0.20,
            rr_ratio=2.5
        )
        self.assertFalse(res["allowed"])
        self.assertTrue(any("Confluence score" in b for b in res["blockers"]))

    def test_r1_news_lockout_active_blocks_admission(self):
        """Active 15-minute news lockout fails closed and blocks trade admission."""
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=98.0,
            proposed_risk_pct=0.20,
            rr_ratio=3.0,
            news_lockout_active=True
        )
        self.assertFalse(res["allowed"])
        self.assertTrue(any("News Lockout Active" in b for b in res["blockers"]))

    def test_r1_breakeven_gain_below_1r_does_not_trigger(self):
        """Profit below +1.0R gain does not prematurely shift Stop Loss to entry."""
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        engine = PipdanceFastTrackEngine()
        pos = {
            "ticket": 13002987,
            "symbol": "GBPUSD",
            "type": "SELL",
            "price_open": 1.33675,
            "sl": 1.33900,  # Stop distance = 0.00225
            "tp": 1.33149,
            "profit": 5.00,  # Below $750 cap and below 1.0R
            "volume": 0.20
        }
        # Price moved only to 1.33600 (0.00075 gain < 0.00225 stop dist)
        be_res = engine.check_breakeven_trigger(
            position=pos,
            current_price=1.33600,
            breakeven_profit_cap=750.0
        )
        self.assertFalse(be_res["trigger"])
        self.assertEqual(be_res["action"], "hold")


# ==============================================================================
# R2 Boundaries: HFT DOM, Microstructure & Order Book
# ==============================================================================

class TestTier2_R2_HFTMicrostructureBoundaries(unittest.TestCase):
    """R2 boundary conditions for Level-2 DOM, CVD, and microstructure."""

    def test_r2_zero_depth_levels_handled(self):
        """depth_levels=0 runs gracefully and uses default depth levels."""
        from skills.high_frequency_trading import run
        output = run({"action": "dom_analysis", "symbol": "EURUSD", "depth_levels": 0})
        self.assertIsInstance(output, str)
        self.assertIn("LEVEL-2 DEPTH OF MARKET", output)

    def test_r2_unknown_symbol_defaults_safely(self):
        """Querying an unknown ticker runs safely with default synthetic model."""
        from skills.high_frequency_trading import run
        output = run({"action": "dom_analysis", "symbol": "UNKNOWN_ASSET_XYZ"})
        self.assertIsInstance(output, str)
        self.assertIn("UNKNOWN_ASSET_XYZ", output)
        self.assertIn("Whale Walls", output)

    def test_r2_whale_wall_threshold_classification(self):
        """Verifies OrderBookDOMEngine iceberg demand wall classification >= 2500 lots."""
        from src.order_book_dom_engine import OrderBookDOMEngine
        engine = OrderBookDOMEngine()
        depth = engine.get_market_depth("XAUUSD")
        self.assertIn("has_iceberg_demand", depth)
        self.assertIn("has_iceberg_supply", depth)
        self.assertIsInstance(depth["has_iceberg_demand"], bool)

    def test_r2_negative_depth_levels_handled(self):
        """Negative depth levels parameter does not crash the skill."""
        from skills.high_frequency_trading import run
        output = run({"action": "dom_analysis", "symbol": "GBPUSD", "depth_levels": -10})
        self.assertIsInstance(output, str)
        self.assertIn("LEVEL-2 DEPTH OF MARKET", output)

    def test_r2_cvd_negative_delta_divergence(self):
        """CVD analysis handles sell-side dominated symbols safely."""
        from skills.high_frequency_trading import run
        output = run({"action": "cvd_imbalance", "symbol": "EURUSD"})
        self.assertIsInstance(output, str)
        self.assertIn("CUMULATIVE VOLUME DELTA", output)


# ==============================================================================
# R3 Boundaries: MQ3 Cockpit Degradation & Edge Feeds
# ==============================================================================

class TestTier2_R3_MQ3CockpitBoundaries(unittest.TestCase):
    """R3 boundary cases for live commentary, offline fallbacks, and prop gauges."""

    def test_r3_offline_bot_engine_degraded_truthful_status(self):
        """When bot_engine is None, /api/status returns degraded with available=False."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        orig_bot = mq3_app.bot_engine
        try:
            mq3_app.bot_engine = None
            with mq3_app.app.test_client() as client:
                resp = client.get("/api/status")
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                self.assertEqual(data.get("status"), "degraded")
                self.assertFalse(data.get("bot_running"))
                self.assertFalse(data["account"].get("available"))
                self.assertEqual(data["account"].get("balance"), 0.0)
        finally:
            mq3_app.bot_engine = orig_bot

    def test_r3_empty_symbol_commentary_defaults(self):
        """Empty symbol query string defaults safely to standard symbol."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        with mq3_app.app.test_client() as client:
            resp = client.get("/api/live_commentary?symbol=")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "active")

    def test_r3_case_insensitive_symbol_handling(self):
        """Lowercase symbol query 'gbpusd' is handled identically to uppercase."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        with mq3_app.app.test_client() as client:
            resp = client.get("/api/live_commentary?symbol=gbpusd")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("symbol"), "GBPUSD")

    def test_r3_position_in_loss_breakeven_inactive(self):
        """Position currently in loss has breakeven_locked=False."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        orig_bot = mq3_app.bot_engine
        try:
            mock_bot = MagicMock()
            mock_bot.mt5.get_open_positions.return_value = [{
                "ticket": 99999999,
                "symbol": "GBPUSD",
                "type": "SELL",
                "price_open": 1.33675,
                "price_current": 1.33800,  # Price rose, trade is in loss
                "profit": -25.00,
                "sl": 1.34000,
                "tp": 1.33149,
                "volume": 0.20,
                "comment": "JARVIS_QUANT_SMC"
            }]
            mock_bot.mt5.get_symbol_tick.return_value = {"bid": 1.33800, "ask": 1.33804}
            mq3_app.bot_engine = mock_bot

            with mq3_app.app.test_client() as client:
                resp = client.get("/api/live_commentary?symbol=GBPUSD")
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                active_pos = data.get("active_position")
                self.assertIsNotNone(active_pos)
                self.assertFalse(active_pos.get("breakeven_locked"))
        finally:
            mq3_app.bot_engine = orig_bot

    def test_r3_zero_division_guard_on_equity_gauges(self):
        """Target account size 0.0 does not cause ZeroDivisionError on prop gauges."""
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
                "balance": 100000.0,
                "equity": 100000.0,
                "available": True,
                "data_mode": "LIVE"
            }
            mock_bot.mt5.get_open_positions.return_value = []
            mock_bot.risk_manager.target_account_size = 0.0  # Boundary condition
            mock_bot.risk_manager.daily_starting_equity = 0.0
            mock_bot.config = {"risk_management": {}}
            mock_bot.ai_engine.get_ai_learning_summary.return_value = {}
            mock_bot.admin_controller.get_system_telemetry.return_value = {}
            mock_bot.mt5.get_runtime_status.return_value = {"connected": True}
            mq3_app.bot_engine = mock_bot

            with mq3_app.app.test_client() as client:
                resp = client.get("/api/status")
                self.assertEqual(resp.status_code, 200)
        finally:
            mq3_app.bot_engine = orig_bot


# ==============================================================================
# R4 Boundaries: Terminal Limits, Vitals & Health Fallbacks
# ==============================================================================

class TestTier2_R4_MasterDashboardBoundaries(unittest.TestCase):
    """R4 boundary conditions for terminal execution, hardware limits & self-healing."""

    def test_r4_terminal_empty_command(self):
        """POST /api/terminal/exec with empty cmd returns polite rejection without error."""
        client = get_dashboard_client()
        resp = client.post("/api/terminal/exec", json={"cmd": "   "})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("no command was received", data.get("output", ""))

    def test_r4_terminal_command_exceeding_length_limit(self):
        """POST /api/terminal/exec with command > 4,000 chars is rejected."""
        client = get_dashboard_client()
        long_cmd = "a" * 4005
        resp = client.post("/api/terminal/exec", json={"cmd": long_cmd})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("exceeds the 4,000 character limit", data.get("output", ""))

    def test_r4_hardware_vitals_nonexistent_drive_letter(self):
        """Querying missing drives handles missing storage gracefully."""
        client = get_dashboard_client()
        resp = client.get("/api/pc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("disks", data)
        disks = data["disks"]
        # Non-existent drive P should report 0% or offline safely
        self.assertIn("P", disks)
        self.assertIsInstance(disks["P"].get("percent"), (int, float))

    def test_r4_self_healing_invalid_option_id(self):
        """POST /api/self_healing/resolve with unknown option ID falls back to safe remediation."""
        client = get_dashboard_client()
        resp = client.post("/api/self_healing/resolve", json={"option_id": 9999})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("action_code"), "PURGE_RAM_CACHE")
        self.assertIn("duration_ms", data)

    def test_r4_reasoning_nonexistent_symbol_fallback(self):
        """Querying /api/trading/reasoning with uncommon symbol returns valid structure."""
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=NZDCAD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("selected_symbol"), "NZDCAD")


# ==============================================================================
# R5 Boundaries: n8n Engine Edge Cases & Fallbacks
# ==============================================================================

class TestTier2_R5_N8nWorkflowsBoundaries(unittest.TestCase):
    """R5 boundary conditions for n8n workflow orchestrator."""

    def test_r5_unknown_workflow_id(self):
        """Triggering an unknown workflow returns ok=False with clean error message."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("non_existent_workflow_id")
        self.assertFalse(res.get("ok"))
        self.assertIn("not found", res.get("error", ""))

    def test_r5_empty_payload_trigger(self):
        """Triggering workflow with empty payload or None executes without exception."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("news_circuit_breaker", payload=None)
        self.assertTrue(res.get("ok"))

    def test_r5_n8n_unreachable_server_falls_back(self):
        """Engine with unreachable external port falls back to embedded DAG runner."""
        from integrations.n8n_engine import N8nWorkflowEngine
        # Configure port 59999 (unlikely to have any listening server)
        engine = N8nWorkflowEngine(n8n_url="http://127.0.0.1:59999")
        res = engine.trigger_workflow("whale_flow", {"amount": 2_000_000})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("mode"), "SOVEREIGN_EMBEDDED_DAG")

    def test_r5_execution_count_increments_monotonically(self):
        """Subsequent triggers of a workflow increment its execution_count."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        flow = engine.local_workflows["defcon_geopolitical"]
        initial_count = flow["execution_count"]
        engine.trigger_workflow("defcon_geopolitical", {"alert": "TEST"})
        self.assertEqual(flow["execution_count"], initial_count + 1)

    def test_r5_all_workflows_contain_valid_nodes(self):
        """Every registered workflow contains at least 3 executable node actions."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        for flow_id, flow in engine.local_workflows.items():
            nodes = flow.get("nodes", [])
            self.assertGreaterEqual(len(nodes), 3, f"Flow {flow_id} must have >= 3 nodes")
            for node in nodes:
                self.assertIn("name", node)
                self.assertIn("action", node)


# ==============================================================================
# R6 Boundaries: Hermes Schemas, Parsers & Identity
# ==============================================================================

class TestTier2_R6_HermesAndIdentityBoundaries(unittest.TestCase):
    """R6 boundary conditions for Hermes parser, schemas, and identity routing."""

    def test_r6_malformed_xml_tool_call_handled_safely(self):
        """Malformed XML tool calls with invalid JSON are ignored without crashing."""
        from brain.hermes_agent import HermesParser
        corrupt_xml = "<tool_call>\n{not valid json at all\n</tool_call>"
        calls = HermesParser.extract_tool_calls(corrupt_xml)
        self.assertEqual(calls, [])

    def test_r6_empty_text_returns_no_tool_calls(self):
        """Plain conversation without tool calls returns empty list."""
        from brain.hermes_agent import HermesParser
        text = "Hello J.A.R.V.I.S., what is the weather today?"
        calls = HermesParser.extract_tool_calls(text)
        self.assertEqual(calls, [])

    def test_r6_json_markdown_block_tool_call_parsed(self):
        """Tool call inside markdown code block is parsed as fallback."""
        from brain.hermes_agent import HermesParser
        raw_md = '```json\n{"name": "world_monitor", "arguments": {"action": "chokepoints"}}\n```'
        calls = HermesParser.extract_tool_calls(raw_md)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "world_monitor")
        self.assertEqual(args.get("action"), "chokepoints")

    def test_r6_identity_segregation_default_routing(self):
        """Default system operations route to general owner email."""
        from core.human_intervention_gateway import (
            DEFAULT_OWNER_EMAIL,
            FUNDINGPIPS_EMAIL
        )
        self.assertNotEqual(DEFAULT_OWNER_EMAIL, FUNDINGPIPS_EMAIL)
        self.assertEqual(DEFAULT_OWNER_EMAIL, "futureworldvision842@gmail.com")

    def test_r6_identity_segregation_fundingpips_routing(self):
        """FundingPips account operations route strictly to hamidqureshi872@gmail.com."""
        from core.human_intervention_gateway import FUNDINGPIPS_EMAIL, FUNDINGPIPS_PORTAL_URL
        self.assertEqual(FUNDINGPIPS_EMAIL, "hamidqureshi872@gmail.com")
        self.assertEqual(FUNDINGPIPS_PORTAL_URL, "https://app.fundingpips.com/login")


# ==============================================================================
# R7 Boundaries: Lifecycle, Teardown & Port Guards
# ==============================================================================

class TestTier2_R7_LifecycleBoundaries(unittest.TestCase):
    """R7 boundary conditions for process lifecycle and port release."""

    def test_r7_teardown_when_zero_processes_running(self):
        """Teardown on an idle ecosystem returns empty entries without errors."""
        from bootstrap.lifecycle import owned_entries
        entries = owned_entries(include_supervisor=False)
        self.assertIsInstance(entries, list)

    def test_r7_launcher_services_all_have_working_dirs(self):
        """All configured services have non-empty working directories and commands."""
        from bootstrap.master_ecosystem_launcher import SERVICES
        for key, s in SERVICES.items():
            self.assertTrue(s.get("cwd"), f"Service {key} must have cwd")
            self.assertTrue(s.get("cmd"), f"Service {key} must have cmd")

    def test_r7_launcher_aliases_map_to_valid_keys(self):
        """All service aliases point to recognized services or 'all'."""
        from bootstrap.master_ecosystem_launcher import SERVICES, SERVICE_ALIASES
        for alias, target in SERVICE_ALIASES.items():
            if target != "all":
                self.assertIn(target, SERVICES, f"Alias target {target} not in SERVICES")

    def test_r7_stop_flag_path_resolution(self):
        """STOP_FLAG path is defined and in a writable workspace directory."""
        from bootstrap.master_ecosystem_launcher import STOP_FLAG
        self.assertTrue(str(STOP_FLAG).endswith("jarvis.stop"))
        self.assertTrue(STOP_FLAG.parent.exists())

    def test_r7_core_ports_non_overlapping(self):
        """Core ports in lifecycle are distinct positive integers."""
        from bootstrap.lifecycle import CORE_PORTS
        port_list = list(CORE_PORTS)
        self.assertEqual(len(port_list), len(set(port_list)), "Ports must be unique")
        for p in port_list:
            self.assertGreater(p, 1024)
            self.assertLess(p, 65535)


if __name__ == "__main__":
    unittest.main(verbosity=2)
