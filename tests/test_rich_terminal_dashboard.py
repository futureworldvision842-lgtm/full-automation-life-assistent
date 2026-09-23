"""
tests/test_rich_terminal_dashboard.py
=============================================================================
Comprehensive unit and integration test suite for Worker M1:
  - Rich Terminal UI & Multi-Panel Dashboard (ui/rich_terminal_dashboard.py)
  - Platform Runtime Interface Contracts (get_terminal_dashboard_data)
  - Dual-Mode CLI Console & Bilingual Roman Urdu / English NLP (terminal.py)
  - CLI Visualizer Integration in main.py
=============================================================================
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ui.rich_terminal_dashboard import (
    RichTerminalDashboard,
    get_terminal_dashboard_data,
    render_terminal_dashboard,
)
from platform_runtime import get_terminal_dashboard_data as runtime_get_dashboard_data


class TestRichTerminalDashboardDataContract(unittest.TestCase):
    """Verifies that get_terminal_dashboard_data conforms to PROJECT.md interface specifications."""

    def test_top_level_keys(self):
        data = get_terminal_dashboard_data()
        expected_keys = {"trading", "defcon", "fleet_vitals", "system_vitals"}
        self.assertTrue(expected_keys.issubset(data.keys()), f"Missing keys in telemetry data: {expected_keys - data.keys()}")

    def test_trading_data_schema(self):
        data = get_terminal_dashboard_data()
        trading = data["trading"]
        self.assertIn("login", trading)
        self.assertIn("server", trading)
        self.assertIn("balance", trading)
        self.assertIn("equity", trading)
        self.assertIn("open_positions", trading)
        self.assertIn("floating_pnl", trading)
        self.assertIn("win_rate", trading)

        self.assertIsInstance(trading["login"], int)
        self.assertIsInstance(trading["server"], str)
        self.assertIsInstance(trading["balance"], (int, float))
        self.assertIsInstance(trading["equity"], (int, float))
        self.assertIsInstance(trading["open_positions"], list)
        self.assertIsInstance(trading["floating_pnl"], (int, float))
        self.assertIsInstance(trading["win_rate"], (int, float))

    def test_defcon_radar_schema(self):
        data = get_terminal_dashboard_data()
        defcon = data["defcon"]
        self.assertIn("threat_level", defcon)
        self.assertIn("maritime_chokepoints", defcon)
        self.assertIn("gold_multiplier", defcon)
        self.assertIn("sentiment", defcon)

        self.assertIn("DEFCON", defcon["threat_level"])
        self.assertEqual(len(defcon["maritime_chokepoints"]), 5, "Must monitor 5 strategic maritime chokepoints")
        self.assertGreaterEqual(defcon["gold_multiplier"], 1.0)
        self.assertIsInstance(defcon["sentiment"], str)

        cp_names = [cp["name"] for cp in defcon["maritime_chokepoints"]]
        self.assertTrue(any("Hormuz" in name for name in cp_names))
        self.assertTrue(any("Bab el-Mandeb" in name or "Mandeb" in name for name in cp_names))
        self.assertTrue(any("Suez" in name for name in cp_names))
        self.assertTrue(any("Malacca" in name for name in cp_names))
        self.assertTrue(any("Taiwan" in name for name in cp_names))

    def test_fleet_vitals_schema(self):
        data = get_terminal_dashboard_data()
        fleet = data["fleet_vitals"]
        required_nodes = ["dashboard", "mobile", "mq3", "odysseus", "ollama", "world_monitor", "discord_bot"]
        for node in required_nodes:
            self.assertIn(node, fleet, f"Node {node} missing from fleet vitals")
            self.assertIsInstance(fleet[node], bool)

    def test_system_vitals_schema(self):
        data = get_terminal_dashboard_data()
        vitals = data["system_vitals"]
        self.assertIn("cpu_pct", vitals)
        self.assertIn("ram_pct", vitals)
        self.assertIn("gpu_pct", vitals)
        self.assertIn("network_latency_ms", vitals)

        self.assertIsInstance(vitals["cpu_pct"], float)
        self.assertIsInstance(vitals["ram_pct"], float)
        self.assertIsInstance(vitals["gpu_pct"], float)
        self.assertIsInstance(vitals["network_latency_ms"], float)
        self.assertGreaterEqual(vitals["cpu_pct"], 0.0)
        self.assertGreaterEqual(vitals["ram_pct"], 0.0)

    def test_platform_runtime_contract_parity(self):
        data1 = get_terminal_dashboard_data()
        data2 = runtime_get_dashboard_data()
        self.assertEqual(set(data1.keys()), set(data2.keys()))


class TestRichTerminalDashboardUI(unittest.TestCase):
    """Verifies layout generation and rendering."""

    def setUp(self):
        self.dashboard = RichTerminalDashboard()

    def test_build_layout_structure(self):
        layout = self.dashboard.build_layout()
        self.assertIsNotNone(layout)
        # Check layout partitions
        for name in ("header", "trading", "defcon", "fleet", "system", "activity", "footer"):
            child = layout[name]
            self.assertIsNotNone(child)
            self.assertEqual(child.name, name)

    def test_panels_creation(self):
        data = get_terminal_dashboard_data()
        header = self.dashboard.create_header(data)
        trading = self.dashboard.create_trading_panel(data)
        defcon = self.dashboard.create_defcon_panel(data)
        fleet = self.dashboard.create_fleet_panel(data)
        system = self.dashboard.create_system_vitals_panel(data)
        activity = self.dashboard.create_activity_log_panel()
        footer = self.dashboard.create_footer()

        self.assertIsNotNone(header)
        self.assertIsNotNone(trading)
        self.assertIsNotNone(defcon)
        self.assertIsNotNone(fleet)
        self.assertIsNotNone(system)
        self.assertIsNotNone(activity)
        self.assertIsNotNone(footer)

    def test_render_static(self):
        # Must execute without throwing exceptions
        self.dashboard.render_static()
        render_terminal_dashboard()


class TestBilingualDualModeCLI(unittest.TestCase):
    """Verifies English and Roman Urdu command processing and execution."""

    def setUp(self):
        self.dashboard = RichTerminalDashboard()

    def test_roman_urdu_greetings(self):
        rep = self.dashboard.execute_command("kya haal hai")
        self.assertTrue(any(w in rep.lower() for w in ("alhamdulillah", "operational", "healthy", "ready")))

    def test_roman_urdu_gold_query(self):
        rep = self.dashboard.execute_command("aaj ka gold rate batao")
        self.assertIsInstance(rep, str)
        self.assertGreater(len(rep), 5)

    def test_roman_urdu_positions_query(self):
        rep = self.dashboard.execute_command("open trades dikhao")
        self.assertIsInstance(rep, str)
        self.assertTrue(len(rep) > 0)

    def test_roman_urdu_system_status(self):
        rep = self.dashboard.execute_command("system vitals check karo")
        self.assertIn("CPU:", rep)
        self.assertIn("RAM:", rep)

    def test_english_defcon_query(self):
        rep = self.dashboard.execute_command("defcon")
        self.assertIsInstance(rep, str)
        self.assertTrue(len(rep) > 0)

    def test_english_chokepoints_query(self):
        rep = self.dashboard.execute_command("chokepoints")
        self.assertIsInstance(rep, str)
        self.assertTrue(len(rep) > 0)

    def test_english_trading_status(self):
        rep = self.dashboard.execute_command("trade status")
        self.assertIsInstance(rep, str)
        self.assertTrue(len(rep) > 0)

    def test_exit_and_clear_commands(self):
        rep_exit = self.dashboard.execute_command("exit")
        self.assertIn("standing down", rep_exit.lower())

        rep_clear = self.dashboard.execute_command("clear")
        self.assertIn("cleared", rep_clear.lower())

    def test_empty_command(self):
        rep = self.dashboard.execute_command("   ")
        self.assertIn("no command was received", rep.lower())


class TestTerminalAndMainIntegration(unittest.TestCase):
    """Verifies integration with terminal.py and main.py."""

    def test_terminal_powershell_function(self):
        from terminal import run_powershell
        res = run_powershell("echo TEST_OUTPUT_OK")
        self.assertIn("TEST_OUTPUT_OK", res)

    def test_main_cli_visualizer_detection(self):
        import main
        self.assertTrue(hasattr(main, "main"))


if __name__ == "__main__":
    unittest.main()
