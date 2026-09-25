"""
core/repo_api_router.py — FastAPI Router for Autonomous GitHub Assimilation & Task Panopticon
=============================================================================================
Sovereign Master: Muhammad Qureshi
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.autonomous_repo_orchestrator import get_repo_orchestrator
from core.llm.colibri_bridge import get_colibri_bridge

repo_router = APIRouter(prefix="/api/repos", tags=["GitHub Assimilation Panopticon"])
task_panopticon_router = APIRouter(prefix="/api/tasks", tags=["Task Panopticon & Telemetry"])


class RepoAssimilateRequest(BaseModel):
    repo: str = Field(..., description="GitHub repository URL or owner/name (e.g. JustVugg/colibri)")
    requested_by: Optional[str] = "Master Muhammad Qureshi"


class WhatsAppDirectiveRequest(BaseModel):
    sender: Optional[str] = "+923468053268"
    message: str = Field(..., description="Incoming WhatsApp message body")


class ColibriPlanRequest(BaseModel):
    model_name: Optional[str] = "GLM-5.2 (744B)"
    ram_budget_gb: Optional[int] = None
    ctx_len: Optional[int] = 2048


# -----------------------------------------------------------------------------
# GitHub Repository Panopticon Endpoints
# -----------------------------------------------------------------------------
@repo_router.get("/integrated")
async def list_integrated_repos():
    """Returns directory of all integrated GitHub repositories with capabilities and live status."""
    orch = get_repo_orchestrator()
    return {"ok": True, "repositories": orch.get_all_integrated_repos()}


@repo_router.post("/assimilate")
async def assimilate_repository(req: RepoAssimilateRequest):
    """Clones, inspects, extracts tools, and hot-registers a new GitHub repository into runtime."""
    orch = get_repo_orchestrator()
    res = orch.assimilate_new_repo(req.repo, requested_by=req.requested_by or "Master Muhammad Qureshi")
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@repo_router.get("/discover")
async def discover_repositories():
    """Returns curated trending open-source tools matching Master's domains."""
    orch = get_repo_orchestrator()
    return {"ok": True, "curated_discovery": orch.discover_trending_repos()}


# -----------------------------------------------------------------------------
# Colibrì MoE Inference Engine Endpoints
# -----------------------------------------------------------------------------
@repo_router.get("/colibri/status")
async def get_colibri_status():
    """Returns Colibrì engine hardware vitals, model support, and readiness."""
    bridge = get_colibri_bridge()
    return {"ok": True, "colibri": bridge.get_engine_status()}


@repo_router.post("/colibri/plan")
async def calculate_colibri_plan(req: ColibriPlanRequest):
    """Calculates MoE SSD expert streaming resource plan and token speed estimate."""
    bridge = get_colibri_bridge()
    plan = bridge.calculate_resource_plan(
        model_name=req.model_name or "GLM-5.2 (744B)",
        ram_budget_gb=req.ram_budget_gb,
        ctx_len=req.ctx_len or 2048
    )
    return plan


@repo_router.get("/colibri/doctor")
async def run_colibri_doctor():
    """Executes colibri doctor checks and reports operational health."""
    bridge = get_colibri_bridge()
    return bridge.run_doctor_diagnostics()


# -----------------------------------------------------------------------------
# WhatsApp Gateway Repo Directive Simulation
# -----------------------------------------------------------------------------
@repo_router.post("/whatsapp/process_directive")
async def process_whatsapp_directive(req: WhatsAppDirectiveRequest):
    """Processes incoming WhatsApp message containing repo directives and triggers auto-ingestion."""
    orch = get_repo_orchestrator()
    return orch.process_incoming_repo_directive(req.sender or "Master Muhammad", req.message)


# -----------------------------------------------------------------------------
# Cognitive Task Panopticon Endpoints
# -----------------------------------------------------------------------------
@task_panopticon_router.get("/panopticon")
async def get_task_panopticon():
    """Returns real-time streaming status of daemons, active tasks, history, and roadmap."""
    orch = get_repo_orchestrator()
    return orch.get_autonomous_execution_panopticon()
