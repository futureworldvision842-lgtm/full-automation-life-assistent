"""Read-only JARVIS agent directory for the paired GAIGS mobile app.

This module reports local service availability.  It exposes no command runner,
credentials, private memory, screen data, phone number or message content.
"""

from __future__ import annotations

import os
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None


ROOT = Path(__file__).resolve().parent.parent


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            return True
    except OSError:
        return False


def _process_running(needle: str) -> bool:
    if psutil is None:
        return False
    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").lower()
            if not (name.startswith("python") or name.startswith("node") or name.startswith("hermes")):
                continue
            if needle.lower() in " ".join(process.info.get("cmdline") or []).lower():
                return True
        except Exception:
            continue
    return False


def _agent(agent_id: str, name: str, status: str, detail: str, now: str) -> dict:
    return {
        "id": agent_id,
        "name": name,
        "status": status,
        "detail": detail,
        "lastSeen": now if status in {"online", "ready"} else None,
    }


def build_agent_hub() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    hermes_exe = Path(os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\hermes.exe"))
    hermes_ready = hermes_exe.exists() or shutil.which("hermes") is not None
    moltbot_installed = shutil.which("clawdbot") is not None
    world_monitor_ready = (ROOT / "actions" / "world_monitor.py").exists()
    voice_ready = _process_running("main.py")
    bridge_ready = _port_open(8090)
    ollama_ready = _port_open(11434)
    heartbeat_ready = _process_running("heartbeat_reporter.py")
    mission_ready = _process_running("mission_daemon.py")
    agents = [
        _agent("jarvis-core", "JARVIS PC Core", "online" if bridge_ready else "offline", "Read-only status bridge on port 8090", now),
        _agent("voice", "JARVIS Voice Listener", "online" if voice_ready else "offline", "Push-to-mute desktop speech loop; no hidden mobile microphone", now),
        _agent("heartbeat", "GAIGS Cloud Heartbeat", "online" if heartbeat_ready else "offline", "Status-only relay; no commands, files, memory or messages leave the PC", now),
        _agent("mission", "Mission Control", "online" if mission_ready else "offline", "Read-only property health, sourced mission memory and owner-approved daily briefings", now),
        _agent("world", "World Monitor", "ready" if world_monitor_ready else "offline", "Local source and briefing engine", now),
        _agent("moltbot", "MoltBot", "online" if moltbot_installed and _port_open(18789) else "offline", "Local clawdbot gateway on port 18789" if moltbot_installed else "Install extras to add the local gateway", now),
        _agent("hermes", "Hermes Agent", "ready" if hermes_ready else "offline", "Nous Hermes with user-approved Codex authentication" if hermes_ready else "Hermes is not installed on this PC", now),
        _agent("whatsapp", "WhatsApp Bridge", "online" if _port_open(3200) else "offline", "Baileys multi-device bridge; message contents are not exposed", now),
        _agent("ops", "JARVIS Ops", "online" if _port_open(8770) else "offline", "Local operations dashboard", now),
        _agent("ollama", "Private Local Model", "online" if ollama_ready else "offline", "Ollama inference with qwen2.5:1.5b fallback", now),
    ]
    return {
        "name": "Muhammad's JARVIS",
        "generatedAt": now,
        "privacy": "status-only",
        "agents": agents,
    }
