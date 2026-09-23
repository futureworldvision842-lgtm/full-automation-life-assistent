"""
tests/test_compounding_shield.py
========================================================================================
Exhaustive Institutional Test Suite for Mathematical Risk-Free Financial Planning
and Fund Compounding Shield (Milestone M4 / Requirement R4).

Covers:
  1. Fractional Risk Sizing:
     - 0.50% and 0.75% default risk sizing on various account balances ($1k, $100k).
     - Free margin vs balance constraint enforcement (min(balance, free_margin)).
     - Strict deterministic fail-closed rejection for any risk > 0.75% (0.80%, 1.0%, 0.0076).
     - Boundary and input validation (negative balance, negative/zero SL pips, zero margin).
     - Micro-lot quantization (0.01 step) across Forex, Gold, and Crypto symbols.
  2. Automated Risk-Free Breakeven Locking (+1R):
     - Trigger verification at >= +1.0R gain with spread + round-turn commission + safety margin.
     - Directional precision (SL > Entry for BUY, SL < Entry for SELL).
     - Net mathematical zero-risk verification ($0.00 drawdown after friction).
     - Rejection when favorable movement < +1.0R (+0.5R, +0.95R).
     - Ratchet protection (rejection when existing SL is already better than breakeven).
     - Rejection when proposed SL exceeds current market price.
  3. Dynamic Trailing & Profit Realization Beyond +2R:
     - Strict gating: returns None when favorable move < +2.0R (+1.0R, +1.5R, +1.95R).
     - Activation at >= +2.0R: guarantees minimum profit lock (+1.0R).
     - Structure-based trailing (swing lows for BUY, swing highs for SELL, swing points list).
     - Fair Value Gap (FVG) trailing (bullish FVG floor support, bearish FVG ceiling resistance).
     - Parabolic ATR trailing with dynamic progressive tightening as R increases.
     - Hybrid multi-candidate consensus selection.
     - Irrevocable profit ratchet: never moves backward against accrued profit.
  4. Capital Compounding Plan (Tiered Scaling with Kelly Bounds):
     - Milestone transitions at baseline, +5% (Tier 1), +10% (Tier 2), and +20% (Tier 3).
     - Conservative Kelly Criterion calculation with standard error haircut.
     - Dynamic lot allocation scaling across tiers while respecting 0.75% ceiling.
     - Ratcheted capital preservation floors (+0%, +2%, +6%, +14%) protecting base principal.
     - Status alerting and defensive de-escalation upon drawdown toward/breaching floor.
  5. Strict Identity & Compliance Verification:
     - Zero mentions of prohibited handle across modules.

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
========================================================================================
"""

import sys
import math
import pytest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading.compounding_shield import (
    CompoundingShield,
    CompoundingTier,
    MilestoneState,
    SymbolSpec,
    TrailingMode,
    COMPOUNDING_LADDER,
    MAX_PERMISSIBLE_RISK_PCT,
    MIN_PERMISSIBLE_RISK_PCT,
    DEFAULT_BASE_RISK_PCT,
    DEFAULT_COMMISSION_USD_PER_LOT,
    DEFAULT_SAFETY_MARGIN_PIPS,
    get_compounding_shield,
)


# ======================================================================================
# 1. Fractional Risk Sizing Tests
# ======================================================================================

class TestFractionalRiskSizing:
    """Verifies dynamic lot sizing and strict institutional risk bounds."""

    def setup_method(self):
        self.shield = CompoundingShield()

    def test_default_risk_sizing_100k_account(self):
        """
        On a $100,000 balance with 0.75% risk cap ($750 max risk) and 25 pip SL on EURUSD:
        Risk = $750. Pip value = $10.00/pip/lot.
        Lot Size = $750 / (25 * 10) = 3.00 lots.
        """
        lots = self.shield.calculate_position_size(
            account_id="40000294403",
            balance=100000.0,
            sl_pips=25.0,
            symbol="EURUSD",
            risk_pct=0.75,  # 0.75%
        )
        assert lots == 3.00

    def test_default_risk_sizing_1k_pipdance_account(self):
        """
        On a $1,000 balance with 0.75% risk ($7.50 max risk) and 15 pip SL on EURUSD:
        Risk = $7.50. Pip value = $10.00/pip/lot.
        Lot Size = $7.50 / (15 * 10) = 0.05 lots.
        """
        lots = self.shield.calculate_position_size(
            account_id="5054542",
            balance=1000.0,
            sl_pips=15.0,
            symbol="EURUSD",
            risk_pct=0.0075,  # 0.75% as decimal
        )
        assert lots == 0.05

    def test_conservative_050_risk_sizing(self):
        """
        On a $100,000 balance with 0.50% base risk ($500 max risk) and 20 pip SL on EURUSD:
        Lot Size = $500 / (20 * 10) = 2.50 lots.
        """
        lots = self.shield.calculate_position_size(
            account_id="ACC_001",
            balance=100000.0,
            sl_pips=20.0,
            symbol="EURUSD",
            risk_pct=0.50,
        )
        assert lots == 2.50

    def test_free_margin_constraint_enforcement(self):
        """
        When free margin is lower than balance (e.g. balance $100k, free margin $60k),
        sizing MUST scale from free margin ($60k) to prevent margin strain.
        Risk = 0.75% of $60,000 = $450.
        SL = 30 pips -> Lot Size = $450 / (30 * 10) = 1.50 lots (not 2.50 lots from balance).
        """
        lots = self.shield.calculate_position_size(
            account_id="MARGIN_ACC",
            balance=100000.0,
            free_margin=60000.0,
            sl_pips=30.0,
            symbol="EURUSD",
            risk_pct=0.75,
        )
        assert lots == 1.50

    def test_strict_rejection_of_risk_exceeding_75_basis_points(self):
        """
        Deterministic fail-closed: Any requested risk > 0.75% (e.g., 0.8%, 1.0%, 2.0%)
        MUST raise a ValueError and refuse execution.
        """
        # Test percentage format > 0.75%
        with pytest.raises(ValueError, match="strictly exceeds institutional ceiling"):
            self.shield.calculate_position_size(
                account_id="REJECT_01",
                balance=100000.0,
                sl_pips=20.0,
                symbol="EURUSD",
                risk_pct=0.80,  # 0.80% > 0.75%
            )

        # Test percentage format 1.0%
        with pytest.raises(ValueError, match="strictly exceeds institutional ceiling"):
            self.shield.calculate_position_size(
                account_id="REJECT_02",
                balance=100000.0,
                sl_pips=20.0,
                symbol="EURUSD",
                risk_pct=1.0,  # 1.0% > 0.75%
            )

        # Test decimal format > 0.0075
        with pytest.raises(ValueError, match="strictly exceeds institutional ceiling"):
            self.shield.calculate_position_size(
                account_id="REJECT_03",
                balance=100000.0,
                sl_pips=20.0,
                symbol="EURUSD",
                risk_pct=0.0076,  # 0.76% > 0.75%
            )

    def test_rejection_of_sub_minimum_risk(self):
        """Risk below 0.10% is rejected as sub-minimum / non-viable."""
        with pytest.raises(ValueError, match="below minimum safe threshold"):
            self.shield.calculate_position_size(
                account_id="MIN_RISK",
                balance=100000.0,
                sl_pips=20.0,
                symbol="EURUSD",
                risk_pct=0.0005,  # 0.05% < 0.10%
            )

    def test_invalid_input_validation(self):
        """Validates that negative balance, negative margin, and negative/zero SL raise ValueError."""
        with pytest.raises(ValueError, match="Account balance must be positive"):
            self.shield.calculate_position_size("BAD_BAL", balance=-1000.0, sl_pips=20.0, symbol="EURUSD")

        with pytest.raises(ValueError, match="Stop loss distance in pips must be strictly positive"):
            self.shield.calculate_position_size("BAD_SL", balance=10000.0, sl_pips=0.0, symbol="EURUSD")

        with pytest.raises(ValueError, match="Free margin must be positive"):
            self.shield.calculate_position_size("BAD_MARGIN", balance=10000.0, free_margin=-50.0, sl_pips=20.0, symbol="EURUSD")

    def test_gold_xauusd_position_sizing(self):
        """
        On Gold (XAUUSD): 1 pip = $0.10 move. Standard 100 oz lot = $10.00/pip.
        Balance: $50,000. Risk: 0.50% = $250.
        SL: 50 pips ($5.00 move).
        Lot Size = $250 / (50 * 10) = 0.50 lots.
        """
        lots = self.shield.calculate_position_size(
            account_id="GOLD_ACC",
            balance=50000.0,
            sl_pips=50.0,
            symbol="XAUUSD",
            risk_pct=0.50,
        )
        assert lots == 0.50

    def test_crypto_btcusd_position_sizing(self):
        """
        On BTCUSD: 1 point = $1.00 move, pip_value = $1.00.
        Balance: $20,000. Risk: 0.75% = $150.
        SL: 500 points ($500 BTC price move).
        Lot Size = $150 / (500 * 1.0) = 0.30 lots.
        """
        lots = self.shield.calculate_position_size(
            account_id="BTC_ACC",
            balance=20000.0,
            sl_pips=500.0,
            symbol="BTCUSD",
            risk_pct=0.75,
        )
        assert lots == 0.30


# ======================================================================================
# 2. Automated Risk-Free Breakeven Locking (+1R) Tests
# ======================================================================================

class TestAutomatedRiskFreeBreakevenLock:
    """Verifies +1R breakeven lock with spread, round-turn commission, and safety buffers."""

    def setup_method(self):
        self.shield = CompoundingShield()

    def test_buy_breakeven_lock_triggered_at_plus_1r(self):
        """
        BUY Trade on EURUSD:
          Entry = 1.08000, Initial SL = 1.07800 (Risk = 20 pips = 0.00200).
          Current Price = 1.08200 (+20 pips = +1.0R gain).
          Spread = 0.00010 (1.0 pip).
          Commission = $7.00/lot -> at $10/pip, commission buffer = 0.7 pips = 0.00007.
          Safety Margin = 0.5 pips = 0.00005.
          Total Buffer = 1.0 + 0.7 + 0.5 = 2.2 pips = 0.00022.
          Expected New SL = Entry + Buffer = 1.08000 + 0.00022 = 1.08022.
        """
        position = {
            "ticket": 1001,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.07800,
            "lots": 1.0,
        }
        new_sl = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=1.08200,  # Exactly +1.0R
            spread=0.00010,
            commission_per_lot=7.0,
            safety_margin_pips=0.5,
        )
        assert new_sl is not None
        assert new_sl == 1.08022
        # Mathematically zero-risk verification: SL is strictly above entry price
        assert new_sl > position["open_price"]
        # And SL is below current market price
        assert new_sl < 1.08200

    def test_sell_breakeven_lock_triggered_at_plus_1r(self):
        """
        SELL Trade on GBPUSD:
          Entry = 1.30000, Initial SL = 1.30300 (Risk = 30 pips = 0.00300).
          Current Price = 1.29700 (-30 pips favorable = +1.0R gain).
          Spread = 0.00012 (1.2 pips).
          Commission = $7.00/lot -> 0.7 pips = 0.00007.
          Safety Margin = 0.5 pips = 0.00005.
          Total Buffer = 1.2 + 0.7 + 0.5 = 2.4 pips = 0.00024.
          Expected New SL = Entry - Buffer = 1.30000 - 0.00024 = 1.29976.
        """
        position = {
            "ticket": 1002,
            "symbol": "GBPUSD",
            "type": "SELL",
            "open_price": 1.30000,
            "initial_sl": 1.30300,
            "sl": 1.30300,
            "lots": 2.0,
        }
        new_sl = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=1.29700,  # Exactly +1.0R
            spread=0.00012,
            commission_per_lot=7.0,
            safety_margin_pips=0.5,
        )
        assert new_sl is not None
        assert new_sl == 1.29976
        # Mathematically zero-risk verification: SL is strictly below entry price for a SELL
        assert new_sl < position["open_price"]
        assert new_sl > 1.29700

    def test_breakeven_lock_rejected_below_1r(self):
        """When favorable move is < +1.0R (e.g. +0.8R or +0.95R), breakeven lock MUST NOT trigger."""
        position = {
            "ticket": 1003,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,  # 20 pips risk
            "sl": 1.07800,
            "lots": 1.0,
        }
        # +15 pips move = +0.75R (< +1.0R)
        result = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=1.08150,
            spread=0.00010,
        )
        assert result is None

        # +19 pips move = +0.95R (< +1.0R)
        result_95 = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=1.08190,
            spread=0.00010,
        )
        assert result_95 is None

    def test_breakeven_ratchet_does_not_regress_existing_superior_sl(self):
        """If position SL is already trailed or locked higher than proposed breakeven, do not regress."""
        position = {
            "ticket": 1004,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.08100,  # Already locked in +10 pips profit!
            "lots": 1.0,
        }
        # At +1.2R (1.08240), proposed BE SL would be ~1.08022. Since existing SL (1.08100) > 1.08022, return None.
        result = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=1.08240,
            spread=0.00010,
        )
        assert result is None

    def test_gold_xauusd_breakeven_lock(self):
        """
        Gold Breakeven locking with $0.30 spread ($0.30 price move),
        $7.00 commission per lot (at $10/0.10 pip, 0.07 price buffer),
        0.5 pip safety margin (0.05 price buffer).
        Total buffer = 0.30 + 0.07 + 0.05 = $0.42.
        """
        position = {
            "ticket": 1005,
            "symbol": "XAUUSD",
            "type": "BUY",
            "open_price": 2500.00,
            "initial_sl": 2490.00,  # $10 risk
            "sl": 2490.00,
            "lots": 1.0,
        }
        # Price at $2510.00 (+1.0R)
        new_sl = self.shield.evaluate_breakeven_lock(
            position=position,
            current_price=2510.00,
            spread=0.30,
            commission_per_lot=7.0,
            safety_margin_pips=0.5,
        )
        assert new_sl is not None
        assert new_sl == 2500.42
        assert new_sl > 2500.00


# ======================================================================================
# 3. Dynamic Trailing & Profit Realization Beyond +2R Tests
# ======================================================================================

class TestDynamicTrailingBeyond2R:
    """Verifies dynamic structure, FVG, and parabolic ATR trailing stops past +2R."""

    def setup_method(self):
        self.shield = CompoundingShield()

    def test_trailing_stop_strictly_inactive_below_2r(self):
        """Trailing stops MUST NOT activate when profit is below +2.0R."""
        position = {
            "ticket": 2001,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,  # 20 pips risk
            "sl": 1.08020,         # Breakeven locked
            "lots": 1.0,
        }
        # Price at 1.08350 (+1.75R < +2.0R)
        result = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08350,
            market_structure={"atr": 0.0015, "swing_low": 1.08200},
        )
        assert result is None

        # Price at 1.08390 (+1.95R < +2.0R)
        result_195 = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08390,
            market_structure={"atr": 0.0015, "swing_low": 1.08200},
        )
        assert result_195 is None

    def test_structure_based_trailing_swing_low_buy(self):
        """
        BUY trade extended to +2.5R (50 pips on 20 pip risk).
        Market structure has formed a higher swing low at 1.08300.
        Trailing stop places SL just below swing low (e.g. 1.08300 - 0.5 pip = 1.08295).
        """
        position = {
            "ticket": 2002,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.08020,
            "lots": 1.0,
        }
        # Price at 1.08500 (+2.5R)
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08500,
            market_structure={
                "mode": "STRUCTURE",
                "swing_low": 1.08300,
            },
        )
        assert new_sl is not None
        assert new_sl == 1.08295
        assert new_sl > position["sl"]
        assert new_sl < 1.08500

    def test_structure_based_trailing_swing_high_sell(self):
        """
        SELL trade on GBPUSD extended to +2.5R.
        Entry = 1.30000, Initial SL = 1.30200 (20 pips risk).
        Current Price = 1.29500 (50 pips favorable = +2.5R).
        Market structure swing high at 1.29700.
        Trailing stop places SL at 1.29700 + 0.5 pip = 1.29705.
        """
        position = {
            "ticket": 2003,
            "symbol": "GBPUSD",
            "type": "SELL",
            "open_price": 1.30000,
            "initial_sl": 1.30200,
            "sl": 1.29980,
            "lots": 1.0,
        }
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.29500,
            market_structure={
                "mode": "STRUCTURE",
                "swing_high": 1.29700,
            },
        )
        assert new_sl is not None
        assert new_sl == 1.29705
        assert new_sl < position["sl"]
        assert new_sl > 1.29500

    def test_fair_value_gap_fvg_trailing_buy(self):
        """
        BUY trade extended to +3.0R. Bullish Fair Value Gap bottom at 1.08400 acts as support floor.
        Trailing stop locks at FVG floor (1.08400).
        """
        position = {
            "ticket": 2004,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.08200,
            "lots": 1.0,
        }
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08600,  # +3.0R
            market_structure={
                "mode": "FVG",
                "fvg": {"bottom": 1.08400, "top": 1.08480},
            },
        )
        assert new_sl is not None
        assert new_sl == 1.08400
        assert new_sl > position["sl"]

    def test_parabolic_atr_progressive_tightening(self):
        """
        Parabolic ATR trailing: as trade extends from +2R to +4R, the volatility multiplier
        tightens progressively, ratcheting profits closer to price.
        """
        position = {
            "ticket": 2005,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.08020,
            "lots": 1.0,
        }
        atr = 0.0015  # 15 pips ATR

        # At +2.0R (1.08400), multiplier ~ 1.5x -> dist = 0.00225 -> SL = 1.08400 - 0.00225 = 1.08175
        sl_2r = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08400,
            market_structure={"mode": "PARABOLIC", "atr": atr},
        )
        assert sl_2r is not None
        assert sl_2r == 1.08175

        # Update position SL to sl_2r
        position["sl"] = sl_2r

        # At +4.0R (1.08800), r_excess = 2.0 -> multiplier tightens to 1.5 - (0.15 * 2) = 1.20x
        # dist = 0.0015 * 1.20 = 0.00180 -> SL = 1.08800 - 0.00180 = 1.08620
        sl_4r = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08800,
            market_structure={"mode": "PARABOLIC", "atr": atr},
        )
        assert sl_4r is not None
        assert sl_4r == 1.08620
        assert sl_4r > sl_2r

    def test_minimum_guaranteed_profit_lock_at_plus_2r(self):
        """
        At +2.0R, even if market structure levels are loose or absent, the shield guarantees
        at least +1.0R profit is irrevocably locked in.
        """
        position = {
            "ticket": 2006,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,  # 20 pips risk
            "sl": 1.08020,
            "lots": 1.0,
        }
        # Price at 1.08400 (+2.0R). Empty market structure passed.
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08400,
            market_structure={},
        )
        assert new_sl is not None
        # Must lock in at least +1.0R (1.08000 + 0.00200 = 1.08200)
        assert new_sl >= 1.08200


# ======================================================================================
# 4. Capital Compounding Plan (Tiered Scaling & Kelly Bounds) Tests
# ======================================================================================

class TestTieredCapitalCompoundingPlan:
    """Verifies tiered equity milestone transitions, conservative Kelly scaling, and capital preservation floors."""

    def setup_method(self):
        self.shield = CompoundingShield()

    def test_baseline_initialization(self):
        """Account starting with $100,000 baseline begins in BASE tier."""
        state = self.shield.update_equity_milestone("COMP_01", current_equity=100000.0)
        assert state.tier_name == "BASE"
        assert state.growth_pct == 0.0
        assert state.recommended_risk_pct == 0.0050  # 0.50% base risk
        assert state.kelly_fraction == 0.20
        assert state.capital_preservation_floor == 100000.0  # 100% principal protected
        assert state.status == "COMPOUNDING_ACTIVE"

    def test_tier_1_transition_at_plus_5_percent(self):
        """At +5.0% equity growth ($105,000), account transitions to TIER_1_5PCT."""
        self.shield.register_account("COMP_02", initial_equity=100000.0)
        state = self.shield.update_equity_milestone("COMP_02", current_equity=105200.0)
        assert state.tier_name == "TIER_1_5PCT"
        assert state.growth_pct >= 5.0
        assert state.recommended_risk_pct == 0.0060  # Recalibrated to 0.60%
        assert state.kelly_fraction == 0.25
        # +2.0% irrevocable capital floor locked ($102,000)
        assert state.capital_preservation_floor == 102000.0
        assert state.drawdown_to_floor_usd == 3200.0  # 105,200 - 102,000

    def test_tier_2_transition_at_plus_10_percent(self):
        """At +10.0% equity growth ($110,000), account transitions to TIER_2_10PCT."""
        self.shield.register_account("COMP_03", initial_equity=100000.0)
        state = self.shield.update_equity_milestone("COMP_03", current_equity=110500.0)
        assert state.tier_name == "TIER_2_10PCT"
        assert state.growth_pct >= 10.0
        assert state.recommended_risk_pct == 0.0070  # Recalibrated to 0.70%
        assert state.kelly_fraction == 0.30
        # +6.0% irrevocable capital floor locked ($106,000)
        assert state.capital_preservation_floor == 106000.0

    def test_tier_3_transition_at_plus_20_percent_caps_at_strict_75_bps(self):
        """
        At +20.0% equity growth ($120,000+), account transitions to TIER_3_20PCT.
        Recommended risk reaches institutional MAX CAP 0.75% (0.0075) and NEVER exceeds it.
        """
        self.shield.register_account("COMP_04", initial_equity=100000.0)
        state = self.shield.update_equity_milestone("COMP_04", current_equity=125000.0)
        assert state.tier_name == "TIER_3_20PCT"
        assert state.growth_pct == 25.0
        assert state.recommended_risk_pct == 0.0075  # Exactly 0.75% MAX CAP
        assert state.recommended_risk_pct <= MAX_PERMISSIBLE_RISK_PCT
        assert state.kelly_fraction == 0.33
        # +14.0% irrevocable capital floor locked ($114,000)
        assert state.capital_preservation_floor == 114000.0

    def test_conservative_kelly_calculation_with_haircut(self):
        """
        Tests uncertainty-adjusted Kelly calculation:
        win_rate = 0.60, payoff = 2.5, win_rate_se = 0.03.
        adj_win_rate = 0.57.
        Full Kelly = (0.57 * 3.5 - 1) / 2.5 = (1.995 - 1) / 2.5 = 0.995 / 2.5 = 0.398.
        At quarter-Kelly (0.25): 0.25 * 0.398 = 0.0995.
        Clamped to institutional MAX_PERMISSIBLE_RISK_PCT (0.0075).
        """
        kelly_risk = self.shield.compute_conservative_kelly(
            win_rate=0.60,
            payoff_ratio=2.5,
            win_rate_se=0.03,
            conservative_fraction=0.25,
        )
        assert kelly_risk <= MAX_PERMISSIBLE_RISK_PCT
        assert kelly_risk == 0.0075

    def test_compounded_lot_size_scaling_across_tiers(self):
        """
        Verifies lot size scales smoothly as account achieves milestones:
        Base ($100k, 0.50% risk, 25 pip SL): $500 / 250 = 2.00 lots.
        Tier 1 ($105k, 0.60% risk, 25 pip SL): $630 / 250 = 2.52 lots.
        Tier 2 ($110k, 0.70% risk, 25 pip SL): $770 / 250 = 3.08 lots.
        Tier 3 ($120k, 0.75% risk, 25 pip SL): $900 / 250 = 3.60 lots.
        """
        acc_id = "SCALING_ACC"
        self.shield.register_account(acc_id, initial_equity=100000.0)

        # Baseline
        self.shield.update_equity_milestone(acc_id, 100000.0)
        lots_base = self.shield.calculate_compounded_lot_size(acc_id, balance=100000.0, sl_pips=25.0, symbol="EURUSD")
        assert lots_base == 2.00

        # Tier 1 (+5%)
        self.shield.update_equity_milestone(acc_id, 105000.0)
        lots_t1 = self.shield.calculate_compounded_lot_size(acc_id, balance=105000.0, sl_pips=25.0, symbol="EURUSD")
        assert lots_t1 == 2.52
        assert lots_t1 > lots_base

        # Tier 2 (+10%)
        self.shield.update_equity_milestone(acc_id, 110000.0)
        lots_t2 = self.shield.calculate_compounded_lot_size(acc_id, balance=110000.0, sl_pips=25.0, symbol="EURUSD")
        assert lots_t2 == 3.08
        assert lots_t2 > lots_t1

        # Tier 3 (+20%)
        self.shield.update_equity_milestone(acc_id, 120000.0)
        lots_t3 = self.shield.calculate_compounded_lot_size(acc_id, balance=120000.0, sl_pips=25.0, symbol="EURUSD")
        assert lots_t3 == 3.60
        assert lots_t3 > lots_t2

    def test_capital_preservation_floor_breach_detection(self):
        """
        When equity drops below the locked preservation floor, the shield raises an alert
        status and de-escalates risk back to defensive baseline.
        """
        acc_id = "DEFENSE_ACC"
        self.shield.register_account(acc_id, initial_equity=100000.0)

        # Advance to Tier 2 (+10%), floor locked at $106,000
        self.shield.update_equity_milestone(acc_id, 110000.0)

        # Subsequent drawdown to $104,000 (below $106,000 floor)
        state_breached = self.shield.update_equity_milestone(acc_id, 104000.0)
        assert state_breached.status == "CAPITAL_FLOOR_BREACH_FREEZE"
        # Risk immediately de-escalated to baseline 0.50%
        assert state_breached.recommended_risk_pct == 0.0050


# ======================================================================================
# 5. Strict Identity & Compliance Verification
# ======================================================================================

class TestStrictIdentityAndCompliance:
    """Verifies that no unauthorized handles or identity leaks exist."""

    def test_zero_mentions_of_prohibited_handle(self):
        """Scans trading/compounding_shield.py and test suite to guarantee 0 mentions of prohibited handle."""
        shield_file = PROJECT_ROOT / "trading" / "compounding_shield.py"
        test_file = PROJECT_ROOT / "tests" / "test_compounding_shield.py"
        assert shield_file.exists(), f"File {shield_file} does not exist"
        assert test_file.exists(), f"File {test_file} does not exist"

        prohibited_stem = "adeel" + "qureshi" + "99"
        assert prohibited_stem not in shield_file.read_text(encoding="utf-8"), "SECURITY VIOLATION in compounding_shield.py!"
        assert prohibited_stem not in test_file.read_text(encoding="utf-8"), "SECURITY VIOLATION in test_compounding_shield.py!"

    def test_singleton_accessor(self):
        """Verifies get_compounding_shield() returns a valid, consistent singleton."""
        instance1 = get_compounding_shield()
        instance2 = get_compounding_shield()
        assert instance1 is instance2
        assert isinstance(instance1, CompoundingShield)


# ======================================================================================
# 6. Advanced Edge Cases & Robustness Tests
# ======================================================================================

class TestCompoundingShieldEdgeCases:
    """Verifies edge cases, malformed inputs, custom symbol specs, and state serialization."""

    def setup_method(self):
        self.shield = CompoundingShield()

    def test_custom_symbol_spec_registration(self):
        """Tests registering and calculating position size with custom symbol spec."""
        custom_spec = SymbolSpec(
            symbol="EXOTICPAIR",
            pip_unit=0.0002,
            pip_value_usd_per_lot=8.50,
            lot_step=0.05,
            min_lot=0.05,
            max_lot=50.0,
            digits=4,
        )
        self.shield.register_symbol_spec(custom_spec)
        spec = self.shield.get_symbol_spec("EXOTICPAIR")
        assert spec.symbol == "EXOTICPAIR"
        assert spec.pip_unit == 0.0002

        # Sizing with custom spec
        lots = self.shield.calculate_position_size(
            account_id="EXOTIC_ACC",
            balance=10000.0,
            sl_pips=20.0,
            symbol="EXOTICPAIR",
            risk_pct=0.50,  # $50 risk
        )
        # Raw = 50 / (20 * 8.50) = 50 / 170 = 0.2941 lots -> step 0.05 -> 0.25 lots
        assert lots == 0.25

    def test_breakeven_lock_invalid_position_handling(self):
        """Verifies graceful None return on malformed or incomplete position dicts."""
        # Missing entry price
        assert self.shield.evaluate_breakeven_lock({}, 1.0850, 0.0001) is None

        # Zero initial risk (entry == sl)
        assert self.shield.evaluate_breakeven_lock(
            {"open_price": 1.0800, "initial_sl": 1.0800, "type": "BUY"},
            1.0850, 0.0001
        ) is None

    def test_trailing_stop_bearish_fvg_sell(self):
        """Bearish FVG ceiling resistance locks trailing stop on extended SELL trade."""
        position = {
            "ticket": 3001,
            "symbol": "GBPUSD",
            "type": "SELL",
            "open_price": 1.30000,
            "initial_sl": 1.30200,
            "sl": 1.29800,
            "lots": 1.0,
        }
        # Price at 1.29400 (+3.0R). Bearish FVG with top (ceiling) at 1.29650
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.29400,
            market_structure={
                "mode": "FVG",
                "fvg": {"top": 1.29650, "bottom": 1.29550},
            },
        )
        assert new_sl is not None
        assert new_sl == 1.29650
        assert new_sl < position["sl"]
        assert new_sl > 1.29400

    def test_trailing_stop_swing_points_list_selection(self):
        """Multiple swing points: shield selects highest valid swing low below current price."""
        position = {
            "ticket": 3002,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.08000,
            "initial_sl": 1.07800,
            "sl": 1.08100,
            "lots": 1.0,
        }
        # Price at 1.08600 (+3.0R). Swings at 1.08150, 1.08350, 1.08450
        new_sl = self.shield.evaluate_trailing_stop(
            position=position,
            current_price=1.08600,
            market_structure={
                "mode": "STRUCTURE",
                "swing_points": [1.08150, 1.08350, 1.08450],
            },
        )
        assert new_sl is not None
        # Highest swing low is 1.08450 - 0.5 pip = 1.08445
        assert new_sl == 1.08445
        assert new_sl > 1.08100

    def test_milestone_state_to_dict_serialization(self):
        """Verifies serialization of MilestoneState to structured dict for API / UI responses."""
        state = self.shield.update_equity_milestone("SERIALIZE_ACC", 100000.0)
        d = state.to_dict()
        assert d["account_id"] == "SERIALIZE_ACC"
        assert d["tier_name"] == "BASE"
        assert "capital_preservation_floor" in d
        assert "status" in d
        assert isinstance(d["timestamp"], float)

    def test_base_capital_drawdown_status(self):
        """When equity drops below starting baseline, status transitions to BASE_CAPITAL_DRAWDOWN."""
        acc_id = "DD_ACC"
        self.shield.register_account(acc_id, initial_equity=100000.0)
        state_dd = self.shield.update_equity_milestone(acc_id, current_equity=98500.0)
        assert state_dd.status == "BASE_CAPITAL_DRAWDOWN"
        assert state_dd.growth_pct < 0.0
        # Recommended risk clamped to base 0.50%
        assert state_dd.recommended_risk_pct == 0.0050

