"""
tests/test_challenger2_m3_empirical_stress.py — Master Empirical Challenger 2 Stress Harness.
=============================================================================================
Comprehensive empirical stress test suite for Milestone 3 (Requirement R3: Dynamic Multi-Account Law & Rule Auto-Calibrator):
1. Platform Profile Coverage across all 8 platforms (Funding Pips, FTMO, MyFundedFX, Personal MT5, Binance Spot, Binance Futures, Hyperliquid DEX, Scalp 5M).
2. WhatsApp Natural Language & Structured Onboarding Directive Ingestion.
3. Malformed, Corrupted, Boundary, and Adversarial Onboarding Commands.
4. Atomic Updates, Race Conditions, and High-Concurrency Multi-Threaded Stress on Fleet Config.
5. Whitelist Security, Spoofing Resistance, and Null-Byte/Control-Character Adversarial Payloads.
6. End-to-End Integration between WhatsApp QR Manager, MultiAccountAutoOnboarder, and FleetRiskManager.
"""

import os
import re
import json
import time
import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.whatsapp_copilot import is_whitelisted_number, AUTHORIZED_CONTACTS, ELITE_TRADE_GROUP_JID
from src.fleet_risk_manager import FleetRiskManager


class TestPlatformProfilesAndLawCalibration(unittest.TestCase):
    """
    Validates complete mathematical calibration across all 8 platform profiles.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="fleet_test_")
        self.test_config = os.path.join(self.temp_dir, "fleet_config.json")
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_funding_pips_calibration(self):
        """Funding Pips: 2.5% daily loss, 6.0% max loss, 0.75% risk, 35% consistency, LIVE_MT5."""
        res = self.onboarder.onboard_new_account("FP_50K", "FundingPips-Live", 50000.0, "FUNDING_PIPS")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 1250.0)
        self.assertEqual(acc["trailing_hwm_floor"], 47000.0)
        self.assertEqual(acc["risk_per_trade_pct"], 0.0075)
        self.assertEqual(acc["consistency_cap_pct"], 35.0)
        self.assertEqual(acc["execution_mode"], "LIVE_MT5")
        self.assertIn("XAUUSD", acc["allowed_assets"])

    def test_ftmo_calibration(self):
        """FTMO: 4.0% daily loss, 8.0% max loss, 1.0% risk, 50% consistency, LIVE_MT5."""
        res = self.onboarder.onboard_new_account("FTMO_100K", "FTMO-Live", 100000.0, "FTMO")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 4000.0)
        self.assertEqual(acc["trailing_hwm_floor"], 92000.0)
        self.assertEqual(acc["risk_per_trade_pct"], 0.01)
        self.assertEqual(acc["consistency_cap_pct"], 50.0)
        self.assertEqual(acc["execution_mode"], "LIVE_MT5")

    def test_myfundedfx_calibration(self):
        """MyFundedFX: 4.0% daily loss, 6.0% max loss, 0.75% risk, 40% consistency, LIVE_MT5."""
        res = self.onboarder.onboard_new_account("MFF_25K", "MyFundedFX-Server", 25000.0, "MYFUNDEDFX")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 1000.0)
        self.assertEqual(acc["trailing_hwm_floor"], 23500.0)
        self.assertEqual(acc["risk_per_trade_pct"], 0.0075)
        self.assertEqual(acc["consistency_cap_pct"], 40.0)
        self.assertEqual(acc["execution_mode"], "LIVE_MT5")

    def test_personal_mt5_calibration(self):
        """Personal MT5: 5.0% daily loss, 15.0% max loss, 1.5% risk, 100% consistency, LIVE_MT5."""
        res = self.onboarder.onboard_new_account("ICM_10K", "ICMarkets-Live", 10000.0, "PERSONAL_MT5")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 500.0)
        self.assertEqual(acc["trailing_hwm_floor"], 8500.0)
        self.assertEqual(acc["risk_per_trade_pct"], 0.015)
        self.assertEqual(acc["consistency_cap_pct"], 100.0)
        self.assertEqual(acc["execution_mode"], "LIVE_MT5")
        self.assertIn("SOLUSD", acc["allowed_assets"])

    def test_binance_spot_calibration(self):
        """Binance Spot: 5.0% daily loss, 20.0% max loss, 1.5% risk, CRYPTO_BINANCE_SPOT."""
        res = self.onboarder.onboard_new_account("BIN_SPOT", "Binance-Live", 2000.0, "BINANCE_SPOT")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 100.0)
        self.assertEqual(acc["trailing_hwm_floor"], 1600.0)
        self.assertEqual(acc["risk_per_trade_pct"], 0.015)
        self.assertEqual(acc["execution_mode"], "CRYPTO_BINANCE_SPOT")
        self.assertIn("BNBUSDT", acc["allowed_assets"])
        self.assertIn("XRPUSDT", acc["allowed_assets"])

    def test_binance_futures_calibration(self):
        """Binance Futures: 5.0% daily loss, 20.0% max loss, 1.5% risk, CRYPTO_BINANCE_FUTURES."""
        res = self.onboarder.onboard_new_account("BIN_FUT", "Binance-Live", 3000.0, "BINANCE_FUTURES")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 150.0)
        self.assertEqual(acc["trailing_hwm_floor"], 2400.0)
        self.assertEqual(acc["execution_mode"], "CRYPTO_BINANCE_FUTURES")
        self.assertIn("BTCUSDT", acc["allowed_assets"])

    def test_hyperliquid_dex_calibration(self):
        """Hyperliquid: 5.0% daily loss, 20.0% max loss, 1.5% risk, CRYPTO_HYPERLIQUID."""
        res = self.onboarder.onboard_new_account("HL_DEX", "Hyperliquid-Mainnet", 500.0, "HYPERLIQUID")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 25.0)
        self.assertEqual(acc["trailing_hwm_floor"], 400.0)
        self.assertEqual(acc["execution_mode"], "CRYPTO_HYPERLIQUID")
        self.assertIn("BTC-PERP", acc["allowed_assets"])
        self.assertIn("ETH-PERP", acc["allowed_assets"])

    def test_scalp5m_calibration(self):
        """Scalp 5M: 5.0% daily loss, 20.0% max loss, 1.5% risk, CRYPTO_BINANCE."""
        res = self.onboarder.onboard_new_account("SCALP_100", "Binance-Live", 100.0, "SCALP_5M")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["daily_loss_dollar_cap"], 5.0)
        self.assertEqual(acc["trailing_hwm_floor"], 80.0)
        self.assertEqual(acc["execution_mode"], "CRYPTO_BINANCE")
        self.assertIn("BTCUSDT", acc["allowed_assets"])
        self.assertIn("BTC-PERP", acc["allowed_assets"])

    def test_alias_normalization_matrix(self):
        """Comprehensive verification of all platform alias variations."""
        test_cases = [
            ("funding_pips", "FUNDING_PIPS"),
            ("fundingpips", "FUNDING_PIPS"),
            ("FUNDING PIPS", "FUNDING_PIPS"),
            ("fp", "FUNDING_PIPS"),
            ("funding", "FUNDING_PIPS"),
            ("ftmo", "FTMO"),
            ("myfundedfx", "MYFUNDEDFX"),
            ("my_funded_fx", "MYFUNDEDFX"),
            ("MY FUNDED FX", "MYFUNDEDFX"),
            ("mff", "MYFUNDEDFX"),
            ("personal_mt5", "PERSONAL_MT5"),
            ("personalmt5", "PERSONAL_MT5"),
            ("PERSONAL MT5", "PERSONAL_MT5"),
            ("personal", "PERSONAL_MT5"),
            ("icmarkets", "PERSONAL_MT5"),
            ("exness", "PERSONAL_MT5"),
            ("pepperstone", "PERSONAL_MT5"),
            ("oanda", "PERSONAL_MT5"),
            ("binance_spot", "BINANCE_SPOT"),
            ("binancespot", "BINANCE_SPOT"),
            ("spot", "BINANCE_SPOT"),
            ("binance_futures", "BINANCE_FUTURES"),
            ("binancefutures", "BINANCE_FUTURES"),
            ("futures", "BINANCE_FUTURES"),
            ("perp", "BINANCE_FUTURES"),
            ("binance_perp", "BINANCE_FUTURES"),
            ("hyperliquid", "HYPERLIQUID"),
            ("hyperliquid_dex", "HYPERLIQUID"),
            ("hl", "HYPERLIQUID"),
            ("dex", "HYPERLIQUID"),
            ("scalp_5m", "SCALP_5M"),
            ("scalp5m", "SCALP_5M"),
            ("scalp", "SCALP_5M"),
            ("5m", "SCALP_5M"),
            ("crypto", "CRYPTO_EXCHANGE"),
            ("binance", "BINANCE_SPOT"),
            (None, "FUNDING_PIPS"),
            ("", "FUNDING_PIPS"),
            ("unknown_custom_prop", "FUNDING_PIPS")
        ]
        for raw, expected in test_cases:
            result = MultiAccountAutoOnboarder.normalize_account_type(raw)
            self.assertEqual(result, expected, f"Alias failed: '{raw}' -> got '{result}', expected '{expected}'")


class TestWhatsAppDirectiveIngestion(unittest.TestCase):
    """
    Stress-tests natural language and structured WhatsApp onboarding directive parsing.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="directive_test_")
        self.test_config = os.path.join(self.temp_dir, "fleet_config.json")
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_structured_prop_firm_directive(self):
        """Standard structured command with all tokens."""
        cmd = "onboard account 5054340275 server MetaQuotes-Demo balance 25000 type FundingPips"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["account_id"], "5054340275")
        self.assertEqual(acc["server"], "MetaQuotes-Demo")
        self.assertEqual(acc["starting_balance"], 25000.0)
        self.assertEqual(acc["account_type"], "FUNDING_PIPS")

    def test_crypto_exchange_scalp5m_directive(self):
        """Crypto exchange syntax for Scalp5m."""
        cmd = "onboard crypto exchange Binance balance 100 type Scalp5m"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["account_id"], "BINANCE_100")
        self.assertEqual(acc["server"], "Binance-Live")
        self.assertEqual(acc["starting_balance"], 100.0)
        self.assertEqual(acc["account_type"], "SCALP_5M")
        self.assertEqual(acc["daily_loss_dollar_cap"], 5.0)

    def test_crypto_exchange_hyperliquid_dex_directive(self):
        """Crypto exchange syntax for Hyperliquid DEX."""
        cmd = "onboard crypto exchange Hyperliquid balance 500 type DEX"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["account_id"], "HYPERLIQUID_500")
        self.assertEqual(acc["server"], "Hyperliquid-Mainnet")
        self.assertEqual(acc["starting_balance"], 500.0)
        self.assertEqual(acc["account_type"], "HYPERLIQUID")
        self.assertEqual(acc["execution_mode"], "CRYPTO_HYPERLIQUID")

    def test_crypto_direct_syntax(self):
        """Direct syntax without 'exchange' keyword: onboard binance balance 1000 type spot."""
        cmd = "onboard binance balance 1000 type spot"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["starting_balance"], 1000.0)
        self.assertEqual(acc["account_type"], "BINANCE_SPOT")

    def test_dollar_sign_balance_parsing(self):
        """Balance formatted with $ symbol: onboard account 9999 server Live balance $50000 type FTMO."""
        cmd = "onboard account 9999 server Live balance $50000 type FTMO"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["account_data"]["starting_balance"], 50000.0)
        self.assertEqual(res["account_data"]["account_type"], "FTMO")

    def test_custom_risk_specification_in_directive(self):
        """Directive specifying custom risk: onboard account 1122 server Demo balance 100000 type FTMO risk 0.5%."""
        cmd = "onboard account 1122 server Demo balance 100000 type FTMO risk 0.5%"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["account_data"]["risk_per_trade_pct"], 0.005)

    def test_onboard_directive_confirmation_message_formatting(self):
        """Verifies clear, structured confirmation message generation."""
        cmd = "onboard account 776655 server MyFundedFX-Server balance 25000 type MyFundedFX"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        msg = res["message"]
        self.assertIn("Account #776655 (MYFUNDEDFX) onboarded successfully!", msg)
        self.assertIn("• Platform / Server: MyFundedFX-Server", msg)
        self.assertIn("• Starting Balance: $25,000.00", msg)
        self.assertIn("• Daily Loss Cap: $1,000.00 (4.00%)", msg)
        self.assertIn("• Trailing Floor: $23,500.00 (6.00% max loss)", msg)
        self.assertIn("• Execution Mode: LIVE_MT5", msg)
        self.assertIn("• Risk per Trade: 0.75%", msg)


class TestAdversarialAndMalformedDirectives(unittest.TestCase):
    """
    Stress-tests malformed, corrupted, boundary, and adversarial inputs.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="malformed_test_")
        self.test_config = os.path.join(self.temp_dir, "fleet_config.json")
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_non_onboard_messages_gracefully_ignored(self):
        """Non-onboard commands return None without exceptions."""
        non_onboard = [
            "buy xauusd 0.1",
            "what is the gold plan today?",
            "status",
            "fleet",
            "",
            "   ",
            "onboarding is great",  # doesn't start with 'onboard '
            "help",
            "12345"
        ]
        for msg in non_onboard:
            res = self.onboarder.parse_whatsapp_onboard_directive(msg)
            self.assertIsNone(res, f"Expected None for non-directive: '{msg}'")

    def test_missing_balance_directive(self):
        """Directive missing balance token returns None."""
        cmd = "onboard account 12345 server MetaQuotes-Demo type FundingPips"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNone(res)

    def test_non_numeric_balance_directive(self):
        """Directive with non-numeric balance returns None."""
        cmd = "onboard account 12345 server MetaQuotes-Demo balance abc type FundingPips"
        res = self.onboarder.parse_whatsapp_onboard_directive(cmd)
        self.assertIsNone(res)

    def test_boundary_micro_balance(self):
        """Micro balance $0.01 handled safely without division-by-zero."""
        res = self.onboarder.onboard_new_account("MICRO_01", "Personal-Live", 0.01, "PERSONAL_MT5")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["starting_balance"], 0.01)
        self.assertEqual(acc["daily_loss_dollar_cap"], 0.0)
        self.assertEqual(acc["trailing_hwm_floor"], 0.01)

    def test_boundary_sovereign_wealth_balance(self):
        """Massive sovereign wealth balance ($100 Trillion) handled accurately."""
        huge_balance = 100_000_000_000_000.0
        res = self.onboarder.onboard_new_account("SOV_01", "FundingPips-Live", huge_balance, "FUNDING_PIPS")
        self.assertTrue(res["success"])
        acc = res["account_data"]
        self.assertEqual(acc["starting_balance"], huge_balance)
        self.assertEqual(acc["daily_loss_dollar_cap"], 2_500_000_000_000.0)
        self.assertEqual(acc["trailing_hwm_floor"], 94_000_000_000_000.0)

    def test_adversarial_injection_payloads_in_account_id(self):
        """Tests XSS, SQLi, Path Traversal, and Template Injection payloads in account ID."""
        payloads = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE accounts; --",
            "admin' OR '1'='1",
            "../../../../etc/passwd",
            "{{ 7 * 7 }}",
            "ACC~!@#$%^&*()_+{}[]:;'<>,.?/",
            "حساب_محمد_١٢٣",
            "测试账户_PropFirm_888",
            "ACC-🔥-ALPHA-99"
        ]
        for payload in payloads:
            res = self.onboarder.onboard_new_account(
                account_id=payload,
                server="TestServer",
                balance=10000.0,
                account_type="FTMO"
            )
            self.assertTrue(res["success"], f"Failed to onboard with payload: {payload}")
            self.assertIn(f"account_{payload}", self.onboarder.fleet["fleet"])

        # Reload fleet from disk to verify JSON serialization integrity
        reloaded = MultiAccountAutoOnboarder(config_path=self.test_config)
        for payload in payloads:
            self.assertIn(f"account_{payload}", reloaded.fleet["fleet"])


class TestFleetConfigConcurrencyAndAtomicSafety(unittest.TestCase):
    """
    Stress-tests multi-threaded concurrent onboarding and JSON persistence integrity.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="concurrency_test_")
        self.test_config = os.path.join(self.temp_dir, "fleet_config.json")
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multi_threaded_concurrent_onboarding_stress(self):
        """Simulates 50 concurrent onboarding threads writing simultaneously."""
        num_threads = 50
        errors = []
        results = []

        def worker(thread_idx: int):
            try:
                acc_id = f"BURST_ACC_{thread_idx:04d}"
                acc_type = "FUNDING_PIPS" if thread_idx % 2 == 0 else "HYPERLIQUID"
                balance = 25000.0 + (thread_idx * 100.0)
                res = self.onboarder.onboard_new_account(
                    account_id=acc_id,
                    server=f"{acc_type}-Server",
                    balance=balance,
                    account_type=acc_type
                )
                if not res.get("success"):
                    errors.append(f"Thread {thread_idx} returned failure: {res}")
                results.append(res)
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")
        self.assertEqual(len(results), num_threads)

        # Verify JSON file validity on disk
        self.assertTrue(os.path.exists(self.test_config))
        with open(self.test_config, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("fleet", data)
        self.assertIn("active_accounts", data)
        self.assertIn("total_aum_potential", data)
        self.assertGreaterEqual(data["active_accounts"], 1)

    def test_corrupted_config_file_fallback(self):
        """Verifies automatic fallback to default fleet when config file is corrupted."""
        with open(self.test_config, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON DATA CORRUPTED FILE ###")

        fallback_onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        self.assertIn("account_25k", fallback_onboarder.fleet["fleet"])
        self.assertEqual(fallback_onboarder.fleet["active_accounts"], 1)
        self.assertEqual(fallback_onboarder.fleet["total_aum_potential"], 25000.0)


class TestWhitelistSecurityAndAdversarialPayloads(unittest.TestCase):
    """
    Stress-tests whitelist authentication, spoofing resistance, and control character payloads.
    """

    def setUp(self):
        self.qr = WhatsAppQRManager()
        self.authorized_jid = "923468053268@s.whatsapp.net"
        self.elite_group_jid = ELITE_TRADE_GROUP_JID

    def test_authorized_master_owner_allowed(self):
        """Master owner phone JID and LID are whitelisted."""
        self.assertTrue(is_whitelisted_number("923468053268@s.whatsapp.net"))
        self.assertTrue(is_whitelisted_number("923468053268"))
        self.assertTrue(is_whitelisted_number("+92 346 8053268"))
        self.assertTrue(is_whitelisted_number("923468053268:1@s.whatsapp.net"))
        self.assertTrue(is_whitelisted_number("923468053268@lid"))
        self.assertTrue(is_whitelisted_number("master_user@lid"))
        self.assertTrue(is_whitelisted_number("linked_device_user@lid"))

    def test_elite_trade_group_participant_gating(self):
        """Elite Trade Group requires whitelisted participant JID."""
        # Elite group with authorized participant -> ALLOWED
        self.assertTrue(is_whitelisted_number(self.elite_group_jid, participant_jid=self.authorized_jid))
        # Elite group with unapproved participant -> BLOCKED
        self.assertFalse(is_whitelisted_number(self.elite_group_jid, participant_jid="923001122334@s.whatsapp.net"))
        # Elite group with unapproved LID participant -> BLOCKED
        self.assertFalse(is_whitelisted_number(self.elite_group_jid, participant_jid="unknown_attacker@lid"))

    def test_unapproved_groups_blocked(self):
        """Unapproved WhatsApp groups are strictly dropped."""
        unapproved_groups = [
            "120363000000000000@g.us",
            "random_forex_signals@g.us",
            "crypto_whales_vip@g.us"
        ]
        for g in unapproved_groups:
            self.assertFalse(is_whitelisted_number(g))
            reply = self.qr.handle_incoming_command("status", g)
            self.assertEqual(reply, "")

    def test_status_broadcasts_blocked(self):
        """Status broadcast channels are strictly dropped."""
        self.assertFalse(is_whitelisted_number("status@broadcast"))
        self.assertFalse(is_whitelisted_number("broadcast@s.whatsapp.net"))

    def test_purged_secondary_contacts_permanently_blocked(self):
        """Explicitly tests that purged contacts from Milestone 1 cannot bypass whitelist."""
        purged = [
            "923487117832@s.whatsapp.net",
            "923322555238@s.whatsapp.net",
            "923375893095@s.whatsapp.net",
            "923487117832",
            "923322555238",
            "923375893095"
        ]
        for num in purged:
            self.assertFalse(is_whitelisted_number(num), f"Purged number passed whitelist: {num}")
            reply = self.qr.handle_incoming_command("status", num)
            self.assertEqual(reply, "")

    def test_adversarial_null_byte_and_control_characters(self):
        """Adversarial payloads with null bytes, newlines, and control characters must be rejected."""
        adversarial_jids = [
            "923468053268\x00@s.whatsapp.net",
            "\x00923468053268@s.whatsapp.net",
            "923468053268\r\n@s.whatsapp.net",
            "923468053268\x1b@s.whatsapp.net",
            "923468053268\x08@s.whatsapp.net",
            "923468053268\x7f@s.whatsapp.net",
            "923468053268\t@s.whatsapp.net",
            "923468053268;DROP TABLE--@s.whatsapp.net",
            "923468053268admin@s.whatsapp.net",
            "923468053268@s.whatsapp.net.evil.com",
            "923468053268:abc@s.whatsapp.net",
            "923468053268:1:2@s.whatsapp.net"
        ]
        for jid in adversarial_jids:
            self.assertFalse(is_whitelisted_number(jid), f"Adversarial JID bypassed security: {repr(jid)}")
            reply = self.qr.handle_incoming_command("status", jid)
            self.assertEqual(reply, "", f"Adversarial JID triggered response: {repr(jid)}")

    def test_phone_number_formatting_and_country_code_handling(self):
        """Tests that Pakistani country code formats (0092, 0346, +92) normalize correctly."""
        valid_formats = [
            "00923468053268@s.whatsapp.net",
            "03468053268@s.whatsapp.net",
            "+923468053268@s.whatsapp.net",
            "+92-346-8053268@s.whatsapp.net",
            "923468053268@s.whatsapp.net"
        ]
        for fmt in valid_formats:
            self.assertTrue(is_whitelisted_number(fmt), f"Failed for valid phone format: {fmt}")

    def test_type_safety_with_invalid_types(self):
        """Passing non-string or None to is_whitelisted_number returns False safely."""
        invalid_types = [None, 12345, 923468053268, ["923468053268"], {"jid": "923468053268"}, True, False]
        for inv in invalid_types:
            self.assertFalse(is_whitelisted_number(inv))


class TestHighVolumeConcurrencyStress(unittest.TestCase):
    """
    Simulates high-volume concurrent read and write operations.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="high_vol_test_")
        self.test_config = os.path.join(self.temp_dir, "fleet_config.json")
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_reads_and_writes_high_volume(self):
        """Tests 100 concurrent workers performing simultaneous onboarding and reads."""
        num_workers = 100
        errors = []

        def worker_task(idx: int):
            try:
                if idx % 2 == 0:
                    # Write operation
                    acc_id = f"HIGH_VOL_ACC_{idx}"
                    res = self.onboarder.onboard_new_account(
                        account_id=acc_id,
                        server="Server-Test",
                        balance=10000.0 + idx,
                        account_type="FUNDING_PIPS"
                    )
                    if not res.get("success"):
                        errors.append(f"Write failed at {idx}")
                else:
                    # Read operation
                    fleet = self.onboarder._load_fleet()
                    if not isinstance(fleet, dict) or "fleet" not in fleet:
                        errors.append(f"Read corrupted fleet at {idx}")
            except Exception as e:
                errors.append(f"Worker {idx} error: {e}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]
            for f in as_completed(futures):
                f.result()

        self.assertEqual(len(errors), 0, f"High volume concurrency encountered errors: {errors}")


class TestWhatsAppQRManagerE2EIntegration(unittest.TestCase):
    """
    End-to-end integration between WhatsApp QR Manager, AutoOnboarder, and FleetRiskManager.
    """

    def setUp(self):
        self.qr = WhatsAppQRManager()
        self.authorized_sender = "923468053268@s.whatsapp.net"

    def test_e2e_whatsapp_mt5_onboard_command(self):
        """End-to-end MT5 onboarding directive through WhatsApp QR Manager."""
        cmd = "onboard account 88332211 server IC-Live balance 5000 type PersonalMT5"
        reply = self.qr.handle_incoming_command(cmd, self.authorized_sender)
        self.assertIn("ACCOUNT ONBOARDED SUCCESSFULLY", reply)
        self.assertIn("88332211", reply)
        self.assertIn("PERSONAL_MT5", reply)
        self.assertIn("$5,000.00", reply)

    def test_e2e_whatsapp_crypto_onboard_command(self):
        """End-to-end Crypto onboarding directive through WhatsApp QR Manager."""
        cmd = "onboard crypto exchange Binance balance 100 type Scalp5m"
        reply = self.qr.handle_incoming_command(cmd, self.authorized_sender)
        self.assertIn("ACCOUNT ONBOARDED SUCCESSFULLY", reply)
        self.assertIn("BINANCE_100", reply)
        self.assertIn("SCALP_5M", reply)
        self.assertIn("$100.00", reply)

    def test_e2e_fleet_risk_manager_synchronization(self):
        """Verifies FleetRiskManager loads newly onboarded accounts dynamically."""
        risk_mgr = FleetRiskManager()
        initial_accounts = len(risk_mgr.accounts_state)

        # Onboard new account via QR manager
        cmd = "onboard account 772211 server Demo balance 25000 type FundingPips"
        self.qr.handle_incoming_command(cmd, self.authorized_sender)

        # Reload risk manager fleet
        risk_mgr.load_fleet()
        updated_accounts = len(risk_mgr.accounts_state)
        self.assertGreaterEqual(updated_accounts, initial_accounts)

        # Validate pre-trade risk on the onboarded account
        approved, reason = risk_mgr.validate_pre_trade_risk("772211", "XAUUSD", 0.10, "BUY")
        self.assertTrue(approved, f"Pre-trade validation failed: {reason}")


if __name__ == "__main__":
    unittest.main()
