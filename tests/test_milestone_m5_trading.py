"""
tests/test_milestone_m5_trading.py — Autonomous Trading, Macro Strategy & Meme Coin Alpha Radar
=============================================================================================
Verification test suite for Milestone M5:
1. 3D Orderbook Depth, CVD Absorption & Liquidity Heatmap for Gold, EURUSD, BTC, SOL.
2. Solana Pump.fun & Raydium Meme Coin Alpha Radar (bonding curves, whale signals, volume surge).
3. AI-Trader Consensus Stream (Bullish Advocate, Bearish Challenger, Risk Officer veto,
   closed-bar evidence score, geopolitical news impact correlation).
4. Strict Deterministic Risk Enforcement on FundingPips #40000294403 ($750 / 0.75% max cap,
   1:2.5 min RR, +1.0R dynamic breakeven trigger, emergency panic close-all).
5. Private Key Isolation (SOLANA_PRIVATE_KEY, EVM_PRIVATE_KEY strictly from env).
6. Dashboard Trading API endpoints & WebSocket stream.
7. Frontend 3D component TradingAlphaRadar3D.js.

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
"""

import os
import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading.trading_service import (
    generate_3d_orderbook_depth,
    generate_3d_liquidity_heatmap,
    normalize_symbol,
    get_asset_config
)
from trading.pump_fun_scanner import (
    PumpFunScanner,
    get_pump_fun_scanner,
    PUMP_FUN_GRADUATION_SOL_THRESHOLD
)
from trading.consensus_chamber import (
    ConsensusChamber,
    get_consensus_chamber,
    RiskOfficer,
    BullishAdvocate,
    BearishChallenger
)
from core.trading.reasoning import BigSharksReasoningEngine
from dashboard import app


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# 1. 3D ORDERBOOK DEPTH, CVD ABSORPTION & LIQUIDITY HEATMAPS
# =============================================================================

@pytest.mark.parametrize("symbol", ["XAUUSD", "EURUSD", "BTC", "SOL"])
def test_3d_orderbook_depth_multi_asset(symbol):
    """Verifies Level-2 3D DOM depth, cumulative volume, and CVD absorption for Gold, EURUSD, BTC, SOL."""
    data = generate_3d_orderbook_depth(symbol, levels=20)
    assert data["ok"] is True
    assert data["symbol"] == normalize_symbol(symbol)
    assert data["mid_price"] > 0
    assert data["spread"] > 0
    assert data["spread_bps"] > 0
    assert len(data["bids"]) == 20
    assert len(data["asks"]) == 20

    # Ensure cumulative volumes are strictly monotonically increasing
    for i in range(1, len(data["bids"])):
        assert data["bids"][i]["cum_volume"] >= data["bids"][i - 1]["cum_volume"]
    for i in range(1, len(data["asks"])):
        assert data["asks"][i]["cum_volume"] >= data["asks"][i - 1]["cum_volume"]

    # Ensure CVD absorption curve is present
    cvd = data["cvd_absorption"]
    assert "net_delta" in cvd
    assert "absorption_type" in cvd
    assert len(cvd["curve"]) == 20

    # Ensure whale walls are detected with asset-specific thresholds
    assert "whale_walls" in data
    assert isinstance(data["whale_walls"], list)
    assert len(data["whale_walls"]) > 0


@pytest.mark.parametrize("symbol", ["XAUUSD", "EURUSD", "BTC", "SOL"])
def test_3d_liquidity_heatmap_multi_asset(symbol):
    """Verifies 3D spatial liquidity heatmap grid, price levels, and iceberg clusters."""
    data = generate_3d_liquidity_heatmap(symbol)
    assert data["ok"] is True
    assert data["symbol"] == normalize_symbol(symbol)
    assert data["price_levels_count"] == 28
    assert data["time_slices_count"] == 20
    assert len(data["heatmap_grid"]) == 28
    assert len(data["heatmap_matrix_3d"]) == 20  # 20 time slices
    assert len(data["heatmap_matrix_3d"][0]) == 28  # 28 price levels per slice

    # Verify absorption zones exist
    zones = data["absorption_zones"]
    assert len(zones) >= 2
    types = [z["type"] for z in zones]
    assert "DEMAND_ABSORPTION_CLUSTER" in types
    assert "SUPPLY_OVERHEAD_CLUSTER" in types


# =============================================================================
# 2. SOLANA PUMP.FUN & RAYDIUM MEME COIN ALPHA RADAR
# =============================================================================

def test_pump_fun_bonding_curve_calculation():
    """Verifies Pump.fun curve progression: 0% to 100% and graduation at 85 SOL."""
    scanner = PumpFunScanner()

    # Zero SOL reserves -> 0% progress
    p0, mc_sol0, mc_usd0, grad0 = scanner.calculate_bonding_curve(0.0)
    assert p0 == 0.0
    assert grad0 is False

    # Halfway (42.5 SOL) -> 50% progress
    p50, mc_sol50, mc_usd50, grad50 = scanner.calculate_bonding_curve(42.5)
    assert abs(p50 - 50.0) < 0.1
    assert grad50 is False

    # Graduation (85.0 SOL) -> 100% progress and graduated
    p100, mc_sol100, mc_usd100, grad100 = scanner.calculate_bonding_curve(85.0)
    assert p100 == 100.0
    assert grad100 is True
    assert mc_usd100 > 0


def test_pump_fun_volume_velocity_and_whale_detection():
    """Verifies 5m volume acceleration, buy pressure, and whale accumulation scoring."""
    scanner = PumpFunScanner()

    # Test surging volume velocity: 5m = $20k, 1h = $60k -> (20000*12)/60000 = 4.0x
    vol_accel, buy_pressure, is_surging = scanner.compute_volume_velocity(
        vol_5m=20000.0, vol_1h=60000.0, buys_5m=150, sells_5m=50
    )
    assert vol_accel == 4.0
    assert buy_pressure == 3.0
    assert is_surging is True

    # Test whale accumulation detection
    trades = [
        {"side": "BUY", "sol_amount": 12.0, "user": "WhaleA"},
        {"side": "BUY", "sol_amount": 7.5, "user": "WhaleB"},
        {"side": "BUY", "sol_amount": 1.2, "user": "RetailA"},  # Below 5 SOL
        {"side": "SELL", "sol_amount": 10.0, "user": "SellerA"},
    ]
    whale_count, whale_score, signals = scanner.analyze_whale_activity(trades)
    assert whale_count == 2
    assert whale_score > 50.0
    assert len(signals) == 2


def test_pump_fun_scanner_radar_summary():
    """Verifies get_radar_summary returns high conviction tokens and safety verdicts."""
    scanner = get_pump_fun_scanner()
    summary = scanner.get_radar_summary()
    assert summary["ok"] is True
    assert summary["chain"] == "solana"
    assert summary["total_tracked"] >= 4
    assert "tokens" in summary
    assert isinstance(summary["tokens"], list)

    # Validate token fields
    token = summary["tokens"][0]
    assert "mint" in token
    assert "symbol" in token
    assert "bonding_curve_pct" in token
    assert "vol_accel" in token
    assert "alpha_conviction_score" in token
    assert "safety_verdict" in token


# =============================================================================
# 3. AI-TRADER CONSENSUS STREAM (CHAMBER DEBATE & VETO POWER)
# =============================================================================

def test_consensus_chamber_approval_with_closed_bar_and_geopolitics():
    """Verifies that a compliant trade on Gold reaches high conviction consensus."""
    chamber = get_consensus_chamber(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)

    proposal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "entry_price": 2715.0,
        "stop_loss": 2707.0,   # 8 pts risk
        "take_profit": 2736.0,  # 21 pts reward -> R:R = 2.625
        "account_id": "40000294403",
        "account_balance": 100000.0,
        "risk_pct": 0.50,       # 0.5% <= 0.75%
        "risk_usd": 500.0,      # $500 <= $750
        "rr_ratio": 2.625,
    }

    result = chamber.debate(proposal)
    assert result.approved is True
    assert result.status == "APPROVED_HIGH_CONVICTION"
    assert result.consensus_score >= 70.0
    assert result.closed_bar_evidence_score > 0.0
    assert "correlation_bias" in result.geopolitical_news_impact
    assert result.execution_plan is not None
    assert result.execution_plan["breakeven_trigger_price"] == 2723.0  # Entry + 1.0R


def test_consensus_chamber_risk_officer_unanimous_veto_risk_cap():
    """Verifies that Risk Officer strictly VETOES any trade exceeding 0.75% / $750 cap."""
    chamber = ConsensusChamber(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)

    proposal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "entry_price": 2715.0,
        "stop_loss": 2707.0,
        "take_profit": 2740.0,
        "account_id": "40000294403",
        "account_balance": 100000.0,
        "risk_pct": 0.95,       # EXCEEDS 0.75%
        "risk_usd": 950.0,      # EXCEEDS $750
        "rr_ratio": 3.1,
    }

    result = chamber.debate(proposal)
    assert result.approved is False
    assert result.status == "VETOED_BY_RISK_OFFICER"
    assert result.consensus_score == 0.0
    assert "exceeds" in result.veto_reason.lower()


def test_consensus_chamber_risk_officer_veto_insufficient_rr():
    """Verifies that Risk Officer strictly VETOES trades with R:R < 2.5."""
    chamber = ConsensusChamber(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)

    proposal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "entry_price": 2715.0,
        "stop_loss": 2705.0,   # 10 pts risk
        "take_profit": 2725.0,  # 10 pts reward -> R:R = 1.0 < 2.5
        "account_id": "40000294403",
        "account_balance": 100000.0,
        "risk_pct": 0.50,
        "risk_usd": 500.0,
        "rr_ratio": 1.0,
    }

    result = chamber.debate(proposal)
    assert result.approved is False
    assert result.status == "VETOED_BY_RISK_OFFICER"
    assert "below required threshold of 2.5" in result.veto_reason


def test_consensus_chamber_risk_officer_veto_news_blackout():
    """Verifies that Risk Officer strictly VETOES trades scheduled during 15-minute news blackout."""
    chamber = ConsensusChamber(max_risk_pct=0.75, max_risk_usd=750.0, min_rr=2.5)

    proposal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "entry_price": 2715.0,
        "stop_loss": 2705.0,
        "take_profit": 2745.0,
        "account_id": "40000294403",
        "account_balance": 100000.0,
        "risk_pct": 0.50,
        "risk_usd": 500.0,
        "rr_ratio": 3.0,
    }

    market_context = {
        "minutes_to_high_impact_news": 8.0  # Within 15m blackout
    }

    result = chamber.debate(proposal, market_context)
    assert result.approved is False
    assert result.status == "VETOED_BY_RISK_OFFICER"
    assert "blackout" in result.veto_reason.lower()


# =============================================================================
# 4. DETERMINISTIC RISK ENFORCEMENT ON FUNDINGPIPS #40000294403
# =============================================================================

def test_funding_pips_risk_governance_status():
    """Verifies FundingPips #40000294403 status rules ($750 max risk, 1:2.5 min RR, +1.0R BE)."""
    engine = BigSharksReasoningEngine()
    status = engine.get_funding_pips_risk_status()
    assert status["ok"] is True
    assert status["account_id"] == "40000294403"
    assert status["firm"] == "FundingPips"
    assert status["max_risk_cap_usd"] == 750.0
    assert status["max_risk_pct"] == 0.75
    assert status["min_rr_ratio"] == 2.5
    assert status["dynamic_breakeven_r_trigger"] == 1.0
    assert status["news_circuit_breaker_minutes"] == 15
    assert status["is_compliant"] is True


def test_dynamic_breakeven_trigger_lock():
    """Verifies that dynamic breakeven locks stop loss to entry price at +1.0R."""
    engine = BigSharksReasoningEngine()

    # Case 1: Trade at +0.5R profit (breakeven not locked yet)
    be_hold = engine.evaluate_dynamic_breakeven(
        entry_price=2700.0, current_price=2705.0, sl_price=2690.0, direction="BUY", profit_usd=250.0
    )
    assert be_hold["breakeven_locked"] is False
    assert be_hold["action"] == "hold"

    # Case 2: Trade reaches +1.0R profit (entry 2700, SL 2690, current 2710 -> R=1.0)
    be_lock = engine.evaluate_dynamic_breakeven(
        entry_price=2700.0, current_price=2710.0, sl_price=2690.0, direction="BUY", profit_usd=500.0
    )
    assert be_lock["breakeven_locked"] is True
    assert be_lock["action"] == "lock_sl_to_entry"
    assert be_lock["new_sl"] == 2700.0


# =============================================================================
# 5. PRIVATE KEY ISOLATION
# =============================================================================

def test_private_key_isolation_no_disk_leaks():
    """Verifies that hot wallet keys are strictly sourced via environment variables."""
    from trading.dex_execution_engine import DexExecutionEngine
    engine = DexExecutionEngine(mode="PAPER")

    # In PAPER mode, get_solana_private_key reads from os.environ
    assert engine.get_solana_private_key() == os.environ.get("SOLANA_PRIVATE_KEY")
    assert engine.get_evm_private_key() == os.environ.get("EVM_PRIVATE_KEY")

    # Verify that no file in runtime/ or config/ stores raw private keys
    runtime_dir = ROOT / "runtime"
    if runtime_dir.exists():
        for file in runtime_dir.glob("*.json"):
            content = file.read_text(encoding="utf-8")
            assert "SOLANA_PRIVATE_KEY=" not in content
            assert "EVM_PRIVATE_KEY=" not in content


# =============================================================================
# 6. FASTAPI DASHBOARD TRADING ENDPOINTS
# =============================================================================

def test_dashboard_api_trading_orderbook(client):
    """GET /api/trading/orderbook/{symbol} returns Level-2 3D depth and CVD curve."""
    res = client.get("/api/trading/orderbook/XAUUSD")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["symbol"] == "XAUUSD"
    assert "bids" in data
    assert "asks" in data
    assert "cvd_absorption" in data


def test_dashboard_api_trading_heatmap(client):
    """GET /api/trading/heatmap/{symbol} returns 3D liquidity heatmap terrain."""
    res = client.get("/api/trading/heatmap/BTC")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["symbol"] == "BTC"
    assert "heatmap_grid" in data
    assert "heatmap_matrix_3d" in data


def test_dashboard_api_trading_pump_radar(client):
    """GET /api/trading/pump_radar returns Solana Pump.fun alpha candidates."""
    res = client.get("/api/trading/pump_radar")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["chain"] == "solana"
    assert len(data["tokens"]) > 0


def test_dashboard_api_trading_risk_status(client):
    """GET /api/trading/risk_status returns FundingPips #40000294403 parameters."""
    res = client.get("/api/trading/risk_status")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["account_id"] == "40000294403"
    assert data["max_risk_cap_usd"] == 750.0


def test_dashboard_api_trading_council(client):
    """GET /api/trading/council/{symbol} returns live Consensus Chamber debate."""
    res = client.get("/api/trading/council/SOL")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["symbol"] == "SOL"
    assert "council_verdict" in data
    assert "agents" in data
    assert "closed_bar_evidence_score" in data
    assert "geopolitical_news_impact" in data


def test_dashboard_api_trading_close_all(client):
    """POST /api/trading/close_all executes 1-tap panic liquidation."""
    res = client.post("/api/trading/close_all")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["executed"] is True
    assert "PANIC CLOSE-ALL" in data["message"] or "LIQUIDATION" in data["message"] or "closed" in data["message"].lower()


# =============================================================================
# 7. FRONTEND 3D VISUALIZER ARTIFACT
# =============================================================================

def test_frontend_trading_alpha_radar_3d_file():
    """Verifies that web/js/TradingAlphaRadar3D.js is created and populated."""
    js_path = ROOT / "web" / "js" / "TradingAlphaRadar3D.js"
    assert js_path.exists()
    content = js_path.read_text(encoding="utf-8")
    assert len(content) > 5000
    assert "TradingAlphaRadar3D" in content
    assert "renderOrderbook3D" in content
    assert "renderHeatmap3D" in content
    assert "emergencyPanicClose" in content
    assert "FundingPips #40000294403" in content
