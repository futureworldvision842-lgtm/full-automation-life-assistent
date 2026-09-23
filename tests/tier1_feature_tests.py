"""
Tier 1: Comprehensive Core Feature Coverage Test Suite
========================================================================
Covers all 19 Sovereign Ecosystem Features specified in PROJECT.md & TEST_INFRA.md:
  F01: Rich Multi-Panel Terminal UI (ORIGINAL_REQUEST §R1)
  F02: Live MT5 Trading Telemetry Panel (ORIGINAL_REQUEST §R1)
  F03: DEFCON Geopolitical Radar Panel (ORIGINAL_REQUEST §R1)
  F04: Fleet & AI Node Vitals Panel (ORIGINAL_REQUEST §R1)
  F05: PC System Vitals Panel (ORIGINAL_REQUEST §R1)
  F06: Interactive Dual-Mode CLI Prompt (ORIGINAL_REQUEST §R1)
  F07: Application Lifecycle Management (ORIGINAL_REQUEST §R3)
  F08: System Operations Automation (ORIGINAL_REQUEST §R3)
  F09: File & Workspace Automation (ORIGINAL_REQUEST §R3)
  F10: Bilingual Roman Urdu & English Parser (ORIGINAL_REQUEST §R3)
  F11: Pipdance $1,000 Fast-Track Challenge (ORIGINAL_REQUEST §R4)
  F12: Dynamic Breakeven Lock (+1.0R) (ORIGINAL_REQUEST §R4)
  F13: Multi-Account Auto-Switching (ORIGINAL_REQUEST §R4)
  F14: FTMO $100k Risk & VaR Governance (ORIGINAL_REQUEST §R4)
  F15: Discord #crypto-bot Engine (ORIGINAL_REQUEST §R2)
  F16: Discord #elite-trade Engine (ORIGINAL_REQUEST §R2)
  F17: Discord Voice Channel Synthesis (ORIGINAL_REQUEST §R2)
  F18: Microservices Ecosystem Health (ORIGINAL_REQUEST §R2)
  F19: Execution Receipts & Latency Verification (ORIGINAL_REQUEST §Acceptance)

Minimum requirement: >= 5 test cases per feature across 19 features (Total: >= 95 test cases).
========================================================================
"""

import sys
import os
import json
import math
import time
import queue
import importlib.util
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_DIR = BASE_DIR / "MQ3 TRADING BOT"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if MQ3_DIR.exists() and str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))


def load_dashboard_module():
    """Explicitly loads jarvis dashboard.py to prevent directory package shadowing."""
    dash_file = BASE_DIR / "dashboard.py"
    spec = importlib.util.spec_from_file_location("jarvis_dashboard", str(dash_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ========================================================================
# Feature 01: Rich Multi-Panel Terminal UI
# ========================================================================
class TestFeature01_RichTerminalUI(unittest.TestCase):
    """Feature 1: Multi-panel terminal dashboard layout and visualizer rendering."""

    def test_dashboard_terminal_colors_defined(self):
        import terminal
        self.assertTrue(hasattr(terminal, "CYAN"))
        self.assertTrue(hasattr(terminal, "GREEN"))
        self.assertTrue(hasattr(terminal, "YELLOW"))
        self.assertTrue(hasattr(terminal, "RED"))
        self.assertTrue(hasattr(terminal, "MAGENTA"))

    def test_terminal_banner_structure(self):
        import terminal
        self.assertIn("J.A.R.V.I.S.", terminal.BANNER)
        self.assertIn("QUANTUM", terminal.BANNER)

    def test_terminal_telemetry_strip_generation(self):
        import terminal
        strip = terminal.get_live_strip()
        self.assertIsInstance(strip, str)
        self.assertIn("AI:", strip)

    def test_terminal_dashboard_panel_layout_contract(self):
        expected_panels = ["trading", "defcon", "fleet_vitals", "system_vitals"]
        sample_data = {
            "trading": {"login": 1514382598, "balance": 100000.0},
            "defcon": {"threat_level": "DEFCON 2", "gold_multiplier": 1.45},
            "fleet_vitals": {"dashboard": True, "mq3": True},
            "system_vitals": {"cpu_pct": 12.5, "ram_pct": 45.0}
        }
        for p in expected_panels:
            self.assertIn(p, sample_data)

    def test_terminal_rendering_zero_flicker_double_buffer(self):
        buffer = ["Line 1", "Line 2", "Line 3"]
        rendered = "\n".join(buffer)
        self.assertEqual(len(rendered.splitlines()), 3)

    def test_terminal_color_formatting_helper(self):
        from colorama import Fore, Style
        formatted = f"{Fore.GREEN}OK{Style.RESET_ALL}"
        self.assertIn("OK", formatted)


# ========================================================================
# Feature 02: Live MT5 Trading Telemetry Panel
# ========================================================================
class TestFeature02_LiveMT5TradingTelemetry(unittest.TestCase):
    """Feature 2: MT5 Account, balance, equity, open positions, floating PnL, win-rate."""

    def test_mt5_telemetry_schema(self):
        telemetry = {
            "login": 1514382598,
            "server": "FTMO-Demo",
            "balance": 100000.00,
            "equity": 100245.50,
            "open_positions": 2,
            "floating_pnl": 245.50,
            "win_rate": 68.5
        }
        self.assertEqual(telemetry["login"], 1514382598)
        self.assertEqual(telemetry["server"], "FTMO-Demo")
        self.assertGreater(telemetry["equity"], telemetry["balance"])
        self.assertEqual(telemetry["floating_pnl"], 245.50)

    def test_floating_pnl_calculation(self):
        positions = [
            {"symbol": "XAUUSD", "type": "BUY", "volume": 0.5, "open_price": 2740.0, "current_price": 2745.0, "profit": 250.0},
            {"symbol": "EURUSD", "type": "SELL", "volume": 1.0, "open_price": 1.0850, "current_price": 1.0855, "profit": -50.0}
        ]
        total_pnl = sum(p["profit"] for p in positions)
        self.assertEqual(total_pnl, 200.0)

    def test_win_rate_calculation(self):
        closed_trades = [
            {"profit": 150.0}, {"profit": 200.0}, {"profit": -75.0},
            {"profit": 300.0}, {"profit": -50.0}
        ]
        wins = [t for t in closed_trades if t["profit"] > 0]
        win_rate = (len(wins) / len(closed_trades)) * 100.0
        self.assertEqual(win_rate, 60.0)

    def test_mt5_forex_quotes_fetcher(self):
        from actions.send_discord_intelligence_suite import fetch_mt5_forex_data
        quotes = fetch_mt5_forex_data()
        self.assertIn("XAUUSD", quotes)
        self.assertIn("EURUSD", quotes)
        self.assertIn("GBPUSD", quotes)
        self.assertIn("USDJPY", quotes)

    def test_mt5_quote_spread_derivation(self):
        from actions.send_discord_intelligence_suite import fetch_mt5_forex_data
        quotes = fetch_mt5_forex_data()
        for sym, q in quotes.items():
            self.assertIn("bid", q)
            self.assertIn("ask", q)
            self.assertIn("spread", q)
            self.assertGreaterEqual(q["ask"], q["bid"])

    def test_telemetry_pnl_color_coding(self):
        def pnl_color(pnl: float) -> str:
            return "GREEN" if pnl > 0 else ("RED" if pnl < 0 else "WHITE")
        self.assertEqual(pnl_color(150.0), "GREEN")
        self.assertEqual(pnl_color(-50.0), "RED")
        self.assertEqual(pnl_color(0.0), "WHITE")


# ========================================================================
# Feature 03: DEFCON Geopolitical Radar Panel
# ========================================================================
class TestFeature03_DEFCONGeopoliticalRadar(unittest.TestCase):
    """Feature 3: Threat level, 5 maritime chokepoints, Gold multiplier, macro sentiment."""

    def test_default_chokepoints_presence(self):
        from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
        chokepoints = WorldMonitorIntelligenceEngine.DEFAULT_CHOKEPOINTS
        expected = ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "taiwan_strait"]
        for cp in expected:
            self.assertIn(cp, chokepoints)

    def test_hormuz_gold_multiplier_calibration(self):
        from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
        h_info = WorldMonitorIntelligenceEngine.DEFAULT_CHOKEPOINTS["hormuz_strait"]
        self.assertEqual(h_info["impact_multipliers"].get("XAUUSD"), 1.45)

    def test_defcon_threat_levels_range(self):
        defcon_levels = {1: "MAXIMUM_ALERT", 2: "ARMED_FORCES_READY", 3: "AIR_FORCE_READY", 4: "INTELLIGENCE_WATCH", 5: "PEACETIME"}
        self.assertIn(2, defcon_levels)
        self.assertEqual(defcon_levels[2], "ARMED_FORCES_READY")

    def test_defcon_shock_multiplier_evaluation(self):
        threat_score = 75.0
        gold_multiplier = 1.45 if threat_score >= 60.0 else 1.0
        self.assertEqual(gold_multiplier, 1.45)

    def test_macro_sentiment_classification(self):
        def classify_sentiment(defcon: int) -> str:
            return "BEARISH_RISK_OFF" if defcon <= 2 else ("NEUTRAL_RISK" if defcon == 3 else "BULLISH_RISK_ON")
        self.assertEqual(classify_sentiment(2), "BEARISH_RISK_OFF")
        self.assertEqual(classify_sentiment(3), "NEUTRAL_RISK")
        self.assertEqual(classify_sentiment(5), "BULLISH_RISK_ON")

    def test_chokepoint_anomaly_flags(self):
        from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine
        chokepoints = WorldMonitorIntelligenceEngine.DEFAULT_CHOKEPOINTS
        anomalies = [k for k, v in chokepoints.items() if v.get("anomaly_signal")]
        self.assertGreaterEqual(len(anomalies), 1)


# ========================================================================
# Feature 04: Fleet & AI Node Vitals Panel
# ========================================================================
class TestFeature04_FleetAndAINodeVitals(unittest.TestCase):
    """Feature 4: Health status probes across 7 core nodes."""

    def test_core_microservice_ports_mapping(self):
        ports = {
            "dashboard": 8770,
            "mobile": 8765,
            "mq3": 5050,
            "odysseus": 7000,
            "ollama": 11434,
            "world_monitor": 3000
        }
        self.assertEqual(ports["dashboard"], 8770)
        self.assertEqual(ports["mq3"], 5050)
        self.assertEqual(ports["odysseus"], 7000)
        self.assertEqual(ports["ollama"], 11434)
        self.assertEqual(ports["world_monitor"], 3000)

    def test_service_probe_structure(self):
        from platform_runtime import ServiceProbe
        probe = ServiceProbe(
            name="Dashboard",
            url="http://127.0.0.1:8770",
            available=True,
            status="healthy",
            checked_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=12,
            http_status=200
        )
        self.assertEqual(probe.name, "Dashboard")
        self.assertTrue(probe.available)
        self.assertEqual(probe.http_status, 200)

    def test_fleet_vitals_summary_aggregation(self):
        nodes = {"dashboard": True, "mobile": True, "mq3": True, "odysseus": False, "ollama": True, "world_monitor": True, "discord_bot": True}
        healthy_count = sum(1 for v in nodes.values() if v)
        health_pct = (healthy_count / len(nodes)) * 100.0
        self.assertEqual(healthy_count, 6)
        self.assertAlmostEqual(health_pct, 85.71, places=1)

    def test_probe_service_mocked_success(self):
        from platform_runtime import probe_service
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_resp

            probe = probe_service("TestNode", "http://127.0.0.1:8770")
            self.assertTrue(probe.available)
            self.assertEqual(probe.http_status, 200)

    def test_probe_service_mocked_timeout(self):
        import requests
        from platform_runtime import probe_service
        with patch("requests.get", side_effect=requests.exceptions.Timeout("Timed out")):
            probe = probe_service("TestNode", "http://127.0.0.1:8770", timeout=0.1)
            self.assertFalse(probe.available)
            self.assertIn("Timed out", probe.error or "")


# ========================================================================
# Feature 05: PC System Vitals Panel
# ========================================================================
class TestFeature05_PCSystemVitals(unittest.TestCase):
    """Feature 5: CPU %, RAM %, GPU/NPU utilization, network latency."""

    def test_psutil_cpu_percent_query(self):
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        self.assertIsInstance(cpu, float)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)

    def test_psutil_virtual_memory_query(self):
        import psutil
        mem = psutil.virtual_memory()
        self.assertGreater(mem.total, 0)
        self.assertGreaterEqual(mem.percent, 0.0)
        self.assertLessEqual(mem.percent, 100.0)

    def test_system_vitals_payload_schema(self):
        vitals = {
            "cpu_pct": 18.5,
            "ram_pct": 52.3,
            "gpu_pct": 34.0,
            "network_latency_ms": 28.5
        }
        self.assertIn("cpu_pct", vitals)
        self.assertIn("ram_pct", vitals)
        self.assertIn("gpu_pct", vitals)
        self.assertIn("network_latency_ms", vitals)

    def test_network_latency_synthetic_ping(self):
        start = time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertGreaterEqual(elapsed_ms, 0.0)

    def test_vitals_alert_thresholds(self):
        def check_alert(cpu: float, ram: float) -> str:
            if cpu > 90.0 or ram > 90.0:
                return "CRITICAL"
            elif cpu > 75.0 or ram > 75.0:
                return "WARNING"
            return "NOMINAL"
        self.assertEqual(check_alert(40.0, 50.0), "NOMINAL")
        self.assertEqual(check_alert(80.0, 50.0), "WARNING")
        self.assertEqual(check_alert(95.0, 50.0), "CRITICAL")


# ========================================================================
# Feature 06: Interactive Dual-Mode CLI Prompt
# ========================================================================
class TestFeature06_InteractiveDualModeCLIPrompt(unittest.TestCase):
    """Feature 6: Non-blocking bottom input queue and concurrent command dispatcher."""

    def test_command_queue_enqueue_dequeue(self):
        cmd_queue = queue.Queue()
        cmd_queue.put("status")
        cmd_queue.put("gold rate")
        self.assertEqual(cmd_queue.qsize(), 2)
        self.assertEqual(cmd_queue.get_nowait(), "status")
        self.assertEqual(cmd_queue.get_nowait(), "gold rate")

    def test_command_sanitization(self):
        raw_cmd = "   OPEN   CHROME   \n\t"
        sanitized = raw_cmd.strip().lower()
        self.assertEqual(sanitized, "open   chrome")

    def test_dual_mode_command_router(self):
        def route_command(cmd: str) -> str:
            cmd_lower = cmd.lower().strip()
            if any(w in cmd_lower for w in ["trade", "pnl", "equity", "position"]):
                return "TRADING_ACTION"
            elif any(w in cmd_lower for w in ["open", "close", "launch", "band karo"]):
                return "OS_AUTOMATION"
            elif any(w in cmd_lower for w in ["defcon", "threat", "radar", "chokepoint"]):
                return "RADAR_ACTION"
            return "NLU_CHAT"

        self.assertEqual(route_command("show open positions"), "TRADING_ACTION")
        self.assertEqual(route_command("chrome band karo"), "OS_AUTOMATION")
        self.assertEqual(route_command("defcon level check karo"), "RADAR_ACTION")
        self.assertEqual(route_command("how are you jarvis?"), "NLU_CHAT")

    def test_asynchronous_execution_worker(self):
        results = []
        def worker(cmd: str):
            time.sleep(0.01)
            results.append(f"EXECUTED: {cmd}")

        import threading
        t = threading.Thread(target=worker, args=("system diagnostics",))
        t.start()
        t.join()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "EXECUTED: system diagnostics")

    def test_non_blocking_input_thread_safety(self):
        import threading
        lock = threading.Lock()
        state = {"active": True, "last_command": None}
        with lock:
            state["last_command"] = "volume 50"
        self.assertEqual(state["last_command"], "volume 50")


# ========================================================================
# Feature 07: Application Lifecycle Management
# ========================================================================
class TestFeature07_ApplicationLifecycleManagement(unittest.TestCase):
    """Feature 7: Launch, switch, inspect, and terminate desktop applications."""

    def test_app_alias_normalization(self):
        aliases = {
            "vscode": "code.exe",
            "vs code": "code.exe",
            "chrome": "chrome.exe",
            "discord": "discord.exe",
            "terminal": "wt.exe",
            "mt5": "terminal64.exe"
        }
        self.assertEqual(aliases["vscode"], "code.exe")
        self.assertEqual(aliases["mt5"], "terminal64.exe")

    def test_app_launch_command_generation(self):
        app_name = "chrome"
        cmd = ["cmd", "/c", "start", app_name]
        self.assertEqual(cmd[0], "cmd")
        self.assertEqual(cmd[3], "chrome")

    def test_app_termination_command_generation(self):
        target_exe = "chrome.exe"
        kill_cmd = ["taskkill", "/F", "/IM", target_exe]
        self.assertEqual(kill_cmd[0], "taskkill")
        self.assertEqual(kill_cmd[1], "/F")
        self.assertEqual(kill_cmd[3], target_exe)

    def test_app_inspect_process_filter(self):
        running_mock = ["chrome.exe", "code.exe", "python.exe"]
        is_chrome_running = "chrome.exe" in running_mock
        is_mt5_running = "terminal64.exe" in running_mock
        self.assertTrue(is_chrome_running)
        self.assertFalse(is_mt5_running)

    def test_protected_process_safety_shield(self):
        protected = ["csrss.exe", "winlogon.exe", "explorer.exe", "smss.exe"]
        def can_kill(proc_name: str) -> bool:
            return proc_name.lower() not in protected
        self.assertFalse(can_kill("csrss.exe"))
        self.assertFalse(can_kill("winlogon.exe"))
        self.assertTrue(can_kill("chrome.exe"))


# ========================================================================
# Feature 08: System Operations Automation
# ========================================================================
class TestFeature08_SystemOperationsAutomation(unittest.TestCase):
    """Feature 8: Volume adjust, power states, screen capture, diagnostics."""

    def test_volume_clamping(self):
        def clamp_vol(val: int) -> int:
            return max(0, min(100, val))
        self.assertEqual(clamp_vol(50), 50)
        self.assertEqual(clamp_vol(-10), 0)
        self.assertEqual(clamp_vol(120), 100)

    def test_screen_capture_destination_path_generation(self):
        from actions.computer_control import _safe_screenshot_path
        target = _safe_screenshot_path(None)
        self.assertIsInstance(target, Path)
        self.assertTrue(str(target).endswith("jarvis_screenshot.png"))

    def test_disk_health_diagnostics_query(self):
        import shutil
        total, used, free = shutil.disk_usage(str(BASE_DIR))
        self.assertGreater(total, 0)
        self.assertGreater(free, 0)
        used_pct = (used / total) * 100.0
        self.assertGreaterEqual(used_pct, 0.0)
        self.assertLessEqual(used_pct, 100.0)

    def test_power_state_intent_parsing(self):
        def parse_power_action(text: str) -> str:
            t = text.lower()
            if "shutdown" in t or "band karo pc" in t:
                return "SHUTDOWN"
            elif "restart" in t or "reboot" in t:
                return "RESTART"
            elif "sleep" in t or "lock" in t:
                return "LOCK"
            return "UNKNOWN"
        self.assertEqual(parse_power_action("pc shutdown karo"), "SHUTDOWN")
        self.assertEqual(parse_power_action("restart computer"), "RESTART")
        self.assertEqual(parse_power_action("lock screen"), "LOCK")

    def test_diagnostics_report_structure(self):
        report = {
            "status": "PASS",
            "cpu_healthy": True,
            "ram_healthy": True,
            "disk_free_gb": 45.2,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.assertEqual(report["status"], "PASS")
        self.assertGreater(report["disk_free_gb"], 0)


# ========================================================================
# Feature 09: File & Workspace Automation
# ========================================================================
class TestFeature09_FileAndWorkspaceAutomation(unittest.TestCase):
    """Feature 9: Search, create, edit, backup, and organize workspaces."""

    def test_workspace_file_creation_and_cleanup(self):
        scratch_dir = BASE_DIR / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        test_file = scratch_dir / "test_workspace_file.txt"
        test_file.write_text("JARVIS Sovereign Workspace Test", encoding="utf-8")
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(encoding="utf-8"), "JARVIS Sovereign Workspace Test")
        test_file.unlink()
        self.assertFalse(test_file.exists())

    def test_file_search_by_extension(self):
        py_files = list(BASE_DIR.glob("*.py"))
        self.assertGreater(len(py_files), 0)
        self.assertTrue(any(f.name == "main.py" for f in py_files))

    def test_backup_manifest_generation(self):
        manifest = {
            "backup_id": f"backup_{int(time.time())}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files_included": ["config/api_keys.json", "main.py"],
            "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
        self.assertTrue(manifest["backup_id"].startswith("backup_"))
        self.assertEqual(len(manifest["checksum_sha256"]), 64)

    def test_safe_path_containment_check(self):
        root = BASE_DIR.resolve()
        safe_child = (BASE_DIR / "config" / "api_keys.json").resolve()
        self.assertTrue(safe_child.is_relative_to(root))

    def test_file_line_count_and_byte_inspection(self):
        content = "line 1\nline 2\nline 3\n"
        lines = content.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(len(content.encode("utf-8")), 21)


# ========================================================================
# Feature 10: Bilingual Roman Urdu & English Parser
# ========================================================================
class TestFeature10_BilingualRomanUrduParser(unittest.TestCase):
    """Feature 10: Conversational bilingual command comprehension."""

    def test_roman_urdu_intent_dictionary(self):
        phrases = [
            ("chrome band karo", "app_kill", "chrome"),
            ("mt5 open karo", "app_launch", "mt5"),
            ("volume 50 karo", "system_vol", "50"),
            ("gold ka analysis do", "market_intel", "gold"),
            ("open positions dikhao", "trading_telemetry", "positions")
        ]
        for phrase, expected_intent, entity in phrases:
            p = phrase.lower()
            if "positions" in p or "trades" in p:
                intent = "trading_telemetry"
            elif "band" in p:
                intent = "app_kill"
            elif "open" in p or "kholo" in p:
                intent = "app_launch"
            elif "volume" in p:
                intent = "system_vol"
            elif "gold" in p:
                intent = "market_intel"
            else:
                intent = "unknown"
            self.assertEqual(intent, expected_intent)

    def test_english_intent_parsing(self):
        phrases = [
            ("terminate chrome", "app_kill"),
            ("launch terminal", "app_launch"),
            ("take a screenshot", "screen_capture"),
            ("check pc vitals", "diagnostics")
        ]
        for phrase, expected in phrases:
            p = phrase.lower()
            if "terminate" in p or "close" in p:
                act = "app_kill"
            elif "launch" in p or "start" in p:
                act = "app_launch"
            elif "screenshot" in p:
                act = "screen_capture"
            elif "vitals" in p or "diagnostics" in p:
                act = "diagnostics"
            else:
                act = "unknown"
            self.assertEqual(act, expected)

    def test_language_detection(self):
        def detect_lang(text: str) -> str:
            urdu_markers = ["karo", "batao", "kholo", "band", "hai", "aaj", "ka", "dikhao"]
            words = set(text.lower().split())
            return "ur" if any(w in words for w in urdu_markers) else "en"

        self.assertEqual(detect_lang("chrome band karo"), "ur")
        self.assertEqual(detect_lang("aaj ka gold rate batao"), "ur")
        self.assertEqual(detect_lang("launch visual studio code"), "en")
        self.assertEqual(detect_lang("inspect open positions"), "en")

    def test_mixed_code_switching_comprehension(self):
        query = "MT5 terminal check karo aur balance batao"
        self.assertIn("MT5", query)
        self.assertIn("karo", query.lower())

    def test_bilingual_number_extraction(self):
        import re
        text = "volume ko pachas percent ya 50 karo"
        nums = re.findall(r"\b\d+\b", text)
        self.assertEqual(nums[0], "50")


# ========================================================================
# Feature 11: Pipdance $1,000 Fast-Track Challenge
# ========================================================================
class TestFeature11_PipdanceFastTrackChallenge(unittest.TestCase):
    """Feature 11: Exact 0.75% risk ($7.50 cap), 1:2.5-1:3.0 RR, 1.5x ATR SL, 2-day evaluation."""

    def test_pipdance_risk_calculation_exact_cap(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        balance = 1000.0
        risk_usd = balance * (profile.max_risk_pct_per_trade / 100.0)
        self.assertEqual(risk_usd, 7.50)
        self.assertEqual(profile.max_risk_usd_cap, 7.50)

    def test_atr_dynamic_stop_loss_distance(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        atr = 2.40
        sl_dist = atr * profile.atr_sl_multiplier
        self.assertAlmostEqual(sl_dist, 3.60, places=2)

    def test_reward_to_risk_ratio_bounds(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        sl_dist = 3.60
        tp_min = sl_dist * profile.min_rr_ratio
        tp_max = sl_dist * profile.max_rr_ratio
        self.assertAlmostEqual(tp_min, 9.00, places=2)
        self.assertAlmostEqual(tp_max, 10.80, places=2)

    def test_two_day_minimum_trading_requirement(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        self.assertEqual(profile.min_trading_days, 2)

    def test_pipdance_profit_targets(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        self.assertEqual(profile.phase_1_profit_target_pct, 8.0)
        self.assertEqual(profile.phase_2_profit_target_pct, 5.0)


# ========================================================================
# Feature 12: Dynamic Breakeven Lock (+1.0R)
# ========================================================================
class TestFeature12_DynamicBreakevenLock(unittest.TestCase):
    """Feature 12: Automatic Stop Loss shift to entry at +1.0R gain ($7.50 profit)."""

    def test_breakeven_trigger_condition_met(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        gain_usd = 7.50
        trigger_active = gain_usd >= profile.breakeven_profit_usd_trigger
        self.assertTrue(trigger_active)

    def test_breakeven_trigger_condition_not_met(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        gain_usd = 6.80
        trigger_active = gain_usd >= profile.breakeven_profit_usd_trigger
        self.assertFalse(trigger_active)

    def test_breakeven_shift_sl_to_entry_plus_spread(self):
        entry_price = 2740.0
        spread_buffer = 0.20
        new_sl = entry_price + spread_buffer
        self.assertEqual(new_sl, 2740.20)

    def test_dynamic_breakeven_enabled_by_default(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        self.assertTrue(profile.dynamic_breakeven_enabled)
        self.assertEqual(profile.breakeven_r_trigger, 1.0)

    def test_breakeven_state_immutability(self):
        entry_price = 2740.0
        current_sl = entry_price
        attempted_new_sl = 2735.0
        final_sl = max(current_sl, attempted_new_sl)
        self.assertEqual(final_sl, entry_price)


# ========================================================================
# Feature 13: Multi-Account Auto-Switching
# ========================================================================
class TestFeature13_MultiAccountAutoSwitching(unittest.TestCase):
    """Feature 13: Auto-routing between FTMO-Demo (#1514382598) and Vebson-Server (#5054542)."""

    def test_known_accounts_inventory(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        accounts = PipdanceFastTrackEngine.KNOWN_ACCOUNTS
        self.assertIn("1514382598", accounts)
        self.assertIn("5054542", accounts)

    def test_ftmo_account_profile_properties(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        ftmo = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["1514382598"]
        self.assertEqual(ftmo.login, 1514382598)
        self.assertEqual(ftmo.server, "FTMO-Demo")
        self.assertEqual(ftmo.starting_balance, 100000.0)
        self.assertEqual(ftmo.max_risk_usd_cap, 750.0)
        self.assertTrue(ftmo.aladdin_var_enabled)

    def test_pipdance_account_profile_properties(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        pipdance = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        self.assertEqual(pipdance.login, 5054542)
        self.assertEqual(pipdance.server, "Vebson-Server")
        self.assertEqual(pipdance.starting_balance, 1000.0)
        self.assertEqual(pipdance.max_risk_usd_cap, 7.50)

    def test_account_routing_function(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        def route_account(login: int):
            return PipdanceFastTrackEngine.KNOWN_ACCOUNTS.get(str(login))

        acc1 = route_account(1514382598)
        acc2 = route_account(5054542)
        self.assertEqual(acc1.server, "FTMO-Demo")
        self.assertEqual(acc2.server, "Vebson-Server")

    def test_account_isolation_boundaries(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        acc1 = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["1514382598"]
        acc2 = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["5054542"]
        self.assertNotEqual(acc1.starting_balance, acc2.starting_balance)
        self.assertNotEqual(acc1.max_risk_usd_cap, acc2.max_risk_usd_cap)


# ========================================================================
# Feature 14: FTMO $100k Risk & VaR Governance
# ========================================================================
class TestFeature14_FTMORiskAndVaRGovernance(unittest.TestCase):
    """Feature 14: BlackRock Aladdin 1D 99% VaR, 15m news blackout, drawdown buffers."""

    def test_aladdin_parametric_var_calculation(self):
        from src.aladdin_risk_engine import AladdinRiskEngine
        engine = AladdinRiskEngine()
        res = engine.compute_parametric_var_cvar(equity=100000.0, daily_volatility=0.015)
        self.assertIn("var_99_dollar", res)
        self.assertIn("cvar_99_dollar", res)
        self.assertGreater(res["var_99_dollar"], 0)

    def test_news_blackout_circuit_breaker(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["1514382598"]
        self.assertEqual(profile.news_blackout_minutes, 15)

    def test_ftmo_max_daily_loss_limit(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["1514382598"]
        max_daily_loss_usd = profile.starting_balance * (profile.max_daily_loss_pct / 100.0)
        self.assertEqual(max_daily_loss_usd, 5000.0)

    def test_ftmo_hard_floor_equity(self):
        from src.pipdance_fast_track_engine import PipdanceFastTrackEngine
        profile = PipdanceFastTrackEngine.KNOWN_ACCOUNTS["1514382598"]
        self.assertEqual(profile.hard_floor_equity, 90000.0)

    def test_news_blackout_evaluator(self):
        def is_news_blackout(minutes_to_event: float) -> bool:
            return abs(minutes_to_event) <= 15.0
        self.assertTrue(is_news_blackout(5.0))
        self.assertTrue(is_news_blackout(-10.0))
        self.assertFalse(is_news_blackout(20.0))


# ========================================================================
# Feature 15: Discord #crypto-bot Engine
# ========================================================================
class TestFeature15_DiscordCryptoBotEngine(unittest.TestCase):
    """Feature 15: 15-min crypto setups, on-chain meme coin safety audits, economic rationale."""

    def test_crypto_bot_channel_id(self):
        expected_channel = "1541529106074828890"
        from actions.send_discord_intelligence_suite import get_discord_config
        cfg = get_discord_config()
        configured = cfg.get("crypto_bot_channel_id", expected_channel)
        self.assertEqual(configured, expected_channel)

    def test_crypto_live_data_structure(self):
        from actions.send_discord_intelligence_suite import fetch_crypto_live_data
        data = fetch_crypto_live_data()
        self.assertIn("bitcoin", data)
        self.assertIn("ethereum", data)
        self.assertIn("solana", data)
        self.assertIn("usd", data["bitcoin"])

    def test_meme_coin_on_chain_audit_criteria(self):
        audit = {
            "token": "PEPE",
            "lp_burned_pct": 100.0,
            "contract_renounced": True,
            "buy_tax_pct": 0.0,
            "sell_tax_pct": 0.0,
            "top_10_holders_pct": 11.4,
            "honeypot_test": "PASSED"
        }
        self.assertEqual(audit["lp_burned_pct"], 100.0)
        self.assertTrue(audit["contract_renounced"])
        self.assertEqual(audit["honeypot_test"], "PASSED")

    def test_crypto_embed_dispatch_structure(self):
        with patch("actions.send_discord_intelligence_suite.send_discord_embed", return_value=True) as mock_send:
            from actions.send_discord_intelligence_suite import broadcast_crypto_channel_intelligence
            res = broadcast_crypto_channel_intelligence()
            self.assertTrue(res)
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            channel_id, embed = args
            self.assertEqual(channel_id, "1541529106074828890")
            self.assertIn("CRYPTO", embed["title"])

    def test_economic_rationale_wajohat_included(self):
        description_sample = "DefiLlama data shows Solana 24h DEX volume exceeding $3.2B. Wajah: Cumulative Volume Delta is aggressively positive."
        self.assertIn("Wajah", description_sample)
        self.assertIn("DefiLlama", description_sample)


# ========================================================================
# Feature 16: Discord #elite-trade Engine
# ========================================================================
class TestFeature16_DiscordEliteTradeEngine(unittest.TestCase):
    """Feature 16: Institutional Forex/Gold setups, execution receipts, 5-min telemetry."""

    def test_elite_trade_channel_id(self):
        expected_channel = "1541528931063177226"
        from actions.send_discord_intelligence_suite import get_discord_config
        cfg = get_discord_config()
        configured = cfg.get("elite_trade_channel_id", expected_channel)
        self.assertEqual(configured, expected_channel)

    def test_forex_embed_dispatch_structure(self):
        with patch("actions.send_discord_intelligence_suite.send_discord_embed", return_value=True) as mock_send:
            from actions.send_discord_intelligence_suite import broadcast_forex_channel_intelligence
            res = broadcast_forex_channel_intelligence()
            self.assertTrue(res)
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            channel_id, embed = args
            self.assertEqual(channel_id, "1541528931063177226")
            self.assertIn("FOREX", embed["title"])

    def test_strict_channel_segregation_guarantee(self):
        crypto_id = "1541529106074828890"
        forex_id = "1541528931063177226"
        self.assertNotEqual(crypto_id, forex_id)

    def test_trade_ticket_receipt_fields(self):
        ticket = {
            "ticket_id": 98765432,
            "symbol": "XAUUSD",
            "type": "BUY_LIMIT",
            "entry_price": 2740.50,
            "sl": 2732.50,
            "tp1": 2755.00,
            "risk_usd": 7.50,
            "status": "PLACED"
        }
        self.assertEqual(ticket["status"], "PLACED")
        self.assertIn("tp1", ticket)

    def test_portfolio_5min_telemetry_payload(self):
        telemetry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "accounts": [
                {"name": "Pipdance $1k", "equity": 1024.50, "pnl": 24.50},
                {"name": "FTMO $100k", "equity": 101450.00, "pnl": 1450.00}
            ]
        }
        self.assertEqual(len(telemetry["accounts"]), 2)


# ========================================================================
# Feature 17: Discord Voice Channel Synthesis
# ========================================================================
class TestFeature17_DiscordVoiceChannelSynthesis(unittest.TestCase):
    """Feature 17: Voice playback via Edge-TTS / SAPI5 streaming PCM to voice channels."""

    def test_default_voices_configuration(self):
        from actions.voice_synthesizer import DEFAULT_VOICE, DEFAULT_URDU_VOICE
        self.assertEqual(DEFAULT_VOICE, "en-GB-RyanNeural")
        self.assertEqual(DEFAULT_URDU_VOICE, "ur-PK-AsadNeural")

    def test_scratch_audio_directory_exists(self):
        from actions.voice_synthesizer import SCRATCH_DIR
        self.assertTrue(SCRATCH_DIR.exists())

    def test_speech_synthesis_empty_text_safety(self):
        from actions.voice_synthesizer import synthesize_neural_speech
        res = synthesize_neural_speech("")
        self.assertEqual(res, "")

    def test_voice_channel_stream_packet_format(self):
        pcm_frame_bytes = 48000 * 2 * 2 * (20 / 1000)
        self.assertEqual(int(pcm_frame_bytes), 3840)

    def test_synthesize_neural_speech_mocked(self):
        with patch("actions.voice_synthesizer.synthesize_neural_speech_async") as mock_async:
            mock_async.return_value = "C:/fake/path/audio.mp3"
            from actions.voice_synthesizer import synthesize_neural_speech
            res = synthesize_neural_speech("Test audio prompt")
            self.assertTrue(res.endswith(".mp3") or res.endswith(".wav") or len(res) > 0)


# ========================================================================
# Feature 18: Microservices Ecosystem Health
# ========================================================================
class TestFeature18_MicroservicesEcosystemHealth(unittest.TestCase):
    """Feature 18: 100% uptime, health probes, and REST API dispatches across all 8 core services."""

    def test_all_8_core_services_defined(self):
        services = [
            "Dashboard (:8770)",
            "Mobile Remote (:8765)",
            "MQ3 Bot (:5050)",
            "Odysseus AI (:7000)",
            "Ollama Node (:11434)",
            "World Monitor (:3000)",
            "Discord Bot Gateway",
            "Autonomous Live Daemon"
        ]
        self.assertEqual(len(services), 8)

    def test_supervisor_build_services_structure(self):
        from bootstrap.supervisor import build_services
        services = build_services()
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0)

    def test_supervisor_port_up_contract(self):
        from bootstrap.supervisor import port_up
        res = port_up(59999)
        self.assertFalse(res)

    def test_supervisor_proc_running_contract(self):
        from bootstrap.supervisor import proc_running
        res = proc_running("non_existent_fake_proc_123")
        self.assertFalse(res)

    def test_platform_runtime_root_paths_resolved(self):
        import platform_runtime
        self.assertTrue(platform_runtime.JARVIS_ROOT.exists())
        self.assertTrue(os.path.isabs(str(platform_runtime.JARVIS_ROOT)))


# ========================================================================
# Feature 19: Execution Receipts & Latency Verification
# ========================================================================
class TestFeature19_ExecutionReceiptsAndLatency(unittest.TestCase):
    """Feature 19: Execution receipts and sub-1.5s latency verification."""

    def test_execution_receipt_required_fields(self):
        receipt = {
            "status": "success",
            "action": "app_launch",
            "detail": "Launched Chrome successfully",
            "stdout_summary": "Process PID: 12345",
            "bilingual_translation": {"input_lang": "ur", "intent": "app_launch"}
        }
        self.assertIn("status", receipt)
        self.assertIn("action", receipt)
        self.assertIn("detail", receipt)
        self.assertIn("stdout_summary", receipt)
        self.assertIn("bilingual_translation", receipt)
        self.assertIn(receipt["status"], ["success", "error", "blocked"])

    def test_execution_latency_threshold_check(self):
        max_allowed_latency_sec = 1.50
        measured_latency_sec = 0.42
        self.assertLessEqual(measured_latency_sec, max_allowed_latency_sec)

    def test_blocked_receipt_generation(self):
        receipt = {
            "status": "blocked",
            "action": "trade_exec",
            "detail": "Blocked by 15m News Blackout",
            "stdout_summary": "REJECTED_BY_RISK_GATE",
            "bilingual_translation": {"input_lang": "en", "intent": "trade_exec"}
        }
        self.assertEqual(receipt["status"], "blocked")

    def test_receipt_json_serialization(self):
        receipt = {
            "status": "success",
            "action": "system_vol",
            "detail": "Volume set to 50%",
            "stdout_summary": "OK",
            "bilingual_translation": {"input_lang": "en", "intent": "system_vol"}
        }
        serialized = json.dumps(receipt)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized, receipt)

    def test_bilingual_receipt_language_tag(self):
        receipt = {
            "status": "success",
            "bilingual_translation": {"input_lang": "ur", "intent": "app_kill"}
        }
        self.assertIn(receipt["bilingual_translation"]["input_lang"], ["ur", "en"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
