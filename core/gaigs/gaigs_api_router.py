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
gaigs_civilization_router = router
gaigs_media_router = media_router

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
    title: Optional[str] = "Civic Proposal"
    description: Optional[str] = ""
    category: str = "POLICY"
    proposal_text: Optional[str] = None

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
    title = req.title or (req.proposal_text[:40] if req.proposal_text else "Proposal")
    desc = req.description or req.proposal_text or ""
    assessment = engine.evaluate_islamic_ethics(title, desc, req.category)
    comp_score = getattr(assessment, "composite_ethics_score", 90.0) if hasattr(assessment, "composite_ethics_score") else assessment.get("ethics_score", 90.0)
    verdict = getattr(assessment, "verdict", "ETHICAL_APPROVED") if hasattr(assessment, "verdict") else assessment.get("verdict", "ETHICAL_APPROVED")
    rec = getattr(assessment, "recommendations", "") if hasattr(assessment, "recommendations") else assessment.get("recommendation", "")
    tawhid = getattr(assessment, "tawhid_coherence_score", 95) if hasattr(assessment, "tawhid_coherence_score") else 95
    adl = getattr(assessment, "adl_justice_score", 95) if hasattr(assessment, "adl_justice_score") else 95
    shura = getattr(assessment, "shura_consultation_score", 90) if hasattr(assessment, "shura_consultation_score") else 90
    amanah = getattr(assessment, "amanah_integrity_score", 90) if hasattr(assessment, "amanah_integrity_score") else 90
    rahmah = getattr(assessment, "rahmah_compassion_score", 90) if hasattr(assessment, "rahmah_compassion_score") else 90

    return {
        "ok": True,
        "assessment": assessment,
        "evaluation": {
            "composite_score": comp_score,
            "verdict": verdict,
            "breakdown": {
                "tawhid": tawhid,
                "adl": adl,
                "shura": shura,
                "amanah": amanah,
                "rahmah": rahmah,
            },
            "notes": rec
        }
    }

# Convenient aliases for GAIGS endpoints
@router.get("/proposals")
async def list_proposals_alias():
    return await list_proposals()

@router.post("/vote")
async def cast_vote_alias(req: VoteRequest):
    res = await cast_vote(req)
    if isinstance(res, dict) and "vote_receipt_hash" in res:
        res["vote_receipt"] = res["vote_receipt_hash"]
    return res

@router.get("/challenges")
async def list_challenges_alias():
    return await list_challenges()

@router.get("/transparency/spending")
async def get_transparency_spending_alias():
    engine = get_civilization_engine()
    return {"ok": True, "records": engine.get_transparency_ledger()}


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

class ScriptFlexibleRequest(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = "both"
    hook_style: Optional[str] = None
    topic: Optional[str] = None
    topic_focus: Optional[str] = None
    on_this_day: Optional[bool] = True
    date_str: Optional[str] = None

@media_router.post("/generate_script")
async def generate_script_alias(req: ScriptFlexibleRequest):
    engine = get_social_media_engine()
    topic = req.topic or req.topic_focus
    lang = "urdu" if req.language == "urdu" else ("english" if req.language == "english" else "both")
    scripts = engine.generate_daily_scripts(date_str=req.date_str, topic_focus=topic, language=lang)
    script = scripts[0] if scripts else None
    return {"ok": True, "script": script, "scripts": scripts, "generated_count": len(scripts)}

class ScriptApproveFlexibleRequest(BaseModel):
    script_id: str
    decision: Optional[str] = "APPROVED_YEH_DABAO"

@media_router.post("/approve_script")
async def approve_script_alias(req: ScriptApproveFlexibleRequest):
    engine = get_social_media_engine()
    res = engine.approve_script(req.script_id)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res
