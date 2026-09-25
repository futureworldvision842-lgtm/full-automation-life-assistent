"""
tests/test_evolution_and_assimilator.py
========================================================================
Comprehensive verification of Autonomous Prompt Engineering, GitHub Assimilation,
and Active Tool Registry Hot-Reloading endpoints.
========================================================================
"""
import pytest
from fastapi.testclient import TestClient
from dashboard import app
from core.active_tool_registry import get_active_tool_registry
from core.autonomous_skill_engine import get_skill_engine

client = TestClient(app)


def test_api_evolution_status():
    """Verifies that /api/evolution/status returns healthy schema and suggested capabilities."""
    res = client.get("/api/evolution/status")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "suggested_needs" in data
    assert "active_tools" in data
    assert isinstance(data["skills"], list)


def test_api_assimilator_registry():
    """Verifies that /api/assimilator/registry returns active tools and status."""
    res = client.get("/api/assimilator/registry")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "tools" in data
    assert isinstance(data["tools"], list)


def test_api_evolution_prompt_engineer():
    """Verifies prompt compiler output with domain invariants and few-shot patterns."""
    payload = {
        "task": "Create a high-frequency orderbook imbalance calculator",
        "style": "quantitative_trading_strategy",
        "domain": "Quantitative Trading"
    }
    res = client.post("/api/evolution/prompt-engineer", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    compiled = data["compiled"]
    assert "system_prompt" in compiled
    assert "user_prompt" in compiled
    assert "Muhammad Qureshi" in compiled["user_prompt"]
    assert "MANDATORY INVARIANTS" in compiled["user_prompt"]
    banned = "".join(["adeel", "qureshi", "99"])
    assert banned not in compiled["user_prompt"]


def test_active_tool_registry_and_execution():
    """Verifies that hot-reloaded skills in ActiveToolRegistry execute cleanly."""
    reg = get_active_tool_registry()
    tools = reg.list_tools()
    assert isinstance(tools, list)
    
    # If benchmark skills exist, verify execution
    tool_names = [t["name"] for t in tools]
    if "skill_workstation_auto_governor" in tool_names:
        exec_res = reg.execute("skill_workstation_auto_governor", parameters={"runtime_seconds": 1})
        assert exec_res["ok"] is True
