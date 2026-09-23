"""
tests/test_turtle_soup_cvd_absorption.py
Tests for Features 12 & 13: Turtle Soup EQH/EQL Sweeps and Lee-Ready CVD Order Absorption.
"""

import pandas as pd
import numpy as np
import pytest
from src.order_flow_quant import OrderFlowQuantEngine


class TestTurtleSoupCVDSuite:

    @pytest.fixture
    def quant(self):
        return OrderFlowQuantEngine(pip_tolerance=2.0)

    def test_equal_lows_eql_inducement_sweep(self, quant):
        # Create bars with EQL at 2640.0 on Gold
        highs = [2650.0] * 25
        lows = [2645.0] * 25
        opens = [2648.0] * 25
        closes = [2647.0] * 25

        lows[4] = 2640.00
        lows[11] = 2640.10  # EQL within 2 pips ($0.20)
        lows[-1] = 2639.20  # Sweep wick below EQL
        opens[-1] = 2644.00
        closes[-1] = 2643.00  # Closes back above EQL

        df = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})
        ind = quant.detect_eqh_eql_inducement(df, symbol="XAUUSD")

        assert ind["is_swept"] is True
        assert ind["inducement_type"] == "BULLISH_EQL_SWEEP"
        assert abs(ind["level"] - 2640.0) <= 0.20

    def test_lee_ready_quote_rule_and_tick_test(self, quant):
        # Tick 1: Ask hit -> Buy (+1)
        # Tick 2: Bid hit -> Sell (-1)
        # Tick 3: Mid price, higher than last -> Uptick (+1)
        # Tick 4: Mid price, same as last -> Zero-tick carry (+1)
        ticks = pd.DataFrame({
            "bid": [1.0850, 1.0850, 1.0850, 1.0850],
            "ask": [1.0852, 1.0852, 1.0852, 1.0852],
            "last": [1.0852, 1.0850, 1.0851, 1.0851],
            "volume": [10.0, 10.0, 10.0, 10.0]
        })
        res = quant.compute_tick_cvd(ticks)
        assert res["total_volume"] == 40.0
        # Deltas: +10, -10, +10, +10 = +20
        assert res["net_delta"] == 20
        assert res["total_buy_vol"] == 30.0
        assert res["total_sell_vol"] == 10.0
        assert res["buyer_ratio"] == 0.75
        assert res["absorption_type"] == "BUYER_ABSORPTION"

    def test_seller_absorption_divergence(self, quant):
        # Price Higher High (2660 > 2650), but CVD Lower High (+300 < +900)
        div = quant.detect_absorption_divergence(
            price_swing_1=2650.0,
            price_swing_2=2660.0,
            cvd_swing_1=900.0,
            cvd_swing_2=300.0
        )
        assert div["absorption_detected"] is True
        assert div["type"] == "SELLER_ABSORPTION"
        assert div["bias"] == "BEARISH_REVERSAL"
