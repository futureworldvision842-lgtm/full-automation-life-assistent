"""
intelligence/vibe_sentiment.py
===============================
HKUDS/Vibe-Trading Social Sentiment Engine for J.A.R.V.I.S.
Calculates real-time "Vibe Score" (-100.0 to +100.0) from social chatter,
news headlines, and meme token sentiment using local Ollama (qwen2.5:0.5b on :11434)
with deterministic high-speed local fallback.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import urllib.request
import json
import re
import time
import logging

logger = logging.getLogger("Jarvis.VibeTrading")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:0.5b"

# High-conviction lexical weight dictionaries for instant fallback & fusion
BULLISH_LEXICON: Dict[str, float] = {
    "breakout": 15.0,
    "accumulation": 20.0,
    "accumulating": 20.0,
    "god candle": 25.0,
    "parabolic": 20.0,
    "whale buy": 25.0,
    "institutional inflow": 30.0,
    "ath": 15.0,
    "all time high": 15.0,
    "bullish": 15.0,
    "pump": 10.0,
    "listing": 20.0,
    "airdrop": 10.0,
    "partnership": 15.0,
    "expansion": 12.0,
    "moon": 10.0,
    "surge": 15.0,
    "rebound": 15.0,
    "safe haven": 20.0,
}

BEARISH_LEXICON: Dict[str, float] = {
    "rug": -35.0,
    "rug pull": -40.0,
    "honeypot": -40.0,
    "dump": -25.0,
    "liquidation": -20.0,
    "cascade": -20.0,
    "exploit": -40.0,
    "hack": -40.0,
    "sec crackdown": -30.0,
    "investigation": -25.0,
    "insider dump": -35.0,
    "unlock": -15.0,
    "scam": -40.0,
    "bearish": -15.0,
    "selloff": -20.0,
    "insolvency": -45.0,
    "fud": -10.0,
    "rejection": -15.0,
    "war": -20.0,
    "escalation": -20.0,
}


@dataclass
class VibeSentimentResult:
    target: str
    vibe_score: float  # -100.0 to +100.0
    sentiment_label: str  # EXTREME_FEAR, FEAR, NEUTRAL, GREED, EXTREME_GREED
    viral_momentum: float  # 0.0 to 10.0
    bullish_signals: List[str]
    bearish_signals: List[str]
    risk_flags: List[str]
    source: str  # "OLLAMA_LOCAL" or "FAST_LEXICAL_ENGINE"
    latency_ms: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "vibe_score": round(self.vibe_score, 2),
            "sentiment_label": self.sentiment_label,
            "viral_momentum": round(self.viral_momentum, 2),
            "bullish_signals": self.bullish_signals,
            "bearish_signals": self.bearish_signals,
            "risk_flags": self.risk_flags,
            "source": self.source,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
        }


class VibeSentimentEngine:
    """
    Real-time social and multimodal sentiment engine.
    Fuses local Ollama SLM reasoning with deterministic lexical heuristics.
    """
    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.ollama_url = ollama_url
        self.model = model

    def analyze(self, target: str, texts: List[str], use_slm: bool = True) -> VibeSentimentResult:
        """
        Analyzes a batch of headlines, tweets, or social posts for a given asset/token.
        """
        start_t = time.perf_counter()
        target_upper = target.upper()

        if not texts:
            return VibeSentimentResult(
                target=target_upper,
                vibe_score=0.0,
                sentiment_label="NEUTRAL",
                viral_momentum=0.0,
                bullish_signals=[],
                bearish_signals=[],
                risk_flags=[],
                source="EMPTY_INPUT",
                latency_ms=0.0,
            )

        # 1. High-speed deterministic lexical pass
        bull_found: List[str] = []
        bear_found: List[str] = []
        risk_flags: List[str] = []
        lexical_sum = 0.0

        combined_text = " \n ".join(texts).lower()

        for phrase, weight in BULLISH_LEXICON.items():
            if re.search(r"\b" + re.escape(phrase) + r"\b", combined_text):
                lexical_sum += weight
                bull_found.append(phrase)

        for phrase, weight in BEARISH_LEXICON.items():
            if re.search(r"\b" + re.escape(phrase) + r"\b", combined_text):
                lexical_sum += weight
                bear_found.append(phrase)
                if weight <= -30.0:
                    risk_flags.append(f"SEVERE_RISK: {phrase.upper()} detected")

        # Normalize lexical score into -100 to +100
        lexical_score = max(-100.0, min(100.0, lexical_sum))
        source_used = "FAST_LEXICAL_ENGINE"
        final_score = lexical_score

        # 2. Local Ollama SLM check if enabled and reachable
        if use_slm:
            slm_score = self._query_ollama(target_upper, texts[:5])
            if slm_score is not None:
                # 60% SLM + 40% lexical confirmation
                final_score = (slm_score * 0.60) + (lexical_score * 0.40)
                source_used = "OLLAMA_LOCAL_FUSION"

        final_score = max(-100.0, min(100.0, final_score))

        # 3. Derive label and viral momentum
        if final_score >= 60.0:
            label = "EXTREME_GREED"
        elif final_score >= 20.0:
            label = "GREED"
        elif final_score <= -60.0:
            label = "EXTREME_FEAR"
        elif final_score <= -20.0:
            label = "FEAR"
        else:
            label = "NEUTRAL"

        # Viral momentum based on volume of signal hits
        total_signals = len(bull_found) + len(bear_found)
        viral_momentum = min(10.0, (total_signals * 1.25) + (len(texts) * 0.2))

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return VibeSentimentResult(
            target=target_upper,
            vibe_score=final_score,
            sentiment_label=label,
            viral_momentum=viral_momentum,
            bullish_signals=bull_found,
            bearish_signals=bear_found,
            risk_flags=risk_flags,
            source=source_used,
            latency_ms=elapsed_ms,
        )

    def _query_ollama(self, target: str, sample_texts: List[str]) -> Optional[float]:
        """Calls local Ollama instance with a strict 2-second timeout."""
        prompt = (
            f"Analyze sentiment for {target} on a scale of -100 (extreme panic/bearish) to +100 (extreme hype/bullish).\n"
            f"Texts:\n" + "\n".join(f"- {t}" for t in sample_texts) + "\n"
            f"Respond ONLY with a single JSON object: {{\"score\": <integer between -100 and 100>}}"
        )
        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    response_text = body.get("response", "")
                    parsed = json.loads(response_text)
                    val = float(parsed.get("score", 0.0))
                    return max(-100.0, min(100.0, val))
        except Exception as e:
            logger.debug("Ollama SLM offline or timed out, relying on fast deterministic lexicon: %s", e)
            return None
        return None


_global_vibe_engine: Optional[VibeSentimentEngine] = None

def get_vibe_sentiment_engine() -> VibeSentimentEngine:
    global _global_vibe_engine
    if _global_vibe_engine is None:
        _global_vibe_engine = VibeSentimentEngine()
    return _global_vibe_engine
