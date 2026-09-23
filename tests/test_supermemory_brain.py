"""
tests/test_supermemory_brain.py
================================
Verification for supermemoryai/supermemory cognitive brain.
Tests SQLite WAL persistence, sub-500ms semantic lookup, knowledge graph, and market lessons.
"""

import pytest
import time
import os
from pathlib import Path
from memory.supermemory_brain import SupermemoryBrain

@pytest.fixture
def temp_brain():
    db_file = Path(__file__).resolve().parent.parent / "memory" / "test_supermemory_sandbox.db"
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass
    brain = SupermemoryBrain(db_path=db_file)
    yield brain
    # Teardown
    try:
        if db_file.exists():
            os.remove(db_file)
        wal_file = Path(str(db_file) + "-wal")
        if wal_file.exists():
            os.remove(wal_file)
        shm_file = Path(str(db_file) + "-shm")
        if shm_file.exists():
            os.remove(shm_file)
    except Exception:
        pass



class TestSupermemoryBrain:
    def test_database_initialization_and_wal(self, temp_brain):
        with temp_brain._get_connection() as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert mode.lower() == "wal"

    def test_seed_sovereign_invariants(self, temp_brain):
        triples = temp_brain.query_knowledge_graph(subject="Master Muhammad Qureshi")
        assert len(triples) >= 2
        predicates = [t.predicate for t in triples]
        assert "phone_number" in predicates
        assert "official_email" in predicates

        # Verify phone number and email
        phone_triple = [t for t in triples if t.predicate == "phone_number"][0]
        assert phone_triple.object == "+923468053268"

    def test_remember_and_sub_500ms_recall(self, temp_brain):
        # Insert test memories
        temp_brain.remember(
            content="FundingPips prop account #40000294403 has strict 0.75% max risk ceiling.",
            category="trading_rule",
            tags=["prop", "fundingpips", "risk"],
        )
        temp_brain.remember(
            content="Solana meme coins require honeypot checks and minimum liquidity of $50,000.",
            category="meme_strategy",
            tags=["solana", "memes"],
        )
        temp_brain.remember(
            content="XAUUSD Gold institutional discount OTE occurs between 61.8% and 78.6% Fibonacci.",
            category="smc_concepts",
            tags=["gold", "fibonacci"],
        )

        # Time semantic recall
        start_t = time.perf_counter()
        recalled = temp_brain.recall("What is the risk limit on FundingPips account?")
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        assert elapsed_ms < 500.0, f"Recall took {elapsed_ms:.2f}ms, exceeding 500ms threshold!"
        assert len(recalled) > 0
        top = recalled[0]
        assert "FundingPips" in top.content
        assert top.access_count >= 1

    def test_knowledge_graph_relationship_traversal(self, temp_brain):
        temp_brain.add_knowledge_triple("XAUUSD", "has_discount_zone", "Fib_70.5%", confidence=0.98)
        temp_brain.add_knowledge_triple("Fib_70.5%", "triggers", "Long_Entry_Confirmation", confidence=0.92)

        results = temp_brain.query_knowledge_graph(subject="XAUUSD")
        assert len(results) >= 1
        assert results[0].object == "Fib_70.5%"

        next_hop = temp_brain.query_knowledge_graph(subject="Fib_70.5%")
        assert len(next_hop) >= 1
        assert next_hop[0].object == "Long_Entry_Confirmation"

    def test_market_lessons_and_daily_learnings(self, temp_brain):
        l_id = temp_brain.record_market_lesson(
            symbol="EURUSD",
            lesson_type="LIQUIDITY_HUNT",
            description="London open swept previous day high then reversed aggressively.",
            outcome="WIN",
            rule_deduced="Never enter long on London open breakout before liquidity sweep occurs."
        )
        assert l_id.startswith("lesson_EURUSD_")

        lessons = temp_brain.get_recent_lessons(symbol="EURUSD")
        assert len(lessons) == 1
        assert lessons[0]["rule_deduced"].startswith("Never enter long")

        # Check that it is also retrievable semantically
        recalled = temp_brain.recall("London breakout liquidity sweep")
        assert len(recalled) >= 1
        assert "EURUSD" in recalled[0].content

    def test_zero_prohibited_identifer(self, temp_brain):
        all_triples = temp_brain.query_knowledge_graph()
        all_text = str([t.to_dict() for t in all_triples]).lower()
        assert "adeel" not in all_text
        assert "qureshi99" not in all_text
