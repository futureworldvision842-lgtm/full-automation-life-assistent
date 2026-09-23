"""
tests/test_m1_prop_risk_and_hft_suite.py
========================================================================================
Comprehensive Unit & Integration Test Suite for Milestone M1:
Institutional MT5 Prop-Trading, Risk Kernel & HFT DOM Engine.

Verifies:
1. FundingPips account #40000294403 ($100k balance) synchronized across risk kernels:
   - 0.75% max risk cap ($750.00 dollar cap on #40000294403).
   - 1:2.5 minimum RR ratio.
   - Dynamic breakeven lock at +1.0R gain.
   - Verified across DeterministicRiskKernel, RiskManager, PipdanceFastTrackEngine, PortfolioRiskService.
2. Standalone & Integrated Multi-Timeframe (M15 + H1 + H4) Trend Confluence Filtering:
   - Vetoes / blocks trades on trend mismatch.
   - Approves trades on full trend alignment.
3. Big Sharks & SMC Trade Reasoning Engine:
   - Verifiable rationale: SMC/ICT Liquidity Sweep, Fair Value Gap (FVG 50% CE),
     Order Block retest, Wyckoff Accumulation/Distribution phase, M15+H1+H4 confluence.
   - Macro catalyst: DXY trend direction and 15m economic news circuit breaker check.
   - Complies with /api/trading/reasoning interface contract.
4. Level-2 DOM & HFT Quant Microstructure Engine (skills/high_frequency_trading.py):
   - DOM bid/ask parsing (handling both 'bids'/'asks' and 'top_bids'/'top_asks').
   - Institutional whale wall detection (>1,000 lots).
   - Lee-Ready CVD net delta, buyer ratio, and order absorption classifier.
   - CVD absorption divergence detection.
   - Sub-second latency (<2ms) and tick spread expansion radar.
   - Turtle Soup liquidity sweep and IPDA dealing range killzone filter.
========================================================================================
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

# Setup repository paths
ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from src.risk_manager import RiskManager
from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from src.portfolio_risk_service import PortfolioRiskService
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from skills.high_frequency_trading import (
    HighFrequencyTradingEngine,
    analyze_hft_microstructure,
    get_hft_engine,
    run as hft_run
)
from core.trading.reasoning import (
    BigSharksReasoningEngine,
    get_trading_reasoning,
    get_reasoning_engine
)


class TestM1PropRiskAndHFTSuite(unittest.TestCase):

    def setUp(self):
        self.risk_kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.risk_mgr = RiskManager({
            "account_info": {"target_account_size": 100000.0},
            "risk_management": {
                "risk_per_trade_pct": 0.75,
                "max_risk_usd_cap": 750.0,
                "min_rr_ratio": 2.5,
                "dynamic_breakeven_r": 1.0,
                "max_daily_loss_pct": 4.0,
                "max_total_loss_pct": 10.0,
                "max_open_trades": 3,
                "max_daily_trades": 3,
            }
        })
        self.pip_engine = PipdanceFastTrackEngine()
        self.prs = PortfolioRiskService()
        self.hft_engine = HighFrequencyTradingEngine()
        self.reasoning_engine = BigSharksReasoningEngine()
        self.confluence_filter = MultiTimeframeConfluenceFilter()

    # =========================================================================
    # 1. RISK KERNEL & ACCOUNT #40000294403 SYNCHRONIZATION
    # =========================================================================

    def test_01_deterministic_risk_kernel_account_parameters(self):
        """Verify DeterministicRiskKernel enforces 0.75% / $750 cap, 1:2.5 min RR, +1.0R BE."""
        params = self.risk_kernel.get_risk_parameters("40000294403")
        self.assertEqual(params["account"], "40000294403")
        self.assertEqual(params["max_risk_cap"], 750.0)
        self.assertEqual(params["risk_pct"], 0.75)
        self.assertEqual(params["min_rr"], 2.5)
        self.assertEqual(params["dynamic_be_r"], 1.0)

        # Admitted trade: 0.75% risk, 1:2.5 RR, 92 confluence
        res = self.risk_kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id="40000294403",
            balance=100000.0
        )
        self.assertTrue(res["allowed"], f"Admissible trade was blocked: {res['blockers']}")
        self.assertEqual(res["decision"], "ADMITTED_PROPOSAL")
        self.assertEqual(res["passed_gates_count"], 18)
        self.assertEqual(res["risk_usd"], 750.0)
        self.assertEqual(res["max_risk_usd_cap"], 750.0)

    def test_02_deterministic_risk_kernel_rejects_excessive_risk(self):
        """DeterministicRiskKernel strictly blocks trades exceeding 0.75% or $750 cap."""
        # Breach percentage: 0.80% > 0.75%
        res_pct = self.risk_kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.80,
            rr_ratio=2.5,
            account_id="40000294403",
            balance=100000.0
        )
        self.assertFalse(res_pct["allowed"])
        self.assertEqual(res_pct["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max allowed (0.75%)" in b for b in res_pct["blockers"]))

        # Breach dollar cap: proposed_risk_usd = 850.0 > $750.00
        res_dollar = self.risk_kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.5,
            account_id="40000294403",
            balance=100000.0,
            proposed_risk_usd=850.0
        )
        self.assertFalse(res_dollar["allowed"])
        self.assertTrue(any("exceeds max cap ($750.00)" in b for b in res_dollar["blockers"]))

    def test_03_deterministic_risk_kernel_rejects_low_rr_ratio(self):
        """DeterministicRiskKernel rejects trades with RR ratio < 1:2.5."""
        res_rr = self.risk_kernel.evaluate_admission(
            symbol="GBPUSD",
            confluence_score=92.0,
            proposed_risk_pct=0.75,
            rr_ratio=2.0,  # Below 1:2.5 minimum
            account_id="40000294403",
            balance=100000.0
        )
        self.assertFalse(res_rr["allowed"])
        self.assertTrue(any("below minimum 1:2.5" in b for b in res_rr["blockers"]))

    def test_04_deterministic_risk_kernel_dynamic_breakeven_evaluation(self):
        """DeterministicRiskKernel confirms dynamic breakeven trigger at >= +1.0R gain."""
        # 1. Gain < 1.0R (0.75R) -> Maintain SL
        eval_low = self.risk_kernel.evaluate_dynamic_breakeven(current_gain_r=0.75, profit_usd=562.50, entry_price=1.33675)
        self.assertFalse(eval_low["trigger"])
        self.assertEqual(eval_low["action"], "maintain_sl")

        # 2. Gain >= 1.0R (1.10R) -> Lock SL to entry
        eval_hit = self.risk_kernel.evaluate_dynamic_breakeven(current_gain_r=1.10, profit_usd=825.00, entry_price=1.33675)
        self.assertTrue(eval_hit["trigger"])
        self.assertEqual(eval_hit["action"], "lock_sl_to_entry")
        self.assertEqual(eval_hit["new_sl"], 1.33675)

    def test_05_risk_manager_dollar_cap_and_lot_ceilings(self):
        """RiskManager caps dollar risk to $750.00 on #40000294403 and enforces lot ceilings."""
        balance = 100000.0
        rules = self.risk_mgr.get_account_rules("40000294403")
        self.assertEqual(rules["max_risk_usd_cap"], 750.0)
        self.assertEqual(rules["max_risk_pct"], 0.75)
        self.assertEqual(rules["min_rr_ratio"], 2.5)
        self.assertEqual(rules["dynamic_breakeven_r"], 1.0)

        # Gold lot ceiling <= 0.10L
        gold_lot = self.risk_mgr.calculate_position_size(balance, 10.0, "XAUUSD")
        self.assertLessEqual(gold_lot, 0.10, f"Gold lot ceiling breached: {gold_lot}")

        # Forex lot ceiling <= 0.20L
        fx_lot = self.risk_mgr.calculate_position_size(balance, 10.0, "EURUSD")
        self.assertLessEqual(fx_lot, 0.20, f"Forex lot ceiling breached: {fx_lot}")

        # Crypto lot ceiling <= 0.01L
        crypto_lot = self.risk_mgr.calculate_position_size(balance, 10.0, "BTCUSD")
        self.assertLessEqual(crypto_lot, 0.01, f"Crypto lot ceiling breached: {crypto_lot}")

        # Dynamic breakeven check in RiskManager
        be_res = self.risk_mgr.check_dynamic_breakeven(
            entry_price=1.3300,
            current_price=1.3340,  # +40 pips gain
            sl_price=1.3260,       # 40 pips initial risk -> exact +1.0R gain
            direction="BUY"
        )
        self.assertTrue(be_res["trigger"])
        self.assertEqual(be_res["new_sl"], 1.3300)

    def test_06_pipdance_engine_calculates_750_cap_on_40000294403(self):
        """PipdanceFastTrackEngine accurately applies $750 cap and 1:2.5 RR on #40000294403."""
        res = self.pip_engine.calculate_risk(
            balance=100000.0,
            atr=0.0015,
            symbol="GBPUSD",
            entry_price=1.33675,
            direction="SELL",
            rr_ratio=2.5,
            account_id="40000294403"
        )
        self.assertEqual(res["status"], "approved")
        self.assertEqual(res["risk_pct"], 0.75)
        self.assertEqual(res["risk_usd"], 750.0)
        self.assertEqual(res["max_risk_cap"], 750.0)
        self.assertEqual(res["rr_ratio"], 2.5)
        self.assertEqual(res["breakeven_lock_threshold_r"], 1.0)
        self.assertEqual(res["breakeven_lock_usd"], 750.0)

    def test_07_portfolio_risk_service_account_40000294403(self):
        """PortfolioRiskService confirms #40000294403 has $750 cap and admits 0.75% risk."""
        acc = self.prs.get_account("40000294403")
        self.assertIsNotNone(acc)
        self.assertEqual(acc.max_risk_usd_cap, 750.0)
        self.assertEqual(acc.max_risk_pct, 0.75)

        ok, reason, telem = self.prs.evaluate_trade_admission_risk(
            account_id="40000294403",
            symbol="GBPUSD",
            direction="SELL",
            risk_pct=0.75
        )
        self.assertTrue(ok, f"0.75% risk trade on #40000294403 was rejected: {reason}")
        self.assertLessEqual(telem["risk_dollar"], 750.01)

    # =========================================================================
    # 2. MULTI-TIMEFRAME (M15 + H1 + H4) TREND CONFLUENCE FILTERING
    # =========================================================================

    def test_08_confluence_filter_vetoes_mismatched_trends(self):
        """Confluence filter blocks trades when M15 trend conflicts with H1 or H4."""
        def make_df(base, slope, count=60):
            return pd.DataFrame({"close": [base + i * slope for i in range(count)]})

        df_bull = make_df(1.3300, 0.0002)
        df_bear = make_df(1.3300, -0.0002)

        # M15 Bull vs H1 Bear -> BLOCKED
        ok1, d1, m1 = self.confluence_filter.evaluate_trend_confluence(df_bull, df_bear, df_bull)
        self.assertFalse(ok1)
        self.assertEqual(m1.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # M15 Bull vs H4 Bear -> BLOCKED
        ok2, d2, m2 = self.confluence_filter.evaluate_trend_confluence(df_bull, df_bull, df_bear)
        self.assertFalse(ok2)
        self.assertEqual(m2.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # M15 Bear vs H1 Bull -> BLOCKED
        ok3, d3, m3 = self.confluence_filter.evaluate_trend_confluence(df_bear, df_bull, df_bear)
        self.assertFalse(ok3)
        self.assertEqual(m3.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Full alignment -> APPROVED
        ok_bull, d_bull, _ = self.confluence_filter.evaluate_trend_confluence(df_bull, df_bull, df_bull)
        self.assertTrue(ok_bull)
        self.assertEqual(d_bull, "BUY")

        ok_bear, d_bear, _ = self.confluence_filter.evaluate_trend_confluence(df_bear, df_bear, df_bear)
        self.assertTrue(ok_bear)
        self.assertEqual(d_bear, "SELL")

    # =========================================================================
    # 3. BIG SHARKS & SMART MONEY (SMC) TRADE REASONING ENGINE
    # =========================================================================

    def test_09_smc_setup_verifiable_components(self):
        """BigSharksReasoningEngine generates verifiable SMC rationale."""
        res = self.reasoning_engine.evaluate_smc_setup(symbol="GBPUSD", direction="SELL")
        self.assertIn("ICT Institutional Liquidity Sweep", res["setup_name"])
        self.assertTrue(res["liquidity_sweep"]["verified"])
        self.assertIn("1.33600", res["liquidity_sweep"]["description"])
        self.assertIn("retail buy stops", res["liquidity_sweep"]["description"])
        self.assertTrue(res["fair_value_gap"]["mitigated"])
        self.assertEqual(res["fair_value_gap"]["consequent_encroachment_50"], 1.33560)
        self.assertEqual(res["order_block"]["level"], 1.33675)
        self.assertIn("DISTRIBUTION_PHASE_C_UTAD", res["wyckoff"]["phase"])

    def test_10_macro_catalyst_dxy_and_news_circuit_breaker(self):
        """BigSharksReasoningEngine evaluates DXY trend and 15m economic news circuit breaker."""
        macro = self.reasoning_engine.evaluate_macro_catalyst("GBPUSD")
        self.assertEqual(macro["dxy_index"]["trend_direction"], "BULLISH_EXPANSION")
        self.assertEqual(macro["dxy_index"]["correlation"], "INVERSE")
        self.assertTrue(macro["news_circuit_breaker_15m"]["circuit_breaker_passed"])
        self.assertEqual(macro["news_circuit_breaker_15m"]["window_minutes"], 15)

    def test_11_full_trading_reasoning_payload_contract(self):
        """get_trading_reasoning complies with the PROJECT.md interface contract."""
        payload = get_trading_reasoning("GBPUSD")
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["account"], "40000294403")
        self.assertEqual(payload["risk_params"]["max_risk_cap"], 750.0)
        self.assertEqual(payload["risk_params"]["risk_pct"], 0.75)
        self.assertEqual(payload["risk_params"]["min_rr"], 2.5)
        self.assertEqual(payload["risk_params"]["dynamic_be_r"], 1.0)

        # Must include latest_setups with all required keys
        self.assertGreaterEqual(len(payload["latest_setups"]), 1)
        setup = payload["latest_setups"][0]
        self.assertEqual(setup["symbol"], "GBPUSD")
        self.assertIn("setup_type", setup)
        self.assertIn("big_sharks", setup)
        self.assertIn("macro_catalyst", setup)
        self.assertIn("confluence", setup)
        self.assertIn("rationale", setup)
        self.assertTrue(len(setup["rationale"]) > 50)

        # Must include hft_microstructure with whale_walls, cvd_absorption, spread_radar
        self.assertIn("hft_microstructure", payload)
        hft = payload["hft_microstructure"]
        self.assertIn("whale_walls", hft)
        self.assertIn("cvd_absorption", hft)
        self.assertIn("spread_radar", hft)

    # =========================================================================
    # 4. HFT LEVEL-2 DOM & QUANT MICROSTRUCTURE ENGINE
    # =========================================================================

    def test_12_hft_dom_parsing_both_key_conventions(self):
        """HFT engine parses DOM data with both 'top_bids'/'top_asks' and 'bids'/'asks'."""
        dom = self.hft_engine.get_dom_data("XAUUSD")
        self.assertIn("top_bids", dom)
        self.assertIn("top_asks", dom)
        self.assertIn("bids", dom)
        self.assertIn("asks", dom)
        self.assertGreater(dom["total_bid_volume"], 0.0)
        self.assertGreater(dom["total_ask_volume"], 0.0)

    def test_13_hft_whale_wall_detection_over_1000_lots(self):
        """HFT engine detects institutional whale walls (>1,000 lots)."""
        dom = self.hft_engine.get_dom_data("XAUUSD")
        walls = dom["whale_walls"]
        self.assertGreaterEqual(len(walls), 1, "Must detect at least one whale wall")
        for w in walls:
            self.assertGreater(w["volume"], 1000.0, f"Whale wall volume must be > 1,000 lots: {w['volume']}")
            self.assertTrue(w["is_whale_wall"])
            self.assertIn(w["type"], ("BID_SUPPORT_WHALE_WALL", "ASK_RESISTANCE_WHALE_WALL"))

    def test_14_hft_cvd_net_delta_and_absorption_classifier(self):
        """HFT engine computes Lee-Ready CVD net delta and absorption classification."""
        # Simulated tick feed: aggressive buyer absorption
        ticks = pd.DataFrame({
            "bid": [1.0850, 1.0850, 1.0850, 1.0850],
            "ask": [1.0852, 1.0852, 1.0852, 1.0852],
            "last": [1.0852, 1.0852, 1.0852, 1.0850],  # 3 buys, 1 sell
            "volume": [100.0, 150.0, 200.0, 50.0]
        })
        res = self.hft_engine.compute_cvd_and_absorption("EURUSD", ticks=ticks)
        self.assertGreater(res["net_delta"], 0.0)
        self.assertEqual(res["absorption_type"], "BUYER_ABSORPTION")
        self.assertIn(res["divergence_bias"], ("BULLISH_CONTINUATION", "BULLISH_REVERSAL"))

    def test_15_hft_sub_2ms_latency_and_spread_radar(self):
        """HFT engine verifies sub-second latency (<2ms) and tick spread expansion radar."""
        lat = self.hft_engine.evaluate_latency_and_spread("XAUUSD")
        self.assertLess(lat["latency_ms"], 2.0, f"Latency {lat['latency_ms']}ms exceeded 2.0ms threshold")
        self.assertTrue(lat["sub_2ms_passed"])
        self.assertEqual(lat["latency_status"], "SUB_2MS_OPTIMAL")
        self.assertEqual(lat["spread_status"], "STABLE_NORMAL")
        self.assertLess(lat["spread_multiplier"], 2.5)

    def test_16_hft_turtle_soup_sweep_and_ipda_killzone(self):
        """HFT engine detects Turtle Soup sweeps and evaluates IPDA dealing range & killzones."""
        ipda = self.hft_engine.evaluate_turtle_soup_and_ipda("XAUUSD")
        self.assertIn("turtle_soup", ipda)
        self.assertTrue(ipda["turtle_soup"]["is_swept"])
        self.assertIn(ipda["turtle_soup"]["inducement_type"], ("BULLISH_EQL_SWEEP", "BEARISH_EQH_SWEEP"))

        # IPDA Dealing Range & 50% CE
        dr = ipda["ipda_dealing_range"]
        self.assertEqual(dr["equilibrium_50_ce"], round((dr["high"] + dr["low"]) / 2.0, 3))
        self.assertIn(dr["regime"], ("DISCOUNT_INSTITUTIONAL_BUY_ZONE", "PREMIUM_INSTITUTIONAL_SELL_ZONE"))

        # IPDA Killzone
        kz = ipda["ipda_killzone"]
        self.assertIn(kz["session"], (
            "LONDON_KILL_ZONE", "NY_KILL_ZONE", "ASIAN_SESSION_LOCKOUT", "ROLLOVER_OR_OFF_HOURS_LOCKOUT"
        ))

    def test_17_hft_skill_run_dispatch_actions(self):
        """hft_run() dispatches all manifest actions cleanly with zero unhandled exceptions."""
        actions = ["dom", "whale_walls", "cvd", "latency", "turtle_soup", "full_hft_scan"]
        for act in actions:
            out = hft_run({"action": act, "symbol": "GBPUSD"})
            self.assertIsInstance(out, str)
            self.assertFalse(out.startswith("HFT Engine Error"), f"Action {act} threw error: {out}")
            self.assertIn(act.upper().split("_")[0], out.upper())


if __name__ == "__main__":
    unittest.main(verbosity=2)
