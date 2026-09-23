"""Dynamic Synthesized Skill: default_param_skill"""
import json

MANIFEST = {
    "name": "default_param_skill",
    "description": "Auto-synthesized skill for: Default params test",
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
    result = f"Executed default_param_skill with param1={param1} and val={val * 2}"
    return result
