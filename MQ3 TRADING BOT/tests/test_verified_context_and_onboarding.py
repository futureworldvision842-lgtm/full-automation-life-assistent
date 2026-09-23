from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dashboard import app as dashboard_app
from src.multi_account_auto_onboarder import MultiAccountAutoOnboarder
from src.verified_market_context import VerifiedMarketContextEngine


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakePublicSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        del params, timeout
        if url.endswith("/api/v3/depth"):
            return FakeResponse({
                "lastUpdateId": 1,
                "bids": [["100", "5"], ["99", "3"]],
                "asks": [["101", "1"], ["102", "1"]],
            })
        if url.endswith("/api/v3/aggTrades"):
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            return FakeResponse([
                {"p": "100", "q": "2", "T": now_ms, "m": False},
                {"p": "100", "q": "1", "T": now_ms, "m": True},
            ])
        if "72hh-3qpy.json" in url:
            return FakeResponse([{
                "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
                "report_date_as_yyyy_mm_dd": "2026-08-11T00:00:00",
                "open_interest_all": "400000",
                "m_money_positions_long_all": "150000",
                "m_money_positions_short_all": "10000",
            }])
        if url.endswith("press_all.xml"):
            xml = b"""<?xml version='1.0'?><rss><channel><item>
            <title>Federal Reserve issues a policy release</title>
            <link>https://www.federalreserve.gov/example</link>
            <category>Monetary Policy</category>
            <pubDate>Wed, 19 Aug 2026 14:00:00 GMT</pubDate>
            </item></channel></rss>"""
            return FakeResponse(content=xml)
        raise AssertionError(f"Unexpected URL: {url}")


def make_public_engine():
    engine = VerifiedMarketContextEngine(timeout_seconds=1, cache_seconds=60)
    engine._session = FakePublicSession()
    return engine


def test_public_crypto_snapshot_is_single_venue_context_not_whale_attribution():
    result = make_public_engine().crypto_microstructure("BTCUSD")

    assert result["status"] == "AVAILABLE"
    assert result["data_mode"] == "LIVE_PUBLIC_SINGLE_VENUE"
    assert result["depth_imbalance_ratio"] > 0
    assert result["taker_flow_imbalance_ratio"] > 0
    assert result["actionable"] is False
    assert "not a named-whale feed" in result["limitations"]


def test_cftc_context_is_explicitly_weekly_and_non_actionable():
    result = make_public_engine().cftc_positioning("XAUUSD")

    assert result["status"] == "AVAILABLE"
    assert result["data_mode"] == "OFFICIAL_WEEKLY_DELAYED"
    assert result["net_contracts"] == 140000
    assert result["net_pct_open_interest"] == 35.0
    assert result["actionable"] is False
    assert "Tuesday" in result["limitations"]


def test_source_coverage_keeps_global_attribution_and_calendar_unavailable():
    engine = make_public_engine()
    coverage = engine.source_coverage({
        "available": True,
        "data_mode": "BROKER_DEMO",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    })

    by_id = {item["id"]: item for item in coverage["sources"]}
    assert by_id["mt5_broker"]["status"] == "AVAILABLE"
    assert by_id["binance_public"]["status"] == "AVAILABLE"
    assert by_id["cftc_cot"]["status"] == "AVAILABLE"
    assert by_id["federal_reserve_rss"]["status"] == "AVAILABLE"
    assert by_id["global_attributable_order_flow"]["status"] == "UNAVAILABLE"
    assert by_id["global_high_impact_calendar"]["execution_role"] == "REQUIRED_GATE"


def test_whatsapp_onboarding_rejects_secrets_and_registers_metadata_inactive(tmp_path):
    onboarder = MultiAccountAutoOnboarder(str(tmp_path / "fleet.json"))

    secret = onboarder.parse_whatsapp_onboard_directive(
        "onboard account 123456 server FundingPips-Trial balance 5000 type FundingPips password dont-store-me"
    )
    assert secret["success"] is False
    assert "Secret rejected" in secret["message"]
    assert not (tmp_path / "fleet.json").exists()

    result = onboarder.parse_whatsapp_onboard_directive(
        "onboard account 123456 server FundingPips-Trial balance 5000 type FundingPips model FUNDING_PIPS_2_STEP_STANDARD stage EVALUATION_PHASE_1"
    )
    assert result["success"] is True
    account = result["account_data"]
    assert account["is_active"] is False
    assert account["telemetry_verified"] is False
    assert account["execution_mode"] == "PAPER_UNVERIFIED"
    assert account["registration_status"] == "METADATA_REGISTERED_AWAITING_TERMINAL_BINDING"
    saved = (tmp_path / "fleet.json").read_text(encoding="utf-8")
    assert "dont-store-me" not in saved


def test_onboarding_validation_only_claims_match_for_attached_login_and_server(monkeypatch):
    connector = SimpleNamespace(
        get_account_info=lambda: {
            "available": True,
            "login": 40000243427,
            "server": "FundingPips-Trial",
            "data_mode": "BROKER_DEMO",
        }
    )
    monkeypatch.setattr(dashboard_app, "bot_engine", SimpleNamespace(mt5=connector, config={"symbols": ["XAUUSD"]}))
    client = dashboard_app.app.test_client()

    matched = client.post("/api/onboarding/validate", json={
        "account_id": "40000243427",
        "server": "FundingPips-Trial",
        "platform": "FUNDING_PIPS",
    })
    assert matched.status_code == 200
    assert matched.get_json()["broker_session_match"] is True
    assert matched.get_json()["execution_enabled"] is False

    other = client.post("/api/onboarding/validate", json={
        "account_id": "50000999999",
        "server": "FundingPips-Trial",
        "platform": "FUNDING_PIPS",
    })
    assert other.status_code == 200
    assert other.get_json()["broker_session_match"] is False
    assert other.get_json()["registration_mode"] == "PAPER_UNVERIFIED"


def test_frontend_has_source_matrix_and_tab_scoped_required_fields():
    html = (Path(__file__).parents[1] / "dashboard" / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'id="verified-source-panel"' in html
    assert 'id="source-coverage-grid"' in html
    assert 'id="context-cftc"' in html
    assert 'id="context-crypto"' in html
    assert "disabledByPane" in html
    assert "/api/onboarding/validate" in html
    assert "Do not paste secrets into the dashboard" in html


def test_whatsapp_auth_directory_is_absolute_and_status_reports_saved_session():
    source = (Path(__file__).parents[1] / "whatsapp_bridge" / "server.js").read_text(encoding="utf-8")

    assert "fileURLToPath(import.meta.url)" in source
    assert "path.join(BRIDGE_DIR, 'whatsapp_auth')" in source
    assert "saved_session_present" in source
    assert "session_persistence" in source
    assert "bridge_verified_owner: !isGroup" in source


def test_token_authenticated_bridge_owner_lid_is_accepted_but_unproved_lid_is_blocked(monkeypatch):
    class FakeWhatsAppManager:
        bot_engine = None

        @staticmethod
        def handle_incoming_command(command, sender, participant=None, is_group=False):
            del sender, participant, is_group
            return f"handled:{command}"

    monkeypatch.setenv("MQ3_BRIDGE_TOKEN", "unit-test-bridge-token")
    monkeypatch.setattr(dashboard_app, "whatsapp_qr_mgr", FakeWhatsAppManager())
    client = dashboard_app.app.test_client()
    headers = {"X-MQ3-Bridge-Token": "unit-test-bridge-token"}
    owner_lid = "155353362788506@lid"

    accepted = client.post(
        "/api/whatsapp_command",
        headers=headers,
        json={
            "sender": owner_lid,
            "participant": owner_lid,
            "isGroup": False,
            "bridge_verified_owner": True,
            "command": "status",
        },
    )
    assert accepted.status_code == 200
    assert accepted.get_json()["reply"] == "handled:status"

    unproved = client.post(
        "/api/whatsapp_command",
        headers=headers,
        json={
            "sender": owner_lid,
            "participant": owner_lid,
            "isGroup": False,
            "command": "status",
        },
    )
    assert unproved.status_code == 403

    missing_token = client.post(
        "/api/whatsapp_command",
        json={
            "sender": owner_lid,
            "bridge_verified_owner": True,
            "command": "status",
        },
    )
    assert missing_token.status_code == 401
