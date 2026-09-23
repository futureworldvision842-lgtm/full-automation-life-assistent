"""
src/historical_50yr_regime_library.py
50-Year Market Historical Regime & Crisis Library (1971–2026).
Computes 7D Cosine Similarity, Radial Basis Distance, and Dynamic Risk Scaling.
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("Historical50YrRegimeLibrary")


class Historical50YrRegimeLibrary:
    """
    50-Year Historical Crisis & SuperContext Regime Classifier.
    Evaluates live multi-asset features against 10 historical crisis centroids across a 7D normalized feature vector:
    [realized_vol_annual, drawdown_depth_pct, dxy_momentum_20d, yield_curve_stress,
     liquidity_spread_stress, cross_asset_correlation, safe_haven_gold_impulse]
    """

    def __init__(self):
        # 10 Crisis Centroids across 7D feature space
        self.crisis_archetypes: Dict[str, Dict[str, Any]] = {
            # 1. 1970s Stagflation & Nixon Shock (1971-1979)
            "1971_NIXON_SHOCK_STAGFLATION": {
                "centroid": np.array([0.24, 0.12, -0.15, -0.40, 0.45, -0.30, 0.85], dtype=float),
                "era": "1971-1979",
                "description": "Bretton Woods collapse, runaway stagflation, energy embargo, massive sovereign gold accumulation, fiat debasement.",
                "sovereign_rule": "Sovereign hard asset accumulation; buy dips on Gold; avoid holding unhedged fiat cash in high-inflation shocks.",
                "risk_scalar": 0.80,
                "default_action": "SOVEREIGN_HARD_ASSET_EXPANSION"
            },
            # 2. 1987 Black Monday Cascade (Oct 19, 1987)
            "1987_BLACK_MONDAY_CASCADE": {
                "centroid": np.array([0.55, 0.28, 0.05, 0.20, 0.85, 0.70, 0.15], dtype=float),
                "era": "1987",
                "description": "Portfolio insurance automated dynamic hedging liquidation cascade, single-day 22.6% crash, severe liquidity vacuum.",
                "sovereign_rule": "Never short after a 4-sigma panic flush; buy structural support retests after central bank liquidity backstops.",
                "risk_scalar": 0.20,
                "default_action": "DEFENSIVE_CIRCUIT_BREAKER"
            },
            # 3. 1997 Asian Financial Crisis (1997-1998)
            "1997_ASIAN_FINANCIAL_CRISIS": {
                "centroid": np.array([0.38, 0.20, 0.25, 0.15, 0.75, 0.50, 0.30], dtype=float),
                "era": "1997-1998",
                "description": "Emerging market currency peg collapse (Thai Baht, Indonesian Rupiah), Russian debt default, LTCM hedge fund bailout.",
                "sovereign_rule": "Avoid pegged currencies under speculative attack; trade safe-haven USD & Gold surges; strict stop loss enforcement.",
                "risk_scalar": 0.40,
                "default_action": "MODERATE_PRUDENCE"
            },
            # 4. 2000 Dot-Com Bubble Collapse (2000-2002)
            "2000_DOTCOM_BUBBLE_COLLAPSE": {
                "centroid": np.array([0.32, 0.45, 0.10, -0.25, 0.50, 0.20, 0.25], dtype=float),
                "era": "2000-2002",
                "description": "Speculative tech mania unwind, multi-year valuation contraction, Nasdaq -78%, Fed aggressive easing cycle.",
                "sovereign_rule": "Honor higher-timeframe bearish order blocks; avoid buying unconfirmed dips in speculative high-multiple assets.",
                "risk_scalar": 0.60,
                "default_action": "SELECTIVE_TREND_DISCIPLINE"
            },
            # 5. 2008 Global Financial Crisis (2008-2009)
            "2008_GFC_CREDIT_FREEZE": {
                "centroid": np.array([0.65, 0.40, 0.30, 0.60, 0.95, 0.85, 0.50], dtype=float),
                "era": "2008-2009",
                "description": "Subprime mortgage contagion, Lehman Brothers insolvency, interbank credit freeze, cross-currency basis blowout, multi-asset liquidation.",
                "sovereign_rule": "Survive the initial margin liquidation phase; once central bank quantitative easing begins, ride multi-year Gold & hard asset supercycles.",
                "risk_scalar": 0.20,
                "default_action": "DEFENSIVE_CIRCUIT_BREAKER"
            },
            # 6. 2011 US Debt Downgrade & Eurozone Crisis (2011)
            "2011_US_DEBT_DOWNGRADE_EURO_CRISIS": {
                "centroid": np.array([0.35, 0.18, -0.10, 0.30, 0.55, -0.20, 0.90], dtype=float),
                "era": "2011",
                "description": "US S&P AAA credit rating downgrade, European sovereign debt crisis (PIGS), Gold super-spike to $1,920/oz.",
                "sovereign_rule": "Sovereign debt skepticism powers explosive Gold momentum; trade long Gold with trailing high-water-mark stops.",
                "risk_scalar": 0.70,
                "default_action": "GOLD_EXPANSION_PROTOCOL"
            },
            # 7. 2015 Swiss National Bank EUR/CHF Shock (Jan 2015)
            "2015_SNB_EUR_CHF_PEG_REMOVAL": {
                "centroid": np.array([0.70, 0.25, -0.05, 0.10, 0.90, 0.40, 0.40], dtype=float),
                "era": "2015",
                "description": "Swiss National Bank abruptly abandons 1.20 floor on EUR/CHF; instantaneous 30% collapse, liquidity pulled, retail broker insolvencies.",
                "sovereign_rule": "Never trade near artificial central bank price pegs without guaranteed hard stop loss; monitor broker execution latency.",
                "risk_scalar": 0.20,
                "default_action": "DEFENSIVE_CIRCUIT_BREAKER"
            },
            # 8. 2020 COVID-19 Liquidity Freeze (Feb-Mar 2020)
            "2020_COVID_LIQUIDITY_FREEZE": {
                "centroid": np.array([0.75, 0.35, 0.35, 0.70, 0.95, 0.90, -0.15], dtype=float),
                "era": "2020",
                "description": "Global pandemic lockdown, margin dash for cash, circuit breakers tripped 4 times in 10 days, WTI crude negative (-$37), unlimited Fed QE.",
                "sovereign_rule": "Extreme margin liquidation flushes create once-in-a-decade discount buying opportunities on higher-timeframe Fair Value Gaps and Order Blocks.",
                "risk_scalar": 0.30,
                "default_action": "MODERATE_PRUDENCE"
            },
            # 9. 2022 Fed Aggressive Tightening & Inflation Shock (2022)
            "2022_FED_TIGHTENING_INFLATION_SHOCK": {
                "centroid": np.array([0.28, 0.22, 0.25, -0.80, 0.45, 0.65, -0.05], dtype=float),
                "era": "2022",
                "description": "40-year high inflation, aggressive Fed rate hikes (525 bps), historic bond market crash, 60/40 portfolio breakdown, crypto credit wipeouts.",
                "sovereign_rule": "DXY king during aggressive rate hike cycles; trade with institutional order flow and macro trend pullbacks.",
                "risk_scalar": 0.65,
                "default_action": "MACRO_TREND_ALIGNMENT"
            },
            # 10. 2023-2026 AI Boom, Geopolitical Weaponization & Sovereign De-Dollarization
            "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH": {
                "centroid": np.array([0.20, 0.08, -0.08, -0.20, 0.35, -0.15, 0.80], dtype=float),
                "era": "2023-2026",
                "description": "Maritime chokepoint escalations (Red Sea, Hormuz, Taiwan Strait), weaponization of foreign reserves, global central bank gold accumulation, structural fiscal deficits.",
                "sovereign_rule": "Gold is the premier institutional sovereign asset; exploit discount FVG pullbacks; trade chokepoint escalation safe-haven bids.",
                "risk_scalar": 0.90,
                "default_action": "SOVEREIGN_HARD_ASSET_EXPANSION"
            }
        }

        # Backward compatibility aliases
        self.crisis_archetypes["1971_GOLD_UNPEG_STAGFLATION"] = self.crisis_archetypes["1971_NIXON_SHOCK_STAGFLATION"]
        self.crisis_archetypes["2015_SNB_PEG_REMOVAL"] = self.crisis_archetypes["2015_SNB_EUR_CHF_PEG_REMOVAL"]
        self.crisis_archetypes["2020_COVID_LIQUIDITY_DUMP"] = self.crisis_archetypes["2020_COVID_LIQUIDITY_FREEZE"]
        self.crisis_archetypes["2022_2026_SOVEREIGN_DEBT_DOMINANCE"] = self.crisis_archetypes["2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"]

    def classify_current_regime(
        self,
        realized_vol_annual: float = 0.18,
        current_drawdown_pct: float = 0.03,
        dxy_20d_ret: float = -0.05,
        yield_curve_stress: float = -0.10,
        spread_stress_score: float = 0.25,
        cross_asset_correlation: float = -0.15,
        gold_20d_ret: float = 0.70,
        feature_vector: Optional[Union[np.ndarray, List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Classifies live multi-asset features against 50 years of crises using 7D Cosine Similarity & RBF Distance.
        """
        if feature_vector is not None:
            v = np.array(feature_vector, dtype=float)
            if len(v) == 5:
                # 5-element mapping: [vol, drawdown, dxy, spread, gold] -> expand to 7D
                live_vector = np.array([v[0], v[1], v[2], yield_curve_stress, v[3], cross_asset_correlation, v[4]], dtype=float)
            elif len(v) == 7:
                live_vector = v
            else:
                live_vector = np.pad(v, (0, max(0, 7 - len(v))))[:7]
        else:
            live_vector = np.array([
                realized_vol_annual,
                current_drawdown_pct,
                dxy_20d_ret,
                yield_curve_stress,
                spread_stress_score,
                cross_asset_correlation,
                gold_20d_ret
            ], dtype=float)

        norm_live = float(np.linalg.norm(live_vector))
        best_match = "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"
        highest_composite_sim = -1.0
        all_similarities: Dict[str, float] = {}

        # Canonical primary 10 archetypes
        canonical_archetypes = [
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

        for crisis_name in canonical_archetypes:
            data = self.crisis_archetypes[crisis_name]
            centroid = data["centroid"]
            norm_centroid = float(np.linalg.norm(centroid))

            # 1. Cosine Similarity
            dot_product = float(np.dot(live_vector, centroid))
            cosine_sim = dot_product / (max(norm_live, 1e-7) * max(norm_centroid, 1e-7))
            cosine_sim = float(np.clip(cosine_sim, -1.0, 1.0))

            # 2. Euclidean Distance & Radial Basis Proximity
            euc_dist = float(np.linalg.norm(live_vector - centroid))
            rbf_sim = float(np.exp(-euc_dist / 2.0))

            # 3. Composite Similarity (70% Cosine Angular + 30% RBF Proximity)
            composite_sim = (0.70 * max(cosine_sim, 0.0)) + (0.30 * rbf_sim)
            all_similarities[crisis_name] = round(composite_sim, 4)

            if composite_sim > highest_composite_sim:
                highest_composite_sim = composite_sim
                best_match = crisis_name

        matched_data = self.crisis_archetypes[best_match]

        # Dynamic Risk Scaling Matrix
        is_elevated_stress = (live_vector[0] >= 0.25) or (live_vector[1] >= 0.08) or (live_vector[4] >= 0.40)

        if highest_composite_sim >= 0.75 and best_match in [
            "1987_BLACK_MONDAY_CASCADE", "2008_GFC_CREDIT_FREEZE",
            "2015_SNB_EUR_CHF_PEG_REMOVAL", "2020_COVID_LIQUIDITY_FREEZE"
        ] and is_elevated_stress:
            risk_scalar = 0.20
            action = "DEFENSIVE_CIRCUIT_BREAKER"
        elif highest_composite_sim >= 0.60 and best_match in [
            "1987_BLACK_MONDAY_CASCADE", "2008_GFC_CREDIT_FREEZE",
            "2015_SNB_EUR_CHF_PEG_REMOVAL", "2020_COVID_LIQUIDITY_FREEZE"
        ] and is_elevated_stress:
            risk_scalar = 0.50
            action = "MODERATE_PRUDENCE"
        elif highest_composite_sim >= 0.65 and best_match in [
            "1971_NIXON_SHOCK_STAGFLATION", "2011_US_DEBT_DOWNGRADE_EURO_CRISIS",
            "2023_2026_AI_GEOPOLITICAL_SOVEREIGN_RUSH"
        ]:
            risk_scalar = matched_data["risk_scalar"]
            action = matched_data.get("default_action", "SOVEREIGN_HARD_ASSET_EXPANSION")
        else:
            risk_scalar = 1.00
            action = "NORMAL_SOVEREIGN_EXECUTION"

        return {
            "closest_crisis_regime": best_match,
            "era": matched_data.get("era", "HISTORICAL"),
            "crisis_similarity": round(highest_composite_sim, 4),
            "similarity_pct": round(highest_composite_sim * 100.0, 2),
            "action_protocol": action,
            "risk_scalar": risk_scalar,
            "description": matched_data.get("description", ""),
            "sovereign_rule": matched_data.get("sovereign_rule", ""),
            "all_crisis_similarities": all_similarities
        }
