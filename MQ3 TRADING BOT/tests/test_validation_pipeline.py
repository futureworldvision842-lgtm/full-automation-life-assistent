"""Unit tests for BrokerExecutionSimulator and WalkForwardValidator.

Verifies:
1. Lot size stepping and clamping rules.
2. Spread, slippage, and commission accounting.
3. Same-bar SL/TP ambiguity conservative stop-first policy.
4. Walk-forward out-of-sample validation and receipt creation.
"""

import pandas as pd
import numpy as np
import pytest

from src.broker_execution_simulator import (
    BrokerExecutionSimulator,
    BrokerSpecification,
    OrderType,
    FillStatus,
)
from src.validation_pipeline import WalkForwardValidator
from src.strategy_registry import StrategyRegistry, StrategyStage


def test_simulator_lot_normalization():
    spec = BrokerSpecification(symbol="XAUUSD", min_lot=0.01, max_lot=5.0, lot_step=0.01)
    sim = BrokerExecutionSimulator(spec)

    # Valid step
    lots, ok, _ = sim.normalize_lot_size(0.054)
    assert ok is True
    assert lots == 0.05

    # Below minimum
    lots, ok, reason = sim.normalize_lot_size(0.005)
    assert ok is False
    assert "below minimum" in reason

    # Above maximum
    lots, ok, _ = sim.normalize_lot_size(10.0)
    assert ok is True
    assert lots == 5.0

    # Non-finite
    lots, ok, _ = sim.normalize_lot_size(float("nan"))
    assert ok is False


def test_simulator_spread_and_slippage_deduction():
    spec = BrokerSpecification(
        symbol="XAUUSD",
        digits=2,
        point=0.01,
        spread_points=25.0,  # 0.25 USD
        slippage_base_points=5.0,  # 0.05 USD
        commission_per_lot_usd=6.0,
    )
    sim = BrokerExecutionSimulator(spec)

    trade, status, _ = sim.simulate_entry(
        order_type=OrderType.BUY,
        lots=1.0,
        reference_price=2500.00,
        stop_loss=2490.00,
        take_profit=2520.00,
        timestamp_utc="2026-08-20T12:00:00Z",
    )
    assert status == FillStatus.FILLED
    assert trade is not None
    # Entry price should be 2500.00 + 0.25 (spread) + 0.05 (slippage) = 2500.30
    assert trade.entry_price == 2500.30
    assert trade.commission_usd == 6.0


def test_simulator_conservative_same_bar_ambiguity():
    spec = BrokerSpecification(symbol="XAUUSD", digits=2, point=0.01)
    sim = BrokerExecutionSimulator(spec)

    trade, status, _ = sim.simulate_entry(
        order_type=OrderType.BUY,
        lots=0.10,
        reference_price=2500.00,
        stop_loss=2490.00,
        take_profit=2520.00,
        timestamp_utc="2026-08-20T12:00:00Z",
    )
    assert trade is not None

    # Bar with Low <= 2490 AND High >= 2520 (Extreme ambiguity bar)
    closed, reason = sim.process_bar(
        trade,
        bar_open=2500.0,
        bar_high=2530.0,
        bar_low=2480.0,
        bar_close=2510.0,
        timestamp_utc="2026-08-20T12:15:00Z",
    )
    assert closed is True
    assert reason == "STOP_LOSS_CONSERVATIVE_AMBIGUITY"
    assert trade.exit_price == 2490.00
    assert trade.net_profit_usd < 0.0


def test_walk_forward_validation_and_receipt_creation():
    reg = StrategyRegistry()
    strategy = reg.get_strategy("STRAT_TREND_CONT_OTE", "1.0.0")
    assert strategy is not None

    # Generate 500 bars of synthetic trend data
    np.random.seed(42)
    prices = 2500.0 + np.cumsum(np.random.normal(0.2, 2.0, 500))
    highs = prices + np.random.uniform(0.5, 3.0, 500)
    lows = prices - np.random.uniform(0.5, 3.0, 500)
    opens = prices - np.random.uniform(-1.0, 1.0, 500)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
    })

    validator = WalkForwardValidator()
    metrics, receipt = validator.validate_strategy_on_ohlcv(strategy, df, folds=3)

    assert metrics.total_trades >= 0
    assert receipt.receipt_id.startswith("VR_STRAT_TREND_CONT_OTE")
    assert receipt.lookahead_audit_passed is True
    assert receipt.approved_stage in (StrategyStage.DEMO, StrategyStage.RESEARCH)
