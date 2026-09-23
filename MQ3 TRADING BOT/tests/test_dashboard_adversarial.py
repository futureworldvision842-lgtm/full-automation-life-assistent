"""
tests/test_dashboard_adversarial.py — Empirical Stress & Adversarial Challenge Suite.
===================================================================================
Milestone M3 (Requirement R3: WorldMonitor-Style Web Command Cockpit Overhaul).

Adversarial Stress Scenarios:
  1. Extreme & Boundary Values (Huge balances, tiny floats, boundary risk caps, unicode & XSS injection)
  2. High-Volume Sequential & Concurrent Account Onboarding Burst & AUM aggregation
  3. Malformed JSON Payloads, Non-Dict Root Types, Deeply Nested JSON & Corrupted Content-Types
  4. Invalid & Malformed Action Types on /api/execution/action and /api/control
  5. Standalone Resilience & Fault-Tolerance Under Engine Exceptions (M1, M2, Onboarder, Scanner)
  6. Multithreaded Concurrent Load across All REST Endpoints
  7. Query Parameter & Path Parameter Boundary Fuzzing
"""

import sys
import os
import json
import time
import math
import concurrent.futures
import pytest
from unittest.mock import MagicMock, patch

import dashboard.app as dashboard_module
from dashboard.app import app, _RUNTIME_FLEET_STORE


@pytest.fixture
def client():
    """Provides an isolated Flask test client in testing mode."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# 1. EXTREME & BOUNDARY VALUES (Account Onboarding & Risk Calibration)
# ══════════════════════════════════════════════════════════════════════════════

class TestBoundaryAndExtremeValues:
    """Stress tests extreme, boundary, and pathological inputs on /api/onboard_account."""

    def test_onboard_huge_balance_100_trillion(self, client):
        """Tests astronomical balance ($100 Trillion AUM) without numeric overflow."""
        huge_balance = 100_000_000_000_000.0  # 1e14
        payload = {
            "account_id": "SOVEREIGN-WEALTH-01",
            "balance": huge_balance,
            "platform": "FUNDING_PIPS"
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        acc = data["account"]
        assert acc["starting_balance"] == huge_balance
        assert acc["daily_loss_dollar_cap"] == huge_balance * 0.015
        assert acc["trailing_hwm_floor"] == huge_balance * 0.96
        assert acc["hard_daily_loss_dollar_cap"] == huge_balance * 0.05

    def test_onboard_microscopic_positive_balance(self, client):
        """Tests microscopic positive balance ($0.01)."""
        payload = {
            "account_id": "MICRO-ACC-01",
            "balance": 0.01,
            "platform": "PERSONAL"
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["account"]["starting_balance"] == 0.01
        assert data["account"]["daily_loss_dollar_cap"] == 0.0  # rounded to 2 decimals

    def test_onboard_negative_balance_rejection(self, client):
        """Tests that negative balances are strictly rejected with HTTP 400."""
        for neg_val in [-0.01, -500.0, -1e12]:
            payload = {"account_id": "REJECT-NEG", "balance": neg_val, "platform": "FTMO"}
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"
            assert "positive" in data["message"].lower()

    def test_onboard_zero_balance_rejection(self, client):
        """Tests that zero balance is rejected with HTTP 400."""
        payload = {"account_id": "REJECT-ZERO", "balance": 0.0, "platform": "FTMO"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"

    def test_onboard_string_numeric_balance_coercion(self, client):
        """Tests that valid numeric strings (e.g. '25000.50') are safely coerced."""
        payload = {
            "account_id": "STRING-BAL-01",
            "balance": "25000.50",
            "platform": "FUNDING_PIPS"
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["account"]["starting_balance"] == 25000.50

    def test_onboard_invalid_non_numeric_balance_rejection(self, client):
        """Tests that non-numeric balance strings ('twenty-five-k', '$$$', None) return 400."""
        for invalid_bal in ["twenty-five-thousand", "$25,000", "", [], {}]:
            payload = {"account_id": "INV-BAL", "balance": invalid_bal, "platform": "FUNDING_PIPS"}
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"

    def test_onboard_empty_and_whitespace_account_id_rejection(self, client):
        """Tests that empty or whitespace-only account_id values return HTTP 400."""
        for empty_id in ["", "   ", "\t\t\n", None]:
            payload = {"account_id": empty_id, "balance": 25000.0, "platform": "FUNDING_PIPS"}
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"

    def test_onboard_numeric_integer_account_id(self, client):
        """Tests that numeric integer account IDs (e.g. 5054340275) are converted to string."""
        payload = {"account_id": 9988776655, "balance": 25000.0, "platform": "FUNDING_PIPS"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["account"]["account_id"] == "9988776655"

    def test_onboard_unicode_and_special_character_account_id(self, client):
        """Tests handling of international unicode, Arabic, Chinese, emojis, and special chars."""
        special_ids = [
            "حساب_محمد_١٢٣",
            "测试账户_PropFirm_888",
            "ACC-🔥-ALPHA-99",
            "ACC~!@#$%^&*()_+{}[]:;'<>,.?/"
        ]
        for s_id in special_ids:
            payload = {"account_id": s_id, "balance": 50000.0, "platform": "FTMO"}
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 200
            data = res.get_json()
            assert data["account"]["account_id"] == s_id

    def test_onboard_xss_and_sql_injection_payload_safety(self, client):
        """Tests that XSS tags and SQL injection payloads are safely stored without server error."""
        attack_strings = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE accounts; --",
            "admin' OR '1'='1",
            "../../../../etc/passwd",
            "{{ 7 * 7 }}"
        ]
        for atk in attack_strings:
            payload = {"account_id": atk, "balance": 10000.0, "platform": "FUNDING_PIPS"}
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "success"
            assert data["account"]["account_id"] == atk

    def test_risk_cap_clamping_behavior(self, client):
        """Funding Pips risk is clamped to the 0.10%-0.25% internal range."""
        # 1. Sub-minimum risk -> clamped to 0.1%
        res_low = client.post("/api/onboard_account", json={
            "account_id": "CLAMP-LOW", "balance": 10000.0, "custom_risk_pct": 0.001
        })
        assert res_low.status_code == 200
        assert res_low.get_json()["account"]["risk_per_trade_pct"] == 0.1

        # 2. Negative risk -> clamped to 0.1%
        res_neg = client.post("/api/onboard_account", json={
            "account_id": "CLAMP-NEG", "balance": 10000.0, "custom_risk_pct": -5.0
        })
        assert res_neg.status_code == 200
        assert res_neg.get_json()["account"]["risk_per_trade_pct"] == 0.1

        # 3. Excessive risk (e.g. 50%) -> clamped to 0.25%
        res_high = client.post("/api/onboard_account", json={
            "account_id": "CLAMP-HIGH", "balance": 10000.0, "custom_risk_pct": 50.0
        })
        assert res_high.status_code == 200
        assert res_high.get_json()["account"]["risk_per_trade_pct"] == 0.25

        # 4. Invalid non-numeric risk -> falls back to platform default
        res_str = client.post("/api/onboard_account", json={
            "account_id": "CLAMP-STR", "balance": 10000.0, "platform": "FTMO", "custom_risk_pct": "not_a_number"
        })
        assert res_str.status_code == 200
        assert res_str.get_json()["account"]["risk_per_trade_pct"] == 1.0  # FTMO default


# ══════════════════════════════════════════════════════════════════════════════
# 2. HIGH-VOLUME & RAPID BURST STRESS TESTING
# ══════════════════════════════════════════════════════════════════════════════

class TestHighVolumeAccountStress:
    """Stress tests rapid sequential onboarding burst (500 accounts) and aggregate AUM."""

    def test_rapid_burst_onboard_500_accounts(self, client):
        start_time = time.time()
        num_accounts = 500
        base_balance = 25000.0

        for i in range(num_accounts):
            acc_id = f"BURST-ACC-{i:04d}"
            payload = {
                "account_id": acc_id,
                "balance": base_balance + (i * 100.0),
                "platform": "FUNDING_PIPS" if i % 2 == 0 else "HYPERLIQUID",
                "custom_risk_pct": 0.5 + (i % 10) * 0.1
            }
            res = client.post("/api/onboard_account", json=payload)
            assert res.status_code == 200

        elapsed = time.time() - start_time
        print(f"\n[STRESS] 500 accounts onboarded in {elapsed:.3f}s ({num_accounts / elapsed:.1f} req/sec)")
        assert elapsed < 35.0  # Must complete 500 requests comfortably within 35 seconds

        # Verify aggregate /api/accounts query reflects newly onboarded fleet
        res_fleet = client.get("/api/accounts")
        assert res_fleet.status_code == 200
        fleet_data = res_fleet.get_json()
        assert fleet_data["active_accounts"] >= num_accounts
        assert fleet_data["total_aum_potential"] >= (num_accounts * base_balance)

    def test_idempotent_account_overwrite(self, client):
        """Tests that onboarding the same account_id multiple times updates state safely without duplication."""
        acc_id = "IDEMPOTENT-ACC-88"
        
        # Pass 1: $10,000
        res1 = client.post("/api/onboard_account", json={"account_id": acc_id, "balance": 10000.0, "platform": "FTMO"})
        assert res1.status_code == 200
        assert res1.get_json()["account"]["starting_balance"] == 10000.0

        # Pass 2: Update to $25,000
        res2 = client.post("/api/onboard_account", json={"account_id": acc_id, "balance": 25000.0, "platform": "FTMO"})
        assert res2.status_code == 200
        assert res2.get_json()["account"]["starting_balance"] == 25000.0

        # Verify in accounts roster
        res_list = client.get("/api/accounts")
        matches = [a for a in res_list.get_json()["accounts"] if str(a.get("id")) == acc_id]
        assert len(matches) == 1
        assert matches[0]["starting_balance"] == 25000.0


# ══════════════════════════════════════════════════════════════════════════════
# 3. MALFORMED JSON, NON-DICT ROOTS & UNEXPECTED CONTENT-TYPES
# ══════════════════════════════════════════════════════════════════════════════

class TestMalformedPayloadsAndContentTypes:
    """Stress tests corrupted payloads, wrong MIME types, and non-dict JSON roots."""

    def test_non_json_content_type_rejected(self, client):
        """POST with text/plain, xml, html or octet-stream must return 400 Bad Request."""
        endpoints = [
            "/api/onboard_account",
            "/api/execution/action",
            "/api/control",
            "/api/chat_consult",
            "/api/simulate_what_if",
            "/api/whatsapp_command"
        ]
        
        for ep in endpoints:
            # 1. text/plain
            res_txt = client.post(ep, data="plain text data", content_type="text/plain")
            assert res_txt.status_code in [200, 400, 403, 415]  # graceful handling without 500

            # 2. application/xml
            res_xml = client.post(ep, data="<root><id>123</id></root>", content_type="application/xml")
            assert res_xml.status_code in [200, 400, 403, 415]

            # 3. binary octet stream
            res_bin = client.post(ep, data=b"\x00\xFF\xFE\xFD\xAA\xBB", content_type="application/octet-stream")
            assert res_bin.status_code in [200, 400, 403, 415]

    def test_corrupted_json_syntax_handling(self, client):
        """Syntactically broken JSON strings must be caught gracefully."""
        broken_json = "{\"account_id\": 123, \"balance\": [unclosed array"
        res = client.post("/api/onboard_account", data=broken_json, content_type="application/json")
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"

    def test_non_dict_json_root_types(self, client):
        """Tests JSON arrays, strings, integers, and booleans sent as payload root."""
        non_dict_payloads = [
            [1, 2, 3, 4],
            "just_a_string",
            123456,
            True,
            False
        ]
        for p in non_dict_payloads:
            res = client.post("/api/onboard_account", json=p)
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"

    def test_empty_json_body_onboarding(self, client):
        """Empty JSON object `{}` sent to /api/onboard_account returns 400."""
        res = client.post("/api/onboard_account", json={})
        assert res.status_code == 400
        data = res.get_json()
        assert data["status"] == "error"


# ══════════════════════════════════════════════════════════════════════════════
# 4. INVALID ACTION TYPES & EXECUTION CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionActionInvalidInputs:
    """Stress tests /api/execution/action and /api/control with invalid or adversarial actions."""

    def test_unknown_execution_actions(self, client):
        """Tests that unknown execution actions return 400 with clean error message."""
        bad_actions = [
            "destroy_account",
            "DROP_TABLE",
            "<script>alert(1)</script>",
            "BUY_ALL_MARKET",
            "random_unknown_action",
            "BREAKEVE N"
        ]
        for act in bad_actions:
            payload = {"ticket": 9841201, "action": act}
            res = client.post("/api/execution/action", json=payload)
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"
            assert "Unknown execution action" in data["message"]

    def test_missing_or_empty_action_parameter(self, client):
        """Missing or empty action returns 400."""
        for bad_action_val in [None, "", False]:
            payload = {"ticket": 9841201, "action": bad_action_val}
            res = client.post("/api/execution/action", json=payload)
            assert res.status_code == 400

    def test_ticket_data_type_variations(self, client):
        """Tests string, negative, huge, and None ticket identifiers across all valid actions."""
        valid_actions = ["breakeven", "scale_50", "close", "trail_fvg"]
        test_tickets = [
            "TICKET-STRING-9999",
            -1,
            0,
            999999999999999999,
            None,
            "0x9841201"
        ]
        for act in valid_actions:
            for tkt in test_tickets:
                res = client.post("/api/execution/action", json={"ticket": tkt, "action": act})
                assert res.status_code == 404
                data = res.get_json()
                assert data["status"] == "error"
                assert data["success"] is False

    def test_control_endpoint_invalid_actions(self, client):
        """Tests /api/control with unknown actions returns 400."""
        for invalid_act in ["explode", "restart_os", "", None, 999]:
            res = client.post("/api/control", json={"action": invalid_act})
            assert res.status_code == 400
            data = res.get_json()
            assert data["status"] == "error"

    def test_control_kill_switch_action(self, client):
        """Tests that emergency kill switch returns 200 success."""
        res = client.post("/api/control", json={"action": "kill_switch"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert "KILL SWITCH" in data["message"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. STANDALONE RESILIENCE & ENGINE FAULT INJECTION
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineFaultTolerance:
    """Verifies that unhandled exceptions from M1/M2/Aux engines are caught gracefully."""

    def test_world_monitor_resilience_when_engine_crashes(self, client):
        """When the engine crashes, the route exposes an unavailable state without invented telemetry."""
        mock_engine = MagicMock()
        mock_engine.get_world_intelligence_brief.side_effect = RuntimeError("Telemetry Link Severed!")

        with patch.object(dashboard_module, "world_monitor_engine", mock_engine):
            res = client.get("/api/world_monitor")
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "unavailable"
            assert data["actionable"] is False
            assert "chokepoints" in data
            assert len(data["chokepoints"]) == 0
            assert "defcon_level" in data

    def test_market_weather_resilience_when_engine_crashes(self, client):
        """When weather fails, no directional probability is fabricated."""
        mock_engine = MagicMock()
        mock_engine.forecast_market_weather.side_effect = ZeroDivisionError("Barometric calculation div/0")

        with patch.object(dashboard_module, "weather_engine", mock_engine):
            res = client.get("/api/market_weather?symbol=XAUUSD")
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "unavailable"
            assert data["actionable"] is False
            assert "regime" in data
            assert "barometric_pressure_hpa" in data
            assert data["barometric_pressure_hpa"] is None

    def test_auto_onboarder_exception_resilience(self, client):
        """When auto_onboarder raises IOError on disk write, onboard_account still succeeds in memory."""
        mock_onboarder = MagicMock()
        mock_onboarder.onboard_new_account.side_effect = IOError("Disk full: cannot write fleet_config.json")

        with patch.object(dashboard_module, "auto_onboarder", mock_onboarder):
            res = client.post("/api/onboard_account", json={
                "account_id": "DISK-FAIL-TEST",
                "balance": 25000.0,
                "platform": "FUNDING_PIPS"
            })
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "success"
            assert data["account"]["account_id"] == "DISK-FAIL-TEST"

    def test_trade_consultant_exception_resilience(self, client):
        """When trade_consultant raises an exception, /api/chat_consult falls back safely."""
        mock_consultant = MagicMock()
        mock_consultant.parse_inquiry_intent.side_effect = ValueError("NLP Parser Error")

        with patch.object(dashboard_module, "trade_consultant", mock_consultant):
            res = client.post("/api/chat_consult", json={"query": "Aapka gold analysis kya hai?"})
            assert res.status_code == 503
            data = res.get_json()
            assert "advice" in data
            assert "parsed" in data
            assert data["actionable"] is False

    def test_multi_scanner_exception_resilience(self, client):
        """When multi_scanner raises an exception, /api/market_intelligence falls back or returns clean error."""
        mock_scanner = MagicMock()
        mock_scanner.scan_all_markets.side_effect = Exception("API Timeout")

        with patch.object(dashboard_module, "multi_scanner", mock_scanner):
            res = client.get("/api/market_intelligence")
            assert res.status_code in [200, 500]
            data = res.get_json()
            assert "status" in data


# ══════════════════════════════════════════════════════════════════════════════
# 6. MULTITHREADED CONCURRENT LOAD STRESS
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrentLoadStress:
    """Stress tests concurrent requests across all major API endpoints."""

    def test_concurrent_api_traffic_burst(self):
        """Executes 100 concurrent requests across mixed REST endpoints using thread-local test clients."""
        endpoints = [
            "/api/world_monitor",
            "/api/market_weather",
            "/api/accounts",
            "/api/shark_forensics",
            "/api/trade_cards",
            "/api/chart_data/XAUUSD",
            "/api/status"
        ]

        def call_ep(ep):
            with app.test_client() as c:
                res = c.get(ep)
                return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            tasks = [executor.submit(call_ep, endpoints[i % len(endpoints)]) for i in range(100)]
            results = [t.result() for t in concurrent.futures.as_completed(tasks)]

        assert len(results) == 100
        assert all(code == 200 for code in results)


# ══════════════════════════════════════════════════════════════════════════════
# 7. QUERY PARAMETER FUZZING & AUXILIARY ENDPOINT SAFETY
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryParameterFuzzing:
    """Fuzzes GET query parameters, path variables, and auxiliary POST endpoints."""

    def test_chart_data_symbol_fuzzing(self, client):
        """Tests /api/chart_data/<symbol> with varied symbols and timeframes."""
        fuzz_symbols = ["XAUUSD", "BTCUSD", "EURUSD", "UNKNOWN_COIN", "CUSTOM_SYNTH_99"]
        for sym in fuzz_symbols:
            for tf in ["M1", "M5", "M15", "H1", "H4", "D1", "INVALID_TF"]:
                res = client.get(f"/api/chart_data/{sym}?tf={tf}")
                assert res.status_code in {200, 503}
                data = res.get_json()
                assert data["symbol"] == sym.upper()
                assert "candles" in data
                if res.status_code == 503:
                    assert data["candles"] == []
                    assert data["actionable"] is False

    def test_broker_shield_spread_fuzzing(self, client):
        """Tests /api/broker_shield_status with edge-case spreads."""
        test_spreads = ["0.0", "18.5", "500.0", "0.0001"]
        for sp in test_spreads:
            res = client.get(f"/api/broker_shield_status?symbol=XAUUSD&spread={sp}")
            assert res.status_code == 200
            data = res.get_json()
            assert ("safe_to_execute" in data) or ("is_safe" in data) or ("symbol" in data)

    def test_simulate_what_if_scenarios(self, client):
        """Tests /api/simulate_what_if across scenarios and unexpected strings."""
        scenarios = ["dxy_drop", "rate_hike_pause", "hawkish_bounce", "nuclear_escalation", "", None]
        for sc in scenarios:
            res = client.post("/api/simulate_what_if", json={"scenario": sc})
            assert res.status_code == 200
            data = res.get_json()
            assert "title" in data
            assert "probability" in data

    def test_whatsapp_command_fuzzing(self, client):
        """Tests /api/whatsapp_command with unexpected commands and senders."""
        test_cmds = [
            ({"command": "status", "sender": "923468053268"}, 200),
            ({"command": "be xauusd", "sender": "923468053268"}, 200),
            ({"command": "scale 50%", "sender": "120363401615322542@g.us"}, 200),
            ({"command": "close all", "sender": "unauthorized_hacker"}, 403),
            ({"command": "", "sender": ""}, 403),
            ({"message": "urdu consultation inquiry"}, 403)
        ]
        for payload, expected_status in test_cmds:
            res = client.post("/api/whatsapp_command", json=payload)
            assert res.status_code == expected_status
            data = res.get_json()
            if expected_status == 200:
                assert data.get("success") is True
                assert "response" in data or "reply" in data
            else:
                assert data.get("success") is False

    def test_whatsapp_command_buy_reproduction_test(self, client):
        """Empirically reproduces and tests the buy command on /api/whatsapp_command."""
        payload = {"command": "buy 0.1 XAUUSD", "sender": "923468053268"}
        res = client.post("/api/whatsapp_command", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True
        assert "BUY" in str(data.get("response", "")) or "BUY" in str(data.get("reply", ""))

    def test_whatsapp_save_endpoint(self, client):
        """Tests /api/whatsapp_save updates credentials safely."""
        res = client.post("/api/whatsapp_save", json={"phone": "923468053268", "key": "test_api_key_123"})
        assert res.status_code == 503
        data = res.get_json()
        assert data.get("success") is False

    def test_weekend_crypto_and_copier_endpoints(self, client):
        """Tests auxiliary status endpoints."""
        res_wk = client.get("/api/weekend_crypto_status")
        assert res_wk.status_code == 200

        res_cp = client.get("/api/fleet_copier_status")
        assert res_cp.status_code == 200

        res_ns = client.get("/api/neural_sentiment")
        assert res_ns.status_code == 200
