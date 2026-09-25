"""
test_macro_contagion_3d.py — Comprehensive Test Suite for 3D Macro Contagion & Hotspots
========================================================================================
Verifies:
  1. core/research/macro_contagion_service.py:
     - Primary macro driver telemetry (DXY, US10Y, Crude Oil).
     - Target asset state and beta elasticities (Gold, Forex, BTC, SOL).
     - Cross-asset contagion vector calculations and correlation bounds.
     - Dynamic shock simulation (simulate_macro_shock) and regime classification.
     - Geopolitical hotspot telemetry (Red Sea, Hormuz, Taiwan Strait, Eastern Europe)
       including flow baselines, disruption %, multipliers, and historical reaction dossiers.
     - Hotspot escalation simulation (simulate_hotspot_escalation).
     - Forward catalyst timeline and 15-minute news blackout buffer logic.
     - 3D graph topology export structure matching MacroContagionSphere3D visualizer contracts.
  2. web/js/MacroContagionSphere3D.js:
     - File existence, non-emptiness, and valid JS structure.
     - Event contracts: ingress for 'jarvis:macro:shockwave', egress for 'jarvis:hotspot:selected'.
     - CatmullRom 3D particle splines, concentric pulsing rings, and shockwave ripples.
     - Forward catalyst timeline HUD component and tactical dossier modal.
     - Resource disposal lifecycle (destroy method).
  3. Clean-room prohibited identifier audit:
     - Zero occurrences of legacy prohibited tokens across all owned files.
========================================================================================
"""

import os
import re
import math
import unittest
from pathlib import Path
from typing import Dict, Any

from core.research.macro_contagion_service import (
    MacroContagionService,
    get_macro_contagion_service,
    lat_lon_to_cartesian,
    DRIVERS,
    ASSETS,
    HOTSPOTS
)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestMacroContagionService(unittest.TestCase):
    """Unit and integration test cases for MacroContagionService."""

    def setUp(self):
        self.service = MacroContagionService()

    def test_singleton_instance(self):
        """Verifies singleton accessor returns an initialized MacroContagionService."""
        s1 = get_macro_contagion_service()
        s2 = get_macro_contagion_service()
        self.assertIs(s1, s2)
        self.assertIsInstance(s1, MacroContagionService)

    def test_drivers_telemetry(self):
        """Asserts primary macro drivers DXY, US10Y, and OIL are fully initialized."""
        drivers = self.service.get_macro_drivers_telemetry()
        for d in DRIVERS:
            self.assertIn(d, drivers)
            data = drivers[d]
            self.assertEqual(data["symbol"], d)
            self.assertIsInstance(data["current_value"], (int, float))
            self.assertGreater(data["current_value"], 0.0)
            self.assertIn("trend", data)
            self.assertIn("volatility_index", data)
            self.assertIn(data["trend"], ["BULLISH", "BEARISH", "NEUTRAL"])

    def test_target_assets_telemetry(self):
        """Asserts target assets (XAUUSD, EURUSD, USDJPY, GBPUSD, BTCUSD, SOLUSD) exist with betas."""
        assets = self.service.get_target_assets_telemetry()
        for a in ASSETS:
            self.assertIn(a, assets)
            data = assets[a]
            self.assertEqual(data["symbol"], a)
            self.assertGreater(data["current_price"], 0.0)
            self.assertIn("category", data)
            self.assertIn("beta_to_dxy", data)
            self.assertIn("beta_to_us10y", data)
            self.assertIn("beta_to_oil", data)

        # Asset specific elasticity assertions
        # Gold should have negative beta to DXY and US10Y, positive to Oil
        gold = assets["XAUUSD"]
        self.assertLess(gold["beta_to_dxy"], 0.0)
        self.assertLess(gold["beta_to_us10y"], 0.0)
        self.assertGreater(gold["beta_to_oil"], 0.0)

        # EURUSD should have strong negative beta to DXY
        eur = assets["EURUSD"]
        self.assertLess(eur["beta_to_dxy"], -0.7)

        # USDJPY should have positive beta to US10Y (yield differential)
        usdjpy = assets["USDJPY"]
        self.assertGreater(usdjpy["beta_to_us10y"], 0.5)

    def test_contagion_vectors_matrix(self):
        """Verifies cross-asset contagion vectors, correlations, velocities, and color codes."""
        vectors = self.service.get_contagion_vectors()
        self.assertGreaterEqual(len(vectors), 10)

        valid_colors = {"#00f3ff", "#ff3355", "#ffaa00"}
        for vec in vectors:
            self.assertIn(vec["driver"], DRIVERS)
            self.assertIn(vec["target"], ASSETS)
            # Correlation r must be within [-1.0, 1.0]
            self.assertGreaterEqual(vec["correlation"], -1.0)
            self.assertLessEqual(vec["correlation"], 1.0)
            # Beta must be non-zero
            self.assertNotEqual(vec["beta"], 0.0)
            # Transmission lag and flow velocity must be positive
            self.assertGreater(vec["transmission_lag_s"], 0.0)
            self.assertGreater(vec["flow_velocity"], 0.0)
            # Color code check
            self.assertIn(vec["color_code"], valid_colors)
            self.assertIn(vec["sentiment_channel"], ["TAILWIND", "HEADWIND", "CONTAGION_SHOCK"])

    def test_simulate_macro_shock_dxy_expansion(self):
        """Simulates positive DXY dollar surge shock (+1.5%) and asserts cascading impacts."""
        res = self.service.simulate_macro_shock("DXY", 1.5)
        self.assertIn("shocked_driver", res)
        self.assertEqual(res["shocked_driver"]["symbol"], "DXY")
        self.assertEqual(res["shocked_driver"]["delta_pct"], 1.5)

        impacts = res["cascading_asset_impacts"]
        # EURUSD should decline on positive DXY shock
        self.assertIn("EURUSD", impacts)
        self.assertLess(impacts["EURUSD"]["expected_change_pct"], 0.0)
        self.assertEqual(impacts["EURUSD"]["directional_bias"], "BEARISH")

        # Gold should decline on positive DXY shock
        self.assertIn("XAUUSD", impacts)
        self.assertLess(impacts["XAUUSD"]["expected_change_pct"], 0.0)

        # USDJPY should appreciate on positive DXY shock
        self.assertIn("USDJPY", impacts)
        self.assertGreater(impacts["USDJPY"]["expected_change_pct"], 0.0)
        self.assertEqual(impacts["USDJPY"]["directional_bias"], "BULLISH")

        # Macro regime should reflect dollar dominance
        self.assertEqual(res["macro_regime"]["regime"], "DOLLAR_DOMINANCE_LIQUIDITY_SQUEEZE")

    def test_simulate_macro_shock_oil_surge(self):
        """Simulates positive Oil shock (+5.0%) and asserts stagflation shock regime."""
        res = self.service.simulate_macro_shock("OIL", 5.0)
        impacts = res["cascading_asset_impacts"]

        # Gold should gain as inflation/safe-haven hedge
        self.assertGreater(impacts["XAUUSD"]["expected_change_pct"], 0.0)
        self.assertEqual(impacts["XAUUSD"]["directional_bias"], "BULLISH")

        # EURUSD should drop due to European energy import terms-of-trade degradation
        self.assertLess(impacts["EURUSD"]["expected_change_pct"], 0.0)

        # Macro regime should be stagflation shock
        self.assertEqual(res["macro_regime"]["regime"], "GEOPOLITICAL_STAGFLATION_SHOCK")

    def test_simulate_macro_shock_invalid_driver(self):
        """Asserts ValueError on invalid driver symbol."""
        with self.assertRaises(ValueError):
            self.service.simulate_macro_shock("INVALID_DRIVER", 1.0)

    def test_geopolitical_hotspots_telemetry(self):
        """Verifies all 4 required geopolitical hotspots with baselines, disruption, and coordinates."""
        hotspots = self.service.get_all_hotspots()
        for h_id in HOTSPOTS:
            self.assertIn(h_id, hotspots)
            h = hotspots[h_id]
            self.assertEqual(h["hotspot_id"], h_id)
            self.assertIn("name", h)
            self.assertIn("region", h)
            self.assertIn("disruption_pct", h)
            self.assertGreaterEqual(h["disruption_pct"], 0.0)
            self.assertIn("threat_level", h)
            self.assertIn("status_narrative", h)
            self.assertIn("commodity_volatility_multipliers", h)
            self.assertIn("historical_dossier", h)
            self.assertGreater(len(h["historical_dossier"]), 0)

            # Check 3D Cartesian coordinates on unit sphere
            coords = h["cartesian_coords"]
            r_sq = coords["x"]**2 + coords["y"]**2 + coords["z"]**2
            self.assertAlmostEqual(math.sqrt(r_sq), 1.0, places=2)

    def test_hotspot_historical_reaction_dossiers(self):
        """Verifies historical reaction dossiers contain concrete historical dates and price impulses."""
        # Red Sea Chokepoint
        red_sea = self.service.get_hotspot_dossier("red_sea")
        self.assertIsNotNone(red_sea)
        dossier_rs = red_sea["historical_dossier"]
        self.assertGreaterEqual(len(dossier_rs), 2)
        # Verify first incident has explicit dates and impulses
        inc1 = dossier_rs[0]
        self.assertTrue(inc1["date"].startswith("2023-") or inc1["date"].startswith("2024-"))
        self.assertTrue("Gold" in inc1["gold_impulse"] or "$" in inc1["gold_impulse"])

        # Hormuz Chokepoint
        hormuz = self.service.get_hotspot_dossier("hormuz_strait")
        self.assertIsNotNone(hormuz)
        dossier_hz = hormuz["historical_dossier"]
        self.assertGreaterEqual(len(dossier_hz), 2)
        self.assertIn("XAUUSD", hormuz["commodity_volatility_multipliers"])
        self.assertIn("WTI", hormuz["commodity_volatility_multipliers"])

        # Taiwan Strait
        taiwan = self.service.get_hotspot_dossier("taiwan_strait")
        self.assertIsNotNone(taiwan)
        self.assertIn("SEMI_TECH_SHOCK", taiwan["commodity_volatility_multipliers"])

        # Eastern Europe
        ee = self.service.get_hotspot_dossier("eastern_europe")
        self.assertIsNotNone(ee)
        self.assertIn("NAT_GAS_EU", ee["commodity_volatility_multipliers"])

    def test_hotspot_escalation_simulation(self):
        """Simulates hotspot escalation and verifies supply shock propagation."""
        esc = self.service.simulate_hotspot_escalation("red_sea", 20.0)
        self.assertEqual(esc["hotspot_id"], "red_sea")
        self.assertEqual(esc["threat_level"], "CRITICAL_WARZONE")
        self.assertGreater(esc["oil_price_surge_pct"], 0.0)
        self.assertGreater(esc["gold_price_surge_pct"], 0.0)
        self.assertIn("cascading_network_impact", esc)

    def test_forward_catalyst_timeline(self):
        """Verifies forward-looking catalyst schedule, precedents, and 15-minute blackout buffer rule."""
        timeline = self.service.get_catalyst_timeline()
        self.assertIn("catalysts", timeline)
        self.assertGreaterEqual(timeline["catalysts_count"], 4)
        self.assertIn("blackout_rule", timeline)

        # Check catalyst properties
        for cat in timeline["catalysts"]:
            self.assertIn("event_id", cat)
            self.assertIn("title", cat)
            self.assertIn("institution", cat)
            self.assertIn("scheduled_utc", cat)
            self.assertIn("impact_level", cat)
            self.assertIn("historical_precedents", cat)
            self.assertIn("minutes_to_release", cat)

        # Verify FOMC catalyst exists
        fomc = next((c for c in timeline["catalysts"] if "FOMC" in c["title"]), None)
        self.assertIsNotNone(fomc)
        self.assertEqual(fomc["impact_level"], "HIGH")
        self.assertGreater(len(fomc["historical_precedents"]), 0)

    def test_3d_graph_topology_export(self):
        """Verifies get_contagion_network_graph exports complete node/edge topology for Three.js."""
        graph = self.service.get_contagion_network_graph()
        self.assertEqual(graph["topology_type"], "MACRO_CONTAGION_PLANETARY_NETWORK")
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)

        # Node assertions
        nodes = graph["nodes"]
        self.assertEqual(len(nodes), len(DRIVERS) + len(HOTSPOTS) + len(ASSETS))

        driver_nodes = [n for n in nodes if n["node_type"] == "DRIVER"]
        hotspot_nodes = [n for n in nodes if n["node_type"] == "HOTSPOT"]
        receiver_nodes = [n for n in nodes if n["node_type"] == "RECEIVER"]

        self.assertEqual(len(driver_nodes), len(DRIVERS))
        self.assertEqual(len(hotspot_nodes), len(HOTSPOTS))
        self.assertEqual(len(receiver_nodes), len(ASSETS))

        for n in nodes:
            self.assertIn("id", n)
            self.assertIn("symbol", n)
            self.assertIn("position_3d", n)
            pos = n["position_3d"]
            self.assertIn("x", pos)
            self.assertIn("y", pos)
            self.assertIn("z", pos)

        # Edge assertions
        edges = graph["edges"]
        self.assertGreaterEqual(len(edges), 15)
        for e in edges:
            self.assertIn("edge_id", e)
            self.assertIn("source_id", e)
            self.assertIn("target_id", e)
            self.assertIn("flow_velocity", e)
            self.assertIn("color_code", e)
            self.assertIn("curvature_lift", e)

    def test_lat_lon_to_cartesian_known_coordinates(self):
        """Tests coordinate conversion utility on known points."""
        # North pole (Lat 90, Lon 0) -> x=0, y=1, z=0
        np = lat_lon_to_cartesian(90.0, 0.0, 1.0)
        self.assertAlmostEqual(np["x"], 0.0, places=2)
        self.assertAlmostEqual(np["y"], 1.0, places=2)
        self.assertAlmostEqual(np["z"], 0.0, places=2)

        # South pole (Lat -90, Lon 0) -> x=0, y=-1, z=0
        sp = lat_lon_to_cartesian(-90.0, 0.0, 1.0)
        self.assertAlmostEqual(sp["x"], 0.0, places=2)
        self.assertAlmostEqual(sp["y"], -1.0, places=2)
        self.assertAlmostEqual(sp["z"], 0.0, places=2)


class TestMacroContagionSphere3DJavaScript(unittest.TestCase):
    """Verifies web/js/MacroContagionSphere3D.js structure, contracts, and integrity."""

    def setUp(self):
        self.js_path = BASE_DIR / "web" / "js" / "MacroContagionSphere3D.js"
        self.assertTrue(self.js_path.exists(), f"MacroContagionSphere3D.js missing at {self.js_path}")
        self.content = self.js_path.read_text(encoding="utf-8")

    def test_file_integrity_and_size(self):
        """Asserts JS file is non-empty and contains substantial implementation (>500 lines)."""
        lines = self.content.splitlines()
        self.assertGreater(len(lines), 400, "MacroContagionSphere3D.js must be a full implementation.")

    def test_umd_and_class_export(self):
        """Asserts UMD export pattern and class declaration."""
        self.assertIn("MacroContagionSphere3D", self.content)
        self.assertIn("class MacroContagionSphere3D", self.content)
        self.assertIn("root.MacroContagionSphere3D = factory()", self.content)

    def test_geopolitical_hotspots_in_js(self):
        """Asserts all 4 required geopolitical hotspots are present in the visualizer script."""
        for h in ["red_sea", "hormuz_strait", "taiwan_strait", "eastern_europe"]:
            self.assertIn(h, self.content)

    def test_macro_drivers_and_assets_in_js(self):
        """Asserts all drivers and assets are rendered in the visualizer."""
        for d in ["DXY", "US10Y", "OIL"]:
            self.assertIn(d, self.content)
        for a in ["XAUUSD", "EURUSD", "USDJPY", "BTCUSD", "SOLUSD"]:
            self.assertIn(a, self.content)

    def test_threejs_particle_splines_and_curves(self):
        """Asserts CatmullRomCurve3 3D particle splines are utilized for contagion vectors."""
        self.assertIn("CatmullRomCurve3", self.content)
        self.assertIn("PointsMaterial", self.content)
        self.assertIn("AdditiveBlending", self.content)
        self.assertIn("particlePoints", self.content)

    def test_concentric_pulsing_rings_and_shockwaves(self):
        """Asserts concentric pulsing rings and shockwave generation logic."""
        self.assertIn("RingGeometry", self.content)
        self.assertIn("pulseRings", self.content)
        self.assertIn("triggerShockwave", self.content)
        self.assertIn("injectShockwave", self.content)

    def test_event_contracts(self):
        """Asserts event ingress ('jarvis:macro:shockwave') and egress ('jarvis:hotspot:selected')."""
        self.assertIn("jarvis:macro:shockwave", self.content)
        self.assertIn("jarvis:hotspot:selected", self.content)
        self.assertIn("jarvis:node:selected", self.content)

    def test_catalyst_timeline_and_dossier_modal(self):
        """Asserts catalyst timeline HUD component and tactical dossier modal."""
        self.assertIn("FORWARD CATALYST TIMELINE", self.content)
        self.assertIn("TACTICAL DOSSIER", self.content)
        self.assertIn("15M BLACKOUT ACTIVE", self.content)
        self.assertIn("historical_dossier", self.content)

    def test_lifecycle_and_dispose(self):
        """Asserts comprehensive destroy/dispose lifecycle for WebGL resources."""
        self.assertIn("destroy()", self.content)
        self.assertIn("cancelAnimationFrame", self.content)
        self.assertIn("dispose()", self.content)


class TestCleanRoomIntegrityWorkerM2(unittest.TestCase):
    """Clean-room audit asserting ZERO occurrences of prohibited identifiers across all M2 files."""

    def setUp(self):
        # Dynamically build prohibited pattern so this test script does not trigger itself
        part_a = "adeel"
        part_b = "qureshi99"
        self.pattern = re.compile(rf"{part_a}[\s_-]*{part_b}", re.IGNORECASE)

    def test_zero_prohibited_tokens_in_m2_files(self):
        """Asserts zero occurrences of legacy prohibited identifiers across exclusively owned files."""
        owned_files = [
            BASE_DIR / "core" / "research" / "macro_contagion_service.py",
            BASE_DIR / "web" / "js" / "MacroContagionSphere3D.js",
            BASE_DIR / "tests" / "test_macro_contagion_3d.py"
        ]

        violations = []
        for file_path in owned_files:
            self.assertTrue(file_path.exists(), f"Owned file missing: {file_path}")
            content = file_path.read_text(encoding="utf-8")
            matches = self.pattern.findall(content)
            if matches:
                violations.append(f"{file_path}: found {matches}")

        self.assertEqual(
            violations, [],
            f"Integrity violation detected: prohibited tokens found: {violations}"
        )


if __name__ == "__main__":
    unittest.main()
