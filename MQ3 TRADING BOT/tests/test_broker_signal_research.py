from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.broker_signal_research import BrokerSignalResearchEngine
from src.signal_decision_manager import SignalDecisionManager


class FakeConnector:
    def __init__(self, direction="up", open_positions=0, equity=50000.0):
        self.direction = direction
        self.open_positions = open_positions
        self.equity = equity
        self.order_calls = 0

    def get_historical_candles(self, symbol, timeframe, count=260):
        size = max(count, 270)
        if self.direction == "up":
            close = np.linspace(100.0, 130.0, size)
            open_ = close - 0.12
        elif self.direction == "down":
            close = np.linspace(130.0, 100.0, size)
            open_ = close + 0.12
        else:
            close = np.full(size, 115.0)
            open_ = close.copy()
        return pd.DataFrame(
            {
                "time": pd.date_range(
                    end=pd.Timestamp.now(tz="UTC").floor("5min"), periods=size, freq="5min"
                ),
                "open": open_,
                "high": np.maximum(open_, close) + 0.25,
                "low": np.minimum(open_, close) - 0.25,
                "close": close,
                "tick_volume": np.linspace(100, 180, size),
                "real_volume": np.zeros(size),
            }
        )

    def get_live_spread(self, symbol):
        now = datetime.now(timezone.utc).isoformat()
        midpoint = 130.0 if self.direction == "up" else 100.0 if self.direction == "down" else 115.0
        return {
            "bid": midpoint - 0.05,
            "ask": midpoint + 0.05,
            "spread_points": 10.0,
            "spread_pips": 1.0,
            "is_normal": True,
            "data_mode": "BROKER_DEMO",
            "observed_at": now,
            "age_seconds": 0.05,
        }

    def get_account_info(self):
        return {
            "available": True,
            "login": 12345678,
            "server": "Test-Demo",
            "equity": self.equity,
            "currency": "USD",
            "data_mode": "BROKER_DEMO",
        }

    def get_open_positions(self):
        return [{"ticket": i} for i in range(self.open_positions)]

    def get_symbol_spec(self, symbol):
        return {
            "digits": 2,
            "volume_min": 0.01,
            "volume_step": 0.01,
            "volume_max": 100.0,
            "trade_tick_size": 0.01,
            "trade_tick_value": 1.0,
            "trade_tick_value_loss": 1.0,
        }

    def order_send(self, *args, **kwargs):
        self.order_calls += 1
        raise AssertionError("research must never place an order")


def make_config():
    return {
        "risk_management": {
            "risk_per_trade_pct": 0.25,
            "max_open_trades": 3,
            "gold_atr_sl_multiplier": 2.5,
            "forex_atr_sl_multiplier": 1.5,
        }
    }


def test_uptrend_produces_broker_backed_candidate_but_never_execution_ready():
    connector = FakeConnector("up")
    result = BrokerSignalResearchEngine(connector, make_config()).analyze("XAUUSD")

    assert result["status"] == "research_ready"
    assert result["decision"] == "BUY_CANDIDATE"
    assert result["direction"] == "BUY"
    assert result["data_mode"] == "BROKER_DEMO"
    assert result["actionable"] is False
    assert result["execution_ready"] is False
    assert result["news_clearance"]["status"] == "UNVERIFIED"
    assert result["order_flow"]["status"] == "UNAVAILABLE"
    assert result["institution_attribution"]["status"] == "UNAVAILABLE"
    assert "not a calibrated win probability" in result["confidence_note"]
    assert connector.order_calls == 0


def test_downtrend_is_scored_symmetrically():
    result = BrokerSignalResearchEngine(FakeConnector("down"), make_config()).analyze("XAUUSD")
    assert result["decision"] == "SELL_CANDIDATE"
    assert result["direction"] == "SELL"
    assert result["sell_score"] > result["buy_score"]
    assert result["plan"]["stop_loss"] > result["plan"]["entry_reference"]


def test_range_wait_has_no_order_levels_or_calibrated_probability():
    result = BrokerSignalResearchEngine(FakeConnector("range"), make_config()).analyze("XAUUSD")
    assert result["decision"] == "WAIT"
    assert result["direction"] is None
    assert result["plan"]["stop_loss"] is None
    assert result["owner_decision_required"] is False
    assert all(scenario["probability"] is None for scenario in result["scenarios"])


def test_account_cap_blocks_suitability_and_lot_is_never_forced():
    connector = FakeConnector("up", open_positions=3, equity=1.0)
    result = BrokerSignalResearchEngine(connector, make_config()).analyze("XAUUSD")
    account = result["account_suitability"]
    assert account["verdict"] == "DO_NOT_TAKE_NOW"
    assert account["calculated_lots"] is None
    assert any("Open-position cap reached" in reason for reason in account["reasons"])
    assert any("no forced minimum lot" in reason for reason in account["reasons"])


def test_what_if_uses_broker_baseline_but_returns_no_probability_or_profit():
    engine = BrokerSignalResearchEngine(FakeConnector("up"), make_config())
    result = engine.simulate("XAUUSD", 2.0)
    assert result["status"] == "scenario_only"
    assert result["data_mode"] == "HYPOTHETICAL_FROM_BROKER_BASELINE"
    assert result["hypothetical_price"] > result["baseline_price"]
    assert result["probability"] is None
    assert result["estimated_profit"] is None
    assert result["actionable"] is False


def test_multi_asset_scan_ranks_configured_symbols_without_execution():
    connector = FakeConnector("up")
    scan = BrokerSignalResearchEngine(connector, make_config()).scan(["XAUUSD", "EURUSD", "XAUUSD"])
    assert scan["status"] == "research_scan"
    assert scan["coverage"] == {"configured": 2, "research_ready": 2, "unavailable": 0}
    assert [row["symbol"] for row in scan["results"]] == ["XAUUSD", "EURUSD"]
    assert all(row["execution_ready"] is False for row in scan["results"])
    assert connector.order_calls == 0


def test_multi_asset_scan_isolates_a_symbol_with_missing_quote():
    class PartiallyUnavailableConnector(FakeConnector):
        def get_live_spread(self, symbol):
            if symbol == "BTCUSD":
                return {
                    "bid": None, "ask": None, "is_normal": False,
                    "data_mode": "UNAVAILABLE", "age_seconds": None,
                }
            return super().get_live_spread(symbol)

    connector = PartiallyUnavailableConnector("up")
    scan = BrokerSignalResearchEngine(connector, make_config()).scan(["XAUUSD", "BTCUSD"])
    assert scan["coverage"] == {"configured": 2, "research_ready": 1, "unavailable": 1}
    btc = next(row for row in scan["results"] if row["symbol"] == "BTCUSD")
    assert btc["status"] == "unavailable"
    assert btc["decision"] == "WAIT"
    assert btc["bid"] is None


def test_stale_quote_fails_closed():
    connector = FakeConnector("up")
    original = connector.get_live_spread

    def stale(symbol):
        result = original(symbol)
        result["age_seconds"] = 30.0
        return result

    connector.get_live_spread = stale
    result = BrokerSignalResearchEngine(connector, make_config()).analyze("XAUUSD")
    assert result["execution_ready"] is False
    assert any("stale" in blocker.lower() for blocker in result["blockers"])


def test_decision_receipt_records_yes_but_sends_no_order(tmp_path):
    connector = FakeConnector("up")
    signal = BrokerSignalResearchEngine(connector, make_config()).analyze("XAUUSD")
    manager = SignalDecisionManager(str(tmp_path / "decisions.jsonl"))

    approved = manager.record(signal, "YES")
    rejected = manager.record(signal, "NO")

    assert approved["status"] == "APPROVAL_RECORDED_EXECUTION_BLOCKED"
    assert approved["order_sent"] is False
    assert rejected["status"] == "REJECTED_NO_ORDER"
    assert rejected["order_sent"] is False
    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert connector.order_calls == 0


def test_dashboard_signal_and_what_if_endpoints_are_research_only(monkeypatch, tmp_path):
    import dashboard.app as dashboard_app

    class FakeBot:
        mt5 = FakeConnector("up")
        config = {**make_config(), "symbols": ["XAUUSD"]}

    monkeypatch.delenv("MQ3_DASHBOARD_CONTROL_TOKEN", raising=False)
    monkeypatch.setattr(dashboard_app, "bot_engine", FakeBot())
    monkeypatch.setattr(dashboard_app, "signal_research_engine", None)
    monkeypatch.setattr(
        dashboard_app,
        "verified_market_context",
        type("FakeContext", (), {"symbol_context": staticmethod(lambda symbol: {
            "status": "AVAILABLE", "symbol": symbol, "actionable": False, "available_sources": 1,
        })})(),
    )
    monkeypatch.setattr(
        dashboard_app,
        "signal_decision_manager",
        SignalDecisionManager(str(tmp_path / "dashboard-decisions.jsonl")),
    )
    client = dashboard_app.app.test_client()

    signal_response = client.get("/api/signal_research?symbol=XAUUSD")
    assert signal_response.status_code == 200
    signal = signal_response.get_json()
    assert signal["decision"] == "BUY_CANDIDATE"
    assert signal["execution_ready"] is False
    assert signal["verified_public_context"]["actionable"] is False
    assert signal["public_context_execution_role"] == "DISPLAY_ONLY_NOT_SCORED"

    indicator_response = client.get("/api/indicator_ensemble?symbol=XAUUSD&timeframe=M15")
    assert indicator_response.status_code == 200
    indicator = indicator_response.get_json()
    assert indicator["status"] == "AVAILABLE"
    assert indicator["symbol"] == "XAUUSD"
    assert indicator["timeframe"] == "M15"
    assert indicator["forming_bar_used"] is False
    assert indicator["actionable"] is False
    assert indicator["execution_ready"] is False

    scan_response = client.get("/api/signal_scan")
    assert scan_response.status_code == 200
    scan = scan_response.get_json()
    assert scan["coverage"]["configured"] == 1
    assert scan["results"][0]["symbol"] == "XAUUSD"
    assert scan["results"][0]["execution_ready"] is False

    scenario_response = client.post("/api/simulate_what_if", json={"symbol": "XAUUSD", "shock_pct": 0.5})
    assert scenario_response.status_code == 200
    scenario = scenario_response.get_json()
    assert scenario["probability"] is None
    assert scenario["actionable"] is False

    decision_response = client.post(
        "/api/signal_decision",
        json={"symbol": "XAUUSD", "signal_id": signal["signal_id"], "decision": "YES"},
    )
    assert decision_response.status_code == 200
    decision = decision_response.get_json()
    assert decision["order_sent"] is False
    assert decision["status"] == "APPROVAL_RECORDED_EXECUTION_BLOCKED"


def test_whatsapp_signal_uses_same_broker_research_and_yes_is_not_an_order(tmp_path):
    from src.whatsapp_qr_manager import WhatsAppQRManager

    class FakeBot:
        mt5 = FakeConnector("up")
        config = make_config()

    manager = WhatsAppQRManager(bot_engine=FakeBot())
    manager.signal_decisions = SignalDecisionManager(str(tmp_path / "wa-decisions.jsonl"))
    manager.verified_market_context = type("FakeContext", (), {"symbol_context": staticmethod(lambda symbol: {
        "status": "AVAILABLE",
        "symbol": symbol,
        "cftc_positioning": {
            "status": "AVAILABLE", "category": "Managed Money", "net_contracts": 140000,
            "net_pct_open_interest": 35.0, "observed_at": "2026-08-11T00:00:00+00:00",
        },
        "crypto_microstructure": {"status": "UNAVAILABLE"},
        "official_policy_news": {
            "status": "AVAILABLE", "releases": [{"title": "Official policy release"}],
        },
    })})()
    sender = "923468053268@s.whatsapp.net"

    signal_reply = manager.handle_incoming_command("signal XAUUSD", sender)
    assert "BROKER SIGNAL RESEARCH" in signal_reply
    assert "VERIFIED PUBLIC CONTEXT (NOT SCORED)" in signal_reply
    assert "CFTC Managed Money" in signal_reply
    assert "display-only" in signal_reply
    assert "Named bank/fund/whale attribution: *UNAVAILABLE*" in signal_reply
    assert "not win probability" in signal_reply

    approval_reply = manager.handle_incoming_command("YES", sender)
    assert "no order was created" in approval_reply.lower()
    assert "Order sent: NO" in approval_reply
    assert manager.bot_engine.mt5.order_calls == 0

    scan_reply = manager.handle_incoming_command("scan market", sender)
    assert "CONFIGURED BROKER MARKET RESEARCH SCAN" in scan_reply
    assert "No scan result is an order" in scan_reply


def test_frontend_exposes_signal_evidence_scenarios_and_explicit_decision_boundary():
    from pathlib import Path

    html = (Path(__file__).parents[1] / "dashboard" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="signal-research-desk"' in html
    assert 'id="signal-evidence"' in html
    assert 'id="signal-blockers"' in html
    assert 'id="signal-scenarios"' in html
    assert 'id="signal-scan-strip"' in html
    assert "Evidence score (not probability)" in html
    assert "YES — record reviewed approval" in html
    assert "YES never bypasses execution gates" in html


def test_mt5_broker_server_bar_time_is_normalized_to_utc(monkeypatch):
    import src.mt5_connector as mt5_module

    broker_wall_clock_epoch = int(datetime(2026, 8, 19, 16, 45, tzinfo=timezone.utc).timestamp())
    rates = np.array(
        [(broker_wall_clock_epoch, 1.0, 1.2, 0.9, 1.1, 100, 10, 0)],
        dtype=[
            ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"),
            ("close", "f8"), ("tick_volume", "i8"), ("spread", "i4"), ("real_volume", "i8"),
        ],
    )

    class FakeMt5Module:
        TIMEFRAME_M15 = 15

        @staticmethod
        def copy_rates_from_pos(symbol, timeframe, start, count):
            return rates

    monkeypatch.setattr(mt5_module, "MT5_AVAILABLE", True)
    monkeypatch.setattr(mt5_module, "mt5", FakeMt5Module())
    connector = mt5_module.MT5Connector(
        {"prop_rules": {"server_timezone": "UTC+03:00"}}, simulation_mode=False
    )
    connector.connected = True

    frame = connector.get_historical_candles("XAUUSD", "M15", 1)
    assert str(frame.iloc[0]["time"]) == "2026-08-19 13:45:00+00:00"
