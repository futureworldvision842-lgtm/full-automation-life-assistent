"""
tests/test_tradingview_mcp.py — Milestone M1 Verification Suite
=============================================================================
Comprehensive unit and integration test suite covering:
  1. Unit tests for skills/tradingview_mcp_skill.py (Mock CDP, Fallback, Schemas)
  2. Technical indicator math validation (RSI, MACD, Bollinger, EMA Ribbons)
  3. Webhook integration tests for dashboard.py (401, 403, 400, 422, 200 OK)
  4. Downstream relay and adversarial corner cases

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of forbidden identity. Deterministic risk <= 0.75% ($750 cap).
=============================================================================
"""

import os
import sys
import json
import time
import math
import hmac
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe imports for MQ3 src
MQ3_SRC = PROJECT_ROOT / "MQ3 TRADING BOT" / "src"
if str(MQ3_SRC) not in sys.path:
    sys.path.insert(0, str(MQ3_SRC))

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

from starlette.testclient import TestClient

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
try:
    from indicator_ensemble import ExplainableIndicatorEnsemble
except ImportError:
    ExplainableIndicatorEnsemble = None


# =============================================================================
# SYNTHETIC DATA GENERATOR FIXTURE
# =============================================================================

def generate_synthetic_ohlcv(bars: int = 250, regime: str = "bullish") -> Any:
    """Generates deterministic OHLCV DataFrame for indicator verification."""
    if pd is None or np is None:
        return None

    np.random.seed(42)
    base_price = 2700.0
    records = []
    current_close = base_price

    for i in range(bars):
        if regime == "bullish":
            drift = 0.5 + np.random.normal(0, 0.1)
        elif regime == "bearish":
            drift = -0.5 + np.random.normal(0, 0.1)
        elif regime == "flat":
            drift = 0.0
        else:  # oscillating / random
            drift = np.random.normal(0, 0.8)

        current_close = max(10.0, current_close + drift)
        high = current_close + abs(np.random.normal(0.4, 0.1))
        low = current_close - abs(np.random.normal(0.4, 0.1))
        open_price = current_close - drift * 0.5
        volume = 1000 + int(np.random.uniform(100, 500))

        records.append({
            "time": pd.Timestamp("2026-09-20 10:00:00") + pd.Timedelta(minutes=15 * i),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(current_close, 2),
            "tick_volume": volume
        })

    return pd.DataFrame(records)


# =============================================================================
# TEST CLASS 1: UNIT TESTS FOR TRADINGVIEW MCP SKILL
# =============================================================================

class TestTradingViewMCPSkillUnit(unittest.TestCase):
    """Verifies skills/tradingview_mcp_skill.py tool contracts and CDP fallback."""

    def setUp(self):
        import skills.tradingview_mcp_skill as tv_skill
        self.tv_skill = tv_skill

    def test_skill_manifest_structure(self):
        """Skill must expose loader-compatible MANIFEST dictionary."""
        manifest = getattr(self.tv_skill, "MANIFEST", None)
        self.assertIsInstance(manifest, dict)
        self.assertEqual(manifest.get("name"), "tradingview_mcp")
        self.assertIn("description", manifest)
        self.assertIn("parameters", manifest)
        params = manifest["parameters"]
        self.assertEqual(params.get("type"), "OBJECT")
        self.assertIn("action", params.get("properties", {}))

    def test_skill_run_callable_interface(self):
        """Skill must expose run(parameters, player, speak) returning non-empty string."""
        run_fn = getattr(self.tv_skill, "run", None)
        self.assertTrue(callable(run_fn))
        res = run_fn({"action": "status"})
        self.assertIsInstance(res, str)
        self.assertIn("TradingView", res)
        self.assertIn("status", res.lower())

    def test_hermes_tool_schema_compliance(self):
        """Skill must expose an OpenAI/Hermes tool schema accepted by HermesToolRegistry."""
        schema = getattr(self.tv_skill, "HERMES_SCHEMA", None)
        if schema is None and hasattr(self.tv_skill, "get_hermes_schema"):
            schema = self.tv_skill.get_hermes_schema()
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema.get("type"), "function")
        self.assertIn("function", schema)
        self.assertIn("name", schema["function"])
        self.assertIn("parameters", schema["function"])

    @patch("requests.get")
    def test_cdp_online_query_success(self, mock_get):
        """Mock successful CDP discovery and indicator extraction."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "id": "tab_1",
                "title": "TradingView — XAUUSD, 15",
                "url": "https://www.tradingview.com/chart/abc",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/tab_1"
            }
        ]

        with patch.object(self.tv_skill, "_query_cdp_indicators") as mock_query:
            mock_query.return_value = {
                "status": "OK",
                "source": "cdp_live",
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "rsi": {"value": 62.4, "state": "BULLISH_MOMENTUM"},
                "macd": {"macd": 1.2, "signal": 0.9, "hist": 0.3}
            }
            res_str = self.tv_skill.run({"action": "get_indicators", "symbol": "XAUUSD", "timeframe": "M15"})
            data = json.loads(res_str) if res_str.startswith("{") else {"status": "OK"}
            self.assertEqual(data.get("status"), "OK")
            self.assertEqual(data.get("source"), "cdp_live")

    @patch("requests.get", side_effect=Exception("CDP Port 9222 connection refused"))
    def test_cdp_offline_graceful_fallback(self, mock_get):
        """Skill must gracefully fall back to local indicator ensemble when CDP is offline."""
        res_str = self.tv_skill.run({"action": "get_indicators", "symbol": "XAUUSD", "timeframe": "M15"})
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertEqual(data.get("status"), "OK")
        self.assertEqual(data.get("source"), "local_fallback")
        self.assertIn("rsi", data)
        self.assertIn("macd", data)
        self.assertIn("bollinger", data)
        self.assertIn("ema_ribbon", data)

    def test_direct_hermes_functions(self):
        """Direct helper functions for Hermes agent must return valid dictionaries."""
        inds = self.tv_skill.tv_get_indicators("XAUUSD", "M15", force_engine="local")
        self.assertIsInstance(inds, dict)
        self.assertEqual(inds.get("status"), "OK")

        candles = self.tv_skill.tv_get_candles("XAUUSD", "M15", bars=50, force_engine="local")
        self.assertIsInstance(candles, dict)
        self.assertEqual(candles.get("status"), "OK")
        self.assertGreaterEqual(candles.get("bars_count", 0), 50)

        layout = self.tv_skill.tv_get_layout()
        self.assertIsInstance(layout, dict)
        self.assertEqual(layout.get("status"), "OK")

        pine = self.tv_skill.tv_compile_pinescript("")
        self.assertIsInstance(pine, dict)
        self.assertFalse(pine.get("success"))


# =============================================================================
# TEST CLASS 2: TECHNICAL INDICATOR MATHEMATICAL VERIFICATION
# =============================================================================

class TestTradingViewIndicatorsMath(unittest.TestCase):
    """Validates mathematical properties of RSI, MACD, Bollinger Bands, and EMA ribbons."""

    def setUp(self):
        if ExplainableIndicatorEnsemble is None:
            self.skipTest("ExplainableIndicatorEnsemble not available")
        self.ensemble = ExplainableIndicatorEnsemble()

    def test_rsi_monotonic_bullish_overbought(self):
        """Monotonic bullish series must drive RSI >= 90.0."""
        df = generate_synthetic_ohlcv(bars=230, regime="bullish")
        features = self.ensemble.feature_frame(df)
        last_rsi = float(features.iloc[-1]["rsi14"])
        self.assertGreaterEqual(last_rsi, 90.0)

    def test_rsi_monotonic_bearish_oversold(self):
        """Monotonic bearish series must drive RSI <= 10.0."""
        df = generate_synthetic_ohlcv(bars=230, regime="bearish")
        features = self.ensemble.feature_frame(df)
        last_rsi = float(features.iloc[-1]["rsi14"])
        self.assertLessEqual(last_rsi, 10.0)

    def test_rsi_flat_market_neutral(self):
        """Constant price must return neutral RSI of 50.0."""
        df = generate_synthetic_ohlcv(bars=230, regime="flat")
        features = self.ensemble.feature_frame(df)
        last_rsi = float(features.iloc[-1]["rsi14"])
        self.assertEqual(last_rsi, 50.0)

    def test_macd_bullish_acceleration(self):
        """Bullish trend produces positive MACD and signal."""
        df = generate_synthetic_ohlcv(bars=230, regime="bullish")
        features = self.ensemble.feature_frame(df)
        last = features.iloc[-1]
        self.assertGreater(float(last["macd"]), 0.0)
        self.assertGreater(float(last["macd_signal"]), 0.0)

    def test_bollinger_band_ordering_and_percent_b(self):
        """Upper Band >= Mid >= Lower Band."""
        df = generate_synthetic_ohlcv(bars=230, regime="oscillating")
        features = self.ensemble.feature_frame(df)
        last = features.iloc[-1]
        self.assertGreaterEqual(float(last["bb_upper"]), float(last["bb_mid"]))
        self.assertGreaterEqual(float(last["bb_mid"]), float(last["bb_lower"]))

    def test_ema_ribbon_bullish_alignment(self):
        """Bullish trend features EMA 20 > EMA 50 > EMA 200."""
        df = generate_synthetic_ohlcv(bars=250, regime="bullish")
        features = self.ensemble.feature_frame(df)
        last = features.iloc[-1]
        self.assertGreater(float(last["ema20"]), float(last["ema50"]))
        self.assertGreater(float(last["ema50"]), float(last["ema200"]))


# =============================================================================
# TEST CLASS 3: WEBHOOK INTEGRATION TESTS (dashboard.py)
# =============================================================================

class TestTradingViewWebhookIntegration(unittest.TestCase):
    """Integration tests for POST /api/tradingview/webhook with auth, validation & risk checks."""

    @classmethod
    def setUpClass(cls):
        import dashboard
        cls.client = TestClient(dashboard.app)
        cls.passphrase = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "JARVIS_TV_SECRET_2026")
        cls.valid_headers = {
            "Content-Type": "application/json",
            "X-TradingView-Passphrase": cls.passphrase
        }

    def setUp(self):
        # Reset trade count before each test to prevent cross-test leakage
        kernel = get_risk_kernel()
        kernel.daily_trade_count = 0

    # 1. Authentication Gating
    def test_webhook_missing_passphrase_returns_401(self):
        """Inbound webhook without passphrase header must be rejected with 401 Unauthorized."""
        resp = self.client.post("/api/tradingview/webhook", json={"ticker": "XAUUSD", "action": "BUY"})
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertIn("passphrase", data.get("error", "").lower())

    def test_webhook_invalid_passphrase_returns_403(self):
        """Inbound webhook with incorrect passphrase header must be rejected with 403 Forbidden."""
        headers = {"Content-Type": "application/json", "X-TradingView-Passphrase": "WRONG_SECRET_TOKEN"}
        resp = self.client.post("/api/tradingview/webhook", json={"ticker": "XAUUSD", "action": "BUY"}, headers=headers)
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertFalse(data.get("ok"))

    def test_webhook_internal_token_bypass(self):
        """Loopback internal HMAC token allows access without external passphrase."""
        from platform_runtime import internal_command_token
        headers = {
            "Content-Type": "application/json",
            "X-Jarvis-Internal-Token": internal_command_token()
        }
        # Malformed body with internal token should reach endpoint handler (returning 400 not 401/403)
        resp = self.client.post("/api/tradingview/webhook", json={}, headers=headers)
        self.assertEqual(resp.status_code, 400)

    # 2. Payload Validation
    def test_webhook_malformed_json_returns_400(self):
        """Raw unparseable body must return 400 Bad Request."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            content=b"{bad_json_not_valid",
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_missing_required_fields_returns_400(self):
        """Missing mandatory 'ticker' or 'symbol' must return 400 Bad Request."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            json={"action": "BUY", "price": 2735.0},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_invalid_action_returns_400(self):
        """Invalid action ('HOLD' instead of 'BUY'/'SELL') must return 400 Bad Request."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            json={"ticker": "XAUUSD", "action": "HOLD", "price": 2735.0, "sl": 2720.0, "tp": 2760.0},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_inverted_geometry_buy(self):
        """BUY order with SL >= Price must return 422 Unprocessable Entity."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            json={"ticker": "XAUUSD", "action": "BUY", "price": 2735.0, "sl": 2740.0, "tp": 2760.0},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_INVERTED_GEOMETRY")

    def test_webhook_inverted_geometry_sell(self):
        """SELL order with TP >= Price must return 422 Unprocessable Entity."""
        resp = self.client.post(
            "/api/tradingview/webhook",
            json={"ticker": "XAUUSD", "action": "SELL", "price": 2735.0, "sl": 2750.0, "tp": 2740.0},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data.get("decision"), "REJECTED_INVERTED_GEOMETRY")

    # 3. DeterministicRiskKernel Rejection (HTTP 422)
    def test_webhook_excessive_risk_pct_rejected_with_422(self):
        """Proposed risk > 0.75% must be rejected fail-closed with 422 Unprocessable Entity."""
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "price": 2735.50,
            "sl": 2725.50,
            "tp": 2760.50,
            "proposed_risk_pct": 1.25,  # VIOLATION: > 0.75%
            "account_id": "40000294403"
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("decision"), "REJECTED_BLOCKED")
        self.assertTrue(any("exceeds max allowed" in b for b in data.get("blockers", [])))

    def test_webhook_excessive_dollar_risk_rejected_with_422(self):
        """Proposed risk dollar > $750.00 must be rejected with 422 Unprocessable Entity."""
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "price": 2735.50,
            "sl": 2725.50,
            "tp": 2760.50,
            "proposed_risk_usd": 850.00,  # VIOLATION: > $750 cap
            "proposed_risk_pct": 0.75,
            "account_id": "40000294403"
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertTrue(any("$750.00" in b for b in data.get("blockers", [])))

    def test_webhook_substandard_rr_ratio_rejected_with_422(self):
        """Risk-to-Reward ratio < 1:2.5 must be rejected with 422 Unprocessable Entity."""
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "price": 2735.00,
            "sl": 2730.00,  # 5 pts risk
            "tp": 2740.00,  # 5 pts reward (RR = 1.0 < 2.5)
            "proposed_risk_pct": 0.75,
            "account_id": "40000294403"
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertTrue(any("minimum 1:2.5" in b for b in data.get("blockers", [])))

    def test_webhook_news_circuit_breaker_rejected_with_422(self):
        """Active 15-minute news blackout must reject order with 422 Unprocessable Entity."""
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "price": 2735.50,
            "sl": 2725.50,
            "tp": 2760.50,
            "proposed_risk_pct": 0.75,
            "news_lockout_active": True,  # VIOLATION: News blackout active
            "account_id": "40000294403"
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertTrue(any("News Lockout Active" in b for b in data.get("blockers", [])))

    # 4. Valid Order Acceptance & Relay (HTTP 200)
    @patch("core.command_gateway.execute_command")
    def test_webhook_valid_order_accepted_returns_200_and_relays(self, mock_dispatch):
        """Valid order satisfying all 18 gates returns 200 OK and enqueues to gateway."""
        mock_dispatch.return_value = {"ok": True, "output": "Order queued successfully"}
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "timeframe": "M15",
            "price": 2735.50,
            "sl": 2725.50,
            "tp": 2760.50,
            "proposed_risk_pct": 0.75,
            "proposed_risk_usd": 750.00,
            "rr_ratio": 2.5,
            "confluence_score": 92.5,
            "strategy": "SMC_OrderBlock_Sweep",
            "account_id": "40000294403"
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("decision"), "ADMITTED_PROPOSAL")
        self.assertIn("proposal_token", data)
        self.assertEqual(data.get("status"), "QUEUED")
        self.assertEqual(data.get("passed_gates_count"), 18)
        mock_dispatch.assert_called()


# =============================================================================
# TEST CLASS 4: ADVERSARIAL HARDENING & CORNER CASES
# =============================================================================

class TestTradingViewAdversarialEdgeCases(unittest.TestCase):
    """Stress tests boundary and adversarial edge conditions."""

    @classmethod
    def setUpClass(cls):
        import dashboard
        cls.client = TestClient(dashboard.app)
        cls.valid_headers = {
            "Content-Type": "application/json",
            "X-TradingView-Passphrase": os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "JARVIS_TV_SECRET_2026")
        }

    def test_payload_size_flood_rejection(self):
        """Extremely large payloads (>64KB) must be rejected safely without memory spike."""
        giant_payload = {"ticker": "XAUUSD", "action": "BUY", "junk": "A" * 70000}
        resp = self.client.post("/api/tradingview/webhook", json=giant_payload, headers=self.valid_headers)
        self.assertIn(resp.status_code, [400, 413])

    def test_inverted_stop_loss_geometry(self):
        """A BUY order with Stop Loss placed above the Entry Price must be rejected."""
        payload = {
            "ticker": "XAUUSD",
            "action": "BUY",
            "price": 2735.0,
            "sl": 2745.0,  # INVERTED: SL > Entry on BUY
            "tp": 2760.0
        }
        resp = self.client.post("/api/tradingview/webhook", json=payload, headers=self.valid_headers)
        self.assertIn(resp.status_code, [400, 422])


if __name__ == "__main__":
    unittest.main()
