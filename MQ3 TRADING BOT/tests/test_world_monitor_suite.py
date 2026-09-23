"""
test_world_monitor_suite.py — Master Test Suite for Requirement R1 (Milestone M1).
===================================================================================
Covers all 7 core features & Interface Contracts:
  1. Strategic Maritime Chokepoints (EIA baselines, dynamic disruption %, incident tracking).
  2. Asset Impact Multipliers (XAUUSD, WTI/Brent, DXY, EURUSD, BTCUSD).
  3. 4-Pillar Country Instability Index (CII: Unrest, Conflict, Security, Information & DEFCON 1-5).
  4. Polymarket Geopolitical Odds Ingestion (implied probability, volume, risk level, target asset).
  5. Economic Calendar Feeds & Currency-Specific Lockout Matrix.
  6. 15-Minute Pre/Post News Circuit Breaker State Machine & NewsFilter synchronization.
  7. Predictive Weather Engine Fusion (CYCLONE, HURRICANE, THUNDERSTORM, SUNNY, STORMY, FOGGY).
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.world_monitor_intelligence_engine import (
    WorldMonitorIntelligenceEngine,
    get_world_monitor_brief
)
from src.economic_calendar_radar import EconomicCalendarRadar
from src.news_filter import NewsFilter
from src.predictive_weather_engine import PredictiveWeatherEngine
from src.market_satellite_radar import MarketSatelliteRadar


class TestWorldMonitorIntelligenceEngine(unittest.TestCase):
    """
    Unit & Integration Tests for WorldMonitorIntelligenceEngine (Features 1, 2, 3, 4).
    """

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 1: STRATEGIC MARITIME CHOKEPOINTS
    # ══════════════════════════════════════════════════════════════════════════

    def test_01_canonical_chokepoints_presence_and_baselines(self):
        """Validates all 5 strategic chokepoints with exact EIA flow baselines."""
        brief = self.engine.get_world_intelligence_brief()
        chokepoints = brief["chokepoints"]

        required_keys = ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "taiwan_strait"]
        for key in required_keys:
            self.assertIn(key, chokepoints, f"Missing chokepoint: {key}")

        # Baseline checks
        self.assertEqual(chokepoints["hormuz_strait"]["baseline_mbd"], 21.0)
        self.assertEqual(chokepoints["bab_el_mandeb"]["baseline_mbd"], 6.2)
        self.assertEqual(chokepoints["suez"]["baseline_mbd"], 7.6)
        self.assertEqual(chokepoints["malacca_strait"]["baseline_mbd"], 17.2)
        self.assertEqual(chokepoints["taiwan_strait"]["baseline_mbd"], 0.0)

        # Uppercase alias compatibility
        self.assertIn("STRAIT_OF_HORMUZ", chokepoints)
        self.assertIn("BAB_EL_MANDEB_RED_SEA", chokepoints)
        self.assertIn("SUEZ_CANAL", chokepoints)
        self.assertIn("MALACCA_STRAIT", chokepoints)
        self.assertIn("TAIWAN_STRAIT", chokepoints)

    def test_02_disruption_percentage_mathematics(self):
        """Tests dynamic disruption formula: (1.0 - (current / baseline)) * 100%."""
        # 1. 50% flow cut in Hormuz (21.0 -> 10.5 mbd)
        disruption_50 = self.engine.calculate_disruption_percentage(21.0, 10.5)
        self.assertEqual(disruption_50, 50.0)

        # 2. Total blockage (0.0 mbd)
        disruption_total = self.engine.calculate_disruption_percentage(6.2, 0.0)
        self.assertEqual(disruption_total, 100.0)

        # 3. Normal flow (full capacity)
        disruption_zero = self.engine.calculate_disruption_percentage(17.2, 17.2)
        self.assertEqual(disruption_zero, 0.0)

        # 4. Overflow capacity (25 mbd through 21 mbd channel)
        disruption_over = self.engine.calculate_disruption_percentage(21.0, 25.0)
        self.assertEqual(disruption_over, 0.0)

    def test_03_chokepoint_flow_updates_and_anomaly_triggers(self):
        """Tests real-time flow update and automatic anomaly detection."""
        # Update Bab el-Mandeb flow to near zero
        updated = self.engine.update_chokepoint_flow("bab_el_mandeb", current_mbd=0.5, incident_count=45)
        self.assertAlmostEqual(updated["current_mbd"], 0.5)
        self.assertGreater(updated["disruption_pct"], 90.0)
        self.assertTrue(updated["anomaly_signal"])
        self.assertEqual(updated["risk_level"], "CRITICAL_WARZONE")

        # Recover flow in Malacca
        recovered = self.engine.update_chokepoint_flow("malacca_strait", current_mbd=17.2, incident_count=0)
        self.assertEqual(recovered["disruption_pct"], 0.0)
        self.assertFalse(recovered["anomaly_signal"])
        self.assertEqual(recovered["risk_level"], "STABLE_SURVEILLANCE")

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 2: ASSET IMPACT MULTIPLIERS
    # ══════════════════════════════════════════════════════════════════════════

    def test_04_asset_impact_multipliers_across_symbols(self):
        """Validates quantitative macro multipliers for Gold, Oil, Euro, Yen, and Bitcoin."""
        bias_gold = self.engine.get_geopolitical_market_bias("XAUUSD")
        bias_oil = self.engine.get_geopolitical_market_bias("WTI")
        bias_eur = self.engine.get_geopolitical_market_bias("EURUSD")
        bias_jpy = self.engine.get_geopolitical_market_bias("USDJPY")
        bias_btc = self.engine.get_geopolitical_market_bias("BTCUSD")

        # Gold & Oil: Safe-Haven and supply shocks
        self.assertIn(bias_gold["bias"], ["STRONG_BUY", "BUY"])
        self.assertGreaterEqual(bias_gold["macro_multiplier"], 1.35)
        self.assertGreater(bias_gold["confluence_boost"], 0.0)
        self.assertTrue(len(bias_gold["key_drivers"]) >= 2)

        self.assertIn(bias_oil["bias"], ["STRONG_BUY", "BUY"])
        self.assertGreaterEqual(bias_oil["macro_multiplier"], 1.30)

        # Euro: Supply chain drag and freight inflation
        self.assertEqual(bias_eur["bias"], "SELL")
        self.assertLessEqual(bias_eur["macro_multiplier"], 0.85)
        self.assertLess(bias_eur["confluence_boost"], 0.0)

        # Bitcoin: Sovereign hedge / liquid alternative
        self.assertGreaterEqual(bias_btc["macro_multiplier"], 1.15)

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 3: 4-PILLAR COUNTRY INSTABILITY INDEX (CII) & DEFCON
    # ══════════════════════════════════════════════════════════════════════════

    def test_05_4_pillar_cii_calculation_and_weights(self):
        """Tests exact 4-pillar weighting: 0.20*unrest + 0.40*conflict + 0.25*security + 0.15*info."""
        components = {
            "unrest": 80.0,
            "conflict": 90.0,
            "security": 70.0,
            "information": 60.0
        }
        # Expected: 0.20*80 + 0.40*90 + 0.25*70 + 0.15*60 = 16 + 36 + 17.5 + 9 = 78.5
        score = self.engine.calculate_country_instability_score(components)
        self.assertEqual(score, 78.5)

    def test_06_defcon_level_classification(self):
        """Tests DEFCON 1 through 5 categorization."""
        self.assertEqual(self.engine.get_defcon_level(90.0), 1)  # Critical Warzone
        self.assertEqual(self.engine.get_defcon_level(75.0), 2)  # High Tension
        self.assertEqual(self.engine.get_defcon_level(60.0), 3)  # Elevated
        self.assertEqual(self.engine.get_defcon_level(35.0), 4)  # Normal Watch
        self.assertEqual(self.engine.get_defcon_level(15.0), 5)  # Low Stable

    def test_07_country_instability_update_dynamic(self):
        """Tests dynamic update of regional CII scores and global DEFCON re-calibration."""
        region = self.engine.update_country_instability(
            "MIDDLE_EAST_REGION",
            components={"unrest": 95.0, "conflict": 100.0, "security": 95.0, "information": 90.0}
        )
        # Expected: 0.20*95 + 0.40*100 + 0.25*95 + 0.15*90 = 19 + 40 + 23.75 + 13.5 = 96.25 -> 96.2
        self.assertEqual(region["score"], 96.2)
        self.assertEqual(region["level"], "CRITICAL")

        brief = self.engine.get_world_intelligence_brief()
        self.assertIn(brief["defcon_level"], [1, 2, 3])

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 4: POLYMARKET GEOPOLITICAL ODDS INGESTION
    # ══════════════════════════════════════════════════════════════════════════

    def test_08_polymarket_odds_ingestion_and_filtering(self):
        """Tests ingestion and filtering of live Polymarket prediction market streams."""
        raw_candidates = [
            {
                "event": "China-Taiwan Military Confrontation by 2027",
                "implied_probability_pct": 22.5,
                "volume_usd": 5400000.0,
                "trend": "RISING"
            },
            {
                "event": "Middle East Major Regional Escalation in 2026",
                "implied_probability_pct": 74.0,
                "volume_usd": 28500000.0,
                "trend": "CRITICAL"
            },
            {
                "event": "Random illiquid meme prediction market",
                "implied_probability_pct": 5.0,
                "volume_usd": 500.0,  # Below $20k volume threshold
                "trend": "FLAT"
            }
        ]
        parsed = self.engine.ingest_polymarket_odds(raw_candidates)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["market_shock_level"], "EXTREME")
        self.assertEqual(parsed[0]["impact_asset"], "XAUUSD")
        self.assertEqual(parsed[1]["market_shock_level"], "SEVERE")
        self.assertEqual(parsed[1]["impact_asset"], "WTI")

    def test_09_whatsapp_world_monitor_card_generation(self):
        """Validates formatting and structure of institutional WhatsApp intelligence card."""
        card = self.engine.generate_whatsapp_world_monitor_card()
        self.assertIsInstance(card, str)
        self.assertIn("WORLD MONITOR — GLOBAL SITUATIONAL INTELLIGENCE", card)
        self.assertIn("5 STRATEGIC MARITIME CHOKEPOINTS", card)
        self.assertIn("Strait of Hormuz", card)
        self.assertIn("Bab el-Mandeb", card)
        self.assertIn("Taiwan Strait", card)
        self.assertIn("4-PILLAR COUNTRY INSTABILITY INDEX", card)
        self.assertIn("POLYMARKET GEOPOLITICAL ODDS", card)
        self.assertIn("MARKET SHOCK MULTIPLIERS", card)


class TestEconomicCalendarAndCircuitBreakers(unittest.TestCase):
    """
    Unit & Integration Tests for EconomicCalendarRadar and NewsFilter (Features 5 & 6).
    """

    def setUp(self):
        self.radar = EconomicCalendarRadar(blackout_minutes_before=15, blackout_minutes_after=15)
        self.radar.clear_events()
        self.news_filter = NewsFilter()
        self.news_filter.radar.clear_events()

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 5: CURRENCY-SPECIFIC LOCKOUT MATRIX
    # ══════════════════════════════════════════════════════════════════════════

    def test_10_currency_extraction_across_assets(self):
        """Validates currency extraction from various Forex, Commodity, and Crypto symbols."""
        self.assertEqual(self.radar.extract_symbol_currencies("XAUUSD"), {"USD"})
        self.assertEqual(self.radar.extract_symbol_currencies("EURUSD"), {"EUR", "USD"})
        self.assertEqual(self.radar.extract_symbol_currencies("GBPJPY"), {"GBP", "JPY"})
        self.assertEqual(self.radar.extract_symbol_currencies("USDCAD"), {"USD", "CAD"})
        self.assertEqual(self.radar.extract_symbol_currencies("WTI"), {"USD"})
        self.assertEqual(self.radar.extract_symbol_currencies("BTCUSD"), {"USD"})

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 6: 15-MINUTE PRE/POST NEWS CIRCUIT BREAKER STATE MACHINE
    # ══════════════════════════════════════════════════════════════════════════

    def test_11_pre_news_blackout_state(self):
        """Verifies trade blocking 8 minutes before high-impact FOMC announcement."""
        now_utc = datetime.now(timezone.utc)
        # Event in 8 minutes (Inside 15-min pre-news window)
        fomc_time = now_utc + timedelta(minutes=8)
        self.radar.inject_event("FOMC Rate Decision", "USD", fomc_time, impact="HIGH")

        clearance_gold = self.radar.evaluate_news_clearance("XAUUSD")
        self.assertFalse(clearance_gold["is_cleared"])
        self.assertTrue(clearance_gold["is_blackout"])
        self.assertIn("PRE_NEWS_BLACKOUT", clearance_gold["lockout_reason"])
        self.assertIsNotNone(clearance_gold["active_event"])
        self.assertEqual(clearance_gold["active_event"]["title"], "FOMC Rate Decision")

        # EURUSD is also locked by USD event
        clearance_eur = self.radar.evaluate_news_clearance("EURUSD")
        self.assertFalse(clearance_eur["is_cleared"])
        self.assertTrue(clearance_eur["is_blackout"])

    def test_12_post_news_blackout_state(self):
        """Verifies trade blocking 6 minutes after high-impact NFP release (volatility cooloff)."""
        now_utc = datetime.now(timezone.utc)
        # Event occurred 6 minutes ago (Inside 15-min post-news window)
        nfp_time = now_utc - timedelta(minutes=6)
        self.radar.inject_event("Non-Farm Payrolls (NFP)", "USD", nfp_time, impact="HIGH")

        clearance = self.radar.evaluate_news_clearance("XAUUSD")
        self.assertFalse(clearance["is_cleared"])
        self.assertTrue(clearance["is_blackout"])
        self.assertIn("POST_NEWS_BLACKOUT", clearance["lockout_reason"])
        self.assertIn("Volatility cooloff active", clearance["lockout_reason"])

    def test_13_outside_blackout_window_clearance(self):
        """Verifies normal clearance when event is > 15 mins away or > 15 mins past."""
        now_utc = datetime.now(timezone.utc)
        # Event in 45 minutes (Outside 15-min window)
        future_time = now_utc + timedelta(minutes=45)
        self.radar.inject_event("US CPI Report", "USD", future_time, impact="HIGH")

        clearance = self.radar.evaluate_news_clearance("XAUUSD")
        # Ensure it's cleared (assuming not a weekend rollover)
        if now_utc.weekday() not in [5, 6] and not (now_utc.weekday() == 4 and now_utc.hour >= 20):
            self.assertTrue(clearance["is_cleared"])
            self.assertFalse(clearance["is_blackout"])
            self.assertEqual(clearance["upcoming_events_count"], 1)

    def test_14_unrelated_currency_isolation(self):
        """Verifies EUR event locks EURJPY but DOES NOT lock GBPUSD or AUDCAD."""
        now_utc = datetime.now(timezone.utc)
        ecb_time = now_utc + timedelta(minutes=5)
        self.radar.inject_event("ECB Interest Rate Decision", "EUR", ecb_time, impact="HIGH")

        # EURJPY should be locked
        clearance_eurjpy = self.radar.evaluate_news_clearance("EURJPY")
        self.assertFalse(clearance_eurjpy["is_cleared"])
        self.assertTrue(clearance_eurjpy["is_blackout"])

        # GBPUSD should NOT be locked by EUR news (unless weekend)
        if now_utc.weekday() not in [5, 6] and not (now_utc.weekday() == 4 and now_utc.hour >= 20):
            clearance_gbpusd = self.radar.evaluate_news_clearance("GBPUSD")
            self.assertTrue(clearance_gbpusd["is_cleared"])
            self.assertFalse(clearance_gbpusd["is_blackout"])

    def test_15_news_filter_synchronization(self):
        """Validates that NewsFilter.is_news_active synchronizes with EconomicCalendarRadar."""
        now_utc = datetime.now(timezone.utc)
        cpi_time = now_utc + timedelta(minutes=7)
        self.news_filter.radar.inject_event("US Core CPI", "USD", cpi_time, impact="HIGH")

        is_active, msg = self.news_filter.is_news_active("XAUUSD")
        self.assertTrue(is_active)
        self.assertIn("PRE_NEWS_BLACKOUT", msg)


class TestPredictiveWeatherEngineFusion(unittest.TestCase):
    """
    Unit & Integration Tests for PredictiveWeatherEngine (Feature 7 & Interface Contract 3).
    """

    def setUp(self):
        self.world_monitor = WorldMonitorIntelligenceEngine()
        self.calendar_radar = EconomicCalendarRadar()
        self.calendar_radar.clear_events()
        self.weather_engine = PredictiveWeatherEngine(
            world_monitor=self.world_monitor,
            calendar_radar=self.calendar_radar
        )

    # ══════════════════════════════════════════════════════════════════════════
    # FEATURE 7: ATMOSPHERIC REGIMES & INTERFACE CONTRACT 3
    # ══════════════════════════════════════════════════════════════════════════

    def test_16_cyclone_news_lockout_regime(self):
        """Tests that active news blackout triggers CYCLONE_NEWS_LOCKOUT regime with 0.0x risk."""
        now_utc = datetime.now(timezone.utc)
        self.calendar_radar.inject_event("FOMC Statement", "USD", now_utc + timedelta(minutes=5), impact="HIGH")

        forecast = self.weather_engine.forecast_market_weather("XAUUSD")
        self.assertEqual(forecast["weather_state"], "CYCLONE_NEWS_LOCKOUT")
        self.assertEqual(forecast["risk_multiplier"], 0.0)
        self.assertEqual(forecast["trade_policy"], "Trading Strictly Halted / Entries Blocked")
        self.assertIn("News Circuit Breaker", forecast["advisory"])

    def test_17_hurricane_risk_off_regime_on_defcon_escalation(self):
        """Tests that DEFCON 1/2 triggers HURRICANE_RISK_OFF with 1.50x safe-haven boost on Gold."""
        # Escalate Middle East & Eastern Europe to extreme warzone
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION",
            components={"unrest": 99.0, "conflict": 100.0, "security": 100.0, "information": 95.0}
        )
        self.world_monitor.update_country_instability(
            "EASTERN_EUROPE",
            components={"unrest": 95.0, "conflict": 100.0, "security": 98.0, "information": 90.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=2.0, incident_count=80)

        brief = self.world_monitor.get_world_intelligence_brief()
        self.assertLessEqual(brief["defcon_level"], 2)

        forecast_gold = self.weather_engine.forecast_market_weather("XAUUSD")
        self.assertEqual(forecast_gold["weather_state"], "HURRICANE_RISK_OFF")
        self.assertEqual(forecast_gold["risk_multiplier"], 1.50)
        self.assertEqual(forecast_gold["trade_policy"], "Execute Safe-Haven BUY (Gold/Oil), Block Pro-cyclical FX")

        forecast_eur = self.weather_engine.forecast_market_weather("EURUSD")
        self.assertEqual(forecast_eur["weather_state"], "HURRICANE_RISK_OFF")
        self.assertEqual(forecast_eur["risk_multiplier"], 0.50)

    def test_18_sunny_bullish_updraft_regime(self):
        """Tests SUNNY_BULLISH_UPDRAFT classification on strong bullish candlestick momentum."""
        # Create a series of bullish candles
        closes = [2600.0 + (i * 3.0) for i in range(30)]
        df_m15 = pd.DataFrame({
            "open": [c - 1.5 for c in closes],
            "high": [c + 2.0 for c in closes],
            "low": [c - 2.0 for c in closes],
            "close": closes,
            "tick_volume": [200] * 30
        })
        df_h1 = df_m15.copy()

        # Reset world monitor to normal watch (DEFCON 4/5)
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 20.0, "conflict": 15.0, "security": 20.0, "information": 20.0}
        )
        self.world_monitor.update_country_instability(
            "EASTERN_EUROPE", components={"unrest": 15.0, "conflict": 10.0, "security": 15.0, "information": 15.0}
        )
        self.world_monitor.update_country_instability(
            "EAST_ASIA_PACIFIC", components={"unrest": 10.0, "conflict": 10.0, "security": 10.0, "information": 10.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=21.0, incident_count=0)
        self.world_monitor.update_chokepoint_flow("bab_el_mandeb", current_mbd=6.2, incident_count=0)

        forecast = self.weather_engine.forecast_market_weather(df_h1, df_m15, symbol="XAUUSD")
        self.assertEqual(forecast["weather_state"], "SUNNY_BULLISH_UPDRAFT")
        self.assertGreaterEqual(forecast["updraft_probability"], 65.0)
        self.assertEqual(forecast["risk_multiplier"], 1.30)
        self.assertEqual(forecast["trade_policy"], "Full Size Long Entries Permitted")

    def test_19_stormy_bearish_downdraft_regime(self):
        """Tests STORMY_BEARISH_DOWNDRAFT classification on strong downward momentum."""
        closes = [2600.0 - (i * 3.0) for i in range(30)]
        df_m15 = pd.DataFrame({
            "open": [c + 1.5 for c in closes],
            "high": [c + 2.0 for c in closes],
            "low": [c - 2.0 for c in closes],
            "close": closes,
            "tick_volume": [200] * 30
        })
        df_h1 = df_m15.copy()

        # Reset world monitor to normal watch
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 20.0, "conflict": 15.0, "security": 20.0, "information": 20.0}
        )
        self.world_monitor.update_country_instability(
            "EASTERN_EUROPE", components={"unrest": 15.0, "conflict": 10.0, "security": 15.0, "information": 15.0}
        )
        self.world_monitor.update_country_instability(
            "EAST_ASIA_PACIFIC", components={"unrest": 10.0, "conflict": 10.0, "security": 10.0, "information": 10.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=21.0, incident_count=0)
        self.world_monitor.update_chokepoint_flow("bab_el_mandeb", current_mbd=6.2, incident_count=0)

        forecast = self.weather_engine.forecast_market_weather(df_h1, df_m15, symbol="EURUSD")
        self.assertEqual(forecast["weather_state"], "STORMY_BEARISH_DOWNDRAFT")
        self.assertGreaterEqual(forecast["downdraft_probability"], 65.0)
        self.assertEqual(forecast["risk_multiplier"], 1.30)
        self.assertEqual(forecast["trade_policy"], "Full Size Short Entries Permitted")

    def test_20_foggy_liquidity_trap_regime(self):
        """Tests FOGGY_LIQUIDITY_TRAP classification on flat/choppy range-bound market."""
        # Flat range
        closes = [2600.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(30)]
        df_m15 = pd.DataFrame({
            "open": [2600.0] * 30,
            "high": [2600.5] * 30,
            "low": [2599.5] * 30,
            "close": closes,
            "tick_volume": [50] * 30
        })
        df_h1 = df_m15.copy()

        # Reset world monitor to normal watch
        self.world_monitor.update_country_instability(
            "MIDDLE_EAST_REGION", components={"unrest": 20.0, "conflict": 15.0, "security": 20.0, "information": 20.0}
        )
        self.world_monitor.update_country_instability(
            "EASTERN_EUROPE", components={"unrest": 15.0, "conflict": 10.0, "security": 15.0, "information": 15.0}
        )
        self.world_monitor.update_country_instability(
            "EAST_ASIA_PACIFIC", components={"unrest": 10.0, "conflict": 10.0, "security": 10.0, "information": 10.0}
        )
        self.world_monitor.update_chokepoint_flow("hormuz_strait", current_mbd=21.0, incident_count=0)
        self.world_monitor.update_chokepoint_flow("bab_el_mandeb", current_mbd=6.2, incident_count=0)

        forecast = self.weather_engine.forecast_market_weather(df_h1, df_m15, symbol="USDJPY")
        self.assertEqual(forecast["weather_state"], "FOGGY_LIQUIDITY_TRAP")
        self.assertEqual(forecast["risk_multiplier"], 0.50)
        self.assertEqual(forecast["trade_policy"], "Range Scalping Only / Tight SL at Asian Highs/Lows")

    def test_21_interface_contract_3_compliance(self):
        """Verifies exact compliance with PROJECT.md Interface Contract 3 dictionary keys."""
        forecast = self.weather_engine.forecast_market_weather("XAUUSD")

        # Required fields in contract 3
        self.assertIn("symbol", forecast)
        self.assertIn("weather_state", forecast)
        self.assertIn("updraft_probability", forecast)
        self.assertIn("downdraft_probability", forecast)
        self.assertIn("barometric_pressure_hpa", forecast)
        self.assertIn("risk_multiplier", forecast)
        self.assertIn("trade_policy", forecast)
        self.assertIn("advisory", forecast)
        self.assertIsInstance(forecast["updraft_probability"], float)
        self.assertIsInstance(forecast["downdraft_probability"], float)
        self.assertIsInstance(forecast["barometric_pressure_hpa"], float)
        self.assertIsInstance(forecast["risk_multiplier"], float)


if __name__ == "__main__":
    unittest.main()
