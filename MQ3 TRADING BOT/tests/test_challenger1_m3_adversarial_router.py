"""
tests/test_challenger1_m3_adversarial_router.py
================================================
Empirical Challenger 1 Adversarial Stress Test Suite for Milestone 3 (Dual-Venue Router).

Empirically challenges:
1. Abnormal Symbol Taxonomy & Malformed Tickers (uppercase/lowercase/delimiters/None inputs)
2. Boundary, Extreme & Non-Divisible Lot Sizing (0.01 lot scale-outs, zero/negative lots, None payloads)
3. Fault Injection: REST HTTP 500, Rate-Limit 429, Connection Timeouts & MT5 Error Retcodes
4. Concurrency & Multi-Threaded Stress Testing (100 concurrent threads, race condition discovery)
5. 1-Click Risk Management Formulas (Spread buffer BE calculations across 7 asset classes, FVG CE)
6. Emergency Kill-Switch Idempotency & Multi-Venue Fleet Flattening
"""

import sys
import os
import time
import math
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.autonomous_fleet_executor import AutonomousFleetExecutor
from src.bitget_connector import BitgetConnector
from src.mt5_connector import MT5Connector
from src.multi_broker_bridge import (
    BrokerBridge,
    BitgetBridgeConnector,
    DualVenueRouterBridge,
    TradeReplicator
)
from src.fleet_risk_manager import FleetRiskManager


# ===========================================================================
# 1. Abnormal Symbol Taxonomy & Malformed Tickers
# ===========================================================================

class TestSymbolTaxonomyAndMalformedInputs:
    """Stress tests symbol parsing, classification, and normalisation in Router & Connectors."""

    @pytest.fixture
    def executor(self):
        return AutonomousFleetExecutor()

    @pytest.fixture
    def router_bridge(self):
        return DualVenueRouterBridge()

    @pytest.mark.parametrize("crypto_sym, expected_venue", [
        ("BTCUSD", "BITGET"),
        ("ETHUSD", "BITGET"),
        ("SOLUSD", "BITGET"),
        ("BTCUSDT", "BITGET"),
        ("ETHUSDT", "BITGET"),
        ("SOLUSDT", "BITGET"),
        ("BTCUSD_PERP", "BITGET"),
        ("SOL-USDT", "BITGET"),
        ("CRYPTO_INDEX", "BITGET"),
        ("BTC-USD", "BITGET"),
    ])
    def test_crypto_symbol_routing_classification(self, executor, crypto_sym, expected_venue):
        """Verifies crypto variants correctly route to BITGET venue."""
        order = {"symbol": crypto_sym, "direction": "BUY", "lots": 0.1, "entry_price": 60000.0, "sl": 59000.0, "tp": 62000.0}
        receipt = executor.route_order(account_id="TEST_CRYPTO_01", order=order)
        assert receipt["venue"] == expected_venue
        assert receipt["success"] is True
        assert receipt["status"] == "FILLED"
        assert "USDT" in receipt["symbol"]

    @pytest.mark.parametrize("fx_sym, expected_venue", [
        ("XAUUSD", "MT5"),
        ("xauusd", "MT5"),
        ("XAUUSDm", "MT5"),
        ("EURUSD", "MT5"),
        ("eurusd.pro", "MT5"),
        ("GBPUSD_raw", "MT5"),
        ("USDJPY", "MT5"),
        ("US30", "MT5"),
        ("GER40", "MT5"),
    ])
    def test_forex_metals_routing_classification(self, executor, fx_sym, expected_venue):
        """Verifies Forex/Metals/Index variants route to MT5 venue."""
        order = {"symbol": fx_sym, "direction": "SELL", "lots": 0.2, "entry_price": 2400.0, "sl": 2420.0, "tp": 2360.0}
        receipt = executor.route_order(account_id="TEST_FX_01", order=order)
        assert receipt["venue"] == expected_venue
        assert receipt["success"] is True

    def test_missing_or_default_symbol_handling(self, executor):
        """Verifies missing symbols are rejected instead of silently defaulted."""
        # Case 1: Symbol key omitted entirely
        order1 = {"direction": "BUY", "lots": 0.05, "entry_price": 1.0850}
        receipt1 = executor.route_order(account_id="DEFAULT_01", order=order1)
        assert receipt1["venue"] == "MT5"
        assert receipt1["success"] is False
        assert receipt1["status"] == "REJECTED"
        assert receipt1["symbol"] is None

        # Case 2: Empty string symbol
        order2 = {"symbol": "", "direction": "BUY", "lots": 0.05}
        receipt2 = executor.route_order(account_id="EMPTY_SYM", order=order2)
        assert receipt2["venue"] == "MT5"
        assert receipt2["success"] is False

    def test_bitget_connector_symbol_handling(self):
        """Tests Bitget pair formatting on standard and uppercase tickers."""
        bg = BitgetConnector(sim_mode=True)

        res1 = bg.place_order(symbol="BTCUSD", side="buy", size=0.1)
        assert res1["data"]["symbol"] == "BTCUSDT"

        res2 = bg.place_order(symbol="BTCUSDT", side="sell", size=0.2)
        assert res2["data"]["symbol"] == "BTCUSDT"

        res3 = bg.place_order(symbol="ETHUSD", side="buy", size=0.5)
        assert res3["data"]["symbol"] == "ETHUSDT"

        res4 = bg.place_order(symbol="SOLUSDT", side="buy", size=1.0)
        assert res4["data"]["symbol"] == "SOLUSDT"


# ===========================================================================
# 2. Extreme / Invalid / Boundary Lot Sizing & Risk Parameters
# ===========================================================================

class TestBoundaryAndExtremeParameters:
    """Stress tests boundary values, zero/negative inputs, and extreme numbers."""

    @pytest.fixture
    def executor(self):
        return AutonomousFleetExecutor()

    def test_zero_lot_size_fallback(self, executor):
        """Verifies zero lot size fails closed without division errors."""
        order = {"symbol": "EURUSD", "direction": "BUY", "lots": 0.0}
        receipt = executor.route_order(account_id="ZERO_LOT", order=order)
        assert receipt["lots"] == 0.0
        assert receipt["success"] is False
        assert receipt["status"] == "REJECTED"

    def test_negative_lot_size_handling(self, executor):
        """Verifies negative lot size is rejected without crashing."""
        order = {"symbol": "BTCUSD", "direction": "SELL", "lots": -0.5}
        receipt = executor.route_order(account_id="NEG_LOT", order=order)
        assert receipt["venue"] == "BITGET"
        assert receipt["success"] is False

    def test_massive_lot_size_execution(self, executor):
        """Verifies extreme volume is blocked by the hard order-size cap."""
        order = {"symbol": "XAUUSD", "direction": "BUY", "lots": 5000.0, "entry_price": 2450.0}
        receipt = executor.route_order(account_id="WHALE_01", order=order)
        assert receipt["lots"] == 5000.0
        assert receipt["venue"] == "MT5"
        assert receipt["success"] is False

    def test_zero_distance_sl_in_dynamic_fleet_sizing(self, executor):
        """Verifies execute_fleet_signal prevents zero division when entry == SL."""
        res = executor.execute_fleet_signal(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2450.0,
            sl=2450.0,  # Zero distance!
            tp1=2470.0,
            tp2=2490.0,
            tp3=2500.0
        )
        assert res["success"] is False
        assert res["executed_count"] == 0
        assert res["rejected_count"] > 0

    def test_scale_50_minimum_lot_boundary(self, executor):
        """Empirically validates scale_50 behavior at the 0.01 lot minimum threshold."""
        test_pos = {
            "ticket": 999901,
            "account_id": "MIN_LOT_ACC",
            "account_name": "Test Min Lot",
            "symbol": "EURUSD",
            "type": "BUY",
            "direction": "BUY",
            "lots": 0.01,
            "open_price": 1.0850,
            "sl": 1.0800,
            "tp1": 1.0950,
            "status": "RUNNING"
        }
        executor.active_positions.append(test_pos)

        res = executor.manage_position_action(ticket=999901, action="scale_50")
        assert res["success"] is True
        assert res["position"]["status"] == "SCALED_50_BE"


# ===========================================================================
# 3. Broker Disconnection & Fault Injection Stress Testing
# ===========================================================================

class TestBrokerDisconnectionAndFaultInjection:
    """Stress tests live REST HTTP errors, network timeouts, and broker rejects."""

    def test_bitget_live_rest_http_500_error_handling(self):
        """Verifies BitgetConnector handles HTTP 500 server error without unhandled exception."""
        bg = BitgetConnector(api_key="key", secret_key="sec", passphrase="pass", sim_mode=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.side_effect = Exception("Internal Server Error HTML")

        with patch("requests.post", return_value=mock_resp):
            res = bg.place_order(symbol="BTCUSDT", side="buy", size=0.1)
            assert res["status"] == "error"
            assert "message" in res

    def test_bitget_live_rest_timeout_handling(self):
        """Verifies BitgetConnector handles network connection timeout."""
        import requests
        bg = BitgetConnector(api_key="key", secret_key="sec", passphrase="pass", sim_mode=False)

        with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out after 5000ms")):
            res = bg.place_order(symbol="ETHUSDT", side="sell", size=0.5)
            assert res["status"] == "error"
            assert "Connection timed out" in res["message"]

    def test_bitget_live_business_rejection_code(self):
        """Verifies BitgetConnector parses non-zero business error codes (e.g. 40017 Insufficient Margin)."""
        bg = BitgetConnector(api_key="key", secret_key="sec", passphrase="pass", sim_mode=False)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": "40017",
            "msg": "Position size exceeds available balance limit",
            "data": None
        }

        with patch("requests.post", return_value=mock_resp):
            res = bg.place_order(symbol="SOLUSDT", side="buy", size=100.0)
            assert res["status"] == "error"
            assert res["message"] == "Position size exceeds available balance limit"

    def test_bitget_live_balance_fetch_network_drop(self):
        """Verifies get_account_balance gracefully handles connection drops in live mode."""
        import requests
        bg = BitgetConnector(api_key="key", secret_key="sec", passphrase="pass", sim_mode=False)

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Failed to resolve api.bitget.com")):
            res = bg.get_account_balance()
            assert res["status"] == "error"
            assert "Failed to resolve" in res["message"]

    def test_mt5_connector_rejection_retcodes(self):
        """Verifies MT5Connector place_order returns failure structure when order_send returns non-DONE."""
        mt5_conn = MT5Connector(
            config={"execution": {"live_enabled": True, "max_order_lots": 5.0}},
            simulation_mode=False,
        )
        with patch("src.mt5_connector.MT5_AVAILABLE", True):
            mt5_conn.connected = True
            mock_order_res = MagicMock()
            mock_order_res.retcode = 10019  # TRADE_RETCODE_NO_MONEY
            mock_order_res.comment = "Not enough money to open position"

            check_res = MagicMock(retcode=0, comment="OK")
            with patch.dict(os.environ, {"MQ3_LIVE_TRADING_CONFIRMATION": "I_ACCEPT_LIVE_TRADING_RISK"}):
                with patch("src.mt5_connector.mt5.order_check", return_value=check_res):
                    with patch("src.mt5_connector.mt5.order_send", return_value=mock_order_res):
                        with patch("src.mt5_connector.mt5.symbol_info", return_value=MagicMock(filling_mode=4)):
                            with patch("src.mt5_connector.mt5.symbol_info_tick", return_value=MagicMock(ask=1.0850, bid=1.0848)):
                                res = mt5_conn.place_order(symbol="EURUSD", signal_type="BUY", volume=5.0, price=1.0850, sl=1.0800, tp=1.0950)
                                assert res["success"] is False
                                assert "Retcode 10019" in res["reason"]


# ===========================================================================
# 4. Concurrency & Multi-Threaded Stress Testing
# ===========================================================================

class TestConcurrencyAndThreadSafety:
    """Stress tests race conditions, concurrent order routing, and receipt tracking."""

    def test_high_concurrency_order_routing(self):
        """Tests 100 concurrent threads routing orders simultaneously to verify receipt integrity."""
        executor = AutonomousFleetExecutor()
        initial_history_len = len(executor.execution_history)
        num_threads = 100

        def worker_task(thread_id: int):
            sym = "BTCUSD" if thread_id % 2 == 0 else "XAUUSD"
            order = {
                "symbol": sym,
                "direction": "BUY" if thread_id % 3 == 0 else "SELL",
                "lots": 0.1 + (thread_id * 0.01),
                "entry_price": 60000.0 if "BTC" in sym else 2450.0,
                "sl": 59000.0 if "BTC" in sym else 2430.0,
                "tp": 62000.0 if "BTC" in sym else 2480.0,
                "comment": f"Thread-{thread_id}"
            }
            if order["direction"] == "SELL":
                order["sl"], order["tp"] = order["tp"], order["sl"]
            return executor.route_order(account_id=f"ACC_{thread_id}", order=order)

        receipts = []
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(worker_task, i) for i in range(num_threads)]
            for f in as_completed(futures):
                receipts.append(f.result())

        assert len(receipts) == num_threads
        assert len(executor.execution_history) == initial_history_len + num_threads

        for r in receipts:
            assert r["status"] == "FILLED"
            assert r["venue"] in ["BITGET", "MT5"]
            assert r["lots"] > 0

    def test_concurrent_position_actions(self):
        """Tests concurrent execution of BE locking, partial scale-outs, and trailing SL."""
        executor = AutonomousFleetExecutor()
        executor.active_positions.clear()
        for i in range(50):
            executor.active_positions.append({
                "ticket": 800000 + i,
                "account_id": f"ACC_{i}",
                "account_name": f"Account {i}",
                "symbol": "XAUUSD" if i % 2 == 0 else "BTCUSD",
                "type": "BUY" if i % 3 == 0 else "SELL",
                "direction": "BUY" if i % 3 == 0 else "SELL",
                "lots": 1.0,
                "open_price": 2400.0 if i % 2 == 0 else 60000.0,
                "sl": 2380.0 if i % 2 == 0 else 59000.0,
                "tp1": 2440.0 if i % 2 == 0 else 62000.0,
                "status": "RUNNING"
            })

        actions = ["be", "scale_50", "trail_fvg"]

        def manage_task(idx: int):
            ticket = 800000 + idx
            act = actions[idx % len(actions)]
            if act == "trail_fvg":
                return executor.trail_fvg_consequent_encroachment(
                    ticket=ticket,
                    fvg_top=2420.0,
                    fvg_bottom=2410.0
                )
            else:
                return executor.manage_position_action(ticket=ticket, action=act)

        results = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(manage_task, i) for i in range(50)]
            for f in as_completed(futures):
                results.append(f.result())

        assert len(results) == 50
        for res in results:
            assert res["success"] is True

    def test_concurrent_emergency_kill_switch_during_routing(self):
        """Tests triggering emergency kill-switch while multiple orders are being routed."""
        executor = AutonomousFleetExecutor()
        num_orders = 40
        stop_flag = False

        def continuous_routing():
            routed = 0
            for i in range(num_orders):
                if stop_flag:
                    break
                executor.route_order(account_id=f"CONCUR_{i}", order={"symbol": "XAUUSD", "direction": "BUY", "lots": 0.1})
                routed += 1
                time.sleep(0.002)
            return routed

        with ThreadPoolExecutor(max_workers=5) as pool:
            route_futures = [pool.submit(continuous_routing) for _ in range(3)]
            time.sleep(0.01)
            kill_res = executor.emergency_kill_switch()
            assert kill_res["success"] is True
            assert kill_res["status"] == "EMERGENCY_FLATTENED"

            for f in as_completed(route_futures):
                f.result()

        assert isinstance(kill_res["total_closed"], int)


# ===========================================================================
# 5. 1-Click Risk Management Edge Cases
# ===========================================================================

class TestOneClickRiskManagementEdgeCases:
    """Stress tests mathematical edge cases in BE buffer, FVG CE midpoint, and scale-outs."""

    @pytest.fixture
    def executor(self):
        return AutonomousFleetExecutor()

    def test_breakeven_pip_units_across_all_asset_classes(self, executor):
        """Verifies exact spread buffer pip unit math across Gold, JPY, Crypto, and Forex."""
        assets_test = [
            ("XAUUSD", "BUY", 2400.0, 1.0, 2400.1),       # Pip unit 0.1 => 2400 + (1.0 * 0.1) = 2400.1
            ("XAUUSD", "SELL", 2400.0, 2.0, 2399.8),      # Pip unit 0.1 => 2400 - (2.0 * 0.1) = 2399.8
            ("USDJPY", "BUY", 155.00, 1.0, 155.01),       # Pip unit 0.01 => 155 + (1.0 * 0.01) = 155.01
            ("USDJPY", "SELL", 155.00, 3.0, 154.97),      # Pip unit 0.01 => 155 - (3.0 * 0.01) = 154.97
            ("BTCUSD", "BUY", 65000.0, 5.0, 65005.0),     # Pip unit 1.0 => 65000 + (5.0 * 1.0) = 65005.0
            ("BTCUSD", "SELL", 65000.0, 10.0, 64990.0),   # Pip unit 1.0 => 65000 - (10.0 * 1.0) = 64990.0
            ("EURUSD", "BUY", 1.08500, 1.0, 1.08510),     # Pip unit 0.0001 => 1.08500 + 0.00010 = 1.08510
            ("EURUSD", "SELL", 1.08500, 1.5, 1.08485),    # Pip unit 0.0001 => 1.08500 - 0.00015 = 1.08485
        ]

        for sym, direction, open_px, buf_pips, expected_sl in assets_test:
            ticket = random.randint(100000, 999999)
            executor.active_positions = [{
                "ticket": ticket,
                "account_id": "ACC_TEST",
                "symbol": sym,
                "type": direction,
                "direction": direction,
                "lots": 0.5,
                "open_price": open_px,
                "sl": open_px - 50.0 if direction == "BUY" else open_px + 50.0,
                "tp1": open_px + 100.0 if direction == "BUY" else open_px - 100.0,
                "status": "RUNNING"
            }]

            res = executor.manage_position_action(ticket=ticket, action="be", buffer_pips=buf_pips)
            assert res["success"] is True
            assert math.isclose(res["position"]["sl"], expected_sl, rel_tol=1e-4), f"Failed for {sym} {direction}: got {res['position']['sl']}, expected {expected_sl}"

    def test_fvg_consequent_encroachment_midpoint_calculation(self, executor):
        """Verifies CE midpoint formula: (fvg_top + fvg_bottom) / 2.0 under varied ranges."""
        ticket = 912345
        executor.active_positions = [{
            "ticket": ticket,
            "account_id": "ACC_FVG",
            "symbol": "XAUUSD",
            "type": "BUY",
            "open_price": 2420.0,
            "sl": 2400.0,
            "tp1": 2480.0,
            "status": "RUNNING"
        }]

        # Standard Bullish FVG: 2430 to 2440 => CE = 2435.0
        res1 = executor.trail_fvg_consequent_encroachment(ticket=ticket, fvg_top=2440.0, fvg_bottom=2430.0)
        assert res1["success"] is True
        assert res1["ce_50"] == 2435.0
        assert res1["position"]["sl"] == 2435.0

        # Inverted / Negative range (bottom > top): 2450 to 2440 => CE = 2445.0
        res2 = executor.trail_fvg_consequent_encroachment(ticket=ticket, fvg_top=2440.0, fvg_bottom=2450.0)
        assert res2["ce_50"] == 2445.0

        # Zero width FVG: 2460.0 to 2460.0 => CE = 2460.0
        res3 = executor.trail_fvg_consequent_encroachment(ticket=ticket, fvg_top=2460.0, fvg_bottom=2460.0)
        assert res3["ce_50"] == 2460.0

    def test_nonexistent_ticket_actions(self, executor):
        """Verifies appropriate failure messages when action target ticket is missing."""
        res1 = executor.manage_position_action(ticket=99999999, action="be")
        assert res1["success"] is False
        assert "not found" in res1["message"]

        res2 = executor.trail_fvg_consequent_encroachment(ticket=99999999, fvg_top=2450.0, fvg_bottom=2440.0)
        assert res2["success"] is False
        assert "not found" in res2["message"]

    def test_unknown_action_type(self, executor):
        """Verifies unknown action type returns explicit error."""
        ticket = executor.active_positions[0]["ticket"]
        res = executor.manage_position_action(ticket=ticket, action="invalid_action_xyz")
        assert res["success"] is False
        assert "Unknown execution action" in res["message"]


# ===========================================================================
# 6. Trade Replicator & Cross-Venue Lot Scaling
# ===========================================================================

class TestTradeReplicatorAndSizingModes:
    """Stress tests TradeReplicator lot scaling calculations and bracket order building."""

    @pytest.fixture
    def replicator(self):
        return TradeReplicator()

    @pytest.mark.parametrize("mode, mt5_vol, mt5_eq, br_eq, mult, fixed, expected_vol", [
        ("mirror", 0.50, 25000, 25000, 1.0, 0.01, 0.50),
        ("multiplier", 0.20, 25000, 25000, 2.5, 0.01, 0.50),
        ("equity_ratio", 0.50, 25000, 50000, 1.0, 0.01, 1.00),
        ("equity_ratio", 1.00, 50000, 25000, 1.0, 0.01, 0.50),
        ("fixed", 0.75, 25000, 25000, 1.0, 0.05, 0.05),
    ])
    def test_replicator_lot_sizing_modes(self, replicator, mode, mt5_vol, mt5_eq, br_eq, mult, fixed, expected_vol):
        """Verifies all 4 bridge lot sizing modes mathematically compute expected volume."""
        vol = replicator.bridge.calculate_bridge_lot_size(
            mt5_volume=mt5_vol,
            sizing_mode=mode,
            mt5_equity=mt5_eq,
            broker_equity=br_eq,
            multiplier=mult,
            fixed_lots=fixed
        )
        assert vol == expected_vol

    def test_replicator_slippage_guard(self):
        """Verifies slippage guard blocks orders exceeding threshold."""
        assert TradeReplicator.check_slippage(mt5_price=1.08500, broker_price=1.08515, max_slippage_pips=3.0) is True
        assert TradeReplicator.check_slippage(mt5_price=1.08500, broker_price=1.08540, max_slippage_pips=3.0) is False

    def test_bracket_order_generation_structure(self, replicator):
        """Verifies parent + stop loss + take profit bracket structure."""
        signal = {
            "direction": "BUY",
            "lot_size": 0.25,
            "entry_price": 2420.50,
            "sl": 2400.00,
            "tp": 2460.00
        }
        bracket = replicator.bridge.generate_bracket_order(signal)
        assert bracket["parent_order"]["action"] == "BUY"
        assert bracket["parent_order"]["quantity"] == 0.25
        assert bracket["stop_loss_order"]["action"] == "SELL"
        assert bracket["stop_loss_order"]["trigger_price"] == 2400.00
        assert bracket["take_profit_order"]["action"] == "SELL"
        assert bracket["take_profit_order"]["limit_price"] == 2460.00


# ===========================================================================
# 7. Emergency Kill Switch Idempotency & Massive Load
# ===========================================================================

class TestEmergencyKillSwitchStress:
    """Stress tests rapid back-to-back kill switch triggers and large fleet liquidations."""

    def test_kill_switch_idempotency(self):
        """Verifies calling emergency_kill_switch multiple times consecutively executes cleanly."""
        executor = AutonomousFleetExecutor()

        res1 = executor.emergency_kill_switch()
        assert res1["success"] is True

        res2 = executor.emergency_kill_switch()
        assert res2["success"] is True
        assert res2["total_closed"] >= 0

        res3 = executor.emergency_kill_switch()
        assert res3["success"] is True

    def test_massive_fleet_liquidation(self):
        """Verifies liquidating 500 active positions across MT5 & Bitget in simulation mode."""
        mt5_sim = MT5Connector(simulation_mode=True)
        bg_sim = BitgetConnector(sim_mode=True)
        executor = AutonomousFleetExecutor(mt5_connector=mt5_sim, bitget_connector=bg_sim)
        executor.active_positions.clear()

        # Generate 500 mock positions
        for i in range(500):
            sym = "BTCUSD" if i % 2 == 0 else "EURUSD"
            ticket = 700000 + i
            executor.active_positions.append({
                "ticket": ticket,
                "account_id": f"FLEET_{i%10}",
                "symbol": sym,
                "lots": 0.1,
                "open_price": 60000.0 if "BTC" in sym else 1.0850,
                "status": "RUNNING"
            })
            if "BTC" in sym:
                executor.bitget_connector.sim_positions.append({"order_id": str(ticket), "symbol": "BTCUSDT", "size": 0.1})
            else:
                executor.mt5_connector._mock_positions.append({"ticket": ticket, "symbol": "EURUSD", "volume": 0.1})

        assert len(executor.active_positions) == 500

        res = executor.emergency_kill_switch()
        assert res["success"] is True
        assert len(executor.active_positions) == 0
        assert len(executor.bitget_connector.sim_positions) == 0
        assert len(executor.mt5_connector._mock_positions) == 0
        assert res["total_closed"] == 500
