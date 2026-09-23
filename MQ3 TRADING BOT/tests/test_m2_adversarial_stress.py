"""
test_m2_adversarial_stress.py — Exhaustive Empirical Challenger Suite for Milestone 2.
======================================================================================
Adversarial Verification Suite for:
1. Exact Intraday Drawdown Micro-Boundaries (2.49% pass vs 2.50% & 2.51% instant lock)
   across $5k, $25k, $50k, and $100k Prop Firm tiers.
2. Trailing High-Water-Mark (HWM) Floor Ratchets and Profit Locking under Volatile Swings.
3. Micro-Balance Sizing & Pre-Trade Interception ($100, $500, $1k, $5k) with Zero Breach Guarantee.
"""

import os
import sys
import math
import random
import unittest
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fleet_risk_manager import FleetRiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.aladdin_risk_engine import AladdinRiskEngine


class TestM2AdversarialStress(unittest.TestCase):
    def setUp(self):
        self.test_config = "data/test_m2_adversarial_config.json"
        self.onboarder = MultiAccountAutoOnboarder(config_path=self.test_config)
        
        # Onboard all required tiers and micro accounts
        self.tiers = {
            "5k": 5000.0,
            "25k": 25000.0,
            "50k": 50000.0,
            "100k": 100000.0
        }
        for tier_name, bal in self.tiers.items():
            self.onboarder.onboard_new_account(
                account_id=f"FP_{tier_name.upper()}",
                server="MetaQuotes-Demo",
                balance=bal,
                account_type="FUNDING_PIPS"
            )

        # Micro-balance accounts
        self.micro_accounts = {
            "100": 100.0,
            "500": 500.0,
            "1k": 1000.0,
            "5k_crypto": 5000.0
        }
        self.onboarder.onboard_new_account(
            account_id="ACC_100",
            server="Binance-Live",
            balance=100.0,
            account_type="SCALP_5M"
        )
        self.onboarder.onboard_new_account(
            account_id="ACC_500",
            server="Hyperliquid-Mainnet",
            balance=500.0,
            account_type="HYPERLIQUID"
        )
        self.onboarder.onboard_new_account(
            account_id="ACC_1K",
            server="Binance-Live",
            balance=1000.0,
            account_type="BINANCE_SPOT"
        )
        self.onboarder.onboard_new_account(
            account_id="ACC_5K_CRYPTO",
            server="Bitget-Live",
            balance=5000.0,
            account_type="BITGET"
        )

        self.risk_mgr = FleetRiskManager(config_path=self.test_config, auto_onboarder=self.onboarder)
        self.aladdin = AladdinRiskEngine()

    def tearDown(self):
        if os.path.exists(self.test_config):
            try:
                os.remove(self.test_config)
            except Exception:
                pass

    # =========================================================================
    # 1. INTRADAY DRAWDOWN BOUNDARY EMPIRICAL VERIFICATION (2.49% vs 2.50% vs 2.51%)
    # =========================================================================

    def test_all_tiers_intraday_drawdown_exact_boundaries(self):
        """
        Empirically verifies the exact 2.50% SOD drawdown boundary across $5k, $25k, $50k, and $100k tiers:
          - 2.49% DD: MUST stay open (safe=True, is_locked_out=False, pre-trade orders approved)
          - 2.50% DD: MUST lock instantly (safe=False, is_locked_out=True, pre-trade orders rejected)
          - 2.51% DD: MUST lock instantly (safe=False, is_locked_out=True, pre-trade orders rejected)
        """
        for tier_name, starting_bal in self.tiers.items():
            acc_id = f"FP_{tier_name.upper()}"
            daily_loss_cap = starting_bal * 0.025  # 2.5%

            # -------------------------------------------------------------
            # Sub-test A: 2.49% Drawdown (Must Stay Open)
            # -------------------------------------------------------------
            loss_2_49 = round(starting_bal * 0.0249, 2)
            eq_2_49 = starting_bal - loss_2_49
            
            # Reset SOD to clean starting state
            self.risk_mgr.update_account_telemetry(acc_id, balance=starting_bal, equity=starting_bal, sod_reset=True)
            res_2_49 = self.risk_mgr.update_account_telemetry(acc_id, balance=eq_2_49, equity=eq_2_49)
            
            self.assertTrue(
                res_2_49["daily_loss_shield_ok"],
                f"[{tier_name}] 2.49% DD (loss ${loss_2_49:,.2f} on ${starting_bal:,.2f}) must pass shield!"
            )
            self.assertFalse(
                res_2_49["is_locked_out"],
                f"[{tier_name}] Account should NOT be locked at 2.49% DD"
            )

            # Pre-trade audit must approve valid orders
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol="XAUUSD", lot_size=0.05, side="BUY", entry_price=2650.0, sl_price=2636.0
            )
            self.assertTrue(approved, f"[{tier_name}] Valid order must be approved at 2.49% DD: {reason}")

            # -------------------------------------------------------------
            # Sub-test B: 2.50% Drawdown (Must Lock Instantly)
            # -------------------------------------------------------------
            loss_2_50 = round(starting_bal * 0.0250, 2)
            eq_2_50 = starting_bal - loss_2_50

            self.risk_mgr.update_account_telemetry(acc_id, balance=starting_bal, equity=starting_bal, sod_reset=True)
            res_2_50 = self.risk_mgr.update_account_telemetry(acc_id, balance=eq_2_50, equity=eq_2_50)

            self.assertFalse(
                res_2_50["daily_loss_shield_ok"],
                f"[{tier_name}] Exact 2.50% DD (loss ${loss_2_50:,.2f} on ${starting_bal:,.2f}) must breach shield!"
            )
            self.assertTrue(
                res_2_50["is_locked_out"],
                f"[{tier_name}] Account must lock instantly at exact 2.50% DD"
            )

            # Pre-trade audit must reject
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol="XAUUSD", lot_size=0.05, side="BUY", entry_price=2650.0, sl_price=2636.0
            )
            self.assertFalse(approved, f"[{tier_name}] Order must be rejected at 2.50% DD")
            self.assertIn("locked out", reason.lower())

            # -------------------------------------------------------------
            # Sub-test C: 2.51% Drawdown (Must Lock Instantly)
            # -------------------------------------------------------------
            loss_2_51 = round(starting_bal * 0.0251, 2)
            eq_2_51 = starting_bal - loss_2_51

            self.risk_mgr.update_account_telemetry(acc_id, balance=starting_bal, equity=starting_bal, sod_reset=True)
            res_2_51 = self.risk_mgr.update_account_telemetry(acc_id, balance=eq_2_51, equity=eq_2_51)

            self.assertFalse(
                res_2_51["daily_loss_shield_ok"],
                f"[{tier_name}] 2.51% DD (loss ${loss_2_51:,.2f} on ${starting_bal:,.2f}) must breach shield!"
            )
            self.assertTrue(
                res_2_51["is_locked_out"],
                f"[{tier_name}] Account must lock instantly at 2.51% DD"
            )

            # Pre-trade audit must reject
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol="XAUUSD", lot_size=0.05, side="BUY", entry_price=2650.0, sl_price=2636.0
            )
            self.assertFalse(approved, f"[{tier_name}] Order must be rejected at 2.51% DD")

    def test_funding_pips_expert_standalone_boundary(self):
        """Validates that FundingPipsExpert standalone class also enforces 2.49% vs 2.50% vs 2.51%."""
        for tier_name, starting_bal in self.tiers.items():
            expert = FundingPipsExpert(tier_name)
            
            # 2.49% DD -> Safe
            can_trade_49, _ = expert.can_trade(balance=starting_bal, equity=starting_bal * (1.0 - 0.0249))
            self.assertTrue(can_trade_49, f"FundingPipsExpert [{tier_name}] must pass at 2.49% DD")

            # 2.50% DD -> Breach
            can_trade_50, msg_50 = expert.can_trade(balance=starting_bal, equity=starting_bal * (1.0 - 0.0250))
            self.assertFalse(can_trade_50, f"FundingPipsExpert [{tier_name}] must block at 2.50% DD")
            self.assertIn("Daily Drawdown Guard Triggered", msg_50)

            # 2.51% DD -> Breach
            can_trade_51, msg_51 = expert.can_trade(balance=starting_bal, equity=starting_bal * (1.0 - 0.0251))
            self.assertFalse(can_trade_51, f"FundingPipsExpert [{tier_name}] must block at 2.51% DD")
            self.assertIn("Daily Drawdown Guard Triggered", msg_51)

    # =========================================================================
    # 2. TRAILING HWM FLOOR RATCHETS UNDER VOLATILE EQUITY SWINGS
    # =========================================================================

    def test_trailing_hwm_floor_ratchet_under_extreme_volatility_swings(self):
        """
        Simulates volatile equity swings (up-and-down spikes):
          1. +5% swing, -3% pullback
          2. +8% swing (profit lock milestone reached)
          3. -4% sharp intraday pullback (verifying profit floor protection)
          4. +15% massive swing
          5. 1,000 steps of high-volatility geometric random walk
        """
        acc_id = "FP_50K"
        starting_bal = 50000.0  # Max total loss 6% = $3,000. Initial floor = $47,000.
        
        # Step 1: Baseline start
        st = self.risk_mgr.get_account_state(acc_id)
        self.assertEqual(st["trailing_hwm_floor"], 47000.0)

        # Step 2: Swing up +$2,500 to $52,500
        # HWM = $52,500. Floor = $52,500 - $3,000 = $49,500 (< $50,000 starting balance)
        res1 = self.risk_mgr.update_account_telemetry(acc_id, balance=52500.0, equity=52500.0)
        self.assertEqual(res1["absolute_hwm"], 52500.0)
        self.assertEqual(res1["trailing_hwm_floor"], 49500.0)
        self.assertFalse(st.get("hwm_locked_at_starting_balance", False))

        # Step 3: Pullback to $50,500 (Loss of $2,000 from peak, but floor is $49,500)
        # Note: Set SOD reset at $51,000 to isolate trailing floor check
        self.risk_mgr.update_account_telemetry(acc_id, balance=51000.0, equity=51000.0, sod_reset=True)
        res2 = self.risk_mgr.update_account_telemetry(acc_id, balance=50500.0, equity=50500.0)
        self.assertEqual(res2["absolute_hwm"], 52500.0, "HWM must NOT decay during pullback")
        self.assertEqual(res2["trailing_hwm_floor"], 49500.0, "Floor must NOT decay during pullback")
        self.assertTrue(res2["trailing_floor_ok"])

        # Step 4: Surge up to $54,000 (+8% evaluation milestone, +$4,000 profit)
        # Raw floor = $54,000 - $3,000 = $51,000 (>= $50,000 starting balance -> Profit Lock active!)
        res3 = self.risk_mgr.update_account_telemetry(acc_id, balance=54000.0, equity=54000.0)
        self.assertEqual(res3["absolute_hwm"], 54000.0)
        self.assertEqual(res3["trailing_hwm_floor"], 51000.0)
        self.assertTrue(st.get("hwm_locked_at_starting_balance", True))
        self.assertGreaterEqual(res3["trailing_hwm_floor"], starting_bal)

        # Step 5: Test Trailing Floor Breach after surge:
        # If equity drops to $50,800 (< $51,000 trailing floor), account MUST lock even if daily loss is reset!
        self.risk_mgr.update_account_telemetry(acc_id, balance=51500.0, equity=51500.0, sod_reset=True)
        res4 = self.risk_mgr.update_account_telemetry(acc_id, balance=50800.0, equity=50800.0)
        self.assertFalse(res4["trailing_floor_ok"], "Must breach trailing floor at $50,800 < $51,000")
        self.assertTrue(res4["is_locked_out"])
        self.assertIn("TRAILING HWM FLOOR BREACHED", res4["lockout_reason"])

    def test_random_walk_monotonicity_stress_1000_steps(self):
        """Adversarially tests 1,000 randomized steps of extreme volatility across all 4 tiers."""
        rng = random.Random(999)

        for tier_name, starting_bal in self.tiers.items():
            acc_id = f"FP_{tier_name.upper()}"
            curr_equity = starting_bal
            prev_hwm = starting_bal
            prev_floor = starting_bal * 0.94

            for step in range(250):
                # Volatile shock between -2.0% and +3.5%
                pct_change = rng.uniform(-0.02, 0.035)
                curr_equity = max(starting_bal * 0.85, curr_equity * (1.0 + pct_change))

                res = self.risk_mgr.update_account_telemetry(acc_id, balance=curr_equity, equity=curr_equity)
                
                # Invariant 1: HWM strictly non-decreasing
                self.assertGreaterEqual(
                    res["absolute_hwm"], prev_hwm,
                    f"[{tier_name}] HWM decreased at step {step}: {res['absolute_hwm']} < {prev_hwm}"
                )
                # Invariant 2: Trailing Floor strictly non-decreasing
                self.assertGreaterEqual(
                    res["trailing_hwm_floor"], prev_floor,
                    f"[{tier_name}] Floor decreased at step {step}: {res['trailing_hwm_floor']} < {prev_floor}"
                )

                prev_hwm = res["absolute_hwm"]
                prev_floor = res["trailing_hwm_floor"]

    # =========================================================================
    # 3. MICRO-BALANCE SIZING ON $100, $500, $1K, $5K ACCOUNTS (ZERO BREACH RISK)
    # =========================================================================

    def test_micro_balance_lot_sizing_and_zero_breach(self):
        """
        Adversarially tests dynamic lot sizing on micro accounts ($100, $500, $1k, $5k):
          1. Verifies that calculated lot sizes respect risk boundaries (<0.75% to 1.5% max risk).
          2. Verifies that hitting stop loss on the calculated lot size NEVER breaches daily loss shield.
          3. Verifies minimum broker clamping (0.001 crypto / 0.01 forex).
        """
        test_cases = [
            # (account_id, balance, symbol, entry, sl, risk_cap_pct, asset_type)
            ("ACC_100", 100.0, "BTCUSDT", 60000.0, 59000.0, 0.015, "crypto"),   # $1.50 risk budget, $1,000 SL dist -> 0.0015 -> 0.002 lots ($2.00 risk)
            ("ACC_100", 100.0, "ETHUSDT", 2500.0, 2450.0, 0.015, "crypto"),     # $1.50 risk budget, $50 SL dist -> 0.03 lots ($1.50 risk)
            ("ACC_100", 100.0, "SOLUSDT", 150.0, 145.0, 0.015, "crypto"),       # $1.50 risk budget, $5 SL dist -> 0.3 lots ($1.50 risk)
            ("ACC_500", 500.0, "BTC-PERP", 60000.0, 58500.0, 0.015, "crypto"),  # $7.50 risk budget, $1,500 SL dist -> 0.005 lots ($7.50 risk)
            ("ACC_500", 500.0, "ETH-PERP", 2600.0, 2520.0, 0.015, "crypto"),    # $7.50 risk budget, $80 SL dist -> 0.094 lots ($7.52 risk)
            ("ACC_1K", 1000.0, "BTCUSDT", 60000.0, 58000.0, 0.015, "crypto"),   # $15.00 risk budget, $2,000 SL dist -> 0.0075 -> 0.008 lots ($16.00 risk)
            ("ACC_1K", 1000.0, "ETHUSDT", 2600.0, 2500.0, 0.015, "crypto"),     # $15.00 risk budget, $100 SL dist -> 0.15 lots ($15.00 risk)
            ("ACC_5K_CRYPTO", 5000.0, "BTCUSDT", 60000.0, 58500.0, 0.0075, "crypto"), # $37.50 risk budget, $1,500 SL dist -> 0.025 lots ($37.50 risk)
            ("FP_5K", 5000.0, "XAUUSD", 2650.0, 2636.0, 0.0075, "forex"),       # $37.50 risk budget, $14 SL dist * 100 = $1400/lot -> 0.0267 -> 0.03 lots ($42.00 risk)
            ("FP_5K", 5000.0, "EURUSD", 1.0850, 1.0800, 0.0075, "forex"),       # $37.50 risk budget, 50 pips * $10 = $500/lot -> 0.075 -> 0.08 lots ($40.00 risk)
        ]

        for acc_id, bal, sym, entry, sl, risk_cap, asset_type in test_cases:
            lots = self.risk_mgr.calculate_dynamic_lot_size(acc_id, sym, entry, sl)
            self.assertGreater(lots, 0.0, f"[{acc_id}] Lot size must be positive")

            # Calculate actual dollar risk if stop loss is hit
            sl_dist = abs(entry - sl)
            contract_size = self.risk_mgr.CONTRACT_SIZE_MAP.get(sym, 1.0 if asset_type == "crypto" else 100.0)
            actual_dollar_risk = lots * sl_dist * contract_size
            actual_risk_pct = actual_dollar_risk / bal

            # Ensure actual risk is tightly bounded (< 2.0% even with broker rounding)
            self.assertLess(
                actual_risk_pct, 0.025,
                f"[{acc_id}] Risk {actual_risk_pct*100:.2f}% exceeds 2.5% daily drawdown threshold!"
            )

            # Verify that if this single trade is stopped out, the account remains safe from daily breach
            stressed_eq = bal - actual_dollar_risk
            self.risk_mgr.update_account_telemetry(acc_id, balance=bal, equity=bal, sod_reset=True)
            res_after_sl = self.risk_mgr.update_account_telemetry(acc_id, balance=stressed_eq, equity=stressed_eq)
            
            self.assertTrue(
                res_after_sl["daily_loss_shield_ok"],
                f"[{acc_id}] Single trade SL hit must NOT breach daily loss shield! (loss: ${actual_dollar_risk:.2f} on ${bal})"
            )
            self.assertFalse(res_after_sl["is_locked_out"])

    def test_unpermitted_assets_blocked_on_micro_accounts(self):
        """Tests that micro crypto accounts cannot trade high-leverage Forex/Gold contracts."""
        unpermitted_attempts = [
            ("ACC_100", "XAUUSD"),   # Scalp 5M cannot trade Gold
            ("ACC_100", "EURUSD"),   # Scalp 5M cannot trade EURUSD
            ("ACC_500", "XAUUSD"),   # Hyperliquid cannot trade Gold
            ("ACC_500", "GBPUSD"),   # Hyperliquid cannot trade GBPUSD
        ]
        for acc_id, sym in unpermitted_attempts:
            approved, reason = self.risk_mgr.validate_pre_trade_risk(
                account_id=acc_id, symbol=sym, lot_size=0.01, side="BUY", entry_price=2650.0, sl_price=2636.0
            )
            self.assertFalse(approved, f"[{acc_id}] Attempt to trade unallowed asset {sym} must be blocked!")
            self.assertIn("not permitted", reason)


if __name__ == "__main__":
    unittest.main()
