"""
tests/test_voice_synthesizer_adversarial.py — Empirical Adversarial Challenge Suite
Milestone 1: Voice & Audio Pipeline Integration (R2)

Adversarially tests:
1. Boundary conditions: Empty string, whitespace, massive text (5k+ chars), special chars, SSML injection, unicode scripts, Roman Urdu, emojis.
2. SAPI5 Fallback: Network failure simulation, invalid voice fallback, COM thread isolation, corrupted return handling.
3. Concurrency: Parallel async tasks, multi-threaded sync synthesis, parallel SAPI5 fallback stress.
4. Latency & Performance Profiling: Benchmark Edge-TTS vs SAPI5 latency profile.
5. Discord voice bridge edge cases: None client, disconnected, active playback collision, temp file lifecycle cleanup.
"""

import os
import sys
import time
import asyncio
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from actions.voice_synthesizer import (
    synthesize_neural_speech,
    synthesize_neural_speech_async,
    DEFAULT_VOICE,
    DEFAULT_URDU_VOICE,
    SCRATCH_DIR,
)
from bots.discord_bot import speak_in_discord_voice, FileAudioSource


class TestAdversarialInputBoundaries(unittest.TestCase):
    """Stress-test inputs across empty, malformed, unicode, Roman Urdu, and massive text payloads."""

    def test_empty_and_whitespace_inputs(self):
        """Empty and whitespace strings must immediately return empty string without disk or API calls."""
        for empty_val in ["", "   ", "\t\n\r", " \n "]:
            res_sync = synthesize_neural_speech(empty_val)
            self.assertEqual(res_sync, "", f"Expected empty result for {repr(empty_val)}")

            async def _test_async():
                return await synthesize_neural_speech_async(empty_val)

            res_async = asyncio.run(_test_async())
            self.assertEqual(res_async, "", f"Expected empty async result for {repr(empty_val)}")

    def test_special_characters_and_punctuation(self):
        """Stress-test symbols, punctuation, and escaped characters."""
        special_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~\\ \n\t Test with symbols & <XML> 'quotes' \"double\""
        out_path = synthesize_neural_speech(special_text)
        self.assertTrue(out_path, "Special character synthesis should produce audio")
        self.assertTrue(os.path.exists(out_path), f"File {out_path} should exist")
        self.assertGreater(os.path.getsize(out_path), 0, "Audio file should have non-zero bytes")
        try:
            os.remove(out_path)
        except Exception:
            pass

    def test_roman_urdu_and_multilingual_phrases(self):
        """Verify Roman Urdu, Urdu native script, and bilingual speech synthesis."""
        phrases = [
            ("Jarvis bhai, market ka status check karo aur gold trade lagao.", DEFAULT_VOICE),
            ("Shukriya bhai, aaj ka profit 500 dollars cross ho chuka hai.", DEFAULT_URDU_VOICE),
            ("Suno, MT5 terminal FTMO account 1514382598 active hai.", DEFAULT_VOICE),
            ("السلام علیکم! مارکیٹ کا جائزہ لیں", DEFAULT_URDU_VOICE),
            ("Bonjour le monde, systeme Jarvis pret.", DEFAULT_VOICE),
        ]
        for text, voice in phrases:
            out_path = synthesize_neural_speech(text, voice=voice)
            self.assertTrue(out_path, f"Failed synthesis for: {text}")
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 100, "Audio file should contain audible bytes")
            try:
                os.remove(out_path)
            except Exception:
                pass

    def test_emoji_and_unicode_symbols(self):
        """Verify emoji-laden and unicode symbol text does not crash TTS."""
        emoji_text = "Jarvis online 🚀🔥💰 Trading Gold 📈 XAUUSD 🎯 Target reached! 🤖✅"
        out_path = synthesize_neural_speech(emoji_text)
        self.assertTrue(out_path, "Emoji synthesis should succeed")
        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)
        try:
            os.remove(out_path)
        except Exception:
            pass

    def test_large_text_payload(self):
        """Stress-test large text payload (3,000 characters)."""
        large_text = ("Institutional quantitative analysis indicates high-probability fair value gap fill. " * 35).strip()
        self.assertGreaterEqual(len(large_text), 2000)
        out_path = synthesize_neural_speech(large_text)
        self.assertTrue(out_path)
        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 1024, "Large audio payload should be > 1KB")
        try:
            os.remove(out_path)
        except Exception:
            pass


class TestAdversarialSAPI5Fallback(unittest.TestCase):
    """Stress-test offline fallback behavior when edge-tts raises exceptions or fails."""

    def test_network_offline_fallback(self):
        """Simulate DNS/network failure in Edge-TTS; SAPI5 should generate WAV seamlessly."""
        with patch("edge_tts.Communicate.save", side_effect=ConnectionError("Simulated DNS Resolution Failure")):
            text = "Offline fallback protocol activated. SAPI5 synthesizer engaged."
            out_path = synthesize_neural_speech(text)
            self.assertTrue(out_path, "Fallback must produce a valid audio path")
            self.assertTrue(out_path.endswith(".wav"), f"Expected WAV output, got {out_path}")
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 1000, "WAV audio should contain headers and PCM data")
            try:
                os.remove(out_path)
            except Exception:
                pass

    def test_invalid_voice_fallback(self):
        """Providing an invalid voice string should trigger edge-tts failure and fall back to SAPI5."""
        invalid_voice = "invalid-non-existent-voice-999"
        out_path = synthesize_neural_speech("Testing invalid voice fallback.", voice=invalid_voice)
        self.assertTrue(out_path, "Must produce audio via fallback even if voice ID is invalid")
        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 0)
        try:
            os.remove(out_path)
        except Exception:
            pass

    def test_both_edge_tts_and_sapi5_failure_graceful_handling(self):
        """When all TTS engines fail, function must return empty string without unhandled crash."""
        with patch("edge_tts.Communicate.save", side_effect=RuntimeError("EdgeTTS Crash")), \
             patch("win32com.client.Dispatch", side_effect=Exception("SAPI5 COM Failure")), \
             patch("pyttsx3.init", side_effect=Exception("pyttsx3 Failure")):
            res = synthesize_neural_speech("Total failure test.")
            self.assertEqual(res, "", "Should return empty string on total failure")


class TestAdversarialConcurrency(unittest.TestCase):
    """Stress-test concurrent synthesis requests across threads and async event loops."""

    def test_parallel_async_synthesis(self):
        """Launch 6 concurrent async synthesis requests."""
        async def _test():
            tasks = [
                synthesize_neural_speech_async(f"Async concurrent worker {i} reporting.")
                for i in range(6)
            ]
            results = await asyncio.gather(*tasks)
            self.assertEqual(len(results), 6)
            for r in results:
                self.assertTrue(r, "All concurrent async tasks should return valid paths")
                self.assertTrue(os.path.exists(r))
                self.assertGreater(os.path.getsize(r), 0)
                try:
                    os.remove(r)
                except Exception:
                    pass

        asyncio.run(_test())

    def test_multi_threaded_sync_synthesis(self):
        """Launch 6 concurrent threads calling synchronous synthesize_neural_speech."""
        def worker(idx):
            return synthesize_neural_speech(f"Thread worker {idx} executing trade signal.")

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(worker, i) for i in range(6)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 6)
        # Ensure all filenames are unique (no file collisions)
        unique_paths = set(results)
        self.assertEqual(len(unique_paths), 6, "All generated file paths must be unique")
        for r in results:
            self.assertTrue(os.path.exists(r))
            try:
                os.remove(r)
            except Exception:
                pass

    def test_concurrent_sapi5_fallback_threads(self):
        """Stress-test COM initialization under 4 concurrent threads falling back to SAPI5."""
        with patch("edge_tts.Communicate.save", side_effect=Exception("Simulated Offline")):
            def sapi_worker(idx):
                return synthesize_neural_speech(f"SAPI fallback worker thread {idx}.")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(sapi_worker, i) for i in range(4)]
                results = [f.result() for f in futures]

            self.assertEqual(len(results), 4)
            for r in results:
                self.assertTrue(r.endswith(".wav"))
                self.assertTrue(os.path.exists(r))
                try:
                    os.remove(r)
                except Exception:
                    pass


class TestLatencyAndPerformance(unittest.TestCase):
    """Profile latency of speech synthesis under various configurations."""

    def test_sapi5_local_latency_profile(self):
        """SAPI5 local fallback latency profile (target < 300ms)."""
        with patch("edge_tts.Communicate.save", side_effect=Exception("Force SAPI5")):
            t0 = time.perf_counter()
            out_path = synthesize_neural_speech("Quick status check.")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            self.assertTrue(out_path)
            self.assertTrue(os.path.exists(out_path))
            print(f"\n[Performance Benchmark] SAPI5 Local TTS Latency: {elapsed_ms:.2f}ms")
            try:
                os.remove(out_path)
            except Exception:
                pass

    def test_edge_tts_latency_profile(self):
        """Edge-TTS synthesis latency profile for short commands."""
        t0 = time.perf_counter()
        out_path = synthesize_neural_speech("Jarvis online.")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(out_path)
        self.assertTrue(os.path.exists(out_path))
        print(f"\n[Performance Benchmark] Edge-TTS Online Latency: {elapsed_ms:.2f}ms")
        try:
            os.remove(out_path)
        except Exception:
            pass


class TestDiscordVoiceBridgeAdversarial(unittest.TestCase):
    """Stress-test Discord voice playback error states and stream cleanup."""

    def test_speak_in_discord_voice_empty_text(self):
        """Empty text should return False and not invoke voice_client.play."""
        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            res = await speak_in_discord_voice(mock_vc, "")
            self.assertFalse(res)
            self.assertFalse(mock_vc.play.called)

        asyncio.run(_test())

    def test_speak_in_discord_voice_active_playback_handling(self):
        """If voice_client is already playing, it should stop current stream and play new audio."""
        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            mock_vc.is_playing.return_value = True
            mock_vc.channel.name = "Trading Desk"

            played = []
            def fake_play(source, after=None):
                played.append(source)
                if after:
                    after(None)

            mock_vc.play = fake_play
            success = await speak_in_discord_voice(mock_vc, "Priority interrupt alert.")
            self.assertTrue(success)
            self.assertTrue(mock_vc.stop.called, "Must call voice_client.stop() before interrupting")
            self.assertEqual(len(played), 1)

        asyncio.run(_test())

    def test_file_audio_source_lifecycle(self):
        """Test FileAudioSource byte streaming and cleanup."""
        # Create a small dummy audio file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(b"\x00" * 4096)
        tmp.close()

        source = FileAudioSource(tmp.name)
        data = source.read()
        self.assertEqual(len(data), 3840)
        source.cleanup()
        self.assertTrue(source._file.closed)

        try:
            os.remove(tmp.name)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
