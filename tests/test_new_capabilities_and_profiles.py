"""
tests/test_new_capabilities_and_profiles.py
================================================================================
Targeted verification suite for newly implemented capabilities:
1. Multi-Profile Chrome Intelligence (Hamid 872 Profile 2 vs Adeel Vision Profile 42)
2. WhatsApp Self-Chat Loop and Anti-Loop Protection
3. DEX Screener Meme Coin Quant Research Skill
4. Dynamic Local Agent Mesh & Orchestrator
5. MongoDB Document Store Manager
================================================================================
"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _exec(cmd):
    from core.command_gateway import execute_command
    return execute_command(cmd, channel="terminal", owner_id="local_user", authorized=True)


class TestMultiProfileChromeIntelligence(unittest.TestCase):
    """Verifies profile separation: Hamid 872 for FundingPips, Adeel for AI."""

    def test_os_automation_routes_hamid872_for_fundingpips(self):
        from actions.os_automation import launch_app
        # Mock or run launch_app for hamid 872
        res = launch_app("funding pips hamid 872 profile")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("profile"), "Profile 2")
        self.assertIn("fundingpips.com", res.get("url"))

    def test_command_gateway_routes_fundingpips_to_profile2(self):
        res = _exec("funding pips hamid 872 profile kholo")
        self.assertTrue(res.get("ok"))
        data = res.get("data", {})
        self.assertEqual(data.get("profile_dir"), "Profile 2")
        self.assertEqual(data.get("profile"), "Hamid 872")
        self.assertIn("fundingpips.com", data.get("destination"))

    def test_command_gateway_routes_chatgpt_to_profile42(self):
        res = _exec("adeel vision wali profile open kero os main chatgpt open kero")
        self.assertTrue(res.get("ok"))
        data = res.get("data", {})
        self.assertIn(data.get("profile_dir"), ("Profile 42", "adeel"))
        self.assertIn("chatgpt.com", data.get("destination"))


class TestDEXScreenerMemeCoinResearch(unittest.TestCase):
    """Verifies live on-chain DEX Screener quant scanning."""

    def test_top_boosted_meme_coins(self):
        from skills.dexscreener_meme_research import get_top_boosted_meme_coins
        res = get_top_boosted_meme_coins(limit=3)
        self.assertIsInstance(res, str)
        self.assertIn("DEX SCREENER TOP BOOSTED MEME COINS", res)

    def test_search_meme_coin_pepe(self):
        from skills.dexscreener_meme_research import search_meme_coin
        res = search_meme_coin("pepe")
        self.assertIsInstance(res, str)
        self.assertIn("DEX SCREENER MEME COIN RADAR", res)
        self.assertIn("Liquidity", res)

    def test_deep_meme_coin_research_audit(self):
        from skills.dexscreener_meme_research import deep_meme_coin_research
        res = deep_meme_coin_research("bonk")
        self.assertIsInstance(res, str)
        self.assertIn("QUANT REPUTATION SCORE", res)

    def test_command_gateway_meme_coin_routing(self):
        res = _exec("trending meme coins")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("intent"), "meme_coin_scan")
        self.assertIn("DEX SCREENER", res.get("output"))


class TestDynamicLocalAgentMesh(unittest.TestCase):
    """Verifies dynamic local sub-agent creation and management."""

    def setUp(self):
        from brain.local_agent_orchestrator import get_agent_orchestrator
        self.orchestrator = get_agent_orchestrator()

    def test_default_agent_roster(self):
        agents = self.orchestrator.list_agents()
        self.assertGreaterEqual(len(agents), 5)
        ids = [a["agent_id"] for a in agents]
        self.assertIn("trading_sentinel", ids)
        self.assertIn("research_scout", ids)
        self.assertIn("system_guardian", ids)
        self.assertIn("vibe_coder", ids)
        self.assertIn("communications_officer", ids)

    def test_create_custom_subagent(self):
        res = self.orchestrator.create_custom_agent(
            name="Meme Coin Sniper",
            role="On-Chain DEX Specialist",
            specialty="Instant liquidity pool auditing on Solana",
            system_prompt="Audit liquidity lock and buy/sell tax.",
            tools=["dexscreener_meme_research"]
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("agent_id"), "meme_coin_sniper")

    def test_command_gateway_local_agents_roster(self):
        res = _exec("list agents")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("intent"), "local_agents_hud")
        self.assertIn("DYNAMIC LOCAL AGENT MESH", res.get("output"))


class TestMongoDBDocumentStore(unittest.TestCase):
    """Verifies document store CRUD and local persistent fallback."""

    def setUp(self):
        from database.mongodb_manager import get_mongodb_manager
        self.db = get_mongodb_manager()

    def test_document_insert_and_find(self):
        doc = {"test_key": "audit_value_123", "author": "Master Muhammad"}
        insert_res = self.db.insert_one("unit_test_collection", doc)
        self.assertTrue(insert_res.get("ok"))

        found = self.db.find("unit_test_collection", {"test_key": "audit_value_123"})
        self.assertGreaterEqual(len(found), 1)
        self.assertEqual(found[0]["author"], "Master Muhammad")

    def test_mongodb_skill_execution(self):
        from skills.mongodb_skill import run as run_mongo
        out = run_mongo({"action": "status"})
        self.assertIn("MONGODB / DOCUMENT STORE STATUS", out)


class TestWhatsAppSelfChatAndAntiLoop(unittest.TestCase):
    """Verifies WhatsApp self-chat support, Baileys lexical scoping, ring-buffer bounding, and 4-layer loop mitigation."""

    def test_baileys_lexical_scoping_and_bounding(self):
        import subprocess
        import json
        baileys_file = ROOT / "wa" / "jarvis_baileys.js"
        self.assertTrue(baileys_file.exists(), "wa/jarvis_baileys.js must exist")

        code = baileys_file.read_text(encoding="utf-8")
        start_idx = code.find("async function start()")
        self.assertNotEqual(start_idx, -1, "start() function must exist")

        sent_ids_idx = code.find("const jarvisSentIds = new Set()")
        seen_idx = code.find("const seen = new Set()")
        self.assertNotEqual(sent_ids_idx, -1, "jarvisSentIds must be declared")
        self.assertNotEqual(seen_idx, -1, "seen must be declared")

        self.assertLess(sent_ids_idx, start_idx, "jarvisSentIds must be in module scope before start()")
        self.assertLess(seen_idx, start_idx, "seen must be in module scope before start()")

        # Ensure no shadow redeclarations inside start()
        inside_start = code[start_idx:]
        self.assertNotIn("const jarvisSentIds =", inside_start)
        self.assertNotIn("let jarvisSentIds =", inside_start)
        self.assertNotIn("const seen =", inside_start)
        self.assertNotIn("let seen =", inside_start)

        # Run node -c syntax check
        node_res = subprocess.run(["node", "-c", str(baileys_file)], capture_output=True, text=True)
        self.assertEqual(node_res.returncode, 0, f"node -c syntax check failed: {node_res.stderr}")

        # Run Node execution test for ring-buffer bounding at 2000 items
        node_script = """
        const fs = require('fs');
        const code = fs.readFileSync('wa/jarvis_baileys.js', 'utf8');
        const snippet = code.substring(code.indexOf('const jarvisSentIds = new Set()'), code.indexOf('async function start()'));
        const fn = new Function(snippet + `
          for (let i = 0; i < 2050; i++) {
            jarvisSentIds.add('MSG_' + i);
          }
          return {
            size: jarvisSentIds.size,
            has_0: jarvisSentIds.has('MSG_0'),
            has_49: jarvisSentIds.has('MSG_49'),
            has_50: jarvisSentIds.has('MSG_50'),
            has_2049: jarvisSentIds.has('MSG_2049')
          };
        `);
        console.log(JSON.stringify(fn()));
        """
        proc = subprocess.run(["node", "-e", node_script], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Node ring-buffer test failed: {proc.stderr}")
        report = json.loads(proc.stdout)
        self.assertEqual(report["size"], 2000, "jarvisSentIds must be bounded at 2000 entries")
        self.assertFalse(report["has_0"], "Oldest item MSG_0 must be evicted")
        self.assertFalse(report["has_49"], "Oldest item MSG_49 must be evicted")
        self.assertTrue(report["has_50"], "Item MSG_50 must be retained")
        self.assertTrue(report["has_2049"], "Newest item MSG_2049 must be retained")

    def test_whatsapp_self_chat_condition_and_loop_mitigation(self):
        baileys_file = ROOT / "wa" / "jarvis_baileys.js"
        code = baileys_file.read_text(encoding="utf-8")

        # Verify isSelfChat condition
        self.assertIn("isSelfChat", code)
        self.assertIn("923468053268", code)
        self.assertIn("fromMe", code)

        # Verify 4-layer loop mitigation:
        # Layer 1: Outbound message ID tracking
        self.assertIn("jarvisSentIds.has(msg.key.id)", code)
        # Layer 2: Inbound deduplication cache
        self.assertIn("seen.has(msg.key.id)", code)
        # Layer 3: Anti-loop regex for J.A.R.V.I.S. response signatures
        self.assertIn("^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\\[J\\.A\\.R\\.V\\.I\\.S\\.)", code)
        # Layer 4: WhatsAppRateLimiter
        from core.whatsapp_rate_limiter import get_whatsapp_limiter, WhatsAppRateLimiter
        limiter = get_whatsapp_limiter()
        self.assertIsInstance(limiter, WhatsAppRateLimiter)
        can_send, reason = limiter.can_dispatch_whatsapp(is_user_reply=True)
        self.assertTrue(can_send, "User reply must always be allowed through rate limiter")

    def test_r1_chrome_profile_routing_and_prohibition(self):
        # FundingPips uses Profile 2
        funding_file = ROOT / "actions" / "fundingpips_automation.py"
        funding_code = funding_file.read_text(encoding="utf-8")
        self.assertIn('profile_dir = "Profile 2"', funding_code)
        self.assertIn("hamidqureshi872@gmail.com", funding_code)

        # Adeel Vision uses Profile 42
        adeel_file = ROOT / "perception" / "chrome_adeel_navigator.py"
        adeel_code = adeel_file.read_text(encoding="utf-8")
        self.assertIn('"Profile 42"', adeel_code)
        self.assertIn("adeelvision3@gmail.com", adeel_code)

        # Command gateway routing
        from core.command_gateway import execute_command
        res_fp = execute_command("open funding pips", authorized=True)
        self.assertTrue(res_fp.get("ok"))
        self.assertEqual(res_fp.get("data", {}).get("profile_dir"), "Profile 2")

        res_ai = execute_command("open chatgpt", authorized=True)
        self.assertTrue(res_ai.get("ok"))
        self.assertEqual(res_ai.get("data", {}).get("profile_dir"), "Profile 42")

        # Prohibition check across production directories
        forbidden = "adeel" + "qureshi99"
        for folder in ["actions", "core", "skills", "perception", "trading", "config", "wa"]:
            for p in (ROOT / folder).rglob("*"):
                if p.is_file() and p.suffix in (".py", ".js", ".json", ".html", ".md"):
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    self.assertNotIn(forbidden, content.lower(), f"Forbidden string found in {p}")


if __name__ == "__main__":
    unittest.main()

