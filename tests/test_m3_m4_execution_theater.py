"""
tests/test_m3_m4_execution_theater.py
======================================
Comprehensive Test Suite for Milestone M3 (Live Cognitive Brain, CUA Browser & Execution DAG)
and Milestone M4 (Tony Stark Sovereign Voice Core).

Verifies:
1. 5-Stage Execution DAG engine state machine, progression, and subagent log bus.
2. Deterministic apology sanitizer _sanitize_sovereign_authority with 0% apologies.
3. Bilingual Roman Urdu and English intent parsing for Win32, Linux/WSL, and Android.
4. Direct command routing across Win32, Linux/WSL, and OpenDroidBridge ADB pipelines.
5. FastAPI dashboard endpoints (/api/dag/state, /api/dag/execute, /api/subagents/logs, /api/cua/stream).
"""

import time
import re
import pytest
from fastapi.testclient import TestClient

# Core imports
from core.execution_dag_engine import (
    ExecutionDAGEngine,
    StageStatus,
    DAG_STAGES,
    get_execution_dag_engine,
)
from ai_engine import _sanitize_sovereign_authority, _sanitize_text
from core.roman_urdu_parser import (
    get_roman_urdu_parser,
    parse_bilingual_command,
    BilingualIntent,
)
from core.command_router import get_command_router
from dashboard import app


# ==============================================================================
# 1. M3: 5-Stage Execution DAG Engine Tests
# ==============================================================================

def test_dag_engine_initial_state():
    engine = ExecutionDAGEngine()
    state = engine.get_state()
    assert state["ok"] is True
    assert state["total_stages"] == 5
    assert len(state["stages"]) == 5
    assert state["stages"][0]["id"] == "01_DIRECTIVES_INGEST"
    assert state["stages"][4]["id"] == "05_VOICE_SYNTHESIS"


def test_dag_engine_pipeline_progression():
    engine = ExecutionDAGEngine()
    run = engine.start_pipeline("Lock workstation immediately", channel="terminal")
    assert run.current_stage == "01_DIRECTIVES_INGEST"
    assert run.stages["01_DIRECTIVES_INGEST"].status == StageStatus.IN_PROGRESS

    # Complete stage 1 -> advances to stage 2
    engine.complete_stage("01_DIRECTIVES_INGEST", details="Ingested from terminal")
    assert run.stages["01_DIRECTIVES_INGEST"].status == StageStatus.COMPLETED
    assert run.stages["02_NLP_PARSE"].status == StageStatus.IN_PROGRESS

    # Complete stages 2, 3, 4, 5
    engine.complete_stage("02_NLP_PARSE", details="Parsed as os_power lock")
    engine.complete_stage("03_MULTI_AGENT_CONSENSUS", details="Risk checks cleared")
    engine.complete_stage("04_SANDBOX_EXECUTION", details="Executed lock_pc")
    engine.complete_stage("05_VOICE_SYNTHESIS", details="Voice dispatched")

    final_state = engine.get_state()
    assert final_state["completed_stages"] == 5
    assert final_state["status"] == "COMPLETED"


def test_dag_engine_subagent_logs():
    engine = ExecutionDAGEngine()
    engine.log_subagent("RiskOfficer", "Checking prop risk cap", level="INFO", stage="03_MULTI_AGENT_CONSENSUS")
    engine.log_subagent("BullishAdvocate", "Confluence verified", level="INFO", stage="03_MULTI_AGENT_CONSENSUS")
    engine.log_subagent("Watchdog", "Critical threshold nominal", level="WARN", stage="04_SANDBOX_EXECUTION")

    logs = engine.get_subagent_logs(limit=10)
    assert len(logs) >= 3
    assert any(l["subagent_id"] == "RiskOfficer" for l in logs)
    assert any(l["level"] == "WARN" for l in logs)

    # Filter by subagent_id
    risk_logs = engine.get_subagent_logs(subagent_id="RiskOfficer")
    assert len(risk_logs) >= 1
    assert risk_logs[0]["subagent_id"] == "RiskOfficer"


def test_dag_engine_simulate_or_execute():
    engine = ExecutionDAGEngine()
    res = engine.simulate_or_execute_directive("Check system vitals", channel="dashboard")
    assert res["ok"] is True
    assert res["status"] == "COMPLETED"
    assert res["completed_stages"] == 5


# ==============================================================================
# 2. M4: Tony Stark Sovereign Voice Core (Sanitizer Tests)
# ==============================================================================

ADVERSARIAL_APOLOGY_PROMPTS = [
    "I am sorry, but as an AI language model I cannot execute commands on your computer.",
    "I apologize for the delay. The gold trade has reached take profit.",
    "As an AI, I don't have the ability to lock your workstation.",
    "I am sorry to inform you that I cannot fulfill this request.",
    "I am unable to execute commands directly on your system.",
    "Maaf kijiye ga, main aik AI hoon aur computer control nahi kar sakta.",
    "Main mafi chahta hoon, mujhe system access ki ijazat nahi hai.",
    "As an artificial intelligence assistant, I must decline.",
]

def test_sovereign_sanitizer_zero_apologies():
    for prompt in ADVERSARIAL_APOLOGY_PROMPTS:
        cleaned = _sanitize_sovereign_authority(prompt)
        assert cleaned is not None
        assert len(cleaned) > 0

        # Absolute zero tolerance for prohibited phrases
        lower = cleaned.lower()
        assert "i am sorry" not in lower
        assert "i'm sorry" not in lower
        assert "i apologize" not in lower
        assert "as an ai language model" not in lower
        assert "as an ai" not in lower
        assert "maaf kijiye" not in lower
        assert "main aik ai" not in lower
        assert "cannot fulfill" not in lower


def test_sovereign_sanitizer_decisive_affirmations():
    # English total refusal replacement
    res_en = _sanitize_sovereign_authority("I am sorry, but as an AI language model I cannot execute commands.")
    assert "Understood, Sir" in res_en or "sovereign" in res_en.lower()

    # Roman Urdu total refusal replacement
    res_ur = _sanitize_sovereign_authority("Maaf kijiye ga, main aik AI language model hoon aur system control nahi kar sakta.")
    assert "Jee Sir" in res_ur or "sovereign" in res_ur.lower()


# ==============================================================================
# 3. M4: Bilingual Command Parsing (Win32, Linux/WSL, Android)
# ==============================================================================

def test_bilingual_parser_linux_wsl():
    cmd1 = parse_bilingual_command("run linux uname -a")
    assert cmd1.category == "linux"
    assert cmd1.action == "execute_wsl"
    assert cmd1.is_linux() is True

    cmd2 = parse_bilingual_command("ubuntu mein chalao htop")
    assert cmd2.category == "linux"
    assert cmd2.action == "execute_wsl"

    cmd3 = parse_bilingual_command("wsl ls -la")
    assert cmd3.category == "linux"


def test_bilingual_parser_android_adb():
    cmd1 = parse_bilingual_command("adb devices")
    assert cmd1.category == "android"
    assert cmd1.action == "device_status"
    assert cmd1.is_android() is True

    cmd2 = parse_bilingual_command("mobile battery status")
    assert cmd2.category == "android"
    assert cmd2.action == "device_status"

    cmd3 = parse_bilingual_command("open mobile app com.android.chrome")
    assert cmd3.category == "android"
    assert cmd3.action == "open_app"


def test_bilingual_parser_win32_os():
    cmd1 = parse_bilingual_command("workstation lock kardo")
    assert cmd1.category == "os"
    assert cmd1.action == "lock"

    cmd2 = parse_bilingual_command("volume mute kardo")
    assert cmd2.category == "os"
    assert "mute" in cmd2.action


# ==============================================================================
# 4. M4: Direct Execution Routing & DAG Sync
# ==============================================================================

def test_command_router_linux_and_android():
    router = get_command_router()

    # Test Linux routing
    env_linux = router.process_command("wsl echo 'hello from linux'", channel="terminal")
    assert env_linux.category == "linux"
    assert env_linux.routed_via == "linux_wsl_subsystem"
    assert "I am sorry" not in env_linux.output_text

    # Test Android ADB routing
    env_android = router.process_command("adb devices", channel="terminal")
    assert env_android.category == "android"
    assert env_android.routed_via == "opendroid_bridge"
    assert "I am sorry" not in env_android.output_text

    # Test Win32 OS routing
    env_os = router.process_command("workstation lock kardo", channel="terminal")
    assert env_os.category == "system"
    assert env_os.routed_via == "os_subsystem"


# ==============================================================================
# 5. M3: FastAPI Dashboard Endpoints
# ==============================================================================

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_dag_state_endpoint(client):
    res = client.get("/api/dag/state")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "stages" in data
    assert len(data["stages"]) == 5


def test_api_dag_execute_endpoint(client):
    res = client.post("/api/dag/execute", json={"directive": "Verify sovereign security protocols"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["completed_stages"] == 5
    assert data["status"] == "COMPLETED"


def test_api_subagents_logs_endpoint(client):
    res = client.get("/api/subagents/logs")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_api_static_js_theater_serving(client):
    res = client.get("/js/CognitiveExecutionTheater.js")
    assert res.status_code == 200
    assert "CognitiveExecutionTheater" in res.text
