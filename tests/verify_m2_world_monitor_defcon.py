"""
verify_m2_world_monitor_defcon.py — Comprehensive Verification Suite for Milestone M2.
========================================================================================
Verifies Subsystem R2: World Monitor and Geopolitical DEFCON Engine:
1. Maritime Chokepoints and Geopolitical Risk Telemetry:
   - All 6 strategic maritime chokepoints verified active:
     Hormuz, Bab el-Mandeb, Suez Canal, Malacca, Panama, Bosporus and Dardanelles.
   - Flow baseline, disruption calculations, risk levels.
   - 4-pillar Country Instability Index (CII: unrest, conflict, security, info).
   - Polymarket geopolitical odds ingestion and filtering.
   - Composite risk formula: 0.40*max_cii + 0.20*avg_cii + 0.25*max_disruption + 0.15*max_poly.
2. DEFCON Engine and Macro Multipliers:
   - DEFCON 1 through 5 scoring.
   - Gold (XAUUSD): 1.45x multiplier at DEFCON 2 / 1.35x at DEFCON 3 with +0.50 confluence boost.
   - Crude Oil (WTI): 1.50x multiplier at DEFCON 2 / 1.35x at DEFCON 3 with +0.45 confluence boost
     and +$8.50/bbl structural risk premium.
3. Position Sizing Wiring and Hard Ceilings:
   - Scaling base lot sizes with macro multipliers strictly clamps to funded account hard ceilings:
     0.10L Gold, 0.20L Forex, 0.01L Crypto, and $100 dollar cap.
   - Counter-macro conflict veto: selling Gold during critical chokepoint crisis is vetoed.
   - Integration with actions/mq3_trading._execute_direct_trade.
4. Windows cp1252 Console Encoding Safety:
   - Zero UnicodeEncodeError: 'charmap' crashes on cp1252 consoles.
5. Dashboard Telemetry Endpoints:
   - GET /api/world/chokepoints/telemetry and GET /api/geopolitical/fusion return valid data.
"""

import unittest
import sys
from pathlib import Path

# Setup paths
JARVIS_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = JARVIS_ROOT / "MQ3 TRADING BOT"

if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
from actions.geospatial_intelligence import CHOKEPOINTS_DATA, get_chokepoints_telemetry
from core.geopolitical_trading_fusion import geopolitical_fusion, GeopoliticalTradingFusion
from actions.mq3_trading import _execute_direct_trade


class TestMilestoneM2Verification(unittest.TestCase):

    def setUp(self):
        self.engine = WorldMonitorIntelligenceEngine()
        self.fusion = geopolitical_fusion

    # ==========================================================================
    # 1. MARITIME CHOKEPOINTS TELEMETRY & COMPOSITE RISK
    # ==========================================================================

    def test_01_all_six_strategic_maritime_chokepoints_active(self):
        """Verifies all 6 strategic maritime chokepoints exist and are active in both engines."""
        required_chokepoints = [
            "hormuz",
            "bab_el_mandeb",
            "suez",
            "malacca",
            "panama",
            "bosporus",
        ]
        # In geospatial_intelligence
        geo_cp_ids = [cp["id"] for cp in CHOKEPOINTS_DATA]
        for req in required_chokepoints:
            self.assertIn(req, geo_cp_ids, f"Missing chokepoint in geospatial: {req}")

        # In WorldMonitorIntelligenceEngine
        wm_cp = self.engine.chokepoints
        for req in ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "panama_canal", "bosporus_dardanelles"]:
            self.assertIn(req, wm_cp, f"Missing chokepoint in intelligence engine: {req}")
            self.assertGreater(wm_cp[req]["baseline_mbd"], 0.0)
            self.assertGreaterEqual(wm_cp[req]["current_mbd"], 0.0)
            self.assertGreaterEqual(wm_cp[req]["disruption_pct"], 0.0)

    def test_02_disruption_percentage_calculation(self):
        """Verifies exact mathematical disruption formula: (1 - current/baseline) * 100%."""
        # Test baseline 21.0, current 14.5 -> disruption 31.0%
        d1 = WorldMonitorIntelligenceEngine.calculate_disruption_percentage(21.0, 14.5)
        self.assertAlmostEqual(d1, 31.0, delta=0.1)

        # Test baseline 8.8, current 2.98 -> disruption 66.1%
        d2 = WorldMonitorIntelligenceEngine.calculate_disruption_percentage(8.8, 2.98)
        self.assertAlmostEqual(d2, 66.1, delta=0.2)

        # Zero baseline artery (e.g. Taiwan container) uses incident scaling
        d_incident = WorldMonitorIntelligenceEngine.calculate_disruption_percentage(0.0, 0.0, incident_count=25)
        self.assertEqual(d_incident, 20.0)

    def test_03_four_pillar_country_instability_index(self):
        """Verifies 4-pillar Country Instability Index (CII) formula."""
        # Weights: 0.20*unrest + 0.40*conflict + 0.25*security + 0.15*information
        components = {
            "unrest": 80.0,
            "conflict": 90.0,
            "security": 70.0,
            "information": 60.0
        }
        expected = 0.20 * 80.0 + 0.40 * 90.0 + 0.25 * 70.0 + 0.15 * 60.0  # 16 + 36 + 17.5 + 9 = 78.5
        calculated = WorldMonitorIntelligenceEngine.calculate_country_instability_score(components)
        self.assertAlmostEqual(calculated, expected, places=1)

    def test_04_global_composite_risk_index_and_defcon(self):
        """Verifies composite risk weighted formula and DEFCON level mapping."""
        brief = self.engine.get_world_intelligence_brief()
        self.assertIn("defcon_level", brief)
        self.assertIn("global_composite_risk_index", brief)
        self.assertEqual(brief["defcon_level"], 2)  # Baseline evaluates to DEFCON 2
        self.assertGreaterEqual(brief["global_composite_risk_index"], 70.0)

        # Verify DEFCON mapping thresholds
        self.assertEqual(WorldMonitorIntelligenceEngine.get_defcon_level(90.0), 1)
        self.assertEqual(WorldMonitorIntelligenceEngine.get_defcon_level(75.0), 2)
        self.assertEqual(WorldMonitorIntelligenceEngine.get_defcon_level(55.0), 3)
        self.assertEqual(WorldMonitorIntelligenceEngine.get_defcon_level(30.0), 4)
        self.assertEqual(WorldMonitorIntelligenceEngine.get_defcon_level(15.0), 5)

    # ==========================================================================
    # 2. MACRO RISK MULTIPLIERS FUSION (GOLD & OIL)
    # ==========================================================================

    def test_05_gold_macro_multiplier_fusion(self):
        """Verifies Gold (XAUUSD): 1.45x at DEFCON 2 / 1.35x at DEFCON 3 with +0.50 confluence boost."""
        gold_bias = self.engine.evaluate_geopolitical_market_bias("XAUUSD")
        self.assertEqual(gold_bias["bias"], "STRONG_BUY")
        self.assertEqual(gold_bias["geopolitical_bias"], "STRONG_BULLISH")
        self.assertEqual(gold_bias["confluence_boost"], 0.50)
        self.assertEqual(gold_bias["macro_multiplier"], 1.45)
        self.assertEqual(gold_bias["strategy_weight_multiplier"], 1.45)

        # Simulate DEFCON 3
        orig_defcon = self.engine.defcon_level
        try:
            self.engine.defcon_level = 3
            defcon3_bias = self.engine.evaluate_geopolitical_market_bias("XAUUSD")
            self.assertEqual(defcon3_bias["macro_multiplier"], 1.35)
            self.assertEqual(defcon3_bias["confluence_boost"], 0.50)
        finally:
            self.engine.defcon_level = orig_defcon

    def test_06_wti_macro_multiplier_and_risk_premium(self):
        """Verifies Crude Oil (WTI): 1.50x at DEFCON 2 / 1.35x at DEFCON 3 with +0.45 confluence boost
        and +$8.50/bbl structural risk premium."""
        wti_bias = self.engine.evaluate_geopolitical_market_bias("WTI")
        self.assertEqual(wti_bias["bias"], "STRONG_BUY")
        self.assertEqual(wti_bias["geopolitical_bias"], "STRONG_BULLISH")
        self.assertEqual(wti_bias["confluence_boost"], 0.45)
        self.assertEqual(wti_bias["macro_multiplier"], 1.50)
        self.assertEqual(wti_bias["strategy_weight_multiplier"], 1.50)
        self.assertEqual(wti_bias.get("oil_geopolitical_risk_premium_usd"), 8.50)

        # Simulate DEFCON 3
        orig_defcon = self.engine.defcon_level
        try:
            self.engine.defcon_level = 3
            defcon3_oil = self.engine.evaluate_geopolitical_market_bias("WTI")
            self.assertEqual(defcon3_oil["macro_multiplier"], 1.35)
            self.assertEqual(defcon3_oil["confluence_boost"], 0.45)
        finally:
            self.engine.defcon_level = orig_defcon

    # ==========================================================================
    # 3. POSITION SIZING WIRING & HARD LOT CEILINGS
    # ==========================================================================

    def test_07_lot_size_scaling_respects_hard_ceilings(self):
        """Verifies lot size scales with macro multiplier while strictly clamping to hard ceilings."""
        # Gold (XAUUSD): base lot 0.08L * 1.45x = 0.116L -> clamped strictly to 0.10L
        gold_scaled = self.fusion.scale_position_size("XAUUSD", base_lot=0.08, base_risk_usd=80.0, action="BUY")
        self.assertTrue(gold_scaled["approved"])
        self.assertEqual(gold_scaled["lot_size"], 0.10)
        self.assertEqual(gold_scaled["hard_lot_ceiling"], 0.10)
        self.assertLessEqual(gold_scaled["lot_size"], 0.10)
        # Dollar risk: 80 * 1.45 = 116.0 -> strictly capped to 100.0
        self.assertEqual(gold_scaled["risk_usd"], 100.0)

        # Gold (XAUUSD): base lot 0.04L * 1.45x = 0.058L -> rounds to 0.06L (below 0.10 ceiling)
        gold_scaled_small = self.fusion.scale_position_size("XAUUSD", base_lot=0.04, base_risk_usd=40.0, action="BUY")
        self.assertEqual(gold_scaled_small["lot_size"], 0.06)
        self.assertEqual(gold_scaled_small["risk_usd"], 58.0)
        self.assertLessEqual(gold_scaled_small["lot_size"], 0.10)

        # Forex (EURUSD): ceiling is 0.20L
        fx_scaled = self.fusion.scale_position_size("EURUSD", base_lot=0.15, base_risk_usd=100.0, action="SELL")
        self.assertTrue(fx_scaled["approved"])
        self.assertLessEqual(fx_scaled["lot_size"], 0.20)
        self.assertLessEqual(fx_scaled["risk_usd"], 100.0)

        # Forex (EURUSD): base lot 0.25L -> clamped to 0.20L
        fx_clamped = self.fusion.scale_position_size("EURUSD", base_lot=0.25, base_risk_usd=100.0, action="BUY")
        self.assertLessEqual(fx_clamped["lot_size"], 0.20)

        # Crypto (BTCUSD): ceiling is 0.01L
        crypto_scaled = self.fusion.scale_position_size("BTCUSD", base_lot=0.05, base_risk_usd=100.0, action="BUY")
        self.assertEqual(crypto_scaled["lot_size"], 0.01)
        self.assertEqual(crypto_scaled["hard_lot_ceiling"], 0.01)

    def test_08_counter_macro_trade_direction_conflict_veto(self):
        """Verifies trade direction conflict veto (e.g. selling Gold during DEFCON 2 / chokepoint crisis)."""
        # Attempting to SELL Gold when macro is STRONG_BUY during DEFCON 2
        appr, mult, reason = self.fusion.evaluate_trade_confluence("XAUUSD", "SELL")
        self.assertFalse(appr, "Selling Gold during critical crisis must be vetoed")
        self.assertEqual(mult, 0.0)
        self.assertIn("COUNTER-MACRO VETO", reason)

        # Sizing engine returns lot_size = 0.0 on veto
        scaled = self.fusion.scale_position_size("XAUUSD", base_lot=0.05, action="SELL")
        self.assertFalse(scaled["approved"])
        self.assertTrue(scaled["vetoed"])
        self.assertEqual(scaled["lot_size"], 0.0)
        self.assertEqual(scaled["risk_usd"], 0.0)

        # Direct execution in mq3_trading blocks trade
        exec_msg = _execute_direct_trade("XAUUSD", "SELL", lots=0.05)
        self.assertIn("[TRADE BLOCKED]", exec_msg)

    # ==========================================================================
    # 4. WINDOWS CP1252 CONSOLE ENCODING SAFETY
    # ==========================================================================

    def test_09_console_cp1252_encoding_resilience(self):
        """Verifies all evaluation messages encode cleanly in Windows cp1252 with zero UnicodeEncodeError."""
        test_cases = [
            ("XAUUSD", "BUY"),
            ("XAUUSD", "SELL"),
            ("WTI", "BUY"),
            ("WTI", "SELL"),
            ("EURUSD", "BUY"),
            ("EURUSD", "SELL"),
            ("BTCUSD", "BUY"),
            ("BTCUSD", "SELL"),
            ("USDJPY", "BUY"),
        ]
        for sym, act in test_cases:
            _, _, reason = self.fusion.evaluate_trade_confluence(sym, act)
            try:
                encoded = reason.encode("cp1252")
                self.assertIsInstance(encoded, bytes)
            except UnicodeEncodeError as uee:
                self.fail(f"UnicodeEncodeError on cp1252 for {sym} {act}: {uee}")

    # ==========================================================================
    # 5. DASHBOARD TELEMETRY ENDPOINTS
    # ==========================================================================

    def test_10_dashboard_telemetry_endpoints(self):
        """Verifies GET /api/world/chokepoints/telemetry and GET /api/geopolitical/fusion."""
        import importlib.util
        from fastapi.testclient import TestClient

        spec = importlib.util.spec_from_file_location("main_dashboard", str(JARVIS_ROOT / "dashboard.py"))
        main_dashboard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_dashboard)
        app = main_dashboard.app

        client = TestClient(app)

        # Endpoint 1: /api/world/chokepoints/telemetry
        r1 = client.get("/api/world/chokepoints/telemetry")
        self.assertEqual(r1.status_code, 200)
        data1 = r1.json()
        self.assertTrue(data1.get("ok"))
        self.assertIn("defcon_level", data1)
        self.assertIn("chokepoints", data1)
        self.assertGreaterEqual(len(data1["chokepoints"]), 6)
        self.assertIn("macro_bias", data1)
        self.assertIn("XAUUSD", data1["macro_bias"])
        self.assertIn("WTI", data1["macro_bias"])

        # Endpoint 2: /api/geopolitical/fusion
        r2 = client.get("/api/geopolitical/fusion")
        self.assertEqual(r2.status_code, 200)
        data2 = r2.json()
        self.assertTrue(data2.get("ok"))
        self.assertEqual(data2["defcon_level"], 2)
        self.assertAlmostEqual(data2["macro_bias"]["XAUUSD"]["macro_multiplier"], 1.45, places=2)
        self.assertAlmostEqual(data2["macro_bias"]["WTI"]["macro_multiplier"], 1.50, places=2)

    def test_11_dashboard_chokepoint_update_persistence(self):
        """Verifies POST /api/world/chokepoints/update persists across subsequent GET telemetry requests."""
        import importlib.util
        from fastapi.testclient import TestClient

        spec = importlib.util.spec_from_file_location("main_dashboard", str(JARVIS_ROOT / "dashboard.py"))
        main_dashboard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_dashboard)
        app = main_dashboard.app
        client = TestClient(app)

        # 1. Warm up telemetry
        r_init = client.get("/api/world/chokepoints/telemetry")
        self.assertEqual(r_init.status_code, 200)

        # 2. Update Hormuz Strait to 0.0 flow
        r_post = client.post("/api/world/chokepoints/update", json={
            "id": "hormuz_strait",
            "current_mbd": 0.0,
            "incident_count": 45,
            "risk_level": "CRITICAL_WARZONE"
        })
        self.assertEqual(r_post.status_code, 200)
        post_data = r_post.json()
        self.assertTrue(post_data.get("ok"))
        self.assertEqual(post_data["chokepoint"]["flow_pct_of_baseline"], 0.0)
        self.assertEqual(post_data["chokepoint"]["disruption_pct"], 100.0)

        # 3. Read back telemetry to confirm persistence
        r_get = client.get("/api/world/chokepoints/telemetry")
        self.assertEqual(r_get.status_code, 200)
        get_data = r_get.json()
        self.assertTrue(get_data.get("ok"))
        hormuz_cp = next(c for c in get_data["chokepoints"] if "hormuz" in c["id"])
        self.assertEqual(hormuz_cp["flow_pct"], 0.0)
        self.assertEqual(hormuz_cp["disruption_pct"], 100.0)

    def test_12_lowercase_symbol_cleaning_crypto_and_crude(self):
        """Verifies lowercase symbols ('btcusd', 'crude') are cleanly handled without ticker corruption."""
        # Case A: Lowercase crypto 'btcusd' must enforce CRYPTO 0.01L ceiling
        res_btc = self.fusion.scale_position_size("btcusd", base_lot=0.50, base_risk_usd=100.0, action="BUY")
        self.assertTrue(res_btc["approved"])
        self.assertFalse(res_btc["vetoed"])
        self.assertEqual(res_btc["asset_class"], "CRYPTO")
        self.assertEqual(res_btc["hard_lot_ceiling"], 0.01)
        self.assertEqual(res_btc["lot_size"], 0.01)

        # Case B: Lowercase commodity 'crude' SELL must be vetoed under DEFCON 2
        appr_crude, mult_crude, reason_crude = self.fusion.evaluate_trade_confluence("crude", "SELL")
        self.assertFalse(appr_crude, "Selling crude against strong bullish macro must be vetoed")
        self.assertEqual(mult_crude, 0.0)
        self.assertIn("COUNTER-MACRO VETO", reason_crude)

    def test_13_defensive_base_lot_guards(self):
        """Verifies non-positive or NaN base_lot sizes are safely rejected."""
        import math

        for bad_lot in [float("nan"), 0.0, -0.05, -1.0]:
            res = self.fusion.scale_position_size("XAUUSD", base_lot=bad_lot, action="BUY")
            self.assertFalse(res["approved"])
            self.assertTrue(res["vetoed"])
            self.assertEqual(res["lot_size"], 0.0)
            self.assertEqual(res["risk_usd"], 0.0)
            self.assertIn("Invalid base lot size", res["reason"])


if __name__ == "__main__":
    unittest.main()
