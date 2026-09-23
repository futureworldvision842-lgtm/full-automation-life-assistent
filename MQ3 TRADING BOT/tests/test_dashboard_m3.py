"""
tests/test_dashboard_m3.py — Comprehensive Master Test Suite for Milestone M3.
=============================================================================
Milestone M3 (Requirement R3: WorldMonitor-Style Web Command Cockpit Overhaul).

Validates:
  1. Flask Route Availability & Template DOM Component Integrity (Features 17-20)
  2. GET /api/world_monitor (5 Maritime Chokepoints, 4-Pillar CII, DEFCON Levels, Polymarket Odds)
  3. GET /api/market_weather (Atmospheric Pressure, Updraft/Downdraft Probabilities, Regime Badges)
  4. GET /api/accounts & POST /api/onboard_account (Multi-Account Onboarding, Validation, Risk Rules)
  5. GET /api/shark_forensics (Lee-Ready CVD Absorption, Wyckoff Phase A-E, Dark Pool Footprint)
  6. GET /api/trade_cards (Live Visual Cards, PnL, R:R, Aladdin VaR Verification)
  7. POST /api/execution/action & POST /api/control (1-Click Risk Controls: Breakeven, Scale 50%, Close)
  8. Boundary Safety & HTTP Status Code Invariants (400 Bad Request, 405 Method Not Allowed)
"""

import json
import pytest
from dashboard.app import app, _RUNTIME_FLEET_STORE


@pytest.fixture
def client():
    """Provides a fresh Flask test client for isolated testing."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# 1. CORE ROUTE & TEMPLATE DOM INTEGRITY (Features 17–20)
# ══════════════════════════════════════════════════════════════════════════════

class TestFlaskCockpitBasics:
    """Verifies cockpit HTML loading and baseline telemetry endpoints."""

    def test_index_page_loads_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "<title>" in html
        assert "WorldMonitor" in html or "ALADDIN" in html

    def test_status_endpoint_returns_success(self, client):
        res = client.get("/api/status")
        assert res.status_code == 200
        data = res.get_json()
        assert "account" in data
        assert "prop_firm_gauges" in data
        assert data["account"]["balance"] > 0
        assert "daily_limit_pct" in data["prop_firm_gauges"]

    def test_template_contains_all_five_m3_components(self, client):
        """Verifies HTML DOM contains all 5 required UI elements and containers."""
        res = client.get("/")
        assert res.status_code == 200
        html = res.get_data(as_text=True)

        # Feature 17: Maritime Geopolitical Radar
        assert 'id="maritime-radar-panel"' in html or 'id="wm-radar-widget"' in html
        assert 'id="chokepoint-container"' in html
        assert 'id="defcon-level"' in html
        assert 'id="cii-bars-container"' in html

        # Feature 18: Market Weather Barometer
        assert 'id="market-weather-barometer"' in html or 'id="weather-barometer-widget"' in html
        assert 'id="regime-badge"' in html
        assert 'id="barometric-pressure"' in html
        assert 'id="updraft-gauge"' in html

        # Feature 19: Dynamic Multi-Account Onboarding Modal
        assert 'id="onboard-modal"' in html
        assert 'id="btn-open-onboard"' in html
        assert 'id="onboard-account-form"' in html
        assert 'id="tab-funding-pips"' in html or 'data-tab="tab-prop"' in html
        assert 'id="accounts-table"' in html

        # Feature 20: Visual Trade Cards & Institutional Shark Forensics
        assert 'id="trade-cards-container"' in html
        assert 'id="shark-forensics-panel"' in html
        assert 'id="shark-cvd-meter"' in html
        assert 'id="shark-wyckoff-matrix"' in html

        # TradingView Interactive Candlestick Chart
        assert 'id="tradingViewChart"' in html


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE 17: MARITIME GEOPOLITICAL RADAR ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

class TestWorldMonitorEndpoint:
    """Verifies GET /api/world_monitor contract, chokepoints, CII, and DEFCON."""

    def test_world_monitor_default_payload(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "defcon_level" in data
        assert 1 <= data["defcon_level"] <= 5
        assert "global_risk_index" in data
        assert 0.0 <= data["global_risk_index"] <= 100.0
        assert "primary_geopolitical_hotspot" in data

    def test_world_monitor_all_5_chokepoints_present(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        data = res.get_json()
        cps = data.get("chokepoints", {})

        required_chokepoints = ["hormuz_strait", "bab_el_mandeb", "suez", "malacca_strait", "taiwan_strait"]
        for cp in required_chokepoints:
            assert cp in cps, f"Missing strategic chokepoint {cp}"
            cp_data = cps[cp]
            assert "baseline_mbd" in cp_data
            assert "disruption_pct" in cp_data
            assert 0.0 <= cp_data["disruption_pct"] <= 100.0
            assert "risk_level" in cp_data
            assert "impact_multipliers" in cp_data

    def test_world_monitor_cii_instability_regions(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        data = res.get_json()
        cii = data.get("country_instability", data.get("instability_index", {}))

        expected_regions = ["MIDDLE_EAST_REGION", "EASTERN_EUROPE", "EAST_ASIA_PACIFIC", "EUROZONE", "UNITED_STATES"]
        for region in expected_regions:
            assert region in cii, f"Missing CII region {region}"
            score = cii[region].get("score", cii[region].get("composite_cii"))
            assert score is not None
            assert 0.0 <= float(score) <= 100.0

    def test_world_monitor_symbol_query_parameter(self, client):
        res = client.get("/api/world_monitor?symbol=BTCUSD")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("market_bias", {}).get("symbol") == "BTCUSD"

    def test_world_monitor_polymarket_and_alerts(self, client):
        res = client.get("/api/world_monitor")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data.get("polymarket_odds"), list)
        assert len(data.get("polymarket_odds")) >= 1
        assert isinstance(data.get("active_global_alerts"), list)

    def test_world_monitor_post_method_not_allowed(self, client):
        res = client.post("/api/world_monitor", json={"test": 123})
        assert res.status_code == 405


# ══════════════════════════════════════════════════════════════════════════════
# 3. FEATURE 18: MARKET WEATHER BAROMETER ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

class TestMarketWeatherEndpoint:
    """Verifies GET /api/market_weather contract, atmospheric barometers, and regimes."""

    def test_market_weather_default_payload(self, client):
        res = client.get("/api/market_weather")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "regime" in data
        assert "regime_badge" in data
        assert "updraft_probability" in data
        assert "downdraft_probability" in data
        assert "barometric_pressure_hpa" in data
        assert data["barometric_pressure_hpa"] > 900.0

    def test_market_weather_regime_badge_validity(self, client):
        res = client.get("/api/market_weather")
        assert res.status_code == 200
        data = res.get_json()
        valid_badges = {
            "CLEAR_UPDRAFT", "STORM_DOWNDRAFT", "HURRICANE_DOWNDRAFT",
            "GALE_UPDRAFT", "SQUALL_TRANSITION", "THUNDERSTORM_VOLATILITY",
            "FOGGY_LIQUIDITY_TRAP", "SUNNY_BULLISH_UPDRAFT", "STORMY_BEARISH_DOWNDRAFT"
        }
        assert data["regime_badge"] in valid_badges

    def test_market_weather_probabilities_sum_100(self, client):
        res = client.get("/api/market_weather?symbol=XAUUSD")
        assert res.status_code == 200
        data = res.get_json()
        updraft = float(data["updraft_probability"])
        downdraft = float(data["downdraft_probability"])
        assert 0.0 <= updraft <= 100.0
        assert 0.0 <= downdraft <= 100.0
        assert abs((updraft + downdraft) - 100.0) < 1.0

    def test_market_weather_custom_symbol_and_timeframe(self, client):
        res = client.get("/api/market_weather?symbol=EURUSD&timeframe=H1")
        assert res.status_code == 200
        data = res.get_json()
        assert data["symbol"] == "EURUSD"
        assert data["timeframe"] == "H1"

    def test_market_weather_news_clearance(self, client):
        res = client.get("/api/market_weather")
        assert res.status_code == 200
        data = res.get_json()
        assert "news_clearance" in data
        assert "advisory" in data

    def test_market_weather_post_method_not_allowed(self, client):
        res = client.post("/api/market_weather", json={"symbol": "XAUUSD"})
        assert res.status_code == 405


# ══════════════════════════════════════════════════════════════════════════════
# 4. FEATURE 19: MULTI-ACCOUNT FLEET & ONBOARDING ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiAccountAndOnboarding:
    """Verifies GET /api/accounts and POST /api/onboard_account validation & persistence."""

    def test_get_accounts_initial_state(self, client):
        res = client.get("/api/accounts")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert data["active_accounts"] >= 1
        assert data["total_aum_potential"] >= 25000.0
        assert len(data["accounts"]) >= 1

    def test_onboard_funding_pips_50k_account(self, client):
        payload = {
            "account_id": "FP-50K-9988",
            "balance": 50000.0,
            "platform": "FUNDING_PIPS",
            "server": "FundingPips-Server",
            "account_name": "Funding Pips 50k Challenger",
            "custom_risk_pct": 0.75
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code in [200, 201]
        data = res.get_json()
        assert data.get("status") == "success"
        assert data.get("success") is True
        assert "account" in data
        acc = data["account"]
        assert acc["account_id"] == "FP-50K-9988"
        assert acc["starting_balance"] == 50000.0
        assert acc["daily_loss_dollar_cap"] == 1250.0  # 2.5% of $50,000
        assert acc["trailing_hwm_floor"] == 47000.0   # 6.0% drawdown floor

    def test_onboard_ftmo_100k_account(self, client):
        payload = {
            "account_id": "FTMO-100K-3344",
            "balance": 100000.0,
            "platform": "FTMO",
            "server": "FTMO-Server",
            "account_name": "FTMO 100k Challenge",
            "custom_risk_pct": 1.0
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code in [200, 201]
        data = res.get_json()
        assert data.get("status") == "success"
        acc = data["account"]
        assert acc["starting_balance"] == 100000.0
        assert acc["daily_loss_dollar_cap"] == 4000.0  # 4.0% of $100k
        assert acc["trailing_hwm_floor"] == 92000.0   # 8.0% max loss

    def test_onboard_crypto_hyperliquid_account(self, client):
        payload = {
            "account_id": "HL-0x71C3948",
            "balance": 15000.0,
            "platform": "HYPERLIQUID",
            "server": "Arbitrum-Mainnet",
            "account_name": "Hyperliquid DEX Master Vault",
            "custom_risk_pct": 1.5
        }
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code in [200, 201]
        data = res.get_json()
        assert data.get("status") == "success"
        assert data["account"]["starting_balance"] == 15000.0

    def test_onboarded_account_reflected_in_get_accounts(self, client):
        unique_id = "UNIQUE-PERSIST-7777"
        payload = {
            "account_id": unique_id,
            "balance": 75000.0,
            "platform": "FUNDING_PIPS"
        }
        res_post = client.post("/api/onboard_account", json=payload)
        assert res_post.status_code in [200, 201]

        res_get = client.get("/api/accounts")
        assert res_get.status_code == 200
        data_get = res_get.get_json()
        account_ids = [str(a.get("id") or a.get("account_id")) for a in data_get["accounts"]]
        assert unique_id in account_ids

    def test_onboard_missing_account_id_returns_400(self, client):
        payload = {"balance": 25000.0, "platform": "FUNDING_PIPS"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 400
        data = res.get_json()
        assert data.get("status") == "error"
        assert "account_id" in data.get("message", "")

    def test_onboard_missing_balance_returns_400(self, client):
        payload = {"account_id": "TEST-NO-BAL", "platform": "FUNDING_PIPS"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 400
        data = res.get_json()
        assert data.get("status") == "error"
        assert "balance" in data.get("message", "")

    def test_onboard_negative_balance_returns_400(self, client):
        payload = {"account_id": "TEST-NEG", "balance": -5000.0, "platform": "FUNDING_PIPS"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 400
        data = res.get_json()
        assert data.get("status") == "error"

    def test_onboard_zero_balance_returns_400(self, client):
        payload = {"account_id": "TEST-ZERO", "balance": 0.0, "platform": "FUNDING_PIPS"}
        res = client.post("/api/onboard_account", json=payload)
        assert res.status_code == 400

    def test_onboard_non_json_body_returns_400(self, client):
        res = client.post("/api/onboard_account", data="invalid non json text", content_type="text/plain")
        assert res.status_code == 400

    def test_onboard_get_method_not_allowed(self, client):
        res = client.get("/api/onboard_account")
        assert res.status_code == 405


# ══════════════════════════════════════════════════════════════════════════════
# 5. FEATURE 20: INSTITUTIONAL SHARK FORENSICS & TRADE CARDS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSharkForensicsAndTradeCards:
    """Verifies GET /api/shark_forensics and GET /api/trade_cards."""

    def test_shark_forensics_payload_structure(self, client):
        res = client.get("/api/shark_forensics")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "wyckoff_phase" in data
        assert "phase" in data["wyckoff_phase"]
        assert "cvd_divergence" in data
        assert "buyer_ratio" in data["cvd_divergence"]
        assert "dark_pool_footprint" in data
        assert "turtle_soup_inducement" in data
        assert "asian_session_box" in data
        assert "judas_swing" in data

    def test_shark_forensics_cvd_ratios(self, client):
        res = client.get("/api/shark_forensics?symbol=XAUUSD")
        assert res.status_code == 200
        data = res.get_json()
        cvd = data["cvd_divergence"]
        buyer = float(cvd["buyer_ratio"])
        seller = float(cvd["seller_ratio"])
        assert 0.0 <= buyer <= 1.0
        assert 0.0 <= seller <= 1.0
        assert abs((buyer + seller) - 1.0) < 0.01

    def test_shark_forensics_symbols_catalog(self, client):
        res = client.get("/api/shark_forensics")
        assert res.status_code == 200
        data = res.get_json()
        symbols = data.get("symbols", {})
        assert "XAUUSD" in symbols
        assert "BTCUSD" in symbols
        assert "EURUSD" in symbols

    def test_trade_cards_payload_structure(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "positions" in data
        assert "pending_signals" in data
        assert "summary" in data
        assert isinstance(data["positions"], list)
        assert isinstance(data["pending_signals"], list)

    def test_trade_cards_position_metrics(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()
        positions = data.get("positions", [])
        if positions:
            pos = positions[0]
            assert "ticket" in pos
            assert "symbol" in pos
            assert "lots" in pos
            assert "open_price" in pos
            assert "sl" in pos
            assert "profit" in pos or "pnl" in pos

    def test_trade_cards_pending_signals_aladdin_var(self, client):
        res = client.get("/api/trade_cards")
        assert res.status_code == 200
        data = res.get_json()
        signals = data.get("pending_signals", [])
        if signals:
            sig = signals[0]
            assert "symbol" in sig
            assert "reward_to_risk" in sig or "rr_ratio" in sig
            assert "aladdin_var_approved" in sig


# ══════════════════════════════════════════════════════════════════════════════
# 6. 1-CLICK RAPID RISK EXECUTION & CONTROL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionActionControls:
    """Verifies POST /api/execution/action and POST /api/control."""

    def test_execution_action_breakeven(self, client):
        payload = {"ticket": 9841201, "action": "breakeven"}
        res = client.post("/api/execution/action", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "Breakeven" in data.get("message", "")

    def test_execution_action_scale_50(self, client):
        payload = {"ticket": 9841201, "action": "scale_50"}
        res = client.post("/api/execution/action", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"
        assert "scaled out 50%" in data.get("message", "")

    def test_execution_action_close(self, client):
        payload = {"ticket": 9841201, "action": "close"}
        res = client.post("/api/execution/action", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"

    def test_execution_action_trail_fvg(self, client):
        payload = {"ticket": 9841201, "action": "trail_fvg"}
        res = client.post("/api/execution/action", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("status") == "success"

    def test_execution_action_missing_action_returns_400(self, client):
        payload = {"ticket": 9841201}
        res = client.post("/api/execution/action", json=payload)
        assert res.status_code == 400

    def test_control_pause_and_resume(self, client):
        res_pause = client.post("/api/control", json={"action": "pause"})
        assert res_pause.status_code == 200
        assert res_pause.get_json().get("success") is True

        res_resume = client.post("/api/control", json={"action": "resume"})
        assert res_resume.status_code == 200
        assert res_resume.get_json().get("success") is True

    def test_chart_data_endpoint(self, client):
        res = client.get("/api/chart_data/XAUUSD?tf=M15")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("symbol") == "XAUUSD"
        assert "candles" in data
        assert len(data["candles"]) > 0
        candle = data["candles"][0]
        assert "time" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle


# ══════════════════════════════════════════════════════════════════════════════
# 7. ALPHA MODELS & SELF-EVOLUTION ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAlphaModelsEndpoint:
    """Verifies GET /api/alpha_models schema and metrics."""

    def test_alpha_models_returns_200_and_schema(self, client):
        res = client.get("/api/alpha_models")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, dict)
        assert "total_live_trades_analyzed" in data or "models" in data or "active_alpha_models" in data

    def test_alpha_models_win_rate_and_state(self, client):
        res = client.get("/api/alpha_models")
        assert res.status_code == 200
        data = res.get_json()
        if "overall_win_rate_pct" in data:
            assert data["overall_win_rate_pct"] > 50.0
        if "active_alpha_models" in data:
            assert data["active_alpha_models"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 8. WHATSAPP LIVE PORTAL & DIRECTIVE WEBHOOK TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestWhatsAppDirectivesAndPortal:
    """Verifies GET /whatsapp pairing portal and POST /whatsapp directive webhook."""

    def test_whatsapp_portal_get_returns_200_html(self, client):
        res = client.get("/whatsapp")
        assert res.status_code == 200
        assert "html" in res.content_type.lower() or "text/html" in res.headers.get("Content-Type", "")
        assert b"WhatsApp" in res.data or b"Sovereign AI Copilot" in res.data

    def test_whatsapp_directive_status(self, client):
        payload = {"command": "STATUS", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"
        assert len(data.get("response", data.get("reply", ""))) > 0

    def test_whatsapp_directive_kill(self, client):
        payload = {"command": "KILL", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"

    def test_whatsapp_directive_close_all(self, client):
        payload = {"command": "CLOSE ALL", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"

    def test_whatsapp_directive_be(self, client):
        payload = {"command": "BE", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"

    def test_whatsapp_directive_scale50(self, client):
        payload = {"command": "SCALE50", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"

    def test_whatsapp_directive_scale_50_with_space(self, client):
        payload = {"command": "SCALE 50", "sender": "923468053268"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("success") is True or data.get("status") == "success"

    def test_whatsapp_unauthorized_sender_rejected(self, client):
        payload = {"command": "KILL", "sender": "19999999999"}
        res = client.post("/whatsapp", json=payload)
        assert res.status_code == 403
        data = res.get_json()
        assert data.get("success") is False


# ══════════════════════════════════════════════════════════════════════════════
# 9. LIQUIDATION RADAR ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLiquidationRadarEndpoint:
    """Verifies GET /api/liquidation_radar across core symbols."""

    def test_liquidation_radar_btcusd(self, client):
        res = client.get("/api/liquidation_radar?symbol=BTCUSD")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("symbol") == "BTCUSD"
        assert "liquidity_magnet" in data or "bsl_clusters" in data or "stop_pools" in data

    def test_liquidation_radar_all_core_assets(self, client):
        for sym in ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            res = client.get(f"/api/liquidation_radar?symbol={sym}")
            assert res.status_code == 200
            data = res.get_json()
            assert data.get("symbol") == sym
            assert data.get("status") == "success" or "liquidity_magnet" in data

