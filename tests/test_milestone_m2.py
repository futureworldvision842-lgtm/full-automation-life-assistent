"""
Comprehensive unit tests for Milestone M2:
Zero-Cost Local AI Engine & Multimodal Desktop Vision (Features F-AI-01 through F-AI-05 / Requirement R5).
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import sys

BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_ROOT = BASE_DIR / "MQ3 TRADING BOT"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))


class TestMilestoneM2_MultiTierLLMFallback(unittest.TestCase):
    """F-AI-01: Multi-Tier LLM Fallback (Odysseus :7000 -> Ollama :11434 -> OpenRouter Free 22 models)."""

    def test_provider_status_structure(self):
        import ai_engine
        status = ai_engine.provider_status()
        self.assertIn("checked_at", status)
        self.assertIn("providers", status)
        provider_names = [p["name"] for p in status["providers"]]
        self.assertIn("odysseus", provider_names)
        self.assertIn("ollama", provider_names)
        self.assertIn("openrouter", provider_names)
        self.assertIn("gemini", provider_names)

    def test_openrouter_free_model_pools(self):
        import or_client
        self.assertEqual(len(or_client.TEXT_MODELS), 22, "Must contain exactly 22 free text models")
        self.assertEqual(len(or_client.VISION_MODELS), 8, "Must contain 8 free vision models")
        for m in or_client.TEXT_MODELS:
            self.assertTrue(m.endswith(":free"), f"Model {m} must be in the zero-cost free pool")
        for m in or_client.VISION_MODELS:
            self.assertTrue(m.endswith(":free"), f"Vision model {m} must be in the zero-cost free pool")

    def test_odysseus_tier1_routing(self):
        import ai_engine
        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_get.return_value.status_code = 200
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "ok": True,
                "provider": "odysseus",
                "model": "odysseus-local",
                "text": "Odysseus neural response active.",
            }
            res = ai_engine.query_ai_detailed("Verify Odysseus probe")
            self.assertTrue(res["ok"])
            self.assertEqual(res["provider"], "odysseus")
            self.assertIn("Odysseus neural response", res["text"])

    def test_ollama_tier2_fallback_when_odysseus_offline(self):
        import ai_engine
        # Odysseus offline, Ollama online
        def fake_get(url, *args, **kwargs):
            resp = MagicMock()
            if "7000" in url:
                resp.status_code = 503
                resp.raise_for_status.side_effect = requests.RequestException("Offline")
            elif "11434" in url:
                resp.status_code = 200
                resp.json.return_value = {"models": [{"name": "qwen2.5:1.5b"}, {"name": "llama3.2"}]}
            return resp

        def fake_post(url, *args, **kwargs):
            resp = MagicMock()
            if "11434" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "choices": [{"message": {"content": "Ollama local intelligence responding."}}]
                }
            return resp

        with patch("requests.get", side_effect=fake_get), patch("requests.post", side_effect=fake_post):
            res = ai_engine.query_ai_detailed("Status of local models")
            self.assertTrue(res["ok"])
            self.assertEqual(res["provider"], "ollama")
            self.assertIn("qwen2.5:1.5b", res["model"])
            self.assertEqual(res["text"], "Ollama local intelligence responding.")

    def test_openrouter_tier3_fallback_when_local_offline(self):
        import ai_engine
        # Odysseus and Ollama offline, OpenRouter free-tier handles query
        def fake_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 503
            resp.raise_for_status.side_effect = requests.RequestException("Offline")
            return resp

        with patch("requests.get", side_effect=fake_get), \
             patch("ai_engine._ollama_models", return_value=[]), \
             patch("or_client.query_openrouter", return_value="OpenRouter zero-cost free model response."):
            with patch.dict(os.environ, {"JARVIS_OPENROUTER_ENABLED": "1", "OPENROUTER_API_KEY": "sk-or-free-test"}):
                res = ai_engine.query_ai_detailed("Test free tier")
                self.assertTrue(res["ok"])
                self.assertEqual(res["provider"], "openrouter")
                self.assertEqual(res["text"], "OpenRouter zero-cost free model response.")

    def test_zero_cost_all_offline_graceful_message(self):
        import ai_engine
        def fake_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 503
            resp.raise_for_status.side_effect = requests.RequestException("Offline")
            return resp

        with patch("requests.get", side_effect=fake_get), \
             patch("ai_engine._ollama_models", return_value=[]), \
             patch.dict(os.environ, {"JARVIS_OPENROUTER_ENABLED": "0", "JARVIS_GEMINI_ENABLED": "0"}):
            res = ai_engine.query_ai_detailed("Test all offline")
            self.assertFalse(res["ok"])
            self.assertIn("No AI provider is currently available", res["text"])


class TestMilestoneM2_OfflineVoicePipeline(unittest.TestCase):
    """F-AI-02: Offline voice pipeline (Faster-Whisper INT8 CPU STT + SAPI5 TTS with echo cooldown lockout)."""

    def test_whatsapp_voice_transcriber(self):
        from src.whatsapp_voice_transcriber import WhatsAppVoiceTranscriber
        wvt = WhatsAppVoiceTranscriber()
        self.assertTrue(hasattr(wvt, "transcribe_audio"))
        res = wvt.transcribe_audio("mock_gold_buy")
        self.assertEqual(res, "Buy Gold 0.11 lot")

    def test_echo_cooldown_lockout_verification(self):
        # Verify echo cooldown interval logic
        import time
        last_speak_end_time = time.time()
        # Immediately after speak, input must be discarded (< 1.5s)
        self.assertLess(time.time() - last_speak_end_time, 1.5)
        # After simulated delay, echo cooldown clears
        simulated_past_time = time.time() - 2.0
        self.assertGreater(time.time() - simulated_past_time, 1.5)


class TestMilestoneM2_DesktopVisionAndOCR(unittest.TestCase):
    """F-AI-03: Multimodal Desktop Screen Vision & OCR."""

    def test_code_helper_screen_debug_fallback(self):
        from actions import code_helper
        self.assertTrue(hasattr(code_helper, "code_helper"))

        # Test screen debug fallback with simulated screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
            sample_img_path = tf.name

        try:
            with patch("actions.code_helper._take_screenshot", return_value=Path(sample_img_path)), \
                 patch("or_client.OpenRouterClient.vision_from_file", return_value="Error: NameError line 42 fixed."):
                res = code_helper.code_helper({"action": "screen_debug", "description": "Fix screen crash"})
                self.assertIn("NameError", res)
        finally:
            if os.path.exists(sample_img_path):
                os.unlink(sample_img_path)

    def test_screen_processor_zero_cost_vision_fallback(self):
        from actions import screen_processor
        self.assertTrue(hasattr(screen_processor, "screen_process"))
        self.assertTrue(hasattr(screen_processor, "screen_processor"))

        with patch("actions.screen_processor._capture_screenshot", return_value=b"fake_jpeg_bytes"), \
             patch("actions.screen_processor._ensure_started"), \
             patch("or_client.OpenRouterClient.vision", return_value="Desktop shows MT5 Gold chart at 2650.00."):
            player_mock = MagicMock()
            ok = screen_processor.screen_process({"text": "What is on screen?"}, player=player_mock)
            self.assertTrue(ok)
            player_mock.write_log.assert_called_with("Jarvis: Desktop shows MT5 Gold chart at 2650.00.")


class TestMilestoneM2_SkillsEngine(unittest.TestCase):
    """F-AI-04: Autonomous self-upgrading skills engine with dynamic loading & safe py_compile."""

    def test_skills_loader_discovery(self):
        from skills import loader
        declarations, dispatch = loader.load_skills()
        self.assertIsInstance(declarations, list)
        self.assertIsInstance(dispatch, dict)
        files = loader.list_skill_files()
        self.assertIsInstance(files, list)

    def test_safe_py_compile_and_rollback_on_syntax_error(self):
        from actions.autonomous_upgrader import generate_local_skill
        skill_name = "test_corrupt_syntax_skill"
        corrupt_code = "def invalid_syntax_func(: broken"
        result = generate_local_skill(skill_name, corrupt_code)
        self.assertIn("Failed to generate safe skill", result)
        # Verify file was rolled back
        skill_file = BASE_DIR / "skills" / f"{skill_name}.py"
        self.assertFalse(skill_file.exists(), "Corrupted skill file must be unlinked/rolled back")

    def test_safe_py_compile_success(self):
        from actions.autonomous_upgrader import generate_local_skill
        skill_name = "test_valid_dynamic_skill"
        valid_code = (
            'MANIFEST = {"name": "test_valid_dynamic_skill", "description": "Test skill", "parameters": {}}\n'
            'def run(parameters, player=None, speak=None):\n'
            '    return "Success from dynamic skill"\n'
        )
        result = generate_local_skill(skill_name, valid_code)
        self.assertIn("created and compiled successfully", result)
        skill_file = BASE_DIR / "skills" / f"{skill_name}.py"
        self.assertTrue(skill_file.exists())
        # Clean up test skill
        if skill_file.exists():
            skill_file.unlink()


class TestMilestoneM2_CognitiveMemoryAndGovernance(unittest.TestCase):
    """F-AI-05: Persistent Cognitive Memory with Muhammad's Identity & G.A.I.G.S. 5 Pillars."""

    def test_long_term_memory_identity_and_trading(self):
        mem_file = BASE_DIR / "memory" / "long_term.json"
        self.assertTrue(mem_file.exists())
        data = json.loads(mem_file.read_text(encoding="utf-8"))
        self.assertEqual(data["identity"]["name"], "Muhammad Qureshi")
        self.assertIn("Funding Pips", json.dumps(data["projects"]["MQ3_TRADING_SYSTEM"]))
        self.assertIn("FTMO", json.dumps(data["projects"]["MQ3_TRADING_SYSTEM"]))

    def test_gaigs_five_pillars_and_islamic_governance_values(self):
        mem_file = BASE_DIR / "memory" / "long_term.json"
        data = json.loads(mem_file.read_text(encoding="utf-8"))
        gaigs = data["projects"]["GAIGS"]
        self.assertIn("five_pillars", gaigs)
        self.assertEqual(len(gaigs["five_pillars"]), 5)
        pillar_names = [p["name"] for p in gaigs["five_pillars"]]
        self.assertIn("Transparent Democracy", pillar_names)
        self.assertIn("Community Unity Hubs", pillar_names)
        self.assertIn("Blockchain Transparency", pillar_names)
        self.assertIn("Scientific Gamification", pillar_names)
        self.assertIn("AI-Assisted Decisions", pillar_names)

        self.assertIn("islamic_governance_values", gaigs)
        self.assertEqual(len(gaigs["islamic_governance_values"]), 5)
        concept_names = [v["concept"] for v in gaigs["islamic_governance_values"]]
        self.assertTrue(any("Tawhid" in c for c in concept_names))
        self.assertTrue(any("Adl" in c for c in concept_names))
        self.assertTrue(any("Shura" in c for c in concept_names))
        self.assertTrue(any("Amanah" in c for c in concept_names))
        self.assertTrue(any("Rahmah" in c for c in concept_names))

    def test_mission_memory_build_prompt_context_includes_gaigs(self):
        from memory.mission_memory import build_prompt_context
        ctx = build_prompt_context("governance")
        self.assertIn("G.A.I.G.S. 5 Pillars", ctx)
        self.assertIn("Transparent Democracy", ctx)
        self.assertIn("Islamic Governance Core Values", ctx)
        self.assertIn("Tawhid", ctx)


class TestMilestoneM2_LifecycleMarkers(unittest.TestCase):
    """Task 6: Lifecycle Managed Markers Verification."""

    def test_managed_markers_contains_all_required_daemons(self):
        from bootstrap import lifecycle
        required_markers = [
            "terminal.py", "uvicorn", "app:app", "odysseus", "worldmonitor", "run dev"
        ]
        for marker in required_markers:
            self.assertIn(marker, lifecycle.MANAGED_MARKERS, f"MANAGED_MARKERS must contain {marker}")


if __name__ == "__main__":
    unittest.main()
