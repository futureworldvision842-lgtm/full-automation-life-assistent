"""
Empirical Adversarial Stress Test Suite - Challenger 2
Milestone M1: Unified Process Supervisor & Multi-Service Lifecycle (Requirement R1)

Empirical Verification of:
1. Launcher script portability and dynamic path evaluation across Batch and PowerShell.
2. Process lifecycle boundary containment: guarantee no termination of unauthorized OS processes outside KNOWN_PROJECT_ROOTS.
3. Platform runtime service readiness probes: socket resilience, timeout handling, payload corruption tolerance.
4. Supervisor build services, watchdog checks, and hardware vitals telemetry.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import dashboard
import platform_runtime
from bootstrap import lifecycle, supervisor


class TestLauncherPortabilityStress(unittest.TestCase):
    """Empirically stress-test launcher script portability and path syntax."""

    def setUp(self):
        self.root = BASE_DIR
        self.launch_master_bat = self.root / "LAUNCH_JARVIS_MASTER.bat"
        self.start_full_bat = self.root / "START_FULL_JARVIS_ECOSYSTEM.bat"
        self.start_full_ps1 = self.root / "START_FULL_JARVIS_ECOSYSTEM.ps1"
        self.stop_bat = self.root / "STOP_JARVIS.bat"
        self.run_bat = self.root / "run.bat"
        self.start_boot_bat = self.root / "start_jarvis_boot.bat"
        self.start_all_ps1 = self.root / "start_all.ps1"

    def test_all_bat_files_no_hardcoded_legacy_paths(self):
        """Scan all batch files to ensure zero hardcoded E:\\jarvis or legacy paths."""
        bat_files = list(self.root.glob("*.bat"))
        self.assertGreater(len(bat_files), 0, "Batch files must exist in repository root")
        
        legacy_tokens = ["E:\\jarvis", "e:\\jarvis", "jarvis_wweb.js"]
        for bat in bat_files:
            if bat.name.endswith("_old.bat"):
                continue  # Skip archived files explicitly named _old
            content = bat.read_text(encoding="utf-8", errors="ignore")
            for token in legacy_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"File {bat.name} contains legacy token '{token}'"
                )

    def test_all_ps1_files_no_hardcoded_legacy_paths(self):
        """Scan all PS1 scripts for legacy tokens."""
        ps1_files = list(self.root.glob("*.ps1"))
        self.assertGreater(len(ps1_files), 0, "PowerShell files must exist in repository root")
        
        legacy_tokens = ["E:\\jarvis", "e:\\jarvis", "jarvis_wweb.js"]
        for ps1 in ps1_files:
            content = ps1.read_text(encoding="utf-8", errors="ignore")
            for token in legacy_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"File {ps1.name} contains legacy token '{token}'"
                )

    def test_bat_quoting_for_paths_with_spaces(self):
        """Verify that batch scripts quote %~dp0 expansions to support directories with spaces."""
        for bat in [self.launch_master_bat, self.start_full_bat, self.stop_bat, self.run_bat]:
            if not bat.exists():
                continue
            content = bat.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                clean = line.strip()
                if clean.startswith("cd /d") and "%~dp0" in clean:
                    self.assertIn(
                        '"%~dp0"',
                        clean,
                        f"Unquoted '%~dp0' found in {bat.name} at line {idx}: '{line}'"
                    )

    def test_powershell_syntax_validation(self):
        """Empirically validate PowerShell scripts using PowerShell AST parser."""
        ps_scripts = [self.start_full_ps1, self.start_all_ps1]
        for script in ps_scripts:
            if not script.exists():
                continue
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"$errors = $null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$null, [ref]$errors); "
                f"if ($errors.Count -gt 0) {{ foreach ($e in $errors) {{ Write-Error $e.Message }}; exit 1 }} else {{ exit 0 }}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertEqual(
                res.returncode,
                0,
                f"PowerShell syntax validation failed for {script.name}:\n{res.stderr}\n{res.stdout}"
            )

    def test_start_full_ps1_dry_run_path_resolution(self):
        """Simulate execution of START_FULL_JARVIS_ECOSYSTEM.ps1 variable resolution."""
        ps_command = (
            f"$ROOT = '{self.root}'; "
            f"$PY = if (Test-Path \"$ROOT\\.venv\\Scripts\\python.exe\") {{ \"$ROOT\\.venv\\Scripts\\python.exe\" }} "
            f"elseif (Get-Command 'py' -ErrorAction SilentlyContinue) {{ 'py' }} else {{ 'python' }}; "
            f"Write-Output \"RESOLVED_PY:$PY\"; "
            f"Write-Output \"RESOLVED_ROOT:$ROOT\"; "
        )
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_command]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0)
        self.assertIn("RESOLVED_ROOT:", res.stdout)
        self.assertIn("RESOLVED_PY:", res.stdout)


class TestLifecycleContainmentStress(unittest.TestCase):
    """Empirically stress-test boundary containment of lifecycle process termination."""

    def test_under_boundary_strict_prefix_containment(self):
        """
        Adversarial test for _under(path, roots).
        Prefix matching MUST NOT match sibling directories that share a name prefix.
        e.g. 'P:\\Vision Point Work\\jarvis' should NOT contain 'P:\\Vision Point Work\\jarvis_fake'.
        """
        root_str = str(lifecycle.ROOT)
        
        # Valid descendants
        self.assertTrue(lifecycle._under(root_str))
        self.assertTrue(lifecycle._under(os.path.join(root_str, "bootstrap")))
        self.assertTrue(lifecycle._under(os.path.join(root_str, "actions", "submodule")))
        self.assertTrue(lifecycle._under(Path(root_str) / "skills" / "my_skill"))
        
        # Adversarial prefix attacks (sibling paths with prefix overlap)
        adversarial_paths = [
            f"{root_str}_fake",
            f"{root_str}-backup",
            f"{root_str}.old",
            f"{root_str}_malicious\\sub",
            f"{root_str}2",
            f"{root_str}_workspace",
        ]
        for adv_path in adversarial_paths:
            self.assertFalse(
                lifecycle._under(adv_path),
                f"_under() improperly matched adversarial prefix sibling: {adv_path}"
            )

    def test_under_case_insensitivity_and_slash_normalization(self):
        """Test Windows case-insensitivity and forward/backward slash normalization in _under()."""
        root_str = str(lifecycle.ROOT)
        
        # Inverted case
        upper_root = root_str.upper()
        lower_root = root_str.lower()
        self.assertTrue(lifecycle._under(upper_root))
        self.assertTrue(lifecycle._under(lower_root))
        
        # Forward slashes
        forward_slash = root_str.replace("\\", "/") + "/bootstrap/lifecycle.py"
        self.assertTrue(lifecycle._under(forward_slash))

    def test_under_empty_and_none_inputs(self):
        """Test _under() with null or empty values."""
        self.assertFalse(lifecycle._under(None))
        self.assertFalse(lifecycle._under(""))

    def test_process_is_managed_comprehensive_matrix(self):
        """
        Run a high-density classification matrix testing authorized vs unauthorized processes.
        """
        root = str(lifecycle.ROOT)
        unauthorized_dirs = [
            r"C:\Windows\System32",
            r"C:\Program Files\Python314",
            r"C:\Users\user\AppData\Local",
            r"D:\TradingBots\OtherBot",
            r"P:\Vision Point Work\UnrelatedProject",
            r"C:\Windows\explorer.exe",
        ]
        
        # 1. Hostile / Non-managed executables in root MUST NOT be managed
        unmanaged_binaries = [
            ("notepad.exe", ["notepad.exe", "file.txt"]),
            ("explorer.exe", ["explorer.exe"]),
            ("svchost.exe", ["svchost.exe", "-k", "netsvcs"]),
            ("chrome.exe", ["chrome.exe", "--remote-debugging-port=9222"]),
            ("git.exe", ["git", "status"]),
            ("code.exe", ["code", "."]),
            ("powershell.exe", ["powershell", "-Command", "Get-Process"]),
        ]
        for name, cmd in unmanaged_binaries:
            self.assertFalse(
                lifecycle.process_is_managed(name, cmd, root),
                f"Unauthorized executable '{name}' in ROOT was incorrectly classified as managed!"
            )
            for bad_dir in unauthorized_dirs:
                self.assertFalse(
                    lifecycle.process_is_managed(name, cmd, bad_dir),
                    f"Unauthorized executable '{name}' in '{bad_dir}' was incorrectly classified as managed!"
                )

        # 2. Managed executables in UNAUTHORIZED directories MUST NOT be managed
        managed_runtimes = ["python.exe", "pythonw.exe", "node.exe", "ollama.exe", "bun.exe", "cmd.exe"]
        for runtime in managed_runtimes:
            for bad_dir in unauthorized_dirs:
                # Even if cmdline mentions a managed marker (e.g. main.py)
                self.assertFalse(
                    lifecycle.process_is_managed(runtime, [runtime, "main.py"], bad_dir),
                    f"Process '{runtime}' in unauthorized directory '{bad_dir}' was incorrectly managed!"
                )
                self.assertFalse(
                    lifecycle.process_is_managed(runtime, [runtime, "dashboard.py"], bad_dir),
                    f"Process '{runtime}' in unauthorized directory '{bad_dir}' was incorrectly managed!"
                )
                self.assertFalse(
                    lifecycle.process_is_managed(runtime, [runtime, "server.py"], bad_dir),
                    f"Process '{runtime}' in unauthorized directory '{bad_dir}' was incorrectly managed!"
                )

        # 3. Python running an UNMANAGED script inside root MUST NOT be managed
        unmanaged_scripts = [
            "random_work.py",
            "scratch_script.py",
            "test_something.py",
            "setup.py",
            "-m pip install pytest",
        ]
        for script in unmanaged_scripts:
            self.assertFalse(
                lifecycle.process_is_managed("python.exe", ["python.exe", script], root),
                f"Unmanaged script '{script}' inside root was incorrectly classified as managed!"
            )

        # 4. Legit managed services inside root MUST be managed
        valid_managed_services = [
            ("python.exe", ["python.exe", "main.py"], root),
            ("python.exe", ["python.exe", "dashboard.py"], root),
            ("python.exe", ["python.exe", "mobile_control.py"], root),
            ("python.exe", ["python.exe", "server.py"], os.path.join(root, "web")),
            ("python.exe", ["python.exe", "heartbeat_reporter.py"], os.path.join(root, "web")),
            ("python.exe", ["python.exe", "mission_daemon.py"], os.path.join(root, "agent")),
            ("python.exe", ["python.exe", "bootstrap/supervisor.py"], root),
            ("python.exe", ["python.exe", "src/autonomous_live_daemon.py"], str(platform_runtime.MQ3_ROOT)),
            ("python.exe", ["python.exe", "run.py", "--demo"], str(platform_runtime.MQ3_ROOT)),
            ("node.exe", ["node.exe", "jarvis_baileys.js"], os.path.join(root, "wa")),
            ("ollama.exe", ["ollama", "serve"], root),
        ]
        for name, cmd, cwd in valid_managed_services:
            self.assertTrue(
                lifecycle.process_is_managed(name, cmd, cwd),
                f"Legitimate service '{name} {cmd}' in '{cwd}' failed to be classified as managed!"
            )

    def test_stop_managed_processes_does_not_kill_caller_or_parent(self):
        """Verify that stop_managed_processes dry-run excludes caller and parent PIDs."""
        my_pid = os.getpid()
        parent_pid = os.getppid()
        
        result = lifecycle.stop_managed_processes(reason="challenger-stress-test", dry_run=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        
        matched_pids = {p.get("pid") for p in result["processes"]}
        self.assertNotIn(my_pid, matched_pids, "stop_managed_processes must NEVER target caller process!")
        self.assertNotIn(parent_pid, matched_pids, "stop_managed_processes must NEVER target parent process!")

    def test_managed_processes_psutil_resilience(self):
        """Stress-test managed_processes with genuine psutil exceptions."""
        mock_proc_access_denied = MagicMock()
        mock_proc_access_denied.pid = 9991
        mock_proc_access_denied.cwd.side_effect = psutil.AccessDenied(pid=9991)

        mock_proc_no_such_proc = MagicMock()
        mock_proc_no_such_proc.pid = 9992
        mock_proc_no_such_proc.cwd.side_effect = psutil.NoSuchProcess(pid=9992)

        mock_proc_valid = MagicMock()
        mock_proc_valid.pid = 9993
        mock_proc_valid.info = {"name": "python.exe", "cmdline": ["python", "dashboard.py"]}
        mock_proc_valid.cwd.return_value = str(lifecycle.ROOT)

        with patch("bootstrap.lifecycle.psutil.process_iter", return_value=[
            mock_proc_access_denied,
            mock_proc_no_such_proc,
            mock_proc_valid,
        ]):
            found = lifecycle.managed_processes(exclude_pids=())
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].pid, 9993)

    def test_audit_logging_persists_valid_jsonl(self):
        """Verify that lifecycle stop operations write valid JSONL entries."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_audit_file = Path(tmp_dir) / "test_lifecycle.jsonl"
            with patch.object(lifecycle, "AUDIT_LOG", test_audit_file):
                lifecycle.stop_managed_processes(reason="test-audit-log-verification", dry_run=True)
                self.assertTrue(test_audit_file.exists())
                lines = test_audit_file.read_text(encoding="utf-8").strip().splitlines()
                self.assertGreaterEqual(len(lines), 1)
                last_entry = json.loads(lines[-1])
                self.assertEqual(last_entry["reason"], "test-audit-log-verification")
                self.assertEqual(last_entry["event"], "stop-request")
                self.assertTrue(last_entry["dryRun"])
                self.assertIn("at", last_entry)


class TestPlatformRuntimeProbesStress(unittest.TestCase):
    """Empirically stress-test platform_runtime service probes and socket safety."""

    def test_probe_service_connection_refused_no_uncaught_exception(self):
        """
        Probe a closed local TCP port.
        Must return a valid ServiceProbe with available=False, status='offline', without raising.
        """
        closed_port = 58971
        probe = platform_runtime.probe_service("test_offline_daemon", f"http://127.0.0.1:{closed_port}", timeout=0.3)
        
        self.assertIsInstance(probe, platform_runtime.ServiceProbe)
        self.assertFalse(probe.available)
        self.assertEqual(probe.status, "offline")
        self.assertIsNone(probe.http_status)
        self.assertIsNotNone(probe.error)
        self.assertIn("Connection", probe.error)
        self.assertGreaterEqual(probe.latency_ms, 0)
        self.assertIsInstance(probe.checked_at, str)

    def test_probe_service_malformed_url_safety(self):
        """Probe malformed or invalid URLs; must handle gracefully without crash."""
        malformed_urls = [
            "http://invalid.domain.that.does.not.exist.example.test:9999",
            "http://999.999.999.999:80",
            "not-a-url",
            "http://localhost:99999",  # invalid port
        ]
        for url in malformed_urls:
            probe = platform_runtime.probe_service("malformed_test", url, timeout=0.2)
            self.assertIsInstance(probe, platform_runtime.ServiceProbe)
            self.assertFalse(probe.available)
            self.assertEqual(probe.status, "offline")
            self.assertIsNotNone(probe.error)

    def test_probe_service_http_status_codes(self):
        """Test probe_service classification across various HTTP status codes."""
        status_expectations = [
            (200, True, "online", None),
            (201, True, "online", None),
            (204, True, "online", None),
            (301, False, "degraded", "HTTP 301"),
            (400, False, "degraded", "HTTP 400"),
            (401, False, "degraded", "HTTP 401"),
            (403, False, "degraded", "HTTP 403"),
            (404, False, "degraded", "HTTP 404"),
            (500, False, "degraded", "HTTP 500"),
            (502, False, "degraded", "HTTP 502"),
            (503, False, "degraded", "HTTP 503"),
        ]
        for code, expected_avail, expected_status, expected_error in status_expectations:
            mock_resp = MagicMock()
            mock_resp.status_code = code
            mock_resp.json.return_value = {}
            with patch("requests.get", return_value=mock_resp):
                probe = platform_runtime.probe_service("mock_svc", "http://127.0.0.1:8000")
                self.assertEqual(probe.available, expected_avail, f"Failed for HTTP {code}")
                self.assertEqual(probe.status, expected_status, f"Failed status for HTTP {code}")
                self.assertEqual(probe.error, expected_error, f"Failed error for HTTP {code}")

    def test_whatsapp_probe_corrupted_json_resilience(self):
        """Test WhatsApp probe when HTTP 200 is returned but response body is corrupted or non-JSON."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON token")
        
        with patch("requests.get", return_value=mock_resp):
            probe = platform_runtime.probe_service("whatsapp", "http://127.0.0.1:3200/status")
            self.assertTrue(probe.available)
            self.assertEqual(probe.status, "online")
            self.assertIsNotNone(probe.details)
            self.assertTrue(probe.details["bridge_online"])
            self.assertFalse(probe.details["whatsapp_connected"])
            self.assertIsNone(probe.details["pairing_required"])

    def test_runtime_snapshot_degraded_when_any_service_down(self):
        """Test that runtime_snapshot status is degraded if even 1 service is offline."""
        def mock_probe_mixed(name, url, timeout=1.5):
            is_up = (name == "mq3")
            return platform_runtime.ServiceProbe(
                name=name,
                url=url,
                available=is_up,
                status="online" if is_up else "offline",
                checked_at=platform_runtime.utc_now(),
                http_status=200 if is_up else None,
                error=None if is_up else "Connection refused"
            )

        with patch("platform_runtime.probe_service", side_effect=mock_probe_mixed):
            snapshot = platform_runtime.runtime_snapshot()
            self.assertEqual(snapshot["status"], "degraded")
            self.assertEqual(len(snapshot["services"]), 5)

    def test_runtime_snapshot_online_when_all_services_up(self):
        """Test runtime_snapshot status is online when all services are available."""
        def mock_probe_all_up(name, url, timeout=1.5):
            return platform_runtime.ServiceProbe(
                name=name,
                url=url,
                available=True,
                status="online",
                checked_at=platform_runtime.utc_now(),
                http_status=200,
                error=None
            )

        with patch("platform_runtime.probe_service", side_effect=mock_probe_all_up):
            snapshot = platform_runtime.runtime_snapshot(include_public_api=True)
            self.assertEqual(snapshot["status"], "online")
            self.assertEqual(len(snapshot["services"]), 6)

    def test_mq3_dashboard_port_env_handling(self):
        """Test valid and invalid env vars for mq3_dashboard_port."""
        valid_ports = [("5050", 5050), ("5055", 5055), ("8000", 8000)]
        for env_val, expected in valid_ports:
            with patch.dict(os.environ, {"JARVIS_MQ3_PORT": env_val}):
                self.assertEqual(platform_runtime.mq3_dashboard_port(), expected)

        invalid_ports = ["-1", "0", "70000", "not_int", ""]
        for env_val in invalid_ports:
            with patch.dict(os.environ, {"JARVIS_MQ3_PORT": env_val}):
                with patch("platform_runtime._load_json", return_value={}):
                    self.assertEqual(platform_runtime.mq3_dashboard_port(), 5050)


class TestSupervisorAndTelemetryStress(unittest.TestCase):
    """Empirically test supervisor service definitions and hardware vitals telemetry."""

    def test_supervisor_build_services_zero_port_collisions(self):
        """Verify build_services defines distinct ports for all port-based services."""
        services = supervisor.build_services()
        ports = [key for name, kind, key, cmd, cwd in services if kind == "port"]
        self.assertEqual(len(ports), len(set(ports)), f"Port collision detected: {ports}")

    def test_supervisor_port_up_closed_and_open(self):
        """Verify supervisor.port_up handles both closed and open ports cleanly."""
        # Closed port
        self.assertFalse(supervisor.port_up(59122))
        
        # Test with a mock socket connect_ex returning 0
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_sock_cls.return_value = mock_sock
            self.assertTrue(supervisor.port_up(8770))

    def test_api_pc_schema_and_ranges(self):
        """Verify dashboard.api_pc returns valid ranges and schema."""
        vitals = dashboard.api_pc()
        self.assertIsInstance(vitals, dict)
        self.assertIn("cpu", vitals)
        self.assertIn("mem", vitals)
        self.assertIn("disk_c", vitals)
        self.assertIn("disk_p", vitals)
        self.assertIn("procs", vitals)
        self.assertGreaterEqual(vitals["cpu"], 0.0)
        self.assertLessEqual(vitals["cpu"], 100.0)
        self.assertGreaterEqual(vitals["mem"], 0.0)
        self.assertLessEqual(vitals["mem"], 100.0)
        self.assertGreaterEqual(vitals["procs"], 1)


if __name__ == "__main__":
    unittest.main()
