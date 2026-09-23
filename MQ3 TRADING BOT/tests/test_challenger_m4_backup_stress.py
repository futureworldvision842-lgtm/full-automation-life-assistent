"""
tests/test_challenger_m4_backup_stress.py — Empirical Challenger 1 Adversarial Test Suite for StateBackupManager.

Author: Challenger 1 (Milestone 4)
Target: src.state_backup_manager.StateBackupManager

Adversarial Stress Scenarios Tested:
  Scenario 1: Archive Corruption
    - 1.1 Truncated .tar.gz (abrupt EOF)
    - 1.2 Corrupted .tar.gz header bytes (magic header overwritten)
    - 1.3 Bit-flipped compressed payload (data block corruption)
    - 1.4 Truncated .zip archive
    - 1.5 Corrupted .zip central directory header
    - 1.6 0-byte archive file rejection

  Scenario 2: Malicious Archive Path Traversal (Tar Slip & Zip Slip)
    - 2.1 Tar archive with relative path traversal (../../malicious_slip.txt)
    - 2.2 Zip archive with relative path traversal (../../malicious_slip.txt)
    - 2.3 Archive with absolute drive path escapes (C:/evil/pwn.txt or C:\\evil\\pwn.txt)
    - 2.4 Archive with nested internal traversal (data/cognitive_memory/../../escaped.json)

  Scenario 3: Atomic Rollback on Failure
    - 3.1 Failure during staging extraction aborts cleanly
    - 3.2 Mid-flight failure during Phase 5 live replacement (first file replaced, second file fails -> live rollback restores 1st file)
    - 3.3 Post-restore verification failure (Phase 6) triggers complete rollback
    - 3.4 Successful atomic restore verifies clean end-to-end replacement

  Scenario 4: SQLite Database Corruption in Staging
    - 4.1 Injection of non-SQLite raw garbage payload
    - 4.2 Injection of SQLite DB with corrupted internal B-Tree pages (PRAGMA integrity_check failure)
    - 4.3 Verification that live SQLite DB is never modified or locked when staged DB is corrupted

  Scenario 5: Retention Pruning Under High Load & Guardrails
    - 5.1 High load: 50 snapshot records spanning 1 to 60 days
    - 5.2 Expired snapshots (>30 days) pruned cleanly from disk and manifest
    - 5.3 Valid snapshots (<=30 days) preserved on disk and manifest
    - 5.4 min_keep=1 respected when all 50 snapshots are expired (>30 days)
    - 5.5 min_keep=5 respected when all 50 snapshots are expired
    - 5.6 Manifest integrity and counter reconciliation (total, active, pruned)
    - 5.7 Self-healing manifest rebuild when manifest.json is wiped/corrupted
"""

import os
import sys
import json
import time
import shutil
import io
import tarfile
import zipfile
import hashlib
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
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


class TestAdversarialScenario1ArchiveCorruption(unittest.TestCase):
    """Scenario 1: Archive Corruption Stress Testing."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_s1_corr_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cog_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        self.initial_config = {"system": "live_pristine", "timestamp": "2026-08-15T00:00:00Z"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.initial_config, f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE trades (id INT PRIMARY KEY, symbol TEXT, profit REAL);")
            conn.execute("INSERT INTO trades VALUES (1, 'XAUUSD', 500.0);")
            conn.commit()

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )
        self.valid_tar_meta = self.mgr.create_snapshot(label="valid_tar", format="tar.gz")
        self.valid_zip_meta = self.mgr.create_snapshot(label="valid_zip", format="zip")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _assert_live_state_intact(self):
        """Helper to verify live state was never corrupted."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.assertEqual(cfg, self.initial_config)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            res = cur.fetchone()
            self.assertEqual(res[0], "ok")
            rows = conn.execute("SELECT * FROM trades WHERE id = 1;").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], "XAUUSD")

    def test_1_1_truncated_tar_gz_rejected_cleanly(self):
        """1.1 Truncated .tar.gz archive fails safely and leaves live state intact."""
        tar_path = self.valid_tar_meta["absolute_path"]
        with open(tar_path, "rb") as f:
            full_bytes = f.read()

        corrupt_tar = os.path.join(self.backups_dir, "snapshot_truncated.tar.gz")
        # Truncate to first 30% of bytes
        with open(corrupt_tar, "wb") as f:
            f.write(full_bytes[: len(full_bytes) // 3])

        result = self.mgr.restore_snapshot(corrupt_tar)
        self.assertFalse(result, "Restore of truncated tar.gz must return False")
        self._assert_live_state_intact()

    def test_1_2_corrupted_tar_header_rejected_cleanly(self):
        """1.2 Overwritten tar header bytes trigger clean abort."""
        tar_path = self.valid_tar_meta["absolute_path"]
        with open(tar_path, "rb") as f:
            full_bytes = bytearray(f.read())

        # Overwrite beginning 64 bytes with garbage
        full_bytes[:64] = b"\xDE\xAD\xBE\xEF" * 16

        corrupt_tar = os.path.join(self.backups_dir, "snapshot_header_corrupt.tar.gz")
        with open(corrupt_tar, "wb") as f:
            f.write(full_bytes)

        result = self.mgr.restore_snapshot(corrupt_tar)
        self.assertFalse(result, "Restore of header-corrupted tar.gz must return False")
        self._assert_live_state_intact()

    def test_1_3_bit_flipped_payload_rejected_cleanly(self):
        """1.3 Bit-flipped compressed payload is detected and rejected cleanly."""
        tar_path = self.valid_tar_meta["absolute_path"]
        with open(tar_path, "rb") as f:
            full_bytes = bytearray(f.read())

        # Flip multiple bits in the middle of payload
        mid = len(full_bytes) // 2
        for offset in range(mid, min(mid + 32, len(full_bytes))):
            full_bytes[offset] ^= 0xFF

        corrupt_tar = os.path.join(self.backups_dir, "snapshot_bitflip.tar.gz")
        with open(corrupt_tar, "wb") as f:
            f.write(full_bytes)

        result = self.mgr.restore_snapshot(corrupt_tar)
        self.assertFalse(result, "Restore of bit-flipped payload must return False")
        self._assert_live_state_intact()

    def test_1_4_truncated_zip_archive_rejected_cleanly(self):
        """1.4 Truncated .zip archive fails safely and leaves live state intact."""
        zip_path = self.valid_zip_meta["absolute_path"]
        with open(zip_path, "rb") as f:
            full_bytes = f.read()

        corrupt_zip = os.path.join(self.backups_dir, "snapshot_truncated.zip")
        with open(corrupt_zip, "wb") as f:
            f.write(full_bytes[: len(full_bytes) // 2])

        result = self.mgr.restore_snapshot(corrupt_zip)
        self.assertFalse(result, "Restore of truncated zip must return False")
        self._assert_live_state_intact()

    def test_1_5_corrupted_zip_central_directory_rejected(self):
        """1.5 Corrupted zip central directory triggers safe abort."""
        zip_path = self.valid_zip_meta["absolute_path"]
        with open(zip_path, "rb") as f:
            full_bytes = bytearray(f.read())

        # Overwrite last 128 bytes (zip central dir)
        full_bytes[-128:] = b"\x00" * 128

        corrupt_zip = os.path.join(self.backups_dir, "snapshot_zip_cd_corrupt.zip")
        with open(corrupt_zip, "wb") as f:
            f.write(full_bytes)

        result = self.mgr.restore_snapshot(corrupt_zip)
        self.assertFalse(result, "Restore of corrupted zip central directory must return False")
        self._assert_live_state_intact()

    def test_1_6_zero_byte_archive_rejection(self):
        """1.6 0-byte archive file is rejected before extraction attempt."""
        empty_path = os.path.join(self.backups_dir, "snapshot_empty.tar.gz")
        with open(empty_path, "wb") as f:
            pass

        result = self.mgr.restore_snapshot(empty_path)
        self.assertFalse(result, "0-byte archive must return False")
        self._assert_live_state_intact()


class TestAdversarialScenario2PathTraversal(unittest.TestCase):
    """Scenario 2: Malicious Archive Path Traversal (Tar Slip & Zip Slip Defense)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_s2_trav_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"guard": "secure"}, f)

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )
        self.outside_canary_file = os.path.join(self.test_dir, "canary_pwned.txt")
        self.parent_canary_file = os.path.join(os.path.dirname(self.test_dir), "canary_parent.txt")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if os.path.exists(self.parent_canary_file):
            try:
                os.remove(self.parent_canary_file)
            except Exception:
                pass

    def test_2_1_tar_slip_relative_path_traversal_blocked(self):
        """2.1 Crafting a tar archive containing ../../malicious.txt is rejected."""
        malicious_tar_path = os.path.join(self.backups_dir, "snapshot_malicious_slip.tar.gz")

        # Craft malicious tar in memory
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            payload = b"PWNED_BY_PATH_TRAVERSAL"
            ti = tarfile.TarInfo(name="../../malicious_escape.txt")
            ti.size = len(payload)
            ti.mtime = int(time.time())
            tar.addfile(ti, io.BytesIO(payload))

            # Also add a valid file
            valid_payload = b'{"status": "ok"}'
            ti_valid = tarfile.TarInfo(name="config.json")
            ti_valid.size = len(valid_payload)
            ti_valid.mtime = int(time.time())
            tar.addfile(ti_valid, io.BytesIO(valid_payload))

        with open(malicious_tar_path, "wb") as f:
            f.write(tar_buf.getvalue())

        # Attempt restore
        result = self.mgr.restore_snapshot(malicious_tar_path)
        self.assertFalse(result, "Restore must return False when archive contains path traversal")

        # Verify no file was created outside staging or in test_dir parent
        self.assertFalse(os.path.exists(self.outside_canary_file))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "malicious_escape.txt")))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.test_dir), "malicious_escape.txt")))

    def test_2_2_zip_slip_relative_path_traversal_blocked(self):
        """2.2 Crafting a zip archive containing ../../malicious.txt is rejected."""
        malicious_zip_path = os.path.join(self.backups_dir, "snapshot_malicious_slip.zip")

        with zipfile.ZipFile(malicious_zip_path, "w") as zf:
            zf.writestr("../../canary_pwned.txt", "PWNED_ZIP_SLIP_ATTACK")
            zf.writestr("config.json", '{"status": "ok"}')

        result = self.mgr.restore_snapshot(malicious_zip_path)
        self.assertFalse(result, "Restore must return False when zip contains path traversal")

        self.assertFalse(os.path.exists(self.outside_canary_file))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "canary_pwned.txt")))

    def test_2_3_archive_with_absolute_path_escape_blocked(self):
        """2.3 Archive member with absolute drive path is rejected."""
        malicious_tar_path = os.path.join(self.backups_dir, "snapshot_malicious_abs.tar.gz")

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            payload = b"ABSOLUTE_PATH_ATTACK"
            # Windows drive absolute path
            ti = tarfile.TarInfo(name="C:/evil/malicious_abs_pwn.txt")
            ti.size = len(payload)
            ti.mtime = int(time.time())
            tar.addfile(ti, io.BytesIO(payload))

        with open(malicious_tar_path, "wb") as f:
            f.write(tar_buf.getvalue())

        result = self.mgr.restore_snapshot(malicious_tar_path)
        self.assertFalse(result, "Restore must reject absolute member paths")

    def test_2_4_nested_internal_traversal_blocked(self):
        """2.4 Archive member with nested .. internal traversal escaping target dir is rejected."""
        malicious_zip_path = os.path.join(self.backups_dir, "snapshot_nested_trav.zip")

        with zipfile.ZipFile(malicious_zip_path, "w") as zf:
            zf.writestr("data/cognitive_memory/../../../../escaped_secret.txt", "EXFILTRATION_TEST")

        result = self.mgr.restore_snapshot(malicious_zip_path)
        self.assertFalse(result, "Nested internal traversal escape must be rejected")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "escaped_secret.txt")))


class TestAdversarialScenario3AtomicRollback(unittest.TestCase):
    """Scenario 3: Atomic Rollback on Failure."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_s3_roll_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.cog_dir = os.path.join(self.data_dir, "cognitive_memory")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.cog_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

        self.original_config = {"version": "1.0.0", "balance": 100000.0, "state": "ORIGINAL"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.original_config, f)

        self.db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE live_orders (ticket INT PRIMARY KEY, symbol TEXT, lots REAL);")
            conn.execute("INSERT INTO live_orders VALUES (555, 'BTCUSD', 1.5);")
            conn.commit()

        self.memory_path = os.path.join(self.cog_dir, "semantic_memory.json")
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump({"patterns": {"OTE_LONG": {"weight": 1.25}}}, f)

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )
        # Snapshot 1: Represents the valid target snapshot to restore
        self.target_snap = self.mgr.create_snapshot(label="target_point")

        # Now live state mutates to a new active state (Snapshot 2 era)
        self.active_config = {"version": "2.0.0", "balance": 105000.0, "state": "ACTIVE_MUTATED"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.active_config, f)

        self.active_memory = {"patterns": {"OTE_LONG": {"weight": 1.60}, "NEW_PATTERN": {"weight": 1.10}}}
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.active_memory, f)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO live_orders VALUES (777, 'ETHUSD', 5.0);")
            conn.commit()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _assert_live_state_matches_active_mutated(self):
        """Verifies live files match the pre-restore ACTIVE_MUTATED state."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.assertEqual(cfg, self.active_config)

        with open(self.memory_path, "r", encoding="utf-8") as f:
            mem = json.load(f)
            self.assertEqual(mem, self.active_memory)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM live_orders ORDER BY ticket;").fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], 555)
            self.assertEqual(rows[1][0], 777)

    def test_3_1_exception_during_staging_aborts_without_modifying_live(self):
        """3.1 If staging extraction fails, live files remain untouched."""
        with patch.object(self.mgr, "_sanitize_and_validate_member_path", side_effect=PermissionError("Simulated Disk Lock")):
            result = self.mgr.restore_snapshot(self.target_snap["path"])
            self.assertFalse(result)
            self._assert_live_state_matches_active_mutated()

    def test_3_2_mid_flight_phase5_replacement_failure_triggers_complete_rollback(self):
        """
        3.2 Force a failure during Phase 5 replacement (e.g. while replacing the 2nd file after 1st was replaced).
        Verify that automatic rollback kicks in and restores all live files back to ACTIVE_MUTATED.
        """
        orig_replace = os.replace
        replace_calls = {"count": 0}

        def flaky_replace(src, dst):
            replace_calls["count"] += 1
            # Allow the 1st replacement to succeed, but raise error on 2nd replacement
            if replace_calls["count"] >= 2:
                raise PermissionError("Simulated locked file during live replacement")
            return orig_replace(src, dst)

        with patch("src.state_backup_manager.os.replace", side_effect=flaky_replace):
            result = self.mgr.restore_snapshot(self.target_snap["path"])
            self.assertFalse(result, "Restore must fail when Phase 5 replacement raises an error")

        # Verify rollback restored active mutated state completely
        self._assert_live_state_matches_active_mutated()

    def test_3_3_post_restore_verification_failure_triggers_rollback(self):
        """3.3 Post-restore verification failure (Phase 6) triggers full rollback."""
        with patch.object(self.mgr, "_verify_sqlite_integrity", side_effect=[True, False]):
            # First call (Phase 3 staging audit) passes True, second call (Phase 6 post-restore) returns False
            result = self.mgr.restore_snapshot(self.target_snap["path"], verify_sqlite=True)
            self.assertFalse(result, "Restore must return False when Phase 6 verification fails")

        self._assert_live_state_matches_active_mutated()

    def test_3_4_successful_atomic_restore_completes_cleanly(self):
        """3.4 When no failure occurs, restore completely swaps state to target snapshot."""
        result = self.mgr.restore_snapshot(self.target_snap["path"], verify_sqlite=True)
        self.assertTrue(result)

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.assertEqual(cfg, self.original_config)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM live_orders;").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], 555)


class TestAdversarialScenario4SQLiteStagingCorruption(unittest.TestCase):
    """Scenario 4: SQLite Database Corruption in Staging."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_s4_sqldb_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"status": "LIVE_TRADE_EXECUTION"}, f)

        self.live_db_path = os.path.join(self.data_dir, "trade_memory.db")
        with sqlite3.connect(self.live_db_path) as conn:
            conn.execute("CREATE TABLE institutional_positions (ticket INT PRIMARY KEY, asset TEXT, pnl REAL);")
            conn.execute("INSERT INTO institutional_positions VALUES (888001, 'XAUUSD', 12500.0);")
            conn.execute("INSERT INTO institutional_positions VALUES (888002, 'BTCUSD', 34200.0);")
            conn.commit()

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _assert_live_db_unmodified(self):
        """Verifies live database is completely healthy and contains original rows."""
        with sqlite3.connect(self.live_db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            res = cur.fetchone()
            self.assertEqual(res[0], "ok")
            rows = conn.execute("SELECT * FROM institutional_positions ORDER BY ticket;").fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][1], "XAUUSD")
            self.assertEqual(rows[1][1], "BTCUSD")

    def test_4_1_corrupt_non_sqlite_db_payload_in_snapshot_triggers_abort(self):
        """4.1 Injecting non-SQLite garbage into snapshot is detected in Phase 3 staging and aborts."""
        corrupt_snap_path = os.path.join(self.backups_dir, "snapshot_corrupt_db.tar.gz")

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            # Corrupted DB file
            bad_db_bytes = b"CORRUPTED_RAW_BINARY_NOT_A_VALID_SQLITE_HEADER_12345"
            ti_db = tarfile.TarInfo(name="data/trade_memory.db")
            ti_db.size = len(bad_db_bytes)
            ti_db.mtime = int(time.time())
            tar.addfile(ti_db, io.BytesIO(bad_db_bytes))

            # Valid config
            cfg_bytes = b'{"status": "FROM_SNAPSHOT"}'
            ti_cfg = tarfile.TarInfo(name="config.json")
            ti_cfg.size = len(cfg_bytes)
            ti_cfg.mtime = int(time.time())
            tar.addfile(ti_cfg, io.BytesIO(cfg_bytes))

        with open(corrupt_snap_path, "wb") as f:
            f.write(tar_buf.getvalue())

        # Attempt restore with verify_sqlite=True
        result = self.mgr.restore_snapshot(corrupt_snap_path, verify_sqlite=True)
        self.assertFalse(result, "Restore must return False when staged DB fails integrity check")

        # Live DB must not be modified
        self._assert_live_db_unmodified()

        # Config must not be modified
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.assertEqual(cfg["status"], "LIVE_TRADE_EXECUTION")

    def test_4_2_corrupted_btree_page_integrity_check_failure(self):
        """4.2 SQLite database with valid header but corrupted internal B-Tree page is rejected."""
        # Create a real multi-page SQLite database then corrupt B-Tree data pages
        temp_bad_db = os.path.join(self.test_dir, "temp_bad.db")
        with sqlite3.connect(temp_bad_db) as conn:
            conn.execute("CREATE TABLE orders (id INT PRIMARY KEY, note TEXT);")
            conn.executemany("INSERT INTO orders VALUES (?, ?);", [(i, f"Trade order note payload {i}" * 50) for i in range(500)])
            conn.commit()

        # Corrupt the middle data pages
        db_size = os.path.getsize(temp_bad_db)
        with open(temp_bad_db, "r+b") as f:
            f.seek(db_size // 2)
            f.write(b"\xAA\xBB\xCC\xDD" * 500)

        # Verify integrity check fails on this corrupted DB
        self.assertFalse(self.mgr._verify_sqlite_integrity(temp_bad_db))

        # Bundle it into a snapshot
        corrupt_snap_path = os.path.join(self.backups_dir, "snapshot_corrupted_btree.tar.gz")
        with open(temp_bad_db, "rb") as f:
            bad_bytes = f.read()

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            ti = tarfile.TarInfo(name="data/trade_memory.db")
            ti.size = len(bad_bytes)
            ti.mtime = int(time.time())
            tar.addfile(ti, io.BytesIO(bad_bytes))

        with open(corrupt_snap_path, "wb") as f:
            f.write(tar_buf.getvalue())

        result = self.mgr.restore_snapshot(corrupt_snap_path, verify_sqlite=True)
        self.assertFalse(result, "Restore must abort on corrupted SQLite B-Tree")
        self._assert_live_db_unmodified()


class TestAdversarialScenario5RetentionPruningHighLoad(unittest.TestCase):
    """Scenario 5: Retention Pruning Under High Load and Guardrails."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_s5_prune_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"retention": "test"}, f)

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _generate_synthetic_snapshots(self, count: int, age_distribution: List[int]) -> List[Dict[str, Any]]:
        """
        Creates real files and manifest entries for `count` snapshots with given day offsets.
        """
        now_dt = datetime.now(timezone.utc)
        snapshots = []

        for i in range(count):
            age_days = age_distribution[i % len(age_distribution)]
            snap_time = now_dt - timedelta(days=age_days, seconds=i * 60)
            time_str = snap_time.strftime("%Y%m%d_%H%M%S")
            label = f"load_{i:03d}_age_{age_days}d"
            filename = f"snapshot_{time_str}_{label}.tar.gz"
            filepath = os.path.join(self.backups_dir, filename)

            # Create minimal valid gzip tar file
            with tarfile.open(filepath, "w:gz") as tar:
                cfg_bytes = f'{{"index": {i}, "age": {age_days}}}'.encode("utf-8")
                ti = tarfile.TarInfo(name="config.json")
                ti.size = len(cfg_bytes)
                ti.mtime = int(snap_time.timestamp())
                tar.addfile(ti, io.BytesIO(cfg_bytes))

            # Set file mtime on disk
            os.utime(filepath, (snap_time.timestamp(), snap_time.timestamp()))

            snap_meta = {
                "snapshot_id": f"snapshot_{time_str}_{label}",
                "filename": filename,
                "path": f"data/backups/{filename}",
                "absolute_path": filepath,
                "timestamp": snap_time.isoformat(),
                "label": label,
                "format": "tar.gz",
                "size_bytes": os.path.getsize(filepath),
                "sha256": self.mgr._calculate_sha256(filepath),
                "file_count": 1,
                "files": [{"path": "config.json", "size_bytes": len(cfg_bytes)}],
                "status": "AVAILABLE"
            }
            snapshots.append(snap_meta)

        # Sort newest first
        snapshots.sort(key=lambda s: s["timestamp"], reverse=True)

        manifest = {
            "manifest_version": "1.0.0",
            "created_at": now_dt.isoformat(),
            "updated_at": now_dt.isoformat(),
            "total_backups": len(snapshots),
            "active_backups": len(snapshots),
            "pruned_backups": 0,
            "last_backup": snapshots[0] if snapshots else None,
            "last_restore": None,
            "snapshots": snapshots
        }
        self.mgr._save_manifest_atomic(manifest)
        return snapshots

    def test_5_1_and_5_2_and_5_3_50_snapshots_high_load_pruning(self):
        """
        5.1, 5.2, 5.3: Generate 50 snapshots:
          - 20 snapshots with ages 31 to 60 days (expired)
          - 30 snapshots with ages 0 to 29 days (valid)
        Verify:
          - Exactly 20 snapshots pruned.
          - 30 valid snapshots preserved on disk and manifest.
          - No valid snapshot is deleted.
        """
        # 20 expired ages (31..60), 30 valid ages (0..29)
        ages = [45, 50, 60, 35, 32, 40, 38, 55, 31, 42,
                58, 33, 36, 48, 52, 34, 39, 44, 49, 59] + list(range(0, 30))
        self.assertEqual(len(ages), 50)

        snapshots = self._generate_synthetic_snapshots(50, ages)
        self.assertEqual(len(self.mgr.get_backup_manifest()), 50)

        pruned_count = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertEqual(pruned_count, 20, "Should prune exactly 20 expired snapshots")

        remaining = self.mgr.get_backup_manifest()
        self.assertEqual(len(remaining), 30, "Should retain exactly 30 valid snapshots")

        # Verify all remaining snapshots exist on disk and have age <= 30
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=30)
        for snap in remaining:
            self.assertTrue(os.path.exists(snap["absolute_path"]))
            snap_dt = datetime.fromisoformat(snap["timestamp"])
            self.assertGreaterEqual(snap_dt, cutoff_dt)

        # Verify manifest reconciliation
        full_man = self.mgr.get_full_manifest_data()
        self.assertEqual(full_man["active_backups"], 30)
        self.assertEqual(full_man["pruned_backups"], 20)

    def test_5_4_all_50_snapshots_expired_min_keep_1_guardrail(self):
        """
        5.4 When ALL 50 snapshots are expired (>30 days), min_keep=1 preserves the single newest snapshot.
        """
        # All 50 snapshots are between 35 and 90 days old
        ages = [35 + (i % 55) for i in range(50)]
        snapshots = self._generate_synthetic_snapshots(50, ages)

        pruned_count = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertEqual(pruned_count, 49, "Must prune 49 and keep 1 newest snapshot")

        remaining = self.mgr.get_backup_manifest()
        self.assertEqual(len(remaining), 1, "Must retain exactly 1 snapshot due to min_keep=1")
        self.assertTrue(os.path.exists(remaining[0]["absolute_path"]))
        # Verify the kept one is the newest of the 50
        self.assertEqual(remaining[0]["snapshot_id"], snapshots[0]["snapshot_id"])

    def test_5_5_all_50_snapshots_expired_min_keep_5_guardrail(self):
        """
        5.5 When ALL 50 snapshots are expired, min_keep=5 preserves the top 5 newest snapshots.
        """
        ages = [40 + (i % 50) for i in range(50)]
        snapshots = self._generate_synthetic_snapshots(50, ages)

        pruned_count = self.mgr.prune_snapshots(retention_days=30, min_keep=5)
        self.assertEqual(pruned_count, 45, "Must prune 45 and keep 5 newest snapshots")

        remaining = self.mgr.get_backup_manifest()
        self.assertEqual(len(remaining), 5, "Must retain exactly 5 snapshots due to min_keep=5")
        for i in range(5):
            self.assertEqual(remaining[i]["snapshot_id"], snapshots[i]["snapshot_id"])
            self.assertTrue(os.path.exists(remaining[i]["absolute_path"]))

    def test_5_6_manifest_counter_reconciliation_under_repeated_pruning(self):
        """5.6 Repeated pruning calls maintain accurate manifest metadata and idempotent counts."""
        ages = [40, 50, 60, 10, 5]
        self._generate_synthetic_snapshots(5, ages)

        # 1st prune: 3 expired pruned
        p1 = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertEqual(p1, 3)

        # 2nd prune immediately: 0 pruned (idempotent)
        p2 = self.mgr.prune_snapshots(retention_days=30, min_keep=1)
        self.assertEqual(p2, 0)

        full_man = self.mgr.get_full_manifest_data()
        self.assertEqual(full_man["active_backups"], 2)
        self.assertEqual(full_man["pruned_backups"], 3)

    def test_5_7_manifest_self_healing_reconstruction_from_disk(self):
        """5.7 When manifest.json is corrupted or wiped, manager reconstructs it from on-disk archives."""
        ages = [5, 10, 15]
        self._generate_synthetic_snapshots(3, ages)

        # Corrupt manifest.json
        manifest_file = os.path.join(self.backups_dir, "manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write("GARBAGE_NON_JSON_DATA{{}}")

        # get_backup_manifest() should trigger _rebuild_manifest_from_disk()
        rebuilt_manifest = self.mgr.get_backup_manifest()
        self.assertEqual(len(rebuilt_manifest), 3)

        # Verify rebuilt manifest has all valid SHA256 and filenames
        for item in rebuilt_manifest:
            self.assertTrue(os.path.exists(item["absolute_path"]))
            self.assertEqual(len(item["sha256"]), 64)


class TestAdversarialMultiThreadedStress(unittest.TestCase):
    """Bonus Adversarial Stress: Concurrent Multi-Threaded Operations."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="adv_mt_stress_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.data_dir = os.path.join(self.test_dir, "data")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"counter": 0}, f)

        self.mgr = StateBackupManager(
            workspace_root=self.test_dir,
            backup_dir=self.backups_dir,
            config_path=self.config_path
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_concurrent_snapshot_creation_thread_safety(self):
        """10 concurrent threads creating snapshots simultaneously without race conditions."""
        threads = []
        results = []
        errors = []

        def worker(idx):
            try:
                meta = self.mgr.create_snapshot(label=f"thread_{idx}")
                results.append(meta)
            except Exception as e:
                errors.append(e)

        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent snapshot creation had errors: {errors}")
        self.assertEqual(len(results), 10)

        # Verify manifest recorded all 10
        manifest = self.mgr.get_backup_manifest()
        self.assertEqual(len(manifest), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
