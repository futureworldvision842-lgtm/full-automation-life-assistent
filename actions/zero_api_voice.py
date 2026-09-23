"""Optional local microphone listener. Offline Whisper + Windows speech by default.

Listening starts only when explicitly requested. Browser push-to-talk remains
the recommended interface because transcripts can be reviewed before execution.
"""

import os
import sys
import time
import queue
import threading
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("ZeroAPIVoice")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from actions.voice_synthesizer import synthesize_neural_speech
from core.command_router import get_command_router
from actions.local_speech import transcribe

_LISTENING_ACTIVE = False
_AUDIO_QUEUE = queue.Queue()


def is_listening() -> bool:
    global _LISTENING_ACTIVE
    return _LISTENING_ACTIVE


def speak_zero_cost(text: str, voice: str = "en-GB-RyanNeural") -> str:
    """Synthesizes and plays neural speech 100% free with zero API keys."""
    if not text:
        return ""
    try:
        audio_file = synthesize_neural_speech(text, voice=voice)
        if audio_file and os.path.exists(audio_file):
            try:
                import playsound
                playsound.playsound(audio_file, block=False)
            except Exception:
                # Play using PowerShell or Windows default player silently
                import subprocess
                subprocess.Popen(["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()"], creationflags=0x08000000)
        return audio_file
    except Exception as e:
        logger.warning("Playback warning: %s", e)
        return ""


def process_user_speech_input(spoken_text: str, feedback_callback: Optional[Callable[[str], None]] = None) -> str:
    """
    Processes spoken user text:
    1. Routes through sovereign Command Router (MT5 trade, OS app, volume, screen, etc.)
    2. If conversational query, answers via Local Ollama / Odysseus / Autonomous Browser Agent
    3. Speaks back response via Edge-TTS
    """
    clean_prompt = (spoken_text or "").strip()
    if not clean_prompt:
        return ""

    logger.info("🎙️ Heard User: '%s'", clean_prompt)
    if feedback_callback:
        feedback_callback(f"👤 You: {clean_prompt}")

    router = get_command_router()
    res = router.process_command(clean_prompt, channel="terminal", sender_id="muhammad", synthesize_audio=False)

    # Preserve denials/failures: never send a rejected action back to an LLM.
    reply_text = res.output_text if res else "No command receipt was returned."

    logger.info("🤖 J.A.R.V.I.S. Reply: %s", reply_text[:120])
    if feedback_callback:
        feedback_callback(f"⚡ JARVIS: {reply_text}")

    # Speak response
    speak_zero_cost(reply_text[:300])
    return reply_text


def start_voice_listener_background(callback: Optional[Callable[[str], None]] = None):
    """Starts continuous background voice listening loop."""
    global _LISTENING_ACTIVE
    if _LISTENING_ACTIVE:
        return
    _LISTENING_ACTIVE = True

    def _listener_worker():
        global _LISTENING_ACTIVE
        logger.info("Zero-API Voice Listener started.")
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                logger.info("Microphone calibrated. Listening for commands...")

                while _LISTENING_ACTIVE:
                    try:
                        audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=8.0)
                        try:
                            # Offline STT: never uploads microphone audio to Google.
                            receipt = transcribe(audio.get_wav_data())
                            text = receipt.get("text", "") if receipt.get("ok") else ""
                            if text:
                                process_user_speech_input(text, feedback_callback=callback)
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError:
                            pass
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        time.sleep(0.5)
        except Exception as ex:
            logger.warning("Voice listener notice: %s. Listener stopped; browser push-to-talk remains available.", ex)
            _LISTENING_ACTIVE = False

    t = threading.Thread(target=_listener_worker, daemon=True, name="ZeroAPIVoiceListener")
    t.start()


def stop_voice_listener():
    global _LISTENING_ACTIVE
    _LISTENING_ACTIVE = False
    logger.info("Zero-API Voice Listener stopped.")
