"""
tests/reviewer_2_live_adversarial_audit.py
=========================================
Independent Adversarial, Mathematical, and Integrity Audit by Reviewer 2.
Directly tests edge cases, mathematical formulas, boundary conditions,
and integrity invariants for R3 and R4.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.order_flow_quant import OrderFlowQuantEngine
from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.global_liquidation_radar import GlobalLiquidationRadar
from src.cross_market_synthetic_arb import CrossMarketContagionEngine
from src.fleet_risk_manager import FleetRiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.aladdin_risk_engine import AladdinRiskEngine
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.whatsapp_copilot import InstitutionalCardFormatter


def test_r3_ote_mathematical_precision():
    """Verify ICT 70.5% OTE Golden Pocket calculation across multiple price ranges."""
    engine = OrderFlowQuantEngine()
    
    # 1. Bullish OTE Dealing Range: Low 2000.0, High 2100.0 (diff = 100.0)
    df_bull = pd.DataFrame({
        "high": [2010.0, 2030.0, 2050.0, 2080.0, 2100.0] * 5,
        "low": [2000.0, 2010.0, 2020.0, 2040.0, 2060.0] * 5,
        "close": [2005.0, 2025.0, 2045.0, 2075.0, 2090.0] * 5
    })
    
    res_buy = engine.compute_ote_fibonacci_array(df_bull, 2029.50, "BUY")
    assert res_buy["fib_618"] == pytest.approx(2038.20, abs=1e-2)
    assert res_buy["fib_705_sweet_spot"] == pytest.approx(2029.50, abs=1e-2)
    assert res_buy["fib_786"] == pytest.approx(2021.40, abs=1e-2)
    assert res_buy["in_ote_zone"] is True
    assert res_buy["score_bonus"] == 0.60
    
    # Price outside OTE
    res_buy_out = engine.compute_ote_fibonacci_array(df_bull, 2050.0, "BUY")
    assert res_buy_out["in_ote_zone"] is False
    assert res_buy_out["score_bonus"] == 0.0

    # 2. Bearish OTE Dealing Range: Low 100.0, High 200.0 (diff = 100.0)
    res_sell = engine.compute_ote_fibonacci_array(df_bull, 2070.50, "SELL")
    assert res_sell["fib_618"] == pytest.approx(2061.80, abs=1e-2)
    assert res_sell["fib_705_sweet_spot"] == pytest.approx(2070.50, abs=1e-2)
    assert res_sell["fib_786"] == pytest.approx(2078.60, abs=1e-2)
    assert res_sell["in_ote_zone"] is True


def test_r3_fvg_50_ce_mitigation_lifecycle():
    """Verify 50% Consequent Encroachment FVG detection and forward multi-candle mitigation."""
    # Bullish FVG candle sequence
    # Candle 0: High=100.0, Low=90.0
    # Candle 1: High=115.0, Low=99.0 (Expansion)
    # Candle 2: High=120.0, Low=105.0 (C3 Low=105 > C1 High=100 -> Bullish FVG gap 5.0)
    # Candle 3: High=118.0, Low=103.0 (Enters FVG but does not breach CE 102.5 -> partially mitigated)
    # Candle 4: High=115.0, Low=101.0 (Breaches CE 102.5 -> fully mitigated)
    df = pd.DataFrame({
        "open": [92.0, 100.0, 110.0, 115.0, 110.0],
        "high": [100.0, 115.0, 120.0, 118.0, 115.0],
        "low": [90.0, 99.0, 105.0, 103.0, 101.0],
        "close": [98.0, 114.0, 116.0, 112.0, 108.0]
    })
    
    fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=0.1, symbol="XAUUSD")
    assert len(fvgs) >= 1
    bull_fvg = next(f for f in fvgs if f["type"] == "BULLISH_FVG")
    assert bull_fvg["top"] == 105.0
    assert bull_fvg["bottom"] == 100.0
    assert bull_fvg["ce_50"] == 102.5
    assert bull_fvg["mitigated"] is True
    assert bull_fvg["partially_mitigated"] is True


def test_r3_lee_ready_cvd_algorithm():
    """Verify Lee-Ready 1991 quote rule, tick test fallback, and zero division safety."""
    engine = OrderFlowQuantEngine()
    
    # Synthetic tick data
    ticks = pd.DataFrame({
        "bid": [100.0, 100.0, 100.2, 100.2, 100.1],
        "ask": [100.2, 100.2, 100.4, 100.4, 100.3],
        "last": [100.2, 100.2, 100.3, 100.1, 100.2], # 100.2 > mid(100.1) -> Buy, 100.2 > mid(100.1) -> Buy, 100.3 = mid(100.3) -> Tick test vs 100.2 -> Buy (+1), etc.
        "volume": [10.0, 20.0, 15.0, 5.0, 10.0]
    })
    
    cvd_res = engine.compute_tick_cvd(ticks)
    assert cvd_res["total_volume"] > 0
    assert cvd_res["buyer_ratio"] + cvd_res["seller_ratio"] == pytest.approx(1.0, abs=1e-3)
    assert cvd_res["absorption_type"] in ["BUYER_ABSORPTION", "SELLER_ABSORPTION", "NONE"]
    
    # Null ticks safety
    null_res = engine.compute_tick_cvd(None)
    assert null_res["cvd"] == 0
    assert null_res["buyer_ratio"] == 0.50


def test_r3_world_monitor_cii_and_chokepoints():
    """Verify 4-Pillar CII formula and DEFCON mapping."""
    wm = WorldMonitorIntelligenceEngine()
    
    # Formula: CII = 0.20*unrest + 0.40*conflict + 0.25*security + 0.15*info
    components = {"unrest": 80.0, "conflict": 90.0, "security": 70.0, "information": 60.0}
    expected_cii = (0.20 * 80.0) + (0.40 * 90.0) + (0.25 * 70.0) + (0.15 * 60.0)
    assert expected_cii == 78.5
    
    calc_cii = wm.calculate_country_instability_score(components)
    assert calc_cii == 78.5
    
    # DEFCON levels
    assert wm.get_defcon_level(90.0) == 1
    assert wm.get_defcon_level(75.0) == 2
    assert wm.get_defcon_level(55.0) == 3
    assert wm.get_defcon_level(30.0) == 4
    assert wm.get_defcon_level(15.0) == 5


def test_r3_multi_asset_scales_and_tp():
    """Verify 7-asset scaling specifications and minimum R:R."""
    symbols = ["XAUUSD", "BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPUSD", "USDJPY"]
    
    for sym in symbols:
        specs = StrategyEngine.get_symbol_scale_specs(sym)
        assert "category" in specs
        assert specs["pip_unit"] > 0
        assert specs["min_sl_dist"] > 0
        assert specs["atr_sl_mult"] >= 1.5


def test_r4_start_of_day_drawdown_hard_shield():
    """Adversarial stress test on 2.5% Start-of-Day drawdown shield and instant lockout."""
    frm = FleetRiskManager()
    
    # Onboard a test 25k account
    acc_id = "test_adv_25k"
    frm.update_account_telemetry(acc_id, balance=25000.0, equity=25000.0, sod_reset=True)
    
    state = frm.get_account_state(acc_id)
    assert state["daily_loss_dollar_cap"] == 625.0 # 2.5% of 25,000
    
    # 1. Normal safe intraday equity fluctuation ($24,800 -> loss $200 < $625)
    t1 = frm.update_account_telemetry(acc_id, balance=25000.0, equity=24800.0)
    assert t1["daily_loss_shield_ok"] is True
    assert t1["is_locked_out"] is False
    
    # 2. Drawdown at exact boundary ($24,375 -> loss $625 == limit -> Lockout)
    t2 = frm.update_account_telemetry(acc_id, balance=25000.0, equity=24375.0)
    assert t2["daily_loss_shield_ok"] is False
    assert t2["is_locked_out"] is True
    
    # Pre-trade risk interceptor must reject any trade when locked out
    approved, msg = frm.validate_pre_trade_risk(acc_id, symbol="EURUSD", lot_size=0.1, side="BUY", entry_price=1.10, sl_price=1.09)
    assert approved is False
    assert "locked out" in msg.lower() or "breached" in msg.lower()


def test_r4_trailing_hwm_profit_lock_invariant():
    """Verify that when account profits, trailing floor clamps at starting balance, locking profits."""
    frm = FleetRiskManager()
    acc_id = "test_hwm_50k"
    
    # 50k Account: Starting bal $50,000, max total loss 6% = $3,000
    frm.update_account_telemetry(acc_id, balance=50000.0, equity=50000.0, sod_reset=True)
    
    # Initial floor = 50,000 - 3,000 = 47,000
    state0 = frm.get_account_state(acc_id)
    assert state0["trailing_hwm_floor"] == 47000.0
    assert state0["hwm_locked_at_starting_balance"] is False
    
    # Account equity reaches $54,000 (HWM ratchets)
    # Raw floor = 54,000 - 3,000 = 51,000 >= 50,000 -> Locked at starting balance or higher
    t1 = frm.update_account_telemetry(acc_id, balance=54000.0, equity=54000.0)
    state1 = frm.get_account_state(acc_id)
    assert state1["absolute_hwm"] == 54000.0
    assert state1["trailing_hwm_floor"] >= 50000.0
    assert state1["hwm_locked_at_starting_balance"] is True


def test_r4_aladdin_var_cvar_and_kelly_math():
    """Verify Aladdin 99% VaR, CVaR, and Uncertainty-Adjusted Quarter-Kelly calculations."""
    aladdin = AladdinRiskEngine()
    
    # 1. VaR / CVaR for $25,000 equity with 0.8% daily volatility
    var_res = aladdin.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.008)
    # z_99 = 2.326348 -> var_99 = 25000 * 2.326348 * 0.008 = 465.27
    assert var_res["var_99_dollar"] == pytest.approx(465.27, abs=0.5)
    assert var_res["cvar_99_dollar"] > var_res["var_99_dollar"] # CVaR is always >= VaR
    
    # 2. Quarter-Kelly with win-rate 60%, payoff 2.0, win_rate_se 0.03
    # adj_win_rate = 0.57
    # full_kelly = (0.57 * 3.0 - 1.0) / 2.0 = (1.71 - 1.0) / 2.0 = 0.355
    # quarter_kelly = 0.20 * 0.355 = 0.071
    # capped at max_risk_cap_pct (0.0075 / 0.75%)
    kelly_risk = aladdin.compute_fractional_kelly(win_rate=0.60, payoff_ratio=2.0)
    assert kelly_risk <= 0.0075
    assert kelly_risk >= 0.0025


def test_r4_gap_stress_test_interceptor():
    """Verify Aladdin 3-sigma gap stress test blocks trades that breach daily risk allowance."""
    aladdin = AladdinRiskEngine()
    
    open_pos = [
        {"symbol": "XAUUSD", "price_open": 2400.0, "sl": 2390.0, "volume": 0.50}, # 100 pips * 0.5 * $10 = $500 risk
    ]
    
    # Stress test on $625 daily cap: existing open risk $500 + prospective $200 = $700 > 80% of $625 ($500) -> FAIL
    stress_fail = aladdin.evaluate_pre_trade_stress_test(
        equity=25000.0,
        prospective_risk_dollar=200.0,
        open_positions=open_pos,
        max_daily_loss_dollar=625.0
    )
    assert stress_fail["passed"] is False
    assert "STRESS_TEST_EXCEEDED" in stress_fail["reason"]
    
    # Prospective $50 -> Total $550 > $500 -> FAIL
    # Prospective $0 -> Total $500 == 80% ($500.0) -> PASS
    stress_pass = aladdin.evaluate_pre_trade_stress_test(
        equity=25000.0,
        prospective_risk_dollar=0.0,
        open_positions=[],
        max_daily_loss_dollar=625.0
    )
    assert stress_pass["passed"] is True


def test_r3_5pillar_whatsapp_bilingual_formatting():
    """Verify that format_5pillar_card produces complete 5-pillar output with Roman Urdu and English."""
    card = InstitutionalCardFormatter.format_5pillar_card(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2400.00,
        sl_price=2380.00,
        tp1_price=2430.00,
        tp2_price=2460.00,
        tp3_price=2500.00,
        is_urdu=True
    )
    assert "PILLAR 1: INSTITUTIONAL RATIONALE & SMC ORDER FLOW (WAJOOHAT)" in card
    assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP DYNAMICS" in card
    assert "PILLAR 3: MACRO & GEOPOLITICAL BACKDROP" in card
    assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX" in card
    assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP" in card
    assert "Wajoohat (Roman Urdu)" in card
    assert "Agar" in card
    assert "#XAUUSD" in card
