"""
tests/test_asian_judas_swings.py
Tests for Feature 11: Asian Session Box (00-06 UTC) & London Open Judas Swings (07-10 UTC).
"""

import pandas as pd
import pytest
from src.market_maker_game_engine import MarketMakerGameEngine


class TestAsianJudasSwingsSuite:

    @pytest.fixture
    def mm_engine(self):
        return MarketMakerGameEngine()

    def test_asian_range_box_calculation(self, mm_engine):
        times = pd.date_range("2026-01-01 00:00:00", periods=6, freq="1h", tz="UTC")
        df_asian = pd.DataFrame({
            "time": times,
            "high": [2642.0, 2645.0, 2644.0, 2648.0, 2643.0, 2646.0],
            "low":  [2636.0, 2638.0, 2637.0, 2639.0, 2635.0, 2638.0],
            "open": [2638.0, 2642.0, 2643.0, 2644.0, 2641.0, 2644.0],
            "close":[2642.0, 2643.0, 2644.0, 2642.0, 2643.0, 2645.0]
        })
        box = mm_engine.calculate_asian_session_box(df_asian)
        assert box["asian_high"] == 2648.0
        assert box["asian_low"] == 2635.0
        assert box["asian_range"] == 13.0
        assert box["asian_mid"] == 2641.5
        assert box["candle_count"] == 6

    def test_london_open_bullish_judas_swing(self, mm_engine):
        # Asian Box: High = 2650.0, Low = 2640.0
        df_asian = pd.DataFrame({
            "high": [2650.0, 2648.0],
            "low":  [2640.0, 2642.0],
            "open": [2642.0, 2645.0],
            "close":[2648.0, 2644.0]
        })
        # London Open Candle: Sweeps to 2635.0 (below Asian Low 2640.0), closes at 2644.0 with lower wick = 9.0
        df_london = pd.DataFrame({
            "high": [2646.0],
            "low":  [2635.0],
            "open": [2644.0],
            "close":[2644.0]
        })
        judas = mm_engine.detect_judas_swing(df_london, session_name="LONDON", df_asian=df_asian)
        assert judas["judas_detected"] is True
        assert judas["type"] == "BULLISH_JUDAS_SWING"
        assert judas["swept_level"] == 2640.0
        assert judas["rejection_wick_price"] == 2635.0

    def test_rejection_wick_ratio_filter(self, mm_engine):
        # Asian Box: High = 2650.0
        df_asian = pd.DataFrame({"high": [2650.0], "low": [2640.0], "open": [2645.0], "close": [2648.0]})
        # Strong clean breakout candle (closes far above 2650 with minimal upper wick)
        df_breakout = pd.DataFrame({
            "high": [2660.0],
            "low":  [2648.0],
            "open": [2649.0],
            "close":[2659.0]  # Closes outside box -> Not a fakeout rejection
        })
        judas = mm_engine.detect_judas_swing(df_breakout, session_name="LONDON", df_asian=df_asian)
        assert judas["judas_detected"] is False
