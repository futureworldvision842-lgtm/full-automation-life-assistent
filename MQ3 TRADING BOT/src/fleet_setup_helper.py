"""MQ3 Multi-Account Fleet Setup & Compliance Helper.

Provides:
1. Multi-Terminal portable folder validation
2. Account registration with credential isolation (password_env)
3. Anti-collision execution jitter configuration (prop firm safe)
4. Automated fleet status & health diagnostics
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("FleetSetupHelper")


class FleetSetupHelper:
    DEFAULT_CONFIG_PATH = Path("data/fleet_config.json")
    DEFAULT_FLEET_DIR = Path("C:/MT5_Fleet")

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH

    def load_fleet_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return self._create_default_fleet_template()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read fleet config from {self.config_path}: {exc}")
            return self._create_default_fleet_template()

    def _create_default_fleet_template(self) -> Dict[str, Any]:
        return {
            "schema_version": 2,
            "mode": "BROKER_DEMO",
            "anti_collision_jitter": {
                "enabled": True,
                "min_delay_ms": 250,
                "max_delay_ms": 750,
                "purpose": "Prevents exact-millisecond copy-trading signature across prop firm accounts"
            },
            "fleet": {
                "account_100k": {
                    "account_name": "$100K Client Alpha",
                    "account_id": "400001001",
                    "server": "FundingPips-Trial",
                    "terminal_path": "C:\\MT5_Fleet\\Terminal_100k\\terminal64.exe",
                    "password_env": "MT5_PASSWORD_100K",
                    "starting_balance": 100000.0,
                    "account_type": "FUNDING_PIPS",
                    "prop_model": "FUNDING_PIPS_2_STEP_STANDARD",
                    "account_stage": "EVALUATION_PHASE_1",
                    "risk_per_trade_pct": 0.0025,
                    "max_daily_loss_pct": 0.015,
                    "max_total_loss_pct": 0.04,
                    "hard_daily_loss_pct": 0.05,
                    "hard_total_loss_pct": 0.10,
                    "is_active": True,
                    "telemetry_verified": False,
                    "execution_mode": "BROKER_DEMO"
                },
                "account_50k": {
                    "account_name": "$50K Client Beta",
                    "account_id": "40000243427",
                    "server": "FundingPips-Trial",
                    "terminal_path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                    "password_env": "MT5_PASSWORD_50K",
                    "starting_balance": 50000.0,
                    "account_type": "FUNDING_PIPS",
                    "prop_model": "FUNDING_PIPS_2_STEP_STANDARD",
                    "account_stage": "EVALUATION_PHASE_1",
                    "risk_per_trade_pct": 0.0025,
                    "max_daily_loss_pct": 0.015,
                    "max_total_loss_pct": 0.04,
                    "hard_daily_loss_pct": 0.05,
                    "hard_total_loss_pct": 0.10,
                    "is_active": True,
                    "telemetry_verified": True,
                    "execution_mode": "BROKER_DEMO"
                },
                "account_25k": {
                    "account_name": "$25K Client Gamma",
                    "account_id": "400003003",
                    "server": "FundingPips-Trial",
                    "terminal_path": "C:\\MT5_Fleet\\Terminal_25k\\terminal64.exe",
                    "password_env": "MT5_PASSWORD_25K",
                    "starting_balance": 25000.0,
                    "account_type": "FUNDING_PIPS",
                    "prop_model": "FUNDING_PIPS_2_STEP_STANDARD",
                    "account_stage": "EVALUATION_PHASE_1",
                    "risk_per_trade_pct": 0.0025,
                    "max_daily_loss_pct": 0.015,
                    "max_total_loss_pct": 0.04,
                    "hard_daily_loss_pct": 0.05,
                    "hard_total_loss_pct": 0.10,
                    "is_active": True,
                    "telemetry_verified": False,
                    "execution_mode": "BROKER_DEMO"
                },
                "account_5k": {
                    "account_name": "$5K Client Micro",
                    "account_id": "400004004",
                    "server": "FundingPips-Trial",
                    "terminal_path": "C:\\MT5_Fleet\\Terminal_5k\\terminal64.exe",
                    "password_env": "MT5_PASSWORD_5K",
                    "starting_balance": 5000.0,
                    "account_type": "FUNDING_PIPS",
                    "prop_model": "FUNDING_PIPS_2_STEP_STANDARD",
                    "account_stage": "EVALUATION_PHASE_1",
                    "risk_per_trade_pct": 0.0025,
                    "max_daily_loss_pct": 0.015,
                    "max_total_loss_pct": 0.04,
                    "hard_daily_loss_pct": 0.05,
                    "hard_total_loss_pct": 0.10,
                    "is_active": True,
                    "telemetry_verified": False,
                    "execution_mode": "BROKER_DEMO"
                }
            }
        }

    def save_fleet_config(self, config: Dict[str, Any]) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as exc:
            logger.error(f"Failed to save fleet config to {self.config_path}: {exc}")
            return False

    def validate_terminal_path(self, terminal_path: str) -> Dict[str, Any]:
        p = Path(terminal_path)
        exists = p.exists() and p.is_file()
        is_exe = p.suffix.lower() == ".exe"
        return {
            "path": str(p),
            "exists": exists,
            "is_executable": is_exe,
            "valid": exists and is_exe,
            "status": "VALID_TERMINAL" if (exists and is_exe) else "TERMINAL_NOT_FOUND"
        }

    def apply_execution_jitter(self, min_ms: int = 250, max_ms: int = 750) -> float:
        """Introduces randomized micro-delay to prevent exact-millisecond copy-trading fingerprint."""
        delay_sec = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
        time.sleep(delay_sec)
        return delay_sec

    def register_account(
        self,
        account_key: str,
        account_name: str,
        account_id: str,
        server: str,
        terminal_path: str,
        password_env: str,
        starting_balance: float,
        risk_pct: float = 0.0025
    ) -> Dict[str, Any]:
        cfg = self.load_fleet_config()
        fleet = cfg.get("fleet", {})
        fleet[account_key] = {
            "account_name": account_name,
            "account_id": str(account_id),
            "server": server,
            "terminal_path": terminal_path,
            "password_env": password_env,
            "starting_balance": float(starting_balance),
            "account_type": "FUNDING_PIPS",
            "prop_model": "FUNDING_PIPS_2_STEP_STANDARD",
            "account_stage": "EVALUATION_PHASE_1",
            "risk_per_trade_pct": float(risk_pct),
            "max_daily_loss_pct": 0.015,
            "max_total_loss_pct": 0.04,
            "hard_daily_loss_pct": 0.05,
            "hard_total_loss_pct": 0.10,
            "is_active": True,
            "telemetry_verified": False,
            "execution_mode": "BROKER_DEMO"
        }
        cfg["fleet"] = fleet
        ok = self.save_fleet_config(cfg)
        return {
            "success": ok,
            "account_key": account_key,
            "account_id": account_id,
            "balance": starting_balance,
            "risk_pct": risk_pct
        }


fleet_setup_helper = FleetSetupHelper()
