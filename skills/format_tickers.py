"""Dynamic Synthesized Skill: format_tickers"""
import json

MANIFEST = {
    "name": "format_tickers",
    "description": "Auto-synthesized skill for: Format crypto tickers v2 with volume",
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
    result = f"Executed format_tickers with param1={param1} and val={val * 2}"
    return result
