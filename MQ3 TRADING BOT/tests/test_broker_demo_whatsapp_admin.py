"""Focused acceptance tests for broker-demo telemetry and WhatsApp admin safety."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from dashboard import app as dashboard_app
from src.admin_command_manager import AdminCommandManager
from src.mt5_connector import MT5Connector
from src.whatsapp_qr_manager import WhatsAppQRManager


ROOT = Path(__file__).resolve().parents[1]


def test_connected_demo_account_is_labelled_broker_demo_and_orders_stay_locked(monkeypatch):
    connector = MT5Connector(
        config={
            "execution": {
                "demo_order_execution_enabled": False,
                "require_demo_confirmation_env": True,
            }
        },
        simulation_mode=False,
    )
    connector.connected = True
    demo_account = SimpleNamespace(trade_mode=0)
    monkeypatch.setattr("src.mt5_connector.mt5.account_info", lambda: demo_account)
    order_send = MagicMock()
    monkeypatch.setattr("src.mt5_connector.mt5.order_send", order_send)

    assert connector._broker_data_mode() == "BROKER_DEMO"
    authorized, reason = connector._live_execution_authorized()
    assert authorized is False
    assert "demo order execution is disabled" in reason.lower()
    runtime = connector.get_runtime_status()
    assert runtime["data_mode"] == "BROKER_DEMO"
    assert runtime["live_execution_authorized"] is False

    order = connector.place_order("XAUUSD", "BUY", 0.01, 4350.0, 4340.0, 4370.0)
    assert order["success"] is False
    assert order["mode"] == "BROKER_DEMO_LOCKED"
    assert connector.modify_position(123, 4345.0, 4370.0) is False
    assert connector.close_partial_position(123, 0.01) is False
    assert connector.close_position(123) is False
    assert connector.emergency_close_all() == 0
    order_send.assert_not_called()


def test_admin_memory_and_update_requests_are_audited_without_remote_apply(tmp_path):
    manager = AdminCommandManager(project_root=str(tmp_path))

    remembered = manager.handle(
        "remember Prefer concise Roman Urdu status replies",
        sender="923468053268@s.whatsapp.net",
        is_group=False,
    )
    assert "Memory stored" in remembered
    memory_records = manager._read_jsonl(manager.memory_path)
    assert memory_records[-1]["kind"] == "OPERATOR_MEMORY"
    assert memory_records[-1]["record_hash"]

    rejected_secret = manager.handle(
        "remember API key is abc123",
        sender="923468053268@s.whatsapp.net",
        is_group=False,
    )
    assert "rejected" in rejected_secret.lower()
    assert len(manager._read_jsonl(manager.memory_path)) == 1

    requested = manager.handle(
        "update request add a reviewed Urdu help reply",
        sender="923468053268@s.whatsapp.net",
        is_group=False,
    )
    assert "queued for local review" in requested
    update_records = manager._read_jsonl(manager.request_path)
    assert update_records[-1]["status"] == "PENDING_LOCAL_REVIEW"

    blocked = manager.handle(
        "update apply now",
        sender="923468053268@s.whatsapp.net",
        is_group=False,
    )
    assert "Remote code apply is blocked" in blocked
    assert len(manager._read_jsonl(manager.request_path)) == 1

    group_blocked = manager.handle(
        "system status",
        sender="120363401615322542@g.us",
        is_group=True,
    )
    assert "direct owner chat" in group_blocked


def test_whatsapp_manager_attaches_ephemeral_token_and_has_no_external_fallback(monkeypatch):
    monkeypatch.setenv("MQ3_BRIDGE_TOKEN", "unit-test-bridge-token")
    manager = WhatsAppQRManager.__new__(WhatsAppQRManager)
    manager.BRIDGE_URL = "http://127.0.0.1:3001"
    response = MagicMock(status_code=503)
    post = MagicMock(return_value=response)
    monkeypatch.setattr("src.whatsapp_qr_manager.requests.post", post)

    assert manager.send_message("local test") is False
    assert post.call_args.kwargs["headers"] == {
        "X-MQ3-Bridge-Token": "unit-test-bridge-token"
    }
    source = (ROOT / "src" / "whatsapp_qr_manager.py").read_text(encoding="utf-8")
    assert "callmebot" not in source.lower()


def test_owner_alert_delivery_is_whitelisted_and_uses_bridge_token(monkeypatch):
    monkeypatch.setenv("MQ3_BRIDGE_TOKEN", "owner-alert-token")
    manager = WhatsAppQRManager.__new__(WhatsAppQRManager)
    manager.BRIDGE_URL = "http://127.0.0.1:3001"
    response = MagicMock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {"success": True}
    post = MagicMock(return_value=response)
    monkeypatch.setattr("src.whatsapp_qr_manager.requests.post", post)

    blocked = manager.notify_client_account_update(
        "15555550123", "test", "must not be sent"
    )
    assert blocked["success"] is False
    post.assert_not_called()

    sent = manager.notify_client_account_update(
        "923468053268", "owner research alerts", "local integration test"
    )
    assert sent["success"] is True
    assert post.call_args.kwargs["headers"] == {
        "X-MQ3-Bridge-Token": "owner-alert-token"
    }


def test_whatsapp_webhooks_require_the_memory_only_bridge_token(monkeypatch):
    monkeypatch.setenv("MQ3_BRIDGE_TOKEN", "dashboard-unit-token")
    client = dashboard_app.app.test_client()
    payload = {
        "command": "system status",
        "sender": "923468053268@s.whatsapp.net",
        "isGroup": False,
    }

    assert client.post("/api/whatsapp_command", json=payload).status_code == 401
    assert client.post(
        "/api/whatsapp_command",
        json=payload,
        headers={"X-MQ3-Bridge-Token": "wrong"},
    ).status_code == 401

    qr_manager = MagicMock()
    qr_manager.handle_incoming_command.return_value = "verified reply"
    monkeypatch.setattr(dashboard_app, "whatsapp_qr_mgr", qr_manager)
    response = client.post(
        "/api/whatsapp_command",
        json=payload,
        headers={"X-MQ3-Bridge-Token": "dashboard-unit-token"},
    )
    assert response.status_code == 200
    assert response.get_json()["reply"] == "verified reply"


def test_node_bridge_forwards_the_same_token_to_command_and_audio_webhooks():
    source = (ROOT / "whatsapp_bridge" / "server.js").read_text(encoding="utf-8")

    assert "MQ3_DASHBOARD_BASE_URL" in source
    assert "`${DASHBOARD_BASE_URL}/api/whatsapp_command`" in source
    assert "`${DASHBOARD_BASE_URL}/api/whatsapp_audio`" in source
    assert source.count("'X-MQ3-Bridge-Token': BRIDGE_TOKEN") >= 2


def test_dashboard_trade_cards_and_tickers_use_broker_telemetry_without_mutation(monkeypatch):
    connector = MagicMock()
    connector.get_account_info.return_value = {
        "available": True,
        "data_mode": "BROKER_DEMO",
    }
    connector.get_runtime_status.return_value = {
        "live_execution_authorized": False,
    }
    connector.get_open_positions.return_value = [
        {
            "ticket": 123,
            "symbol": "XAUUSD",
            "type": "BUY",
            "volume": 0.01,
            "price_open": 4340.0,
            "price_current": 4350.0,
            "sl": 4320.0,
            "tp": 4380.0,
            "profit": 10.0,
            "comment": "external-demo-position",
        }
    ]
    connector.get_live_spread.side_effect = lambda symbol: (
        {
            "ask": 4350.2,
            "bid": 4350.0,
            "spread_points": 20.0,
            "data_mode": "BROKER_DEMO",
        }
        if symbol == "XAUUSD"
        else {"ask": None, "bid": None, "data_mode": "UNAVAILABLE"}
    )
    engine = SimpleNamespace(
        mt5=connector,
        config={"jarvis_master": {"position_management_active": False}},
    )
    monkeypatch.setattr(dashboard_app, "bot_engine", engine)
    client = dashboard_app.app.test_client()

    cards = client.get("/api/trade_cards").get_json()
    assert cards["data_mode"] == "BROKER_DEMO"
    assert cards["summary"]["total_open_positions"] == 1
    assert cards["positions"][0]["source"] == "MT5 Broker Position"
    assert cards["positions"][0]["mutation_authorized"] is False
    assert cards["positions"][0]["strategy_attribution"] is None

    tickers = client.get("/api/tickers").get_json()
    assert tickers["ticks"]["XAUUSD"]["available"] is True
    assert tickers["ticks"]["XAUUSD"]["source"] == "MT5 Broker Tick"
    assert tickers["ticks"]["BTCUSD"]["available"] is False

    html = (ROOT / "dashboard" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Math.random() - 0.48" not in html
    assert "POSITION MUTATION LOCKED" in html


def test_research_alert_registration_rejects_non_owner_numbers(monkeypatch):
    monkeypatch.delenv("MQ3_DASHBOARD_CONTROL_TOKEN", raising=False)
    client = dashboard_app.app.test_client()

    response = client.post(
        "/api/subscribe_signals",
        json={
            "name": "Not Owner",
            "phone": "+15555550123",
            "asset_preference": "ALL_ASSETS",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["status"] == "blocked"


def test_connected_whatsapp_page_masks_identity_and_describes_actual_command_boundary(monkeypatch):
    bridge_status = MagicMock()
    bridge_status.json.return_value = {
        "connected": True,
        "user": "923468053268:79@s.whatsapp.net",
        "has_qr": False,
        "qr_image": None,
    }
    monkeypatch.setattr(dashboard_app.requests, "get", MagicMock(return_value=bridge_status))
    client = dashboard_app.app.test_client()

    html = client.get("/whatsapp").get_data(as_text=True)

    assert "WhatsApp Connected — Saved Session" in html
    assert "***3268" in html
    assert "923468053268:79@s.whatsapp.net" not in html
    assert "system status" in html
    assert "update request &lt;change&gt;" in html
    assert "Remote code apply" in html
    assert "Automated trade signals" not in html
