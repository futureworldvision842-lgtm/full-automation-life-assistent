"""
trading/ai_trader/types.py — Type definitions and data schemas for HKUDS AI-Trader.
=============================================================================
Data classes, enums, and verdict schemas supporting cooperative multi-agent
reasoning (Macro Analyst, Order Flow Scout, Stat Arb, Coordinator), factor mining,
and deterministic risk gating.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MacroRegime(str, Enum):
    GEOPOLITICAL_FLIGHT_TO_SAFETY = "GEOPOLITICAL_FLIGHT_TO_SAFETY"
    LIQUIDITY_EXPANSION = "LIQUIDITY_EXPANSION"
    RISK_OFF_CONTRACTION = "RISK_OFF_CONTRACTION"
    BALANCED_RANGE = "BALANCED_RANGE"


class AbsorptionType(str, Enum):
    BUYER_ABSORPTION = "BUYER_ABSORPTION"
    SELLER_ABSORPTION = "SELLER_ABSORPTION"
    BALANCED = "BALANCED"


class ArbitrageType(str, Enum):
    CROSS_PAIR_SPREAD = "CROSS_PAIR_SPREAD"
    GSR_RELATIVE_VALUE = "GSR_RELATIVE_VALUE"
    PERP_FUNDING_CARRY = "PERP_FUNDING_CARRY"
    NONE = "NONE"


class SignalGrade(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    WEAK = "WEAK"


@dataclass
class MacroVerdict:
    """Institutional macroeconomic, monetary, and geopolitical intelligence output."""
    symbol: str
    bias: str                                  # "BULLISH", "BEARISH", "NEUTRAL"
    conviction: float                          # 0.0 to 1.0
    macro_regime: str                          # e.g. "GEOPOLITICAL_FLIGHT_TO_SAFETY"
    defcon_level: int                          # 1 to 5
    geopolitical_risk_score: float             # 0.0 to 100.0
    macro_multiplier: float                    # e.g. 1.45 for Gold during disruption
    news_lockout_active: bool                  # True if within 15m blackout window
    news_event_name: Optional[str] = None
    dxy_trend: str = "RANGE"                   # "BULLISH", "BEARISH", "RANGE"
    dxy_correlation: float = -0.85
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bias": self.bias,
            "conviction": self.conviction,
            "macro_regime": self.macro_regime,
            "defcon_level": self.defcon_level,
            "geopolitical_risk_score": self.geopolitical_risk_score,
            "macro_multiplier": self.macro_multiplier,
            "news_lockout_active": self.news_lockout_active,
            "news_event_name": self.news_event_name,
            "dxy_trend": self.dxy_trend,
            "dxy_correlation": self.dxy_correlation,
            "rationale": self.rationale
        }


@dataclass
class OrderFlowVerdict:
    """Microstructure tactical order flow and Level-2 DOM surveillance output."""
    symbol: str
    bias: str                                  # "BULLISH_ACCUMULATION", "BEARISH_DISTRIBUTION", "NEUTRAL"
    conviction: float                          # 0.0 to 1.0
    dom_imbalance_ratio: float                 # sum(bids) / max(1.0, sum(asks))
    dom_bias: str                              # "BULLISH_ABSORPTION", "BEARISH_DISTRIBUTION", "BALANCED"
    whale_walls_count: int = 0
    whale_walls: List[Dict[str, Any]] = field(default_factory=list)
    cvd_net_delta: float = 0.0
    absorption_type: str = "BALANCED"          # "BUYER_ABSORPTION", "SELLER_ABSORPTION", "BALANCED"
    absorption_divergence: str = "NEUTRAL"      # "BULLISH_CONTINUATION", "BEARISH_REVERSAL", "NEUTRAL"
    turtle_soup_swept: bool = False
    turtle_soup_details: Dict[str, Any] = field(default_factory=dict)
    ipda_regime: str = "EQUILIBRIUM"           # "DISCOUNT_BUY_ZONE", "PREMIUM_SELL_ZONE", "EQUILIBRIUM"
    session_killzone: str = "OFF_HOURS"        # "LONDON_KILL_ZONE", "NY_KILL_ZONE", "CRYPTO_CONTINUOUS", "OFF_HOURS"
    killzone_active: bool = False
    spread_multiplier: float = 1.0
    spread_status: str = "STABLE_NORMAL"       # "STABLE_NORMAL", "ELEVATED_WATCH", "EXPANDED_LOCKOUT"
    sub_2ms_ready: bool = True
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bias": self.bias,
            "conviction": self.conviction,
            "dom_imbalance_ratio": self.dom_imbalance_ratio,
            "dom_bias": self.dom_bias,
            "whale_walls_count": self.whale_walls_count,
            "whale_walls": self.whale_walls,
            "cvd_net_delta": self.cvd_net_delta,
            "absorption_type": self.absorption_type,
            "absorption_divergence": self.absorption_divergence,
            "turtle_soup_swept": self.turtle_soup_swept,
            "turtle_soup_details": self.turtle_soup_details,
            "ipda_regime": self.ipda_regime,
            "session_killzone": self.session_killzone,
            "killzone_active": self.killzone_active,
            "spread_multiplier": self.spread_multiplier,
            "spread_status": self.spread_status,
            "sub_2ms_ready": self.sub_2ms_ready,
            "rationale": self.rationale
        }


@dataclass
class StatArbVerdict:
    """Relative value, cointegration, mean-reversion spreads, and synthetic arbitrage output."""
    symbol: str
    bias: str                                  # "BULLISH_MEAN_REVERSION", "BEARISH_MEAN_REVERSION", "NEUTRAL"
    conviction: float                          # 0.0 to 1.0
    arbitrage_type: str = "NONE"               # "CROSS_PAIR_SPREAD", "GSR_RELATIVE_VALUE", "PERP_FUNDING_CARRY", "NONE"
    pair_symbol: Optional[str] = None          # e.g., "GBPUSD" when trading "EURUSD"
    hedge_ratio: float = 1.0                   # OLS slope
    spread_zscore: float = 0.0
    half_life_bars: float = 0.0                # Ornstein-Uhlenbeck half-life
    expected_reversion_target: float = 0.0
    funding_rate_8h: float = 0.0
    funding_annualized_pct: float = 0.0
    basis_pct: float = 0.0
    gsr_ratio: float = 80.0                    # Gold/Silver Ratio
    gsr_regime: str = "NORMAL"
    cointegration_confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bias": self.bias,
            "conviction": self.conviction,
            "arbitrage_type": self.arbitrage_type,
            "pair_symbol": self.pair_symbol,
            "hedge_ratio": self.hedge_ratio,
            "spread_zscore": self.spread_zscore,
            "half_life_bars": self.half_life_bars,
            "expected_reversion_target": self.expected_reversion_target,
            "funding_rate_8h": self.funding_rate_8h,
            "funding_annualized_pct": self.funding_annualized_pct,
            "basis_pct": self.basis_pct,
            "gsr_ratio": self.gsr_ratio,
            "gsr_regime": self.gsr_regime,
            "cointegration_confidence": self.cointegration_confidence,
            "rationale": self.rationale
        }


@dataclass
class SignalQualityScore:
    """HKUDS 5-dimension heuristic signal quality assessment."""
    composite_score: float                     # 0.0 to 5.0
    verifiability: float                       # 30% weight
    evidence: float                            # 25% weight
    specificity: float                         # 20% weight
    novelty: float                             # 15% weight
    timeliness: float                          # 10% weight
    grade: str                                 # "EXCELLENT", "GOOD", "FAIR", "WEAK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 2),
            "verifiability": round(self.verifiability, 2),
            "evidence": round(self.evidence, 2),
            "specificity": round(self.specificity, 2),
            "novelty": round(self.novelty, 2),
            "timeliness": round(self.timeliness, 2),
            "grade": self.grade
        }


@dataclass
class ConsensusVerdict:
    """Cooperative multi-agent consensus synthesis produced by AITraderCoordinator."""
    symbol: str
    admitted: bool
    direction: str                             # "BUY", "SELL", "HOLD"
    confluence_score: float                    # 0.0 to 100.0
    unanimous: bool = False
    macro_verdict: Optional[MacroVerdict] = None
    orderflow_verdict: Optional[OrderFlowVerdict] = None
    stat_arb_verdict: Optional[StatArbVerdict] = None
    quality_score: Optional[SignalQualityScore] = None
    blockers: List[str] = field(default_factory=list)
    synthesis_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "admitted": self.admitted,
            "direction": self.direction,
            "confluence_score": round(self.confluence_score, 2),
            "unanimous": self.unanimous,
            "macro_verdict": self.macro_verdict.to_dict() if self.macro_verdict else None,
            "orderflow_verdict": self.orderflow_verdict.to_dict() if self.orderflow_verdict else None,
            "stat_arb_verdict": self.stat_arb_verdict.to_dict() if self.stat_arb_verdict else None,
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
            "blockers": self.blockers,
            "synthesis_rationale": self.synthesis_rationale
        }


@dataclass
class CandidateSetup:
    """Candidate trade setup formulated by AI-Trader for submission to DeterministicRiskKernel."""
    symbol: str
    direction: str                             # "BUY", "SELL"
    entry_price: float
    sl: float
    tp: float
    rr_ratio: float
    risk_pct: float
    risk_usd: float
    lot_size: float = 0.10
    dynamic_be_trigger_r: float = 1.0
    consensus_verdict: Optional[ConsensusVerdict] = None
    proposal_token: Optional[str] = None
    timestamp_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "sl": self.sl,
            "tp": self.tp,
            "lot_size": self.lot_size,
            "rr_ratio": round(self.rr_ratio, 2),
            "risk_pct": round(self.risk_pct, 4),
            "risk_usd": round(self.risk_usd, 2),
            "dynamic_be_trigger_r": self.dynamic_be_trigger_r,
            "consensus_verdict": self.consensus_verdict.to_dict() if self.consensus_verdict else None,
            "proposal_token": self.proposal_token,
            "timestamp_utc": self.timestamp_utc
        }


@dataclass
class FactorEvaluationReport:
    """Statistical evaluation metrics and gating report for a mined alpha factor."""
    factor_name: str
    expression: str
    ic_pearson: float
    rank_ic_spearman: float
    information_ratio: float
    sharpe_ratio: float
    autocorrelation: float
    turnover: float
    monotonicity: float
    passed: bool
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "expression": self.expression,
            "ic_pearson": round(self.ic_pearson, 4),
            "rank_ic_spearman": round(self.rank_ic_spearman, 4),
            "information_ratio": round(self.information_ratio, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "autocorrelation": round(self.autocorrelation, 4),
            "turnover": round(self.turnover, 4),
            "monotonicity": round(self.monotonicity, 4),
            "passed": self.passed,
            "rejection_reasons": self.rejection_reasons
        }
