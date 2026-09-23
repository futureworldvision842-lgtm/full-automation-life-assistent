"""One-time owner approvals for consequential remote JARVIS commands.

The module never grants authority to a model.  It classifies the owner's remote
request, blocks explicitly unsafe propagation/access requests, and requires a
short-lived confirmation code before consequential commands are released to the
existing JARVIS planner.  Pending approvals and the audit trail remain local.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "scratch" / "owner_approvals.json"
AUDIT_PATH = ROOT / "logs" / "owner-control.jsonl"
APPROVAL_TTL_SECONDS = 10 * 60
_lock = threading.Lock()
_invalid_attempts: dict[str, list[float]] = {}


@dataclass(frozen=True)
class Decision:
    action: str
    message: str
    command: str = ""
    code: str = ""
    risk: str = "low"


_BLOCKED_PATTERNS = [
    re.compile(r"\b(hack|exploit|steal|exfiltrat|credential dump|keylog|ransomware|botnet)\b", re.I),
    re.compile(r"\b(disable|bypass|evade)\b.{0,40}\b(antivirus|firewall|security|authentication|permission)\b", re.I),
    re.compile(r"\b(without permission|without consent|unauthori[sz]ed)\b", re.I),
    re.compile(r"\b(self|yourself|jarvis)\b.{0,50}\b(spread|replicat|infect|propagat)\b.{0,50}\b(server|device|internet|network|computer|data.?center)\b", re.I),
    re.compile(r"\b(spread|replicat|infect|propagat)\b.{0,50}\b(server|device|internet|network|computer|data.?center)\b", re.I),
]

_HIGH_RISK_RULES = [
    ("financial", re.compile(r"\b(send|transfer|release|withdraw|deposit|pay|buy|sell|trade)\b.{0,60}\b(money|funds?|crypto|bitcoin|ethereum|wallet|pkr|usd|rupees?)\b", re.I)),
    ("publishing", re.compile(r"\b(publish|deploy|push|merge|release|upload|make public)\b", re.I)),
    ("messaging", re.compile(r"\b(send|forward|post|reply)\b.{0,60}\b(whatsapp|email|message|instagram|telegram|linkedin|facebook|youtube)\b", re.I)),
    ("destructive", re.compile(r"\b(delete|remove|erase|wipe|format|overwrite|reset|uninstall)\b", re.I)),
    ("security", re.compile(r"\b(password|api key|secret|token|credential|permission|administrator|firewall|security setting)\b", re.I)),
    ("software change", re.compile(r"\b(install|upgrade|patch|apply code|modify code|edit file|write file)\b|\bupdate\b.{0,40}\b(app|site|code|software|system|jarvis|package|repo)\b", re.I)),
    ("governance", re.compile(r"\b(vote|ballot|approve member|reject member|appoint|recall|veto|governance decision)\b", re.I)),
    ("device control", re.compile(r"\b(shutdown|restart|reboot|factory reset|remote control|take control|screenshot|camera|microphone)\b", re.I)),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_summary(text: str, limit: int = 240) -> str:
    value = re.sub(r"(?i)(password|token|secret|api[_ -]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", text or "")
    value = re.sub(r"\b[A-Za-z0-9_\-]{32,}\b", "[REDACTED]", value)
    value = " ".join(value.split())
    return value[:limit]


def _load_pending() -> dict:
    try:
        data = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_pending(data: dict) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = PENDING_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(PENDING_PATH)


def _audit(event: str, source: str, owner_id: str, command: str, risk: str, code: str = "") -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": _now_iso(),
        "event": event,
        "source": _safe_summary(source, 40),
        "owner": hashlib.sha256((owner_id or "owner").encode("utf-8")).hexdigest()[:12],
        "command": _safe_summary(command),
        "risk": risk,
        "approval": code,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _prune(data: dict, now: float) -> dict:
    return {code: item for code, item in data.items() if float(item.get("expires", 0)) > now}


def _risk_for(command: str) -> tuple[str, str]:
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(command):
            return "blocked", "unauthorized propagation or access"
    matches = [name for name, pattern in _HIGH_RISK_RULES if pattern.search(command)]
    return ("high", ", ".join(matches)) if matches else ("low", "read-only or ordinary assistance")


def request_consequential_approval(
    command: str,
    reason: str,
    source: str = "desktop-ui",
    owner_id: str = "owner",
) -> Decision:
    """Create/reuse an approval for a caller-classified consequential action.

    Tool adapters know more than the natural-language classifier about whether
    a particular operation mutates local or external state.  This entry point
    lets them fail closed without teaching the model an approval bypass.  The
    payload is released only by the same exact ``approve CODE`` flow used by
    :func:`evaluate_command`.
    """
    text = (command or "").strip()
    risk_reason = " ".join((reason or "consequential action").strip().split())
    if not text:
        return Decision("invalid", "Command is empty.")

    now = time.time()
    with _lock:
        pending = _prune(_load_pending(), now)
        digest = hashlib.sha256(f"{owner_id}\0{text}".encode("utf-8")).hexdigest()
        for code, item in pending.items():
            if item.get("digest") == digest and item.get("owner_id") == owner_id:
                return Decision(
                    "approval_required",
                    f"Approval required ({risk_reason}). Reply: approve {code}",
                    text,
                    code,
                    risk_reason,
                )

        code = secrets.token_hex(5).upper()
        pending[code] = {
            "command": text,
            "digest": digest,
            "owner_id": owner_id,
            "source": source,
            "risk": risk_reason,
            "created": now,
            "expires": now + APPROVAL_TTL_SECONDS,
        }
        _save_pending(pending)
        _audit("approval_requested", source, owner_id, text, risk_reason, code)
        return Decision(
            "approval_required",
            f"This action can change state ({risk_reason}). Reply within 10 minutes: "
            f"approve {code}. To cancel: reject {code}.",
            text,
            code,
            risk_reason,
        )


def evaluate_command(command: str, source: str = "whatsapp", owner_id: str = "owner") -> Decision:
    """Return execute, approval_required, denied, rejected, or invalid."""
    text = (command or "").strip()
    if not text:
        return Decision("invalid", "Command is empty.")
    now = time.time()

    approve = re.fullmatch(r"(?i)approve\s+([A-F0-9]{6,16})", text)
    reject = re.fullmatch(r"(?i)(?:reject|cancel)\s+([A-F0-9]{6,16})", text)

    with _lock:
        pending = _prune(_load_pending(), now)
        if approve:
            code = approve.group(1).upper()
            attempts = [stamp for stamp in _invalid_attempts.get(owner_id, []) if now - stamp < 300]
            _invalid_attempts[owner_id] = attempts
            if len(attempts) >= 8:
                _audit("approval_rate_limited", source, owner_id, text, "high", code)
                return Decision("invalid", "Too many invalid approval attempts. Try again later.")
            item = pending.get(code)
            if not item or item.get("owner_id") != owner_id:
                attempts.append(now)
                _audit("invalid_approval", source, owner_id, text, "high", code)
                return Decision("invalid", "Approval code is invalid or expired.")
            pending.pop(code, None)
            _invalid_attempts.pop(owner_id, None)
            _save_pending(pending)
            original = str(item.get("command") or "")
            _audit("approved", source, owner_id, original, str(item.get("risk") or "high"), code)
            return Decision("execute", "Owner approval accepted.", original, code, "approved")
        if reject:
            code = reject.group(1).upper()
            item = pending.get(code)
            if not item or item.get("owner_id") != owner_id:
                _audit("invalid_rejection", source, owner_id, text, "high", code)
                return Decision("invalid", "Approval code is invalid or expired.")
            pending.pop(code, None)
            _save_pending(pending)
            _audit("rejected", source, owner_id, str((item or {}).get("command") or ""), "high", code)
            return Decision("rejected", "Pending command cancelled.", code=code, risk="high")

        risk, reason = _risk_for(text)
        if risk == "blocked":
            _audit("denied", source, owner_id, text, risk)
            return Decision(
                "denied",
                "I cannot spread into systems, bypass security, or access devices without informed owner permission. I can prepare an opt-in deployment plan instead.",
                risk=risk,
            )
        if risk == "high":
            digest = hashlib.sha256(f"{owner_id}\0{text}".encode("utf-8")).hexdigest()
            for code, item in pending.items():
                if item.get("digest") == digest and item.get("owner_id") == owner_id:
                    return Decision("approval_required", f"Approval required ({reason}). Reply: approve {code}", text, code, risk)
            code = secrets.token_hex(5).upper()
            pending[code] = {
                "command": text,
                "digest": digest,
                "owner_id": owner_id,
                "source": source,
                "risk": reason,
                "created": now,
                "expires": now + APPROVAL_TTL_SECONDS,
            }
            _save_pending(pending)
            _audit("approval_requested", source, owner_id, text, reason, code)
            return Decision(
                "approval_required",
                f"This command can change external state ({reason}). Reply within 10 minutes: approve {code}. To cancel: reject {code}.",
                text,
                code,
                reason,
            )

        _save_pending(pending)
        _audit("released", source, owner_id, text, risk)
        return Decision("execute", "Command accepted.", text, risk=risk)


def decision_json(decision: Decision) -> dict:
    return asdict(decision)
