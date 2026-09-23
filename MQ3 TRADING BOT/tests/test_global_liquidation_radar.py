"""
tests/test_global_liquidation_radar.py
Comprehensive test suite for GlobalLiquidationRadar and /api/liquidation_radar endpoint across all 7 assets.
"""

import pytest
import time
from unittest.mock import patch
from src.global_liquidation_radar import GlobalLiquidationRadar
from dashboard.app import app


@pytest.fixture
def radar():
    return GlobalLiquidationRadar(cache_ttl_seconds=1)


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestGlobalLiquidationRadarUnit:
    """Unit tests for the GlobalLiquidationRadar core engine."""

    ALL_ASSETS = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

    @pytest.mark.parametrize("symbol", ALL_ASSETS)
    def test_fetch_liquidation_intel_all_assets_schema(self, radar, symbol):
        """Verify schema integrity and valid values across all 7 supported instruments."""
        intel = radar.fetch_liquidation_intel(symbol=symbol)
        
        assert intel["status"] == "success"
        assert intel["symbol"] == symbol.replace("/", "").replace("_", "").replace("-", "").upper()
        assert isinstance(intel["mark_price"], (int, float))
        assert intel["mark_price"] > 0
        assert isinstance(intel["long_short_account_ratio"], float)
        assert intel["retail_sentiment"] in ["BULLISH_OVERLEVERAGED", "BEARISH_OVERLEVERAGED", "NEUTRAL_BALANCED"]
        assert intel["long_liquidation_volume_total_usd"] >= 0
        assert intel["short_liquidation_volume_total_usd"] >= 0
        assert "liquidity_magnet" in intel
        assert "direction" in intel["liquidity_magnet"]
        assert "target_price" in intel["liquidity_magnet"]
        assert "intensity" in intel["liquidity_magnet"]
        assert "hunt_probability_pct" in intel["liquidity_magnet"]
        assert intel["liquidity_magnet"]["hunt_probability_pct"] in [88.5, 72.0]
        assert "liquidation_heatmap" in intel
        assert "long_liquidation_pools" in intel["liquidation_heatmap"]
        assert "short_liquidation_pools" in intel["liquidation_heatmap"]
        assert len(intel["liquidation_heatmap"]["long_liquidation_pools"]) == 5
        assert len(intel["liquidation_heatmap"]["short_liquidation_pools"]) == 5

    def test_mathematical_pool_levels_relative_to_mark_price(self, radar):
        """Verify long stops sit below mark price and short stops sit above mark price."""
        intel = radar.fetch_liquidation_intel("BTCUSD", current_price=60000.0)
        mark = intel["mark_price"]
        assert mark == 60000.0

        long_pools = intel["liquidation_heatmap"]["long_liquidation_pools"]
        short_pools = intel["liquidation_heatmap"]["short_liquidation_pools"]

        # Longs liquidated below price (Sell Stop Liquidity - SSL)
        for pool in long_pools:
            assert pool["price_level"] < mark, f"Long liq {pool['price_level']} must be below mark {mark}"
            assert pool["liquidity_type"] == "SELL_STOP_LIQUIDITY (SSL)"

        # Shorts liquidated above price (Buy Stop Liquidity - BSL)
        for pool in short_pools:
            assert pool["price_level"] > mark, f"Short liq {pool['price_level']} must be above mark {mark}"
            assert pool["liquidity_type"] == "BUY_STOP_LIQUIDITY (BSL)"

        # Check leverage tier ordering: 100x is closest to mark, 5x is furthest
        assert long_pools[0]["price_level"] > long_pools[1]["price_level"] > long_pools[2]["price_level"] > long_pools[3]["price_level"] > long_pools[4]["price_level"]
        assert short_pools[0]["price_level"] < short_pools[1]["price_level"] < short_pools[2]["price_level"] < short_pools[3]["price_level"] < short_pools[4]["price_level"]

    def test_shark_magnet_directional_bias(self, radar):
        """Verify shark magnet direction is correctly assigned based on volume imbalance."""
        # 1. High long/short ratio -> heavy long stop pool -> downside hunt
        clusters_down = radar._calculate_liquidation_clusters(60000.0, ls_ratio=2.0, symbol="BTCUSD")
        long_vol_down = sum(c["volume_usd"] for c in clusters_down["long_liquidation_pools"])
        short_vol_down = sum(c["volume_usd"] for c in clusters_down["short_liquidation_pools"])
        assert long_vol_down > short_vol_down * 1.15

        # 2. Low long/short ratio -> heavy short stop pool -> upside squeeze
        clusters_up = radar._calculate_liquidation_clusters(60000.0, ls_ratio=0.4, symbol="BTCUSD")
        long_vol_up = sum(c["volume_usd"] for c in clusters_up["long_liquidation_pools"])
        short_vol_up = sum(c["volume_usd"] for c in clusters_up["short_liquidation_pools"])
        assert short_vol_up > long_vol_up * 1.15

    def test_caching_and_ttl(self, radar):
        """Verify memory cache returns identical reference within TTL and updates after expiration."""
        r1 = radar.fetch_liquidation_intel("BTCUSD", current_price=50000.0)
        # Immediate subsequent call should hit cache
        r2 = radar.fetch_liquidation_intel("BTCUSD", current_price=55000.0)
        assert r1["mark_price"] == r2["mark_price"] == 50000.0

        # Wait for TTL to expire
        time.sleep(1.1)
        r3 = radar.fetch_liquidation_intel("BTCUSD", current_price=55000.0)
        assert r3["mark_price"] == 55000.0

    def test_symbol_normalization(self, radar):
        """Verify symbol string formatting variations resolve to standard clean symbol."""
        symbols = ["btc/usd", "BTC_USD", "btc-usd", "BTCUSD"]
        for sym in symbols:
            intel = radar.fetch_liquidation_intel(sym, current_price=60000.0)
            assert intel["symbol"] == "BTCUSD"

    def test_network_failure_fallback_resilience(self, radar):
        """Verify that when network requests fail, default fallback prices and metrics are returned safely."""
        with patch("urllib.request.urlopen", side_effect=Exception("Connection timed out")):
            intel_btc = radar.fetch_liquidation_intel("BTCUSD")
            assert intel_btc["status"] == "success"
            assert intel_btc["mark_price"] == 63300.0
            assert intel_btc["long_short_account_ratio"] == 1.05

            intel_eth = radar.fetch_liquidation_intel("ETHUSD")
            assert intel_eth["status"] == "success"
            assert intel_eth["mark_price"] == 1888.00

            intel_sol = radar.fetch_liquidation_intel("SOLUSD")
            assert intel_sol["status"] == "success"
            assert intel_sol["mark_price"] == 75.50

            intel_gold = radar.fetch_liquidation_intel("XAUUSD")
            assert intel_gold["status"] == "success"
            assert intel_gold["mark_price"] == 4437.30


class TestLiquidationRadarEndpoint:
    """Integration tests for the Flask GET /api/liquidation_radar endpoint."""

    ALL_ASSETS = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

    @pytest.mark.parametrize("symbol", ALL_ASSETS)
    def test_endpoint_returns_200_all_assets(self, test_client, symbol):
        """Verify GET /api/liquidation_radar?symbol={sym} returns HTTP 200 with valid schema."""
        resp = test_client.get(f"/api/liquidation_radar?symbol={symbol}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data["status"] == "success"
        assert data["symbol"] == symbol
        assert "liquidity_magnet" in data
        assert "liquidation_heatmap" in data
        assert len(data["liquidation_heatmap"]["long_liquidation_pools"]) == 5
        assert len(data["liquidation_heatmap"]["short_liquidation_pools"]) == 5

    def test_endpoint_default_query_and_edge_cases(self, test_client):
        """Verify endpoint behavior with empty query and non-standard symbols."""
        # 1. No symbol param -> defaults to BTCUSD
        resp_default = test_client.get("/api/liquidation_radar")
        assert resp_default.status_code == 200
        data_default = resp_default.get_json()
        assert data_default["symbol"] == "BTCUSD"

        # 2. Arbitrary symbol
        resp_arb = test_client.get("/api/liquidation_radar?symbol=UNKNOWN_ASSET")
        assert resp_arb.status_code == 200
        data_arb = resp_arb.get_json()
        assert data_arb["status"] == "success"
        assert data_arb["symbol"] == "UNKNOWNASSET"
