"""Mission memory, property registry and daily report access for JARVIS."""

from memory.mission_memory import (
    build_prompt_context,
    latest_daily_report,
    properties,
    recall,
    remember,
)


MANIFEST = {
    "name": "mission_control",
    "description": "Recall the founder mission, list authorized sites, store an owner-approved mission fact, or read the latest daily mission report.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "context | sites | remember | recall | daily_report"},
            "text": {"type": "STRING", "description": "Fact to remember or recall query."},
            "category": {"type": "STRING", "description": "Memory category when remembering."},
        },
        "required": ["action"],
    },
}


def run(parameters=None, player=None, speak=None):
    values = parameters or {}
    action = str(values.get("action") or "context").strip().lower()
    text = str(values.get("text") or "").strip()
    if action == "sites":
        rows = properties()
        return "\n".join(f"{item.get('name')}: {item.get('url')} — {item.get('control')}" for item in rows) or "No properties registered."
    if action == "remember":
        if not text:
            return "Tell me the mission fact to remember."
        memory_id = remember(text, category=str(values.get("category") or "mission"), source="owner-command")
        return f"Mission memory #{memory_id} stored locally with its source."
    if action == "recall":
        rows = recall(text, limit=8)
        return "\n".join(f"[{item['category']}] {item['text']} (source: {item['source']})" for item in rows) or "No matching mission memory yet."
    if action == "daily_report":
        return latest_daily_report() or "No daily mission report has been created yet."
    return build_prompt_context(text)

