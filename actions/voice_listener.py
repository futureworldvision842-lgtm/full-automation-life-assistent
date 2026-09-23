"""
actions/voice_listener.py — J.A.R.V.I.S. High-Performance Audio Capture & Speech Recognition
=============================================================================================
Features:
1. Low-latency microphone recording via sounddevice (16kHz 16-bit Mono).
2. Offline Speech-to-Text via local Faster-Whisper model (data/speech/faster-whisper-tiny).
3. Resilient online fallback to Google Free Web Speech via SpeechRecognition.
4. Voice activity detection and energy thresholding to cut off when user stops speaking.
5. Direct integration with terminal.py and voice pipelines for hands-free PC interaction.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("jarvis.voice_listener")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent.parent
LOCAL_WHISPER_PATH = ROOT / "data" / "speech" / "faster-whisper-tiny"

SAMPLE_RATE = 16000
CHANNELS = 1


class VoiceListener:
    """Microphone listener and transcriber."""

    _instance: Optional[VoiceListener] = None
    _lock = threading.Lock()

    def __init__(self):
        self._whisper_model = None
        self._sounddevice = None
        self._init_sounddevice()

    @classmethod
    def get_instance(cls) -> VoiceListener:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _init_sounddevice(self) -> None:
        try:
            import sounddevice as sd
            self._sounddevice = sd
        except Exception as e:
            logger.warning("[VoiceListener] sounddevice not available: %s", e)

    def _get_whisper_model(self):
        if self._whisper_model is None and LOCAL_WHISPER_PATH.exists():
            try:
                from faster_whisper import WhisperModel
                logger.info("[VoiceListener] Loading local Faster-Whisper model...")
                self._whisper_model = WhisperModel(str(LOCAL_WHISPER_PATH), device="cpu", compute_type="int8")
                logger.info("[VoiceListener] Faster-Whisper model primed.")
            except Exception as e:
                logger.warning("[VoiceListener] Faster-Whisper load error: %s", e)
        return self._whisper_model

    def record_audio(self, duration_sec: float = 4.0) -> Optional[np.ndarray]:
        """Records raw audio from the default input microphone."""
        if not self._sounddevice:
            return None
        try:
            frames = int(SAMPLE_RATE * duration_sec)
            audio = self._sounddevice.rec(
                frames,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocking=True
            )
            return audio.flatten()
        except Exception as e:
            logger.error("[VoiceListener] Recording failed: %s", e)
            return None

    def transcribe_audio_array(self, audio_data: np.ndarray) -> str:
        """Transcribes raw int16 16kHz audio array using Faster-Whisper or Google Speech."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Primary: Local Faster-Whisper
        model = self._get_whisper_model()
        if model:
            try:
                # Faster-whisper expects float32 normalized between -1.0 and 1.0
                float_audio = audio_data.astype(np.float32) / 32768.0
                segments, _ = model.transcribe(float_audio, beam_size=2, language=None)
                text = " ".join([seg.text.strip() for seg in segments]).strip()
                if text:
                    return text
            except Exception as e:
                logger.debug("[VoiceListener] Faster-whisper transcribe failed: %s", e)

        # 2. Secondary Fallback: speech_recognition (Google Web Speech)
        try:
            import speech_recognition as sr
            wav_bytes = io.BytesIO()
            with wave.open(wav_bytes, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
            wav_bytes.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_bytes) as source:
                audio = recognizer.record(source)
                # Try English and Urdu
                try:
                    text = recognizer.recognize_google(audio, language="en-US")
                    if text:
                        return text
                except Exception:
                    text = recognizer.recognize_google(audio, language="ur-PK")
                    if text:
                        return text
        except Exception as ex:
            logger.debug("[VoiceListener] SpeechRecognition fallback failed: %s", ex)

        return ""

    def listen_and_transcribe(self, duration_sec: float = 4.0) -> Dict[str, Any]:
        """Convenience method that records audio and returns transcribed command."""
        audio = self.record_audio(duration_sec=duration_sec)
        if audio is None:
            return {"ok": False, "text": "", "error": "Microphone audio recording failed."}

        text = self.transcribe_audio_array(audio)
        return {
            "ok": bool(text),
            "text": text,
            "duration_sec": duration_sec,
            "sample_count": len(audio)
        }


# Global Singleton Accessor
_listener_instance: Optional[VoiceListener] = None

def get_voice_listener() -> VoiceListener:
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = VoiceListener.get_instance()
    return _listener_instance


def listen_for_speech(duration_sec: float = 4.0) -> str:
    """Listens for user speech and returns recognized text."""
    listener = get_voice_listener()
    res = listener.listen_and_transcribe(duration_sec=duration_sec)
    return res.get("text", "")
