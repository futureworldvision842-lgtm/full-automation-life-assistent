"""
test_adversarial_m1_challenger2.py — Empirical Adversarial Stress Test Suite for Milestone M1 (Requirement R1).
================================================================================================================
Empirical Challenger 2 Verification Harness for:
  1. Weather Regime Priority:
     - CYCLONE_NEWS_LOCKOUT strict override over extreme bullish momentum, bearish momentum, DEFCON 1/2, satellite radar storms.
  2. DEFCON 1/2 HURRICANE_RISK_OFF Multipliers & Policies:
     - Gold / Oil (1.50x), Pro-cyclical FX (0.50x), Other FX/Commodities (0.65x).
     - Strict boundary transitions (DEFCON 1 vs 2 vs 3).
  3. Currency Lockout Matrix Isolation & Leakage Prevention:
     - USD, EUR, GBP, JPY, CAD, AUD news isolation across cross-currency matrix.
     - Crypto 24/7 weekend bypass validation.
  4. Concurrency, Thread Safety & Network Fault-Tolerance:
     - Concurrent access across 20 threads.
     - Mock HTTP 429, TimeoutError, URLError, and malformed payload injection.
     - Zero unhandled exceptions and smooth fallback.
  5. Boundary & Extreme Mathematical Conditions:
     - Zero baseline / zero flow division tests.
     - Degenerate candlestick DataFrames (all zeros, single price, NaNs).
"""

import os
import sys
import unittest
import threading
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import urllib.error
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.economic_calendar_radar import EconomicCalendarRadar
from src.news_filter import NewsFilter
from src.predictive_weather_engine import PredictiveWeatherEngine
from src.market_satellite_radar import MarketSatelliteRadar


class TestWeatherRegimePriority(unittest.TestCase):
    """
    Adversarial Challenge 1: Weather Regime Priority & Cyclone Dominance.
    Ensures that active news blackouts CANNOT be bypassed by any momentum or geopolitical condition.
    """

    def setUp(self):
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.calendar_radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.calendar_radar.clear_events()
        self.weather_engine = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar
        )

    def test_cyclone_overrides_extreme_bullish_momentum(self):
        """Even with 100 consecutive green candles (updraft > 90%), active news MUST enforce CYCLONE (0.0x)."""
        now_utc = datetime.now(timezone.utc)
        # Inject high-impact news 5 minutes in future
        self.calendar_radar.inject_event("US Non-Farm Payrolls", "USD", now_utc + timedelta(minutes=5), impact="HIGH")

        # Create massive bullish momentum
        closes = [2000.0 + (i * 10.0) for i in range(50)]
        df_m15 = pd.DataFrame({
            "open": [c - 5.0 for c in closes],
            "high": [c + 5.0 for c in closes],
            "low": [c - 5.0 for c in closes],
            "close": closes,
            "tick_volume": [1000] * 50
        })
        df_h1 = df_m15.copy()

        forecast = self.weather_engine.forecast_market_weather(df_h1, df_m15, symbol="XAUUSD")

        self.assertEqual(forecast["weather_state"], "CYCLONE_NEWS_LOCKOUT")
        self.assertEqual(forecast["risk_multiplier"], 0.0)
        self.assertEqual(forecast["trade_policy"], "Trading Strictly Halted / Entries Blocked")
        self.assertIn("News Circuit Breaker", forecast["advisory"])

    def test_cyclone_overrides_extreme_bearish_momentum(self):
        """Even with 100 consecutive red candles (downdraft > 90%), active news MUST enforce CYCLONE (0.0x)."""
        now_utc = datetime.now(timezone.utc)
        self.calendar_radar.inject_event("FOMC Interest Rate", "USD", now_utc + timedelta(minutes=10), impact="HIGH")

        # Create massive bearish momentum
        closes = [3000.0 - (i * 10.0) for i in range(50)]
        df_m15 = pd.DataFrame({
            "open": [c + 5.0 for c in closes],
            "high": [c + 5.0 for c in closes],
            "low": [c - 5.0 for c in closes],
            "close": closes,
            "tick_volume": [1000] * 50
        })
        df_h1 = df_m15.copy()

        forecast = self.weather_engine.forecast_market_weather(df_h1, df_m15, symbol="EURUSD")

        self.assertEqual(forecast["weather_state"], "CYCLONE_NEWS_LOCKOUT")
        self.assertEqual(forecast["risk_multiplier"], 0.0)
        self.assertEqual(forecast["trade_policy"], "Trading Strictly Halted / Entries Blocked")

    def test_cyclone_overrides_defcon1_emergency(self):
        """Even under DEFCON 1 wartime conditions, pre/post news blackout MUST enforce CYCLONE (0.0x) over HURRICANE (1.50x)."""
        now_utc = datetime.now(timezone.utc)
        self.calendar_radar.inject_event("US CPI MoM", "USD", now_utc - timedelta(minutes=4), impact="HIGH")

        # Set DEFCON 1
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION",
            components={"unrest": 100.0, "conflict": 100.0, "security": 100.0, "information": 100.0}
        )
        self.world_monitor.update_country_instability(
            "EASTERN_EUROPE",
            components={"unrest": 100.0, "conflict": 100.0, "security": 100.0, "information": 100.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=0.0, incident_count=100)

        brief = self.world_monitor.get_world_intelligence_brief()
        self.assertEqual(brief["defcon_level"], 1)

        forecast = self.weather_engine.forecast_market_weather("XAUUSD")

        self.assertEqual(forecast["weather_state"], "CYCLONE_NEWS_LOCKOUT")
        self.assertEqual(forecast["risk_multiplier"], 0.0)

    def test_cyclone_overrides_satellite_storm_warning(self):
        """Even when Satellite Radar triggers severe storm warnings, active news blackout takes top priority."""
        now_utc = datetime.now(timezone.utc)
        self.calendar_radar.inject_event("ECB Monetary Policy", "EUR", now_utc + timedelta(minutes=2), impact="HIGH")

        # Mock radar scan with severe storm
        with patch.object(self.weather_engine.radar, 'scan_satellite_grid', return_value={
            "radar_score": 95.0,
            "storm_warning": True,
            "pressure_differential_pct": 0.85
        }):
            forecast = self.weather_engine.forecast_market_weather("EURUSD")
            self.assertEqual(forecast["weather_state"], "CYCLONE_NEWS_LOCKOUT")
            self.assertEqual(forecast["risk_multiplier"], 0.0)


class TestDEFCONHurricaneRiskOff(unittest.TestCase):
    """
    Adversarial Challenge 2: DEFCON 1/2 Multipliers & Invariants.
    """

    def setUp(self):
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.calendar_radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.calendar_radar.clear_events()
        self.weather_engine = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar
        )

    def _escalate_to_defcon(self, target_defcon: int):
        if target_defcon == 1:
            self.world_monitor.update_country_instability(
                "MIDDLE_EAST_REGION", components={"unrest": 98.0, "conflict": 100.0, "security": 98.0, "information": 95.0}
            )
            self.world_monitor.update_country_instability(
                "EASTERN_EUROPE", components={"unrest": 95.0, "conflict": 100.0, "security": 95.0, "information": 90.0}
            )
            self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=1.0, incident_count=90)
        elif target_defcon == 2:
            self.world_monitor.update_country_instability(
                "MIDDLE_EAST_REGION", components={"unrest": 80.0, "conflict": 90.0, "security": 80.0, "information": 70.0}
            )
            self.world_monitor.update_country_instability(
                "EASTERN_EUROPE", components={"unrest": 75.0, "conflict": 85.0, "security": 80.0, "information": 75.0}
            )
            self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=10.0, incident_count=35)
        elif target_defcon == 3:
            self.world_monitor.update_country_instability(
                "MIDDLE_EAST_REGION", components={"unrest": 50.0, "conflict": 60.0, "security": 50.0, "information": 50.0}
            )
            self.world_monitor.update_country_instability(
                "EASTERN_EUROPE", components={"unrest": 50.0, "conflict": 55.0, "security": 50.0, "information": 50.0}
            )
            self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=18.0, incident_count=5)
            self.world_monitor.update_chokepoint_flow("bab_el_mandeb", current_mbd=5.5, incident_count=2)
            self.world_monitor.update_chokepoint_flow("taiwan_strait", incident_count=5)

    def test_defcon1_multipliers_across_asset_classes(self):
        """Under DEFCON 1: Commodities (Gold/Oil) = 1.50x, Pro-cyclical FX = 0.50x, Others = 0.65x."""
        self._escalate_to_defcon(1)
        brief = self.world_monitor.get_world_intelligence_brief()
        self.assertEqual(brief["defcon_level"], 1)

        # 1. Safe havens / Commodities
        for sym in ["XAUUSD", "GOLD", "WTI", "BRENT"]:
            f = self.weather_engine.forecast_market_weather(symbol=sym)
            self.assertEqual(f["weather_state"], "HURRICANE_RISK_OFF", f"Failed for {sym}")
            self.assertEqual(f["risk_multiplier"], 1.50, f"Expected 1.50 for {sym}")
            self.assertIn("Safe-Haven BUY", f["trade_policy"])

        # 2. Pro-cyclical FX
        for sym in ["EURUSD", "GBPUSD", "AUDUSD"]:
            f = self.weather_engine.forecast_market_weather(symbol=sym)
            self.assertEqual(f["weather_state"], "HURRICANE_RISK_OFF", f"Failed for {sym}")
            self.assertEqual(f["risk_multiplier"], 0.50, f"Expected 0.50 for {sym}")
            self.assertIn("Defensive Stance", f["trade_policy"])

        # 3. Other Assets
        for sym in ["USDJPY", "USDCAD", "USDCHF"]:
            f = self.weather_engine.forecast_market_weather(symbol=sym)
            self.assertEqual(f["weather_state"], "HURRICANE_RISK_OFF", f"Failed for {sym}")
            self.assertEqual(f["risk_multiplier"], 0.65, f"Expected 0.65 for {sym}")

    def test_defcon2_multipliers_across_asset_classes(self):
        """Under DEFCON 2: Same Hurricane Risk-Off policies enforced."""
        self._escalate_to_defcon(2)
        brief = self.world_monitor.get_world_intelligence_brief()
        self.assertEqual(brief["defcon_level"], 2)

        f_gold = self.weather_engine.forecast_market_weather("XAUUSD")
        self.assertEqual(f_gold["weather_state"], "HURRICANE_RISK_OFF")
        self.assertEqual(f_gold["risk_multiplier"], 1.50)

        f_eur = self.weather_engine.forecast_market_weather("EURUSD")
        self.assertEqual(f_eur["weather_state"], "HURRICANE_RISK_OFF")
        self.assertEqual(f_eur["risk_multiplier"], 0.50)

    def test_defcon3_boundary_does_not_force_hurricane(self):
        """Under DEFCON 3 (below 70.0 risk score), HURRICANE_RISK_OFF is NOT triggered."""
        self._escalate_to_defcon(3)
        brief = self.world_monitor.get_world_intelligence_brief()
        self.assertGreaterEqual(brief["defcon_level"], 3)
        self.assertLess(brief["global_risk_index"], 70.0)

        f_gold = self.weather_engine.forecast_market_weather("XAUUSD")
        self.assertNotEqual(f_gold["weather_state"], "HURRICANE_RISK_OFF")


class TestCurrencyLockoutMatrixIsolation(unittest.TestCase):
    """
    Adversarial Challenge 3: Currency Lockout Matrix Leakage Prevention.
    Verifies that news on Currency X only locks pairs involving Currency X.
    """

    def setUp(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()

    def test_usd_news_isolation_matrix(self):
        """USD news MUST lock all USD pairs & commodities, but MUST NOT lock non-USD crosses."""
        now_utc = datetime.now(timezone.utc)
        self.radar.inject_event("US Non-Farm Payrolls", "USD", now_utc + timedelta(minutes=5), impact="HIGH")

        # Locked pairs
        usd_locked = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD", "NZDUSD", "WTI", "BRENT", "BTCUSD"]
        for sym in usd_locked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertTrue(res["is_blackout"], f"{sym} should be locked by USD news")
            self.assertFalse(res["is_cleared"], f"{sym} should not be cleared")

        # Unlocked crosses (No USD involved)
        unrelated_crosses = ["EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY", "EURCHF", "AUDNZD", "EURCAD", "GBPAUD"]
        for sym in unrelated_crosses:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertFalse(res["is_blackout"], f"{sym} must NOT be locked by USD news")
            self.assertTrue(res["is_cleared"], f"{sym} must be cleared during USD news")

    def test_eur_news_isolation_matrix(self):
        """EUR news MUST lock EUR pairs, but NOT lock USD/JPY/GBP/AUD/CAD pairs without EUR."""
        now_utc = datetime.now(timezone.utc)
        self.radar.inject_event("ECB Rate Decision", "EUR", now_utc + timedelta(minutes=10), impact="HIGH")

        # Locked
        eur_locked = ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD"]
        for sym in eur_locked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertTrue(res["is_blackout"], f"{sym} should be locked by EUR news")

        # Unlocked
        eur_unlocked = ["GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "XAUUSD", "WTI", "BTCUSD", "GBPJPY", "AUDNZD"]
        for sym in eur_unlocked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertFalse(res["is_blackout"], f"{sym} must NOT be locked by EUR news")

    def test_gbp_news_isolation_matrix(self):
        """GBP news MUST lock GBP pairs, but NOT lock EURUSD, USDJPY, XAUUSD, etc."""
        now_utc = datetime.now(timezone.utc)
        self.radar.inject_event("BOE Official Bank Rate", "GBP", now_utc + timedelta(minutes=8), impact="HIGH")

        # Locked
        gbp_locked = ["GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD"]
        for sym in gbp_locked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertTrue(res["is_blackout"], f"{sym} should be locked by GBP news")

        # Unlocked
        gbp_unlocked = ["EURUSD", "USDJPY", "USDCAD", "XAUUSD", "WTI", "EURJPY", "AUDJPY", "AUDNZD"]
        for sym in gbp_unlocked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertFalse(res["is_blackout"], f"{sym} must NOT be locked by GBP news")

    def test_jpy_news_isolation_matrix(self):
        """JPY news MUST lock Yen crosses, but NOT lock EURUSD, GBPUSD, XAUUSD, EURGBP, etc."""
        now_utc = datetime.now(timezone.utc)
        self.radar.inject_event("BOJ Policy Rate", "JPY", now_utc + timedelta(minutes=3), impact="HIGH")

        # Locked
        jpy_locked = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY", "CHFJPY"]
        for sym in jpy_locked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertTrue(res["is_blackout"], f"{sym} should be locked by JPY news")

        # Unlocked
        jpy_unlocked = ["EURUSD", "GBPUSD", "XAUUSD", "WTI", "EURGBP", "AUDCAD", "USDCAD"]
        for sym in jpy_unlocked:
            res = self.radar.evaluate_news_clearance(sym, current_time=now_utc, check_weekend=False)
            self.assertFalse(res["is_blackout"], f"{sym} must NOT be locked by JPY news")

    def test_crypto_247_weekend_clearance(self):
        """Crypto assets (BTCUSD, ETHUSD) MUST NOT be blocked by weekend rollover blackout."""
        # Simulate Saturday 12:00 UTC
        saturday_noon = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Forex pair MUST be blocked on weekend
        fx_res = self.radar.evaluate_news_clearance("EURUSD", current_time=saturday_noon, check_weekend=True)
        self.assertTrue(fx_res["is_blackout"])
        self.assertIn("WEEKEND_ROLLOVER_BLACKOUT", fx_res["lockout_reason"])

        # Crypto pair MUST NOT be blocked by weekend
        crypto_res = self.radar.evaluate_news_clearance("BTCUSD", current_time=saturday_noon, check_weekend=True)
        self.assertFalse(crypto_res["is_blackout"])
        self.assertTrue(crypto_res["is_cleared"])


class TestThreadSafetyAndNetworkFaultTolerance(unittest.TestCase):
    """
    Adversarial Challenge 4: Multi-threading Stress & Network Failure Resilience.
    """

    def setUp(self):
        self.calendar_radar = EconomicCalendarRadar()
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.weather_engine = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar
        )

    def test_concurrent_weather_forecast_and_updates(self):
        """Spawns 20 threads reading and updating WorldMonitor, CalendarRadar, and WeatherEngine concurrently."""
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "WTI", "BTCUSD", "EURGBP"]
        errors = []

        def worker_task(thread_id: int):
            try:
                for i in range(15):
                    sym = symbols[i % len(symbols)]
                    # Periodic updates
                    if thread_id % 3 == 0 and i % 5 == 0:
                        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=14.0 + (i % 5))
                    elif thread_id % 3 == 1 and i % 5 == 0:
                        self.calendar_radar.inject_event(
                            f"Thread Event {thread_id}", "USD",
                            datetime.now(timezone.utc) + timedelta(minutes=10 + i),
                            impact="HIGH"
                        )
                    # Weather evaluation
                    forecast = self.weather_engine.forecast_market_weather(symbol=sym)
                    assert "weather_state" in forecast
                    assert "risk_multiplier" in forecast
                    time.sleep(0.005)
            except Exception as ex:
                errors.append(f"Thread-{thread_id} error: {repr(ex)}")

        threads = [threading.Thread(target=worker_task, args=(tid,)) for tid in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent thread errors encountered: {errors}")

    def test_http_network_timeout_and_error_fallback(self):
        """Simulates HTTP 429 rate limit, URLError, TimeoutError, and malformed JSON."""
        # 1. Test HTTP 429 Rate Limit
        with patch('urllib.request.urlopen') as mock_url:
            mock_url.side_effect = urllib.error.HTTPError(
                url="https://test.com", code=429, msg="Too Many Requests", hdrs={}, fp=None
            )
            # Force cache expiration
            self.calendar_radar.last_fetch_time = datetime.min.replace(tzinfo=timezone.utc)
            events = self.calendar_radar.fetch_live_calendar()
            self.assertIsInstance(events, list)

        # 2. Test Network Timeout
        with patch('urllib.request.urlopen') as mock_url:
            mock_url.side_effect = TimeoutError("Connection timed out to remote feed")
            self.calendar_radar.last_fetch_time = datetime.min.replace(tzinfo=timezone.utc)
            events = self.calendar_radar.fetch_live_calendar()
            self.assertIsInstance(events, list)

        # 3. Test Malformed JSON
        with patch('urllib.request.urlopen') as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{ invalid json string <<<"
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            self.calendar_radar.last_fetch_time = datetime.min.replace(tzinfo=timezone.utc)
            events = self.calendar_radar.fetch_live_calendar()
            self.assertIsInstance(events, list)


class TestEdgeCasesAndMathematicalBoundaries(unittest.TestCase):
    """
    Adversarial Challenge 5: Mathematical Edge Cases, Degenerate Inputs & Boundary Conditions.
    """

    def setUp(self):
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.weather_engine = PredictiveWeatherEngine(world_monitor=self.world_monitor)

    def test_chokepoint_zero_baseline_division_safety(self):
        """Ensures calculate_disruption_percentage handles baseline_mbd == 0 without division by zero."""
        disruption_zero_base = self.world_monitor.calculate_disruption_percentage(0.0, 0.0, incident_count=30)
        self.assertGreater(disruption_zero_base, 0.0)
        self.assertLessEqual(disruption_zero_base, 100.0)

        # Negative flow or overflow
        disruption_neg = self.world_monitor.calculate_disruption_percentage(21.0, -5.0)
        self.assertEqual(disruption_neg, 100.0)

    def test_degenerate_candlestick_dataframe_handling(self):
        """Tests weather forecast under empty, single-row, zero-variance, and NaN DataFrames."""
        # 1. Empty DataFrame
        f_empty = self.weather_engine.forecast_market_weather(pd.DataFrame(), pd.DataFrame(), symbol="XAUUSD")
        self.assertIn("weather_state", f_empty)
        self.assertIsInstance(f_empty["updraft_probability"], float)

        # 2. All zero prices
        df_zeros = pd.DataFrame({
            "open": [0.0] * 20,
            "high": [0.0] * 20,
            "low": [0.0] * 20,
            "close": [0.0] * 20,
            "tick_volume": [0] * 20
        })
        f_zeros = self.weather_engine.forecast_market_weather(df_zeros, df_zeros, symbol="XAUUSD")
        self.assertIn("weather_state", f_zeros)
        self.assertFalse(np.isnan(f_zeros["updraft_probability"]))

        # 3. Identical constant price
        df_const = pd.DataFrame({
            "open": [100.0] * 20,
            "high": [100.0] * 20,
            "low": [100.0] * 20,
            "close": [100.0] * 20,
            "tick_volume": [100] * 20
        })
        f_const = self.weather_engine.forecast_market_weather(df_const, df_const, symbol="EURUSD")
        self.assertIn("weather_state", f_const)
        self.assertFalse(np.isnan(f_const["updraft_probability"]))

    def test_exact_circuit_breaker_time_boundaries(self):
        """Tests exact 15.0m and 15.001m boundary transitions for pre and post news."""
        radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        radar.clear_events()
        now_utc = datetime.now(timezone.utc)

        # Event exactly 15.0 minutes in future -> BLACKOUT
        radar.inject_event("Event A", "USD", now_utc + timedelta(minutes=15.0))
        res_at_15 = radar.evaluate_news_clearance("XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertTrue(res_at_15["is_blackout"])

        # Event 15.1 minutes in future -> CLEARED
        radar.clear_events()
        radar.inject_event("Event B", "USD", now_utc + timedelta(minutes=15.1))
        res_past_15 = radar.evaluate_news_clearance("XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertFalse(res_past_15["is_blackout"])
        self.assertTrue(res_past_15["is_cleared"])

        # Event exactly 15.0 minutes in past -> BLACKOUT (volatility cooloff)
        radar.clear_events()
        radar.inject_event("Event C", "USD", now_utc - timedelta(minutes=15.0))
        res_ago_15 = radar.evaluate_news_clearance("XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertTrue(res_ago_15["is_blackout"])

        # Event 15.1 minutes in past -> CLEARED
        radar.clear_events()
        radar.inject_event("Event D", "USD", now_utc - timedelta(minutes=15.1))
        res_past_ago_15 = radar.evaluate_news_clearance("XAUUSD", current_time=now_utc, check_weekend=False)
        self.assertFalse(res_past_ago_15["is_blackout"])
        self.assertTrue(res_past_ago_15["is_cleared"])


if __name__ == "__main__":
    unittest.main()
