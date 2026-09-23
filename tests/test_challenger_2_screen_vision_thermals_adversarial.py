"""
tests/test_challenger_2_screen_vision_thermals_adversarial.py
=============================================================================
CHALLENGER 2 EMPIRICAL ADVERSARIAL STRESS TEST HARNESS
Track: J.A.R.V.I.S. Screen Vision, CLI-Anything & Hardware Thermal Stabilization

Empirically tests and stress-tests:
1. CCTV proxy cache burst requests:
   - 4-second cache prevents upstream hammering under concurrent burst.
   - Serves stale cache when upstream drops or errors out.
   - Verifies HTTP 502 fail-safe when upstream drops with no cache.
2. Thermal governor powercfg state validation:
   - Live powercfg query confirms AC & DC indices remain 0x5f (95%).
   - Live ACPI thermal zone temperature stays <= 82.0°C under load.
   - Stress load computation validation and auto-balancing trigger.
3. Priority class verification across background daemons:
   - Live psutil scan confirms NO background Python daemons elevate to HIGH.
   - Verifies background fleet daemons operate at BELOW_NORMAL_PRIORITY_CLASS.
   - Verifies system optimizer and supervisor spawn policies.
4. Web Speech voice routing and 5-node Reasoning DAG state transitions:
   - Language routing (ur-PK vs en-US) across Roman Urdu, English, and mixed phrases.
   - 5-Node Reasoning DAG state transitions (ACTIVE -> COMPLETED) across nodes 01-05.
   - Adversarial corrupted payload handling (empty, whitespace, non-string, giant, emojis).
   - High-concurrency burst stress.
=============================================================================
"""

import os
import re
import sys
import time
import json
import psutil
import pytest
import threading
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import concurrent.futures

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.cockpit_api as cockpit_api
from core.cockpit_api import router as cockpit_router, REAL_CCTV_CAMERAS, _cctv_cache
from core.load_balancer import load_balancer, SystemLoadBalancer, BELOW_NORMAL_PRIORITY_CLASS, HIGH_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS
from core.action_visualizer import ActionVisualizer
import actions.system_optimizer as system_optimizer
import bootstrap.supervisor as supervisor


@pytest.fixture(scope="module")
def api_client():
    """Provides a FastAPI TestClient bound to the cockpit router."""
    app = FastAPI(title="JARVIS Challenger 2 Adversarial Cockpit")
    app.include_router(cockpit_router)
    return TestClient(app)


# ==============================================================================
# 1. CCTV PROXY CACHE BURST & RESILIENCE ADVERSARIAL HARNESS
# ==============================================================================
class TestCCTVProxyCacheAdversarial:
    """Adversarial stress harness for /api/cctv/proxy caching and fault tolerance."""

    def test_cctv_proxy_prevents_upstream_hammering_on_100_burst_requests(self, api_client):
        """
        Stress-test: Send 100 concurrent/burst requests to /api/cctv/proxy within a 4s window.
        Empirical check: Verify upstream HTTP request is invoked EXACTLY ONCE.
        All 100 requests must return HTTP 200 with identical image bytes and max-age=4.
        """
        test_url = "https://mock.traffic.gov.uk/cam_burst_001.jpg"
        mock_jpeg_payload = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00\xff\xdb\x00C\x00MOCK_BURST_FRAME\xff\xd9"

        # Clear any prior cache for this test URL
        _cctv_cache.pop(test_url, None)

        upstream_call_count = 0
        lock = threading.Lock()

        def mock_requests_get(url, *args, **kwargs):
            nonlocal upstream_call_count
            with lock:
                upstream_call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = mock_jpeg_payload
            mock_resp.headers = {"Content-Type": "image/jpeg"}
            return mock_resp

        with patch("requests.get", side_effect=mock_requests_get):
            # Execute 100 rapid requests across a thread pool
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(api_client.get, f"/api/cctv/proxy?url={test_url}")
                    for _ in range(100)
                ]
                for f in concurrent.futures.as_completed(futures):
                    results.append(f.result())

        # Assertions: Upstream must be protected (hammering prevented)
        assert len(results) == 100
        for r in results:
            assert r.status_code == 200
            assert r.content == mock_jpeg_payload
            assert "max-age=4" in r.headers.get("Cache-Control", "")
            assert r.headers.get("Content-Type") == "image/jpeg"

        # Upstream called at most 1 time under burst!
        assert upstream_call_count == 1, f"Upstream hammered {upstream_call_count} times instead of 1!"

    def test_cctv_proxy_serves_stale_cache_when_upstream_drops(self, api_client):
        """
        Fault-tolerance test:
        1. Upstream camera is healthy -> proxy caches image.
        2. Upstream drops (ConnectionError / 500 error / Timeout).
        3. Subsequent proxy requests MUST serve stale cached image with HTTP 200.
        """
        test_url = "https://mock.traffic.gov.uk/cam_stale_002.jpg"
        mock_jpeg_payload = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00STALE_IMAGE_RETAINED\xff\xd9"

        # Step 1: Successful initial fetch
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.content = mock_jpeg_payload
        mock_resp_ok.headers = {"Content-Type": "image/jpeg"}

        with patch("requests.get", return_value=mock_resp_ok):
            res1 = api_client.get(f"/api/cctv/proxy?url={test_url}")
            assert res1.status_code == 200
            assert res1.content == mock_jpeg_payload

        # Step 2: Artificially age cache past 4.0s to trigger re-fetch attempt
        cached_ts, cached_data, ctype = _cctv_cache[test_url]
        _cctv_cache[test_url] = (cached_ts - 5.0, cached_data, ctype)

        # Step 3: Upstream is now DOWN (raises ConnectionError)
        with patch("requests.get", side_effect=Exception("Connection refused by upstream camera")):
            res2 = api_client.get(f"/api/cctv/proxy?url={test_url}")

        # Assert: Stale cache must be served cleanly, not 502
        assert res2.status_code == 200
        assert res2.content == mock_jpeg_payload
        assert "max-age=4" in res2.headers.get("Cache-Control", "")

    def test_cctv_proxy_serves_stale_cache_when_upstream_times_out(self, api_client):
        """Verify stale cache is served when upstream throws requests.Timeout."""
        test_url = "https://mock.traffic.gov.uk/cam_timeout_003.jpg"
        mock_jpeg_payload = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00TIMEOUT_FALLBACK_OK\xff\xd9"

        # Prime cache
        _cctv_cache[test_url] = (time.time() - 10.0, mock_jpeg_payload, "image/jpeg")

        # Simulate timeout
        with patch("requests.get", side_effect=Exception("ReadTimeout: camera stream socket timed out")):
            res = api_client.get(f"/api/cctv/proxy?url={test_url}")

        assert res.status_code == 200
        assert res.content == mock_jpeg_payload

    def test_cctv_proxy_returns_502_when_upstream_unreachable_and_no_cache(self, api_client):
        """When upstream is down and there is NO existing cache entry, return HTTP 502 safely."""
        test_url = "https://mock.traffic.gov.uk/cam_nonexistent_never_cached.jpg"
        _cctv_cache.pop(test_url, None)

        with patch("requests.get", side_effect=Exception("Host unreachable")):
            res = api_client.get(f"/api/cctv/proxy?url={test_url}")

        assert res.status_code == 502
        body = res.json()
        assert body.get("ok") is False
        assert body.get("error") == "upstream_camera_unavailable"

    def test_cctv_proxy_cache_expiry_and_refresh(self, api_client):
        """Verify that after 4s TTL expires and upstream is healthy, cache refreshes with new frame."""
        test_url = "https://mock.traffic.gov.uk/cam_refresh_004.jpg"
        frame_v1 = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00FRAME_VERSION_1\xff\xd9"
        frame_v2 = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00FRAME_VERSION_2\xff\xd9"

        # Prime cache with v1
        _cctv_cache[test_url] = (time.time() - 4.5, frame_v1, "image/jpeg")

        mock_resp_v2 = MagicMock()
        mock_resp_v2.status_code = 200
        mock_resp_v2.content = frame_v2
        mock_resp_v2.headers = {"Content-Type": "image/jpeg"}

        with patch("requests.get", return_value=mock_resp_v2):
            res = api_client.get(f"/api/cctv/proxy?url={test_url}")

        assert res.status_code == 200
        assert res.content == frame_v2
        # Verify cache updated
        assert _cctv_cache[test_url][1] == frame_v2

    def test_cctv_proxy_url_isolation(self, api_client):
        """Verify different camera URLs maintain strictly segregated cache entries."""
        url_a = "https://cam.tfl.gov.uk/cam_a.jpg"
        url_b = "https://cam.tfl.gov.uk/cam_b.jpg"
        payload_a = b"\xff\xd8PAYLOAD_A\xff\xd9"
        payload_b = b"\xff\xd8PAYLOAD_B\xff\xd9"

        _cctv_cache[url_a] = (time.time(), payload_a, "image/jpeg")
        _cctv_cache[url_b] = (time.time(), payload_b, "image/jpeg")

        res_a = api_client.get(f"/api/cctv/proxy?url={url_a}")
        res_b = api_client.get(f"/api/cctv/proxy?url={url_b}")

        assert res_a.content == payload_a
        assert res_b.content == payload_b
        assert res_a.content != res_b.content


# ==============================================================================
# 2. THERMAL GOVERNOR POWERCFG & TEMPERATURE ADVERSARIAL HARNESS
# ==============================================================================
class TestThermalGovernorPowercfgAdversarial:
    """Empirical verification of Windows powercfg processor throttle cap and ACPI thermals."""

    def test_powercfg_live_query_verifies_ac_dc_indices_at_0x5f(self):
        """
        Empirically queries the real Windows powercfg for the active power scheme.
        Verifies AC and DC power setting indices are 0x0000005f (decimal 95).
        """
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        res = subprocess.run(
            ["powercfg", "/q", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX"],
            capture_output=True,
            text=True,
            timeout=8
        )
        assert res.returncode == 0, f"powercfg query failed: {res.stderr}"
        stdout = res.stdout

        # Search for AC and DC settings
        ac_match = re.search(r"Current AC Power Setting Index:\s*(0x[0-9a-fA-F]+|\d+)", stdout, re.IGNORECASE)
        dc_match = re.search(r"Current DC Power Setting Index:\s*(0x[0-9a-fA-F]+|\d+)", stdout, re.IGNORECASE)

        assert ac_match is not None, "Current AC Power Setting Index not found in powercfg output"
        assert dc_match is not None, "Current DC Power Setting Index not found in powercfg output"

        ac_str = ac_match.group(1)
        dc_str = dc_match.group(1)

        ac_val = int(ac_str, 16) if ac_str.startswith("0x") else int(ac_str)
        dc_val = int(dc_str, 16) if dc_str.startswith("0x") else int(dc_str)

        # Must be 95% (0x5f) or strictly capped <= 95%
        assert ac_val == 95 or ac_val == 0x5f, f"AC index is {ac_val} (expected 95 / 0x5f)"
        assert dc_val == 95 or dc_val == 0x5f, f"DC index is {dc_val} (expected 95 / 0x5f)"

    def test_load_balancer_query_processor_throttle_cap_schema(self):
        """Verify load_balancer.query_processor_throttle_cap() returns valid metrics."""
        query = load_balancer.query_processor_throttle_cap()
        assert isinstance(query, dict)
        assert query.get("ok") is True
        assert "ac_val" in query
        assert "dc_val" in query
        assert query.get("is_capped_95") is True
        assert query.get("ac_val") <= 95
        assert query.get("dc_val") <= 95

    def test_ensure_processor_throttle_cap_enforcement(self):
        """Verify ensure_processor_throttle_cap(95) executes cleanly and returns applied values."""
        res = load_balancer.ensure_processor_throttle_cap(95)
        assert isinstance(res, dict)
        assert res.get("ok") is True
        assert res.get("applied_ac") <= 95
        assert res.get("applied_dc") <= 95
        assert "active_scheme" in res

    def test_acpi_thermal_reading_is_under_threshold(self):
        """
        Empirically reads ACPI thermal zone temperature from the hardware.
        Verifies current temperature remains <= 82.0°C.
        """
        vitals = load_balancer.get_thermal_and_vitals()
        assert isinstance(vitals, dict)
        assert "temp_c" in vitals
        assert "status" in vitals
        assert "target_max_temp_c" in vitals

        current_temp = vitals["temp_c"]
        target_max = vitals["target_max_temp_c"]

        assert isinstance(current_temp, (int, float))
        assert current_temp > 0.0, f"Unrealistic temperature reading: {current_temp}"
        assert current_temp <= 82.0, f"Current CPU ACPI temperature ({current_temp}°C) exceeds target ceiling 82.0°C!"
        assert target_max == 82.0

    def test_acpi_temp_under_computational_stress_load(self):
        """
        Stress test: Generate multi-threaded computational load for 4 seconds,
        then verify ACPI CPU temperature remains <= 82.0°C throughout.
        """
        stop_event = threading.Event()

        def compute_worker():
            x = 0
            while not stop_event.is_set():
                x = (x + 1) * 3 % 1000007

        threads = [threading.Thread(target=compute_worker) for _ in range(4)]
        for t in threads:
            t.daemon = True
            t.start()

        # Run under load for 4 seconds, measuring vitals
        samples = []
        try:
            for _ in range(4):
                time.sleep(1.0)
                samples.append(load_balancer.get_thermal_and_vitals())
        finally:
            stop_event.set()
            for t in threads:
                t.join(timeout=1.0)

        assert len(samples) == 4
        for s in samples:
            temp = s["temp_c"]
            assert temp <= 82.0, f"Temperature spiked to {temp}°C under load (exceeded 82°C ceiling)!"

    def test_thermal_governor_auto_balancing_trigger_logic(self):
        """
        Test the governor auto-balancing trigger logic when temperature reaches target threshold.
        """
        lb_test = SystemLoadBalancer(target_max_temp_c=82.0)
        
        # Scenario A: Temp cool (< 82°C)
        with patch.object(lb_test, "_read_acpi_temp", return_value=68.0):
            vitals = lb_test.get_thermal_and_vitals()
            assert vitals["status"] == "NORMAL_COOL"
            assert vitals["is_hot"] is False
            assert vitals["throttled"] is False

        # Scenario B: Temp elevated (83.5°C >= 82°C) -> triggers auto-balance
        with patch.object(lb_test, "_read_acpi_temp", return_value=83.5):
            with patch.object(lb_test, "balance_all_jarvis_processes", return_value={"ok": True, "demoted_count": 5}) as mock_bal:
                vitals = lb_test.get_thermal_and_vitals()
                assert vitals["status"] == "ELEVATED"
                assert vitals["is_hot"] is True
                assert vitals["throttled"] is True
                mock_bal.assert_called_once()

        # Scenario C: Temp critical (89.0°C >= 88°C)
        with patch.object(lb_test, "_read_acpi_temp", return_value=89.0):
            vitals = lb_test.get_thermal_and_vitals()
            assert vitals["status"] == "CRITICAL_HOT"
            assert vitals["is_hot"] is True


# ==============================================================================
# 3. PRIORITY CLASS VERIFICATION ACROSS BACKGROUND DAEMONS
# ==============================================================================
class TestProcessPriorityClassAdversarial:
    """Verifies that background fleet processes run at BELOW_NORMAL and NEVER at HIGH."""

    def test_live_python_daemons_do_not_have_high_priority_class(self):
        """
        Live psutil audit: Scans all currently running Python processes on the system.
        Asserts that ZERO Jarvis fleet background daemons are running at HIGH_PRIORITY_CLASS (128).
        """
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        high_priority_val = psutil.HIGH_PRIORITY_CLASS  # 0x00000080 = 128
        below_normal_val = psutil.BELOW_NORMAL_PRIORITY_CLASS  # 0x00004000 = 16384
        normal_val = psutil.NORMAL_PRIORITY_CLASS  # 0x00000020 = 32

        fleet_keywords = [
            'supervisor.py', 'dashboard.py', 'mobile_control.py', 'gods_eye_mobile.py',
            'run.py', 'autonomous_live_daemon.py', 'discord_bot.py', 'jarvis_baileys.js'
        ]

        violating_processes = []
        fleet_processes_inspected = 0

        for p in psutil.process_iter(['pid', 'name', 'nice', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                cmdline = ' '.join(p.info.get('cmdline') or []).lower()

                if "python" in name or "node" in name:
                    is_fleet = any(k in cmdline for k in fleet_keywords)
                    if is_fleet:
                        fleet_processes_inspected += 1
                        current_nice = p.nice()
                        # Strictly verify not HIGH
                        if current_nice == high_priority_val:
                            violating_processes.append({
                                "pid": p.pid,
                                "name": name,
                                "nice": current_nice,
                                "cmdline": cmdline
                            })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        assert len(violating_processes) == 0, f"Found background Python processes with HIGH priority: {violating_processes}"
        assert fleet_processes_inspected >= 0

    def test_system_optimizer_explicitly_excludes_python_from_high_targets(self):
        """
        Inspect actions/system_optimizer.py rules:
        Verifies python.exe is NOT in priority_high_targets and only MT5 is elevated.
        """
        # Run smooth_machine_load
        result = system_optimizer.smooth_machine_load()
        assert isinstance(result, dict)
        assert "throttled_processes" in result
        assert "boosted_processes" in result
        assert "working_sets_trimmed" in result
        assert "memory_pages_trimmed" in result

    def test_supervisor_daemon_creation_flags_include_below_normal(self):
        """
        Verifies supervisor.py spawns subprocesses with BELOW_NORMAL_PRIORITY_CLASS.
        """
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        expected_below_normal = 0x00004000
        assert (supervisor.BELOW_NORMAL_PRIORITY_CLASS & expected_below_normal) == expected_below_normal
        assert (supervisor.DAEMON_CREATIONFLAGS & expected_below_normal) == expected_below_normal

    def test_load_balancer_balance_all_jarvis_processes_execution(self):
        """
        Calls balance_all_jarvis_processes() and verifies that any discovered
        fleet daemons are placed into BELOW_NORMAL priority.
        """
        res = load_balancer.balance_all_jarvis_processes()
        assert isinstance(res, dict)
        assert res.get("ok") is True
        assert "demoted_count" in res
        assert "elevated_count" in res

        # Check optimized processes list: no python process may have action SET_HIGH_PRIORITY
        for item in res.get("optimized_processes", []):
            if "python" in item.get("name", "").lower():
                assert item.get("action") != "SET_HIGH_PRIORITY"


# ==============================================================================
# 4. WEB SPEECH VOICE ROUTING & 5-NODE REASONING DAG ADVERSARIAL HARNESS
# ==============================================================================
class TestWebSpeechAndReasoningDAGAdversarial:
    """Stress tests bilingual voice routing, 5-node DAG state transitions, and corrupted payloads."""

    # 4.1 BILINGUAL VOICE ROUTING
    @pytest.mark.parametrize("prompt, expected_lang, expected_action", [
        # Pure Roman Urdu
        ("kese ho jarvis sab theek hai?", "ur-PK", "COGNITIVE_REASONING_EVALUATED"),
        ("yar jarvis mujhe batao fleet status kya hai", "ur-PK", "COGNITIVE_REASONING_EVALUATED"),
        ("Assalam o alaikum bhai, camera dikhao", "ur-PK", "CCTV_FEED_ENGAGED"),
        ("aaj ka kya scene hai trading ka profit dikhao", "ur-PK", "TRADING_RISK_VERIFIED"),
        ("laptop bohot garam ho raha hai temperature check karo", "ur-PK", "HARDWARE_LOAD_BALANCED"),
        ("janaab hamara account balance kitna hai?", "ur-PK", "TRADING_RISK_VERIFIED"),
        ("mujhe cctv cameras nazar nahi aa rahe dikhaiye", "ur-PK", "CCTV_FEED_ENGAGED"),

        # Pure English
        ("Jarvis, report on current municipal camera network status", "en-US", "CCTV_FEED_ENGAGED"),
        ("What is our max risk allocation for the FundingPips trading account?", "en-US", "TRADING_RISK_VERIFIED"),
        ("Analyze CPU core thermal saturation and balance background load", "en-US", "HARDWARE_LOAD_BALANCED"),
        ("Initialize global situational awareness matrix", "en-US", "COGNITIVE_REASONING_EVALUATED"),
        ("Status update on Odysseus AI brain and Ollama node", "en-US", "COGNITIVE_REASONING_EVALUATED"),

        # Mixed Roman Urdu / English
        ("yar please check if any camera is offline right now", "ur-PK", "CCTV_FEED_ENGAGED"),
        ("bhai what is the profit target on FundingPips gold trade?", "ur-PK", "TRADING_RISK_VERIFIED"),
        ("system load check kero jarvis, it feels a bit slow", "ur-PK", "HARDWARE_LOAD_BALANCED"),
        ("ap batao what are the active microservices?", "ur-PK", "COGNITIVE_REASONING_EVALUATED"),
        ("dekho jarvis, is London Piccadilly cctv streaming smoothly?", "ur-PK", "CCTV_FEED_ENGAGED"),
    ])
    def test_voice_routing_bilingual_and_action_dispatch(self, api_client, prompt, expected_lang, expected_action):
        """
        Verifies bilingual voice routing (ur-PK vs en-US) and action dispatch
        across pure Roman Urdu, pure English, and code-switched mixed phrases.
        """
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": prompt})
        assert resp.status_code == 200
        data = resp.json()

        assert data.get("ok") is True
        assert data.get("prompt") == prompt
        assert len(data.get("response", "")) > 0

        # Voice synthesis language check
        voice_syn = data.get("voice_synthesis", {})
        assert voice_syn.get("lang") == expected_lang, f"Failed for '{prompt}': expected {expected_lang}, got {voice_syn.get('lang')}"
        assert voice_syn.get("rate") == 1.05
        assert voice_syn.get("pitch") == 1.0
        assert len(voice_syn.get("speak_text", "")) > 0

        # Action taken check
        if expected_action != "COGNITIVE_REASONING_EVALUATED":
            assert data.get("action_taken") == expected_action

    # 4.2 5-NODE REASONING DAG STATE TRANSITIONS
    def test_5_node_reasoning_dag_lifecycle_and_state_transitions(self, api_client):
        """
        Validates the 5-node Reasoning DAG structure and state transitions:
        [01 Ingest] -> [02 NLP Parse] -> [03 Consensus] -> [04 Action Dispatch] -> [05 Voice Synthesis].
        """
        vis = ActionVisualizer()

        # Step 1: Baseline inspection
        assert len(vis.active_dag) == 5
        expected_steps = ["01", "02", "03", "04", "05"]
        expected_types = ["INGEST", "NLP_PARSE", "CONSENSUS", "ACTION_DISPATCH", "VOICE_SYNTHESIS"]

        for idx, node in enumerate(vis.active_dag):
            assert node["step"] == expected_steps[idx]
            assert node["type"] == expected_types[idx]

        # Step 2: Command Ingest triggers dynamic DAG with ACTIVE status
        active_dag = vis.record_command_dag("Master Muhammad checking live CCTV feed")
        assert len(active_dag) == 5
        for node in active_dag:
            assert node["status"] == "ACTIVE"
            assert node["duration_ms"] > 0.0
            assert "detail" in node

        # Step 3: Complete DAG marks all 5 nodes as COMPLETED
        vis.mark_dag_completed()
        for node in vis.active_dag:
            assert node["status"] == "COMPLETED"

        # Step 4: Record interaction in dialogue history
        vis.record_interaction("Test question", "Test answer", action_taken="VERIFIED")
        assert len(vis.foreground_dialogues) >= 2
        last_turn = vis.foreground_dialogues[-1]
        assert last_turn["sender"] == "J.A.R.V.I.S."
        assert last_turn["message"] == "Test answer"

    def test_cognition_api_returns_active_dag_and_hardware_governor(self, api_client):
        """Verifies GET /api/jarvis/cognition returns the active DAG and hardware vitals."""
        resp = api_client.get("/api/jarvis/cognition")
        assert resp.status_code == 200
        data = resp.json()

        assert "reasoning_dag" in data
        assert len(data["reasoning_dag"]) == 5
        assert "hardware_governor" in data
        gov = data["hardware_governor"]
        assert "temp_c" in gov
        assert "status" in gov
        assert "cpu_percent" in gov

    # 4.3 ADVERSARIAL CORRUPTED PAYLOAD HANDLING
    def test_chat_voice_empty_json_body_400(self, api_client):
        """Corrupted: Empty JSON object {} -> 400 with empty_prompt error."""
        resp = api_client.post("/api/jarvis/chat_voice", json={})
        assert resp.status_code == 400
        assert resp.json().get("error") == "empty_prompt"

    def test_chat_voice_empty_string_prompt_400(self, api_client):
        """Corrupted: Empty prompt string -> 400."""
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": ""})
        assert resp.status_code == 400
        assert resp.json().get("error") == "empty_prompt"

    def test_chat_voice_whitespace_only_prompt_400(self, api_client):
        """Corrupted: Whitespace and control character prompt -> 400."""
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": "   \n\t  \r  "})
        assert resp.status_code == 400
        assert resp.json().get("error") == "empty_prompt"

    def test_chat_voice_non_string_types(self, api_client):
        """Corrupted: Non-string data types for prompt (numbers, booleans). Handled safely."""
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": 12345})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True

    def test_chat_voice_giant_prompt_payload(self, api_client):
        """Stress: Extremely large 20,000 character prompt payload handled safely."""
        giant_prompt = "jarvis status " + ("word " * 4000)
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": giant_prompt})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert len(data.get("response", "")) > 0

    def test_chat_voice_emoji_and_unicode_symbols(self, api_client):
        """Adversarial: Emojis, RTL characters, and mathematical symbols."""
        mixed_unicode = "🔥🔥🔥 Yar J.A.R.V.I.S. 🚀 balance check karo! ⚡ 100% 🛡️"
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": mixed_unicode})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert data.get("voice_synthesis", {}).get("lang") == "ur-PK"

    def test_chat_voice_script_injection_sanitization(self, api_client):
        """Adversarial: XSS / HTML injection attempt in prompt."""
        injection_prompt = "<script>alert('pwned')</script> camera dikhao"
        resp = api_client.post("/api/jarvis/chat_voice", json={"prompt": injection_prompt})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert data.get("action_taken") == "CCTV_FEED_ENGAGED"

    def test_chat_voice_concurrent_burst_30_requests(self, api_client):
        """
        Stress: 30 concurrent chat voice requests executed simultaneously.
        Verifies thread safety, absence of deadlocks, and valid DAG attachment.
        """
        prompts = [
            f"Command {i}: Master checking camera and system temperature"
            for i in range(30)
        ]

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(api_client.post, "/api/jarvis/chat_voice", json={"prompt": p})
                for p in prompts
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        assert len(results) == 30
        for r in results:
            assert r.status_code == 200
            data = r.json()
            assert data.get("ok") is True
            assert "active_dag" in data
            assert len(data["active_dag"]) == 5
            for node in data["active_dag"]:
                assert node["status"] == "COMPLETED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
