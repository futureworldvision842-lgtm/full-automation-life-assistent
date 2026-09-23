"""Comprehensive Verification Test Suite for Milestone 3:
1-Shot Dynamic Skill Catalog & Continuous Vector Mission Memory.

Verifies:
1. 384-Dimensional Dense Vector Memory Embeddings and Sub-Second Retrieval (<50ms query latency).
2. 1-Shot Dynamic Skill Synthesis from Natural Language (English & Roman Urdu).
3. AST Validation and Security Guardrails against destructive operations.
4. Automatic Companion Unit Test Generation & Isolated Subprocess Execution.
5. Automated 1-Attempt Self-Repair Loop.
6. Zero-Guidance Autonomous Recall & 100% Fidelity Execution.
"""

import ast
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from memory import mission_memory
from skills import dynamic_compiler
from skills.dynamic_compiler import (
    DynamicSkillCompiler,
    SkillCompilationResult,
    normalize_skill_name,
    validate_skill_ast,
)

ROOT = Path(__file__).resolve().parent.parent


class TestDense384VectorMemory(unittest.TestCase):
    """Verifies 384-dim dense vector embedding engine and SQLite vector memory."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_mission_memory.db"
        self.db_patch = patch.object(mission_memory, "DB_PATH", self.test_db_path)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_embedding_dimensions_and_normalization(self):
        """Verifies embeddings are exactly 384-dimensional and unit-normalized."""
        sample_texts = [
            "Institutional MT5 Gold trading risk management and stop loss rules.",
            "Server status ping on ports 8770, 8765, 5050.",
            "bhai server status check karo aur ports ping karo",
            "G.A.I.G.S. Islamic governance principles and human accountability.",
        ]
        for text in sample_texts:
            vec = mission_memory.get_embedding(text)
            self.assertIsInstance(vec, np.ndarray)
            self.assertEqual(vec.shape, (384,), f"Vector must be 384-dim, got {vec.shape}")
            norm = float(np.linalg.norm(vec))
            self.assertAlmostEqual(norm, 1.0, places=4, msg="Vector must have unit L2 norm")

    def test_sub_second_query_latency(self):
        """Verifies vector memory query latency is well below 50ms."""
        # Seed 50 diverse vector memories
        for i in range(50):
            mission_memory.remember_vector(
                content=f"Workflow pattern #{i}: automated data verification and logging task for module_{i}.",
                category="workflow",
                key=f"workflow_{i}",
                metadata={"index": i},
            )

        queries = [
            "automated data verification task",
            "module_12 logging workflow",
            "verify data pattern and check module",
            "server health monitoring",
            "gold trading risk limits",
        ]
        latencies: list[float] = []
        for q in queries:
            t0 = time.perf_counter()
            results = mission_memory.recall_vector(q, limit=5, min_similarity=0.30)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            self.assertIsInstance(results, list)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        self.assertLess(avg_latency, 50.0, f"Average query latency ({avg_latency:.2f}ms) must be <50ms")
        self.assertLess(max_latency, 50.0, f"Max query latency ({max_latency:.2f}ms) must be <50ms")

    def test_semantic_similarity_clustering(self):
        """Verifies conceptually related queries yield high cosine score while unrelated yield low score."""
        mission_memory.remember_vector(
            content="Institutional Trading Risk Rules: Daily Loss Shield 2.5%, Trade Risk Cap 0.50%, FTMO account protection.",
            category="trading_rule",
            key="ftmo_risk_rule",
            metadata={"account": "FTMO"},
        )

        related_query = "What is the max daily drawdown and risk cap for prop accounts?"
        unrelated_query = "How to bake a chocolate strawberry birthday cake?"

        related_results = mission_memory.recall_vector(related_query, category="trading_rule", limit=1, min_similarity=0.40)
        unrelated_results = mission_memory.recall_vector(unrelated_query, category="trading_rule", limit=1, min_similarity=-1.0)

        self.assertTrue(len(related_results) > 0, "Related query should find matching trading rule")
        self.assertTrue(len(unrelated_results) > 0, "Unrelated query with min_similarity=-1.0 should return candidate")

        related_score = related_results[0].similarity
        unrelated_score = unrelated_results[0].similarity

        self.assertGreater(related_score, 0.70, f"Related score {related_score} should be >= 0.70")
        self.assertLess(unrelated_score, 0.40, f"Unrelated score {unrelated_score} should be < 0.40")
        self.assertGreater(related_score, unrelated_score + 0.30)

    def test_bilingual_roman_urdu_semantic_matching(self):
        """Verifies Roman Urdu queries match English knowledge via semantic expansion."""
        mission_memory.remember_vector(
            content="Server status inspection: Ping TCP ports 8770, 8765, 5050 and check host vitals.",
            category="skill",
            key="server_status_ping",
            metadata={"skill_name": "server_status_ping"},
        )

        urdu_query = "bhai server ka status batao aur ports check karo"
        matches = mission_memory.recall_vector(urdu_query, category="skill", limit=1, min_similarity=0.50)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].key, "server_status_ping")
        self.assertGreaterEqual(matches[0].similarity, 0.70)

    def test_crud_and_update_operations(self):
        """Verifies remember_vector, update on duplicate key, delete, and list operations."""
        row_id_1 = mission_memory.remember_vector("Initial content", category="notes", key="note_1")
        self.assertGreater(row_id_1, 0)

        row_id_2 = mission_memory.remember_vector("Updated content with more details", category="notes", key="note_1")
        self.assertEqual(row_id_1, row_id_2)

        items = mission_memory.list_vector_memories(category="notes")
        self.assertEqual(len(items), 1)
        self.assertIn("Updated content", items[0].content)

        deleted = mission_memory.delete_vector_memory("note_1", category="notes")
        self.assertTrue(deleted)

        items_after = mission_memory.list_vector_memories(category="notes")
        self.assertEqual(len(items_after), 0)


class TestDynamicSkillCompiler(unittest.TestCase):
    """Verifies 1-shot skill synthesis, companion unit tests, AST validation, and self-repair."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_dir = Path(self.temp_dir.name) / "skills"
        self.tests_dir = Path(self.temp_dir.name) / "tests_skills"
        self.quarantine_dir = Path(self.temp_dir.name) / "quarantine"
        self.test_db_path = Path(self.temp_dir.name) / "test_memory.db"

        self.compiler = DynamicSkillCompiler(
            skills_dir=self.skills_dir,
            tests_dir=self.tests_dir,
        )
        self.compiler.quarantine_dir = self.quarantine_dir
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.db_patch = patch.object(mission_memory, "DB_PATH", self.test_db_path)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_ast_validation_valid_skill(self):
        """Verifies AST validation passes for valid skill with MANIFEST and run()."""
        valid_code = '''
"""Sample valid dynamic skill."""
MANIFEST = {
    "name": "sample_valid_skill",
    "description": "Calculates sum of two numbers",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "a": {"type": "NUMBER"},
            "b": {"type": "NUMBER"}
        }
    }
}

def run(parameters=None, player=None, speak=None) -> str:
    params = parameters or {}
    a = float(params.get("a", 0))
    b = float(params.get("b", 0))
    return f"Sum is {a + b}"
'''
        ok, msg = validate_skill_ast(valid_code)
        self.assertTrue(ok, f"Expected AST valid, got error: {msg}")

    def test_ast_validation_missing_manifest_or_run(self):
        """Verifies AST validation rejects code missing MANIFEST or run()."""
        no_manifest = "def run(parameters=None): return 'hello'"
        ok1, msg1 = validate_skill_ast(no_manifest)
        self.assertFalse(ok1)
        self.assertIn("MANIFEST", msg1)

        no_run = "MANIFEST = {'name': 'test', 'description': 'd', 'parameters': {}}"
        ok2, msg2 = validate_skill_ast(no_run)
        self.assertFalse(ok2)
        self.assertIn("run", msg2)

    def test_ast_security_guardrails_blocks_destructive_commands(self):
        """Verifies security scanner blocks destructive commands and dangerous calls."""
        destructive_cases = [
            ("format D:", "MANIFEST={'name':'f','description':'','parameters':{}}\ndef run(p=None): os.system('format D:')"),
            ("rmdir /s", "MANIFEST={'name':'r','description':'','parameters':{}}\ndef run(p=None): subprocess.run('rmdir /s /q temp')"),
            ("shutil.rmtree('/')", "import shutil\nMANIFEST={'name':'s','description':'','parameters':{}}\ndef run(p=None): shutil.rmtree('/')"),
            ("eval", "MANIFEST={'name':'e','description':'','parameters':{}}\ndef run(p=None): eval('__import__(\"os\").remove(\"file\")')"),
        ]
        for name, code in destructive_cases:
            ok, msg = validate_skill_ast(code)
            self.assertFalse(ok, f"Destructive code '{name}' should be blocked")
            self.assertIn("Security Violation", msg)

    def test_1shot_compilation_file_backup(self):
        """Verifies 1-shot compilation for file backup workflow."""
        instruction = "Whenever I say 'backup project data', compress folder 'data' to 'backups' and log the size."
        res = self.compiler.compile_skill_from_instruction(instruction, "backup_project_data")

        self.assertTrue(res.success, f"Compilation failed: {res.error}")
        self.assertEqual(res.skill_name, "backup_project_data")
        self.assertIsNotNone(res.file_path)
        self.assertIsNotNone(res.test_path)
        self.assertTrue(Path(res.file_path).exists())
        self.assertTrue(Path(res.test_path).exists())

        exec_res = self.compiler.execute_skill("backup_project_data", {"source_dir": "test_src", "target_dir": str(self.temp_dir.name)})
        self.assertTrue(exec_res["ok"])
        self.assertIn("Backup Completed", exec_res["output"])

    def test_1shot_compilation_gold_lot_calculator(self):
        """Verifies 1-shot compilation for institutional gold trading calculator."""
        instruction = "Calculate lot size and risk for FTMO gold trading with balance, risk percent, and stoploss pips."
        res = self.compiler.compile_skill_from_instruction(instruction, "ftmo_gold_lot_calculator")

        self.assertTrue(res.success, f"Compilation failed: {res.error}")
        self.assertTrue(Path(res.file_path).exists())

        exec_res = self.compiler.execute_skill(
            "ftmo_gold_lot_calculator",
            {"account_balance": 100000.0, "risk_percent": 0.50, "stop_loss_pips": 20.0, "symbol": "XAUUSD"},
        )
        self.assertTrue(exec_res["ok"])
        self.assertIn("Institutional Position Matrix", exec_res["output"])
        self.assertIn("$100,000.00", exec_res["output"])

    def test_companion_unit_test_generation_and_execution(self):
        """Verifies companion unit test file passes isolated unittest execution."""
        instruction = "Convert currency from USD to PKR with amount and exchange rate calculation."
        res = self.compiler.compile_skill_from_instruction(instruction, "currency_converter_pkr")

        self.assertTrue(res.success, f"Compilation error: {res.error}")
        test_path = Path(res.test_path)
        self.assertTrue(test_path.exists())

        passed, test_meta = self.compiler.run_isolated_test(test_path)
        self.assertTrue(passed, f"Isolated test failed: {test_meta}")
        self.assertEqual(test_meta["returncode"], 0)

    def test_self_repair_loop_recovers_from_initial_failure(self):
        """Verifies automated 1-attempt self-repair loop heals defective skill code."""
        failing_code = '''MANIFEST = {
    "name": "auto_repaired_skill",
    "description": "Skill needing self-repair",
    "parameters": {"type": "OBJECT", "properties": {}}
}

def run(parameters=None, player=None, speak=None) -> str:
    data = json.dumps({"status": "healthy", "timestamp": time.time()})
    return data
'''
        ast_ok, _ = validate_skill_ast(failing_code)
        self.assertTrue(ast_ok)

        repaired_code, repaired_test = self.compiler.attempt_self_repair(
            "auto_repaired_skill",
            failing_code,
            "NameError: name 'json' is not defined",
            {"name": "auto_repaired_skill", "description": "Skill needing self-repair", "parameters": {}},
        )

        self.assertIn("import json", repaired_code)
        self.assertIn("import time", repaired_code)


class TestZeroGuidanceSkillRecall(unittest.TestCase):
    """Verifies zero-guidance recall matching user commands to stored skills."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_dir = Path(self.temp_dir.name) / "skills"
        self.tests_dir = Path(self.temp_dir.name) / "tests_skills"
        self.test_db_path = Path(self.temp_dir.name) / "test_memory.db"

        self.compiler = DynamicSkillCompiler(
            skills_dir=self.skills_dir,
            tests_dir=self.tests_dir,
        )
        self.db_patch = patch.object(mission_memory, "DB_PATH", self.test_db_path)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_zero_guidance_autonomous_recall_and_execution(self):
        """Verifies zero-guidance skill recall and 100% fidelity execution."""
        instruction = "Whenever I say 'backup project data', compress folder 'data' to 'backups' and log the size."
        comp_res = self.compiler.compile_skill_from_instruction(instruction, "backup_project_data")
        self.assertTrue(comp_res.success)

        subsequent_command = "backup workspace project data to backups archive"
        recall_res = self.compiler.autonomous_recall_and_execute(subsequent_command, min_similarity=0.50)

        self.assertTrue(recall_res["ok"])
        self.assertEqual(recall_res["recalled_skill"], "backup_project_data")
        self.assertGreaterEqual(recall_res["similarity"], 0.70)
        self.assertIn("Backup Completed", recall_res["result"]["output"])

    def test_zero_guidance_bilingual_roman_urdu_recall(self):
        """Verifies Roman Urdu instruction compiled skill is recalled with Roman Urdu command."""
        instruction = "Jab bhi main kahoon 'server status check karo', to ports 8770, 8765, 5050 ping karo aur summary do."
        comp_res = self.compiler.compile_skill_from_instruction(instruction, "server_status_ping")
        self.assertTrue(comp_res.success)

        subsequent_urdu_cmd = "bhai server status check karo aur ports ping karo"
        recall_res = self.compiler.autonomous_recall_and_execute(subsequent_urdu_cmd, min_similarity=0.50)

        self.assertTrue(recall_res["ok"])
        self.assertEqual(recall_res["recalled_skill"], "server_status_ping")
        self.assertGreaterEqual(recall_res["similarity"], 0.70)
        self.assertIn("Server Status Probe", recall_res["result"]["output"])


if __name__ == "__main__":
    unittest.main()
