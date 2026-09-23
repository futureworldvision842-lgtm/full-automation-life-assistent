"""
tests/test_discord_intelligence_m4.py — Verification Suite for Milestone M4:
24/7 Discord Dual-Channel Intelligence Engine & Voice Gateway
-----------------------------------------------------------------------------
Comprehensive test suite verifying:
1. Dual-Channel Routing & Separation:
   - #crypto-bot (1541529106074828890) -> 100% Crypto Only.
   - #elite-trade (1541528931063177226) -> 100% Forex & Prop Accounts Only.
   - 0% cross-channel contamination or leakage.
2. Crypto Intelligence Suite:
   - High-ROI setup proposals (BTCUSD, ETHUSD, SOLUSD, SUI, TAO, ONDO).
   - Quantitative On-Chain Meme Safety Audits (anti-rug, LP lock %, honeypot test, dev distribution, safety score).
   - Macroeconomic rationale (wajohat) & predictive What-If scenarios.
3. Forex & Prop Firm Trading Suite:
   - Institutional Forex/Gold setups (XAUUSD, EURUSD, GBPUSD, USDJPY).
   - Instant trade execution tickets & dynamic breakeven locks (+1.0R SL shift).
   - Live 5-minute portfolio telemetry for Pipdance $1,000 (#5054542) & FTMO $100k (#1514382598).
   - BlackRock Aladdin 1-Day 99% VaR calculation & compliance check.
   - 15-minute high-impact economic news blackout check.
4. Neural Voice Synthesizer & Discord Voice Gateway:
   - Edge-TTS async and sync synthesis with RyanNeural & AsadNeural.
   - SAPI5 COM fallback when network offline.
   - Discord voice streaming (FFmpegPCMAudio + FileAudioSource fallback) & temp file cleanup.
5. REST API Dispatcher & Gateway Latency:
   - HTTP 200/201 response verification with mock API.
   - Bot Gateway latency tracking (<1.5s SLA).
   - 429 Rate-limit retry with exponential backoff.
"""

from __future__ import annotations

import os
import sys
import json
import time
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from actions.send_discord_intelligence_suite import (
    CRYPTO_BOT_CHANNEL_ID,
    ELITE_TRADE_CHANNEL_ID,
    get_discord_config,
    validate_channel_separation,
    send_discord_embed_with_response,
    send_discord_embed,
    send_discord_message,
    fetch_crypto_live_data,
    audit_meme_coin_safety,
    generate_crypto_intelligence_payload,
    broadcast_crypto_channel_intelligence,
    fetch_mt5_forex_data,
    calculate_aladdin_var_99,
    evaluate_news_blackout,
    build_trade_execution_ticket,
    build_breakeven_lock_alert,
    generate_portfolio_telemetry_payload,
    generate_forex_intelligence_payload,
    broadcast_forex_channel_intelligence,
    broadcast_portfolio_telemetry,
    broadcast_execution_ticket,
    broadcast_breakeven_lock,
)
from actions.voice_synthesizer import (
    synthesize_neural_speech,
    synthesize_neural_speech_async,
    speak_text,
    get_available_voices,
    clean_old_temp_audio_files,
    DEFAULT_VOICE,
    DEFAULT_URDU_VOICE,
    DEFAULT_ASAD_VOICE,
    DEFAULT_US_VOICE,
)
from bots.discord_bot import (
    bot,
    load_discord_config,
    get_bot_gateway_latency_ms,
    speak_in_discord_voice,
    FileAudioSource,
    call_jarvis_backend,
)


class TestDualChannelSeparationAndConfig(unittest.TestCase):
    """Test channel separation rules and configuration loading."""

    def test_channel_ids_and_config(self):
        self.assertEqual(CRYPTO_BOT_CHANNEL_ID, "1541529106074828890")
        self.assertEqual(ELITE_TRADE_CHANNEL_ID, "1541528931063177226")

        cfg = get_discord_config()
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg.get("crypto_bot_channel_id"), CRYPTO_BOT_CHANNEL_ID)
        self.assertEqual(cfg.get("elite_trade_channel_id"), ELITE_TRADE_CHANNEL_ID)

    def test_validate_channel_separation(self):
        # Crypto content only in crypto channel
        self.assertTrue(validate_channel_separation(CRYPTO_BOT_CHANNEL_ID, "crypto"))
        self.assertFalse(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, "crypto"))
        self.assertFalse(validate_channel_separation("1234567890", "crypto"))

        # Forex content only in elite-trade channel
        self.assertTrue(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, "forex"))
        self.assertTrue(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, "prop"))
        self.assertTrue(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, "elite_trade"))
        self.assertFalse(validate_channel_separation(CRYPTO_BOT_CHANNEL_ID, "forex"))
        self.assertFalse(validate_channel_separation("9876543210", "prop"))


class TestCryptoIntelligenceSuite(unittest.TestCase):
    """Test Crypto intelligence, setup proposals, and on-chain meme safety audits."""

    def test_fetch_crypto_live_data(self):
        data = fetch_crypto_live_data()
        self.assertIsInstance(data, dict)
        for coin in ["bitcoin", "ethereum", "solana", "sui", "pepe"]:
            self.assertIn(coin, data)
            self.assertIn("usd", data[coin])
            self.assertGreater(data[coin]["usd"], 0)

    def test_on_chain_meme_safety_audit_pass(self):
        safe_token = {
            "symbol": "PEPE",
            "lp_locked_pct": 100.0,
            "contract_renounced": True,
            "mint_authority_disabled": True,
            "buy_tax_pct": 0.0,
            "sell_tax_pct": 0.0,
            "top_10_holders_pct": 11.4,
            "honeypot_safe": True
        }
        res = audit_meme_coin_safety(safe_token)
        self.assertEqual(res["symbol"], "PEPE")
        self.assertTrue(res["passed"])
        self.assertEqual(res["safety_score"], 100.0)
        self.assertIn("VERIFIED SAFE", res["verdict"])
        self.assertEqual(len(res["risk_flags"]), 0)

    def test_on_chain_meme_safety_audit_honeypot_fail(self):
        honeypot_token = {
            "symbol": "SCAMCOIN",
            "lp_locked_pct": 100.0,
            "contract_renounced": True,
            "mint_authority_disabled": True,
            "buy_tax_pct": 0.0,
            "sell_tax_pct": 99.0,
            "top_10_holders_pct": 50.0,
            "honeypot_safe": False
        }
        res = audit_meme_coin_safety(honeypot_token)
        self.assertEqual(res["symbol"], "SCAMCOIN")
        self.assertFalse(res["passed"])
        self.assertEqual(res["safety_score"], 0.0)
        self.assertIn("FAILED", res["verdict"])
        self.assertTrue(any("HONEYPOT" in f for f in res["risk_flags"]))

    def test_on_chain_meme_safety_audit_low_lp_and_mint_active(self):
        risky_token = {
            "symbol": "RISKYDOGE",
            "lp_locked_pct": 60.0,
            "contract_renounced": False,
            "mint_authority_disabled": False,
            "buy_tax_pct": 5.0,
            "sell_tax_pct": 5.0,
            "top_10_holders_pct": 35.0,
            "honeypot_safe": True
        }
        res = audit_meme_coin_safety(risky_token)
        self.assertFalse(res["passed"])
        self.assertLess(res["safety_score"], 80.0)
        self.assertGreater(len(res["risk_flags"]), 1)

    def test_generate_crypto_intelligence_payload(self):
        embed = generate_crypto_intelligence_payload()
        self.assertIn("title", embed)
        self.assertIn("description", embed)
        self.assertIn("color", embed)
        self.assertEqual(embed["color"], 0x00E5FF)

        desc = embed["description"]
        # Verify required coins & rationale
        self.assertIn("Bitcoin (BTC/USD)", desc)
        self.assertIn("Ethereum (ETH/USD)", desc)
        self.assertIn("Solana (SOL/USD)", desc)
        self.assertIn("Wajah", desc)
        self.assertIn("ON-CHAIN MEME COIN SAFETY AUDITS", desc)
        self.assertIn("PEPE", desc)
        self.assertIn("BONK", desc)
        self.assertIn("WIF", desc)
        self.assertIn("What If Bitcoin Breaks", desc)

    def test_broadcast_crypto_channel_intelligence(self):
        with patch("actions.send_discord_intelligence_suite.send_discord_embed", return_value=True) as mock_send:
            res = broadcast_crypto_channel_intelligence()
            self.assertTrue(res)
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            self.assertEqual(args[0], CRYPTO_BOT_CHANNEL_ID)
            self.assertIn("CRYPTO", args[1]["title"])


class TestForexAndPropIntelligenceSuite(unittest.TestCase):
    """Test Forex intelligence, instant tickets, breakeven locks, and portfolio telemetry."""

    def test_fetch_mt5_forex_data(self):
        data = fetch_mt5_forex_data()
        self.assertIsInstance(data, dict)
        for sym in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            self.assertIn(sym, data)
            self.assertIn("bid", data[sym])
            self.assertIn("ask", data[sym])
            self.assertGreater(data[sym]["ask"], data[sym]["bid"])

    def test_calculate_aladdin_var_99_compliant(self):
        var_res = calculate_aladdin_var_99(equity=100000.0, daily_volatility=0.006)
        self.assertEqual(var_res["equity"], 100000.0)
        self.assertTrue(var_res["var_99_compliant"])
        self.assertIn("COMPLIANT", var_res["status"])
        self.assertLess(var_res["var_99_pct"], 2.50)
        self.assertGreater(var_res["var_99_dollar"], 0.0)
        self.assertGreater(var_res["cvar_99_dollar"], var_res["var_99_dollar"])

    def test_calculate_aladdin_var_99_exceeded(self):
        var_res = calculate_aladdin_var_99(equity=100000.0, daily_volatility=0.035)
        self.assertFalse(var_res["var_99_compliant"])
        self.assertIn("EXCEEDED", var_res["status"])
        self.assertGreater(var_res["var_99_pct"], 2.50)

    def test_evaluate_news_blackout(self):
        res = evaluate_news_blackout("XAUUSD")
        self.assertIsInstance(res, dict)
        self.assertIn("is_blackout_active", res)
        self.assertIn("symbol", res)
        self.assertEqual(res["symbol"], "XAUUSD")

    def test_build_trade_execution_ticket(self):
        ticket = build_trade_execution_ticket(
            ticket_id="TICKET-TEST-101",
            account_name="Pipdance $1,000 Fast-Track",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=4650.00,
            sl_price=4640.00,
            tp1_price=4662.00,
            tp2_price=4680.00,
            lots=0.01,
            risk_pct=0.75,
            risk_usd=7.50,
            rationale="15m Asian Low Liquidity Sweep + FVG Retracement"
        )
        self.assertIn("TICKET-TEST-101", ticket["title"])
        self.assertEqual(ticket["color"], 0x00FF88)
        desc = ticket["description"]
        self.assertIn("Pipdance $1,000 Fast-Track", desc)
        self.assertIn("0.75%", desc)
        self.assertIn("$7.50", desc)
        self.assertIn("Take Profit 1 (+1.0R / BE trigger)", desc)
        self.assertIn("Take Profit 2 (+2.5R - 3.0R Target)", desc)

    def test_build_breakeven_lock_alert(self):
        alert = build_breakeven_lock_alert(
            ticket_id="TICKET-TEST-101",
            account_name="Pipdance $1,000 Fast-Track",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=4650.00,
            old_sl=4640.00,
            new_sl=4650.45,
            current_profit_usd=7.50,
            r_multiple=1.0
        )
        self.assertIn("DYNAMIC BREAKEVEN LOCKED", alert["title"])
        desc = alert["description"]
        self.assertIn("+1.0R Gain Achieved", desc)
        self.assertIn("4650.45000", desc)
        self.assertIn("Guaranteed Zero-Loss Position", desc)

    def test_generate_portfolio_telemetry_payload(self):
        embed = generate_portfolio_telemetry_payload()
        self.assertIn("title", embed)
        self.assertEqual(embed["color"], 0x00FF88)
        desc = embed["description"]
        # Verify Pipdance $1k telemetry
        self.assertIn("PIPDANCE $1,000 2-STEP FAST-TRACK (#5054542)", desc)
        self.assertIn("Vebson-Server", desc)
        self.assertIn("0.75% Risk ($7.50 Cap)", desc)
        self.assertIn("**Trailing Floor Equity:** `$900.00`", desc)
        # Verify FTMO $100k telemetry
        self.assertIn("FTMO $100,000 INSTITUTIONAL EVALUATION (#1514382598)", desc)
        self.assertIn("FTMO-Demo", desc)
        self.assertIn("**Trailing Floor Equity:** `$90,000.00`", desc)
        self.assertIn("Aladdin 1-Day 99% VaR", desc)

    def test_generate_forex_intelligence_payload(self):
        embed = generate_forex_intelligence_payload()
        self.assertIn("title", embed)
        desc = embed["description"]
        self.assertIn("GOLD (XAU/USD)", desc)
        self.assertIn("EUR/USD", desc)
        self.assertIn("GBP/USD", desc)
        self.assertIn("USD/JPY", desc)
        self.assertIn("15-Min News Blackout", desc)
        self.assertIn("Dynamic Breakeven", desc)

    def test_broadcast_forex_and_portfolio_telemetry(self):
        with patch("actions.send_discord_intelligence_suite.send_discord_embed", return_value=True) as mock_send:
            res_f = broadcast_forex_channel_intelligence()
            self.assertTrue(res_f)
            mock_send.assert_called_with(ELITE_TRADE_CHANNEL_ID, unittest.mock.ANY)

            res_p = broadcast_portfolio_telemetry()
            self.assertTrue(res_p)

            res_t = broadcast_execution_ticket({"ticket_id": "TICKET-1"})
            self.assertTrue(res_t)

            res_b = broadcast_breakeven_lock({"ticket_id": "TICKET-1"})
            self.assertTrue(res_b)


class TestNeuralVoiceSynthesizer(unittest.TestCase):
    """Test Edge-TTS synthesis, SAPI5 offline fallback, and voice persona registry."""

    def test_get_available_voices(self):
        voices = get_available_voices()
        self.assertIn("en-GB-RyanNeural", voices)
        self.assertIn("ur-PK-AsadNeural", voices)
        self.assertIn("en-US-GuyNeural", voices)

    def test_synthesize_neural_speech_sync(self):
        text = "J.A.R.V.I.S. neural voice synthesis test."
        out = synthesize_neural_speech(text, voice=DEFAULT_VOICE)
        self.assertTrue(out)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)
        try:
            os.remove(out)
        except Exception:
            pass

    def test_synthesize_neural_speech_async(self):
        async def _run():
            text = "Asynchronous neural voice synthesis test."
            out = await synthesize_neural_speech_async(text, voice=DEFAULT_US_VOICE)
            self.assertTrue(out)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 0)
            try:
                os.remove(out)
            except Exception:
                pass

        asyncio.run(_run())

    def test_synthesize_sapi5_fallback_on_edge_tts_failure(self):
        with patch("edge_tts.Communicate.save", side_effect=Exception("Network Unreachable")):
            text = "Testing Windows SAPI5 fallback audio generation."
            out = synthesize_neural_speech(text, voice=DEFAULT_VOICE)
            self.assertTrue(out, "SAPI5 fallback must produce a valid audio file path")
            self.assertTrue(os.path.exists(out), f"File {out} must exist")
            self.assertGreater(os.path.getsize(out), 0)
            try:
                os.remove(out)
            except Exception:
                pass

    def test_clean_old_temp_audio_files(self):
        # Create a test file
        test_file = BASE_DIR / "scratch" / "jarvis_voice_test_old.mp3"
        test_file.write_bytes(b"test audio bytes")
        # Artificially age it
        os.utime(str(test_file), (time.time() - 7200, time.time() - 7200))

        cleaned = clean_old_temp_audio_files(max_age_seconds=3600)
        self.assertGreaterEqual(cleaned, 1)
        self.assertFalse(test_file.exists())


class TestDiscordBotEngineAndVoiceGateway(unittest.TestCase):
    """Test Discord bot commands, gateway latency, voice streaming, and message routing."""

    def test_get_bot_gateway_latency_ms(self):
        latency = get_bot_gateway_latency_ms()
        self.assertIsInstance(latency, float)
        self.assertLess(latency, 1500.0, "Gateway latency must be < 1.5s SLA")

    def test_file_audio_source(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"A" * 7680)
            tf_name = tf.name

        try:
            source = FileAudioSource(tf_name)
            chunk1 = source.read()
            self.assertEqual(len(chunk1), 3840)
            chunk2 = source.read()
            self.assertEqual(len(chunk2), 3840)
            chunk3 = source.read()
            self.assertEqual(len(chunk3), 0)
            source.cleanup()
        finally:
            if os.path.exists(tf_name):
                os.remove(tf_name)

    def test_speak_in_discord_voice_mocked(self):
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        mock_vc.is_playing.return_value = False

        async def _run():
            with patch("actions.voice_synthesizer.synthesize_neural_speech_async", return_value="dummy_voice.mp3"), \
                 patch("os.path.exists", return_value=True), \
                 patch("shutil.which", return_value=None):
                res = await speak_in_discord_voice(mock_vc, "Voice test message", voice=DEFAULT_VOICE)
                self.assertTrue(res)
                mock_vc.play.assert_called_once()

        asyncio.run(_run())

    def test_speak_in_discord_voice_disconnected(self):
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = False

        async def _run():
            res = await speak_in_discord_voice(mock_vc, "Test", voice=DEFAULT_VOICE)
            self.assertFalse(res)

        asyncio.run(_run())


class TestRestApiDispatcher(unittest.TestCase):
    """Test Discord REST API dispatch, latency measurement, and 429 backoff handling."""

    def test_send_discord_embed_with_response_missing_token(self):
        res = send_discord_embed_with_response(CRYPTO_BOT_CHANNEL_ID, {"title": "Test"}, token="")
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], 401)
        self.assertIn("token", res["error"].lower())

    def test_send_discord_embed_with_response_missing_channel(self):
        res = send_discord_embed_with_response("", {"title": "Test"}, token="dummy_token")
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], 400)

    def test_send_discord_embed_with_response_mock_http_200(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = send_discord_embed_with_response(
                CRYPTO_BOT_CHANNEL_ID,
                {"title": "Test Embed"},
                token="valid_test_token"
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["status"], 200)
            self.assertLess(res["latency_ms"], 1500.0)

    def test_send_discord_embed_with_response_retry_on_429(self):
        import urllib.error
        http_429 = urllib.error.HTTPError("https://discord.com", 429, "Too Many Requests", {}, None)
        mock_resp_200 = MagicMock()
        mock_resp_200.status = 201
        mock_resp_200.__enter__.return_value = mock_resp_200
        mock_resp_200.__exit__.return_value = None

        # First call raises 429, second call succeeds with 201
        with patch("urllib.request.urlopen", side_effect=[http_429, mock_resp_200]), \
             patch("time.sleep", return_value=None):
            res = send_discord_embed_with_response(
                ELITE_TRADE_CHANNEL_ID,
                {"title": "Test Retry"},
                token="valid_test_token",
                max_retries=1
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["status"], 201)
            self.assertEqual(res["attempt"], 2)


if __name__ == "__main__":
    unittest.main()
