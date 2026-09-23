"""
tests/test_m2_cognitive_smc_ai.py
Comprehensive Master Test Suite for Milestone M2:
Muhammad's Jarvis Cognitive Intelligence & Self-Upgrading Memory.

Covers:
  - Feature 8: OpenHuman Cognitive Engine (4-phase tick cycle, SQLite WAL checkpointing, tilt detection)
  - Feature 9: 50-Year Historical Crisis Regime Library (10 centroids, 7D Cosine & RBF similarity, risk scaling)
  - Feature 10: FVG 50% Consequent Encroachment (CE 50%) & Multi-Candle Mitigation Lifecycle
  - Feature 11: Asian Session Box (00-06 UTC) & London Open Judas Swings (07-10 UTC)
  - Feature 12: Turtle Soup Equal Highs / Lows (EQH/EQL) Inducement Sweeps across multi-assets
  - Feature 13: Lee-Ready (1991) Cumulative Volume Delta (CVD) & Order Absorption Divergence
  - Feature 14: Roman Urdu & English NLP Lexicon & Entity Extraction
  - Feature 15: 3-Pillar What-If Scenario Matrix & 3-Sigma Stress Testing (Aladdin 99% VaR/CVaR)
  - Feature 16: Auto-Calibrated Funding Pips 25k Trade Proposals & Prop Firm Shields
"""

import os
import tempfile
import sqlite3
import datetime
import numpy as np
import pandas as pd
import pytest

from src.openhuman_cognitive_engine import (
    OpenHumanCognitiveEngine,
    MemoryTreeManager,
    SubconsciousReflectionEngine,
    SuperContextBuilder
)
from src.historical_50yr_regime_library import Historical50YrRegimeLibrary
from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.market_maker_game_engine import MarketMakerGameEngine
from src.order_flow_quant import OrderFlowQuantEngine
from src.free_ai_intelligence_core import FreeAIIntelligenceCore


# ===========================================================================
# 1. Feature 8: OpenHuman Cognitive Engine & SQLite WAL Tests
# ===========================================================================

class TestOpenHumanCognitiveEngine:

    @pytest.fixture
    def cognitive_setup(self):
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test_cognitive.db")
        tree_path = os.path.join(tmp_dir, "test_tree.json")
        mem_tree = MemoryTreeManager(tree_path=tree_path)
        regime_lib = Historical50YrRegimeLibrary()
        engine = OpenHumanCognitiveEngine(db_path=db_path, memory_tree=mem_tree, regime_library=regime_lib)
        return engine, db_path, mem_tree

    def test_four_phase_tick_cycle(self, cognitive_setup):
        engine, db_path, mem_tree = cognitive_setup
        assert engine.state == "IDLE"

        # Phase 1: OBSERVE
        tick = {
            "symbol": "XAUUSD",
            "price": 2650.50,
            "spread": 0.20,
            "atr": 1.20,
            "cvd_delta": 450.0,
            "equity": 25000.0,
            "balance": 25000.0
        }
        engine.observe(tick)
        assert engine.state == "OBSERVED"
        assert len(engine.observation_buffer) == 1
        assert engine.tick_sequence == 1

        # Phase 2: PREPARE CONTEXT
        context = engine.prepare_context("XAUUSD")
        assert engine.state == "CONTEXT_PREPARED"
        assert context["symbol"] == "XAUUSD"
        assert "historical_regime" in context
        assert "relevant_lessons" in context

        # Phase 3: REFLECT
        history = [
            {"outcome": "WIN", "pnl": 120.0, "symbol": "XAUUSD", "session": "LONDON_OPEN"},
            {"outcome": "WIN", "pnl": 150.0, "symbol": "XAUUSD", "session": "LONDON_OPEN"},
            {"outcome": "WIN", "pnl": 90.0, "symbol": "EURUSD", "session": "NEW_YORK_OPEN"},
            {"outcome": "WIN", "pnl": 110.0, "symbol": "XAUUSD", "session": "LONDON_OPEN"},
            {"outcome": "WIN", "pnl": 130.0, "symbol": "BTCUSD", "session": "ASIAN_SESSION"},
        ]
        reflection = engine.reflect(trade_history=history)
        assert engine.state == "REFLECTED"
        assert "insights" in reflection
        assert any(i["category"] == "STREAK" for i in reflection["insights"])

        # Phase 4: COMMIT
        commit_res = engine.commit()
        assert commit_res["status"] == "COMMITTED"
        assert engine.state == "IDLE"

        # Verify SQLite checkpoint insertion
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT checkpoint_id, equity, balance FROM cognitive_checkpoints")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 25000.0
        conn.close()

    def test_sqlite_crash_recovery(self, cognitive_setup):
        engine, db_path, mem_tree = cognitive_setup
        engine.observe({"symbol": "XAUUSD", "price": 2650.0, "equity": 25400.0, "balance": 25000.0})
        engine.prepare_context()
        engine.reflect()
        res = engine.commit()
        checkpoint_id = res["checkpoint_id"]

        # Spin up fresh engine instance pointing to the same DB
        recovered_engine = OpenHumanCognitiveEngine(db_path=db_path)
        assert recovered_engine.tick_sequence == engine.tick_sequence
        assert recovered_engine.active_directives is not None

    def test_emotional_tilt_shield_activation(self, cognitive_setup):
        engine, _, _ = cognitive_setup
        tilt_history = [
            {"outcome": "WIN", "pnl": 100.0, "symbol": "XAUUSD"},
            {"outcome": "LOSS", "pnl": -150.0, "symbol": "XAUUSD"},
            {"outcome": "LOSS", "pnl": -180.0, "symbol": "XAUUSD"}
        ]
        engine.observe({"symbol": "XAUUSD", "price": 2650.0})
        engine.prepare_context()
        reflection = engine.reflect(trade_history=tilt_history)

        assert reflection["directives"]["pause_trading"] is True
        assert reflection["directives"]["risk_multiplier"] == 0.25
        assert any(i["category"] == "TILT" for i in reflection["insights"])

    def test_memory_tree_storage_and_compression(self, cognitive_setup):
        _, _, mem_tree = cognitive_setup
        mem_tree.store_lesson("GOLD_PATTERNS", "Bullish FVG at Asian low is 80% win rate", importance_score=0.90)
        mem_tree.store_lesson("GOLD_PATTERNS", "Low importance noise lesson", importance_score=0.10)

        lessons = mem_tree.get_relevant_lessons("XAUUSD", limit=5)
        assert len(lessons) >= 1
        assert lessons[0]["lesson"] == "Bullish FVG at Asian low is 80% win rate"

        # Compress memory
        removed = mem_tree.compress_memory(min_importance=0.20)
        assert removed == 1
        lessons_after = mem_tree.get_relevant_lessons("XAUUSD", limit=5)
        assert len(lessons_after) == 1

    def test_supercontext_score_calculation(self):
        builder = SuperContextBuilder()
        analysis = {
            "trend_direction": "BULLISH",
            "rsi": 45.0,
            "atr": 1.5,
            "current_price": 2650.0,
            "fincept_sentiment": 65.0
        }
        ctx = builder.build_trade_context("XAUUSD", analysis)
        assert 0 <= ctx["context_score"] <= 100
        assert ctx["context_score"] >= 40


# ===========================================================================
# 2. Feature 9: 50-Year Historical Crisis Regime Library Tests
# ===========================================================================

class TestHistorical50YrRegimeLibrary:

    @pytest.fixture
    def regime_lib(self):
        return Historical50YrRegimeLibrary()

    def test_ten_crisis_centroids_dimensions(self, regime_lib):
        assert len(regime_lib.crisis_archetypes) >= 10
        canonical_10 = [
            "1971_NIXON_SHOCK_STAGFLATION",
            "1987_BLACK_MONDAY_CASCADE",
            "1997_ASIAN_FINANCIAL_CRISIS",
            "2000_DOTCOM_BUBBLE_COLLAPSE",
            "2008_GFC_CREDIT_FREEZE",
            "2011_US_DEBT_DOWNGRADE_EURO_CRISIS",
            "2015_SNB_EUR_CHF_PEG_REMOVAL",
            "2020_COVID_LIQUIDITY_FREEZE",
            "2022_FED_TIGHTENING_INFLATION_SHOCK",
            "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"
        ]
        for name in canonical_10:
            assert name in regime_lib.crisis_archetypes
            centroid = regime_lib.crisis_archetypes[name]["centroid"]
            assert isinstance(centroid, np.ndarray)
            assert len(centroid) == 7

    def test_exact_centroid_matching(self, regime_lib):
        # Pass exact 2008 GFC centroid vector
        gfc_centroid = regime_lib.crisis_archetypes["2008_GFC_CREDIT_FREEZE"]["centroid"]
        res = regime_lib.classify_current_regime(feature_vector=gfc_centroid)

        assert res["closest_crisis_regime"] == "2008_GFC_CREDIT_FREEZE"
        assert res["crisis_similarity"] >= 0.95
        assert res["risk_scalar"] == 0.20
        assert res["action_protocol"] == "DEFENSIVE_CIRCUIT_BREAKER"

    def test_sovereign_gold_rush_regime(self, regime_lib):
        # High gold impulse, negative yield curve stress, moderate vol
        res = regime_lib.classify_current_regime(
            realized_vol_annual=0.20,
            current_drawdown_pct=0.04,
            dxy_20d_ret=-0.08,
            yield_curve_stress=-0.20,
            spread_stress_score=0.35,
            cross_asset_correlation=-0.15,
            gold_20d_ret=0.80
        )
        assert res["closest_crisis_regime"] in [
            "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH",
            "1971_NIXON_SHOCK_STAGFLATION",
            "2011_US_DEBT_DOWNGRADE_EURO_CRISIS"
        ]
        assert res["risk_scalar"] >= 0.70

    def test_backward_compatibility_5_feature_input(self, regime_lib):
        # 5-element input: [vol, drawdown, dxy, spread, gold]
        res = regime_lib.classify_current_regime(feature_vector=[0.65, 0.40, 0.30, 0.95, 0.50])
        assert "closest_crisis_regime" in res
        assert "all_crisis_similarities" in res


# ===========================================================================
# 3. Feature 10: FVG 50% Consequent Encroachment & Mitigation Tests
# ===========================================================================

class TestFVGConsequentEncroachment:

    def test_bullish_fvg_ce_and_mitigation_lifecycle(self):
        # 3 candles forming Bullish FVG: C1 High=100.0, C2 Large Green, C3 Low=104.0
        # Then C4 dips to 103.0 (partially mitigated), C5 dips to 101.5 (hits CE 50%=102.0)
        data = {
            "time": pd.date_range("2026-01-01", periods=6, freq="15min"),
            "open":  [98.0, 100.5, 105.0, 106.0, 104.0, 102.0],
            "high":  [100.0, 106.0, 107.0, 106.5, 104.5, 103.0],
            "low":   [97.5, 100.0, 104.0, 102.5, 101.5, 101.0],
            "close": [99.5, 105.5, 106.0, 103.5, 102.0, 102.5]
        }
        df = pd.DataFrame(data)
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=1.0, symbol="EURUSD")

        assert len(fvgs) >= 1
        bull_fvg = next(f for f in fvgs if f["type"] == "BULLISH_FVG")
        assert bull_fvg["top"] == 104.0
        assert bull_fvg["bottom"] == 100.0
        assert bull_fvg["ce"] == 102.0
        assert bull_fvg["ce_50"] == 102.0
        assert bull_fvg["mitigated"] is True
        assert bull_fvg["partially_mitigated"] is True

    def test_bearish_fvg_ce_calculation(self):
        # 3 candles forming Bearish FVG: C1 Low=110.0, C2 Large Red, C3 High=106.0
        data = {
            "time": pd.date_range("2026-01-01", periods=4, freq="15min"),
            "open":  [112.0, 109.0, 105.0, 104.0],
            "high":  [113.0, 109.5, 106.0, 105.0],
            "low":   [110.0, 104.0, 103.0, 103.5],
            "close": [110.5, 104.5, 104.0, 104.5]
        }
        df = pd.DataFrame(data)
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=1.0, symbol="EURUSD")

        assert len(fvgs) >= 1
        bear_fvg = next(f for f in fvgs if f["type"] == "BEARISH_FVG")
        assert bear_fvg["top"] == 110.0
        assert bear_fvg["bottom"] == 106.0
        assert bear_fvg["ce_50"] == 108.0


# ===========================================================================
# 4. Feature 11: Asian Session Box & London Judas Swings Tests
# ===========================================================================

class TestAsianJudasSwings:

    def test_asian_session_box_calculation(self):
        engine = MarketMakerGameEngine()
        times = pd.date_range("2026-01-01 00:00:00", periods=8, freq="1h", tz="UTC")
        df = pd.DataFrame({
            "time": times,
            "high": [2640.0, 2645.0, 2642.0, 2648.0, 2644.0, 2646.0, 2655.0, 2660.0],
            "low":  [2635.0, 2638.0, 2636.0, 2637.0, 2639.0, 2638.0, 2642.0, 2650.0],
            "open": [2636.0, 2640.0, 2641.0, 2643.0, 2641.0, 2644.0, 2645.0, 2655.0],
            "close":[2640.0, 2642.0, 2643.0, 2644.0, 2644.0, 2645.0, 2654.0, 2658.0]
        })
        box = engine.calculate_asian_session_box(df)
        assert box["asian_high"] == 2648.0
        assert box["asian_low"] == 2635.0
        assert box["asian_range"] == 13.0
        assert box["asian_mid"] == 2641.5

    def test_london_open_bearish_judas_swing_detection(self):
        engine = MarketMakerGameEngine()
        # Asian Box: High = 2650.0, Low = 2640.0
        df_asian = pd.DataFrame({
            "high": [2650.0, 2648.0],
            "low":  [2640.0, 2642.0],
            "open": [2642.0, 2645.0],
            "close":[2648.0, 2644.0]
        })
        # London Open Candle: Sweeps to 2655.0, closes at 2646.0 with upper wick = 9.0 (range=11.0, wick > 40%)
        df_london = pd.DataFrame({
            "high": [2655.0],
            "low":  [2644.0],
            "open": [2645.0],
            "close":[2646.0]
        })
        judas = engine.detect_judas_swing(df_london, session_name="LONDON", df_asian=df_asian)
        assert judas["judas_detected"] is True
        assert judas["type"] == "BEARISH_JUDAS_SWING"
        assert judas["swept_level"] == 2650.0
        assert judas["rejection_wick_price"] == 2655.0


# ===========================================================================
# 5. Features 12 & 13: Turtle Soup Sweeps & Lee-Ready CVD Tests
# ===========================================================================

class TestTurtleSoupAndLeeReadyCVD:

    def test_turtle_soup_eqh_sweep(self):
        quant = OrderFlowQuantEngine(pip_tolerance=2.0)
        # Create 25 bars with Equal Highs at 2650.0 on Gold, and last bar sweeping to 2650.80 and closing at 2648.0
        highs = [2640.0] * 25
        lows = [2630.0] * 25
        opens = [2635.0] * 25
        closes = [2635.0] * 25

        highs[5] = 2650.00
        highs[12] = 2650.10  # EQH cluster within 2.0 pips ($0.20 on Gold)
        highs[-1] = 2650.80  # Sweep bar
        opens[-1] = 2646.00
        closes[-1] = 2648.00
        lows[-1] = 2645.00

        df = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        inducement = quant.detect_eqh_eql_inducement(df, symbol="XAUUSD")

        assert inducement["is_swept"] is True
        assert inducement["inducement_type"] == "BEARISH_EQH_SWEEP"
        assert abs(inducement["level"] - 2650.10) < 0.20

    def test_lee_ready_cvd_calculation_and_absorption(self):
        quant = OrderFlowQuantEngine()
        ticks = pd.DataFrame({
            "bid": [2650.0, 2650.1, 2650.2, 2650.3, 2650.4],
            "ask": [2650.2, 2650.3, 2650.4, 2650.5, 2650.6],
            "last": [2650.2, 2650.3, 2650.4, 2650.5, 2650.6],  # Trade at ask -> Buy (+1)
            "volume": [10.0, 15.0, 20.0, 25.0, 30.0]
        })
        cvd_res = quant.compute_tick_cvd(ticks)
        assert cvd_res["net_delta"] == 100
        assert cvd_res["buyer_ratio"] == 1.00
        assert cvd_res["divergence"] == "BULLISH_CVD_SURGE"
        assert cvd_res["absorption_type"] == "BUYER_ABSORPTION"

    def test_detect_absorption_divergence(self):
        quant = OrderFlowQuantEngine()
        # Price Lower Low (2640 < 2645), CVD Higher Low (+800 > +400)
        div = quant.detect_absorption_divergence(
            price_swing_1=2645.0,
            price_swing_2=2640.0,
            cvd_swing_1=400.0,
            cvd_swing_2=800.0
        )
        assert div["absorption_detected"] is True
        assert div["type"] == "BUYER_ABSORPTION"
        assert div["bias"] == "BULLISH_REVERSAL"


# ===========================================================================
# 6. Features 14, 15, 16: Free AI Intelligence Core Tests
# ===========================================================================

class TestFreeAIIntelligenceCore:

    @pytest.fixture
    def ai_core(self):
        return FreeAIIntelligenceCore()

    def test_roman_urdu_intent_parsing(self, ai_core):
        queries = [
            ("kya gold buy karna chahiye?", "MARKET_BIAS_QUERY", "XAUUSD", "BUY"),
            ("aaj ka risk kitna bacha hai?", "RISK_DRAWDOWN_QUERY", "XAUUSD", "NEUTRAL"),
            ("agar btc 5% crash kar jaye to kya hoga?", "WHAT_IF_SCENARIO_QUERY", "BTCUSD", "NEUTRAL"),
            ("funding pips 25k trade proposal do gold par", "TRADE_PROPOSAL_REQUEST", "XAUUSD", "NEUTRAL"),
            ("buy xauusd 0.10 lot", "TRADE_EXECUTION_COMMAND", "XAUUSD", "BUY"),
            ("tamam trades close kar do", "TRADE_MANAGEMENT_COMMAND", "XAUUSD", "NEUTRAL"),
            ("salam jarvis status batao", "GREETING_OR_STATUS_QUERY", "XAUUSD", "NEUTRAL")
        ]
        for q, expected_intent, expected_sym, expected_dir in queries:
            res = ai_core.parse_intent(q)
            assert res["intent"] == expected_intent, f"Failed intent for query: {q}"
            assert res["symbol"] == expected_sym, f"Failed symbol for query: {q}"
            if expected_dir != "NEUTRAL":
                assert res["direction"] == expected_dir

    def test_three_pillar_what_if_matrix(self, ai_core):
        # 1. Test standard shock matrix
        res = ai_core.generate_what_if_matrix(symbol="XAUUSD", current_price=2650.0, direction="BUY", custom_shock_pct=0.005)
        pillars = res["pillars"]
        assert "pillar_1_base_case" in pillars
        assert "pillar_2_bull_case" in pillars
        assert "pillar_3_stress_case" in pillars

        base = pillars["pillar_1_base_case"]
        assert base["win_probability"] == 0.62
        assert base["expected_pnl_usd"] > 0

        stress = pillars["pillar_3_stress_case"]
        assert "var_99_usd" in stress
        assert "cvar_99_usd" in stress
        assert stress["compliance_status"] == "SAFE_UNDER_STRESS"

        # 2. Test large shock warning
        large_res = ai_core.generate_what_if_matrix(symbol="XAUUSD", current_price=2650.0, direction="BUY", custom_shock_pct=0.05)
        assert large_res["pillars"]["pillar_3_stress_case"]["compliance_status"] == "WARNING_LIMIT_BREACH"

    def test_funding_pips_25k_proposal_calibration(self, ai_core):
        prop = ai_core.generate_funding_pips_25k_proposal(symbol="XAUUSD", direction="BUY", current_price=2650.0)
        assert prop["account_tier"] == "Funding Pips $25,000 Challenge"
        assert prop["risk_dollar"] <= 250.00  # Max 1%
        assert prop["max_daily_loss_shield"] == 625.0
        assert prop["max_total_loss_shield"] == 1500.0
        assert prop["aladdin_var_approved"] is True
        assert prop["compliance_verdict"] == "APPROVED_FOR_25K_EXECUTION"
        assert prop["lot_size"] > 0.0
        assert "👑 *FUNDING PIPS 25K TRADE PROPOSAL" in prop["formatted_proposal"]

    def test_universal_consult_market(self, ai_core):
        resp = ai_core.consult_market("agar gold 3% drop ho jaye to kya hoga?")
        assert resp["intent"] == "WHAT_IF_SCENARIO_QUERY"
        assert "what_if_matrix" in resp
        assert "🔮 *3-PILLAR WHAT-IF" in resp["advisory_response"]

        resp_prop = ai_core.consult_market("give me a 25k trade setup for EURUSD")
        assert resp_prop["intent"] == "TRADE_PROPOSAL_REQUEST"
        assert "trade_proposal" in resp_prop
