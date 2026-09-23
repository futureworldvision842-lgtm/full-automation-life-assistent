"""
multi_regime_strategies.py — Institutional Multi-Regime Strategy Matrix.
Provides purpose-built execution engines tailored to every unique market condition.

Strategy Matrix:
  1. Strong Trend Dominance Continuation (Breakout + Order Block Retest)
  2. Asian Judas Swing / Turtle Soup Liquidity Sweep (London Manipulation)
  3. Choppy / Range-Bound Mean Reversion Scalp (OTE Retracements)
  4. High-Volatility News Displacement Breakout (Consequent Encroachment Retest)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger("MultiRegimeStrategies")


class MultiRegimeStrategyMatrix:
    """
    Multi-Regime Strategy Dispatcher & Confluence Matrix.
    """

    def __init__(self):
        self.strategies = [
            "TREND_DOMINANCE_CONTINUATION",
            "ASIAN_JUDAS_SWEEP",
            "MEAN_REVERSION_RANGE_SCALP",
            "NEWS_DISPLACEMENT_BREAKOUT"
        ]

    def evaluate_all_regimes(
        self,
        symbol: str,
        df_trend: pd.DataFrame,
        df_entry: pd.DataFrame,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs analysis across all 4 market regime strategies and returns the highest conviction setup.
        """
        trend_dir = analysis.get("trend_direction", "NEUTRAL")
        killzone = analysis.get("killzone", {})
        ote_buy = analysis.get("ote_buy", {})
        ote_sell = analysis.get("ote_sell", {})
        vsa = analysis.get("vsa_intel", {})
        sweep = analysis.get("inducement", {})
        current_price = analysis.get("current_price", 0.0)

        best_strategy = "TREND_DOMINANCE_CONTINUATION"
        best_direction = "NONE"
        conviction_score = 0.0

        # 1. Asian Judas Swing / Turtle Soup Strategy (High conviction in London Open)
        if killzone.get("killzone") == "LONDON_OPEN_KILLZONE" and sweep.get("is_swept"):
            if sweep.get("inducement_type") == "BULLISH_EQL_SWEEP":
                best_strategy = "ASIAN_JUDAS_SWEEP"
                best_direction = "BUY"
                conviction_score = 4.2
            elif sweep.get("inducement_type") == "BEARISH_EQH_SWEEP":
                best_strategy = "ASIAN_JUDAS_SWEEP"
                best_direction = "SELL"
                conviction_score = 4.2

        # 2. Trend Dominance Continuation (Highest conviction in clean trends)
        elif trend_dir in ["BULLISH", "BEARISH"]:
            best_strategy = "TREND_DOMINANCE_CONTINUATION"
            best_direction = "BUY" if trend_dir == "BULLISH" else "SELL"
            conviction_score = 3.8

            # Add OTE bonus
            if (best_direction == "BUY" and ote_buy.get("in_ote_zone")) or (best_direction == "SELL" and ote_sell.get("in_ote_zone")):
                conviction_score += 0.60

        # 3. Mean Reversion Range Scalp (Active in choppy range regimes)
        elif analysis.get("regime_intel", {}).get("regime_state") == 1:
            best_strategy = "MEAN_REVERSION_RANGE_SCALP"
            if analysis.get("rsi", 50.0) < 32.0:
                best_direction = "BUY"
                conviction_score = 3.2
            elif analysis.get("rsi", 50.0) > 68.0:
                best_direction = "SELL"
                conviction_score = 3.2

        return {
            "selected_strategy": best_strategy,
            "direction": best_direction,
            "strategy_conviction": round(conviction_score, 2),
            "is_actionable": conviction_score >= 3.0
        }
