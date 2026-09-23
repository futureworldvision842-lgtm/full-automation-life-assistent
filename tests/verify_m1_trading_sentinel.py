"""
verify_m1_trading_sentinel.py — Comprehensive Programmatic Verification for Milestone M1.
========================================================================================
Verifies:
1. Hard Lot Ceilings & Dollar Risk:
   - Account #40000294403 on XAUUSD never exceeds 0.10L across ATR 0.01 to 200.0.
   - Forex ceiling <= 0.20L.
   - Crypto ceiling <= 0.01L.
   - Dollar risk capped at min(equity * risk_pct, 100.0).
2. Multi-Timeframe (M15 + H1 + H4) Trend Confluence Filter:
   - Blocks trades on M15 vs H1/H4 conflict.
   - Approves trades on full alignment (M15 bull + H1 bull + H4 non-bear; M15 bear + H1 bear + H4 non-bull).
3. Session Kill-Zone Gating:
   - London Kill Zone (07:00-11:30 UTC) -> Approved.
   - NY Kill Zone (12:30-16:30 UTC) -> Approved.
   - Asian session (00:00-07:00 UTC) -> Rejected ("ASIAN_SESSION_LOCKOUT").
   - Rollover & Off-Hours (11:30-12:30, 16:30-24:00 UTC) -> Rejected ("ROLLOVER_OR_OFF_HOURS_LOCKOUT").
4. PortfolioRiskService Account #40000294403 Pre-Registration & Clamping:
   - Balance $100,449.03, max_risk_usd_cap $100.0, max_risk_pct 0.25%, floor $90,000.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
from pathlib import Path
import sys
import unittest
import pandas as pd
import numpy as np

# Setup paths
JARVIS_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = JARVIS_ROOT / "MQ3 TRADING BOT"

if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from src.risk_manager import RiskManager
from src.fleet_risk_manager import FleetRiskManager
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from src.institutional_knowledge import InstitutionalKnowledge
from src.trade_admission import TradeAdmissionGate
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState


class TestMilestoneM1Verification(unittest.TestCase):

    def setUp(self):
        with open(MQ3_ROOT / "config.json", "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.pip_engine = PipdanceFastTrackEngine()
        self.rm = RiskManager(self.cfg)
        self.frm = FleetRiskManager()
        self.confluence = MultiTimeframeConfluenceFilter()
        self.gate = TradeAdmissionGate()
        self.prs = PortfolioRiskService()

    def test_a_lot_size_across_volatility_regimes(self):
        """Programmatic verification: lot size on account #40000294403 never exceeds 0.10L on XAUUSD."""
        atrs = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]
        balance = 100449.03

        for atr in atrs:
            # 1. Pipdance engine
            res = self.pip_engine.calculate_risk(balance=balance, atr=atr, symbol="XAUUSD", entry_price=2500.0)
            self.assertLessEqual(res["lot_size"], 0.10, f"Pipdance Gold lot breach at ATR {atr}: {res['lot_size']}")
            self.assertLessEqual(res["risk_usd"], 100.01, f"Pipdance Risk breach at ATR {atr}: {res['risk_usd']}")

            # 2. RiskManager
            sl_pips = (1.5 * atr) * 10.0
            rm_lot = self.rm.calculate_position_size(balance, sl_pips, "XAUUSD")
            self.assertLessEqual(rm_lot, 0.10, f"RiskManager Gold lot breach at ATR {atr}: {rm_lot}")

            # 3. FleetRiskManager
            frm_lot = self.frm.calculate_position_size(balance, sl_pips, "XAUUSD")
            self.assertLessEqual(frm_lot, 0.10, f"FleetRiskManager Gold lot breach at ATR {atr}: {frm_lot}")

            frm_dyn = self.frm.calculate_dynamic_lot_size(1, "XAUUSD", 2500.0, 2500.0 - (1.5 * atr))
            self.assertLessEqual(frm_dyn, 0.10, f"FleetRiskManager Dynamic Gold lot breach at ATR {atr}: {frm_dyn}")

    def test_b_hard_lot_ceilings_forex_and_crypto(self):
        """Forex is capped at <= 0.20L and Crypto at <= 0.01L."""
        balance = 100449.03

        fx_lots = self.rm.calculate_position_size(balance, 1.0, "EURUSD")
        self.assertLessEqual(fx_lots, 0.20, f"Forex ceiling breached in RM: {fx_lots}")

        fx_frm = self.frm.calculate_position_size(balance, 1.0, "EURUSD")
        self.assertLessEqual(fx_frm, 0.20, f"Forex ceiling breached in FRM: {fx_frm}")

        crypto_lots = self.rm.calculate_position_size(balance, 10.0, "BTCUSD")
        self.assertLessEqual(crypto_lots, 0.01, f"Crypto ceiling breached in RM: {crypto_lots}")

        crypto_frm = self.frm.calculate_position_size(balance, 10.0, "BTCUSD")
        self.assertLessEqual(crypto_frm, 0.01, f"Crypto ceiling breached in FRM: {crypto_frm}")

        # Explicit verification: SOLUSD lot ceiling <= 0.01 across Pipdance engine, RM, and FRM
        sol_pip = self.pip_engine.calculate_risk(balance=balance, atr=0.1, symbol="SOLUSD", entry_price=150.0)
        self.assertLessEqual(sol_pip["lot_size"], 0.01, f"SOLUSD ceiling breached in Pipdance engine: {sol_pip['lot_size']}")

        sol_lots = self.rm.calculate_position_size(balance, 1.0, "SOLUSD")
        self.assertLessEqual(sol_lots, 0.01, f"SOLUSD ceiling breached in RM: {sol_lots}")

        sol_frm = self.frm.calculate_position_size(balance, 1.0, "SOLUSD")
        self.assertLessEqual(sol_frm, 0.01, f"SOLUSD ceiling breached in FRM: {sol_frm}")

        # Check config max_order_lots is 0.20
        self.assertEqual(self.cfg.get("execution", {}).get("max_order_lots"), 0.20)

    def test_c_confluence_filter_vetoes_trend_conflicts(self):
        """Confluence filter strictly blocks trade execution when M15 conflicts with H1/H4."""
        def make_df(base, slope, count=60):
            return pd.DataFrame({"close": [base + i * slope for i in range(count)]})

        df_bull = make_df(2500.0, 1.5)
        df_bear = make_df(2500.0, -1.5)

        # Case 1: M15 Bullish, H1 Bearish, H4 Bullish -> BLOCKED
        ok1, d1, m1 = self.confluence.evaluate_trend_confluence(df_bull, df_bear, df_bull)
        self.assertFalse(ok1)
        self.assertEqual(m1.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Case 2: M15 Bullish, H1 Bullish, H4 Bearish -> BLOCKED
        ok2, d2, m2 = self.confluence.evaluate_trend_confluence(df_bull, df_bull, df_bear)
        self.assertFalse(ok2)
        self.assertEqual(m2.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Case 3: M15 Bearish, H1 Bullish, H4 Bearish -> BLOCKED
        ok3, d3, m3 = self.confluence.evaluate_trend_confluence(df_bear, df_bull, df_bear)
        self.assertFalse(ok3)
        self.assertEqual(m3.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Case 4: M15 Bearish, H1 Bearish, H4 Bullish -> BLOCKED
        ok4, d4, m4 = self.confluence.evaluate_trend_confluence(df_bear, df_bear, df_bull)
        self.assertFalse(ok4)
        self.assertEqual(m4.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Case 5: Full Bullish Confluence -> APPROVED BUY
        ok5, d5, m5 = self.confluence.evaluate_trend_confluence(df_bull, df_bull, df_bull)
        self.assertTrue(ok5)
        self.assertEqual(d5, "BUY")
        self.assertTrue(m5.get("approved"))

        # Case 6: Full Bearish Confluence -> APPROVED SELL
        ok6, d6, m6 = self.confluence.evaluate_trend_confluence(df_bear, df_bear, df_bear)
        self.assertTrue(ok6)
        self.assertEqual(d6, "SELL")
        self.assertTrue(m6.get("approved"))

    def test_d_session_kill_zone_windows(self):
        """Kill-zone filter rejects entries outside London (07:00-11:30 UTC) and NY (12:30-16:30 UTC)."""
        test_vectors = [
            (datetime.datetime(2026, 9, 16, 2, 0, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 6, 59, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 7, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 11, 30, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 16, 30, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 23, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
        ]

        for dt, exp_ok, exp_session in test_vectors:
            ok, session = InstitutionalKnowledge.is_in_kill_zone(dt)
            self.assertEqual(ok, exp_ok, f"InstitutionalKnowledge failed for {dt}: got {ok}, expected {exp_ok}")
            self.assertEqual(session, exp_session, f"Session mismatch for {dt}: got {session}, expected {exp_session}")

            ctx = {
                "data_mode": "LIVE",
                "actionable": True,
                "market_open": True,
                "quote_observed_at": dt.isoformat(),
                "signal_generated_at": dt.isoformat(),
                "current_time_utc": dt.isoformat(),
                "quote_source": "MT5_TEST",
                "spread": 10.0,
                "typical_spread": 10.0,
                "news_clearance": {"verified": True, "is_blackout": False, "is_cleared": True, "age_seconds": 5.0}
            }
            admitted, reasons = self.gate.evaluate(ctx, live=True)
            has_kz_reject = any("outside London" in r for r in reasons)
            if exp_ok:
                self.assertFalse(has_kz_reject, f"Gate rejected {dt} for kill-zones: {reasons}")
            else:
                self.assertTrue(has_kz_reject, f"Gate did not reject {dt} for kill-zones: {reasons}")

    def test_e_portfolio_risk_service_account_40000294403(self):
        """Account #40000294403 pre-registered, $100 dollar cap clamping, 0.25% risk limit."""
        acc = self.prs.get_account("40000294403")
        self.assertIsNotNone(acc, "Account #40000294403 not pre-registered in PortfolioRiskService")
        self.assertEqual(acc.starting_balance, 100449.03)
        self.assertEqual(acc.max_risk_usd_cap, 100.0)
        self.assertEqual(acc.max_risk_pct, 0.25)
        self.assertEqual(acc.max_daily_loss_pct, 5.0)
        self.assertEqual(acc.max_total_loss_pct, 10.0)
        self.assertEqual(acc.trailing_hwm_floor, 90000.0)

        # 0.25% risk -> Approved, dollar risk clamped to <= $100.00
        ok, reason, telem = self.prs.evaluate_trade_admission_risk("40000294403", "XAUUSD", "BUY", 0.25)
        self.assertTrue(ok, f"Trade with 0.25% risk rejected: {reason}")
        self.assertEqual(telem["risk_dollar"], 100.0)
        self.assertLessEqual(telem["risk_dollar"], 100.0)

        # 0.50% risk -> Rejected (exceeds 0.25%)
        ok_fail, reason_fail, _ = self.prs.evaluate_trade_admission_risk("40000294403", "XAUUSD", "BUY", 0.50)
        self.assertFalse(ok_fail)
        self.assertIn("exceeds maximum allowable", reason_fail)

        # Default get_or_register_account call must NOT clobber pre-registered starting equity
        acc_default = self.prs.get_or_register_account("40000294403")
        self.assertEqual(acc_default.current_equity, 100449.03)
        self.assertEqual(acc_default.current_balance, 100449.03)
        self.assertFalse(acc_default.is_locked)

        # Pathological floating point risk_pct (NaN, Inf) must be rejected
        ok_nan, reason_nan, _ = self.prs.evaluate_trade_admission_risk("40000294403", "XAUUSD", "BUY", float("nan"))
        self.assertFalse(ok_nan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
