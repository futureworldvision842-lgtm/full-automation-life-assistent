"""Owner-only WhatsApp memory and locally reviewed update-request inbox.

No command in this module executes user-provided shell text or modifies source
code. Code update requests are persisted for later local review with a
tamper-evident receipt. Non-secret operator notes can be stored as memory.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import uuid
from typing import Any, Dict, List, Optional


_SECRET_PATTERN = re.compile(
    r"(?i)(password|passwd|api[ _-]?key|access[ _-]?token|secret|private[ _-]?key|seed phrase|recovery phrase)"
)


class AdminCommandManager:
    """Narrow, auditable administrative command surface for the owner chat."""

    PREFIXES = (
        "system status",
        "remember ",
        "memory",
        "update status",
        "update check",
        "update request ",
        "update apply",
    )

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
        self.memory_path = self.project_root / "data" / "operator_memory.jsonl"
        self.request_path = self.project_root / "runtime" / "admin_update_requests.jsonl"
        self._lock = threading.RLock()

    @classmethod
    def matches(cls, command: str) -> bool:
        normalized = str(command or "").strip().lower()
        return any(normalized == prefix.rstrip() or normalized.startswith(prefix) for prefix in cls.PREFIXES)

    @staticmethod
    def _canonical_hash(record: Dict[str, Any]) -> str:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        records: List[Dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    records.append(item)
        except OSError:
            return []
        return records

    def _append_receipt(self, path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            records = self._read_jsonl(path)
            record = {
                **payload,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "previous_hash": records[-1].get("record_hash") if records else None,
            }
            record["record_hash"] = self._canonical_hash(record)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            return record

    def _git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=4,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "UNAVAILABLE"
        return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"

    def _system_status(self, bot_engine: Any, whatsapp_status: Optional[Dict[str, Any]]) -> str:
        account: Dict[str, Any] = {}
        runtime: Dict[str, Any] = {}
        if bot_engine is not None and getattr(bot_engine, "mt5", None) is not None:
            account = bot_engine.mt5.get_account_info()
            runtime = bot_engine.mt5.get_runtime_status()
        login = str(account.get("login") or "")
        return (
            "🛡️ *MQ3 VERIFIED SYSTEM STATUS*\n"
            f"• Broker mode: {account.get('data_mode', 'UNAVAILABLE')}\n"
            f"• Account: ***{login[-4:] if login else 'N/A'} @ {account.get('server', 'N/A')}\n"
            f"• Broker telemetry: {'CONNECTED' if account.get('available') else 'UNAVAILABLE'}\n"
            f"• Order execution: {'AUTHORIZED' if runtime.get('live_execution_authorized') else 'LOCKED'}\n"
            f"• Engine: {'RUNNING' if getattr(bot_engine, 'running', False) else 'STOPPED'}"
            f" / {'TELEMETRY-ONLY' if getattr(bot_engine, 'telemetry_only', False) else 'STRATEGY'}\n"
            f"• WhatsApp: {'CONNECTED' if (whatsapp_status or {}).get('connected') else 'DISCONNECTED'}\n"
            "• Real-money funded execution: LOCKED"
        )

    def _remember(self, text: str) -> str:
        note = text.strip()
        if not note:
            return "⚠️ Usage: `remember <non-secret instruction>`"
        if len(note) > 1000:
            return "⚠️ Memory rejected: instruction exceeds 1000 characters."
        if _SECRET_PATTERN.search(note):
            return "🛑 Memory rejected: passwords, API keys, tokens, and recovery secrets must never be stored in chat memory."
        record = self._append_receipt(
            self.memory_path,
            {"id": f"MEM-{uuid.uuid4().hex[:10].upper()}", "kind": "OPERATOR_MEMORY", "text": note},
        )
        return f"🧠 Memory stored with receipt `{record['id']}`. It updates local operator memory, not trading evidence or source code."

    def _memory_list(self) -> str:
        records = self._read_jsonl(self.memory_path)[-5:]
        if not records:
            return "🧠 No operator memory entries are stored yet."
        lines = ["🧠 *RECENT OPERATOR MEMORY* (newest last)"]
        for item in records:
            text = str(item.get("text", "")).replace("\n", " ")[:180]
            lines.append(f"• `{item.get('id', 'UNKNOWN')}` — {text}")
        return "\n".join(lines)

    def _update_status(self) -> str:
        branch = self._git("branch", "--show-current")
        head = self._git("rev-parse", "--short=12", "HEAD")
        dirty_output = self._git("status", "--porcelain=v1")
        dirty_count = 0 if dirty_output in {"", "UNAVAILABLE"} else len(dirty_output.splitlines())
        pending = len(self._read_jsonl(self.request_path))
        return (
            "🔄 *MQ3 UPDATE STATUS*\n"
            f"• Branch: {branch}\n"
            f"• Local commit: {head}\n"
            f"• Uncommitted paths: {dirty_count}\n"
            f"• Update requests recorded: {pending}\n"
            "• Automatic remote code apply: BLOCKED (local review + tests required)"
        )

    def _update_request(self, description: str) -> str:
        request_text = description.strip()
        if not request_text:
            return "⚠️ Usage: `update request <required change>`"
        if len(request_text) > 1500:
            return "⚠️ Update request rejected: description exceeds 1500 characters."
        if _SECRET_PATTERN.search(request_text):
            return "🛑 Update request rejected: do not include credentials or secrets."
        record = self._append_receipt(
            self.request_path,
            {
                "id": f"UPD-{uuid.uuid4().hex[:10].upper()}",
                "kind": "CODE_UPDATE_REQUEST",
                "description": request_text,
                "status": "PENDING_LOCAL_REVIEW",
                "requested_branch": self._git("branch", "--show-current"),
                "requested_head": self._git("rev-parse", "--short=12", "HEAD"),
            },
        )
        return (
            f"📥 Update request `{record['id']}` queued for local review. "
            "No code, shell command, service, or trading setting was changed remotely."
        )

    def handle(
        self,
        command: str,
        *,
        sender: str,
        is_group: bool,
        bot_engine: Any = None,
        whatsapp_status: Optional[Dict[str, Any]] = None,
    ) -> str:
        del sender  # Upstream strict whitelist already authenticated identity.
        if is_group:
            return "🛑 Owner admin commands are accepted only in the direct owner chat, never in a group."
        raw = str(command or "").strip()
        normalized = raw.lower()
        if normalized == "system status":
            return self._system_status(bot_engine, whatsapp_status)
        if normalized.startswith("remember "):
            return self._remember(raw[len("remember "):])
        if normalized in {"memory", "memory list"}:
            return self._memory_list()
        if normalized in {"update status", "update check"}:
            return self._update_status()
        if normalized.startswith("update request "):
            return self._update_request(raw[len("update request "):])
        if normalized.startswith("update apply"):
            return (
                "🛑 Remote code apply is blocked. WhatsApp may queue an update request, "
                "but source changes require local review, tests, rollback preparation, and explicit approval."
            )
        return "⚠️ Unknown owner admin command. Try `system status`, `memory list`, or `update status`."
