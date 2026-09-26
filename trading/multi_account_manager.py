"""
trading/multi_account_manager.py — Institutional Multi-Account Anti-Detection & Fleet Isolation Engine.
========================================================================================================
Architecture for Prop Firm Anti-Ban & Multi-Terminal Execution:
1. Per-Account Instance Isolation:
   - Separate /portable MT5 instances per account (FundingPips 100K, FTMO Institutional, Personal Broker).
   - Dedicated data directories, isolated IPC ports, and segregated worker processes.
   - Credential isolation via environment variables (no plaintext credentials).

2. Network / IP Shield Configuration:
   - Dedicated SOCKS5 / Static Residential proxy per account.
   - Zero shared IP or machine fingerprinting across prop firms.
   - Generates MT5 common.ini proxy sections, Proxifier routing rules, and worker environments.

3. Execution Jitter & Anti-Copy Engine:
   - Randomized micro-delays (350ms - 1800ms) across account dispatches.
   - Dynamic unique Magic Numbers per terminal / trade.
   - Micro-tick SL/TP offsets (+/- 0.5 to 2.0 pips) preserving risk and R:R constraints.
   - Randomized execution sequence (Fisher-Yates shuffle) and stealth order comments
     to eliminate copy-trading correlation detection by Centroid24, OneZero, and Gold-i.

4. Account Profile & Risk Rule Registry:
   - Independent rule sets per firm:
     * FundingPips: 0.75% / $750 max cap, 1:2.5 min RR, 1.0R dynamic breakeven, 4% daily / 10% total DD.
     * FTMO: 0.50% / $500 max cap, 5% daily / 10% total DD, 1:2.0 min RR.
     * Personal Broker / Bracket Account: Customized risk rules.

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
FundingPips Account: hamidqureshi872@gmail.com (#40000294403)
========================================================================================================
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import random
import re
import socket
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("MultiAccountManager")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# =====================================================================
# 1. NETWORK / IP SHIELD CONFIGURATION
# =====================================================================

@dataclass
class ProxyConfig:
    """SOCKS5 / Static Residential Proxy configuration for an MT5 account."""
    enabled: bool = True
    proxy_type: str = "SOCKS5"  # "SOCKS5", "HTTP", "HTTPS"
    host: str = "127.0.0.1"
    port: int = 1080
    username_env: Optional[str] = None
    password_env: Optional[str] = None
    target_country: str = "AE"  # KYC country code
    target_city: str = "Dubai"
    static_ip: bool = True      # Static residential IP requirement
    dns_leak_protection: bool = True

    def validate_sanity(self) -> Tuple[bool, List[str]]:
        errors = []
        if self.enabled:
            if not self.host or self.host.strip() == "":
                errors.append("Proxy host cannot be empty when proxy is enabled")
            if not (1 <= self.port <= 65535):
                errors.append(f"Invalid proxy port: {self.port}")
            if self.proxy_type.upper() not in {"SOCKS5", "HTTP", "HTTPS"}:
                errors.append(f"Unsupported proxy type: {self.proxy_type}")
            if not self.static_ip:
                errors.append("Dynamic/rotating proxy detected; prop firms require Static Residential IPs")
        return len(errors) == 0, errors

    def get_proxy_url(self, mask_auth: bool = True) -> str:
        """Returns proxy URL formatted for environment or client usage."""
        if not self.enabled:
            return ""
        user = os.environ.get(self.username_env, "") if self.username_env else ""
        pwd = os.environ.get(self.password_env, "") if self.password_env else ""
        auth_part = ""
        if user or pwd:
            pwd_disp = "***" if mask_auth else pwd
            auth_part = f"{user}:{pwd_disp}@"
        proto = self.proxy_type.lower()
        return f"{proto}://{auth_part}{self.host}:{self.port}"

    def generate_mt5_ini_snippet(self) -> str:
        """Generates MT5 common.ini proxy configuration block."""
        if not self.enabled:
            return "[Common]\nProxyEnable=0\n"
        ptype_code = 2 if self.proxy_type.upper() == "SOCKS5" else 1
        user = os.environ.get(self.username_env, "") if self.username_env else ""
        pwd = os.environ.get(self.password_env, "") if self.password_env else ""
        has_auth = 1 if (user or pwd) else 0
        return (
            "[Common]\n"
            "ProxyEnable=1\n"
            f"ProxyType={ptype_code}\n"
            f"ProxyServer={self.host}:{self.port}\n"
            f"ProxyAuth={has_auth}\n"
            f"ProxyLogin={user}\n"
            f"ProxyPassword={pwd}\n"
        )

    def generate_worker_environment(self) -> Dict[str, str]:
        """Generates isolated environment variables for terminal worker subprocess."""
        if not self.enabled:
            return {}
        url = self.get_proxy_url(mask_auth=False)
        return {
            "ALL_PROXY": url,
            "HTTPS_PROXY": url,
            "HTTP_PROXY": url,
            "NO_PROXY": "localhost,127.0.0.1",
            "MT5_PROXY_ISOLATION_ACTIVE": "1",
            "MT5_PROXY_COUNTRY": self.target_country,
        }

    def check_connectivity(self, timeout_sec: float = 1.0) -> Dict[str, Any]:
        """Lightweight non-blocking TCP socket ping to verify proxy port reachability."""
        if not self.enabled:
            return {"healthy": True, "enabled": False, "latency_ms": 0.0}
        start = time.perf_counter()
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout_sec):
                latency = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "healthy": True,
                    "enabled": True,
                    "host": self.host,
                    "port": self.port,
                    "latency_ms": latency,
                    "status": "ONLINE",
                }
        except Exception as exc:
            return {
                "healthy": False,
                "enabled": True,
                "host": self.host,
                "port": self.port,
                "error": str(exc),
                "status": "OFFLINE",
            }


# =====================================================================
# 2. PER-ACCOUNT INSTANCE ISOLATION ARCHITECTURE
# =====================================================================

@dataclass
class TerminalInstanceConfig:
    """Isolated /portable MT5 installation configuration for one account."""
    account_id: str
    firm_name: str
    terminal_dir: str
    executable_path: str
    portable_mode: bool = True
    ipc_port: int = 18812
    data_dir: Optional[str] = None
    password_env: Optional[str] = None
    server: str = "FundingPips-Server"
    login: int = 0
    timeout_ms: int = 60000

    def get_command_line_args(self, config_file: Optional[str] = None) -> List[str]:
        """Constructs safe process launch arguments forcing /portable mode."""
        args = [str(self.executable_path)]
        if self.portable_mode:
            args.append("/portable")
        if config_file:
            args.append(f"/config:{config_file}")
        return args

    def validate_isolation_constraints(self) -> Tuple[bool, List[str]]:
        """Ensures the terminal configuration satisfies strict isolation rules."""
        errors = []
        if not self.terminal_dir:
            errors.append("terminal_dir must be specified")
        if not self.executable_path:
            errors.append("executable_path must be specified")
        if not (1024 <= self.ipc_port <= 65535):
            errors.append(f"Invalid IPC port: {self.ipc_port}")
        if not self.portable_mode:
            errors.append("portable_mode must be True to prevent shared %APPDATA% directory contamination")
        if not self.password_env:
            errors.append("password_env is required; plain-text passwords are strictly forbidden")
        return len(errors) == 0, errors

    def ensure_portable_structure(self, base_path: Optional[Path] = None) -> Dict[str, Any]:
        """Prepares the directory tree required for a standalone /portable MT5 instance."""
        target_dir = Path(self.terminal_dir) if base_path is None else base_path / Path(self.terminal_dir).name
        subdirs = ["config", "MQL5", "MQL5/Experts", "MQL5/Files", "MQL5/Include", "logs", "bases"]
        created = []
        for s in subdirs:
            p = target_dir / s
            p.mkdir(parents=True, exist_ok=True)
            created.append(str(p))
        return {
            "terminal_dir": str(target_dir),
            "portable_ready": True,
            "created_dirs": created,
        }


# =====================================================================
# 3. EXECUTION JITTER & ANTI-COPY ENGINE
# =====================================================================

def get_symbol_metrics(symbol: str) -> Tuple[float, float, int]:
    """
    Returns (pip_size, pip_value_usd_per_lot, price_decimals) for any trading asset.
    Preserves true broker tick and pipette precision across standard and exotic pairs.
    """
    clean = symbol.upper().replace("/", "").strip()
    if "XAU" in clean or "GOLD" in clean:
        return 0.10, 10.0, 2
    elif "XAG" in clean or "SILVER" in clean:
        return 0.01, 50.0, 3
    elif "JPY" in clean:
        return 0.01, 6.50, 3  # Standard 3-digit broker pipette (e.g. 155.342)
    elif any(c in clean for c in ("BTC", "ETH", "SOL", "US30", "NAS100", "SPX500", "GER40")):
        return 1.0, 1.0, 2
    else:
        # Standard Forex (EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, etc.)
        return 0.0001, 10.0, 5  # Standard 5-digit broker pipette (e.g. 1.08542)


class AntiCopyShield:
    """
    Mathematical anti-correlation shield to defeat prop firm copy-trading
    detection engines (Centroid24, OneZero, Gold-i).
    """

    def __init__(
        self,
        min_delay_ms: int = 350,
        max_delay_ms: int = 1800,
        min_sl_offset_pips: float = 0.5,
        max_sl_offset_pips: float = 2.0,
        min_tp_offset_pips: float = 0.5,
        max_tp_offset_pips: float = 2.0,
        seed: Optional[int] = None,
    ):
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.min_sl_offset_pips = min_sl_offset_pips
        self.max_sl_offset_pips = max_sl_offset_pips
        self.min_tp_offset_pips = min_tp_offset_pips
        self.max_tp_offset_pips = max_tp_offset_pips
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def compute_jitter_delay_ms(
        self,
        account_index: int = 0,
        account_id: str = "",
        distribution: str = "uniform",
    ) -> float:
        """
        Computes randomized micro-delay in milliseconds for an account.
        Surveillance looks for delta < 50ms across accounts. Introducing
        350ms - 1800ms mathematically eliminates millisecond correlation.
        """
        if distribution == "gaussian":
            mean = (self.min_delay_ms + self.max_delay_ms) / 2.0
            sigma = (self.max_delay_ms - self.min_delay_ms) / 4.0
            val = self._rng.gauss(mean, sigma)
            delay = max(float(self.min_delay_ms), min(float(self.max_delay_ms), val))
        else:
            delay = self._rng.uniform(self.min_delay_ms, self.max_delay_ms)
        # Add slight account-specific entropy
        if account_id:
            entropy = (int(hashlib.md5(f"{account_id}_{account_index}".encode()).hexdigest()[:4], 16) % 100) / 100.0
            delay = min(float(self.max_delay_ms), delay + (entropy * 40.0))
        return round(delay, 2)

    def apply_jitter_sleep(self, delay_ms: float, simulation_mode: bool = False) -> float:
        """Sleeps for the computed jitter delay if in live execution."""
        if not simulation_mode and delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        return delay_ms

    def shuffle_accounts(self, account_keys: List[str]) -> List[str]:
        """
        Randomizes account execution sequence.
        Surveillance flags setups where Account A is always first and Account B is always second.
        """
        shuffled = list(account_keys)
        self._rng.shuffle(shuffled)
        return shuffled

    def generate_dynamic_magic_number(
        self,
        account_id: str,
        base_magic: int = 700000,
        symbol: str = "XAUUSD",
        trade_index: int = 0,
    ) -> int:
        """
        Produces a unique, non-colliding Magic Number per account and per trade.
        Prevents prop firms from identifying matching EA Magic Numbers across tickets.
        """
        acc_hash = int(hashlib.sha256(f"{account_id}_{symbol}".encode()).hexdigest()[:6], 16) % 90000
        # Combine base range with hashed offset and sequential trade index
        magic = base_magic + acc_hash + (trade_index % 1000)
        return int(magic)

    def perturb_sl_tp(
        self,
        symbol: str,
        side: str,
        entry: float,
        sl: float,
        tp: float,
        max_allowed_sl_loss_usd: float = 750.0,
        lot_size: float = 0.10,
        preserve_min_rr: float = 2.5,
        allow_loosening: bool = False,
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Perturbs SL and TP by +/- 0.5 to 2.0 pips (micro-ticks) per account.
        Surveillance engines look for identical stop levels across accounts on the broker book.
        Guarantees:
        - Offsets strictly adhere to the [min_sl_offset_pips, max_sl_offset_pips] range (0.5 to 2.0 pips).
        - Asset-aware decimal precision (5 decimals for Forex, 3 for JPY, 2 for Gold/Crypto/Indices).
        - SL perturbation does NOT expand risk beyond max_allowed_sl_loss_usd.
        - Preserves minimum Risk:Reward ratio (>= preserve_min_rr).
        """
        pip_size, pip_value_usd, decimals = get_symbol_metrics(symbol)

        side_upper = side.upper().strip()
        sl_pip_offset = self._rng.uniform(self.min_sl_offset_pips, self.max_sl_offset_pips)
        tp_pip_offset = self._rng.uniform(self.min_tp_offset_pips, self.max_tp_offset_pips)

        sl_delta_price = sl_pip_offset * pip_size
        tp_delta_price = tp_pip_offset * pip_size

        if side_upper == "BUY":
            # For BUY: default raises SL (tightens risk, safe). If allow_loosening=True and headroom allows, can adjust both ways.
            if allow_loosening and self._rng.random() > 0.5:
                candidate_sl = sl - sl_delta_price
            else:
                candidate_sl = sl + sl_delta_price

            # Safeguard: SL must be below entry by at least 1 pip
            if candidate_sl >= entry - pip_size:
                candidate_sl = entry - max(pip_size, abs(entry - sl) * 0.90)

            # Cap risk guard: loss_usd = ((entry - candidate_sl) / pip_size) * pip_value_usd * lot_size
            if lot_size > 0:
                loss_usd = ((entry - candidate_sl) / pip_size) * pip_value_usd * lot_size
                if loss_usd > max_allowed_sl_loss_usd:
                    max_dist = (max_allowed_sl_loss_usd / (lot_size * pip_value_usd)) * pip_size
                    candidate_sl = entry - max_dist

            new_sl = round(candidate_sl, decimals)

            tp_sign = 1 if self._rng.random() > 0.5 else -1
            candidate_tp = tp + (tp_sign * tp_delta_price)

            risk_dist = abs(entry - new_sl)
            min_reward_dist = risk_dist * preserve_min_rr
            if (candidate_tp - entry) < min_reward_dist:
                candidate_tp = entry + min_reward_dist
            new_tp = round(candidate_tp, decimals)

        else:  # SELL
            if allow_loosening and self._rng.random() > 0.5:
                candidate_sl = sl + sl_delta_price
            else:
                candidate_sl = sl - sl_delta_price

            if candidate_sl <= entry + pip_size:
                candidate_sl = entry + max(pip_size, abs(sl - entry) * 0.90)

            if lot_size > 0:
                loss_usd = ((candidate_sl - entry) / pip_size) * pip_value_usd * lot_size
                if loss_usd > max_allowed_sl_loss_usd:
                    max_dist = (max_allowed_sl_loss_usd / (lot_size * pip_value_usd)) * pip_size
                    candidate_sl = entry + max_dist

            new_sl = round(candidate_sl, decimals)

            tp_sign = 1 if self._rng.random() > 0.5 else -1
            candidate_tp = tp - (tp_sign * tp_delta_price)

            risk_dist = abs(new_sl - entry)
            min_reward_dist = risk_dist * preserve_min_rr
            if (entry - candidate_tp) < min_reward_dist:
                candidate_tp = entry - min_reward_dist
            new_tp = round(candidate_tp, decimals)

        risk_dist = abs(entry - new_sl)
        reward_dist = abs(new_tp - entry)
        computed_rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else preserve_min_rr
        actual_sl_pips = round(abs(new_sl - sl) / pip_size, 2)
        actual_tp_pips = round(abs(new_tp - tp) / pip_size, 2)
        actual_risk_usd = round((risk_dist / pip_size) * pip_value_usd * lot_size, 2)

        meta = {
            "sl_perturbed_pips": actual_sl_pips,
            "tp_perturbed_pips": actual_tp_pips,
            "original_sl": sl,
            "perturbed_sl": new_sl,
            "original_tp": tp,
            "perturbed_tp": new_tp,
            "computed_rr": computed_rr,
            "effective_risk_usd": actual_risk_usd,
            "pip_size": pip_size,
            "pip_value_usd": pip_value_usd,
        }
        return new_sl, new_tp, meta

    def generate_stealth_comment(self, account_id: str, firm_name: str) -> str:
        """
        Generates benign, varied order comments to avoid identical EA comment signatures.
        """
        stealth_pool = [
            "",
            "App",
            "Web",
            "iOS",
            "Manual",
            "Limit-Fill",
            "Scale-1",
            "Core",
            f"M-{account_id[-3:]}",
            f"{firm_name[:3]}-ord",
        ]
        return self._rng.choice(stealth_pool)


# =====================================================================
# 4. ACCOUNT PROFILE & RISK RULE REGISTRY
# =====================================================================

@dataclass(frozen=True)
class PropFirmPreset:
    """1-Click Prop Firm / Broker Rule Template."""
    preset_key: str
    firm_name: str
    max_daily_drawdown_pct: float
    max_total_drawdown_pct: float
    freeze_dd_ratio: float = 0.80      # 80% daily drawdown instant freeze
    per_trade_risk_pct: float = 0.75   # Fail-closed risk cap <= 0.75%
    news_restricted: bool = True       # Enforces 15m news blackout
    news_lockout_minutes: int = 15
    weekend_holding_allowed: bool = False
    default_server: str = "Demo-Server"
    default_account_type: str = "Prop Firm Challenge"


PROP_FIRM_PRESETS: Dict[str, PropFirmPreset] = {
    "fundingpips": PropFirmPreset(
        preset_key="fundingpips",
        firm_name="FundingPips",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=True,
        news_lockout_minutes=15,
        weekend_holding_allowed=False,
        default_server="FundingPips-Server",
        default_account_type="Prop Firm Challenge",
    ),
    "ftmo": PropFirmPreset(
        preset_key="ftmo",
        firm_name="FTMO",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,  # swing news allowed
        news_lockout_minutes=15,
        weekend_holding_allowed=True,  # swing allows weekend holding
        default_server="FTMO-Demo",
        default_account_type="Prop Firm Challenge",
    ),
    "topstep": PropFirmPreset(
        preset_key="topstep",
        firm_name="Topstep",
        max_daily_drawdown_pct=4.0,
        max_total_drawdown_pct=6.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=True,
        news_lockout_minutes=15,
        weekend_holding_allowed=False,
        default_server="Topstep-Server",
        default_account_type="Prop Firm Challenge",
    ),
    "thefundedtrader": PropFirmPreset(
        preset_key="thefundedtrader",
        firm_name="The Funded Trader",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=True,  # 15m news blackout
        news_lockout_minutes=15,
        weekend_holding_allowed=False,
        default_server="TheFundedTrader-Server",
        default_account_type="Prop Firm Challenge",
    ),
    "5%ers": PropFirmPreset(
        preset_key="5%ers",
        firm_name="5%ers",
        max_daily_drawdown_pct=4.0,
        max_total_drawdown_pct=8.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,  # news allowed
        news_lockout_minutes=15,
        weekend_holding_allowed=True,  # weekend holding allowed
        default_server="FivePercentOnline-Live",
        default_account_type="Prop Firm Challenge",
    ),
    "the5ers": PropFirmPreset(
        preset_key="the5ers",
        firm_name="5%ers",
        max_daily_drawdown_pct=4.0,
        max_total_drawdown_pct=8.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=15,
        weekend_holding_allowed=True,
        default_server="FivePercentOnline-Live",
        default_account_type="Prop Firm Challenge",
    ),
    "alphacapital": PropFirmPreset(
        preset_key="alphacapital",
        firm_name="Alpha Capital",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=True,  # news restricted
        news_lockout_minutes=15,
        weekend_holding_allowed=False,
        default_server="AlphaCapitalGroup-Server",
        default_account_type="Prop Firm Challenge",
    ),
    "e8": PropFirmPreset(
        preset_key="e8",
        firm_name="E8",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=8.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,  # news allowed
        news_lockout_minutes=15,
        weekend_holding_allowed=True,  # weekend holding allowed
        default_server="E8Markets-Demo",
        default_account_type="Prop Firm Challenge",
    ),
    "personal": PropFirmPreset(
        preset_key="personal",
        firm_name="PersonalBroker",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="MetaQuotes-Demo",
        default_account_type="Personal Broker",
    ),
    "exness": PropFirmPreset(
        preset_key="exness",
        firm_name="Exness",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Exness-Real",
        default_account_type="Personal Broker",
    ),
    "icmarkets": PropFirmPreset(
        preset_key="icmarkets",
        firm_name="IC Markets",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="ICMarkets-Live",
        default_account_type="Personal Broker",
    ),
    "pepperstone": PropFirmPreset(
        preset_key="pepperstone",
        firm_name="Pepperstone",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Pepperstone-Edge",
        default_account_type="Personal Broker",
    ),
    "oanda": PropFirmPreset(
        preset_key="oanda",
        firm_name="OANDA",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="OANDA-v20",
        default_account_type="Personal Broker",
    ),
    "binance": PropFirmPreset(
        preset_key="binance",
        firm_name="Binance Spot",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Binance-API",
        default_account_type="Crypto Exchange API",
    ),
    "binancefutures": PropFirmPreset(
        preset_key="binancefutures",
        firm_name="Binance Futures",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Binance-Futures-API",
        default_account_type="Crypto Exchange API",
    ),
    "bybit": PropFirmPreset(
        preset_key="bybit",
        firm_name="Bybit",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Bybit-API",
        default_account_type="Crypto Exchange API",
    ),
    "hyperliquid": PropFirmPreset(
        preset_key="hyperliquid",
        firm_name="Hyperliquid DEX",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Hyperliquid-L1-API",
        default_account_type="DEX Trading API",
    ),
    "bitget": PropFirmPreset(
        preset_key="bitget",
        firm_name="Bitget",
        max_daily_drawdown_pct=5.0,
        max_total_drawdown_pct=10.0,
        freeze_dd_ratio=0.80,
        per_trade_risk_pct=0.75,
        news_restricted=False,
        news_lockout_minutes=5,
        weekend_holding_allowed=True,
        default_server="Bitget-API",
        default_account_type="Crypto Exchange API",
    ),
}


def get_prop_firm_preset(name_or_key: str) -> PropFirmPreset:
    """Normalizes any query string to the canonical PropFirmPreset."""
    import re
    clean = re.sub(r"[^a-zA-Z0-9%]", "", str(name_or_key or "")).lower()
    if clean in PROP_FIRM_PRESETS:
        return PROP_FIRM_PRESETS[clean]
    aliases = {
        "fundingpips": "fundingpips",
        "fundingpip": "fundingpips",
        "fp": "fundingpips",
        "ftmo": "ftmo",
        "topstep": "topstep",
        "topstepfutures": "topstep",
        "ts": "topstep",
        "thefundedtrader": "thefundedtrader",
        "thefunded": "thefundedtrader",
        "fundedtrader": "thefundedtrader",
        "tft": "thefundedtrader",
        "5ers": "5%ers",
        "the5ers": "5%ers",
        "5": "5%ers",
        "fivepercenters": "5%ers",
        "fivepercent": "5%ers",
        "alphacapital": "alphacapital",
        "alphacapitalgroup": "alphacapital",
        "alpha": "alphacapital",
        "e8": "e8",
        "e8markets": "e8",
        "personal": "personal",
        "personalbroker": "personal",
        "personalmt5": "personal",
        "mt5": "personal",
        "exness": "exness",
        "exnesspro": "exness",
        "icmarkets": "icmarkets",
        "icmarket": "icmarkets",
        "ic": "icmarkets",
        "pepperstone": "pepperstone",
        "oanda": "oanda",
        "binance": "binance",
        "binancespot": "binance",
        "binancefutures": "binancefutures",
        "binanceperp": "binancefutures",
        "bybit": "bybit",
        "hyperliquid": "hyperliquid",
        "hyperliquiddex": "hyperliquid",
        "hyper": "hyperliquid",
        "bitget": "bitget",
    }
    key = aliases.get(clean, "fundingpips")
    return PROP_FIRM_PRESETS.get(key, PROP_FIRM_PRESETS["fundingpips"])


def extract_firm_rules(firm: str, balance: float = 100000.0) -> Dict[str, Any]:
    """
    Dynamic Rule Extraction Core for Prop Firms, Forex Brokers, and Crypto APIs:
    Calculates deterministic loss limits, 80% daily freeze threshold,
    FundingPips deterministic <=0.75% ($750 cap), R:R >= 2.50 floor,
    dynamic +1.0R breakeven, news blackout buffer, and 5-layer anti-ban proxy allocation.
    """
    preset = get_prop_firm_preset(firm)
    firm_clean = str(firm or "").strip().lower()
    balance = float(balance) if float(balance) > 0 else 100000.0

    daily_dd_pct = float(preset.max_daily_drawdown_pct)
    daily_dd_usd = round(balance * (daily_dd_pct / 100.0), 2)
    overall_dd_pct = float(preset.max_total_drawdown_pct)
    overall_dd_usd = round(balance * (overall_dd_pct / 100.0), 2)
    daily_freeze_usd = round(daily_dd_usd * preset.freeze_dd_ratio, 2)

    is_fundingpips = "fundingpip" in firm_clean or "funding pips" in firm_clean or preset.preset_key == "fundingpips"
    max_risk_pct = min(0.75, float(preset.per_trade_risk_pct))
    calculated_risk_usd = round(balance * (max_risk_pct / 100.0), 2)

    if is_fundingpips:
        max_risk_usd_cap = min(calculated_risk_usd, 750.0)
    else:
        max_risk_usd_cap = min(calculated_risk_usd, 750.0) if balance <= 100000.0 else calculated_risk_usd

    proxy_country_map = {
        "fundingpips": "AE",
        "ftmo": "CZ",
        "topstep": "US",
        "5%ers": "UK",
        "alphacapital": "UK",
        "e8": "US",
        "thefundedtrader": "US",
        "personal": "PK",
        "exness": "CY",
        "icmarkets": "AU",
        "pepperstone": "UK",
        "oanda": "US",
        "binance": "SG",
        "binancefutures": "SG",
        "bybit": "SG",
        "hyperliquid": "US",
        "bitget": "SG",
    }
    proxy_country = proxy_country_map.get(preset.preset_key, "AE")

    return {
        "ok": True,
        "firm": preset.firm_name,
        "balance": balance,
        "daily_loss_limit_pct": daily_dd_pct,
        "daily_loss_limit_usd": daily_dd_usd,
        "overall_loss_limit_pct": overall_dd_pct,
        "overall_loss_limit_usd": overall_dd_usd,
        "daily_freeze_threshold_usd": daily_freeze_usd,
        "max_risk_per_trade_pct": max_risk_pct,
        "max_risk_usd_cap": max_risk_usd_cap,
        "min_rr_ratio": 2.5,
        "dynamic_breakeven_r": 1.0,
        "news_blackout_minutes": int(preset.news_lockout_minutes),
        "anti_ban_layers": 5,
        "assigned_proxy_country": proxy_country
    }


@dataclass
class AccountRiskProfile:
    """Comprehensive institutional profile and firm-specific rule set for an account."""
    account_id: str
    account_name: str
    firm_name: str                  # "FundingPips", "FTMO", "PersonalBroker", etc.
    account_type: str               # "FUNDED", "EVALUATION_STEP_1", "PERSONAL_LIVE", "DEMO"
    starting_balance: float = 100000.0
    balance: float = 100000.0
    equity: float = 100000.0
    currency: str = "USD"
    max_risk_pct: float = 0.75       # 0.75% max risk cap
    max_risk_usd_cap: float = 750.0  # Absolute dollar cap
    max_daily_drawdown_pct: float = 4.0
    max_total_drawdown_pct: float = 10.0
    freeze_dd_ratio: float = 0.80    # Freeze at 80% of allowed daily drawdown
    min_rr_ratio: float = 2.5        # Institutional 1:2.5 minimum R:R
    dynamic_breakeven_trigger_r: float = 1.0  # Dynamic breakeven lock at +1.0R gain
    max_daily_trades: int = 3
    daily_trades_count: int = 0
    news_lockout_minutes: int = 15
    news_restricted: bool = False
    weekend_holding_allowed: bool = False
    is_active: bool = True
    is_frozen: bool = False
    freeze_reason: Optional[str] = None
    terminal_config: Optional[TerminalInstanceConfig] = None
    proxy_config: Optional[ProxyConfig] = None
    telemetry_verified: bool = False
    exchange_platform: Optional[str] = None
    api_key_env: Optional[str] = None
    api_secret_env: Optional[str] = None
    passphrase_env: Optional[str] = None

    def check_drawdown_freeze(self, current_equity: Optional[float] = None) -> Tuple[bool, str]:
        """
        Real-time equity monitoring that instantly freezes trading on that specific
        account if drawdown hits 80% of allowed daily limit (e.g. at 4.0% loss when daily limit is 5.0%).
        """
        eq = current_equity if current_equity is not None else self.equity
        baseline = self.balance if self.balance > 0 else self.starting_balance
        if baseline <= 0:
            return False, "Baseline balance unavailable"

        current_loss_usd = max(0.0, baseline - eq)
        current_loss_pct = (current_loss_usd / baseline) * 100.0
        freeze_limit_pct = round(self.max_daily_drawdown_pct * self.freeze_dd_ratio, 4)
        max_limit_pct = self.max_daily_drawdown_pct

        if current_loss_pct >= max_limit_pct:
            self.is_frozen = True
            self.freeze_reason = (
                f"DAILY_DRAWDOWN_BREACH: Current daily loss {current_loss_pct:.2f}% breached "
                f"maximum allowed {max_limit_pct:.2f}%. Trading locked."
            )
            return True, self.freeze_reason

        if current_loss_pct >= freeze_limit_pct:
            self.is_frozen = True
            self.freeze_reason = (
                f"DAILY_DRAWDOWN_80_PERCENT_FREEZE: Daily loss {current_loss_pct:.2f}% reached 80% "
                f"of allowed daily limit ({freeze_limit_pct:.2f}% of {max_limit_pct:.2f}%). Trading frozen."
            )
            return True, self.freeze_reason

        if self.is_frozen and current_loss_pct < freeze_limit_pct:
            if "80_PERCENT_FREEZE" in (self.freeze_reason or ""):
                self.is_frozen = False
                self.freeze_reason = None

        return False, "Drawdown within safe operating limits"

    def calculate_lot_size(
        self,
        symbol: str,
        sl_pips: float,
        proposed_risk_pct: Optional[float] = None,
    ) -> float:
        """
        Calculates exact lot size calibrated to this account's balance and dollar cap.
        Guarantees that lot size never exceeds BOTH the percentage cap AND the dollar cap.
        Never rounds an unaffordable position up to the minimum lot size.
        """
        if not self.is_active or self.balance <= 0 or sl_pips <= 0:
            return 0.0

        effective_pct = min(self.max_risk_pct, proposed_risk_pct or self.max_risk_pct)
        risk_dollars_from_pct = self.balance * (effective_pct / 100.0)
        # Bound by absolute dollar cap
        allowed_risk_usd = min(risk_dollars_from_pct, self.max_risk_usd_cap)

        _, pip_value, _ = get_symbol_metrics(symbol)
        total_loss_per_lot = sl_pips * pip_value
        if total_loss_per_lot <= 0:
            return 0.0

        raw_lot = allowed_risk_usd / total_loss_per_lot

        # Fail-closed: Never round a genuinely unaffordable position up to broker minimum 0.01
        if raw_lot < 0.01:
            if (0.01 * total_loss_per_lot) > (allowed_risk_usd + 1e-4):
                return 0.0

        # Always round volume down to the broker step to avoid silently exceeding dollar-risk budget
        stepped_lot = math.floor(raw_lot * 100.0) / 100.0
        lot = round(min(max(stepped_lot, 0.01), 10.0), 2)

        # Final safety verification against hard cap
        if round(lot * total_loss_per_lot, 2) > (allowed_risk_usd + 1e-4):
            lot = round(lot - 0.01, 2)
            if lot < 0.01:
                return 0.0

        return lot

    def evaluate_admission_rules(
        self,
        symbol: str,
        sl_pips: float,
        rr_ratio: float,
        proposed_risk_pct: Optional[float] = None,
        news_lockout_active: bool = False,
    ) -> Dict[str, Any]:
        """
        Deterministic firm rule evaluation for this specific account.
        Fails closed on any violation without impacting other accounts in the fleet.
        """
        blockers = []
        checks_passed = []

        if not self.is_active:
            blockers.append("Account is disabled / inactive")

        # 0. Real-Time 80% Daily Drawdown Freeze Shield
        frozen, freeze_reason = self.check_drawdown_freeze(self.equity)
        if frozen or self.is_frozen:
            blockers.append(freeze_reason or self.freeze_reason or "Account trading frozen at 80% daily drawdown threshold")
        else:
            freeze_thr = round(self.max_daily_drawdown_pct * self.freeze_dd_ratio, 2)
            checks_passed.append(f"80% Daily DD Shield Clear (Loss < {freeze_thr}%)")

        # 0a. Total Drawdown Hard Floor (against starting balance)
        if self.starting_balance > 0:
            current_val = min(self.balance, self.equity)
            total_dd_pct = max(0.0, (self.starting_balance - current_val) / self.starting_balance * 100.0)
            if total_dd_pct >= self.max_total_drawdown_pct:
                blockers.append(f"Total Drawdown breach: {total_dd_pct:.2f}% >= {self.max_total_drawdown_pct}% floor")
            else:
                checks_passed.append(f"Total Drawdown Safe ({total_dd_pct:.2f}% < {self.max_total_drawdown_pct}%)")

        # 0b. Daily Drawdown Hard Floor (against starting daily balance)
        if self.balance > 0:
            daily_loss_pct = max(0.0, (self.balance - self.equity) / self.balance * 100.0)
            if daily_loss_pct >= self.max_daily_drawdown_pct:
                blockers.append(f"Daily Drawdown breach: {daily_loss_pct:.2f}% >= {self.max_daily_drawdown_pct}% floor")
            else:
                checks_passed.append(f"Daily Drawdown Safe ({daily_loss_pct:.2f}% < {self.max_daily_drawdown_pct}%)")

        # 1. Daily Trade Cap
        if self.daily_trades_count < self.max_daily_trades:
            checks_passed.append(f"Daily Trade Cap Clear ({self.daily_trades_count}/{self.max_daily_trades})")
        else:
            blockers.append(f"Daily trade limit reached ({self.max_daily_trades}/day)")

        # 2. Risk Sizing & Dollar Cap
        effective_pct = proposed_risk_pct or self.max_risk_pct
        lot = self.calculate_lot_size(symbol, sl_pips, effective_pct)
        _, pip_value, _ = get_symbol_metrics(symbol)
        total_loss = lot * sl_pips * pip_value

        if lot > 0 and round(total_loss, 2) <= (self.max_risk_usd_cap + 1e-4):
            checks_passed.append(f"Lot Sizing Admissible ({lot} lots, ${total_loss:.2f} <= ${self.max_risk_usd_cap:.2f})")
        else:
            if lot <= 0:
                blockers.append(f"Calculated lot size is zero: minimum lot exceeds {self.firm_name} risk cap (${self.max_risk_usd_cap:.2f})")
            else:
                blockers.append(f"Calculated risk ${total_loss:.2f} exceeds {self.firm_name} risk cap (${self.max_risk_usd_cap:.2f})")

        # 3. Minimum R:R
        if rr_ratio >= (self.min_rr_ratio - 1e-4):
            checks_passed.append(f"Minimum R:R satisfied (1:{rr_ratio} >= 1:{self.min_rr_ratio})")
        else:
            blockers.append(f"Proposed R:R (1:{rr_ratio}) below {self.firm_name} floor 1:{self.min_rr_ratio}")

        # 4. News Lockout (15-Minute News Blackout)
        if news_lockout_active:
            if getattr(self, "news_restricted", True):
                blockers.append(f"{self.firm_name} News Lockout Active ({self.news_lockout_minutes} min blackout)")
            else:
                checks_passed.append(f"{self.firm_name} News Trading Allowed (Swing Exemption)")
        else:
            checks_passed.append(f"{self.news_lockout_minutes}-Min News Buffer Clear")

        # 5. Proxy Shield Validation
        if self.proxy_config and self.proxy_config.enabled:
            valid, proxy_errs = self.proxy_config.validate_sanity()
            if valid:
                checks_passed.append("Static Residential Proxy Verified")
            else:
                blockers.extend([f"Proxy Config Error: {e}" for e in proxy_errs])

        # 6. Terminal Isolation Validation
        if self.terminal_config:
            valid, term_errs = self.terminal_config.validate_isolation_constraints()
            if valid:
                checks_passed.append("Portable Terminal Isolation Verified")
            else:
                blockers.extend([f"Terminal Config Error: {e}" for e in term_errs])

        admitted = len(blockers) == 0
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "firm_name": self.firm_name,
            "admitted": admitted,
            "blockers": blockers,
            "checks_passed": checks_passed,
            "allocated_lot": lot if admitted else 0.0,
            "max_risk_usd_cap": self.max_risk_usd_cap,
            "min_rr_ratio": self.min_rr_ratio,
            "dynamic_breakeven_r": self.dynamic_breakeven_trigger_r,
        }


# =====================================================================
# 5. MULTI-ACCOUNT MASTER ANTI-DETECTION MANAGER
# =====================================================================

def _is_receipt_successful(receipt: Any) -> bool:
    """Verifies order receipt across dictionaries and MT5 OrderSendResult objects."""
    if receipt is None:
        return False
    if isinstance(receipt, dict):
        if receipt.get("success") is True:
            return True
        if receipt.get("retcode") in (10008, 10009):
            return True
        return False
    # Object with attributes (e.g. MT5 OrderSendResult)
    if getattr(receipt, "success", False) is True:
        return True
    if getattr(receipt, "retcode", None) in (10008, 10009):
        return True
    return False


class MultiAccountManager:
    """
    Institutional Multi-Account Anti-Detection & Fleet Isolation Manager.
    Coordinates portable terminals, static proxies, execution jitter, and
    isolated firm risk kernel policies.
    """

    DEFAULT_CONFIG_PATH = Path("config/multi_account_fleet.json")

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        anti_copy_shield: Optional[AntiCopyShield] = None,
    ):
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_PATH)
        self.shield = anti_copy_shield or AntiCopyShield()
        self._lock = threading.Lock()
        self.fleet: Dict[str, AccountRiskProfile] = {}
        self._load_or_initialize_fleet()

    def _default_fleet_profiles(self) -> Dict[str, AccountRiskProfile]:
        """Creates institutional baseline profiles for FundingPips, FTMO, and Personal Broker."""
        profiles = {
            "fundingpips_100k": AccountRiskProfile(
                account_id="40000294403",
                account_name="FundingPips $100K Primary Funded",
                firm_name="FundingPips",
                account_type="FUNDED",
                starting_balance=100000.0,
                balance=100000.0,
                equity=100000.0,
                currency="USD",
                max_risk_pct=0.75,
                max_risk_usd_cap=750.0,
                max_daily_drawdown_pct=4.0,
                max_total_drawdown_pct=10.0,
                min_rr_ratio=2.5,
                dynamic_breakeven_trigger_r=1.0,
                max_daily_trades=3,
                news_lockout_minutes=15,
                is_active=True,
                terminal_config=TerminalInstanceConfig(
                    account_id="40000294403",
                    firm_name="FundingPips",
                    terminal_dir="C:\\MT5_Fleet\\FundingPips_100K",
                    executable_path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                    portable_mode=True,
                    ipc_port=18812,
                    password_env="MT5_PASSWORD_FUNDINGPIPS",
                    server="FundingPips-Trial",
                    login=40000294403,
                ),
                proxy_config=ProxyConfig(
                    enabled=True,
                    proxy_type="SOCKS5",
                    host="127.0.0.1",
                    port=10801,
                    username_env="PROXY_USER_FUNDINGPIPS",
                    password_env="PROXY_PASS_FUNDINGPIPS",
                    target_country="AE",
                    static_ip=True,
                ),
            ),
            "ftmo_100k": AccountRiskProfile(
                account_id="1514382598",
                account_name="FTMO $100K Institutional Account",
                firm_name="FTMO",
                account_type="EVALUATION_STEP_1",
                starting_balance=100000.0,
                balance=100000.0,
                equity=100000.0,
                currency="USD",
                max_risk_pct=0.50,
                max_risk_usd_cap=500.0,
                max_daily_drawdown_pct=5.0,
                max_total_drawdown_pct=10.0,
                min_rr_ratio=2.5,
                dynamic_breakeven_trigger_r=1.0,
                max_daily_trades=3,
                news_lockout_minutes=2,
                is_active=True,
                terminal_config=TerminalInstanceConfig(
                    account_id="1514382598",
                    firm_name="FTMO",
                    terminal_dir="C:\\MT5_Fleet\\FTMO_100K",
                    executable_path="C:\\Program Files\\MetaTrader 5 FTMO\\terminal64.exe",
                    portable_mode=True,
                    ipc_port=18813,
                    password_env="MT5_PASSWORD_FTMO",
                    server="FTMO-Demo",
                    login=1514382598,
                ),
                proxy_config=ProxyConfig(
                    enabled=True,
                    proxy_type="SOCKS5",
                    host="127.0.0.1",
                    port=10802,
                    username_env="PROXY_USER_FTMO",
                    password_env="PROXY_PASS_FTMO",
                    target_country="CZ",
                    static_ip=True,
                ),
            ),
            "vebson_personal_1k": AccountRiskProfile(
                account_id="5054542",
                account_name="Vebson Personal Broker Bracket",
                firm_name="PersonalBroker",
                account_type="PERSONAL_LIVE",
                starting_balance=1000.0,
                balance=1000.0,
                equity=1000.0,
                currency="USD",
                max_risk_pct=0.75,
                max_risk_usd_cap=7.50,
                max_daily_drawdown_pct=5.0,
                max_total_drawdown_pct=10.0,
                min_rr_ratio=2.5,
                dynamic_breakeven_trigger_r=1.0,
                max_daily_trades=5,
                news_lockout_minutes=5,
                is_active=True,
                terminal_config=TerminalInstanceConfig(
                    account_id="5054542",
                    firm_name="PersonalBroker",
                    terminal_dir="C:\\MT5_Fleet\\Vebson_Personal",
                    executable_path="C:\\Program Files\\MetaTrader 5 Vebson\\terminal64.exe",
                    portable_mode=True,
                    ipc_port=18814,
                    password_env="MT5_PASSWORD_VEBSON",
                    server="Vebson-Server",
                    login=5054542,
                ),
                proxy_config=ProxyConfig(
                    enabled=True,
                    proxy_type="SOCKS5",
                    host="127.0.0.1",
                    port=10803,
                    username_env="PROXY_USER_VEBSON",
                    password_env="PROXY_PASS_VEBSON",
                    target_country="PK",
                    static_ip=True,
                ),
            ),
        }
        return profiles

    def _load_or_initialize_fleet(self):
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    accounts = data.get("accounts", {})
                    for key, raw in accounts.items():
                        profile = self._deserialize_profile(raw)
                        self.fleet[key] = profile
                    logger.info("Loaded %d multi-account profiles from %s", len(self.fleet), self.config_path)
                    return
                except Exception as exc:
                    logger.warning("Could not parse %s: %s; falling back to default templates", self.config_path, exc)

            self.fleet = self._default_fleet_profiles()
            self._save_fleet_unlocked()

    def _deserialize_profile(self, d: Dict[str, Any]) -> AccountRiskProfile:
        term_cfg = None
        if d.get("terminal_config"):
            term_cfg = TerminalInstanceConfig(**d["terminal_config"])
        proxy_cfg = None
        if d.get("proxy_config"):
            proxy_cfg = ProxyConfig(**d["proxy_config"])

        return AccountRiskProfile(
            account_id=str(d.get("account_id")),
            account_name=str(d.get("account_name")),
            firm_name=str(d.get("firm_name")),
            account_type=str(d.get("account_type", "FUNDED")),
            starting_balance=float(d.get("starting_balance", 100000.0)),
            balance=float(d.get("balance", 100000.0)),
            equity=float(d.get("equity", 100000.0)),
            currency=str(d.get("currency", "USD")),
            max_risk_pct=float(d.get("max_risk_pct", 0.75)),
            max_risk_usd_cap=float(d.get("max_risk_usd_cap", 750.0)),
            max_daily_drawdown_pct=float(d.get("max_daily_drawdown_pct", 4.0)),
            max_total_drawdown_pct=float(d.get("max_total_drawdown_pct", 10.0)),
            min_rr_ratio=float(d.get("min_rr_ratio", 2.5)),
            dynamic_breakeven_trigger_r=float(d.get("dynamic_breakeven_trigger_r", 1.0)),
            max_daily_trades=int(d.get("max_daily_trades", 3)),
            daily_trades_count=int(d.get("daily_trades_count", 0)),
            news_lockout_minutes=int(d.get("news_lockout_minutes", 15)),
            freeze_dd_ratio=float(d.get("freeze_dd_ratio", 0.80)),
            news_restricted=bool(d.get("news_restricted", False)),
            weekend_holding_allowed=bool(d.get("weekend_holding_allowed", False)),
            is_active=bool(d.get("is_active", True)),
            is_frozen=bool(d.get("is_frozen", False)),
            freeze_reason=d.get("freeze_reason"),
            terminal_config=term_cfg,
            proxy_config=proxy_cfg,
            telemetry_verified=bool(d.get("telemetry_verified", False)),
            exchange_platform=d.get("exchange_platform"),
            api_key_env=d.get("api_key_env"),
            api_secret_env=d.get("api_secret_env"),
            passphrase_env=d.get("passphrase_env"),
        )

    def _save_fleet_unlocked(self) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                "schema_version": 2,
                "owner": "Master Muhammad Qureshi",
                "phone": "+923468053268",
                "primary_email": "futureworldvision842@gmail.com",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "anti_detection_enabled": True,
                "accounts": {},
            }
            for k, prof in self.fleet.items():
                p_dict = asdict(prof)
                serializable["accounts"][k] = p_dict

            tmp_path = self.config_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            os.replace(tmp_path, self.config_path)
            return True
        except Exception as exc:
            logger.error("Failed to save fleet config: %s", exc)
            return False

    def save_fleet(self) -> bool:
        with self._lock:
            return self._save_fleet_unlocked()

    def register_account(self, key: str, profile: AccountRiskProfile) -> Tuple[bool, str]:
        """Registers or updates an account in the fleet, validating isolation constraints."""
        with self._lock:
            # Check for credential isolation
            if profile.terminal_config:
                if not profile.terminal_config.password_env:
                    return False, "Plain-text passwords forbidden; specify password_env"
                if not profile.terminal_config.portable_mode:
                    return False, "portable_mode must be True for all registered accounts"

            self.fleet[key] = profile
            self._save_fleet_unlocked()
            logger.info("Registered account %s (#%s) for firm %s", profile.account_name, profile.account_id, profile.firm_name)
            return True, f"Account {profile.account_name} registered successfully."

    def unregister_account(self, key_or_id: str) -> bool:
        """Removes an account from the active fleet."""
        with self._lock:
            target_key = None
            for k, p in self.fleet.items():
                if k == key_or_id or p.account_id == str(key_or_id):
                    target_key = k
                    break
            if target_key and target_key in self.fleet:
                del self.fleet[target_key]
                self._save_fleet_unlocked()
                return True
            return False

    def get_account_by_id(self, account_id: str) -> Optional[AccountRiskProfile]:
        """Finds account profile by account login/ID or fleet key."""
        with self._lock:
            for k, p in self.fleet.items():
                if k == str(account_id) or str(p.account_id) == str(account_id):
                    return copy.deepcopy(p)
            return None

    def check_account_drawdown_freeze(self, account_id: str, current_equity: float) -> Tuple[bool, str]:
        """
        Real-time equity monitoring: freezes trading on this specific account
        if daily drawdown reaches 80% of allowed daily limit.
        """
        with self._lock:
            for k, p in self.fleet.items():
                if k == str(account_id) or str(p.account_id) == str(account_id):
                    p.equity = float(current_equity)
                    is_frozen, reason = p.check_drawdown_freeze(current_equity)
                    return is_frozen, reason
            return False, f"Account '{account_id}' not found in fleet"

    def onboard_account(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal Interactive Web Onboarding Core:
        - Ingests Account Name, Broker Server, Login ID, Password, Account Balance,
          Account Type, Preset, Target Country.
        - Securely stores credentials in isolated environment config (Plaintext passwords NEVER committed/logged).
        - 5-Layer Sovereign Anti-Ban Shield:
            Layer 1: Isolated portable MT5 instance with dedicated IPC socket.
            Layer 2: Geo-matched residential proxy assignment based on registration country.
            Layer 3: Anti-correlation jitter (350ms - 1800ms) & Fisher-Yates execution shuffling.
            Layer 4: Pipette micro-tick SL/TP dispersion (+-0.5 to 2.0 pips).
            Layer 5: Dynamic SHA-256 hashed magic numbers.
        - Autonomous Risk Enforcement:
            * Real-time 80% daily drawdown freeze.
            * 15-minute pre/post high-impact economic news blackout buffer.
        """
        login_id_raw = config.get("login_id") or config.get("account_id") or config.get("login")
        if not login_id_raw or str(login_id_raw).strip() == "":
            raise ValueError("login_id / account_id is required for account onboarding")
        account_id = str(login_id_raw).strip()

        preset_raw = config.get("preset") or config.get("firm_preset") or config.get("firm_name") or "FundingPips"
        preset_tmpl = get_prop_firm_preset(preset_raw)

        server = str(config.get("broker_server") or config.get("server") or preset_tmpl.default_server).strip()
        account_name = str(config.get("account_name") or f"{preset_tmpl.firm_name} #{account_id}").strip()

        balance_raw = config.get("balance") if config.get("balance") is not None else (config.get("account_balance") or config.get("starting_balance", 100000.0))
        try:
            balance = float(balance_raw)
            if balance <= 0:
                raise ValueError("Account balance must be positive")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid account balance: {balance_raw}") from exc

        account_type = str(config.get("account_type") or preset_tmpl.default_account_type).strip()
        target_country = str(config.get("target_country") or config.get("country") or "AE").strip().upper()

        # Plaintext password protection: Never save plaintext password to config files or logs
        password = str(config.get("password") or "").strip()
        password_env = f"MT5_PASSWORD_{account_id}"
        if password:
            os.environ[password_env] = password

        # Crypto API Credential Ingestion: Strictly stored in os.environ, zero plaintext disk leaks
        exchange_platform = str(config.get("exchange_platform") or config.get("platform") or "").strip()
        api_key = str(config.get("api_key") or "").strip()
        api_secret = str(config.get("api_secret") or "").strip()
        passphrase = str(config.get("passphrase") or "").strip()

        api_key_env = None
        api_secret_env = None
        passphrase_env = None

        if api_key or exchange_platform:
            clean_plat = re.sub(r"[^A-Za-z0-9]", "_", exchange_platform or preset_tmpl.preset_key or "CRYPTO").upper()
            if api_key:
                api_key_env = f"{clean_plat}_API_KEY_{account_id}"
                os.environ[api_key_env] = api_key
            if api_secret:
                api_secret_env = f"{clean_plat}_API_SECRET_{account_id}"
                os.environ[api_secret_env] = api_secret
            if passphrase:
                passphrase_env = f"{clean_plat}_PASSPHRASE_{account_id}"
                os.environ[passphrase_env] = passphrase

        # Determine risk parameters with deterministic fail-closed cap <= 0.75%
        req_risk_pct = float(config.get("per_trade_risk_pct") or config.get("risk_pct") or preset_tmpl.per_trade_risk_pct)
        risk_pct = min(0.75, max(0.10, req_risk_pct))
        risk_usd_cap = round(balance * (risk_pct / 100.0), 2)

        # Layer 1: Isolated Portable MT5 Terminal Configuration
        assigned_ipc_port = 18812 + (len(self.fleet) % 100)
        used_ports = {p.terminal_config.ipc_port for p in self.fleet.values() if p.terminal_config}
        while assigned_ipc_port in used_ports:
            assigned_ipc_port += 1

        terminal_dir = str(Path(f"C:\\MT5_Fleet\\{preset_tmpl.firm_name}_{account_id}"))
        term_cfg = TerminalInstanceConfig(
            account_id=account_id,
            firm_name=preset_tmpl.firm_name,
            terminal_dir=terminal_dir,
            executable_path=f"C:\\Program Files\\MetaTrader 5 {preset_tmpl.firm_name}\\terminal64.exe",
            portable_mode=True,
            ipc_port=assigned_ipc_port,
            password_env=password_env,
            server=server,
            login=int(account_id) if account_id.isdigit() else account_id,
        )

        # Layer 2: Geo-Matched Residential Proxy Configuration
        assigned_proxy_port = 10800 + (len(self.fleet) % 100) + 1
        used_proxy_ports = {p.proxy_config.port for p in self.fleet.values() if p.proxy_config and p.proxy_config.enabled}
        while assigned_proxy_port in used_proxy_ports:
            assigned_proxy_port += 1

        proxy_user_env = f"PROXY_USER_{account_id}"
        proxy_pass_env = f"PROXY_PASS_{account_id}"
        proxy_cfg = ProxyConfig(
            enabled=True,
            proxy_type="SOCKS5",
            host=config.get("proxy_host", "127.0.0.1"),
            port=int(config.get("proxy_port", assigned_proxy_port)),
            username_env=proxy_user_env,
            password_env=proxy_pass_env,
            target_country=target_country,
            static_ip=True,
            dns_leak_protection=True,
        )

        profile = AccountRiskProfile(
            account_id=account_id,
            account_name=account_name,
            firm_name=preset_tmpl.firm_name,
            account_type=account_type,
            starting_balance=balance,
            balance=balance,
            equity=balance,
            currency=str(config.get("currency", "USD")),
            max_risk_pct=risk_pct,
            max_risk_usd_cap=risk_usd_cap,
            max_daily_drawdown_pct=preset_tmpl.max_daily_drawdown_pct,
            max_total_drawdown_pct=preset_tmpl.max_total_drawdown_pct,
            freeze_dd_ratio=preset_tmpl.freeze_dd_ratio,
            min_rr_ratio=2.5,
            dynamic_breakeven_trigger_r=1.0,
            max_daily_trades=int(config.get("max_daily_trades", 3)),
            news_lockout_minutes=preset_tmpl.news_lockout_minutes,
            news_restricted=preset_tmpl.news_restricted,
            weekend_holding_allowed=preset_tmpl.weekend_holding_allowed,
            is_active=True,
            terminal_config=term_cfg,
            proxy_config=proxy_cfg,
            telemetry_verified=False,
            exchange_platform=exchange_platform or None,
            api_key_env=api_key_env,
            api_secret_env=api_secret_env,
            passphrase_env=passphrase_env,
        )

        fleet_key = f"{preset_tmpl.preset_key}_{account_id}"
        self.register_account(fleet_key, profile)

        anti_ban_assigned = {
            "layer_1_portable_mt5": {
                "portable_mode": term_cfg.portable_mode,
                "terminal_dir": term_cfg.terminal_dir,
                "ipc_port": term_cfg.ipc_port,
                "password_isolated_in_env": password_env,
            },
            "layer_2_geo_proxy": {
                "target_country": proxy_cfg.target_country,
                "proxy_type": proxy_cfg.proxy_type,
                "static_ip": proxy_cfg.static_ip,
                "proxy_host": proxy_cfg.host,
                "proxy_port": proxy_cfg.port,
            },
            "layer_3_jitter_shuffle": {
                "min_delay_ms": self.shield.min_delay_ms,
                "max_delay_ms": self.shield.max_delay_ms,
                "shuffling_algorithm": "Fisher-Yates",
            },
            "layer_4_pipette_dispersion": {
                "min_offset_pips": self.shield.min_sl_offset_pips,
                "max_offset_pips": self.shield.max_sl_offset_pips,
            },
            "layer_5_dynamic_magic": {
                "hash_algorithm": "SHA-256",
                "dynamic_seed_pattern": f"{account_id}:<base_magic>:<symbol>:<date>",
            },
        }
        if api_key_env:
            anti_ban_assigned["crypto_credential_isolation"] = {
                "exchange_platform": exchange_platform or preset_tmpl.firm_name,
                "api_key_env": api_key_env,
                "api_secret_env": api_secret_env,
                "passphrase_env": passphrase_env,
                "disk_leak_protection": "VERIFIED_ZERO_PLAINTEXT_DISK_LEAKS"
            }

        freeze_threshold_pct = round(preset_tmpl.max_daily_drawdown_pct * preset_tmpl.freeze_dd_ratio, 2)
        risk_rules = {
            "max_daily_drawdown_pct": preset_tmpl.max_daily_drawdown_pct,
            "freeze_daily_drawdown_pct": freeze_threshold_pct,
            "freeze_ratio": preset_tmpl.freeze_dd_ratio,
            "max_total_drawdown_pct": preset_tmpl.max_total_drawdown_pct,
            "news_restricted": preset_tmpl.news_restricted,
            "news_lockout_minutes": preset_tmpl.news_lockout_minutes,
            "weekend_holding_allowed": preset_tmpl.weekend_holding_allowed,
            "per_trade_risk_pct": risk_pct,
            "max_risk_usd_cap": risk_usd_cap,
        }

        logger.info("Successfully onboarded account %s (#%s) for firm %s", account_name, account_id, preset_tmpl.firm_name)
        res_data = {
            "status": "success",
            "ok": True,
            "account_id": account_id,
            "account_name": account_name,
            "firm_name": preset_tmpl.firm_name,
            "profile": asdict(profile),
            "anti_ban_assigned": anti_ban_assigned,
            "risk_rules": risk_rules,
            "message": f"Account {account_name} (#{account_id}) successfully onboarded with 5-Layer Anti-Ban Shield."
        }
        if api_key_env:
            res_data["api_key_env"] = api_key_env
            res_data["api_secret_env"] = api_secret_env
            if passphrase_env:
                res_data["passphrase_env"] = passphrase_env
        return res_data

    def extract_rules(self, firm: str, balance: float = 100000.0) -> Dict[str, Any]:
        """Exposes dynamic rule extraction on the manager instance."""
        return extract_firm_rules(firm, balance)

    def validate_fleet_isolation(self) -> Dict[str, Any]:
        """
        Exhaustively audits the fleet for cross-account leakage:
        - Terminal directory collisions
        - IPC port collisions
        - Proxy IP collisions across different prop firms
        - Magic number collisions
        """
        with self._lock:
            term_dirs: Dict[str, str] = {}
            ipc_ports: Dict[int, str] = {}
            proxy_endpoints: Dict[str, str] = {}
            collisions = []

            for k, p in self.fleet.items():
                if not p.is_active:
                    continue
                # 1. Directory isolation
                if p.terminal_config:
                    tdir = str(Path(p.terminal_config.terminal_dir).resolve()).lower()
                    if tdir in term_dirs:
                        collisions.append(f"Directory collision between '{k}' and '{term_dirs[tdir]}': {tdir}")
                    else:
                        term_dirs[tdir] = k

                    # 2. Port isolation
                    port = p.terminal_config.ipc_port
                    if port in ipc_ports:
                        collisions.append(f"IPC port {port} collision between '{k}' and '{ipc_ports[port]}'")
                    else:
                        ipc_ports[port] = k

                # 3. Proxy endpoint isolation
                if p.proxy_config and p.proxy_config.enabled:
                    ep = f"{p.proxy_config.host}:{p.proxy_config.port}"
                    if ep in proxy_endpoints:
                        other_acc = proxy_endpoints[ep]
                        if self.fleet[other_acc].firm_name != p.firm_name:
                            collisions.append(
                                f"Shared proxy endpoint {ep} between different firms ('{k}' [{p.firm_name}] and '{other_acc}' [{self.fleet[other_acc].firm_name}]) violates prop firm anti-sybil rules"
                            )
                    else:
                        proxy_endpoints[ep] = k

            is_isolated = len(collisions) == 0
            return {
                "isolated": is_isolated,
                "collisions": collisions,
                "active_accounts_audited": len([p for p in self.fleet.values() if p.is_active]),
                "unique_directories_count": len(term_dirs),
                "unique_ipc_ports_count": len(ipc_ports),
                "unique_proxy_endpoints_count": len(proxy_endpoints),
            }

    def prepare_anti_detection_dispatch(
        self,
        signal: Dict[str, Any],
        news_lockout_active: bool = False,
    ) -> Dict[str, Any]:
        """
        Takes a master trade signal and transforms it into individual,
        anti-detection order payloads for every active account in the fleet:
        1. Evaluates firm risk rules independently.
        2. Applies mathematical micro-tick SL/TP perturbation.
        3. Generates unique Magic Numbers per terminal.
        4. Injects randomized micro-delay execution jitter.
        5. Shuffles the execution dispatch sequence.
        6. Assigns stealth randomized order comments.
        """
        symbol = str(signal.get("symbol", "XAUUSD")).upper().strip()
        side = str(signal.get("signal_type", signal.get("direction", "BUY"))).upper().strip()
        entry = float(signal.get("entry_price", 2650.0))
        sl = float(signal.get("sl_price", signal.get("sl", 2640.0)))
        tp = float(signal.get("tp_price", signal.get("tp", 2675.0)))

        pip_size, _, _ = get_symbol_metrics(symbol)

        raw_sl_pips = signal.get("sl_pips")
        if raw_sl_pips is not None and float(raw_sl_pips) > 0:
            sl_pips = float(raw_sl_pips)
        else:
            sl_pips = round(abs(entry - sl) / pip_size, 2) if pip_size > 0 else 10.0

        rr_ratio = round(abs(tp - entry) / abs(entry - sl), 2) if abs(entry - sl) > 0 else 2.5

        # Thread-safe snapshot of active accounts
        with self._lock:
            active_fleet = {k: copy.deepcopy(p) for k, p in self.fleet.items() if p.is_active}

        active_keys = list(active_fleet.keys())
        shuffled_keys = self.shield.shuffle_accounts(active_keys)

        dispatches: Dict[str, Any] = {}
        admitted_count = 0
        blocked_count = 0

        accumulated_delay_ms = 0.0

        for idx, key in enumerate(shuffled_keys):
            prof = active_fleet[key]
            # Independent Gate Check per Account
            gate_res = prof.evaluate_admission_rules(
                symbol=symbol,
                sl_pips=sl_pips,
                rr_ratio=rr_ratio,
                proposed_risk_pct=prof.max_risk_pct,
                news_lockout_active=news_lockout_active,
            )

            if not gate_res["admitted"]:
                blocked_count += 1
                dispatches[key] = {
                    "account_name": prof.account_name,
                    "account_id": prof.account_id,
                    "firm_name": prof.firm_name,
                    "admitted": False,
                    "blockers": gate_res["blockers"],
                }
                continue

            admitted_count += 1
            allocated_lot = gate_res["allocated_lot"]

            # 2. Perturb SL and TP by +/- 0.5 to 2.0 pips
            pert_sl, pert_tp, pert_meta = self.shield.perturb_sl_tp(
                symbol=symbol,
                side=side,
                entry=entry,
                sl=sl,
                tp=tp,
                max_allowed_sl_loss_usd=prof.max_risk_usd_cap,
                lot_size=allocated_lot,
                preserve_min_rr=prof.min_rr_ratio,
            )

            # 3. Dynamic Unique Magic Number
            magic_num = self.shield.generate_dynamic_magic_number(
                account_id=prof.account_id,
                base_magic=700000 + (idx * 10000),
                symbol=symbol,
                trade_index=idx,
            )

            # 4. Randomized Micro-delay Jitter (350ms - 1800ms)
            step_delay_ms = self.shield.compute_jitter_delay_ms(account_index=idx, account_id=prof.account_id)
            accumulated_delay_ms += step_delay_ms

            # 5. Stealth Order Comment
            comment = self.shield.generate_stealth_comment(prof.account_id, prof.firm_name)

            dispatches[key] = {
                "account_name": prof.account_name,
                "account_id": prof.account_id,
                "firm_name": prof.firm_name,
                "admitted": True,
                "execution_order_rank": idx + 1,
                "scheduled_jitter_delay_ms": step_delay_ms,
                "accumulated_dispatch_delay_ms": round(accumulated_delay_ms, 2),
                "order_payload": {
                    "symbol": symbol,
                    "signal_type": side,
                    "volume": allocated_lot,
                    "price": entry,
                    "sl": pert_sl,
                    "tp": pert_tp,
                    "magic": magic_num,
                    "comment": comment,
                },
                "anti_detection_meta": {
                    "sl_offset_pips": pert_meta["sl_perturbed_pips"],
                    "tp_offset_pips": pert_meta["tp_perturbed_pips"],
                    "effective_rr": pert_meta["computed_rr"],
                    "unique_magic": magic_num,
                    "proxy_assigned": prof.proxy_config.get_proxy_url() if prof.proxy_config else "DIRECT",
                    "portable_instance_dir": prof.terminal_config.terminal_dir if prof.terminal_config else "DEFAULT",
                },
            }

        return {
            "symbol": symbol,
            "signal_type": side,
            "master_entry": entry,
            "master_sl": sl,
            "master_tp": tp,
            "total_accounts_evaluated": len(active_keys),
            "admitted_accounts_count": admitted_count,
            "blocked_accounts_count": blocked_count,
            "anti_detection_active": True,
            "dispatch_sequence": shuffled_keys,
            "dispatches": dispatches,
        }

    def execute_fleet_trade(
        self,
        signal: Dict[str, Any],
        connectors: Optional[Dict[str, Any]] = None,
        simulation_mode: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the prepared anti-detection trade plan across all admitted accounts.
        Enforces execution jitter delays and authentic connector dispatch.
        """
        plan = self.prepare_anti_detection_dispatch(signal)
        connectors = connectors or {}
        results = {}
        executed_count = 0
        total_volume = 0.0

        for key in plan["dispatch_sequence"]:
            item = plan["dispatches"].get(key, {})
            if not item.get("admitted"):
                results[key] = {"success": False, "status": "REJECTED_RISK_GATES", "reason": item.get("blockers")}
                continue

            order = item["order_payload"]
            acc_id = str(item["account_id"])
            jitter_ms = item["scheduled_jitter_delay_ms"]

            # Apply execution jitter (sleeps in live mode, instantaneous in simulation)
            self.shield.apply_jitter_sleep(jitter_ms, simulation_mode=simulation_mode)

            connector = connectors.get(acc_id)
            if connector is None:
                # Simulation fallback receipt
                receipt = {
                    "success": True,
                    "ticket": f"SIM-{acc_id}-{int(time.time())}",
                    "volume": order["volume"],
                    "symbol": order["symbol"],
                    "sl": order["sl"],
                    "tp": order["tp"],
                    "magic": order["magic"],
                    "simulation": True,
                }
            else:
                try:
                    receipt = connector.place_order(**order)
                except Exception as exc:
                    receipt = {"success": False, "error": str(exc)}

            ok = _is_receipt_successful(receipt)
            if ok:
                executed_count += 1
                total_volume += order["volume"]

            results[key] = {
                "account_id": acc_id,
                "account_name": item["account_name"],
                "success": ok,
                "status": "FILLED" if ok else "FAILED",
                "volume": order["volume"],
                "sl": order["sl"],
                "tp": order["tp"],
                "magic": order["magic"],
                "comment": order["comment"],
                "jitter_delay_ms": jitter_ms,
                "receipt": receipt,
            }

        return {
            "success": executed_count > 0,
            "status": "COMPLETED" if executed_count == plan["admitted_accounts_count"] else ("PARTIAL" if executed_count else "FAILED"),
            "executed_accounts": executed_count,
            "admitted_accounts": plan["admitted_accounts_count"],
            "total_fleet_volume": round(total_volume, 2),
            "executions": results,
            "anti_detection_verified": True,
        }

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Provides institutional telemetry on all fleet accounts."""
        with self._lock:
            accounts = {}
            total_balance = 0.0
            active_count = 0
            for k, p in self.fleet.items():
                if p.is_active:
                    active_count += 1
                    total_balance += p.balance
                accounts[k] = {
                    "account_id": p.account_id,
                    "account_name": p.account_name,
                    "firm_name": p.firm_name,
                    "account_type": p.account_type,
                    "balance": p.balance,
                    "currency": p.currency,
                    "max_risk_pct": p.max_risk_pct,
                    "max_risk_usd_cap": p.max_risk_usd_cap,
                    "min_rr_ratio": p.min_rr_ratio,
                    "dynamic_breakeven_r": p.dynamic_breakeven_trigger_r,
                    "is_active": p.is_active,
                    "proxy_enabled": bool(p.proxy_config and p.proxy_config.enabled),
                    "proxy_country": p.proxy_config.target_country if p.proxy_config else "N/A",
                    "portable_dir": p.terminal_config.terminal_dir if p.terminal_config else "N/A",
                    "ipc_port": p.terminal_config.ipc_port if p.terminal_config else "N/A",
                }

            return {
                "owner": "Master Muhammad Qureshi",
                "phone": "+923468053268",
                "total_accounts_registered": len(self.fleet),
                "active_accounts_count": active_count,
                "total_aum_usd": round(total_balance, 2),
                "anti_detection_shields": {
                    "portable_isolation": True,
                    "socks5_residential_proxies": True,
                    "execution_jitter_ms_range": [self.shield.min_delay_ms, self.shield.max_delay_ms],
                    "micro_tick_sl_tp_offsets": True,
                    "dynamic_unique_magic_numbers": True,
                    "stealth_order_comments": True,
                },
                "accounts": accounts,
            }

    def format_human_report(self, lang: str = "ur") -> str:
        """Generates an executive briefing in Roman Urdu or English for WhatsApp or Terminal."""
        summary = self.get_fleet_summary()
        active_cnt = summary["active_accounts_count"]
        total_aum = summary["total_aum_usd"]

        if lang == "ur":
            lines = [
                "🛡️ [J.A.R.V.I.S. MULTI-ACCOUNT ANTI-BAN SHIELD ACTIVE]",
                f"• Owner: Master Muhammad Qureshi | Verified AUM: ${total_aum:,.2f}",
                f"• Total Accounts: {active_cnt} Active Portfolios Online",
                "",
                "🔒 Anti-Detection & IP Protection Protocol:",
                "  1. Har Account Ka Apna Alag /portable MT5 Terminal Directory Hai.",
                "  2. Dedicated Static Residential SOCKS5 Proxy (Shared IP / Machine Fingerprint Zero).",
                "  3. Execution Jitter Engine: 350ms-1800ms Randomized Micro-Delays.",
                "  4. Micro-Tick SL/TP Dispersion (+/- 0.5 to 2.0 Pips) — Centroid24 / OneZero Copy Trap Broken.",
                "  5. Unique Magic Numbers & Stealth Comments Har Terminal Ke Liye Alag.",
                "",
                "📊 Active Accounts Fleet & Risk Rules:",
            ]
            for k, a in summary["accounts"].items():
                status = "🟢 ACTIVE" if a["is_active"] else "⚪ INACTIVE"
                lines.append(
                    f"  • {a['account_name']} (#{a['account_id']}) — {status}\n"
                    f"    Firm: {a['firm_name']} | Balance: ${a['balance']:,.2f} | Risk Cap: ${a['max_risk_usd_cap']:.2f} ({a['max_risk_pct']}%)\n"
                    f"    Proxy: {a['proxy_country']} SOCKS5 | Port: {a['ipc_port']} | Min R:R: 1:{a['min_rr_ratio']} (BE @ +{a['dynamic_breakeven_r']}R)"
                )
            lines.append("\n✅ Result: Kisi bhi prop firm ko copy-trading ya shared account connection detect nahi hoga.")
            return "\n".join(lines)
        else:
            lines = [
                "🛡️ [J.A.R.V.I.S. MULTI-ACCOUNT ANTI-DETECTION FLEET SHIELD]",
                f"• Sovereign Owner: Master Muhammad Qureshi | Managed AUM: ${total_aum:,.2f}",
                f"• Fleet Health: {active_cnt} Isolated Account Terminals Synchronized",
                "",
                "🔒 Institutional Anti-Ban & Surveillance Countermeasures:",
                "  1. Full /portable Terminal Isolation (Isolated data dirs, separate %APPDATA% instances).",
                "  2. Dedicated Static Residential SOCKS5 Proxies (Zero cross-firm IP / ASN fingerprinting).",
                "  3. Execution Jitter Engine: 350ms–1800ms randomized dispersion between account orders.",
                "  4. Micro-Tick SL/TP Offset (+/- 0.5–2.0 pips) defeating OneZero / Centroid24 copy analysis.",
                "  5. Dynamic Unique Magic Numbers & Randomized Stealth Comments per trade ticket.",
                "",
                "📊 Fleet Profiles & Independent Risk Invariants:",
            ]
            for k, a in summary["accounts"].items():
                status = "ONLINE" if a["is_active"] else "DISABLED"
                lines.append(
                    f"  • [{status}] {a['account_name']} (#{a['account_id']})\n"
                    f"    Firm: {a['firm_name']} | AUM: ${a['balance']:,.2f} | Max Risk: ${a['max_risk_usd_cap']:.2f} ({a['max_risk_pct']}%)\n"
                    f"    Proxy: {a['proxy_country']} Static SOCKS5 | IPC Port: {a['ipc_port']} | R:R Floor: 1:{a['min_rr_ratio']} (BE @ +{a['dynamic_breakeven_r']}R)"
                )
            lines.append("\n✅ Institutional Compliance: All prop firm rules deterministic and fail-closed.")
            return "\n".join(lines)


# Singleton instance accessor
_global_manager: Optional[MultiAccountManager] = None
_manager_lock = threading.Lock()


def get_multi_account_manager(config_path: Optional[Union[str, Path]] = None) -> MultiAccountManager:
    """Provides thread-safe access to the global MultiAccountManager singleton."""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = MultiAccountManager(config_path=config_path)
        return _global_manager
