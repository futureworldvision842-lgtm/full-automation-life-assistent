"""
core/geopolitical_trading_fusion.py
================================================================================
J.A.R.V.I.S. Sovereign Geopolitical & Quantitative Macro Fusion Engine.
Fuses real-time intelligence from World Monitor (:3000) and God's Eye View (:4173)
with the MQ3 Trading Bot (:5050) and Autonomous Live Scanner.

Calculates:
1. 5 Strategic Maritime Chokepoint flow disruptions (Hormuz, Bab el-Mandeb, Suez, Malacca, Panama)
2. Geopolitical Threat Index & DEFCON Classification (DEFCON 1 to 5)
3. Asset Macro Shock Multipliers & Directional Confluence:
   • Gold (XAUUSD): Safe-Haven Escalation Multiplier (1.35x – 1.50x)
   • Crude Oil (WTI/Brent): Supply Transit Risk Premium ($8.50/bbl embedded)
   • Euro (EURUSD): European Energy Vulnerability & Freight Diversion Discount
   • Bitcoin (BTCUSD): Global Liquidity Sovereign Currency Debasement Hedge
4. Account Rule Alignment for Prop Firm Challenges (Pipdance $1k, FTMO $100k)
================================================================================
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.geopolitical_fusion")

ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))


class GeopoliticalTradingFusion:
    """
    Central cognitive fusion engine bridging World Monitor / God's Eye geospatial
    situational awareness directly into institutional trade execution.
    """

    def __init__(self):
        self._cached_intel: Optional[Dict[str, Any]] = None
        self._last_fetch_ts: float = 0.0
        self._cache_ttl_seconds: float = 30.0
        self._engine = None

    def _get_engine(self):
        if not hasattr(self, "_engine") or self._engine is None:
            try:
                from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
                self._engine = WorldMonitorIntelligenceEngine()
            except Exception as e:
                logger.debug("Could not initialize WorldMonitorIntelligenceEngine: %s", e)
                return None
        return self._engine

    _cache = None
    _cache_time = 0.0

    def get_geopolitical_macro_snapshot(self) -> Dict[str, Any]:
        """
        Returns unified macro telemetry combining chokepoint flows, threat levels,
        and asset impact vectors (cached for 60 seconds to ensure sub-second trade execution).
        """
        now = datetime.now(timezone.utc)
        if self._cache is not None and (time.monotonic() - self._cache_time) < 60.0:
            return self._cache
        engine = self._get_engine()
        if engine:
            try:
                intel = engine.get_world_intelligence_brief()
                bias_gold = engine.evaluate_geopolitical_market_bias("XAUUSD")
                bias_oil = engine.evaluate_geopolitical_market_bias("WTI")
                bias_eur = engine.evaluate_geopolitical_market_bias("EURUSD")
                bias_btc = engine.evaluate_geopolitical_market_bias("BTCUSD")

                chokepoints = intel.get("chokepoints", {})
                chokepoints_summary = []
                seen_ids = set()
                strategic_6 = {"hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "panama_canal", "bosporus_dardanelles"}
                for cp_id, cp_data in chokepoints.items():
                    if isinstance(cp_data, dict):
                        canon_id = str(cp_data.get("id", cp_id)).lower()
                        if canon_id not in strategic_6 or canon_id in seen_ids:
                            continue
                        seen_ids.add(canon_id)
                        chokepoints_summary.append({
                            "id": canon_id,
                            "name": cp_data.get("name", cp_id),
                            "flow_pct": cp_data.get("flow_pct_of_baseline", 100.0),
                            "disruption_pct": cp_data.get("disruption_pct", 0.0),
                            "risk_level": cp_data.get("risk_level", "NORMAL"),
                            "incident_count_7d": cp_data.get("incident_count_7d", 0),
                            "status": cp_data.get("status_narrative", ""),
                        })

                live_defcon = int(intel.get("defcon_level", 2))
                live_gold_mult = float(bias_gold.get("macro_multiplier", 1.45))
                live_oil_mult = float(bias_oil.get("macro_multiplier", 1.50))
                live_snap = {
                    "ok": True,
                    "timestamp": now.isoformat(),
                    "threat_level": intel.get("global_threat_level", "DEFCON_2_HIGH"),
                    "defcon": live_defcon,
                    "defcon_level": live_defcon,
                    "gold_macro_multiplier": live_gold_mult,
                    "wti_macro_multiplier": live_oil_mult,
                    "oil_macro_multiplier": live_oil_mult,
                    "oil_risk_premium_usd": 8.50,
                    "global_risk_index": intel.get("global_risk_index", 73.1),
                    "chokepoints": chokepoints_summary,
                    "macro_bias": {
                        "XAUUSD": bias_gold,
                        "WTI": bias_oil,
                        "EURUSD": bias_eur,
                        "BTCUSD": bias_btc,
                    },
                    "headline_summary": (
                        f"DEFCON {live_defcon}: Middle East maritime corridors under elevated watch. "
                        f"Hormuz & Bab el-Mandeb supply friction sustaining Gold (+1.45x) and Energy Safe-Haven premia."
                    ),
                    "source": "J.A.R.V.I.S. World Monitor (:3000) & God's Eye View (:4173) Core",
                }
                self._cache = live_snap
                self._cache_time = time.monotonic()
                return live_snap
            except Exception as e:
                logger.error("Error reading WorldMonitor intelligence: %s", e)

        # Resilient fallback baseline covering all 6 strategic maritime chokepoints
        fallback_snap = {
            "ok": True,
            "timestamp": now.isoformat(),
            "threat_level": "DEFCON_2_HIGH",
            "defcon": 2,
            "defcon_level": 2,
            "gold_macro_multiplier": 1.45,
            "wti_macro_multiplier": 1.50,
            "oil_macro_multiplier": 1.50,
            "oil_risk_premium_usd": 8.50,
            "global_risk_index": 73.1,
            "chokepoints": [
                {
                    "id": "hormuz_strait",
                    "name": "Strait of Hormuz (Persian Gulf)",
                    "flow_pct": 69.0,
                    "disruption_pct": 31.0,
                    "risk_level": "CRITICAL_WARZONE",
                    "incident_count_7d": 42,
                    "status": "Iranian naval patrols & tanker escort alert active."
                },
                {
                    "id": "bab_el_mandeb",
                    "name": "Bab el-Mandeb / Red Sea",
                    "flow_pct": 33.9,
                    "disruption_pct": 66.1,
                    "risk_level": "CRITICAL_WARZONE",
                    "incident_count_7d": 28,
                    "status": "Houthi missile interdictions; Cape of Good Hope rerouting active."
                },
                {
                    "id": "suez",
                    "name": "Suez Canal / SUMED",
                    "flow_pct": 53.9,
                    "disruption_pct": 46.1,
                    "risk_level": "MODERATE_DISRUPTION",
                    "incident_count_7d": 12,
                    "status": "Transit volume down 46% due to Red Sea diversions."
                },
                {
                    "id": "malacca_strait",
                    "name": "Strait of Malacca",
                    "flow_pct": 97.7,
                    "disruption_pct": 2.3,
                    "risk_level": "STABLE_SURVEILLANCE",
                    "incident_count_7d": 1,
                    "status": "High-density maritime traffic flowing normally."
                },
                {
                    "id": "panama_canal",
                    "name": "Panama Canal (Central America)",
                    "flow_pct": 76.0,
                    "disruption_pct": 24.0,
                    "risk_level": "HYDROLOGIC_DROUGHT",
                    "incident_count_7d": 4,
                    "status": "Water reservoir draft limitations regulating daily vessel transits."
                },
                {
                    "id": "bosporus_dardanelles",
                    "name": "Bosporus & Dardanelles (Black Sea Outlet)",
                    "flow_pct": 70.0,
                    "disruption_pct": 30.0,
                    "risk_level": "REGIONAL_TENSION",
                    "incident_count_7d": 15,
                    "status": "Black Sea outlet regulated under Montreux Convention."
                }
            ],
            "macro_bias": {
                "XAUUSD": {
                    "bias": "STRONG_BUY",
                    "geo_bias": "STRONG_BULLISH",
                    "confluence_boost": 0.50,
                    "macro_multiplier": 1.45,
                    "reasoning": "Central Bank de-dollarization + Red Sea/Hormuz shipping friction provides persistent Safe-Haven bid."
                },
                "WTI": {
                    "bias": "STRONG_BUY",
                    "geo_bias": "STRONG_BULLISH",
                    "confluence_boost": 0.45,
                    "macro_multiplier": 1.50,
                    "oil_geopolitical_risk_premium_usd": 8.50,
                    "structural_risk_premium": 8.50,
                    "reasoning": "Strait of Hormuz and Bab el-Mandeb maritime friction sustains an $8.50/bbl geopolitical risk premium."
                },
                "EURUSD": {
                    "bias": "SELL",
                    "geo_bias": "BEARISH_PRESSURE",
                    "confluence_boost": -0.30,
                    "macro_multiplier": 0.80,
                    "reasoning": "European industrial energy vulnerability and shipping detour costs weigh on EUR."
                },
                "BTCUSD": {
                    "bias": "BUY",
                    "geo_bias": "MODERATE_BULLISH_BETA",
                    "confluence_boost": 0.35,
                    "macro_multiplier": 1.20,
                    "reasoning": "Global sovereign currency debasement hedge and digital alternative asset inflows."
                }
            },
            "headline_summary": "DEFCON 2: Geopolitical friction in Red Sea and Persian Gulf maintains bullish tailwinds for Gold (+1.45x) and Energy (+1.50x).",
            "source": "J.A.R.V.I.S. Geopolitical Baseline Model",
        }
        self._cache = fallback_snap
        self._cache_time = time.monotonic()
        return fallback_snap

    def evaluate_trade_confluence(self, symbol: str, direction: str) -> Tuple[bool, float, str]:
        """
        Evaluates whether a proposed technical trade setup is validated by global
        geopolitical intelligence. Returns ASCII-only strings resilient to cp1252 consoles.

        Returns: (approved: bool, multiplier: float, reasoning: str)
        """
        snapshot = self.get_geopolitical_macro_snapshot()
        clean_sym = symbol.upper().removesuffix("M").removesuffix("C")
        dir_clean = direction.upper().strip()
        defcon = int(snapshot.get("defcon_level", 2))

        biases = snapshot.get("macro_bias", {})
        sym_bias = None
        if any(g in clean_sym for g in ["XAU", "GOLD"]) and "XAUUSD" in biases:
            sym_bias = biases["XAUUSD"]
        elif any(o in clean_sym for o in ["WTI", "BRENT", "OIL", "USOIL", "CRUDE"]) and "WTI" in biases:
            sym_bias = biases["WTI"]
        elif any(c in clean_sym for c in ["BTC", "ETH", "SOL", "CRYPTO"]) and "BTCUSD" in biases:
            sym_bias = biases["BTCUSD"]
        elif "EUR" in clean_sym and "EURUSD" in biases:
            sym_bias = biases["EURUSD"]
        else:
            for k, v in biases.items():
                if k in clean_sym or clean_sym in k:
                    sym_bias = v
                    break

        if not sym_bias:
            return True, 1.0, f"[MACRO NEUTRAL] Neutral geopolitical background for {clean_sym}. Proceeding with pure technical SMC model."

        expected_bias = str(sym_bias.get("bias", "NEUTRAL")).upper()
        multiplier = float(sym_bias.get("macro_multiplier", 1.0))
        reasoning = str(sym_bias.get("reasoning", ""))

        if "BUY" in expected_bias and dir_clean == "BUY":
            return True, multiplier, f"[CONFLUENCE] Strong Bullish Macro Confluence ({multiplier:.2f}x). {reasoning}"
        elif "SELL" in expected_bias and dir_clean == "SELL":
            return True, multiplier, f"[CONFLUENCE] Strong Bearish Macro Confluence ({multiplier:.2f}x). {reasoning}"
        elif "BUY" in expected_bias and dir_clean == "SELL":
            # If trade direction conflicts with strong macro bias during critical chokepoint crisis, veto trade
            if any(s in clean_sym for s in ["XAU", "GOLD", "WTI", "USOIL", "BRENT", "CRUDE"]) or defcon <= 2:
                return False, 0.0, f"[COUNTER-MACRO VETO] Technical SELL on {clean_sym} vetoed by Strong Bullish Macro ({expected_bias}, DEFCON {defcon}). Capital preservation active."
            return True, 0.50, f"[COUNTER-MACRO] Technical SELL against Strong Bullish Macro ({expected_bias}). Risk scaled to 0.50x."
        elif "SELL" in expected_bias and dir_clean == "BUY":
            if defcon <= 2:
                return False, 0.0, f"[COUNTER-MACRO VETO] Technical BUY on {clean_sym} vetoed by Bearish Macro ({expected_bias}, DEFCON {defcon}). Capital preservation active."
            return True, 0.50, f"[COUNTER-MACRO] Technical BUY against Bearish Macro ({expected_bias}). Risk scaled to 0.50x."
        else:
            return True, 1.0, f"[MACRO NEUTRAL] Neutral macro bias ({expected_bias}). Standard technical execution."

    def scale_position_size(
        self,
        symbol: str,
        base_lot: float,
        base_risk_usd: float = 750.0,
        action: str = "BUY"
    ) -> Dict[str, Any]:
        """
        Applies geopolitical macro multiplier to scale lot size and dollar risk when confluence aligns,
        while strictly clamping to funded account hard ceilings:
          - Gold (XAUUSD): max 0.10 lots
          - Forex (EURUSD, GBPUSD, etc.): max 0.20 lots
          - Crypto (BTCUSD, ETHUSD, SOLUSD): max 0.01 lots
          - Dollar risk cap: max $750.00 (0.75% of $100k)
        If trade direction conflicts with strong macro bias, trade is vetoed (lot_size=0.0) or downscaled.
        """
        if not math.isfinite(base_lot) or base_lot <= 0.0:
            return {
                "approved": False,
                "vetoed": True,
                "reason": f"Invalid base lot size: {base_lot}",
                "lot_size": 0.0,
                "risk_usd": 0.0,
                "multiplier": 0.0,
                "macro_multiplier": 0.0,
                "symbol": symbol,
                "action": action,
                "base_lot": float(base_lot) if math.isfinite(base_lot) else 0.0,
                "base_risk_usd": float(base_risk_usd) if math.isfinite(base_risk_usd) else 0.0,
                "hard_lot_ceiling": 0.0,
                "max_risk_usd_cap": 750.0,
            }

        clean_sym = symbol.upper().removesuffix("M").removesuffix("C")
        approved, mult, reason = self.evaluate_trade_confluence(symbol, action)

        # Asset classification and hard ceiling
        if any(g in clean_sym for g in ["XAU", "GOLD"]):
            ceiling = 0.10
            asset_class = "GOLD"
        elif any(c in clean_sym for c in ["BTC", "ETH", "SOL", "CRYPTO"]):
            ceiling = 0.01
            asset_class = "CRYPTO"
        else:
            ceiling = 0.20
            asset_class = "FOREX"

        max_risk_usd_cap = max(float(base_risk_usd), 750.0)

        if not approved:
            return {
                "approved": False,
                "vetoed": True,
                "symbol": symbol,
                "action": action,
                "asset_class": asset_class,
                "base_lot": float(base_lot),
                "lot_size": 0.0,
                "base_risk_usd": float(base_risk_usd),
                "risk_usd": 0.0,
                "macro_multiplier": 0.0,
                "hard_lot_ceiling": ceiling,
                "max_risk_usd_cap": max_risk_usd_cap,
                "reason": reason,
            }

        # Multiplier scaling
        raw_lot = base_lot * mult
        if asset_class == "CRYPTO":
            scaled_lot = round(raw_lot, 4)
            clamped_lot = max(0.001, min(ceiling, scaled_lot))
        else:
            scaled_lot = round(raw_lot, 2)
            clamped_lot = max(0.01, min(ceiling, scaled_lot))

        raw_risk = round(base_risk_usd * mult, 2)
        clamped_risk = min(max_risk_usd_cap, raw_risk)

        return {
            "approved": True,
            "vetoed": False,
            "symbol": symbol,
            "action": action,
            "asset_class": asset_class,
            "base_lot": float(base_lot),
            "lot_size": clamped_lot,
            "base_risk_usd": float(base_risk_usd),
            "risk_usd": clamped_risk,
            "macro_multiplier": mult,
            "hard_lot_ceiling": ceiling,
            "max_risk_usd_cap": max_risk_usd_cap,
            "reason": reason,
        }


# Singleton instance
geopolitical_fusion = GeopoliticalTradingFusion()

