"""
multi_account_auto_onboarder.py — Dynamic Multi-Account & Multi-Market Auto-Onboarder.
====================================================================================
Enables autonomous onboarding of any trading account supplied by the user:
  1. Prop Firm Evaluation Accounts (Funding Pips 25k/50k/100k, FTMO, MyFundedFX, Topstep).
  2. Personal Broker Accounts (IC Markets, Exness, Pepperstone, OANDA).
  3. Crypto Exchange Accounts (Binance Spot, Binance Futures, Hyperliquid DEX, Scalp 5M).
  4. Auto-Calibrates Risk Rules, Daily Loss Caps, Max Lots, and Asset Allowances.
  5. Dynamically updates data/fleet_config.json and routes execution.
"""

import os
import re
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Union

from src.prop_rules import build_account_policy, normalize_model

logger = logging.getLogger("MultiAccountAutoOnboarder")

_SECRET_DIRECTIVE_PATTERN = re.compile(
    r"\b(password|passwd|passphrase|api[_ -]?key|api[_ -]?secret|secret[_ -]?key|seed phrase|recovery code|private key|token)\b",
    re.IGNORECASE,
)


class MultiAccountAutoOnboarder:
    """
    Dynamic Multi-Account Onboarding & Risk Policy Calibrator.
    """

    FLEET_CONFIG_PATH = "data/fleet_config.json"

    PROP_FIRM_PROFILES = {
        "FUNDING_PIPS": {
            "name": "Funding Pips Prop Firm",
            "daily_loss_pct": 1.5,
            "max_loss_pct": 4.0,
            "risk_per_trade_pct": 0.25,
            "consistency_cap_pct": 60.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED"
        },
        "FTMO": {
            "name": "FTMO Evaluation Account",
            "daily_loss_pct": 4.0,  # 4.0% safe floor (5.0% hard limit)
            "max_loss_pct": 8.0,    # 8.0% max loss (10.0% hard limit)
            "risk_per_trade_pct": 1.0,
            "consistency_cap_pct": 50.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED"
        },
        "MYFUNDEDFX": {
            "name": "MyFundedFX Prop Firm",
            "daily_loss_pct": 4.0,  # 4.0% safe floor (5.0% hard limit)
            "max_loss_pct": 6.0,    # 6.0% safe (8.0% hard limit)
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 40.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED"
        },
        "PERSONAL_MT5": {
            "name": "Personal Live / Demo MT5 Account",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 15.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"],
            "execution_mode": "PAPER_UNVERIFIED"
        },
        "BINANCE_SPOT": {
            "name": "Binance Spot Account",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 20.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "BINANCE_FUTURES": {
            "name": "Binance USD-M Futures Account",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 20.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "HYPERLIQUID": {
            "name": "Hyperliquid On-Chain DEX Account",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 20.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTC-PERP", "ETH-PERP", "SOL-PERP"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "SCALP_5M": {
            "name": "Crypto 5M Micro Scalping Account",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 20.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BTC-PERP", "ETH-PERP"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "BITGET": {
            "name": "Bitget Crypto Futures & Spot Account",
            "daily_loss_pct": 3.0,
            "max_loss_pct": 15.0,
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "CRYPTO_EXCHANGE": {
            "name": "Crypto Spot & Perpetuals (Bitget / Binance / Hyperliquid)",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 20.0,
            "risk_per_trade_pct": 1.5,
            "consistency_cap_pct": 100.0,
            "allowed_assets": ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD"],
            "execution_mode": "PAPER_CRYPTO_UNVERIFIED"
        },
        "THE_FUNDED_TRADER": {
            "name": "The Funded Trader Standard Challenge",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 10.0,
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 50.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED",
            "news_restricted": True,
            "weekend_holding_allowed": False
        },
        "THE_5ERS": {
            "name": "5%ers High Stakes / Bootcamp",
            "daily_loss_pct": 4.0,
            "max_loss_pct": 8.0,
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 50.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED",
            "news_restricted": False,
            "weekend_holding_allowed": True
        },
        "ALPHA_CAPITAL": {
            "name": "Alpha Capital Standard Evaluation",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 10.0,
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 50.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED",
            "news_restricted": True,
            "weekend_holding_allowed": False
        },
        "E8": {
            "name": "E8 Evaluation Model",
            "daily_loss_pct": 5.0,
            "max_loss_pct": 8.0,
            "risk_per_trade_pct": 0.75,
            "consistency_cap_pct": 50.0,
            "allowed_assets": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
            "execution_mode": "PAPER_UNVERIFIED",
            "news_restricted": False,
            "weekend_holding_allowed": True
        }
    }

    PROFILE_ALIASES = {
        "FUNDING_PIPS": "FUNDING_PIPS",
        "FUNDINGPIPS": "FUNDING_PIPS",
        "FUNDING_PIP": "FUNDING_PIPS",
        "FUNDING PIPS": "FUNDING_PIPS",
        "FP": "FUNDING_PIPS",
        "FUNDING": "FUNDING_PIPS",
        "FTMO": "FTMO",
        "THE_FUNDED_TRADER": "THE_FUNDED_TRADER",
        "THEFUNDEDTRADER": "THE_FUNDED_TRADER",
        "FUNDEDTRADER": "THE_FUNDED_TRADER",
        "TFT": "THE_FUNDED_TRADER",
        "5ERS": "THE_5ERS",
        "THE_5ERS": "THE_5ERS",
        "THE5ERS": "THE_5ERS",
        "5%ERS": "THE_5ERS",
        "5%": "THE_5ERS",
        "FIVE_PERCENTERS": "THE_5ERS",
        "ALPHA_CAPITAL": "ALPHA_CAPITAL",
        "ALPHACAPITAL": "ALPHA_CAPITAL",
        "ALPHA": "ALPHA_CAPITAL",
        "E8": "E8",
        "E8_MARKETS": "E8",
        "E8MARKETS": "E8",
        "MYFUNDEDFX": "MYFUNDEDFX",
        "PERSONAL": "PERSONAL_MT5",
        "PERSONAL_MT5": "PERSONAL_MT5",
        "BINANCE": "BINANCE_FUTURES",
        "BINANCE_SPOT": "BINANCE_SPOT",
        "BINANCE_FUTURES": "BINANCE_FUTURES",
        "BITGET": "BITGET",
        "BITGET_FUTURES": "BITGET",
        "HYPERLIQUID": "HYPERLIQUID",
        "SCALP_5M": "SCALP_5M",
        "CRYPTO": "BITGET",

        "MYFUNDEDFX": "MYFUNDEDFX",
        "MY_FUNDED_FX": "MYFUNDEDFX",
        "MY FUNDED FX": "MYFUNDEDFX",
        "MFF": "MYFUNDEDFX",
        "MYFUNDED": "MYFUNDEDFX",

        "PERSONAL_MT5": "PERSONAL_MT5",
        "PERSONALMT5": "PERSONAL_MT5",
        "PERSONAL MT5": "PERSONAL_MT5",
        "PERSONAL": "PERSONAL_MT5",
        "PERSONALMT": "PERSONAL_MT5",
        "ICMARKETS": "PERSONAL_MT5",
        "EXNESS": "PERSONAL_MT5",
        "PEPPERSTONE": "PERSONAL_MT5",
        "OANDA": "PERSONAL_MT5",

        "BINANCE_SPOT": "BINANCE_SPOT",
        "BINANCESPOT": "BINANCE_SPOT",
        "BINANCE SPOT": "BINANCE_SPOT",
        "SPOT": "BINANCE_SPOT",

        "BINANCE_FUTURES": "BINANCE_FUTURES",
        "BINANCEFUTURES": "BINANCE_FUTURES",
        "BINANCE FUTURES": "BINANCE_FUTURES",
        "BINANCE_PERP": "BINANCE_FUTURES",
        "BINANCE PERP": "BINANCE_FUTURES",
        "BINANCEPERP": "BINANCE_FUTURES",
        "FUTURES": "BINANCE_FUTURES",
        "PERP": "BINANCE_FUTURES",

        "HYPERLIQUID": "HYPERLIQUID",
        "HYPERLIQUID_DEX": "HYPERLIQUID",
        "HYPERLIQUID DEX": "HYPERLIQUID",
        "HL": "HYPERLIQUID",
        "DEX": "HYPERLIQUID",

        "SCALP_5M": "SCALP_5M",
        "SCALP5M": "SCALP_5M",
        "SCALP 5M": "SCALP_5M",
        "SCALP": "SCALP_5M",
        "5M": "SCALP_5M",

        "CRYPTO_EXCHANGE": "CRYPTO_EXCHANGE",
        "CRYPTO": "CRYPTO_EXCHANGE",
        "BINANCE": "BINANCE_SPOT",
    }

    def __init__(self, config_path: str = FLEET_CONFIG_PATH):
        self.config_path = config_path
        normalized_path = os.path.normcase(os.path.abspath(self.config_path))
        default_path = os.path.normcase(os.path.abspath(self.FLEET_CONFIG_PATH))
        is_main_app_config = os.path.basename(normalized_path) == "config.json" and normalized_path != default_path
        self._persistence_enabled = not is_main_app_config
        if is_main_app_config:
            logger.warning("Fleet persistence disabled: main application config.json cannot be used as a fleet store")
        if os.path.dirname(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self.fleet: Dict[str, Any] = self._load_fleet()

    def _load_fleet(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "fleet" in data:
                        return data
            except Exception as e:
                logger.warning(f"Error loading fleet config: {e}")
        return self._default_fleet()

    def _default_fleet(self) -> Dict[str, Any]:
        return {
            "schema_version": 2,
            "mode": "EMPTY_PAPER_FLEET",
            "active_accounts": 0,
            "total_aum_potential": 0.0,
            "fleet": {}
        }

    def _save_fleet(self):
        if not self._persistence_enabled:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.fleet, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fleet config: {e}")

    @classmethod
    def normalize_account_type(cls, account_type: Optional[str], default: str = "FUNDING_PIPS") -> str:
        """
        Normalizes any alias or user string into canonical account profile key.
        """
        if not account_type:
            return default
        raw = str(account_type).strip().upper()
        
        # Direct exact match
        if raw in cls.PROP_FIRM_PROFILES:
            return raw
        if raw in cls.PROFILE_ALIASES:
            return cls.PROFILE_ALIASES[raw]

        # Normalized string without special chars
        clean = re.sub(r'[^A-Z0-9]', '', raw)
        if clean in cls.PROFILE_ALIASES:
            return cls.PROFILE_ALIASES[clean]

        # Heuristic matching
        if "MYFUNDED" in clean or "MFF" in clean:
            return "MYFUNDEDFX"
        if "FUNDING" in clean:
            return "FUNDING_PIPS"
        if "FTMO" in clean:
            return "FTMO"
        if "PERSONAL" in clean or "ICMARKET" in clean or "EXNESS" in clean:
            return "PERSONAL_MT5"
        if "SCALP" in clean or "5M" in clean:
            return "SCALP_5M"
        if "HYPERLIQUID" in clean or "DEX" in clean or "HL" == clean:
            return "HYPERLIQUID"
        if "FUTURES" in clean or "PERP" in clean:
            return "BINANCE_FUTURES"
        if "BINANCE" in clean or "SPOT" in clean:
            return "BINANCE_SPOT"
        if "THE_FUNDED_TRADER" in clean or "FUNDEDTRADER" in clean or "TFT" in clean:
            return "THE_FUNDED_TRADER"
        if "5ERS" in clean or "5%" in clean or "FIVEPERCENT" in clean:
            return "THE_5ERS"
        if "ALPHACAPITAL" in clean or "ALPHA" in clean:
            return "ALPHA_CAPITAL"
        if "E8" in clean:
            return "E8"
        if "CRYPTO" in clean:
            return "CRYPTO_EXCHANGE"

        return default

    def onboard_new_account(
        self,
        account_id: Union[int, str],
        server: str,
        balance: float,
        account_type: str = "FUNDING_PIPS",
        account_name: Optional[str] = None,
        custom_risk_pct: Optional[float] = None,
        execution_mode: Optional[str] = None,
        prop_model: Optional[str] = None,
        account_stage: Optional[str] = None,
        reward_cycle: Optional[str] = None,
        client_whatsapp: Optional[str] = None,
        password: Optional[str] = None,
        target_country: Optional[str] = None,
        strict_metadata: bool = False,
        activate: bool = True,
    ) -> Dict[str, Any]:
        """
        Dynamically registers and risk-calibrates a new trading account.
        """
        account_id_text = str(account_id or "").strip()
        server_text = str(server or "").strip()
        if password:
            os.environ[f"MT5_PASSWORD_{account_id_text}"] = str(password)
        if strict_metadata and not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", account_id_text):
            return {"success": False, "message": "Account ID must be 3-64 letters, numbers, dots, underscores, or hyphens."}
        if strict_metadata and not re.fullmatch(r"[A-Za-z0-9_.-]{2,100}", server_text):
            return {"success": False, "message": "Server must be 2-100 letters, numbers, dots, underscores, or hyphens."}
        try:
            balance_value = float(balance)
        except (TypeError, ValueError):
            return {"success": False, "message": "Starting balance must be numeric."}
        if not 50.0 <= balance_value <= 10_000_000.0:
            return {"success": False, "message": "Starting balance must be between 50 and 10,000,000."}
        if custom_risk_pct is not None:
            try:
                requested_risk = float(custom_risk_pct)
            except (TypeError, ValueError):
                return {"success": False, "message": "Risk per trade must be numeric."}
            if not 0.05 <= requested_risk <= 2.0:
                return {"success": False, "message": "Risk per trade must be between 0.05% and 2.0%."}

        canonical_type = self.normalize_account_type(account_type)
        profile = self.PROP_FIRM_PROFILES.get(canonical_type, self.PROP_FIRM_PROFILES["FUNDING_PIPS"])

        risk_pct = custom_risk_pct if custom_risk_pct is not None else profile["risk_per_trade_pct"]
        daily_loss_pct = profile["daily_loss_pct"]
        max_loss_pct = profile["max_loss_pct"]

        prop_policy: Optional[Dict[str, Any]] = None
        if canonical_type == "FUNDING_PIPS":
            selected_model = normalize_model(prop_model or "FUNDING_PIPS_2_STEP_STANDARD")
            prop_policy = build_account_policy(
                account_size=float(balance),
                model=selected_model,
                stage=account_stage,
                reward_cycle=reward_cycle,
            )
            risk_pct = float(custom_risk_pct) if custom_risk_pct is not None else prop_policy["internal_risk_per_trade_pct"]
            risk_pct = min(risk_pct, prop_policy["internal_risk_per_trade_pct"])
            daily_loss_pct = prop_policy["internal_daily_stop_pct"]
            max_loss_pct = prop_policy["internal_overall_stop_pct"]

        acc_key = f"account_{account_id_text}"
        existing = self.fleet.get("fleet", {}).get(acc_key)
        if strict_metadata and existing and (
            str(existing.get("server", "")).lower() != server_text.lower()
            or str(existing.get("account_type", "")).upper() != canonical_type
        ):
            return {
                "success": False,
                "message": "That account ID already exists with different server/type metadata; resolve it locally instead of overwriting it remotely.",
            }
        name = account_name or f"{profile['name']} #{account_id}"
        exec_mode = execution_mode or profile.get("execution_mode", "PAPER_UNVERIFIED")
        if str(exec_mode).upper().startswith("LIVE"):
            exec_mode = "LIVE_REQUESTED_LOCKED"

        bal_float = balance_value
        daily_loss_dollar_cap = round(bal_float * (daily_loss_pct / 100.0), 2)
        trailing_hwm_floor = round(bal_float * (1.0 - (max_loss_pct / 100.0)), 2)

        new_entry = {
            "account_name": name,
            "account_id": account_id_text,
            "server": server_text,
            "starting_balance": bal_float,
            "account_type": canonical_type,
            "risk_per_trade_pct": round(risk_pct / 100.0, 4) if risk_pct > 0.05 else round(risk_pct, 4),
            "max_daily_loss_pct": round(daily_loss_pct / 100.0, 4),
            "max_total_loss_pct": round(max_loss_pct / 100.0, 4),
            "daily_loss_dollar_cap": daily_loss_dollar_cap,
            "trailing_hwm_floor": trailing_hwm_floor,
            "allowed_assets": profile["allowed_assets"],
            "consistency_cap_pct": profile.get("consistency_cap_pct", 100.0),
            "is_active": bool(activate),
            "telemetry_verified": False,
            "rule_adherence": "UNVERIFIED",
            "registration_status": "METADATA_REGISTERED_AWAITING_TERMINAL_BINDING",
            "onboarded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "execution_mode": exec_mode
        }
        if client_whatsapp:
            new_entry["client_whatsapp"] = str(client_whatsapp).strip()
        if prop_policy:
            new_entry.update({
                "prop_model": prop_policy["model"],
                "account_stage": prop_policy["stage"],
                "loss_floor_type": prop_policy["loss_floor_type"],
                "profit_target_pct": prop_policy["profit_target_pct"],
                "minimum_trading_days": prop_policy["minimum_trading_days"],
                "reward_cycle": prop_policy["reward_cycle"],
                "exact_reward_cycle_required_before_master_live": prop_policy["exact_reward_cycle_required_before_master_live"],
                "hard_risk_per_trade_idea_pct": prop_policy["hard_risk_per_trade_idea_pct"],
                "legacy_risk_per_trade_idea_rule_applies": prop_policy["legacy_risk_per_trade_idea_rule_applies"],
                "firm_max_open_risk_pct": prop_policy["firm_max_open_risk_pct"],
                "striking_system_applies": prop_policy["striking_system_applies"],
                "striking_warning_trigger_pct": prop_policy["striking_warning_trigger_pct"],
                "striking_warning_count_to_breach": prop_policy["striking_warning_count_to_breach"],
                "hard_daily_loss_pct": prop_policy["hard_daily_loss_fraction"],
                "hard_total_loss_pct": prop_policy["hard_overall_loss_fraction"],
                "hard_daily_loss_dollar_cap": prop_policy["hard_daily_loss_dollars_at_start"],
                "hard_total_loss_dollar_cap": prop_policy["hard_overall_loss_dollars"],
                "internal_daily_stop_pct": prop_policy["internal_daily_stop_pct"] / 100.0,
                "internal_total_stop_pct": prop_policy["internal_overall_stop_pct"] / 100.0,
                "rules_verified_on": prop_policy["rules_verified_on"],
                "rule_source_url": prop_policy["source_url"],
                "live_readiness_stage": "PAPER",
                "enforce_internal_risk_caps": True,
            })

        self.fleet["fleet"][acc_key] = new_entry
        self.fleet["active_accounts"] = len([a for a in self.fleet["fleet"].values() if a.get("is_active")])
        self.fleet["total_aum_potential"] = sum(float(a.get("starting_balance", 0.0)) for a in self.fleet["fleet"].values())

        self._save_fleet()
        logger.info(f"Registered account metadata #{account_id_text} ({name} | ${bal_float:,.2f})")

        msg = (
            f"Account #{account_id_text} ({canonical_type}) metadata registered safely.\n"
            f"• Platform / Server: {server_text}\n"
            f"• Starting Balance: ${bal_float:,.2f}\n"
            f"• Daily Loss Cap: ${daily_loss_dollar_cap:,.2f} ({daily_loss_pct:.2f}%)\n"
            f"• Internal Loss Floor: ${trailing_hwm_floor:,.2f} ({max_loss_pct:.2f}% internal stop)\n"
            f"• Execution Mode: {exec_mode}\n"
            f"• Risk per Trade: {risk_pct:.2f}%\n"
            f"• Telemetry: UNVERIFIED — bind and verify its own terminal before activation"
        )

        return {
            "success": True,
            "account_key": acc_key,
            "account_data": new_entry,
            "message": msg
        }

    def parse_whatsapp_onboard_directive(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parses WhatsApp message strings supporting both MT5/Prop firm and Crypto directives:
        - 'onboard account 5054340275 server MetaQuotes-Demo balance 25000 type FundingPips'
        - 'onboard account 882244 server MyFundedFX-Server balance 50000 type MyFundedFX'
        - 'onboard crypto exchange Binance balance 100 type Scalp5m'
        - 'onboard crypto exchange Hyperliquid balance 500 type DEX'
        - 'onboard exchange Binance balance 1000 type BinanceSpot'
        """
        raw = text.strip()
        if not raw.lower().startswith("onboard"):
            return None
        if _SECRET_DIRECTIVE_PATTERN.search(raw):
            return {
                "success": False,
                "message": "Secret rejected. Never send an MT5 password, API key, passphrase, token, private key, seed phrase, or recovery code in WhatsApp.",
            }

        # Extract balance
        bal_match = re.search(r'balance\s+([0-9.]+)', raw, re.IGNORECASE)
        if not bal_match:
            bal_match = re.search(r'\$([0-9.]+)', raw)
        if not bal_match:
            return None
        try:
            balance = float(bal_match.group(1))
        except (TypeError, ValueError):
            return {"success": False, "message": "Starting balance must be numeric."}

        # Extract type
        type_match = re.search(r'type\s+([a-zA-Z0-9_-]+)', raw, re.IGNORECASE)
        raw_type = type_match.group(1) if type_match else None

        # Extract server
        server_match = re.search(r'server\s+([a-zA-Z0-9_.-]+)', raw, re.IGNORECASE)
        server = server_match.group(1) if server_match else None

        # Extract custom risk if specified
        risk_match = re.search(r'risk\s+([0-9.]+)%?', raw, re.IGNORECASE)
        custom_risk = float(risk_match.group(1)) if risk_match else None

        model_match = re.search(r'model\s+([a-zA-Z0-9_-]+)', raw, re.IGNORECASE)
        prop_model = model_match.group(1) if model_match else None
        stage_match = re.search(r'(?:stage|phase)\s+([a-zA-Z0-9_-]+)', raw, re.IGNORECASE)
        account_stage = stage_match.group(1) if stage_match else None

        # Check for MT5 / Prop Firm account syntax
        acc_match = re.search(r'(?:account|prop\s*firm)\s+([a-zA-Z0-9_.-]+)', raw, re.IGNORECASE)
        
        # Check for Crypto Exchange syntax
        crypto_match = re.search(r'(?:crypto\s+)?exchange\s+([a-zA-Z0-9_.-]+)', raw, re.IGNORECASE)
        crypto_direct = re.search(r'onboard\s+(?:crypto\s+)?(binance|hyperliquid|bybit|bitget)', raw, re.IGNORECASE)

        if acc_match:
            acc_id = acc_match.group(1)
            acc_type = raw_type or "FUNDING_PIPS"
            server = server or "MetaQuotes-Demo"
        elif crypto_match or crypto_direct:
            exchange_name = (crypto_match.group(1) if crypto_match else crypto_direct.group(1)).capitalize()
            acc_type = raw_type or exchange_name
            canonical_type = self.normalize_account_type(acc_type)
            acc_id = f"{exchange_name.upper()}_{int(balance)}"
            if server is None:
                if "HYPERLIQUID" in canonical_type:
                    server = "Hyperliquid-Mainnet"
                elif "BINANCE" in canonical_type:
                    server = "Binance-Live"
                elif "BITGET" in canonical_type:
                    server = "Bitget-Live"
                else:
                    server = f"{exchange_name}-Live"
        else:
            # Fallback check
            tokens = raw.split()
            if len(tokens) >= 2 and tokens[1].lower() not in ["account", "crypto", "exchange", "balance"]:
                acc_id = tokens[1]
                acc_type = raw_type or "FUNDING_PIPS"
                server = server or "MetaQuotes-Demo"
            else:
                return None

        return self.onboard_new_account(
            account_id=acc_id,
            server=server,
            balance=balance,
            account_type=acc_type,
            custom_risk_pct=custom_risk,
            prop_model=prop_model,
            account_stage=account_stage,
            strict_metadata=True,
            activate=False,
        )
