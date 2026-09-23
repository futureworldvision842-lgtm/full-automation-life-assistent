"""
AI-Trader Intelligence Module
Extracted from HKUDS/AI-Trader repository architecture.
Provides Signal Quality Scoring, Multi-Agent Consensus Voting,
and Free Market Data Fetching (yfinance, Hyperliquid).
"""

import logging
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Signal Quality Scorer  (0 – 5 scale, 5 weighted dimensions)
# ---------------------------------------------------------------------------

class SignalQualityScorer:
    """
    Evaluates a trade signal on a 0-5 composite scale using five
    weighted metrics inspired by AI-Trader's signal_quality.py engine.

    Weights:
        Verifiability  30 %   – direction, symbol, SL/TP present?
        Evidence       25 %   – supporting indicators / pattern count
        Specificity    20 %   – lot size, session, weather forecast present?
        Novelty        15 %   – not a duplicate of the last N signals
        Timeliness     10 %   – inside an active ICT Kill Zone?
    """

    WEIGHTS = {
        "verifiability": 0.30,
        "evidence":      0.25,
        "specificity":   0.20,
        "novelty":       0.15,
        "timeliness":    0.10,
    }

    def __init__(self, recent_window: int = 20):
        self.recent_signals: List[str] = []
        self.recent_window = recent_window
        logger.info("SignalQualityScorer initialized (AI-Trader extraction).")

    # ---- public ----------------------------------------------------------

    def score_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Return a dict with per-dimension scores and composite quality."""
        v = self._score_verifiability(signal)
        e = self._score_evidence(signal)
        s = self._score_specificity(signal)
        n = self._score_novelty(signal)
        t = self._score_timeliness(signal)

        composite = (
            v * self.WEIGHTS["verifiability"]
            + e * self.WEIGHTS["evidence"]
            + s * self.WEIGHTS["specificity"]
            + n * self.WEIGHTS["novelty"]
            + t * self.WEIGHTS["timeliness"]
        )

        # remember fingerprint for novelty checks
        fp = self._fingerprint(signal)
        self.recent_signals.append(fp)
        if len(self.recent_signals) > self.recent_window:
            self.recent_signals.pop(0)

        result = {
            "composite_quality": round(composite, 2),
            "verifiability": round(v, 2),
            "evidence": round(e, 2),
            "specificity": round(s, 2),
            "novelty": round(n, 2),
            "timeliness": round(t, 2),
            "grade": self._grade(composite),
        }
        logger.info(
            f"[Signal Quality] {signal.get('symbol','?')} {signal.get('direction','?')} "
            f"=> Composite {result['composite_quality']}/5.0 ({result['grade']})"
        )
        return result

    # ---- private dimensions ----------------------------------------------

    @staticmethod
    def _score_verifiability(sig: Dict) -> float:
        score = 0.0
        if sig.get("direction") in ("BUY", "SELL"):
            score += 2.0
        if sig.get("symbol"):
            score += 1.0
        if sig.get("sl") is not None:
            score += 1.0
        if sig.get("tp") is not None:
            score += 1.0
        return min(score, 5.0)

    @staticmethod
    def _score_evidence(sig: Dict) -> float:
        score = 0.0
        patterns = sig.get("patterns", [])
        score += min(len(patterns) * 1.0, 3.0)
        if sig.get("confluence_score", 0) >= 1.0:
            score += 1.0
        if sig.get("weather_forecast"):
            score += 1.0
        return min(score, 5.0)

    @staticmethod
    def _score_specificity(sig: Dict) -> float:
        score = 0.0
        if sig.get("lot_size") is not None:
            score += 1.5
        if sig.get("session"):
            score += 1.0
        if sig.get("weather_forecast"):
            score += 1.0
        if sig.get("fincept_sentiment") is not None:
            score += 0.75
        if sig.get("atr") is not None:
            score += 0.75
        return min(score, 5.0)

    def _score_novelty(self, sig: Dict) -> float:
        fp = self._fingerprint(sig)
        duplicates = self.recent_signals.count(fp)
        if duplicates == 0:
            return 5.0
        elif duplicates == 1:
            return 3.0
        elif duplicates == 2:
            return 1.5
        return 0.0

    @staticmethod
    def _score_timeliness(sig: Dict) -> float:
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        # ICT Kill Zones (London 07-10, NY 13-16)
        if 7 <= hour <= 10 or 13 <= hour <= 16:
            return 5.0
        # Extended sessions
        if 6 <= hour <= 11 or 12 <= hour <= 17:
            return 3.0
        # Asian / off-hours
        return 1.5

    @staticmethod
    def _fingerprint(sig: Dict) -> str:
        key = f"{sig.get('symbol','')}-{sig.get('direction','')}-{sig.get('entry_price','')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 4.0:
            return "EXCELLENT"
        if score >= 3.0:
            return "GOOD"
        if score >= 2.0:
            return "FAIR"
        return "WEAK"


# ---------------------------------------------------------------------------
# 2. Multi-Agent Consensus Voter  (3-bot approval gate)
# ---------------------------------------------------------------------------

class MultiAgentConsensusVoter:
    """
    Before any trade executes, three specialised virtual sub-bots
    independently vote APPROVE / REJECT / ABSTAIN.

    Trade proceeds only if **>= 2 APPROVE** votes are cast.

    Bots:
        TrendBot      – EMA 50/200 alignment & trend direction
        MomentumBot   – RSI extremes & MACD histogram direction
        StructureBot  – SMC pattern presence (FVG, OB, Sweep)
    """

    def __init__(self):
        logger.info("MultiAgentConsensusVoter initialized (3-bot gate).")

    def vote(self, analysis: Dict[str, Any], signal_direction: str) -> Dict[str, Any]:
        """Run all three bots and return aggregated verdict."""
        trend_vote    = self._trend_bot(analysis, signal_direction)
        momentum_vote = self._momentum_bot(analysis, signal_direction)
        structure_vote = self._structure_bot(analysis, signal_direction)

        votes = [trend_vote["vote"], momentum_vote["vote"], structure_vote["vote"]]
        approve_count = votes.count("APPROVE")
        reject_count  = votes.count("REJECT")

        approved = approve_count >= 2

        result = {
            "approved": approved,
            "approve_count": approve_count,
            "reject_count": reject_count,
            "trend_bot": trend_vote,
            "momentum_bot": momentum_vote,
            "structure_bot": structure_vote,
            "verdict": "CONSENSUS_APPROVED" if approved else "CONSENSUS_REJECTED",
        }

        symbol = analysis.get("symbol", "?")
        logger.info(
            f"[Consensus Vote] {symbol} {signal_direction}: "
            f"Trend={trend_vote['vote']} Momentum={momentum_vote['vote']} "
            f"Structure={structure_vote['vote']} => {result['verdict']}"
        )
        return result

    # ---- individual bots -------------------------------------------------

    @staticmethod
    def _trend_bot(analysis: Dict, direction: str) -> Dict[str, str]:
        trend = analysis.get("trend_direction", "NEUTRAL")
        has_support = analysis.get("active_support") is not None
        has_resistance = analysis.get("active_resistance") is not None
        has_ob = (analysis.get("bullish_ob") if direction == "BUY" else analysis.get("bearish_ob")) is not None

        if direction == "BUY" and trend == "BULLISH":
            return {"vote": "APPROVE", "reason": "Trend aligned BULLISH with EMA50 > EMA200"}
        if direction == "SELL" and trend == "BEARISH":
            return {"vote": "APPROVE", "reason": "Trend aligned BEARISH with EMA50 < EMA200"}
        
        # If price is at a strong Support/OB/Resistance, TrendBot ABSTAINS rather than blocks
        if (direction == "BUY" and (has_support or has_ob)) or (direction == "SELL" and (has_resistance or has_ob)):
            return {"vote": "ABSTAIN", "reason": f"Trend {trend} but Key Price Action Level active"}
            
        if trend == "NEUTRAL":
            return {"vote": "ABSTAIN", "reason": "Trend is NEUTRAL / mixed EMAs"}
        return {"vote": "REJECT", "reason": f"Trend is {trend}, conflicts with {direction}"}

    @staticmethod
    def _momentum_bot(analysis: Dict, direction: str) -> Dict[str, str]:
        rsi = analysis.get("rsi", 50.0)
        has_support = analysis.get("active_support") is not None
        has_resistance = analysis.get("active_resistance") is not None
        has_ob = (analysis.get("bullish_ob") if direction == "BUY" else analysis.get("bearish_ob")) is not None

        if direction == "BUY":
            if rsi > 78:
                return {"vote": "REJECT", "reason": f"RSI {rsi:.1f} is extreme overbought — risky BUY"}
            if rsi < 35 and (has_support or has_ob):
                return {"vote": "APPROVE", "reason": f"RSI {rsi:.1f} is Oversold at Support — Value Buy"}
            if rsi <= 75:
                return {"vote": "APPROVE", "reason": f"RSI {rsi:.1f} supports BUY"}
        elif direction == "SELL":
            if rsi < 22:
                return {"vote": "REJECT", "reason": f"RSI {rsi:.1f} is extreme oversold — risky SELL"}
            if rsi > 65 and (has_resistance or has_ob):
                return {"vote": "APPROVE", "reason": f"RSI {rsi:.1f} is Overbought at Resistance — Value Sell"}
            if rsi >= 25:
                return {"vote": "APPROVE", "reason": f"RSI {rsi:.1f} supports SELL"}

        return {"vote": "ABSTAIN", "reason": f"RSI {rsi:.1f} is neutral"}

    @staticmethod
    def _structure_bot(analysis: Dict, direction: str) -> Dict[str, str]:
        has_fvg = (analysis.get("bullish_fvg") if direction == "BUY"
                   else analysis.get("bearish_fvg"))
        has_ob  = (analysis.get("bullish_ob") if direction == "BUY"
                   else analysis.get("bearish_ob"))
        has_sr  = (analysis.get("active_support") if direction == "BUY"
                   else analysis.get("active_resistance"))
        sweep   = analysis.get("liquidity_sweep", {})
        sweep_type = sweep.get("type", "")
        candlesticks = analysis.get("candlestick_patterns", [])

        smc_count = 0
        reasons = []
        if has_ob:
            smc_count += 2
            reasons.append("Institutional Order Block")
        if has_sr:
            smc_count += 2
            reasons.append("Key Support/Resistance")
        if (direction == "BUY" and "BULLISH" in sweep_type) or \
           (direction == "SELL" and "BEARISH" in sweep_type):
            smc_count += 2
            reasons.append(f"Liquidity Sweep ({sweep_type})")
        if has_fvg:
            smc_count += 1
            reasons.append("Fair Value Gap")
        if candlesticks:
            smc_count += 1
            reasons.append("Reversal Candlestick")

        if smc_count >= 2:
            return {"vote": "APPROVE", "reason": f"Strong Price Action & SMC: {', '.join(reasons)}"}
        if smc_count == 1:
            return {"vote": "ABSTAIN", "reason": f"Partial Price Action: {', '.join(reasons)}"}
        return {"vote": "REJECT", "reason": "No Price Action / Support / SMC structure detected"}


# ---------------------------------------------------------------------------
# 3. Free Market Data Fetcher  (yfinance + Hyperliquid)
# ---------------------------------------------------------------------------

class FreeMarketDataFetcher:
    """
    Fetches auxiliary market data from 100 % free sources:
      • yfinance   – DXY / SPX correlation with Gold
      • Hyperliquid – BTC/ETH crypto sentiment (no API key)
    """

    HYPERLIQUID_URL = "https://api.hyperliquid.xyz/info"

    def __init__(self):
        self._yf_available = False
        try:
            import yfinance  # noqa: F401
            self._yf_available = True
        except ImportError:
            logger.warning("yfinance not installed — DXY/SPX correlation disabled.")
        logger.info("FreeMarketDataFetcher initialized (yfinance + Hyperliquid).")

    def get_dxy_correlation(self, gold_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Fetch DXY (US Dollar Index) and compute inverse correlation with Gold."""
        if not self._yf_available:
            return {"available": False, "correlation": None, "source": "yfinance_unavailable"}

        try:
            import yfinance as yf
            dxy = yf.download("DX-Y.NYB", period="5d", interval="1h", progress=False)
            if dxy.empty:
                return {"available": False, "correlation": None, "source": "empty_dxy_series"}

            dxy_returns = dxy['Close'].pct_change().dropna().values.flatten()

            if gold_df is not None and len(gold_df) >= len(dxy_returns):
                gold_returns = gold_df['close'].pct_change().dropna().values[-len(dxy_returns):]
                min_len = min(len(dxy_returns), len(gold_returns))
                if min_len > 5:
                    corr = float(np.corrcoef(dxy_returns[:min_len], gold_returns[:min_len])[0, 1])
                    return {"available": True, "correlation": round(corr, 4), "source": "yfinance_live"}

            return {
                "available": False,
                "correlation": None,
                "source": "aligned_gold_series_required",
            }
        except Exception as e:
            logger.warning(f"DXY correlation fetch failed: {e}")
            return {"available": False, "correlation": None, "source": "fetch_error"}

    def get_crypto_sentiment(self) -> Dict[str, Any]:
        """Query Hyperliquid for BTC/ETH mid-prices as crypto risk sentiment proxy."""
        try:
            import urllib.request
            payload = json.dumps({"type": "allMids"}).encode()
            req = urllib.request.Request(
                self.HYPERLIQUID_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            btc_price = float(data.get("BTC", 0))
            eth_price = float(data.get("ETH", 0))

            # Simple risk-on / risk-off heuristic
            if btc_price > 0:
                sentiment = "RISK_ON" if btc_price > 50000 else "RISK_NEUTRAL" if btc_price > 30000 else "RISK_OFF"
            else:
                sentiment = "UNKNOWN"

            return {
                "btc_price": btc_price,
                "eth_price": eth_price,
                "sentiment": sentiment,
                "source": "hyperliquid_free",
            }
        except Exception as e:
            logger.warning(f"Hyperliquid crypto sentiment fetch failed: {e}")
            return {"btc_price": 0, "eth_price": 0, "sentiment": "UNAVAILABLE", "source": "error"}

    def get_market_regime(self, gold_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Combine DXY correlation + crypto sentiment into a market regime label."""
        dxy = self.get_dxy_correlation(gold_df)
        crypto = self.get_crypto_sentiment()

        if not dxy.get("available") or dxy.get("correlation") is None:
            result = {
                "regime": "UNAVAILABLE",
                "confidence": 0.0,
                "actionable": False,
                "reason": "Verified aligned DXY and gold returns are required.",
                "dxy_correlation": None,
                "dxy_source": dxy.get("source", "unknown"),
                "crypto_sentiment": crypto.get("sentiment", "UNAVAILABLE"),
                "crypto_source": crypto.get("source", "unknown"),
                "btc_price": crypto.get("btc_price", 0),
            }
            logger.info("[Market Regime] UNAVAILABLE (verified DXY/gold correlation missing)")
            return result

        # Regime determination
        corr = float(dxy["correlation"])
        crypto_sent = crypto.get("sentiment", "UNKNOWN")

        if corr < -0.7 and crypto_sent == "RISK_ON":
            regime = "GOLD_BULLISH_MACRO"
            confidence = 0.85
        elif corr < -0.7 and crypto_sent == "RISK_OFF":
            regime = "FLIGHT_TO_SAFETY"
            confidence = 0.70
        elif corr > -0.3:
            regime = "DECORRELATED_CAUTION"
            confidence = 0.50
        else:
            regime = "NEUTRAL_MACRO"
            confidence = 0.60

        result = {
            "regime": regime,
            "confidence": confidence,
            "actionable": True,
            "dxy_correlation": corr,
            "dxy_source": dxy.get("source", "unknown"),
            "crypto_sentiment": crypto_sent,
            "crypto_source": crypto.get("source", "unknown"),
            "btc_price": crypto.get("btc_price", 0),
        }
        logger.info(f"[Market Regime] {regime} (confidence {confidence:.0%})")
        return result
