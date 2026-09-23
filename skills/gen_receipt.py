"""Dynamic Synthesized Skill: gen_receipt"""
import json

MANIFEST = {
    "name": "gen_receipt",
    "description": "Auto-synthesized skill for: Generate automated trading receipt",
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
    result = f"Executed gen_receipt with param1={param1} and val={val * 2}"
    return result
