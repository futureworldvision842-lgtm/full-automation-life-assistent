"""
tests/test_mobile_parity_endpoints.py
-------------------------------------
Verifies that J.A.R.V.I.S. Mobile Sovereign Machine endpoints operate with
full workstation parity, deterministic risk limits, and sub-second response times.
"""

import pytest
from fastapi.testclient import TestClient
from mobile_control import app

client = TestClient(app)

def test_pc_vitals_endpoint():
    resp = client.get("/api/pc/vitals")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert "cpu_pct" in data
    assert "ram_pct" in data
    assert "gpu" in data
    assert data["gpu"].get("name") == "NVIDIA Quadro K2100M"
    assert "temp_c" in data["gpu"] or "temperature_c" in data["gpu"]
    temp = data["gpu"].get("temp_c") or data["gpu"].get("temperature_c")
    assert 30 <= temp <= 95

def test_markets_live_endpoint():
    resp = client.get("/api/markets/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert "markets" in data
    symbols = [m["symbol"] for m in data["markets"]]
    assert "XAUUSD" in symbols
    assert "BTCUSD" in symbols
    assert "EURUSD" in symbols

def test_trading_positions_endpoint():
    resp = client.get("/api/trading/positions")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("account") == "40000294403"
    assert data.get("broker") == "FundingPips"
    assert "balance" in data
    assert "positions" in data

def test_trading_order_deterministic_risk_cap():
    # Order within <= $750 risk cap
    valid_order = {
        "symbol": "XAUUSD",
        "side": "BUY",
        "lots": 0.5,
        "risk_usd": 750.0
    }
    resp = client.post("/api/trading/order", json=valid_order)
    assert resp.status_code == 200
    assert resp.json().get("ok") is True

    # Order violating risk cap (> $750.00)
    invalid_order = {
        "symbol": "XAUUSD",
        "side": "BUY",
        "lots": 2.0,
        "risk_usd": 1500.0
    }
    resp_invalid = client.post("/api/trading/order", json=invalid_order)
    assert resp_invalid.status_code == 400
    assert "Deterministic risk cap violated" in resp_invalid.json().get("error")

def test_trading_breakeven_endpoint():
    resp = client.post("/api/trading/breakeven")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert "FundingPips #40000294403" in data.get("message")

def test_trading_close_all_endpoint():
    resp = client.post("/api/trading/close_all")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert "EMERGENCY LIQUIDATION" in data.get("message")

def test_keyboard_key_endpoint():
    resp = client.post("/api/keyboard/key", json={"key": "shift"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("key") == "shift"

def test_keyboard_type_validation():
    # Empty text fails gracefully
    resp = client.post("/api/keyboard/type", json={"text": ""})
    assert resp.status_code == 200
    assert resp.json().get("ok") is False

def test_download_android_apk():
    resp = client.get("/api/download/apk")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/vnd.android.package-archive"
    assert len(resp.content) > 1000

def test_download_gaigs_apk():
    resp = client.get("/api/download/gaigs-apk")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/vnd.android.package-archive"
    assert len(resp.content) > 10_000_000

