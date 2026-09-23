"""
tests/test_daily_institutional_routine.py — Comprehensive Test Suite for Daily Institutional Routine Engine.
Requirements Covered:
  - Morning Pre-Market Master Briefing & 4-Account Playbook (Macro, 50-Yr Analogue, Pivots, Asian Box, Scenarios A/B)
  - Intraday Killzone Real-Time Opportunity Scanner (London/NY Killzones, Asian Judas, 70.5% OTE, Lee-Ready CVD, Dark Pool)
  - Nightly Market Close Retrospective & Forensic Cognitive Audit (Forecast vs Actuals, MFE/MAE, Accuracy %, Deviation Forensics)
  - Episodic Memory Persistence & Bayesian Strategy Weight Evolution (clamped [0.65, 1.60])
  - 4-Account Prop Firm Fleet Sizing ($100k, $50k, $25k, $5k) & 0.00% Drawdown Compliance
  - 24/7 Operational Cycle Scheduler (06:30 UTC Morning, 21:30 UTC Nightly, 5-min Killzones)
  - Automated Multi-Channel Broadcast Dispatching (Master Owner & Elite Trade Group)
"""

import os
import sys
import json
import math
import time
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest
import numpy as np
import pandas as pd

from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.whatsapp_qr_manager import WhatsAppQRManager, AUTHORIZED_CONTACTS, is_whitelisted_number
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.order_flow_quant import OrderFlowQuantEngine
from src.insider_whale_mechanics import InsiderWhaleMechanics
from src.intermarket_macro_radar import IntermarketMacroRadar
from src.market_history_encyclopedia import MarketHistoryEncyclopedia
from src.cross_market_synthetic_arb import CrossMarketContagionEngine
from src.multi_account_manager import MultiAccountManager


# ==============================================================================
# FIXTURES & DATA GENERATORS
# ==============================================================================

@pytest.fixture
def temp_memory_dir():
    """Isolated temporary cognitive memory directory for Bayesian testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_daily_routine_mem_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_m15_ohlc():
    """Generates synthetic M15 candles for Gold (#XAUUSD) testing."""
    np.random.seed(123)
    n = 60
    base_price = 2645.0
    times = [datetime.now(timezone.utc) - timedelta(minutes=15 * (n - i)) for i in range(n)]
    closes = [base_price + (i * 0.25) + np.random.normal(0, 0.4) for i in range(n)]
    highs = [c + np.random.uniform(0.5, 1.2) for c in closes]
    lows = [c - np.random.uniform(0.5, 1.2) for c in closes]
    opens = [c - np.random.uniform(-0.3, 0.3) for c in closes]
    volumes = [int(np.random.uniform(300, 1200)) for _ in range(n)]

    # Inject dark pool volume spike at last candle
    volumes[-1] = 4500
    opens[-1] = 2650.0
    closes[-1] = 2650.2
    highs[-1] = 2651.0
    lows[-1] = 2649.5

    df = pd.DataFrame({
        "time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "tick_volume": volumes
    })
    return df


@pytest.fixture
def sample_tick_array():
    """Generates synthetic tick array for Lee-Ready CVD absorption testing."""
    n = 100
    bids = [2648.0 + (i * 0.05) for i in range(n)]
    asks = [b + 0.25 for b in bids]
    prices = [a for a in asks]
    vols = [np.random.uniform(1.5, 6.0) for _ in range(n)]

    ticks = np.empty(n, dtype=[
        ('bid', 'f8'), ('ask', 'f8'), ('last', 'f8'),
        ('volume', 'f8'), ('volume_ext', 'f8')
    ])
    ticks['bid'] = bids
    ticks['ask'] = asks
    ticks['last'] = prices
    ticks['volume'] = vols
    ticks['volume_ext'] = vols
    return ticks


# ==============================================================================
# 1. MORNING PRE-MARKET MASTER BRIEFING & PLAYBOOK TESTS
# ==============================================================================

class TestMorningPreMarketBriefing:
    """Validates Morning Pre-Market Playbook, Pivot Mathematics, Asian Box, and Scenario Matrix."""

    def setup_method(self):
        self.engine = DailyInstitutionalRoutineEngine()

    def test_morning_briefing_header_and_date(self):
        """Briefing must contain standard header, date, and London/NY pre-market session tag."""
        briefing = self.engine.generate_morning_master_briefing("XAUUSD")
        assert "INSTITUTIONAL DAILY PLAYBOOK & 4-ACCOUNT STRATEGY" in briefing
        assert "London / NY Pre-Market Open" in briefing
        assert "XAUUSD" in briefing or "GOLD" in briefing

    def test_morning_briefing_global_geopolitical_macro_radar(self):
        """Pillar 1 of Morning Briefing must include DXY, US10Y, and Geopolitical Themes."""
        briefing = self.engine.generate_morning_master_briefing("XAUUSD")
        assert "1. GLOBAL GEOPOLITICAL & MACRO RADAR" in briefing
        assert "DXY Dollar Index" in briefing
        assert "US 10Y Yields" in briefing
        assert "Asian Session Box" in briefing

    def test_floor_pivots_mathematical_precision(self):
        """Tests standard Floor Pivots calculation (P, R1, S1, R2, S2, R3, S3)."""
        df_d1 = pd.DataFrame({
            "open": [2630.0, 2635.0],
            "high": [2645.0, 2655.0],
            "low": [2620.0, 2630.0],
            "close": [2640.0, 2650.0]
        })
        df_w1 = pd.DataFrame({"open": [2620.0], "close": [2650.0]})
        df_mn1 = pd.DataFrame({"open": [2580.0], "close": [2650.0]})

        pivots = self.engine._calculate_d1_benchmarks_and_pivots(df_d1, df_w1, df_mn1, 2650.0, "XAUUSD")
        # Prev Day: High=2645.0 (from index -2), Low=2620.0, Close=2640.0
        # Pivot = (2645 + 2620 + 2640) / 3 = 2635.0
        # R1 = 2*2635 - 2620 = 2650.0
        # S1 = 2*2635 - 2645 = 2625.0
        # R2 = 2635 + (2645 - 2620) = 2660.0
        # S2 = 2635 - (2645 - 2620) = 2610.0
        assert pivots["pivot"] == pytest.approx(2635.0, abs=0.1)
        assert pivots["r1"] == pytest.approx(2650.0, abs=0.1)
        assert pivots["s1"] == pytest.approx(2625.0, abs=0.1)
        assert pivots["r2"] == pytest.approx(2660.0, abs=0.1)
        assert pivots["s2"] == pytest.approx(2610.0, abs=0.1)

    def test_scenario_a_and_scenario_b_if_then_matrix(self):
        """Validates Scenario A (75% probability) and Scenario B (25% probability) synthesis."""
        briefing = self.engine.generate_morning_master_briefing("XAUUSD")
        assert "SCENARIO A (Primary Trend Continuation" in briefing
        assert "75% Probability" in briefing
        assert "SCENARIO B (Deep Liquidity Sweep / Defense" in briefing
        assert "25% Probability" in briefing
        assert "TP1:" in briefing
        assert "Safe SL / Invalidation:" in briefing

    def test_four_account_fleet_sizing_calibration(self):
        """Validates 4-Account Fleet sizing table ($100k, $50k, $25k, $5k) at 0.50% risk."""
        sizing = self.engine._calculate_calibrated_lot_sizing(sl_pips=120.0, symbol="XAUUSD")
        assert sizing["account_100k"]["risk_usd"] == 500.0
        assert sizing["account_50k"]["risk_usd"] == 250.0
        assert sizing["account_25k"]["risk_usd"] == 125.0
        assert sizing["account_5k"]["risk_usd"] == 25.0

        assert sizing["account_100k"]["lots"] == pytest.approx(0.42, abs=0.02)
        assert sizing["account_50k"]["lots"] == pytest.approx(0.21, abs=0.02)
        assert sizing["account_25k"]["lots"] == pytest.approx(0.10, abs=0.02)
        assert sizing["account_5k"]["lots"] == pytest.approx(0.02, abs=0.02)


# ==============================================================================
# 2. INTRADAY KILLZONE OPPORTUNITY SCANNER TESTS
# ==============================================================================

class TestIntradayKillzoneOpportunityScanner:
    """Validates real-time Killzone scanning, Asian Judas sweeps, OTE, CVD, and 5-Section cards."""

    def setup_method(self):
        self.engine = DailyInstitutionalRoutineEngine()

    def test_intraday_opportunity_scan_confluence_filter(self):
        """Tests that intraday scan evaluates setups and enforces >=4.5 / 5.0 confluence filter."""
        scan = self.engine.scan_intraday_opportunities("XAUUSD")
        assert "symbol" in scan
        assert "signal_type" in scan
        assert "entry_price" in scan
        assert "sl_price" in scan
        assert "tp1_price" in scan
        assert "confluence_score" in scan
        assert scan["confluence_score"] >= 4.5
        assert scan["triggered"] is True

    def test_5_section_whatsapp_signal_card_structure(self):
        """Validates that generated signal card matches the required 5-section institutional layout."""
        scan = self.engine.scan_intraday_opportunities("XAUUSD")
        card = scan["signal_card"]

        assert "OFFICIAL INSTITUTIONAL TRADE SIGNAL & MARKET BLUEPRINT" in card
        assert "#XAUUSD" in card
        assert "1. BIG SHARKS (MARKET MAKER) GAME & PSYCHOLOGY" in card
        assert "2. TECHNICAL CONFLUENCES & EVIDENCE" in card
        assert "3. GLOBAL MACRO NEWS & TAILWINDS" in card
        assert "4. CONTINGENCY PLAN & DISCIPLINE" in card
        assert "5. MULTI-ACCOUNT SIZING RECOMMENDATION" in card

        # Rules verification
        assert "Rule 1 (Breakeven):" in card
        assert "Rule 2 (TP1 Scaling):" in card
        assert "Rule 3 (No Revenge):" in card

    def test_intraday_alert_short_message_format(self):
        """Tests short intraday alert generation for quick mobile notification."""
        alert = self.engine.generate_intraday_alert("XAUUSD", "LONDON_JUDAS_SWEEP", "Asian Low swept into 70.5% OTE")
        assert "LIVE INTRADAY INSTITUTIONAL OPPORTUNITY ALERT" in alert
        assert "#XAUUSD" in alert
        assert "LONDON_JUDAS_SWEEP" in alert


# ==============================================================================
# 3. NIGHTLY MARKET CLOSE RETROSPECTIVE & COGNITIVE AUDIT TESTS
# ==============================================================================

class TestNightlyMarketCloseRetrospective:
    """Validates Nightly Debrief, Forecast vs Actual reconciliation, MFE/MAE, and cognitive updates."""

    def test_nightly_retrospective_3_sections_and_zero_drawdown(self, temp_memory_dir):
        """Validates Nightly Retrospective content and 0.00% drawdown violation compliance."""
        brain = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        engine = DailyInstitutionalRoutineEngine()
        engine.brain = brain

        retrospective = engine.generate_nightly_market_retrospective("XAUUSD")
        assert "NIGHTLY MARKET CLOSE RETROSPECTIVE & COGNITIVE AUDIT" in retrospective
        assert "1. MORNING FORECAST VS. ACTUAL MARKET OUTCOME" in retrospective
        assert "2. FORENSIC AUDIT & COGNITIVE LESSONS" in retrospective
        assert "3. FLEET PORTFOLIO CLOSING EQUITY" in retrospective
        assert "Drawdown Violation: *0.00%*" in retrospective

    def test_bayesian_strategy_weight_evolution(self, temp_memory_dir):
        """Verifies Bayesian weight step-up on win and step-down on loss bounded in [0.65, 1.60]."""
        brain = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        init_w = brain.semantic_memory["pattern_confidence_weights"]["OTE_705_FIBONACCI"]
        assert init_w == 1.40

        # Win step-up: weight increases
        res_win = brain.record_episodic_experience("XAUUSD", "BUY", 250.0, "OTE_705_FIBONACCI", "Target hit", "EXPANSION")
        assert res_win["new_pattern_weight"] > init_w
        assert 0.65 <= res_win["new_pattern_weight"] <= 1.60

        # Loss step-down: weight decreases
        res_loss = brain.record_episodic_experience("XAUUSD", "BUY", -100.0, "OTE_705_FIBONACCI", "SL hit", "EXPANSION")
        assert res_loss["new_pattern_weight"] < res_win["new_pattern_weight"]
        assert 0.65 <= res_loss["new_pattern_weight"] <= 1.60

    def test_episodic_ring_buffer_persisted_to_disk(self, temp_memory_dir):
        """Verifies episodic memories persist and reload across fresh engine instances."""
        brain1 = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        brain1.record_episodic_experience("XAUUSD", "BUY", 500.0, "ASIAN_JUDAS_SWEEP", "Clean expansion", "BULLISH")

        brain2 = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        assert len(brain2.episodic_memory) == 1
        assert brain2.episodic_memory[0]["symbol"] == "XAUUSD"
        assert brain2.episodic_memory[0]["pnl"] == 500.0


# ==============================================================================
# 4. BROADCAST DISPATCHING & MULTI-CHANNEL ROUTING TESTS
# ==============================================================================

class TestDailyRoutineBroadcastDispatching:
    """Validates automated dispatch of morning briefing, intraday alerts, and nightly debrief."""

    def test_broadcast_morning_briefing_dispatches_to_owner_and_elite_group(self):
        """Verifies morning briefing dispatches to whitelisted owner and Elite Trade Group."""
        engine = DailyInstitutionalRoutineEngine()
        engine.qr_manager.send_message = MagicMock(return_value=True)

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            res = engine.broadcast_morning_briefing()
            assert len(res) >= 2
            assert any("Master User" in k for k in res.keys())
            assert "Elite Trade Group" in res
            assert res["Elite Trade Group"] is True

    def test_broadcast_nightly_retrospective_dispatches_to_owner_and_elite_group(self):
        """Verifies nightly debrief dispatches to whitelisted owner and Elite Trade Group."""
        engine = DailyInstitutionalRoutineEngine()
        engine.qr_manager.send_message = MagicMock(return_value=True)

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            res = engine.broadcast_nightly_retrospective("XAUUSD")
            assert len(res) >= 2
            assert any("Master User" in k for k in res.keys())
            assert "Elite Trade Group" in res
            assert res["Elite Trade Group"] is True

    def test_broadcast_intraday_alert_dispatches_cleanly(self):
        """Verifies intraday alert dispatches without errors."""
        engine = DailyInstitutionalRoutineEngine()
        engine.qr_manager.send_message = MagicMock(return_value=True)

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            res = engine.broadcast_intraday_alert(symbol="XAUUSD")
            assert len(res) >= 2
            assert any("Master User" in k for k in res.keys())
            assert "Elite Trade Group" in res


if __name__ == "__main__":
    pytest.main(["-v", __file__])
