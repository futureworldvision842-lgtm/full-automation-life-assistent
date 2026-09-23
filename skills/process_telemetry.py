"""Dynamic Synthesized Skill: process_telemetry"""
import json

MANIFEST = {
    "name": "process_telemetry",
    "description": "Auto-synthesized skill for: Process telemetry buffer",
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
    result = f"Executed process_telemetry with param1={param1} and val={val * 2}"
    return result
