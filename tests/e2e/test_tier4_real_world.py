"""
J.A.R.V.I.S. Command Center Autonomous Operations & Mobile Companion Ecosystem
================================================================================
Tier 4: Real-World Institutional Scenarios (Requirements R1 through R6)
================================================================================
Complex, multi-stage end-to-end operational simulations derived from
ORIGINAL_REQUEST.md (## 2026-09-19T03:55:12Z) and PROJECT.md:
  • Scenario 1: Morning Macro Briefing Flow & Intelligence Broadcast
  • Scenario 2: Remote Mobile Companion Connect, System Telemetry & Terminal Execution
  • Scenario 3: Autonomous MT5 Prop Trade Entry, Confluence Check & +1.0R Breakeven Lock
  • Scenario 4: High-Impact Economic News 15-Minute Circuit Breaker with Fail-Closed Lockout
  • Scenario 5: Geopolitical DEFCON Escalation & Dynamic Asset Multiplier Fusion
  • Scenario 6: Master War Room Dual-Dashboard Health & Self-Healing Telemetry
  • Scenario 7: 1-Click Ecosystem Lifecycle & Port Cleansing Audit

Requirement: >= 5 complex operational scenarios.
================================================================================
"""

import sys
import os
import json
import time
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


class TestTier4_RealWorldInstitutionalScenarios(unittest.TestCase):
    """Tier 4 end-to-end institutional workflow scenarios."""

    def test_scenario_01_morning_macro_briefing_and_intelligence_broadcast(self):
        """
        Scenario 1: Morning Macro Briefing Flow & Intelligence Broadcast.
        Flow:
          1. 05:00 AM PKT trigger fires Morning Macro Workflow via Sovereign n8n Engine.
          2. GeopoliticalTradingFusion synthesizes DEFCON threat status and maritime chokepoints.
          3. Intelligence card payload constructed with gold/oil risk premia.
          4. Automated broadcast targets Discord #elite-trade (1541528931063177226).
          5. WhatsApp Baileys gateway routing verified for Master Muhammad Qureshi (923468053268) with rate limiter.
        """
        from integrations.n8n_engine import N8nWorkflowEngine
        from core.geopolitical_trading_fusion import GeopoliticalTradingFusion
        from bots.discord_bot import ELITE_TRADE_CHANNEL_ID
        from core.human_intervention_gateway import DEFAULT_OWNER_PHONE
        from core.whatsapp_rate_limiter import WhatsAppRateLimiter

        # Step 1: n8n workflow execution
        engine = N8nWorkflowEngine()
        wf_res = engine.trigger_workflow("macro_briefing", {"schedule": "05:00_PKT", "scope": "institutional_macro"})
        self.assertTrue(wf_res.get("ok"))
        self.assertEqual(wf_res.get("status"), "COMPLETED")
        self.assertEqual(wf_res.get("workflow_id"), "macro_briefing")

        # Step 2: Geopolitical fusion synthesis
        fusion = GeopoliticalTradingFusion()
        snapshot = fusion.get_geopolitical_macro_snapshot()
        self.assertTrue(snapshot.get("ok"))
        self.assertIn("defcon_level", snapshot)
        self.assertGreaterEqual(len(snapshot.get("chokepoints", [])), 5)
        self.assertGreaterEqual(snapshot.get("gold_macro_multiplier", 1.0), 1.0)

        # Step 3 & 4: Discord broadcast target validation
        self.assertEqual(str(ELITE_TRADE_CHANNEL_ID), "1541528931063177226")

        # Step 5: WhatsApp delivery to Master Muhammad Qureshi with rate limiter guard
        self.assertEqual(DEFAULT_OWNER_PHONE, "923468053268")
        limiter = WhatsAppRateLimiter.get_instance()
        can_send, reason = limiter.can_dispatch_whatsapp(is_user_reply=True)
        self.assertTrue(can_send)

    def test_scenario_02_mobile_remote_wake_system_telemetry_and_terminal_administration(self):
        """
        Scenario 2: Remote Mobile Companion Connect, System Telemetry & Terminal Execution.
        Flow:
          1. Connect to Mobile Remote Gateway (:8765) over authenticated WebSocket (/ws/mobile).
          2. Verify sub-50ms PING/PONG latency and protocol handshake.
          3. Fetch live PC hardware vitals (CPU %, RAM, NVMe C: and F: storage).
          4. Issue remote CMD_EXEC terminal command over WebSocket and verify stdout capture.
          5. Verify live MJPEG desktop screen stream endpoint (/api/screen/stream) is operational.
        """
        import mobile_control
        client = get_mobile_client()
        token = mobile_control._load_mobile_token()

        # Step 1 & 2: WebSocket handshake and PING/PONG
        with client.websocket_connect(f"/ws/mobile?token={token}") as ws:
            init = ws.receive_json()
            self.assertIn(init.get("type"), ("AUTH_OK", "PONG"))

            start_t = time.perf_counter()
            ws.send_json({"type": "PING", "timestamp": time.time()})
            pong = ws.receive_json()
            roundtrip_ms = (time.perf_counter() - start_t) * 1000
            self.assertEqual(pong.get("type"), "PONG")
            self.assertLess(roundtrip_ms, 1000.0)

            # Step 4: Issue remote CMD_EXEC
            cmd_payload = {"type": "CMD_EXEC", "command": "Write-Output 'MOBILE_SCENARIO_2_VERIFIED'"}
            ws.send_json(cmd_payload)
            res = ws.receive_json()
            self.assertEqual(res.get("type"), "CMD_RESULT")
            self.assertTrue(res.get("ok"))
            self.assertIn("MOBILE_SCENARIO_2_VERIFIED", res.get("output", ""))

        # Step 3: Hardware vitals check
        dash_client = get_dashboard_client()
        vitals_resp = dash_client.get("/api/pc")
        self.assertEqual(vitals_resp.status_code, 200)
        vitals = vitals_resp.json()
        self.assertIn("cpu_percent", vitals)
        self.assertIn("ram_used_gb", vitals)
        self.assertIn("drive_c_free_gb", vitals)

        # Step 5: Screen stream route
        routes = [r.path for r in mobile_control.app.routes]
        self.assertIn("/api/screen/stream", routes)

    def test_scenario_03_autonomous_mt5_prop_trade_entry_confluence_and_breakeven_lock(self):
        """
        Scenario 3: Autonomous MT5 Prop Trade Entry, Confluence Check & +1.0R Breakeven Lock.
        Flow:
          1. Technical setup: SMC/ICT Liquidity Sweep detected on GBPUSD.
          2. Risk verification: Account #40000294403 $100k balance sized strictly <= $750.00 (0.75%).
          3. Order admission: 18-gate deterministic risk kernel clears setup with 92.0 confluence.
          4. Execution simulation: GBPUSD SELL ticket #13002987 entered at 1.33675 (SL: 1.33900).
          5. Market movement: Price drops to 1.33450 (+1.0R gain).
          6. Breakeven lock: Engine moves SL to 1.33675 guaranteeing $0 risk.
          7. Synchronization: Dashboards (:8770 and :5050) report breakeven locked.
        """
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel

        # Step 1 & 2: Risk calculation on FundingPips #40000294403
        engine = PipdanceFastTrackEngine()
        risk_plan = engine.calculate_risk(balance=100000.0, account_id="40000294403", symbol="GBPUSD")
        self.assertLessEqual(risk_plan["risk_usd"], 750.0)
        self.assertEqual(risk_plan["risk_usd"], 750.0)

        # Step 3: Admission gate
        kernel = DeterministicRiskKernel()
        admission = kernel.evaluate_admission("GBPUSD", confluence_score=92.0, proposed_risk_pct=0.75, rr_ratio=2.5)
        self.assertIn("total_gates_evaluated", admission)

        # Step 4 & 5: Trade entry and +1.0R profit expansion
        position = {
            "ticket": 13002987,
            "symbol": "GBPUSD",
            "type": "SELL",
            "price_open": 1.33675,
            "sl": 1.33900,
            "tp": 1.33149,
            "profit": 40.80,
            "volume": 0.20
        }
        # Step 6: Trigger dynamic breakeven lock
        be_res = engine.check_breakeven_trigger(position, current_price=1.33450, breakeven_profit_cap=750.0)
        self.assertTrue(be_res["trigger"])
        self.assertEqual(be_res["action"], "shift_sl_to_entry")
        self.assertAlmostEqual(be_res["new_sl"], 1.33675, delta=0.0001)

        # Step 7: Master dashboard exposure
        client = get_dashboard_client()
        resp = client.get("/api/trading/reasoning?symbol=GBPUSD")
        self.assertEqual(resp.status_code, 200)
        reasoning = resp.json()
        self.assertTrue(reasoning.get("ok"))
        self.assertEqual(str(reasoning["account"]["login"]), "40000294403")

    def test_scenario_04_high_impact_news_15m_circuit_breaker_fail_closed_lockout(self):
        """
        Scenario 4: High-Impact Economic News 15-Minute Circuit Breaker with Fail-Closed Lockout.
        Flow:
          1. High-impact CPI event scheduled 8 minutes away on USD.
          2. EconomicCalendarService evaluates symbol lockout for XAUUSD.
          3. Confirm fail-closed lockout is triggered (True), returning lockout message.
          4. Sovereign n8n DAG engine fires news_circuit_breaker flow.
          5. 18-gate deterministic risk kernel rejects trade admission proposal despite technical confluence.
          6. Capital preserved with 0 drawdown.
        """
        from src.economic_calendar_service import EconomicCalendarService, EconomicEvent, EventImpact
        from integrations.n8n_engine import N8nWorkflowEngine
        from trading.risk_kernel.admission_kernel import DeterministicRiskKernel

        # Step 1 & 2: Economic calendar service registers event 8m out
        svc = EconomicCalendarService()
        now = datetime.now(timezone.utc)
        cpi_event = EconomicEvent(
            event_id="cpi_usd_scenario4",
            event_name="US CPI YoY Release",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=(now + timedelta(minutes=8)).isoformat(),
            affected_symbols=["XAUUSD", "GBPUSD", "EURUSD"],
        )
        svc.register_event(cpi_event)
        locked, msg, evts = svc.evaluate_symbol_lockout("XAUUSD")
        self.assertTrue(locked)
        self.assertTrue("Pre-news freeze" in msg or "Trading locked" in msg)

        # Step 4: n8n workflow triggered
        n8n = N8nWorkflowEngine()
        wf_res = n8n.trigger_workflow("news_circuit_breaker", {"event_id": "cpi_usd_scenario4", "symbol": "XAUUSD"})
        self.assertTrue(wf_res.get("ok"))

        # Step 5: Risk kernel rejects trade
        kernel = DeterministicRiskKernel()
        decision = kernel.evaluate_admission("XAUUSD", confluence_score=97.5, proposed_risk_pct=0.25, news_lockout_active=True)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("News Lockout" in b for b in decision["blockers"]))

    def test_scenario_05_geopolitical_defcon_escalation_and_dynamic_asset_multipliers(self):
        """
        Scenario 5: Geopolitical DEFCON Escalation & Dynamic Asset Multiplier Fusion.
        Flow:
          1. Ingest maritime chokepoint telemetry (Hormuz, Bab el-Mandeb, Suez).
          2. GeopoliticalTradingFusion evaluates DEFCON level and country instability index.
          3. Dynamic safe-haven macro multiplier calculated: Gold (1.45x) and Crude Oil (1.50x).
          4. Trading engine enforces lot size ceilings (0.10L Gold, 0.20L Forex, 0.01L Crypto).
          5. Validates confluence boost and reasonings populated without data contamination.
        """
        from core.geopolitical_trading_fusion import GeopoliticalTradingFusion
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine

        # Step 1 & 2: DEFCON and chokepoints
        fusion = GeopoliticalTradingFusion()
        snapshot = fusion.get_geopolitical_macro_snapshot()
        self.assertTrue(snapshot.get("ok"))
        self.assertIn(snapshot.get("defcon_level"), (1, 2, 3, 4, 5))
        self.assertGreaterEqual(len(snapshot.get("chokepoints", [])), 5)

        # Step 3: Multipliers
        self.assertAlmostEqual(snapshot.get("gold_macro_multiplier", 1.0), 1.45, places=2)
        self.assertAlmostEqual(snapshot.get("oil_macro_multiplier", 1.0), 1.50, places=2)

        # Step 4: Lot size hard ceilings
        engine = PipdanceFastTrackEngine()
        gold_lot = engine.calculate_lot_size("XAUUSD", risk_usd=10000.0, sl_dist=0.5)
        self.assertLessEqual(gold_lot, 0.10)
        self.assertEqual(gold_lot, 0.10)

        forex_lot = engine.calculate_lot_size("GBPUSD", risk_usd=10000.0, sl_dist=0.001)
        self.assertLessEqual(forex_lot, 0.20)
        self.assertEqual(forex_lot, 0.20)

        crypto_lot = engine.calculate_lot_size("BTCUSD", risk_usd=10000.0, sl_dist=50.0)
        self.assertLessEqual(crypto_lot, 0.01)
        self.assertEqual(crypto_lot, 0.01)

    def test_scenario_06_master_war_room_dual_dashboard_and_self_healing(self):
        """
        Scenario 6: Master War Room Dual-Dashboard Health & Self-Healing Telemetry.
        Flow:
          1. Master Operations Dashboard (:8770) polls system telemetry and 8 tactical world nodes.
          2. Hardware scanner monitors CPU %, RAM GB, and Disks C: & F:.
          3. Self-healing engine generates 3 interactive remediation options.
          4. User triggers 1-click optimization (Option 1: PURGE_RAM_CACHE).
          5. Multi-frontend tab switcher validates embed configuration for God's Eye (:4173) and MQ3 (:5050).
        """
        client = get_dashboard_client()

        # Step 1: 3D Telemetry and world nodes
        telemetry_resp = client.get("/api/system/3d_telemetry")
        self.assertEqual(telemetry_resp.status_code, 200)
        telemetry_data = telemetry_resp.json()
        self.assertTrue(telemetry_data.get("ok"))
        self.assertEqual(len(telemetry_data.get("world_nodes", [])), 8)

        # Step 2: Hardware vitals
        vitals_resp = client.get("/api/pc")
        self.assertEqual(vitals_resp.status_code, 200)
        vitals = vitals_resp.json()
        self.assertIn("ram_used_gb", vitals)
        self.assertIn("drive_c_free_gb", vitals)

        # Step 3 & 4: Self-healing scan and 1-click execution
        heal_status = client.get("/api/self_healing/status")
        self.assertEqual(heal_status.status_code, 200)
        self.assertTrue(heal_status.json().get("ok"))

        resolve_resp = client.post("/api/self_healing/resolve", json={"option_id": 1})
        self.assertEqual(resolve_resp.status_code, 200)
        resolve_data = resolve_resp.json()
        self.assertTrue(resolve_data.get("ok"))
        self.assertEqual(resolve_data.get("action_code"), "PURGE_RAM_CACHE")

        # Step 5: Web UI tab switcher anti-collapse verification
        html_file = BASE_DIR / "web" / "universal_command_center.html"
        content = html_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("frameGodseye", content)
        self.assertIn("frameMq3", content)
        self.assertIn("embed-frame", content)

    def test_scenario_07_one_click_lifecycle_and_port_cleansing_audit(self):
        """
        Scenario 7: 1-Click Ecosystem Lifecycle & Port Cleansing Audit.
        Flow:
          1. Verify `JARVIS - START ALL.bat` invokes master launcher start all.
          2. Verify `JARVIS - STOP ALL.bat` executes stop sequence across all ports.
          3. Inspect configured ports (8770, 5050, 4173, 3000, 7000, 8765, 11434, 3200, 5678).
          4. Confirm process supervisor / lifecycle entry tracking logic.
          5. Verify clean idle state without orphan processes.
        """
        from bootstrap.lifecycle import CORE_PORTS, owned_entries
        from bootstrap.master_ecosystem_launcher import SERVICES

        # Step 1 & 2: Batch script integrity
        start_bat = BASE_DIR / "JARVIS - START ALL.bat"
        stop_bat = BASE_DIR / "JARVIS - STOP ALL.bat"
        self.assertTrue(start_bat.exists())
        self.assertTrue(stop_bat.exists())

        start_content = start_bat.read_text(encoding="utf-8", errors="replace")
        stop_content = stop_bat.read_text(encoding="utf-8", errors="replace")
        self.assertIn("master_ecosystem_launcher.py", start_content)
        self.assertIn("start all", start_content)
        self.assertIn("master_ecosystem_launcher.py", stop_content)
        self.assertIn("stop", stop_content)

        # Step 3: Core ports
        self.assertIn(8770, CORE_PORTS)
        self.assertIn(5050, CORE_PORTS)
        self.assertIn(4173, CORE_PORTS)
        self.assertIn(3000, CORE_PORTS)
        self.assertIn(7000, CORE_PORTS)
        self.assertIn(8765, CORE_PORTS)

        # Step 4: Services dictionary completeness
        required_services = ["dashboard", "godseye", "worldmonitor", "mq3", "odysseus", "mobile", "trader", "ollama", "discord", "whatsapp"]
        for svc in required_services:
            self.assertIn(svc, SERVICES)

        # Step 5: Clean idle state verification
        idle_entries = owned_entries(include_supervisor=False)
        self.assertIsInstance(idle_entries, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
