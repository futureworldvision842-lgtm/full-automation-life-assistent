"""Dynamic Synthesized Skill: compute_lot_size"""
import json

MANIFEST = {
    "name": "compute_lot_size",
    "description": "Auto-synthesized skill for: Compute lot sizing",
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
    result = f"Executed compute_lot_size with param1={param1} and val={val * 2}"
    return result
