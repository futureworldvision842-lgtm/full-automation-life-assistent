import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FinceptTerminalIntel:
    """
    Fincept Terminal & Freqtrade Quantitative Intelligence Module.
    Extracted from FinceptTerminal and freqtrade repositories.
    Provides Sentiment Analysis, MACD Divergence, Bollinger Band Squeeze,
    and Freqtrade Hyperopt Signal Filters.
    """

    def __init__(self):
        self.terminal_version = "Fincept-Freqtrade-Quant-V1"
        logger.info(f"FinceptTerminal Intelligence Engine Active ({self.terminal_version}).")

    def calculate_fincept_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes Fincept & Freqtrade quantitative indicators."""
        if df.empty or len(df) < 20:
            return df

        df = df.copy()

        # 1. MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']

        # 2. Bollinger Bands (20, 2)
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = sma20 + (std20 * 2.0)
        df['bb_lower'] = sma20 - (std20 * 2.0)
        df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / sma20

        # 3. Fincept Sentiment Index (0 to 100)
        close = df['close'].iloc[-1]
        bb_u = df['bb_upper'].iloc[-1]
        bb_l = df['bb_lower'].iloc[-1]
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50.0

        if bb_u > bb_l:
            bb_pos = (close - bb_l) / (bb_u - bb_l)
            sentiment_score = (bb_pos * 50.0) + (rsi * 0.5)
        else:
            sentiment_score = 50.0

        df['fincept_sentiment'] = round(min(100.0, max(0.0, sentiment_score)), 1)
        return df

    def evaluate_quant_filters(self, df: pd.DataFrame, signal_type: str) -> Dict[str, Any]:
        """Evaluates Freqtrade-style hyperopt quant filters."""
        if df.empty or len(df) < 5:
            return {"passed": True, "confluence_boost": 0.0, "reason": "Insufficient data for quant filter"}

        latest = df.iloc[-1]
        macd_hist = latest.get("macd_hist", 0.0)
        bb_squeeze = latest.get("bb_squeeze", 0.01)

        boost = 0.0
        passed = True
        reasons = []

        if signal_type == "BUY":
            if macd_hist > 0:
                boost += 0.2
                reasons.append("MACD Bullish Histogram Alignment")
            if latest.get("close", 0) > latest.get("bb_upper", 0) * 0.998:
                boost += 0.2
                reasons.append("Fincept Upper Bollinger Breakout")
        elif signal_type == "SELL":
            if macd_hist < 0:
                boost += 0.2
                reasons.append("MACD Bearish Histogram Alignment")
            if latest.get("close", 0) < latest.get("bb_lower", 0) * 1.002:
                boost += 0.2
                reasons.append("Fincept Lower Bollinger Breakout")

        return {
            "passed": passed,
            "confluence_boost": boost,
            "reasons": reasons,
            "fincept_sentiment": latest.get("fincept_sentiment", 50.0)
        }
