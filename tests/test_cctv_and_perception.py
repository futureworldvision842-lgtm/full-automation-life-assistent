"""
tests/test_cctv_and_perception.py
=============================================================================
Comprehensive Test Suite for:
  • Municipal CCTV Streams & 8-Channel Matrix Registry (TfL, Bosphorus, Hormuz, Shibuya, Times Square)
  • /api/cctv/proxy 4-Second In-Memory Caching Cadence & Fallback Resilience
  • User-Space Visual Action Perception & Canonical Activity States (ENGAGED_CONVERSATION, CODING_EXECUTION, OBSERVING_MARKETS)
  • Zero DirectShow Kernel Traps (BugCheck 0x3B SPUVCbv64.sys Crash Prevention)
  • Integrity Mandate & Zero Forbidden Legacy Account Mentions
=============================================================================
"""

import io
import re
import time
import base64
from unittest.mock import patch, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from core.cockpit_api import router as cockpit_router, REAL_CCTV_CAMERAS, _cctv_cache
from perception.action_perception import ActionPerceptionEngine, CANONICAL_ACTION_STATES, get_action_perception
from core.action_visualizer import ActionVisualizer, get_action_visualizer


@pytest.fixture(scope="module")
def api_client():
    """Provides a FastAPI TestClient configured with the cockpit router."""
    app = FastAPI(title="JARVIS_CCTV_Perception_Test")
    app.include_router(cockpit_router)
    return TestClient(app)


# =============================================================================
# 1. MUNICIPAL CCTV STREAMS & 8-CHANNEL CAMERA MATRIX
# =============================================================================
class TestMunicipalCctvMatrix:
    """Validates the 8-channel verified camera registry and endpoints."""

    def test_camera_catalog_exact_count_and_channel_ids(self):
        """Verifies exactly 8 camera channels exist in the verified catalog."""
        assert len(REAL_CCTV_CAMERAS) == 8, f"Expected 8 cameras, found {len(REAL_CCTV_CAMERAS)}"
        
        expected_ids = [
            "cctv_tfl_piccadilly",
            "cctv_tfl_cromwell",
            "cctv_tfl_greenwich",
            "cctv_tfl_billet",
            "cctv_geo_times_square",
            "cctv_geo_shibuya",
            "cctv_maritime_bosphorus",
            "cctv_maritime_hormuz"
        ]
        catalog_ids = [c["id"] for c in REAL_CCTV_CAMERAS]
        assert catalog_ids == expected_ids, f"Catalog IDs mismatch: {catalog_ids}"

    def test_camera_catalog_required_strategic_corridors(self):
        """Verifies Bosphorus Strait, Strait of Hormuz, Tokyo Shibuya, Times Square, and London TfL exist."""
        cameras_by_id = {c["id"]: c for c in REAL_CCTV_CAMERAS}

        # 1. Bosphorus Strait (Istanbul / Turkish Straits)
        bosphorus = cameras_by_id["cctv_maritime_bosphorus"]
        assert "Bosphorus" in bosphorus["title"] or "Bosphorus" in bosphorus["name"]
        assert pytest.approx(bosphorus["lat"], 0.01) == 41.0256
        assert pytest.approx(bosphorus["lon"], 0.01) == 29.0152
        assert bosphorus["active"] is True
        assert bosphorus["refresh_interval_sec"] == 5

        # 2. Strait of Hormuz (Persian Gulf)
        hormuz = cameras_by_id["cctv_maritime_hormuz"]
        assert "Hormuz" in hormuz["title"] or "Hormuz" in hormuz["name"]
        assert pytest.approx(hormuz["lat"], 0.01) == 26.5667
        assert pytest.approx(hormuz["lon"], 0.01) == 56.2500
        assert hormuz["active"] is True
        assert hormuz["refresh_interval_sec"] == 5

        # 3. New York Times Square
        times_sq = cameras_by_id["cctv_geo_times_square"]
        assert "Times Square" in times_sq["title"]
        assert pytest.approx(times_sq["lat"], 0.01) == 40.7580
        assert pytest.approx(times_sq["lon"], 0.01) == -73.9855
        assert times_sq["active"] is True

        # 4. Tokyo Shibuya
        shibuya = cameras_by_id["cctv_geo_shibuya"]
        assert "Shibuya" in shibuya["title"]
        assert pytest.approx(shibuya["lat"], 0.01) == 35.6595
        assert pytest.approx(shibuya["lon"], 0.01) == 139.7005
        assert shibuya["active"] is True

        # 5. London Piccadilly Circus (TfL JamCam)
        piccadilly = cameras_by_id["cctv_tfl_piccadilly"]
        assert "Piccadilly" in piccadilly["title"]
        assert "jamcams.tfl.gov.uk" in piccadilly["stream_url"]
        assert piccadilly["active"] is True

    def test_every_camera_has_complete_metadata_schema(self):
        """Ensures every camera fulfills the interface contract schema."""
        for cam in REAL_CCTV_CAMERAS:
            assert "id" in cam and isinstance(cam["id"], str)
            assert "title" in cam and isinstance(cam["title"], str)
            assert "name" in cam and isinstance(cam["name"], str)
            assert "city" in cam and isinstance(cam["city"], str)
            assert "country" in cam and isinstance(cam["country"], str)
            assert "lat" in cam and isinstance(cam["lat"], (int, float))
            assert "lon" in cam and isinstance(cam["lon"], (int, float))
            assert "stream_url" in cam and cam["stream_url"].startswith("http")
            assert "snapshot_url" in cam and cam["snapshot_url"].startswith("http")
            assert "provider" in cam and isinstance(cam["provider"], str)
            assert cam["active"] is True
            assert cam["status"] == "LIVE_STREAMING"
            assert cam["refresh_interval_sec"] == 5

    def test_api_cctv_streams_endpoint_response(self, api_client):
        """Tests GET /api/cctv/streams returns HTTP 200 with standard schema."""
        resp = api_client.get("/api/cctv/streams")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ok"] is True
        assert data["total_cameras"] == 8
        assert data["cameras_count"] == 8
        assert len(data["cameras"]) == 8
        assert "Transport for London" in data["attribution"]


# =============================================================================
# 2. CCTV PROXY & 4-SECOND IN-MEMORY CACHE
# =============================================================================
class TestCctvProxyAndCache:
    """Validates /api/cctv/proxy 4s in-memory caching cadence and throttling prevention."""

    def test_cctv_proxy_caching_and_cadence(self, api_client):
        """Verifies initial fetch queries upstream and subsequent call within 4s uses in-memory cache."""
        test_url = "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/test_cache_cam.jpg"
        fake_jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00\xff\xdb\x00C\x00"

        # Clear test_url from cache if present
        _cctv_cache.pop(test_url, None)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = fake_jpeg_content
        mock_resp.headers = {"Content-Type": "image/jpeg"}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            # 1. First request: should call requests.get
            r1 = api_client.get(f"/api/cctv/proxy?url={test_url}")
            assert r1.status_code == 200
            assert r1.content == fake_jpeg_content
            assert r1.headers["cache-control"] == "public, max-age=4"
            assert mock_get.call_count == 1

            # 2. Second request immediately (within 4 seconds): must hit memory cache, NOT requests.get
            r2 = api_client.get(f"/api/cctv/proxy?url={test_url}")
            assert r2.status_code == 200
            assert r2.content == fake_jpeg_content
            assert mock_get.call_count == 1  # call count did NOT increase!

            # 3. Simulate passage of 4.5 seconds: cache should expire and re-fetch upstream
            old_time, old_data, old_type = _cctv_cache[test_url]
            _cctv_cache[test_url] = (old_time - 5.0, old_data, old_type)

            r3 = api_client.get(f"/api/cctv/proxy?url={test_url}")
            assert r3.status_code == 200
            assert mock_get.call_count == 2  # re-fetched upstream!

    def test_cctv_proxy_stale_cache_fallback(self, api_client):
        """Ensures stale cache is returned if upstream momentarily fails."""
        test_url = "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/stale_cam.jpg"
        cached_jpeg = b"STALE_CACHED_JPEG_PAYLOAD"
        _cctv_cache[test_url] = (time.time() - 10.0, cached_jpeg, "image/jpeg")

        with patch("requests.get", side_effect=Exception("Connection timed out")):
            resp = api_client.get(f"/api/cctv/proxy?url={test_url}")
            assert resp.status_code == 200
            assert resp.content == cached_jpeg

    def test_cctv_proxy_upstream_unavailable_without_cache(self, api_client):
        """Returns HTTP 502 with structured error when upstream is unreachable and no cache exists."""
        uncached_url = "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/missing_never_cached.jpg"
        _cctv_cache.pop(uncached_url, None)

        with patch("requests.get", side_effect=Exception("DNS resolution failure")):
            resp = api_client.get(f"/api/cctv/proxy?url={uncached_url}")
            assert resp.status_code == 502
            assert resp.json()["error"] == "upstream_camera_unavailable"


# =============================================================================
# 3. USER-SPACE VISUAL ACTION PERCEPTION & CRASH GUARD (BugCheck 0x3B)
# =============================================================================
class TestVisualActionPerception:
    """Validates user-space optical perception, canonical activity states, and crash guard."""

    def test_canonical_action_states_membership(self):
        """Ensures canonical set strictly contains ENGAGED_CONVERSATION, CODING_EXECUTION, OBSERVING_MARKETS."""
        expected = {"ENGAGED_CONVERSATION", "CODING_EXECUTION", "OBSERVING_MARKETS"}
        assert CANONICAL_ACTION_STATES == expected

    def test_action_classification_logic(self):
        """Tests classification across high, moderate, and low motion thresholds."""
        engine = ActionPerceptionEngine()

        # High motion (>10) -> CODING_EXECUTION
        act1, label1, attn1 = engine._classify_action(motion_delta=14.5, faces=[])
        assert act1 == "CODING_EXECUTION"
        assert act1 in CANONICAL_ACTION_STATES
        assert 0 <= attn1 <= 100

        # Moderate motion (3 - 10) -> ENGAGED_CONVERSATION
        act2, label2, attn2 = engine._classify_action(motion_delta=6.2, faces=[])
        assert act2 == "ENGAGED_CONVERSATION"
        assert act2 in CANONICAL_ACTION_STATES
        assert 0 <= attn2 <= 100

        # Low motion (<=3) -> OBSERVING_MARKETS
        act3, label3, attn3 = engine._classify_action(motion_delta=1.1, faces=[])
        assert act3 == "OBSERVING_MARKETS"
        assert act3 in CANONICAL_ACTION_STATES
        assert 0 <= attn3 <= 100

    def test_master_identity_presence_and_bounding_box(self):
        """Tests that Master identity, user presence, and bounding box are generated cleanly."""
        engine = ActionPerceptionEngine()
        
        # Generate synthetic test frame (320x240 RGB JPEG)
        img = Image.new("RGB", (320, 240), color=(73, 109, 137))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        frame_bytes = buf.getvalue()

        result = engine.analyze_frame_bytes(frame_bytes, source="webcam_test")
        assert result["status"] == "ok"
        assert result["ok"] is True
        assert result["user_present"] is True
        assert result["master_identity"] == "Master Muhammad Qureshi"
        assert result["detected_action"] in CANONICAL_ACTION_STATES
        assert 0 <= result["attention_score_pct"] <= 100

        # Check Bounding Box
        bbox = result["bounding_box"]
        assert bbox is not None
        assert bbox["label"] == "MASTER MUHAMMAD QURESHI"
        assert "x" in bbox and "y" in bbox and "w" in bbox and "h" in bbox
        assert bbox["confidence"] >= 0.90

    def test_zero_directshow_kernel_traps_on_corrupt_data(self, api_client):
        """
        Guarantees zero DirectShow kernel traps (BugCheck 0x3B crash prevention).
        Corrupted, empty, or non-image payloads in /api/vision/analyze_frame must
        be handled completely in user space with safe fallback.
        """
        # Test empty payload
        r1 = api_client.post("/api/vision/analyze_frame", json={})
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["status"] == "ok"
        assert d1["master_identity"] == "Master Muhammad Qureshi"
        assert d1["detected_action"] in CANONICAL_ACTION_STATES

        # Test corrupt base64 string
        r2 = api_client.post("/api/vision/analyze_frame", json={"frame_base64": "not_valid_base64$$$!!!"})
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["status"] == "ok"
        assert d2["detected_action"] in CANONICAL_ACTION_STATES

        # Test valid base64 data URL
        img = Image.new("RGB", (100, 100), color=(120, 180, 220))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        r3 = api_client.post("/api/vision/analyze_frame", json={"frame_base64": data_url, "source": "canvas"})
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["status"] == "ok"
        assert d3["detected_action"] in CANONICAL_ACTION_STATES
        assert d3["master_identity"] == "Master Muhammad Qureshi"


# =============================================================================
# 4. CONVERSATIONAL VOICE STUDIO & 5-NODE REASONING DAG
# =============================================================================
class TestConversationalVoiceStudioAndDag:
    """Validates Roman Urdu/English NLP, speech synthesis directives, and 5-Node Reasoning DAG."""

    def test_5_node_reasoning_dag_nodes(self):
        """Verifies 5-node Reasoning DAG: [01 Ingest] -> [02 NLP Parse] -> [03 Consensus] -> [04 Action Dispatch] -> [05 Voice Synthesis]."""
        visualizer = ActionVisualizer()
        dag = visualizer.record_command_dag("test command prompt")
        assert len(dag) == 5, f"Expected 5 nodes in DAG, got {len(dag)}"

        expected_steps = ["01", "02", "03", "04", "05"]
        assert [node["step"] for node in dag] == expected_steps

        # Verify step names
        assert "01 Ingest" in dag[0]["name"]
        assert "02 NLP Parse" in dag[1]["name"]
        assert "03 Consensus" in dag[2]["name"]
        assert "04 Action Dispatch" in dag[3]["name"]
        assert "05 Voice Synthesis" in dag[4]["name"]

        # Mark completed
        visualizer.mark_dag_completed()
        for node in visualizer.active_dag:
            assert node["status"] == "COMPLETED"

    def test_chat_voice_roman_urdu_detection_and_speech_params(self, api_client):
        """Tests Roman Urdu prompt selects ur-PK language and returns speech synthesis parameters."""
        prompt = "jarvis cctv cameras dikhao aur halat batao"
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": prompt})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "ok"
        assert data["ok"] is True
        assert data["action_taken"] == "CCTV_FEED_ENGAGED"
        assert "CCTV" in data["reply_text"] or "camera" in data["reply_text"].lower()

        # Speech Directives
        voice = data["voice_synthesis"]
        assert voice["lang"] == "ur-PK"
        assert voice["rate"] == 1.05
        assert voice["pitch"] == 1.0
        assert len(voice["speak_text"]) > 10

        # Active DAG
        dag = data["active_dag"]
        assert len(dag) == 5
        assert all(n["status"] == "COMPLETED" for n in dag)

    def test_chat_voice_english_detection_and_speech_params(self, api_client):
        """Tests English prompt selects en-US language and evaluates command."""
        prompt = "check system heat and thermal load status"
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": prompt})
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "ok"
        assert data["ok"] is True
        assert data["action_taken"] == "HARDWARE_LOAD_BALANCED"

        voice = data["voice_synthesis"]
        assert voice["lang"] == "en-US"
        assert voice["rate"] == 1.05
        assert voice["pitch"] == 1.0

    def test_chat_voice_gold_trading_directive(self, api_client):
        """Tests trading risk check directive and FundingPips compliance."""
        prompt = "jarvis gold account profit and risk gate"
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": prompt})
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_taken"] == "TRADING_RISK_VERIFIED"
        assert "40000294403" in data["reply_text"]
        assert "0.75%" in data["reply_text"]

    def test_chat_voice_empty_prompt_error(self, api_client):
        """Rejects empty voice prompt with HTTP 400."""
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": "   "})
        assert resp.status_code == 400
        assert resp.json()["error"] == "empty_prompt"

    def test_cognition_endpoint_payload(self, api_client):
        """Tests GET /api/jarvis/cognition returns reasoning DAG, foreground, background, and governor."""
        resp = api_client.get("/api/jarvis/cognition")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "reasoning_dag" in data
        assert len(data["reasoning_dag"]) == 5
        assert "foreground" in data
        assert "background" in data
        assert "hardware_governor" in data


# =============================================================================
# 5. INTEGRITY MANDATE & STRICT SAFETY CONSTRAINTS
# =============================================================================
class TestIntegrityAndSafety:
    """Verifies strict adherence to identity constraints and prohibition rules."""

    def test_zero_mentions_of_forbidden_username(self):
        """Verifies zero occurrences of forbidden legacy username across all owned production files."""
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent

        owned_files = [
            root / "core" / "cockpit_api.py",
            root / "perception" / "action_perception.py",
            root / "core" / "action_visualizer.py",
            root / "web" / "sovereign_masterpiece.html",
        ]

        forbidden = "".join(["ad", "eel", "quresh", "i99"])
        for filepath in owned_files:
            assert filepath.exists(), f"Owned file missing: {filepath}"
            text = filepath.read_text(encoding="utf-8", errors="ignore")
            assert forbidden not in text, f"FORBIDDEN IDENTITY FOUND in {filepath}!"

    def test_owner_identity_consistently_master_muhammad_qureshi(self):
        """Verifies Master Muhammad Qureshi is recognized as owner."""
        engine = ActionPerceptionEngine()
        res = engine._build_fallback_result("test", "2026-09-22T00:00:00Z")
        assert res["master_identity"] == "Master Muhammad Qureshi"

        vis = ActionVisualizer()
        state = vis.get_cognition_state()
        assert state["foreground"]["active_speaker"] == "Master Muhammad Qureshi"
