"""
memory/dual_tier_memory.py — Dual-Tier Cognitive Memory Engine for J.A.R.V.I.S.
==============================================================================
Implements:
1. Tier 1: Short-Term Working Memory (Transient / Ephemeral):
   - Fast rolling in-memory buffer + runtime/short_term_memory.json.
   - Holds 24h transient events, active discussion topics, intraday targets, and working scratchpads.
   - Automatic lifecycle expiration: items older than 24h or exceeding turn limits are pruned.
2. Tier 2: Permanent Long-Term Memory (Durable SQLite + JSON):
   - SQLite backed (memory/long_term_memory.db) + synchronized long_term.json.
   - Stores immutable owner rules, persistent identity/preferences, verified technical strategies,
     learned bug fixes, and system facts.
3. Intelligent Promotion Classifier:
   - Automatically detects whether user statements belong to transient chatter or permanent rules:
     * "Aaj gold 2650 jayega" -> Tier 1 (Ephemeral intraday target)
     * "Hamaisha gold par 20 pips se zyada ka risk mat lena" -> Tier 2 (Promoted to Permanent Rule)
4. Context Injection:
   - Merges both tiers into a compact, relevance-filtered memory envelope for reasoning engines.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("jarvis.memory.dual_tier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _BASE_DIR / "runtime"
_MEMORY_DIR = _BASE_DIR / "memory"

_SHORT_TERM_FILE = _RUNTIME_DIR / "short_term_memory.json"
_LONG_TERM_DB = _MEMORY_DIR / "long_term_memory.db"
_LONG_TERM_JSON = _MEMORY_DIR / "long_term.json"

DEFAULT_TTL_HOURS = 24
MAX_WORKING_TURNS = 40


# ==============================================================================
# TIER 1: SHORT-TERM WORKING MEMORY (TRANSIENT)
# ==============================================================================

@dataclass
class WorkingTurn:
    turn_id: str
    role: str  # "user" or "jarvis"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    topic: Optional[str] = None
    transient_data: Dict[str, Any] = field(default_factory=dict)


class ShortTermWorkingMemory:
    """
    Manages transient session state with automatic 24-hour expiration.
    """

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.ttl_hours = ttl_hours
        self._lock = threading.Lock()
        self.turns: List[WorkingTurn] = []
        self.active_context: Dict[str, Any] = {}
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        with self._lock:
            if _SHORT_TERM_FILE.exists():
                try:
                    data = json.loads(_SHORT_TERM_FILE.read_text(encoding="utf-8"))
                    self.active_context = data.get("active_context", {})
                    raw_turns = data.get("turns", [])
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=self.ttl_hours)
                    loaded = []
                    for t in raw_turns:
                        try:
                            ts = datetime.fromisoformat(t.get("timestamp", ""))
                            if ts >= cutoff:
                                loaded.append(WorkingTurn(
                                    turn_id=t.get("turn_id", ""),
                                    role=t.get("role", "user"),
                                    content=t.get("content", ""),
                                    timestamp=t.get("timestamp", ""),
                                    topic=t.get("topic"),
                                    transient_data=t.get("transient_data", {})
                                ))
                        except Exception:
                            continue
                    self.turns = loaded[-MAX_WORKING_TURNS:]
                except Exception as e:
                    logger.debug("Could not read short term memory: %s", e)

    def _save(self) -> None:
        with self._lock:
            try:
                data = {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "active_context": self.active_context,
                    "turns": [asdict(t) for t in self.turns]
                }
                _SHORT_TERM_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.error("Failed to persist short term memory: %s", e)

    def add_exchange(self, user_text: str, jarvis_text: str, topic: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> None:
        """Appends a turn pair to working memory and performs routine pruning."""
        now_iso = datetime.now(timezone.utc).isoformat()
        u_turn = WorkingTurn(
            turn_id=f"u_{int(time.time()*1000)}",
            role="user",
            content=user_text.strip(),
            timestamp=now_iso,
            topic=topic,
            transient_data=data or {}
        )
        j_turn = WorkingTurn(
            turn_id=f"j_{int(time.time()*1000)+1}",
            role="jarvis",
            content=jarvis_text.strip(),
            timestamp=now_iso,
            topic=topic,
            transient_data=data or {}
        )
        with self._lock:
            self.turns.append(u_turn)
            self.turns.append(j_turn)
            # Prune turns older than TTL
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.ttl_hours)
            self.turns = [t for t in self.turns if datetime.fromisoformat(t.timestamp) >= cutoff][-MAX_WORKING_TURNS:]
            if topic:
                self.active_context["last_active_topic"] = topic
            self.active_context["last_activity"] = now_iso
        self._save()

    def set_session_variable(self, key: str, value: Any) -> None:
        """Sets a transient session variable (e.g. pending proposal, active trade idea)."""
        with self._lock:
            self.active_context[key] = {
                "val": value,
                "set_at": datetime.now(timezone.utc).isoformat()
            }
        self._save()

    def get_session_variable(self, key: str, max_age_hours: float = 6.0) -> Optional[Any]:
        with self._lock:
            entry = self.active_context.get(key)
            if not entry or not isinstance(entry, dict):
                return None
            try:
                ts = datetime.fromisoformat(entry.get("set_at", ""))
                if datetime.now(timezone.utc) - ts <= timedelta(hours=max_age_hours):
                    return entry.get("val")
            except Exception:
                return None
        return None

    def get_recent_dialogue(self, limit: int = 10) -> List[Dict[str, str]]:
        """Returns recent turns for conversational prompt context."""
        with self._lock:
            return [{"role": t.role, "content": t.content} for t in self.turns[-limit:]]

    def clear(self) -> None:
        """Explicitly resets short-term working memory."""
        with self._lock:
            self.turns.clear()
            self.active_context.clear()
        self._save()


# ==============================================================================
# TIER 2: PERMANENT LONG-TERM MEMORY (DURABLE SQLITE)
# ==============================================================================

class LongTermDurableMemory:
    """
    SQLite-backed permanent knowledge base and rule repository.
    Never expires automatically.
    """

    def __init__(self):
        self.db_path = _LONG_TERM_DB
        self._lock = threading.Lock()
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()
        self._seed_default_rules()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        with self._lock, self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS permanent_rules (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    rule_text TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS owner_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS learned_knowledge (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL
                );
            """)
            conn.commit()

    def _seed_default_rules(self) -> None:
        """Seeds foundational owner directives if database is fresh."""
        default_rules = [
            ("rule_risk_limit", "risk", "Hamaisha per-trade risk 0.25% se 1.0% ke darmiyan rakhein, kabhi exceed na karein.", 1),
            ("rule_high_impact_news", "trading", "Red folder High Impact US CPI/NFP news ke waqt live trade open karne se pehle approval lein.", 1),
            ("rule_bilingual_voice", "communication", "Master User (Muhammad Qureshi) ke sath Roman Urdu aur English technical blend mein baat karein.", 1),
            ("rule_final_decision", "protocol", "Koi bhi bara irreversible action lene se pehle WhatsApp par detail discuss karein aur final joint decision confirmation lein.", 1),
            ("rule_chrome_adeel", "browser", "Chrome Profile 'Adeel' (Profile 42) mein user ke paid ChatGPT aur Gemini accounts logged in hain.", 1)
        ]
        with self._lock, self._get_conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            for r_id, cat, text, prio in default_rules:
                conn.execute(
                    "INSERT OR IGNORE INTO permanent_rules (id, category, rule_text, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                    (r_id, cat, text, prio, now)
                )
            # Seed owner profile
            conn.execute("INSERT OR IGNORE INTO owner_profile (key, value, updated_at) VALUES (?, ?, ?)",
                         ("owner_name", "Muhammad Qureshi", now))
            conn.execute("INSERT OR IGNORE INTO owner_profile (key, value, updated_at) VALUES (?, ?, ?)",
                         ("owner_phone", "923468053268", now))
            conn.execute("INSERT OR IGNORE INTO owner_profile (key, value, updated_at) VALUES (?, ?, ?)",
                         ("chrome_profile_name", "adeel", now))
            conn.execute("INSERT OR IGNORE INTO owner_profile (key, value, updated_at) VALUES (?, ?, ?)",
                         ("chrome_profile_dir", "Profile 42", now))
            conn.commit()

    def add_permanent_rule(self, rule_text: str, category: str = "general", priority: int = 1) -> str:
        """Adds a permanent inviolable rule to long-term memory."""
        rule_id = f"rule_{int(time.time()*1000)}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO permanent_rules (id, category, rule_text, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                (rule_id, category, rule_text.strip(), priority, now)
            )
            conn.commit()
        logger.info("Added permanent rule: %s", rule_text)
        return rule_id

    def get_all_rules(self) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute("SELECT id, category, rule_text, priority, created_at FROM permanent_rules ORDER BY priority DESC, created_at ASC")
            return [dict(row) for row in cursor.fetchall()]

    def set_profile_fact(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO owner_profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), now)
            )
            conn.commit()

    def get_profile_facts(self) -> Dict[str, str]:
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute("SELECT key, value FROM owner_profile")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def add_learned_knowledge(self, topic: str, content: str, source: str = "user_instruction") -> str:
        k_id = f"k_{int(time.time()*1000)}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO learned_knowledge (id, topic, content, source, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (k_id, topic, content.strip(), source, 1.0, now)
            )
            conn.commit()
        return k_id

    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 2]
        if not words:
            return []
        with self._lock, self._get_conn() as conn:
            clause = " OR ".join(["content LIKE ? OR topic LIKE ?" for _ in words])
            params = []
            for w in words:
                params.extend([f"%{w}%", f"%{w}%"])
            sql = f"SELECT id, topic, content, source, created_at FROM learned_knowledge WHERE {clause} LIMIT {limit}"
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# MEMORY PROMOTION CLASSIFIER & DUAL-TIER COORDINATOR
# ==============================================================================

class DualTierMemoryCoordinator:
    """
    Unified coordinator managing Short-Term and Long-Term memory tiers,
    classifying incoming messages and generating prompt context.
    """

    PERMANENT_RULE_TRIGGERS = [
        "hamaisha", "hamesha", "always", "rule", "asool", "kabhi mat", "never",
        "yaad rakhna", "remember that", "permanent", "strictly", "mera policy",
        "meri aadat", "hamesha yad", "zaroori asool"
    ]

    PROFILE_FACT_TRIGGERS = [
        "mera naam", "my name is", "mera phone", "my phone", "meri email", "my email",
        "mera account", "i prefer", "mujhe pasand hai", "meri preference"
    ]

    SHORT_TERM_EPHEMERAL_TRIGGERS = [
        "aaj", "today", "abhi", "now", "kal", "tomorrow", "is waqt", "current",
        "thori der", "later", "target", "aaj ka", "today's", "temporary"
    ]

    def __init__(self):
        self.short_term = ShortTermWorkingMemory()
        self.long_term = LongTermDurableMemory()

    def classify_and_record(self, user_text: str, jarvis_text: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Intelligently classifies user input:
        - Promotes to Long-Term Memory if permanent rule or profile fact.
        - Records in Short-Term Working Memory for immediate multi-turn conversational context.
        """
        text_lower = user_text.lower()
        classification = {
            "tier": "SHORT_TERM",
            "promoted_to_long_term": False,
            "rule_saved": None,
            "fact_saved": None
        }

        # 1. Check for Permanent Rule Promotion
        is_permanent_rule = any(trigger in text_lower for trigger in self.PERMANENT_RULE_TRIGGERS)
        if is_permanent_rule:
            rule_id = self.long_term.add_permanent_rule(user_text, category=topic or "owner_policy", priority=2)
            classification["tier"] = "DUAL_TIER"
            classification["promoted_to_long_term"] = True
            classification["rule_saved"] = rule_id

        # 2. Check for Profile Fact Promotion
        is_profile_fact = any(trigger in text_lower for trigger in self.PROFILE_FACT_TRIGGERS)
        if is_profile_fact:
            key = "user_preference"
            if "naam" in text_lower or "name" in text_lower:
                key = "owner_name"
            elif "email" in text_lower:
                key = "owner_email"
            elif "phone" in text_lower or "number" in text_lower:
                key = "owner_phone"
            self.long_term.set_profile_fact(key, user_text)
            classification["tier"] = "DUAL_TIER"
            classification["promoted_to_long_term"] = True
            classification["fact_saved"] = key

        # 3. Always log to Short-Term working memory
        self.short_term.add_exchange(user_text, jarvis_text, topic=topic)
        return classification

    def add_permanent_rule(self, rule_text: str, category: str = "general", priority: int = 1) -> str:
        return self.long_term.add_permanent_rule(rule_text, category=category, priority=priority)

    def add_learned_knowledge(self, topic: str, content: str, source: str = "user_instruction") -> str:
        return self.long_term.add_learned_knowledge(topic, content, source=source)

    def set_profile_fact(self, key: str, value: str) -> None:
        self.long_term.set_profile_fact(key, value)

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return self.long_term.get_all_rules()

    def get_profile_facts(self) -> Dict[str, str]:
        return self.long_term.get_profile_facts()

    def build_unified_memory_context(self, current_query: str = "") -> str:
        """
        Generates a rich, structured memory context block for LLM prompts & WhatsApp discussions.
        """
        rules = self.long_term.get_all_rules()
        profile = self.long_term.get_profile_facts()
        recent_turns = self.short_term.get_recent_dialogue(limit=6)

        lines = [
            "=== J.A.R.V.I.S. DUAL-TIER COGNITIVE MEMORY ===",
            "[TIER 2: DURABLE OWNER RULES & INVIOLABLE PRINCIPLES]"
        ]
        for k, v in profile.items():
            lines.append(f"• {k.replace('_', ' ').title()}: {v}")
        for r in rules[:5]:
            lines.append(f"• [{r['category'].upper()}] {r['rule_text']}")

        # Query relevant knowledge if available
        if current_query:
            relevant = self.long_term.search_knowledge(current_query, limit=2)
            if relevant:
                lines.append("\n[TIER 2: RELEVANT HISTORICAL KNOWLEDGE]")
                for item in relevant:
                    lines.append(f"• ({item['topic']}): {item['content'][:150]}")

        lines.append("\n[TIER 1: RECENT WORKING MEMORY & CONVERSATIONAL CONTEXT (PAST 24H)]")
        if recent_turns:
            for t in recent_turns:
                prefix = "User" if t["role"] == "user" else "J.A.R.V.I.S."
                lines.append(f"• {prefix}: {t['content'][:200]}")
        else:
            lines.append("• (No active previous turns in this 24h window)")

        lines.append("==================================================")
        return "\n".join(lines)


# Singleton Accessor
_memory_coordinator_instance: Optional[DualTierMemoryCoordinator] = None

def get_dual_tier_memory() -> DualTierMemoryCoordinator:
    global _memory_coordinator_instance
    if _memory_coordinator_instance is None:
        _memory_coordinator_instance = DualTierMemoryCoordinator()
    return _memory_coordinator_instance
