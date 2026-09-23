"""
test_reviewer2_m1_adversarial.py — Empirical Adversarial Stress Test Suite for Milestone M1.
============================================================================================
Probes edge conditions and failure modes:
1. Missing, empty, malformed, and NaN candle data in trend_confluence_filter and market_analyzer.
2. Zero, negative, and extreme ATR in pipdance_engine, risk_manager, fleet_risk_manager.
3. Extreme balances (0, negative, micro, $100M) across all risk and sizing engines.
4. Timezone awareness in InstitutionalKnowledge and TradeAdmissionGate.
5. Integrity check: ensure calculations are genuine, not hardcoded or bypassed.
"""

from __future__ import annotations

import datetime
from datetime import timezone, timedelta
import json
import math
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from src.trend_confluence_filter import MultiTimeframeConfluenceFilter
from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
from src.risk_manager import RiskManager
from src.fleet_risk_manager import FleetRiskManager
from src.portfolio_risk_service import PortfolioRiskService, AccountRiskState
from src.institutional_knowledge import InstitutionalKnowledge
from src.trade_admission import TradeAdmissionGate


class TestMilestoneM1AdversarialStress(unittest.TestCase):

    def setUp(self):
        with open(MQ3_ROOT / "config.json", "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.confluence = MultiTimeframeConfluenceFilter()
        self.pip_engine = PipdanceFastTrackEngine()
        self.rm = RiskManager(self.cfg)
        self.frm = FleetRiskManager()
        self.prs = PortfolioRiskService()
        self.gate = TradeAdmissionGate()

    # -------------------------------------------------------------------------
    # 1. Edge Condition: Missing, Empty, Malformed, and NaN Candles
    # -------------------------------------------------------------------------
    def test_edge_candles_none_or_empty(self):
        """None or empty DataFrames should fail gracefully with False and safe telemetry."""
        # All None
        ok, direction, meta = self.confluence.evaluate_trend_confluence(None, None, None)
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("Insufficient M15", meta.get("reason", ""))

        # Empty DataFrame
        empty_df = pd.DataFrame()
        ok, direction, meta = self.confluence.evaluate_trend_confluence(empty_df, empty_df, empty_df)
        self.assertFalse(ok)
        self.assertIsNone(direction)

        # Insufficient rows (< 20)
        short_df = pd.DataFrame({"close": [100.0 + i for i in range(15)]})
        ok, direction, meta = self.confluence.evaluate_trend_confluence(short_df, short_df, short_df)
        self.assertFalse(ok)
        self.assertIsNone(direction)

        # Missing 'close' column
        no_close_df = pd.DataFrame({"price": [100.0 + i for i in range(30)]})
        ok, direction, meta = self.confluence.evaluate_trend_confluence(no_close_df, no_close_df, no_close_df)
        self.assertFalse(ok)
        self.assertIsNone(direction)

    def test_edge_candles_nan_or_inf(self):
        """Candles containing NaN or Inf should not cause unhandled crashes."""
        nan_df = pd.DataFrame({"close": [float("nan")] * 30})
        ok, direction, meta = self.confluence.evaluate_trend_confluence(nan_df, nan_df, nan_df)
        self.assertFalse(ok)

    def test_edge_candles_flat_market(self):
        """Flat market (zero volatility, identical closes) should be handled as neutral."""
        flat_df = pd.DataFrame({"close": [2500.0] * 50})
        ok, direction, meta = self.confluence.evaluate_trend_confluence(flat_df, flat_df, flat_df)
        self.assertFalse(ok)
        self.assertIsNone(direction)
        self.assertIn("neutral", meta.get("reason", "").lower())

    # -------------------------------------------------------------------------
    # 2. Edge Condition: Zero, Negative, and NaN ATR
    # -------------------------------------------------------------------------
    def test_edge_zero_and_negative_atr_pipdance_engine(self):
        """Pipdance engine must fall back safely when ATR is 0 or negative."""
        balance = 100449.03
        for bad_atr in [0.0, -1.0, -0.0001]:
            res = self.pip_engine.calculate_risk(balance=balance, atr=bad_atr, symbol="XAUUSD", entry_price=2500.0)
            self.assertGreater(res["atr"], 0, f"Failed fallback for ATR {bad_atr}")
            self.assertLessEqual(res["lot_size"], 0.10)
            self.assertLessEqual(res["risk_usd"], 100.01)
            self.assertGreater(res["sl_dist"], 0)

        # Forex with zero ATR
        res_fx = self.pip_engine.calculate_risk(balance=balance, atr=0.0, symbol="EURUSD", entry_price=1.0850)
        self.assertGreater(res_fx["atr"], 0)
        self.assertLessEqual(res_fx["lot_size"], 0.20)
        self.assertLessEqual(res_fx["risk_usd"], 100.01)

        # Crypto with zero ATR
        res_crypto = self.pip_engine.calculate_risk(balance=balance, atr=0.0, symbol="BTCUSD", entry_price=60000.0)
        self.assertGreater(res_crypto["atr"], 0)
        self.assertLessEqual(res_crypto["lot_size"], 0.01)
        self.assertLessEqual(res_crypto["risk_usd"], 100.01)

    def test_edge_nan_atr_vulnerability(self):
        """Adversarial probe: float('nan') ATR bypasses 'atr <= 0' check and raises ValueError in math.floor."""
        # This confirms our finding that float('nan') ATR causes an unhandled ValueError in math.floor(raw_lots)
        with self.assertRaises(ValueError):
            self.pip_engine.calculate_risk(balance=100449.03, atr=float("nan"), symbol="XAUUSD", entry_price=2500.0)

    def test_edge_zero_sl_pips_risk_managers(self):
        """RiskManager and FleetRiskManager should return minimum safe lot size when sl_pips <= 0."""
        # RiskManager
        lot_zero = self.rm.calculate_position_size(100449.03, 0.0, "XAUUSD")
        self.assertEqual(lot_zero, 0.01)
        lot_neg = self.rm.calculate_position_size(100449.03, -10.0, "XAUUSD")
        self.assertEqual(lot_neg, 0.01)

        # FleetRiskManager calculate_position_size
        frm_zero = self.frm.calculate_position_size(100449.03, 0.0, "XAUUSD")
        self.assertEqual(frm_zero, 0.01)

        # FleetRiskManager calculate_dynamic_lot_size with identical entry and SL
        dyn_zero = self.frm.calculate_dynamic_lot_size(1, "XAUUSD", 2500.0, 2500.0)
        self.assertEqual(dyn_zero, 0.01)

    # -------------------------------------------------------------------------
    # 3. Edge Condition: Extreme Balances
    # -------------------------------------------------------------------------
    def test_edge_extreme_balance_astronomical(self):
        """Astronomical balance ($100,000,000) must NEVER breach lot ceilings or $100 dollar risk."""
        astro_balance = 100_000_000.0
        # Pipdance engine
        res_gold = self.pip_engine.calculate_risk(balance=astro_balance, atr=2.0, symbol="XAUUSD", entry_price=2500.0)
        self.assertLessEqual(res_gold["lot_size"], 0.10)
        self.assertLessEqual(res_gold["risk_usd"], 100.01)

        res_fx = self.pip_engine.calculate_risk(balance=astro_balance, atr=0.0015, symbol="EURUSD", entry_price=1.0850)
        self.assertLessEqual(res_fx["lot_size"], 0.20)
        self.assertLessEqual(res_fx["risk_usd"], 100.01)

        res_crypto = self.pip_engine.calculate_risk(balance=astro_balance, atr=500.0, symbol="BTCUSD", entry_price=60000.0)
        self.assertLessEqual(res_crypto["lot_size"], 0.01)
        self.assertLessEqual(res_crypto["risk_usd"], 100.01)

        # RiskManager
        rm_gold = self.rm.calculate_position_size(astro_balance, 5.0, "XAUUSD")
        self.assertLessEqual(rm_gold, 0.10)

        rm_fx = self.rm.calculate_position_size(astro_balance, 5.0, "EURUSD")
        self.assertLessEqual(rm_fx, 0.20)

        rm_crypto = self.rm.calculate_position_size(astro_balance, 5.0, "BTCUSD")
        self.assertLessEqual(rm_crypto, 0.01)

        # FleetRiskManager
        frm_gold = self.frm.calculate_position_size(astro_balance, 5.0, "XAUUSD")
        self.assertLessEqual(frm_gold, 0.10)

        frm_fx = self.frm.calculate_position_size(astro_balance, 5.0, "EURUSD")
        self.assertLessEqual(frm_fx, 0.20)

        frm_crypto = self.frm.calculate_position_size(astro_balance, 5.0, "BTCUSD")
        self.assertLessEqual(frm_crypto, 0.01)

    def test_edge_extreme_balance_zero_or_negative(self):
        """Zero or negative balance in PortfolioRiskService should trigger drawdown limits."""
        acc = self.prs.get_or_register_account("40000294403", equity=0.0, balance=0.0)
        acc.current_equity = 0.0
        ok, reason = acc.evaluate_drawdown_limits()
        self.assertFalse(ok, "Account with $0 equity passed drawdown limits")
        self.assertIn("drawdown limit breached", reason.lower())

        acc.current_equity = -1000.0
        ok_neg, reason_neg = acc.evaluate_drawdown_limits()
        self.assertFalse(ok_neg, "Account with negative equity passed drawdown limits")
        self.assertIn("drawdown limit breached", reason_neg.lower())

    # -------------------------------------------------------------------------
    # 4. Edge Condition: Timezone Awareness
    # -------------------------------------------------------------------------
    def test_timezone_awareness_utc_vs_non_utc(self):
        """Check behavior when non-UTC timezone-aware datetime is passed."""
        # 12:00:00 UTC+5 (PKT) is 07:00:00 UTC (London Kill Zone open)
        tz_pkt = timezone(timedelta(hours=5))
        dt_pkt = datetime.datetime(2026, 9, 16, 12, 0, 0, tzinfo=tz_pkt)
        
        # Test how TradeAdmissionGate handles it:
        ctx = {
            "data_mode": "LIVE",
            "actionable": True,
            "market_open": True,
            "quote_observed_at": dt_pkt.isoformat(),
            "signal_generated_at": dt_pkt.isoformat(),
            "current_time_utc": dt_pkt.isoformat(),
            "quote_source": "MT5_TEST",
            "spread": 10.0,
            "typical_spread": 10.0,
            "news_clearance": {"verified": True, "is_blackout": False, "is_cleared": True, "age_seconds": 5.0}
        }
        admitted, reasons = self.gate.evaluate(ctx, live=True)
        # In TradeAdmissionGate, _timestamp converts dt_pkt to UTC (07:00 UTC) which IS London Kill Zone!
        has_kz_reject = any("outside London" in r for r in reasons)
        self.assertFalse(has_kz_reject, f"TradeAdmissionGate failed to normalize timezone-aware datetime to UTC: {reasons}")

        # In InstitutionalKnowledge.is_in_kill_zone(dt_pkt), it inspects dt.hour directly
        # When passed dt_pkt (hour=12), it treats it as 12:00 (which is ROLLOVER_OR_OFF_HOURS)
        is_kz, session = InstitutionalKnowledge.is_in_kill_zone(dt_pkt)
        self.assertFalse(is_kz)  # InstitutionalKnowledge assumes caller passes UTC
        # If passed converted UTC:
        dt_as_utc = dt_pkt.astimezone(timezone.utc)
        is_kz_utc, session_utc = InstitutionalKnowledge.is_in_kill_zone(dt_as_utc)
        self.assertTrue(is_kz_utc)
        self.assertEqual(session_utc, "LONDON_KILL_ZONE")

    # -------------------------------------------------------------------------
    # 5. Integrity & Non-Trivial Implementation Checks
    # -------------------------------------------------------------------------
    def test_integrity_dynamic_calculation(self):
        """Ensure calculations are dynamic and mathematical, not static stubs or hardcoded mocks."""
        # Varying SL distance beyond the ceiling clamp should produce varying lot sizes
        sl_pips_list = [50, 100, 200, 500]
        lots = [self.pip_engine.calculate_lot_size("EURUSD", 100.0, sl * 0.0001) for sl in sl_pips_list]
        self.assertEqual(lots, [0.20, 0.10, 0.05, 0.02])
        self.assertEqual(len(set(lots)), 4, "Lot size calculation failed to dynamically scale with SL distance")


if __name__ == "__main__":
    unittest.main(verbosity=2)
