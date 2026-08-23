"""
gold_advisor — Gold (XAU/USD) market analysis + trade idea for J.A.R.V.I.S.

Pulls live gold price + ~1 month history (Yahoo GC=F), recent gold news, and asks
Gemini to read it like a desk analyst (trend, key levels, news drivers, what the
big players / central banks are likely doing) and produce a clear, actionable
view. Can optionally deliver it to WhatsApp.

INFORMATIONAL ONLY — not financial advice. Trading carries risk.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import requests
    _HAS_REQ = True
except Exception:
    _HAS_REQ = False

_UA = {"User-Agent": "Mozilla/5.0 (JARVIS GoldAdvisor)"}


def _base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _key():
    try:
        return json.loads((_base() / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key")
    except Exception:
        return None


def _gold_data():
    """Live gold + 1mo history stats from Yahoo GC=F."""
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1mo&interval=1d",
        headers=_UA, timeout=10)
    res = r.json()["chart"]["result"][0]
    meta = res["meta"]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    out = {"price": price}
    if closes:
        out["high_1mo"] = max(closes)
        out["low_1mo"] = min(closes)
        out["d7_ago"] = closes[-6] if len(closes) >= 6 else closes[0]
        out["d30_ago"] = closes[0]
        out["chg_7d"] = ((price - out["d7_ago"]) / out["d7_ago"] * 100) if out.get("d7_ago") else 0
        out["chg_30d"] = ((price - out["d30_ago"]) / out["d30_ago"] * 100) if out.get("d30_ago") else 0
    return out


def _gold_news(n=8):
    try:
        import feedparser
        url = "https://news.google.com/rss/search?q=gold+price+XAU+when:3d&hl=en-US&gl=US&ceid=US:en"
        if _HAS_REQ:
            feed = feedparser.parse(requests.get(url, headers=_UA, timeout=10).content)
        else:
            feed = feedparser.parse(url)
        return [e.title.strip() for e in feed.entries[:n] if getattr(e, "title", "")]
    except Exception:
        return []


def _analyze(data, news):
    key = _key()
    hl = "\n".join(f"- {h}" for h in news) or "(no fresh headlines)"
    facts = (
        f"Spot ~${data.get('price','?'):.1f}/oz. "
        f"7d change {data.get('chg_7d',0):+.1f}%, 30d change {data.get('chg_30d',0):+.1f}%. "
        f"1-month high ${data.get('high_1mo','?'):.0f}, low ${data.get('low_1mo','?'):.0f}."
    )
    try:
        from google import genai
        c = genai.Client(api_key=key)
        prompt = (
            "You are a precious-metals desk analyst briefing a trader on GOLD (XAU/USD). "
            "Using the data and headlines, write a tight, practical read:\n"
            "1) Trend & momentum (1 line).\n"
            "2) Key levels: nearest support & resistance (approx numbers).\n"
            "3) What's driving it — news/macro, and what the big players (central banks, "
            "funds, safe-haven flows) are likely doing.\n"
            "4) A clear actionable VIEW: bias (buy/sell/wait), a sensible entry zone, a "
            "stop-loss, and a target — as levels.\n"
            "5) One-line risk note.\n"
            "Be concrete with numbers. Under 160 words. End with: "
            "'⚠ Informational only, not financial advice.'\n\n"
            f"DATA: {facts}\n\nHEADLINES:\n{hl}"
        )
        r = c.models.generate_content(model="gemini-flash-latest", contents=prompt)
        return (r.text or "").strip()
    except Exception as e:
        return (f"GOLD ~${data.get('price','?')}/oz | 7d {data.get('chg_7d',0):+.1f}% | "
                f"30d {data.get('chg_30d',0):+.1f}%.\nHeadlines:\n{hl}\n"
                f"(AI analysis unavailable: {str(e)[:60]})\n⚠ Informational only, not financial advice.")


MANIFEST = {
    "name": "gold_advisor",
    "description": (
        "Gold (XAU/USD) market analysis and trade idea: live price, recent history, "
        "news drivers, big-player positioning, with key levels and an actionable bias "
        "(entry/stop/target). Use when Boss asks about gold, gold trading, or for a gold "
        "update/suggestion. Set send_whatsapp=true with a whatsapp_to contact to deliver "
        "it to WhatsApp. Informational only, not financial advice."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "send_whatsapp": {"type": "BOOLEAN", "description": "Also send the suggestion to WhatsApp."},
            "whatsapp_to": {"type": "STRING", "description": "WhatsApp contact name to send to (e.g. 'Muhammad' or a saved contact)."},
        },
        "required": [],
    },
}


def run(parameters=None, player=None, speak=None):
    parameters = parameters or {}
    if not _HAS_REQ:
        return "Gold data needs the requests library, Sir."
    if player is not None:
        try:
            player.write_log("GOLD: analysing live market...")
        except Exception:
            pass
    try:
        data = _gold_data()
    except Exception as e:
        return f"Couldn't fetch gold price right now, Sir ({str(e)[:60]})."
    news = _gold_news()
    analysis = _analyze(data, news)

    stamp = datetime.now().strftime("%a %d %b, %H:%M")
    msg = f"\U0001F947 GOLD BRIEF — {stamp}\n\n{analysis}"

    # Optional WhatsApp delivery
    if parameters.get("send_whatsapp"):
        to = (parameters.get("whatsapp_to") or "").strip()
        if not to:
            # Default to the Boss's configured daily-brief contact.
            try:
                cfg = json.loads((_base() / "config" / "gold_config.json").read_text(encoding="utf-8"))
                contacts = cfg.get("whatsapp_contacts") or []
                if contacts:
                    to = str(contacts[0].get("number") or contacts[0].get("name") or "").strip()
            except Exception:
                pass
        if not to:
            return msg + "\n\n(Tell me which WhatsApp contact to send it to, Sir.)"
        try:
            from actions.send_message import send_message
            # send_message expects 'message_text' (NOT 'message') — an empty message
            # is rejected, so pass the right key and verify the outcome honestly.
            result = send_message(
                parameters={"platform": "whatsapp", "receiver": to, "message_text": msg},
                player=player,
            )
            if isinstance(result, str) and result.lower().startswith("message sent"):
                return msg + f"\n\n✅ Sent to {to} on WhatsApp."
            return msg + f"\n\n(WhatsApp delivery NOT confirmed: {str(result)[:100]})"
        except Exception as e:
            return msg + f"\n\n(WhatsApp send failed: {str(e)[:60]})"
    return msg


if __name__ == "__main__":
    print(run({}))
