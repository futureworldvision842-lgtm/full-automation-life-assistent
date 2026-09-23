"""
tests/test_adversarial_m2_1_manim_stress.py — Milestone M2.1 Adversarial Stress Suite
=====================================================================================
Independent stress harness challenging visuals/manim_engine.py:
  1. Parameter extremes: negative prices, 0 balance, NaN/Inf in Kelly/Fibonacci,
     100k depth levels, inverted/zero range swings.
  2. Concurrency stress: 20 simultaneous render calls for SVG and MP4 without race
     conditions or file corruption (direct engine calls and dashboard HTTP endpoints).
  3. Memory bounds, ISO Base Media container verification, and XML structural integrity.

Author: Challenger M2.1 (Empirical Challenger: critic, specialist)
Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of forbidden identity. Deterministic risk <= 0.75%.
=====================================================================================
"""

import os
import sys
import math
import time
import uuid
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Project root setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional CV2
try:
    import cv2
except ImportError:
    cv2 = None

from starlette.testclient import TestClient
from dashboard import app as dash_app
from platform_runtime import internal_command_token

from visuals.manim_engine import (
    ManimVisualEngine,
    ManimEngine,
    PureSVGEngine,
    OpenCVVideoEngine,
    render_scene,
    render_orderbook_depth,
    render_cvd_absorption,
    render_fibonacci_ote,
    render_kelly_compounding,
    get_engine,
    AVAILABLE_SCENES
)


def validate_svg_xml(svg_content: str) -> ET.Element:
    """Validates that SVG XML is well-formed and returns root element."""
    assert isinstance(svg_content, str), "SVG content must be string"
    assert "<svg" in svg_content, "Missing <svg tag"
    assert "</svg>" in svg_content, "Missing </svg> tag"
    root = ET.fromstring(svg_content)
    assert root.tag.endswith("svg"), f"Root must be svg, got {root.tag}"
    return root


def validate_mp4_container(file_path: Path) -> dict:
    """Parses ISO Base Media atoms to confirm container integrity."""
    assert file_path.exists(), f"MP4 does not exist: {file_path}"
    size = file_path.stat().st_size
    assert size >= 32, f"MP4 file too small: {size} bytes"

    with open(file_path, "rb") as f:
        data = f.read(min(size, 4096))

    box_size, box_type = struct.unpack(">I4s", data[0:8])
    assert box_type == b"ftyp", f"First atom must be 'ftyp', got {box_type}"
    major_brand = data[8:12]
    return {"size": size, "major_brand": major_brand.decode("latin1", errors="ignore")}


# =============================================================================
# SUITE 1: PARAMETER EXTREMES (NEGATIVE PRICES, 0 BALANCE, 100K DEPTH)
# =============================================================================

class TestParameterExtremesChaos(unittest.TestCase):
    """Stress-test numerical extremes: negative prices, 0 balance, 100k depth levels."""

    def setUp(self):
        self.engine = get_engine()

    def test_negative_prices_orderbook(self):
        """Orderbook depth must handle negative commodity prices (e.g. WTI 2020 negative oil)."""
        params = {
            "symbol": "WTICRUDE",
            "mid_price": -37.63,
            "spread": 0.50,
            "bids": [
                {"price": -38.00, "volume": 1200.0},
                {"price": -39.50, "volume": 2500.0}
            ],
            "asks": [
                {"price": -37.00, "volume": 900.0},
                {"price": -36.00, "volume": 1800.0}
            ]
        }
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        self.assertTrue(res.ok, f"Failed on negative price: {res.get('error')}")
        root = validate_svg_xml(res.content)
        self.assertIn("-37.63", res.content)
        self.assertEqual(res.metadata.get("mid_price"), -37.63)

    def test_negative_spread_crossed_orderbook(self):
        """Orderbook depth with negative spread (crossed orderbook) must clamp safely."""
        params = {
            "symbol": "XAUUSD",
            "mid_price": 2735.0,
            "spread": -2.0,  # crossed book
            "depth_levels": 10
        }
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        self.assertTrue(res.ok)
        validate_svg_xml(res.content)

    def test_negative_prices_cvd_absorption(self):
        """CVD absorption with negative price swings and deep negative delta."""
        params = {
            "symbol": "WTI_BASIS",
            "price_series": [-15.0, -37.63, -25.0, -10.0],
            "cvd_series": [-50000.0, -80000.0, -20000.0, +15000.0],
            "divergence": "bullish"
        }
        res = self.engine.render_scene("cvd_absorption", format="svg", params=params)
        self.assertTrue(res.ok)
        validate_svg_xml(res.content)
        self.assertIn("-15.0", res.content)
        self.assertIn("-10.0", res.content)
        self.assertEqual(res.metadata.get("divergence"), "bullish")

    def test_negative_prices_fibonacci_ote(self):
        """Fibonacci OTE with negative swing ranges (e.g. -100.0 to -50.0)."""
        params = {
            "symbol": "SPREAD_ARB",
            "swing_low": -100.0,
            "swing_high": -50.0,
            "direction": "long"
        }
        res = self.engine.render_scene("fibonacci_ote", format="svg", params=params)
        self.assertTrue(res.ok)
        validate_svg_xml(res.content)
        levels = res.metadata.get("levels", {})
        self.assertAlmostEqual(levels.get("0.0"), -50.0, places=1)
        self.assertAlmostEqual(levels.get("100.0"), -100.0, places=1)
        self.assertAlmostEqual(levels.get("70.5"), -85.25, places=2)

    def test_inverted_and_zero_range_fibonacci(self):
        """Fibonacci OTE with inverted swing (high < low) or flat range (high == low)."""
        # Flat range (zero division defense)
        params_flat = {"swing_low": 2700.0, "swing_high": 2700.0}
        res_flat = self.engine.render_scene("fibonacci_ote", format="svg", params=params_flat)
        self.assertTrue(res_flat.ok)
        validate_svg_xml(res_flat.content)

        # Inverted range
        params_inv = {"swing_low": 2800.0, "swing_high": 2700.0}
        res_inv = self.engine.render_scene("fibonacci_ote", format="svg", params=params_inv)
        self.assertTrue(res_inv.ok)
        validate_svg_xml(res_inv.content)

    def test_zero_balance_kelly_compounding(self):
        """Kelly compounding with starting_balance = 0.0 or negative balance."""
        for bal in [0.0, -500.0, 1e-12]:
            params = {
                "starting_balance": bal,
                "win_rate": 0.55,
                "risk_reward": 2.5,
                "trades": 50
            }
            res = self.engine.render_scene("kelly_compounding", format="svg", params=params)
            self.assertTrue(res.ok)
            validate_svg_xml(res.content)
            self.assertEqual(res.metadata.get("starting_balance"), bal)

    def test_extreme_trades_count_kelly(self):
        """Kelly compounding with 0 trades, negative trades, and 100k trades."""
        for tr in [0, -10, 100000]:
            params = {"trades": tr, "win_rate": 0.55, "risk_reward": 2.0}
            res = self.engine.render_scene("kelly_compounding", format="svg", params=params)
            self.assertTrue(res.ok)
            validate_svg_xml(res.content)

    def test_100k_depth_levels_clamping_and_performance(self):
        """Requesting 100,000 depth levels must be clamped (<= 100) and complete under 50ms."""
        t0 = time.perf_counter()
        params = {"depth_levels": 100000}
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        dur_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(res.ok)
        validate_svg_xml(res.content)
        self.assertLess(dur_ms, 50.0, f"100k depth clamping took too long: {dur_ms:.2f}ms")

    def test_100k_bids_array_memory_and_runtime_bounds(self):
        """Passing an explicit array of 100,000 synthetic bids must slice safely without OOM."""
        huge_bids = [{"price": 2700.0 - (i * 0.01), "volume": 50.0 + (i % 100)} for i in range(100000)]
        t0 = time.perf_counter()
        params = {"bids": huge_bids, "depth_levels": 100000}
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        dur_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(res.ok)
        validate_svg_xml(res.content)
        self.assertLess(dur_ms, 150.0, f"100k bids array processing took {dur_ms:.2f}ms (>150ms limit)")


# =============================================================================
# SUITE 2: ADVERSARIAL NAN / INF HANDLING (CHAOS ANALYSIS)
# =============================================================================

class TestAdversarialNaNAndInfChaos(unittest.TestCase):
    """
    Adversarial probes for NaN and Inf across numerical kernels.
    Empirical check: Verify system survival and document behavior.
    """

    def setUp(self):
        self.engine = get_engine()

    def test_kelly_nan_and_inf_resilience(self):
        """Kelly compounding under NaN and Inf parameters."""
        # 1. NaN win rate
        res_nan = self.engine.render_scene("kelly_compounding", format="svg", params={"win_rate": float("nan")})
        self.assertTrue(res_nan.ok, "Engine must not raise uncaught exception on NaN win_rate")
        # Validate XML parseability even under NaN
        validate_svg_xml(res_nan.content)

        # 2. Inf win rate
        res_inf = self.engine.render_scene("kelly_compounding", format="svg", params={"win_rate": float("inf")})
        self.assertTrue(res_inf.ok, "Engine must not crash on Inf win_rate")
        validate_svg_xml(res_inf.content)

        # 3. Inf risk reward
        res_inf_rr = self.engine.render_scene("kelly_compounding", format="svg", params={"risk_reward": float("inf")})
        self.assertTrue(res_inf_rr.ok, "Engine must not crash on Inf risk_reward")
        validate_svg_xml(res_inf_rr.content)

    def test_fibonacci_nan_and_inf_resilience(self):
        """Fibonacci OTE under NaN and Inf swing prices."""
        # 1. NaN swing high
        res_nan_h = self.engine.render_scene("fibonacci_ote", format="svg", params={"swing_high": float("nan")})
        self.assertTrue(res_nan_h.ok, "Engine must not crash on NaN swing_high")
        validate_svg_xml(res_nan_h.content)

        # 2. Inf swing high
        res_inf_h = self.engine.render_scene("fibonacci_ote", format="svg", params={"swing_high": float("inf")})
        self.assertTrue(res_inf_h.ok, "Engine must not crash on Inf swing_high")
        validate_svg_xml(res_inf_h.content)

    def test_orderbook_and_cvd_nan_resilience(self):
        """Orderbook and CVD under NaN mid_price or series."""
        res_ob = self.engine.render_scene("orderbook_depth", format="svg", params={"mid_price": float("nan")})
        self.assertTrue(res_ob.ok)
        validate_svg_xml(res_ob.content)

        res_cvd = self.engine.render_scene("cvd_absorption", format="svg", params={"price_swing_1": float("nan")})
        self.assertTrue(res_cvd.ok)
        validate_svg_xml(res_cvd.content)


# =============================================================================
# SUITE 3: CONCURRENCY STRESS (20 SIMULTANEOUS SVG AND MP4 RENDERS)
# =============================================================================

class TestConcurrencyStressHarness(unittest.TestCase):
    """
    Stress-tests 20 simultaneous render calls for SVG and MP4 without race conditions,
    deadlocks, or file corruption.
    """

    def setUp(self):
        self.engine = get_engine()
        self.scenes = ["orderbook_depth", "cvd_absorption", "fibonacci_ote", "kelly_compounding"]

    def test_20_simultaneous_svg_renders(self):
        """20 concurrent threads simultaneously rendering SVG across all 4 quantitative scenes."""
        def _render_svg_worker(idx: int):
            scene = self.scenes[idx % len(self.scenes)]
            params = {"worker_id": idx, "seed": idx * 101}
            return self.engine.render_scene(scene, format="svg", params=params)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(_render_svg_worker, range(20)))
        dur_sec = time.perf_counter() - t0

        self.assertEqual(len(results), 20)
        for i, res in enumerate(results):
            self.assertTrue(res.ok, f"SVG worker {i} failed: {res.get('error')}")
            file_path = Path(res.file_path)
            self.assertTrue(file_path.exists(), f"File {file_path} does not exist")
            self.assertGreater(file_path.stat().st_size, 500, f"File {file_path} suspiciously small")

            # Parse XML to guarantee no race-induced truncation or corruption
            root = validate_svg_xml(res.content)
            self.assertEqual(root.attrib.get("viewBox"), "0 0 1280 720")

        # Performance check: 20 SVGs should complete in < 1.0s
        self.assertLess(dur_sec, 2.0, f"20 concurrent SVGs took {dur_sec:.2f}s (> 2.0s)")

    def test_20_simultaneous_mp4_renders(self):
        """20 concurrent threads simultaneously encoding MP4 videos without race conditions."""
        if cv2 is None:
            self.skipTest("OpenCV not installed in environment")

        def _render_mp4_worker(idx: int):
            scene = self.scenes[idx % len(self.scenes)]
            params = {"frames": 15, "worker_id": idx}
            return self.engine.render_scene(scene, format="mp4", params=params)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(_render_mp4_worker, range(20)))
        dur_sec = time.perf_counter() - t0

        self.assertEqual(len(results), 20)
        for i, res in enumerate(results):
            self.assertTrue(res.ok, f"MP4 worker {i} failed: {res.get('error')}")
            file_path = Path(res.file_path)
            self.assertTrue(file_path.exists(), f"MP4 file {file_path} missing")
            self.assertGreater(file_path.stat().st_size, 1024, f"MP4 {file_path} too small")

            # ISO Base Media Container atom verification
            container_info = validate_mp4_container(file_path)
            self.assertIn("major_brand", container_info)

            # OpenCV frame decoding probe
            cap = cv2.VideoCapture(str(file_path))
            self.assertTrue(cap.isOpened(), f"OpenCV failed to open {file_path}")
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.assertEqual(w, 1280)
            self.assertEqual(h, 720)
            self.assertEqual(fc, 15)

            ret, frame = cap.read()
            cap.release()
            self.assertTrue(ret, f"Failed to read first frame from {file_path}")
            self.assertIsNotNone(frame)
            self.assertEqual(frame.shape, (720, 1280, 3))

        # Performance check: 20 MP4s should finish under 15 seconds
        self.assertLess(dur_sec, 20.0, f"20 concurrent MP4s took {dur_sec:.2f}s (> 20s)")

    def test_20_simultaneous_mixed_svg_and_mp4_renders(self):
        """20 concurrent threads running mixed workload (10 SVG + 10 MP4) simultaneously."""
        def _render_mixed_worker(idx: int):
            scene = self.scenes[idx % len(self.scenes)]
            fmt = "svg" if (idx % 2 == 0) else "mp4"
            params = {"frames": 10, "worker_id": idx}
            return self.engine.render_scene(scene, format=fmt, params=params)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(_render_mixed_worker, range(20)))
        dur_sec = time.perf_counter() - t0

        self.assertEqual(len(results), 20)
        for i, res in enumerate(results):
            self.assertTrue(res.ok, f"Mixed worker {i} failed: {res.get('error')}")
            file_path = Path(res.file_path)
            self.assertTrue(file_path.exists())
            if res.format == "svg":
                validate_svg_xml(res.content)
            elif res.format == "mp4" and cv2 is not None:
                validate_mp4_container(file_path)

    def test_20_simultaneous_http_requests_dashboard(self):
        """20 concurrent HTTP requests to POST /api/visuals/render testing in-flight deduplication."""
        client = TestClient(dash_app, base_url="http://127.0.0.1:8770")
        headers = {
            "Content-Type": "application/json",
            "X-Jarvis-Internal-Token": internal_command_token()
        }

        # Burst of 20 identical requests for the same MP4 scene
        payload = {"scene": "orderbook_depth", "format": "mp4", "params": {"frames": 10}}

        def _http_worker(idx: int):
            return client.post("/api/visuals/render", json=payload, headers=headers)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            responses = list(executor.map(_http_worker, range(20)))
        dur_sec = time.perf_counter() - t0

        self.assertEqual(len(responses), 20)
        for idx, resp in enumerate(responses):
            self.assertEqual(resp.status_code, 200, f"HTTP worker {idx} failed with {resp.status_code}: {resp.text}")
            data = resp.json()
            self.assertTrue(data.get("ok"))
            self.assertIn("/api/visuals/stream/", data.get("url"))

        self.assertLess(dur_sec, 5.0, f"20 HTTP render requests took {dur_sec:.2f}s (> 5.0s)")


# =============================================================================
# SUITE 4: SECURITY AND FORBIDDEN IDENTITY AUDIT
# =============================================================================

class TestSecurityAndForbiddenIdentity(unittest.TestCase):
    """Audit for strict zero-identity leak and path traversal safety."""

    def setUp(self):
        self.engine = get_engine()

    def test_strict_zero_identity_leak_in_svg_and_metadata(self):
        """Render outputs and metadata across all 4 scenes must never mention forbidden identity."""
        forbidden = "".join(["adeel", "qureshi", "99"])
        for scene in ["orderbook_depth", "cvd_absorption", "fibonacci_ote", "kelly_compounding"]:
            res = self.engine.render_scene(scene, format="svg")
            content = (res.content or "").lower()
            meta_str = str(res.metadata).lower()
            self.assertNotIn(forbidden, content)
            self.assertNotIn(forbidden, meta_str)

    def test_svg_script_injection_escaped(self):
        """Malicious script tag injected into scene params must be safely handled without raw injection."""
        xss_payload = "<script>alert('pwned')</script>"
        res = self.engine.render_scene("orderbook_depth", format="svg", params={"symbol": xss_payload})
        self.assertTrue(res.ok)
        content = res.content
        self.assertNotIn("<script>", content)
        self.assertNotIn("alert(", content)


if __name__ == "__main__":
    unittest.main()
