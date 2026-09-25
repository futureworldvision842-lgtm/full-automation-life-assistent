"""
tests/test_mobile_gaigs_integration.py — Mobile Companion GAIGS & Media Studio Integration Tests
================================================================================================
Sovereign Master: Muhammad Qureshi
"""

import pytest
from starlette.testclient import TestClient

from mobile_control import app, _load_mobile_page


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_mobile_page_contains_gaigs_and_media_tabs():
    """Verify that mobile.html contains tabGaigs and all interactive elements."""
    html = _load_mobile_page()
    assert "tabGaigs" in html
    assert "VIRAL SOCIAL MEDIA SCRIPT STUDIO" in html
    assert "GAIGS 5-PILLAR CIVILIZATION ENGINE" in html
    assert "mobMediaChannel" in html
    assert "btnMobGenScript" in html
    assert "mobProposalsContainer" in html
    assert "runMobileEthicsAudit" in html


def test_mobile_endpoint_media_channels(client):
    """Verify that /api/media/channels is accessible via mobile gateway."""
    resp = client.get("/api/media/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "@HistoryOS-1" in [ch["handle"] for ch in data["channels"].values()]


def test_mobile_endpoint_gaigs_overview(client):
    """Verify that /api/gaigs/overview is accessible via mobile gateway."""
    resp = client.get("/api/gaigs/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OPERATIONAL"
    assert "Muhammad Qureshi" in data["sovereign_founder"]


def test_mobile_endpoint_generate_and_approve_script(client):
    """Verify viral script generation and approval on mobile."""
    gen_resp = client.post("/api/media/generate_script", json={
        "channel": "@TheTimelineReset",
        "language": "english",
        "hook_style": "shocking_twist",
        "topic": "The Day Rome Never Fell",
        "on_this_day": False
    })
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["ok"] is True
    script = gen_data["script"]
    script_id = script.get("script_id") or script.get("id")
    assert script_id is not None

    # Approve script via mobile 1-tap "Yeh Dabao"
    appr_resp = client.post("/api/media/approve_script", json={
        "script_id": script_id,
        "decision": "APPROVED_YEH_DABAO"
    })
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["ok"] is True


def test_mobile_endpoint_gaigs_voting(client):
    """Verify direct democracy voting on mobile with SHA-256 receipt."""
    # First get proposals
    p_resp = client.get("/api/gaigs/proposals")
    assert p_resp.status_code == 200
    proposals = p_resp.json()["proposals"]
    assert len(proposals) > 0
    prop_id = proposals[0].get("proposal_id") or proposals[0].get("id")

    # Vote FOR
    vote_resp = client.post("/api/gaigs/vote", json={
        "proposal_id": prop_id,
        "voter_id": "TEST_MOBILE_USER_99",
        "choice": "FOR"
    })
    assert vote_resp.status_code == 200
    vdata = vote_resp.json()
    assert vdata["ok"] is True
    assert "vote_receipt" in vdata or "vote_receipt_hash" in vdata


def test_mobile_endpoint_ethics_evaluation(client):
    """Verify Islamic ethics evaluation on mobile."""
    eth_resp = client.post("/api/gaigs/ethics/evaluate", json={
        "proposal_text": "Zero-interest Islamic community cooperative fund with mutual aid and shura consultation."
    })
    assert eth_resp.status_code == 200
    edata = eth_resp.json()
    assert edata["ok"] is True
    assert edata["evaluation"]["verdict"] in ["ETHICAL_APPROVED", "CONDITIONALLY_ACCEPTABLE"]
    assert edata["evaluation"]["composite_score"] >= 60.0
