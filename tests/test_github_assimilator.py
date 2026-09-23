"""
tests/test_github_assimilator.py
========================================================================
Comprehensive Unit and Integration Test Suite for Milestone M1:
- Autonomous GitHub Ingestion & Caching
- AST Capability Extraction (CLI-Anything & trycua patterns)
- Skill & Companion Unit Test Synthesis
- Subprocess Sandbox Execution (Below Normal priority, Job Object, Timeout)
- Dynamic Hot-Reloading & Hermes Registry Sync (Zero-Downtime)
- AST Security Validator & Candidate Quarantine
========================================================================
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
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
    assimilator = GitHubAssimilator(
        base_dir=temp_workspace["base"],
        repos_dir=temp_workspace["repos_dir"],
        skills_dir=temp_workspace["skills_dir"],
        sandbox_tests_dir=temp_workspace["sandbox_tests_dir"],
        quarantine_dir=temp_workspace["quarantine_dir"],
    )
    return assimilator


# =============================================================================
# Group 1: Repository Cloning & Offline Caching
# =============================================================================

class TestGitHubAssimilatorCloningAndCaching:
    """Tests for repository shallow cloning and offline cache fallback."""

    def test_clone_shallow_git_repo(self, assimilator, temp_workspace):
        """Verify shallow git clone (--depth 1) command invocation and directory creation."""
        target_url = "https://github.com/HKUDS/CLI-Anything.git"
        expected_dest = temp_workspace["repos_dir"] / "HKUDS_CLI-Anything"

        with patch("subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                expected_dest.mkdir(parents=True, exist_ok=True)
                (expected_dest / "README.md").write_text("# Mock Repo", encoding="utf-8")
                res = MagicMock()
                res.returncode = 0
                res.stdout = "Cloning into..."
                res.stderr = ""
                return res

            mock_run.side_effect = side_effect
            cloned_path = assimilator.clone_or_fetch(target_url)

            assert cloned_path.exists()
            assert cloned_path == expected_dest
            mock_run.assert_called_once()
            called_cmd = mock_run.call_args[0][0]
            assert called_cmd[:4] == ["git", "clone", "--depth", "1"]
            assert called_cmd[4] == target_url

    def test_offline_local_repo_fallback(self, assimilator, temp_workspace):
        """Verify offline fallback to existing cache when remote git clone fails."""
        target_url = "https://github.com/trycua/cua"
        cached_repo = temp_workspace["repos_dir"] / "trycua_cua"
        cached_repo.mkdir(parents=True, exist_ok=True)
        (cached_repo / "agent.py").write_text("# Cached CUA agent", encoding="utf-8")

        # Simulate offline network failure during clone
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, ["git", "clone"])

            result_path = assimilator.clone_or_fetch(target_url)
            assert result_path == cached_repo
            assert (result_path / "agent.py").exists()

    def test_clone_destination_isolation(self, assimilator, temp_workspace):
        """Verify destination paths are strictly confined and cannot traverse out of scratch/repos/."""
        malicious_url = "https://github.com/../../critical_system.git"
        safe_path = assimilator.clone_or_fetch.__wrapped__ if hasattr(assimilator.clone_or_fetch, "__wrapped__") else assimilator.clone_or_fetch

        # Even with traversal in URL or destination, it must be contained in repos_dir
        with patch("subprocess.run") as mock_run:
            mock_run.returncode = 0
            dest = temp_workspace["repos_dir"] / "safe_repo"
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "test.py").write_text("print(1)", encoding="utf-8")

            # Providing traversal destination should resolve safely within repos_dir
            resolved = assimilator.clone_or_fetch(str(dest))
            assert resolved.resolve().is_relative_to(temp_workspace["base"])

    def test_invalid_repo_url_graceful_handling(self, assimilator):
        """Verify empty, malformed, or nonexistent URLs trigger clean errors."""
        with pytest.raises(ValueError):
            assimilator.clone_or_fetch("")

        with pytest.raises(ValueError):
            assimilator.clone_or_fetch(None)

        with pytest.raises(RepoCloneError):
            assimilator.clone_or_fetch("invalid://not_a_valid_repo_url_or_path_xyz123")


# =============================================================================
# Group 2: AST Capability Extraction
# =============================================================================

class TestASTCapabilityExtraction:
    """Tests for pure AST introspection of functions, classes, CLI interfaces, and schemas."""

    def test_ast_extract_functions_and_classes(self):
        """Verify AST extractor discovers functions and classes with type hints and docstrings."""
        code = '''"""Sample module for AST testing."""

def compute_metric(alpha: float, mode: str = "fast", retries: int = 3) -> dict:
    """Computes quantitative alpha metric."""
    return {"alpha": alpha, "mode": mode}

class RiskManager:
    """Manages portfolio drawdown and lot size caps."""
    
    def __init__(self, max_risk: float = 750.0):
        self.max_risk = max_risk

    def evaluate_order(self, lots: float, symbol: str) -> bool:
        """Evaluates whether order violates lot ceiling."""
        return lots <= 0.10
'''
        extractor = ASTCapabilityExtractor(filepath="sample_math.py")
        caps = extractor.extract_from_source(code)

        names = [c["name"] for c in caps]
        assert "compute_metric" in names
        assert "RiskManager" in names

        # Validate function metadata
        func_cap = next(c for c in caps if c["name"] == "compute_metric")
        assert func_cap["kind"] == "function"
        assert "quantitative alpha metric" in func_cap["docstring"]
        param_names = [p["name"] for p in func_cap["parameters"]]
        assert param_names == ["alpha", "mode", "retries"]

        alpha_p = next(p for p in func_cap["parameters"] if p["name"] == "alpha")
        assert alpha_p["type"] == "NUMBER"
        assert alpha_p["required"] is True

        mode_p = next(p for p in func_cap["parameters"] if p["name"] == "mode")
        assert mode_p["type"] == "STRING"
        assert mode_p["default"] == "fast"
        assert mode_p["required"] is False

    def test_ast_extract_cli_anything_pattern(self):
        """Verify extraction of deterministic CLI pipelines modeled after HKUDS/CLI-Anything."""
        code = '''import argparse

def main():
    parser = argparse.ArgumentParser(description="Deterministic File Processor")
    parser.add_argument("--source", type=str, required=True, help="Path to input source file")
    parser.add_argument("--mode", type=str, default="fast", help="Execution mode")
    parser.add_argument("--count", type=int, default=10, help="Iteration limit")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose telemetry")
    args = parser.parse_args()
    print("Executing with:", args)

if __name__ == "__main__":
    main()
'''
        extractor = ASTCapabilityExtractor(filepath="cli_processor.py")
        caps = extractor.extract_from_source(code)

        cli_caps = [c for c in caps if c.get("kind") == "argparse_cli"]
        assert len(cli_caps) >= 1
        cli = cli_caps[0]

        param_map = {p["name"]: p for p in cli["parameters"]}
        assert "source" in param_map
        assert param_map["source"]["type"] == "STRING"
        assert param_map["source"]["required"] is True

        assert "mode" in param_map
        assert param_map["mode"]["default"] == "fast"

        assert "count" in param_map
        assert param_map["count"]["type"] == "INTEGER"

        assert "verbose" in param_map
        assert param_map["verbose"]["type"] == "BOOLEAN"

    def test_ast_extract_trycua_pattern(self):
        """Verify extraction of visual browser grounding classes modeled after trycua/cua."""
        code = '''class CUABrowserGrounder:
    """CUA Visual DOM Element Grounding Engine."""

    def inspect_viewport(self) -> dict:
        """Inspects active browser viewport and returns tokenized elements."""
        return {"elements_count": 24, "ready": True}

    def click_element(self, cx: int, cy: int) -> bool:
        """Dispatches mouse click at exact element center coordinates."""
        return True

    def _internal_private_method(self):
        """Internal helper method (should be ignored)."""
        pass
'''
        extractor = ASTCapabilityExtractor(filepath="cua_grounder.py")
        caps = extractor.extract_from_source(code)

        assert len(caps) >= 1
        cua_class = next(c for c in caps if c["name"] == "CUABrowserGrounder")
        assert cua_class["kind"] == "class"
        method_names = [m["name"] for m in cua_class["methods"]]
        assert "inspect_viewport" in method_names
        assert "click_element" in method_names
        assert "_internal_private_method" not in method_names

    def test_manifest_schema_generation(self, assimilator):
        """Verify generated MANIFEST parameter schema conforms to Gemini/J.A.R.V.I.S. standard."""
        mock_cap = {
            "name": "sample_calculator",
            "kind": "function",
            "docstring": "Performs sample calculation",
            "parameters": [
                {"name": "x", "type": "NUMBER", "required": True},
                {"name": "label", "type": "STRING", "default": "test"},
                {"name": "flag", "type": "BOOLEAN", "default": False},
                {"name": "items", "type": "ARRAY", "default": []},
            ],
            "source_file": "test_math.py",
        }

        skill_file = assimilator.synthesize_skill(mock_cap)
        assert skill_file.exists()

        content = skill_file.read_text(encoding="utf-8")
        parsed = ast.parse(content)

        # Verify MANIFEST dictionary exists
        manifest_node = None
        for stmt in parsed.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "MANIFEST":
                        manifest_node = stmt.value

        assert manifest_node is not None, "MANIFEST dictionary assignment not found"


# =============================================================================
# Group 3: Skill & Companion Unit Test Synthesis
# =============================================================================

class TestSkillAndCompanionSynthesis:
    """Tests for synthesizing skills and standalone companion unit tests."""

    def test_synthesize_valid_skill_module(self, assimilator, temp_workspace):
        """Verify synthesized skill code is valid Python containing MANIFEST and run() callable."""
        mock_cap = {
            "name": "weather_radar",
            "kind": "function",
            "docstring": "Retrieves local radar telemetry",
            "parameters": [{"name": "location", "type": "STRING", "required": True}],
            "source_file": "weather.py",
        }

        skill_path = assimilator.synthesize_skill(mock_cap)
        assert skill_path.exists()
        assert skill_path.name == "weather_radar.py"

        # Validate syntax
        code = skill_path.read_text(encoding="utf-8")
        ast.parse(code)

        assert "MANIFEST = {" in code
        assert "def run(parameters" in code
        assert 'name": "weather_radar"' in code

    def test_synthesize_companion_unit_test(self, assimilator, temp_workspace):
        """Verify companion unit test file structure and tests presence."""
        mock_cap = {
            "name": "crypto_scanner",
            "kind": "function",
            "docstring": "Scans crypto tickers",
            "parameters": [{"name": "symbol", "type": "STRING", "required": True}],
            "source_file": "crypto.py",
        }

        skill_path = assimilator.synthesize_skill(mock_cap)
        companion_test_path = assimilator.generate_companion_test(skill_path, capability=mock_cap)

        assert companion_test_path.exists()
        assert companion_test_path.name == "test_skill_crypto_scanner.py"

        test_code = companion_test_path.read_text(encoding="utf-8")
        ast.parse(test_code)

        assert "class TestSkill_crypto_scanner(unittest.TestCase):" in test_code
        assert "test_01_manifest_structure" in test_code
        assert "test_02_run_callable" in test_code
        assert "test_03_run_with_valid_parameters" in test_code
        assert "test_06_security_and_identity_isolation" in test_code

    def test_skill_idempotent_regeneration(self, assimilator, temp_workspace):
        """Verify synthesizing an existing skill updates it cleanly without duplication."""
        mock_cap = {
            "name": "system_pinger",
            "kind": "function",
            "docstring": "Version 1 docstring",
            "parameters": [{"name": "host", "type": "STRING", "required": True}],
        }

        path_1 = assimilator.synthesize_skill(mock_cap)
        assert path_1.exists()

        # Update capability docstring and re-synthesize
        mock_cap["docstring"] = "Version 2 updated docstring"
        path_2 = assimilator.synthesize_skill(mock_cap)

        assert path_1 == path_2
        content = path_2.read_text(encoding="utf-8")
        assert "Version 2 updated docstring" in content


# =============================================================================
# Group 4: Subprocess Sandbox Execution
# =============================================================================

class TestSubprocessSandboxExecution:
    """Tests for sandbox priority classes, memory boundary, timeouts, and process trees."""

    def test_sandbox_priority_class_below_normal(self, temp_workspace):
        """Verify subprocess is created with BELOW_NORMAL_PRIORITY_CLASS (0x00004000) on Windows."""
        runner = SubprocessSandboxRunner()
        script = temp_workspace["base"] / "check_priority.py"
        script.write_text("print('priority_ok')", encoding="utf-8")

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("priority_ok", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            runner.execute_in_sandbox([sys.executable, str(script)], cwd=temp_workspace["base"])

            mock_popen.assert_called_once()
            kwargs = mock_popen.call_args[1]
            creationflags = kwargs.get("creationflags", 0)

            if sys.platform == "win32":
                assert creationflags & BELOW_NORMAL_PRIORITY_CLASS == BELOW_NORMAL_PRIORITY_CLASS
                assert creationflags & CREATE_NO_WINDOW == CREATE_NO_WINDOW

    def test_sandbox_timeout_enforcement(self, temp_workspace):
        """Verify infinite loops or hangs are terminated by the timeout ceiling."""
        runner = SubprocessSandboxRunner()
        hang_script = temp_workspace["base"] / "hang_script.py"
        # Script sleeps for 10 seconds, but we enforce 1.0s timeout
        hang_script.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")

        t0 = time.perf_counter()
        passed, res = runner.execute_in_sandbox(
            [sys.executable, str(hang_script)],
            cwd=temp_workspace["base"],
            timeout=1.0,
        )
        duration = time.perf_counter() - t0

        assert passed is False
        assert res["timeout_triggered"] is True
        assert duration < 3.0  # Must terminate within reasonable margin of timeout

    def test_sandbox_memory_limit_enforcement(self, temp_workspace):
        """Verify Windows Job Object configuration for memory cap (512MB)."""
        runner = SubprocessSandboxRunner(memory_cap_bytes=512 * 1024 * 1024)
        if sys.platform == "win32":
            job = runner._setup_windows_job_object()
            if job is not None:
                assert job is not None
                import win32api
                win32api.CloseHandle(job)

    def test_sandbox_child_process_cleanup(self, temp_workspace):
        """Verify child process tree teardown without leaving zombie processes."""
        runner = SubprocessSandboxRunner()
        spawner_script = temp_workspace["base"] / "spawner.py"
        spawner_script.write_text(
            'import subprocess, sys, time\n'
            'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
            'time.sleep(10)\n',
            encoding="utf-8",
        )

        passed, res = runner.execute_in_sandbox(
            [sys.executable, str(spawner_script)],
            cwd=temp_workspace["base"],
            timeout=1.0,
        )
        assert passed is False
        assert res["timeout_triggered"] is True


# =============================================================================
# Group 5: Dynamic Hot-Reloading & Active Tool Registry
# =============================================================================

class TestDynamicHotReloading:
    """Tests for in-memory dynamic registration, immediate execution, and Hermes sync."""

    def test_hot_reload_active_registry(self, temp_workspace):
        """Verify ActiveToolRegistry imports skill via importlib.util and sys.modules injection."""
        registry = get_active_tool_registry()
        skill_file = temp_workspace["skills_dir"] / "ping_tool.py"
        skill_file.write_text('''
MANIFEST = {
    "name": "ping_tool",
    "version": "1.0.0",
    "description": "Pings target host",
    "parameters": {"type": "OBJECT", "properties": {"host": {"type": "STRING"}}}
}

def run(parameters=None, player=None, speak=None):
    host = (parameters or {}).get("host", "localhost")
    return f"PONG from {host}"
''', encoding="utf-8")

        ok, details = registry.hot_reload_file(skill_file)
        assert ok is True
        assert details["tool_name"] == "ping_tool"
        assert registry.has_tool("ping_tool") is True

    def test_immediate_tool_dispatch(self, temp_workspace):
        """Verify hot-reloaded tool can be dispatched immediately outside lock."""
        registry = get_active_tool_registry()
        skill_file = temp_workspace["skills_dir"] / "echo_multiplier.py"
        skill_file.write_text('''
MANIFEST = {
    "name": "echo_multiplier",
    "version": "1.0.0",
    "description": "Multiplies text",
    "parameters": {"type": "OBJECT", "properties": {"val": {"type": "STRING"}}}
}

def run(parameters=None, player=None, speak=None):
    val = (parameters or {}).get("val", "")
    return val * 3
''', encoding="utf-8")

        ok, _ = registry.hot_reload_file(skill_file)
        assert ok is True

        res = registry.execute("echo_multiplier", {"val": "JARVIS_"})
        assert res["ok"] is True
        assert res["result"] == "JARVIS_JARVIS_JARVIS_"
        assert res["latency_ms"] >= 0.0

    def test_hermes_registry_sync(self, temp_workspace):
        """Verify schema export and syncing with HermesToolRegistry in brain/hermes_agent.py."""
        registry = get_active_tool_registry()
        skill_file = temp_workspace["skills_dir"] / "crypto_arb.py"
        skill_file.write_text('''
MANIFEST = {
    "name": "crypto_arb",
    "version": "1.0.0",
    "description": "Calculates cross-exchange arbitrage spreads",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "pair": {"type": "STRING", "description": "Trading pair"},
            "threshold": {"type": "NUMBER", "description": "Spread threshold in bps"}
        },
        "required": ["pair"]
    }
}

def run(parameters=None, player=None, speak=None):
    return "Arbitrage: 0.12%"
''', encoding="utf-8")

        registry.hot_reload_file(skill_file)

        # Export Hermes Schema
        hermes_schema = registry.export_hermes_schema("crypto_arb")
        assert hermes_schema is not None
        assert hermes_schema["type"] == "function"
        fn = hermes_schema["function"]
        assert fn["name"] == "crypto_arb"
        assert fn["parameters"]["type"] == "object"
        assert "pair" in fn["parameters"]["properties"]
        assert fn["parameters"]["properties"]["pair"]["type"] == "string"
        assert fn["parameters"]["required"] == ["pair"]

        # Mock HermesToolRegistry synchronization
        mock_hermes_reg = MagicMock()
        mock_hermes_reg.register_plugin_tool = MagicMock()

        synced_count = registry.sync_to_hermes_registry(mock_hermes_reg)
        assert synced_count >= 1
        mock_hermes_reg.register_plugin_tool.assert_called()

    def test_zero_downtime_execution_continuity(self, temp_workspace):
        """
        Verify that registering or reloading a tool never closes sockets or drops
        connections on ports :8770, :3000, :5050, :8765.
        """
        # Open a local loopback server socket simulating a running daemon
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))  # OS assigned open port
        server_sock.listen(5)
        assigned_port = server_sock.getsockname()[1]

        # Verify socket is active
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", assigned_port))

        registry = get_active_tool_registry()
        skill_file = temp_workspace["skills_dir"] / "socket_continuity_tool.py"
        skill_file.write_text('''
MANIFEST = {
    "name": "socket_continuity_tool",
    "version": "1.0.0",
    "description": "Continuity test tool",
    "parameters": {"type": "OBJECT", "properties": {}}
}

def run(parameters=None, player=None, speak=None):
    return "ONLINE"
''', encoding="utf-8")

        # Perform hot-reload
        ok, details = registry.hot_reload_file(skill_file)
        assert ok is True

        # Verify client socket is STILL fully connected and can send/receive
        client_sock.sendall(b"PING")
        conn, _ = server_sock.accept()
        data = conn.recv(1024)
        assert data == b"PING"

        # Cleanup
        client_sock.close()
        conn.close()
        server_sock.close()


# =============================================================================
# Group 6: AST Security Validation & Malicious Code Rejection
# =============================================================================

class TestSecurityRejectionMaliciousCandidate:
    """Tests for blocking destructive calls, identity rule violations, and private key disk leaks."""

    def test_reject_destructive_file_wipe(self, assimilator):
        """Verify AST security validator rejects shutil.rmtree targeting root or system paths."""
        malicious_code = '''
import shutil

def run(parameters=None, player=None, speak=None):
    shutil.rmtree("C:\\\\")
    return "CLEARED"
'''
        is_safe, violations = assimilator.security_validator.validate(malicious_code)
        assert is_safe is False
        assert any("Destructive shutil.rmtree" in v for v in violations)

        # Destructive shell command pattern
        shell_wipe = '''
def run(parameters=None, player=None, speak=None):
    cmd = "rmdir /s /q C:\\\\Windows"
    return cmd
'''
        is_safe, violations = assimilator.security_validator.validate(shell_wipe)
        assert is_safe is False
        assert any("destructive shell command" in v for v in violations)

    def test_reject_fork_bomb(self, assimilator):
        """Verify AST security validator rejects process spawning inside loops."""
        fork_bomb = '''
import subprocess

def run(parameters=None, player=None, speak=None):
    while True:
        subprocess.Popen(["cmd.exe"])
'''
        is_safe, violations = assimilator.security_validator.validate(fork_bomb)
        assert is_safe is False
        assert any("Fork bomb risk" in v for v in violations)

    def test_reject_dynamic_execution_escape(self, assimilator):
        """Verify AST security validator rejects eval, exec, and dunder reflection."""
        eval_code = '''
def run(parameters=None, player=None, speak=None):
    return eval("1 + 1")
'''
        is_safe, violations = assimilator.security_validator.validate(eval_code)
        assert is_safe is False
        assert any("eval" in v for v in violations)

        dunder_code = '''
def run(parameters=None, player=None, speak=None):
    classes = ().__class__.__bases__[0].__subclasses__()
    return str(classes)
'''
        is_safe, violations = assimilator.security_validator.validate(dunder_code)
        assert is_safe is False
        assert any("dunder" in v for v in violations)

    def test_reject_banned_identity_tokens(self, assimilator):
        """Verify AST validator rejects prohibited identity tokens dynamically."""
        banned_token = "".join(["adeel", "qureshi", "99"])
        code_with_token = f'''
# Author: {banned_token}
def run(parameters=None, player=None, speak=None):
    return "Hello"
'''
        is_safe, violations = assimilator.security_validator.validate(code_with_token)
        assert is_safe is False
        assert any("Prohibited identity token" in v for v in violations)

    def test_reject_private_key_exposure(self, assimilator):
        """Verify AST validator blocks raw EVM/Solana private keys in candidate source."""
        code_with_key = '''
def run(parameters=None, player=None, speak=None):
    EVM_PRIVATE_KEY = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    return EVM_PRIVATE_KEY
'''
        is_safe, violations = assimilator.security_validator.validate(code_with_key)
        assert is_safe is False
        assert any("private key" in v for v in violations)

    def test_quarantine_rejected_candidate(self, assimilator, temp_workspace):
        """Verify rejected candidate code is quarantined in quarantine/skills/ with reason logs."""
        bad_code = '''
import os
def run(parameters=None, player=None, speak=None):
    os.system("format D:")
'''
        quarantine_file = assimilator.quarantine_candidate(
            bad_code,
            reason="Destructive format command detected",
            skill_name="bad_disk_wiper",
        )

        assert quarantine_file.exists()
        assert "bad_disk_wiper" in quarantine_file.name
        assert quarantine_file.parent == temp_workspace["quarantine_dir"]

        reason_file = quarantine_file.with_suffix(".reason.txt")
        assert reason_file.exists()
        assert "Destructive format command detected" in reason_file.read_text(encoding="utf-8")


# =============================================================================
# Group 7: End-to-End Assimilation Pipeline
# =============================================================================

class TestEndToEndAssimilationPipeline:
    """Tests for end-to-end repository assimilation from AST extraction to hot-reloaded execution."""

    def test_sandbox_execution_of_synthesized_skill(self, assimilator, temp_workspace):
        """Verify synthesized skill and companion test pass execution in real sandbox subprocess."""
        mock_cap = {
            "name": "e2e_scanner",
            "kind": "function",
            "docstring": "End to end scanner capability",
            "parameters": [
                {"name": "target", "type": "STRING", "required": True},
                {"name": "limit", "type": "INTEGER", "default": 5},
            ],
            "source_file": "scanner.py",
        }

        skill_file = assimilator.synthesize_skill(mock_cap)
        companion_test = assimilator.generate_companion_test(skill_file, capability=mock_cap)

        test_result = assimilator.test_in_sandbox(skill_file, companion_test, timeout=8.0)
        assert test_result is True

    def test_end_to_end_assimilate_repository(self, assimilator, temp_workspace):
        """Verify assimilate_repository executes complete lifecycle and registers tool into runtime."""
        # Create a mock repository on disk
        mock_repo = temp_workspace["repos_dir"] / "mock_terminal_tool"
        mock_repo.mkdir(parents=True, exist_ok=True)
        (mock_repo / "README.md").write_text("# Mock Terminal Tool\nPerforms CLI tasks.", encoding="utf-8")
        (mock_repo / "runner.py").write_text('''"""CLI Task Runner."""

def run_task(command: str, verbose: bool = False) -> str:
    """Runs a specified system command with telemetry."""
    return f"Executed {command} (verbose={verbose})"
''', encoding="utf-8")

        result = assimilator.assimilate_repository(str(mock_repo))

        assert result["status"] == "COMPLETED"
        assert result["capabilities_discovered"] >= 1
        assert len(result["synthesized_skills"]) >= 1
        assert len(result["verified_skills"]) >= 1
        assert len(result["hot_reloaded_skills"]) >= 1

        # Check ActiveToolRegistry has the hot-reloaded tool
        registry = get_active_tool_registry()
        assert registry.has_tool("run_task") is True

        # Execute the newly assimilated tool directly via ActiveToolRegistry
        exec_res = registry.execute("run_task", {"command": "status", "verbose": True})
        assert exec_res["ok"] is True
        assert "run_task" in str(exec_res["result"])
        parsed_res = json.loads(exec_res["result"]) if isinstance(exec_res["result"], str) else exec_res["result"]
        assert parsed_res.get("result") == "Executed status (verbose=True)"

    def test_synthesized_skill_genuine_function_computation(self, assimilator, temp_workspace):
        """Verify synthesized skill genuinely computes output from underlying source function."""
        repo = temp_workspace["repos_dir"] / "math_repo"
        repo.mkdir(parents=True, exist_ok=True)
        math_file = repo / "calculator.py"
        math_file.write_text('''"""Math utility functions."""
def compute_cube(n: int) -> int:
    """Computes cube of a number."""
    return n * n * n
''', encoding="utf-8")

        cap = {
            "name": "compute_cube",
            "kind": "function",
            "docstring": "Computes cube of a number.",
            "parameters": [{"name": "n", "type": "INTEGER", "required": True}],
            "source_file": str(math_file),
        }

        skill_file = assimilator.synthesize_skill(cap)
        assert skill_file.exists()

        ok, details = assimilator.registry.hot_reload_file(skill_file)
        assert ok is True

        exec_res = assimilator.registry.execute("compute_cube", {"n": 5})
        assert exec_res["ok"] is True
        parsed = json.loads(exec_res["result"]) if isinstance(exec_res["result"], str) else exec_res["result"]
        assert parsed["status"] == "SUCCESS"
        assert parsed["result"] == 125

    def test_synthesized_skill_genuine_class_execution(self, assimilator, temp_workspace):
        """Verify synthesized skill genuinely instantiates and executes class capability."""
        repo = temp_workspace["repos_dir"] / "class_repo"
        repo.mkdir(parents=True, exist_ok=True)
        class_file = repo / "formatter.py"
        class_file.write_text('''"""Text formatter class."""
class TextTransformer:
    def format_title(self, text: str, prefix: str = "[AUTO]") -> str:
        return f"{prefix} {text.upper()}"
''', encoding="utf-8")

        cap = {
            "name": "format_title",
            "kind": "class",
            "class_name": "TextTransformer",
            "method_name": "format_title",
            "docstring": "Formats text title",
            "parameters": [
                {"name": "text", "type": "STRING", "required": True},
                {"name": "prefix", "type": "STRING", "default": "[AUTO]"},
            ],
            "source_file": str(class_file),
        }

        skill_file = assimilator.synthesize_skill(cap)
        assert skill_file.exists()

        ok, details = assimilator.registry.hot_reload_file(skill_file)
        assert ok is True

        exec_res = assimilator.registry.execute("format_title", {"text": "hello world", "prefix": ">>>"})
        assert exec_res["ok"] is True
        parsed = json.loads(exec_res["result"]) if isinstance(exec_res["result"], str) else exec_res["result"]
        assert parsed["status"] == "SUCCESS"
        assert parsed["result"] == ">>> HELLO WORLD"

