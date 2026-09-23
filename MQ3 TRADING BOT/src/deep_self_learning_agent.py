"""
deep_self_learning_agent.py — FinMem 3-Tier Cognitive Self-Learning & Strategy Evolution Engine.
Implements Working, Episodic, and Semantic Memory layers for continuous autonomous strategy mutation.

Memory Layers:
  1. Working Memory: Live tick stream, spread expansion, and session killzones.
  2. Episodic Memory: Rich trade forensics, win/loss retrospectives, and experience replay buffer.
  3. Semantic Memory: Immutable institutional rules, prop firm defense limits, and market maker trap patterns.
"""

import json
import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("DeepSelfLearningAgent")


class DeepSelfLearningAgent:
    """
    FinMem 3-Tier Cognitive Self-Learning AI Agent.
    Implements formal Beta-Binomial conjugate Bayesian pattern weight updates.
    """

    _lock = threading.RLock()

    def __init__(self, memory_dir: str = "data/cognitive_memory"):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        self.episodic_path = os.path.join(self.memory_dir, "episodic_memory.json")
        self.semantic_path = os.path.join(self.memory_dir, "semantic_memory.json")

        self.working_memory: Dict[str, Any] = {}
        self.episodic_memory: List[Dict[str, Any]] = self._load_json(self.episodic_path, default=[])
        self.semantic_memory: Dict[str, Any] = self._load_json(self.semantic_path, default=self._default_semantic())

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: str, data: Any):
        """Thread-safe atomic JSON file writing with temporary file replacement."""
        with self._lock:
            try:
                temp_path = f"{path}.{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                for _ in range(5):
                    try:
                        os.replace(temp_path, path)
                        break
                    except Exception:
                        time.sleep(0.01)
                else:
                    # Direct fallback if replace failed
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving cognitive memory to {path}: {e}")

    def _default_semantic(self) -> Dict[str, Any]:
        return {
            "immutable_rules": [
                "Always enforce 1:1 R:R Breakeven lock before letting runners float.",
                "Never short Gold on Bullish Macro expansion days.",
                "Never enter during 15-minute high-impact economic news window.",
                "De-risk lot sizing by 50% once daily profit target ($400+) is banked."
            ],
            "pattern_confidence_weights": {
                "M15_ORDER_BLOCK_RETEST": 1.35,
                "OTE_705_FIBONACCI": 1.40,
                "ASIAN_JUDAS_SWEEP": 1.45,
                "CVD_DELTA_ABSORPTION": 1.30,
                "DARK_POOL_ACCUMULATION": 1.38
            },
            "bayesian_priors": {
                "M15_ORDER_BLOCK_RETEST": {"alpha": 4.769, "beta": 1.539, "expected_theta": 0.756, "weight": 1.35},
                "OTE_705_FIBONACCI": {"alpha": 5.154, "beta": 1.154, "expected_theta": 0.817, "weight": 1.40},
                "ASIAN_JUDAS_SWEEP": {"alpha": 5.538, "beta": 0.770, "expected_theta": 0.878, "weight": 1.45},
                "CVD_DELTA_ABSORPTION": {"alpha": 4.385, "beta": 1.923, "expected_theta": 0.695, "weight": 1.30},
                "DARK_POOL_ACCUMULATION": {"alpha": 5.000, "beta": 1.308, "expected_theta": 0.793, "weight": 1.38}
            }
        }

    def update_working_memory(self, symbol: str, current_price: float, killzone: str, spread_pts: float):
        """Updates real-time working memory layer."""
        self.working_memory = {
            "symbol": symbol,
            "current_price": current_price,
            "killzone": killzone,
            "spread_points": spread_pts,
            "timestamp": time.time()
        }

    def bayesian_update_pattern(self, pattern_name: str, outcome: str, profit: float = 0.0) -> Dict[str, Any]:
        """
        Beta-Binomial Conjugate Bayesian Pattern Weight Updating:
          alpha_post = alpha_prior + (outcome == 'WIN')
          beta_post = beta_prior + (outcome == 'LOSS')
          E[theta] = alpha_post / (alpha_post + beta_post)
          w_new = clamp(0.65 + 0.95 * E[theta], 0.65, 1.60)
        """
        with self._lock:
            priors = self.semantic_memory.setdefault("bayesian_priors", {})
            weights = self.semantic_memory.setdefault("pattern_confidence_weights", {})

            prior = priors.get(pattern_name)
            if not prior:
                # Initialize prior calibrated to existing weight
                curr_w = weights.get(pattern_name, 1.125)
                theta_0 = max(0.01, min(0.99, (curr_w - 0.65) / 0.95))
                alpha_prior = round(theta_0 * 6.308, 3)
                beta_prior = round((1.0 - theta_0) * 6.308, 3)
            else:
                alpha_prior = float(prior.get("alpha", 5.0))
                beta_prior = float(prior.get("beta", 1.3))

            outcome_clean = outcome.strip().upper()
            is_win = (outcome_clean == "WIN") or (profit > 0 and outcome_clean != "LOSS")
            is_loss = (outcome_clean == "LOSS") or (profit < 0 and outcome_clean != "WIN")

            alpha_post = alpha_prior + (1.0 if is_win else 0.0)
            beta_post = beta_prior + (1.0 if is_loss else 0.0)

            expected_theta = alpha_post / (alpha_post + beta_post)
            w_raw = 0.65 + 0.95 * expected_theta
            w_new = round(min(1.60, max(0.65, w_raw)), 3)

            priors[pattern_name] = {
                "alpha": round(alpha_post, 2),
                "beta": round(beta_post, 2),
                "expected_theta": round(expected_theta, 4),
                "weight": w_new
            }
            weights[pattern_name] = w_new

            self._save_json(self.semantic_path, self.semantic_memory)

        return {
            "pattern": pattern_name,
            "outcome": outcome,
            "alpha": alpha_post,
            "beta": beta_post,
            "expected_theta": expected_theta,
            "weight": w_new,
            "profit": profit
        }

    def record_episodic_experience(
        self,
        symbol: str,
        direction: str,
        pnl: float,
        pattern: str,
        reason: str,
        regime: str
    ) -> Dict[str, Any]:
        """
        Records a completed trade into episodic memory and triggers Bayesian cognitive reflection.
        """
        is_win = pnl > 0
        experience = {
            "symbol": symbol,
            "direction": direction,
            "pnl": round(pnl, 2),
            "is_win": is_win,
            "pattern": pattern,
            "reason": reason,
            "regime": regime,
            "timestamp": datetime.now().isoformat()
        }
        with self._lock:
            self.episodic_memory.append(experience)
            if len(self.episodic_memory) > 500:
                self.episodic_memory.pop(0)
            self._save_json(self.episodic_path, self.episodic_memory)

        # Reflect & Evolve Pattern Weight via Beta-Binomial Conjugate Bayesian Updating
        outcome_str = "WIN" if is_win else "LOSS"
        bayes_res = self.bayesian_update_pattern(pattern, outcome_str, profit=pnl)
        new_w = bayes_res["weight"]

        logger.info(f"[FinMem Cognitive AI] Trade reflected: {symbol} PnL ${pnl:+.2f} | Pattern '{pattern}' Beta-Binomial weight tuned to {new_w}x (alpha={bayes_res['alpha']:.1f}, beta={bayes_res['beta']:.1f}, E[theta]={bayes_res['expected_theta']:.3f})")
        return {
            "status": "EPISODIC_EXPERIENCE_INTEGRATED",
            "is_win": is_win,
            "new_pattern_weight": new_w,
            "total_memories": len(self.episodic_memory),
            "bayesian_update": bayes_res
        }

    def get_cognitive_ai_summary(self) -> Dict[str, Any]:
        """Returns full cognitive memory status and learned weights."""
        with self._lock:
            total = len(self.episodic_memory)
            wins = sum(1 for e in self.episodic_memory if e.get("is_win"))
            win_rate = (wins / max(total, 1)) * 100.0 if total > 0 else 100.0
            pattern_weights = dict(self.semantic_memory.get("pattern_confidence_weights", {}))
            rules_count = len(self.semantic_memory.get("immutable_rules", []))
            priors = dict(self.semantic_memory.get("bayesian_priors", {}))

        return {
            "total_episodic_experiences": total,
            "win_rate_pct": round(win_rate, 1),
            "pattern_weights": pattern_weights,
            "bayesian_priors": priors,
            "semantic_rules_count": rules_count,
            "cognitive_state": "AUTONOMOUS_LEARNING_ACTIVE"
        }
