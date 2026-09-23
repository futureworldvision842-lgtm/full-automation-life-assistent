"""
Unit Tests for Unified Process Supervisor (bootstrap/supervisor.py)
Milestone M1 / Requirement R1 / Feature F-SUP-01 & F-SUP-02
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bootstrap import supervisor
from platform_runtime import MQ3_ROOT, mq3_dashboard_port


class TestSupervisor(unittest.TestCase):
    """Test suite for Central Supervisor daemon orchestration and lifecycle."""

    def test_build_services_returns_valid_service_tuples(self):
        services = supervisor.build_services()
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0, "Supervisor should build at least 1 service")
        for s in services:
            self.assertEqual(len(s), 5, f"Service tuple {s} must have exactly 5 elements")
            name, kind, key, cmd, cwd = s
            self.assertIsInstance(name, str)
            self.assertIn(kind, ("port", "proc"))
            if kind == "port":
                self.assertIsInstance(key, int)
                self.assertGreater(key, 0)
                self.assertLessEqual(key, 65535)
            else:
                self.assertIsInstance(key, str)
            self.assertIsInstance(cmd, list)
            self.assertTrue(os.path.exists(cwd), f"Working directory {cwd} must exist")

    def test_daemon11_mq3_autonomous_live_scanner_present_when_file_exists(self):
        services = supervisor.build_services()
        service_names = [s[0] for s in services]
        mq3_daemon_file = os.path.join(str(MQ3_ROOT), "src", "autonomous_live_daemon.py")
        if os.path.exists(mq3_daemon_file):
            self.assertIn(
                "MQ3 Autonomous Live Scanner",
                service_names,
                "Daemon #11 (MQ3 Autonomous Live Scanner) must be registered in build_services()"
            )
            # Find the service tuple
            mq3_service = next(s for s in services if s[0] == "MQ3 Autonomous Live Scanner")
            self.assertEqual(mq3_service[1], "proc")
            self.assertEqual(mq3_service[2], "autonomous_live_daemon.py")
            self.assertIn("autonomous_live_daemon.py", " ".join(mq3_service[3]))

    def test_zero_port_collisions_across_all_monitored_services(self):
        """Verify all port-based services have unique, non-colliding port allocations."""
        services = supervisor.build_services()
        port_services = [s for s in services if s[1] == "port"]
        ports = [s[2] for s in port_services]
        duplicate_ports = {p for p in ports if ports.count(p) > 1}
        self.assertEqual(
            len(duplicate_ports), 0,
            f"Port collision detected among monitored services: {duplicate_ports}"
        )

    def test_mq3_telemetry_port_standardized_to_5050(self):
        """Verify default MQ3 cockpit port is 5050."""
        services = supervisor.build_services()
        mq3_cockpit = [s for s in services if s[0] == "MQ3 Trading Cockpit"]
        if mq3_cockpit:
            self.assertEqual(mq3_cockpit[0][2], 5050)
            self.assertIn("5050", mq3_cockpit[0][3])

    def test_port_up_contract(self):
        # Closed port on loopback returns False
        self.assertFalse(supervisor.port_up(59998))
        self.assertIsInstance(supervisor.port_up(8770), bool)

    def test_proc_running_contract(self):
        # Non-existent needle returns False
        self.assertFalse(supervisor.proc_running("non_existent_process_marker_xyz_9999"))

    def test_alive_dispatcher(self):
        with patch.object(supervisor, "port_up", return_value=True) as mock_port:
            self.assertTrue(supervisor.alive("port", 8770))
            mock_port.assert_called_once_with(8770)

        with patch.object(supervisor, "proc_running", return_value=True) as mock_proc:
            self.assertTrue(supervisor.alive("proc", "main.py"))
            mock_proc.assert_called_once_with("main.py")

    def test_spawn_process_flags(self):
        import subprocess
        with patch("subprocess.Popen") as mock_popen:
            supervisor.spawn("TestDaemon", [sys.executable, "test.py"], str(BASE_DIR))
            mock_popen.assert_called_once_with(
                [sys.executable, "test.py"],
                cwd=str(BASE_DIR),
                creationflags=supervisor.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def test_manual_stop_flag_exits_supervisor(self):
        with patch("os.path.exists", return_value=True):
            # When STOP_FLAG exists, main() returns immediately without spawning
            with patch("bootstrap.supervisor.build_services") as mock_build:
                supervisor.main()
                mock_build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
