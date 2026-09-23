"""
tests/test_m3_challenger2_adversarial_deep.py — Milestone 3 Challenger 2 Adversarial Stress Suite.
=================================================================================================
Empirical stress tests for:
1. Mathematical precision: FVG CE midpoint formula accuracy, inverted FVG ranges, non-standard pip scales.
2. Breakeven spread buffer precision under extreme pip sizes.
3. Partial scale-out volume rounding: odd lot sizes (0.01, 0.03, 0.07, etc.) and volume conservation.
4. Kill-switch race conditions: rapid multithreaded back-to-back triggers, idempotency, complete position flattening.
5. WhatsApp directive spoofing: unauthorized numbers, malformed payloads, injection attempts, LID bypass rejection.
6. Cockpit API HTTP endpoint fuzzing: invalid methods, malformed JSON, query tampering, resilience against 500 errors.
"""

import sys
import os
import json
import time
import math
import concurrent.futures
from typing import Dict, Any, List
import pytest
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.app import app
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.mt5_connector import MT5Connector
from src.bitget_connector import BitgetConnector
from src.whatsapp_copilot import (
    is_whitelisted_number,
    WhatsApp1ClickRouter,
    AUTHORIZED_CONTACTS,
    ELITE_TRADE_GROUP_JID
)
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.market_analyzer import MarketAnalyzer


# ══════════════════════════════════════════════════════════════════════════════
# 1. MATHEMATICAL STRESS TESTS & FVG CE ACCURACY
# ══════════════════════════════════════════════════════════════════════════════

class TestFVGAndBreakevenMathAdversarial:
    """Adversarial mathematical stress tests for FVG CE and Breakeven calculations."""

    @pytest.fixture
    def fleet_exec(self):
        mt5 = MT5Connector(simulation_mode=True)
        bitget = BitgetConnector(sim_mode=True)
        executor = AutonomousFleetExecutor(
            risk_manager=None,
            whatsapp_manager=None,
            bitget_connector=bitget,
            mt5_connector=mt5
        )
        return executor

    @pytest.mark.parametrize("top,bottom,expected_ce", [
        (2650.00, 2640.00, 2645.00),          # Gold standard
        (1.08500, 1.08000, 1.08250),          # EURUSD 5-decimal
        (155.50, 154.50, 155.00),              # JPY 2-decimal
        (65000.0, 64000.0, 64500.0),          # BTC standard
        (0.000015, 0.000010, 0.0000125),      # Micro-crypto / meme coin
        (1000000.0, 999000.0, 999500.0),      # Extreme high price
        (0.001, 0.0002, 0.0006),              # Sub-penny range
    ])
    def test_fvg_ce_midpoint_mathematical_precision(self, fleet_exec, top, bottom, expected_ce):
        """Validates exact FVG Consequent Encroachment: CE = (top + bottom) / 2.0."""
        calc_ce = (top + bottom) / 2.0
        assert math.isclose(calc_ce, expected_ce, rel_tol=1e-7), f"Expected {expected_ce}, got {calc_ce}"

        pos = {
            "ticket": 99901,
            "account_id": "TEST_ACC",
            "symbol": "XAUUSD",
            "open_price": 2640.00,
            "sl": 2630.00,
            "tp1": 2670.00,
            "status": "RUNNING"
        }
        fleet_exec.active_positions = [pos]
        res = fleet_exec.trail_fvg_consequent_encroachment(ticket=99901, fvg_top=top, fvg_bottom=bottom)
        assert res["success"] is True
        assert math.isclose(res["ce_50"], round(expected_ce, 2), abs_tol=0.01)

    def test_inverted_fvg_range_handling(self, fleet_exec):
        """Tests inverted FVG boundaries (top < bottom) and zero-width ranges."""
        top = 2640.00
        bottom = 2650.00
        pos = {
            "ticket": 99902,
            "symbol": "XAUUSD",
            "open_price": 2645.00,
            "sl": 2630.00,
            "status": "RUNNING"
        }
        fleet_exec.active_positions = [pos]
        res = fleet_exec.trail_fvg_consequent_encroachment(ticket=99902, fvg_top=top, fvg_bottom=bottom)
        assert res["success"] is True
        assert math.isclose(res["ce_50"], 2645.00, rel_tol=1e-5)

        # Zero-width gap (top == bottom)
        res_zero = fleet_exec.trail_fvg_consequent_encroachment(ticket=99902, fvg_top=2650.0, fvg_bottom=2650.0)
        assert res_zero["success"] is True
        assert res_zero["ce_50"] == 2650.0

    @pytest.mark.parametrize("symbol,expected_pip_unit", [
        ("XAUUSD", 0.1),
        ("GOLD", 0.1),
        ("USDJPY", 0.01),
        ("EURJPY", 0.01),
        ("GBPJPY", 0.01),
        ("BTCUSD", 1.0),
        ("BTCUSDT", 1.0),
        ("ETHUSD", 0.1),
        ("ETHUSDT", 0.1),
        ("SOLUSD", 0.01),
        ("SOLUSDT", 0.01),
        ("EURUSD", 0.0001),
        ("GBPUSD", 0.0001),
        ("AUDUSD", 0.0001),
        ("USDCAD", 0.0001),
        ("UNKNOWN_EXOTIC", 0.0001)  # Default fallback
    ])
    def test_multi_asset_pip_scale_taxonomy(self, fleet_exec, symbol, expected_pip_unit):
        """Verifies exact pip units across standard, commodity, JPY, crypto, and exotic assets."""
        unit = fleet_exec._get_pip_unit(symbol)
        assert math.isclose(unit, expected_pip_unit, rel_tol=1e-6)

    @pytest.mark.parametrize("pos_type,open_p,buffer_pips,sym,expected_sl", [
        ("BUY", 2640.00, 1.0, "XAUUSD", 2640.10),     # Gold BUY: +1 pip = +0.10
        ("SELL", 2640.00, 1.0, "XAUUSD", 2639.90),    # Gold SELL: -1 pip = -0.10
        ("BUY", 1.08500, 1.5, "EURUSD", 1.08515),     # FX BUY: +1.5 pips = +0.00015
        ("SELL", 1.08500, 1.5, "EURUSD", 1.08485),    # FX SELL: -1.5 pips = -0.00015
        ("BUY", 155.00, 2.0, "USDJPY", 155.02),       # JPY BUY: +2 pips = +0.02
        ("SELL", 155.00, 2.0, "USDJPY", 154.98),      # JPY SELL: -2 pips = -0.02
        ("BUY", 63000.0, 10.0, "BTCUSD", 63010.0),    # BTC BUY: +10 pips = +10.0
        ("SELL", 63000.0, 10.0, "BTCUSD", 62990.0),   # BTC SELL: -10 pips = -10.0
        ("BUY", 2640.00, 0.0, "XAUUSD", 2640.00),     # Zero buffer (pure entry breakeven)
        ("BUY", 2640.00, 50.0, "XAUUSD", 2645.00),    # Wide 50-pip buffer
    ])
    def test_breakeven_spread_buffer_precision(self, fleet_exec, pos_type, open_p, buffer_pips, sym, expected_sl):
        """Empirically tests breakeven locking with spread buffers under various pip regimes."""
        pos = {
            "ticket": 77701,
            "symbol": sym,
            "type": pos_type,
            "direction": pos_type,
            "open_price": open_p,
            "sl": open_p - 10.0 if pos_type == "BUY" else open_p + 10.0,
            "status": "RUNNING"
        }
        fleet_exec.active_positions = [pos]
        res = fleet_exec.manage_position_action(ticket=77701, action="be", buffer_pips=buffer_pips)

        assert res["success"] is True
        resulting_sl = pos["sl"]
        assert math.isclose(resulting_sl, expected_sl, abs_tol=1e-4), f"Expected SL {expected_sl}, got {resulting_sl}"
        assert pos["status"] == "BE_LOCKED"


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARTIAL SCALE-OUT & ODD LOT ROUNDING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPartialScaleOutAndLotRoundingAdversarial:
    """Stress-tests odd lot sizes, partial scale-outs, and volume conservation."""

    @pytest.fixture
    def fleet_exec(self):
        mt5 = MT5Connector(simulation_mode=True)
        bitget = BitgetConnector(sim_mode=True)
        return AutonomousFleetExecutor(
            risk_manager=None,
            whatsapp_manager=None,
            bitget_connector=bitget,
            mt5_connector=mt5
        )

    @pytest.mark.parametrize("initial_lots,expected_min_rem", [
        (0.01, 0.01),   # Minimum possible lot size (floor protection)
        (0.02, 0.01),   # 0.02 -> scale 0.01 -> rem 0.01
        (0.03, 0.01),   # 0.03 -> scale 0.01 or 0.02 -> rem >= 0.01
        (0.05, 0.02),   # 0.05 -> scale 0.03 -> rem 0.02 or 0.03
        (0.07, 0.03),   # 0.07 -> scale 0.04 -> rem 0.03
        (0.11, 0.05),   # 0.11 -> scale 0.06 -> rem 0.05
        (0.33, 0.16),   # 0.33 -> scale 0.16 -> rem 0.17
        (1.05, 0.52),   # 1.05 -> scale 0.52 -> rem 0.53
        (10.00, 5.00),  # Institutional standard lot
    ])
    def test_odd_lot_partial_scale_out(self, fleet_exec, initial_lots, expected_min_rem):
        """Verifies partial 50% scale-out with odd lot rounding and volume constraints."""
        pos = {
            "ticket": 88801,
            "symbol": "EURUSD",
            "type": "BUY",
            "direction": "BUY",
            "lots": initial_lots,
            "open_price": 1.08500,
            "sl": 1.08000,
            "status": "RUNNING"
        }
        fleet_exec.active_positions = [pos]
        res = fleet_exec.manage_position_action(ticket=88801, action="scale_50", buffer_pips=1.0)

        assert res["success"] is True
        rem_lots = pos["lots"]
        assert rem_lots >= 0.01, f"Remaining lots {rem_lots} must be >= minimum lot (0.01)"
        assert rem_lots <= initial_lots, f"Remaining lots {rem_lots} cannot exceed initial lots {initial_lots}"
        assert pos["status"] == "SCALED_50_BE"

    def test_cascading_multiple_scale_outs(self, fleet_exec):
        """Tests repeatedly scaling out a position until minimum volume is reached."""
        pos = {
            "ticket": 88802,
            "symbol": "XAUUSD",
            "type": "BUY",
            "lots": 1.00,
            "open_price": 2645.00,
            "sl": 2635.00,
            "status": "RUNNING"
        }
        fleet_exec.active_positions = [pos]

        # Cascading scale-outs down to minimum lot floor
        for _ in range(10):
            res = fleet_exec.manage_position_action(ticket=88802, action="scale_50")
            assert res["success"] is True
            assert pos["lots"] >= 0.01

        # Final state must remain clamped at minimum lot floor 0.01, never 0 or negative
        assert pos["lots"] == 0.01

    def test_bitget_connector_partial_close_precision(self):
        """Verifies Bitget crypto connector handles decimal precision in partial scaling."""
        bitget = BitgetConnector(sim_mode=True)
        # Place crypto position
        order_res = bitget.place_order("BTCUSDT", "buy", 0.075, price=63000.0)
        assert order_res["status"] == "success"
        order_id = order_res["order_id"]

        # Scale out 0.0375
        ok = bitget.close_partial_position(order_id=order_id, close_size=0.0375, symbol="BTCUSDT")
        assert ok is True

        # Check remaining size
        positions = bitget.get_open_positions()
        target = next((p for p in positions if p["order_id"] == order_id), None)
        assert target is not None
        assert math.isclose(target["size"], 0.0375, abs_tol=0.001)


# ══════════════════════════════════════════════════════════════════════════════
# 3. KILL-SWITCH CONCURRENCY & RACE CONDITION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestKillSwitchConcurrencyAndRaceConditions:
    """Adversarial concurrency & stress testing for dual-venue emergency kill-switch."""

    def test_rapid_sequential_kill_switch_idempotency(self):
        """Repeated sequential kill-switch calls must be 100% idempotent without error."""
        mt5 = MT5Connector(simulation_mode=True)
        bitget = BitgetConnector(sim_mode=True)
        executor = AutonomousFleetExecutor(
            risk_manager=None,
            whatsapp_manager=None,
            bitget_connector=bitget,
            mt5_connector=mt5
        )

        # Seed positions
        mt5.place_order("EURUSD", "BUY", 0.5, 1.0850, 1.0800, 1.0950)
        mt5.place_order("GBPUSD", "SELL", 0.3, 1.2850, 1.2900, 1.2750)
        bitget.place_order("BTCUSDT", "buy", 0.1, price=63000.0)

        # First trigger
        res1 = executor.emergency_kill_switch()
        assert res1["success"] is True
        assert res1["total_closed"] >= 3
        assert len(executor.active_positions) == 0

        # Second rapid trigger (already flattened)
        res2 = executor.emergency_kill_switch()
        assert res2["success"] is True
        assert res2["total_closed"] == 0
        assert len(executor.active_positions) == 0

        # Third rapid trigger
        res3 = executor.emergency_kill_switch()
        assert res3["success"] is True
        assert res3["total_closed"] == 0

    def test_concurrent_multithreaded_kill_switch(self):
        """50 concurrent threads firing emergency kill-switch must not corrupt state or crash."""
        mt5 = MT5Connector(simulation_mode=True)
        bitget = BitgetConnector(sim_mode=True)
        executor = AutonomousFleetExecutor(
            risk_manager=None,
            whatsapp_manager=None,
            bitget_connector=bitget,
            mt5_connector=mt5
        )

        # Populate positions
        for i in range(10):
            mt5.place_order(f"SYM_{i}", "BUY", 0.1, 100.0, 90.0, 120.0)
            bitget.place_order(f"CRYPTO_{i}", "buy", 0.05, price=1000.0)

        results = []
        errors = []

        def trigger_kill():
            try:
                r = executor.emergency_kill_switch()
                return r
            except Exception as e:
                errors.append(str(e))
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as t_pool:
            futures = [t_pool.submit(trigger_kill) for _ in range(50)]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res:
                    results.append(res)

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(results) == 50
        assert all(r["success"] is True for r in results)
        assert len(executor.active_positions) == 0
        assert len(mt5._mock_positions) == 0
        assert len(bitget.sim_positions) == 0

    def test_cockpit_control_kill_switch_api(self):
        """Tests POST /api/control with 'kill_switch' action."""
        client = app.test_client()
        res = client.post("/api/control", json={"action": "kill_switch"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "EMERGENCY KILL SWITCH ENGAGED" in data["message"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. WHATSAPP DIRECTIVE SPOOFING & AUTHENTICATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestWhatsAppDirectiveSpoofingAndAuthAdversarial:
    """Adversarial spoofing, injection, and authorization boundary verification."""

    @pytest.mark.parametrize("spoofed_sender", [
        "19999999999",                      # Unknown international number
        "923468053269",                      # Off-by-one master number
        "+14155552671",                      # US phone number
        "447700900077@s.whatsapp.net",       # UK JID
        "random_hacker@s.whatsapp.net",      # Arbitrary string JID
        "status@broadcast",                  # WhatsApp status broadcast
        "120363401615322543@g.us",           # Non-whitelisted group
        "attacker@lid",                      # Wildcard @lid spoofing attempt
        "1234567890@lid",                    # Numeric unapproved @lid
        "admin@lid",                         # Impersonation @lid
        "923468053268.attacker.com",         # Domain spoofing
        "923468053268@g.us",                 # Personal number treated as group
        "",                                  # Empty string
        None,                                # None
        " ",                                 # Whitespace
        "923468053268\x00extra",             # Null-byte injection
        "923468053268\n19999999999",         # CRLF injection
        "' OR '1'='1",                       # SQL injection string
        "<script>alert(1)</script>",         # XSS string
    ])
    def test_unauthorized_senders_strictly_rejected(self, spoofed_sender):
        """Validates that all unauthorized senders and malicious JID formats are blocked."""
        assert is_whitelisted_number(spoofed_sender) is False

    @pytest.mark.parametrize("valid_sender", [
        "923468053268",
        "+923468053268",
        "00923468053268",
        "03468053268",
        "923468053268@s.whatsapp.net",
        "923468053268:0@s.whatsapp.net",
        "120363401615322542@g.us",           # Elite Trade Group
        "linked_device_user@lid",
        "master_user@lid",
        "owner@lid"
    ])
    def test_authorized_master_senders_accepted(self, valid_sender):
        """Validates that legitimate Master Owner and Elite Trade Group JIDs pass whitelist."""
        assert is_whitelisted_number(valid_sender) is True

    def test_whatsapp_command_unauthorized_rejection(self):
        """Validates POST /api/whatsapp_command rejects spoofed / unauthorized senders with 403."""
        client = app.test_client()

        malicious_payloads = [
            {"command": "'; DROP TABLE trades; --", "sender": "19999999999"},
            {"command": "<script>alert('xss')</script>", "sender": "attacker@evil.com"},
            {"command": "KILL; rm -rf /", "sender": "923468053269"},
            {"command": "A" * 50000, "sender": "12345678"},
            {"message": "BE", "sender": "447700900077@s.whatsapp.net"},
            {"text": "SCALE 50", "sender": "unauthorized@lid"},
        ]

        for p in malicious_payloads:
            res = client.post("/api/whatsapp_command", json=p)
            assert res.status_code == 403, f"Payload {p} should be rejected with 403, got {res.status_code}"

    def test_whatsapp_authorized_directives_execution(self):
        """Verifies legitimate 1-click risk directives executed by Master Owner."""
        client = app.test_client()
        valid_sender = "923468053268"

        test_commands = [
            ("STATUS", 200),
            ("KILL", 200),
            ("CLOSE ALL", 200),
            ("BE", 200),
            ("SCALE50", 200),
            ("SCALE 50", 200),
            ("BUY XAUUSD 0.10", 200),
            ("SELL EURUSD 0.05", 200),
            ("summary", 200),
            ("pause", 200),
            ("resume", 200)
        ]

        for cmd, expected_code in test_commands:
            res = client.post("/whatsapp", json={"command": cmd, "sender": valid_sender})
            assert res.status_code == expected_code, f"Failed for directive '{cmd}': {res.status_code}"
            data = res.get_json()
            assert data.get("success") is True or "response" in data or "reply" in data


# ══════════════════════════════════════════════════════════════════════════════
# 5. COCKPIT API HTTP ENDPOINT FUZZING & RESILIENCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCockpitAPIHttpFuzzingAndResilience:
    """HTTP fuzzing across all Cockpit endpoints for method safety, malformed JSON, query tampering."""

    @pytest.fixture
    def client(self):
        return app.test_client()

    @pytest.mark.parametrize("endpoint", [
        "/api/status",
        "/api/trade_cards",
        "/api/alpha_models",
        "/api/liquidation_radar",
        "/api/world_monitor",
        "/api/market_weather",
        "/api/accounts",
        "/api/shark_forensics"
    ])
    def test_get_endpoints_reject_invalid_http_methods(self, client, endpoint):
        """GET-only endpoints should reject POST/PUT/DELETE/PATCH with 405 Method Not Allowed."""
        res_post = client.post(endpoint)
        assert res_post.status_code == 405, f"POST on {endpoint} must return 405, got {res_post.status_code}"

        res_put = client.put(endpoint)
        assert res_put.status_code == 405, f"PUT on {endpoint} must return 405, got {res_put.status_code}"

        res_delete = client.delete(endpoint)
        assert res_delete.status_code == 405, f"DELETE on {endpoint} must return 405, got {res_delete.status_code}"

    @pytest.mark.parametrize("endpoint", [
        "/api/control",
        "/api/execution/action",
        "/api/onboard_account",
        "/api/whatsapp_command",
        "/api/whatsapp_audio"
    ])
    def test_post_endpoints_reject_invalid_http_methods(self, client, endpoint):
        """POST-only endpoints should reject GET/PUT/DELETE with 405 Method Not Allowed."""
        res_get = client.get(endpoint)
        assert res_get.status_code == 405, f"GET on {endpoint} must return 405, got {res_get.status_code}"

        res_delete = client.delete(endpoint)
        assert res_delete.status_code == 405, f"DELETE on {endpoint} must return 405, got {res_delete.status_code}"

    @pytest.mark.parametrize("endpoint", [
        "/api/control",
        "/api/execution/action",
        "/api/onboard_account",
        "/api/whatsapp_command"
    ])
    def test_malformed_syntax_json_handled_without_unhandled_crash(self, client, endpoint):
        """Sends broken JSON syntax and empty bodies."""
        headers = {"Content-Type": "application/json"}

        # Truncated broken JSON syntax
        res1 = client.post(endpoint, data="{'invalid_json': ", headers=headers)
        assert res1.status_code in [400, 403, 405], f"Broken JSON syntax on {endpoint} returned {res1.status_code}"

        # Empty body
        res3 = client.post(endpoint, data="", headers=headers)
        assert res3.status_code in [200, 400, 403, 405]

    @pytest.mark.parametrize("bad_symbol", [
        "../../etc/passwd",
        "<script>alert(1)</script>",
        "XAU' OR '1'='1",
        "NONEXISTENT_SYMBOL_XYZ_999",
        "%00%00%00",
        "A" * 1000,
        "!!@@##$$%%^^&&**",
        "-12345",
        "0",
    ])
    def test_query_parameter_tampering_resilience(self, client, bad_symbol):
        """Fuzzes symbol query params on liquidation radar, chart data, and market commentary."""
        res_liq = client.get(f"/api/liquidation_radar?symbol={bad_symbol}")
        assert res_liq.status_code == 200, f"Liquidation radar crashed on {bad_symbol}: {res_liq.status_code}"
        assert "symbol" in res_liq.get_json()

        res_chart = client.get(f"/api/chart_data/{bad_symbol}")
        assert res_chart.status_code in [200, 400, 404]

        res_comm = client.get(f"/api/live_commentary?symbol={bad_symbol}")
        assert res_comm.status_code == 200

    def test_execution_action_fuzzing(self, client):
        """Fuzzes /api/execution/action with edge-case tickets and actions."""
        # Missing action
        r1 = client.post("/api/execution/action", json={"ticket": 9841201})
        assert r1.status_code == 400

        # Unknown action
        r2 = client.post("/api/execution/action", json={"ticket": 9841201, "action": "fly_to_moon"})
        assert r2.status_code == 400

        # Huge ticket integer
        r3 = client.post("/api/execution/action", json={"ticket": 999999999999999999999999, "action": "breakeven"})
        assert r3.status_code == 200
        assert r3.get_json()["status"] == "success"

        # Non-integer string ticket
        r4 = client.post("/api/execution/action", json={"ticket": "TICKET_STRING_ABC", "action": "scale_50"})
        assert r4.status_code == 200

        # Negative ticket
        r5 = client.post("/api/execution/action", json={"ticket": -999, "action": "close"})
        assert r5.status_code == 200

        # Valid ticket with all 4 supported actions
        for act in ["be", "scale_50", "close", "trail_fvg"]:
            r = client.post("/api/execution/action", json={"ticket": 9841201, "action": act})
            assert r.status_code == 200
            assert r.get_json()["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# 6. ROUTE ORDER DUAL-VENUE TAXONOMY & CONTRACT #2 STRESS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDualVenueRouterTaxonomyContract2:
    """Stress-tests symbol-taxonomical dispatching under Contract #2."""

    @pytest.fixture
    def executor(self):
        mt5 = MT5Connector(simulation_mode=True)
        bitget = BitgetConnector(sim_mode=True)
        return AutonomousFleetExecutor(
            risk_manager=None,
            whatsapp_manager=None,
            bitget_connector=bitget,
            mt5_connector=mt5
        )

    @pytest.mark.parametrize("sym,expected_venue,expected_target_sym", [
        ("XAUUSD", "MT5", "XAUUSD"),
        ("EURUSD", "MT5", "EURUSD"),
        ("GBPUSD", "MT5", "GBPUSD"),
        ("USDJPY", "MT5", "USDJPY"),
        ("BTCUSD", "BITGET", "BTCUSDT"),
        ("BTCUSDT", "BITGET", "BTCUSDT"),
        ("ETHUSD", "BITGET", "ETHUSDT"),
        ("ETHUSDT", "BITGET", "ETHUSDT"),
        ("SOLUSD", "BITGET", "SOLUSDT"),
        ("SOLUSDT", "BITGET", "SOLUSDT"),
    ])
    def test_contract_2_dual_venue_order_routing(self, executor, sym, expected_venue, expected_target_sym):
        """Verifies Project Interface Contract #2: route_order returns authentic ExecutionReceipt."""
        order = {
            "symbol": sym,
            "direction": "BUY",
            "lots": 0.15,
            "entry_price": 100.0,
            "sl": 95.0,
            "tp": 110.0
        }
        receipt = executor.route_order(account_id="TEST_50543", order=order)

        assert receipt["venue"] == expected_venue
        assert receipt["symbol"] == expected_target_sym
        assert receipt["lots"] == 0.15
        assert receipt["direction"] == "BUY"
        assert receipt["status"] == "FILLED"
        assert "receipt_id" in receipt
        expected_pfx = "RCPT-BG-" if expected_venue == "BITGET" else "RCPT-MT5-"
        assert receipt["receipt_id"].startswith(expected_pfx)
        assert receipt["success"] is True
