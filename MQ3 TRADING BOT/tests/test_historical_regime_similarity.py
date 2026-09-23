"""
tests/test_historical_regime_similarity.py
Tests for Feature 9: 50-Year Historical Crisis Regime Library, 7D Cosine Similarity, and Dynamic Risk Scaling.
"""

import numpy as np
import pytest
from src.historical_50yr_regime_library import Historical50YrRegimeLibrary


class TestHistoricalRegimeSimilarity:

    @pytest.fixture
    def lib(self):
        return Historical50YrRegimeLibrary()

    def test_crisis_centroids_dimensions_and_metadata(self, lib):
        assert len(lib.crisis_archetypes) >= 10
        canonical_10 = [
            "1971_NIXON_SHOCK_STAGFLATION",
            "1987_BLACK_MONDAY_CASCADE",
            "1997_ASIAN_FINANCIAL_CRISIS",
            "2000_DOTCOM_BUBBLE_COLLAPSE",
            "2008_GFC_CREDIT_FREEZE",
            "2011_US_DEBT_DOWNGRADE_EURO_CRISIS",
            "2015_SNB_EUR_CHF_PEG_REMOVAL",
            "2020_COVID_LIQUIDITY_FREEZE",
            "2022_FED_TIGHTENING_INFLATION_SHOCK",
            "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"
        ]
        for name in canonical_10:
            assert name in lib.crisis_archetypes
            entry = lib.crisis_archetypes[name]
            assert "centroid" in entry
            assert len(entry["centroid"]) == 7
            assert "era" in entry
            assert "description" in entry
            assert "sovereign_rule" in entry

    def test_cosine_and_euclidean_similarity_math(self, lib):
        # Pass identical 1987 Black Monday vector
        v_87 = lib.crisis_archetypes["1987_BLACK_MONDAY_CASCADE"]["centroid"]
        res = lib.classify_current_regime(feature_vector=v_87)

        assert res["closest_crisis_regime"] == "1987_BLACK_MONDAY_CASCADE"
        assert res["crisis_similarity"] >= 0.95
        assert res["action_protocol"] == "DEFENSIVE_CIRCUIT_BREAKER"
        assert res["risk_scalar"] == 0.20

    def test_risk_scalar_circuit_breaker_levels(self, lib):
        # 1. Critical Crash Regime (2008 GFC) -> 0.20x
        res_gfc = lib.classify_current_regime(feature_vector=lib.crisis_archetypes["2008_GFC_CREDIT_FREEZE"]["centroid"])
        assert res_gfc["risk_scalar"] == 0.20
        assert res_gfc["action_protocol"] == "DEFENSIVE_CIRCUIT_BREAKER"

        # 2. Sovereign Hard Asset Expansion (2023-2026 AI/Geopolitical) -> 0.90x
        res_gold = lib.classify_current_regime(feature_vector=lib.crisis_archetypes["2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"]["centroid"])
        assert res_gold["risk_scalar"] >= 0.80
        assert res_gold["action_protocol"] == "SOVEREIGN_HARD_ASSET_EXPANSION"

        # 3. Normal conditions -> 1.00x
        normal_vector = [0.10, 0.01, 0.0, 0.0, 0.10, 0.0, 0.0]
        res_norm = lib.classify_current_regime(feature_vector=normal_vector)
        assert res_norm["risk_scalar"] == 1.00
        assert res_norm["action_protocol"] == "NORMAL_SOVEREIGN_EXECUTION"
