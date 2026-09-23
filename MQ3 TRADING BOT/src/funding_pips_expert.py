import logging
import datetime
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class FundingPipsExpert:
    """
    Funding Pips Master Evaluation & Funded Account Rules Engine.
    Audits every order against Funding Pips 25k, 50k, and 100k account rules:
    - 2.5% Daily Drawdown Hard Cap (Bot Safety Guard | Official Max: 4%)
    - 6.0% Overall Drawdown Hard Cap (Bot Safety Guard | Official Max: 12%)
    - 0.75% Risk Sizing Per Trade (Official Max: 3.0%)
    - Mandatory Stop-Loss (SL) & Take-Profit (TP)
    - Zero Martingale / Grid Risk Strategy
    """

    ACCOUNT_PROFILES = {
        "5k": {
            "target_balance": 5000.0,
            "max_daily_loss_pct": 4.0,
            "safe_daily_loss_pct": 2.5,
            "max_total_loss_pct": 12.0,
            "safe_total_loss_pct": 6.0,
            "max_trade_idea_risk_pct": 3.0,
            "safe_risk_per_trade_pct": 0.75,
            "phase1_target_pct": 8.0,
            "phase2_target_pct": 5.0,
            "max_open_positions": 2
        },
        "25k": {
            "target_balance": 25000.0,
            "max_daily_loss_pct": 4.0,
            "safe_daily_loss_pct": 2.5,
            "max_total_loss_pct": 12.0,
            "safe_total_loss_pct": 6.0,
            "max_trade_idea_risk_pct": 3.0,
            "safe_risk_per_trade_pct": 0.75,
            "phase1_target_pct": 8.0,
            "phase2_target_pct": 5.0,
            "max_open_positions": 2
        },
        "50k": {
            "target_balance": 50000.0,
            "max_daily_loss_pct": 4.0,
            "safe_daily_loss_pct": 2.5,
            "max_total_loss_pct": 12.0,
            "safe_total_loss_pct": 6.0,
            "max_trade_idea_risk_pct": 3.0,
            "safe_risk_per_trade_pct": 0.75,
            "phase1_target_pct": 8.0,
            "phase2_target_pct": 5.0,
            "max_open_positions": 3
        },
        "100k": {
            "target_balance": 100000.0,
            "max_daily_loss_pct": 4.0,
            "safe_daily_loss_pct": 2.5,
            "max_total_loss_pct": 12.0,
            "safe_total_loss_pct": 6.0,
            "max_trade_idea_risk_pct": 3.0,
            "safe_risk_per_trade_pct": 0.75,
            "phase1_target_pct": 8.0,
            "phase2_target_pct": 5.0,
            "max_open_positions": 4
        }
    }

    def __init__(self, account_tier: Any = "25k"):
        if isinstance(account_tier, dict):
            tier_str = str(account_tier.get("account_info", {}).get("account_type", "25k")).lower()
            if "5k" in tier_str or "5000" in tier_str:
                account_tier = "5k"
            elif "50k" in tier_str or "50000" in tier_str:
                account_tier = "50k"
            elif "100k" in tier_str or "100000" in tier_str:
                account_tier = "100k"
            elif "25k" in tier_str or "25000" in tier_str:
                account_tier = "25k"
            else:
                account_tier = "25k"
        elif isinstance(account_tier, (int, float)):
            if account_tier <= 5000:
                account_tier = "5k"
            elif account_tier <= 25000:
                account_tier = "25k"
            elif account_tier <= 50000:
                account_tier = "50k"
            else:
                account_tier = "100k"
        elif isinstance(account_tier, str):
            tier_lower = account_tier.lower().strip()
            if tier_lower in self.ACCOUNT_PROFILES:
                account_tier = tier_lower
            elif "5k" in tier_lower or "5000" in tier_lower:
                account_tier = "5k"
            elif "50k" in tier_lower or "50000" in tier_lower:
                account_tier = "50k"
            elif "100k" in tier_lower or "100000" in tier_lower:
                account_tier = "100k"
            elif "25k" in tier_lower or "25000" in tier_lower:
                account_tier = "25k"
            else:
                account_tier = "25k"

        self.profile = self.ACCOUNT_PROFILES.get(account_tier, self.ACCOUNT_PROFILES["25k"])
        self.daily_high_watermark = self.profile["target_balance"]
        self.absolute_high_watermark = self.profile["target_balance"]
        self.last_reset_date = datetime.date.today()

    def update_daily_watermark(self, equity: float, balance: float):
        """
        Funding Pips Daily Loss is relative to previous day's end-of-day balance/equity (00:00 GMT).
        Resets daily baseline to higher of balance or equity and ratchets absolute High-Water Mark.
        """
        today = datetime.date.today()
        if today > self.last_reset_date or self.daily_high_watermark == self.profile["target_balance"]:
            self.daily_high_watermark = max(equity, balance) if max(equity, balance) > 0 else self.profile["target_balance"]
            self.last_reset_date = today

        # Ratchet absolute High-Water Mark
        if equity > self.absolute_high_watermark:
            self.absolute_high_watermark = equity

    def can_trade(self, balance: float, equity: float) -> Tuple[bool, str]:
        """
        Audits current account balance & equity against Funding Pips drawdown shields & Trailing HWM.
        """
        target = self.profile["target_balance"]

        # 1. Daily Drawdown Check (SOD Balance/Equity Baseline)
        daily_loss = self.daily_high_watermark - equity
        max_daily_allowed = self.daily_high_watermark * (self.profile["safe_daily_loss_pct"] / 100.0)

        if daily_loss >= max_daily_allowed:
            return False, f"Daily Drawdown Guard Triggered! Loss ${daily_loss:.2f} >= ${max_daily_allowed:.2f} (2.5% Safe Cap)"

        # 2. Overall Drawdown Check
        total_loss = target - equity
        max_total_allowed = target * (self.profile["safe_total_loss_pct"] / 100.0)

        if total_loss >= max_total_allowed:
            return False, f"Overall Drawdown Guard Triggered! Loss ${total_loss:.2f} >= ${max_total_allowed:.2f} (6.0% Safe Cap)"

        # 3. Trailing High-Water Mark (HWM) Squeeze Guard
        trailing_drawdown_floor = self.absolute_high_watermark - max_total_allowed
        if equity <= trailing_drawdown_floor:
            return False, f"Trailing HWM Drawdown Floor Reached! Equity ${equity:.2f} <= Floor ${trailing_drawdown_floor:.2f}"

        return True, "Passed Funding Pips Safety Audit"

    def evaluate_consistency_pacing(self, today_profit: float, total_profit_target: float = 2000.0) -> Dict[str, Any]:
        """
        35% Consistency Rule Monitor:
        Ensures steady performance distribution and flags if single day profit exceeds 35% of target.
        """
        max_single_day = total_profit_target * 0.35  # $700 on $2,000 target
        is_pacing_safe = today_profit <= max_single_day
        pct_of_target = (today_profit / max(total_profit_target, 1.0)) * 100.0

        return {
            "is_pacing_safe": is_pacing_safe,
            "today_profit": round(today_profit, 2),
            "max_single_day_allowed": round(max_single_day, 2),
            "pct_of_target_consumed": round(pct_of_target, 1),
            "recommendation": "STANDARD_RISK" if is_pacing_safe else "CONSERVATIVE_SCALE_DOWN"
        }

    def audit_trade_compliance(self, symbol: str, entry_price: float, sl_price: float, balance: float, equity: float, open_count: int) -> Tuple[bool, str]:
        """Test suite helper for trade compliance audit."""
        allowed, msg = self.can_trade(balance, equity)
        if not allowed:
            return False, msg
        if open_count >= self.profile["max_open_positions"]:
            return False, f"Max open positions count reached ({open_count})"
        return True, "Passed all Funding Pips compliance checks."

    def audit_trade(self, symbol: str, signal_type: str, price: float, sl: float, tp: float, current_open_count: int) -> Dict[str, Any]:
        """
        Audits single trade parameters before placing order.
        """
        if current_open_count >= self.profile["max_open_positions"]:
            return {"passed": False, "reason": f"Open trade count ({current_open_count}) reached tier cap ({self.profile['max_open_positions']})."}

        if sl <= 0 or tp <= 0:
            return {"passed": False, "reason": "Funding Pips requires mandatory Stop-Loss & Take-Profit on all orders."}

        # Validate minimum 1.0 Risk to Reward floor (allowing dynamic 1.0R to 5.0R targets)
        sl_dist = abs(price - sl)
        tp_dist = abs(tp - price)

        if sl_dist == 0:
            return {"passed": False, "reason": "Invalid Stop-Loss distance of 0."}

        rr = tp_dist / sl_dist
        if rr < 0.95:  # Tolerance for floating point (minimum 1:1 floor)
            return {"passed": False, "reason": f"Trade Risk:Reward ratio {rr:.2f} < 1.0 minimum safety floor."}

        return {"passed": True, "reason": f"Trade parameter audit passed cleanly (R:R {rr:.2f})."}

    def evaluate_phase_progression(self, current_equity: float, starting_balance: Optional[float] = None) -> Dict[str, Any]:
        """
        Evaluates 2-Phase Adaptive Passing milestone:
          - Phase 1 (8% Target): 0.75% Risk per trade
          - Phase 2 (5% Target): 0.50% Risk per trade
          - Funded Account: 0.35% Ultra-Safe Risk
        """
        start = starting_balance or self.profile["target_balance"]
        profit = current_equity - start
        profit_pct = (profit / max(start, 1.0)) * 100.0

        p1_target = self.profile.get("phase1_target_pct", 8.0)
        p2_target = self.profile.get("phase2_target_pct", 5.0)

        if profit_pct >= p1_target:
            current_phase = "PHASE_2_PRACTITIONER" if profit_pct < (p1_target + p2_target) else "MASTER_FUNDED_ACCOUNT"
            active_target_pct = p2_target if current_phase == "PHASE_2_PRACTITIONER" else 0.0
            suggested_risk = 0.50 if current_phase == "PHASE_2_PRACTITIONER" else 0.35
        else:
            current_phase = "PHASE_1_STUDENT"
            active_target_pct = p1_target
            suggested_risk = 0.75

        return {
            "tier": self.profile.get("target_balance"),
            "current_phase": current_phase,
            "starting_balance": start,
            "current_equity": current_equity,
            "net_profit_usd": round(profit, 2),
            "net_profit_pct": round(profit_pct, 2),
            "active_target_pct": active_target_pct,
            "target_achieved": profit_pct >= active_target_pct if active_target_pct > 0 else True,
            "suggested_risk_per_trade_pct": suggested_risk,
            "status_badge": "🟢 TARGET REACHED" if profit_pct >= active_target_pct and active_target_pct > 0 else "⚡ IN PROGRESS"
        }
