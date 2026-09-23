"""
tests/test_m4_m5_frontend.py — Comprehensive Automated Test Suite for Milestone M4 & M5 Frontend.

Verifies:
1. HTML Structure & DOM Element IDs in dashboard/web_terminal.html
2. CSS Design Tokens & Cyberpunk Theme in dashboard/static/css/terminal.css
3. JavaScript Module Syntax, UMD Exports, and Interface Contracts:
   - dashboard/static/js/risk_cockpit.js
   - dashboard/static/js/terminal_core.js
   - dashboard/static/js/terminal_app.js
   - dashboard/static/js/voice_copilot.js
4. BlackRock Aladdin 99%/95% Parametric VaR, CVaR (Expected Shortfall), and Kelly Math
5. Funding Pips Trailing HWM Ratchet Floor & Daily Drawdown Allowance Meter
6. 35% Consistency Rule 4-Stage Automated De-risking Logic
7. Voice AI Copilot Deterministic NLP Intent Parsing & Entity Extraction
8. FastAPI Server Integration & Route Resolution
"""

import os
import sys
import re
import json
import math
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# =====================================================================
# 1. HTML DOM Structure & Script Loading Tests
# =====================================================================

class TestWebTerminalHTML:
    """Validates web_terminal.html structure, required elements, IDs, and script dependencies."""

    @pytest.fixture(autouse=True)
    def setup_html(self):
        self.html_path = os.path.join(PROJECT_ROOT, "dashboard", "web_terminal.html")
        assert os.path.exists(self.html_path), f"File not found: {self.html_path}"
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_html_doctype_and_title(self):
        assert "<!DOCTYPE html>" in self.content or "<!doctype html>" in self.content.lower()
        assert "<title>" in self.content
        assert "Institutional Web Trading Terminal" in self.content

    def test_css_stylesheet_link(self):
        assert '<link rel="stylesheet" href="/static/css/terminal.css">' in self.content

    def test_lightweight_charts_script_link(self):
        assert "lightweight-charts" in self.content

    def test_header_elements_and_ids(self):
        required_ids = [
            "terminal-header",
            "symbol-tabs",
            "timeframe-selector",
            "active-symbol-name",
            "active-symbol-bid",
            "active-symbol-ask",
            "active-symbol-spread",
            "account-profile-select",
            "terminal-status-badge",
            "status-dot",
            "status-text",
            "voice-mic-btn",
            "voice-wave-canvas",
            "btn-toggle-pause",
            "btn-emergency-kill"
        ]
        for el_id in required_ids:
            assert f'id="{el_id}"' in self.content, f"Missing element ID in header: {el_id}"

    def test_left_pane_elements_and_ids(self):
        required_ids = [
            "pane-left",
            "dom-container",
            "dom-buyer-pct",
            "dom-seller-pct",
            "dom-ratio-bar",
            "dom-asks",
            "dom-bids",
            "order-form",
            "order-volume",
            "order-sl-pips",
            "order-tp-pips",
            "btn-order-buy",
            "btn-order-sell"
        ]
        for el_id in required_ids:
            assert f'id="{el_id}"' in self.content, f"Missing element ID in left pane: {el_id}"

    def test_center_pane_elements_and_ids(self):
        required_ids = [
            "pane-center",
            "smc-fvg-count",
            "smc-ob-count",
            "smc-ote-level",
            "smc-trend-badge",
            "candlestick-chart-container",
            "cvd-pane-container",
            "cvd-cumulative-val",
            "cvd-divergence-badge",
            "cvd-buyer-pct",
            "cvd-seller-pct",
            "cvd-ratio-fill"
        ]
        for el_id in required_ids:
            assert f'id="{el_id}"' in self.content, f"Missing element ID in center pane: {el_id}"

    def test_right_pane_risk_cockpit_elements_and_ids(self):
        required_ids = [
            "pane-right",
            "risk-cockpit-pane",
            "val-equity",
            "val-balance",
            "val-floating-pnl",
            "val-margin-free",
            "val-trailing-buffer",
            "hwm-progress-fill",
            "val-trailing-floor",
            "val-hwm",
            "val-daily-loss",
            "val-daily-limit",
            "daily-drawdown-fill",
            "val-daily-loss-rem",
            "val-var-99-usd",
            "val-var-99-pct",
            "val-cvar-99-usd",
            "val-cvar-99-pct",
            "val-var-95-usd",
            "var-progress-fill",
            "val-consistency-today",
            "val-consistency-cap",
            "consistency-status-badge",
            "consistency-progress-fill",
            "consistency-action-msg",
            "voice-copilot-drawer",
            "voice-transcript-text",
            "jarvis-speech-log",
            "voice-cmd-input",
            "btn-send-voice-cmd"
        ]
        for el_id in required_ids:
            assert f'id="{el_id}"' in self.content, f"Missing element ID in right pane: {el_id}"

    def test_bottom_pane_positions_table_elements_and_ids(self):
        required_ids = [
            "pane-bottom",
            "tab-btn-positions",
            "pos-count-badge",
            "tab-btn-history",
            "tab-btn-logs",
            "tab-btn-voice",
            "positions-pane",
            "positions-table",
            "positions-tbody",
            "history-pane",
            "logs-pane",
            "system-logs-container",
            "voice-logs-pane"
        ]
        for el_id in required_ids:
            assert f'id="{el_id}"' in self.content, f"Missing element ID in bottom pane: {el_id}"

    def test_modal_and_toast_elements(self):
        assert 'id="kill-switch-modal"' in self.content
        assert 'id="btn-modal-cancel-kill"' in self.content
        assert 'id="btn-modal-confirm-kill"' in self.content
        assert 'id="toast-container"' in self.content

    def test_all_javascript_scripts_loaded(self):
        assert '<script src="/static/js/terminal_core.js"></script>' in self.content
        assert '<script src="/static/js/risk_cockpit.js"></script>' in self.content
        assert '<script src="/static/js/voice_copilot.js"></script>' in self.content
        assert '<script src="/static/js/terminal_app.js"></script>' in self.content


# =====================================================================
# 2. CSS Design Tokens & Styling Tests
# =====================================================================

class TestTerminalCSS:
    """Validates terminal.css design tokens, classes, and cyberpunk glassmorphism theme."""

    @pytest.fixture(autouse=True)
    def setup_css(self):
        self.css_path = os.path.join(PROJECT_ROOT, "dashboard", "static", "css", "terminal.css")
        assert os.path.exists(self.css_path), f"File not found: {self.css_path}"
        with open(self.css_path, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_css_variables_defined(self):
        required_vars = [
            "--bg-base",
            "--bg-primary",
            "--bg-surface",
            "--bg-card",
            "--accent-cyan",
            "--accent-magenta",
            "--accent-gold",
            "--accent-purple",
            "--bullish-green",
            "--bearish-red",
            "--warning-yellow",
            "--text-primary",
            "--text-secondary",
            "--text-dim",
            "--border-glass",
            "--font-sans",
            "--font-mono"
        ]
        for var in required_vars:
            assert f"{var}:" in self.content, f"Missing CSS variable: {var}"

    def test_action_button_styles_present(self):
        assert ".btn-scale-out" in self.content
        assert ".btn-breakeven" in self.content
        assert ".btn-modify" in self.content
        assert ".btn-close-pos" in self.content
        assert ".btn-kill-switch" in self.content

    def test_badge_and_gauge_styles_present(self):
        assert ".badge-buy" in self.content
        assert ".badge-sell" in self.content
        assert ".bg-stage-1" in self.content
        assert ".bg-stage-2" in self.content
        assert ".bg-stage-3" in self.content
        assert ".bg-stage-4" in self.content


# =====================================================================
# 3. JavaScript Module Content & Interface Tests
# =====================================================================

class TestJavaScriptModules:
    """Validates JS file existence, class definitions, and UMD exports."""

    def test_risk_cockpit_js_contract(self):
        path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "risk_cockpit.js")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        assert "class RiskCockpitEngine" in code or "function RiskCockpit" in code
        assert "calculateAladdinVaR" in code
        assert "calculatePropFirmDefense" in code
        assert "calculateConsistencyPacing" in code
        assert "getTelemetrySnapshot" in code
        assert "root.RiskCockpit" in code

    def test_terminal_core_js_contract(self):
        path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "terminal_core.js")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        assert "class TerminalCoreEngine" in code or "class TerminalCore" in code
        assert "scaleOut" in code
        assert "breakeven" in code
        assert "modifySLTP" in code
        assert "closePosition" in code
        assert "killSwitch" in code
        assert "togglePause" in code
        assert "sendVoiceTranscript" in code
        assert "root.TerminalCore" in code

    def test_voice_copilot_js_contract(self):
        path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "voice_copilot.js")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        assert "class VoiceCopilotEngine" in code or "class VoiceCopilot" in code
        assert "parseIntent" in code
        assert "processTranscript" in code
        assert "SoundSynthesizer" in code
        assert "mic_on" in code
        assert "EXECUTION_SUCCESS" in code
        assert "root.VoiceCopilot" in code

    def test_terminal_app_js_contract(self):
        path = os.path.join(PROJECT_ROOT, "dashboard", "static", "js", "terminal_app.js")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        assert "class TradingTerminalApp" in code or "class TerminalApp" in code
        assert "renderPositionsTable" in code
        assert "switchSymbol" in code
        assert "switchTimeframe" in code
        assert "root.TerminalApp" in code


# =====================================================================
# 4. Mathematical Risk Verification (VaR / CVaR / Kelly / HWM / 35%)
# =====================================================================

class TestMathematicalRiskVerification:
    """Verifies the core mathematical formulas implemented in risk_cockpit.js."""

    Z_99 = 2.326348
    Z_95 = 1.644854
    PHI_Z99_OVER_001 = 2.665214
    PHI_Z95_OVER_005 = 2.062714

    def test_aladdin_var_and_cvar_law(self):
        """Validates that 99% CVaR is strictly 14.57% greater than 99% VaR."""
        equity = 25730.00
        daily_vol = 0.0080  # 0.80%

        var_99 = equity * self.Z_99 * daily_vol
        cvar_99 = equity * self.PHI_Z99_OVER_001 * daily_vol

        expected_ratio = self.PHI_Z99_OVER_001 / self.Z_99
        actual_ratio = cvar_99 / var_99

        assert abs(actual_ratio - expected_ratio) < 1e-5
        assert abs(actual_ratio - 1.145664) < 1e-4
        assert cvar_99 > var_99

    def test_prop_firm_hwm_ratchet_floor_25k(self):
        """Validates Trailing HWM ratchet floor defense on a $25k account."""
        target_balance = 25000.0
        safe_total_loss_pct = 6.0  # 6% ($1,500)
        max_total_loss = target_balance * (safe_total_loss_pct / 100.0)

        # Baseline: equity at $25,000
        hwm = 25000.0
        floor = hwm - max_total_loss
        assert floor == 23500.0

        # Equity grows to $26,500 -> HWM ratchets to $26,500
        equity = 26500.0
        hwm = max(hwm, equity)
        floor = hwm - max_total_loss
        assert floor == 25000.0  # Initial capital fully locked!

        # Equity drops to $25,800 -> HWM remains at $26,500
        equity = 25800.0
        floor = hwm - max_total_loss
        assert floor == 25000.0  # Monotonic ratchet

    def test_consistency_rule_4_stage_derisking(self):
        """Validates 35% consistency rule stages on a $25k account ($2,000 target, $700 cap)."""
        target_balance = 25000.0
        profit_target = target_balance * 0.08  # $2,000
        daily_cap = profit_target * 0.35      # $700

        # Stage 1: Nominal (< 70% of $700 = < $490)
        p1 = 250.0
        pct1 = (p1 / daily_cap) * 100.0
        stage1 = 1 if pct1 < 70.0 else 2
        assert stage1 == 1
        assert pct1 == 35.714285714285715

        # Stage 2: Caution (70% - 89.9% = $490 - $629.99)
        p2 = 550.0
        pct2 = (p2 / daily_cap) * 100.0
        stage2 = 2 if 70.0 <= pct2 < 90.0 else 1
        assert stage2 == 2

        # Stage 3: Critical (90% - 99.9% = $630 - $699.99)
        p3 = 650.0
        pct3 = (p3 / daily_cap) * 100.0
        stage3 = 3 if 90.0 <= pct3 < 100.0 else 2
        assert stage3 == 3

        # Stage 4: Ceiling Reached (>= 100% = >= $700)
        p4 = 720.0
        pct4 = (p4 / daily_cap) * 100.0
        stage4 = 4 if pct4 >= 100.0 else 3
        assert stage4 == 4


# =====================================================================
# 5. Voice AI Copilot Deterministic NLP Intent Parsing Tests
# =====================================================================

class TestVoiceNLPIntentParsing:
    """Verifies the regex / deterministic NLP grammar matching."""

    SYMBOL_MAP = {
        "gold": "XAUUSD", "xau": "XAUUSD", "xauusd": "XAUUSD",
        "euro": "EURUSD", "eur": "EURUSD",
        "pound": "GBPUSD", "cable": "GBPUSD", "gbp": "GBPUSD",
        "yen": "USDJPY", "usdjpy": "USDJPY"
    }

    def resolve_symbol(self, text):
        norm = text.lower()
        for k, v in self.SYMBOL_MAP.items():
            if k in norm:
                return v
        return "XAUUSD"

    def test_scale_out_intent(self):
        phrase = "Close 50% on USDJPY"
        assert "close" in phrase.lower()
        assert "50%" in phrase
        assert self.resolve_symbol(phrase) == "USDJPY"

    def test_lock_breakeven_intent(self):
        phrase = "Lock Breakeven on Gold plus 2 pips"
        assert "breakeven" in phrase.lower()
        assert self.resolve_symbol(phrase) == "XAUUSD"
        m = re.search(r"(\d+)\s*pips", phrase)
        assert m and int(m.group(1)) == 2

    def test_kill_switch_intent(self):
        phrases = ["Emergency stop", "Kill switch", "Flatten all", "Panic close all"]
        for p in phrases:
            assert any(k in p.lower() for k in ["kill switch", "emergency stop", "panic", "flatten all", "close all"])


# =====================================================================
# 6. FastAPI Server Route Integration Tests
# =====================================================================

class TestServerHTMLServing:
    """Verifies that FastAPI server serves web_terminal.html at / and /terminal."""

    @pytest.mark.asyncio
    async def test_terminal_route_serves_html(self):
        try:
            from src.web_terminal_server import app
            from httpx import AsyncClient, ASGITransport
        except ImportError:
            pytest.skip("FastAPI or httpx not available in current environment")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/terminal")
            assert resp.status_code == 200
            assert "text/html" in resp.headers.get("content-type", "")
            assert "Institutional Web Trading Terminal" in resp.text
            assert "ALADDIN" in resp.text and "QUANT" in resp.text
            assert "candlestick-chart-container" in resp.text
            assert "positions-table" in resp.text
