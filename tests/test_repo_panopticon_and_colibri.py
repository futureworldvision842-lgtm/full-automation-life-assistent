import pytest
from starlette.testclient import TestClient
from dashboard import app as dashboard_app
from mobile_control import app as mobile_app
from core.autonomous_repo_orchestrator import get_repo_orchestrator
from core.llm.colibri_bridge import ColibriBridge


def test_repo_orchestrator_initial_state():
    orch = get_repo_orchestrator()
    repos = orch.get_all_integrated_repos()
    assert len(repos) >= 7
    names = [r["name"] for r in repos]
    assert "colibri" in names
    assert "CLI-Anything" in names
    assert "cua" in names
    assert "Global-Ai-Decentralize-Governance-System" in names
    assert "freqtrade" in names
    assert "openhuman" in names


def test_colibri_bridge_diagnostics():
    bridge = ColibriBridge()
    status = bridge.get_engine_status()
    assert "workstation_hardware" in status
    assert status["workstation_hardware"]["total_ram_gb"] > 0
    assert status["workstation_hardware"]["free_disk_gb"] > 0
    assert "version" in status
    assert status["installed"] is True
    plan = bridge.calculate_resource_plan("GLM-5.2")
    assert plan["model_name"] == "GLM-5.2"
    assert "active_experts_in_ram" in plan
    assert plan["ok"] is True


def test_task_panopticon_payload():
    orch = get_repo_orchestrator()
    panopticon = orch.get_autonomous_execution_panopticon()
    assert "daemons" in panopticon
    assert len(panopticon["daemons"]) >= 5
    assert "active_tasks" in panopticon
    assert "previous_milestones" in panopticon
    assert "future_roadmap" in panopticon


def test_dashboard_repo_endpoints():
    client = TestClient(dashboard_app)

    # 1. Repos integrated
    resp = client.get("/api/repos/integrated")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["repositories"]) >= 7

    # 2. Colibri status
    resp_coli = client.get("/api/repos/colibri/status")
    assert resp_coli.status_code == 200
    coli_data = resp_coli.json()
    assert coli_data["ok"] is True
    assert coli_data["colibri"]["installed"] is True
    assert "workstation_hardware" in coli_data["colibri"]

    # 3. Colibri plan (POST)
    resp_plan = client.post("/api/repos/colibri/plan", json={"model_name": "GLM-5.2"})
    assert resp_plan.status_code == 200
    assert resp_plan.json()["ok"] is True
    assert resp_plan.json()["model_name"] == "GLM-5.2"

    # 4. Task panopticon
    resp_tasks = client.get("/api/tasks/panopticon")
    assert resp_tasks.status_code == 200
    assert "daemons" in resp_tasks.json()

    # 5. WhatsApp directive simulation
    resp_wa = client.post(
        "/api/repos/whatsapp/process_directive",
        json={"sender": "+923468053268", "message": "https://github.com/JustVugg/colibri.git"}
    )
    assert resp_wa.status_code == 200
    wa_data = resp_wa.json()
    assert wa_data["ok"] is True
    assert wa_data["action"] == "GITHUB_URL_ASSIMILATION"
    assert "Master Muhammad" in wa_data["reply"]


def test_mobile_repo_endpoints():
    client = TestClient(mobile_app)

    # 1. Repos integrated
    resp = client.get("/api/repos/integrated")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    # 2. Colibri status
    resp_coli = client.get("/api/repos/colibri/status")
    assert resp_coli.status_code == 200
    assert resp_coli.json()["ok"] is True

    # 3. Task panopticon
    resp_tasks = client.get("/api/tasks/panopticon")
    assert resp_tasks.status_code == 200
    assert resp_tasks.json()["ok"] is True
