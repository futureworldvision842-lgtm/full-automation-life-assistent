"""
Unit Tests for Launcher Scripts & Remediation
Milestone M1 / Requirement R1 / Feature F-SUP-04
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class TestLauncherScripts(unittest.TestCase):
    """Test suite ensuring all launcher scripts use dynamic paths without legacy hardcoding."""

    def test_launch_jarvis_master_bat_has_no_hardcoded_e_paths(self):
        script = BASE_DIR / "LAUNCH_JARVIS_MASTER.bat"
        self.assertTrue(script.exists(), "LAUNCH_JARVIS_MASTER.bat must exist")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("E:\\jarvis", content, "LAUNCH_JARVIS_MASTER.bat must not contain hardcoded E:\\jarvis")
        self.assertNotIn("jarvis_wweb.js", content, "LAUNCH_JARVIS_MASTER.bat must not reference legacy jarvis_wweb.js")
        self.assertIn("jarvis_baileys.js", content, "LAUNCH_JARVIS_MASTER.bat must reference jarvis_baileys.js")
        self.assertIn("%~dp0", content, "LAUNCH_JARVIS_MASTER.bat must use dynamic %~dp0 relative paths")

    def test_start_full_jarvis_ecosystem_bat_has_no_hardcoded_e_paths(self):
        script = BASE_DIR / "START_FULL_JARVIS_ECOSYSTEM.bat"
        self.assertTrue(script.exists(), "START_FULL_JARVIS_ECOSYSTEM.bat must exist")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("E:\\jarvis", content, "START_FULL_JARVIS_ECOSYSTEM.bat must not contain hardcoded E:\\jarvis")
        self.assertNotIn("jarvis_wweb.js", content, "START_FULL_JARVIS_ECOSYSTEM.bat must not reference legacy jarvis_wweb.js")
        self.assertIn("jarvis_baileys.js", content, "START_FULL_JARVIS_ECOSYSTEM.bat must reference jarvis_baileys.js")
        self.assertIn("%~dp0", content, "START_FULL_JARVIS_ECOSYSTEM.bat must use dynamic %~dp0 relative paths")

    def test_start_full_jarvis_ecosystem_ps1_has_no_hardcoded_e_paths(self):
        script = BASE_DIR / "START_FULL_JARVIS_ECOSYSTEM.ps1"
        self.assertTrue(script.exists(), "START_FULL_JARVIS_ECOSYSTEM.ps1 must exist")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("E:\\jarvis", content, "START_FULL_JARVIS_ECOSYSTEM.ps1 must not contain hardcoded E:\\jarvis")
        self.assertIn("jarvis_baileys.js", content, "START_FULL_JARVIS_ECOSYSTEM.ps1 must reference jarvis_baileys.js")
        self.assertIn("$PSScriptRoot", content, "START_FULL_JARVIS_ECOSYSTEM.ps1 must use dynamic $PSScriptRoot")

    def test_jarvis_start_all_cmd_structure_and_dynamic_paths(self):
        script = BASE_DIR / "JARVIS - START ALL.cmd"
        self.assertTrue(script.exists(), "JARVIS - START ALL.cmd must exist in project root")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("E:\\jarvis", content, "JARVIS - START ALL.cmd must not contain hardcoded E:\\jarvis")
        self.assertIn("%~dp0", content, "JARVIS - START ALL.cmd must use dynamic %~dp0 relative paths")
        self.assertIn("bootstrap\\supervisor.py", content, "JARVIS - START ALL.cmd must launch bootstrap\\supervisor.py")
        self.assertIn("8770", content, "JARVIS - START ALL.cmd must probe and open port 8770")
        self.assertIn("http://127.0.0.1:8770", content, "JARVIS - START ALL.cmd must open http://127.0.0.1:8770")

    def test_jarvis_stop_all_cmd_structure_and_clean_termination(self):
        script = BASE_DIR / "JARVIS - STOP ALL.cmd"
        self.assertTrue(script.exists(), "JARVIS - STOP ALL.cmd must exist in project root")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("E:\\jarvis", content, "JARVIS - STOP ALL.cmd must not contain hardcoded E:\\jarvis")
        self.assertIn("%~dp0", content, "JARVIS - STOP ALL.cmd must use dynamic %~dp0 relative paths")
        self.assertIn("bootstrap\\stop_all.py", content, "JARVIS - STOP ALL.cmd must execute bootstrap\\stop_all.py")
        for port in ("8770", "8765", "5050", "7000", "3000"):
            self.assertIn(port, content, f"JARVIS - STOP ALL.cmd must reference port {port}")


if __name__ == "__main__":
    unittest.main()
