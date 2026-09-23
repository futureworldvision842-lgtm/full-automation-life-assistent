import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bootstrap import lifecycle
from platform_runtime import MQ3_ROOT, WORLD_MONITOR_ROOT


class LifecycleTests(unittest.TestCase):
    def test_only_known_runtime_in_known_project_is_managed(self):
        self.assertTrue(lifecycle.process_is_managed("python.exe", ["python", "main.py"], str(lifecycle.ROOT)))
        self.assertFalse(lifecycle.process_is_managed("python.exe", ["python", "main.py"], r"C:\unrelated"))
        self.assertFalse(lifecycle.process_is_managed("notepad.exe", ["notepad"], str(lifecycle.ROOT)))

    def test_external_integration_runtime_is_managed_by_exact_root(self):
        external = lifecycle.KNOWN_PROJECT_ROOTS[1]
        self.assertTrue(lifecycle.process_is_managed("bun.exe", ["bun", "start"], str(external)))

    def test_manual_stop_flag_is_explicit_and_reversible(self):
        with tempfile.TemporaryDirectory() as folder:
            flag = Path(folder) / "jarvis.stop"
            with patch.object(lifecycle, "STOP_FLAG", flag):
                lifecycle.request_manual_stop("unit-test")
                self.assertEqual(flag.read_text(encoding="utf-8"), "unit-test\n")
                lifecycle.clear_manual_stop()
                self.assertFalse(flag.exists())

    def test_mq3_and_world_monitor_roots_registered(self):
        self.assertIn(MQ3_ROOT, lifecycle.KNOWN_PROJECT_ROOTS)
        self.assertIn(WORLD_MONITOR_ROOT, lifecycle.KNOWN_PROJECT_ROOTS)

    def test_autonomous_live_daemon_and_run_py_managed(self):
        self.assertIn("autonomous_live_daemon.py", lifecycle.MANAGED_MARKERS)
        self.assertIn("run.py", lifecycle.MANAGED_MARKERS)
        self.assertTrue(lifecycle.process_is_managed(
            "python.exe",
            ["python", "src/autonomous_live_daemon.py"],
            str(MQ3_ROOT)
        ))

    def test_stop_managed_processes_dry_run(self):
        result = lifecycle.stop_managed_processes(reason="test-dry-run", dry_run=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertFalse(result["manualStop"])
        self.assertIsInstance(result["processes"], list)


if __name__ == "__main__":
    unittest.main()
