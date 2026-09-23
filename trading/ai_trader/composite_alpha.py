"""
trading/ai_trader/composite_alpha.py — Multi-Asset Composite Alpha Scoring Engine
=============================================================================
Combines orthogonal Qlib Alpha158 and dynamic institutional factors into calibrated
composite alpha scores. Applies asset-class specific factor weighting regimes
for Forex Majors (EURUSD, GBPUSD), Gold (XAUUSD), and Crypto Majors (BTC, ETH, SOL).

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import math
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from trading.ai_trader.qlib_factors import (
    QlibAlpha158,
    compute_pvt,
    compute_vas,
    compute_lee_ready_cvd,
    compute_str,
)


class CompositeAlphaEngine:
    """
    Asset-specific composite alpha scoring engine.
    Normalizes multi-factor distributions using robust rolling z-scores and applies
    institutional weighting matrices tailored to distinct asset-class market dynamics.
    """

    DEFAULT_REGIMES = {
        "FOREX": {
            "mean_reversion": 0.35,
            "momentum": 0.20,
            "vas": 0.25,
            "cvd": 0.10,
            "macro_div": 0.10,
        },
        "GOLD": {
            "mean_reversion": 0.15,
            "momentum": 0.40,
            "vas": 0.20,
            "cvd": 0.15,
            "macro_div": 0.10,
        },
        "CRYPTO": {
            "mean_reversion": 0.10,
            "momentum": 0.30,
            "vas": 0.15,
            "cvd": 0.35,
            "macro_div": 0.10,
        },
    }

    def __init__(self, asset_weights: Optional[Dict[str, Dict[str, float]]] = None):
        self.asset_weights = asset_weights or self.DEFAULT_REGIMES

    def get_asset_category(self, symbol: str) -> str:
        sym = symbol.upper().strip()
        if any(k in sym for k in ["XAU", "GOLD", "XAG", "SILVER"]):
            return "GOLD"
        elif any(k in sym for k in ["BTC", "ETH", "SOL", "CRYPTO"]):
            return "CRYPTO"
        else:
            return "FOREX"

    @staticmethod
    def _robust_zscore(series: pd.Series) -> float:
        """Computes current robust z-score: clip((val - median) / (IQR + eps), -2.5, 2.5) / 2.5."""
        s = series.dropna()
        if len(s) < 2:
            return 0.0
        val = float(s.iloc[-1])
        median = float(s.median())
        q75, q25 = float(s.quantile(0.75)), float(s.quantile(0.25))
        iqr = q75 - q25
        scale = iqr if iqr > 1e-6 else float(s.std()) + 1e-6
        z = (val - median) / scale
        clipped = max(-2.5, min(2.5, z))
        return clipped / 2.5  # Returns in [-1.0, 1.0]

    def compute_composite_score(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Calculates asset-specific composite alpha score and institutional trade bias.
        Returns:
            {
                "symbol": symbol,
                "alpha_score": float (-1.0 to 1.0),
                "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
                "confluence_bonus": float (0.0 to 0.40),
                "factors": Dict[str, float]
            }
        """
        category = self.get_asset_category(symbol)
        weights = self.asset_weights.get(category, self.DEFAULT_REGIMES["FOREX"])

        # Compute factor series
        str_series = compute_str(df, window=20)
        vas_series = compute_vas(df, atr_period=14)
        _, cvd_div_series = compute_lee_ready_cvd(df, window=20)
        pvt_osc_series = compute_pvt(df, window=20)

        # Momentum: 20-bar ROC
        close = df["close"]
        safe_shift = np.where(close.shift(20).bfill() != 0, close.shift(20).bfill(), 1e-9)
        roc_series = (close / safe_shift) - 1.0

        # Robust z-scores
        z_mr = self._robust_zscore(str_series)
        z_mom = self._robust_zscore(roc_series)
        z_vas = self._robust_zscore(vas_series)
        z_cvd = self._robust_zscore(cvd_div_series)
        z_div = self._robust_zscore(pvt_osc_series)

        factor_zscores = {
            "mean_reversion": round(z_mr, 4),
            "momentum": round(z_mom, 4),
            "vas": round(z_vas, 4),
            "cvd": round(z_cvd, 4),
            "macro_div": round(z_div, 4),
        }

        # Weighted combination
        composite = (
            weights["mean_reversion"] * z_mr +
            weights["momentum"] * z_mom +
            weights["vas"] * z_vas +
            weights["cvd"] * z_cvd +
            weights["macro_div"] * z_div
        )
        composite = max(-1.0, min(1.0, composite))

        # Directional bias
        if composite >= 0.25:
            bias = "BULLISH"
        elif composite <= -0.25:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        confluence_bonus = round(abs(composite) * 0.40, 2)

        return {
            "symbol": symbol.upper().strip(),
            "category": category,
            "alpha_score": round(composite, 4),
            "bias": bias,
            "confluence_bonus": confluence_bonus,
            "factors": factor_zscores,
        }
