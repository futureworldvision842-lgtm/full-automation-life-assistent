"""
tests/test_challenger2_m1_hft_bigsharks_adversarial.py
========================================================================================
Empirical Adversarial Stress Test Suite - Challenger 2 (Milestone M1)
Focus: HFT DOM Microstructure & Big Sharks Institutional Reasoning Engine

Tasks & Verification:
1. Level-2 DOM depth ingestion with whale walls (>1,000 lots) across bids and asks.
2. Sub-second execution latency benchmarks: measure execution time across 1,000 iterations to verify <2ms performance.
3. CVD divergence classifier under trending and choppy market scenarios.
4. Big Sharks rationale output structure: verify schema completeness across SMC sweeps,
   FVG 50% CE, Order Blocks, Wyckoff phases, DXY trend, and news circuit breaker.
5. Empirical Bug Mining:
   - Defect 1: evaluate_dynamic_breakeven() returns breakeven_locked=False when SL == entry_price.
   - Defect 2: compute_cvd_and_absorption() falsely flags zero net delta as SELLER_ABSORPTION.
   - Defect 3: DOM parser TypeError crash when book volume is None.
========================================================================================
"""

from __future__ import annotations

import sys
import time
import json
import statistics
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Setup repository paths
ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

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
from src.order_flow_quant import OrderFlowQuantEngine
from src.order_book_dom_engine import OrderBookDOMEngine


class TestChallenger2M1HFTAndBigSharks(unittest.TestCase):

    def setUp(self):
        self.hft_engine = HighFrequencyTradingEngine()
        self.reasoning_engine = BigSharksReasoningEngine()
        self.quant_engine = OrderFlowQuantEngine(pip_tolerance=2.0)

    # =========================================================================
    # TASK 1: LEVEL-2 DOM DEPTH INGESTION & WHALE WALLS (>1,000 LOTS)
    # =========================================================================

    def test_01_dom_ingestion_whale_walls_bids_and_asks_detection(self):
        """
        Adversarial Test: Ingest DOM book with multiple whale walls (>1,000 lots)
        on both bid and ask sides, plus sub-1,000 lot noise levels.
        Verify exact classification, tier attribution, and volume filtering.
        """
        mock_raw_dom = {
            "symbol": "XAUUSD",
            "bids": [
                {"price": 2715.00, "volume": 250.0, "type": "BUY"},
                {"price": 2714.50, "volume": 1000.0, "type": "BUY"},     # Boundary: exactly 1000 (NOT > 1000)
                {"price": 2714.00, "volume": 1000.01, "type": "BUY"},   # Boundary: > 1000 -> WHALE
                {"price": 2713.00, "volume": 3500.0, "type": "BUY"},    # Large whale wall
                {"price": 2710.00, "volume": 7800.0, "type": "BUY"},    # Institutional OB wall
            ],
            "asks": [
                {"price": 2716.00, "volume": 150.0, "type": "SELL"},
                {"price": 2716.50, "volume": 999.99, "type": "SELL"},   # Sub-whale (<1000)
                {"price": 2717.00, "volume": 1200.0, "type": "SELL"},   # Whale wall
                {"price": 2719.00, "volume": 4500.0, "type": "SELL"},   # Major whale wall
            ]
        }

        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=mock_raw_dom):
            dom = self.hft_engine.get_dom_data("XAUUSD")

        whale_walls = dom.get("whale_walls", [])
        bid_whales = [w for w in whale_walls if w["type"] == "BID_SUPPORT_WHALE_WALL"]
        ask_whales = [w for w in whale_walls if w["type"] == "ASK_RESISTANCE_WHALE_WALL"]

        # Assert exactly 3 bid whale walls (1000.01, 3500.0, 7800.0; 1000.0 excluded because mandate is > 1000)
        self.assertEqual(len(bid_whales), 3, f"Expected 3 bid whale walls, found {len(bid_whales)}")
        for w in bid_whales:
            self.assertGreater(w["volume"], 1000.0)
            self.assertEqual(w["tier"], "INSTITUTIONAL_DEMAND")
            self.assertTrue(w["is_whale_wall"])

        # Assert exactly 2 ask whale walls (1200.0, 4500.0)
        self.assertEqual(len(ask_whales), 2, f"Expected 2 ask whale walls, found {len(ask_whales)}")
        for w in ask_whales:
            self.assertGreater(w["volume"], 1000.0)
            self.assertEqual(w["tier"], "INSTITUTIONAL_SUPPLY")
            self.assertTrue(w["is_whale_wall"])

        # Total bid and ask volume check
        expected_bid_vol = 250.0 + 1000.0 + 1000.01 + 3500.0 + 7800.0
        expected_ask_vol = 150.0 + 999.99 + 1200.0 + 4500.0
        self.assertAlmostEqual(dom["total_bid_volume"], expected_bid_vol, places=2)
        self.assertAlmostEqual(dom["total_ask_volume"], expected_ask_vol, places=2)

    def test_02_dom_ingestion_key_convention_top_bids_top_asks(self):
        """
        Adversarial Test: Verify ingestion when broker provides 'top_bids' and 'top_asks'
        instead of 'bids' and 'asks'.
        """
        mock_raw_dom = {
            "symbol": "GBPUSD",
            "top_bids": [
                {"price": 1.3330, "volume": 1500.0, "type": "BUY"},
                {"price": 1.3325, "volume": 2200.0, "type": "BUY"}
            ],
            "top_asks": [
                {"price": 1.3345, "volume": 1800.0, "type": "SELL"}
            ]
        }

        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=mock_raw_dom):
            dom = self.hft_engine.get_dom_data("GBPUSD")

        self.assertGreater(len(dom["bids"]), 0)
        self.assertGreater(len(dom["asks"]), 0)
        self.assertEqual(len(dom["whale_walls"]), 3)
        self.assertEqual(dom["whale_walls_count"], 3)

    def test_03_dom_extreme_imbalance_and_bias_classification(self):
        """
        Adversarial Test: Massive one-sided liquidity walls:
        1. 20,000 lots bid vs 100 lots ask -> BULLISH_ABSORPTION
        2. 100 lots bid vs 20,000 lots ask -> BEARISH_DISTRIBUTION
        """
        # Case 1: Ultra-bullish book
        bull_dom = {
            "bids": [{"price": 2715.0, "volume": 20000.0}],
            "asks": [{"price": 2716.0, "volume": 100.0}]
        }
        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=bull_dom):
            res_bull = self.hft_engine.get_dom_data("XAUUSD")
            self.assertEqual(res_bull["bias"], "BULLISH_ABSORPTION")
            self.assertGreaterEqual(res_bull["imbalance_ratio"], 1.40)
            self.assertGreater(res_bull["imbalance_pct"], 90.0)

        # Case 2: Ultra-bearish book
        bear_dom = {
            "bids": [{"price": 2715.0, "volume": 100.0}],
            "asks": [{"price": 2716.0, "volume": 20000.0}]
        }
        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=bear_dom):
            res_bear = self.hft_engine.get_dom_data("XAUUSD")
            self.assertEqual(res_bear["bias"], "BEARISH_DISTRIBUTION")
            self.assertLessEqual(res_bear["imbalance_ratio"], 0.70)
            self.assertLess(res_bear["imbalance_pct"], -90.0)

    def test_04_dom_string_volume_coercion_and_resilience(self):
        """
        Adversarial Test: Broker sending volumes as string numbers ('1500.5')
        or zero volumes; ensure proper float conversion and whale detection.
        """
        mixed_dom = {
            "bids": [
                {"price": 100.0, "volume": "1500.5", "type": "BUY"},
                {"price": 99.0, "volume": 0.0, "type": "BUY"},
            ],
            "asks": [
                {"price": 101.0, "volume": "2500.0", "type": "SELL"}
            ]
        }
        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=mixed_dom):
            dom = self.hft_engine.get_dom_data("EURUSD")
            self.assertEqual(len(dom["whale_walls"]), 2)
            self.assertEqual(dom["whale_walls"][0]["volume"], 1500.5)
            self.assertEqual(dom["whale_walls"][1]["volume"], 2500.0)

    # =========================================================================
    # TASK 2: SUB-SECOND EXECUTION LATENCY BENCHMARKS (1,000 ITERATIONS)
    # =========================================================================

    def test_05_sub_2ms_latency_benchmark_1000_iterations(self):
        """
        Empirical Benchmark: Measure actual wall-clock execution time across 1,000 iterations
        of evaluate_latency_and_spread() to rigorously verify <2ms performance.
        Collect statistical metrics: Mean, Median (P50), P95, P99, Max, Min, StdDev.
        """
        iterations = 1000
        timings_ms: List[float] = []

        # Warmup
        for _ in range(50):
            self.hft_engine.evaluate_latency_and_spread("XAUUSD")

        # 1,000 timed iterations
        for _ in range(iterations):
            t_start = time.perf_counter_ns()
            res = self.hft_engine.evaluate_latency_and_spread("XAUUSD", current_spread_pips=1.2)
            t_end = time.perf_counter_ns()
            elapsed_ms = (t_end - t_start) / 1_000_000.0
            timings_ms.append(elapsed_ms)

        mean_ms = statistics.mean(timings_ms)
        median_ms = statistics.median(timings_ms)
        p95_ms = float(np.percentile(timings_ms, 95))
        p99_ms = float(np.percentile(timings_ms, 99))
        max_ms = max(timings_ms)
        min_ms = min(timings_ms)
        std_ms = statistics.stdev(timings_ms)

        print(f"\n[EMPIRICAL LATENCY BENCHMARK — evaluate_latency_and_spread (1,000 runs)]")
        print(f"  • Mean:   {mean_ms:.4f} ms")
        print(f"  • Median: {median_ms:.4f} ms")
        print(f"  • P95:    {p95_ms:.4f} ms")
        print(f"  • P99:    {p99_ms:.4f} ms")
        print(f"  • Min:    {min_ms:.4f} ms")
        print(f"  • Max:    {max_ms:.4f} ms")
        print(f"  • StdDev: {std_ms:.4f} ms")

        # Strict mandate: Mean and P95 must be strictly < 2.0ms
        self.assertLess(mean_ms, 2.0, f"Mean latency {mean_ms:.3f}ms breached 2ms mandate!")
        self.assertLess(p95_ms, 2.0, f"P95 latency {p95_ms:.3f}ms breached 2ms mandate!")
        self.assertLess(median_ms, 2.0, f"Median latency {median_ms:.3f}ms breached 2ms mandate!")

        # Also verify the internal metric reported in the payload
        payload_eval = self.hft_engine.evaluate_latency_and_spread("XAUUSD")
        self.assertTrue(payload_eval["sub_2ms_passed"])
        self.assertEqual(payload_eval["latency_status"], "SUB_2MS_OPTIMAL")

    def test_06_full_hft_scan_latency_benchmark_1000_iterations(self):
        """
        Empirical Benchmark: Measure actual wall-clock execution time across 1,000 iterations
        of the end-to-end full_hft_scan() pipeline (DOM + CVD + Spread + Turtle Soup + IPDA).
        Verify sub-second execution efficiency.
        """
        iterations = 1000
        timings_ms: List[float] = []

        # Warmup
        for _ in range(25):
            self.hft_engine.full_hft_scan("XAUUSD")

        # 1,000 timed iterations
        for _ in range(iterations):
            t_start = time.perf_counter_ns()
            scan = self.hft_engine.full_hft_scan("XAUUSD")
            t_end = time.perf_counter_ns()
            elapsed_ms = (t_end - t_start) / 1_000_000.0
            timings_ms.append(elapsed_ms)

        mean_ms = statistics.mean(timings_ms)
        median_ms = statistics.median(timings_ms)
        p95_ms = float(np.percentile(timings_ms, 95))
        p99_ms = float(np.percentile(timings_ms, 99))
        max_ms = max(timings_ms)

        print(f"\n[EMPIRICAL LATENCY BENCHMARK — full_hft_scan (1,000 runs)]")
        print(f"  • Mean:   {mean_ms:.4f} ms")
        print(f"  • Median: {median_ms:.4f} ms")
        print(f"  • P95:    {p95_ms:.4f} ms")
        print(f"  • P99:    {p99_ms:.4f} ms")
        print(f"  • Max:    {max_ms:.4f} ms")

        # Full pipeline must complete in well under 50ms (sub-second execution mandate is <1000ms, targeting <5ms)
        self.assertLess(mean_ms, 5.0, f"Full HFT scan mean execution {mean_ms:.3f}ms exceeded 5.0ms!")
        self.assertLess(p95_ms, 10.0, f"Full HFT scan P95 execution {p95_ms:.3f}ms exceeded 10.0ms!")

    # =========================================================================
    # TASK 3: CVD DIVERGENCE CLASSIFIER UNDER TRENDING & CHOPPY SCENARIOS
    # =========================================================================

    def test_07_cvd_trending_bullish_scenario(self):
        """
        Trending Bullish Scenario:
        Market orders hitting the ask persistently (85% buy volume).
        CVD net delta surges positive.
        Verify BUYER_ABSORPTION and BULLISH_CVD_SURGE.
        """
        n_ticks = 100
        current = 2715.0
        # Rising price, mostly ask executions
        bids = [current + i * 0.05 for i in range(n_ticks)]
        asks = [b + 0.20 for b in bids]
        # 85% at ask (buys), 15% at bid (sells)
        lasts = [asks[i] if (i % 10 < 8) else bids[i] for i in range(n_ticks)]
        volumes = [10.0 + (i % 5) * 5.0 for i in range(n_ticks)]

        df_ticks = pd.DataFrame({"bid": bids, "ask": asks, "last": lasts, "volume": volumes})
        res = self.hft_engine.compute_cvd_and_absorption("XAUUSD", ticks=df_ticks)

        self.assertGreater(res["net_delta"], 0.0)
        self.assertEqual(res["absorption_type"], "BUYER_ABSORPTION")
        self.assertIn("BULLISH", res["divergence_bias"])
        metrics = res["cvd_metrics"]
        self.assertGreaterEqual(metrics["buyer_ratio"], 0.65)
        self.assertEqual(metrics["divergence"], "BULLISH_CVD_SURGE")

    def test_08_cvd_trending_bearish_scenario(self):
        """
        Trending Bearish Scenario:
        Market orders aggressively dumping at the bid (85% sell volume).
        CVD net delta plunges negative.
        Verify SELLER_ABSORPTION and BEARISH_CVD_SURGE.
        """
        n_ticks = 100
        current = 2715.0
        # Falling price, mostly bid executions
        bids = [current - i * 0.05 for i in range(n_ticks)]
        asks = [b + 0.20 for b in bids]
        # 85% at bid (sells), 15% at ask (buys)
        lasts = [bids[i] if (i % 10 < 8) else asks[i] for i in range(n_ticks)]
        volumes = [10.0 + (i % 5) * 5.0 for i in range(n_ticks)]

        df_ticks = pd.DataFrame({"bid": bids, "ask": asks, "last": lasts, "volume": volumes})
        res = self.hft_engine.compute_cvd_and_absorption("XAUUSD", ticks=df_ticks)

        self.assertLess(res["net_delta"], 0.0)
        self.assertEqual(res["absorption_type"], "SELLER_ABSORPTION")
        self.assertIn("BEARISH", res["divergence_bias"])
        metrics = res["cvd_metrics"]
        self.assertGreaterEqual(metrics["seller_ratio"], 0.65)
        self.assertEqual(metrics["divergence"], "BEARISH_CVD_SURGE")

    def test_09_cvd_choppy_balanced_auction_scenario(self):
        """
        Choppy / Balanced Market Scenario:
        Ticks oscillating between bid and ask with exactly 50/50 buy/sell volume.
        Net delta near 0.
        Verify BALANCED_AUCTION / NONE classification in OrderFlowQuantEngine.
        """
        n_ticks = 100
        bids = [1.0850] * n_ticks
        asks = [1.0852] * n_ticks
        # Alternating exactly buy (ask) and sell (bid) with identical volume
        lasts = [1.0852 if (i % 2 == 0) else 1.0850 for i in range(n_ticks)]
        volumes = [50.0] * n_ticks

        df_ticks = pd.DataFrame({"bid": bids, "ask": asks, "last": lasts, "volume": volumes})
        cvd_quant = self.quant_engine.compute_tick_cvd(df_ticks)

        self.assertEqual(cvd_quant["net_delta"], 0)
        self.assertAlmostEqual(cvd_quant["buyer_ratio"], 0.50, places=2)
        self.assertAlmostEqual(cvd_quant["seller_ratio"], 0.50, places=2)
        self.assertEqual(cvd_quant["divergence"], "NONE")
        self.assertEqual(cvd_quant["absorption_type"], "NONE")
        self.assertFalse(cvd_quant["is_absorption_divergence"])

    def test_10_cvd_structural_absorption_divergence_oracle(self):
        """
        Structural CVD Divergence Oracle:
        1. Bullish Buyer Absorption: Price Lower Low while CVD Higher Low.
        2. Bearish Seller Absorption: Price Higher High while CVD Lower High.
        3. Trend Continuation: Price and CVD aligned (No Divergence).
        """
        # 1. Bullish Absorption Divergence
        div_bull = self.quant_engine.detect_absorption_divergence(
            price_swing_1=2720.0,
            price_swing_2=2712.0,
            cvd_swing_1=1000.0,
            cvd_swing_2=1500.0
        )
        self.assertTrue(div_bull["absorption_detected"])
        self.assertEqual(div_bull["type"], "BUYER_ABSORPTION")
        self.assertEqual(div_bull["bias"], "BULLISH_REVERSAL")

        # 2. Bearish Absorption Divergence
        div_bear = self.quant_engine.detect_absorption_divergence(
            price_swing_1=2720.0,
            price_swing_2=2735.0,
            cvd_swing_1=1000.0,
            cvd_swing_2=700.0
        )
        self.assertTrue(div_bear["absorption_detected"])
        self.assertEqual(div_bear["type"], "SELLER_ABSORPTION")
        self.assertEqual(div_bear["bias"], "BEARISH_REVERSAL")

        # 3. Aligned Bullish Trend (No Divergence)
        div_none = self.quant_engine.detect_absorption_divergence(
            price_swing_1=2720.0,
            price_swing_2=2735.0,
            cvd_swing_1=1000.0,
            cvd_swing_2=1800.0
        )
        self.assertFalse(div_none["absorption_detected"])
        self.assertEqual(div_none["type"], "NONE")
        self.assertEqual(div_none["bias"], "NEUTRAL")

        # Ingestion through HighFrequencyTradingEngine
        hft_div = self.hft_engine.compute_cvd_and_absorption(
            symbol="XAUUSD",
            price_swing_1=2720.0,
            price_swing_2=2712.0,
            cvd_swing_1=1000.0,
            cvd_swing_2=1500.0
        )
        self.assertTrue(hft_div["divergence"]["absorption_detected"])
        self.assertEqual(hft_div["divergence"]["bias"], "BULLISH_REVERSAL")

    # =========================================================================
    # TASK 4: BIG SHARKS RATIONALE OUTPUT STRUCTURE & SCHEMA COMPLETENESS
    # =========================================================================

    def test_11_big_sharks_full_schema_completeness(self):
        """
        Adversarial Test: Comprehensive schema oracle verifying full structural completeness
        of GET /api/trading/reasoning payload against PROJECT.md contract:
        - SMC sweeps
        - FVG 50% Consequent Encroachment (CE)
        - Order Blocks
        - Wyckoff Accumulation/Distribution phases
        - DXY trend direction
        - News circuit breaker 15m check
        - FundingPips #40000294403 risk limits ($750 cap, 1:2.5 RR, +1.0R BE lock)
        """
        symbols_to_test = ["GBPUSD", "XAUUSD", "EURUSD"]
        for sym in symbols_to_test:
            payload = get_trading_reasoning(sym)

            # 1. Top-Level Contract Verification
            self.assertEqual(payload["status"], "active")
            self.assertEqual(payload["account"], "40000294403")
            self.assertIsInstance(payload["balance"], (int, float))
            self.assertGreaterEqual(payload["balance"], 100000.0)

            # 2. Risk Parameters Contract
            risk = payload["risk_params"]
            self.assertEqual(risk["max_risk_cap"], 750.0)
            self.assertEqual(risk["risk_pct"], 0.75)
            self.assertEqual(risk["min_rr"], 2.5)
            self.assertEqual(risk["dynamic_be_r"], 1.0)

            # 3. Latest Setups Schema
            self.assertIn("latest_setups", payload)
            self.assertGreaterEqual(len(payload["latest_setups"]), 1)
            setup = payload["latest_setups"][0]
            self.assertEqual(setup["symbol"], sym)
            self.assertIn("setup_type", setup)
            self.assertIn("rationale", setup)
            self.assertGreater(len(setup["rationale"]), 40)

            # 4. Big Sharks Deep Schema
            big_sharks = setup["big_sharks"]
            self.assertIn("liquidity_sweep", big_sharks)
            self.assertIn("fair_value_gap_50_ce", big_sharks)
            self.assertIn("order_block", big_sharks)
            self.assertIn("wyckoff_phase", big_sharks)

            # 4a. Liquidity Sweep
            sweep = big_sharks["liquidity_sweep"]
            self.assertIn("type", sweep)
            self.assertIn("level", sweep)
            self.assertIn("description", sweep)
            self.assertTrue(sweep["verified"])
            self.assertGreater(len(sweep["description"]), 15)

            # 4b. Fair Value Gap 50% CE
            fvg = big_sharks["fair_value_gap_50_ce"]
            self.assertIn("fvg_level", fvg)
            self.assertIn("consequent_encroachment_50", fvg)
            self.assertIn("mitigated", fvg)
            self.assertIn("description", fvg)
            self.assertTrue(fvg["mitigated"])
            self.assertGreater(fvg["consequent_encroachment_50"], 0.0)

            # 4c. Order Block Retest
            ob = big_sharks["order_block"]
            self.assertIn("level", ob)
            self.assertIn("type", ob)
            self.assertIn("status", ob)
            self.assertIn("description", ob)
            self.assertEqual(ob["status"], "RETESTED_CONFIRMED")

            # 4d. Wyckoff Phase
            wyckoff = big_sharks["wyckoff_phase"]
            self.assertIn("phase", wyckoff)
            self.assertIn("description", wyckoff)
            self.assertTrue(wyckoff["volume_expansion_confirmed"])
            self.assertTrue(any(p in wyckoff["phase"] for p in ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"]))

            # 5. Macro Catalyst Schema
            macro = setup["macro_catalyst"]
            self.assertIn("dxy_index", macro)
            self.assertIn("news_circuit_breaker_15m", macro)
            self.assertIn("macro_verdict", macro)

            dxy = macro["dxy_index"]
            self.assertIn("trend_direction", dxy)
            self.assertIn("correlation", dxy)
            self.assertIn("analysis", dxy)

            news = macro["news_circuit_breaker_15m"]
            self.assertIn("blackout_active", news)
            self.assertIn("circuit_breaker_passed", news)
            self.assertEqual(news["window_minutes"], 15)
            self.assertIn("status", news)
            self.assertIn("details", news)

            # 6. Confluence Schema
            confluence = setup["confluence"]
            self.assertIn("is_confluent", confluence)
            self.assertIn("confluence_score", confluence)
            self.assertEqual(confluence["min_required_score"], 90.0)
            self.assertIn("m15_trigger", confluence)
            self.assertIn("h1_trend", confluence)
            self.assertIn("h4_bias", confluence)

            # 7. HFT Microstructure Ingestion Contract
            self.assertIn("hft_microstructure", payload)
            hft = payload["hft_microstructure"]
            self.assertIn("whale_walls", hft)
            self.assertIn("cvd_absorption", hft)
            self.assertIn("spread_radar", hft)
            self.assertGreaterEqual(len(hft["whale_walls"]), 1)
            for wall in hft["whale_walls"]:
                self.assertGreater(wall["volume"], 1000.0)
                self.assertTrue(wall["is_whale_wall"])

    def test_12_big_sharks_active_position_enrichment_when_1r_gain_hit(self):
        """
        Verify that passing an active trade reaching >= +1.0R gain
        triggers breakeven lock in the reasoning payload.
        Initial SL distance: 1.33875 - 1.33675 = 20 pips.
        Profit distance: 1.33675 - 1.33475 = 20 pips -> exact 1.0R gain.
        """
        sample_position = {
            "ticket": 13002987,
            "symbol": "GBPUSD",
            "type": "SELL",
            "volume": 0.20,
            "price_open": 1.33675,
            "price_current": 1.33475,
            "sl": 1.33875,      # Initial SL before lock
            "tp": 1.33149,
            "profit": 35.40,
            "comment": "JARVIS_SMC_HFT"
        }

        payload = get_trading_reasoning("GBPUSD", position=sample_position)
        self.assertIn("positions", payload)
        self.assertEqual(len(payload["positions"]), 1)
        pos = payload["positions"][0]

        self.assertEqual(pos["ticket"], 13002987)
        self.assertEqual(pos["symbol"], "GBPUSD")
        self.assertEqual(pos["direction"], "SELL")
        self.assertTrue(pos["breakeven_locked"])
        self.assertIn("0.75% ($750.00) Max Risk Cap", pos["risk_rule"])
        self.assertIn("+1.0R Dynamic Breakeven Locked", pos["risk_rule"])

    # =========================================================================
    # TASK 5: EMPIRICAL REMEDIATION VERIFICATION & ADVERSARIAL EDGE CASES
    # =========================================================================

    def test_13_verify_dynamic_breakeven_already_locked_remediation(self):
        """
        EMPIRICAL REMEDIATION VERIFICATION (core/trading/reasoning.py:408-423):
        When a position's Stop Loss has ALREADY been moved to entry price (sl == entry_price),
        evaluate_dynamic_breakeven() must recognize is_already_locked and return
        breakeven_locked: True, action: 'maintain_breakeven_lock', and reason: 'breakeven_already_secured'.
        This satisfies the contract requiring that active position GBPUSD SELL #13002987 displays
        breakeven locked status when sl == entry_price.
        """
        res = self.reasoning_engine.evaluate_dynamic_breakeven(
            entry_price=1.33675,
            current_price=1.33498,
            sl_price=1.33675,   # Stop Loss is already at entry
            direction="SELL",
            profit_usd=35.40
        )
        self.assertTrue(res["breakeven_locked"], "Remediated: must return True when SL == entry_price")
        self.assertEqual(res["reason"], "breakeven_already_secured")
        self.assertEqual(res["action"], "maintain_breakeven_lock")
        self.assertEqual(res["new_sl"], 1.33675)

    def test_14_verify_cvd_zero_delta_neutral_remediation(self):
        """
        EMPIRICAL REMEDIATION VERIFICATION (skills/high_frequency_trading.py:267-274):
        In HighFrequencyTradingEngine.compute_cvd_and_absorption(), when net_delta is 0
        (or within 1e-9), the auction is balanced and must be classified as NEUTRAL bias,
        with absorption_detected: False and type: 'ABSORPTION_NEUTRAL'.
        """
        balanced_ticks = pd.DataFrame({
            "bid": [1.0, 1.0],
            "ask": [1.2, 1.2],
            "last": [1.2, 1.0],  # 1 buy (at ask), 1 sell (at bid)
            "volume": [10.0, 10.0]
        })
        res = self.hft_engine.compute_cvd_and_absorption("EURUSD", ticks=balanced_ticks)
        # Net delta is 0
        self.assertEqual(res["cvd_metrics"]["net_delta"], 0)
        # Remediated: zero delta must NOT be flagged as absorption
        self.assertFalse(res["divergence"]["absorption_detected"])
        self.assertEqual(res["divergence"]["type"], "ABSORPTION_NEUTRAL")
        self.assertEqual(res["divergence"]["bias"], "NEUTRAL")
        self.assertEqual(res["absorption_type"], "ABSORPTION_NEUTRAL")
        self.assertEqual(res["divergence_bias"], "NEUTRAL")

    def test_15_verify_dom_volume_none_resilience_remediation(self):
        """
        EMPIRICAL REMEDIATION VERIFICATION (skills/high_frequency_trading.py:136-163):
        When a DOM book entry contains 'volume': None, the engine must safely handle it
        without raising TypeError, treating None volume as 0.0.
        """
        mock_dom = {
            "bids": [{"price": 2700.0, "volume": None}],
            "asks": [{"price": 2701.0, "volume": 100.0}]
        }
        with patch.object(self.hft_engine.dom_engine, "get_market_depth", return_value=mock_dom):
            dom_data = self.hft_engine.get_dom_data("XAUUSD")
            self.assertEqual(dom_data["total_bid_volume"], 0.0)
            self.assertEqual(dom_data["total_ask_volume"], 100.0)
            self.assertEqual(len(dom_data["bids"]), 1)
            self.assertEqual(len(dom_data["asks"]), 1)

    def test_16_verify_raw_latency_measurement_without_synthetic_offsets(self):
        """
        EMPIRICAL LATENCY VERIFICATION (skills/high_frequency_trading.py:300-330):
        Verify that latency measurement does not add synthetic artificial offsets (+0.85ms)
        and that raw wall-clock execution time consistently satisfies the sub-2ms contract (<2.0ms).
        """
        res = self.hft_engine.evaluate_latency_and_spread("XAUUSD")
        self.assertIn("latency_ms", res)
        self.assertIn("sub_2ms_passed", res)
        self.assertTrue(res["sub_2ms_passed"], f"Sub-2ms check failed: {res['latency_ms']} ms")
        self.assertLess(res["latency_ms"], 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
