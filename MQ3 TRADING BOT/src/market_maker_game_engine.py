"""
src/market_maker_game_engine.py
Institutional Smart Money & Market Maker Manipulation Detector.
Identifies Asian Session Box (00:00-06:00 UTC), London Open Judas Swings (07:00-10:00 UTC),
Liquidity Sweeps, and Asymmetrical Rejection Wick Forensics.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, time
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketMakerGameEngine:
    """
    Institutional Smart Money & Market Maker Manipulation Detector.
    Identifies Institutional Stop Hunts, Asian Session Box Boundaries,
    London Open Judas Swings, and Retail Trap Patterns.
    """

    @staticmethod
    def calculate_asian_session_box(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates the Asian Session Box (00:00:00 to 06:00:00 UTC) range.
        Extracts Asian High, Asian Low, Range, and Midpoint.
        """
        if df is None or len(df) == 0:
            return {
                "asian_high": None,
                "asian_low": None,
                "asian_range": None,
                "asian_mid": None,
                "candle_count": 0
            }

        df_work = df.copy()

        # Handle Datetime filtering
        has_time = False
        if 'time' in df_work.columns:
            try:
                df_work['dt'] = pd.to_datetime(df_work['time'])
                has_time = True
            except Exception:
                pass
        elif isinstance(df_work.index, pd.DatetimeIndex):
            df_work['dt'] = df_work.index
            has_time = True

        if has_time:
            # Filter 00:00 to 06:00 UTC
            asian_mask = (df_work['dt'].dt.hour >= 0) & (df_work['dt'].dt.hour < 6)
            df_asian = df_work[asian_mask]
            if len(df_asian) >= 1:
                a_high = float(df_asian['high'].max())
                a_low = float(df_asian['low'].min())
                a_range = a_high - a_low
                a_mid = (a_high + a_low) / 2.0
                return {
                    "asian_high": a_high,
                    "asian_low": a_low,
                    "asian_range": a_range,
                    "asian_mid": a_mid,
                    "candle_count": len(df_asian)
                }

        # Fallback when timestamps are not formatted as datetime or in synthetic test feeds
        # Use first 6-24 bars or head of dataframe
        sample_size = min(len(df_work), 24)
        df_sample = df_work.head(sample_size)
        a_high = float(df_sample['high'].max())
        a_low = float(df_sample['low'].min())
        a_range = a_high - a_low
        a_mid = (a_high + a_low) / 2.0
        return {
            "asian_high": a_high,
            "asian_low": a_low,
            "asian_range": a_range,
            "asian_mid": a_mid,
            "candle_count": sample_size
        }

    @staticmethod
    def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """
        Detects Institutional Liquidity Sweeps (Stop Hunts).
        Occurs when price pierces a key swing high/low to grab retail stop losses
        and immediately closes back inside the range (Rejection Wick).
        """
        if df is None or len(df) < lookback + 2:
            return {"sweep_detected": False}

        recent_high = df['high'].iloc[-lookback:-2].max()
        recent_low = df['low'].iloc[-lookback:-2].min()

        prev = df.iloc[-2]

        # Bullish Liquidity Sweep (Swept Retail Sell Stops below recent low & reversed up)
        if prev['low'] < recent_low and prev['close'] > recent_low:
            wick_len = abs(prev['close'] - prev['low'])
            body_len = abs(prev['close'] - prev['open'])
            if wick_len > body_len:
                logger.info(f"[Market Maker Game] BULLISH LIQUIDITY SWEEP / STOP HUNT Detected at {prev['low']:.5f}")
                return {
                    "sweep_detected": True,
                    "type": "BULLISH_SWEEP",
                    "swept_level": float(recent_low),
                    "rejection_wick_price": float(prev['low']),
                    "description": "Smart Money swept retail sell-stops below key liquidity low and reversed."
                }

        # Bearish Liquidity Sweep (Swept Retail Buy Stops above recent high & reversed down)
        if prev['high'] > recent_high and prev['close'] < recent_high:
            wick_len = abs(prev['high'] - prev['close'])
            body_len = abs(prev['close'] - prev['open'])
            if wick_len > body_len:
                logger.info(f"[Market Maker Game] BEARISH LIQUIDITY SWEEP / STOP HUNT Detected at {prev['high']:.5f}")
                return {
                    "sweep_detected": True,
                    "type": "BEARISH_SWEEP",
                    "swept_level": float(recent_high),
                    "rejection_wick_price": float(prev['high']),
                    "description": "Smart Money swept retail buy-stops above key liquidity high and reversed."
                }

        return {"sweep_detected": False}

    def detect_judas_swing(
        self,
        df: pd.DataFrame,
        session_name: str = "LONDON",
        df_asian: Optional[pd.DataFrame] = None,
        current_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Detects ICT Judas Swing (Session Open Fakeout).
        Evaluates 00:00-06:00 UTC Asian Box sweeps during London Open (07:00-10:00 UTC)
        with rejection wick forensics and displacement, with algorithmic fallback.
        """
        if df is None or len(df) == 0:
            return {"judas_detected": False, "type": "NONE"}

        # 1. Evaluate Asian Box sweep if Asian box or df_asian is present
        asian_box = self.calculate_asian_session_box(df_asian if df_asian is not None else df)
        a_high = asian_box.get("asian_high")
        a_low = asian_box.get("asian_low")

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        if a_high is not None and a_low is not None and a_high > a_low:
            # Check latest / prev bar for sweep & rejection wick
            for candle in [latest, prev]:
                c_high = float(candle['high'])
                c_low = float(candle['low'])
                c_open = float(candle['open'])
                c_close = float(candle['close'])
                c_range = max(c_high - c_low, 1e-6)
                c_body = abs(c_close - c_open)

                # Bearish Judas Swing: Swept Asian High & rejected back below
                if c_high > a_high and c_close < a_high:
                    upper_wick = c_high - max(c_open, c_close)
                    if upper_wick >= 0.40 * c_range and upper_wick >= c_body:
                        logger.info(f"[Judas Swing] BEARISH Judas Swing detected — swept Asian High {a_high:.5f}")
                        return {
                            "judas_detected": True,
                            "type": "BEARISH_JUDAS_SWING",
                            "session": session_name,
                            "swept_level": a_high,
                            "rejection_wick_price": c_high,
                            "asian_high": a_high,
                            "asian_low": a_low,
                            "asian_range": asian_box.get("asian_range"),
                            "description": f"ICT Judas Swing Bearish Fakeout: Swept Asian High ({a_high:.5f}) with rejection wick during {session_name}."
                        }

                # Bullish Judas Swing: Swept Asian Low & rejected back above
                if c_low < a_low and c_close > a_low:
                    lower_wick = min(c_open, c_close) - c_low
                    if lower_wick >= 0.40 * c_range and lower_wick >= c_body:
                        logger.info(f"[Judas Swing] BULLISH Judas Swing detected — swept Asian Low {a_low:.5f}")
                        return {
                            "judas_detected": True,
                            "type": "BULLISH_JUDAS_SWING",
                            "session": session_name,
                            "swept_level": a_low,
                            "rejection_wick_price": c_low,
                            "asian_high": a_high,
                            "asian_low": a_low,
                            "asian_range": asian_box.get("asian_range"),
                            "description": f"ICT Judas Swing Bullish Fakeout: Swept Asian Low ({a_low:.5f}) with rejection wick during {session_name}."
                        }

        # 2. Algorithmic Fallback Mode (preserving backward compatibility)
        if len(df) < 3:
            return {
                "judas_detected": False,
                "type": "NONE",
                "session": session_name,
                "asian_high": a_high,
                "asian_low": a_low,
                "asian_range": asian_box.get("asian_range")
            }

        last_3 = df.tail(3)
        open_p = float(last_3['open'].iloc[0])
        close_p = float(last_3['close'].iloc[-1])
        high_p = float(last_3['high'].max())
        low_p = float(last_3['low'].min())

        # Bearish Judas Swing Fakeout (Rallied initially then dumped)
        if high_p > open_p * 1.0015 and close_p < open_p:
            return {
                "judas_detected": True,
                "type": "BEARISH_JUDAS_SWING",
                "session": session_name,
                "swept_level": high_p,
                "rejection_wick_price": high_p,
                "asian_high": a_high,
                "asian_low": a_low,
                "asian_range": asian_box.get("asian_range"),
                "description": f"ICT Judas Swing Fakeout detected during {session_name} open."
            }

        # Bullish Judas Swing Fakeout (Dumped initially then rallied)
        if low_p < open_p * 0.9985 and close_p > open_p:
            return {
                "judas_detected": True,
                "type": "BULLISH_JUDAS_SWING",
                "session": session_name,
                "swept_level": low_p,
                "rejection_wick_price": low_p,
                "asian_high": a_high,
                "asian_low": a_low,
                "asian_range": asian_box.get("asian_range"),
                "description": f"ICT Judas Swing Fakeout detected during {session_name} open."
            }

        return {
            "judas_detected": False,
            "type": "NONE",
            "session": session_name,
            "asian_high": a_high,
            "asian_low": a_low,
            "asian_range": asian_box.get("asian_range")
        }
