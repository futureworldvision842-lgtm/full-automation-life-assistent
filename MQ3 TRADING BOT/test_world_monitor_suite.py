"""
test_world_monitor_suite.py — Comprehensive Test Suite for World Monitor Intelligence Integration.
Verifies:
  1. WorldMonitorIntelligenceEngine global threat scoring and chokepoint data.
  2. Multi-asset geopolitical market bias vectors (XAUUSD, WTI, EURUSD, BTCUSD).
  3. WhatsApp World Monitor card generation.
  4. WhatsApp QR manager command routing for 'world' and 'worldmonitor'.
"""

import unittest
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.whatsapp_qr_manager import WhatsAppQRManager


class TestWorldMonitorSuite(unittest.TestCase):

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()
        self.qr_mgr = WhatsAppQRManager()

    def test_01_world_intelligence_brief(self):
        """Verifies situational brief, threat levels, and chokepoint mapping."""
        brief = self.engine.get_world_intelligence_brief()
        self.assertIn("global_threat_level", brief)
        self.assertIn("global_composite_risk_index", brief)
        self.assertIn("chokepoints", brief)
        self.assertIn("STRAIT_OF_HORMUZ", brief["chokepoints"])
        self.assertIn("BAB_EL_MANDEB_RED_SEA", brief["chokepoints"])
        self.assertGreater(brief["global_composite_risk_index"], 50.0)

    def test_02_geopolitical_market_bias(self):
        """Verifies multi-asset geopolitical transmission vectors."""
        # Gold Test
        gold_bias = self.engine.evaluate_geopolitical_market_bias("XAUUSD")
        self.assertEqual(gold_bias["geopolitical_bias"], "STRONG_BULLISH")
        self.assertGreater(gold_bias["confluence_boost"], 0.0)
        self.assertGreater(gold_bias["strategy_weight_multiplier"], 1.0)

        # WTI Crude Oil Test
        wti_bias = self.engine.evaluate_geopolitical_market_bias("WTI")
        self.assertEqual(wti_bias["geopolitical_bias"], "STRONG_BULLISH")

        # EURUSD Test
        eur_bias = self.engine.evaluate_geopolitical_market_bias("EURUSD")
        self.assertEqual(eur_bias["geopolitical_bias"], "BEARISH_PRESSURE")

    def test_03_whatsapp_card_formatting(self):
        """Verifies WhatsApp intelligence card format."""
        card = self.engine.generate_whatsapp_world_monitor_card()
        self.assertIn("WORLD MONITOR", card)
        self.assertIn("Global Threat Level", card)
        self.assertIn("Strait of Hormuz", card)
        self.assertIn("Gold (XAUUSD)", card)

    def test_04_whatsapp_command_routing(self):
        """Verifies 'world' and 'worldmonitor' commands return formatted card."""
        reply1 = self.qr_mgr.handle_incoming_command("world", "120363401615322542@g.us")
        self.assertIn("WORLD MONITOR", reply1)

        reply2 = self.qr_mgr.handle_incoming_command("worldmonitor", "120363401615322542@g.us")
        self.assertIn("WORLD MONITOR", reply2)

        reply3 = self.qr_mgr.handle_incoming_command("geopolitics", "120363401615322542@g.us")
        self.assertIn("WORLD MONITOR", reply3)




if __name__ == "__main__":
    unittest.main()
