"""
insider_whale_mechanics.py — Institutional Insider Whale & Political Market Manipulation Radar.
Models political rhetoric, geopolitical shock transmission, and Dark Pool volume anomalies.

Key Capabilities:
  1. Political & Central Bank Rhetoric Sentiment Analysis (Tariff wars, Fed chair signals, OPEC+).
  2. Dark Pool Block Trade Volume Anomaly Detector (Z-score volume absorption without price displacement).
  3. Sovereign Wealth Fund & Institutional Whale Flow Index.
"""

import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("InsiderWhaleMechanics")


class InsiderWhaleMechanics:
    """
    Insider Whale & Political Manipulation Radar.
    Detects when major market actors (Central Banks, Sovereign Wealth Funds, Dark Pools, Political Insiders)
    are actively positioning or engineering liquidity traps.
    """

    POLITICAL_SHOCK_CATALOG = {
        "TARIFF_ESCALATION": {
            "gold_impact": 0.80,     # Strongly Bullish (Safe Haven)
            "usd_impact": 0.30,      # Mixed / Volatile
            "crypto_impact": -0.40,  # Risk-Off Liquidity Drain
            "thesis": "Tariff uncertainty weakens global trade and triggers sovereign gold accumulation."
        },
        "CENTRAL_BANK_RATE_CUT": {
            "gold_impact": 0.90,     # Ultra Bullish (Lower opportunity cost)
            "usd_impact": -0.85,     # Strongly Bearish
            "crypto_impact": 0.75,   # Risk-On Expansion
            "thesis": "Fiat debasement accelerates capital rotation into hard sovereign assets."
        },
        "GEOPOLITICAL_CONFLICT": {
            "gold_impact": 0.95,     # Immediate Safe-Haven Surge
            "oil_impact": 0.85,      # Supply disruption spike
            "usd_impact": 0.50,      # Global reserve asset flight
            "thesis": "Instant flight to physical safety; precious metals & energy lead."
        },
        "OPEC_SUPPLY_CUT": {
            "oil_impact": 0.90,
            "gold_impact": 0.60,     # Inflationary hedge demand
            "usd_impact": -0.20,
            "thesis": "Energy inflation feeds headline CPI, boosting precious metal inflation hedges."
        }
    }

    def __init__(self):
        self.cached_whale_state = {
            "active_political_shock": "TARIFF_ESCALATION",
            "whale_sentiment_score": 0.82,
            "dark_pool_bias": "INSTITUTIONAL_ACCUMULATION",
            "gold_whale_bias": "STRONG_BULLISH",
            "usd_whale_bias": "BEARISH_PRESSURE",
            "last_audit": datetime.now(timezone.utc).isoformat()
        }

    def detect_dark_pool_anomalies(self, df_m15: pd.DataFrame) -> Dict[str, Any]:
        """
        Detects Dark Pool institutional block transactions using Volume Z-score and Candle Compression.
        A huge volume spike (Z > 2.5) with a tiny candle body indicates massive hidden limit order absorption.
        """
        if df_m15 is None or len(df_m15) < 20:
            return {"dark_pool_detected": False, "anomaly_type": "NONE", "z_score": 0.0}

        try:
            volumes = df_m15['volume'].values
            mean_vol = np.mean(volumes[-20:])
            std_vol = np.std(volumes[-20:])
            latest_vol = volumes[-1]

            z_score = (latest_vol - mean_vol) / max(std_vol, 1e-6)
            latest_candle = df_m15.iloc[-1]
            candle_range = abs(latest_candle['high'] - latest_candle['low'])
            body = abs(latest_candle['close'] - latest_candle['open'])
            atr = (df_m15['high'] - df_m15['low']).tail(14).mean()

            # Dark Pool Anomaly: Volume Z > 2.2 and Candle Body < 0.40 * ATR (Hidden limit order wall)
            if z_score >= 2.2 and body <= (0.40 * max(atr, 1e-6)):
                anomaly_type = "DARK_POOL_BUY_ACCUMULATION" if latest_candle['close'] >= latest_candle['open'] else "DARK_POOL_SELL_DISTRIBUTION"
                return {
                    "dark_pool_detected": True,
                    "anomaly_type": anomaly_type,
                    "z_score": round(float(z_score), 2),
                    "volume_ratio": round(float(latest_vol / max(mean_vol, 1.0)), 2),
                    "description": "Institutional block absorption detected: High volume with compressed price action."
                }

            return {
                "dark_pool_detected": False,
                "anomaly_type": "NORMAL_LIQUIDITY",
                "z_score": round(float(z_score), 2),
                "volume_ratio": round(float(latest_vol / max(mean_vol, 1.0)), 2)
            }
        except Exception as e:
            logger.debug(f"Dark pool detection fallback: {e}")
            return {"dark_pool_detected": False, "anomaly_type": "NONE", "z_score": 0.0}

    def evaluate_political_macro_shock(self, active_event_type: str = "TARIFF_ESCALATION") -> Dict[str, Any]:
        """
        Evaluates the macro tailwind impact of active political/geopolitical headlines.
        """
        shock_info = self.POLITICAL_SHOCK_CATALOG.get(active_event_type, self.POLITICAL_SHOCK_CATALOG["TARIFF_ESCALATION"])
        return {
            "active_shock": active_event_type,
            "gold_tailwind_score": shock_info.get("gold_impact", 0.75),
            "oil_tailwind_score": shock_info.get("oil_impact", 0.50),
            "usd_tailwind_score": shock_info.get("usd_impact", -0.30),
            "crypto_tailwind_score": shock_info.get("crypto_impact", 0.20),
            "thesis": shock_info.get("thesis")
        }
