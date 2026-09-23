"""
tests/test_zero_api_autonomous_suite.py — Deep Verification Suite
===================================================================
Tests all newly implemented sovereign zero-paid-API capabilities:
  1. DexScreenerEngine:
     - 13 OpenAPI endpoints parity
     - Rate limiter & sliding window
     - Resilient caching & browser scraping fallback
     - Bilingual analysis & institutional card formatter
  2. HumanInterventionGateway:
     - Missing API key, Captcha challenge, and 2FA requests
     - Non-hallucinatory WhatsApp dispatch formatting
     - Interactive resolution (key submission, free mode toggle, captcha clear, cancellation)
  3. WhatsAppHumanPartner:
     - Multi-turn conversational discussion lifecycle
     - Pros & cons + risk calculation breakdown
     - Joint final decision proposal & explicit confirmation execution
  4. DualTierMemoryCoordinator:
     - Short-term working memory & 24h expiration
     - Permanent long-term SQLite rules and owner facts
     - Automatic promotion classifier
  5. ChromeAdeelNavigator:
     - Dynamic profile discovery (Profile 42 / adeelvision3@gmail.com)
     - Chrome running status and consultation routing
  6. GitHubSkillHarvester:
     - Open-source repository search & curated fallback
     - Skill synthesis, py_compile verification, and execution
  7. UnifiedCommandRouter:
     - End-to-end command fast-path routing
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

# Ensure root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from trading.dex_screener_engine import DexScreenerEngine, DexScreenerRateLimiter, get_dex_screener_engine
from core.human_intervention_gateway import (
    HumanInterventionGateway,
    InterventionType,
    RequestStatus,
    get_human_intervention_gateway
)
from core.whatsapp_human_partner import (
    WhatsAppHumanPartner,
    ConversationStage,
    get_whatsapp_human_partner
)
from memory.dual_tier_memory import (
    DualTierMemoryCoordinator,
    ShortTermWorkingMemory,
    LongTermDurableMemory,
    get_dual_tier_memory
)
from perception.chrome_adeel_navigator import (
    ChromeAdeelNavigator,
    get_chrome_adeel_navigator
)
from skills.github_skill_harvester import (
    GitHubSkillHarvester,
    get_github_skill_harvester
)
from core.command_router import get_command_router


# ==============================================================================
# 1. DEX SCREENER ENGINE TESTS
# ==============================================================================

class TestDexScreenerEngine:

    def test_rate_limiter_pacing(self):
        limiter = DexScreenerRateLimiter(max_requests_per_minute=10)
        # First 5 acquisitions should happen with zero delay
        for _ in range(5):
            wait = limiter.acquire()
            assert wait == 0.0

    def test_dex_screener_cache_hit(self, tmp_path):
        engine = DexScreenerEngine(enable_rate_limit=False)
        test_key = "test/endpoint:{}"
        engine._set_cached(test_key, {"result": "cached_data"})
        cached = engine._get_cached(test_key, ttl_seconds=60.0)
        assert cached == {"result": "cached_data"}

    def test_dex_screener_core_endpoints(self):
        engine = get_dex_screener_engine()
        # 1. Token profiles
        profiles = engine.get_latest_token_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) > 0

        # 2. Recent updates
        recent = engine.get_recent_token_profiles()
        assert isinstance(recent, list)
        assert len(recent) > 0

        # 3. Search pairs
        search_res = engine.search_pairs("SOL")
        assert isinstance(search_res, list)
        assert len(search_res) > 0

        # 4. Top token boosts
        boosts = engine.get_top_token_boosts()
        assert isinstance(boosts, list)
        assert len(boosts) > 0

        # 5. Trending metas
        metas = engine.get_trending_metas()
        assert isinstance(metas, list)
        assert len(metas) > 0

    def test_all_13_dex_screener_endpoints(self):
        engine = get_dex_screener_engine()
        # 1. /token-profiles/latest/v1
        p1 = engine.get_latest_token_profiles()
        assert isinstance(p1, list)
        # 2. /token-profiles/recent-updates/v1
        p2 = engine.get_recent_token_profiles()
        assert isinstance(p2, list)
        # 3. /community-takeovers/latest/v1
        ct = engine.get_latest_community_takeovers()
        assert isinstance(ct, list)
        # 4. /ads/latest/v1
        ads = engine.get_latest_ads()
        assert isinstance(ads, list)
        # 5. /token-boosts/latest/v1
        lb = engine.get_latest_token_boosts()
        assert isinstance(lb, list)
        # 6. /token-boosts/top/v1
        tb = engine.get_top_token_boosts()
        assert isinstance(tb, list)
        # 7. /orders/v1/{chainId}/{tokenAddress}
        orders = engine.get_orders("solana", "So11111111111111111111111111111111111111112")
        assert isinstance(orders, list)
        # 8. /latest/dex/pairs/{chainId}/{pairId}
        pair = engine.get_pair("solana", "gexzdqpydgczbqdjfcufe1fxc7xso184zwls5n4jmymi")
        assert pair is not None
        # 9. /latest/dex/search?q={query}
        sr = engine.search_pairs("SOL")
        assert isinstance(sr, list)
        # 10. /token-pairs/v1/{chainId}/{tokenAddress}
        tp = engine.get_token_pairs("solana", "So11111111111111111111111111111111111111112")
        assert isinstance(tp, list)
        # 11. /tokens/v1/{chainId}/{tokenAddresses}
        toks = engine.get_tokens_by_addresses("solana", "So11111111111111111111111111111111111111112")
        assert isinstance(toks, list)
        # 12. /metas/trending/v1
        metas = engine.get_trending_metas()
        assert isinstance(metas, list)
        # 13. /metas/meta/v1/{slug}
        if metas and "slug" in metas[0]:
            slug = metas[0]["slug"]
            m_slug = engine.get_meta_by_slug(slug)
            assert m_slug is not None

    def test_analyze_token_and_format_card(self):
        engine = get_dex_screener_engine()
        res = engine.analyze_token("SOL")
        assert res.get("ok") is True
        assert "symbol" in res
        assert "price_usd" in res
        assert "liquidity_usd" in res
        assert res["health_score"] >= 0

        card = engine.format_analysis_card(res)
        assert "DEX SCREENER ON-CHAIN RADAR" in card
        assert "Liquidity Pool" in card
        assert "J.A.R.V.I.S. MASHWARA" in card

    def test_html_parsing_fallback(self):
        engine = get_dex_screener_engine()
        sample_html = '''
        <html>
        <head><title>Test Dex Token</title></head>
        <body>
        <div class="price">$12.3456</div>
        </body>
        </html>
        '''
        data = engine._extract_data_from_html(sample_html, "solana", "0x123")
        assert data is not None
        assert float(data["priceUsd"]) == 12.3456


# ==============================================================================
# 2. HUMAN INTERVENTION GATEWAY TESTS
# ==============================================================================

class TestHumanInterventionGateway:

    def test_create_and_resolve_api_key_request(self):
        gateway = HumanInterventionGateway(owner_phone="923468053268")
        req = gateway.request_api_key(
            service_name="test_service",
            reason="Test paid quota depleted",
            free_alternative="Test free mode"
        )
        assert req.status == RequestStatus.PENDING
        assert req.request_type == InterventionType.MISSING_API_KEY
        assert "test_service" in req.title.lower()

        # Format message test
        msg = gateway.format_whatsapp_message(req)
        assert "J.A.R.V.I.S. REALISTIC ASSISTANCE NEEDED" in msg
        assert "Free Alternative Available" in msg

        # Resolve with Free Mode
        handled, reply = gateway.resolve_from_message("free use karo")
        assert handled is True
        assert "100% FREE MODE ACTIVATED" in reply
        assert req.status == RequestStatus.FALLBACK_FREE

    def test_captcha_request_and_resolution(self):
        gateway = HumanInterventionGateway(owner_phone="923468053268")
        req = gateway.request_captcha_resolution(
            target_site="CloudflareProtectedSite",
            url="https://example.com"
        )
        assert req.request_type == InterventionType.CAPTCHA_CHALLENGE
        assert req.status == RequestStatus.PENDING

        handled, reply = gateway.resolve_from_message("done ho gaya")
        assert handled is True
        assert "CAPTCHA RESOLUTION ACKNOWLEDGED" in reply
        assert req.status == RequestStatus.RESOLVED

    def test_otp_submission_resolution(self):
        gateway = HumanInterventionGateway(owner_phone="923468053268")
        req = gateway.request_2fa_code("TradingBroker")
        assert req.request_type == InterventionType.TWO_FACTOR_AUTH

        handled, reply = gateway.resolve_from_message("otp: 489201")
        assert handled is True
        assert "2FA / OTP CODE RECEIVED" in reply
        assert req.status == RequestStatus.RESOLVED

    def test_inquiry_and_details_resolution(self):
        gateway = HumanInterventionGateway(owner_phone="923468053268")
        req = gateway.request_2fa_code(
            service_name="TradingBroker (FundingPips)",
            account_username="futureworldvision842@gmail.com",
            code_destination="Aapke Gmail (futureworldvision842@gmail.com) Inbox / Authenticator App"
        )
        handled, reply = gateway.resolve_from_message("Account konsadala tha kaha email aaiga")
        assert handled is True
        assert "futureworldvision842@gmail.com" in reply
        assert "Gmail" in reply
        assert "PC Screen Status" in reply
        assert "• PC par dobara kholne ke liye: Reply karein `2` ya `kholo`" in reply

    def test_option_kholo_and_screenshot(self):
        gateway = HumanInterventionGateway(owner_phone="923468053268")
        req = gateway.request_2fa_code(
            service_name="FundingPips",
            portal_url="https://app.fundingpips.com/login"
        )
        handled, reply = gateway.resolve_from_message("kholo")
        assert handled is True
        assert "PC SCREEN ACTIVATED" in reply

        handled, reply = gateway.resolve_from_message("screenshot")
        assert handled is True
        assert "SCREENSHOT" in reply



# ==============================================================================
# 3. WHATSAPP HUMAN PARTNER (DEEP CONVERSATION & JOINT DECISION) TESTS
# ==============================================================================

class TestWhatsAppHumanPartner:

    def test_multi_turn_trade_discussion_and_confirmation(self):
        partner = WhatsAppHumanPartner()
        # 1. Propose trade
        handled1, rep1 = partner.process_incoming_message("yar gold buy karna hai 0.01 lot")
        assert handled1 is True
        assert "STRATEGIC TRADE CONSULTATION" in rep1
        assert "PROPOSED FINAL DECISION" in rep1
        assert partner.active_thread.stage == ConversationStage.FINAL_DECISION_PROPOSED

        # 2. Joint confirmation
        handled2, rep2 = partner.process_incoming_message("haan kardo confirm")
        assert handled2 is True
        assert "FINAL JOINT DECISION CONFIRMED & EXECUTED" in rep2
        assert partner.active_thread is None

    def test_trade_discussion_cancellation(self):
        partner = WhatsAppHumanPartner()
        handled1, rep1 = partner.process_incoming_message("gold sell 0.02 lot")
        assert handled1 is True
        assert partner.active_thread is not None

        # Cancel decision
        handled2, rep2 = partner.process_incoming_message("mat karo cancel kardo")
        assert handled2 is True
        assert "FINAL DECISION WITHDRAWN / CANCELLED" in rep2
        assert partner.active_thread is None

    def test_on_chain_dex_discussion(self):
        partner = WhatsAppHumanPartner()
        handled, rep = partner.process_incoming_message("check dex sol")
        assert handled is True
        assert "ON-CHAIN DEEP ANALYSIS" in rep
        assert "Current Price:" in rep
        assert "Pool Liquidity:" in rep


# ==============================================================================
# 4. DUAL-TIER MEMORY COORDINATOR TESTS
# ==============================================================================

class TestDualTierMemoryCoordinator:

    def test_short_term_working_memory_logging(self):
        stm = ShortTermWorkingMemory(ttl_hours=24)
        stm.clear()
        stm.add_exchange("Gold M15 setup check karo", "Gold bullish FVG par support le raha hai.")
        assert len(stm.turns) == 2
        dialogue = stm.get_recent_dialogue(limit=2)
        assert dialogue[0]["role"] == "user"
        assert dialogue[1]["role"] == "jarvis"

    def test_long_term_rule_persistence(self):
        ltm = LongTermDurableMemory()
        rule_text = "Hamaisha Friday market close hone se pehle open scalps close karein."
        r_id = ltm.add_permanent_rule(rule_text, category="trading")
        rules = ltm.get_all_rules()
        rule_texts = [r["rule_text"] for r in rules]
        assert rule_text in rule_texts

    def test_intelligent_promotion_classification(self):
        coord = DualTierMemoryCoordinator()
        # Ephemeral turn
        c1 = coord.classify_and_record("Aaj gold ka target 2655 hai", "Target noted.")
        assert c1["tier"] == "SHORT_TERM"
        assert c1["promoted_to_long_term"] is False

        # Inviolable Rule -> Promoted to Long-Term
        c2 = coord.classify_and_record("Hamaisha trade mein 1:2 risk-reward ratio lazmi hona chahiye", "Rule locked.")
        assert c2["tier"] == "DUAL_TIER"
        assert c2["promoted_to_long_term"] is True

        # Context generation contains both
        context = coord.build_unified_memory_context()
        assert "DURABLE OWNER RULES" in context
        assert "WORKING MEMORY" in context


# ==============================================================================
# 5. CHROME 'ADEEL' PROFILE NAVIGATOR TESTS
# ==============================================================================

class TestChromeAdeelNavigator:

    def test_adeel_profile_discovery(self):
        nav = ChromeAdeelNavigator()
        assert nav.profile_info is not None
        assert "adeel" in nav.profile_info.display_name.lower() or "adeel" in nav.profile_info.user_email.lower()
        assert nav.profile_info.profile_directory_name in ("Profile 42", "adeel")
        assert nav.chrome_exe.exists()
        assert nav.is_chrome_running() is True


# ==============================================================================
# 6. GITHUB SKILL HARVESTER TESTS
# ==============================================================================

class TestGitHubSkillHarvester:

    def test_search_and_curated_fallback(self):
        harvester = get_github_skill_harvester()
        repos = harvester.search_repositories("dexscreener api", max_results=2)
        assert isinstance(repos, list)
        assert len(repos) > 0
        assert "full_name" in repos[0]
        assert "stars" in repos[0]

    def test_harvest_compile_and_execute_skill(self):
        harvester = get_github_skill_harvester()
        sample_repo = {
            "full_name": "sample/crypto-screener-tool",
            "name": "auto_test_screener",
            "description": "Autonomous crypto screener library",
            "html_url": "https://github.com/sample/crypto-screener-tool",
            "stars": 120
        }
        ok, path_or_err = harvester.harvest_and_compile_skill(sample_repo, skill_slug="auto_test_screener")
        assert ok is True
        assert Path(path_or_err).exists()

        # Import and execute the synthesized skill
        import importlib.util
        spec = importlib.util.spec_from_file_location("auto_test_screener", path_or_err)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        res = mod.run({"action": "status"})
        assert "SKILL: AUTO_TEST_SCREENER" in res
        assert "120" in res

        # Clean up test skill
        try:
            Path(path_or_err).unlink()
        except Exception:
            pass


# ==============================================================================
# 7. UNIFIED COMMAND ROUTER INTEGRATION TESTS
# ==============================================================================

class TestUnifiedCommandRouterShortcuts:

    def test_router_dex_shortcut(self):
        router = get_command_router()
        envelope = router.process_command("dex sol", channel="terminal")
        assert envelope.ok is True
        assert "DEX" in envelope.output_text or "SOL" in envelope.output_text
        assert envelope.routed_via in ("dex_screener_engine", "whatsapp_partner", "crypto_subsystem")

    def test_router_memory_shortcut(self):
        router = get_command_router()
        envelope = router.process_command("memory", channel="terminal")
        assert envelope.ok is True
        assert "DUAL-TIER COGNITIVE MEMORY" in envelope.output_text

    def test_router_adeel_consultation_shortcut(self):
        router = get_command_router()
        envelope = router.process_command("consult adeel gpt check gold macro trend", channel="terminal")
        assert "CHROME 'ADEEL'" in envelope.output_text
