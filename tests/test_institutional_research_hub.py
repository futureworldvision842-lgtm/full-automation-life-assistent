"""
test_institutional_research_hub.py — Verification Suite for Institutional Market Research Hub (R1).
Tests:
  1. GET /api/research/forex/macro (CSM 28-pair, Central Bank Rate Differentials, 15-min Blackout Buffer).
  2. GET /api/research/crypto/memes (Solana Raydium & Pump.fun Alpha Stream, bonding curve %, whale index, safety score).
  3. GET /api/research/crypto/gems (Spot Crypto Fundamental Dossiers: drawdowns, tokenomics, commits, staking, valuation).
  4. Unit math tests for CurrencyStrengthMeter, CentralBankRateMatrix, EconomicNewsBlackoutManager, MemeAlphaStreamer, SpotCryptoDossierEngine.
  5. Dashboard route mounting and unauthenticated access via exempt_paths.
"""

import pytest
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient

from dashboard import app
from core.research.macro_surveillance import (
    CurrencyStrengthMeter,
    CentralBankRateMatrix,
    EconomicNewsBlackoutManager,
    MacroSurveillanceEngine,
    MAJOR_CURRENCIES,
    PAIRS_28,
)
from core.research.meme_alpha_stream import MemeAlphaStreamer
from core.research.spot_crypto_dossier import SpotCryptoDossierEngine


@pytest.fixture(scope="module")
def client():
    """Starlette TestClient bound to the full JARVIS Command Center dashboard."""
    return TestClient(app)


# =============================================================================
# UNIT TESTS: MACRO SURVEILLANCE & CSM
# =============================================================================

def test_currency_strength_meter_structure_and_bounds():
    """Validates that CSM evaluates 28 pairs and yields 0.0-10.0 scores for all 8 major currencies."""
    csm = CurrencyStrengthMeter()
    result = csm.calculate_strength()

    assert "currency_strength" in result
    assert "rankings" in result
    assert "strongest" in result
    assert "weakest" in result
    assert result["pairs_evaluated"] == 28

    scores = result["currency_strength"]
    for curr in MAJOR_CURRENCIES:
        assert curr in scores, f"Missing currency: {curr}"
        score = scores[curr]
        assert 0.0 <= score <= 10.0, f"Score out of bounds for {curr}: {score}"

    assert len(result["rankings"]) == 8
    # Top ranked should equal strongest
    assert result["rankings"][0]["currency"] == result["strongest"]["currency"]


def test_currency_strength_meter_relative_movement():
    """Validates that positive movement in USD pairs boosts USD strength and depresses quote currencies."""
    csm = CurrencyStrengthMeter()
    # Simulate a massive USD surge
    pair_changes = {
        "EURUSD": -1.5,
        "GBPUSD": -1.5,
        "USDJPY": +2.0,
        "USDCHF": +1.5,
        "USDCAD": +1.5,
        "AUDUSD": -2.0,
        "NZDUSD": -2.0,
    }
    result = csm.calculate_strength(pair_changes=pair_changes)
    scores = result["currency_strength"]

    # USD must be significantly stronger than EUR, GBP, AUD, NZD
    assert scores["USD"] > scores["EUR"]
    assert scores["USD"] > scores["AUD"]
    assert scores["USD"] >= 7.0


def test_central_bank_rate_matrix_differentials():
    """Validates policy rate differentials for Fed, ECB, BoE, and BoJ."""
    matrix_eng = CentralBankRateMatrix()
    res = matrix_eng.compute_matrix()

    assert "policy_rates" in res
    assert "rate_differentials" in res
    assert "pair_carry_matrix" in res

    diffs = res["rate_differentials"]
    # Check core central banks
    assert diffs["FED_ECB"] == pytest.approx(1.75, abs=0.01)  # 5.50 - 3.75
    assert diffs["FED_BOJ"] == pytest.approx(5.25, abs=0.01)  # 5.50 - 0.25
    assert diffs["BOE_BOJ"] == pytest.approx(4.75, abs=0.01)  # 5.00 - 0.25

    carry = res["pair_carry_matrix"]
    assert "USD/JPY" in carry
    assert carry["USD/JPY"]["spread_pct"] == pytest.approx(5.25, abs=0.01)
    assert carry["USD/JPY"]["carry_bias"] == "STRONG_CARRY_LONG"

    assert "EUR/USD" in carry
    assert carry["EUR/USD"]["spread_pct"] == pytest.approx(-1.75, abs=0.01)
    assert carry["EUR/USD"]["carry_bias"] == "MILD_CARRY_SHORT"


def test_economic_news_blackout_buffer_logic():
    """Validates deterministic 15-minute Pre-News and Post-News trading blackout buffer."""
    blackout_mgr = EconomicNewsBlackoutManager(
        blackout_minutes_before=15,
        blackout_minutes_after=15,
        include_reference_events=False
    )
    blackout_mgr.clear_injected_events()

    now_utc = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Inactive when event is 30 minutes away
    blackout_mgr.inject_event(
        title="US Non-Farm Payrolls",
        currency="USD",
        event_time_utc=now_utc + timedelta(minutes=30),
        impact="HIGH"
    )
    status_30m = blackout_mgr.evaluate_blackout_status(symbol="EURUSD", now=now_utc)
    assert status_30m["blackout_active"] is False

    # 2. Active when event is 10 minutes away (Pre-News Blackout)
    blackout_mgr.clear_injected_events()
    blackout_mgr.inject_event(
        title="FOMC Interest Rate Decision",
        currency="USD",
        event_time_utc=now_utc + timedelta(minutes=10),
        impact="HIGH"
    )
    status_10m = blackout_mgr.evaluate_blackout_status(symbol="EURUSD", now=now_utc)
    assert status_10m["blackout_active"] is True
    assert "PRE_NEWS_BLACKOUT" in status_10m["blackout_reason"]
    assert status_10m["minutes_remaining"] == pytest.approx(25.0, abs=0.1)  # 10m until + 15m post

    # 3. Active when event occurred 8 minutes ago (Post-News Blackout)
    blackout_mgr.clear_injected_events()
    blackout_mgr.inject_event(
        title="US CPI YoY",
        currency="USD",
        event_time_utc=now_utc - timedelta(minutes=8),
        impact="HIGH"
    )
    status_post8m = blackout_mgr.evaluate_blackout_status(symbol="EURUSD", now=now_utc)
    assert status_post8m["blackout_active"] is True
    assert "POST_NEWS_BLACKOUT" in status_post8m["blackout_reason"]
    assert status_post8m["minutes_remaining"] == pytest.approx(7.0, abs=0.1)  # 15m - 8m

    # 4. Cleared when event occurred 20 minutes ago
    blackout_mgr.clear_injected_events()
    blackout_mgr.inject_event(
        title="US CPI YoY",
        currency="USD",
        event_time_utc=now_utc - timedelta(minutes=20),
        impact="HIGH"
    )
    status_post20m = blackout_mgr.evaluate_blackout_status(symbol="EURUSD", now=now_utc)
    assert status_post20m["blackout_active"] is False


# =============================================================================
# UNIT TESTS: MEME ALPHA STREAMER
# =============================================================================

def test_meme_alpha_streamer_schema_and_scoring():
    """Validates that MemeAlphaStreamer produces scored tokens matching the interface contract."""
    streamer = MemeAlphaStreamer()
    tokens = streamer.get_scored_tokens(limit=10)

    assert len(tokens) > 0
    for t in tokens:
        # Interface Contract required fields
        assert "symbol" in t and isinstance(t["symbol"], str)
        assert "address" in t and isinstance(t["address"], str)
        assert "bonding_curve_pct" in t and isinstance(t["bonding_curve_pct"], (int, float))
        assert "whale_accumulation_index" in t and isinstance(t["whale_accumulation_index"], (int, float))
        assert "safety_score" in t and isinstance(t["safety_score"], int)
        assert "dev_audit" in t and isinstance(t["dev_audit"], dict)

        # Extended fields
        assert 0.0 <= t["bonding_curve_pct"] <= 100.0
        assert 0.0 <= t["whale_accumulation_index"] <= 100.0
        assert 0 <= t["safety_score"] <= 100
        assert 0.0 <= t["composite_conviction_score"] <= 100.0

        # Dev audit fields
        dev = t["dev_audit"]
        assert "dev_holding_pct" in dev
        assert "dev_dump_detected" in dev
        assert "lp_burn_lock_verified" in dev
        assert "mint_authority_revoked" in dev


def test_meme_alpha_streamer_filtering():
    """Validates filtering by minimum score, graduating curve, and whale accumulation."""
    streamer = MemeAlphaStreamer()
    all_tokens = streamer.get_scored_tokens(min_score=0.0)

    high_conviction = streamer.get_scored_tokens(min_score=80.0)
    for t in high_conviction:
        assert t["composite_conviction_score"] >= 80.0

    graduating = streamer.get_scored_tokens(graduating_only=True)
    for t in graduating:
        assert t["bonding_curve_pct"] >= 75.0


# =============================================================================
# UNIT TESTS: SPOT CRYPTO DOSSIER ENGINE
# =============================================================================

def test_spot_crypto_dossiers_comprehensiveness():
    """Validates that SpotCryptoDossierEngine covers 10 prospective assets with complete metrics."""
    engine = SpotCryptoDossierEngine()
    dossiers = engine.get_dossiers()

    expected_assets = {"SOL", "BTC", "ETH", "NEAR", "SUI", "RENDER", "TAO", "INJ", "LINK", "AAVE"}
    actual_symbols = {d["symbol"] for d in dossiers}
    assert expected_assets.issubset(actual_symbols), f"Missing assets: {expected_assets - actual_symbols}"

    for d in dossiers:
        # Interface Contract required fields
        assert "symbol" in d and isinstance(d["symbol"], str)
        assert "name" in d and isinstance(d["name"], str)
        assert "drawdowns" in d and isinstance(d["drawdowns"], dict)
        assert "tokenomics" in d and isinstance(d["tokenomics"], dict)
        assert "commits" in d and isinstance(d["commits"], dict)
        assert "staking_yield" in d and isinstance(d["staking_yield"], (int, float))
        assert "valuation_percentile" in d and isinstance(d["valuation_percentile"], (int, float))

        # Check Drawdown Distribution fields
        dd = d["drawdowns"]
        assert "ath_price_usd" in dd
        assert "drawdown_from_ath_pct" in dd
        assert "max_cycle_drawdown_pct" in dd
        assert "historical_recovery_days_p50" in dd
        assert dd["drawdown_from_ath_pct"] <= 0.0

        # Check Tokenomics fields
        tok = d["tokenomics"]
        assert "circulating_supply" in tok
        assert "circulating_pct" in tok
        assert "annual_inflation_rate_pct" in tok
        assert "upcoming_unlocks" in tok

        # Check Commit Activity fields
        com = d["commits"]
        assert "github_commits_30d" in com
        assert "core_active_developers_monthly" in com
        assert "developer_ecosystem_rank" in com

        # Check Valuation fields
        assert 0.0 <= d["valuation_percentile"] <= 100.0
        val = d["valuation"]
        assert "composite_fundamental_score" in val
        assert 0.0 <= val["composite_fundamental_score"] <= 100.0


def test_spot_crypto_dossiers_symbol_filtering():
    """Validates retrieval of single assets like SOL or TAO."""
    engine = SpotCryptoDossierEngine()
    sol_dossier = engine.get_dossiers(symbol="SOL")
    assert len(sol_dossier) == 1
    assert sol_dossier[0]["symbol"] == "SOL"
    assert sol_dossier[0]["name"] == "Solana"
    assert sol_dossier[0]["staking_yield"] == 6.85

    tao_dossier = engine.get_dossiers(symbol="TAO")
    assert len(tao_dossier) == 1
    assert tao_dossier[0]["symbol"] == "TAO"
    assert tao_dossier[0]["category"] == "Decentralized Machine Intelligence / AI Subnets"


# =============================================================================
# INTEGRATION TESTS: FASTAPI ENDPOINTS VIA DASHBOARD TESTCLIENT
# =============================================================================

def test_api_research_forex_macro_endpoint(client):
    """GET /api/research/forex/macro returns 200 and matches interface contract."""
    response = client.get("/api/research/forex/macro")
    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert "currency_strength" in data
    assert "rate_differentials" in data
    assert "blackout_active" in data
    assert "upcoming_events" in data

    # Check 8 major currencies
    for c in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]:
        assert c in data["currency_strength"]

    # Check rate differentials
    assert "FED_ECB" in data["rate_differentials"]
    assert "FED_BOJ" in data["rate_differentials"]
    assert isinstance(data["blackout_active"], bool)


def test_api_research_crypto_memes_endpoint(client):
    """GET /api/research/crypto/memes returns 200 and matches interface contract."""
    response = client.get("/api/research/crypto/memes?limit=15")
    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert "tokens" in data
    assert isinstance(data["tokens"], list)
    assert len(data["tokens"]) > 0

    first = data["tokens"][0]
    assert "symbol" in first
    assert "address" in first
    assert "bonding_curve_pct" in first
    assert "whale_accumulation_index" in first
    assert "safety_score" in first
    assert "dev_audit" in first


def test_api_research_crypto_gems_endpoint(client):
    """GET /api/research/crypto/gems returns 200 and matches interface contract."""
    response = client.get("/api/research/crypto/gems")
    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert "gems" in data
    assert isinstance(data["gems"], list)
    assert len(data["gems"]) >= 10

    # Specific symbol filter
    resp_sol = client.get("/api/research/crypto/gems?symbol=SOL")
    assert resp_sol.status_code == 200
    data_sol = resp_sol.json()
    assert len(data_sol["gems"]) == 1
    assert data_sol["gems"][0]["symbol"] == "SOL"


def test_api_research_health_endpoint(client):
    """GET /api/research/health returns 200 OK."""
    response = client.get("/api/research/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
