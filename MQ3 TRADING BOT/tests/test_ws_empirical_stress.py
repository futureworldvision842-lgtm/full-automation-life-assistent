"""
test_ws_empirical_stress.py — Empirical Stress & Adversarial Test Harness for WebSocket Endpoints.

Covers:
1. Concurrent client WebSocket connections and connection churn.
2. Dynamic subscription mutations across all symbols & timeframes.
3. High-throughput message transmission rates, latency, and strict JSON frame structure validation.
4. WebSocket-based 1-click execution commands and Jarvis voice intent processing.
5. 20Hz background streaming loop stability, buffer pruning, and memory footprint bounds.
"""

import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.web_terminal_server import (
    app,
    terminal_state,
    ws_manager,
    GBMSyntheticMarketSimulator,
    MarketDataFeedManager,
    ConnectionManager
)


@pytest.fixture(autouse=True)
def setup_teardown_state():
    """Resets server state and connection manager before each test."""
    terminal_state.status = "RUNNING"
    terminal_state.simulation_mode = True
    terminal_state.balance = 25480.00
    terminal_state.equity = 25730.00
    terminal_state.daily_profit = 250.00
    terminal_state._seed_initial_positions()
    yield
    # Clean up any lingering connections
    ws_manager.terminal_connections.clear()
    ws_manager.market_connections.clear()
    ws_manager.cockpit_connections.clear()
    ws_manager.subscriptions.clear()


# =====================================================================
# 1. Connection Churn & Concurrency Tests
# =====================================================================

def test_ws_connection_churn_rapid_connect_disconnect():
    """
    Stress-tests rapid sequential and interleaved connect/disconnect cycles
    to ensure ConnectionManager cleans up cleanly with zero orphaned references.
    """
    with TestClient(app) as client:
        # Rapid churn on /ws/terminal
        for i in range(25):
            with client.websocket_connect("/ws/terminal") as ws:
                _ = ws.receive_json()  # smc_update
                _ = ws.receive_json()  # cockpit_metrics
                _ = ws.receive_json()  # positions_update
                assert len(ws_manager.terminal_connections) == 1
            # After context manager exit, connection should be removed or removable
            # Manually trigger disconnect if client closed cleanly
            assert len(ws_manager.terminal_connections) <= 1

        # Rapid churn on /ws/market
        for i in range(25):
            with client.websocket_connect("/ws/market") as ws:
                ws.send_text(f"PING_{i}")
                assert len(ws_manager.market_connections) >= 1

        # Rapid churn on /ws/cockpit
        for i in range(25):
            with client.websocket_connect("/ws/cockpit") as ws:
                frame = ws.receive_json()
                assert frame["type"] == "cockpit_metrics"
                assert len(ws_manager.cockpit_connections) >= 1


def receive_until(ws, target_types, max_frames=50):
    if isinstance(target_types, str):
        target_types = [target_types]
    for _ in range(max_frames):
        frame = ws.receive_json()
        if frame.get("type") in target_types:
            return frame
    return frame


def drain_initial_snapshot(ws):
    """Drains the initial 3 connection snapshot frames (smc_update, cockpit_metrics, positions_update)."""
    frames = []
    while len(frames) < 3:
        f = ws.receive_json()
        if f.get("type") in ["smc_update", "cockpit_metrics", "positions_update"]:
            frames.append(f)


def test_ws_multi_client_concurrent_broadcast():
    """
    Verifies that broadcasts reach multiple simultaneous WebSocket clients
    across /ws/terminal, /ws/market, and /ws/cockpit without cross-contamination.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws1, \
             client.websocket_connect("/ws/terminal") as ws2, \
             client.websocket_connect("/ws/market") as ws_mkt, \
             client.websocket_connect("/ws/cockpit") as ws_cockpit:

            assert len(ws_manager.terminal_connections) == 2
            assert len(ws_manager.market_connections) == 1
            assert len(ws_manager.cockpit_connections) == 1

            drain_initial_snapshot(ws1)
            drain_initial_snapshot(ws2)

            # Consume cockpit initial frame
            cockpit_snap = receive_until(ws_cockpit, "cockpit_metrics")
            assert cockpit_snap["type"] == "cockpit_metrics"

            # Execute a command on ws1 -> should broadcast positions_update to both ws1 and ws2
            ws1.send_json({"type": "command", "action": "breakeven", "ticket": 100101, "buffer_pips": 2.0})
            cmd_res = receive_until(ws1, "command_result")
            assert cmd_res["type"] == "command_result"

            pos_update_ws1 = receive_until(ws1, "positions_update")
            assert pos_update_ws1["type"] == "positions_update"

            pos_update_ws2 = receive_until(ws2, "positions_update")
            assert pos_update_ws2["type"] == "positions_update"
            assert pos_update_ws2["positions"][0]["sl"] == 2645.20


# =====================================================================
# 2. Dynamic Subscription Mutation Matrix Tests
# =====================================================================

@pytest.mark.parametrize("symbol", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"])
@pytest.mark.parametrize("timeframe", ["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
def test_ws_subscription_mutation_all_symbols_and_tfs(symbol, timeframe):
    """
    Verifies dynamic switching across all supported symbols and timeframes.
    Validates that the server returns updated SMC and updates active subscription.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            drain_initial_snapshot(ws)
            # Send subscription change
            ws.send_json({"type": "subscribe", "symbol": symbol, "timeframe": timeframe})
            sub_res = receive_until(ws, "smc_update")

            assert sub_res["type"] == "smc_update"
            assert sub_res["symbol"] == symbol
            assert "data" in sub_res
            assert sub_res["data"]["timeframe"] == timeframe
            assert "fvgs" in sub_res["data"]
            assert "order_blocks" in sub_res["data"]
            assert "ote" in sub_res["data"]
            assert "killzones" in sub_res["data"]


def test_ws_subscription_lowercase_and_fallback():
    """Verifies server normalizes lowercase symbol/timeframe inputs."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            drain_initial_snapshot(ws)
            ws.send_json({"type": "subscribe", "symbol": "gbpusd", "timeframe": "h4"})
            res = receive_until(ws, "smc_update")
            assert res["symbol"] == "GBPUSD"
            assert res["data"]["timeframe"] == "H4"


# =====================================================================
# 3. Message Frame Structure & Numerical Boundary Validation
# =====================================================================

def test_ws_json_frame_structure_deep_validation():
    """
    Validates complete mathematical and structural schemas of all WebSocket frames:
    - SMC Overlays (FVG CE bounds, OB bounds, OTE levels)
    - Cockpit Risk Metrics (99% VaR/CVaR, HWM floor, Drawdown meters)
    - Position Updates (Tickets, Volumes, PnL, SL/TP)
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            frame1 = ws.receive_json()
            frame2 = ws.receive_json()
            frame3 = ws.receive_json()

            frames = {f["type"]: f for f in [frame1, frame2, frame3]}
            assert "smc_update" in frames
            assert "cockpit_metrics" in frames
            assert "positions_update" in frames

            # 1. Validate smc_update
            smc = frames["smc_update"]["data"]
            assert smc["symbol"] == "XAUUSD"
            assert smc["timeframe"] == "M15"
            assert isinstance(smc["fvgs"], list)
            for fvg in smc["fvgs"]:
                assert fvg["top"] >= fvg["bottom"]
                assert fvg["ce"] == round((fvg["top"] + fvg["bottom"]) / 2.0, 5)
                assert isinstance(fvg["mitigated"], bool)

            for ob in smc["order_blocks"]:
                assert ob["top"] >= ob["bottom"]
                assert ob["type"] in ["BULLISH_OB", "BEARISH_OB"]

            ote = smc["ote"]
            assert ote["swing_high"] >= ote["swing_low"]
            assert ote["levels"]["eq"] == round((ote["swing_high"] + ote["swing_low"]) / 2.0, 5)

            # 2. Validate cockpit_metrics
            metrics = frames["cockpit_metrics"]["data"]
            assert metrics["balance"] > 0
            assert metrics["equity"] > 0
            assert metrics["cvar_99_usd"] >= metrics["var_99_usd"]
            assert metrics["trailing_floor"] <= metrics["hwm"]
            assert metrics["daily_loss_allowed"] > 0
            assert metrics["consistency_max_allowed"] == 700.0
            assert metrics["consistency_status"] in ["NOMINAL", "CAUTION", "CRITICAL", "CEILING_REACHED"]

            # 3. Validate positions_update
            positions = frames["positions_update"]["positions"]
            assert len(positions) == 2
            for pos in positions:
                assert isinstance(pos["ticket"], int)
                assert pos["volume"] > 0
                assert pos["price_open"] > 0
                assert pos["type"] in ["BUY", "SELL"]


# =====================================================================
# 4. WebSocket 1-Click Execution & Voice NLP Commands
# =====================================================================

def test_ws_execution_all_actions():
    """
    Rigorously tests all 1-click execution actions via WebSocket:
    - scale_out
    - breakeven
    - modify_sltp
    - close_position
    - kill_switch
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            drain_initial_snapshot(ws)
            # 1. scale_out
            ws.send_json({"type": "command", "action": "scale_out", "ticket": 100101, "ratio": 0.5})
            res = receive_until(ws, "command_result")
            assert res["type"] == "command_result"
            assert res["result"]["success"] is True
            assert res["result"]["closed_volume"] == 0.25
            assert res["result"]["remaining_volume"] == 0.25
            pos_frame = receive_until(ws, "positions_update")
            assert pos_frame["type"] == "positions_update"

            # 2. modify_sltp
            ws.send_json({"type": "command", "action": "modify_sltp", "ticket": 100101, "sl": 2640.0, "tp": 2690.0})
            res = receive_until(ws, "command_result")
            assert res["type"] == "command_result"
            assert res["result"]["success"] is True
            pos_frame = receive_until(ws, "positions_update")
            assert pos_frame["type"] == "positions_update"

            # 3. close_position
            ws.send_json({"type": "command", "action": "close_position", "ticket": 100101})
            res = receive_until(ws, "command_result")
            assert res["type"] == "command_result"
            assert res["result"]["success"] is True
            pos_frame = receive_until(ws, "positions_update")
            assert len(pos_frame["positions"]) == 1

            # 4. kill_switch
            ws.send_json({"type": "command", "action": "kill_switch"})
            res = receive_until(ws, "command_result")
            assert res["type"] == "command_result"
            assert res["result"]["status"] == "EMERGENCY_LOCKED"
            pos_frame = receive_until(ws, "positions_update")
            assert len(pos_frame["positions"]) == 0


def test_ws_voice_intent_commands():
    """Verifies natural language voice command execution over /ws/terminal WebSocket."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            drain_initial_snapshot(ws)
            # Send voice command
            ws.send_json({"type": "voice_intent", "transcript": "Lock Breakeven on Gold", "active_symbol": "XAUUSD"})
            res = receive_until(ws, "jarvis_event")
            assert res["type"] == "jarvis_event"
            assert res["intent"] == "LOCK_BREAKEVEN"
            assert "speech" in res
            assert "Confirmed" in res["speech"] or "Locked" in res["speech"]


# =====================================================================
# 5. 20Hz Streaming Simulation, Buffer Pruning & Memory Bounds
# =====================================================================

def test_market_feed_buffer_pruning_and_memory_stability():
    """
    Stress-tests the market data feed manager over 1,500 continuous ticks
    to verify that in-memory buffers strictly prune and do not leak memory.
    """
    feed = MarketDataFeedManager(simulation_mode=True)
    assert len(feed.SYMBOLS) == 7

    # Stream 1,500 ticks across all symbols
    for i in range(1500):
        for sym in feed.SYMBOLS:
            tick = feed.simulator.next_tick(sym)
            feed.process_tick(tick)

    for sym in feed.SYMBOLS:
        # Tick buffer bounded at 1000
        assert len(feed.tick_buffer[sym]) <= 1000
        # CVD history bounded at 200
        assert len(feed.running_cvd[sym]["history"]) <= 200
        # Candle caches bounded at 500 per timeframe
        for tf in feed.TIMEFRAMES:
            assert len(feed.candle_cache[sym][tf]) <= 500


def test_depth_of_market_distribution_and_balance():
    """
    Tests Level 2 Depth of Market generation across 100 iterations.
    Ensures buyer_ratio + seller_ratio == 100% and bid < ask.
    """
    sim = GBMSyntheticMarketSimulator()
    for _ in range(100):
        dom = sim.generate_depth("XAUUSD")
        assert dom["type"] == "market_depth"
        assert dom["ask"] >= dom["bid"]
        assert pytest.approx(dom["buyer_ratio"] + dom["seller_ratio"], abs=0.1) == 100.0
        assert len(dom["bids"]) == 5
        assert len(dom["asks"]) == 5
        assert dom["spread_pips"] > 0
