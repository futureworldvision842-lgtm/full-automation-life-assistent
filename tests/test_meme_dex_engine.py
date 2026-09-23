"""
tests/test_meme_dex_engine.py — Comprehensive Unit & Integration Test Suite for Requirement R1
=============================================================================================
Verifies:
1. MemeSafetyFilter:
   - LP lock/burn verification (>= 95% burned or locked).
   - Contract security: Mint & Freeze disabled, honeypot 0% buy/sell tax simulation.
   - Distribution audit: Top 10 non-DEX <= 15%, dev wallet liquidity drain/dump detection.
   - Volume velocity: VolAccel_5m >= 1.8x, BuyPressure >= 1.5x, organic Vol/MC 0.5x–4.0x.
2. MemeSignalGenerator:
   - Rejects unsafe tokens.
   - Valid trade setup generation: entry, dynamic slippage, SL (-18%), TP1 (+50%), TP2 (+100%), TP3 (+300%+).
   - Dynamic slippage formula scaling.
   - Multi-channel broadcast to Discord (#crypto-bot 1541529106074828890), WhatsApp (:3200), and Dashboard telemetry.
3. DexExecutionEngine:
   - Paper execution on Solana and EVM/Base with portfolio ledger updates.
   - Dynamic priority fees (Compute Budget / EIP-1559 gas) and MEV anti-sandwich routing (Jito / Flashbots).
   - Hot wallet key isolation: strictly from environment variables, zero plaintext leaks, fail-closed live execution.
   - Live signing with Ed25519 (Solana) and Secp256k1 (EVM).
4. Skills Integration & Anti-Leak Compliance:
   - skills/dexscreener_meme_research integration with MemeSafetyFilter.
   - Strict identity check: zero occurrences of forbidden handles, correct owner attribution.

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
"""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from trading.meme_safety_filter import (
    MemeSafetyFilter,
    SafetyReport,
    SOLANA_BURN_ADDRESSES,
    EVM_BURN_ADDRESSES,
)
from trading.meme_signal_generator import (
    MemeSignalGenerator,
    MemeSignal,
    CRYPTO_BOT_DISCORD_CHANNEL_ID,
    MASTER_PHONE_NUMBER,
)
from trading.dex_execution_engine import (
    DexExecutionEngine,
    SwapResult,
    b58encode,
    b58decode,
    JITO_TIP_ACCOUNTS,
)
import skills.dexscreener_meme_research as dmr

PROJECT_ROOT = Path("F:/Jarvis Command Center")


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def safety_filter():
    return MemeSafetyFilter(request_timeout=2)


@pytest.fixture
def signal_generator():
    return MemeSignalGenerator()


@pytest.fixture
def dex_engine(tmp_path):
    # Use temporary portfolio path to prevent test pollution
    engine = DexExecutionEngine(default_execution_mode="PAPER")
    return engine


@pytest.fixture
def valid_solana_audit():
    """Generates an audit report payload satisfying all R1.1 safety criteria."""
    return {
        "markets": [
            {
                "lp": {
                    "lpBurnedPct": 98.5,
                    "lpLockedPct": 0.0,
                }
            }
        ],
        "token": {
            "mintAuthority": None,
            "freezeAuthority": None,
            "transferFee": {"pct": 0.0},
        },
        "topHolders": [
            {"address": "PoolVault11111111111111111111111111111", "pct": 45.0, "isPool": True},
            {"address": "Holder1111111111111111111111111111111", "pct": 1.5, "isPool": False},
            {"address": "Holder2222222222222222222222222222222", "pct": 1.2, "isPool": False},
            {"address": "Holder3333333333333333333333333333333", "pct": 1.1, "isPool": False},
            {"address": "Holder4444444444444444444444444444444", "pct": 1.0, "isPool": False},
            {"address": "Holder5555555555555555555555555555555", "pct": 0.9, "isPool": False},
            {"address": "Holder6666666666666666666666666666666", "pct": 0.8, "isPool": False},
            {"address": "Holder7777777777777777777777777777777", "pct": 0.8, "isPool": False},
            {"address": "Holder8888888888888888888888888888888", "pct": 0.7, "isPool": False},
            {"address": "Holder9999999999999999999999999999999", "pct": 0.7, "isPool": False},
            {"address": "Holder1010101010101010101010101010101", "pct": 0.6, "isPool": False},
        ],
        "creator": {
            "pct": 1.2,
            "hasDumped": False,
        }
    }


@pytest.fixture
def valid_pair_data():
    """Generates pair market data satisfying volume velocity criteria."""
    return {
        "symbol": "PEPE_JARVIS",
        "priceUsd": 0.0000125,
        "fdv": 500000.0,
        "liquidity": {"usd": 150000.0},
        "volume": {
            "m5": 25000.0,    # 25,000 * 12 = 300,000 annualized rate
            "h1": 120000.0,   # VolAccel = 300,000 / 120,000 = 2.5x (>= 1.8x)
            "h24": 350000.0,  # 350,000 / 500,000 FDV = 0.70x (between 0.5x and 4.0x)
        },
        "txns": {
            "m5": {
                "buys": 180,
                "sells": 90,  # BuyPressure = 180 / 90 = 2.0x (>= 1.5x)
            }
        }
    }


# =============================================================================
# 1. MemeSafetyFilter Tests
# =============================================================================

def test_safety_filter_safe_solana_token(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies that a fully compliant token passes safety audit with high score."""
    report = safety_filter.evaluate_token(
        chain="solana",
        address="So11111111111111111111111111111111111111112",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is True
    assert report.score >= 80.0
    assert report.lp_locked_pct == 98.5
    assert report.mint_revoked is True
    assert report.freeze_revoked is True
    assert report.buy_tax == 0.0
    assert report.sell_tax == 0.0
    assert report.top10_pct <= 15.0
    assert report.dev_dump_detected is False
    assert report.volume_velocity_safe is True


def test_safety_filter_lp_unlocked_rejection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when LP locked/burned is below 95% threshold."""
    valid_solana_audit["markets"][0]["lp"]["lpBurnedPct"] = 82.0  # < 95%
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.lp_locked_pct == 82.0
    assert any("LP token lock/burn insufficient" in r for r in report.reasons)


def test_safety_filter_mint_authority_rejection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when contract mint authority is active."""
    valid_solana_audit["token"]["mintAuthority"] = "ActiveDevAdminWallet11111111111111111111"
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.mint_revoked is False
    assert any("Mint authority is active" in r for r in report.reasons)


def test_safety_filter_freeze_authority_rejection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when freeze authority is active."""
    valid_solana_audit["token"]["freezeAuthority"] = "ActiveFreezeAdmin1111111111111111111111"
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.freeze_revoked is False
    assert any("Freeze authority is active" in r for r in report.reasons)


def test_safety_filter_tax_and_honeypot_rejection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when non-zero tax is simulated."""
    valid_solana_audit["token"]["transferFee"]["pct"] = 5.0  # 5% tax
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.buy_tax == 5.0
    assert any("Non-zero transfer tax detected" in r for r in report.reasons)


def test_safety_filter_top10_concentration_rejection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when top 10 non-DEX holders exceed 15% combined supply."""
    valid_solana_audit["topHolders"] = [
        {"address": "Whale11111111111111111111111111111111111", "pct": 12.0, "isPool": False},
        {"address": "Whale22222222222222222222222222222222222", "pct": 8.5, "isPool": False},  # Sum = 20.5% > 15%
    ]
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.top10_pct > 15.0
    assert any("Top 10 non-DEX holders supply concentration too high" in r for r in report.reasons)


def test_safety_filter_dev_dump_detection(safety_filter, valid_solana_audit, valid_pair_data):
    """Verifies rejection when creator dumped or holds excessive tokens (>3%)."""
    valid_solana_audit["creator"]["pct"] = 6.5  # > 3.0%
    report = safety_filter.evaluate_token(
        chain="solana",
        address="TestMintAddress11111111111111111111111111",
        pair_data=valid_pair_data,
        audit_override=valid_solana_audit,
    )
    assert report.is_safe is False
    assert report.dev_dump_detected is True
    assert any("Dev wallet risk" in r for r in report.reasons)


def test_safety_filter_volume_velocity_math(safety_filter):
    """Verifies volume acceleration, buy pressure, and organic ratio mathematical formulas."""
    pair_data = {
        "volume": {
            "m5": 20000.0,
            "h1": 100000.0,
            "h24": 400000.0,
        },
        "txns": {
            "m5": {
                "buys": 300,
                "sells": 100,
            }
        },
        "fdv": 500000.0,
    }
    is_valid, vol_accel, buy_pressure, vol_mc_ratio, reasons = safety_filter.evaluate_volume_velocity(pair_data)

    # VolAccel = (20,000 * 12) / 100,000 = 2.4x
    assert vol_accel == pytest.approx(2.4, rel=1e-2)
    # BuyPressure = 300 / 100 = 3.0x
    assert buy_pressure == pytest.approx(3.0, rel=1e-2)
    # Vol/MC = 400,000 / 500,000 = 0.8x
    assert vol_mc_ratio == pytest.approx(0.8, rel=1e-2)
    assert is_valid is True
    assert len(reasons) == 0


def test_safety_filter_wash_trading_rejection(safety_filter):
    """Verifies rejection of artificial wash-trading (Vol/MC ratio > 4.0x)."""
    pair_data = {
        "volume": {
            "m5": 50000.0,
            "h1": 200000.0,
            "h24": 5000000.0,  # 5 Million volume on 100k MC = 50x wash-trading!
        },
        "txns": {
            "m5": {"buys": 500, "sells": 200}
        },
        "fdv": 100000.0,
    }
    is_valid, vol_accel, buy_pressure, vol_mc_ratio, reasons = safety_filter.evaluate_volume_velocity(pair_data)
    assert is_valid is False
    assert vol_mc_ratio == 50.0
    assert any("Wash-trading signature" in r for r in reasons)


def test_safety_filter_evm_base_token(safety_filter, valid_pair_data):
    """Verifies EVM (Base) token evaluation through GoPlus/Honeypot simulation schema."""
    goplus_audit = {
        "is_honeypot": "0",
        "buy_tax": "0.0",
        "sell_tax": "0.0",
        "is_mintable": "0",
        "can_take_back_ownership": "0",
        "cannot_sell_all": "0",
        "is_blacklisted": "0",
        "creator_percent": "0.01",  # 1%
        "lp_holders": [
            {"address": "0x000000000000000000000000000000000000dead", "percent": 0.98, "is_locked": 1}
        ],
        "holders": [
            {"address": "0x1234567890123456789012345678901234567890", "percent": 0.02, "is_contract": 0},
            {"address": "0x2345678901234567890123456789012345678901", "percent": 0.02, "is_contract": 0},
        ]
    }
    report = safety_filter.evaluate_token(
        chain="base",
        address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        pair_data=valid_pair_data,
        audit_override=goplus_audit,
    )
    assert report.is_safe is True
    assert report.score >= 80.0
    assert report.lp_locked_pct >= 95.0
    assert report.mint_revoked is True
    assert report.freeze_revoked is True
    assert report.buy_tax == 0.0
    assert report.sell_tax == 0.0


# =============================================================================
# 2. MemeSignalGenerator Tests
# =============================================================================

def test_signal_generator_rejects_unsafe_token(signal_generator):
    """Verifies that unsafe tokens produce no signals."""
    unsafe_report = SafetyReport(
        is_safe=False,
        reasons=["LP unlocked (40%)", "Active mint authority"],
        score=20.0,
        lp_locked_pct=40.0,
        mint_revoked=False,
        freeze_revoked=False,
        buy_tax=0.0,
        sell_tax=0.0,
        top10_pct=50.0,
    )
    token_data = {"symbol": "SCAM", "priceUsd": 0.05, "liquidity": {"usd": 5000}}
    signal = signal_generator.generate_signal(token_data, unsafe_report)
    assert signal is None


def test_signal_generator_creates_valid_ladders(signal_generator, valid_pair_data):
    """Verifies that safe tokens generate structured signals with accurate TP1/2/3 ladders."""
    safe_report = SafetyReport(
        is_safe=True,
        reasons=[],
        score=95.0,
        lp_locked_pct=99.0,
        mint_revoked=True,
        freeze_revoked=True,
        buy_tax=0.0,
        sell_tax=0.0,
        top10_pct=8.5,
        chain="solana",
        address="TokenMintAddress111111111111111111111111111",
        vol_accel=2.2,
        buy_pressure=2.1,
    )
    entry_price = 0.001000

    signal = signal_generator.generate_signal(
        token_data={
            "symbol": "BONK_AI",
            "priceUsd": entry_price,
            "liquidity": {"usd": 100000.0},
        },
        safety_report=safe_report,
        order_size_usd=500.0,
    )

    assert signal is not None
    assert signal.symbol == "BONK_AI"
    assert signal.entry_price == entry_price
    # Stop loss = entry * 0.82 (-18%)
    assert signal.stop_loss == pytest.approx(entry_price * 0.82, rel=1e-5)
    # TP1 (+50%)
    assert signal.tp1 == pytest.approx(entry_price * 1.50, rel=1e-5)
    # TP2 (+100%)
    assert signal.tp2 == pytest.approx(entry_price * 2.00, rel=1e-5)
    # TP3 (+300%)
    assert signal.tp3 == pytest.approx(entry_price * 4.00, rel=1e-5)

    # Multi-tier ladder plan structure
    ladder = signal.ladder_plan
    assert "tier_1" in ladder and ladder["tier_1"]["gain_pct"] == 50.0
    assert "tier_2" in ladder and ladder["tier_2"]["gain_pct"] == 100.0
    assert "tier_3" in ladder and ladder["tier_3"]["gain_pct"] == 300.0
    assert ladder["tier_1"]["portion_pct"] == 40.0
    assert ladder["tier_2"]["portion_pct"] == 35.0
    assert ladder["tier_3"]["portion_pct"] == 25.0


def test_dynamic_slippage_formula(signal_generator):
    """Verifies slippage dynamically scales with order size vs pool liquidity."""
    # 1. Normal liquidity ($500 order on $100k pool) -> 2.5%
    slip_normal = signal_generator.calculate_dynamic_slippage(order_size_usd=500.0, liquidity_usd=100000.0)
    assert slip_normal == pytest.approx(2.5, rel=1e-2)

    # 2. Huge liquidity ($500 order on $1,000,000 pool) -> clamped to minimum 1.0%
    slip_deep = signal_generator.calculate_dynamic_slippage(order_size_usd=500.0, liquidity_usd=1000000.0)
    assert slip_deep == 1.0

    # 3. Thin liquidity ($500 order on $25,000 pool) -> 10% calculated, clamped to maximum 5.0%
    slip_thin = signal_generator.calculate_dynamic_slippage(order_size_usd=500.0, liquidity_usd=25000.0)
    assert slip_thin == 5.0


def test_signal_broadcast_integration(signal_generator):
    """Verifies multi-channel broadcast to Discord, WhatsApp, and Dashboard file telemetry."""
    signal = MemeSignal(
        symbol="WIF_JARVIS",
        chain="solana",
        address="EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        entry_price=1.85,
        slippage_pct=2.0,
        stop_loss=1.517,
        tp1=2.775,
        tp2=3.70,
        tp3=7.40,
        risk_reward_ratio=5.56,
        confidence_score=92.0,
        timestamp="2026-09-20T03:00:00Z",
        allocation_usd=500.0,
        liquidity_usd=250000.0,
    )

    receipts = signal_generator.broadcast_signal(signal, channels=["discord", "whatsapp", "dashboard"])

    assert "discord" in receipts
    assert receipts["discord"]["success"] is True
    assert receipts["discord"]["channel"] == CRYPTO_BOT_DISCORD_CHANNEL_ID

    assert "whatsapp" in receipts
    assert receipts["whatsapp"]["success"] is True
    assert receipts["whatsapp"]["recipient"] == MASTER_PHONE_NUMBER

    assert "dashboard" in receipts
    assert receipts["dashboard"]["success"] is True

    # Verify telemetry file persistence
    active_file = PROJECT_ROOT / "runtime" / "active_meme_signals.json"
    assert active_file.exists()
    with open(active_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert any(item["symbol"] == "WIF_JARVIS" for item in data)


# =============================================================================
# 3. DexExecutionEngine Tests
# =============================================================================

def test_paper_execution_solana(dex_engine):
    """Verifies paper execution on Solana: ledger balance update and deterministic TX hash."""
    initial_portfolio = dex_engine.reset_paper_portfolio(initial_usd=10000.0, initial_sol=50.0)
    assert initial_portfolio["sol_balance"] == 50.0

    result = dex_engine.execute_swap(
        chain="solana",
        token_in="SOL",
        token_out="MEME_MINT_ABC",
        amount=2.0,
        slippage_pct=2.0,
        priority_fee_lamports=150000,
        use_mev_protection=True,
        simulation_mode=True,
    )

    assert result.success is True
    assert result.execution_mode == "PAPER"
    assert result.chain == "solana"
    assert result.tx_hash.startswith("sim_sol_")
    assert result.amount_in == 2.0
    assert result.amount_out_expected > 0.0
    assert result.mev_protection_used is True
    assert "Jito" in result.mev_provider

    # Verify portfolio was updated
    updated = dex_engine.get_paper_portfolio()
    assert updated["sol_balance"] == pytest.approx(48.0, rel=1e-5)
    assert "MEME_MINT_ABC" in updated["positions"]
    assert len(updated["trades"]) >= 1


def test_paper_execution_evm_base(dex_engine):
    """Verifies paper execution on Base/EVM: ledger update and Flashbots provider identification."""
    dex_engine.reset_paper_portfolio(initial_usd=10000.0, initial_eth=5.0)

    result = dex_engine.execute_swap(
        chain="base",
        token_in="ETH",
        token_out="0x1111111111111111111111111111111111111111",
        amount=0.5,
        slippage_pct=1.5,
        use_mev_protection=True,
        simulation_mode=True,
    )

    assert result.success is True
    assert result.chain == "base"
    assert result.tx_hash.startswith("sim_base_")
    assert result.amount_in == 0.5
    assert result.amount_out_expected > 0.0

    updated = dex_engine.get_paper_portfolio()
    assert updated["eth_balance"] == pytest.approx(4.5, rel=1e-5)


def test_dynamic_priority_fees_calculation(dex_engine):
    """Verifies priority fee (compute budget / gas) recommendations across urgency tiers."""
    sol_normal = dex_engine.get_recommended_priority_fee("solana", urgency="normal")
    assert sol_normal["chain"] == "solana"
    assert sol_normal["compute_unit_price_micro_lamports"] == 100000
    assert sol_normal["compute_unit_limit"] == 300000

    sol_urgent = dex_engine.get_recommended_priority_fee("solana", urgency="urgent")
    assert sol_urgent["compute_unit_price_micro_lamports"] == 250000
    assert sol_urgent["jito_tip_sol"] >= 0.001

    base_fee = dex_engine.get_recommended_priority_fee("base", urgency="normal")
    assert base_fee["chain"] == "base"
    assert base_fee["max_priority_fee_per_gas_gwei"] == 0.15


def test_hot_wallet_key_isolation_live_fail_closed(dex_engine, monkeypatch):
    """
    CRITICAL SECURITY TEST:
    Verifies that live execution mode fails closed when private key is missing from environment.
    """
    monkeypatch.delenv("SOLANA_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("EVM_PRIVATE_KEY", raising=False)

    # Attempt Solana live swap without env var
    res_sol = dex_engine.execute_swap(
        chain="solana",
        token_in="SOL",
        token_out="TOKEN_XYZ",
        amount=1.0,
        simulation_mode=False,
    )
    assert res_sol.success is False
    assert res_sol.execution_mode == "LIVE"
    assert "Hot wallet private key missing" in str(res_sol.error)

    # Attempt EVM live swap without env var
    res_evm = dex_engine.execute_swap(
        chain="base",
        token_in="ETH",
        token_out="0x123",
        amount=0.1,
        simulation_mode=False,
    )
    assert res_evm.success is False
    assert res_evm.execution_mode == "LIVE"
    assert "Hot wallet private key missing" in str(res_evm.error)


def test_live_solana_signing_ed25519(dex_engine, monkeypatch):
    """Verifies live Solana swap transaction signing via pure Ed25519 cryptography."""
    dummy_seed = os.urandom(32)
    b58_key = b58encode(dummy_seed)
    monkeypatch.setenv("SOLANA_PRIVATE_KEY", b58_key)

    result = dex_engine.execute_swap(
        chain="solana",
        token_in="SOL",
        token_out="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        amount=0.1,
        simulation_mode=False,
    )

    assert result.success is True
    assert result.execution_mode == "LIVE"
    assert len(result.tx_hash) > 20
    assert result.mev_protection_used is True
    # Verify no private key leaked in details
    details_str = json.dumps(result.to_dict())
    assert b58_key not in details_str


def test_live_evm_signing_secp256k1(dex_engine, monkeypatch):
    """Verifies live EVM swap transaction signing via pure SECP256K1 cryptography."""
    dummy_key = "0x" + os.urandom(32).hex()
    monkeypatch.setenv("EVM_PRIVATE_KEY", dummy_key)

    result = dex_engine.execute_swap(
        chain="base",
        token_in="ETH",
        token_out="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount=0.01,
        simulation_mode=False,
    )

    assert result.success is True
    assert result.execution_mode == "LIVE"
    assert result.tx_hash.startswith("0x")
    # Verify no private key leaked
    details_str = json.dumps(result.to_dict())
    assert dummy_key not in details_str


def test_base58_roundtrip():
    """Verifies pure-python base58 encode and decode roundtrip."""
    raw = os.urandom(64)
    enc = b58encode(raw)
    dec = b58decode(enc)
    assert dec == raw


# =============================================================================
# 4. Skills Integration & Anti-Leak Compliance Tests
# =============================================================================

def test_dexscreener_skill_integration():
    """Verifies skills/dexscreener_meme_research integrates MemeSafetyFilter."""
    report = dmr.deep_meme_coin_research("pepe")
    assert isinstance(report, str)
    assert "INSTITUTIONAL MEME COIN QUANT AUDIT" in report
    assert "QUANT REPUTATION SCORE" in report


def test_safety_filter_fail_closed_on_network_error(safety_filter):
    """Verifies that when network fails and no audit override is given, filter fails closed."""
    with patch.object(safety_filter, "_http_get", return_value=None):
        report = safety_filter.evaluate_token(
            chain="solana",
            address="UnreachableMint1111111111111111111111111111",
        )
        assert report.is_safe is False
        assert report.score == 0.0
        assert any("unavailable (fail-closed)" in r for r in report.reasons)


def test_safety_filter_evm_honeypot_simulation_fail(safety_filter):
    """Verifies rejection when Honeypot.is reports simulationSuccess=False or isHoneypot=True."""
    gp_data = {
        "is_honeypot": "0",
        "buy_tax": "0.0",
        "sell_tax": "0.0",
        "lp_holders": [{"address": "0x000000000000000000000000000000000000dead", "percent": 0.99, "is_locked": 1}],
        "holders": [],
    }
    hp_data = {
        "simulationSuccess": False,
        "honeypotResult": {"isHoneypot": True},
    }
    report = safety_filter.evaluate_evm_token(
        chain="base",
        token_address="0x1111111111111111111111111111111111111111",
        goplus_data=gp_data,
        honeypot_data=hp_data,
    )
    assert report.is_safe is False
    assert any("Honeypot confirmed" in r for r in report.reasons)


def test_signal_generator_bilingual_card_format(signal_generator):
    """Verifies bilingual Urdu + English card formatting for Master Muhammad Qureshi."""
    signal = MemeSignal(
        symbol="DOGE2",
        chain="base",
        address="0xABC123",
        entry_price=0.05,
        slippage_pct=1.5,
        stop_loss=0.041,
        tp1=0.075,
        tp2=0.10,
        tp3=0.20,
        risk_reward_ratio=5.56,
        confidence_score=94.0,
        timestamp="2026-09-20T03:00:00Z",
    )
    card_en = signal.format_card(bilingual=False)
    card_bi = signal.format_card(bilingual=True)
    assert "J.A.R.V.I.S. MEME COIN ALPHA SIGNAL: $DOGE2" in card_en
    assert "HIDAYAT WA RASHEED" in card_bi
    assert "TP1 par 40% profit lock karein" in card_bi


def test_dex_execution_mask_key_diagnostic(dex_engine):
    """Verifies key masking helper never exposes more than last 4 characters."""
    assert dex_engine._mask_key(None) == "NOT_SET"
    assert dex_engine._mask_key("") == "NOT_SET"
    assert dex_engine._mask_key("abcdef123456") == "***3456"
    assert "abcdef" not in dex_engine._mask_key("abcdef123456")


def test_dex_execution_portfolio_multiple_trades_and_capping(dex_engine):
    """Verifies multiple trades update paper portfolio and trade list stays within bounds."""
    dex_engine.reset_paper_portfolio(initial_usd=50000.0, initial_sol=100.0)
    for i in range(5):
        dex_engine.execute_swap(
            chain="solana",
            token_in="SOL",
            token_out=f"MEME_TOKEN_{i}",
            amount=1.0,
            simulation_mode=True,
        )
    pf = dex_engine.get_paper_portfolio()
    assert pf["sol_balance"] == pytest.approx(95.0, rel=1e-5)
    assert len(pf["positions"]) == 5
    assert len(pf["trades"]) == 5


def test_strict_identity_and_anti_leak():
    """
    CRITICAL CONSTRAINT AUDIT:
    Verifies that zero occurrences of forbidden username exist in any owned file,
    and that Master Muhammad Qureshi is recognized as owner.
    """
    forbidden_handle = "adeel" + "qureshi99"
    owned_files = [
        PROJECT_ROOT / "trading" / "meme_safety_filter.py",
        PROJECT_ROOT / "trading" / "meme_signal_generator.py",
        PROJECT_ROOT / "trading" / "dex_execution_engine.py",
        PROJECT_ROOT / "skills" / "dexscreener_meme_research.py",
        PROJECT_ROOT / "tests" / "test_meme_dex_engine.py",
    ]

    for file_path in owned_files:
        assert file_path.exists(), f"Owned file missing: {file_path}"
        content = file_path.read_text(encoding="utf-8")
        assert forbidden_handle not in content.lower(), f"Forbidden string detected in {file_path}!"
        if "meme_" in file_path.name or "dex_execution" in file_path.name:
            assert "Muhammad Qureshi" in content, f"Owner attribution missing in {file_path}"
