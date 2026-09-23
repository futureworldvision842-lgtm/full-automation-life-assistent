"""
fleet_risk_manager.py — Dynamic Multi-Account Risk Governor & Calibration Core.
=============================================================================
Enforces real-time risk compliance across the entire multi-account fleet:
  1. Start-of-Day (SOD 00:00 UTC) Drawdown Shields (2.5% FP, 4.0% FTMO/MFF, 5.0% Crypto).
  2. Trailing High-Water-Mark (HWM) Floor Ratchet with Starting Balance Profit Lock.
  3. 5-Stage Consistency Pacing Gauge (<20% 1.0x, 20-25% 0.8x, 25-30% 0.5x, 30-35% 0.25x, >35% lockout).
  4. 3.5x ATR Dynamic Stop-Loss & Multi-Tier Take-Profit Calculation (TP1 1.5R, TP2 2.5R, TP3 4.0R).
  5. Dynamic Lot Sizing calibrated to account equity, asset pip value, and pacing multipliers.
  6. Comprehensive Pre-Trade Risk Audit Interceptor & Fleet Telemetry Dashboard.
"""

import os
import json
import logging
import datetime
import math
from typing import Dict, Any, List, Optional, Tuple, Union

from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder

logger = logging.getLogger("FleetRiskManager")


class FleetRiskManager:
    """
    Unified Multi-Account Risk Governor and Dynamic Rule Calibrator.
    """

    DEFAULT_CONFIG_PATH = "data/fleet_config.json"
    MAX_ORDER_LOTS = 5.0

    # Default baseline ATR values per symbol category if not provided live
    DEFAULT_ATR_MAP = {
        "XAUUSD": 3.50,
        "GOLD": 3.50,
        "XAGUSD": 0.35,
        "SILVER": 0.35,
        "BTCUSD": 450.0,
        "BTCUSDT": 450.0,
        "BTC-PERP": 450.0,
        "ETHUSD": 35.0,
        "ETHUSDT": 35.0,
        "ETH-PERP": 35.0,
        "SOLUSD": 2.50,
        "SOLUSDT": 2.50,
        "SOL-PERP": 2.50,
        "BNBUSDT": 5.00,
        "XRPUSDT": 0.025,
        "EURUSD": 0.0035,
        "GBPUSD": 0.0045,
        "USDJPY": 0.45,
        "GBPJPY": 0.65,
        "AUDUSD": 0.0035,
        "USDCAD": 0.0035,
    }

    # Contract sizing multiplier (value per 1.0 full point move per 1.0 lot)
    CONTRACT_SIZE_MAP = {
        "XAUUSD": 100.0,      # 100 oz per lot ($1 move = $100)
        "GOLD": 100.0,
        "XAGUSD": 5000.0,     # 5000 oz per lot ($1 move = $5000)
        "SILVER": 5000.0,
        "EURUSD": 100000.0,   # Standard Forex lot (0.0001 = $10)
        "GBPUSD": 100000.0,
        "AUDUSD": 100000.0,
        "NZDUSD": 100000.0,
        "USDCAD": 100000.0,
        "USDCHF": 100000.0,
        "EURGBP": 100000.0,
        "EURJPY": 1000.0,     # 100,000 / 100
        "USDJPY": 1000.0,     # 100,000 / 100 (0.01 pip = ~$6.5-$10)
        "GBPJPY": 1000.0,
        "AUDJPY": 1000.0,
        "CADJPY": 1000.0,
        "CHFJPY": 1000.0,
        "NZDJPY": 1000.0,
        "BTCUSD": 1.0,        # 1 coin per unit
        "BTCUSDT": 1.0,
        "BTC-PERP": 1.0,
        "ETHUSD": 1.0,
        "ETHUSDT": 1.0,
        "ETH-PERP": 1.0,
        "SOLUSD": 1.0,
        "SOLUSDT": 1.0,
        "SOL-PERP": 1.0,
        "BNBUSDT": 1.0,
        "XRPUSDT": 1.0,
        "DOGEUSDT": 1.0,
        "ADAUSDT": 1.0,
    }

    @classmethod
    def get_contract_size(cls, symbol: str) -> float:
        """
        Dynamically resolves contract size per 1.0 standard lot.
        """
        clean_sym = symbol.upper().replace("/", "").replace(" ", "").strip()
        if clean_sym in cls.CONTRACT_SIZE_MAP:
            return cls.CONTRACT_SIZE_MAP[clean_sym]
        
        orig_clean = symbol.upper().replace("/", "").replace(" ", "").replace("-", "").strip()
        if orig_clean in cls.CONTRACT_SIZE_MAP:
            return cls.CONTRACT_SIZE_MAP[orig_clean]

        # Crypto perpetuals & tokens
        crypto_tokens = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "MATIC", "SUI", "NEAR", "PEPE", "PERP"]
        if any(tok in clean_sym for tok in crypto_tokens):
            return 1.0

        # JPY pairs
        if clean_sym.endswith("JPY"):
            return 1000.0

        # Metals
        if "XAU" in clean_sym or "GOLD" in clean_sym:
            return 100.0
        if "XAG" in clean_sym or "SILVER" in clean_sym:
            return 5000.0

        # Forex pairs (6 letters)
        fx_currencies = ["EUR", "GBP", "USD", "AUD", "NZD", "CAD", "CHF"]
        if len(clean_sym) == 6 and any(clean_sym.startswith(c) for c in fx_currencies) and any(clean_sym.endswith(c) for c in fx_currencies):
            return 100000.0

        return 100.0

    def __init__(
        self,
        config_path: str = DEFAULT_CONFIG_PATH,
        auto_onboarder: Optional[MultiAccountAutoOnboarder] = None
    ):
        self.config_path = config_path
        normalized_path = os.path.normcase(os.path.abspath(self.config_path))
        default_path = os.path.normcase(os.path.abspath(self.DEFAULT_CONFIG_PATH))
        self._persistence_enabled = not (
            os.path.basename(normalized_path) == "config.json" and normalized_path != default_path
        )
        self.auto_onboarder = auto_onboarder or MultiAccountAutoOnboarder(config_path=self.config_path)
        self.accounts_state: Dict[str, Dict[str, Any]] = {}
        self.load_fleet()

    def load_fleet(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Loads fleet configuration and synchronizes in-memory account states.
        """
        path = config_path or self.config_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "fleet" in data:
                        self._sync_accounts_from_config(data)
                        return data
            except Exception as e:
                logger.warning(f"Error loading fleet config in FleetRiskManager: {e}")

        # Fallback to auto_onboarder fleet
        if self.auto_onboarder and hasattr(self.auto_onboarder, "fleet"):
            self._sync_accounts_from_config(self.auto_onboarder.fleet)
            return self.auto_onboarder.fleet

        default_data = {
            "schema_version": 2,
            "mode": "EMPTY_PAPER_FLEET",
            "active_accounts": 0,
            "total_aum_potential": 0.0,
            "fleet": {},
        }
        self._sync_accounts_from_config(default_data)
        return default_data

    def _sync_accounts_from_config(self, fleet_data: Dict[str, Any]):
        """
        Synchronizes live telemetry tracking structures from raw config dict.
        """
        fleet_dict = fleet_data.get("fleet", {})
        for key, acc in fleet_dict.items():
            acc_id = str(acc.get("account_id", key))
            starting_bal = float(acc.get("starting_balance", 25000.0))
            
            # Preserve existing live state if already initialized
            existing = self.accounts_state.get(acc_id)
            if existing:
                existing["account_name"] = acc.get("account_name", existing["account_name"])
                existing["account_type"] = acc.get("account_type", existing["account_type"])
                existing["server"] = acc.get("server", existing["server"])
                existing["risk_per_trade_pct"] = float(acc.get("risk_per_trade_pct", existing["risk_per_trade_pct"]))
                existing["max_daily_loss_pct"] = float(acc.get("max_daily_loss_pct", existing["max_daily_loss_pct"]))
                existing["max_total_loss_pct"] = float(acc.get("max_total_loss_pct", existing["max_total_loss_pct"]))
                existing["daily_loss_dollar_cap"] = float(acc.get("daily_loss_dollar_cap", existing["daily_loss_dollar_cap"]))
                existing["allowed_assets"] = acc.get("allowed_assets", existing["allowed_assets"])
                existing["consistency_cap_pct"] = float(acc.get("consistency_cap_pct", existing.get("consistency_cap_pct", 100.0)))
                existing["is_active"] = bool(acc.get("is_active", True))
                existing["execution_mode"] = acc.get("execution_mode", existing.get("execution_mode", "PAPER_UNVERIFIED"))
                for field in (
                    "prop_model", "account_stage", "loss_floor_type", "profit_target_pct",
                    "minimum_trading_days", "reward_cycle", "exact_reward_cycle_required_before_master_live",
                    "hard_risk_per_trade_idea_pct", "legacy_risk_per_trade_idea_rule_applies",
                    "firm_max_open_risk_pct", "striking_system_applies",
                    "striking_warning_trigger_pct", "striking_warning_count_to_breach",
                    "hard_daily_loss_pct", "hard_total_loss_pct",
                    "hard_daily_loss_dollar_cap", "hard_total_loss_dollar_cap",
                    "internal_daily_stop_pct", "internal_total_stop_pct", "rules_verified_on",
                    "rule_source_url", "live_readiness_stage", "client_whatsapp",
                    "enforce_internal_risk_caps",
                ):
                    if field in acc:
                        existing[field] = acc[field]
                if "onboarded_at" in acc:
                    existing["onboarded_at"] = acc["onboarded_at"]
                continue

            # Initialize fresh account state
            self.accounts_state[acc_id] = {
                "account_id": acc_id,
                "account_key": key,
                "account_name": acc.get("account_name", f"Account #{acc_id}"),
                "server": acc.get("server", "MetaQuotes-Demo"),
                "account_type": acc.get("account_type", "FUNDING_PIPS"),
                "starting_balance": starting_bal,
                "balance": starting_bal,
                "equity": starting_bal,
                "daily_sod_equity": starting_bal,
                "daily_sod_balance": starting_bal,
                "absolute_hwm": starting_bal,
                "open_positions": [],
                "today_realized_pnl": 0.0,
                "today_unrealized_pnl": 0.0,
                "risk_per_trade_pct": float(acc.get("risk_per_trade_pct", 0.0075)),
                "max_daily_loss_pct": float(acc.get("max_daily_loss_pct", 0.025)),
                "max_total_loss_pct": float(acc.get("max_total_loss_pct", 0.06)),
                "daily_loss_dollar_cap": float(acc.get("daily_loss_dollar_cap", starting_bal * 0.025)),
                "trailing_hwm_floor": float(acc.get("trailing_hwm_floor", starting_bal * 0.94)),
                "consistency_cap_pct": float(acc.get("consistency_cap_pct", 35.0)),
                "allowed_assets": acc.get("allowed_assets", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]),
                "execution_mode": acc.get("execution_mode", "PAPER_UNVERIFIED"),
                "prop_model": acc.get("prop_model"),
                "account_stage": acc.get("account_stage"),
                "loss_floor_type": acc.get("loss_floor_type", "TRAILING_HIGH_WATER_MARK"),
                "profit_target_pct": float(acc.get("profit_target_pct", 8.0)),
                "minimum_trading_days": int(acc.get("minimum_trading_days", 0)),
                "reward_cycle": acc.get("reward_cycle"),
                "exact_reward_cycle_required_before_master_live": bool(acc.get("exact_reward_cycle_required_before_master_live", False)),
                "hard_risk_per_trade_idea_pct": acc.get("hard_risk_per_trade_idea_pct"),
                "legacy_risk_per_trade_idea_rule_applies": bool(acc.get("legacy_risk_per_trade_idea_rule_applies", False)),
                "firm_max_open_risk_pct": acc.get("firm_max_open_risk_pct"),
                "striking_system_applies": acc.get("striking_system_applies"),
                "striking_warning_trigger_pct": acc.get("striking_warning_trigger_pct"),
                "striking_warning_count_to_breach": acc.get("striking_warning_count_to_breach"),
                "hard_daily_loss_pct": float(acc.get("hard_daily_loss_pct", acc.get("max_daily_loss_pct", 0.025))),
                "hard_total_loss_pct": float(acc.get("hard_total_loss_pct", acc.get("max_total_loss_pct", 0.06))),
                "hard_daily_loss_dollar_cap": float(acc.get("hard_daily_loss_dollar_cap", acc.get("daily_loss_dollar_cap", starting_bal * 0.025))),
                "hard_total_loss_dollar_cap": float(acc.get("hard_total_loss_dollar_cap", starting_bal * float(acc.get("max_total_loss_pct", 0.06)))),
                "internal_daily_stop_pct": float(acc.get("internal_daily_stop_pct", acc.get("max_daily_loss_pct", 0.025))),
                "internal_total_stop_pct": float(acc.get("internal_total_stop_pct", acc.get("max_total_loss_pct", 0.06))),
                "rules_verified_on": acc.get("rules_verified_on"),
                "rule_source_url": acc.get("rule_source_url"),
                "live_readiness_stage": acc.get("live_readiness_stage", "PAPER"),
                "client_whatsapp": acc.get("client_whatsapp", ""),
                "enforce_internal_risk_caps": bool(acc.get("enforce_internal_risk_caps", False)),
                "is_active": bool(acc.get("is_active", True)),
                "onboarded_at": acc.get("onboarded_at", None),
                "is_locked_out": False,
                "lockout_reason": None,
                "hwm_locked_at_starting_balance": False,
                "trades_today": int(acc.get("trades_today", 0)),
                "consecutive_losses": int(acc.get("consecutive_losses", 0)),
                "server_day": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).date().isoformat(),
            }

    def save_fleet(self) -> None:
        """
        Persists state updates back to configuration storage.
        """
        if not self._persistence_enabled:
            logger.warning("Fleet persistence skipped because config.json is not a fleet data store")
            return

        out_fleet = {}
        for acc_id, st in self.accounts_state.items():
            key = st.get("account_key", f"account_{acc_id}")
            entry = {
                "account_name": st["account_name"],
                "account_id": acc_id,
                "server": st["server"],
                "starting_balance": st["starting_balance"],
                "account_type": st["account_type"],
                "risk_per_trade_pct": st["risk_per_trade_pct"],
                "max_daily_loss_pct": st["max_daily_loss_pct"],
                "max_total_loss_pct": st["max_total_loss_pct"],
                "daily_loss_dollar_cap": st["daily_loss_dollar_cap"],
                "trailing_hwm_floor": st["trailing_hwm_floor"],
                "allowed_assets": st["allowed_assets"],
                "consistency_cap_pct": st["consistency_cap_pct"],
                "is_active": st["is_active"],
                "execution_mode": st["execution_mode"]
            }
            for field in (
                "prop_model", "account_stage", "loss_floor_type", "profit_target_pct",
                "minimum_trading_days", "reward_cycle", "exact_reward_cycle_required_before_master_live",
                "hard_risk_per_trade_idea_pct", "legacy_risk_per_trade_idea_rule_applies",
                "firm_max_open_risk_pct", "striking_system_applies",
                "striking_warning_trigger_pct", "striking_warning_count_to_breach",
                "hard_daily_loss_pct", "hard_total_loss_pct",
                "hard_daily_loss_dollar_cap", "hard_total_loss_dollar_cap",
                "internal_daily_stop_pct", "internal_total_stop_pct", "rules_verified_on",
                "rule_source_url", "live_readiness_stage", "client_whatsapp",
                "enforce_internal_risk_caps",
            ):
                if st.get(field) is not None:
                    entry[field] = st[field]
            if "onboarded_at" in st and st["onboarded_at"]:
                entry["onboarded_at"] = st["onboarded_at"]
            out_fleet[key] = entry

        total_aum = sum(float(a["starting_balance"]) for a in out_fleet.values())
        active_cnt = len([a for a in out_fleet.values() if a["is_active"]])

        payload = {
            "active_accounts": active_cnt,
            "total_aum_potential": total_aum,
            "fleet": out_fleet
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fleet in FleetRiskManager: {e}")

    def get_account_state(self, account_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Retrieves live state for a given account ID or key.
        """
        str_id = str(account_id).strip()
        if str_id in self.accounts_state:
            return self.accounts_state[str_id]

        # Search by key
        for st in self.accounts_state.values():
            if st.get("account_key") == str_id or str(st.get("account_id")) == str_id:
                return st
        return None

    def update_account_telemetry(
        self,
        account_id: Union[str, int],
        balance: float,
        equity: float,
        realized_pnl_delta: float = 0.0,
        sod_reset: bool = False
    ) -> Dict[str, Any]:
        """
        Ratchets peak equity HWM, updates intraday PnL, and validates drawdown shields.
        """
        state = self.get_account_state(account_id)
        if not state:
            # Auto-register fallback
            str_id = str(account_id).strip()
            self.auto_onboarder.onboard_new_account(
                account_id=str_id,
                server="MetaQuotes-Demo",
                balance=balance,
                account_type="FUNDING_PIPS"
            )
            self.load_fleet()
            state = self.get_account_state(account_id)

        bal = float(balance)
        eq = float(equity)
        if not all(math.isfinite(value) and value >= 0 for value in (bal, eq)):
            raise ValueError("balance and equity must be finite non-negative values")

        current_server_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).date().isoformat()
        if state.get("server_day") != current_server_day:
            sod_reset = True

        if sod_reset:
            state["daily_sod_equity"] = max(bal, eq)
            state["daily_sod_balance"] = bal
            state["today_realized_pnl"] = 0.0
            state["today_unrealized_pnl"] = 0.0
            state["is_locked_out"] = False
            state["lockout_reason"] = None
            state["trades_today"] = 0
            state["consecutive_losses"] = 0
            state["server_day"] = current_server_day
            if state.get("enforce_internal_risk_caps"):
                baseline = max(bal, eq)
                state["daily_loss_dollar_cap"] = baseline * float(state.get("internal_daily_stop_pct", state["max_daily_loss_pct"]))
                state["hard_daily_loss_dollar_cap"] = baseline * float(state.get("hard_daily_loss_pct", state["max_daily_loss_pct"]))

        state["balance"] = bal
        state["equity"] = eq
        state["today_realized_pnl"] += float(realized_pnl_delta)
        state["today_unrealized_pnl"] = eq - bal

        # Ratchet absolute High-Water Mark
        if eq > state["absolute_hwm"]:
            state["absolute_hwm"] = eq

        # Recalculate Trailing HWM Floor
        starting_bal = state["starting_balance"]
        max_total_loss_pct = state["max_total_loss_pct"]
        if state.get("loss_floor_type") == "STATIC_STARTING_BALANCE":
            state["trailing_hwm_floor"] = starting_bal * (1.0 - max_total_loss_pct)
            state["hwm_locked_at_starting_balance"] = False
        else:
            raw_floor = state["absolute_hwm"] - (starting_bal * max_total_loss_pct)
            # Legacy/trailing profile ratchet.
            if raw_floor >= starting_bal:
                state["trailing_hwm_floor"] = max(raw_floor, starting_bal)
                state["hwm_locked_at_starting_balance"] = True
            else:
                state["trailing_hwm_floor"] = raw_floor

        # Evaluate risk status
        daily_shield = self.check_daily_loss_shield(account_id)
        trailing_guard = self.check_trailing_hwm_floor(account_id)
        hard_limits = self.check_firm_hard_limits(account_id)

        if not daily_shield["safe"]:
            state["is_locked_out"] = True
            state["lockout_reason"] = daily_shield["message"]
        elif not trailing_guard["safe"]:
            state["is_locked_out"] = True
            state["lockout_reason"] = trailing_guard["message"]

        return {
            "account_id": state["account_id"],
            "balance": bal,
            "equity": eq,
            "absolute_hwm": state["absolute_hwm"],
            "daily_sod_equity": state["daily_sod_equity"],
            "daily_loss_dollars": max(0.0, state["daily_sod_equity"] - eq),
            "daily_loss_pct": round(((state["daily_sod_equity"] - eq) / state["daily_sod_equity"]) * 100.0, 2) if state["daily_sod_equity"] > 0 else 0.0,
            "trailing_hwm_floor": state["trailing_hwm_floor"],
            "daily_loss_shield_ok": daily_shield["safe"],
            "trailing_floor_ok": trailing_guard["safe"],
            "is_locked_out": state["is_locked_out"],
            "lockout_reason": state["lockout_reason"],
            "firm_hard_limits_safe": hard_limits["safe"],
            "firm_hard_limit_details": hard_limits,
        }

    def check_daily_loss_shield(self, account_id: Union[str, int]) -> Dict[str, Any]:
        """
        Validates that intraday equity loss does not breach daily loss cap:
        (Equity_SOD - Equity_current) < MaxDailyLoss
        Also enforces real-time 80% daily drawdown freeze:
        Instantly freezes trading on that specific account if drawdown hits 80% of allowed daily limit.
        """
        state = self.get_account_state(account_id)
        if not state:
            return {"safe": False, "breached": True, "frozen_80_pct": True, "message": f"Account '{account_id}' not found"}

        sod_eq = state["daily_sod_equity"]
        curr_eq = state["equity"]
        max_daily_pct = state["max_daily_loss_pct"]
        max_allowed_dollar_loss = state["daily_loss_dollar_cap"]
        freeze_ratio = float(state.get("freeze_dd_ratio", 0.80))
        freeze_dollar_limit = max_allowed_dollar_loss * freeze_ratio
        freeze_pct = max_daily_pct * freeze_ratio

        intraday_loss = sod_eq - curr_eq

        if intraday_loss >= max_allowed_dollar_loss:
            return {
                "safe": False,
                "breached": True,
                "frozen_80_pct": True,
                "intraday_loss": round(intraday_loss, 2),
                "max_allowed_loss": round(max_allowed_dollar_loss, 2),
                "freeze_threshold_usd": round(freeze_dollar_limit, 2),
                "loss_pct": round((intraday_loss / sod_eq) * 100.0, 2) if sod_eq > 0 else 0.0,
                "limit_pct": round(max_daily_pct * 100.0, 2),
                "message": f"DAILY LOSS SHIELD BREACHED! Intraday Loss: ${intraday_loss:,.2f} >= Limit: ${max_allowed_dollar_loss:,.2f}"
            }

        if intraday_loss >= freeze_dollar_limit:
            return {
                "safe": False,
                "breached": False,
                "frozen_80_pct": True,
                "intraday_loss": round(intraday_loss, 2),
                "max_allowed_loss": round(max_allowed_dollar_loss, 2),
                "freeze_threshold_usd": round(freeze_dollar_limit, 2),
                "buffer_remaining": round(max_allowed_dollar_loss - intraday_loss, 2),
                "loss_pct": round((intraday_loss / sod_eq) * 100.0, 2) if sod_eq > 0 else 0.0,
                "freeze_limit_pct": round(freeze_pct * 100.0, 2),
                "limit_pct": round(max_daily_pct * 100.0, 2),
                "message": f"DAILY DRAWDOWN 80% FREEZE TRIGGERED! Intraday Loss: ${intraday_loss:,.2f} reached 80% limit (${freeze_dollar_limit:,.2f}) of daily cap (${max_allowed_dollar_loss:,.2f}). Trading frozen."
            }

        buffer_remaining = max_allowed_dollar_loss - intraday_loss
        return {
            "safe": True,
            "breached": False,
            "frozen_80_pct": False,
            "intraday_loss": max(0.0, round(intraday_loss, 2)),
            "buffer_remaining": round(buffer_remaining, 2),
            "buffer_to_freeze": max(0.0, round(freeze_dollar_limit - intraday_loss, 2)),
            "loss_pct": round((max(0.0, intraday_loss) / sod_eq) * 100.0, 2) if sod_eq > 0 else 0.0,
            "limit_pct": round(max_daily_pct * 100.0, 2),
            "message": "Daily loss within safe shield limits"
        }

    def evaluate_daily_drawdown_freeze(
        self,
        account_id: Union[str, int],
        current_equity: Optional[float] = None,
        freeze_ratio: float = 0.80
    ) -> Dict[str, Any]:
        """
        Evaluates whether account drawdown hits 80% of allowed daily limit.
        Returns detailed status and whether trading is allowed.
        """
        state = self.get_account_state(account_id)
        if not state:
            return {"status": "NOT_FOUND", "trading_allowed": False, "reason": f"Account '{account_id}' not found"}

        sod_eq = float(state["daily_sod_equity"])
        curr_eq = float(current_equity if current_equity is not None else state["equity"])
        max_daily_pct = float(state["max_daily_loss_pct"])
        max_allowed_dollar_loss = float(state["daily_loss_dollar_cap"])

        intraday_loss = max(0.0, sod_eq - curr_eq)
        loss_pct = (intraday_loss / sod_eq) if sod_eq > 0 else 0.0

        freeze_dollar = max_allowed_dollar_loss * freeze_ratio
        freeze_pct = max_daily_pct * freeze_ratio

        if intraday_loss >= max_allowed_dollar_loss:
            return {
                "status": "BREACHED",
                "is_frozen": True,
                "trading_allowed": False,
                "can_trade": False,
                "intraday_loss_usd": round(intraday_loss, 2),
                "current_loss_pct": round(loss_pct * 100.0, 2),
                "max_daily_loss_pct": round(max_daily_pct * 100.0, 2),
                "reason": f"Daily loss {loss_pct*100:.2f}% breached maximum allowed limit {max_daily_pct*100:.2f}%.",
            }
        elif intraday_loss >= freeze_dollar:
            return {
                "status": "FROZEN_80_PERCENT_SHIELD",
                "is_frozen": True,
                "trading_allowed": False,
                "can_trade": False,
                "intraday_loss_usd": round(intraday_loss, 2),
                "current_loss_pct": round(loss_pct * 100.0, 2),
                "freeze_threshold_pct": round(freeze_pct * 100.0, 2),
                "max_daily_loss_pct": round(max_daily_pct * 100.0, 2),
                "reason": f"Daily loss {loss_pct*100:.2f}% reached 80% freeze threshold ({freeze_pct*100:.2f}% of {max_daily_pct*100:.2f}%). Trading locked.",
            }
        return {
            "status": "ACTIVE",
            "is_frozen": False,
            "trading_allowed": True,
            "can_trade": True,
            "intraday_loss_usd": round(intraday_loss, 2),
            "current_loss_pct": round(loss_pct * 100.0, 2),
            "freeze_threshold_pct": round(freeze_pct * 100.0, 2),
            "buffer_remaining_usd": round(freeze_dollar - intraday_loss, 2),
            "reason": "Daily loss within safe operating limits (below 80% freeze threshold).",
        }

    def check_trailing_hwm_floor(self, account_id: Union[str, int]) -> Dict[str, Any]:
        """
        Validates that Equity_current > Floor_HWM:
        Floor_HWM = HWM_abs - (StartingBalance * MaxTotalLossPct)
        """
        state = self.get_account_state(account_id)
        if not state:
            return {"safe": False, "breached": True, "message": f"Account '{account_id}' not found"}

        curr_eq = state["equity"]
        floor = state["trailing_hwm_floor"]
        cushion = curr_eq - floor

        floor_label = "Static loss floor" if state.get("loss_floor_type") == "STATIC_STARTING_BALANCE" else "Trailing HWM floor"
        if curr_eq <= floor:
            return {
                "safe": False,
                "breached": True,
                "current_equity": round(curr_eq, 2),
                "trailing_floor": round(floor, 2),
                "deficit": round(floor - curr_eq, 2),
                "message": f"{floor_label.upper()} BREACHED! Equity ${curr_eq:,.2f} <= Floor ${floor:,.2f}"
            }

        return {
            "safe": True,
            "breached": False,
            "current_equity": round(curr_eq, 2),
            "trailing_floor": round(floor, 2),
            "cushion": round(cushion, 2),
            "hwm_locked_at_starting_balance": state.get("hwm_locked_at_starting_balance", False),
            "floor_type": state.get("loss_floor_type", "TRAILING_HIGH_WATER_MARK"),
            "message": f"{floor_label} safe. Cushion to internal stop: ${cushion:,.2f}"
        }

    def check_firm_hard_limits(self, account_id: Union[str, int]) -> Dict[str, Any]:
        """Report official breach-line distance separately from tighter internal stops."""
        state = self.get_account_state(account_id)
        if not state:
            return {"safe": False, "message": f"Account '{account_id}' not found"}
        equity = float(state["equity"])
        starting = float(state["starting_balance"])
        hard_daily_cap = float(state.get("hard_daily_loss_dollar_cap", state["daily_loss_dollar_cap"]))
        daily_baseline = float(state["daily_sod_equity"])
        daily_floor = daily_baseline - hard_daily_cap
        hard_total_cap = float(state.get("hard_total_loss_dollar_cap", starting * float(state.get("hard_total_loss_pct", state["max_total_loss_pct"]))))
        if state.get("loss_floor_type") == "TRAILING_HIGH_WATER_MARK":
            overall_floor = float(state["absolute_hwm"]) - hard_total_cap
        else:
            overall_floor = starting - hard_total_cap
        safe = equity > daily_floor and equity > overall_floor
        return {
            "safe": safe,
            "equity": round(equity, 2),
            "daily_hard_floor": round(daily_floor, 2),
            "overall_hard_floor": round(overall_floor, 2),
            "daily_cushion": round(equity - daily_floor, 2),
            "overall_cushion": round(equity - overall_floor, 2),
            "message": "Firm hard-limit cushions are positive" if safe else "FIRM HARD LIMIT REACHED OR BREACHED",
        }

    def calculate_consistency_pacing(
        self,
        account_id: Union[str, int],
        profit_target: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        5-stage institutional consistency pacing gauge:
          - Stage 1 (<20%): 1.0x risk multiplier (OPTIMAL)
          - Stage 2 (20%-25%): 0.8x risk multiplier (CAUTION)
          - Stage 3 (25%-30%): 0.5x risk multiplier (CONSERVATIVE)
          - Stage 4 (30%-35%): 0.25x risk multiplier (MAX_DERISK)
          - Stage 5 (>35%): 0.0x risk multiplier (LOCKOUT - daily entries paused)
        """
        state = self.get_account_state(account_id)
        starting_bal = state["starting_balance"] if state else 25000.0
        
        # Target profit defaults to 8% evaluation milestone (e.g. $2,000 on 25k)
        configured_target_pct = float(state.get("profit_target_pct", 8.0)) if state else 8.0
        target = profit_target if profit_target and profit_target > 0 else (starting_bal * configured_target_pct / 100.0)

        # Intraday profit = equity gain from SOD baseline
        sod_eq = state["daily_sod_equity"] if state else starting_bal
        curr_eq = state["equity"] if state else starting_bal
        today_profit = max(0.0, curr_eq - sod_eq + (state.get("today_realized_pnl", 0.0) if state else 0.0))

        pacing_pct = (today_profit / target) * 100.0 if target > 0 else 0.0

        if pacing_pct < 20.0:
            stage = 1
            multiplier = 1.0
            status = "OPTIMAL"
            can_trade = True
        elif pacing_pct < 25.0:
            stage = 2
            multiplier = 0.8
            status = "CAUTION"
            can_trade = True
        elif pacing_pct < 30.0:
            stage = 3
            multiplier = 0.5
            status = "CONSERVATIVE"
            can_trade = True
        elif pacing_pct <= 35.0:
            stage = 4
            multiplier = 0.25
            status = "MAX_DERISK"
            can_trade = True
        else:
            stage = 5
            multiplier = 0.0
            status = "LOCKOUT"
            can_trade = False

        return {
            "stage": stage,
            "pacing_pct": round(pacing_pct, 2),
            "risk_multiplier": multiplier,
            "status": status,
            "can_trade": can_trade,
            "today_profit": round(today_profit, 2),
            "profit_target": round(target, 2),
            "message": f"Stage {stage} ({status}): Pacing {pacing_pct:.1f}% of target. Risk multiplier: {multiplier:.2f}x"
        }

    def calculate_atr_stops(
        self,
        symbol: str,
        current_price: float,
        side: str,
        atr_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates 3.5x ATR dynamic stops and multi-tier Take Profits:
          - SL = Entry - (3.5 * ATR) [BUY] or Entry + (3.5 * ATR) [SELL]
          - TP1 = 1.5R (Scale 50% + Breakeven Lock)
          - TP2 = 2.5R (Primary Target)
          - TP3 = 4.0R (Runner Trailing Target)
        """
        clean_sym = symbol.upper().replace("/", "").replace(" ", "").strip()
        price = float(current_price)
        norm_side = side.upper().strip()

        # Resolve ATR
        if atr_value is not None and float(atr_value) > 0:
            atr = float(atr_value)
        else:
            atr = self.DEFAULT_ATR_MAP.get(clean_sym)
            if not atr:
                # Generic fallback: 0.5% of price
                atr = price * 0.005

        sl_distance = 3.5 * atr

        if norm_side in ["BUY", "LONG"]:
            sl = round(price - sl_distance, 5)
            tp1 = round(price + (1.5 * sl_distance), 5)
            tp2 = round(price + (2.5 * sl_distance), 5)
            tp3 = round(price + (4.0 * sl_distance), 5)
        else:
            sl = round(price + sl_distance, 5)
            tp1 = round(price - (1.5 * sl_distance), 5)
            tp2 = round(price - (2.5 * sl_distance), 5)
            tp3 = round(price - (4.0 * sl_distance), 5)

        return {
            "symbol": clean_sym,
            "side": "BUY" if norm_side in ["BUY", "LONG"] else "SELL",
            "entry_price": price,
            "atr": round(atr, 5),
            "sl_distance": round(sl_distance, 5),
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr_tp1": 1.5,
            "rr_tp2": 2.5,
            "rr_tp3": 4.0
        }

    def calculate_dynamic_lot_size(
        self,
        account_id: Union[str, int],
        symbol: str,
        entry_price: float,
        sl_price: float,
        custom_risk_pct: Optional[float] = None
    ) -> float:
        """
        Computes risk-calibrated position lot sizing clamped to valid broker bounds.
        """
        state = self.get_account_state(account_id)
        equity = state["equity"] if state else 25000.0

        # Base risk percentage
        if custom_risk_pct is not None:
            raw_risk = float(custom_risk_pct)
            base_risk_pct = (raw_risk / 100.0) if raw_risk > 0.05 else raw_risk
        elif state:
            raw_state_risk = float(state["risk_per_trade_pct"])
            base_risk_pct = raw_state_risk / 100.0 if raw_state_risk > 0.05 else raw_state_risk
        else:
            base_risk_pct = 0.0075

        # Factor in Consistency Pacing multiplier
        pacing = self.calculate_consistency_pacing(account_id)
        pacing_mult = pacing.get("risk_multiplier", 1.0)
        effective_risk_pct = base_risk_pct * pacing_mult

        if effective_risk_pct <= 0:
            return 0.0

        risk_dollars = min(equity * effective_risk_pct, 100.0)
        sl_dist = abs(float(entry_price) - float(sl_price))
        if sl_dist <= 0:
            return 0.01

        clean_sym = symbol.upper().replace("/", "").replace(" ", "").strip()
        contract_size = self.get_contract_size(clean_sym)

        # Dollar risk per 1.0 lot
        dollar_per_lot = sl_dist * contract_size
        if dollar_per_lot <= 0:
            return 0.01

        raw_lots = risk_dollars / dollar_per_lot

        # Never round a genuinely unaffordable position up to the broker minimum.
        min_lot = 0.001 if any(token in clean_sym for token in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA")) else 0.01
        if state and state.get("enforce_internal_risk_caps") and raw_lots < min_lot:
            return 0.0

        # Determine asset-specific maximum lot ceilings
        if any(token in clean_sym for token in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA")):
            asset_max_lot = 0.01  # Crypto: max 0.01 lots
        elif "XAU" in clean_sym or "GOLD" in clean_sym:
            asset_max_lot = 0.10  # Gold: max 0.10 lots
        else:
            asset_max_lot = 0.20  # Forex & other assets: max 0.20 lots

        # Clamping based on asset type
        if any(token in clean_sym for token in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA")):
            # Crypto sizing
            clamped = max(0.001, min(asset_max_lot, raw_lots))
            # Always round volume down to the broker step. Nearest rounding can
            # silently exceed the approved dollar-risk budget.
            return round(max(0.001, math.floor((clamped + 1e-12) / 0.001) * 0.001), 3)
        else:
            # Forex & Metals sizing
            clamped = max(0.01, min(asset_max_lot, raw_lots))
            return round(max(0.01, math.floor((clamped + 1e-12) / 0.01) * 0.01), 2)

    def calculate_position_size(self, current_equity: float, sl_pips: float, symbol: str = "EURUSD", *args, **kwargs) -> float:
        """
        Calculates position lot size adhering strictly to funded prop firm rules:
        - Gold (XAUUSD): max 0.10 lots
        - Forex (EURUSD, GBPUSD, etc.): max 0.20 lots
        - Crypto (BTCUSD, ETHUSD, SOLUSD): max 0.01 lots
        - Dollar risk cap: min(current_equity * (risk_pct / 100.0), 100.0)
        """
        if sl_pips <= 0:
            return 0.01

        risk_pct = 0.25
        risk_amount = min(current_equity * (risk_pct / 100.0), 100.0)
        sym = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")

        if any(tok in sym for tok in ["BTC", "ETH", "SOL"]):
            pip_value = 1.0
            max_lot = 0.01
        elif "XAU" in sym or "GOLD" in sym:
            pip_value = 10.0
            max_lot = 0.10
        elif "JPY" in sym:
            pip_value = 6.50
            max_lot = 0.20
        else:
            pip_value = 10.0
            max_lot = 0.20

        lot_size = risk_amount / (sl_pips * pip_value)
        lot_size = round(lot_size, 2)
        lot_size = max(0.01, min(lot_size, max_lot))
        return lot_size

    def validate_pre_trade_risk(
        self,
        account_id: Union[str, int],
        symbol: str,
        lot_size: float,
        side: str,
        entry_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        news_lockout_active: bool = False,
    ) -> Tuple[bool, str]:
        """
        Comprehensive pre-trade risk audit returning (approved: bool, reason: str).
        """
        state = self.get_account_state(account_id)
        if not state:
            return False, f"Account '{account_id}' not found in fleet"

        if not state.get("is_active", True):
            return False, f"Account '{account_id}' is deactivated"

        if state.get("is_locked_out", False):
            return False, f"Account locked out: {state.get('lockout_reason', 'Drawdown limit reached')}"

        # 0. Economic News Blackout Audit (15-Minute Pre/Post High Impact News)
        if news_lockout_active and state.get("news_restricted", True):
            return False, "15-minute high-impact economic news blackout active. Trading restricted."

        clean_sym = symbol.upper().replace("/", "").replace(" ", "").strip()
        allowed = [s.upper().replace("/", "").replace(" ", "").strip() for s in state.get("allowed_assets", [])]
        
        # Check asset permission
        if allowed and clean_sym not in allowed:
            # Allow common cross-matching (e.g. XAUUSD vs GOLD, BTCUSD vs BTCUSDT)
            matched = any(clean_sym in a or a in clean_sym for a in allowed)
            if not matched:
                return False, f"Asset '{clean_sym}' not permitted for account type '{state['account_type']}'"

        # 1. Daily Loss Shield Audit
        daily_check = self.check_daily_loss_shield(account_id)
        if not daily_check["safe"]:
            return False, daily_check["message"]

        # 2. Trailing Floor Audit
        floor_check = self.check_trailing_hwm_floor(account_id)
        if not floor_check["safe"]:
            return False, floor_check["message"]

        # 3. Consistency Pacing Audit
        pacing = self.calculate_consistency_pacing(account_id)
        if not pacing["can_trade"]:
            return False, f"Consistency pacing lockout (>35% daily target reached: {pacing['pacing_pct']}%)"

        # 4. Stop Loss Orientation Audit
        norm_side = side.upper().strip()
        if entry_price is not None and sl_price is not None:
            ep = float(entry_price)
            sl = float(sl_price)
            if norm_side in ["BUY", "LONG"] and sl >= ep:
                return False, f"Invalid BUY Stop Loss: SL (${sl}) must be below Entry (${ep})"
            if norm_side in ["SELL", "SHORT"] and sl <= ep:
                return False, f"Invalid SELL Stop Loss: SL (${sl}) must be above Entry (${ep})"

        # 5. Take Profit R:R Validation (if provided)
        if entry_price is not None and sl_price is not None and tp_price is not None:
            ep = float(entry_price)
            sl = float(sl_price)
            tp = float(tp_price)
            sl_dist = abs(ep - sl)
            tp_dist = abs(tp - ep)
            if sl_dist > 0:
                rr = tp_dist / sl_dist
                if rr < 0.95:
                    return False, f"Invalid Trade Risk:Reward ratio {rr:.2f} < 1.0 minimum safety floor"

        # 6. Numeric/Volume Audit
        numeric = [float(lot_size)]
        numeric.extend(float(v) for v in (entry_price, sl_price, tp_price) if v is not None)
        if not all(math.isfinite(v) for v in numeric):
            return False, "Trade contains NaN or infinite numeric values"
        if float(lot_size) <= 0 or float(lot_size) > self.MAX_ORDER_LOTS:
            return False, f"Lot size must be > 0 and <= {self.MAX_ORDER_LOTS:g}"

        if state.get("enforce_internal_risk_caps"):
            if int(state.get("trades_today", 0)) >= 3:
                return False, "Internal daily trade-count lockout reached"
            if int(state.get("consecutive_losses", 0)) >= 3:
                return False, "Three consecutive losses triggered the daily lockout"
            if entry_price is None or sl_price is None or tp_price is None:
                return False, "Live-ready accounts require explicit entry, SL, and TP"

            ep = float(entry_price)
            stop = float(sl_price)
            contract_size = self.get_contract_size(clean_sym)
            proposed_risk = abs(ep - stop) * contract_size * float(lot_size)
            equity = float(state["equity"])
            configured_risk = float(state.get("risk_per_trade_pct", 0.0025))
            if configured_risk > 0.05:
                configured_risk /= 100.0
            per_trade_budget = equity * min(configured_risk, 0.0025)
            if proposed_risk > per_trade_budget * 1.02:
                return False, f"Proposed risk ${proposed_risk:.2f} exceeds internal per-trade budget ${per_trade_budget:.2f}"

            open_positions = state.get("open_positions", [])
            open_risk = sum(max(0.0, float(item.get("risk_dollars", 0.0))) for item in open_positions)
            if open_risk + proposed_risk > equity * 0.005:
                return False, "Fleet account open-risk cap (0.50% equity) would be exceeded"
            correlated_risk = sum(
                max(0.0, float(item.get("risk_dollars", 0.0)))
                for item in open_positions
                if str(item.get("symbol", "")).upper() == clean_sym and str(item.get("side", "")).upper() == norm_side
            )
            if correlated_risk + proposed_risk > equity * 0.0035:
                return False, "Correlated trade-idea risk cap (0.35% equity) would be exceeded"
            if proposed_risk > float(daily_check.get("buffer_remaining", 0.0)) * 0.75:
                return False, "Proposed risk would consume the protected daily-loss buffer"
            if proposed_risk > float(floor_check.get("cushion", 0.0)) * 0.75:
                return False, "Proposed risk would consume the protected overall-loss buffer"

        return True, "APPROVED_PRE_TRADE_STRESS_SAFE"

    def register_open_position(self, account_id: Union[str, int], position: Dict[str, Any]) -> None:
        state = self.get_account_state(account_id)
        if not state:
            raise ValueError(f"Account '{account_id}' not found")
        state.setdefault("open_positions", []).append(dict(position))
        state["trades_today"] = int(state.get("trades_today", 0)) + 1

    def release_position(self, account_id: Union[str, int], ticket: Any, *, realized_pnl: float = 0.0) -> None:
        state = self.get_account_state(account_id)
        if not state:
            return
        state["open_positions"] = [item for item in state.get("open_positions", []) if str(item.get("ticket")) != str(ticket)]
        pnl = float(realized_pnl)
        state["consecutive_losses"] = int(state.get("consecutive_losses", 0)) + 1 if pnl < 0 else 0

    def get_fleet_risk_dashboard(self) -> str:
        """
        Formats a comprehensive telemetry summary string across all accounts in the fleet.
        """
        lines = [
            "🛡️ *FLEET RISK & DRAWDOWN TELEMETRY DASHBOARD*",
            "═════════════════════════════════════════════"
        ]

        total_aum = sum(st["equity"] for st in self.accounts_state.values())
        active_count = len([st for st in self.accounts_state.values() if st["is_active"]])

        lines.append(f"💼 *Total Traded Fleet Equity:* ${total_aum:,.2f}")
        lines.append(f"⚡ *Active Traded Accounts:* {active_count} / {len(self.accounts_state)}")
        lines.append("")

        for acc_id, st in self.accounts_state.items():
            status_badge = "🔴 LOCKED" if st["is_locked_out"] else ("🟢 ACTIVE" if st["is_active"] else "⚪ INACTIVE")
            daily_loss = max(0.0, st["daily_sod_equity"] - st["equity"])
            floor_cushion = max(0.0, st["equity"] - st["trailing_hwm_floor"])
            pacing = self.calculate_consistency_pacing(acc_id)

            lines.append(f"📌 *{st['account_name']}* [{status_badge}]")
            lines.append(f"  • Login/ID: #{acc_id} | Mode: {st['execution_mode']}")
            lines.append(f"  • Balance: ${st['balance']:,.2f} | Equity: ${st['equity']:,.2f}")
            lines.append(f"  • Daily Drawdown: ${daily_loss:,.2f} / ${st['daily_loss_dollar_cap']:,.2f} Cap")
            lines.append(f"  • Trailing Floor: ${st['trailing_hwm_floor']:,.2f} (Cushion: ${floor_cushion:,.2f})")
            lines.append(f"  • Pacing: Stage {pacing['stage']} ({pacing['status']} - {pacing['risk_multiplier']}x risk)")
            lines.append("")

        return "\n".join(lines).strip()
