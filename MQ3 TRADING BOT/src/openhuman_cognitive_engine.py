"""
src/openhuman_cognitive_engine.py
OpenHuman Subconscious Self-Reflection Engine & SuperContext Assembler.
Implements the 4-Phase Tick Cycle: observe -> prepare_context -> reflect -> commit.
Provides SQLite checkpointing in WAL mode, Memory Tree Management, and SuperContext synthesis.
"""

import os
import json
import sqlite3
import logging
import threading
import uuid
import datetime
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime, timezone
import numpy as np

from src.historical_50yr_regime_library import Historical50YrRegimeLibrary

logger = logging.getLogger("OpenHumanCognitiveEngine")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "openhuman_cognitive.db")
MEMORY_TREE_PATH = os.path.join(DATA_DIR, "memory_tree.json")


# ---------------------------------------------------------------------------
# 1. Memory Tree Manager (hierarchical memory store)
# ---------------------------------------------------------------------------

class MemoryTreeManager:
    """
    Hierarchical memory store with importance scoring and category compression.
    Organizes lessons across multi-asset categories.
    """
    CATEGORIES = [
        "GOLD_PATTERNS", "FOREX_PATTERNS", "CRYPTO_PATTERNS", "SESSION_BEHAVIOR",
        "RISK_LESSONS", "MARKET_MAKER_GAMES", "NEWS_IMPACT", "STRATEGY_PERFORMANCE", "GENERAL"
    ]

    def __init__(self, tree_path: str = MEMORY_TREE_PATH):
        self.tree_path = tree_path
        os.makedirs(os.path.dirname(self.tree_path), exist_ok=True)
        self._lock = threading.RLock()
        self.tree = self._load_tree()

    def store_lesson(self, category: str, lesson: str, importance_score: float = 0.5) -> None:
        """Stores a new lesson with deduplication and thread-safety."""
        with self._lock:
            if category not in self.CATEGORIES:
                category = "GENERAL"
            entry = {
                "lesson": lesson,
                "importance": round(min(max(importance_score, 0.0), 1.0), 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "access_count": 0
            }
            if category not in self.tree:
                self.tree[category] = []
            existing = [e.get("lesson") for e in self.tree[category] if isinstance(e, dict)]
            if lesson not in existing:
                self.tree[category].append(entry)
                self._save_tree()
                logger.info(f"[Memory Tree] Stored lesson in {category}: {lesson[:80]}...")

    def get_relevant_lessons(self, symbol: str, limit: int = 5, context: str = "") -> List[Dict[str, Any]]:
        """Retrieves top K lessons relevant to the given symbol and market context."""
        with self._lock:
            relevant = []
            search_cats = list(self.CATEGORIES)
            sym_u = symbol.upper()
            if "XAU" in sym_u or "GOLD" in sym_u:
                search_cats = ["GOLD_PATTERNS", "MARKET_MAKER_GAMES", "SESSION_BEHAVIOR", "RISK_LESSONS"]
            elif any(c in sym_u for c in ("BTC", "ETH", "SOL")):
                search_cats = ["CRYPTO_PATTERNS", "MARKET_MAKER_GAMES", "RISK_LESSONS"]
            elif any(f in sym_u for f in ("EUR", "GBP", "USD", "JPY")):
                search_cats = ["FOREX_PATTERNS", "SESSION_BEHAVIOR", "NEWS_IMPACT", "RISK_LESSONS"]

            for cat in search_cats:
                for item in self.tree.get(cat, []):
                    if isinstance(item, dict):
                        item["access_count"] = item.get("access_count", 0) + 1
                        relevant.append({**item, "category": cat})

            relevant.sort(key=lambda x: x.get("importance", 0.0), reverse=True)
            return relevant[:limit]

    def compress_memory(self, min_importance: float = 0.20) -> int:
        """Prunes low-importance lessons to keep working memory lean."""
        with self._lock:
            removed = 0
            for cat in list(self.tree.keys()):
                before = len(self.tree[cat])
                self.tree[cat] = [
                    e for e in self.tree[cat]
                    if isinstance(e, dict) and e.get("importance", 0.0) >= min_importance
                ]
                removed += before - len(self.tree[cat])
            if removed > 0:
                self._save_tree()
                logger.info(f"[Memory Compression] Removed {removed} low-importance entries (< {min_importance}).")
            return removed

    def _load_tree(self) -> Dict[str, List[Dict]]:
        if os.path.exists(self.tree_path):
            try:
                with open(self.tree_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return {cat: data.get(cat, []) for cat in self.CATEGORIES}
            except Exception:
                pass
        return {cat: [] for cat in self.CATEGORIES}

    def _save_tree(self) -> None:
        try:
            with open(self.tree_path, "w", encoding="utf-8") as f:
                json.dump(self.tree, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory tree: {e}")


# ---------------------------------------------------------------------------
# 2. Subconscious Reflection Engine (background reflection & diagnostics)
# ---------------------------------------------------------------------------

class SubconsciousReflectionEngine:
    """
    Autonomous background reflection engine inspired by OpenHuman.
    Analyzes trade outcomes, streaks, session win rates, and symbol bleed.
    """

    def __init__(self):
        self.reflection_memory: List[Dict[str, Any]] = []
        self.insights: List[str] = []
        self.goals: Dict[str, Any] = {
            "daily_target_pct": 1.0,
            "weekly_target_pct": 3.0,
            "max_daily_loss_pct": 2.5,
        }
        logger.info("SubconsciousReflectionEngine initialized.")

    def reflect_on_trades(self, trade_history: List[Dict[str, Any]]) -> List[str]:
        """Analyzes recent closed trades and surfaces behavioral insights."""
        if not trade_history:
            return ["No recent trades to reflect on."]

        insights: List[str] = []

        # 1. Streak Diagnostics
        outcomes = [t.get("outcome", "UNKNOWN") for t in trade_history[-20:]]
        wins = outcomes.count("WIN")
        losses = outcomes.count("LOSS")
        total = wins + losses
        win_rate = wins / max(total, 1)

        if win_rate >= 0.70 and total >= 5:
            insights.append(f"🔥 Hot streak: {win_rate:.0%} win rate over last {total} trades — maintain discipline.")
        elif win_rate <= 0.35 and total >= 5:
            insights.append(f"⚠️ Cold streak: {win_rate:.0%} win rate — consider reducing lot size or pausing.")

        # 2. Session Analysis
        session_wins: Dict[str, int] = {}
        session_total: Dict[str, int] = {}
        for t in trade_history[-30:]:
            sess = t.get("session", "UNKNOWN")
            session_total[sess] = session_total.get(sess, 0) + 1
            if t.get("outcome") == "WIN":
                session_wins[sess] = session_wins.get(sess, 0) + 1

        for sess, tot in session_total.items():
            wr = session_wins.get(sess, 0) / max(tot, 1)
            if wr >= 0.75 and tot >= 3:
                insights.append(f"📊 {sess} session is your strongest — {wr:.0%} win rate.")
            elif wr <= 0.30 and tot >= 3:
                insights.append(f"📉 {sess} session underperforming ({wr:.0%}) — consider avoiding.")

        # 3. Symbol Bleed Detection
        symbol_pnl: Dict[str, float] = {}
        for t in trade_history[-30:]:
            sym = t.get("symbol", "UNKNOWN")
            symbol_pnl[sym] = symbol_pnl.get(sym, 0.0) + t.get("pnl", 0.0)

        for sym, pnl in symbol_pnl.items():
            if pnl > 0:
                insights.append(f"💰 {sym} is profitable (+${pnl:.2f}) in recent history.")
            elif pnl < -50.0:
                insights.append(f"🔴 {sym} is bleeding (-${abs(pnl):.2f}) — reassess strategy.")

        # 4. Sweep Patterns
        sweep_count = sum(1 for t in trade_history[-20:] if t.get("pattern") and "SWEEP" in str(t.get("pattern", "")))
        if sweep_count >= 3:
            insights.append(f"🎯 {sweep_count} liquidity sweep trades detected — stop-hunt setups are active.")

        self.insights = insights
        self.reflection_memory.extend([
            {"timestamp": datetime.now(timezone.utc).isoformat(), "insight": i}
            for i in insights
        ])

        for insight in insights:
            logger.info(f"[Subconscious Reflection] {insight}")

        return insights

    def generate_morning_briefing(self) -> Dict[str, Any]:
        """Creates pre-session market summary."""
        now = datetime.now(timezone.utc)
        hour = now.hour

        if 5 <= hour <= 8:
            session_ahead = "LONDON_OPEN"
            focus = "Watch for London open liquidity sweep & Judas swing setups"
        elif 11 <= hour <= 14:
            session_ahead = "NEW_YORK_OPEN"
            focus = "Prepare for NY open volatility expansion & institutional flow"
        elif 20 <= hour <= 23:
            session_ahead = "ASIAN_SESSION"
            focus = "Low volatility — only high-confluence Gold setups recommended"
        else:
            session_ahead = "OFF_HOURS"
            focus = "Market is in transition — exercise patience"

        briefing = {
            "timestamp": now.isoformat(),
            "session_ahead": session_ahead,
            "focus_directive": focus,
            "recent_insights": self.insights[-5:] if self.insights else ["No recent reflections available."],
            "goals": self.goals,
        }
        return briefing

    def update_trading_goals(self, current_equity: float, starting_equity: float) -> Dict[str, Any]:
        """Tracks daily and weekly target progress."""
        pnl = current_equity - starting_equity
        pnl_pct = (pnl / max(starting_equity, 1)) * 100.0

        daily_target = self.goals["daily_target_pct"]
        weekly_target = self.goals["weekly_target_pct"]

        status = {
            "current_equity": current_equity,
            "starting_equity": starting_equity,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "daily_target_pct": daily_target,
            "daily_progress": round(min(pnl_pct / daily_target * 100, 100), 1) if daily_target > 0 else 0,
            "weekly_target_pct": weekly_target,
            "recommendation": "KEEP_TRADING",
        }

        if pnl_pct >= daily_target:
            status["recommendation"] = "DAILY_TARGET_HIT — consider stopping for the day"
        elif pnl_pct <= -self.goals["max_daily_loss_pct"]:
            status["recommendation"] = "MAX_DAILY_LOSS_HIT — STOP TRADING IMMEDIATELY"
        elif pnl_pct >= daily_target * 0.7:
            status["recommendation"] = "APPROACHING_TARGET — tighten risk, reduce lot size"

        return status


# ---------------------------------------------------------------------------
# 3. SuperContext Builder (pre-trade intelligence assembler)
# ---------------------------------------------------------------------------

class SuperContextBuilder:
    """
    Assembles all available intelligence into a structured SuperContext dictionary
    prior to order execution.
    """

    def __init__(self, memory_tree: Optional[MemoryTreeManager] = None,
                 reflection: Optional[SubconsciousReflectionEngine] = None):
        self.memory_tree = memory_tree or MemoryTreeManager()
        self.reflection = reflection or SubconsciousReflectionEngine()
        self.regime_library = Historical50YrRegimeLibrary()

    def build_trade_context(
        self,
        symbol: str,
        analysis: Dict[str, Any],
        weather_forecast: Optional[Dict] = None,
        market_regime: Optional[Dict] = None,
        consensus_vote: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Assembles memory, regime, and real-time conditions into SuperContext."""
        lessons = self.memory_tree.get_relevant_lessons(symbol)
        briefing = self.reflection.generate_morning_briefing()

        # Classify historical crisis regime
        regime = market_regime or self.regime_library.classify_current_regime(
            realized_vol_annual=analysis.get("atr", 0.18) * 1.5,
            current_drawdown_pct=0.03,
            gold_20d_ret=0.75 if "XAU" in symbol.upper() else 0.10
        )

        context = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trend": analysis.get("trend_direction", "UNKNOWN"),
            "rsi": analysis.get("rsi", 50.0),
            "atr": analysis.get("atr", 0.0),
            "current_price": analysis.get("current_price", 0.0),
            "fincept_sentiment": analysis.get("fincept_sentiment", 50.0),
            "weather": weather_forecast or {},
            "market_regime": regime,
            "consensus": consensus_vote or {},
            "session_ahead": briefing.get("session_ahead", "UNKNOWN"),
            "focus_directive": briefing.get("focus_directive", ""),
            "relevant_lessons": [l.get("lesson", "") for l in lessons[:5]],
            "recent_insights": briefing.get("recent_insights", []),
        }

        context["context_score"] = self.get_context_score(context)
        return context

    @staticmethod
    def get_context_score(context: Dict[str, Any]) -> int:
        """Returns 0-100 score reflecting confidence and data availability."""
        score = 0
        if context.get("trend") and context["trend"] != "UNKNOWN":
            score += 15
        if context.get("rsi") is not None:
            score += 10
        if context.get("atr") and context["atr"] > 0:
            score += 10
        if context.get("fincept_sentiment") is not None:
            score += 5
        if context.get("weather"):
            score += 15
        if context.get("market_regime") and (
            context["market_regime"].get("regime") or context["market_regime"].get("closest_crisis_regime")
        ):
            score += 15
        if context.get("consensus") and context["consensus"].get("verdict"):
            score += 15
        lessons = context.get("relevant_lessons", [])
        score += min(len(lessons) * 3, 10)
        insights = context.get("recent_insights", [])
        if insights and insights[0] != "No recent reflections available.":
            score += 5

        return min(score, 100)


# ---------------------------------------------------------------------------
# 4. OpenHuman Cognitive Engine (4-Phase Tick Cycle & SQLite WAL Checkpointing)
# ---------------------------------------------------------------------------

class OpenHumanCognitiveEngine:
    """
    OpenHuman Subconscious Self-Reflection Engine.
    Executes the 4-phase tick cycle:
        Phase 1: observe(tick_data)
        Phase 2: prepare_context(symbol)
        Phase 3: reflect(trade_history)
        Phase 4: commit()
    with ACID SQLite Checkpointing in WAL mode.
    """

    def __init__(
        self,
        db_path: str = DB_PATH,
        memory_tree: Optional[MemoryTreeManager] = None,
        regime_library: Optional[Historical50YrRegimeLibrary] = None
    ):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.memory_tree = memory_tree or MemoryTreeManager()
        self.regime_library = regime_library or Historical50YrRegimeLibrary()
        self.reflection_engine = SubconsciousReflectionEngine()

        # Telemetry & Buffers
        self.observation_buffer: deque = deque(maxlen=1000)
        self.trade_history: List[Dict[str, Any]] = []
        self.insights: List[Dict[str, Any]] = []
        self.active_directives: Dict[str, Any] = {
            "pause_trading": False,
            "risk_multiplier": 1.0,
            "allowed_symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"],
            "max_lot_override": None
        }
        self.goals: Dict[str, Any] = {
            "daily_target_pct": 1.0,
            "weekly_target_pct": 3.0,
            "max_daily_loss_pct": 2.5
        }

        # Finite State Machine: IDLE -> OBSERVED -> CONTEXT_PREPARED -> REFLECTED -> COMMITTED -> IDLE
        self.state = "IDLE"
        self.current_context: Dict[str, Any] = {}
        self.current_reflection: Dict[str, Any] = {}
        self.tick_sequence: int = 0

        self._init_sqlite()
        self.restore_latest_checkpoint()

    def _init_sqlite(self) -> None:
        """Initializes SQLite database with WAL mode and necessary tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cognitive_checkpoints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        checkpoint_id TEXT UNIQUE NOT NULL,
                        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        tick_sequence INTEGER NOT NULL,
                        session_name TEXT NOT NULL,
                        equity REAL NOT NULL,
                        balance REAL NOT NULL,
                        daily_pnl REAL NOT NULL,
                        drawdown_pct REAL NOT NULL,
                        matched_regime TEXT NOT NULL,
                        regime_similarity REAL NOT NULL,
                        risk_scalar REAL NOT NULL,
                        directives_json TEXT NOT NULL,
                        insights_json TEXT NOT NULL,
                        context_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subconscious_reflections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        checkpoint_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        insight_text TEXT NOT NULL,
                        recommended_action TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cognitive_memory_nodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        lesson_text TEXT UNIQUE NOT NULL,
                        importance_score REAL NOT NULL DEFAULT 0.50,
                        access_count INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    # ── Phase 1: OBSERVE ──────────────────────────────────────────────────
    def observe(self, tick_data: Dict[str, Any]) -> None:
        """Ingests raw market tick and execution telemetry into bounded ring buffer."""
        with self._lock:
            sanitized = {
                "timestamp": tick_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "symbol": str(tick_data.get("symbol", "XAUUSD")),
                "price": float(tick_data.get("price", 0.0)),
                "bid": float(tick_data.get("bid", tick_data.get("price", 0.0))),
                "ask": float(tick_data.get("ask", tick_data.get("price", 0.0))),
                "spread": float(tick_data.get("spread", 0.0)),
                "atr": float(tick_data.get("atr", 0.0)),
                "cvd_delta": float(tick_data.get("cvd_delta", 0.0)),
                "equity": float(tick_data.get("equity", 25000.0)),
                "balance": float(tick_data.get("balance", 25000.0)),
                "session": str(tick_data.get("session", self._get_current_session()))
            }
            self.observation_buffer.append(sanitized)
            self.tick_sequence += 1
            self.state = "OBSERVED"

    # ── Phase 2: PREPARE CONTEXT ──────────────────────────────────────────
    def prepare_context(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Assembles synthesized SuperContext and working memory state."""
        with self._lock:
            latest_obs = self.observation_buffer[-1] if self.observation_buffer else {}
            target_symbol = symbol or latest_obs.get("symbol", "XAUUSD")

            balance = latest_obs.get("balance", 25000.0)
            equity = latest_obs.get("equity", 25000.0)
            drawdown_pct = max((balance - equity) / max(balance, 1.0), 0.0)

            # Historical 50-Yr Regime Classification
            regime_intel = self.regime_library.classify_current_regime(
                realized_vol_annual=max(latest_obs.get("atr", 0.18) * 1.5, 0.05),
                current_drawdown_pct=drawdown_pct,
                dxy_20d_ret=-0.05,
                spread_stress_score=min(latest_obs.get("spread", 0.1) / 2.0, 1.0),
                gold_20d_ret=0.75 if "XAU" in target_symbol.upper() else 0.10
            )

            lessons = self.memory_tree.get_relevant_lessons(target_symbol, limit=5)
            session = latest_obs.get("session", self._get_current_session())

            self.current_context = {
                "symbol": target_symbol,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session": session,
                "latest_observation": latest_obs,
                "historical_regime": regime_intel,
                "relevant_lessons": [l["lesson"] for l in lessons if isinstance(l, dict) and "lesson" in l],
                "active_goals": self.goals,
                "directives": self.active_directives,
                "context_score": 85
            }
            self.state = "CONTEXT_PREPARED"
            return self.current_context

    # ── Phase 3: REFLECT ──────────────────────────────────────────────────
    def reflect(self, trade_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs cognitive heuristic diagnostics, tilt detection, and formulates execution directives."""
        with self._lock:
            if trade_history is not None:
                self.trade_history = trade_history

            insights = []
            directives = {
                "pause_trading": False,
                "risk_multiplier": 1.0,
                "allowed_symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"],
                "max_lot_override": None
            }

            # 1. Streak Diagnostics
            outcomes = [t.get("outcome", "UNKNOWN") for t in self.trade_history[-20:]]
            wins = outcomes.count("WIN")
            losses = outcomes.count("LOSS")
            total = wins + losses
            win_rate = wins / max(total, 1)

            if total >= 5 and win_rate >= 0.70:
                insights.append({
                    "category": "STREAK",
                    "severity": "INFO",
                    "text": f"🔥 Hot streak: {win_rate:.0%} win rate over last {total} trades — discipline lock active.",
                    "action": "MAINTAIN_DISCIPLINE"
                })
            elif total >= 5 and win_rate <= 0.35:
                directives["risk_multiplier"] = 0.50
                insights.append({
                    "category": "STREAK",
                    "severity": "WARNING",
                    "text": f"⚠️ Cold streak: {win_rate:.0%} win rate — scaling down risk by 50%.",
                    "action": "SCALE_DOWN_RISK"
                })

            # 2. Emotional Tilt & Revenge Trading Shield
            recent_losses = [t for t in self.trade_history[-3:] if t.get("outcome") == "LOSS"]
            if len(recent_losses) >= 2:
                directives["pause_trading"] = True
                directives["risk_multiplier"] = 0.25
                insights.append({
                    "category": "TILT",
                    "severity": "CRITICAL",
                    "text": "🛑 Consecutive loss threshold hit (2+ losses) — enforcing tilt cooling-off pause.",
                    "action": "MANDATORY_COOLING_PAUSE"
                })

            # 3. Symbol Bleed Diagnostics
            symbol_pnls: Dict[str, float] = {}
            for t in self.trade_history[-30:]:
                s = t.get("symbol", "UNKNOWN")
                symbol_pnls[s] = symbol_pnls.get(s, 0.0) + float(t.get("pnl", 0.0))

            for s, pnl in symbol_pnls.items():
                if pnl < -100.0:
                    insights.append({
                        "category": "SYMBOL_BLEED",
                        "severity": "WARNING",
                        "text": f"🔴 Symbol Bleed alert on {s} (-${abs(pnl):.2f}) — tightening entry confluence.",
                        "action": "RESTRICT_SYMBOL"
                    })

            # 4. Historical Crisis Regime Risk Multiplier
            regime = self.current_context.get("historical_regime", {})
            regime_scalar = regime.get("risk_scalar", 1.0)
            if regime_scalar < 1.0:
                directives["risk_multiplier"] = min(directives["risk_multiplier"], regime_scalar)
                insights.append({
                    "category": "CRISIS_REGIME",
                    "severity": "SHIELD",
                    "text": f"🛡️ Crisis Regime active ({regime.get('closest_crisis_regime')}) — risk scalar {regime_scalar:.2f}x.",
                    "action": regime.get("action_protocol", "DEFENSIVE_CIRCUIT_BREAKER")
                })

            self.insights = insights
            self.active_directives = directives
            self.current_reflection = {
                "insights": insights,
                "directives": directives,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.state = "REFLECTED"
            return self.current_reflection

    # ── Phase 4: COMMIT ───────────────────────────────────────────────────
    def commit(self) -> Dict[str, Any]:
        """Atomically persists cognitive checkpoint to SQLite in WAL mode."""
        with self._lock:
            checkpoint_id = f"CHK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            latest_obs = self.observation_buffer[-1] if self.observation_buffer else {}
            regime = self.current_context.get("historical_regime", {})

            equity = latest_obs.get("equity", 25000.0)
            balance = latest_obs.get("balance", 25000.0)
            daily_pnl = equity - balance
            drawdown_pct = max((balance - equity) / max(balance, 1.0), 0.0)

            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cognitive_checkpoints (
                        checkpoint_id, tick_sequence, session_name, equity, balance,
                        daily_pnl, drawdown_pct, matched_regime, regime_similarity,
                        risk_scalar, directives_json, insights_json, context_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint_id,
                    self.tick_sequence,
                    self._get_current_session(),
                    equity,
                    balance,
                    daily_pnl,
                    drawdown_pct,
                    regime.get("closest_crisis_regime", "NORMAL"),
                    regime.get("crisis_similarity", 1.0),
                    self.active_directives.get("risk_multiplier", 1.0),
                    json.dumps(self.active_directives),
                    json.dumps(self.insights),
                    str(hash(json.dumps(self.current_context, default=str)))
                ))

                for ins in self.insights:
                    cursor.execute("""
                        INSERT INTO subconscious_reflections (
                            checkpoint_id, category, severity, insight_text, recommended_action
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        checkpoint_id,
                        ins.get("category", "GENERAL"),
                        ins.get("severity", "INFO"),
                        ins.get("text", ""),
                        ins.get("action", "")
                    ))

                conn.commit()
            finally:
                conn.close()

            # Compress low-importance memory tree nodes
            self.memory_tree.compress_memory(min_importance=0.20)

            self.state = "IDLE"
            return {
                "checkpoint_id": checkpoint_id,
                "status": "COMMITTED",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def restore_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Restores cognitive engine state from the latest SQLite checkpoint."""
        with self._lock:
            if not os.path.exists(self.db_path):
                return None
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT checkpoint_id, tick_sequence, directives_json, insights_json
                    FROM cognitive_checkpoints ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    self.tick_sequence = row[1]
                    self.active_directives = json.loads(row[2])
                    self.insights = json.loads(row[3])
                    logger.info(f"Restored cognitive engine from checkpoint {row[0]}")
                    return {"checkpoint_id": row[0], "tick_sequence": row[1]}
            except Exception as e:
                logger.warning(f"Could not restore checkpoint: {e}")
            finally:
                conn.close()
            return None

    def _get_current_session(self) -> str:
        hour = datetime.now(timezone.utc).hour
        if 0 <= hour < 6:
            return "ASIAN_SESSION"
        elif 6 <= hour < 12:
            return "LONDON_OPEN"
        elif 12 <= hour < 18:
            return "NEW_YORK_OPEN"
        return "OFF_HOURS"
