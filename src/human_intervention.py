"""
src/human_intervention.py — Real-Time On-Screen Human Intervention & Captcha Alert Modal
==========================================================================================
Coordinates on-screen intervention dialogues for J.A.R.V.I.S. when manual human input
is required (Cloudflare turnstiles, reCAPTCHA, 2FA OTP codes, or critical confirmations).

Features:
  1. Spawns an on-screen TOPMOST modal window (Tkinter / Win32) centered on the desktop.
  2. Brings the target browser or application window into immediate foreground focus.
  3. Speaks / plays an audible audio chime notifying Master Muhammad Qureshi.
  4. Provides interactive 1-click actions:
     - [I Have Solved It / Done]
     - [Bring Browser to Front]
     - [Switch to 100% Free / Public Feed]
     - [Cancel / Dismiss]
  5. Syncs state with core/human_intervention_gateway.py and WhatsApp dispatch.
==========================================================================================
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("HumanIntervention")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_OWNER_NAME = "Master Muhammad Qureshi"
DEFAULT_OWNER_PHONE = "923468053268"
DEFAULT_OWNER_EMAIL = "futureworldvision842@gmail.com"
FUNDINGPIPS_ACCOUNT_ID = "40000294403"
FUNDINGPIPS_EMAIL = "hamidqureshi872@gmail.com"
FUNDINGPIPS_HOLDER = "Ahmed Qureshi"


def focus_window(window_title: str = "", url: str = "") -> bool:
    """Brings the window matching window_title or opens url in the default browser."""
    try:
        if url:
            webbrowser.open(url)
            time.sleep(0.3)

        if sys.platform == "win32" and window_title:
            user32 = ctypes.windll.user32
            # Search for window title substring
            hwnd_found = None

            def _enum_windows_callback(hwnd, extra):
                nonlocal hwnd_found
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if window_title.lower() in buff.value.lower():
                        hwnd_found = hwnd
                        return False  # stop enumeration
                return True

            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(_enum_windows_callback)
            user32.EnumWindows(enum_proc, 0)

            if hwnd_found:
                SW_RESTORE = 9
                user32.ShowWindow(hwnd_found, SW_RESTORE)
                user32.SetForegroundWindow(hwnd_found)
                return True
    except Exception as exc:
        logger.debug(f"focus_window notice: {exc}")
    return False


def notify_voice(text: str) -> None:
    """Speaks notification text to alert Master Muhammad."""
    def _speak():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            try:
                # Windows system beep fallback
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass
    threading.Thread(target=_speak, daemon=True).start()


def show_onscreen_modal(
    title: str,
    reason: str,
    explanation_ur: str,
    target_url: str = "",
    window_title: str = "",
    account_info: str = "",
    on_resolved: Optional[Callable[[], None]] = None,
    on_free_mode: Optional[Callable[[], None]] = None,
    timeout_sec: int = 180,
) -> None:
    """
    Renders a topmost on-screen modal window to notify Master Muhammad.
    Runs non-blocking in a dedicated thread.
    """
    def _run_gui():
        try:
            import tkinter as tk
            from tkinter import ttk

            root = tk.Tk()
            root.title(f"J.A.R.V.I.S. — {title}")
            root.attributes("-topmost", True)
            root.configure(bg="#0a0f1d")
            root.geometry("560x380")
            root.resizable(False, False)

            # Center on screen
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            x = (root.winfo_screenwidth() // 2) - (w // 2)
            y = (root.winfo_screenheight() // 2) - (h // 2)
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Header Frame
            header = tk.Frame(root, bg="#111827", padx=16, pady=12)
            header.pack(fill="x")

            lbl_sub = tk.Label(
                header,
                text="J.A.R.V.I.S. SOVEREIGN PC ASSISTANT",
                font=("Segoe UI", 9, "bold"),
                fg="#38bdf8",
                bg="#111827"
            )
            lbl_sub.pack(anchor="w")

            lbl_title = tk.Label(
                header,
                text=f"🚨 HUMAN INTERVENTION REQUIRED: {title.upper()}",
                font=("Segoe UI", 12, "bold"),
                fg="#f87171",
                bg="#111827"
            )
            lbl_title.pack(anchor="w")

            # Body Frame
            body = tk.Frame(root, bg="#0a0f1d", padx=20, pady=14)
            body.pack(fill="both", expand=True)

            msg_owner = tk.Label(
                body,
                text=f"Master {DEFAULT_OWNER_NAME}:",
                font=("Segoe UI", 10, "bold"),
                fg="#e2e8f0",
                bg="#0a0f1d"
            )
            msg_owner.pack(anchor="w")

            msg_tech = tk.Label(
                body,
                text=f"• Problem: {reason}",
                font=("Segoe UI", 9),
                fg="#94a3b8",
                bg="#0a0f1d",
                wraplength=510,
                justify="left"
            )
            msg_tech.pack(anchor="w", pady=(2, 6))

            if account_info:
                msg_acc = tk.Label(
                    body,
                    text=f"• Account: {account_info}",
                    font=("Segoe UI", 9, "bold"),
                    fg="#fbbf24",
                    bg="#0a0f1d"
                )
                msg_acc.pack(anchor="w", pady=(0, 6))

            msg_ur = tk.Label(
                body,
                text=f"🎙️ Roman Urdu:\n\"{explanation_ur}\"",
                font=("Segoe UI", 9, "italic"),
                fg="#38bdf8",
                bg="#0a0f1d",
                wraplength=510,
                justify="left"
            )
            msg_ur.pack(anchor="w", pady=(0, 10))

            # Buttons Frame
            btn_frame = tk.Frame(root, bg="#0a0f1d", padx=16, pady=12)
            btn_frame.pack(fill="x", side="bottom")

            def _btn_solved():
                if on_resolved:
                    on_resolved()
                root.destroy()

            def _btn_focus():
                focus_window(window_title or title, target_url)

            def _btn_free():
                if on_free_mode:
                    on_free_mode()
                root.destroy()

            def _btn_dismiss():
                root.destroy()

            btn_solved = tk.Button(
                btn_frame,
                text="✅ Solved & Verified",
                font=("Segoe UI", 9, "bold"),
                bg="#10b981",
                fg="#ffffff",
                activebackground="#059669",
                activeforeground="#ffffff",
                padx=10,
                pady=6,
                command=_btn_solved,
                relief="flat"
            )
            btn_solved.pack(side="left", padx=4)

            btn_focus = tk.Button(
                btn_frame,
                text="🌐 Open / Focus Browser",
                font=("Segoe UI", 9, "bold"),
                bg="#2563eb",
                fg="#ffffff",
                activebackground="#1d4ed8",
                activeforeground="#ffffff",
                padx=10,
                pady=6,
                command=_btn_focus,
                relief="flat"
            )
            btn_focus.pack(side="left", padx=4)

            btn_free = tk.Button(
                btn_frame,
                text="⚡ 100% Free Mode",
                font=("Segoe UI", 9),
                bg="#334155",
                fg="#cbd5e1",
                activebackground="#475569",
                activeforeground="#ffffff",
                padx=8,
                pady=6,
                command=_btn_free,
                relief="flat"
            )
            btn_free.pack(side="left", padx=4)

            btn_cancel = tk.Button(
                btn_frame,
                text="Dismiss",
                font=("Segoe UI", 9),
                bg="#1e293b",
                fg="#94a3b8",
                activebackground="#334155",
                activeforeground="#ffffff",
                padx=8,
                pady=6,
                command=_btn_dismiss,
                relief="flat"
            )
            btn_cancel.pack(side="right", padx=4)

            # Auto close after timeout_sec
            root.after(timeout_sec * 1000, lambda: root.destroy())
            root.mainloop()

        except Exception as e:
            logger.warning(f"On-screen modal GUI notice: {e}")
            # Non-GUI fallback: print to stdout
            print(f"\n[J.A.R.V.I.S. INTERVENTION ALERT]\n• {title}: {reason}\n• Urdu: {explanation_ur}\n")

    threading.Thread(target=_run_gui, daemon=True).start()


class HumanInterventionService:
    """
    Unified manager for human interventions across browser automation,
    financial portals, and system administration.
    """

    def __init__(self):
        self.pending_file = RUNTIME_DIR / "pending_human_requests.json"

    def request_captcha_assistance(
        self,
        target_site: str,
        url: str = "",
        action_blocked: str = "Web scraping or portal login",
        window_title: str = ""
    ) -> Dict[str, Any]:
        """
        Triggered when a Captcha / Cloudflare challenge is detected.
        Pops up modal on screen, brings browser to front, and speaks voice alert.
        """
        req_id = f"CAP-{int(time.time())}"
        reason = f"Cloudflare Turnstile or CAPTCHA detected on {target_site} ({url or 'live page'})."
        explanation_ur = (
            f"Sir, {target_site} par verification challenge aa gaya hai. "
            f"Maine browser screen par samne open kar diya hai. Baraye meherbani checkbox ya captcha solve karein."
        )

        # 1. Bring window to front
        focus_window(window_title or target_site, url)

        # 2. Voice chime
        notify_voice(f"Master Muhammad, captcha verification is required on screen for {target_site}.")

        # 3. Show Topmost On-Screen Modal
        show_onscreen_modal(
            title=f"Captcha Challenge ({target_site})",
            reason=reason,
            explanation_ur=explanation_ur,
            target_url=url,
            window_title=window_title or target_site,
            account_info=f"{DEFAULT_OWNER_NAME} ({DEFAULT_OWNER_EMAIL})",
            on_resolved=lambda: self._mark_resolved(req_id, "Solved on screen by Master Muhammad"),
            on_free_mode=lambda: self._mark_resolved(req_id, "Switched to free alternative")
        )

        # 4. Sync with core/human_intervention_gateway.py if available
        try:
            from core.human_intervention_gateway import HumanInterventionGateway
            gw = HumanInterventionGateway()
            gw.request_captcha_resolution(
                target_site=target_site,
                url=url,
                action_blocked=action_blocked,
                account_username=DEFAULT_OWNER_EMAIL,
                window_title=window_title or target_site
            )
        except Exception as e:
            logger.debug(f"Gateway sync notice: {e}")

        return {
            "ok": True,
            "request_id": req_id,
            "type": "CAPTCHA_CHALLENGE",
            "target_site": target_site,
            "status": "PENDING_HUMAN_ACTION",
            "message": f"On-screen modal opened. Browser brought to foreground for {target_site}."
        }

    def request_2fa_assistance(
        self,
        service_name: str,
        account_username: str = "",
        code_destination: str = "",
        url: str = "",
        window_title: str = ""
    ) -> Dict[str, Any]:
        """
        Triggered when a 2FA OTP code is needed.
        """
        req_id = f"2FA-{int(time.time())}"
        user_display = account_username or DEFAULT_OWNER_EMAIL
        dest_display = code_destination or f"Gmail ({user_display}) / Authenticator"

        reason = f"2FA verification code required to proceed on {service_name}."
        explanation_ur = (
            f"Sir, {service_name} ke liye 2FA/OTP code chahiye. "
            f"Code aapke '{dest_display}' par bheja gaya hai."
        )

        focus_window(window_title or service_name, url)
        notify_voice(f"Master Muhammad, 2FA code is needed for {service_name}.")

        show_onscreen_modal(
            title=f"2FA Code Needed ({service_name})",
            reason=reason,
            explanation_ur=explanation_ur,
            target_url=url,
            window_title=window_title or service_name,
            account_info=f"User: {user_display} | Destination: {dest_display}",
            on_resolved=lambda: self._mark_resolved(req_id, "2FA confirmed by user"),
            on_free_mode=lambda: self._mark_resolved(req_id, "Free alternative selected")
        )

        try:
            from core.human_intervention_gateway import HumanInterventionGateway
            gw = HumanInterventionGateway()
            gw.request_2fa_code(
                service_name=service_name,
                action_blocked=f"Accessing {service_name}",
                account_username=user_display,
                code_destination=dest_display,
                portal_url=url,
                window_title=window_title or service_name
            )
        except Exception as e:
            logger.debug(f"Gateway sync notice: {e}")

        return {
            "ok": True,
            "request_id": req_id,
            "type": "TWO_FACTOR_AUTH",
            "service_name": service_name,
            "status": "PENDING_HUMAN_ACTION",
            "message": f"2FA on-screen alert displayed for {service_name}."
        }

    def _mark_resolved(self, req_id: str, note: str = "") -> None:
        logger.info(f"Human intervention {req_id} marked RESOLVED: {note}")


# Global singleton
human_service = HumanInterventionService()
