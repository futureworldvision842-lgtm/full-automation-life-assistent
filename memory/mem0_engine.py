"""
memory/mem0_engine.py
========================================================================
J.A.R.V.I.S. Cognitive Episodic & Semantic Memory Engine (Mem0-Style).
Provides persistent semantic recall, user preference extraction,
and contextual memories across trading history and PC workflows.
========================================================================
"""

import os
import sys
import json
import time
import math
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("mem0_engine")

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_STORE_FILE = BASE_DIR / "memory" / "mem0_store.jsonl"


class Mem0CognitiveMemory:
    """Semantic and episodic long-term memory engine."""

    def __init__(self):
        self.store_path = MEMORY_STORE_FILE
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.memories = self._load_all_memories()

    def _load_all_memories(self) -> List[Dict[str, Any]]:
        """Loads memories from persistent JSONL file."""
        if not self.store_path.exists():
            default_memories = [
                {
                    "id": "mem_001",
                    "category": "user_profile",
                    "content": "Master Muhammad Qureshi is the creator and owner of the J.A.R.V.I.S. Sovereign AI OS.",
                    "importance": 1.0,
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "id": "mem_002",
                    "category": "trading_rule",
                    "content": "Strict 90+ confluence required before MT5 demo order admission. Daily loss cap is 2.5% hard floor on FTMO #1514382598.",
                    "importance": 0.95,
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "id": "mem_003",
                    "category": "system_policy",
                    "content": "J.A.R.V.I.S. operates 100% locally with zero paid API costs, supporting Roman Urdu and English bilingual communication.",
                    "importance": 0.9,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
            self._save_all_memories(default_memories)
            return default_memories

        memories = []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        memories.append(json.loads(line.strip()))
        except Exception:
            pass
        return memories

    def _save_all_memories(self, memories: List[Dict[str, Any]]):
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                for m in memories:
                    f.write(json.dumps(m) + "\n")
        except Exception:
            pass

    def add_memory(self, content: str, category: str = "general", importance: float = 0.8) -> Dict[str, Any]:
        """Stores a new memory entry."""
        entry = {
            "id": f"mem_{int(time.time()*1000)}",
            "category": category,
            "content": content.strip(),
            "importance": importance,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.memories.append(entry)
        try:
            with open(self.store_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
        return entry

    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs fast semantic-token keyword similarity search."""
        query_words = set(query.lower().split())
        scored = []
        for m in self.memories:
            c_words = set(m.get("content", "").lower().split())
            intersection = query_words.intersection(c_words)
            score = len(intersection) * m.get("importance", 0.8)
            if score > 0 or len(query_words) == 0:
                scored.append((score, m))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]] if scored else self.memories[:limit]

    def get_context_injection(self, query: str = "") -> str:
        """Returns relevant context memories formatted for LLM system prompt."""
        matches = self.search_memories(query, limit=4)
        if not matches:
            return ""
        lines = ["=== RELEVANT LONG-TERM COGNITIVE MEMORIES (MEM0) ==="]
        for m in matches:
            lines.append(f"? [{m.get('category').upper()}]: {m.get('content')}")
        return "\n".join(lines)


_GLOBAL_MEM0_ENGINE: Optional[Mem0CognitiveMemory] = None


def get_mem0_engine() -> Mem0CognitiveMemory:
    global _GLOBAL_MEM0_ENGINE
    if _GLOBAL_MEM0_ENGINE is None:
        _GLOBAL_MEM0_ENGINE = Mem0CognitiveMemory()
    return _GLOBAL_MEM0_ENGINE
