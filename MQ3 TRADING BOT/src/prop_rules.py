"""Versioned prop-firm rule profiles and conservative internal risk policies.

The hard limits in this module are compliance limits, not trading targets.  The
bot uses tighter internal limits so a spread spike, gap, commission, or delayed
equity update is less likely to touch a firm's breach line.

Funding Pips rules change over time.  The profile version and source URLs are
therefore included in every generated account policy and live execution must be
blocked if the operator has not selected an exact model and stage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


RULES_VERIFIED_ON = "2026-08-19"
FUNDING_PIPS_SOURCES = {
    "comparison": "https://help.fundingpips.com/hc/en-us/articles/48368490585105-Compare-Account-Models",
    "responsible_trading": "https://help.fundingpips.com/hc/en-us/articles/47328410434065-Responsible-Trading-Policy",
    "two_step_standard": "https://help.fundingpips.com/hc/en-us/articles/34501809112081-2-Step-Standard",
    "two_step_pro": "https://help.fundingpips.com/hc/en-us/articles/34502027344017-2-Step-Pro-Model",
    "two_step_flex": "https://help.fundingpips.com/hc/en-us/articles/47835196271249-2-Step-Flex",
    "one_step_flex": "https://help.fundingpips.com/hc/en-us/articles/34501697434385-1-Step-Flex",
    "zero": "https://help.fundingpips.com/hc/en-us/articles/34502157694865-FundingPips-Zero",
    "news_weekend": "https://help.fundingpips.com/hc/en-us/articles/34504137479441-News-Trading-Weekend-Holding",
    "automation": "https://help.fundingpips.com/hc/en-us/articles/34505029138449-Trading-Conduct-and-Security-Standards",
}


class AccountStage(str, Enum):
    EVALUATION_PHASE_1 = "EVALUATION_PHASE_1"
    EVALUATION_PHASE_2 = "EVALUATION_PHASE_2"
    MASTER = "MASTER"


class LossFloorType(str, Enum):
    STATIC_STARTING_BALANCE = "STATIC_STARTING_BALANCE"
    TRAILING_HIGH_WATER_MARK = "TRAILING_HIGH_WATER_MARK"


@dataclass(frozen=True)
class PropRuleProfile:
    key: str
    display_name: str
    phases: int
    phase_1_target_pct: float
    phase_2_target_pct: Optional[float]
    minimum_trading_days_phase_1: int
    minimum_trading_days_phase_2: int
    hard_daily_loss_pct: float
    hard_overall_loss_pct: float
    loss_floor_type: LossFloorType
    server_utc_offset_hours: int = 3
    inactivity_days: int = 30
    evaluation_news_hunting_prohibited: bool = True
    master_news_restricted_minutes: int = 5
    master_news_swing_exception_hours: int = 5
    master_weekend_holding_allowed: bool = False
    evaluation_weekend_holding_allowed: bool = True
    max_open_risk_pct: Optional[float] = None
    source_key: str = "comparison"


PROFILES: Dict[str, PropRuleProfile] = {
    "FUNDING_PIPS_1_STEP_FLEX": PropRuleProfile(
        key="FUNDING_PIPS_1_STEP_FLEX",
        display_name="Funding Pips 1 Step Flex",
        phases=1,
        phase_1_target_pct=12.0,
        phase_2_target_pct=None,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=3.0,
        hard_overall_loss_pct=12.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        source_key="one_step_flex",
    ),
    "FUNDING_PIPS_2_STEP_STANDARD": PropRuleProfile(
        key="FUNDING_PIPS_2_STEP_STANDARD",
        display_name="Funding Pips 2 Step Standard",
        phases=2,
        phase_1_target_pct=8.0,
        phase_2_target_pct=5.0,
        minimum_trading_days_phase_1=3,
        minimum_trading_days_phase_2=3,
        hard_daily_loss_pct=5.0,
        hard_overall_loss_pct=10.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        source_key="two_step_standard",
    ),
    "FUNDING_PIPS_2_STEP_PRO": PropRuleProfile(
        key="FUNDING_PIPS_2_STEP_PRO",
        display_name="Funding Pips 2 Step Pro",
        phases=2,
        phase_1_target_pct=6.0,
        phase_2_target_pct=6.0,
        minimum_trading_days_phase_1=1,
        minimum_trading_days_phase_2=1,
        hard_daily_loss_pct=3.0,
        hard_overall_loss_pct=6.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        source_key="two_step_pro",
    ),
    "FUNDING_PIPS_2_STEP_FLEX": PropRuleProfile(
        key="FUNDING_PIPS_2_STEP_FLEX",
        display_name="Funding Pips 2 Step Flex",
        phases=2,
        phase_1_target_pct=10.0,
        phase_2_target_pct=6.0,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=4.0,
        hard_overall_loss_pct=12.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        source_key="two_step_flex",
    ),
    "FUNDING_PIPS_ZERO": PropRuleProfile(
        key="FUNDING_PIPS_ZERO",
        display_name="Funding Pips Zero Instant Master",
        phases=0,
        phase_1_target_pct=0.0,
        phase_2_target_pct=None,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=3.0,
        hard_overall_loss_pct=5.0,
        loss_floor_type=LossFloorType.TRAILING_HIGH_WATER_MARK,
        master_news_restricted_minutes=10,
        evaluation_weekend_holding_allowed=False,
        max_open_risk_pct=1.0,
        source_key="zero",
    ),
    "FTMO_STANDARD": PropRuleProfile(
        key="FTMO_STANDARD",
        display_name="FTMO Standard / Swing Evaluation",
        phases=2,
        phase_1_target_pct=10.0,
        phase_2_target_pct=5.0,
        minimum_trading_days_phase_1=4,
        minimum_trading_days_phase_2=4,
        hard_daily_loss_pct=5.0,
        hard_overall_loss_pct=10.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        evaluation_news_hunting_prohibited=False,
        master_news_restricted_minutes=0,
        master_weekend_holding_allowed=True,
        evaluation_weekend_holding_allowed=True,
        source_key="comparison",
    ),
    "THE_FUNDED_TRADER_STANDARD": PropRuleProfile(
        key="THE_FUNDED_TRADER_STANDARD",
        display_name="The Funded Trader Standard Challenge",
        phases=2,
        phase_1_target_pct=10.0,
        phase_2_target_pct=5.0,
        minimum_trading_days_phase_1=3,
        minimum_trading_days_phase_2=3,
        hard_daily_loss_pct=5.0,
        hard_overall_loss_pct=10.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        evaluation_news_hunting_prohibited=True,
        master_news_restricted_minutes=15,
        master_weekend_holding_allowed=False,
        evaluation_weekend_holding_allowed=False,
        source_key="comparison",
    ),
    "THE_5ERS_BOOTCAMP": PropRuleProfile(
        key="THE_5ERS_BOOTCAMP",
        display_name="5%ers High Stakes / Bootcamp",
        phases=2,
        phase_1_target_pct=8.0,
        phase_2_target_pct=5.0,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=4.0,
        hard_overall_loss_pct=8.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        evaluation_news_hunting_prohibited=False,
        master_news_restricted_minutes=0,
        master_weekend_holding_allowed=True,
        evaluation_weekend_holding_allowed=True,
        source_key="comparison",
    ),
    "ALPHA_CAPITAL_STANDARD": PropRuleProfile(
        key="ALPHA_CAPITAL_STANDARD",
        display_name="Alpha Capital Standard Evaluation",
        phases=2,
        phase_1_target_pct=8.0,
        phase_2_target_pct=5.0,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=5.0,
        hard_overall_loss_pct=10.0,
        loss_floor_type=LossFloorType.STATIC_STARTING_BALANCE,
        evaluation_news_hunting_prohibited=True,
        master_news_restricted_minutes=15,
        master_weekend_holding_allowed=False,
        evaluation_weekend_holding_allowed=False,
        source_key="comparison",
    ),
    "E8_EVALUATION": PropRuleProfile(
        key="E8_EVALUATION",
        display_name="E8 Evaluation Model",
        phases=2,
        phase_1_target_pct=8.0,
        phase_2_target_pct=4.0,
        minimum_trading_days_phase_1=0,
        minimum_trading_days_phase_2=0,
        hard_daily_loss_pct=5.0,
        hard_overall_loss_pct=8.0,
        loss_floor_type=LossFloorType.TRAILING_HIGH_WATER_MARK,
        evaluation_news_hunting_prohibited=False,
        master_news_restricted_minutes=0,
        master_weekend_holding_allowed=True,
        evaluation_weekend_holding_allowed=True,
        source_key="comparison",
    ),
}


MODEL_ALIASES = {
    "2_STEP_STANDARD": "FUNDING_PIPS_2_STEP_STANDARD",
    "STANDARD": "FUNDING_PIPS_2_STEP_STANDARD",
    "FUNDING_PIPS": "FUNDING_PIPS_2_STEP_STANDARD",
    "FUNDINGPIPS": "FUNDING_PIPS_2_STEP_STANDARD",
    "2_STEP_PRO": "FUNDING_PIPS_2_STEP_PRO",
    "PRO": "FUNDING_PIPS_2_STEP_PRO",
    "2_STEP_FLEX": "FUNDING_PIPS_2_STEP_FLEX",
    "FLEX": "FUNDING_PIPS_2_STEP_FLEX",
    "1_STEP_FLEX": "FUNDING_PIPS_1_STEP_FLEX",
    "ZERO": "FUNDING_PIPS_ZERO",
    "FTMO": "FTMO_STANDARD",
    "FTMO_STANDARD": "FTMO_STANDARD",
    "FTMO_SWING": "FTMO_STANDARD",
    "THE_FUNDED_TRADER": "THE_FUNDED_TRADER_STANDARD",
    "THEFUNDEDTRADER": "THE_FUNDED_TRADER_STANDARD",
    "TFT": "THE_FUNDED_TRADER_STANDARD",
    "5ERS": "THE_5ERS_BOOTCAMP",
    "THE_5ERS": "THE_5ERS_BOOTCAMP",
    "THE5ERS": "THE_5ERS_BOOTCAMP",
    "FIVE_PERCENTERS": "THE_5ERS_BOOTCAMP",
    "5%ERS": "THE_5ERS_BOOTCAMP",
    "ALPHA_CAPITAL": "ALPHA_CAPITAL_STANDARD",
    "ALPHACAPITAL": "ALPHA_CAPITAL_STANDARD",
    "ALPHA": "ALPHA_CAPITAL_STANDARD",
    "E8": "E8_EVALUATION",
    "E8_MARKETS": "E8_EVALUATION",
    "E8MARKETS": "E8_EVALUATION",
}


def normalize_model(model: Optional[str], *, require_explicit: bool = False) -> str:
    raw = str(model or "").strip().upper().replace("-", "_").replace(" ", "_")
    if raw in PROFILES:
        return raw
    if raw in MODEL_ALIASES:
        if require_explicit and raw in {"FUNDING_PIPS", "FUNDINGPIPS"}:
            raise ValueError("Exact Funding Pips model is required for live readiness")
        return MODEL_ALIASES[raw]
    if not raw and not require_explicit:
        return "FUNDING_PIPS_2_STEP_STANDARD"
    raise ValueError(f"Unknown Prop Firm model: {model!r}")


def normalize_stage(stage: Optional[str], profile: PropRuleProfile) -> AccountStage:
    if profile.phases == 0:
        return AccountStage.MASTER
    raw = str(stage or AccountStage.EVALUATION_PHASE_1.value).strip().upper()
    aliases = {
        "PHASE1": AccountStage.EVALUATION_PHASE_1,
        "PHASE_1": AccountStage.EVALUATION_PHASE_1,
        "EVAL1": AccountStage.EVALUATION_PHASE_1,
        "PHASE2": AccountStage.EVALUATION_PHASE_2,
        "PHASE_2": AccountStage.EVALUATION_PHASE_2,
        "EVAL2": AccountStage.EVALUATION_PHASE_2,
        "FUNDED": AccountStage.MASTER,
        "MASTER_ACCOUNT": AccountStage.MASTER,
    }
    if raw in aliases:
        normalized = aliases[raw]
    else:
        try:
            normalized = AccountStage(raw)
        except ValueError as exc:
            raise ValueError(f"Unknown account stage: {stage!r}") from exc
    if profile.phases == 1 and normalized == AccountStage.EVALUATION_PHASE_2:
        raise ValueError(f"{profile.display_name} does not have Phase 2")
    return normalized


def build_account_policy(
    *,
    account_size: float,
    model: Optional[str],
    stage: Optional[str] = None,
    reward_cycle: Optional[str] = None,
    require_explicit_model: bool = False,
) -> Dict[str, Any]:
    """Return hard firm rules plus deliberately tighter internal controls."""
    size = float(account_size)
    if size <= 0:
        raise ValueError("account_size must be positive")
    model_key = normalize_model(model, require_explicit=require_explicit_model)
    profile = PROFILES[model_key]
    account_stage = normalize_stage(stage, profile)

    if account_stage == AccountStage.EVALUATION_PHASE_1:
        target_pct = profile.phase_1_target_pct
        minimum_days = profile.minimum_trading_days_phase_1
    elif account_stage == AccountStage.EVALUATION_PHASE_2:
        target_pct = float(profile.phase_2_target_pct or 0.0)
        minimum_days = profile.minimum_trading_days_phase_2
    else:
        target_pct = 0.0
        minimum_days = 0

    # These are operational stops, not Funding Pips' breach limits.
    internal_risk_per_trade_pct = 0.25
    internal_daily_stop_pct = min(1.50, profile.hard_daily_loss_pct * 0.50)
    internal_overall_stop_pct = min(4.00, profile.hard_overall_loss_pct * 0.60)
    # Funding Pips' published 3%/2% Risk Per Trade Idea rule belongs only to
    # legacy 10%-target Standard Master accounts.  Current Standard accounts
    # have an 8% evaluation target, so exposing 3%/2% as their hard limit would
    # be both inaccurate and dangerously permissive.
    legacy_risk_per_idea_applies = False
    hard_risk_per_idea_pct: Optional[float] = None

    normalized_reward_cycle = str(reward_cycle or "").strip().upper().replace("-", "_").replace(" ", "_")
    reward_cycle_aliases = {
        "ONDEMAND": "ON_DEMAND",
        "ON_DEMAND": "ON_DEMAND",
        "WEEKLY": "WEEKLY",
        "BIWEEKLY": "BI_WEEKLY",
        "BI_WEEKLY": "BI_WEEKLY",
        "MONTHLY": "MONTHLY",
    }
    if normalized_reward_cycle:
        try:
            normalized_reward_cycle = reward_cycle_aliases[normalized_reward_cycle]
        except KeyError as exc:
            raise ValueError(f"Unknown reward cycle: {reward_cycle!r}") from exc
    else:
        normalized_reward_cycle = ""

    is_current_standard_master = (
        model_key == "FUNDING_PIPS_2_STEP_STANDARD"
        and account_stage == AccountStage.MASTER
    )
    striking_system_applies: Optional[bool] = False
    striking_warning_trigger_pct: Optional[float] = None
    if is_current_standard_master and not normalized_reward_cycle:
        # The selected reward cycle changes the trigger and, for smaller
        # accounts, whether the standard trigger applies at all.  Fail later
        # live-readiness checks until the operator selects the exact cycle.
        striking_system_applies = None
    elif is_current_standard_master and normalized_reward_cycle == "MONTHLY":
        striking_system_applies = True
        striking_warning_trigger_pct = 1.0
    elif is_current_standard_master:
        striking_system_applies = size > 25000
        striking_warning_trigger_pct = 1.2 if striking_system_applies else None

    # New evaluation accounts of 25K+ are subject to the published concentration policy.
    concentration_applies = size >= 25000 and account_stage != AccountStage.MASTER

    if "FTMO" in model_key:
        firm_str = "FTMO"
    elif "THE_FUNDED_TRADER" in model_key:
        firm_str = "THE_FUNDED_TRADER"
    elif "5ERS" in model_key or "FIVE_PERCENTERS" in model_key:
        firm_str = "5ERS"
    elif "ALPHA_CAPITAL" in model_key:
        firm_str = "ALPHA_CAPITAL"
    elif "E8" in model_key:
        firm_str = "E8"
    else:
        firm_str = "FUNDING_PIPS"

    result = asdict(profile)
    result["loss_floor_type"] = profile.loss_floor_type.value
    result.update(
        {
            "firm": firm_str,
            "model": model_key,
            "stage": account_stage.value,
            "account_size": size,
            "profit_target_pct": target_pct,
            "profit_target_dollars": round(size * target_pct / 100.0, 2),
            "minimum_trading_days": minimum_days,
            "hard_daily_loss_fraction": profile.hard_daily_loss_pct / 100.0,
            "hard_overall_loss_fraction": profile.hard_overall_loss_pct / 100.0,
            "hard_daily_loss_dollars_at_start": round(size * profile.hard_daily_loss_pct / 100.0, 2),
            "hard_overall_loss_dollars": round(size * profile.hard_overall_loss_pct / 100.0, 2),
            "hard_risk_per_trade_idea_pct": hard_risk_per_idea_pct,
            "legacy_risk_per_trade_idea_rule_applies": legacy_risk_per_idea_applies,
            "firm_max_open_risk_pct": profile.max_open_risk_pct,
            "reward_cycle": normalized_reward_cycle or None,
            "exact_reward_cycle_required_before_master_live": is_current_standard_master,
            "striking_system_applies": striking_system_applies,
            "striking_warning_trigger_pct": striking_warning_trigger_pct,
            "striking_warning_count_to_breach": 4 if striking_system_applies else None,
            "striking_warnings_reset_after_reward": False if striking_system_applies else None,
            "internal_risk_per_trade_pct": internal_risk_per_trade_pct,
            "internal_daily_stop_pct": internal_daily_stop_pct,
            "internal_overall_stop_pct": internal_overall_stop_pct,
            "internal_daily_stop_dollars_at_start": round(size * internal_daily_stop_pct / 100.0, 2),
            "internal_overall_stop_dollars": round(size * internal_overall_stop_pct / 100.0, 2),
            "internal_max_open_risk_pct": 0.50,
            "internal_max_correlated_idea_risk_pct": 0.35,
            "internal_max_trades_per_day": 3,
            "internal_consecutive_loss_lockout": 3,
            "internal_news_blackout_minutes": 15,
            "internal_weekend_holding_allowed": False,
            "daily_loss_baseline": "HIGHER_OF_OPENING_BALANCE_OR_EQUITY",
            "daily_reset_server_time": "00:00 UTC+03:00",
            "profit_concentration_policy_applies": concentration_applies,
            "profit_concentration_threshold_pct": 60.0 if concentration_applies else None,
            "rules_verified_on": RULES_VERIFIED_ON,
            "source_url": FUNDING_PIPS_SOURCES.get(profile.source_key, FUNDING_PIPS_SOURCES["comparison"]),
            "automation_policy_url": FUNDING_PIPS_SOURCES["automation"],
            "news_weekend_policy_url": FUNDING_PIPS_SOURCES["news_weekend"],
            "operator_warning": "Re-verify current dashboard/email rules before every purchase and stage transition.",
        }
    )
    return result


def list_supported_profiles() -> Dict[str, Dict[str, Any]]:
    return {
        key: {
            "display_name": profile.display_name,
            "phases": profile.phases,
            "daily_loss_pct": profile.hard_daily_loss_pct,
            "overall_loss_pct": profile.hard_overall_loss_pct,
            "phase_1_target_pct": profile.phase_1_target_pct,
            "phase_2_target_pct": profile.phase_2_target_pct,
            "source_url": FUNDING_PIPS_SOURCES[profile.source_key],
        }
        for key, profile in PROFILES.items()
    }
