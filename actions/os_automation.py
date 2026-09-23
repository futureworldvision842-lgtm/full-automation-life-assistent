"""
actions/os_automation.py
===============================================================================
OS Sovereign Computer Control & Bilingual Automation Suite:
- Application Lifecycle Management (launch, switch, inspect, gracefully terminate)
- Dynamic Windows Registry & System Application Discovery Engine
- System Operations & Power Controls Integration
- File & Workspace Automation Integration
- Bilingual Roman Urdu & English Natural Language Dispatcher with Execution Receipts
===============================================================================
"""

import os
import sys
import re
import time
import uuid
import ctypes
import shutil
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# Import modularized subsystems
from actions.bilingual_parser import parse_bilingual_command, APP_ALIASES_MAP
from actions.system_control import handle_system_control_action, get_system_diagnostics
from actions.workspace_tools import handle_workspace_action


_CURRENT_OS = platform.system()
_BASE_DIR = Path(__file__).resolve().parent.parent

# Common Windows Application Executable Paths & Registry Locators
_STATIC_WINDOWS_APP_PATHS: Dict[str, List[str]] = {
    "MetaTrader 5": [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\FTMO MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal.exe",
        "terminal64.exe"
    ],
    "MetaTrader 4": [
        r"C:\Program Files (x86)\MetaTrader 4\terminal.exe",
        r"C:\Program Files\MetaTrader 4\terminal.exe",
        "terminal.exe"
    ],
    "Google Chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "chrome.exe", "chrome"
    ],
    "Mozilla Firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        "firefox.exe", "firefox"
    ],
    "Microsoft Edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "msedge.exe", "msedge"
    ],
    "Brave Browser": [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        "brave.exe", "brave"
    ],
    "Visual Studio Code": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe"),
        "code.cmd", "code.exe", "code"
    ],
    "Cursor": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe"),
        "cursor.exe", "cursor"
    ],
    "Discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
        "Discord.exe", "discord"
    ],
    "Telegram": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        "Telegram.exe", "telegram"
    ],
    "WhatsApp": [
        os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
        "whatsapp:"
    ],
    "Spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "spotify.exe", "spotify:"
    ],
    "Terminal": [
        "wt.exe", "powershell.exe", "cmd.exe"
    ],
    "Command Prompt": [
        "cmd.exe"
    ],
    "PowerShell": [
        "powershell.exe", "pwsh.exe"
    ],
    "Notepad": [
        "notepad.exe"
    ],
    "Calculator": [
        "calc.exe"
    ],
    "Task Manager": [
        "taskmgr.exe"
    ],
    "File Explorer": [
        "explorer.exe"
    ],
    "Windows Settings": [
        "ms-settings:"
    ],
    "Paint": [
        "mspaint.exe"
    ],
    "Obsidian": [
        os.path.expandvars(r"%LOCALAPPDATA%\Obsidian\Obsidian.exe"),
        "obsidian.exe"
    ],
    "Postman": [
        os.path.expandvars(r"%LOCALAPPDATA%\Postman\Postman.exe"),
        "postman.exe"
    ],
    "VLC Media Player": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        "vlc.exe"
    ],
    "CapCut": [
        os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\*\CapCut.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\CapCut\CapCut.exe"),
        "CapCut.exe", "capcut"
    ],
    "Tor Browser": [
        os.path.expandvars(r"%USERPROFILE%\Desktop\Tor Browser\Browser\firefox.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tor Browser\Browser\firefox.exe"),
        "firefox.exe"
    ],
    "UrbanVPN": [
        os.path.expandvars(r"%PROGRAMFILES%\UrbanVPN\UrbanVPN.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\UrbanVPN\UrbanVPN.exe"),
        "urbanvpn.exe"
    ],
    "Opera Air Browser": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\launcher.exe"),
        "opera.exe"
    ],
    "MetaEditor 5": [
        r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
        "metaeditor64.exe"
    ]
}


def _discover_windows_registry_apps() -> Dict[str, str]:
    """Queries Windows Registry App Paths keys to discover installed applications."""
    discovered: Dict[str, str] = {}
    if _CURRENT_OS != "Windows":
        return discovered

    try:
        import winreg
        for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root_key, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                    num_subkeys, _, _ = winreg.QueryInfoKey(key)
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                val, _ = winreg.QueryValueEx(subkey, "")
                                if val and Path(val).exists():
                                    clean_key = subkey_name.lower().replace(".exe", "")
                                    discovered[clean_key] = val
                        except Exception:
                            continue
            except Exception:
                continue
    except Exception:
        pass
    return discovered


_REGISTRY_APPS = _discover_windows_registry_apps()


# =============================================================================
# 1. Application Management Lifecycle
# =============================================================================

def _find_running_app_processes(app_name_or_alias: str) -> List[Any]:
    """Finds all running psutil.Process instances matching an app name or alias."""
    if not _PSUTIL_AVAILABLE:
        return []

    matched = []
    target_clean = app_name_or_alias.lower().replace(" ", "").replace(".exe", "")
    canonical = APP_ALIASES_MAP.get(app_name_or_alias.lower(), app_name_or_alias).lower().replace(" ", "").replace(".exe", "")

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            raw_proc_name = proc.info.get("name") or ""
            name_clean = raw_proc_name.lower().replace(" ", "").replace(".exe", "")
            if not name_clean or len(name_clean) < 3:
                continue
            if target_clean == name_clean or canonical == name_clean or target_clean in name_clean or canonical in name_clean:
                matched.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matched


def launch_app(app_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Launches a desktop application by canonical name or alias.
    """
    raw_name = (app_name or "").strip()

    # Intercept Chrome profile and web destinations
    low_raw = raw_name.lower()
    if any(w in low_raw for w in ["hamid", "hamid 872", "hamid872", "funding pips", "fundingpips"]):
        try:
            from perception.chrome_adeel_navigator import CHROME_EXE_CANDIDATES
            chrome_exe = next((c for c in CHROME_EXE_CANDIDATES if c.exists()), CHROME_EXE_CANDIDATES[0])
            dest_url = "https://app.fundingpips.com/login"
            if "youtube" in low_raw:
                dest_url = "https://youtube.com"
            prof_dir = "Profile 2"
            prof_name = "Hamid 872"
            cmd = [str(chrome_exe), f"--profile-directory={prof_dir}", dest_url]
            subprocess.Popen(cmd, close_fds=True)
            return {
                "ok": True,
                "success": True,
                "status": "success",
                "app": "Google Chrome",
                "profile": prof_dir,
                "url": dest_url,
                "message": f"Opened Google Chrome ({prof_name}) to {dest_url}."
            }
        except Exception:
            pass
    elif (any(w in low_raw for w in ["profile", "adeel", "vision"]) and any(w in low_raw for w in ["chrome", "browser", "chatgpt", "gemini", "claude", "deepseek"])) or ("chatgpt" in low_raw and "chrome" in low_raw):
        try:
            from perception.chrome_adeel_navigator import get_chrome_adeel_navigator
            nav = get_chrome_adeel_navigator()
            dest_url = "https://chatgpt.com"
            if "gemini" in low_raw:
                dest_url = "https://gemini.google.com"
            elif "claude" in low_raw:
                dest_url = "https://claude.ai"
            elif "deepseek" in low_raw:
                dest_url = "https://chat.deepseek.com"
            prof_dir = nav.profile_info.profile_directory_name or "Profile 42"
            cmd = [str(nav.chrome_exe), f"--profile-directory={prof_dir}", dest_url]
            subprocess.Popen(cmd, close_fds=True)
            return {
                "ok": True,
                "success": True,
                "status": "success",
                "app": "Google Chrome",
                "profile": prof_dir,
                "url": dest_url,
                "message": f"Opened Google Chrome ({nav.profile_info.display_name}) to {dest_url}."
            }
        except Exception as e:
            pass

    # Clean leading/trailing Urdu sentence particles
    cleaned_name = re.sub(r"\b(kero|karo|chalao|kholdo|khol do|khol|open kero|os main|us main|main|mein|par)\b", "", raw_name, flags=re.IGNORECASE).strip()
    clean_target = cleaned_name if cleaned_name else raw_name
    canonical = APP_ALIASES_MAP.get(clean_target.lower(), clean_target)
    extra_args = args or []

    running_procs = _find_running_app_processes(canonical)
    already_running = len(running_procs) > 0

    candidates = _STATIC_WINDOWS_APP_PATHS.get(canonical, [canonical, f"{canonical}.exe"])

    reg_clean = canonical.lower().replace(" ", "")
    if reg_clean in _REGISTRY_APPS:
        candidates = [_REGISTRY_APPS[reg_clean]] + candidates
    for k, v in _REGISTRY_APPS.items():
        if k in raw_name.lower() or raw_name.lower() in k:
            if v not in candidates:
                candidates = [v] + candidates

    launched = False
    launched_path = None
    spawned_pid = None

    if _CURRENT_OS == "Windows":
        for cand in candidates:
            if cand.startswith("ms-settings:") or cand.endswith(":"):
                try:
                    os.startfile(cand)
                    launched = True
                    launched_path = cand
                    break
                except Exception:
                    continue

            cand_expanded = os.path.expandvars(cand)
            if "*" in cand_expanded:
                import glob
                globbed = glob.glob(cand_expanded)
                if globbed and Path(globbed[0]).exists():
                    cand_expanded = globbed[0]

            cand_path = Path(cand_expanded)
            if cand_path.exists():
                try:
                    cmd = [str(cand_path)] + extra_args
                    p = subprocess.Popen(cmd, shell=False)
                    spawned_pid = p.pid
                    launched = True
                    launched_path = str(cand_path)
                    break
                except Exception:
                    pass

        if not launched:
            for cand in candidates:
                binary = shutil.which(cand)
                if binary:
                    try:
                        cmd = [binary] + extra_args
                        p = subprocess.Popen(cmd, shell=False)
                        spawned_pid = p.pid
                        launched = True
                        launched_path = binary
                        break
                    except Exception:
                        pass

        # Check Desktop and OneDrive Desktop .lnk shortcuts
        if not launched:
            for desk_dir in [Path(os.path.expanduser("~")) / "OneDrive" / "Desktop", Path(os.path.expanduser("~")) / "Desktop"]:
                if desk_dir.exists():
                    for lnk in desk_dir.glob("*.lnk"):
                        if canonical.lower() in lnk.name.lower() or raw_name.lower() in lnk.name.lower():
                            try:
                                os.startfile(str(lnk))
                                launched = True
                                launched_path = str(lnk)
                                break
                            except Exception:
                                pass
                if launched:
                    break

        if not launched:
            try:
                os.startfile(canonical)
                launched = True
                launched_path = canonical
            except Exception:
                try:
                    os.startfile(f"{raw_name}.exe")
                    launched = True
                    launched_path = f"{raw_name}.exe"
                except Exception as e:
                    return {
                        "status": "error",
                        "app": canonical,
                        "already_running": already_running,
                        "detail": f"Failed to launch '{canonical}': {e}"
                    }

    else:
        try:
            cmd = [canonical] + extra_args
            p = subprocess.Popen(cmd)
            spawned_pid = p.pid
            launched = True
            launched_path = canonical
        except Exception as e:
            return {
                "status": "error",
                "app": canonical,
                "detail": f"Failed to spawn application on {_CURRENT_OS}: {e}"
            }

    return {
        "status": "success",
        "action": "app_launch",
        "app": canonical,
        "launched_path": launched_path,
        "spawned_pid": spawned_pid,
        "already_running": already_running,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": f"Successfully launched '{canonical}' (PID: {spawned_pid or 'attached'}, Already running: {already_running})."
    }


def switch_app(app_name: str) -> Dict[str, Any]:
    """
    Brings the existing window of an application to the foreground.
    """
    canonical = APP_ALIASES_MAP.get(app_name.lower(), app_name)

    if _CURRENT_OS == "Windows":
        activated = False
        matched_title = None
        matched_hwnd = None

        try:
            user32 = ctypes.windll.user32
            found_windows = []

            def _enum_windows_callback(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        if title:
                            found_windows.append((hwnd, title))
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            user32.EnumWindows(EnumWindowsProc(_enum_windows_callback), 0)

            cand_terms = [canonical.lower(), app_name.lower()]
            for hwnd, title in found_windows:
                title_lower = title.lower()
                if any(term in title_lower for term in cand_terms):
                    SW_RESTORE = 9
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    activated = True
                    matched_title = title
                    matched_hwnd = hwnd
                    break
        except Exception:
            pass

        if not activated:
            try:
                ps_script = f'(New-Object -ComObject WScript.Shell).AppActivate("{canonical}")'
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=2)
                if "True" in res.stdout:
                    activated = True
                    matched_title = canonical
            except Exception:
                pass

        if activated:
            return {
                "status": "success",
                "action": "app_switch",
                "app": canonical,
                "window_title": matched_title,
                "hwnd": matched_hwnd,
                "detail": f"Switched focus to '{canonical}' ({matched_title or 'active'})."
            }

    return {
        "status": "error",
        "action": "app_switch",
        "app": canonical,
        "detail": f"Could not find an active visible window for '{canonical}' to switch to."
    }


def inspect_apps(filter_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Inspects running desktop applications, window titles, memory, and CPU usage.
    """
    if not _PSUTIL_AVAILABLE:
        return {
            "status": "error",
            "detail": "psutil library unavailable for application inspection.",
            "applications": []
        }

    canonical_filter = APP_ALIASES_MAP.get(filter_name.lower(), filter_name).lower() if filter_name else None
    apps = []

    window_titles_by_pid: Dict[int, List[str]] = {}
    if _CURRENT_OS == "Windows":
        try:
            user32 = ctypes.windll.user32
            def _enum_win(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()
                        if title:
                            pid = ctypes.wintypes.DWORD()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            window_titles_by_pid.setdefault(pid.value, []).append(title)
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            user32.EnumWindows(EnumWindowsProc(_enum_win), 0)
        except Exception:
            pass

    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = proc.info
            pid = info["pid"]
            name = info["name"]
            titles = window_titles_by_pid.get(pid, [])
            mem_mb = round(info["memory_info"].rss / (1024**2), 1) if info.get("memory_info") else 0.0

            if canonical_filter:
                match = (canonical_filter in name.lower()) or any(canonical_filter in t.lower() for t in titles)
                if not match:
                    continue
            else:
                is_known = any(k.lower() in name.lower() for k in APP_ALIASES_MAP.keys())
                if not titles and not is_known:
                    continue

            apps.append({
                "pid": pid,
                "name": name,
                "window_titles": titles,
                "memory_mb": mem_mb,
                "cpu_percent": info.get("cpu_percent") or 0.0,
                "status": "RUNNING"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "status": "success",
        "action": "app_inspect",
        "total_count": len(apps),
        "filter": filter_name,
        "applications": apps,
        "detail": f"Inspected {len(apps)} running desktop application(s) matching filter: '{filter_name or 'all'}'."
    }


def terminate_app(app_name: str, force: bool = False, graceful_timeout: float = 1.0) -> Dict[str, Any]:
    """
    Gracefully requests an application to terminate, falling back to force kill.
    """
    canonical = APP_ALIASES_MAP.get(app_name.lower(), app_name)
    procs = _find_running_app_processes(canonical)

    if not procs:
        return {
            "status": "success",
            "action": "app_kill",
            "app": canonical,
            "terminated_count": 0,
            "terminated_pids": [],
            "detail": f"No running instances of '{canonical}' found."
        }

    terminated_pids = []
    for p in procs:
        try:
            pid = p.pid
            p.terminate()
            terminated_pids.append(pid)
        except Exception:
            pass

    if _PSUTIL_AVAILABLE and terminated_pids:
        try:
            gone, alive = psutil.wait_procs(procs, timeout=graceful_timeout)
            if alive and force:
                for p in alive:
                    try:
                        p.kill()
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "status": "success",
        "action": "app_kill",
        "app": canonical,
        "terminated_count": len(terminated_pids),
        "terminated_pids": terminated_pids,
        "force_used": force,
        "detail": f"Terminated {len(terminated_pids)} process instance(s) of '{canonical}' (PIDs: {terminated_pids})."
    }


# =============================================================================
# 2. Master OS Sovereign Unified Dispatcher
# =============================================================================

def execute_pc_action(
    command_str: str,
    origin: str = "cli",
    is_owner: bool = True
) -> Dict[str, Any]:
    """
    Authoritative OS Sovereign Automation Handler complying with PROJECT.md Interface Contract:
    - Parses bilingual Roman Urdu & English natural language commands
    - Executes application management, system controls, workspace ops, and diagnostics
    - Enforces owner security authorization on privileged operations
    - Returns structured execution receipt dict:
      {
          "status": "success" | "error" | "blocked",
          "action": "app_launch" | "app_kill" | "app_switch" | "app_inspect" | "system_vol" | "screen_capture" | "file_op" | "diagnostics" | "system_power",
          "detail": str,
          "stdout_summary": str,
          "bilingual_translation": {"input_lang": "ur|en", "intent": str},
          "execution_receipt": { ... }
      }
    """
    start_time = time.perf_counter()
    receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
    ts_utc = datetime.now(timezone.utc).isoformat()

    # Step 1: Parse bilingual command
    parsed = parse_bilingual_command(command_str)
    action = parsed.get("action", "diagnostics")
    intent = parsed.get("intent", action)
    target = parsed.get("target")
    parameters = parsed.get("parameters", {})
    input_lang = parsed.get("input_lang", "en")
    translated_intent = parsed.get("translated_intent", intent)

    # Step 2: Security & Authorization Guard
    PRIVILEGED_ACTIONS = {"system_power", "app_kill"}
    if not is_owner and action in PRIVILEGED_ACTIONS:
        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        receipt = {
            "receipt_id": receipt_id,
            "timestamp": ts_utc,
            "origin": origin,
            "is_owner": is_owner,
            "execution_time_ms": exec_ms,
            "action": action,
            "target": target,
            "parameters": parameters,
            "result": {"status": "blocked", "reason": "unauthorized_origin"}
        }
        return {
            "status": "blocked",
            "action": action,
            "detail": f"Security policy: Unprivileged execution blocked for action '{action}'.",
            "stdout_summary": f"[SECURITY BLOCKED] Action '{action}' requires owner privileges.",
            "bilingual_translation": {
                "input_lang": input_lang,
                "intent": translated_intent
            },
            "execution_receipt": receipt
        }

    # Step 3: Dispatch to Subsystems
    result_data: Dict[str, Any] = {}

    try:
        if action == "app_launch":
            result_data = launch_app(app_name=target or parameters.get("canonical", command_str))
        elif action == "app_kill":
            force = parameters.get("force", False)
            result_data = terminate_app(app_name=target or parameters.get("canonical", command_str), force=force)
        elif action == "app_switch":
            result_data = switch_app(app_name=target or parameters.get("canonical", command_str))
        elif action == "app_inspect":
            result_data = inspect_apps(filter_name=parameters.get("filter"))
        elif action in {"system_vol", "screen_capture", "diagnostics", "system_power"}:
            result_data = handle_system_control_action(action=action, target=target, parameters=parameters)
        elif action == "file_op":
            result_data = handle_workspace_action(action=action, target=target, parameters=parameters)
        else:
            result_data = {
                "status": "error",
                "detail": f"Unrecognized OS automation action: '{action}'."
            }
    except Exception as e:
        result_data = {
            "status": "error",
            "detail": f"Exception during execution: {e}"
        }

    exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
    final_status = result_data.get("status", "success")
    detail_msg = result_data.get("detail", f"Action {action} completed successfully.")

    receipt = {
        "receipt_id": receipt_id,
        "timestamp": ts_utc,
        "origin": origin,
        "is_owner": is_owner,
        "execution_time_ms": exec_ms,
        "action": action,
        "target": target,
        "parameters": parameters,
        "result": result_data
    }

    return {
        "status": final_status,
        "action": action,
        "detail": detail_msg,
        "stdout_summary": f"[{action.upper()}] {detail_msg} ({exec_ms}ms)",
        "bilingual_translation": {
            "input_lang": input_lang,
            "intent": translated_intent
        },
        "execution_receipt": receipt
    }
