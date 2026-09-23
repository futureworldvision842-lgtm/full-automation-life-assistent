"""
tests/test_r2_ai_scalping_advisory.py — Comprehensive Test Suite for Requirement R2:
Hyper-Intelligent AI Trade Advisor & What-If Scenario Scalper (Urdu & English).
===================================================================================

Verifies:
  1. Natural Language Constraint Parser (arbitrary balance $100-$100k, timeframes 5m/15m/1h/scalp, venues Binance/Hyperliquid/FundingPips).
  2. Dynamic Multi-Asset Scanner & Best Crypto Discovery (momentum, volatility, CVD, ranking matrix).
  3. Live Order Flow & CVD Ingestion (Lee-Ready CVD delta absorption, 50% Equilibrium, 70.5% OTE).
  4. Deep Macro & Shark Forensics (Hormuz, Red Sea/Bab el-Mandeb, Suez, CII 82.5, Fed Net Liquidity, Asian Judas swings, retail traps).
  5. Scenario A/B What-If Conditional Matrix (Bullish Expansion vs Bearish Defense/Reload).
  6. Actionable Execution Targets (Entry, SL with exact dollar risk for $100 balance, TP1-3, R:R calculation, leverage recommendations).
  7. Dual-Language Institutional Synthesis (Muhammad's Sovereign Institutional Mashwara in Roman Urdu + English matrix).
  8. Interface Contract Compliance & Sub-500ms Latency SLA.
  9. WhatsApp QR Manager 2-way Conversational AI Dispatch.
"""

import time
import pytest
import unittest
from src.free_ai_intelligence_core import FreeAIIntelligenceCore
from src.whatsapp_qr_manager import WhatsAppQRManager


class TestR2AIScalpingAdvisory(unittest.TestCase):
    def setUp(self):
        self.ai = FreeAIIntelligenceCore()
        self.qr = WhatsAppQRManager()
        self.sender = "923468053268@s.whatsapp.net"

    # ── 1. Natural Language Constraint Parser ──────────────────────────────────

    def test_nlp_constraint_parser_crypto_100_dollar_5m(self):
        """Tests parsing arbitrary $100 balance and 5m timeframe on Binance."""
        q = "I have $100 in Binance, check and give me best position for 5-minute trade for now on any best crypto"
        constraints = self.ai.parse_query_constraints(q)
        self.assertEqual(constraints["balance"], 100.0)
        self.assertEqual(constraints["timeframe"], "5m")
        self.assertEqual(constraints["venue"], "Binance")
        self.assertTrue(constraints["is_best_crypto"])

    def test_nlp_constraint_parser_roman_urdu_scalp(self):
        """Tests Roman Urdu query with $100 balance and scalp request."""
        q = "Mere pas $100 hain binance pe, 5 minute scalp trade batao best crypto pe"
        constraints = self.ai.parse_query_constraints(q)
        self.assertEqual(constraints["balance"], 100.0)
        self.assertEqual(constraints["timeframe"], "5m")
        self.assertEqual(constraints["venue"], "Binance")
        self.assertTrue(constraints["is_urdu"])
        self.assertTrue(constraints["is_best_crypto"])

    def test_nlp_constraint_parser_hyperliquid_500_dollar(self):
        """Tests parsing $500 on Hyperliquid DEX with 15m timeframe."""
        q = "What is the best 15m trade on Hyperliquid with $500 balance for SOL?"
        constraints = self.ai.parse_query_constraints(q)
        self.assertEqual(constraints["balance"], 500.0)
        self.assertEqual(constraints["timeframe"], "15m")
        self.assertEqual(constraints["venue"], "Hyperliquid")
        self.assertEqual(constraints["detected_symbol"], "SOLUSD")

    def test_nlp_constraint_parser_prop_firm_25k(self):
        """Tests parsing $25,000 Funding Pips challenge account."""
        q = "Give me 1h trade plan for $25000 balance on FundingPips for Gold"
        constraints = self.ai.parse_query_constraints(q)
        self.assertEqual(constraints["balance"], 25000.0)
        self.assertEqual(constraints["timeframe"], "1h")
        self.assertEqual(constraints["venue"], "FundingPips")
        self.assertEqual(constraints["detected_symbol"], "XAUUSD")

    # ── 2. Dynamic Multi-Asset Scanner & Best Crypto Discovery ─────────────────

    def test_best_crypto_discovery_and_ranking(self):
        """Tests dynamic multi-asset evaluation and ranking across BTC, ETH, SOL."""
        ranking = self.ai.rank_and_select_best_crypto(timeframe="5m")
        self.assertIn(ranking["best_symbol"], ["BTCUSD", "ETHUSD", "SOLUSD"])
        self.assertGreater(ranking["best_price"], 0.0)
        self.assertEqual(len(ranking["ranked_candidates"]), 3)
        self.assertIn("MULTI-ASSET CRYPTO RANKING MATRIX", ranking["ranking_summary_text"])
        # Check scores are properly ordered descending
        scores = [c["total_score"] for c in ranking["ranked_candidates"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    # ── 3. Live Order Flow & CVD Ingestion ─────────────────────────────────────

    def test_live_order_flow_and_cvd_ingestion(self):
        """Tests live 5m market structure, Lee-Ready CVD, 50% Eq, and 70.5% OTE."""
        of = self.ai.get_live_order_flow_and_cvd("BTCUSD", timeframe="5m")
        self.assertEqual(of["symbol"], "BTCUSD")
        self.assertGreater(of["live_price"], 0.0)
        self.assertGreater(of["equilibrium_50"], 0.0)
        self.assertGreater(of["ote_705_sweet_spot"], 0.0)
        self.assertIn("buyer_ratio", of)
        self.assertGreaterEqual(of["buyer_ratio"], 0.50)
        self.assertIn("absorption_desc", of)
        self.assertIn("funding_rate_8h", of)

    # ── 4. Deep Macro & Shark Forensics ────────────────────────────────────────

    def test_deep_macro_and_shark_forensics(self):
        """Tests ingestion of maritime chokepoints, CII index, Fed Net Liquidity, and shark traps."""
        macro = self.ai.get_macro_and_shark_forensics("XAUUSD")
        self.assertIn("Strait of Hormuz", macro["chokepoints_summary"])
        self.assertIn("Red Sea", macro["chokepoints_summary"])
        self.assertGreaterEqual(macro["cii_score"], 70.0)
        self.assertIn("CRITICAL", macro["cii_status"])
        self.assertGreaterEqual(macro["fed_liq_b"], 5000.0)
        self.assertIn("Asian Judas Swing", macro["shark_forensics"])

    # ── 5. Scenario A/B What-If Matrix & Actionable Targets ────────────────────

    def test_scenario_ab_what_if_matrix_and_actionable_targets(self):
        """Tests Scenario A/B conditional branches and balance-calibrated dollar risk."""
        targets = self.ai.build_scenario_ab_and_targets(
            symbol="BTCUSD",
            live_price=96500.0,
            balance=100.0,
            timeframe="5m",
            venue="Binance",
            direction="BUY"
        )
        self.assertEqual(targets["symbol"], "BTCUSD")
        self.assertEqual(targets["entry_price"], 96500.0)
        self.assertLess(targets["sl_price"], 96500.0)
        self.assertGreater(targets["tp1_price"], 96500.0)
        self.assertGreater(targets["tp2_price"], targets["tp1_price"])
        self.assertGreater(targets["tp3_price"], targets["tp2_price"])

        # Check calibrated dollar risk: for $100 balance, risk must be <= $2.00
        self.assertLessEqual(targets["max_dollar_loss"], 2.00)
        self.assertGreaterEqual(targets["max_dollar_loss"], 1.00)

        # Check R:R ratios
        self.assertGreaterEqual(targets["rr_tp1"], 1.5)
        self.assertGreaterEqual(targets["rr_tp2"], 2.5)
        self.assertGreaterEqual(targets["rr_tp3"], 3.5)

        # Check Scenario A and Scenario B conditional branches
        sc_a = targets["scenario_a"]
        sc_b = targets["scenario_b"]
        self.assertIn("IF", sc_a["trigger"])
        self.assertIn("THEN", sc_a["action"])
        self.assertIn("IF", sc_b["trigger"])
        self.assertIn("THEN", sc_b["action"])

    # ── 6. Dual-Language Institutional Synthesis ───────────────────────────────

    def test_dual_language_institutional_synthesis_content(self):
        """Tests complete formatted output containing Roman Urdu Mashwara and English matrix."""
        res = self.ai.consult_market("I have $100 in Binance, check and give me best position for 5-minute trade for now on any best crypto")
        text = res["advisory_response"]

        # Check sections presence
        self.assertIn("JARVIS AI INSTITUTIONAL TRADE ADVISOR", text)
        self.assertIn("TARGET ASSET:", text)
        self.assertIn("ACCOUNT BALANCE:", text)
        self.assertIn("$100.00", text)
        self.assertIn("CALIBRATED RISK:", text)
        self.assertIn("1. LIVE MARKET TELEMETRY", text)
        self.assertIn("2. DEEP MACRO & GEOPOLITICAL SHARK RADAR", text)
        self.assertIn("3. MUHAMMAD'S SOVEREIGN INSTITUTIONAL MASHWARA (ROMAN URDU):", text)
        self.assertIn("MASHWARA:", text)
        self.assertIn("Big Sharks Game", text)
        self.assertIn("Sovereign Hidayat:", text)
        self.assertIn("4. SCENARIO A/B WHAT-IF CONDITIONAL MATRIX:", text)
        self.assertIn("SCENARIO A", text)
        self.assertIn("SCENARIO B", text)
        self.assertIn("5. ACTIONABLE EXECUTION TARGETS & SIZING", text)
        self.assertIn("Optimal Entry:", text)
        self.assertIn("Structural Stop Loss (SL):", text)
        self.assertIn("Take Profit 1 (TP1):", text)
        self.assertIn("Take Profit 2 (TP2):", text)
        self.assertIn("Take Profit 3 (TP3):", text)
        self.assertIn("Direct WhatsApp Command:", text)

    # ── 7. Interface Contract Verification ─────────────────────────────────────

    def test_consult_market_interface_contract(self):
        """Verifies dictionary returned meets PROJECT.md interface contract."""
        res = self.ai.consult_market("Mere pas $100 hain Binance pe 5m scalp trade batao")

        # Required fields from interface contract
        self.assertIn("advisory_response", res)
        self.assertIn("asset", res)
        self.assertIn("entry", res)
        self.assertIn("sl", res)
        self.assertIn("tp1", res)
        self.assertIn("tp2", res)
        self.assertIn("tp3", res)
        self.assertIn("rr", res)
        self.assertIn("scenario_a", res)
        self.assertIn("scenario_b", res)
        self.assertIn("macro_summary", res)

        # Value type validations
        self.assertIsInstance(res["advisory_response"], str)
        self.assertIsInstance(res["asset"], str)
        self.assertIsInstance(res["entry"], (int, float))
        self.assertIsInstance(res["sl"], (int, float))
        self.assertIsInstance(res["tp1"], (int, float))
        self.assertIsInstance(res["tp2"], (int, float))
        self.assertIsInstance(res["tp3"], (int, float))
        self.assertIsInstance(res["rr"], (int, float))
        self.assertIsInstance(res["scenario_a"], str)
        self.assertIsInstance(res["scenario_b"], str)
        self.assertIsInstance(res["macro_summary"], str)

    # ── 8. Performance Latency SLA Benchmark ───────────────────────────────────

    def test_consult_market_sub_500ms_sla(self):
        """Verifies end-to-end consultation executes in under 500ms."""
        query = "I have $100 in Binance, check and give me best position for 5-minute trade for now on any best crypto"
        # First call warms cache if needed
        self.ai.consult_market(query)
        start = time.perf_counter()
        res = self.ai.consult_market(query)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(res["advisory_response"])
        self.assertLess(elapsed_ms, 500.0, f"Expected <500ms execution, took {elapsed_ms:.2f}ms")

    # ── 9. WhatsApp Conversational Dispatch Integration ────────────────────────

    def test_whatsapp_qr_manager_scalping_consultation(self):
        """Tests that WhatsApp QR Manager routes natural queries to the AI Advisor."""
        query = "I have $100 in Binance, check and give me best position for 5-minute trade for now on any best crypto"
        reply = self.qr.handle_incoming_command(query, self.sender)

        self.assertIn("JARVIS AI INSTITUTIONAL TRADE ADVISOR", reply)
        self.assertIn("ACCOUNT BALANCE:", reply)
        self.assertIn("$100.00", reply)
        self.assertIn("MUHAMMAD'S SOVEREIGN INSTITUTIONAL MASHWARA", reply)
        self.assertIn("SCENARIO A", reply)
        self.assertIn("SCENARIO B", reply)


if __name__ == "__main__":
    unittest.main()
