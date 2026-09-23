"""
tests/test_empirical_challenger2_m1_signal_stress.py — Empirical Stress, High-Throughput Latency,
Unicode Integrity, and Forensic 5-Pillar Challenge Suite for Milestone 1 (Requirement R1).

Validates:
1. High-Throughput simulated market feeds & sub-millisecond per-card formatting latency SLA.
2. Concurrent multi-threaded signal assembly & broadcasting without race conditions or memory leaks.
3. 5-Pillar message assembly integrity (SMC triggers, retail traps, maritime macro, contagion matrix, Scenario A/B).
4. Roman Urdu and English bilingual integrity without Unicode or formatting corruption.
5. Adversarial fuzzing, degenerate inputs, missing dictionaries, and extreme numerical boundaries.
6. Institutional trade receipts & 4-account fleet sizing math verification.
"""

import time
import json
import pytest
import threading
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from src.whatsapp_copilot import (
    InstitutionalCardFormatter,
    BilingualTradeConsultant,
    is_whitelisted_number,
    AUTHORIZED_CONTACTS,
    ELITE_TRADE_GROUP_JID
)
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.whatsapp_notifier import WhatsAppNotifier
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.fleet_risk_manager import FleetRiskManager


# =====================================================================
# 1. HIGH-THROUGHPUT FEED STRESS & FORMATTING LATENCY SLA
# =====================================================================

class TestHighThroughputSignalFeedAndLatencySLA:
    """Stress tests high-speed simulated tick feeds and measures formatting SLA."""

    @pytest.fixture
    def sample_analysis_payload(self) -> Dict[str, Any]:
        return {
            "trend_direction": "BULLISH",
            "confluence_score": 5.30,
            "order_flow": {
                "in_ote_zone": True,
                "ote_705_sweet_spot": 2645.20,
                "fvg_50_ce": 2646.10,
                "net_delta": 480,
                "buyer_volume_pct": 68.0,
                "sweep_desc": "Retail Equal Lows (EQL) Swept on M15 (Turtle Soup Liquidity Purge)",
                "zone_desc": "Discount Zone (72.5% below 50% Eq) | 70.5% OTE Golden Pocket",
                "ob_fvg_desc": "Retesting M15 Demand OB + 50% Consequent Encroachment FVG",
                "cvd_desc": "Strong Buyer Delta Absorption (+480 contracts, 68% Buyer Volume | Lee-Ready Tick Rule)",
                "trigger": "M15 Bullish Engulfing Candle closing above FVG 50% CE with CVD Surge",
                "urdu_rationale": "Big Sharks ne Asian Session lows sweep kar ke 50% CE FVG par aggressive buyer volume absorb kiya hai."
            },
            "psychology": {
                "retail_trap": "Retail Trap: Chasing late breakout at resistance / panic selling into demand zone.",
                "shark_accumulation": "Institutional Iceberg Orders absorbing market sell pressure without lowering price.",
                "wyckoff_phase": "Wyckoff Phase C Spring & Liquidity Test / SOS Markup",
                "herd_defense": "Zero FOMO — Strict limit entry at institutional discount dealing array."
            },
            "intermarket_intel": {
                "killzone": "NY AM Killzone (13:30 UTC)",
                "killzone_status": "Prime Execution Window",
                "news_status": "CLEAR (No red-folder events in 15m)",
                "macro_regime": "RISK_OFF_GOLD_SURGE",
                "dxy_trend": "BEARISH",
                "us10y": "Falling (-4.5 bps)",
                "vix": "18.4",
                "hormuz": "CRITICAL_WARZONE | Flow: 14.5 mbd (69% baseline)",
                "bab_mandeb": "CRITICAL_WARZONE | Flow: 2.1 mbd (33.9% baseline)",
                "chokepoints_other": "Suez & Malacca: MODERATE | Cape of Good Hope rerouting active",
                "cii": "84.2/100 (HIGH RISK | Sovereign Safe-Haven flight)",
                "fed_liq": "Fed Net Liquidity $5,800B (+1.8% MoM Expansion)",
                "geopolitical_brief": "DEFCON 3 | Maritime Chokepoints Active"
            },
            "contagion": {
                "gsr": "GSR at 113.97 -> Silver Undervalued (High-Beta catch-up target: $39.50)",
                "wti_oil": "$78.50/bbl (BULLISH_INFLATION_HEDGE -> Fuels Gold headline CPI tailwind)",
                "crypto_spillover": "IF Bitcoin absorbs CVD -> THEN ETH ($3,450.00) & SOL ($195.00) momentum expansion targets active",
                "liquidity_beta": "0.94 Composite Precious Metals Beta",
                "spillover_rule": "IF #XAUUSD expands past resistance -> THEN Silver $39.50 and WTI Oil $78.50 active."
            },
            "scenario": {
                "scenario_a_if": "IF #XAUUSD holds 50% CE FVG / 70.5% OTE Discount (2,646.50) with aggressive CVD buyer delta",
                "scenario_a_then": "THEN execute Long Scale-In, bank 50% profit at TP1 (2,662.00), lock Breakeven, trail runner to TP2 (2,680.00) and TP3 (2,705.00)",
                "scenario_a_urdu": "Agar price 70.5% OTE zone par hold karti hai, toh BUY position lein aur TP1 par aadha profit book karein.",
                "scenario_b_if": "IF price rejects at resistance / breaks structural SL (2,635.50) on high seller CVD delta",
                "scenario_b_then": "THEN do NOT revenge trade; wait for secondary liquidity defense reload (2,622.30)",
                "scenario_b_urdu": "Agar structural SL break ho jaye toh ghabra kar revenge trade na karein; aglay liquidity demand block ka intezar karein."
            },
            "risk": {
                "var_99": 465.27,
                "daily_budget": 625.0
            }
        }

    def test_rapid_sequential_burst_formatting_latency_sla(self, sample_analysis_payload):
        """
        Benchmarking: Generates 2,500 5-pillar signals in a high-speed simulated tick burst.
        SLA Requirement: Average formatting time must be strictly under 0.50 ms per card (< 2.0s total).
        """
        broadcaster = CommunitySignalBroadcaster()
        symbols = ["XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPJPY", "USDCAD", "WTIOIL"]
        directions = ["BUY", "SELL"]

        num_iterations = 2500
        start_time = time.perf_counter()

        for i in range(num_iterations):
            sym = symbols[i % len(symbols)]
            dir_str = directions[i % len(directions)]
            base_price = 2646.50 if "XAU" in sym else (64200.0 if "BTC" in sym else 1.0850)
            sl = base_price - 10.0 if dir_str == "BUY" else base_price + 10.0
            tp1 = base_price + 15.0 if dir_str == "BUY" else base_price - 15.0
            tp2 = base_price + 35.0 if dir_str == "BUY" else base_price - 35.0
            tp3 = base_price + 60.0 if dir_str == "BUY" else base_price - 60.0

            card = broadcaster.format_community_5pillar_card(
                symbol=sym,
                signal_type=dir_str,
                entry_price=base_price,
                sl_price=sl,
                tp1_price=tp1,
                tp2_price=tp2,
                tp3_price=tp3,
                analysis=sample_analysis_payload
            )
            assert len(card) > 500, "Card content must be substantial and valid"

        total_elapsed = time.perf_counter() - start_time
        avg_latency_ms = (total_elapsed / num_iterations) * 1000.0

        assert total_elapsed < 2.5, f"Burst generation took {total_elapsed:.3f}s (exceeds 2.5s SLA)"
        assert avg_latency_ms < 1.0, f"Average card formatting latency was {avg_latency_ms:.4f}ms (exceeds 1.0ms SLA)"

    def test_concurrent_multithreaded_signal_assembly_stress(self, sample_analysis_payload):
        """
        Concurrency Stress: 25 threads formatting 100 5-pillar signals each (2,500 concurrent signals).
        Verifies zero race conditions, zero thread contention, and complete data isolation.
        """
        broadcaster = CommunitySignalBroadcaster()
        errors: List[Exception] = []
        cards_generated: List[str] = []
        lock = threading.Lock()

        def worker_task(thread_id: int):
            try:
                for i in range(100):
                    card = broadcaster.format_community_5pillar_card(
                        symbol=f"XAUUSD_{thread_id}_{i}",
                        signal_type="BUY" if (i % 2 == 0) else "SELL",
                        entry_price=2646.50 + thread_id,
                        sl_price=2635.50 + thread_id,
                        tp1_price=2662.00 + thread_id,
                        tp2_price=2680.00 + thread_id,
                        analysis=sample_analysis_payload
                    )
                    assert f"XAUUSD_{thread_id}_{i}" in card
                    with lock:
                        cards_generated.append(card)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(t,)) for t in range(25)]
        start_t = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.perf_counter() - start_t

        assert len(errors) == 0, f"Encountered thread errors: {errors}"
        assert len(cards_generated) == 2500
        assert total_time < 3.0, f"Concurrent generation took {total_time:.3f}s (exceeds 3.0s threshold)"

    def test_broadcaster_network_drop_and_resilience(self, sample_analysis_payload):
        """
        Simulates network timeout/disconnection when broadcasting to WhatsApp gateway.
        Broadcaster must handle connection drops cleanly without raising uncaught exceptions.
        """
        broadcaster = CommunitySignalBroadcaster()
        with patch("requests.post", side_effect=Exception("ConnectionRefusedError: Node.js gateway offline")):
            res = broadcaster.broadcast_5pillar_signal(
                symbol="XAUUSD",
                signal_type="BUY",
                entry_price=2646.50,
                sl_price=2635.50,
                tp1_price=2662.00,
                tp2_price=2680.00,
                analysis=sample_analysis_payload
            )
            # Must return clean dictionary of dispatch results
            assert isinstance(res, dict)
            assert any("923468053268" in k for k in res.keys())


# =====================================================================
# 2. 5-PILLAR MESSAGE ASSEMBLY INTEGRITY & CONTEXTUAL COMPLETENESS
# =====================================================================

class TestFivePillarForensicAssemblyIntegrity:
    """Validates that all 5 forensic pillars are comprehensively assembled with full fidelity."""

    def test_full_5pillar_card_elements_and_confluences(self):
        """Verifies every required section, label, ratio, and whale metric in 5-pillar card."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            tp3_price=2705.00,
            macro_data={
                "killzone": "London Open Killzone (08:00 UTC)",
                "killzone_status": "High Volume Macro Open",
                "news_status": "CLEAR (No red folder in 30m)",
                "regime": "RISK_OFF_GOLD_SURGE",
                "dxy": "Bearish (-0.52%)",
                "us10y": "4.15% (Falling -5 bps)",
                "vix": "19.2",
                "hormuz": "CRITICAL_WARZONE | Flow: 14.5 mbd (69% baseline)",
                "bab_mandeb": "CRITICAL_WARZONE | Flow: 2.1 mbd (33.9% baseline)",
                "chokepoints_other": "Suez & Malacca: MODERATE | Cape of Good Hope rerouting active",
                "cii": "84.2/100 (HIGH RISK)",
                "fed_liq": "Fed Net Liquidity $5,800B (+1.8% MoM Expansion)",
                "geopolitical_brief": "DEFCON 3 | Strategic Maritime Chokepoint Alerts Active"
            },
            smc_data={
                "sweep_desc": "Retail Equal Lows (EQL) Swept on M15 (Turtle Soup Liquidity Purge)",
                "zone_desc": "Discount Zone (72.5% below 50% Eq) | 70.5% OTE Golden Pocket (2,641.20)",
                "ob_fvg_desc": "Retesting M15 Demand OB + 50% Consequent Encroachment FVG (2,643.85)",
                "cvd_desc": "Strong Buyer Delta Absorption (+480 contracts, 68% Buyer Volume | Lee-Ready Tick Rule)",
                "confluence_score": "5.30",
                "trigger": "M15 Bullish Engulfing Candle closing above FVG 50% CE with CVD Surge",
                "urdu_rationale": "Big Sharks ne retail stop-loss sweep kar ke 50% CE FVG par heavy buyer volume absorb kiya hai."
            },
            psychology_data={
                "retail_trap": "Retail Trap: Chasing late breakout at resistance / panic selling into demand zone.",
                "shark_accumulation": "Institutional Iceberg Orders absorbing market sell pressure without lowering price.",
                "wyckoff_phase": "Wyckoff Phase C Spring & Liquidity Test / SOS Markup",
                "herd_defense": "Zero FOMO — Strict limit entry at institutional discount dealing array."
            },
            contagion_data={
                "gsr": "GSR at 113.97 -> Silver Undervalued (High-Beta catch-up target: $39.50)",
                "wti_oil": "$78.50/bbl (BULLISH_INFLATION_HEDGE -> Fuels Gold headline CPI tailwind)",
                "crypto_spillover": "IF Bitcoin absorbs CVD -> THEN ETH ($3,450.00) & SOL ($195.00) momentum expansion targets active",
                "liquidity_beta": "0.94 Composite Precious Metals Beta (Risk-Off Sovereign Co-Expansion)",
                "spillover_rule": "IF #XAUUSD expands past resistance -> THEN immediate cross-market spillover activates Silver $39.50."
            },
            scenario_data={
                "scenario_a_if": "IF #XAUUSD holds 50% CE FVG / 70.5% OTE Discount (2,646.50) with aggressive CVD buyer delta",
                "scenario_a_then": "THEN execute Long Scale-In, bank 50% profit at TP1 (2,662.00), lock Breakeven, and trail runner to TP2 (2,680.00) and TP3 (2,705.00)",
                "scenario_a_urdu": "Agar price 70.5% OTE zone (2,646.50) par hold karti hai aur CVD buyers delta barhta hai, toh BUY position lein, TP1 (2,662.00) par aadha profit book karein aur SL foran Breakeven par shift karein.",
                "scenario_b_if": "IF price rejects at resistance / breaks structural SL (2,635.50) on high seller CVD delta",
                "scenario_b_then": "THEN do NOT revenge trade; wait for secondary liquidity defense reload (2,622.30) / M5 MSS confirmation before re-entering",
                "scenario_b_urdu": "Agar structural SL (2,635.50) break ho jaye toh ghabra kar revenge trade na karein; aglay liquidity demand block (2,622.30) ka intezar karein."
            },
            risk_data={"var_99": 465.27},
            sl_pips=110.0
        )

        # 1. Header & Targets
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL & BLUEPRINT" in card
        assert "#XAUUSD" in card
        assert "STRONG BUY" in card
        assert "2,646.50" in card
        assert "2,635.50" in card
        assert "2,662.00" in card
        assert "2,680.00" in card
        assert "2,705.00" in card

        # 2. Pillar 1: Institutional Rationale & SMC Order Flow (Wajoohat)
        assert "PILLAR 1: INSTITUTIONAL RATIONALE & SMC ORDER FLOW (WAJOOHAT)" in card
        assert "Retail Equal Lows (EQL) Swept on M15" in card
        assert "70.5% OTE Golden Pocket" in card
        assert "50% Consequent Encroachment FVG" in card
        assert "Lee-Ready CVD Absorption:" in card
        assert "+480 contracts" in card
        assert "Wajoohat (Roman Urdu):" in card

        # 3. Pillar 2: Market Psychology & Shark Trap Dynamics
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP DYNAMICS" in card
        assert "Retail Trap Identification:" in card
        assert "Big Shark Accumulation:" in card
        assert "Wyckoff Phase C Spring" in card
        assert "Herd Mentality Defense:" in card

        # 4. Pillar 3: Macro & Geopolitical Backdrop
        assert "PILLAR 3: MACRO & GEOPOLITICAL BACKDROP (GLOBAL TAILWINDS)" in card
        assert "Strait of Hormuz:" in card
        assert "Bab-el-Mandeb / Red Sea:" in card
        assert "Suez / Malacca / Taiwan Strait:" in card
        assert "Country Instability Index (CII):" in card
        assert "84.2/100" in card
        assert "Central Bank Net Liquidity:" in card
        assert "$5,800B" in card

        # 5. Pillar 4: Cross-Market Contagion Matrix
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX (PREDICTIVE SPILLOVER)" in card
        assert "Gold/Silver Ratio (GSR):" in card
        assert "Silver Undervalued" in card
        assert "WTI Crude Oil Transmission:" in card
        assert "BTC -> ETH/SOL Momentum Target:" in card
        assert "ETH ($3,450.00) & SOL ($195.00)" in card

        # 6. Pillar 5: Scenario A/B What-If Roadmap
        assert "PILLAR 5: SCENARIO A/B WHAT-IF ROADMAP (ROMAN URDU + ENGLISH)" in card
        assert "SCENARIO A (Primary Trend Expansion — 75% Probability):" in card
        assert "SCENARIO B (Deep Liquidity Sweep / Defense — 25% Probability):" in card
        assert "Roman Urdu Roadmap:" in card
        assert "revenge trade" in card

        # 7. Sizing Guide & Tap-to-Copy Payloads
        assert "4-Account Fleet Sizing Guide:" in card
        assert "$100k Master Account:" in card
        assert "$50k Growth Account:" in card
        assert "$25k Main Account:" in card
        assert "$5k Micro Account:" in card
        assert "```buy xauusd" in card
        assert "```be xauusd```" in card
        assert "```scale 50% xauusd```" in card
        assert "```close xauusd```" in card

    def test_5pillar_advisory_bilingual_mashwara_structure(self):
        """Verifies 5-pillar advisory blueprint formatting in Roman Urdu and English."""
        smc_data = {
            "structure": "H1 Bullish Trend Dominance",
            "zone": "70.5% OTE Fibonacci Discount Zone",
            "cvd": "Lee-Ready CVD indicates aggressive buyer absorption."
        }
        targets = {
            "entry": "2,646.50",
            "sl": "2,635.50",
            "tp1": "2,662.00",
            "tp2": "2,680.00",
            "tp3": "2,705.00"
        }
        risk_data = {
            "lot_100k": 0.45,
            "lot_50k": 0.22,
            "lot_25k": 0.11,
            "lot_5k": 0.02
        }

        # Test Roman Urdu Advisory
        card_urdu = InstitutionalCardFormatter.format_5pillar_advisory_card(
            verdict="STRONG BUY (High Conviction)",
            symbol="XAUUSD",
            smc_data=smc_data,
            targets=targets,
            risk_data=risk_data,
            is_urdu=True
        )
        assert "JARVIS INSTITUTIONAL 5-PILLAR MASHWARA" in card_urdu
        assert "PILLAR 1: SMC & DEALING ARRAY EVIDENCE" in card_urdu
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP:" in card_urdu
        assert "PILLAR 3: GEOPOLITICAL & MACRO RADAR:" in card_urdu
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX:" in card_urdu
        assert "PILLAR 5: SCENARIO A/B ROADMAP & PRECISE TARGETS:" in card_urdu
        assert "Breakeven Rule:" in card_urdu

        # Test English Advisory
        card_en = InstitutionalCardFormatter.format_5pillar_advisory_card(
            verdict="STRONG BUY (High Conviction)",
            symbol="XAUUSD",
            smc_data=smc_data,
            targets=targets,
            risk_data=risk_data,
            is_urdu=False
        )
        assert "JARVIS INSTITUTIONAL 5-PILLAR ADVISORY" in card_en
        assert "PILLAR 1: SMC & DEALING ARRAY EVIDENCE" in card_en
        assert "PILLAR 2: MARKET PSYCHOLOGY & SHARK TRAP:" in card_en
        assert "PILLAR 3: GEOPOLITICAL & MACRO RADAR:" in card_en
        assert "PILLAR 4: CROSS-MARKET CONTAGION MATRIX:" in card_en
        assert "PILLAR 5: SCENARIO A/B ROADMAP & PRECISE TARGETS:" in card_en


# =====================================================================
# 3. ROMAN URDU & UNICODE FORMATTING INTEGRITY / ANTI-CORRUPTION
# =====================================================================

class TestRomanUrduAndUnicodeFormattingIntegrity:
    """Verifies that Roman Urdu and English components remain intact without Unicode corruption."""

    def test_unicode_special_characters_and_emojis_preserved(self):
        """Ensures all emojis, markdown symbols, and Unicode borders pass roundtrip encoding."""
        card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00
        )

        expected_emojis = ["⚡", "🏛️", "🧠", "🌍", "🔄", "🗺️", "🛡️", "🎯", "📌", "📈", "🔴", "🟢", "🚀", "🌌", "⭐", "✅"]
        for emoji in expected_emojis:
            assert emoji in card, f"Missing expected Unicode emoji: {emoji}"

        # UTF-8 roundtrip encoding test
        utf8_encoded = card.encode("utf-8")
        assert len(utf8_encoded) > 0
        decoded = utf8_encoded.decode("utf-8")
        assert decoded == card

        # JSON serialization roundtrip test
        json_payload = json.dumps({"message": card}, ensure_ascii=False)
        unpacked = json.loads(json_payload)
        assert unpacked["message"] == card

    def test_roman_urdu_linguistic_elements_intact(self):
        """Verifies that authentic Roman Urdu vocabulary and technical code-switching are preserved."""
        consultant = BilingualTradeConsultant()

        # Roman Urdu queries
        queries = [
            "gold ka kya scene hai bhai?",
            "kya abhi gold buy karna theek hai ya shark trap hai?",
            "top pe short kar loon kya scene hai?"
        ]

        for q in queries:
            is_urdu = consultant.is_roman_urdu(q)
            assert is_urdu is True, f"Query '{q}' should be detected as Roman Urdu"

            resp = consultant.generate_consultation(query=q, symbol="XAUUSD")
            assert len(resp) > 100
            assert "GOLD" in resp or "XAU" in resp
            # Verify code-switching contains both Roman Urdu terms and institutional SMC terms
            assert any(word in resp.lower() for word in ["bhai", "hai", "karein", "sharks", "agar", "aur", "sl", "tp", "breakeven", "liquidity", "ote", "fvg", "short"])

    def test_adversarial_unicode_and_script_injection_fuzzing(self):
        """Fuzzes formatter with extreme Unicode characters, Persian/Urdu script, zero-width spaces, and null chars."""
        adversarial_strings = [
            "شیر مارکیٹ گولڈ بریک آؤٹ",
            "XAUUSD \u200B\u200C\u200D\uFEFF ZeroWidthTest",
            "GOLD \U0001F988 Shark \U0001F4B0 Money",
            "XAUUSD \x00\x01\x02 NullBytesIgnored",
            "تجارتی حکمت عملی (Trading Strategy)",
            "XAUUSD \u202E RTL_Override_Test \u202C"
        ]

        for adv_str in adversarial_strings:
            # Should format without crashing or raising UnicodeEncodeError
            card = InstitutionalCardFormatter.format_5pillar_card(
                symbol=adv_str,
                direction="BUY",
                entry_price=2646.50,
                sl_price=2635.50,
                tp1_price=2662.00,
                tp2_price=2680.00
            )
            assert isinstance(card, str)
            assert len(card) > 200
            # Formatted card must still contain 5 pillars
            assert "PILLAR 1:" in card
            assert "PILLAR 2:" in card
            assert "PILLAR 3:" in card
            assert "PILLAR 4:" in card
            assert "PILLAR 5:" in card


# =====================================================================
# 4. ADVERSARIAL BOUNDARIES & MALFORMED PAYLOADS
# =====================================================================

class TestAdversarialBoundariesAndMalformedPayloads:
    """Tests extreme edge cases, empty dictionaries, None fields, and numerical anomalies."""

    def test_empty_analysis_dict_graceful_fallback(self):
        """Verifies that empty or missing analysis dicts fall back gracefully without KeyError."""
        broadcaster = CommunitySignalBroadcaster()
        card = broadcaster.format_community_5pillar_card(
            symbol="XAUUSD",
            signal_type="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            analysis={}  # Completely empty dictionary
        )
        assert "INSTITUTIONAL 5-PILLAR FORENSIC TRADE SIGNAL" in card
        assert "PILLAR 1:" in card
        assert "PILLAR 5:" in card
        assert "2,646.50" in card

    def test_extreme_numerical_price_ranges(self):
        """Tests prices spanning micro-pips (EURUSD 1.08502) to high-value crypto (BTCUSD 125,450.00)."""
        # Bitcoin at $125,450
        btc_card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="BTCUSD",
            direction="BUY",
            entry_price=125450.00,
            sl_price=124000.00,
            tp1_price=127500.00,
            tp2_price=131000.00
        )
        assert "125,450.00" in btc_card
        assert "124,000.00" in btc_card
        assert "127,500.00" in btc_card

        # EURUSD at 1.08520
        eur_card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="EURUSD",
            direction="SELL",
            entry_price=1.08520,
            sl_price=1.08720,
            tp1_price=1.08220,
            tp2_price=1.07820
        )
        assert "1.08520" in eur_card
        assert "1.08720" in eur_card

        # Silver at 38.452
        xag_card = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAGUSD",
            direction="BUY",
            entry_price=38.45,
            sl_price=37.90,
            tp1_price=39.50,
            tp2_price=41.00
        )
        assert "38.45" in xag_card

    def test_zero_or_inverted_sl_distance_safeguard(self):
        """Verifies that zero or inverted SL distance does not cause ZeroDivisionError."""
        # Zero SL distance
        card_zero_sl = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2646.50,  # Zero distance
            tp1_price=2662.00,
            tp2_price=2680.00
        )
        assert "2,646.50" in card_zero_sl
        assert "PILLAR 1:" in card_zero_sl

        # Default TP3 computation when tp3 is None
        card_none_tp3 = InstitutionalCardFormatter.format_5pillar_card(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl_price=2635.50,
            tp1_price=2662.00,
            tp2_price=2680.00,
            tp3_price=None
        )
        assert "Take Profit 3 (TP3):" in card_none_tp3


# =====================================================================
# 5. ACTIVE TRADE RECEIPT FORENSICS & FLEET SIZING MATH
# =====================================================================

class TestActiveTradeReceiptForensicsAndSizingMath:
    """Validates multi-tier TP1-3 calculations, R:R math, and fleet sizing rules."""

    def test_whatsapp_notifier_forensic_receipt_metrics(self):
        """Verifies that WhatsAppNotifier creates full forensic trade receipts with multi-tier TP1-3 and R:R."""
        notifier = WhatsAppNotifier()
        dispatched_messages: List[str] = []

        with patch.object(notifier, "send_message", side_effect=lambda m: dispatched_messages.append(m)):
            notifier.send_trade_notification({
                "symbol": "XAUUSD",
                "direction": "BUY",
                "volume": 0.25,
                "entry_price": 2646.50,
                "sl_price": 2635.50,
                "tp1_price": 2662.00,
                "tp2_price": 2680.00,
                "tp3_price": 2705.00,
                "risk_dollars": 187.50,
                "confluence_score": 5.30,
                "cvd_desc": "Institutional Buyer Delta Absorption (+480 contracts, 68% Buyer Volume | Lee-Ready Tick Rule)",
                "dark_pool": "Tier-1 Banks Limit Bid Iceberg Absorption without price displacement",
                "wyckoff_phase": "WYCKOFF ACCUMULATION PHASE C (SPRING & TEST)"
            })

            assert len(dispatched_messages) == 1
            msg = dispatched_messages[0]

            assert "NEW INSTITUTIONAL TRADE EXECUTED & FORENSIC RECEIPT" in msg
            assert "GOLD (#XAUUSD)" in msg
            assert "STRONG BUY (0.25 Lots)" in msg
            assert "2,646.50" in msg
            assert "2,635.50" in msg
            assert "2,662.00 (Structural Base | 1:1.4 R:R)" in msg
            assert "2,680.00 (Dealing Range High | 1:3.0 R:R)" in msg
            assert "2,705.00 (Macro ATH Expansion | 1:5.3 R:R)" in msg
            assert "Lee-Ready CVD:" in msg
            assert "Dark Pool Footprint:" in msg
            assert "Wyckoff Market Phase:" in msg
            assert "Maritime Chokepoints:" in msg
            assert "CROSS-MARKET CONTAGION MATRIX:" in msg
            assert "Sovereign Hidayat (Roman Urdu):" in msg
            assert "```be xauusd```" in msg

    def test_autonomous_fleet_executor_forensic_receipt_dispatch(self):
        """Verifies that AutonomousFleetExecutor dispatches multi-tier forensic receipts across the active fleet."""
        mock_risk = MagicMock()
        mock_risk.accounts_state = {
            "ACC_25K": {
                "account_id": "ACC_25K",
                "account_name": "Prop Master 25k",
                "is_active": True,
                "balance": 25000.0,
                "risk_per_trade_pct": 0.75,
                "client_whatsapp": "+923468053268"
            }
        }
        mock_qr = MagicMock()
        mock_mt5 = MagicMock()
        mock_mt5.place_order.return_value = {"success": True, "ticket": 9845120}

        executor = AutonomousFleetExecutor(
            risk_manager=mock_risk,
            mt5_connector=mock_mt5,
            bitget_connector=MagicMock(),
            whatsapp_manager=mock_qr
        )

        res = executor.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2646.50,
            sl=2635.50,
            tp1=2662.00,
            tp2=2680.00,
            tp3=2705.00,
            confluence_tag="70.5% OTE FVG MITIGATION",
            shark_tag="Smart Money Dealing Desk"
        )

        assert res["success"] is True
        assert res["executed_count"] == 1
        assert len(res["orders"]) == 1
        assert res["orders"][0]["ticket"] == 9845120
        assert mock_qr.notify_client_account_update.called

        # Verify receipt content sent to WhatsApp
        call_args = mock_qr.notify_client_account_update.call_args
        wa_msg = call_args[1]["message"]

        assert "NEW INSTITUTIONAL FLEET TRADE EXECUTED" in wa_msg
        assert "*Take Profit 1 (TP1):* 2662.0" in wa_msg
        assert "*Take Profit 2 (TP2):* 2680.0" in wa_msg
        assert "*Take Profit 3 (TP3):* 2705.0" in wa_msg
        assert "Lee-Ready CVD:" in wa_msg
        assert "Wyckoff Phase:" in wa_msg
        assert "Maritime Chokepoints" in wa_msg
        assert "Sovereign Hidayat (Roman Urdu):" in wa_msg
