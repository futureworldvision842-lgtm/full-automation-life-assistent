"""
tests/test_dashboard_sovereign_routes.py
=========================================
Verification for newly added OpenDroid, Dimos, and Consensus routes in dashboard.py (:8770).
"""

import pytest
from starlette.testclient import TestClient
import dashboard
from mobile.opendroid_bridge import get_opendroid_bridge

@pytest.fixture
def client():
    return TestClient(dashboard.app, base_url="http://127.0.0.1:8770")


class TestDashboardSovereignRoutes:
    def test_approval_verify_via_browser_and_json(self, client):
        bridge = get_opendroid_bridge()
        token = bridge.create_verification_request(
            action_type="TEST_TRADE_VERIFICATION",
            summary_en="Verify execution for 0.5% risk Gold order",
            summary_urdu="Gold order verify karein",
        )

        # 1. Test HTML rendering (browser one-tap "Yeh Dabao")
        html_resp = client.get(
            f"/api/approval/verify/{token.token_id}?decision=approve",
            headers={"Accept": "text/html"}
        )
        assert html_resp.status_code == 200
        assert "APPROVED &amp; VERIFIED" in html_resp.text or "APPROVED & VERIFIED" in html_resp.text
        assert "Master Muhammad Qureshi" in html_resp.text
        assert token.token_id in html_resp.text

        # Secondary verify should return 400 (already approved)
        json_resp = client.get(
            f"/api/approval/verify/{token.token_id}?decision=approve",
            headers={"Accept": "application/json"}
        )
        assert json_resp.status_code == 400
        assert json_resp.json()["status"] == "APPROVED"

    def test_approval_pending_endpoint(self, client):
        resp = client.get("/api/approval/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert isinstance(data["pending"], list)

    def test_mobile_opendroid_status_endpoint(self, client):
        resp = client.get("/api/mobile/opendroid/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["status"]["owner"] == "Master Muhammad Qureshi"
        assert data["status"]["bridge"] == "OpenDroid_ADB_v2"

    def test_mobile_opendroid_action_endpoint(self, client):
        resp = client.post("/api/mobile/opendroid/action", json={"action": "tap", "x": 400, "y": 600})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["result"]["success"] is True

    def test_dimos_vitals_endpoint(self, client):
        resp = client.get("/api/dimos/vitals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "cpu_percent" in data["vitals"]
        assert len(data["devices"]) >= 4

    def test_consensus_debate_endpoint(self, client):
        proposal = {
            "proposal_id": "PROP-DASH-01",
            "symbol": "XAUUSD",
            "action": "BUY",
            "price": 2650.0,
            "stop_loss": 2640.0,
            "take_profit": 2680.0,
            "risk_pct": 0.50,
            "risk_usd": 500.0,
            "rr_ratio": 3.0,
        }
        context = {
            "indicators": {"rsi": 52.0, "trend": "BULLISH", "cvd_delta": 300.0, "ote_discount": True},
            "spread_bps": 1.0,
            "minutes_to_high_impact_news": 60.0,
        }
        resp = client.post("/api/consensus/debate", json={"proposal": proposal, "context": context})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["result"]["approved"] is True
        assert data["result"]["status"] == "APPROVED_HIGH_CONVICTION"

    def test_zero_prohibited_identifer(self, client):
        resp = client.get("/api/dimos/vitals")
        dump = str(resp.json()).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump
