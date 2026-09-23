from datetime import datetime, timedelta, timezone
import math
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.data_provenance import DataEnvelope, DataMode, execution_data_gate
from src.higgsfield_vision_engine import HiggsfieldVisionEngine
from src.bitget_connector import BitgetConnector
from src.mt5_connector import MT5Connector
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.predictive_weather_engine import PredictiveWeatherEngine


def test_synthetic_data_can_never_be_actionable():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        DataEnvelope(
            source="demo",
            mode=DataMode.SYNTHETIC,
            observed_at=now,
            received_at=now,
            actionable=True,
        )


def test_execution_gate_rejects_stale_and_synthetic_inputs():
    now = datetime.now(timezone.utc)
    live_but_stale = DataEnvelope(
        source="broker_quote",
        mode=DataMode.LIVE,
        observed_at=now - timedelta(minutes=5),
        received_at=now,
        actionable=True,
    )
    synthetic = DataEnvelope(
        source="demo_order_flow",
        mode=DataMode.SYNTHETIC,
        observed_at=now,
        received_at=now,
        actionable=False,
    )
    approved, reasons = execution_data_gate(
        [live_but_stale, synthetic], max_age_seconds=30, required_sources=["broker_quote"]
    )
    assert approved is False
    assert any("stale" in reason for reason in reasons)
    assert any("SYNTHETIC" in reason for reason in reasons)


def test_paper_connector_is_default_and_rejects_non_finite_volume():
    connector = MT5Connector()
    assert connector.simulation_mode is True
    result = connector.place_order("XAUUSD", "BUY", math.inf, 2650.0, 2640.0, 2670.0)
    assert result["success"] is False
    assert result["mode"] == "REJECTED"


def test_live_connector_is_locked_without_config_and_acknowledgement(monkeypatch):
    connector = MT5Connector(config={}, simulation_mode=False)
    connector.connected = True
    monkeypatch.delenv("MQ3_LIVE_TRADING_CONFIRMATION", raising=False)
    authorized, reason = connector._live_execution_authorized()
    assert authorized is False
    assert "disabled" in reason.lower()


def test_live_connectors_require_fresh_central_gate_receipt():
    assert MT5Connector._valid_central_admission(None)[0] is False
    assert BitgetConnector._valid_central_admission({})[0] is False

    stale = {
        "executor": "AutonomousFleetExecutor",
        "readiness_passed": True,
        "risk_passed": True,
        "market_admission_passed": True,
        "signal_quality_passed": True,
        "issued_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
    }
    assert MT5Connector._valid_central_admission(stale)[0] is False
    assert BitgetConnector._valid_central_admission(stale)[0] is False


def test_fleet_onboarder_cannot_overwrite_main_application_config(tmp_path):
    main_config = tmp_path / "config.json"
    original = '{"execution":{"live_enabled":false},"risk_management":{"risk_per_trade_pct":0.25}}'
    main_config.write_text(original, encoding="utf-8")
    onboarder = MultiAccountAutoOnboarder(config_path=str(main_config))
    onboarder.onboard_new_account(
        account_id="TEST",
        server="DEMO",
        balance=5_000,
        account_type="FUNDING_PIPS",
        prop_model="FUNDING_PIPS_2_STEP_STANDARD",
    )
    assert main_config.read_text(encoding="utf-8") == original


def test_insufficient_visual_data_fails_closed():
    engine = HiggsfieldVisionEngine()
    result = engine.audit_candlestick_rejection_visually(pd.DataFrame(), "BUY")
    assert result["is_clean_rejection"] is False
    assert result["visual_conviction"] == 0.0
    assert result["data_mode"] == "INSUFFICIENT_DATA"


def test_legacy_weather_model_cannot_authorize_execution_or_increase_size():
    radar = MagicMock()
    radar.scan_satellite_grid.return_value = {
        "radar_score": 99.0,
        "storm_warning": False,
        "pressure_differential_pct": 0.5,
    }
    world = MagicMock()
    world.get_world_intelligence_brief.return_value = {
        "defcon_level": 3,
        "global_risk_index": 10.0,
    }
    world.get_geopolitical_market_bias.return_value = {"bias": "STRONG_BUY"}
    calendar = MagicMock()
    calendar.evaluate_news_clearance.return_value = {
        "active_event": None,
        "lockout_reason": "CLEAR_NO_BLACKOUT",
    }

    result = PredictiveWeatherEngine(
        world_monitor=world,
        calendar_radar=calendar,
        satellite_radar=radar,
    ).forecast_market_weather(symbol="XAUUSD")

    assert result["data_mode"] == "MODEL_HYPOTHESIS"
    assert result["actionable"] is False
    assert result["risk_multiplier"] == 0.0
    assert result["strategy_weight_multiplier"] == 0.0
    assert result["trade_policy"] == "RESEARCH_ONLY_NO_EXECUTION"
