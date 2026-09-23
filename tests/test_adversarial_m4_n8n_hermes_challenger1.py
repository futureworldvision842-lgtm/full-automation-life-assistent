"""
tests/test_adversarial_m4_n8n_hermes_challenger1.py
================================================================================
Empirical Adversarial Challenge Suite for Milestone M4:
Local n8n Server, Hermes-3 Agent & 1-Click Lifecycle Controls.

Author: Challenger 1 (teamwork_preview_challenger_m4_1)
Mission:
  1. Empirically stress-test local n8n DAG engine and 5 institutional workflows:
     - Test timeout fallback when n8n server is offline / hanging / erroring.
     - Test execution of each workflow with corrupt / partial / hostile payload data.
     - Test 90+ confluence gate rejection when confluence is < 90 (boundary stress).
     - Verify SHA-256 audit signature authenticity, format, and entropy.
  2. Run stress tests and verify system robustness.
  3. Validate Hermes-3 tool execution robustness and lifecycle port governance.
================================================================================
"""

import os
import sys
import time
import re
import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from integrations.n8n_engine import (
    N8nWorkflowEngine,
    get_n8n_engine,
    run_morning_macro_workflow,
    run_whale_alert_workflow,
    run_news_circuit_breaker_workflow,
    run_defcon_escalation_workflow,
    run_broadcast_workflow,
)


class TestN8nTimeoutAndOfflineFallback(unittest.TestCase):
    """Stress-test external webhook failure modes and fallback to sovereign embedded DAG engine."""

    def setUp(self):
        # Use a non-existent port to guarantee external connection failure
        self.engine = N8nWorkflowEngine(n8n_url="http://127.0.0.1:59999")

    def test_fallback_when_n8n_server_offline(self):
        """When local n8n server is offline, trigger_workflow must fall back cleanly to embedded DAG."""
        t0 = time.time()
        res = self.engine.trigger_workflow("macro_briefing", {"scope": "test"})
        elapsed = time.time() - t0

        self.assertTrue(res.get("ok"), "Fallback execution must succeed")
        self.assertEqual(res.get("mode"), "SOVEREIGN_EMBEDDED_DAG")
        self.assertEqual(res.get("status"), "COMPLETED")
        self.assertEqual(res.get("workflow_id"), "macro_briefing")
        self.assertEqual(res.get("nodes_executed"), 5)
        # Verify fallback happens within 1.5 seconds even with network attempt
        self.assertLess(elapsed, 2.0, f"Fallback took too long: {elapsed:.2f}s")

    @patch("integrations.n8n_engine.requests.post")
    def test_fallback_when_n8n_webhook_hangs_timeout(self, mock_post):
        """Simulate a hanging webhook; engine must catch requests.Timeout and fall back seamlessly."""
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out after 0.3s")

        t0 = time.time()
        res = self.engine.trigger_workflow("whale_flow", {"min_usd": 2_000_000})
        elapsed = time.time() - t0

        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("mode"), "SOVEREIGN_EMBEDDED_DAG")
        self.assertEqual(res.get("nodes_executed"), 3)
        self.assertLess(elapsed, 1.0, f"Hanging timeout fallback took too long: {elapsed:.2f}s")

    @patch("integrations.n8n_engine.requests.post")
    def test_fallback_when_n8n_webhook_returns_http_500_or_502(self, mock_post):
        """When n8n server returns HTTP 500/502 error, engine must fall back to embedded DAG."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        res = self.engine.trigger_workflow("news_circuit_breaker", {})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("mode"), "SOVEREIGN_EMBEDDED_DAG")
        self.assertEqual(res.get("nodes_executed"), 3)

    def test_health_check_offline_returns_sovereign_embedded(self):
        """When n8n port is offline, health check must report EMBEDDED_SOVEREIGN_ENGINE mode."""
        health = self.engine.check_n8n_server_health()
        self.assertTrue(health.get("online"))
        self.assertEqual(health.get("mode"), "EMBEDDED_SOVEREIGN_ENGINE")
        self.assertIn("Embedded sovereign", health.get("message", ""))

    @patch("integrations.n8n_engine.requests.get")
    def test_health_check_online_returns_live_n8n_server(self, mock_get):
        """When n8n server responds with HTTP 200 on /healthz, report LIVE_N8N_SERVER mode."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        health = self.engine.check_n8n_server_health()
        self.assertTrue(health.get("online"))
        self.assertEqual(health.get("mode"), "LIVE_N8N_SERVER")


class TestInstitutionalWorkflowsCorruptAndPartialPayloads(unittest.TestCase):
    """Stress-test each of the 5 institutional workflows with malformed, hostile, or missing payload data."""

    def setUp(self):
        self.engine = get_n8n_engine()

    def test_workflow_1_macro_briefing_corrupt_payloads(self):
        """Workflow 1 (macro_briefing) must tolerate empty, None, and type-corrupted payloads."""
        # 1. Empty dict
        res1 = self.engine.trigger_workflow("macro_briefing", {})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("nodes_executed"), 5)

        # 2. None payload
        res2 = self.engine.trigger_workflow("macro_briefing", None)
        self.assertTrue(res2.get("ok"))
        self.assertEqual(res2.get("nodes_executed"), 5)

        # 3. Hostile / unexpected types
        res3 = self.engine.trigger_workflow("macro_briefing", {"scope": 12345, "yields": [1, 2, 3]})
        self.assertTrue(res3.get("ok"))

        # 4. Oversized payload
        res4 = self.engine.trigger_workflow("macro_briefing", {"noise": "x" * 20000})
        self.assertTrue(res4.get("ok"))

    def test_workflow_2_whale_flow_corrupt_payloads(self):
        """Workflow 2 (whale_flow) must survive invalid threshold values and null arguments."""
        # 1. Empty dict
        res1 = self.engine.trigger_workflow("whale_flow", {})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("nodes_executed"), 3)

        # 2. String instead of numeric threshold
        res2 = self.engine.trigger_workflow("whale_flow", {"min_usd": "ONE_MILLION_DOLLARS"})
        self.assertTrue(res2.get("ok"))

        # 3. Negative extreme threshold
        res3 = self.engine.trigger_workflow("whale_flow", {"threshold_usd": -999999999})
        self.assertTrue(res3.get("ok"))

    def test_workflow_3_news_circuit_breaker_corrupt_payloads(self):
        """Workflow 3 (news_circuit_breaker) must handle corrupted calendar event payloads."""
        # 1. Empty dict
        res1 = self.engine.trigger_workflow("news_circuit_breaker", {})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("nodes_executed"), 3)

        # 2. Malformed event object
        res2 = self.engine.trigger_workflow("news_circuit_breaker", {
            "event": {"title": None, "impact": 9999},
            "window_minutes": "FIFTEEN"
        })
        self.assertTrue(res2.get("ok"))

        # 3. Null values
        res3 = self.engine.trigger_workflow("news_circuit_breaker", {"event": None, "window_minutes": None})
        self.assertTrue(res3.get("ok"))

    def test_workflow_4_defcon_geopolitical_corrupt_payloads(self):
        """Workflow 4 (defcon_geopolitical) must handle missing or non-dict conflict parameters."""
        # 1. Empty dict
        res1 = self.engine.trigger_workflow("defcon_geopolitical", {})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("nodes_executed"), 3)

        # 2. Hostile parameters
        res2 = self.engine.trigger_workflow("defcon_geopolitical", {
            "chokepoints": "ALL_CLOSED",
            "action": 99999
        })
        self.assertTrue(res2.get("ok"))

    def test_workflow_5_discord_whatsapp_broadcast_corrupt_payloads(self):
        """Workflow 5 (discord_whatsapp_broadcast) must gracefully handle corrupt confluence scores."""
        # 1. Empty dict (defaults to 92.5)
        res1 = self.engine.trigger_workflow("discord_whatsapp_broadcast", {})
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("nodes_executed"), 5)

        # 2. Corrupt confluence: string not convertible to float
        res2 = self.engine.trigger_workflow("discord_whatsapp_broadcast", {"confluence": "INVALID_SCORE"})
        self.assertTrue(res2.get("ok"))
        # Node error is captured inside node details rather than crashing the engine
        confluence_node = next(n for n in res2["node_details"] if n["node"] == "validate_confluence")
        self.assertEqual(confluence_node["result"].get("status"), "ERROR")

        # 3. None confluence (NoneType)
        res3 = self.engine.trigger_workflow("discord_whatsapp_broadcast", {"confluence": None})
        self.assertTrue(res3.get("ok"))
        confluence_node3 = next(n for n in res3["node_details"] if n["node"] == "validate_confluence")
        self.assertEqual(confluence_node3["result"].get("status"), "ERROR")

        # 4. Hostile symbol and direction types
        res4 = self.engine.trigger_workflow("discord_whatsapp_broadcast", {
            "symbol": 12345,
            "direction": ["BUY", "SELL"],
            "confluence": 95.0
        })
        self.assertTrue(res4.get("ok"))
        card_node = next(n for n in res4["node_details"] if n["node"] == "format_institutional_card")
        self.assertEqual(card_node["result"].get("status"), "CARD_FORMATTED")

    def test_invalid_workflow_id_returns_error(self):
        """Requesting non-existent workflow id returns ok=False error without throwing."""
        res = self.engine.trigger_workflow("non_existent_institutional_flow", {})
        self.assertFalse(res.get("ok"))
        self.assertIn("error", res)


class TestConfluenceGate90PlusRejection(unittest.TestCase):
    """Stress-test the 90+ confluence gate with boundary values around 90.0."""

    def setUp(self):
        self.engine = get_n8n_engine()

    def _execute_gate(self, confluence_value):
        return self.engine._execute_node_action("risk_gate.verify_90_plus", {"confluence": confluence_value})

    def test_gate_admissions_above_or_equal_to_90(self):
        """Confluence >= 90.0 must be ADMITTED."""
        test_admissions = [
            (90.0, "exact 90.0 threshold"),
            (90.0001, "just above 90.0"),
            (92.5, "typical institutional score"),
            (99.9, "high conviction"),
            (100.0, "maximum theoretical score"),
            (105.0, "overshoot score"),
        ]
        for score, desc in test_admissions:
            with self.subTest(score=score, description=desc):
                res = self._execute_gate(score)
                self.assertTrue(res.get("passed"), f"Score {score} should pass gate: {res}")
                self.assertEqual(res.get("verdict"), "ADMITTED_INSTITUTIONAL_CONFLUENCE")
                self.assertEqual(res.get("confluence_score"), float(score))

    def test_gate_rejections_below_90(self):
        """Confluence < 90.0 must be strictly REJECTED."""
        test_rejections = [
            (89.9999, "just below 90.0 threshold"),
            (89.9, "near threshold sub-90"),
            (85.0, "moderate sub-90"),
            (75.0, "retail grade"),
            (50.0, "coin flip"),
            (0.0, "zero conviction"),
            (-10.0, "negative confluence"),
        ]
        for score, desc in test_rejections:
            with self.subTest(score=score, description=desc):
                res = self._execute_gate(score)
                self.assertFalse(res.get("passed"), f"Score {score} should be rejected: {res}")
                self.assertEqual(res.get("verdict"), "REJECTED_BELOW_90")
                self.assertEqual(res.get("confluence_score"), float(score))

    def test_broadcast_workflow_reflects_sub_90_rejection_in_node_results(self):
        """In discord_whatsapp_broadcast, a sub-90 confluence score explicitly records REJECTED_BELOW_90."""
        res_rejected = run_broadcast_workflow({"confluence": 88.5, "symbol": "XAUUSD"})
        self.assertTrue(res_rejected.get("ok"))
        val_node = next(n for n in res_rejected["node_details"] if n["node"] == "validate_confluence")
        self.assertFalse(val_node["result"].get("passed"))
        self.assertEqual(val_node["result"].get("verdict"), "REJECTED_BELOW_90")

        res_passed = run_broadcast_workflow({"confluence": 94.0, "symbol": "XAUUSD"})
        self.assertTrue(res_passed.get("ok"))
        val_node_p = next(n for n in res_passed["node_details"] if n["node"] == "validate_confluence")
        self.assertTrue(val_node_p["result"].get("passed"))
        self.assertEqual(val_node_p["result"].get("verdict"), "ADMITTED_INSTITUTIONAL_CONFLUENCE")


class TestSha256AuditSignatureAuthenticity(unittest.TestCase):
    """Verify cryptographic authenticity, formatting, entropy, and tamper-resistance of audit signatures."""

    def setUp(self):
        self.engine = get_n8n_engine()

    def _generate_signature(self, symbol="XAUUSD"):
        return self.engine._execute_node_action("audit.sign_receipt", {"symbol": symbol})

    def test_signature_format_and_sha256_spec(self):
        """Signature must be a 64-character lowercase hexadecimal SHA-256 digest."""
        sig_data = self._generate_signature()
        self.assertEqual(sig_data.get("algorithm"), "SHA-256")
        self.assertEqual(sig_data.get("status"), "CRYPTOGRAPHICALLY_SIGNED")
        self.assertIn("audit_signature", sig_data)

        digest = sig_data["audit_signature"]
        self.assertIsInstance(digest, str)
        self.assertEqual(len(digest), 64, f"SHA-256 digest must be 64 characters, got {len(digest)}")
        self.assertRegex(digest, r"^[a-f0-9]{64}$", "Digest must consist exclusively of lowercase hex chars")

    def test_signature_entropy_and_uniqueness(self):
        """Sequential signature requests must produce unique digests (entropy via timestamp)."""
        signatures = set()
        for _ in range(10):
            sig = self._generate_signature("XAUUSD")["audit_signature"]
            self.assertNotIn(sig, signatures, "Collision detected in SHA-256 audit signatures!")
            signatures.add(sig)
            time.sleep(0.002)  # Tiny pause to advance time.time() counter

        self.assertEqual(len(signatures), 10)

    def test_signature_timestamp_iso_validity(self):
        """Timestamp in audit receipt must be a valid ISO 8601 string."""
        sig_data = self._generate_signature()
        ts_str = sig_data.get("timestamp")
        self.assertIsNotNone(ts_str)
        # Parse ISO string
        parsed = datetime.fromisoformat(ts_str)
        self.assertIsInstance(parsed, datetime)


class TestHermesAgentRobustnessAndLifecycleSafety(unittest.TestCase):
    """Stress-test Hermes-3 tool execution handling and lifecycle port management."""

    def test_hermes_tool_execution_unregistered_tool(self):
        """HermesAgent must handle unknown tool gracefully without uncaught exception."""
        from brain.hermes_agent import get_hermes_agent
        agent = get_hermes_agent()
        res = agent.execute_tool("totally_unknown_tool_xyz", {"arg": 123})
        self.assertTrue(isinstance(res, (dict, str)))
        self.assertIn("totally_unknown_tool_xyz", str(res))

    def test_hermes_tool_execution_with_corrupt_arguments(self):
        """HermesAgent tool execution with unexpected argument types handles safely."""
        from brain.hermes_agent import get_hermes_agent
        agent = get_hermes_agent()
        # Pass non-string symbol to hft_dom_analyzer
        res = agent.execute_tool("hft_dom_analyzer", {"symbol": None})
        self.assertTrue(isinstance(res, (dict, str)))
        self.assertIn("HFT", str(res))

    def test_lifecycle_core_ports_tuple_invariants(self):
        """Core ports tuple must strictly contain 9 ports with Ollama (11434), WA (3200), n8n (5678)."""
        from bootstrap.lifecycle import CORE_PORTS
        self.assertEqual(len(CORE_PORTS), 9)
        self.assertNotIn(11435, CORE_PORTS)
        for p in (8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678):
            self.assertIn(p, CORE_PORTS)

    def test_lifecycle_safe_port_freeing_on_idle_ports(self):
        """free_ports on inactive / unbound ports must return cleanly without hanging."""
        from bootstrap.lifecycle import free_ports
        freed = free_ports([59998, 59999])
        self.assertIsInstance(freed, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
