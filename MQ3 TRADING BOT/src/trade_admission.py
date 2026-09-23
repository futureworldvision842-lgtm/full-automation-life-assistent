"""Fail-closed market-context admission for live and broker-demo orders.

Strategy confidence is never sufficient on its own. A live or demo order must also
have a fresh broker quote, a fresh signal, verified calendar clearance, an open
market, acceptable spread, sufficient time before weekend close, strategy registry
validation receipt, and portfolio risk clearance.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from src.economic_calendar_service import economic_calendar_service
from src.portfolio_risk_service import portfolio_risk_service
from src.strategy_registry import strategy_registry, StrategyStage
from src.institutional_knowledge import InstitutionalKnowledge
from src.trend_confluence_filter import trend_confluence_filter


def _timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class TradeAdmissionGate:
    def __init__(
        self,
        *,
        max_quote_age_seconds: float = 5.0,
        max_signal_age_seconds: float = 60.0,
        max_calendar_age_seconds: float = 300.0,
        max_spread_multiplier: float = 2.0,
        min_minutes_to_weekend_close: float = 180.0,
    ):
        self.max_quote_age_seconds = float(max_quote_age_seconds)
        self.max_signal_age_seconds = float(max_signal_age_seconds)
        self.max_calendar_age_seconds = float(max_calendar_age_seconds)
        self.max_spread_multiplier = float(max_spread_multiplier)
        self.min_minutes_to_weekend_close = float(min_minutes_to_weekend_close)

    def evaluate(self, context: Optional[Dict[str, Any]], *, live: bool) -> Tuple[bool, List[str]]:
        if not live:
            return True, []
        if not isinstance(context, dict):
            return False, ["Live order has no market_context"]

        reasons: List[str] = []
        now = datetime.now(timezone.utc)
        data_mode = str(context.get("data_mode", "")).upper()
        if data_mode != "LIVE":
            reasons.append(f"Market data mode must be LIVE, got {data_mode or 'MISSING'}")
        if context.get("actionable") is not True:
            reasons.append("Market context is not explicitly actionable")
        if context.get("market_open") is not True:
            reasons.append("Market-open status is missing or false")

        quote_at = _timestamp(context.get("quote_observed_at"))
        signal_at = _timestamp(context.get("signal_generated_at"))
        if not quote_at:
            reasons.append("Fresh broker quote timestamp is missing")
        elif max(0.0, (now - quote_at).total_seconds()) > self.max_quote_age_seconds:
            reasons.append("Broker quote is stale")
        if not signal_at:
            reasons.append("Signal generation timestamp is missing")
        elif max(0.0, (now - signal_at).total_seconds()) > self.max_signal_age_seconds:
            reasons.append("Signal is stale")

        calendar = context.get("news_clearance")
        if not isinstance(calendar, dict):
            reasons.append("Verified news calendar clearance is missing")
        else:
            if calendar.get("verified") is not True:
                reasons.append("News calendar clearance is unverified")
            if calendar.get("is_blackout") is True or calendar.get("is_cleared") is not True:
                reasons.append("High-impact news blackout is active or unclear")
            age = calendar.get("age_seconds")
            try:
                if not math.isfinite(float(age)) or float(age) > self.max_calendar_age_seconds:
                    reasons.append("News calendar snapshot is stale")
            except (TypeError, ValueError):
                reasons.append("News calendar age is missing")

        try:
            spread = float(context.get("spread"))
            typical_spread = float(context.get("typical_spread"))
            if not all(math.isfinite(value) and value >= 0 for value in (spread, typical_spread)):
                raise ValueError
            if typical_spread <= 0:
                reasons.append("Typical spread baseline is unavailable")
            elif spread > typical_spread * self.max_spread_multiplier:
                reasons.append("Current spread exceeds the live admission multiplier")
        except (TypeError, ValueError):
            reasons.append("Verified spread telemetry is missing")

        minutes_to_close = context.get("minutes_to_weekend_close")
        if now.weekday() == 4:
            try:
                minutes = float(minutes_to_close)
                if not math.isfinite(minutes) or minutes < self.min_minutes_to_weekend_close:
                    reasons.append("Too close to weekend market close")
            except (TypeError, ValueError):
                reasons.append("Friday order lacks weekend-close telemetry")

        source = str(context.get("quote_source", "")).strip()
        if not source:
            reasons.append("Broker quote source is missing")

        # Session kill-zone evaluation (London 07:00-11:30 UTC and NY 12:30-16:30 UTC)
        check_time = _timestamp(context.get("current_time_utc")) or quote_at or now
        if not context.get("bypass_kill_zone", False):
            is_kz, kz_session = InstitutionalKnowledge.is_in_kill_zone(check_time)
            if not is_kz:
                reasons.append("Trade entry rejected outside London (07:00-11:30 UTC) and NY (12:30-16:30 UTC) kill zones")

        # MTF Trend Confluence check if provided
        if "mtf_confluence" in context:
            mtf = context["mtf_confluence"]
            if isinstance(mtf, dict) and not mtf.get("approved", False):
                reasons.append(mtf.get("reason", "MTF trend conflict: M15 conflicts with H1/H4"))
        elif any(k in context for k in ("m15_df", "h1_df", "h4_df")):
            m15 = context.get("m15_df")
            h1 = context.get("h1_df")
            h4 = context.get("h4_df")
            c_ok, c_dir, c_meta = trend_confluence_filter.evaluate_trend_confluence(
                m15, h1, h4, symbol=context.get("symbol", "XAUUSD"), direction_hint=context.get("direction")
            )
            if not c_ok:
                reasons.append(c_meta.get("reason", "MTF trend conflict: M15 conflicts with H1/H4"))

        return not reasons, list(dict.fromkeys(reasons))

    def evaluate_comprehensive_admission(
        self,
        *,
        account_id: str,
        symbol: str,
        direction: str,
        strategy_id: str,
        strategy_version: str,
        regime: str,
        risk_pct: float,
        market_context: Optional[Dict[str, Any]],
        is_live_order: bool = False,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Unified Central Admission Authority.
        All orders (Live, Demo, Auto, Manual, WhatsApp) MUST pass this single gate.
        """
        blockers: List[str] = []
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        # 1. Evaluate Market Context & Freshness
        ok_context, context_reasons = self.evaluate(market_context, live=is_live_order)
        if not ok_context:
            blockers.extend(context_reasons)

        # 2. Strategy Registry & Regime Eligibility Gate
        strat = strategy_registry.get_strategy(strategy_id, strategy_version)
        if not strat:
            blockers.append(f"Strategy {strategy_id}@{strategy_version} not found in Strategy Registry")
        else:
            if not strat.is_enabled:
                blockers.append(f"Strategy {strategy_id} is disabled")
            ok_regime, regime_reason = strat.is_regime_eligible(regime)
            if not ok_regime:
                blockers.append(regime_reason)

            # Check Validation Receipt if Live
            if is_live_order:
                if not strat.active_validation_receipt:
                    blockers.append(f"Strategy {strategy_id} has no active validation receipt for live trading")
                elif strat.active_validation_receipt.is_expired(now_iso):
                    blockers.append(f"Strategy {strategy_id} validation receipt expired on {strat.active_validation_receipt.expiry_date_utc}")
                elif strat.active_validation_receipt.approved_stage not in (StrategyStage.CANARY, StrategyStage.LIVE):
                    blockers.append(f"Strategy {strategy_id} validation stage {strat.active_validation_receipt.approved_stage.value} is not approved for live trading")

        # 3. Official Economic Calendar Gate
        cal_locked, cal_reason, _ = economic_calendar_service.evaluate_symbol_lockout(symbol, now_iso)
        if cal_locked:
            blockers.append(cal_reason)

        # 4. Portfolio & Account Risk Gate
        ok_risk, risk_reason, risk_telemetry = portfolio_risk_service.evaluate_trade_admission_risk(
            account_id=account_id,
            symbol=symbol,
            direction=direction,
            risk_pct=risk_pct,
            current_time_utc=now_iso,
        )
        if not ok_risk:
            blockers.append(risk_reason)

        # 5. Multi-Timeframe Trend Confluence Gate
        if isinstance(market_context, dict):
            if "mtf_confluence" in market_context:
                mtf = market_context["mtf_confluence"]
                if isinstance(mtf, dict) and not mtf.get("approved", False):
                    blockers.append(mtf.get("reason", "MTF trend conflict: M15 conflicts with H1/H4"))
            elif any(k in market_context for k in ("m15_df", "h1_df", "h4_df")):
                m15 = market_context.get("m15_df")
                h1 = market_context.get("h1_df")
                h4 = market_context.get("h4_df")
                c_ok, c_dir, c_meta = trend_confluence_filter.evaluate_trend_confluence(
                    m15, h1, h4, symbol=symbol, direction_hint=direction
                )
                if not c_ok:
                    blockers.append(c_meta.get("reason", "MTF trend conflict: M15 conflicts with H1/H4"))

        is_admitted = len(blockers) == 0
        admission_receipt = {
            "admitted": is_admitted,
            "account_id": account_id,
            "symbol": symbol,
            "direction": direction,
            "strategy_id": strategy_id,
            "regime": regime,
            "timestamp_utc": now_iso,
            "blockers": blockers,
            "risk_telemetry": risk_telemetry,
        }
        return is_admitted, blockers, admission_receipt


# Global singleton gate
trade_admission_gate = TradeAdmissionGate()
