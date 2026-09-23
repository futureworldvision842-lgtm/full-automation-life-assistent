"""
tests/test_terminal_dashboard_m1.py
========================================================================================
Authoritative Milestone M1 Test Suite:
Rich Full-Screen Terminal Visualizer Dashboard & Dual-Mode CLI Console Verification
========================================================================================
"""

import os
import sys
import unittest
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ui.rich_terminal_dashboard import (
    RichTerminalDashboard,
    get_terminal_dashboard_data,
    render_terminal_dashboard,
    run_terminal_dashboard,
)
from platform_runtime import get_terminal_dashboard_data as get_runtime_terminal_data


class TestMilestone1_TerminalVisualizerPanels(unittest.TestCase):
    """Verifies all 4 dynamic panels and telemetry data contracts for Milestone M1."""

    def test_live_trading_panel_metrics(self):
        data = get_terminal_dashboard_data()
        trading = data.get("trading", {})
        
        self.assertIn("login", trading)
        self.assertIn("server", trading)
        self.assertIn("balance", trading)
        self.assertIn("equity", trading)
        self.assertIn("open_positions", trading)
        self.assertIn("floating_pnl", trading)
        self.assertIn("win_rate", trading)

        self.assertIsInstance(trading["login"], int)
        self.assertIsInstance(trading["server"], str)
        self.assertGreater(trading["balance"], 0.0)
        self.assertGreater(trading["equity"], 0.0)
        self.assertIsInstance(trading["open_positions"], list)
        self.assertIsInstance(trading["floating_pnl"], float)
        self.assertGreater(trading["win_rate"], 50.0)

    def test_defcon_geopolitical_radar_panel(self):
        data = get_terminal_dashboard_data()
        defcon = data.get("defcon", {})

        self.assertEqual(defcon.get("threat_level"), "DEFCON 2")
        self.assertEqual(defcon.get("gold_multiplier"), 1.45)
        self.assertEqual(defcon.get("sentiment"), "BEARISH_RISK_OFF")

        chokepoints = defcon.get("maritime_chokepoints", [])
        self.assertEqual(len(chokepoints), 5, "Must monitor exactly 5 strategic maritime corridors")

        names = [cp.get("name") for cp in chokepoints]
        self.assertTrue(any("Hormuz" in n for n in names))
        self.assertTrue(any("Bab el-Mandeb" in n or "Mandeb" in n for n in names))
        self.assertTrue(any("Suez" in n for n in names))
        self.assertTrue(any("Malacca" in n for n in names))
        self.assertTrue(any("Taiwan" in n for n in names))

        for cp in chokepoints:
            self.assertIn("status", cp)
            self.assertIn("threat_score", cp)
            self.assertIn("flow", cp)
            self.assertGreaterEqual(cp["threat_score"], 0)
            self.assertLessEqual(cp["threat_score"], 100)

    def test_core_fleet_and_node_vitals_panel(self):
        data = get_terminal_dashboard_data()
        fleet = data.get("fleet_vitals", {})

        expected_nodes = [
            "dashboard",      # :8770
            "mobile",         # :8765
            "mq3",            # :5050
            "odysseus",       # :7000
            "ollama",         # :11434
            "world_monitor",  # :3000
            "discord_bot",    # Discord Gateway
        ]

        for node in expected_nodes:
            self.assertIn(node, fleet, f"Expected node '{node}' in fleet_vitals")
            self.assertIsInstance(fleet[node], bool)

    def test_pc_system_vitals_panel(self):
        data = get_terminal_dashboard_data()
        vitals = data.get("system_vitals", {})

        self.assertIn("cpu_pct", vitals)
        self.assertIn("ram_pct", vitals)
        self.assertIn("gpu_pct", vitals)
        self.assertIn("network_latency_ms", vitals)

        self.assertIsInstance(vitals["cpu_pct"], float)
        self.assertIsInstance(vitals["ram_pct"], float)
        self.assertIsInstance(vitals["gpu_pct"], float)
        self.assertIsInstance(vitals["network_latency_ms"], float)

        self.assertGreaterEqual(vitals["cpu_pct"], 0.0)
        self.assertLessEqual(vitals["cpu_pct"], 100.0)
        self.assertGreaterEqual(vitals["ram_pct"], 0.0)
        self.assertLessEqual(vitals["ram_pct"], 100.0)

    def test_platform_runtime_data_equivalence(self):
        d1 = get_terminal_dashboard_data()
        d2 = get_runtime_terminal_data()
        self.assertEqual(d1["defcon"]["threat_level"], d2["defcon"]["threat_level"])
        self.assertEqual(len(d1["defcon"]["maritime_chokepoints"]), len(d2["defcon"]["maritime_chokepoints"]))


class TestMilestone1_InteractiveDualModeBilingualNLU(unittest.TestCase):
    """Verifies bilingual natural language command processing for Roman Urdu & English."""

    def setUp(self):
        self.dashboard = RichTerminalDashboard()

    def test_bilingual_roman_urdu_greetings(self):
        res = self.dashboard.execute_command("kya haal hai jarvis")
        self.assertTrue(any(w in res.lower() for w in ("alhamdulillah", "operational", "healthy", "ready")))

    def test_bilingual_roman_urdu_gold_analysis(self):
        res = self.dashboard.execute_command("aaj ka gold rate batao")
        self.assertIsInstance(res, str)
        self.assertGreater(len(res), 5)

    def test_bilingual_roman_urdu_positions(self):
        res = self.dashboard.execute_command("open trades dikhao")
        self.assertIsInstance(res, str)
        self.assertGreater(len(res), 0)

    def test_bilingual_roman_urdu_trading_stop(self):
        res = self.dashboard.execute_command("trading band karo")
        self.assertIsInstance(res, str)
        self.assertGreater(len(res), 0)

    def test_bilingual_roman_urdu_system_vitals(self):
        res = self.dashboard.execute_command("system vitals check karo")
        self.assertIn("CPU:", res)
        self.assertIn("RAM:", res)

    def test_english_defcon_and_chokepoints(self):
        res_defcon = self.dashboard.execute_command("defcon")
        self.assertIsInstance(res_defcon, str)

        res_cp = self.dashboard.execute_command("chokepoints")
        self.assertIsInstance(res_cp, str)

    def test_powershell_execution_command(self):
        res = self.dashboard.execute_command("!echo M1_VERIFIED")
        self.assertIn("M1_VERIFIED", res)

    def test_activity_log_history_tracking(self):
        self.dashboard.execute_command("trade status")
        self.dashboard.execute_command("kya haal hai")
        self.assertGreaterEqual(len(self.dashboard.command_history), 2)


class TestMilestone1_LayoutAndNonBlockingRendering(unittest.TestCase):
    """Verifies non-blocking UI layout and offline fallback."""

    def setUp(self):
        self.dashboard = RichTerminalDashboard()

    def test_rich_layout_generation(self):
        layout = self.dashboard.build_layout()
        self.assertIsNotNone(layout)
        for section in ["header", "trading", "defcon", "fleet", "system", "activity", "footer"]:
            self.assertIsNotNone(layout[section])

    def test_static_rendering_smoke(self):
        self.dashboard.render_static()
        render_terminal_dashboard()

    def test_offline_fallback_resilience(self):
        # Even when all ports are offline or unreachable, get_terminal_dashboard_data must return valid dict
        data = get_terminal_dashboard_data()
        self.assertIsNotNone(data)
        self.assertIn("trading", data)
        self.assertIn("defcon", data)
        self.assertIn("fleet_vitals", data)
        self.assertIn("system_vitals", data)


if __name__ == "__main__":
    unittest.main()
