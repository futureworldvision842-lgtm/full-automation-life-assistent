"""
adversarial_debate_engine.py — Multi-Agent Adversarial Debate & Consensus Framework.
Inspired by TradingAgents (TauricResearch) and AI Hedge Fund (virattt/ai-hedge-fund).

Operates a structured debate between:
  1. Bullish Quant Researcher (presents long thesis & structural confirmations)
  2. Bearish Risk Auditor (actively hunts for invalidations, traps & counter-arguments)
  3. Chief Investment Officer (CIO Judge) (renders final execution verdict)
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("AdversarialDebate")


class AdversarialDebateEngine:
    """
    Adversarial Debate State Machine.
    Eliminates confirmation bias by subjecting prospective trade signals to rigorous cross-examination.
    """

    def __init__(self, conviction_threshold: float = 0.65):
        self.conviction_threshold = conviction_threshold

    def conduct_debate(
        self,
        symbol: str,
        proposed_direction: str,
        analysis: Dict[str, Any],
        confluence_score: float
    ) -> Dict[str, Any]:
        """
        Runs the Bull vs Bear adversarial cross-examination loop.
        """
        bull_arguments = []
        bear_arguments = []

        trend = analysis.get("trend_direction", "NEUTRAL")
        rsi = analysis.get("rsi", 50.0)
        prem_disc = analysis.get("premium_discount", {})
        adr_intel = analysis.get("adr_intel", {})
        ote_buy = analysis.get("ote_buy", {})
        ote_sell = analysis.get("ote_sell", {})
        vsa = analysis.get("vsa_intel", {})
        killzone = analysis.get("killzone", {})
        regime = analysis.get("regime_intel", {})

        # ── 1. Bullish Researcher Arguments ───────────────────────────────────
        if trend == "BULLISH":
            bull_arguments.append("H1 Macro Trend is strongly BULLISH (Trend Alignment).")
        if prem_disc.get("zone") == "DISCOUNT":
            bull_arguments.append(f"Price is in institutional DISCOUNT ({prem_disc.get('discount_pct')}% discount).")
        if ote_buy.get("in_ote_zone"):
            bull_arguments.append("Price is in 70.5% Optimal Trade Entry (OTE) Golden Pocket.")
        if vsa.get("type") == "BULLISH_ABSORPTION":
            bull_arguments.append(f"VSA Bullish Institutional Absorption confirmed ({vsa.get('volume_ratio')}x volume).")
        if killzone.get("is_prime_killzone"):
            bull_arguments.append(f"Active Prime Killzone: {killzone.get('killzone')}.")
        if rsi < 35.0:
            bull_arguments.append(f"RSI is oversold ({rsi:.1f}) offering high-value mean reversion.")

        # ── 2. Bearish Risk Auditor Arguments ──────────────────────────────────
        if trend == "BEARISH":
            bear_arguments.append("H1 Macro Trend is strongly BEARISH (Counter-trend danger!).")
        if prem_disc.get("zone") == "PREMIUM":
            bear_arguments.append(f"Price is in PREMIUM zone ({prem_disc.get('discount_pct')}% discount) — buying here is retail trap.")
        if adr_intel.get("is_adr_exhausted"):
            bear_arguments.append(f"14-Day ADR is exhausted ({adr_intel.get('adr_pct_consumed')}% spent today). Chasing is dangerous.")
        if regime.get("regime_state") == 2:
            bear_arguments.append("Market is in HIGH_VOLATILITY_TURBULENCE state — risk of sudden wick stops.")
        if rsi > 68.0:
            bear_arguments.append(f"RSI is overbought ({rsi:.1f}) near macro resistance.")
        if vsa.get("type") == "BEARISH_ABSORPTION":
            bear_arguments.append("Bearish Institutional Absorption detected overhead.")

        # ── 3. CIO Final Adjudication ─────────────────────────────────────────
        bull_score = len(bull_arguments) * 1.0 + (confluence_score if proposed_direction == "BUY" else 0.0)
        bear_score = len(bear_arguments) * 1.0 + (confluence_score if proposed_direction == "SELL" else 0.0)

        fatal_flaws = []
        # Critical fatal objections
        if proposed_direction == "BUY" and trend == "BEARISH":
            fatal_flaws.append("FATAL: Attempting BUY against BEARISH H1 Trend.")
        if proposed_direction == "SELL" and trend == "BULLISH":
            fatal_flaws.append("FATAL: Attempting SELL against BULLISH H1 Trend.")
        if proposed_direction == "BUY" and prem_disc.get("zone") == "PREMIUM" and not analysis.get("active_support"):
            fatal_flaws.append("FATAL: Buying at Premium without verified support.")
        if proposed_direction == "SELL" and prem_disc.get("zone") == "DISCOUNT" and not analysis.get("active_resistance"):
            fatal_flaws.append("FATAL: Selling at Discount without verified resistance.")

        is_approved = len(fatal_flaws) == 0 and (
            (proposed_direction == "BUY" and bull_score >= bear_score) or
            (proposed_direction == "SELL" and bear_score >= bull_score)
        )

        cio_verdict = "DEBATE_APPROVED" if is_approved else "DEBATE_VETOED"
        rejection_reason = " | ".join(fatal_flaws) if fatal_flaws else ("Bearish arguments outweigh bull thesis." if proposed_direction == "BUY" else "Bullish arguments outweigh bear thesis.")

        logger.info(
            f"[Adversarial Debate] {symbol} {proposed_direction}: "
            f"Bulls({len(bull_arguments)}) vs Bears({len(bear_arguments)}) => {cio_verdict}"
        )

        return {
            "verdict": cio_verdict,
            "approved": is_approved,
            "bull_score": round(bull_score, 2),
            "bear_score": round(bear_score, 2),
            "bull_arguments": bull_arguments,
            "bear_arguments": bear_arguments,
            "fatal_flaws": fatal_flaws,
            "rejection_reason": rejection_reason if not is_approved else "None"
        }
