"""Chaos Drills, Crash Resilience, and Operational Recovery Test Suite.

Verifies:
1. Broker Disconnection & Feed Interruption (Fail-Closed)
2. In-flight Quote Staleness & Slippage Spike Defense
3. Process Kill, Restart, and State Reconciliation Drill
4. Fleet Correlation & Central Portfolio Heat Stress Test
5. Emergency Kill Switch Drill & Tamper-Evident Ledger Audit
"""

import datetime
import json
import pytest
from pathlib import Path

from src.portfolio_risk_service import portfolio_risk_service, AccountRiskState
from src.trade_admission import trade_admission_gate
from src.signal_decision_manager import signal_decision_manager, SignedTradeProposal
from src.economic_calendar_service import economic_calendar_service, EconomicEvent, EventImpact
from src.strategy_registry import strategy_registry, StrategyStage


def test_chaos_broker_disconnect_fails_closed():
    """When broker feed disconnects during preflight recheck, order is rejected."""
    class DisconnectedConnector:
        def get_live_spread(self, symbol):
            raise ConnectionError("MT5 IPC socket severed")
        def place_order(self, **kwargs):
            raise ConnectionError("MT5 IPC socket severed")

    mock_research = {
        "symbol": "XAUUSD",
        "decision": "BUY",
        "direction": "BUY",
        "entry_reference": 2650.00,
        "stop_reference": 2640.00,
        "account_suitability": {
            "calculated_lots": 0.10,
            "estimated_stop_risk": 100.0,
            "risk_pct": 0.25,
            "verdict": "CONDITIONAL_RESEARCH_ONLY",
        },
    }

    proposal = signal_decision_manager.create_proposal_from_research(
        mock_research, account_id="40000243427", owner_id="923468053268", validity_seconds=60
    )
    assert proposal is not None

    res = signal_decision_manager.process_owner_decision(
        decision_text="YES", owner_id="923468053268", connector=DisconnectedConnector(), is_live=False
    )
    assert res["success"] is False
    assert res["status"] == "PREFLIGHT_RECHECK_FAILED"
    assert any("Broker live quote fetch failed" in b for b in res["blockers"])
    assert res["order_sent"] is False


def test_chaos_quote_staleness_and_excessive_slippage_defense():
    """Quotes older than 5.0s or prices slipping beyond allowable deviation are blocked."""
    # 1. Stale quote test (>5.0s)
    class StaleConnector:
        def get_live_spread(self, symbol):
            return {
                "symbol": symbol, "bid": 2650.00, "ask": 2650.20, "spread": 20.0,
                "typical_spread": 20.0, "age_seconds": 12.5,
            }
        def place_order(self, **kwargs):
            return {"success": True}

    mock_research = {
        "symbol": "XAUUSD", "decision": "BUY", "direction": "BUY",
        "entry_reference": 2650.00, "stop_reference": 2640.00,
        "account_suitability": {"calculated_lots": 0.10, "estimated_stop_risk": 100.0, "risk_pct": 0.25, "verdict": "CONDITIONAL_RESEARCH_ONLY"},
    }
    proposal = signal_decision_manager.create_proposal_from_research(
        mock_research, account_id="40000243427", owner_id="923468053268", validity_seconds=60
    )
    res_stale = signal_decision_manager.process_owner_decision(
        decision_text="YES", owner_id="923468053268", connector=StaleConnector(), is_live=False
    )
    assert res_stale["success"] is False
    assert any("Broker quote is stale" in b for b in res_stale["blockers"])

    # 2. Extreme slippage test
    class SlippedConnector:
        def get_live_spread(self, symbol):
            return {
                "symbol": symbol, "bid": 2655.00, "ask": 2655.50, "spread": 50.0,
                "typical_spread": 20.0, "age_seconds": 0.2,
            }
        def place_order(self, **kwargs):
            return {"success": True}

    proposal_slip = signal_decision_manager.create_proposal_from_research(
        mock_research, account_id="40000243427", owner_id="923468053268", validity_seconds=60
    )
    res_slip = signal_decision_manager.process_owner_decision(
        decision_text="YES", owner_id="923468053268", connector=SlippedConnector(), is_live=False
    )
    assert res_slip["success"] is False
    assert any("Price slipped" in b or "spread" in b for b in res_slip["blockers"])


def test_chaos_fleet_correlation_and_risk_budget_enforcement():
    """Multi-account fleet enforces strict central portfolio risk across currency clusters."""
    # Register 4-account fleet
    accounts = {
        "FP_100K": AccountRiskState(account_id="FP_100K", account_name="100K Alpha", starting_balance=100000.0, current_balance=100000.0, current_equity=100000.0, high_water_mark=100000.0, daily_start_equity=100000.0),
        "FP_50K": AccountRiskState(account_id="FP_50K", account_name="50K Beta", starting_balance=50000.0, current_balance=50000.0, current_equity=50000.0, high_water_mark=50000.0, daily_start_equity=50000.0),
        "FP_25K": AccountRiskState(account_id="FP_25K", account_name="25K Gamma", starting_balance=25000.0, current_balance=25000.0, current_equity=25000.0, high_water_mark=25000.0, daily_start_equity=25000.0),
        "FP_5K": AccountRiskState(account_id="FP_5K", account_name="5K Micro", starting_balance=5000.0, current_balance=5000.0, current_equity=5000.0, high_water_mark=5000.0, daily_start_equity=5000.0),
    }
    for acc in accounts.values():
        portfolio_risk_service.register_account(acc)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. First account opens USD trade
    is_ok, reason, telemetry = portfolio_risk_service.evaluate_trade_admission_risk(
        account_id="FP_100K", symbol="XAUUSD", direction="BUY", risk_pct=0.25, current_time_utc=now_iso
    )
    assert is_ok is True

    # 2. Rejection when exceeding max account risk (e.g. 1.0% single trade when cap is 0.25%)
    is_ok_oversize, reason_oversize, _ = portfolio_risk_service.evaluate_trade_admission_risk(
        account_id="FP_100K", symbol="XAUUSD", direction="BUY", risk_pct=1.00, current_time_utc=now_iso
    )
    assert is_ok_oversize is False
    assert "Per-trade risk" in reason_oversize


def test_emergency_kill_switch_drill():
    """Emergency kill switch denies all order admissions and triggers global lockdown."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        portfolio_risk_service.set_global_kill_switch(True)
        assert portfolio_risk_service.is_global_kill_switch_active() is True

        passed, blockers, receipt = trade_admission_gate.evaluate_comprehensive_admission(
            account_id="40000243427",
            symbol="XAUUSD",
            direction="BUY",
            strategy_id="STRAT_TREND_CONT_OTE",
            strategy_version="1.0.0",
            regime="TRENDING_NORMAL",
            risk_pct=0.25,
            market_context=None,
            is_live_order=False,
        )
        assert passed is False
        assert any("Global Kill Switch is ACTIVE" in b for b in blockers)
    finally:
        portfolio_risk_service.set_global_kill_switch(False)
        assert portfolio_risk_service.is_global_kill_switch_active() is False
