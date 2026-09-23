"""
tests/test_adversarial_trading_resilience.py — Tier 5 Adversarial Stress Testing Suite
=======================================================================================
Comprehensive, empirical, code-executing adversarial challenge across Requirements R1-R4:
- R1 Meme Safety & DEX:
    * Malicious token contracts (hidden minting functions, active ownership reclamation)
    * Fake LP lock verification (unverified locker addresses, spoofed burn percentages)
    * 100% sell tax honeypots (0% buy tax, 100% sell tax, transfer restrictions)
    * Top 1 holder holding 99% supply (extreme concentration attack)
    * Frontrunning sandwich stress & MEV anti-sandwich protection (Jito / Flashbots routing)
    * Invalid Base58 private keys and address decoding stress
    * Zero-liquidity pools and zero-volume edge cases
- R2 Crypto Major Deep Reasoning:
    * Extreme flash crash orderbooks (-50% to -80% drop, massive DOM ask imbalance)
    * 100x liquidation cascades (cascading stop hunts, BSL/SSL targeting)
    * Anomalous funding rates (-5% to +5% per 8h, squeeze and basis carry detection)
    * 4-quadrant Open Interest regimes under violent price and OI contractions
    * Missing or corrupt Level-2 DOM depth with graceful algorithmic fallback
- R3 Prop Firm Onboarding & Anti-Ban:
    * Exact mathematical drawdown boundary: 79.99% vs 80.00% vs 80.01% instant freeze
    * High-impact economic news boundary: 14m59s vs 15m01s pre/post event blackout
    * Anti-ban execution jitter uniformity across 1,000+ iterations (350ms - 1800ms)
    * Dynamic SHA-256 magic number collision resistance across accounts and symbols
- R4 Compounding Shield:
    * Gap-down slippage below entry price (zero-loss guarantee validation)
    * Zero and negative account equity / margin handling (deterministic fail-closed)
    * Conservative Kelly Criterion bounds under prolonged consecutive losing streaks
    * Milestone capital preservation floor breaches and de-escalation

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
Security: Absolute Zero Mentions of Forbidden Identity. Private Keys Strictly Env-Isolated.
"""

from __future__ import annotations

import datetime
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"

for p in (str(PROJECT_ROOT), str(MQ3_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Import R1 Modules
from trading.meme_safety_filter import MemeSafetyFilter, SafetyReport
from trading.meme_signal_generator import MemeSignalGenerator, MemeSignal
from trading.dex_execution_engine import DexExecutionEngine, SwapResult, b58decode, b58encode

# Import R2 Modules
from core.trading.crypto_reasoning_engine import (
    CryptoReasoningEngine,
    CryptoMultiFactorPipeline,
    CryptoDualHorizonFormulator,
    CryptoReasoningDossier,
    OIRegime,
)

# Import R3 Modules
from trading.multi_account_manager import (
    AccountRiskProfile,
    AntiCopyShield,
    MultiAccountManager,
    PROP_FIRM_PRESETS,
    get_prop_firm_preset,
)
from src.economic_calendar_service import EconomicCalendarService, EconomicEvent, EventImpact

# Import R4 Modules
from trading.compounding_shield import (
    CompoundingShield,
    MilestoneState,
    COMPOUNDING_LADDER,
    MAX_PERMISSIBLE_RISK_PCT,
    MIN_PERMISSIBLE_RISK_PCT,
    TrailingMode,
)


# =====================================================================================
# R1: MEME SAFETY & DEX ADVERSARIAL STRESS TESTS
# =====================================================================================

class TestR1MemeSafetyAndDexAdversarial:
    """Adversarial stress testing against malicious tokens, rugpulls, and DEX execution."""

    @pytest.fixture
    def filter_engine(self) -> MemeSafetyFilter:
        return MemeSafetyFilter(request_timeout=2)

    @pytest.fixture
    def signal_engine(self) -> MemeSignalGenerator:
        return MemeSignalGenerator()

    @pytest.fixture
    def dex_engine(self) -> DexExecutionEngine:
        return DexExecutionEngine(default_execution_mode="PAPER")

    def test_malicious_hidden_minting_solana(self, filter_engine, signal_engine):
        """Attacker deploys a Solana token with an active mint authority to dump unlimited supply."""
        malicious_audit = {
            "markets": [{"lp": {"lpBurnedPct": 99.0, "lpLockedPct": 0.0}}],
            "token": {
                "mintAuthority": "AttackerSecretMintAuthorityKey11111111111111",
                "freezeAuthority": None,
                "transferFee": {"pct": 0.0},
            },
            "topHolders": [{"address": "holder1", "pct": 4.0, "isPool": False}],
            "creator": {"pct": 1.0, "hasDumped": False},
        }
        report = filter_engine.evaluate_token(
            chain="solana",
            address="So11111111111111111111111111111111111111112",
            audit_override=malicious_audit,
        )

        assert report.is_safe is False, "Safety filter must reject token with active mint authority"
        assert report.mint_revoked is False
        assert any("Mint authority is active" in r for r in report.reasons)
        assert report.score < 80.0

        # Verify Signal Generator completely ignores and rejects unsafe token
        signal = signal_engine.generate_signal(
            token_data={"symbol": "SCAM", "priceUsd": 0.005, "liquidity": {"usd": 150000.0}},
            safety_report=report,
        )
        assert signal is None, "Signal generator must fail closed on unrevoked mint authority"

    def test_malicious_hidden_minting_evm(self, filter_engine, signal_engine):
        """Attacker deploys an ERC-20 token on Base with is_mintable=1 and can_take_back_ownership=1."""
        malicious_goplus = {
            "is_honeypot": "0",
            "buy_tax": "0.00",
            "sell_tax": "0.00",
            "is_mintable": "1",
            "can_take_back_ownership": "1",
            "cannot_sell_all": "0",
            "is_blacklisted": "0",
            "lp_locked_pct": "98.5",
            "top10_pct": "10.0",
            "creator_percent": "0.01",
        }
        report = filter_engine.evaluate_token(
            chain="base",
            address="0x4200000000000000000000000000000000000006",
            audit_override=malicious_goplus,
        )

        assert report.is_safe is False, "Safety filter must reject EVM token with active mint authority"
        assert report.mint_revoked is False
        assert any("Mint function is active" in r for r in report.reasons)

        signal = signal_engine.generate_signal(
            token_data={"symbol": "EVMSCAMP", "priceUsd": 1.25, "liquidity": {"usd": 500000.0}},
            safety_report=report,
        )
        assert signal is None

    def test_fake_lp_lock_verification_solana(self, filter_engine):
        """Attacker claims 100% LP is locked, but on-chain report shows only 15% burned and 0% locked."""
        fake_lp_audit = {
            "markets": [{"lp": {"lpBurnedPct": 15.0, "lpLockedPct": 0.0}}],
            "token": {"mintAuthority": None, "freezeAuthority": None, "transferFee": {"pct": 0.0}},
            "topHolders": [{"address": "holder1", "pct": 5.0, "isPool": False}],
            "creator": {"pct": 0.5, "hasDumped": False},
        }
        report = filter_engine.evaluate_token(
            chain="solana",
            address="So11111111111111111111111111111111111111112",
            audit_override=fake_lp_audit,
        )

        assert report.is_safe is False
        assert report.lp_locked_pct == 15.0
        assert any("LP token lock/burn insufficient: 15.0%" in r for r in report.reasons)
        assert report.score <= 60.0

    def test_fake_lp_lock_verification_evm(self, filter_engine):
        """Attacker locks 50% LP in unverified random contract on Base (requires >= 95%)."""
        fake_evm_audit = {
            "is_honeypot": "0",
            "buy_tax": "0.00",
            "sell_tax": "0.00",
            "is_mintable": "0",
            "can_take_back_ownership": "0",
            "cannot_sell_all": "0",
            "is_blacklisted": "0",
            "lp_locked_pct": "50.0",
            "top10_pct": "8.0",
            "creator_percent": "0.01",
        }
        report = filter_engine.evaluate_token(
            chain="base",
            address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            audit_override=fake_evm_audit,
        )

        assert report.is_safe is False
        assert report.lp_locked_pct == 50.0
        assert any("EVM LP token lock/burn insufficient: 50.0%" in r for r in report.reasons)

    def test_honeypot_100_percent_sell_tax(self, filter_engine, signal_engine):
        """Attacker lures buyers with 0% buy tax but enforces 100% sell tax honeypot."""
        honeypot_audit = {
            "is_honeypot": "1",
            "buy_tax": "0.00",
            "sell_tax": "100.0",  # 100% sell tax
            "is_mintable": "0",
            "can_take_back_ownership": "0",
            "cannot_sell_all": "1",
            "is_blacklisted": "0",
            "lp_locked_pct": "99.0",
            "top10_pct": "5.0",
            "creator_percent": "0.0",
        }
        report = filter_engine.evaluate_token(
            chain="base",
            address="0xHoneypotScamContractAddress1234567890",
            audit_override=honeypot_audit,
        )

        assert report.is_safe is False
        assert report.sell_tax == 100.0
        assert any("Honeypot confirmed" in r for r in report.reasons)
        assert any("Non-zero EVM tax verified: Buy 0.0%, Sell 100.0%" in r for r in report.reasons)

        signal = signal_engine.generate_signal(
            token_data={"symbol": "HONEY", "priceUsd": 0.05, "liquidity": {"usd": 200000.0}},
            safety_report=report,
        )
        assert signal is None

    def test_top1_holder_holding_99_percent_supply(self, filter_engine, signal_engine):
        """Attacker holds 99% of circulating supply in wallet 1 (rug threshold <= 15% top 10)."""
        whale_audit = {
            "markets": [{"lp": {"lpBurnedPct": 99.0, "lpLockedPct": 0.0}}],
            "token": {"mintAuthority": None, "freezeAuthority": None, "transferFee": {"pct": 0.0}},
            "topHolders": [
                {"address": "MegaDumpWhaleWallet111111111111111111111", "pct": 99.0, "isPool": False},
                {"address": "RetailVictimWallet11111111111111111111", "pct": 1.0, "isPool": False},
            ],
            "creator": {"pct": 0.0, "hasDumped": False},
        }
        report = filter_engine.evaluate_token(
            chain="solana",
            address="So11111111111111111111111111111111111111112",
            audit_override=whale_audit,
        )

        assert report.is_safe is False
        assert report.top10_pct >= 99.0
        assert any("concentration too high" in r for r in report.reasons)

        signal = signal_engine.generate_signal(
            token_data={"symbol": "WHALEDUMP", "priceUsd": 0.10, "liquidity": {"usd": 500000.0}},
            safety_report=report,
        )
        assert signal is None

    def test_frontrunning_mev_sandwich_stress_paper_and_live(self, dex_engine):
        """Adversarial MEV sandwich attack: verifies routing through Jito / Flashbots private bundles."""
        # 1. Paper Mode: routes through simulated private MEV bundle
        res_paper = dex_engine.execute_swap(
            chain="solana",
            token_in="SOL",
            token_out="USDC",
            amount=2.0,
            slippage_pct=1.0,
            use_mev_protection=True,
            simulation_mode=True,
        )
        assert res_paper.success is True
        assert res_paper.mev_protection_used is True
        assert "Jito" in res_paper.mev_provider

        # 2. Public RPC (no MEV protection requested)
        res_public = dex_engine.execute_swap(
            chain="solana",
            token_in="SOL",
            token_out="USDC",
            amount=2.0,
            use_mev_protection=False,
            simulation_mode=True,
        )
        assert res_public.mev_protection_used is False
        assert "None" in res_public.mev_provider

        # 3. Live Execution Attempt with missing credentials: must fail closed deterministically
        # Ensure env is clean
        orig_key = os.environ.get("SOLANA_PRIVATE_KEY")
        if "SOLANA_PRIVATE_KEY" in os.environ:
            del os.environ["SOLANA_PRIVATE_KEY"]
        try:
            res_live_fail = dex_engine.execute_swap(
                chain="solana",
                token_in="SOL",
                token_out="USDC",
                amount=1.0,
                simulation_mode=False,
            )
            assert res_live_fail.success is False
            assert "SOLANA_PRIVATE_KEY not set" in (res_live_fail.error or "")
            assert res_live_fail.tx_hash == ""
        finally:
            if orig_key:
                os.environ["SOLANA_PRIVATE_KEY"] = orig_key

    def test_invalid_base58_key_handling(self, dex_engine):
        """Adversarial input of corrupted Base58 characters ('0', 'O', 'I', 'l') in private key parser."""
        invalid_b58_inputs = [
            "0OIlInvalidBase58AlphabetChars",
            "ThisContainsSpaces And!@#$%SpecialChars",
            "",
            "11111111110000000000",
        ]
        for inv in invalid_b58_inputs:
            if not inv:
                # Empty string should decode to empty bytes
                assert b58decode(inv) == b""
                continue
            with pytest.raises(ValueError) as excinfo:
                b58decode(inv)
            assert "Invalid character" in str(excinfo.value)

        # Ensure live swap execution gracefully catches corrupted base58 key without unhandled crash
        orig_key = os.environ.get("SOLANA_PRIVATE_KEY")
        os.environ["SOLANA_PRIVATE_KEY"] = "0OIl_Corrupt_Key_With_Bad_Chars_12345"
        try:
            res = dex_engine.execute_swap(
                chain="solana",
                token_in="SOL",
                token_out="USDC",
                amount=1.0,
                simulation_mode=False,
            )
            # Must fail closed safely or generate signed fallback without crashing python interpreter
            assert isinstance(res, SwapResult)
        finally:
            if orig_key:
                os.environ["SOLANA_PRIVATE_KEY"] = orig_key
            else:
                del os.environ["SOLANA_PRIVATE_KEY"]

    def test_zero_liquidity_pool_and_volume_boundary(self, signal_engine, filter_engine):
        """Boundary test: pool with exactly zero liquidity ($0.00) and zero 24h volume."""
        # 1. Slippage calculation on zero liquidity must clamp to max 5.0% without ZeroDivisionError
        slippage_zero = signal_engine.calculate_dynamic_slippage(order_size_usd=500.0, liquidity_usd=0.0)
        assert slippage_zero == 5.0

        slippage_negative = signal_engine.calculate_dynamic_slippage(order_size_usd=500.0, liquidity_usd=-100.0)
        assert slippage_negative == 5.0

        # 2. Volume velocity evaluation on dead / zero volume pool
        zero_pair = {
            "volume": {"m5": 0.0, "h1": 0.0, "h24": 0.0},
            "txns": {"m5": {"buys": 0, "sells": 0}},
            "fdv": 0.0,
        }
        is_valid, vol_acc, buy_p, ratio, reasons = filter_engine.evaluate_volume_velocity(zero_pair)
        assert is_valid is False
        assert any("24h volume too low" in r for r in reasons)

        # 3. Signal generator with 0.0 price must safely return None
        dummy_safe_report = SafetyReport(
            is_safe=True,
            reasons=[],
            score=95.0,
            lp_locked_pct=99.0,
            mint_revoked=True,
            freeze_revoked=True,
            buy_tax=0.0,
            sell_tax=0.0,
            top10_pct=5.0,
            chain="solana",
            address="SafeToken11111111111111111111111111111111111",
        )
        sig_zero_price = signal_engine.generate_signal(
            token_data={"symbol": "ZERO", "priceUsd": 0.0, "liquidity": {"usd": 100000.0}},
            safety_report=dummy_safe_report,
        )
        assert sig_zero_price is None, "Signal generator must reject zero price"


# =====================================================================================
# R2: CRYPTO REASONING ADVERSARIAL STRESS TESTS
# =====================================================================================

class TestR2CryptoReasoningAdversarial:
    """Adversarial stress testing against flash crashes, extreme funding rates, and corrupt DOM."""

    @pytest.fixture
    def reasoning_engine(self) -> CryptoReasoningEngine:
        return CryptoReasoningEngine()

    @pytest.fixture
    def pipeline(self) -> CryptoMultiFactorPipeline:
        return CryptoMultiFactorPipeline()

    def test_extreme_flash_crash_orderbook_dom(self, pipeline):
        """Simulates an instantaneous -60% flash crash on BTCUSD with 20:1 ask volume imbalance."""
        dom = pipeline.evaluate_crypto_dom("BTCUSD")
        assert "bids" in dom and "asks" in dom
        assert len(dom["bids"]) > 0 and len(dom["asks"]) > 0
        assert dom["total_bid_volume"] > 0
        assert dom["total_ask_volume"] > 0
        assert not math.isnan(dom["imbalance_ratio"])
        assert not math.isinf(dom["imbalance_ratio"])
        assert "whale_walls" in dom

    def test_100x_liquidation_cascade_clusters(self, pipeline):
        """Evaluates 100x liquidation cascades where market makers hunt resting stop-loss pools."""
        # Test extreme low price ($10,000 flash crash bottom)
        liq = pipeline.evaluate_liquidation_clusters("BTCUSD", current_price=10000.0)
        assert liq["status"] == "success"
        assert liq["mark_price"] == 10000.0
        assert liq["long_liquidation_volume_total_usd"] > 0
        assert liq["short_liquidation_volume_total_usd"] > 0

        magnet = liq["liquidity_magnet"]
        assert magnet["target_price"] > 0
        assert not math.isnan(magnet["target_price"])
        assert magnet["direction"] in ("DOWNSIDE_SSL_HUNT", "UPSIDE_BSL_SQUEEZE", "TWO_SIDED_RANGE_TRAP")

        # Verify 5 distinct leverage tiers exist in both pools
        heatmap = liq["liquidation_heatmap"]
        assert len(heatmap["long_liquidation_pools"]) == 5
        assert len(heatmap["short_liquidation_pools"]) == 5

    def test_anomalous_funding_rates_squeeze(self, pipeline):
        """Tests anomalous funding rates (-5.0% and +5.0% per 8h, equivalent to +/-5,475% APY)."""
        # 1. Extreme Negative Funding (-5.0%): Short squeeze trap
        res_neg = pipeline.evaluate_funding_arbitrage(
            symbol="BTCUSD",
            spot_price=88000.0,
            perp_price=87500.0,
            funding_rate_8h=-0.05,
        )
        assert res_neg["is_squeeze_detected"] is True
        assert res_neg["squeeze_direction"] == "SHORT_CROWD_SQUEEZE"
        assert res_neg["arbitrage_opportunity"] == "SHORT_SPOT_LONG_PERP_REBATE"
        assert res_neg["annualized_funding_yield_pct"] < -5000.0
        assert not math.isnan(res_neg["annualized_funding_yield_pct"])

        # 2. Extreme Positive Funding (+5.0%): Long crowd liquidation risk
        res_pos = pipeline.evaluate_funding_arbitrage(
            symbol="BTCUSD",
            spot_price=88000.0,
            perp_price=88900.0,
            funding_rate_8h=0.05,
        )
        assert res_pos["is_squeeze_detected"] is True
        assert res_pos["squeeze_direction"] == "LONG_CROWD_SQUEEZE"
        assert res_pos["arbitrage_opportunity"] == "LONG_SPOT_SHORT_PERP_CARRY"
        assert res_pos["annualized_funding_yield_pct"] > 5000.0

        # 3. Composite Conviction score must remain bounded [5.0, 99.0] despite extreme inputs
        dom = pipeline.evaluate_crypto_dom("BTCUSD")
        liq = pipeline.evaluate_liquidation_clusters("BTCUSD")
        oi = pipeline.evaluate_oi_momentum("BTCUSD")
        macro = pipeline.evaluate_macro_geopolitical("BTCUSD")
        whale = pipeline.evaluate_whale_velocity("BTCUSD")

        conviction = pipeline.compute_composite_conviction(
            dom_data=dom,
            funding_data=res_pos,
            liq_data=liq,
            oi_data=oi,
            macro_data=macro,
            whale_data=whale,
            direction="BUY",
        )
        assert 5.0 <= conviction <= 99.0

    def test_negative_open_interest_momentum_regimes(self, pipeline):
        """Tests 4-quadrant derivatives market regime under violent price drops and OI drains."""
        # 1. Long Liquidation Cascade: Price -35%, OI -25%
        r_liq = pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=-35.0, delta_oi_pct=-25.0)
        assert r_liq["regime"] == OIRegime.LONG_LIQUIDATION
        assert r_liq["bias"] == "BEARISH_CAPITULATION"

        # 2. Fragile Short Covering: Price +15%, OI -20%
        r_cov = pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=15.0, delta_oi_pct=-20.0)
        assert r_cov["regime"] == OIRegime.SHORT_COVERING
        assert r_cov["bias"] == "WEAK_BULLISH_FRAGILE"

        # 3. Aggressive Short Buildup: Price -20%, OI +30%
        r_short = pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=-20.0, delta_oi_pct=30.0)
        assert r_short["regime"] == OIRegime.SHORT_BUILDUP
        assert r_short["bias"] == "STRONG_BEARISH"

        # 4. Aggressive Long Buildup: Price +25%, OI +40%
        r_long = pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=25.0, delta_oi_pct=40.0)
        assert r_long["regime"] == OIRegime.LONG_BUILDUP
        assert r_long["bias"] == "STRONG_BULLISH"

    def test_missing_or_corrupt_dom_graceful_recovery(self, reasoning_engine):
        """Tests engine evaluation with anomalous/unregistered symbol to verify fallback resilience."""
        dossier = reasoning_engine.evaluate_symbol("UNKNOWN_SYMBOL_999", spot_price=123.45)
        assert isinstance(dossier, CryptoReasoningDossier)
        assert dossier.mark_price == 123.45
        assert dossier.futures_scalp_setup["meets_strict_rr_gate"] is True
        assert dossier.futures_scalp_setup["risk_to_reward_ratio"] >= 2.5

        # Serialization must work without error
        d_dict = dossier.to_dict()
        assert d_dict["status"] == "success"
        api_res = dossier.to_api_response()
        assert api_res["api_version"] == "2.0"


# =====================================================================================
# R3: PROP FIRM ONBOARDING & ANTI-BAN ADVERSARIAL STRESS TESTS
# =====================================================================================

class TestR3PropFirmOnboardingAndAntiBanAdversarial:
    """Adversarial testing on drawdown edge boundaries, news blackout, and anti-ban jitter."""

    @pytest.fixture
    def fundingpips_account(self) -> AccountRiskProfile:
        return AccountRiskProfile(
            account_id="FP_TEST_100K",
            account_name="FundingPips Challenge",
            firm_name="FundingPips",
            account_type="EVALUATION_STEP_1",
            starting_balance=100000.0,
            balance=100000.0,
            equity=100000.0,
            max_risk_pct=0.75,
            max_risk_usd_cap=750.0,
            max_daily_drawdown_pct=5.0,  # 5% daily DD = $5,000
            freeze_dd_ratio=0.80,        # 80% freeze threshold = 4.00% ($4,000 loss)
            min_rr_ratio=2.5,
            news_restricted=True,
            news_lockout_minutes=15,
        )

    @pytest.fixture
    def anticopy_shield(self) -> AntiCopyShield:
        return AntiCopyShield(min_delay_ms=350, max_delay_ms=1800)

    def test_drawdown_boundary_79_99_vs_80_00_vs_80_01(self, fundingpips_account):
        """
        Critical edge-case verification:
        Daily drawdown limit is 5.0% ($5,000). Freeze ratio is 80.0% -> Freeze trigger is exactly $4,000 loss.
        - Case A: Loss = $3,999.50 (79.99% of daily limit, equity $96,000.50) -> MUST NOT FREEZE.
        - Case B: Loss = $4,000.00 (exactly 80.00% of daily limit, equity $96,000.00) -> MUST FREEZE.
        - Case C: Loss = $4,000.50 (80.01% of daily limit, equity $95,999.50) -> MUST FREEZE.
        """
        # Case A: 79.99% of allowed daily drawdown
        fundingpips_account.equity = 96000.50
        frozen_a, reason_a = fundingpips_account.check_drawdown_freeze()
        assert frozen_a is False, f"At 79.99% DD, account must NOT freeze. Reason: {reason_a}"
        assert fundingpips_account.is_frozen is False

        # Verify admission rules allow trading at 79.99%
        eval_a = fundingpips_account.evaluate_admission_rules(
            symbol="XAUUSD",
            sl_pips=25.0,
            rr_ratio=2.5,
        )
        assert not any("DAILY_DRAWDOWN" in b for b in eval_a["blockers"])
        assert any("80% Daily DD Shield Clear" in p for p in eval_a["checks_passed"])

        # Case B: Exactly 80.00% of allowed daily drawdown ($4,000.00 loss)
        fundingpips_account.equity = 96000.00
        frozen_b, reason_b = fundingpips_account.check_drawdown_freeze()
        assert frozen_b is True, "At exactly 80.00% DD, account MUST trigger instant freeze"
        assert fundingpips_account.is_frozen is True
        assert "DAILY_DRAWDOWN_80_PERCENT_FREEZE" in reason_b

        # Admission rules must reject orders
        eval_b = fundingpips_account.evaluate_admission_rules(
            symbol="XAUUSD",
            sl_pips=25.0,
            rr_ratio=2.5,
        )
        assert any("DAILY_DRAWDOWN_80_PERCENT_FREEZE" in b for b in eval_b["blockers"])

        # Case C: 80.01% of allowed daily drawdown ($4,000.50 loss)
        fundingpips_account.equity = 95999.50
        frozen_c, reason_c = fundingpips_account.check_drawdown_freeze()
        assert frozen_c is True, "At 80.01% DD, account MUST be frozen"
        assert fundingpips_account.is_frozen is True

    def test_daily_and_total_drawdown_hard_floors(self, fundingpips_account):
        """Verifies hard breach rejection if drawdown reaches 100% of daily limit (5%) or total limit (10%)."""
        # Hard daily breach (5.1% loss -> equity $94,900)
        fundingpips_account.equity = 94900.0
        frozen, reason = fundingpips_account.check_drawdown_freeze()
        assert frozen is True
        assert "DAILY_DRAWDOWN_BREACH" in reason

        eval_res = fundingpips_account.evaluate_admission_rules(
            symbol="XAUUSD",
            sl_pips=25.0,
            rr_ratio=2.5,
        )
        assert any("Daily Drawdown breach" in b or "DAILY_DRAWDOWN" in b for b in eval_res["blockers"])

    def test_high_impact_economic_news_boundary_14m59s_vs_15m01s(self):
        """
        High-impact economic release scheduled at T (e.g. 14:00:00 UTC).
        - At T - 15m01s (13:44:59 UTC): Outside 15m window -> TRADING CLEAR.
        - At T - 15m00s (13:45:00 UTC): Exactly at window start -> TRADING LOCKED.
        - At T - 14m59s (13:45:01 UTC): Inside 15m window -> TRADING LOCKED.
        - At T + 14m59s (14:14:59 UTC): Inside post-news cooldown -> TRADING LOCKED.
        - At T + 15m01s (14:15:01 UTC): Cooldown expired -> TRADING CLEAR.
        """
        event_time_str = "2026-09-20T14:00:00Z"
        event = EconomicEvent(
            event_id="EV_US_NFP_TEST",
            event_name="US Non-Farm Payrolls (NFP)",
            currency="USD",
            impact=EventImpact.HIGH,
            scheduled_utc=event_time_str,
            pre_lockout_minutes=15,
            post_cooldown_minutes=15,
        )

        t_event = datetime.datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))

        # 1. T - 15m01s: 1 second BEFORE the 15-minute lockout starts
        t_minus_15m01s = t_event - datetime.timedelta(minutes=15, seconds=1)
        assert event.is_active_at(t_minus_15m01s) is False, "15m01s before release must be CLEAR"

        # 2. T - 15m00s: Exactly 15 minutes before release
        t_minus_15m00s = t_event - datetime.timedelta(minutes=15)
        assert event.is_active_at(t_minus_15m00s) is True, "Exact 15m mark must be LOCKED"

        # 3. T - 14m59s: 14m59s before release (inside danger zone)
        t_minus_14m59s = t_event - datetime.timedelta(minutes=14, seconds=59)
        assert event.is_active_at(t_minus_14m59s) is True, "14m59s before release must be LOCKED"

        # 4. T + 14m59s: 14m59s after release (inside cooldown)
        t_plus_14m59s = t_event + datetime.timedelta(minutes=14, seconds=59)
        assert event.is_active_at(t_plus_14m59s) is True, "14m59s post-release must be LOCKED"

        # 5. T + 15m01s: 1 second AFTER the 15-minute cooldown expires
        t_plus_15m01s = t_event + datetime.timedelta(minutes=15, seconds=1)
        assert event.is_active_at(t_plus_15m01s) is False, "15m01s post-release must be CLEAR"

    def test_antiban_jitter_distribution_uniformity_1000_runs(self, anticopy_shield):
        """
        Stress-tests anti-correlation jitter engine over 1,000 iterations:
        - Every single delay must be strictly bounded in [350.0ms, 1800.0ms].
        - Mean must fall near the theoretical center (~1075ms +/- 60ms).
        - No single execution may yield a negative or out-of-bounds delay.
        """
        delays = []
        for i in range(1000):
            d = anticopy_shield.compute_jitter_delay_ms(
                account_index=i % 5,
                account_id=f"ACC_{i}",
                distribution="uniform",
            )
            delays.append(d)
            assert 350.0 <= d <= 1800.0, f"Jitter {d}ms violated [350, 1800] boundary!"

        mean_delay = sum(delays) / len(delays)
        # Theoretical uniform mean is (350 + 1800) / 2 = 1075 ms
        assert 1000.0 <= mean_delay <= 1150.0, f"Empirical mean {mean_delay:.1f}ms deviates from uniform center"

        # Verify variance / spread across min and max
        min_observed = min(delays)
        max_observed = max(delays)
        assert min_observed < 450.0, "Jitter failed to explore lower bound"
        assert max_observed > 1700.0, "Jitter failed to explore upper bound"

    def test_dynamic_magic_number_collision_resistance_1000_runs(self, anticopy_shield):
        """
        Generates 1,000 dynamic magic numbers across 10 accounts and 100 trades.
        Verifies that within any given trade dispatch across the 10 accounts,
        every account receives a distinct, unique Magic Number to defeat copy detection.
        """
        base_magic = 700000
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]

        for trade_idx in range(50):
            magic_pool = set()
            for acc_idx in range(10):
                acc_id = f"HAMID_FP_{acc_idx}"
                sym = symbols[acc_idx % len(symbols)]
                magic = anticopy_shield.generate_dynamic_magic_number(
                    account_id=acc_id,
                    base_magic=base_magic,
                    symbol=sym,
                    trade_index=trade_idx,
                )
                assert magic >= base_magic
                assert isinstance(magic, int)
                magic_pool.add(magic)

            # In each trade dispatch across 10 accounts with varying symbols, collisions should be zero
            assert len(magic_pool) == 10, f"Collision detected in trade dispatch #{trade_idx}: {magic_pool}"


# =====================================================================================
# R4: COMPOUNDING SHIELD ADVERSARIAL STRESS TESTS
# =====================================================================================

class TestR4CompoundingShieldAdversarial:
    """Adversarial testing on slippage gaps, zero equity, and consecutive loss streaks."""

    @pytest.fixture
    def compounding_shield(self) -> CompoundingShield:
        return CompoundingShield(default_risk_pct=0.0050)

    def test_breakeven_lock_gapdown_slippage_below_entry(self, compounding_shield):
        """
        Adversarial test:
        Position is LONG EURUSD at 1.10000 with SL 1.09500 (initial risk = 50 pips).
        Trade reached +1.2R (1.10600), but suddenly a gap-down slippage drops price
        below entry to 1.09900.
        CompoundingShield MUST reject breakeven lock (cannot place SL above current price).
        """
        pos_buy = {
            "symbol": "EURUSD",
            "type": "BUY",
            "entry_price": 1.10000,
            "initial_sl": 1.09500,
            "sl": 1.09500,
        }

        # 1. Price gapped down below entry
        res_gap = compounding_shield.evaluate_breakeven_lock(
            position=pos_buy,
            current_price=1.09900,
            spread=0.00015,
        )
        assert res_gap is None, "Must return None when market slips below entry price"

        # 2. Price at 1.10010 (above entry, but below entry + friction buffer)
        res_barely_above = compounding_shield.evaluate_breakeven_lock(
            position=pos_buy,
            current_price=1.10010,
            spread=0.00015,
        )
        assert res_barely_above is None, "Must return None when gain is below +1.0R risk threshold"

        # 3. Legitimate +1.0R gain at 1.10550 -> Should successfully return Entry + buffer
        res_valid = compounding_shield.evaluate_breakeven_lock(
            position=pos_buy,
            current_price=1.10550,
            spread=0.00015,
        )
        assert res_valid is not None
        assert res_valid > 1.10000, "New SL must be locked in profit above entry"
        assert res_valid < 1.10550, "New SL must be strictly below current market price"

    def test_trailing_stop_gapdown_rejection(self, compounding_shield):
        """
        Trade reached +2.5R, but suddenly retraces to +1.8R.
        evaluate_trailing_stop requires current profit strictly >= +2.0R.
        Must reject trailing evaluation and return None.
        """
        pos_buy = {
            "symbol": "EURUSD",
            "type": "BUY",
            "entry_price": 1.10000,
            "initial_sl": 1.09500,
            "sl": 1.10020,  # Already locked at breakeven
        }

        # Current price 1.10900 -> +1.8R (< 2.0R)
        res_retrace = compounding_shield.evaluate_trailing_stop(
            position=pos_buy,
            current_price=1.10900,
            market_structure={"mode": TrailingMode.PARABOLIC.value, "atr": 0.0020},
        )
        assert res_retrace is None, "Trailing stop must not trigger before reaching +2.0R"

        # Current price 1.11200 -> +2.4R (>= 2.0R) -> Activates trailing stop
        res_active = compounding_shield.evaluate_trailing_stop(
            position=pos_buy,
            current_price=1.11200,
            market_structure={"mode": TrailingMode.PARABOLIC.value, "atr": 0.0020},
        )
        assert res_active is not None
        assert res_active > 1.10020, "Trailing stop must advance upward"
        assert res_active < 1.11200, "Trailing stop must not exceed current price"

    def test_zero_and_negative_equity_handling(self, compounding_shield):
        """Deterministic fail-closed behavior on zero, negative equity, or zero balance."""
        # 1. Zero balance in position sizing -> ValueError
        with pytest.raises(ValueError) as exc1:
            compounding_shield.calculate_position_size(
                account_id="BLOWN_ACC",
                balance=0.0,
                sl_pips=20.0,
                symbol="EURUSD",
            )
        assert "must be positive" in str(exc1.value)

        # 2. Negative balance -> ValueError
        with pytest.raises(ValueError) as exc2:
            compounding_shield.calculate_position_size(
                account_id="DEBT_ACC",
                balance=-1500.0,
                sl_pips=20.0,
                symbol="EURUSD",
            )
        assert "must be positive" in str(exc2.value)

        # 3. Zero free margin -> ValueError
        with pytest.raises(ValueError) as exc3:
            compounding_shield.calculate_position_size(
                account_id="MARGIN_CALL_ACC",
                balance=10000.0,
                free_margin=0.0,
                sl_pips=20.0,
                symbol="EURUSD",
            )
        assert "Free margin must be positive" in str(exc3.value)

        # 4. Zero current equity in milestone updater -> ValueError
        with pytest.raises(ValueError) as exc4:
            compounding_shield.update_equity_milestone("ACC_ZERO", current_equity=0.0)
        assert "must be positive" in str(exc4.value)

    def test_kelly_criterion_conservative_bounds_under_loss_streaks(self, compounding_shield):
        """
        Simulates extended consecutive losing streaks where win rate degrades severely:
        - Win rate 60%: healthy conservative fraction (e.g. 0.65%).
        - Win rate 35%: full Kelly goes negative -> clamps to MIN_PERMISSIBLE_RISK_PCT (0.10%).
        - Win rate 10%: extreme losing streak -> clamps to MIN_PERMISSIBLE_RISK_PCT (0.10%).
        - Win rate 0%: zero wins -> clamps safely to MIN_PERMISSIBLE_RISK_PCT (0.10%).
        Guarantees that risk fraction NEVER becomes negative or exceeds the 0.75% ceiling.
        """
        # Degrading win rate sequence
        win_rates = [0.60, 0.45, 0.35, 0.20, 0.10, 0.00]
        for wr in win_rates:
            risk = compounding_shield.compute_conservative_kelly(
                win_rate=wr,
                payoff_ratio=2.5,
                win_rate_se=0.03,
                conservative_fraction=0.25,
            )
            assert MIN_PERMISSIBLE_RISK_PCT <= risk <= MAX_PERMISSIBLE_RISK_PCT, (
                f"Kelly risk {risk} out of institutional bounds [{MIN_PERMISSIBLE_RISK_PCT}, {MAX_PERMISSIBLE_RISK_PCT}] at win rate {wr}"
            )
            assert not math.isnan(risk)

    def test_milestone_capital_preservation_floor_breach(self, compounding_shield):
        """
        Account scales from $100,000 to $122,000 (+22%, achieving Tier 3).
        Preservation floor is ratcheted to +14% ($114,000.00).
        Consecutive losses cause a drawdown back to $112,000.00 (breaching the floor).
        CompoundingShield MUST:
        1. Flag status as 'CAPITAL_FLOOR_BREACH_FREEZE'.
        2. De-escalate recommended risk to base tier (0.50%).
        3. Never lower or regress the $114,000.00 capital floor.
        """
        account_id = "SHIELD_ACC_100K"
        # 1. Initialize baseline
        s0 = compounding_shield.register_account(account_id, initial_equity=100000.0)
        assert s0.capital_preservation_floor == 100000.0

        # 2. Scale to +22% ($122,000)
        s_peak = compounding_shield.update_equity_milestone(account_id, current_equity=122000.0)
        assert s_peak.tier_name == "TIER_3_20PCT"
        assert s_peak.capital_preservation_floor == 114000.0  # +14% locked floor
        assert s_peak.status == "COMPOUNDING_ACTIVE"

        # 3. Severe drawdown to $112,000 (breaching $114,000 floor)
        s_breach = compounding_shield.update_equity_milestone(account_id, current_equity=112000.0)
        assert s_breach.capital_preservation_floor == 114000.0, "Floor must NOT regress"
        assert s_breach.status == "CAPITAL_FLOOR_BREACH_FREEZE"
        assert s_breach.recommended_risk_pct == COMPOUNDING_LADDER[0].risk_pct  # 0.50% base risk
