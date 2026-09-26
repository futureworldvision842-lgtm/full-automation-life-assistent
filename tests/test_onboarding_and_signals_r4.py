"""
tests/test_onboarding_and_signals_r4.py
========================================================================================
Institutional Test Suite for Milestone M4 / R4 Deltas & R2/R3 Sovereign Masterpiece UI:
  1. Universal 1-Click Onboarding Rule Extraction (GET & POST /api/accounts/rules/extract)
     - FundingPips deterministic 0.75% ($750 cap), 80% daily freeze, R:R >= 2.50 floor,
       dynamic +1.0R breakeven, 15m blackout, anti-ban proxy allocation
     - Broad multi-firm matrix: FTMO, Topstep, 5%ers, Exness, Bybit, Binance, Hyperliquid
  2. Crypto API Ingestion with Zero Plaintext Disk Leaks (POST /api/accounts/onboard)
     - Ingestion of exchange_platform, api_key, api_secret, passphrase
     - Strict isolation in os.environ, zero credentials in fleet JSON or response
  3. Autonomous Multi-Timeframe Signals Aggregator API (GET /api/trading/signals/autonomous)
     - Institutional setups for XAUUSD, EURUSD, GBPUSD, USDJPY, BTCUSD, SOLUSD
     - Confidence score (0-100), M15/H1/H4 confirmation, R:R >= 2.50, $750 max risk cap
     - Query symbol filtering
  4. Sovereign Masterpiece UI Integration:
     - R2 Delta: MacroContagionSphere3D script tag and macro contagion container
     - R3 Delta: jarvis:smc:pattern_clicked event listener and Explainable AI modal
     - R4 Delta 1: Universal 1-Click Onboarding Modal with 3 tabs and real-time rule preview
  5. Zero Prohibited Identifiers Scan across all owned files.
========================================================================================
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
import dashboard
from trading.multi_account_manager import (
    MultiAccountManager,
    get_multi_account_manager,
    extract_firm_rules,
    get_prop_firm_preset,
    PROP_FIRM_PRESETS,
)


@pytest.fixture(scope="module")
def client():
    """Provides a Starlette TestClient bound to the flagship dashboard app."""
    return TestClient(dashboard.app)


class TestRuleExtractionEndpoint:
    """Tests GET and POST /api/accounts/rules/extract."""

    def test_fundingpips_100k_rules_get(self, client):
        resp = client.get("/api/accounts/rules/extract?firm=FundingPips&balance=100000")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ok"] is True
        assert data["firm"] == "FundingPips"
        assert data["balance"] == 100000.0
        assert data["daily_loss_limit_pct"] == 5.0
        assert data["daily_loss_limit_usd"] == 5000.0
        assert data["overall_loss_limit_pct"] == 10.0
        assert data["overall_loss_limit_usd"] == 10000.0
        # 80% daily freeze: 5000.0 * 0.80 = 4000.0
        assert data["daily_freeze_threshold_usd"] == 4000.0
        # Deterministic FundingPips cap: <= 0.75% ($750 max cap)
        assert data["max_risk_per_trade_pct"] <= 0.75
        assert data["max_risk_usd_cap"] <= 750.0
        # R:R >= 2.50 floor & dynamic +1.0R breakeven
        assert data["min_rr_ratio"] >= 2.50
        assert data["dynamic_breakeven_r"] == 1.0
        # News blackout & anti-ban proxy
        assert data["news_blackout_minutes"] == 15
        assert data["anti_ban_layers"] == 5
        assert data["assigned_proxy_country"] == "AE"

    def test_fundingpips_rules_post(self, client):
        payload = {"firm": "fundingpips", "balance": 100000.0}
        resp = client.post("/api/accounts/rules/extract", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["ok"] is True
        assert data["firm"] == "FundingPips"
        assert data["balance"] == 100000.0
        assert data["daily_freeze_threshold_usd"] == 4000.0
        assert data["max_risk_usd_cap"] == 750.0
        assert data["min_rr_ratio"] >= 2.50
        assert data["dynamic_breakeven_r"] == 1.0
        assert data["news_blackout_minutes"] == 15
        assert data["assigned_proxy_country"] == "AE"

    def test_fundingpips_large_balance_strictly_capped_at_750(self, client):
        # Even with $200k balance, FundingPips risk cap must remain strictly <= $750.0
        resp = client.get("/api/accounts/rules/extract?firm=FundingPips&balance=200000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == 200000.0
        assert data["max_risk_usd_cap"] == 750.0
        assert data["daily_loss_limit_usd"] == 10000.0
        assert data["daily_freeze_threshold_usd"] == 8000.0

    def test_fundingpips_small_balance_proportional_risk(self, client):
        # At $50k balance, 0.75% is $375, which is <= $750 cap
        resp = client.get("/api/accounts/rules/extract?firm=FundingPips&balance=50000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == 50000.0
        assert data["max_risk_usd_cap"] == 375.0

    def test_multi_firm_rule_matrix(self, client):
        # FTMO
        ftmo = client.get("/api/accounts/rules/extract?firm=ftmo&balance=100000").json()
        assert ftmo["ok"] is True
        assert ftmo["assigned_proxy_country"] == "CZ"
        assert ftmo["min_rr_ratio"] >= 2.50

        # Topstep
        topstep = client.get("/api/accounts/rules/extract?firm=topstep&balance=100000").json()
        assert topstep["ok"] is True
        assert topstep["assigned_proxy_country"] == "US"
        assert topstep["daily_loss_limit_pct"] == 4.0

        # 5%ers
        five_pct = client.get("/api/accounts/rules/extract?firm=5%25ers&balance=100000").json()
        assert five_pct["ok"] is True
        assert five_pct["assigned_proxy_country"] == "UK"

        # Exness
        exness = client.get("/api/accounts/rules/extract?firm=exness&balance=50000").json()
        assert exness["ok"] is True
        assert exness["assigned_proxy_country"] == "CY"

        # Bybit
        bybit = client.get("/api/accounts/rules/extract?firm=bybit&balance=50000").json()
        assert bybit["ok"] is True
        assert bybit["assigned_proxy_country"] == "SG"

        # Binance
        binance = client.get("/api/accounts/rules/extract?firm=binance&balance=100000").json()
        assert binance["ok"] is True
        assert binance["assigned_proxy_country"] == "SG"

    def test_direct_manager_rule_extraction(self):
        manager = get_multi_account_manager()
        rules = manager.extract_rules("FundingPips", 100000.0)
        assert rules["ok"] is True
        assert rules["firm"] == "FundingPips"
        assert rules["max_risk_usd_cap"] <= 750.0
        assert rules["daily_freeze_threshold_usd"] == 4000.0
        assert rules["anti_ban_layers"] == 5


class TestCryptoApiIngestion:
    """Tests Crypto API key ingestion with zero plaintext disk exposure (POST /api/accounts/onboard)."""

    def test_crypto_onboard_env_only_storage(self, client):
        account_id = "test_binance_vault_901"
        payload = {
            "account_id": account_id,
            "account_name": "Sovereign Binance Prop API",
            "exchange_platform": "binance",
            "api_key": "BINANCE_LIVE_API_KEY_SUPER_SECRET_12345",
            "api_secret": "BINANCE_SECRET_HMAC_HEX_OCTET_ABCDEF",
            "passphrase": "binance_vault_passphrase_secure",
            "balance": 150000.0,
            "preset": "binance"
        }

        resp = client.post("/api/accounts/onboard", json=payload)
        assert resp.status_code == 200
        res_json = resp.json()

        assert res_json["status"] == "success"
        assert res_json["ok"] is True
        assert res_json["account_id"] == account_id

        # Verify plaintext secrets are NEVER returned in response JSON
        raw_text = resp.text
        assert "BINANCE_LIVE_API_KEY_SUPER_SECRET_12345" not in raw_text
        assert "BINANCE_SECRET_HMAC_HEX_OCTET_ABCDEF" not in raw_text
        assert "binance_vault_passphrase_secure" not in raw_text

        # Verify secrets are isolated in os.environ
        expected_key_env = f"BINANCE_API_KEY_{account_id}"
        expected_secret_env = f"BINANCE_API_SECRET_{account_id}"
        expected_pass_env = f"BINANCE_PASSPHRASE_{account_id}"

        assert os.environ.get(expected_key_env) == "BINANCE_LIVE_API_KEY_SUPER_SECRET_12345"
        assert os.environ.get(expected_secret_env) == "BINANCE_SECRET_HMAC_HEX_OCTET_ABCDEF"
        assert os.environ.get(expected_pass_env) == "binance_vault_passphrase_secure"

        # Verify fleet config JSON on disk DOES NOT contain the plaintext credentials
        fleet_file = PROJECT_ROOT / "config" / "multi_account_fleet.json"
        if fleet_file.exists():
            disk_content = fleet_file.read_text(encoding="utf-8")
            assert "BINANCE_LIVE_API_KEY_SUPER_SECRET_12345" not in disk_content
            assert "BINANCE_SECRET_HMAC_HEX_OCTET_ABCDEF" not in disk_content
            assert "binance_vault_passphrase_secure" not in disk_content

    def test_bybit_crypto_onboard(self, client):
        account_id = "test_bybit_vault_902"
        payload = {
            "account_id": account_id,
            "account_name": "Bybit Institutional Hedging",
            "exchange_platform": "bybit",
            "api_key": "BYBIT_API_KEY_TEST_ALPHA",
            "api_secret": "BYBIT_SECRET_HASH_TEST_BETA",
            "balance": 100000.0,
            "preset": "bybit"
        }

        resp = client.post("/api/accounts/onboard", json=payload)
        assert resp.status_code == 200
        res_json = resp.json()
        assert res_json["ok"] is True

        assert "BYBIT_API_KEY_TEST_ALPHA" not in resp.text
        assert "BYBIT_SECRET_HASH_TEST_BETA" not in resp.text
        assert os.environ.get(f"BYBIT_API_KEY_{account_id}") == "BYBIT_API_KEY_TEST_ALPHA"
        assert os.environ.get(f"BYBIT_API_SECRET_{account_id}") == "BYBIT_SECRET_HASH_TEST_BETA"


class TestAutonomousSignalsAggregator:
    """Tests GET /api/trading/signals/autonomous."""

    def test_autonomous_signals_payload_structure(self, client):
        resp = client.get("/api/trading/signals/autonomous")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ok"] is True
        assert "timestamp" in data
        assert "signals" in data
        assert isinstance(data["signals"], list)
        assert len(data["signals"]) >= 6

        # Check risk governor block
        assert "risk_governor" in data
        gov = data["risk_governor"]
        assert gov["max_risk_usd_cap"] <= 750.0
        assert gov["max_risk_pct"] <= 0.75
        assert gov["min_rr_floor"] >= 2.50
        assert gov["dynamic_breakeven_r"] == 1.0
        assert gov["news_blackout_minutes"] == 15

    def test_all_six_institutional_instruments_present(self, client):
        resp = client.get("/api/trading/signals/autonomous")
        signals = resp.json()["signals"]
        symbols = {s["symbol"] for s in signals}

        expected_symbols = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "SOLUSD"}
        assert expected_symbols.issubset(symbols), f"Missing symbols: {expected_symbols - symbols}"

    def test_signal_confluences_and_risk_parameters(self, client):
        resp = client.get("/api/trading/signals/autonomous")
        signals = resp.json()["signals"]

        for sig in signals:
            sym = sig["symbol"]
            # Confidence score between 0 and 100
            assert 0.0 <= sig["confidence"] <= 100.0, f"Confidence out of bounds for {sym}"
            assert sig["confidence"] >= 80.0, f"Low confidence signal found for {sym}"

            # Multi-timeframe confirmation (M15, H1, H4)
            mtf = sig["timeframe_confirmation"]
            assert "m15" in mtf and len(mtf["m15"]) > 0, f"Missing m15 confirmation for {sym}"
            assert "h1" in mtf and len(mtf["h1"]) > 0, f"Missing h1 confirmation for {sym}"
            assert "h4" in mtf and len(mtf["h4"]) > 0, f"Missing h4 confirmation for {sym}"

            # Entry, SL, TP numerical validity
            entry = float(sig["entry"])
            sl = float(sig["stop_loss"])
            tp = float(sig["take_profit"])
            assert entry > 0 and sl > 0 and tp > 0

            # Strict Risk:Reward >= 2.50
            rr = float(sig["risk_reward_ratio"])
            assert rr >= 2.50, f"R:R ratio {rr} is below 2.50 floor for {sym}"

            # FundingPips risk cap <= $750.0 and <= 0.75%
            assert sig["risk_amount_usd"] <= 750.0, f"Risk USD {sig['risk_amount_usd']} exceeds $750 for {sym}"
            assert sig["risk_pct"] <= 0.75, f"Risk pct {sig['risk_pct']} exceeds 0.75% for {sym}"

            # Dynamic breakeven and news blackout
            assert sig["dynamic_breakeven_r"] == 1.0
            assert sig["news_blackout_buffer_min"] == 15

    def test_signal_query_filter_by_symbol(self, client):
        # Test XAUUSD filter
        resp_gold = client.get("/api/trading/signals/autonomous?symbol=XAUUSD")
        assert resp_gold.status_code == 200
        gold_signals = resp_gold.json()["signals"]
        assert len(gold_signals) == 1
        assert gold_signals[0]["symbol"] == "XAUUSD"

        # Test BTCUSD filter
        resp_btc = client.get("/api/trading/signals/autonomous?symbol=BTCUSD")
        assert resp_btc.status_code == 200
        btc_signals = resp_btc.json()["signals"]
        assert len(btc_signals) == 1
        assert btc_signals[0]["symbol"] == "BTCUSD"


class TestSovereignMasterpieceHtmlDeltas:
    """Verifies R2, R3, and R4 Delta UI markup and scripts in web/sovereign_masterpiece.html."""

@pytest.fixture(scope="module")
def html_content():
    html_path = PROJECT_ROOT / "web" / "sovereign_masterpiece.html"
    assert html_path.exists(), "web/sovereign_masterpiece.html does not exist"
    return html_path.read_text(encoding="utf-8")


class TestSovereignMasterpieceHtmlDeltas:
    """Verifies R2, R3, and R4 Delta UI markup and scripts in web/sovereign_masterpiece.html."""

    def test_r2_macro_contagion_sphere_included_and_mounted(self, html_content):
        # R2 Delta: MacroContagionSphere3D.js script tag
        assert '<script src="/js/MacroContagionSphere3D.js"></script>' in html_content
        # Macro contagion container and mount point
        assert 'id="macroContagionContainer"' in html_content
        assert 'id="macroContagionSphereMount"' in html_content
        # Mount function invocation
        assert "mountMacroContagionSphere" in html_content
        assert "MacroContagionSphere3D" in html_content

    def test_r3_smc_pattern_clicked_event_and_explainable_ai_modal(self, html_content):
        # R3 Delta: Event listener for 'jarvis:smc:pattern_clicked'
        assert "'jarvis:smc:pattern_clicked'" in html_content or '"jarvis:smc:pattern_clicked"' in html_content
        # Explainable AI modal element
        assert 'id="explainableAiModal"' in html_content
        # Calls POST /api/trading/explain
        assert "/api/trading/explain" in html_content
        # Bilingual AI modal tabs (EN and UR)
        assert "btnThesisEn" in html_content
        assert "btnThesisUr" in html_content
        assert "switchExplainLang" in html_content

    def test_r4_universal_onboarding_modal_with_three_tabs_and_rule_preview(self, html_content):
        # R4 Delta 1: Universal 1-Click Onboarding Modal
        assert 'id="universalOnboardingModal"' in html_content
        # Three tabs: Prop Firms, Broker MT5, Crypto APIs
        assert 'id="tabBtnProp"' in html_content
        assert 'id="tabBtnBroker"' in html_content
        assert 'id="tabBtnCrypto"' in html_content
        # Tab content containers
        assert 'id="paneOnboardProp"' in html_content
        assert 'id="paneOnboardBroker"' in html_content
        assert 'id="paneOnboardCrypto"' in html_content
        # Real-time rule preview grid
        assert 'id="onboardRulePreviewGrid"' in html_content
        # Dynamic rule extraction call to /api/accounts/rules/extract
        assert "/api/accounts/rules/extract" in html_content
        assert "updateOnboardRulePreview" in html_content
        assert "submitUniversalOnboardingModal" in html_content


class TestZeroProhibitedIdentifiers:
    """Verifies that none of the modified/owned files contain prohibited tokens."""

    PROHIBITED_TOKEN = "".join(["g", "u", "l", "l", "a", "m"])

    def test_zero_prohibited_tokens_in_owned_files(self):
        owned_files = [
            PROJECT_ROOT / "dashboard.py",
            PROJECT_ROOT / "trading" / "multi_account_manager.py",
            PROJECT_ROOT / "core" / "trading" / "custom_strategy_engine.py",
            PROJECT_ROOT / "web" / "sovereign_masterpiece.html",
            PROJECT_ROOT / "tests" / "test_onboarding_and_signals_r4.py",
        ]

        violations = []
        for file_path in owned_files:
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if self.PROHIBITED_TOKEN in text.lower():
                violations.append(str(file_path))

        assert len(violations) == 0, f"Prohibited identifier found in: {violations}"
