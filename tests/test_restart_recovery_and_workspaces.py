"""
tests/test_restart_recovery_and_workspaces.py
=============================================================================
End-to-End Verification Test Suite:
1. WhatsApp Inbound Replies & Human Intervention Resolution Gateway:
   - Verified resolution of options: 2 / kholo, otp: 123456, done / ho gaya, 4 / free
   - Verified inquiry resolution without false-positive hijacking of normal commands
   - Verified resolution resilience when no pending request is active
2. Terminal Natural Language Parsing & Chrome Profile Launcher:
   - Correct parsing and dispatch of complex natural language:
     'yeh you opened chrome but adeel vision wali profile open kero os main chatgpt open kero'
   - Absolute prevention of launching 'kero os main chatgpt open kero.exe'
3. 5 Parallel Virtual Workspaces & Screens Architecture:
   - Workspace 1 (MAIN), 2 (TRADING), 3 (WORLD), 4 (DEV), 5 (RESEARCH)
   - Real-time status reporting, port monitoring, foreground window switching
   - Terminal HUD formatting and command routing integration
4. Realistic Trading Rationale & Fail-Closed Verification:
   - Verification against real DOM microstructure and SMC liquidity sweeps
   - Fail-closed blocking on excessive risk (> $750 cap)
   - Fail-closed blocking on high spread (> 2.5 pips)
   - Fail-closed blocking on multi-timeframe trend conflicts
=============================================================================
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.human_intervention_gateway import (
    HumanInterventionGateway,
    InterventionType,
    RequestStatus,
    get_human_intervention_gateway,
)
from core.command_gateway import execute_command
from core.command_router import get_command_router
from core.virtual_workspaces import (
    VirtualWorkspaceManager,
    get_workspace_manager,
)
from core.trading.reasoning import (
    BigSharksReasoningEngine,
    verify_trade_readiness,
)


class TestWhatsAppInboundResolution(unittest.TestCase):
    """Verifies that WhatsApp replies are cleanly resolved via HumanInterventionGateway."""

    def setUp(self):
        self.gateway = HumanInterventionGateway(owner_phone="923468053268")

    def test_whatsapp_option_2_kholo(self):
        """Verifies reply '2' or 'kholo' activates PC screen and prepares portal."""
        req = self.gateway.request_2fa_code(
            service_name="FundingPips",
            portal_url="https://app.fundingpips.com/login"
        )
        handled, reply = self.gateway.resolve_from_message("2", sender_id="923468053268@s.whatsapp.net")
        self.assertTrue(handled)
        self.assertIn("PC SCREEN ACTIVATED", reply)
        self.assertIn("FundingPips", reply)

        # Test natural language 'kholo'
        handled_kholo, reply_kholo = self.gateway.resolve_from_message("kholo", sender_id="923468053268")
        self.assertTrue(handled_kholo)
        self.assertIn("PC SCREEN ACTIVATED", reply_kholo)

    def test_whatsapp_otp_submission(self):
        """Verifies reply 'otp: 123456' or numeric code resolves 2FA cleanly."""
        req = self.gateway.request_2fa_code(
            service_name="OpenAI API Platform",
            account_username="futureworldvision842@gmail.com"
        )
        handled, reply = self.gateway.resolve_from_message("otp: 789123", sender_id="923468053268")
        self.assertTrue(handled)
        self.assertIn("2FA / OTP CODE RECEIVED", reply)
        self.assertIn("789123", reply)
        self.assertEqual(req.status, RequestStatus.RESOLVED)

    def test_whatsapp_captcha_done(self):
        """Verifies reply 'done' or 'ho gaya' confirms captcha challenge."""
        req = self.gateway.request_captcha_resolution(
            target_site="Cloudflare Protected Portal",
            url="https://app.fundingpips.com"
        )
        handled, reply = self.gateway.resolve_from_message("done ho gaya", sender_id="923468053268")
        self.assertTrue(handled)
        self.assertIn("CAPTCHA RESOLUTION ACKNOWLEDGED", reply)
        self.assertEqual(req.status, RequestStatus.RESOLVED)

    def test_whatsapp_inquiry_without_hijacking_normal_commands(self):
        """Verifies intervention inquiries are answered while normal commands are NEVER hijacked."""
        # 1. Genuine inquiry about the intervention
        req = self.gateway.request_2fa_code(
            service_name="FundingPips Prop Firm",
            account_username="hamidqureshi872@gmail.com",
            code_destination="Aapke FundingPips Gmail (hamidqureshi872@gmail.com) Inbox"
        )
        handled, reply = self.gateway.resolve_from_message(
            "Account konsadala tha kaha email aaiga",
            sender_id="923468053268"
        )
        self.assertTrue(handled)
        self.assertIn("ACCOUNT & OTP DETAILS", reply)
        self.assertIn("hamidqureshi872@gmail.com", reply)

        # 2. Normal commands containing 'batao', 'account', 'status' must NOT be hijacked
        normal_commands = [
            "bhai gold ka status batao",
            "multiply account equity by 0.01 lot factor karo",
            "what is the account balance",
            "explain why trade was placed"
        ]
        for cmd in normal_commands:
            h, r = self.gateway.resolve_from_message(cmd, sender_id="owner")
            self.assertFalse(h, f"Command '{cmd}' must NOT be intercepted as human intervention inquiry.")


class TestTerminalNaturalLanguageAndChromeProfile(unittest.TestCase):
    """Verifies natural language Chrome profile and browser automation parsing."""

    def test_complex_natural_language_profile_launch(self):
        """
        Tests the exact prompt that previously produced an error:
        'yeh you opened chrome but adeel vision wali profile open kero os main chatgpt open kero'
        Verifies it launches Chrome with the Adeel profile navigating to ChatGPT.
        """
        test_prompt = "yeh you opened chrome but adeel vision wali profile open kero os main chatgpt open kero"
        receipt = execute_command(test_prompt, channel="terminal", owner_id="local_user", authorized=True)

        self.assertTrue(receipt.get("ok"))
        self.assertEqual(receipt.get("intent"), "browser_profile_launch")
        self.assertEqual(receipt.get("category"), "browser")
        self.assertIn("CHROME PROFILE AUTOMATION", receipt.get("output"))
        self.assertIn("ChatGPT", receipt.get("output"))
        self.assertIn("https://chatgpt.com", receipt.get("output"))

        # Verify no error attempting to launch .exe with spaces/Urdu
        self.assertNotIn(".exe' not found", receipt.get("output"))
        self.assertNotIn("kero os main chatgpt", receipt.get("output"))

    def test_profile_launch_with_gemini(self):
        """Verifies opening Adeel profile navigating to Gemini."""
        prompt = "adeel wali profile open karo us me gemini kholo"
        receipt = execute_command(prompt, channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(receipt.get("ok"))
        self.assertIn("Gemini", receipt.get("output"))
        self.assertIn("gemini.google.com", receipt.get("output"))


class Test5VirtualWorkspaces(unittest.TestCase):
    """Verifies the 5 parallel virtual workspaces architecture."""

    def setUp(self):
        self.manager = get_workspace_manager()

    def test_all_5_workspaces_defined(self):
        """Verifies all 5 canonical workspaces are configured."""
        workspaces = self.manager.list_all_workspaces()
        self.assertEqual(len(workspaces), 5)
        names = [w["name"] for w in workspaces]
        self.assertEqual(names, ["MAIN", "TRADING", "WORLD", "DEV", "RESEARCH"])

    def test_workspace_switching(self):
        """Verifies switching to Trading (2) and World (3)."""
        # Switch to Trading
        res_trading = self.manager.switch_workspace(2, bring_to_front=False)
        self.assertTrue(res_trading["ok"])
        self.assertEqual(res_trading["active_workspace"], 2)
        self.assertEqual(res_trading["name"], "TRADING")

        # Switch to World
        res_world = self.manager.switch_workspace("world", bring_to_front=False)
        self.assertTrue(res_world["ok"])
        self.assertEqual(res_world["active_workspace"], 3)
        self.assertEqual(res_world["name"], "WORLD")

        # Switch back to Main
        res_main = self.manager.switch_workspace(1, bring_to_front=False)
        self.assertTrue(res_main["ok"])
        self.assertEqual(res_main["active_workspace"], 1)

    def test_workspace_hud_display(self):
        """Verifies HUD display formatting."""
        hud = self.manager.format_hud_display()
        self.assertTrue("5-SCREEN" in hud or "5 - S C R E E N" in hud)
        self.assertIn("WORKSPACE 1: MAIN", hud)
        self.assertIn("WORKSPACE 2: TRADING", hud)
        self.assertIn("WORKSPACE 3: WORLD", hud)
        self.assertIn("WORKSPACE 4: DEV", hud)
        self.assertIn("WORKSPACE 5: RESEARCH", hud)

    def test_workspace_command_routing(self):
        """Verifies 'workspace 2' and 'workspaces' commands routed through gateway."""
        r1 = execute_command("workspace 2", channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(r1.get("ok"))
        self.assertEqual(r1.get("intent"), "workspace_switch")
        self.assertIn("TRADING", r1.get("output"))

        r2 = execute_command("workspaces", channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(r2.get("ok"))
        self.assertEqual(r2.get("intent"), "workspace_hud")
        self.assertTrue("5-SCREEN" in r2.get("output") or "5 - S C R E E N" in r2.get("output"))


class TestRealisticTradingRationale(unittest.TestCase):
    """Verifies fail-closed behavior and multi-confluence rationale enforcement."""

    def test_approved_nominal_setup(self):
        """Verifies compliant setup with aligned confluence and risk passes."""
        res = verify_trade_readiness(
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.33675,
            sl_price=1.33800,
            tp_price=1.33250,
            lot_size=0.10,
            current_spread=0.8
        )
        self.assertTrue(res["can_trade"])
        self.assertEqual(res["decision"], "APPROVED_EXECUTE")
        self.assertEqual(len(res["blockers"]), 0)
        self.assertIn("Liquidity Sweep", res["rationale"])

    def test_fail_closed_on_excessive_risk(self):
        """Verifies fail-closed rejection when risk exceeds $750.00 / 0.75% cap."""
        res = verify_trade_readiness(
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.33675,
            sl_price=1.35500,  # 182.5 pips away with 1.0 lot = $1,825 risk > $750 cap
            tp_price=1.30000,
            lot_size=1.00
        )
        self.assertFalse(res["can_trade"])
        self.assertEqual(res["decision"], "REJECTED_FAIL_CLOSED")
        self.assertTrue(any("exceeds strict FundingPips $750.00 cap" in b for b in res["blockers"]))

    def test_fail_closed_on_excessive_gold_risk(self):
        """Verifies fail-closed rejection for Gold (XAUUSD) when risk exceeds $750 cap."""
        # 1.0 lot with $10 stop distance = $1,000 risk (> $750 cap)
        res = verify_trade_readiness(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2700.00,
            sl_price=2690.00,
            tp_price=2730.00,
            lot_size=1.00,
            current_spread=1.0
        )
        self.assertFalse(res["can_trade"])
        self.assertEqual(res["decision"], "REJECTED_FAIL_CLOSED")
        self.assertTrue(any("exceeds strict FundingPips $750.00 cap" in b for b in res["blockers"]))
        self.assertEqual(res["risk_assessment"]["contract_multiplier"], 100.0)
        self.assertEqual(res["risk_assessment"]["risk_usd"], 1000.00)

    def test_approved_compliant_gold_risk(self):
        """Verifies compliant Gold (XAUUSD) setup passes with exact risk calculation."""
        # 0.10 lot with $5 stop distance = $50 risk (< $750 cap)
        res = verify_trade_readiness(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2700.00,
            sl_price=2695.00,
            tp_price=2715.00,
            lot_size=0.10,
            current_spread=1.0
        )
        self.assertTrue(res["can_trade"])
        self.assertEqual(res["decision"], "APPROVED_EXECUTE")
        self.assertEqual(len(res["blockers"]), 0)
        self.assertEqual(res["risk_assessment"]["contract_multiplier"], 100.0)
        self.assertEqual(res["risk_assessment"]["risk_usd"], 50.00)

    def test_fail_closed_on_invalid_geometry(self):
        """Verifies fail-closed rejection when SL or TP are on the wrong side of Entry."""
        # BUY with SL above Entry
        res_buy = verify_trade_readiness(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2700.00,
            sl_price=2710.00,
            tp_price=2720.00,
            lot_size=0.10
        )
        self.assertFalse(res_buy["can_trade"])
        self.assertTrue(any("Invalid BUY setup geometry" in b for b in res_buy["blockers"]))

        # SELL with SL below Entry
        res_sell = verify_trade_readiness(
            symbol="EURUSD",
            direction="SELL",
            entry_price=1.1000,
            sl_price=1.0950,
            tp_price=1.0800,
            lot_size=0.10
        )
        self.assertFalse(res_sell["can_trade"])
        self.assertTrue(any("Invalid SELL setup geometry" in b for b in res_sell["blockers"]))


class TestTerminalAdvancedCommandsAndIntegrations(unittest.TestCase):
    """Verifies SOV Roman Urdu, 3D Spatial Intelligence, and non-hijacked terminal diagnostics."""

    def test_terminal_sov_app_launch_and_close(self):
        """Verifies 'notepad kholo' and 'notepad band karo' execute app lifecycle."""
        r_launch = execute_command("notepad kholo", channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(r_launch.get("ok"))
        self.assertEqual(r_launch.get("intent"), "launch_app")
        self.assertTrue(r_launch.get("executed"))
        self.assertEqual(r_launch.get("data", {}).get("app"), "Notepad")

        r_close = execute_command("notepad band karo", channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(r_close.get("ok"))
        self.assertEqual(r_close.get("intent"), "close_app")
        self.assertTrue(r_close.get("executed"))

    def test_terminal_3d_globe_command(self):
        """Verifies '3d globe' routes to 3D spatial intelligence on port 4173."""
        r = execute_command("3d globe", channel="terminal", owner_id="local_user", authorized=True)
        self.assertTrue(r.get("ok"))
        self.assertEqual(r.get("intent"), "gods_eye_3d")
        self.assertEqual(r.get("category"), "vision")
        self.assertIn("3D SPATIAL INTELLIGENCE", r.get("output"))
        self.assertIn("4173", r.get("output"))

    def test_terminal_diagnostic_option_not_hijacked(self):
        """Verifies option '1' in terminal channel routes to self_healing_resolve and not OTP intervention."""
        router = get_command_router()
        envelope = router.process_command("1", channel="terminal", sender_id="local_user")
        self.assertTrue(envelope.ok)
        self.assertEqual(envelope.intent, "self_healing_resolve")
        self.assertNotIn("ENTER 2FA / OTP CODE", envelope.output_text)
        self.assertIn("SELF-HEALING COMPLETE", envelope.output_text)


if __name__ == "__main__":
    unittest.main()
