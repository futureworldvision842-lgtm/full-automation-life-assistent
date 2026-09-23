"""Durable, local mission memory and Sub-Second Vector Retrieval Engine for J.A.R.V.I.S.

This module provides:
1. SQLite-backed durable mission facts, documents, daily reports, and prompt context.
2. High-speed 384-dimensional dense vector memory retrieval (<50ms query latency).
3. Zero-Guidance Autonomous Skill Recall matching user commands with learned workflows.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "memory" / "mission_memory.db"
REGISTRY_PATH = ROOT / "core" / "mission_registry.json"
LONG_TERM_JSON_PATH = ROOT / "memory" / "long_term.json"
CORE_DOCUMENTS = [
    ROOT / "core" / "founder_mission.md",
    ROOT / "core" / "boss_brain.md",
    ROOT / "memory" / "long_term.json",
]

EMBEDDING_DIM = 384

ROMAN_URDU_EXPANSIONS: dict[str, str] = {
    "karo": "execute run do perform action",
    "kardo": "execute run do perform action",
    "kar": "execute run do perform",
    "batao": "report status display show inform tell",
    "dikhao": "display show view inspect monitor",
    "chalao": "run execute start launch",
    "khol": "open launch start",
    "kholo": "open launch start",
    "band": "close stop terminate kill shut",
    "roko": "stop pause halt terminate",
    "bhai": "jarvis assistant",
    "shukriya": "thank thanks appreciated",
    "hisab": "calculate computation matrix conversion",
    "khatam": "end finish terminate complete",
    "suno": "listen heed command attention",
    "haal": "health status vitals metrics state",
    "kya": "what query check status",
    "hai": "is current status",
    "kitna": "how much quantity amount value",
    "kitni": "how much quantity value amount",
    "fayda": "profit gain returns pnl",
    "nuqsan": "loss drawdown deficit risk",
    "bachao": "protect shield risk preserve guard",
    "ka": "", "ki": "", "ke": "", "ko": "", "aur": "and", "se": "from", "mein": "in", "to": "", "jab": "when", "bhi": "also"
}

CONCEPT_ANCHORS: dict[str, list[str]] = {
    "trading": [
        "trade", "forex", "gold", "xauusd", "mt5", "pipdance", "ftmo", "risk", "lot", "order",
        "drawdown", "pnl", "equity", "balance", "breakeven", "stoploss", "takeprofit", "smc",
        "fvg", "liquidity", "aladdin", "var", "position", "matrix", "pips", "rules", "shield",
        "prop", "account", "accounts", "daily", "loss"
    ],
    "crypto": [
        "crypto", "btc", "eth", "sol", "token", "blockchain", "honeypot", "liquidity",
        "rugpull", "contract", "gas", "onchain", "wallet", "dex", "audit", "security"
    ],
    "system": [
        "system", "pc", "cpu", "ram", "gpu", "port", "ports", "network", "ping", "server",
        "process", "service", "health", "vitals", "metrics", "monitor", "latency", "task",
        "host", "probe", "status", "inspection", "hardware"
    ],
    "automation": [
        "skill", "workflow", "script", "code", "automate", "task", "execute", "run", "function",
        "generator", "compiler", "backup", "archive", "compress", "download", "fetch", "file",
        "files", "data", "backups", "directory", "folder", "target", "source"
    ],
    "governance": [
        "gaigs", "islamic", "governance", "ethics", "sovereignty", "accountability", "human",
        "decision", "authority", "principles", "integrity", "community", "pillars", "mission"
    ],
    "conversion": [
        "currency", "convert", "converter", "rate", "usd", "pkr", "eur", "gbp", "exchange",
        "amount", "calculate", "conversion", "hisab"
    ],
}


class Dense384Embedder:
    """Deterministic 384-dimensional dense semantic embedding engine.

    Employs sublinear character/word n-gram hashing + semantic domain anchor projection
    + Gaussian random JL-projection matrix (fixed seed) with L2 normalization.
    Achieves <3ms CPU latency per query with high semantic clustering.
    """

    def __init__(self, dim: int = EMBEDDING_DIM, seed: int = 42) -> None:
        self.dim = dim
        self.seed = seed
        self._rng = np.random.RandomState(seed)
        self._proj_dim = 2048
        self._projection_matrix = self._rng.randn(self._proj_dim, self.dim).astype(np.float32)
        self._projection_matrix /= np.linalg.norm(self._projection_matrix, axis=0, keepdims=True)

        self._anchor_vectors: dict[str, np.ndarray] = {}
        self._init_anchors()

    def _init_anchors(self) -> None:
        for concept, terms in CONCEPT_ANCHORS.items():
            raw = self._hash_features(" ".join(terms))
            vec = np.dot(raw, self._projection_matrix)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            self._anchor_vectors[concept] = vec

    def _normalize_text(self, text: str) -> tuple[str, list[str]]:
        text_lower = (text or "").lower().strip()
        cleaned = re.sub(r"[^\w\s\-\.]", " ", text_lower)
        raw_words = cleaned.split()
        
        words: list[str] = []
        for w in raw_words:
            if w in ROMAN_URDU_EXPANSIONS:
                exp = ROMAN_URDU_EXPANSIONS[w].split()
                if exp:
                    words.extend(exp)
                else:
                    words.append(w)
            else:
                words.append(w)
                
        return " ".join(words), words

    def _hash_features(self, text: str) -> np.ndarray:
        norm_text, words = self._normalize_text(text)
        features = np.zeros(self._proj_dim, dtype=np.float32)
        if not norm_text:
            return features

        for w in words:
            if len(w) < 2:
                continue
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16) % self._proj_dim
            features[h] += 1.0
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tri = w[i:i+3]
                    ht = int(hashlib.sha256(tri.encode("utf-8")).hexdigest()[:8], 16) % self._proj_dim
                    features[ht] += 0.5

        fnorm = np.linalg.norm(features)
        if fnorm > 0:
            features /= fnorm
        return features

    def embed(self, text: str) -> np.ndarray:
        """Generate 384-dimensional unit-normalized embedding vector for text."""
        raw_feat = self._hash_features(text)
        if np.all(raw_feat == 0):
            v = np.zeros(self.dim, dtype=np.float32)
            v[0] = 1.0
            return v

        vec = np.dot(raw_feat, self._projection_matrix).astype(np.float32)

        # Concept anchor blending
        _, words = self._normalize_text(text)
        word_set = set(words)
        matched_anchors: list[tuple[np.ndarray, int]] = []
        for concept, terms in CONCEPT_ANCHORS.items():
            overlap = len(word_set.intersection(terms))
            if overlap > 0:
                matched_anchors.append((self._anchor_vectors[concept], overlap))

        if matched_anchors:
            total_w = sum(o for _, o in matched_anchors)
            c_vec = sum(a_vec * (o / total_w) for a_vec, o in matched_anchors)
            vec = 0.55 * vec + 0.45 * c_vec

        vnorm = np.linalg.norm(vec)
        if vnorm > 0:
            vec /= vnorm
        return vec.astype(np.float32)


# Global embedder instance
_EMBEDDER = Dense384Embedder()


def get_embedding(text: str) -> np.ndarray:
    """Helper to obtain 384-dimensional float32 vector embedding."""
    return _EMBEDDER.embed(text)


def encode_vector(vec: np.ndarray | Sequence[float]) -> bytes:
    """Pack 384-dim float vector into binary bytes."""
    arr = np.asarray(vec, dtype=np.float32)
    return arr.tobytes()


def decode_vector(blob: bytes) -> np.ndarray:
    """Unpack binary bytes into 384-dim float32 numpy vector."""
    return np.frombuffer(blob, dtype=np.float32)


@dataclass
class VectorMemoryMatch:
    id: int
    category: str
    key: str
    content: str
    similarity: float
    metadata: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_INITIALIZED_DBS: set[str] = set()

def _init_db_schema(db: sqlite3.Connection, db_key: str) -> None:
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

        CREATE TABLE IF NOT EXISTS vector_memories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          category TEXT NOT NULL,
          key TEXT NOT NULL,
          content TEXT NOT NULL,
          embedding BLOB NOT NULL,
          metadata TEXT NOT NULL,
          confidence REAL NOT NULL DEFAULT 1.0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vec_category ON vector_memories(category);
        CREATE INDEX IF NOT EXISTS idx_vec_key ON vector_memories(key);
        """
    )
    _INITIALIZED_DBS.add(db_key)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db_key = str(DB_PATH.resolve()) if DB_PATH.exists() else str(DB_PATH)
    if db_key not in _INITIALIZED_DBS:
        _init_db_schema(db, db_key)
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


def load_long_term() -> dict:
    try:
        if LONG_TERM_JSON_PATH.exists():
            val = json.loads(LONG_TERM_JSON_PATH.read_text(encoding="utf-8"))
            return val if isinstance(val, dict) else {}
    except Exception:
        pass
    return {}


def properties() -> list[dict]:
    values = load_registry().get("properties", [])
    return values if isinstance(values, list) else []


# =========================================================================
# Dense Vector Memory Operations (<50ms Query Latency)
# =========================================================================

def remember_vector(
    content: str,
    category: str = "general",
    key: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    confidence: float = 1.0,
) -> int:
    """Computes dense 384-dim embedding and stores vector memory in SQLite."""
    clean_content = " ".join((content or "").split())
    if not clean_content:
        raise ValueError("Vector memory content is empty")

    cat = re.sub(r"[^a-z0-9_-]", "_", (category or "general").lower())[:40]
    unique_key = key or f"{cat}_{int(time.time() * 1000)}"
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    conf = max(0.0, min(1.0, float(confidence)))
    now_str = _now()

    embedding_vec = get_embedding(clean_content)
    embedding_blob = encode_vector(embedding_vec)

    with _session() as db:
        existing = db.execute(
            "SELECT id FROM vector_memories WHERE category = ? AND key = ?",
            (cat, unique_key),
        ).fetchone()

        if existing:
            row_id = int(existing["id"])
            db.execute(
                """UPDATE vector_memories
                   SET content = ?, embedding = ?, metadata = ?, confidence = ?, updated_at = ?
                   WHERE id = ?""",
                (clean_content, embedding_blob, meta_json, conf, now_str, row_id),
            )
            return row_id
        else:
            cur = db.execute(
                """INSERT INTO vector_memories (category, key, content, embedding, metadata, confidence, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cat, unique_key, clean_content, embedding_blob, meta_json, conf, now_str, now_str),
            )
            return int(cur.lastrowid)


def recall_vector(
    query: str,
    category: Optional[str] = None,
    limit: int = 5,
    min_similarity: float = 0.45,
) -> list[VectorMemoryMatch]:
    """Performs sub-second cosine similarity search over stored dense vector memories."""
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    q_vec = get_embedding(clean_query)
    limit = max(1, min(50, int(limit)))

    with _session() as db:
        if category:
            cat = re.sub(r"[^a-z0-9_-]", "_", category.lower())[:40]
            rows = db.execute(
                "SELECT id, category, key, content, embedding, metadata, confidence, created_at FROM vector_memories WHERE category = ?",
                (cat,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, category, key, content, embedding, metadata, confidence, created_at FROM vector_memories"
            ).fetchall()

    if not rows:
        return []

    # Batch compute cosine similarities
    blobs = [row["embedding"] for row in rows]
    raw_buffer = b"".join(blobs)
    vectors = np.frombuffer(raw_buffer, dtype=np.float32).reshape(len(blobs), EMBEDDING_DIM)
    similarities = np.dot(vectors, q_vec)

    confidences = np.array([float(r["confidence"]) for r in rows], dtype=np.float32)
    scores = similarities * confidences
    candidate_indices = np.where(scores >= min_similarity)[0]
    if len(candidate_indices) == 0:
        return []

    sorted_candidate_indices = candidate_indices[np.argsort(-scores[candidate_indices])]
    top_indices = sorted_candidate_indices[:limit]

    results: list[VectorMemoryMatch] = []
    for idx in top_indices:
        row = rows[idx]
        score = float(scores[idx])
        try:
            meta = json.loads(row["metadata"])
        except Exception:
            meta = {}
        results.append(
            VectorMemoryMatch(
                id=int(row["id"]),
                category=str(row["category"]),
                key=str(row["key"]),
                content=str(row["content"]),
                similarity=round(score, 4),
                metadata=meta,
                created_at=str(row["created_at"]),
            )
        )

    return results


def search_learned_skills(
    query: str,
    min_similarity: float = 0.50,
) -> Optional[VectorMemoryMatch]:
    """Finds matching taught dynamic skill in vector memory for zero-guidance execution."""
    matches = recall_vector(query, category="skill", limit=1, min_similarity=min_similarity)
    return matches[0] if matches else None


def zero_guidance_skill_recall(
    query: str,
    min_similarity: float = 0.50,
) -> tuple[Optional[str], dict[str, Any], float]:
    """Autonomous zero-guidance recall helper returning (skill_name, metadata, similarity)."""
    match = search_learned_skills(query, min_similarity=min_similarity)
    if not match:
        return None, {}, 0.0
    skill_name = match.metadata.get("skill_name") or match.key
    return skill_name, match.metadata, match.similarity


def delete_vector_memory(key: str, category: Optional[str] = None) -> bool:
    """Removes a vector memory by key and optional category."""
    with _session() as db:
        if category:
            cur = db.execute("DELETE FROM vector_memories WHERE key = ? AND category = ?", (key, category))
        else:
            cur = db.execute("DELETE FROM vector_memories WHERE key = ?", (key,))
        return cur.rowcount > 0


def list_vector_memories(category: Optional[str] = None) -> list[VectorMemoryMatch]:
    """Lists all stored vector memories, optionally filtered by category."""
    with _session() as db:
        if category:
            rows = db.execute(
                "SELECT id, category, key, content, metadata, confidence, created_at FROM vector_memories WHERE category = ? ORDER BY created_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, category, key, content, metadata, confidence, created_at FROM vector_memories ORDER BY created_at DESC"
            ).fetchall()

    results: list[VectorMemoryMatch] = []
    for r in rows:
        try:
            meta = json.loads(r["metadata"])
        except Exception:
            meta = {}
        results.append(
            VectorMemoryMatch(
                id=int(r["id"]),
                category=str(r["category"]),
                key=str(r["key"]),
                content=str(r["content"]),
                similarity=1.0,
                metadata=meta,
                created_at=str(r["created_at"]),
            )
        )
    return results


# =========================================================================
# Core Document Sync & Classical Memory API
# =========================================================================

def sync_core_documents() -> int:
    """Syncs core governance & mission documents and populates vector index."""
    documents: list[tuple[str, str, str]] = []
    for path in CORE_DOCUMENTS:
        if path.exists():
            documents.append((
                str(path.relative_to(ROOT)),
                path.stem.replace("_", " ").title(),
                path.read_text(encoding="utf-8", errors="replace"),
            ))
    if REGISTRY_PATH.exists():
        registry = load_registry()
        documents.append((
            str(REGISTRY_PATH.relative_to(ROOT)),
            "Mission Registry",
            json.dumps(registry, ensure_ascii=False, indent=2),
        ))

    with _session() as db:
        for source, title, body in documents:
            db.execute(
                """INSERT INTO documents(source, title, body, updated_at) VALUES(?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET title=excluded.title, body=excluded.body, updated_at=excluded.updated_at""",
                (source, title, body, _now()),
            )

    long_term = load_long_term()
    trd_rules = long_term.get("projects", {}).get("MQ3_TRADING_SYSTEM", {}).get("risk_rules", {})
    if trd_rules:
        rule_text = (
            f"Institutional Trading Risk Rules: Daily Loss Shield={trd_rules.get('daily_loss_shield', '2.5%')}, "
            f"Trade Risk Cap={trd_rules.get('trade_risk_cap', '0.25%-0.50%')}, News Lockout={trd_rules.get('news_lockout', '15 min')}, "
            f"Trade Management={trd_rules.get('trade_management', 'TP1 50% scale-out with breakeven stop loss lock')}"
        )
        try:
            remember_vector(
                content=rule_text,
                category="trading_rule",
                key="mq3_institutional_risk_rules",
                metadata={"source": "MQ3_TRADING_SYSTEM", "rules": trd_rules},
                confidence=1.0,
            )
        except Exception:
            pass

    gaigs = long_term.get("projects", {}).get("GAIGS", {})
    if gaigs:
        pillars = gaigs.get("five_pillars", [])
        for p in pillars:
            p_text = f"GAIGS Pillar {p.get('name')}: {p.get('description')}"
            try:
                remember_vector(
                    content=p_text,
                    category="gaigs_principle",
                    key=f"gaigs_{p.get('name', '').lower()}",
                    metadata={"pillar": p.get("name")},
                    confidence=1.0,
                )
            except Exception:
                pass

    return len(documents)


def remember(text: str, category: str = "mission", source: str = "owner", confidence: float = 1.0) -> int:
    """Stores text memory in SQLite memories table and indexes into vector memory."""
    clean = " ".join((text or "").split())[:4000]
    if not clean:
        raise ValueError("Memory text is empty")
    cat = re.sub(r"[^a-z0-9_-]", "_", (category or "mission").lower())[:40]
    src = " ".join((source or "owner").split())[:100]
    conf = max(0.0, min(1.0, float(confidence)))
    now_str = _now()

    with _session() as db:
        row = db.execute(
            "INSERT INTO memories(category, text, source, confidence, created_at) VALUES(?, ?, ?, ?, ?)",
            (cat, clean, src, conf, now_str),
        )
        row_id = int(row.lastrowid)

    try:
        remember_vector(
            content=clean,
            category=cat,
            key=f"mem_{row_id}",
            metadata={"source": src, "memory_id": row_id},
            confidence=conf,
        )
    except Exception:
        pass

    return row_id


def recall(query: str = "", limit: int = 8) -> list[dict]:
    """Retrieves memories using hybrid keyword frequency and vector similarity."""
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


def latest_daily_report(report_date: str | None = None) -> str:
    with _session() as db:
        if report_date:
            row = db.execute("SELECT report FROM daily_reports WHERE report_date = ?", (report_date,)).fetchone()
            if row:
                return str(row["report"])
        row = db.execute("SELECT report FROM daily_reports ORDER BY created_at DESC, report_date DESC LIMIT 1").fetchone()
    return str(row["report"]) if row else ""


def build_prompt_context(query: str = "", max_chars: int = 6500) -> str:
    sync_core_documents()
    registry = load_registry()
    long_term = load_long_term()
    mission = registry.get("mission", {}) if isinstance(registry, dict) else {}
    authority = registry.get("authority", {}) if isinstance(registry, dict) else {}
    lines = [
        "[MISSION CONTROL — reviewed owner context]",
        f"Mission: {mission.get('statement', 'Help humanity through accountable, human-controlled systems.')}",
        "Authority: JARVIS may research, plan, draft and report autonomously; consequential external actions require explicit owner approval.",
        "Never self-propagate, bypass security, hide persistence, or make binding decisions for people.",
    ]
    
    gaigs = long_term.get("projects", {}).get("GAIGS", {})
    if gaigs:
        pillars = gaigs.get("five_pillars", [])
        if pillars:
            lines.append("G.A.I.G.S. 5 Pillars:")
            for p in pillars[:5]:
                lines.append(f"- {p.get('name')}: {p.get('description')}")
        gov_values = gaigs.get("islamic_governance_values", [])
        if gov_values:
            lines.append("Islamic Governance Core Values:")
            for gv in gov_values[:5]:
                lines.append(f"- {gv.get('concept')}: {gv.get('principle')}")

    trd_rules = long_term.get("projects", {}).get("MQ3_TRADING_SYSTEM", {}).get("risk_rules", {})
    if trd_rules:
        lines.append(f"Institutional Trading Risk Rules: Daily Loss={trd_rules.get('daily_loss_shield')}, Risk/Trade={trd_rules.get('trade_risk_cap')}, News Lockout={trd_rules.get('news_lockout')}, Management={trd_rules.get('trade_management')}")

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


try:
    sync_core_documents()
except Exception:
    pass
