"""
core/reasoning_dag.py
======================
ByteDance Deer-Flow Deep Reasoning Pipeline for J.A.R.V.I.S.
Provides Directed Acyclic Graph (DAG) structured reasoning:
  - Deconstructs complex market and operational queries into verifiable nodes.
  - Enforces topological execution order with cycle detection.
  - Synthesizes World Monitor macro alerts, on-chain whale activity, sentiment, and risk gates.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import time
import logging

logger = logging.getLogger("Jarvis.DeerFlowDAG")

class DAGCycleException(Exception):
    """Raised when a circular dependency is detected in the reasoning graph."""
    pass

class DAGDependencyMissingException(Exception):
    """Raised when a node depends on a non-existent upstream node."""
    pass


@dataclass
class ReasoningNode:
    node_id: str
    node_type: str  # INGEST, HYPOTHESIS, VALIDATION, CROSS_REFERENCE, DECISION
    description: str
    depends_on: List[str] = field(default_factory=list)
    action: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None
    output: Optional[Dict[str, Any]] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "description": self.description,
            "depends_on": self.depends_on,
            "output": self.output,
            "status": self.status,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


class ReasoningDAG:
    """
    Structured deep reasoning execution pipeline.
    """
    def __init__(self, dag_id: str, title: str):
        self.dag_id = dag_id
        self.title = title
        self.nodes: Dict[str, ReasoningNode] = {}

    def add_node(
        self,
        node_id: str,
        node_type: str,
        description: str,
        depends_on: Optional[List[str]] = None,
        action: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> "ReasoningDAG":
        """Adds a reasoning node to the DAG."""
        deps = depends_on or []
        self.nodes[node_id] = ReasoningNode(
            node_id=node_id,
            node_type=node_type,
            description=description,
            depends_on=deps,
            action=action,
        )
        return self

    def topological_sort(self) -> List[str]:
        """
        Validates graph dependencies and returns a topologically ordered list of node IDs.
        Raises DAGDependencyMissingException or DAGCycleException if invalid.
        """
        # 1. Verify all dependencies exist
        for node_id, node in self.nodes.items():
            for dep in node.depends_on:
                if dep not in self.nodes:
                    raise DAGDependencyMissingException(f"Node '{node_id}' depends on missing node '{dep}'")

        # 2. Cycle detection via Kahn's algorithm
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for node_id, node in self.nodes.items():
            for dep in node.depends_on:
                adj[dep].append(node_id)
                in_degree[node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        ordered: List[str] = []

        while queue:
            curr = queue.pop(0)
            ordered.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(self.nodes):
            cycle_nodes = [nid for nid, deg in in_degree.items() if deg > 0]
            raise DAGCycleException(f"Circular dependency detected involving nodes: {cycle_nodes}")

        return ordered

    def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes all DAG nodes in strict topological order, passing upstream
        node outputs and accumulated context down the graph.
        """
        start_time = time.perf_counter()
        execution_order = self.topological_sort()
        context = dict(initial_context or {})
        node_outputs: Dict[str, Any] = {}

        for node_id in execution_order:
            node = self.nodes[node_id]
            node.status = "RUNNING"
            n_start = time.perf_counter()

            # Gather upstream outputs
            upstream_data = {dep: node_outputs.get(dep) for dep in node.depends_on}

            try:
                if node.action:
                    result = node.action(context, upstream_data)
                else:
                    result = {"status": "PASSTHROUGH", "data": upstream_data}

                node.output = result
                node.status = "COMPLETED"
                node_outputs[node_id] = result

                # Update accumulated context if node produced new context keys
                if isinstance(result, dict) and "context_update" in result:
                    context.update(result["context_update"])

            except Exception as exc:
                logger.exception("Reasoning DAG error in node %s: %s", node_id, exc)
                node.status = "FAILED"
                node.error = str(exc)
                node_outputs[node_id] = {"error": str(exc)}
                break
            finally:
                node.execution_time_ms = (time.perf_counter() - n_start) * 1000.0

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        is_success = all(n.status == "COMPLETED" for n in self.nodes.values())

        # Extract final decision node output if present
        final_decision = None
        for n in reversed(execution_order):
            if self.nodes[n].node_type == "DECISION" and self.nodes[n].status == "COMPLETED":
                final_decision = self.nodes[n].output
                break

        return {
            "dag_id": self.dag_id,
            "title": self.title,
            "success": is_success,
            "total_nodes": len(self.nodes),
            "execution_order": execution_order,
            "node_details": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "node_outputs": node_outputs,
            "final_decision": final_decision,
            "elapsed_ms": round(total_elapsed_ms, 2),
        }


def build_market_reasoning_dag(symbol: str = "XAUUSD") -> ReasoningDAG:
    """
    Standard Deer-Flow deep reasoning graph for market intelligence:
      1. data_ingest: Technical OHLCV + SMC levels
      2. world_monitor_ingest: Geopolitical DEFCON + Macro yields
      3. social_vibe_score: Social sentiment analysis
      4. cross_reference: Multi-modal synthesis
      5. risk_gating: Non-negotiable <=0.75% risk audit
      6. sovereign_decision: Final directional order or hold
    """
    dag = ReasoningDAG(dag_id=f"DAG-{symbol}", title=f"Deep Reasoning Pipeline for {symbol}")

    def ingest_tech(ctx, upstream):
        return {
            "symbol": symbol,
            "trend": ctx.get("trend", "BULLISH"),
            "rsi": ctx.get("rsi", 54.0),
            "smc_zone": "DISCOUNT_OTE",
        }

    def ingest_macro(ctx, upstream):
        return {
            "geopolitical_risk": ctx.get("defcon", "DEFCON_3_ELEVATED"),
            "us_10y_yield": ctx.get("yield_10y", 4.72),
            "dxy_index": ctx.get("dxy", 103.8),
        }

    def ingest_vibe(ctx, upstream):
        from intelligence.vibe_sentiment import get_vibe_sentiment_engine
        vibe_eng = get_vibe_sentiment_engine()
        headlines = ctx.get("headlines", [f"Strong institutional buying in {symbol}", "Gold safe-haven flight continues"])
        res = vibe_eng.analyze(symbol, headlines, use_slm=False)
        return res.to_dict()

    def cross_ref(ctx, upstream):
        tech = upstream.get("tech_data", {})
        macro = upstream.get("macro_data", {})
        vibe = upstream.get("vibe_data", {})

        confluence_score = 50.0
        if tech.get("trend") == "BULLISH":
            confluence_score += 20.0
        if "ELEVATED" in str(macro.get("geopolitical_risk")):
            confluence_score += 15.0
        if vibe.get("vibe_score", 0.0) > 20.0:
            confluence_score += 15.0

        return {
            "confluence_score": min(100.0, confluence_score),
            "hypothesis": f"Bullish continuation for {symbol} supported by geopolitical demand and tech OTE discount.",
        }

    def risk_audit(ctx, upstream):
        from trading.consensus_chamber.agents import RiskOfficer
        officer = RiskOfficer(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)
        proposal = {
            "symbol": symbol,
            "action": "BUY",
            "price": ctx.get("price", 2650.0),
            "stop_loss": ctx.get("stop_loss", 2640.0),
            "take_profit": ctx.get("take_profit", 2680.0),
            "risk_pct": ctx.get("risk_pct", 0.50),
            "risk_usd": ctx.get("risk_usd", 500.0),
            "rr_ratio": 3.0,
        }
        verdict = officer.evaluate(proposal, {})
        return verdict

    def sovereign_decision(ctx, upstream):
        risk = upstream.get("risk_check", {})
        confluence = upstream.get("confluence", {})
        approved = risk.get("approved", False) and confluence.get("confluence_score", 0.0) >= 70.0
        return {
            "symbol": symbol,
            "action": "BUY" if approved else "WAIT",
            "verdict": "EXECUTE_HIGH_CONVICTION" if approved else "PASS_INSUFFICIENT_CONFLUENCE",
            "risk_approved": risk.get("approved", False),
            "confluence_score": confluence.get("confluence_score", 0.0),
            "breakeven_armed": True if approved else False,
        }

    dag.add_node("tech_data", "INGEST", "Ingest Technical Indicators", action=ingest_tech)
    dag.add_node("macro_data", "INGEST", "Ingest World Monitor Geopolitical & Yield Data", action=ingest_macro)
    dag.add_node("vibe_data", "INGEST", "Compute Real-Time Vibe Sentiment", action=ingest_vibe)
    dag.add_node("confluence", "CROSS_REFERENCE", "Cross-Reference Multimodal Streams", depends_on=["tech_data", "macro_data", "vibe_data"], action=cross_ref)
    dag.add_node("risk_check", "VALIDATION", "Enforce Strict Prop-Firm Risk Bounds", depends_on=["confluence"], action=risk_audit)
    dag.add_node("final_decision", "DECISION", "Emit Sovereign Trading Decision", depends_on=["confluence", "risk_check"], action=sovereign_decision)

    return dag
