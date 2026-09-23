"""
actions/ollama_odysseus.py
========================================================================
J.A.R.V.I.S. Local AI Manager (Ollama & Odysseus Integration).
Manages the configured local Ollama models (Jarvis-owned port 11435)
and Odysseus AI Server (http://localhost:7000) with zero external cost.
========================================================================
"""

import os
import sys
import json
import time
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

import requests
import re
from platform_runtime import OLLAMA_URL

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_CONFIG = BASE_DIR / "config" / "local_model.json"
OLLAMA_EXE = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"


def get_local_ai_status() -> Dict[str, Any]:
    """Returns comprehensive health and model status for Ollama and Odysseus."""
    # 1. Check Ollama
    ollama_online = False
    ollama_models = []
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            ollama_online = True
            ollama_models = [m.get("name") for m in r.json().get("models", [])]
    except Exception:
        pass

    # 2. Check Odysseus
    odysseus_online = False
    odysseus_info = {}
    try:
        r = requests.get("http://127.0.0.1:7000/api/health", timeout=1.5)
        if r.status_code == 200:
            odysseus_online = True
            odysseus_info = r.json()
    except Exception:
        pass

    # 3. Read active model preference
    active_model = "qwen2.5:0.5b"
    if MODEL_CONFIG.exists():
        try:
            active_model = json.loads(MODEL_CONFIG.read_text(encoding="utf-8")).get("active_model", active_model)
        except Exception:
            pass

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ollama": {
            "online": ollama_online,
            "url": OLLAMA_URL,
            "models_installed": ollama_models,
            "models_count": len(ollama_models),
            "binary_path": str(OLLAMA_EXE) if OLLAMA_EXE.exists() else "ollama (system)",
        },
        "odysseus": {
            "online": odysseus_online,
            "url": "http://127.0.0.1:7000",
            "default_user": "admin",
            "health": odysseus_info,
        },
        "active_model_preference": active_model,
        "recommended_zero_cost_models": [],
        "selection_note": "Use the installed model inventory. Quality and latency depend on this PC and must be tested; no model guarantees accurate trading or screen interpretation."

    }


def pull_ollama_model(model_name: str) -> Dict[str, Any]:
    """Pulls a new model into local Ollama in background."""
    clean_name = model_name.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.:/-]{0,120}", clean_name):
        return {"ok": False, "error": "Use a valid Ollama model name."}

    exe = str(OLLAMA_EXE) if OLLAMA_EXE.exists() else "ollama"
    try:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = OLLAMA_URL
        env["OLLAMA_MODELS"] = str(BASE_DIR / "data" / "ollama" / "models")
        subprocess.Popen([exe, "pull", clean_name], env=env,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            "ok": True,
            "queued": True,
            "download_verified": False,
            "message": f"Pull process started for '{clean_name}' on {OLLAMA_URL}. Check models status to verify completion.",
            "model": clean_name
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_active_model(model_name: str) -> Dict[str, Any]:
    """Sets the preferred local model."""
    clean_name = model_name.strip()
    MODEL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CONFIG.write_text(json.dumps({"active_model": clean_name}, indent=2), encoding="utf-8")
    return {"ok": True, "active_model": clean_name, "message": f"Preferred local model set to '{clean_name}'."}


def ollama_odysseus(params: Optional[Dict[str, Any]] = None) -> str:
    """Action entry point for terminal and agent execution."""
    params = params or {}
    action = str(params.get("action", "status")).lower()
    
    if action in ("status", "health", "info"):
        st = get_local_ai_status()
        text = "=== ?? J.A.R.V.I.S. LOCAL AI ECOSYSTEM (OLLAMA & ODYSSEUS) ===\n"
        text += f"? Ollama Daemon: {'ONLINE ??' if st['ollama']['online'] else 'OFFLINE ??'} ({st['ollama']['url']})\n"
        text += f"  Installed Models ({st['ollama']['models_count']}): {', '.join(st['ollama']['models_installed']) if st['ollama']['models_installed'] else 'None (Download below)'}\n"
        text += f"? Odysseus AI Server: {'ONLINE ??' if st['odysseus']['online'] else 'OFFLINE ??'} ({st['odysseus']['url']})\n"
        text += f"? Active Model: {st['active_model_preference']}\n\n"
        text += st["selection_note"] + "\n"
        for m in st["recommended_zero_cost_models"]:
            text += f"  - '{m['name']}' ({m['size']}): {m['desc']}\n"
        return text

    elif action in ("pull", "download"):
        m_name = str(params.get("model") or params.get("name") or "llama3.2:1b")
        res = pull_ollama_model(m_name)
        return res.get("message") or res.get("error")

    elif action in ("set", "switch", "use"):
        m_name = str(params.get("model") or params.get("name") or "qwen2.5:0.5b")
        res = set_active_model(m_name)
        return res.get("message") or res.get("error")

    elif action in ("chat", "test", "query"):
        prompt = str(params.get("prompt") or "Hello from J.A.R.V.I.S. Sovereign AI System")
        engine = str(params.get("engine") or "both").lower()
        results = []
        if engine in ("both", "ollama"):
            try:
                r = requests.post(f"{OLLAMA_URL}/api/chat", json={
                    "model": "qwen2.5:0.5b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                }, timeout=25)
                if r.status_code == 200:
                    ans = r.json().get("message", {}).get("content")
                    results.append(f"🟢 [OLLAMA (qwen2.5:0.5b)]: {ans}")
                else:
                    results.append(f"🔴 [OLLAMA ERROR]: HTTP {r.status_code}")
            except Exception as e:
                results.append(f"🔴 [OLLAMA OFFLINE]: {e}")
        if engine in ("both", "odysseus"):
            try:
                r = requests.post("http://127.0.0.1:7000/api/sovereign/chat", json={
                    "prompt": prompt
                }, timeout=25)
                if r.status_code == 200:
                    ans = r.json().get("text")
                    results.append(f"🟢 [ODYSSEUS (:7000)]: {ans}")
                else:
                    results.append(f"🔴 [ODYSSEUS ERROR]: HTTP {r.status_code}")
            except Exception as e:
                results.append(f"🔴 [ODYSSEUS OFFLINE]: {e}")
        return "\n\n".join(results)

    return f"Unknown action '{action}'. Available: status, pull <model>, use <model>, chat <prompt>."
