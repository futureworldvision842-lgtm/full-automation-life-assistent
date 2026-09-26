"""
tests/test_challenger2_remote_security_colibri_empirical.py
============================================================
EMPIRICAL CHALLENGER STRESS HARNESS (Teamwork Swarm R1-R7 Verification)
Focus Areas:
1. Sentinel Human Assistance Alert Modal (SOLVED, OTP_SUBMIT, KEY_SUBMIT, FREE_MODE, CANCEL; task pausing & state preservation)
2. Credential Isolation (Crypto API keys & MT5 passwords in os.environ exclusively; zero disk/response JSON leaks)
3. Colibri Bridge & Doctor Diagnostics (/api/repos/colibri/doctor and resource planner under extreme context lengths)
4. Thermal Governor & Workstation Stability (CPU throttle cap <=95% and ceiling <82°C strictly preserved)

Sovereign Master: Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Zero occurrences of prohibited identifiers anywhere.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from dashboard import app as dashboard_app
from core.human_intervention_gateway import (
    HumanInterventionGateway,
    HumanInterventionRequest,
    InterventionType,
    RequestStatus,
    get_human_intervention_gateway,
)
from core.self_healing_sentinel import get_self_healing_sentinel
from core.llm.colibri_bridge import get_colibri_bridge
from core.load_balancer import SystemLoadBalancer, load_balancer
from trading.multi_account_manager import get_multi_account_manager

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# =============================================================================
# 1. SENTINEL HUMAN ASSISTANCE ALERT MODAL & TASK PAUSING STRESS TESTS
# =============================================================================

class TestSentinelHumanAlertsEmpirical:
    """Empirical verification of alert creation, state holding, and all 5 resolution actions."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(dashboard_app, raise_server_exceptions=False)
        self.gw = get_human_intervention_gateway()

    def test_alert_creation_and_task_pausing(self):
        """Stress-tests alert creation across multiple intervention types and confirms task pausing."""
        # 1. Create CAPTCHA challenge alert
        res_cap = self.client.post("/api/alerts/create", json={
            "alert_type": "CAPTCHA_CHALLENGE",
            "title": "Cloudflare Turnstile Obstacle",
            "target_service": "FundingPips Portal",
            "reason": "Cloudflare interactive checkbox verification required",
            "action_blocked": "Daily risk limit sync",
            "portal_url": "https://app.fundingpips.com/login",
            "explanation_ur": "Sir, screen par Cloudflare checkbox solve karein."
        })
        assert res_cap.status_code == 200
        data_cap = res_cap.json()
        assert data_cap["ok"] is True
        req_id_cap = data_cap["alert"]["request_id"]
        assert req_id_cap.startswith("REQ-CAP-")

        # 2. Create 2FA/OTP alert
        res_otp = self.client.post("/api/alerts/create", json={
            "alert_type": "TWO_FACTOR_AUTH",
            "title": "FTMO Mobile Authenticator Code",
            "target_service": "FTMO Portal",
            "reason": "6-digit TOTP token required",
            "action_blocked": "EVALUATION_STEP_1 login",
            "account_username": "futureworldvision842@gmail.com",
            "code_destination": "Google Authenticator App"
        })
        assert res_otp.status_code == 200
        req_id_otp = res_otp.json()["alert"]["request_id"]
        assert req_id_otp.startswith("REQ-2FA-")

        # 3. Create Missing API Key alert
        res_key = self.client.post("/api/alerts/create", json={
            "alert_type": "MISSING_API_KEY",
            "title": "Glassnode On-Chain Institutional Key",
            "target_service": "Glassnode",
            "reason": "Premium whale wallet cluster telemetry",
            "action_blocked": "Macro whale tracking",
            "suggested_free_alternative": "Solscan RPC + DEX Screener Free Scraping"
        })
        assert res_key.status_code == 200
        req_id_key = res_key.json()["alert"]["request_id"]
        assert req_id_key.startswith("REQ-API-")

        # 4. Verify pending ledger reflects held alerts
        pending_resp = self.client.get("/api/alerts/pending")
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        assert pending_data["ok"] is True
        assert pending_data["count"] >= 3
        pending_ids = [a["request_id"] for a in pending_data["alerts"]]
        assert req_id_cap in pending_ids
        assert req_id_otp in pending_ids
        assert req_id_key in pending_ids

        # 5. Verify Sentinel diagnosis recognizes held tasks and reports HUMAN_ASSISTANCE_REQUIRED
        sentinel = get_self_healing_sentinel()
        diag = sentinel.diagnose_system()
        assert diag["ok"] is True
        assert diag["overall_state"] == "HUMAN_ASSISTANCE_REQUIRED"
        held_ids = [h["request_id"] for h in diag["pending_interventions"]]
        assert req_id_cap in held_ids

        # 6. Verify Sentinel auto-heal does NOT drop or forget held tasks
        heal_res = sentinel.auto_heal()
        assert heal_res["ok"] is True
        assert heal_res["held_count"] >= 3
        still_held_ids = [h["request_id"] for h in heal_res["held_tasks_awaiting_human"]]
        assert req_id_cap in still_held_ids

    def test_resolution_all_five_actions(self):
        """Validates all 5 resolution actions: SOLVED, OTP_SUBMIT, KEY_SUBMIT, FREE_MODE, CANCEL."""
        created_ids = {}

        # 1. Alert for SOLVED (CAPTCHA)
        r_cap = self.client.post("/api/alerts/create", json={
            "alert_type": "CAPTCHA_CHALLENGE",
            "title": "Cloudflare Test for SOLVED",
            "target_service": "ServiceSolved",
            "reason": "Cloudflare check",
            "action_blocked": "Sync"
        })
        created_ids["SOLVED"] = r_cap.json()["alert"]["request_id"]

        # 2. Alert for OTP_SUBMIT (2FA)
        r_otp = self.client.post("/api/alerts/create", json={
            "alert_type": "TWO_FACTOR_AUTH",
            "title": "OTP Test for OTP_SUBMIT",
            "target_service": "ServiceOTP",
            "reason": "OTP Needed",
            "action_blocked": "Login"
        })
        created_ids["OTP_SUBMIT"] = r_otp.json()["alert"]["request_id"]

        # 3. Alert for KEY_SUBMIT (API Key)
        r_key = self.client.post("/api/alerts/create", json={
            "alert_type": "MISSING_API_KEY",
            "title": "Key Test for KEY_SUBMIT",
            "target_service": "ServiceKey",
            "reason": "API Key needed",
            "action_blocked": "Scrape"
        })
        created_ids["KEY_SUBMIT"] = r_key.json()["alert"]["request_id"]

        # 4. Alert for FREE_MODE (API Key fallback)
        r_free = self.client.post("/api/alerts/create", json={
            "alert_type": "MISSING_API_KEY",
            "title": "Free Mode Test",
            "target_service": "ServiceFree",
            "reason": "Paid key missing",
            "action_blocked": "Fetch",
            "suggested_free_alternative": "Public REST Fallback"
        })
        created_ids["FREE_MODE"] = r_free.json()["alert"]["request_id"]

        # 5. Alert for CANCEL (Generic Alert)
        r_cancel = self.client.post("/api/alerts/create", json={
            "alert_type": "CAPTCHA_CHALLENGE",
            "title": "Cancel Alert Test",
            "target_service": "ServiceCancel",
            "reason": "Test cancellation",
            "action_blocked": "Blocked task"
        })
        created_ids["CANCEL"] = r_cancel.json()["alert"]["request_id"]

        # Action 1: SOLVED
        r1 = self.client.post("/api/alerts/resolve", json={
            "request_id": created_ids["SOLVED"],
            "action": "SOLVED",
            "value": "Operator completed human checkbox on screen"
        })
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["ok"] is True
        assert d1["status"] == RequestStatus.RESOLVED.value
        assert d1["alert"]["resolution_details"]["action"] == "SOLVED"

        # Action 2: OTP_SUBMIT
        r2 = self.client.post("/api/alerts/resolve", json={
            "request_id": created_ids["OTP_SUBMIT"],
            "action": "OTP_SUBMIT",
            "value": "842910"
        })
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["ok"] is True
        assert d2["status"] == RequestStatus.RESOLVED.value
        assert d2["alert"]["resolution_details"]["otp"] == "842910"

        # Action 3: KEY_SUBMIT
        r3 = self.client.post("/api/alerts/resolve", json={
            "request_id": created_ids["KEY_SUBMIT"],
            "action": "KEY_SUBMIT",
            "value": "sk-ant-challenger-stress-key-12345"
        })
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["ok"] is True
        assert d3["status"] == RequestStatus.RESOLVED.value
        assert d3["alert"]["resolution_details"]["action"] == "KEY_SUBMIT"

        # Action 4: FREE_MODE
        r4 = self.client.post("/api/alerts/resolve", json={
            "request_id": created_ids["FREE_MODE"],
            "action": "FREE_MODE"
        })
        assert r4.status_code == 200
        d4 = r4.json()
        assert d4["ok"] is True
        assert d4["status"] == RequestStatus.FALLBACK_FREE.value
        assert d4["alert"]["resolution_details"]["action"] == "FREE_MODE"

        # Action 5: CANCEL
        r5 = self.client.post("/api/alerts/resolve", json={
            "request_id": created_ids["CANCEL"],
            "action": "CANCEL"
        })
        assert r5.status_code == 200
        d5 = r5.json()
        assert d5["ok"] is True
        assert d5["status"] == RequestStatus.CANCELLED.value
        assert d5["alert"]["resolution_details"]["action"] == "CANCEL"

        # Verify history captures all 5 resolved requests
        hist_resp = self.client.get("/api/alerts/history?limit=20")
        assert hist_resp.status_code == 200
        hist_ids = [h["request_id"] for h in hist_resp.json()["history"]]
        for act, rid in created_ids.items():
            assert rid in hist_ids, f"Resolved request for {act} ({rid}) missing from history!"

    def test_state_preservation_across_reloads(self):
        """Verifies that gateway preserves state and resolution details when reloading from disk."""
        # Create and resolve an alert
        res = self.client.post("/api/alerts/create", json={
            "alert_type": "CAPTCHA_CHALLENGE",
            "title": "Persistence Test Alert",
            "target_service": "PersistenceService",
            "reason": "Testing ledger persistence on disk",
            "action_blocked": "Disk persistence test"
        })
        req_id = res.json()["alert"]["request_id"]

        self.client.post("/api/alerts/resolve", json={
            "request_id": req_id,
            "action": "SOLVED",
            "value": "Persistence confirmed"
        })

        # Re-initialize a fresh gateway instance to read back from disk
        fresh_gw = HumanInterventionGateway(owner_phone="+923468053268")
        with fresh_gw._lock:
            assert req_id in fresh_gw._requests
            loaded_req = fresh_gw._requests[req_id]
            assert loaded_req.status == RequestStatus.RESOLVED
            assert loaded_req.resolution_details is not None
            assert loaded_req.resolution_details["action"] == "SOLVED"
            assert loaded_req.target_service == "PersistenceService"

    def test_adversarial_critical_confirmation_unhandled_defect(self):
        """Adversarial Test: Proves CRITICAL_CONFIRMATION is handled cleanly with 200 status."""
        res = self.client.post("/api/alerts/create", json={
            "alert_type": "CRITICAL_CONFIRMATION",
            "title": "Risk Limit Override Confirmation",
            "target_service": "RiskKernel",
            "reason": "Exceeding daily trade count",
            "action_blocked": "Trade dispatch"
        })
        assert res.status_code == 200, f"Expected 200 with properly implemented gateway method, got {res.status_code}"
        assert res.json()["ok"] is True

    def test_adversarial_resolve_nonexistent_when_no_pending_defect(self):
        """Adversarial Test: Proves resolving non-existent ID with 0 pending requests returns 404 Not Found cleanly without 500."""
        # Temporarily mark all pending as resolved so pending list is empty
        gw = get_human_intervention_gateway()
        with gw._lock:
            for r in gw._requests.values():
                r.status = RequestStatus.RESOLVED

        resp = self.client.post("/api/alerts/resolve", json={
            "request_id": "DEFINITELY_NON_EXISTENT_ID_99999",
            "action": "SOLVED"
        })
        assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


# =============================================================================
# 2. CREDENTIAL ISOLATION & ZERO PLAINTEXT DISK LEAK TESTS
# =============================================================================

class TestCredentialIsolationEmpirical:
    """Verifies simulated Crypto API keys and MT5 passwords remain exclusively in os.environ."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(dashboard_app, raise_server_exceptions=False)
        self.mgr = get_multi_account_manager()

    def test_crypto_api_credential_isolation(self):
        """Attempts onboarding with simulated Crypto API keys; verifies os.environ isolation & zero disk leaks."""
        account_id = "challenger_crypto_vault_777"
        simulated_api_key = "CRYPTO_KEY_EMPIRICAL_CHALLENGER_9999_SECRET"
        simulated_api_secret = "CRYPTO_SECRET_HMAC_SHA256_HEX_HASH_8888"
        simulated_passphrase = "CRYPTO_PASSPHRASE_CHALLENGER_VAULT_7777"

        payload = {
            "account_id": account_id,
            "account_name": "Empirical Binance Institutional API",
            "exchange_platform": "binance",
            "api_key": simulated_api_key,
            "api_secret": simulated_api_secret,
            "passphrase": simulated_passphrase,
            "balance": 200000.0,
            "preset": "binance"
        }

        resp = self.client.post("/api/accounts/onboard", json=payload)
        assert resp.status_code == 200
        res_json = resp.json()
        assert res_json["ok"] is True
        assert res_json["status"] == "success"

        # 1. Assert plaintext secrets NEVER appear in response JSON or text
        response_text = resp.text
        assert simulated_api_key not in response_text
        assert simulated_api_secret not in response_text
        assert simulated_passphrase not in response_text

        # 2. Assert secrets exist in os.environ
        expected_key_env = f"BINANCE_API_KEY_{account_id}"
        expected_secret_env = f"BINANCE_API_SECRET_{account_id}"
        expected_pass_env = f"BINANCE_PASSPHRASE_{account_id}"

        assert os.environ.get(expected_key_env) == simulated_api_key
        assert os.environ.get(expected_secret_env) == simulated_api_secret
        assert os.environ.get(expected_pass_env) == simulated_passphrase

        # 3. Assert fleet config JSON on disk DOES NOT contain plaintext secrets
        fleet_file = PROJECT_ROOT / "config" / "multi_account_fleet.json"
        if fleet_file.exists():
            disk_content = fleet_file.read_text(encoding="utf-8")
            assert simulated_api_key not in disk_content
            assert simulated_api_secret not in disk_content
            assert simulated_passphrase not in disk_content
            assert expected_key_env in disk_content or f"{account_id}" in disk_content

        # Cleanup
        self.mgr.unregister_account(account_id)
        os.environ.pop(expected_key_env, None)
        os.environ.pop(expected_secret_env, None)
        os.environ.pop(expected_pass_env, None)

    def test_mt5_password_isolation(self):
        """Attempts onboarding with simulated MT5 password; verifies os.environ isolation & zero disk leaks."""
        account_id = "challenger_mt5_acc_888"
        simulated_password = "MT5_StrongP@ssw0rd!#$2026_Empirical"

        payload = {
            "login_id": account_id,
            "account_name": "Empirical FundingPips MT5",
            "broker_server": "FundingPips-Server",
            "password": simulated_password,
            "balance": 100000.0,
            "preset": "FundingPips"
        }

        resp = self.client.post("/api/accounts/onboard", json=payload)
        assert resp.status_code == 200
        res_json = resp.json()
        assert res_json["ok"] is True

        # 1. Plaintext password NEVER in response text
        assert simulated_password not in resp.text

        # 2. Password strictly isolated in os.environ
        expected_pwd_env = f"MT5_PASSWORD_{account_id}"
        assert os.environ.get(expected_pwd_env) == simulated_password

        # 3. Plaintext password NEVER on disk
        fleet_file = PROJECT_ROOT / "config" / "multi_account_fleet.json"
        if fleet_file.exists():
            disk_content = fleet_file.read_text(encoding="utf-8")
            assert simulated_password not in disk_content

        # Cleanup
        self.mgr.unregister_account(account_id)
        os.environ.pop(expected_pwd_env, None)


# =============================================================================
# 3. COLIBRI BRIDGE & DOCTOR DIAGNOSTICS STRESS TESTS
# =============================================================================

class TestColibriDiagnosticsEmpirical:
    """Empirical verification of Colibri MoE doctor diagnostics and resource planning under extreme contexts."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(dashboard_app, raise_server_exceptions=False)
        self.bridge = get_colibri_bridge()

    def test_colibri_doctor_endpoint(self):
        """Verifies GET /api/repos/colibri/doctor confirms operational health."""
        resp = self.client.get("/api/repos/colibri/doctor")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["engine_operational"] is True
        assert "colibri v" in data["raw_info"] or "tiny engine" in data["raw_info"]

    def test_colibri_status_endpoint(self):
        """Verifies GET /api/repos/colibri/status returns hardware vitals and model support."""
        resp = self.client.get("/api/repos/colibri/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        colibri = data["colibri"]
        assert colibri["engine"] == "Colibrì MoE Hierarchical Streaming Engine"
        assert "GLM-5.2 (744B)" in colibri["supported_model_families"]
        assert "DeepSeek V4 Flash" in colibri["supported_model_families"]
        assert "Kimi K3 (2.8T)" in colibri["supported_model_families"]
        assert "workstation_hardware" in colibri
        hw = colibri["workstation_hardware"]
        assert hw["total_ram_gb"] > 0
        assert hw["recommended_ram_budget_gb"] >= 8

    def test_resource_planner_scaling_large_context_lengths(self):
        """Stress-tests /api/repos/colibri/plan across extreme context lengths (up to 1,000,000 tokens)."""
        test_contexts = [
            2048,       # standard short
            8192,       # standard medium
            32768,      # long context
            65536,      # ultra-long context
            128000,     # frontier context (GLM-5.2 / DeepSeek)
            1000000,    # 1M token mega context stress
        ]

        for ctx in test_contexts:
            payload = {
                "model_name": "GLM-5.2 (744B)",
                "ram_budget_gb": 16,
                "ctx_len": ctx
            }
            resp = self.client.post("/api/repos/colibri/plan", json=payload)
            assert resp.status_code == 200
            plan = resp.json()
            assert plan["ok"] is True
            assert plan["context_length"] == ctx
            assert plan["ram_budget_gb"] == 16
            assert plan["active_experts_in_ram"] >= 4
            assert plan["nvme_streaming_rate_mbs"] > 0
            assert "thermal governor will cap CPU throttle at 95%" in plan["recommendation"]


# =============================================================================
# 4. THERMAL GOVERNOR & WORKSTATION STABILITY TESTS
# =============================================================================

class TestThermalGovernorWorkstationStabilityEmpirical:
    """Empirical verification of 95% CPU throttle cap and thermal ceiling <82°C."""

    def test_live_powercfg_throttle_cap_query(self):
        """Verifies that live host PROCTHROTTLEMAX is capped at <= 95%."""
        if sys.platform != "win32":
            pytest.skip("Windows only test")
        res = load_balancer.query_processor_throttle_cap()
        assert res["ok"] is True
        assert res["ac_val"] <= 95, f"Expected AC throttle cap <= 95%, found {res['ac_val']}%"
        assert res["dc_val"] <= 95, f"Expected DC throttle cap <= 95%, found {res['dc_val']}%"
        assert res["is_capped_95"] is True

    def test_ensure_processor_throttle_cap_enforcement(self):
        """Enforces 95% throttle cap via powercfg and verifies contract."""
        res = load_balancer.ensure_processor_throttle_cap(95)
        assert res["ok"] is True
        assert res["applied_ac"] == 95
        assert res["applied_dc"] == 95
        assert res["cap_percent"] == 95

    def test_thermal_ceiling_invariant(self):
        """Verifies target thermal ceiling is strictly 82.0°C and reports status."""
        vitals = load_balancer.get_thermal_and_vitals()
        assert vitals["target_max_temp_c"] == 82.0
        assert isinstance(vitals["temp_c"], (int, float))
        assert vitals["status"] in {"NORMAL_COOL", "ELEVATED", "CRITICAL_HOT"}

    def test_simulated_thermal_runaway_triggers_balancing(self):
        """Simulates CPU temperature hitting 84.5°C and verifies immediate process balancing."""
        gov = SystemLoadBalancer(target_max_temp_c=82.0)
        gov._last_auto_balance_time = 0.0

        with patch.object(gov, "_read_acpi_temp", return_value=84.5), \
             patch.object(gov, "_read_gpu_temp", return_value=60.0), \
             patch.object(gov, "balance_all_jarvis_processes", return_value={"ok": True, "demoted_count": 5}) as mock_bal:
            vitals = gov.get_thermal_and_vitals()
            assert vitals["temp_c"] == 84.5
            assert vitals["is_hot"] is True
            assert vitals["status"] == "ELEVATED"
            assert vitals["throttled"] is True
            mock_bal.assert_called_once()

    def test_sentinel_reports_thermal_and_throttle_safe(self):
        """Verifies SelfHealingSentinel reports thermal safety (<82°C) and active 95% cap."""
        sentinel = get_self_healing_sentinel()
        diag = sentinel.diagnose_system()
        assert diag["ok"] is True
        hw = diag["hardware"]
        assert hw["thermal_safe"] is True
        assert hw["thermal_celsius"] < 82.0
        assert "95%" in hw["throttle_cap"]
