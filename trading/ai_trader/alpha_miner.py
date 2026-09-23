"""
trading/ai_trader/alpha_miner.py — Autonomous Alpha Formula Mining Engine
=============================================================================
Autonomous quantitative formula miner utilizing zero-cost local Ollama
(qwen2.5:0.5b on http://127.0.0.1:11434) with robust deterministic fallback
templates across 5 institutional factor categories (35+ templates).
Features safe AST validation, correlation pruning, and pure Pandas/NumPy execution.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import json
import logging
import math
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from trading.ai_trader.types import FactorEvaluationReport
from trading.ai_trader.formula_parser import FormulaASTParser
from trading.ai_trader.alpha_evaluator import AlphaEvaluator

logger = logging.getLogger("AITraderAlphaMiner")


# 35+ Deterministic Institutional Factor Templates across 5 Categories
DETERMINISTIC_TEMPLATES: List[Dict[str, str]] = [
    # Category 1: Volatility-Normalized Momentum
    {
        "name": "vol_norm_mom_5_10",
        "expression": "Div(Sub(close, Ref(close, 5)), Std(close, 10))",
        "rationale": "5-bar price momentum normalized by 10-bar realized volatility.",
        "category": "Momentum"
    },
    {
        "name": "vol_norm_mom_10_20",
        "expression": "Div(Sub(close, Ref(close, 10)), Std(close, 20))",
        "rationale": "10-bar price momentum normalized by 20-bar realized volatility.",
        "category": "Momentum"
    },
    {
        "name": "vol_norm_mom_20_40",
        "expression": "Div(Sub(close, Ref(close, 20)), Std(close, 40))",
        "rationale": "20-bar price momentum normalized by 40-bar realized volatility.",
        "category": "Momentum"
    },
    {
        "name": "ema_cross_vol_spread",
        "expression": "Div(Sub(EMA(close, 5), EMA(close, 20)), Std(close, 20))",
        "rationale": "Fast vs slow EMA trend divergence scaled by rolling standard deviation.",
        "category": "Momentum"
    },
    {
        "name": "macd_style_momentum",
        "expression": "Div(Sub(EMA(close, 12), EMA(close, 26)), Std(close, 20))",
        "rationale": "Institutional MACD differential normalized by 20-bar volatility.",
        "category": "Momentum"
    },
    {
        "name": "delta_zscore_thrust_5_20",
        "expression": "Mul(Sign(Delta(close, 5)), ZScore(close, 20))",
        "rationale": "Short-term momentum direction confirmed by multi-period z-score.",
        "category": "Momentum"
    },
    {
        "name": "delta_zscore_thrust_10_30",
        "expression": "Mul(Sign(Delta(close, 10)), ZScore(close, 30))",
        "rationale": "Intermediate momentum directional thrust confirmed by 30-bar z-score.",
        "category": "Momentum"
    },

    # Category 2: Mean Reversion & Over-Extension
    {
        "name": "mean_reversion_10",
        "expression": "Neg(Div(Sub(close, Mean(close, 10)), Std(close, 10)))",
        "rationale": "Negative z-score distance from 10-bar mean (overextension snapback).",
        "category": "MeanReversion"
    },
    {
        "name": "mean_reversion_20",
        "expression": "Neg(Div(Sub(close, Mean(close, 20)), Std(close, 20)))",
        "rationale": "Negative z-score distance from 20-bar mean.",
        "category": "MeanReversion"
    },
    {
        "name": "mean_reversion_30",
        "expression": "Neg(Div(Sub(close, Mean(close, 30)), Std(close, 30)))",
        "rationale": "Negative z-score distance from 30-bar mean.",
        "category": "MeanReversion"
    },
    {
        "name": "vwap_mean_reversion_20",
        "expression": "Neg(Div(Sub(close, vwap), Std(close, 20)))",
        "rationale": "Mean reversion pull toward volume-weighted average price (VWAP).",
        "category": "MeanReversion"
    },
    {
        "name": "vwap_mean_reversion_10",
        "expression": "Neg(Div(Sub(close, vwap), Std(close, 10)))",
        "rationale": "Tactical VWAP mean-reversion snapback on 10-bar volatility.",
        "category": "MeanReversion"
    },
    {
        "name": "channel_position_reversion_20",
        "expression": "Sub(0.5, Div(Sub(close, TsMin(low, 20)), Add(Sub(TsMax(high, 20), TsMin(low, 20)), 1e-9)))",
        "rationale": "Inverse 20-bar Donchian channel position (buy lows, sell highs).",
        "category": "MeanReversion"
    },
    {
        "name": "channel_position_reversion_10",
        "expression": "Sub(0.5, Div(Sub(close, TsMin(low, 10)), Add(Sub(TsMax(high, 10), TsMin(low, 10)), 1e-9)))",
        "rationale": "Inverse 10-bar Donchian channel position.",
        "category": "MeanReversion"
    },
    {
        "name": "kmid_vwap_dev_composite",
        "expression": "0.4 * KMID + 0.6 * VWAP_DEV",
        "rationale": "Composite candlestick body momentum and VWAP deviation.",
        "category": "MeanReversion"
    },

    # Category 3: Volatility Asymmetry & Range Expansion
    {
        "name": "vol_range_expansion_10",
        "expression": "Mul(Sign(Sub(close, open)), Div(Sub(high, low), Mean(Sub(high, low), 10)))",
        "rationale": "Directional candle body scaled by relative bar range expansion.",
        "category": "Volatility"
    },
    {
        "name": "vol_range_expansion_20",
        "expression": "Mul(Sign(Sub(close, open)), Div(Sub(high, low), Mean(Sub(high, low), 20)))",
        "rationale": "Directional candle body scaled by 20-bar relative range expansion.",
        "category": "Volatility"
    },
    {
        "name": "intrabar_close_location_value",
        "expression": "Div(Sub(Mul(2.0, close), Add(high, low)), Add(Sub(high, low), 1e-9))",
        "rationale": "Intrabar close position relative to high-low range (CLV).",
        "category": "Volatility"
    },
    {
        "name": "vol_ratio_5_20",
        "expression": "Div(Std(close, 5), Add(Std(close, 20), 1e-9))",
        "rationale": "Short-term volatility expansion relative to 20-bar background volatility.",
        "category": "Volatility"
    },
    {
        "name": "vol_ratio_10_30",
        "expression": "Div(Std(close, 10), Add(Std(close, 30), 1e-9))",
        "rationale": "Intermediate volatility expansion relative to 30-bar background volatility.",
        "category": "Volatility"
    },
    {
        "name": "wick_asymmetry_factor",
        "expression": "Sub(Div(Sub(high, close), Add(Sub(high, low), 1e-9)), Div(Sub(close, low), Add(Sub(high, low), 1e-9)))",
        "rationale": "Upper shadow vs lower shadow asymmetry indicating buyer/seller rejection.",
        "category": "Volatility"
    },
    {
        "name": "candle_body_zscore_combo",
        "expression": "Mul(Div(Sub(close, open), Add(Sub(high, low), 1e-9)), ZScore(close, 20))",
        "rationale": "Candle body fraction scaled by multi-period price z-score.",
        "category": "Volatility"
    },

    # Category 4: Price-Volume Correlation & Flow Dynamics
    {
        "name": "price_vol_corr_10",
        "expression": "Corr(close, volume, 10)",
        "rationale": "10-bar price-volume rolling correlation.",
        "category": "Volume"
    },
    {
        "name": "price_vol_corr_20",
        "expression": "Corr(close, volume, 20)",
        "rationale": "20-bar price-volume rolling correlation.",
        "category": "Volume"
    },
    {
        "name": "corr_diff_5_20",
        "expression": "Sub(Corr(close, volume, 5), Corr(close, volume, 20))",
        "rationale": "Price-volume correlation differential (short vs medium horizon).",
        "category": "Volume"
    },
    {
        "name": "corr_diff_10_30",
        "expression": "Sub(Corr(close, volume, 10), Corr(close, volume, 30))",
        "rationale": "Intermediate price-volume correlation shift.",
        "category": "Volume"
    },
    {
        "name": "vol_scaled_zscore_10",
        "expression": "Mul(Div(Sub(close, Mean(close, 10)), Std(close, 10)), Div(volume, Mean(volume, 10)))",
        "rationale": "Price z-score amplified by volume surge ratio.",
        "category": "Volume"
    },
    {
        "name": "vol_scaled_zscore_20",
        "expression": "Mul(Div(Sub(close, Mean(close, 20)), Std(close, 20)), Div(volume, Mean(volume, 20)))",
        "rationale": "20-bar price z-score amplified by volume surge ratio.",
        "category": "Volume"
    },
    {
        "name": "delta_volume_flow_20",
        "expression": "Mul(Sign(Delta(close, 5)), Div(volume, Mean(volume, 20)))",
        "rationale": "Directional delta flow scaled by 20-bar volume multiple.",
        "category": "Volume"
    },

    # Category 5: Oscillator & Exhaustion Differentials
    {
        "name": "rsi_velocity_5",
        "expression": "Delta(RSI(close, 14), 5)",
        "rationale": "5-bar rate of change in 14-period RSI.",
        "category": "Oscillator"
    },
    {
        "name": "rsi_velocity_3",
        "expression": "Delta(RSI(close, 14), 3)",
        "rationale": "3-bar rate of change in 14-period RSI.",
        "category": "Oscillator"
    },
    {
        "name": "rsi_normalized_center",
        "expression": "Div(Sub(RSI(close, 14), 50.0), 50.0)",
        "rationale": "Centered normalized 14-period RSI (-1.0 to +1.0).",
        "category": "Oscillator"
    },
    {
        "name": "rsi_normalized_center_fast",
        "expression": "Div(Sub(RSI(close, 7), 50.0), 50.0)",
        "rationale": "Centered normalized 7-period fast RSI.",
        "category": "Oscillator"
    },
    {
        "name": "rsi_mean_reversion_fade",
        "expression": "Neg(Div(Sub(RSI(close, 14), 50.0), 50.0))",
        "rationale": "RSI exhaustion mean-reversion fade.",
        "category": "Oscillator"
    },
    {
        "name": "rsi_momentum_thrust",
        "expression": "Mul(Sign(Delta(close, 3)), Div(Sub(RSI(close, 14), 50.0), 50.0))",
        "rationale": "RSI momentum thrust aligned with 3-bar delta sign.",
        "category": "Oscillator"
    },
    {
        "name": "fast_slow_rsi_spread",
        "expression": "Sub(RSI(close, 7), RSI(close, 21))",
        "rationale": "Fast (7) vs Slow (21) RSI spread differential.",
        "category": "Oscillator"
    },
]


class AITraderAlphaMiner:
    """
    Autonomous Quantitative Alpha Formula Miner.
    Zero-paid API: Queries local Ollama instance (qwen2.5:0.5b on :11434).
    Falls back gracefully to 35+ deterministic templates when Ollama is offline.
    """

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:0.5b"):
        self.ollama_url = ollama_url
        self.model = model
        self.evaluator = AlphaEvaluator()
        self._template_idx = 0

    def generate_candidate_formula(self, symbol: str, asset_class: str = "Forex") -> Dict[str, Any]:
        """
        Attempts to generate formula via local Ollama.
        Falls back deterministically if Ollama is unreachable or returns invalid AST.
        """
        # 1. Try Local Ollama Node
        try:
            prompt = (
                f"You are a Quantitative Alpha Researcher. Generate ONE mathematical trading formula for {asset_class} ({symbol}).\n"
                "Operands available: open, high, low, close, volume, vwap.\n"
                "Unary operators: Abs, Sign, Log, Sqrt, Neg.\n"
                "Binary operators: Add, Sub, Mul, Div, Max, Min.\n"
                "Timeseries operators: Ref, Delta, Mean, Std, Sum, TsMax, TsMin, EMA, ZScore, Corr, RSI.\n"
                "Return strictly valid JSON:\n"
                '{"name": "alpha_name", "expression": "Div(Sub(close, Ref(close, 5)), Std(close, 10))", "rationale": "...", "asset_class": "' + asset_class + '", "intended_horizon": "1h"}'
            )

            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "{}")
                parsed = json.loads(response_text)
                expr = parsed.get("expression", "")

                if expr and FormulaASTParser.validate_expression(expr):
                    return {
                        "name": parsed.get("name", "ollama_mined_alpha"),
                        "expression": expr,
                        "rationale": parsed.get("rationale", "Mined by local Ollama qwen2.5:0.5b"),
                        "asset_class": asset_class,
                        "intended_horizon": parsed.get("intended_horizon", "1h"),
                        "source": "OLLAMA"
                    }
        except Exception:
            pass  # Fall through to deterministic fallback bank

        # 2. Deterministic Template Bank Fallback
        tmpl = DETERMINISTIC_TEMPLATES[self._template_idx % len(DETERMINISTIC_TEMPLATES)]
        self._template_idx += 1

        return {
            "name": tmpl["name"],
            "expression": tmpl["expression"],
            "rationale": tmpl["rationale"],
            "asset_class": asset_class,
            "intended_horizon": "1h",
            "source": "DETERMINISTIC_FALLBACK"
        }

    def mine_alphas(self, df: pd.DataFrame, symbol: str, count: int = 10) -> List[FactorEvaluationReport]:
        """
        Mines, parses, evaluates, and filters candidate alpha formulas against market data.
        """
        reports: List[FactorEvaluationReport] = []
        for _ in range(count):
            cand = self.generate_candidate_formula(symbol)
            expr = cand["expression"]
            name = cand["name"]
            try:
                factor_series = FormulaASTParser.evaluate(expr, df)
                report = self.evaluator.evaluate_factor(
                    factor=factor_series,
                    df=df,
                    factor_name=name,
                    expression=expr
                )
                reports.append(report)
            except Exception as e:
                logger.debug(f"Failed to evaluate candidate formula {name}: {e}")

        # Sort by absolute Rank IC descending
        reports.sort(key=lambda r: abs(r.rank_ic_spearman), reverse=True)
        return reports

    @classmethod
    def prune_redundant_alphas(
        cls,
        reports: List[FactorEvaluationReport],
        df: pd.DataFrame,
        threshold: float = 0.65
    ) -> List[FactorEvaluationReport]:
        """
        Applies greedy orthogonal correlation pruning:
        Keeps highest IR factors while pruning any factor with pairwise |Rank Corr| >= threshold.
        """
        if not reports:
            return []

        # Sort reports by Information Ratio descending
        sorted_reports = sorted(reports, key=lambda r: abs(r.information_ratio), reverse=True)
        selected: List[FactorEvaluationReport] = []
        selected_series: List[pd.Series] = []

        for rep in sorted_reports:
            try:
                s = FormulaASTParser.evaluate(rep.expression, df)
            except Exception:
                continue

            # Check correlation against already selected
            is_redundant = False
            for prev_s in selected_series:
                clean = pd.concat([s, prev_s], axis=1).dropna()
                if len(clean) > 5:
                    corr = clean.iloc[:, 0].rank().corr(clean.iloc[:, 1].rank())
                    if math.isfinite(corr) and abs(corr) >= threshold:
                        is_redundant = True
                        break

            if not is_redundant:
                selected.append(rep)
                selected_series.append(s)

        return selected
