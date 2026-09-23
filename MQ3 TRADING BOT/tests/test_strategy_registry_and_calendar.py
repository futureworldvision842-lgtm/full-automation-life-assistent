"""Unit and integration tests for Strategy Registry & Economic Calendar Service.

Verifies:
1. Versioned strategy definitions & regime gating.
2. Validation receipts & expiry checks.
3. Official macro calendar pre-news freezes & post-news cooldowns.
4. Currency and asset class isolation.
"""

import datetime
import pytest
from src.strategy_registry import (
    StrategyRegistry,
    StrategyDefinition,
    StrategyStage,
    MarketRegimeType,
    ValidationReceipt,
)
from src.economic_calendar_service import (
    EconomicCalendarService,
    EconomicEvent,
    EventImpact,
)


def test_strategy_registry_returns_versioned_definitions():
    reg = StrategyRegistry()
    strats = reg.list_strategies()
    assert len(strats) >= 7

    trend_strat = reg.get_strategy("STRAT_TREND_CONT_OTE", "1.0.0")
    assert trend_strat is not None
    assert trend_strat.family == "Trend"
    assert trend_strat.min_risk_reward_ratio >= 2.0
    assert "XAUUSD" in trend_strat.supported_symbols
    assert trend_strat.active_validation_receipt is not None
    assert trend_strat.active_validation_receipt.lookahead_audit_passed is True


def test_strategy_regime_filtering():
    reg = StrategyRegistry()
    trend_strat = reg.get_strategy("STRAT_TREND_CONT_OTE", "1.0.0")

    # Eligible in TRENDING_NORMAL
    ok, reason = trend_strat.is_regime_eligible("TRENDING_NORMAL")
    assert ok is True

    # Ineligible in RANGE_NORMAL
    ok, reason = trend_strat.is_regime_eligible("RANGE_NORMAL")
    assert ok is False
    assert "strictly prohibited" in reason or "not in eligible" in reason

    # Ineligible in VOLATILITY_SHOCK
    ok, reason = trend_strat.is_regime_eligible("VOLATILITY_SHOCK")
    assert ok is False

    # Check eligible strategies query
    eligible_trending = reg.get_eligible_strategies("XAUUSD", "M15", "TRENDING_NORMAL")
    strat_ids = [s.strategy_id for s in eligible_trending]
    assert "STRAT_TREND_CONT_OTE" in strat_ids
    assert "STRAT_RANGE_MEAN_REV" not in strat_ids


def test_strategy_validation_receipt_expiry():
    receipt = ValidationReceipt(
        receipt_id="VR_TEST_01",
        strategy_id="STRAT_TEST",
        strategy_version="1.0.0",
        data_sources=["MT5_OHLCV"],
        sample_start_utc="2025-01-01T00:00:00Z",
        sample_end_utc="2025-12-31T23:59:59Z",
        symbols=["EURUSD"],
        timeframes=["M15"],
        total_trades=100,
        win_rate_pct=55.0,
        profit_factor=1.6,
        expectancy_r=0.4,
        max_drawdown_pct=3.0,
        sharpe_ratio=1.5,
        slippage_sensitivity_score=0.9,
        lookahead_audit_passed=True,
        walk_forward_efficiency_pct=75.0,
        approved_stage=StrategyStage.DEMO,
        approved_at_utc="2026-01-01T00:00:00Z",
        expiry_date_utc="2026-06-01T00:00:00Z",
    )
    # Check valid before expiry
    assert receipt.is_expired("2026-05-01T00:00:00Z") is False
    # Check expired after expiry
    assert receipt.is_expired("2026-07-01T00:00:00Z") is True


def test_economic_calendar_pre_news_freeze():
    cal = EconomicCalendarService()
    cal._events.clear()

    # Event scheduled at 14:00 UTC
    cal.register_event(EconomicEvent(
        event_id="EV_TEST_CPI",
        event_name="US CPI Release Test",
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_utc="2026-08-20T14:00:00Z",
        pre_lockout_minutes=15,
        post_cooldown_minutes=15,
        source_agency="US Bureau of Labor Statistics",
        source_url="https://www.bls.gov/cpi/",
    ))

    # At 13:50 UTC (10 mins before): XAUUSD should be LOCKED
    locked, reason, ev = cal.evaluate_symbol_lockout("XAUUSD", "2026-08-20T13:50:00Z")
    assert locked is True
    assert "Pre-news freeze" in reason
    assert "US CPI Release Test" in reason

    # At 13:40 UTC (20 mins before): XAUUSD should be CLEAR
    locked, reason, ev = cal.evaluate_symbol_lockout("XAUUSD", "2026-08-20T13:40:00Z")
    assert locked is False
    assert "Market clear" in reason


def test_economic_calendar_post_news_cooldown():
    cal = EconomicCalendarService()
    cal._events.clear()

    cal.register_event(EconomicEvent(
        event_id="EV_TEST_FOMC",
        event_name="FOMC Decision Test",
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_utc="2026-08-20T18:00:00Z",
        pre_lockout_minutes=15,
        post_cooldown_minutes=15,
    ))

    # At 18:05 UTC (5 mins after): EURUSD should be in COOLDOWN
    locked, reason, ev = cal.evaluate_symbol_lockout("EURUSD", "2026-08-20T18:05:00Z")
    assert locked is True
    assert "Post-news cooldown" in reason

    # At 18:20 UTC (20 mins after): EURUSD should be CLEAR
    locked, reason, ev = cal.evaluate_symbol_lockout("EURUSD", "2026-08-20T18:20:00Z")
    assert locked is False


def test_economic_calendar_currency_isolation():
    cal = EconomicCalendarService()
    cal._events.clear()

    # ECB Event for EUR
    cal.register_event(EconomicEvent(
        event_id="EV_TEST_ECB",
        event_name="ECB Rate Test",
        currency="EUR",
        impact=EventImpact.HIGH,
        scheduled_utc="2026-08-20T12:15:00Z",
        pre_lockout_minutes=15,
        post_cooldown_minutes=15,
    ))

    # At 12:10 UTC: EURUSD must be locked, but USDJPY must be clear
    locked_eur, _, _ = cal.evaluate_symbol_lockout("EURUSD", "2026-08-20T12:10:00Z")
    locked_jpy, _, _ = cal.evaluate_symbol_lockout("USDJPY", "2026-08-20T12:10:00Z")

    assert locked_eur is True
    assert locked_jpy is False


def test_economic_event_official_sources_attribution():
    cal = EconomicCalendarService()
    events = cal.get_upcoming_events(horizon_hours=48)
    for ev in events:
        assert ev["source_agency"] != ""
        assert ev["source_url"].startswith("http")
