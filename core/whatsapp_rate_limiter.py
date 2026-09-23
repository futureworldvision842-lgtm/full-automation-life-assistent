"""
core/whatsapp_rate_limiter.py — WhatsApp Anti-Ban Rate Limiter & DND Silence Controller
========================================================================================
1. WhatsApp Anti-Ban Protocol:
   - Limits outbound unprompted automated messages to protect the WhatsApp account from bans.
   - Enforces a minimum interval between proactive alerts and hourly caps.
   - Direct replies to explicit user requests/commands are always allowed.
2. Do Not Disturb (DND) / Silence Mode:
   - Recognizes Roman Urdu and English silence commands:
     "mujhey 2 ghantey tang mat kerna", "tang mat karo", "dnd for 4 hours", "messages band rakho".
   - Suppresses unprompted alerts and notifications while DND is active.
   - Persists state in runtime/whatsapp_dnd_state.json.
3. Unrestricted Discord:
   - Discord has ZERO restrictions ("full azadi") for trading signals, logs, and chatter.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.whatsapp_limiter")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_ROOT_DIR = Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _ROOT_DIR / "runtime"
_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
_DND_STATE_FILE = _RUNTIME_DIR / "whatsapp_dnd_state.json"
_RATE_LIMIT_STATE_FILE = _RUNTIME_DIR / "whatsapp_rate_limit_state.json"

# Anti-Ban Safe Thresholds
MIN_INTERVAL_BETWEEN_PROACTIVE_ALERTS_SEC = 300  # Minimum 5 minutes between unprompted messages
MAX_PROACTIVE_ALERTS_PER_HOUR = 8               # Max 8 unprompted messages per hour to prevent ban
DEFAULT_DND_HOURS = 2.0                          # Default 2 hours if user doesn't specify number


class WhatsAppRateLimiter:
    """Manages WhatsApp rate limits, anti-ban pacing, and Do Not Disturb (DND) state."""

    _instance: Optional[WhatsAppRateLimiter] = None
    _lock = threading.Lock()

    def __init__(self):
        self._dispatch_timestamps: List[float] = []
        self._load_state()

    @classmethod
    def get_instance(cls) -> WhatsAppRateLimiter:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # --------------------------------------------------------------------------
    # STATE MANAGEMENT
    # --------------------------------------------------------------------------

    def _load_state(self) -> None:
        """Loads DND and rate limiting timestamps from disk."""
        if _RATE_LIMIT_STATE_FILE.exists():
            try:
                data = json.loads(_RATE_LIMIT_STATE_FILE.read_text(encoding="utf-8"))
                now = time.time()
                # Keep timestamps from the last 3600 seconds
                self._dispatch_timestamps = [t for t in data.get("timestamps", []) if (now - t) < 3600]
            except Exception as e:
                logger.debug("Could not read rate limit state: %s", e)
                self._dispatch_timestamps = []

    def _save_state(self) -> None:
        """Persists dispatch timestamps to disk."""
        try:
            now = time.time()
            self._dispatch_timestamps = [t for t in self._dispatch_timestamps if (now - t) < 3600]
            _RATE_LIMIT_STATE_FILE.write_text(
                json.dumps({"timestamps": self._dispatch_timestamps, "updated_at": now}, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug("Could not save rate limit state: %s", e)

    # --------------------------------------------------------------------------
    # DO NOT DISTURB (DND) / SILENCE MODE
    # --------------------------------------------------------------------------

    def is_dnd_active(self) -> Tuple[bool, float, str]:
        """
        Returns (is_active, remaining_seconds, human_remaining_str).
        """
        if not _DND_STATE_FILE.exists():
            return False, 0.0, ""

        try:
            data = json.loads(_DND_STATE_FILE.read_text(encoding="utf-8"))
            if not data.get("dnd_active", False):
                return False, 0.0, ""

            until_epoch = float(data.get("dnd_until_epoch", 0.0))
            now = time.time()
            if now < until_epoch:
                remaining = until_epoch - now
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                if hours > 0:
                    time_str = f"{hours} ghantay {minutes} minute" if minutes > 0 else f"{hours} ghantay"
                else:
                    time_str = f"{minutes} minute"
                return True, remaining, time_str
            else:
                # DND has expired
                self.disable_dnd()
                return False, 0.0, ""
        except Exception as e:
            logger.debug("Error checking DND state: %s", e)
            return False, 0.0, ""

    def enable_dnd(self, duration_seconds: float, reason: str = "") -> Dict[str, Any]:
        """Activates DND silence mode for the given duration."""
        now = time.time()
        until_epoch = now + duration_seconds
        until_dt = datetime.fromtimestamp(until_epoch, tz=timezone.utc)
        until_iso = until_dt.isoformat()

        hours = duration_seconds / 3600.0
        if hours >= 1.0:
            human_dur = f"{hours:.1f}".rstrip("0").rstrip(".") + " ghantay"
        else:
            human_dur = f"{int(duration_seconds // 60)} minute"

        payload = {
            "dnd_active": True,
            "dnd_until_epoch": until_epoch,
            "dnd_until_iso": until_iso,
            "duration_seconds": duration_seconds,
            "duration_human": human_dur,
            "reason": reason or "User requested silence",
            "activated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            _DND_STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to persist DND state: %s", e)

        logger.info("WhatsApp DND activated for %s (until %s)", human_dur, until_iso)
        return payload

    def disable_dnd(self) -> Dict[str, Any]:
        """Disables DND silence mode."""
        payload = {
            "dnd_active": False,
            "dnd_until_epoch": 0.0,
            "dnd_until_iso": None,
            "deactivated_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            _DND_STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to disable DND state: %s", e)

        logger.info("WhatsApp DND deactivated. Normal notifications resumed.")
        return payload

    # --------------------------------------------------------------------------
    # NATURAL LANGUAGE DND COMMAND PARSER
    # --------------------------------------------------------------------------

    @staticmethod
    def parse_dnd_command(message: str) -> Optional[Tuple[str, float]]:
        """
        Parses incoming message to detect DND / silence instructions.
        Returns: ("ENABLE", duration_seconds) | ("DISABLE", 0.0) | ("STATUS", 0.0) | None
        """
        clean = str(message or "").lower().strip()

        # Check for DND Cancellation / Unmute
        unmute_triggers = [
            "dnd band", "dnd off", "unmute", "shor machao", "bol sakte ho",
            "messages on kardo", "dnd khatam", "dnd disable", "resume messages"
        ]
        if any(t in clean for t in unmute_triggers) or clean in {"dnd off", "unmute", "bolna shuru karo"}:
            return "DISABLE", 0.0

        # Check for DND Status Query
        if clean in {"dnd status", "dnd check", "silent status", "kya dnd on hai", "dnd kab tak hai"}:
            return "STATUS", 0.0

        # Check for DND Activation triggers
        dnd_triggers = [
            "tang mat kerna", "tang mat karna", "tang mat karo", "disturb mat kerna",
            "disturb mat karna", "disturb mat karo", "dnd", "silent", "khamosh raho",
            "messages band", "msg band", "notification band", "mute raho", "chup raho",
            "do not disturb"
        ]

        matched = any(t in clean for t in dnd_triggers)
        if not matched:
            return None

        # Extract duration
        # Patterns like: "2 ghantey", "2 hours", "3 hrs", "30 mins", "1.5 ghante"
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ghantay|ghante|ghanta|hour|hours|hrs|hr|h)\b", clean)
        if hour_match:
            try:
                num_hours = float(hour_match.group(1))
                return "ENABLE", num_hours * 3600.0
            except ValueError:
                pass

        min_match = re.search(r"(\d+)\s*(?:minute|minutes|mins|min|m)\b", clean)
        if min_match:
            try:
                num_mins = float(min_match.group(1))
                return "ENABLE", num_mins * 60.0
            except ValueError:
                pass

        # If user just said "tang mat kerna" or "dnd" without duration, default to DEFAULT_DND_HOURS
        return "ENABLE", DEFAULT_DND_HOURS * 3600.0

    # --------------------------------------------------------------------------
    # GATEKEEPER & RATE LIMIT CHECK
    # --------------------------------------------------------------------------

    def can_dispatch_whatsapp(
        self,
        is_user_reply: bool = False,
        severity: str = "INFO",
        is_critical_anomaly: bool = False
    ) -> Tuple[bool, str]:
        """
        Determines whether a message is permitted to be sent via WhatsApp.
        - Direct user replies: ALWAYS allowed.
        - Critical anomalies / security: allowed unless strictly silenced.
        - DND Active: Blocks all proactive unprompted notifications.
        - Rate limiting / Anti-Ban: Enforces cooldown between messages.
        """
        # 1. Synchronous user replies are always allowed (conversational flow)
        if is_user_reply:
            return True, "user_reply_permitted"

        # 2. Check Do Not Disturb (DND)
        is_dnd, remaining, time_str = self.is_dnd_active()
        if is_dnd:
            return False, f"dnd_active_remaining_{time_str}"

        # 3. Only allow CRITICAL severity for proactive alerts (strictly within limit)
        clean_sev = str(severity or "").upper()
        if clean_sev not in {"CRITICAL", "EMERGENCY", "HIGH"} and not is_critical_anomaly:
            return False, "suppressed_non_critical_severity"

        # 4. Anti-Ban Rate Pacing: Cooldown between automated messages
        now = time.time()
        with self._lock:
            recent_hour = [t for t in self._dispatch_timestamps if (now - t) < 3600]
            if len(recent_hour) >= MAX_PROACTIVE_ALERTS_PER_HOUR:
                return False, "rate_limit_hourly_cap_reached"

            if self._dispatch_timestamps:
                last_time = self._dispatch_timestamps[-1]
                if (now - last_time) < MIN_INTERVAL_BETWEEN_PROACTIVE_ALERTS_SEC:
                    return False, "rate_limit_cooldown_active"

            return True, "permitted"

    def record_dispatch(self, is_user_reply: bool = False) -> None:
        """Records an outbound WhatsApp dispatch for anti-ban rate tracking."""
        if not is_user_reply:
            now = time.time()
            with self._lock:
                self._dispatch_timestamps.append(now)
                self._save_state()

    # --------------------------------------------------------------------------
    # DISCORD EXEMPTION (100% UNRESTRICTED)
    # --------------------------------------------------------------------------

    @staticmethod
    def can_dispatch_discord() -> Tuple[bool, str]:
        """Discord has full freedom ('full azadi') with zero rate limits or DND restrictions."""
        return True, "discord_unrestricted_full_azadi"


def get_whatsapp_limiter() -> WhatsAppRateLimiter:
    return WhatsAppRateLimiter.get_instance()
