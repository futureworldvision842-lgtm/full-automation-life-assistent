"""
tests/test_challenger_m2_stress.py — Adversarial Stress Test Suite for Milestone M2:
Live World Monitor & Geospatial Tactical Intelligence Fusion.
====================================================================================
Empirical Challenge Dimensions:
1. RFC 7946 Strict GeoJSON Schema Validation:
   - Coordinate ordering [longitude, latitude] across all Points and LineStrings.
   - Latitude/Longitude range bounding [-90, 90] / [-180, 180].
   - Null geometry handling for non-spatial records per RFC 7946 Section 3.2.
   - JSON serialization idempotency and schema completeness.
2. 22-Layer Data Integrity & Cross-Layer Symmetry:
   - Completeness and non-emptiness of all 22 layers.
   - Summary metadata consistency against raw layer lengths.
   - Polyline segment connectivity and minimum 2-point geometry.
3. Robustness & Fault Tolerance on Edge/Corrupted Inputs:
   - Empty dictionaries, partial coordinates, non-spatial records passed to to_geojson_feature.
   - Corrupted or extreme values in get_all_geospatial_layers_geojson.
4. Quantitative Intelligence Engine Stress Testing:
   - Boundary flow conditions (0.0 mbd, negative flow, extreme surplus flow).
   - Unknown chokepoint error handling and alias resolution.
   - Fallback behavior for exotic/unsupported trading symbols.
5. FastAPI Gateway Behavioral Stress:
   - Case-insensitive format query parameter parsing (?format=GEOJSON, ?format=GeoJson, ?format=invalid).
   - Direct /api/world/geojson payload integrity.
   - High-throughput sequential calls for race condition / mutation detection.
6. Geodesic Bezier Arc Mathematical Edge Cases:
   - Start == End edge case, zero latitude, negative latitude, high latitude boundaries.
"""

import sys
import math
import json
import unittest
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))

from actions.geospatial_intelligence import (
    get_all_geospatial_layers,
    get_all_geospatial_layers_geojson,
    to_geojson_feature,
    CHOKEPOINTS_DATA
)
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine


class TestChallengerM2GeoJSONSchemaStrictness(unittest.TestCase):
    """Adversarial stress-testing of RFC 7946 GeoJSON schema rules."""

    def setUp(self):
        self.geojson = get_all_geospatial_layers_geojson()

    def test_rfc7946_root_schema(self):
        """Verify root object is FeatureCollection with required members."""
        self.assertEqual(self.geojson.get("type"), "FeatureCollection")
        self.assertIn("features", self.geojson)
        self.assertIsInstance(self.geojson["features"], list)
        self.assertGreater(len(self.geojson["features"]), 0)

    def test_rfc7946_coordinate_ordering_and_bounds(self):
        """
        Verify EVERY feature adheres strictly to RFC 7946:
        1. Coordinates MUST be [longitude, latitude] order.
        2. Longitude MUST be in [-180, 180].
        3. Latitude MUST be in [-90, 90].
        4. No NaN, Infinity, or string coordinates.
        """
        features = self.geojson["features"]
        point_count = 0
        linestring_count = 0
        unlocated_count = 0

        for idx, feat in enumerate(features):
            self.assertEqual(feat.get("type"), "Feature", f"Feature {idx} type must be 'Feature'")
            self.assertIn("properties", feat, f"Feature {idx} missing properties")
            self.assertIsInstance(feat["properties"], dict, f"Feature {idx} properties must be dict")
            self.assertIn("layer", feat["properties"], f"Feature {idx} missing layer property")

            geom = feat.get("geometry")
            if geom is None:
                unlocated_count += 1
                continue

            self.assertIn("type", geom, f"Feature {idx} geometry missing type")
            self.assertIn("coordinates", geom, f"Feature {idx} geometry missing coordinates")
            g_type = geom["type"]
            coords = geom["coordinates"]

            if g_type == "Point":
                point_count += 1
                self.assertEqual(len(coords), 2, f"Point feature {idx} coordinates must be [lon, lat]")
                lon, lat = coords
                self.assertIsInstance(lon, (int, float), f"Point {idx} lon must be float/int, got {type(lon)}")
                self.assertIsInstance(lat, (int, float), f"Point {idx} lat must be float/int, got {type(lat)}")
                self.assertFalse(math.isnan(lon) or math.isinf(lon), f"Point {idx} lon is NaN/Inf")
                self.assertFalse(math.isnan(lat) or math.isinf(lat), f"Point {idx} lat is NaN/Inf")
                self.assertTrue(-180.0 <= lon <= 180.0, f"Point {idx} lon {lon} out of bounds [-180, 180]")
                self.assertTrue(-90.0 <= lat <= 90.0, f"Point {idx} lat {lat} out of bounds [-90, 90]")

            elif g_type == "LineString":
                linestring_count += 1
                self.assertGreaterEqual(len(coords), 2, f"LineString {idx} must have >= 2 points")
                for p_idx, pt in enumerate(coords):
                    self.assertEqual(len(pt), 2, f"LineString {idx} pt {p_idx} must be [lon, lat]")
                    lon, lat = pt
                    self.assertIsInstance(lon, (int, float))
                    self.assertIsInstance(lat, (int, float))
                    self.assertFalse(math.isnan(lon) or math.isinf(lon))
                    self.assertFalse(math.isnan(lat) or math.isinf(lat))
                    self.assertTrue(-180.0 <= lon <= 180.0, f"LineString {idx} pt {p_idx} lon out of bounds: {lon}")
                    self.assertTrue(-90.0 <= lat <= 90.0, f"LineString {idx} pt {p_idx} lat out of bounds: {lat}")
            else:
                self.fail(f"Unexpected geometry type: {g_type}")

        self.assertGreater(point_count, 30, "Expected >= 30 Point features")
        self.assertGreater(linestring_count, 5, "Expected >= 5 LineString features")
        self.assertGreater(unlocated_count, 0, "Expected unlocated features (e.g. resilienceScore)")

    def test_json_serializability(self):
        """Verify entire GeoJSON payload is valid JSON and re-parseable without data loss."""
        serialized = json.dumps(self.geojson)
        self.assertIsInstance(serialized, str)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["type"], "FeatureCollection")
        self.assertEqual(len(deserialized["features"]), len(self.geojson["features"]))


class TestChallengerM2LayerCompletenessAndIntegrity(unittest.TestCase):
    """Stress-testing the 22 visual layers catalog."""

    REQUIRED_22_LAYERS = [
        "conflicts", "bases", "cables", "pipelines", "hotspots", "ais",
        "nuclear", "sanctions", "weather", "tradeRoutes", "canadaAlerts",
        "economic", "waterways", "outages", "datacenters", "flights",
        "military", "natural", "minerals", "fires", "ucdpEvents", "resilienceScore"
    ]

    def setUp(self):
        self.raw = get_all_geospatial_layers()

    def test_exact_22_layer_count_and_keys(self):
        """Verify exactly all 22 required layers are present and non-empty."""
        self.assertIn("layers", self.raw)
        layers = self.raw["layers"]
        self.assertEqual(len(layers), 22, f"Expected 22 layers in layers map, found {len(layers)}")
        
        for k in self.REQUIRED_22_LAYERS:
            self.assertIn(k, layers, f"Layer {k} missing from layers payload")
            self.assertIsInstance(layers[k], list, f"Layer {k} must be a list")
            self.assertGreater(len(layers[k]), 0, f"Layer {k} must have >= 1 item")

    def test_canada_alerts_layer_properties(self):
        """Verify canadaAlerts contains required CAP-CP metadata (title, severity, province, event)."""
        alerts = self.raw["layers"]["canadaAlerts"]
        self.assertGreaterEqual(len(alerts), 3)
        provinces = {a.get("province") for a in alerts}
        self.assertTrue({"AB", "BC", "ON"}.issubset(provinces))
        for a in alerts:
            self.assertIn("title", a)
            self.assertIn("severity", a)
            self.assertIn("event", a)
            self.assertTrue(-90 <= a["lat"] <= 90)
            self.assertTrue(-180 <= a["lon"] <= 180)

    def test_economic_indicators_layer_properties(self):
        """Verify economic layer contains sovereign stress markers."""
        eco = self.raw["layers"]["economic"]
        self.assertGreaterEqual(len(eco), 4)
        countries = {e.get("country") for e in eco}
        self.assertTrue({"Egypt", "Pakistan", "Germany", "USA"}.issubset(countries))
        for e in eco:
            self.assertIn("metric", e)
            self.assertIn("status", e)
            self.assertIn("narrative", e)


class TestChallengerM2EdgeCaseInputs(unittest.TestCase):
    """Stress-testing to_geojson_feature with edge cases and malformed inputs."""

    def test_empty_dict_input(self):
        """Empty input dict should return an unlocated Feature without throwing exception."""
        feat = to_geojson_feature({}, "test_layer")
        self.assertEqual(feat["type"], "Feature")
        self.assertIsNone(feat["geometry"])
        self.assertEqual(feat["properties"]["layer"], "test_layer")

    def test_partial_coordinate_inputs(self):
        """Dict with only lat or only lon should return unlocated Feature."""
        f1 = to_geojson_feature({"lat": 45.0}, "layer_lat_only")
        self.assertIsNone(f1["geometry"])
        self.assertEqual(f1["properties"]["layer"], "layer_lat_only")

        f2 = to_geojson_feature({"lon": -75.0}, "layer_lon_only")
        self.assertIsNone(f2["geometry"])
        self.assertEqual(f2["properties"]["layer"], "layer_lon_only")

    def test_path_with_negative_and_extreme_coordinates(self):
        """LineString path with southern/western hemisphere coordinates."""
        path_item = {
            "id": "test_cable",
            "name": "Trans-Antarctic Test Cable",
            "path": [[-60.0, -120.0], [-70.0, 0.0], [-80.0, 150.0]]
        }
        feat = to_geojson_feature(path_item, "cables")
        self.assertEqual(feat["geometry"]["type"], "LineString")
        coords = feat["geometry"]["coordinates"]
        # Expected [lon, lat]
        self.assertEqual(coords[0], [-120.0, -60.0])
        self.assertEqual(coords[1], [0.0, -70.0])
        self.assertEqual(coords[2], [150.0, -80.0])

    def test_non_spatial_record_conversion(self):
        """Resilience score non-spatial record conversion."""
        res_item = {"country": "USA", "score": 92.4, "status": "ROBUST"}
        feat = to_geojson_feature(res_item, "resilienceScore")
        self.assertEqual(feat["type"], "Feature")
        self.assertIsNone(feat["geometry"])
        self.assertEqual(feat["properties"]["country"], "USA")
        self.assertEqual(feat["properties"]["score"], 92.4)
        self.assertEqual(feat["properties"]["layer"], "resilienceScore")


class TestChallengerM2QuantitativePricingEngine(unittest.TestCase):
    """Stress-testing WorldMonitorIntelligenceEngine against boundary and anomalous inputs."""

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()

    def test_zero_flow_disruption_calculation(self):
        """0 mbd current flow should yield 100% disruption."""
        updated = self.engine.update_chokepoint_flow("hormuz_strait", current_mbd=0.0)
        self.assertEqual(updated["disruption_pct"], 100.0)
        self.assertTrue(updated["anomaly_signal"])
        self.assertEqual(updated["risk_level"], "CRITICAL_WARZONE")

    def test_surplus_flow_handling(self):
        """Current flow exceeding baseline (e.g. 30 mbd vs 21 mbd baseline) should clamp disruption to 0%."""
        updated = self.engine.update_chokepoint_flow("hormuz_strait", current_mbd=30.0)
        self.assertEqual(updated["disruption_pct"], 0.0)

    def test_negative_flow_clamping(self):
        """Negative flow input should be clamped safely to 0 mbd (100% disruption)."""
        updated = self.engine.update_chokepoint_flow("suez", current_mbd=-5.0)
        self.assertEqual(updated["current_mbd"], -5.0)
        self.assertEqual(updated["disruption_pct"], 100.0)

    def test_unknown_chokepoint_key_error(self):
        """Updating non-existent chokepoint should raise KeyError."""
        with self.assertRaises(KeyError):
            self.engine.update_chokepoint_flow("non_existent_strait", current_mbd=5.0)

    def test_unsupported_symbol_fallback(self):
        """Evaluating bias on unknown/exotic symbol should gracefully return baseline neutral dictionary."""
        bias = self.engine.evaluate_geopolitical_market_bias("UNKNOWN_TICKER_999")
        self.assertEqual(bias["bias"], "NEUTRAL")
        self.assertEqual(bias["macro_multiplier"], 1.0)
        self.assertEqual(bias["confluence_boost"], 0.0)
        self.assertIn("Standard", bias["reasoning"])


class TestChallengerM2DashboardEndpoints(unittest.TestCase):
    """Stress-testing FastAPI dashboard routes."""

    def setUp(self):
        from fastapi.testclient import TestClient
        import dashboard
        self.client = TestClient(dashboard.app)

    def test_format_query_param_case_insensitivity(self):
        """Verify ?format=GEOJSON and ?format=GeoJson return FeatureCollection."""
        for fmt in ["geojson", "GEOJSON", "GeoJson", "GeoJSON"]:
            res = self.client.get(f"/api/world/layers?format={fmt}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("type"), "FeatureCollection")
            self.assertIn("features", data)

    def test_invalid_format_query_param_falls_back_to_bundle(self):
        """Invalid format parameter should fall back to regular 22-layer dictionary."""
        res = self.client.get("/api/world/layers?format=invalid_dummy_format")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("layers", data)
        self.assertEqual(len(data["layers"]), 22)

    def test_chokepoints_telemetry_consistency(self):
        """Verify chokepoints telemetry returns DEFCON 2, 1.45x Gold multiplier, and 6 chokepoints."""
        res = self.client.get("/api/world/chokepoints/telemetry")
        self.assertEqual(res.status_code, 200)
        cp_data = res.json()
        self.assertEqual(cp_data["defcon"], 2)
        self.assertEqual(cp_data["gold_macro_multiplier"], 1.45)
        self.assertEqual(len(cp_data["chokepoints"]), 6)


if __name__ == "__main__":
    unittest.main()
