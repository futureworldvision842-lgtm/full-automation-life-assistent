"""Explainable closed-bar indicator ensemble.

The goal is not to collect every technical indicator.  Many popular indicators
are transformations of the same price series and counting them independently
creates false confidence.  This module groups a deliberately small, auditable
set into four families (trend, momentum, structure, activity), detects the
current volatility/regime state, and reports disagreement explicitly.

It never reads a forming candle, never generates an order, never returns a win
probability, and never claims that tick volume identifies a participant.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd


class ExplainableIndicatorEnsemble:
    """Compute bounded indicator-family diagnostics from broker closed OHLCV."""

    MINIMUM_BARS = 220
    CATALOG = (
        "EMA20/50/200",
        "MACD(12,26,9)",
        "ADX/DMI(14)",
        "RSI(14)",
        "Stochastic(14,3)",
        "ROC(10)",
        "ATR(14)",
        "Bollinger(20,2)",
        "Donchian(20)",
        "Kaufman efficiency ratio(10)",
        "tick-volume z-score/activity proxy",
    )

    @staticmethod
    def _clip(value: float, lower: float = -100.0, upper: float = 100.0) -> float:
        if not math.isfinite(float(value)):
            return 0.0
        return float(max(lower, min(upper, value)))

    @staticmethod
    def _number(value: Any, digits: int = 4) -> Any:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return round(number, digits) if math.isfinite(number) else None

    @staticmethod
    def _state(score: float) -> str:
        if score >= 25:
            return "BULLISH"
        if score <= -25:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _observed_at(frame: pd.DataFrame) -> Any:
        if "time" not in frame.columns or frame.empty:
            return None
        try:
            return pd.to_datetime(frame.iloc[-1]["time"], utc=True).isoformat()
        except Exception:
            return None

    @classmethod
    def feature_frame(cls, frame: pd.DataFrame) -> pd.DataFrame:
        """Return causal features; every row uses only that row and its past."""
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("indicator input must be a pandas DataFrame")
        missing = {"open", "high", "low", "close"} - set(frame.columns)
        if missing:
            raise ValueError(f"indicator input is missing columns: {sorted(missing)}")

        df = frame.copy()
        for column in ("open", "high", "low", "close"):
            df[column] = pd.to_numeric(df[column], errors="coerce")
        volume_source = df["tick_volume"] if "tick_volume" in df.columns else df.get("real_volume", 0)
        df["tick_volume"] = pd.to_numeric(volume_source, errors="coerce").fillna(0.0)
        df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

        close = df["close"]
        high = df["high"]
        low = df["low"]
        previous_close = close.shift(1)

        for span in (20, 50, 200):
            df[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()

        true_range = pd.concat(
            [(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1
        ).max(axis=1)
        df["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        df["atr_pct"] = 100.0 * df["atr14"] / close.replace(0, np.nan)

        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        relative_strength = gain / loss.replace(0, np.nan)
        rsi = 100.0 - 100.0 / (1.0 + relative_strength)
        rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
        rsi = rsi.mask((gain == 0) & (loss > 0), 0.0)
        df["rsi14"] = rsi.mask((gain == 0) & (loss == 0), 50.0).fillna(50.0)

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
        smoothed_tr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().replace(0, np.nan)
        df["plus_di14"] = 100.0 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr
        df["minus_di14"] = 100.0 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr
        di_sum = (df["plus_di14"] + df["minus_di14"]).replace(0, np.nan)
        dx = 100.0 * (df["plus_di14"] - df["minus_di14"]).abs() / di_sum
        df["adx14"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

        bb_mid = close.rolling(20, min_periods=20).mean()
        bb_std = close.rolling(20, min_periods=20).std(ddof=0)
        df["bb_mid"] = bb_mid
        df["bb_upper"] = bb_mid + 2.0 * bb_std
        df["bb_lower"] = bb_mid - 2.0 * bb_std
        bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
        df["bb_width_pct"] = 100.0 * bb_range / bb_mid.replace(0, np.nan)
        df["bb_percent_b"] = (close - df["bb_lower"]) / bb_range

        rolling_low = low.rolling(14, min_periods=14).min()
        rolling_high = high.rolling(14, min_periods=14).max()
        stochastic_range = (rolling_high - rolling_low).replace(0, np.nan)
        df["stoch_k"] = 100.0 * (close - rolling_low) / stochastic_range
        df["stoch_d"] = df["stoch_k"].rolling(3, min_periods=3).mean()
        df["roc10_pct"] = close.pct_change(10) * 100.0

        df["donchian_high20"] = high.rolling(20, min_periods=20).max().shift(1)
        df["donchian_low20"] = low.rolling(20, min_periods=20).min().shift(1)
        donchian_range = (df["donchian_high20"] - df["donchian_low20"]).replace(0, np.nan)
        df["donchian_position"] = (close - df["donchian_low20"]) / donchian_range

        absolute_change = (close - close.shift(10)).abs()
        path_length = close.diff().abs().rolling(10, min_periods=10).sum().replace(0, np.nan)
        df["efficiency_ratio10"] = absolute_change / path_length

        volume_mean = df["tick_volume"].rolling(20, min_periods=20).mean()
        volume_std = df["tick_volume"].rolling(20, min_periods=20).std(ddof=0).replace(0, np.nan)
        df["volume_z20"] = (df["tick_volume"] - volume_mean) / volume_std
        signed_activity = np.sign(close - df["open"]) * df["tick_volume"]
        df["signed_activity20"] = (
            signed_activity.rolling(20, min_periods=20).sum()
            / df["tick_volume"].rolling(20, min_periods=20).sum().replace(0, np.nan)
        )
        df["realized_vol20_pct"] = close.pct_change().rolling(20, min_periods=20).std(ddof=0) * 100.0
        return df

    def analyze(self, frame: pd.DataFrame, timeframe: str = "M15") -> Dict[str, Any]:
        features = self.feature_frame(frame)
        if len(features) < self.MINIMUM_BARS:
            return {
                "status": "UNAVAILABLE",
                "data_mode": "BROKER_DERIVED_CLOSED_OHLCV",
                "actionable": False,
                "timeframe": timeframe,
                "reason": f"At least {self.MINIMUM_BARS} closed broker bars are required",
                "catalog": list(self.CATALOG),
            }

        last = features.iloc[-1]
        close = float(last["close"])
        atr = float(last["atr14"]) if pd.notna(last["atr14"]) else 0.0
        atr_safe = max(atr, abs(close) * 1e-9)

        ema_alignment = 100.0 if last["ema20"] > last["ema50"] > last["ema200"] else -100.0 if last["ema20"] < last["ema50"] < last["ema200"] else 0.0
        macd_component = self._clip(float(last["macd_hist"]) / atr_safe * 180.0)
        di_component = self._clip(float(last["plus_di14"] - last["minus_di14"]) * 2.0)
        trend_score = self._clip(0.50 * ema_alignment + 0.25 * macd_component + 0.25 * di_component)
        adx = float(last["adx14"]) if pd.notna(last["adx14"]) else 0.0
        if adx < 18.0:
            trend_score *= 0.55

        rsi_component = self._clip((float(last["rsi14"]) - 50.0) * 2.0)
        stochastic_component = self._clip(((float(last["stoch_k"]) if pd.notna(last["stoch_k"]) else 50.0) - 50.0) * 2.0)
        atr_pct = float(last["atr_pct"]) if pd.notna(last["atr_pct"]) and last["atr_pct"] > 0 else 0.01
        roc_component = self._clip(float(last["roc10_pct"]) / atr_pct * 18.0) if pd.notna(last["roc10_pct"]) else 0.0
        momentum_score = self._clip((rsi_component + stochastic_component + roc_component) / 3.0)

        donchian_position = float(last["donchian_position"]) if pd.notna(last["donchian_position"]) else 0.5
        range_component = self._clip((donchian_position - 0.5) * 160.0)
        breakout_component = 100.0 if close > float(last["donchian_high20"]) else -100.0 if close < float(last["donchian_low20"]) else 0.0
        candle_component = self._clip((close - float(last["open"])) / atr_safe * 70.0)
        structure_score = self._clip(0.45 * range_component + 0.35 * breakout_component + 0.20 * candle_component)

        signed_activity = float(last["signed_activity20"]) if pd.notna(last["signed_activity20"]) else 0.0
        volume_z = float(last["volume_z20"]) if pd.notna(last["volume_z20"]) else 0.0
        volume_direction = 1.0 if close > float(last["open"]) else -1.0 if close < float(last["open"]) else 0.0
        activity_score = self._clip(75.0 * signed_activity + 12.5 * self._clip(volume_z, -2.0, 2.0) * volume_direction)

        family_scores = {
            "trend": trend_score,
            "momentum": momentum_score,
            "structure": structure_score,
            "activity": activity_score,
        }
        weights = {"trend": 0.35, "momentum": 0.25, "structure": 0.25, "activity": 0.15}
        ensemble_score = self._clip(sum(family_scores[name] * weights[name] for name in weights))
        states = {name: self._state(score) for name, score in family_scores.items()}
        bullish_families = sum(state == "BULLISH" for state in states.values())
        bearish_families = sum(state == "BEARISH" for state in states.values())
        conflict = bullish_families > 0 and bearish_families > 0

        atr_median = features["atr_pct"].tail(100).median()
        bb_median = features["bb_width_pct"].tail(100).median()
        atr_ratio = float(last["atr_pct"] / atr_median) if pd.notna(atr_median) and atr_median > 0 else 1.0
        bb_ratio = float(last["bb_width_pct"] / bb_median) if pd.notna(bb_median) and bb_median > 0 else 1.0
        efficiency = float(last["efficiency_ratio10"]) if pd.notna(last["efficiency_ratio10"]) else 0.0
        if atr_ratio >= 1.65 or bb_ratio >= 1.80:
            regime = "VOLATILITY_SHOCK"
        elif adx >= 25.0 and efficiency >= 0.28:
            regime = "TRENDING_HIGH_VOL" if atr_ratio >= 1.25 else "TRENDING_NORMAL"
        elif adx < 20.0 and efficiency < 0.30:
            regime = "RANGE_LOW_VOL" if atr_ratio < 0.80 else "RANGE_NORMAL"
        else:
            regime = "TRANSITION_MIXED"

        directional_bias = self._state(ensemble_score)
        agreement = max(bullish_families, bearish_families)
        evidence_quality = "BROAD_AGREEMENT" if agreement >= 3 and not conflict else "CONFLICTED" if conflict else "LIMITED_AGREEMENT"
        return {
            "status": "AVAILABLE",
            "data_mode": "BROKER_DERIVED_CLOSED_OHLCV",
            "source": "Attached MT5 broker closed OHLCV/tick-volume bars",
            "observed_at": self._observed_at(features),
            "actionable": False,
            "timeframe": timeframe,
            "bars_used": len(features),
            "forming_bar_used": False,
            "directional_bias": directional_bias,
            "ensemble_score": round(ensemble_score, 1),
            "evidence_quality": evidence_quality,
            "family_conflict": conflict,
            "bullish_families": bullish_families,
            "bearish_families": bearish_families,
            "regime": regime,
            "regime_metrics": {
                "adx14": self._number(adx, 2),
                "efficiency_ratio10": self._number(efficiency, 3),
                "atr_ratio_to_100bar_median": self._number(atr_ratio, 3),
                "bollinger_width_ratio_to_100bar_median": self._number(bb_ratio, 3),
            },
            "families": {
                "trend": {
                    "score": round(trend_score, 1), "state": states["trend"],
                    "reason": "EMA alignment + MACD histogram + DMI direction, damped when ADX is weak",
                },
                "momentum": {
                    "score": round(momentum_score, 1), "state": states["momentum"],
                    "reason": "RSI + Stochastic + ATR-normalized 10-bar rate of change",
                },
                "structure": {
                    "score": round(structure_score, 1), "state": states["structure"],
                    "reason": "Prior Donchian range position/breakout + current closed-candle body",
                },
                "activity": {
                    "score": round(activity_score, 1), "state": states["activity"],
                    "reason": "Candle-signed tick-volume activity + volume z-score; not true aggressor CVD",
                },
            },
            "indicators": {
                "close": self._number(close, 6),
                "ema20": self._number(last["ema20"], 6),
                "ema50": self._number(last["ema50"], 6),
                "ema200": self._number(last["ema200"], 6),
                "macd": self._number(last["macd"], 6),
                "macd_signal": self._number(last["macd_signal"], 6),
                "macd_histogram": self._number(last["macd_hist"], 6),
                "adx14": self._number(adx, 2),
                "plus_di14": self._number(last["plus_di14"], 2),
                "minus_di14": self._number(last["minus_di14"], 2),
                "rsi14": self._number(last["rsi14"], 2),
                "stochastic_k": self._number(last["stoch_k"], 2),
                "stochastic_d": self._number(last["stoch_d"], 2),
                "roc10_pct": self._number(last["roc10_pct"], 3),
                "atr14": self._number(last["atr14"], 6),
                "atr_pct": self._number(last["atr_pct"], 3),
                "bollinger_percent_b": self._number(last["bb_percent_b"], 3),
                "bollinger_width_pct": self._number(last["bb_width_pct"], 3),
                "donchian_high20": self._number(last["donchian_high20"], 6),
                "donchian_low20": self._number(last["donchian_low20"], 6),
                "efficiency_ratio10": self._number(efficiency, 3),
                "volume_z20": self._number(volume_z, 3),
                "signed_tick_activity20": self._number(signed_activity, 3),
                "realized_vol20_pct": self._number(last["realized_vol20_pct"], 4),
            },
            "catalog": list(self.CATALOG),
            "decision_use": "CONFLICT_GUARD_AND_EXPLANATION_ONLY",
            "warning": "Indicator families are heuristics, not independent probabilities. They require walk-forward validation and never authorize an order.",
        }
