"""
tests/test_unified_command_router.py — Comprehensive Test Suite for Milestone 4
================================================================================
Verifies:
1. High-Speed Bilingual NLP Engine (RomanUrduParser) for English and Roman Urdu.
2. Structured Telemetry Card schemas and multi-surface renderers (Terminal, Discord, Rich).
3. Unified Multi-Device Command Router across PC Terminal, Mobile (:8765), Discord Bot, and Dashboard (:8770).
4. Permission and Channel Security verification (channel separation, owner authentication).
5. 1-Shot Dynamic Skill Teaching -> AST compilation -> Vector Memory Registration.
6. Zero-Guidance Autonomous Recall & 100% Fidelity Execution.
7. Core Subsystem Action Routing (MT5 trading, OS automation, browser/vision, radar, crypto).
8. Neural Voice Synthesis Integration (Edge-TTS / SAPI5 fallback).
9. Dashboard & Discord Gateway Ingress Integration.
================================================================================
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.command_router import (
    JarvisExecutionEnvelope,
    UnifiedCommandRouter,
    get_command_router,
    route_command,
)
from core.roman_urdu_parser import (
    BilingualIntent,
    RomanUrduParser,
    get_roman_urdu_parser,
    parse_bilingual_command,
)
from core.telemetry_cards import (
    TelemetryCard,
    build_command_card,
    build_error_card,
    build_radar_card,
    build_skill_card,
    build_trading_card,
    build_vitals_card,
)
from memory import mission_memory
from skills.dynamic_compiler import DynamicSkillCompiler

ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# 1. BILINGUAL NLP ENGINE & ROMAN URDU PARSER TESTS
# ==============================================================================

class TestRomanUrduParser(unittest.TestCase):
    """Verifies English & Roman Urdu language detection, normalization, and intent parsing."""

    def setUp(self):
        self.parser = RomanUrduParser()

    def test_language_detection_english_and_urdu(self):
        """Verifies language classification accuracy across English and Roman Urdu phrasing."""
        urdu_samples = [
            "bhai gold ka status batao",
            "workstation lock kardo",
            "volume barhao aur awaz tez karo",
            "chrome kholo",
            "trade close kardo",
            "jab bhi main kahoon test to ping karo",
            "account balance kya hai",
            "tamam positions band kardo",
            "tasveer lo aur screen dekho",
            "defcon level kya hai bhai"
        ]
        for phrase in urdu_samples:
            lang = self.parser.detect_language(phrase)
            self.assertEqual(lang, "ur", f"Expected 'ur' for: '{phrase}', got '{lang}'")

        english_samples = [
            "show trading status and equity",
            "lock the workstation immediately",
            "increase volume to 80 percent",
            "open google chrome browser",
            "close all open positions",
            "whenever I say backup then create zip",
            "what is the account balance",
            "capture screen and inspect vitals",
            "search web for deepseek r1 code",
            "check system diagnostics"
        ]
        for phrase in english_samples:
            lang = self.parser.detect_language(phrase)
            self.assertEqual(lang, "en", f"Expected 'en' for: '{phrase}', got '{lang}'")

    def test_phonetic_normalization(self):
        """Verifies Roman Urdu spelling and compound verb normalization."""
        raw_text = "bhae awaz badha do aur screen shot lo aur chrome khol do"
        norm = self.parser.normalize_text(raw_text)
        self.assertIn("bhai", norm)
        self.assertIn("barhao", norm)
        self.assertIn("screenshot", norm)
        self.assertIn("kholdo", norm)

    def test_trading_intent_extraction(self):
        """Verifies trading intent, symbol, action, and lot size extraction."""
        # 1. Roman Urdu status query
        intent1 = self.parser.parse_command("bhai gold ka status batao")
        self.assertEqual(intent1.category, "trading")
        self.assertEqual(intent1.target, "XAUUSD")
        self.assertEqual(intent1.action, "status")
        self.assertEqual(intent1.language, "ur")

        # 2. English trade execution with lot size
        intent2 = self.parser.parse_command("buy 0.05 lot XAUUSD sl 2710 tp 2740")
        self.assertEqual(intent2.category, "trading")
        self.assertEqual(intent2.action, "buy")
        self.assertEqual(intent2.target, "XAUUSD")
        self.assertEqual(intent2.parameters.get("lots"), 0.05)
        self.assertEqual(intent2.parameters.get("sl"), 2710.0)
        self.assertEqual(intent2.parameters.get("tp"), 2740.0)

        # 3. Roman Urdu close trade
        intent3 = self.parser.parse_command("tamam trade close kardo")
        self.assertEqual(intent3.category, "trading")
        self.assertEqual(intent3.action, "close")

    def test_os_control_intent_extraction(self):
        """Verifies OS automation intents for locking, volume, apps, and screenshots."""
        # Lock PC (Urdu)
        lock_intent = self.parser.parse_command("workstation lock kardo")
        self.assertEqual(lock_intent.category, "os")
        self.assertEqual(lock_intent.action, "lock")

        # Volume Increase (Urdu)
        vol_intent = self.parser.parse_command("volume barhao")
        self.assertEqual(vol_intent.category, "os")
        self.assertEqual(vol_intent.action, "volume_up")

        # Set Volume to 60%
        vol_set = self.parser.parse_command("volume 60% par set kardo")
        self.assertEqual(vol_set.category, "os")
        self.assertEqual(vol_set.action, "volume_set")
        self.assertEqual(vol_set.parameters.get("value"), 60)

        # Launch Application
        app_intent = self.parser.parse_command("chrome kholo")
        self.assertEqual(app_intent.category, "os")
        self.assertEqual(app_intent.action, "launch_app")
        self.assertEqual(app_intent.target, "Google Chrome")

        # Close Application
        kill_intent = self.parser.parse_command("vscode band kardo")
        self.assertEqual(kill_intent.category, "os")
        self.assertEqual(kill_intent.action, "terminate_app")
        self.assertEqual(kill_intent.target, "Visual Studio Code")

        # Screenshot
        screen_intent = self.parser.parse_command("screen ki tasveer lo")
        self.assertEqual(screen_intent.category, "os")
        self.assertEqual(screen_intent.action, "screen_capture")

    def test_1shot_skill_teaching_intent_extraction(self):
        """Verifies extraction of 1-shot skill teaching workflows in Urdu and English."""
        # Roman Urdu pattern
        ur_teach = self.parser.parse_command("jab bhi main kahoon server_status to ping all ports karo")
        self.assertEqual(ur_teach.intent, "teach_skill")
        self.assertEqual(ur_teach.category, "skill")
        self.assertEqual(ur_teach.parameters.get("trigger"), "server_status")
        self.assertIn("ping all ports", ur_teach.parameters.get("action"))

        # English pattern
        en_teach = self.parser.parse_command("whenever I say backup_project then create zip archive of current directory")
        self.assertEqual(en_teach.intent, "teach_skill")
        self.assertEqual(en_teach.category, "skill")
        self.assertEqual(en_teach.parameters.get("trigger"), "backup_project")

    def test_radar_and_crypto_intent_extraction(self):
        """Verifies geopolitical radar and crypto market intents."""
        radar_intent = self.parser.parse_command("defcon level aur chokepoints ka haal batao")
        self.assertEqual(radar_intent.category, "radar")

        crypto_intent = self.parser.parse_command("crypto btc aur meme coin analysis karo")
        self.assertEqual(crypto_intent.category, "crypto")


# ==============================================================================
# 2. STRUCTURED TELEMETRY CARDS & RENDERER TESTS
# ==============================================================================

class TestTelemetryCards(unittest.TestCase):
    """Verifies TelemetryCard schemas, serialization, and multi-surface renderers."""

    def test_trading_telemetry_card_schema(self):
        """Verifies trading telemetry card attributes and metrics."""
        card = build_trading_card(
            symbol="XAUUSD",
            action="BUY",
            lots=0.05,
            pnl=245.50,
            equity=101245.50,
            balance=101000.00,
            var_99=488.88,
            order_id=987654,
            status="EXECUTED"
        )
        self.assertEqual(card.card_type, "trading")
        self.assertEqual(card.status, "EXECUTED")
        self.assertIn("XAUUSD", card.title)
        self.assertEqual(card.metrics["symbol"], "XAUUSD")
        self.assertEqual(card.metrics["action"], "BUY")
        self.assertEqual(card.metrics["lot_size"], "0.05 lots")
        self.assertEqual(card.metrics["ticket"], "#987654")
        self.assertGreater(card.color, 0)

        # JSON Serialization
        card_dict = card.to_dict()
        self.assertIsInstance(card_dict, dict)
        self.assertEqual(card_dict["card_type"], "trading")
        json_str = card.to_json()
        self.assertIn("XAUUSD", json_str)

    def test_vitals_telemetry_card_schema(self):
        """Verifies system vitals card generation and nominal status."""
        card = build_vitals_card(
            cpu_pct=18.5,
            ram_pct=42.0,
            gpu_pct=10.0,
            network_latency_ms=12.5,
            active_daemons=11,
            total_daemons=11
        )
        self.assertEqual(card.card_type, "system_vitals")
        self.assertEqual(card.status, "OK")
        self.assertEqual(card.metrics["cpu_utilization"], "18.5%")
        self.assertEqual(card.metrics["core_fleet_daemons"], "11/11 Active")

    def test_radar_telemetry_card_schema(self):
        """Verifies geopolitical DEFCON radar card generation."""
        card = build_radar_card(
            defcon_level=2,
            threat_status="DEFCON 2 — HEIGHTENED TENSION",
            chokepoints_disrupted=3,
            gold_multiplier=1.45
        )
        self.assertEqual(card.card_type, "geopolitical_radar")
        self.assertEqual(card.status, "DEFCON 2")
        self.assertEqual(card.metrics["global_threat_level"], "DEFCON 2")
        self.assertEqual(card.metrics["gold_macro_multiplier"], "1.45x")

    def test_skill_execution_telemetry_card_schema(self):
        """Verifies dynamic skill execution card generation."""
        card = build_skill_card(
            skill_name="calc_gold_lot",
            status="COMPILED",
            execution_time_ms=45.2,
            parameters={"risk_pct": 0.75},
            result="Synthesized skill calc_gold_lot successfully.",
            repaired=False
        )
        self.assertEqual(card.card_type, "skill_execution")
        self.assertEqual(card.status, "COMPILED")
        self.assertEqual(card.metrics["skill_name"], "calc_gold_lot")
        self.assertEqual(card.metrics["self_repaired"], "No (Zero Error)")

    def test_multi_surface_renderers(self):
        """Verifies Terminal ANSI text and Discord Embed rendering."""
        card = build_trading_card(symbol="EURUSD", action="SELL", lots=0.10, pnl=120.0)

        # 1. Terminal Text Renderer
        term_text = card.render_terminal_text()
        self.assertIn("TRADING TELEMETRY", term_text)
        self.assertIn("EURUSD", term_text)
        self.assertIn("╔", term_text)

        # 2. Discord Embed Renderer
        embed = card.render_discord_embed()
        self.assertIn("title", embed)
        self.assertIn("fields", embed)
        self.assertGreater(len(embed["fields"]), 0)
        self.assertEqual(embed["fields"][0]["name"], "Symbol")
        self.assertEqual(embed["fields"][0]["value"], "EURUSD")

        # 3. Rich Panel Renderer
        rich_panel = card.render_rich_panel()
        self.assertIsNotNone(rich_panel)


# ==============================================================================
# 3. UNIFIED COMMAND ROUTER & MULTI-DEVICE INGRESS TESTS
# ==============================================================================

class TestUnifiedCommandRouter(unittest.TestCase):
    """Verifies UnifiedCommandRouter pipeline, security gates, and multi-device routing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_router_memory.db"
        self.test_skills_dir = Path(self.temp_dir.name) / "skills"
        self.test_tests_dir = Path(self.temp_dir.name) / "tests_skills"
        self.test_skills_dir.mkdir(parents=True, exist_ok=True)
        self.test_tests_dir.mkdir(parents=True, exist_ok=True)

        self.db_patch = patch.object(mission_memory, "DB_PATH", self.test_db_path)
        self.db_patch.start()

        self.compiler = DynamicSkillCompiler(
            skills_dir=self.test_skills_dir,
            tests_dir=self.test_tests_dir
        )
        self.router = UnifiedCommandRouter(
            parser=RomanUrduParser(),
            compiler=self.compiler
        )

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_empty_and_whitespace_command(self):
        """Verifies graceful handling of empty commands."""
        env = self.router.process_command("", channel="terminal", sender_id="owner")
        self.assertFalse(env.ok)
        self.assertIn("no command", env.output_text.lower())
        self.assertEqual(env.intent, "empty")

    def test_multi_device_channel_routing(self):
        """Verifies command ingress across PC Terminal, Mobile (:8765), Dashboard, and Discord."""
        channels = ["terminal", "mobile", "dashboard", "discord_dm", "cli"]
        for chan in channels:
            env = self.router.process_command(
                command="bhai gold ka status batao",
                channel=chan,
                sender_id="owner",
                synthesize_audio=False
            )
            self.assertTrue(env.ok)
            self.assertEqual(env.channel, chan)
            self.assertEqual(env.category, "trading")
            self.assertEqual(env.language, "ur")
            self.assertIsInstance(env.telemetry, TelemetryCard)
            self.assertEqual(env.telemetry.card_type, "trading")

    def test_permission_and_channel_security_boundaries(self):
        """Verifies unauthenticated users are blocked and Discord channel separation is enforced."""
        # 1. Unauthenticated user trying to shutdown or execute raw shell
        unauth_env = self.router.process_command(
            command="!del /s /q c:\\test",
            channel="discord_dm",
            sender_id="unknown_unauthorized_user"
        )
        self.assertFalse(unauth_env.ok)
        self.assertEqual(unauth_env.intent, "unauthorized_access")
        self.assertIn("restricted", unauth_env.output_text.lower())

        # 2. Discord Channel Separation: Crypto in #elite-trade
        crypto_in_forex_env = self.router.process_command(
            command="btc crypto analysis",
            channel="discord_elite",
            sender_id="owner"
        )
        self.assertFalse(crypto_in_forex_env.ok)
        self.assertEqual(crypto_in_forex_env.intent, "channel_barrier_violation")
        self.assertIn("crypto-bot", crypto_in_forex_env.output_text)

        # 3. Discord Channel Separation: Forex in #crypto-bot
        forex_in_crypto_env = self.router.process_command(
            command="xauusd gold trade signals",
            channel="discord_crypto",
            sender_id="owner"
        )
        self.assertFalse(forex_in_crypto_env.ok)
        self.assertEqual(forex_in_crypto_env.intent, "channel_barrier_violation")
        self.assertIn("elite-trade", forex_in_crypto_env.output_text)

    def test_1shot_skill_teaching_and_vector_registration(self):
        """Verifies 1-shot skill teaching compiles code, AST validates, and registers in vector memory."""
        teach_cmd = "jab bhi main kahoon calculate_gold_lot to multiply account equity by 0.01 lot factor karo"
        env = self.router.process_command(
            command=teach_cmd,
            channel="terminal",
            sender_id="owner"
        )
        self.assertTrue(env.ok)
        self.assertEqual(env.intent, "teach_skill")
        self.assertEqual(env.routed_via, "skill_compiler")
        self.assertEqual(env.telemetry.card_type, "skill_execution")
        self.assertEqual(env.telemetry.status, "COMPILED")

        # Confirm skill exists in vector memory
        match = mission_memory.search_learned_skills("calculate_gold_lot", min_similarity=0.40)
        self.assertIsNotNone(match, "Taught skill must be indexed in vector memory.")

    def test_zero_guidance_autonomous_skill_recall(self):
        """Verifies learned skill is autonomously recalled and executed on subsequent matching command."""
        # 1. Teach skill
        teach_cmd = "whenever I say project_stats then compute files count and repository size"
        teach_env = self.router.process_command(teach_cmd, channel="terminal", sender_id="owner")
        self.assertTrue(teach_env.ok)

        # 2. Autonomous recall and execution without re-teaching
        recall_cmd = "project_stats"
        recall_env = self.router.process_command(recall_cmd, channel="terminal", sender_id="owner")
        self.assertTrue(recall_env.ok)
        self.assertEqual(recall_env.routed_via, "learned_skill")
        self.assertEqual(recall_env.telemetry.card_type, "skill_execution")
        self.assertEqual(recall_env.telemetry.status, "EXECUTED")

    def test_trading_subsystem_action_routing(self):
        """Verifies trading subsystem routing and telemetry card generation."""
        env = self.router.process_command(
            command="trade buy 0.02 lot XAUUSD sl 2715 tp 2745",
            channel="terminal",
            sender_id="owner"
        )
        self.assertTrue(env.ok)
        self.assertEqual(env.routed_via, "trading_subsystem")
        self.assertEqual(env.telemetry.card_type, "trading")
        self.assertEqual(env.telemetry.metrics["symbol"], "XAUUSD")
        self.assertEqual(env.telemetry.metrics["action"], "BUY")

    def test_os_automation_subsystem_routing(self):
        """Verifies OS control routing for lock, volume, and screenshot."""
        with patch("actions.system_control.lock_pc", return_value={"status": "OK", "message": "Workstation locked."}) as mock_lock:
            env = self.router.process_command("workstation lock kardo", channel="terminal", sender_id="owner")
            self.assertTrue(env.ok)
            self.assertEqual(env.routed_via, "os_subsystem")
            mock_lock.assert_called_once()

        with patch("actions.system_control.handle_system_control_action", return_value={"status": "OK", "message": "Volume increased."}) as mock_vol:
            env_vol = self.router.process_command("volume barhao", channel="terminal", sender_id="owner")
            self.assertTrue(env_vol.ok)
            self.assertEqual(env_vol.routed_via, "os_subsystem")
            mock_vol.assert_called_once()

    def test_geopolitical_radar_and_crypto_routing(self):
        """Verifies World Monitor radar and crypto analytics routing."""
        env_radar = self.router.process_command("world shock defcon", channel="terminal", sender_id="owner")
        self.assertTrue(env_radar.ok)
        self.assertEqual(env_radar.routed_via, "radar_subsystem")
        self.assertEqual(env_radar.telemetry.card_type, "geopolitical_radar")

        env_crypto = self.router.process_command("crypto btc live price", channel="terminal", sender_id="owner")
        self.assertTrue(env_crypto.ok)
        self.assertEqual(env_crypto.routed_via, "crypto_subsystem")

    def test_neural_voice_synthesis_feedback(self):
        """Verifies Edge-TTS / SAPI5 neural voice synthesis integration."""
        with patch("actions.voice_synthesizer.synthesize_neural_speech", return_value="C:\\temp\\voice.mp3") as mock_synth:
            # English voice persona
            env_en = self.router.process_command(
                command="show trading status",
                channel="terminal",
                sender_id="owner",
                synthesize_audio=True
            )
            self.assertTrue(env_en.ok)
            self.assertIsNotNone(env_en.audio_path)
            mock_synth.assert_called()

            # Urdu voice persona (ur-PK-AsadNeural)
            mock_synth.reset_mock()
            env_ur = self.router.process_command(
                command="bhai gold ka status batao",
                channel="terminal",
                sender_id="owner",
                synthesize_audio=True
            )
            self.assertTrue(env_ur.ok)
            self.assertIsNotNone(env_ur.audio_path)
            mock_synth.assert_called_with(mock_synth.call_args[0][0], voice="ur-PK-AsadNeural")

    def test_execution_envelope_serialization(self):
        """Verifies complete serialization of JarvisExecutionEnvelope."""
        env = self.router.process_command("status", channel="dashboard", sender_id="owner")
        d = env.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("ok", d)
        self.assertIn("command", d)
        self.assertIn("intent", d)
        self.assertIn("category", d)
        self.assertIn("channel", d)
        self.assertIn("telemetry", d)
        self.assertIsInstance(d["telemetry"], dict)
        self.assertIn("execution_time_ms", d)


if __name__ == "__main__":
    unittest.main()
