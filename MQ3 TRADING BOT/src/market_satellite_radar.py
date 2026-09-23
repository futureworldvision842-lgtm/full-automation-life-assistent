import logging
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MarketSatelliteRadar:
    """
    Market Satellite Doppler Radar & Global Financial Macro Scanner.
    Analogy to Weather Satellite Radar: Scans multi-timeframe price action grids,
    liquidity pressure fronts, and global macroeconomic storm vectors.
    """

    def __init__(self):
        self.radar_status = "ACTIVE_SATELLITE_LINK"
        logger.info("Market Satellite Doppler Radar Initialized & Scanning Orbit.")

    def scan_satellite_grid(self, df_h1: pd.DataFrame, df_m15: pd.DataFrame, symbol: str = "XAUUSD") -> Dict[str, Any]:
        """Scans multi-layer market pressure grid like satellite weather radar."""
        if (
            df_h1 is None or df_m15 is None or
            df_h1.empty or df_m15.empty or
            'close' not in df_h1.columns or
            'high' not in df_m15.columns or
            'low' not in df_m15.columns
        ):
            return {"barometric_pressure": "NEUTRAL", "storm_warning": False, "radar_score": 50.0}

        # 1. Barometric Price Pressure Differential
        h1_close = df_h1['close'].values
        h1_ema20 = pd.Series(h1_close).ewm(span=20, adjust=False).mean().values
        h1_ema50 = pd.Series(h1_close).ewm(span=50, adjust=False).mean().values

        pressure_diff = (h1_close[-1] - h1_ema50[-1]) / (h1_ema50[-1] + 1e-9) * 100.0

        if pressure_diff > 0.15:
            barometric_pressure = "HIGH_PRESSURE_UPWARD"
        elif pressure_diff < -0.15:
            barometric_pressure = "LOW_PRESSURE_DOWNWARD"
        else:
            barometric_pressure = "STABLE_ATMOSPHERE"

        # 2. Turbulence & Volatility Storm Warning (ATR & Volume Spikes)
        tr = np.abs(df_m15['high'] - df_m15['low']).values
        atr_14 = np.mean(tr[-14:]) if len(tr) >= 14 else 0.001
        recent_volatility = tr[-1]

        storm_warning = (recent_volatility > (atr_14 * 2.2))

        # 3. Radar Composite Confluence Score (0 to 100)
        score = 50.0
        if barometric_pressure == "HIGH_PRESSURE_UPWARD":
            score += 25.0
        elif barometric_pressure == "LOW_PRESSURE_DOWNWARD":
            score -= 25.0

        if storm_warning:
            logger.warning(f"[Satellite Radar Warning] VOLATILITY STORM DETECTED on {symbol}! Spike: {recent_volatility:.4f} > ATR {atr_14:.4f}")

        return {
            "symbol": symbol,
            "barometric_pressure": barometric_pressure,
            "pressure_differential_pct": round(pressure_diff, 3),
            "storm_warning": storm_warning,
            "radar_score": round(min(100.0, max(0.0, score)), 1),
            "scan_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
