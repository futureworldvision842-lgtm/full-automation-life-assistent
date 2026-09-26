"""
tests/test_empirical_challenger_r1_r7.py
=========================================
Empirical Adversarial Stress Harness for Trading Risk Invariants, R:R Floor,
Dynamic Breakeven, News Blackout, Quadratic Voting Math, and Spending Ledger Array Safety.

Challenger 1 Role: critic, specialist.
Authoritative Specifications:
  1. FundingPips #40000294403 Invariant ($10M, $100k, $50k) -> max risk <= $750.0 and <= 0.75%.
  2. R:R Floor: Reject signals / orders with R:R < 2.50.
  3. Dynamic Breakeven: +1.0R gain moves stop loss to entry + offset.
  4. News Blackout: 15-minute buffer enforcement around high-impact news.
  5. Quadratic Voting Math: Edge cases (credits=0 -> weight=0 / rejected ge 1, credits=1 -> 1, credits=25 -> 5, credits=100 -> 10).
  6. Spending Ledger Array Safety: /api/gaigs/transparency/spending returns true JSON list for 'records' so .map() never crashes.
"""

import math
import time
from datetime import datetime, timezone, timedelta
import pytest
from starlette.testclient import TestClient

from dashboard import app
from trading.multi_account_manager import extract_firm_rules, get_multi_account_manager
from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from core.trading.custom_strategy_engine import (
    DeterministicRiskGuard,
    NaturalLanguageStrategyInterpreter,
    VisualRuleBuilderEngine,
    DYNAMIC_BREAKEVEN_TRIGGER_R,
    MIN_INSTITUTIONAL_RR,
    MAX_PERMISSIBLE_RISK_PCT,
    MAX_FUNDINGPIPS_USD_CAP,
    NEWS_BLACKOUT_BUFFER_MINUTES,
)
from core.research.macro_surveillance import EconomicNewsBlackoutManager
from core.research.macro_contagion_service import get_macro_contagion_service
from core.gaigs.civilization_engine import get_civilization_engine


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ==============================================================================
# 1. FundingPips #40000294403 Invariant (Extreme Balances: $10M, $100k, $50k)
# ==============================================================================
class TestFundingPipsExtremeBalances:
    """
    Stress-tests FundingPips invariant across extreme balances:
      - $10,000,000 ($10M ultra-whale)
      - $100,000 ($100k standard funded account)
      - $50,000 ($50k entry evaluation account)
    Guarantees:
      - Maximum dollar risk is strictly capped at <= $750.0
      - Maximum percentage risk is strictly capped at <= 0.75%
    """

    @pytest.mark.parametrize("balance, expected_max_usd, expected_max_pct", [
        (10_000_000.0, 750.0, 0.75),   # $10M balance: dollar cap clamps at $750.0
        (100_000.0, 750.0, 0.75),      # $100k balance: 0.75% is exactly $750.0
        (50_000.0, 375.0, 0.75),       # $50k balance: 0.75% is $375.0 (<= $750.0 and <= 0.75%)
        (1_000_000.0, 750.0, 0.75),    # $1M balance: dollar cap clamps at $750.0
        (25_000.0, 187.50, 0.75),      # $25k balance: 0.75% is $187.50
    ])
    def test_extract_firm_rules_extreme_balances(self, balance, expected_max_usd, expected_max_pct):
        rules = extract_firm_rules("FundingPips", balance=balance)
        assert rules["ok"] is True
        assert rules["balance"] == balance
        assert rules["max_risk_usd_cap"] <= 750.0
        assert rules["max_risk_usd_cap"] <= round(expected_max_usd + 1e-4, 2)
        assert rules["max_risk_per_trade_pct"] <= 0.75
        assert rules["max_risk_per_trade_pct"] <= expected_max_pct

        # Dollar risk must never exceed balance * max_risk_pct / 100
        effective_pct_at_cap = (rules["max_risk_usd_cap"] / balance) * 100.0
        assert effective_pct_at_cap <= 0.75 + 1e-6
        assert rules["max_risk_usd_cap"] <= 750.0

    @pytest.mark.parametrize("balance", [10_000_000.0, 100_000.0, 50_000.0])
    def test_deterministic_risk_guard_clamp_risk(self, balance):
        # Even if operator requests 5.0% risk on a $10M account:
        clamped_pct, clamped_usd = DeterministicRiskGuard.clamp_risk(
            requested_risk_pct=5.0,
            balance=balance,
            account_id="40000294403",
            firm_name="FundingPips"
        )
        assert clamped_usd <= 750.0
        assert clamped_pct <= 0.75
        assert clamped_usd <= round(balance * (clamped_pct / 100.0) + 0.01, 2)

    def test_api_rules_extract_endpoint_fundingpips_10m(self, client):
        resp = client.get("/api/accounts/rules/extract?firm=FundingPips&balance=10000000.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["balance"] == 10_000_000.0
        assert data["max_risk_usd_cap"] <= 750.0
        assert data["max_risk_per_trade_pct"] <= 0.75

    def test_risk_kernel_gate2_rejects_dollar_risk_exceeding_750(self):
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        # Attempt to admit order with $750.01 dollar risk
        res = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.75,
            proposed_risk_usd=750.01,
            rr_ratio=2.50,
            account_id="40000294403",
            balance=100000.0
        )
        assert res["allowed"] is False
        assert res["decision"] == "REJECTED_BLOCKED"
        assert any("exceeds max cap ($750.00)" in b for b in res["blockers"])

    def test_risk_kernel_gate2_rejects_percentage_risk_exceeding_0_75(self):
        kernel = DeterministicRiskKernel(account_id="40000294403", balance=100000.0)
        # Attempt to admit order with 0.76% risk
        res = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.76,
            proposed_risk_usd=750.0,
            rr_ratio=2.50,
            account_id="40000294403",
            balance=100000.0
        )
        assert res["allowed"] is False
        assert any("exceeds max allowed (0.75%)" in b for b in res["blockers"])


# ==============================================================================
# 2. R:R Floor (Attempt to Submit/Extract Signals with R:R < 2.50 -> Rejection)
# ==============================================================================
class TestRiskRewardFloorRejection:
    """
    Empirically verifies rejection when attempting to submit or extract signals with R:R < 2.50.
    """

    @pytest.mark.parametrize("sub_rr", [1.0, 1.5, 2.0, 2.40, 2.49, 2.499])
    def test_admission_kernel_gate8_rejects_sub_2_50_rr(self, sub_rr):
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="EURUSD",
            confluence_score=94.0,
            proposed_risk_pct=0.50,
            proposed_risk_usd=500.0,
            rr_ratio=sub_rr,
            account_id="40000294403"
        )
        assert res["allowed"] is False
        assert res["decision"] == "REJECTED_BLOCKED"
        assert any("below minimum 1:2.5" in b for b in res["blockers"])

    def test_admit_order_geometry_sub_2_50_rr_blocked(self):
        kernel = DeterministicRiskKernel()
        # Order with entry=2650.0, SL=2640.0 (dist=10), TP=2670.0 (dist=20) -> R:R = 2.0 (< 2.50)
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.0,
            "sl": 2640.0,
            "tp": 2670.0,  # 20 / 10 = 2.0 R:R
            "lot_size": 0.5,
            "confluence_score": 95.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = kernel.admit_order(order)
        assert res["allowed"] is False
        assert res["decision"] == "REJECTED_BLOCKED"
        assert res["rr_ratio"] == 2.0
        assert any("below minimum 1:2.5" in b for b in res["blockers"])

    def test_autonomous_signals_endpoint_all_signals_satisfy_rr_floor(self, client):
        resp = client.get("/api/trading/signals/autonomous")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["signals"]) > 0
        assert data["risk_governor"]["min_rr_floor"] >= 2.50

        for sig in data["signals"]:
            rr = sig["risk_reward_ratio"]
            assert rr >= 2.50, f"Signal {sig['symbol']} violated R:R floor with {rr}"
            # Also verify price geometry matches advertised R:R
            entry = sig["entry"]
            sl = sig["stop_loss"]
            tp = sig["take_profit"]
            sl_dist = abs(entry - sl)
            tp_dist = abs(tp - entry)
            calc_rr = round(tp_dist / sl_dist, 2)
            assert calc_rr >= 2.50, f"Calculated R:R {calc_rr} for {sig['symbol']} is < 2.50"

    def test_custom_strategy_engine_nlp_clamps_sub_2_50_rr(self):
        interpreter = NaturalLanguageStrategyInterpreter()
        # User requests sub-floor 1:1.5 RR: "buy gold sl 20 pips tp 30 pips"
        strat = interpreter.parse_prompt("buy gold sl 20 pips tp 30 pips", account_balance=100000.0)
        assert strat.sl_pips == 20.0
        # TP must be clamped upward to at least 20 * 2.5 = 50.0 pips
        assert strat.tp_pips >= 50.0
        assert strat.target_rr >= 2.50

    def test_custom_strategy_engine_visual_builder_clamps_sub_2_50_rr(self):
        builder = VisualRuleBuilderEngine()
        schema = {
            "symbol": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "conditions": [{"indicator": "SMC_ORDER_BLOCK", "operator": "RETESTS", "threshold": "BULLISH_OB"}],
            "risk_pct": 0.50,
            "sl_pips": 20.0,
            "tp_pips": 30.0,  # 1.5 R:R
        }
        valid, errors, strat = builder.validate_schema(schema, balance=100000.0)
        assert valid is True
        assert strat.target_rr >= 2.50
        assert strat.tp_pips >= 50.0


# ==============================================================================
# 3. Dynamic Breakeven (+1.0R Gain Moves SL to Entry + Offset)
# ==============================================================================
class TestDynamicBreakevenVerification:
    """
    Empirically verifies dynamic breakeven logic:
      - At < +1.0R gain, SL remains unchanged
      - At >= +1.0R gain, SL moves to entry + offset (BUY) or entry - offset (SELL)
      - Admitted orders in admission kernel have dynamic breakeven armed at 1.0R
    """

    def test_buy_dynamic_breakeven_trigger_and_offset(self):
        entry = 2000.0
        initial_sl = 1990.0  # 10.0 risk distance -> 1.0R = 2010.0
        pip_size = 0.10
        spread_pips = 1.0
        commission_pips = 0.5
        safety_buffer_pips = 0.5
        # Total offset = (1.0 + 0.5 + 0.5) * 0.10 = 0.20

        # Sub-1.0R excursion: current_price = 2008.0 (+0.8R)
        sub_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="BUY",
            entry=entry,
            initial_sl=initial_sl,
            current_price=2008.0,
            pip_size=pip_size,
            spread_pips=spread_pips,
            commission_pips=commission_pips,
            safety_buffer_pips=safety_buffer_pips
        )
        assert sub_sl is None, "Breakeven should not trigger below +1.0R gain"

        # Exactly +1.0R excursion: current_price = 2010.0
        at_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="BUY",
            entry=entry,
            initial_sl=initial_sl,
            current_price=2010.0,
            pip_size=pip_size,
            spread_pips=spread_pips,
            commission_pips=commission_pips,
            safety_buffer_pips=safety_buffer_pips
        )
        assert at_sl is not None
        assert at_sl == 2000.20  # entry + 0.20 offset
        assert at_sl > entry, "New SL must be locked strictly above entry to cover fees"

        # Beyond +1.0R excursion: current_price = 2015.0 (+1.5R)
        above_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="BUY",
            entry=entry,
            initial_sl=initial_sl,
            current_price=2015.0,
            pip_size=pip_size,
            spread_pips=spread_pips,
            commission_pips=commission_pips,
            safety_buffer_pips=safety_buffer_pips
        )
        assert above_sl == 2000.20

    def test_sell_dynamic_breakeven_trigger_and_offset(self):
        entry = 2000.0
        initial_sl = 2010.0  # 10.0 risk distance -> 1.0R favorable excursion = 1990.0
        pip_size = 0.10
        spread_pips = 1.0
        commission_pips = 0.5
        safety_buffer_pips = 0.5
        # Total offset = 0.20

        # Sub-1.0R: current_price = 1992.0 (+0.8R)
        sub_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="SELL",
            entry=entry,
            initial_sl=initial_sl,
            current_price=1992.0,
            pip_size=pip_size,
            spread_pips=spread_pips,
            commission_pips=commission_pips,
            safety_buffer_pips=safety_buffer_pips
        )
        assert sub_sl is None

        # At +1.0R: current_price = 1990.0
        at_sl = DeterministicRiskGuard.evaluate_breakeven_trigger(
            side="SELL",
            entry=entry,
            initial_sl=initial_sl,
            current_price=1990.0,
            pip_size=pip_size,
            spread_pips=spread_pips,
            commission_pips=commission_pips,
            safety_buffer_pips=safety_buffer_pips
        )
        assert at_sl is not None
        assert at_sl == 1999.80  # entry - 0.20 offset
        assert at_sl < entry, "New SL on SELL must be locked strictly below entry to cover fees"

    def test_risk_kernel_dynamic_breakeven_evaluator(self):
        kernel = DeterministicRiskKernel()
        # Sub-1.0R
        res_sub = kernel.evaluate_dynamic_breakeven(current_gain_r=0.9, entry_price=2650.0)
        assert res_sub["trigger"] is False
        assert res_sub["action"] == "maintain_sl"
        assert res_sub["new_sl"] is None

        # Exactly 1.0R
        res_at = kernel.evaluate_dynamic_breakeven(current_gain_r=1.0, entry_price=2650.0)
        assert res_at["trigger"] is True
        assert res_at["action"] == "lock_sl_to_entry"
        assert res_at["new_sl"] == 2650.0

        # Super-1.0R
        res_super = kernel.evaluate_dynamic_breakeven(current_gain_r=1.8, entry_price=2650.0)
        assert res_super["trigger"] is True
        assert res_super["new_sl"] == 2650.0

    def test_admitted_order_attaches_armed_dynamic_breakeven(self):
        kernel = DeterministicRiskKernel()
        order = {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2650.0,
            "sl": 2642.0,  # dist = 8.0
            "tp": 2672.0,  # dist = 22.0 -> R:R = 2.75
            "lot_size": 0.5,
            "confluence_score": 95.0,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        res = kernel.admit_order(order)
        assert res["allowed"] is True
        be = res["dynamic_breakeven"]
        assert be is not None
        assert be["status"] == "ARMED"
        assert be["threshold_r"] == 1.0
        # Trigger price for BUY is entry + sl_dist = 2650.0 + 8.0 = 2658.0
        assert be["breakeven_trigger_price"] == 2658.0
        assert be["breakeven_lock_sl"] == 2650.0
        assert be["action_on_trigger"] == "lock_sl_to_entry"
        assert be["zero_drawdown_guaranteed"] is True


# ==============================================================================
# 4. News Blackout (15-Minute Buffer Enforcement)
# ==============================================================================
class TestNewsBlackoutEnforcement:
    """
    Empirically verifies 15-minute buffer enforcement around high-impact economic news.
      - Pre-news: Active within 15m prior to release
      - Post-news: Active within 15m following release
      - Clear: Inactive at > 15m away
    """

    def test_economic_news_blackout_manager_pre_and_post_buffers(self):
        mgr = EconomicNewsBlackoutManager(blackout_minutes_before=15, blackout_minutes_after=15, include_reference_events=False)
        base_time = datetime(2026, 9, 26, 14, 0, 0, tzinfo=timezone.utc)

        # Inject high-impact event at 14:00 UTC
        mgr.inject_event(
            title="Non-Farm Payrolls",
            currency="USD",
            event_time_utc=base_time,
            impact="HIGH"
        )

        # Test Case 1: T - 10 minutes (13:50 UTC) -> Inside PRE-news buffer
        status_1350 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time - timedelta(minutes=10))
        assert status_1350["blackout_active"] is True
        assert "PRE_NEWS_BLACKOUT" in status_1350["blackout_reason"]

        # Test Case 2: T - 14.9 minutes (13:45:06 UTC) -> Inside PRE-news buffer
        status_1345 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time - timedelta(minutes=14.9))
        assert status_1345["blackout_active"] is True

        # Test Case 3: T - 15.1 minutes (13:44:54 UTC) -> Outside buffer (Clear)
        status_1344 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time - timedelta(minutes=15.1))
        assert status_1344["blackout_active"] is False

        # Test Case 4: T + 5 minutes (14:05 UTC) -> Inside POST-news buffer (Cooloff)
        status_1405 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time + timedelta(minutes=5))
        assert status_1405["blackout_active"] is True
        assert "POST_NEWS_BLACKOUT" in status_1405["blackout_reason"]

        # Test Case 5: T + 14.9 minutes (14:14:54 UTC) -> Inside POST-news buffer
        status_1414 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time + timedelta(minutes=14.9))
        assert status_1414["blackout_active"] is True

        # Test Case 6: T + 15.1 minutes (14:15:06 UTC) -> Outside buffer (Clear)
        status_1415 = mgr.evaluate_blackout_status(symbol="EURUSD", now=base_time + timedelta(minutes=15.1))
        assert status_1415["blackout_active"] is False

    def test_admission_kernel_gate5_blocks_when_news_blackout_active(self):
        kernel = DeterministicRiskKernel()
        res = kernel.evaluate_admission(
            symbol="EURUSD",
            confluence_score=95.0,
            proposed_risk_pct=0.50,
            proposed_risk_usd=500.0,
            rr_ratio=2.50,
            news_lockout_active=True,
            account_id="40000294403"
        )
        assert res["allowed"] is False
        assert any("15-Minute High-Impact News Lockout Active" in b for b in res["blockers"])

    def test_custom_strategy_deterministic_guard_news_check(self):
        # 10 minutes away -> VETO
        is_active, reason = DeterministicRiskGuard.check_news_blackout(minutes_to_high_impact_news=10.0)
        assert is_active is True
        assert "VETO_NEWS_BLACKOUT" in reason

        # 15.0 minutes away -> VETO
        is_active, reason = DeterministicRiskGuard.check_news_blackout(minutes_to_high_impact_news=15.0)
        assert is_active is True

        # 15.1 minutes away -> Clear
        is_active, reason = DeterministicRiskGuard.check_news_blackout(minutes_to_high_impact_news=15.1)
        assert is_active is False
        assert "Market clear" in reason


# ==============================================================================
# 5. Quadratic Voting Math (Edge Cases: credits=0, 1, 25, 100)
# ==============================================================================
class TestQuadraticVotingMath:
    """
    Empirically verifies Quadratic Voting formula W = sqrt(credits_spent):
      - Pure math:
        credits=0 -> weight=0
        credits=1 -> weight=1
        credits=25 -> weight=5
        credits=100 -> weight=10
      - Engine API:
        credits=0 -> rejected (requires positive integer >= 1)
        credits=1 -> weight=1.0
        credits=25 -> weight=5.0
        credits=100 -> weight=10.0
      - FastAPI route validation:
        credits_spent=0 -> HTTP 422 Unprocessable Entity (Field ge=1)
    """

    @pytest.mark.parametrize("credits_spent, expected_weight", [
        (0, 0.0),
        (1, 1.0),
        (4, 2.0),
        (9, 3.0),
        (16, 4.0),
        (25, 5.0),
        (36, 6.0),
        (49, 7.0),
        (64, 8.0),
        (81, 9.0),
        (100, 10.0),
    ])
    def test_pure_quadratic_voting_formula(self, credits_spent, expected_weight):
        weight = math.sqrt(credits_spent)
        assert weight == expected_weight

    def test_civilization_engine_quadratic_voting_weights(self):
        engine = get_civilization_engine()
        proposals = engine.list_proposals()
        assert len(proposals) > 0
        prop_id = proposals[0]["proposal_id"]

        # credits = 1 -> weight = 1.0
        r1 = engine.cast_quadratic_vote(prop_id, "voter_emp_1", 1, "FOR")
        assert r1["ok"] is True
        assert r1["weight"] == 1.0

        # credits = 25 -> weight = 5.0
        r25 = engine.cast_quadratic_vote(prop_id, "voter_emp_25", 25, "FOR")
        assert r25["ok"] is True
        assert r25["weight"] == 5.0

        # credits = 100 -> weight = 10.0
        r100 = engine.cast_quadratic_vote(prop_id, "voter_emp_100", 100, "FOR")
        assert r100["ok"] is True
        assert r100["weight"] == 10.0

    def test_civilization_engine_rejects_credits_zero_and_negative(self):
        engine = get_civilization_engine()
        proposals = engine.list_proposals()
        prop_id = proposals[0]["proposal_id"]

        # credits = 0 -> Must be rejected with controlled error message
        r0 = engine.cast_quadratic_vote(prop_id, "voter_emp_0", 0, "FOR")
        assert r0["ok"] is False
        assert "positive integer >= 1" in r0["error"]

        # credits = -10 -> Must be rejected
        r_neg = engine.cast_quadratic_vote(prop_id, "voter_emp_neg", -10, "FOR")
        assert r_neg["ok"] is False
        assert "positive integer >= 1" in r_neg["error"]

    def test_api_quadratic_vote_validation_rejects_zero_credits(self, client):
        # The API schema enforces Field(..., ge=1)
        resp = client.post("/api/gaigs/democracy/quadratic-vote", json={
            "proposal_id": "GAIGS-PROP-001",
            "voter_id": "challenger_tester",
            "credits_spent": 0,
            "choice": "FOR"
        })
        # Must return 422 Unprocessable Entity
        assert resp.status_code == 422


# ==============================================================================
# 6. Spending Ledger Array Safety (/api/gaigs/transparency/spending)
# ==============================================================================
class TestSpendingLedgerArraySafety:
    """
    Confirms that /api/gaigs/transparency/spending returns a true JSON list for 'records'
    so that frontend `.map()` never crashes.
    """

    def test_spending_endpoint_returns_json_list_records(self, client):
        resp = client.get("/api/gaigs/transparency/spending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "records" in data

        records = data["records"]
        # Must be a true list
        assert isinstance(records, list), f"Expected list but got {type(records)}"

        # Verify JavaScript .map() safety: iteration over every item does not raise
        mapped_ids = [r.get("id") or r.get("tx_hash") for r in records]
        assert isinstance(mapped_ids, list)
        assert len(mapped_ids) == len(records)

    def test_spending_records_have_dual_key_compatibility(self, client):
        resp = client.get("/api/gaigs/transparency/spending")
        assert resp.status_code == 200
        records = resp.json()["records"]

        for rec in records:
            # Dual keys guarantee both legacy and upgraded frontends do not crash
            assert "id" in rec and "tx_hash" in rec
            assert "category" in rec and "department" in rec
            assert "vendor" in rec and "recipient" in rec
            assert "amount" in rec and "amount_usd" in rec
            assert isinstance(rec["amount_usd"], (int, float))
            assert rec["amount_usd"] >= 0

    def test_empty_ledger_still_returns_empty_list(self):
        engine = get_civilization_engine()
        records = engine.get_spending_records()
        assert isinstance(records, list)
        # Even if empty, it is an empty list [] which allows .map() to return []
        mapped = list(map(lambda r: r.get("id"), records))
        assert isinstance(mapped, list)
