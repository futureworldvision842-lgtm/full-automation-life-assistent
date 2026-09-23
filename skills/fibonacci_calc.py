"""Dynamic Synthesized Skill: fibonacci_calc"""
import json

MANIFEST = {
    "name": "fibonacci_calc",
    "description": "Auto-synthesized skill for: Compute fibonacci series",
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
    result = f"Executed fibonacci_calc with param1={param1} and val={val * 2}"
    return result
