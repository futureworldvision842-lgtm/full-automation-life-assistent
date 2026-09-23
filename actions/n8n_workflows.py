"""
actions/n8n_workflows.py
========================================================================
JARVIS Action Wrapper for n8n Workflow Automation Engine.
"""

from typing import Dict, Any, Optional
from integrations.n8n_engine import get_n8n_engine


def n8n_workflows(params: Optional[Dict[str, Any]] = None) -> str:
    """Dispatches workflow actions and queries to the n8n Workflow Engine."""
    params = params or {}
    action = str(params.get("action", "list")).lower()
    workflow_id = str(params.get("workflow_id") or params.get("id") or "").strip()
    payload = params.get("payload", {})
    
    engine = get_n8n_engine()
    
    if action in ("list", "workflows", "all"):
        flows = engine.list_workflows()
        res = "=== ? J.A.R.V.I.S. N8N WORKFLOW AUTOMATIONS ===\n"
        for f in flows:
            res += f"? [{f['id']}] {f['name']} (Runs: {f['execution_count']})\n"
            res += f"  Trigger: {f['trigger']} | Last: {f['last_run'] or 'Never'}\n"
            res += f"  Description: {f['description']}\n\n"
        return res
        
    elif action in ("trigger", "run", "exec"):
        if not workflow_id:
            return "?? Error: Please provide a workflow_id (e.g. 'macro_briefing', 'whale_flow', 'news_circuit_breaker')."
        res = engine.trigger_workflow(workflow_id, payload)
        import json
        return f"=== ? N8N WORKFLOW EXECUTION: {workflow_id} ===\n{json.dumps(res, indent=2)}"
        
    elif action in ("health", "status"):
        h = engine.check_n8n_server_health()
        return f"=== N8N ENGINE STATUS ===\nStatus: {'ONLINE' if h.get('online') else 'OFFLINE'}\nMode: {h.get('mode')}\nHost: {h.get('url')}"
        
    return f"Unknown n8n action '{action}'. Available: list, trigger <workflow_id>, health."
