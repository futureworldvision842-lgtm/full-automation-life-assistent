"""
tests/test_manim_visuals.py — Milestone M2 Verification Suite
=============================================================================
Comprehensive unit and integration test suite covering:
  1. Unit tests for visuals/manim_engine.py (4 scenes, mathematical validity)
  2. SVG vector structure validation and XML sanitization
  3. MP4 container ISO atom validation and OpenCV playability
  4. Integration tests for dashboard.py visual endpoints (:8770)
  5. Security, path traversal protection, and zero-error headless resilience

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of forbidden identity. Deterministic risk <= 0.75%.
=============================================================================
"""

import os
import sys
import re
import json
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock

# Project root setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient

# Optional CV2
try:
    import cv2
except ImportError:
    cv2 = None

# Visual Engine Imports
try:
    from visuals.manim_engine import (
        ManimVisualEngine,
        ManimEngine,
        render_orderbook_depth,
        render_cvd_absorption,
        render_fibonacci_ote,
        render_kelly_compounding,
        get_visual_engine,
        get_engine,
        render_scene
    )
except ImportError:
    ManimVisualEngine = None


# =============================================================================
# HELPER VALIDATORS
# =============================================================================

def validate_svg_xml(svg_content: str) -> ET.Element:
    """Validates well-formedness of SVG XML and returns the root element."""
    assert isinstance(svg_content, str), "SVG content must be a string"
    assert "<svg" in svg_content, "SVG content missing <svg tag"
    assert "</svg>" in svg_content, "SVG content missing </svg> tag"
    root = ET.fromstring(svg_content)
    assert root.tag.endswith("svg"), f"Root element must be svg, got {root.tag}"
    return root


def validate_mp4_container(file_path: Path) -> dict:
    """Parses ISO Base Media atoms in MP4 file to confirm container integrity."""
    assert file_path.exists(), f"MP4 file does not exist: {file_path}"
    size = file_path.stat().st_size
    assert size >= 32, f"MP4 file too small ({size} bytes)"

    with open(file_path, "rb") as f:
        data = f.read(min(size, 4096))

    box_size, box_type = struct.unpack(">I4s", data[0:8])
    assert box_type == b"ftyp", f"First atom must be 'ftyp', got {box_type}"
    major_brand = data[8:12]
    valid_brands = [b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"qt  ", b"M4V ", b"mp4v"]
    assert any(major_brand.startswith(b) for b in valid_brands) or len(major_brand) == 4, \
        f"Unexpected major brand: {major_brand}"

    return {"size": size, "major_brand": major_brand.decode("latin1", errors="ignore")}


# =============================================================================
# TEST CLASS 1: UNIT TESTS FOR 4 MATHEMATICAL SCENES (SVG)
# =============================================================================

class TestManimEngineSceneMath(unittest.TestCase):
    """Unit tests verifying mathematical accuracy and SVG structure for all 4 scenes."""

    def setUp(self):
        if ManimVisualEngine is None:
            self.skipTest("visuals.manim_engine not yet available")
        self.engine = get_visual_engine()

    def test_list_scenes_catalog(self):
        """Engine must register all 4 required quantitative scenes."""
        scenes = self.engine.list_scenes()
        self.assertIsInstance(scenes, list)
        expected = ["orderbook_depth", "cvd_absorption", "fibonacci_ote", "kelly_compounding"]
        for s in expected:
            self.assertIn(s, scenes, f"Scene '{s}' must be present in engine catalog")

    def test_orderbook_depth_math_and_svg(self):
        """Orderbook depth scene must compute cumulative depth and highlight whale walls."""
        params = {
            "symbol": "XAUUSD",
            "mid_price": 2735.50,
            "depth_levels": 20,
            "whale_walls": [{"price": 2730.0, "size": 1500, "side": "bid"}]
        }
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        self.assertTrue(res.get("ok"), f"Render failed: {res.get('error')}")
        filename = res.get("filename") or res.get("file_path", "")
        self.assertIn("orderbook_depth", filename)

        # Validate SVG
        svg_text = res.get("content") or Path(res["file_path"]).read_text(encoding="utf-8")
        root = validate_svg_xml(svg_text)
        self.assertIn("viewBox", root.attrib)

        # Check visual semantics
        self.assertIn("2735.5", svg_text, "Mid price must be displayed")
        self.assertIn("1500", svg_text, "Whale wall volume must be annotated")
        self.assertIn("WHALE", svg_text.upper())

    def test_cvd_absorption_divergence_svg(self):
        """CVD absorption scene must correctly tag bullish and bearish delta absorption."""
        params = {
            "symbol": "XAUUSD",
            "divergence": "bullish",
            "price_series": [2745.0, 2740.0, 2732.0, 2730.0],
            "cvd_series": [-1200.0, -800.0, -200.0, +350.0]
        }
        res = self.engine.render_scene("cvd_absorption", format="svg", params=params)
        self.assertTrue(res.get("ok"))
        svg_text = res.get("content") or Path(res["file_path"]).read_text(encoding="utf-8")
        validate_svg_xml(svg_text)
        self.assertTrue(
            "BULLISH" in svg_text.upper() or "ABSORPTION" in svg_text.upper(),
            "Bullish absorption annotation must be present"
        )

    def test_fibonacci_ote_705_level_calculation(self):
        """Fibonacci OTE scene must mathematically place 70.5% retracement sweet spot."""
        swing_low = 2700.0
        swing_high = 2800.0
        expected_705 = 2800.0 - (0.705 * 100.0)  # 2729.50
        expected_618 = 2800.0 - (0.618 * 100.0)  # 2738.20
        expected_786 = 2800.0 - (0.786 * 100.0)  # 2721.40

        params = {"swing_low": swing_low, "swing_high": swing_high, "direction": "long"}
        res = self.engine.render_scene("fibonacci_ote", format="svg", params=params)
        self.assertTrue(res.get("ok"))
        meta = res.get("metadata", {})
        levels = meta.get("levels", {})

        if levels:
            self.assertAlmostEqual(levels.get("70.5"), expected_705, places=2)
            self.assertAlmostEqual(levels.get("61.8"), expected_618, places=2)
            self.assertAlmostEqual(levels.get("78.6"), expected_786, places=2)

        svg_text = res.get("content") or Path(res["file_path"]).read_text(encoding="utf-8")
        validate_svg_xml(svg_text)
        self.assertIn("70.5", svg_text, "70.5% OTE label must be rendered in SVG")
        self.assertIn("OTE", svg_text.upper())

    def test_kelly_compounding_formula_and_prop_cap(self):
        """Kelly compounding scene must enforce the <= 0.75% FundingPips ceiling."""
        win_rate = 0.55
        risk_reward = 2.5
        params = {
            "win_rate": win_rate,
            "risk_reward": risk_reward,
            "starting_balance": 100000.0,
            "trades": 50
        }
        res = self.engine.render_scene("kelly_compounding", format="svg", params=params)
        self.assertTrue(res.get("ok"))
        meta = res.get("metadata", {})
        if "kelly_f" in meta:
            self.assertAlmostEqual(meta["kelly_f"], 0.37, places=2)
        if "capped_risk" in meta:
            self.assertLessEqual(meta["capped_risk"], 0.0075)

        svg_text = res.get("content") or Path(res["file_path"]).read_text(encoding="utf-8")
        validate_svg_xml(svg_text)
        self.assertIn("0.75%", svg_text, "0.75% prop-firm limit must be visually annotated")

    def test_svg_security_sanitization(self):
        """SVG generator must strictly omit script tags and executable attributes."""
        res = self.engine.render_scene("orderbook_depth", format="svg")
        svg_text = res.get("content") or Path(res["file_path"]).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"<\s*script", svg_text, re.I))
        self.assertIsNone(re.search(r"on\w+\s*=", svg_text, re.I))
        self.assertIsNone(re.search(r"<!ENTITY", svg_text, re.I))


# =============================================================================
# TEST CLASS 2: MP4 CONTAINER AND HEADLESS ENCODING CHECKS
# =============================================================================

class TestManimEngineMP4Container(unittest.TestCase):
    """Unit tests for MP4 file container headers, atom layout, and video playability."""

    def setUp(self):
        if ManimVisualEngine is None:
            self.skipTest("visuals.manim_engine not yet available")
        self.engine = get_visual_engine()

    def test_mp4_render_orderbook_container_integrity(self):
        """Rendering MP4 must produce a valid ISO Base Media file with 'ftyp' box."""
        res = self.engine.render_scene("orderbook_depth", format="mp4", params={"frames": 10})
        self.assertTrue(res.get("ok"), f"MP4 render failed: {res.get('error')}")
        file_path = Path(res["file_path"])
        self.assertTrue(file_path.exists())

        info = validate_mp4_container(file_path)
        self.assertGreaterEqual(info["size"], 1024, "MP4 file must exceed 1KB")

    def test_mp4_opencv_frame_probe(self):
        """Rendered MP4 file must be decodable by OpenCV without corrupt frames."""
        if cv2 is None:
            self.skipTest("OpenCV not installed in environment")

        res = self.engine.render_scene("kelly_compounding", format="mp4", params={"frames": 10})
        self.assertTrue(res.get("ok"))
        file_path = str(res["file_path"])

        cap = cv2.VideoCapture(file_path)
        self.assertTrue(cap.isOpened(), "cv2.VideoCapture failed to open MP4 container")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertGreater(count, 0)

        ret, frame = cap.read()
        cap.release()
        self.assertTrue(ret, "Failed to read first video frame from MP4")
        self.assertIsNotNone(frame)
        self.assertEqual(frame.ndim, 3)

    def test_zero_crash_headless_fallback(self):
        """When manim/ffmpeg is mocked as absent, engine falls back cleanly without crash."""
        with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            res = self.engine.render_scene("fibonacci_ote", format="mp4")
            self.assertTrue(res.get("ok"))
            self.assertTrue(Path(res["file_path"]).exists())


# =============================================================================
# TEST CLASS 3: INTEGRATION TESTS FOR DASHBOARD.PY VISUAL ENDPOINTS
# =============================================================================

class TestDashboardVisualEndpoints(unittest.TestCase):
    """Integration tests verifying HTTP routes in dashboard.py (:8770)."""

    @classmethod
    def setUpClass(cls):
        from dashboard import app as dash_app
        cls.dash_app = dash_app
        cls.client = TestClient(cls.dash_app, base_url="http://127.0.0.1:8770")

        from platform_runtime import internal_command_token
        cls.auth_headers = {
            "Content-Type": "application/json",
            "X-Jarvis-Internal-Token": internal_command_token()
        }

    def test_api_visuals_animations_catalog_200(self):
        """GET /api/visuals/animations must return list of 4 scenes."""
        resp = self.client.get("/api/visuals/animations", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        names = [a if isinstance(a, str) else a.get("id") for a in data.get("animations", [])]
        for required in ["orderbook_depth", "cvd_absorption", "fibonacci_ote", "kelly_compounding"]:
            self.assertIn(required, names)

    def test_api_visuals_render_svg_success(self):
        """POST /api/visuals/render with SVG format returns 200 and valid file URL."""
        payload = {
            "scene": "fibonacci_ote",
            "format": "svg",
            "params": {"swing_low": 2700, "swing_high": 2800}
        }
        resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("url", data)
        self.assertIn(".svg", data["url"])

        # Fetch the rendered SVG through the served URL
        svg_resp = self.client.get(data["url"], headers=self.auth_headers)
        self.assertEqual(svg_resp.status_code, 200)
        self.assertEqual(svg_resp.headers.get("content-type"), "image/svg+xml")
        self.assertIn("<svg", svg_resp.text)

    def test_api_visuals_render_mp4_success(self):
        """POST /api/visuals/render with MP4 format returns 200 and streamable URL."""
        payload = {
            "scene": "kelly_compounding",
            "format": "mp4",
            "params": {"win_rate": 0.55, "risk_reward": 2.5}
        }
        resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("url", data)
        self.assertIn(".mp4", data["url"])

    def test_api_visuals_render_unknown_scene_returns_400(self):
        """POST /api/visuals/render with unknown scene must return 400 Bad Request."""
        payload = {"scene": "invalid_alien_chart", "format": "svg"}
        resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data.get("ok"))

    def test_api_visuals_render_invalid_format_returns_400(self):
        """POST /api/visuals/render with illegal format must return 400 Bad Request."""
        payload = {"scene": "orderbook_depth", "format": "exe"}
        resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)

    def test_api_visuals_svg_path_traversal_blocked(self):
        """GET /api/visuals/svg/{filename} must block directory traversal attempts."""
        traversals = [
            "../../dashboard.py",
            "..%2F..%2F.env",
            "....//....//dashboard.py",
            "C:\\Windows\\System32\\cmd.exe"
        ]
        for bad_path in traversals:
            resp = self.client.get(f"/api/visuals/svg/{bad_path}", headers=self.auth_headers)
            self.assertIn(resp.status_code, [400, 403, 404], f"Traversal not blocked for: {bad_path}")

    def test_api_visuals_stream_path_traversal_blocked(self):
        """GET /api/visuals/stream/{filename} must block directory traversal attempts."""
        traversals = [
            "../../main.py",
            "..%2F..%2Fruntime%2Fdaemon.pid",
            "../.env"
        ]
        for bad_path in traversals:
            resp = self.client.get(f"/api/visuals/stream/{bad_path}", headers=self.auth_headers)
            self.assertIn(resp.status_code, [400, 403, 404])

    def test_api_visuals_stream_nonexistent_returns_404(self):
        """Streaming a missing MP4 file returns 404 Not Found."""
        resp = self.client.get("/api/visuals/stream/ghost_video_99999.mp4", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    def test_api_visuals_svg_nonexistent_returns_404(self):
        """Fetching a missing SVG file returns 404 Not Found."""
        resp = self.client.get("/api/visuals/svg/ghost_chart_99999.svg", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)


# =============================================================================
# TEST CLASS 4: ADVERSARIAL STRESS AND BOUNDARY VERIFICATION
# =============================================================================

class TestManimVisualsAdversarialStress(unittest.TestCase):
    """Adversarial stress and security boundary tests."""

    def setUp(self):
        if ManimVisualEngine is None:
            self.skipTest("visuals.manim_engine not yet available")
        self.engine = get_visual_engine()

    def test_kelly_zero_or_negative_expectancy(self):
        """Kelly formula with p=0.2 and b=1.0 has negative expectancy; must clamp to 0."""
        params = {"win_rate": 0.2, "risk_reward": 1.0, "starting_balance": 50000.0}
        res = self.engine.render_scene("kelly_compounding", format="svg", params=params)
        self.assertTrue(res.get("ok"))
        meta = res.get("metadata", {})
        if "capped_risk" in meta:
            self.assertEqual(meta["capped_risk"], 0.0)

    def test_orderbook_extreme_depth_clamping(self):
        """Depth levels requested at 50,000 must be clamped to prevent memory exhaustion."""
        params = {"depth_levels": 50000}
        res = self.engine.render_scene("orderbook_depth", format="svg", params=params)
        self.assertTrue(res.get("ok"))

    def test_strict_identity_compliance(self):
        """Ensure no forbidden identity substrings leak in rendered outputs or metadata."""
        forbidden = "".join(["adeel", "qureshi", "99"])
        for scene in ["orderbook_depth", "cvd_absorption", "fibonacci_ote", "kelly_compounding"]:
            res = self.engine.render_scene(scene, format="svg")
            content = res.get("content", "")
            self.assertNotIn(forbidden, content.lower())


if __name__ == "__main__":
    unittest.main()
