"""
actions/voice_synthesizer.py — J.A.R.V.I.S. Neural Voice & Speech Synthesis Engine
---------------------------------------------------------------------------------
Features:
- Zero-cost high-fidelity neural TTS powered by Edge-TTS (RyanNeural British & AsadNeural Urdu/English).
- Resilient offline fallback to Windows Native SAPI5 COM interface (SpVoice + SpFileStream).
- Secondary fallback to pyttsx3 offline engine.
- Asynchronous and synchronous synthesis pipelines with automatic temp file cleanup.
- Direct PCM/WAV generation and playback routing for Discord Voice Channels and local speakers.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger("VoiceSynthesizer")

BASE_DIR = Path(__file__).resolve().parent.parent
SCRATCH_DIR = BASE_DIR / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Standard Voice Personas
DEFAULT_VOICE = "en-GB-RyanNeural"       # Jarvis Classic British Persona
DEFAULT_US_VOICE = "en-US-GuyNeural"      # Jarvis US Persona
DEFAULT_URDU_VOICE = "ur-PK-AsadNeural"   # Bilingual Urdu Persona
DEFAULT_ASAD_VOICE = "ur-PK-AsadNeural"   # Asad Neural Persona
DEFAULT_FEMALE_VOICE = "en-US-AriaNeural"

SUPPORTED_VOICES = [
    "en-GB-RyanNeural",
    "ur-PK-AsadNeural",
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    "ur-PK-UzmaNeural",
]


def get_available_voices() -> List[str]:
    """Returns the list of certified supported neural voice personas."""
    return list(SUPPORTED_VOICES)


def clean_old_temp_audio_files(max_age_seconds: int = 3600) -> int:
    """Removes temporary synthesized audio files older than max_age_seconds."""
    removed_count = 0
    now = time.time()
    try:
        for p in SCRATCH_DIR.glob("jarvis_voice_*.*"):
            try:
                if p.is_file() and (now - p.stat().st_mtime) > max_age_seconds:
                    p.unlink(missing_ok=True)
                    removed_count += 1
            except Exception as e:
                logger.debug("Failed removing temp audio file %s: %s", p, e)
    except Exception as e:
        logger.debug("Error during temp audio cleanup: %s", e)
    return removed_count


async def synthesize_neural_speech_async(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_path: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%"
) -> str:
    """
    Asynchronously synthesizes speech using Edge-TTS with SAPI5 offline fallback.
    Returns the absolute path to the generated audio file (MP3 or WAV).
    """
    if not text or not text.strip():
        return ""

    clean_text = text.strip()

    if not output_path:
        file_id = f"jarvis_voice_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        output_path = str(SCRATCH_DIR / f"{file_id}.mp3")

    # Zero-API High-Fidelity Edge-TTS with automatic offline SAPI5 fallback
    if os.getenv("JARVIS_ONLINE_TTS_ENABLED", "1") != "0":
        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean_text, voice, rate=rate, pitch=pitch, volume=volume)
            await asyncio.wait_for(communicate.save(output_path), timeout=12)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return os.path.abspath(output_path)
        except Exception as e:
            logger.warning("Online speech unavailable (%s); trying local SAPI5", type(e).__name__)

    # 2. Secondary Offline Fallback: Windows Native SAPI5 (SpVoice COM)
    wav_path = str(Path(output_path).with_suffix(".wav"))
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        stream = None
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            stream.Open(wav_path, 3, False)
            speaker.AudioOutputStream = stream
            speaker.Speak(clean_text)
        finally:
            if stream is not None:
                try:
                    stream.Close()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return os.path.abspath(wav_path)
    except Exception as e:
        logger.warning("[VoiceSynthesizer] SAPI5 COM fallback failed (%s). Trying pyttsx3...", e)

    # 3. Tertiary Offline Fallback: pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(clean_text, wav_path)
        engine.runAndWait()
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return os.path.abspath(wav_path)
    except Exception as e:
        logger.error("[VoiceSynthesizer] All synthesis engines failed for text: %s (Error: %s)", clean_text[:40], e)

    return ""


def synthesize_neural_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_path: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%"
) -> str:
    """
    Synchronous entrypoint for neural speech synthesis.
    Safely executes within or outside an existing asyncio event loop.
    """
    if not text or not text.strip():
        return ""

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    lambda: asyncio.run(
                        synthesize_neural_speech_async(text, voice, output_path, rate, pitch, volume)
                    )
                )
                return future.result()
        else:
            return loop.run_until_complete(
                synthesize_neural_speech_async(text, voice, output_path, rate, pitch, volume)
            )
    except RuntimeError:
        return asyncio.run(
            synthesize_neural_speech_async(text, voice, output_path, rate, pitch, volume)
        )


def speak_text(text: str, voice: str = DEFAULT_VOICE, async_play: bool = True) -> bool:
    """
    Synthesizes and speaks text directly through the Windows default audio endpoint.
    """
    import subprocess
    import threading

    def _play_worker():
        audio_file = ""
        try:
            audio_file = synthesize_neural_speech(text, voice)
            if not audio_file or not os.path.exists(audio_file):
                return
            if audio_file.endswith(".wav"):
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            else:
                # Play mp3 via Windows Media Player COM headless
                ps_script = (
                    f"$wmp = New-Object -ComObject WMPlayer.OCX; "
                    f"$wmp.settings.volume = 100; "
                    f"$wmp.URL = '{audio_file}'; "
                    f"$wmp.controls.play(); "
                    f"Start-Sleep -Milliseconds 400; "
                    f"while ($wmp.playState -eq 3) {{ Start-Sleep -Milliseconds 100 }}"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
        except Exception as e:
            logger.debug("[VoicePlayback Notice] %s", e)
        finally:
            if audio_file and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except Exception:
                    pass

    if async_play:
        t = threading.Thread(target=_play_worker, daemon=True)
        t.start()
        return True
    else:
        _play_worker()
        return True
