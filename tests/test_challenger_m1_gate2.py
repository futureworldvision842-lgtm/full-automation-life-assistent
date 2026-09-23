"""
tests/test_challenger_m1_gate2.py
========================================================================
Gate 2 Empirical Adversarial Stress Test Suite for Milestone M1
Author: teamwork_preview_challenger_m1_gate2_2 (Empirical Challenger)
Roles: critic, specialist

Mission:
Adversarially challenge the hardened AST Security Validator and repository ingestion:
1. Test evasions against builtins.eval, builtins.exec, getattr(builtins, "eval"), getattr(os, "system")
2. Test list-form subprocess shell commands (subprocess.run(["del", "/f", ...]))
3. Test graceful skipping of syntax error files in ingested repos
4. Test sandbox verification boundary defense and error trapping
5. Test ActiveToolRegistry pre-execution security and atomic rollback
========================================================================
"""

from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

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
    AssimilatorASTSecurityValidator,
    ASTCapabilityExtractor,
    ASTParsingError,
    BannedIdentityError,
    DestructiveCodeError,
    GitHubAssimilator,
    HotReloadError,
    RepoCloneError,
    RiskCeilingViolationError,
    SecurityViolationError,
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
# 1. Challenge: Evasions against builtins.eval/exec and getattr reflection
# =============================================================================

class TestASTBuiltinsAndReflectionEvasions:
    """
    Adversarial evaluation of AST Security Validator against obfuscated
    and reflected invocation of execution primitives and dangerous OS methods.
    """

    def test_direct_builtins_eval_and_exec_blocked(self, assimilator):
        """Verify builtins.eval and builtins.exec direct calls are rejected."""
        payloads = [
            "import builtins\nbuiltins.eval('1+1')",
            "import builtins\nbuiltins.exec('x = 1')",
            "import builtins as b\nb.eval('1+1')",
            "import builtins as b\nb.exec('x = 1')",
            "from builtins import eval\neval('1+1')",
            "from builtins import exec\nexec('x = 1')",
            "from builtins import compile\ncompile('1+1', '', 'eval')",
            "from builtins import __import__\n__import__('os')",
            "from __builtins__ import eval\neval('1+1')",
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Payload should be blocked: {code}"
            assert len(violations) >= 1

    def test_dynamic_importlib_primitives_blocked(self, assimilator):
        """Verify importlib dynamic loading primitives are rejected."""
        payloads = [
            "from importlib import import_module\nmod = import_module('os')",
            "from importlib import __import__\nmod = __import__('os')",
            "import importlib\nmod = importlib.import_module('os')",
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"importlib payload should be blocked: {code}"
            assert any("import" in v.lower() for v in violations)

    def test_getattr_builtins_eval_and_exec_reflection_blocked(self, assimilator):
        """Verify getattr(builtins, 'eval') and variants are rejected."""
        payloads = [
            'f = getattr(builtins, "eval")',
            'f = getattr(builtins, "exec")',
            'f = getattr(__builtins__, "eval")',
            'f = getattr(__builtins__, "exec")',
            'f = getattr(builtins, "compile")',
            'f = getattr(builtins, "__import__")',
            'f = getattr(builtins, "import_module")',
            'f = getattr(mod, "eval")',
            'f = getattr(x, "exec")',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"getattr execution reflection should be blocked: {code}"
            assert any("getattr" in v or "reflection" in v or "builtins" in v for v in violations)

    def test_getattr_os_system_and_primitives_blocked(self, assimilator):
        """Verify getattr(os, 'system') and OS primitives are rejected."""
        payloads = [
            'getattr(os, "system")("dir")',
            'getattr(os, "popen")("dir")',
            'getattr(os, "spawnl")(0, "cmd")',
            'getattr(os, "kill")(123, 9)',
            'getattr(os, "fork")()',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"getattr OS primitive should be blocked: {code}"
            assert any("os" in v.lower() or "getattr" in v.lower() for v in violations)

    def test_getattr_with_folded_string_concatenation_blocked(self, assimilator):
        """Verify getattr with binary addition ('ev' + 'al') is folded and blocked."""
        payloads = [
            'getattr(builtins, "ev" + "al")',
            'getattr(builtins, "ex" + "ec")',
            'getattr(os, "sys" + "tem")',
            'getattr(os, "pop" + "en")',
            'getattr(builtins, "comp" + "ile")',
            'getattr(builtins, "__im" + "port__")',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Folded getattr should be blocked: {code}"
            assert len(violations) >= 1

    def test_dunder_reflection_in_getattr_blocked(self, assimilator):
        """Verify sandbox-escape dunders via getattr are blocked."""
        payloads = [
            'getattr(obj, "__subclasses__")',
            'getattr(cls, "__bases__")',
            'getattr(fn, "__globals__")',
            'getattr(fn, "__code__")',
            'getattr(fn, "__mro__")',
            'getattr(fn, "__builtins__")',
            'getattr(obj, "__sub" + "classes__")',
            'getattr(fn, "__glo" + "bals__")',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Dunder reflection should be blocked: {code}"
            assert any("dunder" in v.lower() or "reflection" in v.lower() for v in violations)

    def test_banned_modules_import_blocked(self, assimilator):
        """Verify BANNED_MODULES cannot be imported."""
        banned = ["builtins", "ctypes", "winreg", "msvcrt", "win32con", "win32gui", "win32process", "win32api"]
        for mod in banned:
            code1 = f"import {mod}"
            is_safe1, _ = assimilator.security_validator.validate(code1)
            assert not is_safe1, f"Import of {mod} should be blocked"

            code2 = f"from {mod} import something"
            is_safe2, _ = assimilator.security_validator.validate(code2)
            assert not is_safe2, f"Import from {mod} should be blocked"

    def test_concatenated_identity_tokens_strictly_blocked(self, assimilator):
        """Verify prohibited identity tokens assembled via string concatenation are detected."""
        token_parts = ["adeel", "qureshi", "99"]
        payloads = [
            f'user = "{token_parts[0]}" + "{token_parts[1]}" + "{token_parts[2]}"',
            f'user = "{token_parts[0]}" + "{token_parts[1]}{token_parts[2]}"',
            f'user = "{token_parts[0]}{token_parts[1]}" + "{token_parts[2]}"',
            f'user = "{"".join(token_parts)}"',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Identity token payload should be blocked: {code}"
            assert any("prohibited identity token" in v.lower() for v in violations)


# =============================================================================
# 2. Challenge: List-form subprocess shell commands
# =============================================================================

class TestListFormSubprocessShellCommands:
    """
    Adversarial evaluation of subprocess argument list / tuple inspection:
    - Destructive commands in list form (del, rmdir, rm, format, shutdown, mkfs)
    - Concatenated tokens inside lists
    - False positive resistance (legitimate safe commands must pass)
    """

    def test_destructive_del_in_list_form_blocked(self, assimilator):
        """Verify subprocess.run(['del', '/f', ...]) variants are blocked."""
        payloads = [
            'subprocess.run(["del", "/f", "target.txt"])',
            'subprocess.run(["del", "/s", "target.txt"])',
            'subprocess.run(["del", "/F", "/S", "target.txt"])',
            'subprocess.run(["del", "/s", "/f", "target.txt"])',
            'subprocess.run(["erase", "/f", "target.txt"])',
            'subprocess.run(["erase", "/s", "target.txt"])',
            'subprocess.Popen(["del", "/f", "target.txt"])',
            'subprocess.call(["del", "/f", "target.txt"])',
            'subprocess.check_call(["del", "/f", "target.txt"])',
            'subprocess.check_output(["del", "/f", "target.txt"])',
            'subprocess.run(args=["del", "/f", "target.txt"])',
            'subprocess.run(("del", "/f", "target.txt"))',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Destructive del command should be blocked: {code}"
            assert any("destructive" in v.lower() or "del" in v.lower() for v in violations)

    def test_destructive_rmdir_and_rm_in_list_form_blocked(self, assimilator):
        """Verify subprocess rmdir /s and rm -rf variants are blocked."""
        payloads = [
            'subprocess.run(["rmdir", "/s", "my_dir"])',
            'subprocess.run(["rmdir", "/s", "/q", "my_dir"])',
            'subprocess.run(["rmdir", "/S", "my_dir"])',
            'subprocess.run(["rm", "-rf", "/"])',
            'subprocess.run(["rm", "-fr", "C:\\\\"])',
            'subprocess.run(["rm", "-r", "-f", "/"])',
            'subprocess.run(["rm", "-rf", "~"])',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Destructive rmdir/rm command should be blocked: {code}"
            assert any("destructive" in v.lower() or "shell" in v.lower() for v in violations)

    def test_destructive_format_mkfs_shutdown_in_list_form_blocked(self, assimilator):
        """Verify format, mkfs, and shutdown in list form are blocked."""
        payloads = [
            'subprocess.run(["format", "D:"])',
            'subprocess.run(["mkfs", "/dev/sda1"])',
            'subprocess.run(["shutdown", "-s"])',
            'subprocess.run(["reboot"])',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Format/shutdown command should be blocked: {code}"
            assert any("destructive" in v.lower() for v in violations)

    def test_list_form_commands_with_concatenation_blocked(self, assimilator):
        """Verify folded string concatenation inside list elements is blocked."""
        payloads = [
            'subprocess.run(["d" + "el", "/f", "target.txt"])',
            'subprocess.run(["del", "/" + "f", "target.txt"])',
            'subprocess.run(["rm" + "dir", "/s", "target_dir"])',
            'cmd_list = ["d" + "el", "/f", "file.txt"]',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Concatenated list command should be blocked: {code}"
            assert any("destructive" in v.lower() for v in violations)

    def test_standalone_list_and_tuple_literals_blocked(self, assimilator):
        """Verify visit_List and visit_Tuple check destructive tokens even outside subprocess.run."""
        payloads = [
            'DANGEROUS = ["del", "/f", "target.txt"]',
            'DANGEROUS_TUPLE = ("rmdir", "/s", "c:\\temp")',
            'OPS = [["del", "/f", "x.log"], ["rmdir", "/s", "y"]]',
        ]
        for code in payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert not is_safe, f"Literal list/tuple with dangerous command should be blocked: {code}"
            assert len(violations) >= 1

    def test_legitimate_safe_subprocess_commands_allowed(self, assimilator):
        """
        FALSE POSITIVE RESISTANCE:
        Verify that harmless developer subprocess commands are NOT blocked.
        """
        safe_payloads = [
            'subprocess.run(["git", "status"])',
            'subprocess.run(["git", "clone", "--depth", "1", "https://github.com/repo"])',
            'subprocess.run(["python", "-m", "pytest", "tests/"])',
            'subprocess.run(["pip", "install", "-r", "requirements.txt"])',
            'subprocess.run(["echo", "operation complete"])',
            'subprocess.run(["npm", "run", "build"])',
            'subprocess.run(["ls", "-la"])',
            'subprocess.run(["dir"])',
            'subprocess.run(["python", "worker.py", "--mode", "production"])',
        ]
        for code in safe_payloads:
            is_safe, violations = assimilator.security_validator.validate(code)
            assert is_safe, f"Safe command was falsely blocked: {code} -> Violations: {violations}"
            assert len(violations) == 0


# =============================================================================
# 3. Challenge: Graceful skipping of syntax error files in ingested repos
# =============================================================================

class TestSyntaxErrorGracefulSkippingInIngestedRepos:
    """
    Adversarial evaluation of repository ingestion when corrupt, malformed,
    or legacy Python files with SyntaxErrors exist alongside valid modules.
    """

    def test_repo_with_multiple_syntax_errors_skips_and_extracts_healthy_modules(self, assimilator, temp_workspace):
        """
        Verify that a repository with 3 different types of syntax errors
        skips all bad files without raising SecurityViolationError, and
        successfully extracts capabilities from the healthy files.
        """
        repo_dir = temp_workspace["repos_dir"] / "mixed_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        # File 1: SyntaxError (unclosed parenthesis)
        (repo_dir / "err_unclosed_paren.py").write_text(
            "def broken_paren(a, b:\n    return a + b", encoding="utf-8"
        )

        # File 2: SyntaxError (unterminated triple-quote string)
        (repo_dir / "err_unterminated_str.py").write_text(
            '"""Unterminated docstring\ndef never_reached(): pass', encoding="utf-8"
        )

        # File 3: SyntaxError (invalid tokens / Python 2 legacy print)
        (repo_dir / "err_invalid_tokens.py").write_text(
            "def bad_syntax():\n    return %%% invalid", encoding="utf-8"
        )

        # File 4: Clean valid worker function
        (repo_dir / "clean_worker.py").write_text("""
def calculate_metrics(count: int, factor: float) -> float:
    \"\"\"Calculates business metrics cleanly.\"\"\"
    return float(count) * factor
""", encoding="utf-8")

        # File 5: Clean valid class
        (repo_dir / "clean_transformer.py").write_text("""
class DataFormatter:
    \"\"\"Formats raw data into structured payload.\"\"\"
    def format_text(self, raw: str) -> str:
        return f"[FORMATTED] {raw.strip()}"
""", encoding="utf-8")

        # Execute capability extraction
        caps = assimilator.extract_capabilities(repo_dir)

        # Assertions:
        # 1. Extraction must succeed without raising an exception
        assert isinstance(caps, list)
        assert len(caps) >= 2, f"Expected at least 2 capabilities extracted, got {len(caps)}"

        # 2. Extracted capabilities must contain clean_worker and clean_transformer
        extracted_names = [c["name"] for c in caps]
        assert any("calculate_metrics" in n for n in extracted_names), f"calculate_metrics missing in {extracted_names}"
        assert any("DataFormatter" in n for n in extracted_names), f"DataFormatter missing in {extracted_names}"

        # 3. Verify synthesis works on extracted clean capabilities
        worker_cap = next(c for c in caps if "calculate_metrics" in c["name"])
        skill_path = assimilator.synthesize_skill(worker_cap)
        assert skill_path.exists(), f"Synthesized skill file not found: {skill_path}"

        # 4. Verify synthesized skill runs cleanly
        res = assimilator.hot_reload_into_registry(skill_path)
        assert res["ok"] is True
        assert res["status"] == "REGISTERED"

    def test_repo_with_only_syntax_errors_returns_fallback_gracefully(self, assimilator, temp_workspace):
        """
        Verify that a repository containing ONLY files with SyntaxErrors does not crash,
        and returns the fallback capability to satisfy downstream caller contracts.
        """
        repo_dir = temp_workspace["repos_dir"] / "all_broken_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        (repo_dir / "broken1.py").write_text("class Unfinished:", encoding="utf-8")
        (repo_dir / "broken2.py").write_text("def no_body()", encoding="utf-8")

        caps = assimilator.extract_capabilities(repo_dir)
        assert isinstance(caps, list)
        assert len(caps) >= 1
        assert caps[0]["name"] == "cli_anything_tool"

    def test_syntax_error_file_with_prohibited_token_is_not_cloaked(self, assimilator, temp_workspace):
        """
        SECURITY VETTING:
        An attacker attempts to evade detection by embedding a prohibited identity token
        or destructive command inside a file with invalid syntax, hoping the validator
        skips it as a benign syntax error.
        Verify that SecurityViolationError / BannedIdentityError is STILL raised!
        """
        repo_dir = temp_workspace["repos_dir"] / "trojan_syntax_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        # Embedding prohibited token in invalid syntax
        banned_token = "".join(["adeel", "qureshi", "99"])
        trojan_file = repo_dir / "trojan.py"
        trojan_file.write_text(f"def broken_func(\n    # {banned_token}\n    return 42", encoding="utf-8")

        with pytest.raises(BannedIdentityError) as exc_info:
            assimilator.extract_capabilities(repo_dir)

        assert "Prohibited identity token" in str(exc_info.value)

    def test_syntax_error_file_with_destructive_command_is_gracefully_skipped(self, assimilator, temp_workspace):
        """
        Verify that an unparseable file with broken syntax is safely and gracefully skipped
        without crashing the repository assimilation process, and no capabilities are extracted from it.
        """
        repo_dir = temp_workspace["repos_dir"] / "trojan_cmd_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        trojan_file = repo_dir / "trojan_cmd.py"
        trojan_file.write_text("def broken(\n    cmd = 'rmdir /s /q C:\\\\Windows'\n", encoding="utf-8")

        valid_file = repo_dir / "valid_module.py"
        valid_file.write_text("def valid_tool() -> str:\n    return 'safe'\n", encoding="utf-8")

        caps = assimilator.extract_capabilities(repo_dir)
        assert len(caps) >= 1
        # Only valid_tool must be extracted, trojan_cmd must be completely omitted
        cap_names = [c["name"] for c in caps]
        assert "valid_tool" in cap_names
        assert "broken" not in cap_names

    def test_valid_syntax_with_destructive_command_raises_destructive_code_error(self, assimilator, temp_workspace):
        """
        Verify that when syntax is valid, destructive shell command triggers DestructiveCodeError.
        """
        repo_dir = temp_workspace["repos_dir"] / "real_destructive_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        bad_file = repo_dir / "destroy.py"
        bad_file.write_text("def bad_func():\n    cmd = 'rmdir /s /q C:\\\\Windows'\n    return cmd\n", encoding="utf-8")

        with pytest.raises(DestructiveCodeError) as exc_info:
            assimilator.extract_capabilities(repo_dir)

        assert "destructive" in str(exc_info.value).lower()


# =============================================================================
# 4. Challenge: Sandbox verification & error trapping
# =============================================================================

class TestSandboxVerificationAndErrorTrapping:
    """
    Adversarial evaluation of test_in_sandbox:
    - Return type strict contract (bool)
    - Timeout ceiling enforcement
    - Infinite loop trapping
    - Non-zero exit code / assertion failure handling
    """

    def test_sandbox_returns_bool_on_all_outcomes(self, assimilator, temp_workspace):
        """Verify test_in_sandbox strictly returns bool as required by PROJECT.md."""
        # 1. Invalid timeout
        res_neg = assimilator.test_in_sandbox("nonexistent.py", timeout=-1.0)
        assert res_neg is False
        assert isinstance(res_neg, bool)

        # 2. Non-existent file
        res_non = assimilator.test_in_sandbox("missing_skill.py", timeout=2.0)
        assert res_non is False
        assert isinstance(res_non, bool)

        # 3. Infinite loop skill
        loop_skill = temp_workspace["skills_dir"] / "hang_skill.py"
        loop_skill.write_text("""
MANIFEST = {"name": "hang_skill", "version": "1.0", "description": "hang", "parameters": {}}
def run(p=None, player=None, speak=None):
    while True:
        pass
""", encoding="utf-8")
        res_loop = assimilator.test_in_sandbox(loop_skill, timeout=2.0)
        assert res_loop is False
        assert isinstance(res_loop, bool)

        # 4. Healthy skill
        healthy_skill = temp_workspace["skills_dir"] / "healthy_skill.py"
        healthy_skill.write_text("""
MANIFEST = {"name": "healthy_skill", "version": "1.0", "description": "healthy", "parameters": {}}
def run(p=None, player=None, speak=None):
    return "SUCCESS"
""", encoding="utf-8")
        res_healthy = assimilator.test_in_sandbox(healthy_skill, timeout=5.0)
        assert res_healthy is True
        assert isinstance(res_healthy, bool)


# =============================================================================
# 5. Challenge: ActiveToolRegistry Zero-Downtime & Atomic Rollback
# =============================================================================

class TestActiveToolRegistryLifecycleAndRollback:
    """
    Adversarial evaluation of ActiveToolRegistry:
    - Pre-execution security screening
    - Trapping SystemExit during hot reload
    - Clean sys.modules cleanup on failed compilation or execution
    - Zero server socket interruption
    """

    def test_hot_reload_rejects_banned_identity_before_exec(self, temp_workspace):
        """Verify ActiveToolRegistry blocks banned token before compiling/executing."""
        registry = get_active_tool_registry()
        banned_token = "".join(["adeel", "qureshi", "99"])

        bad_tool = temp_workspace["skills_dir"] / "bad_identity_tool.py"
        bad_tool.write_text(f"""
# {banned_token}
MANIFEST = {{"name": "bad_identity_tool", "version": "1.0", "description": "bad", "parameters": {{}}}}
def run(p=None, player=None, speak=None):
    return "bad"
""", encoding="utf-8")

        success, details = registry.hot_reload_file(bad_tool)
        assert success is False
        assert "Security violation" in details["error"]
        assert "bad_identity_tool" not in registry._tools

    def test_hot_reload_traps_system_exit_cleanly(self, temp_workspace):
        """Verify a tool calling sys.exit(1) on import does not crash the host process."""
        registry = get_active_tool_registry()

        exit_tool = temp_workspace["skills_dir"] / "exit_tool.py"
        exit_tool.write_text("""
import sys
sys.exit(42)
MANIFEST = {"name": "exit_tool", "version": "1.0", "description": "exit", "parameters": {}}
def run(p=None, player=None, speak=None):
    return "never"
""", encoding="utf-8")

        # Must not terminate host process
        success, details = registry.hot_reload_file(exit_tool)
        assert success is False
        assert "Module exec failed" in details["error"]
        assert "exit_tool" not in registry._tools
        assert "skills.exit_tool" not in sys.modules

    def test_hot_reload_atomic_rollback_on_broken_runtime(self, temp_workspace):
        """
        Verify that if an existing working tool is reloaded with broken code,
        the registry preserves the existing working version or rolls back sys.modules cleanly.
        """
        registry = get_active_tool_registry()

        tool_path = temp_workspace["skills_dir"] / "resilient_tool.py"
        # Version 1 (Working)
        tool_path.write_text("""
MANIFEST = {"name": "resilient_tool", "version": "1.0", "description": "v1", "parameters": {}}
def run(p=None, player=None, speak=None):
    return "v1_result"
""", encoding="utf-8")

        success, details = registry.hot_reload_file(tool_path)
        assert success is True
        assert registry.get_tool("resilient_tool")() == "v1_result"

        # Version 2 (Broken runtime error)
        tool_path.write_text("""
raise RuntimeError("Catastrophic error during import")
MANIFEST = {"name": "resilient_tool", "version": "2.0", "description": "v2", "parameters": {}}
def run(p=None, player=None, speak=None):
    return "v2_result"
""", encoding="utf-8")

        success2, details2 = registry.hot_reload_file(tool_path)
        assert success2 is False
        # The previous version must still be callable or cleanly rolled back
        fn = registry.get_tool("resilient_tool")
        assert fn is not None
        assert fn() == "v1_result"
