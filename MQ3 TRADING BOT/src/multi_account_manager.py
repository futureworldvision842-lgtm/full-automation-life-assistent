"""
multi_account_manager.py — Institutional Multi-Account Prop Firm Fleet Manager.
Manages a portfolio fleet of Funding Pips & Prop Firm accounts:
  1. $100,000 Master Funded Account (Conservative 0.50% Risk / Capital Shield)
  2. $50,000 Funded Account (0.60% Risk Allocation)
  3. $25,000 Evaluation Account (0.75% Risk / Active Account #5054340275)
  4. $5,000 Fast Scalp Account (0.80% Growth Allocation)

Capabilities:
  • Multi-Terminal Order Routing & Position Sync
  • Individual Trailing High-Water Mark & Daily Loss Allocators
  • WhatsApp Multi-Account Voice/Text Routing ("status 100k", "buy gold on 50k")
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MultiAccountManager")


class MultiAccountManager:
    """
    Multi-Account Prop Firm Fleet Manager.
    """

    def __init__(self, config_path: str = "data/accounts_fleet.json"):
        self.config_path = config_path
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self.fleet = self._load_fleet()

    def _load_fleet(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        # Default Template for the 4 Accounts
        return {
            "accounts": {
                "25k_active": {
                    "account_id": "5054340275",
                    "account_name": "$25k Funding Pips Active Evaluation",
                    "server": "FundingPips-Demo",
                    "starting_balance": 25000.0,
                    "target_profit": 2000.0,
                    "risk_per_trade_pct": 0.0075, # 0.75%
                    "daily_loss_limit_pct": 2.5,
                    "max_trailing_loss_pct": 6.0,
                    "execution_mode": "AUTONOMOUS_FULL_POWER",
                    "is_active": True
                },
                "100k_master": {
                    "account_id": "PENDING_CREDENTIALS",
                    "account_name": "$100k Master Funded Account",
                    "server": "FundingPips-Server",
                    "starting_balance": 100000.0,
                    "target_profit": 8000.0,
                    "risk_per_trade_pct": 0.0050, # 0.50% (Ultra Conservative)
                    "daily_loss_limit_pct": 2.0,
                    "max_trailing_loss_pct": 5.0,
                    "execution_mode": "SEMI_AUTONOMOUS_INTERACTIVE",
                    "is_active": False
                },
                "50k_growth": {
                    "account_id": "PENDING_CREDENTIALS",
                    "account_name": "$50k Funded Account",
                    "server": "FundingPips-Server",
                    "starting_balance": 50000.0,
                    "target_profit": 4000.0,
                    "risk_per_trade_pct": 0.0060, # 0.60%
                    "daily_loss_limit_pct": 2.2,
                    "max_trailing_loss_pct": 5.5,
                    "execution_mode": "SEMI_AUTONOMOUS_INTERACTIVE",
                    "is_active": False
                },
                "5k_scalp": {
                    "account_id": "PENDING_CREDENTIALS",
                    "account_name": "$5k Fast Scalp Account",
                    "server": "FundingPips-Server",
                    "starting_balance": 5000.0,
                    "target_profit": 500.0,
                    "risk_per_trade_pct": 0.0080, # 0.80%
                    "daily_loss_limit_pct": 2.5,
                    "max_trailing_loss_pct": 6.0,
                    "execution_mode": "AUTONOMOUS_FULL_POWER",
                    "is_active": False
                }
            }
        }

    def _save_fleet(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.fleet, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving accounts fleet: {e}")

    def update_account_credentials(self, account_key: str, login: str, password: str, server: str = "FundingPips-Server"):
        """Updates login credentials for a specific account in the fleet."""
        if account_key in self.fleet["accounts"]:
            acc = self.fleet["accounts"][account_key]
            acc["account_id"] = login
            acc["server"] = server
            acc["is_active"] = True
            self._save_fleet()
            logger.info(f"[Fleet Manager] Updated credentials for {acc['account_name']} (#{login})")
            return True
        return False

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Generates a summary of all accounts in the fleet."""
        total_aum = sum(a["starting_balance"] for a in self.fleet["accounts"].values())
        active_count = sum(1 for a in self.fleet["accounts"].values() if a.get("is_active"))
        return {
            "total_aum_potential": total_aum,
            "active_accounts": active_count,
            "fleet": self.fleet["accounts"]
        }
