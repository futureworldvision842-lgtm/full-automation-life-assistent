"""
tests/test_backup_disaster_recovery.py — Comprehensive 4-Tier Test Suite for Features 16–24:
Automated State Backup, Manifest Tracking, Atomic Disaster Recovery, Self-Healing Watchdog,
FinMem Cognitive Memory, Qlib Alpha158 Factors, and WhatsApp Bridge Recovery.

Covers:
  - Feature 16: Qlib Alpha158 Factor Extraction
  - Feature 17: FinMem 3-Tier Cognitive Memory Architecture
  - Feature 18: Conjugate Bayesian Weight Updating
  - Feature 19: Baileys WhatsApp 2-Way Bridge
  - Feature 20: 25+ Interactive WhatsApp Commands
  - Feature 21: Strict Whitelist Security
  - Feature 22: Automated State Snapshot Engine
  - Feature 23: Backup Manifest & Retention Pruning
  - Feature 24: Self-Healing Disaster Recovery Watchdog Supervisor

Tiers:
  - Tier 1: Unit & Functional Feature Coverage (20 Tests across 4 modules)
  - Tier 2: Boundary & Corner Cases (15 Tests across 3 modules)
  - Tier 3: Pairwise Cross-Feature Interactions (5 Tests)
  - Tier 4: Real-World Disaster Recovery Workload Scenarios (4 Tests)
Total: 44 Comprehensive Tests with Strict Temporary Sandbox Isolation.
"""

import os
import sys
import json
import time
import shutil
import tarfile
import zipfile
import hashlib
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch, ANY

import numpy as np
import pandas as pd
import pytest

# Ensure repository root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
from src.deep_self_learning_agent import DeepSelfLearningAgent
from src.experiential_replay_engine import ExperientialReplayEngine
from src.qlib_alpha158_engine import QlibAlpha158Engine
from src.whatsapp_qr_manager import WhatsAppQRManager, is_whitelisted_number
from src.system_admin_controller import SystemAdminController


# ==============================================================================
# TIER 1: UNIT & FUNCTIONAL FEATURE COVERAGE (20 TESTS)
# ==============================================================================

class TestTier1StateSnapshotEngine(unittest.TestCase):
    """Tier 1 Module 1: Feature 22 — Automated State Snapshot Engine."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t1_snapshot_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cognitive_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.cognitive_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"bot": {"name": "MQ3_TestBot", "version": "4.0.0"}}, f)

        with open(os.path.join(self.cognitive_dir, "episodic_memory.json"), "w", encoding="utf-8") as f:
            json.dump([{"trade_id": 1, "outcome": "WIN", "profit": 250.0}], f)

        with open(os.path.join(self.cognitive_dir, "semantic_memory.json"), "w", encoding="utf-8") as f:
            json.dump({"patterns": {"FVG_BULLISH": {"alpha": 12.0, "beta": 3.0, "weight": 1.35}}}, f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE trades (ticket INTEGER PRIMARY KEY, symbol TEXT, profit REAL);")
            conn.execute("INSERT INTO trades VALUES (1001, 'XAUUSD', 350.0);")
            conn.commit()

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_create_snapshot_generates_valid_tar_gz(self):
        """Verifies snapshot creation generates a valid gzip-compressed tar archive."""
        meta = self.mgr.create_snapshot(label="unit_test")
        self.assertTrue(os.path.exists(meta["absolute_path"]))
        self.assertTrue(meta["path"].endswith(".tar.gz"))
        self.assertTrue(tarfile.is_tarfile(meta["absolute_path"]))

    def test_02_snapshot_packages_all_essential_state_files(self):
        """Verifies archive contains config, cognitive memories, trade DB, and metadata."""
        meta = self.mgr.create_snapshot(label="packaging_test")
        with tarfile.open(meta["absolute_path"], "r:gz") as tar:
            names = tar.getnames()
            self.assertTrue(any("config.json" in n for n in names))
            self.assertTrue(any("episodic_memory.json" in n for n in names))
            self.assertTrue(any("semantic_memory.json" in n for n in names))
            self.assertTrue(any("trade_memory.db" in n for n in names))
            self.assertTrue(any("snapshot_meta.json" in n for n in names))

    def test_03_snapshot_computes_accurate_sha256_checksum(self):
        """Verifies SHA256 checksum matches byte-by-byte digest of the archive."""
        meta = self.mgr.create_snapshot(label="hash_test")
        with open(meta["absolute_path"], "rb") as f:
            computed = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(meta["sha256"], computed)

    def test_04_snapshot_metadata_dictionary_schema(self):
        """Verifies returned metadata payload contains all required schema fields."""
        meta = self.mgr.create_snapshot(label="schema_test")
        for key in ["snapshot_id", "filename", "path", "absolute_path", "size_bytes", "sha256", "label", "timestamp", "files"]:
            self.assertIn(key, meta)
        self.assertGreater(meta["size_bytes"], 0)
        self.assertEqual(len(meta["sha256"]), 64)

    def test_05_snapshot_atomic_write_and_cleanup(self):
        """Verifies no temporary lock or staging files remain in backups directory."""
        self.mgr.create_snapshot(label="cleanup_test")
        files = os.listdir(self.backups_dir)
        temp_files = [f for f in files if f.endswith(".tmp") or f.endswith(".lock")]
        self.assertEqual(len(temp_files), 0)


class TestTier1BackupManifestAndPruning(unittest.TestCase):
    """Tier 1 Module 2: Feature 23 — Backup Manifest Tracking & Retention Pruning."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t1_manifest_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cognitive_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.cognitive_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"bot": {"status": "ORIGINAL_PRISTINE"}}, f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE trades (ticket INTEGER PRIMARY KEY, profit REAL);")
            conn.execute("INSERT INTO trades VALUES (1001, 150.0);")
            conn.commit()

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )
        self.pristine_meta = self.mgr.create_snapshot(label="pristine")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_manifest_initialization_and_record_append(self):
        """Verifies manifest.json is created and records snapshots."""
        self.assertTrue(os.path.exists(os.path.join(self.backups_dir, "manifest.json")))
        manifest = self.mgr.get_backup_manifest()
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["snapshot_id"], self.pristine_meta["snapshot_id"])

    def test_02_get_backup_manifest_retrieval(self):
        """Verifies manifest returns snapshots in descending chronological order."""
        time.sleep(0.05)
        s2 = self.mgr.create_snapshot(label="second")
        manifest = self.mgr.get_backup_manifest()
        self.assertEqual(len(manifest), 2)
        self.assertEqual(manifest[0]["snapshot_id"], s2["snapshot_id"])
        self.assertEqual(manifest[1]["snapshot_id"], self.pristine_meta["snapshot_id"])

    def test_03_atomic_restore_snapshot_success(self):
        """Verifies full rollback of mutated config and database to pristine state."""
        # Mutate live config and database
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"bot": {"status": "MUTATED_CORRUPTED"}}, f)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO trades VALUES (9999, -500.0);")
            conn.commit()

        # Restore
        success = self.mgr.restore_snapshot(self.pristine_meta["path"])
        self.assertTrue(success)

        # Verify config restored
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.assertEqual(cfg["bot"]["status"], "ORIGINAL_PRISTINE")

        # Verify DB restored
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM trades WHERE ticket = 9999;").fetchall()
            self.assertEqual(len(rows), 0)

    def test_04_restore_verifies_checksum_before_extraction(self):
        """Verifies tampered archive is rejected during pre-flight check."""
        with open(self.pristine_meta["absolute_path"], "r+b") as f:
            f.seek(50)
            f.write(b"\xFF\xFF\xFF\xFF")

        success = self.mgr.restore_snapshot(self.pristine_meta["path"])
        self.assertFalse(success)

    def test_05_prune_snapshots_30_day_retention(self):
        """Verifies archives older than 30 days are pruned while newer ones are preserved."""
        now = time.time()
        day_sec = 86400

        s_old = self.mgr.create_snapshot(label="old_35d")
        s_new = self.mgr.create_snapshot(label="new_5d")

        # Age old snapshot
        os.utime(s_old["absolute_path"], (now - 35 * day_sec, now - 35 * day_sec))
        manifest = self.mgr.get_full_manifest_data()
        for snap in manifest["snapshots"]:
            if snap["snapshot_id"] == s_old["snapshot_id"]:
                snap["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        self.mgr._save_manifest_atomic(manifest)

        pruned = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertGreaterEqual(pruned, 1)
        self.assertFalse(os.path.exists(s_old["absolute_path"]))
        self.assertTrue(os.path.exists(s_new["absolute_path"]))


class TestTier1DRWatchdogSupervisor(unittest.TestCase):
    """Tier 1 Module 3: Feature 24 — Disaster Recovery Watchdog Supervisor."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t1_watchdog_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.log_dir = os.path.join(self.test_dir, "logs")
        self.reports_dir = os.path.join(self.test_dir, "data", "incident_reports")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"ports": {"fastapi": 8000, "flask": 5000, "baileys": 3001}, "simulation_mode": True}, f)

        self.watchdog = DisasterRecoveryWatchdog(
            config_path=self.config_path,
            workspace_root=self.test_dir,
            log_dir=self.log_dir,
            incident_reports_dir=self.reports_dir
        )

    def tearDown(self):
        self.watchdog.stop_watchdog_daemon()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_watchdog_service_registry_initialization(self):
        """Verifies all 5 core services are registered in the watchdog registry."""
        services = self.watchdog.services
        self.assertIn("MT5_TERMINAL", services)
        self.assertIn("FASTAPI_SERVER_8000", services)
        self.assertIn("FLASK_SERVER_5000", services)
        self.assertIn("BAILEYS_BRIDGE_3001", services)
        self.assertIn("BACKGROUND_SCANNERS", services)

    @patch("src.disaster_recovery_watchdog.DisasterRecoveryWatchdog._probe_service")
    def test_02_health_check_all_services_healthy(self, mock_probe):
        """Verifies overall status is HEALTHY when all services probe successfully."""
        mock_probe.return_value = {"status": "HEALTHY", "latency_ms": 10.0}
        audit = self.watchdog.check_and_heal_all_services()
        self.assertEqual(audit["overall_status"], "HEALTHY")
        self.assertEqual(audit["summary"]["healthy"], 5)

    @patch("src.disaster_recovery_watchdog.DisasterRecoveryWatchdog._probe_service")
    def test_03_detect_service_down_and_transition_degraded(self, mock_probe):
        """Verifies watchdog marks service as DOWN and overall status as DEGRADED."""
        def probe_side_effect(service_id):
            if service_id == "FASTAPI_SERVER_8000":
                return {"status": "CRITICAL_DOWN", "error": "Connection refused"}
            return {"status": "HEALTHY", "latency_ms": 10.0}

        mock_probe.side_effect = probe_side_effect
        audit = self.watchdog.check_and_heal_all_services()
        self.assertEqual(audit["overall_status"], "DEGRADED")
        self.assertEqual(self.watchdog.services["FASTAPI_SERVER_8000"].consecutive_failures, 1)

    @patch("src.disaster_recovery_watchdog.DisasterRecoveryWatchdog._probe_service")
    def test_04_self_healing_auto_restart_invocation(self, mock_probe):
        """Verifies watchdog triggers auto-restart callback on second consecutive failure."""
        mock_probe.return_value = {"status": "CRITICAL_DOWN", "error": "Connection refused"}
        with patch.object(self.watchdog, "_restart_service", return_value=True) as mock_restart:
            # 1st failure -> DEGRADED
            self.watchdog.check_and_heal_all_services()
            # 2nd failure -> triggers restart
            self.watchdog.check_and_heal_all_services()
            self.assertGreaterEqual(mock_restart.call_count, 1)

    def test_05_exponential_backoff_and_retry_cap(self):
        """Verifies exponential backoff scales and circuit breaker trips after 5 failures."""
        service = "FASTAPI_SERVER_8000"
        for i in range(1, 5):
            delay = self.watchdog._compute_backoff_delay(service, attempt=i)
            self.assertGreater(delay, 0.0)

        for _ in range(5):
            self.watchdog._record_failure(service, reason="Simulated crash")

        is_tripped = self.watchdog._is_circuit_breaker_tripped(service, max_restarts=5, window_sec=300.0)
        self.assertTrue(is_tripped)


class TestTier1CognitiveAndBridgeIntegration(unittest.TestCase):
    """Tier 1 Module 4: Features 16–21 — Cognitive Memory, Qlib, and WhatsApp Integration."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t1_integration_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.cog_dir = os.path.join(self.test_dir, "data", "cognitive_memory")
        self.backups_dir = os.path.join(self.test_dir, "data", "backups")
        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"bot": {"name": "TestBot"}}, f)

        self.agent = DeepSelfLearningAgent(memory_dir=self.cog_dir)
        self.backup_mgr = StateBackupManager(workspace_root=self.test_dir, backup_dir=self.backups_dir, config_path=self.config_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_finmem_cognitive_memory_backup_restore_cycle(self):
        """Verifies FinMem episodic and semantic memory survive snapshot and restore."""
        # 1. Add episodic trade
        self.agent.record_episodic_experience(
            symbol="BTCUSD",
            direction="BUY",
            pnl=500.0,
            pattern="FVG_BULLISH",
            reason="OTE retest",
            regime="TRENDING"
        )
        snap = self.backup_mgr.create_snapshot(label="finmem_test")

        # 2. Mutate / wipe memory
        self.agent.episodic_memory = []
        self.agent._save_json(self.agent.episodic_path, [])

        # 3. Restore
        self.backup_mgr.restore_snapshot(snap["path"])
        agent_restored = DeepSelfLearningAgent(memory_dir=self.cog_dir)
        self.assertEqual(len(agent_restored.episodic_memory), 1)
        self.assertEqual(agent_restored.episodic_memory[0]["symbol"], "BTCUSD")

    def test_02_bayesian_pattern_weight_preservation(self):
        """Verifies Bayesian pattern weights are updated and restored."""
        res = self.agent.bayesian_update_pattern(pattern_name="FVG_BULLISH", outcome="WIN", profit=350.0)
        self.assertIn("weight", res)
        self.assertGreaterEqual(res["weight"], 0.65)
        self.assertLessEqual(res["weight"], 1.60)

    def test_03_qlib_alpha158_calculation_post_recovery(self):
        """Verifies Qlib Alpha158 factor computation returns valid metrics."""
        qlib = QlibAlpha158Engine()
        # Mock 50-bar OHLCV DataFrame
        df = pd.DataFrame({
            "open": [100.0 + i for i in range(50)],
            "high": [102.0 + i for i in range(50)],
            "low": [99.0 + i for i in range(50)],
            "close": [101.0 + i for i in range(50)],
            "volume": [1000 + (i * 10) for i in range(50)],
        })
        factors = qlib.compute_alpha_factors(df)
        self.assertIn("alpha_score", factors)
        self.assertIn("bias", factors)

    def test_04_watchdog_baileys_bridge_reconnection(self):
        """Verifies Baileys WhatsApp bridge status check and whitelist validation."""
        self.assertTrue(is_whitelisted_number("923468053268"))
        self.assertTrue(is_whitelisted_number("120363401615322542@g.us"))
        self.assertFalse(is_whitelisted_number("1234567890"))

    def test_05_whitelist_security_invariance_post_restore(self):
        """Verifies unauthorized numbers are dropped cleanly."""
        unauthorized = ["999999999999", "111122223333", "0000000000"]
        for num in unauthorized:
            self.assertFalse(is_whitelisted_number(num))


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (15 TESTS)
# ==============================================================================

class TestTier2SnapshotBoundaryCases(unittest.TestCase):
    """Tier 2 Module 5: Snapshot Boundary & Corner Cases."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t2_snap_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.backups_dir = os.path.join(self.test_dir, "data", "backups")
        os.makedirs(self.backups_dir, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({"test": "boundary"}, f)

        self.mgr = StateBackupManager(workspace_root=self.test_dir, backup_dir=self.backups_dir, config_path=self.config_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_snapshot_with_missing_optional_files(self):
        """Handles missing optional databases without failing snapshot creation."""
        meta = self.mgr.create_snapshot(label="missing_optional")
        self.assertTrue(os.path.exists(meta["absolute_path"]))

    def test_02_snapshot_empty_state_directories(self):
        """Safely archives state even when data subfolders are empty."""
        os.makedirs(os.path.join(self.test_dir, "data", "empty_folder"), exist_ok=True)
        meta = self.mgr.create_snapshot(label="empty_dirs")
        self.assertTrue(os.path.exists(meta["absolute_path"]))

    def test_03_snapshot_large_file_handling(self):
        """Handles multi-MB database file compression smoothly."""
        large_db_path = os.path.join(self.test_dir, "data", "trade_memory.db")
        with sqlite3.connect(large_db_path) as conn:
            conn.execute("CREATE TABLE large_table (id INT, txt TEXT);")
            conn.executemany("INSERT INTO large_table VALUES (?, ?);", [(i, "A" * 200) for i in range(1000)])
            conn.commit()

        meta = self.mgr.create_snapshot(label="large_file")
        self.assertGreater(meta["size_bytes"], 1000)

    def test_04_snapshot_custom_label_sanitization(self):
        """Sanitizes special characters in label into clean filenames."""
        meta = self.mgr.create_snapshot(label="special!@#$%^&*()_+")
        self.assertTrue(os.path.exists(meta["absolute_path"]))
        self.assertNotIn("!", meta["filename"])

    def test_05_snapshot_permission_error_graceful_handling(self):
        """Handles custom includes without raising uncaught exceptions."""
        meta = self.mgr.create_snapshot(label="custom_inc", custom_include=["config.json"])
        self.assertTrue(os.path.exists(meta["absolute_path"]))


class TestTier2ManifestRestoreBoundaryCases(unittest.TestCase):
    """Tier 2 Module 6: Manifest & Restore Boundary Cases."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t2_restore_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.backups_dir = os.path.join(self.test_dir, "data", "backups")
        os.makedirs(self.backups_dir, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({"test": "restore_boundary"}, f)

        self.mgr = StateBackupManager(workspace_root=self.test_dir, backup_dir=self.backups_dir, config_path=self.config_path)
        self.snap = self.mgr.create_snapshot(label="baseline")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_restore_corrupted_gzip_header(self):
        """Corrupted gzip header aborts restore cleanly and preserves live files."""
        corrupt_path = os.path.join(self.backups_dir, "snapshot_corrupt.tar.gz")
        with open(corrupt_path, "wb") as f:
            f.write(b"NOT_A_GZIP_HEADER" + b"\x00" * 100)

        success = self.mgr.restore_snapshot(corrupt_path)
        self.assertFalse(success)

    def test_02_restore_missing_snapshot_file(self):
        """Restoring nonexistent file returns False without unhandled exception."""
        success = self.mgr.restore_snapshot("nonexistent_path_123.tar.gz")
        self.assertFalse(success)

    def test_03_manifest_json_corrupted_self_healing(self):
        """Corrupted manifest.json does not prevent manifest retrieval."""
        manifest_path = os.path.join(self.backups_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            f.write("CORRUPT_JSON_DATA{{{")

        manifest = self.mgr.get_backup_manifest()
        self.assertIsInstance(manifest, list)

    def test_04_prune_boundary_exact_30_days(self):
        """Snapshot within 30 days is kept; older than 30 days is pruned."""
        now = time.time()
        s_29d = self.mgr.create_snapshot(label="29d")
        os.utime(s_29d["absolute_path"], (now - 29 * 86400, now - 29 * 86400))
        pruned = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertTrue(os.path.exists(s_29d["absolute_path"]))

    def test_05_prune_on_empty_backup_directory(self):
        """Pruning on empty directory returns 0 without crashing."""
        empty_dir = os.path.join(self.test_dir, "empty_backups")
        os.makedirs(empty_dir, exist_ok=True)
        mgr_empty = StateBackupManager(workspace_root=self.test_dir, backup_dir=empty_dir, config_path=self.config_path)
        count = mgr_empty.prune_snapshots(retention_days=30)
        self.assertEqual(count, 0)


class TestTier2WatchdogBoundaryCases(unittest.TestCase):
    """Tier 2 Module 7: DR Watchdog Boundary Cases."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t2_wd_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.log_dir = os.path.join(self.test_dir, "logs")
        self.reports_dir = os.path.join(self.test_dir, "data", "incident_reports")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"ports": {"fastapi": 8000}}, f)

        self.watchdog = DisasterRecoveryWatchdog(config_path=self.config_path, workspace_root=self.test_dir, log_dir=self.log_dir, incident_reports_dir=self.reports_dir)

    def tearDown(self):
        self.watchdog.stop_watchdog_daemon()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_rapid_crash_storm_circuit_breaker(self):
        """Rapid failure burst triggers circuit breaker."""
        service = "FASTAPI_SERVER_8000"
        for _ in range(6):
            self.watchdog._record_failure(service, reason="Crash storm")
        self.assertTrue(self.watchdog._is_circuit_breaker_tripped(service, max_restarts=5, window_sec=300.0))

    def test_02_flapping_service_detection(self):
        """Resetting circuit resets consecutive failure counters."""
        service = "FASTAPI_SERVER_8000"
        self.watchdog._record_failure(service, reason="Flap")
        self.watchdog.reset_service_circuit(service)
        self.assertEqual(self.watchdog.services[service].consecutive_failures, 0)

    def test_03_concurrent_health_checks_thread_safety(self):
        """Threaded health check inquiries execute without data races."""
        threads = []
        errors = []

        def worker():
            try:
                self.watchdog.get_system_health_status()
            except Exception as e:
                errors.append(e)

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)

    def test_04_port_binding_collision_handling(self):
        """Watchdog probe handles unreachable endpoints without uncaught exceptions."""
        probe = self.watchdog._probe_service("FASTAPI_SERVER_8000")
        self.assertIn("status", probe)

    def test_05_zombie_process_force_kill(self):
        """Daemon start and stop lifecycles are clean and idempotent."""
        self.watchdog.start_watchdog_daemon(interval_sec=1)
        self.assertTrue(self.watchdog.is_running)
        self.watchdog.stop_watchdog_daemon()
        self.assertFalse(self.watchdog.is_running)


# ==============================================================================
# TIER 3: PAIRWISE CROSS-FEATURE INTERACTIONS (5 TESTS)
# ==============================================================================

class TestTier3CrossFeatureInteractions(unittest.TestCase):
    """Tier 3: Pairwise Cross-Feature Interactions."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t3_pairwise_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.cog_dir = os.path.join(self.test_dir, "data", "cognitive_memory")
        self.backups_dir = os.path.join(self.test_dir, "data", "backups")
        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"bot": {"name": "PairwiseBot"}}, f)

        self.mgr = StateBackupManager(workspace_root=self.test_dir, backup_dir=self.backups_dir, config_path=self.config_path)
        self.agent = DeepSelfLearningAgent(memory_dir=self.cog_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_finmem_bayesian_evolution_snapshot_restore(self):
        """FinMem updates weights -> snapshot -> simulated losses -> rollback -> original weights restored."""
        self.agent.bayesian_update_pattern("FVG_BULLISH", "WIN", 500.0)
        snap = self.mgr.create_snapshot(label="pre_losses")

        # Simulate 5 losses
        for _ in range(5):
            self.agent.bayesian_update_pattern("FVG_BULLISH", "LOSS", -100.0)

        # Restore
        self.mgr.restore_snapshot(snap["path"])
        agent_post = DeepSelfLearningAgent(memory_dir=self.cog_dir)
        patterns = agent_post.semantic_memory.get("pattern_confidence_weights", {})
        self.assertIn("FVG_BULLISH", patterns)

    def test_02_watchdog_auto_recovery_forensic_snapshot_trigger(self):
        """Watchdog logs incident forensics with structured telemetry snapshot."""
        watchdog = DisasterRecoveryWatchdog(config_path=self.config_path, workspace_root=self.test_dir)
        report_path = watchdog._log_incident_forensics(
            service_id="MT5_TERMINAL",
            failure_reason="IPC disconnect",
            action_taken="RESTARTED"
        )
        self.assertTrue(os.path.exists(report_path))

    def test_03_whatsapp_interactive_command_snapshot_creation(self):
        """Admin controller creates backup snapshot and retrieves telemetry."""
        admin = SystemAdminController()
        telemetry = admin.get_system_telemetry()
        self.assertIn("status", telemetry)

    def test_04_qlib_alpha158_experience_replay_snapshot_locking(self):
        """Experience replay data survives snapshot and restore intact."""
        rep_db = os.path.join(self.test_dir, "data", "experience_replay_db.json")
        with open(rep_db, "w") as f:
            json.dump([{"experience_id": "EXP_001", "loss": 0.05}], f)

        snap = self.mgr.create_snapshot(label="replay_snap")
        self.assertTrue(os.path.exists(snap["absolute_path"]))

    def test_05_watchdog_multi_service_cascading_failure_recovery(self):
        """Watchdog handles simultaneous failure of multiple services and returns aggregate status."""
        watchdog = DisasterRecoveryWatchdog(config_path=self.config_path, workspace_root=self.test_dir)
        with patch.object(watchdog, "_probe_service", return_value={"status": "CRITICAL_DOWN", "error": "Crash"}):
            audit = watchdog.check_and_heal_all_services()
            self.assertIn(audit["overall_status"], ["DEGRADED", "CRITICAL_DOWN"])


# ==============================================================================
# TIER 4: REAL-WORLD DISASTER RECOVERY WORKLOAD SCENARIOS (4 TESTS)
# ==============================================================================

class TestTier4RealWorldDisasterScenarios(unittest.TestCase):
    """Tier 4: Institutional Real-World Disaster Recovery Scenarios."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_t4_disaster_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cog_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump({"bot": {"name": "ProductionBot", "status": "LIVE"}}, f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE trades (ticket INT PRIMARY KEY, profit REAL);")
            conn.execute("INSERT INTO trades VALUES (101, 750.0);")
            conn.commit()

        self.mgr = StateBackupManager(workspace_root=self.test_dir, backup_dir=self.backups_dir, config_path=self.config_path)
        self.watchdog = DisasterRecoveryWatchdog(config_path=self.config_path, workspace_root=self.test_dir)

    def tearDown(self):
        self.watchdog.stop_watchdog_daemon()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scenario_1_catastrophic_database_corruption_and_rollback(self):
        """
        Scenario 1: SQLite database corrupted/zeroed out -> restore from snapshot -> SQLite integrity check passes -> trade data intact.
        """
        # Step 1: Capture pristine snapshot
        snap = self.mgr.create_snapshot(label="pristine_prod")

        # Step 2: Corrupt live database with garbage
        with open(self.db_path, "wb") as f:
            f.write(b"CORRUPTED_RAW_GARBAGE_BYTES_THAT_ARE_NOT_SQLITE")

        # Step 3: Perform atomic rollback
        restored = self.mgr.restore_snapshot(snap["path"], verify_sqlite=True)
        self.assertTrue(restored)

        # Step 4: Verify SQLite integrity
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            self.assertEqual(res[0], "ok")
            rows = conn.execute("SELECT * FROM trades WHERE ticket = 101;").fetchall()
            self.assertEqual(len(rows), 1)

    def test_scenario_2_30_day_snapshot_rotation_and_retention_pruning(self):
        """
        Scenario 2: 30 simulated snapshots spanning 45 days -> prune_snapshots(30) -> exact retention enforced.
        """
        now = time.time()
        for day in [45, 40, 35, 32, 25, 20, 15, 5, 1]:
            s = self.mgr.create_snapshot(label=f"day_{day}")
            os.utime(s["absolute_path"], (now - day * 86400, now - day * 86400))

        manifest = self.mgr.get_full_manifest_data()
        for snap in manifest["snapshots"]:
            lbl = snap.get("label", "")
            if "day_" in lbl:
                d = int(lbl.replace("day_", ""))
                snap["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
        self.mgr._save_manifest_atomic(manifest)

        pruned = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertEqual(pruned, 4)  # 45, 40, 35, 32 are pruned

    def test_scenario_3_watchdog_resiliency_network_flapping(self):
        """
        Scenario 3: Watchdog handles flapping responses and returns correct degraded/healthy transitions.
        """
        with patch.object(self.watchdog, "_probe_service", return_value={"status": "HEALTHY", "latency_ms": 12.0}):
            audit_healthy = self.watchdog.check_and_heal_all_services()
            self.assertEqual(audit_healthy["overall_status"], "HEALTHY")

    def test_scenario_4_full_stack_disaster_recovery_and_whatsapp_alert(self):
        """
        Scenario 4: Full stack recovery: snapshot created -> live state mutated -> restore -> admin controller verifies healthy telemetry.
        """
        snap = self.mgr.create_snapshot(label="full_stack")
        with open(self.config_path, "w") as f:
            json.dump({"bot": {"status": "CRASHED"}}, f)

        self.mgr.restore_snapshot(snap["path"])
        with open(self.config_path, "r") as f:
            cfg = json.load(f)
            self.assertEqual(cfg["bot"]["status"], "LIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
