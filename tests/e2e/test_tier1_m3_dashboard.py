"""
tests/e2e/test_tier1_m3_dashboard.py
================================================================================
Milestone M3: Unified Master Dashboard Frontend, PC Control & 3D Health HUD
================================================================================
Comprehensive behavioral verification tests covering:
  1. Terminal / Direct PowerShell Execution authorization and whitelisting
  2. Active Process Explorer with kill-switch safety & real termination
  3. Hardware Vitals & Self-Healing Diagnostics with dynamic options
  4. 3D Real-Time Holographic Earth & PC Health HUD with 8 tactical nodes
  5. Multi-Frontend Workspace Switcher with WebGL anti-collapse CSS & resize events
  6. Conversational J.A.R.V.I.S. Console in Roman Urdu and English
"""

import sys
import os
import time
import subprocess
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from starlette.testclient import TestClient
import dashboard
from core.command_router import get_command_router


class TestTier1_M3_MasterDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(dashboard.app)
        cls.router = get_command_router()

    def test_sender_authorization_whitelist(self):
        """Verify dashboard:127.0.0.1, dashboard, 127.0.0.1, and localhost are authorized."""
        self.assertTrue(self.router.is_authorized_sender("dashboard:127.0.0.1", "dashboard"))
        self.assertTrue(self.router.is_authorized_sender("dashboard", "dashboard"))
        self.assertTrue(self.router.is_authorized_sender("127.0.0.1", "dashboard"))
        self.assertTrue(self.router.is_authorized_sender("localhost", "dashboard"))

    def test_terminal_powershell_direct_execution(self):
        """Verify commands prefixed with '!' execute via PowerShell and return stdout."""
        resp = self.client.post("/api/terminal/exec", json={"cmd": "!dir"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("Directory: ", data.get("output", ""))

    def test_terminal_execute_dedicated_endpoint(self):
        """Verify POST /api/terminal/execute accepts command and returns success, output, exit_code."""
        resp = self.client.post("/api/terminal/execute", json={"command": "Get-Date", "sender_id": "dashboard"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("exit_code"), 0)
        self.assertTrue(len(data.get("output", "")) > 0)

    def test_system_processes_explorer_listing(self):
        """Verify GET /api/system/processes returns sorted process list with expected fields."""
        resp = self.client.get("/api/system/processes?limit=25&sort_by=cpu")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertTrue(data.get("success"))
        self.assertGreater(data.get("total_processes", 0), 0)
        procs = data.get("processes", [])
        self.assertGreater(len(procs), 0)
        p0 = procs[0]
        self.assertIn("pid", p0)
        self.assertIn("name", p0)
        self.assertIn("cpu_percent", p0)
        self.assertIn("memory_mb", p0)
        self.assertIn("status", p0)

    def test_system_process_kill_kernel_protection(self):
        """Verify kernel PIDs (<=4) cannot be terminated."""
        resp = self.client.post("/api/system/process/kill", json={"pid": 4})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("Cannot terminate system kernel process", data.get("message", ""))

    def test_system_process_kill_genuine_termination(self):
        """Verify genuine termination of a running process via psutil."""
        proc = subprocess.Popen(["powershell", "-Command", "Start-Sleep -Seconds 30"])
        try:
            time.sleep(0.3)
            pid = proc.pid
            resp = self.client.post("/api/system/process/kill", json={"pid": pid})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("ok"))
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("pid"), pid)
            proc.poll()
            self.assertIsNotNone(proc.returncode)
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_hardware_vitals_multi_drive(self):
        """Verify CPU %, RAM GB, and drives C: and F: storage telemetry."""
        resp = self.client.get("/api/pc")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("cpu", data)
        self.assertIn("ram_used_gb", data)
        self.assertIn("ram_total_gb", data)
        self.assertIn("drive_c_free_gb", data)
        self.assertIn("drive_f_free_gb", data)

    def test_3d_telemetry_tactical_nodes(self):
        """Verify 8 tactical nodes are present in /api/system/3d_telemetry."""
        resp = self.client.get("/api/system/3d_telemetry")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        nodes = data.get("world_nodes", [])
        self.assertEqual(len(nodes), 8)
        node_ids = {n["id"] for n in nodes}
        for expected in ["HQ_ISL", "MKT_LON", "MKT_NYC", "MKT_TKO", "MKT_SGP", "CHK_HRM", "CHK_MND", "GEO_TWN"]:
            self.assertIn(expected, node_ids)

    def test_self_healing_status_and_resolution(self):
        """Verify self-healing diagnostic returns health and can execute remediation."""
        r1 = self.client.get("/api/self_healing/status")
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertTrue(d1.get("ok"))
        self.assertIn("health", d1)
        self.assertIn("diagnostic_prompt", d1)

        r2 = self.client.post("/api/self_healing/resolve", json={"option_id": 1})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertTrue(d2.get("ok"))

    def test_frontend_html_m3_compliance(self):
        """Verify HTML contains Process Explorer card, WebGL CSS, 8 tactical nodes, and switcher resize dispatch."""
        html_path = BASE_DIR / "web" / "universal_command_center.html"
        html = html_path.read_text(encoding="utf-8", errors="replace")
        self.assertIn("proc-explorer-card", html)
        self.assertIn("fetchProcesses", html)
        self.assertIn("killProcess", html)
        self.assertIn(".tab-pane", html)
        self.assertIn("visibility: hidden", html)
        self.assertIn("opacity: 0", html)
        self.assertIn("GEO_TWN", html)
        self.assertIn("frameMq3", html)
        self.assertIn("dispatchEvent", html)

    def test_conversational_console_bilingual(self):
        """Verify Roman Urdu dialogue greeting and English command processing."""
        resp = self.client.post("/api/terminal/exec", json={"cmd": "kese ho jarvis"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("Main theek hoon Sir", data.get("output", ""))

        r_th = self.client.get("/api/jarvis/thoughts")
        self.assertEqual(r_th.status_code, 200)
        self.assertIn("thoughts", r_th.json())


if __name__ == "__main__":
    unittest.main()
