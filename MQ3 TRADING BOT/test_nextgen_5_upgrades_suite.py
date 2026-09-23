"""
test_nextgen_5_upgrades_suite.py — Comprehensive Test Harness for 5 Next-Gen Quantitative Upgrades:
  1. MultiTerminalCopier (Simultaneous fleet sizing & replication)
  2. NeuralNewsSentimentStream (NLP breaking headline scoring & shock detection)
  3. OrderBookDOMEngine (Level-2 market depth & iceberg order detection)
  4. BrokerBBookDefenseShield (Midnight rollover spread traps & latency armor)
  5. WeekendCryptoArbitrageEngine (24/7 weekend crypto mode & SMC OTE scan)
"""

import unittest
from datetime import datetime, timezone
from src.multi_terminal_copier import MultiTerminalCopier
from src.neural_news_sentiment_stream import NeuralNewsSentimentStream
from src.order_book_dom_engine import OrderBookDOMEngine
from src.broker_bbook_defense_shield import BrokerBBookDefenseShield
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine


class TestNextGen5UpgradesSuite(unittest.TestCase):

    def setUp(self):
        self.copier = MultiTerminalCopier()
        self.sentiment = NeuralNewsSentimentStream()
        self.dom = OrderBookDOMEngine()
        self.shield = BrokerBBookDefenseShield()
        self.weekend_engine = WeekendCryptoArbitrageEngine()

    def test_01_multi_terminal_copier_sizing_and_dispatch(self):
        """Tests simultaneous lot sizing and master-to-slave replication."""
        master_trade = {
            "ticket": "TEST_MASTER_101",
            "symbol": "XAUUSD",
            "signal_type": "BUY",
            "entry_price": 4376.50,
            "sl_price": 4364.50,
            "tp_price": 4396.60,
            "sl_pips": 12.0,
            "volume": 1.04
        }
        res = self.copier.replicate_order(master_trade)
        self.assertIn("slave_executions", res)
        self.assertEqual(len(res["slave_executions"]), 4)

        # Verify lot sizes
        slaves = res["slave_executions"]
        self.assertEqual(slaves["100k_master"]["allocated_lot"], 4.17)
        self.assertEqual(slaves["50k_funded"]["allocated_lot"], 2.08)
        self.assertEqual(slaves["25k_active"]["allocated_lot"], 1.08)
        self.assertEqual(slaves["5k_scalp"]["allocated_lot"], 0.21)
        self.assertGreater(res["total_fleet_volume"], 7.0)

    def test_02_neural_news_sentiment_stream_scoring(self):
        """Tests NLP sentiment scoring for breaking geopolitical headlines."""
        bullish_headline = "Central banks accelerate physical Gold reserve purchases amid currency diversification"
        score_data = self.sentiment.score_headline(bullish_headline)
        self.assertGreater(score_data["score"], 0.30)
        self.assertIn("BULLISH", score_data["category"])

        bearish_headline = "Fed delivers unexpected hawkish rate hike as dollar surges"
        bear_data = self.sentiment.score_headline(bearish_headline)
        self.assertLess(bear_data["score"], -0.30)
        self.assertIn("BEARISH", bear_data["category"])

        feed_data = self.sentiment.analyze_news_feed()
        self.assertIn("score", feed_data)
        self.assertIn("category", feed_data)

    def test_03_order_book_dom_iceberg_walls(self):
        """Tests Level-2 DOM resting liquidity depth and iceberg detection."""
        depth = self.dom.get_market_depth("XAUUSD")
        self.assertIn("total_bid_volume", depth)
        self.assertIn("total_ask_volume", depth)
        self.assertIn("imbalance_ratio", depth)
        self.assertTrue(depth["has_iceberg_demand"] or depth["has_iceberg_supply"] or depth["imbalance_ratio"] > 0)
        self.assertIn(depth["verdict"], ["STRONG_INSTITUTIONAL_BUY_ABSORPTION", "STRONG_INSTITUTIONAL_SELL_WALL", "NEUTRAL"])

    def test_04_broker_bbook_defense_shield(self):
        """Tests midnight rollover spread trap detection and execution safety."""
        # Normal spread test
        safe_audit = self.shield.audit_trade_safety("XAUUSD", spread_pips=18.0, ping_ms=35.0)
        self.assertIn("safe_to_execute", safe_audit)
        self.assertIn("recommended_order_type", safe_audit)

        # Toxic spread spike test
        toxic_audit = self.shield.audit_trade_safety("XAUUSD", spread_pips=65.0, ping_ms=35.0)
        self.assertFalse(toxic_audit["safe_to_execute"])
        self.assertEqual(toxic_audit["recommended_order_type"], "LIMIT_BRACKET_ONLY")

        # Midnight rollover window test (21:30 UTC)
        rollover_time = datetime(2026, 8, 15, 21, 30, tzinfo=timezone.utc)
        self.assertTrue(self.shield.is_rollover_window(rollover_time))

        # Normal session time test (14:00 UTC)
        normal_time = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
        self.assertFalse(self.shield.is_rollover_window(normal_time))

    def test_05_weekend_crypto_arbitrage_engine(self):
        """Tests weekend session detection and crypto SMC OTE setups."""
        # Saturday test
        saturday = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(self.weekend_engine.is_traditional_market_closed(saturday))

        # Tuesday test
        tuesday = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(self.weekend_engine.is_traditional_market_closed(tuesday))

        # Scan weekend setups
        setups = self.weekend_engine.scan_weekend_crypto_setups()
        self.assertIsInstance(setups, list)
        self.assertGreater(len(setups), 0)
        btc_setup = setups[0]
        self.assertEqual(btc_setup["symbol"], "BTCUSD")
        self.assertEqual(btc_setup["signal_type"], "BUY")
        self.assertEqual(btc_setup["confluence_score"], 4.8)


if __name__ == "__main__":
    unittest.main()
