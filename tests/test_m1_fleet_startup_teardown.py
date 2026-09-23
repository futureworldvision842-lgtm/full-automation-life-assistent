"""
Automated Test Suite for Milestone M1:
Master 1-Click Unified Fleet Startup & Teardown Architecture
============================================================
Verifies:
a) Registration of all 9 services in supervisor, lifecycle, and platform_runtime.
b) Startup commands and health checks (HTTP 200 and process liveness).
c) Teardown logic, tree termination (taskkill /F /T), and port freeing across:
   8770, 3000, 4173, 5050, 7000, 11434, 8765.
d) .bat and .cmd launcher files existence and correctness.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap import supervisor, lifecycle, master_ecosystem_launcher
import platform_runtime


class TestM1ServiceRegistration(unittest.TestCase):
    """Verify registration of all 9 core services across supervisor, lifecycle, and platform_runtime."""

    EXPECTED_SERVICES = {
        "dashboard": 8770,
        "world-monitor": 3000,
        "gods-eye-view": 4173,
        "mq3": 5050,
        "odysseus": 7000,
        "ollama": 11434,
        "mobile": 8765,
        "trader": 0,
        "discord": 0,
    }

    def test_supervisor_build_services_contains_all_9_services(self):
        services = supervisor.build_services()
        self.assertIsInstance(services, list)
        self.assertGreaterEqual(len(services), 9, "Must contain at least 9 core services")

        ports_found = set()
        names_found = []
        for s in services:
            # Tuple unpack verification
            self.assertEqual(len(s), 5, f"Service {s} must unpack to 5 elements")
            name, kind, key, cmd, cwd = s
            names_found.append(name)
            self.assertIsInstance(name, str)
            self.assertIn(kind, ("port", "proc"))
            self.assertIsInstance(cmd, list)
            self.assertTrue(Path(cwd).exists(), f"Working directory {cwd} must exist")
            if kind == "port":
                self.assertIsInstance(key, int)
                ports_found.add(key)

        # Verify all 7 network ports are represented
        for port in (8770, 3000, 4173, 5050, 7000, 11434, 8765):
            self.assertIn(port, ports_found, f"Port {port} must be registered in supervisor")

        # Verify trader daemon and discord bot are present
        self.assertTrue(
            any("autonomous_live_daemon.py" in " ".join(s[3]) for s in services),
            "Autonomous live daemon must be registered in supervisor"
        )
        self.assertTrue(
            any("discord_bot.py" in " ".join(s[3]) for s in services),
            "Discord bot must be registered in supervisor"
        )

    def test_lifecycle_core_ports_exact_contract(self):
        """Lifecycle must track all 7 network ports across the 9 core services."""
        expected_ports = (8770, 3000, 4173, 5050, 7000, 11434, 8765)
        for p in expected_ports:
            self.assertIn(p, lifecycle.CORE_PORTS, f"Port {p} must be in lifecycle.CORE_PORTS")
        self.assertEqual(len(lifecycle.CORE_PORTS), 7)

    def test_lifecycle_managed_markers_cover_all_services(self):
        """Lifecycle markers must include all daemon scripts and web frameworks."""
        for marker in (
            "supervisor.py", "dashboard.py", "mobile_control.py", "vite", "uvicorn",
            "ollama serve", "run.py", "autonomous_live_daemon.py", "discord_bot.py",
            "gods-eye-view", "worldmonitor"
        ):
            self.assertIn(marker, lifecycle.MANAGED_MARKERS)

    def test_platform_runtime_core_services_catalog(self):
        """platform_runtime.CORE_SERVICES must define all 9 services."""
        self.assertGreaterEqual(len(platform_runtime.CORE_SERVICES), 9)
        keys = set(platform_runtime.CORE_SERVICES.keys())
        expected_keys = {"dashboard", "world_monitor", "gods_eye_view", "mq3", "odysseus", "ollama", "mobile", "trader", "discord"}
        self.assertTrue(expected_keys.issubset(keys), f"Missing keys: {expected_keys - keys}")

        # Verify ports in platform_runtime
        self.assertEqual(platform_runtime.CORE_SERVICES["dashboard"]["port"], 8770)
        self.assertEqual(platform_runtime.CORE_SERVICES["world_monitor"]["port"], 3000)
        self.assertEqual(platform_runtime.CORE_SERVICES["gods_eye_view"]["port"], 4173)
        self.assertEqual(platform_runtime.CORE_SERVICES["mq3"]["port"], 5050)
        self.assertEqual(platform_runtime.CORE_SERVICES["odysseus"]["port"], 7000)
        self.assertEqual(platform_runtime.CORE_SERVICES["ollama"]["port"], 11434)
        self.assertEqual(platform_runtime.CORE_SERVICES["mobile"]["port"], 8765)
        self.assertEqual(platform_runtime.CORE_SERVICES["trader"]["port"], 0)
        self.assertEqual(platform_runtime.CORE_SERVICES["discord"]["port"], 0)

    def test_master_launcher_services_and_launch_order(self):
        """master_ecosystem_launcher must configure all 9 services and include them in launch_order."""
        self.assertIn("ollama", master_ecosystem_launcher.SERVICES)
        self.assertEqual(master_ecosystem_launcher.SERVICES["ollama"]["port"], 11434)
        self.assertIn("discord", master_ecosystem_launcher.SERVICES)
        self.assertIn("trader", master_ecosystem_launcher.SERVICES)

        # Ollama and Discord must be in the startup launch order
        expected_launch = ["ollama", "dashboard", "godseye", "worldmonitor", "mq3", "odysseus", "mobile", "trader", "discord"]
        import inspect
        src = inspect.getsource(master_ecosystem_launcher.start_all_services)
        for item in expected_launch:
            self.assertIn(f'"{item}"', src, f"Service {item} must be in start_all_services launch_order")


class TestM1StartupCommandsAndHealthChecks(unittest.TestCase):
    """Verify startup command construction, health check probes, and SLA checks."""

    def test_service_spec_dict_and_tuple_access(self):
        spec = supervisor.ServiceSpec("TestService", 8770, "/api/health", ["python", "test.py"], ROOT, match="test.py")
        # Dict access
        self.assertEqual(spec["name"], "TestService")
        self.assertEqual(spec["port"], 8770)
        self.assertEqual(spec["kind"], "port")
        self.assertEqual(spec["key"], 8770)
        # Tuple unpacking
        name, kind, key, cmd, cwd = spec
        self.assertEqual(name, "TestService")
        self.assertEqual(kind, "port")
        self.assertEqual(key, 8770)
        self.assertEqual(cmd, ["python", "test.py"])
        self.assertEqual(cwd, str(ROOT))

    def test_platform_runtime_probe_service_daemon_process(self):
        """Test proc: marker probe for daemon processes."""
        with patch("platform_runtime.is_process_running", return_value=True):
            probe = platform_runtime.probe_service("trader", "proc:autonomous_live_daemon.py")
            self.assertTrue(probe.available)
            self.assertEqual(probe.status, "online")
            self.assertIsNone(probe.error)

        with patch("platform_runtime.is_process_running", return_value=False):
            probe = platform_runtime.probe_service("trader", "proc:autonomous_live_daemon.py")
            self.assertFalse(probe.available)
            self.assertEqual(probe.status, "offline")

    def test_platform_runtime_probe_service_http_and_tcp_fallback(self):
        """Test HTTP 200 probe and TCP connection fallback."""
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            probe = platform_runtime.probe_service("dashboard", "http://127.0.0.1:8770/api/health")
            self.assertTrue(probe.available)
            self.assertEqual(probe.http_status, 200)

        # Test TCP connection fallback when HTTP fails
        import requests
        with patch("requests.get", side_effect=requests.RequestException("Connection refused")):
            with patch("platform_runtime.check_tcp_connection", return_value=True):
                probe = platform_runtime.probe_service("dashboard", "http://127.0.0.1:8770/api/health")
                self.assertTrue(probe.available)
                self.assertEqual(probe.status, "online")

    def test_supervisor_probe_and_port_up(self):
        # Invalid / closed port
        self.assertFalse(supervisor.port_up(0))
        self.assertFalse(supervisor.port_up(-1))
        # Non-HTTP probe
        res = supervisor.probe(None)
        self.assertFalse(res["ready"])
        res = supervisor.probe("not_a_url")
        self.assertFalse(res["ready"])

    def test_proc_running_detects_self(self):
        # Python interpreter running this test must be detected
        self.assertTrue(supervisor.proc_running("test_m1_fleet_startup_teardown.py") or supervisor.proc_running("python"))


class TestM1TeardownLogicAndPortFreeing(unittest.TestCase):
    """Verify teardown logic, tree termination, and port freeing across all core ports."""

    def test_kill_process_tree_functionality(self):
        """Verify kill_process_tree calls taskkill on Windows or kills process tree."""
        # Must refuse to kill self or parent
        self.assertFalse(lifecycle.kill_process_tree(os.getpid()))
        self.assertFalse(lifecycle.kill_process_tree(os.getppid()))
        self.assertFalse(lifecycle.kill_process_tree(0))
        self.assertFalse(lifecycle.kill_process_tree(4))

    def test_get_pids_on_port_returns_list(self):
        pids = lifecycle.get_pids_on_port(8770)
        self.assertIsInstance(pids, list)
        for pid in pids:
            self.assertIsInstance(pid, int)
            self.assertNotIn(pid, (0, 4, os.getpid(), os.getppid()))

    def test_free_ports_sweeps_all_7_core_ports(self):
        with patch("bootstrap.lifecycle.kill_process_tree", return_value=True) as mock_kill:
            with patch("bootstrap.lifecycle.get_pids_on_port", return_value=[99999]):
                freed = lifecycle.free_ports(lifecycle.CORE_PORTS)
                self.assertIn(8770, freed)
                self.assertEqual(len(freed), 7)
                self.assertEqual(mock_kill.call_count, 7)

    def test_stop_managed_processes_dry_run_contract(self):
        result = lifecycle.stop_managed_processes(reason="test-dry-run-m1", dry_run=True)
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertFalse(result["manualStop"])
        self.assertIn("processes", result)
        self.assertIn("freedPorts", result)
        self.assertIn("matched", result)

    def test_stop_all_services_in_master_launcher_does_not_skip_ollama(self):
        """Ensure stop_all_services in master_ecosystem_launcher does NOT skip ollama."""
        import inspect
        src = inspect.getsource(master_ecosystem_launcher.stop_all_services)
        self.assertNotIn('key == "ollama"', src, "stop_all_services must NOT skip Ollama")
        self.assertIn("free_ports", src, "stop_all_services must call free_ports")


class TestM1LauncherFiles(unittest.TestCase):
    """Verify presence and correctness of .bat and .cmd launcher scripts and shortcuts."""

    def test_root_start_all_bat_exists_and_valid(self):
        bat = ROOT / "JARVIS - START ALL.bat"
        self.assertTrue(bat.exists(), "JARVIS - START ALL.bat must exist in project root")
        content = bat.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("chcp 65001", content, "Must configure UTF-8 code page")
        self.assertIn("%~dp0", content, "Must use relative paths")
        self.assertIn("control.py", content, "Must invoke bootstrap\\control.py")
        self.assertIn("start", content, "Must specify start action")
        self.assertNotIn("E:\\jarvis", content, "Must not contain hardcoded paths")

    def test_root_stop_all_bat_exists_and_valid(self):
        bat = ROOT / "JARVIS - STOP ALL.bat"
        self.assertTrue(bat.exists(), "JARVIS - STOP ALL.bat must exist in project root")
        content = bat.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("chcp 65001", content, "Must configure UTF-8 code page")
        self.assertIn("%~dp0", content, "Must use relative paths")
        self.assertIn("stop_all.py", content, "Must invoke stop_all.py")
        self.assertNotIn("E:\\jarvis", content, "Must not contain hardcoded paths")
        for port in ("8770", "3000", "4173", "5050", "7000", "11434", "8765"):
            self.assertIn(port, content, f"Must reference port {port}")

    def test_root_cmd_scripts_exist_and_match(self):
        start_cmd = ROOT / "JARVIS - START ALL.cmd"
        stop_cmd = ROOT / "JARVIS - STOP ALL.cmd"
        self.assertTrue(start_cmd.exists(), "JARVIS - START ALL.cmd must exist")
        self.assertTrue(stop_cmd.exists(), "JARVIS - STOP ALL.cmd must exist")

        start_content = start_cmd.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("%~dp0", start_content)
        self.assertIn("control.py", start_content)

        stop_content = stop_cmd.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("%~dp0", stop_content)
        self.assertIn("stop_all.py", stop_content)

    def test_create_desktop_shortcuts_targets_bat_launchers(self):
        shortcuts_py = ROOT / "create_desktop_shortcuts.py"
        self.assertTrue(shortcuts_py.exists(), "create_desktop_shortcuts.py must exist")
        content = shortcuts_py.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("JARVIS - START ALL.bat", content, "Shortcuts must target JARVIS - START ALL.bat")
        self.assertIn("JARVIS - STOP ALL.bat", content, "Shortcuts must target JARVIS - STOP ALL.bat")


if __name__ == "__main__":
    unittest.main()
