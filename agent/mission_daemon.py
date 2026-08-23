"""Daily, owner-controlled mission operations for JARVIS.

The daemon performs read-only health checks, stores a local sourced report and
sends that report to the owner's configured WhatsApp contact.  It proposes
improvements; it never edits, deploys, spends, messages third parties or installs
updates on its own.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.mission_memory import latest_daily_report, properties, save_daily_report


CHECK_INTERVAL_SECONDS = max(60, int(os.getenv("JARVIS_MISSION_CHECK_INTERVAL", "300")))
DAILY_HOUR = max(0, min(23, int(os.getenv("JARVIS_DAILY_BRIEF_HOUR", "9"))))
OWNER_CONTACT = os.getenv("JARVIS_OWNER_WHATSAPP_CONTACT", "boss").strip() or "boss"


def _site_health(item: dict) -> dict:
    url = str(item.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"name": item.get("name", "Unknown"), "url": url, "ok": False, "detail": "invalid URL"}
    request = urllib.request.Request(url, method="GET", headers={"user-agent": "JARVIS-Mission-Health/1.0", "range": "bytes=0-1023"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            response.read(1024)
            elapsed = int((time.monotonic() - started) * 1000)
            return {"name": item.get("name"), "url": url, "ok": 200 <= response.status < 400, "status": response.status, "ms": elapsed}
    except urllib.error.HTTPError as error:
        return {"name": item.get("name"), "url": url, "ok": False, "status": error.code, "detail": "HTTP error"}
    except Exception as error:
        return {"name": item.get("name"), "url": url, "ok": False, "detail": type(error).__name__}


def _agent_status() -> list[dict]:
    try:
        from web.agent_hub import build_agent_hub
        return list(build_agent_hub().get("agents") or [])
    except Exception:
        return []


def build_daily_report() -> str:
    site_list = properties()
    with ThreadPoolExecutor(max_workers=4) as pool:
        site_rows = list(pool.map(_site_health, site_list))
    agents = _agent_status()
    online_agents = [item for item in agents if item.get("status") in {"online", "ready"}]
    offline_agents = [item for item in agents if item.get("status") not in {"online", "ready"}]
    healthy_sites = [item for item in site_rows if item.get("ok")]
    unhealthy_sites = [item for item in site_rows if not item.get("ok")]

    lines = [
        "J.A.R.V.I.S. DAILY MISSION BRIEF",
        datetime.now().strftime("%A, %d %B %Y — %H:%M"),
        "",
        f"SYSTEM: {len(online_agents)}/{len(agents)} registered agents ready.",
        f"MISSION PROPERTIES: {len(healthy_sites)}/{len(site_rows)} reachable.",
    ]
    if offline_agents:
        lines.append("Attention: " + ", ".join(str(item.get("name")) for item in offline_agents[:6]) + " offline/degraded.")
    if unhealthy_sites:
        lines.append("Site review: " + ", ".join(f"{item.get('name')} ({item.get('status') or item.get('detail')})" for item in unhealthy_sites[:6]))
    lines.extend([
        "",
        "TODAY'S SAFE AUTONOMOUS WORK:",
        "• Monitor approved services and public properties.",
        "• Preserve sourced mission memory and prepare improvement proposals.",
        "• Keep drafts and research non-binding until Muhammad approves execution.",
        "",
        "OWNER CONTROL: publish, deploy, money, messages to others, governance, credentials, installs and deletion require a one-time approval code.",
        "Reply to JARVIS with a research/planning command any time. Consequential commands will show exactly what needs approval.",
    ])
    return "\n".join(lines)


def send_owner_whatsapp(message: str) -> bool:
    payload = json.dumps({"name": OWNER_CONTACT, "message": message}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:3200/send",
        data=payload,
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def run_once(send: bool = True) -> str:
    report = build_daily_report()
    save_daily_report(report)
    delivered = send_owner_whatsapp(report) if send else False
    print(f"[MissionDaemon] Daily report stored. WhatsApp delivered: {delivered}")
    return report


def _report_is_today() -> bool:
    current = latest_daily_report()
    return datetime.now().strftime("%d %B %Y") in current


def run_forever() -> None:
    print("[MissionDaemon] Owner-controlled mission loop online.")
    while True:
        now = datetime.now()
        if now.hour >= DAILY_HOUR and not _report_is_today():
            try:
                run_once(send=True)
            except Exception as error:
                print(f"[MissionDaemon] Report error: {type(error).__name__}")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-send", action="store_true")
    options = parser.parse_args()
    if options.once:
        print(run_once(send=not options.no_send))
    else:
        run_forever()

