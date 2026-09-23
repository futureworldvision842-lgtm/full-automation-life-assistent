"""
src/state_backup_manager.py — Institutional State Backup & Point-in-Time Disaster Recovery Manager.
Milestone: M4 (State Backup & Self-Healing Disaster Recovery)

Capabilities:
  1. Transactionally consistent snapshot creation (.tar.gz and .zip) with cryptographic SHA256 hashing.
  2. Safe SQLite online backup via Connection.backup() to prevent torn pages during active trading.
  3. Process-safe and thread-safe manifest tracking (data/backups/manifest.json) using atomic swaps.
  4. 6-Phase atomic state restore with pre-flight verification, staged SQLite PRAGMA integrity check,
     and automatic live rollback on any failure.
  5. 30-Day retention pruning with strict min_keep guardrails to prevent backup wipeout.
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
import logging
import tempfile
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger("StateBackupManager")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class BackupError(Exception):
    """Base exception for all backup manager operations."""
    pass


class DatabaseIntegrityError(BackupError):
    """Raised when SQLite database fails PRAGMA integrity_check."""
    pass


class RestoreValidationError(BackupError):
    """Raised when a snapshot archive fails pre-flight validation."""
    pass


class SecurityError(BackupError):
    """Raised when archive contains path traversal or illegal member paths."""
    pass


class StateBackupManager:
    """
    Autonomous State Backup & Point-in-Time Disaster Recovery Manager.
    Manages automated snapshots, atomic rollback, and retention pruning.
    """

    # Core state targets relative to workspace root
    DEFAULT_STATE_TARGETS = [
        "config.json",
        "data/cognitive_memory/episodic_memory.json",
        "data/cognitive_memory/semantic_memory.json",
        "data/trade_memory.db",
        "data/experience_replay_db.json",
        "data/memory_tree.json",
        "data/accounts_fleet.json",
        "data/firebase_memory.json",
        "data/mongodb_memory.json"
    ]

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        backup_dir: Optional[str] = None,
        manifest_file: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs
    ):
        """
        Initializes StateBackupManager with configurable workspace and backup directories.
        Supports keyword aliases (project_root, root_dir, backups_dir, manifest_path).
        """
        # Resolve workspace root
        raw_root = (
            workspace_root
            or kwargs.get("project_root")
            or kwargs.get("root_dir")
            or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        )
        self.workspace_root = os.path.abspath(raw_root)
        self.project_root = self.workspace_root  # Alias for backward compatibility
        self.root_dir = self.workspace_root      # Alias for backward compatibility

        # Resolve backup directory
        raw_backup_dir = (
            backup_dir
            or kwargs.get("backups_dir")
            or os.path.join(self.workspace_root, "data", "backups")
        )
        self.backup_dir = os.path.abspath(raw_backup_dir)
        self.backups_dir = self.backup_dir  # Alias

        # Resolve manifest file path
        raw_manifest_file = (
            manifest_file
            or kwargs.get("manifest_path")
            or os.path.join(self.backup_dir, "manifest.json")
        )
        self.manifest_file = os.path.abspath(raw_manifest_file)
        self.manifest_path = self.manifest_file  # Alias

        # Resolve config file path
        self.config_path = os.path.abspath(
            config_path or os.path.join(self.workspace_root, "config.json")
        )

        self._lock = threading.RLock()
        os.makedirs(self.backup_dir, exist_ok=True)
        self._ensure_manifest_exists()

    def _ensure_manifest_exists(self) -> None:
        """Initializes an empty manifest.json if missing or invalid."""
        with self._lock:
            if not os.path.exists(self.manifest_file) or os.path.getsize(self.manifest_file) == 0:
                initial_manifest = {
                    "manifest_version": "1.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "total_backups": 0,
                    "active_backups": 0,
                    "pruned_backups": 0,
                    "last_backup": None,
                    "last_restore": None,
                    "snapshots": []
                }
                self._save_manifest_atomic(initial_manifest)

    def _load_manifest(self) -> Dict[str, Any]:
        """Loads manifest.json with safe JSON parsing and auto-recovery fallback."""
        with self._lock:
            if os.path.exists(self.manifest_file):
                try:
                    with open(self.manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "snapshots" in data:
                            return data
                except Exception as e:
                    logger.warning(f"Manifest JSON read/parse failed ({e}). Rebuilding manifest from disk...")

            # Rebuild manifest dynamically if file is corrupted or missing
            return self._rebuild_manifest_from_disk()

    def _rebuild_manifest_from_disk(self) -> Dict[str, Any]:
        """Scans the backup directory and reconstructs manifest.json from existing archives."""
        with self._lock:
            discovered_snapshots = []
            if os.path.exists(self.backup_dir):
                for filename in os.listdir(self.backup_dir):
                    if filename.startswith("snapshot_") and (filename.endswith(".tar.gz") or filename.endswith(".zip") or filename.endswith(".tgz")):
                        archive_path = os.path.join(self.backup_dir, filename)
                        try:
                            file_size = os.path.getsize(archive_path)
                            sha256_hash = self._calculate_sha256(archive_path)
                            mtime = os.path.getmtime(archive_path)
                            iso_time = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                            
                            # Parse label and snapshot_id
                            base_name = filename.rsplit(".", 2)[0] if filename.endswith(".tar.gz") else filename.rsplit(".", 1)[0]
                            parts = base_name.split("_", 3)
                            label = parts[3] if len(parts) >= 4 else "auto"
                            
                            snapshot_entry = {
                                "snapshot_id": base_name,
                                "filename": filename,
                                "path": os.path.relpath(archive_path, self.workspace_root).replace("\\", "/"),
                                "absolute_path": archive_path,
                                "timestamp": iso_time,
                                "label": label,
                                "format": "tar.gz" if filename.endswith(".tar.gz") or filename.endswith(".tgz") else "zip",
                                "size_bytes": file_size,
                                "sha256": sha256_hash,
                                "file_count": 0,
                                "files": [],
                                "status": "AVAILABLE"
                            }
                            discovered_snapshots.append(snapshot_entry)
                        except Exception as err:
                            logger.error(f"Failed to inspect backup archive {filename}: {err}")

            discovered_snapshots.sort(key=lambda s: s.get("timestamp", ""), reverse=True)

            manifest_data = {
                "manifest_version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total_backups": len(discovered_snapshots),
                "active_backups": len(discovered_snapshots),
                "pruned_backups": 0,
                "last_backup": discovered_snapshots[0] if discovered_snapshots else None,
                "last_restore": None,
                "snapshots": discovered_snapshots
            }
            self._save_manifest_atomic(manifest_data)
            return manifest_data

    def _save_manifest_atomic(self, manifest_data: Dict[str, Any]) -> None:
        """Persists manifest.json safely using a unique temporary file and atomic replace."""
        with self._lock:
            manifest_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            temp_path = f"{self.manifest_file}.tmp.{os.getpid()}_{int(time.time()*1000)}"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                # Retry loop for Windows file locking contention
                for attempt in range(4):
                    try:
                        os.replace(temp_path, self.manifest_file)
                        break
                    except PermissionError:
                        if attempt == 3:
                            raise
                        time.sleep(0.05 * (2 ** attempt))
            except Exception as e:
                logger.error(f"Failed to atomic-save manifest: {e}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                raise

    @staticmethod
    def _calculate_sha256(file_path: str) -> str:
        """Calculates the SHA256 cryptographic hash of a file in 64KB chunks."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    def _safe_sqlite_backup(self, src_path: str, dest_path: str) -> bool:
        """
        Safely copies a live SQLite database using SQLite Online Backup API
        to prevent torn pages or WAL read-lock issues during active trading.
        """
        if not os.path.exists(src_path):
            return False
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        src_conn = None
        dst_conn = None
        try:
            src_conn = sqlite3.connect(src_path, timeout=10.0)
            try:
                src_conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass

            dst_conn = sqlite3.connect(dest_path)
            with dst_conn:
                src_conn.backup(dst_conn, pages=0)
            return True
        except Exception as e:
            logger.warning(f"SQLite Online Backup warning for {src_path} ({e}). Falling back to direct copy.")
            try:
                shutil.copy2(src_path, dest_path)
                return True
            except Exception as copy_err:
                logger.error(f"Direct SQLite copy fallback failed: {copy_err}")
                return False
        finally:
            if dst_conn:
                try:
                    dst_conn.close()
                except Exception:
                    pass
            if src_conn:
                try:
                    src_conn.close()
                except Exception:
                    pass

    def _verify_sqlite_integrity(self, db_path: str) -> bool:
        """Executes PRAGMA integrity_check on a SQLite database file."""
        if not os.path.exists(db_path):
            return False
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            rows = cursor.fetchall()
            return len(rows) > 0 and str(rows[0][0]).strip().lower() == "ok"
        except Exception as e:
            logger.error(f"SQLite integrity check failed for {db_path}: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _sanitize_and_validate_member_path(self, target_dir: str, member_name: str) -> str:
        """Guards against Tar Slip / Zip Slip path traversal security vulnerabilities."""
        normalized = os.path.normpath(member_name).lstrip("/\\")
        if normalized.startswith("..") or os.path.isabs(normalized):
            raise SecurityError(f"Illegal path traversal attempt in archive member: {member_name}")

        dest_path = os.path.abspath(os.path.join(target_dir, normalized))
        target_abs = os.path.abspath(target_dir)
        if not dest_path.startswith(target_abs + os.sep) and dest_path != target_abs:
            raise SecurityError(f"Path escape attempt in archive member: {member_name}")
        return dest_path

    def create_snapshot(
        self,
        label: str = "auto",
        format: str = "tar.gz",
        custom_include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a transactionally consistent, compressed snapshot archive of all system state.
        
        Args:
            label: Semantic descriptor for snapshot (e.g. 'auto', 'manual', 'hourly', 'pre_upgrade').
            format: Compression format ('tar.gz' or 'zip'). Default: 'tar.gz'.
            custom_include: Optional list of additional relative file paths to bundle.
            
        Returns:
            Dict[str, Any] containing comprehensive snapshot metadata.
        """
        with self._lock:
            now_dt = datetime.now(timezone.utc)
            timestamp_str = now_dt.strftime("%Y%m%d_%H%M%S")
            iso_timestamp = now_dt.isoformat()
            clean_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")).lower() or "auto"

            ext = ".tar.gz" if format.lower() in ("tar.gz", "tgz") else ".zip"
            snapshot_id = f"snapshot_{timestamp_str}_{clean_label}"
            filename = f"{snapshot_id}{ext}"
            archive_path = os.path.join(self.backup_dir, filename)

            # Assemble target list
            target_candidates = list(self.DEFAULT_STATE_TARGETS)

            # Dynamically discover all memory json files
            cognitive_dir = os.path.join(self.workspace_root, "data", "cognitive_memory")
            if os.path.exists(cognitive_dir):
                for f in os.listdir(cognitive_dir):
                    if f.endswith(".json"):
                        rel_p = f"data/cognitive_memory/{f}"
                        if rel_p not in target_candidates:
                            target_candidates.append(rel_p)

            if custom_include:
                for item in custom_include:
                    if item not in target_candidates:
                        target_candidates.append(item)

            # Create isolated staging directory
            staging_dir = os.path.join(self.backup_dir, f".staging_{snapshot_id}_{int(time.time()*1000)}")
            os.makedirs(staging_dir, exist_ok=True)

            files_meta = []
            try:
                for rel_path in target_candidates:
                    src_full = os.path.normpath(os.path.join(self.workspace_root, rel_path))
                    if not os.path.exists(src_full):
                        continue

                    stage_dest = os.path.normpath(os.path.join(staging_dir, rel_path))
                    os.makedirs(os.path.dirname(stage_dest), exist_ok=True)

                    if rel_path.endswith(".db"):
                        self._safe_sqlite_backup(src_full, stage_dest)
                    else:
                        shutil.copy2(src_full, stage_dest)

                    file_sha = self._calculate_sha256(stage_dest)
                    file_size = os.path.getsize(stage_dest)
                    normalized_rel = rel_path.replace("\\", "/")
                    files_meta.append({
                        "path": normalized_rel,
                        "size_bytes": file_size,
                        "sha256": file_sha
                    })

                # Write snapshot_meta.json into staging header
                meta_content = {
                    "snapshot_id": snapshot_id,
                    "timestamp": iso_timestamp,
                    "label": clean_label,
                    "format": format,
                    "files": files_meta,
                    "system": {
                        "platform": sys.platform,
                        "python_version": sys.version.split()[0]
                    }
                }
                with open(os.path.join(staging_dir, "snapshot_meta.json"), "w", encoding="utf-8") as f:
                    json.dump(meta_content, f, indent=2)

                # Compress staging folder into target archive
                if format.lower() in ("tar.gz", "tgz"):
                    with tarfile.open(archive_path, "w:gz") as tar:
                        for root, _, files in os.walk(staging_dir):
                            for f in files:
                                full_f = os.path.join(root, f)
                                rel_f = os.path.relpath(full_f, staging_dir).replace("\\", "/")
                                tar.add(full_f, arcname=rel_f)
                else:
                    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_f:
                        for root, _, files in os.walk(staging_dir):
                            for f in files:
                                full_f = os.path.join(root, f)
                                rel_f = os.path.relpath(full_f, staging_dir).replace("\\", "/")
                                zip_f.write(full_f, arcname=rel_f)

            finally:
                if os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir, ignore_errors=True)

            archive_sha = self._calculate_sha256(archive_path)
            archive_size = os.path.getsize(archive_path)
            rel_archive_path = os.path.relpath(archive_path, self.workspace_root).replace("\\", "/")

            snapshot_summary = {
                "snapshot_id": snapshot_id,
                "filename": filename,
                "path": rel_archive_path,
                "absolute_path": archive_path,
                "timestamp": iso_timestamp,
                "label": clean_label,
                "format": format,
                "size_bytes": archive_size,
                "sha256": archive_sha,
                "file_count": len(files_meta),
                "files": files_meta,
                "status": "AVAILABLE"
            }

            # Update manifest.json
            manifest = self._load_manifest()
            manifest["total_backups"] = manifest.get("total_backups", 0) + 1
            manifest["active_backups"] = len(manifest.get("snapshots", [])) + 1
            manifest["last_backup"] = snapshot_summary
            snapshots_list = manifest.get("snapshots", [])
            snapshots_list.insert(0, snapshot_summary)
            manifest["snapshots"] = snapshots_list
            self._save_manifest_atomic(manifest)

            logger.info(f"Snapshot created successfully: {snapshot_id} ({archive_size} bytes, {len(files_meta)} files)")
            return snapshot_summary

    def restore_snapshot(
        self,
        snapshot_path: str,
        verify_sqlite: bool = True
    ) -> bool:
        """
        Executes safe 6-phase atomic rollback from a snapshot archive:
          1. Pre-flight verification (existence, checksum match).
          2. Isolated staging extraction with Zip Slip defense.
          3. Staged component integrity audit (JSON parse, SQLite PRAGMA integrity_check).
          4. Live state rollback backup creation.
          5. Atomic file replacement to live workspace.
          6. Post-restore verification (and instant rollback on any error).
        """
        with self._lock:
            start_time = time.perf_counter()

            # Resolve snapshot path
            full_snap_path = snapshot_path if os.path.isabs(snapshot_path) else os.path.join(self.workspace_root, snapshot_path)
            if not os.path.exists(full_snap_path):
                # Try finding in backup_dir
                alt_path = os.path.join(self.backup_dir, os.path.basename(snapshot_path))
                if os.path.exists(alt_path):
                    full_snap_path = alt_path
                else:
                    logger.error(f"Snapshot file not found: {snapshot_path}")
                    return False

            if os.path.getsize(full_snap_path) == 0:
                logger.error(f"Snapshot file is empty (0 bytes): {snapshot_path}")
                return False

            # Phase 1: Pre-flight Verification
            sha_calc = self._calculate_sha256(full_snap_path)
            manifest = self._load_manifest()
            snap_record = next(
                (s for s in manifest.get("snapshots", [])
                 if s.get("filename") == os.path.basename(full_snap_path)
                 or s.get("snapshot_id") == os.path.basename(full_snap_path)),
                None
            )
            if snap_record and snap_record.get("sha256") and snap_record.get("sha256") != sha_calc:
                logger.error(
                    f"SHA256 checksum mismatch for snapshot {snapshot_path}. "
                    f"Expected: {snap_record.get('sha256')}, Got: {sha_calc}"
                )
                return False

            staging_dir = os.path.join(self.backup_dir, f".tmp_restore_staging_{int(time.time()*1000)}")
            rollback_dir = os.path.join(self.backup_dir, f".tmp_rollback_{int(time.time()*1000)}")
            os.makedirs(staging_dir, exist_ok=True)
            os.makedirs(rollback_dir, exist_ok=True)

            try:
                # Phase 2: Isolated Staging Extraction
                if full_snap_path.endswith(".tar.gz") or full_snap_path.endswith(".tgz"):
                    try:
                        with tarfile.open(full_snap_path, "r:gz") as tar:
                            for member in tar.getmembers():
                                self._sanitize_and_validate_member_path(staging_dir, member.name)
                            tar.extractall(staging_dir)
                    except Exception as tar_err:
                        logger.error(f"Tar extraction failed: {tar_err}")
                        return False
                elif full_snap_path.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(full_snap_path, "r") as zip_f:
                            for member_name in zip_f.namelist():
                                self._sanitize_and_validate_member_path(staging_dir, member_name)
                            zip_f.extractall(staging_dir)
                    except Exception as zip_err:
                        logger.error(f"Zip extraction failed: {zip_err}")
                        return False
                else:
                    logger.error(f"Unsupported snapshot archive format: {full_snap_path}")
                    return False

                # Phase 3: Integrity Validation on Staged Files
                for root, _, files in os.walk(staging_dir):
                    for f in files:
                        staged_file = os.path.join(root, f)
                        if f.endswith(".json"):
                            try:
                                with open(staged_file, "r", encoding="utf-8") as jf:
                                    json.load(jf)
                            except Exception as json_err:
                                raise RestoreValidationError(f"Staged JSON file {f} is corrupted: {json_err}")
                        elif f.endswith(".db") and verify_sqlite:
                            if not self._verify_sqlite_integrity(staged_file):
                                raise DatabaseIntegrityError(f"Staged SQLite database {f} failed PRAGMA integrity_check.")

                # Phase 4: Stage Live Rollback Backup
                extracted_relative_files = []
                for root, _, files in os.walk(staging_dir):
                    for f in files:
                        if f == "snapshot_meta.json":
                            continue
                        full_f = os.path.join(root, f)
                        rel_f = os.path.relpath(full_f, staging_dir)
                        extracted_relative_files.append(rel_f)

                        live_target = os.path.join(self.workspace_root, rel_f)
                        if os.path.exists(live_target):
                            rb_target = os.path.join(rollback_dir, rel_f)
                            os.makedirs(os.path.dirname(rb_target), exist_ok=True)
                            if rel_f.endswith(".db"):
                                self._safe_sqlite_backup(live_target, rb_target)
                            else:
                                shutil.copy2(live_target, rb_target)

                # Phase 5: Atomic Live Replacement
                for rel_f in extracted_relative_files:
                    staged_source = os.path.join(staging_dir, rel_f)
                    live_target = os.path.join(self.workspace_root, rel_f)
                    os.makedirs(os.path.dirname(live_target), exist_ok=True)

                    if rel_f.endswith(".db"):
                        if not self._safe_sqlite_backup(staged_source, live_target):
                            raise BackupError(f"Failed to copy staged database to live target: {rel_f}")
                    else:
                        temp_live = f"{live_target}.tmp.{int(time.time()*1000)}"
                        shutil.copy2(staged_source, temp_live)
                        os.replace(temp_live, live_target)

                # Phase 6: Post-Restore Verification
                if verify_sqlite:
                    for rel_f in extracted_relative_files:
                        if rel_f.endswith(".db"):
                            live_db = os.path.join(self.workspace_root, rel_f)
                            if not self._verify_sqlite_integrity(live_db):
                                raise DatabaseIntegrityError(f"Live database {rel_f} failed integrity check post-restore.")

                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                snap_id = snap_record.get("snapshot_id") if snap_record else os.path.basename(full_snap_path)

                manifest["last_restore"] = {
                    "snapshot_id": snap_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "SUCCESS",
                    "restored_files_count": len(extracted_relative_files),
                    "sqlite_integrity_passed": verify_sqlite,
                    "duration_ms": elapsed_ms
                }
                self._save_manifest_atomic(manifest)
                logger.info(f"Snapshot {snap_id} successfully restored in {elapsed_ms}ms ({len(extracted_relative_files)} files).")
                return True

            except Exception as e:
                logger.error(f"Restore failed ({e}). Executing automatic rollback to pre-restore live state...")
                # Automatic Rollback
                for root, _, files in os.walk(rollback_dir):
                    for f in files:
                        full_rb = os.path.join(root, f)
                        rel_rb = os.path.relpath(full_rb, rollback_dir)
                        live_target = os.path.join(self.workspace_root, rel_rb)
                        try:
                            if rel_rb.endswith(".db"):
                                self._safe_sqlite_backup(full_rb, live_target)
                            else:
                                shutil.copy2(full_rb, live_target)
                        except Exception as rb_err:
                            logger.critical(f"Critical error restoring rollback file {rel_rb}: {rb_err}")
                return False

            finally:
                shutil.rmtree(staging_dir, ignore_errors=True)
                shutil.rmtree(rollback_dir, ignore_errors=True)

    def prune_snapshots(
        self,
        retention_days: int = 30,
        min_keep: int = 1
    ) -> int:
        """
        Prunes snapshot archives older than retention_days while guaranteeing min_keep backups.
        
        Args:
            retention_days: Number of days to retain backups (default 30).
            min_keep: Minimum number of newest snapshots to preserve unconditionally (default 1).
            
        Returns:
            int: Number of snapshot archives deleted.
        """
        with self._lock:
            cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
            manifest = self._load_manifest()
            snapshots = manifest.get("snapshots", [])

            if len(snapshots) <= min_keep:
                logger.info(f"Snapshot count ({len(snapshots)}) <= min_keep ({min_keep}). No pruning performed.")
                return 0

            # Sort newest first
            try:
                snapshots.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
            except Exception:
                pass

            kept_snapshots = []
            pruned_count = 0

            for idx, snap in enumerate(snapshots):
                # Unconditionally preserve top min_keep snapshots
                if idx < min_keep:
                    kept_snapshots.append(snap)
                    continue

                snap_time_str = snap.get("timestamp")
                is_expired = False
                if snap_time_str:
                    try:
                        snap_dt = datetime.fromisoformat(snap_time_str)
                        if snap_dt.tzinfo is None:
                            snap_dt = snap_dt.replace(tzinfo=timezone.utc)
                        if snap_dt < cutoff_dt:
                            is_expired = True
                    except Exception:
                        pass

                # Also inspect disk mtime if available
                snap_fn = snap.get("filename", "")
                snap_abs = snap.get("absolute_path") or os.path.join(self.backup_dir, snap_fn)
                if not is_expired and os.path.exists(snap_abs):
                    mtime_dt = datetime.fromtimestamp(os.path.getmtime(snap_abs), tz=timezone.utc)
                    if mtime_dt < cutoff_dt:
                        is_expired = True

                if is_expired:
                    if os.path.exists(snap_abs):
                        try:
                            os.remove(snap_abs)
                            logger.info(f"Pruned expired backup file: {snap_fn}")
                        except Exception as e:
                            logger.warning(f"Could not remove backup file {snap_fn}: {e}")
                    pruned_count += 1
                else:
                    kept_snapshots.append(snap)

            manifest["snapshots"] = kept_snapshots
            manifest["active_backups"] = len(kept_snapshots)
            manifest["pruned_backups"] = manifest.get("pruned_backups", 0) + pruned_count
            self._save_manifest_atomic(manifest)

            logger.info(f"Pruned {pruned_count} snapshots older than {retention_days} days.")
            return pruned_count

    def get_backup_manifest(self) -> List[Dict[str, Any]]:
        """
        Returns sorted list of snapshot manifest entries (newest first).
        """
        manifest = self._load_manifest()
        return manifest.get("snapshots", [])

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Returns list of active snapshots."""
        return self.get_backup_manifest()

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Returns metadata of the most recent snapshot."""
        snapshots = self.get_backup_manifest()
        return snapshots[0] if snapshots else None

    def get_full_manifest_data(self) -> Dict[str, Any]:
        """Returns the full manifest dictionary."""
        return self._load_manifest()


if __name__ == "__main__":
    print("Testing StateBackupManager CLI...")
    mgr = StateBackupManager()
    snap = mgr.create_snapshot(label="manual_cli")
    print(f"Created snapshot: {snap.get('snapshot_id')} ({snap.get('size_bytes')} bytes)")
    manifest = mgr.get_backup_manifest()
    print(f"Total manifest entries: {len(manifest)}")
