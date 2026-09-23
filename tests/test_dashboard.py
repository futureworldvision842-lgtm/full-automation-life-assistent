"""
Unit Tests for Dashboard Hardware Telemetry & Probes (dashboard.py)
Milestone M1 / Requirement R1 / Feature F-SUP-03
"""

import sys
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def load_dashboard():
    dash_path = BASE_DIR / "dashboard.py"
    spec = importlib.util.spec_from_file_location("jarvis_dashboard_test", str(dash_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDashboard(unittest.TestCase):
    """Test suite for dashboard hardware telemetry and platform status APIs."""

    @classmethod
    def setUpClass(cls):
        cls.dash = load_dashboard()

    def test_api_pc_schema_completeness(self):
        result = self.dash.api_pc()
        self.assertIsInstance(result, dict)
        for key in ("cpu", "mem", "disk_c", "disk_p", "procs"):
            self.assertIn(key, result, f"Expected key '{key}' in /api/pc payload")
            self.assertIsInstance(result[key], (int, float), f"Key '{key}' should be numeric")

    def test_api_pc_range_validity(self):
        result = self.dash.api_pc()
        self.assertGreaterEqual(result["cpu"], 0.0)
        self.assertLessEqual(result["cpu"], 100.0)
        self.assertGreaterEqual(result["mem"], 0.0)
        self.assertLessEqual(result["mem"], 100.0)
        self.assertGreaterEqual(result["disk_c"], 0.0)
        self.assertLessEqual(result["disk_c"], 100.0)
        self.assertGreaterEqual(result["disk_p"], 0.0)
        self.assertLessEqual(result["disk_p"], 100.0)
        self.assertGreater(result["procs"], 0)

    def test_api_pc_exception_graceful_recovery(self):
        with patch("psutil.cpu_percent", side_effect=RuntimeError("Hardware sensor disconnected")):
            result = self.dash.api_pc()
            self.assertIn("error", result)
            self.assertEqual(result["cpu"], 0)
            self.assertEqual(result["mem"], 0)
            self.assertEqual(result["disk_c"], 0)
            self.assertEqual(result["disk_p"], 0)
            self.assertEqual(result["procs"], 0)

    def test_api_platform_status_returns_valid_snapshot(self):
        from platform_runtime import ServiceProbe
        with patch("platform_runtime.probe_service") as mock_probe:
            mock_probe.return_value = ServiceProbe(
                name="test",
                url="http://localhost:8770",
                available=True,
                status="online",
                checked_at="2026-08-24T00:00:00Z",
                latency_ms=5,
                http_status=200,
                error=None,
                details=None
            )
            snapshot = self.dash.api_platform_status()
            self.assertIsInstance(snapshot, dict)
            self.assertIn("status", snapshot)
            self.assertIn("services", snapshot)

    def test_api_integrations_returns_endpoints(self):
        integrations = self.dash.api_integrations()
        self.assertIsInstance(integrations, dict)
        self.assertIn("mq3", integrations)
        self.assertIn("world_monitor", integrations)
        self.assertIn("whatsapp_qr", integrations)


if __name__ == "__main__":
    unittest.main()
