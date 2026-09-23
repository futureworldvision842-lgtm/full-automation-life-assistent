"""
tests/test_m4_n8n_hermes_lifecycle_suite.py
================================================================================
Comprehensive Milestone M4 Verification Test Suite.
Validates:
  1. Local n8n Server & 5 Sovereign Embedded DAG Workflows (R5)
  2. Exportable standard n8n v1 JSON templates in config/workflows/ (R5)
  3. Nous Hermes-3 Cognitive Agent & 26 Structured Function Schemas (R6)
  4. User Identity & Credential Segregation in Human Intervention Gateway (R6)
  5. Desktop 1-Click Complete System Lifecycle Controls & Port Management (R7)
================================================================================
"""

import os
import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestM4_N8nEngineAndWorkflows(unittest.TestCase):
    """Verifies local n8n server connection, sovereign embedded DAG execution, and JSON templates."""

    def setUp(self):
        from integrations.n8n_engine import get_n8n_engine
        self.engine = get_n8n_engine()

    def test_n8n_server_health_and_fallback(self):
        """Engine must provide health check defaulting to :5678 and fallback to embedded sovereign DAG."""
        health = self.engine.check_n8n_server_health()
        self.assertTrue(health.get("online"))
        self.assertIn("url", health)
        self.assertIn(":5678", health["url"])
        self.assertIn(health.get("mode"), ("LIVE_N8N_SERVER", "EMBEDDED_SOVEREIGN_ENGINE"))

    def test_all_five_institutional_workflows_registered(self):
        """All 5 institutional workflows specified in R5 must be registered."""
        flows = {w["id"]: w for w in self.engine.list_workflows()}
        required = [
            "macro_briefing",
            "whale_flow",
            "news_circuit_breaker",
            "defcon_geopolitical",
            "discord_whatsapp_broadcast",
        ]
        for req in required:
            self.assertIn(req, flows, f"Workflow '{req}' must be defined in n8n engine")
            self.assertTrue(flows[req].get("active"))
            self.assertGreater(len(flows[req].get("nodes", [])), 0)

    def test_all_five_json_templates_valid(self):
        """Exportable standard n8n v1 JSON templates must exist in config/workflows/ and be well-formed."""
        wf_dir = ROOT / "config" / "workflows"
        self.assertTrue(wf_dir.exists(), "config/workflows directory must exist")
        required_templates = [
            "morning_macro.json",
            "whale_alert.json",
            "news_circuit_breaker.json",
            "defcon_escalation.json",
            "discord_whatsapp_broadcast.json",
        ]
        for tpl_name in required_templates:
            tpl_path = wf_dir / tpl_name
            self.assertTrue(tpl_path.exists(), f"Workflow template '{tpl_name}' must exist")
            content = json.loads(tpl_path.read_text(encoding="utf-8"))
            self.assertIn("name", content)
            self.assertIn("nodes", content)
            self.assertIn("connections", content)
            self.assertIsInstance(content["nodes"], list)
            self.assertGreater(len(content["nodes"]), 0)
            self.assertIsInstance(content["connections"], dict)

    def test_macro_briefing_embedded_execution(self):
        """Morning Macro Briefing flow must execute genuine DAG nodes and return synthesized briefing."""
        res = self.engine.trigger_workflow("macro_briefing", {"scope": "all_assets"})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("nodes_executed"), 5)
        self.assertEqual(res.get("status"), "COMPLETED")
        actions = [n["action"] for n in res.get("node_details", [])]
        self.assertIn("institutional_matrix", actions)
        self.assertIn("ai_summary", actions)

    def test_whale_flow_embedded_execution(self):
        """Whale Transfer & On-Chain Flow Monitor must evaluate netflow bias and large transfers."""
        res = self.engine.trigger_workflow("whale_flow", {"threshold_usd": 1_000_000})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("nodes_executed"), 3)
        actions = [n["action"] for n in res.get("node_details", [])]
        self.assertIn("onchain.whales", actions)
        self.assertIn("crypto.bias", actions)

    def test_news_circuit_breaker_embedded_execution(self):
        """Economic News Circuit Breaker must inspect 15m blackout window."""
        res = self.engine.trigger_workflow("news_circuit_breaker", {"event": "CPI_RELEASE"})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("nodes_executed"), 3)
        actions = [n["action"] for n in res.get("node_details", [])]
        self.assertIn("mq3_trading.calendar", actions)
        self.assertIn("risk_gate.lockout", actions)

    def test_defcon_geopolitical_embedded_execution(self):
        """Geopolitical DEFCON Escalation flow must calculate shock multiplier."""
        res = self.engine.trigger_workflow("defcon_geopolitical", {"alert": "CHOKEPOINT_TENSION"})
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("nodes_executed"), 3)
        actions = [n["action"] for n in res.get("node_details", [])]
        self.assertIn("world_monitor.conflict", actions)
        self.assertIn("trading.risk_multiplier", actions)

    def test_discord_whatsapp_broadcast_embedded_execution(self):
        """High-Conviction Broadcast must verify 90+ confluence and sign audit receipt."""
        res = self.engine.trigger_workflow("discord_whatsapp_broadcast", {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "confluence": 94.5
        })
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("nodes_executed"), 5)
        actions = [n["action"] for n in res.get("node_details", [])]
        self.assertIn("risk_gate.verify_90_plus", actions)
        self.assertIn("format.signal_card", actions)
        self.assertIn("audit.sign_receipt", actions)

    def test_dag_runner_convenience_functions(self):
        """Module-level convenience runners must execute corresponding workflows cleanly."""
        from integrations.n8n_engine import (
            run_morning_macro_workflow,
            run_whale_alert_workflow,
            run_news_circuit_breaker_workflow,
            run_defcon_escalation_workflow,
            run_broadcast_workflow
        )
        self.assertTrue(run_morning_macro_workflow().get("ok"))
        self.assertTrue(run_whale_alert_workflow().get("ok"))
        self.assertTrue(run_news_circuit_breaker_workflow().get("ok"))
        self.assertTrue(run_defcon_escalation_workflow().get("ok"))
        self.assertTrue(run_broadcast_workflow({"confluence": 93.0}).get("ok"))


class TestM4_HermesCognitiveAgentAndSchemas(unittest.TestCase):
    """Verifies Hermes-3 tool registry expansion (>=24 structured schemas), XML generation, and dispatch."""

    def setUp(self):
        from brain.hermes_agent import get_hermes_agent
        self.agent = get_hermes_agent()

    def test_tool_registry_has_at_least_24_schemas(self):
        """Registry must contain at least 24 structured schemas (configured: 26)."""
        tools = self.agent.registry.tools
        self.assertIsInstance(tools, list)
        self.assertGreaterEqual(len(tools), 24)
        self.assertEqual(len(tools), 26)

    def test_all_26_schemas_well_formed_json_schemas(self):
        """Every tool schema must be a valid JSON function schema with properties and required array."""
        for tool in self.agent.registry.tools:
            self.assertEqual(tool.get("type"), "function")
            fn = tool.get("function", {})
            self.assertIn("name", fn)
            self.assertIn("description", fn)
            self.assertGreater(len(fn["description"]), 10)
            params = fn.get("parameters", {})
            self.assertEqual(params.get("type"), "object")
            self.assertIn("properties", params)
            self.assertIn("required", params)
            self.assertIsInstance(params["properties"], dict)
            self.assertIsInstance(params["required"], list)

    def test_browser_tools_schemas_present(self):
        """All 8 browser automation tools must be registered."""
        tool_names = {t["function"]["name"] for t in self.agent.registry.tools}
        browser_tools = [
            "browser_navigate",
            "browser_click",
            "browser_type",
            "browser_press",
            "browser_screenshot",
            "browser_scroll",
            "browser_wait",
            "browser_close",
        ]
        for b in browser_tools:
            self.assertIn(b, tool_names, f"Browser tool '{b}' must be in Hermes registry")

    def test_trading_and_hft_tools_schemas_present(self):
        """All 6 quantitative trading & HFT tools must be registered."""
        tool_names = {t["function"]["name"] for t in self.agent.registry.tools}
        trading_tools = [
            "mq3_trading",
            "trading_risk_kernel",
            "hft_dom_analyzer",
            "circuit_breaker_check",
            "breakeven_lock_enforcer",
            "cvd_divergence_detector",
        ]
        for t in trading_tools:
            self.assertIn(t, tool_names, f"Trading tool '{t}' must be in Hermes registry")

    def test_intelligence_and_macro_tools_schemas_present(self):
        """All 4 intelligence & macro tools must be registered."""
        tool_names = {t["function"]["name"] for t in self.agent.registry.tools}
        macro_tools = [
            "world_monitor",
            "institutional_matrix",
            "optical_motion_detector",
            "defcon_escalation_flow",
        ]
        for m in macro_tools:
            self.assertIn(m, tool_names, f"Macro tool '{m}' must be in Hermes registry")

    def test_workflows_and_os_tools_schemas_present(self):
        """All 4 workflow/comm and 4 OS/system tools must be registered."""
        tool_names = {t["function"]["name"] for t in self.agent.registry.tools}
        other_tools = [
            "n8n_workflows", "discord_broadcast", "whatsapp_message", "voice_synthesizer",
            "computer_control", "app_launcher", "process_manager", "system_diagnostics",
        ]
        for o in other_tools:
            self.assertIn(o, tool_names, f"Tool '{o}' must be in Hermes registry")

    def test_hermes_prompt_header_xml_format(self):
        """Prompt header must output official Nous Hermes XML <tools> and <tool_call> tags."""
        header = self.agent.registry.get_hermes_prompt_header()
        self.assertIn("<tools>", header)
        self.assertIn("</tools>", header)
        self.assertIn("<tool_call>", header)
        self.assertIn("</tool_call>", header)

    def test_hermes_parser_extracts_calls(self):
        """HermesParser must extract structured tool calls from XML and JSON formats."""
        from brain.hermes_agent import HermesParser
        xml_input = (
            "<tool_call>\n"
            '{"name": "hft_dom_analyzer", "arguments": {"symbol": "XAUUSD"}}\n'
            "</tool_call>"
        )
        calls = HermesParser.extract_tool_calls(xml_input)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "hft_dom_analyzer")
        self.assertEqual(calls[0][1]["symbol"], "XAUUSD")

    def test_tool_dispatch_execution(self):
        """execute_tool must dispatch to actual subsystem implementations."""
        res_diag = self.agent.execute_tool("system_diagnostics", {})
        self.assertIsInstance(res_diag, dict)
        self.assertEqual(res_diag.get("status"), "HEALTHY")
        self.assertIn("cpu_percent", res_diag)
        self.assertIn("ram_used_gb", res_diag)

        res_hft = self.agent.execute_tool("hft_dom_analyzer", {"symbol": "XAUUSD"})
        self.assertIn("DEPTH OF MARKET", str(res_hft))

        res_cvd = self.agent.execute_tool("cvd_divergence_detector", {"symbol": "GBPUSD"})
        self.assertIn("CUMULATIVE VOLUME DELTA", str(res_cvd))

        res_wa = self.agent.execute_tool("whatsapp_message", {"message": "Test Alert"})
        self.assertEqual(res_wa.get("status"), "WHATSAPP_DISPATCHED")

    def test_browser_control_compatibility(self):
        """actions/browser_control.py must define default browser detection and binaries."""
        import actions.browser_control as bc
        self.assertTrue(hasattr(bc, "browser_control"))
        self.assertTrue(hasattr(bc, "_get_default_browser_id"))
        self.assertTrue(hasattr(bc, "_BROWSER_BINARIES"))


class TestM4_HumanInterventionAndAccountSegregation(unittest.TestCase):
    """Verifies strict separation between FundingPips prop firm credentials and General operations."""

    def setUp(self):
        from core.human_intervention_gateway import HumanInterventionGateway
        self.gw = HumanInterventionGateway()

    def test_credentials_constants_values(self):
        """Credential constants must match authoritative accounts exactly."""
        from core.human_intervention_gateway import (
            FUNDINGPIPS_EMAIL,
            FUNDINGPIPS_PASSWORD,
            FUNDINGPIPS_ACCOUNT_ID,
            FUNDINGPIPS_PORTAL_URL,
            DEFAULT_OWNER_EMAIL,
            DEFAULT_OWNER_PHONE
        )
        self.assertEqual(FUNDINGPIPS_EMAIL, "hamidqureshi872@gmail.com")
        self.assertEqual(FUNDINGPIPS_PASSWORD, "AHMA5ss$#")
        self.assertEqual(FUNDINGPIPS_ACCOUNT_ID, "40000294403")
        self.assertEqual(FUNDINGPIPS_PORTAL_URL, "https://app.fundingpips.com/login")
        self.assertEqual(DEFAULT_OWNER_EMAIL, "futureworldvision842@gmail.com")
        self.assertEqual(DEFAULT_OWNER_PHONE, "923468053268")

    def test_2fa_request_stores_fundingpips_user_and_dest(self):
        """request_2fa_code for FundingPips must populate eff_user and eff_dest without empty fallback."""
        req = self.gw.request_2fa_code("FundingPips Portal")
        self.assertEqual(req.account_username, "hamidqureshi872@gmail.com")
        self.assertIn("hamidqureshi872@gmail.com", req.code_destination)
        self.assertIn("hamidqureshi872@gmail.com", req.reason_technical)

    def test_2fa_request_stores_general_user_and_dest(self):
        """request_2fa_code for general services must populate general owner email and destination."""
        req = self.gw.request_2fa_code("General System Operation")
        self.assertEqual(req.account_username, "futureworldvision842@gmail.com")
        self.assertIn("futureworldvision842@gmail.com", req.code_destination)
        self.assertIn("futureworldvision842@gmail.com", req.reason_technical)

    def test_captcha_request_segregation(self):
        """request_captcha_resolution must properly segregate FundingPips from General."""
        fp_cap = self.gw.request_captcha_resolution("FundingPips Portal", "https://app.fundingpips.com")
        self.assertEqual(fp_cap.account_username, "hamidqureshi872@gmail.com")

        gen_cap = self.gw.request_captcha_resolution("Cloudflare DEX", "https://dexscreener.com")
        self.assertEqual(gen_cap.account_username, "futureworldvision842@gmail.com")


class TestM4_LifecycleControlsAndFleetLauncher(unittest.TestCase):
    """Verifies core ports configuration, 10-daemon launcher, and batch controls."""

    def test_lifecycle_core_ports_typo_fixed_and_ports_present(self):
        """Typo 11435 must be absent, and 11434 (Ollama), 3200 (WA), 5678 (n8n) must be present."""
        from bootstrap.lifecycle import CORE_PORTS
        self.assertNotIn(11435, CORE_PORTS, "Port 11435 was a typo and must NOT be in CORE_PORTS")
        self.assertIn(11434, CORE_PORTS, "Port 11434 (Ollama) must be in CORE_PORTS")
        self.assertIn(3200, CORE_PORTS, "Port 3200 (WhatsApp) must be in CORE_PORTS")
        self.assertIn(5678, CORE_PORTS, "Port 5678 (n8n) must be in CORE_PORTS")
        expected_tuple = (8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678)
        self.assertEqual(CORE_PORTS, expected_tuple)

    def test_free_ports_function_callable(self):
        """free_ports must be callable and return freed ports list."""
        from bootstrap.lifecycle import free_ports
        res = free_ports([99999])
        self.assertIsInstance(res, list)

    def test_kill_process_tree_fallback_safe(self):
        """kill_process_tree must handle invalid or unmanaged PID safely."""
        from bootstrap.lifecycle import kill_process_tree
        self.assertFalse(kill_process_tree(-1))
        self.assertFalse(kill_process_tree(0))

    def test_master_launcher_configures_ten_fleet_daemons(self):
        """SERVICES in master_ecosystem_launcher must configure exactly 10 fleet daemons."""
        from bootstrap.master_ecosystem_launcher import SERVICES
        self.assertEqual(len(SERVICES), 10)
        expected = [
            "dashboard", "godseye", "worldmonitor", "mq3", "odysseus",
            "mobile", "trader", "ollama", "discord", "whatsapp"
        ]
        for key in expected:
            self.assertIn(key, SERVICES)
            self.assertIn("cmd", SERVICES[key])
            self.assertIn("port", SERVICES[key])

    def test_batch_controls_exist_and_in_sync(self):
        """Root START and STOP batch files must exist and configure all daemons."""
        start_bat = ROOT / "JARVIS - START ALL.bat"
        stop_bat = ROOT / "JARVIS - STOP ALL.bat"
        self.assertTrue(start_bat.exists())
        self.assertTrue(stop_bat.exists())

        start_txt = start_bat.read_text(encoding="utf-8")
        self.assertIn("10 SERVICES STARTED SUCCESSFULLY!", start_txt)
        self.assertIn("40000294403", start_txt)

        stop_txt = stop_bat.read_text(encoding="utf-8")
        self.assertIn("5678", stop_txt)
        self.assertIn("3200", stop_txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
