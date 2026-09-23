"""
aladdin_regime_model.py — Quantitative Market Regime & Volatility Clustering Model.
Classifies multi-asset financial time-series into latent statistical states.

States:
  State 0: LOW_VOLATILITY_TREND (Optimal Trend Continuation, Standard/Full Kelly)
  State 1: MEAN_REVERTING_CHOP (Range Bound, OTE Retracement Only)
  State 2: HIGH_VOLATILITY_TURBULENCE (Crisis / News Expansion, De-leverage Risk by 75%)
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger("AladdinRegimeModel")


class QuantitativeRegimeDetector:
    """
    3-State Statistical Regime Classifier & Volatility Targeting Engine.
    """

    def __init__(self, target_annualized_vol: float = 0.08):
        self.target_annualized_vol = target_annualized_vol

    def detect_regime(self, df_candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Extracts log returns, rolling volatility, and trend momentum
        to classify the statistical market regime and compute the dynamic volatility risk scalar.
        """
        if df_candles is None or len(df_candles) < 30:
            return {
                "regime_state": 0,
                "regime_name": "LOW_VOLATILITY_TREND",
                "vol_scalar": 1.0,
                "realized_vol_annual_pct": 8.0,
                "is_trading_allowed": True,
                "risk_adjustment": 1.0
            }

        try:
            closes = df_candles['close'].values
            log_ret = np.diff(np.log(closes))
            
            daily_vol = float(np.std(log_ret[-20:])) if len(log_ret) >= 20 else float(np.std(log_ret))
            annual_vol = daily_vol * np.sqrt(252 * 24)  # Annualized from hourly/M15 bars
            
            # Volatility Targeting Scalar
            vol_scalar = min(max(self.target_annualized_vol / max(annual_vol, 1e-4), 0.25), 1.5)

            # Volatility percentile ranking
            rolling_vols = [np.std(log_ret[max(0, i-20):i]) for i in range(20, len(log_ret))]
            current_vol_pctl = (sum(1 for v in rolling_vols if v <= daily_vol) / max(len(rolling_vols), 1)) * 100.0

            # State Classification
            if current_vol_pctl >= 85.0 or annual_vol > 0.25:
                regime_state = 2
                regime_name = "HIGH_VOLATILITY_TURBULENCE"
                risk_adjustment = 0.25  # 75% risk reduction during turbulence
                is_trading_allowed = True
            elif current_vol_pctl <= 35.0:
                regime_state = 0
                regime_name = "LOW_VOLATILITY_TREND"
                risk_adjustment = 1.0   # Full standard risk
                is_trading_allowed = True
            else:
                regime_state = 1
                regime_name = "MEAN_REVERTING_CHOP"
                risk_adjustment = 0.70  # Conservative risk in choppy ranges
                is_trading_allowed = True

            return {
                "regime_state": regime_state,
                "regime_name": regime_name,
                "vol_scalar": round(vol_scalar, 2),
                "realized_vol_annual_pct": round(annual_vol * 100.0, 2),
                "volatility_percentile": round(current_vol_pctl, 1),
                "is_trading_allowed": is_trading_allowed,
                "risk_adjustment": round(risk_adjustment, 2)
            }
        except Exception as e:
            logger.warning(f"Regime detection fallback: {e}")
            return {
                "regime_state": 0,
                "regime_name": "LOW_VOLATILITY_TREND",
                "vol_scalar": 1.0,
                "realized_vol_annual_pct": 8.0,
                "is_trading_allowed": True,
                "risk_adjustment": 1.0
            }
