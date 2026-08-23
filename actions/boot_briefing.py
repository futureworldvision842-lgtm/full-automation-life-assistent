"""
boot_briefing.py — J.A.R.V.I.S. "wake-up" intelligence brief.

When Jarvis first comes online, this module gathers a snapshot of everything
the Boss wants to hear on start-up and packages it into a single instruction
turn that Jarvis then speaks naturally:

    • Greeting (time-of-day aware)
    • Islamabad weather (live)
    • PC / host condition (battery, CPU, RAM, disk, uptime)
    • Jarvis's own status + duty summary
    • Markets — gold, silver, oil, crypto (BTC/ETH/BNB)
    • Geopolitical / global headlines that matter

All data is fetched here in Python from free, key-less sources so the briefing
is fast and reliable — Jarvis does NOT have to make a chain of tool calls at
boot. Every fetch is best-effort with a short timeout; anything that fails is
simply marked unavailable and the briefing still goes out.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

_TIMEOUT = 5


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------
# Individual collectors — each returns a short human string (never raises).
# ----------------------------------------------------------------------------

def _greeting() -> str:
    h = datetime.now().hour
    if h < 5:
        part = "It's late night"
    elif h < 12:
        part = "Good morning"
    elif h < 17:
        part = "Good afternoon"
    elif h < 21:
        part = "Good evening"
    else:
        part = "Good night hours"
    return f"{part}. Right now it is {datetime.now().strftime('%A, %B %d — %I:%M %p')}."


def get_weather(city: str = "Islamabad") -> str:
    if not _HAS_REQUESTS:
        return "Weather: unavailable (no network module)."
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=_TIMEOUT)
        cur = r.json()["current_condition"][0]
        desc  = cur["weatherDesc"][0]["value"]
        temp  = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        hum   = cur["humidity"]
        wind  = cur["windspeedKmph"]
        return (f"{city} weather: {desc}, {temp}°C (feels like {feels}°C), "
                f"humidity {hum}%, wind {wind} km/h.")
    except Exception:
        # Fallback compact endpoint
        try:
            r = requests.get(f"https://wttr.in/{city}?format=%C+%t+humidity+%h+wind+%w",
                             timeout=_TIMEOUT)
            if r.ok and r.text.strip():
                return f"{city} weather: {r.text.strip()}."
        except Exception:
            pass
        return f"{city} weather: unavailable right now."


def get_pc_status() -> str:
    if not _HAS_PSUTIL:
        return "PC status: unavailable (psutil missing)."
    try:
        parts = []

        # Battery
        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                plug = "charging" if bat.power_plugged else "on battery"
                parts.append(f"battery {int(bat.percent)}% ({plug})")
            else:
                parts.append("battery: desktop / no battery")
        except Exception:
            pass

        # CPU + RAM
        cpu = psutil.cpu_percent(interval=0.4)
        ram = psutil.virtual_memory()
        parts.append(f"CPU {cpu:.0f}%")
        parts.append(f"RAM {ram.percent:.0f}% used "
                     f"({ram.used/1e9:.1f} of {ram.total/1e9:.1f} GB)")

        # Disks (best-effort for common drives)
        for drive in ("C:\\", "E:\\"):
            try:
                d = psutil.disk_usage(drive)
                parts.append(f"disk {drive[0]}: {d.percent:.0f}% full "
                             f"({d.free/1e9:.0f} GB free)")
            except Exception:
                pass

        # Uptime
        try:
            up = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            hrs, mins = divmod(int(up.total_seconds()) // 60, 60)
            parts.append(f"uptime {hrs}h {mins}m")
        except Exception:
            pass

        return "PC status: " + ", ".join(parts) + "."
    except Exception as e:
        return f"PC status: partial read failed ({str(e)[:40]})."


def get_markets() -> str:
    if not _HAS_REQUESTS:
        return "Markets: unavailable (no network module)."

    bits = []

    # --- Precious metals + oil via gold-api.com (free, key-less, per troy oz USD)
    metal_syms = [("XAU", "Gold"), ("XAG", "Silver")]
    for sym, label in metal_syms:
        try:
            r = requests.get(f"https://api.gold-api.com/price/{sym}", timeout=_TIMEOUT)
            price = r.json().get("price")
            if price:
                bits.append(f"{label} ${float(price):,.2f}/oz")
        except Exception:
            pass

    # --- Oil (WTI crude) via Yahoo Finance futures (free, key-less)
    oil_done = False
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/CL=F",
            params={"interval": "1d", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_TIMEOUT,
        )
        meta = r.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev  = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price:
            chg_s = ""
            if prev:
                chg_s = f" ({(price - prev) / prev * 100:+.1f}% 24h)"
            bits.append(f"Crude oil (WTI) ${float(price):,.2f}/bbl{chg_s}")
            oil_done = True
    except Exception:
        pass
    if not oil_done:
        try:
            r = requests.get("https://api.gold-api.com/price/WTI", timeout=_TIMEOUT)
            price = r.json().get("price")
            if price:
                bits.append(f"Crude oil (WTI) ${float(price):,.2f}/bbl")
                oil_done = True
        except Exception:
            pass
    if not oil_done:
        bits.append("Crude oil: price unavailable")

    # --- Crypto via CoinGecko (free, key-less) with 24h change
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin,ethereum,binancecoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=_TIMEOUT,
        )
        data = r.json()
        for cid, label in (("bitcoin", "BTC"), ("ethereum", "ETH"), ("binancecoin", "BNB")):
            d = data.get(cid)
            if d and d.get("usd") is not None:
                chg = d.get("usd_24h_change")
                chg_s = f" ({chg:+.1f}% 24h)" if isinstance(chg, (int, float)) else ""
                bits.append(f"{label} ${d['usd']:,.0f}{chg_s}")
    except Exception:
        bits.append("Crypto: prices unavailable")

    if not bits:
        return "Markets: unavailable right now."
    return "Markets — " + "; ".join(bits) + "."


def get_geopolitics(limit: int = 6) -> str:
    """Pull top world/geopolitical headlines from the existing world_monitor feeds."""
    try:
        if str(_base_dir()) not in sys.path:
            sys.path.insert(0, str(_base_dir()))
        from actions.world_monitor import get_headlines
    except Exception:
        return "Global news: monitor module unavailable."

    titles = []
    for cat in ("world", "middleeast", "defense"):
        try:
            for h in get_headlines(cat, limit=3) or []:
                title = (h.get("title") or "").strip() if isinstance(h, dict) else str(h).strip()
                src   = (h.get("source") or "").strip() if isinstance(h, dict) else ""
                if title:
                    titles.append(f"{title}" + (f" ({src})" if src else ""))
        except Exception:
            continue

    # de-dupe preserving order
    seen, uniq = set(), []
    for t in titles:
        k = t.lower()[:60]
        if k not in seen:
            seen.add(k)
            uniq.append(t)
        if len(uniq) >= limit:
            break

    if not uniq:
        return "Global news: no fresh headlines fetched."
    return "Top global headlines:\n  - " + "\n  - ".join(uniq)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def gather_briefing_data(city: str = "Islamabad") -> dict:
    """Run all collectors concurrently and return a dict of strings."""
    tasks = {
        "greeting":    _greeting,
        "weather":     lambda: get_weather(city),
        "pc":          get_pc_status,
        "markets":     get_markets,
        "geopolitics": get_geopolitics,
    }
    results = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut, name in list(futures.items()):
            try:
                results[name] = fut.result(timeout=_TIMEOUT + 4)
            except Exception as e:
                results[name] = f"{name}: unavailable ({str(e)[:30]})."
    return results


def build_briefing_instruction(city: str = "Islamabad") -> str:
    """
    Build the hidden instruction turn that Jarvis speaks on boot.
    Returns a single string to send via session.send_client_content.
    """
    d = gather_briefing_data(city)

    data_block = (
        f"{d.get('greeting','')}\n\n"
        f"WEATHER — {d.get('weather','')}\n\n"
        f"HOST MACHINE — {d.get('pc','')}\n\n"
        f"{d.get('markets','')}\n\n"
        f"{d.get('geopolitics','')}"
    )

    instruction = (
        "[SYSTEM — BOOT BRIEFING]\n"
        "You (J.A.R.V.I.S.) have just come online. Deliver a CRISP, SHORT greeting to the Boss NOW, "
        "out loud, in ONE short natural sentence in your usual Urdu/English mix (e.g. 'Good day sir! "
        "J.A.R.V.I.S. online, all systems operational in Islamabad. How can I assist you today?'). "
        "Keep it under 30 words! Do NOT deliver a long lecture or list all data out loud unless he asks. "
        f"Here is your background data for reference if asked:\n\n{data_block}\n"
    )
    return instruction
