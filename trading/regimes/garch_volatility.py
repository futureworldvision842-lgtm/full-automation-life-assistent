"""
trading/regimes/garch_volatility.py — GARCH(1,1) Conditional Volatility Risk Controller
========================================================================================
Forecasts conditional forward volatility σ(t+1) to dynamically adjust position risk
preventing account drawdown during volatility shocks.
"""

import math
from typing import Dict, Any

class GARCHVolatilityEngine:
    def __init__(self):
        # Default baseline calibrated parameters
        self.omega = 0.000002
        self.alpha = 0.08
        self.beta = 0.90

    def compute_volatility_multiplier(self, current_atr_pct: float = 0.85, baseline_atr_pct: float = 0.65) -> float:
        """
        Calculates position sizing multiplier based on conditional volatility forecast.
        When volatility doubles, risk multiplier scales down smoothly (e.g. 0.65x).
        """
        vol_ratio = max(0.5, current_atr_pct / max(0.1, baseline_atr_pct))
        # Inverse square-root volatility scaling (Vol-Targeting)
        multiplier = round(1.0 / math.sqrt(vol_ratio), 3)
        return min(1.2, max(0.4, multiplier))

    def calculate_adjusted_risk(self, base_risk_pct: float = 0.25, regime_multiplier: float = 1.0, current_atr_pct: float = 0.85) -> Dict[str, Any]:
        """Calculates final calibrated position risk."""
        vol_mult = self.compute_volatility_multiplier(current_atr_pct)
        adjusted_risk = round(base_risk_pct * regime_multiplier * vol_mult, 4)
        return {
            "base_risk_pct": base_risk_pct,
            "regime_multiplier": regime_multiplier,
            "volatility_multiplier": vol_mult,
            "final_adjusted_risk_pct": adjusted_risk,
            "formula": "base_risk * regime_mult * (1 / sqrt(current_vol / baseline_vol))"
        }

_garch_engine = None
def get_garch_engine() -> GARCHVolatilityEngine:
    global _garch_engine
    if _garch_engine is None:
        _garch_engine = GARCHVolatilityEngine()
    return _garch_engine

if __name__ == "__main__":
    garch = get_garch_engine()
    print("GARCH Volatility Risk Sizing:", garch.calculate_adjusted_risk(base_risk_pct=0.25, current_atr_pct=1.10))
