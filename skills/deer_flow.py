"""
deer_flow — delegate DEEP RESEARCH to DeerFlow (bytedance/deer-flow) from Jarvis.

DeerFlow is a multi-agent deep-research framework (planner, researcher, coder,
reporter) — installed at E:\\jarvis\\bots\\deer-flow, configured to use the
Boss's Gemini key + DuckDuckGo search (no extra API keys needed).

This skill:
  1. Starts the DeerFlow gateway (port 8001) if it isn't running.
  2. Reports the console URL so the Boss can watch the research live.
  3. (Runtime-discovers the API where possible.)
"""
import json
import os
import subprocess
import time
import urllib.request

DEER = r"E:\jarvis\bots\deer-flow"
BACKEND = os.path.join(DEER, "backend")
UV = os.path.expandvars(r"%LOCALAPPDATA%\hermes\bin\uv.exe")
if not os.path.exists(UV):
    UV = "uv"
PORT = 8001
NEW_CONSOLE = 0x00000010

MANIFEST = {
    "name": "deer_flow",
    "description": (
        "Delegate a DEEP RESEARCH task to DeerFlow — a multi-agent research "
        "framework (planner → researchers → reporter) that browses the web and "
        "produces detailed reports. Use when Boss asks for deep/thorough research, "
        "a report, market/topic analysis, or 'deer flow'. Actions: start (boot the "
        "server & give console URL), status, research (submit a question)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start | status | research (default: research)"},
            "query": {"type": "STRING", "description": "The research question/task."},
        },
        "required": [],
    },
}


def _up() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/models", timeout=3) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return True   # server answered (e.g. 401 with auth on) — it's up
    except Exception:
        return False


def _installed() -> bool:
    return os.path.exists(os.path.join(BACKEND, ".venv"))


def _start_server() -> str:
    if _up():
        return "already running"
    if not _installed():
        return "not installed yet (dependencies still downloading — try again in a few minutes)"
    env = os.environ.copy()
    env.update({"PYTHONPATH": ".", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                "DEER_FLOW_PROJECT_ROOT": DEER,
                # local single-user gateway on 127.0.0.1 — no login screen
                "DEER_FLOW_AUTH_DISABLED": "1",
                # keep uv's python + cache on E: (C: is nearly full)
                "UV_CACHE_DIR": r"E:\uv_cache",
                "UV_PYTHON_INSTALL_DIR": r"E:\uv_python"})
    subprocess.Popen(
        [UV, "run", "uvicorn", "app.gateway.app:app", "--host", "127.0.0.1",
         "--port", str(PORT)],
        cwd=BACKEND, env=env, creationflags=NEW_CONSOLE)
    for _ in range(30):
        time.sleep(2)
        if _up():
            return "started"
    return "start attempted — server not answering yet (it may still be warming up)"


def run(parameters=None, player=None, speak=None):
    p = parameters or {}
    action = (p.get("action") or "research").strip().lower()
    query = (p.get("query") or "").strip()

    if action == "status":
        if _up():
            return f"DeerFlow is ONLINE, Sir — console at http://127.0.0.1:{PORT}."
        if not _installed():
            return "DeerFlow is installed at E:\\jarvis\\bots\\deer-flow but its dependencies are still being set up, Sir."
        return "DeerFlow is installed but not running, Sir. Say 'start deer flow' to boot it."

    state = _start_server()
    if "not installed" in state:
        return f"DeerFlow: {state}, Sir."

    base = f"DeerFlow gateway {state} — console: http://127.0.0.1:{PORT}"
    if action == "start" or not query:
        return f"{base}. Give me a research question and I'll hand it over, Sir."

    # Best-effort research submission (API is thread-based; if the exact route
    # isn't available in this build, the Boss can drive it from the console).
    try:
        data = json.dumps({"content": query}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/api/threads", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            tid = json.loads(r.read()).get("id") or json.loads(r.read()).get("thread_id")
        if tid:
            return (f"Research thread created on DeerFlow (id {tid}), Sir. "
                    f"Watch it live at http://127.0.0.1:{PORT}. Topic: {query}")
    except Exception:
        pass
    return (f"{base}. I couldn't auto-submit via API in this build, Sir — open the "
            f"console and paste the question, or let me research it myself with "
            f"web_search + hermes meanwhile. Topic noted: {query}")


if __name__ == "__main__":
    print(run({"action": "status"}))
