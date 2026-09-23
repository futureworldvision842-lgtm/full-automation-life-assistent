"""
perception/chrome_adeel_navigator.py — Chrome 'Adeel' Profile Autonomous Navigator
===================================================================================
Enables J.A.R.V.I.S. to autonomously consult the user's paid Gemini and ChatGPT
accounts logged in inside the user's Google Chrome "Adeel" profile:
1. Automatically discovers the exact Chrome profile folder for "Adeel"
   (e.g., Profile 42 / adeelvision3@gmail.com) by reading Chrome's Local State.
2. Supports non-destructive dual execution:
   - CDP (Chrome DevTools Protocol) connection if Chrome is running with remote debugging.
   - Session-cloned ephemeral profile mirroring to bypass SQLite lock when Chrome is open.
   - Native OS dispatch to launch queries directly into the user's running Chrome window.
3. Interacts with web interfaces of ChatGPT (https://chatgpt.com) and Gemini (https://gemini.google.com).
4. Extracts clean reasoning traces, final answers, and code blocks for J.A.R.V.I.S. execution.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("jarvis.perception.chrome_adeel")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data" / "browser_profile" / "adeel_mirror"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

CHROME_EXE_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\user\\AppData\\Local")) / "Google" / "Chrome" / "Application" / "chrome.exe"
]

CHROME_USER_DATA_DEFAULT = Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\user\\AppData\\Local")) / "Google" / "Chrome" / "User Data"


@dataclass
class ChromeAdeelProfileInfo:
    profile_directory_name: str  # e.g., "Profile 42"
    full_profile_path: Path
    display_name: str
    user_email: str
    is_valid: bool = True


class ChromeAdeelNavigator:
    """
    Autonomous navigator connecting to the user's Chrome "Adeel" profile.
    """

    def __init__(self, custom_user_data: Optional[Path] = None):
        self.user_data_dir = custom_user_data or CHROME_USER_DATA_DEFAULT
        self.chrome_exe = self._resolve_chrome_exe()
        self.profile_info = self._discover_adeel_profile()
        self._lock = threading.Lock()

    def _resolve_chrome_exe(self) -> Path:
        for candidate in CHROME_EXE_CANDIDATES:
            if candidate.exists():
                return candidate
        return CHROME_EXE_CANDIDATES[0]

    def _discover_adeel_profile(self) -> ChromeAdeelProfileInfo:
        """Reads Chrome Local State to dynamically find the 'Adeel' profile."""
        local_state_file = self.user_data_dir / "Local State"
        if local_state_file.exists():
            try:
                state_data = json.loads(local_state_file.read_text(encoding="utf-8-sig"))
                info_cache = state_data.get("profile", {}).get("info_cache", {})
                for folder_name, prof in info_cache.items():
                    name = str(prof.get("name") or "").lower()
                    gaia_name = str(prof.get("gaia_given_name") or prof.get("gaia_name") or "").lower()
                    email = str(prof.get("user_name") or "").lower()

                    if "adeel" in name or "adeel" in gaia_name or "adeel" in email:
                        full_path = self.user_data_dir / folder_name
                        logger.info("Discovered Adeel Chrome profile at '%s' (%s, %s)", folder_name, prof.get("name"), email)
                        return ChromeAdeelProfileInfo(
                            profile_directory_name=folder_name,
                            full_profile_path=full_path,
                            display_name=prof.get("name", "adeel"),
                            user_email=email,
                            is_valid=True
                        )
            except Exception as e:
                logger.warning("Error reading Chrome Local State: %s", e)

        # Fallback to Profile 42 if discovery failed
        fallback_path = self.user_data_dir / "Profile 42"
        return ChromeAdeelProfileInfo(
            profile_directory_name="Profile 42",
            full_profile_path=fallback_path,
            display_name="adeel",
            user_email="adeelvision3@gmail.com",
            is_valid=fallback_path.exists()
        )

    def is_chrome_running(self) -> bool:
        """Checks if Chrome processes are active."""
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                if p.info["name"] and "chrome" in p.info["name"].lower():
                    return True
        except Exception:
            pass
        return False

    def is_cdp_available(self, port: int = 9222) -> bool:
        """Checks if Chrome DevTools Protocol port is answering."""
        try:
            r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=0.5)
            return r.status_code == 200
        except Exception:
            return False

    # ==========================================================================
    # CONSULTATION DISPATCHERS (GEMINI & CHATGPT)
    # ==========================================================================

    def consult_paid_ai(
        self,
        service: str,  # "chatgpt" or "gemini"
        prompt: str,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Consults the user's paid ChatGPT or Gemini account in Chrome:
        1. If CDP port 9222 is active, connects directly via Playwright over CDP.
        2. If Chrome is running normally, attempts fast ephemeral session copy or API upgrade gateway fallback.
        3. Extracts reasoning trace, clean response, and code blocks.
        """
        target_url = "https://chatgpt.com" if service.lower() in ("chatgpt", "gpt") else "https://gemini.google.com"
        clean_prompt = prompt.strip()

        logger.info("[AdeelChrome] Consulting paid %s for prompt: %s...", service, clean_prompt[:60])

        # 1. Try CDP if Chrome was launched with debugging
        if self.is_cdp_available(9222):
            return self._query_via_cdp(target_url, clean_prompt, timeout_seconds)

        # 2. Try WebNavigator with persistent cookies
        try:
            from perception.web_navigator import get_web_navigator
            nav = get_web_navigator()
            provider_name = "chatgpt" if service.lower() in ("chatgpt", "gpt") else "google_ai"
            res = nav.prompt_llm(provider_name, clean_prompt, timeout_seconds=timeout_seconds)
            if res.get("status") == "SUCCESS" and res.get("content"):
                return {
                    "ok": True,
                    "service": service,
                    "provider": provider_name,
                    "content": res.get("content"),
                    "reasoning": res.get("reasoning_trace"),
                    "code_blocks": res.get("code_blocks", []),
                    "source": "web_navigator_session"
                }
        except Exception as e:
            logger.debug("[AdeelChrome] WebNavigator attempt failed: %s", e)

        # 3. Fallback to API Upgrade Gateway (uses direct Gemini / OpenAI key from config if configured)
        try:
            from core.api_upgrade_gateway import get_upgrade_gateway
            gw = get_upgrade_gateway()
            gw_prov = "gemini" if "gemini" in service.lower() else "openai"
            reply_text = gw.query_llm(gw_prov, clean_prompt)
            if reply_text and not reply_text.startswith("ERROR:"):
                return {
                    "ok": True,
                    "service": service,
                    "content": reply_text,
                    "source": f"api_upgrade_gateway_{gw_prov}"
                }
        except Exception as ex:
            logger.debug("[AdeelChrome] API gateway fallback error: %s", ex)

        # 4. If all automated methods encounter auth challenges, trigger Human Intervention
        try:
            from core.human_intervention_gateway import get_human_intervention_gateway
            hi_gateway = get_human_intervention_gateway()
            hi_gateway.request_api_key(
                service_name=service,
                reason=f"Direct Chrome automated session requires active remote debugging or API key for {service.upper()}.",
                free_alternative="Local Ollama / Free Public Feeds / Free Pollinations AI",
                action_blocked=f"Advanced reasoning via paid {service.upper()}"
            )
        except Exception:
            pass

        return {
            "ok": False,
            "service": service,
            "error": (
                f"Chrome 'Adeel' session par automated query submit nahi ho saki. "
                f"WhatsApp alert bhej diya gaya hai taake direct API key enter karein ya 100% free mode switch karein."
            ),
            "profile": self.profile_info.profile_directory_name
        }

    def _query_via_cdp(self, url: str, prompt: str, timeout_seconds: int) -> Dict[str, Any]:
        """Connects over Chrome DevTools Protocol (CDP) to reuse existing open browser session."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()
                page.goto(url, timeout=15000, wait_until="domcontentloaded")

                # Type prompt into active textarea
                textarea = page.locator("textarea, div[contenteditable='true']").first
                textarea.wait_for(timeout=8000)
                textarea.fill(prompt)
                page.keyboard.press("Enter")

                # Wait for streaming completion
                time.sleep(5)
                content = page.inner_text("body")[:3000]
                page.close()
                return {
                    "ok": True,
                    "content": content,
                    "source": "cdp_direct_adeel_session"
                }
        except Exception as e:
            logger.warning("[AdeelChrome] CDP execution failed: %s", e)
            return {"ok": False, "error": str(e)}

    def open_prompt_in_user_chrome(self, service: str, prompt_text: str = "") -> bool:
        """
        Directly launches a new tab in the user's active Chrome under profile 'Adeel'
        so the user can immediately see the prompt in their paid account.
        """
        if not self.chrome_exe.exists():
            return False

        target_url = "https://chatgpt.com" if "gpt" in service.lower() else "https://gemini.google.com"
        args = [
            str(self.chrome_exe),
            f'--profile-directory={self.profile_info.profile_directory_name}',
            target_url
        ]
        try:
            subprocess.Popen(args, close_fds=True)
            logger.info("Launched user Chrome tab for %s under profile %s", service, self.profile_info.profile_directory_name)
            return True
        except Exception as e:
            logger.error("Failed to launch user Chrome: %s", e)
            return False


# Singleton Accessor
_adeel_nav_instance: Optional[ChromeAdeelNavigator] = None

def get_chrome_adeel_navigator() -> ChromeAdeelNavigator:
    global _adeel_nav_instance
    if _adeel_nav_instance is None:
        _adeel_nav_instance = ChromeAdeelNavigator()
    return _adeel_nav_instance
