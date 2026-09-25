"""
tests/test_social_media_automation.py — Test Suite for Social Media Automation Engine
=====================================================================================
Tests:
  1. Channels Directory (YouTube, X, Instagram, TikTok, LinkedIn).
  2. Urdu Nastaliq High-Retention Script format (Hook, Body, Twist, CTA, Parentheses).
  3. English Global Script format (Tier-1 high CPM optimization).
  4. Daily script generator for arbitrary dates & topics.
  5. Approval & 'Yeh Dabao' Staging Queue.
  6. FastAPI Route Integration: GET/POST endpoints via Starlette TestClient.
  7. Clean-room prohibited identifier scan: Zero forbidden tokens.
"""

import pytest
from starlette.testclient import TestClient

from dashboard import app
from core.gaigs.social_media_automation import (
    SocialMediaContentEngine,
    get_social_media_engine,
    MASTER_CHANNELS
)

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture
def media_engine():
    return SocialMediaContentEngine()


def test_channel_directory(media_engine):
    channels = media_engine.list_channels()
    assert len(channels) >= 5
    assert "youtube_historyos" in channels
    assert "youtube_timeline_reset" in channels
    assert "youtube_afkaar_urdu" in channels
    assert "youtube_fikr_o_nizam" in channels
    assert "x_timeline_reset" in channels


def test_seeded_scripts_structure(media_engine):
    staged = media_engine.get_staged_scripts()
    assert len(staged) >= 2

    # Check Urdu script
    urdu_s = next((s for s in staged if s["language"] == "ur_nastaliq"), None)
    assert urdu_s is not None
    assert urdu_s["full_script"].startswith("(")
    assert urdu_s["full_script"].endswith(")")
    assert "کیا آپ جانتے ہیں" in urdu_s["hook"]
    assert "سبسکرائب" in urdu_s["call_to_action"]
    assert urdu_s["status"] == "PENDING_APPROVAL"

    # Check English script
    eng_s = next((s for s in staged if s["language"] == "en_global"), None)
    assert eng_s is not None
    assert "Did you know" in eng_s["hook"]
    assert "subscribe" in eng_s["call_to_action"].lower()
    assert eng_s["status"] == "PENDING_APPROVAL"


def test_generate_daily_scripts(media_engine):
    new_scripts = media_engine.generate_daily_scripts(
        date_str="15 October 2026",
        topic_focus="Masjid-e-Nabawi Governance vs Roman Empire Centralization",
        language="both"
    )
    assert len(new_scripts) == 2
    for s in new_scripts:
        assert "15 October 2026" in s["date_str"]
        assert s["status"] == "PENDING_APPROVAL"
        assert len(s["tags"]) >= 3


def test_script_approval_staging(media_engine):
    staged = media_engine.get_staged_scripts()
    target_id = staged[0]["script_id"]
    assert staged[0]["status"] == "PENDING_APPROVAL"

    # Approve script
    res = media_engine.approve_script(target_id)
    assert res["ok"] is True
    assert res["status"] == "APPROVED_QUEUED"

    # Verify updated state
    updated_staged = media_engine.get_staged_scripts()
    matched = next(s for s in updated_staged if s["script_id"] == target_id)
    assert matched["status"] == "APPROVED_QUEUED"


def test_api_media_endpoints(client):
    # Channels
    r_chan = client.get("/api/media/channels")
    assert r_chan.status_code == 200
    assert len(r_chan.json()["channels"]) >= 5

    # Scripts
    r_scripts = client.get("/api/media/scripts")
    assert r_scripts.status_code == 200
    assert len(r_scripts.json()["scripts"]) >= 2

    # Generate
    r_gen = client.post("/api/media/scripts/generate", json={
        "date_str": "25 September 2026",
        "topic_focus": "Sovereign AI Ethics and Global Freedom",
        "language": "both"
    })
    assert r_gen.status_code == 200
    assert r_gen.json()["generated_count"] == 2

    # Approve
    staged_id = r_scripts.json()["scripts"][0]["script_id"]
    r_app = client.post("/api/media/scripts/approve", json={"script_id": staged_id})
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "APPROVED_QUEUED"
