"""
voice.py ? Top-level Neural Voice Interface for J.A.R.V.I.S.
============================================================
Provides easy speak() and synthesize() functions.
"""

from actions.voice_synthesizer import speak_text, synthesize_neural_speech, DEFAULT_VOICE, DEFAULT_URDU_VOICE

def speak(text: str, voice: str = DEFAULT_VOICE, async_play: bool = True):
    """Speaks text using British Jarvis neural voice or Roman Urdu voice."""
    return speak_text(text, voice=voice, async_play=async_play)

def synthesize(text: str, voice: str = DEFAULT_VOICE, output_path: str = None) -> str:
    """Synthesizes text to audio file (MP3/WAV) and returns the file path."""
    return synthesize_neural_speech(text, voice=voice, output_path=output_path)
