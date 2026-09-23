"""
tests/test_m2_challenger1_feeds_stress.py — M2 Challenger 1 Feeds, Rates & Networks Empirical Stress Test Suite.

Empirical Challenge Areas:
  1. Offline Fallback Resilience & Timeout Recovery under Simulated Network Failures.
  2. High-Concurrency Multi-Threaded & Async Stress on TTL Caches.
  3. Malformed Payload Fuzzing, Missing Keys, Zero & Negative Pricing Handling.
  4. Extreme Funding Rate Divergence (>0.05%/8h, Negative Rates, Extreme Basis Spreads).
"""

import asyncio
import concurrent.futures
import json
import logging
import math
import os
import sys
import threading
import time
import unittest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Ensure repo root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine
from src.multi_asset_scanner import MultiAssetScanner
from src.strategy import StrategyEngine


# ==============================================================================
# AREA 1: OFFLINE FALLBACK RESILIENCE & TIMEOUT RECOVERY
# ==============================================================================

class TestArea1_NetworkFailureAndRecovery(unittest.TestCase):
    """Empirical testing of network drops, timeouts, errors, and recovery across all feeds."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=1.0, offline_mode=False)

    def test_binance_ticker_resilience_under_network_errors(self):
        """Simulates diverse network errors on Binance 24hr ticker and verifies deterministic fallback."""
        error_types = [
            ConnectionResetError("Connection reset by peer"),
            TimeoutError("The read operation timed out"),
            Exception("HTTP 429 Too Many Requests"),
            Exception("HTTP 500 Internal Server Error"),
            Exception("HTTP 503 Service Unavailable"),
            ValueError("JSONDecodeError: Expecting value: line 1 column 1 (char 0)"),
        ]

        for err in error_types:
            with patch.object(self.engine, "_http_get", side_effect=err):
                self.engine.clear_cache()
                ticker = self.engine.get_ticker_24hr("BTCUSD")
                self.assertIsNotNone(ticker)
                self.assertEqual(ticker["symbol"], "BTCUSD")
                self.assertGreater(ticker["last_price"], 0.0)
                self.assertEqual(ticker["source"], "Offline High-Fidelity Baseline")

    def test_hyperliquid_resilience_under_network_errors(self):
        """Simulates diverse network errors on Hyperliquid DEX and verifies deterministic fallback."""
        error_types = [
            ConnectionRefusedError("Connection refused to api.hyperliquid.xyz"),
            TimeoutError("POST https://api.hyperliquid.xyz/info timed out"),
            Exception("HTTP 502 Bad Gateway"),
            json.decoder.JSONDecodeError("Invalid JSON", "raw text", 0),
        ]

        for err in error_types:
            with patch.object(self.engine, "_http_post_json", side_effect=err):
                self.engine.clear_cache()
                # 1. Perpetual context
                ctx = self.engine.get_perpetual_context("BTC")
                self.assertIsNotNone(ctx)
                self.assertEqual(ctx["coin"], "BTC")
                self.assertGreater(ctx["mark_price"], 0.0)
                self.assertIn("funding_rate_8h", ctx)
                self.assertEqual(ctx["source"], "Offline Hyperliquid Model")

                # 2. All Mids
                mids = self.engine.get_all_mids()
                self.assertIn("BTC", mids)
                self.assertIn("ETH", mids)

                # 3. Predicted Fundings
                pf = self.engine.get_predicted_fundings("BTC")
                self.assertIsInstance(pf, dict)
                self.assertIn("BinPerp", pf)

    def test_coingecko_and_yahoo_resilience_under_network_errors(self):
        """Simulates diverse network errors on CoinGecko and Yahoo Finance."""
        for err in [Exception("HTTP 403 Forbidden"), Exception("HTTP 429 Rate Limit Exceeded")]:
            with patch.object(self.engine, "_http_get", side_effect=err):
                self.engine.clear_cache()
                # CoinGecko
                cg = self.engine.get_global_crypto_metrics()
                self.assertGreater(cg["total_market_cap_usd"], 1e11)
                self.assertGreater(cg["btc_dominance_pct"], 0.0)
                self.assertEqual(cg["source"], "Offline CoinGecko Model")

                # Yahoo Macro
                macro = self.engine.get_macro_overview()
                self.assertIn("gold", macro)
                self.assertIn("dxy", macro)
                self.assertGreater(macro["gold"]["price"], 1000.0)
                self.assertGreater(macro["gold_silver_ratio"], 0.0)

    def test_network_recovery_cycle_offline_to_live_to_offline(self):
        """
        Tests cycle: Live Network -> Network Outage -> Fallback -> Network Restored -> Live Fresh Data.
        """
        # Step 1: Live Mock Response
        live_ticker = {
            "symbol": "BTCUSDT",
            "lastPrice": "99123.45",
            "bidPrice": "99120.00",
            "askPrice": "99125.00",
            "priceChange": "1500.00",
            "priceChangePercent": "1.53",
            "highPrice": "99500.00",
            "lowPrice": "97500.00",
            "volume": "25000.0",
            "quoteVolume": "2475000000.0",
        }
        with patch.object(self.engine, "_http_get", return_value=live_ticker):
            self.engine.clear_cache()
            t1 = self.engine.get_ticker_24hr("BTCUSD")
            self.assertEqual(t1["last_price"], 99123.45)
            self.assertEqual(t1["source"], "Binance Public API")

        # Step 2: Network Outage + Cache Expiry
        with patch.object(self.engine, "_http_get", side_effect=ConnectionResetError("Outage")):
            self.engine.clear_cache()
            t2 = self.engine.get_ticker_24hr("BTCUSD")
            self.assertEqual(t2["last_price"], 98500.0)  # Default fallback
            self.assertEqual(t2["source"], "Offline High-Fidelity Baseline")

        # Step 3: Network Restored with New Live Price
        live_ticker_recovered = dict(live_ticker, lastPrice="101500.00")
        with patch.object(self.engine, "_http_get", return_value=live_ticker_recovered):
            self.engine.clear_cache()
            t3 = self.engine.get_ticker_24hr("BTCUSD")
            self.assertEqual(t3["last_price"], 101500.00)
            self.assertEqual(t3["source"], "Binance Public API")

    def test_consolidated_intel_under_cascading_partial_failures(self):
        """
        Tests consolidated market intelligence when Binance succeeds, Hyperliquid fails, CoinGecko succeeds, Yahoo fails.
        """
        def custom_http_get(url, params=None):
            if "binance" in url:
                return {
                    "lastPrice": "97000.0",
                    "bidPrice": "96999.0",
                    "askPrice": "97001.0",
                    "priceChange": "500.0",
                    "priceChangePercent": "0.52",
                    "highPrice": "98000.0",
                    "lowPrice": "96000.0",
                    "volume": "10000.0",
                    "quoteVolume": "970000000.0",
                }
            if "coingecko" in url:
                return {
                    "data": {
                        "total_market_cap": {"usd": 3100000000000.0},
                        "total_volume": {"usd": 65000000000.0},
                        "market_cap_percentage": {"btc": 58.2, "eth": 12.1, "sol": 3.4},
                        "active_cryptocurrencies": 16000,
                        "market_cap_change_percentage_24h_usd": 1.2,
                    }
                }
            if "yahoo" in url:
                raise Exception("Yahoo Gateway Timeout 504")
            return {}

        def custom_http_post(url, payload):
            raise ConnectionError("Hyperliquid connection refused")

        with patch.object(self.engine, "_http_get", side_effect=custom_http_get), \
             patch.object(self.engine, "_http_post_json", side_effect=custom_http_post):
            self.engine.clear_cache()
            intel = self.engine.get_consolidated_market_intel()
            self.assertIn("crypto_assets", intel)
            self.assertIn("global_crypto_metrics", intel)
            self.assertIn("macro_overview", intel)

            # Binance live
            btc_spot = intel["crypto_assets"]["BTCUSD"]["spot"]
            self.assertEqual(btc_spot["last_price"], 97000.0)

            # Hyperliquid fallback
            btc_perp = intel["crypto_assets"]["BTCUSD"]["perpetual"]
            self.assertGreater(btc_perp["mark_price"], 0.0)

            # CoinGecko live
            cg = intel["global_crypto_metrics"]
            self.assertEqual(cg["btc_dominance_pct"], 58.2)

            # Yahoo fallback
            macro = intel["macro_overview"]
            self.assertGreater(macro["gold"]["price"], 1000.0)


# ==============================================================================
# AREA 2: HIGH-CONCURRENCY MULTI-THREADED & ASYNC STRESS ON TTL CACHES
# ==============================================================================

class TestArea2_ConcurrencyAndTTLCaches(unittest.TestCase):
    """Stress tests concurrent read/writes, cache invalidations, and async operations."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)

    def test_multithreaded_cache_concurrency_stress(self):
        """
        Launches 32 concurrent threads executing 1,000 operations across ticker, perpetual, macro, and klines.
        Verifies thread safety, absence of deadlocks, and zero corrupted payloads.
        """
        num_threads = 32
        ops_per_thread = 35
        errors: List[Exception] = []
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        coins = ["BTC", "ETH", "SOL", "GOLD", "EUR"]

        def worker(thread_id: int):
            try:
                for j in range(ops_per_thread):
                    sym = symbols[(thread_id + j) % len(symbols)]
                    coin = coins[(thread_id + j) % len(coins)]

                    # Randomly interleave cache clears and queries
                    if j % 10 == 0:
                        self.engine.clear_cache()

                    # Query Binance ticker
                    t = self.engine.get_ticker_24hr(sym)
                    assert t["symbol"] == sym
                    assert t["last_price"] > 0

                    # Query Hyperliquid perp
                    ctx = self.engine.get_perpetual_context(coin)
                    assert ctx["coin"] == coin
                    assert ctx["mark_price"] > 0

                    # Query Macro overview
                    macro = self.engine.get_macro_overview()
                    assert "gold" in macro
                    assert macro["gold"]["price"] > 0

                    # Query depth
                    depth = self.engine.get_order_book_depth(sym, limit=10)
                    assert len(depth["bids"]) == 10
                    assert len(depth["asks"]) == 10

                    # Query klines
                    klines = self.engine.get_klines(sym, interval="15m", limit=10)
                    assert len(klines) == 10

                    # Direct cache read/write tests
                    key = f"thread_test_key_{thread_id % 4}"
                    self.engine._set_to_cache(key, {"ts": time.time(), "val": j})
                    cached = self.engine._get_from_cache(key, ttl=5.0)
                    if cached:
                        assert "val" in cached
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        start_t = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
        elapsed = time.time() - start_t

        self.assertEqual(len(errors), 0, f"Encountered {len(errors)} errors in concurrent threads: {errors[:5]}")
        self.assertLess(elapsed, 10.0, f"Concurrency test took too long: {elapsed:.2f}s")

    def test_ttl_cache_expiration_boundaries(self):
        """Verifies exact TTL expiration across ticker (3s), perpetual (15s), and macro (60s)."""
        self.engine.clear_cache()

        # Set manual timestamps into cache to simulate aging
        now = time.time()
        with self.engine._lock:
            self.engine._cache["ticker_test"] = (now - 2.9, {"price": 100.0})
            self.engine._cache["ticker_expired"] = (now - 3.1, {"price": 100.0})
            self.engine._cache["perp_test"] = (now - 14.9, {"funding": 0.0001})
            self.engine._cache["perp_expired"] = (now - 15.1, {"funding": 0.0001})
            self.engine._cache["macro_test"] = (now - 59.9, {"dxy": 104.0})
            self.engine._cache["macro_expired"] = (now - 60.1, {"dxy": 104.0})

        # Check ticker TTL = 3.0s
        self.assertIsNotNone(self.engine._get_from_cache("ticker_test", self.engine.TTL_TICKER))
        self.assertIsNone(self.engine._get_from_cache("ticker_expired", self.engine.TTL_TICKER))

        # Check perpetual TTL = 15.0s
        self.assertIsNotNone(self.engine._get_from_cache("perp_test", self.engine.TTL_PERPETUAL))
        self.assertIsNone(self.engine._get_from_cache("perp_expired", self.engine.TTL_PERPETUAL))

        # Check macro TTL = 60.0s
        self.assertIsNotNone(self.engine._get_from_cache("macro_test", self.engine.TTL_MACRO))
        self.assertIsNone(self.engine._get_from_cache("macro_expired", self.engine.TTL_MACRO))

    def test_async_concurrent_gather_stress(self):
        """Stress tests 50 simultaneous asyncio tasks querying async wrappers."""
        async def run_stress():
            tasks = []
            for i in range(50):
                sym = "BTCUSD" if i % 3 == 0 else ("ETHUSD" if i % 3 == 1 else "SOLUSD")
                tasks.append(self.engine.async_get_crypto_asset_snapshot(sym))
                tasks.append(self.engine.async_get_global_crypto_metrics())
                tasks.append(self.engine.async_get_macro_overview())

            results = await asyncio.gather(*tasks, return_exceptions=False)
            return results

        results = asyncio.run(run_stress())
        self.assertEqual(len(results), 150)
        for r in results:
            self.assertIsNotNone(r)
            self.assertIn("timestamp", r)


# ==============================================================================
# AREA 3: MALFORMED API PAYLOAD FUZZING, MISSING KEYS, ZERO/NEGATIVE PRICING
# ==============================================================================

class TestArea3_MalformedPayloadFuzzing(unittest.TestCase):
    """Adversarial stress testing against malformed API payloads and extreme dirty inputs."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(timeout=1.0, offline_mode=False)

    def test_binance_ticker_fuzzing_missing_keys_and_bad_types(self):
        """Fuzzes Binance 24hr ticker endpoint with dirty and malformed payloads."""
        fuzz_payloads = [
            {},  # Empty
            {"code": -1121, "msg": "Invalid symbol."},  # Binance error payload
            {"lastPrice": "0.0", "bidPrice": "0.0", "askPrice": "0.0"},  # Zero pricing
            {"lastPrice": "-999.50", "bidPrice": "-1000.0", "askPrice": "-999.0"},  # Negative pricing
            {"lastPrice": "NaN", "priceChange": "null"},  # NaN strings
            {"lastPrice": "Infinity", "volume": "-Infinity"},
            {"lastPrice": None, "volume": None},  # None values
            {"lastPrice": "invalid_string_not_number"},
            {"lastPrice": "99999999999999999999.99"},  # Huge value
        ]

        for payload in fuzz_payloads:
            with patch.object(self.engine, "_http_get", return_value=payload):
                self.engine.clear_cache()
                # Must not raise unhandled exception
                ticker = self.engine.get_ticker_24hr("BTCUSD")
                self.assertIsNotNone(ticker)
                self.assertEqual(ticker["symbol"], "BTCUSD")
                self.assertIn("last_price", ticker)
                self.assertIsInstance(ticker["last_price"], (int, float))

    def test_binance_depth_fuzzing_empty_crossed_and_malformed_arrays(self):
        """Fuzzes Binance L2 depth endpoint with empty, crossed, and corrupt bids/asks."""
        depth_payloads = [
            {"bids": [], "asks": []},  # Empty
            {"bids": [["100.0", "1.0"]], "asks": []},  # Single-sided bids
            {"bids": [], "asks": [["101.0", "1.0"]]},  # Single-sided asks
            {"bids": [["105.0", "1.0"]], "asks": [["100.0", "1.0"]]},  # Crossed book (bid > ask)
            {"bids": [["invalid", "10"], ["100"]], "asks": [[None, 20]]},  # Corrupted data
            {"bids": None, "asks": None},  # None
            {},  # Empty dict
        ]

        for payload in depth_payloads:
            with patch.object(self.engine, "_http_get", return_value=payload):
                self.engine.clear_cache()
                depth = self.engine.get_order_book_depth("BTCUSD", limit=10)
                self.assertIsNotNone(depth)
                self.assertIn("bids", depth)
                self.assertIn("asks", depth)
                self.assertIn("order_book_imbalance", depth)
                self.assertIn("bid_ask_spread", depth)
                self.assertIsInstance(depth["order_book_imbalance"], float)
                # Imbalance must stay within [-1.0, 1.0]
                self.assertGreaterEqual(depth["order_book_imbalance"], -1.0)
                self.assertLessEqual(depth["order_book_imbalance"], 1.0)

    def test_hyperliquid_context_fuzzing_empty_universe_and_bad_indices(self):
        """Fuzzes Hyperliquid metaAndAssetCtxs endpoint."""
        hl_fuzz_payloads = [
            [],  # Empty list
            {},  # Empty dict
            None,  # None
            [{"universe": []}, []],  # Empty universe
            [{"universe": [{"name": "DIFFERENT_COIN"}]}, [{"funding": "0.0001"}]],  # Missing target coin
            [{"universe": [{"name": "BTC"}]}, []],  # Index out of bounds (ctxs empty)
            [{"universe": [{"name": "BTC"}]}, [{"funding": "invalid_num", "markPx": "NaN"}]],  # Corrupted numbers
            [{"universe": [{"name": "BTC"}]}, [{"funding": "-0.05", "markPx": "0.0"}]],  # Zero mark price
        ]

        for payload in hl_fuzz_payloads:
            with patch.object(self.engine, "_http_post_json", return_value=payload):
                self.engine.clear_cache()
                ctx = self.engine.get_perpetual_context("BTC")
                self.assertIsNotNone(ctx)
                self.assertEqual(ctx["coin"], "BTC")
                self.assertIn("mark_price", ctx)
                self.assertIn("funding_rate_8h", ctx)
                self.assertIsInstance(ctx["mark_price"], (int, float))
                self.assertIsInstance(ctx["funding_rate_8h"], (int, float))

    def test_hyperliquid_predicted_fundings_fuzzing(self):
        """Fuzzes Hyperliquid predictedFundings endpoint."""
        pred_payloads = [
            [],
            {},
            None,
            "corrupted string",
            [["BTC", [["BinPerp", {"fundingRate": "0.0001"}]]]],  # Valid 1 venue
            [["BTC", "malformed venue list"]],
            [["BTC", [["BinPerp", {}]]]],  # Missing fundingRate
            [["BTC", [["BinPerp", {"fundingRate": "invalid_float"}]]]],
        ]

        for payload in pred_payloads:
            with patch.object(self.engine, "_http_post_json", return_value=payload):
                self.engine.clear_cache()
                pf = self.engine.get_predicted_fundings("BTC")
                self.assertIsNotNone(pf)
                self.assertIsInstance(pf, dict)

    def test_coingecko_global_fuzzing_rate_limit_and_null_data(self):
        """Fuzzes CoinGecko global endpoint."""
        cg_payloads = [
            {},
            {"status": {"error_code": 429, "error_message": "Rate limit exceeded"}},
            {"data": None},
            {"data": {}},
            {"data": {"total_market_cap": None, "market_cap_percentage": None}},
            {"data": {"total_market_cap": {"usd": "invalid"}, "market_cap_percentage": {"btc": -10.0}}},
        ]

        for payload in cg_payloads:
            with patch.object(self.engine, "_http_get", return_value=payload):
                self.engine.clear_cache()
                cg = self.engine.get_global_crypto_metrics()
                self.assertIsNotNone(cg)
                self.assertIn("total_market_cap_usd", cg)
                self.assertIn("btc_dominance_pct", cg)
                self.assertIsInstance(cg["total_market_cap_usd"], (int, float))
                self.assertGreaterEqual(cg["total_market_cap_usd"], 0.0)

    def test_yahoo_macro_fuzzing_null_results_and_zero_closes(self):
        """Fuzzes Yahoo Finance chart endpoint."""
        yahoo_payloads = [
            {},
            {"chart": {}},
            {"chart": {"result": None, "error": {"code": "Not Found"}}},
            {"chart": {"result": []}},
            {"chart": {"result": [{"meta": {}}]}},
            {"chart": {"result": [{"meta": {"regularMarketPrice": 0.0, "previousClose": 0.0}}]}},
            {"chart": {"result": [{"meta": {"regularMarketPrice": -50.0, "previousClose": -45.0}}]}},
            {"chart": {"result": [{"meta": {"regularMarketPrice": "invalid_px"}}]}},
        ]

        for payload in yahoo_payloads:
            with patch.object(self.engine, "_http_get", return_value=payload):
                self.engine.clear_cache()
                quote = self.engine.fetch_macro_quote("GC=F")
                self.assertIsNotNone(quote)
                self.assertEqual(quote["ticker"], "GC=F")
                self.assertIn("price", quote)
                self.assertIsInstance(quote["price"], (int, float))


# ==============================================================================
# AREA 4: EXTREME FUNDING RATE DIVERGENCE & BASIS SPREAD CALCULATIONS
# ==============================================================================

class TestArea4_ExtremeFundingAndBasisDivergence(unittest.TestCase):
    """Empirically stress tests funding rate calculations, basis spreads, and squeeze alerts."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)
        self.weekend_engine = WeekendCryptoArbitrageEngine(feeds_engine=self.engine)

    def test_extreme_positive_funding_rates(self):
        """
        Tests extreme positive funding rates: +0.05%, +0.10%, +0.50% / 8h (+54.75% to +547.5% APR).
        Verifies:
          - detect_funding_squeeze flags LONG_SQUEEZE_RISK and BEARISH_EXHAUSTION
          - WeekendCryptoArbitrageEngine flags LONG_CROWD_SQUEEZE and LONG_SPOT_SHORT_PERP_CARRY
        """
        rates = [0.0005, 0.0010, 0.0050, 0.0200]

        for fr in rates:
            with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": fr, "mark_price": 98500.0, "coin": "BTC"}):
                # 1. Feeds engine detection
                alert = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.0005)
                self.assertIsNotNone(alert)
                self.assertEqual(alert["squeeze_direction"], "LONG_SQUEEZE_RISK")
                self.assertEqual(alert["bias"], "BEARISH_EXHAUSTION")
                self.assertAlmostEqual(alert["funding_rate_8h"], fr, places=6)
                self.assertAlmostEqual(alert["annualized_pct"], fr * 3.0 * 365.0 * 100.0, places=1)

                # 2. Weekend arbitrage engine
                spread = self.weekend_engine.track_funding_spread("BTCUSD")
                self.assertTrue(spread["is_squeeze_detected"])
                self.assertEqual(spread["squeeze_direction"], "LONG_CROWD_SQUEEZE")
                self.assertEqual(spread["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")

    def test_extreme_negative_funding_rates(self):
        """
        Tests extreme negative funding rates: -0.05%, -0.10%, -0.50% / 8h (-54.75% to -547.5% APR).
        Verifies:
          - detect_funding_squeeze flags SHORT_SQUEEZE_RISK and BULLISH_EXHAUSTION
          - WeekendCryptoArbitrageEngine flags SHORT_CROWD_SQUEEZE and SHORT_SPOT_LONG_PERP_REBATE
        """
        rates = [-0.0005, -0.0010, -0.0050, -0.0200]

        for fr in rates:
            with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": fr, "mark_price": 98500.0, "coin": "BTC"}):
                # 1. Feeds engine detection
                alert = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.0005)
                self.assertIsNotNone(alert)
                self.assertEqual(alert["squeeze_direction"], "SHORT_SQUEEZE_RISK")
                self.assertEqual(alert["bias"], "BULLISH_EXHAUSTION")
                self.assertAlmostEqual(alert["funding_rate_8h"], fr, places=6)

                # 2. Weekend arbitrage engine
                spread = self.weekend_engine.track_funding_spread("BTCUSD")
                self.assertTrue(spread["is_squeeze_detected"])
                self.assertEqual(spread["squeeze_direction"], "SHORT_CROWD_SQUEEZE")
                self.assertEqual(spread["arbitrage_opportunity"], "SHORT_SPOT_LONG_PERP_REBATE")

    def test_neutral_and_near_zero_funding_rates(self):
        """
        Tests neutral rates: 0.000000, 0.000010, 0.000100.
        Verifies no false positive squeeze triggers.
        """
        neutral_rates = [0.0, 0.0000125, 0.0001000, -0.0001000, 0.0004999, -0.0004999]

        for fr in neutral_rates:
            with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": fr, "mark_price": 98500.0, "coin": "BTC"}):
                alert = self.engine.detect_funding_squeeze("BTC", threshold_8h=0.0005)
                self.assertIsNone(alert)

                spread = self.weekend_engine.track_funding_spread("BTCUSD")
                self.assertFalse(spread["is_squeeze_detected"])
                self.assertEqual(spread["squeeze_direction"], "NORMAL")
                self.assertEqual(spread["arbitrage_opportunity"], "NONE")

    def test_extreme_basis_divergences_and_zero_division_safety(self):
        """
        Tests basis spread calculations under:
          - Extreme Contango: Spot $95,000, Perp $115,000 (+$20,000 basis, +21.05% spread)
          - Extreme Backwardation: Spot $100,000, Perp $80,000 (-$20,000 basis, -20.00% spread)
          - Zero spot price: Spot $0.0, Perp $100.0 (must not crash with ZeroDivisionError)
          - Negative spot price: Spot -$50.0, Perp $100.0 (handled safely)
        """
        test_cases = [
            # spot, perp, expected_basis, expected_pct_approx
            (95000.0, 115000.0, 20000.0, 21.0526),
            (100000.0, 80000.0, -20000.0, -20.0000),
            (0.0, 100.0, 100.0, 10000.0),  # max(0, 1.0) = 1.0 -> 100/1 * 100 = 10000%
            (-50.0, 100.0, 150.0, 15000.0),  # max(-50, 1.0) = 1.0
        ]

        for spot, perp, exp_basis, exp_pct in test_cases:
            with patch.object(self.engine, "get_ticker_24hr", return_value={"last_price": spot, "symbol": "BTCUSD"}), \
                 patch.object(self.engine, "get_perpetual_context", return_value={"mark_price": perp, "funding_rate_8h": 0.0001, "coin": "BTC"}):
                res = self.engine.get_funding_rate_spread("BTC")
                self.assertEqual(res["basis_spread"], round(exp_basis, 2))
                self.assertAlmostEqual(res["basis_spread_pct"], round(exp_pct, 4), places=2)

                arb_res = self.weekend_engine.calculate_basis_and_spread("BTCUSD", spot, perp, 0.0001)
                self.assertEqual(arb_res["basis_dollar"], round(exp_basis, 2))

    def test_cross_venue_funding_spread_discrepancies(self):
        """
        Tests multi-venue spread when Hyperliquid is +0.08%, Binance predicted is -0.02%, and Bybit is +0.15%.
        Verifies calculation of cross_venue_spreads.
        """
        hl_ctx = {"mark_price": 98500.0, "funding_rate_8h": 0.0008, "coin": "BTC"}
        pred_venues = {
            "BinPerp": -0.0002,
            "BybitPerp": 0.0015,
            "HlPerp": 0.0008,
        }

        with patch.object(self.engine, "get_perpetual_context", return_value=hl_ctx), \
             patch.object(self.engine, "get_predicted_fundings", return_value=pred_venues), \
             patch.object(self.engine, "get_ticker_24hr", return_value={"last_price": 98400.0, "symbol": "BTCUSD"}):
            spread = self.engine.get_funding_rate_spread("BTC")
            self.assertIn("cross_venue_spreads", spread)
            cvs = spread["cross_venue_spreads"]
            self.assertIn("hl_vs_binance", cvs)
            self.assertIn("hl_vs_bybit", cvs)
            self.assertIsInstance(cvs["hl_vs_binance"], float)
            self.assertIsInstance(cvs["hl_vs_bybit"], float)

    def test_weekend_scanner_opportunity_generation_under_extreme_squeeze(self):
        """
        Verifies scan_weekend_crypto_setups prioritizes and flags opportunities with boosted confluence score (4.85)
        and ARBITRAGE_CARRY signal action under extreme funding squeeze conditions.
        """
        with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": 0.0012, "mark_price": 98500.0, "coin": "BTC"}), \
             patch.object(self.engine, "get_ticker_24hr", return_value={"last_price": 98400.0, "symbol": "BTCUSD"}):
            setups = self.weekend_engine.scan_weekend_crypto_setups()
            self.assertGreaterEqual(len(setups), 1)
            btc_setup = next(s for s in setups if s["symbol"] == "BTCUSD")
            self.assertEqual(btc_setup["signal_type"], "ARBITRAGE_CARRY")
            self.assertEqual(btc_setup["confluence_score"], 4.85)
            self.assertTrue(btc_setup["funding_spread"]["is_squeeze_detected"])
            self.assertEqual(btc_setup["funding_spread"]["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
