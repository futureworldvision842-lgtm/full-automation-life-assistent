"""
test_websocket_adversarial_stress.py — Empirical Challenger Stress Suite for WebSocket Channels.

Adversarially tests:
1. High-Frequency Connection Churn (rapid connects, disconnects, concurrent bursts).
2. 20Hz Continuous Streaming Throughput & Latency across 7 symbols.
3. Frame Structure Integrity & Schema Validation for all message types.
4. Dynamic Subscription & Command Handling (subscribe, commands, voice intents, malformed inputs).
5. Dead Client Disconnect Resilience & Memory Bounding (zero unhandled exceptions, clean socket eviction).
"""

import os
import sys
import time
import asyncio
import pytest
from typing import List, Dict, Any
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.web_terminal_server import (
    app,
    terminal_state,
    ws_manager,
    voice_engine,
    ConnectionManager,
    realtime_streaming_worker
)


@pytest.fixture(autouse=True)
def clean_test_environment():
    """Resets server state and empties active connection sets before each test."""
    terminal_state.status = "RUNNING"
    terminal_state.simulation_mode = True
    terminal_state.balance = 25480.00
    terminal_state.equity = 25730.00
    terminal_state.daily_profit = 250.00
    terminal_state._seed_initial_positions()

    # Clear WS connections
    ws_manager.terminal_connections.clear()
    ws_manager.market_connections.clear()
    ws_manager.cockpit_connections.clear()
    ws_manager.worldmonitor_connections.clear()
    ws_manager.subscriptions.clear()
    yield
    # Cleanup after test
    ws_manager.terminal_connections.clear()
    ws_manager.market_connections.clear()
    ws_manager.cockpit_connections.clear()
    ws_manager.worldmonitor_connections.clear()
    ws_manager.subscriptions.clear()


# =====================================================================
# Mock Async WebSocket for Concurrency & Dead-Socket Stress Testing
# =====================================================================

class MockAsyncWebSocket:
    """High-performance mock WebSocket client for load & fault injection."""

    def __init__(self, should_fail: bool = False):
        self.accepted = False
        self.closed = False
        self.should_fail = should_fail
        self.sent_messages: List[Dict[str, Any]] = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: Dict[str, Any]):
        if self.should_fail or self.closed:
            raise RuntimeError("ConnectionResetError: Client socket aborted prematurely")
        self.sent_messages.append(data)

    async def receive_json(self) -> Dict[str, Any]:
        if self.should_fail or self.closed:
            raise RuntimeError("WebSocketDisconnect")
        return {"type": "ping"}

    async def receive_text(self) -> str:
        if self.should_fail or self.closed:
            raise RuntimeError("WebSocketDisconnect")
        return "ping"

    def close(self):
        self.closed = True


# =====================================================================
# 1. HIGH-FREQUENCY CONNECTION CHURN TESTS
# =====================================================================

def test_high_frequency_sequential_churn_all_channels():
    """
    Rapidly connects and disconnects 30 clients sequentially across all 4 channels.
    Verifies zero memory leaks and proper registration/deregistration.
    """
    channels = ["terminal", "market", "cockpit", "worldmonitor"]
    iterations = 30

    with TestClient(app) as client:
        for ch in channels:
            for _ in range(iterations):
                with client.websocket_connect(f"/ws/{ch}") as ws:
                    if ch == "terminal":
                        assert len(ws_manager.terminal_connections) == 1
                        assert len(ws_manager.subscriptions) == 1
                    elif ch == "market":
                        assert len(ws_manager.market_connections) == 1
                    elif ch == "cockpit":
                        assert len(ws_manager.cockpit_connections) == 1
                    elif ch == "worldmonitor":
                        assert len(ws_manager.worldmonitor_connections) == 1

                # Disconnect immediately after context exit
                if ch == "terminal":
                    assert len(ws_manager.terminal_connections) == 0
                    assert len(ws_manager.subscriptions) == 0
                elif ch == "market":
                    assert len(ws_manager.market_connections) == 0
                elif ch == "cockpit":
                    assert len(ws_manager.cockpit_connections) == 0
                elif ch == "worldmonitor":
                    assert len(ws_manager.worldmonitor_connections) == 0


@pytest.mark.asyncio
async def test_concurrent_high_load_client_burst():
    """
    Tests ConnectionManager under heavy load with 200 concurrent mock clients
    (50 per channel) receiving simultaneous broadcasts.
    """
    mgr = ConnectionManager()
    clients_terminal = [MockAsyncWebSocket() for _ in range(50)]
    clients_market = [MockAsyncWebSocket() for _ in range(50)]
    clients_cockpit = [MockAsyncWebSocket() for _ in range(50)]
    clients_wm = [MockAsyncWebSocket() for _ in range(50)]

    # Connect all 200 clients
    for ws in clients_terminal:
        await mgr.connect(ws, "terminal")
    for ws in clients_market:
        await mgr.connect(ws, "market")
    for ws in clients_cockpit:
        await mgr.connect(ws, "cockpit")
    for ws in clients_wm:
        await mgr.connect(ws, "worldmonitor")

    assert len(mgr.terminal_connections) == 50
    assert len(mgr.market_connections) == 50
    assert len(mgr.cockpit_connections) == 50
    assert len(mgr.worldmonitor_connections) == 50
    assert len(mgr.subscriptions) == 50

    # Broadcast to all channels
    msg = {"type": "burst_test", "timestamp": int(time.time()), "data": "payload"}
    await mgr.broadcast_channel("terminal", msg)
    await mgr.broadcast_channel("market", msg)
    await mgr.broadcast_channel("cockpit", msg)
    await mgr.broadcast_channel("worldmonitor", msg)

    for ws in clients_terminal + clients_market + clients_cockpit + clients_wm:
        assert len(ws.sent_messages) == 1
        assert ws.sent_messages[0]["type"] == "burst_test"

    # Disconnect all
    for ws in clients_terminal:
        mgr.disconnect(ws, "terminal")
    for ws in clients_market:
        mgr.disconnect(ws, "market")
    for ws in clients_cockpit:
        mgr.disconnect(ws, "cockpit")
    for ws in clients_wm:
        mgr.disconnect(ws, "worldmonitor")

    assert len(mgr.terminal_connections) == 0
    assert len(mgr.market_connections) == 0
    assert len(mgr.cockpit_connections) == 0
    assert len(mgr.worldmonitor_connections) == 0
    assert len(mgr.subscriptions) == 0


# =====================================================================
# 2. FRAME STRUCTURE INTEGRITY & SCHEMA VALIDATION
# =====================================================================

def test_frame_schema_integrity_terminal_channel():
    """
    Validates complete mathematical and structural schema of all message types on /ws/terminal.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            frames_by_type: Dict[str, Dict[str, Any]] = {}

            # Drain frames until we have captured all key frame types
            for _ in range(12):
                frame = ws.receive_json()
                t = frame.get("type")
                if t and t not in frames_by_type:
                    frames_by_type[t] = frame
                if len(frames_by_type) >= 4:
                    break

            assert "smc_update" in frames_by_type
            assert "cockpit_metrics" in frames_by_type
            assert "positions_update" in frames_by_type

            # Verify SMC Update Structure
            smc_frame = frames_by_type["smc_update"]
            assert smc_frame["symbol"] == "XAUUSD"
            data = smc_frame["data"]
            assert "fvgs" in data and isinstance(data["fvgs"], list)
            assert "order_blocks" in data and isinstance(data["order_blocks"], list)
            assert "ote" in data and isinstance(data["ote"], dict)
            assert "killzones" in data and len(data["killzones"]) == 3
            for fvg in data["fvgs"]:
                assert "top" in fvg and "bottom" in fvg and "ce" in fvg
                assert fvg["top"] >= fvg["bottom"]
                assert pytest.approx(fvg["ce"], rel=1e-3) == (fvg["top"] + fvg["bottom"]) / 2.0

            # Verify Cockpit Metrics Structure
            cockpit_frame = frames_by_type["cockpit_metrics"]
            c_data = cockpit_frame["data"]
            assert c_data["balance"] > 0
            assert c_data["equity"] > 0
            assert c_data["var_99_usd"] > 0
            assert c_data["cvar_99_usd"] > c_data["var_99_usd"]  # CVaR > VaR property
            assert "hwm" in c_data and "trailing_floor" in c_data

            # Verify Positions Update Structure
            pos_frame = frames_by_type["positions_update"]
            assert "positions" in pos_frame
            assert isinstance(pos_frame["positions"], list)
            for p in pos_frame["positions"]:
                assert "ticket" in p
                assert "symbol" in p
                assert "type" in p
                assert "volume" in p
                assert "price_open" in p
                assert "sl" in p
                assert "tp" in p

            # Verify World Monitor Update Structure if present or query directly
            wm_frame = frames_by_type.get("world_monitor_update")
            if not wm_frame:
                wm_frame = {"type": "world_monitor_update", "data": terminal_state.get_world_monitor_data()}
            wm_data = wm_frame["data"]
            assert wm_data["status"] == "success"
            assert "DEFCON" in wm_data["global_threat_level"]
            assert len(wm_data["chokepoints"]) == 5
            for cp in wm_data["chokepoints"]:
                assert "name" in cp and "risk_level" in cp and "global_oil_pct" in cp


def test_market_depth_and_cvd_frame_structures():
    """
    Validates structural correctness of market_depth and cvd_update frames.
    """
    # 1. Test DOM generation
    dom = terminal_state.feed_manager.simulator.generate_depth("BTCUSD")
    assert dom["type"] == "market_depth"
    assert dom["symbol"] == "BTCUSD"
    assert "bids" in dom and len(dom["bids"]) == 5
    assert "asks" in dom and len(dom["asks"]) == 5
    assert "buyer_ratio" in dom and "seller_ratio" in dom
    assert pytest.approx(dom["buyer_ratio"] + dom["seller_ratio"], abs=0.5) == 100.0

    # 2. Test CVD generation
    cvd = terminal_state.feed_manager.get_cvd("ETHUSD", limit=50)
    assert cvd["symbol"] == "ETHUSD"
    assert "cvd_history" in cvd
    assert "current_ratio" in cvd
    assert "divergence" in cvd
    assert cvd["divergence"]["type"] in ["NONE", "BULLISH_ABSORPTION", "BEARISH_ABSORPTION"]


# =====================================================================
# 3. DYNAMIC SUBSCRIPTION & MULTI-SYMBOL SWITCHING TESTS (7 SYMBOLS)
# =====================================================================

@pytest.mark.parametrize("symbol", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"])
def test_dynamic_symbol_subscription_and_tick_filtering(symbol):
    """
    Subscribes to each of the 7 assets and verifies:
    1. Immediate smc_update for the new symbol.
    2. Continuous live ticks received match the subscribed symbol.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            # Drain initial frames
            for _ in range(4):
                ws.receive_json()

            # Subscribe to symbol
            ws.send_json({"type": "subscribe", "symbol": symbol, "timeframe": "M5"})

            # Receive smc_update for subscribed symbol
            res = ws.receive_json()
            while res.get("type") != "smc_update" or res.get("symbol") != symbol:
                res = ws.receive_json()

            assert res["type"] == "smc_update"
            assert res["symbol"] == symbol
            assert res["data"]["symbol"] == symbol
            assert res["data"]["timeframe"] == "M5"

            # Check that subsequent live ticks received are for the subscribed symbol
            found_tick = False
            for _ in range(10):
                frame = ws.receive_json()
                if frame.get("type") == "tick":
                    assert frame["symbol"] == symbol
                    assert frame["bid"] > 0
                    assert frame["ask"] >= frame["bid"]
                    assert frame["last"] > 0
                    found_tick = True
                    break

            assert found_tick is True


def test_rapid_subscription_switching_all_7_assets():
    """
    Rapidly switches subscriptions across all 7 assets on the same connection.
    Verifies subscription state remains accurate and consistent.
    """
    symbols = ["XAUUSD", "BTCUSD", "EURUSD", "ETHUSD", "GBPUSD", "SOLUSD", "USDJPY"]
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            # Drain initial frames
            for _ in range(4):
                ws.receive_json()

            for sym in symbols:
                ws.send_json({"type": "subscribe", "symbol": sym, "timeframe": "H1"})
                res = ws.receive_json()
                while res.get("type") != "smc_update" or res.get("symbol") != sym:
                    res = ws.receive_json()
                assert res["type"] == "smc_update"
                assert res["symbol"] == sym
                assert res["data"]["timeframe"] == "H1"


# =====================================================================
# 4. WEBSOCKET 1-CLICK COMMAND EXECUTION & VOICE INTENT TESTS
# =====================================================================

def test_websocket_1click_all_actions():
    """
    Tests all 1-click execution actions through WebSocket messages:
    scale_out, breakeven, modify_sltp, close_position, kill_switch.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            for _ in range(4):
                ws.receive_json()

            # 1. Scale Out
            ws.send_json({"type": "command", "action": "scale_out", "ticket": 100101, "ratio": 0.5})
            res = ws.receive_json()
            while res.get("type") not in ["command_result"]:
                res = ws.receive_json()
            assert res["action"] == "scale_out"
            assert res["result"]["success"] is True
            assert res["result"]["closed_volume"] == 0.25

            # 2. Breakeven
            ws.send_json({"type": "command", "action": "breakeven", "ticket": 100102, "buffer_pips": 2.0})
            res = ws.receive_json()
            while res.get("type") not in ["command_result"]:
                res = ws.receive_json()
            assert res["action"] == "breakeven"
            assert res["result"]["success"] is True

            # 3. Modify SL/TP
            ws.send_json({"type": "command", "action": "modify_sltp", "ticket": 100101, "sl": 2640.0, "tp": 2690.0})
            res = ws.receive_json()
            while res.get("type") not in ["command_result"]:
                res = ws.receive_json()
            assert res["action"] == "modify_sltp"
            assert res["result"]["success"] is True

            # 4. Close Position
            ws.send_json({"type": "command", "action": "close_position", "ticket": 100101})
            res = ws.receive_json()
            while res.get("type") not in ["command_result"]:
                res = ws.receive_json()
            assert res["action"] == "close_position"
            assert res["result"]["success"] is True

            # 5. Kill Switch
            ws.send_json({"type": "command", "action": "kill_switch"})
            res = ws.receive_json()
            while res.get("type") not in ["command_result"]:
                res = ws.receive_json()
            assert res["action"] == "kill_switch"
            assert res["result"]["success"] is True
            assert res["result"]["status"] == "EMERGENCY_LOCKED"


def test_websocket_voice_intent_execution():
    """
    Tests natural language voice intents over WebSocket channel.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            for _ in range(4):
                ws.receive_json()

            # Send voice command
            ws.send_json({
                "type": "voice_intent",
                "transcript": "Scale out 50% on Gold",
                "active_symbol": "XAUUSD"
            })
            res = ws.receive_json()
            while res.get("type") != "jarvis_event":
                res = ws.receive_json()

            assert res["type"] == "jarvis_event"
            assert res["intent"] == "SCALE_OUT_PARTIAL"
            assert "speech" in res
            assert res["data"]["success"] is True


# =====================================================================
# 5. RESILIENCE TO MALFORMED INPUTS & DEAD SOCKETS
# =====================================================================

def test_websocket_malformed_message_handling():
    """
    Sends invalid types, missing parameters, and empty commands to verify no crash occurs.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            for _ in range(4):
                ws.receive_json()

            # Empty dictionary
            ws.send_json({})

            # Unknown type
            ws.send_json({"type": "UNKNOWN_GARBAGE_TYPE", "payload": 12345})

            # Incomplete command
            ws.send_json({"type": "command", "action": "scale_out"})

            # Incomplete voice
            ws.send_json({"type": "voice_intent"})

            # Connection remains intact and responsive
            ws.send_json({"type": "subscribe", "symbol": "EURUSD", "timeframe": "M15"})
            res = ws.receive_json()
            while res.get("type") != "smc_update" or res.get("symbol") != "EURUSD":
                res = ws.receive_json()
            assert res["symbol"] == "EURUSD"


@pytest.mark.asyncio
async def test_dead_socket_pruning_and_fault_tolerance():
    """
    Injects 30 faulty sockets that crash on send alongside 30 healthy sockets.
    Verifies that broadcast automatically purges faulty sockets without raising exceptions.
    """
    mgr = ConnectionManager()
    healthy_clients = [MockAsyncWebSocket(should_fail=False) for _ in range(30)]
    faulty_clients = [MockAsyncWebSocket(should_fail=True) for _ in range(30)]

    for ws in healthy_clients:
        await mgr.connect(ws, "terminal")
        mgr.set_subscription(ws, "XAUUSD")
    for ws in faulty_clients:
        await mgr.connect(ws, "terminal")
        mgr.set_subscription(ws, "XAUUSD")

    assert len(mgr.terminal_connections) == 60
    assert len(mgr.subscriptions) == 60

    # Broadcast terminal ticks
    ticks = {
        "XAUUSD": {"bid": 2650.0, "ask": 2650.5, "last": 2650.2, "time": int(time.time()), "volume": 10}
    }
    await mgr.broadcast_terminal_ticks(ticks)

    # All faulty sockets must be evicted; healthy sockets must remain
    assert len(mgr.terminal_connections) == 30
    assert len(mgr.subscriptions) == 30
    for ws in healthy_clients:
        assert ws in mgr.terminal_connections
        assert len(ws.sent_messages) == 1

    # Broadcast general channel message
    await mgr.broadcast_channel("terminal", {"type": "heartbeat"})
    for ws in healthy_clients:
        assert len(ws.sent_messages) == 2


# =====================================================================
# 6. 20Hz CONTINUOUS STREAMING THROUGHPUT & LATENCY BENCHMARK
# =====================================================================

@pytest.mark.asyncio
async def test_20hz_worker_execution_cycles_and_timing():
    """
    Runs 50 iterations of the 20Hz streaming worker mechanics across all 7 assets with concurrent subscribers.
    Validates that each cycle executes well within the 50ms budget (sub-100ms latency requirement).
    """
    mgr = ConnectionManager()
    subscribers = {}
    for sym in terminal_state.feed_manager.SYMBOLS:
        ws = MockAsyncWebSocket()
        await mgr.connect(ws, "terminal")
        mgr.set_subscription(ws, sym, "M15")
        subscribers[sym] = ws

    latencies = []
    iterations = 50

    for _ in range(iterations):
        t0 = time.perf_counter()

        # Step 1: Simulate tick updates for 7 assets
        ticks = {}
        for sym in terminal_state.feed_manager.SYMBOLS:
            tick = terminal_state.feed_manager.simulator.next_tick(sym)
            ticks[sym] = tick
            terminal_state.feed_manager.process_tick(tick)

        # Step 2: Update MTM positions
        terminal_state.update_positions_mtm()

        # Step 3: Broadcast ticks to specific subscribed clients
        await mgr.broadcast_terminal_ticks(ticks)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    # Validate that every subscriber received ticks
    for sym, ws in subscribers.items():
        assert len(ws.sent_messages) == iterations
        assert all(m["symbol"] == sym for m in ws.sent_messages)

    # Latency assertions: 20Hz cycle must complete in < 25ms
    assert avg_latency < 25.0, f"Average cycle latency {avg_latency:.2f}ms exceeds 25ms threshold"
    assert p95_latency < 40.0, f"P95 cycle latency {p95_latency:.2f}ms exceeds 40ms threshold"
    assert max_latency < 50.0, f"Max cycle latency {max_latency:.2f}ms exceeds 50ms budget"
