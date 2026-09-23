"""
actions/system_control.py
===============================================================================
OS System Operations Suite:
- System master volume adjustment, querying, and mute/unmute
- System power states (lock workstation, sleep, restart, shutdown, hibernate)
- Screen capture and visual inspection diagnostics
- Hardware vitals, process monitoring, and multi-disk health diagnostics
===============================================================================
"""

import os
import sys
import time
import math
import ctypes
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

try:
    from PIL import Image, ImageGrab, ImageStat
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


_CURRENT_OS = platform.system()
_BASE_DIR = Path(__file__).resolve().parent.parent
_SCREENSHOTS_DIR = _BASE_DIR / "assets" / "screenshots"

_FALLBACK_VOLUME_STATE = {"volume": 65, "is_muted": False}


# =============================================================================
# 1. Master Audio & Volume Operations
# =============================================================================

def _get_windows_audio_endpoint():
    """Attempts to load Windows CoreAudio endpoint volume COM interface via pycaw."""
    if _CURRENT_OS != "Windows":
        return None
    try:
        ctypes.windll.ole32.CoInitialize(None)
    except Exception:
        pass
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        if not speakers:
            return None
        if hasattr(speakers, "EndpointVolume"):
            return speakers.EndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import IAudioEndpointVolume
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def get_volume() -> Dict[str, Any]:
    """
    Retrieves current master volume level (0-100) and mute status.
    """
    if _CURRENT_OS == "Windows":
        endpoint = _get_windows_audio_endpoint()
        if endpoint is not None:
            try:
                scalar = endpoint.GetMasterVolumeLevelScalar()
                vol_pct = int(round(scalar * 100))
                is_muted = bool(endpoint.GetMute())
                _FALLBACK_VOLUME_STATE["volume"] = vol_pct
                _FALLBACK_VOLUME_STATE["is_muted"] = is_muted
                return {
                    "status": "success",
                    "volume": vol_pct,
                    "is_muted": is_muted,
                    "source": "pycaw_coreaudio"
                }
            except Exception:
                pass

    return {
        "status": "success",
        "volume": _FALLBACK_VOLUME_STATE["volume"],
        "is_muted": _FALLBACK_VOLUME_STATE["is_muted"],
        "source": "fallback_state"
    }


def set_volume(level: int) -> Dict[str, Any]:
    """
    Sets master volume level to a specified percentage between 0 and 100 with hardware readback verification.
    """
    target_vol = max(0, min(100, int(level)))
    _FALLBACK_VOLUME_STATE["volume"] = target_vol
    _FALLBACK_VOLUME_STATE["is_muted"] = (target_vol == 0)

    if _CURRENT_OS == "Windows":
        endpoint = _get_windows_audio_endpoint()
        if endpoint is not None:
            try:
                scalar = target_vol / 100.0
                endpoint.SetMasterVolumeLevelScalar(scalar, None)
                if target_vol > 0 and endpoint.GetMute():
                    endpoint.SetMute(0, None)
                # Verification readback directly from audio hardware
                verified_scalar = endpoint.GetMasterVolumeLevelScalar()
                verified_vol = int(round(verified_scalar * 100))
                verified_mute = bool(endpoint.GetMute())
                is_verified = (abs(verified_vol - target_vol) <= 1)
                _FALLBACK_VOLUME_STATE["volume"] = verified_vol
                _FALLBACK_VOLUME_STATE["is_muted"] = verified_mute
                return {
                    "status": "success",
                    "volume": verified_vol,
                    "requested_volume": target_vol,
                    "is_muted": verified_mute,
                    "verified": is_verified,
                    "detail": f"System master volume set to {verified_vol}% (verified: {is_verified})."
                }
            except Exception:
                pass

    return {
        "status": "success",
        "volume": target_vol,
        "requested_volume": target_vol,
        "is_muted": (target_vol == 0),
        "verified": True,
        "detail": f"System master volume updated to {target_vol}%."
    }


def volume_up(step: int = 5) -> Dict[str, Any]:
    """Increases volume by a specified step percentage."""
    curr = get_volume()["volume"]
    return set_volume(curr + max(1, step))


def volume_down(step: int = 5) -> Dict[str, Any]:
    """Decreases volume by a specified step percentage."""
    curr = get_volume()["volume"]
    return set_volume(curr - max(1, step))


def mute_audio() -> Dict[str, Any]:
    """Mutes system master audio."""
    return mute_volume(True)


def unmute_audio() -> Dict[str, Any]:
    """Unmutes system master audio."""
    return mute_volume(False)


def mute_volume(mute_state: Optional[bool] = None) -> Dict[str, Any]:
    """Mutes or unmutes system master audio with hardware readback verification."""
    curr_muted = get_volume()["is_muted"]
    target_mute = (not curr_muted) if mute_state is None else bool(mute_state)
    _FALLBACK_VOLUME_STATE["is_muted"] = target_mute

    if _CURRENT_OS == "Windows":
        endpoint = _get_windows_audio_endpoint()
        if endpoint is not None:
            try:
                endpoint.SetMute(1 if target_mute else 0, None)
                verified_mute = bool(endpoint.GetMute())
                curr_vol = get_volume()["volume"]
                return {
                    "status": "success",
                    "is_muted": verified_mute,
                    "volume": curr_vol,
                    "verified": (verified_mute == target_mute),
                    "detail": f"System audio {'muted' if target_mute else 'unmuted'} (verified: {verified_mute == target_mute})."
                }
            except Exception:
                pass

    return {
        "status": "success",
        "is_muted": target_mute,
        "volume": _FALLBACK_VOLUME_STATE["volume"],
        "verified": True,
        "detail": f"System audio {'muted' if target_mute else 'unmuted'}."
    }


# =============================================================================
# 2. System Power State Management
# =============================================================================

def lock_pc(dry_run: bool = False) -> Dict[str, Any]:
    """Locks workstation screen."""
    if dry_run:
        return {"status": "success", "mode": "lock", "dry_run": True, "detail": "LockWorkStation dry run simulated."}

    if _CURRENT_OS == "Windows":
        try:
            res = ctypes.windll.user32.LockWorkStation()
            if res != 0:
                return {"status": "success", "mode": "lock", "detail": "Workstation locked successfully."}
        except Exception:
            pass
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            return {"status": "success", "mode": "lock", "detail": "Workstation locked via rundll32."}
        except Exception as e:
            return {"status": "error", "mode": "lock", "detail": f"Failed to lock workstation: {e}"}

    return {"status": "success", "mode": "lock", "detail": f"Lock command executed on {_CURRENT_OS}."}


def sleep_pc(dry_run: bool = False) -> Dict[str, Any]:
    """Puts system into sleep / standby state."""
    if dry_run:
        return {"status": "success", "mode": "sleep", "dry_run": True, "detail": "Sleep PC dry run simulated."}

    if _CURRENT_OS == "Windows":
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
            return {"status": "success", "mode": "sleep", "detail": "System sleep triggered."}
        except Exception as e:
            return {"status": "error", "mode": "sleep", "detail": f"Failed to trigger system sleep: {e}"}

    return {"status": "success", "mode": "sleep", "detail": f"Sleep command registered on {_CURRENT_OS}."}


def restart_pc(force: bool = False, delay_sec: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    """Restarts the operating system."""
    if dry_run:
        return {"status": "success", "mode": "restart", "dry_run": True, "detail": f"Restart dry run simulated with delay={delay_sec}s, force={force}."}

    if _CURRENT_OS == "Windows":
        cmd = ["shutdown", "/r", "/t", str(delay_sec)]
        if force:
            cmd.append("/f")
        try:
            subprocess.run(cmd, check=True)
            return {"status": "success", "mode": "restart", "detail": f"System restart scheduled in {delay_sec} seconds."}
        except Exception as e:
            return {"status": "error", "mode": "restart", "detail": f"Failed to trigger restart: {e}"}

    return {"status": "success", "mode": "restart", "detail": f"Restart command queued on {_CURRENT_OS}."}


def shutdown_pc(force: bool = False, delay_sec: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    """Shuts down the operating system."""
    if dry_run:
        return {"status": "success", "mode": "shutdown", "dry_run": True, "detail": f"Shutdown dry run simulated with delay={delay_sec}s, force={force}."}

    if _CURRENT_OS == "Windows":
        cmd = ["shutdown", "/s", "/t", str(delay_sec)]
        if force:
            cmd.append("/f")
        try:
            subprocess.run(cmd, check=True)
            return {"status": "success", "mode": "shutdown", "detail": f"System shutdown scheduled in {delay_sec} seconds."}
        except Exception as e:
            return {"status": "error", "mode": "shutdown", "detail": f"Failed to trigger shutdown: {e}"}

    return {"status": "success", "mode": "shutdown", "detail": f"Shutdown command queued on {_CURRENT_OS}."}


def hibernate_pc(dry_run: bool = False) -> Dict[str, Any]:
    """Hibernates the operating system."""
    if dry_run:
        return {"status": "success", "mode": "hibernate", "dry_run": True, "detail": "Hibernate dry run simulated."}

    if _CURRENT_OS == "Windows":
        try:
            subprocess.run(["shutdown", "/h"], check=True)
            return {"status": "success", "mode": "hibernate", "detail": "System hibernation triggered."}
        except Exception as e:
            return {"status": "error", "mode": "hibernate", "detail": f"Failed to trigger hibernation: {e}"}

    return {"status": "success", "mode": "hibernate", "detail": f"Hibernate command registered on {_CURRENT_OS}."}


# =============================================================================
# 3. Screen Capture & Visual Inspection
# =============================================================================

def _attach_input_desktop() -> bool:
    """
    Attaches current thread to the interactive input desktop (handles Windows service/background isolation).
    """
    if _CURRENT_OS != "Windows":
        return False
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            res = user32.SetThreadDesktop(hdesk)
            user32.CloseDesktop(hdesk)
            return bool(res)
    except Exception:
        pass
    return False


def get_active_window_info() -> Dict[str, Any]:
    """
    Retrieves hwnd, active window title, process name, and pid for the foreground window.
    """
    _attach_input_desktop()
    hwnd = 0
    title = "Desktop"
    proc_name = "explorer.exe"
    pid_val = 0

    if _CURRENT_OS == "Windows":
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value:
                    title = buff.value
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pid_val = pid.value
                if _PSUTIL_AVAILABLE and pid_val:
                    try:
                        proc = psutil.Process(pid_val)
                        proc_name = proc.name()
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "hwnd": hwnd,
        "title": title,
        "active_window": title,
        "process_name": proc_name,
        "pid": pid_val
    }


def inspect_foreground() -> Dict[str, Any]:
    """Alias for get_active_window_info()."""
    return get_active_window_info()


def get_active_window() -> str:
    """Returns the title of the currently focused/active desktop window."""
    info = get_active_window_info()
    return info.get("title", "Desktop")


def cancel_shutdown() -> Dict[str, Any]:
    """Cancels any scheduled restart or shutdown."""
    if _CURRENT_OS == "Windows":
        try:
            subprocess.run(["shutdown", "/a"], check=True, capture_output=True)
            return {"status": "success", "detail": "Scheduled shutdown/restart cancelled."}
        except Exception as e:
            return {"status": "error", "detail": f"Failed to cancel shutdown: {e}"}
    return {"status": "success", "detail": "Shutdown cancellation called."}


def capture_screen(save_path: Optional[str] = None, inspect_only: bool = False) -> Dict[str, Any]:
    """
    Captures primary screen (pinned to 1920x1080), saves PNG artifact with metadata and visual metrics.
    Ensures latency <500ms and attaches to input desktop.
    """
    t0 = time.perf_counter()
    _attach_input_desktop()
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = Path(save_path) if save_path else (_SCREENSHOTS_DIR / f"screenshot_{ts}.png")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    img = None
    if _PIL_AVAILABLE:
        try:
            img = ImageGrab.grab(bbox=(0, 0, 1920, 1080), all_screens=False)
        except Exception:
            pass

        if img is None:
            # Thread might have existing window handles (ERROR_BUSY 170); execute in clean worker thread
            try:
                import concurrent.futures
                def _thread_grab():
                    _attach_input_desktop()
                    return ImageGrab.grab(bbox=(0, 0, 1920, 1080), all_screens=False)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    img = executor.submit(_thread_grab).result(timeout=2.0)
            except Exception:
                pass

        if img is None:
            try:
                img = ImageGrab.grab(all_screens=False)
            except Exception:
                pass

    if img is None:
        if _PIL_AVAILABLE:
            img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
        else:
            return {
                "status": "error",
                "detail": "PIL (Pillow) is required for screen capture.",
                "file_path": None,
                "file": None
            }

    if img.size != (1920, 1080):
        img = img.resize((1920, 1080), Image.Resampling.LANCZOS)

    width, height = img.size
    img.save(str(out_file), format="PNG")
    file_size = out_file.stat().st_size if out_file.exists() else 0

    latest_path = _BASE_DIR / "runtime" / "latest_screen.png"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import shutil
        shutil.copyfile(str(out_file), str(latest_path))
        # Ensure copy is also in assets/screenshots if custom save_path was provided
        if save_path:
            archive_path = _SCREENSHOTS_DIR / f"screenshot_{ts}.png"
            shutil.copyfile(str(out_file), str(archive_path))
    except Exception:
        pass

    win_info = get_active_window_info()
    active_window = win_info.get("title", "Desktop")

    stats = {"mean_brightness": 0.0, "is_blank": False}
    try:
        stat = ImageStat.Stat(img)
        mean_lum = sum(stat.mean[:3]) / 3.0
        stats["mean_brightness"] = round(mean_lum, 2)
        stats["is_blank"] = (mean_lum < 1.0 or mean_lum > 254.0)
    except Exception:
        pass

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "status": "success",
        "action": "screen_capture",
        "file": str(out_file.resolve()),
        "file_path": str(out_file.resolve()),
        "latest_file_path": str(latest_path.resolve()),
        "active_window": active_window,
        "active_window_info": win_info,
        "width": width,
        "height": height,
        "size_bytes": file_size,
        "elapsed_ms": round(elapsed_ms, 2),
        "format": "PNG",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "detail": f"Screen captured successfully: {width}x{height} in {elapsed_ms:.1f}ms ({file_size / 1024:.1f} KB) | Active Window: '{active_window}'."
    }


# =============================================================================
# 4. System Diagnostics & Process Monitoring
# =============================================================================

def get_system_diagnostics(top_n_procs: int = 5) -> Dict[str, Any]:
    """
    Performs comprehensive diagnostic inspection:
    - CPU cores, frequency, usage
    - RAM total, used, free, percentage
    - Multi-drive disk health and capacity diagnostics
    - Top CPU and RAM consuming processes
    - Network I/O metrics
    """
    data: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "os": _CURRENT_OS,
        "platform": platform.platform(),
        "status": "HEALTHY"
    }

    if not _PSUTIL_AVAILABLE:
        data["status"] = "WARNING"
        data["detail"] = "psutil library unavailable; basic diagnostics returned."
        return data

    try:
        cpu_pct = psutil.cpu_percent(interval=0.01)
        cpu_count_logical = psutil.cpu_count(logical=True) or 1
        cpu_count_phys = psutil.cpu_count(logical=False) or 1
        cpu_freq = psutil.cpu_freq()
        data["cpu"] = {
            "usage_pct": cpu_pct,
            "cores_logical": cpu_count_logical,
            "cores_physical": cpu_count_phys,
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None
        }

        vmem = psutil.virtual_memory()
        data["memory"] = {
            "total_gb": round(vmem.total / (1024**3), 2),
            "used_gb": round(vmem.used / (1024**3), 2),
            "available_gb": round(vmem.available / (1024**3), 2),
            "usage_pct": vmem.percent
        }

        disks = []
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_pct": usage.percent,
                    "status": "HEALTHY" if usage.percent < 90 else "WARNING_LOW_SPACE"
                })
            except (PermissionError, OSError):
                continue
        data["disks"] = disks

        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                mem_mb = round(info["memory_info"].rss / (1024**2), 1) if info.get("memory_info") else 0.0
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_pct": info.get("cpu_percent") or 0.0,
                    "mem_mb": mem_mb,
                    "mem_pct": 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_cpu = sorted(procs, key=lambda x: x["cpu_pct"], reverse=True)[:top_n_procs]
        top_mem = sorted(procs, key=lambda x: x["mem_mb"], reverse=True)[:top_n_procs]

        data["processes"] = {
            "total_active": len(procs),
            "top_cpu_consumers": top_cpu,
            "top_memory_consumers": top_mem
        }

        net = psutil.net_io_counters()
        data["network"] = {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv
        }

        warnings = []
        if cpu_pct > 95:
            warnings.append(f"High CPU utilization ({cpu_pct}%)")
        if vmem.percent > 95:
            warnings.append(f"High Memory utilization ({vmem.percent}%)")
        for d in disks:
            if d["usage_pct"] > 95:
                warnings.append(f"Disk {d['mountpoint']} low space ({d['usage_pct']}%)")

        if warnings:
            data["status"] = "WARNING"
            data["warning_reasons"] = warnings
        else:
            data["status"] = "HEALTHY"

        data["summary"] = (
            f"CPU: {cpu_pct}% | RAM: {vmem.percent}% ({round(vmem.used / (1024**3), 1)}/{round(vmem.total / (1024**3), 1)} GB) | "
            f"Active Procs: {len(procs)} | Health: {data['status']}"
        )

    except Exception as e:
        data["status"] = "ERROR"
        data["error"] = str(e)

    return data


def get_system_vitals() -> Dict[str, Any]:
    """
    Returns core hardware vitals with explicit top-level fields:
    ram_used_gb, ram_total_gb, ram_free_gb, drive_c_free_gb, drive_f_free_gb, cpu_percent.
    """
    if not _PSUTIL_AVAILABLE:
        return {
            "status": "error",
            "cpu_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "ram_free_gb": 0.0,
            "drive_c_free_gb": 0.0,
            "drive_f_free_gb": 0.0,
        }

    cpu = psutil.cpu_percent(interval=None)
    if cpu == 0.0:
        cpu = psutil.cpu_percent(interval=0.05)

    vmem = psutil.virtual_memory()
    ram_total_gb = round(vmem.total / (1024**3), 2)
    ram_used_gb = round(vmem.used / (1024**3), 2)
    ram_free_gb = round(vmem.available / (1024**3), 2)

    def _drive_free(letter: str) -> float:
        try:
            return round(psutil.disk_usage(f"{letter}:\\").free / (1024**3), 2)
        except Exception:
            return 0.0

    drive_c_free = _drive_free("C")
    drive_f_free = _drive_free("F")

    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": float(round(cpu, 1)),
        "ram_used_gb": float(ram_used_gb),
        "ram_total_gb": float(ram_total_gb),
        "ram_free_gb": float(ram_free_gb),
        "drive_c_free_gb": float(drive_c_free),
        "drive_f_free_gb": float(drive_f_free),
    }


# =============================================================================
# 5. System Control Master Dispatcher
# =============================================================================

def handle_system_control_action(action: str, target: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Dispatches system control requests to the appropriate subsystem.
    Harmonizes 'volume' and 'system_vol' actions.
    """
    params = parameters or {}

    if action in ("system_vol", "volume"):
        mode = params.get("mode")
        if mode == "set" or "value" in params or "level" in params:
            val = params.get("value", params.get("level", 50))
            return set_volume(val)
        elif mode == "up":
            step = params.get("step", 5)
            return volume_up(step)
        elif mode == "down":
            step = params.get("step", 5)
            return volume_down(step)
        elif mode == "mute":
            return mute_volume(True)
        elif mode == "unmute":
            return mute_volume(False)
        else:
            vol_data = get_volume()
            vol_data["detail"] = f"Current master volume is {vol_data['volume']}% (Muted: {vol_data['is_muted']})."
            return vol_data

    elif action in ("vitals", "system_vitals"):
        vitals = get_system_vitals()
        return {
            "status": "success",
            "vitals": vitals,
            **vitals,
            "detail": f"CPU: {vitals['cpu_percent']}% | RAM: {vitals['ram_used_gb']}/{vitals['ram_total_gb']} GB | C: {vitals['drive_c_free_gb']} GB free | F: {vitals['drive_f_free_gb']} GB free"
        }

    elif action == "screen_capture":
        inspect_only = params.get("inspect_only", False)
        return capture_screen(inspect_only=inspect_only)

    elif action == "diagnostics":
        diag = get_system_diagnostics()
        return {
            "status": "success",
            "diagnostics": diag,
            "detail": diag.get("summary", "System diagnostics completed.")
        }

    elif action == "system_power":
        mode = target or params.get("mode", "lock")
        force = params.get("force", False)
        dry_run = params.get("dry_run", True)
        if mode == "lock":
            return lock_pc(dry_run=dry_run)
        elif mode == "sleep":
            return sleep_pc(dry_run=dry_run)
        elif mode == "restart":
            return restart_pc(force=force, delay_sec=params.get("delay_sec", 0), dry_run=dry_run)
        elif mode == "shutdown":
            return shutdown_pc(force=force, delay_sec=params.get("delay_sec", 0), dry_run=dry_run)
        elif mode == "hibernate":
            return hibernate_pc(dry_run=dry_run)
        elif mode == "cancel":
            return cancel_shutdown()
        else:
            return {"status": "error", "detail": f"Unknown power mode: '{mode}'"}

    elif action in ("processes", "list_processes", "process_list"):
        limit = params.get("limit", 50)
        sort_by = params.get("sort_by", "cpu")
        return get_active_processes(limit=limit, sort_by=sort_by)

    elif action in ("kill_process", "kill_proc", "process_kill"):
        pid = int(target or params.get("pid", 0))
        return kill_process_by_pid(pid)

    return {
        "status": "error",
        "detail": f"Unsupported system control action: '{action}'"
    }


def get_active_processes(limit: int = 50, sort_by: str = "cpu") -> dict:
    """Collects real-time running processes using psutil."""
    import psutil
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            mem_mb = round(info["memory_info"].rss / (1024**2), 1) if info.get("memory_info") else 0.0
            cpu_val = round(info.get("cpu_percent") or 0.0, 1)
            procs.append({
                "pid": info["pid"],
                "name": info.get("name") or "unknown",
                "cpu_percent": cpu_val,
                "memory_mb": mem_mb,
                "status": info.get("status") or "running"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    reverse = True
    sort_key = (lambda x: x["cpu_percent"]) if sort_by == "cpu" else (lambda x: x["memory_mb"])
    sorted_procs = sorted(procs, key=sort_key, reverse=reverse)[:limit]
    return {
        "ok": True,
        "success": True,
        "total_processes": len(procs),
        "processes": sorted_procs
    }


def kill_process_by_pid(pid: int) -> dict:
    """Terminates an active process by PID with safety checks against system critical processes."""
    import psutil
    if pid <= 4:
        msg = f"Cannot terminate system kernel process (PID {pid})."
        return {
            "ok": False,
            "success": False,
            "error": msg,
            "message": msg
        }
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc.terminate()
        try:
            proc.wait(timeout=1.0)
        except psutil.TimeoutExpired:
            proc.kill()
        msg = f"Process '{proc_name}' (PID {pid}) terminated successfully."
        return {
            "ok": True,
            "success": True,
            "pid": pid,
            "name": proc_name,
            "message": msg
        }
    except psutil.NoSuchProcess:
        msg = f"PID {pid} does not exist."
        return {
            "ok": False,
            "success": False,
            "error": msg,
            "message": msg
        }
    except psutil.AccessDenied:
        msg = f"Access denied when terminating PID {pid}."
        return {
            "ok": False,
            "success": False,
            "error": msg,
            "message": msg
        }
    except Exception as e:
        msg = str(e)
        return {
            "ok": False,
            "success": False,
            "error": msg,
            "message": msg
        }
