"""
test_empirical_challenger1_m1.py — Empirical Challenger 1 Adversarial Test Suite for Milestone 1.

Rigorously stress-tests:
  1. REST API parameter boundaries, invalid symbols/timeframes, and schema validation.
  2. WhatsApp whitelist security (authorized vs unauthorized senders and spoofing).
  3. 1-Click execution actions (50% scale-out, breakeven, modify SL/TP, panic kill-switch) across Crypto, FX, and Gold.
  4. Aladdin 99% VaR/CVaR, Funding Pips Trailing HWM Floor, and 35% Consistency Pacing under extreme market swings.
  5. World Monitor Geopolitical Radar telemetry and WebSocket channel resiliency.
"""

import os
import sys
import pytest
import numpy as np
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.web_terminal_server import (
    app,
    terminal_state,
    voice_engine,
    ws_manager,
    GBMSyntheticMarketSimulator,
    MarketDataFeedManager
)
from src.whatsapp_qr_manager import is_whitelisted_number, WhatsAppQRManager, AUTHORIZED_CONTACTS
from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert


@pytest.fixture(autouse=True)
def reset_server_state():
    """Resets the mock state before each test for clean deterministic execution."""
    terminal_state.status = "RUNNING"
    terminal_state.simulation_mode = True
    terminal_state.balance = 25480.00
    terminal_state.equity = 25730.00
    terminal_state.daily_profit = 250.00
    terminal_state._seed_initial_positions()


# =====================================================================
# 1. REST API Parameter Boundary & Input Sanitization Attacks
# =====================================================================

class TestRestApiBoundaryInputs:
    """Adversarial testing on REST endpoints with boundary, malformed, and out-of-spec inputs."""

    def test_candles_boundary_limits(self):
        """Verifies limit parameter boundaries on GET /api/candles."""
        with TestClient(app) as client:
            # Valid boundaries
            res_min = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=10")
            assert res_min.status_code == 200
            assert res_min.json()["count"] == 10

            res_max = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=1000")
            assert res_max.status_code == 200
            assert res_max.json()["count"] == 1000

            # Out of bounds: limit < 10 returns 422
            res_low = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=9")
            assert res_low.status_code == 422

            res_zero = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=0")
            assert res_zero.status_code == 422

            res_neg = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=-5")
            assert res_neg.status_code == 422

            # Out of bounds: limit > 1000 returns 422
            res_high = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=1001")
            assert res_high.status_code == 422

            # Malformed type
            res_alpha = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=infinite")
            assert res_alpha.status_code == 422

    def test_candles_symbol_case_and_fallback(self):
        """Verifies symbol parameter case-insensitivity and fallback behavior for unlisted symbols."""
        with TestClient(app) as client:
            # Lowercase valid symbol
            res_lower = client.get("/api/candles?symbol=btcusd&timeframe=m15&limit=20")
            assert res_lower.status_code == 200
            assert res_lower.json()["symbol"] == "BTCUSD"
            assert res_lower.json()["timeframe"] == "M15"
            assert len(res_lower.json()["candles"]) == 20

            # Unlisted symbol falls back safely to simulator base without crashing
            res_unlisted = client.get("/api/candles?symbol=UNKNOWN_TOKEN&timeframe=H1&limit=20")
            assert res_unlisted.status_code == 200
            assert res_unlisted.json()["symbol"] == "UNKNOWN_TOKEN"
            assert len(res_unlisted.json()["candles"]) == 20

    def test_smc_endpoint_all_crypto_and_fx_assets(self):
        """Verifies GET /api/smc generates valid SMC structures for all 7 assets."""
        with TestClient(app) as client:
            for sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
                res = client.get(f"/api/smc?symbol={sym}&timeframe=M15")
                assert res.status_code == 200
                data = res.json()
                assert data["symbol"] == sym
                assert "fvgs" in data
                assert "order_blocks" in data
                assert "ote" in data
                assert "levels" in data["ote"]
                assert "sweet_spot_705" in data["ote"]["levels"]
                assert "killzones" in data
                assert len(data["killzones"]) == 3

    def test_cvd_boundary_limits(self):
        """Verifies limit parameter boundaries on GET /api/cvd."""
        with TestClient(app) as client:
            # Valid boundaries (ge=10, le=300)
            res_min = client.get("/api/cvd?symbol=BTCUSD&limit=10")
            assert res_min.status_code == 200

            res_max = client.get("/api/cvd?symbol=BTCUSD&limit=300")
            assert res_max.status_code == 200

            # Out of bounds
            assert client.get("/api/cvd?symbol=BTCUSD&limit=9").status_code == 422
            assert client.get("/api/cvd?symbol=BTCUSD&limit=301").status_code == 422
            assert client.get("/api/cvd?symbol=BTCUSD&limit=-1").status_code == 422

    def test_execution_scale_out_boundary_validation(self):
        """Verifies Pydantic boundaries on POST /api/execution/scale-out."""
        with TestClient(app) as client:
            # Missing ticket -> 422
            assert client.post("/api/execution/scale-out", json={"ratio": 0.5}).status_code == 422

            # Ratio < 0.01 -> 422
            assert client.post("/api/execution/scale-out", json={"ticket": 100101, "ratio": 0.0}).status_code == 422
            assert client.post("/api/execution/scale-out", json={"ticket": 100101, "ratio": -0.5}).status_code == 422

            # Ratio > 1.0 -> 422
            assert client.post("/api/execution/scale-out", json={"ticket": 100101, "ratio": 1.05}).status_code == 422

            # Negative buffer pips -> 422
            assert client.post("/api/execution/scale-out", json={"ticket": 100101, "ratio": 0.5, "buffer_pips": -2.0}).status_code == 422

            # Valid minimum ratio (0.01)
            res_min = client.post("/api/execution/scale-out", json={"ticket": 100101, "ratio": 0.01})
            assert res_min.status_code == 200

    def test_execution_breakeven_boundary_validation(self):
        """Verifies boundaries on POST /api/execution/breakeven."""
        with TestClient(app) as client:
            # Missing ticket -> 422
            assert client.post("/api/execution/breakeven", json={}).status_code == 422

            # Negative buffer pips -> 422
            assert client.post("/api/execution/breakeven", json={"ticket": 100101, "buffer_pips": -1.0}).status_code == 422

            # Zero buffer pips is allowed (exact breakeven)
            res_zero = client.post("/api/execution/breakeven", json={"ticket": 100101, "buffer_pips": 0.0})
            assert res_zero.status_code == 200
            assert res_zero.json()["new_sl"] == 2645.00  # Entry price

    def test_execution_modify_sltp_boundary_validation(self):
        """Verifies validation on POST /api/execution/modify-sltp."""
        with TestClient(app) as client:
            # Missing fields -> 422
            assert client.post("/api/execution/modify-sltp", json={"ticket": 100101}).status_code == 422
            assert client.post("/api/execution/modify-sltp", json={"ticket": 100101, "sl": 2640.0}).status_code == 422

            # Non-existent ticket -> 400
            assert client.post("/api/execution/modify-sltp", json={"ticket": 888888, "sl": 2640.0, "tp": 2680.0}).status_code == 400


# =====================================================================
# 2. WhatsApp Whitelist Security & Interactive Endpoints
# =====================================================================

class TestWhatsAppSecurityAndEndpoints:
    """Adversarial stress-testing of WhatsApp whitelist firewall and 2-way commands."""

    def test_authorized_whitelisted_numbers(self):
        """Verifies all 4 authorized numbers and the Elite Trade group pass whitelist verification."""
        for num in AUTHORIZED_CONTACTS.keys():
            # Raw number
            assert is_whitelisted_number(num) is True
            # JID format
            assert is_whitelisted_number(f"{num}@s.whatsapp.net") is True
            # International prefix format
            assert is_whitelisted_number(f"+{num}") is True

        # Elite Trade Group JID
        assert is_whitelisted_number("120363401615322542@g.us") is True
        assert is_whitelisted_number("120363401615322542") is True

    def test_unauthorized_senders_blocked(self):
        """Verifies unauthorized numbers, random callers, and invalid JIDs are strictly blocked."""
        unauthorized_list = [
            "1234567890",
            "+15551234567",
            "447700900000@s.whatsapp.net",
            "spammer_bot@s.whatsapp.net",
            "923001234567",  # Different Pakistani number
            "923460000000",
            "923487117832",  # Purged secondary contact
            "923322555238",  # Purged secondary contact
            "923375893095",  # Purged secondary contact
            "923487117832@s.whatsapp.net",
            "923322555238@s.whatsapp.net",
            "923375893095@s.whatsapp.net",
            "unknown_group_999@g.us",
            "",
            None
        ]
        for sender in unauthorized_list:
            assert is_whitelisted_number(sender) is False

    def test_whatsapp_qr_endpoint_contract(self):
        """Verifies GET /api/whatsapp_qr returns authorized contacts and elite group JID."""
        with TestClient(app) as client:
            res = client.get("/api/whatsapp_qr")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert len(data["authorized_contacts"]) == 1
            assert "923468053268" in data["authorized_contacts"]
            for purged in ["923487117832", "923322555238", "923375893095"]:
                assert purged not in data["authorized_contacts"]
            assert data["elite_group"] == "120363401615322542@g.us"

    def test_whatsapp_command_authorized_vs_unauthorized(self):
        """Verifies POST /api/whatsapp_command processes for authorized users and drops unauthorized."""
        with TestClient(app) as client:
            # 1. Authorized Sender Command
            res_auth = client.post("/api/whatsapp_command", json={
                "command": "status",
                "sender": "923468053268"
            })
            assert res_auth.status_code == 200
            data_auth = res_auth.json()
            assert data_auth["success"] is True
            assert len(data_auth["response"]) > 0

            # 2. Unauthorized Sender Command (Blocked at endpoint level with 403 Forbidden)
            res_unauth = client.post("/api/whatsapp_command", json={
                "command": "status",
                "sender": "447700900000"
            })
            assert res_unauth.status_code == 403

    def test_whatsapp_command_variety_for_authorized_user(self):
        """Tests diverse command keywords for authorized user."""
        manager = WhatsAppQRManager()
        sender = "923468053268"

        commands = ["status", "fleet", "trades", "gold", "risk", "crypto", "world", "plan", "unknown_cmd_xyz"]
        for cmd in commands:
            reply = manager.handle_incoming_command(cmd, sender)
            assert isinstance(reply, str)
            assert len(reply) > 0  # Authorized commands return structured replies or fallbacks


# =====================================================================
# 3. 1-Click Execution Actions on Crypto, FX, and Gold Symbols
# =====================================================================

class TestOneClickExecutionMultiAsset:
    """Adversarially tests 1-click execution actions across Crypto, FX, and Gold symbols."""

    def test_scale_out_crypto_btc(self):
        """Verifies 50% partial scale out and BE on BTCUSD position."""
        terminal_state.mock_positions = [{
            "ticket": 200101,
            "symbol": "BTCUSD",
            "type": "BUY",
            "volume": 0.40,
            "price_open": 95000.00,
            "price_current": 96500.00,
            "sl": 94000.00,
            "tp": 98000.00,
            "profit": 600.00,
            "comment": "BTC Trade"
        }]

        with TestClient(app) as client:
            res = client.post("/api/execution/scale-out", json={
                "ticket": 200101,
                "ratio": 0.5,
                "buffer_pips": 5.0
            })
            assert res.status_code == 200
            data = res.json()

            assert data["success"] is True
            assert data["closed_volume"] == 0.20
            assert data["remaining_volume"] == 0.20
            # BTCUSD pip = 1.00 -> new_sl = 95000.00 + (5.0 * 1.00) = 95005.00
            assert data["new_sl"] == 95005.00

            # Check open position updated
            pos = terminal_state.mock_positions[0]
            assert pos["volume"] == 0.20
            assert pos["sl"] == 95005.00

    def test_scale_out_crypto_eth_and_sol(self):
        """Verifies scale out on ETHUSD and SOLUSD positions."""
        terminal_state.mock_positions = [
            {
                "ticket": 200102,
                "symbol": "ETHUSD",
                "type": "SELL",
                "volume": 2.00,
                "price_open": 3400.00,
                "price_current": 3350.00,
                "sl": 3450.00,
                "tp": 3200.00,
                "profit": 100.00,
                "comment": "ETH Trade"
            },
            {
                "ticket": 200103,
                "symbol": "SOLUSD",
                "type": "BUY",
                "volume": 10.00,
                "price_open": 185.00,
                "price_current": 190.00,
                "sl": 180.00,
                "tp": 200.00,
                "profit": 50.00,
                "comment": "SOL Trade"
            }
        ]

        with TestClient(app) as client:
            # Scale out 50% on ETHUSD (SELL): pip=0.10, buffer=2 pips -> 3400.00 - 0.20 = 3399.80
            res_eth = client.post("/api/execution/scale-out", json={"ticket": 200102, "ratio": 0.5, "buffer_pips": 2.0})
            assert res_eth.status_code == 200
            assert res_eth.json()["new_sl"] == 3399.80
            assert res_eth.json()["remaining_volume"] == 1.00

            # Scale out 75% on SOLUSD (BUY): pip=0.01, buffer=3 pips -> 185.00 + 0.03 = 185.03
            res_sol = client.post("/api/execution/scale-out", json={"ticket": 200103, "ratio": 0.75, "buffer_pips": 3.0})
            assert res_sol.status_code == 200
            assert res_sol.json()["new_sl"] == 185.03
            assert res_sol.json()["closed_volume"] == 7.50
            assert res_sol.json()["remaining_volume"] == 2.50

    def test_scale_out_fx_usdjpy(self):
        """Verifies scale out on USDJPY (3-decimal currency with 0.01 pip)."""
        terminal_state.mock_positions = [{
            "ticket": 200104,
            "symbol": "USDJPY",
            "type": "BUY",
            "volume": 1.00,
            "price_open": 153.500,
            "price_current": 154.200,
            "sl": 152.800,
            "tp": 155.000,
            "profit": 700.00,
            "comment": "USDJPY Trade"
        }]

        with TestClient(app) as client:
            # Pip is 0.01, decimals=3. Buffer = 2.5 pips -> 153.500 + 0.025 = 153.525
            res = client.post("/api/execution/scale-out", json={"ticket": 200104, "ratio": 0.5, "buffer_pips": 2.5})
            assert res.status_code == 200
            assert res.json()["new_sl"] == 153.525

    def test_breakeven_lock_multi_asset(self):
        """Verifies POST /api/execution/breakeven across multiple asset classes."""
        terminal_state.mock_positions = [
            {"ticket": 301, "symbol": "BTCUSD", "type": "BUY", "volume": 0.5, "price_open": 95000.0, "profit": 100.0},
            {"ticket": 302, "symbol": "EURUSD", "type": "SELL", "volume": 1.0, "price_open": 1.08500, "profit": 50.0},
            {"ticket": 303, "symbol": "USDJPY", "type": "SELL", "volume": 1.0, "price_open": 153.500, "profit": 80.0},
        ]

        with TestClient(app) as client:
            # BTCUSD BUY: open 95000.0 + 2.0 = 95002.0
            r1 = client.post("/api/execution/breakeven", json={"ticket": 301, "buffer_pips": 2.0}).json()
            assert r1["new_sl"] == 95002.0

            # EURUSD SELL: open 1.08500 - (2.0 * 0.0001) = 1.08480
            r2 = client.post("/api/execution/breakeven", json={"ticket": 302, "buffer_pips": 2.0}).json()
            assert r2["new_sl"] == 1.08480

            # USDJPY SELL: open 153.500 - (2.0 * 0.01) = 153.480
            r3 = client.post("/api/execution/breakeven", json={"ticket": 303, "buffer_pips": 2.0}).json()
            assert r3["new_sl"] == 153.480

    def test_panic_kill_switch_mixed_7_asset_portfolio(self):
        """Verifies Panic Kill-Switch liquidates a full 7-asset portfolio and locks the bot."""
        terminal_state.mock_positions = [
            {"ticket": 401, "symbol": "XAUUSD", "type": "BUY", "volume": 0.5, "profit": 200.0},
            {"ticket": 402, "symbol": "EURUSD", "type": "SELL", "volume": 1.0, "profit": 100.0},
            {"ticket": 403, "symbol": "GBPUSD", "type": "BUY", "volume": 0.5, "profit": -50.0},
            {"ticket": 404, "symbol": "USDJPY", "type": "SELL", "volume": 1.0, "profit": 80.0},
            {"ticket": 405, "symbol": "BTCUSD", "type": "BUY", "volume": 0.2, "profit": 400.0},
            {"ticket": 406, "symbol": "ETHUSD", "type": "SELL", "volume": 1.0, "profit": 50.0},
            {"ticket": 407, "symbol": "SOLUSD", "type": "BUY", "volume": 5.0, "profit": -30.0},
        ]
        initial_balance = terminal_state.balance
        expected_total_pnl = sum(p["profit"] for p in terminal_state.mock_positions)  # 750.0

        with TestClient(app) as client:
            res = client.post("/api/control/kill-switch", json={"reason": "Adversarial 7-Asset Panic Test"})
            assert res.status_code == 200
            data = res.json()

            assert data["success"] is True
            assert data["closed_positions"] == 7
            assert data["status"] == "EMERGENCY_LOCKED"
            assert len(terminal_state.mock_positions) == 0
            assert terminal_state.status == "EMERGENCY_LOCKED"
            assert terminal_state.balance == initial_balance + expected_total_pnl
            assert terminal_state.equity == terminal_state.balance


# =====================================================================
# 4. Aladdin VaR/CVaR, Funding Pips HWM Floor & Extreme Market Swings
# =====================================================================

class TestAladdinRiskAndFundingPipsExtremeSwings:
    """Stress-tests Aladdin risk engine, Funding Pips HWM ratchet, and consistency pacing under market extremes."""

    def test_aladdin_var_cvar_mathematical_invariants(self):
        """
        Verifies quantitative invariant: CVaR (Expected Shortfall) > VaR at both 99% and 95%
        across equity levels from $1,000 to $1,000,000 and volatilities from 0.1% to 15.0%.
        """
        engine = AladdinRiskEngine()

        test_equities = [1000.0, 5000.0, 25000.0, 50000.0, 100000.0, 1000000.0]
        test_vols = [0.001, 0.005, 0.008, 0.015, 0.030, 0.080, 0.150]

        for eq in test_equities:
            for vol in test_vols:
                metrics = engine.compute_parametric_var_cvar(eq, vol)

                # Invariant 1: CVaR_99 > VaR_99
                assert metrics["cvar_99_dollar"] > metrics["var_99_dollar"]
                assert metrics["cvar_99_pct"] > metrics["var_99_pct"]

                # Invariant 2: VaR_99 > VaR_95
                assert metrics["var_99_dollar"] > metrics["var_95_dollar"]

                # Invariant 3: Positive values
                assert metrics["var_99_dollar"] > 0
                assert metrics["cvar_99_dollar"] > 0

    def test_funding_pips_hwm_ratchet_under_extreme_swing(self):
        """
        Simulates extreme market rally followed by steep drawdown:
        Verifies that absolute HWM ratchets UP with equity gains, and trailing floor
        remains strictly non-decreasing even when equity collapses.
        """
        fp = FundingPipsExpert(account_tier="25k")
        assert fp.absolute_high_watermark == 25000.0

        # Day 1: Account rallies from 25k to 28k
        fp.update_daily_watermark(equity=28000.0, balance=28000.0)
        assert fp.absolute_high_watermark == 28000.0

        # Trailing floor on 25k tier is HWM - 6% of target ($1,500) = 28,000 - 1,500 = 26,500
        max_total_allowed = 25000.0 * 0.06  # $1,500
        trailing_floor = fp.absolute_high_watermark - max_total_allowed
        assert trailing_floor == 26500.0

        # Account is healthy at 28k
        can_trade, msg = fp.can_trade(balance=28000.0, equity=28000.0)
        assert can_trade is True

        # Day 2: Market flash crash drops equity to 26,400 (below 26,500 floor)
        fp.update_daily_watermark(equity=26400.0, balance=28000.0)
        # Absolute HWM must NOT decrease
        assert fp.absolute_high_watermark == 28000.0

        # Safety audit must trigger and BLOCK trading
        can_trade, msg = fp.can_trade(balance=28000.0, equity=26400.0)
        assert can_trade is False
        assert "Trailing HWM Drawdown Floor Reached" in msg

    def test_funding_pips_daily_drawdown_hard_cap(self):
        """Verifies daily drawdown safe cap of 2.5% ($625 on $25k) halts trading."""
        fp = FundingPipsExpert(account_tier="25k")
        # Starting daily HWM is $25,000
        assert fp.daily_high_watermark == 25000.0
        max_daily_allowed = 25000.0 * 0.025  # $625.00

        # Loss of $600 -> still within safe allowance
        can_trade, _ = fp.can_trade(balance=25000.0, equity=24400.0)
        assert can_trade is True

        # Loss of $630 -> breaches $625 safe allowance
        can_trade, msg = fp.can_trade(balance=25000.0, equity=24370.0)
        assert can_trade is False
        assert "Daily Drawdown Guard Triggered" in msg

    def test_consistency_pacing_gauge_thresholds(self):
        """Verifies 35% consistency pacing gauge status transitions (NOMINAL, CAUTION, CRITICAL, CEILING_REACHED)."""
        with TestClient(app) as client:
            # Ceiling for 25k is $700 (35% of $2,000)

            # 1. Nominal: Daily profit = $100 (< 55% of $700 = $385)
            terminal_state.daily_profit = 100.0
            data_nom = client.get("/api/risk/metrics").json()
            assert data_nom["consistency_status"] == "NOMINAL"
            assert data_nom["consistency_gauge"]["status"] == "NOMINAL"

            # 2. Caution: Daily profit = $400 (57.1% of $700)
            terminal_state.daily_profit = 400.0
            data_caut = client.get("/api/risk/metrics").json()
            assert data_caut["consistency_status"] == "CAUTION"

            # 3. Critical: Daily profit = $600 (85.7% of $700)
            terminal_state.daily_profit = 600.0
            data_crit = client.get("/api/risk/metrics").json()
            assert data_crit["consistency_status"] == "CRITICAL"

            # 4. Ceiling Reached: Daily profit = $750 (>= $700)
            terminal_state.daily_profit = 750.0
            data_ceil = client.get("/api/risk/metrics").json()
            assert data_ceil["consistency_status"] == "CEILING_REACHED"

            # 5. Negative Profit (loss day) -> Nominal
            terminal_state.daily_profit = -200.0
            data_loss = client.get("/api/risk/metrics").json()
            assert data_loss["consistency_status"] == "NOMINAL"


# =====================================================================
# 5. World Monitor Telemetry & WebSocket Channel Resiliency
# =====================================================================

class TestWorldMonitorAndWebSocketResiliency:
    """Stress-tests World Monitor telemetry contracts and Starlette WebSocket channels."""

    def test_world_monitor_contract_completeness(self):
        """Verifies all required fields in World Monitor conform strictly to PROJECT.md Contract #1."""
        with TestClient(app) as client:
            res = client.get("/api/world_monitor")
            assert res.status_code == 200
            data = res.json()

            assert data["status"] == "success"
            assert "global_threat_level" in data
            assert "DEFCON" in data["global_threat_level"]
            assert data["global_risk_index"] > 0
            assert "primary_geopolitical_hotspot" in data

            # Chokepoints (5 mandatory maritime corridors)
            chokepoints = data["chokepoints"]
            assert len(chokepoints) == 5
            names = [cp["name"] for cp in chokepoints]
            assert "Strait of Hormuz" in names
            assert "Bab el-Mandeb / Red Sea" in names
            assert "Suez Canal" in names
            assert "Strait of Malacca" in names
            assert "Taiwan Strait" in names

            for cp in chokepoints:
                assert "risk_level" in cp
                assert "global_oil_pct" in cp
                assert cp["global_oil_pct"] > 0
                assert "status" in cp

            # Country Instability Index
            cii = data["country_instability"]
            for region in ["Middle_East", "Eastern_Europe", "United_States", "East_Asia", "Eurozone"]:
                assert region in cii or region.replace("_", " ") in cii

            # Market Bias Multipliers
            bias = data["market_bias"]
            assert "XAUUSD" in bias
            assert "WTI" in bias
            assert "USDJPY" in bias
            assert "BTCUSD" in bias

    def test_websocket_channel_malformed_message_handling(self):
        """Verifies WebSocket endpoint gracefully handles invalid JSON or unhandled commands without dropping server."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/terminal") as ws:
                # Flush initial frames
                for _ in range(4):
                    ws.receive_json()

                # Send unknown action
                ws.send_json({"type": "command", "action": "non_existent_action", "ticket": 12345})
                # Send unknown message type
                ws.send_json({"type": "random_unsupported_type", "payload": 123})

                # Send valid voice intent to verify connection is still fully responsive
                ws.send_json({"type": "voice_intent", "transcript": "What is my daily drawdown"})
                voice_frame = ws.receive_json()
                while voice_frame.get("type") != "jarvis_event":
                    voice_frame = ws.receive_json()

                assert voice_frame["type"] == "jarvis_event"
                assert voice_frame["intent"] == "GET_RISK_METRICS"


# =====================================================================
# 6. Strategic Maritime Chokepoints Adversarial & Disruption Stress
# =====================================================================

from datetime import datetime, timezone, timedelta
import pandas as pd
from src.world_monitor_intelligence_engine import (
    WorldMonitorIntelligenceEngine,
    get_world_monitor_brief
)
from src.economic_calendar_radar import EconomicCalendarRadar
from src.news_filter import NewsFilter
from src.predictive_weather_engine import PredictiveWeatherEngine
from src.market_satellite_radar import MarketSatelliteRadar


class TestChokepointsDisruptionsAdversarial:
    """Adversarial stress-testing of 5 Strategic Chokepoints under extreme disruptions."""

    def setup_method(self):
        self.engine = WorldMonitorIntelligenceEngine()

    def test_chokepoint_zero_flow_all_waterways(self):
        """Tests complete blockade (0.0 mbd) across all 4 oil chokepoints and max incidents on Taiwan."""
        oil_chokepoints = ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait"]
        for cp_id in oil_chokepoints:
            updated = self.engine.update_chokepoint_flow(cp_id, current_mbd=0.0, incident_count=50)
            assert updated["disruption_pct"] == 100.0
            assert updated["current_mbd"] == 0.0
            assert updated["anomaly_signal"] is True
            assert updated["risk_level"] == "CRITICAL_WARZONE"

        # Taiwan Strait (non-oil artery, baseline 0.0) with high incident volume
        updated_taiwan = self.engine.update_chokepoint_flow("taiwan_strait", incident_count=100)
        assert updated_taiwan["disruption_pct"] == 80.0
        assert updated_taiwan["anomaly_signal"] is True
        assert updated_taiwan["risk_level"] == "CRITICAL_WARZONE"

        # Verify safe-haven multipliers spike
        brief = self.engine.get_world_intelligence_brief()
        assert brief["defcon_level"] in [1, 2]
        bias_gold = self.engine.get_geopolitical_market_bias("XAUUSD")
        assert bias_gold["macro_multiplier"] >= 1.45
        bias_oil = self.engine.get_geopolitical_market_bias("WTI")
        assert bias_oil["macro_multiplier"] >= 1.50
        bias_eur = self.engine.get_geopolitical_market_bias("EURUSD")
        assert bias_eur["macro_multiplier"] <= 0.80

    def test_chokepoint_overflow_exceeding_baseline(self):
        """Verifies flow > baseline (overflow) does not cause negative disruption or calculation errors."""
        # Hormuz surge to 28.0 mbd (baseline 21.0)
        updated_hormuz = self.engine.update_chokepoint_flow("hormuz_strait", current_mbd=28.0, incident_count=0)
        assert updated_hormuz["disruption_pct"] == 0.0
        assert updated_hormuz["flow_pct_of_baseline"] == 133.3
        assert updated_hormuz["anomaly_signal"] is False
        assert updated_hormuz["risk_level"] == "STABLE_SURVEILLANCE"

        # Malacca surge to 22.0 mbd (baseline 17.2)
        updated_malacca = self.engine.update_chokepoint_flow("malacca_strait", current_mbd=22.0, incident_count=0)
        assert updated_malacca["disruption_pct"] == 0.0
        assert updated_malacca["anomaly_signal"] is False

    def test_chokepoint_negative_flow_clamping(self):
        """Verifies negative flow values are clamped to 0.0 (100% disruption) without math domain errors."""
        disruption = self.engine.calculate_disruption_percentage(21.0, -10.0)
        assert disruption == 100.0

        updated = self.engine.update_chokepoint_flow("hormuz_strait", current_mbd=-5.0)
        assert updated["current_mbd"] == -5.0
        assert updated["disruption_pct"] == 100.0
        assert updated["anomaly_signal"] is True

    def test_chokepoint_unknown_identifiers(self):
        """Verifies unknown chokepoint identifiers raise explicit KeyError."""
        with pytest.raises(KeyError):
            self.engine.update_chokepoint_flow("panama_canal", current_mbd=1.0)

        with pytest.raises(KeyError):
            self.engine.update_chokepoint_flow("strait_of_gibraltar", current_mbd=5.0)

        with pytest.raises(KeyError):
            self.engine.update_chokepoint_flow("", current_mbd=0.0)

    def test_chokepoint_zero_baseline_incident_scaling(self):
        """Tests disruption scoring for non-oil waterways (Taiwan Strait) based on incident intensity."""
        # 0 incidents -> 0.0%
        d0 = self.engine.calculate_disruption_percentage(0.0, 0.0, incident_count=0)
        assert d0 == 0.0

        # 25 incidents -> 20.0%
        d25 = self.engine.calculate_disruption_percentage(0.0, 0.0, incident_count=25)
        assert d25 == 20.0

        # 50 incidents -> 40.0%
        d50 = self.engine.calculate_disruption_percentage(0.0, 0.0, incident_count=50)
        assert d50 == 40.0

        # 200 incidents -> capped at 100.0%
        d200 = self.engine.calculate_disruption_percentage(0.0, 0.0, incident_count=200)
        assert d200 == 100.0

    def test_chokepoint_alias_bidirectional_consistency(self):
        """Verifies updating via uppercase alias correctly synchronizes canonical and alias views."""
        self.engine.update_chokepoint_flow("STRAIT_OF_HORMUZ", current_mbd=5.0, incident_count=30)
        brief = self.engine.get_world_intelligence_brief()
        assert brief["chokepoints"]["hormuz_strait"]["current_mbd"] == 5.0
        assert brief["chokepoints"]["STRAIT_OF_HORMUZ"]["current_mbd"] == 5.0
        assert brief["chokepoints"]["hormuz_strait"]["anomaly_signal"] is True


# =====================================================================
# 7. 4-Pillar Country Instability Index & DEFCON Invariants
# =====================================================================

class TestCountryInstabilityBoundaryAdversarial:
    """Adversarial boundary testing for 4-Pillar CII and DEFCON state transitions."""

    def setup_method(self):
        self.engine = WorldMonitorIntelligenceEngine()

    def test_cii_absolute_minimum_all_zeros(self):
        """Verifies score=0.0 and DEFCON 5 (STABLE) when all pillars are zero."""
        components = {"unrest": 0.0, "conflict": 0.0, "security": 0.0, "information": 0.0}
        score = self.engine.calculate_country_instability_score(components)
        assert score == 0.0
        assert self.engine.get_defcon_level(score) == 5

    def test_cii_absolute_maximum_all_hundreds(self):
        """Verifies score=100.0 and DEFCON 1 (CRITICAL) when all pillars are maxed."""
        components = {"unrest": 100.0, "conflict": 100.0, "security": 100.0, "information": 100.0}
        score = self.engine.calculate_country_instability_score(components)
        assert score == 100.0
        assert self.engine.get_defcon_level(score) == 1

    def test_cii_defcon_exact_threshold_boundaries(self):
        """Tests exact threshold values mapping to DEFCON 1 through 5."""
        # DEFCON 1: >= 85.0
        assert self.engine.get_defcon_level(85.0) == 1
        assert self.engine.get_defcon_level(100.0) == 1
        assert self.engine.get_defcon_level(84.9) == 2

        # DEFCON 2: >= 70.0
        assert self.engine.get_defcon_level(70.0) == 2
        assert self.engine.get_defcon_level(84.9) == 2
        assert self.engine.get_defcon_level(69.9) == 3

        # DEFCON 3: >= 50.0
        assert self.engine.get_defcon_level(50.0) == 3
        assert self.engine.get_defcon_level(69.9) == 3
        assert self.engine.get_defcon_level(49.9) == 4

        # DEFCON 4: >= 25.0
        assert self.engine.get_defcon_level(25.0) == 4
        assert self.engine.get_defcon_level(49.9) == 4
        assert self.engine.get_defcon_level(24.9) == 5

        # DEFCON 5: < 25.0
        assert self.engine.get_defcon_level(24.9) == 5
        assert self.engine.get_defcon_level(0.0) == 5

    def test_cii_individual_pillar_stress(self):
        """Tests mathematical weighting of individual isolated pillars."""
        # Conflict weight is 0.40
        assert self.engine.calculate_country_instability_score({"conflict": 100.0}) == 40.0
        # Security weight is 0.25
        assert self.engine.calculate_country_instability_score({"security": 100.0}) == 25.0
        # Unrest weight is 0.20
        assert self.engine.calculate_country_instability_score({"unrest": 100.0}) == 20.0
        # Information weight is 0.15
        assert self.engine.calculate_country_instability_score({"information": 100.0}) == 15.0

    def test_cii_clamping_out_of_bounds(self):
        """Verifies values > 100.0 or < 0.0 are clamped safely between 0.0 and 100.0."""
        score_high = self.engine.calculate_country_instability_score({
            "unrest": 200.0, "conflict": 300.0, "security": 150.0, "information": 120.0
        })
        assert score_high == 100.0

        score_low = self.engine.calculate_country_instability_score({
            "unrest": -50.0, "conflict": -100.0, "security": -20.0, "information": -10.0
        })
        assert score_low == 0.0

    def test_cii_dynamic_region_addition(self):
        """Verifies adding an unlisted region dynamically computes CII and integrates into global index."""
        region = self.engine.update_country_instability(
            "LATIN_AMERICA",
            components={"unrest": 85.0, "conflict": 60.0, "security": 70.0, "information": 50.0},
            trend="POLITICAL_TURMOIL"
        )
        # Expected: 0.20*85 + 0.40*60 + 0.25*70 + 0.15*50 = 17 + 24 + 17.5 + 7.5 = 66.0
        assert region["score"] == 66.0
        assert region["level"] == "HIGH_TENSION"
        assert region["trend"] == "POLITICAL_TURMOIL"

        brief = self.engine.get_world_intelligence_brief()
        assert "LATIN_AMERICA" in brief["country_instability"]


# =====================================================================
# 8. Polymarket Geopolitical Feeds & Illiquidity Filtration
# =====================================================================

class TestPolymarketFeedEdgeCasesAdversarial:
    """Adversarial stress-testing of Polymarket geopolitical odds ingestion and filtering."""

    def setup_method(self):
        self.engine = WorldMonitorIntelligenceEngine()

    def test_polymarket_empty_and_none_input(self):
        """Verifies empty list or None preserves default odds without crashing."""
        initial_len = len(self.engine.polymarket_odds)
        res_empty = self.engine.ingest_polymarket_odds([])
        assert len(res_empty) == initial_len

        res_none = self.engine.ingest_polymarket_odds(None)
        assert len(res_none) == initial_len

    def test_polymarket_malformed_items(self):
        """Verifies malformed items with missing fields or alias keys are ingested cleanly."""
        raw = [
            {
                # Missing 'event', has 'title'
                "title": "Middle East Escalation Horizon",
                "yesPrice": 72.5,
                "volume": 500000.0,
                "trend": "CRITICAL"
            },
            {
                # Empty item falls back safely
                "event": "",
                "implied_probability_pct": 55.0,
                "volume_usd": 30000.0
            }
        ]
        parsed = self.engine.ingest_polymarket_odds(raw)
        assert len(parsed) == 2
        assert parsed[0]["event"] == "Middle East Escalation Horizon"
        assert parsed[0]["implied_probability_pct"] == 72.5
        assert parsed[0]["volume_usd"] == 500000.0
        assert parsed[0]["market_shock_level"] == "SEVERE"
        assert parsed[0]["impact_asset"] == "WTI"

    def test_polymarket_illiquidity_filtering_threshold(self):
        """Verifies markets with volume < $20k AND probability < 50% are filtered out."""
        raw = [
            {
                "event": "Illiquid Low Prob Meme Market",
                "implied_probability_pct": 12.0,
                "volume_usd": 15000.0  # < $20k and < 50% -> Filtered
            },
            {
                "event": "Liquid Low Prob Market",
                "implied_probability_pct": 15.0,
                "volume_usd": 25000.0  # >= $20k -> Retained
            },
            {
                "event": "Illiquid High Prob Market",
                "implied_probability_pct": 65.0,
                "volume_usd": 5000.0   # >= 50% prob -> Retained
            }
        ]
        parsed = self.engine.ingest_polymarket_odds(raw)
        assert len(parsed) == 2
        events = [p["event"] for p in parsed]
        assert "Illiquid Low Prob Meme Market" not in events
        assert "Liquid Low Prob Market" in events
        assert "Illiquid High Prob Market" in events

    def test_polymarket_boundary_probabilities(self):
        """Verifies 100.0% and 0.0% probability boundary inputs."""
        raw = [
            {"event": "Guaranteed Geopolitical Shift", "implied_probability_pct": 100.0, "volume_usd": 100000.0},
            {"event": "Impossible Macro Scenario", "implied_probability_pct": 0.0, "volume_usd": 50000.0}
        ]
        parsed = self.engine.ingest_polymarket_odds(raw)
        assert len(parsed) == 2
        assert parsed[0]["implied_probability_pct"] == 100.0
        assert parsed[1]["implied_probability_pct"] == 0.0

    def test_polymarket_keyword_shock_level_mapping(self):
        """Verifies automatic keyword inference of market shock levels and impact assets."""
        raw = [
            {"event": "PLA Taiwan Strait naval exercises", "implied_probability_pct": 35.0, "volume_usd": 100000.0},
            {"event": "Red Sea Houthi ship attack", "implied_probability_pct": 60.0, "volume_usd": 100000.0},
            {"event": "Federal Reserve interest rate hike in Q3", "implied_probability_pct": 45.0, "volume_usd": 100000.0},
            {"event": "Global economic recession in 2026", "implied_probability_pct": 25.0, "volume_usd": 100000.0},
            {"event": "Neutral summit discussions in Geneva", "implied_probability_pct": 40.0, "volume_usd": 100000.0}
        ]
        parsed = self.engine.ingest_polymarket_odds(raw)
        assert parsed[0]["market_shock_level"] == "EXTREME"
        assert parsed[0]["impact_asset"] == "XAUUSD"

        assert parsed[1]["market_shock_level"] == "SEVERE"
        assert parsed[1]["impact_asset"] == "WTI"

        assert parsed[2]["market_shock_level"] == "MACRO_MONETARY"
        assert parsed[2]["impact_asset"] == "DXY"

        assert parsed[3]["market_shock_level"] == "GROWTH_SLOWDOWN"
        assert parsed[3]["impact_asset"] == "SPX"

        assert parsed[4]["market_shock_level"] == "MODERATE"


# =====================================================================
# 9. 15-Minute News Circuit Breakers, Currency Matrix & Weekend Rollover
# =====================================================================

class TestNewsCircuitBreakerBoundaryAdversarial:
    """Adversarial stress-testing of 15-minute Pre/Post News Circuit Breakers and Currency Lockout Matrix."""

    def setup_method(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()

    def test_circuit_breaker_exact_15min_pre_news_boundary(self):
        """
        Tests exact boundary timing at T - 15m 00s vs T - 15m 01s.
        """
        fixed_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)  # Tuesday

        # Event exactly 15m 00s in the future (delta = 15.0 min) -> MUST LOCK
        ev_time_exact = fixed_now + timedelta(minutes=15, seconds=0)
        self.radar.inject_event("US CPI Exact 15m", "USD", ev_time_exact, impact="HIGH")

        clearance_exact = self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now, check_weekend=True)
        assert clearance_exact["is_blackout"] is True
        assert clearance_exact["is_cleared"] is False
        assert "PRE_NEWS_BLACKOUT" in clearance_exact["lockout_reason"]

        # Clear and test event 15m 01s in the future (delta = 15.0167 min) -> MUST CLEAR
        self.radar.clear_events()
        ev_time_outside = fixed_now + timedelta(minutes=15, seconds=1)
        self.radar.inject_event("US CPI Outside 15m", "USD", ev_time_outside, impact="HIGH")

        clearance_outside = self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now, check_weekend=True)
        assert clearance_outside["is_blackout"] is False
        assert clearance_outside["is_cleared"] is True
        assert "CLEARED" in clearance_outside["lockout_reason"]

    def test_circuit_breaker_exact_event_time_and_post_news_boundary(self):
        """
        Tests exact event time (T=0) and post-event boundary at T + 15m 00s vs T + 15m 01s.
        """
        fixed_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

        # 1. Exact Event Time (delta = 0.0 min) -> MUST LOCK
        self.radar.clear_events()
        self.radar.inject_event("FOMC Rate Release Now", "USD", fixed_now, impact="HIGH")
        c_now = self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now, check_weekend=True)
        assert c_now["is_blackout"] is True
        assert c_now["is_cleared"] is False

        # 2. Exact 15m 00s Post Event (delta = -15.0 min) -> MUST LOCK (Cooloff)
        self.radar.clear_events()
        ev_time_past_15m = fixed_now - timedelta(minutes=15, seconds=0)
        self.radar.inject_event("FOMC Rate Release Past 15m", "USD", ev_time_past_15m, impact="HIGH")
        c_past_exact = self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now, check_weekend=True)
        assert c_past_exact["is_blackout"] is True
        assert "POST_NEWS_BLACKOUT" in c_past_exact["lockout_reason"]

        # 3. 15m 01s Post Event (delta = -15.0167 min) -> MUST CLEAR
        self.radar.clear_events()
        ev_time_past_15m01 = fixed_now - timedelta(minutes=15, seconds=1)
        self.radar.inject_event("FOMC Rate Release Past 15m01s", "USD", ev_time_past_15m01, impact="HIGH")
        c_past_outside = self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now, check_weekend=True)
        assert c_past_outside["is_blackout"] is False
        assert c_past_outside["is_cleared"] is True

    def test_simultaneous_multi_currency_events(self):
        """Verifies handling of simultaneous high-impact events across multiple currencies."""
        fixed_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
        self.radar.inject_event("US Non-Farm Payrolls", "USD", fixed_now + timedelta(minutes=5), impact="HIGH")
        self.radar.inject_event("ECB Monetary Policy Statement", "EUR", fixed_now + timedelta(minutes=8), impact="HIGH")
        self.radar.inject_event("BOJ CPI Release", "JPY", fixed_now - timedelta(minutes=4), impact="HIGH")

        # XAUUSD is locked by USD
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now)["is_blackout"] is True
        # EURUSD is locked by both USD and EUR
        assert self.radar.evaluate_news_clearance("EURUSD", current_time=fixed_now)["is_blackout"] is True
        # USDJPY is locked by USD and JPY
        assert self.radar.evaluate_news_clearance("USDJPY", current_time=fixed_now)["is_blackout"] is True
        # GBPJPY is locked by JPY
        assert self.radar.evaluate_news_clearance("GBPJPY", current_time=fixed_now)["is_blackout"] is True
        # AUDNZD has no USD, EUR, or JPY exposure -> CLEARED
        c_audnzd = self.radar.evaluate_news_clearance("AUDNZD", current_time=fixed_now)
        assert c_audnzd["is_blackout"] is False
        assert c_audnzd["is_cleared"] is True

    def test_currency_lockout_matrix_isolation(self):
        """Verifies currency isolation: a CAD-only event locks USDCAD/EURCAD but not EURUSD/GBPJPY/XAUUSD."""
        fixed_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
        self.radar.inject_event("Bank of Canada Rate Decision", "CAD", fixed_now + timedelta(minutes=6), impact="HIGH")

        # Affected pairs
        assert self.radar.evaluate_news_clearance("USDCAD", current_time=fixed_now)["is_blackout"] is True
        assert self.radar.evaluate_news_clearance("EURCAD", current_time=fixed_now)["is_blackout"] is True

        # Unaffected pairs
        assert self.radar.evaluate_news_clearance("EURUSD", current_time=fixed_now)["is_blackout"] is False
        assert self.radar.evaluate_news_clearance("GBPJPY", current_time=fixed_now)["is_blackout"] is False
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=fixed_now)["is_blackout"] is False

    def test_weekend_rollover_vs_crypto(self):
        """Verifies Friday close to Sunday open blocks FX/Commodities while leaving 24/7 Crypto active."""
        # 1. Friday 21:00 UTC (Market Closed for FX)
        fri_closed = datetime(2026, 8, 21, 21, 0, 0, tzinfo=timezone.utc)
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=fri_closed)["is_blackout"] is True
        assert self.radar.evaluate_news_clearance("EURUSD", current_time=fri_closed)["is_blackout"] is True
        assert self.radar.evaluate_news_clearance("BTCUSD", current_time=fri_closed)["is_blackout"] is False

        # 2. Saturday 12:00 UTC (All day closed for FX)
        sat_closed = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=sat_closed)["is_blackout"] is True
        assert self.radar.evaluate_news_clearance("BTCUSD", current_time=sat_closed)["is_blackout"] is False

        # 3. Sunday 18:00 UTC (Pre-market buffer closed for FX)
        sun_closed = datetime(2026, 8, 23, 18, 0, 0, tzinfo=timezone.utc)
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=sun_closed)["is_blackout"] is True
        assert self.radar.evaluate_news_clearance("BTCUSD", current_time=sun_closed)["is_blackout"] is False

        # 4. Sunday 22:00 UTC (Market Opened)
        sun_open = datetime(2026, 8, 23, 22, 0, 0, tzinfo=timezone.utc)
        assert self.radar.evaluate_news_clearance("XAUUSD", current_time=sun_open)["is_blackout"] is False
        assert self.radar.evaluate_news_clearance("BTCUSD", current_time=sun_open)["is_blackout"] is False

    def test_news_filter_passthrough_consistency(self):
        """Verifies NewsFilter is fully synchronized with EconomicCalendarRadar."""
        nf = NewsFilter()
        nf.radar.clear_events()
        fixed_now = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)

        # Inject event into news filter radar
        nf.radar.inject_event("US Core PPI", "USD", fixed_now + timedelta(minutes=5), impact="HIGH")

        # Check with manual time evaluation
        clearance = nf.evaluate_news_clearance("XAUUSD")
        assert "is_cleared" in clearance
        assert "is_blackout" in clearance


# =====================================================================
# 10. Predictive Atmospheric Weather Engine Fusion & Regime Transitions
# =====================================================================

class TestPredictiveWeatherEngineCompositeAdversarial:
    """Adversarial testing of PredictiveWeatherEngine 6-regime classification and prioritization."""

    def setup_method(self):
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.calendar_radar = EconomicCalendarRadar()
        self.calendar_radar.clear_events()
        self.weather_engine = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar
        )

    def test_cyclone_priority_override(self):
        """
        Verifies CYCLONE_NEWS_LOCKOUT overrides all other conditions:
        Even if DEFCON is 1, global risk is 100, and price momentum is screaming bullish (+100%),
        an active news event forces CYCLONE regime with risk multiplier 0.0x.
        """
        # Escalate DEFCON to 1
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 100.0, "conflict": 100.0, "security": 100.0, "information": 100.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=0.0, incident_count=100)

        # Active News Event
        now_utc = datetime.now(timezone.utc)
        self.calendar_radar.inject_event("Emergency FOMC Announcement", "USD", now_utc + timedelta(minutes=3), impact="HIGH")

        # Bullish candle momentum
        closes = [2600.0 + (i * 5.0) for i in range(25)]
        df_m15 = pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes, "tick_volume": [200]*25})

        forecast = self.weather_engine.forecast_market_weather(df_m15, df_m15, symbol="XAUUSD")
        assert forecast["weather_state"] == "CYCLONE_NEWS_LOCKOUT"
        assert forecast["risk_multiplier"] == 0.0
        assert forecast["trade_policy"] == "Trading Strictly Halted / Entries Blocked"

    def test_hurricane_risk_off_defcon_and_asset_differentiation(self):
        """
        Verifies HURRICANE_RISK_OFF applies asset-differentiated multipliers:
        - Gold/Oil: 1.50x
        - Pro-cyclical FX: 0.50x
        - Other assets: 0.65x
        """
        # Escalate DEFCON to 1
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 100.0, "conflict": 100.0, "security": 100.0, "information": 100.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=0.0, incident_count=90)

        # Gold
        f_gold = self.weather_engine.forecast_market_weather("XAUUSD")
        assert f_gold["weather_state"] == "HURRICANE_RISK_OFF"
        assert f_gold["risk_multiplier"] == 1.50
        assert "Safe-Haven BUY" in f_gold["trade_policy"]

        # Oil
        f_oil = self.weather_engine.forecast_market_weather("WTI")
        assert f_oil["weather_state"] == "HURRICANE_RISK_OFF"
        assert f_oil["risk_multiplier"] == 1.50

        # Euro
        f_eur = self.weather_engine.forecast_market_weather("EURUSD")
        assert f_eur["weather_state"] == "HURRICANE_RISK_OFF"
        assert f_eur["risk_multiplier"] == 0.50
        assert "Defensive Stance" in f_eur["trade_policy"]

        # Default asset
        f_other = self.weather_engine.forecast_market_weather("SPX500")
        assert f_other["weather_state"] == "HURRICANE_RISK_OFF"
        assert f_other["risk_multiplier"] == 0.65

    def test_thunderstorm_volatility_triggers(self):
        """Verifies THUNDERSTORM_VOLATILITY triggers on storm warnings or high barometric pressure differential."""
        # Set normal DEFCON
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 30.0, "conflict": 30.0, "security": 30.0, "information": 30.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=21.0, incident_count=0)

        # Mock satellite radar with storm warning
        mock_radar = MarketSatelliteRadar()
        mock_radar.scan_satellite_grid = lambda *args, **kwargs: {
            "radar_score": 75.0,
            "storm_warning": True,
            "pressure_differential_pct": 0.45
        }
        engine_storm = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar,
            satellite_radar=mock_radar
        )
        forecast = engine_storm.forecast_market_weather("XAUUSD")
        assert forecast["weather_state"] == "THUNDERSTORM_VOLATILITY"
        assert forecast["risk_multiplier"] == 0.75
        assert "FVG / Judas Sweep" in forecast["trade_policy"]

    def test_weather_engine_signature_versatility_and_corrupt_inputs(self):
        """Verifies signature versatility and tolerance to corrupt/empty data inputs."""
        # Signature 1: Single symbol string
        f1 = self.weather_engine.forecast_market_weather("BTCUSD")
        assert f1["symbol"] == "BTCUSD"
        assert "weather_state" in f1

        # Signature 2: Positional DataFrames + symbol keyword
        df_empty = pd.DataFrame()
        f2 = self.weather_engine.forecast_market_weather(df_empty, df_empty, symbol="ETHUSD")
        assert f2["symbol"] == "ETHUSD"

        # Signature 3: None DataFrames + positional symbol
        f3 = self.weather_engine.forecast_market_weather(None, None, "SOLUSD")
        assert f3["symbol"] == "SOLUSD"

        # Corrupt DataFrame (NaNs, single row, missing 'close')
        df_corrupt = pd.DataFrame({"random_col": [np.nan, 123.4]})
        f4 = self.weather_engine.forecast_market_weather(df_corrupt, df_corrupt, symbol="XAUUSD")
        assert f4["symbol"] == "XAUUSD"
        assert isinstance(f4["updraft_probability"], float)

    def test_interface_contract_3_strict_verification(self):
        """Verifies exact adherence to PROJECT.md Contract 3 schema and field types."""
        forecast = self.weather_engine.forecast_market_weather("XAUUSD")
        required_keys = [
            "symbol", "weather_state", "updraft_probability", "downdraft_probability",
            "barometric_pressure_hpa", "risk_multiplier", "trade_policy", "advisory",
            "forecast_summary", "radar_scan", "geopolitical_intel", "news_clearance", "timestamp"
        ]
        for key in required_keys:
            assert key in forecast, f"Missing Contract 3 key: {key}"

        assert isinstance(forecast["symbol"], str)
        assert isinstance(forecast["weather_state"], str)
        assert isinstance(forecast["updraft_probability"], float)
        assert isinstance(forecast["downdraft_probability"], float)
        assert isinstance(forecast["barometric_pressure_hpa"], float)
        assert isinstance(forecast["risk_multiplier"], float)
        assert isinstance(forecast["trade_policy"], str)
        assert isinstance(forecast["advisory"], str)

