"""
trading/consensus_chamber/__init__.py
======================================
TauricResearch/TradingAgents Consensus Chamber for J.A.R.V.I.S.
Provides multi-agent pre-trade debate and non-negotiable Risk Officer veto.
"""

from .agents import (
    BullishAdvocate,
    BearishChallenger,
    RiskOfficer,
    ExecutionSpecialist,
    DebateAgent,
)
from .chamber import ConsensusChamber, ConsensusResult, get_consensus_chamber

__all__ = [
    "BullishAdvocate",
    "BearishChallenger",
    "RiskOfficer",
    "ExecutionSpecialist",
    "DebateAgent",
    "ConsensusChamber",
    "ConsensusResult",
    "get_consensus_chamber",
]
