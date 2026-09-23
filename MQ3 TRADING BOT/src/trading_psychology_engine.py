"""
trading_psychology_engine.py — Institutional Behavioral Discipline & Tilt Defense Engine.
Enforces psychological rules to eliminate human/algorithmic emotional pitfalls:
  1. Anti-Revenge Trading & Post-Loss Cooldown
  2. Profit Euphoria Lock (Capital Preservation after winning streaks)
  3. Consecutive Loss Circuit Breaker
  4. Daily Over-Trading Limit (Max Trades Cap)
"""

import time
import logging
from typing import Dict, Any, Tuple
from datetime import datetime, date

logger = logging.getLogger("TradingPsychology")


class TradingPsychologyEngine:
    """
    Behavioral Discipline & Risk Psychology Guardian.
    """

    def __init__(
        self,
        post_loss_cooldown_seconds: int = 600,     # 10 min cooldown after a loss
        max_consecutive_losses: int = 2,           # 2 consecutive loss circuit breaker
        daily_profit_scale_down_threshold: float = 400.0, # Scale risk after $400 profit
        max_trades_per_day: int = 8
    ):
        self.post_loss_cooldown_seconds = post_loss_cooldown_seconds
        self.max_consecutive_losses = max_consecutive_losses
        self.profit_threshold = daily_profit_scale_down_threshold
        self.max_trades_per_day = max_trades_per_day

        # State Tracking
        self.current_day = date.today()
        self.daily_trade_count = 0
        self.consecutive_losses = 0
        self.last_loss_time = 0.0
        self.circuit_breaker_active_until = 0.0

    def _reset_if_new_day(self):
        today = date.today()
        if today != self.current_day:
            self.current_day = today
            self.daily_trade_count = 0
            self.consecutive_losses = 0
            self.circuit_breaker_active_until = 0.0

    def record_trade_outcome(self, pnl_dollar: float):
        """Records trade result for psychological tracking."""
        self._reset_if_new_day()
        self.daily_trade_count += 1

        if pnl_dollar < 0:
            self.consecutive_losses += 1
            self.last_loss_time = time.time()
            if self.consecutive_losses >= self.max_consecutive_losses:
                # Halt for 1 hour after 2 consecutive losses
                self.circuit_breaker_active_until = time.time() + 3600
                logger.warning(f"[Psychology Engine] 2 Consecutive Losses recorded. Circuit Breaker active for 60 minutes.")
        else:
            self.consecutive_losses = 0

    def evaluate_psychological_clearance(self, today_profit: float) -> Tuple[bool, str, float]:
        """
        Evaluates psychological clearance.
        Returns: (is_approved: bool, reason: str, risk_multiplier: float)
        """
        self._reset_if_new_day()
        now = time.time()

        # 1. Check Circuit Breaker
        if now < self.circuit_breaker_active_until:
            rem_min = int((self.circuit_breaker_active_until - now) / 60)
            return False, f"CONSECUTIVE_LOSS_CIRCUIT_BREAKER: In cooldown for {rem_min} more minutes.", 0.0

        # 2. Check Post-Loss Revenge Trading Cooldown
        if (now - self.last_loss_time) < self.post_loss_cooldown_seconds:
            rem_sec = int(self.post_loss_cooldown_seconds - (now - self.last_loss_time))
            return False, f"ANTI_REVENGE_COOLDOWN: Pausing for {rem_sec}s after last stop-out to ensure market calm.", 0.0

        # 3. Check Daily Max Trades Cap
        if self.daily_trade_count >= self.max_trades_per_day:
            return False, f"MAX_DAILY_TRADES_REACHED: {self.daily_trade_count}/{self.max_trades_per_day} trades completed today.", 0.0

        # 4. Profit Euphoria Risk Scaling
        risk_mult = 1.0
        if today_profit >= self.profit_threshold:
            risk_mult = 0.50  # Cut risk in half to preserve banked profit!
            reason = f"PROFIT_PROTECTION_MODE: Day profit ${today_profit:.2f} >= ${self.profit_threshold:.2f} — Risk scaled to 50%."
        else:
            reason = "PSYCHOLOGICAL_CLEARANCE_APPROVED"

        return True, reason, risk_mult
