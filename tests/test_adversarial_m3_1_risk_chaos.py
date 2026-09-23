"""
tests/test_adversarial_m3_1_risk_chaos.py — Milestone M3.1 Risk Kernel Chaos & Boundary Stress Suite
=====================================================================================================
Adversarial challenge and boundary stress harness targeting:
  1. DeterministicRiskKernel.admit_order()
  2. DeterministicRiskKernel.evaluate_admission()
  3. AITraderCoordinator (Consensus, HKUDS Quality, and Candidate Setup Formulation)

Challenge Dimensions:
  - Exact $750.00 vs $750.0001 dollar risk boundary
  - 0.75% vs 0.7501% percentage risk boundary
  - Inverted geometry with micro-pips and zero distance (SL = Entry, TP = Entry)
  - Extreme floating point injection: NaN, Inf, -Inf, 1e308, integer overflow (10**400)
  - High-concurrency race condition: 50 threads hammering admit_order() simultaneously
  - News lockout toggle under live concurrent requests
  - Malformed/missing dictionary keys and fail-closed integrity

Author: Challenger M3.1 (Empirical Challenger: critic, specialist)
Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of forbidden identity. Deterministic risk <= 0.75%, $750 cap.
=====================================================================================================
"""

import sys
import math
import time
import threading
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from trading.ai_trader.coordinator import AITraderCoordinator, get_ai_trader_coordinator
from trading.ai_trader.types import Direction, ConsensusVerdict, CandidateSetup


class TestRiskBoundaryConditions(unittest.TestCase):
    """Stress tests exact boundary thresholds for dollar cap and percentage risk."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_exact_750_dollar_risk_admitted(self):
        """Exact $750.00 risk must pass all gates on account #40000294403."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2642.50,
            "tp": 2670.00,
            "lot_size": 1.0,
            "proposed_risk_usd": 750.00,
            "proposed_risk_pct": 0.75,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertTrue(res["allowed"], f"Exact $750.00 must be admitted: {res.get('blockers')}")
        self.assertEqual(res["decision"], "ADMITTED_PROPOSAL")

    def test_750_0001_dollar_risk_rejected(self):
        """
        Adversarial Boundary: $750.0001 exceeds the $750.00 dollar cap.
        The kernel must fail closed and reject any risk strictly greater than $750.00.
        """
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2642.50,
            "tp": 2670.00,
            "lot_size": 1.0,
            "proposed_risk_usd": 750.0001,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "$750.0001 exceeds $750.00 cap and must be blocked")
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_750_01_dollar_risk_rejected(self):
        """$750.01 risk exceeds $750.00 cap and must be strictly blocked."""
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2642.50,
            "tp": 2670.00,
            "lot_size": 1.0,
            "proposed_risk_usd": 750.01,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "$750.01 must be blocked")

    def test_exact_0_75_pct_risk_admitted(self):
        """Exact 0.75% risk is admitted on $100k account."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_pct": 0.75,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertTrue(res["allowed"], f"Exact 0.75% must be admitted: {res.get('blockers')}")

    def test_0_7501_pct_risk_rejected(self):
        """0.7501% risk exceeds 0.75% cap and must be strictly blocked."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_pct": 0.7501,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "0.7501% must be blocked")
        self.assertTrue(any("exceeds max allowed" in b.lower() for b in res["blockers"]))

    def test_0_80_pct_risk_rejected(self):
        """0.80% risk must be blocked."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_pct": 0.80,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])


class TestGeometryAndDistanceBoundaries(unittest.TestCase):
    """Stress tests inverted geometry, zero distance, micro-pips, and negative prices."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_inverted_buy_sl_equal_entry(self):
        """BUY order where SL == Entry (zero distance) must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.1000,
            "tp": 1.1200,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() or "distance" in b.lower() for b in res["blockers"]))

    def test_inverted_buy_tp_equal_entry(self):
        """BUY order where TP == Entry (zero profit distance) must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0900,
            "tp": 1.1000,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_inverted_sell_sl_equal_entry(self):
        """SELL order where SL == Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.1000,
            "sl": 1.1000,
            "tp": 1.0800,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() or "distance" in b.lower() for b in res["blockers"]))

    def test_inverted_sell_tp_equal_entry(self):
        """SELL order where TP == Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.1000,
            "sl": 1.1100,
            "tp": 1.1000,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_inverted_buy_sl_above_entry(self):
        """BUY order with SL > Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.1050,
            "tp": 1.1200,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_inverted_buy_tp_below_entry(self):
        """BUY order with TP < Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.0900,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_inverted_sell_sl_below_entry(self):
        """SELL order with SL < Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.0800,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_inverted_sell_tp_above_entry(self):
        """SELL order with TP > Entry must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.1000,
            "sl": 1.1100,
            "tp": 1.1200,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("geometry" in b.lower() for b in res["blockers"]))

    def test_zero_distance_sl_tp(self):
        """Both SL and TP equal Entry price (flat line) must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.1000,
            "tp": 1.1000,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_micro_pip_distance_zero_guard(self):
        """Micro-pip distance (1e-10) below minimum precision threshold (1e-9) must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.1000 - 1e-10,
            "tp": 1.1200,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])
        self.assertTrue(any("distance" in b.lower() for b in res["blockers"]))

    def test_negative_price_levels(self):
        """Negative or zero prices must fail closed."""
        for bad_p in [0.0, -1.0, -100.0]:
            order = {
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": bad_p,
                "sl": 1.0900,
                "tp": 1.1200,
                "lot_size": 0.1
            }
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"])


class TestExtremeFloatingPointAndOverflowInjection(unittest.TestCase):
    """Stress tests IEEE 754 NaN/Inf injection, negative inputs, and large numbers."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_nan_in_entry_price_rejected(self):
        """NaN in entry_price must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": float("nan"),
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_nan_in_sl_rejected(self):
        """NaN in sl must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": float("nan"),
            "tp": 1.1150,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_nan_in_tp_rejected(self):
        """NaN in tp must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": float("nan"),
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_nan_in_lot_size_rejected(self):
        """NaN in lot_size must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": float("nan")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_nan_in_balance_rejected(self):
        """NaN in balance must be rejected."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "balance": float("nan")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_nan_in_proposed_risk_usd_fails_closed(self):
        """
        Adversarial Float Injection: NaN in proposed_risk_usd must FAIL CLOSED.
        The kernel must NOT silently ignore NaN and admit the order.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_usd": float("nan")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with NaN proposed_risk_usd must be rejected")
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_nan_in_proposed_risk_pct_fails_closed(self):
        """
        Adversarial Float Injection: NaN in proposed_risk_pct must FAIL CLOSED.
        The kernel must NOT silently ignore NaN and admit the order.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_pct": float("nan")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with NaN proposed_risk_pct must be rejected")
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_inf_in_proposed_risk_usd_fails_closed(self):
        """
        Adversarial Float Injection: Inf in proposed_risk_usd must FAIL CLOSED.
        The kernel must NOT silently ignore Inf and admit the order.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_usd": float("inf")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with Inf proposed_risk_usd must be rejected")
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_inf_in_proposed_risk_pct_fails_closed(self):
        """
        Adversarial Float Injection: Inf in proposed_risk_pct must FAIL CLOSED.
        The kernel must NOT silently ignore Inf and admit the order.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_pct": float("inf")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with Inf proposed_risk_pct must be rejected")

    def test_negative_inf_in_proposed_risk_usd_fails_closed(self):
        """
        Adversarial Float Injection: -Inf in proposed_risk_usd must FAIL CLOSED.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_usd": float("-inf")
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with -Inf proposed_risk_usd must be rejected")

    def test_negative_proposed_risk_usd_fails_closed(self):
        """
        Adversarial Injection: Negative proposed_risk_usd must FAIL CLOSED.
        The kernel must NOT silently ignore negative risk and admit the order.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "proposed_risk_usd": -500.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with negative proposed_risk_usd must be rejected")

    def test_huge_integer_overflow_int_10_400_no_crash(self):
        """
        Adversarial Overflow: Passing int 10**400 in entry_price must NOT crash
        the system with unhandled OverflowError; it must fail closed safely.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 10**400,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1
        }
        try:
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"])
        except OverflowError:
            self.fail("admit_order() crashed with unhandled OverflowError on 10**400 entry_price!")

    def test_huge_integer_overflow_sl_10_400_no_crash(self):
        """Passing int 10**400 in SL must fail closed without crashing."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 10**400,
            "tp": 1.1150,
            "lot_size": 0.1
        }
        try:
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"])
        except OverflowError:
            self.fail("admit_order() crashed with unhandled OverflowError on 10**400 sl!")

    def test_float_1e308_extreme_bound(self):
        """1e308 float boundary in entry_price fails closed without crashing."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1e308,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])


class TestHighConcurrencyAndRaceConditions(unittest.TestCase):
    """Stress tests high concurrency and multi-threaded race conditions."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_50_threads_daily_trade_limit_governor(self):
        """
        High Concurrency Stress: 50 threads hammering admit_order() simultaneously.
        Must admit EXACTLY 3 trades (the daily governor limit) and block 47 trades.
        Daily trade count must equal exactly 3 with zero state corruption.
        """
        results = []
        errors = []

        def worker(idx):
            try:
                order = {
                    "symbol": "XAUUSD",
                    "direction": "BUY",
                    "entry_price": 2650.0 + idx,
                    "sl": 2642.5 + idx,
                    "tp": 2670.0 + idx,
                    "lot_size": 1.0,
                    "proposed_risk_usd": 750.00,
                    "proposed_risk_pct": 0.75,
                    "confluence_score": 92.0
                }
                res = self.kernel.admit_order(order)
                results.append(res)
            except Exception as e:
                errors.append((idx, e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors occurred: {errors}")
        self.assertEqual(len(results), 50)
        admitted = [r for r in results if r.get("allowed")]
        blocked = [r for r in results if not r.get("allowed")]

        self.assertEqual(len(admitted), 3, f"Expected exactly 3 admitted trades, got {len(admitted)}")
        self.assertEqual(len(blocked), 47, f"Expected 47 blocked trades, got {len(blocked)}")
        self.assertEqual(self.kernel.daily_trade_count, 3)

    def test_news_lockout_toggle_under_live_concurrency(self):
        """
        High Concurrency Stress: 50 threads with dynamic news lockout toggling.
        Zero orders with news_lockout_active=True must ever be admitted.
        """
        results = []
        errors = []

        def worker(idx):
            try:
                # Even threads have news lockout active
                news_active = (idx % 2 == 0)
                order = {
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "entry_price": 1.1000 + (idx * 0.0001),
                    "sl": 1.0950 + (idx * 0.0001),
                    "tp": 1.1150 + (idx * 0.0001),
                    "lot_size": 0.1,
                    "confluence_score": 92.0,
                    "news_lockout_active": news_active
                }
                res = self.kernel.admit_order(order)
                results.append((idx, news_active, res))
            except Exception as e:
                errors.append((idx, e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        news_active_admitted = [r for idx, news_active, r in results if news_active and r.get("allowed")]
        self.assertEqual(len(news_active_admitted), 0, "No order with news lockout active can be admitted!")


class TestMalformedAndMissingKeysChaos(unittest.TestCase):
    """Stress tests malformed payloads, missing critical keys, and type corruptions."""

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()

    def test_none_order_payload(self):
        """None order payload fails closed cleanly."""
        res = self.kernel.admit_order(None)
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_empty_dict_payload(self):
        """Empty dictionary fails closed cleanly."""
        res = self.kernel.admit_order({})
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision"], "REJECTED_BLOCKED")

    def test_non_dict_payload_types(self):
        """Non-dict payloads (string, list, int) fail closed cleanly."""
        for bad in ["not_a_dict", [1, 2, 3], 9999]:
            res = self.kernel.admit_order(bad)
            self.assertFalse(res["allowed"])

    def test_missing_symbol_rejected(self):
        """
        Adversarial Missing Key: Order with symbol: None must FAIL CLOSED.
        Trading orders without a valid ticker symbol cannot be admitted.
        """
        order = {
            "symbol": None,
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "confluence_score": 92.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with symbol: None must be rejected")

    def test_empty_string_symbol_rejected(self):
        """Order with symbol: '' (empty string) must FAIL CLOSED."""
        order = {
            "symbol": "",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "confluence_score": 92.0
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"], "Order with empty symbol must be rejected")

    def test_missing_direction_rejected(self):
        """Missing or None direction fails closed."""
        order = {
            "symbol": "EURUSD",
            "direction": None,
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_missing_price_levels_rejected(self):
        """Missing entry_price, sl, or tp fails closed."""
        for missing_key in ["entry_price", "sl", "tp"]:
            order = {
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": 1.1000,
                "sl": 1.0950,
                "tp": 1.1150
            }
            del order[missing_key]
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"])

    def test_non_numeric_price_strings_rejected(self):
        """String price inputs like 'not_a_float' fail closed without unhandled crash."""
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": "not_a_float",
            "sl": 1.0950,
            "tp": 1.1150
        }
        res = self.kernel.admit_order(order)
        self.assertFalse(res["allowed"])

    def test_non_numeric_confluence_score_no_crash(self):
        """
        Adversarial Input: confluence_score='not_a_float' must NOT crash with ValueError;
        it must fail closed cleanly.
        """
        order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 0.1,
            "confluence_score": "not_a_float"
        }
        try:
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"])
        except ValueError:
            self.fail("admit_order() crashed with unhandled ValueError on non-numeric confluence_score string!")


class TestAITraderCoordinatorStress(unittest.TestCase):
    """Stress tests AITraderCoordinator multi-agent synthesis under chaos."""

    def setUp(self):
        self.coordinator = AITraderCoordinator()

    def test_coordinator_synthesize_empty_and_corrupt_datahub(self):
        """Empty or None datahub snapshot handled gracefully without crashing."""
        for bad_dh in [None, {}, {"corrupt_key": [1, 2]}]:
            verdict = self.coordinator.analyze_and_synthesize("EURUSD", bad_dh)
            self.assertIsInstance(verdict, ConsensusVerdict)
            self.assertFalse(verdict.admitted)

    def test_coordinator_synthesize_non_numeric_scores_no_crash(self):
        """
        Adversarial Telemetry: datahub with string scores ('not_a_float') must NOT crash
        with unhandled ValueError.
        """
        bad_dh = {
            "macro_score": "not_a_float",
            "orderflow_score": 90.0
        }
        try:
            verdict = self.coordinator.analyze_and_synthesize("EURUSD", bad_dh)
            self.assertFalse(verdict.admitted)
        except ValueError:
            self.fail("analyze_and_synthesize() crashed with unhandled ValueError on non-numeric macro_score!")

    def test_coordinator_signal_quality_nan_inf_geometry(self):
        """Signal quality scoring with NaN/Inf prices returns weak quality score."""
        from trading.ai_trader.types import OrderFlowVerdict, MacroVerdict
        dummy_flow = OrderFlowVerdict(
            symbol="EURUSD",
            bias="BULLISH",
            conviction=0.8,
            dom_imbalance_ratio=1.2,
            dom_bias="BULLISH_ABSORPTION",
            session_killzone="LONDON",
            killzone_active=True,
            spread_status="NORMAL",
            spread_multiplier=1.1,
            sub_2ms_ready=True,
            absorption_divergence="NEUTRAL",
            whale_walls_count=1,
            turtle_soup_swept=False,
            rationale="Test"
        )
        dummy_macro = MacroVerdict(
            symbol="EURUSD",
            bias="BULLISH",
            conviction=0.8,
            macro_regime="BALANCED_RANGE",
            defcon_level=5,
            geopolitical_risk_score=20.0,
            macro_multiplier=1.0,
            news_lockout_active=False,
            dxy_trend="BEARISH",
            rationale="Test"
        )
        score = self.coordinator.score_signal_quality(
            symbol="EURUSD",
            direction="BUY",
            entry_price=float("nan"),
            sl=1.0950,
            tp=1.1150,
            orderflow_verdict=dummy_flow,
            macro_verdict=dummy_macro,
            datahub={}
        )
        self.assertLess(score.verifiability, 5.0)

    def test_coordinator_e2e_rejection_of_chaotic_signals(self):
        """Coordinator candidate setup formulation returns None when conditions are unadmitted."""
        bad_dh = {
            "current_price": float("nan"),
            "news_lockout_active": True
        }
        setup = self.coordinator.formulate_candidate_setup("EURUSD", bad_dh)
        self.assertIsNone(setup, "Setup must be None when input data is corrupt/unadmitted")


if __name__ == "__main__":
    unittest.main()
