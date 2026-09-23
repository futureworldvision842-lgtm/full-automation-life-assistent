"""
core/sovereign_api_router.py — FastAPI Router for Sovereign Capabilities
========================================================================
Unifies:
  1. Sovereign GitHub Tool Assimilator & Active Registry (/api/assimilator/*)
  2. CLI-Anything Cross-Platform Terminal Bridge (/api/cli_anything/*)
  3. Recursive Self-Evolution & SQLite WAL Telemetry (/api/evolution/*)
========================================================================
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.github_assimilator import GitHubAssimilator
from core.active_tool_registry import ActiveToolRegistry
from tools.cli_anything_bridge import CLIAnythingBridge
from core.self_evolution import SelfEvolutionKernel

logger = logging.getLogger("Jarvis.SovereignAPI")
router = APIRouter(prefix="/api", tags=["Sovereign Capabilities"])

# Singletons
_assimilator: Optional[GitHubAssimilator] = None
_tool_registry: Optional[ActiveToolRegistry] = None
_cli_bridge: Optional[CLIAnythingBridge] = None
_evolution_kernel: Optional[SelfEvolutionKernel] = None


def get_assimilator() -> GitHubAssimilator:
    global _assimilator
    if _assimilator is None:
        _assimilator = GitHubAssimilator()
    return _assimilator


def get_tool_registry() -> ActiveToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ActiveToolRegistry()
    return _tool_registry


def get_cli_bridge() -> CLIAnythingBridge:
    global _cli_bridge
    if _cli_bridge is None:
        _cli_bridge = CLIAnythingBridge()
    return _cli_bridge


def get_evolution_kernel() -> SelfEvolutionKernel:
    global _evolution_kernel
    if _evolution_kernel is None:
        _evolution_kernel = SelfEvolutionKernel()
    return _evolution_kernel


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class AssimilateRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or local path")
    target_name: Optional[str] = Field(default=None, description="Optional custom skill name")


class CLITerminalRequest(BaseModel):
    command: str = Field(..., description="Command to execute")
    shell: str = Field(default="auto", description="powershell, cmd, git_bash, wsl, auto")
    timeout: float = Field(default=30.0, description="Execution timeout in seconds")
    retries: int = Field(default=2, description="Auto-retry attempts on transient failure")


class CLISynthesizeRequest(BaseModel):
    workflow_name: str = Field(..., description="Workflow name: app_launch, file_export, browser_nav, data_pipeline")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters dictionary")


class RecipeStoreRequest(BaseModel):
    task_key: str = Field(..., description="Task identifier key")
    recipe: Dict[str, Any] = Field(..., description="Optimized execution recipe dictionary")


class BackupRequest(BaseModel):
    target_file: str = Field(..., description="Relative or absolute path of file to snapshot")


# -----------------------------------------------------------------------------
# 1. GITHUB ASSIMILATOR & ACTIVE TOOL REGISTRY ENDPOINTS
# -----------------------------------------------------------------------------

@router.post("/assimilator/assimilate", summary="Assimilate GitHub Repository")
async def assimilate_repo(payload: AssimilateRequest) -> Dict[str, Any]:
    """
    Autonomously clones a GitHub repository, extracts capabilities via AST,
    synthesizes a Python skill module, tests it in the sandbox, and hot-reloads it.
    """
    assimilator = get_assimilator()
    registry = get_tool_registry()
    kernel = get_evolution_kernel()

    t0 = time.perf_counter()
    try:
        # 1. Clone repository
        repo_dir = assimilator.clone_or_fetch(payload.repo_url)

        # 2. Extract capabilities
        caps = assimilator.extract_capabilities(repo_dir)

        # 3. Synthesize skills
        synthesized_skills = []
        for cap in caps:
            if payload.target_name:
                cap["module"] = payload.target_name
            skill_path = assimilator.synthesize_skill(cap)
            
            # Sandbox validation
            sandboxed = assimilator.test_in_sandbox(skill_path)
            if sandboxed:
                reload_res = assimilator.hot_reload_into_registry(skill_path)
                synthesized_skills.append({
                    "skill_name": skill_path.stem,
                    "path": str(skill_path),
                    "status": "LOADED" if reload_res.get("ok") else "FAILED",
                    "details": reload_res
                })

        latency = round((time.perf_counter() - t0) * 1000, 2)
        kernel.record_execution("assimilator_repo_ingest", latency, True)

        return {
            "ok": True,
            "repo_url": payload.repo_url,
            "capabilities_found": len(caps),
            "synthesized_skills": synthesized_skills,
            "active_tools_count": len(registry.list_tools()),
            "duration_ms": latency
        }
    except Exception as e:
        latency = round((time.perf_counter() - t0) * 1000, 2)
        kernel.record_execution("assimilator_repo_ingest", latency, False, str(e))
        return {
            "ok": False,
            "error": str(e),
            "duration_ms": latency
        }


@router.get("/assimilator/registry", summary="List Active Tool Registry")
def list_registry_tools() -> Dict[str, Any]:
    """Returns all currently loaded and registered dynamic skills."""
    registry = get_tool_registry()
    tools = registry.list_tools()
    return {
        "ok": True,
        "count": len(tools),
        "tools": tools
    }


# -----------------------------------------------------------------------------
# 2. CLI-ANYTHING CROSS-PLATFORM TERMINAL BRIDGE ENDPOINTS
# -----------------------------------------------------------------------------

@router.post("/cli_anything/execute", summary="Execute Cross-Platform Terminal Command")
def execute_cli_command(payload: CLITerminalRequest) -> Dict[str, Any]:
    """
    Executes a terminal command across PowerShell, CMD, Git Bash, or WSL2
    with automated retries, timeout guard, and BugCheck 0x7E crash prevention.
    """
    bridge = get_cli_bridge()
    kernel = get_evolution_kernel()

    res = bridge.execute_terminal(
        command=payload.command,
        shell=payload.shell,
        retries=payload.retries,
        timeout=payload.timeout
    )

    kernel.record_execution(
        f"cli_{payload.shell}",
        res.get("duration_ms", 10.0),
        res.get("ok", False),
        res.get("stderr") if not res.get("ok") else None
    )

    return res


@router.post("/cli_anything/synthesize", summary="Synthesize Declarative GUI-to-CLI Pipeline")
def synthesize_cli_pipeline(payload: CLISynthesizeRequest) -> Dict[str, Any]:
    """Translates a declarative GUI action into an optimized CLI command string."""
    bridge = get_cli_bridge()
    try:
        cmd = bridge.synthesize_cli_command(payload.workflow_name, payload.parameters)
        return {
            "ok": True,
            "workflow": payload.workflow_name,
            "synthesized_command": cmd
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


# -----------------------------------------------------------------------------
# 3. RECURSIVE SELF-EVOLUTION & TELEMETRY ENDPOINTS
# -----------------------------------------------------------------------------

@router.get("/evolution/telemetry", summary="Get Self-Evolution Telemetry & Health")
def get_evolution_telemetry(threshold_ms: float = 500.0) -> Dict[str, Any]:
    """
    Returns telemetry metrics from SQLite WAL trace memory:
    total traces, SLA degradation alerts, and active optimization recipes.
    """
    kernel = get_evolution_kernel()
    degraded = kernel.evaluate_performance_degradation(threshold_latency_ms=threshold_ms)

    import sqlite3
    conn = sqlite3.connect(str(kernel.db_path))
    try:
        trace_count = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        recent_traces = [
            {
                "id": r[0], "tool": r[1], "latency_ms": r[2],
                "success": bool(r[3]), "recorded_at": r[4]
            }
            for r in conn.execute(
                "SELECT id, tool_name, latency_ms, success, recorded_at FROM traces ORDER BY id DESC LIMIT 20"
            ).fetchall()
        ]
        recipe_keys = [
            r[0] for r in conn.execute("SELECT task_key FROM recipes ORDER BY optimized_at DESC LIMIT 50").fetchall()
        ]
    finally:
        conn.close()

    return {
        "ok": True,
        "db_path": str(kernel.db_path),
        "total_traces": trace_count,
        "recent_traces": recent_traces,
        "degraded_tools": degraded,
        "cached_recipe_keys": recipe_keys,
        "fundingpips_invariants": {
            "account": "40000294403",
            "max_risk_pct": 0.75,
            "max_risk_dollars": 750.0,
            "rr_target": 2.5,
            "breakeven_trigger_r": 1.0,
            "status": "COMPLIANT_LOCKED"
        }
    }


@router.post("/evolution/recipe", summary="Store Execution Optimization Recipe")
def store_recipe_endpoint(payload: RecipeStoreRequest) -> Dict[str, Any]:
    """Stores an execution recipe in the SQLite WAL recipes table."""
    kernel = get_evolution_kernel()
    kernel.store_recipe(payload.task_key, payload.recipe)
    return {
        "ok": True,
        "task_key": payload.task_key,
        "status": "STORED"
    }


@router.get("/evolution/recipe/{task_key}", summary="Get Execution Optimization Recipe")
def get_recipe_endpoint(task_key: str) -> Dict[str, Any]:
    """Retrieves a cached execution recipe by task key."""
    kernel = get_evolution_kernel()
    rec = kernel.get_optimized_recipe(task_key)
    if rec:
        return {"ok": True, "task_key": task_key, "recipe": rec}
    return {"ok": False, "error": f"Recipe not found for '{task_key}'"}


@router.post("/evolution/backup", summary="Create Atomic File Backup")
def create_backup_endpoint(payload: BackupRequest) -> Dict[str, Any]:
    """Creates a timestamped snapshot of a file in runtime/backups/."""
    kernel = get_evolution_kernel()
    target = ROOT / payload.target_file
    backup_path = kernel.create_atomic_backup(target)
    return {
        "ok": True,
        "target_file": str(target),
        "backup_path": str(backup_path),
        "timestamp": time.time()
    }
