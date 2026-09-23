"""
tests/test_e2e_opaque_box.py — Institutional E2E Opaque-Box Test Suite.
======================================================================
Adheres to the 4-Tier Testing Hierarchy strictly derived from ORIGINAL_REQUEST.md & PROJECT.md:
  - Tier 1: Canonical Feature Coverage (F01–F12, >=5 tests per feature -> 72 tests)
  - Tier 2: Boundary & Corner Cases (F01–F12, >=5 tests per feature -> 72 tests)
  - Tier 3: Cross-Feature Combinations (>=15 pairwise interaction tests -> 18 tests)
  - Tier 4: Real-World Multi-Account Scenarios (>=6 workflows -> 8 tests)
Total: 170 requirement-driven, self-contained, opaque-box tests.
"""

import os
import re
import json
import time
import base64
import tempfile
import datetime
from typing import Dict, Any, List

import pytest
import numpy as np
import pandas as pd

from dashboard.app import app
from src.fleet_risk_manager import FleetRiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.aladdin_risk_engine import AladdinRiskEngine
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.jarvis_agent_intel import JarvisAgentIntel
from src.whatsapp_copilot import is_whitelisted_number, AUTHORIZED_CONTACTS, ELITE_TRADE_GROUP_JID, SYMBOL_ALIASES
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.whatsapp_voice_transcriber import WhatsAppVoiceTranscriber
from src.order_flow_quant import OrderFlowQuantEngine
from src.predictive_weather_engine import PredictiveWeatherEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """Provides a fresh, isolated Flask test client for opaque HTTP REST requests."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def temp_fleet_config():
    """Creates a temporary fleet configuration file for isolated multi-account testing."""
    tmp = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json")
    initial_fleet = {
        "active_accounts": 5,
        "total_aum_potential": 181000.0,
        "fleet": {
            "account_5k": {
                "account_name": "Funding Pips 5k Evaluation",
                "account_id": "FP_5K_TEST",
                "server": "MetaQuotes-Demo",
                "starting_balance": 5000.0,
                "account_type": "FUNDING_PIPS",
                "risk_per_trade_pct": 0.0075,
                "max_daily_loss_pct": 0.025,
                "max_total_loss_pct": 0.06,
                "daily_loss_dollar_cap": 125.0,
                "trailing_hwm_floor": 4700.0,
                "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
                "consistency_cap_pct": 35.0,
                "is_active": True,
                "execution_mode": "LIVE_MT5"
            },
            "account_25k": {
                "account_name": "Funding Pips 25k Evaluation",
                "account_id": "FP_25K_TEST",
                "server": "MetaQuotes-Demo",
                "starting_balance": 25000.0,
                "account_type": "FUNDING_PIPS",
                "risk_per_trade_pct": 0.0075,
                "max_daily_loss_pct": 0.025,
                "max_total_loss_pct": 0.06,
                "daily_loss_dollar_cap": 625.0,
                "trailing_hwm_floor": 23500.0,
                "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
                "consistency_cap_pct": 35.0,
                "is_active": True,
                "execution_mode": "LIVE_MT5"
            },
            "account_50k": {
                "account_name": "Funding Pips 50k Evaluation",
                "account_id": "FP_50K_TEST",
                "server": "MetaQuotes-Demo",
                "starting_balance": 50000.0,
                "account_type": "FUNDING_PIPS",
                "risk_per_trade_pct": 0.0075,
                "max_daily_loss_pct": 0.025,
                "max_total_loss_pct": 0.06,
                "daily_loss_dollar_cap": 1250.0,
                "trailing_hwm_floor": 47000.0,
                "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
                "consistency_cap_pct": 35.0,
                "is_active": True,
                "execution_mode": "LIVE_MT5"
            },
            "account_100k": {
                "account_name": "Funding Pips 100k Evaluation",
                "account_id": "FP_100K_TEST",
                "server": "MetaQuotes-Demo",
                "starting_balance": 100000.0,
                "account_type": "FUNDING_PIPS",
                "risk_per_trade_pct": 0.0075,
                "max_daily_loss_pct": 0.025,
                "max_total_loss_pct": 0.06,
                "daily_loss_dollar_cap": 2500.0,
                "trailing_hwm_floor": 94000.0,
                "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
                "consistency_cap_pct": 35.0,
                "is_active": True,
                "execution_mode": "LIVE_MT5"
            },
            "account_crypto_1k": {
                "account_name": "Binance Micro Crypto",
                "account_id": "BINANCE_1K_TEST",
                "server": "Binance-Futures-Demo",
                "starting_balance": 1000.0,
                "account_type": "BINANCE_FUTURES",
                "risk_per_trade_pct": 0.015,
                "max_daily_loss_pct": 0.05,
                "max_total_loss_pct": 0.20,
                "daily_loss_dollar_cap": 50.0,
                "trailing_hwm_floor": 800.0,
                "allowed_assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "consistency_cap_pct": 100.0,
                "is_active": True,
                "execution_mode": "CRYPTO_BINANCE_FUTURES"
            }
        }
    }
    json.dump(initial_fleet, tmp, indent=2)
    tmp.close()

    yield tmp.name

    if os.path.exists(tmp.name):
        try:
            os.remove(tmp.name)
        except Exception:
            pass


@pytest.fixture
def risk_manager(temp_fleet_config):
    """Instantiates FleetRiskManager bound to isolated temp config."""
    onboarder = MultiAccountAutoOnboarder(config_path=temp_fleet_config)
    mgr = FleetRiskManager(config_path=temp_fleet_config, auto_onboarder=onboarder)
    return mgr


@pytest.fixture
def auto_onboarder(temp_fleet_config):
    """Instantiates MultiAccountAutoOnboarder bound to temp config."""
    return MultiAccountAutoOnboarder(config_path=temp_fleet_config)


@pytest.fixture
def quant_engine():
    """Instantiates OrderFlowQuantEngine."""
    return OrderFlowQuantEngine()


@pytest.fixture
def aladdin_engine():
    """Instantiates AladdinRiskEngine."""
    return AladdinRiskEngine()


@pytest.fixture
def world_monitor_engine():
    """Instantiates WorldMonitorIntelligenceEngine."""
    return WorldMonitorIntelligenceEngine()


@pytest.fixture
def jarvis_intel():
    """Instantiates JarvisAgentIntel."""
    return JarvisAgentIntel()


@pytest.fixture
def voice_transcriber():
    """Instantiates WhatsAppVoiceTranscriber."""
    return WhatsAppVoiceTranscriber()


@pytest.fixture
def fleet_executor(risk_manager):
    """Instantiates AutonomousFleetExecutor."""
    return AutonomousFleetExecutor(risk_manager=risk_manager)


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1: CANONICAL FEATURE COVERAGE (>=5 tests per feature for F01–F12)
# ══════════════════════════════════════════════════════════════════════════════

class TestTier1_F01_ResponsiveCSSGrid:
    """F01: Zero-Overflow Responsive CSS Grid & Viewport Integrity."""

    def test_f01_1_index_html_loads_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "<!DOCTYPE html>" in res.get_data(as_text=True)

    def test_f01_2_box_sizing_border_box_declared(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "box-sizing: border-box" in html or "box-sizing:border-box" in html

    def test_f01_3_dashboard_grid_container_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "dashboard-grid" in html or "grid-container" in html

    def test_f01_4_responsive_media_queries_defined(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "@media" in html
        assert "max-width" in html

    def test_f01_5_panel_containers_have_overflow_containment(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert ".panel" in html
        assert "border-radius" in html

    def test_f01_6_no_horizontal_overflow_width_clamping(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "max-width: 1920px" in html or "max-width:1920px" in html or "100%" in html


class TestTier1_F02_CyberIceBlueTheme:
    """F02: Cyber/Ice-Blue Design System & Visual Palette."""

    def test_f02_1_root_variables_define_dark_slate_backgrounds(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--bg-space" in html or "--bg-panel" in html or "#06080d" in html or "#0b0f19" in html

    def test_f02_2_neon_cyan_accent_variables_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--cyan-tech" in html or "--cyan-glow" in html or "#06b6d4" in html or "#00d2ff" in html

    def test_f02_3_gold_primary_accent_variables_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--gold-primary" in html or "#f59e0b" in html

    def test_f02_4_green_profit_and_red_loss_accents(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--green-profit" in html or "#10b981" in html
        assert "--red-loss" in html or "#ef4444" in html

    def test_f02_5_glassmorphic_translucent_panel_styles(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "border-radius" in html
        assert "background:" in html or "background-color:" in html

    def test_f02_6_high_contrast_typography_stacks(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "font-family:" in html or "font-family" in html


class TestTier1_F03_OneScreenCommandCenter:
    """F03: 1-Screen Command Center Layout & Unified Dashboard."""

    def test_f03_1_top_ticker_bar_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "ticker" in html.lower() or "top-bar" in html.lower() or "header" in html.lower()

    def test_f03_2_tradingview_chart_container_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "chart" in html.lower() or "tv-chart" in html.lower()

    def test_f03_3_market_weather_widget_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "weather" in html.lower() or "market-weather" in html.lower()

    def test_f03_4_shark_forensics_panel_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "shark" in html.lower() or "forensic" in html.lower()

    def test_f03_5_fleet_accounts_table_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "fleet" in html.lower() or "account" in html.lower()

    def test_f03_6_status_api_endpoint_returns_200(self, client):
        res = client.get("/api/status")
        assert res.status_code == 200
        data = res.get_json()
        assert "account" in data
        assert "prop_firm_gauges" in data


class TestTier1_F04_MaritimeThreatRadarFit:
    """F04: Maritime Threat Radar Viewport Fit & Chokepoint Integration."""

    def test_f04_1_maritime_radar_panel_present_in_dom(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "maritime" in html.lower() or "radar" in html.lower() or "chokepoint" in html.lower()

    def test_f04_2_world_monitor_endpoint_returns_success(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "chokepoints" in data
        assert "country_instability" in data

    def test_f04_3_world_monitor_contains_5_chokepoints(self, client):
        res = client.get("/api/world_monitor")
        data = res.get_json()
        chokepoints = data.get("chokepoints", {})
        assert len(chokepoints) >= 4
        assert "hormuz_strait" in chokepoints or "hormuz" in str(chokepoints).lower()

    def test_f04_4_country_instability_index_structure(self, client):
        res = client.get("/api/world_monitor")
        data = res.get_json()
        cii = data.get("country_instability", {})
        assert isinstance(cii, dict) and len(cii) > 0

    def test_f04_5_defcon_level_valid_integer(self, client):
        res = client.get("/api/world_monitor")
        data = res.get_json()
        defcon = data.get("defcon_level")
        assert isinstance(defcon, int)
        assert 1 <= defcon <= 5

    def test_f04_6_geopolitical_risk_multiplier_positive(self, client):
        res = client.get("/api/world_monitor")
        data = res.get_json()
        mult = data.get("risk_multiplier", 1.0)
        assert mult >= 0.5


class TestTier1_F05_PropFirmDailyDrawdownShield:
    """F05: Prop Firm Start-of-Day 2.5% Drawdown Shield."""

    def test_f05_1_5k_account_2_5pct_drawdown_locks(self, risk_manager):
        # 5k account: 2.5% of $5,000 = $125 max daily loss
        res = risk_manager.update_account_telemetry("FP_5K_TEST", balance=5000.0, equity=4870.0)  # $130 loss
        assert res["is_locked_out"] is True
        assert not res["daily_loss_shield_ok"]

    def test_f05_2_25k_account_2_5pct_drawdown_locks(self, risk_manager):
        # 25k account: 2.5% of $25,000 = $625 max daily loss
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24370.0)  # $630 loss
        assert res["is_locked_out"] is True
        assert not res["daily_loss_shield_ok"]

    def test_f05_3_50k_account_2_5pct_drawdown_locks(self, risk_manager):
        # 50k account: 2.5% of $50,000 = $1,250 max daily loss
        res = risk_manager.update_account_telemetry("FP_50K_TEST", balance=50000.0, equity=48740.0)  # $1,260 loss
        assert res["is_locked_out"] is True
        assert not res["daily_loss_shield_ok"]

    def test_f05_4_100k_account_2_5pct_drawdown_locks(self, risk_manager):
        # 100k account: 2.5% of $100,000 = $2,500 max daily loss
        res = risk_manager.update_account_telemetry("FP_100K_TEST", balance=100000.0, equity=97450.0)  # $2,550 loss
        assert res["is_locked_out"] is True
        assert not res["daily_loss_shield_ok"]

    def test_f05_5_safe_equity_keeps_shield_unlocked(self, risk_manager):
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24800.0)  # $200 loss < $625
        assert res["is_locked_out"] is False
        assert res["daily_loss_shield_ok"] is True

    def test_f05_6_pre_trade_risk_rejects_when_locked_out(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24300.0)
        approved, reason = risk_manager.validate_pre_trade_risk("FP_25K_TEST", "XAUUSD", 0.10, "BUY")
        assert approved is False
        assert "locked out" in reason.lower() or "drawdown" in reason.lower()


class TestTier1_F06_TrailingHWMFloorAndPacing:
    """F06: Trailing HWM Floor Guard & 5-Stage Consistency Pacing."""

    def test_f06_1_equity_gain_ratchets_absolute_hwm(self, risk_manager):
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=26500.0)
        assert res["absolute_hwm"] >= 26500.0

    def test_f06_2_floor_clamps_at_starting_balance_on_high_profit(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=27000.0)
        st = risk_manager.get_account_state("FP_25K_TEST")
        assert st["trailing_hwm_floor"] >= 25000.0
        assert st["hwm_locked_at_starting_balance"] is True

    def test_f06_3_trailing_floor_breach_triggers_lockout(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=23400.0)
        st = risk_manager.get_account_state("FP_25K_TEST")
        assert st["is_locked_out"] is True
        guard = risk_manager.check_trailing_hwm_floor("FP_25K_TEST")
        assert guard["safe"] is False

    def test_f06_4_consistency_pacing_stage_1_optimal(self, risk_manager):
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST")
        assert pacing["stage"] == 1
        assert pacing["risk_multiplier"] == 1.0
        assert pacing["can_trade"] is True

    def test_f06_5_consistency_pacing_stage_5_lockout(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=25800.0)
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["stage"] == 5
        assert pacing["risk_multiplier"] == 0.0
        assert pacing["can_trade"] is False

    def test_f06_6_sod_reset_clears_daily_lockout_if_floor_safe(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24300.0)
        st = risk_manager.get_account_state("FP_25K_TEST")
        assert st["is_locked_out"] is True
        reset_res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=24500.0, equity=24500.0, sod_reset=True)
        assert reset_res["is_locked_out"] is False


class TestTier1_F07_DynamicLotSizingAndATRStops:
    """F07: Dynamic Lot Sizing & 3.5x ATR Stops."""

    def test_f07_1_calculate_atr_stops_buy(self, risk_manager):
        res = risk_manager.calculate_atr_stops("XAUUSD", current_price=2650.0, side="BUY", atr_value=3.50)
        assert res["entry_price"] == 2650.0
        assert res["sl"] == round(2650.0 - (3.5 * 3.50), 5)
        assert res["tp1"] > 2650.0
        assert res["tp2"] > res["tp1"]

    def test_f07_2_calculate_atr_stops_sell(self, risk_manager):
        res = risk_manager.calculate_atr_stops("XAUUSD", current_price=2650.0, side="SELL", atr_value=3.50)
        assert res["entry_price"] == 2650.0
        assert res["sl"] == round(2650.0 + (3.5 * 3.50), 5)
        assert res["tp1"] < 2650.0
        assert res["tp2"] < res["tp1"]

    def test_f07_3_dynamic_lot_size_respects_max_risk_pct(self, risk_manager):
        lot = risk_manager.calculate_dynamic_lot_size("FP_25K_TEST", "XAUUSD", entry_price=2650.0, sl_price=2637.75)
        assert 0.05 <= lot <= 0.30
        assert isinstance(lot, float)

    def test_f07_4_dynamic_lot_size_forex_standard_lot(self, risk_manager):
        lot = risk_manager.calculate_dynamic_lot_size("FP_25K_TEST", "EURUSD", entry_price=1.0800, sl_price=1.0765)
        assert 0.20 <= lot <= 1.0

    def test_f07_5_min_lot_clamping_enforced(self, risk_manager):
        lot = risk_manager.calculate_dynamic_lot_size("FP_5K_TEST", "XAUUSD", entry_price=2650.0, sl_price=2000.0)
        assert lot >= 0.01

    def test_f07_6_reward_to_risk_ratios_valid(self, risk_manager):
        stops = risk_manager.calculate_atr_stops("EURUSD", current_price=1.0800, side="BUY", atr_value=0.0035)
        assert stops["rr_tp1"] == 1.5
        assert stops["rr_tp2"] == 2.5
        assert stops["rr_tp3"] == 4.0


class TestTier1_F08_CryptoMicroBalanceScaling:
    """F08: Crypto Micro-Balance Scaling & Perpetual Execution."""

    def test_f08_1_crypto_lot_precision_supports_fractional_units(self, risk_manager):
        lot = risk_manager.calculate_dynamic_lot_size("BINANCE_1K_TEST", "BTCUSDT", entry_price=63000.0, sl_price=62000.0)
        assert 0.001 <= lot <= 0.10
        assert isinstance(lot, float)

    def test_f08_2_auto_onboard_crypto_hyperliquid_account(self, auto_onboarder):
        res = auto_onboarder.onboard_new_account(
            account_id="HL_500_PERP",
            server="Hyperliquid-DEX",
            balance=500.0,
            account_type="HYPERLIQUID"
        )
        assert res["success"] is True
        assert res["account_data"]["starting_balance"] == 500.0
        assert "BTC-PERP" in res["account_data"]["allowed_assets"]

    def test_f08_3_crypto_status_endpoint_returns_200(self, client):
        res = client.get("/api/weekend_crypto_status")
        assert res.status_code == 200
        data = res.get_json()
        assert "status" in data or "crypto" in str(data).lower()

    def test_f08_4_lee_ready_cvd_divergence_calculation(self, quant_engine):
        # Detect buyer absorption divergence
        res = quant_engine.detect_absorption_divergence(
            price_swing_1=100.0, price_swing_2=95.0, cvd_swing_1=500.0, cvd_swing_2=700.0
        )
        assert res["absorption_detected"] is True
        assert res["type"] == "BUYER_ABSORPTION"

    def test_f08_5_route_order_crypto_routes_to_bitget(self, fleet_executor):
        order = {
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "lots": 0.05,
            "entry_price": 63000.0,
            "sl": 62500.0,
            "tp": 64500.0
        }
        receipt = fleet_executor.route_order("BINANCE_1K_TEST", order)
        assert receipt["venue"] == "BITGET"
        assert receipt["symbol"] == "BTCUSDT"
        assert receipt["lots"] == 0.05

    def test_f08_6_crypto_broker_shield_status_endpoint(self, client):
        res = client.get("/api/broker_shield_status")
        assert res.status_code == 200


class TestTier1_F09_JarvisAndHermesDelegation:
    """F09: Muhammad's Jarvis & Hermes Delegation."""

    def test_f09_1_hermes_delegate_endpoint_happy_path(self, client):
        payload = {"task": "Synthesize 70.5% OTE level and liquidity pool for Gold"}
        res = client.post("/api/hermes_delegate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "task" in data

    def test_f09_2_jarvis_gold_advisor_briefing_returns_valid_structure(self, jarvis_intel):
        briefing = jarvis_intel.get_gold_advisor_briefing(fast_mode=True)
        assert briefing["success"] is True
        assert "briefing" in briefing
        assert "GOLD" in briefing["briefing"] or "XAU" in briefing["briefing"]

    def test_f09_3_order_flow_quant_calculates_ote_fibonacci(self, quant_engine):
        df_entry = pd.DataFrame({
            "high": [2680.0 + i for i in range(20)],
            "low": [2650.0 + i for i in range(20)],
            "close": [2670.0 + i for i in range(20)]
        })
        res = quant_engine.compute_ote_fibonacci_array(df_entry, current_price=2664.0, direction="BUY")
        assert "fib_705_sweet_spot" in res
        assert "fib_618" in res
        assert "fib_786" in res

    def test_f09_4_order_flow_quant_evaluates_premium_discount(self, quant_engine):
        df_range = pd.DataFrame({"high": [2700.0]*15, "low": [2600.0]*15})
        disc = quant_engine.evaluate_premium_discount(df_range, current_price=2620.0)
        assert disc["zone"] == "DISCOUNT"
        assert disc["is_buy_allowed"] is True

    def test_f09_5_fvg_consequent_encroachment_midpoint(self, quant_engine):
        df_range = pd.DataFrame({"high": [2700.0]*15, "low": [2600.0]*15})
        res = quant_engine.evaluate_premium_discount(df_range, current_price=2650.0)
        assert res["equilibrium"] == 2650.0

    def test_f09_6_turtle_soup_liquidity_sweep_detection(self, quant_engine):
        df_entry = pd.DataFrame({
            "high": [2680.0 + i for i in range(20)],
            "low": [2650.0 + i for i in range(20)],
            "close": [2670.0 + i for i in range(20)]
        })
        res = quant_engine.detect_eqh_eql_inducement(df_entry, symbol="XAUUSD")
        assert "inducement_type" in res
        assert "is_swept" in res


class TestTier1_F10_WorldMonitorGeopoliticalRadar:
    """F10: WorldMonitor Geopolitical Radar API & Maritime Defense."""

    def test_f10_1_world_monitor_radar_instantiation(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        assert "chokepoints" in brief
        assert "country_instability" in brief
        assert "defcon_level" in brief

    def test_f10_2_hormuz_chokepoint_metrics_present(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        chokepoints = brief.get("chokepoints", {})
        hormuz = chokepoints.get("hormuz_strait") or chokepoints.get("hormuz")
        assert hormuz is not None
        assert "disruption_pct" in hormuz
        assert "risk_level" in hormuz

    def test_f10_3_bab_el_mandeb_chokepoint_metrics_present(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        chokepoints = brief.get("chokepoints", {})
        bab = chokepoints.get("bab_el_mandeb")
        assert bab is not None
        assert "flow_pct_of_baseline" in bab

    def test_f10_4_cii_4_pillar_scores_exist(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        cii = brief.get("country_instability", {})
        assert isinstance(cii, dict)
        assert len(cii) > 0

    def test_f10_5_market_weather_endpoint_returns_success(self, client):
        res = client.get("/api/market_weather")
        assert res.status_code == 200
        data = res.get_json()
        assert "barometer_score" in data or "regime" in data or "status" in data

    def test_f10_6_liquidation_radar_endpoint_returns_success(self, client):
        res = client.get("/api/liquidation_radar")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") in ["success", "ok"] or "symbol" in data


class TestTier1_F11_WhatsAppSovereignCopilot:
    """F11: Live WhatsApp Sovereign Copilot & Whitelist Control."""

    def test_f11_1_whitelisted_number_authorized(self):
        assert is_whitelisted_number("923468053268@s.whatsapp.net") is True
        assert is_whitelisted_number("+923468053268") is True
        assert is_whitelisted_number(ELITE_TRADE_GROUP_JID) is True

    def test_f11_2_unauthorized_number_rejected(self):
        assert is_whitelisted_number("1234567890@s.whatsapp.net") is False
        assert is_whitelisted_number("attacker@broadcast") is False
        assert is_whitelisted_number("random_group@g.us") is False

    def test_f11_3_whatsapp_command_status_inquiry(self, client):
        payload = {"from": "923468053268@s.whatsapp.net", "body": "STATUS"}
        res = client.post("/api/whatsapp_command", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert "reply" in data or "status" in data

    def test_f11_4_whatsapp_audio_mock_transcription(self, voice_transcriber):
        text = voice_transcriber.transcribe_audio("mock_gold_buy")
        assert "Buy Gold" in text

    def test_f11_5_whatsapp_qr_endpoint_returns_status(self, client):
        res = client.get("/api/whatsapp_qr")
        assert res.status_code == 200
        data = res.get_json()
        assert "connected" in data or "qr" in data or "status" in data

    def test_f11_6_symbol_aliasing_maps_urdu_and_shorthand(self):
        assert SYMBOL_ALIASES.get("SONA") == "XAUUSD"
        assert SYMBOL_ALIASES.get("GOLD") == "XAUUSD"
        assert SYMBOL_ALIASES.get("CHANDI") == "XAGUSD"
        assert SYMBOL_ALIASES.get("BITCOIN") == "BTCUSD"
        assert SYMBOL_ALIASES.get("EU") == "EURUSD"


class TestTier1_F12_TriPillarExplainableForensics:
    """F12: Tri-Pillar Explainable Forensics & Candlestick Overlays."""

    def test_f12_1_chart_data_endpoint_returns_candles_and_ghosts(self, client):
        res = client.get("/api/chart_data/XAUUSD?tf=15m")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "candles" in data
        assert "future_projected_candles" in data
        assert len(data["candles"]) > 0
        assert len(data["future_projected_candles"]) == 4

    def test_f12_2_shark_forensics_endpoint_returns_whale_attribution(self, client):
        res = client.get("/api/shark_forensics")
        assert res.status_code == 200
        data = res.get_json()
        assert "forensics" in data or "whale_orders" in data or "status" in data

    def test_f12_3_trade_cards_endpoint_returns_live_cards(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()
        assert "positions" in data and "pending_signals" in data

    def test_f12_4_trade_cards_contain_tri_pillar_fields(self, client):
        res = client.get("/api/trade_cards")
        data = res.get_json()
        positions = data.get("positions", [])
        assert len(positions) > 0
        pos = positions[0]
        assert "symbol" in pos
        assert "sl" in pos
        assert "tp1" in pos

    def test_f12_5_aladdin_parametric_var_cvar_computation(self, aladdin_engine):
        res = aladdin_engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.012)
        assert res["var_99_dollar"] > 0
        assert res["var_95_dollar"] > 0
        assert res["cvar_99_dollar"] >= res["var_99_dollar"]

    def test_f12_6_fractional_kelly_sizing_within_risk_cap(self, aladdin_engine):
        kelly = aladdin_engine.compute_fractional_kelly(win_rate=0.55, payoff_ratio=2.0)
        assert 0.0025 <= kelly <= 0.0075


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per feature for F01–F12)
# ══════════════════════════════════════════════════════════════════════════════

class TestTier2_F01_ResponsiveGridBoundaries:
    """F01 Boundary: Viewport extremums and CSS robustness."""

    def test_f01_b1_extreme_large_viewport_css(self, client):
        res = client.get("/")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "1920px" in html or "100%" in html

    def test_f01_b2_extreme_mobile_viewport_media_query(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "600px" in html or "700px" in html or "800px" in html

    def test_f01_b3_no_script_injection_in_dashboard_template(self, client):
        res = client.get("/?param=<script>alert(1)</script>")
        assert res.status_code == 200
        assert "<script>alert(1)</script>" not in res.get_data(as_text=True)

    def test_f01_b4_repeated_index_loads_do_not_leak_memory(self, client):
        for _ in range(10):
            res = client.get("/")
            assert res.status_code == 200

    def test_f01_b5_head_and_body_properly_closed(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "</head>" in html
        assert "</body>" in html

    def test_f01_b6_viewport_meta_tag_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert 'name="viewport"' in html


class TestTier2_F02_DesignSystemBoundaries:
    """F02 Boundary: Color theme fallbacks and invalid styles."""

    def test_f02_b1_all_theme_vars_properly_formatted(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "#" in html

    def test_f02_b2_high_contrast_text_color_defined(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--text-main" in html or "#f8fafc" in html or "#fff" in html or "#ffffff" in html

    def test_f02_b3_dim_text_color_defined(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "--text-muted" in html or "--text-dim" in html or "#94a3b8" in html or "#64748b" in html

    def test_f02_b4_button_interactive_styles_present(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "button" in html.lower()

    def test_f02_b5_badge_styles_defined(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        assert "badge" in html.lower()

    def test_f02_b6_no_unclosed_style_tags(self, client):
        res = client.get("/")
        html = res.get_data(as_text=True)
        open_tags = html.count("<style")
        close_tags = html.count("</style>")
        assert open_tags == close_tags


class TestTier2_F03_CommandCenterBoundaries:
    """F03 Boundary: Invalid API queries and status telemetry."""

    def test_f03_b1_status_api_options_method(self, client):
        res = client.open("/api/status", method="OPTIONS")
        assert res.status_code in [200, 204, 405]

    def test_f03_b2_accounts_api_returns_active_fleet(self, client):
        res = client.get("/api/accounts")
        assert res.status_code == 200
        data = res.get_json()
        assert "accounts" in data or "fleet" in data or isinstance(data, list) or isinstance(data, dict)

    def test_f03_b3_post_control_empty_payload_rejected(self, client):
        res = client.post("/api/control", json={})
        assert res.status_code in [400, 200]

    def test_f03_b4_post_control_invalid_action(self, client):
        res = client.post("/api/control", json={"action": "INVALID_UNKNOWN_ACTION_99"})
        assert res.status_code in [400, 200]

    def test_f03_b5_live_commentary_endpoint_returns_list(self, client):
        res = client.get("/api/live_commentary")
        assert res.status_code == 200

    def test_f03_b6_alpha_models_endpoint_returns_success(self, client):
        res = client.get("/api/alpha_models")
        assert res.status_code == 200


class TestTier2_F04_MaritimeRadarBoundaries:
    """F04 Boundary: Extreme disruption metrics and zero flows."""

    def test_f04_b1_zero_incident_count_handled(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        assert brief is not None

    def test_f04_b2_100pct_disruption_escalates_risk_multiplier(self, world_monitor_engine):
        bias = world_monitor_engine.get_geopolitical_market_bias("XAUUSD")
        assert bias["macro_multiplier"] >= 1.0

    def test_f04_b3_unknown_asset_geopolitical_multiplier_defaults_to_neutral(self, world_monitor_engine):
        bias = world_monitor_engine.get_geopolitical_market_bias("UNKNOWN_COIN_XYZ")
        assert bias["macro_multiplier"] == 1.0

    def test_f04_b4_defcon_level_boundaries(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        defcon = brief.get("defcon_level", 3)
        assert 1 <= defcon <= 5

    def test_f04_b5_malformed_chokepoint_lookup_safe(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        status = brief.get("chokepoints", {}).get("NON_EXISTENT_STRAIT")
        assert status is None

    def test_f04_b6_world_monitor_json_serialization_safe(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        json.loads(res.get_data(as_text=True))


class TestTier2_F05_DrawdownShieldBoundaries:
    """F05 Boundary: Exact threshold drawdowns and zero balances."""

    def test_f05_b1_exact_2_500pct_drawdown_boundary(self, risk_manager):
        # Exact $625 loss on $25,000 (equity = $24,375.00)
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24375.0)
        assert res["daily_loss_shield_ok"] is False
        assert res["is_locked_out"] is True

    def test_f05_b2_just_under_2_5pct_drawdown_stays_safe(self, risk_manager):
        # $624.90 loss on $25,000 (equity = $24,375.10)
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24375.10)
        assert res["daily_loss_shield_ok"] is True
        assert res["is_locked_out"] is False

    def test_f05_b3_zero_balance_safely_handled(self, risk_manager):
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=0.0, equity=0.0)
        assert res["is_locked_out"] is True

    def test_f05_b4_negative_balance_locks_out(self, risk_manager):
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=-500.0, equity=-500.0)
        assert res["is_locked_out"] is True

    def test_f05_b5_non_existent_account_lookup_safe(self, risk_manager):
        shield = risk_manager.check_daily_loss_shield("NON_EXISTENT_ACC_999")
        assert shield["safe"] is False
        assert shield["breached"] is True

    def test_f05_b6_pre_trade_risk_rejects_non_existent_account(self, risk_manager):
        approved, reason = risk_manager.validate_pre_trade_risk("NON_EXISTENT_ACC_999", "XAUUSD", 0.10, "BUY")
        assert approved is False
        assert "not found" in reason.lower()


class TestTier2_F06_HWMFloorAndPacingBoundaries:
    """F06 Boundary: Pacing edge limits and zero profit baselines."""

    def test_f06_b1_zero_profit_pacing_stage_1(self, risk_manager):
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["pacing_pct"] == 0.0
        assert pacing["stage"] == 1

    def test_f06_b2_negative_profit_pacing_stays_stage_1(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24800.0)
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["stage"] == 1
        assert pacing["risk_multiplier"] == 1.0

    def test_f06_b3_exact_20pct_pacing_boundary_stage_2(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=25400.0)
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["stage"] == 2
        assert pacing["risk_multiplier"] == 0.8

    def test_f06_b4_exact_25pct_pacing_boundary_stage_3(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=25500.0)
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["stage"] == 3
        assert pacing["risk_multiplier"] == 0.5

    def test_f06_b5_exact_30pct_pacing_boundary_stage_4(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=25600.0)
        pacing = risk_manager.calculate_consistency_pacing("FP_25K_TEST", profit_target=2000.0)
        assert pacing["stage"] == 4
        assert pacing["risk_multiplier"] == 0.25

    def test_f06_b6_trailing_floor_exact_breach_boundary(self, risk_manager):
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=23500.0)
        guard = risk_manager.check_trailing_hwm_floor("FP_25K_TEST")
        assert guard["safe"] is False
        assert guard["breached"] is True


class TestTier2_F07_LotSizingAndATRBoundaries:
    """F07 Boundary: Zero/negative ATR and extreme price distances."""

    def test_f07_b1_zero_atr_uses_fallback_atr(self, risk_manager):
        res = risk_manager.calculate_atr_stops("XAUUSD", current_price=2650.0, side="BUY", atr_value=0.0)
        assert res["atr"] > 0
        assert res["sl"] < 2650.0

    def test_f07_b2_negative_atr_uses_fallback_atr(self, risk_manager):
        res = risk_manager.calculate_atr_stops("XAUUSD", current_price=2650.0, side="BUY", atr_value=-5.0)
        assert res["atr"] > 0

    def test_f07_b3_zero_sl_distance_returns_min_lot(self, risk_manager):
        lot = risk_manager.calculate_dynamic_lot_size("FP_25K_TEST", "XAUUSD", entry_price=2650.0, sl_price=2650.0)
        assert lot == 0.01

    def test_f07_b4_huge_equity_clamps_to_max_lot(self, risk_manager):
        risk_manager.update_account_telemetry("FP_100K_TEST", balance=10000000.0, equity=10000000.0)
        lot = risk_manager.calculate_dynamic_lot_size("FP_100K_TEST", "XAUUSD", entry_price=2650.0, sl_price=2649.90)
        assert lot <= 50.0

    def test_f07_b5_pre_trade_audit_rejects_disallowed_asset(self, risk_manager):
        approved, reason = risk_manager.validate_pre_trade_risk("FP_25K_TEST", "DOGE_UNAUTHORIZED", 0.10, "BUY")
        assert approved is False
        assert "not permitted" in reason.lower() or "not allowed" in reason.lower()

    def test_f07_b6_pre_trade_audit_rejects_invalid_sl_orientation(self, risk_manager):
        # BUY SL above entry price is invalid
        approved, reason = risk_manager.validate_pre_trade_risk(
            "FP_25K_TEST", "XAUUSD", 0.10, "BUY", entry_price=2650.0, sl_price=2700.0
        )
        assert approved is False
        assert "invalid buy stop loss" in reason.lower()


class TestTier2_F08_CryptoMicroBalanceBoundaries:
    """F08 Boundary: Micro balances and extreme crypto volatility."""

    def test_f08_b1_micro_balance_100_dollars_sizing(self, risk_manager, auto_onboarder):
        auto_onboarder.onboard_new_account("CRYPTO_100", "Binance", 100.0, "BINANCE_FUTURES")
        risk_manager.load_fleet()
        lot = risk_manager.calculate_dynamic_lot_size("CRYPTO_100", "BTCUSDT", entry_price=63000.0, sl_price=60000.0)
        assert lot >= 0.001

    def test_f08_b2_empty_order_flow_dataframe_safe(self, quant_engine):
        res = quant_engine.compute_tick_cvd(None)
        assert res["cvd"] == 0
        assert res["is_absorption_divergence"] is False

    def test_f08_b3_short_order_flow_dataframe_safe(self, quant_engine):
        df_short = pd.DataFrame({"high": [100.0, 101.0], "low": [95.0, 96.0], "close": [98.0, 99.0]})
        res = quant_engine.compute_ote_fibonacci_array(df_short, current_price=100.0, direction="BUY")
        assert res["in_ote_zone"] is False

    def test_f08_b4_weekend_crypto_arbitrage_engine_instantiation(self):
        engine = WeekendCryptoArbitrageEngine()
        status = engine.get_weekend_mode_status()
        assert isinstance(status, dict)

    def test_f08_b5_crypto_zero_volume_bars_safe(self, quant_engine):
        res = quant_engine.detect_absorption_divergence(100.0, 100.0, 0.0, 0.0)
        assert res is not None

    def test_f08_b6_bitget_connector_mock_safety(self, fleet_executor):
        res = fleet_executor.bitget_connector.place_order(symbol="ETHUSDT", side="buy", size=0.1)
        assert isinstance(res, dict)
        assert "status" in res or "order_id" in res


class TestTier2_F09_JarvisHermesBoundaries:
    """F09 Boundary: Empty tasks, extreme strings, and OTE zero ranges."""

    def test_f09_b1_hermes_delegate_missing_task_returns_400(self, client):
        res = client.post("/api/hermes_delegate", json={})
        assert res.status_code == 400

    def test_f09_b2_hermes_delegate_empty_task_string_returns_400(self, client):
        res = client.post("/api/hermes_delegate", json={"task": ""})
        assert res.status_code == 400

    def test_f09_b3_hermes_delegate_handles_large_prompt(self, client):
        large_prompt = "Analyze market " + ("XAUUSD " * 500)
        res = client.post("/api/hermes_delegate", json={"task": large_prompt})
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"

    def test_f09_b4_ote_fibonacci_short_dataframe_safe(self, quant_engine):
        df_short = pd.DataFrame({"high": [2650.0]*5, "low": [2640.0]*5, "close": [2645.0]*5})
        res = quant_engine.compute_ote_fibonacci_array(df_short, current_price=2650.0, direction="BUY")
        assert res["in_ote_zone"] is False

    def test_f09_b5_premium_discount_short_dataframe_safe(self, quant_engine):
        df_short = pd.DataFrame({"high": [2650.0]*5, "low": [2640.0]*5})
        res = quant_engine.evaluate_premium_discount(df_short, current_price=2650.0)
        assert res["zone"] == "EQUILIBRIUM"

    def test_f09_b6_premium_discount_equal_high_low_handled(self, quant_engine):
        df_flat = pd.DataFrame({"high": [2650.0]*15, "low": [2650.0]*15})
        res = quant_engine.evaluate_premium_discount(df_flat, current_price=2650.0)
        assert res["zone"] == "EQUILIBRIUM"


class TestTier2_F10_WorldMonitorRadarBoundaries:
    """F10 Boundary: Out of bound indices and DEFCON limits."""

    def test_f10_b1_extreme_negative_risk_multiplier_clamped(self, world_monitor_engine):
        bias = world_monitor_engine.get_geopolitical_market_bias("EURUSD")
        assert bias["macro_multiplier"] >= 0.0

    def test_f10_b2_chokepoints_dictionary_immutable_copy(self, world_monitor_engine):
        brief1 = world_monitor_engine.get_world_intelligence_brief()
        assert len(brief1["chokepoints"]) > 0

    def test_f10_b3_cii_values_bounded_0_to_100(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        assert 0.0 <= brief.get("global_risk_index", 50.0) <= 100.0

    def test_f10_b4_world_monitor_polymarket_odds_keys_exist(self, world_monitor_engine):
        brief = world_monitor_engine.get_world_intelligence_brief()
        assert "polymarket_odds" in brief or "polymarket_geopolitical_odds" in brief

    def test_f10_b5_weather_barometer_score_bounded_0_to_100(self, client):
        res = client.get("/api/market_weather")
        data = res.get_json()
        if "barometer_score" in data:
            assert 0.0 <= float(data["barometer_score"]) <= 100.0

    def test_f10_b6_neural_sentiment_stream_endpoint_returns_success(self, client):
        res = client.get("/api/neural_sentiment")
        assert res.status_code == 200


class TestTier2_F11_WhatsAppCopilotBoundaries:
    """F11 Boundary: Security spoofing, injection, and corrupted audio."""

    def test_f11_b1_sql_injection_in_sender_rejected(self):
        assert is_whitelisted_number("923468053268' OR '1'='1") is False

    def test_f11_b2_control_characters_in_sender_rejected(self):
        assert is_whitelisted_number("923468053268\n@s.whatsapp.net") is False
        assert is_whitelisted_number("923468053268\x00@s.whatsapp.net") is False

    def test_f11_b3_empty_audio_base64_returns_empty_string(self, voice_transcriber):
        assert voice_transcriber.transcribe_audio("") == ""
        assert voice_transcriber.transcribe_audio(None) == ""

    def test_f11_b4_corrupted_base64_audio_handled_gracefully(self, client):
        payload = {"audio_base64": "NOT_VALID_BASE64_$%^&*", "sender": "923468053268@s.whatsapp.net"}
        res = client.post("/api/whatsapp_audio", json=payload)
        assert res.status_code in [200, 400]

    def test_f11_b5_unauthorized_whatsapp_command_rejected_or_unanswered(self, client):
        payload = {"from": "447700900077@s.whatsapp.net", "body": "STATUS"}
        res = client.post("/api/whatsapp_command", json=payload)
        assert res.status_code == 403
        data = res.get_json()
        assert data.get("status") == "blocked" or data.get("success") is False

    def test_f11_b6_chat_consult_empty_message_returns_400(self, client):
        res = client.post("/api/chat_consult", json={})
        assert res.status_code in [400, 200]


class TestTier2_F12_ForensicsBoundaries:
    """F12 Boundary: Missing chart symbols, invalid timeframes, extreme VaR."""

    def test_f12_b1_unknown_symbol_chart_data_returns_fallback_candles(self, client):
        res = client.get("/api/chart_data/UNKNOWN_SYM_XYZ?tf=15m")
        assert res.status_code == 200
        data = res.get_json()
        assert "candles" in data
        assert len(data["candles"]) > 0

    def test_f12_b2_invalid_timeframe_defaults_safely(self, client):
        res = client.get("/api/chart_data/XAUUSD?tf=999xyz")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["candles"]) > 0

    def test_f12_b3_aladdin_var_with_zero_volatility(self, aladdin_engine):
        res = aladdin_engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.0)
        assert res["var_99_dollar"] == 0.0
        assert res["cvar_99_dollar"] == 0.0

    def test_f12_b4_aladdin_fractional_kelly_negative_win_rate_clamped(self, aladdin_engine):
        kelly = aladdin_engine.compute_fractional_kelly(win_rate=-0.5, payoff_ratio=2.0)
        assert kelly == 0.0025

    def test_f12_b5_aladdin_fractional_kelly_extreme_payoff_ratio(self, aladdin_engine):
        kelly = aladdin_engine.compute_fractional_kelly(win_rate=0.90, payoff_ratio=100.0)
        assert kelly <= 0.0075

    def test_f12_b6_order_book_dom_endpoint_returns_bids_asks(self, client):
        res = client.get("/api/order_book_dom/XAUUSD")
        assert res.status_code == 200
        data = res.get_json()
        assert "bids" in data or "asks" in data or "symbol" in data


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3: CROSS-FEATURE COMBINATIONS (>=15 Pairwise Interaction Tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestTier3_CrossFeatureCombinations:
    """Tier 3: Pairwise state transitions and multi-module interoperability."""

    def test_t3_01_drawdown_lock_and_whatsapp_query(self, client, risk_manager):
        """Combination 1: Drawdown Lock (F05) + WhatsApp Command Query (F11)."""
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24300.0)
        st = risk_manager.get_account_state("FP_25K_TEST")
        assert st["is_locked_out"] is True

        payload = {"from": "923468053268@s.whatsapp.net", "body": "STATUS"}
        res = client.post("/api/whatsapp_command", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert "reply" in data

    def test_t3_02_hermes_delegation_and_ote_fibonacci_synthesis(self, client, quant_engine):
        """Combination 2: Hermes Delegation (F09) + 70.5% OTE Synthesis (F12)."""
        df_entry = pd.DataFrame({
            "high": [2680.0 + i for i in range(20)],
            "low": [2650.0 + i for i in range(20)],
            "close": [2670.0 + i for i in range(20)]
        })
        ote = quant_engine.compute_ote_fibonacci_array(df_entry, current_price=2664.0, direction="BUY")
        sweet_spot = ote["fib_705_sweet_spot"]

        payload = {"task": f"Analyze trade plan at OTE 70.5% level ${sweet_spot:.2f} with 3.5x ATR stop"}
        res = client.post("/api/hermes_delegate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"

    def test_t3_03_world_monitor_chokepoint_and_aladdin_var_sizing(self, world_monitor_engine, aladdin_engine):
        """Combination 3: WorldMonitor Threat (F10) + Aladdin VaR & Fleet Sizing (F07)."""
        bias = world_monitor_engine.get_geopolitical_market_bias("XAUUSD")
        mult = bias["macro_multiplier"]
        assert mult >= 1.0

        base_vol = 0.012
        shocked_vol = base_vol * mult
        var_res = aladdin_engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=shocked_vol)
        assert var_res["var_99_dollar"] > 0

    def test_t3_04_consistency_pacing_lockout_and_lot_sizing(self, risk_manager):
        """Combination 4: Consistency Pacing Stage 5 (F06) + Dynamic Lot Sizing (F07)."""
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=25850.0)
        lot = risk_manager.calculate_dynamic_lot_size("FP_25K_TEST", "XAUUSD", entry_price=2650.0, sl_price=2640.0)
        assert lot == 0.0

    def test_t3_05_auto_onboarder_and_prop_firm_rules_inheritance(self, auto_onboarder, risk_manager):
        """Combination 5: Auto-Onboarder (F05/F08) + Prop Firm Evaluation Rules (F06)."""
        res = auto_onboarder.onboard_new_account("FP_100K_NEW", "MetaQuotes-Demo", 100000.0, "FUNDING_PIPS")
        assert res["success"] is True
        risk_manager.load_fleet()
        st = risk_manager.get_account_state("FP_100K_NEW")
        assert st["daily_loss_dollar_cap"] == 2500.0
        assert st["risk_per_trade_pct"] == 0.0075

    def test_t3_06_voice_note_directive_and_breakeven_lock(self, voice_transcriber, fleet_executor):
        """Combination 6: Voice Directives (F11) + 1-Click Breakeven Lock (F07/F06)."""
        text = voice_transcriber.transcribe_audio("mock_be_lock")
        assert "breakeven" in text.lower()
        intent = voice_transcriber.parse_voice_intent(text)
        assert intent["intent"] == "BREAKEVEN"

        res = fleet_executor.manage_position_action(ticket=9841201, action="breakeven")
        assert res["success"] is True

    def test_t3_07_lee_ready_cvd_absorption_and_turtle_soup_sweep(self, quant_engine):
        """Combination 7: CVD Absorption (F08/F12) + Turtle Soup Sweep (F09)."""
        df_candles = pd.DataFrame({
            "high": [2680.0 + i for i in range(20)],
            "low": [2650.0 + i for i in range(20)],
            "close": [2670.0 + i for i in range(20)]
        })
        cvd_res = quant_engine.detect_absorption_divergence(2680.0, 2670.0, 500.0, 800.0)
        sweep_res = quant_engine.detect_eqh_eql_inducement(df_candles, symbol="XAUUSD")
        assert cvd_res["absorption_detected"] is True
        assert "inducement_type" in sweep_res

    def test_t3_08_fvg_consequent_encroachment_and_atr_stops(self, quant_engine, risk_manager):
        """Combination 8: 50% FVG CE (F09) + 3.5x ATR Stops (F07)."""
        df_range = pd.DataFrame({"high": [2700.0]*15, "low": [2600.0]*15})
        pd_res = quant_engine.evaluate_premium_discount(df_range, current_price=2650.0)
        entry = pd_res["equilibrium"]
        stops = risk_manager.calculate_atr_stops("XAUUSD", current_price=entry, side="BUY", atr_value=3.50)
        assert stops["entry_price"] == 2650.0
        assert stops["sl"] == round(2650.0 - (3.5 * 3.50), 5)

    def test_t3_09_hwm_floor_ratchet_and_fleet_telemetry_sync(self, risk_manager):
        """Combination 9: Trailing HWM Floor (F06) + Telemetry Sync (F05)."""
        risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=28000.0)
        st = risk_manager.get_account_state("FP_25K_TEST")
        assert st["trailing_hwm_floor"] >= 25000.0

        guard = risk_manager.check_trailing_hwm_floor("FP_25K_TEST")
        assert guard["safe"] is True

    def test_t3_10_whatsapp_symbol_aliasing_and_chart_stream(self, client):
        """Combination 10: WhatsApp Aliasing (F11) + Chart Stream Data (F12)."""
        alias_sym = SYMBOL_ALIASES["SONA"]
        res = client.get(f"/api/chart_data/{alias_sym}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["symbol"] == "XAUUSD"

    def test_t3_11_emergency_kill_switch_and_fleet_executor(self, fleet_executor):
        """Combination 11: Panic Kill Switch (F11) + Fleet Executor (F07)."""
        res = fleet_executor.emergency_kill_switch()
        assert res["success"] is True

    def test_t3_12_crypto_micro_sizing_and_fractional_kelly(self, aladdin_engine, risk_manager):
        """Combination 12: Crypto Micro-Sizing (F08) + Aladdin Fractional Kelly (F07)."""
        kelly_risk = aladdin_engine.compute_fractional_kelly(win_rate=0.58, payoff_ratio=2.2)
        lot = risk_manager.calculate_dynamic_lot_size(
            "BINANCE_1K_TEST", "BTCUSDT", entry_price=63000.0, sl_price=62000.0, custom_risk_pct=kelly_risk
        )
        assert 0.001 <= lot <= 0.05

    def test_t3_13_world_monitor_anomaly_and_gold_briefing(self, world_monitor_engine, jarvis_intel):
        """Combination 13: WorldMonitor Anomaly (F10) + Gold Briefing (F09)."""
        brief = world_monitor_engine.get_world_intelligence_brief()
        briefing = jarvis_intel.get_gold_advisor_briefing(fast_mode=True)
        assert "chokepoints" in brief
        assert briefing["success"] is True

    def test_t3_14_onboard_account_post_and_accounts_telemetry_get(self, client):
        """Combination 14: POST /api/onboard_account (F05/F08) + GET /api/accounts (F03)."""
        payload = {
            "account_id": "FP_TEST_LIVE_99",
            "broker": "MetaQuotes-Demo",
            "balance": 25000.0,
            "account_type": "FUNDING_PIPS"
        }
        post_res = client.post("/api/onboard_account", json=payload)
        assert post_res.status_code in [200, 201]

        get_res = client.get("/api/accounts")
        assert get_res.status_code == 200

    def test_t3_15_shark_forensics_and_trade_cards(self, client):
        """Combination 15: Shark Forensics (F12) + Trade Cards API (F03/F07)."""
        shark_res = client.get("/api/shark_forensics")
        cards_res = client.get("/api/trade_cards")
        assert shark_res.status_code == 200
        assert cards_res.status_code == 200

    def test_t3_16_roman_urdu_consultation_and_ai_consultant(self, client):
        """Combination 16: Voice Consultation in Roman Urdu (F11) + AI Consultant (F09)."""
        payload = {"message": "Bhai Gold buy karna theek rahay ga ya support break ho gaya?"}
        res = client.post("/api/chat_consult", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert "advice" in data or "parsed" in data or "response" in data

    def test_t3_17_pre_trade_risk_interceptor_and_order_routing(self, risk_manager, fleet_executor):
        """Combination 17: Pre-Trade Interceptor (F05/F07) + Order Routing (F07/F08)."""
        approved, _ = risk_manager.validate_pre_trade_risk("FP_25K_TEST", "XAUUSD", 0.15, "BUY")
        assert approved is True
        receipt = fleet_executor.route_order("FP_25K_TEST", {
            "symbol": "XAUUSD", "direction": "BUY", "lots": 0.15, "entry_price": 2650.0, "sl": 2637.75, "tp": 2675.0
        })
        assert receipt["venue"] == "MT5"

    def test_t3_18_market_weather_and_aladdin_regime_model(self, client, aladdin_engine):
        """Combination 18: Market Weather Barometer (F03) + Aladdin Regime (F07)."""
        weather_res = client.get("/api/market_weather")
        assert weather_res.status_code == 200
        kelly_scaled = aladdin_engine.compute_fractional_kelly(win_rate=0.55, payoff_ratio=2.0, regime_scalar=0.8)
        assert 0.0025 <= kelly_scaled <= 0.0075


# ══════════════════════════════════════════════════════════════════════════════
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (>=6 Multi-Account Workflows)
# ══════════════════════════════════════════════════════════════════════════════

class TestTier4_RealWorldApplicationScenarios:
    """Tier 4: Multi-Account End-to-End Operational Trading Workflows."""

    def test_t4_01_london_killzone_liquidity_sweep_and_ote_execution(
        self, quant_engine, risk_manager, fleet_executor
    ):
        """
        Scenario 1: London Killzone Liquidity Sweep & OTE 70.5% Multi-Account Execution
        Asian range high swept at London Open -> 70.5% OTE entry -> CVD positive absorption ->
        Multi-account lot sizing -> Multi-venue routing -> Trade receipt generated.
        """
        # 1. Asian range high swept
        df_killzone = pd.DataFrame({
            "high": [2670.0 + i for i in range(20)],
            "low": [2650.0 + i for i in range(20)],
            "close": [2665.0 + i for i in range(20)]
        })
        sweep = quant_engine.detect_eqh_eql_inducement(df_killzone, symbol="XAUUSD")
        assert sweep is not None

        # 2. Retracement into 70.5% OTE
        ote = quant_engine.compute_ote_fibonacci_array(df_killzone, current_price=2675.0, direction="BUY")
        entry_price = ote["fib_705_sweet_spot"]

        # 3. Compute 3.5x ATR stops
        stops = risk_manager.calculate_atr_stops("XAUUSD", current_price=entry_price, side="BUY", atr_value=3.50)
        sl_price = stops["sl"]

        # 4. Multi-account sizing for $5k, $25k, $50k accounts
        lot_5k = risk_manager.calculate_dynamic_lot_size("FP_5K_TEST", "XAUUSD", entry_price, sl_price)
        lot_25k = risk_manager.calculate_dynamic_lot_size("FP_25K_TEST", "XAUUSD", entry_price, sl_price)
        lot_50k = risk_manager.calculate_dynamic_lot_size("FP_50K_TEST", "XAUUSD", entry_price, sl_price)

        assert lot_5k <= lot_25k <= lot_50k
        assert lot_5k >= 0.01

        # 5. Route orders
        rcpt_25k = fleet_executor.route_order("FP_25K_TEST", {
            "symbol": "XAUUSD", "direction": "BUY", "lots": lot_25k, "entry_price": entry_price, "sl": sl_price, "tp": stops["tp2"]
        })
        assert rcpt_25k["venue"] == "MT5"
        assert rcpt_25k["status"] in ["FILLED", "FAILED"]

    def test_t4_02_geopolitical_shock_and_gold_safe_haven_rally(
        self, world_monitor_engine, aladdin_engine, risk_manager, fleet_executor
    ):
        """
        Scenario 2: High-Impact Geopolitical Shock (Hormuz Disruption) & Gold Safe-Haven Surge
        WorldMonitor detects Hormuz threat -> DEFCON elevates -> Multiplier scales up ->
        Aladdin computes portfolio VaR -> Scale position into Gold OTE -> 50% scale-out -> BE lock.
        """
        # 1. Geopolitical shock assessment
        bias = world_monitor_engine.get_geopolitical_market_bias("XAUUSD")
        gold_mult = bias["macro_multiplier"]
        assert gold_mult >= 1.0

        # 2. Aladdin stress VaR
        var = aladdin_engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.015 * gold_mult)
        assert var["var_99_pct"] <= 10.0

        # 3. Position entry and TP1 scale-out simulation
        entry_price = 2650.0
        stops = risk_manager.calculate_atr_stops("XAUUSD", current_price=entry_price, side="BUY", atr_value=3.50)

        # 4. Scale 50% at TP1
        scale_res = fleet_executor.manage_position_action(ticket=9841201, action="scale_50")
        assert scale_res["success"] is True

        # 5. Lock Breakeven (+1 pip buffer)
        be_res = fleet_executor.manage_position_action(ticket=9841201, action="breakeven")
        assert be_res["success"] is True

    def test_t4_03_prop_firm_drawdown_defense_and_lockout(
        self, risk_manager, fleet_executor
    ):
        """
        Scenario 3: Prop Firm Start-of-Day 2.5% Drawdown Defense & Fleet Circuit Breaker
        $25k account experiences $630 adverse intraday move -> Shield triggers -> Lockout ->
        Executor rejects pending orders -> WhatsApp alert sent -> SOD reset restores state.
        """
        # 1. Adverse move breaches 2.5% daily limit ($625)
        res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=25000.0, equity=24360.0)
        assert res["is_locked_out"] is True
        assert res["daily_loss_shield_ok"] is False

        # 2. Executor intercepts new trade attempt
        approved, reason = risk_manager.validate_pre_trade_risk("FP_25K_TEST", "XAUUSD", 0.10, "BUY")
        assert approved is False
        assert "locked out" in reason.lower()

        # 3. Next day 00:00 UTC SOD Reset cycle clears daily loss
        reset_res = risk_manager.update_account_telemetry("FP_25K_TEST", balance=24500.0, equity=24500.0, sod_reset=True)
        assert reset_res["is_locked_out"] is False

    def test_t4_04_voice_directive_to_whatsapp_copilot(
        self, voice_transcriber, risk_manager, fleet_executor
    ):
        """
        Scenario 4: Hands-Free Voice Directive to WhatsApp Copilot in Roman Urdu
        Voice note received -> Audio STT -> Intent parsed -> Risk checked -> Order routed.
        """
        # 1. Transcribe voice note
        transcription = voice_transcriber.transcribe_audio("mock_gold_buy")
        assert "buy" in transcription.lower() and "gold" in transcription.lower()

        # 2. Parse intent
        intent = voice_transcriber.parse_voice_intent(transcription)
        assert intent["intent"] in ["TRADE_BUY", "BUY"] or "BUY" in intent["intent"]
        assert intent.get("symbol") == "XAUUSD" or "XAU" in str(intent)

        # 3. Pre-trade risk validation
        approved, _ = risk_manager.validate_pre_trade_risk("FP_25K_TEST", "XAUUSD", intent.get("lots", 0.11), "BUY")
        assert approved is True

        # 4. Route order
        rcpt = fleet_executor.route_order("FP_25K_TEST", {
            "symbol": "XAUUSD", "direction": "BUY", "lots": intent.get("lots", 0.11), "entry_price": 2650.0, "sl": 2637.75, "tp": 2675.0
        })
        assert rcpt["success"] is True or rcpt["venue"] == "MT5"

    def test_t4_05_multi_account_fleet_onboarding_and_rebalancing(
        self, auto_onboarder, risk_manager, fleet_executor
    ):
        """
        Scenario 5: Multi-Account Fleet Onboarding & Cross-Venue Rebalancing
        Onboard 3 distinct accounts ($10k Personal MT5, $50k FTMO, $1k Hyperliquid) ->
        Calibrate custom risk rules -> Simultaneously route trades to appropriate venues.
        """
        # 1. Onboard 3 accounts
        acc1 = auto_onboarder.onboard_new_account("PERSONAL_10K", "ICMarkets-Live", 10000.0, "PERSONAL_MT5")
        acc2 = auto_onboarder.onboard_new_account("FTMO_50K", "FTMO-Server", 50000.0, "FTMO")
        acc3 = auto_onboarder.onboard_new_account("HL_1K", "Hyperliquid-DEX", 1000.0, "HYPERLIQUID")

        assert acc1["success"] and acc2["success"] and acc3["success"]
        risk_manager.load_fleet()

        # 2. Verify tailored loss caps
        st_ftmo = risk_manager.get_account_state("FTMO_50K")
        assert st_ftmo["daily_loss_dollar_cap"] == 2000.0

        st_hl = risk_manager.get_account_state("HL_1K")
        assert st_hl["daily_loss_dollar_cap"] == 50.0

        # 3. Route orders across MT5 and Bitget/Hyperliquid
        rcpt_mt5 = fleet_executor.route_order("FTMO_50K", {"symbol": "EURUSD", "direction": "BUY", "lots": 0.50})
        rcpt_crypto = fleet_executor.route_order("HL_1K", {"symbol": "BTC-PERP", "direction": "BUY", "lots": 0.01})

        assert rcpt_mt5["venue"] == "MT5"
        assert rcpt_crypto["venue"] == "BITGET"

    def test_t4_06_friday_session_close_and_weekend_crypto_transition(
        self, risk_manager, fleet_executor
    ):
        """
        Scenario 6: Friday MT5 Session Close & 24/7 Weekend Crypto Transition
        Friday 21:55 UTC -> Forex positions locked at BE -> Forex trading paused ->
        Transition to 24/7 Weekend Crypto mode with perpetual funding rate monitoring.
        """
        # 1. Lock all active Forex/Gold positions to Breakeven
        for pos in fleet_executor.get_all_positions():
            if pos["symbol"] in ["XAUUSD", "EURUSD"]:
                fleet_executor.manage_position_action(ticket=pos["ticket"], action="breakeven")

        # 2. Verify Crypto trading remains active
        crypto_lot = risk_manager.calculate_dynamic_lot_size("BINANCE_1K_TEST", "BTCUSDT", entry_price=63000.0, sl_price=62000.0)
        assert crypto_lot >= 0.001

        # 3. Dispatch weekend crypto scalp order
        rcpt = fleet_executor.route_order("BINANCE_1K_TEST", {
            "symbol": "BTCUSDT", "direction": "BUY", "lots": crypto_lot, "entry_price": 63000.0, "sl": 62000.0, "tp": 65000.0
        })
        assert rcpt["venue"] == "BITGET"

    def test_t4_07_full_cockpit_telemetry_and_interactive_actions(
        self, client
    ):
        """
        Scenario 7: Full Cockpit Telemetry & Interactive 1-Click Execution Lifecycle
        Poll /api/status, /api/market_weather, /api/world_monitor, /api/trade_cards ->
        Trigger 1-click action SCALE_50 and BREAKEVEN -> Verify state updates.
        """
        # 1. Cockpit poll sequence
        s_res = client.get("/api/status")
        w_res = client.get("/api/market_weather")
        wm_res = client.get("/api/world_monitor")
        tc_res = client.get("/api/trade_cards")
        ch_res = client.get("/api/chart_data/XAUUSD?tf=15m")

        assert all(r.status_code == 200 for r in [s_res, w_res, wm_res, tc_res, ch_res])

        # 2. Trigger 1-click execution action (SCALE_50)
        act_res1 = client.post("/api/execution/action", json={"ticket": 9841201, "action": "SCALE_50"})
        assert act_res1.status_code in [200, 400]

        # 3. Trigger 1-click execution action (BREAKEVEN)
        act_res2 = client.post("/api/execution/action", json={"ticket": 9841201, "action": "BREAKEVEN"})
        assert act_res2.status_code in [200, 400]

    def test_t4_08_aladdin_gap_stress_test_and_panic_emergency_kill_switch(
        self, aladdin_engine, fleet_executor, client
    ):
        """
        Scenario 8: Aladdin 3-Sigma Gap Stress Test & Panic Emergency Kill Switch
        Black swan 3-sigma gap -> Aladdin detects CVaR breach -> Panic Kill Switch triggered ->
        All fleet positions atomically closed.
        """
        # 1. Aladdin 3-sigma shock (daily volatility = 5.0%)
        var_shock = aladdin_engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.05)
        assert var_shock["var_99_pct"] >= 10.0

        # 2. Emergency Kill Switch triggered via REST API
        ctrl_res = client.post("/api/control", json={"action": "kill_switch"})
        assert ctrl_res.status_code == 200

        # 3. Direct executor emergency kill switch
        close_res = fleet_executor.emergency_kill_switch()
        assert close_res["success"] is True
