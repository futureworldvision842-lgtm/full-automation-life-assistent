"""
tests/test_crypto_reasoning_engine.py
================================================================================
Comprehensive Unit & Integration Test Suite for J.A.R.V.I.S. Crypto Major
Deep Reasoning Engine (Requirement R2).

Verifies:
  1. Multi-factor reasoning pipeline:
     - Level-2 DOM depth, order book imbalance & crypto whale walls (>50 BTC, >500 ETH, >5,000 SOL)
     - 24/7 Funding rate arbitrage, perp vs spot basis carry, and squeeze detection
     - Liquidation cluster heatmaps across 5 leverage tiers (100x, 50x, 25x, 10x, 5x) and Shark Magnet targets
     - 4-Quadrant Open Interest (OI) momentum classification (Long Buildup, Short Buildup, Short Covering, Long Liquidation)
     - World Monitor macro catalysts & geopolitical risk index (DEFCON levels, 6 maritime chokepoints flow multipliers)
     - On-chain whale transaction velocity (> $1M USD movements & exchange netflows)
     - Weighted composite conviction scoring (0 to 100%)
  2. Dual-horizon strategy formulation:
     - Spot Accumulation: DCA tiers (-3% to -5%, -8% to -12%, -15% to -25%), liquidity grab zones, Wyckoff Phase C Spring, discount equilibrium
     - Futures Scalps / Intraday: Strict R:R >= 2.5, liquidity sweep triggers, structural invalidation levels, dynamic breakeven locks (+1.0R)
  3. Reasoning dossier dispatch & /api/crypto/reasoning schema format
  4. HFT skill crypto whale walls & 24/7 continuous session awareness
  5. Global liquidation radar data_mode: LIVE & market provenance
================================================================================
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"

for p in (str(PROJECT_ROOT), str(MQ3_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.trading.crypto_reasoning_engine import (
    CryptoReasoningEngine,
    CryptoDeepReasoningEngine,
    CryptoReasoningDossier,
    CryptoMultiFactorPipeline,
    CryptoDualHorizonFormulator,
    OIRegime,
    get_crypto_reasoning_engine,
)
from skills.high_frequency_trading import HighFrequencyTradingEngine
from src.global_liquidation_radar import GlobalLiquidationRadar


class TestCryptoDOMAndWhaleWalls(unittest.TestCase):
    """Verifies Level-2 DOM depth, volume imbalance, and crypto whale wall detection."""

    def setUp(self):
        self.pipeline = CryptoMultiFactorPipeline()
        self.hft_engine = HighFrequencyTradingEngine()

    def test_crypto_whale_wall_thresholds_registration(self):
        """Verifies native whale wall thresholds for BTC, ETH, SOL, and FX."""
        btc_th, btc_unit = self.hft_engine.get_whale_wall_threshold("BTCUSD")
        self.assertEqual(btc_th, 50.0)
        self.assertEqual(btc_unit, "BTC")

        eth_th, eth_unit = self.hft_engine.get_whale_wall_threshold("ETHUSD")
        self.assertEqual(eth_th, 500.0)
        self.assertEqual(eth_unit, "ETH")

        sol_th, sol_unit = self.hft_engine.get_whale_wall_threshold("SOLUSD")
        self.assertEqual(sol_th, 5000.0)
        self.assertEqual(sol_unit, "SOL")

        fx_th, fx_unit = self.hft_engine.get_whale_wall_threshold("GBPUSD")
        self.assertEqual(fx_th, 1000.0)
        self.assertEqual(fx_unit, "Lots")

    def test_dom_evaluation_returns_valid_structure(self):
        """Verifies DOM evaluation returns bids, asks, imbalance ratio, and bias."""
        dom_btc = self.pipeline.evaluate_crypto_dom("BTCUSD")
        self.assertIn("imbalance_ratio", dom_btc)
        self.assertIn("imbalance_pct", dom_btc)
        self.assertIn("bias", dom_btc)
        self.assertIn("whale_walls", dom_btc)
        self.assertIn("whale_threshold", dom_btc)
        self.assertEqual(dom_btc["whale_threshold"], 50.0)
        self.assertGreater(dom_btc["total_bid_volume"], 0.0)
        self.assertGreater(dom_btc["total_ask_volume"], 0.0)

    def test_hft_24_7_continuous_session_for_crypto_majors(self):
        """Verifies crypto majors are treated as 24/7 active continuously."""
        # Test during typical Asian session hours (03:00 UTC)
        asian_dt = datetime(2026, 9, 20, 3, 0, tzinfo=timezone.utc)
        btc_scan = self.hft_engine.evaluate_turtle_soup_and_ipda("BTCUSD", current_time_utc=asian_dt)
        self.assertTrue(btc_scan["ipda_killzone"]["is_active"])
        self.assertIn("CRYPTO", btc_scan["ipda_killzone"]["session"])

        # Test during rollover / off hours (22:30 UTC)
        off_dt = datetime(2026, 9, 20, 22, 30, tzinfo=timezone.utc)
        eth_scan = self.hft_engine.evaluate_turtle_soup_and_ipda("ETHUSD", current_time_utc=off_dt)
        self.assertTrue(eth_scan["ipda_killzone"]["is_active"])
        self.assertIn("CRYPTO", eth_scan["ipda_killzone"]["session"])

        # Traditional FX symbol should be locked out in Asian/off hours
        fx_scan = self.hft_engine.evaluate_turtle_soup_and_ipda("GBPUSD", current_time_utc=asian_dt)
        self.assertFalse(fx_scan["ipda_killzone"]["is_active"])
        self.assertEqual(fx_scan["ipda_killzone"]["session"], "ASIAN_SESSION_LOCKOUT")


class TestFundingRateArbitrageEngine(unittest.TestCase):
    """Verifies Perp vs Spot basis carry, funding yields, and squeeze classifications."""

    def setUp(self):
        self.pipeline = CryptoMultiFactorPipeline()

    def test_basis_carry_and_yield_calculation(self):
        """Verifies basis spread dollar, percentage, and annualized yield calculations."""
        res = self.pipeline.evaluate_funding_arbitrage(
            symbol="BTCUSD",
            spot_price=88000.0,
            perp_price=88150.0,
            funding_rate_8h=0.00015  # +0.015% per 8h
        )
        self.assertEqual(res["basis_dollar"], 150.0)
        self.assertAlmostEqual(res["basis_pct"], (150.0 / 88000.0) * 100.0, places=3)
        # Annualized: 0.00015 * 3 * 365 * 100 = 16.425%
        self.assertAlmostEqual(res["annualized_funding_yield_pct"], 16.43, places=1)
        self.assertFalse(res["is_squeeze_detected"])

    def test_extreme_funding_squeeze_arbitrage_carry(self):
        """Verifies detection of high funding contango carry (>= +0.05% per 8h)."""
        res = self.pipeline.evaluate_funding_arbitrage(
            symbol="ETHUSD",
            spot_price=2800.0,
            perp_price=2825.0,
            funding_rate_8h=0.0008  # +0.08% per 8h (> +0.05%)
        )
        self.assertTrue(res["is_squeeze_detected"])
        self.assertEqual(res["squeeze_direction"], "LONG_CROWD_SQUEEZE")
        self.assertEqual(res["arbitrage_opportunity"], "LONG_SPOT_SHORT_PERP_CARRY")

    def test_extreme_negative_funding_short_squeeze_rebate(self):
        """Verifies detection of extreme backwardation short squeeze (<= -0.05% per 8h)."""
        res = self.pipeline.evaluate_funding_arbitrage(
            symbol="SOLUSD",
            spot_price=145.0,
            perp_price=142.5,
            funding_rate_8h=-0.00075  # -0.075% per 8h (<= -0.05%)
        )
        self.assertTrue(res["is_squeeze_detected"])
        self.assertEqual(res["squeeze_direction"], "SHORT_CROWD_SQUEEZE")
        self.assertEqual(res["arbitrage_opportunity"], "SHORT_SPOT_LONG_PERP_REBATE")


class TestLiquidationClustersAndStopHunts(unittest.TestCase):
    """Verifies liquidation clusters across 100x–5x leverage tiers and market provenance."""

    def setUp(self):
        self.radar = GlobalLiquidationRadar()
        self.pipeline = CryptoMultiFactorPipeline()

    def test_global_liquidation_radar_provenance_and_live_mode(self):
        """Verifies that GlobalLiquidationRadar explicitly attaches data_mode: LIVE and source."""
        intel = self.radar.fetch_liquidation_intel("BTCUSD")
        self.assertEqual(intel["status"], "success")
        self.assertEqual(intel["data_mode"], "LIVE")
        self.assertTrue(bool(intel.get("source")))
        self.assertTrue(bool(intel.get("observed_at")))

        # Check observed_at is a valid ISO timestamp not in future
        obs_dt = datetime.fromisoformat(intel["observed_at"].replace("Z", "+00:00"))
        self.assertLessEqual(obs_dt, datetime.now(timezone.utc))

    def test_all_5_leverage_tiers_present(self):
        """Verifies liquidation heatmaps cover 100x, 50x, 25x, 10x, and 5x tiers."""
        liq_data = self.pipeline.evaluate_liquidation_clusters("BTCUSD", current_price=90000.0)
        heatmap = liq_data["liquidation_heatmap"]

        long_tiers = [p["leverage_tier"] for p in heatmap["long_liquidation_pools"]]
        short_tiers = [p["leverage_tier"] for p in heatmap["short_liquidation_pools"]]

        for tier in ("100x", "50x", "25x", "10x", "5x"):
            self.assertTrue(any(tier in t for t in long_tiers), f"Missing {tier} in long pools")
            self.assertTrue(any(tier in t for t in short_tiers), f"Missing {tier} in short pools")

    def test_shark_magnet_direction_and_targets(self):
        """Verifies that Shark Magnet targets pool with higher liquidation density."""
        liq_data = self.pipeline.evaluate_liquidation_clusters("ETHUSD", current_price=3000.0)
        magnet = liq_data["liquidity_magnet"]
        self.assertIn("direction", magnet)
        self.assertIn("target_price", magnet)
        self.assertIn("shark_rationale", magnet)
        self.assertGreater(magnet["target_price"], 0.0)


class TestOIMomentumEngine(unittest.TestCase):
    """Verifies the 4-quadrant derivatives Open Interest momentum regime classification."""

    def setUp(self):
        self.pipeline = CryptoMultiFactorPipeline()

    def test_quadrant_1_long_buildup(self):
        """Price Up + OI Up -> Long Buildup (Aggressive Buying)."""
        res = self.pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=2.5, delta_oi_pct=4.2)
        self.assertEqual(res["regime"], OIRegime.LONG_BUILDUP)
        self.assertEqual(res["bias"], "STRONG_BULLISH")
        self.assertGreater(res["conviction_modifier"], 0)

    def test_quadrant_2_short_buildup(self):
        """Price Down + OI Up -> Short Buildup (Aggressive Shorting)."""
        res = self.pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=-2.1, delta_oi_pct=3.8)
        self.assertEqual(res["regime"], OIRegime.SHORT_BUILDUP)
        self.assertEqual(res["bias"], "STRONG_BEARISH")
        self.assertLess(res["conviction_modifier"], 0)

    def test_quadrant_3_short_covering(self):
        """Price Up + OI Down -> Short Covering (Fragile Rally)."""
        res = self.pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=1.8, delta_oi_pct=-2.5)
        self.assertEqual(res["regime"], OIRegime.SHORT_COVERING)
        self.assertEqual(res["bias"], "WEAK_BULLISH_FRAGILE")

    def test_quadrant_4_long_liquidation(self):
        """Price Down + OI Down -> Long Liquidation (Capitulation)."""
        res = self.pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=-3.5, delta_oi_pct=-4.0)
        self.assertEqual(res["regime"], OIRegime.LONG_LIQUIDATION)
        self.assertEqual(res["bias"], "BEARISH_CAPITULATION")

    def test_neutral_consolidation_regime(self):
        """Near-zero delta -> Neutral Consolidation."""
        res = self.pipeline.evaluate_oi_momentum("BTCUSD", delta_price_pct=0.01, delta_oi_pct=0.02)
        self.assertEqual(res["regime"], OIRegime.NEUTRAL_CONSOLIDATION)
        self.assertEqual(res["bias"], "NEUTRAL")


class TestWorldMonitorMacroAndWhaleVelocity(unittest.TestCase):
    """Verifies macro catalysts (DEFCON, 6 maritime chokepoints) and whale velocity."""

    def setUp(self):
        self.pipeline = CryptoMultiFactorPipeline()

    def test_world_monitor_chokepoints_and_defcon(self):
        """Verifies ingestion of DEFCON rating and 6 strategic maritime chokepoints."""
        macro = self.pipeline.evaluate_macro_geopolitical("BTCUSD")
        self.assertIn("defcon_level", macro)
        self.assertIn("average_chokepoint_disruption_pct", macro)
        self.assertGreaterEqual(macro["chokepoints_tracked_count"], 6)

        cp_ids = [cp["id"] for cp in macro["strategic_chokepoints"]]
        required_6 = ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "panama_canal", "bosporus_dardanelles"]
        for required_id in required_6:
            self.assertIn(required_id, cp_ids, f"Chokepoint {required_id} missing from telemetry")

    def test_on_chain_whale_velocity(self):
        """Verifies on-chain whale transaction velocity and exchange netflow reporting."""
        whale = self.pipeline.evaluate_whale_velocity("BTCUSD")
        self.assertIn("whale_velocity_score", whale)
        self.assertIn("netflow_status", whale)
        self.assertIn("tracked_threshold", whale)
        self.assertGreaterEqual(whale["whale_velocity_score"], 0.0)
        self.assertLessEqual(whale["whale_velocity_score"], 100.0)


class TestDualHorizonStrategyFormulation(unittest.TestCase):
    """Verifies Spot DCA plans and precision Futures Scalps with strict R:R >= 2.5."""

    def setUp(self):
        self.formulator = CryptoDualHorizonFormulator()

    def test_spot_accumulation_dca_tiers(self):
        """Verifies DCA Tiers are within -3% to -5%, -8% to -12%, -15% to -25%."""
        plan = self.formulator.formulate_spot_accumulation(
            symbol="BTCUSD",
            current_price=88000.0,
            recent_swing_high=92000.0,
            recent_swing_low=75000.0
        )
        tiers = plan["dca_tiers"]
        self.assertEqual(len(tiers), 3)

        t1, t2, t3 = tiers[0], tiers[1], tiers[2]
        self.assertGreaterEqual(t1["pullback_target_pct"], 3.0)
        self.assertLessEqual(t1["pullback_target_pct"], 5.0)

        self.assertGreaterEqual(t2["pullback_target_pct"], 8.0)
        self.assertLessEqual(t2["pullback_target_pct"], 12.0)

        self.assertGreaterEqual(t3["pullback_target_pct"], 15.0)
        self.assertLessEqual(t3["pullback_target_pct"], 25.0)

        # Allocation sum equals 100%
        tot_alloc = sum(t["allocation_pct"] for t in tiers)
        self.assertEqual(tot_alloc, 100.0)

        # Wyckoff Phase C Spring verified
        self.assertEqual(plan["wyckoff_phase"], "PHASE_C_SPRING")
        self.assertIn("liquidity_grab_zone", plan)

    def test_futures_scalp_strict_rr_and_dynamic_breakeven(self):
        """Verifies Futures scalps enforce strict R:R >= 2.5 and +1.0R breakeven lock."""
        # Test BUY Setup
        buy_setup = self.formulator.formulate_futures_scalp(
            symbol="BTCUSD",
            direction="BUY",
            current_price=88000.0
        )
        self.assertTrue(buy_setup["meets_strict_rr_gate"])
        self.assertGreaterEqual(buy_setup["risk_to_reward_ratio"], 2.5)
        self.assertLess(buy_setup["stop_loss"], buy_setup["entry_price"])
        self.assertGreater(buy_setup["take_profit_ladder"]["tp2_2_5r"]["price"], buy_setup["entry_price"])
        self.assertEqual(buy_setup["dynamic_breakeven_rule"]["activation_r_multiple"], 1.0)
        self.assertIn("structural_invalidation_level", buy_setup)

        # Test SELL Setup
        sell_setup = self.formulator.formulate_futures_scalp(
            symbol="ETHUSD",
            direction="SELL",
            current_price=2800.0
        )
        self.assertTrue(sell_setup["meets_strict_rr_gate"])
        self.assertGreaterEqual(sell_setup["risk_to_reward_ratio"], 2.5)
        self.assertGreater(sell_setup["stop_loss"], sell_setup["entry_price"])
        self.assertLess(sell_setup["take_profit_ladder"]["tp2_2_5r"]["price"], sell_setup["entry_price"])


class TestCryptoReasoningEngineEndToEnd(unittest.TestCase):
    """Verifies end-to-end reasoning engine, dossier builder, and API serialization."""

    def setUp(self):
        self.engine = CryptoReasoningEngine()

    def test_evaluate_symbol_returns_full_dossier(self):
        """Verifies that evaluate_symbol returns a complete CryptoReasoningDossier."""
        dossier = self.engine.evaluate_symbol("BTCUSD")
        self.assertIsInstance(dossier, CryptoReasoningDossier)
        self.assertEqual(dossier.symbol, "BTCUSD")
        self.assertGreater(dossier.mark_price, 0.0)
        self.assertIn(dossier.direction, ("BUY", "SELL"))
        self.assertGreaterEqual(dossier.composite_conviction_score, 0.0)
        self.assertLessEqual(dossier.composite_conviction_score, 100.0)

        # Check required dossier components
        self.assertTrue(bool(dossier.why_this_trade))
        self.assertTrue(bool(dossier.invalidation_conditions))
        self.assertTrue(bool(dossier.summary_card))
        self.assertIn("structural_invalidation_price", dossier.invalidation_levels)
        self.assertIn("dca_tiers", dossier.spot_dca_plan)
        self.assertIn("take_profit_ladder", dossier.futures_scalp_setup)

    def test_api_crypto_reasoning_schema_compliance(self):
        """Verifies serialization format matches /api/crypto/reasoning requirements."""
        api_data = self.engine.get_api_reasoning("ETHUSD")
        self.assertEqual(api_data["status"], "success")
        self.assertEqual(api_data["api_version"], "2.0")
        self.assertIn("provenance", api_data)
        self.assertEqual(api_data["provenance"]["data_mode"], "LIVE")
        self.assertIn("multi_factor_analysis", api_data)
        self.assertIn("spot_dca_plan", api_data)
        self.assertIn("futures_scalp_setup", api_data)
        self.assertIn("invalidation_levels", api_data)

    def test_evaluate_all_majors_coverage(self):
        """Verifies evaluate_all_majors covers BTCUSD, ETHUSD, and SOLUSD."""
        all_dossiers = self.engine.evaluate_all_majors()
        self.assertIn("BTCUSD", all_dossiers)
        self.assertIn("ETHUSD", all_dossiers)
        self.assertIn("SOLUSD", all_dossiers)
        for sym, d in all_dossiers.items():
            self.assertGreater(d.mark_price, 0.0)
            self.assertGreaterEqual(d.futures_scalp_setup["risk_to_reward_ratio"], 2.5)

    def test_singleton_and_alias_identity(self):
        """Verifies singleton getter and CryptoDeepReasoningEngine alias."""
        engine1 = get_crypto_reasoning_engine()
        engine2 = get_crypto_reasoning_engine()
        self.assertIs(engine1, engine2)
        self.assertIs(CryptoDeepReasoningEngine, CryptoReasoningEngine)


if __name__ == "__main__":
    unittest.main()
