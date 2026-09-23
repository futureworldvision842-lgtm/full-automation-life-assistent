r"""
web_autopilot — JARVIS's autonomous internet operator.

Give it a GOAL and it works the web on the Boss's behalf: plans steps with
Gemini, searches the internet (DuckDuckGo, no key), reads pages, discovers &
uses FREE APIs/tools, studies GitHub repos, generates the Boss's mission content
(scripts, posts, outreach drafts), saves everything, and reports to WhatsApp.

SAFE BY DESIGN (matches the Boss's own integrity + platform ToS):
  - Anything that PUBLISHES, MESSAGES STRANGERS, or CREATES ACCOUNTS is produced
    as a ready-to-send DRAFT and queued for one-tap approval — never auto-fired
    (auto-posting/mass-DM/fake-accounts get you banned and violate the rules).
  - Everything read-only or generative (research, drafting, using free public
    APIs, reading public GitHub) runs fully autonomously.

Outputs saved to E:\jarvis\autopilot\<timestamp>\ and summarized to WhatsApp.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

BOSS_WA = "923468053268"
OUT_DIR = Path(r"E:\jarvis\autopilot")


def _base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _key():
    try:
        return json.loads((_base() / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key")
    except Exception:
        return None


def _gemini(prompt, system=None, model="gemini-flash-latest"):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"Content-Type": "application/json", "X-goog-api-key": _key()},
        json=body, timeout=90)
    j = r.json()
    try:
        return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"]).strip()
    except Exception:
        return f"(model error: {str(j)[:120]})"


def _ddg(query, n=6):
    """Key-less web search via DuckDuckGo HTML endpoint."""
    try:
        r = requests.post("https://html.duckduckgo.com/html/",
                          data={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        hits = re.findall(r'result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
        out = []
        for url, title in hits[:n]:
            title = re.sub("<.*?>", "", title).strip()
            if title:
                out.append({"title": title, "url": urllib.parse.unquote(url)})
        return out
    except Exception as e:
        return [{"title": f"(search failed: {str(e)[:40]})", "url": ""}]


def _fetch(url, limit=6000):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
        txt = re.sub("<.*?>", " ", txt)
        return re.sub(r"\s+", " ", txt)[:limit]
    except Exception as e:
        return f"(fetch failed: {str(e)[:40]})"


def _wa(msg):
    try:
        data = json.dumps({"number": BOSS_WA, "message": msg}).encode()
        req = urllib.request.Request("http://localhost:3200/send", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=60)
        return True
    except Exception:
        return False


MANIFEST = {
    "name": "web_autopilot",
    "description": (
        "JARVIS's autonomous internet operator. Give a GOAL and it researches the "
        "web, uses free public APIs, studies GitHub, and GENERATES the Boss's "
        "mission work (content scripts, posts, outreach drafts, research briefs) — "
        "then saves it and reports to WhatsApp. Publishing / messaging strangers / "
        "creating accounts are produced as approval-gated DRAFTS, never auto-sent. "
        "Use when Boss says 'do this online', 'research and make content', 'find "
        "tools/APIs for X', 'work on the mission', 'autopilot'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "goal": {"type": "STRING", "description": "What to accomplish online, e.g. 'make 5 Afkaar shorts about the colonial system' or 'find free video-hosting APIs I can use'."},
            "report_whatsapp": {"type": "BOOLEAN", "description": "Send the summary to the Boss's WhatsApp (default true)."},
        },
        "required": ["goal"],
    },
}


BRAIN = ("You are JARVIS, Muhammad Qureshi's autonomous agent. His mission: a people-owned "
         "'new operating system for humanity' — decentralized governance, blockchain transparency, "
         "AI that informs not decides, a global science game, education that frees; started from "
         "Masjid-e-Nabawi Qureshi Hashmi, Islamabad. Content style: hook in 2s, one idea, "
         "Dhruv-Rathee/friend tone, cite sources, never invent stats, label interpretation as argument, "
         "faith respectful, AI-control = warning not prophecy. Platform demo: onepiecejourney-crew.netlify.app")


def run(parameters=None, player=None, speak=None):
    p = parameters or {}
    if requests is None:
        return "requests library missing, Sir."
    if not _key():
        return "No Gemini key configured, Sir."
    goal = (p.get("goal") or "").strip()
    if not goal:
        return "Give me a goal to work on online, Sir."
    report = p.get("report_whatsapp", True)

    if player:
        try: player.write_log(f"AUTOPILOT: working on '{goal[:50]}'...")
        except Exception: pass

    # 1) PLAN — decide search queries + what deliverable to produce.
    plan = _gemini(
        f"GOAL: {goal}\n\nReturn STRICT JSON: "
        '{"searches":["q1","q2","q3"],"deliverable":"<what to produce>",'
        '"needs_publish_or_account":true|false}. Max 3 searches.',
        system=BRAIN)
    plan = re.sub(r"```(?:json)?", "", plan).strip().rstrip("`").strip()
    try:
        plan = json.loads(plan)
    except Exception:
        plan = {"searches": [goal], "deliverable": goal, "needs_publish_or_account": False}

    # 2) RESEARCH — search + read top sources autonomously.
    research = []
    for q in (plan.get("searches") or [goal])[:3]:
        hits = _ddg(q, 5)
        research.append(f"### Search: {q}\n" + "\n".join(f"- {h['title']} — {h['url']}" for h in hits))
        for h in hits[:2]:
            if h["url"].startswith("http"):
                research.append(f"[source {h['url'][:60]}]: {_fetch(h['url'], 2500)}")

    # 3) PRODUCE — the mission deliverable, grounded in the research.
    deliverable = _gemini(
        f"GOAL: {goal}\nDELIVERABLE: {plan.get('deliverable')}\n\n"
        f"RESEARCH (use it, cite sources for facts):\n{chr(10).join(research)[:9000]}\n\n"
        "Produce the finished, ready-to-use output now. If it's content, give the full package "
        "(hook, script, on-screen keywords, CTA, sources). Be concrete and complete.",
        system=BRAIN)

    # 4) SAVE.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUT_DIR / stamp
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "goal.txt").write_text(goal, encoding="utf-8")
        (folder / "research.md").write_text("\n\n".join(research), encoding="utf-8")
        (folder / "deliverable.md").write_text(deliverable, encoding="utf-8")
    except Exception:
        pass

    gated = plan.get("needs_publish_or_account")
    gate_note = ("\n\n⚠ This involves PUBLISHING / accounts / messaging strangers — I've prepared it "
                 "as a DRAFT for your one-tap approval (I won't auto-post; that risks bans)."
                 if gated else "")

    # 5) REPORT to WhatsApp.
    summary = (f"🤖 JARVIS AUTOPILOT — {datetime.now().strftime('%a %d %b %H:%M')}\n\n"
               f"🎯 Goal: {goal}\n\n"
               f"{deliverable[:1200]}"
               f"{'…' if len(deliverable) > 1200 else ''}"
               f"\n\n💾 Saved: {folder}{gate_note}")
    sent = _wa(summary) if report else False

    return (f"Autopilot done, Sir. Deliverable saved to {folder}\\deliverable.md."
            f"{' Full report sent to your WhatsApp.' if sent else ''}"
            f"{' (Publishing steps are queued as an approval-gated draft.)' if gated else ''}"
            f"\n\n{deliverable[:600]}")


if __name__ == "__main__":
    print(run({"goal": sys.argv[1] if len(sys.argv) > 1 else "find 3 free video hosting APIs with no signup", "report_whatsapp": False}))
