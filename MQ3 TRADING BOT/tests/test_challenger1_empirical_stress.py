"""
tests/test_challenger1_empirical_stress.py — Adversarial Empirical Stress Harness.
Executed by Challenger 1 to rigorously stress test all core subsystems under extreme boundary conditions,
numerical edge cases, thread concurrency, malformed inputs, and disaster scenarios.
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import tempfile
import threading
import numpy as np
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.state_backup_manager import StateBackupManager
from src.disaster_recovery_watchdog import DisasterRecoveryWatchdog
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine
from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.whatsapp_qr_manager import WhatsAppQRManager, is_whitelisted_number, AUTHORIZED_CONTACTS, ELITE_TRADE_GROUP_JID


# ==============================================================================
# 1. ADVERSARIAL RISK ENGINE & MATHEMATICAL BOUNDARIES
# ==============================================================================

class TestAladdinRiskEngineStress:
    """Stress tests Aladdin VaR/CVaR and Fractional Kelly under extreme conditions."""

    def test_parametric_var_cvar_extreme_equity(self):
        engine = AladdinRiskEngine()
        # Near-zero equity
        res_zero = engine.compute_parametric_var_cvar(equity=0.001, daily_volatility=0.02)
        assert res_zero["var_99_dollar"] >= 0.0
        assert res_zero["cvar_99_dollar"] >= res_zero["var_99_dollar"]

        # Huge equity ($100M)
        res_huge = engine.compute_parametric_var_cvar(equity=100_000_000.0, daily_volatility=0.035)
        assert res_huge["var_99_dollar"] > 0
        assert res_huge["cvar_99_dollar"] > res_huge["var_99_dollar"]
        assert res_huge["var_99_pct"] > 0

    def test_parametric_var_cvar_extreme_volatility(self):
        engine = AladdinRiskEngine()
        # Zero volatility
        res_zero_vol = engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=0.0)
        assert res_zero_vol["var_99_dollar"] == 0.0
        assert res_zero_vol["cvar_99_dollar"] == 0.0

        # Ultra-high volatility (e.g. 500% daily in flash crash)
        res_high_vol = engine.compute_parametric_var_cvar(equity=25000.0, daily_volatility=5.0)
        assert res_high_vol["var_99_dollar"] > 25000.0
        assert res_high_vol["cvar_99_dollar"] > res_high_vol["var_99_dollar"]

    def test_fractional_kelly_boundary_conditions(self):
        engine = AladdinRiskEngine()

        # 0% win rate -> must return baseline minimum (0.0025)
        risk_zero = engine.compute_fractional_kelly(win_rate=0.0, payoff_ratio=2.0)
        assert risk_zero == 0.0025

        # 100% win rate with massive payoff -> must cap at max_risk_cap_pct (0.0075)
        risk_max = engine.compute_fractional_kelly(win_rate=1.0, payoff_ratio=10.0)
        assert risk_max == 0.0075

        # Extreme payoff ratio (0.0001)
        risk_low_b = engine.compute_fractional_kelly(win_rate=0.5, payoff_ratio=0.0001)
        assert risk_low_b == 0.0025

        # High standard error (win_rate_se = 0.4)
        risk_high_se = engine.compute_fractional_kelly(win_rate=0.45, payoff_ratio=2.0, win_rate_se=0.4)
        assert risk_high_se == 0.0025

    def test_pre_trade_stress_test_extreme_drawdown(self):
        engine = AladdinRiskEngine()
        equity = 25000.0
        max_daily_loss = 625.0  # 2.5% on 25k

        # Case 1: Low risk trade within limit
        res_pass = engine.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=100.0,
            open_positions=[],
            max_daily_loss_dollar=max_daily_loss
        )
        assert res_pass["passed"] is True
        assert res_pass["risk_utilization_pct"] == 16.0

        # Case 2: Risk exceeds 80% daily limit (80% of 625 = 500)
        res_fail = engine.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=550.0,
            open_positions=[],
            max_daily_loss_dollar=max_daily_loss
        )
        assert res_fail["passed"] is False
        assert "STRESS_TEST_EXCEEDED" in res_fail["reason"]

        # Case 3: Multiple open positions in Gold and Crypto pushing risk over cap
        open_pos = [
            {"symbol": "XAUUSD", "price_open": 2400.0, "sl": 2390.0, "volume": 0.5},  # $500 risk
            {"symbol": "BTCUSD", "price_open": 60000.0, "sl": 59000.0, "volume": 0.1} # $100 risk
        ]
        res_multi = engine.evaluate_pre_trade_stress_test(
            equity=equity,
            prospective_risk_dollar=50.0,
            open_positions=open_pos,
            max_daily_loss_dollar=max_daily_loss
        )
        assert res_multi["passed"] is False
        assert res_multi["total_stressed_risk_dollar"] == 650.0


# ==============================================================================
# 2. FUNDING PIPS 25K/50K/100K COMPLIANCE & DRAWDOWN BOUNDARY STRESS
# ==============================================================================

class TestFundingPipsBoundaryStress:
    """Rigorous boundary value testing for Funding Pips rules."""

    def test_daily_drawdown_exact_boundary(self):
        fp = FundingPipsExpert("25k")
        # Target: $25,000, 2.5% Safe Cap = $625.00
        # SOD baseline = 25000.0
        fp.daily_high_watermark = 25000.0

        # Boundary 1: $624.99 loss ($24,375.01 equity) -> Must PASS
        can_trade_pass, _ = fp.can_trade(balance=25000.0, equity=24375.01)
        assert can_trade_pass is True

        # Boundary 2: $625.00 loss ($24,375.00 equity) -> Must FAIL (Trigger safe guard)
        can_trade_exact, msg = fp.can_trade(balance=25000.0, equity=24375.00)
        assert can_trade_exact is False
        assert "Daily Drawdown Guard Triggered" in msg

        # Boundary 3: $625.01 loss ($24,374.99 equity) -> Must FAIL
        can_trade_fail, _ = fp.can_trade(balance=25000.0, equity=24374.99)
        assert can_trade_fail is False

    def test_overall_drawdown_exact_boundary(self):
        fp = FundingPipsExpert("25k")
        # Target: $25,000, 6.0% Safe Cap = $1,500.00
        # Absolute floor: $23,500.00

        # Boundary 1: $1,499.99 loss ($23,500.01 equity) -> Must PASS (assuming daily reset doesn't breach)
        fp.daily_high_watermark = 23600.0
        can_pass, _ = fp.can_trade(balance=23600.0, equity=23500.01)
        assert can_pass is True

        # Boundary 2: $1,500.00 loss ($23,500.00 equity) -> Must FAIL
        can_fail, msg = fp.can_trade(balance=23600.0, equity=23500.00)
        assert can_fail is False
        assert "Overall Drawdown Guard Triggered" in msg

    def test_trailing_high_watermark_ratchet(self):
        fp = FundingPipsExpert("25k")
        # Step 1: Equity reaches $28,000 (Ratchets absolute_high_watermark)
        fp.update_daily_watermark(equity=28000.0, balance=28000.0)
        assert fp.absolute_high_watermark == 28000.0

        # 6.0% max loss from target = $1,500. Trailing floor = $28,000 - $1,500 = $26,500.00
        fp.daily_high_watermark = 28000.0

        # Equity at $27,400.00 (loss = $600 < $625 daily cap, and equity > $26,500 floor) -> PASS
        can_p, _ = fp.can_trade(balance=28000.0, equity=27400.0)
        assert can_p is True

        # Equity drops to $26,500.00 -> FAIL
        can_f, msg = fp.can_trade(balance=28000.0, equity=26500.0)
        assert can_f is False
        assert "Trailing HWM Drawdown Floor Reached" in msg or "Daily Drawdown" in msg

    def test_consistency_pacing_evaluation(self):
        fp = FundingPipsExpert("25k")
        # Target: $2,000 profit, 35% cap = $700.00

        # Case 1: Today profit $699.99 -> SAFE
        res1 = fp.evaluate_consistency_pacing(today_profit=699.99, total_profit_target=2000.0)
        assert res1["is_pacing_safe"] is True
        assert res1["recommendation"] == "STANDARD_RISK"

        # Case 2: Today profit $700.00 -> SAFE
        res2 = fp.evaluate_consistency_pacing(today_profit=700.00, total_profit_target=2000.0)
        assert res2["is_pacing_safe"] is True

        # Case 3: Today profit $700.01 -> SCALE DOWN
        res3 = fp.evaluate_consistency_pacing(today_profit=700.01, total_profit_target=2000.0)
        assert res3["is_pacing_safe"] is False
        assert res3["recommendation"] == "CONSERVATIVE_SCALE_DOWN"

    def test_audit_trade_risk_reward_and_mandatory_sltp(self):
        fp = FundingPipsExpert("25k")

        # Missing SL/TP -> FAIL
        res_no_sl = fp.audit_trade("BTCUSD", "BUY", 60000.0, 0.0, 62000.0, 0)
        assert res_no_sl["passed"] is False

        # R:R ratio < 1.0 (e.g. SL dist = 100, TP dist = 50 -> RR = 0.5) -> FAIL
        res_bad_rr = fp.audit_trade("EURUSD", "BUY", 1.1000, 1.0900, 1.1050, 0)
        assert res_bad_rr["passed"] is False
        assert "minimum safety floor" in res_bad_rr["reason"]

        # Valid 1:2 R:R -> PASS
        res_good = fp.audit_trade("EURUSD", "BUY", 1.1000, 1.0950, 1.1100, 0)
        assert res_good["passed"] is True

        # Max open positions cap (tier 25k max 2) -> FAIL
        res_max_pos = fp.audit_trade("EURUSD", "BUY", 1.1000, 1.0950, 1.1100, 2)
        assert res_max_pos["passed"] is False


# ==============================================================================
# 3. FINMEM CONJUGATE BAYESIAN LEARNING & CONCURRENCY STRESS
# ==============================================================================

class TestFinMemBayesianConjugateStress:
    """Stress tests FinMem Beta-Binomial conjugate updating and concurrency."""

    @pytest.fixture
    def temp_memory_dir(self):
        tmp = tempfile.mkdtemp(prefix="test_finmem_challenger_")
        yield tmp
        shutil.rmtree(tmp, ignore_errors=True)

    def test_bayesian_weight_clamping_invariants(self, temp_memory_dir):
        agent = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        pattern = "TEST_PATTERN_EXTREME"

        # 50 consecutive WINS
        for _ in range(50):
            res = agent.bayesian_update_pattern(pattern, "WIN", profit=150.0)
            assert 0.65 <= res["weight"] <= 1.60

        assert res["weight"] > 1.50
        assert res["weight"] <= 1.60
        assert res["alpha"] > 40.0

        # 100 consecutive LOSSES on a separate pattern to test downward convergence towards 0.65
        loss_pattern = "TEST_PATTERN_LOSS_EXTREME"
        for _ in range(100):
            res_loss = agent.bayesian_update_pattern(loss_pattern, "LOSS", profit=-100.0)
            assert 0.65 <= res_loss["weight"] <= 1.60

        assert res_loss["weight"] < 0.75
        assert res_loss["weight"] >= 0.65
        assert res_loss["beta"] > 90.0

    def test_episodic_memory_ring_buffer_cap(self, temp_memory_dir):
        agent = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        # Record 550 experiences
        for i in range(550):
            agent.record_episodic_experience(
                symbol="EURUSD",
                direction="BUY",
                pnl=50.0 if i % 2 == 0 else -30.0,
                pattern="M15_ORDER_BLOCK_RETEST",
                reason=f"Stress test sample {i}",
                regime="TRENDING"
            )

        # Buffer must be capped at 500
        assert len(agent.episodic_memory) == 500
        summary = agent.get_cognitive_ai_summary()
        assert summary["total_episodic_experiences"] == 500
        assert summary["win_rate_pct"] == 50.0

    def test_multithreaded_bayesian_update_concurrency(self, temp_memory_dir):
        agent = DeepSelfLearningAgent(memory_dir=temp_memory_dir)
        num_threads = 8
        updates_per_thread = 25
        errors = []

        def worker(thread_id):
            try:
                for j in range(updates_per_thread):
                    outcome = "WIN" if (thread_id + j) % 2 == 0 else "LOSS"
                    agent.record_episodic_experience(
                        symbol="BTCUSD",
                        direction="BUY",
                        pnl=100.0 if outcome == "WIN" else -80.0,
                        pattern=f"PATTERN_T_{thread_id}",
                        reason="Concurrency stress",
                        regime="HIGH_VOL"
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(agent.episodic_memory) == num_threads * updates_per_thread

        # Verify semantic memory file is valid JSON
        with open(agent.semantic_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert "pattern_confidence_weights" in saved_data
            for tid in range(num_threads):
                pat = f"PATTERN_T_{tid}"
                assert pat in saved_data["pattern_confidence_weights"]
                assert 0.65 <= saved_data["pattern_confidence_weights"][pat] <= 1.60


# ==============================================================================
# 4. STATE BACKUP & DISASTER RECOVERY INTEGRITY STRESS
# ==============================================================================

class TestStateBackupAndWatchdogStress:
    """Stress tests snapshot creation, corruption detection, and process watchdog."""

    @pytest.fixture
    def mock_env(self):
        tmp_dir = tempfile.mkdtemp(prefix="test_backup_challenger_")
        ws_root = os.path.join(tmp_dir, "workspace")
        backup_dir = os.path.join(ws_root, "data", "backups")
        os.makedirs(os.path.join(ws_root, "data", "cognitive_memory"), exist_ok=True)

        # Create dummy config and db
        with open(os.path.join(ws_root, "config.json"), "w") as f:
            json.dump({"version": "2.0.0", "symbol": "BTCUSD"}, f)

        with open(os.path.join(ws_root, "data", "cognitive_memory", "semantic_memory.json"), "w") as f:
            json.dump({"rules": ["Rule1", "Rule2"]}, f)

        db_path = os.path.join(ws_root, "data", "trade_memory.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT, pnl REAL);")
        conn.execute("INSERT INTO trades VALUES (1, 'BTCUSD', 450.50);")
        conn.commit()
        conn.close()

        yield ws_root, backup_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_snapshot_creation_and_atomic_restore(self, mock_env):
        ws_root, backup_dir = mock_env
        mgr = StateBackupManager(workspace_root=ws_root, backup_dir=backup_dir)

        # 1. Create Snapshot
        snap = mgr.create_snapshot(label="test_clean")
        assert os.path.exists(snap["absolute_path"])
        assert snap["file_count"] >= 3
        assert snap["sha256"] is not None

        # 2. Modify live state
        with open(os.path.join(ws_root, "config.json"), "w") as f:
            json.dump({"version": "CORRUPTED"}, f)

        # 3. Restore Snapshot
        success = mgr.restore_snapshot(snap["absolute_path"], verify_sqlite=True)
        assert success is True

        # 4. Verify restored content matches original
        with open(os.path.join(ws_root, "config.json"), "r") as f:
            cfg = json.load(f)
            assert cfg["version"] == "2.0.0"

    def test_tampered_archive_checksum_corruption_detection(self, mock_env):
        ws_root, backup_dir = mock_env
        mgr = StateBackupManager(workspace_root=ws_root, backup_dir=backup_dir)

        # Create snapshot
        snap = mgr.create_snapshot(label="tamper_target")
        archive_path = snap["absolute_path"]

        # Tamper with archive file content (append random bytes to break SHA256 & archive)
        with open(archive_path, "ab") as f:
            f.write(b"CORRUPTION_BYTES_ADVERSARIAL")

        # Attempt restore -> Must safely detect checksum mismatch and return False
        restore_result = mgr.restore_snapshot(archive_path, verify_sqlite=True)
        assert restore_result is False

        # Live state must remain uncorrupted
        with open(os.path.join(ws_root, "config.json"), "r") as f:
            cfg = json.load(f)
            assert cfg["version"] == "2.0.0"

    def test_backup_pruning_retention_guardrail(self, mock_env):
        ws_root, backup_dir = mock_env
        mgr = StateBackupManager(workspace_root=ws_root, backup_dir=backup_dir)

        # Create 4 snapshots
        snaps = [mgr.create_snapshot(label=f"snap_{i}") for i in range(4)]
        assert len(mgr.get_backup_manifest()) == 4

        # Prune with retention 0 days but min_keep = 2 -> Exactly 2 newest must be kept
        pruned = mgr.prune_snapshots(retention_days=0, min_keep=2)
        assert pruned == 2
        remaining = mgr.get_backup_manifest()
        assert len(remaining) == 2


# ==============================================================================
# 5. FREE PUBLIC FEEDS & WEEKEND CRYPTO ARBITRAGE STRESS
# ==============================================================================

class TestCryptoFeedsAndArbitrageStress:
    """Stress tests public feeds parser and weekend arbitrage calculations."""

    def test_hyperliquid_perpetual_context_parsing(self):
        engine = FreePublicFeedsEngine()

        # Normal context parsing with live or cached call
        ctx = engine.get_perpetual_context("SOL")
        assert isinstance(ctx, dict)
        assert "mark_price" in ctx
        assert "funding_rate_8h" in ctx
        assert ctx["mark_price"] > 0

    def test_weekend_arbitrage_window_determination(self):
        arb = WeekendCryptoArbitrageEngine()

        # Case 1: Friday 21:59:59 UTC -> Not closed yet
        dt_fri_pre = datetime(2026, 8, 14, 21, 59, 59, tzinfo=timezone.utc)
        assert arb.is_traditional_market_closed(dt_fri_pre) is False

        # Case 2: Friday 22:00:00 UTC -> Market closed (Weekend active)
        dt_fri_start = datetime(2026, 8, 14, 22, 0, 0, tzinfo=timezone.utc)
        assert arb.is_traditional_market_closed(dt_fri_start) is True

        # Case 3: Saturday 12:00:00 UTC -> Market closed (Weekend active)
        dt_sat = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert arb.is_traditional_market_closed(dt_sat) is True

        # Case 4: Sunday 20:59:59 UTC -> Market closed (Weekend active)
        dt_sun = datetime(2026, 8, 16, 20, 59, 59, tzinfo=timezone.utc)
        assert arb.is_traditional_market_closed(dt_sun) is True

        # Case 5: Sunday 21:00:01 UTC -> Forex reopened
        dt_sun_post = datetime(2026, 8, 16, 21, 0, 1, tzinfo=timezone.utc)
        assert arb.is_traditional_market_closed(dt_sun_post) is False

    def test_funding_spread_basis_inversion(self):
        arb = WeekendCryptoArbitrageEngine()
        spread_info = arb.track_funding_spread("BTCUSD")
        assert "symbol" in spread_info
        assert "spot_price" in spread_info
        assert "perp_mark_price" in spread_info
        assert "basis_spread" in spread_info
        assert "annualized_funding_pct" in spread_info


# ==============================================================================
# 6. WHATSAPP QR COMMAND ROUTER & WHITELIST SECURITY STRESS
# ==============================================================================

class TestWhatsAppWhitelistAndCommandRouterStress:
    """Stress tests whitelist security and command routing with adversarial inputs."""

    def test_whitelist_security_verification(self):
        # Authorized Master Owner and Elite Trade Group
        assert is_whitelisted_number("923468053268@s.whatsapp.net") is True
        assert is_whitelisted_number(ELITE_TRADE_GROUP_JID) is True

        # Purged secondary family numbers (Strictly Rejected)
        assert is_whitelisted_number("923487117832@s.whatsapp.net") is False
        assert is_whitelisted_number("923322555238@s.whatsapp.net") is False
        assert is_whitelisted_number("923375893095@s.whatsapp.net") is False

        # Unauthorized numbers / Attackers
        assert is_whitelisted_number("+19998887777@s.whatsapp.net") is False
        assert is_whitelisted_number("hacker@malicious.com") is False
        assert is_whitelisted_number("") is False
        assert is_whitelisted_number(None) is False

    def test_adversarial_command_handling(self):
        qr = WhatsAppQRManager()
        sender = "923468053268@s.whatsapp.net"

        # List of interactive commands to verify
        commands = [
            "status", "trades", "risk", "report", "fleet",
            "gold", "crypto", "news", "world", "whales",
            "crisis", "rates", "scan", "signal",
            "buy gold 0.05", "sell eurusd 0.05", "breakeven",
            "scale 50%", "pause", "resume", "advisor"
        ]

        for cmd in commands:
            resp = qr.handle_incoming_command(cmd, sender)
            assert isinstance(resp, str)
            assert len(resp) > 0

        # Adversarial payload: SQL injection, Unicode, huge strings
        adversarial_payloads = [
            "'; DROP TABLE trades; --",
            "<script>alert(1)</script>",
            "consult " + "A" * 500,
            "Main Gold buy karna chahta hoon",
            "   \n\t  STATUS   \r\n  "
        ]

        for bad_cmd in adversarial_payloads:
            resp = qr.handle_incoming_command(bad_cmd, sender)
            assert resp is not None
            assert isinstance(resp, str)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
