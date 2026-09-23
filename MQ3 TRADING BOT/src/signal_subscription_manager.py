"""
signal_subscription_manager.py — VIP Signal Subscription & Direct Alert Hub.
=============================================================================
Manages public signal subscriptions, stores client phone numbers and preferences,
and orchestrates automated dispatch of institutional signals, whale alerts, and
account updates via WhatsApp.
"""

import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SignalSubscriptionManager")


class SignalSubscriptionManager:
    """
    VIP Signal & Client Notification Registry.
    """

    DEFAULT_STORE_PATH = "data/signal_subscribers.json"

    def __init__(self, store_path: str = DEFAULT_STORE_PATH):
        self.store_path = store_path
        if os.path.dirname(self.store_path):
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        self.subscribers: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "subscribers" in data:
                        return data["subscribers"]
            except Exception as e:
                logger.warning(f"Error loading signal subscribers: {e}")
        return self._default_subscribers()

    def _default_subscribers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Muhammad Owner",
                "phone": "+923468053268",
                "normalized_phone": "923468053268",
                "tier": "MASTER_OWNER",
                "asset_preference": "ALL_ASSETS",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]

    def _save(self):
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump({"subscribers": self.subscribers, "total": len(self.subscribers)}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving signal subscribers: {e}")

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Strips spaces, dashes, parentheses and leading +, returning clean digits.
        Normalizes local PK 03XXXXXXXXX to 923XXXXXXXXX.
        """
        clean = re.sub(r"[^\d]", "", str(phone or ""))
        if clean.startswith("00"):
            clean = clean[2:]
        if clean.startswith("0") and len(clean) == 11:
            clean = "92" + clean[1:]
        return clean

    def subscribe(
        self,
        phone: str,
        name: Optional[str] = "Trader",
        asset_preference: Optional[str] = "ALL_ASSETS",
        tier: Optional[str] = "VIP_MEMBER"
    ) -> Dict[str, Any]:
        """
        Registers or updates a subscriber for daily signals and whale alerts.
        """
        norm = self.normalize_phone(phone)
        if not norm or len(norm) < 8:
            return {"success": False, "message": "Invalid phone number format."}

        # Check existing
        for sub in self.subscribers:
            if sub.get("normalized_phone") == norm:
                sub["name"] = name or sub.get("name", "Trader")
                sub["asset_preference"] = asset_preference or sub.get("asset_preference", "ALL_ASSETS")
                sub["is_active"] = True
                sub["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return {
                    "success": True,
                    "is_new": False,
                    "subscriber": sub,
                    "message": f"Welcome back, {name}! Your VIP signal subscription has been refreshed."
                }

        new_sub = {
            "name": name or "Trader",
            "phone": str(phone).strip(),
            "normalized_phone": norm,
            "tier": tier or "VIP_MEMBER",
            "asset_preference": asset_preference or "ALL_ASSETS",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.subscribers.append(new_sub)
        self._save()

        return {
            "success": True,
            "is_new": True,
            "subscriber": new_sub,
            "message": f"🎉 Congratulations {name}! You are now subscribed to Institutional VIP Trading Signals & Whale Alerts on WhatsApp ({phone})."
        }

    def get_all_subscribers(self) -> List[Dict[str, Any]]:
        return self.subscribers
