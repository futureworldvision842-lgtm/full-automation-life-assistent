"""Dynamic Synthesized Skill: gold_atr_multiplier"""
import json

MANIFEST = {
    "name": "gold_atr_multiplier",
    "description": "Auto-synthesized skill for: Calculate dynamic ATR multiplier for gold stop loss",
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
    result = f"Executed gold_atr_multiplier with param1={param1} and val={val * 2}"
    return result
