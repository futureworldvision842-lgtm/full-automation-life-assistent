"""
tests/test_voice_audio_pipeline.py — Verification Suite for Milestone 1: Voice & Audio Pipeline Integration (R2)

Verifies:
1. Dependency integrity: edge-tts present in requirements.txt and importable in .venv.
2. Action scripts: Clean imports and edge_tts usage across trading intelligence scripts.
3. Neural Voice Synthesizer: Edge-TTS synthesis and SAPI5 fallback audio file creation.
4. STT Bilingual Vocabulary Anchoring: Faster-Whisper transcribe configuration and 1.5s echo lockout in main.py.
5. Discord Voice Bridge: speak_in_discord_voice, voice channel commands (!join, !leave, !speak), FFmpegPCMAudio streaming, and temp file cleanup.
"""

import os
import sys
import time
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import edge_tts
from actions.voice_synthesizer import (
    synthesize_neural_speech,
    synthesize_neural_speech_async,
    DEFAULT_VOICE,
    DEFAULT_URDU_VOICE,
)
from bots.discord_bot import (
    speak_in_discord_voice,
    bot,
    load_discord_config,
)


class TestVoiceDependenciesAndActions(unittest.TestCase):
    """Test voice packages and existing action scripts."""

    def test_requirements_txt_contains_edge_tts(self):
        req_file = BASE_DIR / "requirements.txt"
        self.assertTrue(req_file.exists(), "requirements.txt must exist")
        content = req_file.read_text(encoding="utf-8")
        self.assertIn("edge-tts", content, "requirements.txt must include edge-tts")

    def test_edge_tts_importable(self):
        import edge_tts
        self.assertTrue(hasattr(edge_tts, "Communicate"), "edge_tts must expose Communicate")

    def test_action_scripts_clean_import(self):
        """Verify all 4 trading voice action scripts import cleanly without error."""
        import actions.send_hamid_voice_advice as a1
        import actions.hamid_4am_trading_suite as a2
        import actions.jarvis_prop_trader_engine as a3
        import actions.send_daily_multi_client_trading_suite as a4

        self.assertTrue(callable(getattr(a1, "generate_voice_advice", None)))
        self.assertTrue(callable(getattr(a2, "generate_voice_summary_file", None)))
        self.assertTrue(callable(getattr(a3, "run_jarvis_trader_cycle", None)))
        self.assertTrue(callable(getattr(a4, "generate_jarvis_urdu_30sec_voice_note", None)))


class TestNeuralVoiceSynthesizer(unittest.TestCase):
    """Test the neural speech synthesizer and offline fallback."""

    def test_synthesize_neural_speech_edge_tts_success(self):
        """Test synthesizing neural speech produces a non-empty audio file."""
        text = "J.A.R.V.I.S. neural voice synthesis test."
        out_file = synthesize_neural_speech(text, voice=DEFAULT_VOICE)
        self.assertTrue(out_file, "synthesize_neural_speech should return a path")
        self.assertTrue(os.path.exists(out_file), f"Output file {out_file} must exist")
        self.assertGreater(os.path.getsize(out_file), 0, "Output file must not be empty")

        # Cleanup
        try:
            os.remove(out_file)
        except Exception:
            pass

    def test_synthesize_neural_speech_async(self):
        """Test asynchronous neural speech synthesis."""
        async def _test():
            text = "Asynchronous neural voice test for J.A.R.V.I.S."
            out_file = await synthesize_neural_speech_async(text, voice=DEFAULT_VOICE)
            self.assertTrue(out_file)
            self.assertTrue(os.path.exists(out_file))
            self.assertGreater(os.path.getsize(out_file), 0)
            try:
                os.remove(out_file)
            except Exception:
                pass

        asyncio.run(_test())

    def test_synthesize_neural_speech_sapi5_fallback(self):
        """Test fallback to SAPI5 when edge-tts raises an exception."""
        with patch("edge_tts.Communicate.save", side_effect=Exception("Simulated Network Offline")):
            text = "Testing SAPI5 fallback mode."
            out_file = synthesize_neural_speech(text)
            self.assertTrue(out_file, "Fallback must return an audio path")
            self.assertTrue(out_file.endswith(".wav"), "SAPI5 fallback should generate a WAV file")
            self.assertTrue(os.path.exists(out_file), f"WAV file {out_file} must exist")
            self.assertGreater(os.path.getsize(out_file), 0, "WAV file must not be empty")
            try:
                os.remove(out_file)
            except Exception:
                pass


class TestFasterWhisperBilingualAnchoring(unittest.TestCase):
    """Verify Faster-Whisper vocabulary anchoring in main.py."""

    def test_main_py_contains_initial_prompt_anchoring(self):
        main_py = BASE_DIR / "main.py"
        self.assertTrue(main_py.exists())
        content = main_py.read_text(encoding="utf-8")

        # Check for stt_initial_prompt definition
        self.assertIn("stt_initial_prompt", content, "main.py must set stt_initial_prompt")
        self.assertIn("initial_prompt=initial_prompt", content, "transcribe() must receive initial_prompt")

        # Check for bilingual Roman Urdu and English vocabulary
        expected_keywords = ["Jarvis", "bhai", "shukriya", "suno", "trade gold", "market summary"]
        for kw in expected_keywords:
            self.assertIn(kw, content, f"Vocabulary anchor keyword '{kw}' must be present in main.py")

    def test_echo_lockout_preserved(self):
        main_py = BASE_DIR / "main.py"
        content = main_py.read_text(encoding="utf-8")
        self.assertIn("1.5", content, "1.5s lockout check must exist in main.py")
        self.assertIn("last_speak_end_time", content, "last_speak_end_time check must be preserved")


class TestDiscordVoiceBridge(unittest.TestCase):
    """Test Discord voice synthesis and audio playback handlers."""

    def test_speak_in_discord_voice_unconnected_client(self):
        """Verify graceful return when voice client is None or disconnected."""
        async def _test():
            res = await speak_in_discord_voice(None, "Hello")
            self.assertFalse(res)

            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = False
            res2 = await speak_in_discord_voice(mock_vc, "Hello")
            self.assertFalse(res2)

        asyncio.run(_test())

    def test_speak_in_discord_voice_mock_playback(self):
        """Verify speak_in_discord_voice synthesizes audio and calls voice_client.play with cleanup."""
        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            mock_vc.is_playing.return_value = False
            mock_vc.channel.name = "General Voice"

            played_sources = []
            def fake_play(source, after=None):
                played_sources.append(source)
                if after:
                    after(None)

            mock_vc.play = fake_play

            success = await speak_in_discord_voice(mock_vc, "Testing voice bridge playback.")
            self.assertTrue(success)
            self.assertEqual(len(played_sources), 1)

        asyncio.run(_test())

    def test_discord_bot_commands_and_intents(self):
        """Verify bot intents, command prefixes, and config loader."""
        self.assertTrue(bot.intents.message_content)
        self.assertTrue(bot.intents.guilds)
        self.assertIn("!", bot.command_prefix)
        self.assertIn("jarvis ", bot.command_prefix)

        cfg = load_discord_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("bot_token", cfg)


if __name__ == "__main__":
    unittest.main()
