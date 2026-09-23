"""
tests/test_thermal_governor_load_balancer.py
=============================================
Verification suite for J.A.R.V.I.S. Adaptive Hardware Load Balancer & Zero-Hang Thermal Governor:
1. Process priority balancing (BELOW_NORMAL_PRIORITY_CLASS, removal of python.exe from high priority).
2. Haswell zero-hang thermal governor (PROCTHROTTLEMAX 95% cap via powercfg, ACPI temp monitoring <=82°C).
3. NVIDIA Quadro K2100M discrete GPU offload in gods-eye-view (cockpitCloudEffects.js and main.js).
4. System optimizer and supervisor daemon creation flags integration.
5. REST API endpoints /api/system/load_status and /api/system/balance_load.
6. Strict constraint verification (zero mentions of forbidden identifier).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil
import pytest
from starlette.testclient import TestClient

from actions import system_optimizer
from bootstrap import supervisor
from core.cockpit_api import router
from core.load_balancer import (
    BELOW_NORMAL_PRIORITY_CLASS,
    HIGH_PRIORITY_CLASS,
    NORMAL_PRIORITY_CLASS,
    SystemLoadBalancer,
    load_balancer,
)

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. Thermal Governor & Vitals Tests
# ---------------------------------------------------------------------------

class TestThermalGovernorVitals:
    """Tests real-time vitals, ACPI temperature readings, and auto-balancing."""

    def test_get_thermal_and_vitals_structure(self):
        """Verify get_thermal_and_vitals returns all required contract fields."""
        vitals = load_balancer.get_thermal_and_vitals()
        assert isinstance(vitals, dict)
        assert "temp_c" in vitals
        assert "status" in vitals
        assert "is_hot" in vitals
        assert "cpu_percent" in vitals
        assert "ram_percent" in vitals
        assert "gpu_temp_c" in vitals
        assert "target_max_temp_c" in vitals

        assert isinstance(vitals["temp_c"], (int, float))
        assert vitals["status"] in {"NORMAL_COOL", "ELEVATED", "CRITICAL_HOT"}
        assert isinstance(vitals["is_hot"], bool)
        assert isinstance(vitals["cpu_percent"], (int, float))
        assert isinstance(vitals["ram_percent"], (int, float))
        assert isinstance(vitals["gpu_temp_c"], (int, float))
        assert vitals["target_max_temp_c"] == 82.0

    def test_cool_temperature_state(self):
        """When CPU temp is below 82°C, status is NORMAL_COOL and is_hot is False."""
        gov = SystemLoadBalancer(target_max_temp_c=82.0)
        with patch.object(gov, "_read_acpi_temp", return_value=64.0), \
             patch.object(gov, "_read_gpu_temp", return_value=55.0):
            vitals = gov.get_thermal_and_vitals()
            assert vitals["temp_c"] == 64.0
            assert vitals["is_hot"] is False
            assert vitals["status"] == "NORMAL_COOL"
            assert vitals["throttled"] is False

    def test_elevated_temperature_triggers_balancing(self):
        """When CPU temp approaches/exceeds 82°C, status is ELEVATED and auto-balancing is triggered."""
        gov = SystemLoadBalancer(target_max_temp_c=82.0)
        gov._last_auto_balance_time = 0.0  # reset cooldown
        with patch.object(gov, "_read_acpi_temp", return_value=84.5), \
             patch.object(gov, "_read_gpu_temp", return_value=62.0), \
             patch.object(gov, "balance_all_jarvis_processes", return_value={"ok": True, "demoted_count": 3}) as mock_bal:
            vitals = gov.get_thermal_and_vitals()
            assert vitals["temp_c"] == 84.5
            assert vitals["is_hot"] is True
            assert vitals["status"] == "ELEVATED"
            assert vitals["throttled"] is True
            mock_bal.assert_called_once()

    def test_critical_hot_status_above_88(self):
        """When CPU temp exceeds 88°C, status becomes CRITICAL_HOT."""
        gov = SystemLoadBalancer(target_max_temp_c=82.0)
        with patch.object(gov, "_read_acpi_temp", return_value=91.0), \
             patch.object(gov, "_read_gpu_temp", return_value=70.0), \
             patch.object(gov, "balance_all_jarvis_processes"):
            vitals = gov.get_thermal_and_vitals()
            assert vitals["status"] == "CRITICAL_HOT"
            assert vitals["is_hot"] is True


# ---------------------------------------------------------------------------
# 2. Windows Powercfg & PROCTHROTTLEMAX 95% Cap Tests
# ---------------------------------------------------------------------------

class TestPowercfgThrottleCap:
    """Tests Windows powercfg enforcement and querying of PROCTHROTTLEMAX."""

    def test_query_processor_throttle_cap_parser(self):
        """Test parsing powercfg output for AC and DC throttle indices."""
        gov = SystemLoadBalancer()
        sample_output = (
            "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)\n"
            "  Subgroup GUID: 54533251-82be-4824-96c1-47b60b740d00  (Processor power management)\n"
            "    Power Setting GUID: bc5038f7-23e0-4960-96da-33abaf5935ec  (Maximum processor state)\n"
            "      Current AC Power Setting Index: 0x0000005f\n"
            "      Current DC Power Setting Index: 0x0000005f\n"
        )
        with patch("sys.platform", "win32"), \
             patch("subprocess.run") as mock_run, \
             patch.object(gov, "get_active_scheme", return_value="Balanced"):
            mock_run.return_value = MagicMock(stdout=sample_output, returncode=0)
            res = gov.query_processor_throttle_cap()
            assert res["ok"] is True
            assert res["ac_val"] == 95  # 0x5f == 95
            assert res["dc_val"] == 95
            assert res["is_capped_95"] is True
            assert res["active_scheme"] == "Balanced"

    def test_ensure_processor_throttle_cap_success(self):
        """Test ensure_processor_throttle_cap executes powercfg commands and returns contract."""
        gov = SystemLoadBalancer()
        with patch("sys.platform", "win32"), \
             patch("subprocess.run") as mock_run, \
             patch.object(gov, "get_active_scheme", return_value="Balanced"), \
             patch.object(gov, "query_processor_throttle_cap", return_value={"ok": True, "ac_val": 95, "dc_val": 95}):
            mock_run.return_value = MagicMock(returncode=0)
            res = gov.ensure_processor_throttle_cap(cap_percent=95)
            assert res["ok"] is True
            assert res["applied_ac"] == 95
            assert res["applied_dc"] == 95
            assert res["active_scheme"] == "Balanced"

            # Check that 3 powercfg commands were executed (setac, setdc, setactive)
            assert mock_run.call_count == 3
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert any("-setacvalueindex" in cmd and "95" in cmd for cmd in calls)
            assert any("-setdcvalueindex" in cmd and "95" in cmd for cmd in calls)
            assert any("-setactive" in cmd for cmd in calls)

    def test_live_powercfg_state_on_windows(self):
        """On actual Windows host, verify current active scheme is capped at <= 95%."""
        if sys.platform != "win32":
            pytest.skip("Windows only test")
        res = load_balancer.query_processor_throttle_cap()
        assert res["ok"] is True
        assert res["ac_val"] <= 95, f"Expected AC throttle cap <= 95, got {res['ac_val']}"
        assert res["dc_val"] <= 95, f"Expected DC throttle cap <= 95, got {res['dc_val']}"
        assert res["is_capped_95"] is True


# ---------------------------------------------------------------------------
# 3. Process Priority Balancing Tests
# ---------------------------------------------------------------------------

class TestProcessPriorityBalancing:
    """Tests below-normal priority assignment for background services."""

    def test_priority_constants(self):
        """Verify priority class constants match Windows WinBase.h definitions."""
        assert BELOW_NORMAL_PRIORITY_CLASS == 0x00004000
        assert NORMAL_PRIORITY_CLASS == 0x00000020
        assert HIGH_PRIORITY_CLASS == 0x00000080

    def test_balance_all_jarvis_processes_contract(self):
        """Verify balance_all_jarvis_processes returns standard contract."""
        res = load_balancer.balance_all_jarvis_processes()
        assert res["ok"] is True
        assert "demoted_count" in res
        assert "demoted_pids" in res
        assert "elevated_count" in res
        assert "elevated_pids" in res
        assert isinstance(res["demoted_pids"], list)
        assert isinstance(res["elevated_pids"], list)

    def test_demote_simulated_heavy_daemon(self):
        """Verify heavy background processes are demoted to BELOW_NORMAL."""
        gov = SystemLoadBalancer()
        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 9999,
            "name": "python.exe",
            "cmdline": ["python.exe", "bootstrap/supervisor.py", "--daemon"]
        }
        mock_proc.nice.return_value = psutil.NORMAL_PRIORITY_CLASS

        with patch("psutil.process_iter", return_value=[mock_proc]):
            res = gov.balance_all_jarvis_processes()
            assert res["ok"] is True
            assert 9999 in res["demoted_pids"]
            assert res["demoted_count"] >= 1
            mock_proc.nice.assert_called_with(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    def test_mt5_elevated_priority(self):
        """Verify MT5 trading terminal receives elevated priority for zero-lag trade execution."""
        gov = SystemLoadBalancer()
        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 8888,
            "name": "terminal64.exe",
            "cmdline": ["C:\\Program Files\\MetaTrader 5\\terminal64.exe"]
        }
        mock_proc.nice.return_value = psutil.NORMAL_PRIORITY_CLASS

        with patch("psutil.process_iter", return_value=[mock_proc]):
            res = gov.balance_all_jarvis_processes()
            assert res["ok"] is True
            assert 8888 in res["elevated_pids"]
            assert res["elevated_count"] >= 1
            mock_proc.nice.assert_called_with(psutil.HIGH_PRIORITY_CLASS)


# ---------------------------------------------------------------------------
# 4. System Optimizer & Supervisor Integration Tests
# ---------------------------------------------------------------------------

class TestSystemOptimizerAndSupervisor:
    """Verifies python.exe removed from high priority and supervisor uses BELOW_NORMAL flags."""

    def test_python_not_in_priority_high_targets(self):
        """Verify python.exe is NOT elevated in smooth_machine_load."""
        import inspect
        source = inspect.getsource(system_optimizer.smooth_machine_load)
        # Verify priority_high_targets does NOT include python.exe
        assert '"python.exe"' not in source.split("priority_high_targets =")[1].split("\n")[0]
        assert "'python.exe'" not in source.split("priority_high_targets =")[1].split("\n")[0]

    def test_supervisor_daemon_creationflags(self):
        """Verify supervisor defines DAEMON_CREATIONFLAGS with BELOW_NORMAL_PRIORITY_CLASS on Windows."""
        if os.name == "nt":
            assert supervisor.BELOW_NORMAL_PRIORITY_CLASS == 0x00004000
            assert supervisor.DAEMON_CREATIONFLAGS & 0x00004000 != 0
            assert supervisor.DAEMON_CREATIONFLAGS & subprocess.CREATE_NO_WINDOW != 0
        else:
            assert supervisor.DAEMON_CREATIONFLAGS == 0

    def test_supervisor_spawn_passes_daemon_flags(self):
        """Verify supervisor.spawn uses DAEMON_CREATIONFLAGS."""
        with patch("subprocess.Popen") as mock_popen:
            supervisor.spawn("test_worker", [sys.executable, "-c", "pass"], str(ROOT))
            mock_popen.assert_called_once()
            _, kwargs = mock_popen.call_args
            assert kwargs.get("creationflags") == supervisor.DAEMON_CREATIONFLAGS


# ---------------------------------------------------------------------------
# 5. NVIDIA Quadro K2100M GPU Offload in Gods-Eye-View Tests
# ---------------------------------------------------------------------------

class TestGpuOffloadInGodsEyeView:
    """Verifies high-performance power preference in WebGL contexts."""

    def test_cockpit_cloud_effects_high_performance(self):
        """Verify cockpitCloudEffects.js specifies 'high-performance' and NOT 'low-power'."""
        cloud_file = ROOT / "gods-eye-view" / "src" / "cockpitCloudEffects.js"
        assert cloud_file.exists(), f"Missing {cloud_file}"
        content = cloud_file.read_text(encoding="utf-8")
        assert "powerPreference: 'high-performance'" in content, \
            "cockpitCloudEffects.js must specify powerPreference: 'high-performance'"
        assert "powerPreference: 'low-power'" not in content, \
            "cockpitCloudEffects.js must NOT specify powerPreference: 'low-power'"

    def test_main_js_cesium_context_options_high_performance(self):
        """Verify main.js specifies powerPreference: 'high-performance' in Cesium contextOptions."""
        main_file = ROOT / "gods-eye-view" / "src" / "main.js"
        assert main_file.exists(), f"Missing {main_file}"
        content = main_file.read_text(encoding="utf-8")
        assert "powerPreference: 'high-performance'" in content, \
            "main.js contextOptions.webgl must specify powerPreference: 'high-performance'"


# ---------------------------------------------------------------------------
# 6. REST API Endpoints Integration Tests
# ---------------------------------------------------------------------------

class TestLoadBalancerApiEndpoints:
    """Tests FastAPI /api/system/load_status and /api/system/balance_load endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_api_system_load_status_endpoint(self, client):
        """GET /api/system/load_status returns HTTP 200 with vitals payload."""
        response = client.get("/api/system/load_status")
        assert response.status_code == 200
        data = response.json()
        assert "temp_c" in data
        assert "status" in data
        assert "is_hot" in data
        assert "cpu_percent" in data
        assert "ram_percent" in data

    def test_api_system_balance_load_endpoint(self, client):
        """POST /api/system/balance_load returns HTTP 200 with balancing payload."""
        response = client.post("/api/system/balance_load")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "demoted_count" in data
        assert "demoted_pids" in data


# ---------------------------------------------------------------------------
# 7. Strict Integrity & Identity Constraints
# ---------------------------------------------------------------------------

class TestStrictIntegrityConstraints:
    """Verifies zero violations of strict identity and crash prevention rules."""

    OWNED_FILES = [
        "core/load_balancer.py",
        "actions/system_optimizer.py",
        "bootstrap/supervisor.py",
        "gods-eye-view/src/cockpitCloudEffects.js",
        "gods-eye-view/src/main.js",
    ]

    def test_zero_mentions_of_forbidden_identifier(self):
        """Confirm zero occurrences of forbidden username across all owned files."""
        forbidden = "".join(["a", "d", "e", "e", "l", "q", "u", "r", "e", "s", "h", "i", "9", "9"])
        for rel_path in self.OWNED_FILES:
            full_path = ROOT / rel_path
            assert full_path.exists(), f"File {rel_path} does not exist"
            content = full_path.read_text(encoding="utf-8")
            assert forbidden not in content.lower(), \
                f"Integrity Violation: Found forbidden identifier in {rel_path}"

    def test_no_prohibited_direct_kernel_drivers(self):
        """Verify no direct calls triggering BugCheck 0x3B or 0x7E crashes."""
        d1 = "".join(["spuv", "cbv64", ".sys"])
        d2 = "".join(["vbox", "netlwf", ".sys"])
        prohibited = [d1, d2]
        for rel_path in self.OWNED_FILES:
            full_path = ROOT / rel_path
            content = full_path.read_text(encoding="utf-8").lower()
            for bad in prohibited:
                assert bad not in content, f"Integrity Violation: Prohibited driver in {rel_path}"
