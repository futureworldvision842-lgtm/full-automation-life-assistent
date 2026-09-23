import logging
from typing import Dict, List, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ChartPatternEngine:
    """
    Advanced Multi-Chart & Candlestick Pattern Recognition Engine.
    Detects Pinbars, Engulfing Candles, Double Tops/Bottoms, and Breaker Blocks.
    """

    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> Dict[str, Any]:
        """Detects high-probability candlestick patterns on recent bars."""
        patterns = []
        if len(df) < 3:
            return {"patterns": patterns}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        body = abs(latest['close'] - latest['open'])
        candle_range = latest['high'] - latest['low']
        upper_wick = latest['high'] - max(latest['open'], latest['close'])
        lower_wick = min(latest['open'], latest['close']) - latest['low']

        # 1. Bullish Pinbar / Hammer
        if candle_range > 0 and (lower_wick / candle_range) >= 0.60:
            patterns.append({
                "type": "BULLISH_PINBAR",
                "bias": "BULLISH",
                "confidence": 0.85,
                "description": "Bullish Pinbar / Rejection Hammer showing heavy buying pressure at low."
            })

        # 2. Bearish Pinbar / Shooting Star
        if candle_range > 0 and (upper_wick / candle_range) >= 0.60:
            patterns.append({
                "type": "BEARISH_PINBAR",
                "bias": "BEARISH",
                "confidence": 0.85,
                "description": "Bearish Pinbar / Shooting Star showing heavy selling pressure at high."
            })

        # 3. Bullish Engulfing
        if prev['close'] < prev['open'] and latest['close'] > latest['open']:
            if latest['close'] >= prev['open'] and latest['open'] <= prev['close']:
                patterns.append({
                    "type": "BULLISH_ENGULFING",
                    "bias": "BULLISH",
                    "confidence": 0.80,
                    "description": "Bullish Engulfing candle completely swallowing previous bearish candle."
                })

        # 4. Bearish Engulfing
        if prev['close'] > prev['open'] and latest['close'] < latest['open']:
            if latest['close'] <= prev['open'] and latest['open'] >= prev['close']:
                patterns.append({
                    "type": "BEARISH_ENGULFING",
                    "bias": "BEARISH",
                    "confidence": 0.80,
                    "description": "Bearish Engulfing candle completely swallowing previous bullish candle."
                })

        return {"patterns": patterns}

    @staticmethod
    def detect_double_top_bottom(df: pd.DataFrame, window: int = 30) -> Dict[str, Any]:
        """Detects Double Top and Double Bottom chart structural patterns."""
        if len(df) < window:
            return {"structure_pattern": None}

        sub = df.tail(window)
        highs = sub['high'].values
        lows = sub['low'].values

        # Double Bottom Detection
        min1_idx = np.argmin(lows[:window//2])
        min2_idx = np.argmin(lows[window//2:]) + window//2
        if abs(lows[min1_idx] - lows[min2_idx]) / lows[min1_idx] < 0.0015:
            return {
                "structure_pattern": "DOUBLE_BOTTOM",
                "bias": "BULLISH",
                "support_level": (lows[min1_idx] + lows[min2_idx]) / 2,
                "description": "Double Bottom support structural reversal pattern."
            }

        # Double Top Detection
        max1_idx = np.argmax(highs[:window//2])
        max2_idx = np.argmax(highs[window//2:]) + window//2
        if abs(highs[max1_idx] - highs[max2_idx]) / highs[max1_idx] < 0.0015:
            return {
                "structure_pattern": "DOUBLE_TOP",
                "bias": "BEARISH",
                "resistance_level": (highs[max1_idx] + highs[max2_idx]) / 2,
                "description": "Double Top resistance structural reversal pattern."
            }

        return {"structure_pattern": None}
