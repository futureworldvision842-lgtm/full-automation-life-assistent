"""
adversarial_challenge_m1.py — Empirical Adversarial Stress Test Suite for Milestone M1.
========================================================================================
Adversarially tests:
1. Multi-Timeframe Trend Confluence Filter:
   - Exhaustive verification of all 27 permutations of (M15, H1, H4) in {Bullish, Bearish, Neutral}.
   - Strict blocking of BUY whenever H1 is not bullish or H4 is bearish.
   - Strict blocking of SELL whenever H1 is not bearish or H4 is bullish.
   - Candle shortages (< 25 bars) across M15, H1, H4, empty/None DataFrames, and corrupt data.
2. Session Kill-Zone Gating:
   - Microsecond boundary conditions around kill-zone open and close:
     * 06:59:59 UTC -> REJECT (Asian lockout)
     * 07:00:00 UTC -> APPROVE (London open)
     * 11:30:00 UTC -> APPROVE (London close)
     * 11:30:01 UTC -> REJECT (Midday gap lockout)
     * 12:29:59 UTC -> REJECT (Midday gap lockout)
     * 12:30:00 UTC -> APPROVE (NY open)
     * 16:30:00 UTC -> APPROVE (NY close)
     * 16:30:01 UTC -> REJECT (Rollover / off-hours lockout)
     * 23:59:59 UTC -> REJECT (Asian / rollover lockout)
   - Microsecond precision edge cases.
   - Rejection in TradeAdmissionGate (standard and comprehensive).
   - Rejection and execution gating in AutonomousLiveDaemon.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from src.institutional_knowledge import InstitutionalKnowledge
from src.trade_admission import TradeAdmissionGate
from src.autonomous_live_daemon import AutonomousLiveDaemon


class TestMultiTimeframeTrendConfluenceAdversarial(unittest.TestCase):
    """Exhaustive stress tests for MultiTimeframeConfluenceFilter."""

    def setUp(self):
        self.confluence = MultiTimeframeConfluenceFilter()

        # Synthetic price generators (length 60 bars)
        # Bullish: rising price, close > ema20 > ema50
        self.df_bull = pd.DataFrame({"close": [100.0 + i * 2.0 for i in range(60)]})
        # Bearish: falling price, close < ema20 < ema50
        self.df_bear = pd.DataFrame({"close": [300.0 - i * 2.0 for i in range(60)]})
        # Neutral: flat price, close == ema20 == ema50
        self.df_neut = pd.DataFrame({"close": [100.0 for _ in range(60)]})

        self.series_map = {
            "BULL": self.df_bull,
            "BEAR": self.df_bear,
            "NEUT": self.df_neut,
        }

    def test_all_27_permutations_exhaustive(self):
        """
        Adversarially tests every one of the 3^3 = 27 permutations of (M15, H1, H4).
        Asserts exact gating behavior under direction_hint=None, 'BUY', and 'SELL'.
        """
        states = ["BULL", "BEAR", "NEUT"]
        tested_count = 0

        for m15 in states:
            for h1 in states:
                for h4 in states:
                    tested_count += 1
                    df_m15 = self.series_map[m15]
                    df_h1 = self.series_map[h1]
                    df_h4 = self.series_map[h4]

                    # 1. Test BUY direction hint
                    ok_buy, dir_buy, meta_buy = self.confluence.evaluate_trend_confluence(
                        df_m15, df_h1, df_h4, direction_hint="BUY"
                    )

                    # Strict BUY Rule:
                    # M15 must be BULL, H1 must be BULL, H4 must NOT be BEAR (i.e. BULL or NEUT)
                    expected_buy = (m15 == "BULL") and (h1 == "BULL") and (h4 != "BEAR")
                    self.assertEqual(
                        ok_buy,
                        expected_buy,
                        f"BUY assertion failed for ({m15}, {h1}, {h4}): got {ok_buy}, expected {expected_buy}",
                    )
                    if expected_buy:
                        self.assertEqual(dir_buy, "BUY")
                        self.assertTrue(meta_buy.get("approved"))
                    else:
                        self.assertIsNone(dir_buy)
                        self.assertFalse(meta_buy.get("approved"))
                        self.assertIn("reason", meta_buy)

                    # 2. Test SELL direction hint
                    ok_sell, dir_sell, meta_sell = self.confluence.evaluate_trend_confluence(
                        df_m15, df_h1, df_h4, direction_hint="SELL"
                    )

                    # Strict SELL Rule:
                    # M15 must be BEAR, H1 must be BEAR, H4 must NOT be BULL (i.e. BEAR or NEUT)
                    expected_sell = (m15 == "BEAR") and (h1 == "BEAR") and (h4 != "BULL")
                    self.assertEqual(
                        ok_sell,
                        expected_sell,
                        f"SELL assertion failed for ({m15}, {h1}, {h4}): got {ok_sell}, expected {expected_sell}",
                    )
                    if expected_sell:
                        self.assertEqual(dir_sell, "SELL")
                        self.assertTrue(meta_sell.get("approved"))
                    else:
                        self.assertIsNone(dir_sell)
                        self.assertFalse(meta_sell.get("approved"))
                        self.assertIn("reason", meta_sell)

                    # 3. Test direction_hint=None (trigger inferred from M15)
                    ok_none, dir_none, meta_none = self.confluence.evaluate_trend_confluence(
                        df_m15, df_h1, df_h4, direction_hint=None
                    )
                    if m15 == "BULL":
                        self.assertEqual(ok_none, expected_buy)
                        self.assertEqual(dir_none, "BUY" if expected_buy else None)
                    elif m15 == "BEAR":
                        self.assertEqual(ok_none, expected_sell)
                        self.assertEqual(dir_none, "SELL" if expected_sell else None)
                    else:  # m15 == "NEUT"
                        self.assertFalse(ok_none)
                        self.assertIsNone(dir_none)

        self.assertEqual(tested_count, 27, f"Expected 27 permutations, evaluated {tested_count}")

    def test_buy_strictly_blocked_whenever_h1_not_bullish_or_h4_is_bearish(self):
        """
        Specialized verification: BUY execution is strictly blocked whenever:
        - H1 is not bullish (H1 in ['BEAR', 'NEUT'])
        - H4 is bearish (H4 == 'BEAR')
        """
        states = ["BULL", "BEAR", "NEUT"]
        for h1 in ["BEAR", "NEUT"]:
            for h4 in states:
                ok, d, meta = self.confluence.evaluate_trend_confluence(
                    self.df_bull, self.series_map[h1], self.series_map[h4], direction_hint="BUY"
                )
                self.assertFalse(ok, f"BUY should be blocked when H1={h1}, H4={h4}")
                self.assertEqual(meta.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Even if H1 is BULL, if H4 is BEAR -> strictly blocked
        ok, d, meta = self.confluence.evaluate_trend_confluence(
            self.df_bull, self.df_bull, self.df_bear, direction_hint="BUY"
        )
        self.assertFalse(ok, "BUY should be blocked when H4 is BEAR")
        self.assertEqual(meta.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

    def test_sell_strictly_blocked_whenever_h1_not_bearish_or_h4_is_bullish(self):
        """
        Specialized verification: SELL execution is strictly blocked whenever:
        - H1 is not bearish (H1 in ['BULL', 'NEUT'])
        - H4 is bullish (H4 == 'BULL')
        """
        states = ["BULL", "BEAR", "NEUT"]
        for h1 in ["BULL", "NEUT"]:
            for h4 in states:
                ok, d, meta = self.confluence.evaluate_trend_confluence(
                    self.df_bear, self.series_map[h1], self.series_map[h4], direction_hint="SELL"
                )
                self.assertFalse(ok, f"SELL should be blocked when H1={h1}, H4={h4}")
                self.assertEqual(meta.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

        # Even if H1 is BEAR, if H4 is BULL -> strictly blocked
        ok, d, meta = self.confluence.evaluate_trend_confluence(
            self.df_bear, self.df_bear, self.df_bull, direction_hint="SELL"
        )
        self.assertFalse(ok, "SELL should be blocked when H4 is BULL")
        self.assertEqual(meta.get("reason"), "MTF trend conflict: M15 conflicts with H1/H4")

    def test_candle_shortages_and_corrupt_data(self):
        """
        Verifies behavior with candle shortages (< 25 bars), empty dataframes,
        None values, missing columns, and NaN values.
        """
        # 1. Bar counts < 20 in M15 must reject
        for count in [0, 1, 5, 10, 19]:
            df_short = self.df_bull.iloc[:count]
            ok, d, meta = self.confluence.evaluate_trend_confluence(df_short, self.df_bull, self.df_bull)
            self.assertFalse(ok)
            self.assertEqual(meta.get("reason"), "Insufficient M15 candle data for confluence evaluation")

        # 2. Bar counts < 20 in H1 must reject
        for count in [0, 5, 15, 19]:
            df_short = self.df_bull.iloc[:count]
            ok, d, meta = self.confluence.evaluate_trend_confluence(self.df_bull, df_short, self.df_bull)
            self.assertFalse(ok)
            self.assertEqual(meta.get("reason"), "Insufficient H1 candle data for confluence evaluation")

        # 3. Bar counts < 20 in H4 must reject
        for count in [0, 5, 15, 19]:
            df_short = self.df_bull.iloc[:count]
            ok, d, meta = self.confluence.evaluate_trend_confluence(self.df_bull, self.df_bull, df_short)
            self.assertFalse(ok)
            self.assertEqual(meta.get("reason"), "Insufficient H4 candle data for confluence evaluation")

        # 4. None inputs
        ok_none, _, m_none = self.confluence.evaluate_trend_confluence(None, self.df_bull, self.df_bull)
        self.assertFalse(ok_none)
        self.assertEqual(m_none.get("reason"), "Insufficient M15 candle data for confluence evaluation")

        ok_h1_none, _, m_h1_none = self.confluence.evaluate_trend_confluence(self.df_bull, None, self.df_bull)
        self.assertFalse(ok_h1_none)
        self.assertEqual(m_h1_none.get("reason"), "Insufficient H1 candle data for confluence evaluation")

        # 5. Missing 'close' column
        df_no_close = pd.DataFrame({"price": [100.0] * 30})
        ok_col, _, m_col = self.confluence.evaluate_trend_confluence(df_no_close, self.df_bull, self.df_bull)
        self.assertFalse(ok_col)
        self.assertEqual(m_col.get("reason"), "Insufficient M15 candle data for confluence evaluation")

        # 6. NaN in price series -> fails closed (treated as neutral)
        df_nan = pd.DataFrame({"close": [100.0 + i for i in range(59)] + [np.nan]})
        ok_nan, _, m_nan = self.confluence.evaluate_trend_confluence(df_nan, self.df_bull, self.df_bull)
        self.assertFalse(ok_nan)


class TestSessionKillZoneGatingAdversarial(unittest.TestCase):
    """Adversarial boundary stress tests for Session Kill-Zone Gating."""

    def setUp(self):
        self.gate = TradeAdmissionGate()

    def test_nine_exact_boundary_conditions(self):
        """
        Directly tests the 9 specific boundary conditions required by user prompt:
        - 06:59:59 UTC -> REJECT (Asian lockout)
        - 07:00:00 UTC -> APPROVE (London open)
        - 11:30:00 UTC -> APPROVE (London close)
        - 11:30:01 UTC -> REJECT (Off-hours / midday gap)
        - 12:29:59 UTC -> REJECT (Off-hours / midday gap)
        - 12:30:00 UTC -> APPROVE (NY open)
        - 16:30:00 UTC -> APPROVE (NY close)
        - 16:30:01 UTC -> REJECT (Rollover / off-hours)
        - 23:59:59 UTC -> REJECT (Asian / rollover)
        """
        boundary_matrix = [
            ("06:59:59 UTC", datetime.datetime(2026, 9, 16, 6, 59, 59, 0, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
            ("07:00:00 UTC", datetime.datetime(2026, 9, 16, 7, 0, 0, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            ("11:30:00 UTC", datetime.datetime(2026, 9, 16, 11, 30, 0, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            ("11:30:01 UTC", datetime.datetime(2026, 9, 16, 11, 30, 1, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            ("12:29:59 UTC", datetime.datetime(2026, 9, 16, 12, 29, 59, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            ("12:30:00 UTC", datetime.datetime(2026, 9, 16, 12, 30, 0, 0, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            ("16:30:00 UTC", datetime.datetime(2026, 9, 16, 16, 30, 0, 0, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            ("16:30:01 UTC", datetime.datetime(2026, 9, 16, 16, 30, 1, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            ("23:59:59 UTC", datetime.datetime(2026, 9, 16, 23, 59, 59, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
        ]

        for label, dt, exp_admit, exp_session in boundary_matrix:
            # 1. Test InstitutionalKnowledge
            ok, session = InstitutionalKnowledge.is_in_kill_zone(dt)
            self.assertEqual(ok, exp_admit, f"IK failed for {label}: got {ok}, expected {exp_admit}")
            self.assertEqual(session, exp_session, f"IK session mismatch for {label}: got {session}, expected {exp_session}")

            # 2. Test TradeAdmissionGate.evaluate(live=True)
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
                "news_clearance": {"verified": True, "is_blackout": False, "is_cleared": True, "age_seconds": 5.0},
            }
            admitted, reasons = self.gate.evaluate(ctx, live=True)
            has_kz_reject = any("outside London" in r for r in reasons)
            if exp_admit:
                self.assertTrue(admitted, f"Gate failed to admit {label}: {reasons}")
                self.assertFalse(has_kz_reject, f"Gate rejected {label} for kill-zone: {reasons}")
            else:
                self.assertFalse(admitted, f"Gate admitted outside kill-zone at {label}")
                self.assertTrue(has_kz_reject, f"Gate missing kill-zone rejection reason for {label}: {reasons}")

    def test_microsecond_resolution_behavior(self):
        """
        Microsecond boundary inspection:
        Evaluates sub-second behavior right before and after boundaries.
        Documents the exact second-level discretization characteristics of InstitutionalKnowledge.
        """
        # Pre-open microsecond edges (e.g. 06:59:59.999999 -> ASIAN_SESSION_LOCKOUT)
        ok_pre, sess_pre = InstitutionalKnowledge.is_in_kill_zone(
            datetime.datetime(2026, 9, 16, 6, 59, 59, 999999, tzinfo=timezone.utc)
        )
        self.assertFalse(ok_pre)
        self.assertEqual(sess_pre, "ASIAN_SESSION_LOCKOUT")

        # Pre-NY microsecond edges (e.g. 12:29:59.999999 -> ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        ok_pre_ny, sess_pre_ny = InstitutionalKnowledge.is_in_kill_zone(
            datetime.datetime(2026, 9, 16, 12, 29, 59, 999999, tzinfo=timezone.utc)
        )
        self.assertFalse(ok_pre_ny)
        self.assertEqual(sess_pre_ny, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")

        # Midnight rollover microsecond edge
        ok_late, sess_late = InstitutionalKnowledge.is_in_kill_zone(
            datetime.datetime(2026, 9, 16, 23, 59, 59, 999999, tzinfo=timezone.utc)
        )
        self.assertFalse(ok_late)
        self.assertEqual(sess_late, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")

    def test_autonomous_live_daemon_kill_zone_and_shortage_gating(self):
        """
        Verifies that AutonomousLiveDaemon:
        1. Fully halts market scanning outside institutional kill zones.
        2. Bypasses execution when candle count < 25 bars.
        """
        daemon = AutonomousLiveDaemon(simulation_mode=True)
        daemon.mt5 = MagicMock()
        daemon.mt5.get_open_positions.return_value = []
        daemon.mt5.get_account_info.return_value = {"login": 40000294403, "equity": 100449.03}
        daemon.mt5.get_symbol_tick.return_value = {"bid": 2500.0, "ask": 2500.5}

        # Test 1: Outside kill zones -> scan_markets_and_act immediately aborts (0 calls to mt5.get_open_positions)
        lockout_times = [
            datetime.datetime(2026, 9, 16, 6, 59, 59, tzinfo=timezone.utc),
            datetime.datetime(2026, 9, 16, 11, 30, 1, tzinfo=timezone.utc),
            datetime.datetime(2026, 9, 16, 12, 29, 59, tzinfo=timezone.utc),
            datetime.datetime(2026, 9, 16, 16, 30, 1, tzinfo=timezone.utc),
            datetime.datetime(2026, 9, 16, 23, 59, 59, tzinfo=timezone.utc),
        ]

        for lockout_dt in lockout_times:
            with patch("src.autonomous_live_daemon.datetime") as mock_dt:
                mock_dt.datetime.now.return_value = lockout_dt
                mock_dt.timezone = timezone
                daemon.mt5.get_open_positions.reset_mock()
                actions = daemon.scan_markets_and_act()
                self.assertEqual(actions, [])
                self.assertFalse(daemon.mt5.get_open_positions.called)

        # Test 2: Inside London kill zone -> passes session filter
        london_dt = datetime.datetime(2026, 9, 16, 9, 0, 0, tzinfo=timezone.utc)
        with patch("src.autonomous_live_daemon.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = london_dt
            mock_dt.timezone = timezone

            # Shortage Case A: 24 bars (< 25) -> skipped, 0 trades executed
            daemon.mt5.get_historical_candles.return_value = pd.DataFrame(
                {"close": [2500.0 + i for i in range(24)], "high": [2501.0 + i for i in range(24)], "low": [2499.0 + i for i in range(24)]}
            )
            actions_24 = daemon.scan_markets_and_act()
            self.assertEqual(actions_24, [])

            # Shortage Case B: None candles -> skipped, 0 trades executed
            daemon.mt5.get_historical_candles.return_value = None
            actions_none = daemon.scan_markets_and_act()
            self.assertEqual(actions_none, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
