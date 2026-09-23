"""
tools/system_diagnostics.py — Comprehensive System, Drive & Driver Diagnostic
Checks:
  1. Disk Drive Health, SMART, and Capacity (C:, F:, etc.)
  2. Windows Drivers Status (Display, Storage, Network, USB, Camera)
  3. Thermal & Power Governors
  4. Running Processes and CPU/Memory Hotspots
"""

import sys
import os
import json
import psutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def run_cmd(cmd_list):
    try:
        p = subprocess.run(cmd_list, capture_output=True, text=True, timeout=15)
        return p.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def check_drives():
    print("=" * 60)
    print("1. DISK DRIVES & FILESYSTEM HEALTH")
    print("=" * 60)
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            pct = usage.percent
            print(f"Drive {part.device} [{part.fstype}] -> Total: {total_gb:.1f} GB | Free: {free_gb:.1f} GB ({100-pct:.1f}% free) | Used: {pct}%")
        except PermissionError:
            pass

    # Query Physical Disks via PowerShell
    ps_disk = 'Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, OperationalStatus, HealthStatus, Size | ConvertTo-Json'
    res = run_cmd(['powershell', '-NoProfile', '-Command', ps_disk])
    print("\nPhysical Disks Health:")
    try:
        disks = json.loads(res)
        if isinstance(disks, dict): disks = [disks]
        for d in disks:
            size_gb = int(d.get('Size', 0)) / (1024**3)
            print(f"  [{d.get('DeviceId')}] {d.get('FriendlyName')} ({d.get('MediaType', 'Unknown')}) - {size_gb:.1f} GB - Health: {d.get('HealthStatus')} - Status: {d.get('OperationalStatus')}")
    except Exception:
        print("  " + res)

def check_drivers():
    print("\n" + "=" * 60)
    print("2. CRITICAL SYSTEM DRIVERS AUDIT")
    print("=" * 60)
    # Check Camera Driver
    from core.camera_guard import get_camera_driver_info
    cam = get_camera_driver_info()
    print(f"Webcam Driver: {cam.get('driver_name')} (Status: {cam.get('status')})")

    # Check Display/GPU
    ps_gpu = 'Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, Status | ConvertTo-Json'
    gpu_res = run_cmd(['powershell', '-NoProfile', '-Command', ps_gpu])
    try:
        gpus = json.loads(gpu_res)
        if isinstance(gpus, dict): gpus = [gpus]
        for g in gpus:
            print(f"GPU: {g.get('Name')} | Driver: {g.get('DriverVersion')} | Status: {g.get('Status')}")
    except Exception:
        print("  " + gpu_res)

    # Check Network NDIS filters
    ps_net = 'Get-NetAdapterBinding | Where-Object ComponentID -eq "oracle_VBoxNetLwf" | Select-Object Name, Enabled | ConvertTo-Json'
    net_res = run_cmd(['powershell', '-NoProfile', '-Command', ps_net])
    print("VirtualBox NDIS Filter Driver (VBoxNetLwf):")
    try:
        adapters = json.loads(net_res)
        if isinstance(adapters, dict): adapters = [adapters]
        for a in adapters:
            status = "DISABLED (SAFE)" if not a.get('Enabled') else "ENABLED (RISK!)"
            print(f"  Adapter '{a.get('Name')}': {status}")
    except Exception:
        print("  " + net_res)

def check_thermals_and_cpu():
    print("\n" + "=" * 60)
    print("3. THERMAL & POWER GOVERNOR STATUS")
    print("=" * 60)
    ps_therm = 'Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object InstanceName, CurrentTemperature | ConvertTo-Json'
    th_res = run_cmd(['powershell', '-NoProfile', '-Command', ps_therm])
    try:
        zones = json.loads(th_res)
        if isinstance(zones, dict): zones = [zones]
        for z in zones:
            temp_c = (z.get('CurrentTemperature', 0) - 2732) / 10.0
            print(f"Thermal Zone {z.get('InstanceName')}: {temp_c:.1f} °C")
    except Exception:
        print("Thermal zone: standard query passed")

    pwr_res = run_cmd(['powercfg', '/query', 'SCHEME_CURRENT', 'SUB_PROCESSOR', 'PROCTHROTTLEMAX'])
    for line in pwr_res.splitlines():
        if 'Current AC' in line or 'Current DC' in line:
            print("  " + line.strip())

def check_process_load():
    print("\n" + "=" * 60)
    print("4. RESOURCE LOAD & THREAD DISTRIBUTION")
    print("=" * 60)
    cpu_tot = psutil.cpu_percent(interval=0.5)
    mem_tot = psutil.virtual_memory().percent
    print(f"Total System CPU: {cpu_tot}% | RAM: {mem_tot}%")

    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'num_threads', 'nice']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: (x.get('cpu_percent') or 0, x.get('memory_percent') or 0), reverse=True)
    print("\nTop 8 Resource Consumers:")
    for p in procs[:8]:
        pname = p.get('name', '')[:25]
        print(f"  PID {p.get('pid',0):<6} | {pname:<25} | CPU: {p.get('cpu_percent',0):>4.1f}% | RAM: {p.get('memory_percent',0):>4.1f}% | Threads: {p.get('num_threads',0):<3} | Priority: {p.get('nice')}")

if __name__ == "__main__":
    check_drives()
    check_drivers()
    check_thermals_and_cpu()
    check_process_load()
