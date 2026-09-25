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


    def learn_from_interaction(
        self,
        text: str,
        role: str = "master",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Cognitive Ingestion: Automatically parses natural language interactions,
        extracts entity relationship triples, and registers persistent vector memories.
        Handles both English and Roman Urdu patterns.
        """
        if not text or len(text.strip()) < 3:
            return {"ok": False, "reason": "empty_text"}

        meta = metadata or {}
        now = time.time()
        extracted_triples: List[Tuple[str, str, str]] = []

        # 1. Pattern Extraction for Subject-Predicate-Object
        # Invariants & Preferences
        pref_match = re.search(r"(?:remember that|note that|hamesha|yaad rakhna)\s+([^,.]+?)\s+(?:is|ko|par|has|must be|chahiye)\s+([^,.]+)", text, re.IGNORECASE)
        if pref_match:
            s, o = pref_match.group(1).strip(), pref_match.group(2).strip()
            extracted_triples.append((s, "preference", o))

        # Risk & Account constraints
        risk_match = re.search(r"(?:risk|cap|ceiling|limit)\s+(?:is|hai|set to|capped at)\s+([0-9.]+%?|\$[0-9,.]+)", text, re.IGNORECASE)
        if risk_match:
            val = risk_match.group(1)
            extracted_triples.append(("RiskGovernor", "enforces_limit", val))

        # Symbol / Asset directives
        sym_match = re.search(r"\b(XAUUSD|BTCUSD|EURUSD|GBPUSD|USDJPY|SOLUSD|USOIL)\b", text, re.IGNORECASE)
        if sym_match:
            sym = sym_match.group(1).upper()
            action_match = re.search(r"\b(buy|sell|long|short|bullish|bearish|scalp)\b", text, re.IGNORECASE)
            act = action_match.group(1).lower() if action_match else "monitored"
            extracted_triples.append((sym, "operator_bias", act))

        # Mobile & PC unification assertions
        if any(w in text.lower() for w in ["mobile", "phone", "apk", "android"]):
            extracted_triples.append(("MobileCompanion", "linked_to", "MasterWorkstation"))

        # 2. Persist Vector Memory
        category = meta.get("category", "operator_directive" if role == "master" else "dialogue_memory")
        tags = [role, "conversation"]
        if sym_match:
            tags.append(sym_match.group(1).upper())
        if "risk" in text.lower():
            tags.append("risk")

        mem_id = self.remember(
            content=text,
            category=category,
            metadata={**meta, "role": role, "timestamp": now},
            tags=tags,
        )

        # 3. Persist Knowledge Triples
        triple_ids = []
        for s, p, o in extracted_triples:
            tid = self.add_knowledge_triple(s, p, o, confidence=0.92, source_id=mem_id)
            triple_ids.append(tid)

        return {
            "ok": True,
            "memory_id": mem_id,
            "category": category,
            "triples_extracted": len(triple_ids),
            "triples": [{"subject": s, "predicate": p, "object": o} for s, p, o in extracted_triples],
            "stored_at": now,
        }

    def auto_ingest_trade_execution(self, trade_data: Dict[str, Any]) -> str:
        """
        Automatically ingests trade dispatches or closed orders into cognitive memory,
        updating lessons and the knowledge graph in real-time.
        """
        symbol = str(trade_data.get("symbol", "UNKNOWN")).upper()
        pnl = float(trade_data.get("pnl", 0.0))
        outcome = "WIN" if pnl >= 0 else "LOSS"
        order_type = trade_data.get("order_type", trade_data.get("type", "BUY")).upper()
        lots = trade_data.get("lots", trade_data.get("volume", 0.1))
        rr = trade_data.get("rr", 2.5)
        account = trade_data.get("account_id", "FundingPips #40000294403")

        desc = f"Executed {order_type} on {symbol} ({lots} lots) under {account}. R:R: {rr}. PnL: ${pnl:+.2f}."
        rule = trade_data.get("rule", "Enforce dynamic +1.0R breakeven and strictly cap risk <= 0.75%")

        lesson_id = self.record_market_lesson(
            symbol=symbol,
            lesson_type="AUTOMATED_EXECUTION",
            description=desc,
            outcome=outcome,
            rule_deduced=rule,
        )

        # Connect account to symbol in KG
        self.add_knowledge_triple(str(account), "traded_asset", symbol, confidence=1.0, source_id=lesson_id)
        self.add_knowledge_triple(symbol, "latest_outcome", f"{outcome} (${pnl:+.2f})", confidence=1.0, source_id=lesson_id)

        return lesson_id

    def get_knowledge_graph_d3(self, limit: int = 80) -> Dict[str, Any]:
        """
        Exports the knowledge graph in D3 / Three.js node-link format:
        {'nodes': [{'id': '...', 'name': '...', 'group': '...'}], 'links': [{'source': '...', 'target': '...', 'label': '...'}]}
        """
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT subject, predicate, object, confidence FROM knowledge_graph ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()

        nodes_dict: Dict[str, Dict[str, Any]] = {}
        links: List[Dict[str, Any]] = []

        def _infer_group(name: str) -> str:
            lower = name.lower()
            if "qureshi" in lower or "master" in lower:
                return "Master"
            elif any(s in lower for s in ["xauusd", "btcusd", "eurusd", "gbpusd", "solusd", "fundingpips", "ftmo"]):
                return "Trading"
            elif "risk" in lower or "limit" in lower or "cap" in lower:
                return "RiskGovernor"
            elif "mobile" in lower or "phone" in lower or "apk" in lower:
                return "MobileDevice"
            elif "jarvis" in lower or "agent" in lower or "brain" in lower:
                return "JarvisCore"
            return "General"

        for r in rows:
            s, p, o, conf = r["subject"], r["predicate"], r["object"], r["confidence"]
            if s not in nodes_dict:
                nodes_dict[s] = {"id": s, "name": s, "group": _infer_group(s), "val": 12}
            else:
                nodes_dict[s]["val"] += 2

            if o not in nodes_dict:
                nodes_dict[o] = {"id": o, "name": o, "group": _infer_group(o), "val": 8}
            else:
                nodes_dict[o]["val"] += 1

            links.append({
                "source": s,
                "target": o,
                "label": p,
                "confidence": conf,
            })

        return {
            "nodes": list(nodes_dict.values()),
            "links": links,
            "total_nodes": len(nodes_dict),
            "total_edges": len(links),
        }

    def expand_entity_neighborhood(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Expands 1-hop and 2-hop graph neighborhood around a query entity."""
        triples_1 = self.query_knowledge_graph(subject=entity_name) + self.query_knowledge_graph(object_=entity_name)
        connected_entities = set()
        for t in triples_1:
            connected_entities.add(t.subject)
            connected_entities.add(t.object)

        triples_2 = []
        if depth >= 2:
            for ent in list(connected_entities)[:10]:
                if ent != entity_name:
                    triples_2.extend(self.query_knowledge_graph(subject=ent))

        all_triples = {f"{t.subject}|{t.predicate}|{t.object}": t for t in (triples_1 + triples_2)}.values()
        return {
            "entity": entity_name,
            "triples": [t.to_dict() for t in all_triples],
            "total_relations": len(all_triples),
        }


_global_brain: Optional[SupermemoryBrain] = None

def get_supermemory_brain() -> SupermemoryBrain:
    global _global_brain
    if _global_brain is None:
        _global_brain = SupermemoryBrain()
    return _global_brain

