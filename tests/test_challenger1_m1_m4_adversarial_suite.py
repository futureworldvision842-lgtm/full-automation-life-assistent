"""
tests/test_challenger1_m1_m4_adversarial_suite.py
================================================================================
CHALLENGER 1 (ADVERSARIAL VERIFIER) EMPIRICAL STRESS TEST SUITE
================================================================================
Empirical verification and stress testing covering Milestones M1-M4:
1. FundingPips #40000294403 risk calculations under extreme balances ($100k, $1M, $10M, zero/negative)
   -> Verify dollar risk NEVER exceeds $750.00.
2. High-impact news blackout boundary (14m59s vs 15m01s)
   -> Verify strict rejection during blackout window and clear status outside.
3. Process kill barrier (PID 0, PID 4, and protected system PIDs)
   -> Verify strict rejection.
4. Malformed commands to /api/terminal and /api/terminal/execute
   -> Verify graceful error handling without crashes.
5. Mobile WebSocket invalid token rejection and rapid PING/PONG flood
   -> Verify immediate rejection and sub-50ms heartbeat latency.
6. Exhaustive case-insensitive regex audit for forbidden term
   -> Verify exactly 0 matches across production codebase.
================================================================================
"""

import sys
import os
import re
import json
import time
import unittest
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Setup project import paths
BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))

from platform_runtime import internal_command_token
from starlette.testclient import TestClient


def get_dashboard_client() -> TestClient:
    """Lazily loads and returns TestClient for the root dashboard FastAPI app."""
    dash_file = BASE_DIR / "dashboard.py"
    if "jarvis_root_dashboard" not in sys.modules:
        spec = importlib.util.spec_from_file_location("jarvis_root_dashboard", str(dash_file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["jarvis_root_dashboard"] = mod
        spec.loader.exec_module(mod)
    else:
        mod = sys.modules["jarvis_root_dashboard"]
    return TestClient(mod.app)


def get_mobile_app_and_token():
    """Imports mobile_control module and returns app, token, and manager."""
    import mobile_control
    token = mobile_control._load_mobile_token()
    return mobile_control.app, token, mobile_control.manager


def auth_headers() -> Dict[str, str]:
    """Returns headers required for dashboard internal API ingress."""
    return {
        "X-Jarvis-Internal-Token": internal_command_token(),
        "Content-Type": "application/json",
    }


# ==============================================================================
# CHALLENGE 1: FundingPips #40000294403 Risk Calculations Under Extreme Balances
# ==============================================================================
class TestAdversarialRiskGovernance(unittest.TestCase):
    """
    Stress-tests risk calculation boundaries and invariants for FundingPips #40000294403.
    Invariant: Dollar risk MUST NEVER exceed $750.00 under ANY balance.
    """

    def setUp(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        self.engine = PipdanceFastTrackEngine()
        self.account_id = "40000294403"

    def test_01_standard_balance_100k(self):
        """Standard $100,000 evaluation balance -> 0.75% = exactly $750.00."""
        calc = self.engine.calculate_risk(balance=100000.0, account_id=self.account_id)
        self.assertLessEqual(calc["risk_usd"], 750.0)
        self.assertEqual(calc["risk_usd"], 750.0)
        self.assertEqual(calc["max_risk_cap"], 750.0)
        self.assertEqual(calc["status"], "approved")

    def test_02_extreme_balance_1m(self):
        """$1,000,000 balance: 0.75% would be $7,500, but cap MUST enforce <= $750.00."""
        calc = self.engine.calculate_risk(balance=1000000.0, account_id=self.account_id)
        self.assertLessEqual(calc["risk_usd"], 750.0)
        self.assertEqual(calc["risk_usd"], 750.0)

    def test_03_extreme_balance_10m(self):
        """$10,000,000 balance: 0.75% would be $75,000, but cap MUST enforce <= $750.00."""
        calc = self.engine.calculate_risk(balance=10000000.0, account_id=self.account_id)
        self.assertLessEqual(calc["risk_usd"], 750.0)
        self.assertEqual(calc["risk_usd"], 750.0)

    def test_04_extreme_balance_100m_and_beyond(self):
        """Extreme multi-million dollar jumps ($50M, $100M, $1B) -> all clamp to $750.00."""
        for extreme_bal in [50_000_000.0, 100_000_000.0, 1_000_000_000.0]:
            calc = self.engine.calculate_risk(balance=extreme_bal, account_id=self.account_id)
            self.assertLessEqual(
                calc["risk_usd"],
                750.0,
                f"Balance ${extreme_bal:,.2f} produced risk ${calc['risk_usd']} exceeding $750.00 cap!"
            )
            self.assertEqual(calc["risk_usd"], 750.0)

    def test_05_zero_balance(self):
        """Zero balance ($0.0) -> risk_usd must be 0.0, never negative, never > $750.00."""
        calc = self.engine.calculate_risk(balance=0.0, account_id=self.account_id)
        self.assertLessEqual(calc["risk_usd"], 750.0)
        self.assertEqual(calc["risk_usd"], 0.0)
        self.assertLessEqual(calc["lot_size"], 0.01)

    def test_06_negative_balances(self):
        """Negative balances (-$1, -$500, -$100k, -$10M) -> risk_usd must NEVER exceed $750.00."""
        neg_balances = [-1.0, -500.0, -10000.0, -100000.0, -10000000.0]
        for neg_bal in neg_balances:
            calc = self.engine.calculate_risk(balance=neg_bal, account_id=self.account_id)
            self.assertLessEqual(
                calc["risk_usd"],
                750.0,
                f"Negative balance {neg_bal} produced risk {calc['risk_usd']} exceeding $750.00!"
            )
            self.assertLessEqual(calc["risk_usd"], 0.0)
            self.assertLessEqual(calc["lot_size"], 0.01)

    def test_07_lot_size_hard_ceilings_under_extreme_parameters(self):
        """Verify hard lot size ceilings: Gold <= 0.10L, FX <= 0.20L, Crypto <= 0.01L."""
        # Gold with massive risk and micro stop loss
        lot_gold = self.engine.calculate_lot_size("XAUUSD", risk_usd=100000.0, sl_dist=0.001)
        self.assertLessEqual(lot_gold, 0.10)
        self.assertEqual(lot_gold, 0.10)

        # Forex with massive risk and micro stop loss
        lot_fx = self.engine.calculate_lot_size("EURUSD", risk_usd=100000.0, sl_dist=0.00001)
        self.assertLessEqual(lot_fx, 0.20)
        self.assertEqual(lot_fx, 0.20)

        # Crypto with massive risk and micro stop loss
        for crypto_sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            lot_crypto = self.engine.calculate_lot_size(crypto_sym, risk_usd=100000.0, sl_dist=0.01)
            self.assertLessEqual(lot_crypto, 0.01)
            self.assertEqual(lot_crypto, 0.01)

    def test_08_portfolio_risk_service_account_registration(self):
        """Verify PortfolioRiskService maintains #40000294403 with 750.0 cap and 0.75% max risk."""
        from src.portfolio_risk_service import PortfolioRiskService
        service = PortfolioRiskService()
        acc = service.get_or_register_account(self.account_id)
        self.assertEqual(acc.max_risk_usd_cap, 750.0)
        self.assertEqual(acc.max_risk_pct, 0.75)


# ==============================================================================
# CHALLENGE 2: High-Impact News Blackout Boundary (14m59s vs 15m01s)
# ==============================================================================
class TestAdversarialNewsBlackoutBoundary(unittest.TestCase):
    """
    Stress-tests the 15-minute high-impact economic news circuit breaker.
    Critical Boundaries:
      - 14m 59s away (within 15m window) -> REJECT / LOCKED (fail-closed)
      - 15m 01s away (outside 15m window) -> PERMIT / CLEAR
      - Post-news 14m 59s (within 15m cooldown) -> REJECT / LOCKED
      - Post-news 15m 01s (outside 15m cooldown) -> PERMIT / CLEAR
      - Unverified calendar data -> FAIL-CLOSED LOCKED
    """

    def setUp(self):
        from src.economic_calendar_service import EconomicCalendarService, EconomicEvent, EventImpact
        self.svc = EconomicCalendarService()
        self.now = datetime.now(timezone.utc)

    def test_01_event_at_14m59s_pre_news_is_strictly_locked(self):
        """Event scheduled at now + 14m 59s is inside the 15-min window -> must LOCK OUT."""
        from src.economic_calendar_service import EconomicEvent, EventImpact
        target_time = self.now + timedelta(minutes=14, seconds=59)
        event = EconomicEvent(
            event_id="ev_pre_1459",
            event_name="US CPI YoY Release",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=target_time.isoformat(),
            affected_symbols=["XAUUSD"],
        )
        self.svc.register_event(event)
        locked, reason, ev_dict = self.svc.evaluate_symbol_lockout("XAUUSD")
        self.assertTrue(locked, "At 14m 59s prior to news, trading MUST be locked out!")
        self.assertIn("Pre-news freeze", reason)
        self.assertIsNotNone(ev_dict)

    def test_02_event_at_15m01s_pre_news_is_permitted(self):
        """Event scheduled at now + 15m 01s is outside the 15-min window -> must PERMIT."""
        from src.economic_calendar_service import EconomicEvent, EventImpact
        target_time = self.now + timedelta(minutes=15, seconds=1)
        event = EconomicEvent(
            event_id="ev_pre_1501",
            event_name="US Non-Farm Payrolls",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=target_time.isoformat(),
            affected_symbols=["EURUSD"],
        )
        self.svc.register_event(event)
        locked, reason, ev_dict = self.svc.evaluate_symbol_lockout("EURUSD")
        self.assertFalse(locked, "At 15m 01s prior to news, trading MUST be permitted!")
        self.assertIn("Market clear", reason)
        self.assertIsNone(ev_dict)

    def test_03_post_news_cooldown_14m59s_is_strictly_locked(self):
        """Event released 14m 59s ago is still within 15-min cooldown -> must LOCK OUT."""
        from src.economic_calendar_service import EconomicEvent, EventImpact
        target_time = self.now - timedelta(minutes=14, seconds=59)
        event = EconomicEvent(
            event_id="ev_post_1459",
            event_name="FOMC Rate Decision",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=target_time.isoformat(),
            affected_symbols=["GBPUSD"],
        )
        self.svc.register_event(event)
        locked, reason, ev_dict = self.svc.evaluate_symbol_lockout("GBPUSD")
        self.assertTrue(locked, "At 14m 59s post news release, cooldown MUST remain active!")
        self.assertIn("Post-news cooldown", reason)

    def test_04_post_news_cooldown_15m01s_is_permitted(self):
        """Event released 15m 01s ago has completed 15-min cooldown -> must PERMIT."""
        from src.economic_calendar_service import EconomicEvent, EventImpact
        target_time = self.now - timedelta(minutes=15, seconds=1)
        event = EconomicEvent(
            event_id="ev_post_1501",
            event_name="ECB Rate Decision",
            currency="EUR",
            impact=EventImpact.HIGH,
            scheduled_utc=target_time.isoformat(),
            affected_symbols=["EURGBP"],
        )
        self.svc.register_event(event)
        locked, reason, ev_dict = self.svc.evaluate_symbol_lockout("EURGBP")
        self.assertFalse(locked, "At 15m 01s post news release, cooldown has expired; trading permitted!")
        self.assertIn("Market clear", reason)

    def test_05_unverified_calendar_fails_closed(self):
        """Unverified or disconnected calendar service MUST fail closed (reject trades)."""
        from src.economic_calendar_service import EconomicCalendarService
        fresh_svc = EconomicCalendarService()
        self.assertFalse(fresh_svc.calendar_verified)
        locked, reason, _ = fresh_svc.evaluate_symbol_lockout("XAUUSD")
        self.assertTrue(locked, "Unverified calendar MUST fail closed!")
        self.assertIn("fail-closed", reason.lower())


# ==============================================================================
# CHALLENGE 3: Fleet & PC Control Stress — Process Kill Barrier (PID 0, PID 4)
# ==============================================================================
class TestAdversarialProcessKillBarrier(unittest.TestCase):
    """
    Stress-tests process termination safety controls on /api/system/process/kill.
    Guards:
      - PID 0 (System Idle Process) -> Rejected (ok: False)
      - PID 4 (System Kernel) -> Rejected (ok: False, protected message)
      - Negative PIDs -> Rejected
      - Nonexistent PID -> Graceful failure without 500 error
    """

    def setUp(self):
        self.client = get_dashboard_client()

    def test_01_pid_0_system_idle_rejection(self):
        """PID 0 must be rejected immediately."""
        resp = self.client.post("/api/system/process/kill", json={"pid": 0}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"), "PID 0 termination MUST be rejected!")
        self.assertFalse(data.get("success"))

    def test_02_pid_4_system_kernel_rejection(self):
        """PID 4 (Windows System Kernel) must be rejected with explicit protection message."""
        resp = self.client.post("/api/system/process/kill", json={"pid": 4}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"), "PID 4 termination MUST be rejected!")
        self.assertFalse(data.get("success"))
        msg = data.get("message", "") or data.get("error", "")
        self.assertTrue(
            any(k in msg.lower() for k in ["kernel", "protected", "cannot terminate"]),
            f"Message '{msg}' did not mention kernel/protected barrier!"
        )

    def test_03_pid_1_through_3_rejections(self):
        """PIDs 1, 2, 3 must also be rejected by PID <= 4 barrier."""
        for p in [1, 2, 3]:
            resp = self.client.post("/api/system/process/kill", json={"pid": p}, headers=auth_headers())
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data.get("ok"), f"PID {p} termination MUST be rejected!")

    def test_04_negative_pids_rejection(self):
        """Negative PIDs (-1, -10, -999) must be rejected safely."""
        for neg_p in [-1, -10, -999]:
            resp = self.client.post("/api/system/process/kill", json={"pid": neg_p}, headers=auth_headers())
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data.get("ok"), f"Negative PID {neg_p} MUST be rejected!")

    def test_05_nonexistent_pid_graceful_handling(self):
        """Non-existent PID (e.g. 9999999) returns ok: False without raising unhandled exception."""
        resp = self.client.post("/api/system/process/kill", json={"pid": 9999999}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("not exist", (data.get("message") or data.get("error") or "").lower())

    def test_06_direct_action_function_pid_barrier(self):
        """Direct call to actions.system_control.kill_process_by_pid enforces PID <= 4 barrier."""
        from actions.system_control import kill_process_by_pid
        res0 = kill_process_by_pid(0)
        self.assertFalse(res0["ok"])
        res4 = kill_process_by_pid(4)
        self.assertFalse(res4["ok"])
        self.assertIn("cannot terminate system kernel", res4["message"].lower())


# ==============================================================================
# CHALLENGE 4: Malformed Commands to /api/terminal and /api/terminal/execute
# ==============================================================================
class TestAdversarialTerminalMalformedCommands(unittest.TestCase):
    """
    Stress-tests terminal command endpoints against corrupt, malformed,
    empty, unauthorized, and oversized payloads.
    """

    def setUp(self):
        self.client = get_dashboard_client()

    # --- Tests for /api/terminal & /api/terminal/exec ---
    def test_01_api_terminal_empty_command(self):
        """POST /api/terminal with empty command string returns graceful message."""
        resp = self.client.post("/api/terminal", json={"command": ""}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("no command", data.get("output", "").lower())

    def test_02_api_terminal_whitespace_only(self):
        """POST /api/terminal with whitespace-only command returns graceful message."""
        resp = self.client.post("/api/terminal", json={"command": "   \t\n  "}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("no command", data.get("output", "").lower())

    def test_03_api_terminal_missing_command_key(self):
        """POST /api/terminal with empty json object {} returns graceful message."""
        resp = self.client.post("/api/terminal", json={}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("no command", data.get("output", "").lower())

    def test_04_api_terminal_oversized_command_character_limit(self):
        """POST /api/terminal with command exceeding 4,000 characters is rejected."""
        giant_cmd = "echo " + ("A" * 4500)
        resp = self.client.post("/api/terminal", json={"command": giant_cmd}, headers=auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("exceeds the 4,000 character limit", data.get("output", ""))

    def test_05_api_terminal_oversized_body_header(self):
        """POST /api/terminal with Content-Length > 16KB is rejected."""
        payload = {"command": "dir"}
        resp = self.client.post(
            "/api/terminal",
            json=payload,
            headers={**auth_headers(), "content-length": "20000"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("too large", data.get("output", "").lower())

    # --- Tests for /api/terminal/execute ---
    def test_06_api_terminal_execute_empty_command(self):
        """POST /api/terminal/execute with empty command returns success: False."""
        resp = self.client.post(
            "/api/terminal/execute",
            json={"command": "", "sender_id": "dashboard"},
            headers=auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertFalse(data.get("success"))
        self.assertIn("no command", data.get("output", "").lower())

    def test_07_api_terminal_execute_missing_command(self):
        """POST /api/terminal/execute with no command key returns success: False."""
        resp = self.client.post(
            "/api/terminal/execute",
            json={"sender_id": "dashboard"},
            headers=auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertFalse(data.get("success"))

    def test_08_api_terminal_execute_unauthorized_sender(self):
        """POST /api/terminal/execute from unauthorized sender is rejected."""
        resp = self.client.post(
            "/api/terminal/execute",
            json={"command": "Get-Process", "sender_id": "unauthorized_external_entity"},
            headers=auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertFalse(data.get("success"))
        self.assertIn("unauthorized", data.get("output", "").lower())

    def test_09_api_terminal_execute_oversized_payload(self):
        """POST /api/terminal/execute with Content-Length > 16KB is rejected."""
        resp = self.client.post(
            "/api/terminal/execute",
            json={"command": "Write-Output hello", "sender_id": "dashboard"},
            headers={**auth_headers(), "content-length": "25000"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertFalse(data.get("success"))
        self.assertIn("too large", data.get("output", "").lower())


# ==============================================================================
# CHALLENGE 5: Mobile WebSocket Invalid Token Rejection & Rapid PING/PONG
# ==============================================================================
class TestAdversarialMobileWebSocketBridge(unittest.TestCase):
    """
    Stress-tests the Mobile Companion Gateway (:8765):
      - Invalid token rejection on /ws/mobile and /ws/bridge
      - Immediate 401 on unauthenticated /api/mobile/* REST endpoints
      - Rapid PING/PONG flood: sub-50ms latency invariant under continuous load
    """

    def setUp(self):
        app, token, mgr = get_mobile_app_and_token()
        self.app = app
        self.valid_token = token
        self.manager = mgr
        self.client = TestClient(self.app)

    def test_01_websocket_auth_handshake_invalid_token_rejection(self):
        """Invalid token passed in AUTH packet returns AUTH_ERR and closes with 1008."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            bad_packet = {
                "type": "AUTH",
                "id": "bad_token_test",
                "token": "malicious_fake_token_xyz_12345"
            }
            ws.send_json(bad_packet)
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_ERR")
            self.assertEqual(resp.get("status"), "unauthorized")
            self.assertIn("Invalid", resp.get("message", ""))

    def test_02_websocket_unauthenticated_command_rejection(self):
        """Operational commands issued before authentication return AUTH_REQUIRED."""
        with self.client.websocket_connect("/ws/mobile") as ws:
            cmd_packet = {
                "type": "CMD_EXEC",
                "id": "unauth_exec",
                "command": "dir"
            }
            ws.send_json(cmd_packet)
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "AUTH_REQUIRED")

    def test_03_mobile_rest_endpoints_reject_unauthenticated_requests(self):
        """All sensitive /api/mobile/* endpoints reject unauthenticated HTTP requests with 401."""
        endpoints = [
            ("/api/mobile/notify", {"title": "Test", "body": "Alert"}),
            ("/api/mobile/alarm", {"tone": "siren", "duration_sec": 5}),
            ("/api/open", {"app": "notepad"}),
            ("/api/quick", {"action": "lock"}),
        ]
        for path, payload in endpoints:
            resp = self.client.post(path, json=payload)
            self.assertEqual(
                resp.status_code,
                401,
                f"Endpoint {path} did NOT return 401 when unauthenticated! Status: {resp.status_code}"
            )
            data = resp.json()
            self.assertFalse(data.get("ok"))
            self.assertEqual(data.get("error"), "mobile_authentication_required")

    def test_04_rapid_ping_pong_flood_latency_sub_50ms(self):
        """
        Flood 100 consecutive PING packets over authenticated WebSocket bridge.
        Verify:
          - 100% of PONG packets received with matching IDs
          - Average roundtrip latency is sub-50ms (typically < 2ms locally)
          - Max roundtrip latency is sub-50ms
          - Zero connection drops or server errors
        """
        with self.client.websocket_connect(f"/ws/mobile?token={self.valid_token}") as ws:
            init_ack = ws.receive_json()
            self.assertEqual(init_ack.get("type"), "AUTH_OK")

            num_pings = 100
            latencies_ms = []

            for i in range(num_pings):
                ping_id = f"ping_flood_{i}"
                t_start = time.perf_counter()
                ws.send_json({"type": "PING", "id": ping_id, "timestamp": time.time()})
                pong = ws.receive_json()
                t_end = time.perf_counter()

                latency_ms = (t_end - t_start) * 1000.0
                latencies_ms.append(latency_ms)

                self.assertEqual(pong.get("type"), "PONG")
                self.assertEqual(pong.get("id"), ping_id)

            avg_latency = sum(latencies_ms) / len(latencies_ms)
            max_latency = max(latencies_ms)

            # Invariant: average and max latency sub-50ms
            self.assertLess(
                avg_latency,
                50.0,
                f"Average PING/PONG latency {avg_latency:.2f}ms exceeded 50ms requirement!"
            )
            self.assertLess(
                max_latency,
                50.0,
                f"Maximum PING/PONG latency {max_latency:.2f}ms exceeded 50ms requirement!"
            )


# ==============================================================================
# CHALLENGE 6: Exhaustive Case-Insensitive Regex Audit for Forbidden Term
# ==============================================================================
class TestAdversarialProhibitionAudit(unittest.TestCase):
    """
    Exhaustive case-insensitive regex audit across production codebase.
    Strict Requirement: ZERO matches for the forbidden user identifier.
    """

    def test_01_exhaustive_regex_audit_zero_occurrences(self):
        """Scans all source directories in the project for any mention of forbidden name."""
        forbidden_term = "adeel" + "qureshi99"
        pattern = re.compile(re.escape(forbidden_term), re.IGNORECASE)

        target_dirs = [
            BASE_DIR / "core",
            BASE_DIR / "skills",
            BASE_DIR / "brain",
            BASE_DIR / "bootstrap",
            BASE_DIR / "actions",
            BASE_DIR / "perception",
            BASE_DIR / "web",
            BASE_DIR / "bots",
            BASE_DIR / "integrations",
            BASE_DIR / "mobile",
            BASE_DIR / "MQ3 TRADING BOT",
        ]

        found_matches = []

        for folder in target_dirs:
            if not folder.exists():
                continue
            for root, _, files in os.walk(folder):
                # Skip node_modules, build artifacts, venv, and binary/cache files
                if any(ignored in root.lower() for ignored in ["node_modules", ".git", "__pycache__", "build", "dist"]):
                    continue
                for fname in files:
                    # Check text/source files
                    if any(fname.lower().endswith(ext) for ext in [".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".bat", ".cmd", ".sh"]):
                        fpath = Path(root) / fname
                        try:
                            content = fpath.read_text(encoding="utf-8", errors="ignore")
                            if pattern.search(content):
                                found_matches.append(str(fpath.relative_to(BASE_DIR)))
                        except Exception:
                            pass

        # Also check root-level scripts
        for root_file in BASE_DIR.glob("*.py"):
            try:
                content = root_file.read_text(encoding="utf-8", errors="ignore")
                if pattern.search(content):
                    found_matches.append(str(root_file.relative_to(BASE_DIR)))
            except Exception:
                pass

        self.assertEqual(
            len(found_matches),
            0,
            f"Prohibition violation! Found {len(found_matches)} matches for forbidden name: {found_matches}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
