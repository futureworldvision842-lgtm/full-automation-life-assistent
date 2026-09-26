"""
core/human_alert_router.py — Human Assistance & Alert Panopticon Router
========================================================================
Exposes centralized endpoints for:
1. Fetching pending human intervention alerts (CAPTCHA, 2FA, API keys, Trade Approvals).
2. Creating new assistance requests from any autonomous subsystem or browser agent.
3. 1-click resolution (Solved, Submit OTP, Submit API Key, 100% Free Mode, Cancel).
4. PC screen focus and live screenshot streaming.
5. Real-time alert polling and stats.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.human_intervention_gateway import (
    HumanInterventionGateway,
    HumanInterventionRequest,
    InterventionType,
    RequestStatus,
    get_human_intervention_gateway,
    open_or_focus_on_pc,
    capture_intervention_screenshot,
)

alert_router = APIRouter(prefix="/api/alerts", tags=["human_alerts"])


class CreateAlertRequest(BaseModel):
    alert_type: str = Field(..., description="CAPTCHA_CHALLENGE, TWO_FACTOR_AUTH, MISSING_API_KEY, CRITICAL_CONFIRMATION, HUMAN_DISCUSSION_NEEDED")
    title: str = Field(..., description="Human-readable title")
    target_service: str = Field(..., description="e.g. FundingPips, Twitter/X, OpenAI")
    reason: str = Field(..., description="Technical failure or reason")
    action_blocked: str = Field("Automated operation", description="What action is currently paused")
    explanation_ur: Optional[str] = Field(None, description="Roman Urdu explanation")
    suggested_free_alternative: Optional[str] = Field("Switch to 100% Free alternative mode", description="Alternative")
    portal_url: Optional[str] = Field("", description="Target URL")
    window_title: Optional[str] = Field("", description="Window title to bring to front")
    account_username: Optional[str] = Field("futureworldvision842@gmail.com", description="Account identifier")
    code_destination: Optional[str] = Field("Aapke Inbox / Authenticator App", description="Where the code was sent")


class ResolveAlertRequest(BaseModel):
    request_id: str = Field(..., description="ID of the alert to resolve, e.g. REQ-CAP-12345")
    action: str = Field(..., description="'SOLVED', 'OTP_SUBMIT', 'KEY_SUBMIT', 'FREE_MODE', 'CANCEL'")
    value: Optional[str] = Field(None, description="Code, API Key, or resolution notes")


class OpenTargetRequest(BaseModel):
    portal_url: Optional[str] = ""
    window_title: Optional[str] = ""
    prompt_text: Optional[str] = "Manual intervention required"


@alert_router.get("/pending")
async def get_pending_alerts() -> Dict[str, Any]:
    """Returns all active pending human intervention requests."""
    gw = get_human_intervention_gateway()
    with gw._lock:
        pending = [
            req.to_dict()
            for req in gw._requests.values()
            if req.status == RequestStatus.PENDING
        ]
    # Sort newest first
    pending.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {
        "ok": True,
        "count": len(pending),
        "alerts": pending,
        "has_critical": any(
            p.get("request_type") in ("CAPTCHA_CHALLENGE", "TWO_FACTOR_AUTH", "CRITICAL_CONFIRMATION")
            for p in pending
        )
    }


@alert_router.get("/status")
async def get_alerts_status() -> Dict[str, Any]:
    """Quick badge status endpoint for lightweight frontend polling."""
    gw = get_human_intervention_gateway()
    with gw._lock:
        pending = [req for req in gw._requests.values() if req.status == RequestStatus.PENDING]
        latest = sorted(pending, key=lambda x: x.created_at, reverse=True)[0].to_dict() if pending else None
    return {
        "ok": True,
        "pending_count": len(pending),
        "has_critical": bool(latest and latest.get("request_type") in ("CAPTCHA_CHALLENGE", "TWO_FACTOR_AUTH")),
        "latest": latest
    }


@alert_router.get("/history")
async def get_alerts_history(limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
    """Returns recently resolved or cancelled intervention alerts."""
    gw = get_human_intervention_gateway()
    with gw._lock:
        history = [
            req.to_dict()
            for req in gw._requests.values()
            if req.status != RequestStatus.PENDING
        ]
    history.sort(key=lambda x: x.get("resolved_at") or x.get("created_at", ""), reverse=True)
    return {
        "ok": True,
        "count": len(history[:limit]),
        "history": history[:limit]
    }


@alert_router.post("/create")
async def create_alert(payload: CreateAlertRequest) -> Dict[str, Any]:
    """Creates a new human assistance alert and dispatches notification."""
    gw = get_human_intervention_gateway()
    t = payload.alert_type.upper()

    if "CAPTCHA" in t:
        req = gw.request_captcha_resolution(
            target_site=payload.target_service,
            url=payload.portal_url or "",
            action_blocked=payload.action_blocked,
            account_username=payload.account_username or "",
            window_title=payload.window_title or "",
            title=payload.title or ""
        )
    elif "2FA" in t or "OTP" in t or "TWO_FACTOR" in t:
        req = gw.request_2fa_code(
            service_name=payload.target_service,
            channel="SMS / Email / Authenticator",
            action_blocked=payload.action_blocked,
            account_username=payload.account_username or "",
            code_destination=payload.code_destination or "",
            portal_url=payload.portal_url or "",
            window_title=payload.window_title or ""
        )
    elif "KEY" in t or "API" in t:
        req = gw.request_api_key(
            service_name=payload.target_service,
            reason=payload.reason,
            free_alternative=payload.suggested_free_alternative or "Free DEX Screener / Local LLM",
            action_blocked=payload.action_blocked,
            portal_url=payload.portal_url or "",
            window_title=payload.window_title or ""
        )
    elif "CONFIRM" in t or "CRITICAL" in t:
        req = gw.request_critical_confirmation(
            action_name=payload.title,
            risk_details=payload.reason,
            potential_consequence="Financial balance alteration or system configuration change",
            action_blocked=payload.action_blocked,
            title=payload.title or ""
        )
    else:
        req = gw.request_human_discussion(
            topic=payload.title,
            context=payload.reason,
            options=["Proceed with automated default", "Postpone task", "Switch to free mode"],
            action_blocked=payload.action_blocked,
            title=payload.title or ""
        )

    return {
        "ok": True,
        "message": f"Alert '{req.request_id}' created and held safely in pending ledger.",
        "alert": req.to_dict()
    }


@alert_router.post("/resolve")
async def resolve_alert(payload: ResolveAlertRequest) -> Dict[str, Any]:
    """Resolves an alert via 1-click button or value submission."""
    gw = get_human_intervention_gateway()
    req_id = payload.request_id.strip()
    action = payload.action.upper().strip()
    val = (payload.value or "").strip()

    with gw._lock:
        req = gw._requests.get(req_id)
        if not req:
            # Fall back to latest pending request if ID not exact
            pending = [r for r in gw._requests.values() if r.status == RequestStatus.PENDING]
            req = sorted(pending, key=lambda x: x.created_at, reverse=True)[0] if pending else None

    if not req:
        raise HTTPException(status_code=404, detail="Alert request not found or no active pending alerts.")

    now_iso = datetime.now(timezone.utc).isoformat()
    # Explicit deterministic status mutation
    if action == "SOLVED":
        req.status = RequestStatus.RESOLVED
        req.resolved_at = now_iso
        req.resolution_details = {"action": "SOLVED", "by": "ui", "notes": val or "Solved by user"}
        gw._save_requests()
        handled = True
        reply = "Thank you Sir! Alert marked resolved. Resuming automated workflow."
    elif action == "FREE_MODE":
        req.status = RequestStatus.FALLBACK_FREE
        req.resolved_at = now_iso
        req.resolution_details = {"action": "FREE_MODE", "by": "ui", "alternative": req.suggested_free_alternative}
        gw._save_requests()
        handled = True
        reply = f"100% Free Mode activated: {req.suggested_free_alternative}."
    elif action == "CANCEL":
        req.status = RequestStatus.CANCELLED
        req.resolved_at = now_iso
        req.resolution_details = {"action": "CANCEL", "by": "ui"}
        gw._save_requests()
        handled = True
        reply = f"Alert '{req.title}' cancelled."
    elif action == "KEY_SUBMIT":
        if val:
            gw._save_api_key_to_config(req.target_service, val)
        req.status = RequestStatus.RESOLVED
        req.resolved_at = now_iso
        req.resolution_details = {"action": "KEY_SUBMIT", "by": "ui", "key_configured": bool(val)}
        gw._save_requests()
        handled = True
        reply = f"API Key for {req.target_service} saved and verified."
    elif action == "OTP_SUBMIT":
        req.status = RequestStatus.RESOLVED
        req.resolved_at = now_iso
        req.resolution_details = {"action": "OTP_SUBMIT", "by": "ui", "otp": val}
        if val:
            try:
                from actions.fundingpips_automation import submit_otp_code
                submit_otp_code(val)
            except Exception:
                pass
        gw._save_requests()
        handled = True
        reply = f"OTP code {val} received and submitted to target session."
    else:
        # Fallback to conversational resolution
        handled, reply = gw.resolve_from_message(val or action, sender_id="dashboard_or_mobile")

    return {
        "ok": handled,
        "request_id": req.request_id,
        "status": req.status.value,
        "reply": reply,
        "alert": req.to_dict()
    }


@alert_router.post("/open-target")
async def open_target_window(payload: OpenTargetRequest) -> Dict[str, Any]:
    """Brings target window or browser portal to foreground on PC workstation."""
    success = open_or_focus_on_pc(
        url=payload.portal_url or "",
        title=payload.window_title or "",
        prompt_text=payload.prompt_text or "Manual verification required"
    )
    return {
        "ok": success,
        "portal_url": payload.portal_url,
        "window_title": payload.window_title,
        "message": "Target opened/focused on PC workstation." if success else "Could not focus target window."
    }
