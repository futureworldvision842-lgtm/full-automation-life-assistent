"""
short_term.py — J.A.R.V.I.S. TEMPORARY / WORKING memory.

Companion to memory_manager.py (which holds the *permanent* long-term profile).

This module keeps a small rolling buffer of the most recent conversation turns
(the user's last orders + Jarvis's replies) on disk so that:
  - Jarvis remembers what was just said, even across a restart / reconnect.
  - "pichla order", "wohi wala", "phir se karo" type follow-ups keep working.
  - Recent preferences expressed in the session stay fresh in context.

It is deliberately lightweight and self-trimming: old turns fall off both by
count (keep the last N) and by age (drop anything older than the TTL), so the
temporary memory never grows unbounded and never leaks stale context.
"""

import json
import sys
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR   = _base_dir()
STM_PATH   = BASE_DIR / "memory" / "short_term.json"
_lock      = Lock()

MAX_TURNS      = 24        # how many turns we keep on disk
PROMPT_TURNS   = 10        # how many we surface into the live prompt
TTL_HOURS      = 18        # turns older than this are dropped from the prompt
MAX_TEXT_LEN   = 300       # per-side truncation so the block stays small


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load() -> dict:
    if STM_PATH.exists():
        try:
            data = json.loads(STM_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("turns"), list):
                return data
        except Exception as e:
            print(f"[ShortMem] [Warning] load error: {e}")
    return {"turns": [], "updated": _now_iso()}


def _save(data: dict) -> None:
    try:
        STM_PATH.parent.mkdir(parents=True, exist_ok=True)
        STM_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[ShortMem] [Warning] save error: {e}")


def _clip(text: str) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) > MAX_TEXT_LEN:
        return text[:MAX_TEXT_LEN].rstrip() + "…"
    return text


def add_turn(user_text: str, jarvis_text: str) -> None:
    """Append one exchange to the working memory (called after each turn)."""
    user_text   = _clip(user_text)
    jarvis_text = _clip(jarvis_text)
    if not user_text and not jarvis_text:
        return

    with _lock:
        data  = _load()
        turns = data.get("turns", [])

        # Skip exact duplicate of the immediately preceding turn (echo guard).
        if turns:
            last = turns[-1]
            if last.get("u") == user_text and last.get("j") == jarvis_text:
                return

        turns.append({"u": user_text, "j": jarvis_text, "t": _now_iso()})
        data["turns"]   = turns[-MAX_TURNS:]
        data["updated"] = _now_iso()
        _save(data)


def get_recent(n: int = PROMPT_TURNS, within_hours: int = TTL_HOURS) -> list[dict]:
    """Return the most recent, non-expired turns (newest last)."""
    data   = _load()
    turns  = data.get("turns", [])
    cutoff = datetime.now() - timedelta(hours=within_hours)

    fresh = []
    for turn in turns:
        try:
            ts = datetime.fromisoformat(turn.get("t", ""))
        except Exception:
            ts = datetime.now()          # undated -> treat as fresh
        if ts >= cutoff:
            fresh.append(turn)

    return fresh[-n:]


def _ago(ts_str: str) -> str:
    try:
        delta = datetime.now() - datetime.fromisoformat(ts_str)
    except Exception:
        return "just now"
    secs = int(delta.total_seconds())
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{secs // 60} min ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def format_short_term_for_prompt() -> str:
    """Render the recent conversation as a prompt block, or '' if empty."""
    turns = get_recent()
    if not turns:
        return ""

    lines = [
        "[RECENT CONVERSATION — short-term working memory]",
        "These are the last things that happened between you and the Boss "
        "(most recent last). Use them to keep continuity — remember his last "
        "orders, follow-ups like \"wohi\"/\"phir se\"/\"pichla wala\", and "
        "anything he just told you. Do NOT recite this list back to him.",
    ]
    for turn in turns:
        when = _ago(turn.get("t", ""))
        u = turn.get("u", "")
        j = turn.get("j", "")
        if u:
            lines.append(f"  ({when}) Boss: {u}")
        if j:
            lines.append(f"           You: {j}")

    return "\n".join(lines) + "\n"


def clear_short_term() -> str:
    """Wipe the working memory (long-term profile is untouched)."""
    with _lock:
        _save({"turns": [], "updated": _now_iso()})
    return "Short-term memory cleared."
