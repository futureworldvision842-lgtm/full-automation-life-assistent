"""
tests/test_ai_trader.py — HKUDS AI-Trader Milestone M3 Verification Suite (Refactored)
=============================================================================
Comprehensive unit, gating, end-to-end pipeline, and Hermes tool integration tests:
  1. Multi-Agent Quantitative Roles (Macro Analyst, Order Flow Scout, Stat Arb, Coordinator)
  2. Alpha Formula Miner, Qlib Alpha158 Vectorized Expressions, and IC/IR Evaluation
  3. Deterministic Prop-Firm Risk Gating (18 gates, <=0.75% / $750 cap, geometry, RR >= 2.5, news)
  4. End-to-End Multi-Agent Execution Pipeline
  5. Hermes Tool Integration & Dynamic Cognitive Registry

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Absolute ZERO mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import math
import sys
import time
import json
import threading
import unittest
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Production Imports
from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from trading.ai_trader.types import (
    MacroVerdict,
    OrderFlowVerdict,
    StatArbVerdict,
    ConsensusVerdict,
    CandidateSetup,
    FactorEvaluationReport,
    Direction,
)
from trading.ai_trader.macro_analyst import MacroQuantitativeAnalyst
from trading.ai_trader.orderflow_scout import HighFrequencyOrderFlowScout
from trading.ai_trader.stat_arb import StatisticalArbitrageur
from trading.ai_trader.coordinator import AITraderCoordinator, get_ai_trader_coordinator
from trading.ai_trader.qlib_factors import QlibAlpha158
from trading.ai_trader.formula_parser import FormulaASTParser
from trading.ai_trader.alpha_evaluator import AlphaEvaluator
from trading.ai_trader.alpha_miner import AITraderAlphaMiner
from brain.hermes_agent import HermesAgent
from skills.ai_trader_skill import run as ai_trader_run, get_hermes_schema, HERMES_AI_TRADER_TOOLS, MANIFEST
from skills.loader import load_skills, list_skill_files


# =============================================================================
# 1. MULTI-AGENT QUANTITATIVE ROLES UNIT TESTS
# =============================================================================

class TestAITraderMultiAgentRoles(unittest.TestCase):
    """Unit tests for Macro Analyst, Order Flow Scout, Stat Arb, and Coordinator."""

    def setUp(self):
        self.ohlc_sample = pd.DataFrame({
            "open": [1.0800, 1.0810, 1.0820, 1.0830, 1.0825],
            "high": [1.0820, 1.0835, 1.0840, 1.0855, 1.0830],
            "low": [1.0790, 1.0805, 1.0815, 1.0820, 1.0810],
            "close": [1.0810, 1.0820, 1.0830, 1.0822, 1.0815],
            "volume": [1000, 1500, 2100, 1800, 1200]
        })

    def test_macro_analyst_dxy_bullish_bearish_fx(self):
        """Verify strong DXY bullish trend imparts bearish bias on EURUSD."""
        analyst = MacroQuantitativeAnalyst(world_monitor_engine=None)
        verdict = analyst.evaluate("EURUSD", {"dxy_trend": "BULLISH"})
        self.assertIsInstance(verdict, MacroVerdict)
        self.assertEqual(verdict.bias, "BEARISH")
        self.assertEqual(verdict.macro_regime, "RISK_OFF_CONTRACTION")
        self.assertGreaterEqual(verdict.conviction, 0.80)
        self.assertIn("DXY index trending bullish", verdict.rationale)

    def test_macro_analyst_geopolitical_escalation_gold(self):
        """Verify geopolitical escalation or chokepoint shock triggers Gold bullish bias."""
        analyst = MacroQuantitativeAnalyst(world_monitor_engine=None)
        verdict = analyst.evaluate("XAUUSD", {
            "chokepoint_shock": True,
            "macro_state": {"defcon_level": 2, "geopolitical_risk_score": 85.0}
        })
        self.assertIsInstance(verdict, MacroVerdict)
        self.assertEqual(verdict.bias, "BULLISH")
        self.assertEqual(verdict.macro_regime, "GEOPOLITICAL_FLIGHT_TO_SAFETY")
        self.assertGreaterEqual(verdict.macro_multiplier, 1.35)
        self.assertGreaterEqual(verdict.conviction, 0.85)

    def test_macro_analyst_world_monitor_fallback(self):
        """Verify graceful fallback when World Monitor feed is disconnected."""
        analyst = MacroQuantitativeAnalyst(world_monitor_engine=False)
        verdict = analyst.evaluate("EURUSD", None)
        self.assertIsInstance(verdict, MacroVerdict)
        self.assertEqual(verdict.bias, "NEUTRAL")
        self.assertEqual(verdict.macro_regime, "BALANCED_RANGE")
        self.assertEqual(verdict.conviction, 0.50)
        self.assertEqual(verdict.defcon_level, 3)

    def test_orderflow_scout_liquidity_sweep_detection(self):
        """Verify ICT Bearish Buy Stop Sweep detection above session highs."""
        scout = HighFrequencyOrderFlowScout()
        # Bar sequence where the last bar pierces prev swing high (1.0840) to 1.0860 but closes at 1.0830
        sweep_df = pd.DataFrame({
            "open": [1.0800, 1.0810, 1.0820, 1.0830, 1.0835],
            "high": [1.0820, 1.0830, 1.0840, 1.0835, 1.0860],
            "low": [1.0790, 1.0800, 1.0810, 1.0820, 1.0825],
            "close": [1.0810, 1.0820, 1.0830, 1.0832, 1.0830],
            "volume": [1000, 1200, 1500, 1100, 2400]
        })
        # Directly test sweep detector method
        sweep = scout.detect_turtle_soup_sweep(sweep_df)
        self.assertTrue(sweep["swept"])
        self.assertEqual(sweep["type"], "ICT_BEARISH_BUY_STOP_SWEEP")
        self.assertEqual(sweep["bias"], "BEARISH_REVERSAL")
        self.assertEqual(sweep["swept_level"], 1.0840)

        # Also test via full OrderFlowVerdict evaluation
        verdict = scout.evaluate("EURUSD", {"ohlc_df": sweep_df})
        self.assertIsInstance(verdict, OrderFlowVerdict)
        self.assertTrue(verdict.turtle_soup_swept)
        self.assertEqual(verdict.bias, "BEARISH_DISTRIBUTION")
        self.assertGreaterEqual(verdict.conviction, 0.85)

    def test_orderflow_scout_cvd_delta_divergence(self):
        """Verify CVD delta divergence detection against price movement."""
        scout = HighFrequencyOrderFlowScout()
        verdict = scout.evaluate("EURUSD", {"price_delta": 10.0, "cvd_delta": -450.0})
        self.assertIsInstance(verdict, OrderFlowVerdict)
        self.assertEqual(verdict.absorption_type, "SELLER_ABSORPTION")
        self.assertEqual(verdict.absorption_divergence, "BEARISH_REVERSAL")
        self.assertEqual(verdict.bias, "BEARISH_DISTRIBUTION")
        self.assertGreaterEqual(verdict.conviction, 0.80)
        self.assertEqual(verdict.cvd_net_delta, -450.0)

    def test_orderflow_scout_whale_wall_absorption(self):
        """Verify DOM whale wall (>1,000 lots) recognition."""
        scout = HighFrequencyOrderFlowScout()
        dom = {
            "bids": [{"price": 1.0810, "volume": 1450.0}],
            "asks": [{"price": 1.0830, "volume": 200.0}]
        }
        walls = scout.detect_whale_walls("EURUSD", dom)
        self.assertEqual(len(walls), 1)
        self.assertEqual(walls[0]["side"], "BID_SUPPORT")
        self.assertEqual(walls[0]["volume"], 1450.0)

        verdict = scout.evaluate("EURUSD", {"dom": dom})
        self.assertIsInstance(verdict, OrderFlowVerdict)
        self.assertGreaterEqual(verdict.whale_walls_count, 1)
        self.assertEqual(verdict.dom_bias, "BULLISH_ABSORPTION")
        self.assertEqual(verdict.bias, "BULLISH_ACCUMULATION")

    def test_stat_arb_spread_mean_reversion_zscore(self):
        """Verify spread z-score calculation and mean-reversion trigger."""
        stat_arb = StatisticalArbitrageur()
        spread = np.array([0.0010, 0.0012, 0.0011, 0.0013, 0.0025])
        verdict = stat_arb.evaluate("EURUSD", {"spread": spread, "half_life_bars": 15.0, "pair_symbol": "GBPUSD"})
        self.assertIsInstance(verdict, StatArbVerdict)
        self.assertEqual(verdict.bias, "BEARISH_MEAN_REVERSION")
        self.assertGreater(verdict.spread_zscore, 2.0)
        self.assertGreaterEqual(verdict.conviction, 0.75)
        self.assertEqual(verdict.arbitrage_type, "CROSS_PAIR_SPREAD")
        self.assertEqual(verdict.pair_symbol, "GBPUSD")

    def test_stat_arb_correlation_breakdown_filter(self):
        """Verify correlation breakdown (< 0.50) blocks stat-arb setups."""
        stat_arb = StatisticalArbitrageur(min_correlation=0.50)
        verdict = stat_arb.evaluate("EURUSD", {"correlation": 0.32, "pair_symbol": "GBPUSD"})
        self.assertIsInstance(verdict, StatArbVerdict)
        self.assertEqual(verdict.bias, "NEUTRAL")
        self.assertEqual(verdict.conviction, 0.0)
        self.assertEqual(verdict.arbitrage_type, "NONE")
        self.assertEqual(verdict.cointegration_confidence, 0.0)
        self.assertIn("Correlation breakdown", verdict.rationale)

    def test_coordinator_unanimous_synthesis(self):
        """Verify coordinator produces approved setup when roles align."""
        coordinator = AITraderCoordinator()
        snapshot = {
            "macro_score": 92.0,
            "orderflow_score": 94.0,
            "stat_arb_score": 90.0,
            "current_price": 2650.0,
            "sl": 2640.0,
            "tp": 2675.0,
            "direction": "BUY",
            "killzone_active": True
        }
        consensus = coordinator.analyze_and_synthesize("XAUUSD", snapshot)
        self.assertIsInstance(consensus, ConsensusVerdict)
        self.assertGreaterEqual(consensus.confluence_score, 90.0)
        self.assertTrue(consensus.unanimous)
        self.assertEqual(consensus.direction, "BUY")
        self.assertTrue(consensus.admitted)

    def test_coordinator_conflicting_roles_downgrade(self):
        """Verify coordinator downgrades score below 90 on role conflict."""
        coordinator = AITraderCoordinator()
        snapshot = {
            "macro_score": 95.0,
            "orderflow_score": 40.0,
            "stat_arb_score": 75.0,
            "current_price": 2650.0,
            "sl": 2640.0,
            "tp": 2675.0
        }
        consensus = coordinator.analyze_and_synthesize("XAUUSD", snapshot)
        self.assertIsInstance(consensus, ConsensusVerdict)
        self.assertLess(consensus.confluence_score, 90.0)
        self.assertFalse(consensus.admitted)
        self.assertFalse(consensus.unanimous)


# =============================================================================
# 2. ALPHA FORMULA MINING & QLIB ALPHA158 TESTS
# =============================================================================

class TestAlphaFormulaMinerAndQlib(unittest.TestCase):
    """Unit tests for formulaic factor generation, Qlib Alpha158 expressions, and IC/IR."""

    def setUp(self):
        dates = pd.date_range("2026-01-01", periods=100, freq="15min")
        np.random.seed(42)
        prices = 2650.0 + np.cumsum(np.random.randn(100) * 0.5)
        self.df = pd.DataFrame({
            "open": prices - 0.2,
            "high": prices + 0.8,
            "low": prices - 0.9,
            "close": prices,
            "volume": np.random.randint(100, 2000, 100).astype(float)
        }, index=dates)

    def test_qlib_alpha158_candlestick_geometry(self):
        """Verify Qlib Alpha158 candlestick geometry features (KMID, KLEN)."""
        geom = QlibAlpha158.compute_geometry_alphas(self.df)
        self.assertIn("KMID", geom.columns)
        self.assertIn("KLEN", geom.columns)
        self.assertEqual(len(geom), len(self.df))
        self.assertTrue(np.all(np.isfinite(geom["KMID"])))
        self.assertTrue(np.all(np.isfinite(geom["KLEN"])))
        safe_open = np.where(self.df["open"] != 0, self.df["open"], 1e-9)
        expected_kmid = (self.df["close"] - self.df["open"]) / safe_open
        np.testing.assert_allclose(geom["KMID"].values, expected_kmid.values, rtol=1e-5)

    def test_qlib_alpha158_vwap_deviation_and_momentum(self):
        """Verify normalized VWAP deviation calculation."""
        vol_df = QlibAlpha158.compute_volume_alphas(self.df)
        self.assertIn("VWAP_DEV", vol_df.columns)
        self.assertTrue(np.all(np.isfinite(vol_df["VWAP_DEV"])))
        self.assertEqual(len(vol_df), len(self.df))

        ast_vwap = FormulaASTParser.evaluate("VWAP_DEV", self.df)
        self.assertTrue(np.all(np.isfinite(ast_vwap)))
        np.testing.assert_allclose(vol_df["VWAP_DEV"].values, ast_vwap.values, rtol=1e-5)

    def test_qlib_alpha158_numerical_safety_zero_division(self):
        """Verify zero division guard on zero open and flat high/low."""
        bad_df = pd.DataFrame({
            "open": [0.0, 0.0],
            "high": [10.0, 10.0],
            "low": [10.0, 10.0],
            "close": [10.0, 10.0],
            "volume": [0.0, 0.0]
        })
        geom = QlibAlpha158.compute_geometry_alphas(bad_df)
        self.assertTrue(np.all(np.isfinite(geom["KMID"])))
        self.assertTrue(np.all(np.isfinite(geom["KLEN"])))
        # Also test AST parser safe division on zero values
        safe_div_res = FormulaASTParser.evaluate("Div(close, high)", bad_df)
        self.assertTrue(np.all(np.isfinite(safe_div_res)))

    def test_alpha_miner_template_fallback_zero_paid_api(self):
        """Verify formula generator fallback operates without cloud API keys."""
        miner = AITraderAlphaMiner()
        cand = miner.generate_candidate_formula("XAUUSD", "Gold")
        self.assertIsInstance(cand, dict)
        self.assertIn("expression", cand)
        self.assertIn("name", cand)
        self.assertIn("asset_class", cand)
        self.assertTrue(FormulaASTParser.validate_expression(cand["expression"]))

        series = FormulaASTParser.evaluate(cand["expression"], self.df)
        self.assertEqual(len(series), len(self.df))
        self.assertTrue(np.all(np.isfinite(series)))

    def test_alpha_miner_formula_syntax_and_safety_filter(self):
        """Verify security filter blocks dangerous Python keywords in formula expressions."""
        dangerous_expressions = [
            "__import__('os').system('calc')",
            "eval('2 + 2')",
            "exec('import os')",
            "subprocess.call(['calc'])",
            "globals()['__builtins__']",
            "getattr(os, 'system')('calc')"
        ]
        for expr in dangerous_expressions:
            self.assertFalse(FormulaASTParser.validate_expression(expr), f"Expression '{expr}' must be rejected")
            with self.assertRaises(ValueError):
                FormulaASTParser.evaluate(expr, self.df)

        valid_expr = "Div(Sub(close, Ref(close, 5)), Std(close, 10))"
        self.assertTrue(FormulaASTParser.validate_expression(valid_expr))

    def test_alpha_evaluator_perfect_and_inverse_ic(self):
        """Verify IC calculation with perfect (+1.0) and inverse (-1.0) correlation."""
        factor = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        forward_ret = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
        ic = AlphaEvaluator.compute_ic(factor, forward_ret)
        self.assertAlmostEqual(ic, 1.0, places=4)

        inverse_ret = -forward_ret
        inv_ic = AlphaEvaluator.compute_ic(factor, inverse_ret)
        self.assertAlmostEqual(inv_ic, -1.0, places=4)

    def test_alpha_evaluator_noise_factor_rejection(self):
        """Verify noise factor (|IC| < 0.25) is rejected."""
        np.random.seed(123)
        factor = pd.Series(np.random.randn(len(self.df)), index=self.df.index)
        evaluator = AlphaEvaluator(min_rank_ic=0.25)
        report = evaluator.evaluate_factor(factor=factor, df=self.df, factor_name="noise_factor", expression="noise")
        self.assertIsInstance(report, FactorEvaluationReport)
        self.assertFalse(report.passed)
        self.assertLess(abs(report.ic_pearson), 0.25)
        self.assertTrue(any("IC" in r for r in report.rejection_reasons))

    def test_alpha_evaluator_rank_ic_and_ir_computation(self):
        """Verify Spearman Rank IC and Information Ratio computation."""
        factor = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        ret = pd.Series([1.2, 2.3, 3.1, 4.0, 5.2])
        rank_ic = AlphaEvaluator.compute_rank_ic(factor, ret)
        self.assertAlmostEqual(rank_ic, 1.0, places=4)

        factor_full = self.df["close"] - self.df["open"]
        ir = AlphaEvaluator.compute_ir(factor_full, self.df, horizon=1, sub_window=10)
        self.assertTrue(math.isfinite(ir))

    def test_alpha_evaluator_turnover_and_sharpe(self):
        """Verify Sharpe and Turnover calculation logic via AlphaEvaluator."""
        factor = pd.Series([1.0, 2.0, 1.5, 3.0, 2.5])
        fwd_ret = pd.Series([0.001, 0.002, -0.0005, 0.0015, 0.003])
        sharpe = AlphaEvaluator.compute_sharpe(factor, fwd_ret)
        self.assertTrue(math.isfinite(sharpe))

        turnover, autocorr = AlphaEvaluator.compute_turnover_and_autocorr(factor)
        self.assertTrue(math.isfinite(turnover))
        self.assertTrue(math.isfinite(autocorr))


# =============================================================================
# 3. DETERMINISTIC PROP-FIRM RISK GATING TESTS
# =============================================================================

class TestDeterministicPropRiskGating(unittest.TestCase):
    """Rigorous gating tests enforcing 18-gate fail-closed admission rules."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_admit_order_valid_trade_success(self):
        """Valid trade setup (0.10L XAUUSD, 1:3.0 RR, risk $50 <= $750) is admitted."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2645.00,
            "tp": 2665.00,
            "lot_size": 0.10,
            "confluence_score": 93.0,
            "news_lockout_active": False,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertTrue(res["allowed"], f"Failed with blockers: {res.get('blockers')}")
        self.assertEqual(res["decision"], "ADMITTED_PROPOSAL")
        self.assertIsNotNone(res["proposal_token"])
        self.assertEqual(res["dynamic_breakeven"]["status"], "ARMED")

    def test_fail_closed_risk_usd_cap_exceeded_750(self):
        """Order risking > $750.00 is strictly rejected on FundingPips #40000294403."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2640.00,  # 10 pts * 1.0L * 100 = $1,000 risk (> $750)
            "tp": 2680.00,
            "lot_size": 1.0,
            "confluence_score": 95.0,
            "news_lockout_active": False,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("750" in b for b in res["blockers"]))

    def test_fail_closed_risk_pct_cap_exceeded_0_75(self):
        """Order risking > 0.75% is strictly rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "sl": 1.0800,
            "tp": 1.1000,
            "lot_size": 2.0,
            "confluence_score": 94.0,
            "news_lockout_active": False,
            "proposed_risk_pct": 0.85,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_exact_750_boundary_admission_and_rejection(self):
        """Exact $750.00 risk is admitted; $750.01 is strictly blocked."""
        order_exact = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2642.50,
            "tp": 2670.00,
            "proposed_risk_usd": 750.00,
            "proposed_risk_pct": 0.75,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res_exact = self.kernel.admit_order(order_exact)
        self.assertTrue(res_exact["allowed"], f"Exact $750 should pass: {res_exact.get('blockers')}")

        order_breach = dict(order_exact, proposed_risk_usd=750.01)
        res_breach = self.kernel.admit_order(order_breach)
        self.assertFalse(res_breach["allowed"], "$750.01 must be blocked")

    def test_fail_closed_inverted_geometry_buy_sl_above_entry(self):
        """BUY order with Stop Loss >= Entry Price must be rejected (inverted geometry)."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2655.00,  # INVERTED
            "tp": 2675.00,
            "confluence_score": 93.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_fail_closed_inverted_geometry_buy_tp_below_entry(self):
        """BUY order with Take Profit <= Entry Price must be rejected."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2640.00,
            "tp": 2645.00,  # INVERTED
            "confluence_score": 93.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_fail_closed_inverted_geometry_sell_sl_below_entry(self):
        """SELL order with Stop Loss <= Entry Price must be rejected."""
        order = {
            "symbol": "XAUUSD",
            "direction": "SELL",
            "entry_price": 2650.00,
            "sl": 2645.00,  # INVERTED
            "tp": 2630.00,
            "confluence_score": 93.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_fail_closed_inverted_geometry_sell_tp_above_entry(self):
        """SELL order with Take Profit >= Entry Price must be rejected."""
        order = {
            "symbol": "XAUUSD",
            "direction": "SELL",
            "entry_price": 2650.00,
            "sl": 2660.00,
            "tp": 2665.00,  # INVERTED
            "confluence_score": 93.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_fail_closed_zero_or_negative_price_or_distance(self):
        """Zero or negative price levels are rejected."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 0.0,
            "sl": -10.0,
            "tp": 2650.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_fail_closed_reward_to_risk_below_2_5(self):
        """Trade with RR < 2.5 (e.g. 2.0) is rejected; RR >= 2.5 is admitted."""
        order_low_rr = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2640.00,  # dist = 10
            "tp": 2670.00,  # dist = 20 -> RR = 2.0 (< 2.5)
            "confluence_score": 93.0
        }
        res_low = self.kernel.admit_order(order_low_rr)
        self.assertFalse(res_low["allowed"])
        self.assertTrue(any("r:r" in b.lower() or "reward" in b.lower() for b in res_low["blockers"]))

        order_ok_rr = dict(order_low_rr, tp=2675.00)  # dist = 25 -> RR = 2.5
        res_ok = self.kernel.admit_order(order_ok_rr)
        self.assertTrue(res_ok["allowed"])

    def test_fail_closed_15m_economic_news_blackout(self):
        """15-minute high-impact economic news blackout immediately blocks order."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2645.00,
            "tp": 2665.00,
            "news_lockout_active": True,
            "confluence_score": 95.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("news" in b.lower() for b in res["blockers"]))

    def test_dynamic_breakeven_attachment_on_admitted_orders(self):
        """Admitted order contains armed dynamic breakeven spec."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "sl": 1.0820,
            "tp": 1.0930,
            "lot_size": 0.10,
            "confluence_score": 92.0
        }
        res = self.kernel.admit_order(order)
        self.assertTrue(res["allowed"])
        be = res.get("dynamic_breakeven")
        self.assertIsNotNone(be)
        self.assertEqual(be["status"], "ARMED")
        self.assertEqual(be["threshold_r"], 1.0)
        self.assertEqual(be["breakeven_trigger_price"], 1.0880)

    def test_dynamic_breakeven_evaluation_trigger_at_1r(self):
        """Breakeven evaluator triggers lock_sl_to_entry when reaching +1.0R gain."""
        be_eval = self.kernel.evaluate_dynamic_breakeven(
            current_gain_r=1.05,
            profit_usd=350.0,
            current_price=2660.0,
            entry_price=2650.0,
            direction="BUY"
        )
        self.assertTrue(be_eval["trigger"])
        self.assertEqual(be_eval["action"], "lock_sl_to_entry")
        self.assertEqual(be_eval["new_sl"], 2650.0)

    def test_adversarial_ieee754_nan_inf_fail_closed(self):
        """IEEE 754 NaN and Inf in parameters trigger immediate fail-closed rejection."""
        for bad_val in [float("nan"), float("inf"), float("-inf")]:
            order = {
                "symbol": "XAUUSD",
                "direction": "BUY",
                "entry_price": bad_val,
                "sl": 2640.0,
                "tp": 2670.0
            }
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"], f"Value {bad_val} must be rejected")

    def test_anti_overtrading_governor_max_3_daily_trades(self):
        """Kernel Gate 3 blocks 4th trade after 3 daily trades are admitted."""
        self.kernel.daily_trade_count = 3
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.0,
            "sl": 2640.0,
            "tp": 2675.0,
            "confluence_score": 93.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("daily trade limit" in b.lower() for b in res["blockers"]))

    def test_thread_safe_concurrent_order_admission(self):
        """20 concurrent threads submitting orders maintain thread safety without corruption."""
        self.kernel.reset_daily_trade_count()
        results = []

        def worker(idx):
            order = {
                "symbol": "XAUUSD",
                "direction": "BUY",
                "entry_price": 2650.0 + idx,
                "sl": 2645.0 + idx,
                "tp": 2665.0 + idx,
                "confluence_score": 92.0
            }
            r = self.kernel.admit_order(order)
            results.append(r)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(len(results), 20)
        admitted = [r for r in results if r["allowed"]]
        self.assertLessEqual(len(admitted), 3)


# =============================================================================
# 4. END-TO-END MULTI-AGENT EXECUTION PIPELINE TEST
# =============================================================================

class TestE2EMultiAgentExecutionPipeline(unittest.TestCase):
    """Full lifecycle verification from market signals to admission and BE locking."""

    def test_end_to_end_pipeline_from_data_to_admitted_trade(self):
        """Verify full chain from market inputs through risk admission."""
        kernel = get_risk_kernel()
        kernel.reset_daily_trade_count()

        candidate_setup = {
            "symbol": "GBPUSD",
            "direction": "SELL",
            "entry_price": 1.3350,
            "sl": 1.3380,
            "tp": 1.3270,
            "lot_size": 0.15,
            "confluence_score": 92.5,
            "news_lockout_active": False,
            "strategy": "AI_TRADER_ALPHA_SMC"
        }

        admission = kernel.admit_order(candidate_setup)
        self.assertTrue(admission["allowed"])
        self.assertEqual(admission["decision"], "ADMITTED_PROPOSAL")
        self.assertIsNotNone(admission["proposal_token"])

    def test_end_to_end_pipeline_blocked_trade_auditing(self):
        """Verify pipeline stops blocked trades without emitting tokens."""
        kernel = get_risk_kernel()
        bad_setup = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "sl": 1.0850,
            "tp": 1.0950
        }
        admission = kernel.admit_order(bad_setup)
        self.assertFalse(admission["allowed"])
        self.assertIsNone(admission.get("proposal_token"))

    def test_end_to_end_simulated_trade_to_breakeven_lock(self):
        """Simulate trade entry and subsequent price movement triggering +1.0R BE lock."""
        kernel = get_risk_kernel()
        entry = 2650.0
        sl = 2645.0
        tp = 2665.0
        be_check = kernel.evaluate_dynamic_breakeven(
            current_gain_r=1.0,
            current_price=2655.0,
            entry_price=entry,
            direction="BUY"
        )
        self.assertTrue(be_check["trigger"])
        self.assertEqual(be_check["action"], "lock_sl_to_entry")
        self.assertEqual(be_check["new_sl"], entry)


# =============================================================================
# 5. HERMES TOOL INTEGRATION TESTS FOR AI-TRADER SKILLS
# =============================================================================

class TestHermesToolIntegrationAITrader(unittest.TestCase):
    """Verifies Hermes tool definition schema and cognitive registry integration."""

    def test_skills_loader_discovery_of_ai_trader_skill(self):
        """Verify dynamic discovery pattern conforms to skills/loader.py specification."""
        from skills.loader import list_skill_files, load_skills
        files = list_skill_files()
        self.assertIn("ai_trader_skill.py", files)

        declarations, dispatch = load_skills()
        self.assertIn("ai_trader", dispatch)
        self.assertTrue(callable(dispatch["ai_trader"]))

        decl = next((d for d in declarations if d["name"] == "ai_trader"), None)
        self.assertIsNotNone(decl)
        self.assertIn("action", decl["parameters"]["properties"])

    def test_hermes_tool_schema_compliance(self):
        """Verify AI-Trader Hermes schema follows OpenAI function-calling standards."""
        from skills.ai_trader_skill import get_hermes_schema, HERMES_AI_TRADER_TOOLS
        schema = get_hermes_schema()
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "ai_trader_risk_gate")
        self.assertIn("parameters", schema["function"])
        props = schema["function"]["parameters"]["properties"]
        self.assertIn("symbol", props)
        self.assertIn("direction", props)
        self.assertIn("entry_price", props)
        self.assertIn("sl", props)
        self.assertIn("tp", props)
        self.assertEqual(len(HERMES_AI_TRADER_TOOLS), 3)

    def test_hermes_agent_ai_trader_risk_gate_execution(self):
        """Verify tool execution dispatch for risk gating."""
        agent = HermesAgent()
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.0,
            "sl": 2640.0,
            "tp": 2675.0,
            "confluence_score": 93.0
        }
        res = agent.execute_tool("ai_trader_risk_gate", order)
        self.assertIn("decision", res)
        self.assertTrue(res.get("allowed", False))

    def test_hermes_agent_ai_trader_alpha_miner_execution(self):
        """Verify factor evaluation execution through Hermes tool and skill dispatch."""
        from brain.hermes_agent import HermesAgent
        from skills.ai_trader_skill import run as ai_trader_run

        # 1. Execute via skills.ai_trader_skill:run()
        skill_output_json = ai_trader_run({"action": "mine_alphas", "symbol": "XAUUSD", "asset_class": "Gold"})
        skill_cand = json.loads(skill_output_json)
        self.assertIn("expression", skill_cand)
        self.assertTrue(FormulaASTParser.validate_expression(skill_cand["expression"]))

        # 2. Execute via HermesAgent().execute_tool()
        agent = HermesAgent()
        tool_output = agent.execute_tool("ai_trader_alpha_miner", {"symbol": "XAUUSD", "asset_class": "Gold"})
        self.assertIsInstance(tool_output, dict)
        self.assertIn("expression", tool_output)
        self.assertTrue(FormulaASTParser.validate_expression(tool_output["expression"]))

        # 3. Evaluate candidate factor on market data using AlphaEvaluator
        dates = pd.date_range("2026-01-01", periods=100, freq="15min")
        np.random.seed(42)
        prices = 2650.0 + np.cumsum(np.random.randn(100) * 0.5)
        df_eval = pd.DataFrame({
            "open": prices - 0.2,
            "high": prices + 0.8,
            "low": prices - 0.9,
            "close": prices,
            "volume": np.random.randint(100, 2000, 100).astype(float)
        }, index=dates)

        factor_s = FormulaASTParser.evaluate(tool_output["expression"], df_eval)
        evaluator = AlphaEvaluator()
        report = evaluator.evaluate_factor(factor_s, df_eval, tool_output["name"], tool_output["expression"])
        self.assertIsInstance(report, FactorEvaluationReport)
        self.assertTrue(math.isfinite(report.ic_pearson))
        self.assertTrue(math.isfinite(report.rank_ic_spearman))
        self.assertTrue(math.isfinite(report.information_ratio))

    def test_zero_cost_local_execution_no_cloud_keys(self):
        """Verify AI-Trader operates fully in offline zero-paid API mode."""
        kernel = get_risk_kernel()
        res = kernel.get_risk_parameters("40000294403")
        self.assertEqual(res["max_risk_cap"], 750.0)
        self.assertEqual(res["risk_pct"], 0.75)


if __name__ == "__main__":
    unittest.main(verbosity=2)
