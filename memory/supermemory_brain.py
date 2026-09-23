"""
memory/supermemory_brain.py
============================
Supermemory Cognitive Brain for J.A.R.V.I.S.
Inspired by supermemoryai/supermemory:
  1. Persistent SQLite WAL Vector & Semantic Memory Store.
  2. Knowledge Graph (Subject-Predicate-Object) Relationship Engine.
  3. Market Lessons & Trade Performance Memory with Sub-500ms Offline Retrieval.
  4. Master Muhammad Qureshi's Sovereign Context and Preference Index.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import sqlite3
import json
import time
import math
import re
import os
from pathlib import Path
import logging

logger = logging.getLogger("Jarvis.Supermemory")

_BASE_DIR = Path(__file__).resolve().parent.parent
_SUPERMEMORY_DB = _BASE_DIR / "memory" / "supermemory.db"

# Dimension for local pure-python dense feature embeddings
EMBEDDING_DIM = 128

def _compute_offline_embedding(text: str) -> List[float]:
    """
    Computes a deterministic, normalized 128-dimensional semantic hash embedding
    without external cloud API or heavyweight torch dependencies.
    Runs in sub-millisecond time.
    """
    if not text:
        return [0.0] * EMBEDDING_DIM
    
    vec = [0.0] * EMBEDDING_DIM
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return [0.0] * EMBEDDING_DIM

    for idx, token in enumerate(tokens):
        # Rolling polynomial hash into dimension slots
        h = 0
        for ch in token:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        slot = h % EMBEDDING_DIM
        weight = 1.0 / (1.0 + math.log(1.0 + idx))
        vec[slot] += weight

        # Also encode bigram context if available
        if idx > 0:
            prev = tokens[idx - 1]
            bigram_h = (h * 37 + hash(prev)) & 0xFFFFFFFF
            vec[bigram_h % EMBEDDING_DIM] += weight * 0.75

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [round(x / norm, 6) for x in vec]
    return vec

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Cosine similarity between two normalized vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(vec1, vec2))))


@dataclass
class MemoryRecord:
    memory_id: str
    category: str
    content: str
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: float
    updated_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeTriple:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source_id: Optional[str] = None
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SupermemoryBrain:
    """
    Sovereign cognitive memory brain featuring vector storage,
    knowledge graph indexing, and sub-500ms semantic retrieval.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _SUPERMEMORY_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._seed_sovereign_invariants()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high-concurrency sub-500ms reads
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_database(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    tags TEXT,
                    embedding_json TEXT,
                    created_at REAL,
                    updated_at REAL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL DEFAULT 0
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source_id TEXT,
                    created_at REAL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_sub ON knowledge_graph(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_pred ON knowledge_graph(predicate);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_obj ON knowledge_graph(object);")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_lessons (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    lesson_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    outcome TEXT,
                    rule_deduced TEXT,
                    created_at REAL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_sym ON market_lessons(symbol);")

    def _seed_sovereign_invariants(self):
        """Seed foundational knowledge for Master Muhammad Qureshi."""
        invariants = [
            ("Master Muhammad Qureshi", "is_sole_owner_of", "J.A.R.V.I.S. Command Center"),
            ("Master Muhammad Qureshi", "phone_number", "+923468053268"),
            ("Master Muhammad Qureshi", "official_email", "futureworldvision842@gmail.com"),
            ("FundingPips #40000294403", "max_risk_cap", "0.75% ($750)"),
            ("J.A.R.V.I.S.", "enforces_min_rr", "2.5:1"),
            ("J.A.R.V.I.S.", "enforces_news_blackout", "15_minutes"),
        ]
        for s, p, o in invariants:
            self.add_knowledge_triple(s, p, o, confidence=1.0, source_id="SOVEREIGN_SEED")

    def remember(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """Stores a persistent cognitive memory with its semantic vector."""
        now = time.time()
        m_id = memory_id or f"mem_{int(now * 1000)}_{os.urandom(3).hex()}"
        meta = metadata or {}
        tag_list = tags or []
        embedding = _compute_offline_embedding(content)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO memories (id, category, content, metadata_json, tags, embedding_json, created_at, updated_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content=excluded.content,
                    metadata_json=excluded.metadata_json,
                    tags=excluded.tags,
                    embedding_json=excluded.embedding_json,
                    updated_at=excluded.updated_at
            """, (
                m_id,
                category,
                content,
                json.dumps(meta),
                json.dumps(tag_list),
                json.dumps(embedding),
                now,
                now,
                now,
            ))
        return m_id

    def recall(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.20,
    ) -> List[MemoryRecord]:
        """
        Retrieves top relevant memories using hybrid semantic vector cosine
        and keyword token matching in sub-500ms.
        """
        start_t = time.perf_counter()
        query_vec = _compute_offline_embedding(query)
        query_tokens = set(re.findall(r"\w+", query.lower()))

        results: List[MemoryRecord] = []

        with self._get_connection() as conn:
            if category:
                cur = conn.execute("SELECT * FROM memories WHERE category = ?", (category,))
            else:
                cur = conn.execute("SELECT * FROM memories")
            rows = cur.fetchall()

        now = time.time()
        scored_memories = []

        for row in rows:
            content = row["content"]
            emb_raw = row["embedding_json"]
            row_vec = json.loads(emb_raw) if emb_raw else []
            
            # Vector cosine similarity
            vec_sim = _cosine_similarity(query_vec, row_vec)

            # Keyword lexical overlap
            content_tokens = set(re.findall(r"\w+", content.lower()))
            overlap = len(query_tokens.intersection(content_tokens))
            lex_score = overlap / max(1, len(query_tokens))

            # Hybrid score (60% vector + 40% lexical)
            hybrid_score = (0.60 * vec_sim) + (0.40 * lex_score)

            if hybrid_score >= threshold or overlap > 0:
                scored_memories.append((hybrid_score, row))

        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        # Build records and update access count
        ids_to_bump = []
        for score, row in scored_memories[:limit]:
            record = MemoryRecord(
                memory_id=row["id"],
                category=row["category"],
                content=row["content"],
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                tags=json.loads(row["tags"]) if row["tags"] else [],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                access_count=row["access_count"] + 1,
                last_accessed=now,
                score=round(score, 4),
            )
            results.append(record)
            ids_to_bump.append(row["id"])

        if ids_to_bump:
            with self._get_connection() as conn:
                conn.executemany(
                    "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                    [(now, mid) for mid in ids_to_bump]
                )

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        logger.debug("Supermemory recall for '%s' returned %d items in %.2f ms", query, len(results), elapsed_ms)
        return results

    # =========================================================================
    # Knowledge Graph Operations
    # =========================================================================
    def add_knowledge_triple(
        self,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 1.0,
        source_id: Optional[str] = None,
    ) -> int:
        """Inserts an entity relationship triple into the knowledge graph."""
        with self._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO knowledge_graph (subject, predicate, object, confidence, source_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (subject, predicate, object_, confidence, source_id, time.time()))
            return cur.lastrowid

    def query_knowledge_graph(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_: Optional[str] = None,
    ) -> List[KnowledgeTriple]:
        """Queries knowledge triples with flexible wildcards."""
        query = "SELECT subject, predicate, object, confidence, source_id, created_at FROM knowledge_graph WHERE 1=1"
        params = []
        if subject:
            query += " AND subject LIKE ?"
            params.append(f"%{subject}%")
        if predicate:
            query += " AND predicate LIKE ?"
            params.append(f"%{predicate}%")
        if object_:
            query += " AND object LIKE ?"
            params.append(f"%{object_}%")

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()

        return [
            KnowledgeTriple(
                subject=r["subject"],
                predicate=r["predicate"],
                object=r["object"],
                confidence=r["confidence"],
                source_id=r["source_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # =========================================================================
    # Market Lessons & Daily Learnings
    # =========================================================================
    def record_market_lesson(
        self,
        symbol: str,
        lesson_type: str,
        description: str,
        outcome: str = "WIN",
        rule_deduced: str = "",
    ) -> str:
        """Records a post-trade review or market dynamic insight."""
        now = time.time()
        lesson_id = f"lesson_{symbol}_{int(now)}_{os.urandom(2).hex()}"
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO market_lessons (id, symbol, lesson_type, description, outcome, rule_deduced, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lesson_id, symbol, lesson_type, description, outcome, rule_deduced, now))
        
        # Also mirror into vector memories and KG
        self.remember(
            content=f"Market lesson on {symbol} ({outcome}): {description} Rule: {rule_deduced}",
            category="trading_lesson",
            metadata={"symbol": symbol, "outcome": outcome, "lesson_type": lesson_type},
            tags=[symbol, "lesson", outcome],
            memory_id=f"mem_{lesson_id}",
        )
        if rule_deduced:
            self.add_knowledge_triple(symbol, "requires_rule", rule_deduced, confidence=0.95, source_id=lesson_id)

        return lesson_id

    def get_recent_lessons(self, symbol: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches the latest trading lessons for morning briefings or trade prep."""
        with self._get_connection() as conn:
            if symbol:
                cur = conn.execute(
                    "SELECT * FROM market_lessons WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                    (symbol, limit)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM market_lessons ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]


_global_brain: Optional[SupermemoryBrain] = None

def get_supermemory_brain() -> SupermemoryBrain:
    global _global_brain
    if _global_brain is None:
        _global_brain = SupermemoryBrain()
    return _global_brain
