"""
tests/test_challenger_m3_it2_verification.py
Authoritative Empirical Verification Suite by Challenger M3_it2.1
Tests all 6 boundary vulnerability remediations + additional stress probes.
"""

import sys
import math
import time
import threading
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from trading.ai_trader.coordinator import AITraderCoordinator, get_ai_trader_coordinator


class TestChallengerM3It2EmpiricalVerification(unittest.TestCase):

    def setUp(self):
        self.kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        self.kernel.reset_daily_trade_count()
        self.coordinator = get_ai_trader_coordinator()

    # -------------------------------------------------------------
    # Vulnerability 1: Exact $750.00 vs $750.0001 Dollar Risk Boundary
    # -------------------------------------------------------------
    def test_vulnerability_1_dollar_risk_cap_strict_boundary(self):
        base_order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.00,
            "sl": 2642.50,
            "tp": 2670.00,
            "lot_size": 1.0,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }

        # 1. Exact $750.00 must pass
        order_750 = dict(base_order, proposed_risk_usd=750.00)
        res_750 = self.kernel.admit_order(order_750)
        self.assertTrue(res_750["allowed"], f"Expected $750.00 to pass: {res_750.get('blockers')}")
        self.assertEqual(res_750["decision"], "ADMITTED_PROPOSAL")

        # Reset count for next test
        self.kernel.reset_daily_trade_count()

        # 2. $750.0001 must be strictly rejected
        order_750_0001 = dict(base_order, proposed_risk_usd=750.0001)
        res_750_0001 = self.kernel.admit_order(order_750_0001)
        self.assertFalse(res_750_0001["allowed"], "Expected $750.0001 to be rejected")
        self.assertEqual(res_750_0001["decision"], "REJECTED_BLOCKED")
        self.assertTrue(any("Proposed risk dollar" in b for b in res_750_0001["blockers"]))

        # 3. $750.01 must be strictly rejected
        order_750_01 = dict(base_order, proposed_risk_usd=750.01)
        res_750_01 = self.kernel.admit_order(order_750_01)
        self.assertFalse(res_750_01["allowed"], "Expected $750.01 to be rejected")

        # 4. Percentage cap: 0.75% admitted, 0.7501% rejected
        order_pct_75 = dict(base_order, proposed_risk_pct=0.75)
        del order_pct_75["sl"]
        order_pct_75["sl"] = 2642.50
        res_pct_75 = self.kernel.admit_order(order_pct_75)
        self.assertTrue(res_pct_75["allowed"], f"Expected 0.75% to pass: {res_pct_75.get('blockers')}")

        self.kernel.reset_daily_trade_count()
        order_pct_7501 = dict(base_order, proposed_risk_pct=0.7501)
        res_pct_7501 = self.kernel.admit_order(order_pct_7501)
        self.assertFalse(res_pct_7501["allowed"], "Expected 0.7501% to be rejected")

    # -------------------------------------------------------------
    # Vulnerability 2: Adversarial NaN, Inf, -Inf, and Negative Risk
    # -------------------------------------------------------------
    def test_vulnerability_2_adversarial_nan_inf_negative_fail_closed(self):
        base_order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 1.0,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }

        adversarial_risk_values = [
            float("nan"),
            float("inf"),
            float("-inf"),
            -500.0,
            -0.01,
            0.0
        ]

        for bad_val in adversarial_risk_values:
            # Test in proposed_risk_usd
            o_usd = dict(base_order, proposed_risk_usd=bad_val)
            res = self.kernel.admit_order(o_usd)
            self.assertFalse(
                res["allowed"],
                f"Adversarial proposed_risk_usd={bad_val} must be rejected, got allowed=True"
            )
            self.assertEqual(res["decision"], "REJECTED_BLOCKED")

            # Test in proposed_risk_pct
            o_pct = dict(base_order, proposed_risk_pct=bad_val)
            res_pct = self.kernel.admit_order(o_pct)
            self.assertFalse(
                res_pct["allowed"],
                f"Adversarial proposed_risk_pct={bad_val} must be rejected, got allowed=True"
            )
            self.assertEqual(res_pct["decision"], "REJECTED_BLOCKED")

        # Test NaN in price levels and balance
        for field in ["entry_price", "sl", "tp", "lot_size", "balance"]:
            for bad_float in [float("nan"), float("inf"), float("-inf")]:
                o_bad = dict(base_order)
                o_bad[field] = bad_float
                res_bad = self.kernel.admit_order(o_bad)
                self.assertFalse(
                    res_bad["allowed"],
                    f"Adversarial {field}={bad_float} must be rejected fail-closed"
                )

    # -------------------------------------------------------------
    # Vulnerability 3: Non-Numeric Strings in confluence_score No Crash
    # -------------------------------------------------------------
    def test_vulnerability_3_non_numeric_confluence_strings_no_crash(self):
        base_order = {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.3000,
            "sl": 1.2950,
            "tp": 1.3150,
            "lot_size": 1.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }

        malformed_confluences = [
            "not_a_float",
            "NaN",
            "Infinity",
            "--123",
            "None",
            "null",
            "",
            "   "
        ]

        for conf in malformed_confluences:
            order = dict(base_order, confluence_score=conf)
            try:
                res = self.kernel.admit_order(order)
                self.assertIsInstance(res, dict)
                self.assertFalse(res["allowed"], f"Malformed confluence '{conf}' must be rejected fail-closed")
                self.assertEqual(res["decision"], "REJECTED_BLOCKED")
            except Exception as e:
                self.fail(f"admit_order crashed with {type(e).__name__} on confluence_score='{conf}': {e}")

        # Also verify AITraderCoordinator handles non-numeric telemetry without crashing
        bad_telemetry = {
            "macro_score": "malformed_str",
            "orderflow_score": "unparseable",
            "stat_arb_score": "not_numeric",
            "confluence_score": "bad_score"
        }
        try:
            candidate = self.coordinator.analyze_and_synthesize("EURUSD", bad_telemetry)
            self.assertIsNotNone(candidate)
            self.assertFalse(candidate.admitted)
        except Exception as e:
            self.fail(f"AITraderCoordinator.analyze_and_synthesize crashed with {type(e).__name__}: {e}")

    # -------------------------------------------------------------
    # Vulnerability 4: Empty/None Symbol Rejected Fail-Closed
    # -------------------------------------------------------------
    def test_vulnerability_4_empty_or_none_symbol_rejected(self):
        base_order = {
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 1.0,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }

        invalid_symbols = [
            None,
            "",
            "   ",
            "\t\n",
            False
        ]

        for sym in invalid_symbols:
            order = dict(base_order, symbol=sym)
            res = self.kernel.admit_order(order)
            self.assertFalse(res["allowed"], f"Symbol '{sym}' must be rejected")
            self.assertEqual(res["decision"], "REJECTED_BLOCKED")
            self.assertTrue(
                any("symbol" in b.lower() for b in res.get("blockers", [])),
                f"Blocker must mention symbol: {res.get('blockers')}"
            )

        # Also test order without symbol or ticker key
        order_no_sym = dict(base_order)
        res_no_sym = self.kernel.admit_order(order_no_sym)
        self.assertFalse(res_no_sym["allowed"])
        self.assertEqual(res_no_sym["decision"], "REJECTED_BLOCKED")

        # Also test evaluate_admission directly
        res_eval = self.kernel.evaluate_admission(symbol="")
        self.assertFalse(res_eval["allowed"])
        self.assertTrue(any("symbol" in b.lower() for b in res_eval.get("blockers", [])))

    # -------------------------------------------------------------
    # Vulnerability 5: Large Arbitrary-Precision Integers (10**400) No Crash
    # -------------------------------------------------------------
    def test_vulnerability_5_large_arbitrary_precision_integers_no_crash(self):
        base_order = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1150,
            "lot_size": 1.0,
            "confluence_score": 92.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }

        huge_int = 10**400
        tested_fields = [
            "entry_price",
            "sl",
            "tp",
            "lot_size",
            "balance",
            "proposed_risk_usd",
            "proposed_risk_pct",
            "confluence_score"
        ]

        for field in tested_fields:
            order = dict(base_order, **{field: huge_int})
            try:
                res = self.kernel.admit_order(order)
                self.assertIsInstance(res, dict)
                self.assertFalse(res["allowed"], f"Huge int in {field} must fail closed")
                self.assertEqual(res["decision"], "REJECTED_BLOCKED")
            except OverflowError as e:
                self.fail(f"admit_order crashed with unhandled OverflowError on {field}=10**400: {e}")
            except Exception as e:
                self.fail(f"admit_order crashed with {type(e).__name__} on {field}=10**400: {e}")

    # -------------------------------------------------------------
    # Vulnerability 6: Concurrency Governor (50 Threads) Admits Exactly 3, Blocks 47
    # -------------------------------------------------------------
    def test_vulnerability_6_concurrency_governor_50_threads(self):
        self.kernel.reset_daily_trade_count()
        results = []
        threads = []
        barrier = threading.Barrier(50)

        def worker(thread_idx: int):
            order = {
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": 1.1000,
                "sl": 1.0950,
                "tp": 1.1150,
                "lot_size": 0.5,
                "proposed_risk_usd": 250.0,
                "confluence_score": 95.0,
                "account_id": "40000294403",
                "balance": 100000.0,
                "thread_idx": thread_idx
            }
            # Wait for all 50 threads to be ready so they strike concurrently
            barrier.wait()
            res = self.kernel.admit_order(order)
            results.append(res)

        for i in range(50):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), 50, "All 50 threads must complete")
        admitted = [r for r in results if r["allowed"]]
        rejected = [r for r in results if not r["allowed"]]

        self.assertEqual(len(admitted), 3, f"Exactly 3 trades must be admitted, got {len(admitted)}")
        self.assertEqual(len(rejected), 47, f"Exactly 47 trades must be blocked, got {len(rejected)}")
        self.assertEqual(self.kernel.daily_trade_count, 3, f"Daily trade count must be 3, got {self.kernel.daily_trade_count}")

        # Check that rejected orders failed due to overtrading governor
        for rej in rejected:
            self.assertTrue(
                any("overtrading" in b.lower() or "limit" in b.lower() or "daily" in b.lower() for b in rej["blockers"]),
                f"Expected overtrading blocker in {rej['blockers']}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
