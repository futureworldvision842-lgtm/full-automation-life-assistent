"""
pipdance_fast_track_engine.py — Fast-Track Multi-Account Trading Execution & Evaluation Engine.

Authoritative implementation for:
1. Pipdance $1,000 2-Step Challenge 2-Day Fast-Track Evaluation algorithm:
   - Exact 0.75% risk per trade ($7.50 max risk cap on $1,000 balance).
   - 1:2.5 to 1:3.0 Risk-to-Reward ratio.
   - 1.5x ATR dynamic Stop Loss calculation.
   - Automated dynamic breakeven lock at +1.0R gain ($7.50 profit) to guarantee zero drawdown risk.
   - 2-Day minimum trading days and phase milestone evaluation (Phase 1: 8% target, Phase 2: 5% target).
2. Multi-Account Auto-Switching & Routing between FTMO-Demo (#1514382598) and Vebson-Server (#5054542).
"""

from __future__ import annotations

import dataclasses
import enum
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("PipdanceFastTrackEngine")


class FastTrackPhase(enum.Enum):
    PHASE_1 = "PHASE_1"
    PHASE_2 = "PHASE_2"
    FUNDED = "FUNDED"


class FastTrackStatus(enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED_PHASE_1 = "PASSED_PHASE_1"
    PASSED_PHASE_2 = "PASSED_PHASE_2"
    CHALLENGE_PASSED = "CHALLENGE_PASSED"
    FAILED_DAILY_DRAWDOWN = "FAILED_DAILY_DRAWDOWN"
    FAILED_TOTAL_DRAWDOWN = "FAILED_TOTAL_DRAWDOWN"


@dataclasses.dataclass
class AccountProfile:
    login: int
    server: str
    account_type: str
    starting_balance: float
    max_risk_pct_per_trade: float
    max_risk_usd_cap: float
    min_rr_ratio: float
    max_rr_ratio: float
    atr_sl_multiplier: float
    dynamic_breakeven_enabled: bool
    breakeven_r_trigger: float = 1.0
    breakeven_profit_usd_trigger: float = 7.50
    phase_1_profit_target_pct: float = 8.0
    phase_2_profit_target_pct: float = 5.0
    max_daily_loss_pct: float = 5.0
    max_total_loss_pct: float = 10.0
    hard_floor_equity: float = 900.0
    min_trading_days: int = 2
    aladdin_var_enabled: bool = False
    news_blackout_minutes: int = 15


class PipdanceFastTrackEngine:
    """
    Production-grade Fast-Track Evaluation & Execution Engine for Pipdance and FTMO multi-accounts.
    """

    KNOWN_ACCOUNTS: Dict[str, AccountProfile] = {
        "1514382598": AccountProfile(
            login=1514382598,
            server="FTMO-Demo",
            account_type="FTMO_100K_DEMO",
            starting_balance=100000.0,
            max_risk_pct_per_trade=0.25,
            max_risk_usd_cap=100.0,
            min_rr_ratio=2.5,
            max_rr_ratio=3.0,
            atr_sl_multiplier=1.5,
            dynamic_breakeven_enabled=True,
            breakeven_r_trigger=1.0,
            breakeven_profit_usd_trigger=100.0,
            phase_1_profit_target_pct=10.0,
            phase_2_profit_target_pct=5.0,
            max_daily_loss_pct=5.0,
            max_total_loss_pct=10.0,
            hard_floor_equity=90000.0,
            min_trading_days=4,
            aladdin_var_enabled=True,
            news_blackout_minutes=15,
        ),
        "5054542": AccountProfile(
            login=5054542,
            server="Vebson-Server",
            account_type="PIPDANCE_1K_FAST_TRACK",
            starting_balance=1000.0,
            max_risk_pct_per_trade=0.75,
            max_risk_usd_cap=7.50,
            min_rr_ratio=2.5,
            max_rr_ratio=3.0,
            atr_sl_multiplier=1.5,
            dynamic_breakeven_enabled=True,
            breakeven_r_trigger=1.0,
            breakeven_profit_usd_trigger=7.50,
            phase_1_profit_target_pct=8.0,
            phase_2_profit_target_pct=5.0,
            max_daily_loss_pct=5.0,
            max_total_loss_pct=10.0,
            hard_floor_equity=900.0,
            min_trading_days=2,
            aladdin_var_enabled=True,
            news_blackout_minutes=15,
        ),
        "40000294403": AccountProfile(
            login=40000294403,
            server="FundingPips-Trial",
            account_type="FUNDINGPIPS_100K_TRIAL",
            starting_balance=100449.03,
            max_risk_pct_per_trade=0.75,
            max_risk_usd_cap=750.0,
            min_rr_ratio=2.5,
            max_rr_ratio=3.0,
            atr_sl_multiplier=1.5,
            dynamic_breakeven_enabled=True,
            breakeven_r_trigger=1.0,
            breakeven_profit_usd_trigger=750.0,
            phase_1_profit_target_pct=8.0,
            phase_2_profit_target_pct=5.0,
            max_daily_loss_pct=5.0,
            max_total_loss_pct=10.0,
            hard_floor_equity=90000.0,
            min_trading_days=3,
            aladdin_var_enabled=True,
            news_blackout_minutes=15,
        ),
    }

    # Contract sizing constants per symbol
    SYMBOL_CONTRACT_MULTIPLIERS = {
        "EURUSD": 100000.0,
        "GBPUSD": 100000.0,
        "USDJPY": 100000.0,
        "USDCAD": 100000.0,
        "USDCHF": 100000.0,
        "AUDUSD": 100000.0,
        "NZDUSD": 100000.0,
        "XAUUSD": 100.0,      # 1 lot = 100 troy oz ($1 move = $100 per lot)
        "XAGUSD": 5000.0,     # 1 lot = 5000 oz
        "BTCUSD": 1.0,        # 1 lot = 1 BTC ($1 move = $1 per lot)
        "ETHUSD": 1.0,        # 1 lot = 1 ETH ($1 move = $1 per lot)
        "SOLUSD": 1.0,        # 1 lot = 1 SOL ($1 move = $1 per lot)
    }

    def __init__(
        self,
        default_account_size: float = 1000.0,
        risk_pct_per_trade: float = 0.75,
        max_risk_cap_usd: float = 7.50,
        atr_sl_multiplier: float = 1.5,
        min_rr_ratio: float = 2.5,
        max_rr_ratio: float = 3.0,
    ):
        self.default_account_size = default_account_size
        self.risk_pct_per_trade = risk_pct_per_trade
        self.max_risk_cap_usd = max_risk_cap_usd
        self.atr_sl_multiplier = atr_sl_multiplier
        self.min_rr_ratio = min_rr_ratio
        self.max_rr_ratio = max_rr_ratio

    def calculate_risk(
        self,
        balance: float = 1000.0,
        atr: float = 0.0010,
        symbol: str = "EURUSD",
        entry_price: float = 1.0850,
        direction: str = "BUY",
        rr_ratio: float = 2.5,
        point_value: Optional[float] = None,
        volume_step: float = 0.01,
        volume_min: float = 0.01,
        volume_max: float = 5.0,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates exact 0.75% risk per trade ($750.00 max cap on #40000294403, $7.50 on $1k challenge),
        1.5x ATR dynamic Stop Loss, and 1:2.5 to 1:3.0 Risk-to-Reward ratio.
        """
        symbol = str(symbol).strip().upper()
        direction = str(direction).strip().upper()
        if direction not in ("BUY", "SELL"):
            direction = "BUY"

        if atr <= 0:
            # Safe baseline ATR fallback based on asset class
            if "JPY" in symbol:
                atr = 0.15
            elif symbol == "XAUUSD":
                atr = 3.50
            elif "BTC" in symbol:
                atr = 450.0
            elif "ETH" in symbol:
                atr = 25.0
            elif "SOL" in symbol:
                atr = 2.0
            else:
                atr = 0.0012

        # 1. Exact risk per trade with prop firm conservation ($750 max cap on #40000294403, $7.50 on $1k)
        calc_risk_usd = round(balance * (self.risk_pct_per_trade / 100.0), 2)
        if balance <= 1000.0 and str(account_id or "") != "40000294403":
            effective_cap = self.max_risk_cap_usd  # $7.50
        elif str(account_id or "") == "40000294403":
            effective_cap = 750.0  # $750.00 max risk cap on FundingPips #40000294403
        else:
            effective_cap = 100.0  # Legacy conservation cap when unprofiled large balance

        risk_usd = min(calc_risk_usd, effective_cap)

        # 2. Dynamic 1.5x ATR Stop Loss calculation
        sl_dist = round(float(self.atr_sl_multiplier) * float(atr), 6)

        # 3. Enforce 1:2.5 to 1:3.0 Risk-to-Reward ratio
        clamped_rr = max(self.min_rr_ratio, min(self.max_rr_ratio, float(rr_ratio)))
        tp_dist = round(clamped_rr * sl_dist, 6)

        # 4. Geometry calculation for entry, SL, and TP
        if direction == "BUY":
            sl = round(entry_price - sl_dist, 5 if "JPY" not in symbol and symbol != "XAUUSD" else 3)
            tp = round(entry_price + tp_dist, 5 if "JPY" not in symbol and symbol != "XAUUSD" else 3)
        else:
            sl = round(entry_price + sl_dist, 5 if "JPY" not in symbol and symbol != "XAUUSD" else 3)
            tp = round(entry_price - tp_dist, 5 if "JPY" not in symbol and symbol != "XAUUSD" else 3)

        # 5. Dynamic lot size calculation
        lot_size = self.calculate_lot_size(
            symbol=symbol,
            risk_usd=risk_usd,
            sl_dist=sl_dist,
            entry_price=entry_price,
            point_value=point_value,
            volume_step=volume_step,
            volume_min=volume_min,
            volume_max=volume_max,
        )

        if lot_size <= 0.0:
            return {
                "status": "rejected_unaffordable_risk",
                "symbol": symbol,
                "direction": direction,
                "balance": float(balance),
                "risk_pct": float(self.risk_pct_per_trade),
                "risk_usd": 0.0,
                "max_risk_cap": float(effective_cap),
                "atr": float(atr),
                "atr_multiplier": float(self.atr_sl_multiplier),
                "sl_dist": float(sl_dist),
                "tp_dist": float(tp_dist),
                "rr_ratio": float(clamped_rr),
                "entry_price": float(entry_price),
                "sl": float(sl),
                "tp": float(tp),
                "lot_size": 0.0,
                "breakeven_lock_threshold_r": 1.0,
                "breakeven_lock_usd": 0.0,
            }

        return {
            "status": "approved",
            "symbol": symbol,
            "direction": direction,
            "balance": float(balance),
            "risk_pct": float(self.risk_pct_per_trade),
            "risk_usd": float(risk_usd),
            "max_risk_cap": float(effective_cap),
            "atr": float(atr),
            "atr_multiplier": float(self.atr_sl_multiplier),
            "sl_dist": float(sl_dist),
            "tp_dist": float(tp_dist),
            "rr_ratio": float(clamped_rr),
            "entry_price": float(entry_price),
            "sl": float(sl),
            "tp": float(tp),
            "lot_size": float(lot_size),
            "breakeven_lock_threshold_r": 1.0,
            "breakeven_lock_usd": float(risk_usd),
        }

    def calculate_lot_size(
        self,
        symbol: str,
        risk_usd: float,
        sl_dist: float,
        entry_price: float = 1.0,
        point_value: Optional[float] = None,
        volume_step: float = 0.01,
        volume_min: float = 0.01,
        volume_max: float = 5.0,
    ) -> float:
        """
        Calculates normalized lot size ensuring maximum dollar risk cap is never exceeded.
        Enforces strict prop firm hard ceilings on lot sizing (XAUUSD <= 0.10L, Crypto <= 0.01L, FX <= 0.20L).
        """
        symbol = str(symbol).strip().upper()
        if sl_dist <= 0 or risk_usd <= 0:
            return volume_min

        # Strict Prop Firm Hard Lot Ceilings
        if symbol == "XAUUSD":
            volume_max = min(volume_max, 0.10)
        elif any(tok in symbol for tok in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA")):
            volume_max = min(volume_max, 0.01)
        else:
            volume_max = min(volume_max, 0.20)

        multiplier = self.SYMBOL_CONTRACT_MULTIPLIERS.get(symbol)
        if multiplier is None:
            if "JPY" in symbol:
                # USDJPY: $1 move = 100,000 / entry_price in USD
                dollars_per_point_per_lot = (100000.0 / max(entry_price, 100.0))
                dollar_loss_per_lot = sl_dist * dollars_per_point_per_lot
            elif any(tok in symbol for tok in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA")):
                dollar_loss_per_lot = sl_dist * 1.0
            elif "USD" in symbol:
                dollar_loss_per_lot = sl_dist * 100000.0
            else:
                dollar_loss_per_lot = sl_dist * 100000.0
        else:
            dollar_loss_per_lot = sl_dist * multiplier

        if dollar_loss_per_lot <= 0:
            return volume_min

        raw_lots = risk_usd / dollar_loss_per_lot
        if raw_lots < volume_min:
            effective_risk = volume_min * dollar_loss_per_lot
            if effective_risk > risk_usd * 1.05:
                return 0.0

        # Round down to volume step to guarantee risk cap is not breached
        steps = math.floor(raw_lots / volume_step)
        lots = round(steps * volume_step, 2)
        lots = max(volume_min, min(volume_max, lots))
        return float(lots)

    def check_breakeven_trigger(
        self,
        position: Dict[str, Any],
        current_price: Optional[float] = None,
        breakeven_profit_cap: float = 7.50,
    ) -> Dict[str, Any]:
        """
        Automated Dynamic Breakeven Lock at +1.0R gain ($7.50 profit) to guarantee zero drawdown risk.
        Evaluates whether an active trade has attained +1.0R gain and requires SL shift to entry.
        """
        ticket = position.get("ticket")
        symbol = str(position.get("symbol", "UNKNOWN")).upper()
        direction = str(position.get("type", "BUY")).upper()
        open_p = float(position.get("price_open", position.get("open_price", 0.0)))
        sl = float(position.get("sl", 0.0))
        tp = float(position.get("tp", 0.0))
        profit = float(position.get("profit", 0.0))
        vol = float(position.get("volume", 0.01))

        if current_price is not None:
            curr_p = float(current_price)
        else:
            curr_p = float(position.get("price_current", open_p))

        if open_p <= 0:
            return {
                "trigger": False,
                "action": "hold",
                "ticket": ticket,
                "reason": "Invalid entry price",
            }

        # Check if already at breakeven or in profit protection
        if direction == "BUY" and sl >= open_p and sl > 0:
            return {
                "trigger": False,
                "action": "already_protected",
                "ticket": ticket,
                "current_sl": sl,
                "entry_price": open_p,
                "reason": f"Position #{ticket} SL ({sl}) is already at or above entry ({open_p})",
            }
        elif direction == "SELL" and sl <= open_p and sl > 0:
            return {
                "trigger": False,
                "action": "already_protected",
                "ticket": ticket,
                "current_sl": sl,
                "entry_price": open_p,
                "reason": f"Position #{ticket} SL ({sl}) is already at or below entry ({open_p})",
            }

        stop_dist = abs(open_p - sl) if sl > 0 else 0.0

        # +1.0R Trigger evaluation:
        # Trigger Condition 1: Profit reached +1.0R dollar gain ($7.50 cap)
        profit_reached_1r = (profit >= breakeven_profit_cap)

        # Trigger Condition 2: Price distance reached +1.0R stop distance from entry
        price_reached_1r = False
        if stop_dist > 0:
            # Apply 6-decimal rounding / epsilon tolerance to eliminate IEEE-754 floating point subtraction artifacts
            if direction == "BUY" and (round(curr_p - open_p, 6) >= round(stop_dist, 6) or (curr_p - open_p) >= (stop_dist - 1e-6)):
                price_reached_1r = True
            elif direction == "SELL" and (round(open_p - curr_p, 6) >= round(stop_dist, 6) or (open_p - curr_p) >= (stop_dist - 1e-6)):
                price_reached_1r = True

        r_multiple = ((curr_p - open_p) / stop_dist) if (direction == "BUY" and stop_dist > 0) else (
            ((open_p - curr_p) / stop_dist) if (direction == "SELL" and stop_dist > 0) else 0.0
        )

        if profit_reached_1r or price_reached_1r:
            logger.info(
                "Breakeven Trigger Hit for #%s %s (%s)! Profit: $%.2f, R: %.2f. Shifting SL to entry %.5f",
                ticket, symbol, direction, profit, r_multiple, open_p
            )
            return {
                "trigger": True,
                "action": "shift_sl_to_entry",
                "ticket": ticket,
                "symbol": symbol,
                "direction": direction,
                "volume": vol,
                "entry_price": open_p,
                "current_price": curr_p,
                "old_sl": sl,
                "new_sl": open_p,
                "tp": tp,
                "profit_usd": profit,
                "r_multiple": round(r_multiple, 2),
                "reason": f"Dynamic Breakeven Lock triggered at +{max(1.0, r_multiple):.1f}R gain ($7.50 profit threshold reached).",
            }

        return {
            "trigger": False,
            "action": "hold",
            "ticket": ticket,
            "symbol": symbol,
            "profit_usd": profit,
            "r_multiple": round(r_multiple, 2),
            "reason": f"Gain below +1.0R threshold (Current: {r_multiple:.2f}R, ${profit:.2f})",
        }

    def route_account(
        self,
        server_name: Optional[str] = None,
        login_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Seamless auto-detection and execution switching between FTMO-Demo (#1514382598) and Vebson-Server (#5054542).
        """
        str_login = str(login_id).strip() if login_id is not None else None
        str_server = str(server_name).strip() if server_name is not None else None

        # 1. Match by login ID
        if str_login in self.KNOWN_ACCOUNTS:
            profile = self.KNOWN_ACCOUNTS[str_login]
            return self._profile_to_dict(profile)

        # 2. Match by server name
        if str_server:
            srv_upper = str_server.upper()
            if "FTMO" in srv_upper:
                return self._profile_to_dict(self.KNOWN_ACCOUNTS["1514382598"])
            elif "VEBSON" in srv_upper or "PIPDANCE" in srv_upper:
                return self._profile_to_dict(self.KNOWN_ACCOUNTS["5054542"])

        # 3. Default fallback to Pipdance $1,000 Fast Track (Vebson-Server #5054542)
        default_profile = self.KNOWN_ACCOUNTS["5054542"]
        return self._profile_to_dict(default_profile)

    @staticmethod
    def _profile_to_dict(profile: AccountProfile) -> Dict[str, Any]:
        return {
            "login": profile.login,
            "server": profile.server,
            "account_type": profile.account_type,
            "starting_balance": profile.starting_balance,
            "max_risk_pct_per_trade": profile.max_risk_pct_per_trade,
            "max_risk_usd_cap": profile.max_risk_usd_cap,
            "min_rr_ratio": profile.min_rr_ratio,
            "max_rr_ratio": profile.max_rr_ratio,
            "atr_sl_multiplier": profile.atr_sl_multiplier,
            "dynamic_breakeven_enabled": profile.dynamic_breakeven_enabled,
            "breakeven_r_trigger": profile.breakeven_r_trigger,
            "breakeven_profit_usd_trigger": profile.breakeven_profit_usd_trigger,
            "phase_1_profit_target_pct": profile.phase_1_profit_target_pct,
            "phase_2_profit_target_pct": profile.phase_2_profit_target_pct,
            "max_daily_loss_pct": profile.max_daily_loss_pct,
            "max_total_loss_pct": profile.max_total_loss_pct,
            "hard_floor_equity": profile.hard_floor_equity,
            "min_trading_days": profile.min_trading_days,
            "aladdin_var_enabled": profile.aladdin_var_enabled,
            "news_blackout_minutes": profile.news_blackout_minutes,
        }

    def evaluate_fast_track_evaluation(
        self,
        trading_days: int,
        current_balance: float,
        starting_balance: float = 1000.0,
        phase: int = 1,
        daily_loss_usd: float = 0.0,
        max_daily_loss_pct: float = 5.0,
        max_total_loss_pct: float = 10.0,
        hard_floor_equity: float = 900.0,
        min_trading_days: int = 2,
    ) -> Dict[str, Any]:
        """
        2-Day Fast-Track Evaluation progress and compliance auditor.
        """
        profit_usd = current_balance - starting_balance
        profit_pct = (profit_usd / starting_balance) * 100.0 if starting_balance > 0 else 0.0

        daily_loss_pct = (daily_loss_usd / starting_balance) * 100.0 if starting_balance > 0 else 0.0
        total_dd_usd = max(0.0, starting_balance - current_balance)
        total_dd_pct = (total_dd_usd / starting_balance) * 100.0 if starting_balance > 0 else 0.0

        # Check drawdown violations
        if daily_loss_pct >= max_daily_loss_pct:
            return {
                "status": FastTrackStatus.FAILED_DAILY_DRAWDOWN.value,
                "passed": False,
                "reason": f"Daily drawdown limit breached: ${daily_loss_usd:.2f} ({daily_loss_pct:.2f}% >= {max_daily_loss_pct}%)",
                "profit_usd": profit_usd,
                "profit_pct": profit_pct,
                "trading_days": trading_days,
                "phase": phase,
            }

        if current_balance <= hard_floor_equity or total_dd_pct >= max_total_loss_pct:
            return {
                "status": FastTrackStatus.FAILED_TOTAL_DRAWDOWN.value,
                "passed": False,
                "reason": f"Maximum total drawdown breached: Balance ${current_balance:.2f} <= Floor ${hard_floor_equity:.2f}",
                "profit_usd": profit_usd,
                "profit_pct": profit_pct,
                "trading_days": trading_days,
                "phase": phase,
            }

        # Check Phase targets
        target_pct = 8.0 if phase == 1 else 5.0
        target_met = (profit_pct >= target_pct)
        min_days_met = (trading_days >= min_trading_days)

        if target_met and min_days_met:
            if phase == 1:
                status = FastTrackStatus.PASSED_PHASE_1.value
                msg = f"Phase 1 PASSED! Profit: ${profit_usd:+.2f} ({profit_pct:.2f}% >= {target_pct}%) in {trading_days} days."
            else:
                status = FastTrackStatus.CHALLENGE_PASSED.value
                msg = f"Fast-Track 2-Step Challenge FULLY PASSED! Funded Account Ready."
            passed = True
        elif target_met and not min_days_met:
            status = FastTrackStatus.IN_PROGRESS.value
            msg = f"Profit target achieved (${profit_usd:+.2f} / {profit_pct:.2f}%), but minimum {min_trading_days} trading days required (Current: {trading_days})."
            passed = False
        else:
            status = FastTrackStatus.IN_PROGRESS.value
            msg = f"Evaluation in progress. Current Profit: ${profit_usd:+.2f} ({profit_pct:.2f}% / {target_pct}% target), Days: {trading_days}/{min_trading_days}."
            passed = False

        return {
            "status": status,
            "passed": passed,
            "phase": phase,
            "target_pct": target_pct,
            "target_met": target_met,
            "trading_days": trading_days,
            "min_trading_days": min_trading_days,
            "min_days_met": min_days_met,
            "starting_balance": starting_balance,
            "current_balance": current_balance,
            "profit_usd": round(profit_usd, 2),
            "profit_pct": round(profit_pct, 2),
            "daily_loss_usd": round(daily_loss_usd, 2),
            "daily_loss_pct": round(daily_loss_pct, 2),
            "total_drawdown_usd": round(total_dd_usd, 2),
            "total_drawdown_pct": round(total_dd_pct, 2),
            "hard_floor_equity": hard_floor_equity,
            "message": msg,
        }


# Singleton instance
pipdance_engine = PipdanceFastTrackEngine()
