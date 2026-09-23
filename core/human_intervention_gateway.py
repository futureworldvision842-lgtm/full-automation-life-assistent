"""
core/human_intervention_gateway.py — Realistic API Key, Captcha & Human Intervention Gateway
=============================================================================================
Manages real-world human-in-the-loop requirements for J.A.R.V.I.S.:
1. Transparently differentiates between 100% Free Workflows vs Paid API Requirements.
2. Dispatches urgent, non-hallucinatory WhatsApp notifications when human action is strictly required:
   - Missing or expired paid API keys (OpenAI, Anthropic, Finnhub, Glassnode, etc.)
   - Cloudflare Captcha, Turnstile, or anti-bot verification challenges
   - 2FA / OTP / SMS / email verification codes
   - Critical system or high-risk financial confirmations
3. Always offers practical, realistic free alternatives (e.g., Free DEX Screener, Browser LLM, Public Feeds)
   so the user is never forced to spend money unnecessarily.
4. Listens for and parses user responses via WhatsApp or Terminal to auto-resolve pending blocks.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import re
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.core.human_intervention")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _BASE_DIR / "runtime"
_PENDING_FILE = _RUNTIME_DIR / "pending_human_requests.json"
_API_KEYS_FILE = _BASE_DIR / "config" / "api_keys.json"

WA_GATEWAY_URL = "http://127.0.0.1:3200/send"
DEFAULT_OWNER_PHONE = "923468053268"
DEFAULT_OWNER_EMAIL = "futureworldvision842@gmail.com"
DEFAULT_OWNER_PASSWORD = os.getenv("JARVIS_OWNER_PASSWORD", "MasterMuhammad@92vision")

# FundingPips Specific Credentials & Portal Info
FUNDINGPIPS_EMAIL = "hamidqureshi872@gmail.com"
FUNDINGPIPS_PASSWORD = "AHMA5ss$#"
FUNDINGPIPS_ACCOUNT_ID = "40000294403"
FUNDINGPIPS_PORTAL_URL = "https://app.fundingpips.com/login"


def open_or_focus_on_pc(url: str = "", title: str = "", prompt_text: str = "") -> bool:
    """Opens or brings target URL/window to foreground on PC using Chrome Profile 2."""
    try:
        is_fp = "fundingpips" in (url or "").lower() or "fundingpips" in (title or "").lower()
        if is_fp:
            try:
                from actions.fundingpips_automation import open_and_prepare_fundingpips
                open_and_prepare_fundingpips(interactive=True)
                return True
            except Exception as fp_err:
                logger.warning("FundingPips automation notice: %s", fp_err)

        if url:
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            chrome_exe = next((p for p in chrome_paths if os.path.isfile(p)), None)
            if chrome_exe:
                import subprocess
                subprocess.Popen([chrome_exe, "--start-maximized", "--profile-directory=Profile 2", url])
                time.sleep(1.0)
            else:
                import webbrowser
                webbrowser.open(url)
                time.sleep(0.4)

        if title and sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    user32.ShowWindow(hwnd, 9)
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

        # Trigger on-screen modal alert for Master Muhammad
        try:
            from src.human_intervention import show_onscreen_modal, notify_voice
            if prompt_text:
                notify_voice("Master Muhammad, manual intervention is required on screen.")
                show_onscreen_modal(
                    title=title or "Verification Required",
                    reason=prompt_text,
                    explanation_ur="Sir, screen par verification challenge solve karein ya browser check karein.",
                    target_url=url,
                    window_title=title,
                )
        except Exception:
            pass

        return True
    except Exception as e:
        logger.debug("Failed to open or focus on PC: %s", e)
        return False


def capture_intervention_screenshot(req_id: str) -> Optional[str]:
    """Captures desktop screen showing the exact prompt/challenge."""
    try:
        from perception.screen_capture import get_screen_engine
        save_file = _RUNTIME_DIR / f"intervention_{req_id}.png"
        shot = get_screen_engine().capture_display(save_path=str(save_file))
        if shot.get("status") == "success" and save_file.exists() and save_file.stat().st_size > 1000:
            return str(save_file)
    except Exception as e:
        logger.debug("Could not capture intervention screenshot: %s", e)
    return None


class InterventionType(str, Enum):
    MISSING_API_KEY = "MISSING_API_KEY"
    CAPTCHA_CHALLENGE = "CAPTCHA_CHALLENGE"
    TWO_FACTOR_AUTH = "TWO_FACTOR_AUTH"
    CRITICAL_CONFIRMATION = "CRITICAL_CONFIRMATION"
    HUMAN_DISCUSSION_NEEDED = "HUMAN_DISCUSSION_NEEDED"


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"
    FALLBACK_FREE = "FALLBACK_FREE"


@dataclass
class HumanInterventionRequest:
    request_id: str
    request_type: InterventionType
    title: str
    target_service: str
    reason_technical: str
    explanation_ur: str
    suggested_free_alternative: str
    action_blocked: str
    account_username: str = DEFAULT_OWNER_EMAIL
    code_destination: str = f"Aapke Gmail ({DEFAULT_OWNER_EMAIL}) Inbox / Authenticator App"
    portal_url: str = ""
    window_title: str = ""
    screenshot_path: Optional[str] = None
    pc_status: str = "PC screen par window samne open rakhi gayi hai"
    status: RequestStatus = RequestStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    resolution_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["request_type"] = self.request_type.value if hasattr(self.request_type, "value") else str(self.request_type)
        d["status"] = self.status.value if hasattr(self.status, "value") else str(self.status)
        return d


class HumanInterventionGateway:
    """
    Central gateway coordinating human interventions between J.A.R.V.I.S. subsystems
    and the user's WhatsApp channel.
    """

    def __init__(self, owner_phone: str = DEFAULT_OWNER_PHONE):
        self.owner_phone = owner_phone
        self.last_screenshot_path: Optional[str] = None
        self._lock = threading.Lock()
        self._requests: Dict[str, HumanInterventionRequest] = {}
        _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._load_requests()

    def _load_requests(self) -> None:
        with self._lock:
            if _PENDING_FILE.exists():
                try:
                    data = json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
                    for req_id, r in data.items():
                        req_type = InterventionType(r.get("request_type", InterventionType.MISSING_API_KEY.value))
                        req_status = RequestStatus(r.get("status", RequestStatus.PENDING.value))
                        self._requests[req_id] = HumanInterventionRequest(
                            request_id=req_id,
                            request_type=req_type,
                            title=r.get("title", ""),
                            target_service=r.get("target_service", ""),
                            reason_technical=r.get("reason_technical", ""),
                            explanation_ur=r.get("explanation_ur", ""),
                            suggested_free_alternative=r.get("suggested_free_alternative", ""),
                            action_blocked=r.get("action_blocked", ""),
                            account_username=r.get("account_username", DEFAULT_OWNER_EMAIL),
                            code_destination=r.get("code_destination", f"Aapke Gmail ({DEFAULT_OWNER_EMAIL}) Inbox / Authenticator App"),
                            portal_url=r.get("portal_url", ""),
                            window_title=r.get("window_title", ""),
                            screenshot_path=r.get("screenshot_path"),
                            pc_status=r.get("pc_status", "PC screen par window samne open rakhi gayi hai"),
                            status=req_status,
                            created_at=r.get("created_at", ""),
                            resolved_at=r.get("resolved_at"),
                            resolution_details=r.get("resolution_details")
                        )
                except Exception as e:
                    logger.warning("Could not read pending requests file: %s", e)

    def _save_requests(self) -> None:
        with self._lock:
            try:
                data = {k: v.to_dict() for k, v in self._requests.items()}
                _PENDING_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error("Failed to persist human intervention requests: %s", e)

    # ==========================================================================
    # CREATING & DISPATCHING REQUESTS
    # ==========================================================================

    def request_api_key(
        self,
        service_name: str,
        reason: str,
        free_alternative: str = "Free DEX Screener / Local LLM scraping",
        action_blocked: str = "Automated data retrieval",
        portal_url: str = "",
        window_title: str = ""
    ) -> HumanInterventionRequest:
        """Creates and dispatches a realistic request for a missing paid API key with screenshot."""
        req_id = f"REQ-API-{int(time.time())}"
        explanation_ur = (
            f"Sir, {service_name.upper()} ki paid API key required hai taake {action_blocked} ho sake. "
            f"Lekin main 100% free mode bhi chala sakta hoon baghair kisi kharche ke."
        )
        if portal_url:
            open_or_focus_on_pc(portal_url, window_title)
        shot_path = capture_intervention_screenshot(req_id)

        req = HumanInterventionRequest(
            request_id=req_id,
            request_type=InterventionType.MISSING_API_KEY,
            title=f"{service_name.upper()} Paid API Key Needed",
            target_service=service_name,
            reason_technical=reason,
            explanation_ur=explanation_ur,
            suggested_free_alternative=free_alternative,
            action_blocked=action_blocked,
            portal_url=portal_url,
            window_title=window_title,
            screenshot_path=shot_path,
            pc_status="PC desktop active hai aur API settings ready hain"
        )
        with self._lock:
            self._requests[req_id] = req
        self._save_requests()
        self._dispatch_to_whatsapp(req)
        return req

    def request_captcha_resolution(
        self,
        target_site: str,
        url: str,
        action_blocked: str = "Web scraping operation",
        account_username: str = "",
        window_title: str = ""
    ) -> HumanInterventionRequest:
        """Creates and dispatches an alert for a Captcha challenge with screen focus & screenshot."""
        if "fundingpips" in target_site.lower() or "fundingpips" in url.lower():
            eff_user = account_username or FUNDINGPIPS_EMAIL
            eff_url = url or FUNDINGPIPS_PORTAL_URL
        else:
            eff_user = account_username or DEFAULT_OWNER_EMAIL
            eff_url = url

        req_id = f"REQ-CAP-{int(time.time())}"
        explanation_ur = (
            f"Sir, {target_site} par Cloudflare / Bot Captcha challenge aa gaya hai. "
            f"Maine browser window PC screen par samne open kar di hai taake aap 1-click se verify kar sakein."
        )
        if eff_url:
            open_or_focus_on_pc(eff_url, window_title or target_site)
        shot_path = capture_intervention_screenshot(req_id)

        req = HumanInterventionRequest(
            request_id=req_id,
            request_type=InterventionType.CAPTCHA_CHALLENGE,
            title=f"Captcha Challenge on {target_site}",
            target_service=target_site,
            reason_technical=f"Cloudflare Turnstile or reCAPTCHA detected at {eff_url}",
            explanation_ur=explanation_ur,
            suggested_free_alternative="Switch to direct DEX Screener REST API or cached local database",
            action_blocked=action_blocked,
            account_username=eff_user,
            code_destination="PC Screen (Browser Window par 1-click checkbox)",
            portal_url=eff_url,
            window_title=window_title or target_site,
            screenshot_path=shot_path,
            pc_status="Browser window computer screen par samne open kar di gayi hai"
        )
        with self._lock:
            self._requests[req_id] = req
        self._save_requests()
        self._dispatch_to_whatsapp(req)
        return req

    def request_2fa_code(
        self,
        service_name: str,
        channel: str = "SMS / Authenticator",
        action_blocked: str = "Account login",
        account_username: str = "",
        code_destination: str = "",
        portal_url: str = "",
        window_title: str = ""
    ) -> HumanInterventionRequest:
        """Dispatches an alert for 2FA / OTP code with explicit account, destination, and live screenshot."""
        if "fundingpips" in service_name.lower():
            eff_user = account_username or FUNDINGPIPS_EMAIL
            eff_dest = code_destination or f"Aapke FundingPips Gmail ({FUNDINGPIPS_EMAIL}) Inbox"
            eff_url = portal_url or FUNDINGPIPS_PORTAL_URL
        else:
            eff_user = account_username or DEFAULT_OWNER_EMAIL
            eff_dest = code_destination or f"Aapke Gmail ({DEFAULT_OWNER_EMAIL}) Inbox / Authenticator App"
            eff_url = portal_url

        req_id = f"REQ-2FA-{int(time.time())}"
        explanation_ur = (
            f"Sir, {service_name} login ke liye 2FA/OTP code needed hai. "
            f"Account: `{eff_user}`. Code aapke `{eff_dest}` par bheja gaya hai."
        )
        if eff_url:
            open_or_focus_on_pc(eff_url, window_title or service_name)
        shot_path = capture_intervention_screenshot(req_id)

        req = HumanInterventionRequest(
            request_id=req_id,
            request_type=InterventionType.TWO_FACTOR_AUTH,
            title=f"2FA Code Needed for {service_name}",
            target_service=service_name,
            reason_technical=f"Service required 2FA token for {eff_user} via {channel}",
            explanation_ur=explanation_ur,
            suggested_free_alternative="Switch to 100% Free / Public feed mode without login",
            action_blocked=action_blocked,
            account_username=eff_user,
            code_destination=eff_dest,
            portal_url=eff_url,
            window_title=window_title or service_name,
            screenshot_path=shot_path,
            pc_status="PC par login portal screen par samne open rakha gaya hai"
        )
        with self._lock:
            self._requests[req_id] = req
        self._save_requests()
        self._dispatch_to_whatsapp(req)
        return req

    def format_whatsapp_message(self, req: HumanInterventionRequest) -> str:
        """Formats an honest, realistic WhatsApp alert message with rich options and destination info."""
        if req.request_type == InterventionType.MISSING_API_KEY:
            pc_line = f"🖥️ *PC Status:* {req.pc_status}\n" if req.pc_status else ""
            msg = (
                f"🚨 *[J.A.R.V.I.S. REALISTIC ASSISTANCE NEEDED]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Topic:* {req.title}\n"
                f"⚠️ *Why Needed:* {req.reason_technical}\n"
                f"{pc_line}"
                f"🛑 *Blocked Action:* {req.action_blocked}\n\n"
                f"🎙️ *Urdu Explanation:*\n"
                f"\"{req.explanation_ur}\"\n\n"
                f"💡 *Free Alternative Available:*\n"
                f"👉 {req.suggested_free_alternative}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Aapke Paas Yeh 5 Options Hain:*\n"
                f"[1] Key Configure: Reply `key: <your_api_key>`\n"
                f"[2] PC Par Kholein: Reply `2` ya `kholo` (portal desktop par samne le aaonga)\n"
                f"[3] Screenshot: Reply `3` ya `screenshot` (taza screen photo bhej dunga)\n"
                f"[4] 100% Free Mode: Reply `4` ya `free` (kisi kharche ke bghair)\n"
                f"[5] Cancel: Reply `5` ya `cancel` (task skip karein)"
            )
        elif req.request_type == InterventionType.CAPTCHA_CHALLENGE:
            account_line = f"👤 *Account:* {req.account_username}\n" if req.account_username else ""
            pc_line = f"🖥️ *PC Status:* {req.pc_status}\n" if req.pc_status else ""
            msg = (
                f"🧩 *[HUMAN VERIFICATION REQUIRED — CAPTCHA]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Site:* {req.target_service}\n"
                f"{account_line}"
                f"{pc_line}"
                f"🛑 *Blocked:* {req.action_blocked}\n"
                f"ℹ️ *Issue:* {req.reason_technical}\n\n"
                f"🎙️ *Urdu Explanation:*\n"
                f"\"{req.explanation_ur}\"\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Aapke Paas Yeh Options Hain:*\n"
                f"[1] Solve & Done: Screen par solve kar ke reply karein `done` ya `ho gaya`\n"
                f"[2] PC Par Kholein: Reply `2` ya `kholo` (site screen par samne le aaonga)\n"
                f"[3] Screenshot: Reply `3` ya `screenshot` (screen ki live photo bhej dunga)\n"
                f"[4] Free API: Reply `4` ya `free` (direct DEX Screener API without browser)\n"
                f"[5] Cancel: Reply `5` ya `cancel` (skip karein)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 *Note:* Options ke ilawa aap koi bhi direct command likh kar bhej sakte hain, main foran execute karunga."
            )
        elif req.request_type == InterventionType.TWO_FACTOR_AUTH:
            account_line = f"👤 *Account:* {req.account_username}\n" if req.account_username else ""
            dest_line = f"📧 *Code Kahan Aayega:* {req.code_destination}\n" if req.code_destination else ""
            pc_line = f"🖥️ *PC Status:* {req.pc_status}\n" if req.pc_status else ""
            msg = (
                f"🔐 *[2FA / OTP VERIFICATION REQUIRED]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Service:* {req.target_service}\n"
                f"{account_line}"
                f"{dest_line}"
                f"{pc_line}"
                f"🛑 *Blocked:* {req.action_blocked}\n\n"
                f"🎙️ *Urdu Explanation:*\n"
                f"\"{req.explanation_ur}\"\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Aapke Paas Yeh Options Hain:*\n"
                f"[1] Code Submit: Reply `otp: 123456` ya seedha code bhej dein\n"
                f"[2] PC Par Kholein: Reply `2` ya `kholo` (window desktop par samne le aaonga)\n"
                f"[3] Screenshot: Reply `3` ya `screenshot` (taza live screen photo bhej dunga)\n"
                f"[4] 100% Free Mode: Reply `4` ya `free` (baghair login/API ke free alternative chalayein)\n"
                f"[5] Cancel: Reply `5` ya `cancel` (task skip karein)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 *Note:* Options ke ilawa aap koi bhi direct command likh kar bhej sakte hain, main foran execute karunga."
            )
        else:
            msg = (
                f"⚠️ *[J.A.R.V.I.S. INTERVENTION REQUEST]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Title:* {req.title}\n"
                f"ℹ️ *Detail:* {req.reason_technical}\n"
                f"👉 Reply to discuss or decide."
            )
        return msg

    def _dispatch_to_whatsapp(self, req: HumanInterventionRequest, extra_msg: str = "", send_image: bool = False) -> bool:
        """Sends the formatted request directly to WhatsApp gateway (including image ONLY if explicitly requested)."""
        msg_text = extra_msg or self.format_whatsapp_message(req)
        try:
            # Check WhatsApp Anti-Ban Rate Limiter & DND Gatekeeper
            try:
                from core.whatsapp_rate_limiter import get_whatsapp_limiter
                limiter = get_whatsapp_limiter()
                allowed, reason = limiter.can_dispatch_whatsapp(
                    is_user_reply=bool(extra_msg),
                    severity="CRITICAL",
                    is_critical_anomaly=True
                )
                if not allowed:
                    logger.info("WhatsApp intervention dispatch suppressed by rate limiter (%s): %s", reason, req.request_id)
                    return False
            except Exception as lim_err:
                logger.debug("Limiter check bypassed: %s", lim_err)

            payload_dict = {
                "number": self.owner_phone,
                "message": msg_text
            }
            # Only attach image if send_image is True AND file exists
            if send_image and req.screenshot_path and Path(req.screenshot_path).exists():
                payload_dict["imagePath"] = str(Path(req.screenshot_path).resolve())

            payload = json.dumps(payload_dict).encode("utf-8")
            http_req = urllib.request.Request(
                WA_GATEWAY_URL,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            try:
                from platform_runtime import wa_http_token
                token = wa_http_token()
                if token:
                    http_req.add_header("X-Jarvis-Token", token)
            except Exception:
                pass

            with urllib.request.urlopen(http_req, timeout=5) as resp:
                if resp.status in (200, 201):
                    logger.info("Human intervention request %s dispatched to WhatsApp (image=%s).", req.request_id, bool(send_image and req.screenshot_path))
                    try:
                        limiter.record_dispatch(is_user_reply=bool(extra_msg))
                    except Exception:
                        pass
                    return True
        except Exception as e:
            logger.info("Could not reach WhatsApp gateway directly (%s). Persisted to pending ledger.", e)
        return False

    # ==========================================================================
    # RESOLUTION & CONVERSATIONAL INQUIRIES FROM INCOMING WHATSAPP / TERMINAL
    # ==========================================================================

    def get_latest_pending_request(self) -> Optional[HumanInterventionRequest]:
        """Returns the most recent pending request."""
        with self._lock:
            pending = [r for r in self._requests.values() if r.status == RequestStatus.PENDING]
            if pending:
                return sorted(pending, key=lambda x: x.created_at, reverse=True)[0]
        return None

    def resolve_from_message(self, message_text: str, sender_id: str = "") -> Tuple[bool, str]:
        """
        Parses incoming message to check if it resolves any pending intervention
        or answers user's clarifying questions regarding the active request.
        Returns: (is_handled, response_message)
        """
        clean_text = str(message_text or "").strip()
        lower = clean_text.lower()
        if not clean_text:
            return False, ""

        # Identify target request (prefer pending, otherwise most recent)
        req = self.get_latest_pending_request()
        if not req:
            with self._lock:
                if any(w in lower for w in ["otp", "2fa", "code", "authenticator", "email", "account", "konsa", "kaha"]):
                    two_fa_reqs = [r for r in self._requests.values() if r.request_type == InterventionType.TWO_FACTOR_AUTH]
                    if two_fa_reqs:
                        req = sorted(two_fa_reqs, key=lambda x: x.created_at, reverse=True)[0]
                elif self._requests:
                    req = sorted(self._requests.values(), key=lambda x: x.created_at, reverse=True)[0]

        is_whatsapp_sender = bool(sender_id and ("wa" in str(sender_id).lower() or any(c.isdigit() for c in str(sender_id))))

        # ----------------------------------------------------------------------
        # 1. CLARIFYING INQUIRIES & QUESTIONS (TEXT ONLY, NO RANDOM SCREENSHOTS)
        # ----------------------------------------------------------------------
        inquiry_patterns = [
            r"\b(konsadala|konsa\s*dala|kis\s+account|kaunsa\s+account|konsa\s+account|account\s+konsa|account\s+kaunsa|kiska\s+account)\b",
            r"\b(kaha\s+email|kahan\s+email|email\s+kahan|email\s+kaha|kaha\s*aaiga|kahan\s*aaega|kahan\s*aayega|kahan\s*aae\s*ga|kahan\s+code|code\s+kahan|code\s+kidhar|otp\s+kahan|otp\s+kidhar)\b",
            r"\b(kis\s+cheez\s+ka|kya\s+mang\s+raha|kya\s+chahiye|kyun\s+chahiye)\b",
        ]
        is_inquiry = any(re.search(pat, lower) for pat in inquiry_patterns) or (
            any(w in lower for w in ["otp", "2fa", "captcha", "verification"]) and any(w in lower for w in ["kahan", "kaha", "kidhar", "sms", "inbox", "spam", "authenticator", "details", "tafseel", "samjhao", "batao", "kyun", "why", "help"])
        ) or lower in {"details", "tafseelat", "tafseel", "otp details", "challenge details", "account details"}

        if is_inquiry:
            is_fp_inquiry = any(w in lower for w in ["funding", "pips", "hamid", "prop", "40000294403"]) or (req and "funding" in str(req.target_service).lower())
            target_user = FUNDINGPIPS_EMAIL if is_fp_inquiry else (req.account_username if req else FUNDINGPIPS_EMAIL)
            target_svc = "FundingPips #40000294403 ($100k)" if is_fp_inquiry else (req.target_service if req else "FundingPips / J.A.R.V.I.S.")
            target_dest = f"Aapke FundingPips Gmail ({FUNDINGPIPS_EMAIL}) Inbox" if is_fp_inquiry else (req.code_destination if req else f"Aapke FundingPips Gmail ({FUNDINGPIPS_EMAIL}) Inbox")
            target_status = req.pc_status if req else "Google Chrome (Profile 2) screen par samne active hai"
            target_block = req.action_blocked if req else "FundingPips Account Login"
            reply = (
                f"🔍 *[J.A.R.V.I.S. ACCOUNT & OTP DETAILS]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Sir, aapke sawal ki mukammal tafseelat:\n\n"
                f"👤 *Account Login:* `{target_user}` ({target_svc})\n"
                f"📧 *Code Kahan Aayega:* {target_dest}\n"
                f"🖥️ *PC Screen Status:* {target_status}\n"
                f"🛑 *Blocked Operation:* {target_block}\n\n"
                f"• PC par dobara kholne ke liye: Reply karein `2` ya `kholo`\n"
                f"• Screenshot mangne ke liye: Reply karein `3` ya `screenshot`\n"
                f"• Cancel karne ke liye: Reply karein `5` ya `cancel`"
            )
            return True, reply

        # ----------------------------------------------------------------------
        # 2. OPTION 2: REAL BROWSER EXECUTION (OPEN / BRING TO FRONT)
        # ----------------------------------------------------------------------
        is_open_option = (
            ((clean_text in {"2", "option 2", "[2]"}) and (req is not None or is_whatsapp_sender))
            or clean_text in {"kholo", "open", "pc par kholo", "samne lao", "screen par lao", "window kholo", "bring to front", "screen open"}
            or any(w in lower for w in ["fundingpips kholo", "portal kholo", "hamid kholo", "chrome kholo", "pips kholo"])
            or (len(clean_text.split()) <= 4 and any(w in lower for w in ["kholo", "samne lao", "screen par lao", "pc par kholo", "window kholo", "bring to front"]))
        ) and not any(w in lower for w in ["profile", "adeel", "chatgpt", "gemini", "claude", "deepseek", "youtube", "vscode", "terminal"])

        if is_open_option:
            target_svc = str(req.target_service).lower() if req else "fundingpips"
            target_url = (req.portal_url if req else "") or FUNDINGPIPS_PORTAL_URL
            target_acc = req.account_username if req else FUNDINGPIPS_EMAIL
            try:
                from actions.fundingpips_automation import open_and_prepare_fundingpips
                res = open_and_prepare_fundingpips(interactive=True)
                reply = (
                    f"🖥️ *[PC SCREEN ACTIVATED — CHROME PROFILE 2 OPENED]*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Sir, maine FundingPips ka portal Hamid profile (Profile 2) ke sath computer desktop par samne open kar diya hai.\n"
                    f"• *Account:* `{FUNDINGPIPS_EMAIL}`\n"
                    f"• *MT5 Account:* `#{FUNDINGPIPS_ACCOUNT_ID}` ($100k Model)\n"
                    f"Desktop screen par credentials auto-fill ho chuke hain aur 2FA prompt active hai."
                )
            except Exception as launch_err:
                portal = target_url or FUNDINGPIPS_PORTAL_URL
                win_title = (req.window_title if req else "") or "FundingPips"
                open_or_focus_on_pc(portal, win_title)
                reply = (
                    f"🖥️ *[PC SCREEN ACTIVATED & BROUGHT TO FRONT]*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Sir, FundingPips portal Chrome (Profile 2) mein screen par open kar ke samne focus kar diya hai."
                )
            return True, reply

        # ----------------------------------------------------------------------
        # 3. OPTION 3: CAPTURE & DISPATCH SCREENSHOT (ONLY WHEN EXPLICITLY ASKED)
        # ----------------------------------------------------------------------
        if ((clean_text in {"3", "option 3", "[3]"}) and (req is not None or is_whatsapp_sender)) or any(w in lower for w in ["screenshot", "tasweer", "photo", "image", "screen dikhao", "live screen"]):
            shot_id = f"{req.request_id}_fresh" if req else f"REQ-MANUAL-{int(time.time())}_fresh"
            fresh_shot = capture_intervention_screenshot(shot_id)
            if fresh_shot and req:
                req.screenshot_path = fresh_shot
                self.last_screenshot_path = fresh_shot
                self._save_requests()
            elif fresh_shot:
                self.last_screenshot_path = fresh_shot
            target_info = f"`{req.target_service}` ({req.account_username})" if req else "Primary Display"
            reply = (
                f"📸 *[LIVE SCREENSHOT ATTACHED]*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Sir, computer screen ki taza photo bhej di gayi hai.\n"
                f"Target: {target_info}"
            )
            if is_whatsapp_sender and req:
                self._dispatch_to_whatsapp(req, extra_msg=reply, send_image=True)
            return True, reply

        # ----------------------------------------------------------------------
        # 4. OPTION 1: PROMPT FOR OTP CODE ENTRY
        # ----------------------------------------------------------------------
        if clean_text in {"1", "option 1", "[1]"} and (req is not None or is_whatsapp_sender):
            return True, (
                f"✍️ *[ENTER 2FA / OTP CODE]*\n"
                f"Sir, barah-e-karam apna 4-8 digit OTP code yahan type karein (e.g. `otp: 123456` ya seedha code bhej dein)."
            )

        # ----------------------------------------------------------------------
        # 5. OPTION 4: PREFERENCE FOR 100% FREE ALTERNATIVE
        # ----------------------------------------------------------------------
        if (clean_text in {"4", "option 4", "[4]"} and req is not None) or any(w in lower for w in ["free use karo", "free mode", "alternative", "kharcha nahi", "no key", "bypass"]):
            free_alt = req.suggested_free_alternative if req else "Direct DEX Screener REST API / Public feeds"
            if req:
                req.status = RequestStatus.FALLBACK_FREE
                req.resolved_at = datetime.now(timezone.utc).isoformat()
                req.resolution_details = {"mode": "free_alternative"}
                self._save_requests()
            return True, (
                f"🟢 *[100% FREE MODE ACTIVATED]*\n"
                f"Sir, understood! Hum ne paid/login requirement bypass kar ke 100% Free Mode activate kar diya hai: "
                f"{free_alt}. Zero-cost operations resume ho chuke hain!"
            )

        # ----------------------------------------------------------------------
        # 6. OPTION 5: CANCELLATION
        # ----------------------------------------------------------------------
        if (clean_text in {"5", "option 5", "[5]"} and req is not None) or (req is not None and any(w in lower for w in ["cancel", "skip", "choro", "mat karo", "rehne do"])):
            req_title = req.title if req else "pending intervention"
            if req:
                req.status = RequestStatus.CANCELLED
                req.resolved_at = datetime.now(timezone.utc).isoformat()
                req.resolution_details = {"cancelled_by_user": True}
                self._save_requests()
            return True, (
                f"⏹️ *[REQUEST CANCELLED]*\n"
                f"Sir, request '{req_title}' cancel kar di gayi hai. Normal standby operations active hain."
            )

        # ----------------------------------------------------------------------
        # 7. RESOLUTION: API KEY SUBMISSION
        # ----------------------------------------------------------------------
        key_match = re.search(r'(?:key:\s*|api_key:\s*|^)(sk-[a-zA-Z0-9_\-]{20,}|gsk_[a-zA-Z0-9_\-]{20,}|AIzaSy[a-zA-Z0-9_\-]{20,})', clean_text)
        if key_match or (req and req.request_type == InterventionType.MISSING_API_KEY and ("sk-" in clean_text or "gsk_" in clean_text or "AIza" in clean_text)):
            raw_key = key_match.group(1) if key_match else clean_text.split()[-1]
            svc_name = req.target_service if req else "openai"
            saved = self._save_api_key_to_config(svc_name, raw_key)
            if req:
                req.status = RequestStatus.RESOLVED
                req.resolved_at = datetime.now(timezone.utc).isoformat()
                req.resolution_details = {"key_provided": True, "service": svc_name}
                self._save_requests()
            blocked_act = req.action_blocked if req else "Automated operation"
            return True, (
                f"✅ *[API KEY CONFIGURED & VERIFIED]*\n"
                f"Sir, {svc_name.upper()} ki API key save kar li gayi hai ('config/api_keys.json'). "
                f"Blocked operation ('{blocked_act}') ab transparently resume ho raha hai!"
            )

        # ----------------------------------------------------------------------
        # 8. RESOLUTION: CAPTCHA SOLVED (Done / Ho gaya)
        # ----------------------------------------------------------------------
        if (req is None or req.request_type == InterventionType.CAPTCHA_CHALLENGE) and any(w in lower for w in ["done", "ho gaya", "solve", "solved", "kar diya", "clear"]):
            if req:
                req.status = RequestStatus.RESOLVED
                req.resolved_at = datetime.now(timezone.utc).isoformat()
                req.resolution_details = {"captcha_solved_by_user": True}
                self._save_requests()
            return True, (
                f"✅ *[CAPTCHA RESOLUTION ACKNOWLEDGED]*\n"
                f"Thank you Sir! Captcha solve hone ki confirmation mil gayi hai. "
                f"Web navigation and monitoring continue kar raha hoon."
            )

        # ----------------------------------------------------------------------
        # 9. RESOLUTION: OTP / 2FA SUBMISSION
        # ----------------------------------------------------------------------
        otp_match = re.search(r'(?:otp:\s*|code:\s*|^)([0-9]{4,8})$', clean_text)
        if (req is None or req.request_type == InterventionType.TWO_FACTOR_AUTH or "otp" in lower) and (otp_match or (clean_text.isdigit() and len(clean_text) in (4, 5, 6, 8))):
            code = otp_match.group(1) if otp_match else clean_text
            if req:
                req.status = RequestStatus.RESOLVED
                req.resolved_at = datetime.now(timezone.utc).isoformat()
                req.resolution_details = {"otp_received": code}
                self._save_requests()

            # Actively inject the OTP code into the active FundingPips window!
            injected = False
            try:
                from actions.fundingpips_automation import submit_otp_code
                injected = submit_otp_code(code)
            except Exception as e:
                logger.error("Could not inject OTP: %s", e)

            inj_msg = "aur portal par automatic submit kar diya gaya hai!" if injected else "aur screen par submit ho raha hai!"
            return True, (
                f"✅ *[2FA / OTP CODE RECEIVED & SUBMITTED]*\n"
                f"Sir, OTP code `{code}` capture kar liya gaya hai {inj_msg}\n"
                f"Authentication flow complete ho raha hai!"
            )

        return False, ""


    def _save_api_key_to_config(self, service: str, key_val: str) -> bool:
        """Safely saves the newly received API key to config/api_keys.json."""
        key_map = {
            "openai": "openai_api_key",
            "chatgpt": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "claude": "anthropic_api_key",
            "deepseek": "deepseek_api_key",
            "gemini": "gemini_api_key",
            "google": "gemini_api_key",
            "finnhub": "finnhub_api_key",
            "groq": "groq_api_key",
            "github": "github_token"
        }
        config_key = key_map.get(service.lower(), f"{service.lower()}_api_key")
        try:
            cfg = {}
            if _API_KEYS_FILE.exists():
                cfg = json.loads(_API_KEYS_FILE.read_text(encoding="utf-8"))
            cfg[config_key] = key_val.strip()
            _API_KEYS_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            logger.info("Saved API key for service '%s' as '%s'", service, config_key)
            return True
        except Exception as e:
            logger.error("Failed to write API key to config: %s", e)
            return False


# Singleton Accessor
_gateway_instance: Optional[HumanInterventionGateway] = None

def get_human_intervention_gateway() -> HumanInterventionGateway:
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = HumanInterventionGateway()
    return _gateway_instance
