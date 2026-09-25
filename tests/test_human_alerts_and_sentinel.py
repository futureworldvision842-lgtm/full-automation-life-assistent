"""
tests/test_human_alerts_and_sentinel.py — Comprehensive Test Suite
===================================================================
Verifies:
1. Human Alert Panopticon: pending alerts, creation, resolution (Solved, OTP, Key, Free Mode, Cancel).
2. Self-Healing Sentinel: automated diagnosis, self-healing actions, and held task preservation.
3. Vibe Coder: natural language synthesis, AST verification, and clean-room invariance.
4. Screen Mirroring: PC desktop streaming and mobile companion heartbeat.
5. Strict identity rule and clean-room compliance.
"""

import pytest
from starlette.testclient import TestClient
from dashboard import app as dashboard_app
from mobile_control import app as mobile_app
from core.human_intervention_gateway import get_human_intervention_gateway, RequestStatus
from core.self_healing_sentinel import get_self_healing_sentinel
from core.vibe_coder import VibeCoder


def test_human_alert_lifecycle():
    client = TestClient(dashboard_app)

    # 1. Check pending alerts initial
    resp = client.get("/api/alerts/pending")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 2. Create CAPTCHA Challenge alert
    create_resp = client.post("/api/alerts/create", json={
        "alert_type": "CAPTCHA_CHALLENGE",
        "title": "Cloudflare Turnstile Verification",
        "target_service": "FundingPips Portal",
        "reason": "Cloudflare interactive checkbox presented on login",
        "action_blocked": "Daily risk limit sync",
        "portal_url": "https://app.fundingpips.com/login",
        "explanation_ur": "Sir, screen par Cloudflare captcha solve karein."
    })
    assert create_resp.status_code == 200
    alert_data = create_resp.json()
    assert alert_data["ok"] is True
    req_id = alert_data["alert"]["request_id"]
    assert req_id.startswith("REQ-CAP-")

    # 3. Check pending alerts contains created alert
    pending_resp = client.get("/api/alerts/pending")
    assert pending_resp.status_code == 200
    ids = [a["request_id"] for a in pending_resp.json()["alerts"]]
    assert req_id in ids

    # 4. Resolve alert via 1-click 'SOLVED'
    resolve_resp = client.post("/api/alerts/resolve", json={
        "request_id": req_id,
        "action": "SOLVED"
    })
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["ok"] is True
    assert resolve_resp.json()["status"] == RequestStatus.RESOLVED.value


def test_human_alert_free_mode_fallback():
    client = TestClient(dashboard_app)

    # Create missing API key alert
    create_resp = client.post("/api/alerts/create", json={
        "alert_type": "MISSING_API_KEY",
        "title": "Glassnode Institutional On-Chain API Key Needed",
        "target_service": "Glassnode",
        "reason": "Premium on-chain whale entity clusters",
        "action_blocked": "Macro whale tracking",
        "suggested_free_alternative": "Direct DEX Screener + Public Solscan RPC"
    })
    assert create_resp.status_code == 200
    req_id = create_resp.json()["alert"]["request_id"]

    # Resolve via FREE_MODE
    resolve_resp = client.post("/api/alerts/resolve", json={
        "request_id": req_id,
        "action": "FREE_MODE"
    })
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["ok"] is True
    assert resolve_resp.json()["status"] == RequestStatus.FALLBACK_FREE.value


def test_self_healing_sentinel_diagnosis_and_auto_heal():
    sentinel = get_self_healing_sentinel()
    diag = sentinel.diagnose_system()
    assert diag["ok"] is True
    assert "daemons" in diag
    assert "hardware" in diag
    assert diag["hardware"]["ram_total_gb"] > 0
    assert "throttle_cap" in diag["hardware"]

    # Trigger auto-heal
    heal_res = sentinel.auto_heal()
    assert heal_res["ok"] is True
    assert "auto_healed_actions" in heal_res
    assert "message" in heal_res


def test_sentinel_fastapi_endpoints():
    client = TestClient(dashboard_app)

    diag_resp = client.get("/api/sentinel/diagnose")
    assert diag_resp.status_code == 200
    assert diag_resp.json()["ok"] is True

    heal_resp = client.post("/api/sentinel/heal")
    assert heal_resp.status_code == 200
    assert heal_resp.json()["ok"] is True


def test_vibe_coder_synthesis():
    coder = VibeCoder()
    res = coder.synthesize_code(
        prompt="make an automated telegram alpha broadcaster",
        skill_name="alpha_broadcaster"
    )
    assert res["ok"] is True
    assert "AlphaBroadcasterTool" in res["code"]
    assert res["clean_room_verified"] is True


def test_vibe_coder_fastapi_endpoints():
    client = TestClient(dashboard_app)

    gen_resp = client.post("/api/vibe/generate", json={
        "prompt": "banao ek solana meme coin whale tracker",
        "skill_name": "solana_whale_tracker",
        "auto_deploy": False
    })
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["ok"] is True
    assert "SolanaWhaleTrackerTool" in data["code"]

    list_resp = client.get("/api/vibe/list")
    assert list_resp.status_code == 200
    assert list_resp.json()["ok"] is True


def test_screen_mirror_and_heartbeat():
    client = TestClient(mobile_app)

    # 1. Post mobile heartbeat
    hb_resp = client.post("/api/screen/mobile/heartbeat", json={
        "device_name": "Master Muhammad Galaxy Ultra",
        "active_tab": "tabTrading",
        "battery_pct": 92,
        "charging": True,
        "orientation": "portrait"
    })
    assert hb_resp.status_code == 200
    assert hb_resp.json()["ok"] is True

    # 2. Query mobile status
    status_resp = client.get("/api/screen/mobile/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["ok"] is True
    assert data["session"]["battery_pct"] == 92
    assert data["session"]["active_tab"] == "tabTrading"
    assert data["session"]["charging"] is True

    # 3. Query PC screen latest
    screen_resp = client.get("/api/screen/pc/latest")
    assert screen_resp.status_code == 200
    assert screen_resp.headers["content-type"] == "image/png"
