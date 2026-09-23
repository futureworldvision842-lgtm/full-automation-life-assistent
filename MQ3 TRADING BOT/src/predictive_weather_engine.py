"""
predictive_weather_engine.py — Market Weather Predictive Forecasting Engine.
Synthesizes satellite Doppler radar scans, multi-timeframe price momentum,
geopolitical DEFCON risk states, and live economic news circuit breakers into
atmospheric market weather regimes.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from src.market_satellite_radar import MarketSatelliteRadar
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from src.economic_calendar_radar import EconomicCalendarRadar

logger = logging.getLogger(__name__)


class PredictiveWeatherEngine:
    """
    Market Weather Predictive Forecasting Engine.
    Uses Weather Satellite Radar principles, Geopolitical Threat Vectors, and News Lockout Matrices
    to generate 1-4 hour probabilistic market weather forecasts:
      - CYCLONE_NEWS_LOCKOUT
      - HURRICANE_RISK_OFF
      - THUNDERSTORM_VOLATILITY
      - SUNNY_BULLISH_UPDRAFT
      - STORMY_BEARISH_DOWNDRAFT
      - FOGGY_LIQUIDITY_TRAP
    """

    def __init__(
        self,
        world_monitor: Optional[WorldMonitorIntelligenceEngine] = None,
        calendar_radar: Optional[EconomicCalendarRadar] = None,
        satellite_radar: Optional[MarketSatelliteRadar] = None
    ):
        self.radar = satellite_radar or MarketSatelliteRadar()
        self.world_monitor = world_monitor or WorldMonitorIntelligenceEngine()
        self.calendar_radar = calendar_radar or EconomicCalendarRadar()
        logger.info("[PredictiveWeatherEngine] Initialized with Doppler Radar, WorldMonitor Geopolitics & News Circuit Breaker Fusion.")

    def forecast_market_weather(
        self,
        *args,
        symbol: Optional[str] = None,
        df_h1: Optional[pd.DataFrame] = None,
        df_m15: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Interface Contract 3:
        Generates real-time probabilistic market weather forecast.
        Supports both signatures:
          1. forecast_market_weather("XAUUSD")
          2. forecast_market_weather(df_h1, df_m15, symbol="XAUUSD")
        """
        # Flexible argument unpacking
        if len(args) == 1 and isinstance(args[0], str):
            target_symbol = args[0]
        elif len(args) >= 2 and isinstance(args[0], (pd.DataFrame, type(None))) and isinstance(args[1], (pd.DataFrame, type(None))):
            df_h1 = args[0]
            df_m15 = args[1]
            target_symbol = args[2] if len(args) >= 3 and isinstance(args[2], str) else (symbol or "XAUUSD")
        else:
            target_symbol = symbol or "XAUUSD"

        target_symbol = target_symbol.upper()

        if df_h1 is None:
            df_h1 = pd.DataFrame()
        if df_m15 is None:
            df_m15 = pd.DataFrame()

        # 1. Satellite Radar Grid Scan
        radar_scan = self.radar.scan_satellite_grid(df_h1, df_m15, symbol=target_symbol)
        radar_score = float(radar_scan.get("radar_score", 50.0))
        storm_warning = bool(radar_scan.get("storm_warning", False))
        pressure_diff = float(radar_scan.get("pressure_differential_pct", 0.0))
        barometric_pressure_hpa = round(1013.25 + (pressure_diff * 10.0), 2)

        # 2. Geopolitical Macro Brief & DEFCON State
        intel_brief = self.world_monitor.get_world_intelligence_brief()
        defcon_level = int(intel_brief.get("defcon_level", 3))
        global_risk_index = float(intel_brief.get("global_risk_index", 74.8))
        geo_bias = self.world_monitor.get_geopolitical_market_bias(target_symbol)

        # 3. Live Economic Calendar News Clearance
        news_clearance = self.calendar_radar.evaluate_news_clearance(target_symbol, check_weekend=False)
        is_news_blackout = bool(
            news_clearance.get("active_event") is not None or
            "PRE_NEWS" in news_clearance.get("lockout_reason", "") or
            "POST_NEWS" in news_clearance.get("lockout_reason", "")
        )

        # 4. Momentum & Volatility from Candlesticks (if provided)
        if not df_m15.empty and len(df_m15) >= 10 and 'close' in df_m15.columns:
            closes = df_m15['close'].values
            ret = np.diff(closes) / (closes[:-1] + 1e-9)
            mean_ret = float(np.mean(ret[-10:]))
            mom_component = mean_ret * 12000.0
            radar_component = (radar_score - 50.0) * 0.8
            raw_updraft = 50.0 + mom_component + radar_component
            updraft_prob = min(92.0, max(8.0, raw_updraft))
            downdraft_prob = 100.0 - updraft_prob
        else:
            # Seed probabilistic updraft from macro geopolitical bias & radar score
            if geo_bias.get("bias") in ["STRONG_BUY", "STRONG_BULLISH"]:
                updraft_prob = min(88.0, 68.0 + ((radar_score - 50.0) * 0.3))
            elif geo_bias.get("bias") in ["SELL", "STRONG_SELL"]:
                updraft_prob = max(12.0, 32.0 + ((radar_score - 50.0) * 0.3))
            else:
                updraft_prob = min(85.0, max(15.0, radar_score))
            downdraft_prob = round(100.0 - updraft_prob, 1)

        # ══════════════════════════════════════════════════════════════════════
        # 5. ATMOSPHERIC REGIME CLASSIFICATION ENGINE
        # ══════════════════════════════════════════════════════════════════════

        # Tier 1: CYCLONE_NEWS_LOCKOUT (Highest Priority Overrides All)
        if is_news_blackout:
            weather_state = "CYCLONE_NEWS_LOCKOUT"
            risk_multiplier = 0.0
            trade_policy = "Trading Strictly Halted / Entries Blocked"
            advisory = f"Active High-Impact News Circuit Breaker: {news_clearance.get('lockout_reason')}. Capital preservation locked."
            summary = "CYCLONE WARNING: Market entering blackout window for high-impact macroeconomic announcement."

        # Tier 2: HURRICANE_RISK_OFF (Geopolitical Emergency DEFCON 1 or 2 with extreme risk)
        elif defcon_level <= 2 or global_risk_index >= 80.0:
            weather_state = "HURRICANE_RISK_OFF"
            clean_sym = target_symbol.upper()
            if "XAU" in clean_sym or "GOLD" in clean_sym or "WTI" in clean_sym or "BRENT" in clean_sym:
                risk_multiplier = 1.50
                trade_policy = "Execute Safe-Haven BUY (Gold/Oil), Block Pro-cyclical FX"
                advisory = f"DEFCON {defcon_level} Geopolitical Hurricane Alert. Extreme safe-haven bids active across commodities."
            elif "EUR" in clean_sym or "GBP" in clean_sym or "AUD" in clean_sym:
                risk_multiplier = 0.50
                trade_policy = "Defensive Stance. Block long FX entries during macro shockwave."
                advisory = f"DEFCON {defcon_level} Risk-Off shockwave. Pro-cyclical FX under heavy macro drag."
            else:
                risk_multiplier = 0.65
                trade_policy = "Tighten Stops to Break-Even / Capital Shield"
                advisory = f"DEFCON {defcon_level} Hurricane Volatility. Conservative execution mandatory."
            summary = f"HURRICANE RISK-OFF: Global DEFCON {defcon_level} geopolitical shockwave. Capital flight to safe havens."

        # Tier 3: THUNDERSTORM_VOLATILITY (Satellite Storm / High ATR Turbulence)
        elif storm_warning or (defcon_level == 3 and abs(pressure_diff) > 0.35):
            weather_state = "THUNDERSTORM_VOLATILITY"
            risk_multiplier = 0.75
            trade_policy = "Require 50% FVG / Judas Sweep confirmation before entry"
            advisory = "Thunderstorm volatility detected. Liquidity sweeps and wide stop hunting active."
            summary = "THUNDERSTORM: Heavy atmospheric turbulence. High-probability liquidity hunt in progress."

        # Tier 4: SUNNY_BULLISH_UPDRAFT (Strong Updraft & Bullish Momentum)
        elif updraft_prob >= 65.0:
            weather_state = "SUNNY_BULLISH_UPDRAFT"
            risk_multiplier = 1.30
            trade_policy = "MODEL_HYPOTHESIS_ONLY"
            advisory = "The price-momentum model leans upward; this is not participant attribution or an execution instruction."
            summary = "MODEL HYPOTHESIS: Upward momentum regime; source provenance is required before operational use."

        # Tier 5: STORMY_BEARISH_DOWNDRAFT (Strong Downdraft & Bearish Momentum)
        elif downdraft_prob >= 65.0:
            weather_state = "STORMY_BEARISH_DOWNDRAFT"
            risk_multiplier = 1.30
            trade_policy = "MODEL_HYPOTHESIS_ONLY"
            advisory = "The price-momentum model leans downward; this is not participant attribution or an execution instruction."
            summary = "MODEL HYPOTHESIS: Downward momentum regime; source provenance is required before operational use."

        # Tier 6: FOGGY_LIQUIDITY_TRAP (Consolidation & Range Chop)
        else:
            weather_state = "FOGGY_LIQUIDITY_TRAP"
            risk_multiplier = 0.50
            trade_policy = "Range Scalping Only / Tight SL at Asian Highs/Lows"
            advisory = "Consolidation fog. Low momentum liquidity chop."
            summary = "FOGGY LIQUIDITY TRAP: Range-bound consolidation atmosphere. Asian box range scalp."

        logger.info(
            f"[PredictiveWeatherEngine] {target_symbol}: research-only State={weather_state} | "
            f"Updraft={updraft_prob:.1f}% | Downdraft={downdraft_prob:.1f}% | "
            f"ModelMultiplier={risk_multiplier:.2f}x | ExecutionMultiplier=0.00x | actionable=False"
        )

        # This legacy fusion engine does not yet receive typed, freshness-checked
        # provenance envelopes.  Its numeric result is therefore research-only
        # and must never increase size or authorize an order.  The central live
        # path uses TradeAdmissionGate and SignalQualityGate independently.
        model_risk_multiplier = round(risk_multiplier, 2)
        return {
            "symbol": target_symbol,
            "data_mode": "MODEL_HYPOTHESIS",
            "actionable": False,
            "source": None,
            "observed_at": None,
            "weather_state": weather_state,
            "weather_category": weather_state,  # backward compatibility
            "updraft_probability": round(updraft_prob, 1),
            "updraft_probability_pct": round(updraft_prob, 1),  # backward compatibility
            "downdraft_probability": round(downdraft_prob, 1),
            "downdraft_probability_pct": round(downdraft_prob, 1),  # backward compatibility
            "barometric_pressure_hpa": barometric_pressure_hpa,
            "model_risk_multiplier": model_risk_multiplier,
            "risk_multiplier": 0.0,
            "strategy_weight_multiplier": 0.0,
            "trade_policy": "RESEARCH_ONLY_NO_EXECUTION",
            "advisory": f"UNVERIFIED MODEL — {advisory}",
            "forecast_summary": summary,
            "radar_scan": radar_scan,
            "geopolitical_intel": {
                "threat_level": intel_brief.get("global_threat_level", "ELEVATED_DEFCON_3"),
                "defcon_level": defcon_level,
                "global_risk_index": global_risk_index
            },
            "news_clearance": news_clearance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
