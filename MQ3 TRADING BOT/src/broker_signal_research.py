"""Broker-backed, evidence-first trading research.

This module deliberately stops before execution.  It turns fresh broker quotes
and *closed* OHLCV bars into conditional research, exposes the evidence on both
sides, sizes risk from the broker's contract metadata, and fails closed when a
required source is missing.  Tick volume is treated as an activity proxy; it
does not identify an institution or prove buyer/seller volume.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.indicator_ensemble import ExplainableIndicatorEnsemble


class BrokerSignalResearchEngine:
    """Build short-lived, non-executable research from an attached MT5 feed."""

    REQUIRED_TIMEFRAMES = ("M5", "M15", "H1", "H4")
    ACCEPTED_DATA_MODES = {"BROKER_DEMO", "LIVE"}

    def __init__(self, connector: Any, config: Optional[Dict[str, Any]] = None, cache_seconds: int = 12):
        self.connector = connector
        self.config = config or {}
        self.cache_seconds = max(1, int(cache_seconds))
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.indicator_ensemble = ExplainableIndicatorEnsemble()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _finite(value: Any, default: Optional[float] = None) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default

    @staticmethod
    def _round(value: Optional[float], digits: int) -> Optional[float]:
        return None if value is None else round(float(value), digits)

    @staticmethod
    def _mask_login(login: Any) -> Optional[str]:
        if login is None:
            return None
        raw = str(login)
        return ("*" * max(0, len(raw) - 4)) + raw[-4:]

    @staticmethod
    def _indicator_frame(frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy()
        for column in ("open", "high", "low", "close"):
            df[column] = pd.to_numeric(df[column], errors="coerce")
        if "tick_volume" not in df.columns:
            df["tick_volume"] = pd.to_numeric(df.get("real_volume", 0), errors="coerce").fillna(0)
        else:
            df["tick_volume"] = pd.to_numeric(df["tick_volume"], errors="coerce").fillna(0)
        df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
        close = df["close"]
        df["ema20"] = close.ewm(span=20, adjust=False).mean()
        df["ema50"] = close.ewm(span=50, adjust=False).mean()
        df["ema200"] = close.ewm(span=200, adjust=False).mean()

        previous_close = close.shift(1)
        true_range = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - previous_close).abs(),
                (df["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
        rsi = rsi.mask((gain == 0) & (loss > 0), 0.0)
        df["rsi14"] = rsi.mask((gain == 0) & (loss == 0), 50.0).fillna(50.0)
        return df

    @staticmethod
    def _bar_time(frame: pd.DataFrame) -> Optional[datetime]:
        if frame.empty or "time" not in frame.columns:
            return None
        observed = frame.iloc[-1]["time"]
        try:
            if isinstance(observed, pd.Timestamp):
                parsed = observed.to_pydatetime()
            elif isinstance(observed, datetime):
                parsed = observed
            elif isinstance(observed, (int, float, np.integer, np.floating)):
                parsed = datetime.fromtimestamp(float(observed), timezone.utc)
            else:
                parsed = pd.to_datetime(observed, utc=True).to_pydatetime()
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _trend_state(frame: pd.DataFrame) -> Dict[str, Any]:
        last = frame.iloc[-1]
        slope = float(frame["ema20"].iloc[-1] - frame["ema20"].iloc[-6]) if len(frame) >= 6 else 0.0
        if last["ema20"] > last["ema50"] and last["close"] > last["ema20"] and slope > 0:
            state = "BULLISH"
        elif last["ema20"] < last["ema50"] and last["close"] < last["ema20"] and slope < 0:
            state = "BEARISH"
        else:
            state = "MIXED"
        return {
            "state": state,
            "close": float(last["close"]),
            "ema20": float(last["ema20"]),
            "ema50": float(last["ema50"]),
            "ema200": float(last["ema200"]),
            "ema20_slope": slope,
            "rsi14": float(last["rsi14"]),
            "atr14": float(last["atr14"]),
        }

    @staticmethod
    def _add_evidence(
        destination: List[Dict[str, Any]], timeframe: str, finding: str, side: str, weight: float, value: Any
    ) -> None:
        destination.append(
            {
                "timeframe": timeframe,
                "finding": finding,
                "side": side,
                "weight": float(weight),
                "value": value,
                "source": "MT5 broker closed OHLCV bars",
            }
        )

    def _load_closed_frames(self, symbol: str) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        frames: Dict[str, pd.DataFrame] = {}
        blockers: List[str] = []
        for timeframe in self.REQUIRED_TIMEFRAMES:
            try:
                raw = self.connector.get_historical_candles(symbol, timeframe, count=260)
            except Exception:
                raw = pd.DataFrame()
            if not isinstance(raw, pd.DataFrame) or len(raw) < self.indicator_ensemble.MINIMUM_BARS + 1:
                blockers.append(
                    f"{timeframe} has fewer than {self.indicator_ensemble.MINIMUM_BARS + 1} broker bars "
                    "(including the forming bar)"
                )
                continue
            # Position zero normally includes the forming bar.  Never use it to
            # create a signal because its OHLC and volume can still change.
            closed = self._indicator_frame(raw.iloc[:-1])
            if len(closed) < self.indicator_ensemble.MINIMUM_BARS or self._finite(closed.iloc[-1].get("atr14")) in (None, 0.0):
                blockers.append(f"{timeframe} closed-bar indicators are incomplete")
                continue
            frames[timeframe] = closed
        return frames, blockers

    def _account_suitability(
        self,
        symbol: str,
        direction: Optional[str],
        entry: Optional[float],
        stop: Optional[float],
        execution_blockers: Iterable[str],
    ) -> Dict[str, Any]:
        try:
            account = self.connector.get_account_info()
        except Exception:
            account = {}
        try:
            positions = self.connector.get_open_positions()
        except Exception:
            positions = []
        try:
            spec = self.connector.get_symbol_spec(symbol)
        except Exception:
            spec = {}

        risk_cfg = self.config.get("risk_management", {})
        risk_pct = min(max(float(risk_cfg.get("risk_per_trade_pct", 0.25)), 0.0), 0.25)
        equity = self._finite(account.get("equity"), 0.0) or 0.0
        risk_budget = equity * risk_pct / 100.0
        max_open = int(risk_cfg.get("max_open_trades", 3))
        open_count = len(positions or [])
        local_blockers: List[str] = []
        lot_size: Optional[float] = None
        monetary_risk: Optional[float] = None

        tick_size = self._finite(spec.get("trade_tick_size"))
        tick_value_loss = self._finite(spec.get("trade_tick_value_loss")) or self._finite(spec.get("trade_tick_value"))
        volume_min = self._finite(spec.get("volume_min"))
        volume_step = self._finite(spec.get("volume_step"))
        volume_max = self._finite(spec.get("volume_max"))

        if not account.get("available"):
            local_blockers.append("Verified broker account telemetry is unavailable")
        if open_count >= max_open:
            local_blockers.append(f"Open-position cap reached ({open_count}/{max_open})")
        if not direction or entry is None or stop is None:
            local_blockers.append("No directional candidate has a valid entry and stop")
        elif not all(v and v > 0 for v in (tick_size, tick_value_loss, volume_min, volume_step, volume_max)):
            local_blockers.append("Broker contract/tick-value metadata is incomplete")
        else:
            stop_distance = abs(entry - stop)
            loss_per_lot = (stop_distance / tick_size) * tick_value_loss
            if loss_per_lot <= 0:
                local_blockers.append("Computed stop loss per lot is invalid")
            else:
                raw_lots = risk_budget / loss_per_lot
                stepped = math.floor((raw_lots + 1e-12) / volume_step) * volume_step
                stepped = min(stepped, volume_max)
                if stepped + 1e-12 < volume_min:
                    local_blockers.append(
                        f"Risk-sized volume {raw_lots:.4f} is below broker minimum {volume_min:g}; no forced minimum lot"
                    )
                else:
                    lot_size = round(stepped, 8)
                    monetary_risk = lot_size * loss_per_lot

        all_blockers = list(dict.fromkeys([*execution_blockers, *local_blockers]))
        return {
            "account_login_masked": self._mask_login(account.get("login")),
            "server": account.get("server"),
            "account_data_mode": account.get("data_mode", "UNAVAILABLE"),
            "currency": account.get("currency"),
            "equity": self._round(equity, 2),
            "risk_pct": risk_pct,
            "risk_budget": self._round(risk_budget, 2),
            "open_positions": open_count,
            "max_open_positions": max_open,
            "calculated_lots": lot_size,
            "estimated_stop_risk": self._round(monetary_risk, 2),
            "broker_min_lot": volume_min,
            "broker_lot_step": volume_step,
            "verdict": "DO_NOT_TAKE_NOW" if all_blockers else "CONDITIONAL_RESEARCH_ONLY",
            "reasons": all_blockers or ["Risk size fits broker metadata; all remaining execution gates still apply"],
            "approval_note": "Owner YES is necessary for a future order but never bypasses freshness, news, spread, drawdown, validation, or broker authorization gates.",
        }

    def _unavailable(self, symbol: str, blockers: List[str], quote: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = self._utc_now()
        return {
            "status": "unavailable",
            "symbol": symbol,
            "decision": "WAIT",
            "direction": None,
            "actionable": False,
            "execution_ready": False,
            "data_mode": (quote or {}).get("data_mode", "UNAVAILABLE"),
            "source": "MT5 broker feed",
            "generated_at": now.isoformat(),
            "expires_at": now.isoformat(),
            "evidence_score": 0,
            "confidence_label": "NO_EDGE",
            "confidence_note": "Evidence score is not a win probability.",
            "blockers": list(dict.fromkeys(blockers)),
            "technical_evidence": [],
            "opposing_evidence": [],
            "indicator_ensemble": {
                "status": "UNAVAILABLE",
                "actionable": False,
                "decision_use": "CONFLICT_GUARD_AND_EXPLANATION_ONLY",
                "reason": "Fresh closed broker bars are unavailable or incomplete.",
                "timeframes": {},
            },
            "scenarios": [],
            "institution_attribution": {"status": "UNAVAILABLE", "reason": "OHLCV cannot identify a participant."},
        }

    def analyze(self, symbol: str = "XAUUSD", force: bool = False) -> Dict[str, Any]:
        symbol = str(symbol or "XAUUSD").upper().strip()
        cached = self._cache.get(symbol)
        if cached and not force and time.time() - cached[0] <= self.cache_seconds:
            return cached[1]

        try:
            quote = self.connector.get_live_spread(symbol)
        except Exception:
            quote = {"data_mode": "UNAVAILABLE", "is_normal": False}
        data_mode = str(quote.get("data_mode", "UNAVAILABLE")).upper()
        quote_age = self._finite(quote.get("age_seconds"))
        blockers: List[str] = []
        if data_mode not in self.ACCEPTED_DATA_MODES:
            blockers.append(f"Broker feed mode {data_mode} is not eligible for live research")
        if self._finite(quote.get("bid")) is None or self._finite(quote.get("ask")) is None:
            blockers.append("Fresh broker bid/ask is unavailable")
        if quote_age is None or quote_age > 15:
            blockers.append("Broker quote is stale or has no broker timestamp")
        if quote.get("is_normal") is not True:
            blockers.append("Spread guard is not clear")

        # A technical frame can exist for a symbol that has no current Market
        # Watch tick.  Do not build entry/SL/TP from a missing or ineligible
        # quote, and do not let that one symbol fail a universe scan.
        if (
            data_mode not in self.ACCEPTED_DATA_MODES
            or self._finite(quote.get("bid")) is None
            or self._finite(quote.get("ask")) is None
        ):
            result = self._unavailable(symbol, blockers, quote)
            self._cache[symbol] = (time.time(), result)
            return result

        frames, frame_blockers = self._load_closed_frames(symbol)
        blockers.extend(frame_blockers)
        if len(frames) != len(self.REQUIRED_TIMEFRAMES):
            result = self._unavailable(symbol, blockers, quote)
            self._cache[symbol] = (time.time(), result)
            return result

        now_for_freshness = self._utc_now()
        maximum_closed_bar_age = {"M5": 12 * 60, "M15": 35 * 60, "H1": 2.25 * 3600, "H4": 9 * 3600}
        for timeframe, maximum_age in maximum_closed_bar_age.items():
            bar_time = self._bar_time(frames[timeframe])
            age = (now_for_freshness - bar_time).total_seconds() if bar_time else float("inf")
            if age < 0 or age > maximum_age:
                blockers.append(f"Latest closed {timeframe} broker bar is stale or has an invalid timestamp")

        trends = {tf: self._trend_state(frame) for tf, frame in frames.items()}
        indicator_ensembles = {
            timeframe: self.indicator_ensemble.analyze(frame, timeframe)
            for timeframe, frame in frames.items()
        }
        evidence: List[Dict[str, Any]] = []
        buy_score = 0.0
        sell_score = 0.0

        for timeframe, weight in (("H4", 20), ("H1", 24), ("M15", 14), ("M5", 10)):
            state = trends[timeframe]["state"]
            if state == "BULLISH":
                buy_score += weight
                self._add_evidence(evidence, timeframe, "EMA trend and slope aligned", "BUY", weight, state)
            elif state == "BEARISH":
                sell_score += weight
                self._add_evidence(evidence, timeframe, "EMA trend and slope aligned", "SELL", weight, state)
            else:
                self._add_evidence(evidence, timeframe, "EMA trend is mixed", "NEUTRAL", 0, state)

        m15 = frames["M15"]
        m5 = frames["M5"]
        m15_last = m15.iloc[-1]
        m5_last = m5.iloc[-1]
        atr = float(m15_last["atr14"])
        recent = m15.iloc[-21:-1] if len(m15) >= 22 else m15.iloc[:-1]
        recent_high = float(recent["high"].max())
        recent_low = float(recent["low"].min())
        range_width = max(recent_high - recent_low, atr * 0.25)
        range_position = float((m15_last["close"] - recent_low) / range_width)

        rsi = float(m15_last["rsi14"])
        if 52 <= rsi <= 68:
            buy_score += 10
            self._add_evidence(evidence, "M15", "RSI supports upside without being extreme", "BUY", 10, round(rsi, 1))
        elif 32 <= rsi <= 48:
            sell_score += 10
            self._add_evidence(evidence, "M15", "RSI supports downside without being extreme", "SELL", 10, round(rsi, 1))
        elif rsi > 72:
            sell_score += 3
            self._add_evidence(evidence, "M15", "RSI is stretched; continuation risk is elevated", "SELL", 3, round(rsi, 1))
        elif rsi < 28:
            buy_score += 3
            self._add_evidence(evidence, "M15", "RSI is stretched; continuation risk is elevated", "BUY", 3, round(rsi, 1))

        bullish_trigger = bool(m5_last["close"] > m5_last["open"] and m5_last["close"] > m5_last["ema20"])
        bearish_trigger = bool(m5_last["close"] < m5_last["open"] and m5_last["close"] < m5_last["ema20"])
        if bullish_trigger:
            buy_score += 10
            self._add_evidence(evidence, "M5", "Last closed candle confirms above EMA20", "BUY", 10, float(m5_last["close"]))
        if bearish_trigger:
            sell_score += 10
            self._add_evidence(evidence, "M5", "Last closed candle confirms below EMA20", "SELL", 10, float(m5_last["close"]))

        previous = m15.iloc[-2]
        bullish_sweep = bool(m15_last["low"] < recent_low and m15_last["close"] > recent_low and m15_last["close"] > m15_last["open"])
        bearish_sweep = bool(m15_last["high"] > recent_high and m15_last["close"] < recent_high and m15_last["close"] < m15_last["open"])
        if bullish_sweep:
            buy_score += 10
            self._add_evidence(evidence, "M15", "Closed bar swept recent low and reclaimed it", "BUY", 10, recent_low)
        if bearish_sweep:
            sell_score += 10
            self._add_evidence(evidence, "M15", "Closed bar swept recent high and rejected it", "SELL", 10, recent_high)

        signed_proxy = (np.sign(m15["close"] - m15["open"]) * m15["tick_volume"]).tail(20)
        proxy_total = float(signed_proxy.sum())
        proxy_scale = float(m15["tick_volume"].tail(20).sum()) or 1.0
        proxy_ratio = max(-1.0, min(1.0, proxy_total / proxy_scale))
        if proxy_ratio >= 0.10:
            buy_score += 6
            self._add_evidence(evidence, "M15", "Signed tick-volume activity proxy is positive", "BUY", 6, round(proxy_ratio, 3))
        elif proxy_ratio <= -0.10:
            sell_score += 6
            self._add_evidence(evidence, "M15", "Signed tick-volume activity proxy is negative", "SELL", 6, round(proxy_ratio, 3))
        else:
            self._add_evidence(evidence, "M15", "Signed tick-volume activity proxy is balanced", "NEUTRAL", 0, round(proxy_ratio, 3))

        score_gap = abs(buy_score - sell_score)
        winning_score = max(buy_score, sell_score)
        direction: Optional[str] = None
        if winning_score >= 58 and score_gap >= 18 and not blockers:
            direction = "BUY" if buy_score > sell_score else "SELL"
        decision = f"{direction}_CANDIDATE" if direction else "WAIT"

        bid = float(quote["bid"])
        ask = float(quote["ask"])
        entry = ask if direction == "BUY" else bid if direction == "SELL" else None
        precision = int((getattr(self.connector, "get_symbol_spec", lambda _: {}) (symbol) or {}).get("digits", 5))
        atr_multiplier = float(
            self.config.get("risk_management", {}).get(
                "gold_atr_sl_multiplier" if "XAU" in symbol else "crypto_atr_sl_multiplier" if "BTC" in symbol else "forex_atr_sl_multiplier",
                1.5,
            )
        )
        structure_buffer = 0.15 * atr
        if direction == "BUY":
            stop = min(recent_low - structure_buffer, entry - atr * atr_multiplier)
        elif direction == "SELL":
            stop = max(recent_high + structure_buffer, entry + atr * atr_multiplier)
        else:
            stop = None
        risk_distance = abs(entry - stop) if entry is not None and stop is not None else None
        targets = (
            {
                "tp1_1_5r": entry + risk_distance * 1.5 * (1 if direction == "BUY" else -1),
                "tp2_2r": entry + risk_distance * 2.0 * (1 if direction == "BUY" else -1),
                "tp3_3r": entry + risk_distance * 3.0 * (1 if direction == "BUY" else -1),
            }
            if direction and risk_distance
            else {"tp1_1_5r": None, "tp2_2r": None, "tp3_3r": None}
        )

        news_blocker = "High-impact economic-calendar clearance is UNVERIFIED"
        order_flow_blocker = "Attributable order-book/trade-flow feed is not attached"
        validation_blocker = "This candidate has no current strategy-validation receipt"
        execution_blockers = [news_blocker, order_flow_blocker, validation_blocker]
        primary_ensemble = indicator_ensembles["M15"]
        ensemble_bias = primary_ensemble.get("directional_bias")
        ensemble_score = abs(float(primary_ensemble.get("ensemble_score", 0.0) or 0.0))
        expected_bias = "BULLISH" if direction == "BUY" else "BEARISH" if direction == "SELL" else None
        if expected_bias and ensemble_bias not in {expected_bias, "NEUTRAL"} and ensemble_score >= 30.0:
            execution_blockers.append(
                f"M15 indicator ensemble materially conflicts with the {direction} candidate"
            )
        if primary_ensemble.get("family_conflict"):
            execution_blockers.append("M15 indicator families conflict; independent confirmation is required")
        if primary_ensemble.get("regime") == "VOLATILITY_SHOCK":
            execution_blockers.append("M15 indicator regime is VOLATILITY_SHOCK")
        if not direction:
            execution_blockers.insert(0, "No sufficiently separated directional edge on closed bars")
        if blockers:
            execution_blockers.extend(blockers)

        suitability = self._account_suitability(symbol, direction, entry, stop, execution_blockers)
        all_blockers = list(dict.fromkeys([*execution_blockers, *suitability["reasons"]]))
        selected = [item for item in evidence if item["side"] == direction] if direction else evidence
        opposing = [item for item in evidence if item["side"] not in {direction, "NEUTRAL"}] if direction else []
        now = self._utc_now()
        expiry = now + timedelta(seconds=60)
        closed_time = self._bar_time(m5)
        signal_seed = {
            "symbol": symbol,
            "bar": closed_time.isoformat() if closed_time else None,
            "direction": direction,
            "entry": self._round(entry, precision),
            "stop": self._round(stop, precision),
        }
        signal_id = hashlib.sha256(json.dumps(signal_seed, sort_keys=True).encode("utf-8")).hexdigest()[:20]

        atr_ratio = (m15["atr14"] / m15["close"]).dropna()
        current_atr_ratio = float(atr_ratio.iloc[-1])
        volatility_percentile = float((atr_ratio.tail(100) <= current_atr_ratio).mean() * 100)
        confidence = "STRONG_EVIDENCE" if winning_score >= 78 else "MODERATE_EVIDENCE" if winning_score >= 64 else "WEAK_OR_CONFLICTED"

        rounded_entry = self._round(entry, precision)
        rounded_stop = self._round(stop, precision)
        result = {
            "status": "research_ready",
            "signal_id": signal_id,
            "symbol": symbol,
            "decision": decision,
            "direction": direction,
            "actionable": False,
            "execution_ready": False,
            "owner_decision_required": bool(direction),
            "data_mode": data_mode,
            "source": "MT5 broker quote + closed OHLCV bars",
            "generated_at": now.isoformat(),
            "expires_at": expiry.isoformat(),
            "latest_closed_bar_at": closed_time.isoformat() if closed_time else None,
            "evidence_score": int(round(winning_score)),
            "buy_score": int(round(buy_score)),
            "sell_score": int(round(sell_score)),
            "confidence_label": confidence,
            "confidence_note": "Evidence score is a transparent heuristic, not a calibrated win probability or profit promise.",
            "quote": {
                "bid": self._round(bid, precision),
                "ask": self._round(ask, precision),
                "mid": self._round((bid + ask) / 2, precision),
                "spread_points": quote.get("spread_points"),
                "spread_pips": quote.get("spread_pips"),
                "observed_at": quote.get("observed_at"),
                "age_seconds": self._round(quote_age, 3),
                "spread_guard": "PASS" if quote.get("is_normal") is True else "BLOCK",
            },
            "plan": {
                "entry_type": "WAIT_FOR_TRIGGER; do not chase market" if direction else "NO_ENTRY",
                "entry_zone": [
                    self._round(entry - atr * 0.12, precision) if entry is not None else None,
                    self._round(entry + atr * 0.12, precision) if entry is not None else None,
                ],
                "trigger": (
                    f"Fresh M5 close {'above' if direction == 'BUY' else 'below'} {self._round(float(m5_last['ema20']), precision)} with normal spread"
                    if direction
                    else "Wait for H1/M15 alignment and a confirming closed M5 candle"
                ),
                "entry_reference": rounded_entry,
                "stop_loss": rounded_stop,
                "invalidation": (
                    f"Closed M15 {'below' if direction == 'BUY' else 'above'} {rounded_stop} or any execution gate failure"
                    if direction
                    else "No directional thesis is active"
                ),
                **{key: self._round(value, precision) for key, value in targets.items()},
                "risk_reward_note": "Targets are geometric R-multiples before slippage, spread, commission, swaps, and gaps.",
            },
            "technical_evidence": selected,
            "opposing_evidence": opposing,
            "indicator_ensemble": {
                "status": "AVAILABLE",
                "actionable": False,
                "primary_timeframe": "M15",
                "decision_use": "CONFLICT_GUARD_AND_EXPLANATION_ONLY",
                "timeframes": indicator_ensembles,
                "warning": (
                    "Indicator transforms share price/volume inputs and are not independent probabilities. "
                    "They can block a conflicting candidate but never authorize an order."
                ),
            },
            "timeframe_state": {tf: {k: self._round(v, precision if k != "rsi14" else 1) if isinstance(v, float) else v for k, v in state.items()} for tf, state in trends.items()},
            "market_mechanics": {
                "recent_liquidity_high": self._round(recent_high, precision),
                "recent_liquidity_low": self._round(recent_low, precision),
                "range_position_pct": round(range_position * 100, 1),
                "bullish_low_sweep_reclaim": bullish_sweep,
                "bearish_high_sweep_rejection": bearish_sweep,
                "signed_tick_volume_proxy_ratio": round(proxy_ratio, 3),
                "proxy_warning": "Candle-direction × tick volume is an activity heuristic, not true aggressor CVD and not named-participant flow.",
                "volatility_percentile_100_bars": round(volatility_percentile, 1),
            },
            "institution_attribution": {
                "status": "UNAVAILABLE",
                "reason": "Broker OHLCV/tick volume cannot identify a bank, fund, whale, or insider. Named claims require an attributable licensed/official source.",
            },
            "news_clearance": {"status": "UNVERIFIED", "reason": news_blocker},
            "order_flow": {"status": "UNAVAILABLE", "reason": order_flow_blocker},
            "account_suitability": suitability,
            "blockers": all_blockers,
            "scenarios": [
                {
                    "name": "BULLISH_BREAKOUT_RETEST",
                    "condition": f"M15 closes above {self._round(recent_high, precision)} and retest holds",
                    "response": "Re-run research; consider only a fresh BUY candidate with normal spread and cleared gates.",
                    "no_trade_if": "Breakout closes back inside range or quote/news clearance is stale.",
                    "probability": None,
                },
                {
                    "name": "BEARISH_BREAKDOWN_RETEST",
                    "condition": f"M15 closes below {self._round(recent_low, precision)} and retest fails",
                    "response": "Re-run research; consider only a fresh SELL candidate with normal spread and cleared gates.",
                    "no_trade_if": "Breakdown reclaims the range or quote/news clearance is stale.",
                    "probability": None,
                },
                {
                    "name": "RANGE_MEAN_REVERSION",
                    "condition": f"Price remains between {self._round(recent_low, precision)} and {self._round(recent_high, precision)}",
                    "response": "WAIT near the middle; only study rejection at an edge after a closed-candle trigger.",
                    "no_trade_if": "Spread expands or high-impact news is not cleared.",
                    "probability": None,
                },
                {
                    "name": "VOLATILITY_SHOCK",
                    "condition": f"M15 range exceeds {self._round(2 * atr, precision)} or spread guard fails",
                    "response": "NO TRADE; let price and spread normalize, then rebuild the signal from closed bars.",
                    "no_trade_if": "Always blocked during the shock condition.",
                    "probability": None,
                },
            ],
            "decision_rule": "Research candidate only. Record owner YES/NO after review; execution still requires every independent gate to pass.",
        }
        self._cache[symbol] = (time.time(), result)
        return result

    def simulate(self, symbol: str = "XAUUSD", shock_pct: float = 0.0) -> Dict[str, Any]:
        analysis = self.analyze(symbol)
        if analysis.get("status") != "research_ready" or not analysis.get("quote", {}).get("mid"):
            return {
                "status": "unavailable",
                "data_mode": "HYPOTHETICAL",
                "actionable": False,
                "probability": None,
                "warning": "A fresh broker baseline is required before simulating a price shock.",
                "blockers": analysis.get("blockers", []),
            }
        shock_pct = max(-20.0, min(20.0, float(shock_pct)))
        baseline = float(analysis["quote"]["mid"])
        hypothetical = baseline * (1 + shock_pct / 100.0)
        high = float(analysis["market_mechanics"]["recent_liquidity_high"])
        low = float(analysis["market_mechanics"]["recent_liquidity_low"])
        if hypothetical > high:
            branch = "ABOVE_RECENT_LIQUIDITY_HIGH"
            response = "Wait for a closed breakout and successful retest, then regenerate research. Do not chase the hypothetical price."
        elif hypothetical < low:
            branch = "BELOW_RECENT_LIQUIDITY_LOW"
            response = "Wait for a closed breakdown and failed retest, then regenerate research. Do not chase the hypothetical price."
        else:
            branch = "INSIDE_RECENT_RANGE"
            response = "No breakout confirmation. Study the range edges; avoid a middle-of-range entry."
        return {
            "status": "scenario_only",
            "title": f"What If: {analysis['symbol']} broker-baselined {shock_pct:+.2f}% shock",
            "symbol": analysis["symbol"],
            "signal_id": analysis["signal_id"],
            "data_mode": "HYPOTHETICAL_FROM_BROKER_BASELINE",
            "actionable": False,
            "baseline_source": analysis["source"],
            "baseline_observed_at": analysis["quote"]["observed_at"],
            "baseline_price": baseline,
            "shock_pct": shock_pct,
            "hypothetical_price": round(hypothetical, 5),
            "branch": branch,
            "response": response,
            "probability": None,
            "estimated_profit": None,
            "warning": "This is sensitivity analysis, not a price forecast, probability, order, or profit estimate.",
        }

    def scan(self, symbols: Iterable[str]) -> Dict[str, Any]:
        """Rank the configured broker universe without turning research into orders."""
        rows: List[Dict[str, Any]] = []
        seen = set()
        for raw_symbol in symbols:
            symbol = str(raw_symbol or "").upper().strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            result = self.analyze(symbol)
            quote = result.get("quote", {})
            account = result.get("account_suitability", {})
            rows.append(
                {
                    "symbol": symbol,
                    "status": result.get("status", "unavailable"),
                    "data_mode": result.get("data_mode", "UNAVAILABLE"),
                    "decision": result.get("decision", "WAIT"),
                    "direction": result.get("direction"),
                    "evidence_score": int(result.get("evidence_score", 0) or 0),
                    "buy_score": int(result.get("buy_score", 0) or 0),
                    "sell_score": int(result.get("sell_score", 0) or 0),
                    "bid": quote.get("bid"),
                    "ask": quote.get("ask"),
                    "quote_age_seconds": quote.get("age_seconds"),
                    "spread_guard": quote.get("spread_guard", "BLOCK"),
                    "account_verdict": account.get("verdict", "DO_NOT_TAKE_NOW"),
                    "execution_ready": False,
                    "primary_blocker": (result.get("blockers") or ["No verified broker research"])[0],
                }
            )
        rows.sort(key=lambda row: (row["status"] == "research_ready", row["evidence_score"]), reverse=True)
        return {
            "status": "research_scan",
            "generated_at": self._utc_now().isoformat(),
            "source": "MT5 broker quote + closed OHLCV bars",
            "actionable": False,
            "execution_ready": False,
            "coverage": {
                "configured": len(rows),
                "research_ready": sum(row["status"] == "research_ready" for row in rows),
                "unavailable": sum(row["status"] != "research_ready" for row in rows),
            },
            "results": rows,
            "warning": "Ranking is a same-source technical heuristic, not a win probability, institution identity, or execution approval.",
        }
