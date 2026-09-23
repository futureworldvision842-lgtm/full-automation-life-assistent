"""Compatibility map feed: observed USGS events and explicitly static geography."""
import time
import threading
import requests
from datetime import datetime, timezone

_lock = threading.Lock()
_cache = {"fetched": 0, "events": [], "ok": False}
SOURCE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
LAYERS = ("conflicts", "bases", "cables", "pipelines", "hotspots", "ais", "nuclear", "sanctions", "weather", "tradeRoutes", "canadaAlerts", "economic", "waterways", "outages", "datacenters", "flights", "military", "natural", "minerals", "fires", "ucdpEvents", "resilienceScore")


def get_layers(geojson=False):
    from actions.world_monitor import get_chokepoints
    with _lock:
        if time.time() - _cache["fetched"] > 60:
            try:
                response = requests.get(SOURCE, timeout=(2, 5), headers={"User-Agent": "Jarvis/1.0"})
                response.raise_for_status()
                events = []
                for feature in response.json().get("features", [])[:150]:
                    coordinates = feature.get("geometry", {}).get("coordinates", [])
                    props = feature.get("properties", {})
                    if len(coordinates) < 3 or not isinstance(props.get("time"), (int, float)):
                        continue
                    events.append({"id": feature.get("id"), "lat": coordinates[1], "lon": coordinates[0],
                        "depth": coordinates[2], "title": props.get("title"), "mag": props.get("mag"),
                        "observed_at": datetime.fromtimestamp(props["time"] / 1000, timezone.utc).isoformat(),
                        "source": props.get("url") or SOURCE, "data_mode": "OBSERVED"})
                _cache.update(events=events, ok=True, fetched=time.time())
            except (requests.RequestException, ValueError, TypeError):
                _cache.update(ok=False, fetched=time.time())
    cps = [{k: item[k] for k in ("id", "name", "lat", "lon", "data_mode", "source")} for item in get_chokepoints()]
    layers = {name: [] for name in LAYERS}
    layers.update(waterways=cps, natural=list(_cache["events"]) if _cache["ok"] else [])
    if geojson:
        features = []
        for layer, rows in layers.items():
            for row in rows:
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]}, "properties": {**row, "layer": layer}})
        return {"type": "FeatureCollection", "features": features}
    return {"layers": layers, "chokepoints": cps, "timestamp": time.time(), "data_mode": "MIXED_REFERENCE_AND_OBSERVED",
        "layer_status": {name: "STATIC_REFERENCE" if name == "waterways" else ("OBSERVED" if name == "natural" and _cache["ok"] else "UNAVAILABLE") for name in LAYERS},
        "warning": "Empty unavailable layers mean no connected feed, not an absence of events. Native World Monitor supplies its own source-labelled layers."}
