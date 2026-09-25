"""
core/gaigs/gaigs_api_router.py — FastAPI Router for GAIGS Civilization & Media Engine
=====================================================================================
Sovereign Master: Muhammad Qureshi
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.gaigs.civilization_engine import get_civilization_engine
from core.gaigs.social_media_automation import get_social_media_engine

router = APIRouter(prefix="/api/gaigs", tags=["GAIGS Civilization Upgrade"])
media_router = APIRouter(prefix="/api/media", tags=["Social Media Automation"])

# Request models
class ProposalCreateRequest(BaseModel):
    title: str = Field(..., description="Proposal title")
    category: str = Field(default="CIVIC_WELFARE", description="Category: INFRASTRUCTURE, CIVIC_WELFARE, etc.")
    author: str = Field(default="Muhammad Qureshi", description="Proposal author")
    description: str = Field(..., description="Detailed description")
    quorum_pct: float = Field(default=20.0, description="Required quorum percentage")

class VoteRequest(BaseModel):
    proposal_id: str
    voter_id: str
    choice: str = Field(..., description="FOR, AGAINST, or ABSTAIN")

class HubCreateRequest(BaseModel):
    name: str
    hub_type: str = "MASJID_MODEL"
    city: str
    country: str = "Pakistan"
    latitude: float
    longitude: float
    admin_lead: str
    services: Optional[List[str]] = None

class ExpenditureRequest(BaseModel):
    department: str
    purpose: str
    recipient: str
    amount_usd: float

class SolutionRequest(BaseModel):
    challenge_id: str
    contributor: str
    solution_title: str
    solution_abstract: str
    model_data: Optional[Dict[str, Any]] = None

class EthicsEvaluateRequest(BaseModel):
    title: str
    description: str
    category: str = "POLICY"

class ScriptGenerateRequest(BaseModel):
    date_str: Optional[str] = None
    topic_focus: Optional[str] = None
    language: str = "both"

class ScriptApproveRequest(BaseModel):
    script_id: str


# ---------------------------------------------------------------------------
# GAIGS Endpoints
# ---------------------------------------------------------------------------
@router.get("/overview")
async def get_overview():
    engine = get_civilization_engine()
    return engine.get_civilization_summary()

@router.get("/democracy/proposals")
async def list_proposals():
    engine = get_civilization_engine()
    return {"ok": True, "proposals": engine.list_proposals()}

@router.post("/democracy/proposals")
async def create_proposal(req: ProposalCreateRequest):
    engine = get_civilization_engine()
    prop = engine.submit_proposal(
        title=req.title,
        category=req.category,
        author=req.author,
        description=req.description,
        quorum_pct=req.quorum_pct
    )
    return {"ok": True, "proposal": prop}

@router.post("/democracy/vote")
async def cast_vote(req: VoteRequest):
    engine = get_civilization_engine()
    res = engine.cast_vote(req.proposal_id, req.voter_id, req.choice)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.get("/hubs")
async def list_hubs():
    engine = get_civilization_engine()
    return {"ok": True, "hubs": engine.list_hubs()}

@router.post("/hubs")
async def register_hub(req: HubCreateRequest):
    engine = get_civilization_engine()
    hub = engine.register_hub(
        name=req.name,
        hub_type=req.hub_type,
        city=req.city,
        country=req.country,
        latitude=req.latitude,
        longitude=req.longitude,
        admin_lead=req.admin_lead,
        services=req.services
    )
    return {"ok": True, "hub": hub}

@router.get("/transparency/ledger")
async def get_transparency():
    engine = get_civilization_engine()
    return {"ok": True, "ledger": engine.get_transparency_ledger()}

@router.post("/transparency/expenditure")
async def record_expenditure(req: ExpenditureRequest):
    engine = get_civilization_engine()
    entry = engine.record_expenditure(req.department, req.purpose, req.recipient, req.amount_usd)
    return {"ok": True, "entry": entry}

@router.get("/gamification/challenges")
async def list_challenges():
    engine = get_civilization_engine()
    return {"ok": True, "challenges": engine.list_challenges()}

@router.post("/gamification/solve")
async def solve_challenge(req: SolutionRequest):
    engine = get_civilization_engine()
    res = engine.submit_solution(
        challenge_id=req.challenge_id,
        contributor=req.contributor,
        solution_title=req.solution_title,
        solution_abstract=req.solution_abstract,
        scientific_model_data=req.model_data
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/ethics/evaluate")
async def evaluate_ethics(req: EthicsEvaluateRequest):
    engine = get_civilization_engine()
    assessment = engine.evaluate_islamic_ethics(req.title, req.description, req.category)
    return {"ok": True, "assessment": assessment}


# ---------------------------------------------------------------------------
# Media Endpoints
# ---------------------------------------------------------------------------
@media_router.get("/channels")
async def list_media_channels():
    engine = get_social_media_engine()
    return {"ok": True, "channels": engine.list_channels()}

@media_router.get("/scripts")
async def get_scripts():
    engine = get_social_media_engine()
    return {"ok": True, "scripts": engine.get_staged_scripts()}

@media_router.post("/scripts/generate")
async def generate_scripts(req: ScriptGenerateRequest):
    engine = get_social_media_engine()
    scripts = engine.generate_daily_scripts(
        date_str=req.date_str,
        topic_focus=req.topic_focus,
        language=req.language
    )
    return {"ok": True, "generated_count": len(scripts), "scripts": scripts}

@media_router.post("/scripts/approve")
async def approve_script(req: ScriptApproveRequest):
    engine = get_social_media_engine()
    res = engine.approve_script(req.script_id)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res
