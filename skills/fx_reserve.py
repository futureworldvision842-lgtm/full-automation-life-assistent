"""Dynamic Synthesized Skill: fx_reserve"""
import json

MANIFEST = {
    "name": "fx_reserve",
    "description": "Auto-synthesized skill for: Check foreign exchange reserve",
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
    result = f"Executed fx_reserve with param1={param1} and val={val * 2}"
    return result
