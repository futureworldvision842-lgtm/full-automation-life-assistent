"""
trading/consensus_chamber/chamber.py
=====================================
Multi-Agent Consensus Chamber for J.A.R.V.I.S.
Coordinates structured debate rounds between:
  - BullishAdvocate
  - BearishChallenger
  - RiskOfficer (Unanimous Veto)
  - ExecutionSpecialist

Enforces deterministic risk thresholds and generates institutional execution plans.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import logging

from .agents import BullishAdvocate, BearishChallenger, RiskOfficer, ExecutionSpecialist

logger = logging.getLogger("Jarvis.ConsensusChamber")

@dataclass
class ConsensusResult:
    proposal_id: str
    symbol: str
    action: str
    approved: bool
    status: str
    consensus_score: float
    veto_reason: Optional[str]
    risk_metrics: Dict[str, Any]
    execution_plan: Optional[Dict[str, Any]]
    debate_transcript: List[Dict[str, Any]]
    summary_urdu_en: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "symbol": self.symbol,
            "action": self.action,
            "approved": self.approved,
            "status": self.status,
            "consensus_score": round(self.consensus_score, 2),
            "veto_reason": self.veto_reason,
            "risk_metrics": self.risk_metrics,
            "execution_plan": self.execution_plan,
            "debate_transcript": self.debate_transcript,
            "summary_urdu_en": self.summary_urdu_en,
            "timestamp": self.timestamp,
        }


class ConsensusChamber:
    def __init__(
        self,
        max_risk_pct: float = 0.75,
        max_risk_usd: float = 750.0,
        min_rr: float = 2.5,
        consensus_threshold: float = 70.0,
    ):
        self.consensus_threshold = consensus_threshold
        self.bull_agent = BullishAdvocate()
        self.bear_agent = BearishChallenger()
        self.risk_officer = RiskOfficer(max_risk_pct=max_risk_pct, max_risk_usd=max_risk_usd, min_rr=min_rr)
        self.exec_specialist = ExecutionSpecialist()

    def debate(self, proposal: Dict[str, Any], market_context: Optional[Dict[str, Any]] = None) -> ConsensusResult:
        """
        Conducts multi-agent institutional debate over a proposed trade.
        """
        if market_context is None:
            market_context = {}

        proposal_id = str(proposal.get("proposal_id", f"PROP-{int(time.time() * 1000)}"))
        symbol = str(proposal.get("symbol", "UNKNOWN")).upper()
        action = str(proposal.get("action", "BUY")).upper()

        transcript: List[Dict[str, Any]] = []

        # Round 1: Individual Evaluations
        bull_eval = self.bull_agent.evaluate(proposal, market_context)
        bear_eval = self.bear_agent.evaluate(proposal, market_context)
        risk_eval = self.risk_officer.evaluate(proposal, market_context)
        exec_eval = self.exec_specialist.evaluate(proposal, market_context)

        transcript.append({"round": 1, "phase": "OPENING_ARGUMENTS", "agent": bull_eval["agent"], "data": bull_eval})
        transcript.append({"round": 1, "phase": "OPENING_ARGUMENTS", "agent": bear_eval["agent"], "data": bear_eval})
        transcript.append({"round": 1, "phase": "RISK_AUDIT", "agent": risk_eval["agent"], "data": risk_eval})
        transcript.append({"round": 1, "phase": "EXECUTION_ROUTING", "agent": exec_eval["agent"], "data": exec_eval})

        # UNANIMOUS RISK OFFICER VETO CHECK
        if not risk_eval.get("approved", False):
            veto_reason = risk_eval.get("veto_reason", "Risk parameters violated")
            summary = (
                f"VETOED BY RISK OFFICER: {veto_reason} | "
                f"Master Muhammad Qureshi ki capital safety non-negotiable hai. Trade reject kar di gayi."
            )
            return ConsensusResult(
                proposal_id=proposal_id,
                symbol=symbol,
                action=action,
                approved=False,
                status="VETOED_BY_RISK_OFFICER",
                consensus_score=0.0,
                veto_reason=veto_reason,
                risk_metrics=risk_eval.get("risk_metrics", {}),
                execution_plan=None,
                debate_transcript=transcript,
                summary_urdu_en=summary,
            )

        # Round 2: Cross-Examination & Rebuttal
        bull_rebut = self.bull_agent.rebut(proposal, market_context, [bear_eval])
        bear_rebut = self.bear_agent.rebut(proposal, market_context, [bull_eval])
        transcript.append({"round": 2, "phase": "REBUTTALS", "agent": bull_rebut["agent"], "data": bull_rebut})
        transcript.append({"round": 2, "phase": "REBUTTALS", "agent": bear_rebut["agent"], "data": bear_rebut})

        # Score synthesis
        bull_score = float(bull_eval.get("confidence", 50.0))
        bear_score = float(bear_eval.get("confidence", 50.0))
        exec_score = float(exec_eval.get("confidence", 85.0))

        if action == "BUY":
            # High bull confidence and low bear counter-arguments produce high consensus
            raw_score = (bull_score * 0.55) + ((100.0 - bear_score) * 0.25) + (exec_score * 0.20)
        else: # SELL
            raw_score = (bear_score * 0.55) + ((100.0 - bull_score) * 0.25) + (exec_score * 0.20)

        final_score = max(0.0, min(100.0, raw_score))
        is_approved = final_score >= self.consensus_threshold

        status = "APPROVED_HIGH_CONVICTION" if is_approved else "REJECTED_LOW_CONFLUENCE"
        
        if is_approved:
            summary = (
                f"CONSENSUS REACHED ({final_score:.1f}%): {action} {symbol} approved. "
                f"Risk Officer cleared: {risk_eval['risk_metrics'].get('risk_pct')}% risk. "
                f"Master Sir, execution plan dynamic breakeven +1.0R armed. Tayyar hai!"
            )
        else:
            summary = (
                f"CONSENSUS INSUFFICIENT ({final_score:.1f}% < {self.consensus_threshold}%): "
                f"{action} {symbol} council debate did not meet confluence threshold. Stance: WAIT."
            )

        return ConsensusResult(
            proposal_id=proposal_id,
            symbol=symbol,
            action=action,
            approved=is_approved,
            status=status,
            consensus_score=final_score,
            veto_reason=None if is_approved else f"Score {final_score:.1f} below {self.consensus_threshold}",
            risk_metrics=risk_eval.get("risk_metrics", {}),
            execution_plan=exec_eval.get("execution_plan") if is_approved else None,
            debate_transcript=transcript,
            summary_urdu_en=summary,
        )


_global_chamber: Optional[ConsensusChamber] = None

def get_consensus_chamber(
    max_risk_pct: float = 0.75,
    max_risk_usd: float = 750.0,
    min_rr: float = 2.5,
) -> ConsensusChamber:
    global _global_chamber
    if _global_chamber is None:
        _global_chamber = ConsensusChamber(
            max_risk_pct=max_risk_pct,
            max_risk_usd=max_risk_usd,
            min_rr=min_rr,
        )
    return _global_chamber
