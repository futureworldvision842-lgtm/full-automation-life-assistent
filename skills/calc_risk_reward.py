"""Dynamic Synthesized Skill: calc_risk_reward"""
import json

MANIFEST = {
    "name": "calc_risk_reward",
    "description": "Auto-synthesized skill for: Calculate risk reward ratio for XAUUSD",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "param1": {"type": "STRING", "description": "Primary input parameter"},
            "value": {"type": "NUMBER", "description": "Numeric value"}
        },
        "required": ["param1"]
    }
}

def run(parameters: dict, player=None, speak=None) -> str:
    param1 = parameters.get("param1", "default")
    val = float(parameters.get("value", 1.0))
    result = f"Executed calc_risk_reward with param1={param1} and val={val * 2}"
    return result
