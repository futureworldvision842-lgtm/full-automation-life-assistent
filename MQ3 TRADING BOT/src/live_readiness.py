"""Staged live-readiness evaluation for trading accounts.

Passing unit tests is not equivalent to being ready for a funded account.  This
module turns operational evidence into a fail-closed promotion decision:
PAPER -> SHADOW -> DEMO -> CANARY -> LIVE.  Live order routing reads this file
but never promotes an account automatically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import IntEnum
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple


class ReadinessStage(IntEnum):
    PAPER = 0
    SHADOW = 1
    DEMO = 2
    CANARY = 3
    LIVE = 4


BOOLEAN_GATES = (
    "credentials_rotated",
    "personal_ea_ownership_documented",
    "firm_automation_approval_confirmed",
    "exact_prop_model_selected",
    "exact_reward_cycle_selected_if_master",
    "broker_demo_login_verified",
    "per_account_terminal_binding_verified",
    "broker_symbol_specs_verified",
    "market_data_freshness_verified",
    "news_calendar_verified",
    "whatsapp_delivery_verified",
    "kill_switch_drill_passed",
    "restart_recovery_drill_passed",
    "stale_data_rejection_test_passed",
    "disconnect_rejection_test_passed",
    "operator_accepts_no_profit_guarantee",
)


DEFAULT_THRESHOLDS = {
    "minimum_shadow_trading_days": 20,
    "minimum_shadow_trades": 100,
    "minimum_demo_trading_days": 10,
    "minimum_demo_trades": 50,
    "minimum_out_of_sample_profit_factor": 1.20,
    "maximum_forward_drawdown_pct": 2.0,
    "maximum_execution_error_rate_pct": 1.0,
    "minimum_canary_trades_before_full_live": 30,
}


def _parse_utc(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class LiveReadinessManager:
    DEFAULT_PATH = "data/live_readiness.json"

    def __init__(self, config_path: str = DEFAULT_PATH):
        self.config_path = config_path

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {"schema_version": 1, "global": {}, "accounts": {}}
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {"schema_version": 1, "global": {}, "accounts": {}}
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "global": {}, "accounts": {}, "configuration_error": True}

    @staticmethod
    def _stage(value: Any) -> ReadinessStage:
        raw = str(value or "PAPER").strip().upper()
        try:
            return ReadinessStage[raw]
        except KeyError:
            return ReadinessStage.PAPER

    def _merged_account(self, account_id: Any) -> Dict[str, Any]:
        data = self._load()
        merged: Dict[str, Any] = {}
        merged.update(data.get("global", {}) if isinstance(data.get("global"), dict) else {})
        accounts = data.get("accounts", {}) if isinstance(data.get("accounts"), dict) else {}
        wildcard = accounts.get("*", {})
        if isinstance(wildcard, dict):
            merged.update(wildcard)
        account = accounts.get(str(account_id), {})
        if isinstance(account, dict):
            merged.update(account)
        merged["account_id"] = str(account_id)
        merged["schema_version"] = data.get("schema_version", 1)
        merged["configuration_error"] = bool(data.get("configuration_error", False))
        return merged

    def evaluate(self, account_id: Any) -> Dict[str, Any]:
        cfg = self._merged_account(account_id)
        requested_stage = self._stage(cfg.get("stage"))
        gates = cfg.get("gates", {}) if isinstance(cfg.get("gates"), dict) else {}
        evidence = cfg.get("evidence", {}) if isinstance(cfg.get("evidence"), dict) else {}
        thresholds = dict(DEFAULT_THRESHOLDS)
        if isinstance(cfg.get("thresholds"), dict):
            thresholds.update(cfg["thresholds"])

        blockers: List[str] = []
        warnings: List[str] = []
        if cfg.get("configuration_error"):
            blockers.append("Readiness configuration is missing or invalid")

        completed_boolean_gates = [gate for gate in BOOLEAN_GATES if gates.get(gate) is True]
        missing_boolean_gates = [gate for gate in BOOLEAN_GATES if gates.get(gate) is not True]

        shadow_days = int(evidence.get("shadow_trading_days", 0) or 0)
        shadow_trades = int(evidence.get("shadow_trades", 0) or 0)
        demo_days = int(evidence.get("demo_trading_days", 0) or 0)
        demo_trades = int(evidence.get("demo_trades", 0) or 0)
        profit_factor = float(0.0 if evidence.get("out_of_sample_profit_factor") is None else evidence.get("out_of_sample_profit_factor"))
        max_drawdown = float(100.0 if evidence.get("forward_max_drawdown_pct") is None else evidence.get("forward_max_drawdown_pct"))
        execution_error_rate = float(100.0 if evidence.get("execution_error_rate_pct") is None else evidence.get("execution_error_rate_pct"))
        canary_trades = int(evidence.get("canary_trades", 0) or 0)

        achieved_stage = ReadinessStage.PAPER
        if gates.get("credentials_rotated") and gates.get("personal_ea_ownership_documented"):
            achieved_stage = ReadinessStage.SHADOW

        shadow_passed = (
            shadow_days >= int(thresholds["minimum_shadow_trading_days"])
            and shadow_trades >= int(thresholds["minimum_shadow_trades"])
            and profit_factor >= float(thresholds["minimum_out_of_sample_profit_factor"])
            and max_drawdown <= float(thresholds["maximum_forward_drawdown_pct"])
        )
        if achieved_stage >= ReadinessStage.SHADOW and shadow_passed:
            achieved_stage = ReadinessStage.DEMO

        demo_passed = (
            demo_days >= int(thresholds["minimum_demo_trading_days"])
            and demo_trades >= int(thresholds["minimum_demo_trades"])
            and execution_error_rate <= float(thresholds["maximum_execution_error_rate_pct"])
        )
        all_operational_gates = not missing_boolean_gates
        if achieved_stage >= ReadinessStage.DEMO and demo_passed and all_operational_gates:
            achieved_stage = ReadinessStage.CANARY
        if achieved_stage >= ReadinessStage.CANARY and canary_trades >= int(thresholds["minimum_canary_trades_before_full_live"]):
            achieved_stage = ReadinessStage.LIVE

        if requested_stage > achieved_stage:
            blockers.append(f"Requested {requested_stage.name}, but evidence only supports {achieved_stage.name}")
        if requested_stage >= ReadinessStage.CANARY:
            blockers.extend(f"Gate not confirmed: {gate}" for gate in missing_boolean_gates)
            if not shadow_passed:
                blockers.append("Shadow forward-test thresholds have not passed")
            if not demo_passed:
                blockers.append("Demo execution thresholds have not passed")

        arm_until = _parse_utc(cfg.get("live_arm_expires_at"))
        armed = bool(arm_until and arm_until > datetime.now(timezone.utc))
        if requested_stage >= ReadinessStage.CANARY and not armed:
            blockers.append("Live arm is absent or expired")

        if cfg.get("allow_autonomous_live") is True and requested_stage < ReadinessStage.LIVE:
            warnings.append("Autonomous-live flag is ignored before the LIVE evidence stage")

        return {
            "account_id": str(account_id),
            "requested_stage": requested_stage.name,
            "achieved_stage": achieved_stage.name,
            "stage_authorized": requested_stage <= achieved_stage,
            "live_armed": armed,
            "live_arm_expires_at": arm_until.isoformat() if arm_until else None,
            "allow_autonomous_live": bool(cfg.get("allow_autonomous_live", False) and achieved_stage >= ReadinessStage.LIVE),
            "completed_gates": completed_boolean_gates,
            "missing_gates": missing_boolean_gates,
            "evidence": evidence,
            "thresholds": thresholds,
            "blockers": list(dict.fromkeys(blockers)),
            "warnings": warnings,
            "ready_for_canary": achieved_stage >= ReadinessStage.CANARY and armed and not blockers,
            "ready_for_full_live": achieved_stage >= ReadinessStage.LIVE and armed and not blockers,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def live_execution_allowed(self, account_id: Any, *, autonomous: bool = True) -> Tuple[bool, List[str]]:
        status = self.evaluate(account_id)
        blockers = list(status["blockers"])
        if not status["live_armed"]:
            blockers.append("Account is not time-bounded live-armed")
        if status["achieved_stage"] not in {"CANARY", "LIVE"}:
            blockers.append(f"Evidence stage {status['achieved_stage']} is below CANARY")
        if autonomous and not status["allow_autonomous_live"]:
            blockers.append("Autonomous live execution is not approved")
        return not blockers, list(dict.fromkeys(blockers))

    def fleet_status(self, account_ids: Iterable[Any]) -> Dict[str, Any]:
        statuses = [self.evaluate(account_id) for account_id in account_ids]
        return {
            "accounts": statuses,
            "ready_for_canary_count": sum(1 for item in statuses if item["ready_for_canary"]),
            "ready_for_full_live_count": sum(1 for item in statuses if item["ready_for_full_live"]),
            "all_live_ready": bool(statuses) and all(item["ready_for_full_live"] for item in statuses),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
