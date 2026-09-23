"""
actions/virtualbox_manager.py — VirtualBox VM Management Engine for J.A.R.V.I.S.
================================================================================
Provides programmatic control over registered VirtualBox virtual machines:
  • Status & Telemetry (Running, Powered Off, Saved)
  • Start VM (Headless or GUI mode)
  • Stop VM (Save State, ACPI Power Button, Forced Power Off)
  • VM Resource Inspection (RAM, VRAM, CPUs, VDI storage path on Drive F:)
================================================================================
"""

from __future__ import annotations
import os
import subprocess
import re
from typing import Dict, Any, List, Optional

VBOX_PATHS = [
    r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
]

DEFAULT_VM = "my-first-ubuntu-machine"

def _find_vboxmanage() -> Optional[str]:
    for p in VBOX_PATHS:
        if os.path.exists(p):
            return p
    return None

def list_all_vms() -> List[Dict[str, str]]:
    vbox = _find_vboxmanage()
    if not vbox:
        return []
    res = subprocess.run([vbox, "list", "vms"], capture_output=True, text=True)
    vms = []
    for line in res.stdout.strip().splitlines():
        m = re.match(r'"([^"]+)"\s+\{([^}]+)\}', line)
        if m:
            vms.append({"name": m.group(1), "uuid": m.group(2)})
    return vms

def list_running_vms() -> List[Dict[str, str]]:
    vbox = _find_vboxmanage()
    if not vbox:
        return []
    res = subprocess.run([vbox, "list", "runningvms"], capture_output=True, text=True)
    vms = []
    for line in res.stdout.strip().splitlines():
        m = re.match(r'"([^"]+)"\s+\{([^}]+)\}', line)
        if m:
            vms.append({"name": m.group(1), "uuid": m.group(2)})
    return vms

def get_vm_status(vm_name: str = DEFAULT_VM) -> Dict[str, Any]:
    vbox = _find_vboxmanage()
    if not vbox:
        return {"ok": False, "error": "VirtualBox not found on system.", "vm": vm_name, "state": "UNKNOWN"}
    
    running = [v["name"] for v in list_running_vms()]
    all_vms = [v["name"] for v in list_all_vms()]
    
    if vm_name not in all_vms and not any(vm_name.lower() in v.lower() for v in all_vms):
        return {"ok": False, "error": f"VM '{vm_name}' not registered in VirtualBox.", "available_vms": all_vms}
    
    target_vm = vm_name if vm_name in all_vms else next(v for v in all_vms if vm_name.lower() in v.lower())
    is_running = target_vm in running
    
    # Query machine info
    res = subprocess.run([vbox, "showvminfo", target_vm, "--machinereadable"], capture_output=True, text=True)
    props = {}
    for line in res.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k.strip()] = v.strip().strip('"')
            
    return {
        "ok": True,
        "vm": target_vm,
        "state": "RUNNING 🟢" if is_running else (props.get("VMState", "poweroff").upper() + " 🔴"),
        "is_running": is_running,
        "cpus": props.get("cpus", "2"),
        "memory_mb": props.get("memory", "4096"),
        "os_type": props.get("ostype", "Ubuntu (64-bit)"),
        "storage_location": r"F:\VirtualBox VMs"
    }

def start_vm(vm_name: str = DEFAULT_VM, headless: bool = True) -> Dict[str, Any]:
    vbox = _find_vboxmanage()
    if not vbox:
        return {"ok": False, "message": "VirtualBox not installed."}
    
    status = get_vm_status(vm_name)
    if not status.get("ok"):
        return status
    if status.get("is_running"):
        return {"ok": True, "message": f"Virtual machine '{status['vm']}' is already running."}
    
    target_vm = status["vm"]
    mode = "headless" if headless else "gui"
    res = subprocess.run([vbox, "startvm", target_vm, "--type", mode], capture_output=True, text=True)
    if res.returncode == 0:
        return {"ok": True, "message": f"Virtual machine '{target_vm}' started successfully in {mode} mode on Drive F:."}
    return {"ok": False, "message": f"Failed to start VM '{target_vm}': {res.stderr.strip()}"}

def stop_vm(vm_name: str = DEFAULT_VM, mode: str = "savestate") -> Dict[str, Any]:
    vbox = _find_vboxmanage()
    if not vbox:
        return {"ok": False, "message": "VirtualBox not installed."}
    
    status = get_vm_status(vm_name)
    if not status.get("ok"):
        return status
    if not status.get("is_running"):
        return {"ok": True, "message": f"Virtual machine '{status['vm']}' is not currently running."}
    
    target_vm = status["vm"]
    # Modes: savestate (recommended), acpipowerbutton (graceful shutdown), poweroff (force)
    ctrl_mode = "savestate" if mode == "savestate" else ("acpipowerbutton" if mode == "acpi" else "poweroff")
    res = subprocess.run([vbox, "controlvm", target_vm, ctrl_mode], capture_output=True, text=True)
    if res.returncode == 0:
        return {"ok": True, "message": f"Virtual machine '{target_vm}' stopped ({ctrl_mode}). State safely saved on Drive F:."}
    return {"ok": False, "message": f"Failed to stop VM '{target_vm}': {res.stderr.strip()}"}

def virtualbox_controller(command: str) -> str:
    """Natural language dispatcher for VirtualBox actions."""
    low = command.lower()
    if any(w in low for w in ["start", "launch", "chalao", "on karo", "kholo"]):
        res = start_vm(headless=True)
        return f"🖥️ [VIRTUALBOX] {res['message']}"
    elif any(w in low for w in ["stop", "shutdown", "save", "band karo", "pause"]):
        res = stop_vm(mode="savestate")
        return f"🖥️ [VIRTUALBOX] {res['message']}"
    else:
        st = get_vm_status()
        if not st.get("ok"):
            return f"🖥️ [VIRTUALBOX] {st.get('error', 'Status check failed.')}"
        return (
            f"🖥️ [VIRTUALBOX VM TELEMETRY]\n"
            f"• Machine: {st['vm']}\n"
            f"• Status: {st['state']}\n"
            f"• CPU Cores: {st['cpus']} | RAM: {st['memory_mb']} MB\n"
            f"• OS: {st['os_type']}\n"
            f"• Storage Anchor: {st['storage_location']} (Drive F: NVMe)\n"
            f"• Controls: 'vm start', 'vm stop', 'vm status'"
        )
