"""
tests/test_openhuman_sqlite_checkpointing.py
Tests for Feature 8: OpenHuman Cognitive Engine, 4-Phase Tick Loop, and SQLite WAL Checkpointing.
"""

import os
import tempfile
import sqlite3
import pytest
from src.openhuman_cognitive_engine import OpenHumanCognitiveEngine, MemoryTreeManager, SubconsciousReflectionEngine, SuperContextBuilder
from src.historical_50yr_regime_library import Historical50YrRegimeLibrary


class TestOpenHumanSQLiteCheckpointing:

    @pytest.fixture
    def env(self):
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test_wal_checkpoint.db")
        tree_path = os.path.join(tmp_dir, "test_tree.json")
        mem_tree = MemoryTreeManager(tree_path=tree_path)
        engine = OpenHumanCognitiveEngine(db_path=db_path, memory_tree=mem_tree)
        return engine, db_path, mem_tree

    def test_four_phase_tick_cycle_order(self, env):
        engine, db_path, _ = env
        assert engine.state == "IDLE"

        # Phase 1: observe
        engine.observe({"symbol": "EURUSD", "price": 1.0850, "atr": 0.0015, "spread": 0.0001})
        assert engine.state == "OBSERVED"

        # Phase 2: prepare_context
        ctx = engine.prepare_context("EURUSD")
        assert engine.state == "CONTEXT_PREPARED"
        assert ctx["symbol"] == "EURUSD"

        # Phase 3: reflect
        refl = engine.reflect()
        assert engine.state == "REFLECTED"
        assert "directives" in refl

        # Phase 4: commit
        res = engine.commit()
        assert res["status"] == "COMMITTED"
        assert engine.state == "IDLE"

    def test_sqlite_memory_tree_persistence_and_wal(self, env):
        engine, db_path, mem_tree = env
        mem_tree.store_lesson("FOREX_PATTERNS", "EURUSD Asian low sweep bounce", importance_score=0.85)

        engine.observe({"symbol": "EURUSD", "price": 1.0850, "equity": 25100.0, "balance": 25000.0})
        engine.prepare_context("EURUSD")
        engine.reflect()
        commit_res = engine.commit()

        # Connect directly to SQLite and verify WAL journal mode & checkpoint tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.upper() == "WAL"

        cursor.execute("SELECT checkpoint_id, equity, balance, matched_regime FROM cognitive_checkpoints")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == commit_res["checkpoint_id"]
        assert row[1] == 25100.0
        conn.close()

    def test_supercontext_score_synthesis(self):
        builder = SuperContextBuilder()
        ctx = builder.build_trade_context("XAUUSD", {
            "trend_direction": "BULLISH",
            "rsi": 48.0,
            "atr": 1.4,
            "current_price": 2650.0,
            "fincept_sentiment": 60.0
        })
        assert 0 <= ctx["context_score"] <= 100
        assert ctx["context_score"] >= 45

    def test_crash_recovery_and_rollback(self, env):
        engine, db_path, _ = env
        engine.observe({"symbol": "BTCUSD", "price": 95000.0, "equity": 26000.0, "balance": 25000.0})
        engine.prepare_context("BTCUSD")
        engine.reflect()
        res = engine.commit()

        engine2 = OpenHumanCognitiveEngine(db_path=db_path)
        assert engine2.tick_sequence == engine.tick_sequence
        assert engine2.active_directives is not None
