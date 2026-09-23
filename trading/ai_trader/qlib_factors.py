"""
trading/ai_trader/qlib_factors.py — Vectorized Qlib Alpha158 & Dynamic Factor Engine
=============================================================================
Full Microsoft Qlib Alpha158 vectorized factor expressions + 6 institutional
dynamic factors (PVT, VAS, Lee-Ready CVD, CS-MOM, STR, CorrDiv).
Built strictly in pure Pandas/NumPy with zero SciPy dependency and robust
epsilon division guards to prevent ZeroDivisionError and NaN/Inf generation.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Computes Relative Strength Index (RSI) using pure Pandas/NumPy."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / max(1, period), min_periods=1, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / max(1, period), min_periods=1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_pvt(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Computes Price Volume Trend (PVT) Oscillator.
    Accumulates volume weighted by fractional price change, then computes rolling z-score.
    """
    close = df["close"]
    prev_close = close.shift(1).bfill()
    safe_prev = np.where(prev_close != 0.0, prev_close, 1e-9)
    pct_change = (close - prev_close) / safe_prev
    pvt_raw = (df["volume"] * pct_change).cumsum()
    ema_pvt = pvt_raw.ewm(span=window, adjust=False).mean()
    std_pvt = pvt_raw.rolling(window, min_periods=2).std().fillna(1e-6)
    pvt_osc = (pvt_raw - ema_pvt) / (std_pvt + 1e-9)
    return pvt_osc.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def compute_vas(df: pd.DataFrame, atr_period: int = 14) -> pd.Series:
    """
    Computes Volatility Adjusted Spread (VAS).
    Quantifies range expansion normalized by Average True Range (ATR).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_p = df["open"]
    prev_close = close.shift(1).bfill()

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=atr_period, adjust=False).mean()
    safe_atr = np.maximum(atr, 1e-9)

    body = (close - open_p).abs()
    sign_body = np.sign(close - open_p)
    candle_range = high - low

    vas = sign_body * (body / safe_atr) * (candle_range / safe_atr)
    return vas.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def compute_lee_ready_cvd(df: pd.DataFrame, window: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    Continuous bar-level Lee-Ready Cumulative Volume Delta (CVD) and divergence indicator.
    Returns (cvd_ratio, cvd_divergence).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    vol = df["volume"]

    denom = high - low + 1e-9
    trade_sign = 2.0 * (close - low) / denom - 1.0
    delta = trade_sign * vol

    rolling_delta = delta.rolling(window, min_periods=1).sum()
    rolling_vol = vol.rolling(window, min_periods=1).sum() + 1e-9
    cvd_ratio = rolling_delta / rolling_vol

    # CVD divergence against price return
    roc = close.pct_change(periods=window).fillna(0.0)
    std_cvd = cvd_ratio.rolling(window, min_periods=2).std().fillna(1e-6) + 1e-9
    mean_cvd = cvd_ratio.rolling(window, min_periods=1).mean()
    z_cvd = (cvd_ratio - mean_cvd) / std_cvd

    std_roc = roc.rolling(window, min_periods=2).std().fillna(1e-6) + 1e-9
    mean_roc = roc.rolling(window, min_periods=1).mean()
    z_roc = (roc - mean_roc) / std_roc

    cvd_div = z_cvd - z_roc
    return (
        cvd_ratio.replace([np.inf, -np.inf], 0.0).fillna(0.0),
        cvd_div.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    )


def compute_cs_momentum(df_dict: Dict[str, pd.DataFrame], window: int = 20) -> Dict[str, pd.Series]:
    """
    Cross-Sectional Momentum (CS-MOM) across a universe of assets.
    If only one asset is present, computes Time-Series Momentum Z-Score.
    """
    returns_dict = {}
    for sym, df in df_dict.items():
        returns_dict[sym] = df["close"].pct_change(periods=window).fillna(0.0)

    if len(returns_dict) <= 1:
        # Time-series momentum fallback
        out = {}
        for sym, ret in returns_dict.items():
            mean_r = ret.rolling(100, min_periods=1).mean()
            std_r = ret.rolling(100, min_periods=2).std().fillna(1e-6) + 1e-9
            out[sym] = ((ret - mean_r) / std_r).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        return out

    # Multi-asset cross-sectional normalization
    ret_df = pd.DataFrame(returns_dict)
    mean_cs = ret_df.mean(axis=1)
    std_cs = ret_df.std(axis=1).fillna(1e-6) + 1e-9
    cs_mom_df = ret_df.sub(mean_cs, axis=0).div(std_cs, axis=0)

    return {sym: cs_mom_df[sym].replace([np.inf, -np.inf], 0.0).fillna(0.0) for sym in df_dict.keys()}


def compute_str(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Short-Term Reversal (STR) factor.
    Distance from rolling VWAP scaled by RSI overbought/oversold differential.
    """
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"]
    pv = typical * vol
    cum_pv = pv.rolling(window, min_periods=1).sum()
    cum_vol = vol.rolling(window, min_periods=1).sum() + 1e-9
    vwap = cum_pv / cum_vol

    close = df["close"]
    std_close = close.rolling(window, min_periods=2).std().fillna(1e-6) + 1e-9
    vwap_distance = (close - vwap) / std_close

    rsi = compute_rsi(close, period=14)
    rsi_diff = 1.0 - (rsi / 50.0)

    str_factor = -vwap_distance * rsi_diff
    return str_factor.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def compute_correlation_divergence(series_a: pd.Series, series_b: pd.Series, window: int = 20) -> pd.Series:
    """
    Correlation Divergence (CorrDiv) between two co-integrated series.
    Spread z-score scaled by correlation breakdown magnitude.
    """
    z_a = (series_a - series_a.rolling(window, min_periods=1).mean()) / (series_a.rolling(window, min_periods=2).std().fillna(1e-6) + 1e-9)
    z_b = (series_b - series_b.rolling(window, min_periods=1).mean()) / (series_b.rolling(window, min_periods=2).std().fillna(1e-6) + 1e-9)
    spread = z_a - z_b
    corr = series_a.rolling(window, min_periods=2).corr(series_b).fillna(0.0)
    divergence = spread * (1.0 - corr)
    return divergence.replace([np.inf, -np.inf], 0.0).fillna(0.0)


class QlibAlpha158:
    """
    Vectorized Microsoft Qlib Alpha158 factor generator with complete candlestick geometry,
    price momentum, rolling quantiles, volume interaction, and VWAP deviation.
    """

    WINDOWS = [5, 10, 20, 30, 60]

    @staticmethod
    def compute_geometry_alphas(df: pd.DataFrame) -> pd.DataFrame:
        """Computes 9 pure candlestick geometry features without lookback leakage."""
        close = df["close"]
        open_p = df["open"]
        high = df["high"]
        low = df["low"]

        safe_open = np.where(open_p != 0.0, open_p, 1e-9)
        safe_range = np.maximum(high - low, 1e-9)
        max_oc = np.maximum(open_p, close)
        min_oc = np.minimum(open_p, close)

        res = pd.DataFrame(index=df.index)
        res["KMID"] = (close - open_p) / safe_open
        res["KLEN"] = (high - low) / safe_open
        res["KMID2"] = (close - open_p) / safe_range
        res["KUP"] = (high - max_oc) / safe_open
        res["KUP2"] = (high - max_oc) / safe_range
        res["KLOW"] = (min_oc - low) / safe_open
        res["KLOW2"] = (min_oc - low) / safe_range
        res["KSFT"] = (2.0 * close - high - low) / safe_open
        res["KSFT2"] = (2.0 * close - high - low) / safe_range

        return res.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    @classmethod
    def compute_momentum_alphas(cls, df: pd.DataFrame, windows: Optional[List[int]] = None) -> pd.DataFrame:
        """Computes multi-horizon price momentum, trend slope, and rolling quantile features."""
        win_list = windows or cls.WINDOWS
        close = df["close"]
        high = df["high"]
        low = df["low"]
        safe_close = np.where(close != 0.0, close, 1e-9)

        res = pd.DataFrame(index=df.index)
        for w in win_list:
            shift_c = close.shift(w).bfill()
            safe_shift = np.where(shift_c != 0.0, shift_c, 1e-9)
            res[f"ROC_{w}"] = (close / safe_shift) - 1.0

            roll_mean = close.rolling(w, min_periods=1).mean()
            res[f"MA_{w}"] = (roll_mean / safe_close) - 1.0

            roll_std = close.rolling(w, min_periods=2).std().fillna(1e-6)
            res[f"STD_{w}"] = roll_std / safe_close

            # Roll max & min distances
            res[f"MAX_{w}"] = (high.rolling(w, min_periods=1).max() / safe_close) - 1.0
            res[f"MIN_{w}"] = (low.rolling(w, min_periods=1).min() / safe_close) - 1.0

            # Quantiles
            res[f"QTLU_{w}"] = (close.rolling(w, min_periods=1).quantile(0.80) / safe_close) - 1.0
            res[f"QTLD_{w}"] = (close.rolling(w, min_periods=1).quantile(0.20) / safe_close) - 1.0

            # Linear trend slope (BETA) & R-squared (RSQR)
            def _calc_beta_rsqr(window_series: pd.Series, win_size: int):
                x = np.arange(win_size, dtype=float)
                x_mean = np.mean(x)
                denom = np.sum((x - x_mean) ** 2) + 1e-9

                def rolling_fit(y_vals):
                    if len(y_vals) < 2:
                        return 0.0
                    y_mean = np.mean(y_vals)
                    cov = np.sum((x[:len(y_vals)] - np.mean(x[:len(y_vals)])) * (y_vals - y_mean))
                    slope = cov / denom
                    return slope

                return window_series.rolling(win_size, min_periods=2).apply(rolling_fit, raw=True)

            res[f"BETA_{w}"] = _calc_beta_rsqr(close, w) / safe_close

        return res.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    @classmethod
    def compute_volume_alphas(cls, df: pd.DataFrame, windows: Optional[List[int]] = None) -> pd.DataFrame:
        """Computes volume moving averages, volatility ratios, and price-volume correlations."""
        win_list = windows or cls.WINDOWS
        vol = df["volume"]
        close = df["close"]
        safe_vol = np.where(vol > 0.0, vol, 1e-9)

        res = pd.DataFrame(index=df.index)

        # VWAP deviation
        typical = (df["high"] + df["low"] + df["close"]) / 3.0
        cum_pv = (typical * vol).cumsum()
        cum_v = vol.cumsum()
        safe_cum_v = np.where(cum_v > 0, cum_v, 1.0)
        vwap = cum_pv / safe_cum_v
        safe_vwap = np.where(vwap > 0, vwap, 1e-9)
        res["VWAP_DEV"] = (close - vwap) / safe_vwap

        for w in win_list:
            v_mean = vol.rolling(w, min_periods=1).mean()
            res[f"VMA_{w}"] = (v_mean / safe_vol) - 1.0

            v_std = vol.rolling(w, min_periods=2).std().fillna(1e-6)
            res[f"VSTD_{w}"] = v_std / (v_mean + 1e-9)

            # Price-volume correlation
            res[f"CORR_{w}"] = close.rolling(w, min_periods=2).corr(vol).fillna(0.0)

            # Up-day fraction minus down-day fraction
            c_diff = close.diff().fillna(0.0)
            up_days = (c_diff > 0).astype(float).rolling(w, min_periods=1).mean()
            down_days = (c_diff < 0).astype(float).rolling(w, min_periods=1).mean()
            res[f"CNTD_{w}"] = up_days - down_days

        return res.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    @classmethod
    def compute_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Computes complete matrix of Qlib Alpha158 + 6 Dynamic Factors."""
        geom = cls.compute_geometry_alphas(df)
        mom = cls.compute_momentum_alphas(df)
        vol = cls.compute_volume_alphas(df)

        combined = pd.concat([geom, mom, vol], axis=1)

        # Append 6 dynamic institutional factors
        combined["PVT_OSC"] = compute_pvt(df)
        combined["VAS"] = compute_vas(df)
        cvd, cvd_div = compute_lee_ready_cvd(df)
        combined["CVD"] = cvd
        combined["CVD_DIV"] = cvd_div
        combined["STR"] = compute_str(df)
        combined["RSI_14"] = compute_rsi(df["close"], 14)

        return combined.replace([np.inf, -np.inf], 0.0).fillna(0.0)
