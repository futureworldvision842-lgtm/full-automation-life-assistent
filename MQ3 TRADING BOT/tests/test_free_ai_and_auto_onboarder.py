"""
test_free_ai_and_auto_onboarder.py — Test Suite for Free AI Intelligence Core & Multi-Account Onboarding.
=======================================================================================================
Covers:
  1. Free AI Conversational Core (Urdu/English market consultations, Market Maker trap evaluation).
  2. Multi-Account Auto-Onboarder (dynamic registration, risk calibration, Prop Firm/FTMO/MyFundedFX/Crypto profiles).
  3. All Platform Profiles (Funding Pips, FTMO, MyFundedFX, Personal MT5, Binance Spot/Futures, Hyperliquid DEX, Scalp 5M).
  4. Alias Normalization & Regex directive parsing for MT5 and Crypto exchanges.
  5. WhatsApp QR Manager directive parsing (onboard command, AI conversation, scalp query routing).
"""

import os
import json
import unittest
from src.free_ai_intelligence_core import FreeAIIntelligenceCore
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.whatsapp_qr_manager import WhatsAppQRManager


class TestFreeAIIntelligenceCore(unittest.TestCase):
    def setUp(self):
        self.ai = FreeAIIntelligenceCore()

    def test_gold_consultation_buy_inquiry_urdu(self):
        """Tests Urdu gold buy consultation inquiry."""
        query = "Main Gold buy karna chahta hoon kya karna chahiye?"
        res = self.ai.consult_market(query)
        self.assertEqual(res["detected_symbol"], "XAUUSD")
        self.assertEqual(res["detected_direction"], "BUY")
        self.assertIn("GOLD", res["advisory_response"])
        self.assertIn("Stop Loss", res["advisory_response"])

    def test_gold_consultation_sell_warning_urdu(self):
        """Tests Urdu gold short warning on trend days."""
        query = "Gold ko short / bech dun yahan se?"
        res = self.ai.consult_market(query)
        self.assertEqual(res["detected_symbol"], "XAUUSD")
        self.assertEqual(res["detected_direction"], "SELL")
        self.assertIn("WARNING", res["advisory_response"])
        self.assertEqual(res["market_maker_trap"]["trap_risk"], "CRITICAL")

    def test_crypto_btc_consultation(self):
        """Tests Bitcoin crypto consultation."""
        query = "Bitcoin ka kya scene hai buy karun ya wait karun?"
        res = self.ai.consult_market(query)
        self.assertEqual(res["detected_symbol"], "BTCUSD")
        self.assertIn("BITCOIN", res["advisory_response"])
        self.assertIn("Funding Rate", res["advisory_response"])

    def test_crypto_arbitrary_balance_100_dollar_binance_consultation(self):
        """Tests Requirement R2: $100 balance, 5m timeframe, best crypto on Binance."""
        query = "I have $100 in Binance, check and give me best position for 5-minute trade for now on any best crypto"
        res = self.ai.consult_market(query)
        self.assertIn(res["asset"], ["BTCUSD", "ETHUSD", "SOLUSD"])
        self.assertIn("SCENARIO A", res["advisory_response"])
        self.assertIn("SCENARIO B", res["advisory_response"])
        self.assertIn("MUHAMMAD'S SOVEREIGN INSTITUTIONAL MASHWARA", res["advisory_response"])
        self.assertLessEqual(res["execution_targets"]["max_dollar_loss"], 2.00)

    def test_scenario_ab_matrix_generation_urdu_query(self):
        """Tests Requirement R2: Roman Urdu query generates Scenario A & B matrix."""
        query = "Mere pas $100 hain Binance pe 5m scalp trade batao"
        res = self.ai.consult_market(query)
        self.assertIn("SCENARIO A", res["advisory_response"])
        self.assertIn("SCENARIO B", res["advisory_response"])
        self.assertIn("MASHWARA", res["advisory_response"])
        self.assertGreater(res["entry"], 0.0)
        self.assertGreater(res["sl"], 0.0)
        self.assertGreater(res["tp1"], 0.0)
        self.assertGreater(res["tp2"], 0.0)
        self.assertGreater(res["tp3"], 0.0)


class TestMultiAccountAutoOnboarder(unittest.TestCase):
    def setUp(self):
        self.test_config = "data/test_fleet_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    def test_onboard_funding_pips_account(self):
        """Tests dynamic onboarding of a Funding Pips 50k account."""
        res = self.onboarder.onboard_new_account(
            account_id="5099112233",
            server="FundingPips-Server",
            balance=50000.0,
            account_type="FUNDING_PIPS"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["starting_balance"], 50000.0)
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 1250.0)  # 2.5% of 50k
        self.assertEqual(acc_data["trailing_hwm_floor"], 47000.0)    # 6.0% drawdown
        self.assertEqual(acc_data["consistency_cap_pct"], 35.0)
        self.assertEqual(acc_data["execution_mode"], "LIVE_MT5")

    def test_onboard_ftmo_account(self):
        """Tests dynamic onboarding of an FTMO 100k account."""
        res = self.onboarder.onboard_new_account(
            account_id="FTMO100200",
            server="FTMO-Demo",
            balance=100000.0,
            account_type="FTMO"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["starting_balance"], 100000.0)
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 4000.0)  # 4.0% of 100k
        self.assertEqual(acc_data["trailing_hwm_floor"], 92000.0)    # 8.0% max loss
        self.assertEqual(acc_data["consistency_cap_pct"], 50.0)

    def test_onboard_myfundedfx_account(self):
        """Tests dynamic onboarding of a MyFundedFX 25k account."""
        res = self.onboarder.onboard_new_account(
            account_id="MFF_25K",
            server="MyFundedFX-Server",
            balance=25000.0,
            account_type="MYFUNDEDFX"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["starting_balance"], 25000.0)
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 1000.0)  # 4.0% of 25k
        self.assertEqual(acc_data["trailing_hwm_floor"], 23500.0)    # 6.0% drawdown
        self.assertEqual(acc_data["consistency_cap_pct"], 40.0)

    def test_onboard_personal_mt5_account(self):
        """Tests dynamic onboarding of a Personal MT5 broker account."""
        res = self.onboarder.onboard_new_account(
            account_id="ICM_5000",
            server="ICMarkets-Live",
            balance=5000.0,
            account_type="PERSONAL_MT5"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["starting_balance"], 5000.0)
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 250.0)   # 5.0% of 5k
        self.assertEqual(acc_data["trailing_hwm_floor"], 4250.0)    # 15.0% max loss
        self.assertEqual(acc_data["consistency_cap_pct"], 100.0)

    def test_onboard_binance_spot_account(self):
        """Tests dynamic onboarding of a Binance Spot crypto account."""
        res = self.onboarder.onboard_new_account(
            account_id="BINANCE_SPOT_1",
            server="Binance-Live",
            balance=1000.0,
            account_type="BINANCE_SPOT"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 50.0)    # 5.0% of 1000
        self.assertEqual(acc_data["trailing_hwm_floor"], 800.0)      # 20.0% max loss
        self.assertEqual(acc_data["execution_mode"], "CRYPTO_BINANCE_SPOT")
        self.assertIn("BNBUSDT", acc_data["allowed_assets"])

    def test_onboard_binance_futures_account(self):
        """Tests dynamic onboarding of a Binance Futures crypto account."""
        res = self.onboarder.onboard_new_account(
            account_id="BINANCE_FUT_1",
            server="Binance-Live",
            balance=2000.0,
            account_type="BINANCE_FUTURES"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["execution_mode"], "CRYPTO_BINANCE_FUTURES")
        self.assertIn("BTCUSDT", acc_data["allowed_assets"])

    def test_onboard_hyperliquid_account(self):
        """Tests dynamic onboarding of a Hyperliquid DEX account."""
        res = self.onboarder.onboard_new_account(
            account_id="HL_DEX_1",
            server="Hyperliquid-Mainnet",
            balance=500.0,
            account_type="HYPERLIQUID"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["execution_mode"], "CRYPTO_HYPERLIQUID")
        self.assertIn("BTC-PERP", acc_data["allowed_assets"])

    def test_onboard_scalp5m_account(self):
        """Tests dynamic onboarding of a Scalp 5M micro crypto account."""
        res = self.onboarder.onboard_new_account(
            account_id="SCALP_100",
            server="Binance-Live",
            balance=100.0,
            account_type="SCALP_5M"
        )
        self.assertTrue(res["success"])
        acc_data = res["account_data"]
        self.assertEqual(acc_data["daily_loss_dollar_cap"], 5.0)     # 5.0% of 100
        self.assertEqual(acc_data["trailing_hwm_floor"], 80.0)       # 20.0% max loss
        self.assertEqual(acc_data["execution_mode"], "CRYPTO_BINANCE")

    def test_account_type_alias_normalization(self):
        """Tests that aliases normalize accurately to canonical profiles."""
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("fundingpips"), "FUNDING_PIPS")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("fp"), "FUNDING_PIPS")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("ftmo"), "FTMO")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("mff"), "MYFUNDEDFX")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("myfundedfx"), "MYFUNDEDFX")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("personalmt5"), "PERSONAL_MT5")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("icmarkets"), "PERSONAL_MT5")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("scalp5m"), "SCALP_5M")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("dex"), "HYPERLIQUID")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("hyperliquid"), "HYPERLIQUID")
        self.assertEqual(MultiAccountAutoOnboarder.normalize_account_type("binance_futures"), "BINANCE_FUTURES")

    def test_parse_whatsapp_onboard_directive_prop_firm(self):
        """Tests WhatsApp text directive parsing for MT5 / Prop Firm."""
        msg = "onboard account 77889900 server MetaQuotes-Demo balance 25000 type FundingPips"
        res = self.onboarder.parse_whatsapp_onboard_directive(msg)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["account_data"]["starting_balance"], 25000.0)
        self.assertEqual(res["account_data"]["account_type"], "FUNDING_PIPS")

    def test_parse_whatsapp_onboard_directive_crypto_scalp(self):
        """Tests WhatsApp crypto directive: onboard crypto exchange Binance balance 100 type Scalp5m."""
        msg = "onboard crypto exchange Binance balance 100 type Scalp5m"
        res = self.onboarder.parse_whatsapp_onboard_directive(msg)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["account_data"]["starting_balance"], 100.0)
        self.assertEqual(res["account_data"]["account_type"], "SCALP_5M")
        self.assertEqual(res["account_data"]["daily_loss_dollar_cap"], 5.0)

    def test_parse_whatsapp_onboard_directive_crypto_hyperliquid(self):
        """Tests WhatsApp crypto directive: onboard crypto exchange Hyperliquid balance 500 type DEX."""
        msg = "onboard crypto exchange Hyperliquid balance 500 type DEX"
        res = self.onboarder.parse_whatsapp_onboard_directive(msg)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["account_data"]["starting_balance"], 500.0)
        self.assertEqual(res["account_data"]["account_type"], "HYPERLIQUID")
        self.assertEqual(res["account_data"]["execution_mode"], "CRYPTO_HYPERLIQUID")


class TestWhatsAppQRManagerIntegration(unittest.TestCase):
    def setUp(self):
        self.qr = WhatsAppQRManager()
        self.sender = "923468053268@s.whatsapp.net"

    def test_whatsapp_onboard_command(self):
        """Tests onboard command via WhatsApp QR manager."""
        cmd = "onboard account 99112233 server Demo balance 10000 type PersonalMT5"
        reply = self.qr.handle_incoming_command(cmd, self.sender)
        self.assertIn("ACCOUNT ONBOARDED SUCCESSFULLY", reply)

    def test_whatsapp_crypto_onboard_command(self):
        """Tests crypto onboard command via WhatsApp QR manager."""
        cmd = "onboard crypto exchange Binance balance 100 type Scalp5m"
        reply = self.qr.handle_incoming_command(cmd, self.sender)
        self.assertIn("ACCOUNT ONBOARDED SUCCESSFULLY", reply)

    def test_whatsapp_ai_conversation_advisory(self):
        """Tests natural Urdu question handling."""
        reply = self.qr.handle_incoming_command("Main Gold buy karna chahta hoon", self.sender)
        self.assertIn("GOLD", reply)

    def test_whatsapp_scalp_query_routing(self):
        """Tests Requirement R2: WhatsApp routing of $100 scalp query."""
        cmd = "Mere pas $100 hain Binance pe 5m scalp trade batao"
        reply = self.qr.handle_incoming_command(cmd, self.sender)
        self.assertIn("JARVIS AI INSTITUTIONAL TRADE ADVISOR", reply)
        self.assertIn("ACCOUNT BALANCE:", reply)
        self.assertIn("SCENARIO A", reply)

    def test_elite_group_institutional_broadcast(self):
        """Tests institutional broadcast generation and dispatch payload."""
        res = self.qr.broadcast_elite_group_intel()
        self.assertTrue(res["success"])
        self.assertIn("ELITE_TRADE_GROUP", res["target"])
        self.assertIn("GOLD", res["message"])
        self.assertIn("BITCOIN", res["message"])
        self.assertIn("BIG SHARKS MOVE ANALYSIS", res["message"])
        self.assertIn("STRATEGY EXPLAINER", res["message"])

    def test_client_account_update_notification(self):
        """Tests automated client trade report dispatch."""
        res = self.qr.notify_client_account_update(
            phone="+923468053268",
            account_name="Funding Pips 25k",
            message="Trade #10928 locked to risk-free Breakeven!"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["recipient"], "923468053268")


class TestSignalSubscriptionManager(unittest.TestCase):
    def setUp(self):
        self.test_store = "data/test_signal_subscribers.json"
        from src.signal_subscription_manager import SignalSubscriptionManager
        self.sub_mgr = SignalSubscriptionManager(store_path=self.test_store)

    def tearDown(self):
        if os.path.exists(self.test_store):
            try:
                os.remove(self.test_store)
            except Exception:
                pass

    def test_subscribe_new_vip_client(self):
        """Tests VIP signal registration for new client."""
        res = self.sub_mgr.subscribe(phone="+923001234567", name="Hamza Trader", asset_preference="GOLD_COMMODITIES")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_new"])
        self.assertEqual(res["subscriber"]["normalized_phone"], "923001234567")
        self.assertEqual(res["subscriber"]["name"], "Hamza Trader")

    def test_subscribe_update_existing(self):
        """Tests updating existing subscriber preferences."""
        self.sub_mgr.subscribe(phone="+923001234567", name="Hamza Trader", asset_preference="GOLD_COMMODITIES")
        res2 = self.sub_mgr.subscribe(phone="03001234567", name="Hamza Updated", asset_preference="CRYPTO_FUTURES")
        self.assertTrue(res2["success"])
        self.assertFalse(res2["is_new"])
        self.assertEqual(res2["subscriber"]["name"], "Hamza Updated")


class TestAutonomousFleetExecutor(unittest.TestCase):
    def setUp(self):
        from src.autonomous_fleet_executor import AutonomousFleetExecutor
        self.executor = AutonomousFleetExecutor()

    def test_fleet_positions_retrieval(self):
        """Tests active positions retrieval across curated fleet."""
        positions = self.executor.get_all_positions()
        self.assertGreaterEqual(len(positions), 3)
        symbols = [p["symbol"] for p in positions]
        self.assertIn("XAUUSD", symbols)
        self.assertIn("BTCUSD", symbols)

    def test_execute_fleet_signal(self):
        """Tests dynamic trade execution across active fleet accounts."""
        res = self.executor.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2648.0,
            sl=2640.0,
            tp1=2664.0,
            tp2=2680.0,
            tp3=2700.0,
            confluence_tag="70.5% OTE FVG MITIGATION",
            shark_tag="Citadel Securities"
        )
        self.assertTrue(res["success"])
        self.assertGreater(res["executed_count"], 0)

    def test_manage_position_breakeven_and_scale(self):
        """Tests 1-click breakeven and 50% scale-out."""
        pos = self.executor.get_all_positions()[0]
        ticket = pos["ticket"]
        
        # Test Breakeven
        res_be = self.executor.manage_position_action(ticket=ticket, action="breakeven")
        self.assertTrue(res_be["success"])
        self.assertEqual(res_be["position"]["status"], "BE_LOCKED")

        # Test Scale 50%
        res_scale = self.executor.manage_position_action(ticket=ticket, action="scale_50")
        self.assertTrue(res_scale["success"])
        self.assertEqual(res_scale["position"]["status"], "SCALED_50_BE")


if __name__ == "__main__":
    unittest.main()


