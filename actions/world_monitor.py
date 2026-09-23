"""
world_monitor — Source-labelled global intelligence for J.A.R.V.I.S.

Integrates the curated RSS sources from the worldmonitor project
(https://github.com/koala73/worldmonitor) into Jarvis: pulls live headlines
across geopolitical / regional / finance / defense categories, optionally
AI-synthesizes a spoken brief, and feeds the HUD "WORLD MONITOR" tab.

Usable two ways:
  - get_headlines(category, limit)      -> list[dict] (for the HUD, no AI)
  - world_monitor(parameters, ...)      -> str brief (for the voice tool)
"""
import calendar
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone

import xml.etree.ElementTree as ET

try:
    import feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    feedparser = None
    _HAS_FEEDPARSER = False

class _SimpleEntry:
    def __init__(self, title="", link="", published_parsed=None):
        self.title = title
        self.link = link
        self.published_parsed = published_parsed
        self.updated_parsed = published_parsed

class _SimpleFeed:
    def __init__(self, entries=None):
        self.entries = entries or []

def _fallback_parse(content_or_url):
    try:
        if isinstance(content_or_url, (bytes, str)) and (b"<" in content_or_url if isinstance(content_or_url, bytes) else "<" in content_or_url):
            root = ET.fromstring(content_or_url)
        else:
            return _SimpleFeed([])
        entries = []
        for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            t = item.find("title")
            if t is None:
                t = item.find("{http://www.w3.org/2005/Atom}title")
            title = t.text.strip() if (t is not None and t.text) else ""
            l = item.find("link")
            if l is None:
                l = item.find("{http://www.w3.org/2005/Atom}link")
            link = l.text.strip() if (l is not None and l.text) else ""
            if not link and l is not None:
                link = l.attrib.get("href", "")
            entries.append(_SimpleEntry(title=title, link=link))
        return _SimpleFeed(entries)
    except Exception:
        return _SimpleFeed([])

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


# --- Curated feed set, mirroring worldmonitor's FULL_FEEDS / INTEL_SOURCES ---
# Direct RSS URLs (no proxy). Kept to reliable, mostly-English high-tier sources.
WORLD_FEEDS = {
    "world": [
        ("BBC World",     "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Guardian World","https://www.theguardian.com/world/rss"),
        ("Al Jazeera",    "https://www.aljazeera.com/xml/rss/all.xml"),
        ("Reuters World", "https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en"),
        ("AP News",       "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en"),
        ("UN News",       "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
    ],
    "us": [
        ("NPR News",   "https://feeds.npr.org/1001/rss.xml"),
        ("PBS NewsHour","https://www.pbs.org/newshour/feeds/rss/headlines"),
        ("NBC News",   "https://feeds.nbcnews.com/nbcnews/public/news"),
        ("Politico",   "https://rss.politico.com/politics-news.xml"),
        ("The Hill",   "https://thehill.com/news/feed"),
    ],
    "europe": [
        ("Euronews",  "https://www.euronews.com/rss?format=xml"),
        ("DW News",   "https://rss.dw.com/xml/rss-en-all"),
        ("France 24", "https://www.france24.com/en/rss"),
        ("BBC Europe","https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ],
    "middleeast": [
        ("BBC Middle East","https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
        ("Al Jazeera ME",  "https://www.aljazeera.com/xml/rss/all.xml"),
        ("Times of Israel","https://www.timesofisrael.com/feed/"),
    ],
    "asia": [
        ("NHK World",   "https://www3.nhk.or.jp/nhkworld/en/news/rss/c_all.xml"),
        ("BBC Asia",    "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
        ("Nikkei Asia", "https://news.google.com/rss/search?q=site:asia.nikkei.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("South China Morning Post","https://www.scmp.com/rss/91/feed"),
    ],
    "africa": [
        ("BBC Africa",  "https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
        ("AllAfrica",   "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    ],
    "latam": [
        ("BBC Latin America","https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
        ("MercoPress",       "https://en.mercopress.com/rss/"),
    ],
    "tech": [
        ("The Verge",   "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica","https://feeds.arstechnica.com/arstechnica/index"),
        ("TechCrunch",  "https://techcrunch.com/feed/"),
        ("Hacker News", "https://hnrss.org/frontpage"),
    ],
    "ai": [
        ("Google News AI","https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("VentureBeat AI","https://venturebeat.com/category/ai/feed/"),
        ("MIT Tech Review","https://www.technologyreview.com/feed/"),
    ],
    "finance": [
        ("CNBC",        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
        ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
        ("FT",          "https://news.google.com/rss/search?q=site:ft.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("Yahoo Finance","https://finance.yahoo.com/news/rssindex"),
    ],
    "energy": [
        ("OilPrice",    "https://oilprice.com/rss/main"),
        ("Reuters Energy","https://news.google.com/rss/search?q=energy+oil+gas+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ],
    "defense": [
        ("Defense One",   "https://www.defenseone.com/rss/all/"),
        ("The War Zone",  "https://www.twz.com/feed"),
        ("Defense News",  "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("Task & Purpose","https://taskandpurpose.com/feed/"),
        ("UK MOD",        "https://www.gov.uk/government/organisations/ministry-of-defence.atom"),
    ],
    "crisis": [
        ("ReliefWeb",   "https://reliefweb.int/updates/rss.xml"),
        ("CrisisWatch", "https://news.google.com/rss/search?q=site:crisisgroup.org+when:3d&hl=en-US&gl=US&ceid=US:en"),
    ],
    "gold": [
        ("Kitco Gold",   "https://news.google.com/rss/search?q=gold+price+xauusd+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("FXStreet Gold","https://news.google.com/rss/search?q=site:fxstreet.com+gold+xauusd+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ],
    "forex": [
        ("DailyFX",      "https://news.google.com/rss/search?q=site:dailyfx.com+forex+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("ForexLive",    "https://news.google.com/rss/search?q=site:forexlive.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ],
}

# Friendly aliases so voice commands map to a category.
CATEGORY_ALIASES = {
    "global": "world", "news": "world", "headlines": "world", "geopolitics": "world",
    "america": "us", "usa": "us", "united states": "us",
    "mideast": "middleeast", "middle east": "middleeast", "gulf": "middleeast",
    "technology": "tech",
    "artificial intelligence": "ai",
    "markets": "finance", "stocks": "finance", "economy": "finance",
    "military": "defense", "war": "defense", "intel": "defense", "intelligence": "defense",
    "disaster": "crisis", "humanitarian": "crisis",
}

CATEGORIES = list(WORLD_FEEDS.keys())
_UA = {"User-Agent": "Mozilla/5.0 (JARVIS WorldMonitor)"}
_MAX_HEADLINE_AGE_SECONDS = 7 * 24 * 60 * 60
_FEED_HEALTH: dict[str, list[dict]] = {}


def _iso_utc(timestamp: float | int | None) -> str | None:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _resolve_category(cat: str) -> str:
    if not cat:
        return "world"
    c = cat.strip().lower()
    if c in WORLD_FEEDS:
        return c
    return CATEGORY_ALIASES.get(c, "world")


def _fetch_feed(name: str, url: str, per_feed: int = 5):
    items = []
    fetched_at = time.time()
    try:
        if _HAS_FEEDPARSER and feedparser is not None:
            if _HAS_REQUESTS:
                resp = requests.get(url, headers=_UA, timeout=8)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.content)
            else:
                parsed = feedparser.parse(url)
        else:
            if _HAS_REQUESTS:
                resp = requests.get(url, headers=_UA, timeout=8)
                resp.raise_for_status()
                parsed = _fallback_parse(resp.content)
            else:
                parsed = _fallback_parse(b"")
        for e in parsed.entries[:per_feed]:
            title = (getattr(e, "title", "") or "").strip()
            if not title:
                continue
            ts = 0
            for attr in ("published_parsed", "updated_parsed"):
                tp = getattr(e, attr, None)
                if tp:
                    ts = calendar.timegm(tp)
                    break
            age = max(0, int(fetched_at - ts)) if ts else None
            if age is not None and age > _MAX_HEADLINE_AGE_SECONDS:
                continue
            items.append({
                "source": name,
                "source_url": url,
                "title": title,
                "link": getattr(e, "link", ""),
                "ts": ts,
                "published_at": _iso_utc(ts),
                "fetched_at": _iso_utc(fetched_at),
                "age_seconds": age,
                "stale_after_seconds": _MAX_HEADLINE_AGE_SECONDS,
                "freshness": "CURRENT" if age is not None else "TIMESTAMP_UNAVAILABLE",
                "data_mode": "RSS_OBSERVATION",
            })
        return items, {
            "source": name, "source_url": url, "ok": True,
            "items": len(items), "checked_at": _iso_utc(fetched_at), "error": None,
        }
    except Exception as exc:
        return [], {
            "source": name, "source_url": url, "ok": False, "items": 0,
            "checked_at": _iso_utc(fetched_at),
            "error": f"{type(exc).__name__}: {str(exc)[:160]}",
        }


_FEED_CACHE = {}

def get_headlines(category: str = "world", limit: int = 10) -> list:
    """Fetch + merge headlines for a category. No AI. Used by HUD and the tool."""
    cat = _resolve_category(category)
    now = time.time()
    if cat in _FEED_CACHE and (now - _FEED_CACHE[cat]["ts"] < 45):
        return _FEED_CACHE[cat]["data"][:limit]

    feeds = WORLD_FEEDS.get(cat, WORLD_FEEDS["world"])
    all_items = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as ex:
        futs = {ex.submit(_fetch_feed, n, u): n for n, u in feeds}
        health = []
        for f in as_completed(futs):
            fetched, state = f.result()
            all_items.extend(fetched)
            health.append(state)
    _FEED_HEALTH[cat] = sorted(health, key=lambda item: item["source"])

    # Dedupe by lowercased title, newest first.
    seen, deduped = set(), []
    for it in sorted(all_items, key=lambda x: x["ts"], reverse=True):
        k = it["title"].lower()[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    
    if deduped:
        _FEED_CACHE[cat] = {"ts": now, "data": deduped}
    return deduped[:limit]


def get_feed_health(category: str = "world") -> dict:
    """Return the most recent per-source fetch result for a category."""
    cat = _resolve_category(category)
    if cat not in _FEED_HEALTH:
        get_headlines(cat, 1)
    sources = _FEED_HEALTH.get(cat, [])
    healthy = sum(1 for item in sources if item.get("ok"))
    return {
        "category": cat,
        "status": "observed" if healthy else "unavailable",
        "healthy_sources": healthy,
        "total_sources": len(sources),
        "checked_at": _iso_utc(time.time()),
        "sources": sources,
    }


def _synthesize_brief(category: str, items: list) -> str:
    """Use the shared local-first router, or return a source-labelled list."""
    headlines = "\n".join(f"- [{it['source']}] {it['title']}" for it in items)
    if not headlines:
        return f"Sir, I couldn't pull any fresh {category} headlines right now."
    from ai_engine import query_ai_detailed

    prompt = (
        f"Give a concise spoken {category} intelligence brief based only on the supplied "
        "source-labelled RSS observations. Separate reported facts from inference, do not "
        "call unknown-timestamp items fresh, and make no trading recommendation. Use 4-6 "
        f"developments, under 130 words.\n\nHeadlines:\n{headlines}"
    )
    result = query_ai_detailed(prompt, timeout=18)
    if result.get("ok") and str(result.get("text") or "").strip():
        return str(result["text"]).strip()
    lines = [f"Here are source-retrieved {category} headlines; no AI synthesis is available:"]
    lines += [
        f"{i+1}. {it['title']} ({it['source']}; {it.get('freshness', 'UNKNOWN')})"
        for i, it in enumerate(items[:6])
    ]
    return "\n".join(lines)


def get_weather(city: str = "Islamabad") -> dict:
    """Quick weather via wttr.in (no API key). Returns {} on failure."""
    if not _HAS_REQUESTS:
        return {}
    try:
        r = requests.get(
            f"https://wttr.in/{city}?format=j1", headers=_UA, timeout=14
        )
        data = r.json()
        cur = data["current_condition"][0]
        return {
            "city": city,
            "temp_c": cur.get("temp_C"),
            "feels_c": cur.get("FeelsLikeC"),
            "desc": (cur.get("weatherDesc", [{}])[0].get("value", "")).strip(),
            "humidity": cur.get("humidity"),
            "wind_kph": cur.get("windspeedKmph"),
        }
    except Exception:
        return {}


def get_markets() -> list:
    """Live market snapshot (no key) via Yahoo Finance chart API. Returns list of dicts."""
    if not _HAS_REQUESTS:
        return []
    syms = [("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq"), ("^DJI", "Dow Jones"),
            ("CL=F", "Crude Oil"), ("GC=F", "Gold"), ("BTC-USD", "Bitcoin")]
    out = []
    def _one(sym, name):
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                headers=_UA, timeout=8)
            m = r.json()["chart"]["result"][0]["meta"]
            price = m.get("regularMarketPrice")
            prev = m.get("chartPreviousClose") or m.get("previousClose")
            chg = ((price - prev) / prev * 100) if (price and prev) else 0.0
            return {
                "name": name,
                "price": price,
                "chg": chg,
                "source": "Yahoo Finance chart API",
                "source_url": f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                "observed_at": _iso_utc(m.get("regularMarketTime")),
                "fetched_at": _iso_utc(time.time()),
                "stale_after_seconds": 90,
                "data_mode": "PUBLIC_MARKET_FEED",
            }
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_one, s, n) for s, n in syms]
        for f in as_completed(futs):
            r = f.result()
            if r:
                out.append(r)
    # keep stable order
    order = {n: i for i, (_, n) in enumerate(syms)}
    return sorted(out, key=lambda x: order.get(x["name"], 99))


def get_chokepoints() -> list:
    """Return reference geography only; live threat/transit data lives in World Monitor.

    The previous implementation attached hard-coded threat scores and called
    them real-time.  That was unsafe for both situational awareness and trading,
    so this compatibility endpoint now labels its static facts explicitly.
    """
    return [
        {
            "id": "hormuz",
            "name": "Strait of Hormuz",
            "lat": 26.5667, "lon": 56.2500,
            "baseline_mbd": 21.0,
            "threat_level": "UNAVAILABLE", "threat_score": None, "risk_multiplier": None,
            "status": "Reference location only — use the embedded World Monitor for live data",
            "data_mode": "STATIC_REFERENCE", "source": "JARVIS chokepoint registry"
        },
        {
            "id": "bab_el_mandeb",
            "name": "Bab el-Mandeb Strait",
            "lat": 12.5833, "lon": 43.3333,
            "baseline_mbd": 6.2,
            "threat_level": "UNAVAILABLE", "threat_score": None, "risk_multiplier": None,
            "status": "Reference location only — use the embedded World Monitor for live data",
            "data_mode": "STATIC_REFERENCE", "source": "JARVIS chokepoint registry"
        },
        {
            "id": "suez",
            "name": "Suez Canal",
            "lat": 29.9753, "lon": 32.5599,
            "baseline_mbd": 7.6,
            "threat_level": "UNAVAILABLE", "threat_score": None, "risk_multiplier": None,
            "status": "Reference location only — use the embedded World Monitor for live data",
            "data_mode": "STATIC_REFERENCE", "source": "JARVIS chokepoint registry"
        },
        {
            "id": "malacca",
            "name": "Strait of Malacca",
            "lat": 2.5000, "lon": 101.5000,
            "baseline_mbd": 17.2,
            "threat_level": "UNAVAILABLE", "threat_score": None, "risk_multiplier": None,
            "status": "Reference location only — use the embedded World Monitor for live data",
            "data_mode": "STATIC_REFERENCE", "source": "JARVIS chokepoint registry"
        },
        {
            "id": "taiwan_strait",
            "name": "Taiwan Strait",
            "lat": 23.6978, "lon": 120.9605,
            "baseline_mbd": 4.5,
            "threat_level": "UNAVAILABLE", "threat_score": None, "risk_multiplier": None,
            "status": "Reference location only — use the embedded World Monitor for live data",
            "data_mode": "STATIC_REFERENCE", "source": "JARVIS chokepoint registry"
        }
    ]


def get_earthquakes() -> list:
    """Pulls real-time global earthquakes (M2.5+) from official USGS GeoJSON feed."""
    if not _HAS_REQUESTS:
        return []
    try:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        r = requests.get(url, headers=_UA, timeout=6)
        if r.status_code == 200:
            features = r.json().get("features", [])[:10]
            quakes = []
            for f in features:
                props = f.get("properties", {})
                geom = f.get("geometry", {})
                coords = geom.get("coordinates", [0, 0, 0])
                quakes.append({
                    "title": props.get("title", ""),
                    "mag": props.get("mag", 0.0),
                    "place": props.get("place", ""),
                    "time": props.get("time", 0),
                    "lat": coords[1],
                    "lon": coords[0]
                })
            return quakes
    except Exception:
        pass
    return []


def get_shock_engine() -> dict:
    """Fail closed until provenance-bearing live threat telemetry is attached."""
    return {
        "status": "unavailable",
        "defcon_level": None,
        "geopolitical_tension_score": None,
        "chokepoints_monitored": 0,
        "asset_bias_multipliers": {},
        "actionable": False,
        "reason": (
            "The compatibility RSS adapter has no provenance-bearing live chokepoint telemetry. "
            "Use the embedded World Monitor source-health panels; trading risk must not be "
            "changed from static or headline-only data."
        ),
    }


def get_conflict() -> list:
    """Defense + crisis headlines merged, newest first (for the Conflict Monitor)."""
    items = get_headlines("defense", 10) + get_headlines("crisis", 8)
    seen, dedup = set(), []
    for it in sorted(items, key=lambda x: x["ts"], reverse=True):
        k = it["title"].lower()[:70]
        if k in seen:
            continue
        seen.add(k)
        dedup.append(it)
    return dedup[:14]


def get_situation_brief() -> str:
    """Forward-looking world situation + 'what happens next' outlook (AI)."""
    items = get_headlines("world", 16)
    if not items:
        return "Global situation feed unavailable right now, Sir."
    headlines = "\n".join(f"- {it['title']}" for it in items)
    from ai_engine import query_ai_detailed

    prompt = (
        "Based only on these source-retrieved RSS observations, write three concise "
        "sentences on reported developments and two clearly labelled inference sentences "
        "on possible next developments. Do not invent facts. Under 110 words.\n\n" + headlines
    )
    result = query_ai_detailed(prompt, timeout=18)
    if result.get("ok"):
        return str(result.get("text") or "").strip()
    return "Source-retrieved developments (no AI synthesis): " + "; ".join(
        f"{it['title']} [{it['source']}]" for it in items[:4]
    )


def world_monitor(parameters: dict = None, player=None, speak=None, **kwargs) -> str:
    """Voice tool entrypoint. parameters: {category, limit, brief}."""
    parameters = parameters or {}
    category = _resolve_category(parameters.get("category", "world"))
    limit = int(parameters.get("limit", 10) or 10)
    want_brief = parameters.get("brief", True)

    if player is not None:
        try:
            player.write_log(f"WORLD MONITOR: Fetching source-labelled {category} observations...")
        except Exception:
            pass

    items = get_headlines(category, limit)

    # Push to the HUD tab if the UI exposes the hook.
    if player is not None:
        for hook in ("update_world_monitor", "set_world_headlines"):
            fn = getattr(player, hook, None)
            if callable(fn):
                try:
                    fn(category, items)
                except Exception:
                    pass
                break

    if want_brief:
        return _synthesize_brief(category, items)
    if not items:
        return f"Sir, no fresh {category} headlines available right now."
    return "\n".join(f"{i+1}. {it['title']} ({it['source']})" for i, it in enumerate(items))


if __name__ == "__main__":
    cat = sys.argv[1] if len(sys.argv) > 1 else "world"
    print(world_monitor({"category": cat, "brief": False}))
