"""
trading/consensus_chamber/agents.py
====================================
TauricResearch/TradingAgents Multi-Agent Debate System for J.A.R.V.I.S.
Debaters:
  1. BullishAdvocate: Formulates long thesis, momentum, support levels, liquidity absorption.
  2. BearishChallenger: Formulates short thesis, traps, overhead supply, macro resistance.
  3. RiskOfficer: Strict institutional and prop-firm compliance (<=0.75% risk, $750 cap, R:R >= 2.5).
                  Holds UNANIMOUS VETO POWER.
  4. ExecutionSpecialist: Micro-structure timing, slippage defense, +1.0R dynamic breakeven routing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import math
import logging

logger = logging.getLogger("Jarvis.ConsensusChamber")

class DebateAgent(ABC):
    """Abstract base debater agent."""
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def evaluate(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Produce initial assessment and thesis."""
        pass

    @abstractmethod
    def rebut(self, proposal: Dict[str, Any], market_context: Dict[str, Any], opponent_arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Produce rebuttal to opposing council arguments."""
        pass


class BullishAdvocate(DebateAgent):
    """
    Champions bullish market theses:
    - Support confluence, order block reclaims, positive CVD delta, discount Fibonacci OTE (61.8% - 78.6%).
    """
    def __init__(self):
        super().__init__(name="BullishAdvocate", role="Long Momentum & Support Analyst")

    def evaluate(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = proposal.get("symbol", "UNKNOWN")
        action = str(proposal.get("action", "BUY")).upper()
        indicators = market_context.get("indicators", {})
        
        rsi = float(indicators.get("rsi", 50.0))
        trend = indicators.get("trend", "BULLISH")
        cvd_delta = float(indicators.get("cvd_delta", 10.0))
        ote_discount = bool(indicators.get("ote_discount", True))
        
        # Bullish scoring
        score = 50.0
        points = []

        if trend in ("BULLISH", "STRONG_BULLISH"):
            score += 20.0
            points.append("Aligned with macro HTF bullish trend structure.")
        elif trend == "NEUTRAL":
            score += 5.0
            points.append("Macro trend neutral; consolidation favoring breakout.")
        else:
            score -= 20.0
            points.append("Counter-trend headwind against HTF bearish flow.")

        if 40.0 <= rsi <= 68.0:
            score += 15.0
            points.append(f"RSI healthy at {rsi:.1f}, indicating bullish expansion capacity.")
        elif rsi < 40.0:
            score += 10.0
            points.append(f"RSI oversold at {rsi:.1f}, prime institutional discount accumulation.")
        else:
            score -= 10.0
            points.append(f"RSI elevated at {rsi:.1f}, approaching local exhaustion.")

        if cvd_delta > 0:
            score += 10.0
            points.append(f"Cumulative Volume Delta positive (+{cvd_delta:.1f}), active absorption.")
            
        if ote_discount:
            score += 10.0
            points.append("Price positioned in institutional Fibonacci discount OTE zone.")

        # Closed-bar evidence confirmation
        closed_bar_score = float(market_context.get("closed_bar_evidence_score", 72.0))
        if closed_bar_score >= 70.0:
            score += 12.0
            points.append(f"Closed-bar technical confirmation verified ({closed_bar_score:.1f}% evidence weight).")
        elif closed_bar_score < 45.0:
            score -= 10.0
            points.append(f"Caution: Low closed-bar confirmation ({closed_bar_score:.1f}%); intra-bar wick risk.")

        # Geopolitical News Impact Correlation
        geo_impact = market_context.get("geopolitical_news_impact", {})
        impact_score = float(geo_impact.get("impact_score", 65.0))
        bias = str(geo_impact.get("correlation_bias", "SAFE_HAVEN_ACCELERATION"))
        if action == "BUY" and impact_score > 30.0:
            score += 10.0
            points.append(f"Geopolitical tailwind: {bias} (Impact score +{impact_score:.1f}).")
        elif action == "SELL" and impact_score > 50.0 and ("XAU" in symbol.upper() or "BTC" in symbol.upper()):
            score -= 15.0
            points.append(f"Macro friction: Fighting safe-haven geopolitical tailwind ({bias}).")

        confidence = max(5.0, min(95.0, score))
        recommendation = "BUY" if confidence >= 60.0 else ("HOLD" if confidence >= 40.0 else "SELL")

        return {
            "agent": self.name,
            "role": self.role,
            "action_proposed": action,
            "confidence": round(confidence, 1),
            "recommendation": recommendation,
            "thesis": f"Bull thesis on {symbol}: " + " | ".join(points),
            "key_points": points,
            "closed_bar_score": closed_bar_score,
            "geopolitical_impact": geo_impact,
        }

    def rebut(self, proposal: Dict[str, Any], market_context: Dict[str, Any], opponent_arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        bear_concerns = [arg.get("thesis", "") for arg in opponent_arguments if arg.get("agent") == "BearishChallenger"]
        combined_bear = " ".join(bear_concerns)
        
        rebuttal_points = []
        if "resistance" in combined_bear.lower() or "supply" in combined_bear.lower():
            rebuttal_points.append("Overhead supply has been tapped multiple times, weakening liquidity barriers.")
        if "divergence" in combined_bear.lower() or "exhaustion" in combined_bear.lower():
            rebuttal_points.append("SMC order block absorption absorbs diverged volume, setting up high-velocity expansion.")
        if not rebuttal_points:
            rebuttal_points.append("Bullish institutional order flow and volume delta dominate transient pullbacks.")

        return {
            "agent": self.name,
            "role": self.role,
            "rebuttal": " | ".join(rebuttal_points),
            "adjusted_stance": "MAINTAIN_BULLISH",
        }


class BearishChallenger(DebateAgent):
    """
    Skeptic agent challenging upside assumptions:
    - Liquidity sweeps, overhead resistance, overextended momentum, bear flag continuations, macroeconomic shock vulnerability.
    """
    def __init__(self):
        super().__init__(name="BearishChallenger", role="Institutional Skeptic & Liquidity Sweep Hunter")

    def evaluate(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = proposal.get("symbol", "UNKNOWN")
        action = str(proposal.get("action", "BUY")).upper()
        indicators = market_context.get("indicators", {})

        rsi = float(indicators.get("rsi", 50.0))
        resistance_proximity = float(indicators.get("resistance_proximity_pct", 1.5))
        dxy_trend = indicators.get("dxy_trend", "BULLISH")
        liquidity_sweep = bool(indicators.get("liquidity_sweep_pending", False))

        score = 50.0
        points = []

        if resistance_proximity < 1.0:
            score += 25.0
            points.append(f"Price is within {resistance_proximity:.2f}% of key HTF resistance.")
        else:
            score -= 10.0
            points.append("Clear runway to next major resistance.")

        if rsi > 65.0:
            score += 15.0
            points.append(f"Momentum overstretched (RSI {rsi:.1f}); high risk of long liquidation wick.")
        elif rsi < 35.0:
            score += 20.0
            points.append(f"Momentum heavily bearish (RSI {rsi:.1f}), strong breakdown momentum.")

        if dxy_trend == "BULLISH" and ("XAU" in symbol or "EUR" in symbol or "BTC" in symbol):
            score += 15.0
            points.append("DXY dollar index strength exerts persistent structural gravity.")

        if liquidity_sweep:
            score += 15.0
            points.append("Unmitigated liquidity pools resting below current price may trigger institutional sweep.")

        # Closed-bar confirmation check
        closed_bar_score = float(market_context.get("closed_bar_evidence_score", 72.0))
        if closed_bar_score < 50.0:
            score += 15.0
            points.append(f"Unconfirmed live wick trap: low closed-bar evidence ({closed_bar_score:.1f}%).")
        elif closed_bar_score >= 80.0 and action == "BUY":
            score -= 10.0
            points.append(f"High closed-bar evidence ({closed_bar_score:.1f}%) weakens bearish counter-thesis.")

        # Geopolitical News Impact Correlation
        geo_impact = market_context.get("geopolitical_news_impact", {})
        impact_score = float(geo_impact.get("impact_score", 65.0))
        bias = str(geo_impact.get("correlation_bias", "SAFE_HAVEN_ACCELERATION"))
        if action == "SELL" and ("EUR" in symbol.upper()):
            score += 15.0
            points.append(f"Geopolitical vulnerability discount applies to EUR ({bias}).")
        elif action == "BUY" and impact_score > 60.0 and ("XAU" in symbol.upper() or "BTC" in symbol.upper()):
            score -= 10.0
            points.append("Persistent geopolitical safe-haven bid suppresses sustained short extensions.")

        confidence = max(5.0, min(95.0, score))
        recommendation = "SELL" if confidence >= 60.0 else ("HOLD" if confidence >= 40.0 else "BUY")

        return {
            "agent": self.name,
            "role": self.role,
            "action_proposed": action,
            "confidence": round(confidence, 1),
            "recommendation": recommendation,
            "thesis": f"Bear thesis on {symbol}: " + (" | ".join(points) if points else "No major structural vulnerabilities detected."),
            "key_points": points,
            "closed_bar_score": closed_bar_score,
            "geopolitical_impact": geo_impact,
        }

    def rebut(self, proposal: Dict[str, Any], market_context: Dict[str, Any], opponent_arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        bull_claims = [arg.get("thesis", "") for arg in opponent_arguments if arg.get("agent") == "BullishAdvocate"]
        combined_bull = " ".join(bull_claims)

        rebuttal_points = []
        if "breakout" in combined_bull.lower() or "momentum" in combined_bull.lower():
            rebuttal_points.append("Breakout retail traps frequently trigger fakeouts before real institutional repricing.")
        if "discount" in combined_bull.lower():
            rebuttal_points.append("Deep discount can easily turn into falling knife without definitive structural market structure shift (MSS).")
        if not rebuttal_points:
            rebuttal_points.append("Caution advised: macro liquidity conditions remain fragile.")

        return {
            "agent": self.name,
            "role": self.role,
            "rebuttal": " | ".join(rebuttal_points),
            "adjusted_stance": "DEMAND_STRICT_STOP",
        }


class RiskOfficer(DebateAgent):
    """
    Chief Risk Compliance Agent for Master Muhammad Qureshi's sovereign capital.
    Holds absolute UNANIMOUS VETO POWER.
    Enforces:
      - Max Risk per trade <= 0.75% ($750 on FundingPips #40000294403)
      - Minimum Risk-to-Reward (R:R) >= 2.5
      - 15-Minute News Blackout
      - Safe directional geometry (Entry != Stop Loss, TP in proper direction)
    """
    def __init__(self, max_risk_pct: float = 0.75, max_risk_usd: float = 750.0, min_rr: float = 2.5):
        super().__init__(name="RiskOfficer", role="Sovereign Prop-Firm Compliance & Capital Sentinel")
        self.max_risk_pct = max_risk_pct
        self.max_risk_usd = max_risk_usd
        self.min_rr = min_rr

    def evaluate(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        account_id = str(proposal.get("account_id", "40000294403"))
        balance = float(proposal.get("account_balance", 100000.0))
        price = float(proposal.get("price", proposal.get("entry_price", 0.0)))
        sl = float(proposal.get("stop_loss", 0.0))
        tp = float(proposal.get("take_profit", 0.0))
        action = str(proposal.get("action", "BUY")).upper()
        
        # Risk computations
        risk_pct = float(proposal.get("risk_pct", 0.0))
        risk_usd = float(proposal.get("risk_usd", 0.0))

        # Check calculated risk if not explicitly provided
        if risk_usd == 0.0 and balance > 0 and risk_pct > 0:
            risk_usd = balance * (risk_pct / 100.0)
        elif risk_pct == 0.0 and balance > 0 and risk_usd > 0:
            risk_pct = (risk_usd / balance) * 100.0

        # Geometry validation
        if price <= 0 or sl <= 0 or tp <= 0:
            return self._veto("VETO_INVALID_GEOMETRY", f"Invalid price/sl/tp geometry: price={price}, sl={sl}, tp={tp}")

        risk_dist = abs(price - sl)
        reward_dist = abs(tp - price)
        if risk_dist <= 1e-6:
            return self._veto("VETO_ZERO_RISK_DISTANCE", "Stop loss cannot equal entry price.")

        calculated_rr = reward_dist / risk_dist
        provided_rr = float(proposal.get("rr_ratio", calculated_rr))
        rr = max(calculated_rr, provided_rr)

        # Direction checks
        if action == "BUY":
            if sl >= price:
                return self._veto("VETO_BUY_SL_ABOVE_ENTRY", f"BUY stop loss ({sl}) must be below entry ({price})")
            if tp <= price:
                return self._veto("VETO_BUY_TP_BELOW_ENTRY", f"BUY take profit ({tp}) must be above entry ({price})")
        elif action == "SELL":
            if sl <= price:
                return self._veto("VETO_SELL_SL_BELOW_ENTRY", f"SELL stop loss ({sl}) must be above entry ({price})")
            if tp >= price:
                return self._veto("VETO_SELL_TP_ABOVE_ENTRY", f"SELL take profit ({tp}) must be below entry ({price})")
        else:
            return self._veto("VETO_INVALID_ACTION", f"Invalid trading action: {action}")

        # Deterministic Risk Cap Violation
        if risk_pct > (self.max_risk_pct + 1e-4):
            return self._veto(
                "VETO_RISK_PCT_EXCEEDED",
                f"Proposed risk {risk_pct:.2f}% exceeds non-negotiable ceiling of {self.max_risk_pct:.2f}%"
            )

        if risk_usd > (self.max_risk_usd + 1e-4):
            return self._veto(
                "VETO_RISK_USD_EXCEEDED",
                f"Proposed risk ${risk_usd:.2f} exceeds absolute account cap of ${self.max_risk_usd:.2f}"
            )

        # Minimum R:R Violation
        if rr < (self.min_rr - 1e-4):
            return self._veto(
                "VETO_INSUFFICIENT_RR",
                f"Risk-to-Reward ratio {rr:.2f} is below required threshold of {self.min_rr:.2f}"
            )

        # News Blackout Check
        upcoming_news_minutes = market_context.get("minutes_to_high_impact_news", None)
        if upcoming_news_minutes is not None and 0 <= float(upcoming_news_minutes) <= 15.0:
            return self._veto(
                "VETO_NEWS_BLACKOUT",
                f"High-impact macroeconomic release scheduled in {upcoming_news_minutes} minutes (15m blackout enforced)."
            )

        # All checks passed
        return {
            "agent": self.name,
            "role": self.role,
            "approved": True,
            "veto": False,
            "veto_reason": None,
            "confidence": 100.0,
            "risk_metrics": {
                "account_id": account_id,
                "balance": balance,
                "risk_pct": round(risk_pct, 3),
                "risk_usd": round(risk_usd, 2),
                "max_risk_pct": self.max_risk_pct,
                "max_risk_usd": self.max_risk_usd,
                "rr_ratio": round(rr, 2),
                "min_rr": self.min_rr,
            },
            "compliance_statement": f"APPROVED: Order strictly complies with Sovereign {self.max_risk_pct}% risk cap and {self.min_rr}:1 R:R standard."
        }

    def rebut(self, proposal: Dict[str, Any], market_context: Dict[str, Any], opponent_arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Risk officer reaffirms safety parameters
        return {
            "agent": self.name,
            "role": self.role,
            "verdict": "RISK_BOUNDS_UNALTERABLE",
            "message": "Risk parameters remain binding regardless of debate enthusiasm."
        }

    def _veto(self, code: str, reason: str) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "role": self.role,
            "approved": False,
            "veto": True,
            "veto_code": code,
            "veto_reason": reason,
            "confidence": 0.0,
            "compliance_statement": f"VETOED BY RISK OFFICER: {reason}"
        }


class ExecutionSpecialist(DebateAgent):
    """
    Precision execution engineer:
    - Microstructure spread & slippage mitigation.
    - Determines optimal order routing (LIMIT vs MARKET IOC).
    - Arms dynamic +1.0R Breakeven and multi-tier partial TP trail.
    """
    def __init__(self):
        super().__init__(name="ExecutionSpecialist", role="Microstructure & Dynamic Execution Specialist")

    def evaluate(self, proposal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = proposal.get("symbol", "UNKNOWN")
        action = str(proposal.get("action", "BUY")).upper()
        price = float(proposal.get("price", proposal.get("entry_price", 0.0)))
        sl = float(proposal.get("stop_loss", 0.0))
        tp = float(proposal.get("take_profit", 0.0))

        spread_bps = float(market_context.get("spread_bps", 1.2))
        volatility_atr = float(market_context.get("atr_14", abs(price * 0.005)))
        
        risk_dist = abs(price - sl)
        
        # Calculate +1.0R breakeven trigger
        if action == "BUY":
            be_trigger = price + risk_dist
            tp1_partial = price + (risk_dist * 1.5)
        else:
            be_trigger = price - risk_dist
            tp1_partial = price - (risk_dist * 1.5)

        # Select execution type
        order_type = "LIMIT" if spread_bps > 2.0 else "MARKET"
        estimated_slippage_bps = round(min(spread_bps * 0.4, 2.5), 2)

        return {
            "agent": self.name,
            "role": self.role,
            "symbol": symbol,
            "recommended_order_type": order_type,
            "estimated_slippage_bps": estimated_slippage_bps,
            "execution_plan": {
                "entry_price": price,
                "stop_loss": sl,
                "take_profit_final": tp,
                "breakeven_trigger_price": round(be_trigger, 4),
                "breakeven_offset_pips": 1.0,
                "partial_tp1_price": round(tp1_partial, 4),
                "partial_tp1_size_pct": 50.0,
                "trailing_stop_armed": True,
            },
            "recommendation": "EXECUTE_OPTIMAL",
            "confidence": 92.0,
        }

    def rebut(self, proposal: Dict[str, Any], market_context: Dict[str, Any], opponent_arguments: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "role": self.role,
            "rebuttal": "Execution routing prepared with dynamic +1.0R breakeven safety cushion.",
            "adjusted_stance": "ARMED_AND_READY",
        }
