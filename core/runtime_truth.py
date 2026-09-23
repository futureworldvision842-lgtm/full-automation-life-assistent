"""Observed runtime status and a persistent, bounded command-event ledger."""
from __future__ import annotations
import json
import re
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EVENT_DB = ROOT / "data" / "command_events.db"


def memory_status():
    path = ROOT / "memory" / "mission_memory.db"
    result = {"available": False, "data_mode": "UNAVAILABLE", "vectors": None, "documents": None,
              "source": str(path), "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1) as db:
            result.update(available=True, data_mode="LOCAL_SQLITE",
                vectors=db.execute("SELECT count(*) FROM vector_memories").fetchone()[0],
                documents=db.execute("SELECT count(*) FROM documents").fetchone()[0],
                categories=dict(db.execute("SELECT category,count(*) FROM vector_memories GROUP BY category")))
    except (OSError, sqlite3.Error) as exc:
        result["error"] = type(exc).__name__
    return result


def _connect():
    EVENT_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(EVENT_DB, timeout=3)
    db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp REAL, channel TEXT, ok INTEGER, command TEXT, output TEXT, provider TEXT)")
    return db


def redact(text):
    return re.sub(r"(?i)(password|token|api[_ -]?key|secret)(\s*[:=]\s*)[^\s,;]+", r"\1\2[REDACTED]", str(text))


def record_event(command, result, channel):
    try:
        with _connect() as db:
            db.execute("INSERT INTO events(timestamp,channel,ok,command,output,provider) VALUES(?,?,?,?,?,?)",
                (time.time(), channel, int(bool(result.get("ok"))), redact(command)[:4000],
                 redact(result.get("output", ""))[:6000], str(result.get("provider") or result.get("routed_via") or "local")))
            db.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 1000)")
    except sqlite3.Error:
        pass


def recent_events(limit=30):
    with _connect() as db:
        rows = db.execute("SELECT timestamp,channel,ok,command,output,provider FROM events ORDER BY id DESC LIMIT ?", (min(100, max(1, limit)),)).fetchall()
    return [{"timestamp": r[0], "category": "COMMAND", "badge": "OK" if r[2] else "FAILED",
             "title": r[3], "detail": r[4], "channel": r[1], "ok": bool(r[2]), "provider": r[5]} for r in rows]


def service_status():
    from bootstrap.supervisor import read_state, matching_process
    state = read_state()
    running = bool(matching_process(state.get("supervisor", {})))
    services = []
    for name, item in state.get("services", {}).items():
        current = running and bool(matching_process(item))
        services.append({"name": name, "ready": current and bool(item.get("ready")),
            "status": item.get("status") if current else "not-running", "url": item.get("url"),
            "checked_at": item.get("checked_at"), "log": item.get("log"), "owned": item.get("owned", False)})
    return {"root": str(ROOT), "supervisor_running": running, "services": services,
            "disabled": state.get("disabled", []), "mode": "autonomous-trading-live"}
