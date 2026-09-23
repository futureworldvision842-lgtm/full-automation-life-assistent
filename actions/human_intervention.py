"""
actions/human_intervention.py — Human-in-the-Loop Autonomous Interception & Resolver
=====================================================================================
Enables J.A.R.V.I.S. to:
1. Detect when autonomous tasks (browser scraping, web navigation, 2FA, logins, Cloudflare)
   require human input or CAPTCHA solving.
2. Bring the relevant target window (Chrome, browser, dialog) directly to the foreground.
3. Display a sleek, top-most J.A.R.V.I.S. cybernetic dialog on the Master's desktop.
4. Issue an audio chime/voice announcement to alert Master Muhammad Qureshi.
5. Notify the Master remotely via WhatsApp (+923468053268) and Discord.
6. Seamlessly resume autonomous operations once the human verification is solved.
=====================================================================================
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("HumanIntervention")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent


def bring_window_to_foreground(title_pattern: str = "") -> bool:
    """Finds and brings a window matching title_pattern to the foreground."""
    try:
        import win32gui
        import win32con

        matched_hwnd = None

        def enum_handler(hwnd, extra):
            nonlocal matched_hwnd
            if win32gui.IsWindowVisible(hwnd):
                txt = win32gui.GetWindowText(hwnd)
                if txt and (not title_pattern or title_pattern.lower() in txt.lower()):
                    matched_hwnd = hwnd

        win32gui.EnumWindows(enum_handler, None)

        if matched_hwnd:
            win32gui.ShowWindow(matched_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(matched_hwnd)
            logger.info(f"Brought window (HWND: {matched_hwnd}) matching '{title_pattern}' to foreground.")
            return True
    except Exception as e:
        logger.warning(f"Could not bring window to foreground: {e}")
    return False


def play_intervention_chime():
    """Emits an audible notification alert for Master Muhammad."""
    try:
        import winsound
        # Two-tone J.A.R.V.I.S. wake tone
        winsound.Beep(880, 150)
        time.sleep(0.05)
        winsound.Beep(1320, 250)
    except Exception:
        pass


def notify_channels_intervention(reason: str, task_name: str):
    """Dispatches asynchronous alerts to WhatsApp and Discord."""
    # 1. WhatsApp notification
    try:
        from wa.send_alert import send_whatsapp_message  # type: ignore
        msg = f"⚠️ *[J.A.R.V.I.S. HUMAN INTERVENTION REQUIRED]*\n\nSir, an autonomous operation requires your manual input on-screen:\n• *Task*: {task_name}\n• *Detail*: {reason}\n\nPlease check your desktop screen."
        send_whatsapp_message("923468053268", msg)
    except Exception:
        pass

    # 2. Discord notification
    try:
        from bots.discord_bot import send_channel_message  # type: ignore
        send_channel_message("elite-trade", f"⚠️ **[HUMAN INTERVENTION REQUIRED]**: {task_name} — {reason}")
    except Exception:
        pass


class InterventionDialog:
    """A sleek cybernetic top-most Tkinter modal for Human-in-the-Loop verification."""

    def __init__(self, task_name: str, reason: str, timeout_seconds: int = 180):
        self.task_name = task_name
        self.reason = reason
        self.timeout_seconds = timeout_seconds
        self.resolved = False
        self.remaining = timeout_seconds
        self.root = None

    def show(self) -> bool:
        """Renders the dialog and blocks until user clicks Resolved or timeout expires."""
        try:
            import tkinter as tk
            from tkinter import ttk

            self.root = tk.Tk()
            self.root.title("J.A.R.V.I.S. — HUMAN INTERVENTION REQUIRED")
            self.root.geometry("540x360")
            self.root.configure(bg="#0a0e17")
            self.root.attributes("-topmost", True)
            self.root.resizable(False, False)

            # Center window on screen
            self.root.update_idletasks()
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()
            x = (w - 540) // 2
            y = (h - 360) // 2
            self.root.geometry(f"540x360+{x}+{y}")

            # Header / Arc-Reactor Icon
            header_frame = tk.Frame(self.root, bg="#0d1b2a", height=65)
            header_frame.pack(fill=tk.X, padx=0, pady=0)

            title_lbl = tk.Label(
                header_frame,
                text="⚡ J.A.R.V.I.S. HUMAN ASSISTANCE PROTOCOL",
                font=("Segoe UI", 12, "bold"),
                fg="#00d2ff",
                bg="#0d1b2a"
            )
            title_lbl.pack(pady=10)

            sub_lbl = tk.Label(
                header_frame,
                text="Autonomous Task Intercepted — Human Action Needed",
                font=("Segoe UI", 9),
                fg="#8892b0",
                bg="#0d1b2a"
            )
            sub_lbl.pack(pady=0)

            # Body Card
            body_frame = tk.Frame(self.root, bg="#111c2e", bd=1, relief=tk.SOLID)
            body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

            task_lbl = tk.Label(
                body_frame,
                text=f"🎯 Target Operation: {self.task_name}",
                font=("Segoe UI", 10, "bold"),
                fg="#e6f1ff",
                bg="#111c2e",
                anchor="w"
            )
            task_lbl.pack(fill=tk.X, padx=15, pady=(12, 5))

            reason_lbl = tk.Label(
                body_frame,
                text=f"Reason: {self.reason}\n\nJ.A.R.V.I.S. has brought the browser/app window forward.\nPlease solve the CAPTCHA, 2FA, or verification on screen,\nthen click the confirmation button below.",
                font=("Segoe UI", 9),
                fg="#a8b2d1",
                bg="#111c2e",
                justify=tk.LEFT,
                anchor="w"
            )
            reason_lbl.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

            # Countdown Timer Label
            self.timer_lbl = tk.Label(
                body_frame,
                text=f"⏳ Auto-timeout in {self.remaining}s",
                font=("Segoe UI", 8, "italic"),
                fg="#ffbd2e",
                bg="#111c2e"
            )
            self.timer_lbl.pack(pady=(0, 10))

            # Action Buttons Frame
            btn_frame = tk.Frame(self.root, bg="#0a0e17")
            btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

            def on_resolved():
                self.resolved = True
                if self.root:
                    self.root.destroy()

            def on_cancel():
                self.resolved = False
                if self.root:
                    self.root.destroy()

            btn_resolve = tk.Button(
                btn_frame,
                text="✅ Solved — Resume J.A.R.V.I.S.",
                font=("Segoe UI", 10, "bold"),
                bg="#00b4d8",
                fg="#ffffff",
                activebackground="#0077b6",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                padx=15,
                pady=6,
                command=on_resolved
            )
            btn_resolve.pack(side=tk.RIGHT, padx=5)

            btn_cancel = tk.Button(
                btn_frame,
                text="Abort Task",
                font=("Segoe UI", 9),
                bg="#333a4d",
                fg="#ccd6f6",
                activebackground="#232936",
                activeforeground="#ccd6f6",
                relief=tk.FLAT,
                padx=10,
                pady=6,
                command=on_cancel
            )
            btn_cancel.pack(side=tk.RIGHT, padx=5)

            # Timer tick loop
            def tick():
                if self.remaining > 0 and not self.resolved:
                    self.remaining -= 1
                    if self.timer_lbl:
                        self.timer_lbl.config(text=f"⏳ Auto-timeout in {self.remaining}s")
                    if self.root:
                        self.root.after(1000, tick)
                else:
                    if self.root:
                        self.root.destroy()

            self.root.after(1000, tick)
            self.root.mainloop()
            return self.resolved

        except Exception as e:
            logger.error(f"Failed to launch UI dialog: {e}")
            return False


def request_human_intervention(
    task_name: str,
    reason: str,
    window_title_pattern: str = "",
    timeout_seconds: int = 180
) -> Dict[str, Any]:
    """
    Core entry point to request human assistance.
    
    1. Brings target window to foreground.
    2. Plays audible chime.
    3. Notifies WhatsApp and Discord.
    4. Displays top-most intervention modal dialog.
    5. Returns dict with status and resolution flag.
    """
    logger.info(f"[HUMAN INTERVENTION] Initiated for task: '{task_name}' — Reason: '{reason}'")
    t0 = time.time()

    # 1. Bring target window to front
    if window_title_pattern:
        bring_window_to_foreground(window_title_pattern)
    else:
        # Default: try Chrome or MT5
        bring_window_to_foreground("Chrome")

    # 2. Sound the chime
    threading.Thread(target=play_intervention_chime, daemon=True).start()

    # 3. Notify remote channels
    threading.Thread(target=notify_channels_intervention, args=(reason, task_name), daemon=True).start()

    # 4. Show top-most UI
    dialog = InterventionDialog(task_name, reason, timeout_seconds=timeout_seconds)
    resolved = dialog.show()

    elapsed = round(time.time() - t0, 1)
    logger.info(f"[HUMAN INTERVENTION] Completed in {elapsed}s. Resolved: {resolved}")

    return {
        "ok": resolved,
        "resolved": resolved,
        "task_name": task_name,
        "reason": reason,
        "elapsed_seconds": elapsed,
        "status": "RESOLVED_BY_USER" if resolved else "TIMEOUT_OR_ABORTED"
    }


if __name__ == "__main__":
    print("Testing Human Intervention alert (5s test)...")
    res = request_human_intervention(
        task_name="Cloudflare CAPTCHA Verification",
        reason="Cloudflare Turnstile challenge detected on ChatGPT web interface.",
        window_title_pattern="Chrome",
        timeout_seconds=10
    )
    print("Result:", res)
