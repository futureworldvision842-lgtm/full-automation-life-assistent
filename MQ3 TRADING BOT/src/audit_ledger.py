"""Append-only, tamper-evident JSONL audit ledger for live trade decisions."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import threading
from typing import Any, Dict, Iterable, Tuple


_SECRET_TOKENS = ("password", "secret", "token", "api_key", "passphrase", "private_key")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if any(token in str(key).lower() for token in _SECRET_TOKENS) else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


class AuditLedger:
    def __init__(self, path: str = "data/audit/execution_audit.jsonl"):
        self.path = path
        self._lock = threading.Lock()

    @staticmethod
    def _hash(record_without_hash: Dict[str, Any]) -> str:
        canonical = json.dumps(record_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _last_hash(self) -> str:
        if not os.path.exists(self.path):
            return "GENESIS"
        last = ""
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        if not last:
            return "GENESIS"
        try:
            return str(json.loads(last).get("record_hash", "INVALID"))
        except json.JSONDecodeError:
            return "INVALID"

    def append(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not str(event_type).strip() or not isinstance(payload, dict):
            raise ValueError("event_type and dictionary payload are required")
        with self._lock:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            record = {
                "schema_version": 1,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "event_type": str(event_type).strip(),
                "previous_hash": self._last_hash(),
                "payload": _redact(payload),
            }
            record["record_hash"] = self._hash(record)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return record

    def verify(self) -> Tuple[bool, int, str]:
        previous = "GENESIS"
        count = 0
        if not os.path.exists(self.path):
            return True, 0, "EMPTY"
        with open(self.path, "r", encoding="utf-8") as handle:
            for count, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    return False, count, "INVALID_JSON"
                claimed = record.pop("record_hash", None)
                if record.get("previous_hash") != previous or claimed != self._hash(record):
                    return False, count, "HASH_CHAIN_MISMATCH"
                previous = str(claimed)
        return True, count, previous

