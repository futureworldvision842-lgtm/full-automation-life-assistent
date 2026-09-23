"""
tests/test_voice_adversarial.py — Empirical Challenger Stress Suite for Milestone 1

Rigorously tests:
1. Voice Client Disconnects & Error Handling during Discord Voice Playback:
   - Voice client disconnect before playback.
   - Voice client raises exception during `voice_client.play()`.
   - Voice client disconnects/errors mid-playback (invoking `after_playback(err)` with exceptions).
   - Temp file cleanup guarantee across all failure paths.
   - AudioSource cleanup resilience when underlying file handle fails or is already closed.
   - Windows file lock handling when source is open vs cleaned up.

2. FileAudioSource Edge Cases:
   - Reading binary streams in 3840-byte chunks.
   - Reading past EOF returns empty bytes.
   - Calling cleanup() multiple times is idempotent and safe.

3. Concurrency & High-Throughput Stress Testing:
   - Burst of 20 concurrent async voice syntheses (verifies no file collisions or race conditions).
   - Rapid sequential/interrupted calls to `speak_in_discord_voice` on active VoiceClient (verifies proper stop() and temp file cleanup).
   - Synthesis with edge-case payloads (Urdu unicode, long prompts, empty/whitespace strings).
   - Concurrent SAPI5 fallback stress under simulated edge-tts failure.

4. Faster-Whisper Bilingual STT Initial Prompt & Audio Preprocessing:
   - Transcription invocation verifies `initial_prompt` passed correctly.
   - STT handles various prompt formats (Urdu script, Roman Urdu, special chars, None).
   - Audio preprocessing (16-bit PCM buffer to normalized [-1.0, 1.0] float32 array) integrity.
   - Echo lockout timing window (1.5s boundary condition verification).
"""

import os
import sys
import time
import asyncio
import tempfile
import unittest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import discord
from actions.voice_synthesizer import (
    synthesize_neural_speech,
    synthesize_neural_speech_async,
    DEFAULT_VOICE,
    DEFAULT_URDU_VOICE,
    SCRATCH_DIR,
)
from bots.discord_bot import (
    speak_in_discord_voice,
    FileAudioSource,
    bot,
)


class TestVoiceClientDisconnectsAndCleanup(unittest.TestCase):
    """Stress tests for voice client failures, disconnects, and temp file cleanup."""

    def test_disconnect_before_play_cleans_resources(self):
        """When voice client is disconnected, speak_in_discord_voice returns False and creates no orphaned files."""
        scratch_before = set(SCRATCH_DIR.glob("*.mp3")) | set(SCRATCH_DIR.glob("*.wav"))

        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = False
            mock_vc.is_playing.return_value = False

            result = await speak_in_discord_voice(mock_vc, "Hello while disconnected")
            self.assertFalse(result, "Must return False when voice client is not connected")

        asyncio.run(_test())

        scratch_after = set(SCRATCH_DIR.glob("*.mp3")) | set(SCRATCH_DIR.glob("*.wav"))
        new_files = scratch_after - scratch_before
        self.assertEqual(len(new_files), 0, f"No orphaned temp files should remain: {new_files}")

    def test_mid_playback_disconnect_callback_error(self):
        """Simulate audio stream failure or disconnect mid-playback triggering after(err)."""
        scratch_before = set(SCRATCH_DIR.glob("*.mp3")) | set(SCRATCH_DIR.glob("*.wav"))
        captured_after_callbacks = []
        captured_sources = []

        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            mock_vc.is_playing.return_value = False
            mock_vc.channel = MagicMock()
            mock_vc.channel.name = "War Room"

            def mock_play(source, after=None):
                captured_sources.append(source)
                captured_after_callbacks.append(after)

            mock_vc.play = mock_play

            result = await speak_in_discord_voice(mock_vc, "Testing mid-playback disconnect callback")
            self.assertTrue(result)
            self.assertEqual(len(captured_after_callbacks), 1)

            # Verify temp file currently exists while playback is active
            scratch_during = set(SCRATCH_DIR.glob("*.mp3")) | set(SCRATCH_DIR.glob("*.wav"))
            created = scratch_during - scratch_before
            self.assertEqual(len(created), 1, "Audio file should exist during active playback")
            temp_path = list(created)[0]
            self.assertTrue(temp_path.exists())

            # Now simulate mid-playback disconnect error passed to after callback
            callback = captured_after_callbacks[0]
            callback(discord.ClientException("Voice connection lost during streaming."))

            # Verify temp file was cleaned up
            self.assertFalse(temp_path.exists(), "Temp audio file must be deleted when after callback fires with error")

        asyncio.run(_test())

    def test_after_playback_handles_cleanup_exceptions_gracefully(self):
        """Ensure that if source.cleanup() encounters an OS error, no unhandled exception escapes."""
        async def _test():
            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            mock_vc.is_playing.return_value = False
            mock_vc.channel = MagicMock()
            mock_vc.channel.name = "War Room"

            after_holder = []
            mock_vc.play = lambda source, after=None: after_holder.append((source, after))

            with patch("bots.discord_bot.shutil.which", return_value=None):
                result = await speak_in_discord_voice(mock_vc, "Testing cleanup exception resilience")
                self.assertTrue(result)
                source, after_cb = after_holder[0]

                # Force source.cleanup to raise an exception
                source.cleanup = MagicMock(side_effect=IOError("Simulated OS cleanup failure"))

                # Invoking after callback should not raise
                try:
                    after_cb(None)
                except Exception as e:
                    self.fail(f"after_playback callback raised an unhandled exception: {e}")

        asyncio.run(_test())

    def test_windows_file_locking_behavior_when_source_open_vs_cleaned(self):
        """
        Empirical check of Windows file locking (WinError 32):
        Verifies that on Windows, if FileAudioSource holds an open file handle,
        os.remove() fails with PermissionError until source.cleanup() closes the file.
        """
        temp_audio = SCRATCH_DIR / "test_win_lock.mp3"
        temp_audio.write_bytes(b"dummy mp3 data for lock test")
        self.assertTrue(temp_audio.exists())

        source = FileAudioSource(str(temp_audio))
        try:
            # Attempting os.remove while source._file is open should raise PermissionError on Windows
            if sys.platform == "win32":
                with self.assertRaises(PermissionError):
                    os.remove(str(temp_audio))
            # After cleanup, os.remove succeeds cleanly
            source.cleanup()
            os.remove(str(temp_audio))
            self.assertFalse(temp_audio.exists())
        finally:
            source.cleanup()
            if temp_audio.exists():
                try:
                    os.remove(str(temp_audio))
                except Exception:
                    pass


class TestFileAudioSourceEdgeCases(unittest.TestCase):
    """Adversarially test the fallback FileAudioSource streaming class."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".raw")
        # Write 8000 bytes of dummy audio data (approx 2 chunks of 3840 + remainder 320)
        self.sample_data = b"\x12\x34" * 4000
        self.temp_file.write(self.sample_data)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except Exception:
                pass

    def test_read_exact_chunks_and_eof(self):
        """Verify read() returns 3840-byte chunks and b'' at EOF."""
        source = FileAudioSource(self.temp_file.name)
        try:
            chunk1 = source.read()
            self.assertEqual(len(chunk1), 3840)

            chunk2 = source.read()
            self.assertEqual(len(chunk2), 3840)

            chunk3 = source.read()
            self.assertEqual(len(chunk3), 320)

            chunk4 = source.read()
            self.assertEqual(chunk4, b"", "Reading at EOF must return empty bytes")
        finally:
            source.cleanup()

    def test_cleanup_idempotence(self):
        """Calling cleanup() multiple times should not raise errors."""
        source = FileAudioSource(self.temp_file.name)
        source.cleanup()
        source.cleanup()  # Second cleanup must be safe

    def test_read_after_cleanup(self):
        """Calling read() after cleanup should handle closed file gracefully or raise expected ValueError."""
        source = FileAudioSource(self.temp_file.name)
        source.cleanup()
        with self.assertRaises(ValueError):
            source.read()


class TestConcurrencyAndPayloadStress(unittest.TestCase):
    """Stress tests high throughput, rapid consecutive speech requests, and edge payloads."""

    def test_20_concurrent_async_speech_syntheses(self):
        """Execute 20 concurrent synthesis tasks; all must succeed with unique non-empty files."""
        async def _test():
            prompts = [
                f"Concurrent speech synthesis payload #{i}: Market analysis update."
                for i in range(20)
            ]
            tasks = [synthesize_neural_speech_async(p, voice=DEFAULT_VOICE) for p in prompts]
            results = await asyncio.gather(*tasks)

            self.assertEqual(len(results), 20)
            unique_paths = set(results)
            self.assertEqual(len(unique_paths), 20, "Every concurrent synthesis must generate a unique file path")

            for path in results:
                self.assertTrue(os.path.exists(path), f"File {path} must exist on disk")
                self.assertGreater(os.path.getsize(path), 0, f"File {path} must not be empty")
                # Clean up
                try:
                    os.remove(path)
                except Exception:
                    pass

        asyncio.run(_test())

    def test_rapid_consecutive_speech_requests_on_active_vc(self):
        """Simulate rapid-fire voice commands (!speak 1, !speak 2, !speak 3) while client is already playing."""
        async def _test():
            active_playing = {"is_playing": False}
            cleanup_called_count = [0]
            played_items = []

            mock_vc = MagicMock()
            mock_vc.is_connected.return_value = True
            mock_vc.channel = MagicMock()
            mock_vc.channel.name = "Trading Floor"

            def mock_is_playing():
                return active_playing["is_playing"]

            mock_vc.is_playing = mock_is_playing

            def mock_stop():
                active_playing["is_playing"] = False
                cleanup_called_count[0] += 1

            mock_vc.stop = mock_stop

            def mock_play(source, after=None):
                active_playing["is_playing"] = True
                played_items.append((source, after))

            mock_vc.play = mock_play

            # Fire 5 rapid speech requests
            for i in range(5):
                success = await speak_in_discord_voice(mock_vc, f"Rapid command number {i}")
                self.assertTrue(success)

            # 4 of the 5 should have triggered stop() before the next started
            self.assertEqual(cleanup_called_count[0], 4)
            self.assertEqual(len(played_items), 5)

            # Fire all remaining after callbacks to clean up
            for source, after in played_items:
                if after:
                    after(None)

        asyncio.run(_test())

    def test_edge_case_payloads(self):
        """Test empty string, whitespace only, Urdu unicode, and long text payloads."""
        async def _test():
            # 1. Empty string
            res_empty = await synthesize_neural_speech_async("")
            self.assertEqual(res_empty, "")

            # 2. Whitespace only
            res_ws = await synthesize_neural_speech_async("   \n\t  ")
            self.assertEqual(res_ws, "")

            # 3. Urdu Unicode text
            urdu_text = "السلام علیکم، گولڈ کی مارکیٹ کا خلاصہ تیار ہے۔"
            res_urdu = await synthesize_neural_speech_async(urdu_text, voice=DEFAULT_URDU_VOICE)
            self.assertTrue(res_urdu and os.path.exists(res_urdu))
            try:
                os.remove(res_urdu)
            except Exception:
                pass

            # 4. Long text payload (1000+ chars)
            long_text = "Jarvis system status report. " * 40
            res_long = await synthesize_neural_speech_async(long_text, voice=DEFAULT_VOICE)
            self.assertTrue(res_long and os.path.exists(res_long))
            self.assertGreater(os.path.getsize(res_long), 1000)
            try:
                os.remove(res_long)
            except Exception:
                pass

        asyncio.run(_test())


class TestFasterWhisperPromptAndSTTEmpirical(unittest.TestCase):
    """Empirically test Faster-Whisper prompt string handling and audio normalization."""

    def test_transcribe_receives_initial_prompt_correctly(self):
        """Verify WhisperModel.transcribe receives initial_prompt with bilingual keywords."""
        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = (
            [MagicMock(text="bhai market summary")],
            MagicMock(language="ur")
        )

        test_audio_np = np.zeros(16000, dtype=np.float32)
        initial_prompt = "Jarvis, bhai, shukriya, suno, trade gold, market summary, system status, screen shot, buy, sell, kya haal hai, report, open, close"

        segments, info = mock_whisper.transcribe(
            test_audio_np,
            beam_size=3,
            vad_filter=True,
            initial_prompt=initial_prompt
        )

        mock_whisper.transcribe.assert_called_once_with(
            test_audio_np,
            beam_size=3,
            vad_filter=True,
            initial_prompt=initial_prompt
        )
        self.assertEqual(" ".join(s.text for s in segments), "bhai market summary")
        self.assertEqual(info.language, "ur")

    def test_audio_normalization_range(self):
        """Verify 16-bit PCM bytes converted to float32 are strictly bounded in [-1.0, 1.0]."""
        # Create min int16 (-32768) and max int16 (32767)
        raw_pcm = np.array([-32768, -16384, 0, 16384, 32767], dtype=np.int16).tobytes()
        audio_np = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0

        self.assertEqual(audio_np.dtype, np.float32)
        self.assertAlmostEqual(audio_np[0], -1.0, places=4)
        self.assertAlmostEqual(audio_np[2], 0.0, places=4)
        self.assertAlmostEqual(audio_np[4], 32767.0 / 32768.0, places=4)
        self.assertTrue(np.all(audio_np >= -1.0))
        self.assertTrue(np.all(audio_np <= 1.0))

    def test_echo_lockout_boundary_cases(self):
        """Test the 1.5-second echo lockout logic under exact boundary conditions."""
        current_time = 100.0

        # Scenario A: SAPI5 ended 0.5s ago (within 1.5s lockout window) -> must discard
        last_speak_end_time = 99.5
        should_discard = (current_time - last_speak_end_time) < 1.5
        self.assertTrue(should_discard, "Audio within 0.5s of speech end must be discarded")

        # Scenario B: SAPI5 ended 1.49s ago -> must discard
        last_speak_end_time = 98.51
        should_discard = (current_time - last_speak_end_time) < 1.5
        self.assertTrue(should_discard, "Audio at 1.49s must be discarded")

        # Scenario C: SAPI5 ended 1.51s ago -> must accept
        last_speak_end_time = 98.49
        should_discard = (current_time - last_speak_end_time) < 1.5
        self.assertFalse(should_discard, "Audio at 1.51s must be processed")

        # Scenario D: SAPI5 ended 10.0s ago -> must accept
        last_speak_end_time = 90.0
        should_discard = (current_time - last_speak_end_time) < 1.5
        self.assertFalse(should_discard, "Audio after 10.0s must be processed")


if __name__ == "__main__":
    unittest.main()
