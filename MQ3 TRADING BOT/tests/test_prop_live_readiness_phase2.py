from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from src.audit_ledger import AuditLedger
from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.bitget_connector import BitgetConnector
from src.live_readiness import BOOLEAN_GATES, LiveReadinessManager
from src.mt5_connector import MT5Connector
from src.mt5_terminal_worker import MT5TerminalWorkerProxy
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.multi_terminal_copier import MultiTerminalCopier
from src.prop_rules import build_account_policy, normalize_model
from src.signal_quality_gate import SignalQualityGate
from src.trade_admission import TradeAdmissionGate


def test_funding_pips_standard_uses_static_hard_floor_and_tighter_internal_stops():
    policy = build_account_policy(
        account_size=25_000,
        model="FUNDING_PIPS_2_STEP_STANDARD",
        stage="EVALUATION_PHASE_1",
        require_explicit_model=True,
    )
    assert policy["profit_target_pct"] == 8.0
    assert policy["minimum_trading_days"] == 3
    assert policy["hard_daily_loss_pct"] == 5.0
    assert policy["hard_overall_loss_pct"] == 10.0
    assert policy["loss_floor_type"] == "STATIC_STARTING_BALANCE"
    assert policy["hard_overall_loss_dollars"] == 2_500.0
    assert policy["internal_risk_per_trade_pct"] == 0.25
    assert policy["internal_daily_stop_pct"] == 1.5
    assert policy["internal_overall_stop_pct"] == 4.0
    assert policy["hard_risk_per_trade_idea_pct"] is None
    assert policy["legacy_risk_per_trade_idea_rule_applies"] is False
    assert policy["striking_system_applies"] is False


def test_current_standard_master_striking_rule_depends_on_size_and_reward_cycle():
    standard = build_account_policy(
        account_size=50_000,
        model="FUNDING_PIPS_2_STEP_STANDARD",
        stage="MASTER",
        reward_cycle="BI_WEEKLY",
    )
    assert standard["hard_risk_per_trade_idea_pct"] is None
    assert standard["striking_system_applies"] is True
    assert standard["striking_warning_trigger_pct"] == 1.2
    assert standard["striking_warning_count_to_breach"] == 4

    small_weekly = build_account_policy(
        account_size=25_000,
        model="FUNDING_PIPS_2_STEP_STANDARD",
        stage="MASTER",
        reward_cycle="WEEKLY",
    )
    assert small_weekly["striking_system_applies"] is False

    small_monthly = build_account_policy(
        account_size=5_000,
        model="FUNDING_PIPS_2_STEP_STANDARD",
        stage="MASTER",
        reward_cycle="MONTHLY",
    )
    assert small_monthly["striking_system_applies"] is True
    assert small_monthly["striking_warning_trigger_pct"] == 1.0


def test_zero_max_open_risk_is_not_mislabeled_as_legacy_trade_idea_limit():
    policy = build_account_policy(account_size=25_000, model="FUNDING_PIPS_ZERO")
    assert policy["firm_max_open_risk_pct"] == 1.0
    assert policy["hard_risk_per_trade_idea_pct"] is None


def test_all_published_models_have_distinct_current_hard_limits():
    expected = {
        "FUNDING_PIPS_1_STEP_FLEX": (3.0, 12.0),
        "FUNDING_PIPS_2_STEP_STANDARD": (5.0, 10.0),
        "FUNDING_PIPS_2_STEP_PRO": (3.0, 6.0),
        "FUNDING_PIPS_2_STEP_FLEX": (4.0, 12.0),
        "FUNDING_PIPS_ZERO": (3.0, 5.0),
    }
    for model, limits in expected.items():
        policy = build_account_policy(account_size=5_000, model=model)
        assert (policy["hard_daily_loss_pct"], policy["hard_overall_loss_pct"]) == limits


def test_live_model_selection_rejects_generic_or_missing_name():
    with pytest.raises(ValueError):
        normalize_model(None, require_explicit=True)
    with pytest.raises(ValueError):
        normalize_model("Funding Pips", require_explicit=True)


def test_default_readiness_is_paper_and_blocks_live(tmp_path):
    path = tmp_path / "readiness.json"
    path.write_text(json.dumps({"schema_version": 1, "global": {"stage": "PAPER"}, "accounts": {}}), encoding="utf-8")
    manager = LiveReadinessManager(str(path))
    allowed, blockers = manager.live_execution_allowed("A1", autonomous=True)
    assert allowed is False
    assert blockers
    assert manager.evaluate("A1")["achieved_stage"] == "PAPER"


def test_readiness_requires_all_evidence_and_time_bounded_arm(tmp_path):
    path = tmp_path / "readiness.json"
    future = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "schema_version": 1,
        "global": {
            "stage": "LIVE",
            "live_arm_expires_at": future.isoformat(),
            "allow_autonomous_live": True,
            "gates": {gate: True for gate in BOOLEAN_GATES},
            "evidence": {
                "shadow_trading_days": 20,
                "shadow_trades": 100,
                "demo_trading_days": 10,
                "demo_trades": 50,
                "out_of_sample_profit_factor": 1.20,
                "forward_max_drawdown_pct": 2.0,
                "execution_error_rate_pct": 1.0,
                "canary_trades": 30,
            },
        },
        "accounts": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    manager = LiveReadinessManager(str(path))
    status = manager.evaluate("A1")
    assert status["ready_for_full_live"] is True
    assert manager.live_execution_allowed("A1", autonomous=True) == (True, [])

    payload["global"]["live_arm_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")
    allowed, blockers = manager.live_execution_allowed("A1", autonomous=True)
    assert allowed is False
    assert any("expired" in item or "armed" in item for item in blockers)


def _fresh_market_context():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "data_mode": "LIVE",
        "actionable": True,
        "market_open": True,
        "quote_observed_at": now,
        "signal_generated_at": now,
        "quote_source": "BROKER_MT5",
        "spread": 1.0,
        "typical_spread": 1.0,
        "minutes_to_weekend_close": 600,
        "news_clearance": {"verified": True, "is_blackout": False, "is_cleared": True, "age_seconds": 1},
    }


def _quality_context():
    context = _fresh_market_context()
    context["signal_quality"] = {
        "validation_id": "WF-2026-08",
        "strategy_id": "MQ3-BASELINE",
        "strategy_version": "2.0.0",
        "validation_dataset_hash": "sha256:abc",
        "out_of_sample_trades": 120,
        "out_of_sample_profit_factor": 1.25,
        "validation_max_drawdown_pct": 3.0,
        "estimated_reward_risk_after_costs": 1.6,
        "cost_adjusted_expectancy_r": 0.05,
        "calibration_brier_score": 0.20,
        "independent_evidence": ["broker_structure", "calendar", "cross_asset"],
        "regime_supported": True,
        "duplicate_signal": False,
        "lookahead_bias_check_passed": True,
        "cost_model_verified": True,
    }
    return context


def test_trade_admission_rejects_missing_and_stale_context():
    gate = TradeAdmissionGate()
    assert gate.evaluate(None, live=True)[0] is False
    stale = _fresh_market_context()
    stale["quote_observed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    allowed, reasons = gate.evaluate(stale, live=True)
    assert allowed is False
    assert "Broker quote is stale" in reasons
    assert gate.evaluate(_fresh_market_context(), live=True)[0] is True


def test_signal_quality_gate_requires_versioned_cost_adjusted_evidence():
    gate = SignalQualityGate()
    assert gate.evaluate(_fresh_market_context(), live=True)[0] is False
    assert gate.evaluate(_quality_context(), live=True)[0] is True
    bad = _quality_context()
    bad["signal_quality"]["cost_adjusted_expectancy_r"] = -0.1
    assert gate.evaluate(bad, live=True)[0] is False


def test_mt5_worker_requires_account_specific_live_binding_and_fails_closed_when_unstarted():
    with pytest.raises(ValueError):
        MT5TerminalWorkerProxy(account_id="123", connector_config={"account_validation": {}}, simulation_mode=False)
    proxy = MT5TerminalWorkerProxy(account_id="123", connector_config={}, simulation_mode=True)
    assert proxy.connected is False
    assert proxy.place_order(symbol="XAUUSD")["success"] is False


class _PaperConnector:
    simulation_mode = True

    def __init__(self, login):
        self.login = str(login)
        self.orders = []

    def get_account_info(self):
        return {"available": True, "login": self.login, "data_mode": "PAPER"}

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"success": True, "ticket": f"PAPER-{self.login}-{len(self.orders)}", "mode": "PAPER"}


def test_multi_terminal_copier_reports_only_bound_connector_receipts():
    fleet = {
        "mode": "PAPER",
        "accounts": {
            "a": {"account_id": "A", "account_name": "A", "balance": 5_000, "risk_pct": 0.0025, "is_active": True},
            "b": {"account_id": "B", "account_name": "B", "balance": 25_000, "risk_pct": 0.0025, "is_active": True},
        },
    }
    connector = _PaperConnector("A")
    copier = MultiTerminalCopier(fleet, connectors={"A": connector}, simulation_mode=True)
    result = copier.replicate_order({"symbol": "XAUUSD", "direction": "BUY", "entry_price": 2600, "sl": 2590, "tp": 2620, "sl_pips": 100})
    assert result["executed_accounts"] == 1
    assert result["slave_executions"]["a"]["ticket"].startswith("PAPER-A-")
    assert result["slave_executions"]["b"]["status"] == "REJECTED_NO_CONNECTOR"


def test_funding_pips_crypto_cfd_routes_to_registered_mt5_not_exchange(tmp_path):
    fleet_path = tmp_path / "fleet.json"
    onboarder = MultiAccountAutoOnboarder(config_path=str(fleet_path))
    onboarder.onboard_new_account(
        account_id="FP1", server="DEMO", balance=25_000, account_type="FUNDING_PIPS",
        prop_model="FUNDING_PIPS_2_STEP_STANDARD", account_stage="EVALUATION_PHASE_1",
    )
    from src.fleet_risk_manager import FleetRiskManager

    risk = FleetRiskManager(config_path=str(fleet_path), auto_onboarder=onboarder)
    mt5 = MT5Connector(simulation_mode=True)
    mt5.connect()
    bitget = BitgetConnector(sim_mode=True)
    executor = AutonomousFleetExecutor(
        config_path=str(fleet_path), risk_manager=risk, mt5_connector=mt5,
        bitget_connector=bitget, simulation_mode=True, seed_demo_positions=False,
    )
    receipt = executor.route_order("FP1", {"symbol": "BTCUSD", "direction": "BUY", "lots": 0.001, "entry_price": 60_000, "sl": 59_000, "tp": 62_000})
    assert receipt["success"] is True
    assert receipt["venue"] == "MT5"
    assert bitget.sim_positions == []


def test_audit_ledger_redacts_secrets_and_detects_tampering(tmp_path):
    path = tmp_path / "audit.jsonl"
    ledger = AuditLedger(str(path))
    record = ledger.append("TEST", {"account": "A", "api_key": "secret-value"})
    assert record["payload"]["api_key"] == "[REDACTED]"
    assert ledger.verify()[0] is True

    content = path.read_text(encoding="utf-8").replace('"account": "A"', '"account": "B"')
    path.write_text(content, encoding="utf-8")
    assert ledger.verify()[0] is False
