"""
tests/test_m234_adversarial_stress.py — Comprehensive Adversarial Stress Test Suite for Milestones 2, 3, and 4.

Coverage:
  Dimension 1 (M2): Intraday Scanning under High Noise, Zero Volume, and Extreme Candle Wicks.
  Dimension 2 (M3): Nightly Retrospective under Forecasting Errors, Market Shocks, and Rollover Spreads.
  Dimension 3 (M4): 24-Hour UTC Scheduler Trigger Matrix & WhatsApp Sub-Second (<1000ms) Rapid-Fire Latency.

Engineered by EMPIRICAL CHALLENGER (.agents/challenger_m234_1).
"""

import os
import sys
import time
import json
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

# Ensure repo root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.operational_cycle_scheduler import OperationalCycleScheduler
from src.whatsapp_qr_manager import WhatsAppQRManager, AUTHORIZED_CONTACTS, is_whitelisted_number
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.order_flow_quant import OrderFlowQuantEngine
from src.market_analyzer import MarketAnalyzer
from src.ai_trade_consultant import AITradeConsultant


class TestM2AdversarialIntradayScanning(unittest.TestCase):
    """
    Dimension 1 (M2): Stress testing intraday scanning under high noise,
    zero volume, extreme candle wicks, degenerate series, and confluence gating.
    """

    def setUp(self):
        self.engine = DailyInstitutionalRoutineEngine()
        self.of_quant = OrderFlowQuantEngine()
        self.analyzer = MarketAnalyzer(self.engine.config)

    def test_m2_high_noise_and_heavy_tailed_price_series(self):
        """
        Stress test intraday scanning with high-frequency Student-t heavy-tailed
        returns, random 500-pip jumps, and high volatility.
        """
        np.random.seed(999)
        count = 120
        base_price = 4350.0
        # Student-t noise with 3 degrees of freedom (fat tails)
        t_returns = np.random.standard_t(df=3, size=count) * 0.005
        # Add random Poisson jumps
        jumps = (np.random.poisson(lam=0.05, size=count) > 0) * np.random.choice([-0.02, 0.02], size=count)
        prices = base_price * np.exp(np.cumsum(t_returns + jumps))

        highs = prices * (1.0 + np.abs(np.random.standard_t(df=3, size=count)) * 0.003)
        lows = prices * (1.0 - np.abs(np.random.standard_t(df=3, size=count)) * 0.003)
        opens = (highs + lows) / 2.0
        closes = prices

        times = pd.date_range(end=datetime.now(timezone.utc), periods=count, freq="15min")
        df_m15 = pd.DataFrame({
            "time": times,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "tick_volume": np.random.randint(50, 5000, count)
        })

        # Inject into engine's candle fetch
        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_m15, "W1": df_m15, "MN1": df_m15,
            "H4": df_m15, "H1": df_m15, "M15": df_m15
        }

        scan = self.engine.scan_intraday_opportunities("XAUUSD")

        # Invariants
        self.assertIsInstance(scan, dict)
        self.assertIn("triggered", scan)
        self.assertIn("signal_type", scan)
        self.assertIn(scan["signal_type"], ["BUY", "SELL"])
        self.assertGreater(scan["entry_price"], 0.0)
        self.assertGreater(scan["sl_price"], 0.0)
        self.assertGreater(scan["tp1_price"], 0.0)
        self.assertGreater(scan["tp2_price"], 0.0)
        self.assertGreaterEqual(scan["confluence_score"], 0.0)
        self.assertLessEqual(scan["confluence_score"], 5.0)

        # Directional SL/TP ordering invariants
        if scan["signal_type"] == "BUY":
            self.assertLess(scan["sl_price"], scan["entry_price"], "BUY SL must be below Entry")
            self.assertGreater(scan["tp1_price"], scan["entry_price"], "BUY TP1 must be above Entry")
            self.assertGreater(scan["tp2_price"], scan["tp1_price"], "BUY TP2 must be above TP1")
        else:
            self.assertGreater(scan["sl_price"], scan["entry_price"], "SELL SL must be above Entry")
            self.assertLess(scan["tp1_price"], scan["entry_price"], "SELL TP1 must be below Entry")
            self.assertLess(scan["tp2_price"], scan["tp1_price"], "SELL TP2 must be below TP1")

    def test_m2_zero_volume_and_negative_volume_handling(self):
        """
        Stress test intraday scanning and Lee-Ready CVD when tick volume is zero
        or tick stream is completely empty.
        """
        count = 100
        times = pd.date_range(end=datetime.now(timezone.utc), periods=count, freq="15min")
        df_zero_vol = pd.DataFrame({
            "time": times,
            "open": np.full(count, 4370.0),
            "high": np.full(count, 4375.0),
            "low": np.full(count, 4365.0),
            "close": np.full(count, 4370.0),
            "tick_volume": np.zeros(count, dtype=int)
        })

        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_zero_vol, "W1": df_zero_vol, "MN1": df_zero_vol,
            "H4": df_zero_vol, "H1": df_zero_vol, "M15": df_zero_vol
        }
        # MT5 returns empty tick list
        self.engine.mt5.get_recent_ticks = lambda sym, count=100: []

        scan = self.engine.scan_intraday_opportunities("XAUUSD")
        self.assertIsInstance(scan, dict)
        self.assertFalse(np.isnan(scan["confluence_score"]))
        self.assertFalse(np.isinf(scan["confluence_score"]))
        # CVD should degrade safely to 0.50 buyer ratio
        self.assertEqual(scan["buyer_ratio"], 0.50)

        # Test OrderFlowQuant directly with empty ticks and single tick
        cvd_empty = self.of_quant.compute_tick_cvd([])
        self.assertEqual(cvd_empty["buyer_ratio"], 0.50)
        self.assertEqual(cvd_empty["net_delta"], 0)
        self.assertEqual(cvd_empty["cvd"], 0)

        cvd_single = self.of_quant.compute_tick_cvd([{"bid": 4370.0, "ask": 4370.2, "last": 4370.1, "volume": 10}])
        self.assertIn(cvd_single["buyer_ratio"], [0.50, 1.0, 0.0])

    def test_m2_extreme_wick_candles_and_flash_sweep(self):
        """
        Stress test with 1000-pip single-candle stop-hunt wicks (flash spikes).
        """
        count = 60
        times = pd.date_range(end=datetime.now(timezone.utc), periods=count, freq="15min")
        opens = np.full(count, 4350.0)
        closes = np.full(count, 4350.0)
        highs = np.full(count, 4355.0)
        lows = np.full(count, 4345.0)

        # Inject extreme 1000-pip wick (e.g. flash drop to 4250 and flash spike to 4450)
        lows[30] = 4250.0   # 1000 pips low wick
        highs[45] = 4450.0  # 1000 pips high wick

        df_wicks = pd.DataFrame({
            "time": times,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "tick_volume": np.random.randint(100, 1000, count)
        })

        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_wicks, "W1": df_wicks, "MN1": df_wicks,
            "H4": df_wicks, "H1": df_wicks, "M15": df_wicks
        }

        scan = self.engine.scan_intraday_opportunities("XAUUSD")
        self.assertIsInstance(scan, dict)
        self.assertGreater(scan["sl_pips"], 0.0)
        # Sizing calculations must remain bounded and strictly positive
        sizing = scan["sizing"]
        for acct_key in ["account_100k", "account_50k", "account_25k", "account_5k"]:
            lot = sizing[acct_key]["lots"]
            self.assertGreaterEqual(lot, 0.01, f"{acct_key} lot below minimum micro lot 0.01")
            self.assertLessEqual(lot, 5.00, f"{acct_key} lot exceeds max safety ceiling")

    def test_m2_flatline_and_zero_atr_boundary(self):
        """
        Stress test where price has 0 volatility (flatline open=high=low=close).
        """
        count = 50
        df_flat = pd.DataFrame({
            "time": pd.date_range(end=datetime.now(timezone.utc), periods=count, freq="15min"),
            "open": np.full(count, 4380.00),
            "high": np.full(count, 4380.00),
            "low": np.full(count, 4380.00),
            "close": np.full(count, 4380.00),
            "tick_volume": np.full(count, 100)
        })

        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_flat, "W1": df_flat, "MN1": df_flat,
            "H4": df_flat, "H1": df_flat, "M15": df_flat
        }

        scan = self.engine.scan_intraday_opportunities("XAUUSD")
        self.assertIsInstance(scan, dict)
        # Minimum SL distance fallback should engage (>= 10 pips)
        self.assertGreaterEqual(scan["sl_pips"], 10.0)

    def test_m2_confluence_gating_and_5section_card_integrity(self):
        """
        Verify that trigger status strictly matches confluence_score >= 4.5
        and the 5-section WhatsApp institutional card contains all mandatory sections.
        """
        # Run scan across multiple asset symbols
        for sym in ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            scan = self.engine.scan_intraday_opportunities(sym)
            if scan["confluence_score"] >= 4.5:
                self.assertTrue(scan["triggered"])
            else:
                self.assertFalse(scan["triggered"])

            card = scan["signal_card"]
            # 5 Institutional Sections must be present
            self.assertIn("1. BIG SHARKS (MARKET MAKER) GAME & PSYCHOLOGY:", card)
            self.assertIn("2. TECHNICAL CONFLUENCES & EVIDENCE", card)
            self.assertIn("3. GLOBAL MACRO NEWS & TAILWINDS:", card)
            self.assertIn("4. CONTINGENCY PLAN & DISCIPLINE", card)
            self.assertIn("5. MULTI-ACCOUNT SIZING RECOMMENDATION:", card)
            # Must include 1:1 Breakeven and 50% TP1 rules
            self.assertIn("Breakeven", card)
            self.assertIn("50% volume close", card)
            self.assertIn("Funding Pips", card)


class TestM3AdversarialNightlyRetrospective(unittest.TestCase):
    """
    Dimension 2 (M3): Stress testing nightly retrospective under massive
    forecasting errors, black swan market shocks, spread widening, and Bayesian memory bounds.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.brain = DeepSelfLearningAgent(memory_dir=self.temp_dir)
        self.engine = DailyInstitutionalRoutineEngine()
        self.engine.brain = self.brain

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_m3_black_swan_crash_and_extreme_deviation(self):
        """
        Adversarial Scenario: Morning forecast predicted Bullish OTE target R1=4400,
        invalidation S1=4320. Massive Black Swan shock occurs: Gold crashes to 2500 (1800 point shock).
        """
        count = 100
        # Create crashed market data
        df_crash = pd.DataFrame({
            "time": pd.date_range(end=datetime.now(timezone.utc), periods=count, freq="15min"),
            "open": np.linspace(4350.0, 2500.0, count),
            "high": np.linspace(4360.0, 2550.0, count),
            "low": np.linspace(4340.0, 2480.0, count),
            "close": np.linspace(4350.0, 2500.0, count),
            "tick_volume": np.random.randint(1000, 10000, count)
        })

        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_crash, "W1": df_crash, "MN1": df_crash,
            "H4": df_crash, "H1": df_crash, "M15": df_crash
        }

        retrospective = self.engine.generate_nightly_market_retrospective("XAUUSD")
        self.assertIsInstance(retrospective, str)
        self.assertIn("NIGHTLY MARKET CLOSE RETROSPECTIVE", retrospective)
        self.assertIn("1. MORNING FORECAST VS. ACTUAL MARKET OUTCOME:", retrospective)
        self.assertIn("2. FORENSIC AUDIT & COGNITIVE LESSONS", retrospective)
        self.assertIn("3. FLEET PORTFOLIO CLOSING EQUITY:", retrospective)
        # Should record NEWS_SHOCK_SWEEP or appropriate forensic diagnosis
        self.assertTrue(
            "NEWS_SHOCK_SWEEP" in retrospective or "CLEAN_OTE_EXPANSION" in retrospective or "LOW_VOLATILITY_CHOP" in retrospective
        )

    def test_m3_ultra_low_volatility_consolidation_chop(self):
        """
        Adversarial Scenario: Market has normal ATR in previous days (e.g. D1 range 40 pts, M15 ATR 10 pts)
        but today's entire session remained compressed in 3-point range (day_range < 0.40 * ATR_14).
        Forensic diagnosis must classify as LOW_VOLATILITY_CHOP.
        """
        count = 50
        # D1 with previous normal day (high 4400, low 4340, close 4370) -> Pivot=4370, R1=4400, S1=4340
        df_d1 = pd.DataFrame({
            "time": [datetime.now(timezone.utc) - timedelta(days=2), datetime.now(timezone.utc) - timedelta(days=1)],
            "open": [4350.0, 4360.0],
            "high": [4390.0, 4400.0],
            "low": [4330.0, 4340.0],
            "close": [4360.0, 4370.0],
            "tick_volume": [5000, 5000]
        })

        # M15 has bars with average high-low of 10 points for ATR_14 calculation, but today's high is 4372 and low is 4369 (range = 3.0 < 0.40 * 10 = 4.0)
        highs = np.full(count, 4372.0)
        lows = np.full(count, 4369.0)
        # For historical ATR: earlier bars had 10 pt range
        highs[:30] = 4375.0
        lows[:30] = 4365.0
        # last 14 bars have 10 pt range for ATR_14
        highs[-14:] = 4375.0
        lows[-14:] = 4365.0
        # But today's max high is 4375 and min low is 4365... wait, actual_high is max of whole df_m15.
        # If today's df_m15 is completely compressed: all bars high=4372, low=4369 (range 3.0)
        # and ATR_14 fallback or previous H1 has 12.0 ATR.
        df_tight_m15 = pd.DataFrame({
            "time": pd.date_range(end=datetime.now(timezone.utc), periods=10, freq="15min"),
            "open": np.full(10, 4370.0),
            "high": np.full(10, 4372.0),
            "low": np.full(10, 4369.0),
            "close": np.full(10, 4370.0),
            "tick_volume": np.full(10, 50)
        })

        # Since len(df_tight_m15) < 14, atr_14 = 12.0 (fallback default).
        # day_range = actual_high (4372) - actual_low (4369) = 3.0.
        # 0.40 * 12.0 = 4.8. 3.0 < 4.8 -> LOW_VOLATILITY_CHOP!
        # forecast_tp1 = 4400.0, forecast_inval = 4340.0.
        # actual_high (4372) < forecast_tp1 (4400) -> not clean expansion.
        # actual_low (4369) > forecast_inval (4340) -> not news shock.
        # day_range (3.0) < 0.40 * atr_14 (4.8) -> LOW_VOLATILITY_CHOP!

        self.engine._fetch_symbol_candles = lambda sym: {
            "D1": df_d1, "W1": df_d1, "MN1": df_d1,
            "H4": df_tight_m15, "H1": df_tight_m15, "M15": df_tight_m15
        }

        retrospective = self.engine.generate_nightly_market_retrospective("XAUUSD")
        self.assertIsInstance(retrospective, str)
        self.assertIn("LOW_VOLATILITY_CHOP", retrospective)
        self.assertIn("0.00%* (100% Compliant", retrospective)

    def test_m3_bayesian_weight_clamping_strict_boundaries(self):
        """
        Stress test Bayesian updating over 150 consecutive wins and 150 consecutive losses.
        Must strictly clamp to [0.65, 1.60] interval and never overflow.
        """
        pattern = "TEST_PATTERN_OTE"

        # 150 Consecutive Wins
        for i in range(150):
            res = self.brain.record_episodic_experience(
                symbol="XAUUSD", direction="BUY", pnl=500.0, pattern=pattern,
                reason=f"Win #{i}", regime="BULLISH"
            )
            self.assertLessEqual(res["new_pattern_weight"], 1.60, f"Weight exceeded ceiling: {res['new_pattern_weight']}")

        weights = self.brain.semantic_memory["pattern_confidence_weights"]
        self.assertLessEqual(weights[pattern], 1.60, "Weight exceeded ceiling")
        self.assertGreater(weights[pattern], 1.55, "Weight failed to approach ceiling on wins")

        # 150 Consecutive Losses
        for i in range(150):
            res = self.brain.record_episodic_experience(
                symbol="XAUUSD", direction="SELL", pnl=-500.0, pattern=pattern,
                reason=f"Loss #{i}", regime="BEARISH"
            )
            self.assertGreaterEqual(res["new_pattern_weight"], 0.65, f"Weight dropped below floor: {res['new_pattern_weight']}")

        weights = self.brain.semantic_memory["pattern_confidence_weights"]
        self.assertGreaterEqual(weights[pattern], 0.65, "Weight failed to stay within [0.65, 1.60]")
        self.assertLessEqual(weights[pattern], 1.60, "Weight failed to stay within [0.65, 1.60]")

    def test_m3_episodic_memory_ring_buffer_and_extreme_pnl(self):
        """
        Stress test 1000 rapid memory commits with extreme PnLs (-$10M to +$50M).
        Ring buffer must strictly cap at 500 items.
        """
        for i in range(1000):
            pnl_val = (i % 2 == 0) * 50_000_000.0 - (i % 2 != 0) * 10_000_000.0
            self.brain.record_episodic_experience(
                symbol="XAUUSD", direction="BUY" if i % 2 == 0 else "SELL",
                pnl=pnl_val, pattern="OTE_705_FIBONACCI",
                reason=f"Stress Experience #{i}", regime="VOLATILE"
            )

        self.assertEqual(len(self.brain.episodic_memory), 500, "Episodic memory exceeded 500 ring buffer capacity")

        # Verify JSON persistence on disk
        with open(self.brain.episodic_path, "r") as f:
            disk_memories = json.load(f)
        self.assertEqual(len(disk_memories), 500)

        # Summary check
        summary = self.brain.get_cognitive_ai_summary()
        self.assertEqual(summary["total_episodic_experiences"], 500)
        self.assertEqual(summary["win_rate_pct"], 50.0)


class TestM4AdversarialSchedulerAndWhatsAppCommands(unittest.TestCase):
    """
    Dimension 3 (M4): Stress testing scheduler trigger logic across all 24 hours (1440 mins),
    scheduler lifecycle stability, deduplication, and rapid-fire WhatsApp command latencies (< 1000ms).
    """

    def setUp(self):
        self.engine = DailyInstitutionalRoutineEngine()
        self.scheduler = OperationalCycleScheduler(routine_engine=self.engine)
        self.qr_manager = WhatsAppQRManager()
        self.valid_sender = "923468053268@s.whatsapp.net"

    def test_m4_scheduler_24_hour_utc_exhaustive_sweep(self):
        """
        Exhaustive sweep of all 1,440 minutes in a 24-hour UTC day:
        - 06:30 UTC -> trigger_morning == True (exactly 1 minute)
        - 21:30 UTC -> trigger_nightly == True (exactly 1 minute)
        - London: 07:00-09:59 (3h = 180 min)
        - NY AM: 12:00-14:59 (3h = 180 min)
        - NY PM: 18:00-19:59 (2h = 120 min)
        - Total Killzone minutes = 480 minutes (8 hours)
        - trigger_intraday -> exactly 480 / 5 = 96 triggers
        - Outside killzone -> trigger_intraday == False always
        """
        base_date = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)

        morning_triggers = 0
        nightly_triggers = 0
        killzone_minutes = 0
        intraday_triggers = 0

        for minute_offset in range(1440):
            current_time = base_date + timedelta(minutes=minute_offset)
            triggers = self.scheduler.evaluate_schedule_trigger(current_time)

            if triggers["trigger_morning"]:
                morning_triggers += 1
                self.assertEqual(current_time.strftime("%H:%M"), "06:30")

            if triggers["trigger_nightly"]:
                nightly_triggers += 1
                self.assertEqual(current_time.strftime("%H:%M"), "21:30")

            if triggers["in_killzone"]:
                killzone_minutes += 1
                h = current_time.hour
                self.assertTrue((7 <= h < 10) or (12 <= h < 15) or (18 <= h < 20))

            if triggers["trigger_intraday"]:
                intraday_triggers += 1
                self.assertTrue(triggers["in_killzone"])
                self.assertEqual(current_time.minute % 5, 0)
            else:
                if not triggers["in_killzone"]:
                    self.assertFalse(triggers["trigger_intraday"])

        self.assertEqual(morning_triggers, 1, "Morning briefing must trigger exactly once per day at 06:30 UTC")
        self.assertEqual(nightly_triggers, 1, "Nightly retrospective must trigger exactly once per day at 21:30 UTC")
        self.assertEqual(killzone_minutes, 480, "Total active killzone time must equal 480 minutes (8 hours)")
        self.assertEqual(intraday_triggers, 96, "Intraday scanning must trigger exactly 96 times per day (every 5m in KZ)")

    def test_m4_scheduler_deduplication_and_same_day_idempotence(self):
        """
        Verify that multiple ticks within the same trigger minute execute only once.
        """
        t_0630 = datetime(2026, 8, 15, 6, 30, 0, tzinfo=timezone.utc)
        # Execute 5 consecutive ticks at 06:30
        results_1 = self.scheduler.execute_cycle_tick(t_0630)
        self.assertIn("MORNING_BRIEFING", results_1["executed"])

        results_2 = self.scheduler.execute_cycle_tick(t_0630)
        self.assertNotIn("MORNING_BRIEFING", results_2["executed"], "Morning briefing re-executed within same day")

        # Execute 5 consecutive ticks at 21:30
        t_2130 = datetime(2026, 8, 15, 21, 30, 0, tzinfo=timezone.utc)
        res_night_1 = self.scheduler.execute_cycle_tick(t_2130)
        self.assertIn("NIGHTLY_RETROSPECTIVE", res_night_1["executed"])

        res_night_2 = self.scheduler.execute_cycle_tick(t_2130)
        self.assertNotIn("NIGHTLY_RETROSPECTIVE", res_night_2["executed"], "Nightly retrospective re-executed on same day")

    def test_m4_scheduler_lifecycle_start_stop_rapid_churn(self):
        """
        Stress test rapid start/stop churn of the scheduler daemon thread.
        """
        fast_scheduler = OperationalCycleScheduler(routine_engine=self.engine, interval_sec=1)
        for i in range(5):
            fast_scheduler.start()
            self.assertTrue(fast_scheduler.is_running)
            time.sleep(0.01)
            fast_scheduler.stop()
            self.assertFalse(fast_scheduler.is_running)

    def test_m4_whatsapp_all_18_commands_subsecond_latency_benchmark(self):
        """
        Benchmark every single WhatsApp interactive command:
        MUST return formatted string and respond in < 1000ms SLA.
        """
        commands = [
            "status",
            "fleet",
            "trades",
            "gold",
            "evidence",
            "plan",
            "why",
            "scan",
            "signal",
            "news",
            "whales",
            "crisis",
            "gsr",
            "brain",
            "morning",
            "night",
            "risk",
            "report",
            # Controls & Consultations
            "help",
            "breakeven",
            "scale 50%",
            "close all",
            "buy gold 0.10",
            "pause",
            "resume",
            "consult gold par buy karun ya wait?",
            "explain why we took last trade in urdu"
        ]

        latencies = {}
        for cmd in commands:
            t0 = time.perf_counter()
            response = self.qr_manager.handle_incoming_command(cmd, self.valid_sender)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies[cmd] = elapsed_ms

            self.assertIsInstance(response, str, f"Command '{cmd}' returned non-string")
            self.assertGreater(len(response), 10, f"Command '{cmd}' returned empty/trivial response")
            self.assertLess(elapsed_ms, 1000.0, f"Command '{cmd}' exceeded 1000ms SLA: {elapsed_ms:.2f}ms")

        # Report latencies
        max_cmd = max(latencies, key=latencies.get)
        avg_ms = sum(latencies.values()) / len(latencies)
        print(f"\n[WhatsApp Benchmark] Tested {len(commands)} commands. Avg Latency: {avg_ms:.2f}ms | Worst: '{max_cmd}' ({latencies[max_cmd]:.2f}ms)")
        self.assertLess(avg_ms, 200.0, f"Average command latency too high: {avg_ms:.2f}ms")

    def test_m4_whatsapp_rapid_fire_spam_burst(self):
        """
        Stress test 100 consecutive rapid-fire commands in tight loop.
        """
        cmds = ["status", "gold", "scan", "signal", "brain", "risk", "fleet", "trades"]
        latencies = []

        t_total_start = time.perf_counter()
        for i in range(100):
            cmd = cmds[i % len(cmds)]
            t0 = time.perf_counter()
            resp = self.qr_manager.handle_incoming_command(cmd, self.valid_sender)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            self.assertTrue(len(resp) > 0)
            self.assertLess(lat, 1000.0)

        total_elapsed = time.perf_counter() - t_total_start
        throughput = 100.0 / total_elapsed
        print(f"[WhatsApp Burst] 100 commands processed in {total_elapsed:.3f}s ({throughput:.1f} req/sec). Max single latency: {max(latencies):.2f}ms")
        self.assertGreater(throughput, 10.0, "Throughput below 10 requests/sec")

    def test_m4_whatsapp_concurrent_multithreaded_stress(self):
        """
        Stress test concurrent queries from 8 parallel threads hammering the WhatsApp command engine.
        """
        num_threads = 8
        requests_per_thread = 15
        total_requests = num_threads * requests_per_thread

        def worker_task(thread_id):
            cmds = ["gold", "status", "scan", "fleet", "risk", "brain", "signal", "help"]
            results = []
            for j in range(requests_per_thread):
                cmd = cmds[j % len(cmds)]
                t0 = time.perf_counter()
                resp = self.qr_manager.handle_incoming_command(cmd, self.valid_sender)
                elapsed = (time.perf_counter() - t0) * 1000.0
                results.append((len(resp) > 0, elapsed))
            return results

        t_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            all_res = [f.result() for f in futures]
        t_total = time.perf_counter() - t_start

        flat_results = [item for sublist in all_res for item in sublist]
        success_count = sum(1 for ok, _ in flat_results if ok)
        max_lat = max(lat for _, lat in flat_results)

        self.assertEqual(success_count, total_requests, "Concurrent requests failed")
        self.assertLess(max_lat, 1000.0, f"Max concurrent latency exceeded 1000ms: {max_lat:.2f}ms")
        print(f"[WhatsApp Concurrent] {total_requests} concurrent requests completed in {t_total:.3f}s. Max Latency: {max_lat:.2f}ms. Success: {success_count}/{total_requests}")

    def test_m4_security_whitelist_adversarial_rejection(self):
        """
        Adversarial Security Attack: Attempt to execute commands from unauthorized senders,
        malicious strings, spoofed IDs, and SQL/Command injections.
        Must drop and return empty string "" with zero execution.
        """
        malicious_senders = [
            "1234567890@s.whatsapp.net",
            "9999999999@c.us",
            "hacker@whatsapp.net",
            "923000000000@s.whatsapp.net",
            "admin@server",
            "'; DROP TABLE users; --@s.whatsapp.net",
            "<script>alert(1)</script>@s.whatsapp.net",
            "",
            None
        ]

        commands_to_attempt = [
            "buy gold 10.0",
            "kill switch",
            "close all",
            "status",
            "risk",
            "pause bot"
        ]

        for sender in malicious_senders:
            for cmd in commands_to_attempt:
                resp = self.qr_manager.handle_incoming_command(cmd, sender)
                self.assertEqual(resp, "", f"Security Breach! Unauthorized sender '{sender}' executed '{cmd}'")


if __name__ == "__main__":
    unittest.main()
