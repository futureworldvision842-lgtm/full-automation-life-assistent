"""Durable, local mission memory for JARVIS.

This is deliberately separate from personal profile memory.  It stores mission
facts, plans and daily reports in SQLite, indexes the founder's reviewed core
documents, and returns small source-labelled context blocks for AI prompts.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "memory" / "mission_memory.db"
REGISTRY_PATH = ROOT / "core" / "mission_registry.json"
CORE_DOCUMENTS = [
    ROOT / "core" / "founder_mission.md",
    ROOT / "core" / "boss_brain.md",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
          source TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          body TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          category TEXT NOT NULL,
          text TEXT NOT NULL,
          source TEXT NOT NULL,
          confidence REAL NOT NULL DEFAULT 1.0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS daily_reports (
          report_date TEXT PRIMARY KEY,
          report TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS memories_category_created
          ON memories(category, created_at DESC);
        """
    )
    return db


@contextmanager
def _session():
    db = _connect()
    try:
        with db:
            yield db
    finally:
        db.close()


def load_registry() -> dict:
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def sync_core_documents() -> int:
    documents: list[tuple[str, str, str]] = []
    for path in CORE_DOCUMENTS:
        if path.exists():
            documents.append((str(path.relative_to(ROOT)), path.stem.replace("_", " ").title(), path.read_text(encoding="utf-8", errors="replace")))
    if REGISTRY_PATH.exists():
        registry = load_registry()
        documents.append((str(REGISTRY_PATH.relative_to(ROOT)), "Mission Registry", json.dumps(registry, ensure_ascii=False, indent=2)))
    with _session() as db:
        for source, title, body in documents:
            db.execute(
                """INSERT INTO documents(source, title, body, updated_at) VALUES(?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET title=excluded.title, body=excluded.body, updated_at=excluded.updated_at""",
                (source, title, body, _now()),
            )
    return len(documents)


def remember(text: str, category: str = "mission", source: str = "owner", confidence: float = 1.0) -> int:
    clean = " ".join((text or "").split())[:4000]
    if not clean:
        raise ValueError("Memory text is empty")
    category = re.sub(r"[^a-z0-9_-]", "_", (category or "mission").lower())[:40]
    source = " ".join((source or "owner").split())[:100]
    confidence = max(0.0, min(1.0, float(confidence)))
    with _session() as db:
        row = db.execute(
            "INSERT INTO memories(category, text, source, confidence, created_at) VALUES(?, ?, ?, ?, ?)",
            (category, clean, source, confidence, _now()),
        )
        return int(row.lastrowid)


def recall(query: str = "", limit: int = 8) -> list[dict]:
    limit = max(1, min(20, int(limit)))
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_]{3,}", query or "")][:8]
    with _session() as db:
        rows = db.execute(
            "SELECT id, category, text, source, confidence, created_at FROM memories ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    values = [dict(row) for row in rows]
    if terms:
        values.sort(key=lambda item: sum(term in str(item.get("text", "")).lower() for term in terms), reverse=True)
    return values[:limit]


def save_daily_report(report: str, report_date: str | None = None) -> None:
    date_value = report_date or datetime.now().date().isoformat()
    with _session() as db:
        db.execute(
            """INSERT INTO daily_reports(report_date, report, created_at) VALUES(?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET report=excluded.report, created_at=excluded.created_at""",
            (date_value, (report or "")[:12000], _now()),
        )


def latest_daily_report() -> str:
    with _session() as db:
        row = db.execute("SELECT report FROM daily_reports ORDER BY report_date DESC LIMIT 1").fetchone()
    return str(row["report"]) if row else ""


def properties() -> list[dict]:
    values = load_registry().get("properties", [])
    return values if isinstance(values, list) else []


def build_prompt_context(query: str = "", max_chars: int = 6500) -> str:
    sync_core_documents()
    registry = load_registry()
    mission = registry.get("mission", {}) if isinstance(registry, dict) else {}
    authority = registry.get("authority", {}) if isinstance(registry, dict) else {}
    lines = [
        "[MISSION CONTROL — reviewed owner context]",
        f"Mission: {mission.get('statement', 'Help humanity through accountable, human-controlled systems.')}",
        "Authority: JARVIS may research, plan, draft and report autonomously; consequential external actions require explicit owner approval.",
        "Never self-propagate, bypass security, hide persistence, or make binding decisions for people.",
    ]
    principles = mission.get("principles", []) if isinstance(mission, dict) else []
    if principles:
        lines.append("Principles:")
        lines.extend(f"- {item}" for item in principles[:8])
    if authority.get("requires_owner_approval"):
        lines.append("Owner approval required for: " + "; ".join(authority["requires_owner_approval"][:10]))
    sites = properties()
    if sites:
        lines.append("Known owner properties:")
        lines.extend(f"- {item.get('name')}: {item.get('url')} ({item.get('control')})" for item in sites[:12])
    memories = recall(query, limit=6)
    if memories:
        lines.append("Relevant durable memories:")
        lines.extend(f"- [{item['source']}] {item['text']}" for item in memories)
    result = "\n".join(lines)
    return result[:max_chars]


sync_core_documents()
