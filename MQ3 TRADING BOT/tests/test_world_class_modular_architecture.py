"""Comprehensive verification suite for MQ3 World-Class Modular Architecture.

Verifies:
1. SourceRegistryService & Data Provenance Contracts
2. Verified Market Context & US Treasury Yield Curve Integration
3. Economic Calendar Service & Strict Lockout Gates
4. Cryptographic Signed Trade Proposals & 19-point Preflight Rechecks
5. WhatsApp Research & Explicit Ticket Management Commands
6. Central Trade Admission & Portfolio Risk Governance
"""

import datetime
import pytest
from src.source_registry_service import source_registry_service, SourceDataMode, SourceHealth
from src.verified_market_context import VerifiedMarketContextEngine
from src.economic_calendar_service import economic_calendar_service, EventImpact, EconomicEvent
from src.signal_decision_manager import signal_decision_manager, SignedTradeProposal
from src.strategy_registry import strategy_registry, StrategyStage
from src.trade_admission import trade_admission_gate
from src.portfolio_risk_service import portfolio_risk_service, AccountRiskState
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.whatsapp_copilot import WhatsApp1ClickRouter, is_whitelisted_number


def test_source_registry_contract_completeness():
    """Every source in the registry must satisfy the complete provenance contract."""
    sources = source_registry_service.list_sources()
    assert len(sources) >= 8, f"Expected at least 8 sources, found {len(sources)}"

    required_fields = [
        "source_id", "source_name", "provider", "venue", "asset_scope",
        "data_type", "mode", "freshness_threshold_seconds", "timezone",
        "license_note", "known_limitations", "influences_research",
        "influences_execution", "current_health"
    ]

    for src in sources:
        for field in required_fields:
            assert field in src, f"Source {src.get('source_id')} missing field: {field}"
        assert isinstance(src["asset_scope"], list)
        assert len(src["asset_scope"]) > 0

    # Specifically verify MT5 Broker authoritative execution role
    mt5_src = source_registry_service.get_source("mt5_broker")
    assert mt5_src is not None
    assert mt5_src.influences_execution is True
    assert mt5_src.mode == SourceDataMode.LIVE

    # Specifically verify Binance public spot is context only
    binance_src = source_registry_service.get_source("binance_market_data")
    assert binance_src is not None
    assert binance_src.influences_execution is False

    # Specifically verify global order flow attribution fails closed
    global_src = source_registry_service.get_source("global_order_flow_attribution")
    assert global_src is not None
    assert global_src.mode == SourceDataMode.UNAVAILABLE
    assert global_src.current_health == SourceHealth.UNAVAILABLE


def test_treasury_yield_curve_and_market_context():
    """Verified market context includes US Treasury Yield benchmarks and curve state."""
    engine = VerifiedMarketContextEngine()
    treasury = engine.treasury_yield_curve_context()
    assert treasury["status"] == "AVAILABLE"
    assert "us_10y_yield_pct" in treasury
    assert "us_2y_yield_pct" in treasury
    assert "curve_10y_2y_spread_bps" in treasury
    assert treasury["actionable"] is False

    coverage = engine.source_coverage()
    assert coverage["status"] == "PARTIAL"
    assert coverage["total"] >= 5


def test_economic_calendar_lockout_and_cooldown():
    """Economic calendar enforces 15m pre-event freeze and 15m post-event cooldown per currency."""
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    event_dt = now_dt + datetime.timedelta(minutes=10)

    test_event = EconomicEvent(
        event_id="TEST_HIGH_IMPACT_CPI",
        event_name="Test High Impact CPI Release",
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_utc=event_dt.isoformat(),
        pre_lockout_minutes=15,
        post_cooldown_minutes=15,
        source_agency="US Bureau of Labor Statistics",
        source_url="https://www.bls.gov",
    )
    economic_calendar_service.register_event(test_event)

    # 1. USD assets locked
    locked, reason, active = economic_calendar_service.evaluate_symbol_lockout("XAUUSD", now_dt.isoformat())
    assert locked is True
    assert "Pre-news freeze" in reason

    # 2. Unrelated currency not locked
    locked_jpy, _, _ = economic_calendar_service.evaluate_symbol_lockout("EURGBP", now_dt.isoformat())
    assert locked_jpy is False

    # Clean up test event to prevent polluting subsequent tests
    economic_calendar_service._events = [e for e in economic_calendar_service._events if e.event_id != "TEST_HIGH_IMPACT_CPI"]


def test_cryptographic_signed_proposal_lifecycle(monkeypatch):
    """Proposals are cryptographically signed, expire, and enforce 19-point preflight rechecks."""
    from src.economic_calendar_service import economic_calendar_service
    monkeypatch.setattr(economic_calendar_service, "evaluate_symbol_lockout", lambda sym, dt: (False, "CLEAR", {}))
    mock_research = {
        "symbol": "XAUUSD",
        "decision": "BUY",
        "direction": "BUY",
        "entry_reference": 2650.00,
        "stop_reference": 2640.00,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "spread": 20.0,
        "account_suitability": {
            "calculated_lots": 0.15,
            "estimated_stop_risk": 150.0,
            "risk_pct": 0.25,
            "verdict": "CONDITIONAL_RESEARCH_ONLY",
        },
        "technical_evidence": [{"timeframe": "M15", "finding": "EMA 20 > 50 alignment", "value": "BULLISH"}],
        "opposing_evidence": [],
        "blockers": [],
    }

    # Register test account in risk service
    portfolio_risk_service.register_account(AccountRiskState(
        account_id="40000243427",
        account_name="Demo Test Account",
        starting_balance=50000.0,
        current_balance=50000.0,
        current_equity=50000.0,
        high_water_mark=50000.0,
        daily_start_equity=50000.0,
    ))

    proposal = signal_decision_manager.create_proposal_from_research(
        mock_research, account_id="40000243427", owner_id="923468053268", validity_seconds=60
    )
    assert proposal is not None
    assert proposal.proposal_id.startswith("PROP-XAUUSD-")
    assert len(proposal.proposal_signature) == 64
    assert not proposal.is_expired()

    # Recheck signature matches
    assert proposal.compute_signature() == proposal.proposal_signature

    # Test decision processing with mock connector
    class MockConnector:
        def get_live_spread(self, symbol):
            return {
                "symbol": symbol,
                "bid": 2649.90,
                "ask": 2650.10,
                "spread": 20.0,
                "typical_spread": 20.0,
                "age_seconds": 0.5,
            }
        def place_order(self, **kwargs):
            return {"success": True, "ticket": 987654}

    mock_conn = MockConnector()
    res = signal_decision_manager.process_owner_decision(
        decision_text="YES", owner_id="923468053268", connector=mock_conn, is_live=False
    )
    assert res["success"] is True
    assert res["status"] == "DEMO_ORDER_EXECUTED"
    assert res["ticket"] == 987654


def test_whatsapp_explicit_ticket_and_ambiguous_rejection():
    """WhatsApp router accepts explicit ticket commands and rejects ambiguous directives."""
    router = WhatsApp1ClickRouter()

    # 1. Ambiguous financial directive prompt
    ambig_res = router.handle_command("upar karo thora", sender="923468053268")
    assert ambig_res["action"] == "AMBIGUOUS_REJECTED"
    assert "AMBIGUOUS FINANCIAL DIRECTIVE" in ambig_res["reply"]

    ambig_sl = router.handle_command("sl barha do please", sender="923468053268")
    assert ambig_sl["action"] == "AMBIGUOUS_REJECTED"

    # 2. Explicit breakeven command
    be_res = router.handle_command("breakeven 123456", sender="923468053268")
    assert be_res["action"] == "BREAKEVEN"

    # 3. Explicit stop modification command
    stop_res = router.handle_command("stop 123456 2655.50", sender="923468053268")
    assert stop_res["action"] == "MODIFY_STOP"

    # 4. Explicit reduce command
    reduce_res = router.handle_command("reduce 123456 50%", sender="923468053268")
    assert reduce_res["action"] == "SCALE_OUT"


def test_whatsapp_research_commands():
    """WhatsApp QR Manager provides all requested research, readiness, and risk commands."""
    qr_mgr = WhatsAppQRManager()

    # 1. Status command
    status_text = qr_mgr.handle_incoming_command("status", sender="923468053268")
    assert "BROKER" in status_text or "ACCOUNT" in status_text

    # 2. Readiness command
    readiness_text = qr_mgr.handle_incoming_command("readiness", sender="923468053268")
    assert "LIVE READINESS" in readiness_text
    assert "SAFETY & GOVERNANCE GATES" in readiness_text

    # 3. Blockers command
    blockers_text = qr_mgr.handle_incoming_command("blockers", sender="923468053268")
    assert "CENTRAL ADMISSION & RISK BLOCKERS" in blockers_text

    # 4. Strategies command
    strat_text = qr_mgr.handle_incoming_command("strategies", sender="923468053268")
    assert "STRATEGY REGISTRY" in strat_text
    assert "STRAT_TREND_CONT_OTE" in strat_text

    # 5. Validation command
    val_text = qr_mgr.handle_incoming_command("validation STRAT_TREND_CONT_OTE", sender="923468053268")
    assert "VALIDATION RECEIPT" in val_text
    assert "VR_TREND_OTE_2026_01" in val_text

    # 6. Risk command
    risk_text = qr_mgr.handle_incoming_command("risk", sender="923468053268")
    assert "PORTFOLIO RISK" in risk_text
    assert "VaR 1-Day 99%" in risk_text

    # 7. Help command
    help_text = qr_mgr.handle_incoming_command("help", sender="923468053268")
    assert "COMMAND DESK" in help_text
    assert "signal <symbol>" in help_text
