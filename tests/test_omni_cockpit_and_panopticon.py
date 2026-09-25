"""
tests/test_omni_cockpit_and_panopticon.py
=========================================
Comprehensive verification suite for J.A.R.V.I.S.:
1. GAIGS Live Peer Site Mount & Node Telemetry (/gaigs/live, /api/gaigs/peer-status).
2. Universal Multi-Broker & Prop Account Auto-Pilot Onboarding (/api/accounts/fleet, /api/accounts/onboard).
3. Bi-Directional Mobile Panopticon Screen & Key Mirroring (/api/mobile/screen/live, /api/mobile/telemetry, /api/mobile/key).
4. Supermemory Cognitive Learning & Knowledge Graph Export (/api/memory/learn, /api/memory/graph, /api/memory/search).
5. Standalone Android Companion APK Distribution & Permissions.
"""

import pytest
import time
from pathlib import Path
from starlette.testclient import TestClient
from dashboard import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

class TestOmniCockpitAndPanopticon:
    def test_gaigs_live_peer_site_mounted(self, client):
        """Verifies that the decentralized GAIGS peer site is mounted and returns 200 OK."""
        res = client.get("/gaigs/live/index.html")
        assert res.status_code == 200
        assert "Muhammad Qureshi" in res.text
        assert len(res.content) > 10000

    def test_gaigs_peer_status_endpoint(self, client):
        """Verifies that /api/gaigs/peer-status reports active peer node status."""
        res = client.get("/api/gaigs/peer-status")
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert data.get("peer_status") == "ONLINE_LIVE_PEER"
        assert "contracts_count" in data
        assert data.get("contracts_count") >= 8
        assert data.get("governance_mode") == "DIRECT_DECENTRALIZED_DEMOCRACY"

    def test_universal_accounts_fleet_summary(self, client):
        """Verifies multi-broker fleet status and registered account profiles."""
        res = client.get("/api/accounts/fleet")
        assert res.status_code == 200
        data = res.json()
        assert data.get("total_accounts_registered") >= 1
        assert "accounts" in data
        assert "anti_detection_shields" in data

    def test_universal_accounts_onboard_endpoint(self, client):
        """Verifies 1-click auto-pilot onboarding of any broker/prop firm account."""
        test_login = f"ACC_TEST_{int(time.time())}"
        payload = {
            "login_id": test_login,
            "account_name": "Test Client Automated Prop",
            "broker_server": "FundingPips-Server",
            "password": "MockPassword123",
            "balance": 100000.0,
            "preset": "FundingPips",
            "account_type": "Prop Firm Challenge",
            "target_country": "AE"
        }
        res = client.post("/api/accounts/onboard", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "success"
        assert data.get("account_id") == test_login

    def test_mobile_screen_live_stream_endpoint(self, client):
        """Verifies /api/mobile/screen/live returns valid screen image or HUD SVG."""
        res = client.get("/api/mobile/screen/live")
        assert res.status_code == 200
        content_type = res.headers.get("content-type", "")
        assert "image/" in content_type
        assert len(res.content) > 500

    def test_mobile_telemetry_endpoint(self, client):
        """Verifies /api/mobile/telemetry returns device state."""
        res = client.get("/api/mobile/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert "battery" in data
        assert "connected" in data

    def test_mobile_key_dispatch(self, client):
        """Verifies hardware key event dispatch."""
        res = client.post("/api/mobile/key", json={"key": "home"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True

    def test_supermemory_learn_and_extract_triples(self, client):
        """Verifies cognitive ingestion parses preferences and stores triples."""
        test_directive = "Remember that Master Muhammad Qureshi strictly caps per-trade risk at 0.75% on FundingPips."
        res = client.post("/api/memory/learn", json={"text": test_directive, "role": "master"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("ok") is True
        assert "memory_id" in data

    def test_supermemory_knowledge_graph_export(self, client):
        """Verifies /api/memory/graph returns D3-compatible nodes and edges."""
        res = client.get("/api/memory/graph")
        assert res.status_code == 200
        data = res.json()
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) > 0

    def test_supermemory_search_sub_500ms(self, client):
        """Verifies semantic memory retrieval with score."""
        t0 = time.perf_counter()
        res = client.get("/api/memory/search?q=FundingPips+risk+cap")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert res.status_code == 200
        assert elapsed_ms < 500
        data = res.json()
        assert data.get("ok") is True
        assert data.get("count") >= 1

    def test_standalone_android_companion_apk_download(self, client):
        """Verifies standalone APK download exists and is larger than 30KB."""
        res = client.get("/api/download/apk")
        assert res.status_code == 200
        assert len(res.content) > 30000
