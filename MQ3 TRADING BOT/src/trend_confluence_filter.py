"""
trend_confluence_filter.py — Multi-Timeframe (M15 + H1 + H4) Trend Confluence Filter.
==================================================================================
Strictly enforces institutional trend alignment across:
- M15: Trigger timeframe (EMA 20 and EMA 50)
- H1: Intermediate trend confirmation (EMA 20 and EMA 50)
- H4: Macro directional bias (EMA 20 and EMA 50)

Rules:
- BUY Condition:
  * M15 bullish: close > ema20 > ema50
  * H1 bullish: h1_ema20 > h1_ema50 and h1_close > h1_ema50
  * H4 non-bearish: not (h4_ema20 < h4_ema50)
- SELL Condition:
  * M15 bearish: close < ema20 < ema50
  * H1 bearish: h1_ema20 < h1_ema50 and h1_close < h1_ema50
  * H4 non-bullish: not (h4_ema20 > h4_ema50)
- If M15 trend conflicts with H1 or H4:
  return (False, None, {"reason": "MTF trend conflict: M15 conflicts with H1/H4"})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
import pandas as pd

logger = logging.getLogger("TrendConfluenceFilter")


class MultiTimeframeConfluenceFilter:
    """
    Evaluates multi-timeframe trend confluence across M15, H1, and H4 candles.
    """

    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> float:
        """Calculates the latest EMA value for a given pandas Series."""
        if series is None or len(series) == 0:
            return 0.0
        return float(series.ewm(span=span, adjust=False).mean().iloc[-1])

    def evaluate_trend_confluence(
        self,
        m15_df: Optional[pd.DataFrame],
        h1_df: Optional[pd.DataFrame],
        h4_df: Optional[pd.DataFrame],
        symbol: str = "XAUUSD",
        direction_hint: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Evaluates M15 trigger against H1 trend and H4 macro directional bias.
        
        Returns:
            Tuple of (approved: bool, direction: Optional[str], telemetry: Dict[str, Any])
        """
        telemetry: Dict[str, Any] = {
            "symbol": symbol,
            "approved": False,
            "reason": "",
        }

        # 1. Validate M15 trigger data
        if m15_df is None or len(m15_df) < 20 or "close" not in m15_df.columns:
            telemetry["reason"] = "Insufficient M15 candle data for confluence evaluation"
            return False, None, telemetry

        m15_close = float(m15_df["close"].iloc[-1])
        m15_ema20 = self.calculate_ema(m15_df["close"], 20)
        m15_ema50 = self.calculate_ema(m15_df["close"], 50)

        m15_bullish = (m15_close > m15_ema20) and (m15_ema20 > m15_ema50)
        m15_bearish = (m15_close < m15_ema20) and (m15_ema20 < m15_ema50)

        telemetry["m15"] = {
            "close": m15_close,
            "ema20": m15_ema20,
            "ema50": m15_ema50,
            "bullish": m15_bullish,
            "bearish": m15_bearish,
        }

        # Determine target direction
        target_dir: Optional[str] = None
        if direction_hint:
            target_dir = direction_hint.upper().strip()
        elif m15_bullish:
            target_dir = "BUY"
        elif m15_bearish:
            target_dir = "SELL"
        else:
            telemetry["reason"] = "M15 trend is neutral: neither bullish (close > ema20 > ema50) nor bearish (close < ema20 < ema50)"
            return False, None, telemetry

        telemetry["target_direction"] = target_dir

        # 2. Validate H1 and H4 candle data
        if h1_df is None or len(h1_df) < 20 or "close" not in h1_df.columns:
            telemetry["reason"] = "Insufficient H1 candle data for confluence evaluation"
            return False, None, telemetry

        if h4_df is None or len(h4_df) < 20 or "close" not in h4_df.columns:
            telemetry["reason"] = "Insufficient H4 candle data for confluence evaluation"
            return False, None, telemetry

        # 3. Calculate H1 and H4 EMAs
        h1_close = float(h1_df["close"].iloc[-1])
        h1_ema20 = self.calculate_ema(h1_df["close"], 20)
        h1_ema50 = self.calculate_ema(h1_df["close"], 50)

        h1_bullish = (h1_ema20 > h1_ema50) and (h1_close > h1_ema50)
        h1_bearish = (h1_ema20 < h1_ema50) and (h1_close < h1_ema50)

        h4_close = float(h4_df["close"].iloc[-1])
        h4_ema20 = self.calculate_ema(h4_df["close"], 20)
        h4_ema50 = self.calculate_ema(h4_df["close"], 50)

        h4_bullish = (h4_ema20 > h4_ema50)
        h4_bearish = (h4_ema20 < h4_ema50)

        telemetry["h1"] = {
            "close": h1_close,
            "ema20": h1_ema20,
            "ema50": h1_ema50,
            "bullish": h1_bullish,
            "bearish": h1_bearish,
        }
        telemetry["h4"] = {
            "close": h4_close,
            "ema20": h4_ema20,
            "ema50": h4_ema50,
            "bullish": h4_bullish,
            "bearish": h4_bearish,
        }

        # 4. Check confluence against target direction
        if target_dir == "BUY":
            # BUY condition:
            # M15 bullish (close > ema20 > ema50),
            # H1 bullish (h1_ema20 > h1_ema50 and h1_close > h1_ema50),
            # H4 non-bearish (not (h4_ema20 < h4_ema50))
            if not m15_bullish:
                telemetry["reason"] = "MTF trend conflict: M15 conflicts with H1/H4"
                return False, None, telemetry

            if (not h1_bullish) or h4_bearish:
                telemetry["reason"] = "MTF trend conflict: M15 conflicts with H1/H4"
                return False, None, telemetry

            telemetry["approved"] = True
            telemetry["reason"] = "Full MTF confluence: M15 bullish + H1 bullish + H4 non-bearish"
            return True, "BUY", telemetry

        elif target_dir == "SELL":
            # SELL condition:
            # M15 bearish (close < ema20 < ema50),
            # H1 bearish (h1_ema20 < h1_ema50 and h1_close < h1_ema50),
            # H4 non-bullish (not (h4_ema20 > h4_ema50))
            if not m15_bearish:
                telemetry["reason"] = "MTF trend conflict: M15 conflicts with H1/H4"
                return False, None, telemetry

            if (not h1_bearish) or h4_bullish:
                telemetry["reason"] = "MTF trend conflict: M15 conflicts with H1/H4"
                return False, None, telemetry

            telemetry["approved"] = True
            telemetry["reason"] = "Full MTF confluence: M15 bearish + H1 bearish + H4 non-bullish"
            return True, "SELL", telemetry

        else:
            telemetry["reason"] = f"Unknown direction '{target_dir}'"
            return False, None, telemetry


# Global singleton instance
trend_confluence_filter = MultiTimeframeConfluenceFilter()
