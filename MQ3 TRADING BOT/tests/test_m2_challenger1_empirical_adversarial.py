"""
tests/test_m2_challenger1_empirical_adversarial.py
Adversarial and Empirical Stress Test Suite for Milestone M2.
Empirically stress-tests:
  1. OpenHuman Cognitive Engine (Loss streaks, SQLite WAL corruption, tick bursts, empty DB, NoneType inputs)
  2. Historical 50-Year Regime Library (All-zero, 100-sigma, NaN/Inf, Cosine edge cases, Variable dimensions)
  3. Free AI Conversational Core (Roman Urdu slang/typos, -50% Flash Crashes, Funding Pips 25k rules)
"""

import os
import math
import json
import sqlite3
import tempfile
import threading
import numpy as np
import pytest
from typing import Dict, Any, List

from src.openhuman_cognitive_engine import (
    OpenHumanCognitiveEngine,
    MemoryTreeManager,
    SubconsciousReflectionEngine,
    SuperContextBuilder
)
from src.historical_50yr_regime_library import Historical50YrRegimeLibrary
from src.free_ai_intelligence_core import FreeAIIntelligenceCore


# ===========================================================================
# 1. OpenHuman Cognitive Engine Adversarial Stress Tests
# ===========================================================================

class TestOpenHumanCognitiveEngineAdversarial:
    """Stress tests for OpenHuman cognitive state machine, tilt shield, SQLite WAL, and concurrency."""

    @pytest.fixture
    def temp_env(self):
        temp_dir = tempfile.mkdtemp(prefix="openhuman_adv_")
        db_path = os.path.join(temp_dir, "test_cognitive.db")
        tree_path = os.path.join(temp_dir, "test_tree.json")
        yield db_path, tree_path
        # Clean up
        for f in [db_path, f"{db_path}-wal", f"{db_path}-shm", tree_path]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

    def test_sudden_multi_trade_loss_streaks_tilt_lock(self, temp_env):
        """Test tilt lock activation under sudden 2-loss, 3-loss, and 10-loss streaks."""
        db_path, tree_path = temp_env
        engine = OpenHumanCognitiveEngine(
            db_path=db_path,
            memory_tree=MemoryTreeManager(tree_path=tree_path)
        )

        # 1. Simulate 2 consecutive losses -> Enforces pause_trading=True and risk_multiplier=0.25
        loss_streak_2 = [
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -85.0, "session": "LONDON_OPEN"},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -120.0, "session": "LONDON_OPEN"}
        ]
        reflection_2 = engine.reflect(trade_history=loss_streak_2)
        assert reflection_2["directives"]["pause_trading"] is True
        assert reflection_2["directives"]["risk_multiplier"] == 0.25
        tilt_insights_2 = [i for i in reflection_2["insights"] if i.get("category") == "TILT"]
        assert len(tilt_insights_2) >= 1
        assert tilt_insights_2[0]["severity"] == "CRITICAL"
        assert tilt_insights_2[0]["action"] == "MANDATORY_COOLING_PAUSE"

        # 2. Simulate 10 consecutive catastrophic losses across multiple symbols
        loss_streak_10 = [
            {"symbol": "EURUSD", "outcome": "LOSS", "pnl": -50.0, "session": "LONDON_OPEN"},
            {"symbol": "GBPUSD", "outcome": "LOSS", "pnl": -60.0, "session": "LONDON_OPEN"},
            {"symbol": "USDJPY", "outcome": "LOSS", "pnl": -45.0, "session": "LONDON_OPEN"},
            {"symbol": "BTCUSD", "outcome": "LOSS", "pnl": -150.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "ETHUSD", "outcome": "LOSS", "pnl": -80.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "SOLUSD", "outcome": "LOSS", "pnl": -40.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -180.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -110.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -125.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -140.0, "session": "NEW_YORK_OPEN"}
        ]
        reflection_10 = engine.reflect(trade_history=loss_streak_10)
        assert reflection_10["directives"]["pause_trading"] is True
        assert reflection_10["directives"]["risk_multiplier"] <= 0.25
        # Cold streak warning should also be present
        cold_streak_insights = [i for i in reflection_10["insights"] if i.get("category") == "STREAK"]
        assert len(cold_streak_insights) >= 1
        # Symbol bleed for XAUUSD should be detected (-555.0 PnL)
        bleed_insights = [i for i in reflection_10["insights"] if i.get("category") == "SYMBOL_BLEED"]
        assert len(bleed_insights) >= 1

        # 3. Verify that adding winning trades clears the tilt lock (last 3 trades no longer 2+ losses)
        recovered_history = loss_streak_10 + [
            {"symbol": "XAUUSD", "outcome": "WIN", "pnl": 250.0, "session": "NEW_YORK_OPEN"},
            {"symbol": "XAUUSD", "outcome": "WIN", "pnl": 180.0, "session": "NEW_YORK_OPEN"}
        ]
        reflection_recovered = engine.reflect(trade_history=recovered_history)
        assert reflection_recovered["directives"]["pause_trading"] is False

    def test_corrupted_sqlite_memory_file(self, temp_env):
        """Test engine behavior when SQLite database file is corrupted or contains random garbage."""
        db_path, tree_path = temp_env

        # Create valid database first and populate
        engine = OpenHumanCognitiveEngine(
            db_path=db_path,
            memory_tree=MemoryTreeManager(tree_path=tree_path)
        )
        engine.observe({"symbol": "XAUUSD", "price": 2650.0})
        engine.prepare_context()
        engine.reflect()
        engine.commit()

        # Corrupt the database file
        with open(db_path, "wb") as f:
            f.write(b"GARBAGE_DATA_CORRUPT_NON_SQLITE_HEADER\x00\xff\xfe\xaa" * 20)

        # restore_latest_checkpoint with corrupted DB returns None safely
        res = engine.restore_latest_checkpoint()
        assert res is None

    def test_rapid_tick_bursts_and_concurrency(self, temp_env):
        """Test high-frequency tick ingestion (5,000 ticks across 10 threads) with concurrent commit/reflect."""
        db_path, tree_path = temp_env
        engine = OpenHumanCognitiveEngine(
            db_path=db_path,
            memory_tree=MemoryTreeManager(tree_path=tree_path)
        )

        num_threads = 10
        ticks_per_thread = 500
        threads = []
        errors = []

        def worker_feed(thread_idx: int):
            try:
                for i in range(ticks_per_thread):
                    tick = {
                        "symbol": "XAUUSD" if thread_idx % 2 == 0 else "BTCUSD",
                        "price": 2650.0 + (i * 0.05),
                        "spread": 0.25,
                        "atr": 1.45,
                        "cvd_delta": 50.0 * (1 if i % 2 == 0 else -1),
                        "equity": 25000.0 + (i * 1.5),
                        "balance": 25000.0,
                    }
                    engine.observe(tick)
                    if i % 100 == 0:
                        engine.prepare_context()
                        engine.reflect()
                        engine.commit()
            except Exception as e:
                errors.append(e)

        for t_idx in range(num_threads):
            t = threading.Thread(target=worker_feed, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered during tick burst: {errors}"
        assert engine.tick_sequence == num_threads * ticks_per_thread
        assert len(engine.observation_buffer) <= 1000
        assert len(engine.observation_buffer) == min(num_threads * ticks_per_thread, 1000)

    def test_memory_tree_retrieval_empty_and_corrupted_databases(self, temp_env):
        """Test hierarchical memory tree with empty, non-existent, and malformed files."""
        db_path, tree_path = temp_env

        # 1. Non-existent file
        if os.path.exists(tree_path):
            os.remove(tree_path)
        mem = MemoryTreeManager(tree_path=tree_path)
        assert mem.get_relevant_lessons("XAUUSD") == []
        assert mem.compress_memory() == 0

        # 2. Corrupted JSON file
        with open(tree_path, "w", encoding="utf-8") as f:
            f.write("{MALFORMED JSON :::: [}]}")
        mem_corrupt = MemoryTreeManager(tree_path=tree_path)
        assert mem_corrupt.get_relevant_lessons("BTCUSD") == []

        # 3. Store valid lessons with boundary importance scores
        mem_corrupt.store_lesson("GOLD_PATTERNS", "Judas swing sweeps Asian high", importance_score=0.95)
        mem_corrupt.store_lesson("GOLD_PATTERNS", "Noise pattern below ATR", importance_score=0.10)
        mem_corrupt.store_lesson("INVALID_CAT", "General fallback lesson", importance_score=-0.5)  # clamped to 0.0
        mem_corrupt.store_lesson("RISK_LESSONS", "Always honor 2.5% daily drawdown", importance_score=1.5)  # clamped to 1.0

        gold_lessons = mem_corrupt.get_relevant_lessons("XAUUSD", limit=5)
        assert len(gold_lessons) >= 2
        assert gold_lessons[0]["importance"] >= gold_lessons[1]["importance"]

        # 4. Memory compression removes < 0.20 importance
        removed = mem_corrupt.compress_memory(min_importance=0.20)
        assert removed >= 1
        remaining_gold = mem_corrupt.get_relevant_lessons("XAUUSD", limit=10)
        assert all(l["importance"] >= 0.20 for l in remaining_gold)

    def test_recovery_after_abrupt_shutdown(self, temp_env):
        """Test checkpoint state restoration after simulated crash / engine re-instantiation."""
        db_path, tree_path = temp_env

        # Engine 1: Ingest, reflect, commit
        engine1 = OpenHumanCognitiveEngine(
            db_path=db_path,
            memory_tree=MemoryTreeManager(tree_path=tree_path)
        )
        for i in range(15):
            engine1.observe({"symbol": "XAUUSD", "price": 2650.0 + i, "equity": 24800.0, "balance": 25000.0})
        engine1.prepare_context("XAUUSD")
        engine1.reflect(trade_history=[
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -100.0},
            {"symbol": "XAUUSD", "outcome": "LOSS", "pnl": -100.0}
        ])
        commit_res = engine1.commit()
        assert commit_res["status"] == "COMMITTED"
        last_seq = engine1.tick_sequence

        # Simulate abrupt destruction of engine1 and spawn engine2 pointing to same SQLite DB
        engine2 = OpenHumanCognitiveEngine(
            db_path=db_path,
            memory_tree=MemoryTreeManager(tree_path=tree_path)
        )
        assert engine2.tick_sequence == last_seq
        assert engine2.active_directives["pause_trading"] is True
        assert engine2.active_directives["risk_multiplier"] == 0.25
        assert len(engine2.insights) >= 1


# ===========================================================================
# 2. Historical 50-Year Regime Library Adversarial & Boundary Tests
# ===========================================================================

class TestHistoricalRegimeBoundaryAdversarial:
    """Stress tests for 50-Year Regime Library on boundary, zero, 100-sigma, and dimensional edge cases."""

    @pytest.fixture
    def library(self):
        return Historical50YrRegimeLibrary()

    def test_all_zero_feature_vectors(self, library):
        """Test classification when all features are 0.0 (no division by zero or NaN)."""
        zero_vec = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        res = library.classify_current_regime(feature_vector=zero_vec)

        assert res["closest_crisis_regime"] is not None
        assert not math.isnan(res["crisis_similarity"])
        assert not math.isinf(res["crisis_similarity"])
        assert 0.0 <= res["crisis_similarity"] <= 1.0
        assert res["risk_scalar"] in [0.20, 0.40, 0.50, 0.60, 0.65, 0.70, 0.80, 0.90, 1.00]
        assert "all_crisis_similarities" in res
        for sim in res["all_crisis_similarities"].values():
            assert not math.isnan(sim)

    def test_extreme_100_sigma_market_shocks(self, library):
        """Test extreme 100-sigma market collapse / hyper-volatility scenario."""
        shock_vector = [100.0, 50.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        res = library.classify_current_regime(feature_vector=shock_vector)

        assert res["closest_crisis_regime"] in library.crisis_archetypes
        assert not math.isnan(res["crisis_similarity"])
        assert not math.isinf(res["crisis_similarity"])
        assert res["risk_scalar"] <= 1.00

    def test_extreme_negative_shocks(self, library):
        """Test extreme negative stress vector."""
        neg_vector = [-50.0, -20.0, -100.0, -100.0, -50.0, -100.0, -100.0]
        res = library.classify_current_regime(feature_vector=neg_vector)

        assert res["closest_crisis_regime"] in library.crisis_archetypes
        assert not math.isnan(res["crisis_similarity"])
        assert 0.0 <= res["crisis_similarity"] <= 1.0

    def test_nan_inf_boundary_behavior(self, library):
        """Empirically test regime classification with NaN and Inf features."""
        nan_vector = [np.nan, 0.2, np.inf, -np.inf, 0.1, np.nan, 0.5]
        res = library.classify_current_regime(feature_vector=nan_vector)
        # Verify it returns a dictionary without crashing
        assert isinstance(res, dict)
        assert "closest_crisis_regime" in res
        assert "risk_scalar" in res

    def test_exact_cosine_similarity_edge_cases(self, library):
        """Test exact mathematical alignment with crisis centroids and collinear / orthogonal vectors."""
        # 1. Exact 1987 Black Monday Centroid
        centroid_1987 = library.crisis_archetypes["1987_BLACK_MONDAY_CASCADE"]["centroid"]
        res_1987 = library.classify_current_regime(feature_vector=centroid_1987)
        assert res_1987["closest_crisis_regime"] == "1987_BLACK_MONDAY_CASCADE"
        assert res_1987["crisis_similarity"] >= 0.99
        assert res_1987["risk_scalar"] == 0.20
        assert res_1987["action_protocol"] == "DEFENSIVE_CIRCUIT_BREAKER"

        # 2. Exact 2008 GFC Centroid
        centroid_2008 = library.crisis_archetypes["2008_GFC_CREDIT_FREEZE"]["centroid"]
        res_2008 = library.classify_current_regime(feature_vector=centroid_2008)
        assert res_2008["closest_crisis_regime"] == "2008_GFC_CREDIT_FREEZE"
        assert res_2008["crisis_similarity"] >= 0.99
        assert res_2008["risk_scalar"] == 0.20

        # 3. Exact 2023-2026 Sovereign Gold Centroid
        centroid_2026 = library.crisis_archetypes["2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"]["centroid"]
        res_2026 = library.classify_current_regime(feature_vector=centroid_2026)
        assert res_2026["closest_crisis_regime"] == "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"
        assert res_2026["risk_scalar"] == 0.90
        assert res_2026["action_protocol"] == "SOVEREIGN_HARD_ASSET_EXPANSION"

    def test_varying_input_dimensions_padding_and_truncation(self, library):
        """Test backward compatibility with 5D, 3D, and 12D feature vectors."""
        # 5-element vector
        vec_5d = [0.24, 0.12, -0.15, 0.45, 0.85]
        res_5d = library.classify_current_regime(feature_vector=vec_5d)
        assert res_5d["closest_crisis_regime"] is not None

        # 3-element vector (should auto-pad to 7D)
        vec_3d = [0.55, 0.28, 0.05]
        res_3d = library.classify_current_regime(feature_vector=vec_3d)
        assert res_3d["closest_crisis_regime"] is not None

        # 12-element vector (should auto-truncate to 7D)
        vec_12d = [0.65, 0.40, 0.30, 0.60, 0.95, 0.85, 0.50, 99.0, 99.0, 99.0, 99.0, 99.0]
        res_12d = library.classify_current_regime(feature_vector=vec_12d)
        assert res_12d["closest_crisis_regime"] == "2008_GFC_CREDIT_FREEZE"


# ===========================================================================
# 3. Free AI Conversational Core Adversarial & Prop Firm Rules Tests
# ===========================================================================

class TestFreeAICoreAdversarialSuite:
    """Stress tests for Roman Urdu NLP parser, What-If -50% flash crashes, and Funding Pips 25k rules."""

    @pytest.fixture
    def ai_core(self):
        return FreeAIIntelligenceCore()

    def test_adversarial_roman_urdu_slang_and_typo_variations(self, ai_core):
        """Test parsing of heavily slang-loaded, code-switched, and typo-ridden Roman Urdu trading prompts."""
        test_cases = [
            # 1. Roman Urdu queries
            ("bhai gold khareed loun ya abhi wait karun?", "XAUUSD", "BUY", "MARKET_BIAS_QUERY", False),
            ("sona upar jaega ya neeche? kya lagta hai market", "XAUUSD", "BUY", "MARKET_BIAS_QUERY", True),
            ("xauusd gir rha h btao kia krein", "XAUUSD", "SELL", "MARKET_BIAS_QUERY", False),
            # 2. Risk & drawdown queries
            ("aaj ka risk kitna banta hai 25k account pe?", "XAUUSD", "NEUTRAL", "RISK_DRAWDOWN_QUERY", True),
            ("drawdown limit kitni bachi hai?", "XAUUSD", "NEUTRAL", "RISK_DRAWDOWN_QUERY", True),
            # 3. What-If scenario queries
            ("agar market 20% drop ho jaye toh kya hoga?", "XAUUSD", "SELL", "WHAT_IF_SCENARIO_QUERY", True),
            ("what if btc 10% shock deta hai?", "BTCUSD", "NEUTRAL", "WHAT_IF_SCENARIO_QUERY", False),
            ("scenario btao agar dollar crash kr jaye", "XAUUSD", "NEUTRAL", "WHAT_IF_SCENARIO_QUERY", True),
            # 4. Trade proposal requests
            ("trade setup batao 25k challenge ka", "XAUUSD", "NEUTRAL", "TRADE_PROPOSAL_REQUEST", True),
            ("kitna lot size lagana chahiye gold me?", "XAUUSD", "NEUTRAL", "TRADE_PROPOSAL_REQUEST", True),
            ("btc ka blueprint do", "BTCUSD", "NEUTRAL", "TRADE_PROPOSAL_REQUEST", False),
            # 5. Direct execution commands
            ("buy karo 0.10 lot gold", "XAUUSD", "BUY", "TRADE_EXECUTION_COMMAND", False),
            ("sell 1.5 lots btc", "BTCUSD", "SELL", "TRADE_EXECUTION_COMMAND", False),
            # 6. Trade management commands
            ("breakeven pe shift kardo", "XAUUSD", "NEUTRAL", "TRADE_MANAGEMENT_COMMAND", True),
            ("trade band karo fauran", "XAUUSD", "NEUTRAL", "TRADE_MANAGEMENT_COMMAND", True),
            # 7. Greetings
            ("salam jarvis bhai kaise ho", "XAUUSD", "NEUTRAL", "GREETING_OR_STATUS_QUERY", True),
        ]

        for query, expected_sym, expected_dir, expected_intent, is_urdu in test_cases:
            parsed = ai_core.parse_intent(query)
            assert parsed["symbol"] == expected_sym, f"Failed symbol extraction for: '{query}'. Got {parsed['symbol']}"
            if expected_intent:
                assert parsed["intent"] == expected_intent, f"Failed intent for: '{query}'. Got {parsed['intent']}, expected {expected_intent}"
            if is_urdu:
                assert parsed["is_urdu"] is True, f"Failed is_urdu detection for: '{query}'"

    def test_multi_asset_entity_aliases(self, ai_core):
        """Test slang aliases for multi-asset coverage: sona, chandi, fiber, cable, yen, solana, ether."""
        aliases = [
            ("chandi bechun ya kharidu", "XAGUSD"),
            ("sona buy karna hai", "XAUUSD"),
            ("fiber me trade lagao", "EURUSD"),
            ("cable ka analysis do", "GBPUSD"),
            ("dollar yen me kya position ban sakti h", "USDJPY"),
            ("ether me kitna lot banta hai", "ETHUSD"),
            ("solana long karo", "SOLUSD"),
            ("bitcoin spot analysis", "BTCUSD")
        ]
        for query, expected_sym in aliases:
            parsed = ai_core.parse_intent(query)
            assert parsed["symbol"] == expected_sym, f"Failed alias resolution for '{query}' -> got '{parsed['symbol']}', expected '{expected_sym}'"

    def test_extreme_what_if_shocks_flash_crashes(self, ai_core):
        """Test extreme 3-Pillar What-If matrix under -50% and -90% flash crash shocks."""
        # 1. -50% Flash Crash on BTCUSD ($95,000 -> $47,500)
        what_if_btc_50 = ai_core.generate_what_if_matrix(
            symbol="BTCUSD",
            current_price=95000.0,
            direction="BUY",
            custom_shock_pct=0.50,
            equity=25000.0,
            risk_pct=0.0075
        )
        p3_btc = what_if_btc_50["pillars"]["pillar_3_stress_case"]
        assert p3_btc["shock_pips"] == 47500.0
        assert p3_btc["stressed_loss_usd"] > p3_btc["safe_daily_cap_usd"]
        assert p3_btc["compliance_status"] == "WARNING_LIMIT_BREACH"
        assert p3_btc["var_99_usd"] > 0
        assert p3_btc["cvar_99_usd"] > p3_btc["var_99_usd"]

        # 2. -30% Shock on Gold ($2,650 -> $1,855)
        what_if_gold_30 = ai_core.generate_what_if_matrix(
            symbol="XAUUSD",
            current_price=2650.0,
            direction="BUY",
            custom_shock_pct=0.30,
            equity=25000.0,
            risk_pct=0.0075
        )
        p3_gold = what_if_gold_30["pillars"]["pillar_3_stress_case"]
        assert p3_gold["compliance_status"] == "WARNING_LIMIT_BREACH"

        # 3. Mild 0.5% Normal Market Fluctuation
        what_if_mild = ai_core.generate_what_if_matrix(
            symbol="EURUSD",
            current_price=1.0850,
            direction="BUY",
            custom_shock_pct=0.005,
            equity=25000.0,
            risk_pct=0.0050
        )
        p3_mild = what_if_mild["pillars"]["pillar_3_stress_case"]
        assert p3_mild["compliance_status"] == "SAFE_UNDER_STRESS"

    def test_funding_pips_25k_rules_cannot_be_violated(self, ai_core):
        """Adversarially verify that Funding Pips 25k account rules cannot be breached under any proposal."""
        # 1. User requests absurdly aggressive 50% risk ($12,500)
        proposal_hyper_risk = ai_core.generate_funding_pips_25k_proposal(
            symbol="XAUUSD",
            account_equity=25000.0,
            risk_pct=0.50
        )
        # Must be capped strictly at 1.0% ($250.00)
        assert proposal_hyper_risk["risk_pct"] == 1.00
        assert proposal_hyper_risk["risk_dollar"] == 250.00
        assert proposal_hyper_risk["lot_size"] <= 5.00
        assert proposal_hyper_risk["lot_size"] >= 0.01

        # 2. User requests absurdly micro 0.001% risk ($0.25)
        proposal_micro_risk = ai_core.generate_funding_pips_25k_proposal(
            symbol="XAUUSD",
            account_equity=25000.0,
            risk_pct=0.00001
        )
        # Must be floored at min 0.50% ($125.00)
        assert proposal_micro_risk["risk_pct"] == 0.50
        assert proposal_micro_risk["risk_dollar"] == 125.00

        # 3. Verify R:R Invariants across all supported assets
        all_symbols = ["XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPUSD", "USDJPY"]
        for sym in all_symbols:
            for d in ["BUY", "SELL"]:
                prop = ai_core.generate_funding_pips_25k_proposal(symbol=sym, direction=d, account_equity=25000.0)
                # Risk invariants
                assert prop["risk_dollar"] <= 250.00, f"Risk dollar exceeds 1% cap on {sym}: {prop['risk_dollar']}"
                assert prop["risk_dollar"] >= 125.00, f"Risk dollar below 0.5% floor on {sym}: {prop['risk_dollar']}"
                assert prop["reward_to_risk"] >= 1.5, f"R:R below 1.5 on {sym}: {prop['reward_to_risk']}"
                assert prop["aladdin_var_approved"] is True
                assert prop["compliance_verdict"] == "APPROVED_FOR_25K_EXECUTION"

                # Spatial price invariants
                if d == "BUY":
                    assert prop["stop_loss"] < prop["entry_price"], f"Buy SL must be below entry on {sym}"
                    assert prop["take_profit_1"] > prop["entry_price"], f"Buy TP1 must be above entry on {sym}"
                    assert prop["take_profit_2"] > prop["take_profit_1"], f"Buy TP2 must be above TP1 on {sym}"
                else:
                    assert prop["stop_loss"] > prop["entry_price"], f"Sell SL must be above entry on {sym}"
                    assert prop["take_profit_1"] < prop["entry_price"], f"Sell TP1 must be below entry on {sym}"
                    assert prop["take_profit_2"] < prop["take_profit_1"], f"Sell TP2 must be below TP1 on {sym}"

    def test_consult_market_end_to_end_adversarial_queries(self, ai_core):
        """Test universal consult_market dispatcher with mixed adversarial prompts."""
        queries = [
            "kya lagta hai sona kahan jaega?",
            "agar btc 50% drop ho jaye what if scenario?",
            "trade setup batao gold 25k challenge",
            "aaj ka risk kitna allow hai?",
            "salam bhai system ka status batao",
            "cable short entry setup"
        ]
        for q in queries:
            res = ai_core.consult_market(q)
            assert "query" in res
            assert "intent" in res
            assert "advisory_response" in res
            assert len(res["advisory_response"]) > 20
            assert "engine" in res
