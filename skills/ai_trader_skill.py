"""
skills/ai_trader_skill.py — HKUDS AI-Trader Cooperative Multi-Agent & Risk Skill
=============================================================================
Dynamic skill providing J.A.R.V.I.S. with autonomous quantitative intelligence:
  - Cooperative multi-agent analysis (Macro Analyst, Order Flow Scout, Stat Arb)
  - Vectorized Alpha formula mining and Qlib factor evaluation
  - Deterministic 18-gate prop-firm risk admission (<= 0.75% / $750 cap on #40000294403)
  - Dynamic +1.0R breakeven lock enforcement

Exposes:
  - MANIFEST and run(parameters) for skills/loader.py
  - HERMES_SCHEMA and HERMES_AI_TRADER_TOOLS for brain/hermes_agent.py

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import json
import logging
from typing import Dict, Any, Optional, List

from trading.ai_trader.coordinator import AITraderCoordinator, get_ai_trader_coordinator
from trading.ai_trader.alpha_miner import AITraderAlphaMiner
from trading.risk_kernel.admission_kernel import get_risk_kernel

logger = logging.getLogger("skills.ai_trader_skill")

# =============================================================================
# GEMINI SKILL LOADER MANIFEST (skills/loader.py compliance)
# =============================================================================

MANIFEST: Dict[str, Any] = {
    "name": "ai_trader",
    "description": (
        "HKUDS AI-Trader multi-agent quantitative analyst and deterministic prop-firm risk gating. "
        "Coordinates Macro Analyst, Order Flow Scout, and Stat Arb roles, evaluates alpha factors, "
        "and enforces <= 0.75% / $750 max risk cap on FundingPips #40000294403."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["analyze", "admit_order", "mine_alphas", "risk_parameters", "status"],
                "description": "AI-Trader operation: analyze (multi-agent consensus), admit_order (18-gate prop risk check), mine_alphas, risk_parameters, or status."
            },
            "symbol": {
                "type": "STRING",
                "description": "Ticker symbol (e.g. XAUUSD, EURUSD, GBPUSD, BTCUSD, ETHUSD, SOLUSD)."
            },
            "order": {
                "type": "OBJECT",
                "description": "Order dictionary for admit_order action (symbol, direction, entry_price, sl, tp, lot_size)."
            },
            "count": {
                "type": "INTEGER",
                "description": "Number of alpha factors to mine."
            }
        },
        "required": ["action"]
    }
}


def run(parameters: Optional[Dict[str, Any]] = None, player=None, speak=None) -> str:
    """
    Skill entry point for skills/loader.py dynamic registry.
    """
    params = parameters or {}
    action = str(params.get("action") or "status").lower().strip()
    symbol = str(params.get("symbol") or "XAUUSD").upper().strip()

    coordinator = get_ai_trader_coordinator()
    kernel = get_risk_kernel()

    if action == "status":
        risk_params = kernel.get_risk_parameters("40000294403")
        res = {
            "status": "ACTIVE",
            "subsystem": "HKUDS AI-Trader",
            "account_id": "40000294403",
            "max_risk_cap_usd": risk_params["max_risk_cap"],
            "max_risk_pct": risk_params["risk_pct"],
            "min_rr_ratio": risk_params["min_rr"],
            "dynamic_be_trigger_r": risk_params["dynamic_be_r"],
            "multi_agent_roles": ["MacroQuantitativeAnalyst", "HighFrequencyOrderFlowScout", "StatisticalArbitrageur"]
        }
        if speak and callable(speak):
            speak("AI Trader system active and risk kernel armed.")
        return json.dumps(res, indent=2)

    elif action == "analyze":
        consensus = coordinator.analyze_and_synthesize(symbol, params.get("datahub_snapshot"))
        res = consensus.to_dict()
        if speak and callable(speak):
            speak(f"AI Trader analysis for {symbol}: {consensus.direction} with confluence {consensus.confluence_score:.1f}")
        return json.dumps(res, indent=2)

    elif action == "admit_order":
        order_data = params.get("order") or {
            "symbol": symbol,
            "direction": params.get("direction", "BUY"),
            "entry_price": params.get("entry_price"),
            "sl": params.get("sl"),
            "tp": params.get("tp"),
            "lot_size": params.get("lot_size", 0.10)
        }
        admission = kernel.admit_order(order_data)
        if speak and callable(speak):
            speak(f"Order admission result: {admission['decision']}")
        return json.dumps(admission, indent=2)

    elif action == "mine_alphas":
        miner = AITraderAlphaMiner()
        cand = miner.generate_candidate_formula(symbol, params.get("asset_class", "Forex"))
        return json.dumps(cand, indent=2)

    elif action == "risk_parameters":
        acc = params.get("account_id", "40000294403")
        res = kernel.get_risk_parameters(acc)
        return json.dumps(res, indent=2)

    else:
        return json.dumps({
            "status": "ERROR",
            "message": f"Unknown action '{action}'. Valid actions: analyze, admit_order, mine_alphas, risk_parameters, status."
        })


# =============================================================================
# NOUS HERMES-3 TOOL SCHEMAS (brain/hermes_agent.py compliance)
# =============================================================================

HERMES_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ai_trader_risk_gate",
        "description": "Deterministic 18-gate admission kernel for AI-Trader setups enforcing <= 0.75% / $750 cap and RR >= 2.5.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol"},
                "direction": {"type": "string", "enum": ["BUY", "SELL"], "description": "Order direction"},
                "entry_price": {"type": "number", "description": "Limit/Market entry price"},
                "sl": {"type": "number", "description": "Stop Loss price level"},
                "tp": {"type": "number", "description": "Take Profit price level"},
                "lot_size": {"type": "number", "description": "Proposed lot size"},
                "account_id": {"type": "string", "description": "Account number, e.g. 40000294403"}
            },
            "required": ["symbol", "direction", "entry_price", "sl", "tp"]
        }
    }
}

HERMES_AI_TRADER_TOOLS: List[Dict[str, Any]] = [
    HERMES_SCHEMA,
    {
        "type": "function",
        "function": {
            "name": "ai_trader_alpha_miner",
            "description": "Mine formulaic alpha expressions using local zero-cost Ollama (qwen2.5:0.5b) or deterministic template bank.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Asset ticker (e.g. XAUUSD, EURUSD, BTCUSD)"},
                    "asset_class": {"type": "string", "enum": ["Forex", "Gold", "Crypto"], "description": "Target asset class"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ai_trader_coordinator",
            "description": "Multi-agent consensus evaluation across Macro, Order Flow, and Stat Arb virtual agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Target ticker symbol"}
                },
                "required": ["symbol"]
            }
        }
    }
]


def get_hermes_schema() -> Dict[str, Any]:
    """Returns OpenAI/Hermes tool definition schema."""
    return HERMES_SCHEMA
