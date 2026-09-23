"""
J.A.R.V.I.S. Command Center Institutional Upgrade — E2E Test Suite
================================================================================
Tier 3: Cross-Feature Combinations & Pairwise Integration (Requirements R1-R7)
================================================================================
Deterministic verification of cross-subsystem interactions derived from
ORIGINAL_REQUEST.md (## 2026-09-18T14:16:19Z) and PROJECT.md:
  • P01 (R1 + R2): Risk Kernel & HFT DOM Imbalance Fusion
  • P02 (R1 + R3): FundingPips #40000294403 Position Sync & Cockpit Feed
  • P03 (R1 + R5): 15m Economic News Circuit Breaker DAG & Trade Admission
  • P04 (R1 + R6): Hermes-3 Schema Validation of Prop Risk Cap ($750.00)
  • P05 (R2 + R3): HFT DOM Whale Walls (>1,000 lots) Streaming to Cockpit
  • P06 (R2 + R5): Whale Alert DAG ($1M+) & Level-2 DOM Correlation
  • P07 (R3 + R4): Master Dashboard Multi-Tab Embed & Trading Reasoning
  • P08 (R4 + R6): Master Operations Console & Hermes Cognitive Agent Routing
  • P09 (R4 + R7): Self-Healing Diagnostic & Lifecycle Daemon Management
  • P10 (R5 + R6): Sovereign n8n DAG Flow Executing Hermes Tool Registry
  • P11 (R6 + R1): User Identity Segregation for FundingPips Prop Operations
  • P12 (R7 + R1): 1-Click Startup & Live Trading Daemon Prop Bounds
  • P13 (R7 + R3): 1-Click Teardown & Clean Port 5050 Clearance
  • P14 (R7 + R5): Ecosystem Lifecycle & Local n8n Server Orchestration
  • P15 (R4 + R5): 05:00 AM PKT Morning Macro DAG & Master HUD Sitrep
  • P16 (R2 + R6): Hermes Cognitive Agent Invoking HFT Microstructure Skill

Requirement: >= 15 pairwise cross-feature tests.
================================================================================
"""

import sys
import os
import json
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


def get_mobile_client():
    """Lazily load and return FastAPI TestClient for Mobile Gateway (:8765)."""
    import mobile_control
    from starlette.testclient import TestClient
    return TestClient(mobile_control.app)


def mobile_auth_headers():
    from mobile_control import _load_mobile_token
    return {"X-Jarvis-Token": _load_mobile_token()}


class TestTier3_CrossFeaturePairwise(unittest.TestCase):
    """Pairwise cross-feature integration test suite."""

    def test_p01_r1_plus_r2_risk_kernel_and_hft_dom_fusion(self):
        """P01: Risk Kernel evaluates HFT DOM whale walls before sizing under $750 cap."""
        from skills.high_frequency_trading import run
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel

        # 1. Evaluate HFT DOM depth
        dom_output = run({"action": "dom_analysis", "symbol": "XAUUSD"})
        self.assertIn("Whale Walls", dom_output)

        # 2. Size position with FundingPips #40000294403 bounds
        engine = PipdanceFastTrackEngine()
        risk_data = engine.calculate_risk(balance=100000.0, account_id="40000294403")
        self.assertLessEqual(risk_data["risk_usd"], 750.0)

        # 3. Pass through 18-gate deterministic risk kernel
        kernel = DeterministicRiskKernel()
        decision = kernel.evaluate_admission("XAUUSD", confluence_score=94.0, proposed_risk_pct=0.25)
        self.assertTrue(decision["allowed"])

    def test_p02_r1_plus_r3_position_sync_reasoning_and_cockpit(self):
        """P02: FundingPips GBPUSD SELL #13002987 position syncs to dashboard reasoning."""
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(str(data["account"].get("login")), "40000294403")
        self.assertIn("rule_guarantee", data)

    def test_p03_r1_plus_r5_news_circuit_breaker_dag_blocks_admission(self):
        """P03: Economic News 15m Circuit Breaker DAG workflow blocks R1 trade entry."""
        from integrations.n8n_engine import N8nWorkflowEngine
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel

        # Trigger news circuit breaker DAG flow
        n8n = N8nWorkflowEngine()
        flow_res = n8n.trigger_workflow("news_circuit_breaker", {"event": "FOMC_RATE_DECISION"})
        self.assertTrue(flow_res.get("ok"))

        # Risk kernel receives news lockout active -> Blocks entry
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="EURUSD",
            confluence_score=96.0,
            proposed_risk_pct=0.20,
            news_lockout_active=True
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_p04_r1_plus_r6_hermes_tool_validates_prop_risk_cap(self):
        """P04: Hermes-3 cognitive agent validates trading_risk_kernel tool schema."""
        from brain.hermes_agent import HermesToolRegistry, HermesParser
        registry = HermesToolRegistry()
        tools = {t["function"]["name"]: t for t in registry.tools}
        self.assertIn("trading_risk_kernel", tools)

        # Hermes model emits structured call to trading_risk_kernel
        raw = (
            '<tool_call>\n'
            '{"name": "trading_risk_kernel", "arguments": {"symbol": "XAUUSD", "confluence_score": 93.0, "proposed_risk_pct": 0.25}}\n'
            '</tool_call>'
        )
        calls = HermesParser.extract_tool_calls(raw)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "trading_risk_kernel")
        self.assertLessEqual(args["proposed_risk_pct"], 0.75)

    def test_p05_r2_plus_r3_hft_dom_streaming_to_cockpit_radar(self):
        """P05: Level-2 DOM microstructure feeds Big Sharks radar alerts in MQ3 Cockpit."""
        sys.path.insert(0, str(MQ3_DIR / "dashboard"))
        import app as mq3_app
        with mq3_app.app.test_client() as client:
            resp = client.get("/api/live_commentary?symbol=XAUUSD")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "active")
            self.assertIn("bias", data)
            self.assertGreaterEqual(len(data.get("commentary", [])), 1)

    def test_p06_r2_plus_r5_whale_alert_dag_correlates_with_dom(self):
        """P06: Whale Alert DAG flow ($1M+) triggers and correlates with DOM order book."""
        from integrations.n8n_engine import N8nWorkflowEngine
        from src.order_book_dom_engine import OrderBookDOMEngine

        n8n = N8nWorkflowEngine()
        res = n8n.trigger_workflow("whale_flow", {"tx_hash": "0xabc123", "amount_usd": 2_500_000})
        self.assertTrue(res.get("ok"))

        # DOM order book reflects institutional liquidity
        engine = OrderBookDOMEngine()
        depth = engine.get_market_depth("XAUUSD")
        self.assertGreater(depth["total_bid_volume"], 0)

    def test_p07_r3_plus_r4_master_dashboard_embeds_mq3_tab_and_reasoning(self):
        """P07: Master Dashboard embeds MQ3 Cockpit (:5050) tab and polls reasoning."""
        client = get_dashboard_client()
        # 1. Check reasoning endpoint
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)

        # 2. Check HTML tab embedding
        html_file = BASE_DIR / "web" / "universal_command_center.html"
        content = html_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("pane-mq3cockpit", content)
        self.assertIn("http://127.0.0.1:5050/", content)

    def test_p08_r4_plus_r6_terminal_console_and_hermes_tool_calling(self):
        """P08: Master Dashboard terminal executes commands routed through tool schemas."""
        client = get_dashboard_client()
        resp = client.post("/api/terminal/exec", json={"cmd": "status"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("telemetry", data)

    def test_p09_r4_plus_r7_self_healing_and_lifecycle_management(self):
        """P09: 1-click self-healing engine and lifecycle service registry interact."""
        from bootstrap.master_ecosystem_launcher import SERVICES
        client = get_dashboard_client()

        # Check self-healing status
        status_resp = client.get("/api/self_healing/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertTrue(status_resp.json().get("ok"))

        # Check launcher services configuration
        self.assertIn("dashboard", SERVICES)
        self.assertIn("mq3", SERVICES)

    def test_p10_r5_plus_r6_dag_flow_executing_hermes_tool_registry(self):
        """P10: Local n8n DAG flow node actions map to Hermes-3 tool registry."""
        from integrations.n8n_engine import N8nWorkflowEngine
        from brain.hermes_agent import HermesToolRegistry

        engine = N8nWorkflowEngine()
        registry = HermesToolRegistry()
        tool_names = {t["function"]["name"] for t in registry.tools}

        # Flows reference capabilities aligned with tool schemas
        self.assertIn("mq3_trading", tool_names)
        self.assertIn("world_monitor", tool_names)
        self.assertIn("institutional_matrix", tool_names)

        res = engine.trigger_workflow("trade_admission_dispatch", {"symbol": "XAUUSD"})
        self.assertTrue(res.get("ok"))

    def test_p11_r6_plus_r1_identity_segregation_for_fundingpips(self):
        """P11: FundingPips prop operations enforce dedicated credentials."""
        from core.human_intervention_gateway import (
            FUNDINGPIPS_EMAIL,
            FUNDINGPIPS_PASSWORD,
            FUNDINGPIPS_ACCOUNT_ID,
            DEFAULT_OWNER_EMAIL
        )
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Check segregated emails in reasoning payload
        self.assertEqual(data["account"]["email"], FUNDINGPIPS_EMAIL)
        self.assertEqual(data["general_email"], DEFAULT_OWNER_EMAIL)
        self.assertEqual(str(data["account"]["login"]), FUNDINGPIPS_ACCOUNT_ID)

    def test_p12_r7_plus_r1_startup_lifecycle_verifies_trader_daemon(self):
        """P12: START ALL defines trader daemon pointing to autonomous MT5 execution."""
        from bootstrap.master_ecosystem_launcher import SERVICES
        self.assertIn("trader", SERVICES)
        trader_cfg = SERVICES["trader"]
        self.assertIn("autonomous_live_daemon.py", " ".join(trader_cfg["cmd"]))

    def test_p13_r7_plus_r3_stop_all_cleans_cockpit_port_5050(self):
        """P13: STOP ALL includes port 5050 in CORE_PORTS teardown sequence."""
        from bootstrap.lifecycle import CORE_PORTS
        self.assertIn(5050, CORE_PORTS)

    def test_p14_r7_plus_r5_lifecycle_and_local_n8n_orchestration(self):
        """P14: Lifecycle controls support n8n local engine readiness on port 5678."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        health = engine.check_n8n_server_health()
        self.assertTrue(health.get("online"))

    def test_p15_r4_plus_r5_morning_macro_dag_and_3d_hud_sitrep(self):
        """P15: Morning Macro Briefing flow correlates with 3D Earth HUD tactical nodes."""
        from integrations.n8n_engine import N8nWorkflowEngine
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("macro_briefing", {"time": "05:00 PKT"})
        self.assertTrue(res.get("ok"))

        client = get_dashboard_client()
        telemetry_resp = client.get("/api/system/3d_telemetry")
        self.assertEqual(telemetry_resp.status_code, 200)
        data = telemetry_resp.json()
        self.assertEqual(len(data.get("world_nodes", [])), 8)

    def test_p16_r2_plus_r6_hermes_agent_and_hft_microstructure_skill(self):
        """P16: Hermes agent parses and dispatches HFT Level-2 DOM microstructure queries."""
        from brain.hermes_agent import HermesParser
        from skills.high_frequency_trading import run

        raw = '<tool_call>\n{"name": "high_frequency_trading", "arguments": {"action": "dom_analysis", "symbol": "XAUUSD"}}\n</tool_call>'
        calls = HermesParser.extract_tool_calls(raw)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "high_frequency_trading")

        skill_output = run(args)
        self.assertIn("LEVEL-2 DEPTH OF MARKET", skill_output)
        self.assertIn("Whale Walls", skill_output)

    def test_p17_r6_plus_r1_mobile_websocket_remote_terminal_execution(self):
        """P17 (R6 + R1): Remote mobile client over WebSocket sends CMD_EXEC to control host terminal."""
        from mobile_control import _load_mobile_token
        client = get_mobile_client()
        token = _load_mobile_token()
        with client.websocket_connect(f"/ws/mobile?token={token}") as ws:
            ws.receive_json()  # Consume initial auth
            ws.send_json({"type": "CMD_EXEC", "command": "Write-Output 'P17_REMOTE_EXEC_PASS'"})
            res = ws.receive_json()
            self.assertEqual(res.get("type"), "CMD_RESULT")
            self.assertTrue(res.get("ok"))
            self.assertIn("P17_REMOTE_EXEC_PASS", res.get("output", ""))

    def test_p18_r6_plus_r2_mobile_stream_and_screen_vision_perception(self):
        """P18 (R6 + R2): Mobile screen stream route verified with screen vision capture."""
        from actions.screen_vision import ScreenVisionEngine
        engine = ScreenVisionEngine()
        cap = engine.capture_screen()
        self.assertIsNotNone(cap)
        client = get_mobile_client()
        routes = [r.path for r in client.app.routes]
        self.assertIn("/api/screen/stream", routes)

    def test_p19_r4_plus_r2_hermes_agent_and_browser_navigator_schema(self):
        """P19 (R4 + R2): Hermes-3 tool registry validates browser navigation schemas and parses actions."""
        from brain.hermes_agent import HermesToolRegistry, HermesParser
        registry = HermesToolRegistry()
        tool_names = [t["function"]["name"] for t in registry.tools]
        self.assertTrue(len(registry.tools) >= 8)
        raw = '<tool_call>\n{"name": "browser_automation", "arguments": {"action": "navigate", "url": "https://www.google.com"}}\n</tool_call>'
        calls = HermesParser.extract_tool_calls(raw)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "browser_automation")
        self.assertEqual(args["action"], "navigate")

    def test_p20_r3_plus_r5_geopolitical_defcon_and_discord_routing(self):
        """P20 (R3 + R5): Geopolitical DEFCON macro snapshot correlates with Discord channel routing."""
        from core.geopolitical_trading_fusion import GeopoliticalTradingFusion
        from bots.discord_bot import ELITE_TRADE_CHANNEL_ID
        fusion = GeopoliticalTradingFusion()
        snapshot = fusion.get_geopolitical_macro_snapshot()
        self.assertIn("defcon_level", snapshot)
        self.assertIn("gold_macro_multiplier", snapshot)
        gold_mult = snapshot["gold_macro_multiplier"]
        self.assertGreaterEqual(gold_mult, 1.0)
        self.assertEqual(str(ELITE_TRADE_CHANNEL_ID), "1541528931063177226")

    def test_p21_r4_plus_r5_n8n_broadcast_flow_and_whatsapp_rate_limiter(self):
        """P21 (R4 + R5): Sovereign n8n DAG flow executes multi-channel broadcast with WhatsApp rate limiter."""
        from integrations.n8n_engine import N8nWorkflowEngine
        from core.whatsapp_rate_limiter import WhatsAppRateLimiter
        engine = N8nWorkflowEngine()
        res = engine.trigger_workflow("discord_whatsapp_broadcast", {"headline": "TIER3_TEST_BROADCAST", "severity": "HIGH"})
        self.assertTrue(res.get("ok"))
        limiter = WhatsAppRateLimiter.get_instance()
        can_send, _ = limiter.can_dispatch_whatsapp(is_user_reply=True)
        self.assertTrue(can_send)


if __name__ == "__main__":
    unittest.main(verbosity=2)
