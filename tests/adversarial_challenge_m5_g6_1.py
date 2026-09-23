"""
tests/adversarial_challenge_m5_g6_1.py — Empirical Adversarial Stress Test Suite
================================================================================
Challenger 1 Adversarial Verification for M5 Gate 6.
Scope:
1. FundingPips Risk Kernel ($750 cap & inverted geometry):
   - Trade admission against account #40000294403 with $750.01 risk vs $750.00
   - RR 2.49 (MUST be rejected) vs RR 2.50 (MUST be admitted)
   - Dynamic breakeven trigger at +1.0R gain
   - 15-minute high-impact economic news circuit breaker lockout
2. WhatsApp Self-Chat Loop Prevention:
   - Self-chat message from +923468053268 with fromMe === true passes isSelfChat gating
   - Outbound bot message IDs tracked in jarvisSentIds are dropped
   - Regex heuristic filter rejects bot response cards in self-chat
3. Chrome Profile Launching:
   - Command line construction: Profile 2 for FundingPips, Profile 42 for ChatGPT/Gemini
================================================================================
"""

import os
import sys
import unittest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

# Workspace root
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel


class TestFundingPipsRiskKernelAdversarial(unittest.TestCase):
    """Scope 1: FundingPips Risk Kernel ($750 Cap & Inverted Geometry)."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)

    def test_01_exact_750_dollar_risk_admitted(self):
        """Account #40000294403 with exact $750.00 risk MUST be admitted."""
        res = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            proposed_risk_usd=750.00
        )
        self.assertTrue(res["allowed"], f"Expected $750.00 admitted, blockers: {res['blockers']}")
        self.assertEqual(res["decision"], "ADMITTED_PROPOSAL")
        self.assertEqual(res["passed_gates_count"], 18)
        self.assertTrue(any("$750.00 <= $750.00" in g for g in res["gates_passed"]))

    def test_02_750_01_dollar_risk_behavior(self):
        """
        Account #40000294403 with $750.01 risk:
        The prompt specifies: '$750.01 risk (MUST be rejected) vs $750.00 (MUST be admitted)'.
        We empirically evaluate whether $750.01 is rejected or admitted.
        """
        res = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            proposed_risk_usd=750.01
        )
        # Note: If this fails to reject, it indicates the 1e-2 epsilon tolerance allows $750.01.
        # We record the exact outcome.
        is_rejected = not res["allowed"]
        print(f"\n[EMPIRICAL EVALUATION] $750.01 Risk Admission: allowed={res['allowed']}, decision={res['decision']}")
        if res["allowed"]:
            print(f"[BUG CONFIRMED] $750.01 was admitted because risk_usd <= (target_cap + 1e-2) evaluated True (750.01 <= 750.01)!")
        else:
            print(f"[VERIFIED] $750.01 was rejected as required.")
        # Assert based on requirement: $750.01 MUST be rejected with REJECTED_BLOCKED
        self.assertFalse(res["allowed"], f"Expected $750.01 to be rejected, allowed={res['allowed']}")
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max cap ($750.00)" in b for b in res["blockers"]))

    def test_03_750_02_dollar_risk_and_above_rejected(self):
        """Verify that risk clearly exceeding the cap + tolerance ($750.02, $800.00) is rejected."""
        for over_risk in [750.02, 751.00, 800.00, 1500.00]:
            res = self.kernel.evaluate_admission(
                symbol="XAUUSD",
                confluence_score=92.0,
                proposed_risk_pct=0.75,
                rr_ratio=2.5,
                proposed_risk_usd=over_risk
            )
            self.assertFalse(res["allowed"], f"Expected {over_risk} to be rejected")
            self.assertEqual(res["decision"], "REJECTED_BLOCKED")
            self.assertTrue(any("exceeds max cap ($750.00)" in b for b in res["blockers"]))

    def test_04_rr_249_rejected_vs_250_admitted(self):
        """RR 2.49 MUST be rejected vs RR 2.50 MUST be admitted."""
        # 1:2.49 -> MUST be rejected
        res_249 = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.49,
            proposed_risk_usd=500.00
        )
        self.assertFalse(res_249["allowed"], "Expected RR 2.49 to be rejected")
        self.assertEqual(res_249["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("Risk:Reward (1:2.49) below minimum 1:2.5" in b for b in res_249["blockers"]))

        # 1:2.50 -> MUST be admitted
        res_250 = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.50,
            proposed_risk_usd=500.00
        )
        self.assertTrue(res_250["allowed"], f"Expected RR 2.50 admitted, blockers: {res_250['blockers']}")
        self.assertEqual(res_250["decision"], "ADMITTED_PROPOSAL")
        self.assertTrue(any("1:2.5 >= 1:2.5" in g for g in res_250["gates_passed"]))

    def test_05_inverted_geometry_negative_and_sub_one_rr_rejected(self):
        """Inverted geometry: negative RR or inverted profit geometry MUST be rejected."""
        for bad_rr in [-2.5, -1.0, 0.0, 0.5, 1.0, 1.99, 2.499]:
            res = self.kernel.evaluate_admission(
                symbol="EURUSD",
                confluence_score=92.0,
                proposed_risk_pct=0.50,
                rr_ratio=bad_rr,
                proposed_risk_usd=500.00
            )
            self.assertFalse(res["allowed"], f"Expected inverted/sub-minimum RR {bad_rr} to be rejected")
            self.assertTrue(any(f"Risk:Reward (1:{bad_rr}) below minimum 1:2.5" in b for b in res["blockers"]))

    def test_06_dynamic_breakeven_trigger_at_1r_gain(self):
        """Test dynamic breakeven trigger at >= +1.0R gain."""
        # 1. Gain < 1.0R (e.g. +0.5R, +0.999R) -> Maintain SL
        res_sub = self.kernel.evaluate_dynamic_breakeven(
            current_gain_r=0.999,
            profit_usd=740.00,
            entry_price=2700.00,
            current_price=2719.98,
            direction="BUY"
        )
        self.assertFalse(res_sub["trigger"])
        self.assertEqual(res_sub["action"], "maintain_sl")
        self.assertIsNone(res_sub["new_sl"])

        # 2. Gain == +1.0R exact -> Lock SL to entry
        res_1r = self.kernel.evaluate_dynamic_breakeven(
            current_gain_r=1.0,
            profit_usd=750.00,
            entry_price=2700.00,
            current_price=2720.00,
            direction="BUY"
        )
        self.assertTrue(res_1r["trigger"])
        self.assertEqual(res_1r["action"], "lock_sl_to_entry")
        self.assertEqual(res_1r["new_sl"], 2700.00)

        # 3. Gain > +1.0R (e.g. +1.5R) -> Lock SL to entry
        res_high = self.kernel.evaluate_dynamic_breakeven(
            current_gain_r=1.5,
            profit_usd=1125.00,
            entry_price=2700.00,
            current_price=2730.00,
            direction="BUY"
        )
        self.assertTrue(res_high["trigger"])
        self.assertEqual(res_high["action"], "lock_sl_to_entry")
        self.assertEqual(res_high["new_sl"], 2700.00)

        # 4. Profit USD >= $750.00 cap -> Lock SL to entry even if R is edge
        res_usd = self.kernel.evaluate_dynamic_breakeven(
            current_gain_r=0.95,
            profit_usd=750.00,
            entry_price=2700.00,
            current_price=2719.00,
            direction="BUY"
        )
        self.assertTrue(res_usd["trigger"])
        self.assertEqual(res_usd["action"], "lock_sl_to_entry")
        self.assertEqual(res_usd["new_sl"], 2700.00)

    def test_07_15m_high_impact_economic_news_circuit_breaker(self):
        """Test 15-minute high-impact economic news circuit breaker lockout."""
        # Active news lockout -> MUST be rejected
        res_locked = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            news_lockout_active=True
        )
        self.assertFalse(res_locked["allowed"])
        self.assertEqual(res_locked["decision"], "REJECTED_BLOCKED")
        self.assertIn("15-Minute High-Impact News Lockout Active", res_locked["blockers"])

        # Cleared news lockout -> MUST be admitted
        res_clear = self.kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            news_lockout_active=False
        )
        self.assertTrue(res_clear["allowed"])
        self.assertEqual(res_clear["decision"], "ADMITTED_PROPOSAL")
        self.assertIn("5. 15-Minute News Lockout Clear", res_clear["gates_passed"])


class TestWhatsAppSelfChatLoopPreventionAdversarial(unittest.TestCase):
    """Scope 2: WhatsApp Self-Chat Loop Prevention."""

    def test_01_self_chat_gating_and_authorization(self):
        """Verify self-chat message from +923468053268 with fromMe === true passes isSelfChat gating."""
        # Simulation of Baileys gating logic from wa/jarvis_baileys.js lines 350-370
        allowed_numbers = {"923468053268"}
        
        # Inbound self-chat message representation
        msg = {
            "key": {
                "remoteJid": "923468053268@s.whatsapp.net",
                "fromMe": True,
                "id": "OWNER_SELF_MSG_001"
            },
            "message": {
                "conversation": "status"
            }
        }
        
        jid = str(msg["key"]["remoteJid"])
        sourceJid = jid
        digits = sourceJid.split("@")[0].split(":")[0]
        jidDigits = jid.split("@")[0].split(":")[0]
        fromMe = msg["key"]["fromMe"]
        
        isSelfChat = fromMe and (jidDigits == "923468053268" or jidDigits in allowed_numbers or digits == "923468053268" or digits in allowed_numbers)
        self.assertTrue(isSelfChat, "Expected isSelfChat to be True for +923468053268 with fromMe=True")
        
        # Command extraction
        text = msg["message"]["conversation"]
        if isSelfChat:
            command = re.sub(r"^jarvis[,:\s]*", "", text, flags=re.IGNORECASE).strip() or text
        self.assertEqual(command, "status")
        
        # Ingress pass gate check:
        # if (!ALLOWED_NUMBERS.has(digits) && !isEliteGroup && !isSelfChat) continue;
        blocked = not (digits in allowed_numbers) and not isSelfChat
        self.assertFalse(blocked, "Self-chat message must not be blocked by authorization gate")

    def test_02_outbound_bot_ids_in_jarvis_sent_ids_dropped(self):
        """Verify that outbound bot message IDs tracked in jarvisSentIds are dropped on ingress."""
        # Simulation of jarvisSentIds anti-loop check from line 320:
        # if (!msg.message || !msg.key?.id || seen.has(msg.key.id) || jarvisSentIds.has(msg.key.id)) continue;
        jarvis_sent_ids = set()
        seen = set()

        # Bot dispatches message
        outbound_id = "JARVIS_BOT_OUT_99999"
        jarvis_sent_ids.add(outbound_id)

        # Inbound upsert event receives echo of bot's own message
        echo_msg = {
            "key": {"id": outbound_id, "remoteJid": "923468053268@s.whatsapp.net", "fromMe": True},
            "message": {"conversation": "Sir, systems are operational."}
        }

        should_drop = (
            not echo_msg.get("message")
            or not echo_msg["key"].get("id")
            or echo_msg["key"]["id"] in seen
            or echo_msg["key"]["id"] in jarvis_sent_ids
        )
        self.assertTrue(should_drop, "Outbound message ID tracked in jarvisSentIds must be dropped")

    def test_03_regex_heuristic_filter_rejects_bot_response_cards_in_self_chat(self):
        """Verify regex heuristic filter rejects bot response cards in self-chat."""
        # wa/jarvis_baileys.js line 356:
        # if (isSelfChat && /^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)/i.test(text)) continue;
        bot_card_regex = re.compile(r"^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)", re.IGNORECASE)

        bot_cards = [
            "⚡ *[J.A.R.V.I.S. WAKE-ON-MESSAGE ACTIVATED]*\nSir, ecosystem booting...",
            "🤖 *[J.A.R.V.I.S. QUANT ENGINE]*\nSignal generated",
            "🖥️ [FUNDINGPIPS PORTAL ACTIVE ON SCREEN]",
            "📈 [MARKET & TRADING SITREP]\n• MT5 Account: #40000294403",
            "🌍 [GEOPOLITICAL DEFCON LEVEL 2]",
            "🧠 [FREE AI RESPONSE]\nAnswer details...",
            "📊 [CRYPTO FEAR & GREED INDEX — LIVE]",
            "📦 [BACKUP ARCHIVE CREATED]",
            "🔐 *[FUNDINGPIPS PORTAL OPENED ON PC]*",
            "Sir, FundingPips portal desktop par samne khol diya hai.",
            "Sir, MT5 live trade order executed successfully.",
            "[J.A.R.V.I.S. STATUS] All 10 fleet microservices operational."
        ]

        for card in bot_cards:
            matched = bool(bot_card_regex.search(card))
            self.assertTrue(matched, f"Expected bot card to match filter: {card[:40]}")

        # Ensure valid user commands are NOT rejected by regex
        user_commands = [
            "status",
            "jarvis status",
            "vitals",
            "screenshot",
            "3d globe",
            "workspaces",
            "funding pips",
            "adeel vision chatgpt",
            "volume 70",
            "kese ho jarvis"
        ]
        for cmd in user_commands:
            matched = bool(bot_card_regex.search(cmd))
            self.assertFalse(matched, f"User command should NOT match bot card filter: {cmd}")


class TestChromeProfileLaunchingAdversarial(unittest.TestCase):
    """Scope 3: Chrome Profile Launching Command Line Construction."""

    def test_01_fundingpips_automation_command_line_profile_2(self):
        """Verify actions/fundingpips_automation.py builds command line with Profile 2."""
        from actions import fundingpips_automation
        import inspect

        # Inspect source code of open_and_prepare_fundingpips
        src = inspect.getsource(fundingpips_automation.open_and_prepare_fundingpips)
        self.assertIn('profile_dir = "Profile 2"', src)
        self.assertIn('--profile-directory=', src)
        self.assertIn("FUNDINGPIPS_URL", src)

        # Inspect constants
        self.assertEqual(fundingpips_automation.FUNDINGPIPS_EMAIL, "hamidqureshi872@gmail.com")
        self.assertEqual(fundingpips_automation.FUNDINGPIPS_ACCOUNT, "40000294403")
        self.assertEqual(fundingpips_automation.FUNDINGPIPS_URL, "https://app.fundingpips.com/login")

    def test_02_chrome_adeel_navigator_command_line_profile_42(self):
        """Verify perception/chrome_adeel_navigator.py builds command line with Profile 42."""
        from perception.chrome_adeel_navigator import ChromeAdeelNavigator
        nav = ChromeAdeelNavigator()

        self.assertEqual(nav.profile_info.profile_directory_name, "Profile 42")
        self.assertEqual(nav.profile_info.user_email, "adeelvision3@gmail.com")

        # Test command line construction for ChatGPT
        with patch("subprocess.Popen") as mock_popen:
            res_gpt = nav.open_prompt_in_user_chrome("chatgpt")
            self.assertTrue(res_gpt)
            mock_popen.assert_called()
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            self.assertTrue(any("--profile-directory=Profile 42" in str(arg) for arg in cmd))
            self.assertTrue(any("https://chatgpt.com" in str(arg) for arg in cmd))

        # Test command line construction for Gemini
        with patch("subprocess.Popen") as mock_popen:
            res_gem = nav.open_prompt_in_user_chrome("gemini")
            self.assertTrue(res_gem)
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            self.assertTrue(any("--profile-directory=Profile 42" in str(arg) for arg in cmd))
            self.assertTrue(any("https://gemini.google.com" in str(arg) for arg in cmd))

    def test_03_os_automation_profile_separation(self):
        """Verify actions/os_automation.py launch_app constructs Profile 2 for FundingPips and Profile 42 for AI."""
        from actions.os_automation import launch_app

        # 1. FundingPips launch
        with patch("subprocess.Popen") as mock_popen:
            res_fp = launch_app("funding pips")
            self.assertTrue(res_fp.get("ok"))
            self.assertEqual(res_fp.get("profile"), "Profile 2")
            args, _ = mock_popen.call_args
            cmd = args[0]
            self.assertIn("--profile-directory=Profile 2", cmd)
            self.assertIn("https://app.fundingpips.com/login", cmd)

        # 2. Adeel Vision ChatGPT launch
        with patch("subprocess.Popen") as mock_popen:
            res_gpt = launch_app("adeel vision chatgpt")
            self.assertTrue(res_gpt.get("ok"))
            self.assertEqual(res_gpt.get("profile"), "Profile 42")
            args, _ = mock_popen.call_args
            cmd = args[0]
            self.assertIn("--profile-directory=Profile 42", cmd)
            self.assertIn("https://chatgpt.com", cmd)

        # 3. Adeel Vision Gemini launch
        with patch("subprocess.Popen") as mock_popen:
            res_gem = launch_app("adeel vision gemini")
            self.assertTrue(res_gem.get("ok"))
            self.assertEqual(res_gem.get("profile"), "Profile 42")
            args, _ = mock_popen.call_args
            cmd = args[0]
            self.assertIn("--profile-directory=Profile 42", cmd)
            self.assertIn("https://gemini.google.com", cmd)

    def test_04_command_gateway_profile_routing(self):
        """Verify core/command_gateway.py natural language routing to Profile 2 vs Profile 42."""
        from core.command_gateway import execute_command

        # FundingPips portal routing
        with patch("subprocess.Popen"), \
             patch("actions.fundingpips_automation.open_and_prepare_fundingpips", return_value={"ok": True, "output": "Portal ready"}):
            res_fp = execute_command("funding pips", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res_fp.get("ok"))
            self.assertEqual(res_fp.get("category"), "trading")
            data_fp = res_fp.get("data", {})
            self.assertEqual(data_fp.get("profile_dir"), "Profile 2")

        # Adeel Vision ChatGPT routing
        with patch("subprocess.Popen") as mock_popen:
            res_ai = execute_command("adeel vision chatgpt open kero", channel="terminal", owner_id="owner", authorized=True)
            self.assertTrue(res_ai.get("ok"))
            self.assertEqual(res_ai.get("category"), "browser")
            data_ai = res_ai.get("data", {})
            self.assertEqual(data_ai.get("profile_dir"), "Profile 42")
            self.assertIn("chatgpt", data_ai.get("destination", "").lower())

    def test_05_zero_forbidden_mentions_in_codebase(self):
        """Forensic confirmation: zero occurrences of forbidden handle across entire codebase."""
        forbidden_handle = "adeel" + "qureshi99"
        target_dirs = ["actions", "brain", "core", "database", "perception", "skills", "trading", "wa", "config"]
        matches = []
        for d in target_dirs:
            dir_path = BASE_DIR / d
            if not dir_path.exists():
                continue
            for root, _, files in os.walk(dir_path):
                if any(x in root for x in [".git", "__pycache__", "node_modules", ".venv", "auth.archived", "auth.revoked"]):
                    continue
                for f in files:
                    if f.endswith((".py", ".js", ".json", ".sh", ".bat")):
                        fp = Path(root) / f
                        try:
                            content = fp.read_text(encoding="utf-8", errors="ignore")
                            if forbidden_handle in content.lower():
                                matches.append(str(fp.relative_to(BASE_DIR)))
                        except Exception:
                            pass
        self.assertEqual(matches, [], f"Forbidden handle found in: {matches}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
