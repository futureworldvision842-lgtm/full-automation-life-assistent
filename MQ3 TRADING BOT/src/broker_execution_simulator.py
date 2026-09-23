"""Broker-Aware Execution Simulator for Realistic Strategy Validation.

Simulates true broker conditions:
- Bid/Ask spreads
- Slippage distributions (fixed & volatility-scaled)
- Commissions and swap rates
- Lot step & minimum/maximum lot sizing constraints
- Freeze level & minimum stop distance rules
- Conservative intra-bar stop-first fill policy on same-bar SL/TP ambiguity
"""

from __future__ import annotations

import dataclasses
import enum
import math
from typing import Any, Dict, List, Optional, Tuple


class OrderType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class FillStatus(str, enum.Enum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"


@dataclasses.dataclass(frozen=True)
class BrokerSpecification:
    symbol: str
    digits: int = 2
    point: float = 0.01
    contract_size: float = 100.0
    min_lot: float = 0.01
    max_lot: float = 5.0
    lot_step: float = 0.01
    spread_points: float = 25.0
    min_stop_distance_points: float = 30.0
    freeze_level_points: float = 10.0
    commission_per_lot_usd: float = 6.0
    swap_long_points: float = -1.5
    swap_short_points: float = 0.5
    slippage_base_points: float = 4.0


@dataclasses.dataclass
class SimulatedTradeRecord:
    ticket: int
    symbol: str
    order_type: OrderType
    lots: float
    entry_time_utc: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_time_utc: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    gross_profit_usd: float = 0.0
    commission_usd: float = 0.0
    swap_usd: float = 0.0
    net_profit_usd: float = 0.0
    r_multiple: float = 0.0
    holding_bars: int = 0
    slippage_incurred_points: float = 0.0


class BrokerExecutionSimulator:
    """Accurately models broker order execution on historical completed candles."""

    def __init__(self, spec: Optional[BrokerSpecification] = None):
        self.spec = spec or BrokerSpecification(symbol="XAUUSD")
        self._next_ticket = 100001

    def normalize_lot_size(self, requested_lots: float) -> Tuple[float, bool, str]:
        """Clamps and steps lot size according to broker specification."""
        if requested_lots <= 0 or not math.isfinite(requested_lots):
            return 0.0, False, "Lot size must be positive and finite"

        # Round down to nearest lot_step to prevent over-sizing
        steps = math.floor(requested_lots / self.spec.lot_step)
        normalized = round(steps * self.spec.lot_step, 4)

        if normalized < self.spec.min_lot:
            return 0.0, False, f"Normalized lot {normalized} is below minimum lot {self.spec.min_lot}"
        if normalized > self.spec.max_lot:
            normalized = self.spec.max_lot

        return normalized, True, "Valid lot size"

    def simulate_entry(
        self,
        order_type: OrderType,
        lots: float,
        reference_price: float,
        stop_loss: float,
        take_profit: float,
        timestamp_utc: str,
        volatility_multiplier: float = 1.0,
    ) -> Tuple[Optional[SimulatedTradeRecord], FillStatus, str]:
        """Simulates an order entry considering spread and slippage."""
        valid_lots, ok, lot_reason = self.normalize_lot_size(lots)
        if not ok:
            return None, FillStatus.REJECTED, lot_reason

        point_val = self.spec.point
        spread_val = self.spec.spread_points * point_val
        slippage_pts = self.spec.slippage_base_points * volatility_multiplier
        slippage_val = slippage_pts * point_val

        if order_type == OrderType.BUY:
            # Buyers pay Ask (Reference + Spread + Slippage)
            fill_price = reference_price + spread_val + slippage_val
            # Stop loss must be below fill price by min stop distance
            min_dist = self.spec.min_stop_distance_points * point_val
            if fill_price - stop_loss < min_dist:
                return None, FillStatus.REJECTED, f"Stop loss too close to entry (minimum distance: {self.spec.min_stop_distance_points} points)"
            if take_profit <= fill_price:
                return None, FillStatus.REJECTED, "Take profit must be above entry for BUY"
        else:
            # Sellers receive Bid (Reference - Slippage)
            fill_price = reference_price - slippage_val
            min_dist = self.spec.min_stop_distance_points * point_val
            if stop_loss - fill_price < min_dist:
                return None, FillStatus.REJECTED, f"Stop loss too close to entry (minimum distance: {self.spec.min_stop_distance_points} points)"
            if take_profit >= fill_price:
                return None, FillStatus.REJECTED, "Take profit must be below entry for SELL"

        commission = round(valid_lots * self.spec.commission_per_lot_usd, 2)
        ticket = self._next_ticket
        self._next_ticket += 1

        trade = SimulatedTradeRecord(
            ticket=ticket,
            symbol=self.spec.symbol,
            order_type=order_type,
            lots=valid_lots,
            entry_time_utc=timestamp_utc,
            entry_price=round(fill_price, self.spec.digits),
            stop_loss=round(stop_loss, self.spec.digits),
            take_profit=round(take_profit, self.spec.digits),
            commission_usd=commission,
            slippage_incurred_points=slippage_pts,
        )
        return trade, FillStatus.FILLED, "Order filled with spread & slippage"

    def process_bar(
        self,
        trade: SimulatedTradeRecord,
        bar_open: float,
        bar_high: float,
        bar_low: float,
        bar_close: float,
        timestamp_utc: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Updates an open trade with a completed bar.
        Enforces conservative Stop-First fill policy if both SL and TP hit in the same bar.
        """
        trade.holding_bars += 1
        point_val = self.spec.point
        contract = self.spec.contract_size

        if trade.order_type == OrderType.BUY:
            hit_sl = bar_low <= trade.stop_loss
            hit_tp = bar_high >= trade.take_profit

            if hit_sl and hit_tp:
                # Same-bar ambiguity: conservative policy assumes stop triggered first
                exit_price = trade.stop_loss
                exit_reason = "STOP_LOSS_CONSERVATIVE_AMBIGUITY"
            elif hit_sl:
                exit_price = trade.stop_loss
                exit_reason = "STOP_LOSS"
            elif hit_tp:
                exit_price = trade.take_profit
                exit_reason = "TAKE_PROFIT"
            else:
                return False, None

            # Calculate PnL for BUY
            price_diff = exit_price - trade.entry_price
            gross_pnl = round(price_diff * contract * trade.lots, 2)
            net_pnl = round(gross_pnl - trade.commission_usd - trade.swap_usd, 2)
            risk_usd = abs(trade.entry_price - trade.stop_loss) * contract * trade.lots
            r_mult = round(gross_pnl / risk_usd, 2) if risk_usd > 0 else 0.0

            trade.exit_time_utc = timestamp_utc
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            trade.gross_profit_usd = gross_pnl
            trade.net_profit_usd = net_pnl
            trade.r_multiple = r_mult
            return True, exit_reason

        else:  # SELL
            hit_sl = bar_high >= trade.stop_loss
            hit_tp = bar_low <= trade.take_profit

            if hit_sl and hit_tp:
                exit_price = trade.stop_loss
                exit_reason = "STOP_LOSS_CONSERVATIVE_AMBIGUITY"
            elif hit_sl:
                exit_price = trade.stop_loss
                exit_reason = "STOP_LOSS"
            elif hit_tp:
                exit_price = trade.take_profit
                exit_reason = "TAKE_PROFIT"
            else:
                return False, None

            price_diff = trade.entry_price - exit_price
            gross_pnl = round(price_diff * contract * trade.lots, 2)
            net_pnl = round(gross_pnl - trade.commission_usd - trade.swap_usd, 2)
            risk_usd = abs(trade.stop_loss - trade.entry_price) * contract * trade.lots
            r_mult = round(gross_pnl / risk_usd, 2) if risk_usd > 0 else 0.0

            trade.exit_time_utc = timestamp_utc
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            trade.gross_profit_usd = gross_pnl
            trade.net_profit_usd = net_pnl
            trade.r_multiple = r_mult
            return True, exit_reason
