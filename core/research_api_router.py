"""
core/research_api_router.py — FastAPI Router for Institutional Market Research Hub.
Exposes:
  1. GET /api/research/forex/macro  — 28-pair Currency Strength, Rate Differentials, News Blackout Buffer.
  2. GET /api/research/crypto/memes — Solana Raydium & Pump.fun Alpha Stream with safety & whale audits.
  3. GET /api/research/crypto/gems  — Fundamental Blue-Chip & Spot Crypto Dossiers with quantitative valuation.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.research.macro_surveillance import get_macro_surveillance_engine
from core.research.meme_alpha_stream import get_meme_alpha_streamer
from core.research.spot_crypto_dossier import get_spot_crypto_dossier_engine

logger = logging.getLogger("Jarvis.ResearchAPI")

router = APIRouter(prefix="/api/research", tags=["Institutional Market Research"])


@router.get("/forex/macro")
async def get_forex_macro_surveillance(
    symbol: str = Query("ALL", description="Target Forex pair or ALL for universal macro matrix")
) -> Dict[str, Any]:
    """
    Returns real-time 28-pair Currency Strength Meter (CSM), Central Bank Interest Rate Differentials,
    and 15-minute Pre/Post High-Impact Economic News Blackout Buffer.
    """
    engine = get_macro_surveillance_engine()
    report = engine.get_macro_surveillance_report(symbol=symbol)
    return JSONResponse(content=report)


@router.get("/crypto/memes")
async def get_crypto_meme_alpha(
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum composite conviction score"),
    graduating_only: bool = Query(False, description="Filter for bonding curve >= 75% graduating soon"),
    whale_only: bool = Query(False, description="Filter for whale accumulation index >= 60.0"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tokens to return"),
    stream: bool = Query(False, description="Stream token updates via Server-Sent Events (SSE)")
):
    """
    Delivers scored and audited Solana Pump.fun and Raydium meme tokens with bonding curve velocity,
    whale accumulation index, LP burn/lock verification, dev wallet safety audit, and composite score.
    Supports real-time SSE streaming via ?stream=true.
    """
    streamer = get_meme_alpha_streamer()
    if stream:
        return StreamingResponse(
            streamer.event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    report = streamer.get_meme_research_report(
        min_score=min_score,
        graduating_only=graduating_only,
        whale_accumulating_only=whale_only,
        limit=limit
    )
    return JSONResponse(content=report)


@router.get("/crypto/gems")
async def get_crypto_spot_gems(
    symbol: Optional[str] = Query(None, description="Asset symbol filter (e.g. SOL, BTC, ETH, NEAR, SUI, RENDER, TAO, INJ, LINK, AAVE)"),
    category: Optional[str] = Query(None, description="Category filter (e.g. L1, DePIN, AI, DeFi, Oracle)"),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum composite fundamental score")
) -> Dict[str, Any]:
    """
    Delivers institutional fundamental dossiers for prospective spot crypto assets and blue-chips:
    historical drawdown distributions, tokenomics schedules, developer commit activity,
    staking yield telemetry, and quantitative valuation percentiles.
    """
    dossier_engine = get_spot_crypto_dossier_engine()
    report = dossier_engine.get_gems_research_report(
        symbol=symbol,
        category=category,
        min_score=min_score
    )
    return JSONResponse(content=report)


@router.get("/macro/contagion")
async def get_macro_contagion_network() -> Dict[str, Any]:
    """
    Returns 3D graph topology of macro drivers, geopolitical hotspots,
    and cross-asset contagion vectors for MacroContagionSphere3D visualizer.
    """
    from core.research.macro_contagion_service import get_macro_contagion_service
    service = get_macro_contagion_service()
    return JSONResponse(content=service.get_contagion_network_graph())


@router.get("/macro/hotspots")
async def get_geopolitical_hotspots(
    hotspot_id: Optional[str] = Query(None, description="Specific hotspot ID (e.g. red_sea, hormuz_strait, taiwan_strait, eastern_europe)")
) -> Dict[str, Any]:
    """
    Returns geopolitical hotspot telemetry, baseline transit disruption %,
    commodity volatility multipliers, and historical reaction dossiers.
    """
    from core.research.macro_contagion_service import get_macro_contagion_service
    service = get_macro_contagion_service()
    if hotspot_id:
        dossier = service.get_hotspot_dossier(hotspot_id)
        if not dossier:
            return JSONResponse(status_code=404, content={"error": f"Hotspot '{hotspot_id}' not found"})
        return JSONResponse(content=dossier)
    return JSONResponse(content=service.get_all_hotspots())


@router.get("/macro/catalysts")
async def get_macro_catalysts_timeline() -> Dict[str, Any]:
    """
    Returns forward-looking catalyst timeline with countdowns,
    precedents, and 15-minute news blackout status.
    """
    from core.research.macro_contagion_service import get_macro_contagion_service
    service = get_macro_contagion_service()
    return JSONResponse(content=service.get_catalyst_timeline())


@router.post("/macro/simulate-shock")
async def simulate_macro_shock(request: Request) -> Dict[str, Any]:
    """
    Simulates a macro shock on a driver (DXY, US10Y, OIL) and returns
    cascading asset impacts, regime classification, and tactical guidance.
    """
    from core.research.macro_contagion_service import get_macro_contagion_service
    service = get_macro_contagion_service()
    try:
        body = await request.json()
        driver = body.get("driver", "DXY")
        shock_pct = float(body.get("shock_delta_pct", 1.0))
        result = service.simulate_macro_shock(driver, shock_pct)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.get("/health")
async def get_research_health() -> Dict[str, Any]:
    """Status probe for institutional market research hub."""
    return JSONResponse(content={
        "ok": True,
        "status": "OPERATIONAL",
        "service": "Institutional Market Research Hub",
        "endpoints": [
            "/api/research/forex/macro",
            "/api/research/crypto/memes",
            "/api/research/crypto/gems",
            "/api/research/macro/contagion",
            "/api/research/macro/hotspots",
            "/api/research/macro/catalysts",
            "/api/research/macro/simulate-shock"
        ]
    })

