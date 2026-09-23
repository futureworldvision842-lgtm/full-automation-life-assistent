"""
tests/test_adversarial_m1_challenger_stress.py
========================================================================
Adversarial Stress, Concurrency Contention, Atomic Rollback, and Memory
Leak Challenge Suite for ActiveToolRegistry and GitHubAssimilator.

Challenge Dimensions:
1. High-concurrency tool registration, unregistration, hot-reloading,
   and dispatch under multithreaded contention (20+ threads).
2. Corrupted or invalid python files during hot-reload to verify atomic
   rollback, state preservation, and security evaluation ordering.
3. Repeated rapid registration/unregistration cycles and module unregistration
   sys.modules memory leak verification.
4. Observer deadlock and subscriber contention under RLock.
========================================================================
"""

from __future__ import annotations

import gc
import importlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from core.active_tool_registry import (
    ActiveToolRegistry,
    ToolMetadata,
    get_active_tool_registry,
)
from tools.github_assimilator import (
    GitHubAssimilator,
    AssimilatorASTSecurityValidator,
    SubprocessSandboxRunner,
    BannedIdentityError,
    DestructiveCodeError,
    HotReloadError,
)

logger = logging.getLogger("TestAdversarialM1Stress")


@pytest.fixture(autouse=True)
def clean_registry_and_temp():
    """Ensure a clean registry state before and after each test."""
    registry = get_active_tool_registry()
    registry.clear()
    # Unsubscribe all observers
    with registry._lock:
        registry._subscribers.clear()

    temp_dir = Path("scratch") / "test_adversarial_stress"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    yield {
        "registry": registry,
        "temp_dir": temp_dir,
    }

    registry.clear()
    with registry._lock:
        registry._subscribers.clear()
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Dimension 1: High-Concurrency Tool Registration & Dispatch Contention
# =============================================================================

class TestConcurrencyAndMultithreadedContention:
    """Stress tests high contention across registration, dispatch, and hot-reload."""

    def test_concurrent_tool_execution_while_registering_and_unregistering(self, clean_registry_and_temp):
        """
        Adversarial test: 20 threads executing existing tools in tight loops
        while 10 threads concurrently register, update, and unregister other tools.
        Guarantees zero dictionary iteration crashes, zero deadlocks, and telemetry consistency.
        """
        registry = clean_registry_and_temp["registry"]

        # Register base tools
        for i in range(5):
            name = f"base_tool_{i}"
            manifest = {
                "name": name,
                "version": "1.0.0",
                "parameters": {"type": "OBJECT", "properties": {"val": {"type": "INTEGER"}}},
            }
            def handler(params, **kwargs):
                return params.get("val", 0) * 2
            registry.register(name, manifest, handler)

        stop_event = threading.Event()
        errors: List[str] = []
        execution_successes = [0]
        exec_lock = threading.Lock()

        # Reader/Executor worker
        def executor_worker(worker_id: int):
            while not stop_event.is_set():
                tool_idx = worker_id % 5
                target = f"base_tool_{tool_idx}"
                try:
                    res = registry.execute(target, {"val": worker_id})
                    if res.get("ok"):
                        with exec_lock:
                            execution_successes[0] += 1
                    else:
                        # If tool was unregistered, that's expected if it's dynamic,
                        # but base_tools are not unregistered
                        errors.append(f"Base tool execution failed: {res.get('error')}")
                except Exception as e:
                    errors.append(f"Exception during execute: {type(e).__name__}: {e}")
                time.sleep(0.001)

        # Modifier worker (rapid register / unregister of ephemeral tools)
        def modifier_worker(worker_id: int):
            cycle = 0
            while not stop_event.is_set():
                eph_name = f"eph_tool_{worker_id}_{cycle % 10}"
                try:
                    manifest = {
                        "name": eph_name,
                        "parameters": {"type": "OBJECT", "properties": {}},
                    }
                    registry.register(eph_name, manifest, lambda p, **kw: "eph_ok")
                    # Inspect registry state under contention
                    tools = registry.list_tools()
                    assert isinstance(tools, list)
                    # Dispatch to ephemeral tool
                    res = registry.execute(eph_name, {})
                    assert res.get("ok") is True
                    # Unregister
                    registry.unregister(eph_name)
                except Exception as e:
                    errors.append(f"Exception in modifier {worker_id}: {type(e).__name__}: {e}")
                cycle += 1
                time.sleep(0.002)

        threads = []
        # Launch 20 executor threads
        for i in range(20):
            t = threading.Thread(target=executor_worker, args=(i,), daemon=True)
            threads.append(t)
            t.start()

        # Launch 10 modifier threads
        for i in range(10):
            t = threading.Thread(target=modifier_worker, args=(i,), daemon=True)
            threads.append(t)
            t.start()

        # Let the stress run for 2.5 seconds
        time.sleep(2.5)
        stop_event.set()

        for t in threads:
            t.join(timeout=3.0)

        assert len(errors) == 0, f"Encountered concurrency errors: {errors[:5]}"
        assert execution_successes[0] > 1000, f"Expected >1000 successful executions, got {execution_successes[0]}"

        # Verify telemetry for base tools
        for i in range(5):
            name = f"base_tool_{i}"
            meta = next((m for m in registry.list_tools() if m["name"] == name), None)
            assert meta is not None
            assert meta["execution_count"] > 0
            assert meta["error_count"] == 0

    def test_concurrent_hot_reload_on_same_file_while_executing(self, clean_registry_and_temp):
        """
        Adversarial test: Multiple threads concurrently invoke hot_reload_file()
        on the exact same tool file while other threads execute it continuously.
        Verifies thread safety, atomic state swap, and monotonic version increments.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_file = temp_dir / "concurrent_tool.py"
        tool_code_template = """
MANIFEST = {{"name": "concurrent_tool", "version": "1.0.{ver}", "parameters": {{"type": "OBJECT", "properties": {{}}}}}}
def run(parameters=None, **kwargs):
    return "ver_{ver}"
"""
        # Write initial version
        tool_file.write_text(tool_code_template.format(ver=0), encoding="utf-8")
        ok, res = registry.hot_reload_file(tool_file)
        assert ok is True

        stop_event = threading.Event()
        errors: List[str] = []
        reloads_count = [0]
        exec_count = [0]
        lock = threading.Lock()

        def reloader_worker(w_id: int):
            c = 1
            while not stop_event.is_set():
                try:
                    tool_file.write_text(tool_code_template.format(ver=f"{w_id}_{c}"), encoding="utf-8")
                    ok, res = registry.hot_reload_file(tool_file)
                    if ok:
                        with lock:
                            reloads_count[0] += 1
                    else:
                        # Under high contention, file write might occasionally be partial if racing
                        pass
                except Exception as e:
                    errors.append(f"Reloader error: {e}")
                c += 1
                time.sleep(0.005)

        def executor_worker():
            while not stop_event.is_set():
                try:
                    res = registry.execute("concurrent_tool")
                    assert res.get("ok") is True
                    assert str(res.get("result")).startswith("ver_")
                    with lock:
                        exec_count[0] += 1
                except Exception as e:
                    errors.append(f"Executor error: {e}")
                time.sleep(0.001)

        threads = []
        for i in range(4):
            t = threading.Thread(target=reloader_worker, args=(i,), daemon=True)
            threads.append(t)
            t.start()

        for _ in range(10):
            t = threading.Thread(target=executor_worker, daemon=True)
            threads.append(t)
            t.start()

        time.sleep(2.0)
        stop_event.set()

        for t in threads:
            t.join(timeout=3.0)

        assert len(errors) == 0, f"Errors during concurrent reload: {errors[:5]}"
        assert reloads_count[0] > 10
        assert exec_count[0] > 500

        # Tool must still be registered and callable
        res_final = registry.execute("concurrent_tool")
        assert res_final.get("ok") is True


# =============================================================================
# Dimension 2: Corrupted or Invalid Files During Hot-Reload & Rollback
# =============================================================================

class TestHotReloadCorruptedFilesAndAtomicRollback:
    """Stress tests corrupted, invalid, and hostile files during hot_reload_file."""

    def test_syntax_error_file_triggers_atomic_rollback_of_existing_tool(self, clean_registry_and_temp):
        """
        Adversarial test: A working tool is modified to contain a fatal SyntaxError.
        hot_reload_file must return False, and the existing tool in registry
        MUST remain intact, callable, and producing the previous working output.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_path = temp_dir / "syntax_tool.py"
        valid_code = """
MANIFEST = {"name": "syntax_tool", "parameters": {"type": "OBJECT", "properties": {}}}
def run(parameters=None, **kwargs):
    return "v1_healthy"
"""
        tool_path.write_text(valid_code, encoding="utf-8")
        ok, res = registry.hot_reload_file(tool_path)
        assert ok is True
        assert registry.execute("syntax_tool")["result"] == "v1_healthy"

        # Overwrite with broken syntax
        broken_syntax = """
MANIFEST = {"name": "syntax_tool", "parameters": {"type": "OBJECT", "properties": {}}}
def run(parameters=None, **kwargs:
    this is completely broken syntax !!!
"""
        tool_path.write_text(broken_syntax, encoding="utf-8")
        ok_corrupt, res_corrupt = registry.hot_reload_file(tool_path)

        assert ok_corrupt is False, "hot_reload_file should fail on SyntaxError"
        assert "Module exec failed" in res_corrupt.get("error", "")

        # VERIFY ATOMIC ROLLBACK: Previous tool MUST still exist and return "v1_healthy"
        exec_after = registry.execute("syntax_tool")
        assert exec_after["ok"] is True
        assert exec_after["result"] == "v1_healthy"
        assert registry.get_manifest("syntax_tool")["name"] == "syntax_tool"

    def test_runtime_exception_during_module_exec_triggers_rollback(self, clean_registry_and_temp):
        """
        Adversarial test: A working tool is replaced with code that throws
        ZeroDivisionError on module import.
        Must rollback sys.modules and retain previous working version.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_path = temp_dir / "runtime_err_tool.py"
        tool_path.write_text("""
MANIFEST = {"name": "runtime_err_tool", "parameters": {"type": "OBJECT", "properties": {}}}
def run(parameters=None, **kwargs):
    return "v1_operational"
""", encoding="utf-8")

        ok, _ = registry.hot_reload_file(tool_path)
        assert ok is True

        # Overwrite with top-level runtime exception
        tool_path.write_text("""
MANIFEST = {"name": "runtime_err_tool", "parameters": {"type": "OBJECT", "properties": {}}}
# Fatal runtime crash during module import
x = 1 / 0
def run(parameters=None, **kwargs):
    return "v2_crashed"
""", encoding="utf-8")

        ok_bad, res_bad = registry.hot_reload_file(tool_path)
        assert ok_bad is False
        assert "division by zero" in res_bad.get("error", "")

        # Verify previous working version retained
        exec_res = registry.execute("runtime_err_tool")
        assert exec_res["ok"] is True
        assert exec_res["result"] == "v1_operational"

    def test_missing_or_invalid_manifest_triggers_rollback(self, clean_registry_and_temp):
        """
        Adversarial test: File with missing or invalid MANIFEST (e.g. non-dict).
        Must fail validation and rollback.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_path = temp_dir / "manifest_test_tool.py"
        tool_path.write_text("""
MANIFEST = {"name": "manifest_test_tool", "parameters": {"type": "OBJECT", "properties": {}}}
def run(parameters=None, **kwargs):
    return "valid_manifest"
""", encoding="utf-8")

        ok, _ = registry.hot_reload_file(tool_path)
        assert ok is True

        # Test Case A: MANIFEST is a string, not a dict
        tool_path.write_text("""
MANIFEST = "invalid_manifest_string"
def run(parameters=None, **kwargs):
    return "bad"
""", encoding="utf-8")
        ok_a, res_a = registry.hot_reload_file(tool_path)
        assert ok_a is False
        assert "missing dict MANIFEST" in res_a.get("error", "")

        # Verify rollback
        assert registry.execute("manifest_test_tool")["result"] == "valid_manifest"

        # Test Case B: Missing MANIFEST completely
        tool_path.write_text("""
def run(parameters=None, **kwargs):
    return "no_manifest"
""", encoding="utf-8")
        ok_b, res_b = registry.hot_reload_file(tool_path)
        assert ok_b is False
        assert "missing dict MANIFEST" in res_b.get("error", "")
        assert registry.execute("manifest_test_tool")["result"] == "valid_manifest"

    def test_missing_or_non_callable_run_triggers_rollback(self, clean_registry_and_temp):
        """
        Adversarial test: File with missing or non-callable run attribute.
        Must fail validation and rollback.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_path = temp_dir / "run_test_tool.py"
        tool_path.write_text("""
MANIFEST = {"name": "run_test_tool", "parameters": {"type": "OBJECT", "properties": {}}}
def run(parameters=None, **kwargs):
    return "callable_ok"
""", encoding="utf-8")

        ok, _ = registry.hot_reload_file(tool_path)
        assert ok is True

        # run is a string
        tool_path.write_text("""
MANIFEST = {"name": "run_test_tool", "parameters": {"type": "OBJECT", "properties": {}}}
run = "not_a_function"
""", encoding="utf-8")

        ok_bad, res_bad = registry.hot_reload_file(tool_path)
        assert ok_bad is False
        assert "missing callable run()" in res_bad.get("error", "")
        assert registry.execute("run_test_tool")["result"] == "callable_ok"

    def test_security_check_ordering_vulnerability_in_hot_reload_file(self, clean_registry_and_temp):
        """
        CRITICAL ADVERSARIAL FINDING:
        In core/active_tool_registry.py lines 209-245:
        `spec.loader.exec_module(module)` is invoked in Step 4 BEFORE
        the raw code is checked for prohibited tokens in Step 5 (line 244).
        This test empirically verifies whether top-level code in a file containing
        a prohibited token is executed prior to being rejected!
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        marker_file = temp_dir / "exploit_marker.txt"
        if marker_file.exists():
            marker_file.unlink()

        # File containing prohibited identity token AND top-level side effect
        marker_path_str = str(marker_file).replace("\\", "/")
        hostile_file = temp_dir / "banned_identity_tool.py"
        banned_term = "".join(["ad", "eel", "qur", "eshi", "99"])
        hostile_code = f"""
from pathlib import Path

# Prohibited identity token present:
# Owner identity test: {banned_term}

# Top-level side effect executed at import time:
Path("{marker_path_str}").write_text("SIDE_EFFECT_EXECUTED", encoding="utf-8")

MANIFEST = {{"name": "banned_identity_tool", "parameters": {{"type": "OBJECT", "properties": {{}}}}}}
def run(parameters=None, **kwargs):
    return "hacked"
"""
        hostile_file.write_text(hostile_code, encoding="utf-8")

        # Call hot_reload_file
        ok, res = registry.hot_reload_file(hostile_file)

        # hot_reload_file rejects it due to line 244:
        assert ok is False
        assert "Security violation" in res.get("error", "")

        # EMPIRICAL OBSERVATION: Did the top-level side effect execute before rejection?
        side_effect_occurred = marker_file.exists()
        logger.warning(
            "[Adversarial Observation] Did top-level code execute before prohibited token check? %s",
            side_effect_occurred
        )
        # Note: If side_effect_occurred is True, this confirms an ordering flaw in hot_reload_file!
        # We record this finding without crashing the test:
        assert side_effect_occurred is True, "Empirical proof: exec_module runs before security scan!"

    def test_system_exit_in_hot_reload_file_bubbles_past_exception_handler(self, clean_registry_and_temp):
        """
        ADVERSARIAL FINDING:
        In core/active_tool_registry.py line 210:
        `except Exception as e:` does NOT catch BaseException subclasses like SystemExit!
        If a module contains `raise SystemExit(42)`, hot_reload_file allows it to bubble up.
        This test executes in a controlled subprocess to empirically prove the behavior.
        """
        temp_dir = clean_registry_and_temp["temp_dir"]

        probe_script = temp_dir / "probe_system_exit.py"
        bad_tool = temp_dir / "exit_tool.py"

        bad_tool.write_text("""
import sys
raise SystemExit(42)
""", encoding="utf-8")

        probe_code = f"""
import sys
from pathlib import Path
sys.path.insert(0, r"{Path('.').resolve()}")
from core.active_tool_registry import get_active_tool_registry

registry = get_active_tool_registry()
try:
    ok, res = registry.hot_reload_file(r"{bad_tool.resolve()}")
    print(f"SURVIVED: ok={{ok}}, res={{res}}")
except SystemExit as se:
    print(f"CAUGHT_SYSTEM_EXIT: code={{se.code}}")
    sys.exit(se.code)
"""
        probe_script.write_text(probe_code, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(probe_script)],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        logger.info("[Adversarial Observation] SystemExit probe output: exit_code=%d, stdout=%s", res.returncode, res.stdout.strip())
        # The subprocess exited with code 42 because hot_reload_file did NOT catch SystemExit!
        assert res.returncode == 42
        assert "CAUGHT_SYSTEM_EXIT: code=42" in res.stdout


# =============================================================================
# Dimension 3: Rapid Registration/Unregistration Cycles & Memory Leaks
# =============================================================================

class TestMemoryLeakAndRapidLifecycleCycles:
    """Stress tests repeated rapid registration/unregistration to verify leak resistance."""

    def test_rapid_in_memory_registration_unregistration_leak_check(self, clean_registry_and_temp):
        """
        Rapidly registers and unregisters 2,000 distinct tools in memory.
        Verifies that registry internal data structures empty out completely
        and memory usage does not experience unbounded growth.
        """
        registry = clean_registry_and_temp["registry"]

        gc.collect()
        initial_tools_count = len(registry._tools)
        assert initial_tools_count == 0

        # Perform 2,000 register -> execute -> unregister cycles
        for i in range(2000):
            tool_name = f"churn_tool_{i}"
            manifest = {
                "name": tool_name,
                "version": "1.0.0",
                "parameters": {"type": "OBJECT", "properties": {"v": {"type": "INTEGER"}}},
            }
            # Register
            registry.register(tool_name, manifest, lambda p, **kw: p.get("v", 0) + 1)
            # Execute
            res = registry.execute(tool_name, {"v": i})
            assert res["ok"] is True
            # Unregister
            unreg_ok = registry.unregister(tool_name)
            assert unreg_ok is True

        gc.collect()

        # Verify internal registry structures are completely empty
        assert len(registry._tools) == 0
        assert len(registry._manifests) == 0
        assert len(registry._metadata) == 0
        assert len(registry.list_tools()) == 0
        assert registry._global_version == 4000  # 2000 registers + 2000 unregisters

    def test_sys_modules_leak_when_hot_reloaded_tools_are_unregistered(self, clean_registry_and_temp):
        """
        EMPIRICAL CHALLENGE:
        When a tool is registered via hot_reload_file(), it injects into sys.modules.
        When unregister(tool_name) is called, DOES IT REMOVE THE MODULE FROM sys.modules?
        Or does sys.modules keep accumulating module references?
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        tool_names = [f"leak_probe_tool_{i}" for i in range(20)]
        created_files = []

        for name in tool_names:
            file_p = temp_dir / f"{name}.py"
            file_p.write_text(f"""
MANIFEST = {{"name": "{name}", "parameters": {{"type": "OBJECT", "properties": {{}}}}}}
def run(parameters=None, **kwargs):
    return "{name}_ok"
""", encoding="utf-8")
            created_files.append(file_p)
            ok, _ = registry.hot_reload_file(file_p)
            assert ok is True

        # All 20 tools are loaded and in sys.modules
        for name in tool_names:
            mod_key = f"tools.{name}"
            assert mod_key in sys.modules, f"Expected {mod_key} in sys.modules"

        # Now unregister all 20 tools from the registry
        for name in tool_names:
            unreg_ok = registry.unregister(name)
            assert unreg_ok is True

        # Registry structures are empty:
        assert len(registry._tools) == 0

        # EMPIRICAL OBSERVATION: Check sys.modules
        leaked_in_sys_modules = [f"tools.{name}" for name in tool_names if f"tools.{name}" in sys.modules]
        logger.warning(
            "[Adversarial Observation] Modules retained in sys.modules after unregister: %d / %d",
            len(leaked_in_sys_modules), len(tool_names)
        )
        # Because unregister() does not clean up sys.modules, all 20 modules remain in sys.modules:
        assert len(leaked_in_sys_modules) == 20, (
            "Empirical finding: unregister() does not evict modules from sys.modules!"
        )

        # Cleanup sys.modules for test hygiene
        for k in leaked_in_sys_modules:
            sys.modules.pop(k, None)

    def test_stale_bytecode_caching_vulnerability_on_rapid_reload(self, clean_registry_and_temp):
        """
        EMPIRICAL CHALLENGE: Code Freshness Under Rapid Successive Hot-Reloads.
        Tests whether rapid reloads within the same second/filesystem tick properly
        update the running function or serve stale cached bytecode from __pycache__.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        target = temp_dir / "rapid_tight_tool.py"
        stale_occurrences = []

        # Run 10 rapid rewrites in tight loop with constant file length
        for v in range(1, 11):
            # Equal length payload to stress .pyc header size equality
            payload = f"val_{v:03d}"
            target.write_text(f"""
MANIFEST = {{"name": "rapid_tight_tool", "parameters": {{"type": "OBJECT", "properties": {{}}}}}}
def run(parameters=None, **kwargs):
    return "{payload}"
""", encoding="utf-8")
            ok, res = registry.hot_reload_file(target)
            assert ok is True
            actual = registry.execute("rapid_tight_tool")["result"]
            if actual != payload:
                stale_occurrences.append({"v": v, "expected": payload, "actual": actual})

        logger.warning(
            "[Adversarial Observation] Stale bytecode occurrences in 10 tight reloads: %d / 10",
            len(stale_occurrences)
        )
        # Record whether stale caching occurred
        # If stale_occurrences is non-empty, we confirm the stale reload bug!
        assert len(stale_occurrences) > 0, (
            f"Expected stale bytecode occurrences due to __pycache__ mtime caching, but got 0 stale occurrences!"
        )


    def test_repeated_hot_reload_metadata_and_telemetry_accumulation(self, clean_registry_and_temp):
        """
        Tests repeated reload of a tool file across 50 versions where each version
        has a unique size to bypass .pyc collision.
        Verifies that version increments properly and execution statistics accumulate.
        """
        registry = clean_registry_and_temp["registry"]
        temp_dir = clean_registry_and_temp["temp_dir"]

        target = temp_dir / "reload_telemetry_tool.py"
        for v in range(1, 51):
            padding = " " * v  # ensure varying file size
            target.write_text(f"""
MANIFEST = {{"name": "reload_telemetry_tool", "parameters": {{"type": "OBJECT", "properties": {{}}}}}}
def run(parameters=None, **kwargs):
    #{padding}
    return "v_{v}"
""", encoding="utf-8")
            ok, res = registry.hot_reload_file(target)
            assert ok is True
            assert res["version"] == v

            if v % 10 == 0:
                exec_res = registry.execute("reload_telemetry_tool")
                assert exec_res["ok"] is True

        meta = next(m for m in registry.list_tools() if m["name"] == "reload_telemetry_tool")
        assert meta["version"] == 50
        assert meta["execution_count"] == 5



# =============================================================================
# Dimension 4: Observer Deadlock & Subscriber Contention
# =============================================================================

class TestObserverDeadlockAndContention:
    """Stress tests observer notifications, re-entrancy, and multithreaded Deadlock safety."""

    def test_observer_callback_reentrancy_under_rlock(self, clean_registry_and_temp):
        """
        Tests whether an observer callback can re-entrantly query registry methods
        (has_tool, get_manifest, list_tools, execute) when notified during registration/unregistration.
        """
        registry = clean_registry_and_temp["registry"]
        events_captured = []

        def reentrant_observer(event_type: str, tool_name: str, manifest: Dict[str, Any]):
            # Re-entrant calls into the registry on the same thread:
            has = registry.has_tool(tool_name)
            manifests = registry.get_all_manifests()
            events_captured.append({
                "event": event_type,
                "tool": tool_name,
                "has_tool": has,
                "all_count": len(manifests),
            })

        registry.subscribe(reentrant_observer)

        # Trigger registration
        registry.register("obs_tool_1", {"name": "obs_tool_1"}, lambda p, **kw: "ok")
        # Trigger unregistration
        registry.unregister("obs_tool_1")

        assert len(events_captured) == 2
        assert events_captured[0]["event"] == "TOOL_REGISTERED"
        assert events_captured[0]["has_tool"] is True
        assert events_captured[1]["event"] == "TOOL_UNREGISTERED"
        assert events_captured[1]["has_tool"] is False

    def test_observer_cross_thread_lock_inversion_deadlock_risk(self, clean_registry_and_temp):
        """
        ADVERSARIAL CONCURRENCY PROBE:
        In unregister(): `self._notify()` is called INSIDE `with self._lock:`.
        If an observer callback attempts to acquire an external lock that another thread
        holds while waiting on registry._lock, a classic AB-BA deadlock occurs!
        This test checks whether cross-thread synchronization inside unregister notification
        is vulnerable to lock inversion deadlock.
        """
        registry = clean_registry_and_temp["registry"]

        external_lock = threading.Lock()
        deadlock_detected = threading.Event()
        barrier = threading.Barrier(2)

        def subscriber_callback(event_type: str, tool_name: str, manifest: dict):
            if event_type == "TOOL_UNREGISTERED":
                # Observer tries to acquire external_lock
                # If Thread 2 holds external_lock and calls registry.get_tool(),
                # Thread 1 holds registry._lock and blocks on external_lock!
                acquired = external_lock.acquire(timeout=0.5)
                if not acquired:
                    deadlock_detected.set()
                else:
                    external_lock.release()

        registry.subscribe(subscriber_callback)
        registry.register("deadlock_victim", {"name": "deadlock_victim"}, lambda p: "ok")

        def thread_2_worker():
            # Thread 2 holds external_lock, then calls registry method
            with external_lock:
                barrier.wait()
                # Give thread 1 time to enter unregister() and acquire registry._lock
                time.sleep(0.05)
                # Thread 2 now tries to acquire registry._lock:
                registry.has_tool("deadlock_victim")

        t2 = threading.Thread(target=thread_2_worker, daemon=True)
        t2.start()

        barrier.wait()
        # Thread 1 calls unregister, which holds registry._lock and calls subscriber_callback
        registry.unregister("deadlock_victim")

        t2.join(timeout=1.0)

        logger.warning(
            "[Adversarial Observation] Lock-inversion deadlock risk triggered in unregister observer: %s",
            deadlock_detected.is_set()
        )
        assert deadlock_detected.is_set() is True, (
            "Empirical finding: unregister() notifies subscribers while holding self._lock, causing deadlock risk!"
        )


# =============================================================================
# Dimension 5: Edge Cases in Hermes Schema Export & Sandboxing
# =============================================================================

class TestHermesSchemaExportAndSandboxStress:
    """Stress tests edge cases in Hermes Function schema export and subprocess sandbox."""

    def test_export_hermes_schema_with_null_and_malformed_parameters(self, clean_registry_and_temp):
        """
        Adversarial test: Tools registered with empty, missing, or malformed parameters.
        Must not crash export_hermes_schema.
        """
        registry = clean_registry_and_temp["registry"]

        # Case A: parameters is None
        registry.register("null_params_tool", {"name": "null_params_tool", "parameters": {}}, lambda p: "ok")
        schema_a = registry.export_hermes_schema("null_params_tool")
        assert schema_a is not None
        assert schema_a["function"]["name"] == "null_params_tool"
        assert schema_a["function"]["parameters"]["type"] == "object"

        # Case B: properties with various Gemini types
        complex_manifest = {
            "name": "complex_types_tool",
            "description": "Tool with exotic types",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "count": {"type": "INTEGER", "description": "Count"},
                    "ratio": {"type": "NUMBER"},
                    "tags": {"type": "ARRAY"},
                    "active": {"type": "BOOLEAN"},
                    "metadata": {"type": "OBJECT"},
                    "status": {"type": "STRING", "enum": ["A", "B"], "default": "A"},
                },
                "required": ["count"],
            },
        }
        registry.register("complex_types_tool", complex_manifest, lambda p: "ok")
        schema_b = registry.export_hermes_schema("complex_types_tool")
        assert schema_b is not None
        props = schema_b["function"]["parameters"]["properties"]
        assert props["count"]["type"] == "integer"
        assert props["ratio"]["type"] == "number"
        assert props["tags"]["type"] == "array"
        assert props["active"]["type"] == "boolean"
        assert props["metadata"]["type"] == "object"
        assert props["status"]["type"] == "string"
        assert props["status"]["enum"] == ["A", "B"]
        assert schema_b["function"]["parameters"]["required"] == ["count"]

    def test_sandbox_runner_process_tree_termination(self, clean_registry_and_temp):
        """
        Adversarial test: Subprocess that spawns multiple rogue child processes
        and enters infinite sleep. SubprocessSandboxRunner must terminate the entire tree.
        """
        runner = SubprocessSandboxRunner()
        temp_dir = clean_registry_and_temp["temp_dir"]

        rogue_script = temp_dir / "rogue_parent.py"
        rogue_script.write_text("""
import subprocess
import sys
import time

# Spawn child processes
p1 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(100)"])
p2 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(100)"])
# Sleep to exceed timeout
time.sleep(100)
""", encoding="utf-8")

        passed, res = runner.execute_in_sandbox(
            command=[sys.executable, str(rogue_script.resolve())],
            cwd=Path(".").resolve(),
            timeout=1.5,
        )

        assert passed is False
        assert res["timeout_triggered"] is True
        assert res["exit_code"] == -1

    def test_sync_from_directory_fatal_crash_on_base_exception(self, clean_registry_and_temp):
        """
        EMPIRICAL FINDING:
        sync_from_directory iterates through python files and calls hot_reload_file().
        Because hot_reload_file() does not catch BaseException, if a single corrupted file
        raises SystemExit, the entire directory sync crashes and terminates the process,
        preventing any subsequent valid skills from being loaded.
        """
        temp_dir = clean_registry_and_temp["temp_dir"]
        sync_dir = temp_dir / "sync_skills"
        sync_dir.mkdir(parents=True, exist_ok=True)

        (sync_dir / "01_valid_tool.py").write_text("""
MANIFEST = {"name": "valid_01", "parameters": {"type": "OBJECT", "properties": {}}}
def run(p=None): return "01_ok"
""", encoding="utf-8")

        (sync_dir / "02_fatal_tool.py").write_text("""
import sys
raise SystemExit(99)
""", encoding="utf-8")

        (sync_dir / "03_valid_tool.py").write_text("""
MANIFEST = {"name": "valid_03", "parameters": {"type": "OBJECT", "properties": {}}}
def run(p=None): return "03_ok"
""", encoding="utf-8")

        probe_script = temp_dir / "probe_sync_fatal.py"
        probe_code = f"""
import sys
from pathlib import Path
sys.path.insert(0, r"{Path('.').resolve()}")
from core.active_tool_registry import get_active_tool_registry

reg = get_active_tool_registry()
try:
    count = reg.sync_from_directory(r"{sync_dir.resolve()}")
    print(f"SYNC_COUNT: {{count}}")
except SystemExit as se:
    print(f"SYNC_CRASHED_WITH_SYSTEM_EXIT: code={{se.code}}")
    sys.exit(se.code)
"""
        probe_script.write_text(probe_code, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(probe_script.resolve())],
            capture_output=True,
            text=True,
            timeout=5.0,
        )

        logger.warning(
            "[Adversarial Observation] sync_from_directory crash behavior: exit_code=%d, stdout=%s",
            res.returncode, res.stdout.strip()
        )
        assert res.returncode == 99
        assert "SYNC_CRASHED_WITH_SYSTEM_EXIT: code=99" in res.stdout

    def test_ast_security_catches_obfuscated_banned_tokens_and_dunders(self, clean_registry_and_temp):
        """
        Tests whether AssimilatorASTSecurityValidator catches obfuscated reflection
        and prohibited identifiers.
        """
        validator = AssimilatorASTSecurityValidator()

        # Obfuscated dunder reflection
        code_dunder = "getattr(obj, '__globals__')"
        safe, violations = validator.validate(code_dunder)
        assert safe is False
        assert any("dunder reflection" in v for v in violations)

        # Prohibited token in identifier
        code_token = "".join(["ad", "eel", "qur", "eshi", "99"]) + " = 123"
        safe2, violations2 = validator.validate(code_token)
        assert safe2 is False
        assert any("Prohibited identity token" in v for v in violations2)


