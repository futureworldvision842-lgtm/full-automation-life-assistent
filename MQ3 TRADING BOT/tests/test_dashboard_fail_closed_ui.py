"""Regression tests for dashboard evidence and capital provenance boundaries."""

from unittest.mock import MagicMock, patch

import dashboard.app as dashboard_module
from dashboard.app import app


def _client():
    app.config["TESTING"] = True
    return app.test_client()


def test_dashboard_html_has_no_static_directional_or_order_flow_claims():
    with _client() as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    forbidden = (
        "BUY HEAVY (64.5%)",
        "SWEPT ASIAN LOW",
        "Institutional Spring sweep of sell liquidity",
        "Risk Multiplier: 1.3x",
        ">LIVE</span>",
    )
    for claim in forbidden:
        assert claim not in html
    assert "Attributable global order flow / true CVD" in html
    assert "NOT CONNECTED" in html
    assert "REQUIRED GATE" in html


def test_market_weather_fails_closed_without_provenance():
    unverified_engine = MagicMock()
    unverified_engine.forecast_market_weather.return_value = {
        "updraft_probability": 99.0,
        "risk_multiplier": 2.0,
    }
    with patch.object(dashboard_module, "weather_engine", unverified_engine):
        with _client() as client:
            payload = client.get("/api/market_weather?symbol=XAUUSD").get_json()

    assert payload["status"] == "unavailable"
    assert payload["actionable"] is False
    assert payload["updraft_probability"] is None
    assert payload["risk_multiplier"] == 0.0
    assert payload["news_clearance"]["verified"] is False


def test_shark_forensics_fails_closed_without_attributable_feed():
    with _client() as client:
        payload = client.get("/api/shark_forensics?symbol=XAUUSD").get_json()

    assert payload["status"] == "unavailable"
    assert payload["actionable"] is False
    assert payload["cvd_divergence"]["buyer_ratio"] is None
    assert payload["wyckoff_phase"]["phase"] == "UNAVAILABLE"
    assert payload["order_book_imbalance"]["bid_volume_pct"] is None


def test_simulation_account_is_explicitly_unverified():
    engine = MagicMock()
    engine.mt5.get_account_info.return_value = {
        "available": True,
        "data_mode": "SIMULATION",
        "balance": 25_000.0,
        "equity": 25_000.0,
        "profit": 0.0,
    }
    engine.mt5.get_open_positions.return_value = []
    engine.risk_manager.target_account_size = 25_000.0
    engine.risk_manager.daily_starting_equity = 25_000.0
    engine.config = {"risk_management": {"max_daily_loss_pct": 1.5, "max_total_loss_pct": 4.0}}
    engine.ai_engine.get_ai_learning_summary.return_value = {}
    engine.admin_controller.get_system_telemetry.return_value = {}
    engine.running = False
    engine.paused = True
    engine.system_logs = []
    engine.stats = {}
    engine.whatsapp = None

    with patch.object(dashboard_module, "bot_engine", engine):
        with _client() as client:
            payload = client.get("/api/status").get_json()

    assert payload["data_mode"] == "SIMULATION"
    assert payload["account"]["telemetry_verified"] is False
    assert payload["account"]["capital_type"] == "SIMULATED_OR_UNVERIFIED"


def test_readiness_exposes_missing_live_promotion_gates():
    with _client() as client:
        payload = client.get("/api/readiness").get_json()

    accounts = payload["readiness"]["accounts"]
    assert accounts
    assert all(account["achieved_stage"] == "PAPER" for account in accounts)
    assert all(account["ready_for_full_live"] is False for account in accounts)
    assert all(account["missing_gates"] for account in accounts)
