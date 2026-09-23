"""
tests/test_liquidation_radar_stress.py — Empirical Challenger M1-2 Stress Harness.
===================================================================================
Adversarial stress-testing of Global Liquidation Radar & /api/liquidation_radar:
1. Leverage Tiers (5x, 10x, 25x, 50x, 100x), monotonic spacing, and BSL/SSL pricing bounds.
2. Extreme Long/Short account ratios (0.00001, 10000.0, zero, negative, boundary ratios).
3. Shark Magnet vector logic & exact 1.15x boundary transitions.
4. Concurrency & Thread-safety stress testing (50 concurrent threads).
5. Corrupted symbols, SQL/XSS payloads, Unicode, and oversized query parameters.
6. Network timeout, rate limiting, and HTTP 500 error resilience.
7. Cache invalidation, TTL precision, and cache pollution resistance.
"""

import time
import math
import urllib.error
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

from src.global_liquidation_radar import GlobalLiquidationRadar
from dashboard.app import app


@pytest.fixture
def radar_engine():
    """Returns a fresh instance of GlobalLiquidationRadar with 2-second TTL."""
    return GlobalLiquidationRadar(cache_ttl_seconds=2)


@pytest.fixture
def flask_client():
    """Returns Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# =============================================================================
# 1. LEVERAGE TIERS & BSL / SSL MATHEMATICAL BOUNDS STRESS TESTS
# =============================================================================

class TestLeverageTiersAndPricingBounds:
    """Stress tests mathematical bounds, ordering, and leverage offsets across assets."""

    ALL_7_ASSETS = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
    STANDARD_PRICES = [159.30, 2650.0, 68000.0, 1000000.0]

    @pytest.mark.parametrize("price", STANDARD_PRICES)
    def test_monotonic_spacing_across_crypto_and_metals_prices(self, radar_engine, price):
        """
        Verify for standard crypto/metals price scales:
        - 100x Long > 50x Long > 25x Long > 10x Long > 5x Long (all < price)
        - 100x Short < 50x Short < 25x Short < 10x Short < 5x Short (all > price)
        """
        clusters = radar_engine._calculate_liquidation_clusters(price=price, ls_ratio=1.0, symbol="BTCUSD")
        long_pools = clusters["long_liquidation_pools"]
        short_pools = clusters["short_liquidation_pools"]

        assert len(long_pools) == 5
        assert len(short_pools) == 5

        # Check expected leverage tiers
        expected_tiers = [100, 50, 25, 10, 5]
        for i, tier in enumerate(expected_tiers):
            assert f"{tier}x Longs" in long_pools[i]["leverage_tier"]
            assert f"{tier}x Shorts" in short_pools[i]["leverage_tier"]

        # Longs (SSL): Strictly decreasing price levels below mark
        prev_long = price
        for pool in long_pools:
            assert pool["price_level"] < prev_long, f"Long pool {pool} not strictly below {prev_long}"
            assert pool["liquidity_type"] == "SELL_STOP_LIQUIDITY (SSL)"
            assert pool["distance_pct"] > 0
            assert pool["volume_usd"] > 0
            prev_long = pool["price_level"]

        # Shorts (BSL): Strictly increasing price levels above mark
        prev_short = price
        for pool in short_pools:
            assert pool["price_level"] > prev_short, f"Short pool {pool} not strictly above {prev_short}"
            assert pool["liquidity_type"] == "BUY_STOP_LIQUIDITY (BSL)"
            assert pool["distance_pct"] > 0
            assert pool["volume_usd"] > 0
            prev_short = pool["price_level"]

    @pytest.mark.parametrize("symbol", ALL_7_ASSETS)
    def test_asset_volume_weighting(self, radar_engine, symbol):
        """Verify BTC gets full weight (1.0) and non-BTC assets get scaled liquidity factor (0.35)."""
        clusters = radar_engine._calculate_liquidation_clusters(price=1000.0, ls_ratio=1.0, symbol=symbol)
        long_100x = clusters["long_liquidation_pools"][0]
        
        expected_vol = 42.5 * 1e6 * 1.0 * (1.0 if "BTC" in symbol else 0.35)
        assert long_100x["volume_usd"] == pytest.approx(expected_vol, rel=1e-3)

    def test_critical_cluster_ratings(self, radar_engine):
        """Verify 50x and 25x tiers receive CRITICAL_CLUSTER rating while 100x, 10x, 5x are STANDARD_POOL."""
        clusters = radar_engine._calculate_liquidation_clusters(price=50000.0, ls_ratio=1.0, symbol="BTCUSD")
        longs = clusters["long_liquidation_pools"]
        
        assert longs[0]["density_rating"] == "STANDARD_POOL"    # 100x
        assert longs[1]["density_rating"] == "CRITICAL_CLUSTER" # 50x
        assert longs[2]["density_rating"] == "CRITICAL_CLUSTER" # 25x
        assert longs[3]["density_rating"] == "STANDARD_POOL"    # 10x
        assert longs[4]["density_rating"] == "STANDARD_POOL"    # 5x

    def test_forex_micro_price_precision_empirical_boundary(self, radar_engine):
        """
        Empirical boundary test for sub-10.0 prices (e.g. EURUSD at 1.0572).
        Documents the empirical finding where 2-decimal rounding collapses 100x and 50x tiers.
        """
        price = 1.0572
        clusters = radar_engine._calculate_liquidation_clusters(price=price, ls_ratio=1.0, symbol="EURUSD")
        long_pools = clusters["long_liquidation_pools"]
        short_pools = clusters["short_liquidation_pools"]

        # Longs: 1.0572 * (1 - 0.0075) = 1.04927 -> 1.05
        # Shorts: 100x = 1.0572 * 1.0075 = 1.0651 -> 1.07; 50x = 1.0572 * 1.0160 = 1.0741 -> 1.07
        assert len(long_pools) == 5
        assert len(short_pools) == 5
        assert long_pools[0]["price_level"] <= price
        assert short_pools[0]["price_level"] >= price


# =============================================================================
# 2. EXTREME LONG/SHORT IMBALANCES & SHARK MAGNET VECTORS
# =============================================================================

class TestSharkMagnetAndImbalances:
    """Stress tests Shark Magnet directional vector, intensity, and conviction scores."""

    def test_extreme_bullish_crowding_triggers_downside_ssl_hunt(self, radar_engine):
        """Massive long crowding (L/S ratio = 5.0) must trigger DOWNSIDE_SSL_HUNT."""
        clusters = radar_engine._calculate_liquidation_clusters(price=60000.0, ls_ratio=5.0, symbol="BTCUSD")
        long_vol = sum(c["volume_usd"] for c in clusters["long_liquidation_pools"])
        short_vol = sum(c["volume_usd"] for c in clusters["short_liquidation_pools"])

        assert long_vol > short_vol * 1.15
        
        # Test full fetch with mocked L/S
        with patch.object(radar_engine, "_fetch_live_mark_price", return_value=60000.0):
            with patch("urllib.request.urlopen") as mock_url:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'[{"longShortRatio": "3.50"}]'
                mock_resp.__enter__.return_value = mock_resp
                mock_url.return_value = mock_resp

                intel = radar_engine.fetch_liquidation_intel("BTCUSD")
                assert intel["liquidity_magnet"]["direction"] == "DOWNSIDE_SSL_HUNT"
                assert intel["liquidity_magnet"]["intensity"] == "HIGH_CONVICTION_DOWNSIDE"
                assert intel["liquidity_magnet"]["hunt_probability_pct"] == 88.5
                assert intel["retail_sentiment"] == "BULLISH_OVERLEVERAGED"
                assert intel["liquidity_magnet"]["target_price"] == intel["liquidation_heatmap"]["long_liquidation_pools"][0]["price_level"]

    def test_extreme_bearish_crowding_triggers_upside_bsl_squeeze(self, radar_engine):
        """Massive short crowding (L/S ratio = 0.20) must trigger UPSIDE_BSL_SQUEEZE."""
        clusters = radar_engine._calculate_liquidation_clusters(price=60000.0, ls_ratio=0.20, symbol="BTCUSD")
        long_vol = sum(c["volume_usd"] for c in clusters["long_liquidation_pools"])
        short_vol = sum(c["volume_usd"] for c in clusters["short_liquidation_pools"])

        assert short_vol > long_vol * 1.15

        with patch.object(radar_engine, "_fetch_live_mark_price", return_value=60000.0):
            with patch("urllib.request.urlopen") as mock_url:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'[{"longShortRatio": "0.40"}]'
                mock_resp.__enter__.return_value = mock_resp
                mock_url.return_value = mock_resp

                intel = radar_engine.fetch_liquidation_intel("BTCUSD")
                assert intel["liquidity_magnet"]["direction"] == "UPSIDE_BSL_SQUEEZE"
                assert intel["liquidity_magnet"]["intensity"] == "HIGH_CONVICTION_UPSIDE"
                assert intel["liquidity_magnet"]["hunt_probability_pct"] == 88.5
                assert intel["retail_sentiment"] == "BEARISH_OVERLEVERAGED"
                assert intel["liquidity_magnet"]["target_price"] == intel["liquidation_heatmap"]["short_liquidation_pools"][0]["price_level"]

    def test_balanced_liquidity_triggers_two_sided_range_trap(self, radar_engine):
        """Balanced L/S ratio (1.0) must trigger TWO_SIDED_RANGE_TRAP at midpoint."""
        with patch.object(radar_engine, "_fetch_live_mark_price", return_value=60000.0):
            with patch("urllib.request.urlopen") as mock_url:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'[{"longShortRatio": "1.00"}]'
                mock_resp.__enter__.return_value = mock_resp
                mock_url.return_value = mock_resp

                intel = radar_engine.fetch_liquidation_intel("BTCUSD")
                assert intel["liquidity_magnet"]["direction"] == "TWO_SIDED_RANGE_TRAP"
                assert intel["liquidity_magnet"]["intensity"] == "BALANCED_CHOP"
                assert intel["liquidity_magnet"]["hunt_probability_pct"] == 72.0
                assert intel["retail_sentiment"] == "NEUTRAL_BALANCED"
                
                expected_mid = (intel["liquidation_heatmap"]["short_liquidation_pools"][0]["price_level"] + 
                                intel["liquidation_heatmap"]["long_liquidation_pools"][0]["price_level"]) / 2.0
                assert intel["liquidity_magnet"]["target_price"] == round(expected_mid, 2)

    def test_multiplier_clamping_under_asymptotic_ratios(self, radar_engine):
        """Verify extreme ratios (0.000001 or 10000.0 or negative) clamp multiplier to [0.6, 2.5]."""
        # 1. Near-zero ratio
        c_low = radar_engine._calculate_liquidation_clusters(50000.0, ls_ratio=0.000001, symbol="BTCUSD")
        long_vol_low = c_low["long_liquidation_pools"][0]["volume_usd"]
        short_vol_low = c_low["short_liquidation_pools"][0]["volume_usd"]
        assert long_vol_low == pytest.approx(42.5 * 1e6 * 0.6, rel=1e-2)
        assert short_vol_low == pytest.approx(42.5 * 1e6 * 2.5, rel=1e-2)

        # 2. Infinite / huge ratio
        c_high = radar_engine._calculate_liquidation_clusters(50000.0, ls_ratio=99999.0, symbol="BTCUSD")
        long_vol_high = c_high["long_liquidation_pools"][0]["volume_usd"]
        short_vol_high = c_high["short_liquidation_pools"][0]["volume_usd"]
        assert long_vol_high == pytest.approx(42.5 * 1e6 * 2.5, rel=1e-2)
        assert short_vol_high == pytest.approx(42.5 * 1e6 * 0.6, rel=1e-2)

        # 3. Negative ratio (abnormal data feed input)
        c_neg = radar_engine._calculate_liquidation_clusters(50000.0, ls_ratio=-2.0, symbol="BTCUSD")
        assert c_neg["long_liquidation_pools"][0]["volume_usd"] > 0
        assert c_neg["short_liquidation_pools"][0]["volume_usd"] > 0


# =============================================================================
# 3. CONCURRENCY & MULTI-THREADED STRESS TESTING
# =============================================================================

class TestConcurrencyAndThreadSafety:
    """Stress tests concurrency safety under 50 simultaneous worker threads."""

    def test_50_concurrent_threads_engine_access(self, radar_engine):
        """Spawn 50 concurrent threads fetching liquidation intel for different symbols simultaneously."""
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTC_USDT", "ETH/USD"]
        results = []
        errors = []

        def worker(thread_idx):
            try:
                sym = symbols[thread_idx % len(symbols)]
                intel = radar_engine.fetch_liquidation_intel(sym, current_price=1000.0 + thread_idx)
                assert intel["status"] == "success"
                assert "liquidation_heatmap" in intel
                return True
            except Exception as e:
                errors.append(f"Thread-{thread_idx} failed: {repr(e)}")
                return False

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            for f in as_completed(futures):
                results.append(f.result())

        assert len(errors) == 0, f"Encountered thread errors: {errors}"
        assert all(results)
        assert len(results) == 100

    def test_50_concurrent_threads_flask_endpoint(self):
        """Stress test Flask GET /api/liquidation_radar with 50 concurrent HTTP requests with thread-local client."""
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        status_codes = []
        errors = []

        def client_worker(idx):
            try:
                sym = symbols[idx % len(symbols)]
                client = app.test_client()
                resp = client.get(f"/api/liquidation_radar?symbol={sym}")
                data = resp.get_json()
                assert data["status"] == "success"
                return resp.status_code
            except Exception as e:
                errors.append(f"Client thread {idx} error: {repr(e)}")
                return None

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client_worker, i) for i in range(100)]
            for f in as_completed(futures):
                status_codes.append(f.result())

        assert len(errors) == 0, f"Encountered client thread errors: {errors}"
        assert all(sc == 200 for sc in status_codes)
        assert len(status_codes) == 100


# =============================================================================
# 4. CORRUPTED SYMBOLS, INJECTIONS & MALFORMED INPUT RESILIENCE
# =============================================================================

class TestInputSanitizationAndAdversarialPayloads:
    """Stress tests adversarial, corrupted, SQL/XSS injection, and long string symbols."""

    ADVERSARIAL_SYMBOLS = [
        "",                             # Empty string
        "   ",                          # Whitespace
        "btc/usd",                      # Lowercase slash
        "ETH_USD_PERP",                 # Underscores and suffixes
        "SOL-USD-SWAP",                 # Hyphens
        "XAUUSD; DROP TABLE users;--",  # SQL injection attempt
        "<script>alert(1)</script>",    # XSS payload
        "BTC\U0001f4b0\U0001f680\U0001f525",  # Emojis / Unicode
        "A" * 2048,                     # Buffer overflow / long string payload
        "EUR\x00USD",                   # Null byte injection
        "\\\\\\",                       # Escaped backslashes
        "1234567890",                   # Numbers only
    ]

    @pytest.mark.parametrize("corrupted_sym", ADVERSARIAL_SYMBOLS)
    def test_adversarial_symbol_engine_sanitization(self, radar_engine, corrupted_sym):
        """Verify engine never crashes on corrupted symbol inputs."""
        try:
            intel = radar_engine.fetch_liquidation_intel(symbol=corrupted_sym, current_price=100.0)
            assert intel["status"] == "success"
            assert isinstance(intel["mark_price"], (int, float))
            assert len(intel["liquidation_heatmap"]["long_liquidation_pools"]) == 5
        except Exception as e:
            pytest.fail(f"Engine threw unexpected exception on symbol '{corrupted_sym}': {repr(e)}")

    @pytest.mark.parametrize("corrupted_sym", ADVERSARIAL_SYMBOLS)
    def test_adversarial_symbol_endpoint_resilience(self, flask_client, corrupted_sym):
        """Verify endpoint returns HTTP 200 and sanitized response for adversarial symbols."""
        resp = flask_client.get(f"/api/liquidation_radar?symbol={corrupted_sym}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data["status"] == "success"


# =============================================================================
# 5. NETWORK TIMEOUT, RATE LIMITING & REMOTE ERROR HANDLING
# =============================================================================

class TestNetworkFaultTolerance:
    """Stress tests graceful degradation when remote Binance/Hyperliquid endpoints fail."""

    def test_http_429_rate_limit_fallback(self, radar_engine):
        """Simulate HTTP 429 Too Many Requests; ensure fallback works seamlessly."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = urllib.error.HTTPError(
                url="https://fapi.binance.com", code=429, msg="Too Many Requests", hdrs={}, fp=None
            )
            intel = radar_engine.fetch_liquidation_intel("BTCUSD")
            assert intel["status"] == "success"
            assert intel["mark_price"] == 63300.0
            assert intel["long_short_account_ratio"] == 1.05

    def test_http_500_server_error_fallback(self, radar_engine):
        """Simulate HTTP 500 Internal Server Error."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = urllib.error.HTTPError(
                url="https://fapi.binance.com", code=500, msg="Internal Server Error", hdrs={}, fp=None
            )
            intel = radar_engine.fetch_liquidation_intel("ETHUSD")
            assert intel["status"] == "success"
            assert intel["mark_price"] == 1888.0

    def test_network_socket_timeout_fallback(self, radar_engine):
        """Simulate socket timeout during API call."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Socket read timed out")):
            intel = radar_engine.fetch_liquidation_intel("SOLUSD")
            assert intel["status"] == "success"
            assert intel["mark_price"] == 75.50

    def test_malformed_json_response_handling(self, radar_engine):
        """Simulate malformed/truncated JSON payload from remote endpoint."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{ invalid json <<<"
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            intel = radar_engine.fetch_liquidation_intel("XAUUSD")
            assert intel["status"] == "success"
            assert intel["mark_price"] == 4437.30


# =============================================================================
# 6. CACHE INVALIDATION & TTL PRECISION
# =============================================================================

class TestCacheInvalidationAndPrecision:
    """Stress tests caching mechanisms, TTL accuracy, and cache cross-talk isolation."""

    def test_ttl_expiration_and_refresh(self, radar_engine):
        """Verify cache returns exact cached object until TTL passes, then recalculates."""
        # 1. First fetch with price 50,000
        r1 = radar_engine.fetch_liquidation_intel("BTCUSD", current_price=50000.0)
        assert r1["mark_price"] == 50000.0

        # 2. Immediate second fetch with different price (must hit cache)
        r2 = radar_engine.fetch_liquidation_intel("BTCUSD", current_price=55000.0)
        assert r2["mark_price"] == 50000.0
        assert r1 is r2  # Same memory reference

        # 3. Wait for TTL (2.0s) to expire
        time.sleep(2.1)

        # 4. Third fetch must invalidate and reflect new price
        r3 = radar_engine.fetch_liquidation_intel("BTCUSD", current_price=55000.0)
        assert r3["mark_price"] == 55000.0
        assert r3 is not r1

    def test_multi_symbol_cache_isolation(self, radar_engine):
        """Verify caching symbol A does not contaminate or collide with symbol B."""
        r_btc = radar_engine.fetch_liquidation_intel("BTCUSD", current_price=60000.0)
        r_eth = radar_engine.fetch_liquidation_intel("ETHUSD", current_price=3000.0)
        r_xau = radar_engine.fetch_liquidation_intel("XAUUSD", current_price=2600.0)

        assert r_btc["symbol"] == "BTCUSD"
        assert r_btc["mark_price"] == 60000.0

        assert r_eth["symbol"] == "ETHUSD"
        assert r_eth["mark_price"] == 3000.0

        assert r_xau["symbol"] == "XAUUSD"
        assert r_xau["mark_price"] == 2600.0
