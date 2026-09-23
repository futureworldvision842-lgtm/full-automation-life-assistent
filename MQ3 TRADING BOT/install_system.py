"""
Windows Real System Installer & Auto-Startup Configurator
=========================================================
Registers JARVIS + Trading Bot in Windows Task Scheduler
so both auto-start at Windows login with admin privileges.
"""

import os
import sys
import subprocess
import ctypes
import winreg
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SystemInstaller")

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def relaunch_as_admin():
    """Re-launch this script with administrator privileges."""
    logger.info("Requesting Administrator elevation...")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", PYTHON_EXE,
        f'"{os.path.abspath(__file__)}"', BOT_DIR, 1
    )
    sys.exit(0)


def create_task_scheduler_task(task_name: str, script_path: str, args: str = "") -> bool:
    """Register a Windows Task Scheduler task that runs at login."""
    cmd = (
        f'schtasks /create /tn "{task_name}" '
        f'/tr "{PYTHON_EXE} \\"{script_path}\\" {args}" '
        f'/sc ONLOGON /rl HIGHEST /f'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        logger.info(f"[Task Scheduler] Created: {task_name}")
        return True
    else:
        logger.error(f"[Task Scheduler] Failed: {task_name} — {result.stderr.strip()}")
        return False


def add_to_startup_registry(name: str, script_path: str, args: str = "") -> bool:
    """Add entry to Windows Registry HKCU Run for user-level startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        value = f'"{PYTHON_EXE}" "{script_path}" {args}'
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        logger.info(f"[Registry Startup] Added: {name} -> {value}")
        return True
    except Exception as e:
        logger.error(f"[Registry Startup] Failed: {name} — {e}")
        return False


def create_windows_shortcut(name: str, script_path: str, args: str = "", icon_path: str = "") -> bool:
    """Create a desktop shortcut using PowerShell."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, f"{name}.lnk")

    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{PYTHON_EXE}'
$Shortcut.Arguments = '"{script_path}" {args}'
$Shortcut.WorkingDirectory = '{BOT_DIR}'
$Shortcut.WindowStyle = 1
$Shortcut.Description = '{name}'
$Shortcut.Save()
"""
    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.info(f"[Shortcut] Created on Desktop: {name}.lnk")
        return True
    else:
        logger.error(f"[Shortcut] Failed: {name} — {result.stderr.strip()}")
        return False


def install_all():
    logger.info("=" * 60)
    logger.info("  TRADING BOT + JARVIS — WINDOWS REAL SYSTEM INSTALLER")
    logger.info("=" * 60)

    bot_script   = os.path.join(BOT_DIR, "run.py")
    jarvis_script = os.path.join(BOT_DIR, "run_jarvis.py")

    results = {}

    # 1. Task Scheduler — Trading Bot (runs at login, highest privileges)
    results["bot_task"] = create_task_scheduler_task(
        task_name="TradingBot_AI_25k",
        script_path=bot_script,
        args="--live"
    )

    # 2. Task Scheduler — Jarvis Full Power V7
    results["jarvis_task"] = create_task_scheduler_task(
        task_name="Jarvis_FullPower_V7",
        script_path=jarvis_script,
        args="--poll 20"
    )

    # 3. Registry Startup — Trading Bot (user-level fallback)
    results["bot_registry"] = add_to_startup_registry(
        name="AI_TradingBot_25k",
        script_path=bot_script,
        args="--live"
    )

    # 4. Registry Startup — Jarvis
    results["jarvis_registry"] = add_to_startup_registry(
        name="Jarvis_FullPower_V7",
        script_path=jarvis_script,
        args="--poll 20"
    )

    # 5. Desktop Shortcuts
    results["bot_shortcut"] = create_windows_shortcut(
        name="AI Trading Bot (LIVE)",
        script_path=bot_script,
        args="--live"
    )
    results["jarvis_shortcut"] = create_windows_shortcut(
        name="JARVIS Full Power V7",
        script_path=jarvis_script,
        args="--poll 20"
    )

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("  INSTALLATION SUMMARY")
    logger.info("=" * 60)
    for name, ok in results.items():
        status = "INSTALLED" if ok else "FAILED"
        logger.info(f"  {name:30s}: {status}")

    passed = sum(results.values())
    logger.info(f"\n  {passed}/{len(results)} components installed successfully.")
    logger.info("=" * 60)
    return results


if __name__ == "__main__":
    if not is_admin():
        logger.warning("Not running as Administrator. Requesting elevation...")
        relaunch_as_admin()
    else:
        install_all()
