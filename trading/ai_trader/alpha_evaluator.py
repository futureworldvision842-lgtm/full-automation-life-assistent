"""
trading/ai_trader/alpha_evaluator.py — Quantitative Alpha Factor Evaluation Engine
=============================================================================
Computes Pearson Information Coefficient (IC), Spearman Rank IC, Information
Ratio (IR), Annualized Strategy Sharpe, Autocorrelation, Turnover, and Quantile
Monotonicity. Built entirely in pure Pandas/NumPy with zero SciPy dependency.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

from trading.ai_trader.types import FactorEvaluationReport


class AlphaEvaluator:
    """
    Evaluates predictive power, statistical significance, and turnover stability
    of quantitative alpha factors.
    """

    def __init__(
        self,
        min_rank_ic: float = 0.03,
        min_ir: float = 0.40,
        min_sharpe: float = 1.0,
        min_autocorr: float = 0.60,
        min_monotonicity: float = 0.70
    ):
        self.min_rank_ic = float(min_rank_ic)
        self.min_ir = float(min_ir)
        self.min_sharpe = float(min_sharpe)
        self.min_autocorr = float(min_autocorr)
        self.min_monotonicity = float(min_monotonicity)

    @staticmethod
    def compute_forward_returns(df: pd.DataFrame, horizons: Optional[List[int]] = None) -> Dict[int, pd.Series]:
        """Calculates future forward returns for given bar horizons."""
        hz_list = horizons or [1, 3, 5, 10]
        close = df["close"]
        fwd_dict = {}
        for h in hz_list:
            fwd = (close.shift(-h) - close) / np.maximum(close, 1e-9)
            fwd_dict[h] = fwd.replace([np.inf, -np.inf], 0.0)
        return fwd_dict

    @staticmethod
    def compute_ic(factor: pd.Series, fwd_ret: pd.Series) -> float:
        """Computes Pearson correlation (Information Coefficient). Pure Pandas/NumPy."""
        clean = pd.concat([factor, fwd_ret], axis=1).dropna()
        if len(clean) < 3:
            return 0.0
        corr = clean.iloc[:, 0].corr(clean.iloc[:, 1], method="pearson")
        return 0.0 if not math.isfinite(corr) else float(corr)

    @staticmethod
    def compute_rank_ic(factor: pd.Series, fwd_ret: pd.Series) -> float:
        """
        Computes Spearman Rank Information Coefficient.
        Implemented strictly as Pearson correlation of ranks (pure Pandas/NumPy, zero SciPy).
        """
        clean = pd.concat([factor, fwd_ret], axis=1).dropna()
        if len(clean) < 3:
            return 0.0
        rank_ic = clean.iloc[:, 0].rank().corr(clean.iloc[:, 1].rank())
        return 0.0 if not math.isfinite(rank_ic) else float(rank_ic)

    @classmethod
    def compute_ir(cls, factor: pd.Series, df: pd.DataFrame, horizon: int = 5, sub_window: int = 20) -> float:
        """
        Computes Information Ratio: mean(IC) / std(IC) over rolling sub-windows.
        """
        fwd_dict = cls.compute_forward_returns(df, horizons=[horizon])
        fwd = fwd_dict[horizon]
        clean = pd.concat([factor, fwd], axis=1).dropna()
        if len(clean) < sub_window:
            ic = cls.compute_rank_ic(factor, fwd)
            return abs(ic)

        ics = []
        n_chunks = len(clean) // sub_window
        for i in range(n_chunks):
            chunk = clean.iloc[i * sub_window: (i + 1) * sub_window]
            sub_ic = chunk.iloc[:, 0].rank().corr(chunk.iloc[:, 1].rank())
            if math.isfinite(sub_ic):
                ics.append(sub_ic)

        if not ics:
            return 0.0
        mean_ic = np.mean(ics)
        std_ic = np.std(ics, ddof=1) if len(ics) > 1 else 0.0
        if std_ic < 1e-9:
            return float(mean_ic)
        ir = float(mean_ic / std_ic)
        return ir if math.isfinite(ir) else 0.0

    @staticmethod
    def compute_sharpe(factor: pd.Series, fwd_ret: pd.Series, periods_per_year: int = 252) -> float:
        """Computes annualized strategy Sharpe ratio from rank-weighted simulated positions."""
        clean = pd.concat([factor, fwd_ret], axis=1).dropna()
        if len(clean) < 3:
            return 0.0
        f_vals = clean.iloc[:, 0]
        r_vals = clean.iloc[:, 1]

        f_mean = f_vals.mean()
        f_std = f_vals.std() + 1e-9
        w = np.clip((f_vals - f_mean) / f_std, -1.0, 1.0)
        strat_returns = w * r_vals

        mean_r = strat_returns.mean()
        std_r = strat_returns.std() + 1e-9
        sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)
        return float(sharpe) if math.isfinite(sharpe) else 0.0

    @staticmethod
    def compute_turnover_and_autocorr(factor: pd.Series) -> Tuple[float, float]:
        """Computes factor turnover and 1-bar autocorrelation."""
        s = factor.dropna()
        if len(s) < 3:
            return 0.0, 1.0
        autocorr = s.corr(s.shift(1))
        if not math.isfinite(autocorr):
            autocorr = 0.0

        s_mean = s.mean()
        s_std = s.std() + 1e-9
        w = np.clip((s - s_mean) / s_std, -1.0, 1.0)
        turnover = float(w.diff().abs().mean())
        if not math.isfinite(turnover):
            turnover = 0.0

        return turnover, float(autocorr)

    @staticmethod
    def compute_monotonicity(factor: pd.Series, fwd_ret: pd.Series, bins: int = 5) -> float:
        """
        Computes Quantile Monotonicity Score via rank correlation of group means.
        """
        clean = pd.concat([factor, fwd_ret], axis=1).dropna()
        clean.columns = ["factor", "fwd_ret"]
        if len(clean) < bins * 2:
            return 0.0

        try:
            clean["bin"] = pd.qcut(clean["factor"], q=bins, labels=False, duplicates="drop")
            group_means = clean.groupby("bin")["fwd_ret"].mean()
            if len(group_means) < 2:
                return 0.0
            x = pd.Series(range(len(group_means)))
            y = pd.Series(group_means.values)
            m = float(x.rank().corr(y.rank()))
            return m if math.isfinite(m) else 0.0
        except Exception:
            return 0.0

    def evaluate_factor(
        self,
        factor: pd.Series,
        df: pd.DataFrame,
        factor_name: str = "custom_alpha",
        expression: str = ""
    ) -> FactorEvaluationReport:
        """
        Comprehensive factor evaluation pipeline applying institutional gating thresholds.
        """
        fwd_dict = self.compute_forward_returns(df, horizons=[1, 5])
        fwd_1 = fwd_dict[1]
        fwd_5 = fwd_dict[5]

        ic_pearson = self.compute_ic(factor, fwd_5)
        rank_ic = self.compute_rank_ic(factor, fwd_5)
        ir = self.compute_ir(factor, df, horizon=5)
        sharpe = self.compute_sharpe(factor, fwd_1)
        turnover, autocorr = self.compute_turnover_and_autocorr(factor)
        monotonicity = self.compute_monotonicity(factor, fwd_5)

        rejections = []
        if abs(rank_ic) < self.min_rank_ic:
            rejections.append(f"Rank IC {abs(rank_ic):.4f} below threshold {self.min_rank_ic:.4f}")
        if abs(ir) < self.min_ir:
            rejections.append(f"Information Ratio {abs(ir):.2f} below threshold {self.min_ir:.2f}")
        if sharpe < self.min_sharpe:
            rejections.append(f"Sharpe {sharpe:.2f} below threshold {self.min_sharpe:.2f}")
        if autocorr < self.min_autocorr:
            rejections.append(f"Autocorrelation {autocorr:.2f} below threshold {self.min_autocorr:.2f}")
        if abs(monotonicity) < self.min_monotonicity:
            rejections.append(f"Quantile Monotonicity {abs(monotonicity):.2f} below threshold {self.min_monotonicity:.2f}")

        passed = len(rejections) == 0

        return FactorEvaluationReport(
            factor_name=factor_name,
            expression=expression,
            ic_pearson=round(ic_pearson, 4),
            rank_ic_spearman=round(rank_ic, 4),
            information_ratio=round(ir, 4),
            sharpe_ratio=round(sharpe, 4),
            autocorrelation=round(autocorr, 4),
            turnover=round(turnover, 4),
            monotonicity=round(monotonicity, 4),
            passed=passed,
            rejection_reasons=rejections
        )
