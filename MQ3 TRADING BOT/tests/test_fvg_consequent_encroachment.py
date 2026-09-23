"""
tests/test_fvg_consequent_encroachment.py
Tests for Feature 10: Fair Value Gap 50% Consequent Encroachment (CE 50%) & Multi-Candle Mitigation Lifecycle.
"""

import pandas as pd
import numpy as np
import pytest
from src.market_analyzer import MarketAnalyzer


class TestFVGConsequentEncroachmentSuite:

    def test_bullish_fvg_ce_calculation(self):
        # 3-candle BISI Bullish FVG: C1 High=2000.0, C2 Green, C3 Low=2010.0
        # CE 50% should be (2010.0 + 2000.0) / 2.0 = 2005.0
        df = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=3, freq="15min"),
            "open":  [1995.0, 2001.0, 2012.0],
            "high":  [2000.0, 2015.0, 2018.0],
            "low":   [1990.0, 2000.5, 2010.0],
            "close": [1998.0, 2014.0, 2016.0]
        })
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=1.0, symbol="XAUUSD")
        assert len(fvgs) == 1
        fvg = fvgs[0]
        assert fvg["type"] == "BULLISH_FVG"
        assert fvg["top"] == 2010.0
        assert fvg["bottom"] == 2000.0
        assert fvg["ce"] == 2005.0
        assert fvg["ce_50"] == 2005.0

    def test_bearish_fvg_ce_calculation(self):
        # 3-candle SIBI Bearish FVG: C1 Low=2010.0, C2 Red, C3 High=2000.0
        # CE 50% should be (2010.0 + 2000.0) / 2.0 = 2005.0
        df = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=3, freq="15min"),
            "open":  [2015.0, 2009.0, 1998.0],
            "high":  [2020.0, 2009.5, 2000.0],
            "low":   [2010.0, 1995.0, 1992.0],
            "close": [2012.0, 1996.0, 1994.0]
        })
        fvgs = MarketAnalyzer.detect_fvg(df, min_gap_pips=1.0, symbol="XAUUSD")
        assert len(fvgs) == 1
        fvg = fvgs[0]
        assert fvg["type"] == "BEARISH_FVG"
        assert fvg["top"] == 2010.0
        assert fvg["bottom"] == 2000.0
        assert fvg["ce_50"] == 2005.0

    def test_fvg_mitigation_lifecycle_states(self):
        # Bullish FVG formed at i=2 (gap: bottom=100.0, top=104.0, CE=102.0)
        # Bar 3: Low=105.0 -> Unmitigated
        # Bar 4: Low=103.0 -> Partially Mitigated (enters gap, stays above CE)
        # Bar 5: Low=101.5 -> Fully Mitigated / Rebalanced (touches/pierces CE 50%)
        df_unmit = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=4, freq="15min"),
            "high": [100.0, 106.0, 107.0, 108.0],
            "low":  [97.0, 100.0, 104.0, 105.0],
            "open": [98.0, 100.5, 105.0, 106.0],
            "close":[99.0, 105.5, 106.0, 107.0]
        })
        fvg_unmit = MarketAnalyzer.detect_fvg(df_unmit, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert fvg_unmit["mitigated"] is False
        assert fvg_unmit["partially_mitigated"] is False

        df_part = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=4, freq="15min"),
            "high": [100.0, 106.0, 107.0, 105.0],
            "low":  [97.0, 100.0, 104.0, 103.0],  # 103.0 is below 104.0 (top) but above 102.0 (CE)
            "open": [98.0, 100.5, 105.0, 104.5],
            "close":[99.0, 105.5, 106.0, 103.5]
        })
        fvg_part = MarketAnalyzer.detect_fvg(df_part, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert fvg_part["mitigated"] is False
        assert fvg_part["partially_mitigated"] is True

        df_full = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=4, freq="15min"),
            "high": [100.0, 106.0, 107.0, 105.0],
            "low":  [97.0, 100.0, 104.0, 101.5],  # 101.5 touches below 102.0 (CE)
            "open": [98.0, 100.5, 105.0, 104.5],
            "close":[99.0, 105.5, 106.0, 102.0]
        })
        fvg_full = MarketAnalyzer.detect_fvg(df_full, min_gap_pips=1.0, symbol="EURUSD")[0]
        assert fvg_full["mitigated"] is True
        assert fvg_full["partially_mitigated"] is True

    def test_multi_asset_pip_thresholds(self):
        # Gold gap of $1.50 = 15 pips (pip_unit=0.10)
        df_gold = pd.DataFrame({
            "time": pd.date_range("2026-01-01", periods=3, freq="15min"),
            "high": [2640.0, 2655.0, 2660.0],
            "low":  [2630.0, 2640.5, 2645.0],
            "open": [2635.0, 2641.0, 2650.0],
            "close":[2638.0, 2652.0, 2658.0]
        })
        fvg_gold = MarketAnalyzer.detect_fvg(df_gold, min_gap_pips=5.0, symbol="XAUUSD")
        assert len(fvg_gold) == 1
        assert fvg_gold[0]["gap_pips"] == 50.0  # (2645.0 - 2640.0) / 0.10
