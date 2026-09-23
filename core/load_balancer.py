"""
core/load_balancer.py — J.A.R.V.I.S. Adaptive Load Balancer & Thermal Governor
=============================================================================
Prevents system freezing, mouse lag, and thermal runaway:
1. Automatically assigns BELOW_NORMAL_PRIORITY_CLASS to heavy background daemons
   and microservices so the Windows UI, Explorer, and foreground apps remain
   100% butter-smooth without cursor stutter or thread starvation.
2. Monitors ACPI Thermal Zone temperatures. If CPU approaches or exceeds 82°C,
   automatically triggers process balancing and logs safety telemetry to allow
   heatsink cooling.
3. Enforces processor throttle cap (95%) via Windows powercfg to disable Intel
   Haswell Turbo Boost over-voltage thermal runaway (>100°C) and eliminate BIOS
   emergency shutdowns.
4. Monitors discrete NVIDIA Quadro K2100M GPU vitals to ensure GPU offloading
   prevents CPU package thermal saturation.
=============================================================================
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

logger = logging.getLogger("Jarvis.LoadBalancer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Windows Priority Classes
IDLE_PRIORITY_CLASS = 0x00000040
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
NORMAL_PRIORITY_CLASS = 0x00000020
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
HIGH_PRIORITY_CLASS = 0x00000080

_NVSMI_PATHS = [
    r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    r"C:\Windows\System32\nvidia-smi.exe",
]


class SystemLoadBalancer:
    """Manages CPU, GPU, memory, and thermal load balancing for smooth operation."""

    def __init__(self, target_max_temp_c: float = 82.0):
        self.target_max_temp_c = target_max_temp_c
        self.last_temp_c = 65.0
        self.managed_pids: set[int] = set()
        self._last_auto_balance_time: float = 0.0
        self._gpu_temp_cache: Optional[float] = None
        self._gpu_temp_cache_time: float = 0.0
        self._gpu_cache_ttl: float = 5.0
        self._nvsmi_path: Optional[str] = self._find_nvsmi()

    def _find_nvsmi(self) -> Optional[str]:
        for p in _NVSMI_PATHS:
            if os.path.isfile(p):
                return p
        path_tool = psutil.which("nvidia-smi") if hasattr(psutil, "which") else None
        if path_tool and os.path.isfile(path_tool):
            return path_tool
        return None

    def optimize_current_process(self, priority: str = "below_normal"):
        """
        Sets priority of the calling process to below_normal or idle to ensure
        Windows UI and user interactions never stutter.
        """
        if sys.platform != "win32":
            return

        try:
            p = psutil.Process(os.getpid())
            if priority == "below_normal":
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            elif priority == "idle":
                p.nice(psutil.IDLE_PRIORITY_CLASS)
            elif priority == "normal":
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
            elif priority == "high":
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            logger.info("Process PID %d priority set to %s", os.getpid(), priority)
        except Exception as e:
            logger.debug("Failed to set process priority: %s", e)

    def get_active_scheme(self) -> str:
        """Queries the active Windows power scheme via powercfg."""
        if sys.platform != "win32":
            return "POSIX / Non-Windows"
        try:
            res = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            out = res.stdout.strip()
            if out:
                match = re.search(r"\(([^)]+)\)", out)
                if match:
                    return match.group(1).strip()
                guid_match = re.search(r"Power Scheme GUID:\s*([0-9a-fA-F-]+)", out)
                if guid_match:
                    return guid_match.group(1).strip()
                return out
        except Exception as exc:
            logger.debug("get_active_scheme error: %s", exc)
        return "Unknown"

    def query_processor_throttle_cap(self) -> Dict[str, Any]:
        """
        Queries PROCTHROTTLEMAX on current Windows power scheme.
        Returns:
            {"ok": bool, "ac_val": int, "dc_val": int, "is_capped_95": bool, "active_scheme": str}
        """
        if sys.platform != "win32":
            return {
                "ok": True,
                "ac_val": 95,
                "dc_val": 95,
                "is_capped_95": True,
                "active_scheme": "POSIX / Non-Windows",
                "simulated": True
            }

        active_scheme = self.get_active_scheme()
        try:
            cmd = ["powercfg", "/q", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
            out = res.stdout

            ac_val = None
            dc_val = None

            for line in out.splitlines():
                line_lower = line.lower().strip()
                if "current ac power setting index:" in line_lower:
                    val_str = line.split(":")[-1].strip()
                    try:
                        ac_val = int(val_str, 16) if val_str.startswith("0x") else int(val_str)
                    except ValueError:
                        pass
                elif "current dc power setting index:" in line_lower:
                    val_str = line.split(":")[-1].strip()
                    try:
                        dc_val = int(val_str, 16) if val_str.startswith("0x") else int(val_str)
                    except ValueError:
                        pass

            if ac_val is not None and dc_val is not None:
                return {
                    "ok": True,
                    "ac_val": ac_val,
                    "dc_val": dc_val,
                    "is_capped_95": (ac_val <= 95 and dc_val <= 95),
                    "active_scheme": active_scheme
                }
            return {
                "ok": False,
                "ac_val": ac_val or 0,
                "dc_val": dc_val or 0,
                "is_capped_95": False,
                "active_scheme": active_scheme,
                "error": "Failed to parse AC/DC index from powercfg output"
            }
        except Exception as exc:
            logger.warning("query_processor_throttle_cap failed: %s", exc)
            return {
                "ok": False,
                "ac_val": 0,
                "dc_val": 0,
                "is_capped_95": False,
                "active_scheme": active_scheme,
                "error": str(exc)
            }

    def ensure_processor_throttle_cap(self, cap_percent: int = 95) -> Dict[str, Any]:
        """
        Enforces PROCTHROTTLEMAX cap via Windows powercfg to stop Haswell
        Turbo Boost thermal runaway (>100°C) and eliminate BIOS shutdowns.
        Interface contract:
            {"ok": bool, "applied_ac": int, "applied_dc": int, "active_scheme": str}
        """
        if sys.platform != "win32":
            return {
                "ok": True,
                "applied_ac": cap_percent,
                "applied_dc": cap_percent,
                "active_scheme": "POSIX / Non-Windows",
                "cap_percent": cap_percent
            }

        active_scheme = self.get_active_scheme()
        cap_str = str(cap_percent)
        commands = [
            ["powercfg", "-setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", cap_str],
            ["powercfg", "-setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", cap_str],
            ["powercfg", "-setactive", "SCHEME_CURRENT"]
        ]

        try:
            for cmd in commands:
                subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=True)

            # Verify applied state
            query = self.query_processor_throttle_cap()
            applied_ac = query.get("ac_val", cap_percent)
            applied_dc = query.get("dc_val", cap_percent)

            logger.info("PROCTHROTTLEMAX enforced at %d%% (AC: %d%%, DC: %d%%, Scheme: %s)",
                        cap_percent, applied_ac, applied_dc, active_scheme)

            return {
                "ok": True,
                "applied_ac": applied_ac,
                "applied_dc": applied_dc,
                "active_scheme": active_scheme,
                "cap_percent": cap_percent
            }
        except Exception as exc:
            logger.error("Failed to enforce PROCTHROTTLEMAX cap: %s", exc)
            return {
                "ok": False,
                "applied_ac": 0,
                "applied_dc": 0,
                "active_scheme": active_scheme,
                "cap_percent": cap_percent,
                "error": str(exc)
            }

    def balance_all_jarvis_processes(self) -> Dict[str, Any]:
        """
        Scans and optimizes all Python, Node, and MT5 processes belonging to the fleet.
        Sets background workers and daemons to BELOW_NORMAL priority so the laptop
        never hangs or stutters, and preserves high priority for MT5 trading execution.
        Interface contract:
            {"ok": bool, "demoted_count": int, "demoted_pids": list, "elevated_count": int}
        """
        demoted_pids: List[int] = []
        elevated_pids: List[int] = []
        optimized: List[Dict[str, Any]] = []

        is_win = sys.platform == "win32"
        below_normal = psutil.BELOW_NORMAL_PRIORITY_CLASS if is_win else 10
        high_priority = psutil.HIGH_PRIORITY_CLASS if is_win else -10
        normal_priority = psutil.NORMAL_PRIORITY_CLASS if is_win else 0

        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                cmdline = ' '.join(p.info.get('cmdline') or []).lower()
                pid = p.info['pid']

                # 1. Trading critical targets (MT5) -> elevated priority
                if "terminal64.exe" in name or "metatrader5.exe" in name:
                    try:
                        current_nice = p.nice()
                        if current_nice != high_priority:
                            p.nice(high_priority)
                            elevated_pids.append(pid)
                            optimized.append({'pid': pid, 'name': name, 'action': 'SET_HIGH_PRIORITY'})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    continue

                # 2. Background fleet services and workers -> demote to BELOW_NORMAL
                is_fleet_daemon = any(k in cmdline for k in [
                    'jarvis', 'mq3', 'worldmonitor', 'terminal.py', 'dashboard.py',
                    'worker', 'daemon', 'seeder', 'scraper', 'ollama', 'vite',
                    'discord_bot.py', 'jarvis_baileys.js', 'mobile_control.py',
                    'autonomous_live_daemon.py', 'supervisor.py'
                ])
                is_heavy_runtime = any(name == proc_name for proc_name in [
                    'ollama.exe', 'ollama_llama_server.exe', 'node.exe', 'python.exe', 'pythonw.exe'
                ])

                if is_fleet_daemon or (is_heavy_runtime and "jarvis" in cmdline):
                    current_nice = p.nice()
                    # Demote any process currently at normal or above priority
                    if current_nice in (
                        normal_priority,
                        HIGH_PRIORITY_CLASS if is_win else -10,
                        ABOVE_NORMAL_PRIORITY_CLASS if is_win else -5
                    ):
                        p.nice(below_normal)
                        demoted_pids.append(pid)
                        optimized.append({'pid': pid, 'name': name, 'action': 'SET_BELOW_NORMAL'})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        logger.info("Process balancing complete: demoted=%d, elevated=%d", len(demoted_pids), len(elevated_pids))
        return {
            'ok': True,
            'demoted_count': len(demoted_pids),
            'demoted_pids': demoted_pids,
            'elevated_count': len(elevated_pids),
            'elevated_pids': elevated_pids,
            'optimized_count': len(demoted_pids) + len(elevated_pids),
            'optimized_processes': optimized
        }

    def _read_gpu_temp(self) -> float:
        """Reads NVIDIA Quadro K2100M GPU temperature via nvidia-smi with 5s caching."""
        now = time.monotonic()
        if self._gpu_temp_cache is not None and (now - self._gpu_temp_cache_time) < self._gpu_cache_ttl:
            return self._gpu_temp_cache

        if not self._nvsmi_path:
            self._nvsmi_path = self._find_nvsmi()

        if not self._nvsmi_path:
            return 0.0

        try:
            cmd = [
                self._nvsmi_path,
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4, check=False)
            val = res.stdout.strip()
            if val and val.isdigit():
                temp = float(val)
                self._gpu_temp_cache = temp
                self._gpu_temp_cache_time = now
                return temp
        except Exception as exc:
            logger.debug("Could not read GPU temperature: %s", exc)

        return self._gpu_temp_cache if self._gpu_temp_cache is not None else 0.0

    def get_thermal_and_vitals(self) -> Dict[str, Any]:
        """
        Returns real-time thermal readings and CPU/RAM/GPU distribution.
        If CPU temperature approaches or exceeds target_max_temp_c (82°C),
        automatically triggers process balancing to safeguard Haswell CPU.
        Interface contract:
            {"temp_c": float, "status": str, "is_hot": bool, "cpu_percent": float, "ram_percent": float, "gpu_temp_c": float}
        """
        temp_c = self._read_acpi_temp()
        self.last_temp_c = temp_c
        cpu_pct = psutil.cpu_percent(interval=None)
        vmem = psutil.virtual_memory()
        gpu_temp_c = self._read_gpu_temp()

        # Check if laptop is running hot
        is_hot = temp_c >= self.target_max_temp_c
        status = "CRITICAL_HOT" if temp_c >= 88.0 else ("ELEVATED" if is_hot else "NORMAL_COOL")

        throttled = False
        if is_hot:
            now = time.monotonic()
            if (now - self._last_auto_balance_time) > 10.0:
                logger.warning(
                    "Thermal threshold approached (%.1f°C >= %.1f°C). Auto-balancing Jarvis processes to prevent thermal runaway.",
                    temp_c, self.target_max_temp_c
                )
                self.balance_all_jarvis_processes()
                self._last_auto_balance_time = now
                throttled = True

        return {
            'temp_c': temp_c,
            'status': status,
            'is_hot': is_hot,
            'cpu_percent': cpu_pct,
            'cpu_pct': cpu_pct,
            'ram_percent': vmem.percent,
            'ram_pct': vmem.percent,
            'ram_free_gb': round(vmem.available / (1024**3), 2),
            'gpu_temp_c': gpu_temp_c,
            'target_max_temp_c': self.target_max_temp_c,
            'throttled': throttled
        }

    def _read_acpi_temp(self) -> float:
        """Reads ACPI thermal zone temperature in Celsius."""
        if sys.platform != "win32":
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for _, entries in temps.items():
                            for entry in entries:
                                if entry.current:
                                    return round(float(entry.current), 1)
            except Exception:
                pass
            return self.last_temp_c

        try:
            cmd = ['powershell', '-NoProfile', '-Command', 
                   'Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            val = res.stdout.strip()
            if val:
                vals = [float(v) for v in val.split() if v.isdigit()]
                if vals:
                    # Kelvin tenths to Celsius: (tenths - 2732) / 10.0
                    return round((max(vals) - 2732) / 10.0, 1)
        except Exception:
            pass
        return self.last_temp_c


# Singleton instance
load_balancer = SystemLoadBalancer()

if __name__ == "__main__":
    vitals = load_balancer.get_thermal_and_vitals()
    print("Vitals & Thermals:", json.dumps(vitals, indent=2))
    bal = load_balancer.balance_all_jarvis_processes()
    print("Process Balancing:", json.dumps(bal, indent=2))
    throttle = load_balancer.ensure_processor_throttle_cap(95)
    print("Throttle Cap:", json.dumps(throttle, indent=2))
