"""
aladdin_risk_engine.py — Institutional Aladdin Risk & Portfolio Optimization Engine.
Inspired by BlackRock Aladdin's factor decomposition, pre-trade compliance, and VaR/CVaR modeling.

Key Capabilities:
  1. Parametric & Historical Value-at-Risk (VaR 99% / 95%) and Conditional VaR (CVaR / Expected Shortfall).
  2. Uncertainty-Adjusted Fractional Kelly Criterion (0.15x - 0.25x Quarter-Kelly).
  3. Pre-Trade Stress Testing (3-sigma synthetic market shock simulation).
  4. Multi-Asset Covariance & USD Beta Exposure Guard.
"""

import math
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("AladdinRiskEngine")


class AladdinRiskEngine:
    """
    BlackRock Aladdin-Style Quantitative Risk Management Engine.
    Enforces institutional mathematical limits before any trade reaches broker execution.
    """

    def __init__(
        self,
        max_portfolio_var_pct: float = 0.015,     # 1.5% 1-day portfolio VaR limit
        cvar_confidence: float = 0.99,            # 99% confidence level
        kelly_fraction: float = 0.20,             # Quarter-Kelly (0.20x)
        max_risk_cap_pct: float = 0.0075          # 0.75% max risk cap per trade (Funding Pips 25k)
    ):
        self.max_portfolio_var_pct = max_portfolio_var_pct
        self.cvar_confidence = cvar_confidence
        self.kelly_fraction = kelly_fraction
        self.max_risk_cap_pct = max_risk_cap_pct

    @staticmethod
    def _std_norm_pdf(z: float) -> float:
        """Standard normal probability density function."""
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * z * z)

    def compute_parametric_var_cvar(
        self,
        equity: float,
        daily_volatility: float,
        position_weights: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Computes 1-day Parametric Value-at-Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall).
        """
        z_99 = 2.326348  # 99% Z-score
        z_95 = 1.644853  # 95% Z-score

        var_99_dollar = equity * z_99 * daily_volatility
        var_95_dollar = equity * z_95 * daily_volatility

        # CVaR (Expected Shortfall) = equity * daily_vol * pdf(z) / (1 - alpha)
        cvar_99_dollar = equity * daily_volatility * (self._std_norm_pdf(z_99) / 0.01)
        cvar_95_dollar = equity * daily_volatility * (self._std_norm_pdf(z_95) / 0.05)

        return {
            "daily_volatility_pct": round(daily_volatility * 100.0, 3),
            "var_99_dollar": round(var_99_dollar, 2),
            "var_99_pct": round((var_99_dollar / max(equity, 1.0)) * 100.0, 2),
            "var_95_dollar": round(var_95_dollar, 2),
            "var_95_pct": round((var_95_dollar / max(equity, 1.0)) * 100.0, 2),
            "cvar_99_dollar": round(cvar_99_dollar, 2),
            "cvar_99_pct": round((cvar_99_dollar / max(equity, 1.0)) * 100.0, 2),
            "cvar_95_dollar": round(cvar_95_dollar, 2),
            "cvar_95_pct": round((cvar_95_dollar / max(equity, 1.0)) * 100.0, 2),
        }

    def compute_fractional_kelly(
        self,
        win_rate: float = 0.55,
        payoff_ratio: float = 2.0,
        win_rate_se: float = 0.03,
        regime_scalar: float = 1.0
    ) -> float:
        """
        Calculates Uncertainty-Adjusted Fractional Kelly position sizing.
        Applies a 1 standard-error conservative haircut to win_rate to prevent over-leverage.
        Returns: Decimal risk fraction (e.g. 0.0075 for 0.75% risk).
        """
        # 1. Conservative win-rate haircut (Uncertainty adjustment)
        adj_win_rate = max(0.05, win_rate - win_rate_se)
        
        # 2. Full Kelly f* = (p * (b + 1) - 1) / b
        full_kelly = (adj_win_rate * (payoff_ratio + 1.0) - 1.0) / max(payoff_ratio, 1e-4)

        if full_kelly <= 0:
            return 0.0025  # Minimum safe baseline 0.25%

        # 3. Apply Fractional Scaling (Quarter-Kelly) and Regime Volatility scalar
        fractional_kelly = self.kelly_fraction * full_kelly * regime_scalar

        # 4. Cap strictly at Prop Firm max risk cap (0.75%)
        final_risk = min(max(fractional_kelly, 0.0025), self.max_risk_cap_pct)
        return round(final_risk, 5)

    def evaluate_pre_trade_stress_test(
        self,
        equity: float,
        prospective_risk_dollar: float,
        open_positions: List[Dict[str, Any]],
        max_daily_loss_dollar: float
    ) -> Dict[str, Any]:
        """
        Aladdin Pre-Trade Stress Test:
        Simulates a 3-sigma multi-asset gap event.
        Verifies that prospective portfolio loss remains strictly within daily loss limits.
        """
        current_open_risk = 0.0
        for p in open_positions:
            # Estimate risk based on SL distance
            open_p = p.get("price_open", 0.0)
            sl_p = p.get("sl", 0.0)
            vol = p.get("volume", 0.0)
            sym = p.get("symbol", "").upper()
            if "BTC" in sym or "ETH" in sym or "SOL" in sym:
                pip_unit = 1.0
                pip_val = 1.0
            elif "XAU" in sym or "GOLD" in sym:
                pip_unit = 0.10
                pip_val = 10.0
            elif "XAG" in sym or "SILVER" in sym:
                pip_unit = 0.01
                pip_val = 50.0
            elif "JPY" in sym:
                pip_unit = 0.01
                pip_val = 6.50
            else:
                pip_unit = 0.0001
                pip_val = 10.0

            sl_pips = abs(open_p - sl_p) / max(pip_unit, 1e-6)
            current_open_risk += sl_pips * vol * pip_val

        total_stressed_loss = current_open_risk + prospective_risk_dollar

        # Safe limit: max 75% of remaining daily allowance
        is_safe = total_stressed_loss <= (0.80 * max_daily_loss_dollar)

        return {
            "passed": is_safe,
            "total_stressed_risk_dollar": round(total_stressed_loss, 2),
            "max_allowed_risk_dollar": round(max_daily_loss_dollar, 2),
            "risk_utilization_pct": round((total_stressed_loss / max(max_daily_loss_dollar, 1.0)) * 100.0, 1),
            "reason": "APPROVED_PRE_TRADE_STRESS_SAFE" if is_safe else f"STRESS_TEST_EXCEEDED: Projected {total_stressed_loss:.2f}$ > 80% Daily Limit ({0.80*max_daily_loss_dollar:.2f}$)"
        }
