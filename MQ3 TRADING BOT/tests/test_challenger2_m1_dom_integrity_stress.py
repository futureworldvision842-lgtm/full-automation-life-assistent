"""
tests/test_challenger2_m1_dom_integrity_stress.py — Challenger 2 Empirical Adversarial Stress Test Suite for Milestone 1 (M1).
=============================================================================================================================
Empirically stress-tests:
1. Color Token Completeness & CSS Design System (:root variables, palette tokens, contrast, transparency).
2. DOM Element Retention & Component Structural Integrity (every critical UI element, container, ID, and data-binding).
3. Viewport Overflow Protection & Responsive Breakpoint Geometry (box-sizing, 100vw clamping, overflow-x: hidden, min-width: 0).
4. TradingView Lightweight Charts Styling, Series Instantiation, Crosshair Bindings, and AI Ghost Candle Rendering.
5. Interactive REST Client Integrations & Asynchronous Polling Resilience (Promise.allSettled, error handling, contract mapping).
"""

import os
import sys
import re
import json
import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.app import app


@pytest.fixture
def client():
    """Provides isolated Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def index_html_content(client):
    """Fetches raw index.html rendered by Flask server."""
    res = client.get("/")
    assert res.status_code == 200
    return res.get_data(as_text=True)


@pytest.fixture
def soup(index_html_content):
    """Parses index.html with BeautifulSoup for DOM traversal."""
    return BeautifulSoup(index_html_content, "html.parser")


# =====================================================================
# 1. Color Token Completeness & Futuristic Cyber-Blue Aesthetics (F02)
# =====================================================================

class TestColorTokensAndDesignSystem:
    """Verifies complete adherence to the Cyber/Ice-Blue Design System specified in R1 and PROJECT.md."""

    def test_root_contains_all_prescribed_color_tokens(self, index_html_content):
        """Validates all required background, accent, glow, and border hex tokens in :root."""
        required_tokens = {
            "--bg-space": "#0a1128",
            "--bg-panel-solid": "#0e1e38",
            "--bg-card-solid": "#142952",
            "--accent-neon-cyan": "#00d2ff",
            "--accent-ice-blue": "#38bdf8",
            "--accent-bright-ice": "#67e8f9",
            "--cyan-tech": "#00d2ff",
            "--gold-primary": "#38bdf8",
            "--purple-smart": "#a855f7",
            "--green-profit": "#10b981",
            "--red-loss": "#f43f5e",
            "--text-main": "#f8fafc",
            "--text-muted": "#94a3b8",
            "--text-dim": "#64748b"
        }
        for var_name, expected_hex in required_tokens.items():
            pattern = re.compile(rf"{re.escape(var_name)}\s*:\s*{re.escape(expected_hex)}", re.IGNORECASE)
            assert pattern.search(index_html_content), (
                f"Missing or mismatched CSS variable token '{var_name}: {expected_hex}' in index.html :root block."
            )

    def test_glassmorphic_translucent_panel_definitions(self, index_html_content):
        """Verifies glassmorphism backdrop filters, subtle borders, and box shadows on panels."""
        assert "backdrop-filter: blur" in index_html_content
        assert "-webkit-backdrop-filter: blur" in index_html_content
        assert "--border-subtle: rgba(56, 189, 248, 0.18)" in index_html_content
        assert "--bg-panel: rgba(14, 30, 56, 0.82)" in index_html_content
        assert "--bg-card: rgba(20, 41, 82, 0.70)" in index_html_content

    def test_no_unresolved_var_syntax_errors(self, index_html_content):
        """Ensures all var(--...) calls in the template style block reference known defined tokens."""
        defined_vars = set(re.findall(r"--([a-zA-Z0-9_-]+)\s*:", index_html_content))
        used_vars = set(re.findall(r"var\(--([a-zA-Z0-9_-]+)\)", index_html_content))
        
        # Check that all used variables are defined in :root or styles
        undefined = used_vars - defined_vars
        assert not undefined, f"Found undefined CSS variables referenced in index.html: {undefined}"


# =====================================================================
# 2. DOM Element Retention & Structural Integrity (F01, F03, F04)
# =====================================================================

class TestDOMElementRetentionAndStructure:
    """Verifies that all 100% required DOM components, containers, IDs, and widgets exist."""

    def test_top_navigation_bar_elements(self, soup):
        """Verifies brand title, defcon pill, engine status, fleet count, UTC clock, and action buttons."""
        assert soup.find(class_="navbar") is not None
        assert soup.find(id="nav-engine-status") is not None
        assert soup.find(id="nav-defcon-pill") is not None
        assert soup.find(id="nav-fleet-count") is not None
        assert soup.find(id="utc-clock") is not None
        assert soup.find(id="btn-open-signals") is not None
        assert soup.find(id="btn-broadcast-group") is not None
        assert soup.find(id="btn-open-onboard") is not None

    def test_market_ticker_ribbon_chips(self, soup):
        """Verifies top ticker bar with multi-asset chips (Gold, Silver, USDJPY, EURUSD, GBPUSD, BTCUSD)."""
        ticker_bar = soup.find(id="tickerBar")
        assert ticker_bar is not None
        assert soup.find(id="tick-xau") is not None
        assert soup.find(id="tick-xag") is not None
        assert soup.find(id="tick-usdjpy") is not None
        assert soup.find(id="tick-eurusd") is not None
        assert soup.find(id="tick-gbpusd") is not None
        assert soup.find(id="tick-btcusd") is not None

    def test_kpi_summary_metrics(self, soup):
        """Verifies Master Balance, Floating Equity, Daily Loss Shield, and Fleet AUM KPIs."""
        assert soup.find(id="kpi-balance") is not None
        assert soup.find(id="kpi-profit") is not None
        assert soup.find(id="kpi-equity") is not None
        assert soup.find(id="kpi-daily-loss") is not None
        assert soup.find(id="kpi-total-aum") is not None

    def test_market_weather_barometer_components(self, soup):
        """Verifies Weather Center, dial SVG, needle, pressure gauge, updraft/downdraft bars, advisory."""
        assert soup.find(id="market-weather-barometer") is not None
        assert soup.find(id="weather-symbol-label") is not None
        assert soup.find(id="regime-badge") is not None
        assert soup.find(id="weather-regime-icon") is not None
        assert soup.find(id="weather-regime-text") is not None
        assert soup.find(id="weather-multiplier-text") is not None
        assert soup.find(id="gauge-needle") is not None
        assert soup.find(id="barometric-pressure") is not None
        assert soup.find(id="updraft-gauge") is not None
        assert soup.find(id="weather-updraft-val") is not None
        assert soup.find(id="weather-downdraft-val") is not None
        assert soup.find(id="weather-updraft-bar") is not None
        assert soup.find(id="weather-downdraft-bar") is not None
        assert soup.find(id="weather-advisory-text") is not None
        assert soup.find(id="weather-news-status") is not None
        assert soup.find(id="weather-summary-text") is not None

    def test_tradingview_chart_and_forensics_hud(self, soup):
        """Verifies chart container, timeframe buttons, forecast toggle, floating legend, candle inspector, forensic card."""
        assert soup.find(id="tradingViewChart") is not None
        assert soup.find(id="activeChartTitle") is not None
        assert soup.find(id="liveSourceBadge") is not None
        assert soup.find(id="btn-toggle-forecast") is not None
        assert soup.find(id="liveCommentaryTicker") is not None
        assert soup.find(id="commentaryText") is not None
        assert soup.find(id="chartLegend") is not None
        assert soup.find(id="legSym") is not None
        assert soup.find(id="legO") is not None
        assert soup.find(id="legH") is not None
        assert soup.find(id="legL") is not None
        assert soup.find(id="legC") is not None
        assert soup.find(id="legV") is not None
        assert soup.find(id="candleInspectorBar") is not None
        assert soup.find(id="candleShark") is not None
        assert soup.find(id="candleReason") is not None
        assert soup.find(id="candleCvd") is not None
        assert soup.find(id="candleFvg") is not None
        assert soup.find(id="candleWyckoff") is not None
        assert soup.find(id="forensicCard") is not None

    def test_maritime_threat_radar_components(self, soup):
        """Verifies Maritime Radar panel, DEFCON level, 5 chokepoints container, CII bars, OSINT stream."""
        assert soup.find(id="maritime-radar-panel") is not None
        assert soup.find(id="defcon-level") is not None
        assert soup.find(id="wm-risk-score") is not None
        assert soup.find(id="wm-risk-bar") is not None
        assert soup.find(id="wm-primary-hotspot") is not None
        assert soup.find(id="wm-gold-tailwind") is not None
        assert soup.find(id="wm-oil-premium") is not None
        assert soup.find(id="chokepoint-container") is not None
        assert soup.find(id="cii-bars-container") is not None
        assert soup.find(id="wm-osint-stream") is not None

    def test_shark_forensics_cards_and_order_flow(self, soup):
        """Verifies Lee-Ready CVD meter, Wyckoff phase card, Judas box, DOM imbalance meter."""
        assert soup.find(id="shark-forensics-panel") is not None
        assert soup.find(id="shark-cvd-meter") is not None
        assert soup.find(id="cvd-divergence-label") is not None
        assert soup.find(id="cvd-buyer-val") is not None
        assert soup.find(id="cvd-seller-val") is not None
        assert soup.find(id="cvd-net-val") is not None
        assert soup.find(id="cvd-buyer-bar") is not None
        assert soup.find(id="cvd-seller-bar") is not None
        assert soup.find(id="cvd-narrative-text") is not None
        assert soup.find(id="shark-wyckoff-matrix") is not None
        assert soup.find(id="wyckoff-phase-pill") is not None
        assert soup.find(id="wyckoff-structure-label") is not None
        assert soup.find(id="wyckoff-narrative-text") is not None
        assert soup.find(id="shark-judas-box") is not None
        assert soup.find(id="shark-dom-meter") is not None

    def test_multi_account_fleet_hub_table(self, soup):
        """Verifies accounts table and dynamic table body."""
        assert soup.find(id="accounts-table") is not None
        assert soup.find(id="fleet-table-body") is not None
        assert soup.find(id="fleet-aum-subtitle") is not None

    def test_onboard_modal_and_form_controls(self, soup):
        """Verifies onboarding modal, multi-platform tabs (MT5, Prop, Bitget, Binance, Hyperliquid), inputs, risk guardian."""
        assert soup.find(id="onboard-modal") is not None
        assert soup.find(id="onboard-account-form") is not None
        assert soup.find(id="tab-mt5") is not None
        assert soup.find(id="tab-prop") is not None
        assert soup.find(id="tab-bitget") is not None
        assert soup.find(id="tab-binance") is not None
        assert soup.find(id="tab-hyperliquid") is not None
        assert soup.find(id="prop-firm-provider") is not None
        assert soup.find(id="prop-tier-size") is not None
        assert soup.find(id="risk-daily-loss-pct") is not None
        assert soup.find(id="risk-per-trade-pct") is not None
        assert soup.find(id="btn-test-conn") is not None
        assert soup.find(id="btn-save-onboard") is not None


# =====================================================================
# 3. Viewport Overflow Protection & Responsive Breakpoint Geometry (F01)
# =====================================================================

class TestViewportOverflowAndResponsiveGeometry:
    """Verifies fluid viewport containment, zero horizontal scroll, and CSS grid responsiveness."""

    def test_html_and_body_viewport_constraints(self, index_html_content):
        """Ensures html and body enforce 100vw, overflow-x: hidden, and universal border-box."""
        assert re.search(r"html\s*\{[^}]*width:\s*100vw", index_html_content)
        assert re.search(r"html\s*\{[^}]*max-width:\s*100vw", index_html_content)
        assert re.search(r"html\s*\{[^}]*overflow-x:\s*hidden", index_html_content)
        assert re.search(r"body\s*\{[^}]*overflow-x:\s*hidden", index_html_content)
        assert re.search(r"\*\s*\{[^}]*box-sizing:\s*border-box", index_html_content)

    def test_dashboard_grid_min_width_zero_safety(self, index_html_content):
        """Ensures grid columns and panels use minmax(0, ...) or min-width: 0 to prevent grid blowout."""
        assert "minmax(0," in index_html_content
        assert "min-width: 0" in index_html_content

    def test_responsive_media_query_breakpoints_coverage(self, index_html_content):
        """Verifies responsive media query breakpoints for 1920x1080, 1440x900, 1280x720, and mobile."""
        breakpoints = ["1400px", "1100px", "920px", "900px", "800px", "768px", "700px", "600px", "480px", "420px"]
        for bp in breakpoints:
            assert f"@media (max-width: {bp})" in index_html_content, f"Missing required responsive breakpoint @media (max-width: {bp})"


# =====================================================================
# 4. TradingView Canvas Styling & Chart Script Bindings
# =====================================================================

class TestTradingViewCanvasAndScriptBindings:
    """Verifies TradingView Lightweight Charts library inclusion, dark cyber theme, series, and interactions."""

    def test_tradingview_script_library_included(self, soup):
        """Checks for official TradingView Lightweight Charts library tag."""
        scripts = [s.get("src", "") for s in soup.find_all("script") if s.get("src")]
        assert any("lightweight-charts" in s for s in scripts), "TradingView Lightweight Charts script not found in index.html"

    def test_chart_constructor_cyber_blue_theme_options(self, index_html_content):
        """Validates that createChart uses cyber-blue background (#081026), cyan crosshairs, and custom colors."""
        assert "LightweightCharts.createChart" in index_html_content
        assert "background: { color: '#081026' }" in index_html_content or "color: '#081026'" in index_html_content
        assert "addCandlestickSeries" in index_html_content
        assert "addHistogramSeries" in index_html_content

    def test_crosshair_move_subscription_and_hud_updates(self, index_html_content):
        """Validates that subscribeCrosshairMove updates price legend and candle inspector HUD."""
        assert "tvChart.subscribeCrosshairMove" in index_html_content
        assert "document.getElementById('legO')" in index_html_content
        assert "document.getElementById('candleShark')" in index_html_content
        assert "document.getElementById('candleReason')" in index_html_content
        assert "document.getElementById('candleCvd')" in index_html_content

    def test_resize_observer_window_listener_bound(self, index_html_content):
        """Validates dynamic responsive chart resizing on window resize."""
        assert "window.addEventListener('resize'" in index_html_content
        assert "tvChart.applyOptions" in index_html_content

    def test_ai_ghost_candles_toggle_and_rendering(self, index_html_content):
        """Validates toggleFutureForecast function, active status, and distinct ghost candle coloring."""
        assert "function toggleFutureForecast" in index_html_content
        assert "futureForecastCandles" in index_html_content
        assert "forecastActive" in index_html_content
        assert "rgba(167, 139, 250, 0.6)" in index_html_content or "rgba(245, 158, 11, 0.6)" in index_html_content


# =====================================================================
# 5. REST Endpoint Integrations & Resilience
# =====================================================================

class TestRESTEndpointIntegrationsAndResilience:
    """Verifies that all frontend REST endpoints polled by CockpitCoordinator return valid JSON and expected contracts."""

    def test_chart_data_endpoint_contract(self, client):
        res = client.get("/api/chart_data/XAUUSD?tf=M15")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert len(data.get("candles", [])) > 0
        assert len(data.get("future_projected_candles", [])) == 4
        assert "live_data_source" in data

    def test_world_monitor_endpoint_contract(self, client):
        res = client.get("/api/world_monitor?symbol=XAUUSD")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "chokepoints" in data
        assert len(data["chokepoints"]) >= 5
        # Verify core strategic chokepoints present
        cps_str = json.dumps(data["chokepoints"]).upper()
        assert "HORMUZ" in cps_str
        assert "BAB_EL_MANDEB" in cps_str or "RED_SEA" in cps_str
        assert "MALACCA" in cps_str
        assert "SUEZ" in cps_str
        assert "country_instability" in data
        assert "defcon_level" in data

    def test_market_weather_endpoint_contract(self, client):
        res = client.get("/api/market_weather?symbol=XAUUSD&timeframe=M15")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "regime_badge" in data
        assert "updraft_probability" in data
        assert "downdraft_probability" in data
        assert "barometric_pressure_hpa" in data

    def test_shark_forensics_endpoint_contract(self, client):
        res = client.get("/api/shark_forensics?symbol=XAUUSD&timeframe=M15")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "cvd_divergence" in data
        assert "wyckoff_phase" in data
        assert "judas_swing" in data

    def test_trade_cards_endpoint_contract(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "positions" in data
        assert isinstance(data["positions"], list)

    def test_accounts_endpoint_contract(self, client):
        res = client.get("/api/accounts")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "accounts" in data
        assert len(data["accounts"]) >= 1

    def test_onboard_account_submission_and_reflection(self, client):
        payload = {
            "account_id": "TEST_CHALLENGER2_PROP",
            "broker": "Funding Pips",
            "platform": "FUNDING_PIPS",
            "server": "FundingPips-Demo",
            "balance": 50000.0,
            "account_name": "Funding Pips $50k Challenge",
            "custom_risk_pct": 0.75,
            "client_whatsapp": "+923468053268",
            "risk_rules": {
                "max_daily_loss_pct": 2.5,
                "risk_per_trade_pct": 0.75
            }
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"

        # Verify reflected in GET /api/accounts
        res_acc = client.get("/api/accounts")
        accs = res_acc.get_json().get("accounts", [])
        assert any(a.get("account_id") == "TEST_CHALLENGER2_PROP" or a.get("id") == "TEST_CHALLENGER2_PROP" for a in accs)

    def test_execution_actions_contract(self, client):
        actions = ["breakeven", "scale_50", "trail_fvg", "close"]
        for act in actions:
            payload = {"ticket": 9841201, "action": act}
            res = client.post("/api/execution/action", json=payload)
            assert res.status_code == 200
            data = res.get_json()
            assert data.get("status") == "success"

    def test_control_actions_contract(self, client):
        for act in ["pause", "resume", "kill_switch"]:
            payload = {"action": act}
            res = client.post("/api/control", json=payload)
            assert res.status_code == 200
            data = res.get_json()
            assert data.get("status") == "success"

    def test_control_unhandled_actions_return_400(self, client):
        """Verifies that /api/control properly rejects unhandled action names."""
        for act in ["breakeven", "scale", "unknown_action"]:
            payload = {"action": act}
            res = client.post("/api/control", json=payload)
            assert res.status_code == 400

    def test_vip_signals_subscription_contract(self, client):
        payload = {
            "name": "Challenger2 Verifier",
            "phone": "+923468053268",
            "asset_preference": "ALL_ASSETS"
        }
        res = client.post("/api/subscribe_signals", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"

    def test_coordinator_promise_all_settled_resilience(self, index_html_content):
        """Ensures CockpitCoordinator uses Promise.allSettled so a single failure does not crash polling."""
        assert "Promise.allSettled" in index_html_content


if __name__ == "__main__":
    pytest.main(["-v", __file__])
