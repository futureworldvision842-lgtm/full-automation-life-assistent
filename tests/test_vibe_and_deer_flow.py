"""
tests/test_vibe_and_deer_flow.py
=================================
Verification for HKUDS/Vibe-Trading sentiment and ByteDance Deer-Flow DAG reasoning.
"""

import pytest
from intelligence.vibe_sentiment import VibeSentimentEngine, get_vibe_sentiment_engine
from core.reasoning_dag import (
    ReasoningDAG,
    DAGCycleException,
    DAGDependencyMissingException,
    build_market_reasoning_dag,
)

class TestVibeSentimentEngine:
    def test_bullish_sentiment_detection(self):
        engine = get_vibe_sentiment_engine()
        headlines = [
            "Bitcoin breaks out above key resistance with massive institutional inflow",
            "Whale buy detected on Binance orderbook, parabolic expansion likely",
            "Accumulation phase complete; god candle incoming"
        ]
        res = engine.analyze("BTCUSDT", headlines, use_slm=False)
        assert res.target == "BTCUSDT"
        assert res.vibe_score >= 50.0
        assert res.sentiment_label in ("GREED", "EXTREME_GREED")
        assert res.viral_momentum > 3.0
        assert len(res.bullish_signals) >= 3
        assert len(res.risk_flags) == 0

    def test_severe_bearish_and_honeypot_detection(self):
        engine = get_vibe_sentiment_engine()
        headlines = [
            "Warning: Contract functions indicate honeypot scam on new token",
            "Dev insider dump and rug pull triggered liquidation cascade",
            "SEC crackdown and exploit investigation underway"
        ]
        res = engine.analyze("SHADYCOIN", headlines, use_slm=False)
        assert res.target == "SHADYCOIN"
        assert res.vibe_score <= -50.0
        assert res.sentiment_label in ("FEAR", "EXTREME_FEAR")
        assert len(res.risk_flags) >= 2
        assert any("SEVERE_RISK" in flag for flag in res.risk_flags)

    def test_empty_headlines_neutral(self):
        engine = get_vibe_sentiment_engine()
        res = engine.analyze("ETHUSDT", [], use_slm=False)
        assert res.vibe_score == 0.0
        assert res.sentiment_label == "NEUTRAL"
        assert res.viral_momentum == 0.0

    def test_serialization_dict(self):
        engine = get_vibe_sentiment_engine()
        res = engine.analyze("SOLUSDT", ["Solana ecosystem expansion and DEX volume surge"], use_slm=False)
        d = res.to_dict()
        assert d["target"] == "SOLUSDT"
        assert isinstance(d["vibe_score"], float)
        assert isinstance(d["latency_ms"], float)


class TestDeerFlowReasoningDAG:
    def test_topological_sort_success(self):
        dag = ReasoningDAG(dag_id="test_dag", title="Linear Pipeline")
        dag.add_node("step_a", "INGEST", "A")
        dag.add_node("step_b", "VALIDATION", "B", depends_on=["step_a"])
        dag.add_node("step_c", "DECISION", "C", depends_on=["step_b"])

        order = dag.topological_sort()
        assert order == ["step_a", "step_b", "step_c"]

    def test_cycle_detection(self):
        dag = ReasoningDAG(dag_id="cycle_dag", title="Circular Pipeline")
        dag.add_node("node_1", "INGEST", "1", depends_on=["node_3"])
        dag.add_node("node_2", "INGEST", "2", depends_on=["node_1"])
        dag.add_node("node_3", "INGEST", "3", depends_on=["node_2"])

        with pytest.raises(DAGCycleException):
            dag.topological_sort()

    def test_missing_dependency_detection(self):
        dag = ReasoningDAG(dag_id="broken_dag", title="Broken Pipeline")
        dag.add_node("node_x", "INGEST", "X", depends_on=["non_existent_node"])

        with pytest.raises(DAGDependencyMissingException):
            dag.topological_sort()

    def test_execution_data_propagation(self):
        dag = ReasoningDAG(dag_id="math_dag", title="Accumulation")
        dag.add_node("seed", "INGEST", "Seed Value", action=lambda ctx, up: {"val": 10})
        dag.add_node("double", "VALIDATION", "Multiply by 2", depends_on=["seed"],
                     action=lambda ctx, up: {"val": up["seed"]["val"] * 2})
        dag.add_node("add_five", "DECISION", "Add 5", depends_on=["double"],
                     action=lambda ctx, up: {"val": up["double"]["val"] + 5})

        res = dag.execute({})
        assert res["success"] is True
        assert res["node_outputs"]["add_five"]["val"] == 25
        assert res["final_decision"]["val"] == 25

    def test_market_reasoning_dag_e2e(self):
        dag = build_market_reasoning_dag("XAUUSD")
        context = {
            "trend": "BULLISH",
            "rsi": 52.0,
            "defcon": "DEFCON_3_ELEVATED",
            "yield_10y": 4.65,
            "price": 2650.0,
            "stop_loss": 2640.0,
            "take_profit": 2680.0,
            "risk_pct": 0.50,
            "risk_usd": 500.0,
            "headlines": ["Central bank gold reserve accumulation", "Safe haven inflows accelerate"],
        }
        trace = dag.execute(context)
        assert trace["success"] is True
        assert trace["total_nodes"] == 6
        assert trace["final_decision"] is not None
        assert trace["final_decision"]["action"] == "BUY"
        assert trace["final_decision"]["risk_approved"] is True
        assert trace["final_decision"]["breakeven_armed"] is True
        assert trace["final_decision"]["confluence_score"] >= 80.0

    def test_zero_prohibited_identifer(self):
        dag = build_market_reasoning_dag("XAUUSD")
        trace = dag.execute({})
        dump = str(trace).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump
