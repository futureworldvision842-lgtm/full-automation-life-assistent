"""
tests/test_m1_breakeven_lock_stress.py
========================================================================================
Adversarial Stress Test Suite for Breakeven Lock on Positions Secured at Breakeven.
Author: Challenger 1 (critic, specialist)
Repository: Jarvis Command Center

Tasks Covered:
1. Stress test the breakeven lock check on positions already secured at breakeven (sl == entry_price).
2. Edge cases around epsilon tolerance, direction, price deviations, profit regimes.
3. Verification of GBPUSD SELL #13002987 breakeven lock status across reasoning API.
========================================================================================
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from core.trading.reasoning import (
    BigSharksReasoningEngine,
    get_trading_reasoning,
    get_reasoning_engine
)
from src.risk_manager import RiskManager
from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from trading.risk_kernel.admission_kernel import DeterministicRiskKernel


class TestBreakevenLockSecuredPositionsStress(unittest.TestCase):
    """
    Adversarial stress testing specifically targeting positions already secured at breakeven (sl == entry_price).
    """

    def setUp(self):
        self.reasoning = BigSharksReasoningEngine()
        self.pipdance = PipdanceFastTrackEngine()
        self.risk_kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)

    def test_01_gbpusd_sell_13002987_exact_breakeven_locked(self):
        """Verify position #13002987 (GBPUSD SELL) reports breakeven_locked=True."""
        res = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=1.33675,
            current_price=1.33498,
            sl_price=1.33675,
            direction="SELL",
            profit_usd=35.40
        )
        self.assertTrue(res["breakeven_locked"], f"Expected breakeven_locked True, got: {res}")
        self.assertEqual(res["action"], "maintain_breakeven_lock")
        self.assertEqual(res["reason"], "breakeven_already_secured")
        self.assertEqual(res["new_sl"], 1.33675)
        self.assertAlmostEqual(res["current_r"], 1.0)

    def test_02_buy_positions_exact_breakeven_locked(self):
        """Verify multiple asset classes for BUY positions where sl == entry_price."""
        assets = [
            ("EURUSD", 1.08500, 1.08950, 1.08500, 45.0),
            ("XAUUSD", 2700.00, 2725.50, 2700.00, 255.0),
            ("BTCUSD", 62500.0, 63800.0, 62500.0, 130.0),
            ("USDJPY", 145.200, 146.500, 145.200, 85.0),
        ]
        for symbol, entry, current, sl, profit in assets:
            with self.subTest(symbol=symbol):
                res = self.reasoning.evaluate_dynamic_breakeven(
                    entry_price=entry,
                    current_price=current,
                    sl_price=sl,
                    direction="BUY",
                    profit_usd=profit
                )
                self.assertTrue(res["breakeven_locked"])
                self.assertEqual(res["action"], "maintain_breakeven_lock")
                self.assertEqual(res["reason"], "breakeven_already_secured")
                self.assertEqual(res["new_sl"], entry)

    def test_03_epsilon_deviations_near_entry(self):
        """
        Test epsilon tolerance around sl == entry_price (< 1e-4).
        Broker execution or tick rounding can cause microscopic discrepancies.
        """
        entry = 1.33675
        current = 1.33400
        # Tolerated epsilons (< 1e-4)
        tolerated_sls = [
            entry + 1e-5,
            entry - 1e-5,
            entry + 5e-5,
            entry - 5e-5,
            entry + 9e-5,
            entry - 9e-5,
        ]
        for sl in tolerated_sls:
            with self.subTest(sl=sl):
                res = self.reasoning.evaluate_dynamic_breakeven(
                    entry_price=entry,
                    current_price=current,
                    sl_price=sl,
                    direction="SELL",
                    profit_usd=25.0
                )
                self.assertTrue(
                    res["breakeven_locked"],
                    f"SL {sl} near entry {entry} should be recognized as already secured. Got: {res}"
                )
                self.assertEqual(res["action"], "maintain_breakeven_lock")
                self.assertEqual(res["reason"], "breakeven_already_secured")

    def test_04_position_retraces_to_entry_price(self):
        """
        Adversarial Scenario: Position was secured at breakeven, and now current price
        has pulled back directly to the entry price (profit = $0.00).
        Breakeven lock must STILL be reported as True!
        """
        entry = 1.33675
        sl = 1.33675
        current = 1.33675  # Price retraced exactly to entry
        res = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=entry,
            current_price=current,
            sl_price=sl,
            direction="SELL",
            profit_usd=0.0
        )
        self.assertTrue(res["breakeven_locked"])
        self.assertEqual(res["action"], "maintain_breakeven_lock")
        self.assertEqual(res["reason"], "breakeven_already_secured")
        self.assertEqual(res["new_sl"], entry)

    def test_05_position_retraces_slightly_past_entry_floating_loss(self):
        """
        Adversarial Scenario: Spread widens or tick slips slightly past entry (minor drawdown before stop triggers).
        The position's SL is STILL physically at entry (breakeven secured).
        """
        entry = 1.33675
        sl = 1.33675
        current = 1.33685  # 1 pip past entry on SELL
        res = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=entry,
            current_price=current,
            sl_price=sl,
            direction="SELL",
            profit_usd=-1.00
        )
        self.assertTrue(res["breakeven_locked"])
        self.assertEqual(res["action"], "maintain_breakeven_lock")
        self.assertEqual(res["reason"], "breakeven_already_secured")

    def test_06_pipdance_engine_already_protected_check(self):
        """
        Verify PipdanceFastTrackEngine.check_breakeven_trigger handles positions
        where sl is already at or past entry (already_protected).
        """
        # BUY position: SL == entry
        buy_pos = {
            "ticket": "13002988",
            "symbol": "EURUSD",
            "type": "BUY",
            "price_open": 1.08500,
            "sl": 1.08500,
            "tp": 1.09500,
            "profit": 30.0,
            "volume": 0.10,
            "price_current": 1.08800
        }
        buy_res = self.pipdance.check_breakeven_trigger(
            position=buy_pos,
            current_price=1.08800,
            breakeven_profit_cap=7.50
        )
        self.assertEqual(buy_res["action"], "already_protected")
        self.assertFalse(buy_res["trigger"])

        # SELL position: SL == entry (#13002987)
        sell_pos = {
            "ticket": "13002987",
            "symbol": "GBPUSD",
            "type": "SELL",
            "price_open": 1.33675,
            "sl": 1.33675,
            "tp": 1.33000,
            "profit": 35.40,
            "volume": 0.10,
            "price_current": 1.33498
        }
        sell_res = self.pipdance.check_breakeven_trigger(
            position=sell_pos,
            current_price=1.33498,
            breakeven_profit_cap=7.50
        )
        self.assertEqual(sell_res["action"], "already_protected")
        self.assertFalse(sell_res["trigger"])

    def test_07_api_reasoning_payload_gbpusd_be_status(self):
        """
        Verify the master get_trading_reasoning('GBPUSD') endpoint returns
        GBPUSD SELL ticket #13002987 with breakeven locked status.
        """
        payload = get_trading_reasoning("GBPUSD")
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["account"], "40000294403")

        latest_setups = payload.get("latest_setups", [])
        self.assertGreater(len(latest_setups), 0)

        gbp_setup = latest_setups[0]
        self.assertEqual(gbp_setup["symbol"], "GBPUSD")
        self.assertEqual(gbp_setup["direction"], "SELL")

        be_status = gbp_setup.get("breakeven_status", {})
        self.assertTrue(
            be_status.get("breakeven_locked"),
            f"Expected GBPUSD setup breakeven_locked=True, got {be_status}"
        )
        self.assertEqual(be_status.get("action"), "maintain_breakeven_lock")
        self.assertEqual(be_status.get("reason"), "breakeven_already_secured")
        self.assertAlmostEqual(be_status.get("new_sl"), 1.33675)

    def test_08_degenerate_entry_price_guard(self):
        """
        Adversarial Edge Case: Corrupt or zero entry price must NOT trigger
        is_already_locked and must fail safely.
        """
        # Entry price 0.0
        res_zero = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=0.0,
            current_price=1.33400,
            sl_price=0.0,
            direction="BUY"
        )
        self.assertFalse(res_zero["breakeven_locked"])
        self.assertEqual(res_zero["reason"], "invalid_sl_distance")

        # Entry price negative
        res_neg = self.reasoning.evaluate_dynamic_breakeven(
            entry_price=-100.0,
            current_price=-90.0,
            sl_price=-100.0,
            direction="BUY"
        )
        self.assertFalse(res_neg["breakeven_locked"])
        self.assertEqual(res_neg["reason"], "invalid_sl_distance")


if __name__ == "__main__":
    unittest.main()
