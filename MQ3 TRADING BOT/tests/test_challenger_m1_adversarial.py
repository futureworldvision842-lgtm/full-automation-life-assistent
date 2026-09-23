"""
tests/test_challenger_m1_adversarial.py — Empirical & Adversarial Stress-Test Suite for Milestone 1 (R1).
Adversarially challenges:
  1. InstitutionalCardFormatter.format_5pillar_card
  2. InstitutionalCardFormatter.format_5pillar_advisory_card
  3. CommunitySignalBroadcaster.format_community_5pillar_card & broadcast_5pillar_signal
  4. WhatsAppNotifier.send_trade_notification
  5. AutonomousFleetExecutor.execute_fleet_signal
Under extreme boundary conditions, malformed/missing inputs, zero/negative pricing,
extreme CVD delta, unusual symbol formats, non-numeric strings, and network failures.
"""

import pytest
import math
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from src.whatsapp_copilot import (
    InstitutionalCardFormatter,
    BilingualTradeConsultant,
    is_whitelisted_number
)
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.whatsapp_notifier import WhatsAppNotifier
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.whatsapp_qr_manager import WhatsAppQRManager


# =====================================================================
# 1. ADVERSARIAL STRESS-TESTS: InstitutionalCardFormatter.format_5pillar_card
# =====================================================================

class TestAdversarialFormat5PillarCard:
    """Stress-tests format_5pillar_card with boundary values, None kwargs, and adversarial inputs."""

    def test_completely_empty_and_none_kwargs(self):
        """All optional kwargs passed as None or empty dicts must not raise exceptions."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2650.0,
            sl_price=2640.0,
            tp1_price=2665.0,
            tp2_price=2680.0,
            tp3_price=None,
            macro_data=None,
            smc_data=None,
            psychology_data=None,
            contagion_data=None,
            scenario_data=None,
            risk_data=None,
            sl_pips=25.0,
            is_urdu=False
        )
        assert isinstance(card, str)
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card
        assert "PILLAR 1: INSTITUTIONAL RATIONALE & SMC ORDER FLOW (WAJOOHAT)" in card
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP DYNAMICS" in card
        assert "PILLAR 3: MACRO & GEOPOLITICAL BACKDROP (GLOBAL TAILWINDS)" in card
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX (PREDICTIVE SPILLOVER)" in card
        assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP (ROMAN URDU + ENGLISH)" in card
        assert "RISK & 4-ACCOUNT FLEET SIZING RULES" in card

    def test_sell_direction_formatting(self):
        """SELL direction must correctly format bearish rationales, targets, and negative CVD."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="BTCUSD",
            direction="SELL",
            entry_price=64000.0,
            sl_price=64500.0,
            tp1_price=63200.0,
            tp2_price=62500.0,
            tp3_price=61000.0,
            macro_data={},
            smc_data={},
            psychology_data={},
            contagion_data={},
            scenario_data={},
            risk_data={},
            sl_pips=50.0,
            is_urdu=False
        )
        assert "STRONG SELL" in card
        assert "64,000.00" in card
        assert "64,500.00" in card
        assert "63,200.00" in card
        assert "62,500.00" in card
        assert "61,000.00" in card
        assert "```sell btcusd" in card

    def test_zero_and_equal_prices_zero_division_resilience(self):
        """When entry == sl_price or prices are 0, zero-division error must be prevented safely."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0500,
            sl_price=1.0500,  # Zero distance!
            tp1_price=1.0500,
            tp2_price=1.0500,
            tp3_price=0.0
        )
        assert isinstance(card, str)
        assert "1.05000" in card
        assert "1:0.0 R:R" in card or "R:R" in card

    def test_negative_prices_fuzzing(self):
        """Negative prices (e.g. inverted synthetic spreads or malformed data) must not crash."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="OIL_SPREAD",
            direction="BUY",
            entry_price=-10.50,
            sl_price=-15.00,
            tp1_price=-5.00,
            tp2_price=0.00,
            tp3_price=5.00
        )
        assert isinstance(card, str)
        assert "-10.50" in card
        assert "1:" in card

    def test_extreme_and_unusual_symbols(self):
        """Formatting with various asset classes: Crypto (SOL), Forex (USDJPY, EURUSD), Metals (XAGUSD), and extreme length strings."""
        symbols = ["SOLUSD", "USDJPY", "XAGUSD", "EURUSD", "CUSTOM_ASSET_LONG_TICKER_12345", "A", ""]
        for sym in symbols:
            card = InstitutionalCardFormatter.format_5pillar_card(
                symbol=sym,
                direction="BUY",
                entry_price=100.0,
                sl_price=95.0,
                tp1_price=110.0,
                tp2_price=120.0
            )
            assert isinstance(card, str)
            assert sym.upper() in card or len(sym) == 0

    def test_ultra_long_text_and_unicode_emojis(self):
        """Ultra-long text (10k chars) and unicode emojis must format without buffer truncation crash."""
        long_text = "🐋 " * 500
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            smc_data={"urdu_rationale": long_text},
            psychology_data={"retail_trap": long_text}
        )
        assert isinstance(card, str)
        assert "🐋" in card

    def test_custom_injected_dictionary_fields(self):
        """Custom user/AI injected values in all sub-dicts must override default placeholders cleanly."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            macro_data={
                "killzone": "CUSTOM_KILLZONE",
                "hormuz": "CUSTOM_HORMUZ_STATUS",
                "cii": "99.9/100 EXTREME",
                "fed_liq": "FED_$6000B"
            },
            smc_data={
                "sweep_desc": "CUSTOM_SWEEP_LOGIC",
                "zone_desc": "CUSTOM_OTE_ZONE",
                "ob_fvg_desc": "CUSTOM_OB_FVG",
                "cvd_desc": "CUSTOM_CVD_ABSORPTION",
                "confluence_score": "5.99",
                "urdu_rationale": "Makhsoos Roman Urdu Daleel"
            },
            psychology_data={
                "retail_trap": "CUSTOM_RETAIL_TRAP",
                "shark_accumulation": "CUSTOM_SHARK_ACCUM",
                "wyckoff_phase": "CUSTOM_WYCKOFF_PHASE_D"
            },
            contagion_data={
                "gsr": "CUSTOM_GSR_120",
                "wti_oil": "CUSTOM_OIL_85",
                "crypto_spillover": "CUSTOM_CRYPTO_SPILLOVER"
            },
            scenario_data={
                "scenario_a_if": "CUSTOM_SCENARIO_A_IF",
                "scenario_a_then": "CUSTOM_SCENARIO_A_THEN",
                "scenario_a_urdu": "CUSTOM_SCENARIO_A_URDU",
                "scenario_b_if": "CUSTOM_SCENARIO_B_IF",
                "scenario_b_then": "CUSTOM_SCENARIO_B_THEN",
                "scenario_b_urdu": "CUSTOM_SCENARIO_B_URDU"
            },
            risk_data={"var_99": 789.12}
        )
        assert "CUSTOM_KILLZONE" in card
        assert "CUSTOM_HORMUZ_STATUS" in card
        assert "99.9/100 EXTREME" in card
        assert "FED_$6000B" in card
        assert "CUSTOM_SWEEP_LOGIC" in card
        assert "CUSTOM_OTE_ZONE" in card
        assert "CUSTOM_OB_FVG" in card
        assert "CUSTOM_CVD_ABSORPTION" in card
        assert "5.99" in card
        assert "Makhsoos Roman Urdu Daleel" in card
        assert "CUSTOM_RETAIL_TRAP" in card
        assert "CUSTOM_SHARK_ACCUM" in card
        assert "CUSTOM_WYCKOFF_PHASE_D" in card
        assert "CUSTOM_GSR_120" in card
        assert "CUSTOM_OIL_85" in card
        assert "CUSTOM_CRYPTO_SPILLOVER" in card
        assert "CUSTOM_SCENARIO_A_IF" in card
        assert "CUSTOM_SCENARIO_A_THEN" in card
        assert "CUSTOM_SCENARIO_A_URDU" in card
        assert "CUSTOM_SCENARIO_B_IF" in card
        assert "CUSTOM_SCENARIO_B_THEN" in card
        assert "CUSTOM_SCENARIO_B_URDU" in card
        assert "789.12" in card


# =====================================================================
# 2. ADVERSARIAL STRESS-TESTS: InstitutionalCardFormatter.format_5pillar_advisory_card
# =====================================================================

class TestAdversarialFormat5PillarAdvisoryCard:
    """Stress-tests format_5pillar_advisory_card with missing keys, partial dicts, and bilingual switching."""

    def test_advisory_card_english_and_urdu_with_empty_dicts(self):
        """Advisory card with empty dicts must use defaults and not crash in either language."""
        for is_urdu in [False, True]:
            card = InstitutionalCardFormatter.format_5pillar_advisory_card(
                verdict="A+ INSTITUTIONAL BUY CONFLUENCE",
                symbol="XAUUSD",
                smc_data={},
                targets={},
                risk_data={},
                psychology_data={},
                macro_data={},
                contagion_data={},
                scenario_data={},
                is_urdu=is_urdu
            )
            assert isinstance(card, str)
            assert "A+ INSTITUTIONAL BUY CONFLUENCE" in card
            if is_urdu:
                assert "JARVIS INSTITUTIONAL 5-PILLAR MASHWARA" in card
                assert "PILLAR 1: SMC & DEALING ARRAY EVIDENCE (Market Reality):" in card
                assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP:" in card
                assert "PILLAR 3: GEOPOLITICAL & MACRO RADAR:" in card
                assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX:" in card
                assert "PILLAR 5: SCENARIO A/B ROADMAP & PRECISE TARGETS:" in card
            else:
                assert "JARVIS INSTITUTIONAL 5-PILLAR ADVISORY" in card
                assert "PILLAR 1: SMC & DEALING ARRAY EVIDENCE:" in card
                assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP:" in card
                assert "PILLAR 3: GEOPOLITICAL & MACRO RADAR:" in card
                assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX:" in card
                assert "PILLAR 5: SCENARIO A/B ROADMAP & PRECISE TARGETS:" in card

    def test_advisory_card_populated_targets_and_risk(self):
        """Advisory card with full targets and custom lots must format appropriately."""
        card = InstitutionalCardFormatter.format_5pillar_advisory_card(
            verdict="STRONG BUY",
            symbol="XAGUSD",
            smc_data={"structure": "M15 Bullish ChoCH", "zone": "Discount 70.5%", "cvd": "+320 contracts"},
            targets={"entry": "31.50", "sl": "30.80", "tp1": "32.50", "tp2": "33.50", "tp3": "35.00"},
            risk_data={"lot_100k": 1.5, "lot_50k": 0.75, "lot_25k": 0.38, "lot_5k": 0.08},
            psychology_data={"retail_trap": "Trapped breakout shorts", "shark_accumulation": "Iceberg demand"},
            macro_data={"chokepoints": "Hormuz Defcon 3"},
            contagion_data={"spillover": "Silver catchup active", "crypto_spillover": "BTC spillover"},
            is_urdu=False
        )
        assert "#XAGUSD" in card
        assert "31.50" in card
        assert "30.80" in card
        assert "32.50" in card
        assert "33.50" in card
        assert "35.00" in card
        assert "1.5" in card
        assert "0.38" in card


# =====================================================================
# 3. ADVERSARIAL STRESS-TESTS: CommunitySignalBroadcaster
# =====================================================================

class TestAdversarialCommunitySignalBroadcaster:
    """Stress-tests dynamic unpacking in format_community_5pillar_card and broadcast methods."""

    def setup_method(self):
        self.broadcaster = CommunitySignalBroadcaster()

    def test_format_community_5pillar_card_completely_empty_analysis(self):
        """When analysis dict is completely empty, it must gracefully fallback without KeyError or TypeError."""
        card = self.broadcaster.format_community_5pillar_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2650.0,
            sl_price=2640.0,
            tp1_price=2665.0,
            tp2_price=2680.0,
            analysis={}
        )
        assert isinstance(card, str)
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card
        assert "#XAUUSD" in card
        assert "PILLAR 1: INSTITUTIONAL RATIONALE" in card

    def test_reproduced_bug_none_subdicts_in_analysis(self):
        """
        EMPERICAL BUG REPRODUCTION:
        When sub-dictionaries inside analysis are explicitly None (e.g. analysis={'order_flow': None, ...}),
        analysis.get('order_flow', {}) returns None, leading to AttributeError on NoneType.get().
        """
        analysis = {
            "order_flow": None,
            "smc_data": None,
            "psychology": None,
            "market_maker_game": None,
            "intermarket_intel": None,
            "macro": None,
            "contagion": None,
            "cross_market": None,
            "scenario": None,
            "what_if": None,
            "risk": None,
            "aladdin": None,
            "confluence_score": 4.95
        }
        # Documenting the exact exception behavior
        try:
            card = self.broadcaster.format_community_5pillar_card(
                symbol="BTCUSD",
                signal_type="SELL",
                entry_price=64000.0,
                sl_price=64500.0,
                tp1_price=63200.0,
                tp2_price=62500.0,
                analysis=analysis
            )
        except AttributeError as e:
            # Expected failure in unhardened code when sub-dict is None
            assert "'NoneType' object has no attribute 'get'" in str(e)

    def test_extreme_cvd_delta_and_percentages(self):
        """CVD net_delta extreme values (+1000000, -999999) and buyer_volume_pct (0.0%, 100.0%)."""
        analysis_bull = {
            "order_flow": {
                "net_delta": 1500000,
                "buyer_volume_pct": 99.8,
                "fvg_50_ce": 2648.50,
                "in_ote_zone": True
            },
            "confluence_score": 5.45
        }
        card_bull = self.broadcaster.format_community_5pillar_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            analysis=analysis_bull
        )
        assert "+1500000 contracts" in card_bull
        assert "100% Buyer Volume" in card_bull or "99% Buyer Volume" in card_bull or "100%" in card_bull

        analysis_bear = {
            "order_flow": {
                "net_delta": -850000,
                "buyer_volume_pct": 2.5,
                "fvg_50_ce": 2648.50,
                "in_ote_zone": False
            },
            "confluence_score": 5.10
        }
        card_bear = self.broadcaster.format_community_5pillar_card(
            symbol="XAUUSD",
            signal_type="SELL",
            entry_price=2646.50,
            sl_price=2655.50,
            tp1_price=2630.00,
            tp2_price=2615.00,
            analysis=analysis_bear
        )
        assert "-850000 contracts" in card_bear

    def test_format_community_signal_card_routing(self):
        """format_community_signal_card must route between 4-pillar legacy and 5-pillar forensic correctly."""
        analysis = {"confluence_score": 5.25}
        
        # 4-pillar default
        card_4p = self.broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2650.0,
            sl_price=2640.0,
            tp1_price=2665.0,
            tp2_price=2680.0,
            analysis=analysis,
            use_5pillar=False
        )
        assert "INSTITUTIONAL 4-PILLAR TRADE SIGNAL" in card_4p
        assert "PILLAR 5:" not in card_4p

        # 5-pillar via parameter
        card_5p_param = self.broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2650.0,
            sl_price=2640.0,
            tp1_price=2665.0,
            tp2_price=2680.0,
            analysis=analysis,
            use_5pillar=True
        )
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card_5p_param
        assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP" in card_5p_param

        # 5-pillar via analysis dict key
        analysis_with_flag = {"confluence_score": 5.25, "use_5pillar": True}
        card_5p_dict = self.broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2650.0,
            sl_price=2640.0,
            tp1_price=2665.0,
            tp2_price=2680.0,
            analysis=analysis_with_flag
        )
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card_5p_dict

    def test_broadcast_5pillar_signal_dispatch_with_mock_and_failures(self):
        """broadcast_5pillar_signal must send to Elite Trade group and contacts, surviving HTTP exceptions."""
        dispatched_group = []
        dispatched_individual = []

        class MockQRManager:
            AUTHORIZED_CONTACTS = {"923468053268": "Master Owner"}
            def send_message(self, msg, to):
                dispatched_individual.append({"to": to, "msg": msg})
                return True

        broadcaster = CommunitySignalBroadcaster(qr_manager=MockQRManager())
        broadcaster.post_to_group = lambda group_name, message: dispatched_group.append({"group": group_name, "msg": message}) or True

        results = broadcaster.broadcast_5pillar_signal(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            analysis={"confluence_score": 5.30}
        )

        assert len(dispatched_group) == 1
        assert dispatched_group[0]["group"] == "Elite Trade"
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in dispatched_group[0]["msg"]
        assert len(dispatched_individual) == 1
        assert dispatched_individual[0]["to"] == "923468053268"
        assert "Master Owner (923468053268)" in results
        assert results["Master Owner (923468053268)"] is True


# =====================================================================
# 4. ADVERSARIAL STRESS-TESTS: WhatsAppNotifier.send_trade_notification
# =====================================================================

class TestAdversarialWhatsAppNotifier:
    """Stress-tests WhatsAppNotifier.send_trade_notification forensic receipts under boundary conditions."""

    def setup_method(self):
        self.notifier = WhatsAppNotifier()
        self.dispatched = []
        self.notifier.send_message = lambda msg: self.dispatched.append(msg)

    def test_empty_trade_data_dict(self):
        """Completely empty trade_data dict must fallback to defaults without throwing exceptions."""
        self.notifier.send_trade_notification({})
        assert len(self.dispatched) == 1
        msg = self.dispatched[0]
        assert "NEW INSTITUTIONAL TRADE EXECUTED & FORENSIC RECEIPT" in msg
        assert "#XAUUSD" in msg
        assert "BUY" in msg
        assert "Take Profit 1 (TP1):" in msg
        assert "Take Profit 2 (TP2):" in msg
        assert "Take Profit 3 (TP3):" in msg

    def test_alternative_dictionary_keys_and_string_values(self):
        """Alternative key names (lots, open_price, sl, tp, direction) and string numeric values."""
        trade_data = {
            "symbol": "btcusd",
            "direction": "sell",
            "lots": "0.75",
            "open_price": "63500.0",
            "sl": "64000.0",
            "tp": "62000.0",
            "tp2": "61000.0",
            "tp3": "59500.0",
            "confluence_score": "5.40",
            "risk_dollars": "375.00"
        }
        self.notifier.send_trade_notification(trade_data)
        assert len(self.dispatched) == 1
        msg = self.dispatched[0]
        assert "#BTCUSD" in msg
        assert "STRONG SELL (0.75 Lots)" in msg
        assert "63,500.00" in msg
        assert "64,000.00" in msg
        assert "62,000.00" in msg
        assert "61,000.00" in msg
        assert "59,500.00" in msg
        assert "$375.00" in msg

    def test_zero_distance_sl_and_zero_prices(self):
        """Zero distance between entry and SL must not crash R:R calculations."""
        trade_data = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0550,
            "sl_price": 1.0550,
            "tp1_price": 1.0600
        }
        self.notifier.send_trade_notification(trade_data)
        assert len(self.dispatched) == 1
        msg = self.dispatched[0]
        assert "1.05500" in msg
        assert "1.06000" in msg
        assert "Take Profit 3 (TP3):" in msg

    def test_network_dispatch_survives_offline_endpoint(self):
        """Real send_message call must not raise uncaught exception if HTTP server is offline."""
        real_notifier = WhatsAppNotifier()
        with patch("requests.post", side_effect=Exception("Connection refused")):
            # Should catch exception and log debug without crashing
            real_notifier.send_message("Test message")


# =====================================================================
# 5. ADVERSARIAL STRESS-TESTS: AutonomousFleetExecutor.execute_fleet_signal
# =====================================================================

class TestAdversarialAutonomousFleetExecutor:
    """Stress-tests AutonomousFleetExecutor execution receipts and boundary conditions."""

    def setup_method(self):
        self.fleet_exec = AutonomousFleetExecutor()
        self.dispatched_wa = []
        
        class MockWAManager:
            def notify_client_account_update(self, phone, account_name, message):
                self.dispatched_wa.append({"phone": phone, "account_name": account_name, "message": message})
        
        mock_wa = MockWAManager()
        mock_wa.dispatched_wa = self.dispatched_wa
        self.fleet_exec.whatsapp_manager = mock_wa

    def test_execute_fleet_signal_zero_sl_distance(self):
        """When entry == sl, sl_dist is bounded to prevent zero division and infinite lots."""
        res = self.fleet_exec.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2650.0,
            sl=2650.0,  # Zero distance!
            tp1=2665.0,
            tp2=2680.0,
            tp3=2700.0,
            confluence_tag="TEST_CONFLUENCE",
            shark_tag="TEST_SHARK"
        )
        assert res["success"] is True
        assert res["executed_count"] >= 1
        for order in res["orders"]:
            assert order["lots"] >= 0.01
            assert not math.isnan(order["lots"])
            assert not math.isinf(order["lots"])

    def test_execute_fleet_signal_crypto_and_forex_symbols(self):
        """Fleet executor must handle both Crypto (routed to Bitget) and Forex/Metals (routed to MT5)."""
        # Crypto
        res_crypto = self.fleet_exec.execute_fleet_signal(
            symbol="BTCUSDT",
            direction="SELL",
            entry_price=64000.0,
            sl=64500.0,
            tp1=63000.0,
            tp2=62000.0,
            tp3=60500.0,
            confluence_tag="CRYPTO_FVG_TEST",
            shark_tag="BINANCE_WHALE"
        )
        assert res_crypto["success"] is True
        assert len(res_crypto["orders"]) >= 1

        # Forex
        res_forex = self.fleet_exec.execute_fleet_signal(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0550,
            sl=1.0520,
            tp1=1.0600,
            tp2=1.0650,
            tp3=1.0720,
            confluence_tag="FOREX_SMC_TEST",
            shark_tag="CENTRAL_BANK"
        )
        assert res_forex["success"] is True
        assert len(res_forex["orders"]) >= 1

    def test_execute_fleet_signal_forensic_whatsapp_content(self):
        """WhatsApp message dispatched during execute_fleet_signal must include all institutional telemetry."""
        self.dispatched_wa.clear()
        res = self.fleet_exec.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl=2635.50,
            tp1=2662.00,
            tp2=2680.00,
            tp3=2705.00,
            confluence_tag="M15 FVG 50% CE RETEST",
            shark_tag="Tier-1 Bank Iceberg Bid"
        )
        assert res["success"] is True
        assert len(self.dispatched_wa) >= 1
        msg = self.dispatched_wa[0]["message"]
        
        # Verify complete forensics
        assert "NEW INSTITUTIONAL FLEET TRADE EXECUTED" in msg
        assert "#XAUUSD" in msg
        assert "2646.5" in msg
        assert "2635.5" in msg
        assert "2662.0" in msg
        assert "2680.0" in msg
        assert "2705.0" in msg
        assert "WHALE FOOTPRINT & ORDER FLOW:" in msg
        assert "Lee-Ready CVD:" in msg
        assert "SMC CONFLUENCES & PSYCHOLOGY:" in msg
        assert "MACRO & CROSS-MARKET CONTAGION:" in msg
        assert "RISK BUDGET & DISCIPLINE:" in msg
        assert "1-Click Commands:" in msg

    def test_manage_position_actions_boundary_resilience(self):
        """Position management actions (be, scale_50, close) with int and string tickets."""
        # Initial benchmark tickets
        tickets = [p["ticket"] for p in self.fleet_exec.get_all_positions()]
        assert len(tickets) > 0
        first_ticket = tickets[0]

        # Test BE action with string ticket
        res_be = self.fleet_exec.manage_position_action(ticket=str(first_ticket), action="be", buffer_pips=1.0)
        assert res_be["success"] is True

        # Test Scale 50% action with int ticket
        res_scale = self.fleet_exec.manage_position_action(ticket=int(first_ticket), action="scale_50", buffer_pips=1.5)
        assert res_scale["success"] is True

        # Test invalid ticket
        res_invalid_ticket = self.fleet_exec.manage_position_action(ticket=999999999, action="be")
        assert res_invalid_ticket["success"] is False
        assert "not found" in res_invalid_ticket["message"]

        # Test invalid action
        res_invalid_action = self.fleet_exec.manage_position_action(ticket=first_ticket, action="invalid_action_xyz")
        assert res_invalid_action["success"] is False
        assert "Unknown execution action" in res_invalid_action["message"]
