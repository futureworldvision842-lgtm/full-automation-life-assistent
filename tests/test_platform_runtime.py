"""
Unit Tests for Platform Runtime & Service Probes (platform_runtime.py)
Milestone M1 / Requirement R1 / Feature F-SUP-01 & F-SUP-03
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import platform_runtime


class TestPlatformRuntime(unittest.TestCase):
    """Test suite for platform runtime contracts, probes, and port standardizations."""

    def test_mq3_dashboard_port_defaults_to_5050(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("platform_runtime._load_json", return_value={}):
                port = platform_runtime.mq3_dashboard_port()
                self.assertEqual(port, 5050, "Default MQ3 dashboard port must be 5050")

    def test_mq3_dashboard_port_env_override(self):
        with patch.dict(os.environ, {"JARVIS_MQ3_PORT": "5055"}):
            port = platform_runtime.mq3_dashboard_port()
            self.assertEqual(port, 5055)

    def test_mq3_dashboard_url_format(self):
        url = platform_runtime.MQ3_DASHBOARD_URL
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        self.assertIn("5050", url)

    def test_data_envelope_structure(self):
        envelope = platform_runtime.data_envelope(
            source="test_source",
            data={"key": "value"},
            status="live"
        )
        self.assertEqual(envelope["status"], "live")
        self.assertEqual(envelope["source"], "test_source")
        self.assertEqual(envelope["data"], {"key": "value"})
        self.assertIn("fetched_at", envelope)
        self.assertIsNone(envelope["error"])

    def test_runtime_snapshot_structure(self):
        with patch("platform_runtime.probe_service") as mock_probe:
            mock_probe.return_value = platform_runtime.ServiceProbe(
                name="test",
                url="http://localhost:8770",
                available=True,
                status="online",
                checked_at="2026-08-24T00:00:00Z",
                latency_ms=5,
                http_status=200
            )
            snapshot = platform_runtime.runtime_snapshot()
            self.assertIn("status", snapshot)
            self.assertIn("checked_at", snapshot)
            self.assertIn("services", snapshot)
            self.assertIn("projects", snapshot)
            self.assertIn("jarvis", snapshot["projects"])
            self.assertIn("mq3", snapshot["projects"])
            self.assertIn("world_monitor", snapshot["projects"])

    def test_public_urls_structure(self):
        urls = platform_runtime.public_urls()
        self.assertIn("mq3", urls)
        self.assertIn("world_monitor", urls)
        self.assertIn("whatsapp_qr", urls)
        self.assertIn("odysseus", urls)

    def test_token_generation_contracts(self):
        wa_tok = platform_runtime.wa_http_token()
        self.assertIsInstance(wa_tok, str)
        self.assertGreater(len(wa_tok), 10)

        cmd_tok = platform_runtime.internal_command_token()
        self.assertIsInstance(cmd_tok, str)
        self.assertGreater(len(cmd_tok), 10)


if __name__ == "__main__":
    unittest.main()
