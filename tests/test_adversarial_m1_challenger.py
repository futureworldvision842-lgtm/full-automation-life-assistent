"""
test_adversarial_m1_challenger.py -- Adversarial Empirical Stress Testing Harness for Milestone M1.
===================================================================================================
Empirical Challenger 1: Rigorous stress testing of:
1. Hard Lot Ceilings across extreme volatility regimes (ATR 0.0001 to 1000.0):
   - Gold (XAUUSD) <= 0.10L
   - Forex (EURUSD, GBPUSD) <= 0.20L
   - Crypto (BTCUSD, ETHUSD, SOLUSD) <= 0.01L
2. Dollar risk cap on Account #40000294403 (<= $100.00) and effective dollar risk.
3. PortfolioRiskService trade admission risk under extreme equity variations, large trade sizes,
   and adversarial/pathological inputs.
4. Trend Confluence Filter and Session Kill Zones under adversarial edge conditions.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
import math
from pathlib import Path
import sys
import unittest
import pandas as pd

JARVIS_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = JARVIS_ROOT / "MQ3 TRADING BOT"

if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from src.risk_manager import RiskManager
from src.fleet_risk_manager import FleetRiskManager
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from src.institutional_knowledge import InstitutionalKnowledge


class TestAdversarialM1Challenger(unittest.TestCase):

    def setUp(self):
        with open(MQ3_ROOT / "config.json", "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.pip_engine = PipdanceFastTrackEngine()
        self.rm = RiskManager(self.cfg)
        self.frm = FleetRiskManager()
        self.prs = PortfolioRiskService()
        self.confluence = MultiTimeframeConfluenceFilter()
        self.account_id = "40000294403"
        self.starting_equity = 100449.03

    # =========================================================================
    # SUITE 1: LOT SIZING ACROSS EXTREME ATR VOLATILITY (0.0001 to 1000.0)
    # =========================================================================

    def test_01_gold_hard_lot_ceiling_pipdance_engine(self):
        """Assert Gold (XAUUSD) calculated lot size NEVER exceeds 0.10L in Pipdance engine."""
        atrs = [0.0001, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 3.5, 10.0, 50.0, 100.0, 500.0, 1000.0]
        for atr in atrs:
            res = self.pip_engine.calculate_risk(
                balance=self.starting_equity,
                atr=atr,
                symbol="XAUUSD",
                entry_price=2500.0,
            )
            self.assertLessEqual(
                res["lot_size"],
                0.10,
                f"Gold lot size {res['lot_size']} exceeds 0.10L hard ceiling at ATR {atr}",
            )

    def test_02_forex_hard_lot_ceiling_pipdance_engine(self):
        """Assert Forex (EURUSD, GBPUSD) calculated lot size NEVER exceeds 0.20L in Pipdance engine."""
        atrs = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 1.0, 10.0, 100.0, 1000.0]
        for sym in ["EURUSD", "GBPUSD"]:
            for atr in atrs:
                res = self.pip_engine.calculate_risk(
                    balance=self.starting_equity,
                    atr=atr,
                    symbol=sym,
                    entry_price=1.0850,
                )
                self.assertLessEqual(
                    res["lot_size"],
                    0.20,
                    f"Forex ({sym}) lot size {res['lot_size']} exceeds 0.20L hard ceiling at ATR {atr}",
                )

    def test_03_crypto_hard_lot_ceiling_pipdance_engine(self):
        """Assert Crypto (BTCUSD, ETHUSD, SOLUSD) calculated lot size NEVER exceeds 0.01L in Pipdance engine."""
        atrs = [0.0001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
        crypto_failures = []
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            for atr in atrs:
                res = self.pip_engine.calculate_risk(
                    balance=self.starting_equity,
                    atr=atr,
                    symbol=sym,
                    entry_price=150.0 if sym == "SOLUSD" else (2500.0 if sym == "ETHUSD" else 65000.0),
                )
                if res["lot_size"] > 0.01:
                    crypto_failures.append((sym, atr, res["lot_size"]))

        self.assertEqual(
            crypto_failures,
            [],
            f"Crypto hard lot ceiling (0.01L) breached in Pipdance engine: {crypto_failures}",
        )

    def test_04_crypto_hard_lot_ceiling_risk_manager(self):
        """Assert Crypto (BTCUSD, ETHUSD, SOLUSD) lot size NEVER exceeds 0.01L in RiskManager."""
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            for sl_pips in [0.0001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]:
                lot = self.rm.calculate_position_size(self.starting_equity, sl_pips, sym)
                self.assertLessEqual(
                    lot,
                    0.01,
                    f"Crypto ({sym}) lot size {lot} exceeds 0.01L in RiskManager at sl_pips {sl_pips}",
                )

    def test_05_crypto_hard_lot_ceiling_fleet_risk_manager(self):
        """Assert Crypto (BTCUSD, ETHUSD, SOLUSD) lot size NEVER exceeds 0.01L in FleetRiskManager."""
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
            for sl_pips in [0.0001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]:
                lot = self.frm.calculate_position_size(self.starting_equity, sl_pips, sym)
                self.assertLessEqual(
                    lot,
                    0.01,
                    f"Crypto ({sym}) lot size {lot} exceeds 0.01L in FleetRiskManager at sl_pips {sl_pips}",
                )

    # =========================================================================
    # SUITE 2: DOLLAR RISK CAPS ON ACCOUNT #40000294403
    # =========================================================================

    def test_06_dollar_risk_cap_reported_risk_usd(self):
        """Assert reported risk_usd NEVER exceeds $100.00 on Account #40000294403 across all ATRs."""
        for sym in ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD", "ETHUSD", "SOLUSD"]:
            for atr in [0.0001, 0.01, 0.1, 1.0, 5.0, 10.0, 100.0, 1000.0]:
                res = self.pip_engine.calculate_risk(
                    balance=self.starting_equity,
                    atr=atr,
                    symbol=sym,
                    entry_price=100.0,
                )
                self.assertLessEqual(
                    res["risk_usd"],
                    100.00,
                    f"Reported risk_usd {res['risk_usd']} breached $100.00 cap on {sym} at ATR {atr}",
                )

    def test_07_effective_dollar_risk_unaffordable_trade_rounding(self):
        """
        Adversarial Test: Check if effective dollar risk (lot_size * sl_dist * contract_multiplier)
        exceeds $100.00 under extreme volatility due to forced broker minimum volume rounding.
        """
        atr = 1000.0
        res = self.pip_engine.calculate_risk(
            balance=self.starting_equity,
            atr=atr,
            symbol="XAUUSD",
            entry_price=2500.0,
        )
        effective_dollar_risk = res["lot_size"] * res["sl_dist"] * 100.0
        self.assertLessEqual(
            effective_dollar_risk,
            100.00,
            f"Effective dollar risk ${effective_dollar_risk:.2f} severely exceeds $100.00 cap on Gold at ATR {atr}",
        )

    # =========================================================================
    # SUITE 3: PORTFOLIO RISK SERVICE EXTREME EQUITY VARIATIONS
    # =========================================================================

    def test_08_portfolio_risk_below_hwm_floor_rejected(self):
        """Equity below trailing HWM floor ($90,000.00) must be REJECTED."""
        for eq in [89999.99, 85000.0, 50000.0, 1000.0, 0.0, -500.0]:
            self.prs._accounts.clear()
            self.prs._initialize_default_fleet_accounts()
            acc = self.prs.get_account(self.account_id)
            acc.current_equity = eq
            ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
            self.assertFalse(
                ok,
                f"Trade was approved when equity {eq} is below trailing HWM floor $90,000.00! Reason: {reason}",
            )

    def test_09_portfolio_risk_daily_drawdown_boundary(self):
        """Daily drawdown limit of 5.0% ($5022.45 loss -> equity <= $95,426.57) must REJECT."""
        # 1. Exactly 1 cent below allowed equity -> REJECT
        self.prs._accounts.clear()
        self.prs._initialize_default_fleet_accounts()
        acc = self.prs.get_account(self.account_id)
        acc.current_equity = 95426.57
        ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
        self.assertFalse(ok, f"Trade at equity $95,426.57 should be rejected for daily drawdown, got: {ok}")

        # 2. Within daily limit -> APPROVE
        self.prs._accounts.clear()
        self.prs._initialize_default_fleet_accounts()
        acc = self.prs.get_account(self.account_id)
        acc.current_equity = 95426.59
        ok, reason, telem = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
        self.assertTrue(ok, f"Trade at equity $95,426.59 should be admitted, got: {reason}")
        self.assertLessEqual(telem["risk_dollar"], 100.0)

    def test_10_portfolio_risk_extreme_high_equity(self):
        """Under extreme high equity ($10M), risk_dollar must remain strictly clamped to <= $100.00."""
        self.prs._accounts.clear()
        self.prs._initialize_default_fleet_accounts()
        acc = self.prs.get_account(self.account_id)
        acc.current_equity = 10000000.0
        acc.high_water_mark = 10000000.0
        acc.daily_start_equity = 10000000.0
        acc.starting_balance = 10000000.0
        acc.daily_loss_dollar_cap = 500000.0
        acc.trailing_hwm_floor = 9000000.0

        ok, reason, telem = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
        self.assertTrue(ok, f"Extreme high equity trade rejected: {reason}")
        self.assertLessEqual(
            telem["risk_dollar"],
            100.0,
            f"Risk dollar {telem['risk_dollar']} exceeded $100.00 cap under $10M equity!",
        )

    # =========================================================================
    # SUITE 4: ADVERSARIAL TRADE SIZES & INPUTS TO PORTFOLIO RISK SERVICE
    # =========================================================================

    def test_11_portfolio_risk_excessive_risk_pct_rejected(self):
        """Risk percentage > 0.25% must be REJECTED on Account #40000294403."""
        for rp in [0.26, 0.50, 0.75, 1.0, 5.0, 50.0, 100.0]:
            self.prs._accounts.clear()
            self.prs._initialize_default_fleet_accounts()
            ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", rp)
            self.assertFalse(ok, f"Excessive risk_pct {rp}% was admitted: {reason}")

    def test_12_portfolio_risk_non_positive_risk_pct_rejected(self):
        """Risk percentage <= 0.0% must be REJECTED."""
        for rp in [0.0, -0.01, -0.25, -1.0]:
            self.prs._accounts.clear()
            self.prs._initialize_default_fleet_accounts()
            ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", rp)
            self.assertFalse(ok, f"Non-positive risk_pct {rp}% was admitted: {reason}")

    def test_13_portfolio_risk_nan_and_inf_risk_pct(self):
        """Adversarial floating-point inputs (NaN, Inf) must be REJECTED."""
        for bad_rp in [float("nan"), float("inf"), float("-inf")]:
            self.prs._accounts.clear()
            self.prs._initialize_default_fleet_accounts()
            ok, reason, telem = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", bad_rp)
            self.assertFalse(
                ok,
                f"Pathological risk_pct {bad_rp} was admitted! Telemetry: {telem}",
            )

    def test_14_portfolio_risk_max_open_trades_barrier(self):
        """Account cannot admit more than max_open_trades (3)."""
        self.prs._accounts.clear()
        self.prs._initialize_default_fleet_accounts()
        acc = self.prs.get_account(self.account_id)
        acc.open_positions_count = 3

        ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
        self.assertFalse(ok, f"4th trade admitted despite open_positions_count=3: {reason}")

    def test_15_portfolio_risk_currency_cluster_barrier(self):
        """Portfolio currency cluster cannot exceed max_currency_cluster (3)."""
        self.prs._accounts.clear()
        self.prs._initialize_default_fleet_accounts()
        # Add 3 positions involving USD across other accounts
        ftmo = self.prs.get_account("1514382598")
        ftmo.open_symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        ok, reason, _ = self.prs.evaluate_trade_admission_risk(self.account_id, "XAUUSD", "BUY", 0.25)
        self.assertFalse(ok, f"Trade admitted when USD currency cluster count is already 3: {reason}")

    # =========================================================================
    # SUITE 5: MTF CONFLUENCE & SESSION KILL ZONE ADVERSARIAL EDGES
    # =========================================================================

    def test_16_confluence_adversarial_candle_inputs(self):
        """Trend confluence must reject corrupt, empty, or degenerate candle inputs."""
        empty_df = pd.DataFrame()
        short_df = pd.DataFrame({"close": [2500.0] * 5})
        flat_df = pd.DataFrame({"close": [2500.0] * 30})
        normal_df = pd.DataFrame({"close": [2500.0 + i for i in range(30)]})

        # Empty DF
        ok, d, m = self.confluence.evaluate_trend_confluence(empty_df, normal_df, normal_df)
        self.assertFalse(ok)
        self.assertIn("Insufficient", m.get("reason", ""))

        # Short DF
        ok2, d2, m2 = self.confluence.evaluate_trend_confluence(short_df, normal_df, normal_df)
        self.assertFalse(ok2)
        self.assertIn("Insufficient", m2.get("reason", ""))

        # Flat prices (neutral)
        ok3, d3, m3 = self.confluence.evaluate_trend_confluence(flat_df, normal_df, normal_df)
        self.assertFalse(ok3)
        self.assertIn("neutral", m3.get("reason", ""))

    def test_17_session_kill_zone_exact_microsecond_boundaries(self):
        """Verify kill zone boundaries at exact edge boundaries."""
        # 11:30:00 UTC -> in London
        t1 = datetime.datetime(2026, 9, 16, 11, 30, 0, tzinfo=timezone.utc)
        ok1, sess1 = InstitutionalKnowledge.is_in_kill_zone(t1)
        self.assertTrue(ok1)
        self.assertEqual(sess1, "LONDON_KILL_ZONE")

        # 11:30:01 UTC -> Rollover/Off-hours lockout
        t2 = datetime.datetime(2026, 9, 16, 11, 30, 1, tzinfo=timezone.utc)
        ok2, sess2 = InstitutionalKnowledge.is_in_kill_zone(t2)
        self.assertFalse(ok2)
        self.assertEqual(sess2, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")

        # 12:30:00 UTC -> in NY
        t3 = datetime.datetime(2026, 9, 16, 12, 30, 0, tzinfo=timezone.utc)
        ok3, sess3 = InstitutionalKnowledge.is_in_kill_zone(t3)
        self.assertTrue(ok3)
        self.assertEqual(sess3, "NY_KILL_ZONE")

        # 16:30:00 UTC -> in NY
        t4 = datetime.datetime(2026, 9, 16, 16, 30, 0, tzinfo=timezone.utc)
        ok4, sess4 = InstitutionalKnowledge.is_in_kill_zone(t4)
        self.assertTrue(ok4)
        self.assertEqual(sess4, "NY_KILL_ZONE")

        # 16:30:01 UTC -> Rollover/Off-hours lockout
        t5 = datetime.datetime(2026, 9, 16, 16, 30, 1, tzinfo=timezone.utc)
        ok5, sess5 = InstitutionalKnowledge.is_in_kill_zone(t5)
        self.assertFalse(ok5)
        self.assertEqual(sess5, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
