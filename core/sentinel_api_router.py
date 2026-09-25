"""
core/sentinel_api_router.py — FastAPI endpoints for Self-Healing Sentinel
========================================================================
Exposes:
1. GET /api/sentinel/diagnose: Real-time scan of daemons, thermals, RAM, and held tasks.
2. POST /api/sentinel/heal: Runs automated self-repair first and reports held interventions.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter
from core.self_healing_sentinel import get_self_healing_sentinel

sentinel_router = APIRouter(prefix="/api/sentinel", tags=["self_healing_sentinel"])


@sentinel_router.get("/diagnose")
async def get_system_diagnosis() -> Dict[str, Any]:
    """Scans all system daemons, hardware thermals, memory, and held tasks."""
    sentinel = get_self_healing_sentinel()
    return sentinel.diagnose_system()


@sentinel_router.post("/heal")
async def trigger_auto_healing() -> Dict[str, Any]:
    """Executes automated self-healing cycle and reports remaining human-in-the-loop tasks."""
    sentinel = get_self_healing_sentinel()
    return sentinel.auto_heal()
