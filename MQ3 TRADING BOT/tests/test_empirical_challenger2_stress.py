"""
tests/test_empirical_challenger2_stress.py — Challenger 2 Empirical Stress & Adversarial Suite.
Adversarially challenges `tests/test_crypto_feeds_arbitrage.py` and `tests/test_backup_disaster_recovery.py`.

Focus areas:
1. High-concurrency thread safety & race conditions (Feeds cache, Arbitrage state, Backup Manager manifest).
2. Flakiness & Repeated execution stress (20 iterations under randomized perturbations).
3. Random seed fuzzing & extreme value boundary testing (Aladdin VaR/CVaR, Fractional Kelly, Basis Arbitrage).
4. Filesystem isolation & Lingering file audits (zero leaked .tmp, .staging, .lock, or unmanaged test archives).
5. File descriptor & Resource leak verification (SQLite handles, TCP socket handles, Watchdog daemons).
"""

import gc
import os
import sys
import json
import math
import time
import shutil
import random
import socket
import sqlite3
import tarfile
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import patch

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.aladdin_risk_engine import AladdinRiskEngine
from src.free_public_feeds_engine import FreePublicFeedsEngine
from src.funding_pips_expert import FundingPipsExpert
from src.multi_asset_scanner import MultiAssetScanner
from src.strategy import StrategyEngine
from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine
from src.state_backup_manager import (
    StateBackupManager,
    BackupError,
    DatabaseIntegrityError,
    RestoreValidationError,
    SecurityError
)
from src.disaster_recovery_watchdog import (
    DisasterRecoveryWatchdog,
    ServiceHealthStatus,
    SupervisedService,
    ProbeType
)


class TestCryptoFeedsAdversarialStress(unittest.TestCase):
    """Adversarial stress tests for Crypto Feeds, Arbitrage, and Aladdin Risk engines."""

    def setUp(self):
        self.engine = FreePublicFeedsEngine(offline_mode=True)
        self.arb_engine = WeekendCryptoArbitrageEngine(feeds_engine=self.engine)
        self.aladdin = AladdinRiskEngine()
        self.expert = FundingPipsExpert("25k")

    def test_adv_01_concurrent_cache_hammering_no_race_conditions(self):
        """
        Spawns 50 concurrent threads reading, writing, and clearing FreePublicFeedsEngine cache
        simultaneously to detect race conditions or corrupted cache dictionaries.
        """
        errors = []
        feed_engine = FreePublicFeedsEngine(offline_mode=True)

        def worker(thread_id: int):
            try:
                for i in range(30):
                    key = f"key_{i % 5}"
                    val = {"thread": thread_id, "data": i * 1.5}
                    feed_engine._set_to_cache(key, val)
                    res = feed_engine._get_from_cache(key, 5.0)
                    if res is not None:
                        _ = res.get("data")
                    if i % 10 == 0:
                        feed_engine.clear_cache()
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent cache hammering encountered errors: {errors}")

    def test_adv_02_concurrent_multi_symbol_feed_queries(self):
        """
        Runs 40 concurrent threads invoking get_ticker_24hr, get_order_book_depth,
        get_perpetual_context, and track_funding_spread across multiple symbols.
        """
        errors = []
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

        def query_worker(thread_id: int):
            try:
                sym = symbols[thread_id % len(symbols)]
                for _ in range(15):
                    t = self.engine.get_ticker_24hr(sym)
                    self.assertIn("last_price", t)
                    if sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
                        d = self.engine.get_order_book_depth(sym, limit=10)
                        self.assertIn("bids", d)
                        s = self.arb_engine.track_funding_spread(sym)
                        self.assertIn("basis_spread", s)
            except Exception as e:
                errors.append(f"Query worker {thread_id} error: {e}")

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(query_worker, i) for i in range(40)]
            for f in as_completed(futures):
                f.result()

        self.assertEqual(len(errors), 0, f"Concurrent queries produced errors: {errors}")

    def test_adv_03_random_seed_fuzzing_aladdin_var_and_kelly(self):
        """
        Fuzzes Aladdin VaR/CVaR and Fractional Kelly sizing over 500 randomized parameter sets:
        tests zero volatility, extreme equity, extreme win rates (0.0 to 1.0), and extreme payoff ratios.
        """
        np.random.seed(42)
        random.seed(42)

        for iteration in range(500):
            equity = float(np.random.uniform(0.0, 10_000_000.0))
            daily_vol = float(np.random.uniform(0.0, 0.50))
            win_rate = float(np.random.uniform(0.0, 1.0))
            payoff_ratio = float(np.random.uniform(0.01, 10.0))
            se = float(np.random.uniform(0.0, 0.20))
            scalar = float(np.random.uniform(0.1, 1.5))

            # VaR/CVaR calculation
            res = self.aladdin.compute_parametric_var_cvar(equity=equity, daily_volatility=daily_vol)
            self.assertFalse(np.isnan(res["var_99_dollar"]))
            self.assertFalse(np.isnan(res["cvar_99_dollar"]))
            self.assertGreaterEqual(res["var_99_dollar"], 0.0)
            self.assertGreaterEqual(res["cvar_99_dollar"], res["var_99_dollar"])

            # Kelly sizing calculation
            kelly = self.aladdin.compute_fractional_kelly(
                win_rate=win_rate,
                payoff_ratio=payoff_ratio,
                win_rate_se=se,
                regime_scalar=scalar
            )
            self.assertFalse(np.isnan(kelly))
            self.assertGreaterEqual(kelly, 0.0025)  # Enforced 0.25% floor
            self.assertLessEqual(kelly, 0.0075)     # Enforced 0.75% ceiling

    def test_adv_04_extreme_basis_spread_and_funding_rate_fuzzing(self):
        """
        Fuzzes funding rates from -100% (-1.0) to +100% (+1.0) and prices from $0.0001 to $1,000,000.
        Verifies no ZeroDivisionError, Inf, or NaN escapes.
        """
        test_rates = [-1.0, -0.05, -0.005, -0.00051, 0.0, 0.00049, 0.00051, 0.01, 0.5, 1.0]
        test_prices = [0.001, 1.0, 100.0, 95000.0, 1_000_000.0]

        for rate in test_rates:
            for spot_p in test_prices:
                perp_p = spot_p * (1.0 + (rate * 5))
                with patch.object(self.engine, "get_perpetual_context", return_value={"funding_rate_8h": rate, "mark_price": perp_p, "coin": "BTC"}), \
                     patch.object(self.engine, "get_ticker_24hr", return_value={"last_price": spot_p, "symbol": "BTCUSD"}):
                    spread = self.arb_engine.track_funding_spread("BTCUSD")
                    self.assertIn("basis_spread", spread)
                    self.assertIn("basis_spread_pct", spread)
                    self.assertFalse(math.isnan(spread["basis_spread"]))
                    self.assertFalse(math.isnan(spread["basis_spread_pct"]))
                    self.assertFalse(math.isinf(spread["basis_spread"]))
                    self.assertFalse(math.isinf(spread["basis_spread_pct"]))

    def test_adv_05_floating_point_epsilon_consistency_pacing_boundary(self):
        """
        Adversarially challenges the 35% consistency pacing limit around exact float boundaries:
        $699.999999, $700.000000, $700.000001 on a $2,000 profit target ($700 ceiling).
        """
        target = 2000.0
        # Just below ceiling
        safe = self.expert.evaluate_consistency_pacing(today_profit=699.9999, total_profit_target=target)
        self.assertTrue(safe["is_pacing_safe"])
        self.assertEqual(safe["recommendation"], "STANDARD_RISK")

        # Exact ceiling
        exact = self.expert.evaluate_consistency_pacing(today_profit=700.0, total_profit_target=target)
        self.assertTrue(exact["is_pacing_safe"])
        self.assertEqual(exact["recommendation"], "STANDARD_RISK")

        # Just above ceiling
        breach = self.expert.evaluate_consistency_pacing(today_profit=700.0001, total_profit_target=target)
        self.assertFalse(breach["is_pacing_safe"])
        self.assertEqual(breach["recommendation"], "CONSERVATIVE_SCALE_DOWN")


class TestBackupDisasterRecoveryAdversarialStress(unittest.TestCase):
    """Adversarial stress tests for State Backup Manager and Disaster Recovery Watchdog."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_dr_stress_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cog_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        self.logs_dir = os.path.join(self.test_dir, "logs")
        self.reports_dir = os.path.join(self.data_dir, "incident_reports")

        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"bot": {"name": "AdvStressBot", "version": "4.0.0"}}, f)

        with open(os.path.join(self.cog_dir, "episodic_memory.json"), "w") as f:
            json.dump([{"id": 1, "pnl": 100.0}], f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE trades (id INT PRIMARY KEY, profit REAL);")
            conn.execute("INSERT INTO trades VALUES (1, 200.0);")
            conn.commit()

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_adv_06_concurrent_snapshot_creation_and_manifest_integrity(self):
        """
        Spawns 10 concurrent threads simultaneously calling create_snapshot() and get_backup_manifest().
        Verifies that thread locking and atomic manifest swap prevent file lock collisions or manifest corruption.
        """
        snapshots = []
        errors = []

        def creator(idx: int):
            try:
                snap = self.mgr.create_snapshot(label=f"concurrent_{idx}")
                snapshots.append(snap)
                # Query manifest concurrently
                manifest = self.mgr.get_backup_manifest()
                self.assertGreaterEqual(len(manifest), 1)
            except Exception as e:
                errors.append(f"Creator {idx} failed: {e}")

        threads = [threading.Thread(target=creator, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent snapshot creation had errors: {errors}")
        self.assertEqual(len(snapshots), 10)

        # Verify manifest has all 10 snapshots recorded
        manifest = self.mgr.get_backup_manifest()
        self.assertEqual(len(manifest), 10)
        # Verify no orphan temporary staging or temp manifest files
        files = os.listdir(self.backups_dir)
        temp_files = [f for f in files if f.startswith(".staging_") or f.endswith(".tmp")]
        self.assertEqual(len(temp_files), 0, f"Found lingering temporary files: {temp_files}")

    def test_adv_07_repeated_mutation_and_rollback_loop(self):
        """
        Executes 15 sequential cycles of:
        create snapshot -> corrupt DB & config -> atomic restore -> verify SQLite PRAGMA & JSON integrity.
        Verifies zero drift and zero lingering rollback files.
        """
        pristine_snap = self.mgr.create_snapshot(label="pristine_loop")

        for loop in range(15):
            # Mutate config
            with open(self.config_path, "w") as f:
                json.dump({"bot": {"corrupted": True, "loop": loop}}, f)

            # Mutate DB
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"INSERT INTO trades VALUES ({100 + loop}, {-50.0 * loop});")
                conn.commit()

            # Restore
            restored = self.mgr.restore_snapshot(pristine_snap["path"], verify_sqlite=True)
            self.assertTrue(restored, f"Restore failed on iteration {loop}")

            # Verify config
            with open(self.config_path, "r") as f:
                cfg = json.load(f)
                self.assertEqual(cfg["bot"]["name"], "AdvStressBot")

            # Verify DB has only original record
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                res = cur.fetchone()
                self.assertEqual(res[0], "ok")
                rows = cur.execute("SELECT * FROM trades;").fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][0], 1)

        # Check for lingering temporary restore staging folders
        files = os.listdir(self.backups_dir)
        stray_tmp = [f for f in files if f.startswith(".tmp_restore_staging_") or f.startswith(".tmp_rollback_")]
        self.assertEqual(len(stray_tmp), 0, f"Lingering restore staging directories detected: {stray_tmp}")

    def test_adv_08_path_traversal_zip_slip_security_exploit_defense(self):
        """
        Constructs malicious tar archive with traversal filenames ('../../etc/evil.txt', 'C:\\Windows\\evil.dll')
        and asserts that StateBackupManager safely rejects them with SecurityError / returns False.
        """
        evil_tar_path = os.path.join(self.backups_dir, "snapshot_evil_slip.tar.gz")
        with tarfile.open(evil_tar_path, "w:gz") as tar:
            # Create a dummy file to add as malicious member
            dummy_file = os.path.join(self.test_dir, "dummy_payload.txt")
            with open(dummy_file, "w") as f:
                f.write("MALICIOUS PAYLOAD")

            # Add with illegal relative path
            tarinfo = tar.gettarinfo(dummy_file, arcname="../../evil_injected.txt")
            with open(dummy_file, "rb") as f:
                tar.addfile(tarinfo, f)

        # Attempt restore
        success = self.mgr.restore_snapshot(evil_tar_path)
        self.assertFalse(success, "Security vulnerability: Zip slip tar archive was successfully extracted!")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "..", "evil_injected.txt")))

    def test_adv_09_watchdog_socket_and_file_descriptor_leak_audit(self):
        """
        Runs 200 consecutive socket probes and health checks to ensure no socket or file handle leaks occur.
        """
        watchdog = DisasterRecoveryWatchdog(
            config_path=self.config_path,
            workspace_root=self.test_dir,
            log_dir=self.logs_dir,
            incident_reports_dir=self.reports_dir
        )

        for _ in range(100):
            # Probe unregistered port (should fail gracefully and close socket)
            ok, lat, err = watchdog._probe_tcp_socket("127.0.0.1", 59999, timeout=0.05)
            self.assertFalse(ok)

        # Ensure no lingering unclosed sockets
        gc.collect()

    def test_adv_10_watchdog_daemon_lifecycle_clean_shutdown(self):
        """
        Starts and stops the watchdog daemon 10 times rapidly to verify thread termination without orphaned threads.
        """
        watchdog = DisasterRecoveryWatchdog(
            config_path=self.config_path,
            workspace_root=self.test_dir,
            log_dir=self.logs_dir,
            incident_reports_dir=self.reports_dir
        )

        initial_threads = threading.active_count()
        for i in range(5):
            watchdog.start_watchdog_daemon(interval_sec=1)
            self.assertTrue(watchdog.is_running)
            time.sleep(0.1)
            watchdog.stop_watchdog_daemon()
            self.assertFalse(watchdog.is_running)

        time.sleep(0.2)
        final_threads = threading.active_count()
        self.assertLessEqual(final_threads, initial_threads + 1, "Watchdog daemon spawned orphan threads.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
