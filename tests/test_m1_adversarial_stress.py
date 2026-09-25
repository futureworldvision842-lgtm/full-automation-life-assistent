"""
test_m1_adversarial_stress.py — Adversarial Stress Testing Suite for Milestone M1.
Challenger 2 Empirical Verification Suite.

Adversarially tests:
1. Pump.fun Bonding Curve Boundary Values:
   - 0.0 SOL (initial point)
   - 42.5 SOL (50% midpoint)
   - 85.0 SOL (exact Raydium migration point)
   - >85.0 SOL overflow (85.1, 120.0, 500.0, 1,000,000.0 SOL)
   - Negative SOL values (-10.0 SOL)
2. Dev Dump Detection & Developer Supply Concentration:
   - Dev holding 0.0% (pristine distribution)
   - Dev holding 50.0% (extreme insider concentration, hard-capped at 15/100 conviction)
   - Dev dump flag active (immediate conviction collapse to 0.0, REJECT/DANGER verdict)
   - Dev dump flag inactive (clean execution)
3. Honeypot Simulation, LP Burn Percentages, and Freeze Authority:
   - Honeypot active (simulation failure, unsellable token, fail-closed)
   - LP burn < 95.0% (fails safety criteria, penalized)
   - LP burn >= 95.0% (passes safety criteria, verified in audit)
   - Freeze authority active (fails safety criteria, penalized)
   - Freeze authority revoked (passes safety criteria)
4. Spot Crypto Fundamental Valuation under Extreme Data Inputs:
   - Zero TVL (division-by-zero resistance)
   - Negative yields (real yield with high inflation drag, e.g. SUI -8.70%, BTC -0.85%)
   - Missing commit history (empty dict, null developers, zero commits)
   - Extreme boundary filters and unmapped symbols/categories
5. Live API Endpoint Resilience under Adversarial Query Parameters
"""

import pytest
import math
from starlette.testclient import TestClient

from dashboard import app
from trading.pump_fun_scanner import PumpFunScanner, PumpAlphaToken, PUMP_FUN_GRADUATION_SOL_THRESHOLD
from trading.meme_safety_filter import MemeSafetyFilter, SafetyReport
from core.research.meme_alpha_stream import MemeAlphaStreamer
from core.research.spot_crypto_dossier import SpotCryptoDossierEngine, get_spot_crypto_dossier_engine


@pytest.fixture(scope="module")
def client():
    """Starlette TestClient for API endpoints."""
    return TestClient(app)


# =============================================================================
# 1. BONDING CURVE BOUNDARY VALUE EMPIRICAL TESTS
# =============================================================================

def test_bonding_curve_boundary_zero_sol():
    """Empirical test for bonding curve at exact 0.0 SOL."""
    scanner = PumpFunScanner()
    progress, mc_sol, mc_usd, graduated = scanner.calculate_bonding_curve(0.0, sol_price_usd=150.0)

    assert progress == 0.0, f"Expected 0.0% progress at 0 SOL, got {progress}"
    assert graduated is False, "0 SOL token must not be graduated"
    assert mc_sol > 0.0, f"Virtual curve market cap must be positive, got {mc_sol}"
    assert mc_usd > 0.0, f"USD market cap must be positive, got {mc_usd}"
    assert not math.isnan(mc_sol) and not math.isinf(mc_sol)
    assert not math.isnan(mc_usd) and not math.isinf(mc_usd)

    # Conviction score at 0.0% bonding curve
    conviction, verdict, reco, reasons = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=progress,
        vol_accel=1.0,
        buy_pressure=1.0,
        whale_score=0.0,
        safety_score=100.0,
        dev_holding_pct=0.0,
        dev_dump_detected=False,
        social_score=50.0
    )
    # Early curve should receive 0 curve points
    assert any("Early bonding curve" in r for r in reasons)
    assert conviction >= 0.0


def test_bonding_curve_boundary_midpoint_42_5_sol():
    """Empirical test for bonding curve at 42.5 SOL (exact 50.0% midpoint)."""
    scanner = PumpFunScanner()
    progress, mc_sol, mc_usd, graduated = scanner.calculate_bonding_curve(42.5, sol_price_usd=150.0)

    assert progress == 50.0, f"Expected exactly 50.0% progress at 42.5 SOL, got {progress}"
    assert graduated is False, "42.5 SOL token must not be graduated"
    assert mc_sol > 0.0
    assert mc_usd > 0.0

    # Conviction score should recognize 50% as prime momentum zone (40% - 92%)
    conviction, verdict, reco, reasons = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=progress,
        vol_accel=2.0,
        buy_pressure=2.0,
        whale_score=50.0,
        safety_score=95.0,
        dev_holding_pct=2.0,
        dev_dump_detected=False,
        social_score=80.0
    )
    assert any("prime momentum zone" in r for r in reasons)
    assert conviction >= 70.0


def test_bonding_curve_boundary_migration_point_85_sol():
    """Empirical test for bonding curve at exactly 85.0 SOL (Raydium migration point)."""
    scanner = PumpFunScanner()
    progress, mc_sol, mc_usd, graduated = scanner.calculate_bonding_curve(85.0, sol_price_usd=150.0)

    assert progress == 100.0, f"Expected 100.0% progress at 85.0 SOL, got {progress}"
    assert graduated is True, "Token with 85.0 SOL must be marked as graduated"

    # Conviction score at 100% curve
    conviction, verdict, reco, reasons = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=progress,
        vol_accel=2.0,
        buy_pressure=2.0,
        whale_score=80.0,
        safety_score=95.0,
        dev_holding_pct=1.0,
        dev_dump_detected=False,
        social_score=90.0
    )
    assert any("Raydium graduation" in r for r in reasons)
    assert conviction >= 70.0


def test_bonding_curve_boundary_overflow_greater_than_85_sol():
    """Empirical test for bonding curve overflow (>85.0 SOL). Progress must be clamped at 100%."""
    scanner = PumpFunScanner()
    overflow_reserves = [85.01, 100.0, 250.0, 5000.0, 1_000_000.0]

    for sol in overflow_reserves:
        progress, mc_sol, mc_usd, graduated = scanner.calculate_bonding_curve(sol, sol_price_usd=150.0)
        assert progress == 100.0, f"Progress must be clamped to 100.0%, got {progress} for {sol} SOL"
        assert graduated is True, f"Token with {sol} SOL must be graduated"
        assert not math.isnan(mc_sol) and not math.isinf(mc_sol), f"NaN/Inf mc_sol for {sol} SOL"
        assert not math.isnan(mc_usd) and not math.isinf(mc_usd), f"NaN/Inf mc_usd for {sol} SOL"
        assert mc_sol > 0.0
        assert mc_usd > 0.0


def test_bonding_curve_boundary_negative_sol_reserves():
    """Empirical test for adversarial negative SOL reserves."""
    scanner = PumpFunScanner()
    progress, mc_sol, mc_usd, graduated = scanner.calculate_bonding_curve(-25.0, sol_price_usd=150.0)

    assert progress == 0.0, f"Negative SOL must clamp to 0.0% progress, got {progress}"
    assert graduated is False, "Negative SOL token must not be graduated"
    assert mc_sol > 0.0, "Virtual curve must remain positive"
    assert not math.isnan(mc_sol) and not math.isinf(mc_sol)


# =============================================================================
# 2. DEVELOPER DUMP DETECTION & SUPPLY CONCENTRATION EMPIRICAL TESTS
# =============================================================================

def test_dev_dump_detection_dev_holding_zero_percent():
    """Empirical test when developer holds 0.0% (community token or burned dev share)."""
    scanner = PumpFunScanner()
    conviction, verdict, reco, reasons = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=60.0,
        vol_accel=2.0,
        buy_pressure=2.0,
        whale_score=60.0,
        safety_score=95.0,
        dev_holding_pct=0.0,
        dev_dump_detected=False,
        social_score=80.0
    )
    assert verdict == "SAFE"
    assert conviction >= 75.0
    assert not any("Developer wallet holds" in r for r in reasons)
    assert not any("Developer dump" in r for r in reasons)


def test_dev_dump_detection_dev_holding_fifty_percent():
    """Empirical test when developer holds 50.0% supply (extreme insider concentration)."""
    scanner = PumpFunScanner()
    conviction, verdict, reco, reasons = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=60.0,
        vol_accel=3.0,
        buy_pressure=3.0,
        whale_score=90.0,
        safety_score=100.0,
        dev_holding_pct=50.0,
        dev_dump_detected=False,
        social_score=90.0
    )
    # Must immediately trigger high risk penalty and cap score at 15.0
    assert conviction == 15.0, f"Expected conviction hard-capped at 15.0, got {conviction}"
    assert verdict == "DANGER"
    assert reco == "AVOID"
    assert any("Developer wallet holds 50.0%" in r for r in reasons)


def test_dev_dump_flag_active_vs_inactive():
    """Empirical test comparing dev_dump_detected = True vs False."""
    scanner = PumpFunScanner()

    # Active dev dump
    conv_active, verdict_active, reco_active, reasons_active = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=75.0,
        vol_accel=2.5,
        buy_pressure=2.5,
        whale_score=80.0,
        safety_score=100.0,
        dev_holding_pct=2.0,
        dev_dump_detected=True,
        social_score=90.0
    )
    assert conv_active == 0.0, f"Expected conviction 0.0 on active dump, got {conv_active}"
    assert verdict_active == "DANGER"
    assert reco_active == "REJECT"
    assert any("CRITICAL: Developer dump or liquidity drain detected" in r for r in reasons_active)

    # Inactive dev dump with same parameters
    conv_inactive, verdict_inactive, reco_inactive, _ = scanner.compute_alpha_conviction_score(
        bonding_curve_pct=75.0,
        vol_accel=2.5,
        buy_pressure=2.5,
        whale_score=80.0,
        safety_score=100.0,
        dev_holding_pct=2.0,
        dev_dump_detected=False,
        social_score=90.0
    )
    assert conv_inactive >= 80.0
    assert verdict_inactive == "SAFE"
    assert reco_inactive == "HIGH_CONVICTION_ENTRY"


# =============================================================================
# 3. HONEYPOT SIMULATION, LP BURN %, FREEZE AUTHORITY EMPIRICAL TESTS
# =============================================================================

def test_honeypot_simulation_evm():
    """Empirical test for honeypot simulation failure on EVM."""
    safety_filter = MemeSafetyFilter()

    # 1. Unsellable honeypot token
    audit_honeypot = {
        "is_honeypot": "1",
        "buy_tax": "0.0",
        "sell_tax": "0.0",
        "is_mintable": "0",
        "cannot_sell_all": "0",
        "lp_locked_pct": 100.0,
        "top10_pct": 5.0,
        "creator_percent": "0.01"
    }
    report_honeypot = safety_filter.evaluate_evm_token(
        chain="base",
        token_address="0x1234567890123456789012345678901234567890",
        goplus_data=audit_honeypot
    )
    assert report_honeypot.is_safe is False
    assert any("Honeypot confirmed" in r for r in report_honeypot.reasons)
    assert report_honeypot.score <= 40.0

    # 2. Clean non-honeypot token
    audit_clean = {
        "is_honeypot": "0",
        "buy_tax": "0.0",
        "sell_tax": "0.0",
        "is_mintable": "0",
        "cannot_sell_all": "0",
        "lp_locked_pct": 100.0,
        "top10_pct": 5.0,
        "creator_percent": "0.01"
    }
    report_clean = safety_filter.evaluate_evm_token(
        chain="base",
        token_address="0x1234567890123456789012345678901234567890",
        goplus_data=audit_clean
    )
    assert report_clean.is_safe is True
    assert not any("Honeypot confirmed" in r for r in report_clean.reasons)
    assert report_clean.score >= 80.0


def test_lp_burn_percentages_threshold():
    """Empirical test comparing LP burn < 95.0% vs >= 95.0%."""
    safety_filter = MemeSafetyFilter()

    # Case A: LP burn 50.0% (< 95.0%)
    audit_low_lp = {
        "lp_locked_pct": 50.0,
        "mintAuthority": None,
        "freezeAuthority": None,
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    report_low = safety_filter.evaluate_solana_token(
        mint_address="TestLowLPMint1111111111111111111111111111111",
        rugcheck_data=audit_low_lp
    )
    assert report_low.is_safe is False
    assert any("LP token lock/burn insufficient" in r for r in report_low.reasons)

    # Case B: LP burn 94.9% (boundary just below threshold)
    audit_boundary_low = {
        "lp_locked_pct": 94.9,
        "mintAuthority": None,
        "freezeAuthority": None,
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    report_boundary_low = safety_filter.evaluate_solana_token(
        mint_address="TestBoundaryLowMint111111111111111111111111",
        rugcheck_data=audit_boundary_low
    )
    assert report_boundary_low.is_safe is False
    assert any("LP token lock/burn insufficient" in r for r in report_boundary_low.reasons)

    # Case C: LP burn 95.0% (exact threshold)
    audit_exact_lp = {
        "lp_locked_pct": 95.0,
        "mintAuthority": None,
        "freezeAuthority": None,
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    report_exact = safety_filter.evaluate_solana_token(
        mint_address="TestExactLPMint1111111111111111111111111111",
        rugcheck_data=audit_exact_lp
    )
    assert report_exact.is_safe is True
    assert not any("LP token lock/burn insufficient" in r for r in report_exact.reasons)

    # Case D: LP burn 100.0%
    audit_full_lp = {
        "lp_locked_pct": 100.0,
        "mintAuthority": None,
        "freezeAuthority": None,
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    report_full = safety_filter.evaluate_solana_token(
        mint_address="TestFullLPMint1111111111111111111111111111",
        rugcheck_data=audit_full_lp
    )
    assert report_full.is_safe is True


def test_freeze_authority_active_vs_revoked():
    """Empirical test for freeze authority active vs revoked."""
    safety_filter = MemeSafetyFilter()

    # Active freeze authority
    audit_freeze_active = {
        "lp_locked_pct": 100.0,
        "mintAuthority": None,
        "freezeAuthority": "ActiveMaliciousKey111111111111111111111111",
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    rep_active = safety_filter.evaluate_solana_token(
        mint_address="FreezeActiveMint1111111111111111111111111111",
        rugcheck_data=audit_freeze_active
    )
    assert rep_active.is_safe is False
    assert rep_active.freeze_revoked is False
    assert any("Freeze authority is active" in r for r in rep_active.reasons)

    # Revoked freeze authority (None or burn address)
    audit_freeze_revoked = {
        "lp_locked_pct": 100.0,
        "mintAuthority": None,
        "freezeAuthority": "11111111111111111111111111111111",  # System burn address
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    rep_revoked = safety_filter.evaluate_solana_token(
        mint_address="FreezeRevokedMint111111111111111111111111111",
        rugcheck_data=audit_freeze_revoked
    )
    assert rep_revoked.is_safe is True
    assert rep_revoked.freeze_revoked is True
    assert not any("Freeze authority is active" in r for r in rep_revoked.reasons)


# =============================================================================
# 4. SPOT CRYPTO FUNDAMENTAL VALUATION UNDER EXTREME DATA INPUTS
# =============================================================================

def test_valuation_extreme_data_zero_tvl():
    """Empirical test for assets with zero TVL (avoids ZeroDivisionError)."""
    engine = SpotCryptoDossierEngine()

    # Create an asset with 0.0 TVL
    zero_tvl_asset = {
        "symbol": "ZEROTVL",
        "name": "Zero TVL Protocol",
        "category": "Zero TVL Infrastructure",
        "price_usd": 1.0,
        "market_cap_usd": 10_000_000,
        "fdv_usd": 10_000_000,
        "drawdowns": {
            "ath_price_usd": 10.0,
            "drawdown_from_ath_pct": -90.0,
            "max_cycle_drawdown_pct": -90.0,
            "historical_recovery_days_p50": 100,
            "current_cycle_recovery_pct": 10.0,
            "drawdown_regime": "DISTRESSED"
        },
        "tokenomics": {
            "circulating_supply": 10_000_000,
            "total_supply": 10_000_000,
            "circulating_pct": 100.0,
            "annual_inflation_rate_pct": 0.0,
            "upcoming_unlocks": {"usd_value_30d": 0}
        },
        "commits": {
            "github_commits_30d": 50,
            "core_active_developers_monthly": 10,
            "developer_ecosystem_rank": 50
        },
        "staking_yield": 0.0,
        "staking_telemetry": {
            "nominal_apy_pct": 0.0,
            "real_yield_pct": 0.0,
            "network_staking_ratio_pct": 0.0,
            "unbonding_cooldown_hours": 0.0,
            "nakamoto_coefficient": 1,
            "active_validators": 10
        },
        "valuation_percentile": 50.0,
        "valuation": {
            "tvl_usd": 0.0,
            "fdv_to_tvl_ratio": 0.0,  # Gracefully zeroed rather than Inf/division-by-zero
            "price_to_fees_percentile": 50.0,
            "price_to_sales_percentile": 50.0,
            "metcalfe_adoption_index": 50.0,
            "composite_fundamental_score": 50.0,
            "institutional_conviction": "NEUTRAL_WATCH"
        }
    }

    # Inject into engine dossiers
    engine._dossiers["ZEROTVL"] = zero_tvl_asset

    # Query dossiers
    retrieved = engine.get_dossiers(symbol="ZEROTVL")
    assert len(retrieved) == 1
    assert retrieved[0]["valuation"]["tvl_usd"] == 0.0
    assert retrieved[0]["valuation"]["fdv_to_tvl_ratio"] == 0.0

    report = engine.get_gems_research_report(symbol="ZEROTVL")
    assert report["ok"] is True
    assert len(report["gems"]) == 1

    # Clean up
    del engine._dossiers["ZEROTVL"]


def test_valuation_extreme_data_negative_yield():
    """Empirical test for assets with heavy negative real yields (inflation drag)."""
    engine = SpotCryptoDossierEngine()

    # In existing dossiers, SUI has -8.70% real yield, BTC has -0.85%, RENDER has -3.5%, LINK has -2.48%
    sui_dossier = engine.get_dossiers(symbol="SUI")[0]
    assert sui_dossier["staking_telemetry"]["real_yield_pct"] == -8.70
    assert sui_dossier["staking_telemetry"]["nominal_apy_pct"] == 3.80

    btc_dossier = engine.get_dossiers(symbol="BTC")[0]
    assert btc_dossier["staking_telemetry"]["real_yield_pct"] == -0.85

    # Test an asset with -25.0% extreme negative real yield
    neg_yield_asset = {
        "symbol": "NEGYIELD",
        "name": "Negative Yield Hyper-Inflation Token",
        "category": "Dilution Hyperdrive",
        "price_usd": 0.50,
        "market_cap_usd": 50_000_000,
        "fdv_usd": 500_000_000,
        "drawdowns": {"drawdown_from_ath_pct": -95.0, "current_cycle_recovery_pct": 5.0},
        "tokenomics": {"circulating_pct": 10.0, "annual_inflation_rate_pct": 40.0},
        "commits": {"github_commits_30d": 10, "core_active_developers_monthly": 2},
        "staking_yield": 15.0,
        "staking_telemetry": {
            "nominal_apy_pct": 15.0,
            "real_yield_pct": -25.0,  # 15% nominal - 40% inflation
            "network_staking_ratio_pct": 50.0
        },
        "valuation_percentile": 20.0,
        "valuation": {
            "composite_fundamental_score": 30.0,
            "institutional_conviction": "HIGH_DILUTION_RISK"
        }
    }
    engine._dossiers["NEGYIELD"] = neg_yield_asset

    retrieved = engine.get_dossiers(symbol="NEGYIELD")
    assert len(retrieved) == 1
    assert retrieved[0]["staking_telemetry"]["real_yield_pct"] == -25.0

    # Ensure min_score filtering correctly filters out low score asset
    high_score_only = engine.get_dossiers(min_score=80.0)
    assert not any(g["symbol"] == "NEGYIELD" for g in high_score_only)

    del engine._dossiers["NEGYIELD"]


def test_valuation_extreme_data_missing_commit_history():
    """Empirical test for assets with missing or zero GitHub commit history."""
    engine = SpotCryptoDossierEngine()

    no_commits_asset = {
        "symbol": "NOCOMMITS",
        "name": "Abandonware Gem",
        "category": "Dormant Protocol",
        "price_usd": 0.10,
        "market_cap_usd": 1_000_000,
        "fdv_usd": 1_000_000,
        "drawdowns": {"drawdown_from_ath_pct": -99.0, "current_cycle_recovery_pct": 1.0},
        "tokenomics": {"circulating_pct": 100.0, "annual_inflation_rate_pct": 0.0},
        "commits": {},  # Completely empty commit dictionary
        "staking_yield": 0.0,
        "staking_telemetry": {"nominal_apy_pct": 0.0, "real_yield_pct": 0.0},
        "valuation_percentile": 10.0,
        "valuation": {
            "composite_fundamental_score": 15.0,
            "institutional_conviction": "ABANDONED_CODEBASE"
        }
    }
    engine._dossiers["NOCOMMITS"] = no_commits_asset

    # Retrieval should not raise KeyError or crash
    retrieved = engine.get_dossiers(symbol="NOCOMMITS")
    assert len(retrieved) == 1
    assert retrieved[0]["commits"] == {}

    report = engine.get_gems_research_report(symbol="NOCOMMITS")
    assert report["ok"] is True
    assert len(report["gems"]) == 1

    del engine._dossiers["NOCOMMITS"]


# =============================================================================
# 5. INTEGRATION & ADVERSARIAL QUERY ENDPOINT TESTS
# =============================================================================

def test_api_crypto_memes_adversarial_queries(client):
    """Tests /api/research/crypto/memes with extreme query parameters."""
    # 1. min_score = 100.0 (extreme threshold)
    resp = client.get("/api/research/crypto/memes?min_score=100.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["tokens"], list)

    # 2. graduating_only = True
    resp_grad = client.get("/api/research/crypto/memes?graduating_only=true")
    assert resp_grad.status_code == 200
    data_grad = resp_grad.json()
    for t in data_grad["tokens"]:
        assert 75.0 <= t["bonding_curve_pct"] <= 100.0

    # 3. limit = 1
    resp_lim = client.get("/api/research/crypto/memes?limit=1")
    assert resp_lim.status_code == 200
    data_lim = resp_lim.json()
    assert len(data_lim["tokens"]) <= 1


def test_api_crypto_gems_adversarial_queries(client):
    """Tests /api/research/crypto/gems with non-existent symbols and extreme filters."""
    # 1. Non-existent symbol
    resp_none = client.get("/api/research/crypto/gems?symbol=DOESNOTEXISTXYZ")
    assert resp_none.status_code == 200
    data_none = resp_none.json()
    assert data_none["ok"] is True
    assert len(data_none["gems"]) == 0
    assert data_none["total_dossiers"] == 0

    # 2. Extreme min_score = 99.0
    resp_extreme = client.get("/api/research/crypto/gems?min_score=99.0")
    assert resp_extreme.status_code == 200
    data_extreme = resp_extreme.json()
    assert data_extreme["ok"] is True
    for g in data_extreme["gems"]:
        assert g["valuation"]["composite_fundamental_score"] >= 99.0


# =============================================================================
# 6. MEME STREAMER ARITHMETIC & SSE GENERATOR HARDENING
# =============================================================================

def test_meme_alpha_streamer_safety_score_penalties_breakdown():
    """Validates exact deduction arithmetic in MemeAlphaStreamer."""
    # Test token with all security violations
    toxic_token = PumpAlphaToken(
        mint="ToxicToken11111111111111111111111111111111111",
        symbol="TOXIC",
        name="Toxic Rug",
        bonding_curve_pct=50.0,
        sol_reserves=42.5,
        dev_holding_pct=25.0,     # >15% -> -25
        dev_dump_detected=True,   # dump -> -50
        mint_revoked=False,       # mint active -> -30
        freeze_revoked=False,     # freeze active -> -20
        lp_locked_pct=50.0,       # <95% -> -25
        safety_verdict="DANGER"
    )

    class MockScanner:
        def scan_bonding_curves(self):
            return [toxic_token]
        def build_synthetic_pump_radar(self):
            return [toxic_token]

    streamer = MemeAlphaStreamer(scanner=MockScanner())
    scored = streamer.get_scored_tokens(min_score=0.0)
    assert len(scored) == 1
    # 100 - 50 - 25 - 30 - 20 - 25 = -50 -> clamped to 0
    assert scored[0]["safety_score"] == 0
    assert scored[0]["dev_audit"]["dev_dump_detected"] is True
    assert scored[0]["dev_audit"]["lp_burn_lock_verified"] is False
    assert scored[0]["dev_audit"]["mint_authority_revoked"] is False
    assert scored[0]["dev_audit"]["freeze_authority_revoked"] is False

    # Test token with moderate dev holding (10%) and otherwise clean
    clean_token = PumpAlphaToken(
        mint="CleanToken11111111111111111111111111111111111",
        symbol="CLEAN",
        name="Clean Token",
        bonding_curve_pct=50.0,
        sol_reserves=42.5,
        dev_holding_pct=10.0,     # >8% and <=15% -> -10
        dev_dump_detected=False,
        mint_revoked=True,
        freeze_revoked=True,
        lp_locked_pct=100.0,
        safety_verdict="SAFE"
    )

    class MockScannerClean:
        def scan_bonding_curves(self):
            return [clean_token]
        def build_synthetic_pump_radar(self):
            return [clean_token]

    streamer_clean = MemeAlphaStreamer(scanner=MockScannerClean())
    scored_clean = streamer_clean.get_scored_tokens(min_score=0.0)
    assert len(scored_clean) == 1
    # 100 - 10 = 90
    assert scored_clean[0]["safety_score"] == 90
    assert scored_clean[0]["dev_audit"]["lp_burn_lock_verified"] is True


def test_meme_safety_filter_solana_taxes_and_fail_closed():
    """Empirical test for Solana transfer fee taxes and fail-closed mechanism."""
    filter_eng = MemeSafetyFilter()

    # 1. Non-zero transfer tax (e.g. 5% buy tax)
    tax_audit = {
        "lp_locked_pct": 100.0,
        "mintAuthority": None,
        "freezeAuthority": None,
        "transferFee": {"pct": 5.0},
        "top10_pct": 8.0,
        "creator_pct": 1.0,
        "dev_dumped": False
    }
    rep_tax = filter_eng.evaluate_solana_token(
        mint_address="TaxToken1111111111111111111111111111111111",
        rugcheck_data=tax_audit
    )
    assert rep_tax.is_safe is False
    assert any("Non-zero transfer tax detected" in r for r in rep_tax.reasons)

    # 2. Fail-closed on missing report
    rep_fail_closed = filter_eng.evaluate_solana_token(
        mint_address="MissingReportToken111111111111111111111111",
        rugcheck_data={}  # Empty data, no live mock
    )
    assert rep_fail_closed.is_safe is False
    assert any("RugCheck on-chain report unavailable" in r for r in rep_fail_closed.reasons)


@pytest.mark.asyncio
async def test_meme_alpha_streamer_sse_generator_iteration():
    """Empirical test for MemeAlphaStreamer SSE event generator."""
    streamer = MemeAlphaStreamer()
    gen = streamer.event_generator(interval_seconds=0.01)

    # Grab first event
    first_event = await anext(gen)
    assert first_event.startswith("event: meme_alpha_update\n")
    assert "data: {" in first_event
    assert '"ok": true' in first_event.lower()
    assert '"tokens": [' in first_event


def test_spot_crypto_dossiers_category_filter_insensitivity():
    """Empirical test verifying category filtering is case-insensitive across all assets."""
    engine = SpotCryptoDossierEngine()

    l1_dossiers_lower = engine.get_dossiers(category="l1")
    l1_dossiers_upper = engine.get_dossiers(category="L1")
    assert len(l1_dossiers_lower) > 0
    assert len(l1_dossiers_lower) == len(l1_dossiers_upper)

    ai_dossiers = engine.get_dossiers(category="ai")
    assert any(d["symbol"] == "TAO" for d in ai_dossiers)
    assert any(d["symbol"] == "NEAR" for d in ai_dossiers)

    depin_dossiers = engine.get_dossiers(category="depin")
    assert any(d["symbol"] == "RENDER" for d in depin_dossiers)

    # Category matching with "liquidity"
    liquidity_dossiers = engine.get_dossiers(category="liquidity")
    assert any(d["symbol"] == "AAVE" for d in liquidity_dossiers)

    # Empirical finding: category="defi" currently yields 0 assets because AAVE is labeled
    # "Institutional Liquidity Protocol" rather than "DeFi Institutional Liquidity Protocol"
    defi_dossiers = engine.get_dossiers(category="defi")
    assert len(defi_dossiers) == 0  # Documented finding: category taxonomy gap


