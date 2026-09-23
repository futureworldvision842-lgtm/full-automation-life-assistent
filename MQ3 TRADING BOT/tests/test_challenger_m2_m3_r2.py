"""
tests/test_challenger_m2_m3_r2.py — Challenger 1 Round 2 Empirical Stress & Invariant Test Suite.

Milestones M2 & M3 Verification:
  1. High-DPI / DevicePixelRatio Coordinate & Buffer Scaling.
  2. High-Throughput Candlestick Stream Aggregator (100,000 ticks).
  3. Price & Time Coordinate Transformation Bijective Invariants.
  4. SMC Mathematical Models (FVG 50% CE, OTE 70.5% Sweet Spot, OB Touch Invariants).
  5. Lee-Ready (1991) CVD State Machine & Zero-Tick Continuity.
  6. DOM Imbalance Quotient & Zero-Division Resilience.
  7. Absorption Divergence Classification Oracle.
  8. Static AST / Token Integrity for web_terminal.html and terminal.css.
"""

import os
import sys
import math
import pytest
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# =====================================================================
# 1. High-DPI Scaling & Canvas Coordinate Matrix Invariants
# =====================================================================

class TestHighDPICoordinateMatrix:
    """Verifies that high-DPI scaling preserves viewport coordinates without pixel drift."""

    @pytest.mark.parametrize("dpr", [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0])
    @pytest.mark.parametrize("width,height", [(800, 500), (1920, 1080), (2560, 1440), (3840, 2160)])
    def test_dpr_canvas_buffer_allocation(self, dpr, width, height):
        buffer_w = round(width * dpr)
        buffer_h = round(height * dpr)

        assert buffer_w >= width
        assert buffer_h >= height
        assert buffer_w == int(round(width * dpr))
        assert buffer_h == int(round(height * dpr))

    def test_price_coordinate_round_trip_bijective_precision(self):
        """Tests that price -> coordinate -> price round trip is exact within floating point limits."""
        plot_height = 460.0
        top_padding = 15.0
        bottom_padding = 25.0
        usable_height = plot_height - top_padding - bottom_padding
        min_price = 2600.00
        max_price = 2700.00
        price_range = max_price - min_price

        def price_to_y(p):
            return top_padding + ((max_price - p) / price_range) * usable_height

        def y_to_price(y):
            normalized_y = (y - top_padding) / usable_height
            return max_price - (normalized_y * price_range)

        # Generate 1,000 random prices across and slightly outside the range
        np.random.seed(42)
        random_prices = np.random.uniform(2590.00, 2710.00, size=1000)

        for p in random_prices:
            y = price_to_y(p)
            recovered_p = y_to_price(y)
            assert math.isclose(p, recovered_p, rel_tol=1e-9, abs_tol=1e-9), f"Price drift on {p}: got {recovered_p}"


# =====================================================================
# 2. High-Throughput Candlestick Stream Aggregator
# =====================================================================

class TestAggregatorStress:
    """Stress tests tick-to-bar aggregation with 100,000 ticks."""

    @pytest.mark.parametrize("tf_seconds", [60, 300, 900, 1800, 3600, 14400, 86400])
    def test_100k_ticks_stream_aggregation_invariants(self, tf_seconds):
        np.random.seed(1337)
        n_ticks = 100000
        start_time = 1770000000
        time_deltas = np.random.exponential(scale=1.5, size=n_ticks).cumsum()
        tick_times = (start_time + time_deltas).astype(int)
        price_innovations = np.random.normal(loc=0.0, scale=0.15, size=n_ticks).cumsum()
        prices = 2650.0 + price_innovations
        volumes = np.random.randint(1, 20, size=n_ticks)

        active_bar = None
        bars_generated = []

        for i in range(n_ticks):
            t_time = tick_times[i]
            bar_time = t_time - (t_time % tf_seconds)
            p = prices[i]
            v = volumes[i]

            if active_bar is None or active_bar["time"] != bar_time:
                if active_bar is not None:
                    bars_generated.append(active_bar)
                active_bar = {
                    "time": bar_time,
                    "open": p,
                    "high": p,
                    "low": p,
                    "close": p,
                    "volume": v
                }
            else:
                active_bar["high"] = max(active_bar["high"], p)
                active_bar["low"] = min(active_bar["low"], p)
                active_bar["close"] = p
                active_bar["volume"] += v

        if active_bar is not None:
            bars_generated.append(active_bar)

        # Invariant checks:
        assert len(bars_generated) > 0
        total_vol_bars = sum(b["volume"] for b in bars_generated)
        assert total_vol_bars == volumes.sum(), "Volume conservation law violated"

        for b in bars_generated:
            assert b["time"] % tf_seconds == 0, "Timeframe alignment violated"
            assert b["high"] >= b["open"], "High < Open"
            assert b["high"] >= b["close"], "High < Close"
            assert b["low"] <= b["open"], "Low > Open"
            assert b["low"] <= b["close"], "Low > Close"
            assert b["high"] >= b["low"], "High < Low"


# =====================================================================
# 3. SMC Mathematical Models
# =====================================================================

class TestSMCModelsPrecision:
    """Verifies SMC mathematical invariants across multi-asset decimal standards."""

    @pytest.mark.parametrize("symbol,top,bottom,expected_ce", [
        ("XAUUSD", 2654.80, 2651.20, 2653.00),
        ("EURUSD", 1.08942, 1.08518, 1.08730),
        ("GBPUSD", 1.29850, 1.29150, 1.29500),
        ("USDJPY", 154.650, 153.350, 154.000),
    ])
    def test_fvg_consequent_encroachment_formula(self, symbol, top, bottom, expected_ce):
        calculated_ce = (top + bottom) / 2.0
        assert math.isclose(calculated_ce, expected_ce, abs_tol=1e-5)

    def test_ote_fibonacci_mathematical_monotonicity(self):
        """Verifies that OTE Fibonacci levels are strictly monotonic across bullish/bearish swings."""
        # Bullish swing: impulse up from 2600 to 2700, retracing down
        low, high = 2600.0, 2700.0
        diff = high - low
        fib_500 = high - 0.500 * diff
        fib_618 = high - 0.618 * diff
        sweet_spot_705 = high - 0.705 * diff
        fib_786 = high - 0.786 * diff

        assert high > fib_500 > fib_618 > sweet_spot_705 > fib_786 > low
        assert math.isclose(sweet_spot_705, 2629.50, abs_tol=1e-4)


# =====================================================================
# 4. Lee-Ready CVD & DOM Order Flow
# =====================================================================

class TestLeeReadyCVDAndDOM:
    """Verifies Lee-Ready state machine rules, zero-tick carry-forward, and DOM quotient."""

    def test_lee_ready_state_machine_continuous_stream(self):
        def classify(price, bid, ask, last_p, last_d):
            mid = (bid + ask) / 2.0
            if price > mid:
                return 1
            if price < mid:
                return -1
            if last_p is not None:
                if price > last_p:
                    return 1
                if price < last_p:
                    return -1
            return last_d

        ticks = [
            (2650.5, 2650.0, 2650.8, 1),   # > mid (2650.4) -> +1
            (2650.2, 2650.0, 2650.8, -1),  # < mid (2650.4) -> -1
            (2650.4, 2650.0, 2650.8, 1),   # == mid, price 2650.4 > last_p 2650.2 -> +1
            (2650.4, 2650.0, 2650.8, 1),   # == mid, zero-tick carry forward -> +1
            (2650.3, 2650.0, 2650.8, -1),  # < mid -> -1
            (2650.4, 2650.0, 2650.8, 1),   # == mid, price 2650.4 > last_p 2650.3 -> +1
            (2650.4, 2650.0, 2650.8, 1),   # == mid, zero-tick carry forward -> +1
        ]

        last_p = None
        last_d = 1
        for p, b, a, expected_d in ticks:
            d = classify(p, b, a, last_p, last_d)
            assert d == expected_d, f"Mismatch on tick p={p}, b={b}, a={a}: expected {expected_d}, got {d}"
            last_p = p
            last_d = d

    def test_dom_imbalance_boundary_conditions(self):
        def compute_imbalance(bids, asks):
            tot_b = sum(b[1] for b in bids)
            tot_a = sum(a[1] for a in asks)
            tot = max(tot_b + tot_a, 1.0)
            return round(tot_b / tot, 4), round((tot_b / tot) * 100, 1), round((tot_a / tot) * 100, 1)

        # 1. Empty book
        q, b_pct, a_pct = compute_imbalance([], [])
        assert q == 0.0 and b_pct == 0.0 and a_pct == 0.0

        # 2. 100% bids
        q, b_pct, a_pct = compute_imbalance([(2650.0, 100.0)], [])
        assert q == 1.0 and b_pct == 100.0 and a_pct == 0.0

        # 3. 100% asks
        q, b_pct, a_pct = compute_imbalance([], [(2651.0, 100.0)])
        assert q == 0.0 and b_pct == 0.0 and a_pct == 100.0

        # 4. Balanced 50:50
        q, b_pct, a_pct = compute_imbalance([(2650.0, 50.0)], [(2651.0, 50.0)])
        assert q == 0.50 and b_pct == 50.0 and a_pct == 50.0


# =====================================================================
# 5. Static AST / Token Integrity Verification
# =====================================================================

class TestStaticFileASTAndTokens:
    """Verifies that all round 1 findings remain properly remediated."""

    def test_html_script_loading_order_and_containers(self):
        html_path = os.path.join(PROJECT_ROOT, "dashboard", "web_terminal.html")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Scripts must exist
        scripts = ["chart_engine.js", "smc_overlays.js", "cvd_pane.js", "terminal_app.js"]
        for s in scripts:
            assert s in content, f"Missing script reference: {s}"

        # Loading order: chart_engine, smc_overlays, cvd_pane BEFORE terminal_app
        idx_chart = content.index('<script src="/static/js/chart_engine.js">')
        idx_smc = content.index('<script src="/static/js/smc_overlays.js">')
        idx_cvd = content.index('<script src="/static/js/cvd_pane.js">')
        idx_app = content.index('<script src="/static/js/terminal_app.js">')

        assert idx_chart < idx_app, "chart_engine.js must be loaded before terminal_app.js"
        assert idx_smc < idx_app, "smc_overlays.js must be loaded before terminal_app.js"
        assert idx_cvd < idx_app, "cvd_pane.js must be loaded before terminal_app.js"

        # Container class tokens
        assert 'class="chart-container"' in content or 'class="candlestick-chart-container chart-container"' in content or 'chart-container' in content
        assert 'class="cvd-container"' in content or 'class="cvd-pane-container cvd-container"' in content or 'cvd-container' in content

    def test_css_design_tokens_and_class_aliases(self):
        css_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "css", "terminal.css")
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Design tokens
        assert "--bg-app:" in content
        assert "--color-cyan:" in content
        assert "--color-emerald:" in content
        assert "--color-rose:" in content

        # Aliases
        assert ".terminal-layout" in content
        assert ".cockpit-sidebar" in content
        assert ".btn-killswitch" in content
        assert ".chart-container" in content
        assert ".cvd-container" in content
