"""
tests/test_consensus_chamber.py
================================
Comprehensive verification for TauricResearch/TradingAgents Consensus Chamber.
Verifies multi-agent debate, non-negotiable Risk Officer veto, and execution planning.
"""

import pytest
from trading.consensus_chamber.agents import (
    BullishAdvocate,
    BearishChallenger,
    RiskOfficer,
    ExecutionSpecialist,
)
from trading.consensus_chamber.chamber import ConsensusChamber, get_consensus_chamber

@pytest.fixture
def valid_gold_proposal():
    return {
        "proposal_id": "PROP-XAU-001",
        "symbol": "XAUUSD",
        "action": "BUY",
        "account_id": "40000294403",
        "account_balance": 100000.0,
        "price": 2650.0,
        "stop_loss": 2640.0,    # Risk = 10 pts
        "take_profit": 2680.0,  # Reward = 30 pts -> R:R = 3.0 >= 2.5
        "risk_pct": 0.50,       # 0.50% <= 0.75%
        "risk_usd": 500.0,      # $500 <= $750
        "rr_ratio": 3.0,
    }

@pytest.fixture
def bullish_market_context():
    return {
        "indicators": {
            "rsi": 54.0,
            "trend": "BULLISH",
            "cvd_delta": 450.0,
            "ote_discount": True,
            "resistance_proximity_pct": 3.5,
        },
        "spread_bps": 1.1,
        "minutes_to_high_impact_news": 90.0,
    }


class TestDebateAgents:
    def test_bullish_advocate_favorable(self, valid_gold_proposal, bullish_market_context):
        advocate = BullishAdvocate()
        res = advocate.evaluate(valid_gold_proposal, bullish_market_context)
        assert res["agent"] == "BullishAdvocate"
        assert res["confidence"] >= 70.0
        assert res["recommendation"] == "BUY"
        assert len(res["key_points"]) >= 3

    def test_bullish_advocate_rebuttal(self, valid_gold_proposal, bullish_market_context):
        advocate = BullishAdvocate()
        opp_args = [{"agent": "BearishChallenger", "thesis": "Strong overhead resistance ahead"}]
        rebut = advocate.rebut(valid_gold_proposal, bullish_market_context, opp_args)
        assert "resistance" in rebut["rebuttal"].lower() or "supply" in rebut["rebuttal"].lower()
        assert rebut["adjusted_stance"] == "MAINTAIN_BULLISH"

    def test_bearish_challenger_detection(self, valid_gold_proposal):
        challenger = BearishChallenger()
        context = {
            "indicators": {
                "rsi": 78.0, # overbought
                "resistance_proximity_pct": 0.3, # very close
                "dxy_trend": "BULLISH",
                "liquidity_sweep_pending": True,
            }
        }
        res = challenger.evaluate(valid_gold_proposal, context)
        assert res["agent"] == "BearishChallenger"
        assert res["confidence"] >= 70.0
        assert res["recommendation"] == "SELL"

    def test_execution_specialist_breakeven_calculation(self, valid_gold_proposal, bullish_market_context):
        specialist = ExecutionSpecialist()
        res = specialist.evaluate(valid_gold_proposal, bullish_market_context)
        assert res["agent"] == "ExecutionSpecialist"
        plan = res["execution_plan"]
        # Entry = 2650, SL = 2640 -> Risk = 10 -> BE trigger = 2660.0 (+1.0R)
        assert plan["breakeven_trigger_price"] == 2660.0
        assert plan["stop_loss"] == 2640.0
        assert plan["partial_tp1_price"] == 2665.0  # 1.5R partial
        assert plan["trailing_stop_armed"] is True


class TestRiskOfficerVetoPower:
    def test_risk_officer_approves_compliant_trade(self, valid_gold_proposal, bullish_market_context):
        officer = RiskOfficer(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)
        res = officer.evaluate(valid_gold_proposal, bullish_market_context)
        assert res["approved"] is True
        assert res["veto"] is False
        assert res["veto_reason"] is None
        assert res["risk_metrics"]["risk_pct"] == 0.50
        assert res["risk_metrics"]["risk_usd"] == 500.0

    def test_veto_on_risk_pct_exceeded(self, valid_gold_proposal, bullish_market_context):
        officer = RiskOfficer(max_risk_pct=0.75, max_risk_usd=750.0)
        invalid_prop = dict(valid_gold_proposal)
        invalid_prop["risk_pct"] = 0.85 # > 0.75%
        res = officer.evaluate(invalid_prop, bullish_market_context)
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_RISK_PCT_EXCEEDED"

    def test_veto_on_risk_usd_exceeded(self, valid_gold_proposal, bullish_market_context):
        officer = RiskOfficer(max_risk_pct=0.75, max_risk_usd=750.0)
        invalid_prop = dict(valid_gold_proposal)
        invalid_prop["risk_pct"] = 0.60
        invalid_prop["risk_usd"] = 820.0 # > $750
        res = officer.evaluate(invalid_prop, bullish_market_context)
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_RISK_USD_EXCEEDED"

    def test_veto_on_insufficient_rr(self, valid_gold_proposal, bullish_market_context):
        officer = RiskOfficer(min_rr=2.5)
        invalid_prop = dict(valid_gold_proposal)
        invalid_prop["take_profit"] = 2665.0 # reward = 15, risk = 10 -> R:R = 1.5 < 2.5
        invalid_prop["rr_ratio"] = 1.5
        res = officer.evaluate(invalid_prop, bullish_market_context)
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_INSUFFICIENT_RR"

    def test_veto_on_news_blackout(self, valid_gold_proposal):
        officer = RiskOfficer()
        context = {"minutes_to_high_impact_news": 8.0} # within 15m blackout
        res = officer.evaluate(valid_gold_proposal, context)
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_NEWS_BLACKOUT"

    def test_veto_on_inverted_geometry(self, valid_gold_proposal, bullish_market_context):
        officer = RiskOfficer()
        invalid_prop = dict(valid_gold_proposal)
        invalid_prop["action"] = "BUY"
        invalid_prop["stop_loss"] = 2660.0 # SL above entry on BUY!
        res = officer.evaluate(invalid_prop, bullish_market_context)
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_BUY_SL_ABOVE_ENTRY"


class TestConsensusChamber:
    def test_chamber_approves_high_conviction_trade(self, valid_gold_proposal, bullish_market_context):
        chamber = get_consensus_chamber()
        result = chamber.debate(valid_gold_proposal, bullish_market_context)
        
        assert result.approved is True
        assert result.status == "APPROVED_HIGH_CONVICTION"
        assert result.consensus_score >= 70.0
        assert result.execution_plan is not None
        assert result.execution_plan["breakeven_trigger_price"] == 2660.0
        assert len(result.debate_transcript) >= 4
        assert "Master Muhammad Qureshi" not in result.veto_reason if result.veto_reason else True
        assert "Tayyar hai" in result.summary_urdu_en

        # Test dictionary conversion
        d = result.to_dict()
        assert d["approved"] is True
        assert d["symbol"] == "XAUUSD"

    def test_chamber_strictly_vetoes_when_risk_fails(self, valid_gold_proposal, bullish_market_context):
        chamber = get_consensus_chamber()
        excessive_risk_prop = dict(valid_gold_proposal)
        excessive_risk_prop["risk_pct"] = 1.50 # 1.50% violates 0.75% ceiling!
        
        result = chamber.debate(excessive_risk_prop, bullish_market_context)
        assert result.approved is False
        assert result.status == "VETOED_BY_RISK_OFFICER"
        assert result.consensus_score == 0.0
        assert result.execution_plan is None
        assert "VETO_RISK_PCT_EXCEEDED" in result.veto_reason or "exceeds non-negotiable ceiling" in result.veto_reason
        assert "capital safety" in result.summary_urdu_en.lower()

    def test_chamber_rejects_low_confluence_when_bear_dominant(self, valid_gold_proposal):
        chamber = get_consensus_chamber()
        # Market context is strongly hostile to longs
        bear_context = {
            "indicators": {
                "rsi": 82.0,
                "trend": "BEARISH",
                "cvd_delta": -500.0,
                "ote_discount": False,
                "resistance_proximity_pct": 0.2,
                "liquidity_sweep_pending": True,
            },
            "spread_bps": 1.2,
            "minutes_to_high_impact_news": 120.0,
        }
        result = chamber.debate(valid_gold_proposal, bear_context)
        assert result.approved is False
        assert result.status == "REJECTED_LOW_CONFLUENCE"
        assert result.consensus_score < 70.0
        assert "WAIT" in result.summary_urdu_en

    def test_chamber_approves_valid_sell_short(self):
        chamber = get_consensus_chamber()
        short_proposal = {
            "proposal_id": "PROP-BTC-SHORT-01",
            "symbol": "BTCUSDT",
            "action": "SELL",
            "account_id": "40000294403",
            "account_balance": 100000.0,
            "price": 68000.0,
            "stop_loss": 68500.0,   # Risk = 500
            "take_profit": 66500.0, # Reward = 1500 -> R:R = 3.0 >= 2.5
            "risk_pct": 0.50,
            "risk_usd": 500.0,
            "rr_ratio": 3.0,
        }
        bear_context = {
            "indicators": {
                "rsi": 28.0,
                "trend": "BEARISH",
                "resistance_proximity_pct": 0.4,
                "liquidity_sweep_pending": True,
                "dxy_trend": "BULLISH",
            },
            "spread_bps": 0.8,
            "minutes_to_high_impact_news": 45.0,
        }
        result = chamber.debate(short_proposal, bear_context)
        assert result.approved is True
        assert result.status == "APPROVED_HIGH_CONVICTION"
        assert result.action == "SELL"
        assert result.execution_plan["breakeven_trigger_price"] == 67500.0  # 68000 - 500

    def test_risk_officer_handles_zero_or_negative_inputs(self):
        officer = RiskOfficer()
        bad_prop = {
            "symbol": "SOLUSDT",
            "action": "BUY",
            "price": 0.0,
            "stop_loss": -10.0,
            "take_profit": 100.0,
        }
        res = officer.evaluate(bad_prop, {})
        assert res["approved"] is False
        assert res["veto"] is True
        assert res["veto_code"] == "VETO_INVALID_GEOMETRY"

    def test_zero_prohibited_identifer_in_artifacts(self, valid_gold_proposal, bullish_market_context):
        chamber = get_consensus_chamber()
        res = chamber.debate(valid_gold_proposal, bullish_market_context)
        dump = str(res.to_dict()).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump

