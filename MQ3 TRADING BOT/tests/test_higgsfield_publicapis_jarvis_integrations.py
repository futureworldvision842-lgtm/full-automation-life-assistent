"""
test_higgsfield_publicapis_jarvis_integrations.py — Test Suite for Higgsfield AI, Public-APIs, & Jarvis Integrations.
===================================================================================================================
Covers:
  1. Higgsfield AI Multimodal Vision Engine (credentials, auth headers, candle rejection, SMC confirmation).
  2. Public-APIs Financial & Macro Intelligence Engine (catalog parsing, FX/Gold feeds, search).
  3. Muhammad's Jarvis Master Bridge (Gold advisor skill, World Monitor feed, system control).
  4. TradingBotEngine unified integration.
  5. WhatsApp QR Manager integration for /advisor, /publicapis, /vision.
"""

import os
import unittest
import pandas as pd
import numpy as np

from src.higgsfield_vision_engine import HiggsfieldVisionEngine
from src.public_apis_catalog_engine import PublicAPIsCatalogEngine
from src.jarvis_agent_intel import JarvisAgentIntel
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.bot_engine import TradingBotEngine
from src.whatsapp_qr_manager import WhatsAppQRManager


class TestHiggsfieldVisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = HiggsfieldVisionEngine()

    def test_higgsfield_credentials_and_auth_headers(self):
        """Validates that unconfigured credentials are never invented or emitted."""
        headers = self.engine.get_auth_headers()
        self.assertNotIn("X-API-Key-ID", headers)
        self.assertNotIn("X-API-Key-Secret", headers)
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_candlestick_rejection_audit_bullish(self):
        """Tests visual rejection analysis on a bullish pin bar / sweep candle."""
        df = pd.DataFrame([
            {"open": 2645.0, "high": 2650.0, "low": 2640.0, "close": 2648.0},
            {"open": 2648.0, "high": 2652.0, "low": 2646.0, "close": 2650.0},
            {"open": 2650.0, "high": 2655.0, "low": 2635.0, "close": 2654.0}  # Big lower wick rejection
        ])
        result = self.engine.audit_candlestick_rejection_visually(df, "BUY", symbol="XAUUSD")
        self.assertEqual(result["direction"], "BUY")
        self.assertTrue(result["is_clean_rejection"])
        self.assertGreater(result["visual_conviction"], 60.0)
        self.assertIn("absorption", result["reason"])

    def test_candlestick_rejection_audit_bearish(self):
        """Tests visual rejection analysis on a bearish pin bar."""
        df = pd.DataFrame([
            {"open": 2650.0, "high": 2655.0, "low": 2648.0, "close": 2652.0},
            {"open": 2652.0, "high": 2654.0, "low": 2649.0, "close": 2651.0},
            {"open": 2651.0, "high": 2670.0, "low": 2648.0, "close": 2649.0}  # Big upper wick rejection
        ])
        result = self.engine.audit_candlestick_rejection_visually(df, "SELL", symbol="XAUUSD")
        self.assertEqual(result["direction"], "SELL")
        self.assertTrue(result["is_clean_rejection"])
        self.assertGreater(result["visual_conviction"], 60.0)

    def test_evaluate_smc_visual_confirmation(self):
        """Tests composite visual confirmation integrating SMC dealing ranges."""
        df = pd.DataFrame([
            {"open": 2645.0, "high": 2650.0, "low": 2640.0, "close": 2648.0},
            {"open": 2648.0, "high": 2652.0, "low": 2646.0, "close": 2650.0},
            {"open": 2650.0, "high": 2655.0, "low": 2635.0, "close": 2654.0}
        ])
        smc_intel = {
            "ote": {"in_ote_discount": True},
            "fvgs": [{"type": "BULLISH_FVG", "ce": 2642.0}],
            "order_blocks": [{"type": "BULLISH_OB", "high": 2644.0, "low": 2638.0}]
        }
        res = self.engine.evaluate_smc_visual_confirmation("XAUUSD", "BUY", df, smc_intel)
        self.assertEqual(res["verdict"], "APPROVED")
        self.assertGreaterEqual(res["confidence_pct"], 75.0)

    def test_generate_visual_tearsheet(self):
        """Tests institutional visual tearsheet generation."""
        res = self.engine.generate_visual_tearsheet(
            account_info={"balance": 25960.0, "equity": 26100.0},
            open_positions=[],
            macro_sentiment={"macro_bias": "BULLISH_EXPANSION"}
        )
        self.assertIn("HIGGSFIELD AI VISUAL TEAR-SHEET", res["tearsheet_text"])
        self.assertFalse(res["api_authenticated"])
        self.assertFalse(res["remote_inference_used"])


class TestPublicAPIsCatalogEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PublicAPIsCatalogEngine()

    def test_catalog_indexing(self):
        """Validates that public APIs are indexed into memory."""
        self.assertGreater(self.engine.total_apis_indexed, 0)
        self.assertTrue(len(self.engine.indexed_apis) > 0)

    def test_search_apis(self):
        """Tests keyword search across indexed APIs."""
        results = self.engine.search_apis("finance")
        self.assertIsInstance(results, list)

    def test_fetch_live_fx_rates(self):
        """A feed is observed live or explicitly unavailable, never fabricated."""
        fx = self.engine.fetch_live_fx_rates("USD")
        self.assertIn(fx["data_mode"], {"LIVE_PUBLIC_API", "UNAVAILABLE"})
        if fx["success"]:
            self.assertGreater(len(fx["rates"]), 0)
        else:
            self.assertEqual(fx["rates"], {})

    def test_fetch_live_gold_spot(self):
        """Gold degrades safely when its public endpoint is unavailable."""
        gold = self.engine.fetch_live_gold_spot()
        self.assertEqual(gold["symbol"], "XAUUSD")
        self.assertIn(gold["data_mode"], {"LIVE_PUBLIC_API", "UNAVAILABLE"})
        if gold["success"]:
            self.assertGreater(gold["price"], 2000.0)
        else:
            self.assertIsNone(gold["price"])

    def test_market_intelligence_summary(self):
        """Tests multi-source public market intelligence summary."""
        summary = self.engine.get_market_intelligence_summary()
        self.assertIn(summary["status"], {"ONLINE", "DEGRADED"})
        self.assertIn("gold_spot", summary)
        self.assertIn("forex_crosses", summary)


class TestJarvisAgentIntelBridge(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgentIntel()

    def test_gold_advisor_briefing(self):
        """Tests Gold Advisor skill execution from Muhammad's Jarvis."""
        res = self.agent.get_gold_advisor_briefing()
        self.assertTrue(res["success"])
        self.assertIn("GOLD", res["briefing"])
        self.assertIn("Informational only", res["briefing"])

    def test_world_monitor_headlines(self):
        """Tests World Monitor action execution."""
        headlines = self.agent.get_world_monitor_headlines(category="finance", limit=5)
        self.assertIsInstance(headlines, list)
        self.assertGreater(len(headlines), 0)


class TestUnifiedTradingBotEngineIntegrations(unittest.TestCase):
    def setUp(self):
        self.bot = TradingBotEngine(simulation_mode=True)

    def test_bot_engine_contains_all_master_modules(self):
        """Validates all master modules are active on TradingBotEngine."""
        self.assertIsNotNone(self.bot.higgsfield)
        self.assertIsNotNone(self.bot.public_apis)
        self.assertIsNotNone(self.bot.jarvis_intel)
        self.assertIsNotNone(self.bot.world_monitor_intel)

    def test_whatsapp_qr_manager_new_commands(self):
        """Validates that WhatsApp commands for new modules respond instantaneously."""
        qr = WhatsAppQRManager(bot_engine=self.bot)
        sender = "923468053268@s.whatsapp.net"

        # 1. Gold Advisor
        res_adv = qr.handle_incoming_command("advisor", sender)
        self.assertIn("GOLD", res_adv)

        # 2. Public APIs
        res_apis = qr.handle_incoming_command("publicapis", sender)
        self.assertIn("PUBLIC APIS", res_apis)

        # 3. Vision Tearsheet
        res_vis = qr.handle_incoming_command("vision", sender)
        self.assertIn("HIGGSFIELD", res_vis)


if __name__ == "__main__":
    unittest.main()
