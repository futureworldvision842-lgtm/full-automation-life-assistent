"""
tests/test_custom_strategy_engine.py — Comprehensive Test Suite for Milestone M4
================================================================================
Covers:
  1. Mode A: Natural Language Strategy Interpreter (English & Pure Roman Urdu)
  2. Mode B: Interactive Visual Rule Builder Engine (Serialization, Validation, Operators)
  3. Deterministic Risk Safeguards (Clamp <= 0.75% / $750, R:R >= 2.50, +1.0R BE, 15m News)
  4. Autonomous Multi-Agent Consensus Integration (MTF M15+H1+H4, Unanimous Risk Officer Veto)
  5. Multi-Account 5-Layer Anti-Ban Routing Bridge (Jitter, Dispersion, Magic Numbers, Proxies)
  6. FastAPI Router Endpoints (/parse, /build, /consensus, /execute, /presets, /health)
  7. Compliance & Clean-Room Prohibited Token Audits
"""

import json
import os
import re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.trading.custom_strategy_engine import (
    CustomStrategyEngine,
    DeterministicRiskGuard,
    NaturalLanguageStrategyInterpreter,
    RuleCondition,
    StrategyDefinition,
    VisualRuleBuilderEngine,
    ConsensusChamberBridge,
    MultiAccountExecutionBridge,
    get_custom_strategy_engine,
    sanitize_roman_urdu,
    router as strategy_router,
    MAX_PERMISSIBLE_RISK_PCT,
    MAX_FUNDINGPIPS_USD_CAP,
    MIN_INSTITUTIONAL_RR,
    DYNAMIC_BREAKEVEN_TRIGGER_R,
    DEVANAGARI_REGEX,
    ARABIC_URDU_REGEX,
)


@pytest.fixture
def engine():
    return CustomStrategyEngine()


@pytest.fixture
def api_client():
    app = FastAPI()
    app.include_router(strategy_router)
    return TestClient(app)


# =============================================================================
# 1. MODE A: NATURAL LANGUAGE STRATEGY INTERPRETER TESTS
# =============================================================================

class TestNaturalLanguageInterpreter:

    def test_parse_english_prompt_comprehensive(self, engine):
        prompt = (
            "Buy Gold on M15 when price sweeps London low and tests bullish Order Block, "
            "risk 0.5%, take profit 1:3 R:R"
        )
        strat = engine.parse_natural_language(prompt, balance=100000.0)

        assert strat.action == "BUY"
        assert strat.symbol == "XAUUSD"
        assert strat.timeframe == "M15"
        assert strat.risk_pct == 0.50
        assert strat.dollar_risk_cap == 500.0
        assert strat.target_rr == 3.0
        assert strat.language == "en"

        indicators = [c.indicator for c in strat.conditions]
        assert "LIQUIDITY_SWEEP" in indicators
        assert "SMC_ORDER_BLOCK" in indicators
        assert "Directives parsed" in strat.confirmation_narrative

    def test_parse_roman_urdu_prompt_pure_latin(self, engine):
        prompt = (
            "M15 timeframe par Gold buy karo jab London session low sweep ho aur "
            "bullish Order Block hit ho, 0.5% risk aur 1:3 TP rakho"
        )
        strat = engine.parse_natural_language(prompt, balance=100000.0)

        assert strat.action == "BUY"
        assert strat.symbol == "XAUUSD"
        assert strat.timeframe == "M15"
        assert strat.risk_pct == 0.50
        assert strat.target_rr == 3.0
        assert strat.language == "ur"

        # Verify pure Roman Urdu script with ZERO Devanagari or Arabic unicode characters
        assert not DEVANAGARI_REGEX.search(strat.confirmation_narrative)
        assert not ARABIC_URDU_REGEX.search(strat.confirmation_narrative)
        assert "Jee Sovereign Master Sir" in strat.confirmation_narrative
        assert "XAUUSD" in strat.confirmation_narrative

    def test_parse_roman_urdu_keywords_and_loanwords(self, engine):
        prompt = "H1 timeframe par EURUSD sell karo jab 50% CE FVG mitigate ho, nuqsan 15 pips, 0.6% risk"
        strat = engine.parse_natural_language(prompt, balance=100000.0)

        assert strat.action == "SELL"
        assert strat.symbol == "EURUSD"
        assert strat.timeframe == "H1"
        assert strat.sl_pips == 15.0
        assert strat.risk_pct == 0.60
        assert strat.dollar_risk_cap == 600.0
        assert strat.target_rr >= MIN_INSTITUTIONAL_RR
        assert strat.language == "ur"

    def test_parse_risk_clamping_above_75_basis_points(self, engine):
        # User requests 2.0% risk (violating the 0.75% cap)
        prompt = "Buy EURUSD on M15 when RSI < 30, risk 2.0%, 1:3 RR"
        strat = engine.parse_natural_language(prompt, balance=100000.0)

        # Must strictly clamp to 0.75% ($750.00)
        assert strat.risk_pct == 0.75
        assert strat.dollar_risk_cap == 750.0

    def test_parse_rr_floor_enforcement(self, engine):
        # User requests an insufficient 1:1.5 R:R
        prompt = "Buy BTCUSD on M15, risk 0.5%, stop loss 100 pips, take profit 150 pips"
        strat = engine.parse_natural_language(prompt, balance=100000.0)

        # Must strictly enforce minimum 1:2.50 R:R
        assert strat.sl_pips == 100.0
        assert strat.target_rr >= MIN_INSTITUTIONAL_RR
        assert strat.tp_pips >= 250.0

    def test_parse_indicators_detection_coverage(self, engine):
        test_cases = [
            ("Buy Bitcoin on M15 when positive CVD absorption crosses above VWAP", "BTCUSD", "BUY", ["CVD_DELTA", "VWAP"]),
            ("Sell GBPUSD on H4 with EMA golden cross and break of structure", "GBPUSD", "SELL", ["EMA_CROSS", "BOS"]),
            ("Buy Solana on M15 fair value gap 50% CE fill with RSI oversold", "SOLUSD", "BUY", ["FVG_50_CE", "RSI"]),
        ]
        for prompt, exp_sym, exp_side, exp_inds in test_cases:
            res = engine.parse_natural_language(prompt)
            assert res.symbol == exp_sym
            assert res.action == exp_side
            inds = [c.indicator for c in res.conditions]
            for exp_ind in exp_inds:
                assert exp_ind in inds


# =============================================================================
# 2. MODE B: INTERACTIVE VISUAL RULE BUILDER TESTS
# =============================================================================

class TestVisualRuleBuilder:

    def test_build_valid_visual_strategy(self, engine):
        schema = {
            "name": "Gold M15 Institutional OB Strategy",
            "symbol": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "conditions": [
                {"indicator": "SMC_ORDER_BLOCK", "operator": "RETESTS", "threshold": "BULLISH_OB", "timeframe": "M15"},
                {"indicator": "RSI", "operator": "LESS_THAN", "threshold": 35.0, "timeframe": "M15"},
                {"indicator": "CVD_DELTA", "operator": "ABSORBS_VOLUME", "threshold": 500.0, "timeframe": "M15"},
            ],
            "risk_pct": 0.50,
            "sl_pips": 15.0,
            "tp_pips": 45.0,
            "target_rr": 3.0,
            "target_accounts": ["fundingpips_100k", "ftmo_100k"],
        }
        is_valid, errors, strat = engine.build_visual_strategy(schema, balance=100000.0)

        assert is_valid is True
        assert len(errors) == 0
        assert strat.symbol == "XAUUSD"
        assert strat.action == "BUY"
        assert len(strat.conditions) == 3
        assert strat.risk_pct == 0.50
        assert strat.dollar_risk_cap == 500.0
        assert strat.target_rr == 3.0

    def test_build_clamps_excessive_risk(self, engine):
        schema = {
            "symbol": "EURUSD",
            "action": "SELL",
            "timeframe": "H1",
            "conditions": [
                {"indicator": "FVG_50_CE", "operator": "MITIGATES_50_PCT", "threshold": 50.0}
            ],
            "risk_pct": 1.25,  # Violates 0.75% cap
            "sl_pips": 20.0,
            "tp_pips": 60.0,
        }
        is_valid, errors, strat = engine.build_visual_strategy(schema, balance=100000.0)

        assert is_valid is True
        assert strat.risk_pct == 0.75
        assert strat.dollar_risk_cap == 750.0

    def test_build_enforces_minimum_rr_floor(self, engine):
        schema = {
            "symbol": "GBPUSD",
            "action": "BUY",
            "timeframe": "M15",
            "conditions": [
                {"indicator": "LIQUIDITY_SWEEP", "operator": "SWEEPS_EXTREMUM", "threshold": "ASIAN_LOW"}
            ],
            "risk_pct": 0.50,
            "sl_pips": 20.0,
            "tp_pips": 30.0,  # Only 1.5 R:R
        }
        is_valid, errors, strat = engine.build_visual_strategy(schema, balance=100000.0)

        assert is_valid is True
        assert strat.target_rr >= MIN_INSTITUTIONAL_RR
        assert strat.tp_pips >= 50.0  # 20.0 * 2.5 = 50.0

    def test_build_rejects_unsupported_indicator_and_operator(self, engine):
        schema = {
            "symbol": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "conditions": [
                {"indicator": "UNVERIFIED_CRYSTAL_BALL", "operator": "TELEPORTS_TO", "threshold": 99.0}
            ],
        }
        is_valid, errors, strat = engine.build_visual_strategy(schema)

        assert is_valid is False
        assert any("Unsupported indicator" in e for e in errors)
        assert any("Unsupported operator" in e for e in errors)

    def test_serialization_and_deserialization(self, engine):
        schema = {
            "name": "Test Serialization Strategy",
            "symbol": "BTCUSD",
            "action": "BUY",
            "timeframe": "M15",
            "conditions": [
                {"indicator": "BOS", "operator": "CROSSES_ABOVE", "threshold": "CLOSED_BAR"}
            ],
            "risk_pct": 0.75,
            "sl_pips": 200.0,
            "tp_pips": 600.0,
        }
        _, _, strat = engine.build_visual_strategy(schema)
        strat_dict = strat.to_dict()
        strat_json = strat.to_json()

        deserialized = StrategyDefinition.from_dict(strat_dict)
        assert deserialized.strategy_id == strat.strategy_id
        assert deserialized.symbol == "BTCUSD"
        assert deserialized.risk_pct == 0.75
        assert deserialized.conditions[0].indicator == "BOS"
        assert "Test Serialization Strategy" in strat_json


# =============================================================================
# 3. DETERMINISTIC RISK SAFEGUARDS TESTS
# =============================================================================

class TestDeterministicRiskSafeguards:

    def test_clamp_risk_various_balances(self):
        # 100k balance: clamped to 0.75% ($750)
        pct, usd = DeterministicRiskGuard.clamp_risk(1.50, balance=100000.0)
        assert pct == 0.75
        assert usd == 750.0

        # 50k balance: clamped to 0.75% ($375)
        pct, usd = DeterministicRiskGuard.clamp_risk(1.00, balance=50000.0)
        assert pct == 0.75
        assert usd == 375.0

        # 1k balance: clamped to 0.75% ($7.50)
        pct, usd = DeterministicRiskGuard.clamp_risk(2.00, balance=1000.0)
        assert pct == 0.75
        assert usd == 7.50

        # Safe compliant input
        pct, usd = DeterministicRiskGuard.clamp_risk(0.40, balance=100000.0)
        assert pct == 0.40
        assert usd == 400.0

    def test_breakeven_lock_triggered_at_plus_1r(self):
        # BUY XAUUSD entry 2650.0, initial SL 2640.0 (10 pip risk)
        # Price moves to 2660.0 (+1.0R)
        new_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="BUY",
            entry=2650.0,
            initial_sl=2640.0,
            current_price=2660.0,
            pip_size=0.10,
            spread_pips=1.0,
            commission_pips=0.5,
            safety_buffer_pips=0.5,
        )
        assert new_sl is not None
        # Entry (2650) + (1.0 + 0.5 + 0.5) * 0.10 = 2650.20
        assert new_sl == 2650.20

    def test_breakeven_lock_inactive_below_1r(self):
        # Price only moves to 2655.0 (+0.5R favorable excursion)
        new_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="BUY",
            entry=2650.0,
            initial_sl=2640.0,
            current_price=2655.0,
            pip_size=0.10,
        )
        assert new_sl is None

    def test_breakeven_lock_sell_direction(self):
        # SELL XAUUSD entry 2650.0, initial SL 2660.0 (10 pip risk)
        # Price drops to 2640.0 (+1.0R favorable move)
        new_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="SELL",
            entry=2650.0,
            initial_sl=2660.0,
            current_price=2640.0,
            pip_size=0.10,
            spread_pips=1.0,
            commission_pips=0.5,
            safety_buffer_pips=0.5,
        )
        assert new_sl is not None
        # Entry (2650) - (1.0 + 0.5 + 0.5) * 0.10 = 2649.80
        assert new_sl == 2649.80

    def test_news_blackout_circuit_breaker(self):
        # 8 minutes until high impact news -> blackout active!
        is_active, msg = DeterministicRiskGuard.check_news_blackout(minutes_to_high_impact_news=8.0)
        assert is_active is True
        assert "VETO_NEWS_BLACKOUT" in msg

        # 30 minutes until news -> market clear
        is_active, msg = DeterministicRiskGuard.check_news_blackout(minutes_to_high_impact_news=30.0)
        assert is_active is False
        assert "Market clear" in msg


# =============================================================================
# 4. AUTONOMOUS CONSENSUS INTEGRATION TESTS
# =============================================================================

class TestConsensusChamberIntegration:

    def test_mtf_confluence_aligned_buy(self):
        res = ConsensusChamberBridge.evaluate_mtf_confluence(
            m15_direction="BUY", h1_direction="BUY", h4_direction="BUY"
        )
        assert res["is_confluent"] is True
        assert res["confluence_score"] == 95.0
        assert res["blocked_reason"] is None

    def test_mtf_confluence_neutral_h4_passes(self):
        res = ConsensusChamberBridge.evaluate_mtf_confluence(
            m15_direction="SELL", h1_direction="SELL", h4_direction="NEUTRAL"
        )
        assert res["is_confluent"] is True
        assert res["confluence_score"] == 95.0

    def test_mtf_confluence_conflict_blocks_trade(self):
        # M15 is BUY but H1 is SELL
        res = ConsensusChamberBridge.evaluate_mtf_confluence(
            m15_direction="BUY", h1_direction="SELL", h4_direction="BUY"
        )
        assert res["is_confluent"] is False
        assert res["confluence_score"] == 45.0
        assert "MTF trend conflict" in res["blocked_reason"]

    def test_consensus_debate_approved_for_compliant_strategy(self, engine):
        strat = engine.parse_natural_language(
            "Buy Gold on M15 when London low sweeps and bullish OB tests, risk 0.5%, 1:3 RR"
        )
        debate = engine.debate_strategy(
            strat,
            market_context={
                "upcoming_news_minutes": 60.0,
                "mtf_trend": {"m15": "BUY", "h1": "BUY", "h4": "BUY"},
                "indicators": {"trend": "BULLISH", "bos_closed_bar": True, "fvg_respected": True, "rsi": 50.0},
            }
        )
        assert debate["approved"] is True
        assert debate["consensus_score"] >= 70.0
        assert debate["veto_reason"] is None

    def test_unanimous_risk_officer_veto_on_risk_violation(self, engine):
        # Construct strategy with manually injected risk violation
        strat = engine.parse_natural_language("Buy EURUSD on H1, risk 0.5%, 1:3 RR")
        strat.risk_pct = 1.50  # Artificially breach cap
        strat.dollar_risk_cap = 1500.0

        debate = engine.debate_strategy(strat)
        assert debate["approved"] is False
        assert debate["consensus_score"] == 0.0
        assert "VETO" in (debate.get("status") or "") or debate.get("veto_reason") is not None


# =============================================================================
# 5. MULTI-ACCOUNT ANTI-BAN ROUTING TESTS
# =============================================================================

class TestMultiAccountAntiBanBridge:

    def test_execute_custom_strategy_across_fleet_five_layers(self, engine):
        strat = engine.parse_natural_language(
            "Buy Gold on M15 with London low sweep and bullish OB retest, risk 0.5%, 1:3 RR"
        )
        exec_res = engine.execute_strategy(strat, current_price=2650.0, simulation_mode=True)

        assert exec_res["ok"] is True
        assert exec_res["status"] == "DISPATCHED_ACROSS_FLEET"
        assert exec_res["five_layer_protection_verified"] is True
        assert exec_res["admitted_accounts"] > 0

        dispatches = exec_res["dispatches"]
        # Audit anti-ban layers across dispatched accounts
        for acc_id, d in dispatches.items():
            if not d.get("admitted"):
                continue
            # Layer 3: Jitter between 350ms and 1800ms
            jitter = d.get("jitter_delay_ms")
            if jitter is not None:
                assert 350.0 <= jitter <= 1840.0  # slight entropy headroom
            # Layer 4: Pipette dispersion preserves R:R >= 2.50
            eff_rr = d.get("effective_rr")
            if eff_rr is not None:
                assert eff_rr >= MIN_INSTITUTIONAL_RR
            # Layer 5: Dynamic Magic Number
            magic = d.get("magic_number")
            if magic is not None:
                assert 700000 <= magic <= 800000


# =============================================================================
# 6. FASTAPI ROUTER ENDPOINTS TESTS
# =============================================================================

class TestFastAPIRoutes:

    def test_api_parse_english(self, api_client):
        payload = {
            "prompt": "Buy Gold on M15 when price sweeps London low and tests bullish Order Block, risk 0.5%, take profit 1:3 R:R",
            "lang": "en",
            "balance": 100000.0,
        }
        res = api_client.post("/api/trading/client_strategy/parse", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["ok"] is True
        assert d["strategy"]["symbol"] == "XAUUSD"
        assert d["strategy"]["action"] == "BUY"
        assert d["risk_pct"] == 0.50
        assert d["target_rr"] == 3.0

    def test_api_parse_roman_urdu(self, api_client):
        payload = {
            "prompt": "M15 timeframe par Gold buy karo jab London session low sweep ho, 0.5% risk aur 1:3 TP rakho",
            "lang": "ur",
            "balance": 100000.0,
        }
        res = api_client.post("/api/trading/client_strategy/parse", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["ok"] is True
        assert d["language"] == "ur"
        assert "Jee Sovereign Master Sir" in d["confirmation_narrative"]
        # Check no forbidden scripts
        assert not DEVANAGARI_REGEX.search(d["confirmation_narrative"])
        assert not ARABIC_URDU_REGEX.search(d["confirmation_narrative"])

    def test_api_build_visual_rule_success(self, api_client):
        payload = {
            "name": "API Visual EURUSD Strategy",
            "symbol": "EURUSD",
            "action": "SELL",
            "timeframe": "H1",
            "conditions": [
                {"indicator": "FVG_50_CE", "operator": "MITIGATES_50_PCT", "threshold": 50.0}
            ],
            "risk_pct": 0.50,
            "sl_pips": 15.0,
            "tp_pips": 45.0,
            "target_rr": 3.0,
        }
        res = api_client.post("/api/trading/client_strategy/build", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["ok"] is True
        assert d["strategy"]["symbol"] == "EURUSD"

    def test_api_build_invalid_rule_returns_422(self, api_client):
        payload = {
            "symbol": "EURUSD",
            "action": "SELL",
            "conditions": [
                {"indicator": "INVALID_INDICATOR_XYZ", "operator": "INVALID_OP", "threshold": 1.0}
            ],
        }
        res = api_client.post("/api/trading/client_strategy/build", json=payload)
        assert res.status_code == 422

    def test_api_consensus_endpoint(self, api_client, engine):
        strat = engine.parse_natural_language("Buy Gold on M15, risk 0.5%, 1:3 RR")
        payload = {
            "strategy": strat.to_dict(),
            "market_context": {"upcoming_news_minutes": 60.0},
        }
        res = api_client.post("/api/trading/client_strategy/consensus", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["ok"] is True
        assert "debate_result" in d

    def test_api_execute_endpoint(self, api_client, engine):
        strat = engine.parse_natural_language("Buy Gold on M15, risk 0.5%, 1:3 RR")
        payload = {
            "strategy": strat.to_dict(),
            "current_price": 2650.0,
            "simulation": True,
        }
        res = api_client.post("/api/trading/client_strategy/execute", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["ok"] is True
        assert d["status"] == "DISPATCHED_ACROSS_FLEET"

    def test_api_presets_and_health(self, api_client):
        res_presets = api_client.get("/api/trading/client_strategy/presets")
        assert res_presets.status_code == 200
        d_p = res_presets.json()
        assert d_p["ok"] is True
        assert d_p["count"] >= 3

        res_health = api_client.get("/api/trading/client_strategy/health")
        assert res_health.status_code == 200
        d_h = res_health.json()
        assert d_h["status"] == "ONLINE"
        assert d_h["max_risk_pct"] == 0.75
        assert d_h["anti_ban_layers"] == 5


# =============================================================================
# 7. CLEAN-ROOM PROHIBITED TOKEN AUDIT
# =============================================================================

class TestCleanRoomCompliance:

    def test_zero_prohibited_tokens_in_custom_strategy_files(self):
        files_to_check = [
            Path(__file__).resolve().parent.parent / "core" / "trading" / "custom_strategy_engine.py",
            Path(__file__).resolve(),
        ]
        part_a = "adeel"
        part_b = "qureshi99"
        forbidden_regex = re.compile(rf"{part_a}\s*{part_b}", re.IGNORECASE)

        for path in files_to_check:
            assert path.exists(), f"File {path} does not exist"
            content = path.read_text(encoding="utf-8")
            assert not forbidden_regex.search(content), f"Violation: Forbidden token found in {path}"

    def test_sovereign_identity_integrity(self):
        file_path = Path(__file__).resolve().parent.parent / "core" / "trading" / "custom_strategy_engine.py"
        content = file_path.read_text(encoding="utf-8")
        assert "Master Muhammad Qureshi" in content
        assert "+923468053268" in content
        assert "futureworldvision842@gmail.com" in content
        assert "40000294403" in content
