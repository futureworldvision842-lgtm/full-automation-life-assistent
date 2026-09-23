"""
core/cua_api_router.py — FastAPI Router for CUA (Computer-Use-Agent) Visual Browser
===================================================================================
Endpoints:
  - POST /api/cua/session/init: Initializes CUA session (headless, cdp_url, viewport)
  - POST /api/cua/inspect: Inspects viewport, returning grounded elements and SoM frame
  - POST /api/cua/action: Dispatches web action (click, type, scroll, submit, etc.)
  - POST /api/cua/extract_table: Extracts structured data from page table
  - GET  /api/cua/stream: Live MJPEG frame stream (multipart/x-mixed-replace)
  - POST /api/cua/session/close: Closes active session cleanly
  - GET  /api/cua/status: Returns session status and current configuration
  - POST /api/cua/mode: Toggles between headless research and interactive operator mode
===================================================================================
"""

from __future__ import annotations

import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cua_browser_engine import CUABrowserEngine

logger = logging.getLogger("Jarvis.CUAAPIRouter")

router = APIRouter(prefix="/api/cua", tags=["CUA Visual Browser"])

# Singleton engine instance
_cua_engine: Optional[CUABrowserEngine] = None


def get_cua_engine() -> CUABrowserEngine:
    """Returns or lazily creates the singleton CUABrowserEngine."""
    global _cua_engine
    if _cua_engine is None:
        _cua_engine = CUABrowserEngine()
    return _cua_engine


def set_cua_engine(engine: CUABrowserEngine) -> None:
    """Overrides the engine instance (primarily for isolated test fixtures)."""
    global _cua_engine
    _cua_engine = engine


# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------

class InitSessionRequest(BaseModel):
    headless: bool = Field(default=True, description="Run headless or interactive")
    cdp_url: Optional[str] = Field(default=None, description="Optional CDP URL to attach to")
    viewport: Optional[Dict[str, int]] = Field(default=None, description="Viewport width and height")


class ActionRequest(BaseModel):
    action_type: str = Field(..., description="Action: click, right_click, type, scroll, navigate, submit, press_key")
    element_id: Optional[int] = Field(default=None, description="Numeric target element ID from inspect_viewport")
    coordinates: Optional[List[int]] = Field(default=None, description="Explicit [x, y] coordinates")
    text: Optional[str] = Field(default=None, description="Text for type or navigate action")
    key: Optional[str] = Field(default=None, description="Key for press_key action")


class ExtractTableRequest(BaseModel):
    selector: Optional[Any] = Field(default=None, description="CSS selector or element identifier")
    selector_or_element_id: Optional[Any] = Field(default=None, description="Alternative selector parameter")


class ModeRequest(BaseModel):
    mode: str = Field(default="headless", description="'headless' or 'interactive'")


# -----------------------------------------------------------------------------
# API Route Implementations
# -----------------------------------------------------------------------------

@router.post("/session/init", summary="Initialize CUA Session")
async def init_session(payload: Optional[InitSessionRequest] = None) -> Dict[str, Any]:
    """Initializes Playwright/Chromium session or attaches over CDP."""
    engine = get_cua_engine()
    headless = payload.headless if payload else True
    cdp_url = payload.cdp_url if payload else None
    viewport = payload.viewport if payload else None

    ok = await engine.initialize_session(
        headless=headless,
        cdp_url=cdp_url,
        viewport=viewport
    )
    return {
        "ok": ok,
        "status": "INITIALIZED" if ok else "FAILED",
        "headless": engine.headless,
        "viewport": engine.viewport,
        "url": engine.current_url
    }


@router.post("/inspect", summary="Inspect Visual Viewport")
async def inspect_viewport() -> Dict[str, Any]:
    """Inspects current page viewport, returns grounded elements and SoM frame."""
    engine = get_cua_engine()
    state = await engine.inspect_viewport()
    return state


@router.post("/action", summary="Dispatch Web Action")
async def execute_action(payload: ActionRequest) -> Dict[str, Any]:
    """Dispatches web action with pre-action verification and zero drift guarantee."""
    engine = get_cua_engine()
    result = await engine.execute_action(
        action_type=payload.action_type,
        element_id=payload.element_id,
        coordinates=payload.coordinates,
        text=payload.text,
        key=payload.key
    )
    return result


@router.post("/extract_table", summary="Extract Structured Table Data")
async def extract_table(payload: Optional[ExtractTableRequest] = None) -> Dict[str, Any]:
    """Parses HTML table or grid data into structured row dictionaries."""
    engine = get_cua_engine()
    sel = None
    if payload:
        sel = payload.selector if payload.selector is not None else payload.selector_or_element_id

    rows = await engine.extract_table_data(sel)
    return {
        "ok": True,
        "selector": sel,
        "rows": rows,
        "count": len(rows)
    }


@router.get("/stream", summary="Live MJPEG Viewport Stream")
async def stream_viewport(request: Request):
    """Multipart MJPEG video stream of the live browser viewport."""
    engine = get_cua_engine()

    async def frame_generator():
        while True:
            if await request.is_disconnected():
                break
            frame = await engine.stream_viewport_frame()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
            await asyncio.sleep(0.04)  # ~25 FPS stream rate

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/session/close", summary="Close Active CUA Session")
async def close_session() -> Dict[str, Any]:
    """Closes the active CUA session and cleans up resources."""
    engine = get_cua_engine()
    await engine.close()
    return {
        "ok": True,
        "status": "CLOSED",
        "initialized": engine.initialized
    }


@router.get("/status", summary="Get CUA Engine Status")
async def get_status() -> Dict[str, Any]:
    """Returns engine health, mode, viewport geometry, and active URL."""
    engine = get_cua_engine()
    return {
        "ok": True,
        "initialized": engine.initialized,
        "headless": engine.headless,
        "url": engine.current_url,
        "viewport": engine.viewport,
        "cdp_url": engine.cdp_url
    }


@router.post("/mode", summary="Toggle CUA Mode")
async def toggle_mode(payload: ModeRequest) -> Dict[str, Any]:
    """Toggles mode between headless research and interactive operator assistance."""
    engine = get_cua_engine()
    res = engine.set_mode(payload.mode)
    return res
