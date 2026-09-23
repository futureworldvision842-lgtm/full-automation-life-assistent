"""
tests/test_whatsapp_copilot_m4.py — Comprehensive Test Suite for Milestone M4 (Requirement R4).
Tests:
  - Feature 22: Sovereign WhatsApp Whitelist Security & Lifecycle Hardening
  - Feature 23: Institutional 4-Pillar WhatsApp Cards
  - Feature 24: WhatsApp 1-Click Command Handlers & Sub-300ms Execution Pipeline
  - Feature 25: Voice Audio Note Processing (Buffer ingestion, STT tiers, Intent Router)
  - Feature 26: Bilingual WhatsApp Consultation (Institutional Roman Urdu + English Code-Switching)
"""

import os
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.whatsapp_copilot import (
    is_whitelisted_number,
    AUTHORIZED_CONTACTS,
    ALLOWED_SET,
    ELITE_TRADE_GROUP_JID,
    ALLOWED_LIDS,
    SYMBOL_ALIASES,
    InstitutionalCardFormatter,
    BilingualTradeConsultant,
    WhatsApp1ClickRouter
)
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.whatsapp_voice_transcriber import WhatsAppVoiceTranscriber
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.web_terminal_server import app as fastapi_app


# =====================================================================
# 1. FEATURE 22: SOVEREIGN WHATSAPP WHITELIST SECURITY TESTS
# =====================================================================

class TestWhatsAppWhitelistSecurity:
    """Validates strict single-owner whitelist security and eliminates vulnerabilities."""

    def test_master_owner_jid_variations_accepted(self):
        """Owner phone JIDs in standard, prefixed, or companion device formats must be accepted."""
        valid_jids = [
            "923468053268@s.whatsapp.net",
            "923468053268:0@s.whatsapp.net",
            "923468053268:1@s.whatsapp.net",
            "+923468053268",
            "00923468053268",
            "03468053268",
            "923468053268"
        ]
        for jid in valid_jids:
            assert is_whitelisted_number(jid) is True, f"Expected {jid} to be whitelisted"

    def test_elite_trade_group_jid_accepted(self):
        """Elite Trade Group JID must be accepted."""
        assert is_whitelisted_number(ELITE_TRADE_GROUP_JID) is True
        assert is_whitelisted_number("120363401615322542@g.us") is True

    def test_verified_owner_lid_accepted(self):
        """Verified connected owner LID must be accepted."""
        owner_lid = "249871234567890@lid"
        assert is_whitelisted_number(owner_lid, verified_lid=owner_lid) is True
        assert is_whitelisted_number("249871234567890:0@lid", verified_lid=owner_lid) is True

    def test_unverified_lid_wildcard_vulnerability_eliminated(self):
        """Arbitrary @lid JIDs without verified owner match must be rejected (closes V1 loophole)."""
        unverified_lids = [
            "987654321098765@lid",
            "112233445566778:0@lid",
            "attacker@lid",
            "spoofed_id@lid"
        ]
        for lid in unverified_lids:
            assert is_whitelisted_number(lid, verified_lid=None) is False, f"Vulnerability! Unverified {lid} was accepted"

    def test_unauthorized_senders_and_groups_rejected(self):
        """Unauthorized external numbers and unauthorized groups must be rejected."""
        unauthorized = [
            "1234567890@s.whatsapp.net",
            "+14155552671@s.whatsapp.net",
            "923001234567@s.whatsapp.net",
            "120363999999999999@g.us",  # Unapproved group
            "random_group@g.us",
            "status@broadcast",
            "broadcast@s.whatsapp.net",
            "",
            None,
            12345,
            "923468053268\x00@s.whatsapp.net"  # Injection attempt
        ]
        for sender in unauthorized:
            assert is_whitelisted_number(sender) is False, f"Expected {sender} to be rejected"

    def test_silent_drop_protocol_on_unauthorized_command(self):
        """Unauthorized incoming message must be dropped immediately and silently without reply."""
        qr_mgr = WhatsAppQRManager()
        reply = qr_mgr.handle_incoming_command("buy gold 1.0", sender="1234567890@s.whatsapp.net")
        assert reply == "", "Expected empty string (silent drop) for unauthorized sender"

    def test_group_execution_participant_verification(self):
        """In Elite Trade Group, trade execution commands require whitelisted participant identity."""
        router = WhatsApp1ClickRouter()
        # Group message with non-whitelisted participant
        unauth_res = router.handle_command(
            command_text="buy gold 0.10",
            sender=ELITE_TRADE_GROUP_JID,
            participant="1234567890@s.whatsapp.net",
            is_group=True
        )
        assert unauth_res["success"] is False
        assert unauth_res["reply"] == ""

        # Group message with whitelisted participant
        auth_res = router.handle_command(
            command_text="buy gold 0.10",
            sender=ELITE_TRADE_GROUP_JID,
            participant="923468053268@s.whatsapp.net",
            is_group=True
        )
        assert auth_res["success"] is True
        assert "1-CLICK BUY EXECUTED" in auth_res["reply"]

    def test_api_endpoint_empty_sender_injection_vulnerability_eliminated(self):
        """API endpoints must reject empty or unauthorized sender (closes V2 default fallback loophole)."""
        client = TestClient(fastapi_app)

        # Missing / unauthorized sender should fail or return empty/failed payload
        res_empty = client.post("/api/whatsapp_command", json={"command": "status", "sender": ""})
        assert res_empty.status_code in [200, 403]
        if res_empty.status_code == 200:
            assert res_empty.json()["success"] is False
            assert res_empty.json()["response"] == ""

        res_unauth = client.post("/api/whatsapp_command", json={"command": "status", "sender": "1234567890@s.whatsapp.net"})
        assert res_unauth.status_code in [200, 403]
        if res_unauth.status_code == 200:
            assert res_unauth.json()["success"] is False
            assert res_unauth.json()["response"] == ""

        # Authorized sender succeeds
        res_auth = client.post("/api/whatsapp_command", json={"command": "status", "sender": "923468053268@s.whatsapp.net"})
        assert res_auth.status_code == 200
        assert res_auth.json()["success"] is True


# =====================================================================
# 2. FEATURE 23: INSTITUTIONAL 4-PILLAR WHATSAPP CARDS TESTS
# =====================================================================

class TestInstitutional4PillarCards:
    """Validates the structure, metrics, and tap-to-copy payloads of 4-Pillar trade cards."""

    def test_4pillar_trade_card_structure(self):
        """Card must contain all 4 standard institutional pillars with WhatsApp formatting."""
        card = InstitutionalCardFormatter.format_4pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            macro_data={
                "killzone": "NY AM Killzone (13:30 UTC)",
                "killzone_status": "Prime Execution Window",
                "news_status": "CLEAR",
                "regime": "RISK_OFF_GOLD_SURGE",
                "dxy": "Bearish (-0.45%)",
                "us10y": "Falling (-4.5 bps)",
                "vix": "18.4",
                "geopolitical_brief": "DEFCON 3 | Strait of Hormuz alerts active"
            },
            smc_data={
                "sweep_desc": "Retail Equal Lows (EQL) Swept on M15",
                "zone_desc": "Discount Zone (72.5% below 50% Eq) | 70.5% OTE Golden Pocket",
                "ob_fvg_desc": "Retesting M15 Demand OB + 50% CE FVG",
                "cvd_desc": "Strong Buyer Delta Absorption (+480 contracts, 68% Buyer Volume)",
                "confluence_score": "5.30",
                "trigger": "M15 Bullish Engulfing Candle closing above FVG 50% CE"
            },
            risk_data={"var_99": 465.27},
            sl_pips=110.0
        )

        # Header Verifications
        assert "INSTITUTIONAL 4-PILLAR TRADE SIGNAL & BLUEPRINT" in card
        assert "#XAUUSD" in card
        assert "STRONG BUY" in card
        assert "2,646.50" in card
        assert "2,635.50" in card
        assert "2,662.00" in card
        assert "2,680.00" in card

        # Pillar 1: Macro Context & Geopolitical Radar
        assert "PILLAR 1: MACRO CONTEXT & GEOPOLITICAL RADAR" in card
        assert "Active Killzone:" in card
        assert "News Blackout Shield:" in card
        assert "Macro Regime:" in card
        assert "Intermarket Radar:" in card
        assert "Geopolitical Threat:" in card
        assert "DEFCON 3" in card

        # Pillar 2: SMC & CVD Order Flow Confluence
        assert "PILLAR 2: SMC & CVD ORDER FLOW CONFLUENCE" in card
        assert "Liquidity Sweep:" in card
        assert "Dealing Array:" in card
        assert "Order Block & FVG:" in card
        assert "Lee-Ready CVD:" in card
        assert "AI Quant Consensus:" in card

        # Pillar 3: Risk & Fleet Sizing Rules
        assert "PILLAR 3: RISK & FLEET SIZING RULES" in card
        assert "1-Day 99% Parametric VaR:" in card
        assert "4-Account Fleet Sizing Guide:" in card
        assert "$100k Master Account:" in card
        assert "$50k Growth Account:" in card
        assert "$25k Main Account:" in card
        assert "$5k Micro Account:" in card

        # Pillar 4: Actionable Setup & 1-Click Execution Payloads
        assert "PILLAR 4: ACTIONABLE SETUP & 1-CLICK PAYLOADS" in card
        assert "1-Click Copy Commands" in card
        assert "```buy xauusd" in card
        assert "```be xauusd```" in card
        assert "```scale 50% xauusd```" in card or "```scale 50%```" in card
        assert "```close xauusd```" in card
        assert "Contingency Execution Rules" in card

    def test_community_signal_broadcaster_4pillar_integration(self):
        """CommunitySignalBroadcaster must output the standardized 4-Pillar format."""
        broadcaster = CommunitySignalBroadcaster()
        card = broadcaster.format_community_signal_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            analysis={"trend_direction": "BULLISH", "confluence_score": 5.2}
        )
        assert "PILLAR 1: MACRO CONTEXT" in card
        assert "PILLAR 2: SMC & CVD ORDER FLOW CONFLUENCE" in card
        assert "PILLAR 3: RISK & FLEET SIZING RULES" in card
        assert "PILLAR 4: ACTIONABLE SETUP & 1-CLICK PAYLOADS" in card
        assert "```buy xauusd" in card

    def test_5pillar_trade_card_structure(self):
        """Card must contain all 5 forensic institutional pillars with dynamic unpacking and WhatsApp formatting."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            tp3_price=2705.00,
            macro_data={
                "killzone": "NY AM Killzone (13:30 UTC)",
                "killzone_status": "Prime Execution Window",
                "news_status": "CLEAR",
                "regime": "RISK_OFF_GOLD_SURGE",
                "dxy": "Bearish (-0.45%)",
                "us10y": "Falling (-4.5 bps)",
                "vix": "18.4",
                "hormuz": "CRITICAL_WARZONE | Flow: 14.5 mbd (69% baseline)",
                "bab_mandeb": "CRITICAL_WARZONE | Flow: 2.1 mbd (33.9% baseline)",
                "cii": "84.2/100",
                "fed_liq": "Fed Net Liquidity $5,800B (+1.8% MoM)",
                "geopolitical_brief": "DEFCON 3 | Maritime Chokepoint Alerts Active"
            },
            smc_data={
                "sweep_desc": "Retail Equal Lows (EQL) Swept on M15 (Turtle Soup Purge)",
                "zone_desc": "Discount Zone (72.5% below 50% Eq) | 70.5% OTE Golden Pocket",
                "ob_fvg_desc": "Retesting M15 Demand OB + 50% CE FVG",
                "cvd_desc": "Strong Buyer Delta Absorption (+480 contracts, 68% Buyer Volume)",
                "confluence_score": "5.30",
                "trigger": "M15 Bullish Engulfing Candle closing above FVG 50% CE with CVD Buyer Surge",
                "urdu_rationale": "Big Sharks ne retail stop-loss sweep kar ke 50% CE FVG par heavy buyer volume absorb kiya hai."
            },
            psychology_data={
                "retail_trap": "Retail Trap: Chasing late breakout at resistance / panic selling into demand zone.",
                "shark_accumulation": "Institutional Iceberg Orders absorbing market sell pressure without lowering price.",
                "wyckoff_phase": "Wyckoff Phase C Spring & Liquidity Test / SOS Markup"
            },
            contagion_data={
                "gsr": "GSR at 113.97 -> Silver Undervalued (High-Beta catch-up target: $39.50)",
                "wti_oil": "$78.50/bbl (BULLISH_INFLATION_HEDGE -> Fuels Gold headline CPI tailwind)",
                "crypto_spillover": "IF Bitcoin absorbs CVD -> THEN ETH ($3,450.00) & SOL ($195.00) momentum expansion targets active",
                "liquidity_beta": "0.94 Composite Precious Metals Beta (Risk-Off Sovereign Co-Expansion)"
            },
            scenario_data={
                "scenario_a_if": "IF #XAUUSD holds 50% CE FVG / 70.5% OTE Discount with aggressive CVD buyer delta",
                "scenario_a_then": "THEN execute Long Scale-In, bank 50% profit at TP1, lock Breakeven, trail runner to TP2 and TP3",
                "scenario_a_urdu": "Agar price 70.5% OTE zone par hold karti hai aur CVD buyers delta barhta hai, toh BUY position lein.",
                "scenario_b_if": "IF price rejects at resistance / breaks structural SL on high seller CVD delta",
                "scenario_b_then": "THEN do NOT revenge trade; wait for secondary liquidity defense reload.",
                "scenario_b_urdu": "Agar structural SL break ho jaye toh ghabra kar revenge trade na karein."
            },
            risk_data={"var_99": 465.27},
            sl_pips=110.0
        )

        # Header Verifications
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card
        assert "#XAUUSD" in card
        assert "STRONG BUY" in card
        assert "2,646.50" in card
        assert "2,635.50" in card
        assert "2,662.00" in card
        assert "2,680.00" in card
        assert "2,705.00" in card

        # Pillar 1: Institutional Rationale & SMC Order Flow (Wajoohat)
        assert "PILLAR 1: INSTITUTIONAL RATIONALE & SMC ORDER FLOW (WAJOOHAT)" in card
        assert "Liquidity Sweep:" in card
        assert "Dealing Array & OTE:" in card
        assert "Order Block & FVG:" in card
        assert "Lee-Ready CVD Absorption:" in card
        assert "AI Quant Consensus Score:" in card
        assert "Wajoohat (Roman Urdu):" in card

        # Pillar 2: Market Psychology & Shark Trap Dynamics
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP DYNAMICS" in card
        assert "Retail Trap Identification:" in card
        assert "Big Shark Accumulation:" in card
        assert "Wyckoff Market Phase:" in card

        # Pillar 3: Macro & Geopolitical Backdrop
        assert "PILLAR 3: MACRO & GEOPOLITICAL BACKDROP" in card
        assert "Maritime Chokepoints Threat Radar:" in card
        assert "Strait of Hormuz:" in card
        assert "Bab-el-Mandeb" in card
        assert "Country Instability Index (CII):" in card
        assert "Central Bank Net Liquidity:" in card

        # Pillar 4: Cross-Market Contagion Matrix
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX (PREDICTIVE SPILLOVER)" in card
        assert "Gold/Silver Ratio (GSR):" in card
        assert "WTI Crude Oil Transmission:" in card
        assert "BTC -> ETH/SOL Momentum Target:" in card
        assert "Contagion Spillover Rule:" in card

        # Pillar 5: Scenario A/B What-If Roadmap
        assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP (ROMAN URDU + ENGLISH)" in card
        assert "SCENARIO A (Primary Trend Expansion" in card
        assert "SCENARIO B (Deep Liquidity Sweep / Defense" in card
        assert "Roman Urdu Roadmap:" in card

        # Sizing & 1-Click Payloads
        assert "PILLAR 3: RISK" not in card  # Replaced by standard bottom risk block
        assert "RISK & 4-ACCOUNT FLEET SIZING RULES" in card
        assert "1-Click Copy Commands" in card or "ACTIONABLE 1-CLICK PAYLOADS" in card
        assert "```buy xauusd" in card
        assert "```be xauusd```" in card
        assert "```scale 50% xauusd```" in card
        assert "```close xauusd```" in card

    def test_community_signal_broadcaster_5pillar_integration(self):
        """CommunitySignalBroadcaster must format 5-pillar signal cards when requested."""
        broadcaster = CommunitySignalBroadcaster()
        analysis = {
            "trend_direction": "BULLISH",
            "confluence_score": 5.35,
            "order_flow": {
                "in_ote_zone": True,
                "net_delta": 620,
                "buyer_volume_pct": 72.0,
                "sweep_desc": "Retail Equal Lows (EQL) Swept on M15 (Turtle Soup)",
                "ob_fvg_desc": "Retesting M15 Demand OB + 50% CE FVG",
                "trigger": "M15 Bullish Engulfing Candle above FVG 50% CE",
                "urdu_rationale": "Big Sharks ne Asian Session low sweep kar ke 50% CE FVG par buyers absorb kiye hain."
            },
            "psychology": {
                "retail_trap": "Breakout chasers trapped at resistance.",
                "shark_accumulation": "Iceberg limit bid orders absorbing sell volume.",
                "wyckoff_phase": "Wyckoff Phase C Spring"
            },
            "macro": {
                "killzone": "London Open (08:00 UTC)",
                "macro_regime": "RISK_OFF_GOLD_SURGE",
                "hormuz": "CRITICAL_WARZONE",
                "cii": "84.2/100",
                "fed_liq": "Fed Net Liquidity $5,800B"
            },
            "contagion": {
                "gsr": "GSR at 113.97 -> Silver Target $39.50",
                "wti_oil": "$78.50/bbl tailwind",
                "crypto_spillover": "BTC CVD absorption -> ETH/SOL target"
            },
            "scenario": {
                "scenario_a_if": "IF #XAUUSD holds 50% CE FVG",
                "scenario_a_then": "THEN scale in, bank 50% at TP1, lock BE",
                "scenario_a_urdu": "Agar 70.5% OTE hold kare toh BUY karein.",
                "scenario_b_if": "IF price breaks SL",
                "scenario_b_then": "THEN do NOT revenge trade.",
                "scenario_b_urdu": "Agar SL break ho toh sabar karein."
            },
            "risk": {
                "var_99": 465.27
            }
        }
        card = broadcaster.format_community_5pillar_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            analysis=analysis
        )
        assert "PILLAR 1: INSTITUTIONAL RATIONALE & SMC ORDER FLOW (WAJOOHAT)" in card
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP DYNAMICS" in card
        assert "PILLAR 3: MACRO & GEOPOLITICAL BACKDROP" in card
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX" in card
        assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP" in card
        assert "```buy xauusd" in card

    def test_whatsapp_notifier_forensic_receipt(self):
        """WhatsAppNotifier must format full forensic trade receipts with multi-tier TP1-3, R:R, and whale footprint."""
        from src.whatsapp_notifier import WhatsAppNotifier
        notifier = WhatsAppNotifier()
        dispatched_messages = []
        notifier.send_message = lambda msg: dispatched_messages.append(msg)

        trade_data = {
            "ticket": "PAPER-RECEIPT-1",
            "data_mode": "PAPER",
            "account_id": "TEST-25K",
            "symbol": "XAUUSD",
            "signal_type": "BUY",
            "volume": 0.45,
            "entry_price": 2646.50,
            "sl_price": 2635.50,
            "tp1_price": 2662.00,
            "tp2_price": 2680.00,
            "tp3_price": 2705.00,
            "sl_pips": 110.0,
            "risk_dollars": 495.00,
            "confluence_score": 5.30,
            "pattern": "M15 Demand Order Block + 50% CE FVG",
            "cvd_desc": "Strong Buyer Delta Absorption (+480 contracts, 68% Buyer Volume)",
            "wyckoff_phase": "WYCKOFF ACCUMULATION PHASE C (SPRING & TEST)"
        }
        notifier.send_trade_notification(trade_data)
        assert len(dispatched_messages) == 1
        msg = dispatched_messages[0]
        assert "EXECUTION RECEIPT — VERIFY IN BROKER" in msg
        assert "#XAUUSD" in msg
        assert "2,646.50" in msg
        assert "2,635.50" in msg
        assert "2,662.00" in msg
        assert "PAPER-RECEIPT-1" in msg
        assert "not risk-free" in msg
        assert "WHALE FOOTPRINT" not in msg
        assert "GSR 113.97" not in msg
        assert "`be xauusd`" in msg

    def test_autonomous_fleet_executor_forensic_receipt(self, tmp_path):
        """Paper execution emits a truthful, explicitly unverified WhatsApp receipt."""
        from src.autonomous_fleet_executor import AutonomousFleetExecutor
        from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
        from src.fleet_risk_manager import FleetRiskManager
        fleet_path = tmp_path / "fleet.json"
        onboarder = MultiAccountAutoOnboarder(config_path=str(fleet_path))
        onboarder.onboard_new_account(
            account_id="PAPER_FP", server="DEMO", balance=25_000,
            account_type="FUNDING_PIPS", client_whatsapp="923468053268",
            prop_model="FUNDING_PIPS_2_STEP_STANDARD", account_stage="EVALUATION_PHASE_1",
        )
        risk_manager = FleetRiskManager(config_path=str(fleet_path), auto_onboarder=onboarder)
        dispatched_notifications = []

        class MockWAManager:
            def notify_client_account_update(self, phone, account_name, message):
                dispatched_notifications.append({"phone": phone, "account_name": account_name, "message": message})
                return {"success": True}

        fleet_exec = AutonomousFleetExecutor(
            config_path=str(fleet_path), risk_manager=risk_manager,
            whatsapp_manager=MockWAManager(), simulation_mode=True,
            seed_demo_positions=False,
        )
        res = fleet_exec.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl=2635.50,
            tp1=2662.00,
            tp2=2680.00,
            tp3=2705.00,
            confluence_tag="70.5% OTE FVG MITIGATION",
            shark_tag="UNVERIFIED MARKET-STRUCTURE LABEL"
        )
        assert res["success"] is True
        assert len(dispatched_notifications) >= 1
        msg = dispatched_notifications[0]["message"]
        assert "NEW FLEET TRADE RECEIPT" in msg
        assert "#XAUUSD" in msg
        assert "2646.5" in msg
        assert "2635.5" in msg
        assert "2662.0" in msg
        assert "WHALE FOOTPRINT & ORDER FLOW:" in msg
        assert "Lee-Ready CVD:" in msg
        assert "Cross-market contagion:" in msg
        assert "No verified live values attached" in msg
        assert "Roman Urdu:" in msg
        assert "never guaranteed" in msg


# =====================================================================
# 3. FEATURE 24: WHATSAPP 1-CLICK COMMAND HANDLERS & LATENCY TESTS
# =====================================================================

class TestWhatsApp1ClickCommands:
    """Validates 10 core command types, symbol aliasing, and sub-300ms latency."""

    def setup_method(self):
        self.router = WhatsApp1ClickRouter()
        self.sender = "923468053268@s.whatsapp.net"

    def test_command_1_buy_order_and_sub300ms_latency(self):
        """Test BUY execution with lots, risk %, and latency verification."""
        # Fixed lots
        res = self.router.handle_command("buy gold 0.11", sender=self.sender)
        assert res["success"] is True
        assert res["action"] == "BUY"
        assert res["symbol"] == "XAUUSD"
        assert res["volume"] == 0.11
        assert res["execution_time_ms"] < 300.0, f"Latency {res['execution_time_ms']}ms exceeded 300ms SLA"
        assert "1-CLICK BUY EXECUTED" in res["reply"]

        # Risk % parameter
        res_risk = self.router.handle_command("buy xauusd risk 0.75%", sender=self.sender)
        assert res_risk["success"] is True
        assert res_risk["action"] == "BUY"
        assert res_risk["execution_time_ms"] < 300.0

    def test_command_2_sell_order(self):
        """Test SELL execution with symbol aliasing."""
        res = self.router.handle_command("sell eu 0.25", sender=self.sender)
        assert res["success"] is True
        assert res["action"] == "SELL"
        assert res["symbol"] == "EURUSD"
        assert res["volume"] == 0.25
        assert res["execution_time_ms"] < 300.0
        assert "1-CLICK SELL EXECUTED" in res["reply"]

    def test_command_3_breakeven_lock(self):
        """Breakeven must fail closed without a broker connector."""
        res = self.router.handle_command("be xauusd", sender=self.sender)
        assert res["success"] is False
        assert res["action"] == "BREAKEVEN"
        assert "NOT EXECUTED" in res["reply"]
        assert res["execution_time_ms"] < 300.0

        # Variation: 'breakeven' or 'lock'
        res2 = self.router.handle_command("lock 100101", sender=self.sender)
        assert res2["success"] is False
        assert res2["action"] == "BREAKEVEN"

    def test_command_4_scale_out(self):
        """Scale-out must fail closed without a broker connector."""
        res = self.router.handle_command("scale 50%", sender=self.sender)
        assert res["success"] is False
        assert res["action"] == "SCALE_OUT"
        assert res["ratio"] == 0.50
        assert "NOT EXECUTED" in res["reply"]
        assert res["execution_time_ms"] < 300.0

    def test_command_5_close_and_kill_switch(self):
        """Test CLOSE and EMERGENCY KILL SWITCH commands."""
        # Close specific ticket
        res_ticket = self.router.handle_command("close 100101", sender=self.sender)
        assert res_ticket["success"] is False
        assert res_ticket["action"] == "CLOSE_POSITION"

        # Emergency kill switch
        res_kill = self.router.handle_command("kill switch", sender=self.sender)
        assert res_kill["success"] is False
        assert res_kill["action"] == "CLOSE_ALL"
        assert "NOT EXECUTED" in res_kill["reply"]

    def test_command_6_status_telemetry(self):
        """Test STATUS account metrics."""
        res = self.router.handle_command("status", sender=self.sender)
        assert res["success"] is False
        assert res["action"] == "STATUS"
        assert "TELEMETRY UNAVAILABLE" in res["reply"]
        assert res["execution_time_ms"] < 300.0

    def test_command_7_summary_performance(self):
        """Test SUMMARY performance report."""
        res = self.router.handle_command("summary", sender=self.sender)
        assert res["success"] is False
        assert res["action"] == "SUMMARY"
        assert "PERFORMANCE SUMMARY UNAVAILABLE" in res["reply"]
        assert "were not invented" in res["reply"]

    def test_command_8_and_9_pause_and_resume_controls(self):
        """Test PAUSE and RESUME bot execution directives."""
        bot_mock = MagicMock()
        self.router.bot_engine = bot_mock

        res_pause = self.router.handle_command("pause", sender=self.sender)
        assert res_pause["success"] is True
        assert res_pause["action"] == "PAUSE"
        assert bot_mock.paused is True

        res_resume = self.router.handle_command("resume", sender=self.sender)
        assert res_resume["success"] is True
        assert res_resume["action"] == "RESUME"
        assert bot_mock.paused is False

    def test_command_10_set_risk_per_trade(self):
        """Test RISK percentage adjustment."""
        res = self.router.handle_command("risk 0.75%", sender=self.sender)
        assert res["success"] is True
        assert res["action"] == "SET_RISK"
        assert res["risk_pct"] == 0.25
        assert self.router.active_risk_pct == 0.25
        assert "RISK PER TRADE UPDATED" in res["reply"]

    def test_comprehensive_symbol_aliasing(self):
        """Test symbol alias resolution across metals, crypto, and FX."""
        aliases_to_test = {
            "gold": "XAUUSD", "xau": "XAUUSD", "sona": "XAUUSD",
            "silver": "XAGUSD", "xag": "XAGUSD", "chandi": "XAGUSD",
            "btc": "BTCUSD", "bitcoin": "BTCUSD",
            "eth": "ETHUSD", "ethereum": "ETHUSD",
            "sol": "SOLUSD", "solana": "SOLUSD",
            "eu": "EURUSD", "eur": "EURUSD",
            "gu": "GBPUSD", "cable": "GBPUSD",
            "uj": "USDJPY", "jpy": "USDJPY",
            "ej": "EURJPY", "gj": "GBPJPY", "au": "AUDUSD", "uc": "USDCAD"
        }
        for alias, expected in aliases_to_test.items():
            resolved = self.router.resolve_symbol(alias)
            assert resolved == expected, f"Expected alias {alias} to resolve to {expected}, got {resolved}"


# =====================================================================
# 4. FEATURE 25: VOICE AUDIO NOTE PROCESSING TESTS
# =====================================================================

class TestVoiceAudioNoteProcessing:
    """Validates voice note buffer handling, STT tiers, and intent routing."""

    def setup_method(self):
        self.transcriber = WhatsAppVoiceTranscriber()
        self.router = WhatsApp1ClickRouter()
        self.sender = "923468053268@s.whatsapp.net"

    def test_voice_transcription_mock_tiers(self):
        """Test deterministic mock STT fixtures for unit and CI testing."""
        # Buy voice note
        t_buy = self.transcriber.transcribe_audio("mock_gold_buy")
        assert "Buy Gold 0.11 lot" in t_buy

        # Breakeven voice note
        t_be = self.transcriber.transcribe_audio("mock_be")
        assert "be xauusd" in t_be

        # Roman Urdu market inquiry voice note
        t_urdu = self.transcriber.transcribe_audio("mock_gold_scene")
        assert "XAUUSD ka kya scene hai bhai?" in t_urdu

        # Kill switch voice note
        t_kill = self.transcriber.transcribe_audio("mock_kill_switch")
        assert "Emergency kill switch" in t_kill

    def test_voice_intent_entity_parser(self):
        """Test parsing transcribed speech into structured trading intents."""
        # Buy intent
        p_buy = self.transcriber.parse_voice_intent("Gold buy kar lo 0.5 lot")
        assert p_buy["intent"] == "TRADE_BUY"
        assert p_buy["symbol"] == "XAUUSD"
        assert p_buy["volume"] == 0.5

        # Breakeven intent
        p_be = self.transcriber.parse_voice_intent("Stop loss entry pe move kar do breakeven")
        assert p_be["intent"] == "BREAKEVEN"

        # Scale out intent
        p_scale = self.transcriber.parse_voice_intent("Half close kar do 50% on Gold")
        assert p_scale["intent"] == "SCALE_OUT"

        # Kill switch intent
        p_kill = self.transcriber.parse_voice_intent("Emergency kill switch close all trades")
        assert p_kill["intent"] == "KILL_SWITCH"

        # Consultation intent
        p_consult = self.transcriber.parse_voice_intent("XAUUSD ka kya scene hai bhai?")
        assert p_consult["intent"] == "CONSULTATION"

    def test_end_to_end_voice_audio_command_execution(self):
        """Test full audio note payload processing through router."""
        audio_payload = "mock_gold_buy_base64_stream"
        res = self.router.handle_audio_payload(
            audio_base64=audio_payload,
            sender=self.sender,
            duration=4.5
        )
        assert res["success"] is True
        assert res["action"] == "BUY"
        assert res["symbol"] == "XAUUSD"
        assert res["is_voice_note"] is True
        assert "transcription" in res
        assert "1-CLICK BUY EXECUTED" in res["reply"]

    def test_api_endpoint_audio_command_ingestion(self):
        """Test FastAPI /api/whatsapp_audio endpoint."""
        client = TestClient(fastapi_app)
        payload = {
            "sender": "923468053268@s.whatsapp.net",
            "audio_base64": "mock_gold_buy_sample_data",
            "duration": 4.5,
            "mimetype": "audio/ogg; codecs=opus"
        }
        res = client.post("/api/whatsapp_audio", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "1-CLICK BUY EXECUTED" in data.get("reply", "")


# =====================================================================
# 5. FEATURE 26: BILINGUAL WHATSAPP CONSULTATION TESTS
# =====================================================================

class TestBilingualWhatsAppConsultation:
    """Validates institutional English & Roman Urdu consultation and code-switching."""

    def setup_method(self):
        self.consultant = BilingualTradeConsultant()

    def test_roman_urdu_detection(self):
        """Verifies accurate detection of conversational Roman Urdu queries."""
        urdu_phrases = [
            "XAUUSD ka kya scene hai bhai?",
            "Gold buy karna theek rahay ga ya support break ho gaya?",
            "Bhai market kahan ja rahi hai?",
            "Trade le loon kya?",
            "Sab trades band karo",
            "Gold buy karu ya sell karu?"
        ]
        for phrase in urdu_phrases:
            assert self.consultant.is_roman_urdu(phrase) is True, f"Failed to detect Roman Urdu in: {phrase}"

        english_phrases = [
            "Where is liquidity lying on Gold?",
            "Should I short the top on USDJPY?",
            "What is the macro bias today?",
            "Give me the 4-pillar analysis for EURUSD."
        ]
        for phrase in english_phrases:
            assert self.consultant.is_roman_urdu(phrase) is False, f"Incorrectly detected Urdu in English: {phrase}"

    def test_roman_urdu_consultation_response_structure_and_codeswitching(self):
        """Verifies that Roman Urdu consultation produces institutional advice preserving technical terms."""
        query = "XAUUSD ka kya scene hai bhai? Buy karna theek rahay ga?"
        advice = self.consultant.generate_consultation(query, symbol="XAUUSD")

        assert "JARVIS INSTITUTIONAL" in advice
        assert "VERDICT:" in advice
        # Check technical code-switching (English terms intact in Urdu text)
        assert "SMC" in advice
        assert "OTE" in advice
        assert "Order Flow" in advice or "CVD" in advice
        assert "Breakeven" in advice
        assert "Stop Loss" in advice
        assert "Take Profit" in advice

    def test_english_consultation_response_structure(self):
        """Verifies institutional Wall Street English consultation response."""
        query = "Where is liquidity lying on Gold and should I short the top?"
        advice = self.consultant.generate_consultation(query, symbol="XAUUSD")

        assert "JARVIS INSTITUTIONAL ADVISORY" in advice
        assert "SHORT WARNING" in advice or "VERDICT:" in advice
        assert "LIQUIDITY FORENSICS" in advice or "SMC" in advice
        assert "STRATEGIC PLAYBOOK" in advice or "TARGETS" in advice


# =====================================================================
# 6. END-TO-END INTEGRATION TESTS WITH WHATSAPP QR MANAGER
# =====================================================================

class TestWhatsAppQRManagerIntegration:
    """Verifies end-to-end command dispatching across all operational paths."""

    def setup_method(self):
        self.mgr = WhatsAppQRManager()
        self.owner = "923468053268@s.whatsapp.net"

    def test_qr_manager_all_telemetry_commands(self):
        """Test telemetry and intelligence queries through WhatsAppQRManager."""
        commands = [
            "status", "fleet", "trades", "gold", "evidence", "plan",
            "why", "scan", "signal", "news", "whales", "world",
            "crisis", "crypto", "gsr", "brain", "advisor",
            "publicapis", "vision", "morning", "night", "risk",
            "report", "help"
        ]
        for cmd in commands:
            reply = self.mgr.handle_incoming_command(cmd, sender=self.owner)
            assert reply != "", f"Command '{cmd}' returned empty reply"
            assert len(reply) > 20, f"Command '{cmd}' reply was too short"

    def test_qr_manager_1click_execution_routing(self):
        """Paper entries are labelled, while management fails without broker positions."""
        reply_buy = self.mgr.handle_incoming_command("buy gold 0.10", sender=self.owner)
        assert "1-CLICK BUY EXECUTED" in reply_buy

        reply_be = self.mgr.handle_incoming_command("be xauusd", sender=self.owner)
        assert "BREAKEVEN NOT EXECUTED" in reply_be

        reply_scale = self.mgr.handle_incoming_command("scale 50%", sender=self.owner)
        assert "SCALE-OUT NOT EXECUTED" in reply_scale

    def test_qr_manager_voice_audio_routing(self):
        """Test voice audio routing through WhatsAppQRManager."""
        res = self.mgr.handle_incoming_audio(
            audio_base64="mock_gold_buy_audio",
            sender=self.owner,
            duration=4.5
        )
        assert res["success"] is True
        assert "1-CLICK BUY EXECUTED" in res["reply"]
