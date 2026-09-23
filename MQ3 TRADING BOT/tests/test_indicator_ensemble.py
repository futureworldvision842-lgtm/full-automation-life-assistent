from pathlib import Path

import numpy as np
import pandas as pd

from src.broker_signal_research import BrokerSignalResearchEngine
from src.indicator_ensemble import ExplainableIndicatorEnsemble
from tests.test_broker_signal_research import FakeConnector, make_config


def make_frame(direction: str = "up", bars: int = 270) -> pd.DataFrame:
    index = np.arange(bars, dtype=float)
    baseline = 100.0 + index * 0.12 if direction == "up" else 132.0 - index * 0.12
    close = baseline + np.sin(index / 7.0) * 0.18
    open_ = close - 0.05 if direction == "up" else close + 0.05
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=bars, freq="15min", tz="UTC"),
            "open": open_,
            "high": np.maximum(open_, close) + 0.25,
            "low": np.minimum(open_, close) - 0.25,
            "close": close,
            "tick_volume": 100.0 + (index % 40.0) * 3.0,
        }
    )


def test_trend_ensemble_is_bounded_explainable_and_never_actionable():
    result = ExplainableIndicatorEnsemble().analyze(make_frame("up"), "M15")

    assert result["status"] == "AVAILABLE"
    assert result["directional_bias"] == "BULLISH"
    assert -100.0 <= result["ensemble_score"] <= 100.0
    assert result["regime"].startswith("TRENDING")
    assert result["forming_bar_used"] is False
    assert result["actionable"] is False
    assert result["decision_use"] == "CONFLICT_GUARD_AND_EXPLANATION_ONLY"
    assert set(result["families"]) == {"trend", "momentum", "structure", "activity"}
    assert "not independent probabilities" in result["warning"]
    assert result["indicators"]["rsi14"] > 50.0


def test_downtrend_is_symmetric_and_reports_bearish_families():
    result = ExplainableIndicatorEnsemble().analyze(make_frame("down"), "H1")

    assert result["status"] == "AVAILABLE"
    assert result["directional_bias"] == "BEARISH"
    assert result["bearish_families"] >= 3
    assert result["indicators"]["rsi14"] < 50.0


def test_insufficient_history_fails_closed_with_warmup_requirement():
    result = ExplainableIndicatorEnsemble().analyze(make_frame("up", 100), "M15")

    assert result["status"] == "UNAVAILABLE"
    assert result["actionable"] is False
    assert "220 closed broker bars" in result["reason"]


def test_appending_future_bars_does_not_change_past_features():
    engine = ExplainableIndicatorEnsemble()
    frame = make_frame("up", 300)
    prefix_features = engine.feature_frame(frame.iloc[:250]).iloc[-1]
    full_features_at_same_time = engine.feature_frame(frame).iloc[249]

    for feature in (
        "ema20", "ema50", "ema200", "atr14", "rsi14", "macd_hist", "adx14",
        "bb_percent_b", "stoch_k", "roc10_pct", "donchian_position",
        "efficiency_ratio10", "volume_z20", "signed_activity20",
    ):
        assert prefix_features[feature] == full_features_at_same_time[feature]


def test_signal_research_exposes_ensemble_without_order_authority():
    connector = FakeConnector("up")
    result = BrokerSignalResearchEngine(connector, make_config()).analyze("XAUUSD")

    ensemble = result["indicator_ensemble"]
    assert ensemble["status"] == "AVAILABLE"
    assert ensemble["actionable"] is False
    assert ensemble["primary_timeframe"] == "M15"
    assert set(ensemble["timeframes"]) == {"M5", "M15", "H1", "H4"}
    assert result["execution_ready"] is False
    assert connector.order_calls == 0


def test_dashboard_retires_unsupported_panels_and_future_candles():
    root = Path(__file__).resolve().parents[1]
    html = (root / "dashboard" / "templates" / "index.html").read_text(encoding="utf-8")
    app_source = (root / "dashboard" / "app.py").read_text(encoding="utf-8")

    assert "Closed-Bar Indicator &amp; Regime Lab" in html
    assert "Capability &amp; Data Truth" in html
    assert "Forex & Crypto Market Weather Center" not in html
    assert "Maritime Threat Radar" not in html
    assert "Order-Flow Evidence Monitor" not in html
    assert "future_projected_candles = []" in app_source
    assert "generate_institutional_forecast(" not in app_source

