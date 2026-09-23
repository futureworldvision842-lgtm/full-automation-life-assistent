"""
test_global_market_mastery_suite.py — Unit & Integration Test Suite for Sovereign AI Market Mastery.
Audits all 6 new sovereign modules:
  1. InsiderWhaleMechanics
  2. MarketHistoryEncyclopedia
  3. CrossMarketContagionEngine
  4. DeepSelfLearningAgent
  5. SovereignMacroWhaleRadar
  6. Historical50YrRegimeLibrary
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.insider_whale_mechanics import InsiderWhaleMechanics
from src.market_history_encyclopedia import MarketHistoryEncyclopedia
from src.cross_market_synthetic_arb import CrossMarketContagionEngine
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.sovereign_macro_whale_radar import SovereignMacroWhaleRadar
from src.historical_50yr_regime_library import Historical50YrRegimeLibrary


class TestGlobalMarketMasterySuite(unittest.TestCase):

    def test_01_insider_whale_mechanics(self):
        whales = InsiderWhaleMechanics()
        shock = whales.evaluate_political_macro_shock("TARIFF_ESCALATION")
        self.assertIn("gold_tailwind_score", shock)
        self.assertGreater(shock["gold_tailwind_score"], 0.5)

        # Test Dark Pool Anomaly Detection
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='15min')
        df_m15 = pd.DataFrame({
            "open": [4370.0 + i*0.1 for i in range(30)],
            "high": [4372.0 + i*0.1 for i in range(30)],
            "low": [4369.0 + i*0.1 for i in range(30)],
            "close": [4371.0 + i*0.1 for i in range(30)],
            "volume": [100.0]*29 + [1500.0] # Giant block spike
        }, index=dates)
        dp = whales.detect_dark_pool_anomalies(df_m15)
        self.assertIn("dark_pool_detected", dp)
        self.assertTrue(dp["z_score"] > 2.0)

    def test_02_market_history_encyclopedia(self):
        history = MarketHistoryEncyclopedia()
        res = history.match_nearest_historical_analogue(
            current_volatility_z=1.8,
            dxy_momentum=-0.6,
            inflation_factor=1.4,
            safe_haven_demand=2.2
        )
        self.assertIn("nearest_historical_analogue", res)
        self.assertIn("2024-2026", res["nearest_historical_analogue"])
        self.assertGreater(res["similarity_score_pct"], 80.0)

    def test_03_cross_market_contagion(self):
        engine = CrossMarketContagionEngine()
        gsr = engine.compute_gold_silver_ratio(gold_price=4376.50, silver_price=38.40)
        self.assertGreater(gsr["gsr_ratio"], 85.0)
        self.assertEqual(gsr["gsr_regime"], "SILVER_UNDERVALUED_BULLISH_CATCHUP")

        macro = engine.evaluate_cross_asset_macro_matrix()
        self.assertIn("oil_inflation_impact", macro)
        self.assertIn("crypto_liquidity_flow", macro)

    def test_04_deep_self_learning_agent(self):
        agent = DeepSelfLearningAgent(memory_dir="data/test_cognitive_memory")
        agent.update_working_memory("XAUUSD", 4376.50, "LONDON_KILLZONE", 12.0)
        self.assertEqual(agent.working_memory["symbol"], "XAUUSD")

        # Record a winning trade reflection
        rec = agent.record_episodic_experience(
            symbol="XAUUSD",
            direction="BUY",
            pnl=250.0,
            pattern="M15_ORDER_BLOCK_RETEST",
            reason="70.5% OTE Discount sweep",
            regime="BULLISH_EXPANSION"
        )
        self.assertTrue(rec["is_win"])
        self.assertGreater(rec["new_pattern_weight"], 1.35)

        summary = agent.get_cognitive_ai_summary()
        self.assertEqual(summary["cognitive_state"], "AUTONOMOUS_LEARNING_ACTIVE")

    def test_05_sovereign_macro_whale_radar(self):
        radar = SovereignMacroWhaleRadar()
        
        # OFI test
        df_quotes = pd.DataFrame({
            "bid_price": [4375.0, 4375.5, 4376.0],
            "bid_size": [10.0, 15.0, 20.0],
            "ask_price": [4376.0, 4376.5, 4377.0],
            "ask_size": [5.0, 4.0, 3.0]
        })
        ofi = radar.compute_order_flow_imbalance(df_quotes)
        self.assertIn("ofi_signal", ofi)

        # Net Liquidity test
        net_liq = radar.compute_net_liquidity(fed_balance_sheet_b=6800.0, tga_balance_b=750.0, on_rrp_b=250.0)
        self.assertEqual(net_liq["fed_net_liquidity_b"], 5800.0)
        self.assertTrue(net_liq["is_liquidity_expanding"])

    def test_06_historical_50yr_regime_library(self):
        regimes = Historical50YrRegimeLibrary()
        result = regimes.classify_current_regime(
            realized_vol_annual=0.18,
            current_drawdown_pct=0.03,
            dxy_20d_ret=0.10,
            spread_stress_score=0.30,
            gold_20d_ret=0.75
        )
        self.assertEqual(result["closest_crisis_regime"], "2022_2026_SOVEREIGN_DEBT_DOMINANCE")
        self.assertEqual(result["action_protocol"], "NORMAL_SOVEREIGN_EXECUTION")
        self.assertEqual(result["risk_scalar"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
