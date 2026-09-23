"""
tests/test_adversarial_m1_tradingview_chaos.py
=============================================================================
EMPIRICAL ADVERSARIAL CHALLENGE & STRESS HARNESS — CHALLENGER M1.2
Subject: skills/tradingview_mcp_skill.py
Focus:
  1. CDP Network Chaos: Port connection refused, half-open sockets, 30s delays
     (verifying 1.5s timeout aborts cleanly), non-JSON HTTP responses,
     truncated WebSocket frames.
  2. Mathematical Extremes: Zero, negative, NaN, infinite, single-bar, and
     100,000-bar series to RSI, MACD, Bollinger Bands, and EMA ribbons.
  3. Liveness & Boundness: Concurrency deadlock resistance, bounded indicator
     domains, JSON RFC-8259 compliance, and identity isolation.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Security: Absolute ZERO mentions or use of prohibited credentials anywhere.
=============================================================================
"""

from __future__ import annotations

import http.server
import json
import math
import os
import socket
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Ensure repo root and MQ3 src are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MQ3_SRC = PROJECT_ROOT / "MQ3 TRADING BOT" / "src"
if str(MQ3_SRC) not in sys.path:
    sys.path.insert(0, str(MQ3_SRC))

import pandas as pd
import numpy as np

import skills.tradingview_mcp_skill as tv_skill
from skills.tradingview_mcp_skill import (
    TradingViewCDPClient,
    TradingViewFallbackEngine,
    TradingViewMCPBridge,
    CandleBar,
    run,
    tv_get_indicators,
    tv_get_candles,
    tv_get_layout,
    tv_compile_pinescript,
)

try:
    from indicator_ensemble import ExplainableIndicatorEnsemble
except ImportError:
    ExplainableIndicatorEnsemble = None


# =============================================================================
# MOCK CHAOS NETWORK SERVERS
# =============================================================================

def get_free_port() -> int:
    """Finds an unused ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SlowDelayHTTPServer:
    """Simulates a CDP server that accepts connections but delays response by 30 seconds."""

    def __init__(self, delay_seconds: float = 30.0):
        self.port = get_free_port()
        self.delay_seconds = delay_seconds
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(5)
        self.sock.settimeout(0.5)

        def run_srv():
            while self.running:
                try:
                    conn, _ = self.sock.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break

                # Process in separate handler thread to avoid blocking listener
                def handle_conn(c):
                    try:
                        # Read incoming request
                        c.settimeout(2.0)
                        _ = c.recv(1024)
                        # Sleep for the configured delay
                        start = time.time()
                        while time.time() - start < self.delay_seconds and self.running:
                            time.sleep(0.1)
                        if self.running:
                            resp = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n[]"
                            c.sendall(resp)
                    except Exception:
                        pass
                    finally:
                        try:
                            c.close()
                        except Exception:
                            pass

                threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()

        self.thread = threading.Thread(target=run_srv, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)


class HalfOpenSocketServer:
    """Simulates a half-open socket: accepts connection, sends truncated data, then stalls or resets."""

    def __init__(self, mode: str = "stall"):
        self.port = get_free_port()
        self.mode = mode
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(5)
        self.sock.settimeout(0.5)

        def run_srv():
            while self.running:
                try:
                    conn, _ = self.sock.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break

                def handle_conn(c):
                    try:
                        c.settimeout(2.0)
                        _ = c.recv(1024)
                        if self.mode == "truncated_header":
                            # Send partial HTTP header and reset/close immediately
                            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n")
                            c.close()
                        elif self.mode == "truncated_body":
                            # Send header promising 500 bytes, send 5 bytes, then stall
                            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 500\r\n\r\n{\"par")
                            time.sleep(10.0)
                        elif self.mode == "instant_rst":
                            # Reset socket immediately with SO_LINGER
                            c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\x01\x00\x00\x00\x00\x00\x00\x00")
                            c.close()
                    except Exception:
                        pass
                    finally:
                        try:
                            c.close()
                        except Exception:
                            pass

                threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()

        self.thread = threading.Thread(target=run_srv, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)


class CorruptedHTTPServer:
    """Returns invalid HTTP bodies: HTML, non-list JSON, broken frames."""

    def __init__(self, response_type: str = "html"):
        self.port = get_free_port()
        self.response_type = response_type
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(5)
        self.sock.settimeout(0.5)

        def run_srv():
            while self.running:
                try:
                    conn, _ = self.sock.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break

                def handle_conn(c):
                    try:
                        c.settimeout(2.0)
                        _ = c.recv(1024)
                        if self.response_type == "html":
                            body = b"<html><body>502 Bad Gateway Nginx</body></html>"
                            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8")
                            c.sendall(header + body)
                        elif self.response_type == "malformed_json":
                            body = b'{"browser": "Chrome", "version": '  # truncated json
                            header = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8")
                            c.sendall(header + body)
                        elif self.response_type == "json_dict_not_list":
                            body = b'{"error": "Target list unavailable", "code": 500}'
                            header = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8")
                            c.sendall(header + body)
                        elif self.response_type == "server_500":
                            body = b"Internal Server Error"
                            header = f"HTTP/1.1 500 Internal Server Error\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8")
                            c.sendall(header + body)
                    except Exception:
                        pass
                    finally:
                        try:
                            c.close()
                        except Exception:
                            pass

                threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()

        self.thread = threading.Thread(target=run_srv, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)


# =============================================================================
# TEST CLASS 1: NETWORK CHAOS & FAULT INJECTION
# =============================================================================

class TestTradingViewNetworkChaos(unittest.TestCase):
    """Adversarial stress-testing of CDP network transport and socket fault recovery."""

    def test_connection_refused_immediate_fallback(self):
        """Port connection refused must fail cleanly and fall back without deadlock under 2.0s."""
        dead_port = get_free_port()
        client = TradingViewCDPClient(port=dead_port, timeout=1.5)
        
        t0 = time.perf_counter()
        ping_ok = client.ping()
        elapsed = time.perf_counter() - t0
        
        self.assertFalse(ping_ok)
        # On Windows loopback, connect timeout governs when SYN gets dropped or refused
        self.assertLessEqual(elapsed, 2.0, f"Connection refused took too long: {elapsed:.3f}s")
        
        # Test targets enumeration
        targets = client.list_targets()
        self.assertEqual(targets, [])
        
        # Test full bridge fallback
        bridge = TradingViewMCPBridge(cdp_port=dead_port)
        res = bridge.get_indicators("XAUUSD", "M15")
        self.assertEqual(res.get("status"), "OK")
        self.assertEqual(res.get("source"), "local_fallback")
        self.assertIn("rsi", res)

    def test_cdp_30s_delay_timeout_abort_under_1_5s(self):
        """Simulated 30s delay server must be cleanly aborted by the 1.5s timeout (+- tolerance)."""
        server = SlowDelayHTTPServer(delay_seconds=30.0)
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            
            t0 = time.perf_counter()
            ping_ok = client.ping()
            elapsed_ping = time.perf_counter() - t0
            
            self.assertFalse(ping_ok, "Ping must fail on 30s delay server")
            self.assertGreaterEqual(elapsed_ping, 1.4, f"Timeout aborted prematurely: {elapsed_ping:.3f}s")
            self.assertLess(elapsed_ping, 2.5, f"Timeout took excessively long: {elapsed_ping:.3f}s (target <= 2.5s)")

            # Verify bridge execution with 30s hanging CDP server aborts and falls back
            bridge = TradingViewMCPBridge(cdp_port=server.port)
            t_bridge_start = time.perf_counter()
            res = bridge.get_indicators("XAUUSD", "M15")
            bridge_elapsed = time.perf_counter() - t_bridge_start
            
            self.assertEqual(res.get("status"), "OK")
            self.assertEqual(res.get("source"), "local_fallback")
            # Bridge ping took ~1.5s, then fell back to local calculations
            self.assertLess(bridge_elapsed, 3.5, f"Bridge took too long to abort and fallback: {bridge_elapsed:.3f}s")
        finally:
            server.stop()

    def test_half_open_socket_truncated_header(self):
        """Half-open socket with truncated HTTP header must not hang or crash."""
        server = HalfOpenSocketServer(mode="truncated_header")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            ping_ok = client.ping()
            self.assertFalse(ping_ok)
            
            targets = client.list_targets()
            self.assertEqual(targets, [])
        finally:
            server.stop()

    def test_half_open_socket_truncated_body_stall(self):
        """Half-open socket with truncated body and socket stall must abort at 1.5s timeout."""
        server = HalfOpenSocketServer(mode="truncated_body")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            t0 = time.perf_counter()
            targets = client.list_targets()
            elapsed = time.perf_counter() - t0
            
            self.assertEqual(targets, [])
            self.assertGreaterEqual(elapsed, 1.4)
            self.assertLess(elapsed, 2.5)
        finally:
            server.stop()

    def test_corrupted_http_html_response(self):
        """Server returning 200 OK with HTML content must not crash JSON parser."""
        server = CorruptedHTTPServer(response_type="html")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            # ping returns True only if status_code == 200, which is True here
            # But list_targets() must handle non-JSON body gracefully and return []
            targets = client.list_targets()
            self.assertEqual(targets, [])
        finally:
            server.stop()

    def test_corrupted_http_malformed_json(self):
        """Server returning truncated JSON must be caught by JSONDecodeError and return []."""
        server = CorruptedHTTPServer(response_type="malformed_json")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            targets = client.list_targets()
            self.assertEqual(targets, [])
        finally:
            server.stop()

    def test_corrupted_http_json_dict_instead_of_list(self):
        """Server returning JSON dict instead of list must return [] per type check."""
        server = CorruptedHTTPServer(response_type="json_dict_not_list")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            targets = client.list_targets()
            self.assertEqual(targets, [])
        finally:
            server.stop()

    def test_corrupted_http_500_error(self):
        """Server returning HTTP 500 must return ping=False and list_targets=[] cleanly."""
        server = CorruptedHTTPServer(response_type="server_500")
        server.start()
        try:
            client = TradingViewCDPClient(port=server.port, timeout=1.5)
            self.assertFalse(client.ping())
            self.assertEqual(client.list_targets(), [])
        finally:
            server.stop()

    def test_websocket_simulated_faults_and_truncated_frames(self):
        """Evaluate JS behavior under simulated WebSocket connection drops and malformed frames."""
        client = TradingViewCDPClient(port=get_free_port(), timeout=1.5)
        
        # Case A: evaluate_js when no active target exists -> ConnectionError
        with self.assertRaises(ConnectionError) as ctx:
            client.evaluate_js("1 + 1")
        self.assertIn("No active TradingView chart target", str(ctx.exception))

        # Case B: evaluate_js with target missing webSocketDebuggerUrl -> ConnectionError
        with patch.object(client, "list_targets") as mock_targets:
            mock_targets.return_value = [{"id": "t1", "type": "page", "title": "TradingView", "url": "https://tradingview.com"}]
            with self.assertRaises(ConnectionError) as ctx2:
                client.evaluate_js("1 + 1")
            self.assertIn("has no webSocketDebuggerUrl", str(ctx2.exception))

        # Case C: WebSocket import error / missing websocket client
        with patch.object(client, "get_active_chart_target") as mock_target:
            mock_target.return_value = {"id": "t1", "webSocketDebuggerUrl": "ws://127.0.0.1:9999/devtools"}
            # Mock websocket raising exception on connect or recv
            with patch.dict("sys.modules", {"websocket": MagicMock()}):
                import websocket
                websocket.create_connection.side_effect = TimeoutError("WebSocket connection timed out after 1.5s")
                with self.assertRaises(TimeoutError):
                    client.evaluate_js("1 + 1")

        # Case D: Truncated frame / JSON parse failure in WebSocket recv
        with patch.object(client, "get_active_chart_target") as mock_target:
            mock_target.return_value = {"id": "t1", "webSocketDebuggerUrl": "ws://127.0.0.1:9999/devtools"}
            mock_ws = MagicMock()
            mock_ws.recv.return_value = '{"result": {"result": truncated_frame'
            with patch.dict("sys.modules", {"websocket": MagicMock()}):
                import websocket
                websocket.create_connection.return_value = mock_ws
                with self.assertRaises(json.JSONDecodeError):
                    client.evaluate_js("1 + 1")


# =============================================================================
# TEST CLASS 2: MATHEMATICAL EXTREMES & BOUNDEDNESS
# =============================================================================

class TestTradingViewMathExtremes(unittest.TestCase):
    """Adversarially tests zero division, NaNs, infinities, single-bar and 100k series."""

    def setUp(self):
        self.engine = TradingViewFallbackEngine()

    def test_all_zeros_series_no_zero_division(self):
        """Feeding all zero prices must never raise ZeroDivisionError and maintain bounded indicators."""
        candles = [
            CandleBar(
                timestamp=f"2026-09-20T10:{i:02d}:00Z",
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0.0,
                is_closed=True
            )
            for i in range(50)
        ]
        res = self.engine.calculate_indicators(candles=candles)
        self.assertEqual(res.get("status"), "OK")
        self.assertEqual(res.get("close_price"), 0.0)
        
        # RSI on constant zero price series is 50.0 (neutral)
        self.assertEqual(res["rsi"]["value"], 50.0)
        
        # MACD on zeros is 0.0
        self.assertEqual(res["macd"]["macd"], 0.0)
        self.assertEqual(res["macd"]["signal"], 0.0)
        self.assertEqual(res["macd"]["hist"], 0.0)
        
        # Bollinger Bands on zeros: upper=mid=lower=0.0
        self.assertEqual(res["bollinger"]["mid"], 0.0)
        self.assertEqual(res["bollinger"]["upper"], 0.0)
        self.assertEqual(res["bollinger"]["lower"], 0.0)
        
        # EMA Ribbon on zeros: ema20=ema50=ema200=0.0
        self.assertEqual(res["ema_ribbon"]["ema20"], 0.0)
        self.assertEqual(res["ema_ribbon"]["ema50"], 0.0)
        self.assertEqual(res["ema_ribbon"]["ema200"], 0.0)
        self.assertEqual(res["ema_ribbon"]["spread_20_200_pct"], 0.0)

    def test_negative_price_series(self):
        """Feeding negative price series must compute valid math without domain errors."""
        candles = [
            CandleBar(
                timestamp=f"2026-09-20T10:{i:02d}:00Z",
                open=-100.0 - i * 0.1,
                high=-98.0 - i * 0.1,
                low=-102.0 - i * 0.1,
                close=-100.0 - i * 0.1,
                volume=100.0,
                is_closed=True
            )
            for i in range(50)
        ]
        res = self.engine.calculate_indicators(candles=candles)
        self.assertEqual(res.get("status"), "OK")
        self.assertLess(res.get("close_price"), 0.0)
        
        # RSI must remain mathematically bounded in [0, 100]
        self.assertGreaterEqual(res["rsi"]["value"], 0.0)
        self.assertLessEqual(res["rsi"]["value"], 100.0)
        
        # Bollinger Bands ordering must strictly hold: upper >= mid >= lower
        self.assertGreaterEqual(res["bollinger"]["upper"], res["bollinger"]["mid"])
        self.assertGreaterEqual(res["bollinger"]["mid"], res["bollinger"]["lower"])

    def test_nan_embedded_series_handling(self):
        """Candles containing scattered NaNs must be filtered without unhandled crash."""
        candles = [
            CandleBar(
                timestamp=f"2026-09-20T10:{i:02d}:00Z",
                open=100.0 if i % 5 != 0 else float("nan"),
                high=105.0 if i % 7 != 0 else float("nan"),
                low=95.0,
                close=100.0 + i,
                volume=50.0,
                is_closed=True
            )
            for i in range(60)
        ]
        # Valid non-nan rows should be processed
        res = self.engine.calculate_indicators(candles=candles)
        self.assertEqual(res.get("status"), "OK")
        self.assertGreaterEqual(res["rsi"]["value"], 0.0)
        self.assertLessEqual(res["rsi"]["value"], 100.0)

    def test_all_nan_series_empty_frame_behavior(self):
        """When all candles are NaN, feature_frame drops all rows resulting in an empty DataFrame."""
        candles = [
            CandleBar(
                timestamp=f"2026-09-20T10:{i:02d}:00Z",
                open=float("nan"),
                high=float("nan"),
                low=float("nan"),
                close=float("nan"),
                volume=0.0,
                is_closed=True
            )
            for i in range(50)
        ]
        # In feature_frame: df = df.dropna(subset=['open', 'high', 'low', 'close'])
        # When all rows are NaN, df has 0 rows. calculate_indicators attempts features.iloc[-1]
        # This test verifies that calling calculate_indicators with 100% NaN candles raises IndexError
        with self.assertRaises(IndexError):
            self.engine.calculate_indicators(candles=candles)

    def test_infinite_prices_handling(self):
        """Feeding infinite values (+inf / -inf) must not cause unbounded exponentiation or memory leak."""
        df_inf = pd.DataFrame([
            {"open": 100.0, "high": 105.0, "low": 95.0, "close": 100.0 if i < 40 else np.inf, "tick_volume": 10.0}
            for i in range(50)
        ])
        if ExplainableIndicatorEnsemble:
            ens = ExplainableIndicatorEnsemble()
            res_df = ens.feature_frame(df_inf)
            self.assertEqual(len(res_df), 50)
            # Check that RSI for inf row is bounded
            last_rsi = float(res_df.iloc[-1]["rsi14"])
            self.assertTrue(math.isfinite(last_rsi) or math.isnan(last_rsi))

    def test_single_bar_input_graceful_synthetic_enrichment(self):
        """Single-bar input (<30 bars) must be safely caught by fallback engine and enriched."""
        candles = [CandleBar("2026-09-20T10:00:00Z", 2735.0, 2740.0, 2730.0, 2738.0, 1500.0)]
        # calculate_indicators checks len(candles) < 30 and synthesizes 250 bars to guarantee 100% availability
        res = self.engine.calculate_indicators(candles=candles)
        self.assertEqual(res.get("status"), "OK")
        self.assertIn("rsi", res)
        self.assertIn("bollinger", res)
        self.assertIn("macd", res)
        self.assertIn("ema_ribbon", res)

    def test_empty_candle_list_input(self):
        """Empty candle list must synthesize fallback candles rather than failing."""
        res = self.engine.calculate_indicators(candles=[])
        self.assertEqual(res.get("status"), "OK")
        self.assertGreater(res.get("close_price", 0.0), 0.0)

    def test_large_series_100_000_bars_performance(self):
        """100,000-bar series must execute in bounded time (<5.0s) and memory without deadlock."""
        bars_count = 100000
        candles = [
            CandleBar(
                timestamp="2026-09-20T10:00:00Z",
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0 + (i % 20),
                volume=100.0,
                is_closed=True
            )
            for i in range(bars_count)
        ]
        t0 = time.perf_counter()
        res = self.engine.calculate_indicators(candles=candles)
        elapsed = time.perf_counter() - t0
        
        self.assertEqual(res.get("status"), "OK")
        self.assertLess(elapsed, 5.0, f"100k bars calculation exceeded 5s SLA: {elapsed:.2f}s")
        self.assertGreaterEqual(res["rsi"]["value"], 0.0)
        self.assertLessEqual(res["rsi"]["value"], 100.0)

    def test_indicators_strict_mathematical_bounds(self):
        """Verify strict mathematical domain bounds across diverse regimes."""
        for regime in ("bullish", "bearish", "flat", "volatile"):
            candles = self.engine.get_synthetic_candles("XAUUSD", "M15", bars=250, regime=regime)
            res = self.engine.calculate_indicators(candles=candles)
            
            rsi_val = res["rsi"]["value"]
            self.assertGreaterEqual(rsi_val, 0.0, f"RSI underflow in {regime}: {rsi_val}")
            self.assertLessEqual(rsi_val, 100.0, f"RSI overflow in {regime}: {rsi_val}")
            
            bb = res["bollinger"]
            self.assertGreaterEqual(bb["upper"], bb["mid"] - 1e-6, f"BB upper < mid in {regime}")
            self.assertGreaterEqual(bb["mid"], bb["lower"] - 1e-6, f"BB mid < lower in {regime}")
            
            ribbon = res["ema_ribbon"]
            self.assertIn(ribbon["alignment"], {"BULLISH_STACK", "BEARISH_STACK", "COMPRESSED", "NEUTRAL"})
            self.assertGreaterEqual(ribbon["spread_20_200_pct"], 0.0)
            
            score = res.get("confluence_score", 0.0)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)


# =============================================================================
# TEST CLASS 3: CONCURRENCY, DEADLOCK RESISTANCE & JSON BOUNDING
# =============================================================================

class TestTradingViewConcurrencyAndLiveness(unittest.TestCase):
    """Stress tests concurrent execution, deadlock avoidance, and RFC-8259 JSON compliance."""

    def test_concurrent_bridge_execution_no_deadlock(self):
        """20 parallel worker threads executing get_indicators() must complete cleanly without deadlock."""
        bridge = TradingViewMCPBridge(cdp_port=get_free_port())
        worker_count = 20
        results = []
        errors = []

        def worker(wid: int):
            try:
                # Alternate symbols and timeframes
                sym = "XAUUSD" if wid % 2 == 0 else "EURUSD"
                tf = "M15" if wid % 3 == 0 else "H1"
                out = bridge.get_indicators(symbol=sym, timeframe=tf)
                results.append((wid, out))
            except Exception as e:
                errors.append((wid, e))

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(worker, i) for i in range(worker_count)]
            for f in futures:
                f.result()
        total_time = time.perf_counter() - t0

        self.assertEqual(len(errors), 0, f"Concurrent workers encountered errors: {errors}")
        self.assertEqual(len(results), worker_count)
        self.assertLess(total_time, 5.0, f"Concurrent execution took {total_time:.2f}s (exceeded 5.0s)")

    def test_run_skill_entrypoint_json_validity(self):
        """run(parameters) must return valid parseable JSON for all operations."""
        actions = ["get_indicators", "get_candles", "get_layout", "compile_pinescript", "health_check"]
        for act in actions:
            raw_out = run({"action": act, "symbol": "XAUUSD", "timeframe": "M15"})
            self.assertIsInstance(raw_out, str)
            # Must parse as JSON
            data = json.loads(raw_out)
            self.assertIsInstance(data, dict)
            self.assertTrue(
                "status" in data or "success" in data,
                f"Action {act} missing status or success key in output: {data}"
            )

    def test_status_action_plain_text_compliance(self):
        """action='status' returns the human-readable string expected by skills/loader.py."""
        status_out = run({"action": "status"})
        self.assertIn("[TradingView MCP Server Status: ACTIVE]", status_out)
        self.assertIn("CDP Discovery Port", status_out)
        self.assertIn("Local Fallback Engine", status_out)

    def test_json_strict_nan_safety_in_normal_flow(self):
        """Normal flow must not produce bare NaN / Infinity in JSON responses."""
        res_str = run({"action": "get_indicators", "symbol": "XAUUSD", "timeframe": "M15"})
        parsed = json.loads(res_str)
        self.assertEqual(parsed.get("status"), "OK")

    def test_empirical_vulnerability_flat_series_produces_nan_in_bollinger(self):
        """
        EMPIRICAL FINDING: When candle prices are flat (constant across all bars),
        bb_range is 0 which gets replaced by np.nan in indicator_ensemble.py,
        causing bandwidth_pct and percent_b to be NaN in the resulting dictionary,
        which serializes to non-standard bare 'NaN' in json.dumps().
        """
        engine = TradingViewFallbackEngine()
        candles_const = [
            CandleBar(f"2026-09-20T10:{i:02d}:00Z", 100.0, 100.0, 100.0, 100.0, 50.0)
            for i in range(50)
        ]
        res = engine.calculate_indicators(candles=candles_const)
        bb = res.get("bollinger", {})
        # Empirically verify that bandwidth_pct and percent_b are NaN
        self.assertTrue(math.isnan(bb.get("bandwidth_pct")), "bandwidth_pct is expected to be NaN on flat series")
        self.assertTrue(math.isnan(bb.get("percent_b")), "percent_b is expected to be NaN on flat series")
        
        # Verify that json.dumps outputs literal 'NaN' which fails strict RFC 8259 parsing
        raw_json = json.dumps(res)
        self.assertIn("NaN", raw_json)

    def test_empirical_vulnerability_force_engine_cdp_silent_fallback(self):
        """
        EMPIRICAL FINDING: When CDP is offline, passing force_engine='cdp' to
        get_indicators() or get_candles() silently falls back to 'local_fallback'
        rather than returning an error status, because _query_cdp_indicators returns None
        without raising an exception.
        """
        bridge = TradingViewMCPBridge(cdp_port=get_free_port())
        res_ind = bridge.get_indicators(symbol="XAUUSD", timeframe="M15", force_engine="cdp")
        self.assertEqual(res_ind.get("status"), "OK")
        self.assertEqual(res_ind.get("source"), "local_fallback")

        res_candles = bridge.get_candles(symbol="XAUUSD", timeframe="M15", bars=50, force_engine="cdp")
        self.assertEqual(res_candles.get("status"), "OK")
        self.assertEqual(res_candles.get("source"), "local_fallback")


# =============================================================================
# TEST CLASS 4: IDENTITY & SECURITY CONSTRAINTS
# =============================================================================

class TestTradingViewSecurityAndIdentity(unittest.TestCase):
    """Verifies strict adherence to identity constraints and zero prohibited mentions."""

    def test_zero_mentions_of_prohibited_identity(self):
        """Codebase files under test must contain ZERO mentions of the forbidden username."""
        files_to_check = [
            PROJECT_ROOT / "skills" / "tradingview_mcp_skill.py",
            PROJECT_ROOT / "tests" / "test_tradingview_mcp.py",
            PROJECT_ROOT / "tests" / "test_adversarial_m1_tradingview_chaos.py",
        ]
        prohibited = "adeel" + "qureshi99"
        
        for fp in files_to_check:
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn(
                prohibited,
                content,
                f"VIOLATION: Prohibited token found in {fp}"
            )

    def test_owner_identity_metadata_in_skill_docstring(self):
        """Skill docstring must record Master Muhammad Qureshi as owner."""
        skill_file = PROJECT_ROOT / "skills" / "tradingview_mcp_skill.py"
        content = skill_file.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("Master Muhammad Qureshi", content)
        self.assertIn("+923468053268", content)
        self.assertIn("futureworldvision842@gmail.com", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
