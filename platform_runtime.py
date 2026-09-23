"""Shared runtime discovery and health contracts for the unified JARVIS stack.

This module deliberately contains no credentials.  It resolves the bundled
projects relative to the JARVIS checkout, supports explicit environment
overrides, and exposes small provenance-bearing health envelopes that can be
used by the dashboard, terminal, supervisor, and tests.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import requests


JARVIS_ROOT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_existing(env_name: str, candidates: Iterable[Path]) -> Path:
    configured = os.getenv(env_name, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    materialized = [Path(path) for path in candidates]
    for path in materialized:
        if path.exists():
            return path.resolve()
    # Keep a deterministic expected path even before the optional project is
    # installed.  Callers must still check ``exists()`` before claiming it.
    return materialized[0].resolve()


MQ3_ROOT = _first_existing(
    "JARVIS_MQ3_ROOT",
    (
        JARVIS_ROOT / "MQ3 TRADING BOT",
        JARVIS_ROOT.parent / "MQ3 TRADING BOT",
        Path("P:/MQ3 TRADING BOT"),
    ),
)

WORLD_MONITOR_ROOT = _first_existing(
    "JARVIS_WORLD_MONITOR_ROOT",
    (
        Path("F:/worldmonitor-main"),
        JARVIS_ROOT / "worldmonitor-main",
        MQ3_ROOT / "worldmonitor-main",
        Path("P:/Vision Point Work/jarvis/worldmonitor-main"),
    ),
)

GODS_EYE_VIEW_ROOT = _first_existing(
    "JARVIS_GODS_EYE_VIEW_ROOT",
    (
        JARVIS_ROOT / "integrations" / "gods-eye-view",
        JARVIS_ROOT / "gods-eye-view",
        Path("F:/gods-eye-view"),
        JARVIS_ROOT / "apps" / "gods-eye-view",
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def mq3_dashboard_port() -> int:
    raw = os.getenv("JARVIS_MQ3_PORT", "").strip()
    if raw.isdigit() and 1 <= int(raw) <= 65535:
        return int(raw)
    configured = _load_json(MQ3_ROOT / "config.json")
    try:
        port = int(configured.get("bot", {}).get("dashboard_port", 5050))
        return port if 1 <= port <= 65535 else 5050
    except (TypeError, ValueError):
        return 5050


MQ3_DASHBOARD_URL = os.getenv(
    "JARVIS_MQ3_URL", f"http://127.0.0.1:{mq3_dashboard_port()}"
).rstrip("/")
WORLD_MONITOR_URL = os.getenv(
    "JARVIS_WORLD_MONITOR_URL", "http://127.0.0.1:3000"
).rstrip("/")
WORLD_MONITOR_API_URL = os.getenv(
    "JARVIS_WORLD_MONITOR_API_URL", "https://api.worldmonitor.app"
).rstrip("/")
GODS_EYE_VIEW_URL = os.getenv(
    "JARVIS_GODS_EYE_VIEW_URL", "http://127.0.0.1:4173"
).rstrip("/")
WHATSAPP_URL = os.getenv("JARVIS_WHATSAPP_URL", "http://127.0.0.1:3200").rstrip("/")
ODYSSEUS_URL = os.getenv("JARVIS_ODYSSEUS_URL", "http://127.0.0.1:7000").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DASHBOARD_URL = os.getenv("JARVIS_DASHBOARD_URL", "http://127.0.0.1:8770").rstrip("/")
MOBILE_URL = os.getenv("JARVIS_MOBILE_URL", "http://127.0.0.1:8765").rstrip("/")
WA_LOCAL_CONFIG = JARVIS_ROOT / "config" / "wa.local.json"
INTERNAL_LOCAL_CONFIG = JARVIS_ROOT / "config" / "internal.local.json"

CORE_SERVICES: dict[str, dict[str, Any]] = {
    "dashboard": {
        "name": "Master Operations Command Center",
        "port": 8770,
        "url": f"{DASHBOARD_URL}/api/health",
        "type": "http",
        "description": "Central Operations Command Center and Web HUD",
    },
    "world_monitor": {
        "name": "World Monitor Live Geospatial Radar",
        "port": 3000,
        "url": WORLD_MONITOR_URL,
        "type": "http",
        "description": "Live geospatial intelligence radar and 22 layers",
    },
    "gods_eye_view": {
        "name": "God's Eye View 3D Globe",
        "port": 4173,
        "url": GODS_EYE_VIEW_URL,
        "type": "http",
        "description": "Photorealistic 3D tactical globe and spatial radar",
    },
    "mq3": {
        "name": "MQ3 Institutional Trading Cockpit",
        "port": mq3_dashboard_port(),
        "url": f"{MQ3_DASHBOARD_URL}/api/status",
        "type": "http",
        "description": "Multi-account quantitative trading and risk cockpit",
    },
    "odysseus": {
        "name": "Odysseus AI Brain",
        "port": 7000,
        "url": f"{ODYSSEUS_URL}/api/health",
        "type": "http",
        "description": "Multi-agent cognitive reasoning and consensus engine",
    },
    "ollama": {
        "name": "Ollama Local LLM Node",
        "port": 11434,
        "url": f"{OLLAMA_URL}/api/tags",
        "type": "http",
        "description": "Offline local LLM node with qwen2.5:0.5b",
    },
    "mobile": {
        "name": "Mobile Companion & Remote Gateway",
        "port": 8765,
        "url": f"{MOBILE_URL}/api/health",
        "type": "http",
        "description": "Mobile remote console, PWA, and screen stream",
    },
    "trader": {
        "name": "24/7 Autonomous Multi-Account Trader Daemon",
        "port": 0,
        "url": "proc:autonomous_live_daemon.py",
        "type": "proc",
        "description": "24/7 autonomous position manager and breakeven lock",
    },
    "discord": {
        "name": "Discord Dual-Channel Intelligence Bot",
        "port": 0,
        "url": "proc:discord_bot.py",
        "type": "proc",
        "description": "Dual-channel signals (#elite-trade and #crypto-bot)",
    },
}


def is_process_running(pattern: str) -> bool:
    """Check if any active process command line contains pattern."""
    if not pattern:
        return False
    pat = pattern.lower()
    try:
        import psutil
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or []).lower()
                if pat in cmd:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return False


def check_tcp_connection(host: str, port: int, timeout: float = 0.5) -> bool:
    """Test raw TCP connection to host:port."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wa_http_token() -> str:
    """Return the local WhatsApp HTTP token, creating an ignored token once."""
    configured = os.getenv("JARVIS_WA_HTTP_TOKEN", "").strip()
    if configured:
        return configured
    payload = _load_json(WA_LOCAL_CONFIG)
    token = str(payload.get("http_token") or "").strip()
    if token:
        return token
    token = secrets.token_urlsafe(32)
    WA_LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    WA_LOCAL_CONFIG.write_text(
        json.dumps({"http_token": token}, indent=2), encoding="utf-8"
    )
    return token


def internal_command_token() -> str:
    """Return a local service-to-service token for channel-bound approvals."""
    configured = os.getenv("JARVIS_INTERNAL_COMMAND_TOKEN", "").strip()
    if configured:
        return configured
    payload = _load_json(INTERNAL_LOCAL_CONFIG)
    token = str(payload.get("command_token") or "").strip()
    if token:
        return token
    token = secrets.token_urlsafe(32)
    INTERNAL_LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    INTERNAL_LOCAL_CONFIG.write_text(
        json.dumps({"command_token": token}, indent=2), encoding="utf-8"
    )
    return token


@dataclass(frozen=True)
class ServiceProbe:
    name: str
    url: str
    available: bool
    status: str
    checked_at: str
    latency_ms: int | None = None
    http_status: int | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


def probe_service(name: str, url: str, timeout: float = 1.5) -> ServiceProbe:
    started = time.perf_counter()
    if url.startswith("proc:"):
        marker = url[5:]
        active = is_process_running(marker)
        latency = int((time.perf_counter() - started) * 1000)
        return ServiceProbe(
            name=name,
            url=url,
            available=active,
            status="online" if active else "offline",
            checked_at=utc_now(),
            latency_ms=latency,
            http_status=None,
            error=None if active else "Daemon process offline",
            details={"type": "daemon_process", "marker": marker},
        )

    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "JARVIS/1.0"})
        latency = int((time.perf_counter() - started) * 1000)
        available = 200 <= response.status_code < 300
        details = None
        if name == "whatsapp" and available:
            try:
                payload = response.json()
                connected = bool(payload.get("ready"))
                details = {
                    "bridge_online": True,
                    "whatsapp_connected": connected,
                    "pairing_required": not connected,
                }
            except (ValueError, TypeError):
                details = {
                    "bridge_online": True,
                    "whatsapp_connected": False,
                    "pairing_required": None,
                }
        return ServiceProbe(
            name=name,
            url=url,
            available=available,
            status="online" if available else "degraded",
            checked_at=utc_now(),
            latency_ms=latency,
            http_status=response.status_code,
            error=None if available else f"HTTP {response.status_code}",
            details=details,
        )
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        # Fallback to TCP connection verification if HTTP failed
        tcp_ok = False
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            # Guard against invalid ports
            if parsed.hostname:
                try:
                    port = parsed.port
                    if port and 0 < port <= 65535:
                        tcp_ok = check_tcp_connection(parsed.hostname, port, timeout=0.5)
                except (ValueError, TypeError):
                    tcp_ok = False
        except Exception:
            tcp_ok = False

        if tcp_ok:
            return ServiceProbe(
                name=name,
                url=url,
                available=True,
                status="online",
                checked_at=utc_now(),
                latency_ms=latency,
                http_status=None,
                error=None,
                details={"fallback": "tcp_port_active"},
            )
        return ServiceProbe(
            name=name,
            url=url,
            available=False,
            status="offline",
            checked_at=utc_now(),
            latency_ms=latency,
            error=f"{type(exc).__name__}: {exc}",
            details=None,
        )


def runtime_snapshot(include_public_api: bool = False, full_fleet: bool = False) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    specs = [
        ("dashboard", f"{DASHBOARD_URL}/api/health"),
        ("world_monitor", WORLD_MONITOR_URL),
        ("gods_eye_view", GODS_EYE_VIEW_URL),
        ("mq3", f"{MQ3_DASHBOARD_URL}/api/status"),
        ("odysseus", f"{ODYSSEUS_URL}/api/health"),
    ]
    if full_fleet:
        specs.extend([
            ("ollama", f"{OLLAMA_URL}/api/tags"),
            ("mobile", f"{MOBILE_URL}/api/health"),
            ("trader", "proc:autonomous_live_daemon.py"),
            ("discord", "proc:discord_bot.py"),
        ])
    if (JARVIS_ROOT / "wa/node_modules/@whiskeysockets/baileys").exists():
        specs.append(("whatsapp", f"{WHATSAPP_URL}/status"))
    if include_public_api:
        specs.append(("world_monitor_public_api", f"{WORLD_MONITOR_API_URL}/api/health?compact=1"))

    probes_map = {}
    with ThreadPoolExecutor(max_workers=len(specs)) as ex:
        futures = {ex.submit(probe_service, name, url, 0.8): name for name, url in specs}
        for f in as_completed(futures):
            name = futures[f]
            try:
                probes_map[name] = asdict(f.result())
            except Exception:
                pass

    probes = [probes_map.get(name, asdict(probe_service(name, url, 0.1))) for name, url in specs]
    return {
        "status": "online" if all(item["available"] for item in probes) else "degraded",
        "checked_at": utc_now(),
        "services": probes,
        "projects": {
            "jarvis": {"path": str(JARVIS_ROOT), "available": JARVIS_ROOT.exists()},
            "mq3": {"path": str(MQ3_ROOT), "available": MQ3_ROOT.exists()},
            "world_monitor": {
                "path": str(WORLD_MONITOR_ROOT),
                "available": WORLD_MONITOR_ROOT.exists(),
            },
            "gods_eye_view": {
                "path": str(GODS_EYE_VIEW_ROOT),
                "available": GODS_EYE_VIEW_ROOT.exists(),
            },
        },
        "safety": {
            "dashboard_bind_default": "127.0.0.1",
            "mq3_live_execution_default": "BLOCKED",
            "external_actions_require_owner_approval": True,
        },
    }


def data_envelope(
    *,
    source: str,
    data: Any,
    observed_at: str | None = None,
    status: str = "live",
    error: str | None = None,
    stale_after_seconds: int | None = None,
) -> dict[str, Any]:
    """Return a consistent truth/provenance wrapper for dashboard data."""
    fetched_at = utc_now()
    return {
        "status": status,
        "source": source,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
        "stale_after_seconds": stale_after_seconds,
        "error": error,
        "data": data,
    }


def public_urls() -> dict[str, str]:
    return {
        "mq3": MQ3_DASHBOARD_URL,
        "world_monitor": WORLD_MONITOR_URL,
        "world_monitor_api": WORLD_MONITOR_API_URL,
        "gods_eye_view": GODS_EYE_VIEW_URL,
        "whatsapp_qr": f"{WHATSAPP_URL}/qr",
        "odysseus": ODYSSEUS_URL,
    }


def get_terminal_dashboard_data() -> dict[str, Any]:
    """Terminal Visualizer ↔ Platform Runtime Interface Contract."""
    from ui.rich_terminal_dashboard import get_terminal_dashboard_data as _get_data
    return _get_data()
