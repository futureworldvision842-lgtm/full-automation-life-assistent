"""
tests/test_world_monitor_layer_synthesis.py — Milestone M2: 22-Layer Geospatial Intelligence & GeoJSON Synthesis Test Suite.
========================================================================================================================
Empirically verifies:
1. Complete 22-layer geospatial intelligence synthesis in actions/geospatial_intelligence.py.
2. Layer data structure validation, coordinate integrity, and metadata summaries.
3. Standard RFC 7946 GeoJSON FeatureCollection conversion and [lon, lat] coordinate ordering.
4. 6 strategic maritime chokepoints validation (DEFCON, flow disruption %, Gold multipliers).
5. FastAPI endpoints /api/world/layers, /api/world/geojson, and /api/world/chokepoints/telemetry.
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from actions.geospatial_intelligence import (
    get_all_geospatial_layers,
    get_all_geospatial_layers_geojson,
    to_geojson_feature,
    CHOKEPOINTS_DATA
)


class TestWorldMonitorLayerSynthesis(unittest.TestCase):
    """Test suite for 22-layer geospatial data generation and GeoJSON compliance."""

    EXPECTED_22_LAYERS = [
        "conflicts",
        "bases",
        "cables",
        "pipelines",
        "hotspots",
        "ais",
        "nuclear",
        "sanctions",
        "weather",
        "tradeRoutes",
        "canadaAlerts",
        "economic",
        "waterways",
        "outages",
        "datacenters",
        "flights",
        "military",
        "natural",
        "minerals",
        "fires",
        "ucdpEvents",
        "resilienceScore"
    ]

    def setUp(self):
        self.bundle = get_all_geospatial_layers()

    def test_01_all_22_layers_present(self):
        """Verify that get_all_geospatial_layers() outputs all 22 required layers."""
        self.assertIn("layers", self.bundle)
        layers = self.bundle["layers"]
        
        self.assertEqual(len(self.EXPECTED_22_LAYERS), 22)
        for layer_key in self.EXPECTED_22_LAYERS:
            self.assertIn(layer_key, layers, f"Layer '{layer_key}' missing from geospatial payload")
            self.assertIsInstance(layers[layer_key], list, f"Layer '{layer_key}' should be a list")
            self.assertGreater(len(layers[layer_key]), 0, f"Layer '{layer_key}' should not be empty")

    def test_02_summary_metadata_consistency(self):
        """Verify summary block matches the synthesized layer counts and DEFCON status."""
        self.assertIn("summary", self.bundle)
        summary = self.bundle["summary"]
        self.assertEqual(summary["defcon"], 2)
        self.assertIn("DEFCON 2", summary["global_alert_status"])
        self.assertEqual(summary["active_chokepoints"], 6)
        self.assertEqual(summary["tracked_conflict_zones"], len(self.bundle["layers"]["conflicts"]))
        self.assertEqual(summary["military_bases"], len(self.bundle["layers"]["bases"]))
        self.assertEqual(summary["subsea_cables"], len(self.bundle["layers"]["cables"]))
        self.assertEqual(summary["pipelines"], len(self.bundle["layers"]["pipelines"]))

    def test_03_geodesic_subsea_cables_and_pipelines_path_integrity(self):
        """Verify polylines in cables, pipelines, and trade routes have valid multi-point coordinates."""
        for cable in self.bundle["layers"]["cables"]:
            self.assertIn("name", cable)
            self.assertIn("path", cable)
            self.assertGreaterEqual(len(cable["path"]), 2, f"Cable {cable.get('name')} must have >= 2 coordinates")
            for pt in cable["path"]:
                self.assertEqual(len(pt), 2, f"Coordinate pair {pt} must have [lat, lon]")
                lat, lon = pt
                self.assertTrue(-90 <= lat <= 90, f"Invalid lat: {lat}")
                self.assertTrue(-180 <= lon <= 180, f"Invalid lon: {lon}")

        for route in self.bundle["layers"]["tradeRoutes"]:
            self.assertIn("path", route)
            self.assertGreaterEqual(len(route["path"]), 2)

    def test_04_six_strategic_chokepoints_telemetry(self):
        """Verify all 6 strategic maritime chokepoints match the authoritative specifications."""
        cp_map = {cp["id"]: cp for cp in CHOKEPOINTS_DATA}
        self.assertEqual(len(cp_map), 6, "Must track exactly 6 strategic maritime chokepoints")

        # 1. Strait of Hormuz
        self.assertIn("hormuz", cp_map)
        h = cp_map["hormuz"]
        self.assertAlmostEqual(h["lat"], 26.5667, places=3)
        self.assertAlmostEqual(h["lon"], 56.2500, places=3)
        self.assertEqual(h["baseline_flow"], 21.0)
        self.assertEqual(h["current_flow"], 14.5)
        self.assertEqual(h["disruption_pct"], 31.0)
        self.assertEqual(h["defcon"], 2)
        self.assertEqual(h["gold_sensitivity"], 1.45)

        # 2. Bab el-Mandeb
        self.assertIn("bab_el_mandeb", cp_map)
        b = cp_map["bab_el_mandeb"]
        self.assertAlmostEqual(b["lat"], 12.5833, places=3)
        self.assertEqual(b["baseline_flow"], 8.8)
        self.assertEqual(b["current_flow"], 2.98)
        self.assertEqual(b["disruption_pct"], 66.1)
        self.assertEqual(b["defcon"], 2)
        self.assertEqual(b["gold_sensitivity"], 1.35)

        # 3. Suez Canal
        self.assertIn("suez", cp_map)
        s = cp_map["suez"]
        self.assertEqual(s["baseline_flow"], 12.0)
        self.assertEqual(s["current_flow"], 4.8)
        self.assertEqual(s["disruption_pct"], 60.0)
        self.assertEqual(s["defcon"], 3)
        self.assertEqual(s["gold_sensitivity"], 1.20)

        # 4. Strait of Malacca
        self.assertIn("malacca", cp_map)
        m = cp_map["malacca"]
        self.assertEqual(m["baseline_flow"], 16.0)
        self.assertEqual(m["current_flow"], 15.2)
        self.assertEqual(m["disruption_pct"], 5.0)
        self.assertEqual(m["defcon"], 4)
        self.assertEqual(m["gold_sensitivity"], 1.05)

        # 5. Panama Canal
        self.assertIn("panama", cp_map)
        p = cp_map["panama"]
        self.assertEqual(p["baseline_flow"], 5.0)
        self.assertEqual(p["current_flow"], 3.8)
        self.assertEqual(p["disruption_pct"], 24.0)
        self.assertEqual(p["defcon"], 4)
        self.assertEqual(p["gold_sensitivity"], 1.02)

        # 6. Bosporus & Dardanelles
        self.assertIn("bosporus", cp_map)
        bo = cp_map["bosporus"]
        self.assertEqual(bo["baseline_flow"], 3.0)
        self.assertEqual(bo["current_flow"], 2.1)
        self.assertEqual(bo["disruption_pct"], 30.0)
        self.assertEqual(bo["defcon"], 3)
        self.assertEqual(bo["gold_sensitivity"], 1.15)

    def test_05_rfc_7946_geojson_feature_collection(self):
        """Verify get_all_geospatial_layers_geojson() produces valid RFC 7946 FeatureCollection."""
        geojson = get_all_geospatial_layers_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertIsInstance(geojson["features"], list)
        self.assertGreater(len(geojson["features"]), 50)

        for feat in geojson["features"]:
            self.assertEqual(feat["type"], "Feature")
            self.assertIn("properties", feat)
            self.assertIn("layer", feat["properties"])
            
            geom = feat.get("geometry")
            if geom is not None:
                self.assertIn(geom["type"], ["Point", "LineString", "Polygon"])
                coords = geom["coordinates"]
                if geom["type"] == "Point":
                    self.assertEqual(len(coords), 2)
                    lon, lat = coords
                    self.assertTrue(-180 <= lon <= 180, f"Invalid GeoJSON lon: {lon}")
                    self.assertTrue(-90 <= lat <= 90, f"Invalid GeoJSON lat: {lat}")
                elif geom["type"] == "LineString":
                    self.assertGreaterEqual(len(coords), 2)
                    for pt in coords:
                        lon, lat = pt
                        self.assertTrue(-180 <= lon <= 180)
                        self.assertTrue(-90 <= lat <= 90)

    def test_06_dashboard_endpoints_integration(self):
        """Verify dashboard FastAPI routes for /api/world/layers and /api/world/chokepoints/telemetry."""
        from fastapi.testclient import TestClient
        import dashboard
        client = TestClient(dashboard.app)

        # Standard layers endpoint
        res = client.get("/api/world/layers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("layers", data)
        self.assertEqual(len(data["layers"]), 22)

        # GeoJSON formatted layers endpoint
        res_geojson = client.get("/api/world/layers?format=geojson")
        self.assertEqual(res_geojson.status_code, 200)
        fc = res_geojson.json()
        self.assertEqual(fc["type"], "FeatureCollection")
        self.assertGreater(len(fc["features"]), 0)

        # Dedicated /api/world/geojson endpoint
        res_geo_direct = client.get("/api/world/geojson")
        self.assertEqual(res_geo_direct.status_code, 200)
        fc_direct = res_geo_direct.json()
        self.assertEqual(fc_direct["type"], "FeatureCollection")

        # Chokepoints telemetry endpoint
        res_cp = client.get("/api/world/chokepoints/telemetry")
        self.assertEqual(res_cp.status_code, 200)
        cp_data = res_cp.json()
        self.assertEqual(cp_data["defcon"], 2)
        self.assertEqual(cp_data["gold_macro_multiplier"], 1.45)
        self.assertEqual(len(cp_data["chokepoints"]), 6)


if __name__ == "__main__":
    unittest.main()
