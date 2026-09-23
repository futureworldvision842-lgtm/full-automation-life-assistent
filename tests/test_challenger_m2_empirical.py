"""
tests/test_challenger_m2_empirical.py
================================================================================
EMPIRICAL CHALLENGER 2 STRESS SUITE — MILESTONE M2
(MQ3 Cockpit Dashboard Repair & Live Commentary Restoration)

Adversarial stress-testing of client-side JavaScript execution in:
  dashboard/templates/index.html

Verifies:
1. Headless Chromium browser startup and clean script execution without uncaught
   TypeErrors, ReferenceErrors, or syntax errors.
2. Synthetic malformed commentary payloads (missing tags, None timestamps, null
   arrays, primitive values, HTTP 500 errors, non-JSON strings).
3. Live commentary DOM update logic and dynamic ticker updates.
4. Visual trade cards and breakeven badge rendering (explicit breakeven_locked
   flag, mathematical SL==entry fallback, negative profit, empty positions).
5. Full live backend integration with dashboard/app.py.
================================================================================
"""

import os
import sys
import json
import time
import socket
import threading
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Setup search paths
ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
DASHBOARD_DIR = MQ3_ROOT / "dashboard"
TEMPLATES_DIR = DASHBOARD_DIR / "templates"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from flask import Flask, render_template
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, Browser, Page


class TestChallenger2M2EmpiricalClientSide(unittest.TestCase):
    """Empirical test suite executing client-side JS in real headless Chromium."""

    server = None
    server_thread = None
    server_port = None
    playwright = None
    browser: Browser = None

    @classmethod
    def setUpClass(cls):
        # 1. Spin up an ephemeral HTTP server serving index.html
        flask_app = Flask(__name__, template_folder=str(TEMPLATES_DIR))

        @flask_app.route("/")
        def index_route():
            return render_template("index.html")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        cls.server_port = sock.getsockname()[1]
        sock.close()

        cls.server = make_server("127.0.0.1", cls.server_port, flask_app)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        # 2. Launch headless Chromium
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        if cls.browser:
            cls.browser.close()
        if cls.playwright:
            cls.playwright.stop()
        if cls.server:
            cls.server.shutdown()

    def setUp(self):
        self.page_errors: List[str] = []
        self.console_warnings: List[str] = []
        self.page: Page = self.browser.new_page()

        self.page.on("pageerror", lambda err: self.page_errors.append(str(err)))
        self.page.on("console", lambda msg: self.console_warnings.append(msg.text) if msg.type == "warning" else None)

        # Navigate to the dashboard page
        self.page.goto(f"http://127.0.0.1:{self.server_port}/", wait_until="domcontentloaded", timeout=15000)
        self.page.wait_for_timeout(300)

    def tearDown(self):
        if self.page:
            self.page.close()

    # ==========================================================================
    # CATEGORY 1: BROWSER SCRIPT EXECUTION INTEGRITY
    # ==========================================================================

    def test_01_page_loads_and_initializes_cleanly(self):
        """Verify DOM initializes without uncaught JavaScript exceptions."""
        title = self.page.title()
        self.assertIn("MQ3 Risk Lab", title)
        self.assertEqual(len(self.page_errors), 0, f"Uncaught page errors: {self.page_errors}")

    def test_02_global_commentary_and_trade_card_elements_present(self):
        """Verify required ticker and trade card DOM elements exist."""
        ticker = self.page.query_selector("#liveCommentaryTicker")
        self.assertIsNotNone(ticker, "Missing #liveCommentaryTicker")

        text_el = self.page.query_selector("#commentaryText")
        self.assertIsNotNone(text_el, "Missing #commentaryText")

        badge_el = self.page.query_selector("#commentaryBadge")
        self.assertIsNotNone(badge_el, "Missing #commentaryBadge")

        container = self.page.query_selector("#trade-cards-container")
        self.assertIsNotNone(container, "Missing #trade-cards-container")

        badge_count = self.page.query_selector("#trade-cards-count-badge")
        self.assertIsNotNone(badge_count, "Missing #trade-cards-count-badge")

    # ==========================================================================
    # CATEGORY 2: SYNTHETIC MALFORMED COMMENTARY PAYLOADS INJECTION
    # ==========================================================================

    def _inject_and_run_commentary(self, payload: Any, status: int = 200, content_type: str = "application/json"):
        """Helper to intercept /api/live_commentary and evaluate fetchLiveCommentary()."""
        body_data = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        self.page.unroute("**/api/live_commentary*")
        self.page.route(
            "**/api/live_commentary*",
            lambda route: route.fulfill(status=status, content_type=content_type, body=body_data)
        )
        self.page.evaluate("fetchLiveCommentary()")
        self.page.wait_for_timeout(200)

    def test_03_malformed_empty_object(self):
        """Inject empty object {} -> No uncaught TypeError, polling survives."""
        self._inject_and_run_commentary({})
        self.assertEqual(len(self.page_errors), 0, f"Errors on empty object: {self.page_errors}")

    def test_04_malformed_null_commentary_array(self):
        """Inject {'commentary': null} -> Array.isArray check safely defaults to []."""
        self._inject_and_run_commentary({"commentary": None})
        self.assertEqual(len(self.page_errors), 0, f"Errors on null commentary: {self.page_errors}")

    def test_05_malformed_string_instead_of_array(self):
        """Inject {'commentary': 'malformed_string'} -> Array.isArray check passes safely."""
        self._inject_and_run_commentary({"commentary": "corrupted_payload"})
        self.assertEqual(len(self.page_errors), 0, f"Errors on string commentary: {self.page_errors}")

    def test_06_malformed_number_instead_of_array(self):
        """Inject {'commentary': 99999} -> Array.isArray check handles numeric payload."""
        self._inject_and_run_commentary({"commentary": 99999})
        self.assertEqual(len(self.page_errors), 0, f"Errors on numeric commentary: {self.page_errors}")

    def test_07_malformed_empty_commentary_array(self):
        """Inject {'commentary': []} -> Zero items handled without crash."""
        self._inject_and_run_commentary({"commentary": []})
        self.assertEqual(len(self.page_errors), 0, f"Errors on empty array: {self.page_errors}")

    def test_08_malformed_array_containing_null(self):
        """Inject {'commentary': [null]} -> if (randItem) guard prevents null dereference."""
        self._inject_and_run_commentary({"commentary": [None]})
        self.assertEqual(len(self.page_errors), 0, f"Errors on null item: {self.page_errors}")

    def test_09_malformed_missing_tag_and_time_dual_key_recovery(self):
        """Inject item with only category and timestamp (missing tag and time)."""
        payload = {
            "commentary": [{
                "category": "BIG_SHARKS_RADAR",
                "timestamp": "14:20:00 UTC",
                "text": "Institutional buy absorption detected at support."
            }]
        }
        self._inject_and_run_commentary(payload)
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        content_text = self.page.inner_text("#commentaryText")
        self.assertEqual(badge_text, "BIG SHARKS RADAR")
        self.assertIn("Institutional buy absorption detected", content_text)
        self.assertIn("14:20:00 UTC", content_text)

    def test_10_malformed_missing_category_and_timestamp_legacy_recovery(self):
        """Inject item with only tag and time (missing category and timestamp)."""
        payload = {
            "commentary": [{
                "tag": "TECHNICAL_SETUP",
                "time": "14:25:00 UTC",
                "text": "Fair Value Gap (50% CE) mitigation complete."
            }]
        }
        self._inject_and_run_commentary(payload)
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        content_text = self.page.inner_text("#commentaryText")
        self.assertEqual(badge_text, "TECHNICAL SETUP")
        self.assertIn("Fair Value Gap", content_text)
        self.assertIn("14:25:00 UTC", content_text)

    def test_11_malformed_completely_empty_item_dictionary(self):
        """Inject {'commentary': [{}]} -> Defaults to INSTITUTIONAL and fallback text."""
        self._inject_and_run_commentary({"commentary": [{}]})
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        content_text = self.page.inner_text("#commentaryText")
        self.assertEqual(badge_text, "INSTITUTIONAL")
        self.assertIn("Market structure streaming active", content_text)

    def test_12_malformed_all_fields_explicitly_null(self):
        """Inject item with category=null, tag=null, timestamp=null, text=null."""
        payload = {
            "commentary": [{
                "category": None,
                "tag": None,
                "timestamp": None,
                "time": None,
                "text": None,
                "message": None,
                "title": None
            }]
        }
        self._inject_and_run_commentary(payload)
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        content_text = self.page.inner_text("#commentaryText")
        self.assertEqual(badge_text, "INSTITUTIONAL")
        self.assertIn("Market structure streaming active", content_text)

    def test_13_malformed_non_string_primitive_types(self):
        """Inject numeric category, numeric timestamp, and numeric text."""
        payload = {
            "commentary": [{
                "category": 7777,
                "timestamp": 1726678900,
                "text": 999999
            }]
        }
        self._inject_and_run_commentary(payload)
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        content_text = self.page.inner_text("#commentaryText")
        self.assertEqual(badge_text, "7777")
        self.assertIn("1726678900 — 999999", content_text)

    def test_14_malformed_underscore_tag_formatting(self):
        """Verify String(tag).replace(/_/g, ' ') replaces ALL underscores with spaces."""
        payload = {
            "commentary": [{
                "tag": "LIVE_TRADE_REASONING_MULTIPLE_UNDERSCORES",
                "text": "Position #13002987 breakeven locked.",
                "time": "12:00:00 UTC"
            }]
        }
        self._inject_and_run_commentary(payload)
        self.assertEqual(len(self.page_errors), 0)

        badge_text = self.page.inner_text("#commentaryBadge")
        self.assertEqual(badge_text, "LIVE TRADE REASONING MULTIPLE UNDERSCORES")

    def test_15_malformed_http_500_response_handled_gracefully(self):
        """Inject HTTP 500 error on /api/live_commentary -> if (!res.ok) return exits cleanly."""
        self._inject_and_run_commentary({"error": "Internal Server Crash"}, status=500)
        self.assertEqual(len(self.page_errors), 0)

    def test_16_malformed_non_json_response_handled_gracefully(self):
        """Inject HTML / raw non-JSON text -> Caught by try/catch without uncaught exception."""
        self._inject_and_run_commentary("<html><body>502 Bad Gateway</body></html>", status=200, content_type="text/html")
        self.assertEqual(len(self.page_errors), 0)

    # ==========================================================================
    # CATEGORY 3: LIVE COMMENTARY DOM UPDATE LOGIC
    # ==========================================================================

    def test_17_commentary_dom_updates_dynamically_on_successive_polls(self):
        """Verify successive commentary polls update the DOM without stale text."""
        # 1st poll
        self._inject_and_run_commentary({
            "commentary": [{
                "tag": "FIRST_FEED",
                "text": "First commentary text update.",
                "time": "10:00:01 UTC"
            }]
        })
        self.assertEqual(self.page.inner_text("#commentaryBadge"), "FIRST FEED")
        self.assertIn("First commentary text update.", self.page.inner_text("#commentaryText"))

        # 2nd poll
        self._inject_and_run_commentary({
            "commentary": [{
                "tag": "SECOND_FEED",
                "text": "Second commentary text update.",
                "time": "10:00:09 UTC"
            }]
        })
        self.assertEqual(self.page.inner_text("#commentaryBadge"), "SECOND FEED")
        self.assertIn("Second commentary text update.", self.page.inner_text("#commentaryText"))
        self.assertEqual(len(self.page_errors), 0)

    # ==========================================================================
    # CATEGORY 4: TRADE CARDS & BREAKEVEN BADGE RENDERING
    # ==========================================================================

    def _inject_and_run_trade_cards(self, payload: Any):
        """Helper to intercept /api/trade_cards and evaluate CockpitCoordinator.fetchTradeCards()."""
        body_data = json.dumps(payload) if not isinstance(payload, str) else payload
        self.page.unroute("**/api/trade_cards*")
        self.page.route(
            "**/api/trade_cards*",
            lambda route: route.fulfill(status=200, content_type="application/json", body=body_data)
        )
        self.page.evaluate("CockpitCoordinator.fetchTradeCards()")
        self.page.wait_for_timeout(200)

    def test_18_gbpusd_sell_13002987_renders_breakeven_badge_and_profit(self):
        """Verify ticket #13002987 renders with 🛡️ BREAKEVEN LOCKED badge and profit."""
        payload = {
            "status": "success",
            "positions": [{
                "ticket": 13002987,
                "symbol": "GBPUSD",
                "type": "SELL",
                "direction": "SELL",
                "lots": 0.20,
                "open_price": 1.33675,
                "current_price": 1.33498,
                "profit": 35.40,
                "sl": 1.33675,
                "tp": 1.33149,
                "breakeven_locked": True,
                "strategy_attribution": "ICT Liquidity Sweep + Dynamic Breakeven Lock",
                "mutation_authorized": False
            }]
        }
        self._inject_and_run_trade_cards(payload)
        self.assertEqual(len(self.page_errors), 0)

        card = self.page.query_selector("#card-trade-13002987")
        self.assertIsNotNone(card, "Trade card #card-trade-13002987 was not rendered")

        card_html = card.inner_html()
        self.assertIn("🛡️ BREAKEVEN LOCKED", card_html)
        self.assertIn("+$35.40", card_html)
        self.assertIn("GBPUSD", card_html)
        self.assertIn("1.33675", card_html)

        count_badge = self.page.inner_text("#trade-cards-count-badge")
        self.assertEqual(count_badge.upper(), "1 OPEN POSITIONS")

    def test_19_breakeven_badge_derived_from_sl_equals_entry_price(self):
        """Verify breakeven badge renders when sl == open_price even without explicit boolean flag."""
        payload = {
            "positions": [{
                "ticket": 24001122,
                "symbol": "XAUUSD",
                "type": "BUY",
                "direction": "BUY",
                "lots": 0.10,
                "open_price": 2650.00,
                "current_price": 2656.50,
                "profit": 65.00,
                "sl": 2650.00,  # SL moved to entry
                "tp": 2680.00
                # breakeven_locked is absent
            }]
        }
        self._inject_and_run_trade_cards(payload)
        self.assertEqual(len(self.page_errors), 0)

        card = self.page.query_selector("#card-trade-24001122")
        self.assertIsNotNone(card)
        self.assertIn("🛡️ BREAKEVEN LOCKED", card.inner_html())

    def test_20_breakeven_badge_omitted_when_not_at_breakeven(self):
        """Verify breakeven badge is NOT rendered when SL is below entry and breakeven_locked is False."""
        payload = {
            "positions": [{
                "ticket": 35002233,
                "symbol": "EURUSD",
                "type": "BUY",
                "lots": 0.20,
                "open_price": 1.08500,
                "current_price": 1.08700,
                "profit": 40.00,
                "sl": 1.08200,  # Original risk SL
                "tp": 1.09200,
                "breakeven_locked": False
            }]
        }
        self._inject_and_run_trade_cards(payload)
        self.assertEqual(len(self.page_errors), 0)

        card = self.page.query_selector("#card-trade-35002233")
        self.assertIsNotNone(card)
        self.assertNotIn("BREAKEVEN LOCKED", card.inner_html())

    def test_21_negative_profit_renders_minus_sign(self):
        """Verify position with drawdown renders -$XX.XX in bearish color."""
        payload = {
            "positions": [{
                "ticket": 46003344,
                "symbol": "XAUUSD",
                "type": "BUY",
                "lots": 0.10,
                "open_price": 2655.00,
                "current_price": 2653.20,
                "profit": -18.00,
                "sl": 2645.00,
                "tp": 2675.00
            }]
        }
        self._inject_and_run_trade_cards(payload)
        self.assertEqual(len(self.page_errors), 0)

        card = self.page.query_selector("#card-trade-46003344")
        self.assertIsNotNone(card)
        self.assertIn("-$18.00", card.inner_html())

    def test_22_empty_positions_renders_gated_message(self):
        """Verify empty positions list renders 'No broker-confirmed open positions'."""
        self._inject_and_run_trade_cards({"positions": []})
        self.assertEqual(len(self.page_errors), 0)

        container_text = self.page.inner_text("#trade-cards-container")
        self.assertIn("No broker-confirmed open positions", container_text)

        count_badge = self.page.inner_text("#trade-cards-count-badge")
        self.assertEqual(count_badge.upper(), "0 OPEN POSITIONS")

    def test_23_malformed_trade_cards_empty_and_null_positions(self):
        """Verify empty dict and null positions array default cleanly to zero positions."""
        for malformed in [{}, {"positions": None}, {"positions": []}]:
            self._inject_and_run_trade_cards(malformed)
            self.assertEqual(len(self.page_errors), 0)

    def test_23b_trade_cards_null_root_payload_behavior(self):
        """Document behavior when /api/trade_cards returns literal null body.
        Line 2242 does `data.positions || []`, which will throw TypeError if data is null.
        We verify this behavior empirically with expected TypeError.
        """
        body_data = "null"
        self.page.unroute("**/api/trade_cards*")
        self.page.route(
            "**/api/trade_cards*",
            lambda route: route.fulfill(status=200, content_type="application/json", body=body_data)
        )
        with self.assertRaises(Exception) as ctx:
            self.page.evaluate("CockpitCoordinator.fetchTradeCards()")
        self.assertIn("Cannot read properties of null", str(ctx.exception))

    # ==========================================================================
    # CATEGORY 5: END-TO-END LIVE BACKEND FLASK INTEGRATION
    # ==========================================================================

    def test_24_live_backend_cockpit_server_endpoints(self):
        """Verify backend /api/live_commentary and /api/trade_cards integration."""
        import cockpit.server as cs
        client = cs.app.test_client()

        # 1. Live commentary
        res = client.get("/api/live_commentary?symbol=GBPUSD")
        self.assertEqual(res.status_code, 200)
        comm_data = res.get_json()
        self.assertEqual(comm_data.get("status"), "active")
        self.assertIn("commentary", comm_data)
        self.assertGreaterEqual(len(comm_data["commentary"]), 3)

        # Active position in commentary
        act_pos = comm_data.get("active_position")
        self.assertIsNotNone(act_pos)
        self.assertEqual(act_pos.get("ticket"), 13002987)
        self.assertTrue(act_pos.get("breakeven_locked"))
        self.assertEqual(act_pos.get("profit_usd"), 35.40)

        # Market structure and whale radar
        self.assertIn("market_structure", comm_data)
        self.assertIn("whale_radar", comm_data)
        self.assertGreaterEqual(len(comm_data["whale_radar"].get("whale_walls", [])), 1)

        # 2. Trade cards
        cards_res = client.get("/api/trade_cards")
        self.assertEqual(cards_res.status_code, 200)
        cards_data = cards_res.get_json()
        positions = cards_data.get("positions", [])
        self.assertGreaterEqual(len(positions), 1)
        self.assertTrue(any(p.get("ticket") == 13002987 and p.get("breakeven_locked") for p in positions))

        # 3. Status
        stat_res = client.get("/api/status")
        self.assertEqual(stat_res.status_code, 200)
        stat_data = stat_res.get_json()
        self.assertIn("account", stat_data)
        self.assertIn("prop_firm_gauges", stat_data)


if __name__ == "__main__":
    unittest.main()
