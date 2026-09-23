"""Regression tests for truthful runtime and provenance labels."""

import sqlite3
import threading

from src.ai_learning_engine import AILearningEngine
from src.ai_trader_intel import FreeMarketDataFetcher


def test_ai_summary_does_not_claim_unconfigured_cloud_services(tmp_path):
    engine = object.__new__(AILearningEngine)
    engine.db_path = str(tmp_path / "memory.db")
    engine._lock = threading.RLock()
    engine._init_db()

    summary = engine.get_ai_learning_summary()

    assert summary["ai_status"] == "LOCAL_POST_TRADE_MEMORY"
    assert summary["memory_tree_sync"] == "LOCAL_FILE"
    assert summary["firebase_sync"] == "NOT_CONNECTED_LOCAL_MOCK_ONLY"
    assert summary["mongodb_sync"] == "NOT_CONNECTED_LOCAL_MOCK_ONLY"

    with sqlite3.connect(engine.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0] == 0


def test_dxy_correlation_has_no_invented_fallback():
    fetcher = object.__new__(FreeMarketDataFetcher)
    fetcher._yf_available = False

    result = fetcher.get_dxy_correlation()

    assert result["available"] is False
    assert result["correlation"] is None


def test_market_regime_fails_closed_without_aligned_gold_data(monkeypatch):
    fetcher = object.__new__(FreeMarketDataFetcher)
    monkeypatch.setattr(
        fetcher,
        "get_dxy_correlation",
        lambda gold_df=None: {
            "available": False,
            "correlation": None,
            "source": "aligned_gold_series_required",
        },
    )
    monkeypatch.setattr(
        fetcher,
        "get_crypto_sentiment",
        lambda: {
            "btc_price": 100_000.0,
            "sentiment": "RISK_ON",
            "source": "test_feed",
        },
    )

    result = fetcher.get_market_regime()

    assert result["regime"] == "UNAVAILABLE"
    assert result["confidence"] == 0.0
    assert result["actionable"] is False
    assert result["dxy_correlation"] is None
