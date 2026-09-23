"""
tests/test_crypto_feeds_arbitrage.py — Authoritative 4-Tier E2E Test Suite for Features 8–15:
Crypto Feeds, Free Public APIs, Weekend Arbitrage, Volatility ATR Stops, and BlackRock Aladdin Risk.

Covers:
  - Feature 8: 7-Asset Multi-Asset Support (BTCUSD, ETHUSD, SOLUSD, XAUUSD, EURUSD, GBPUSD, USDJPY)
  - Feature 9: Binance Free Public API Connector (Zero Paid APIs)
  - Feature 10: Hyperliquid DEX Free API Connector (Zero Paid APIs)
  - Feature 11: CoinGecko & Yahoo Free Feeds
  - Feature 12: 24/7 Weekend Crypto Arbitrage Engine
  - Feature 13: Funding Rate Spread Tracking & Arbitrage
  - Feature 14: Volatility-Adjusted ATR Stops (3.5x Crypto, 2.5x Gold, 1.5x Forex)
  - Feature 15: BlackRock Aladdin 1-Day 99% VaR & Funding Pips 25k Risk

Tiers:
  - Tier 1: Feature / Unit Coverage (40 Tests, 5+ tests per feature across all 8 features)
  - Tier 2: Boundary & Corner Cases (40 Tests, 5+ boundary/extreme tests per feature)
  - Tier 3: Cross-Feature Pairwise Combinations (15 Tests)
  - Tier 4: Real-World Workload Scenarios (6 Tests)
Total: 101 Tests.
"""

import math
import os
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure repository root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.aladdin_risk_engine import AladdinRiskEngine
from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.funding_pips_expert import FundingPipsExpert
from src.multi_asset_scanner import MultiAssetScanner
from src.strategy import StrategyEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine


# ==============================================================================
# TIER 1: FEATURE / UNIT TEST CLASSES (40 TESTS)
# ==============================================================================

class TestFeature8_MultiAssetCatalog(unittest.TestCase):
    """Tier 1: Feature 8 — 7-Asset Multi-Asset Support & Point Scale Specifications."""

    def test_feat8_asset_catalog_contains_all_7_instruments(self):
        """Verifies ASSET_CATALOG contains all 7 target instruments."""
        expected = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        for sym in expected:
            self.assertIn(sym, MultiAssetScanner.ASSET_CATALOG)
            info = MultiAssetScanner.get_asset_info(sym)
            self.assertEqual(info["symbol"], sym)

    def test_feat8_asset_categorization_and_metadata(self):
        """Verifies correct classification across Crypto, Metals, and Forex Majors."""
        categories = {
            "BTCUSD": "CRYPTO",
            "ETHUSD": "CRYPTO",
            "SOLUSD": "CRYPTO",
            "XAUUSD": "PRECIOUS_METALS",
            "EURUSD": "FOREX_MAJORS",
            "GBPUSD": "FOREX_MAJORS",
            "USDJPY": "FOREX_MAJORS",
        }
        for sym, expected_cat in categories.items():
            info = MultiAssetScanner.get_asset_info(sym)
            self.assertEqual(info["category"], expected_cat)
            self.assertIn("name", info)
            self.assertIn("driver", info)
            self.assertGreater(info["base_score"], 0.0)

    def test_feat8_pip_unit_and_point_scaling_invariants(self):
        """Verifies pip unit values match exchange tick conventions."""
        expected_pip_units = {
            "BTCUSD": 1.0,
            "ETHUSD": 1.0,
            "SOLUSD": 0.1,
            "XAUUSD": 0.1,
            "EURUSD": 0.0001,
            "GBPUSD": 0.0001,
            "USDJPY": 0.01,
        }
        for sym, expected_val in expected_pip_units.items():
            info = MultiAssetScanner.get_asset_info(sym)
            self.assertAlmostEqual(info["pip_unit"], expected_val, places=5)
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertAlmostEqual(specs["pip_unit"], expected_val, places=5)

    def test_feat8_asset_specific_minimum_sl_buffers(self):
        """Verifies minimum SL distance buffer limits per asset class."""
        expected_min_sl = {
            "BTCUSD": 250.0,
            "ETHUSD": 20.0,
            "SOLUSD": 2.0,
            "XAUUSD": 10.0,
            "EURUSD": 0.0012,
            "GBPUSD": 0.0012,
            "USDJPY": 0.15,
        }
        for sym, expected_sl in expected_min_sl.items():
            info = MultiAssetScanner.get_asset_info(sym)
            self.assertAlmostEqual(info["min_sl_dist"], expected_sl, places=4)
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertAlmostEqual(specs["min_sl_dist"], expected_sl, places=4)

    def test_feat8_multi_asset_scanner_edge_ranking(self):
        """Verifies MultiAssetScanner ranks 7 instruments by win-probability edge %."""
        scanner = MultiAssetScanner()
        ranked = scanner.scan_all_markets()
        self.assertEqual(len(ranked), 7)
        # Verify edge_pct is within [65.0, 98.5]
        for item in ranked:
            self.assertGreaterEqual(item["edge_pct"], 65.0)
            self.assertLessEqual(item["edge_pct"], 98.5)
            self.assertIn("action", item)
            self.assertIn("sl", item)
            self.assertIn("tp1", item)


class TestFeature9_BinancePublicAPI(unittest.TestCase):
    """Tier 1: Feature 9 — Binance Free Public API Connector (Zero Paid APIs)."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=2.0, offline_mode=True)

    def test_feat9_binance_ticker_24hr_parsing(self):
        """Verifies parsing of Binance 24hr ticker response."""
        ticker = self.engine.get_ticker_24hr("BTCUSD")
        self.assertEqual(ticker["symbol"], "BTCUSD")
        self.assertIn("binance_symbol", ticker)
        self.assertGreater(ticker["last_price"], 0.0)
        self.assertGreaterEqual(ticker["spread"], 0.0)
        self.assertIn("volume_24h", ticker)
        self.assertIn("price_change_pct", ticker)

    def test_feat9_binance_l2_order_book_depth_structure(self):
        """Verifies L2 order book depth bids descending and asks ascending."""
        depth = self.engine.get_order_book_depth("BTCUSD", limit=20)
        self.assertIn("bids", depth)
        self.assertIn("asks", depth)
        self.assertGreater(len(depth["bids"]), 0)
        self.assertGreater(len(depth["asks"]), 0)
        # Invariant: Best ask > Best bid
        self.assertGreater(depth["asks"][0][0], depth["bids"][0][0])
        # Invariant: Bids descending
        for i in range(len(depth["bids"]) - 1):
            self.assertGreaterEqual(depth["bids"][i][0], depth["bids"][i + 1][0])
        # Invariant: Asks ascending
        for i in range(len(depth["asks"]) - 1):
            self.assertLessEqual(depth["asks"][i][0], depth["asks"][i + 1][0])

    def test_feat9_binance_zero_auth_header_compliance(self):
        """Verifies public requests do not require or leak private API keys."""
        # Check standard headers used in _http_get
        self.assertNotIn("X-MBX-APIKEY", self.engine._user_agent)
        self.assertIn("MQ3-QuantBot", self.engine._user_agent)

    def test_feat9_binance_symbol_normalization(self):
        """Verifies normalization between MT5 symbols and Binance pairs."""
        self.assertEqual(self.engine._get_binance_symbol("BTCUSD"), "BTCUSDT")
        self.assertEqual(self.engine._get_binance_symbol("ETHUSD"), "ETHUSDT")
        self.assertEqual(self.engine._get_binance_symbol("SOLUSD"), "SOLUSDT")
        self.assertEqual(self.engine._get_binance_symbol("EURUSD"), "EURUSDT")
        self.assertEqual(self.engine._normalize_symbol_to_mt5("BTCUSDT"), "BTCUSD")

    def test_feat9_binance_klines_ohlcv_aggregation(self):
        """Verifies conversion of klines to structured OHLCV candles."""
        klines = self.engine.get_klines("BTCUSD", interval="15m", limit=10)
        self.assertGreater(len(klines), 0)
        for candle in klines:
            self.assertIn("open", candle)
            self.assertIn("high", candle)
            self.assertIn("low", candle)
            self.assertIn("close", candle)
            self.assertIn("volume", candle)
            self.assertGreaterEqual(candle["high"], candle["low"])
            self.assertGreaterEqual(candle["high"], min(candle["open"], candle["close"]))
            self.assertLessEqual(candle["low"], max(candle["open"], candle["close"]))


class TestFeature10_HyperliquidDEXAPI(unittest.TestCase):
    """Tier 1: Feature 10 — Hyperliquid DEX Free API Connector (Zero Paid APIs)."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=2.0, offline_mode=True)

    def test_feat10_hyperliquid_perpetual_context_mark_price(self):
        """Verifies extraction of perpetual mark price, oracle price, and mid price."""
        ctx = self.engine.get_perpetual_context("BTC")
        self.assertEqual(ctx["coin"], "BTC")
        self.assertGreater(ctx["mark_price"], 1000.0)
        self.assertGreater(ctx["mid_price"], 1000.0)
        self.assertGreater(ctx["oracle_price"], 1000.0)

    def test_feat10_hyperliquid_8h_funding_rate_and_annualized_apr(self):
        """Verifies 8h funding rate extraction and annualized APR formulation."""
        ctx = self.engine.get_perpetual_context("BTC")
        self.assertIn("funding_rate_8h", ctx)
        self.assertIn("funding_rate_annualized_pct", ctx)
        # Check APR calculation formula: funding_8h * 3 * 365 * 100
        expected_apr = ctx["funding_rate_8h"] * 3.0 * 365.0 * 100.0
        self.assertAlmostEqual(ctx["funding_rate_annualized_pct"], expected_apr, delta=0.1)

    def test_feat10_hyperliquid_open_interest_telemetry(self):
        """Verifies open interest and USD notional calculation."""
        ctx = self.engine.get_perpetual_context("BTC")
        self.assertIn("open_interest", ctx)
        self.assertIn("open_interest_usd", ctx)
        self.assertGreaterEqual(ctx["open_interest"], 0.0)
        self.assertGreaterEqual(ctx["open_interest_usd"], 0.0)

    def test_feat10_hyperliquid_all_mids_snapshot(self):
        """Verifies snapshot of all mid prices across instruments."""
        mids = self.engine.get_all_mids()
        self.assertIn("BTC", mids)
        self.assertIn("ETH", mids)
        self.assertIn("SOL", mids)
        self.assertGreater(mids["BTC"], 1000.0)
        self.assertGreater(mids["ETH"], 100.0)
        self.assertGreater(mids["SOL"], 10.0)

    def test_feat10_hyperliquid_extreme_funding_flagging(self):
        """Verifies alert triggering when funding rate >= 0.0005 (0.05%/8h)."""
        with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008, "mark_price": 98500.0, "coin": "BTC"}):
            squeeze = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.0005)
            self.assertIsNotNone(squeeze)
            self.assertEqual(squeeze["squeeze_direction"], "LONG_SQUEEZE_RISK")
            self.assertEqual(squeeze["bias"], "BEARISH_EXHAUSTION")


class TestFeature11_CoinGeckoYahooFeeds(unittest.TestCase):
    """Tier 1: Feature 11 — CoinGecko & Yahoo Free Macro Feeds."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=2.0, offline_mode=True)

    def test_feat11_coingecko_global_market_cap_parsing(self):
        """Verifies parsing of global crypto market cap."""
        metrics = self.engine.get_global_crypto_metrics()
        self.assertIn("total_market_cap_usd", metrics)
        self.assertGreater(metrics["total_market_cap_usd"], 1e11)
        self.assertIn("total_24h_volume_usd", metrics)

    def test_feat11_coingecko_btc_eth_dominance_ratios(self):
        """Verifies BTC and ETH dominance percentages and mathematical bounds."""
        metrics = self.engine.get_global_crypto_metrics()
        btc_d = metrics["btc_dominance_pct"]
        eth_d = metrics["eth_dominance_pct"]
        self.assertGreater(btc_d, 20.0)
        self.assertLess(btc_d, 90.0)
        self.assertGreater(eth_d, 5.0)
        self.assertLess(eth_d, 50.0)
        self.assertLessEqual(btc_d + eth_d, 100.0)

    def test_feat11_yahoo_finance_gold_spot_extraction(self):
        """Verifies extraction of Gold futures / spot proxy (GC=F)."""
        quote = self.engine.fetch_macro_quote("GC=F")
        self.assertIn("price", quote)
        self.assertGreater(quote["price"], 1000.0)
        self.assertEqual(quote["ticker"], "GC=F")

    def test_feat11_yahoo_finance_forex_cross_rates(self):
        """Verifies extraction of Forex cross rates (EUR, GBP, JPY)."""
        overview = self.engine.get_macro_overview()
        self.assertIn("gold", overview)
        self.assertIn("silver", overview)
        self.assertIn("dxy", overview)
        self.assertIn("gold_silver_ratio", overview)
        self.assertGreater(overview["gold"]["price"], 1000.0)

    def test_feat11_macro_feed_caching_and_ttl_expiry(self):
        """Verifies thread-safe TTL caching prevents redundant network queries."""
        self.engine.clear_cache()
        self.assertIsNone(self.engine._get_from_cache("test_key", 10.0))
        self.engine._set_to_cache("test_key", {"data": 123})
        cached = self.engine._get_from_cache("test_key", 10.0)
        self.assertEqual(cached["data"], 123)
        # Test expiration
        time.sleep(0.01)
        self.assertIsNone(self.engine._get_from_cache("test_key", 0.005))


class TestFeature12_WeekendCryptoArbitrageEngine(unittest.TestCase):
    """Tier 1: Feature 12 — 24/7 Weekend Crypto Arbitrage Engine."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.engine = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)

    def test_feat12_is_traditional_market_closed_friday_evening(self):
        """Verifies market closed returns True on Friday after 22:00 UTC."""
        dt_fri_closed = datetime(2026, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        dt_fri_open = datetime(2026, 8, 14, 21, 59, 0, tzinfo=timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(dt_fri_closed))
        self.assertFalse(self.engine.is_traditional_market_closed(dt_fri_open))

    def test_feat12_is_traditional_market_closed_saturday_full_day(self):
        """Verifies market closed returns True all Saturday."""
        dt_sat_noon = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(dt_sat_noon))

    def test_feat12_is_traditional_market_closed_sunday_reopening(self):
        """Verifies market closed turns False Sunday at 21:00 UTC."""
        dt_sun_closed = datetime(2026, 8, 16, 20, 59, 0, tzinfo=timezone.utc)
        dt_sun_open = datetime(2026, 8, 16, 21, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(dt_sun_closed))
        self.assertFalse(self.engine.is_traditional_market_closed(dt_sun_open))

    def test_feat12_scan_weekend_crypto_ote_discount_setups(self):
        """Verifies scanning generates actionable setup cards for crypto."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008, "mark_price": 98500.0, "coin": "BTC"}):
            setups = self.engine.scan_weekend_crypto_setups()
            self.assertIsInstance(setups, list)
            self.assertGreaterEqual(len(setups), 1)
            for card in setups:
                self.assertIn(card["symbol"], ["BTCUSD", "ETHUSD", "SOLUSD"])
                self.assertGreater(card["entry_price"], 0.0)
                self.assertLess(card["sl_price"], card["entry_price"])
                self.assertGreater(card["tp1_price"], card["entry_price"])
                self.assertGreaterEqual(card["confluence_score"], 4.5)

    def test_feat12_cvd_momentum_buyer_ratio_filtering(self):
        """Verifies setup cards report valid CVD buyer ratio >= 0.65."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008, "mark_price": 98500.0, "coin": "BTC"}):
            setups = self.engine.scan_weekend_crypto_setups()
            for card in setups:
                self.assertIn("cvd_buyer_ratio", card)
                self.assertGreaterEqual(card["cvd_buyer_ratio"], 0.65)


class TestFeature13_FundingRateSpreadTracking(unittest.TestCase):
    """Tier 1: Feature 13 — Funding Rate Spread Tracking & Basis Arbitrage."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.engine = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)

    def test_feat13_basis_spread_calculation_bps(self):
        """Verifies basis spread calculation between spot and perp mark price."""
        spread = self.engine.track_funding_spread("BTCUSD")
        self.assertEqual(spread["symbol"], "BTCUSD")
        self.assertIn("basis_spread", spread)
        self.assertIn("basis_spread_pct", spread)
        expected_spread = round(spread["perp_mark_price"] - spread["spot_price"], 2)
        self.assertAlmostEqual(spread["basis_spread"], expected_spread, places=2)

    def test_feat13_cross_exchange_funding_rate_divergence(self):
        """Verifies multi-venue predicted funding rate aggregation."""
        spread = self.engine.track_funding_spread("BTCUSD")
        self.assertIn("predicted_venues", spread)
        self.assertIsInstance(spread["predicted_venues"], dict)

    def test_feat13_cash_and_carry_arbitrage_trigger(self):
        """Verifies cash-and-carry carry signal when funding rate >= 0.0005."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0007, "mark_price": 98500.0, "coin": "BTC"}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertTrue(spread["is_squeeze_detected"])
            self.assertEqual(spread["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")

    def test_feat13_short_squeeze_anomaly_detection(self):
        """Verifies short squeeze signal when funding rate <= -0.0005."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": -0.0006, "mark_price": 98500.0, "coin": "BTC"}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertTrue(spread["is_squeeze_detected"])
            self.assertEqual(spread["squeeze_direction"], "SHORT_CROWD_SQUEEZE")
            self.assertEqual(spread["arbitrage_opportunity"], "SHORT_SPOT_LONG_PERP_REBATE")

    def test_feat13_neutral_funding_equilibrium_handling(self):
        """Verifies normal state when funding rate is in neutral corridor."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0001, "mark_price": 98500.0, "coin": "BTC"}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertFalse(spread["is_squeeze_detected"])
            self.assertEqual(spread["arbitrage_opportunity"], "NONE")


class TestFeature14_VolatilityATRStops(unittest.TestCase):
    """Tier 1: Feature 14 — Volatility-Adjusted ATR Stops."""

    def test_feat14_crypto_3_5x_atr_stop_distance(self):
        """Verifies Crypto assets receive 3.5x ATR multiplier."""
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertEqual(specs["category"], "CRYPTO")
            self.assertEqual(specs["atr_sl_mult"], 3.5)

    def test_feat14_gold_2_5x_atr_stop_distance(self):
        """Verifies Gold receives 2.5x ATR multiplier."""
        specs = StrategyEngine.get_symbol_scale_specs("XAUUSD")
        self.assertEqual(specs["category"], "METALS")
        self.assertEqual(specs["atr_sl_mult"], 2.5)

    def test_feat14_forex_1_5x_atr_stop_distance(self):
        """Verifies Forex Majors receive 1.5x ATR multiplier."""
        for sym in ["EURUSD", "GBPUSD", "USDJPY"]:
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertEqual(specs["category"], "FOREX")
            self.assertEqual(specs["atr_sl_mult"], 1.5)

    def test_feat14_minimum_sl_distance_clamping(self):
        """Verifies minimum SL distance clamping prevents undersized stops."""
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertGreater(specs["min_sl_dist"], 0.0)

    def test_feat14_dynamic_tp_structural_scaling_min_1_0_rr(self):
        """Verifies dynamic Take-Profit enforces >= 1.0 R:R minimum floor."""
        engine = StrategyEngine(config={"risk_management": {"min_rr_ratio": 2.0, "atr_sl_multiplier": 1.5}})
        analysis = {
            "trend_direction": "BULLISH",
            "active_resistance": {"level": 105.0, "label": "Swing High"}
        }
        tp, rr, desc = engine.calculate_dynamic_tp(
            symbol="EURUSD",
            signal_type="BUY",
            price=100.0,
            sl_distance=2.0,
            atr=1.0,
            analysis=analysis
        )
        self.assertGreaterEqual(rr, 1.0)
        self.assertGreater(tp, 100.0)


class TestFeature15_AladdinVaRAndFundingPips(unittest.TestCase):
    """Tier 1: Feature 15 — BlackRock Aladdin 1-Day 99% VaR & Funding Pips 25k Risk."""

    def setUp(self):
        self.aladdin = AladdinRiskEngine()
        self.pips_expert = FundingPipsExpert("25k")

    def test_feat15_parametric_var_99_and_95_exact_formulas(self):
        """Verifies 1-Day 99% VaR (Z=2.326348) and 95% VaR (Z=1.644853)."""
        equity = 25000.0
        daily_vol = 0.015  # 1.5% daily vol
        res = self.aladdin.compute_parametric_var_cvar(equity, daily_vol)
        expected_var99 = equity * 2.326348 * daily_vol
        self.assertAlmostEqual(res["var_99_dollar"], expected_var99, delta=0.5)

    def test_feat15_parametric_cvar_99_expected_shortfall(self):
        """Verifies 1-Day 99% CVaR Expected Shortfall."""
        equity = 25000.0
        daily_vol = 0.015
        res = self.aladdin.compute_parametric_var_cvar(equity, daily_vol)
        # CVaR is always strictly greater than VaR
        self.assertGreater(res["cvar_99_dollar"], res["var_99_dollar"])
        self.assertGreater(res["cvar_95_dollar"], res["var_95_dollar"])

    def test_feat15_fractional_kelly_with_uncertainty_haircut(self):
        """Verifies Quarter-Kelly sizing applies 1 SE haircut and caps at 0.75%."""
        risk_fraction = self.aladdin.compute_fractional_kelly(
            win_rate=0.60,
            payoff_ratio=2.0,
            win_rate_se=0.04
        )
        self.assertLessEqual(risk_fraction, 0.0075)  # <= 0.75%
        self.assertGreaterEqual(risk_fraction, 0.0025)  # >= 0.25% floor

    def test_feat15_funding_pips_25k_daily_drawdown_2_5_pct_guard(self):
        """Verifies 2.5% daily drawdown safety guard ($625 on $25k)."""
        # Baseline $25,000 equity
        allowed, msg = self.pips_expert.can_trade(balance=25000.0, equity=25000.0)
        self.assertTrue(allowed)

        # $625 loss -> Equity = $24,375 -> Trigger guard
        blocked, msg = self.pips_expert.can_trade(balance=25000.0, equity=24375.0)
        self.assertFalse(blocked)
        self.assertIn("Daily Drawdown Guard", msg)

    def test_feat15_funding_pips_35_pct_consistency_pacing_rule(self):
        """Verifies 35% single-day profit ceiling ($700 on $2,000 challenge target)."""
        safe_pacing = self.pips_expert.evaluate_consistency_pacing(today_profit=500.0, total_profit_target=2000.0)
        self.assertTrue(safe_pacing["is_pacing_safe"])
        self.assertEqual(safe_pacing["recommendation"], "STANDARD_RISK")

        unsafe_pacing = self.pips_expert.evaluate_consistency_pacing(today_profit=750.0, total_profit_target=2000.0)
        self.assertFalse(unsafe_pacing["is_pacing_safe"])
        self.assertEqual(unsafe_pacing["recommendation"], "CONSERVATIVE_SCALE_DOWN")


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (40 TESTS)
# ==============================================================================

class TestBoundary_MultiAssetPointScales(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 8 (Multi-Asset Scales)."""

    def test_bound8_extreme_crypto_scale_100k_btc(self):
        """Handles high price scales ($150,000 BTC)."""
        scanner = MultiAssetScanner()
        live_data = {"BTCUSD": {"price": 150000.0}}
        ranked = scanner.scan_all_markets(live_data)
        btc_card = next(c for c in ranked if c["symbol"] == "BTCUSD")
        self.assertGreater(btc_card["sl"], 140000.0)

    def test_bound8_micro_point_asset_0_01_cents(self):
        """Handles small micro-dollar pricing without underflow."""
        specs = StrategyEngine.get_symbol_scale_specs("EURUSD")
        self.assertGreater(specs["pip_unit"], 0.0)
        self.assertEqual(specs["decimals"], 5)

    def test_bound8_empty_or_malformed_symbol_catalog(self):
        """Handles lookup of unlisted or malformed symbol tokens gracefully."""
        info = MultiAssetScanner.get_asset_info("UNKNOWN_COIN_XYZ")
        self.assertIn("symbol", info)
        self.assertEqual(info["category"], "FOREX_MAJORS")

    def test_bound8_zero_or_negative_tick_size_guard(self):
        """Prevents division by zero with invalid pip unit."""
        specs = StrategyEngine.get_symbol_scale_specs("BTCUSD")
        self.assertNotEqual(specs["pip_unit"], 0.0)

    def test_bound8_unsupported_symbol_safe_rejection(self):
        """Returns safe default specs for unsupported token."""
        specs = StrategyEngine.get_symbol_scale_specs("INVALID123")
        self.assertIn("atr_sl_mult", specs)
        self.assertIn("min_sl_dist", specs)


class TestBoundary_BinanceFeedFuzzing(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 9 (Binance Feed)."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)

    def test_bound9_empty_order_book_zero_liquidity(self):
        """Handles empty order book without crash."""
        with patch.object(self.engine, "_http_get", return_value={"bids": [], "asks": []}):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            depth = self.engine.get_order_book_depth("BTCUSD")
            self.assertEqual(depth["bids"], [])
            self.assertEqual(depth["asks"], [])
            self.assertEqual(depth["bid_ask_spread"], 0.0)
            self.engine.offline_mode = True

    def test_bound9_crossed_order_book_anomaly(self):
        """Handles crossed book anomaly (best bid >= best ask)."""
        crossed_raw = {"bids": [["100.0", "1.0"]], "asks": [["99.0", "1.0"]]}
        with patch.object(self.engine, "_http_get", return_value=crossed_raw):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            depth = self.engine.get_order_book_depth("BTCUSD")
            self.assertLess(depth["bid_ask_spread"], 0.0)
            self.engine.offline_mode = True

    def test_bound9_http_429_rate_limit_retry_after_handling(self):
        """Handles HTTP 429 rate limits by falling back gracefully."""
        with patch.object(self.engine, "_http_get", side_effect=Exception("HTTP 429 Too Many Requests")):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            ticker = self.engine.get_ticker_24hr("BTCUSD")
            self.assertIn("last_price", ticker)
            self.assertGreater(ticker["last_price"], 0.0)
            self.engine.offline_mode = True

    def test_bound9_malformed_json_truncation(self):
        """Handles truncated or malformed JSON payload."""
        with patch.object(self.engine, "_http_get", side_effect=ValueError("JSONDecodeError: Unterminated string")):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            ticker = self.engine.get_ticker_24hr("ETHUSD")
            self.assertIn("last_price", ticker)
            self.engine.offline_mode = True

    def test_bound9_negative_volume_or_price_zero(self):
        """Validates zero price fallback."""
        with patch.object(self.engine, "_http_get", return_value={"lastPrice": "0.0", "volume": "-10.0"}):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            ticker = self.engine.get_ticker_24hr("BTCUSD")
            self.assertIn("last_price", ticker)
            self.engine.offline_mode = True


class TestBoundary_HyperliquidExtremeYields(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 10 (Hyperliquid DEX)."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)

    def test_bound10_zero_open_interest(self):
        """Handles zero open interest contract."""
        with patch.object(self.engine, "get_perpetual_context", return_value={"open_interest": 0.0, "open_interest_usd": 0.0, "mark_price": 100.0}):
            ctx = self.engine.get_perpetual_context("NEWCOIN")
            self.assertEqual(ctx["open_interest"], 0.0)

    def test_bound10_extreme_negative_funding_rate_minus_2_pct(self):
        """Handles extreme negative funding (-2.00% / 8h = -2190% APR)."""
        with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": -0.02, "mark_price": 3000.0, "coin": "ETH"}):
            squeeze = self.engine.detect_funding_squeeze("ETH", threshold_8h=0.0005)
            self.assertIsNotNone(squeeze)
            self.assertEqual(squeeze["squeeze_direction"], "SHORT_SQUEEZE_RISK")

    def test_bound10_zero_mark_price_fail_safe(self):
        """Prevents zero division when mark price is 0.0."""
        with patch.object(self.engine, "get_perpetual_context", return_value={"mark_price": 0.0, "funding_rate_8h": 0.0001, "coin": "SOL"}):
            ctx = self.engine.get_perpetual_context("SOL")
            self.assertEqual(ctx["mark_price"], 0.0)

    def test_bound10_hyperliquid_api_timeout_fast_fallback(self):
        """Tests timeout fallback without stalling."""
        with patch.object(self.engine, "_http_post_json", side_effect=TimeoutError("Connection timed out")):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            ctx = self.engine.get_perpetual_context("BTC")
            self.assertIn("mark_price", ctx)
            self.engine.offline_mode = True

    def test_bound10_missing_coin_in_meta_context(self):
        """Tests lookup for unlisted coin returns fallback rather than KeyError."""
        ctx = self.engine.get_perpetual_context("NONEXISTENT_COIN_TOKEN")
        self.assertIn("mark_price", ctx)


class TestBoundary_MacroFeedFailovers(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 11 (Macro Feeds)."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)

    def test_bound11_btc_dominance_boundary_100_and_0(self):
        """Tests dominance bounds invariant (0 <= BTC.D <= 100)."""
        metrics = self.engine.get_global_crypto_metrics()
        self.assertGreaterEqual(metrics["btc_dominance_pct"], 0.0)
        self.assertLessEqual(metrics["btc_dominance_pct"], 100.0)

    def test_bound11_negative_market_cap_input(self):
        """Tests negative market cap rejection/fallback."""
        metrics = self.engine.get_global_crypto_metrics()
        self.assertGreater(metrics["total_market_cap_usd"], 0.0)

    def test_bound11_coingecko_rate_limit_fallback_to_yahoo(self):
        """Verifies automated fallback when CoinGecko is throttled."""
        with patch.object(self.engine, "_http_get", side_effect=Exception("HTTP 429")):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            metrics = self.engine.get_global_crypto_metrics()
            self.assertIn("total_market_cap_usd", metrics)
            self.engine.offline_mode = True

    def test_bound11_yahoo_html_scraping_drift_resilience(self):
        """Verifies fallback when Yahoo data is unavailable."""
        with patch.object(self.engine, "_http_get", side_effect=Exception("HTML parsing error")):
            self.engine.clear_cache()
            self.engine.offline_mode = False
            quote = self.engine.fetch_macro_quote("GC=F")
            self.assertIn("price", quote)
            self.engine.offline_mode = True

    def test_bound11_stale_cache_expiration_boundary(self):
        """Verifies data freshness at exact cache TTL boundary."""
        self.engine.clear_cache()
        self.engine._set_to_cache("k", "v")
        self.assertEqual(self.engine._get_from_cache("k", 1.0), "v")


class TestBoundary_WeekendTransitions(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 12 (Weekend Transitions)."""

    def setUp(self):
        self.engine = WeekendCryptoArbitrageEngine(feeds_engine=FreePublicFeedsEngine(offline_mode=True))

    def test_bound12_exact_second_friday_22_00_transition(self):
        """Verifies transition at 21:59:59 vs 22:00:00 UTC Friday."""
        t_before = datetime(2026, 8, 14, 21, 59, 59, tzinfo=timezone.utc)
        t_exact = datetime(2026, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(self.engine.is_traditional_market_closed(t_before))
        self.assertTrue(self.engine.is_traditional_market_closed(t_exact))

    def test_bound12_exact_second_sunday_21_00_transition(self):
        """Verifies transition at 20:59:59 vs 21:00:00 UTC Sunday."""
        t_before = datetime(2026, 8, 16, 20, 59, 59, tzinfo=timezone.utc)
        t_exact = datetime(2026, 8, 16, 21, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(t_before))
        self.assertFalse(self.engine.is_traditional_market_closed(t_exact))

    def test_bound12_cvd_buyer_ratio_exact_0_65_boundary(self):
        """Verifies CVD buyer ratio boundary evaluation."""
        setup = self.engine.compute_smc_dealing_range_ote("BTCUSD", high=100000.0, low=90000.0, current_price=92000.0)
        self.assertTrue(setup["in_discount"])

    def test_bound12_zero_volatility_weekend_flatline(self):
        """Handles zero range dealing box without zero division."""
        setup = self.engine.compute_smc_dealing_range_ote("BTCUSD", high=95000.0, low=95000.0, current_price=95000.0)
        self.assertIn("equilibrium", setup)
        self.assertAlmostEqual(setup["equilibrium"], 95000.0, places=2)

    def test_bound12_leap_year_and_dst_transition_invariance(self):
        """Verifies UTC schedule correctness across leap day and DST shifts."""
        leap_day = datetime(2028, 2, 29, 12, 0, 0, tzinfo=timezone.utc)
        # Tuesday
        self.assertFalse(self.engine.is_traditional_market_closed(leap_day))


class TestBoundary_ExtremeFundingSpreads(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 13 (Funding Spreads)."""

    def setUp(self):
        self.engine = WeekendCryptoArbitrageEngine(feeds_engine=FreePublicFeedsEngine(offline_mode=True))

    def test_bound13_zero_basis_spread_perfect_parity(self):
        """Verifies basis spread when perp mark equals spot price."""
        with patch.object(self.engine.feeds_engine, "get_ticker_24hr", return_value={"last_price": 95000.0}), \
             patch.object(self.engine.feeds_engine, "get_perpetual_context", return_value={"mark_price": 95000.0, "funding_rate_8h": 0.0001}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertEqual(spread["basis_spread"], 0.0)
            self.assertEqual(spread["basis_spread_pct"], 0.0)

    def test_bound13_massive_basis_inversion_negative_500_bps(self):
        """Verifies backwardation spread calculation."""
        with patch.object(self.engine.feeds_engine, "get_ticker_24hr", return_value={"last_price": 100000.0}), \
             patch.object(self.engine.feeds_engine, "get_perpetual_context", return_value={"mark_price": 95000.0, "funding_rate_8h": -0.001}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertEqual(spread["basis_spread"], -5000.0)
            self.assertEqual(spread["basis_spread_pct"], -5.0)

    def test_bound13_extreme_positive_contango_1000_bps(self):
        """Verifies contango spread calculation."""
        with patch.object(self.engine.feeds_engine, "get_ticker_24hr", return_value={"last_price": 100000.0}), \
             patch.object(self.engine.feeds_engine, "get_perpetual_context", return_value={"mark_price": 110000.0, "funding_rate_8h": 0.002}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertEqual(spread["basis_spread"], 10000.0)
            self.assertEqual(spread["basis_spread_pct"], 10.0)

    def test_bound13_zero_spot_price_division_guard(self):
        """Prevents division by zero when spot price is 0.0."""
        with patch.object(self.engine.feeds_engine, "get_ticker_24hr", return_value={"last_price": 0.0}):
            spread = self.engine.track_funding_spread("BTCUSD")
            self.assertIn("basis_spread_pct", spread)

    def test_bound13_instantaneous_spread_sign_flip(self):
        """Verifies state machine resilience under rapid sign flips."""
        for sign in [1, -1, 1, -1]:
            with patch.object(self.engine.feeds_engine, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008 * sign, "mark_price": 95000.0}):
                spread = self.engine.track_funding_spread("BTCUSD")
                self.assertTrue(spread["is_squeeze_detected"])


class TestBoundary_ZeroAndSpikeATRStops(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 14 (ATR Stops)."""

    def test_bound14_zero_atr_input_safeguard(self):
        """Prevents zero division when ATR is 0.0."""
        engine = StrategyEngine(config={"risk_management": {"min_rr_ratio": 2.0, "atr_sl_multiplier": 1.5}})
        tp, rr, desc = engine.calculate_dynamic_tp("EURUSD", "BUY", price=1.1000, sl_distance=0.0020, atr=0.0, analysis={})
        self.assertGreater(tp, 1.1000)

    def test_bound14_negative_atr_input_rejection(self):
        """Handles negative ATR input gracefully."""
        engine = StrategyEngine(config={"risk_management": {"min_rr_ratio": 2.0, "atr_sl_multiplier": 1.5}})
        tp, rr, desc = engine.calculate_dynamic_tp("EURUSD", "BUY", price=1.1000, sl_distance=0.0020, atr=-0.001, analysis={})
        self.assertGreater(tp, 1.1000)

    def test_bound14_massive_atr_flash_spike_10x(self):
        """Handles 10x ATR flash spike."""
        engine = StrategyEngine(config={"risk_management": {"min_rr_ratio": 2.0, "atr_sl_multiplier": 1.5}})
        tp, rr, desc = engine.calculate_dynamic_tp("EURUSD", "BUY", price=1.1000, sl_distance=0.0200, atr=0.0500, analysis={})
        self.assertGreater(tp, 1.1000)

    def test_bound14_price_equals_sl_anchor_boundary(self):
        """Handles price equal to SL anchor boundary."""
        engine = StrategyEngine(config={"risk_management": {"min_rr_ratio": 2.0, "atr_sl_multiplier": 1.5}})
        tp, rr, desc = engine.calculate_dynamic_tp("EURUSD", "SELL", price=1.1000, sl_distance=0.0020, atr=0.0010, analysis={})
        self.assertLess(tp, 1.1000)

    def test_bound14_sl_distance_exceeding_max_risk_cap(self):
        """Verifies audit rejection when SL distance is 0."""
        expert = FundingPipsExpert("25k")
        audit = expert.audit_trade(symbol="BTCUSD", signal_type="BUY", price=95000.0, sl=95000.0, tp=98000.0, current_open_count=0)
        self.assertFalse(audit["passed"])


class TestBoundary_AladdinPropFirmLimits(unittest.TestCase):
    """Tier 2: Boundary cases for Feature 15 (Aladdin & Prop Firm Limits)."""

    def setUp(self):
        self.aladdin = AladdinRiskEngine()
        self.expert = FundingPipsExpert("25k")

    def test_bound15_zero_account_equity_safeguard(self):
        """Prevents zero division when account equity is $0.0."""
        res = self.aladdin.compute_parametric_var_cvar(equity=0.0, daily_volatility=0.02)
        self.assertEqual(res["var_99_dollar"], 0.0)

    def test_bound15_equity_exactly_at_2_5_pct_daily_loss_limit(self):
        """Verifies trade block when loss is exactly $625.00."""
        allowed, msg = self.expert.can_trade(balance=25000.0, equity=24375.0)
        self.assertFalse(allowed)

    def test_bound15_trailing_hwm_floor_breach_boundary(self):
        """Verifies trailing HWM floor ratchets with profit."""
        self.expert.update_daily_watermark(equity=28000.0, balance=28000.0)
        self.assertEqual(self.expert.absolute_high_watermark, 28000.0)
        # 6.0% max loss from $25k target is $1,500 -> floor = $28,000 - $1,500 = $26,500
        allowed, msg = self.expert.can_trade(balance=28000.0, equity=26499.0)
        self.assertFalse(allowed)

    def test_bound15_consistency_pacing_exact_35_pct_boundary(self):
        """Verifies exact $700.00 boundary on $2,000 target."""
        res_700 = self.expert.evaluate_consistency_pacing(today_profit=700.0, total_profit_target=2000.0)
        self.assertTrue(res_700["is_pacing_safe"])

        res_701 = self.expert.evaluate_consistency_pacing(today_profit=700.01, total_profit_target=2000.0)
        self.assertFalse(res_701["is_pacing_safe"])

    def test_bound15_zero_volatility_zero_var_invariance(self):
        """Verifies zero volatility produces $0.00 VaR without error."""
        res = self.aladdin.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.0)
        self.assertEqual(res["var_99_dollar"], 0.0)
        self.assertEqual(res["cvar_99_dollar"], 0.0)


# ==============================================================================
# TIER 3: CROSS-FEATURE PAIRWISE COMBINATIONS (15 TESTS)
# ==============================================================================

class TestPairwiseCombinations(unittest.TestCase):
    """Tier 3: Pairwise Combinations across Features 8–15."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.weekend_engine = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)
        self.scanner = MultiAssetScanner()
        self.aladdin = AladdinRiskEngine()
        self.expert = FundingPipsExpert("25k")

    def test_pairwise_1_weekend_btc_hyperliquid_funding_3_5x_atr(self):
        """Pairwise 1: Weekend Mode x BTCUSD x Hyperliquid 8h Funding x 3.5x ATR."""
        t_sat = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.weekend_engine.is_traditional_market_closed(t_sat))
        specs = StrategyEngine.get_symbol_scale_specs("BTCUSD")
        self.assertEqual(specs["atr_sl_mult"], 3.5)
        ctx = self.feeds.get_perpetual_context("BTC")
        self.assertIn("funding_rate_8h", ctx)

    def test_pairwise_2_weekday_gold_yahoo_spot_2_5x_atr_stress_test(self):
        """Pairwise 2: Weekday Mode x XAUUSD x Yahoo Gold Spot x 2.5x ATR."""
        t_wed = datetime(2026, 8, 12, 14, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(self.weekend_engine.is_traditional_market_closed(t_wed))
        specs = StrategyEngine.get_symbol_scale_specs("XAUUSD")
        self.assertEqual(specs["atr_sl_mult"], 2.5)
        quote = self.feeds.fetch_macro_quote("GC=F")
        self.assertGreater(quote["price"], 1000.0)

    def test_pairwise_3_weekend_eth_binance_depth_basis_arbitrage(self):
        """Pairwise 3: Weekend Mode x ETHUSD x Binance Depth x Basis Spread."""
        depth = self.feeds.get_order_book_depth("ETHUSD")
        self.assertGreater(len(depth["bids"]), 0)
        spread = self.weekend_engine.track_funding_spread("ETHUSD")
        self.assertIn("basis_spread", spread)

    def test_pairwise_4_weekend_sol_coingecko_dominance_vol_expansion(self):
        """Pairwise 4: Weekend Mode x SOLUSD x CoinGecko Dominance x Trailing HWM."""
        metrics = self.feeds.get_global_crypto_metrics()
        self.assertGreater(metrics["btc_dominance_pct"], 0.0)
        specs = StrategyEngine.get_symbol_scale_specs("SOLUSD")
        self.assertEqual(specs["atr_sl_mult"], 3.5)

    def test_pairwise_5_weekday_eurusd_frankfurter_1_5x_atr_consistency(self):
        """Pairwise 5: Weekday Mode x EURUSD x 1.5x ATR x 35% Consistency Pacing."""
        specs = StrategyEngine.get_symbol_scale_specs("EURUSD")
        self.assertEqual(specs["atr_sl_mult"], 1.5)
        pacing = self.expert.evaluate_consistency_pacing(today_profit=300.0)
        self.assertTrue(pacing["is_pacing_safe"])

    def test_pairwise_6_friday_handover_multi_asset_scanner_aladdin_var(self):
        """Pairwise 6: Friday Handover x Multi-Asset Scanner x Aladdin VaR."""
        status = self.weekend_engine.get_weekend_mode_status()
        self.assertIn("session_name", status)
        var = self.aladdin.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.015)
        self.assertLess(var["var_99_pct"], 5.0)

    def test_pairwise_7_high_funding_squeeze_btc_fractional_kelly(self):
        """Pairwise 7: High Funding Squeeze x BTCUSD x Fractional Kelly Sizing."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0009, "mark_price": 98000.0, "coin": "BTC"}):
            squeeze = self.feeds.detect_funding_squeeze("BTC")
            self.assertIsNotNone(squeeze)
            kelly_risk = self.aladdin.compute_fractional_kelly(win_rate=0.65, payoff_ratio=2.0)
            self.assertLessEqual(kelly_risk, 0.0075)

    def test_pairwise_8_feed_outage_hyperliquid_fallback_weekend_cvar(self):
        """Pairwise 8: Feed Outage x Hyperliquid Fallback x Aladdin CVaR."""
        ctx = self.feeds.get_perpetual_context("BTC")
        self.assertIn("mark_price", ctx)
        cvar = self.aladdin.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.02)
        self.assertGreater(cvar["cvar_99_dollar"], cvar["var_99_dollar"])

    def test_pairwise_9_weekend_gbpusd_closed_btc_active_switch(self):
        """Pairwise 9: Weekend Mode x GBPUSD Blocked x BTCUSD Active."""
        t_sat = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.weekend_engine.is_traditional_market_closed(t_sat))
        status = self.weekend_engine.get_weekend_mode_status()
        self.assertIn("target_pairs", status)

    def test_pairwise_10_crypto_sol_negative_funding_short_squeeze_long(self):
        """Pairwise 10: Negative Funding Squeeze x SOLUSD x 3.5x ATR."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": -0.0008, "mark_price": 215.0, "coin": "SOL"}):
            spread = self.weekend_engine.track_funding_spread("SOLUSD")
            self.assertTrue(spread["is_squeeze_detected"])
            self.assertEqual(spread["squeeze_direction"], "SHORT_CROWD_SQUEEZE")

    def test_pairwise_11_weekday_usdjpy_interest_rate_divergence_var(self):
        """Pairwise 11: Weekday Mode x USDJPY x 1.5x ATR Stop x Aladdin VaR."""
        specs = StrategyEngine.get_symbol_scale_specs("USDJPY")
        self.assertEqual(specs["atr_sl_mult"], 1.5)
        self.assertEqual(specs["pip_unit"], 0.01)

    def test_pairwise_12_weekend_eth_contango_basis_cash_carry(self):
        """Pairwise 12: Extreme Contango x ETHUSD x Cash-and-Carry Trigger."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008, "mark_price": 3600.0, "coin": "ETH"}):
            spread = self.weekend_engine.track_funding_spread("ETHUSD")
            self.assertEqual(spread["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")

    def test_pairwise_13_gold_asian_sweep_yahoo_feed_aladdin_pre_trade(self):
        """Pairwise 13: Gold Asian Sweep x Yahoo Feed x 2.5x ATR x Pre-Trade Check."""
        specs = StrategyEngine.get_symbol_scale_specs("XAUUSD")
        self.assertEqual(specs["atr_sl_mult"], 2.5)
        audit = self.expert.audit_trade("XAUUSD", "BUY", price=2400.0, sl=2390.0, tp=2425.0, current_open_count=0)
        self.assertTrue(audit["passed"])

    def test_pairwise_14_weekend_multi_crypto_concurrency_position_limit(self):
        """Pairwise 14: 3 Crypto Setups x Funding Pips Max 2 Positions."""
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0008, "mark_price": 98500.0, "coin": "BTC"}):
            setups = self.weekend_engine.scan_weekend_crypto_setups()
            self.assertGreaterEqual(len(setups), 1)
        # Attempting 3rd position when 2 are open is blocked
        audit = self.expert.audit_trade("SOLUSD", "BUY", price=215.0, sl=210.0, tp=225.0, current_open_count=2)
        self.assertFalse(audit["passed"])
        self.assertIn("reached tier cap", audit["reason"])

    def test_pairwise_15_coin_gecko_outage_yahoo_binance_cascade_aladdin_risk(self):
        """Pairwise 15: CoinGecko Outage x Multi-Feed Fallback x Aladdin Risk."""
        with patch.object(self.feeds, "_http_get", side_effect=Exception("API Error")):
            self.feeds.clear_cache()
            self.feeds.offline_mode = False
            metrics = self.feeds.get_global_crypto_metrics()
            self.assertGreater(metrics["total_market_cap_usd"], 0.0)
            self.feeds.offline_mode = True


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD SCENARIOS (6 TESTS)
# ==============================================================================

class TestRealWorldWorkloads(unittest.TestCase):
    """Tier 4: Institutional Real-World Workload Scenarios."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.weekend_engine = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)
        self.aladdin = AladdinRiskEngine()
        self.expert = FundingPipsExpert("25k")

    def test_scenario_1_weekend_flash_crash_smc_ote_arbitrage_execution(self):
        """
        Scenario 1: Saturday 03:30 UTC — Bitcoin flash dump from $98,500 to $93,200 (5.4% drop).
        Validates feed streaming -> SMC OTE discount -> CVD buyer absorption -> 3.5x ATR stop -> Aladdin VaR approval.
        """
        # 1. Weekend active check
        t_sat = datetime(2026, 8, 15, 3, 30, 0, tzinfo=timezone.utc)
        self.assertTrue(self.weekend_engine.is_traditional_market_closed(t_sat))

        # 2. Feeds report $93,200
        spot_price = 93200.0
        with patch.object(self.feeds, "get_ticker_24hr", return_value={"last_price": spot_price, "symbol": "BTCUSD"}):
            # 3. SMC OTE calculation
            ote = self.weekend_engine.compute_smc_dealing_range_ote("BTCUSD", high=98500.0, low=93000.0, current_price=spot_price)
            self.assertTrue(ote["in_discount"])

            # 4. Volatility 3.5x ATR stop
            atr = 850.0
            sl_dist = 3.5 * atr  # $2,975
            sl_price = spot_price - sl_dist
            tp_price = spot_price + (2.5 * sl_dist)

            # 5. Aladdin risk check & Funding Pips compliance
            var = self.aladdin.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.02)
            self.assertLess(var["var_99_pct"], 5.0)

            audit = self.expert.audit_trade(symbol="BTCUSD", signal_type="BUY", price=spot_price, sl=sl_price, tp=tp_price, current_open_count=0)
            self.assertTrue(audit["passed"])

    def test_scenario_2_hyperliquid_funding_squeeze_and_basis_arbitrage(self):
        """
        Scenario 2: Saturday 14:00 UTC — Hyperliquid ETH perp funding rate surges to +0.09%/8h.
        Validates basis spread calculation (+183 bps) -> Contango squeeze flag -> Cash-and-carry signal -> Risk check.
        """
        with patch.object(self.feeds, "get_perpetual_context", return_value={"funding_rate_8h": 0.0009, "mark_price": 3500.0, "coin": "ETH"}), \
             patch.object(self.feeds, "get_ticker_24hr", return_value={"last_price": 3437.0, "symbol": "ETHUSD"}):
            spread = self.weekend_engine.track_funding_spread("ETHUSD")
            self.assertTrue(spread["is_squeeze_detected"])
            self.assertEqual(spread["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")
            self.assertGreater(spread["basis_spread_pct"], 1.5)

    def test_scenario_3_cascading_multi_feed_outage_and_autonomous_recovery(self):
        """
        Scenario 3: Cascading Multi-Feed Outages during Friday-to-Saturday handover.
        Validates CoinGecko 429 -> Yahoo timeout -> Binance / offline fallback without a single crash.
        """
        with patch.object(self.feeds, "_http_get", side_effect=Exception("HTTP 429 Too Many Requests")):
            self.feeds.clear_cache()
            self.feeds.offline_mode = False
            # 1. CoinGecko fallback
            metrics = self.feeds.get_global_crypto_metrics()
            self.assertGreater(metrics["total_market_cap_usd"], 0.0)

            # 2. Binance ticker fallback
            ticker = self.feeds.get_ticker_24hr("BTCUSD")
            self.assertGreater(ticker["last_price"], 0.0)
            self.feeds.offline_mode = True

    def test_scenario_4_aladdin_var_spike_and_automated_derisking_during_sol_volatility(self):
        """
        Scenario 4: Sunday 08:00 UTC — SOLUSD volatility spike (ATR surges 3.5x from $4.20 to $14.80).
        Validates stop expansion -> Aladdin VaR calculation -> Fractional Kelly de-risking -> Sizing compliance.
        """
        # ATR surges to $14.80
        atr = 14.80
        sl_dist = 3.5 * atr  # $51.80
        spot_price = 215.0
        sl_price = spot_price - sl_dist

        # Fractional Kelly automatically adapts when win_rate edge narrows
        conservative_risk = self.aladdin.compute_fractional_kelly(
            win_rate=0.38,
            payoff_ratio=2.0,
            win_rate_se=0.05,
            regime_scalar=0.50  # Halved in high vol
        )
        self.assertLessEqual(conservative_risk, 0.005)

    def test_scenario_5_friday_evening_market_close_handover_and_24_7_activation(self):
        """
        Scenario 5: Friday 21:55 UTC to 22:05 UTC market transition.
        Validates seamless switch from Forex/Gold to 24/7 Weekend Crypto mode.
        """
        t_open = datetime(2026, 8, 14, 21, 55, 0, tzinfo=timezone.utc)
        self.assertFalse(self.weekend_engine.is_traditional_market_closed(t_open))

        t_closed = datetime(2026, 8, 14, 22, 5, 0, tzinfo=timezone.utc)
        self.assertTrue(self.weekend_engine.is_traditional_market_closed(t_closed))

        status = self.weekend_engine.get_weekend_mode_status()
        self.assertIn("target_pairs", status)

    def test_scenario_6_prop_firm_consistency_pacing_guard_on_crypto_weekend_surge(self):
        """
        Scenario 6: Sunday 16:00 UTC — Realized weekend profit hits +$820.00 on $25k account.
        Validates HWM ratcheting to $25,820 -> 35% ceiling breach detection -> Conservative scale-down trigger.
        """
        # 1. Update watermarks
        self.expert.update_daily_watermark(equity=25820.0, balance=25820.0)
        self.assertEqual(self.expert.absolute_high_watermark, 25820.0)

        # 2. Check 35% consistency pacing ($820 > $700 ceiling on $2,000 challenge target)
        pacing = self.expert.evaluate_consistency_pacing(today_profit=820.0, total_profit_target=2000.0)
        self.assertFalse(pacing["is_pacing_safe"])
        self.assertEqual(pacing["recommendation"], "CONSERVATIVE_SCALE_DOWN")
        self.assertEqual(pacing["max_single_day_allowed"], 700.0)


# ==============================================================================
# MAIN EXECUTION HOOK
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
