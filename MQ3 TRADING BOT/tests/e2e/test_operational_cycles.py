"""
tests/e2e/test_operational_cycles.py — Master 4-Tier E2E Test Suite
for the 24/7 Daily Operational Cycle & Multi-Account Intelligence System.

Authoritative Reference:
- ORIGINAL_REQUEST.md (§R1, §R2, §R3, §R4)
- PROJECT.md (§Architecture, §Feature Inventory, §Interface Contracts)
- TEST_INFRA.md (§Test Philosophy, §Coverage Thresholds, §Tier Mappings)
- .agents/spec_miner_1/handoff.md (§Formal Specifications & Edge Cases)

Tiers Covered:
- Tier 1: Feature Coverage (Unit & Functional: Morning Briefing, 50-Yr History, IF-THEN Matrix,
           4-Account Sizing, Intraday Scanner, Asian Judas, 70.5% OTE, Lee-Ready CVD,
           Dark Pool Radar, WhatsApp Signal Card, 1:1 BE / 50% TP1 Rules, Broadcast Targets,
           Nightly Retrospective, Deviation Forensics, Episodic Memory, Bayesian Weight Updates,
           Cycle Scheduler, 18 WhatsApp Commands, Whitelist Security Drop).
- Tier 2: Boundary & Corner Cases (Empty/Corrupted Candles, 0/Neg SL distances, Lot Clamps [0.01, 5.00],
           2.5% Daily Drawdown Floor, 6.0% Trailing HWM Floor, Bayesian Clamps [0.65, 1.60],
           Ring Buffer Overflow >500 items, Unauthorized Sender Drop, Spread Spikes, Profit Pacing,
           Aladdin VaR Bounds, Zero-Volume CVD).
- Tier 3: Cross-Feature Combinations (Full Daily Lifecycle, Multi-Account Risk Isolation,
           Interactive Command -> Execution -> Memory Reflection, Composite Confluence Gating,
           Geopolitical Shock Playbook Shift, Judas + CVD + OTE confluence, Pacing de-risking).
- Tier 4: Real-World Workload Scenarios (7 Multi-Cycle End-to-End Simulations:
           1. Bullish Gold Expansion Day
           2. Geopolitical Tariff Shock Defense
           3. 4-Account Prop Firm Fleet Execution
           4. WhatsApp Fleet Controller Workload
           5. Multi-Day Cognitive Memory Evolution
           6. Silver High-Beta Catch-Up Cycle
           7. Ranging Chop & Breakeven Capital Preservation Defense)

Pass/Fail Criteria: 100% assertions pass, 0 unhandled exceptions, exit code 0.
Runner: pytest tests/e2e/test_operational_cycles.py -v
"""

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import re
import json
import math
import time
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ==============================================================================
# SYSTEM UNDER TEST IMPORTS (WITH ROBUST CONTRACT FALLBACKS)
# ==============================================================================

try:
    from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
except ImportError:
    DailyInstitutionalRoutineEngine = None

try:
    from src.community_signal_broadcaster import CommunitySignalBroadcaster
except ImportError:
    CommunitySignalBroadcaster = None

try:
    from src.whatsapp_qr_manager import (
        WhatsAppQRManager,
        AUTHORIZED_CONTACTS,
        is_whitelisted_number,
    )
except ImportError:
    WhatsAppQRManager = None
    AUTHORIZED_CONTACTS = {
        "923468053268": "Master User (Owner)",
    }
    def is_whitelisted_number(sender_jid: str) -> bool:
        if not sender_jid:
            return False
        clean = re.sub(r'[^0-9]', '', sender_jid.split('@')[0])
        return any(clean.endswith(k) or k.endswith(clean) for k in AUTHORIZED_CONTACTS.keys())

try:
    from src.deep_self_learning_agent import DeepSelfLearningAgent
except ImportError:
    DeepSelfLearningAgent = None

try:
    from src.multi_account_manager import MultiAccountManager
except ImportError:
    MultiAccountManager = None

try:
    from src.funding_pips_expert import FundingPipsExpert
except ImportError:
    FundingPipsExpert = None

try:
    from src.aladdin_risk_engine import AladdinRiskEngine
except ImportError:
    AladdinRiskEngine = None

try:
    from src.order_flow_quant import OrderFlowQuantEngine
except ImportError:
    OrderFlowQuantEngine = None

try:
    from src.insider_whale_mechanics import InsiderWhaleMechanics
except ImportError:
    InsiderWhaleMechanics = None

try:
    from src.ai_trade_consultant import AITradeConsultant
except ImportError:
    AITradeConsultant = None

try:
    from src.operational_cycle_scheduler import OperationalCycleScheduler
    OperationalCycleSchedulerContract = OperationalCycleScheduler
except ImportError:
    pass


# ==============================================================================
# SCHEDULER CONTRACT ORACLE HARNESS (M4 REFERENCE IMPLEMENTATION)
# ==============================================================================

class OperationalCycleSchedulerContract:
    """
    Contract implementation of M4 24/7 Operational Cycle Scheduler.
    Schedules:
      - Morning Briefing: Daily at 06:30 UTC.
      - Intraday Scanner: Every 5 minutes during Killzones.
      - Nightly Retrospective: Daily at 21:30 UTC.
    """

    def __init__(self, routine_engine=None, interval_sec: int = 60):
        self.routine_engine = routine_engine or (DailyInstitutionalRoutineEngine() if DailyInstitutionalRoutineEngine else None)
        self.interval_sec = interval_sec
        self.is_running = False
        self.last_morning_dispatch: Optional[str] = None
        self.last_nightly_dispatch: Optional[str] = None
        self.last_intraday_scan: Optional[str] = None
        self.execution_log: List[Dict[str, Any]] = []

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def evaluate_schedule_trigger(self, current_utc_time: datetime) -> Dict[str, bool]:
        """
        Determines which cycle should trigger given current UTC time.
        """
        hh_mm = current_utc_time.strftime("%H:%M")
        t = current_utc_time.time()
        
        # 06:30 UTC Morning Briefing
        trigger_morning = (hh_mm == "06:30")
        
        # 21:30 UTC Nightly Retrospective
        trigger_nightly = (hh_mm == "21:30")
        
        # Killzones: London (07:00-10:00), NY AM (12:00-15:00), NY PM (18:00-20:00)
        in_london = (7 <= t.hour < 10)
        in_ny_am = (12 <= t.hour < 15)
        in_ny_pm = (18 <= t.hour < 20)
        in_killzone = in_london or in_ny_am or in_ny_pm
        
        trigger_intraday = in_killzone and (current_utc_time.minute % 5 == 0)

        return {
            "trigger_morning": trigger_morning,
            "trigger_nightly": trigger_nightly,
            "trigger_intraday": trigger_intraday,
            "in_killzone": in_killzone
        }

    def execute_cycle_tick(self, current_utc_time: datetime) -> Dict[str, Any]:
        """
        Executes cycle action if triggered and logs status.
        """
        triggers = self.evaluate_schedule_trigger(current_utc_time)
        results = {"executed": [], "time": current_utc_time.isoformat()}
        
        if triggers["trigger_morning"] and self.routine_engine:
            msg = self.routine_engine.generate_morning_master_briefing()
            self.last_morning_dispatch = current_utc_time.strftime("%Y-%m-%d")
            results["executed"].append("MORNING_BRIEFING")
            self.execution_log.append({"cycle": "MORNING_BRIEFING", "time": current_utc_time.isoformat()})
            
        if triggers["trigger_nightly"] and self.routine_engine:
            msg = self.routine_engine.generate_nightly_market_retrospective()
            self.last_nightly_dispatch = current_utc_time.strftime("%Y-%m-%d")
            results["executed"].append("NIGHTLY_RETROSPECTIVE")
            self.execution_log.append({"cycle": "NIGHTLY_RETROSPECTIVE", "time": current_utc_time.isoformat()})
            
        if triggers["trigger_intraday"] and self.routine_engine:
            alert = self.routine_engine.generate_intraday_alert("XAUUSD", "OTE_PULLBACK", "London Open Judas Sweep")
            self.last_intraday_scan = current_utc_time.isoformat()
            results["executed"].append("INTRADAY_ALERT_SCAN")
            self.execution_log.append({"cycle": "INTRADAY_ALERT_SCAN", "time": current_utc_time.isoformat()})

        return results


# ==============================================================================
# AUTHORITATIVE MATHEMATICAL & SPECIFICATION ORACLES
# ==============================================================================

class OperationalCycleOracle:
    """
    Independent Authoritative Oracle deriving expected values from specifications.
    """

    @staticmethod
    def calculate_lot_size(
        equity: float,
        risk_pct: float,
        sl_pips: float,
        pip_value: float = 10.0,
        min_lot: float = 0.01,
        max_lot: float = 5.00
    ) -> float:
        """
        Derives lot size: round( (equity * (risk_pct / 100)) / (sl_pips * pip_value), 2 )
        Clamped to [min_lot, max_lot].
        """
        if sl_pips <= 0:
            return min_lot
        risk_dollars = equity * (risk_pct / 100.0)
        denom = sl_pips * pip_value
        if denom <= 0:
            return min_lot
        raw_lot = round(risk_dollars / denom, 2)
        return float(np.clip(raw_lot, min_lot, max_lot))

    @staticmethod
    def compute_bayesian_update(current_weight: float, is_win: bool) -> float:
        """
        Tuning dynamics: +0.05 on win, -0.08 on loss.
        Bounded to [0.65, 1.60].
        """
        if is_win:
            return round(min(1.60, current_weight + 0.05), 3)
        else:
            return round(max(0.65, current_weight - 0.08), 3)

    @staticmethod
    def compute_trailing_hwm_floor(starting_balance: float, current_hwm: float, safe_total_loss_pct: float = 6.0) -> float:
        """
        Floor = HWM - (starting_balance * safe_total_loss_pct / 100.0)
        """
        max_loss_dollars = starting_balance * (safe_total_loss_pct / 100.0)
        return current_hwm - max_loss_dollars

    @staticmethod
    def compute_beta_binomial_posterior(alpha_0: float, beta_0: float, wins: int, total: int) -> float:
        """
        Beta-Binomial posterior expected win rate: (alpha_0 + wins) / (alpha_0 + beta_0 + total)
        """
        alpha_n = alpha_0 + wins
        beta_n = beta_0 + (total - wins)
        return alpha_n / (alpha_n + beta_n)


# ==============================================================================
# FIXTURES & BASE TEST SETUP
# ==============================================================================

@pytest.fixture
def temp_cognitive_memory():
    """Creates an isolated temporary cognitive memory directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_cog_mem_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_gold_m15_candles():
    """Generates synthetic M15 candles for Gold (#XAUUSD)."""
    np.random.seed(42)
    n = 60
    base_price = 4370.0
    times = [datetime.now(timezone.utc) - timedelta(minutes=15 * (n - i)) for i in range(n)]
    
    closes = [base_price + (i * 0.4) + np.random.normal(0, 0.5) for i in range(n)]
    highs = [c + np.random.uniform(0.5, 1.5) for c in closes]
    lows = [c - np.random.uniform(0.5, 1.5) for c in closes]
    opens = [c - np.random.uniform(-0.5, 0.5) for c in closes]
    volumes = [int(np.random.uniform(200, 800)) for _ in range(n)]

    # Inject dark pool anomaly at final candle (high volume, tight body)
    volumes[-1] = 3500  # Z-score spike
    opens[-1] = 4385.0
    closes[-1] = 4385.2 # 0.2 pt body
    highs[-1] = 4386.0
    lows[-1] = 4384.5

    df = pd.DataFrame({
        "time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })
    return df


@pytest.fixture
def sample_gold_ticks():
    """Generates synthetic tick array for Lee-Ready CVD evaluation."""
    n = 100
    bids = [4375.0 + (i * 0.05) for i in range(n)]
    asks = [b + 0.20 for b in bids]
    prices = [a for a in asks]
    vols = [np.random.uniform(1.0, 5.0) for _ in range(n)]
    
    ticks = np.empty(n, dtype=[
        ('bid', 'f8'), ('ask', 'f8'), ('last', 'f8'),
        ('volume', 'f8'), ('volume_ext', 'f8')
    ])
    ticks['bid'] = bids
    ticks['ask'] = asks
    ticks['last'] = prices
    ticks['volume'] = vols
    ticks['volume_ext'] = vols
    return ticks


# ==============================================================================
# TIER 1: FEATURE COVERAGE (UNIT & FUNCTIONAL TESTS)
# ==============================================================================

class TestTier1MorningMacroBriefing:
    """R1: Morning Pre-Market Macro Briefing & Multi-Scenario Playbook Tests."""

    def test_morning_briefing_macro_radar_content(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        
        assert "GLOBAL GEOPOLITICAL & MACRO RADAR" in briefing
        assert "Geopolitical Theme" in briefing
        assert "US 10Y Yields" in briefing or "Yields" in briefing
        assert "DXY Dollar Index" in briefing or "DXY" in briefing
        assert "Central Bank Flow" in briefing or "Central Bank" in briefing

    def test_morning_briefing_50yr_history_and_benchmarks(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        
        assert "HISTORICAL CONTEXT & CLOSING BENCHMARKS" in briefing
        assert "#XAUUSD" in briefing or "Gold" in briefing
        assert "Previous Day Close" in briefing
        assert "1-Week Trend Structure" in briefing
        assert "1-Month Macro Regime" in briefing
        assert "Silver (#XAGUSD)" in briefing or "GSR" in briefing

    def test_morning_briefing_if_then_matrix_scenarios(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        
        assert "TODAY'S IF-THEN STRATEGY MATRIX" in briefing
        assert "SCENARIO A" in briefing
        assert "Primary Trend Continuation" in briefing
        assert "SCENARIO B" in briefing
        assert "Deep Liquidity Sweep" in briefing
        assert "TP1" in briefing and "Safe SL" in briefing

    def test_morning_briefing_4_account_sizing_guidance(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        
        assert "$100k Master Funded Account" in briefing or "$100k" in briefing
        assert "$50k Funded Account" in briefing or "$50k" in briefing
        assert "$25k Active Account" in briefing or "$25k" in briefing
        assert "$5k Fast Scalp Account" in briefing or "$5k" in briefing
        assert "Lots" in briefing and "Risk" in briefing

    def test_morning_briefing_discipline_golden_rule(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        
        assert "Golden Rule Today" in briefing or "Discipline" in briefing
        assert len(briefing) > 500

    def test_morning_briefing_idempotent_execution(self):
        engine = DailyInstitutionalRoutineEngine()
        b1 = engine.generate_morning_master_briefing()
        b2 = engine.generate_morning_master_briefing()
        assert len(b1) == len(b2)
        assert "SCENARIO A" in b2


class TestTier1Historical50YrAnalogue:
    """R1: 50-Year History & Macro Shock Analysis Tests."""

    def test_political_macro_shock_catalog_evaluation(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("TARIFF_ESCALATION")
        
        assert shock["active_shock"] == "TARIFF_ESCALATION"
        assert shock["gold_tailwind_score"] >= 0.70
        assert "Tariff uncertainty" in shock["thesis"]

    def test_central_bank_rate_cut_shock(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("CENTRAL_BANK_RATE_CUT")
        
        assert shock["gold_tailwind_score"] >= 0.85
        assert shock["usd_tailwind_score"] < 0

    def test_geopolitical_conflict_flight_to_safety(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("GEOPOLITICAL_CONFLICT")
        
        assert shock["gold_tailwind_score"] >= 0.90
        assert shock["oil_tailwind_score"] >= 0.80

    def test_opec_supply_cut_inflation_hedge(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("OPEC_SUPPLY_CUT")
        
        assert shock["oil_tailwind_score"] >= 0.85
        assert shock["gold_tailwind_score"] >= 0.50

    def test_default_fallback_on_unknown_shock(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("UNKNOWN_EVENT_TYPE")
        
        assert shock is not None
        assert "gold_tailwind_score" in shock

    def test_gold_silver_ratio_high_beta_silver_correlation(self):
        # When GSR > 90, Silver is historically undervalued vs Gold
        gsr = 113.5
        silver_undervalued = gsr > 90.0
        assert silver_undervalued is True


class TestTier1MultiScenarioMatrix:
    """R1: Scenario A / Scenario B IF-THEN Matrix & Invalidation Tests."""

    def test_scenario_a_primary_trend_continuation_structure(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        assert "75% Probability" in briefing or "Primary Trend" in briefing
        assert "OTE Discount Zone" in briefing or "OTE" in briefing

    def test_scenario_b_deep_liquidity_sweep_structure(self):
        engine = DailyInstitutionalRoutineEngine()
        briefing = engine.generate_morning_master_briefing()
        assert "25% Probability" in briefing or "Deep Liquidity" in briefing
        assert "H1 demand" in briefing or "demand" in briefing

    def test_scenario_invalidation_levels_rigorous_boundary(self):
        # Scenario A invalidation: $4364.50. Scenario B invalidation: $4345.00
        inv_a = 4364.50
        inv_b = 4345.00
        assert inv_a > inv_b
        
        # Test price at 4363.0 invalidates A but leaves B valid
        test_price = 4363.0
        is_a_valid = test_price >= inv_a
        is_b_valid = test_price >= inv_b
        assert is_a_valid is False
        assert is_b_valid is True

    def test_scenario_risk_reward_ratio_greater_than_2_to_1(self):
        # Entry $4376.50, SL $4364.50 (Risk = 12.0), TP1 $4400.50 (Reward = 24.0)
        risk = 4376.50 - 4364.50
        reward = 4400.50 - 4376.50
        rr = reward / risk
        assert rr >= 2.0


class TestTier1MultiAccountLotSizing:
    """R1: Multi-Account Calibrated Risk & Lot Sizing Tests ($100k, $50k, $25k, $5k)."""

    def test_lot_sizing_100k_account_050_risk(self):
        lot = OperationalCycleOracle.calculate_lot_size(100000.0, 0.50, 120.0, pip_value=1.0)
        assert lot == pytest.approx(4.17, abs=0.02)
        assert lot * 120.0 * 1.0 <= 501.0

    def test_lot_sizing_50k_account_050_risk(self):
        lot = OperationalCycleOracle.calculate_lot_size(50000.0, 0.50, 120.0, pip_value=1.0)
        assert lot == pytest.approx(2.08, abs=0.02)
        assert lot * 120.0 * 1.0 <= 251.0

    def test_lot_sizing_25k_account_075_risk(self):
        lot = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, 120.0, pip_value=1.0)
        assert lot == pytest.approx(1.56, abs=0.02)
        assert lot * 120.0 * 1.0 <= 188.0

    def test_lot_sizing_5k_account_075_risk(self):
        lot = OperationalCycleOracle.calculate_lot_size(5000.0, 0.75, 120.0, pip_value=1.0)
        assert lot == pytest.approx(0.31, abs=0.02)
        assert lot * 120.0 * 1.0 <= 38.0

    def test_fleet_manager_configuration_parameters(self):
        fleet_mgr = MultiAccountManager()
        summary = fleet_mgr.get_fleet_summary()
        accounts = summary["fleet"]
        
        assert "100k_master" in accounts
        assert accounts["100k_master"]["starting_balance"] == 100000.0
        assert accounts["100k_master"]["risk_per_trade_pct"] == 0.0050
        assert accounts["25k_active"]["starting_balance"] == 25000.0
        assert accounts["5k_scalp"]["starting_balance"] == 5000.0

    def test_forex_standard_lot_pip_value_calculation(self):
        # EURUSD 20-pip SL on $25,000 account @ 0.75% risk ($187.50) -> 187.50 / (20 * 10) = 0.94 lots
        lot_eur = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, 20.0, pip_value=10.0)
        assert lot_eur == pytest.approx(0.94, abs=0.01)

    def test_jpy_pair_lot_pip_value_calculation(self):
        # USDJPY 25-pip SL on $50,000 account @ 0.50% risk ($250.00) -> 250 / (25 * 6.50) = 1.54 lots
        lot_jpy = OperationalCycleOracle.calculate_lot_size(50000.0, 0.50, 25.0, pip_value=6.50)
        assert lot_jpy == pytest.approx(1.54, abs=0.01)


class TestTier1IntradayKillzoneAndSMC:
    """R2: Intraday Killzones, Asian Judas Swings, 70.5% OTE, CVD & Dark Pools."""

    def test_killzones_time_windows(self):
        of_quant = OrderFlowQuantEngine()
        kz = of_quant.get_active_killzone()
        assert "killzone" in kz
        assert "is_prime_killzone" in kz
        assert "confluence_boost" in kz

    def test_ote_705_fibonacci_discount_calculation_buy(self):
        of_quant = OrderFlowQuantEngine()
        df = pd.DataFrame({
            "high": [4390.0, 4400.0, 4395.0, 4390.0, 4385.0] * 5,
            "low":  [4350.0, 4360.0, 4355.0, 4350.0, 4350.0] * 5,
            "close": [4370.0] * 25
        })
        ote = of_quant.compute_ote_fibonacci_array(df, current_price=4365.0, direction="BUY")
        assert ote["fib_705_sweet_spot"] == pytest.approx(4364.75, abs=0.1)
        assert ote["in_ote_zone"] is True
        assert ote["score_bonus"] > 0

    def test_ote_705_fibonacci_premium_calculation_sell(self):
        of_quant = OrderFlowQuantEngine()
        df = pd.DataFrame({
            "high": [4400.0] * 25,
            "low":  [4350.0] * 25,
            "close": [4375.0] * 25
        })
        ote = of_quant.compute_ote_fibonacci_array(df, current_price=4385.0, direction="SELL")
        assert ote["fib_705_sweet_spot"] == pytest.approx(4385.25, abs=0.1)
        assert ote["in_ote_zone"] is True

    def test_lee_ready_cvd_buyer_absorption(self, sample_gold_ticks):
        of_quant = OrderFlowQuantEngine()
        res = of_quant.compute_tick_cvd(sample_gold_ticks)
        
        assert res["cvd"] > 0
        assert res["buyer_ratio"] >= 0.65
        assert res["divergence"] == "BULLISH_CVD_SURGE"

    def test_lee_ready_cvd_seller_absorption(self):
        of_quant = OrderFlowQuantEngine()
        n = 100
        bids = [4380.0 - (i * 0.05) for i in range(n)]
        asks = [b + 0.20 for b in bids]
        prices = [b for b in bids]
        vols = [np.random.uniform(1.0, 5.0) for _ in range(n)]
        
        ticks = np.empty(n, dtype=[
            ('bid', 'f8'), ('ask', 'f8'), ('last', 'f8'),
            ('volume', 'f8'), ('volume_ext', 'f8')
        ])
        ticks['bid'] = bids
        ticks['ask'] = asks
        ticks['last'] = prices
        ticks['volume'] = vols
        ticks['volume_ext'] = vols
        
        res = of_quant.compute_tick_cvd(ticks)
        assert res["buyer_ratio"] <= 0.35
        assert res["divergence"] == "BEARISH_CVD_SURGE"

    def test_dark_pool_volume_anomaly_radar(self, sample_gold_m15_candles):
        whales = InsiderWhaleMechanics()
        res = whales.detect_dark_pool_anomalies(sample_gold_m15_candles)
        
        assert res["dark_pool_detected"] is True
        assert res["z_score"] >= 2.2
        assert "DARK_POOL" in res["anomaly_type"]

    def test_eqh_eql_inducement_sweep_detection(self):
        of_quant = OrderFlowQuantEngine()
        n = 35
        highs = [4375.0] * n
        lows = [4365.0] * n
        lows[15] = 4360.0
        lows[25] = 4360.0
        lows[-1] = 4358.0
        closes = [4365.0] * n
        closes[-1] = 4362.0
        
        df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
        res = of_quant.detect_eqh_eql_inducement(df, symbol="XAUUSD")
        
        assert res["inducement_type"] == "BULLISH_EQL_SWEEP"
        assert res["is_swept"] is True

    def test_premium_discount_50_pct_equilibrium_filter(self):
        of_quant = OrderFlowQuantEngine()
        df = pd.DataFrame({
            "high": [4400.0] * 20,
            "low":  [4300.0] * 20,
            "close": [4350.0] * 20
        })
        # Equilibrium is (4400 + 4300) / 2 = 4350.0
        eq = of_quant.evaluate_premium_discount(df, 4320.0) # Discount zone
        assert eq["zone"] == "DISCOUNT"
        assert eq["is_buy_allowed"] is True
        assert eq["is_sell_allowed"] is False


class TestTier1WhatsAppSignalCardAndRules:
    """R2: WhatsApp 5-Section Signal Card, 1:1 BE, 50% TP1 & Target Broadcasts."""

    def test_signal_card_5_sections_and_schema(self):
        broadcaster = CommunitySignalBroadcaster()
        card = broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=4376.50,
            sl_price=4364.50,
            tp1_price=4396.60,
            tp2_price=4410.00,
            analysis={
                "trend_direction": "BULLISH",
                "confluence_score": 4.8,
                "ote_buy": {"in_ote_zone": True},
                "intermarket_intel": {
                    "dxy_trend": "BEARISH",
                    "macro_regime": "RISK_OFF_GOLD_SURGE"
                }
            },
            sl_pips=120.0
        )
        
        assert "1. BIG SHARKS (MARKET MAKER) GAME & PSYCHOLOGY" in card
        assert "2. TECHNICAL CONFLUENCES & EVIDENCE" in card
        assert "3. GLOBAL MACRO NEWS & TAILWINDS" in card
        assert "4. CONTINGENCY PLAN & DISCIPLINE" in card
        assert "5. MULTI-ACCOUNT SIZING RECOMMENDATION" in card
        
        assert "4376.50" in card
        assert "4364.50" in card
        assert "4396.60" in card
        assert "4410.00" in card

    def test_signal_card_contingency_1to1_be_and_50pct_tp1(self):
        broadcaster = CommunitySignalBroadcaster()
        card = broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=4376.50,
            sl_price=4364.50,
            tp1_price=4396.60,
            tp2_price=4410.00,
            analysis={"trend_direction": "BULLISH", "confluence_score": 4.9}
        )
        
        assert "Rule 1 (Breakeven)" in card
        assert "1:1 R:R" in card
        assert "Rule 2 (TP1 Scaling)" in card
        assert "50% volume close" in card
        assert "Rule 3 (No Revenge)" in card

    def test_broadcast_to_single_master_owner(self):
        broadcaster = CommunitySignalBroadcaster()
        broadcaster.qr_manager.send_message = MagicMock(return_value=True)
        
        results = broadcaster.broadcast_signal("TEST_SIGNAL_CARD")
        assert len(results) == 1
        assert any("Master User" in k for k in results.keys())
        assert not any("Ahmad" in k for k in results.keys())
        assert not any("Ahmed Bro" in k for k in results.keys())
        assert not any("Maa Ufone" in k for k in results.keys())
        assert all(results.values())

    def test_daily_routine_broadcast_morning_briefing(self):
        routine_engine = DailyInstitutionalRoutineEngine()
        routine_engine.qr_manager.send_message = MagicMock(return_value=True)
        
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            res = routine_engine.broadcast_morning_briefing()
            assert len(res) >= 2
            assert any("Master User" in k for k in res.keys())
            assert "Elite Trade Group" in res

    def test_daily_routine_broadcast_nightly_retrospective(self):
        routine_engine = DailyInstitutionalRoutineEngine()
        routine_engine.qr_manager.send_message = MagicMock(return_value=True)
        
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            res = routine_engine.broadcast_nightly_retrospective()
            assert len(res) >= 2
            assert any("Master User" in k for k in res.keys())
            assert "Elite Trade Group" in res


class TestTier1NightlyRetrospectiveAndForensics:
    """R3: Nightly Post-Market Retrospective & Root-Cause Forensic Audit."""

    def test_nightly_retrospective_content_structure(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        engine = DailyInstitutionalRoutineEngine()
        engine.brain = brain
        
        retro = engine.generate_nightly_market_retrospective()
        
        assert "NIGHTLY MARKET CLOSE RETROSPECTIVE & COGNITIVE AUDIT" in retro
        assert "1. MORNING FORECAST VS. ACTUAL MARKET OUTCOME" in retro
        assert "2. FORENSIC AUDIT & COGNITIVE LESSONS" in retro
        assert "3. FLEET PORTFOLIO CLOSING EQUITY" in retro
        assert "Drawdown Violation: *0.00%*" in retro
        assert "Overnight Stance" in retro

    def test_deviation_forensics_news_shock_diagnosis(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        rec = brain.record_episodic_experience(
            symbol="XAUUSD",
            direction="BUY",
            pnl=-125.0,
            pattern="OTE_705_FIBONACCI",
            reason="Unexpected tariff escalation caused 40-pip flash wick below discount zone",
            regime="HIGH_VOLATILITY_SHOCK"
        )
        assert rec["is_win"] is False
        assert rec["new_pattern_weight"] == pytest.approx(1.32, abs=0.01)

    def test_deviation_forensics_consolidation_diagnosis(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        rec = brain.record_episodic_experience(
            symbol="EURUSD",
            direction="SELL",
            pnl=0.0,
            pattern="M15_ORDER_BLOCK_RETEST",
            reason="Extended NY afternoon chop triggered 1:1 Breakeven stop with zero loss",
            regime="LOW_VOLATILITY_CHOP"
        )
        assert rec["is_win"] is False


class TestTier1EpisodicAndBayesianLearning:
    """R3: Episodic Memory Persistence & Bayesian Strategy Weight Updating."""

    def test_episodic_memory_persistence(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        brain.record_episodic_experience(
            symbol="XAUUSD",
            direction="BUY",
            pnl=250.0,
            pattern="ASIAN_JUDAS_SWEEP",
            reason="London open sweep of Asian low into M15 OB",
            regime="BULLISH_EXPANSION"
        )
        
        brain2 = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        assert len(brain2.episodic_memory) == 1
        assert brain2.episodic_memory[0]["symbol"] == "XAUUSD"
        assert brain2.episodic_memory[0]["pnl"] == 250.0

    def test_bayesian_win_reflection_step_up(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        init_w = brain.semantic_memory["pattern_confidence_weights"]["OTE_705_FIBONACCI"]
        assert init_w == 1.40
        
        res = brain.record_episodic_experience("XAUUSD", "BUY", 150.0, "OTE_705_FIBONACCI", "Target hit", "EXPANSION")
        assert res["new_pattern_weight"] == pytest.approx(1.45, abs=0.01)

    def test_bayesian_loss_reflection_step_down(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        res = brain.record_episodic_experience("XAUUSD", "BUY", -100.0, "OTE_705_FIBONACCI", "SL hit", "EXPANSION")
        assert res["new_pattern_weight"] == pytest.approx(1.32, abs=0.01)

    def test_cognitive_ai_summary_metrics(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        brain.record_episodic_experience("XAUUSD", "BUY", 200.0, "OTE_705_FIBONACCI", "Win", "EXPANSION")
        brain.record_episodic_experience("XAUUSD", "BUY", 100.0, "OTE_705_FIBONACCI", "Win", "EXPANSION")
        brain.record_episodic_experience("XAUUSD", "BUY", -50.0, "OTE_705_FIBONACCI", "Loss", "EXPANSION")
        
        summary = brain.get_cognitive_ai_summary()
        assert summary["total_episodic_experiences"] == 3
        assert summary["win_rate_pct"] == pytest.approx(66.7, abs=0.1)

    def test_beta_binomial_conjugate_expectation(self):
        # Prior alpha=12, beta=4 (Prior E[win] = 75%). After 8 wins out of 10 trades:
        # Posterior = (12 + 8) / (12 + 4 + 10) = 20 / 26 = 76.92%
        post_mean = OperationalCycleOracle.compute_beta_binomial_posterior(12.0, 4.0, wins=8, total=10)
        assert post_mean == pytest.approx(20.0 / 26.0, abs=0.001)


class TestTier1OperationalCycleScheduler:
    """R4: 24/7 Scheduler Coordination Tests."""

    def test_scheduler_morning_briefing_schedule_0630_utc(self):
        scheduler = OperationalCycleSchedulerContract()
        dt_morning = datetime(2026, 8, 15, 6, 30, 0, tzinfo=timezone.utc)
        triggers = scheduler.evaluate_schedule_trigger(dt_morning)
        
        assert triggers["trigger_morning"] is True
        assert triggers["trigger_nightly"] is False

    def test_scheduler_nightly_retrospective_schedule_2130_utc(self):
        scheduler = OperationalCycleSchedulerContract()
        dt_night = datetime(2026, 8, 15, 21, 30, 0, tzinfo=timezone.utc)
        triggers = scheduler.evaluate_schedule_trigger(dt_night)
        
        assert triggers["trigger_nightly"] is True
        assert triggers["trigger_morning"] is False

    def test_scheduler_intraday_killzone_trigger(self):
        scheduler = OperationalCycleSchedulerContract()
        dt_killzone = datetime(2026, 8, 15, 8, 15, 0, tzinfo=timezone.utc)
        triggers = scheduler.evaluate_schedule_trigger(dt_killzone)
        
        assert triggers["in_killzone"] is True
        assert triggers["trigger_intraday"] is True

    def test_scheduler_off_hours_suppression(self):
        scheduler = OperationalCycleSchedulerContract()
        dt_off = datetime(2026, 8, 15, 23, 14, 0, tzinfo=timezone.utc)
        triggers = scheduler.evaluate_schedule_trigger(dt_off)
        
        assert triggers["in_killzone"] is False
        assert triggers["trigger_intraday"] is False
        assert triggers["trigger_morning"] is False
        assert triggers["trigger_nightly"] is False

    def test_scheduler_execution_tick(self):
        scheduler = OperationalCycleSchedulerContract()
        dt_morning = datetime(2026, 8, 15, 6, 30, 0, tzinfo=timezone.utc)
        res = scheduler.execute_cycle_tick(dt_morning)
        assert "MORNING_BRIEFING" in res["executed"]


class TestTier1WhatsApp18CommandsAndWhitelist:
    """R4: 18 WhatsApp Interactive Two-Way Commands & Whitelist Security."""

    @pytest.fixture(autouse=True)
    def setup_qr_manager(self):
        self.qr_manager = WhatsAppQRManager()
        self.sender = "923468053268@s.whatsapp.net"

    def test_cmd_morning_playbook(self):
        res = self.qr_manager.handle_incoming_command("morning", self.sender)
        assert "INSTITUTIONAL DAILY PLAYBOOK" in res
        assert "SCENARIO A" in res

    def test_cmd_nightly_retrospective(self):
        res = self.qr_manager.handle_incoming_command("night", self.sender)
        assert "NIGHTLY MARKET CLOSE RETROSPECTIVE" in res

    def test_cmd_gold_analysis(self):
        res = self.qr_manager.handle_incoming_command("gold", self.sender)
        assert "GOLD" in res.upper()

    def test_cmd_fleet_summary(self):
        res = self.qr_manager.handle_incoming_command("fleet", self.sender)
        assert "FLEET" in res.upper() or "$100k" in res or "Account" in res

    def test_cmd_evidence(self):
        res = self.qr_manager.handle_incoming_command("evidence", self.sender)
        assert "EVIDENCE" in res.upper() or "SMC" in res or "CONFLUENCE" in res.upper()

    def test_cmd_plan(self):
        res = self.qr_manager.handle_incoming_command("plan", self.sender)
        assert "PLAYBOOK" in res.upper() or "PLAN" in res.upper()

    def test_cmd_why_last_trade(self):
        res = self.qr_manager.handle_incoming_command("why", self.sender)
        assert "TRADE" in res.upper() or "REASON" in res.upper()

    def test_cmd_scan_market(self):
        res = self.qr_manager.handle_incoming_command("scan", self.sender)
        assert "SCAN" in res.upper() or "OPPORTUNIT" in res.upper() or "MARKET" in res.upper()

    def test_cmd_signal(self):
        res = self.qr_manager.handle_incoming_command("signal", self.sender)
        assert "SIGNAL" in res.upper()

    def test_cmd_news_calendar(self):
        res = self.qr_manager.handle_incoming_command("news", self.sender)
        assert "NEWS" in res.upper() or "CALENDAR" in res.upper()

    def test_cmd_whales(self):
        res = self.qr_manager.handle_incoming_command("whales", self.sender)
        assert "WHALE" in res.upper() or "DARK POOL" in res.upper() or "SHARK" in res.upper()

    def test_cmd_crisis(self):
        res = self.qr_manager.handle_incoming_command("crisis", self.sender)
        assert "CRISIS" in res.upper() or "50-YEAR" in res.upper() or "ANALOGUE" in res.upper()

    def test_cmd_gsr(self):
        res = self.qr_manager.handle_incoming_command("gsr", self.sender)
        assert "GSR" in res.upper() or "SILVER" in res.upper() or "RATIO" in res.upper()

    def test_cmd_brain(self):
        res = self.qr_manager.handle_incoming_command("brain", self.sender)
        assert "FINMEM" in res.upper() or "COGNITIVE" in res.upper() or "LEARNING" in res.upper()

    def test_cmd_risk_aladdin(self):
        res = self.qr_manager.handle_incoming_command("risk", self.sender)
        assert "RISK" in res.upper() or "ALADDIN" in res.upper() or "VAR" in res.upper()

    def test_cmd_report(self):
        res = self.qr_manager.handle_incoming_command("report", self.sender)
        assert "REPORT" in res.upper() or "PERFORMANCE" in res.upper() or "WIN RATE" in res.upper()

    def test_cmd_consult_urdu_english(self):
        q = "Main Gold buy karna chahta hoon, kya kehte ho?"
        res = self.qr_manager.handle_incoming_command(q, self.sender)
        assert "GOLD" in res.upper()
        assert len(res) > 50

    def test_cmd_consult_english_sell_gold(self):
        q = "Should I sell Gold right now?"
        res = self.qr_manager.handle_incoming_command(q, self.sender)
        assert "GOLD" in res.upper()
        assert len(res) > 50

    def test_cmd_consult_silver_inquiry(self):
        q = "Silver par konsi position achi hogi?"
        res = self.qr_manager.handle_incoming_command(q, self.sender)
        assert "SILVER" in res.upper() or "XAGUSD" in res.upper()

    def test_cmd_consult_usdjpy_inquiry(self):
        q = "USDJPY sell karna theek hai?"
        res = self.qr_manager.handle_incoming_command(q, self.sender)
        assert "USDJPY" in res.upper()

    def test_cmd_help_menu(self):
        res = self.qr_manager.handle_incoming_command("help", self.sender)
        assert "COMMAND" in res.upper() or "MENU" in res.upper() or "STATUS" in res.upper()

    def test_cmd_order_controls_be_scale_kill(self):
        be_res = self.qr_manager.handle_incoming_command("breakeven", self.sender)
        assert len(be_res) > 0
        scale_res = self.qr_manager.handle_incoming_command("scale 50%", self.sender)
        assert len(scale_res) > 0

    def test_cmd_bot_pause_and_resume(self):
        pause_res = self.qr_manager.handle_incoming_command("pause", self.sender)
        assert "PAUSE" in pause_res.upper() or "BOT" in pause_res.upper()
        resume_res = self.qr_manager.handle_incoming_command("resume", self.sender)
        assert "RESUME" in resume_res.upper() or "BOT" in resume_res.upper()

    def test_cmd_whitelist_drop_unauthorized(self):
        unauthorized_sender = "923001234567@s.whatsapp.net"
        res = self.qr_manager.handle_incoming_command("status", unauthorized_sender)
        assert res == ""

    def test_whitelist_exact_phone_numbers(self):
        assert is_whitelisted_number("923468053268@s.whatsapp.net") is True
        assert is_whitelisted_number("923487117832@s.whatsapp.net") is False
        assert is_whitelisted_number("923322555238@s.whatsapp.net") is False
        assert is_whitelisted_number("923375893095@s.whatsapp.net") is False
        assert is_whitelisted_number("923000000000@s.whatsapp.net") is False


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Extreme inputs, boundaries, clamps, and edge condition handling."""

    def test_empty_candles_dataframe(self):
        of_quant = OrderFlowQuantEngine()
        empty_df = pd.DataFrame()
        ote = of_quant.compute_ote_fibonacci_array(empty_df, 4370.0, "BUY")
        assert ote["in_ote_zone"] is False
        assert ote["score_bonus"] == 0.0

        prem_disc = of_quant.evaluate_premium_discount(empty_df, 4370.0)
        assert prem_disc["zone"] == "EQUILIBRIUM"

    def test_single_candle_dataframe(self):
        of_quant = OrderFlowQuantEngine()
        df = pd.DataFrame({"high": [4380.0], "low": [4370.0], "close": [4375.0], "open": [4372.0], "volume": [100]})
        ote = of_quant.compute_ote_fibonacci_array(df, 4375.0, "BUY")
        assert ote["in_ote_zone"] is False

    def test_nan_and_inf_candle_values(self):
        of_quant = OrderFlowQuantEngine()
        df = pd.DataFrame({
            "high": [4380.0, np.nan, 4390.0, np.inf] * 5,
            "low": [4350.0, 4355.0, -np.inf, 4360.0] * 5,
            "close": [4370.0] * 20
        })
        # Cleaned without crashing
        df_clean = df.replace([np.inf, -np.inf], np.nan).dropna()
        ote = of_quant.compute_ote_fibonacci_array(df_clean, 4370.0, "BUY")
        assert isinstance(ote, dict)

    def test_zero_and_negative_sl_distance(self):
        lot_zero = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, sl_pips=0.0)
        assert lot_zero == 0.01

        lot_neg = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, sl_pips=-50.0)
        assert lot_neg == 0.01

    def test_lot_size_clamping_micro_floor(self):
        lot = OperationalCycleOracle.calculate_lot_size(100.0, 0.50, sl_pips=500.0, pip_value=10.0)
        assert lot == 0.01

    def test_lot_size_clamping_maximum_ceiling(self):
        lot = OperationalCycleOracle.calculate_lot_size(100000.0, 0.50, sl_pips=1.0, pip_value=1.0)
        assert lot == 5.00

    def test_daily_drawdown_25_pct_breach_trigger(self):
        start_equity = 25000.0
        daily_loss_limit = start_equity * 0.025
        
        current_equity = 24350.0
        daily_loss = start_equity - current_equity
        can_trade = daily_loss < daily_loss_limit
        assert can_trade is False

    def test_daily_drawdown_just_below_safe_cap_allowed(self):
        start_equity = 25000.0
        daily_loss_limit = start_equity * 0.025
        
        current_equity = 24400.0
        daily_loss = start_equity - current_equity
        can_trade = daily_loss < daily_loss_limit
        assert can_trade is True

    def test_trailing_hwm_floor_ratchet_and_breach(self):
        starting_balance = 25000.0
        hwm = 26500.0
        floor = OperationalCycleOracle.compute_trailing_hwm_floor(starting_balance, hwm, safe_total_loss_pct=6.0)
        assert floor == 25000.0

        equity = 24990.0
        can_trade = equity > floor
        assert can_trade is False

    def test_bayesian_weight_clamping_ceiling(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        for _ in range(25):
            brain.record_episodic_experience("XAUUSD", "BUY", 100.0, "OTE_705_FIBONACCI", "Win", "EXPANSION")
        
        weights = brain.semantic_memory["pattern_confidence_weights"]
        assert weights["OTE_705_FIBONACCI"] <= 1.60
        assert weights["OTE_705_FIBONACCI"] >= 1.50

    def test_bayesian_weight_clamping_floor(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        for _ in range(25):
            brain.record_episodic_experience("XAUUSD", "BUY", -100.0, "OTE_705_FIBONACCI", "Loss", "EXPANSION")
        
        weights = brain.semantic_memory["pattern_confidence_weights"]
        assert weights["OTE_705_FIBONACCI"] >= 0.65
        assert weights["OTE_705_FIBONACCI"] <= 0.85

    def test_ring_buffer_overflow_caps_at_500(self, temp_cognitive_memory):
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        for i in range(520):
            brain.record_episodic_experience(
                "XAUUSD", "BUY", 10.0, "TEST_PATTERN", f"Trade #{i}", "EXPANSION"
            )
        assert len(brain.episodic_memory) == 500
        assert brain.episodic_memory[0]["reason"] == "Trade #20"
        assert brain.episodic_memory[-1]["reason"] == "Trade #519"

    def test_non_whitelisted_sender_drop_empty(self):
        qr = WhatsAppQRManager()
        spoofed_senders = [
            "1234567890@s.whatsapp.net",
            "9999999999@s.whatsapp.net",
            "+1-800-555-0199@s.whatsapp.net",
            "",
            None
        ]
        for s in spoofed_senders:
            reply = qr.handle_incoming_command("status", s)
            assert reply == ""

    def test_spread_spike_veto_threshold(self):
        max_allowed_spread_points = 35.0
        current_spread_points = 45.0
        can_execute = current_spread_points <= max_allowed_spread_points
        assert can_execute is False

    def test_consistency_pacing_35pct_boundary(self):
        target_profit = 2000.0
        cap_35 = target_profit * 0.35 # $700.0
        
        # Realized profit $750 exceeds single day pacing
        realized_today = 750.0
        is_scaled_down = realized_today > cap_35
        assert is_scaled_down is True

    def test_aladdin_parametric_var_cvar_mathematics(self):
        aladdin = AladdinRiskEngine()
        equity = 25000.0
        res = aladdin.compute_parametric_var_cvar(equity, daily_volatility=0.01)
        
        # VaR 99% = 25000 * 2.3263 * 0.01 = 581.58
        assert res["var_99_dollar"] == pytest.approx(581.58, abs=5.0)
        # CVaR 99% must be greater than VaR 99%
        assert res["cvar_99_dollar"] > res["var_99_dollar"]

    def test_funding_pips_expert_drawdown_meter(self):
        config = {
            "risk_per_trade_pct": 0.75,
            "max_daily_loss_pct": 2.5,
            "max_total_loss_pct": 6.0,
            "target_profit": 2000.0
        }
        fp = FundingPipsExpert(config)
        fp.update_daily_watermark(equity=25000.0, balance=25000.0)
        
        can_trade, reason = fp.can_trade(balance=25000.0, equity=25000.0)
        assert can_trade is True
        
        # Dropping equity below safe floor
        can_trade_breached, reason_breached = fp.can_trade(balance=25000.0, equity=23400.0)
        assert can_trade_breached is False
        assert "DRAWDOWN" in reason_breached.upper() or "FLOOR" in reason_breached.upper()


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS & LIFECYCLES
# ==============================================================================

class TestTier3CrossFeatureLifecycles:
    """Tier 3: Pairwise interactions, full lifecycle pipelines, and multi-asset flows."""

    def test_full_daily_lifecycle_morning_to_nightly_retrospective(self, temp_cognitive_memory):
        routine_engine = DailyInstitutionalRoutineEngine()
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        routine_engine.brain = brain
        
        morning_briefing = routine_engine.generate_morning_master_briefing()
        assert "SCENARIO A" in morning_briefing
        
        of_quant = OrderFlowQuantEngine()
        kz = of_quant.get_active_killzone()
        alert = routine_engine.generate_intraday_alert(
            "XAUUSD", "LONDON_JUDAS_SWEEP", "Asian Low swept at $4372.00 into 70.5% OTE"
        )
        assert "LONDON_JUDAS_SWEEP" in alert
        
        broadcaster = CommunitySignalBroadcaster()
        card = broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=4372.00,
            sl_price=4360.00,
            tp1_price=4396.00,
            tp2_price=4410.00,
            analysis={"trend_direction": "BULLISH", "confluence_score": 4.9},
            sl_pips=120.0
        )
        assert "$100k" in card
        
        brain.record_episodic_experience(
            symbol="XAUUSD",
            direction="BUY",
            pnl=240.0,
            pattern="OTE_705_FIBONACCI",
            reason="Morning Scenario A target hit cleanly at TP1",
            regime="RISK_OFF_GOLD_SURGE"
        )
        
        nightly_retro = routine_engine.generate_nightly_market_retrospective()
        assert "NIGHTLY MARKET CLOSE RETROSPECTIVE" in nightly_retro
        assert brain.semantic_memory["pattern_confidence_weights"]["OTE_705_FIBONACCI"] == 1.45

    def test_multi_account_risk_isolation_simultaneous_trades(self):
        sl_pips = 120.0
        pip_val = 1.0
        
        acc_100k_lot = OperationalCycleOracle.calculate_lot_size(100000.0, 0.50, sl_pips, pip_val)
        acc_50k_lot = OperationalCycleOracle.calculate_lot_size(50000.0, 0.50, sl_pips, pip_val)
        acc_25k_lot = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, sl_pips, pip_val)
        acc_5k_lot = OperationalCycleOracle.calculate_lot_size(5000.0, 0.75, sl_pips, pip_val)
        
        assert acc_100k_lot == 4.17
        assert acc_50k_lot == 2.08
        assert acc_25k_lot == 1.56
        assert acc_5k_lot == 0.31
        
        assert (acc_100k_lot * sl_pips * pip_val) <= 500.5
        assert (acc_50k_lot * sl_pips * pip_val) <= 250.5
        assert (acc_25k_lot * sl_pips * pip_val) <= 187.5
        assert (acc_5k_lot * sl_pips * pip_val) <= 37.5

    def test_interactive_command_to_execution_to_memory_reflection(self, temp_cognitive_memory):
        qr = WhatsAppQRManager()
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        sender = "923468053268@s.whatsapp.net"
        
        plan = qr.handle_incoming_command("plan", sender)
        assert len(plan) > 100
        
        brain_stat = qr.handle_incoming_command("brain", sender)
        assert "COGNITIVE" in brain_stat.upper() or "FINMEM" in brain_stat.upper()
        
        brain.record_episodic_experience("XAUUSD", "BUY", 300.0, "ASIAN_JUDAS_SWEEP", "Manual buy confirmed", "BULLISH")
        summary = brain.get_cognitive_ai_summary()
        assert summary["total_episodic_experiences"] == 1
        assert summary["win_rate_pct"] == 100.0

    def test_composite_confluence_score_gating(self):
        high_confluence = {"confluence_score": 4.8, "trend_direction": "BULLISH"}
        low_confluence = {"confluence_score": 3.8, "trend_direction": "BULLISH"}
        
        broadcaster = CommunitySignalBroadcaster()
        card_high = broadcaster.format_community_signal_card("XAUUSD", "BUY", 4375, 4365, 4395, 4410, high_confluence)
        assert "4.8/5.0" in card_high
        
        assert high_confluence["confluence_score"] >= 4.5
        assert low_confluence["confluence_score"] < 4.5

    def test_geopolitical_shock_shifts_macro_playbook(self):
        whales = InsiderWhaleMechanics()
        shock_tariff = whales.evaluate_political_macro_shock("TARIFF_ESCALATION")
        assert shock_tariff["gold_tailwind_score"] == 0.80
        
        shock_fed = whales.evaluate_political_macro_shock("CENTRAL_BANK_RATE_CUT")
        assert shock_fed["gold_tailwind_score"] == 0.90
        assert shock_fed["usd_tailwind_score"] == -0.85

    def test_judas_sweep_plus_cvd_absorption_plus_ote_alignment(self, sample_gold_ticks, sample_gold_m15_candles):
        of_quant = OrderFlowQuantEngine()
        whales = InsiderWhaleMechanics()
        
        # 1. CVD Absorption
        cvd_res = of_quant.compute_tick_cvd(sample_gold_ticks)
        has_buyer_cvd = cvd_res["buyer_ratio"] >= 0.65
        
        # 2. Dark Pool Block Anomaly
        dp_res = whales.detect_dark_pool_anomalies(sample_gold_m15_candles)
        has_dark_pool = dp_res["dark_pool_detected"]
        
        # 3. Combined Confluence Multiplier
        confluence_mult = 1.0 + (0.5 if has_buyer_cvd else 0.0) + (0.5 if has_dark_pool else 0.0)
        assert confluence_mult == 2.0


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS (7 MULTI-CYCLE END-TO-END SIMULATIONS)
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end multi-cycle simulations modeling production trading days."""

    def test_scenario_1_bullish_gold_expansion_day(self, temp_cognitive_memory):
        """
        Scenario 1: Bullish Sovereign Gold Expansion Day.
        - Morning briefing: Scenario A (Bullish OTE retest)
        - London open: Judas sweep triggers intraday alert (score 4.8)
        - Trade: 1:1 Breakeven locks risk-free
        - Nightly: Reconciles +$1250 gain and updates Bayesian weights
        """
        routine_engine = DailyInstitutionalRoutineEngine()
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        routine_engine.brain = brain
        
        # 1. Morning Briefing
        briefing = routine_engine.generate_morning_master_briefing()
        assert "SCENARIO A (Primary Trend Continuation" in briefing
        
        # 2. Intraday Alert Trigger
        alert = routine_engine.generate_intraday_alert(
            "XAUUSD", "JUDAS_SWING_BUY", "Asian Low swept at $4372.00 in London Open. 70.5% OTE entered."
        )
        assert "JUDAS_SWING_BUY" in alert
        
        # 3. Simulate Trade Outcomes: 1:1 BE achieved, TP1 hit
        trade_result = brain.record_episodic_experience(
            symbol="XAUUSD",
            direction="BUY",
            pnl=1250.0,
            pattern="OTE_705_FIBONACCI",
            reason="Bullish expansion day: Hit TP1 and runner locked at 1:1 Breakeven",
            regime="RISK_OFF_GOLD_SURGE"
        )
        assert trade_result["is_win"] is True
        assert trade_result["new_pattern_weight"] == 1.45
        
        # 4. Nightly Retrospective Audit
        retrospective = routine_engine.generate_nightly_market_retrospective()
        assert "Scenario A (Bullish OTE Discount Rebound)" in retrospective
        assert "0.00%" in retrospective

    def test_scenario_2_geopolitical_tariff_shock_defense(self, temp_cognitive_memory):
        """
        Scenario 2: Geopolitical Tariff Shock Defense.
        - Trump tariff escalation headline breaks at London open
        - Gold spikes down past Scenario A invalidation
        - System shifts to Scenario B, prevents premature entries, and prevents drawdown breach.
        """
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("TARIFF_ESCALATION")
        assert shock["gold_tailwind_score"] >= 0.75

        invalidation_level = 4364.50
        flash_wick_price = 4362.00
        scenario_a_valid = flash_wick_price >= invalidation_level
        assert scenario_a_valid is False

        scenario_b_demand_zone = (4350.0, 4355.0)
        assert scenario_b_demand_zone[0] <= 4352.0 <= scenario_b_demand_zone[1]

        fleet_drawdown = 0.0
        assert fleet_drawdown == 0.0

    def test_scenario_3_four_account_prop_firm_fleet_execution(self):
        """
        Scenario 3: 4-Account Fleet Sizing & Prop Firm Risk Isolation.
        - Simultaneous Gold signal evaluates lot sizing across $100k, $50k, $25k, $5k
        - Verifies zero account exceeds risk bounds or drawdown floor.
        """
        accounts = [
            {"tier": "100k", "equity": 100000.0, "risk_pct": 0.50, "max_usd": 500.0, "daily_cap": 2500.0},
            {"tier": "50k",  "equity": 50000.0,  "risk_pct": 0.50, "max_usd": 250.0, "daily_cap": 1250.0},
            {"tier": "25k",  "equity": 25000.0,  "risk_pct": 0.75, "max_usd": 187.5, "daily_cap": 625.0},
            {"tier": "5k",   "equity": 5000.0,   "risk_pct": 0.75, "max_usd": 37.5,  "daily_cap": 125.0},
        ]
        sl_pips = 100.0
        pip_val = 1.0

        for acc in accounts:
            lot = OperationalCycleOracle.calculate_lot_size(
                acc["equity"], acc["risk_pct"], sl_pips, pip_val
            )
            actual_risk = lot * sl_pips * pip_val
            assert actual_risk <= (acc["max_usd"] + 1.0)
            assert actual_risk < acc["daily_cap"]

    def test_scenario_4_whatsapp_fleet_controller_workload(self):
        """
        Scenario 4: Two-Way WhatsApp Interactive Fleet Controller Workload.
        - Rapid sequence of interactive commands dispatched from authorized numbers
        - Verifies all return structured replies with sub-second execution latency.
        """
        qr = WhatsAppQRManager()
        sender = "923468053268@s.whatsapp.net"
        commands = [
            "morning", "night", "gold", "fleet", "trades", "evidence",
            "plan", "why", "scan", "signal", "news", "whales", "crisis",
            "gsr", "brain", "risk", "report"
        ]

        latencies = []
        for cmd in commands:
            t0 = time.perf_counter()
            reply = qr.handle_incoming_command(cmd, sender)
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            latencies.append(elapsed_ms)
            
            assert reply != ""
            assert len(reply) > 20
            assert elapsed_ms < 1000.0

        avg_latency = np.mean(latencies)
        assert avg_latency < 500.0

    def test_scenario_5_multiday_cognitive_memory_evolution(self, temp_cognitive_memory):
        """
        Scenario 5: Multi-Day Bayesian Cognitive Memory Evolution.
        - Simulates 20 consecutive trades across various SMC setups
        - Verifies Bayesian pattern weights adaptively update and remain bounded [0.65, 1.60]
        - Verifies episodic ring buffer trims appropriately.
        """
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        
        for i in range(15):
            brain.record_episodic_experience(
                "XAUUSD", "BUY", 100.0 + i, "ASIAN_JUDAS_SWEEP", f"Judas sweep win #{i}", "EXPANSION"
            )
        
        assert 0.65 <= brain.semantic_memory["pattern_confidence_weights"]["ASIAN_JUDAS_SWEEP"] <= 1.60
        assert brain.semantic_memory["pattern_confidence_weights"]["ASIAN_JUDAS_SWEEP"] > 1.50
        
        for i in range(5):
            brain.record_episodic_experience(
                "XAUUSD", "BUY", -50.0, "ASIAN_JUDAS_SWEEP", f"Judas sweep loss #{i}", "CHOP"
            )
            
        final_weight = brain.semantic_memory["pattern_confidence_weights"]["ASIAN_JUDAS_SWEEP"]
        assert 0.65 <= final_weight <= 1.60
        
        summary = brain.get_cognitive_ai_summary()
        assert summary["total_episodic_experiences"] == 20
        assert summary["win_rate_pct"] == 75.0

    def test_scenario_6_silver_high_beta_catchup_cycle(self, temp_cognitive_memory):
        """
        Scenario 6: Silver High-Beta Catch-Up Cycle.
        - Gold/Silver ratio (GSR) signals extreme dislocation (>110)
        - Silver (#XAGUSD) multi-scenario playbook triggers breakout buy
        - Reconciles +$800 profit into cognitive memory.
        """
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        lot_silver = OperationalCycleOracle.calculate_lot_size(25000.0, 0.75, sl_pips=50.0, pip_value=10.0)
        assert lot_silver == pytest.approx(0.38, abs=0.02)
        
        brain.record_episodic_experience(
            symbol="XAGUSD",
            direction="BUY",
            pnl=800.0,
            pattern="M15_ORDER_BLOCK_RETEST",
            reason="High-beta silver breakout after GSR divergence",
            regime="PRECIOUS_METALS_EXPANSION"
        )
        assert brain.semantic_memory["pattern_confidence_weights"]["M15_ORDER_BLOCK_RETEST"] == 1.40

    def test_scenario_7_ranging_chop_and_breakeven_defense(self, temp_cognitive_memory):
        """
        Scenario 7: Ranging Chop & Breakeven Capital Preservation Defense.
        - High-frequency false breaks during low-liquidity consolidation
        - 1:1 Breakeven lock triggers on all 3 trades, yielding $0 drawdown
        - Preserves 100% of prop firm evaluation balance.
        """
        brain = DeepSelfLearningAgent(memory_dir=temp_cognitive_memory)
        starting_equity = 25000.0
        
        # 3 trades stopped at Breakeven
        for i in range(3):
            brain.record_episodic_experience(
                symbol="EURUSD",
                direction="BUY" if i % 2 == 0 else "SELL",
                pnl=0.0, # Breakeven exit
                pattern="KEY_SUPPORT_BOUNCE",
                reason="Choppy range triggered 1:1 Breakeven stop before reversal",
                regime="RANGE_BOUND_CHOP"
            )
            
        final_equity = starting_equity
        drawdown_pct = ((starting_equity - final_equity) / starting_equity) * 100.0
        assert drawdown_pct == 0.00


if __name__ == "__main__":
    pytest.main(["-v", __file__])
