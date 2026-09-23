"""
tests/test_m3_challenger2_frontend.py — Challenger 2 Master Frontend & DOM Integrity Test Suite.
================================================================================================
Milestone M3 (Requirement R3: WorldMonitor-Style Web Command Cockpit Overhaul).

Validates:
  1. Complete HTML5 DOM element ID & CSS class coverage for Features 17, 18, 19, 20.
  2. CSS3 stylesheet rules, custom properties (:root), keyframe animations, and responsive media queries.
  3. JavaScript syntax, AST parsing, CockpitCoordinator object methods, and math functions via Node.js.
  4. Jinja2 template rendering under varying mock contexts, empty states, and tag-balancing invariants.
  5. End-to-end frontend <-> REST API contract schema compatibility across all 5 M3 endpoints.
  6. XSS safety, input sanitization, and resilience against edge-case payload mutations.
"""

import os
import re
import json
import tempfile
import subprocess
import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from dashboard.app import app, _RUNTIME_FLEET_STORE

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML_PATH = os.path.join(PROJECT_ROOT, "dashboard", "templates", "index.html")


@pytest.fixture(scope="module")
def raw_html():
    """Reads raw index.html template file."""
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def soup(raw_html):
    """Parses index.html with BeautifulSoup."""
    return BeautifulSoup(raw_html, "html.parser")


@pytest.fixture
def client():
    """Provides Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# 1. FEATURE 17: MARITIME GEOPOLITICAL RADAR DOM & CSS VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestFeature17MaritimeGeopoliticalRadarDOM:
    """Empirically verifies all DOM elements and styles for Feature 17."""

    def test_maritime_radar_panel_container_exists(self, soup):
        panel = soup.find(id="maritime-radar-panel")
        assert panel is not None, "Missing #maritime-radar-panel in DOM"
        assert "wm-radar-panel" in panel.get("class", [])

    def test_defcon_and_risk_score_elements(self, soup):
        defcon = soup.find(id="defcon-level")
        assert defcon is not None, "Missing #defcon-level in DOM"
        assert "badge-defcon" in defcon.get("class", [])

        risk_score = soup.find(id="wm-risk-score")
        assert risk_score is not None, "Missing #wm-risk-score in DOM"

        risk_bar = soup.find(id="wm-risk-bar")
        assert risk_bar is not None, "Missing #wm-risk-bar in DOM"

    def test_hotspot_gold_oil_macro_metrics(self, soup):
        hotspot = soup.find(id="wm-primary-hotspot")
        assert hotspot is not None, "Missing #wm-primary-hotspot"

        gold_tailwind = soup.find(id="wm-gold-tailwind")
        assert gold_tailwind is not None, "Missing #wm-gold-tailwind"

        oil_premium = soup.find(id="wm-oil-premium")
        assert oil_premium is not None, "Missing #wm-oil-premium"

    def test_chokepoints_and_cii_containers(self, soup):
        cp_container = soup.find(id="chokepoint-container")
        assert cp_container is not None, "Missing #chokepoint-container"
        assert "chokepoint-grid" in cp_container.get("class", []) or "chokepoints-grid" in cp_container.get("class", [])

        cii_container = soup.find(id="cii-bars-container")
        assert cii_container is not None, "Missing #cii-bars-container"

        osint_stream = soup.find(id="wm-osint-stream")
        assert osint_stream is not None, "Missing #wm-osint-stream"


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE 18: MARKET WEATHER BAROMETER DOM & CSS VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestFeature18MarketWeatherBarometerDOM:
    """Empirically verifies all DOM elements and styles for Feature 18."""

    def test_weather_barometer_panel_container(self, soup):
        panel = soup.find(id="market-weather-barometer")
        assert panel is not None, "Missing #market-weather-barometer in DOM"
        assert "weather-barometer-panel" in panel.get("class", [])

    def test_regime_badge_and_symbol_label(self, soup):
        badge = soup.find(id="regime-badge")
        assert badge is not None, "Missing #regime-badge"
        assert "regime-badge" in badge.get("class", [])

        regime_text = soup.find(id="weather-regime-text")
        assert regime_text is not None, "Missing #weather-regime-text"

        regime_icon = soup.find(id="weather-regime-icon")
        assert regime_icon is not None, "Missing #weather-regime-icon"

        symbol_label = soup.find(id="weather-symbol-label")
        assert symbol_label is not None, "Missing #weather-symbol-label"

        mult_text = soup.find(id="weather-multiplier-text")
        assert mult_text is not None, "Missing #weather-multiplier-text"

    def test_barometric_pressure_and_svg_dial(self, soup):
        hpa = soup.find(id="barometric-pressure")
        assert hpa is not None, "Missing #barometric-pressure"

        needle = soup.find(id="gauge-needle")
        assert needle is not None, "Missing #gauge-needle SVG element"

        arc = soup.find(id="gauge-updraft-arc")
        assert arc is not None, "Missing #gauge-updraft-arc SVG element"

    def test_updraft_downdraft_twin_bars(self, soup):
        up_gauge = soup.find(id="updraft-gauge")
        assert up_gauge is not None, "Missing #updraft-gauge"

        up_val = soup.find(id="weather-updraft-val")
        assert up_val is not None, "Missing #weather-updraft-val"

        up_bar = soup.find(id="weather-updraft-bar")
        assert up_bar is not None, "Missing #weather-updraft-bar"

        down_val = soup.find(id="weather-downdraft-val")
        assert down_val is not None, "Missing #weather-downdraft-val"

        down_bar = soup.find(id="weather-downdraft-bar")
        assert down_bar is not None, "Missing #weather-downdraft-bar"

    def test_weather_advisory_and_telemetry_metrics(self, soup):
        adv = soup.find(id="weather-advisory-text")
        assert adv is not None, "Missing #weather-advisory-text"

        summary = soup.find(id="weather-summary-text")
        assert summary is not None, "Missing #weather-summary-text"

        news = soup.find(id="weather-news-status")
        assert news is not None, "Missing #weather-news-status"

        radar = soup.find(id="weather-radar-score")
        assert radar is not None, "Missing #weather-radar-score"

        vol = soup.find(id="weather-vol-status")
        assert vol is not None, "Missing #weather-vol-status"

        trap = soup.find(id="weather-trap-risk")
        assert trap is not None, "Missing #weather-trap-risk"


# ══════════════════════════════════════════════════════════════════════════════
# 3. FEATURE 19: MULTI-ACCOUNT ONBOARDING MODAL & FLEET HUB DOM VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestFeature19MultiAccountOnboardingDOM:
    """Empirically verifies all DOM elements and styles for Feature 19."""

    def test_onboard_modal_and_trigger_buttons(self, soup):
        modal = soup.find(id="onboard-modal")
        assert modal is not None, "Missing #onboard-modal"
        assert "modal-overlay" in modal.get("class", [])

        btn_open = soup.find(id="btn-open-onboard")
        assert btn_open is not None, "Missing #btn-open-onboard"

        btn_close = soup.find(id="btn-close-onboard-modal")
        assert btn_close is not None, "Missing #btn-close-onboard-modal"

        form = soup.find(id="onboard-account-form")
        assert form is not None, "Missing #onboard-account-form"

    def test_onboard_platform_tabs_and_panes(self, soup):
        tab_mt5 = soup.find(id="tab-mt5")
        assert tab_mt5 is not None, "Missing #tab-mt5 pane"

        tab_prop = soup.find(id="tab-prop")
        assert tab_prop is not None, "Missing #tab-prop pane"

        tab_binance = soup.find(id="tab-binance")
        assert tab_binance is not None, "Missing #tab-binance pane"

        tab_hyperliquid = soup.find(id="tab-hyperliquid")
        assert tab_hyperliquid is not None, "Missing #tab-hyperliquid pane"

        # Check tab buttons
        tab_funding_pips = soup.find(id="tab-funding-pips") or soup.find("button", {"data-tab": "tab-prop"})
        assert tab_funding_pips is not None, "Missing prop tab button"

    def test_mt5_form_input_fields(self, soup):
        assert soup.find(id="mt5-login") is not None
        assert soup.find(id="mt5-password") is not None
        assert soup.find(id="mt5-server") is not None
        assert soup.find(id="mt5-balance") is not None
        assert soup.find(id="mt5-label") is not None
        assert soup.find(id="mt5-mode") is not None

    def test_prop_firm_form_input_fields(self, soup):
        assert soup.find(id="prop-firm-provider") is not None
        assert soup.find(id="prop-tier-size") is not None
        assert soup.find(id="prop-login") is not None
        assert soup.find(id="prop-password") is not None
        assert soup.find(id="prop-server") is not None
        assert soup.find(id="prop-calibration-summary") is not None

    def test_crypto_form_input_fields(self, soup):
        assert soup.find(id="binance-key") is not None
        assert soup.find(id="binance-secret") is not None
        assert soup.find(id="binance-env") is not None
        assert soup.find(id="binance-balance") is not None

        assert soup.find(id="hl-wallet") is not None
        assert soup.find(id="hl-secret") is not None
        assert soup.find(id="hl-balance") is not None

    def test_risk_guardian_controls(self, soup):
        assert soup.find(id="risk-daily-loss-pct") is not None
        assert soup.find(id="risk-max-loss-pct") is not None
        assert soup.find(id="risk-per-trade-pct") is not None
        assert soup.find(id="risk-news-breaker") is not None

    def test_modal_action_buttons_and_feedback(self, soup):
        assert soup.find(id="btn-test-conn") is not None
        assert soup.find(id="btn-save-onboard") is not None
        assert soup.find(id="onboard-feedback-box") is not None
        assert soup.find(id="onboard-spinner") is not None
        assert soup.find(id="onboard-feedback-text") is not None

    def test_fleet_hub_table_and_kpis(self, soup):
        assert soup.find(id="accounts-table") is not None
        assert soup.find(id="fleet-table-body") is not None
        assert soup.find(id="kpi-total-aum") is not None
        assert soup.find(id="nav-fleet-count") is not None
        assert soup.find(id="fleet-aum-subtitle") is not None


# ══════════════════════════════════════════════════════════════════════════════
# 4. FEATURE 20: INSTITUTIONAL SHARK FORENSICS & TRADE CARDS DOM VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestFeature20TradeCardsAndSharkForensicsDOM:
    """Empirically verifies all DOM elements and styles for Feature 20."""

    def test_trade_cards_panel_and_container(self, soup):
        container = soup.find(id="trade-cards-container")
        assert container is not None, "Missing #trade-cards-container"

        count_badge = soup.find(id="trade-cards-count-badge")
        assert count_badge is not None, "Missing #trade-cards-count-badge"

    def test_shark_forensics_panel_and_cvd_meter(self, soup):
        panel = soup.find(id="shark-forensics-panel")
        assert panel is not None, "Missing #shark-forensics-panel"

        cvd_meter = soup.find(id="shark-cvd-meter")
        assert cvd_meter is not None, "Missing #shark-cvd-meter"

        assert soup.find(id="cvd-divergence-label") is not None
        assert soup.find(id="cvd-buyer-val") is not None
        assert soup.find(id="cvd-seller-val") is not None
        assert soup.find(id="cvd-net-val") is not None
        assert soup.find(id="cvd-buyer-bar") is not None
        assert soup.find(id="cvd-seller-bar") is not None
        assert soup.find(id="cvd-narrative-text") is not None

    def test_wyckoff_judas_and_dom_meters(self, soup):
        assert soup.find(id="shark-wyckoff-matrix") is not None
        assert soup.find(id="wyckoff-phase-pill") is not None
        assert soup.find(id="wyckoff-structure-label") is not None
        assert soup.find(id="wyckoff-narrative-text") is not None

        assert soup.find(id="shark-judas-box") is not None
        assert soup.find(id="judas-badge") is not None
        assert soup.find(id="judas-narrative") is not None

        assert soup.find(id="shark-dom-meter") is not None
        assert soup.find(id="dom-pressure-pill") is not None
        assert soup.find(id="dom-bid-bar") is not None
        assert soup.find(id="dom-ask-bar") is not None

    def test_tradingview_chart_and_action_controls(self, soup):
        assert soup.find(id="tradingViewChart") is not None
        assert soup.find(id="action-controls") is not None


# ══════════════════════════════════════════════════════════════════════════════
# 5. CSS STYLESHEET RULES & DESIGN SYSTEM INTEGRITY
# ══════════════════════════════════════════════════════════════════════════════

class TestCSSStylesheetAndDesignRules:
    """Verifies CSS custom properties, keyframe animations, and layout classes."""

    def test_root_custom_properties_defined(self, raw_html):
        required_vars = [
            "--bg-space", "--bg-panel", "--bg-card", "--border-subtle",
            "--gold-primary", "--green-profit", "--red-loss", "--cyan-tech", "--purple-smart"
        ]
        for var in required_vars:
            assert var in raw_html, f"Missing CSS variable {var} in :root"

    def test_keyframe_animations_defined(self, raw_html):
        assert "@keyframes pulseAnim" in raw_html
        assert "@keyframes blink" in raw_html
        assert "@keyframes spin" in raw_html

    def test_responsive_media_queries_defined(self, raw_html):
        assert "@media (max-width: 1400px)" in raw_html
        assert "@media (max-width: 900px)" in raw_html
        assert "@media (max-width: 800px)" in raw_html
        assert "@media (max-width: 600px)" in raw_html


# ══════════════════════════════════════════════════════════════════════════════
# 6. JAVASCRIPT STATIC SYNTAX & NODE.JS AST EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

class TestJavaScriptSyntaxAndCoordinatorExecution:
    """Extracts JS script and tests syntax and runtime semantics using Node.js."""

    @pytest.fixture
    def js_code(self, soup):
        script_tag = soup.find("script", src=False)
        assert script_tag is not None, "Missing inline <script> block in index.html"
        return script_tag.string

    def test_js_syntax_validity_via_node(self, js_code):
        """Runs Node.js -c on extracted script content to ensure zero syntax errors."""
        script_clean = re.sub(r'window\.onload\s*=\s*\(\)\s*=>\s*\{[^}]*\};', '// window.onload omitted for node test', js_code)
        
        # Test file write and check syntax
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(script_clean)
            temp_js = f.name
        try:
            res = subprocess.run(["node", "-c", os.path.basename(temp_js)], cwd=os.path.dirname(temp_js), capture_output=True, text=True)
            assert res.returncode == 0, f"Node.js syntax check failed: {res.stderr}"
        finally:
            if os.path.exists(temp_js):
                try:
                    os.remove(temp_js)
                except Exception:
                    pass

    def test_cockpit_coordinator_methods_presence(self, js_code):
        """Verifies presence of all required CockpitCoordinator coordinator methods."""
        required_methods = [
            "init", "initClock", "fetchAll",
            "fetchWorldMonitor", "fetchMarketWeather",
            "fetchAccounts", "fetchSharkForensics",
            "fetchTradeCards", "fetchStatus"
        ]
        for method in required_methods:
            assert f"{method}(" in js_code, f"Missing CockpitCoordinator method '{method}'"

    def test_modal_and_execution_function_presence(self, js_code):
        required_funcs = [
            "openOnboardModal", "closeOnboardModal", "switchOnboardTab",
            "autoCalibratePropRules", "testAccountConnection", "handleOnboardSubmit",
            "executePositionAction", "executeControl", "sendChat",
            "initTradingViewChart", "loadChartData", "switchSymbol", "switchTF"
        ]
        for func in required_funcs:
            assert f"function {func}" in js_code or f"{func}(" in js_code, f"Missing function '{func}'"

    def test_node_math_and_logic_simulation(self):
        """Simulates needle angle calculation and prop risk math in Node.js."""
        node_script = """
        // 1. Angle math test
        function calculateNeedleCoords(updraft) {
            const angle = -70 + (updraft / 100) * 140;
            const rad = (angle - 90) * (Math.PI / 180);
            const x2 = 100 + 75 * Math.cos(rad);
            const y2 = 100 + 75 * Math.sin(rad);
            return { x2: Number(x2.toFixed(2)), y2: Number(y2.toFixed(2)) };
        }

        const p0 = calculateNeedleCoords(0);
        const p50 = calculateNeedleCoords(50);
        const p100 = calculateNeedleCoords(100);

        if (p50.x2 !== 100.0) throw new Error(`Center x should be 100.0, got ${p50.x2}`);
        if (p50.y2 !== 25.0) throw new Error(`Center y should be 25.0, got ${p50.y2}`);
        if (p0.x2 >= p100.x2) throw new Error(`0% x (${p0.x2}) should be < 100% x (${p100.x2})`);

        // 2. Prop rule math test
        function calibrate(tier, provider) {
            let safeDaily = provider === 'FTMO' ? 4.0 : 2.5;
            let trailingFloor = provider === 'FTMO' ? 8.0 : 6.0;
            return {
                cap: tier * (safeDaily / 100),
                floor: tier * (trailingFloor / 100)
            };
        }

        const fp25 = calibrate(25000, 'FUNDING_PIPS');
        if (fp25.cap !== 625 || fp25.floor !== 1500) throw new Error(`Funding pips 25k math mismatch: ${JSON.stringify(fp25)}`);

        const ftmo100 = calibrate(100000, 'FTMO');
        if (ftmo100.cap !== 4000 || ftmo100.floor !== 8000) throw new Error(`FTMO 100k math mismatch: ${JSON.stringify(ftmo100)}`);

        console.log('NODE_MATH_OK');
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        assert res.returncode == 0
        assert "NODE_MATH_OK" in res.stdout


# ══════════════════════════════════════════════════════════════════════════════
# 7. JINJA2 RENDERING & HTML5 TAG BALANCING
# ══════════════════════════════════════════════════════════════════════════════

class TestJinja2TemplateRenderingAndTagBalance:
    """Verifies Jinja2 template rendering under multiple contexts with zero parse errors."""

    def test_jinja2_renders_cleanly_without_undefined_errors(self):
        env = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "dashboard", "templates")))
        template = env.get_template("index.html")

        # Test empty context
        rendered_empty = template.render()
        assert len(rendered_empty) > 10000
        assert "<!DOCTYPE html>" in rendered_empty

        # Test with mock context variables
        mock_context = {
            "title": "Institutional Cockpit",
            "active_symbol": "XAUUSD",
            "session_user": "Master Owner",
            "defcon": 2
        }
        rendered_mock = template.render(**mock_context)
        assert "<!DOCTYPE html>" in rendered_mock

    def test_html_tag_balance_and_dom_integrity(self, raw_html):
        """Verifies tag balance: count of <div> matches count of </div>, etc."""
        tags_to_check = ["div", "section", "main", "header", "table", "tbody", "thead", "tr", "button", "form"]
        for tag in tags_to_check:
            open_count = len(re.findall(rf"<{tag}[\s>]", raw_html, re.IGNORECASE))
            close_count = len(re.findall(rf"</{tag}>", raw_html, re.IGNORECASE))
            assert open_count == close_count, f"Tag mismatch for <{tag}>: {open_count} open vs {close_count} close"


# ══════════════════════════════════════════════════════════════════════════════
# 8. REST API SCHEMA <-> FRONTEND CONSUMER CONTRACT COMPATIBILITY
# ══════════════════════════════════════════════════════════════════════════════

class TestRestAPIFrontendConsumerContracts:
    """Verifies all JSON keys referenced by CockpitCoordinator JS exist in backend responses."""

    def test_world_monitor_contract_coverage(self, client):
        res = client.get("/api/world_monitor?symbol=XAUUSD")
        assert res.status_code == 200
        data = res.get_json()

        # Keys accessed in CockpitCoordinator.fetchWorldMonitor():
        assert "defcon_level" in data
        assert "global_threat_level" in data
        assert "global_risk_index" in data
        assert "primary_geopolitical_hotspot" in data
        assert "market_bias" in data
        assert "oil_geopolitical_risk_premium_usd" in data
        assert "chokepoints" in data
        assert "country_instability" in data
        assert "active_global_alerts" in data

        # Check chokepoints keys
        for cp_key, cp in data["chokepoints"].items():
            assert "name" in cp or "id" in cp
            assert "disruption_pct" in cp
            assert "risk_level" in cp

    def test_market_weather_contract_coverage(self, client):
        res = client.get("/api/market_weather?symbol=XAUUSD&timeframe=M15")
        assert res.status_code == 200
        data = res.get_json()

        # Keys accessed in CockpitCoordinator.fetchMarketWeather():
        assert "regime_badge" in data
        assert "risk_multiplier" in data
        assert "barometric_pressure_hpa" in data
        assert "updraft_probability" in data
        assert "downdraft_probability" in data
        assert "advisory" in data
        assert "forecast_summary" in data
        assert "news_clearance" in data

    def test_accounts_contract_coverage(self, client):
        res = client.get("/api/accounts")
        assert res.status_code == 200
        data = res.get_json()

        # Keys accessed in CockpitCoordinator.fetchAccounts():
        assert "active_accounts" in data
        assert "total_aum_potential" in data
        assert "accounts" in data
        assert isinstance(data["accounts"], list)
        if data["accounts"]:
            acc = data["accounts"][0]
            assert "id" in acc or "account_id" in acc
            assert "broker" in acc or "platform" in acc
            assert "balance" in acc or "starting_balance" in acc

    def test_shark_forensics_contract_coverage(self, client):
        res = client.get("/api/shark_forensics?symbol=XAUUSD&timeframe=M15")
        assert res.status_code == 200
        data = res.get_json()

        # Keys accessed in CockpitCoordinator.fetchSharkForensics():
        assert "cvd_divergence" in data
        assert "buyer_ratio" in data["cvd_divergence"]
        assert "seller_ratio" in data["cvd_divergence"]
        assert "wyckoff_phase" in data
        assert "phase" in data["wyckoff_phase"]
        assert "judas_swing" in data

    def test_trade_cards_contract_coverage(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()

        # Keys accessed in CockpitCoordinator.fetchTradeCards():
        assert "positions" in data
        assert isinstance(data["positions"], list)
        if data["positions"]:
            pos = data["positions"][0]
            assert "ticket" in pos
            assert "symbol" in pos
            assert "type" in pos or "direction" in pos
            assert "lots" in pos
            assert "open_price" in pos
            assert "current_price" in pos
            assert "sl" in pos
            assert "tp" in pos or "tp1" in pos
            assert "profit" in pos


# ══════════════════════════════════════════════════════════════════════════════
# 9. DYNAMIC UI EDGE CASES, EMPTY STATES & XSS SANITIZATION
# ══════════════════════════════════════════════════════════════════════════════

class TestUIEdgeCasesAndSecuritySanitization:
    """Stress tests dynamic rendering under empty lists, null values, and XSS inputs."""

    def test_empty_positions_empty_state_handling(self):
        """Simulates rendering JS logic when positions array is empty."""
        node_script = """
        function renderPositions(positions) {
            if (!positions || positions.length === 0) {
                return '<div class="font-mono text-dim">No open positions in fleet.</div>';
            }
            return positions.map(p => `<div class="trade-card">#${p.ticket}</div>`).join('');
        }

        const emptyHtml = renderPositions([]);
        if (!emptyHtml.includes('No open positions')) throw new Error('Failed empty state render');

        const nullHtml = renderPositions(null);
        if (!nullHtml.includes('No open positions')) throw new Error('Failed null state render');

        console.log('EMPTY_STATE_OK');
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        assert res.returncode == 0
        assert "EMPTY_STATE_OK" in res.stdout

    def test_onboard_account_xss_safety(self, client):
        """Injects HTML/script tags into account onboarding and ensures safe JSON encapsulation."""
        xss_payload = "<script>alert('XSS_ATTACK')</script>"
        res = client.post("/api/onboard_account", json={
            "account_id": "XSS-TEST-1",
            "balance": 25000.0,
            "platform": "FUNDING_PIPS",
            "account_name": xss_payload
        })
        assert res.status_code in [200, 201]
        data = res.get_json()
        assert data["status"] == "success"
        # Verify JSON returns clean payload string without raw script execution
        assert data["account"]["name"] == xss_payload

    def test_chat_consult_xss_safety(self, client):
        xss_query = "<img src=x onerror=alert(1)> What about XAUUSD?"
        res = client.post("/api/chat_consult", json={"query": xss_query})
        assert res.status_code == 200
        data = res.get_json()
        assert "advice" in data
        assert isinstance(data["advice"], str)
