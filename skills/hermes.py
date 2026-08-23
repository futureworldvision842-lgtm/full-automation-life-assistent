"""
hermes — delegate a task to the Hermes Agent (Nous Research) from Jarvis.

Hermes is a full autonomous agent (100+ tools, memory, swarms). This skill lets
Jarvis hand a complex task to Hermes and speak back the result.

Note: Hermes needs its own provider auth — run `hermes login` / `hermes setup`
once in a terminal if it reports no model configured.
"""
import json
import os
import subprocess
from pathlib import Path

HERMES_EXE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\hermes.exe")
# Fallback to the absolute user path (LOCALAPPDATA can differ under packaged hosts).
if not os.path.exists(HERMES_EXE):
    HERMES_EXE = r"C:\Users\HP\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe"

HERMES_MODEL = os.getenv("JARVIS_HERMES_MODEL", "gpt-5.6-terra")
HERMES_PROVIDER = os.getenv("JARVIS_HERMES_PROVIDER", "openai-codex")
HERMES_LOCAL_URL = os.getenv("JARVIS_HERMES_LOCAL_URL", "http://127.0.0.1:11434/v1")


def _gemini_key():
    try:
        cfg = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        return json.loads(cfg.read_text(encoding="utf-8")).get("gemini_api_key")
    except Exception:
        return None

MANIFEST = {
    "name": "hermes",
    "description": (
        "Delegate a complex/agentic task to the Hermes Agent (autonomous agent with "
        "100+ tools, memory, web, code). Use for deep multi-step jobs beyond Jarvis's "
        "built-in tools. Pass the full task as 'task'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "The task/prompt to hand to Hermes."}
        },
        "required": ["task"],
    },
}


def run(parameters=None, player=None, speak=None):
    parameters = parameters or {}
    task = (parameters.get("task") or "").strip()
    if not task:
        return "Sir, what task should I delegate to Hermes?"
    if not os.path.exists(HERMES_EXE):
        return "Hermes is not installed. Run the Hermes installer first."

    if player is not None:
        try:
            player.write_log(f"HERMES: delegating task -> {task[:60]}")
        except Exception:
            pass
    # Run Hermes with Jarvis's working Gemini key + a Gemini model so it works
    # regardless of Hermes's own saved config.
    env = dict(os.environ)
    key = _gemini_key()
    if key:
        env["GEMINI_API_KEY"] = key
        env["GOOGLE_API_KEY"] = key
    if HERMES_PROVIDER == "custom":
        env["OPENAI_BASE_URL"] = HERMES_LOCAL_URL
        env["OPENAI_API_KEY"] = "ollama"
    try:
        command = [
            HERMES_EXE, "-z", task,
            "--provider", HERMES_PROVIDER,
            "--model", HERMES_MODEL,
            "--toolsets", os.getenv(
                "JARVIS_HERMES_TOOLSETS",
                "browser,clarify,memory,session_search,skills,todo",
            ),
            "--cli",
        ]
        # Full unattended tool approval is intentionally opt-in.  The mobile app
        # must never turn a delegated research request into hidden system control.
        if os.environ.get("JARVIS_HERMES_UNSAFE_AUTONOMY") == "1":
            command.insert(-1, "--yolo")
        r = subprocess.run(
            command,
            capture_output=True, text=True, timeout=300,
            cwd=os.path.dirname(HERMES_EXE), env=env,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if not out and err:
            return f"Hermes error: {err[:300]}"
        return out[:2000] or "Hermes finished with no output."
    except subprocess.TimeoutExpired:
        return "Hermes is still working on that long task; it timed out at 5 minutes."
    except Exception as e:
        return f"Failed to run Hermes: {e}"
