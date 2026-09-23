"""
actions/local_speech.py — Hybrid STT Engine (Groq Whisper Turbo + Local Faster-Whisper Fallback)
---------------------------------------------------------------------------------------------
Features:
- High-speed cloud transcription (<400ms) via Groq whisper-large-v3-turbo.
- Zero-network offline fallback to local faster-whisper-tiny.
- Multilingual prompt conditioning ensuring Roman Urdu and English transliteration.
- Direct in-memory buffer processing for WhatsApp PTT voice notes and browser audio.
"""

from __future__ import annotations

import os
import json
import logging
import threading
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("SpeechEngine")

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "speech" / "faster-whisper-tiny"
CONFIG_DIR = ROOT / "config"

_model = None
_lock = threading.Lock()

# Standard prompt to steer Whisper towards Latin script / Roman Urdu command vocabulary
STANDARD_PROMPT = (
    "Jarvis voice commands in English and Roman Urdu: "
    "trades history, trade report, vitals, screenshot lo, capture screen, "
    "computer vision, screen dekho, buy gold, sell gold, close all trades, "
    "kese ho jarvis, status report, mt5 report."
)

# Common Urdu script mappings to ensure resilient routing
URDU_SCRIPT_MAP = {
    "ٹریڈز ہسٹری": "trades history",
    "ٹریڈ ہسٹری": "trades history",
    "ہسٹری": "trades history",
    "سکرین شاٹ": "screenshot",
    "اسکرین شاٹ": "screenshot",
    "تصویر لو": "screenshot",
    "کمپیوٹر": "computer",
    "وائٹلز": "vitals",
    "سونا خریدو": "buy gold 0.01",
    "سونا بیچو": "sell gold 0.01",
    "تمام ٹریڈز بند": "close all trades",
    "ساری ٹریڈز بند": "close all trades",
    "کیسے ہو": "kese ho jarvis",
    "کیا حال ہے": "kese ho jarvis",
}


def _get_groq_key() -> str:
    """Retrieves Groq API key from environment or config files."""
    k = os.environ.get("GROQ_API_KEY", "").strip()
    if k:
        return k
    key_file = CONFIG_DIR / "api_keys.json"
    if key_file.exists():
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return str(data.get("groq_api_key") or data.get("groq") or "").strip()
        except Exception:
            pass
    return ""


def status() -> Dict[str, Any]:
    """Returns the operational status of all speech-to-text engines."""
    has_groq = bool(_get_groq_key())
    has_local = (MODEL_DIR / "model.bin").exists()
    return {
        "ok": True,
        "groq_whisper_available": has_groq,
        "local_whisper_available": has_local,
        "primary_engine": "groq_whisper_large_v3_turbo" if has_groq else ("local_faster_whisper" if has_local else "none"),
        "model_dir": str(MODEL_DIR),
        "stt_loaded": _model is not None,
    }


def _normalize_transcription(text: str) -> str:
    """Normalizes transcribed text, replacing Urdu script keywords if needed."""
    clean = text.strip()
    for ur_phrase, en_cmd in URDU_SCRIPT_MAP.items():
        if ur_phrase in clean:
            clean = clean.replace(ur_phrase, en_cmd)
    return clean.strip()


def transcribe(audio: bytes, filename: str = "voice.ogg", prompt: str = "") -> Dict[str, Any]:
    """
    Transcribes raw audio bytes into clean text.
    Accepts WhatsApp OGG Opus, WebM, MP3, WAV, or M4A.
    """
    if not audio or len(audio) < 50:
        return {"ok": False, "error": "audio_payload_empty", "text": ""}
    if len(audio) > 16 * 1024 * 1024:
        return {"ok": False, "error": "audio_too_large", "text": ""}

    active_prompt = prompt or STANDARD_PROMPT
    groq_key = _get_groq_key()

    # 1. Primary High-Speed Engine: Groq Whisper Large v3 Turbo
    if groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1", timeout=15.0)
            file_tuple = (filename if "." in filename else f"{filename}.ogg", audio)
            resp = client.audio.transcriptions.create(
                file=file_tuple,
                model="whisper-large-v3-turbo",
                response_format="json",
                prompt=active_prompt,
            )
            raw_text = resp.text.strip() if hasattr(resp, "text") else ""
            if raw_text:
                norm_text = _normalize_transcription(raw_text)
                return {
                    "ok": True,
                    "text": norm_text,
                    "raw_text": raw_text,
                    "provider": "groq-whisper-turbo",
                    "executed": False,
                }
        except Exception as e:
            logger.warning("[SpeechEngine] Groq Whisper failed: %s. Falling back to local whisper.", e)

    # 2. Secondary Offline Engine: Local Faster-Whisper
    global _model
    if not (MODEL_DIR / "model.bin").exists():
        return {
            "ok": False,
            "error": "stt_model_unavailable",
            "message": "Groq speech failed and local faster-whisper model weights are missing.",
            "text": ""
        }

    if not _lock.acquire(blocking=True, timeout=10.0):
        return {"ok": False, "error": "speech_engine_busy", "text": ""}

    temp_path = None
    try:
        from faster_whisper import WhisperModel
        if _model is None:
            _model = WhisperModel(
                str(MODEL_DIR),
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
                local_files_only=True
            )
        scratch = ROOT / "scratch" / "speech"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=scratch, suffix=f"_{filename}", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(audio)

        segments, info = _model.transcribe(str(temp_path), beam_size=1, vad_filter=True)
        raw_text = " ".join(s.text.strip() for s in segments).strip()
        norm_text = _normalize_transcription(raw_text)
        return {
            "ok": bool(norm_text),
            "text": norm_text,
            "raw_text": raw_text,
            "language": info.language,
            "duration": info.duration,
            "provider": "local-faster-whisper",
            "executed": False
        }
    except Exception as exc:
        logger.error("[SpeechEngine] Local faster-whisper error: %s", exc)
        return {"ok": False, "error": type(exc).__name__, "message": str(exc), "text": ""}
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
        _lock.release()
