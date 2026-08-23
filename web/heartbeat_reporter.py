"""Publish a sanitized JARVIS health heartbeat to the public GAIGS app.

Only the status-only payload from ``agent_hub`` is sent. This process never
uploads commands, prompts, memory, files, screenshots, contacts or messages.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from agent_hub import build_agent_hub


DEFAULT_ENDPOINT = "https://gaigs-jarvis-v2.qw01.chatgpt.site/api/jarvis-heartbeat"
INTERVAL_SECONDS = max(20, int(os.getenv("GAIGS_HEARTBEAT_INTERVAL", "30")))


def publish_once() -> bool:
    token = os.getenv("GAIGS_HEARTBEAT_TOKEN", "").strip()
    if not token:
        return False
    endpoint = os.getenv("GAIGS_HEARTBEAT_URL", DEFAULT_ENDPOINT).strip() or DEFAULT_ENDPOINT
    payload = json.dumps(build_agent_hub(), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "GAIGS-JARVIS-Heartbeat/2.0",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return 200 <= response.status < 300


def run() -> None:
    print("[Heartbeat] Status-only GAIGS relay started.")
    last_missing_notice = 0.0
    while True:
        try:
            if publish_once():
                print("[Heartbeat] GAIGS cloud status refreshed.")
            elif time.time() - last_missing_notice > 120:
                print("[Heartbeat] Waiting for GAIGS_HEARTBEAT_TOKEN.")
                last_missing_notice = time.time()
        except (OSError, urllib.error.URLError, ValueError) as error:
            print(f"[Heartbeat] Temporary publish failure: {type(error).__name__}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
