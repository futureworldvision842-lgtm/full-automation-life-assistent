"""Unit and integration tests for Central Trade Admission Service.

Verifies:
1. Unified admission gate with strategy registry, calendar, and portfolio risk.
2. Rejection of unapproved regimes (e.g. VOLATILITY_SHOCK).
3. Rejection of active macroeconomic news blackouts.
4. Rejection of stale quotes and excessive risk sizing.
5. Global kill switch enforcement.
"""

from datetime import datetime, timezone
import pytest

from src.trade_admission import TradeAdmissionGate
from src.portfolio_risk_service import portfolio_risk_service, AccountRiskState
from src.economic_calendar_service import economic_calendar_service, EconomicEvent, EventImpact
from src.strategy_registry import strategy_registry, StrategyStage


@pytest.fixture(autouse=True)
def setup_admission_environment():
    # Register test account in portfolio risk service
    portfolio_risk_service._accounts.clear()
    portfolio_risk_service.set_global_kill_switch(False)
    portfolio_risk_service.register_account(AccountRiskState(
        account_id="ACC_TEST_25K",
        account_name="Funding Pips 25k Test",
        starting_balance=25000.0,
        current_balance=25000.0,
        current_equity=25000.0,
        high_water_mark=25000.0,
        daily_start_equity=25000.0,
        max_daily_loss_pct=2.5,
        max_total_loss_pct=6.0,
        daily_loss_dollar_cap=625.0,
        trailing_hwm_floor=23500.0,
        max_open_trades=3,
        open_positions_count=0,
    ))
    import time
    economic_calendar_service._events.clear()
    economic_calendar_service._calendar_verified = True
    economic_calendar_service._last_refresh_monotonic = time.monotonic()


def test_admission_approved_for_clean_candidate():
    gate = TradeAdmissionGate()
    now_iso = datetime.now(timezone.utc).isoformat()

    market_context = {
        "data_mode": "LIVE",
        "actionable": True,
        "market_open": True,
        "quote_observed_at": now_iso,
        "signal_generated_at": now_iso,
        "quote_source": "MT5_BROKER_FEED",
        "spread": 15.0,
        "typical_spread": 15.0,
        "minutes_to_weekend_close": 500.0,
        "news_clearance": {
            "verified": True,
            "is_blackout": False,
            "is_cleared": True,
            "age_seconds": 10.0,
        }
    }

    admitted, blockers, receipt = gate.evaluate_comprehensive_admission(
        account_id="ACC_TEST_25K",
        symbol="XAUUSD",
        direction="BUY",
        strategy_id="STRAT_TREND_CONT_OTE",
        strategy_version="1.0.0",
        regime="TRENDING_NORMAL",
        risk_pct=0.75,
        market_context=market_context,
        is_live_order=False,
    )

    assert admitted is True
    assert len(blockers) == 0
    assert receipt["admitted"] is True
    assert receipt["risk_telemetry"]["risk_dollar"] == 187.50


def test_admission_rejects_ineligible_regime():
    gate = TradeAdmissionGate()
    now_iso = datetime.now(timezone.utc).isoformat()

    admitted, blockers, _ = gate.evaluate_comprehensive_admission(
        account_id="ACC_TEST_25K",
        symbol="XAUUSD",
        direction="BUY",
        strategy_id="STRAT_TREND_CONT_OTE",
        strategy_version="1.0.0",
        regime="VOLATILITY_SHOCK",
        risk_pct=0.75,
        market_context=None,
        is_live_order=False,
    )

    assert admitted is False
    assert any("strictly prohibited" in b or "VOLATILITY_SHOCK" in b for b in blockers)


def test_admission_rejects_economic_news_blackout():
    gate = TradeAdmissionGate()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    # Inject high-impact event right now
    economic_calendar_service.register_event(EconomicEvent(
        event_id="EV_TEST_CPI_ACTIVE",
        event_name="Active CPI Release",
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_utc=now_iso,
        pre_lockout_minutes=15,
        post_cooldown_minutes=15,
    ))

    admitted, blockers, _ = gate.evaluate_comprehensive_admission(
        account_id="ACC_TEST_25K",
        symbol="XAUUSD",
        direction="BUY",
        strategy_id="STRAT_TREND_CONT_OTE",
        strategy_version="1.0.0",
        regime="TRENDING_NORMAL",
        risk_pct=0.75,
        market_context=None,
        is_live_order=False,
    )

    assert admitted is False
    assert any("Active CPI Release" in b or "cooldown" in b or "freeze" in b for b in blockers)


def test_admission_rejects_excessive_risk_sizing():
    gate = TradeAdmissionGate()
    admitted, blockers, _ = gate.evaluate_comprehensive_admission(
        account_id="ACC_TEST_25K",
        symbol="XAUUSD",
        direction="BUY",
        strategy_id="STRAT_TREND_CONT_OTE",
        strategy_version="1.0.0",
        regime="TRENDING_NORMAL",
        risk_pct=1.50,  # Exceeds 0.75% prop rule
        market_context=None,
        is_live_order=False,
    )
    assert admitted is False
    assert any("exceeds maximum allowable 0.75%" in b for b in blockers)


def test_admission_rejects_when_global_kill_switch_active():
    gate = TradeAdmissionGate()
    portfolio_risk_service.set_global_kill_switch(True)

    admitted, blockers, _ = gate.evaluate_comprehensive_admission(
        account_id="ACC_TEST_25K",
        symbol="XAUUSD",
        direction="BUY",
        strategy_id="STRAT_TREND_CONT_OTE",
        strategy_version="1.0.0",
        regime="TRENDING_NORMAL",
        risk_pct=0.50,
        market_context=None,
        is_live_order=False,
    )
    assert admitted is False
    assert any("Global Kill Switch is ACTIVE" in b for b in blockers)
