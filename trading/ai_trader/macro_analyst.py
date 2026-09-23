"""
trading/ai_trader/macro_analyst.py — Macro Quantitative Analyst Agent
=============================================================================
Ingests macroeconomic catalysts, World Monitor geospatial intelligence (:3000),
5 Strategic Maritime Chokepoints (Hormuz, Bab el-Mandeb, Suez, Malacca, Taiwan Strait),
4-Pillar Country Instability Index (CII), DEFCON levels 1-5, DXY trend, real yields,
and 15-minute economic news blackout buffers.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import logging
from typing import Dict, Any, Optional
from trading.ai_trader.types import MacroVerdict, MacroRegime

logger = logging.getLogger("MacroQuantitativeAnalyst")


class MacroQuantitativeAnalyst:
    """
    Macro Quantitative Analyst virtual agent.
    Synthesizes macroeconomic regimes, monetary trends, geopolitical chokepoint shocks,
    and high-impact news blackout tripwires into a structured MacroVerdict.
    """

    def __init__(self, world_monitor_engine=None):
        self.wm_engine = world_monitor_engine
        if self.wm_engine is None:
            try:
                from MQ3_TRADING_BOT.src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
                self.wm_engine = WorldMonitorIntelligenceEngine()
            except Exception:
                try:
                    import importlib.util
                    from pathlib import Path
                    p = Path(__file__).resolve().parent.parent.parent / "MQ3 TRADING BOT" / "src" / "world_monitor_intelligence_engine.py"
                    if p.exists():
                        spec = importlib.util.spec_from_file_location("wm_engine_mod", str(p))
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        self.wm_engine = mod.WorldMonitorIntelligenceEngine()
                except Exception:
                    self.wm_engine = None

    def evaluate(self, symbol: str, datahub_snapshot: Optional[Dict[str, Any]] = None) -> MacroVerdict:
        """
        Evaluates institutional macro backdrop for the target symbol.
        Handles offline/timeout gracefully returning a safe neutral/resilient fallback.
        """
        sym = symbol.upper().strip()
        datahub = datahub_snapshot or {}

        # 1. 15-Minute News Circuit Breaker Check
        news_lockout = bool(
            datahub.get("news_lockout_active") or
            datahub.get("news_blackout") or
            (datahub.get("macro_state", {}).get("news_lockout_active") if isinstance(datahub.get("macro_state"), dict) else False)
        )
        news_event = datahub.get("news_event_name") or datahub.get("macro_state", {}).get("news_event_name") if isinstance(datahub.get("macro_state"), dict) else None

        # 2. Ingest World Monitor Geopolitical Telemetry
        wm_intel = None
        if self.wm_engine is not None:
            try:
                if hasattr(self.wm_engine, "get_world_intelligence_brief"):
                    wm_intel = self.wm_engine.get_world_intelligence_brief()
                elif hasattr(self.wm_engine, "snapshot"):
                    wm_intel = self.wm_engine.snapshot()
            except Exception as e:
                logger.warning(f"World Monitor query failed: {e}. Falling back to default baseline.")
                wm_intel = None

        # Extract or simulate chokepoint and defcon vitals
        defcon_level = 3
        geo_risk_score = 50.0
        chokepoints = {}
        if isinstance(wm_intel, dict):
            defcon_level = int(wm_intel.get("defcon_level", 3))
            geo_risk_score = float(wm_intel.get("global_composite_risk_index", 50.0))
            chokepoints = wm_intel.get("chokepoints", {})
        elif "macro_state" in datahub and isinstance(datahub["macro_state"], dict):
            ms = datahub["macro_state"]
            defcon_level = int(ms.get("defcon_level", 3))
            geo_risk_score = float(ms.get("geopolitical_risk_score", 50.0))
            chokepoints = ms.get("chokepoints", {})

        # Evaluate Chokepoint Disruption
        hormuz_disruption = 0.0
        bab_disruption = 0.0
        if "hormuz_strait" in chokepoints:
            hormuz_disruption = float(chokepoints["hormuz_strait"].get("disruption_pct", 0.0))
        if "bab_el_mandeb" in chokepoints:
            bab_disruption = float(chokepoints["bab_el_mandeb"].get("disruption_pct", 0.0))

        # Check explicit flags from datahub or tests
        chokepoint_shock = (
            hormuz_disruption >= 25.0 or
            bab_disruption >= 25.0 or
            defcon_level <= 2 or
            bool(datahub.get("chokepoint_shock", False))
        )

        # 3. Monetary & Currency Dynamics (DXY & Yields)
        dxy_trend = str(datahub.get("dxy_trend", "RANGE")).upper()
        dxy_val = datahub.get("dxy_value")
        if dxy_val is not None:
            try:
                if float(dxy_val) > 105.0:
                    dxy_trend = "BULLISH"
                elif float(dxy_val) < 100.0:
                    dxy_trend = "BEARISH"
            except (ValueError, TypeError):
                pass

        # 4. Synthesize Bias and Conviction per Asset Class
        bias = "NEUTRAL"
        conviction = 0.60
        macro_regime = MacroRegime.BALANCED_RANGE.value
        macro_multiplier = 1.0
        rationale_parts = []

        # Gold (XAUUSD) Assessment
        if any(k in sym for k in ["XAU", "GOLD"]):
            macro_multiplier = 1.0 + (hormuz_disruption * 0.01 * 0.5) + ((5 - defcon_level) * 0.10)
            if chokepoint_shock:
                bias = "BULLISH"
                conviction = min(0.95, 0.70 + (5 - defcon_level) * 0.08)
                macro_regime = MacroRegime.GEOPOLITICAL_FLIGHT_TO_SAFETY.value
                macro_multiplier = max(1.35, macro_multiplier)
                rationale_parts.append(f"Geopolitical shock / DEFCON {defcon_level} triggered safe-haven gold bid (Multiplier: {macro_multiplier:.2f}x).")
            elif dxy_trend == "BEARISH":
                bias = "BULLISH"
                conviction = 0.78
                macro_regime = MacroRegime.LIQUIDITY_EXPANSION.value
                rationale_parts.append("DXY weakness driving precious metals expansion.")
            elif dxy_trend == "BULLISH":
                bias = "BEARISH"
                conviction = 0.72
                macro_regime = MacroRegime.RISK_OFF_CONTRACTION.value
                rationale_parts.append("Rising DXY real yields creating headwinds for non-yielding bullion.")
            else:
                bias = "NEUTRAL"
                conviction = 0.50
                macro_regime = MacroRegime.BALANCED_RANGE.value
                rationale_parts.append("Gold in balanced macro consolidation.")

        # Forex Majors Assessment (EURUSD, GBPUSD)
        elif any(k in sym for k in ["EUR", "GBP", "USD", "JPY", "AUD"]):
            if dxy_trend == "BULLISH":
                # Strong dollar imparts bearish bias on EURUSD / GBPUSD
                bias = "BEARISH"
                conviction = 0.82
                macro_regime = MacroRegime.RISK_OFF_CONTRACTION.value
                rationale_parts.append(f"DXY index trending bullish imparts persistent downward pressure on {sym}.")
            elif dxy_trend == "BEARISH":
                bias = "BULLISH"
                conviction = 0.80
                macro_regime = MacroRegime.LIQUIDITY_EXPANSION.value
                rationale_parts.append(f"DXY index trending bearish fuels expansion across FX majors ({sym}).")
            else:
                bias = "NEUTRAL"
                conviction = 0.50
                macro_regime = MacroRegime.BALANCED_RANGE.value
                rationale_parts.append(f"{sym} range-bound; Dollar Index consolidating in neutral channel.")

        # Crypto Majors Assessment (BTC, ETH, SOL)
        elif any(k in sym for k in ["BTC", "ETH", "SOL", "CRYPTO"]):
            if chokepoint_shock and defcon_level <= 2:
                # Acute war shock initially causes risk-off liquidity pull in crypto
                bias = "BEARISH"
                conviction = 0.70
                macro_regime = MacroRegime.RISK_OFF_CONTRACTION.value
                rationale_parts.append("Acute geopolitical conflict triggered liquidity contraction across risk assets.")
            elif dxy_trend == "BEARISH":
                bias = "BULLISH"
                conviction = 0.85
                macro_regime = MacroRegime.LIQUIDITY_EXPANSION.value
                rationale_parts.append("Global liquidity expansion and dollar softening fueling crypto rally.")
            else:
                bias = "NEUTRAL"
                conviction = 0.50
                macro_regime = MacroRegime.BALANCED_RANGE.value
                rationale_parts.append("Crypto majors moving in line with local order flow dynamics.")

        else:
            bias = "NEUTRAL"
            conviction = 0.50
            macro_regime = MacroRegime.BALANCED_RANGE.value
            rationale_parts.append(f"Standard macro baseline applied to {sym}.")

        if news_lockout:
            rationale_parts.append("WARNING: High-impact economic news window active within 15 minutes.")

        rationale = " ".join(rationale_parts)

        return MacroVerdict(
            symbol=sym,
            bias=bias,
            conviction=round(conviction, 2),
            macro_regime=macro_regime,
            defcon_level=defcon_level,
            geopolitical_risk_score=round(geo_risk_score, 1),
            macro_multiplier=round(macro_multiplier, 2),
            news_lockout_active=news_lockout,
            news_event_name=news_event,
            dxy_trend=dxy_trend,
            dxy_correlation=-0.85 if "XAU" in sym or "EUR" in sym else -0.50,
            rationale=rationale
        )
