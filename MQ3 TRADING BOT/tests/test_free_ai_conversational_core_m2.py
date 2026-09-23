"""
tests/test_free_ai_conversational_core_m2.py
Tests for Features 14, 15, 16: Multilingual Roman Urdu & English NLP Core, 3-Pillar What-If Matrix & Funding Pips 25k Proposals.
"""

import pytest
from src.free_ai_intelligence_core import FreeAIIntelligenceCore


class TestFreeAIConversationalCoreSuite:

    @pytest.fixture
    def core(self):
        return FreeAIIntelligenceCore()

    def test_roman_urdu_intent_matrix(self, core):
        urdu_matrix = [
            ("kya market buy hai?", "MARKET_BIAS_QUERY", "XAUUSD"),
            ("gold ka kya scene hai?", "MARKET_BIAS_QUERY", "XAUUSD"),
            ("aaj kitna loss afford kar sakte hain?", "RISK_DRAWDOWN_QUERY", "XAUUSD"),
            ("drawdown kitna bacha hai?", "RISK_DRAWDOWN_QUERY", "XAUUSD"),
            ("agar gold 2600 chala jaye to kya hoga?", "WHAT_IF_SCENARIO_QUERY", "XAUUSD"),
            ("agar market crash kar jaye 3%?", "WHAT_IF_SCENARIO_QUERY", "XAUUSD"),
            ("gold buy ka proposal do", "TRADE_PROPOSAL_REQUEST", "XAUUSD"),
            ("kitna lot size lu xauusd par?", "TRADE_PROPOSAL_REQUEST", "XAUUSD"),
            ("xauusd buy 0.10 lot", "TRADE_EXECUTION_COMMAND", "XAUUSD"),
            ("tamam trades band kar do", "TRADE_MANAGEMENT_COMMAND", "XAUUSD"),
            ("sl entry par move karo", "TRADE_MANAGEMENT_COMMAND", "XAUUSD"),
            ("salam jarvis", "GREETING_OR_STATUS_QUERY", "XAUUSD")
        ]
        for query, exp_intent, exp_sym in urdu_matrix:
            res = core.parse_intent(query)
            assert res["intent"] == exp_intent, f"Failed for Urdu query: {query}"
            assert res["symbol"] == exp_sym

    def test_english_intent_matrix(self, core):
        eng_matrix = [
            ("what is the bias on EURUSD?", "MARKET_BIAS_QUERY", "EURUSD"),
            ("show market analysis for btc", "MARKET_BIAS_QUERY", "BTCUSD"),
            ("what is my VaR today?", "RISK_DRAWDOWN_QUERY", "XAUUSD"),
            ("check daily drawdown remaining", "RISK_DRAWDOWN_QUERY", "XAUUSD"),
            ("what if BTC drops 5%?", "WHAT_IF_SCENARIO_QUERY", "BTCUSD"),
            ("stress test gold buy position", "WHAT_IF_SCENARIO_QUERY", "XAUUSD"),
            ("give me a trade proposal for GBPUSD", "TRADE_PROPOSAL_REQUEST", "GBPUSD"),
            ("blueprint setup for 25k challenge", "TRADE_PROPOSAL_REQUEST", "XAUUSD"),
            ("buy 0.05 lot EURUSD", "TRADE_EXECUTION_COMMAND", "EURUSD"),
            ("close all positions immediately", "TRADE_MANAGEMENT_COMMAND", "XAUUSD"),
            ("hello jarvis status report", "GREETING_OR_STATUS_QUERY", "XAUUSD")
        ]
        for query, exp_intent, exp_sym in eng_matrix:
            res = core.parse_intent(query)
            assert res["intent"] == exp_intent, f"Failed for English query: {query}"
            assert res["symbol"] == exp_sym

    def test_entity_resolution_aliases(self, core):
        assert core.parse_intent("sona khareedo")["symbol"] == "XAUUSD"
        assert core.parse_intent("bitcoin analysis")["symbol"] == "BTCUSD"
        assert core.parse_intent("cable buy proposal")["symbol"] == "GBPUSD"
        assert core.parse_intent("fiber short signal")["symbol"] == "EURUSD"
        assert core.parse_intent("dollar yen risk")["symbol"] == "USDJPY"
        assert core.parse_intent("chandi what if matrix")["symbol"] == "XAGUSD"

    def test_three_pillar_what_if_math_and_var(self, core):
        res = core.generate_what_if_matrix(symbol="XAUUSD", current_price=2650.0, direction="BUY")
        p = res["pillars"]

        # Base Case
        b = p["pillar_1_base_case"]
        assert b["reward_to_risk"] == 1.8
        assert b["projected_gain_usd"] > 0

        # Bull Case
        bull = p["pillar_2_bull_case"]
        assert bull["reward_to_risk"] == 3.5
        assert bull["win_probability"] == 0.80

        # Bear Case
        s = p["pillar_3_stress_case"]
        assert s["var_99_usd"] > 0
        assert s["cvar_99_usd"] > s["var_99_usd"]  # CVaR (Expected Shortfall) is strictly greater than VaR

    def test_funding_pips_25k_lot_sizing_calibration(self, core):
        # 1. Gold (pip_val = $10 / 0.10, SL = 60 pips -> SL dist = $6.0)
        # Risk = $25000 * 0.0075 = $187.50
        # Lot = 187.50 / (60 * 10) = 0.31 lots
        gold_prop = core.generate_funding_pips_25k_proposal(symbol="XAUUSD", direction="BUY", current_price=2650.0)
        assert gold_prop["lot_size"] == 0.31
        assert gold_prop["risk_dollar"] == 187.50
        assert gold_prop["reward_to_risk"] >= 2.0

        # 2. EURUSD (pip_val = $10 / 0.0001, SL = 20 pips)
        # Lot = 187.50 / (20 * 10) = 0.94 lots
        eur_prop = core.generate_funding_pips_25k_proposal(symbol="EURUSD", direction="BUY", current_price=1.0850)
        assert eur_prop["lot_size"] == 0.94

    def test_whatsapp_and_web_cockpit_card_formatting(self, core):
        prop = core.generate_funding_pips_25k_proposal(symbol="XAUUSD", direction="BUY")
        text = prop["formatted_proposal"]
        assert "👑 *FUNDING PIPS 25K TRADE PROPOSAL" in text
        assert "$25,000 Evaluation" in text
        assert "Optimal Entry" in text
        assert "Stop Loss (SL)" in text
        assert "Roman Urdu Advice / Mashwara" in text
