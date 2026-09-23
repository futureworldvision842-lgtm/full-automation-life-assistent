"""Per-signal validation gate for live execution.

Account readiness says the deployment has earned permission to reach a broker.
It does not prove that a particular signal is supported.  This gate requires a
versioned out-of-sample validation record, cost-adjusted expectancy, calibrated
confidence, independent evidence, and regime support for every live order.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


class SignalQualityGate:
    def __init__(
        self,
        *,
        minimum_oos_trades: int = 100,
        minimum_profit_factor: float = 1.20,
        maximum_validation_drawdown_pct: float = 4.0,
        minimum_estimated_reward_risk: float = 1.50,
        maximum_brier_score: float = 0.25,
        minimum_independent_evidence: int = 3,
    ):
        self.minimum_oos_trades = int(minimum_oos_trades)
        self.minimum_profit_factor = float(minimum_profit_factor)
        self.maximum_validation_drawdown_pct = float(maximum_validation_drawdown_pct)
        self.minimum_estimated_reward_risk = float(minimum_estimated_reward_risk)
        self.maximum_brier_score = float(maximum_brier_score)
        self.minimum_independent_evidence = int(minimum_independent_evidence)

    @staticmethod
    def _finite_number(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def evaluate(self, market_context: Optional[Dict[str, Any]], *, live: bool) -> Tuple[bool, List[str]]:
        if not live:
            return True, []
        if not isinstance(market_context, dict):
            return False, ["Live order has no market context for signal validation"]
        quality = market_context.get("signal_quality")
        if not isinstance(quality, dict):
            return False, ["Signal-quality evidence is missing"]

        reasons: List[str] = []
        for field in ("validation_id", "strategy_id", "strategy_version", "validation_dataset_hash"):
            if not str(quality.get(field, "")).strip():
                reasons.append(f"Signal quality is missing {field}")

        oos_trades = self._finite_number(quality.get("out_of_sample_trades"))
        if oos_trades is None or oos_trades < self.minimum_oos_trades:
            reasons.append(f"Out-of-sample trades are below {self.minimum_oos_trades}")

        profit_factor = self._finite_number(quality.get("out_of_sample_profit_factor"))
        if profit_factor is None or profit_factor < self.minimum_profit_factor:
            reasons.append(f"Out-of-sample profit factor is below {self.minimum_profit_factor:.2f}")

        drawdown = self._finite_number(quality.get("validation_max_drawdown_pct"))
        if drawdown is None or drawdown < 0 or drawdown > self.maximum_validation_drawdown_pct:
            reasons.append(f"Validation drawdown exceeds {self.maximum_validation_drawdown_pct:.2f}% or is missing")

        reward_risk = self._finite_number(quality.get("estimated_reward_risk_after_costs"))
        if reward_risk is None or reward_risk < self.minimum_estimated_reward_risk:
            reasons.append(f"Cost-adjusted reward:risk is below {self.minimum_estimated_reward_risk:.2f}")

        expectancy = self._finite_number(quality.get("cost_adjusted_expectancy_r"))
        if expectancy is None or expectancy <= 0:
            reasons.append("Cost-adjusted expectancy is not positive")

        brier = self._finite_number(quality.get("calibration_brier_score"))
        if brier is None or brier < 0 or brier > self.maximum_brier_score:
            reasons.append(f"Probability calibration Brier score exceeds {self.maximum_brier_score:.2f} or is missing")

        evidence = quality.get("independent_evidence")
        unique_evidence = {
            str(item).strip().lower()
            for item in evidence
            if str(item).strip()
        } if isinstance(evidence, list) else set()
        if len(unique_evidence) < self.minimum_independent_evidence:
            reasons.append(f"Fewer than {self.minimum_independent_evidence} independent evidence sources are present")

        if quality.get("regime_supported") is not True:
            reasons.append("Current regime is not explicitly supported by validation")
        if quality.get("duplicate_signal") is not False:
            reasons.append("Duplicate-signal check is missing or failed")
        if quality.get("lookahead_bias_check_passed") is not True:
            reasons.append("Look-ahead-bias check is missing or failed")
        if quality.get("cost_model_verified") is not True:
            reasons.append("Spread/commission/slippage cost model is unverified")

        return not reasons, list(dict.fromkeys(reasons))

