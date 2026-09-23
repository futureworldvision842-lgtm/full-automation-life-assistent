"""
experiential_replay_engine.py — Deep Prioritized Experience Replay (PER) & Self-Evolving Engine.
Inspired by Reinforcement Learning (FinRL / Deep Q-Learning) Experience Replay Buffers.

Capabilities:
  1. Stores rich forensic trade execution records (State, Action, Reward, Macro Context).
  2. Autonomous online Bayesian weight optimization.
  3. Dynamic pattern reinforcement & self-healing after every closed trade.
"""

import json
import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("ExperientialReplay")


class ExperientialReplayEngine:
    """
    Self-Learning & Experiential Replay Engine.
    Continuously optimizes setup weights using Beta-Binomial conjugate Bayesian updating.
    """

    _lock = threading.RLock()

    def __init__(self, db_path: str = "data/experience_replay_db.json", max_memory_size: int = 1000):
        self.db_path = db_path
        self.max_memory_size = max_memory_size
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.memory = self._load_db()

    def _load_db(self) -> Dict[str, Any]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_experiences": 0,
            "win_count": 0,
            "loss_count": 0,
            "pattern_rewards": {},
            "bayesian_priors": {},
            "trade_experiences": []
        }

    def _save_db(self):
        """Thread-safe atomic JSON file writing with temporary file replacement."""
        with self._lock:
            try:
                temp_path = f"{self.db_path}.{os.getpid()}_{threading.get_ident()}_{time.time_ns()}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.memory, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                for _ in range(5):
                    try:
                        os.replace(temp_path, self.db_path)
                        break
                    except Exception:
                        time.sleep(0.01)
                else:
                    with open(self.db_path, "w", encoding="utf-8") as f:
                        json.dump(self.memory, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving experience replay DB: {e}")

    def bayesian_update_pattern(self, pattern_name: str, outcome: str, profit: float = 0.0) -> Dict[str, Any]:
        """
        Beta-Binomial Conjugate Bayesian Pattern Weight Updating:
          alpha_post = alpha_prior + (outcome == 'WIN')
          beta_post = beta_prior + (outcome == 'LOSS')
          E[theta] = alpha_post / (alpha_post + beta_post)
          w_new = clamp(0.65 + 0.95 * E[theta], 0.65, 1.60)
        """
        with self._lock:
            priors = self.memory.setdefault("bayesian_priors", {})
            p_stats = self.memory.setdefault("pattern_rewards", {}).setdefault(
                pattern_name, {"wins": 0, "losses": 0, "weight": 1.0}
            )

            prior = priors.get(pattern_name)
            if not prior:
                curr_w = p_stats.get("weight", 1.125)
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
            p_stats["weight"] = w_new

            self._save_db()

        return {
            "pattern": pattern_name,
            "outcome": outcome,
            "alpha": alpha_post,
            "beta": beta_post,
            "expected_theta": expected_theta,
            "weight": w_new,
            "profit": profit
        }

    def record_trade_experience(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl_dollar: float,
        pattern_type: str,
        macro_regime: str,
        confluence_score: float
    ) -> Dict[str, Any]:
        """
        Records a completed trade into the prioritized experience replay buffer and optimizes pattern weights.
        """
        is_win = pnl_dollar > 0
        reward = 1.0 if is_win else -1.2  # Slightly asymmetric penalty for losses

        experience = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_dollar": round(pnl_dollar, 2),
            "is_win": is_win,
            "reward": reward,
            "pattern_type": pattern_type,
            "macro_regime": macro_regime,
            "confluence_score": confluence_score,
            "timestamp": datetime.now().isoformat()
        }

        with self._lock:
            self.memory["trade_experiences"].append(experience)
            if len(self.memory["trade_experiences"]) > self.max_memory_size:
                self.memory["trade_experiences"].pop(0)

            self.memory["total_experiences"] += 1
            if is_win:
                self.memory["win_count"] += 1
            else:
                self.memory["loss_count"] += 1

            p_stats = self.memory.setdefault("pattern_rewards", {}).setdefault(
                pattern_type, {"wins": 0, "losses": 0, "weight": 1.0}
            )
            if is_win:
                p_stats["wins"] += 1
            else:
                p_stats["losses"] += 1

        # Online Beta-Binomial Conjugate Bayesian Pattern Weight Update
        outcome_str = "WIN" if is_win else "LOSS"
        bayes_res = self.bayesian_update_pattern(pattern_type, outcome_str, profit=pnl_dollar)
        new_weight = bayes_res["weight"]

        logger.info(f"[Experience Replay] Logged trade: {symbol} {direction} PnL: ${pnl_dollar:+.2f} | Pattern '{pattern_type}' Bayesian Weight updated to {new_weight}x (alpha={bayes_res['alpha']:.1f}, beta={bayes_res['beta']:.1f})")

        return {
            "status": "EXPERIENCE_RECORDED",
            "is_win": is_win,
            "new_pattern_weight": new_weight,
            "total_experiences": self.memory["total_experiences"],
            "bayesian_update": bayes_res
        }

    def get_pattern_weight(self, pattern_type: str) -> float:
        """Returns the self-learned weight multiplier for a given pattern."""
        with self._lock:
            return self.memory.get("pattern_rewards", {}).get(pattern_type, {}).get("weight", 1.0)
