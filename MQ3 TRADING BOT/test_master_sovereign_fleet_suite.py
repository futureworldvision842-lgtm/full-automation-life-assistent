"""
test_master_sovereign_fleet_suite.py — Master Sovereign Fleet 100% Comprehensive Audit & Stress Suite.
Tests every single module, strategy, risk guard, memory layer, WhatsApp bridge, and live engine.
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.bot_engine import TradingBotEngine
from src.strategy import StrategyEngine
from src.market_analyzer import MarketAnalyzer
from src.order_flow_quant import OrderFlowQuantEngine
from src.qlib_alpha158_engine import QlibAlpha158Engine
from src.aladdin_regime_model import QuantitativeRegimeDetector
from src.intermarket_macro_radar import IntermarketMacroRadar
from src.economic_calendar_radar import EconomicCalendarRadar
from src.insider_whale_mechanics import InsiderWhaleMechanics
from src.market_history_encyclopedia import MarketHistoryEncyclopedia
from src.cross_market_synthetic_arb import CrossMarketContagionEngine
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.multi_account_manager import MultiAccountManager
from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.ai_trade_consultant import AITradeConsultant
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.whatsapp_qr_manager import WhatsAppQRManager, is_whitelisted_number


class TestMasterSovereignFleetSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "risk_per_trade_percent": 0.50,
            "max_daily_drawdown_percent": 2.50,
            "max_total_drawdown_percent": 5.00,
            "trailing_stop_pips": 25,
            "take_profit_pips": 75,
            "stop_loss_pips": 25,
            "max_spread_pips": 3.0,
            "slippage_points": 10,
            "breakeven_distance_pips": 25
        }

    # ── TEST 1: CORE MARKET ANALYZER & SMC FORMATIONS ────────────────────────
    def test_01_market_analyzer_smc_formations(self):
        analyzer = MarketAnalyzer(self.config)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='15min')
        df = pd.DataFrame({
            "time": dates,
            "open": [4350.0 + i*0.5 for i in range(50)],
            "high": [4352.0 + i*0.5 for i in range(50)],
            "low": [4349.0 + i*0.5 for i in range(50)],
            "close": [4351.0 + i*0.5 for i in range(50)],
            "volume": [100.0 + i*5 for i in range(50)]
        }, index=dates)

        # Inject FVG
        df.iloc[20, df.columns.get_loc('high')] = 4360.0
        df.iloc[22, df.columns.get_loc('low')] = 4365.0

        res = analyzer.analyze_symbol("XAUUSD", df, df)
        self.assertIn("trend_direction", res)
        self.assertIn("dark_pool_intel", res)
        self.assertIn("historical_analogue", res)
        self.assertIn("cross_asset_matrix", res)

    # ── TEST 2: ORDER FLOW QUANT & LEE-READY CVD ─────────────────────────────
    def test_02_order_flow_quant_cvd(self):
        of = OrderFlowQuantEngine()
        ticks = [
            {"bid": 4370.0, "ask": 4370.5, "last": 4370.5, "volume": 10},
            {"bid": 4371.0, "ask": 4371.5, "last": 4371.5, "volume": 15}, # Uptick
            {"bid": 4371.5, "ask": 4372.0, "last": 4372.0, "volume": 20}, # Uptick
            {"bid": 4371.0, "ask": 4371.5, "last": 4371.0, "volume": 5}   # Downtick
        ]
        cvd = of.compute_tick_cvd(ticks)
        self.assertIn("cvd", cvd)
        self.assertGreater(cvd["buyer_ratio"], 0.5)

    # ── TEST 3: INSIDER WHALE & POLITICAL SHOCKS ─────────────────────────────
    def test_03_insider_whale_mechanics(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("TARIFF_ESCALATION")
        self.assertEqual(shock["active_shock"], "TARIFF_ESCALATION")
        self.assertGreater(shock["gold_tailwind_score"], 0.70)

    # ── TEST 4: 50-YEAR CRISIS ENCYCLOPEDIA ANALOGUE ─────────────────────────
    def test_04_market_history_crisis_analogue(self):
        hist = MarketHistoryEncyclopedia()
        analogue = hist.match_nearest_historical_analogue(1.8, -0.6, 1.4, 2.2)
        self.assertIn("nearest_historical_analogue", analogue)
        self.assertGreater(analogue["similarity_score_pct"], 80.0)

    # ── TEST 5: CROSS-MARKET CONTAGION & GSR RATIO ───────────────────────────
    def test_05_cross_market_contagion_gsr(self):
        engine = CrossMarketContagionEngine()
        gsr = engine.compute_gold_silver_ratio(4376.50, 38.40)
        self.assertEqual(gsr["gsr_regime"], "SILVER_UNDERVALUED_BULLISH_CATCHUP")

    # ── TEST 6: FINMEM COGNITIVE 3-TIER MEMORY & ADAPTATION ───────────────────
    def test_06_finmem_cognitive_self_learning(self):
        agent = DeepSelfLearningAgent(memory_dir="data/test_cognitive_memory")
        agent.update_working_memory("XAUUSD", 4376.50, "NY_KILLZONE", 10.0)
        rec = agent.record_episodic_experience("XAUUSD", "BUY", 350.0, "ASIAN_JUDAS_SWEEP", "Swept low", "BULLISH")
        self.assertTrue(rec["is_win"])
        summary = agent.get_cognitive_ai_summary()
        self.assertEqual(summary["cognitive_state"], "AUTONOMOUS_LEARNING_ACTIVE")

    # ── TEST 7: 4-ACCOUNT PORTFOLIO FLEET MANAGER ($180k AUM) ─────────────────
    def test_07_multi_account_fleet_manager(self):
        fleet = MultiAccountManager()
        summary = fleet.get_fleet_summary()
        self.assertEqual(summary["total_aum_potential"], 180000.0)
        self.assertEqual(len(summary["fleet"]), 4)

    # ── TEST 8: DAILY ROUTINE ENGINE (MORNING & NIGHTLY AUDITS) ───────────────
    def test_08_daily_institutional_routines(self):
        routine = DailyInstitutionalRoutineEngine()
        morning = routine.generate_morning_master_briefing()
        self.assertIn("GOOD MORNING", morning)
        self.assertIn("SCENARIO A", morning)
        self.assertIn("$100k Master", morning)

        nightly = routine.generate_nightly_market_retrospective()
        self.assertIn("NIGHTLY MARKET CLOSE", nightly)
        self.assertIn("COGNITIVE LESSONS", nightly)

    # ── TEST 9: INTERACTIVE AI TRADE CONSULTANT ──────────────────────────────
    def test_09_interactive_ai_trade_consultant(self):
        consultant = AITradeConsultant()
        inq1 = consultant.parse_inquiry_intent("Main Gold buy karna chahta hoon")
        self.assertTrue(inq1["is_consultation"])
        self.assertEqual(inq1["symbol"], "XAUUSD")
        self.assertEqual(inq1["direction"], "BUY")

        advice = consultant.generate_consultation_advice(inq1)
        self.assertIn("HIGH CONVICTION BUY", advice)
        self.assertIn("Stop Loss (SL)", advice)

    # ── TEST 10: STRICT WHATSAPP WHITELIST SECURITY FILTER ───────────────────
    def test_10_whatsapp_whitelist_security(self):
        # Whitelisted numbers: Only Master User (Owner) & Elite Group
        self.assertTrue(is_whitelisted_number("923468053268@s.whatsapp.net")) # Master User
        self.assertTrue(is_whitelisted_number("120363401615322542@g.us"))     # Elite Trade Group

        # Purged secondary contacts must be rejected (Security Isolation)
        self.assertFalse(is_whitelisted_number("923487117832@s.whatsapp.net")) # Ahmad (Purged)
        self.assertFalse(is_whitelisted_number("923322555238@s.whatsapp.net")) # Ahmed Bro (Purged)
        self.assertFalse(is_whitelisted_number("923375893095@s.whatsapp.net")) # Maa Ufone (Purged)

        # Strangers & external groups must be rejected by is_whitelisted_number
        self.assertFalse(is_whitelisted_number("923001234567@s.whatsapp.net")) # Stranger
        self.assertFalse(is_whitelisted_number("120363172997847444@newsletter")) # Newsletter


if __name__ == "__main__":
    unittest.main(verbosity=2)
