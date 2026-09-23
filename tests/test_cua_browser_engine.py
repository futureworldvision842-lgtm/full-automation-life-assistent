"""
tests/test_cua_browser_engine.py — Comprehensive Unit & Integration Test Suite for CUA
======================================================================================
Tests:
  - Session lifecycle: initialization, viewport geometry, priority class, teardown.
  - Hybrid visual DOM grounding: getBoundingClientRect, center computation, SoM badges.
  - Zero pixel drift & elementFromPoint pre-action verification.
  - Omnimodal web action executor: clicks, human-jitter typing (30-50ms), scrolling, form submit.
  - Structured table data extraction: table rows, columns, numerical parsing.
  - Dual-mode operation: headless vs interactive operator assistance, live MJPEG streaming.
  - Boundary & corner cases: uninitialized states, disabled elements, invalid selectors, offscreen elements.
  - FastAPI router endpoints: status, init, inspect, action, extract_table, stream, close, mode.
======================================================================================
"""

from __future__ import annotations

import os
import sys
import time
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cua_browser_engine import CUABrowserEngine
from core.cua_api_router import router, get_cua_engine, set_cua_engine

import httpx
from fastapi import FastAPI


# =============================================================================
# 1. SESSION LIFECYCLE TESTS
# =============================================================================

class TestCUASessionLifecycle:
    """Verifies CUA session launch, configuration, and graceful teardown."""

    @pytest.mark.asyncio
    async def test_initialize_headless_session(self):
        engine = CUABrowserEngine()
        ok = await engine.initialize_session(headless=True)
        try:
            assert ok is True
            assert engine.initialized is True
            assert engine.headless is True
            assert engine.viewport["width"] == 1920
            assert engine.viewport["height"] == 1080
        finally:
            await engine.close()
            assert engine.initialized is False

    @pytest.mark.asyncio
    async def test_initialize_with_custom_viewport(self):
        engine = CUABrowserEngine()
        custom_vp = {"width": 1280, "height": 720, "scale": 1.0}
        ok = await engine.initialize_session(headless=True, viewport=custom_vp)
        try:
            assert ok is True
            assert engine.viewport["width"] == 1280
            assert engine.viewport["height"] == 720
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_double_initialization_safety(self):
        engine = CUABrowserEngine()
        ok1 = await engine.initialize_session(headless=True)
        assert ok1 is True
        ok2 = await engine.initialize_session(headless=True)
        assert ok2 is True
        assert engine.initialized is True
        await engine.close()
        assert engine.initialized is False

    @pytest.mark.asyncio
    async def test_invalid_cdp_url_fails_cleanly(self):
        engine = CUABrowserEngine()
        ok = await engine.initialize_session(cdp_url="http://invalid-cdp-host:9999")
        assert ok is False
        assert engine.initialized is False

    @pytest.mark.asyncio
    async def test_close_uninitialized_session_idempotent(self):
        engine = CUABrowserEngine()
        assert engine.initialized is False
        # Multiple close calls must be safe and idempotent
        await engine.close()
        await engine.close()
        assert engine.initialized is False

    @pytest.mark.asyncio
    async def test_process_priority_enforcement(self):
        engine = CUABrowserEngine()
        ok = await engine.initialize_session(headless=True)
        try:
            assert ok is True
            # Verify priority helper executes cleanly
            engine._apply_process_priority()
        finally:
            await engine.close()


# =============================================================================
# 2. HYBRID VISUAL DOM GROUNDING TESTS
# =============================================================================

class TestCUAVisualDOMGrounding:
    """Verifies DOM inspection, bounding box calculations, and SoM annotations."""

    @pytest.mark.asyncio
    async def test_inspect_viewport_structure(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            state = await engine.inspect_viewport()
            assert state["ok"] is True
            assert "viewport" in state
            assert "elements" in state
            assert "screenshot_b64" in state
            assert len(state["screenshot_b64"]) > 50
            assert len(state["elements"]) >= 3
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_element_coordinates_and_centering(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            state = await engine.inspect_viewport()
            for el in state["elements"]:
                bx, by, bw, bh = el["bbox"]
                cx, cy = el["center"]
                # Must satisfy exact center coordinate formula
                assert cx == bx + bw // 2
                assert cy == by + bh // 2
                assert bx <= cx <= bx + bw
                assert by <= cy <= by + bh
                assert "role" in el
                assert "tag" in el
                assert "id" in el
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_zero_pixel_drift_between_inspections(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            state1 = await engine.inspect_viewport()
            state2 = await engine.inspect_viewport()
            assert len(state1["elements"]) == len(state2["elements"])
            for e1, e2 in zip(state1["elements"], state2["elements"]):
                assert e1["id"] == e2["id"]
                assert e1["bbox"] == e2["bbox"]
                assert e1["center"] == e2["center"]
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_set_of_marks_screenshot_validity(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            state = await engine.inspect_viewport()
            b64_data = state["screenshot_b64"]
            import base64
            raw_bytes = base64.b64decode(b64_data)
            # Verify valid JPEG or PNG header
            assert raw_bytes.startswith(b"\xff\xd8") or raw_bytes.startswith(b"\x89PNG")
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_override_elements_and_offscreen_filtering(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            # Inject custom elements including offscreen and hidden items
            engine.elements = [
                {"id": 10, "tag": "button", "bbox": [50, 50, 100, 30], "center": [100, 65], "visible": True},
                {"id": 11, "tag": "div", "bbox": [0, 9999, 100, 50], "center": [50, 10024], "visible": True},
                {"id": 12, "tag": "span", "bbox": [0, 0, 0, 0], "center": [0, 0], "visible": True},
                {"id": 13, "tag": "input", "bbox": [200, 200, 150, 30], "center": [275, 215], "visible": False}
            ]
            vp = await engine.inspect_viewport()
            elem_ids = [e["id"] for e in vp["elements"]]
            assert 10 in elem_ids
            # Offscreen, zero-size, and invisible must be filtered out
            assert 11 not in elem_ids
            assert 12 not in elem_ids
            assert 13 not in elem_ids
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_empty_page_grounding(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            engine.elements = []
            vp = await engine.inspect_viewport()
            assert vp["elements"] == []
        finally:
            await engine.close()


# =============================================================================
# 3. OMNIMODAL ACTION EXECUTOR TESTS
# =============================================================================

class TestCUAOmnimodalActionExecutor:
    """Verifies clicks, typing with jitter, scrolling, form submits, and table parsing."""

    @pytest.mark.asyncio
    async def test_dispatch_click_actions(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            # Single click
            res1 = await engine.execute_action("click", element_id=1)
            assert res1["ok"] is True
            assert res1["action_type"] == "click"
            assert "target_coordinates" in res1
            assert res1.get("zero_drift_verified") is True

            # Double click
            res2 = await engine.execute_action("double_click", element_id=1)
            assert res2["ok"] is True
            assert res2["action_type"] == "double_click"

            # Right click
            res3 = await engine.execute_action("right_click", element_id=1)
            assert res3["ok"] is True
            assert res3["action_type"] == "right_click"
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_human_delayed_typing_and_jitter(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("type", element_id=2, text="BTCUSD order")
            assert res["ok"] is True
            assert res["action_type"] == "type"
            assert res["text_typed"] == "BTCUSD order"
            # Verify 30-50ms randomized jitter window
            assert 30.0 <= res["jitter_ms"] <= 50.0
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_smooth_scroll_actions(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res_down = await engine.execute_action("scroll", coordinates=(0, 500))
            assert res_down["ok"] is True
            assert res_down["delta_y"] == 500

            res_up = await engine.execute_action("scroll", coordinates=(0, -350))
            assert res_up["ok"] is True
            assert res_up["delta_y"] == -350
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_form_submission_action(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("submit", element_id=1)
            assert res["ok"] is True
            assert res["action_type"] == "submit"

            res2 = await engine.execute_action("submit_form", element_id=1)
            assert res2["ok"] is True
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_page_navigation_action(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("navigate", text="http://127.0.0.1:8770/hud")
            assert res["ok"] is True
            assert res["current_url"] == "http://127.0.0.1:8770/hud"
            assert engine.current_url == "http://127.0.0.1:8770/hud"
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_press_key_action(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("press_key", key="Enter")
            assert res["ok"] is True
            assert res["key_pressed"] == "Enter"
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_extract_table_data(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            data = await engine.extract_table_data("table#quotes")
            assert len(data) >= 1
            assert "symbol" in data[0]
            assert "price" in data[0]
            assert data[0]["symbol"] == "BTCUSD"
            assert data[0]["price"] == 64250.0
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_extract_table_invalid_or_none(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            assert await engine.extract_table_data("invalid") == []
            assert await engine.extract_table_data("none") == []
            assert await engine.extract_table_data("") == []
        finally:
            await engine.close()


# =============================================================================
# 4. DUAL-MODE & STREAMING TESTS
# =============================================================================

class TestCUADualModeAndStreaming:
    """Verifies headless vs interactive toggling and live MJPEG streaming."""

    def test_set_mode_toggling(self):
        engine = CUABrowserEngine()
        assert engine.headless is True

        res_interactive = engine.set_mode("interactive")
        assert res_interactive["ok"] is True
        assert res_interactive["mode"] == "interactive"
        assert engine.headless is False

        res_headless = engine.set_mode("headless")
        assert res_headless["ok"] is True
        assert res_headless["mode"] == "headless"
        assert engine.headless is True

    @pytest.mark.asyncio
    async def test_stream_viewport_frame_bytes(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            frame = await engine.stream_viewport_frame()
            assert isinstance(frame, bytes)
            assert len(frame) > 100
            # Must have valid JPEG SOI header
            assert frame.startswith(b"\xff\xd8")
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_stream_rate_cap_rapid_burst(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            t0 = time.perf_counter()
            for _ in range(25):
                frame = await engine.stream_viewport_frame()
                assert len(frame) > 0
            elapsed = time.perf_counter() - t0
            # 25 frames throttled in cache must complete in < 1.0s
            assert elapsed < 1.0
        finally:
            await engine.close()


# =============================================================================
# 5. BOUNDARY & CORNER CASES
# =============================================================================

class TestCUABoundaryAndCornerCases:
    """Verifies uninitialized actions, disabled elements, invalid modes, and errors."""

    @pytest.mark.asyncio
    async def test_action_before_initialization_fails_closed(self):
        engine = CUABrowserEngine()
        res = await engine.execute_action("click", coordinates=(100, 100))
        assert res["ok"] is False
        assert "not initialized" in res["error"]

    @pytest.mark.asyncio
    async def test_unsupported_action_type(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("unsupported_action_xyz")
            assert res["ok"] is False
            assert "Unsupported action" in res["error"]
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_click_nonexistent_element_id(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            res = await engine.execute_action("click", element_id=99999)
            assert res["ok"] is False
            assert "not found" in res["error"]
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_click_disabled_element_fails(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            engine.elements = [
                {"id": 42, "tag": "button", "bbox": [10, 10, 50, 20], "center": [35, 20], "visible": True, "disabled": True}
            ]
            res = await engine.execute_action("click", element_id=42)
            assert res["ok"] is False
            assert "disabled" in res["error"]
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_oversized_text_typing(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            massive_text = "M" * 4000
            res = await engine.execute_action("type", element_id=2, text=massive_text)
            assert res["ok"] is True
            assert len(res["text_typed"]) == 4000
        finally:
            await engine.close()

    @pytest.mark.asyncio
    async def test_navigation_resilience_to_errors(self):
        engine = CUABrowserEngine()
        await engine.initialize_session(headless=True)
        try:
            # 404 navigation should be resilient and not raise an unhandled exception
            res = await engine.navigate("http://127.0.0.1:8770/nonexistent_test_route")
            assert res["ok"] is True
            assert "nonexistent" in res["current_url"]
        finally:
            await engine.close()


# =============================================================================
# 6. FASTAPI ROUTER ENDPOINT INTEGRATION TESTS
# =============================================================================

class TestCUAAPIRouterEndpoints:
    """Verifies all FastAPI /api/cua/* endpoints using async HTTP client."""

    @pytest.fixture
    def app(self):
        fastapi_app = FastAPI()
        fastapi_app.include_router(router)
        return fastapi_app

    @pytest.mark.asyncio
    async def test_router_status_endpoint(self, app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/cua/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert "initialized" in data
            assert "viewport" in data

    @pytest.mark.asyncio
    async def test_router_session_lifecycle(self, app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Init session
            init_resp = await client.post("/api/cua/session/init", json={"headless": True})
            assert init_resp.status_code == 200
            init_data = init_resp.json()
            assert init_data["ok"] is True
            assert init_data["status"] == "INITIALIZED"

            # Inspect
            inspect_resp = await client.post("/api/cua/inspect")
            assert inspect_resp.status_code == 200
            inspect_data = inspect_resp.json()
            assert inspect_data["ok"] is True
            assert len(inspect_data["elements"]) >= 3

            # Action: click
            act_resp = await client.post("/api/cua/action", json={"action_type": "click", "element_id": 1})
            assert act_resp.status_code == 200
            assert act_resp.json()["ok"] is True

            # Action: type
            type_resp = await client.post("/api/cua/action", json={"action_type": "type", "element_id": 2, "text": "Router Test"})
            assert type_resp.status_code == 200
            assert type_resp.json()["ok"] is True

            # Extract table
            tbl_resp = await client.post("/api/cua/extract_table", json={"selector": "table#quotes"})
            assert tbl_resp.status_code == 200
            tbl_data = tbl_resp.json()
            assert tbl_data["ok"] is True
            assert len(tbl_data["rows"]) >= 1

            # Mode toggle
            mode_resp = await client.post("/api/cua/mode", json={"mode": "interactive"})
            assert mode_resp.status_code == 200
            assert mode_resp.json()["mode"] == "interactive"

            # Close session
            close_resp = await client.post("/api/cua/session/close")
            assert close_resp.status_code == 200
            assert close_resp.json()["status"] == "CLOSED"
