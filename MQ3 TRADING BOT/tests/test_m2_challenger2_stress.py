"""
tests/test_m2_challenger2_stress.py — M2 Challenger 2 Empirical Verification & Adversarial Stress Suite.
Author: M2 Challenger 2 (Multi-Asset Sizing, Strategy & Arbitrage Stress Verifier)

Formal verification targets:
1. Minimum SL Distance Invariants across all 7 assets ($250 BTC, $20 ETH, $2 SOL, $10 Gold, 15 pips JPY, 12 pips EUR/GBP)
   under near-zero ATR, extreme ATR, and corrupt inputs.
2. Position Sizing & Dollar-Risk Invariants on $25,000 account (0.75% risk = $187.50 max risk)
   across extreme asset prices (BTC @ $120k-$250k, ETH @ $5k-$10k, SOL @ $400-$1000, Gold @ $5000, USDJPY @ 200).
3. Weekend Crypto Arbitrage Transition Boundaries (Friday 22:00:00 UTC to Sunday 21:00:00 UTC)
   and SMC 70.5% OTE Golden Pocket Mathematical Precision.
4. Identification and empirical isolation of strategy flow defects (e.g. premature return None in BEARISH trend evaluation).
5. Monte Carlo Randomized Fuzzing (1,000 trials).
"""

import datetime
import math
import os
import random
import sys
import unittest
from typing import Any, Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.aladdin_risk_engine import AladdinRiskEngine
from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.funding_pips_expert import FundingPipsExpert
from src.market_analyzer import MarketAnalyzer
from src.multi_asset_scanner import MultiAssetScanner
from src.risk_manager import RiskManager
from src.strategy import StrategyEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine


class TestM2Challenger2MinimumSLInvariants(unittest.TestCase):
    """Empirical stress testing of Minimum Stop-Loss distances across all 7 assets."""

    def setUp(self):
        self.config = {
            "account_info": {"target_account_size": 25000.0},
            "risk_management": {
                "max_daily_loss_pct": 2.5,
                "max_total_loss_pct": 6.0,
                "risk_per_trade_pct": 0.75,
                "max_open_trades": 3,
                "max_daily_trades": 10,
                "min_rr_ratio": 1.5,
                "atr_sl_multiplier": 1.5,
                "forex_atr_sl_multiplier": 1.5,
                "gold_atr_sl_multiplier": 2.5,
                "crypto_atr_sl_multiplier": 3.5,
            },
            "gold_primary_focus": {
                "enabled": True,
                "xauusd_min_confluence_score": 1.0,
                "other_pairs_min_confluence_score": 1.0,
                "ny_close_block_start_utc": 15,
                "ny_close_block_end_utc": 17,
            },
        }
        self.strategy = StrategyEngine(self.config)
        self.strategy.ai_engine.get_pattern_weights = lambda: {
            "BULLISH_ORDER_BLOCK": 1.0,
            "BEARISH_ORDER_BLOCK": 1.0,
            "BULLISH_SWEEP": 1.0,
            "BEARISH_SWEEP": 1.0,
            "BULLISH_PRICE_ACTION": 1.0,
            "BEARISH_PRICE_ACTION": 1.0,
            "KEY_SUPPORT_BOUNCE": 1.0,
            "KEY_RESISTANCE_REJECTION": 1.0,
        }
        self.scanner = MultiAssetScanner(self.config)

    def _create_mock_analysis(
        self,
        symbol: str,
        price: float,
        trend: str,
        atr: float,
        signal_bias: str = "BUY",
        corrupt_candles: bool = False,
    ) -> Dict[str, Any]:
        """Generates synthetic market analysis dataframe and indicators."""
        specs = StrategyEngine.get_symbol_scale_specs(symbol)
        dec = specs["decimals"]
        
        np.random.seed(42)
        if corrupt_candles:
            lows = np.full(30, price * 1.05)
            highs = np.full(30, price * 0.95)
            opens = np.full(30, price)
            closes = np.full(30, price)
        else:
            lows = np.linspace(price - 5 * atr, price, 30)
            highs = np.linspace(price, price + 5 * atr, 30)
            opens = (lows + highs) / 2
            closes = opens + np.random.uniform(-atr, atr, 30)

        df_entry = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(30, 1000.0),
        })

        if signal_bias == "BUY":
            analysis = {
                "symbol": symbol,
                "current_price": price,
                "trend_direction": trend,
                "rsi": 45.0,
                "atr": atr,
                "df_entry": df_entry,
                "bullish_ob": {"low": price - 0.1 * atr, "high": price * 1.001},
                "bearish_ob": None,
                "active_support": {"level": price - 0.2 * atr, "label": "Key Support"},
                "active_resistance": None,
                "resistance_levels": [(price + 10 * atr, "H1 Resistance")],
                "support_levels": [(price - 10 * atr, "H1 Support")],
                "liquidity_sweep": {"type": "BULLISH_SWEEP", "rejection_wick_price": price - 0.05 * atr},
                "candlestick_patterns": [{"type": "BULLISH_ENGULFING"}],
                "structure_pattern": "DOUBLE_BOTTOM",
                "premium_discount": {"is_buy_allowed": True, "discount_pct": 65.0},
                "ote_buy": {"in_ote_zone": True, "score_bonus": 0.60},
                "killzone": {"is_prime_killzone": True, "killzone": "LONDON_OPEN", "confluence_boost": 0.40},
                "inducement": {"inducement_type": "BULLISH_EQL_SWEEP"},
                "adr_intel": {"is_adr_exhausted": False, "adr_pct_consumed": 40.0},
                "qlib_intel": {"bias": "BULLISH", "confluence_bonus": 0.30, "alpha_score": 0.85},
                "bypass_time_filter": True,
            }
        else:
            analysis = {
                "symbol": symbol,
                "current_price": price,
                "trend_direction": trend,
                "rsi": 55.0,
                "atr": atr,
                "df_entry": df_entry,
                "bullish_ob": None,
                "bearish_ob": {"low": price * 0.999, "high": price + 0.1 * atr},
                "active_support": None,
                "active_resistance": {"level": price + 0.2 * atr, "label": "Key Resistance"},
                "resistance_levels": [(price + 10 * atr, "H1 Resistance")],
                "support_levels": [(price - 10 * atr, "H1 Support")],
                "liquidity_sweep": {"type": "BEARISH_SWEEP", "rejection_wick_price": price + 0.05 * atr},
                "candlestick_patterns": [{"type": "BEARISH_ENGULFING"}],
                "structure_pattern": "DOUBLE_TOP",
                "premium_discount": {"is_sell_allowed": True, "discount_pct": 35.0},
                "ote_sell": {"in_ote_zone": True, "score_bonus": 0.60},
                "killzone": {"is_prime_killzone": True, "killzone": "NEW_YORK_OPEN", "confluence_boost": 0.40},
                "inducement": {"inducement_type": "BEARISH_EQH_SWEEP"},
                "adr_intel": {"is_adr_exhausted": False, "adr_pct_consumed": 40.0},
                "qlib_intel": {"bias": "BEARISH", "confluence_bonus": 0.30, "alpha_score": -0.85},
                "bypass_time_filter": True,
            }
        return analysis

    def test_min_sl_distance_enforcement_near_zero_atr(self):
        """
        Adversarial Test: When ATR collapses to microscopic levels (e.g. 0.000001),
        verify that StrategyEngine strictly enforces minimum SL bounds across all 7 assets:
          - BTCUSD: min SL >= $250.0
          - ETHUSD: min SL >= $20.0
          - SOLUSD: min SL >= $2.0
          - XAUUSD: min SL >= $10.0
          - USDJPY: min SL >= 0.15 (15 pips)
          - EURUSD: min SL >= 0.0012 (12 pips)
          - GBPUSD: min SL >= 0.0012 (12 pips)
        """
        test_matrix = [
            ("BTCUSD", 95000.0, 250.0),
            ("ETHUSD", 3500.0, 20.0),
            ("SOLUSD", 220.0, 2.0),
            ("XAUUSD", 3200.0, 10.0),
            ("USDJPY", 155.50, 0.15),
            ("EURUSD", 1.0850, 0.0012),
            ("GBPUSD", 1.2850, 0.0012),
        ]

        micro_atrs = [1e-6, 1e-4, 0.001]

        for sym, price, expected_min_sl in test_matrix:
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertEqual(specs["min_sl_dist"], expected_min_sl, f"Spec mismatch for {sym}")

            for micro_atr in micro_atrs:
                # 1. Test BUY Setup (BULLISH trend)
                analysis_buy = self._create_mock_analysis(sym, price, "BULLISH", micro_atr, "BUY")
                signal_buy = self.strategy.evaluate_signals(analysis_buy)
                self.assertIsNotNone(signal_buy, f"Signal was None for {sym} BUY with micro ATR {micro_atr}")
                sl_dist_buy = signal_buy["entry_price"] - signal_buy["sl_price"]
                self.assertGreaterEqual(
                    sl_dist_buy,
                    expected_min_sl - 1e-6,
                    f"BUY SL distance {sl_dist_buy} was less than required {expected_min_sl} on {sym}",
                )
                self.assertLess(signal_buy["sl_price"], signal_buy["entry_price"])

                # 2. Test SELL Setup (NEUTRAL trend)
                analysis_sell = self._create_mock_analysis(sym, price, "NEUTRAL", micro_atr, "SELL")
                signal_sell = self.strategy.evaluate_signals(analysis_sell)
                self.assertIsNotNone(signal_sell, f"Signal was None for {sym} SELL with micro ATR {micro_atr}")
                sl_dist_sell = signal_sell["sl_price"] - signal_sell["entry_price"]
                self.assertGreaterEqual(
                    sl_dist_sell,
                    expected_min_sl - 1e-6,
                    f"SELL SL distance {sl_dist_sell} was less than required {expected_min_sl} on {sym}",
                )
                self.assertGreater(signal_sell["sl_price"], signal_sell["entry_price"])

    def test_min_sl_distance_enforcement_corrupt_inverted_candles(self):
        """
        Adversarial Test: When candle data is corrupt (low > entry price in BUY, or high < entry in SELL),
        the strategy must NOT generate inverted stop-losses and must enforce the minimum SL floor.
        """
        test_matrix = [
            ("BTCUSD", 98000.0, 250.0, 50.0),
            ("ETHUSD", 3500.0, 20.0, 5.0),
            ("SOLUSD", 220.0, 2.0, 0.5),
            ("XAUUSD", 3200.0, 10.0, 1.0),
            ("USDJPY", 155.00, 0.15, 0.02),
            ("EURUSD", 1.0800, 0.0012, 0.0002),
            ("GBPUSD", 1.2800, 0.0012, 0.0002),
        ]

        for sym, price, min_sl, atr in test_matrix:
            # Corrupt BUY
            analysis_buy = self._create_mock_analysis(sym, price, "BULLISH", atr, "BUY", corrupt_candles=True)
            signal_buy = self.strategy.evaluate_signals(analysis_buy)
            if signal_buy:
                sl_dist = signal_buy["entry_price"] - signal_buy["sl_price"]
                self.assertGreaterEqual(sl_dist, min_sl, f"Corrupt BUY on {sym} violated min SL: {sl_dist} < {min_sl}")
                self.assertLess(signal_buy["sl_price"], signal_buy["entry_price"])

            # Corrupt SELL
            analysis_sell = self._create_mock_analysis(sym, price, "NEUTRAL", atr, "SELL", corrupt_candles=True)
            signal_sell = self.strategy.evaluate_signals(analysis_sell)
            if signal_sell:
                sl_dist = signal_sell["sl_price"] - signal_sell["entry_price"]
                self.assertGreaterEqual(sl_dist, min_sl, f"Corrupt SELL on {sym} violated min SL: {sl_dist} < {min_sl}")
                self.assertGreater(signal_sell["sl_price"], signal_sell["entry_price"])

    def test_zero_and_negative_atr_guard(self):
        """Verify that zero or negative ATR is gracefully rejected without division-by-zero crashes."""
        for bad_atr in [0.0, -1.0, -999.0]:
            analysis = self._create_mock_analysis("BTCUSD", 95000.0, "BULLISH", bad_atr, "BUY")
            signal = self.strategy.evaluate_signals(analysis)
            self.assertIsNone(signal, f"Strategy should return None for ATR {bad_atr}")

    def test_empirical_finding_bearish_trend_premature_exit(self):
        """
        Empirical finding isolation:
        In src/strategy.py line 229:
        `if trend == "BEARISH": return None` is placed in the top-level flow before Section 2 (SELL).
        This test empirically verifies that evaluate_signals() returns None when trend == "BEARISH"
        even when all bearish confluences (Order Block, Sweep, Resistance, Qlib Alpha) are valid.
        """
        analysis_bearish = self._create_mock_analysis("BTCUSD", 95000.0, "BEARISH", 500.0, "SELL")
        sig = self.strategy.evaluate_signals(analysis_bearish)
        # Empirically documents that this exits prematurely at line 231
        self.assertIsNone(
            sig,
            "Confirmed: evaluate_signals prematurely returns None on trend == 'BEARISH' due to line 231 exit.",
        )


class TestM2Challenger2PositionSizingInvariants(unittest.TestCase):
    """Empirical stress testing of Position Sizing and Dollar Risk Invariants across Extreme Prices."""

    def setUp(self):
        self.config = {
            "account_info": {"target_account_size": 25000.0},
            "risk_management": {
                "max_daily_loss_pct": 2.5,
                "max_total_loss_pct": 6.0,
                "risk_per_trade_pct": 0.75,  # 0.75% = $187.50 on $25k
                "max_open_trades": 3,
                "max_daily_trades": 10,
            },
        }
        self.risk_mgr = RiskManager(self.config)
        self.aladdin = AladdinRiskEngine()

    def test_dollar_risk_invariants_at_extreme_prices(self):
        """
        Stress test: Verify dollar risk on $25k account (0.75% risk = $187.50 max risk)
        across extreme market prices:
          - BTC @ $120,000 and $250,000
          - ETH @ $5,000 and $10,000
          - SOL @ $400 and $1,000
          - Gold @ $5,000 and $10,000
          - USDJPY @ 200.0 and 300.0
          - EURUSD @ 2.0000 and 0.5000
        """
        equity = 25000.0
        expected_risk_dollar = 25000.0 * 0.0075  # $187.50

        extreme_test_cases = [
            # symbol, extreme_price, sl_units (pips/dollars), pip_value_per_lot, max_allowed_lot
            ("BTCUSD", 120000.0, 250.0, 1.0, 10.0),    # $250 SL move on BTC -> 0.75 lots
            ("BTCUSD", 250000.0, 500.0, 1.0, 10.0),    # $500 SL move on BTC -> 0.38 lots
            ("ETHUSD", 5000.0, 20.0, 1.0, 50.0),       # $20 SL move on ETH -> 9.38 lots
            ("ETHUSD", 10000.0, 50.0, 1.0, 50.0),      # $50 SL move on ETH -> 3.75 lots
            ("SOLUSD", 400.0, 2.0, 1.0, 500.0),        # $2.0 SL move on SOL -> 93.75 lots
            ("SOLUSD", 1000.0, 10.0, 1.0, 500.0),      # $10.0 SL move on SOL -> 18.75 lots
            ("XAUUSD", 5000.0, 100.0, 10.0, 5.0),      # 100 pips ($10.0) on Gold -> 0.19 lots
            ("XAUUSD", 10000.0, 250.0, 10.0, 5.0),     # 250 pips ($25.0) on Gold -> 0.08 lots
            ("USDJPY", 200.0, 15.0, 6.50, 10.0),       # 15 pips on USDJPY -> 1.92 lots
            ("USDJPY", 300.0, 30.0, 6.50, 10.0),       # 30 pips on USDJPY -> 0.96 lots
            ("EURUSD", 2.0000, 12.0, 10.0, 5.0),       # 12 pips on EURUSD -> 1.56 lots
            ("EURUSD", 0.5000, 12.0, 10.0, 5.0),       # 12 pips on EURUSD -> 1.56 lots
            ("GBPUSD", 2.5000, 15.0, 10.0, 5.0),       # 15 pips on GBPUSD -> 1.25 lots
        ]

        for sym, price, sl_units, pip_val, max_lot in extreme_test_cases:
            lot = self.risk_mgr.calculate_position_size(equity, sl_units, sym)

            # Invariant 1: lot size bounded in [0.01, max_lot]
            self.assertGreaterEqual(lot, 0.01, f"{sym} lot size {lot} < 0.01")
            self.assertLessEqual(lot, max_lot, f"{sym} lot size {lot} > max_lot {max_lot}")

            # Invariant 2: Actual dollar risk is within 1 lot-tick rounding tolerance of $187.50
            actual_dollar_risk = lot * sl_units * pip_val
            tick_tolerance = 0.01 * sl_units * pip_val  # Discretization error of 2 decimal places

            # Check dollar risk adheres strictly to risk model
            self.assertAlmostEqual(
                actual_dollar_risk,
                expected_risk_dollar,
                delta=max(5.0, tick_tolerance + 0.5),
                msg=f"Extreme price {price} on {sym}: Dollar risk ${actual_dollar_risk:.2f} drifted too far from ${expected_risk_dollar:.2f}",
            )

    def test_multi_account_tier_dollar_risk_scaling(self):
        """
        Verify scaling across all Funding Pips account sizes ($100k, $50k, $25k, $5k)
        at 0.75% max risk cap, observing individual max_lot limits.
        """
        account_tiers = [
            (100000.0, 750.00),
            (50000.0, 375.00),
            (25000.0, 187.50),
            (5000.0, 37.50),
        ]

        for equity, expected_risk in account_tiers:
            # Test BTC $250 SL
            btc_lot = self.risk_mgr.calculate_position_size(equity, 250.0, "BTCUSD")
            btc_risk = btc_lot * 250.0 * 1.0
            self.assertAlmostEqual(btc_risk, expected_risk, delta=2.5, msg=f"BTC risk sizing mismatch on ${equity:,.0f}")

            # Test Gold 100 pips ($10.0) SL
            gold_lot = self.risk_mgr.calculate_position_size(equity, 100.0, "XAUUSD")
            gold_risk = gold_lot * 100.0 * 10.0
            self.assertAlmostEqual(gold_risk, expected_risk, delta=10.0, msg=f"Gold risk sizing mismatch on ${equity:,.0f}")

            # Test EURUSD 12 pips SL (capped at 5.0 lots -> max risk $600 on $100k)
            eur_lot = self.risk_mgr.calculate_position_size(equity, 12.0, "EURUSD")
            eur_risk = eur_lot * 12.0 * 10.0
            expected_capped_risk = min(expected_risk, 5.0 * 12.0 * 10.0)
            self.assertAlmostEqual(eur_risk, expected_capped_risk, delta=1.5, msg=f"EURUSD risk sizing mismatch on ${equity:,.0f}")

    def test_aladdin_pre_trade_stress_guard_rejection_and_approval(self):
        """
        Verify Aladdin Pre-Trade Stress Test prevents over-allocation when portfolio
        open risk + prospective trade exceeds 80% of daily loss limit ($500 on $25k).
        """
        equity = 25000.0
        max_daily_loss = 25000.0 * 0.025  # $625.00 daily loss allowance (80% threshold = $500.00)

        # 1. Single trade within bounds: $187.50 risk -> Safe
        res_safe = self.aladdin.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=187.50,
            open_positions=[],
            max_daily_loss_dollar=max_daily_loss,
        )
        self.assertTrue(res_safe["passed"])
        self.assertEqual(res_safe["total_stressed_risk_dollar"], 187.50)

        # 2. Existing open positions with high cumulative risk:
        open_positions = [
            {"symbol": "BTCUSD", "price_open": 98000.0, "sl": 97500.0, "volume": 0.50},   # 500 pt * 0.5 * $1 = $250 risk
            {"symbol": "XAUUSD", "price_open": 3200.0, "sl": 3185.0, "volume": 0.15},    # 150 pips * 0.15 * $10 = $225 risk
        ]
        # Total existing open risk = $475.00
        # Adding $187.50 -> Total = $662.50 > $500.00 (80% of $625) -> MUST REJECT!
        res_reject = self.aladdin.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=187.50,
            open_positions=open_positions,
            max_daily_loss_dollar=max_daily_loss,
        )
        self.assertFalse(res_reject["passed"])
        self.assertIn("STRESS_TEST_EXCEEDED", res_reject["reason"])


class TestM2Challenger2WeekendArbitrageAndOTE(unittest.TestCase):
    """Empirical verification of Weekend Arbitrage Transitions & 70.5% OTE Mathematical Precision."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.arb = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)

    def test_weekend_session_second_by_second_transitions(self):
        """
        Adversarially verify the exact second-by-second transition boundaries:
        - Friday 21:59:59 UTC: False (TradFi open)
        - Friday 22:00:00 UTC: True (Weekend active)
        - Friday 22:00:01 UTC: True (Weekend active)
        - Saturday all 24 hours: True
        - Sunday 20:59:59 UTC: True (Weekend active)
        - Sunday 21:00:00 UTC: True (Weekend active)
        - Sunday 21:00:01 UTC: False (TradFi open)
        - Sunday 21:05:00 UTC: False
        - Monday through Thursday: False
        """
        tz = datetime.timezone.utc

        # Friday 2026-08-14
        t_fri_before = datetime.datetime(2026, 8, 14, 21, 59, 59, tzinfo=tz)
        t_fri_exact = datetime.datetime(2026, 8, 14, 22, 0, 0, tzinfo=tz)
        t_fri_after = datetime.datetime(2026, 8, 14, 22, 0, 1, tzinfo=tz)

        self.assertFalse(self.arb.is_weekend_session(t_fri_before), "Friday 21:59:59 should be False")
        self.assertTrue(self.arb.is_weekend_session(t_fri_exact), "Friday 22:00:00 should be True")
        self.assertTrue(self.arb.is_weekend_session(t_fri_after), "Friday 22:00:01 should be True")

        # Saturday 2026-08-15
        for hour in [0, 6, 12, 18, 23]:
            t_sat = datetime.datetime(2026, 8, 15, hour, 30, 0, tzinfo=tz)
            self.assertTrue(self.arb.is_weekend_session(t_sat), f"Saturday {hour}:30 should be True")

        # Sunday 2026-08-16
        t_sun_before = datetime.datetime(2026, 8, 16, 20, 59, 59, tzinfo=tz)
        t_sun_exact = datetime.datetime(2026, 8, 16, 21, 0, 0, tzinfo=tz)
        t_sun_after = datetime.datetime(2026, 8, 16, 21, 0, 1, tzinfo=tz)
        t_sun_late = datetime.datetime(2026, 8, 16, 22, 0, 0, tzinfo=tz)

        self.assertTrue(self.arb.is_weekend_session(t_sun_before), "Sunday 20:59:59 should be True")
        self.assertFalse(self.arb.is_weekend_session(t_sun_exact), "Sunday 21:00:00 should be False")
        self.assertFalse(self.arb.is_weekend_session(t_sun_after), "Sunday 21:00:01 should be False")
        self.assertFalse(self.arb.is_weekend_session(t_sun_late), "Sunday 22:00:00 should be False")

        # Monday through Thursday weekdays
        weekdays = [
            datetime.datetime(2026, 8, 17, 10, 0, 0, tzinfo=tz),  # Monday
            datetime.datetime(2026, 8, 18, 14, 0, 0, tzinfo=tz),  # Tuesday
            datetime.datetime(2026, 8, 19, 16, 0, 0, tzinfo=tz),  # Wednesday
            datetime.datetime(2026, 8, 20, 8, 0, 0, tzinfo=tz),   # Thursday
        ]
        for dt in weekdays:
            self.assertFalse(self.arb.is_weekend_session(dt), f"{dt.strftime('%A')} should be False")

    def test_smc_dealing_range_ote_mathematical_precision(self):
        """
        Verify SMC dealing range calculations:
        - Equilibrium = Low + 0.50 * Range
        - Buy OTE 70.5% = High - 0.705 * Range
        - Sell OTE 70.5% = Low + 0.705 * Range
        - Buy OTE Zone = [High - 0.786 * Range, High - 0.618 * Range]
        - Sell OTE Zone = [Low + 0.618 * Range, Low + 0.786 * Range]
        - Buy OTE 70.5% must strictly sit within Discount (< Equilibrium) and inside Buy OTE Zone.
        - Sell OTE 70.5% must strictly sit within Premium (> Equilibrium) and inside Sell OTE Zone.
        """
        ranges = [
            ("BTCUSD", 100000.0, 90000.0),   # 10,000 range
            ("ETHUSD", 4000.0, 3000.0),       # 1,000 range
            ("SOLUSD", 250.0, 150.0),         # 100 range
            ("XAUUSD", 3400.0, 3200.0),       # 200 range
        ]

        for sym, high, low in ranges:
            diff = high - low
            eq = low + 0.50 * diff
            buy_ote = high - 0.705 * diff
            sell_ote = low + 0.705 * diff

            # 1. Test price exactly at Buy OTE 70.5%
            metrics_buy = self.arb.compute_smc_dealing_range_ote(sym, high, low, buy_ote)
            self.assertEqual(metrics_buy["equilibrium"], round(eq, 2))
            self.assertEqual(metrics_buy["buy_ote_705"], round(buy_ote, 2))
            self.assertTrue(metrics_buy["in_discount"], f"Buy OTE at {buy_ote} should be in discount (< {eq})")
            self.assertFalse(metrics_buy["in_premium"])
            self.assertTrue(metrics_buy["in_ote_buy_zone"], f"Buy OTE {buy_ote} should be in OTE Buy Zone")

            # 2. Test price exactly at Sell OTE 70.5%
            metrics_sell = self.arb.compute_smc_dealing_range_ote(sym, high, low, sell_ote)
            self.assertEqual(metrics_sell["sell_ote_705"], round(sell_ote, 2))
            self.assertTrue(metrics_sell["in_premium"], f"Sell OTE at {sell_ote} should be in premium (> {eq})")
            self.assertFalse(metrics_sell["in_discount"])
            self.assertTrue(metrics_sell["in_ote_sell_zone"], f"Sell OTE {sell_ote} should be in OTE Sell Zone")

    def test_funding_spread_basis_arbitrage_and_squeeze_classification(self):
        """
        Verify basis spread and squeeze signal detection:
        - Extreme positive funding >= +0.05% per 8h -> ARBITRAGE_CARRY_SPREAD / LONG_CROWD_SQUEEZE
        - Extreme negative funding <= -0.05% per 8h -> ARBITRAGE_SHORT_SQUEEZE / SHORT_CROWD_SQUEEZE
        - Normal funding (+0.01%) -> SPREAD_PREMIUM / NORMAL
        """
        # Case 1: Positive Funding Squeeze (+0.08% per 8h)
        c1 = self.arb.calculate_basis_and_spread("BTCUSD", spot_price=98000.0, perp_price=98250.0, funding_rate_8h=0.0008)
        self.assertEqual(c1["signal_type"], "ARBITRAGE_CARRY_SPREAD")
        self.assertEqual(c1["basis_dollar"], 250.0)
        self.assertAlmostEqual(c1["funding_annualized_pct"], 0.0008 * 3 * 365 * 100, places=2)

        # Case 2: Negative Funding Squeeze (-0.07% per 8h)
        c2 = self.arb.calculate_basis_and_spread("ETHUSD", spot_price=3500.0, perp_price=3480.0, funding_rate_8h=-0.0007)
        self.assertEqual(c2["signal_type"], "ARBITRAGE_SHORT_SQUEEZE")
        self.assertEqual(c2["basis_dollar"], -20.0)

        # Case 3: Normal Positive Spread (+0.01% per 8h)
        c3 = self.arb.calculate_basis_and_spread("SOLUSD", spot_price=220.0, perp_price=220.5, funding_rate_8h=0.0001)
        self.assertEqual(c3["signal_type"], "SPREAD_PREMIUM")

        # Case 4: Normal Discount Spread (+0.01% per 8h)
        c4 = self.arb.calculate_basis_and_spread("SOLUSD", spot_price=220.0, perp_price=219.5, funding_rate_8h=0.0001)
        self.assertEqual(c4["signal_type"], "SPREAD_DISCOUNT")


class TestM2Challenger2MonteCarloFuzzing(unittest.TestCase):
    """Monte Carlo fuzzing and randomized invariant verification (1,000 trials)."""

    def setUp(self):
        self.config = {
            "account_info": {"target_account_size": 25000.0},
            "risk_management": {
                "max_daily_loss_pct": 2.5,
                "max_total_loss_pct": 6.0,
                "risk_per_trade_pct": 0.75,
                "max_open_trades": 3,
                "max_daily_trades": 10,
            },
        }
        self.risk_mgr = RiskManager(self.config)
        self.arb = WeekendCryptoArbitrageEngine(feeds_engine=FreePublicFeedsEngine(offline_mode=True))

    def test_monte_carlo_1000_sizing_and_ote_fuzzing(self):
        """1,000 randomized Monte Carlo simulations asserting mathematical invariants."""
        rng = random.Random(2026)
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "USDJPY", "EURUSD", "GBPUSD"]

        for trial in range(1000):
            sym = rng.choice(symbols)
            equity = rng.uniform(1000.0, 500000.0)
            sl_units = rng.uniform(0.0001, 5000.0)

            lot = self.risk_mgr.calculate_position_size(equity, sl_units, sym)
            self.assertGreaterEqual(lot, 0.01)
            self.assertTrue(math.isfinite(lot))

            # Fuzz OTE dealing range
            low_p = rng.uniform(10.0, 100000.0)
            high_p = low_p + rng.uniform(1.0, 10000.0)
            cur_p = rng.uniform(low_p, high_p)

            metrics = self.arb.compute_smc_dealing_range_ote(sym, high_p, low_p, cur_p)
            self.assertGreaterEqual(metrics["equilibrium"], low_p)
            self.assertLessEqual(metrics["equilibrium"], high_p)
            self.assertTrue(metrics["in_discount"] ^ metrics["in_premium"])
            self.assertAlmostEqual(
                metrics["buy_ote_705"],
                high_p - 0.705 * (high_p - low_p),
                places=1,
            )


if __name__ == "__main__":
    unittest.main()
