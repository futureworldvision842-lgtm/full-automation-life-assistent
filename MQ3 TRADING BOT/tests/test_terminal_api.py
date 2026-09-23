"""
test_terminal_api.py — Comprehensive Test Suite for Web Terminal Server, REST Endpoints,
WebSocket Protocols, Aladdin Risk Telemetry, 1-Click Execution, and Voice NLP Copilot.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.web_terminal_server import (
    app,
    terminal_state,
    voice_engine,
    GBMSyntheticMarketSimulator,
    MarketDataFeedManager
)


@pytest.fixture(autouse=True)
def reset_terminal_state():
    """Resets the mock state before each test for clean deterministic execution."""
    terminal_state.status = "RUNNING"
    terminal_state.simulation_mode = True
    terminal_state.balance = 25480.00
    terminal_state.equity = 25730.00
    terminal_state.daily_profit = 250.00
    terminal_state._seed_initial_positions()


# =====================================================================
# 1. System Status & Health Endpoint Tests
# =====================================================================

def test_get_system_status():
    """Verifies GET /api/status returns valid system state and quotes for all 7 assets."""
    with TestClient(app) as client:
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["RUNNING", "PAUSED", "EMERGENCY_LOCKED"]
        assert data["simulation_mode"] is True
        assert "account" in data
        assert data["account"]["balance"] > 0
        assert data["account"]["equity"] > 0
        assert data["account"]["currency"] == "USD"
        assert len(data["active_symbols"]) == 7
        assert "XAUUSD" in data["active_symbols"]
        assert "EURUSD" in data["active_symbols"]
        assert "GBPUSD" in data["active_symbols"]
        assert "USDJPY" in data["active_symbols"]
        assert "BTCUSD" in data["active_symbols"]
        assert "ETHUSD" in data["active_symbols"]
        assert "SOLUSD" in data["active_symbols"]

        for sym, quote in data["quotes"].items():
            assert "bid" in quote
            assert "ask" in quote
            assert "last" in quote
            assert quote["ask"] >= quote["bid"]
            assert quote["last"] > 0

        assert "server_time_utc" in data
        assert data["open_positions_count"] >= 0


# =====================================================================
# 2. Historical Multi-Timeframe Candles Endpoint Tests
# =====================================================================

@pytest.mark.parametrize("symbol", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"])
@pytest.mark.parametrize("timeframe", ["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
def test_get_candles_multi_symbol_timeframe(symbol, timeframe):
    """Verifies GET /api/candles returns coherent OHLCV data across all symbols & timeframes."""
    with TestClient(app) as client:
        limit = 50
        response = client.get(f"/api/candles?symbol={symbol}&timeframe={timeframe}&limit={limit}")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == symbol
        assert data["timeframe"] == timeframe
        assert data["count"] == limit
        assert len(data["candles"]) == limit

        candles = data["candles"]
        for i, c in enumerate(candles):
            assert isinstance(c["time"], int)
            assert c["time"] > 0
            assert c["open"] > 0
            assert c["high"] > 0
            assert c["low"] > 0
            assert c["close"] > 0
            assert c["volume"] >= 0

            # Mathematical Candlestick Consistency
            assert c["high"] >= max(c["open"], c["close"])
            assert c["low"] <= min(c["open"], c["close"])

            # Chronological Ordering
            if i > 0:
                assert c["time"] >= candles[i - 1]["time"]


# =====================================================================
# 3. Institutional SMC Overlays Endpoint Tests
# =====================================================================

def test_get_smc_endpoint_structure_and_ce():
    """Verifies GET /api/smc returns FVGs with 50% CE, Order Blocks, OTE Grids, and Killzones."""
    with TestClient(app) as client:
        response = client.get("/api/smc?symbol=XAUUSD&timeframe=M15")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "XAUUSD"
        assert data["timeframe"] == "M15"
        assert "fvgs" in data
        assert "order_blocks" in data
        assert "ote" in data
        assert "sweeps" in data
        assert "killzones" in data

        # Check FVG 50% CE calculation
        for fvg in data["fvgs"]:
            assert "top" in fvg
            assert "bottom" in fvg
            assert "ce" in fvg
            assert "mitigated" in fvg
            assert fvg["type"] in ["BULLISH_FVG", "BEARISH_FVG"]
            expected_ce = round((fvg["top"] + fvg["bottom"]) / 2.0, 5)
            assert pytest.approx(fvg["ce"], rel=1e-3) == expected_ce

        # Check Order Blocks
        for ob in data["order_blocks"]:
            assert "top" in ob
            assert "bottom" in ob
            assert "type" in ob
            assert "entry_price" in ob
            assert "sl_price" in ob
            assert "touched" in ob
            assert "mitigated" in ob

        # Check OTE Fibonacci Retracement Grid
        ote = data["ote"]
        assert "swing_high" in ote
        assert "swing_low" in ote
        assert "trend" in ote
        assert "in_ote_zone" in ote
        assert "levels" in ote
        levels = ote["levels"]
        assert "eq" in levels
        assert "fib_618" in levels
        assert "sweet_spot_705" in levels
        assert "fib_786" in levels

        # Check Interbank Killzones
        kz = data["killzones"]
        assert len(kz) == 3
        kz_names = [k["name"] for k in kz]
        assert "London Open" in kz_names
        assert "NY Morning (AM)" in kz_names
        assert "NY Afternoon (PM)" in kz_names


# =====================================================================
# 4. Lee-Ready Cumulative Volume Delta (CVD) Endpoint Tests
# =====================================================================

def test_get_cvd_endpoint_metrics():
    """Verifies GET /api/cvd returns tick delta history, buyer/seller ratios, and divergence."""
    with TestClient(app) as client:
        limit = 40
        response = client.get(f"/api/cvd?symbol=XAUUSD&limit={limit}")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "XAUUSD"
        assert "cvd_history" in data
        assert len(data["cvd_history"]) <= limit
        assert len(data["cvd_history"]) > 0

        # Check Ratio
        ratio = data["current_ratio"]
        assert "buyer" in ratio
        assert "seller" in ratio
        assert pytest.approx(ratio["buyer"] + ratio["seller"], abs=0.5) == 100.0

        # Check Divergence Object
        assert "divergence" in data
        assert "active" in data["divergence"]
        assert "type" in data["divergence"]
        assert "description" in data["divergence"]


# =====================================================================
# 5. Aladdin 99% VaR/CVaR & Prop Firm Risk Telemetry Tests
# =====================================================================

def test_get_risk_metrics_endpoint_telemetry():
    """Verifies GET /api/risk/metrics returns Aladdin VaR/CVaR, HWM floor, and consistency pacing."""
    with TestClient(app) as client:
        response = client.get("/api/risk/metrics")
        assert response.status_code == 200
        data = response.json()

        assert data["balance"] > 0
        assert data["equity"] > 0
        assert "floating_pnl" in data
        assert data["var_99_usd"] > 0
        assert data["var_99_pct"] > 0
        assert data["cvar_99_usd"] > 0

        # Quantitative property: CVaR (Expected Shortfall) is strictly greater than VaR at 99%
        assert data["cvar_99_usd"] > data["var_99_usd"]

        # Trailing HWM Floor Defense
        assert data["hwm"] >= data["balance"] or data["hwm"] >= data["equity"]
        assert data["trailing_floor"] < data["hwm"]
        assert data["trailing_buffer_usd"] >= 0

        # Daily Drawdown Allowance
        assert data["daily_loss_allowed"] > 0
        assert data["daily_loss_remaining"] <= data["daily_loss_allowed"]

        # 35% Consistency Pacing
        assert data["consistency_max_allowed"] == 700.0  # 35% of $2,000 target
        assert data["consistency_status"] in ["NOMINAL", "CAUTION", "CRITICAL", "CEILING_REACHED"]

        # Sub-objects
        assert "aladdin_risk" in data
        assert "prop_firm_defense" in data
        assert "consistency_gauge" in data
        assert len(data["open_positions"]) == 2


# =====================================================================
# 6. 1-Click Execution Endpoints Tests
# =====================================================================

def test_execution_scale_out_50():
    """Verifies POST /api/execution/scale-out closes 50% volume and moves SL to breakeven."""
    with TestClient(app) as client:
        payload = {"ticket": 100101, "ratio": 0.5, "buffer_pips": 2.0}
        response = client.post("/api/execution/scale-out", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["ticket"] == 100101
        assert res["closed_volume"] == 0.25
        assert res["remaining_volume"] == 0.25
        # BUY open price 2645.00 + 2 pips (0.20) = 2645.20
        assert res["new_sl"] == 2645.20

        # Verify open positions table updated
        pos_res = client.get("/api/risk/metrics").json()
        pos = next(p for p in pos_res["open_positions"] if p["ticket"] == 100101)
        assert pos["volume"] == 0.25
        assert pos["sl"] == 2645.20


def test_execution_modify_sltp():
    """Verifies POST /api/execution/modify-sltp updates target position SL and TP."""
    with TestClient(app) as client:
        payload = {"ticket": 100101, "sl": 2642.50, "tp": 2685.00}
        response = client.post("/api/execution/modify-sltp", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["ticket"] == 100101
        assert res["sl"] == 2642.50
        assert res["tp"] == 2685.00

        # Verify state reflection
        pos_res = client.get("/api/risk/metrics").json()
        pos = next(p for p in pos_res["open_positions"] if p["ticket"] == 100101)
        assert pos["sl"] == 2642.50
        assert pos["tp"] == 2685.00


def test_execution_breakeven():
    """Verifies POST /api/execution/breakeven secures SL to entry plus buffer pips."""
    with TestClient(app) as client:
        payload = {"ticket": 100102, "buffer_pips": 3.0}
        response = client.post("/api/execution/breakeven", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["ticket"] == 100102
        # EURUSD SELL open at 1.08650 - 3 pips (0.00030) = 1.08620
        assert res["new_sl"] == 1.08620


def test_execution_close_single_position():
    """Verifies POST /api/execution/close-position liquidates target position."""
    with TestClient(app) as client:
        payload = {"ticket": 100101}
        response = client.post("/api/execution/close-position", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["ticket"] == 100101
        assert res["closed_volume"] == 0.50

        # Verify position count reduced to 1
        pos_res = client.get("/api/risk/metrics").json()
        assert len(pos_res["open_positions"]) == 1
        assert pos_res["open_positions"][0]["ticket"] == 100102


def test_execution_invalid_ticket_returns_400():
    """Verifies execution on non-existent ticket gracefully returns 400 Bad Request."""
    with TestClient(app) as client:
        payload = {"ticket": 999999, "ratio": 0.5}
        response = client.post("/api/execution/scale-out", json=payload)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


# =====================================================================
# 7. Emergency Circuit Breaker & Bot Control Tests
# =====================================================================

def test_emergency_kill_switch_action():
    """Verifies POST /api/control/kill-switch closes all positions and sets EMERGENCY_LOCKED."""
    with TestClient(app) as client:
        payload = {"reason": "Adversarial Stress Test Trigger", "cancel_pending": True}
        response = client.post("/api/control/kill-switch", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["closed_positions"] == 2
        assert res["status"] == "EMERGENCY_LOCKED"

        # Check system status reflection
        status_res = client.get("/api/status").json()
        assert status_res["status"] == "EMERGENCY_LOCKED"
        assert status_res["open_positions_count"] == 0


def test_bot_pause_resume_toggle():
    """Verifies POST /api/control/toggle-pause pauses and resumes bot execution."""
    with TestClient(app) as client:
        # Pause
        res = client.post("/api/control/toggle-pause", json={"action": "pause"}).json()
        assert res["success"] is True
        assert res["paused"] is True
        assert res["status"] == "PAUSED"

        # Resume
        res = client.post("/api/control/toggle-pause", json={"action": "resume"}).json()
        assert res["success"] is True
        assert res["paused"] is False
        assert res["status"] == "RUNNING"


# =====================================================================
# 8. Deterministic Voice NLP Parser Tests
# =====================================================================

@pytest.mark.parametrize("transcript,expected_intent,expected_action", [
    ("Close 50% on Gold", "SCALE_OUT_PARTIAL", True),
    ("Scale out half on EURUSD", "SCALE_OUT_PARTIAL", True),
    ("Lock Breakeven on Gold", "LOCK_BREAKEVEN", True),
    ("Protect trade on EURUSD", "LOCK_BREAKEVEN", True),
    ("Set Stop Loss on Gold to 2644.50", "MODIFY_SL_TP", True),
    ("Show Gold Macro Bias", "SHOW_MACRO_BIAS", False),
    ("Scan for Liquidity Sweeps", "SCAN_SWEEPS", False),
    ("Emergency Kill Switch", "EMERGENCY_KILL_SWITCH", True),
    ("What is my daily drawdown", "GET_RISK_METRICS", False),
    ("Jarvis system status", "SYSTEM_STATUS_QUERY", False),
    ("Tell me a random story", "UNKNOWN_FALLBACK", False),
])
def test_voice_nlp_parser_all_intents(transcript, expected_intent, expected_action):
    """Verifies deterministic voice parser maps natural language to correct intent and action."""
    with TestClient(app) as client:
        payload = {"transcript": transcript, "active_symbol": "XAUUSD"}
        response = client.post("/api/voice/command", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["intent"] == expected_intent
        assert res["action_taken"] == expected_action
        assert "response_speech" in res
        assert len(res["response_speech"]) > 10


# =====================================================================
# 9. WebSocket Channels Tests
# =====================================================================

def test_websocket_terminal_initial_snapshot_and_subscription():
    """Verifies /ws/terminal streams initial snapshot, handles subscriptions and commands."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/terminal") as ws:
            # 1. Initial snapshot frames (smc_update, cockpit_metrics, positions_update, world_monitor_update)
            frame1 = ws.receive_json()
            assert frame1["type"] in ["smc_update", "cockpit_metrics", "positions_update", "world_monitor_update"]
            frame2 = ws.receive_json()
            assert frame2["type"] in ["smc_update", "cockpit_metrics", "positions_update", "world_monitor_update"]
            frame3 = ws.receive_json()
            assert frame3["type"] in ["smc_update", "cockpit_metrics", "positions_update", "world_monitor_update"]

            # 2. Send Subscription message
            ws.send_json({"type": "subscribe", "symbol": "EURUSD", "timeframe": "H1"})
            sub_res = ws.receive_json()
            while sub_res.get("type") in ["tick", "candle_update", "cvd_update", "cockpit_metrics", "positions_update", "world_monitor_update"]:
                sub_res = ws.receive_json()
            assert sub_res["type"] == "smc_update"
            assert sub_res["symbol"] == "EURUSD"

            # 3. Send 1-Click Command via WebSocket
            ws.send_json({"type": "command", "action": "breakeven", "ticket": 100101, "buffer_pips": 2.0})
            cmd_res = ws.receive_json()
            while cmd_res.get("type") in ["tick", "candle_update", "cvd_update", "positions_update", "cockpit_metrics", "world_monitor_update"]:
                cmd_res = ws.receive_json()
            assert cmd_res["type"] == "command_result"
            assert cmd_res["action"] == "breakeven"
            assert cmd_res["result"]["success"] is True

            # 4. Send Voice Intent via WebSocket
            ws.send_json({"type": "voice_intent", "transcript": "Show gold macro bias"})
            voice_res = ws.receive_json()
            while voice_res.get("type") in ["tick", "candle_update", "cvd_update", "positions_update", "cockpit_metrics", "world_monitor_update"]:
                voice_res = ws.receive_json()
            assert voice_res["type"] == "jarvis_event"
            assert voice_res["intent"] == "SHOW_MACRO_BIAS"
            assert "speech" in voice_res


def test_websocket_market_channel_connection():
    """Verifies /ws/market accepts connections and stays responsive."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/market") as ws:
            ws.send_text("PING")
            assert ws is not None


def test_websocket_cockpit_channel_telemetry():
    """Verifies /ws/cockpit delivers initial cockpit metrics frame."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/cockpit") as ws:
            frame = ws.receive_json()
            assert frame["type"] == "cockpit_metrics"
            assert "data" in frame
            assert frame["data"]["balance"] > 0
            assert frame["data"]["var_99_usd"] > 0


# =====================================================================
# 10. World Monitor Geopolitical Radar Tests
# =====================================================================

def test_get_world_monitor_endpoint():
    """Verifies GET /api/world_monitor returns DEFCON level, 5 chokepoints, CII v8 scores, and OSINT alerts."""
    with TestClient(app) as client:
        response = client.get("/api/world_monitor")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "global_threat_level" in data
        assert "DEFCON" in data["global_threat_level"]
        assert data["global_risk_index"] > 0
        assert "primary_geopolitical_hotspot" in data

        # Verify 5 Maritime Chokepoints
        assert "chokepoints" in data
        assert len(data["chokepoints"]) == 5
        chokepoint_names = [cp["name"] for cp in data["chokepoints"]]
        assert any("Hormuz" in name for name in chokepoint_names)
        assert any("Suez" in name for name in chokepoint_names)
        assert any("Bab el-Mandeb" in name or "Red Sea" in name for name in chokepoint_names)
        assert any("Malacca" in name for name in chokepoint_names)
        assert any("Taiwan" in name for name in chokepoint_names)

        # Verify Country Instability Index (CII v8)
        assert "country_instability" in data
        assert "Middle_East" in data["country_instability"]
        assert "Eastern_Europe" in data["country_instability"]

        # Verify Market Bias Multipliers
        assert "market_bias" in data
        assert "XAUUSD" in data["market_bias"]
        assert data["market_bias"]["XAUUSD"] > 1.0  # Gold bullish flight

        # Verify Live OSINT Alerts Stream
        assert "osint_alerts" in data
        assert len(data["osint_alerts"]) >= 1
        alert = data["osint_alerts"][0]
        assert "region" in alert
        assert "severity" in alert
        assert "headline" in alert


def test_websocket_worldmonitor_channel_telemetry():
    """Verifies /ws/worldmonitor accepts connection and streams initial geopolitical snapshot frame."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/worldmonitor") as ws:
            frame = ws.receive_json()
            assert frame["type"] == "world_monitor_update"
            assert "data" in frame
            wm_data = frame["data"]
            assert wm_data["status"] == "success"
            assert len(wm_data["chokepoints"]) == 5
            assert "global_threat_level" in wm_data


# =====================================================================
# 11. WhatsApp Multi-Device Bridge & Command Dispatch Tests
# =====================================================================

def test_get_whatsapp_qr_endpoint():
    """Verifies GET /api/whatsapp_qr returns connection status, pairing QR metadata, and authorized contacts."""
    with TestClient(app) as client:
        response = client.get("/api/whatsapp_qr")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "connected" in data
        assert "has_qr" in data
        assert "authorized_contacts" in data
        assert len(data["authorized_contacts"]) == 1
        assert "923468053268" in data["authorized_contacts"]
        assert "923487117832" not in data["authorized_contacts"]
        assert "923322555238" not in data["authorized_contacts"]
        assert "923375893095" not in data["authorized_contacts"]
        assert "elite_group" in data
        assert "120363401615322542@g.us" == data["elite_group"]


def test_post_whatsapp_command_whitelisted():
    """Verifies POST /api/whatsapp_command processes commands for authorized phone numbers."""
    with TestClient(app) as client:
        payload = {
            "command": "status",
            "sender": "923468053268"
        }
        response = client.post("/api/whatsapp_command", json=payload)
        assert response.status_code == 200
        res = response.json()

        assert res["success"] is True
        assert res["command"] == "status"
        assert res["sender"] == "923468053268"
        assert len(res["response"]) > 0


# =====================================================================
# 12. GBM Simulator Market Physics & Crypto Asset Tests
# =====================================================================

def test_gbm_simulator_depth_and_pricing():
    """Verifies GBM Market Simulator generates realistic 5-level DOM depth and positive prices for all 7 assets."""
    sim = GBMSyntheticMarketSimulator()
    for sym in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "SOLUSD"]:
        tick = sim.next_tick(sym)
        assert tick["symbol"] == sym
        assert tick["bid"] > 0
        assert tick["ask"] > 0
        assert tick["ask"] >= tick["bid"]
        assert tick["volume"] > 0

        dom = sim.generate_depth(sym)
        assert dom["symbol"] == sym
        assert len(dom["bids"]) == 5
        assert len(dom["asks"]) == 5
        # Bid prices descending
        for i in range(4):
            assert dom["bids"][i]["price"] >= dom["bids"][i + 1]["price"]
            assert dom["asks"][i]["price"] <= dom["asks"][i + 1]["price"]
        assert pytest.approx(dom["buyer_ratio"] + dom["seller_ratio"], abs=0.5) == 100.0


def test_voice_nlp_crypto_intents():
    """Verifies VoiceNLPEngine parses crypto assets and ratios correctly."""
    engine = voice_engine
    # Test Bitcoin intent
    res_btc = engine.parse_and_execute("Close half on bitcoin", active_symbol="BTCUSD")
    assert res_btc["symbol"] == "BTCUSD"
    assert res_btc["intent"] in ["SCALE_OUT", "SCALE_OUT_PARTIAL"]
    assert res_btc["ratio"] == 0.50

    # Test Solana intent
    res_sol = engine.parse_and_execute("Lock breakeven on solana", active_symbol="SOLUSD")
    assert res_sol["symbol"] == "SOLUSD"
    assert res_sol["intent"] == "LOCK_BREAKEVEN"


# =====================================================================
# 13. Dual-Venue Execution Router & Bitget Position Lifecycle Tests
# =====================================================================

def test_bitget_connector_lifecycle_methods():
    """Verifies BitgetConnector full position lifecycle in simulation mode."""
    from src.bitget_connector import BitgetConnector
    bg = BitgetConnector(sim_mode=True)
    
    # 1. Place order
    res = bg.place_order(symbol="BTCUSD", side="buy", size=0.5, price=63000.0, sl=62000.0, tp=65000.0)
    assert res["status"] == "success"
    order_id = res["order_id"]
    assert order_id.startswith("SIM_BG_")

    # 2. Get open positions
    positions = bg.get_open_positions()
    assert len(positions) >= 1
    target = next((p for p in positions if p["order_id"] == order_id), None)
    assert target is not None
    assert target["size"] == 0.5

    # 3. Modify position SL / TP
    mod_ok = bg.modify_position(order_id=order_id, new_sl=63100.0, new_tp=66000.0)
    assert mod_ok is True
    assert target["sl"] == 63100.0
    assert target["tp"] == 66000.0

    # 4. Partial scale out (50%)
    scale_ok = bg.close_partial_position(order_id=order_id, close_size=0.25)
    assert scale_ok is True
    assert target["size"] == 0.25

    # 5. Position close
    close_ok = bg.close_position(order_id=order_id)
    assert close_ok is True
    assert not any(p["order_id"] == order_id for p in bg.get_open_positions())

    # 6. Emergency close all
    bg.place_order(symbol="ETHUSD", side="buy", size=2.0)
    bg.place_order(symbol="SOLUSD", side="sell", size=10.0)
    assert len(bg.get_open_positions()) == 2
    closed_count = bg.emergency_close_all()
    assert closed_count == 2
    assert len(bg.get_open_positions()) == 0


def test_multi_broker_bridge_dual_venue():
    """Verifies BitgetBridgeConnector and DualVenueRouterBridge routing logic."""
    from src.multi_broker_bridge import BitgetBridgeConnector, DualVenueRouterBridge

    bitget_bridge = BitgetBridgeConnector()
    assert bitget_bridge.is_connected is True
    mapped_btc = bitget_bridge.map_symbol("BTCUSD")
    assert mapped_btc["symbol"] == "BTCUSDT"
    assert mapped_btc["productType"] == "USDT-FUTURES"

    router = DualVenueRouterBridge()
    # Test Crypto routing
    crypto_order = {"symbol": "BTCUSD", "direction": "BUY", "lots": 0.1, "entry_price": 63000.0}
    crypto_res = router.route(crypto_order)
    assert crypto_res["venue"] == "BITGET"
    assert crypto_res["target_symbol"] == "BTCUSDT"
    assert crypto_res["result"]["status"] == "success"

    # Test Forex routing
    forex_order = {"symbol": "EURUSD", "direction": "BUY", "lots": 0.5, "entry_price": 1.0850, "sl": 1.0800, "tp": 1.0950}
    forex_res = router.route(forex_order)
    assert forex_res["venue"] == "MT5"
    assert forex_res["target_symbol"] == "EURUSD"
    assert "bracket" in forex_res


def test_autonomous_fleet_executor_contract2_routing():
    """Verifies AutonomousFleetExecutor.route_order complies with Contract #2."""
    from src.autonomous_fleet_executor import AutonomousFleetExecutor
    executor = AutonomousFleetExecutor()

    # 1. Route Forex order (MT5)
    forex_order = {
        "symbol": "XAUUSD",
        "direction": "BUY",
        "lots": 0.25,
        "entry_price": 2650.0,
        "sl": 2640.0,
        "tp": 2670.0
    }
    rcpt_fx = executor.route_order(account_id="FP_25K_01", order=forex_order)
    assert rcpt_fx["venue"] == "MT5"
    assert rcpt_fx["symbol"] == "XAUUSD"
    assert rcpt_fx["account_id"] == "FP_25K_01"
    assert rcpt_fx["status"] == "FILLED"
    assert "RCPT-MT5-" in rcpt_fx["receipt_id"]

    # 2. Route Crypto order (Bitget)
    crypto_order = {
        "symbol": "BTCUSD",
        "direction": "SELL",
        "lots": 0.5,
        "entry_price": 63400.0,
        "sl": 64000.0,
        "tp": 62000.0
    }
    rcpt_crypto = executor.route_order(account_id="BINANCE_01", order=crypto_order)
    assert rcpt_crypto["venue"] == "BITGET"
    assert rcpt_crypto["symbol"] == "BTCUSDT"
    assert rcpt_crypto["account_id"] == "BINANCE_01"
    assert rcpt_crypto["status"] == "FILLED"
    assert "RCPT-BG-" in rcpt_crypto["receipt_id"]


def test_autonomous_fleet_executor_fvg_ce_trailing():
    """Verifies FVG Consequent Encroachment (50% midpoint) Trailing SL calculation."""
    from src.autonomous_fleet_executor import AutonomousFleetExecutor
    executor = AutonomousFleetExecutor()

    # Seed an active position
    executor.active_positions = [{
        "ticket": 999901,
        "account_id": "TEST_ACC",
        "symbol": "XAUUSD",
        "type": "BUY",
        "direction": "BUY",
        "lots": 0.5,
        "open_price": 2640.0,
        "sl": 2630.0,
        "tp1": 2670.0,
        "status": "RUNNING"
    }]

    # Bullish FVG gap: Top = 2655.0, Bottom = 2645.0 => CE = 2650.0
    res = executor.trail_fvg_consequent_encroachment(
        ticket=999901,
        fvg_top=2655.0,
        fvg_bottom=2645.0,
        gap_type="BULLISH_BISI"
    )
    assert res["success"] is True
    assert res["ce_50"] == 2650.0
    pos = executor.active_positions[0]
    assert pos["sl"] == 2650.0
    assert pos["status"] == "TRAILING_FVG_50_CE"


def test_autonomous_fleet_executor_spread_buffer_breakeven():
    """Verifies Breakeven locking incorporates authentic spread buffer."""
    from src.autonomous_fleet_executor import AutonomousFleetExecutor
    executor = AutonomousFleetExecutor()

    # Seed BUY position on EURUSD (pip_unit = 0.0001, buffer_pips = 1.0 => new_sl = open + 0.0001)
    executor.active_positions = [{
        "ticket": 999902,
        "account_id": "TEST_ACC",
        "symbol": "EURUSD",
        "type": "BUY",
        "direction": "BUY",
        "lots": 1.0,
        "open_price": 1.08500,
        "sl": 1.08000,
        "status": "RUNNING"
    }]

    res = executor.manage_position_action(ticket=999902, action="be", buffer_pips=1.0)
    assert res["success"] is True
    pos = executor.active_positions[0]
    assert pos["sl"] == 1.08510
    assert pos["status"] == "BE_LOCKED"


def test_autonomous_fleet_executor_emergency_kill_switch():
    """Verifies Emergency Kill-Switch flattens fleet positions across venues."""
    from src.autonomous_fleet_executor import AutonomousFleetExecutor
    executor = AutonomousFleetExecutor()
    assert len(executor.active_positions) > 0

    kill_res = executor.emergency_kill_switch()
    assert kill_res["success"] is True
    assert kill_res["status"] == "EMERGENCY_FLATTENED"
    assert len(executor.active_positions) == 0

