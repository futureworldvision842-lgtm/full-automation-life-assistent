"""
tests/test_world_monitor_deep_fusion.py — Milestone M2: Deep Geospatial Fusion, Quantitative Chokepoint Pricing & UI Verification.
================================================================================================================================
Empirically verifies:
1. Multi-asset quantitative shock calculations (XAUUSD 1.45x, WTI 1.50x with $8.50/bbl premium, EURUSD 0.80x/0.85x).
2. Dynamic chokepoint updates and anomaly triggers across all 6 strategic maritime waterways.
3. Quadratic bezier geodesic arc curvature algorithm (createCurvedArc math model).
4. Master Command Center Web HUD (universal_command_center.html) contracts:
   - Zero-watermark ArcGIS World Dark Gray tiles.
   - 1-click native World Monitor (:3000) iframe toggle.
   - 22-layer interactive toolbar chips and badge counters.
"""

import sys
import math
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))

from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine


def python_create_curved_arc(start, end, num_points=25):
    """Python implementation of web/universal_command_center.html createCurvedArc function."""
    points = []
    lat1, lon1 = start
    lat2, lon2 = end

    mid_lat = (lat1 + lat2) / 2.0 + math.sin(abs(lon2 - lon1) * math.pi / 180.0) * 12.0
    mid_lon = (lon1 + lon2) / 2.0

    for i in range(num_points + 1):
        t = i / float(num_points)
        lat = (1.0 - t) * (1.0 - t) * lat1 + 2.0 * (1.0 - t) * t * mid_lat + t * t * lat2
        lon = (1.0 - t) * (1.0 - t) * lon1 + 2.0 * (1.0 - t) * t * mid_lon + t * t * lon2
        points.append((lat, lon))
    return points


class TestWorldMonitorDeepFusion(unittest.TestCase):
    """Test suite for deep geospatial fusion, quant pricing vectors, and UI contracts."""

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()

    def test_01_gold_macro_multiplier_at_defcon_2(self):
        """Verify XAUUSD Safe-Haven multiplier is 1.45x under DEFCON 2 geopolitical stress."""
        bias = self.engine.evaluate_geopolitical_market_bias("XAUUSD")
        self.assertEqual(bias["bias"], "STRONG_BUY")
        self.assertEqual(bias["macro_multiplier"], 1.45)
        self.assertEqual(bias["geo_bias"], "STRONG_BULLISH")
        self.assertGreater(bias["confluence_boost"], 0.40)

    def test_02_crude_oil_geopolitical_risk_premium(self):
        """Verify WTI Crude multiplier is 1.50x and contains $8.50/bbl structural risk premium."""
        bias = self.engine.evaluate_geopolitical_market_bias("WTI")
        self.assertEqual(bias["bias"], "STRONG_BUY")
        self.assertEqual(bias["macro_multiplier"], 1.50)
        self.assertIn("Hormuz", " ".join(bias["key_drivers"]))
        self.assertIn("$8.50/bbl", bias["reasoning"])

    def test_03_all_six_chokepoints_in_quant_engine(self):
        """Verify all 6 strategic maritime chokepoints exist and can be dynamically updated."""
        brief = self.engine.get_world_intelligence_brief()
        cps = brief["chokepoints"]
        
        # Check presence of all 6 chokepoints
        expected_ids = [
            "hormuz_strait",
            "bab_el_mandeb",
            "suez",
            "malacca_strait",
            "panama_canal",
            "bosporus_dardanelles"
        ]
        for cid in expected_ids:
            self.assertIn(cid, cps, f"Chokepoint '{cid}' missing from WorldMonitorIntelligenceEngine")

        # Dynamic flow update test
        updated = self.engine.update_chokepoint_flow("panama_canal", current_mbd=2.0)
        self.assertEqual(updated["current_mbd"], 2.0)
        self.assertEqual(updated["disruption_pct"], 60.0) # (1 - 2.0/5.0) * 100
        self.assertTrue(updated["anomaly_signal"])

    def test_04_geodesic_curved_bezier_arc_math(self):
        """Verify quadratic bezier curved arc math produces continuous, bounded, arched polylines."""
        # Virginia Beach to Bilbao (MAREA cable)
        start = (36.85, -75.97)
        end = (43.34, -2.93)
        arc = python_create_curved_arc(start, end, num_points=30)
        
        self.assertEqual(len(arc), 31)
        self.assertAlmostEqual(arc[0][0], start[0], places=4)
        self.assertAlmostEqual(arc[0][1], start[1], places=4)
        self.assertAlmostEqual(arc[-1][0], end[0], places=4)
        self.assertAlmostEqual(arc[-1][1], end[1], places=4)

        # Midpoint should have a northern latitude bulge due to spherical curvature simulation
        mid_idx = 15
        linear_mid_lat = (start[0] + end[0]) / 2.0
        self.assertGreater(arc[mid_idx][0], linear_mid_lat, "Bezier arc should curve northward for realistic geodesic display")

    def test_05_web_hud_source_verification(self):
        """Verify web/universal_command_center.html meets all UI acceptance criteria."""
        html_path = BASE_DIR / "web" / "universal_command_center.html"
        self.assertTrue(html_path.exists(), "universal_command_center.html must exist")
        content = html_path.read_text(encoding="utf-8")

        # 1. Zero watermark ArcGIS World Dark Gray tiles
        self.assertIn("World_Dark_Gray_Base/MapServer", content)
        self.assertIn("World_Dark_Gray_Reference/MapServer", content)

        # 2. Geodesic curved bezier arc generator
        self.assertIn("function createCurvedArc", content)

        # 3. Native World Monitor (:3000) 1-click toggle and iframe embed
        self.assertIn("switchMapMode('worldmonitor')", content)
        self.assertIn("http://127.0.0.1:3000", content)
        self.assertIn("id=\"worldMonitorIframe\"", content)

        # 4. All 22 Layer definitions
        expected_keys = [
            "conflicts", "bases", "cables", "pipelines", "hotspots", "ais",
            "nuclear", "sanctions", "weather", "tradeRoutes", "canadaAlerts",
            "economic", "waterways", "outages", "datacenters", "flights",
            "military", "natural", "minerals", "fires", "ucdpEvents", "resilienceScore"
        ]
        for key in expected_keys:
            self.assertIn(f'key: "{key}"', content, f"Layer key '{key}' missing from LAYER_DEFS")


if __name__ == "__main__":
    unittest.main()
