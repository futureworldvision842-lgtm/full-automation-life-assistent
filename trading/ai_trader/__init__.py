"""
trading/ai_trader/__init__.py — HKUDS AI-Trader Autonomous Quantitative Intelligence
=============================================================================
Clean exports of all virtual agent roles, vectorized factor engines, safe AST
parsers, factor evaluators, autonomous formula miners, composite scorers,
and multi-agent coordinators.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

from trading.ai_trader.types import (
    Direction,
    MacroRegime,
    AbsorptionType,
    ArbitrageType,
    SignalGrade,
    MacroVerdict,
    OrderFlowVerdict,
    StatArbVerdict,
    SignalQualityScore,
    ConsensusVerdict,
    CandidateSetup,
    FactorEvaluationReport,
)
from trading.ai_trader.macro_analyst import MacroQuantitativeAnalyst
from trading.ai_trader.orderflow_scout import HighFrequencyOrderFlowScout
from trading.ai_trader.stat_arb import StatisticalArbitrageur
from trading.ai_trader.qlib_factors import (
    QlibAlpha158,
    compute_rsi,
    compute_pvt,
    compute_vas,
    compute_lee_ready_cvd,
    compute_cs_momentum,
    compute_str,
    compute_correlation_divergence,
)
from trading.ai_trader.formula_parser import FormulaASTParser
from trading.ai_trader.alpha_evaluator import AlphaEvaluator
from trading.ai_trader.alpha_miner import AITraderAlphaMiner
from trading.ai_trader.composite_alpha import CompositeAlphaEngine
from trading.ai_trader.coordinator import AITraderCoordinator

_global_coordinator = None


def get_ai_trader_coordinator() -> AITraderCoordinator:
    """Returns singleton instance of AITraderCoordinator."""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = AITraderCoordinator()
    return _global_coordinator


__all__ = [
    "Direction",
    "MacroRegime",
    "AbsorptionType",
    "ArbitrageType",
    "SignalGrade",
    "MacroVerdict",
    "OrderFlowVerdict",
    "StatArbVerdict",
    "SignalQualityScore",
    "ConsensusVerdict",
    "CandidateSetup",
    "FactorEvaluationReport",
    "MacroQuantitativeAnalyst",
    "HighFrequencyOrderFlowScout",
    "StatisticalArbitrageur",
    "QlibAlpha158",
    "compute_rsi",
    "compute_pvt",
    "compute_vas",
    "compute_lee_ready_cvd",
    "compute_cs_momentum",
    "compute_str",
    "compute_correlation_divergence",
    "FormulaASTParser",
    "AlphaEvaluator",
    "AITraderAlphaMiner",
    "CompositeAlphaEngine",
    "AITraderCoordinator",
    "get_ai_trader_coordinator",
]
