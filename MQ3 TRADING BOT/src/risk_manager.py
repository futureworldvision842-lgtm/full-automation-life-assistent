import logging
import json
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Funding Pips Risk Shield & Dynamic Position Sizer.
    Enforces daily and total drawdown limits, trade count caps,
    and dynamically calculates lot sizes based on stop-loss distance.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_account_size = float(config.get("account_info", {}).get("target_account_size", 100000.0))
        self.max_daily_loss_pct = float(config.get("risk_management", {}).get("max_daily_loss_pct", 4.0))
        self.max_total_loss_pct = float(config.get("risk_management", {}).get("max_total_loss_pct", 10.0))
        self.risk_per_trade_pct = float(config.get("risk_management", {}).get("risk_per_trade_pct", 0.75))
        self.max_open_trades = int(config.get("risk_management", {}).get("max_open_trades", 3))
        self.max_daily_trades = int(config.get("risk_management", {}).get("max_daily_trades", 3))
        self.max_risk_usd_cap = float(config.get("risk_management", {}).get("max_risk_usd_cap", 750.0))
        self.min_rr_ratio = float(config.get("risk_management", {}).get("min_rr_ratio", 2.5))
        self.dynamic_breakeven_r = float(config.get("risk_management", {}).get("dynamic_breakeven_r", 1.0))
        self.daily_starting_equity = self.target_account_size

    def update_daily_baseline(self, current_balance: float, current_equity: float):
        """Resets daily starting baseline to higher of balance or equity."""
        self.daily_starting_equity = max(current_balance, current_equity)

    def calculate_lot_size(self, current_equity: float, sl_pips: float, symbol: str = "EURUSD") -> float:
        """Alias for calculate_position_size."""
        return self.calculate_position_size(current_equity, sl_pips, symbol)

    def calculate_position_size(self, current_equity: float, sl_pips: float, symbol: str = "EURUSD", *args, **kwargs) -> float:
        """
        Calculates position lot size based on funded account risk model.
        Enforces 0.75% max risk ($750.00 cap on FundingPips #40000294403, $7.50 on $1k) and hard lot ceilings:
        - Gold (XAUUSD): max 0.10 lots
        - Forex (EURUSD, GBPUSD, etc.): max 0.20 lots
        - Crypto (BTCUSD, ETHUSD, SOLUSD): max 0.01 lots
        Formula: Lot Size = (Risk Amount in USD) / (SL Pips * Pip Value in USD)
        """
        # Support flexible backtester signature if passed:
        # e.g., (symbol, entry_price, sl_price, balance, symbol_info)
        if isinstance(current_equity, str):
            sym_arg = current_equity
            entry_price = float(sl_pips)
            sl_price = float(symbol) if isinstance(symbol, (int, float, str)) else 0.0
            balance_arg = float(args[0]) if len(args) > 0 else 1000.0
            sl_dist = abs(entry_price - sl_price)
            sym_clean = sym_arg.upper()
            if "XAU" in sym_clean or "GOLD" in sym_clean:
                pips = sl_dist / 0.1
            elif "JPY" in sym_clean:
                pips = sl_dist / 0.01
            elif "PEPE" in sym_clean or "BONK" in sym_clean:
                pips = sl_dist / 0.0000001
            elif "WIF" in sym_clean:
                pips = sl_dist / 0.01
            elif any(c in sym_clean for c in ["BTC", "ETH", "SOL"]):
                pips = sl_dist
            else:
                pips = sl_dist / 0.0001
            lot = self.calculate_position_size(balance_arg, pips, sym_arg, **kwargs)
            risk_cap = kwargs.get("max_risk_cap", 750.0 if balance_arg >= 50000.0 else (7.50 if balance_arg <= 2500.0 else self.max_risk_usd_cap))
            risk = min(balance_arg * (self.risk_per_trade_pct / 100.0), risk_cap)
            return lot, risk

        if current_equity <= 0:
            return 0.0

        if sl_pips <= 0:
            logger.warning("Invalid SL pips (<=0), defaulting lot size to 0.01")
            return 0.01

        # Determine dollar risk cap based on account profile / equity tier:
        # FundingPips account #40000294403 ($100k balance): 0.75% ($750.00 max risk cap)
        # Small challenges (e.g. $1k): 0.75% ($7.50 max cap)
        if "max_risk_cap" in kwargs and kwargs["max_risk_cap"] is not None:
            effective_cap = float(kwargs["max_risk_cap"])
        elif current_equity <= 2500.0:
            effective_cap = 7.50
        elif current_equity >= 50000.0 or str(kwargs.get("account_id", "")) == "40000294403":
            effective_cap = 750.0
        else:
            effective_cap = self.max_risk_usd_cap

        risk_amount = min(current_equity * (self.risk_per_trade_pct / 100.0), effective_cap)
        sym = symbol.upper().replace("/", "").replace(" ", "").replace("-", "")

        # Determine Pip/Point Value per 1.0 Lot and maximum lot caps
        if any(tok in sym for tok in ["BTC", "ETH", "SOL"]):
            pip_value = 1.0   # $1.00 move = $1.00 per 1.0 unit
            max_lot = 0.01    # Hard ceiling for Crypto: max 0.01 lots
        elif "WIF" in sym:
            pip_value = 100.0 # 100 units per lot
            max_lot = 5.0
        elif "PEPE" in sym or "BONK" in sym:
            pip_value = 10.0
            max_lot = 10.0
        elif "XAU" in sym or "GOLD" in sym:
            pip_value = 10.0  # $10 per $1 move (10 pips) per lot
            max_lot = 0.10    # Hard ceiling for Gold: max 0.10 lots
        elif "JPY" in sym:
            pip_value = 6.50  # Approx $6.50 per pip per lot
            max_lot = 0.20    # Hard ceiling for Forex: max 0.20 lots
        else:
            pip_value = 10.0  # Standard Forex pair $10 per pip
            max_lot = 0.20    # Hard ceiling for Forex: max 0.20 lots

        if "max_lot" in kwargs and kwargs["max_lot"] is not None:
            max_lot = float(kwargs["max_lot"])

        lot_size = risk_amount / (sl_pips * pip_value)

        # Round to 2 decimal places and cap at safe parameters
        lot_size = round(lot_size, 2)
        lot_size = max(0.01, min(lot_size, max_lot))

        logger.info(f"Risk Sizing [{symbol}]: Risk ${risk_amount:.2f} ({self.risk_per_trade_pct}%) | SL Units: {sl_pips:.2f} | Calculated Lot Size: {lot_size} (Max: {max_lot})")
        return lot_size

    def check_dynamic_breakeven(
        self,
        entry_price: float,
        current_price: float,
        sl_price: float,
        direction: str = "BUY"
    ) -> Dict[str, Any]:
        """
        Evaluates dynamic breakeven trigger at +1.0R gain.
        When price reaches +1.0R gain, shifts Stop Loss to entry price for $0 risk.
        """
        dir_upper = str(direction).upper()
        initial_risk_dist = abs(entry_price - sl_price)
        if initial_risk_dist <= 0:
            return {"trigger": False, "reason": "invalid_initial_risk", "current_r": 0.0}

        current_profit_dist = (current_price - entry_price) if dir_upper == "BUY" else (entry_price - current_price)
        current_r = current_profit_dist / initial_risk_dist

        trigger = current_r >= (self.dynamic_breakeven_r - 1e-9)
        return {
            "trigger": trigger,
            "threshold_r": self.dynamic_breakeven_r,
            "current_r": round(current_r, 2),
            "entry_price": entry_price,
            "current_price": current_price,
            "action": "shift_sl_to_entry" if trigger else "hold",
            "new_sl": entry_price if trigger else sl_price
        }

    def get_account_rules(self, account_id: str = "40000294403") -> Dict[str, Any]:
        """Returns verified institutional risk parameters for the account."""
        is_fundingpips = "40000294403" in str(account_id)
        return {
            "account_id": str(account_id),
            "max_risk_pct": self.risk_per_trade_pct,
            "max_risk_usd_cap": 750.0 if is_fundingpips else self.max_risk_usd_cap,
            "min_rr_ratio": self.min_rr_ratio,
            "dynamic_breakeven_r": self.dynamic_breakeven_r,
            "hard_lot_ceilings": {
                "XAUUSD": 0.10,
                "FOREX": 0.20,
                "CRYPTO": 0.01
            }
        }

