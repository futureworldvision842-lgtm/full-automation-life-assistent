"""
content_studio — JARVIS's content engine for Muhammad's channels.

On command, generates COMPLETE, ready-to-shoot video script packages in the
Boss's style (Afkaar / Fikr-o-Nizam / Global English) — hook, full VO script,
on-screen neon keywords, CTA, sources to cite, and a HeyGen-ready version.
Free: uses the Boss's Gemini key, no paid services, no fake engagement.

Real growth only: this produces CONTENT (the thing that actually grows channels).
Posting stays with the Boss — JARVIS drafts, Boss approves & publishes.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

BOSS_WA = "923468053268"
OUT = Path(r"E:\jarvis\content")


def _base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _key():
    try:
        return json.loads((_base() / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key")
    except Exception:
        return None


def _gemini(prompt, system):
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
        headers={"Content-Type": "application/json", "X-goog-api-key": _key()},
        json={"system_instruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": prompt}]}]},
        timeout=90)
    j = r.json()
    try:
        return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"]).strip()
    except Exception:
        return f"(model error: {str(j)[:120]})"


def _wa(msg):
    try:
        data = json.dumps({"number": BOSS_WA, "message": msg}).encode()
        req = urllib.request.Request("http://localhost:3200/send", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=60)
        return True
    except Exception:
        return False


BRAIN = (
    "You are JARVIS, Muhammad Qureshi's scriptwriter. His mission: a people-owned "
    "'new operating system for humanity' — decentralized governance, blockchain "
    "transparency, AI that informs not decides, a global science game, education that "
    "frees; started from Masjid-e-Nabawi Qureshi Hashmi, Islamabad. "
    "STYLE: hook in the first 2 seconds; ONE idea per video; friend-to-friend tone "
    "(Dhruv-Rathee / Sufi-Tram); anime metaphors welcome (AoT walls = borders, One "
    "Piece = freedom). INTEGRITY (never break): never invent stats/quotes/dates — if "
    "unsure say 'verify before airing' and list sources; label interpretation as "
    "argument ('many argue…'); faith = his sincere belief, respectful; AI-control = a "
    "WARNING not a prophecy. Platform: onepiecejourney-crew.netlify.app")


MANIFEST = {
    "name": "content_studio",
    "description": (
        "Generate complete, ready-to-shoot VIDEO SCRIPT packages for the Boss's "
        "channels (Afkaar Urdu, Fikr-o-Nizam, Global English) — hook, full script, "
        "on-screen keywords, CTA, sources, and a HeyGen-ready version. Free (Gemini). "
        "Use when Boss says 'give me a script', 'video script', 'content for [topic]', "
        "'Afkaar short', 'make content'. Real content only — no fake engagement."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "topic": {"type": "STRING", "description": "What the video is about, e.g. 'colonial education system' or 'why the dollar is a weapon'."},
            "channel": {"type": "STRING", "description": "afkaar (Urdu shorts) | fikr (Urdu/Nastaliq mission) | english (global). Default: afkaar."},
            "count": {"type": "INTEGER", "description": "How many scripts (default 1)."},
            "language": {"type": "STRING", "description": "urdu | roman-urdu | english (default matches channel)."},
        },
        "required": ["topic"],
    },
}


def run(parameters=None, player=None, speak=None):
    p = parameters or {}
    if requests is None:
        return "requests missing, Sir."
    if not _key():
        return "No Gemini key, Sir."
    topic = (p.get("topic") or "").strip()
    if not topic:
        return "Give me a topic for the video, Sir."
    channel = (p.get("channel") or "afkaar").lower()
    count = max(1, min(int(p.get("count") or 1), 5))
    lang = (p.get("language") or ("english" if channel == "english" else "roman-urdu")).lower()

    ch_note = {
        "afkaar": "Afkaar Urdu — 45-60s short, viral hook, one shocking fact, question CTA.",
        "fikr": "Fikr-o-Nizam — Urdu/Nastaliq, mission channel, history+system truth, deeper.",
        "english": "Global English — secular, Gen-Z, no religious framing, universal message.",
    }.get(channel, "Afkaar Urdu short.")

    if player:
        try: player.write_log(f"CONTENT: writing {count} script(s) on '{topic[:40]}'...")
        except Exception: pass

    out = _gemini(
        f"Write {count} complete video script package(s). CHANNEL: {ch_note} "
        f"LANGUAGE: {lang}. TOPIC: {topic}.\n\n"
        "For EACH script output exactly:\n"
        "TITLE — <catchy>\nHOOK (0-2s): <scroll-stopper>\n"
        "SCRIPT: <full voiceover, 45-90s>\n"
        "ON-SCREEN KEYWORDS: <3-4 neon words>\n"
        "CTA: <one-word comment + follow tease>\n"
        "SOURCES TO CITE: <for any factual claim, or 'none/verify'>\n"
        "HEYGEN VERSION: <the script cleaned for an avatar to read aloud>\n"
        "---",
        system=BRAIN)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        fp = OUT / f"{channel}_{stamp}.md"
        fp.write_text(f"# {topic} ({channel})\n\n{out}", encoding="utf-8")
    except Exception:
        fp = "(save failed)"

    _wa(f"🎬 JARVIS SCRIPTS — {channel} — {datetime.now().strftime('%d %b %H:%M')}\n"
        f"Topic: {topic}\n\n{out[:1400]}{'…' if len(out) > 1400 else ''}\n\n💾 {fp}")

    return (f"Done, Sir — {count} script(s) for {channel} on '{topic}'. Saved to {fp}, "
            f"full package sent to your WhatsApp.\n\n{out[:800]}")


if __name__ == "__main__":
    print(run({"topic": sys.argv[1] if len(sys.argv) > 1 else "why the current system was built to control", "channel": "afkaar"}))
