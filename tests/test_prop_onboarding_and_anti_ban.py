"""
tests/test_prop_onboarding_and_anti_ban.py
========================================================================================
Institutional Unit & Integration Test Suite for Prop Firm Onboarding, 5-Layer Anti-Ban Shield,
and Autonomous Risk Enforcement (Milestone M3 / Requirement R3).

Covers:
  1. Universal Web Onboarding Endpoint POST /api/accounts/onboard (FastAPI dashboard.py :8770)
  2. Universal Web Onboarding Endpoint POST /api/accounts/onboard (Flask app.py :5050)
  3. Plaintext Password Isolation & Zero Credential Exposure
  4. 1-Click Preset Rule Templates for all 6 required prop firms + personal broker
  5. 5-Layer Sovereign Anti-Ban Shield:
       - Layer 1: Portable MT5 Terminal & IPC Port Segregation
       - Layer 2: Geo-Matched Residential SOCKS5 Proxy
       - Layer 3: Anti-Correlation Jitter (350-1800ms) & Fisher-Yates Sequence Shuffling
       - Layer 4: Pipette Micro-Tick SL/TP Dispersion (+/- 0.5 to 2.0 pips)
       - Layer 5: Dynamic SHA-256 Hashed Magic Numbers
  6. Autonomous Risk Enforcement:
       - Real-time 80% Daily Drawdown Freeze (both multi_account_manager & fleet_risk_manager)
       - 15-Minute Pre/Post High-Impact Economic News Blackout Enforcement
  7. Strict Identity & Compliance Verification (0 occurrences of unauthorized handles)

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
========================================================================================
"""

import copy
import os
import sys
import json
import pytest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))

from trading.multi_account_manager import (
    AccountRiskProfile,
    AntiCopyShield,
    MultiAccountManager,
    PropFirmPreset,
    PROP_FIRM_PRESETS,
    ProxyConfig,
    TerminalInstanceConfig,
    get_multi_account_manager,
    get_prop_firm_preset,
)
from src.prop_rules import (
    PROFILES as MQ3_PROFILES,
    build_account_policy,
    list_supported_profiles,
)
from src.multi_account_auto_onboarder import (
    MultiAccountAutoOnboarder,
)
from src.fleet_risk_manager import (
    FleetRiskManager,
)


# =====================================================================
# 1. 1-CLICK PRESET RULE TEMPLATES VERIFICATION (ALL 6 PROP FIRMS)
# =====================================================================

class TestPropFirmPresetTemplates:
    """Verifies presets across multi_account_manager, prop_rules, and auto_onboarder."""

    REQUIRED_FIRMS = [
        "fundingpips",
        "ftmo",
        "thefundedtrader",
        "5%ers",
        "alphacapital",
        "e8",
    ]

    def test_multi_account_manager_presets_exist(self):
        """All 6 required prop firms plus personal broker exist with accurate limits."""
        for firm in self.REQUIRED_FIRMS:
            preset = get_prop_firm_preset(firm)
            assert preset is not None, f"Preset '{firm}' missing from PROP_FIRM_PRESETS"
            assert preset.max_daily_drawdown_pct > 0
            assert preset.max_total_drawdown_pct > 0
            assert preset.freeze_dd_ratio == 0.80, "Freeze ratio must be 80% of daily limit"
            assert preset.per_trade_risk_pct <= 0.75, "Fail-closed risk cap must be <= 0.75%"

    def test_fundingpips_preset_rules(self):
        fp = get_prop_firm_preset("fundingpips")
        assert fp.max_daily_drawdown_pct == 5.0
        assert fp.max_total_drawdown_pct == 10.0
        assert fp.news_restricted is True, "FundingPips restricts high-impact news trading"
        assert fp.freeze_dd_ratio == 0.80

    def test_ftmo_preset_rules(self):
        ftmo = get_prop_firm_preset("ftmo")
        assert ftmo.max_daily_drawdown_pct == 5.0
        assert ftmo.max_total_drawdown_pct == 10.0
        assert ftmo.news_restricted is False, "FTMO allows news holding on swing model"
        assert ftmo.weekend_holding_allowed is True

    def test_the_funded_trader_preset_rules(self):
        tft = get_prop_firm_preset("thefundedtrader")
        assert tft.max_daily_drawdown_pct == 5.0
        assert tft.max_total_drawdown_pct == 10.0
        assert tft.news_restricted is True, "The Funded Trader enforces news blackout"
        assert tft.news_lockout_minutes == 15

    def test_the_5ers_preset_rules(self):
        five_ers = get_prop_firm_preset("5%ers")
        assert five_ers.max_daily_drawdown_pct == 4.0, "5%ers has 4% daily drawdown limit"
        assert five_ers.max_total_drawdown_pct == 8.0, "5%ers has 8% total drawdown limit"
        assert five_ers.weekend_holding_allowed is True

    def test_alpha_capital_preset_rules(self):
        alpha = get_prop_firm_preset("alphacapital")
        assert alpha.max_daily_drawdown_pct == 5.0
        assert alpha.max_total_drawdown_pct == 10.0
        assert alpha.news_restricted is True

    def test_e8_preset_rules(self):
        e8 = get_prop_firm_preset("e8")
        assert e8.max_daily_drawdown_pct == 5.0
        assert e8.max_total_drawdown_pct == 8.0, "E8 has 8% max drawdown limit"

    def test_mq3_prop_rules_profiles_registered(self):
        """Validates that MQ3 prop_rules.py registers all 6 firm models."""
        expected_models = [
            "FUNDING_PIPS_2_STEP_STANDARD",
            "FTMO_STANDARD",
            "THE_FUNDED_TRADER_STANDARD",
            "THE_5ERS_BOOTCAMP",
            "ALPHA_CAPITAL_STANDARD",
            "E8_EVALUATION",
        ]
        for model in expected_models:
            assert model in MQ3_PROFILES, f"Model '{model}' missing from prop_rules.PROFILES"
            policy = build_account_policy(account_size=100000.0, model=model, stage="EVALUATION_PHASE_1")
            assert policy["account_size"] == 100000.0
            assert policy["internal_daily_stop_pct"] <= policy["hard_daily_loss_pct"]
            assert policy["internal_risk_per_trade_pct"] <= 0.75

    def test_mq3_multi_account_auto_onboarder_profiles(self):
        """Validates that MultiAccountAutoOnboarder recognizes all 6 firm types."""
        onboarder = MultiAccountAutoOnboarder()
        for firm in ["FUNDING_PIPS", "FTMO", "THE_FUNDED_TRADER", "THE_5ERS", "ALPHA_CAPITAL", "E8"]:
            norm = onboarder.normalize_account_type(firm)
            assert norm in onboarder.PROP_FIRM_PROFILES, f"Profile for '{firm}' not in auto_onboarder"


# =====================================================================
# 2. 5-LAYER SOVEREIGN ANTI-BAN SHIELD VERIFICATION
# =====================================================================

class TestFiveLayerAntiBanShield:
    """Verifies all 5 layers of anti-detection in trading/multi_account_manager.py."""

    def test_layer_1_isolated_portable_mt5_instance(self):
        """Layer 1: Isolated /portable directory, dedicated IPC port, and launch args."""
        cfg = TerminalInstanceConfig(
            account_id="998877",
            firm_name="FundingPips",
            terminal_dir="C:\\MT5_Fleet\\FundingPips_998877",
            executable_path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",
            portable_mode=True,
            ipc_port=18825,
            password_env="MT5_PASSWORD_998877",
            server="FundingPips-Server",
        )
        valid, errs = cfg.validate_isolation_constraints()
        assert valid is True
        assert len(errs) == 0

        args = cfg.get_command_line_args()
        assert "/portable" in args, "Must specify /portable to avoid shared %APPDATA% contamination"
        assert 1024 <= cfg.ipc_port <= 65535

    def test_layer_2_geo_matched_residential_proxy(self):
        """Layer 2: Geo-matched static residential proxy configuration."""
        proxy = ProxyConfig(
            enabled=True,
            proxy_type="SOCKS5",
            host="127.0.0.1",
            port=10815,
            username_env="PROXY_USER_998877",
            password_env="PROXY_PASS_998877",
            target_country="AE",
            static_ip=True,
            dns_leak_protection=True,
        )
        valid, errs = proxy.validate_sanity()
        assert valid is True
        assert len(errs) == 0

        ini = proxy.generate_mt5_ini_snippet()
        assert "ProxyEnable=1" in ini
        assert "ProxyType=2" in ini  # SOCKS5 code

        env = proxy.generate_worker_environment()
        assert env["ALL_PROXY"].startswith("socks5://")
        assert env["MT5_PROXY_COUNTRY"] == "AE"

    def test_layer_3_jitter_and_fisher_yates_shuffling(self):
        """Layer 3: 350-1800ms randomized jitter and Fisher-Yates execution shuffling."""
        shield = AntiCopyShield(min_delay_ms=350, max_delay_ms=1800, seed=42)

        delays = [shield.compute_jitter_delay_ms(account_index=i, account_id=f"acc_{i}") for i in range(100)]
        for d in delays:
            assert 350 <= d <= 1800, f"Jitter delay {d}ms outside [350, 1800]ms range"

        # Shuffling across multiple accounts
        accounts = ["acc_alpha", "acc_beta", "acc_gamma", "acc_delta", "acc_epsilon"]
        shuffled_1 = shield.shuffle_accounts(accounts)
        assert set(shuffled_1) == set(accounts)

    def test_layer_4_pipette_micro_tick_dispersion(self):
        """Layer 4: +/- 0.5 to 2.0 pip dispersion preserving risk and R:R constraints."""
        shield = AntiCopyShield(min_sl_offset_pips=0.5, max_sl_offset_pips=2.0, seed=123)

        entry = 2350.00
        original_sl = 2345.00
        original_tp = 2365.00

        new_sl, new_tp, meta = shield.perturb_sl_tp(
            symbol="XAUUSD",
            side="BUY",
            entry=entry,
            sl=original_sl,
            tp=original_tp,
            max_allowed_sl_loss_usd=750.0,
            lot_size=0.10,
            preserve_min_rr=2.5,
        )

        assert meta["sl_perturbed_pips"] >= 0.49, "SL offset must be >= 0.5 pips"
        assert meta["sl_perturbed_pips"] <= 2.05, "SL offset must be <= 2.0 pips"
        assert meta["computed_rr"] >= 2.5, "Risk:Reward ratio must be >= 2.5"
        assert meta["effective_risk_usd"] <= 750.0, "Risk must not exceed $750 dollar cap"
        assert new_sl != original_sl, "SL must be perturbed"

    def test_layer_5_dynamic_sha256_magic_numbers(self):
        """Layer 5: Unique SHA-256 hashed Magic Numbers per account and trade."""
        shield = AntiCopyShield()

        magic_1 = shield.generate_dynamic_magic_number(account_id="40000294403", base_magic=700000, symbol="XAUUSD", trade_index=0)
        magic_2 = shield.generate_dynamic_magic_number(account_id="1514382598", base_magic=700000, symbol="XAUUSD", trade_index=0)
        magic_3 = shield.generate_dynamic_magic_number(account_id="40000294403", base_magic=700000, symbol="XAUUSD", trade_index=1)

        assert magic_1 != magic_2, "Magic numbers across different accounts must be unique"
        assert magic_1 != magic_3, "Magic numbers across different trade indices must be unique"
        assert isinstance(magic_1, int) and magic_1 > 700000


# =====================================================================
# 3. AUTONOMOUS RISK ENFORCEMENT (80% DD FREEZE & NEWS BLACKOUT)
# =====================================================================

class TestAutonomousRiskEnforcement:
    """Verifies instant freeze at 80% of allowed daily limit and news lockout."""

    def test_multi_account_manager_80_percent_drawdown_freeze(self, tmp_path):
        """Account trading freezes when daily equity drawdown reaches 80% of daily limit."""
        cfg_file = tmp_path / "fleet_test.json"
        mgr = MultiAccountManager(config_path=cfg_file)

        # Onboard FundingPips account ($100k balance, 5% daily DD = $5,000 limit. 80% of 5% is 4.0% = $4,000 loss).
        res = mgr.onboard_account({
            "login_id": "112233",
            "account_name": "FundingPips Test",
            "preset": "fundingpips",
            "balance": 100000.0,
            "target_country": "AE",
            "password": "SecretTestPassword123"
        })
        assert res["ok"] is True

        profile = mgr.fleet["fundingpips_112233"]
        assert profile.max_daily_drawdown_pct == 5.0
        assert profile.freeze_dd_ratio == 0.80

        # Scenario A: Loss is 2.0% ($2,000 drawdown -> equity $98,000) => NOT frozen
        frozen, reason = mgr.check_account_drawdown_freeze("112233", current_equity=98000.0)
        assert frozen is False
        admission = profile.evaluate_admission_rules(symbol="XAUUSD", sl_pips=20.0, rr_ratio=2.5)
        assert admission["admitted"] is True

        # Scenario B: Loss hits 4.0% exactly ($4,000 drawdown -> equity $96,000, 80% of 5%) => INSTANT FREEZE
        frozen, reason = mgr.check_account_drawdown_freeze("112233", current_equity=96000.0)
        assert frozen is True
        assert "DAILY_DRAWDOWN_80_PERCENT_FREEZE" in reason
        assert profile.is_frozen is True

        # Order admission blocked
        admission = profile.evaluate_admission_rules(symbol="XAUUSD", sl_pips=20.0, rr_ratio=2.5)
        assert admission["admitted"] is False
        assert any("80_PERCENT_FREEZE" in b for b in admission["blockers"])

    def test_fleet_risk_manager_80_percent_drawdown_freeze(self, tmp_path):
        """MQ3 FleetRiskManager triggers frozen_80_pct at 80% of daily loss cap."""
        fleet_cfg = tmp_path / "fleet_risk_test.json"
        frm = FleetRiskManager(config_path=str(fleet_cfg))

        # Register account with starting balance $100,000 and 5% max daily loss = $5,000 cap
        frm.accounts_state["test_acc"] = {
            "account_id": "test_acc",
            "account_name": "Test Account",
            "starting_balance": 100000.0,
            "balance": 100000.0,
            "equity": 100000.0,
            "daily_sod_equity": 100000.0,
            "max_daily_loss_pct": 0.05,
            "daily_loss_dollar_cap": 5000.0,
            "freeze_dd_ratio": 0.80,
            "max_total_loss_pct": 0.10,
            "trailing_hwm_floor": 90000.0,
            "absolute_hwm": 100000.0,
            "allowed_assets": ["XAUUSD", "EURUSD"],
            "consistency_cap_pct": 50.0,
            "is_active": True,
            "is_locked_out": False,
            "lockout_reason": None,
            "account_type": "FUNDING_PIPS",
            "server": "Demo-Server",
            "server_day": "2026-09-20",
        }

        # Equity drops to $96,500 (Loss = $3,500 < $4,000 freeze limit) => SAFE
        frm.accounts_state["test_acc"]["equity"] = 96500.0
        shield = frm.check_daily_loss_shield("test_acc")
        assert shield["safe"] is True
        assert shield["frozen_80_pct"] is False

        # Equity drops to $95,900 (Loss = $4,100 > $4,000 freeze limit) => 80% FREEZE TRIGGERED
        frm.accounts_state["test_acc"]["equity"] = 95900.0
        shield = frm.check_daily_loss_shield("test_acc")
        assert shield["safe"] is False
        assert shield["frozen_80_pct"] is True
        assert "DAILY DRAWDOWN 80% FREEZE" in shield["message"]

        # evaluate_daily_drawdown_freeze check
        eval_freeze = frm.evaluate_daily_drawdown_freeze("test_acc", current_equity=95900.0)
        assert eval_freeze["is_frozen"] is True
        assert eval_freeze["can_trade"] is False

    def test_economic_news_blackout_enforcement(self):
        """Orders blocked during 15-minute high impact economic news window for restricted firms."""
        frm = FleetRiskManager()
        frm.accounts_state["fp_news_test"] = {
            "account_id": "fp_news_test",
            "account_name": "FP News Test",
            "starting_balance": 100000.0,
            "balance": 100000.0,
            "equity": 100000.0,
            "daily_sod_equity": 100000.0,
            "max_daily_loss_pct": 0.05,
            "daily_loss_dollar_cap": 5000.0,
            "max_total_loss_pct": 0.10,
            "trailing_hwm_floor": 90000.0,
            "absolute_hwm": 100000.0,
            "allowed_assets": ["XAUUSD"],
            "consistency_cap_pct": 50.0,
            "is_active": True,
            "is_locked_out": False,
            "news_restricted": True,
            "account_type": "FUNDING_PIPS",
        }

        # News lockout active -> trade MUST be rejected
        ok, reason = frm.validate_pre_trade_risk(
            account_id="fp_news_test",
            symbol="XAUUSD",
            lot_size=0.10,
            side="BUY",
            entry_price=2350.0,
            sl_price=2340.0,
            news_lockout_active=True,
        )
        assert ok is False
        assert "15-minute high-impact economic news blackout" in reason

    def test_onboard_account_all_six_presets(self, tmp_path):
        """Validates that onboard_account correctly configures all 6 prop firm presets."""
        cfg_file = tmp_path / "fleet_all_presets.json"
        mgr = MultiAccountManager(config_path=cfg_file)

        presets_to_test = [
            ("fundingpips", "101", 5.0, 10.0, 4.0, True),
            ("ftmo", "102", 5.0, 10.0, 4.0, False),
            ("thefundedtrader", "103", 5.0, 10.0, 4.0, True),
            ("5%ers", "104", 4.0, 8.0, 3.2, False),
            ("alphacapital", "105", 5.0, 10.0, 4.0, True),
            ("e8", "106", 5.0, 8.0, 4.0, False),
        ]

        for preset_key, acc_id, expected_daily, expected_total, expected_freeze, expected_news_restr in presets_to_test:
            res = mgr.onboard_account({
                "login_id": acc_id,
                "account_name": f"{preset_key.upper()} Test",
                "preset": preset_key,
                "balance": 100000.0,
                "target_country": "US",
                "password": f"Pass_{acc_id}!",
            })
            assert res["ok"] is True
            rules = res["risk_rules"]
            assert rules["max_daily_drawdown_pct"] == expected_daily
            assert rules["max_total_drawdown_pct"] == expected_total
            assert rules["freeze_daily_drawdown_pct"] == expected_freeze
            assert rules["news_restricted"] == expected_news_restr
            assert "layer_1_portable_mt5" in res["anti_ban_assigned"]
            assert "layer_2_geo_proxy" in res["anti_ban_assigned"]
            assert "layer_3_jitter_shuffle" in res["anti_ban_assigned"]
            assert "layer_4_pipette_dispersion" in res["anti_ban_assigned"]
            assert "layer_5_dynamic_magic" in res["anti_ban_assigned"]

    def test_multi_account_dispatch_selective_news_lockout(self, tmp_path):
        """Verifies dispatch blocks news-restricted accounts while admitting swing-exempt accounts during news."""
        cfg_file = tmp_path / "fleet_news_dispatch.json"
        mgr = MultiAccountManager(config_path=cfg_file)

        # Register FundingPips (news restricted)
        mgr.onboard_account({
            "login_id": "201",
            "account_name": "FP News Restricted",
            "preset": "fundingpips",
            "balance": 100000.0,
            "password": "pass1",
        })
        # Register FTMO (swing news allowed)
        mgr.onboard_account({
            "login_id": "202",
            "account_name": "FTMO Swing Exempt",
            "preset": "ftmo",
            "balance": 100000.0,
            "password": "pass2",
        })

        signal = {
            "symbol": "EURUSD",
            "signal_type": "BUY",
            "entry_price": 1.08500,
            "sl_price": 1.08300,
            "tp_price": 1.09000,
        }

        # News lockout active: FundingPips blocked, FTMO admitted
        dispatch = mgr.prepare_anti_detection_dispatch(signal, news_lockout_active=True)
        dispatches = dispatch["dispatches"]

        fp_key = "fundingpips_201"
        ftmo_key = "ftmo_202"

        assert dispatches[fp_key]["admitted"] is False
        assert any("News Lockout Active" in b for b in dispatches[fp_key]["blockers"])

        assert dispatches[ftmo_key]["admitted"] is True
        assert dispatches[ftmo_key]["order_payload"]["magic"] > 0



# =====================================================================
# 4. WEB ONBOARDING ENDPOINTS & CREDENTIAL ISOLATION
# =====================================================================

class TestWebOnboardingAndCredentialIsolation:
    """Verifies POST /api/accounts/onboard across both servers (:8770 and :5050)."""

    def test_fastapi_master_dashboard_onboarding_route(self):
        """FastAPI POST /api/accounts/onboard on dashboard.py."""
        from starlette.testclient import TestClient
        import dashboard

        client = TestClient(dashboard.app)
        payload = {
            "account_name": "FastAPI Master Account",
            "login_id": "77112233",
            "broker_server": "FundingPips-Live",
            "password": "SuperSecretPassword99!",
            "balance": 100000.0,
            "account_type": "Prop Firm Challenge",
            "preset": "fundingpips",
            "target_country": "AE",
            "per_trade_risk_pct": 0.50,
        }

        try:
            resp = client.post("/api/accounts/onboard", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data.get("ok") is True
            assert data.get("status") == "success"
            assert data.get("account_id") == "77112233"
            assert "anti_ban_assigned" in data
            assert "risk_rules" in data

            # Plaintext password MUST NOT be exposed in response
            assert "SuperSecretPassword99!" not in json.dumps(data)
            assert "password" not in data.get("profile", {})
            # Password env isolated in environment
            assert os.environ.get("MT5_PASSWORD_77112233") == "SuperSecretPassword99!"
        finally:
            get_multi_account_manager().unregister_account("77112233")

    def test_flask_cockpit_onboarding_route(self):
        """Flask POST /api/accounts/onboard on MQ3 TRADING BOT/dashboard/app.py."""
        import importlib.util
        app_path = MQ3_ROOT / "dashboard" / "app.py"
        spec = importlib.util.spec_from_file_location("mq3_cockpit_app", app_path)
        mq3_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mq3_mod)
        flask_app = mq3_mod.app

        flask_app.config["TESTING"] = True
        try:
            with flask_app.test_client() as client:
                payload = {
                    "account_name": "Flask Cockpit FTMO Account",
                    "login_id": "88223344",
                    "broker_server": "FTMO-Server",
                    "password": "AnotherSecretKey456!",
                    "balance": 50000.0,
                    "account_type": "Prop Firm Funded",
                    "preset": "ftmo",
                    "target_country": "CZ",
                    "per_trade_risk_pct": 0.50,
                }
                resp = client.post("/api/accounts/onboard", json=payload)
                assert resp.status_code == 200
                data = resp.get_json()

                assert data.get("ok") is True
                assert data.get("status") == "success"
                assert data.get("account_id") == "88223344"
                assert data["risk_rules"]["freeze_ratio"] == 0.80

                # Plaintext password MUST NOT be in response
                assert "AnotherSecretKey456!" not in json.dumps(data)
                assert os.environ.get("MT5_PASSWORD_88223344") == "AnotherSecretKey456!"
        finally:
            get_multi_account_manager().unregister_account("88223344")

    def test_onboarding_input_validation_errors(self):
        """Rejects missing login_id and non-positive balances with HTTP 400."""
        from starlette.testclient import TestClient
        import dashboard

        client = TestClient(dashboard.app)

        # Missing login_id
        resp1 = client.post("/api/accounts/onboard", json={"balance": 50000.0})
        assert resp1.status_code == 400
        assert "login_id" in resp1.json()["message"]

        # Non-positive balance
        resp2 = client.post("/api/accounts/onboard", json={"login_id": "12345", "balance": -50.0})
        assert resp2.status_code == 400
        assert "positive" in resp2.json()["message"]


# =====================================================================
# 5. STRICT IDENTITY & INTEGRITY RULES AUDIT
# =====================================================================

class TestIdentityAndComplianceAudit:
    """Verifies that the codebase respects owner identity and has 0 unauthorized handles."""

    OWNED_FILES = [
        "trading/multi_account_manager.py",
        "MQ3 TRADING BOT/src/fleet_risk_manager.py",
        "MQ3 TRADING BOT/src/multi_account_auto_onboarder.py",
        "MQ3 TRADING BOT/src/prop_rules.py",
        "dashboard.py",
        "MQ3 TRADING BOT/dashboard/app.py",
    ]

    def test_zero_prohibited_handle_occurrences(self):
        """Absolute ZERO occurrences of prohibited handle anywhere in owned files."""
        forbidden = "".join(["a", "d", "e", "e", "l", "q", "u", "r", "e", "s", "h", "i", "9", "9"])
        for rel_path in self.OWNED_FILES:
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                text = full_path.read_text(encoding="utf-8", errors="ignore")
                assert forbidden not in text, f"PROHIBITED HANDLE FOUND in {rel_path}!"

    def test_owner_identity_present(self):
        """Verifies Master Muhammad Qureshi is recognized as owner."""
        mgr = get_multi_account_manager()
        summary = mgr.get_fleet_summary()
        assert "Master Muhammad Qureshi" in summary["owner"]
        assert "+923468053268" in summary["phone"]
