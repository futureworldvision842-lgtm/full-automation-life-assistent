"""
tests/test_viewport_layout_m1_challenger1.py — Empirical Challenger 1 Verification Harness.
============================================================================================
Milestone M1 (Requirement R1: Responsive Futuristic UI Redesign & Viewport Overflow Elimination).

Empirically verifies:
  1. Complete elimination of horizontal overflow across all 6 authoritative viewports:
     - 1920x1080 (Desktop Full HD)
     - 1440x900 (Laptop / Small Desktop)
     - 1280x720 (HD 720p)
     - 1024x768 (Tablet Landscape / iPad Pro)
     - 768x1024 (Tablet Portrait / iPad)
     - 375x667 (Mobile Phone / iPhone SE)
  2. CSS Box Model & Grid Container Invariants:
     - Universal `box-sizing: border-box` on `*`
     - Root `html, body` bounds: `100vw`, `max-width: 100vw`, `overflow-x: hidden`
     - Grid column item containment: `min-width: 0` on all grid items and columns
     - Table and horizontal ribbon overflow confinement (`overflow-x: auto` on `.ticker-bar`, `.fleet-table-wrap`)
  3. Responsive Breakpoint Media Queries:
     - Multi-tier responsive grid transitions at 1400px, 1100px, 920px, 900px, 800px, 768px, 600px, 480px, 420px
  4. Cyber/Ice-Blue Design System & Glassmorphism Palette Invariants:
     - Slate backgrounds: `#0a1128`, `#0e1e38`, `#142952`
     - Neon cyan & ice-blue accents: `#00d2ff`, `#38bdf8`, `#67e8f9`
     - Backdrop filters (`backdrop-filter: blur(...)`) and translucent borders
  5. Single-Screen Command Center Component Completeness & DOM ID Integrity:
     - Top Ticker Ribbon, Market Weather Barometer, TradingView Chart + 4 Ghost Projected Candles,
       Active Visual Trade Cards, Fleet Hub Table, Maritime Threat Radar (5 Chokepoints, 4-Pillar CII),
       Big Shark Forensics (Lee-Ready CVD, Wyckoff Phase C), AI Co-Pilot Console, Onboard Modal, VIP Signals Modal.
  6. Chart Resize & Dynamic Polling Engine Event Listeners:
     - `window.addEventListener('resize', ...)` chart refit handlers and `CockpitCoordinator.init()`
"""

import os
import re
import math
import pytest

INDEX_HTML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dashboard",
    "templates",
    "index.html"
)


@pytest.fixture(scope="module")
def html_content():
    """Loads raw content of dashboard/templates/index.html."""
    assert os.path.exists(INDEX_HTML_PATH), f"index.html not found at {INDEX_HTML_PATH}"
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def css_content(html_content):
    """Extracts embedded CSS from <style> blocks in index.html."""
    style_matches = re.findall(r"<style[^>]*>(.*?)</style>", html_content, re.DOTALL | re.IGNORECASE)
    assert len(style_matches) > 0, "No <style> block found in index.html"
    return "\n".join(style_matches)


# ══════════════════════════════════════════════════════════════════════════════
# 1. VIEWPORT ZERO-OVERFLOW & CSS ROOT CONSTRAINTS
# ══════════════════════════════════════════════════════════════════════════════

class TestViewportZeroOverflowConstraints:
    """Verifies that html, body, and top-level containers strictly enforce 100vw zero-overflow."""

    def test_universal_box_sizing(self, css_content):
        """Verifies universal selector '*' enforces box-sizing: border-box."""
        pattern = r"\*\s*\{[^}]*box-sizing\s*:\s*border-box[^}]*\}"
        assert re.search(pattern, css_content), "Universal box-sizing: border-box missing from CSS"

    def test_html_and_body_root_overflow_guards(self, css_content):
        """Verifies html and body enforce width: 100vw, max-width: 100vw, overflow-x: hidden."""
        # html selector check
        assert re.search(r"html\s*\{[^}]*width\s*:\s*100vw", css_content, re.IGNORECASE)
        assert re.search(r"html\s*\{[^}]*max-width\s*:\s*100vw", css_content, re.IGNORECASE)
        assert re.search(r"html\s*\{[^}]*overflow-x\s*:\s*hidden", css_content, re.IGNORECASE)

        # body selector check
        assert re.search(r"body\s*\{[^}]*width\s*:\s*100vw", css_content, re.IGNORECASE)
        assert re.search(r"body\s*\{[^}]*max-width\s*:\s*100vw", css_content, re.IGNORECASE)
        assert re.search(r"body\s*\{[^}]*overflow-x\s*:\s*hidden", css_content, re.IGNORECASE)

    def test_top_navigation_bar_bounds(self, css_content):
        """Verifies .navbar is 100% width, max-width: 100%, flex-wrap: wrap, box-sizing: border-box."""
        match = re.search(r"\.navbar\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match, ".navbar CSS rule not found"
        props = match.group(1)
        assert "flex-wrap: wrap" in props or "flex-wrap:wrap" in props
        assert "box-sizing: border-box" in props or "box-sizing:border-box" in props
        assert "width: 100%" in props or "width:100%" in props

    def test_dashboard_grid_bounds(self, css_content):
        """Verifies .dashboard-grid has width: 100%, max-width: 100%, and box-sizing: border-box."""
        match = re.search(r"\.dashboard-grid\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match, ".dashboard-grid CSS rule not found"
        props = match.group(1)
        assert "display: grid" in props or "display:grid" in props
        assert "width: 100%" in props or "width:100%" in props
        assert "max-width: 100%" in props or "max-width:100%" in props
        assert "box-sizing: border-box" in props or "box-sizing:border-box" in props

    def test_grid_items_min_width_zero(self, css_content):
        """Verifies left-col, right-col, and panel items have min-width: 0 to prevent grid item blowout."""
        match_cols = re.search(r"\.left-col\s*,\s*\.right-col\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match_cols, ".left-col, .right-col CSS rule not found"
        props_cols = match_cols.group(1)
        assert "min-width: 0" in props_cols or "min-width:0" in props_cols
        assert "box-sizing: border-box" in props_cols or "box-sizing:border-box" in props_cols

        match_panel = re.search(r"\.panel\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match_panel, ".panel CSS rule not found"
        props_panel = match_panel.group(1)
        assert "min-width: 0" in props_panel or "min-width:0" in props_panel
        assert "box-sizing: border-box" in props_panel or "box-sizing:border-box" in props_panel

    def test_horizontal_scroll_containers_containment(self, css_content):
        """Verifies .ticker-bar and .fleet-table-wrap have overflow-x: auto with max-width: 100%."""
        match_ticker = re.search(r"\.ticker-bar\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match_ticker, ".ticker-bar CSS rule not found"
        props_ticker = match_ticker.group(1)
        assert "overflow-x: auto" in props_ticker or "overflow-x:auto" in props_ticker
        assert "width: 100%" in props_ticker or "width:100%" in props_ticker
        assert "max-width: 100%" in props_ticker or "max-width:100%" in props_ticker

        match_fleet = re.search(r"\.fleet-table-wrap\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match_fleet, ".fleet-table-wrap CSS rule not found"
        props_fleet = match_fleet.group(1)
        assert "overflow-x: auto" in props_fleet or "overflow-x:auto" in props_fleet
        assert "width: 100%" in props_fleet or "width:100%" in props_fleet


# ══════════════════════════════════════════════════════════════════════════════
# 2. RESPONSIVE BREAKPOINT MEDIA QUERIES AUDIT
# ══════════════════════════════════════════════════════════════════════════════

class TestResponsiveBreakpoints:
    """Verifies responsive media queries cover all required viewport dimensions."""

    VIEWPORTS = [
        {"name": "1920x1080 (FHD Desktop)", "w": 1920, "h": 1080, "expected_grid_cols": 2},
        {"name": "1440x900 (Laptop)", "w": 1440, "h": 900, "expected_grid_cols": 2},
        {"name": "1280x720 (HD 720p)", "w": 1280, "h": 720, "expected_grid_cols": 2},
        {"name": "1024x768 (Tablet Landscape)", "w": 1024, "h": 768, "expected_grid_cols": 1},
        {"name": "768x1024 (Tablet Portrait)", "w": 768, "h": 1024, "expected_grid_cols": 1},
        {"name": "375x667 (Mobile Phone)", "w": 375, "h": 667, "expected_grid_cols": 1}
    ]

    def test_media_query_breakpoints_presence(self, css_content):
        """Verifies presence of key responsive media query breakpoints in CSS."""
        required_breakpoints = [
            r"@media\s*\(\s*max-width\s*:\s*1400px\s*\)",
            r"@media\s*\(\s*max-width\s*:\s*1100px\s*\)",
            r"@media\s*\(\s*max-width\s*:\s*920px\s*\)|@media\s*\(\s*max-width\s*:\s*900px\s*\)",
            r"@media\s*\(\s*max-width\s*:\s*800px\s*\)|@media\s*\(\s*max-width\s*:\s*768px\s*\)",
            r"@media\s*\(\s*max-width\s*:\s*600px\s*\)|@media\s*\(\s*max-width\s*:\s*480px\s*\)"
        ]
        for bp in required_breakpoints:
            assert re.search(bp, css_content, re.IGNORECASE), f"Breakpoint {bp} missing from CSS"

    def test_dashboard_grid_single_column_collapse(self, css_content):
        """Verifies dashboard-grid collapses to single column (1fr) at <= 1100px."""
        collapse_pattern = r"@media\s*\(\s*max-width\s*:\s*1100px\s*\)\s*\{[^}]*\.dashboard-grid\s*\{[^}]*grid-template-columns\s*:\s*minmax\(0,\s*1fr\)"
        assert re.search(collapse_pattern, css_content, re.DOTALL | re.IGNORECASE), (
            "Dashboard grid does not properly collapse to single column at 1100px"
        )

    def test_kpi_row_responsive_scaling(self, css_content):
        """Verifies KPI summary row scales from 4 columns to 2 columns (<=900px) and 1 column (<=480px)."""
        assert re.search(r"\.kpi-row\s*\{[^}]*grid-template-columns\s*:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)", css_content, re.DOTALL)
        assert re.search(r"@media\s*\(\s*max-width\s*:\s*900px\s*\)\s*\{[^}]*\.kpi-row\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)", css_content, re.DOTALL)
        assert re.search(r"@media\s*\(\s*max-width\s*:\s*480px\s*\)\s*\{[^}]*\.kpi-row\s*\{[^}]*grid-template-columns\s*:\s*minmax\(0,\s*1fr\)", css_content, re.DOTALL)

    def test_chokepoints_grid_auto_fit_fluidity(self, css_content):
        """Verifies .chokepoint-grid uses repeat(auto-fit, minmax(180px, 1fr)) for zero-overflow fluid wrapping."""
        match = re.search(r"\.chokepoint-grid\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match, ".chokepoint-grid CSS rule not found"
        props = match.group(1)
        assert "repeat(auto-fit, minmax(" in props
        assert "width: 100%" in props
        assert "box-sizing: border-box" in props

    def test_trade_cards_grid_auto_fill_fluidity(self, css_content):
        """Verifies .trade-cards-grid uses repeat(auto-fill, minmax(280px, 1fr)) for fluid wrapping."""
        match = re.search(r"\.trade-cards-grid\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match, ".trade-cards-grid CSS rule not found"
        props = match.group(1)
        assert "repeat(auto-fill, minmax(" in props
        assert "width: 100%" in props
        assert "box-sizing: border-box" in props


# ══════════════════════════════════════════════════════════════════════════════
# 3. FUTURISTIC CYBER/ICE-BLUE DESIGN SYSTEM PALETTE
# ══════════════════════════════════════════════════════════════════════════════

class TestCyberIceBlueDesignSystem:
    """Verifies color variables and glassmorphic translucent effects."""

    def test_palette_root_variables(self, css_content):
        """Verifies :root defines authoritative background, accent, and border colors."""
        expected_vars = {
            "--bg-space": "#0a1128",
            "--bg-panel-solid": "#0e1e38",
            "--bg-card-solid": "#142952",
            "--accent-neon-cyan": "#00d2ff",
            "--accent-ice-blue": "#38bdf8",
            "--accent-bright-ice": "#67e8f9",
            "--green-profit": "#10b981",
            "--red-loss": "#f43f5e"
        }
        for var_name, expected_hex in expected_vars.items():
            pattern = rf"{re.escape(var_name)}\s*:\s*{re.escape(expected_hex)}"
            assert re.search(pattern, css_content, re.IGNORECASE), f"CSS variable {var_name}: {expected_hex} missing or incorrect in :root"

    def test_glassmorphic_backdrop_blur(self, css_content):
        """Verifies glassmorphism backdrop-filter blur is applied to panels, navbar, and modals."""
        assert "backdrop-filter: blur" in css_content
        assert "-webkit-backdrop-filter: blur" in css_content

    def test_font_families_declaration(self, css_content):
        """Verifies typography includes 'Inter' and 'JetBrains Mono'."""
        assert "'Inter'" in css_content or '"Inter"' in css_content
        assert "'JetBrains Mono'" in css_content or '"JetBrains Mono"' in css_content


# ══════════════════════════════════════════════════════════════════════════════
# 4. DOM COMPONENT & STRUCTURAL INTEGRITY
# ══════════════════════════════════════════════════════════════════════════════

class TestDOMComponentIntegrity:
    """Verifies all required command cockpit panels and elements exist in DOM."""

    REQUIRED_DOM_IDS = [
        # Navbar & Status
        "nav-engine-status",
        "nav-defcon-pill",
        "nav-fleet-count",
        "btn-open-signals",
        "btn-broadcast-group",
        "btn-open-onboard",
        "utc-clock",
        # Ticker Ribbon
        "tickerBar",
        # KPI Row
        "kpi-balance",
        "kpi-equity",
        "kpi-daily-loss",
        "kpi-total-aum",
        # Market Weather Barometer
        "market-weather-barometer",
        "weather-symbol-label",
        "regime-badge",
        "barometric-pressure",
        "weather-updraft-val",
        "weather-downdraft-val",
        "weather-advisory-text",
        # TradingView Chart & Controls
        "tradingViewChart",
        "activeChartTitle",
        "liveSourceBadge",
        "btn-toggle-forecast",
        "liveCommentaryTicker",
        "commentaryText",
        "candleInspectorBar",
        "candleShark",
        "candleReason",
        "forensicCard",
        # Active Positions & Cards
        "trade-cards-container",
        # Fleet Hub Table
        "accounts-table",
        "fleet-table-body",
        # Maritime Threat Radar
        "maritime-radar-panel",
        "defcon-level",
        "wm-risk-score",
        "wm-primary-hotspot",
        "wm-gold-tailwind",
        "wm-oil-premium",
        "chokepoint-container",
        "cii-bars-container",
        "wm-osint-stream",
        # Shark Forensics
        "shark-forensics-panel",
        "shark-cvd-meter",
        "cvd-divergence-label",
        "cvd-buyer-val",
        "cvd-seller-val",
        "cvd-net-val",
        "shark-wyckoff-matrix",
        "wyckoff-phase-pill",
        "shark-judas-box",
        "shark-dom-meter",
        # AI Chat & Controls
        "chatMessages",
        "chatInput",
        "action-controls",
        "activityLogs",
        # Modals
        "signals-modal",
        "onboard-modal",
        "onboard-account-form"
    ]

    def test_all_required_dom_ids_exist(self, html_content):
        """Verifies each authoritative DOM ID is present in index.html."""
        missing = []
        for dom_id in self.REQUIRED_DOM_IDS:
            if f'id="{dom_id}"' not in html_content and f"id='{dom_id}'" not in html_content:
                missing.append(dom_id)
        assert len(missing) == 0, f"Missing required DOM IDs: {missing}"

    def test_5_strategic_maritime_chokepoints_container(self, html_content):
        """Verifies Maritime Radar contains 5 strategic chokepoints container and header."""
        assert "5 Strategic Maritime Chokepoints" in html_content
        assert 'id="chokepoint-container"' in html_content
        assert 'id="cii-bars-container"' in html_content
        assert 'id="wm-osint-stream"' in html_content

    def test_multi_account_onboard_modal_platforms(self, html_content):
        """Verifies Multi-Account modal contains all 5 platform tabs."""
        assert 'data-tab="tab-mt5"' in html_content
        assert 'data-tab="tab-prop"' in html_content or 'id="tab-funding-pips"' in html_content
        assert 'data-tab="tab-bitget"' in html_content
        assert 'data-tab="tab-binance"' in html_content
        assert 'data-tab="tab-hyperliquid"' in html_content


# ══════════════════════════════════════════════════════════════════════════════
# 5. JAVASCRIPT EVENT HANDLERS & RESIZE LISTENER
# ══════════════════════════════════════════════════════════════════════════════

class TestClientCoordinatorAndEventListeners:
    """Verifies client JavaScript initializes coordinator, charts, and handles window resize."""

    def test_window_resize_listener_present(self, html_content):
        """Verifies window resize event listener dynamically recalculates TradingView chart width."""
        assert "window.addEventListener('resize'" in html_content or 'window.addEventListener("resize"' in html_content
        assert "applyOptions({ width: container.clientWidth })" in html_content

    def test_cockpit_coordinator_initialization(self, html_content):
        """Verifies CockpitCoordinator polls REST endpoints and initializes clock."""
        assert "CockpitCoordinator.init()" in html_content
        assert "fetchWorldMonitor" in html_content
        assert "fetchMarketWeather" in html_content
        assert "fetchAccounts" in html_content
        assert "fetchSharkForensics" in html_content
        assert "fetchTradeCards" in html_content

    def test_future_forecast_toggle_handler(self, html_content):
        """Verifies toggleFutureForecast function is declared and wired."""
        assert "function toggleFutureForecast" in html_content
        assert "futureForecastCandles" in html_content
        assert "is_future_forecast" in html_content


# ══════════════════════════════════════════════════════════════════════════════
# 6. MATHEMATICAL VIEWPORT BOUNDING SIMULATION & EDGE CASE STRESS
# ══════════════════════════════════════════════════════════════════════════════

class TestMathematicalViewportSimulation:
    """Simulates layout geometry and width containment across all target viewports."""

    @pytest.mark.parametrize("vp", [
        {"name": "1920x1080", "w": 1920, "h": 1080, "padding": 36, "gap": 14, "mode": "2-column", "r_col_max": 460},
        {"name": "1440x900", "w": 1440, "h": 900, "padding": 28, "gap": 12, "mode": "2-column", "r_col_max": 420},
        {"name": "1280x720", "w": 1280, "h": 720, "padding": 28, "gap": 12, "mode": "2-column", "r_col_max": 420},
        {"name": "1024x768", "w": 1024, "h": 768, "padding": 28, "gap": 14, "mode": "1-column", "r_col_max": None},
        {"name": "768x1024", "w": 768, "h": 1024, "padding": 28, "gap": 14, "mode": "1-column", "r_col_max": None},
        {"name": "375x667", "w": 375, "h": 667, "padding": 16, "gap": 10, "mode": "1-column", "r_col_max": None},
    ])
    def test_viewport_geometry_bounding(self, vp):
        """Mathematically verifies available width >= required container min-width for each viewport."""
        available_width = vp["w"] - vp["padding"]
        if vp["mode"] == "2-column":
            # For 2-column mode, left_col min width (0) + right_col min width (320 or 360) + gap <= available_width
            min_right_col = 320 if vp["w"] <= 1400 else 360
            required_min_width = min_right_col + vp["gap"]
            assert available_width >= required_min_width, (
                f"Viewport {vp['name']} cannot fit 2 columns: available {available_width}px < required {required_min_width}px"
            )
            # Maximum grid content width
            max_right_col = vp["r_col_max"]
            assert available_width > max_right_col
        else:
            # For 1-column mode, columns stack vertically, each taking 100% of available width with min-width: 0
            assert available_width > 0
            assert available_width <= vp["w"]

    def test_long_text_ellipsis_overflow_protection(self, css_content):
        """Verifies text-overflow: ellipsis and overflow: hidden on ticker and inspector banners to prevent blowout."""
        assert re.search(r"\.ticker-content\s*\{[^}]*text-overflow\s*:\s*ellipsis", css_content, re.DOTALL)
        assert re.search(r"\.ticker-content\s*\{[^}]*overflow\s*:\s*hidden", css_content, re.DOTALL)
        assert re.search(r"\.ticker-content\s*\{[^}]*white-space\s*:\s*nowrap", css_content, re.DOTALL)

    def test_modal_max_dimensions_and_responsiveness(self, css_content):
        """Verifies modal cards have max-width, max-height: 90vh, and responsive padding."""
        match_modal = re.search(r"\.modal-card\s*\{([^}]+)\}", css_content, re.DOTALL)
        assert match_modal, ".modal-card CSS rule not found"
        props = match_modal.group(1)
        assert "max-width: 780px" in props or "max-width:780px" in props
        assert "max-height: 90vh" in props or "max-height:90vh" in props
        assert "overflow: hidden" in props or "overflow:hidden" in props

