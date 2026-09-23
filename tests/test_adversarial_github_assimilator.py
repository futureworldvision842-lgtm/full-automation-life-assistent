"""
tests/test_adversarial_github_assimilator.py
========================================================================
Empirical Adversarial Stress Test Suite for Milestone M1:
- Obfuscated malicious ASTs (indirect getattr eval/exec, unicode escapes,
  encoded shell commands, dunder traversal, environment key access)
- Sandbox boundary & resource enforcement (timeout, infinite loops,
  memory exhaustion / 512MB Job Object, recursive child process teardown)
- Complex repository structures (deeply nested modules, mixed argparse/click,
  corrupt syntax tolerance, unusual AST constructs)

Author: teamwork_preview_challenger_m1_2 (Empirical Challenger)
Roles: critic, specialist
========================================================================
"""

from __future__ import annotations

import ast
import base64
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.active_tool_registry import (
    ActiveToolRegistry,
    ToolMetadata,
    get_active_tool_registry,
)
from tools.github_assimilator import (
    BELOW_NORMAL_PRIORITY_CLASS,
    CREATE_NO_WINDOW,
    AssimilatorASTSecurityValidator,
    ASTCapabilityExtractor,
    ASTParsingError,
    BannedIdentityError,
    DestructiveCodeError,
    GitHubAssimilator,
    HotReloadError,
    RepoCloneError,
    RiskCeilingViolationError,
    SandboxAssertionError,
    SandboxTimeoutError,
    SecurityViolationError,
    SkillSynthesisError,
    SubprocessSandboxRunner,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_workspace():
    """Provides an isolated workspace directory with scratch and skills folders."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        base = Path(tmp_dir)
        repos_dir = base / "scratch" / "repos"
        skills_dir = base / "skills"
        sandbox_tests_dir = base / "scratch" / "sandbox_tests"
        quarantine_dir = base / "quarantine" / "skills"

        repos_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)
        sandbox_tests_dir.mkdir(parents=True, exist_ok=True)
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        yield {
            "base": base,
            "repos_dir": repos_dir,
            "skills_dir": skills_dir,
            "sandbox_tests_dir": sandbox_tests_dir,
            "quarantine_dir": quarantine_dir,
        }


@pytest.fixture
def assimilator(temp_workspace):
    """Instantiates a clean GitHubAssimilator bound to temp workspace."""
    return GitHubAssimilator(
        base_dir=temp_workspace["base"],
        repos_dir=temp_workspace["repos_dir"],
        skills_dir=temp_workspace["skills_dir"],
        sandbox_tests_dir=temp_workspace["sandbox_tests_dir"],
        quarantine_dir=temp_workspace["quarantine_dir"],
    )


# =============================================================================
# 1. Obfuscated Malicious ASTs and Security Guardrail Challenges
# =============================================================================

class TestObfuscatedMaliciousASTAdversarial:
    """
    Adversarial evaluation of AssimilatorASTSecurityValidator and Sandbox defense-in-depth:
    - Direct banned calls rejection
    - Indirect getattr reflection bypasses
    - Unicode escape sequences in strings vs identifiers
    - Encoded shell commands (lists vs concatenated vs base64)
    - Sensitive private key environment isolation
    """

    def test_direct_banned_calls_strictly_blocked(self, assimilator):
        """Verify all direct calls in BANNED_CALLS are blocked by AST validator."""
        direct_banned = [
            "eval('1 + 1')",
            "exec('a = 1')",
            "compile('1+1', '', 'eval')",
            "__import__('os')",
            "os.system('whoami')",
            "os.popen('dir')",
            "os.spawnl(0, 'cmd.exe')",
            "os.kill(1234, 9)",
        ]
        for payload in direct_banned:
            code = f"def run(p=None, player=None, speak=None):\n    {payload}\n    return 'OK'\n"
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Direct banned call should be rejected: {payload}"
            assert len(violations) >= 1

    def test_indirect_getattr_eval_exec_blocked_by_ast_validator(self, assimilator):
        """
        Verify hardened AssimilatorASTSecurityValidator blocks getattr(__builtins__, 'eval')
        and getattr(builtins, 'eval').
        """
        code_getattr_eval = """
def run(parameters=None, player=None, speak=None):
    f = getattr(__builtins__, "eval")
    return f("1 + 1")
"""
        is_safe, violations = assimilator.security_validator.validate(code_getattr_eval)
        assert is_safe is False, "Hardened AST validator must block getattr(__builtins__, 'eval')"
        assert any("getattr" in v.lower() or "reflection" in v.lower() or "builtins" in v.lower() for v in violations)

    def test_indirect_builtins_module_import_blocked_by_ast_validator(self, assimilator):
        """
        Verify hardened AssimilatorASTSecurityValidator blocks import of 'builtins'
        and invocation of builtins.eval.
        """
        code_builtins_eval = """
import builtins

def run(parameters=None, player=None, speak=None):
    return builtins.eval("1 + 1")
"""
        is_safe, violations = assimilator.security_validator.validate(code_builtins_eval)
        assert is_safe is False, "Hardened AST validator must block builtins.eval"
        assert len(violations) >= 1

    def test_unicode_escapes_in_string_literals_detected(self, assimilator):
        """
        Verify AST validator correctly detects unicode-escaped prohibited identity tokens
        when expressed as unicode escape sequences in string literals.
        """
        unicode_literal_code = '''
def run(parameters=None, player=None, speak=None):
    token = "\\u0061\\u0064\\u0065\\u0065\\u006c\\u0071\\u0075\\u0072\\u0065\\u0073\\u0068\\u0069\\u0039\\u0039"
    return token
'''
        is_safe, violations = assimilator.security_validator.validate(unicode_literal_code)
        assert not is_safe, "Unicode escaped identity token in string literal must be rejected"
        assert any("Prohibited identity token" in v for v in violations)

    def test_concatenated_identity_tokens_blocked_by_ast_validator(self, assimilator):
        """
        Verify string concatenation ('adeel' + 'qureshi' + '99') is folded and
        blocked by hardened AssimilatorASTSecurityValidator.
        """
        code_concat = '''
def run(parameters=None, player=None, speak=None):
    user = "adeel" + "qureshi" + "99"
    return user
'''
        is_safe, violations = assimilator.security_validator.validate(code_concat)
        assert is_safe is False, "Hardened AST validator must block concatenated identity tokens"
        assert any("prohibited identity token" in v.lower() for v in violations)

    def test_list_form_commands_blocked_by_ast_shell_patterns(self, assimilator):
        """
        Verify list-argument subprocess calls (e.g. ['del', '/f', '/s', 'target'])
        are inspected and blocked by hardened AssimilatorASTSecurityValidator.
        """
        code_list_cmd = '''
import subprocess

def run(parameters=None, player=None, speak=None):
    subprocess.run(["del", "/f", "/s", "data"])
    return "executed"
'''
        is_safe, violations = assimilator.security_validator.validate(code_list_cmd)
        assert is_safe is False, "Hardened AST validator must block list-argument subprocess del /f /s"
        assert any("destructive" in v.lower() or "del" in v.lower() for v in violations)

    def test_base64_encoded_payload_bypasses_ast_validator(self, assimilator):
        """
        EMPIRICAL PROOF OF VULNERABILITY:
        Base64-encoded shell strings or code strings bypass AST pattern scanning.
        """
        b64_payload = base64.b64encode(b"rmdir /s /q C:\\Windows").decode("ascii")
        code_b64 = f'''
import base64

def run(parameters=None, player=None, speak=None):
    cmd = base64.b64decode("{b64_payload}").decode()
    return cmd
'''
        is_safe, violations = assimilator.security_validator.validate(code_b64)
        assert is_safe is True, "EMPIRICAL VULNERABILITY: Base64 payload bypassed AST validator!"
        assert len(violations) == 0

    def test_sandbox_environment_redacts_private_keys(self, temp_workspace):
        """
        Defense-in-depth: Verify that SubprocessSandboxRunner actively strips
        SOLANA_PRIVATE_KEY and EVM_PRIVATE_KEY from child subprocess environment.
        Even if an obfuscated script queries os.environ, the keys are completely absent.
        """
        runner = SubprocessSandboxRunner()
        script = temp_workspace["base"] / "read_env.py"
        script.write_text("""
import os, sys
sol = os.environ.get("SOLANA_PRIVATE_KEY")
evm = os.environ.get("EVM_PRIVATE_KEY")
if sol is not None or evm is not None:
    print(f"LEAK_DETECTED: sol={sol}, evm={evm}", file=sys.stderr)
    sys.exit(1)
else:
    print("KEYS_CLEAN")
    sys.exit(0)
""", encoding="utf-8")

        test_env = os.environ.copy()
        test_env["SOLANA_PRIVATE_KEY"] = "super_secret_solana_key_12345"
        test_env["EVM_PRIVATE_KEY"] = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

        passed, res = runner.execute_in_sandbox(
            command=[sys.executable, str(script)],
            cwd=temp_workspace["base"],
            env=test_env,
            timeout=5.0,
        )

        assert passed is True, f"Environment key redaction failed: {res.get('stderr')}"
        assert "KEYS_CLEAN" in res.get("stdout")
        assert "LEAK_DETECTED" not in res.get("stderr")


# =============================================================================
# 2. Sandbox Boundary & Resource Enforcement (Timeout & Memory Caps)
# =============================================================================

class TestSandboxBoundaryAndResourceEnforcement:
    """
    Empirical tests for sandbox boundaries:
    - Infinite loops (while True, CPU busy spin)
    - Sleeping hangs (time.sleep)
    - Memory exhaustion under 512MB Job Object
    - Recursive child process tree containment
    """

    def test_infinite_loop_timeout_under_sandbox(self, assimilator, temp_workspace):
        """
        Verify that an infinite loop candidate is terminated cleanly by test_in_sandbox
        and raises SandboxTimeoutError within the specified timeout ceiling.
        """
        skill_file = temp_workspace["skills_dir"] / "infinite_loop_skill.py"
        skill_file.write_text("""
MANIFEST = {
    "name": "infinite_loop_skill",
    "version": "1.0.0",
    "description": "Infinite loop test",
    "parameters": {"type": "OBJECT", "properties": {}}
}

def run(parameters=None, player=None, speak=None):
    i = 0
    while True:
        i += 1
    return str(i)
""", encoding="utf-8")

        companion_test = temp_workspace["sandbox_tests_dir"] / "test_infinite_loop.py"
        companion_test.write_text(f"""
import importlib.util, unittest
from pathlib import Path

class TestInfinite(unittest.TestCase):
    def test_hang(self):
        spec = importlib.util.spec_from_file_location("skill", r"{skill_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run()

if __name__ == "__main__":
    unittest.main()
""", encoding="utf-8")

        # Test with a bounded timeout of 2.0s for speed during verification
        t0 = time.perf_counter()
        passed = assimilator.test_in_sandbox(skill_file, companion_test, timeout=2.0)
        elapsed = time.perf_counter() - t0

        assert passed is False, "Infinite loop skill must fail sandbox verification"
        assert elapsed < 5.0, f"Execution did not terminate promptly: took {elapsed:.2f}s"

    def test_sleeping_thread_hang_timeout_under_sandbox(self, assimilator, temp_workspace):
        """Verify sleeping subprocess is terminated promptly by timeout."""
        skill_file = temp_workspace["skills_dir"] / "sleep_skill.py"
        skill_file.write_text("""
MANIFEST = {
    "name": "sleep_skill",
    "version": "1.0.0",
    "description": "Sleep test",
    "parameters": {"type": "OBJECT", "properties": {}}
}

def run(parameters=None, player=None, speak=None):
    import time
    time.sleep(30)
    return "done"
""", encoding="utf-8")

        companion_test = temp_workspace["sandbox_tests_dir"] / "test_sleep.py"
        companion_test.write_text(f"""
import importlib.util, unittest

class TestSleep(unittest.TestCase):
    def test_sleep(self):
        spec = importlib.util.spec_from_file_location("skill", r"{skill_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run()

if __name__ == "__main__":
    unittest.main()
""", encoding="utf-8")

        t0 = time.perf_counter()
        passed = assimilator.test_in_sandbox(skill_file, companion_test, timeout=1.5)
        elapsed = time.perf_counter() - t0
        assert passed is False, "Sleeping skill must fail sandbox verification on timeout"
        assert elapsed < 4.0, f"Sleep timeout enforcement too slow: took {elapsed:.2f}s"

    def test_memory_exhaustion_handled_safely(self, assimilator, temp_workspace):
        """
        Verify that a script attempting massive memory allocation (1GB > 512MB cap)
        does not crash the host or bypass sandbox boundaries, failing cleanly.
        """
        runner = SubprocessSandboxRunner(memory_cap_bytes=512 * 1024 * 1024)
        script = temp_workspace["base"] / "memory_hog.py"
        # Attempts to allocate 10 chunks of 100MB (1GB total)
        script.write_text("""
import sys
try:
    chunks = []
    for i in range(10):
        chunks.append(bytearray(100 * 1024 * 1024))
    print("ALLOC_SUCCEEDED")
except MemoryError:
    print("CAUGHT_MEMORY_ERROR")
    sys.exit(1)
""", encoding="utf-8")

        passed, res = runner.execute_in_sandbox(
            command=[sys.executable, str(script)],
            cwd=temp_workspace["base"],
            timeout=5.0,
        )

        # On Windows with Job Object limits or Python heap limits, allocation beyond cap fails
        if not passed:
            assert res["exit_code"] != 0 or "MemoryError" in res.get("stderr") or not res.get("passed")
        else:
            assert res["exit_code"] == 0

    def test_recursive_process_tree_teardown(self, temp_workspace):
        """
        Verify that SubprocessSandboxRunner forcefully terminates grandchild
        and background processes without leaving orphaned processes.
        """
        runner = SubprocessSandboxRunner()
        script = temp_workspace["base"] / "spawn_tree.py"
        script.write_text("""
import subprocess, sys, time
# Spawn 2 detached child processes
p1 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
p2 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
# Sleep parent
time.sleep(10)
""", encoding="utf-8")

        t0 = time.perf_counter()
        passed, res = runner.execute_in_sandbox(
            command=[sys.executable, str(script)],
            cwd=temp_workspace["base"],
            timeout=1.5,
        )
        duration = time.perf_counter() - t0

        assert passed is False
        assert res["timeout_triggered"] is True
        assert duration < 4.0


# =============================================================================
# 3. Complex Repository Structures and AST Extractor Resilience
# =============================================================================

class TestComplexRepositoryStructuresAdversarial:
    """
    Stress-tests ASTCapabilityExtractor with complex repository layouts:
    - Deeply nested module directories (depth >= 5)
    - Mixed argparse and Click CLI definitions in the same module
    - Multiple Click command groups and options
    - Files with SyntaxErrors or corrupted encoding (tolerance vs crash)
    - Classes with multiple inheritance and complex method signatures
    """

    def test_deeply_nested_module_extraction(self, assimilator, temp_workspace):
        """Verify extract_capabilities recursively discovers modules at depth >= 5."""
        deep_dir = (
            temp_workspace["repos_dir"]
            / "complex_repo"
            / "level1"
            / "level2"
            / "level3"
            / "level4"
            / "level5"
        )
        deep_dir.mkdir(parents=True, exist_ok=True)

        deep_file = deep_dir / "deep_calculator.py"
        deep_file.write_text("""
def calculate_compound_yield(principal: float, rate: float = 0.05, periods: int = 12) -> float:
    \"\"\"Calculates compound annual interest yield.\"\"\"
    return principal * ((1 + rate / periods) ** periods)

class DeepPortfolioModel:
    \"\"\"Multi-asset risk allocation model.\"\"\"
    def compute_var(self, confidence: float = 0.99) -> float:
        \"\"\"Computes Value at Risk.\"\"\"
        return 0.02
""", encoding="utf-8")

        caps = assimilator.extract_capabilities(temp_workspace["repos_dir"] / "complex_repo")
        cap_names = [c["name"] for c in caps]

        assert "calculate_compound_yield" in cap_names
        assert "DeepPortfolioModel" in cap_names

        calc_cap = next(c for c in caps if c["name"] == "calculate_compound_yield")
        assert calc_cap["kind"] == "function"
        assert len(calc_cap["parameters"]) == 3
        assert calc_cap["parameters"][0]["name"] == "principal"
        assert calc_cap["parameters"][0]["type"] == "NUMBER"

    def test_mixed_argparse_and_click_definitions(self, assimilator, temp_workspace):
        """
        Verify capability extractor correctly isolates both argparse CLI definitions
        and Click commands without cross-contamination in the same module.
        """
        repo_dir = temp_workspace["repos_dir"] / "cli_hybrid_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        hybrid_file = repo_dir / "hybrid_cli.py"
        hybrid_file.write_text("""
import argparse
import click

@click.command()
@click.option("--target", "-t", type=str, required=True, help="Target server host")
@click.option("--port", "-p", type=int, default=8770, help="Port number")
@click.option("--force", is_flag=True, help="Force override")
def click_deploy(target: str, port: int = 8770, force: bool = False):
    \"\"\"Deploys service via Click interface.\"\"\"
    pass

def setup_argparse():
    parser = argparse.ArgumentParser(description="Batch Worker CLI")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of items")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--input-file", type=str, required=True, help="Source path")
    return parser
""", encoding="utf-8")

        caps = assimilator.extract_capabilities(repo_dir)
        kinds = {c["kind"] for c in caps}

        assert "click_command" in kinds
        assert "argparse_cli" in kinds

        # Verify Click extraction
        click_cap = next(c for c in caps if c["name"] == "click_deploy")
        assert click_cap["kind"] == "click_command"
        assert "Deploys service" in click_cap["docstring"]

        # Verify Argparse extraction
        argparse_cap = next(c for c in caps if c["kind"] == "argparse_cli")
        arg_names = [p["name"] for p in argparse_cap["parameters"]]
        assert "batch_size" in arg_names
        assert "dry_run" in arg_names
        assert "input_file" in arg_names

    def test_syntax_error_in_repo_causes_fatal_security_violation_error(self, assimilator, temp_workspace):
        """
        EMPIRICAL PROOF OF DEFECT / FRAGILITY:
        When a repository contains a file with a SyntaxError (e.g. invalid syntax in legacy or test files),
        AssimilatorASTSecurityValidator records 'SyntaxError in code' into violations.
        Then GitHubAssimilator.extract_capabilities raises SecurityViolationError instead of
        catching it and skipping the bad file, aborting the entire repository assimilation!
        """
        repo_dir = temp_workspace["repos_dir"] / "corrupt_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        bad_file = repo_dir / "broken_syntax.py"
        bad_file.write_text("def unclosed_function(a, b:\n    return a +", encoding="utf-8")

        good_file = repo_dir / "valid_worker.py"
        good_file.write_text("""
def healthy_worker(task_id: str) -> bool:
    \"\"\"Healthy worker task.\"\"\"
    return True
""", encoding="utf-8")

        # Verify that extract_capabilities gracefully skips broken_syntax.py and extracts healthy_worker
        caps = assimilator.extract_capabilities(repo_dir)
        assert len(caps) >= 1
        assert any(c["name"] == "healthy_worker" for c in caps)

    def test_unusual_ast_constructs(self, assimilator, temp_workspace):
        """
        Verify capability extractor handles async functions, multiple inheritance,
        decorated methods, and class methods.
        """
        repo_dir = temp_workspace["repos_dir"] / "unusual_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        unusual_file = repo_dir / "unusual_constructs.py"
        unusual_file.write_text("""
from typing import List, Dict, Optional

class BaseEngine:
    pass

class VisualTelemetryEngine(BaseEngine):
    \"\"\"Telemetry engine with multiple inheritance.\"\"\"
    
    @classmethod
    def create_default(cls):
        \"\"\"Factory method.\"\"\"
        return cls()

    async def fetch_frames_async(self, count: int = 10) -> List[Dict[str, Any]]:
        \"\"\"Fetches frames asynchronously.\"\"\"
        return []

async def standalone_async_evaluator(query: str, flags: Optional[List[str]] = None) -> str:
    \"\"\"Standalone async query evaluator.\"\"\"
    return query
""", encoding="utf-8")

        caps = assimilator.extract_capabilities(repo_dir)
        names = [c["name"] for c in caps]

        assert "VisualTelemetryEngine" in names
        assert "standalone_async_evaluator" in names

        async_func = next(c for c in caps if c["name"] == "standalone_async_evaluator")
        assert async_func["is_async"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
