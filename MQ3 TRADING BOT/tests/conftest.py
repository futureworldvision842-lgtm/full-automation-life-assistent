"""Repository-wide test isolation guards.

Legacy integration tests exercise persistence APIs.  They must never leave the
operator's production configuration, account plan, subscriber list, audit
manifest, or broker-reconciled memory changed after a test run.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_FILES = (
    "config.json",
    "data/fleet_config.json",
    "data/live_readiness.json",
    "data/signal_subscribers.json",
    "data/backups/manifest.json",
    "data/trade_memory.db",
)


@pytest.fixture(scope="session", autouse=True)
def protect_operator_state():
    os.environ["MQ3_TESTING"] = "1"
    snapshots = {}
    for relative in PROTECTED_FILES:
        path = PROJECT_ROOT / relative
        snapshots[path] = path.read_bytes() if path.exists() else None
    backup_dir = PROJECT_ROOT / "data" / "backups"
    original_backups = {path.resolve() for path in backup_dir.glob("snapshot_*")} if backup_dir.exists() else set()

    yield

    import gc
    gc.collect()

    for path, content in snapshots.items():
        try:
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        except Exception:
            pass

    if backup_dir.exists():
        for path in backup_dir.glob("snapshot_*"):
            if path.resolve() not in original_backups:
                try:
                    path.unlink()
                except Exception:
                    pass

