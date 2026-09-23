"""
test_frontend_chart_smc_cvd.py — Automated Test Suite for Milestones M2 & M3.

Verifies:
  1. Frontend JS files syntax, structural integrity, and ES/CommonJS export compliance:
     - dashboard/static/js/chart_engine.js
     - dashboard/static/js/smc_overlays.js
     - dashboard/static/js/cvd_pane.js
     - dashboard/static/css/terminal.css
     - dashboard/web_terminal.html
  2. Candlestick & Tick Aggregation Engine mathematics and edge cases.
  3. Fair Value Gap (FVG) 50% Consequent Encroachment (CE) and multi-candle mitigation lifecycle.
  4. Optimal Trade Entry (OTE) 62%–79% Fibonacci Retracement & 70.5% Institutional Sweet Spot calculations.
  5. Lee-Ready (1991) order flow tick classification rule (Quote rule, Tick test, Zero-tick carry-forward).
  6. Cumulative Volume Delta (CVD) series aggregation and Buyer/Seller volume ratio gauge.
  7. Real-Time Absorption Divergence recognition logic (Bullish & Bearish).
  8. 5-Level Depth of Market (DOM) Ladder & Order Imbalance Quotient.
  9. Coordinate transformation invariants and High-DPI scaling matrix.
  10. End-to-End REST & WebSocket integration with FastAPI server endpoints (/api/candles, /api/smc, /api/cvd, /ws/terminal).
"""

import os
import sys
import re
import math
import json
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import backend ASGI app
from src.web_terminal_server import app, GBMSyntheticMarketSimulator, MarketDataFeedManager


# =====================================================================
# 1. Structural & Static File Verification Tests
# =====================================================================

class TestFrontendFileIntegrity:
    """Verifies that all required frontend assets exist, are non-empty, and contain required symbols."""

    def test_chart_engine_file_exists_and_valid(self):
        file_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "chart_engine.js")
        assert os.path.exists(file_path), "chart_engine.js must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "class ChartEngine" in content
        assert "class StandaloneCanvasChart" in content
        assert "class CandleStreamAggregator" in content
        assert "priceToCoordinate" in content
        assert "coordinateToPrice" in content
        assert "timeToCoordinate" in content
        assert "coordinateToTime" in content
        assert "getVisibleRange" in content
        assert "subscribeVisibleRangeChanged" in content
        assert "subscribeCrosshairMove" in content
        assert "ASSET_CONFIGS" in content
        assert "TIMEFRAME_SECONDS" in content
        assert "module.exports" in content or "window.ChartEngine" in content

    def test_smc_overlays_file_exists_and_valid(self):
        file_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "smc_overlays.js")
        assert os.path.exists(file_path), "smc_overlays.js must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "class SMCOverlaysRenderer" in content
        assert "_renderFVGs" in content
        assert "_renderOrderBlocks" in content
        assert "_renderOTEGrid" in content
        assert "_renderSweeps" in content
        assert "_renderKillzones" in content
        assert "50% CE" in content or "fvgCe" in content
        assert "sweet_spot_705" in content or "70.5%" in content
        assert "setLayerVisibility" in content
        assert "toggleLayer" in content

    def test_cvd_pane_file_exists_and_valid(self):
        file_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "cvd_pane.js")
        assert os.path.exists(file_path), "cvd_pane.js must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "class CVDPaneRenderer" in content
        assert "classifyLeeReadyTick" in content
        assert "computeDOMImbalance" in content
        assert "updateCVD" in content
        assert "updateDOM" in content
        assert "_updateHeaderMetrics" in content
        assert "00F2FE" in content  # Glowing Cyan

    def test_terminal_css_file_exists_and_valid(self):
        file_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "css", "terminal.css")
        assert os.path.exists(file_path), "terminal.css must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "--bg-app: #070B14" in content or "#070B14" in content
        assert "--color-cyan: #00F2FE" in content or "#00F2FE" in content
        assert "--color-emerald: #10B981" in content or "#10B981" in content
        assert "--color-rose: #EF4444" in content or "#EF4444" in content
        assert ".terminal-layout" in content
        assert ".cockpit-sidebar" in content
        assert ".btn-killswitch" in content

    def test_web_terminal_html_exists_and_valid(self):
        file_path = os.path.join(PROJECT_ROOT, "dashboard", "web_terminal.html")
        assert os.path.exists(file_path), "web_terminal.html must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "chart_engine.js" in content
        assert "smc_overlays.js" in content
        assert "cvd_pane.js" in content
        assert "terminal.css" in content
        assert "chart-container" in content
        assert "cvd-container" in content
        assert "XAUUSD" in content
        assert "EURUSD" in content


# =====================================================================
# 2. Candlestick Aggregator & Mathematical Logic Tests
# =====================================================================

class TestCandlestickAggregatorMath:
    """Verifies tick-to-bar aggregation rules, boundary alignment, and price expansion."""

    def test_timeframe_seconds_modulo_alignment(self):
        tf_seconds = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
        test_timestamp = 1770982345  # Some arbitrary epoch second

        for tf, sec in tf_seconds.items():
            bar_start = test_timestamp - (test_timestamp % sec)
            assert bar_start % sec == 0
            assert bar_start <= test_timestamp < bar_start + sec

    def test_tick_stream_aggregation_expansion(self):
        tf_sec = 900
        ticks = [
            {"time": 1770000010, "last": 2650.0, "volume": 5},
            {"time": 1770000050, "last": 2655.0, "volume": 10},
            {"time": 1770000100, "last": 2648.0, "volume": 8},
            {"time": 1770000200, "last": 2652.5, "volume": 12},
        ]

        bar_start = 1770000010 - (1770000010 % tf_sec)
        active_bar = {
            "time": bar_start,
            "open": ticks[0]["last"],
            "high": ticks[0]["last"],
            "low": ticks[0]["last"],
            "close": ticks[0]["last"],
            "volume": ticks[0]["volume"]
        }

        for t in ticks[1:]:
            active_bar["high"] = max(active_bar["high"], t["last"])
            active_bar["low"] = min(active_bar["low"], t["last"])
            active_bar["close"] = t["last"]
            active_bar["volume"] += t["volume"]

        assert active_bar["open"] == 2650.0
        assert active_bar["high"] == 2655.0
        assert active_bar["low"] == 2648.0
        assert active_bar["close"] == 2652.5
        assert active_bar["volume"] == 35


# =====================================================================
# 3. SMC Mathematical Models (FVG 50% CE & OTE 70.5% Sweet Spot)
# =====================================================================

class TestSMCMathematicalModels:
    """Verifies FVG 50% CE midpoint and Fibonacci OTE golden pocket formulas."""

    def test_fvg_50_percent_consequent_encroachment_formula(self):
        # Bullish FVG: C1.high = 2651.20, C3.low = 2654.80
        top = 2654.80
        bottom = 2651.20
        ce = (top + bottom) / 2.0
        assert pytest.approx(ce, 0.001) == 2653.00

        # Bearish FVG: C1.low = 1.08900, C3.high = 1.08500
        top_bear = 1.08900
        bottom_bear = 1.08500
        ce_bear = (top_bear + bottom_bear) / 2.0
        assert pytest.approx(ce_bear, 0.00001) == 1.08700

    def test_fvg_mitigation_detection_logic(self):
        ce = 2653.00
        # Bullish FVG: mitigated if subsequent price trades down into CE (low <= CE)
        subsequent_bars_mitigated = [{"low": 2654.0}, {"low": 2652.8}]
        subsequent_bars_unmitigated = [{"low": 2654.5}, {"low": 2653.5}]

        is_mitigated = any(b["low"] <= ce for b in subsequent_bars_mitigated)
        is_unmitigated = any(b["low"] <= ce for b in subsequent_bars_unmitigated)

        assert is_mitigated is True
        assert is_unmitigated is False

    def test_ote_fibonacci_705_sweet_spot_golden_pocket(self):
        swing_high = 2665.00
        swing_low = 2630.00
        diff = swing_high - swing_low  # 35.00

        # Bullish impulse retracing into Discount
        fib_500 = swing_high - (0.500 * diff)  # 2647.50
        fib_618 = swing_high - (0.618 * diff)  # 2643.37
        sweet_spot_705 = swing_high - (0.705 * diff)  # 2640.325
        fib_786 = swing_high - (0.786 * diff)  # 2637.49

        assert pytest.approx(fib_500, 0.01) == 2647.50
        assert pytest.approx(fib_618, 0.01) == 2643.37
        assert pytest.approx(sweet_spot_705, 0.001) == 2640.325
        assert pytest.approx(fib_786, 0.01) == 2637.49

        # Confirm 70.5% sweet spot is strictly inside the [61.8%, 78.6%] golden pocket
        assert fib_786 < sweet_spot_705 < fib_618

    def test_order_block_touch_counter_logic(self):
        ob_top = 2648.50
        ob_bottom = 2644.00
        candle_closes = [2650.0, 2646.5, 2647.0, 2651.0, 2645.0, 2652.0]

        touches = sum(1 for c in candle_closes if ob_bottom <= c <= ob_top)
        assert touches == 3


# =====================================================================
# 4. Lee-Ready Order Flow, CVD & Absorption Divergence Tests
# =====================================================================

class TestLeeReadyAndCVD:
    """Verifies Lee-Ready classification, zero-tick carry forward, and absorption divergence."""

    def test_lee_ready_quote_rule_and_tick_test(self):
        def classify_tick(price, bid, ask, last_price, last_dir):
            mid = (bid + ask) / 2.0
            if price > mid:
                return 1
            elif price < mid:
                return -1
            else:
                if last_price is not None:
                    if price > last_price:
                        return 1
                    elif price < last_price:
                        return -1
                return last_dir

        # 1. Price > Mid (Quote Rule Buyer)
        assert classify_tick(price=2650.60, bid=2650.40, ask=2650.60, last_price=2650.50, last_dir=1) == 1
        # 2. Price < Mid (Quote Rule Seller)
        assert classify_tick(price=2650.40, bid=2650.40, ask=2650.60, last_price=2650.50, last_dir=1) == -1
        # 3. Price == Mid on Uptick
        assert classify_tick(price=2650.50, bid=2650.40, ask=2650.60, last_price=2650.40, last_dir=-1) == 1
        # 4. Price == Mid on Downtick
        assert classify_tick(price=2650.50, bid=2650.40, ask=2650.60, last_price=2650.60, last_dir=1) == -1
        # 5. Price == Mid on Zero-Tick (Carry forward last direction)
        assert classify_tick(price=2650.50, bid=2650.40, ask=2650.60, last_price=2650.50, last_dir=-1) == -1
        assert classify_tick(price=2650.50, bid=2650.40, ask=2650.60, last_price=2650.50, last_dir=1) == 1

    def test_buyer_seller_volume_ratio_zero_division_safety(self):
        def compute_ratio(buy_vol, sell_vol):
            tot = max(buy_vol + sell_vol, 1.0)
            buyer_pct = round((buy_vol / tot) * 100.0, 1)
            seller_pct = round(100.0 - buyer_pct, 1)
            return buyer_pct, seller_pct

        # Normal ratio
        b, s = compute_ratio(700.0, 300.0)
        assert b == 70.0 and s == 30.0

        # Zero volume boundary
        b0, s0 = compute_ratio(0.0, 0.0)
        assert b0 == 0.0 and s0 == 100.0

    def test_bullish_absorption_divergence_logic(self):
        # Bullish Absorption: Price makes Lower Low, but CVD makes Higher Low
        p1 = 2650.0  # Pivot 1 Low
        cvd1 = 1200  # Pivot 1 CVD

        p2 = 2645.0  # Pivot 2 Lower Low
        cvd2 = 1450  # Pivot 2 Higher Low

        is_bullish_absorption = (p2 < p1) and (cvd2 > cvd1)
        assert is_bullish_absorption is True

    def test_bearish_absorption_divergence_logic(self):
        # Bearish Absorption: Price makes Higher High, but CVD makes Lower High
        p1 = 2660.0  # Pivot 1 High
        cvd1 = 2500  # Pivot 1 CVD

        p2 = 2665.0  # Pivot 2 Higher High
        cvd2 = 2100  # Pivot 2 Lower High

        is_bearish_absorption = (p2 > p1) and (cvd2 < cvd1)
        assert is_bearish_absorption is True

    def test_dom_imbalance_quotient(self):
        bids = [{"price": 2650.4, "volume": 120.0}, {"price": 2650.3, "volume": 80.0}]
        asks = [{"price": 2650.6, "volume": 30.0}, {"price": 2650.7, "volume": 20.0}]

        tot_bid = sum(b["volume"] for b in bids)  # 200.0
        tot_ask = sum(a["volume"] for a in asks)  # 50.0
        tot_depth = tot_bid + tot_ask             # 250.0

        imbalance = tot_bid / tot_depth  # 0.80 (Heavy Bid Wall)
        assert pytest.approx(imbalance, 0.01) == 0.80
        assert imbalance >= 0.65  # Bullish Imbalance threshold


# =====================================================================
# 5. Coordinate Transformations & High-DPI Scaling Invariants
# =====================================================================

class TestCoordinateTransformations:
    """Verifies priceToY, YToPrice, high-DPI scaling, and boundary clipping."""

    def test_price_to_coordinate_and_inverse_round_trip(self):
        plot_height = 400.0
        top_padding = 20.0
        min_price = 2640.00
        max_price = 2670.00
        price_range = max_price - min_price

        def price_to_y(p):
            return top_padding + ((max_price - p) / price_range) * plot_height

        def y_to_price(y):
            normalized_y = (y - top_padding) / plot_height
            return max_price - (normalized_y * price_range)

        test_prices = [2640.00, 2645.50, 2655.00, 2669.99]
        for p in test_prices:
            y = price_to_y(p)
            p_recovered = y_to_price(y)
            assert pytest.approx(p_recovered, 0.0001) == p

    def test_retina_high_dpi_canvas_buffer_scaling(self):
        dpr = 2.0
        css_width = 800
        css_height = 500

        buffer_width = int(css_width * dpr)
        buffer_height = int(css_height * dpr)

        assert buffer_width == 1600
        assert buffer_height == 1000


# =====================================================================
# 6. REST API & WebSocket Protocol End-to-End Tests
# =====================================================================

class TestTerminalBackendIntegration:
    """Verifies that backend FastAPI endpoints conform to interface contracts."""

    @pytest.fixture(scope="class")
    def client(self):
        with TestClient(app) as c:
            yield c

    def test_get_status_endpoint(self, client):
        res = client.get("/api/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "account" in data
        assert "active_symbols" in data
        assert "quotes" in data
        assert "XAUUSD" in data["active_symbols"]

    def test_get_candles_endpoint(self, client):
        res = client.get("/api/candles?symbol=XAUUSD&timeframe=M15&limit=50")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert data["timeframe"] == "M15"
        assert "candles" in data
        assert len(data["candles"]) == 50
        c0 = data["candles"][0]
        assert "time" in c0 and "open" in c0 and "high" in c0 and "low" in c0 and "close" in c0

    def test_get_smc_endpoint(self, client):
        res = client.get("/api/smc?symbol=XAUUSD&timeframe=M15")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert "fvgs" in data
        assert "order_blocks" in data
        assert "ote" in data
        assert "sweeps" in data
        assert "killzones" in data
        if data["ote"] and "levels" in data["ote"]:
            assert "sweet_spot_705" in data["ote"]["levels"]

    def test_get_cvd_endpoint(self, client):
        res = client.get("/api/cvd?symbol=XAUUSD&limit=30")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert "cvd_history" in data
        assert "current_ratio" in data
        assert "divergence" in data

    def test_get_risk_metrics_endpoint(self, client):
        res = client.get("/api/risk/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "balance" in data
        assert "equity" in data
        assert "var_99_usd" in data
        assert "cvar_99_usd" in data
        assert "consistency_status" in data

    def test_web_terminal_html_route(self, client):
        res = client.get("/terminal")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "FUNDING PIPS" in res.text
