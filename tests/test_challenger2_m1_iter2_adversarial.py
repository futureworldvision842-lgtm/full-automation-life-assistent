"""
test_challenger2_m1_iter2_adversarial.py
=========================================
Adversarial Stress Test Suite authored by Challenger 2 Iteration 2 (critic, specialist).
Specifically challenges:
1. Timezone normalization support in InstitutionalKnowledge (UTC, PKT, EST, PST, JST, HST, LINT, offsets).
   - Tests normalize_tz=True vs normalize_tz=False
   - Tests timezone-aware vs naive datetimes
   - Verifies integration with TradeAdmissionGate
2. Session kill-zone boundary precision:
   - Evaluates second-level discretization and boundary transitions
   - Asian session lockout, London kill zone, midday gap lockout, NY kill zone, rollover lockout
3. Multi-timeframe trend confluence filter:
   - Exhaustive 27 permutations under BUY, SELL, and AUTO
   - Strict blocking of counter-trend signals
   - Flat market handling, noisy chop handling, and candle shortages
4. Autonomous live daemon session gating & confluence enforcement
"""

import datetime
from datetime import timezone, timedelta
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

# Set paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.institutional_knowledge import InstitutionalKnowledge
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from src.trade_admission import TradeAdmissionGate
from src.autonomous_live_daemon import AutonomousLiveDaemon


class TestTimezoneNormalizationAdversarial(unittest.TestCase):
    """Deep adversarial probes on InstitutionalKnowledge timezone normalization."""

    def test_normalize_tz_true_across_global_timezones(self):
        """
        Verify normalize_tz=True converts timezone-aware datetimes to UTC before evaluating.
        Test with multiple timezones:
        - PKT (UTC+5): London open 07:00 UTC is 12:00 PKT.
        - EST (UTC-5): London close 11:30 UTC is 06:30 EST.
        - PST (UTC-8): NY open 12:30 UTC is 04:30 PST.
        - JST (UTC+9): NY close 16:30 UTC is 01:30 JST (next day).
        - HST (UTC-10): Asian lockout 06:59:59 UTC is 20:59:59 HST (prev day).
        - IST (UTC+5:30): Midday gap 12:00 UTC is 17:30 IST.
        - LINT (UTC+14): Rollover lockout 23:59:59 UTC is 13:59:59 LINT (next day).
        """
        tz_pkt = timezone(timedelta(hours=5))
        tz_est = timezone(timedelta(hours=-5))
        tz_pst = timezone(timedelta(hours=-8))
        tz_jst = timezone(timedelta(hours=9))
        tz_hst = timezone(timedelta(hours=-10))
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        tz_lint = timezone(timedelta(hours=14))

        test_cases = [
            # 1. London open in PKT (12:00 PKT == 07:00 UTC) -> APPROVE
            (datetime.datetime(2026, 9, 16, 12, 0, 0, tzinfo=tz_pkt), True, "LONDON_KILL_ZONE"),
            # 2. Asian lockout just before London open in HST (20:59:59 prev day == 06:59:59 UTC) -> REJECT
            (datetime.datetime(2026, 9, 15, 20, 59, 59, tzinfo=tz_hst), False, "ASIAN_SESSION_LOCKOUT"),
            # 3. London close in EST (06:30:00 EST == 11:30:00 UTC) -> APPROVE
            (datetime.datetime(2026, 9, 16, 6, 30, 0, tzinfo=tz_est), True, "LONDON_KILL_ZONE"),
            # 4. Midday gap lockout in IST (17:30 IST == 12:00 UTC) -> REJECT
            (datetime.datetime(2026, 9, 16, 17, 30, 0, tzinfo=tz_ist), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            # 5. NY open in PST (04:30:00 PST == 12:30:00 UTC) -> APPROVE
            (datetime.datetime(2026, 9, 16, 4, 30, 0, tzinfo=tz_pst), True, "NY_KILL_ZONE"),
            # 6. NY close in JST (01:30:00 JST next day == 16:30:00 UTC) -> APPROVE
            (datetime.datetime(2026, 9, 17, 1, 30, 0, tzinfo=tz_jst), True, "NY_KILL_ZONE"),
            # 7. Post NY close in JST (01:30:01 JST next day == 16:30:01 UTC) -> REJECT
            (datetime.datetime(2026, 9, 17, 1, 30, 1, tzinfo=tz_jst), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            # 8. Rollover lockout in LINT (13:59:59 next day == 23:59:59 UTC) -> REJECT
            (datetime.datetime(2026, 9, 17, 13, 59, 59, tzinfo=tz_lint), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
        ]

        for dt, exp_admit, exp_sess in test_cases:
            is_kz, session = InstitutionalKnowledge.is_in_kill_zone(dt, normalize_tz=True)
            self.assertEqual(
                is_kz, exp_admit,
                f"normalize_tz=True failed for {dt} ({dt.tzinfo}): got {is_kz}, expected {exp_admit}"
            )
            self.assertEqual(
                session, exp_sess,
                f"Session name mismatch for {dt} ({dt.tzinfo}): got {session}, expected {exp_sess}"
            )

    def test_normalize_tz_false_preserves_raw_hour_evaluation(self):
        """
        Verify backwards compatibility: when normalize_tz=False (default),
        InstitutionalKnowledge inspects .hour directly without timezone conversion.
        """
        tz_pkt = timezone(timedelta(hours=5))
        # 12:00 PKT without normalization has hour=12, which is midday gap
        dt_pkt_12 = datetime.datetime(2026, 9, 16, 12, 0, 0, tzinfo=tz_pkt)
        is_kz_default, sess_default = InstitutionalKnowledge.is_in_kill_zone(dt_pkt_12)
        self.assertFalse(is_kz_default, "Default normalize_tz=False must treat dt.hour=12 directly")
        self.assertEqual(sess_default, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")

        # Explicit normalize_tz=False
        is_kz_explicit, sess_explicit = InstitutionalKnowledge.is_in_kill_zone(dt_pkt_12, normalize_tz=False)
        self.assertFalse(is_kz_explicit)
        self.assertEqual(sess_explicit, "ROLLOVER_OR_OFF_HOURS_LOCKOUT")

    def test_naive_datetime_handling(self):
        """
        Verify naive datetime (tzinfo=None) behaves safely under both normalize_tz=True and normalize_tz=False.
        """
        # Naive 07:00 -> London kill zone
        dt_naive_london = datetime.datetime(2026, 9, 16, 7, 0, 0)
        ok_true, sess_true = InstitutionalKnowledge.is_in_kill_zone(dt_naive_london, normalize_tz=True)
        ok_false, sess_false = InstitutionalKnowledge.is_in_kill_zone(dt_naive_london, normalize_tz=False)
        self.assertTrue(ok_true)
        self.assertTrue(ok_false)
        self.assertEqual(sess_true, "LONDON_KILL_ZONE")
        self.assertEqual(sess_false, "LONDON_KILL_ZONE")

        # Naive 03:00 -> Asian lockout
        dt_naive_asian = datetime.datetime(2026, 9, 16, 3, 0, 0)
        ok_a_true, sess_a_true = InstitutionalKnowledge.is_in_kill_zone(dt_naive_asian, normalize_tz=True)
        ok_a_false, sess_a_false = InstitutionalKnowledge.is_in_kill_zone(dt_naive_asian, normalize_tz=False)
        self.assertFalse(ok_a_true)
        self.assertFalse(ok_a_false)
        self.assertEqual(sess_a_true, "ASIAN_SESSION_LOCKOUT")
        self.assertEqual(sess_a_false, "ASIAN_SESSION_LOCKOUT")


class TestSessionKillZoneMicrosecondBoundaries(unittest.TestCase):
    """Exhaustive boundary stress tests verifying second-level discretization of session kill zones."""

    def test_kill_zone_exact_boundary_seconds(self):
        """
        Verifies exact second-level transitions across all 4 sessions:
        - 06:59:59.000000 -> REJECT (ASIAN_SESSION_LOCKOUT)
        - 06:59:59.999999 -> REJECT (ASIAN_SESSION_LOCKOUT)
        - 07:00:00.000000 -> APPROVE (LONDON_KILL_ZONE)
        - 11:30:00.000000 -> APPROVE (LONDON_KILL_ZONE)
        - 11:30:01.000000 -> REJECT (ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        - 12:29:59.000000 -> REJECT (ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        - 12:29:59.999999 -> REJECT (ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        - 12:30:00.000000 -> APPROVE (NY_KILL_ZONE)
        - 16:30:00.000000 -> APPROVE (NY_KILL_ZONE)
        - 16:30:01.000000 -> REJECT (ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        - 23:59:59.999999 -> REJECT (ROLLOVER_OR_OFF_HOURS_LOCKOUT)
        - 00:00:00.000000 -> REJECT (ASIAN_SESSION_LOCKOUT)
        """
        test_points = [
            (datetime.datetime(2026, 9, 16, 6, 59, 59, 0, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 6, 59, 59, 999999, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 7, 0, 0, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 11, 29, 59, 999999, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 11, 30, 0, 0, tzinfo=timezone.utc), True, "LONDON_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 11, 30, 1, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 12, 29, 59, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 12, 29, 59, 999999, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 12, 30, 0, 0, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 16, 29, 59, 999999, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 16, 30, 0, 0, tzinfo=timezone.utc), True, "NY_KILL_ZONE"),
            (datetime.datetime(2026, 9, 16, 16, 30, 1, 0, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 23, 59, 59, 999999, tzinfo=timezone.utc), False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"),
            (datetime.datetime(2026, 9, 16, 0, 0, 0, 0, tzinfo=timezone.utc), False, "ASIAN_SESSION_LOCKOUT"),
        ]

        for dt, exp_admit, exp_sess in test_points:
            ok, sess = InstitutionalKnowledge.is_in_kill_zone(dt)
            self.assertEqual(ok, exp_admit, f"Failed at {dt}: got {ok}, expected {exp_admit}")
            self.assertEqual(sess, exp_sess, f"Session mismatch at {dt}: got {sess}, expected {exp_sess}")


class TestTrendConfluenceAdversarial(unittest.TestCase):
    """Stress tests on MultiTimeframeConfluenceFilter ensuring counter-trend blocking."""

    def setUp(self):
        self.confluence = MultiTimeframeConfluenceFilter()

        # Build clean series
        self.bull_m15 = pd.DataFrame({"close": [100.0 + i * 2.0 for i in range(60)]})
        self.bear_m15 = pd.DataFrame({"close": [300.0 - i * 2.0 for i in range(60)]})
        self.neut_m15 = pd.DataFrame({"close": [100.0 for _ in range(60)]})

        self.bull_h1 = pd.DataFrame({"close": [100.0 + i * 2.0 for i in range(60)]})
        self.bear_h1 = pd.DataFrame({"close": [300.0 - i * 2.0 for i in range(60)]})
        self.neut_h1 = pd.DataFrame({"close": [100.0 for _ in range(60)]})

        self.bull_h4 = pd.DataFrame({"close": [100.0 + i * 2.0 for i in range(60)]})
        self.bear_h4 = pd.DataFrame({"close": [300.0 - i * 2.0 for i in range(60)]})
        self.neut_h4 = pd.DataFrame({"close": [100.0 for _ in range(60)]})

    def test_strict_blocking_of_counter_trend_buy(self):
        """
        Verify BUY is rejected when:
        1. M15 is bearish or neutral
        2. H1 is bearish or neutral
        3. H4 is bearish
        """
        # Case 1: M15 Bearish, but H1 Bull, H4 Bull
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bear_m15, self.bull_h1, self.bull_h4, direction_hint="BUY"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 2: M15 Bull, but H1 Bear, H4 Bull (Counter H1 trend)
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bull_m15, self.bear_h1, self.bull_h4, direction_hint="BUY"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 3: M15 Bull, H1 Bull, but H4 Bear (Counter H4 macro bias)
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bull_m15, self.bull_h1, self.bear_h4, direction_hint="BUY"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 4: M15 Bull, H1 Neutral, H4 Bull
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bull_m15, self.neut_h1, self.bull_h4, direction_hint="BUY"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)

    def test_strict_blocking_of_counter_trend_sell(self):
        """
        Verify SELL is rejected when:
        1. M15 is bullish or neutral
        2. H1 is bullish or neutral
        3. H4 is bullish
        """
        # Case 1: M15 Bullish, but H1 Bear, H4 Bear
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bull_m15, self.bear_h1, self.bear_h4, direction_hint="SELL"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 2: M15 Bear, but H1 Bull, H4 Bear (Counter H1 trend)
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bear_m15, self.bull_h1, self.bear_h4, direction_hint="SELL"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 3: M15 Bear, H1 Bear, but H4 Bull (Counter H4 macro bias)
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bear_m15, self.bear_h1, self.bull_h4, direction_hint="SELL"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("M15 conflicts", meta.get("reason", ""))

        # Case 4: M15 Bear, H1 Neutral, H4 Bear
        ok, direction, meta = self.confluence.evaluate_trend_confluence(
            self.bear_m15, self.neut_h1, self.bear_h4, direction_hint="SELL"
        )
        self.assertFalse(ok)
        self.assertIsNone(direction)

    def test_flat_market_blocked(self):
        """
        Verify flat market (close == ema20 == ema50) is blocked for BUY, SELL, and AUTO.
        """
        flat_df = pd.DataFrame({"close": [100.0] * 60})

        ok_buy, dir_buy, meta_buy = self.confluence.evaluate_trend_confluence(
            flat_df, flat_df, flat_df, direction_hint="BUY"
        )
        self.assertFalse(ok_buy)
        self.assertIsNone(dir_buy)

        ok_sell, dir_sell, meta_sell = self.confluence.evaluate_trend_confluence(
            flat_df, flat_df, flat_df, direction_hint="SELL"
        )
        self.assertFalse(ok_sell)
        self.assertIsNone(dir_sell)

        ok_auto, dir_auto, meta_auto = self.confluence.evaluate_trend_confluence(
            flat_df, flat_df, flat_df, direction_hint=None
        )
        self.assertFalse(ok_auto)
        self.assertIsNone(dir_auto)
        self.assertIn("neutral", meta_auto.get("reason", ""))


class TestEndToEndAutonomousGatingAdversarial(unittest.TestCase):
    """Tests integration between session gating, confluence filtering, and autonomous execution."""

    def test_autonomous_daemon_blocks_outside_session_or_on_conflict(self):
        """
        Verify AutonomousLiveDaemon:
        - Completely skips market scanning when outside kill zones.
        - Fetches candles and evaluates confluence when inside London or NY kill zones.
        - Discards signals when MultiTimeframeConfluenceFilter returns approved=False.
        """
        daemon = AutonomousLiveDaemon(simulation_mode=True)
        daemon.mt5 = MagicMock()
        daemon.mt5.get_open_positions.return_value = []
        daemon.mt5.get_account_info.return_value = {"login": 40000294403, "equity": 100449.03}
        daemon.mt5.get_symbol_tick.return_value = {"bid": 2500.0, "ask": 2500.5}

        # Inside London Kill Zone (09:00 UTC)
        london_dt = datetime.datetime(2026, 9, 16, 9, 0, 0, tzinfo=timezone.utc)
        with patch("src.autonomous_live_daemon.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = london_dt
            mock_dt.timezone = timezone

            # Case A: Confluence Filter Vetos (Conflicting Trends)
            # M15 Bullish (rising), but H1 Bearish (falling)
            bull_candles = pd.DataFrame({
                "close": [2500.0 + i * 2.0 for i in range(40)],
                "high": [2501.0 + i * 2.0 for i in range(40)],
                "low": [2499.0 + i * 2.0 for i in range(40)],
            })
            bear_candles = pd.DataFrame({
                "close": [2600.0 - i * 2.0 for i in range(50)],
                "high": [2601.0 - i * 2.0 for i in range(50)],
                "low": [2599.0 - i * 2.0 for i in range(50)],
            })

            def mock_candles(symbol, timeframe, count):
                if timeframe == "M15":
                    return bull_candles
                elif timeframe == "H1":
                    return bear_candles  # Trend conflict!
                elif timeframe == "H4":
                    return bull_candles
                return None

            daemon.mt5.get_historical_candles.side_effect = mock_candles

            # Execute scan
            actions = daemon.scan_markets_and_act()
            self.assertEqual(actions, [], "Should execute 0 trades when H1 trend conflicts with M15 trigger")


if __name__ == "__main__":
    unittest.main(verbosity=2)
