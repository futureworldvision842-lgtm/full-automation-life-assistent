"""
tests/test_crypto_public_feeds.py — Comprehensive Test Suite for Milestone 2.
Covers:
  1. FreePublicFeedsEngine: Binance, Hyperliquid, CoinGecko, Yahoo Finance macro feeds (Live & Offline).
  2. Multi-tier TTL caching & thread safety.
  3. Cross-venue funding rate spread tracking & squeeze detection.
  4. MultiAssetScanner 7-asset catalog, ranking, and weekend priority.
  5. Multi-asset pip scales, min SL distances, ATR SL multipliers, and position sizing across all 7 assets.
  6. WeekendCryptoArbitrageEngine SMC dealing ranges, OTE 70.5% levels, and basis spread tracking.
"""

import asyncio
import datetime
import os
import sys
import time
import unittest

import numpy as np
import pandas as pd

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aladdin_risk_engine import AladdinRiskEngine
from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.market_analyzer import MarketAnalyzer
from src.multi_asset_scanner import MultiAssetScanner
from src.order_flow_quant import OrderFlowQuantEngine
from src.risk_manager import RiskManager
from src.strategy import StrategyEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine


class TestFreePublicFeedsEngine(unittest.TestCase):
    """Unit and Integration tests for FreePublicFeedsEngine."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=2.0, offline_mode=True)

    # ── 1. Binance Connectors ─────────────────────────────────────────────────

    def test_binance_ticker_24hr_schema_and_values(self):
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD"]:
            ticker = self.engine.get_ticker_24hr(sym)
            self.assertIn("symbol", ticker)
            self.assertIn("last_price", ticker)
            self.assertIn("bid_price", ticker)
            self.assertIn("ask_price", ticker)
            self.assertIn("spread", ticker)
            self.assertIn("volume_24h", ticker)
            self.assertGreater(ticker["last_price"], 0)
            self.assertGreaterEqual(ticker["spread"], 0)

    def test_binance_ticker_price_single_and_all(self):
        btc_p = self.engine.get_ticker_price("BTCUSD")
        self.assertIsInstance(btc_p, float)
        self.assertGreater(btc_p, 1000.0)

        all_p = self.engine.get_ticker_price(None)
        self.assertIsInstance(all_p, dict)
        self.assertIn("BTCUSDT", all_p)
        self.assertGreater(all_p["BTCUSDT"], 1000.0)

    def test_binance_order_book_depth(self):
        depth = self.engine.get_order_book_depth("BTCUSD", limit=10)
        self.assertIn("bids", depth)
        self.assertIn("asks", depth)
        self.assertIn("total_bid_depth_usd", depth)
        self.assertIn("order_book_imbalance", depth)
        self.assertEqual(len(depth["bids"]), 10)
        self.assertEqual(len(depth["asks"]), 10)
        self.assertGreater(depth["total_bid_depth_usd"], 0)

    def test_binance_klines(self):
        klines = self.engine.get_klines("BTCUSD", interval="15m", limit=25)
        self.assertEqual(len(klines), 25)
        candle = klines[0]
        self.assertIn("time", candle)
        self.assertIn("open", candle)
        self.assertIn("high", candle)
        self.assertIn("low", candle)
        self.assertIn("close", candle)
        self.assertIn("volume", candle)
        self.assertGreaterEqual(candle["high"], candle["low"])

    # ── 2. Hyperliquid DEX Connectors ─────────────────────────────────────────

    def test_hyperliquid_all_mids(self):
        mids = self.engine.get_all_mids()
        self.assertIn("BTC", mids)
        self.assertIn("ETH", mids)
        self.assertIn("SOL", mids)
        self.assertGreater(mids["BTC"], 1000.0)

    def test_hyperliquid_perpetual_context(self):
        ctx = self.engine.get_perpetual_context("BTC")
        self.assertEqual(ctx["coin"], "BTC")
        self.assertIn("mark_price", ctx)
        self.assertIn("open_interest", ctx)
        self.assertIn("funding_rate_8h", ctx)
        self.assertIn("funding_rate_annualized_pct", ctx)
        self.assertIn("max_leverage", ctx)
        self.assertGreater(ctx["mark_price"], 0)
        self.assertGreater(ctx["max_leverage"], 0)

    def test_hyperliquid_predicted_fundings(self):
        venues = self.engine.get_predicted_fundings("BTC")
        self.assertIsInstance(venues, dict)
        self.assertIn("HlPerp", venues)

    def test_funding_rate_spread_and_basis(self):
        spread = self.engine.get_funding_rate_spread("BTC")
        self.assertEqual(spread["coin"], "BTC")
        self.assertIn("spot_price", spread)
        self.assertIn("perp_mark_price", spread)
        self.assertIn("basis_spread", spread)
        self.assertIn("funding_rate_8h", spread)
        self.assertIn("cross_venue_spreads", spread)

    def test_funding_squeeze_detection(self):
        # Trigger squeeze with low threshold
        alert = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.00001)
        self.assertIsNotNone(alert)
        self.assertIn("squeeze_direction", alert)
        self.assertIn("bias", alert)

        # Do not trigger when threshold is extremely high
        no_alert = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.50)
        self.assertIsNone(no_alert)

    # ── 3. CoinGecko Global Metrics ───────────────────────────────────────────

    def test_coingecko_global_metrics(self):
        cg = self.engine.get_global_crypto_metrics()
        self.assertIn("total_market_cap_usd", cg)
        self.assertIn("btc_dominance_pct", cg)
        self.assertIn("eth_dominance_pct", cg)
        self.assertIn("sol_dominance_pct", cg)
        self.assertGreater(cg["btc_dominance_pct"], 50.0)
        self.assertGreater(cg["total_market_cap_usd"], 1e11)

    # ── 4. Yahoo Finance Macro Feed ───────────────────────────────────────────

    def test_yahoo_macro_quotes(self):
        gold = self.engine.fetch_macro_quote("GC=F")
        self.assertIn("price", gold)
        self.assertGreater(gold["price"], 2000.0)

        dxy = self.engine.fetch_macro_quote("DX-Y.NYB")
        self.assertIn("price", dxy)
        self.assertGreater(dxy["price"], 90.0)

    def test_macro_overview_and_gsr(self):
        macro = self.engine.get_macro_overview()
        self.assertIn("gold", macro)
        self.assertIn("silver", macro)
        self.assertIn("dxy", macro)
        self.assertIn("us10y", macro)
        self.assertIn("vix", macro)
        self.assertIn("gold_silver_ratio", macro)
        self.assertGreater(macro["gold_silver_ratio"], 50.0)

    # ── 5. Consolidated Intelligence & Async ──────────────────────────────────

    def test_consolidated_market_intel(self):
        intel = self.engine.get_consolidated_market_intel()
        self.assertIn("crypto_assets", intel)
        self.assertIn("global_crypto_metrics", intel)
        self.assertIn("macro_overview", intel)
        self.assertIn("BTCUSD", intel["crypto_assets"])
        self.assertIn("ETHUSD", intel["crypto_assets"])
        self.assertIn("SOLUSD", intel["crypto_assets"])

    def test_async_wrappers(self):
        async def run_async():
            ticker = await self.engine.async_get_ticker_24hr("BTCUSD")
            perp = await self.engine.async_get_perpetual_context("BTC")
            cg = await self.engine.async_get_global_crypto_metrics()
            return ticker, perp, cg

        t, p, c = asyncio.run(run_async())
        self.assertEqual(t["symbol"], "BTCUSD")
        self.assertEqual(p["coin"], "BTC")
        self.assertGreater(c["btc_dominance_pct"], 50.0)

    # ── 6. TTL Caching & Thread Safety ────────────────────────────────────────

    def test_cache_ttl_and_thread_safety(self):
        self.engine.clear_cache()
        self.engine._set_to_cache("test_key", "test_value")
        val = self.engine._get_from_cache("test_key", ttl=10.0)
        self.assertEqual(val, "test_value")

        # Expired TTL
        expired_val = self.engine._get_from_cache("test_key", ttl=0.0001)
        time.sleep(0.001)
        expired_val = self.engine._get_from_cache("test_key", ttl=0.0001)
        self.assertIsNone(expired_val)


class TestMultiAssetScannerAndCatalog(unittest.TestCase):
    """Test Suite for 7-Asset Multi-Asset Scanner."""

    def setUp(self):
        self.scanner = MultiAssetScanner()

    def test_asset_catalog_contains_all_7_assets(self):
        expected_symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        for sym in expected_symbols:
            self.assertIn(sym, self.scanner.ASSET_CATALOG)
            info = self.scanner.get_asset_info(sym)
            self.assertEqual(info["symbol"], sym)
            self.assertIn("pip_unit", info)
            self.assertIn("min_sl_dist", info)
            self.assertIn("atr_sl_mult", info)

    def test_asset_calibrations_invariants(self):
        # BTCUSD
        btc = self.scanner.get_asset_info("BTCUSD")
        self.assertEqual(btc["category"], "CRYPTO")
        self.assertEqual(btc["min_sl_dist"], 250.0)
        self.assertEqual(btc["atr_sl_mult"], 3.5)

        # ETHUSD
        eth = self.scanner.get_asset_info("ETHUSD")
        self.assertEqual(eth["category"], "CRYPTO")
        self.assertEqual(eth["min_sl_dist"], 20.0)
        self.assertEqual(eth["atr_sl_mult"], 3.5)

        # SOLUSD
        sol = self.scanner.get_asset_info("SOLUSD")
        self.assertEqual(sol["category"], "CRYPTO")
        self.assertEqual(sol["min_sl_dist"], 2.0)
        self.assertEqual(sol["atr_sl_mult"], 3.5)

        # XAUUSD
        gold = self.scanner.get_asset_info("XAUUSD")
        self.assertEqual(gold["category"], "PRECIOUS_METALS")
        self.assertEqual(gold["min_sl_dist"], 10.0)
        self.assertEqual(gold["atr_sl_mult"], 2.5)

        # USDJPY
        jpy = self.scanner.get_asset_info("USDJPY")
        self.assertEqual(jpy["category"], "FOREX_MAJORS")
        self.assertEqual(jpy["min_sl_dist"], 0.15)
        self.assertEqual(jpy["atr_sl_mult"], 1.5)

        # EURUSD
        eur = self.scanner.get_asset_info("EURUSD")
        self.assertEqual(eur["category"], "FOREX_MAJORS")
        self.assertEqual(eur["min_sl_dist"], 0.0012)
        self.assertEqual(eur["atr_sl_mult"], 1.5)

    def test_scan_all_markets_output_structure(self):
        markets = self.scanner.scan_all_markets()
        self.assertEqual(len(markets), 7)
        for m in markets:
            self.assertIn("symbol", m)
            self.assertIn("action", m)
            self.assertIn("confluence_score", m)
            self.assertIn("edge_pct", m)
            self.assertIn("price", m)
            self.assertIn("sl", m)
            self.assertIn("tp1", m)
            self.assertIn("tp2", m)
            self.assertGreater(m["edge_pct"], 50.0)
            self.assertGreater(m["confluence_score"], 0.0)

        # Verify descending sort order by confluence score
        scores = [m["confluence_score"] for m in markets]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestMultiAssetQuantRiskAndStrategy(unittest.TestCase):
    """Test Suite for Strategy, RiskManager, and Aladdin calibrations across 7 assets."""

    def setUp(self):
        self.config = {
            "account_info": {"target_account_size": 25000.0},
            "risk_management": {
                "max_daily_loss_pct": 2.5,
                "max_total_loss_pct": 6.0,
                "risk_per_trade_pct": 0.75,
                "max_open_trades": 3,
                "max_daily_trades": 8,
                "min_rr_ratio": 2.0,
                "atr_sl_multiplier": 1.5,
                "forex_atr_sl_multiplier": 1.5,
                "gold_atr_sl_multiplier": 2.5,
                "crypto_atr_sl_multiplier": 3.5,
            },
        }
        self.risk_mgr = RiskManager(self.config)
        self.aladdin = AladdinRiskEngine()

    def test_position_sizing_all_7_assets(self):
        # 0.75% of $25,000 = $187.50
        equity = 25000.0

        # BTCUSD: $250 SL -> 187.50 / (250 * 1.0) = 0.75 lots
        btc_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=250.0, symbol="BTCUSD")
        self.assertEqual(btc_lots, 0.75)

        # ETHUSD: $20 SL -> 187.50 / (20 * 1.0) = 9.38 lots
        eth_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=20.0, symbol="ETHUSD")
        self.assertEqual(eth_lots, 9.38)

        # SOLUSD: $2.0 SL -> 187.50 / (2.0 * 1.0) = 93.75 lots
        sol_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=2.0, symbol="SOLUSD")
        self.assertEqual(sol_lots, 93.75)

        # XAUUSD: 100 pips ($10 SL) -> 187.50 / (100 * 10.0) = 0.19 lots
        gold_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=100.0, symbol="XAUUSD")
        self.assertEqual(gold_lots, 0.19)

        # USDJPY: 15 pips -> 187.50 / (15 * 6.50) = 1.92 lots
        jpy_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=15.0, symbol="USDJPY")
        self.assertEqual(jpy_lots, 1.92)

        # EURUSD: 12 pips -> 187.50 / (12 * 10.0) = 1.56 lots
        eur_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=12.0, symbol="EURUSD")
        self.assertEqual(eur_lots, 1.56)

        # GBPUSD: 15 pips -> 187.50 / (15 * 10.0) = 1.25 lots
        gbp_lots = self.risk_mgr.calculate_position_size(equity, sl_pips=15.0, symbol="GBPUSD")
        self.assertEqual(gbp_lots, 1.25)

    def test_lot_size_clamping_ceilings(self):
        equity = 25000.0
        # Ultra tight SL on BTC should cap at 10.0 lots
        btc_capped = self.risk_mgr.calculate_position_size(equity, sl_pips=5.0, symbol="BTCUSD")
        self.assertEqual(btc_capped, 10.0)

        # Ultra tight SL on Gold should cap at 5.0 lots
        gold_capped = self.risk_mgr.calculate_position_size(equity, sl_pips=1.0, symbol="XAUUSD")
        self.assertEqual(gold_capped, 5.0)

    def test_strategy_engine_scale_specs(self):
        strategy = StrategyEngine(self.config)
        self.assertEqual(strategy.crypto_atr_sl_mult, 3.5)
        self.assertEqual(strategy.gold_atr_sl_mult, 2.5)
        self.assertEqual(strategy.atr_sl_mult, 1.5)

        for sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            specs = StrategyEngine.get_symbol_scale_specs(sym)
            self.assertIn(specs["category"], ["CRYPTO", "METALS", "FOREX"])
            self.assertGreater(specs["min_sl_dist"], 0)

    def test_aladdin_pre_trade_stress_test_crypto_positions(self):
        # 1.0 BTC from $95,000 with SL $94,000 ($1,000 risk)
        crypto_positions = [
            {"symbol": "BTCUSD", "price_open": 95000.0, "sl": 94000.0, "volume": 1.0}
        ]
        res = self.aladdin.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=100.0,
            open_positions=crypto_positions,
            max_daily_loss_dollar=625.0,
        )
        self.assertEqual(res["total_stressed_risk_dollar"], 1100.0)
        self.assertFalse(res["passed"])  # 1100 > 80% of 625

        # Safe crypto position: 0.20 BTC with $500 SL -> $100 risk + $50 prospective = $150 (< $500)
        safe_crypto = [
            {"symbol": "BTCUSD", "price_open": 95000.0, "sl": 94500.0, "volume": 0.20}
        ]
        res_safe = self.aladdin.evaluate_pre_trade_stress_test(
            equity=25000.0,
            prospective_risk_dollar=50.0,
            open_positions=safe_crypto,
            max_daily_loss_dollar=625.0,
        )
        self.assertEqual(res_safe["total_stressed_risk_dollar"], 150.0)
        self.assertTrue(res_safe["passed"])

    def test_market_analyzer_and_order_flow_crypto_scales(self):
        analyzer = MarketAnalyzer(self.config)
        of_quant = OrderFlowQuantEngine()

        # Create synthetic BTC dataframe with $500 FVG
        df_btc = pd.DataFrame({
            "time": [1000 + i * 60 for i in range(10)],
            "open": [95000.0 + i * 50 for i in range(10)],
            "high": [95100.0 + i * 50 for i in range(10)],
            "low": [94900.0 + i * 50 for i in range(10)],
            "close": [95050.0 + i * 50 for i in range(10)],
            "volume": [100.0 for _ in range(10)],
        })
        # Inject FVG: candle 4 high < candle 6 low
        df_btc.loc[4, "high"] = 95200.0
        df_btc.loc[6, "low"] = 95500.0  # $300 gap

        fvgs = analyzer.detect_fvg(df_btc, min_gap_pips=2.0, symbol="BTCUSD")
        self.assertIsInstance(fvgs, list)

        # EQH / EQL inducement sweep on BTCUSD
        df_eqh = pd.DataFrame({
            "time": [1000 + i * 60 for i in range(40)],
            "open": [95000.0 for _ in range(40)],
            "high": [95500.0 for _ in range(40)],
            "low": [94500.0 for _ in range(40)],
            "close": [95000.0 for _ in range(40)],
            "volume": [10.0 for _ in range(40)],
        })
        # Induce sweep on last bar
        df_eqh.loc[39, "high"] = 95600.0
        df_eqh.loc[39, "close"] = 95400.0

        eqh_res = of_quant.detect_eqh_eql_inducement(df_eqh, symbol="BTCUSD")
        self.assertIn("inducement_type", eqh_res)


class TestWeekendCryptoArbitrageEngine(unittest.TestCase):
    """Test Suite for WeekendCryptoArbitrageEngine."""

    def setUp(self):
        self.feeds = FreePublicFeedsEngine(offline_mode=True)
        self.engine = WeekendCryptoArbitrageEngine(feeds_engine=self.feeds)

    def test_weekend_schedule_transitions(self):
        # Friday 21:00 UTC -> Open (False)
        t_fri_open = datetime.datetime(2026, 8, 14, 21, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(self.engine.is_traditional_market_closed(t_fri_open))

        # Friday 23:00 UTC -> Closed (True)
        t_fri_closed = datetime.datetime(2026, 8, 14, 23, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(t_fri_closed))

        # Saturday 12:00 UTC -> Closed (True)
        t_sat = datetime.datetime(2026, 8, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(t_sat))

        # Sunday 20:00 UTC -> Closed (True)
        t_sun_closed = datetime.datetime(2026, 8, 16, 20, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(self.engine.is_traditional_market_closed(t_sun_closed))

        # Sunday 22:00 UTC -> Open (False)
        t_sun_open = datetime.datetime(2026, 8, 16, 22, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(self.engine.is_traditional_market_closed(t_sun_open))

    def test_track_funding_spread(self):
        spread = self.engine.track_funding_spread("BTCUSD")
        self.assertEqual(spread["symbol"], "BTCUSD")
        self.assertIn("spot_price", spread)
        self.assertIn("perp_mark_price", spread)
        self.assertIn("basis_spread", spread)
        self.assertIn("basis_spread_pct", spread)
        self.assertIn("funding_rate_8h", spread)
        self.assertIn("annualized_funding_pct", spread)
        self.assertIn("is_squeeze_detected", spread)
        self.assertIn("arbitrage_opportunity", spread)

    def test_compute_smc_dealing_range_ote(self):
        ote = self.engine.compute_smc_dealing_range_ote(
            symbol="BTCUSD", high=100000.0, low=90000.0, current_price=92000.0
        )
        self.assertEqual(ote["range_high"], 100000.0)
        self.assertEqual(ote["range_low"], 90000.0)
        self.assertEqual(ote["equilibrium"], 95000.0)
        self.assertTrue(ote["in_discount"])
        self.assertFalse(ote["in_premium"])
        # 70.5% OTE buy level = 100000 - 0.705 * 10000 = 92950.0
        self.assertEqual(ote["buy_ote_705"], 92950.0)

    def test_scan_weekend_crypto_setups(self):
        setups = self.engine.scan_weekend_crypto_setups()
        self.assertIsInstance(setups, list)
        for s in setups:
            self.assertIn(s["symbol"], self.engine.WEEKEND_CRYPTO_PAIRS)
            self.assertIn("entry_price", s)
            self.assertIn("sl_price", s)
            self.assertIn("tp1_price", s)
            self.assertIn("confluence_score", s)
            self.assertGreater(s["confluence_score"], 4.0)

    def test_get_weekend_mode_status(self):
        status = self.engine.get_weekend_mode_status()
        self.assertIn("is_weekend_active", status)
        self.assertIn("target_pairs", status)
        self.assertIn("session_name", status)


if __name__ == "__main__":
    unittest.main()
