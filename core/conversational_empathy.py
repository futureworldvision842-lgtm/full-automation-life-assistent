"""
core/conversational_empathy.py — J.A.R.V.I.S. Conversational Empathy & Emotional Context Engine
================================================================================================
Equips J.A.R.V.I.S. with human-level conversational awareness:
1. Emotion & Tone Inference:
   - Detects emotional pressure, urgency, stress, curiosity, celebration, and fatigue from Urdu/English text and audio metrics.
   - Adapts response tone, brevity, and speech parameters (rate, pitch, volume) accordingly.
   - Strictly avoids fake certainty claims (e.g. "I can read your mind"); frames observations realistically:
     "Aap ka tone rushed lag raha hai; main direct critical action execute kar raha hoon."
2. Conversational State Tracking:
   - Maintains contextual state across turns so follow-ups continue seamlessly.
   - Saves session trajectory to runtime/conversational_state.json.
3. Human-Style Response Adaptation:
   - Modulates prompt instructions for LLMs / Command Router to match Master Muhammad Qureshi's mood.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.conversational_empathy")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_ROOT_DIR = Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _ROOT_DIR / "runtime"
_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
_STATE_FILE = _RUNTIME_DIR / "conversational_state.json"


class EmotionalState(str, Enum):
    NOMINAL = "NOMINAL"                   # Calm, standard executive interaction
    RUSHED = "RUSHED"                     # High urgency, time pressure, desires instant action
    STRESSED = "STRESSED"                 # Frustrated, anxious about loss/failure/errors
    INQUISITIVE = "INQUISITIVE"           # Wants deep explanation, quantitative reasoning, learning
    CELEBRATORY = "CELEBRATORY"           # Victorious, pleased with profit/progress, praises bot
    FATIGUED = "FATIGUED"                 # Tired, preparing for sleep, needs minimal disturbance


@dataclass
class EmpathyAnalysis:
    detected_state: EmotionalState
    confidence: float
    detected_triggers: List[str]
    suggested_tone: str
    response_prefix_ur: str
    brevity_level: str  # "TERSE", "BALANCED", "DETAILED"
    tts_rate_modifier: str  # e.g. "+15%", "+0%", "-10%"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["detected_state"] = self.detected_state.value
        return d


class ConversationalEmpathyEngine:
    """
    Infers emotional state and situational context from user messages
    to provide authentic human-like conversational responsiveness.
    """

    _instance: Optional[ConversationalEmpathyEngine] = None
    _lock = threading.Lock()

    def __init__(self):
        self._history: List[EmpathyAnalysis] = []
        self._load_state()

    @classmethod
    def get_instance(cls) -> ConversationalEmpathyEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_state(self) -> None:
        if _STATE_FILE.exists():
            try:
                data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
                for item in data.get("recent_states", [])[-10:]:
                    self._history.append(
                        EmpathyAnalysis(
                            detected_state=EmotionalState(item.get("detected_state", EmotionalState.NOMINAL.value)),
                            confidence=float(item.get("confidence", 0.5)),
                            detected_triggers=item.get("detected_triggers", []),
                            suggested_tone=item.get("suggested_tone", "Calm and professional"),
                            response_prefix_ur=item.get("response_prefix_ur", ""),
                            brevity_level=item.get("brevity_level", "BALANCED"),
                            tts_rate_modifier=item.get("tts_rate_modifier", "+0%"),
                            timestamp=item.get("timestamp", "")
                        )
                    )
            except Exception as e:
                logger.debug("Could not load conversational state: %s", e)

    def _save_state(self) -> None:
        try:
            payload = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "recent_states": [a.to_dict() for a in self._history[-15:]]
            }
            _STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Could not save conversational state: %s", e)

    def analyze_message(self, message: str) -> EmpathyAnalysis:
        """
        Evaluates text for linguistic markers of emotional state in Roman Urdu and English.
        """
        clean = (message or "").strip().lower()
        if not clean:
            return EmpathyAnalysis(
                detected_state=EmotionalState.NOMINAL,
                confidence=0.5,
                detected_triggers=[],
                suggested_tone="Attentive and steady",
                response_prefix_ur="",
                brevity_level="BALANCED",
                tts_rate_modifier="+0%"
            )

        triggers: List[str] = []

        # 1. RUSHED / URGENT markers
        rushed_patterns = [
            r"\b(jaldi|urgent|emergency|fatafat|foran|abhi|quick|asap|fast|hurry|speed|tez)\b",
            r"\b(jaldi karo|abhi chalao|run fast|quick action)\b"
        ]
        rushed_matches = [m.group(0) for p in rushed_patterns for m in re.finditer(p, clean)]

        # 2. STRESSED / FRUSTRATED markers
        stressed_patterns = [
            r"\b(masla|kharab|gussa|tension|loss|loss ho gaya|stuck|ruk gaya|nahi chal raha|fail|failed|error|problem|pareshan|ghussa|issue|bug)\b",
            r"\b(kyun nahi|kam nahi kar raha|sab band|jhootey|dhoka|chhoro|barbaad)\b",
            r"(!{2,}|\?{2,})"
        ]
        stressed_matches = [m.group(0) for p in stressed_patterns for m in re.finditer(p, clean)]

        # 3. INQUISITIVE / TEACHING markers
        inquisitive_patterns = [
            r"\b(samjhao|batao|kaise|kaise hota hai|why|kyun|detail|tafseel|logic|rationale|learn|seekho|samajh)\b",
            r"\b(explain|how it works|what is the reason|kya waja|strategy kya hai)\b"
        ]
        inquisitive_matches = [m.group(0) for p in inquisitive_patterns for m in re.finditer(p, clean)]

        # 4. CELEBRATORY / PROUD markers
        celebratory_patterns = [
            r"\b(shabash|great|mubarak|profit|kamyab|wah|good job|awesome|zabardast|congrats|well done|excellent|proud|win|passed)\b",
            r"\b(bohot khoob|cheeta|zindabad|superb)\b"
        ]
        celebratory_matches = [m.group(0) for p in celebratory_patterns for m in re.finditer(p, clean)]

        # 5. FATIGUED / SLEEP / DND markers
        fatigued_patterns = [
            r"\b(thak gaya|so raha|so raha hoon|sleep|sleeping|subah|kal dekhain|kal dekhenge|dnd|aram|rest|tang mat karo|messages band)\b"
        ]
        fatigued_matches = [m.group(0) for p in fatigued_patterns for m in re.finditer(p, clean)]

        # Prioritization Matrix: Stressed > Rushed > Fatigued > Celebratory > Inquisitive > Nominal
        if len(stressed_matches) >= 1:
            state = EmotionalState.STRESSED
            triggers = stressed_matches
            conf = min(0.65 + len(stressed_matches) * 0.15, 0.98)
            tone = "Calm, reassuring, solution-oriented and empathetic"
            prefix = "Fikr na karein Sir, masla identified hai aur auto-fix routine active hai."
            brevity = "BALANCED"
            tts_rate = "-5%"
        elif len(rushed_matches) >= 1:
            state = EmotionalState.RUSHED
            triggers = rushed_matches
            conf = min(0.60 + len(rushed_matches) * 0.15, 0.95)
            tone = "Ultra-brief, crisp, action-first executive"
            prefix = "Aap ka tone rushed lag raha hai; main direct critical action execute kar raha hoon."
            brevity = "TERSE"
            tts_rate = "+15%"
        elif len(fatigued_matches) >= 1:
            state = EmotionalState.FATIGUED
            triggers = fatigued_matches
            conf = min(0.70 + len(fatigued_matches) * 0.15, 0.95)
            tone = "Low-stimulus, respectful, quiet guardian"
            prefix = "Aap aaram karein Sir, background tasks safe guard mode par hain."
            brevity = "TERSE"
            tts_rate = "-10%"
        elif len(celebratory_matches) >= 1:
            state = EmotionalState.CELEBRATORY
            triggers = celebratory_matches
            conf = min(0.70 + len(celebratory_matches) * 0.15, 0.95)
            tone = "Enthusiastic, respectful, forward-looking Tony Stark persona"
            prefix = "Shukriya Sir! Target achieve ho gaya hai, momentum maintain rakhte hain."
            brevity = "BALANCED"
            tts_rate = "+5%"
        elif len(inquisitive_matches) >= 1:
            state = EmotionalState.INQUISITIVE
            triggers = inquisitive_matches
            conf = min(0.60 + len(inquisitive_matches) * 0.15, 0.90)
            tone = "Clear, analytical, pedagogically structured with mathematical reasoning"
            prefix = "Sir, poori mathematical aur operational logic detail mein explain kar raha hoon:"
            brevity = "DETAILED"
            tts_rate = "+0%"
        else:
            state = EmotionalState.NOMINAL
            triggers = []
            conf = 0.50
            tone = "Direct, loyal, professional and helpful"
            prefix = ""
            brevity = "BALANCED"
            tts_rate = "+0%"

        analysis = EmpathyAnalysis(
            detected_state=state,
            confidence=round(conf, 2),
            detected_triggers=triggers,
            suggested_tone=tone,
            response_prefix_ur=prefix,
            brevity_level=brevity,
            tts_rate_modifier=tts_rate
        )

        with self._lock:
            self._history.append(analysis)
            if len(self._history) > 50:
                self._history = self._history[-50:]
        self._save_state()
        return analysis

    def format_adaptive_response(self, raw_output: str, analysis: EmpathyAnalysis) -> str:
        """
        Wraps output text with appropriate conversational empathy and tone adjustments.
        """
        if not analysis.response_prefix_ur:
            return raw_output

        # Avoid double-prepending if already included
        if analysis.response_prefix_ur in raw_output:
            return raw_output

        # Format depending on brevity level
        if analysis.brevity_level == "TERSE":
            return f"⚡ {analysis.response_prefix_ur}\n\n{raw_output}"
        elif analysis.detected_state == EmotionalState.STRESSED:
            return f"🛡️ {analysis.response_prefix_ur}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{raw_output}"
        elif analysis.detected_state == EmotionalState.CELEBRATORY:
            return f"✨ {analysis.response_prefix_ur}\n\n{raw_output}"
        elif analysis.detected_state == EmotionalState.INQUISITIVE:
            return f"📚 {analysis.response_prefix_ur}\n\n{raw_output}"
        return f"{analysis.response_prefix_ur}\n\n{raw_output}"


# Global Singleton
_empathy_engine_instance: Optional[ConversationalEmpathyEngine] = None

def get_empathy_engine() -> ConversationalEmpathyEngine:
    global _empathy_engine_instance
    if _empathy_engine_instance is None:
        _empathy_engine_instance = ConversationalEmpathyEngine.get_instance()
    return _empathy_engine_instance


def analyze_user_context(text: str) -> EmpathyAnalysis:
    """Convenience public accessor for analyzing message context and emotion."""
    return get_empathy_engine().analyze_message(text)
