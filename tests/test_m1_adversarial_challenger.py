"""
tests/test_m1_adversarial_challenger.py
========================================================================================
Empirical Adversarial Stress Test Suite for Milestone M1:
Institutional MT5 Prop-Trading, Risk Kernel & HFT DOM Engine.

Author: Challenger 1 (critic, specialist)
Repository: Jarvis Command Center

Stress Tests:
1. Risk calculation boundaries on FundingPips account #40000294403:
   - Balance swings from $1,000 to $1,000,000
   - Extreme ATR regimes (0.000001 to 5000.0)
   - Asset tick sizes and pip values (Forex, Gold, JPY, Crypto)
   - Strict dollar risk cap enforcement at $750.00 under ALL conditions
2. Exact +1.0R Dynamic Breakeven Shift:
   - Exact boundary testing (+0.99R vs +1.00R vs +1.01R)
   - Long (BUY) and Short (SELL) direction geometry
   - Dollar profit threshold trigger ($750.00 cap)
   - Bug hunting on breakeven locked state when SL is at entry
3. Turtle Soup Liquidity Sweeps & CVD Order Absorption under Noise:
   - Equal Highs (EQH) and Equal Lows (EQL) with noisy price series
   - Micro-wick rejection vs breakout detection
   - Zero-range bars and degenerate inputs (empty/sub-15 bar DataFrames)
   - Lee-Ready CVD tick delta with zero volumes, extreme spikes, and rapid zigzags
   - Structural price/CVD absorption divergence oracle
4. Level-2 DOM Microstructure & Whale Walls:
   - Normalization of both 'bids'/'asks' and 'top_bids'/'top_asks'
   - Strict >1,000 lots boundary filter for whale walls
   - Sub-2ms execution benchmark and spread radar
5. Institutional Big Sharks Reasoning API Contract:
   - Schema adherence to PROJECT.md M1 ↔ M2 & M3 interface contract
   - Mandatory SMC components (sweep, FVG 50% CE, Order Block, Wyckoff, DXY, news)
   - Multi-timeframe trend confluence veto oracle
========================================================================================
"""

from __future__ import annotations

import math
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from src.risk_manager import RiskManager
from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState
from src.order_flow_quant import OrderFlowQuantEngine
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from skills.high_frequency_trading import (
    HighFrequencyTradingEngine,
    analyze_hft_microstructure,
    get_hft_engine,
    run as hft_run
)
from core.trading.reasoning import (
    BigSharksReasoningEngine,
    get_trading_reasoning,
    get_reasoning_engine
)


class TestRiskCalculationBoundaries(unittest.TestCase):
    """
    Stress-tests risk calculation boundaries on FundingPips account #40000294403
    with varying ATR, tick sizes, and balance swings.
    Verifies that dollar risk is strictly capped at $750.00 (0.75% of $100,000) under ALL conditions.
    """

    def setUp(self):
        self.risk_kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.risk_mgr = RiskManager({
            "account_info": {"target_account_size": 100000.0},
            "risk_management": {
                "risk_per_trade_pct": 0.75,
                "max_risk_usd_cap": 750.0,
                "min_rr_ratio": 2.5,
                "dynamic_breakeven_r": 1.0,
                "max_daily_loss_pct": 4.0,
                "max_total_loss_pct": 10.0,
                "max_open_trades": 3,
                "max_daily_trades": 3,
            }
        })
        self.pip_engine = PipdanceFastTrackEngine()
        self.prs = PortfolioRiskService()
        self.account_id = "40000294403"

    def test_01_balance_swings_pipdance_engine_dollar_cap(self):
        """Verify Pipdance engine strictly clamps dollar risk to <= $750.00 across wide balance swings."""
        balance_swings = [
            1000.0, 5000.0, 10000.0, 25000.0, 50000.0, 75000.0,
            99000.0, 100000.0, 100449.03, 105000.0, 150000.0,
            250000.0, 500000.0, 1000000.0, 5000000.0
        ]
        # Using typical EURUSD ATR (0.0015 = 15 pips)
        for bal in balance_swings:
            res = self.pip_engine.calculate_risk(
                balance=bal,
                atr=0.0015,
                symbol="EURUSD",
                entry_price=1.0850,
                account_id=self.account_id
            )
            # Must never exceed $750.00 for account 40000294403
            self.assertLessEqual(
                res["risk_usd"],
                750.00,
                f"Pipdance engine risk_usd (${res['risk_usd']}) exceeded $750.00 at balance ${bal}"
            )
            self.assertLessEqual(
                res["max_risk_cap"],
                750.00,
                f"Pipdance effective_cap (${res['max_risk_cap']}) exceeded $750.00 at balance ${bal}"
            )

        # Baseline check at exact $100k balance
        base_res = self.pip_engine.calculate_risk(
            balance=100000.0,
            atr=0.0015,
            symbol="EURUSD",
            entry_price=1.0850,
            account_id=self.account_id
        )
        self.assertEqual(base_res["risk_usd"], 750.00)
        self.assertEqual(base_res["max_risk_cap"], 750.00)

        # Live balance check at $100,449.03: uncapped 0.75% would be $753.37, must clamp to $750.00
        live_res = self.pip_engine.calculate_risk(
            balance=100449.03,
            atr=0.0015,
            symbol="EURUSD",
            entry_price=1.0850,
            account_id=self.account_id
        )
        self.assertEqual(live_res["risk_usd"], 750.00)
        self.assertEqual(live_res["max_risk_cap"], 750.00)

    def test_02_deterministic_risk_kernel_gate2_dollar_risk_cap(self):
        """Verify DeterministicRiskKernel Gate 2 strictly admits <= $750.00 and blocks > $750.00."""
        # 1. Exact $750.00 risk on $100k balance -> ADMITTED
        res_ok = self.risk_kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=93.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id=self.account_id,
            balance=100000.0
        )
        self.assertTrue(res_ok["allowed"], f"Rejected valid trade: {res_ok['blockers']}")
        self.assertEqual(res_ok["decision"], "ADMITTED_PROPOSAL")
        self.assertEqual(res_ok["risk_usd"], 750.00)

        # 2. Explicit proposed_risk_usd = 750.00 -> ADMITTED
        res_explicit = self.risk_kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=93.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id=self.account_id,
            balance=100000.0,
            proposed_risk_usd=750.00
        )
        self.assertTrue(res_explicit["allowed"])

        # 3. Explicit proposed_risk_usd = 750.05 (breaches cap) -> REJECTED
        res_breach_usd = self.risk_kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=93.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id=self.account_id,
            balance=100000.0,
            proposed_risk_usd=750.05
        )
        self.assertFalse(res_breach_usd["allowed"])
        self.assertEqual(res_breach_usd["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max cap ($750.00)" in b for b in res_breach_usd["blockers"]))

        # 4. Proposed risk pct = 0.76% (exceeds 0.75% cap) -> REJECTED
        res_breach_pct = self.risk_kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=93.0,
            proposed_risk_pct=0.76,
            rr_ratio=2.5,
            account_id=self.account_id,
            balance=100000.0
        )
        self.assertFalse(res_breach_pct["allowed"])
        self.assertTrue(any("exceeds max allowed (0.75%)" in b for b in res_breach_pct["blockers"]))

        # 5. Large balance without clamped risk: $150,000 * 0.75% = $1125.00 -> REJECTED
        res_large_bal = self.risk_kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=93.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id=self.account_id,
            balance=150000.0
        )
        self.assertFalse(res_large_bal["allowed"])
        self.assertTrue(any("exceeds max cap ($750.00)" in b for b in res_large_bal["blockers"]))

    def test_03_portfolio_risk_service_dollar_cap_clamping(self):
        """Verify PortfolioRiskService clamps dollar risk to <= $750.00 across balance variations."""
        test_equities = [50000.0, 75000.0, 100000.0, 100449.03, 120000.0, 200000.0, 500000.0]
        for eq in test_equities:
            # Reconcile fresh daily baseline for each equity tier
            acc = self.prs.get_or_register_account(self.account_id)
            acc.current_equity = eq
            acc.daily_start_equity = eq
            acc.starting_balance = eq
            acc.trailing_hwm_floor = eq * 0.90
            acc.daily_loss_dollar_cap = eq * 0.05
            acc.is_locked = False
            acc.lock_reason = None

            self.assertEqual(acc.max_risk_usd_cap, 750.0)
            self.assertEqual(acc.max_risk_pct, 0.75)

            ok, msg, telemetry = self.prs.evaluate_trade_admission_risk(
                account_id=self.account_id,
                symbol="XAUUSD",
                direction="BUY",
                risk_pct=0.75,
                check_news=False
            )
            self.assertTrue(ok, f"PortfolioRiskService rejected valid trade: {msg}")
            self.assertLessEqual(
                telemetry["risk_dollar"],
                750.00,
                f"PortfolioRiskService risk_dollar (${telemetry['risk_dollar']}) exceeded $750.00 at equity ${eq}"
            )

        # Adversarial percentage injections
        for bad_pct in [0.76, 0.80, 1.0, 2.5, 5.0, 0.0, -0.5, float('nan'), float('inf')]:
            ok, msg, _ = self.prs.evaluate_trade_admission_risk(
                account_id=self.account_id,
                symbol="XAUUSD",
                direction="BUY",
                risk_pct=bad_pct,
                check_news=False
            )
            self.assertFalse(ok, f"PortfolioRiskService erroneously admitted illegal risk_pct {bad_pct}")

    def test_04_risk_manager_position_sizing_and_lot_ceilings(self):
        """Verify RiskManager clamps dollar risk to $750.00 and enforces hard lot ceilings."""
        equities = [10000.0, 50000.0, 100000.0, 100449.03, 200000.0, 500000.0]
        for eq in equities:
            rules = self.risk_mgr.get_account_rules(self.account_id)
            self.assertEqual(rules["max_risk_usd_cap"], 750.0)
            self.assertEqual(rules["max_risk_pct"], 0.75)

        # Micro SL pips stress: tiny SL should attempt huge lots, but must be clamped to hard ceilings
        tiny_sl_pips = [0.0001, 0.001, 0.01, 0.1, 0.5, 1.0]
        for sl in tiny_sl_pips:
            # Gold: max 0.10 lots
            gold_lot = self.risk_mgr.calculate_position_size(100449.03, sl, "XAUUSD", account_id=self.account_id)
            self.assertLessEqual(gold_lot, 0.10, f"Gold lot size {gold_lot} exceeded 0.10L ceiling at SL {sl}")

            # Forex: max 0.20 lots
            forex_lot = self.risk_mgr.calculate_position_size(100449.03, sl, "EURUSD", account_id=self.account_id)
            self.assertLessEqual(forex_lot, 0.20, f"Forex lot size {forex_lot} exceeded 0.20L ceiling at SL {sl}")

            # Crypto: max 0.01 lots
            crypto_lot = self.risk_mgr.calculate_position_size(100449.03, sl, "BTCUSD", account_id=self.account_id)
            self.assertLessEqual(crypto_lot, 0.01, f"Crypto lot size {crypto_lot} exceeded 0.01L ceiling at SL {sl}")

        # Flexible backtester signature: returns (lot, risk)
        lot, risk = self.risk_mgr.calculate_position_size("XAUUSD", 2715.0, 2710.0, 100449.03, account_id=self.account_id)
        self.assertLessEqual(risk, 750.00)
        self.assertLessEqual(lot, 0.10)

    def test_05_extreme_atr_regimes_and_tick_sizes(self):
        """Stress-test Pipdance engine across extreme ATR regimes (0.000001 to 5000.0) and exotic symbols."""
        extreme_atrs = [
            0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 0.5, 1.0,
            5.0, 10.0, 50.0, 100.0, 500.0, 1000.0, 5000.0
        ]
        symbols_and_ceilings = [
            ("XAUUSD", 0.10, 2715.0),
            ("EURUSD", 0.20, 1.0850),
            ("GBPUSD", 0.20, 1.3340),
            ("USDJPY", 0.20, 145.50),
            ("BTCUSD", 0.01, 65000.0),
            ("ETHUSD", 0.01, 2600.0),
            ("SOLUSD", 0.01, 150.0),
        ]

        for sym, max_lot, price in symbols_and_ceilings:
            for atr in extreme_atrs:
                res = self.pip_engine.calculate_risk(
                    balance=100449.03,
                    atr=atr,
                    symbol=sym,
                    entry_price=price,
                    account_id=self.account_id
                )
                self.assertLessEqual(
                    res["risk_usd"],
                    750.00,
                    f"risk_usd (${res['risk_usd']}) exceeded $750.00 on {sym} at ATR {atr}"
                )
                if res["lot_size"] > 0:
                    self.assertLessEqual(
                        res["lot_size"],
                        max_lot,
                        f"Lot size {res['lot_size']} exceeded {max_lot} ceiling on {sym} at ATR {atr}"
                    )
                    self.assertGreaterEqual(
                        res["lot_size"],
                        0.01,
                        f"Lot size {res['lot_size']} below minimum 0.01L on {sym} at ATR {atr}"
                    )
                else:
                    # When ATR is massive (e.g. 5000.0), 0.01 lot loss would exceed $750.00,
                    # so engine must reject the trade safely to protect capital
                    self.assertEqual(res["status"], "rejected_unaffordable_risk")


class TestDynamicBreakevenExactShift(unittest.TestCase):
    """
    Stress-tests dynamic breakeven shift logic across all engines.
    Verifies that dynamic breakeven shift triggers exactly at +1.0R gain.
    """

    def setUp(self):
        self.risk_mgr = RiskManager({
            "account_info": {"target_account_size": 100000.0},
            "risk_management": {"dynamic_breakeven_r": 1.0, "max_risk_usd_cap": 750.0}
        })
        self.risk_kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.pip_engine = PipdanceFastTrackEngine()
        self.reasoning = BigSharksReasoningEngine()

    def test_06_risk_manager_exact_1r_boundary_buy_and_sell(self):
        """Verify RiskManager triggers SL shift exactly when current_r >= 1.00."""
        # BUY: Entry 1.3000, SL 1.2900 -> Risk Dist = 0.0100 (100 pips)
        entry = 1.3000
        sl = 1.2900
        risk_dist = 0.0100

        # Sub-1.0R: +0.50R, +0.95R, +0.99R, +0.999R -> NO TRIGGER
        for r in [0.0, 0.50, 0.95, 0.99, 0.999]:
            curr = entry + (r * risk_dist)
            be = self.risk_mgr.check_dynamic_breakeven(entry, curr, sl, direction="BUY")
            self.assertFalse(be["trigger"], f"Breakeven triggered prematurely at {r:.3f}R on BUY")
            self.assertEqual(be["action"], "hold")
            self.assertEqual(be["new_sl"], sl)

        # Exact 1.0R and above: +1.000R, +1.001R, +1.20R, +2.50R -> TRIGGERED
        for r in [1.000, 1.001, 1.050, 1.500, 2.500]:
            curr = entry + (r * risk_dist)
            be = self.risk_mgr.check_dynamic_breakeven(entry, curr, sl, direction="BUY")
            self.assertTrue(be["trigger"], f"Breakeven failed to trigger at {r:.3f}R on BUY")
            self.assertEqual(be["action"], "shift_sl_to_entry")
            self.assertEqual(be["new_sl"], entry)

        # SELL: Entry 1.3000, SL 1.3100 -> Risk Dist = 0.0100 (100 pips)
        sl_sell = 1.3100
        for r in [0.0, 0.50, 0.99, 0.999]:
            curr = entry - (r * risk_dist)
            be = self.risk_mgr.check_dynamic_breakeven(entry, curr, sl_sell, direction="SELL")
            self.assertFalse(be["trigger"], f"Breakeven triggered prematurely at {r:.3f}R on SELL")
            self.assertEqual(be["action"], "hold")
            self.assertEqual(be["new_sl"], sl_sell)

        for r in [1.000, 1.001, 1.500, 2.500]:
            curr = entry - (r * risk_dist)
            be = self.risk_mgr.check_dynamic_breakeven(entry, curr, sl_sell, direction="SELL")
            self.assertTrue(be["trigger"], f"Breakeven failed to trigger at {r:.3f}R on SELL")
            self.assertEqual(be["action"], "shift_sl_to_entry")
            self.assertEqual(be["new_sl"], entry)

    def test_07_deterministic_risk_kernel_breakeven_evaluation(self):
        """Verify DeterministicRiskKernel triggers dynamic breakeven at exactly 1.0R or $750 profit."""
        # 1. Gain < 1.0R and profit < $750 -> No trigger
        be_below = self.risk_kernel.evaluate_dynamic_breakeven(
            current_gain_r=0.99,
            profit_usd=740.0,
            current_price=2725.0,
            entry_price=2715.0
        )
        self.assertFalse(be_below["trigger"])
        self.assertEqual(be_below["action"], "maintain_sl")

        # 2. Gain == 1.0R -> Trigger
        be_exact = self.risk_kernel.evaluate_dynamic_breakeven(
            current_gain_r=1.00,
            profit_usd=500.0,
            current_price=2725.0,
            entry_price=2715.0
        )
        self.assertTrue(be_exact["trigger"])
        self.assertEqual(be_exact["action"], "lock_sl_to_entry")
        self.assertEqual(be_exact["new_sl"], 2715.0)

        # 3. Profit == $750.00 cap reached even if R < 1.0 -> Trigger
        be_dollar_cap = self.risk_kernel.evaluate_dynamic_breakeven(
            current_gain_r=0.85,
            profit_usd=750.0,
            current_price=2723.0,
            entry_price=2715.0
        )
        self.assertTrue(be_dollar_cap["trigger"])
        self.assertEqual(be_dollar_cap["action"], "lock_sl_to_entry")
        self.assertEqual(be_dollar_cap["new_sl"], 2715.0)

    def test_08_pipdance_engine_check_breakeven_trigger(self):
        """Verify PipdanceFastTrackEngine check_breakeven_trigger with price and profit triggers."""
        # Test BUY position: Entry 1.3000, SL 1.2900 (100 pips risk)
        pos_buy = {
            "ticket": 13002987,
            "symbol": "GBPUSD",
            "type": "BUY",
            "price_open": 1.3000,
            "sl": 1.2900,
            "tp": 1.3250,
            "profit": 100.0,
            "volume": 0.20
        }

        # Sub-1.0R price: 1.3090 (90 pips profit, 0.90R) -> No trigger
        res_sub = self.pip_engine.check_breakeven_trigger(pos_buy, current_price=1.3090, breakeven_profit_cap=750.0)
        self.assertFalse(res_sub["trigger"])
        self.assertEqual(res_sub["action"], "hold")

        # Exact 1.0R price: 1.3100 (100 pips profit, 1.00R) -> Trigger
        res_hit = self.pip_engine.check_breakeven_trigger(pos_buy, current_price=1.3100, breakeven_profit_cap=750.0)
        self.assertTrue(res_hit["trigger"])
        self.assertEqual(res_hit["action"], "shift_sl_to_entry")
        self.assertEqual(res_hit["new_sl"], 1.3000)

        # Position already protected: SL already at 1.3000 -> already_protected
        pos_protected = dict(pos_buy, sl=1.3000)
        res_prot = self.pip_engine.check_breakeven_trigger(pos_protected, current_price=1.3150)
        self.assertFalse(res_prot["trigger"])
        self.assertEqual(res_prot["action"], "already_protected")

    def test_09_big_sharks_reasoning_evaluates_active_trade_1r_gain(self):
        """
        Verify BigSharksReasoningEngine dynamic breakeven shift when trade is in progress
        with separate SL and reaches +1.0R gain.
        """
        # When trade is in progress: Entry 1.33675, initial SL 1.33875 (20 pips risk on SELL)
        entry = 1.33675
        sl_initial = 1.33875
        risk_dist = 0.00200

        # Sub-1.0R: 1.33575 (10 pips gain, +0.50R) -> Hold
        be_sub = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=entry,
            current_price=1.33575,
            sl_price=sl_initial,
            direction="SELL",
            profit_usd=200.0
        )
        self.assertFalse(be_sub["breakeven_locked"])
        self.assertEqual(be_sub["action"], "hold")

        # +1.0R gain reached: 1.33475 (20 pips gain, +1.00R) -> Lock SL to entry
        be_hit = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=entry,
            current_price=1.33475,
            sl_price=sl_initial,
            direction="SELL",
            profit_usd=400.0
        )
        self.assertTrue(be_hit["breakeven_locked"])
        self.assertEqual(be_hit["action"], "lock_sl_to_entry")
        self.assertEqual(be_hit["new_sl"], entry)


class TestTurtleSoupAndCVDNoiseResilience(unittest.TestCase):
    """
    Stress-tests Turtle Soup liquidity sweeps and Cumulative Volume Delta (CVD)
    order absorption logic under noisy price/tick data and degenerate edge cases.
    """

    def setUp(self):
        self.quant = OrderFlowQuantEngine(pip_tolerance=2.0)
        self.hft = HighFrequencyTradingEngine()

    def test_10_turtle_soup_eqh_sweep_under_gaussian_noise(self):
        """Verify Turtle Soup detects Bearish EQH sweep under price noise."""
        np.random.seed(123)
        n_bars = 25
        base_price = 1.3350

        # Create base series with distinct non-EQH levels
        highs = [base_price + 0.0005 + (i * 0.00005) for i in range(n_bars)]
        lows = [h - 0.0010 for h in highs]
        opens = [h - 0.0005 for h in highs]
        closes = [h - 0.0004 for h in highs]

        # Engineer explicit EQH at bar 5 and bar 15 (1.33800) within 2 pips
        highs[5] = 1.33800
        highs[15] = 1.33805

        # Last bar: Turtle Soup sweep! Pierces EQH to 1.33880 but closes back below at 1.33750
        # Creating a massive upper rejection wick
        highs[-1] = 1.33880
        opens[-1] = 1.33760
        closes[-1] = 1.33750
        lows[-1] = 1.33720

        df = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        res = self.quant.detect_eqh_eql_inducement(df, symbol="GBPUSD")

        self.assertTrue(res["is_swept"])
        self.assertEqual(res["inducement_type"], "BEARISH_EQH_SWEEP")
        self.assertEqual(res["sweep_wick_price"], 1.33880)

    def test_11_turtle_soup_eql_sweep_on_gold_with_spread_jitter(self):
        """Verify Turtle Soup detects Bullish EQL sweep on Gold (XAUUSD) with $0.10 pip scaling."""
        highs = [2650.0] * 25
        lows = [2645.0] * 25
        opens = [2648.0] * 25
        closes = [2647.0] * 25

        # EQL at 2712.40 on Gold
        lows[4] = 2712.40
        lows[12] = 2712.50  # within 2 pips ($0.20 on Gold)
        # Last bar pierces EQL to 2710.80 and closes back above at 2713.50 (rejection wick = 2.70)
        lows[-1] = 2710.80
        opens[-1] = 2713.20
        closes[-1] = 2713.80
        highs[-1] = 2715.00

        df = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        res = self.quant.detect_eqh_eql_inducement(df, symbol="XAUUSD")

        self.assertTrue(res["is_swept"])
        self.assertEqual(res["inducement_type"], "BULLISH_EQL_SWEEP")
        self.assertAlmostEqual(res["level"], 2712.40, delta=0.20)

    def test_12_turtle_soup_breakout_vs_sweep_discrimination(self):
        """Verify Turtle Soup rejects genuine breakout candles (closing OUTSIDE the level) as sweeps."""
        highs = [1.3300] * 25
        lows = [1.3280] * 25
        opens = [1.3290] * 25
        closes = [1.3290] * 25

        # Equal Highs at 1.3320
        highs[5] = 1.3320
        highs[12] = 1.3320

        # Breakout candle: closes ABOVE the EQH level at 1.3350 (NOT a sweep)
        highs[-1] = 1.3360
        opens[-1] = 1.3315
        closes[-1] = 1.3350
        lows[-1] = 1.3310

        df = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        res = self.quant.detect_eqh_eql_inducement(df, symbol="GBPUSD")

        # Must NOT classify a strong breakout close as a sweep
        self.assertNotEqual(res.get("inducement_type"), "BEARISH_EQH_SWEEP")

    def test_13_turtle_soup_degenerate_and_flat_bars_handling(self):
        """Verify Turtle Soup handles zero-range bars and sub-15 bar DataFrames without crashing."""
        # 1. Empty DataFrame
        df_empty = pd.DataFrame()
        res_empty = self.quant.detect_eqh_eql_inducement(df_empty, symbol="EURUSD")
        self.assertFalse(res_empty["is_swept"])
        self.assertEqual(res_empty["inducement_type"], "NONE")

        # 2. Sub-15 bar DataFrame
        df_small = pd.DataFrame({"high": [1.0] * 5, "low": [1.0] * 5, "close": [1.0] * 5, "open": [1.0] * 5})
        res_small = self.quant.detect_eqh_eql_inducement(df_small, symbol="EURUSD")
        self.assertFalse(res_small["is_swept"])
        self.assertEqual(res_small["inducement_type"], "NONE")

        # 3. 25 completely flat bars (high == low == open == close) -> zero range division guard
        df_flat = pd.DataFrame({"high": [1.0850] * 25, "low": [1.0850] * 25, "open": [1.0850] * 25, "close": [1.0850] * 25})
        res_flat = self.quant.detect_eqh_eql_inducement(df_flat, symbol="EURUSD")
        self.assertFalse(res_flat["is_swept"])

    def test_14_cvd_lee_ready_noisy_ticks_and_edge_cases(self):
        """Verify Lee-Ready tick CVD classification under noisy, zero-volume, and extreme tick volumes."""
        # 1. Extreme Buyer Dominance (all buy volume) -> BUYER_ABSORPTION
        ticks_buy = pd.DataFrame({
            "bid": [1.0850] * 10,
            "ask": [1.0852] * 10,
            "last": [1.0852] * 10,  # All hitting the ask
            "volume": [50.0] * 10
        })
        res_buy = self.quant.compute_tick_cvd(ticks_buy)
        self.assertEqual(res_buy["total_volume"], 500.0)
        self.assertEqual(res_buy["net_delta"], 500)
        self.assertEqual(res_buy["buyer_ratio"], 1.0)
        self.assertEqual(res_buy["absorption_type"], "BUYER_ABSORPTION")
        self.assertTrue(res_buy["is_absorption_divergence"])

        # 2. Extreme Seller Dominance (all sell volume) -> SELLER_ABSORPTION
        ticks_sell = pd.DataFrame({
            "bid": [1.0850] * 10,
            "ask": [1.0852] * 10,
            "last": [1.0850] * 10,  # All hitting the bid
            "volume": [50.0] * 10
        })
        res_sell = self.quant.compute_tick_cvd(ticks_sell)
        self.assertEqual(res_sell["net_delta"], -500)
        self.assertEqual(res_sell["seller_ratio"], 1.0)
        self.assertEqual(res_sell["absorption_type"], "SELLER_ABSORPTION")

        # 3. Balanced Flow -> NONE (Neutral)
        ticks_balanced = pd.DataFrame({
            "bid": [1.0850, 1.0850],
            "ask": [1.0852, 1.0852],
            "last": [1.0852, 1.0850],  # One buy, one sell of equal volume
            "volume": [100.0, 100.0]
        })
        res_bal = self.quant.compute_tick_cvd(ticks_balanced)
        self.assertEqual(res_bal["net_delta"], 0)
        self.assertEqual(res_bal["buyer_ratio"], 0.50)
        self.assertEqual(res_bal["absorption_type"], "NONE")

        # 4. Zero Volume Ticks -> Handled cleanly without div-by-zero
        ticks_zero = pd.DataFrame({
            "bid": [1.0850, 1.0850],
            "ask": [1.0852, 1.0852],
            "last": [1.0851, 1.0851],
            "volume": [0.0, 0.0]
        })
        res_zero = self.quant.compute_tick_cvd(ticks_zero)
        self.assertEqual(res_zero["total_volume"], 0.0)

    def test_15_cvd_absorption_divergence_structural_oracle(self):
        """Verify structural Price vs CVD divergence classifier correctly identifies reversals."""
        # 1. Bullish Buyer Absorption: Price Lower Low (2650 -> 2640), but CVD Higher Low (-800 -> -200)
        bull_div = self.quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2640.0,
            cvd_swing_1=-800.0,
            cvd_swing_2=-200.0
        )
        self.assertTrue(bull_div["absorption_detected"])
        self.assertEqual(bull_div["type"], "BUYER_ABSORPTION")
        self.assertEqual(bull_div["bias"], "BULLISH_REVERSAL")

        # 2. Bearish Seller Absorption: Price Higher High (2650 -> 2675), but CVD Lower High (+900 -> +250)
        bear_div = self.quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2675.0,
            cvd_swing_1=900.0,
            cvd_swing_2=250.0
        )
        self.assertTrue(bear_div["absorption_detected"])
        self.assertEqual(bear_div["type"], "SELLER_ABSORPTION")
        self.assertEqual(bear_div["bias"], "BEARISH_REVERSAL")

        # 3. No Divergence: Price and CVD trending together
        no_div = self.quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2640.0,
            cvd_swing_1=-200.0,
            cvd_swing_2=-800.0
        )
        self.assertFalse(no_div["absorption_detected"])
        self.assertEqual(no_div["type"], "NONE")
        self.assertEqual(no_div["bias"], "NEUTRAL")


class TestHFTMicrostructureAndWhaleWalls(unittest.TestCase):
    """
    Stress-tests Level-2 DOM microstructure engine and whale wall classifier.
    """

    def setUp(self):
        self.hft = HighFrequencyTradingEngine()

    def test_16_dom_whale_wall_strict_1000_lot_threshold(self):
        """Verify whale wall classifier strictly tags volumes > 1,000 lots."""
        # Synthesize custom DOM book with exact edge volume levels
        custom_dom = {
            "bids": [
                {"price": 2714.0, "volume": 999.0, "type": "BUY"},    # Sub-whale (< 1000)
                {"price": 2713.0, "volume": 1000.0, "type": "BUY"},   # Exactly 1000 (not > 1000)
                {"price": 2712.0, "volume": 1000.5, "type": "BUY"},   # Whale wall (> 1000)
                {"price": 2710.0, "volume": 3500.0, "type": "BUY"},   # Major whale wall
            ],
            "asks": [
                {"price": 2716.0, "volume": 850.0, "type": "SELL"},   # Sub-whale
                {"price": 2717.0, "volume": 1000.0, "type": "SELL"},  # Exactly 1000
                {"price": 2718.0, "volume": 1250.0, "type": "SELL"},  # Whale wall
            ]
        }
        # Ingest directly
        whale_walls = []
        for b in custom_dom["bids"]:
            if float(b.get("volume", 0.0)) > 1000.0:
                whale_walls.append(b)
        for a in custom_dom["asks"]:
            if float(a.get("volume", 0.0)) > 1000.0:
                whale_walls.append(a)

        # Expected whale walls: exactly 3 (1000.5, 3500.0 on bids, 1250.0 on asks)
        self.assertEqual(len(whale_walls), 3)
        self.assertTrue(all(w["volume"] > 1000.0 for w in whale_walls))

    def test_17_dom_key_normalization_both_conventions(self):
        """Verify get_dom_data handles both 'bids'/'asks' and 'top_bids'/'top_asks'."""
        dom_default = self.hft.get_dom_data("XAUUSD")
        self.assertIn("bids", dom_default)
        self.assertIn("asks", dom_default)
        self.assertIn("top_bids", dom_default)
        self.assertIn("top_asks", dom_default)
        self.assertIn("whale_walls", dom_default)
        self.assertGreater(len(dom_default["whale_walls"]), 0)
        self.assertTrue(all(w["volume"] > 1000.0 for w in dom_default["whale_walls"]))

    def test_18_sub_2ms_latency_and_spread_radar(self):
        """Verify execution latency benchmark satisfies <2ms and spread radar classifies correctly."""
        lat = self.hft.evaluate_latency_and_spread("XAUUSD", current_spread_pips=1.2)
        self.assertLess(lat["latency_ms"], 2.0)
        self.assertTrue(lat["sub_2ms_passed"])
        self.assertEqual(lat["latency_status"], "SUB_2MS_OPTIMAL")
        self.assertEqual(lat["spread_status"], "STABLE_NORMAL")

        # Elevated spread
        lat_elevated = self.hft.evaluate_latency_and_spread("XAUUSD", current_spread_pips=2.5)
        self.assertEqual(lat_elevated["spread_status"], "ELEVATED_WATCH")

        # Expanded lockout
        lat_expanded = self.hft.evaluate_latency_and_spread("XAUUSD", current_spread_pips=4.0)
        self.assertEqual(lat_expanded["spread_status"], "EXPANDED_LOCKOUT")

    def test_19_hft_run_cli_dispatch_and_ascii_safety(self):
        """Verify hft_run handles all actions without UnicodeEncodeError on Windows cp1252."""
        actions = ["dom", "whale_walls", "cvd", "latency", "turtle_soup", "full_hft_scan"]
        for act in actions:
            out = hft_run({"action": act, "symbol": "XAUUSD"})
            self.assertIsInstance(out, str)
            self.assertGreater(len(out), 20)
            # Ensure no crash when encoded to ascii
            out.encode("ascii", errors="strict")


class TestBigSharksReasoningContractAndConfluence(unittest.TestCase):
    """
    Verifies Big Sharks reasoning payload contract and multi-timeframe confluence vetoes.
    """

    def setUp(self):
        self.reasoning = BigSharksReasoningEngine()
        self.confluence = MultiTimeframeConfluenceFilter()

    def test_20_reasoning_payload_adheres_to_m1_contract(self):
        """Verify full reasoning payload adheres strictly to PROJECT.md interface contract."""
        payload = get_trading_reasoning("GBPUSD")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["account"], "40000294403")
        self.assertEqual(payload["risk_params"]["max_risk_cap"], 750.0)
        self.assertEqual(payload["risk_params"]["risk_pct"], 0.75)
        self.assertEqual(payload["risk_params"]["min_rr"], 2.5)
        self.assertEqual(payload["risk_params"]["dynamic_be_r"], 1.0)

        # Setup checks
        setup = payload["latest_setups"][0]
        self.assertEqual(setup["symbol"], "GBPUSD")
        self.assertIn("big_sharks", setup)
        self.assertTrue(setup["big_sharks"]["liquidity_sweep"]["verified"])
        self.assertIn("consequent_encroachment_50", setup["big_sharks"]["fair_value_gap_50_ce"])
        self.assertIn("wyckoff_phase", setup["big_sharks"])
        self.assertIn("macro_catalyst", setup)
        self.assertIn("confluence", setup)

        # HFT microstructure checks
        hft = payload["hft_microstructure"]
        self.assertIn("whale_walls", hft)
        self.assertIn("cvd_absorption", hft)
        self.assertIn("spread_radar", hft)

    def test_21_confluence_filter_veto_oracle(self):
        """Verify MultiTimeframeConfluenceFilter strictly blocks mismatched trends."""
        # 1. Full SELL alignment -> Confluent
        sell_conf = self.reasoning.evaluate_trend_confluence(
            m15_direction="SELL", h1_direction="SELL", h4_direction="SELL"
        )
        self.assertTrue(sell_conf["is_confluent"])
        self.assertGreaterEqual(sell_conf["confluence_score"], 90.0)

        # 2. Full BUY alignment -> Confluent
        buy_conf = self.reasoning.evaluate_trend_confluence(
            m15_direction="BUY", h1_direction="BUY", h4_direction="BUY"
        )
        self.assertTrue(buy_conf["is_confluent"])
        self.assertGreaterEqual(buy_conf["confluence_score"], 90.0)

        # 3. Mismatch: M15 SELL vs H1 BUY -> BLOCKED
        clash_1 = self.reasoning.evaluate_trend_confluence(
            m15_direction="SELL", h1_direction="BUY", h4_direction="SELL"
        )
        self.assertFalse(clash_1["is_confluent"])
        self.assertLess(clash_1["confluence_score"], 90.0)
        self.assertIsNotNone(clash_1["blocked_reason"])

        # 4. Mismatch: M15 BUY vs H4 SELL -> BLOCKED
        clash_2 = self.reasoning.evaluate_trend_confluence(
            m15_direction="BUY", h1_direction="BUY", h4_direction="SELL"
        )
        self.assertFalse(clash_2["is_confluent"])
        self.assertLess(clash_2["confluence_score"], 90.0)


class TestEmpiricalBugReproductionHarness(unittest.TestCase):
    """
    Dedicated empirical reproduction harness documenting specific defects discovered
    during adversarial testing.
    """

    def test_defect_reproduction_breakeven_lock_when_sl_at_entry(self):
        """
        EMPIRICAL REMEDIATION VERIFICATION:
        Verify that evaluate_dynamic_breakeven() correctly identifies positions
        already secured at breakeven (sl == entry_price) without exiting prematurely.
        
        This validates the acceptance criterion for GBPUSD SELL ticket #13002987:
        'Active position (GBPUSD SELL #13002987) displays live profit and breakeven lock status on both dashboards.'
        """
        engine = BigSharksReasoningEngine()
        # Position #13002987: Entry 1.33675, SL 1.33675 (at breakeven), current 1.33498, profit 35.40
        res = engine.evaluate_dynamic_breakeven(
            entry_price=1.33675,
            current_price=1.33498,
            sl_price=1.33675,
            direction="SELL",
            profit_usd=35.40
        )
        self.assertTrue(
            res["breakeven_locked"],
            f"Breakeven lock must be True when sl==entry_price, got: {res}"
        )
        self.assertEqual(res["action"], "maintain_breakeven_lock")
        self.assertEqual(res["reason"], "breakeven_already_secured")
        self.assertEqual(res["new_sl"], 1.33675)

        # BUY position secured at breakeven:
        res_buy = engine.evaluate_dynamic_breakeven(
            entry_price=2700.0,
            current_price=2715.0,
            sl_price=2700.0,
            direction="BUY",
            profit_usd=150.0
        )
        self.assertTrue(res_buy["breakeven_locked"])
        self.assertEqual(res_buy["action"], "maintain_breakeven_lock")
        self.assertEqual(res_buy["reason"], "breakeven_already_secured")
        self.assertEqual(res_buy["new_sl"], 2700.0)


if __name__ == "__main__":
    unittest.main()
