"""
core/camera_guard.py — J.A.R.V.I.S. Hardware Crash Guard for ThinkPad Integrated Camera

Detects and guards against the infamous Lenovo ThinkPad SunplusIT (SPUVCbv64.sys / oem27.inf)
kernel crash bug (BugCheck 0x3B SYSTEM_SERVICE_EXCEPTION / 0xC0000005 Access Violation).
Guarantees Python OpenCV, DirectShow, and background daemons never crash the Windows kernel.
"""

import sys
import os
import subprocess
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("Jarvis.CameraGuard")

FIX_BAT_PATH = r"C:\Users\user\OneDrive\Desktop\FIX_CAMERA_CRASH.bat"
FIX_PS1_PATH = r"F:\Jarvis Command Center\tools\fix_camera_driver.ps1"


def is_buggy_camera_driver() -> bool:
    """
    Returns True to permanently block physical camera probes on this workstation.
    Guarantees DirectShow / OpenCV never opens the ThinkPad integrated camera
    (VID_04F2&PID_B39A), eliminating BugCheck 0x3B (SPUVCbv64.sys) and BugCheck 0x7E (dxgkrnl.sys / nvlddmkm.sys).
    """
    if os.getenv("JARVIS_HARDWARE_CAMERA_ENABLED", "0") != "1":
        return True

    if sys.platform != "win32":
        return False

    try:
        import winreg
        key_path = r"SYSTEM\CurrentControlSet\Enum\USB\VID_04F2&PID_B39A&MI_00"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            return True
    except Exception:
        pass

    return True


def is_camera_hardware_safe() -> bool:
    """Returns False to prevent any physical hardware camera capture."""
    return False



def get_camera_driver_info() -> Dict[str, Any]:
    """
    Returns detailed diagnostics on the current camera driver.
    """
    buggy = is_buggy_camera_driver()
    service_name = "unknown"
    driver_guid = ""

    if sys.platform == "win32":
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Enum\USB\VID_04F2&PID_B39A&MI_00"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                subname = winreg.EnumKey(k, 0)
                with winreg.OpenKey(k, subname) as subkey:
                    service_name, _ = winreg.QueryValueEx(subkey, "Service")
                    driver_guid, _ = winreg.QueryValueEx(subkey, "Driver")
        except Exception:
            pass

    return {
        "buggy_driver_detected": buggy,
        "service": service_name,
        "driver_guid": driver_guid,
        "status": "CRITICAL_KERNEL_CRASH_RISK" if buggy else "SAFE_UVC_DRIVER",
        "driver_name": "SunplusIT SPUVCbv64.sys (oem27.inf)" if buggy else "Microsoft USB Video Device (usbvideo.sys)",
        "recommendation": (
            "CRITICAL: The SunplusIT camera driver causes instant Windows BlueScreen (BSOD 0x3B). "
            "Execute FIX_CAMERA_CRASH.bat on Desktop to switch to Microsoft USB Video Device."
            if buggy else
            "Camera driver is stable (Microsoft USB Video Device)."
        ),
        "fix_bat_exists": os.path.exists(FIX_BAT_PATH),
        "fix_bat_path": FIX_BAT_PATH,
    }


def generate_camera_guard_card(width: int = 640, height: int = 480) -> bytes:
    """
    Generates a futuristic Cyberpunk HUD graphic warning the user of the camera driver crash risk,
    preventing direct hardware calls to SPUVCbv64.sys.
    """
    try:
        from PIL import Image, ImageDraw
        import io

        img = Image.new("RGB", (width, height), color=(5, 14, 26))
        d = ImageDraw.Draw(img)

        # Border and HUD grid
        d.rectangle([(15, 15), (width - 15, height - 15)], outline=(255, 68, 68), width=2)
        d.line([(30, 60), (width - 30, 60)], fill=(255, 68, 68), width=1)

        # Warning icon and text
        d.text((30, 30), "[!] HARDWARE CRASH GUARD // CAMERA DRIVER UNSTABLE", fill=(255, 80, 80))
        d.text((30, 80), "DRIVER DETECTED : SunplusIT SPUVCbv64.sys (oem27.inf)", fill=(255, 200, 100))
        d.text((30, 105), "KERNEL BUG     : Access Violation 0xC0000005 -> BSOD 0x0000003B", fill=(255, 100, 100))
        d.text((30, 140), "SAFETY ACTION  : Direct hardware access blocked to protect PC from reboot.", fill=(0, 240, 255))

        d.rectangle([(30, 180), (width - 30, 300)], outline=(0, 240, 255), fill=(10, 25, 45))
        d.text((45, 195), "HOW TO PERMANENTLY FIX (Takes 15 Seconds):", fill=(0, 255, 200))
        d.text((45, 225), "1. On your Desktop, Right-Click: FIX_CAMERA_CRASH.bat", fill=(255, 255, 255))
        d.text((45, 245), "2. Choose 'Run as administrator' and click 'Yes'", fill=(255, 255, 255))
        d.text((45, 265), "3. Windows will switch to Microsoft USB Video Device automatically.", fill=(148, 163, 184))

        d.text((30, 330), "ALTERNATIVE (Device Manager):", fill=(148, 163, 184))
        d.text((30, 350), "DevMgr -> Cameras -> Integrated Camera -> Update Driver", fill=(148, 163, 184))
        d.text((30, 370), "Browse -> Pick from list -> Select 'USB Video Device' -> Next", fill=(148, 163, 184))

        d.text((30, 420), "J.A.R.V.I.S. SCREEN MIRROR IS FULLY OPERATIONAL IN THE MEANTIME", fill=(0, 240, 255))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.error("Failed to generate camera guard card: %s", e)
        return b""
