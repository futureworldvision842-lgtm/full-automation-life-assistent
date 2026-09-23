"""
tests/test_adversarial_m1_1_webhook.py — Adversarial Stress Harness for TradingView Inbound Webhook
====================================================================================================
Adversarially tests and stress-tests POST /api/tradingview/webhook in dashboard.py:
1. Authentication bypass attempts: spoofed headers, empty/whitespace passphrases, SQL/injection payloads.
2. Risk breaches: 0.7501%, 0.76%, 1.0%, 5.0% risk; $750.01, $751, $10,000 dollar risk; implicit lot risk.
3. Inverted and pathological geometry: SL > Price for BUY, TP > Price for SELL, negative/zero prices.
4. Macro news blackout protection and minimum 1:2.5 Risk:Reward gating.
5. Malformed/fuzzed payloads and >64KB flood protection.
6. Anti-overtrading daily trade ceiling (max 3 trades/day).
7. High concurrency & race condition stress testing (burst requests).

Strict Identity & Constraints:
- Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com).
- Fail-closed deterministic risk (<= 0.75%, $750.00 cap on Account #40000294403).
"""

import os
import sys
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
MQ3_SRC = os.path.join(BASE, "MQ3 TRADING BOT", "src")
if os.path.exists(MQ3_SRC) and MQ3_SRC not in sys.path:
    sys.path.insert(0, MQ3_SRC)

from starlette.testclient import TestClient
import dashboard
from trading.risk_kernel.admission_kernel import get_risk_kernel, DeterministicRiskKernel
from platform_runtime import internal_command_token


class BaseWebhookTest(unittest.TestCase):
    """Base setup for Webhook adversarial testing."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(dashboard.app)
        cls.valid_passphrase = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "JARVIS_TV_SECRET_2026")
        cls.valid_headers = {
            "Content-Type": "application/json",
            "X-TradingView-Passphrase": cls.valid_passphrase
        }

    def setUp(self):
        # Reset kernel trade count before each individual test to guarantee isolation
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

    def _make_valid_order(self, **kwargs):
        """Helper to create a fully compliant trade payload."""
        base = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "price": 2735.50,
            "sl": 2725.50,          # 10 pts risk
            "tp": 2760.50,          # 25 pts reward (RR = 2.5)
            "proposed_risk_pct": 0.75,
            "proposed_risk_usd": 750.00,
            "rr_ratio": 2.5,
            "confluence_score": 92.5,
            "strategy": "Institutional_SMC_LiquiditySweep",
            "account_id": "40000294403",
            "balance": 100000.0,
            "news_lockout_active": False
        }
        base.update(kwargs)
        return base


# =============================================================================
# 1. AUTHENTICATION & HEADER SPOOFING ATTACKS
# =============================================================================
class TestWebhookAuthBypass(BaseWebhookTest):
    """Adversarially probes authentication gating, header spoofing, and injections."""

    def test_missing_passphrase_returns_401(self):
        """Request with zero auth headers must be rejected with 401 Unauthorized."""
        payload = self._make_valid_order()
        resp = self.client.post("/api/tradingview/webhook", json=payload)
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_UNAUTHORIZED")
        self.assertEqual(data.get("error"), "missing_passphrase")

    def test_empty_passphrase_header_returns_401(self):
        """Empty passphrase header must be rejected with 401."""
        payload = self._make_valid_order()
        resp = self.client.post(
            "/api/tradingview/webhook",
            json=payload,
            headers={"Content-Type": "application/json", "X-TradingView-Passphrase": ""}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "missing_passphrase")

    def test_whitespace_passphrase_header_returns_401(self):
        """Whitespace-only passphrase header must be stripped and rejected with 401."""
        payload = self._make_valid_order()
        for ws in ["   ", "\t", "\n", "\r\n", "  \t\n  "]:
            resp = self.client.post(
                "/api/tradingview/webhook",
                json=payload,
                headers={"Content-Type": "application/json", "X-TradingView-Passphrase": ws}
            )
            self.assertEqual(resp.status_code, 401, f"Failed for whitespace: {repr(ws)}")
            self.assertEqual(resp.json().get("error"), "missing_passphrase")

    def test_invalid_passphrase_header_returns_403(self):
        """Incorrect passphrase header must be rejected with 403 Forbidden."""
        payload = self._make_valid_order()
        resp = self.client.post(
            "/api/tradingview/webhook",
            json=payload,
            headers={"Content-Type": "application/json", "X-TradingView-Passphrase": "WRONG_SECRET_KEY"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_FORBIDDEN")
        self.assertEqual(data.get("error"), "invalid_passphrase")

    def test_spoofed_network_headers_without_auth_rejected_401(self):
        """Spoofing network headers (X-Forwarded-For, X-Real-IP, Host) cannot bypass auth."""
        payload = self._make_valid_order()
        spoofed_headers_list = [
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Forwarded-For": "localhost"},
            {"X-Real-IP": "127.0.0.1"},
            {"X-Real-IP": "::1"},
            {"Host": "127.0.0.1:8770"},
            {"Host": "localhost:8770"},
            {"Origin": "http://127.0.0.1:8770"},
            {"Referer": "http://127.0.0.1:8770/dashboard"},
            {"X-Client-IP": "127.0.0.1"},
            {"CF-Connecting-IP": "127.0.0.1"}
        ]
        for headers in spoofed_headers_list:
            headers["Content-Type"] = "application/json"
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 401, f"Spoofed headers bypassed auth: {headers}")

    def test_spoofed_internal_token_rejected_403(self):
        """Invalid or spoofed internal tokens must not bypass auth."""
        payload = self._make_valid_order()
        for bad_token in ["bad_token", "12345", "None", "false", "root", "admin", "null"]:
            headers = {
                "Content-Type": "application/json",
                "X-Jarvis-Internal-Token": bad_token
            }
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=headers)
            # Without valid passphrase and with invalid internal token -> rejected
            self.assertIn(resp.status_code, [401, 403], f"Bad internal token accepted: {bad_token}")

    def test_sql_injection_in_passphrase_header_rejected_403(self):
        """SQL injection payloads in passphrase header must be safely rejected with 403."""
        payload = self._make_valid_order()
        sqli_payloads = [
            "' OR '1'='1",
            "' OR 1=1 --",
            "admin' --",
            "'; DROP TABLE users; --",
            "' UNION SELECT 1, 'admin', '2026'--",
            "\" OR \"\"=\"",
            "1' or '1' = '1' /*"
        ]
        for sqli in sqli_payloads:
            headers = {"Content-Type": "application/json", "X-TradingView-Passphrase": sqli}
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 403, f"SQLi payload in passphrase not rejected: {sqli}")
            self.assertEqual(resp.json().get("decision"), "REJECTED_FORBIDDEN")

    def test_command_injection_in_passphrase_header_rejected_403(self):
        """Command injection / shell characters in passphrase header must be rejected with 403."""
        payload = self._make_valid_order()
        cmd_payloads = [
            "; whoami",
            "| calc.exe",
            "& ping -n 1 127.0.0.1 &",
            "$(reboot)",
            "`id`",
            "; rm -rf / ;",
            "\n/bin/sh\n"
        ]
        for cmd_inj in cmd_payloads:
            headers = {"Content-Type": "application/json", "X-TradingView-Passphrase": cmd_inj}
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=headers)
            self.assertEqual(resp.status_code, 403, f"Command injection in passphrase not rejected: {cmd_inj}")

    def test_body_passphrase_fallback_validation(self):
        """Passphrase supplied in JSON body must be strictly validated."""
        # Empty body passphrase -> 401
        resp = self.client.post("/api/tradingview/webhook", json=self._make_valid_order(passphrase=""))
        self.assertEqual(resp.status_code, 401)

        # Whitespace body passphrase -> 401
        resp = self.client.post("/api/tradingview/webhook", json=self._make_valid_order(passphrase="   "))
        self.assertEqual(resp.status_code, 401)

        # Wrong body passphrase -> 403
        resp = self.client.post("/api/tradingview/webhook", json=self._make_valid_order(passphrase="incorrect_pwd"))
        self.assertEqual(resp.status_code, 403)

        # SQLi in body passphrase -> 403
        resp = self.client.post("/api/tradingview/webhook", json=self._make_valid_order(passphrase="' OR '1'='1"))
        self.assertEqual(resp.status_code, 403)

    @patch("core.command_gateway.execute_command")
    def test_valid_internal_token_loopback_bypass(self, mock_dispatch):
        """Valid internal HMAC token grants loopback access without external passphrase."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        headers = {
            "Content-Type": "application/json",
            "X-Jarvis-Internal-Token": internal_command_token()
        }
        resp = self.client.post("/api/tradingview/webhook", json=self._make_valid_order(), headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))


# =============================================================================
# 2. RISK SIZING & BOUNDARY BREACH ATTACKS (0.75% / $750.00 CAP)
# =============================================================================
class TestWebhookRiskBreach(BaseWebhookTest):
    """Adversarially tests risk boundaries: 0.75% risk ceiling and $750.00 dollar cap."""

    @patch("core.command_gateway.execute_command")
    def test_risk_percentage_exact_ceiling_0_75_allowed_200(self, mock_dispatch):
        """Risk percentage at exactly 0.75% ceiling must be permitted."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        payload = self._make_valid_order(proposed_risk_pct=0.75, proposed_risk_usd=750.00)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        self.assertEqual(resp.json().get("decision"), "ADMITTED_PROPOSAL")

    def test_risk_percentage_epsilon_breach_0_7501_rejected_422(self):
        """Risk percentage at 0.7501% (epsilon breach) must be deterministically rejected with 422."""
        payload = self._make_valid_order(proposed_risk_pct=0.7501)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max allowed" in b for b in data.get("blockers", [])))

    def test_risk_percentage_breach_0_76_rejected_422(self):
        """Risk percentage at 0.76% must be deterministically rejected with 422."""
        payload = self._make_valid_order(proposed_risk_pct=0.76)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max allowed" in b for b in data.get("blockers", [])))

    def test_risk_percentage_extreme_breaches_rejected_422(self):
        """Risk percentages of 1.0%, 5.0%, and 100.0% must all be rejected with 422."""
        for excessive_pct in [1.0, 2.5, 5.0, 10.0, 50.0, 100.0]:
            payload = self._make_valid_order(proposed_risk_pct=excessive_pct)
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
            self.assertEqual(resp.status_code, 422, f"Failed to reject risk_pct={excessive_pct}")
            data = resp.json()
            self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
            self.assertTrue(any("exceeds max allowed" in b for b in data.get("blockers", [])))

    def test_risk_pct_alternative_field_breach_rejected_422(self):
        """Using alternative field name 'risk_pct' with 0.76% must also be rejected with 422."""
        payload = self._make_valid_order()
        del payload["proposed_risk_pct"]
        payload["risk_pct"] = 0.76
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max allowed" in b for b in data.get("blockers", [])))

    @patch("core.command_gateway.execute_command")
    def test_dollar_risk_exact_cap_750_allowed_200(self, mock_dispatch):
        """Dollar risk of exactly $750.00 must be permitted on $100k account."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        payload = self._make_valid_order(proposed_risk_usd=750.00, proposed_risk_pct=0.75)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))

    def test_dollar_risk_epsilon_breach_750_01_rejected_422(self):
        """Dollar risk of $750.01 (1 cent above cap) must be rejected with 422."""
        payload = self._make_valid_order(proposed_risk_usd=750.01, proposed_risk_pct=0.75)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("$750.00" in b for b in data.get("blockers", [])))

    def test_dollar_risk_breach_751_rejected_422(self):
        """Dollar risk of $751.00 must be deterministically rejected with 422."""
        payload = self._make_valid_order(proposed_risk_usd=751.00, proposed_risk_pct=0.75)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("$751.00" in b or "$750.00" in b for b in data.get("blockers", [])))

    def test_dollar_risk_extreme_breach_10000_rejected_422(self):
        """Dollar risk of $10,000.00 must be rejected with 422."""
        payload = self._make_valid_order(proposed_risk_usd=10000.00, proposed_risk_pct=0.75)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_BLOCKED")

    def test_implicit_dollar_risk_breach_gold_rejected_422(self):
        """When proposed_risk_usd is omitted, calculated lot * sl_dist > $750 must trigger Gate 2 rejection."""
        # Gold: Price=2700, SL=2600 (sl_dist = 100 pts), TP=2950 (dist = 250 pts, RR=2.5)
        # Client explicitly sends lots=0.10 (asset ceiling).
        # Dollar risk = 0.10 * 100 * 100 = $1,000.00 > $750 cap!
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "price": 2700.0,
            "sl": 2600.0,
            "tp": 2950.0,
            "lots": 0.10,
            "account_id": "40000294403",
            "balance": 100000.0
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertGreater(data.get("risk_usd", 0), 750.0)

    def test_pipdance_account_risk_cap_breach_rejected_422(self):
        """Pipdance account #5054542 ($1,000 balance) has $7.50 cap; $10 risk must be rejected with 422."""
        payload = self._make_valid_order(
            account_id="5054542",
            balance=1000.0,
            proposed_risk_usd=10.00,  # VIOLATION: > $7.50 cap
            proposed_risk_pct=0.75
        )
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")

    def test_nan_risk_pct_admission_kernel_bypass(self):
        """EMPIRICAL FINDING: IEEE 754 NaN bypasses Gate 2 sizing cap in DeterministicRiskKernel."""
        kernel = get_risk_kernel()
        adm = kernel.evaluate_admission(
            symbol="XAUUSD",
            confluence_score=92.5,
            proposed_risk_pct=float("nan"),
            proposed_risk_usd=float("nan"),
            rr_ratio=2.5
        )
        # NaN comparisons are guarded; NaN must be deterministically rejected
        self.assertFalse(adm.get("allowed"), "NaN must be rejected by DeterministicRiskKernel")
        self.assertTrue(any("NaN" in b for b in adm.get("blockers", [])))


# =============================================================================
# 3. INVERTED & PATHOLOGICAL GEOMETRY ATTACKS
# =============================================================================
class TestWebhookInvertedGeometry(BaseWebhookTest):
    """Adversarially tests order price geometry (SL < Price < TP for BUY; TP < Price < SL for SELL)."""

    def test_buy_sl_above_price_rejected_422(self):
        """BUY order with Stop Loss placed above Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="BUY", price=2735.0, sl=2740.0, tp=2760.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_INVERTED_GEOMETRY")
        self.assertIn("Inverted BUY geometry", data.get("error", ""))

    def test_buy_sl_equal_price_rejected_422(self):
        """BUY order with Stop Loss equal to Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="BUY", price=2735.0, sl=2735.0, tp=2760.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_buy_tp_below_price_rejected_422(self):
        """BUY order with Take Profit below Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="BUY", price=2735.0, sl=2720.0, tp=2730.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_buy_tp_equal_price_rejected_422(self):
        """BUY order with Take Profit equal to Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="BUY", price=2735.0, sl=2720.0, tp=2735.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_sell_sl_below_price_rejected_422(self):
        """SELL order with Stop Loss below Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="SELL", price=2735.0, sl=2725.0, tp=2710.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_INVERTED_GEOMETRY")
        self.assertIn("Inverted SELL geometry", data.get("error", ""))

    def test_sell_sl_equal_price_rejected_422(self):
        """SELL order with Stop Loss equal to Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="SELL", price=2735.0, sl=2735.0, tp=2710.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_sell_tp_above_price_rejected_422(self):
        """SELL order with Take Profit above Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="SELL", price=2735.0, sl=2745.0, tp=2750.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_sell_tp_equal_price_rejected_422(self):
        """SELL order with Take Profit equal to Entry Price must be rejected with 422."""
        payload = self._make_valid_order(action="SELL", price=2735.0, sl=2745.0, tp=2735.0)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json().get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_negative_or_zero_prices_rejected_400(self):
        """Non-positive prices (zero or negative) must return 400 Bad Request."""
        pathological_cases = [
            {"price": 0.0, "sl": 2720.0, "tp": 2750.0},
            {"price": -2735.0, "sl": 2720.0, "tp": 2750.0},
            {"price": 2735.0, "sl": 0.0, "tp": 2750.0},
            {"price": 2735.0, "sl": -2720.0, "tp": 2750.0},
            {"price": 2735.0, "sl": 2720.0, "tp": 0.0},
            {"price": 2735.0, "sl": 2720.0, "tp": -2750.0},
        ]
        for case in pathological_cases:
            payload = self._make_valid_order(**case)
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
            self.assertEqual(resp.status_code, 400, f"Allowed pathological price case: {case}")
            self.assertEqual(resp.json().get("decision"), "REJECTED_BAD_REQUEST")


# =============================================================================
# 4. MACRO NEWS BLACKOUT & RISK:REWARD GATING
# =============================================================================
class TestWebhookNewsAndRR(BaseWebhookTest):
    """Tests 15-minute high-impact economic news circuit breaker and minimum 1:2.5 RR."""

    def test_explicit_news_lockout_active_rejected_422(self):
        """Explicit news_lockout_active=True must be deterministically rejected with 422."""
        payload = self._make_valid_order(news_lockout_active=True)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("News Lockout Active" in b for b in data.get("blockers", [])))

    def test_simulated_economic_news_blackout_service_rejected_422(self):
        """When portfolio_risk_service indicates news blackout, order must be rejected with 422."""
        try:
            import portfolio_risk_service
            with patch.object(portfolio_risk_service.portfolio_risk_service, "evaluate_economic_news_blackout") as mock_news:
                mock_news.return_value = (True, "US FOMC Rate Decision High Impact Blackout", 14.5)
                payload = self._make_valid_order()
                del payload["news_lockout_active"]  # Allow service fallback to evaluate
                resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
                self.assertEqual(resp.status_code, 422)
                data = resp.json()
                self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
                self.assertTrue(any("News Lockout Active" in b for b in data.get("blockers", [])))
        except ImportError:
            self.skipTest("portfolio_risk_service not importable directly")

    def test_substandard_rr_ratio_rejected_422(self):
        """Risk-to-Reward ratio < 1:2.5 (e.g. 1:1.5) must be rejected with 422."""
        # Risk: 2735.0 - 2725.0 = 10 pts. Reward: 2750.0 - 2735.0 = 15 pts. RR = 1.5 < 2.5
        payload = self._make_valid_order(
            price=2735.0,
            sl=2725.0,
            tp=2750.0,
            rr_ratio=1.5
        )
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("minimum 1:2.5" in b for b in data.get("blockers", [])))

    def test_borderline_rr_ratio_2_49_rejected_422(self):
        """Risk-to-Reward ratio of 2.49 (just below 2.5) must be rejected with 422."""
        payload = self._make_valid_order(rr_ratio=2.49)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        self.assertTrue(any("minimum 1:2.5" in b for b in resp.json().get("blockers", [])))

    @patch("core.command_gateway.execute_command")
    def test_compliant_rr_ratio_2_50_allowed_200(self, mock_dispatch):
        """Risk-to-Reward ratio of exactly 2.50 must be permitted."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        payload = self._make_valid_order(rr_ratio=2.50)
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))


# =============================================================================
# 5. INJECTION ATTACKS IN TICKER AND OTHER FIELDS
# =============================================================================
class TestWebhookPayloadInjections(BaseWebhookTest):
    """Adversarially tests injection attacks within JSON payload fields."""

    def test_invalid_action_rejected_400(self):
        """Action that is not BUY or SELL (e.g. injection, HOLD, CLOSE) must return 400."""
        injected_actions = [
            "HOLD", "CLOSE", "CANCEL",
            "BUY; rm -rf /",
            "SELL' OR '1'='1",
            "DROP TABLE",
            "<script>alert(1)</script>",
            ""
        ]
        for act in injected_actions:
            payload = self._make_valid_order(action=act)
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
            self.assertEqual(resp.status_code, 400, f"Failed to reject invalid action: {act}")
            self.assertEqual(resp.json().get("decision"), "REJECTED_BAD_REQUEST")

    def test_missing_ticker_rejected_400(self):
        """Payload without ticker must be rejected with 400."""
        payload = self._make_valid_order()
        del payload["ticker"]
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("decision"), "REJECTED_BAD_REQUEST")

    def test_non_numeric_price_rejected_400(self):
        """Non-numeric string values for price/sl/tp must return 400 Bad Request."""
        payload = self._make_valid_order(price="not_a_number")
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("decision"), "REJECTED_BAD_REQUEST")

    def test_oversized_payload_flood_protection_rejected_400(self):
        """Payload exceeding 64KB must be rejected with 400 Bad Request."""
        giant_payload = self._make_valid_order(junk_blob="X" * 70000)
        resp = self.client.post("/api/tradingview/webhook", json=giant_payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "payload_too_large")

    def test_malformed_json_bytes_rejected_400(self):
        """Unparseable raw bytes must return 400 Bad Request."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            content=b"{invalid: json, not: quoted",
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "malformed_json")

    def test_json_array_rejected_400(self):
        """JSON Array instead of object must return 400 Bad Request."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            json=[{"ticker": "XAUUSD"}],
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invalid_json_format")


# =============================================================================
# 6. ANTI-OVERTRADING GOVERNOR (MAX 3 TRADES/DAY)
# =============================================================================
class TestWebhookAntiOvertrading(BaseWebhookTest):
    """Tests Gate 3: strict anti-overtrading daily cap (maximum 3 trades admitted per day)."""

    @patch("actions.mq3_trading._execute_direct_trade")
    @patch("core.command_gateway.execute_command")
    def test_max_three_trades_enforced_4th_rejected_422(self, mock_dispatch, mock_direct):
        """When 3 trades are admitted (with isolated direct trade execution), 4th trade must be rejected with 422."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        mock_direct.return_value = "🚀 [TRADE EXECUTED] ticket #12345"
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

        # Trades 1, 2, 3 must be admitted (each increments by 1 in dashboard.py line 991)
        for i in range(1, 4):
            payload = self._make_valid_order()
            resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
            self.assertEqual(resp.status_code, 200, f"Trade #{i} unexpectedly rejected")
            self.assertEqual(resp.json().get("decision"), "ADMITTED_PROPOSAL")

        self.assertEqual(kernel.daily_trade_count, 3)

        # Trade 4 MUST be rejected
        payload_4 = self._make_valid_order()
        resp_4 = self.client.post("/api/tradingview/webhook", json=payload_4, headers=self.valid_headers)
        self.assertEqual(resp_4.status_code, 422)
        data_4 = resp_4.json()
        self.assertFalse(data_4.get("ok"))
        self.assertEqual(data_4.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("Daily trade limit reached" in b for b in data_4.get("blockers", [])))

    def test_daily_trade_counter_multiple_increment_anomaly(self):
        """EMPIRICAL FINDING: Without mocking _execute_direct_trade, a single webhook trade

        causes multiple increments to daily_trade_count, exhausting the 3-trade daily budget prematurely.
        """
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

        payload = self._make_valid_order()
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 200)

        # In hardened environment, daily_trade_count is exactly 1 (zero double-counting)
        self.assertEqual(kernel.daily_trade_count, 1, "Expected exactly 1 trade count increment")


# =============================================================================
# 7. CONCURRENCY & RACE CONDITION STRESS TESTING
# =============================================================================
class TestWebhookConcurrencyStress(BaseWebhookTest):
    """Adversarially tests race conditions under concurrent burst traffic."""

    @patch("core.command_gateway.execute_command")
    def test_concurrent_burst_admissions_respects_max_3_trades(self, mock_dispatch):
        """Firing 20 simultaneous valid orders must admit EXACTLY <= 3 trades and reject all others."""
        mock_dispatch.return_value = {"ok": True, "output": "Queued"}
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

        def send_order(_):
            client = TestClient(dashboard.app)
            payload = self._make_valid_order()
            return client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)

        num_concurrent = 20
        with ThreadPoolExecutor(max_workers=num_concurrent) as pool:
            responses = list(pool.map(send_order, range(num_concurrent)))

        status_codes = [r.status_code for r in responses]
        admitted_200 = status_codes.count(200)
        blocked_422 = status_codes.count(422)

        # At most 3 trades can ever be admitted
        self.assertLessEqual(admitted_200, 3, f"Concurrency breach: {admitted_200} trades admitted (> 3 cap)")
        self.assertEqual(admitted_200 + blocked_422, num_concurrent, "Non-deterministic response codes detected")
        self.assertGreaterEqual(blocked_422, num_concurrent - 3)

    def test_concurrent_burst_risk_breaches_zero_leaks(self):
        """Firing 30 simultaneous adversarial risk breach orders must yield 100% rejection (0 leaks)."""
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

        breach_payloads = [
            self._make_valid_order(proposed_risk_pct=0.76),           # 0.76% risk
            self._make_valid_order(proposed_risk_usd=751.00),         # $751 dollar risk
            self._make_valid_order(price=2735.0, sl=2740.0, tp=2760.0), # Inverted BUY geometry
            self._make_valid_order(news_lockout_active=True),         # News blackout
            self._make_valid_order(rr_ratio=1.2),                     # Bad RR
            self._make_valid_order(price=0.0)                         # Pathological price
        ] * 5  # 30 total requests

        def send_breach(payload):
            client = TestClient(dashboard.app)
            return client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)

        with ThreadPoolExecutor(max_workers=15) as pool:
            responses = list(pool.map(send_breach, breach_payloads))

        status_codes = [r.status_code for r in responses]

        # Zero requests should ever succeed (HTTP 200 is a total failure)
        self.assertEqual(status_codes.count(200), 0, "CRITICAL: Breach payload succeeded under concurrency!")

        # All responses must be either 400 (Bad Request) or 422 (Unprocessable Entity)
        for r in responses:
            self.assertIn(r.status_code, [400, 422], f"Unexpected status code {r.status_code}: {r.text}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
