"""
tests/test_adversarial_m2_gate1_stress.py — Pytest Stress Suite for CUA Engine & Router
Empirical verification of jitter distribution, scroll boundaries, form edge cases,
live MJPEG disconnects, and malformed tables.
"""

from __future__ import annotations

import os
import sys
import time
import math
import pytest
import asyncio
import logging
import threading
import statistics
from pathlib import Path
from typing import Dict, Any, List

import psutil
import uvicorn
import httpx
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cua_browser_engine import CUABrowserEngine
from core.cua_api_router import router, get_cua_engine, set_cua_engine

COMPREHENSIVE_EDGE_CASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CUA Edge Cases & Malformed DOM Testbed</title>
  <style>
    body {
      margin: 0; padding: 20px; font-family: sans-serif;
      background: #0f172a; color: #f8fafc;
    }
    .spacer { height: 4000px; background: linear-gradient(to bottom, #1e293b, #0f172a); }
    .box { margin-bottom: 20px; padding: 15px; border: 1px solid #334155; }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>
  <h1>CUA Stress Test Page</h1>
  <div id="scroll-marker-top">TOP OF PAGE</div>

  <div class="box">
    <h3>Form 1: Disabled Submit Button</h3>
    <form id="form-disabled-btn">
      <input id="inp-disabled-target" type="text" value="some text" />
      <button id="btn-disabled" type="submit" disabled>Disabled Submit</button>
    </form>
  </div>

  <div class="box">
    <h3>Form 2: Form without submit button</h3>
    <form id="form-no-btn" onsubmit="window.__form_no_btn_submitted = true; return false;">
      <input id="inp-no-btn" type="text" placeholder="Type and hit Enter" />
    </form>
  </div>

  <div class="box">
    <h3>Form 3: Required Fields Missing</h3>
    <form id="form-required" onsubmit="window.__form_required_submitted = true; return false;">
      <input id="inp-required" type="text" required placeholder="Required field" />
      <button id="btn-submit-req" type="submit">Submit With Required</button>
    </form>
  </div>

  <div class="box">
    <h3>Form 4: JS Exception on Submit</h3>
    <form id="form-exploding" onsubmit="window.__exploding_called = true; return false;">
      <input id="inp-exploding" type="text" value="crash test" />
      <button id="btn-exploding" type="submit">Explode Submit</button>
    </form>
  </div>

  <div class="box">
    <h3>Table 1: Missing THEAD (Headers in First TR)</h3>
    <table id="tbl-no-thead" border="1">
      <tr><th>Symbol</th><th>OrderType</th><th>Units</th><th>Status</th></tr>
      <tr><td>BTCUSD</td><td>LIMIT</td><td>0.5</td><td>FILLED</td></tr>
      <tr><td>ETHUSD</td><td>MARKET</td><td>2.0</td><td>PENDING</td></tr>
      <tr><td>SOLUSD</td><td>STOP</td><td>10.0</td><td>REJECTED</td></tr>
    </table>
  </div>

  <div class="box">
    <h3>Table 2: Ragged Rows & Colspans</h3>
    <table id="tbl-ragged" border="1">
      <thead>
        <tr><th>Ticker</th><th>Price</th><th>Volume</th><th>Trend</th></tr>
      </thead>
      <tbody>
        <tr><td>XAUUSD</td><td colspan="2">2650.50 (Consolidated)</td><td>BULLISH</td></tr>
        <tr><td>US30</td><td>42100.0</td><td>150000</td><td>BEARISH</td><td>EXTRA_CELL</td></tr>
        <tr><td>EURUSD</td></tr>
      </tbody>
    </table>
  </div>

  <div class="box">
    <h3>Table 3: Nested Table</h3>
    <table id="tbl-nested-outer" border="1">
      <thead>
        <tr><th>Strategy</th><th>SubPortfolio</th><th>TotalVaR</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>Institutional Arb</td>
          <td>
            <table id="tbl-nested-inner" border="1">
              <thead><tr><th>Asset</th><th>Allocation</th></tr></thead>
              <tbody>
                <tr><td>Gold</td><td>60%</td></tr>
                <tr><td>Oil</td><td>40%</td></tr>
              </tbody>
            </table>
          </td>
          <td>12500.00</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="box">
    <h3>Table 4: No TH tags at all (Pure TD grid)</h3>
    <table id="tbl-pure-td" border="1">
      <tr><td>Metric</td><td>Score</td></tr>
      <tr><td>Sharpe</td><td>2.84</td></tr>
      <tr><td>Drawdown</td><td>0.00</td></tr>
    </table>
  </div>

  <div class="box">
    <h3>Table 5: Completely Empty Table</h3>
    <table id="tbl-empty"></table>
  </div>

  <div class="spacer"></div>
  <div id="scroll-marker-bottom">BOTTOM OF PAGE (Y=4000+)</div>
</body>
</html>
"""


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_keystroke_jitter_distribution():
    engine = CUABrowserEngine()
    ok = await engine.initialize_session(headless=True)
    assert ok is True

    try:
        jitters = []
        for _ in range(100):
            res = await engine.execute_action("type", coordinates=[100, 100], text="k")
            assert res["ok"] is True
            j = res["jitter_ms"]
            assert 30.0 <= j <= 50.0, f"Jitter {j} out of [30.0, 50.0] bounds"
            jitters.append(j)

        assert min(jitters) < 35.0
        assert max(jitters) > 45.0
        assert 37.0 <= statistics.mean(jitters) <= 43.0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_wheel_scrolling_boundaries():
    engine = CUABrowserEngine()
    ok = await engine.initialize_session(headless=True)
    assert ok is True

    try:
        await engine._page.set_content(COMPREHENSIVE_EDGE_CASE_HTML)
        page = engine._page

        # Top boundary negative delta
        res_top = await engine.execute_action("scroll", coordinates=[0, -5000])
        assert res_top["ok"] is True
        top_y = await page.evaluate("() => window.scrollY")
        assert top_y == 0

        # Down scroll
        res_mid = await engine.execute_action("scroll", coordinates=[0, 1000])
        assert res_mid["ok"] is True
        await asyncio.sleep(0.1)
        mid_y = await page.evaluate("() => window.scrollY")
        assert mid_y > 0

        # Bottom boundary overshoot
        res_bottom = await engine.execute_action("scroll", coordinates=[0, 100000])
        assert res_bottom["ok"] is True
        await asyncio.sleep(0.1)
        bottom_y = await page.evaluate("() => window.scrollY")
        max_scroll = await page.evaluate("() => document.body.scrollHeight - window.innerHeight")
        assert abs(bottom_y - max_scroll) <= 50

        # Back to top overshoot
        res_back = await engine.execute_action("scroll", coordinates=[0, -200000])
        assert res_back["ok"] is True
        await asyncio.sleep(0.1)
        back_y = await page.evaluate("() => window.scrollY")
        assert back_y == 0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_form_submission_edge_cases():
    engine = CUABrowserEngine()
    ok = await engine.initialize_session(headless=True)
    assert ok is True

    try:
        await engine._page.set_content(COMPREHENSIVE_EDGE_CASE_HTML)
        page = engine._page

        # 1. Disabled submit button
        engine.elements = [
            {"id": 888, "tag": "button", "bbox": [10, 10, 50, 20], "center": [35, 20], "disabled": True, "visible": True}
        ]
        res_dis = await engine.execute_action("submit", element_id=888)
        assert res_dis["ok"] is False
        assert "disabled" in res_dis["error"].lower()
        engine.elements = None

        # 2. Form without submit button (Enter key submits)
        await page.focus("#inp-no-btn")
        res_enter = await engine.execute_action("submit", coordinates=[0, 0])
        assert res_enter["ok"] is True
        await asyncio.sleep(0.1)
        sub_no_btn = await page.evaluate("() => window.__form_no_btn_submitted === true")
        assert sub_no_btn is True

        # 3. Form with missing required fields
        coords_req = await page.evaluate("""() => {
            const r = document.querySelector('#btn-submit-req').getBoundingClientRect();
            return [Math.floor(r.x + r.width/2), Math.floor(r.y + r.height/2)];
        }""")
        res_req = await engine.execute_action("submit", coordinates=coords_req)
        assert res_req["ok"] is True
        await asyncio.sleep(0.1)
        sub_req = await page.evaluate("() => window.__form_required_submitted === true")
        assert sub_req is False  # Native validation prevented form dispatch

        # 4. Form submit handler
        coords_exp = await page.evaluate("""() => {
            const r = document.querySelector('#btn-exploding').getBoundingClientRect();
            return [Math.floor(r.x + r.width/2), Math.floor(r.y + r.height/2)];
        }""")
        res_exp = await engine.execute_action("submit", coordinates=coords_exp)
        assert res_exp["ok"] is True
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_malformed_html_table_extraction():
    engine = CUABrowserEngine()
    ok = await engine.initialize_session(headless=True)
    assert ok is True

    try:
        await engine._page.set_content(COMPREHENSIVE_EDGE_CASE_HTML)

        # Missing THEAD: extracts data rows successfully without error
        d1 = await engine.extract_table_data("#tbl-no-thead")
        assert len(d1) >= 3
        assert "symbol" in d1[0]
        assert d1[0]["symbol"] == "BTCUSD"

        # Ragged rows and colspans
        d2 = await engine.extract_table_data("#tbl-ragged")
        assert len(d2) >= 3
        assert d2[0]["ticker"] == "XAUUSD"

        # Nested tables
        d3_out = await engine.extract_table_data("#tbl-nested-outer")
        d3_in = await engine.extract_table_data("#tbl-nested-inner")
        assert len(d3_out) >= 1
        assert len(d3_in) >= 2

        # Pure TD grid
        d4 = await engine.extract_table_data("#tbl-pure-td")
        assert len(d4) >= 2

        # Empty table
        d5 = await engine.extract_table_data("#tbl-empty")
        assert isinstance(d5, list)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_mjpeg_streaming_concurrency_and_disconnects():
    engine = CUABrowserEngine()
    ok = await engine.initialize_session(headless=True)
    assert ok is True

    try:
        # Verify frame bytes generation
        frame1 = await engine.stream_viewport_frame()
        assert isinstance(frame1, bytes)
        assert len(frame1) > 100
        assert frame1.startswith(b"\xff\xd8")  # JPEG header

        # Verify rate-limiting caching (<100ms returns cached frame immediately)
        frame2 = await engine.stream_viewport_frame()
        assert frame1 == frame2

        # Verify simulated multiple clients reading stream generator directly
        class MockRequest:
            def __init__(self):
                self.disconnected = False
            async def is_disconnected(self):
                return self.disconnected

        async def simulated_client(cid: int, disconnect_early: bool = False):
            req = MockRequest()
            frames_read = 0
            # Emulate frame_generator logic from cua_api_router.py
            for _ in range(5):
                if await req.is_disconnected():
                    break
                f = await engine.stream_viewport_frame()
                assert len(f) > 0
                frames_read += 1
                if disconnect_early and frames_read >= 1:
                    req.disconnected = True
                await asyncio.sleep(0.01)
            return frames_read

        # 5 concurrent clients
        results = await asyncio.gather(*[simulated_client(i, False) for i in range(5)])
        assert all(count == 5 for count in results)

        # 10 rapid disconnect clients
        disconnect_results = await asyncio.gather(*[simulated_client(i, True) for i in range(10)])
        assert all(count == 1 for count in disconnect_results)

        # Verify engine remains fully responsive
        vp = await engine.inspect_viewport()
        assert vp.get("ok") is True
    finally:
        await engine.close()
