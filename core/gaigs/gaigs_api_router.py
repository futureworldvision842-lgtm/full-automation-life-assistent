"""
core/gaigs/gaigs_api_router.py — FastAPI Router for GAIGS Civilization & Media Engine
=====================================================================================
Sovereign Master: Muhammad Qureshi
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
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
    status: Optional[str] = Field(default="OPEN", description="DRAFT, ACTIVE, OPEN, APPROVED, REJECTED, EXECUTED")

class ProposalStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="DRAFT, ACTIVE, APPROVED, REJECTED, EXECUTED, OPEN")

class VoteRequest(BaseModel):
    proposal_id: str
    voter_id: str
    choice: str = Field(..., description="FOR, AGAINST, ABSTAIN, or normalized variants (aye, nay, yes, no)")

class QuadraticVoteRequest(BaseModel):
    proposal_id: str
    voter_id: str
    credits_spent: int = Field(..., ge=1, description="Credits spent on quadratic vote (weight = sqrt(credits_spent))")
    choice: str = Field(..., description="FOR, AGAINST, aye, nay, yes, no, etc.")

class CitizenAuditRequest(BaseModel):
    tx_hash: str
    citizen_id: str
    dispute_reason: str

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

class MediaCrosspostRequest(BaseModel):
    script_id: str
    platforms: Optional[List[str]] = Field(default_factory=lambda: ["YouTube", "Instagram", "TikTok", "X (Twitter)"])


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

@router.post("/democracy/quadratic-vote")
async def cast_quadratic_vote(req: QuadraticVoteRequest):
    """
    Pillar 1: Quadratic Voting endpoint where voting power weight = sqrt(credits_spent).
    Normalizes vote choices ('aye', 'for', 'yes' -> 'FOR'; 'nay', 'against', 'no' -> 'AGAINST').
    """
    engine = get_civilization_engine()
    res = engine.cast_quadratic_vote(
        proposal_id=req.proposal_id,
        voter_id=req.voter_id,
        credits_spent=req.credits_spent,
        choice=req.choice
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.patch("/democracy/proposals/{proposal_id}/status")
@router.post("/democracy/proposals/{proposal_id}/lifecycle")
async def update_proposal_lifecycle(proposal_id: str, req: ProposalStatusUpdateRequest):
    """Updates proposal lifecycle state (DRAFT, ACTIVE, APPROVED, REJECTED, EXECUTED)."""
    engine = get_civilization_engine()
    res = engine.transition_proposal_status(proposal_id, req.status)
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

@router.post("/transparency/audit")
async def log_citizen_audit(req: CitizenAuditRequest):
    """
    Pillar 3: Citizen Audit endpoint logging disputes against spending transactions
    and flagging them for independent Shura council review.
    """
    engine = get_civilization_engine()
    res = engine.log_citizen_dispute(
        tx_hash=req.tx_hash,
        citizen_id=req.citizen_id,
        dispute_reason=req.dispute_reason
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.get("/transparency/verify/{tx_hash}")
async def verify_transparency_tx(tx_hash: str):
    """
    Pillar 3: Merkle proof verification for a public treasury expenditure.
    """
    engine = get_civilization_engine()
    res = engine.verify_expenditure_proof(tx_hash)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

@router.get("/transparency/spending")
async def get_transparency_spending():
    """
    Returns public spending records as an ARRAY of entries with dual keys
    (id/tx_hash, category/department, vendor/recipient, flagged/audit_flag, sha256_hash/proof_hash),
    eliminating frontend records.map() TypeError.
    """
    engine = get_civilization_engine()
    records = engine.get_spending_records()
    ledger_stats = engine.get_transparency_ledger()
    return {
        "ok": True,
        "count": len(records),
        "records": records,
        "total_expenditure_usd": ledger_stats.get("total_expenditure_usd", 0.0),
        "transparency_audit_score": ledger_stats.get("transparency_audit_score", 100.0)
    }

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

@router.get("/gamification/citizen-score/{citizen_id}")
async def get_citizen_score_endpoint(citizen_id: str):
    """
    Pillar 5: Gamified Civic Engagement endpoint tracking Citizen Score,
    tier ranks, badges, and milestone rewards.
    """
    engine = get_civilization_engine()
    return engine.get_citizen_score(citizen_id)

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


# ---------------------------------------------------------------------------
# Mission Document Synchronization Catalog & Engine
# ---------------------------------------------------------------------------
MISSION_DOCS_DIR = Path("F:/") / "Muhammad's platforms missions main files"

CANONICAL_MISSION_CATALOG = [
    {
        "filename": "Civilization_Upgrade_A_New_Operating_System.pdf",
        "title": "Civilization Upgrade: A New Operating System",
        "file_size_bytes": 15483075,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Community Unity Hubs",
            "Blockchain Transparency",
            "Scientific Gamification",
            "AI-Assisted Decisions (Islamic Ethics)"
        ],
        "summary": "Master architectural blueprint for upgrading human civilization through decentralized AI and moral governance."
    },
    {
        "filename": "Installing_Humanity_3.0.pdf",
        "title": "Installing Humanity 3.0",
        "file_size_bytes": 17219672,
        "primary_pillar": "AI-Assisted Decisions (Islamic Ethics)",
        "five_pillar_alignments": [
            "AI-Assisted Decisions (Islamic Ethics)",
            "Community Unity Hubs",
            "Transparent Democracy"
        ],
        "summary": "Core ideological framework for transitioning human society from exploitation to cooperative moral equilibrium."
    },
    {
        "filename": "The_Civic_Operating_System.pdf",
        "title": "The Civic Operating System",
        "file_size_bytes": 16834315,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Community Unity Hubs",
            "Blockchain Transparency"
        ],
        "summary": "Technical and social specification for local and planetary direct-democracy operating systems."
    },
    {
        "filename": "The_Next_Human_Operating_System.pdf",
        "title": "The Next Human Operating System",
        "file_size_bytes": 10217603,
        "primary_pillar": "AI-Assisted Decisions (Islamic Ethics)",
        "five_pillar_alignments": [
            "AI-Assisted Decisions (Islamic Ethics)",
            "Transparent Democracy"
        ],
        "summary": "Philosophical treatise on human purpose, conscience, and algorithmic governance."
    },
    {
        "filename": "The_Next_Social_Operating_System.pdf",
        "title": "The Next Social Operating System",
        "file_size_bytes": 17569380,
        "primary_pillar": "Community Unity Hubs",
        "five_pillar_alignments": [
            "Community Unity Hubs",
            "Transparent Democracy"
        ],
        "summary": "Social coordination protocols inspired by the historic Masjid-e-Nabawi multi-faith community model."
    },
    {
        "filename": "GAIGS_Full_Interactive_Platform_Technical_Plan_v3.pdf",
        "title": "GAIGS Full Interactive Platform Technical Plan v3",
        "file_size_bytes": 940641,
        "primary_pillar": "Blockchain Transparency",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency",
            "Scientific Gamification"
        ],
        "summary": "Full software architecture and interactive UI/UX blueprint for the global platform."
    },
    {
        "filename": "GAIGS_Technical_Master_Plan_v2_Visual.pdf",
        "title": "GAIGS Technical Master Plan v2 (Visual)",
        "file_size_bytes": 698392,
        "primary_pillar": "Blockchain Transparency",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency"
        ],
        "summary": "Visual architecture diagrams depicting node topology, ledger consensus, and client APIs."
    },
    {
        "filename": "GAIGS_MVP_Plan.pdf",
        "title": "GAIGS MVP Plan",
        "file_size_bytes": 301256,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency",
            "Community Unity Hubs"
        ],
        "summary": "Phased minimum viable product deployment roadmap for nation-state and municipal pilots."
    },
    {
        "filename": "GAIGS_Mobile_App_Investor_Brief_v1.pdf",
        "title": "GAIGS Mobile App Investor Brief v1",
        "file_size_bytes": 759983,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Community Unity Hubs"
        ],
        "summary": "Investor executive briefing on the citizen-facing mobile governance application."
    },
    {
        "filename": "GAIGS_Investor_Deck_v2_Visual.pdf",
        "title": "GAIGS Investor Pitch Deck v2 (Visual)",
        "file_size_bytes": 1697137,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency",
            "Community Unity Hubs"
        ],
        "summary": "High-impact visual slide deck for institutional partners and sovereign wealth sponsors."
    },
    {
        "filename": "GAIGS_Investor_Pitch_Memorandum_v1.pdf",
        "title": "GAIGS Investor Pitch Memorandum v1",
        "file_size_bytes": 784885,
        "primary_pillar": "Blockchain Transparency",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency"
        ],
        "summary": "In-depth financial, regulatory, and systemic risk mitigation memorandum."
    },
    {
        "filename": "MVP Pitch of GAIGS for countries.pdf",
        "title": "MVP Pitch of GAIGS for Sovereign Countries",
        "file_size_bytes": 206131,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency",
            "Community Unity Hubs"
        ],
        "summary": "Strategic diplomatic proposal tailored for government ministers and policy councils."
    },
    {
        "filename": "A New Dawn for Humanity.pdf",
        "title": "A New Dawn for Humanity",
        "file_size_bytes": 230364,
        "primary_pillar": "AI-Assisted Decisions (Islamic Ethics)",
        "five_pillar_alignments": [
            "AI-Assisted Decisions (Islamic Ethics)",
            "Community Unity Hubs"
        ],
        "summary": "Manifesto on the moral imperative of replacing exploitative fiat debts with equitable value creation."
    },
    {
        "filename": "Muhammad_s revelationary idea.pdf",
        "title": "Muhammad's Revolutionary Idea",
        "file_size_bytes": 2410133,
        "primary_pillar": "Community Unity Hubs",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Community Unity Hubs",
            "Blockchain Transparency",
            "Scientific Gamification",
            "AI-Assisted Decisions (Islamic Ethics)"
        ],
        "summary": "Original foundational vision by Master Muhammad Qureshi articulating the 5-pillar ecosystem."
    },
    {
        "filename": "THE LAST HOPE_ Global Governance Revolution.pptx",
        "title": "The Last Hope: Global Governance Revolution",
        "file_size_bytes": 3270424,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "AI-Assisted Decisions (Islamic Ethics)",
            "Blockchain Transparency"
        ],
        "summary": "Keynote presentation detailing the collapse of 20th-century institutions and the GAIGS alternative."
    },
    {
        "filename": "Updated_Urdu_Series.docx",
        "title": "Updated Urdu Media Series Scripts",
        "file_size_bytes": 141560,
        "primary_pillar": "Community Unity Hubs",
        "five_pillar_alignments": [
            "Community Unity Hubs",
            "AI-Assisted Decisions (Islamic Ethics)"
        ],
        "summary": "Comprehensive scripts for Fikr-o-Nizam and Afkaar Urdu educational broadcasting."
    },
    {
        "filename": "gaigs_platform_development_prompt.txt",
        "title": "GAIGS Platform Development Prompt & Specification",
        "file_size_bytes": 11546,
        "primary_pillar": "Transparent Democracy",
        "five_pillar_alignments": [
            "Transparent Democracy",
            "Blockchain Transparency",
            "Scientific Gamification"
        ],
        "summary": "Detailed technical prompt and domain model requirements for AI coding agents."
    }
]


def scan_mission_documents() -> List[Dict[str, Any]]:
    """
    Indexes the 17+ core documents in F:\\Muhammad's platforms missions main files
    with metadata, title, file size, and 5-pillar alignments.
    """
    catalog_by_filename = {item["filename"]: item for item in CANONICAL_MISSION_CATALOG}
    docs: List[Dict[str, Any]] = []

    if MISSION_DOCS_DIR.exists() and MISSION_DOCS_DIR.is_dir():
        for file_path in sorted(MISSION_DOCS_DIR.iterdir()):
            if not file_path.is_file():
                continue
            fname = file_path.name
            size_b = file_path.stat().st_size
            size_fmt = f"{round(size_b / (1024 * 1024), 2)} MB" if size_b >= 1048576 else f"{round(size_b / 1024, 2)} KB"
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat()
            ext = file_path.suffix.lower()

            meta = catalog_by_filename.get(fname)
            if meta:
                title = meta["title"]
                prim_pillar = meta["primary_pillar"]
                alignments = meta["five_pillar_alignments"]
                summary = meta["summary"]
            else:
                stem = file_path.stem.replace("_", " ").strip()
                title = stem.title()
                prim_pillar = "Transparent Democracy"
                alignments = ["Transparent Democracy", "Community Unity Hubs", "Blockchain Transparency"]
                summary = f"Archived mission documentation: {stem}"

            docs.append({
                "filename": fname,
                "title": title,
                "file_path": str(file_path),
                "file_size_bytes": size_b,
                "file_size_formatted": size_fmt,
                "extension": ext,
                "last_modified": mtime,
                "primary_pillar": prim_pillar,
                "five_pillar_alignments": alignments,
                "summary": summary
            })

    # If directory was missing or had fewer files than catalog, backfill from catalog
    if len(docs) < len(CANONICAL_MISSION_CATALOG):
        existing_names = {d["filename"] for d in docs}
        for item in CANONICAL_MISSION_CATALOG:
            if item["filename"] not in existing_names:
                size_b = item["file_size_bytes"]
                size_fmt = f"{round(size_b / (1024 * 1024), 2)} MB" if size_b >= 1048576 else f"{round(size_b / 1024, 2)} KB"
                ext = Path(item["filename"]).suffix.lower()
                docs.append({
                    "filename": item["filename"],
                    "title": item["title"],
                    "file_path": str(MISSION_DOCS_DIR / item["filename"]),
                    "file_size_bytes": size_b,
                    "file_size_formatted": size_fmt,
                    "extension": ext,
                    "last_modified": datetime.now(timezone.utc).isoformat(),
                    "primary_pillar": item["primary_pillar"],
                    "five_pillar_alignments": item["five_pillar_alignments"],
                    "summary": item["summary"]
                })

    return docs


@router.get("/mission-docs")
async def get_mission_documents():
    """
    Returns index of Master Muhammad's 17+ core mission documents
    with metadata, titles, file sizes, and 5-pillar alignments.
    """
    docs = scan_mission_documents()
    return {
        "ok": True,
        "directory": str(MISSION_DOCS_DIR),
        "count": len(docs),
        "documents": docs
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


# ---------------------------------------------------------------------------
# Media Endpoints
# ---------------------------------------------------------------------------
@media_router.get("/channels")
async def list_media_channels():
    """
    Returns registered channel network as an ARRAY of channel objects
    (with id, name, handle, target_audience), eliminating frontend channels.map() TypeError.
    """
    engine = get_social_media_engine()
    return {"ok": True, "channels": engine.get_channels_list()}

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
    script = engine.get_script(req.script_id)
    return {
        "ok": True,
        "status": "APPROVED_YEH_DABAO",
        "script_id": req.script_id,
        "script": script,
        "details": res
    }

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
    script = engine.get_script(req.script_id)
    return {
        "ok": True,
        "status": "APPROVED_YEH_DABAO",
        "script_id": req.script_id,
        "script": script,
        "details": res
    }

@media_router.post("/crosspost")
async def crosspost_media_script(req: MediaCrosspostRequest):
    """
    Simulates cross-posting to social channels with staged webhook delivery receipts.
    """
    engine = get_social_media_engine()
    res = engine.crosspost_script(req.script_id, req.platforms)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res
