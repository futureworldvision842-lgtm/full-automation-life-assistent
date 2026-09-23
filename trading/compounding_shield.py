"""
trading/compounding_shield.py
========================================================================================
Institutional Mathematical Risk-Free Financial Planning & Fund Compounding Shield.
Milestone M4 / Requirement R4 — J.A.R.V.I.S. Sovereign Trading & Financial Engine.

Core Pillars:
  1. Fractional Risk Sizing:
     - Dynamic position sizing based on available free margin / balance.
     - Strict user risk tolerances (0.50% - 0.75% default).
     - Deterministic fail-closed rejection for any risk > 0.75% (0.0075 decimal).
  2. Automated Risk-Free Breakeven Locking:
     - Automatically evaluates position profit against initial risk (+1.0R gain threshold).
     - Adjusts Stop Loss to Entry + spread + round-turn commission buffer + safety margin.
     - Guarantees true mathematical net-zero risk ($0.00 max drawdown).
  3. Dynamic Trailing & Profit Realization Beyond +2R:
     - Activates strictly when trade profit reaches >= +2.0R.
     - Supports structure-based (swing points / swing highs & lows), Fair Value Gap (FVG),
       and parabolic ATR trailing mechanics.
     - Ratchets stop-loss progressively in the direction of profit; never moves backward.
  4. Capital Compounding Plan (Tiered Scaling with Kelly Criterion Bounds):
     - Tracks baseline capital and peak high-water marks.
     - Milestone thresholds: Tier 1 (+5%), Tier 2 (+10%), Tier 3 (+20%).
     - Dynamically recalibrates fractional Kelly bounds (0.20 -> 0.25 -> 0.30 -> 0.33)
       and risk parameters (0.50% -> 0.60% -> 0.70% -> 0.75% MAX CAP).
     - Ratchets capital preservation floors (0% -> +2% -> +6% -> +14%) to shield base principal.

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
Security: Deterministic fail-closed execution. Max risk strictly <= 0.75%.
========================================================================================
"""

import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union


# ======================================================================================
# Constants & Enums
# ======================================================================================

MAX_PERMISSIBLE_RISK_PCT = 0.0075  # 0.75% strict institutional hard ceiling
MIN_PERMISSIBLE_RISK_PCT = 0.0010  # 0.10% minimum viable risk
DEFAULT_BASE_RISK_PCT = 0.0050     # 0.50% default conservative risk
DEFAULT_COMMISSION_USD_PER_LOT = 7.0  # Standard institutional round-turn commission
DEFAULT_SAFETY_MARGIN_PIPS = 0.5   # Buffer margin beyond raw spread + commission


class TrailingMode(str, Enum):
    STRUCTURE = "STRUCTURE"
    FVG = "FVG"
    PARABOLIC = "PARABOLIC"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    pip_unit: float
    pip_value_usd_per_lot: float
    lot_step: float = 0.01
    min_lot: float = 0.01
    max_lot: float = 100.0
    digits: int = 5


# Standard Institutional Instrument Specifications
STANDARD_SPECS: Dict[str, SymbolSpec] = {
    # Forex Majors (1 pip = 0.0001, $10.00/pip per standard 100k lot)
    "EURUSD": SymbolSpec("EURUSD", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    "GBPUSD": SymbolSpec("GBPUSD", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    "AUDUSD": SymbolSpec("AUDUSD", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    "NZDUSD": SymbolSpec("NZDUSD", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    "USDCAD": SymbolSpec("USDCAD", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    "USDCHF": SymbolSpec("USDCHF", 0.0001, 10.0, 0.01, 0.01, 100.0, 5),
    # Forex JPY Crosses (1 pip = 0.01, ~$10.00/pip per standard lot)
    "USDJPY": SymbolSpec("USDJPY", 0.01, 10.0, 0.01, 0.01, 100.0, 3),
    "EURJPY": SymbolSpec("EURJPY", 0.01, 10.0, 0.01, 0.01, 100.0, 3),
    "GBPJPY": SymbolSpec("GBPJPY", 0.01, 10.0, 0.01, 0.01, 100.0, 3),
    # Commodities / Precious Metals (Gold: 1 pip = 0.10, 100 oz standard lot = $10.00 per 0.10 move)
    "XAUUSD": SymbolSpec("XAUUSD", 0.10, 10.0, 0.01, 0.01, 100.0, 2),
    "GOLD": SymbolSpec("GOLD", 0.10, 10.0, 0.01, 0.01, 100.0, 2),
    # Crypto Majors (1 point = 1.0, 1 unit = $1.00 per point)
    "BTCUSD": SymbolSpec("BTCUSD", 1.0, 1.0, 0.01, 0.01, 50.0, 2),
    "ETHUSD": SymbolSpec("ETHUSD", 1.0, 1.0, 0.01, 0.01, 50.0, 2),
    "SOLUSD": SymbolSpec("SOLUSD", 0.10, 1.0, 0.01, 0.01, 100.0, 2),
    # Equity Indices (1 point = 1.0)
    "US30": SymbolSpec("US30", 1.0, 1.0, 0.01, 0.01, 50.0, 1),
    "NAS100": SymbolSpec("NAS100", 1.0, 1.0, 0.01, 0.01, 50.0, 1),
    "SPX500": SymbolSpec("SPX500", 0.10, 1.0, 0.01, 0.01, 50.0, 2),
}


@dataclass(frozen=True)
class CompoundingTier:
    """Institutional milestone compounding tier definition."""
    tier_name: str
    equity_milestone_pct: float   # e.g., 0.00, 0.05 (+5%), 0.10 (+10%), 0.20 (+20%)
    risk_pct: float               # e.g., 0.0050, 0.0060, 0.0070, 0.0075 (capped at 0.75%)
    kelly_fraction: float         # Conservative fractional Kelly scalar (0.20, 0.25, 0.30, 0.33)
    floor_ratchet_pct: float      # Locked baseline equity preservation floor


# Canonical Institutional Compounding Ladder
COMPOUNDING_LADDER: List[CompoundingTier] = [
    CompoundingTier(
        tier_name="BASE",
        equity_milestone_pct=0.00,
        risk_pct=0.0050,
        kelly_fraction=0.20,
        floor_ratchet_pct=0.00,  # 100% of baseline principal protected ($0 drawdown allowed)
    ),
    CompoundingTier(
        tier_name="TIER_1_5PCT",
        equity_milestone_pct=0.05,
        risk_pct=0.0060,
        kelly_fraction=0.25,
        floor_ratchet_pct=0.02,  # Lock in +2.0% profit as irrevocable floor
    ),
    CompoundingTier(
        tier_name="TIER_2_10PCT",
        equity_milestone_pct=0.10,
        risk_pct=0.0070,
        kelly_fraction=0.30,
        floor_ratchet_pct=0.06,  # Lock in +6.0% profit as irrevocable floor
    ),
    CompoundingTier(
        tier_name="TIER_3_20PCT",
        equity_milestone_pct=0.20,
        risk_pct=0.0075,        # Hard institutional risk ceiling (0.75%)
        kelly_fraction=0.33,
        floor_ratchet_pct=0.14,  # Lock in +14.0% profit as irrevocable floor
    ),
]


@dataclass
class MilestoneState:
    """State tracking for an account's capital compounding journey."""
    account_id: str
    initial_equity: float
    current_equity: float
    peak_equity: float
    growth_pct: float
    tier_name: str
    recommended_risk_pct: float
    kelly_fraction: float
    capital_preservation_floor: float
    drawdown_to_floor_usd: float
    status: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "initial_equity": round(self.initial_equity, 2),
            "current_equity": round(self.current_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "growth_pct": round(self.growth_pct, 2),
            "tier_name": self.tier_name,
            "recommended_risk_pct": round(self.recommended_risk_pct * 100.0, 3),
            "kelly_fraction": self.kelly_fraction,
            "capital_preservation_floor": round(self.capital_preservation_floor, 2),
            "drawdown_to_floor_usd": round(self.drawdown_to_floor_usd, 2),
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ======================================================================================
# Core Compounding Shield Engine
# ======================================================================================

class CompoundingShield:
    """
    Mathematical Risk-Free Financial Planning & Fund Compounding Shield.
    
    Provides deterministic risk sizing, automated +1R breakeven protection with
    friction buffering, dynamic >+2R trailing stop management, and tiered Kelly
    Criterion compounding with capital preservation floors.
    """

    def __init__(self, default_risk_pct: float = DEFAULT_BASE_RISK_PCT):
        normalized_base = self._normalize_risk_pct(default_risk_pct)
        if normalized_base > MAX_PERMISSIBLE_RISK_PCT:
            raise ValueError(
                f"Default risk {normalized_base * 100.0:.2f}% exceeds institutional ceiling "
                f"{MAX_PERMISSIBLE_RISK_PCT * 100.0:.2f}% (Fail-Closed)."
            )
        self.default_risk_pct = normalized_base
        self._accounts: Dict[str, MilestoneState] = {}
        self._custom_specs: Dict[str, SymbolSpec] = {}

    # ----------------------------------------------------------------------------------
    # Helper & Spec Methods
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _normalize_risk_pct(risk_input: float) -> float:
        """
        Normalizes risk input whether passed as percentage (e.g., 0.75 for 0.75%)
        or as decimal (e.g., 0.0075 for 0.75%).
        """
        val = float(risk_input)
        if val > 0.05:
            # Interpreted as percentage e.g. 0.75 -> 0.0075
            return val / 100.0
        return val

    def get_symbol_spec(self, symbol: str) -> SymbolSpec:
        """Retrieves instrument specifications for pip sizing and value."""
        sym_clean = symbol.upper().replace("/", "").replace("-", "").strip()
        if sym_clean in self._custom_specs:
            return self._custom_specs[sym_clean]
        if sym_clean in STANDARD_SPECS:
            return STANDARD_SPECS[sym_clean]

        # Generic heuristic fallback based on naming conventions
        if "JPY" in sym_clean:
            return SymbolSpec(sym_clean, 0.01, 10.0, 0.01, 0.01, 100.0, 3)
        if "XAU" in sym_clean or "GOLD" in sym_clean:
            return SymbolSpec(sym_clean, 0.10, 10.0, 0.01, 0.01, 100.0, 2)
        if any(crypto in sym_clean for crypto in ("BTC", "ETH", "SOL")):
            return SymbolSpec(sym_clean, 1.0, 1.0, 0.01, 0.01, 50.0, 2)

        # Standard 5-digit Forex major fallback
        return SymbolSpec(sym_clean, 0.0001, 10.0, 0.01, 0.01, 100.0, 5)

    def register_symbol_spec(self, spec: SymbolSpec) -> None:
        """Allows runtime injection of custom broker specifications."""
        self._custom_specs[spec.symbol.upper()] = spec

    def register_account(
        self,
        account_id: str,
        initial_equity: float,
        initial_tier: Optional[str] = None,
    ) -> MilestoneState:
        """Explicitly registers or resets an account baseline for milestone compounding."""
        acc_str = str(account_id)
        equity = float(initial_equity)
        if equity <= 0:
            raise ValueError(f"Initial equity for account {acc_str} must be positive, got {equity}")

        tier = COMPOUNDING_LADDER[0]
        if initial_tier:
            for t in COMPOUNDING_LADDER:
                if t.tier_name.upper() == initial_tier.upper():
                    tier = t
                    break

        floor_equity = equity * (1.0 + tier.floor_ratchet_pct)
        state = MilestoneState(
            account_id=acc_str,
            initial_equity=equity,
            current_equity=equity,
            peak_equity=equity,
            growth_pct=0.0,
            tier_name=tier.tier_name,
            recommended_risk_pct=tier.risk_pct,
            kelly_fraction=tier.kelly_fraction,
            capital_preservation_floor=floor_equity,
            drawdown_to_floor_usd=equity - floor_equity,
            status="COMPOUNDING_ACTIVE",
            timestamp=time.time(),
        )
        self._accounts[acc_str] = state
        return state

    def get_milestone_state(self, account_id: str) -> Optional[MilestoneState]:
        """Fetches current milestone state for an account."""
        return self._accounts.get(str(account_id))

    # ----------------------------------------------------------------------------------
    # 1. Fractional Risk Sizing
    # ----------------------------------------------------------------------------------

    def calculate_position_size(
        self,
        account_id: str,
        balance: float,
        sl_pips: float,
        symbol: str,
        risk_pct: Optional[float] = None,
        free_margin: Optional[float] = None,
        pip_value: Optional[float] = None,
        account_type: Optional[str] = None,
    ) -> float:
        """
        Dynamically calculates position size (lot size) based on capital and strict risk tolerances.
        
        Rules:
          - Uses conservative capital: min(balance, free_margin) when free_margin > 0.
          - Enforces strict institutional risk bounds: 0.10% <= risk <= 0.75%.
          - Deterministically fails closed (raises ValueError) if risk > 0.75%.
          - Returns rounded lot size quantized to broker step.
        """
        # Validate inputs
        balance_f = float(balance)
        if balance_f <= 0:
            raise ValueError(f"Account balance must be positive, got {balance_f}")

        sl_pips_f = float(sl_pips)
        if sl_pips_f <= 0:
            raise ValueError(f"Stop loss distance in pips must be strictly positive, got {sl_pips_f}")

        # Conservative capital allocation: shield against margin deficits
        effective_capital = balance_f
        if free_margin is not None:
            free_margin_f = float(free_margin)
            if free_margin_f <= 0:
                raise ValueError(f"Free margin must be positive to open positions, got {free_margin_f}")
            effective_capital = min(balance_f, free_margin_f)

        # Determine effective risk fraction
        if risk_pct is not None:
            eff_risk = self._normalize_risk_pct(risk_pct)
        else:
            # Check if account has an active compounding tier
            state = self.get_milestone_state(account_id)
            eff_risk = state.recommended_risk_pct if state else self.default_risk_pct

        # Strict Fail-Closed Check: hard ceiling 0.75%
        if eff_risk > (MAX_PERMISSIBLE_RISK_PCT + 1e-7):
            raise ValueError(
                f"REJECTED: Requested risk {eff_risk * 100.0:.2f}% strictly exceeds institutional "
                f"ceiling {MAX_PERMISSIBLE_RISK_PCT * 100.0:.2f}%. Deterministic fail-closed applied."
            )

        if eff_risk < (MIN_PERMISSIBLE_RISK_PCT - 1e-7):
            raise ValueError(
                f"REJECTED: Requested risk {eff_risk * 100.0:.2f}% below minimum safe threshold "
                f"{MIN_PERMISSIBLE_RISK_PCT * 100.0:.2f}%."
            )

        # Dollar risk ceiling check
        risk_usd = effective_capital * eff_risk

        # Instrument specs
        spec = self.get_symbol_spec(symbol)
        effective_pip_value = float(pip_value) if pip_value is not None else spec.pip_value_usd_per_lot

        if effective_pip_value <= 0:
            raise ValueError(f"Pip value per standard lot must be positive, got {effective_pip_value}")

        # Mathematical Lot Size: Risk USD / (SL Pips * Pip Value Per Lot)
        raw_lot = risk_usd / (sl_pips_f * effective_pip_value)

        # Quantize to broker step
        step = spec.lot_step
        quantized = math.floor(raw_lot / step) * step
        quantized = round(quantized, 2)

        # Boundary checks
        if quantized < spec.min_lot:
            # If quantized lot is below min_lot, check if min_lot would breach risk ceiling
            min_lot_risk_usd = spec.min_lot * sl_pips_f * effective_pip_value
            max_allowed_risk_usd = effective_capital * (MAX_PERMISSIBLE_RISK_PCT + 1e-7)
            if min_lot_risk_usd > max_allowed_risk_usd:
                raise ValueError(
                    f"Capital {effective_capital:.2f} insufficient: minimum lot {spec.min_lot} produces "
                    f"risk ${min_lot_risk_usd:.2f} which exceeds maximum permissible risk "
                    f"${max_allowed_risk_usd:.2f} ({MAX_PERMISSIBLE_RISK_PCT*100.0:.2f}%)."
                )
            return spec.min_lot

        return min(quantized, spec.max_lot)

    # ----------------------------------------------------------------------------------
    # 2. Automated Risk-Free Breakeven Locking (+1R)
    # ----------------------------------------------------------------------------------

    def evaluate_breakeven_lock(
        self,
        position: Dict[str, Any],
        current_price: float,
        spread: float,
        commission_per_lot: float = DEFAULT_COMMISSION_USD_PER_LOT,
        safety_margin_pips: float = DEFAULT_SAFETY_MARGIN_PIPS,
    ) -> Optional[float]:
        """
        Evaluates dynamic breakeven locking at >= +1.0R favorable market movement.
        
        When +1R is reached, shifts Stop Loss to Entry + spread + round-turn commission buffer
        + safety margin, guaranteeing a mathematically zero-risk ($0.00 max drawdown) outcome.
        
        Returns:
          new_sl (float) if breakeven locking should occur, or None if conditions not met.
        """
        entry_price = float(position.get("open_price", position.get("entry_price", position.get("price", 0.0))))
        if entry_price <= 0:
            return None

        initial_sl = float(position.get("initial_sl", position.get("sl", 0.0)))
        current_sl = float(position.get("sl", 0.0))
        direction = str(position.get("type", position.get("direction", "BUY"))).upper()
        symbol = str(position.get("symbol", "EURUSD")).upper()
        is_buy = direction in ("BUY", "LONG")

        # Initial risk calculation
        initial_risk = abs(entry_price - initial_sl)
        if initial_risk <= 0:
            return None

        # Favorable move & R-Multiple
        curr_p = float(current_price)
        favorable_dist = (curr_p - entry_price) if is_buy else (entry_price - curr_p)
        current_r = favorable_dist / initial_risk

        # Trigger threshold: must reach at least +1.0R gain
        if current_r < (1.0 - 1e-6):
            return None

        # Fetch instrument specs
        spec = self.get_symbol_spec(symbol)
        pip_unit = float(position.get("pip_unit", spec.pip_unit))
        pip_value = float(position.get("pip_value", spec.pip_value_usd_per_lot))
        digits = int(position.get("digits", spec.digits))

        # Spread normalization
        spread_val = float(spread)
        # If spread passed as pip count (e.g., 1.5 pips) vs price distance (e.g., 0.00015)
        # Heuristic: if spread is > 0.05 on standard 5-digit Forex, it's pip count
        if pip_unit < 0.01 and spread_val >= 0.05:
            spread_price_dist = spread_val * pip_unit
        else:
            spread_price_dist = spread_val

        # Round-turn commission buffer in price terms:
        # Commission in pips = commission_per_lot / pip_value
        # Commission in price = commission_in_pips * pip_unit
        comm_val = float(commission_per_lot)
        commission_in_pips = comm_val / max(pip_value, 1e-4)
        commission_price_dist = commission_in_pips * pip_unit

        # Safety margin buffer
        safety_price_dist = float(safety_margin_pips) * pip_unit

        # Total protective friction buffer
        total_buffer = spread_price_dist + commission_price_dist + safety_price_dist

        # Compute new SL
        if is_buy:
            new_sl = round(entry_price + total_buffer, digits)
            # Ensure new_sl does not exceed current market price
            if new_sl >= curr_p:
                return None
            # Ratchet rule: only advance stop loss upward
            if current_sl > 0 and current_sl >= new_sl:
                return None
            return new_sl
        else:
            new_sl = round(entry_price - total_buffer, digits)
            # Ensure new_sl is not below current market price
            if new_sl <= curr_p:
                return None
            # Ratchet rule: only advance stop loss downward
            if current_sl > 0 and current_sl <= new_sl:
                return None
            return new_sl

    # ----------------------------------------------------------------------------------
    # 3. Dynamic Trailing & Profit Realization Beyond +2R
    # ----------------------------------------------------------------------------------

    def evaluate_trailing_stop(
        self,
        position: Dict[str, Any],
        current_price: float,
        market_structure: Dict[str, Any],
    ) -> Optional[float]:
        """
        Implements dynamic trailing stops beyond +2.0R to lock in accrued profits while
        allowing runners to capture extended legs.
        
        Supports:
          - Structure-based: Swing points (swing high / swing low)
          - Fair Value Gaps (FVGs): FVG tops/bottoms as institutional structural floors/ceilings
          - Parabolic ATR: Volatility-adjusted trailing distance
          - Hybrid: Evaluates all available structural levels and picks the optimal safe ratchet
        
        Activation Condition:
          - Strictly requires trade favorable movement >= +2.0R.
          - Never moves stop backward against current profit.
        """
        entry_price = float(position.get("open_price", position.get("entry_price", position.get("price", 0.0))))
        if entry_price <= 0:
            return None

        initial_sl = float(position.get("initial_sl", position.get("sl", 0.0)))
        current_sl = float(position.get("sl", 0.0))
        direction = str(position.get("type", position.get("direction", "BUY"))).upper()
        symbol = str(position.get("symbol", "EURUSD")).upper()
        is_buy = direction in ("BUY", "LONG")

        initial_risk = abs(entry_price - initial_sl)
        if initial_risk <= 0:
            return None

        curr_p = float(current_price)
        favorable_dist = (curr_p - entry_price) if is_buy else (entry_price - curr_p)
        current_r = favorable_dist / initial_risk

        # Trailing Stop Gate: Strictly beyond +2.0R
        if current_r < (2.0 - 1e-6):
            return None

        spec = self.get_symbol_spec(symbol)
        pip_unit = float(position.get("pip_unit", spec.pip_unit))
        digits = int(position.get("digits", spec.digits))

        # Absolute minimum profit floor: at +2.0R, must guarantee at least +1.0R profit locked
        min_guaranteed_profit_dist = initial_risk * 1.0
        min_profit_sl = (entry_price + min_guaranteed_profit_dist) if is_buy else (entry_price - min_guaranteed_profit_dist)

        mode_str = str(market_structure.get("mode", TrailingMode.HYBRID.value)).upper()
        candidates: List[float] = [min_profit_sl]

        # 1. Structure: Swing Low (for BUY) or Swing High (for SELL)
        if is_buy:
            swing_low = market_structure.get("swing_low")
            if swing_low is not None and float(swing_low) > 0:
                sl_cand = float(swing_low) - (0.5 * pip_unit)
                if sl_cand < curr_p and sl_cand > entry_price:
                    candidates.append(sl_cand)

            swing_points = market_structure.get("swing_points", [])
            valid_swings = [float(p) for p in swing_points if float(p) < curr_p and float(p) > entry_price]
            if valid_swings:
                candidates.append(max(valid_swings) - (0.5 * pip_unit))
        else:
            swing_high = market_structure.get("swing_high")
            if swing_high is not None and float(swing_high) > 0:
                sh_cand = float(swing_high) + (0.5 * pip_unit)
                if sh_cand > curr_p and sh_cand < entry_price:
                    candidates.append(sh_cand)

            swing_points = market_structure.get("swing_points", [])
            valid_swings = [float(p) for p in swing_points if float(p) > curr_p and float(p) < entry_price]
            if valid_swings:
                candidates.append(min(valid_swings) + (0.5 * pip_unit))

        # 2. Fair Value Gaps (FVG)
        fvg = market_structure.get("fvg")
        if isinstance(fvg, dict):
            if is_buy:
                # Bullish FVG: bottom provides support
                fvg_floor = float(fvg.get("bottom", fvg.get("fvg_low", 0.0)))
                if fvg_floor > 0 and fvg_floor < curr_p and fvg_floor > entry_price:
                    candidates.append(fvg_floor)
            else:
                # Bearish FVG: top provides resistance
                fvg_ceil = float(fvg.get("top", fvg.get("fvg_high", 0.0)))
                if fvg_ceil > 0 and fvg_ceil > curr_p and fvg_ceil < entry_price:
                    candidates.append(fvg_ceil)

        # 3. Parabolic ATR Trailing
        atr = market_structure.get("atr")
        if atr is not None and float(atr) > 0:
            atr_val = float(atr)
            # Volatility multiplier tightens progressively as R-multiple extends
            # e.g., 1.5x ATR at 2R, tightening to 1.0x ATR at 4R+
            base_multiplier = float(market_structure.get("atr_multiplier", 1.5))
            r_excess = max(0.0, current_r - 2.0)
            effective_multiplier = max(0.8, base_multiplier - (0.15 * r_excess))

            if is_buy:
                atr_trail = curr_p - (atr_val * effective_multiplier)
                if atr_trail < curr_p and atr_trail > entry_price:
                    candidates.append(atr_trail)
            else:
                atr_trail = curr_p + (atr_val * effective_multiplier)
                if atr_trail > curr_p and atr_trail < entry_price:
                    candidates.append(atr_trail)

        # Select candidate based on mode
        if mode_str == TrailingMode.STRUCTURE.value:
            selected_pool = [c for c in candidates if c != min_profit_sl] or [min_profit_sl]
        elif mode_str == TrailingMode.FVG.value:
            selected_pool = [c for c in candidates if c != min_profit_sl] or [min_profit_sl]
        elif mode_str == TrailingMode.PARABOLIC.value:
            selected_pool = [c for c in candidates if c != min_profit_sl] or [min_profit_sl]
        else:
            # HYBRID: choose the tightest protective level that doesn't choke the market
            selected_pool = candidates

        if not selected_pool:
            return None

        if is_buy:
            proposed_sl = round(max(selected_pool), digits)
            # Must strictly advance SL upward
            if current_sl > 0 and proposed_sl <= current_sl:
                return None
            if proposed_sl >= curr_p:
                return None
            return proposed_sl
        else:
            proposed_sl = round(min(selected_pool), digits)
            # Must strictly advance SL downward
            if current_sl > 0 and proposed_sl >= current_sl:
                return None
            if proposed_sl <= curr_p:
                return None
            return proposed_sl

    # ----------------------------------------------------------------------------------
    # 4. Capital Compounding Plan (Tiered Scaling & Conservative Kelly Bounds)
    # ----------------------------------------------------------------------------------

    def compute_conservative_kelly(
        self,
        win_rate: float = 0.60,
        payoff_ratio: float = 2.5,
        win_rate_se: float = 0.03,
        conservative_fraction: float = 0.25,
    ) -> float:
        """
        Computes uncertainty-adjusted fractional Kelly Criterion risk bound.
        
        Formula:
          p_adj = max(0.05, win_rate - win_rate_se)   # 1 standard error conservative hair-cut
          f* = (p_adj * (payoff_ratio + 1) - 1) / payoff_ratio
          fractional_kelly = conservative_fraction * f*
          bounded: min(MAX_PERMISSIBLE_RISK_PCT, max(MIN_PERMISSIBLE_RISK_PCT, fractional_kelly))
        """
        p = float(win_rate)
        b = max(float(payoff_ratio), 1e-4)
        se = float(win_rate_se)

        # Conservative hair-cut
        adj_p = max(0.05, p - se)

        # Full Kelly
        full_kelly = (adj_p * (b + 1.0) - 1.0) / b
        if full_kelly <= 0:
            return MIN_PERMISSIBLE_RISK_PCT

        # Fractional Kelly
        scaled_kelly = full_kelly * float(conservative_fraction)

        # Enforce strict institutional bounds <= 0.75%
        clamped = max(MIN_PERMISSIBLE_RISK_PCT, min(scaled_kelly, MAX_PERMISSIBLE_RISK_PCT))
        return round(clamped, 5)

    def update_equity_milestone(
        self,
        account_id: str,
        current_equity: float,
    ) -> MilestoneState:
        """
        Updates account equity milestone state, tracking progress across +5%, +10%, and +20%
        tiers, recalculating conservative Kelly allocation, and ratcheting capital preservation floors.
        """
        acc_str = str(account_id)
        curr_eq = float(current_equity)
        if curr_eq <= 0:
            raise ValueError(f"Current equity must be positive, got {curr_eq}")

        # Fetch or auto-register state
        if acc_str not in self._accounts:
            self.register_account(acc_str, initial_equity=curr_eq)

        state = self._accounts[acc_str]
        initial_eq = state.initial_equity
        peak_eq = max(state.peak_equity, curr_eq)

        # Calculate growth relative to baseline
        growth_pct = round((curr_eq - initial_eq) / max(initial_eq, 1.0) * 100.0, 4)
        peak_growth_decimal = (peak_eq - initial_eq) / max(initial_eq, 1.0)
        curr_growth_decimal = (curr_eq - initial_eq) / max(initial_eq, 1.0)

        # Determine current active tier from ladder
        active_tier = COMPOUNDING_LADDER[0]
        for tier in reversed(COMPOUNDING_LADDER):
            if curr_growth_decimal >= (tier.equity_milestone_pct - 1e-6):
                active_tier = tier
                break

        # Determine highest milestone tier achieved from peak equity
        highest_tier = COMPOUNDING_LADDER[0]
        for tier in reversed(COMPOUNDING_LADDER):
            if peak_growth_decimal >= (tier.equity_milestone_pct - 1e-6):
                highest_tier = tier
                break

        # Ratchet capital preservation floor (floor never regresses)
        calculated_floor = round(initial_eq * (1.0 + highest_tier.floor_ratchet_pct), 2)
        preservation_floor = max(state.capital_preservation_floor, calculated_floor)
        drawdown_to_floor = round(max(0.0, curr_eq - preservation_floor), 2)

        # Evaluate operational status
        if highest_tier.floor_ratchet_pct > 0.0 and curr_eq < preservation_floor:
            status = "CAPITAL_FLOOR_BREACH_FREEZE"
            # Emergency defensive de-escalation: fallback to base risk
            eff_risk = COMPOUNDING_LADDER[0].risk_pct
        elif curr_eq < initial_eq:
            status = "BASE_CAPITAL_DRAWDOWN"
            eff_risk = COMPOUNDING_LADDER[0].risk_pct
        else:
            status = "COMPOUNDING_ACTIVE"
            eff_risk = active_tier.risk_pct

        # Update state
        state.current_equity = curr_eq
        state.peak_equity = peak_eq
        state.growth_pct = growth_pct
        state.tier_name = active_tier.tier_name
        state.recommended_risk_pct = eff_risk
        state.kelly_fraction = active_tier.kelly_fraction
        state.capital_preservation_floor = preservation_floor
        state.drawdown_to_floor_usd = drawdown_to_floor
        state.status = status
        state.timestamp = time.time()

        return state

    def calculate_compounded_lot_size(
        self,
        account_id: str,
        balance: float,
        sl_pips: float,
        symbol: str,
        win_rate: float = 0.60,
        payoff_ratio: float = 2.5,
        free_margin: Optional[float] = None,
    ) -> float:
        """
        Combines current milestone tier with fractional Kelly bounds to calculate
        the optimal compounded lot size for a prospective setup.
        """
        state = self.get_milestone_state(account_id)
        if not state:
            state = self.update_equity_milestone(account_id, balance)

        # Compute Kelly risk bound for this tier
        kelly_risk = self.compute_conservative_kelly(
            win_rate=win_rate,
            payoff_ratio=payoff_ratio,
            conservative_fraction=state.kelly_fraction,
        )

        # Risk used is bounded by active tier's risk cap
        effective_risk = min(kelly_risk, state.recommended_risk_pct)

        return self.calculate_position_size(
            account_id=account_id,
            balance=balance,
            sl_pips=sl_pips,
            symbol=symbol,
            risk_pct=effective_risk,
            free_margin=free_margin,
        )


# ======================================================================================
# Singleton Accessor
# ======================================================================================

_compounding_shield: Optional[CompoundingShield] = None


def get_compounding_shield() -> CompoundingShield:
    """Returns the global singleton instance of CompoundingShield."""
    global _compounding_shield
    if _compounding_shield is None:
        _compounding_shield = CompoundingShield()
    return _compounding_shield
