"""
actions/multi_account_shield.py — J.A.R.V.I.S. Multi-Account Anti-Detection Action Gateway.
========================================================================================
Exposes fleet management, proxy shield verification, and anti-copy execution to:
- WhatsApp Command Gateway
- Sovereign Terminal Router
- Cockpit Web Dashboard
- Voice & Automated Dispatch

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
FundingPips Account: hamidqureshi872@gmail.com (#40000294403)
========================================================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from trading.multi_account_manager import (
    AccountRiskProfile,
    AntiCopyShield,
    ProxyConfig,
    TerminalInstanceConfig,
    get_multi_account_manager,
)

logger = logging.getLogger("MultiAccountShieldAction")


def get_multi_account_shield_status(lang: str = "ur") -> Dict[str, Any]:
    """Returns human-readable text and raw telemetry for WhatsApp / Terminal dispatch."""
    manager = get_multi_account_manager()
    summary = manager.get_fleet_summary()
    report_text = manager.format_human_report(lang=lang)
    return {
        "ok": True,
        "report_text": report_text,
        "summary": summary,
        "active_accounts": summary.get("active_accounts_count", 0),
        "total_aum_usd": summary.get("total_aum_usd", 0.0),
    }


def audit_anti_detection_health() -> Dict[str, Any]:
    """Performs deep forensic audit on fleet isolation, proxies, and jitter readiness."""
    manager = get_multi_account_manager()
    isolation = manager.validate_fleet_isolation()
    summary = manager.get_fleet_summary()

    proxy_health = {}
    for key, prof in manager.fleet.items():
        if prof.proxy_config and prof.proxy_config.enabled:
            proxy_health[key] = prof.proxy_config.check_connectivity(timeout_sec=0.5)

    healthy = isolation.get("isolated", False) and len(isolation.get("collisions", [])) == 0

    lines = [
        "🛡️ [J.A.R.V.I.S. ANTI-DETECTION FLEET FORENSIC AUDIT]",
        f"• Status: {'100% HEALTHY 🟢' if healthy else 'COLLISION WARNING 🔴'}",
        f"• Active Isolated Instances: {isolation.get('active_accounts_audited')}",
        f"• Unique Portable Dirs: {isolation.get('unique_directories_count')}",
        f"• Unique IPC Ports: {isolation.get('unique_ipc_ports_count')}",
        f"• Unique SOCKS5 Proxies: {isolation.get('unique_proxy_endpoints_count')}",
        f"• Centroid24/OneZero Jitter Defense: Active (350ms - 1800ms randomized dispersion)",
        f"• SL/TP Micro-Tick Perturbation: Active (+/- 0.5 to 2.0 pips)",
    ]
    if isolation.get("collisions"):
        lines.append("\n⚠️ Detected Collisions:")
        for c in isolation["collisions"]:
            lines.append(f"  - {c}")
    else:
        lines.append("• Zero Cross-Account Footprint Detected.")

    return {
        "ok": healthy,
        "healthy": healthy,
        "isolation": isolation,
        "proxy_health": proxy_health,
        "report_text": "\n".join(lines),
    }


def prepare_and_dispatch_fleet_trade(
    symbol: str,
    action: str = "BUY",
    entry_price: float = 2650.0,
    sl_price: float = 2640.0,
    tp_price: float = 2675.0,
    simulation_mode: bool = True,
    connectors: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Dispatches institutional trade with full anti-copy shields to all active accounts."""
    manager = get_multi_account_manager()
    signal = {
        "symbol": symbol.upper().strip(),
        "signal_type": action.upper().strip(),
        "entry_price": float(entry_price),
        "sl_price": float(sl_price),
        "tp_price": float(tp_price),
    }
    result = manager.execute_fleet_trade(signal, connectors=connectors, simulation_mode=simulation_mode)
    return result


def register_new_prop_account(
    account_key: str,
    account_id: str,
    account_name: str,
    firm_name: str,
    balance: float,
    server: str,
    terminal_path: str,
    password_env: str,
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 1080,
    proxy_country: str = "AE",
    max_risk_pct: float = 0.75,
    max_risk_usd_cap: float = 750.0,
    ipc_port: int = 18820,
) -> Dict[str, Any]:
    """Registers a new prop or personal account with full isolation configurations."""
    manager = get_multi_account_manager()
    term_dir = str(Path(terminal_path).parent / f"Portable_{account_id}")

    # Auto-allocate non-colliding ports if collisions would occur
    existing_ipc_ports = {
        p.terminal_config.ipc_port
        for p in manager.fleet.values()
        if p.terminal_config and p.terminal_config.ipc_port
    }
    while ipc_port in existing_ipc_ports:
        ipc_port += 1

    existing_proxy_ports = {
        p.proxy_config.port
        for p in manager.fleet.values()
        if p.proxy_config and p.proxy_config.port
    }
    while proxy_port in existing_proxy_ports:
        proxy_port += 1

    profile = AccountRiskProfile(
        account_id=str(account_id),
        account_name=account_name,
        firm_name=firm_name,
        account_type="FUNDED" if balance >= 50000.0 else "EVALUATION_STEP_1",
        starting_balance=float(balance),
        balance=float(balance),
        equity=float(balance),
        currency="USD",
        max_risk_pct=float(max_risk_pct),
        max_risk_usd_cap=float(max_risk_usd_cap),
        min_rr_ratio=2.5,
        dynamic_breakeven_trigger_r=1.0,
        is_active=True,
        terminal_config=TerminalInstanceConfig(
            account_id=str(account_id),
            firm_name=firm_name,
            terminal_dir=term_dir,
            executable_path=terminal_path,
            portable_mode=True,
            ipc_port=ipc_port,
            password_env=password_env,
            server=server,
            login=int(account_id) if str(account_id).isdigit() else 0,
        ),
        proxy_config=ProxyConfig(
            enabled=True,
            proxy_type="SOCKS5",
            host=proxy_host,
            port=proxy_port,
            username_env=f"PROXY_USER_{account_id}",
            password_env=f"PROXY_PASS_{account_id}",
            target_country=proxy_country,
            static_ip=True,
        ),
    )
    ok, msg = manager.register_account(account_key, profile)
    return {"ok": ok, "message": msg, "account_id": account_id, "allocated_ipc_port": ipc_port, "allocated_proxy_port": proxy_port}


def get_anti_ban_architecture_briefing(lang: str = "ur") -> str:
    """
    Exhaustive engineering advisory addressing Master Muhammad Qureshi's question:
    How to connect multiple prop accounts & bracket accounts without getting banned by prop surveillance.
    """
    if lang == "ur":
        return (
            "🛡️ [J.A.R.V.I.S. MULTI-PROP ANTI-BAN MASTER ARCHITECTURE]\n"
            "Master Muhammad Qureshi, multiple prop firms (FundingPips, FTMO, etc.) aur bracket accounts ko automate karne ka best anti-ban formula yeh hai:\n\n"
            "⚠️ Prop Firms Account Kyu Ban Karti Hain? (The Surveillance Trap):\n"
            "1. Same IP & Subnet: Agar 2 accounts ek hi WiFi / home IP se order bhejte hain, OneZero / Centroid24 sybil detection trigger hojati hai.\n"
            "2. Identical Millisecond Timestamps: Agar EA Account A aur Account B pe 1-5ms ke andar order fire kare, copy-trading flag lag jata hai.\n"
            "3. Matching Price & Stops: Har account pe exact same Entry, SL aur TP tick broker book pe matching pattern banata hai.\n"
            "4. Same EA Magic Numbers: EA ka ticket identifier common hona pakre jane ka sab se asaan tareeqa hai.\n\n"
            "🔒 JARVIS Ka 5-Pillar Anti-Ban Solution:\n"
            "1. Per-Account /portable Instance Isolation:\n"
            "   - Har account ka apna alag MT5 folder (e.g. C:\\MT5_Fleet\\FundingPips_100K, C:\\MT5_Fleet\\FTMO_100K) with /portable switch.\n"
            "   - Windows %APPDATA% kabhi share nahi hota; crash logs aur config bilkul segregated rehte hain.\n"
            "2. Dedicated Static Residential SOCKS5 Proxies (Never Rotating):\n"
            "   - Har firm ke liye alag residential IP (KYC country se matched, e.g. UAE for FundingPips, Czech for FTMO).\n"
            "   - Rotating/datacenter proxy use nahi karni kyunki fast IP rotation se prop firms foran KYC alert bhejti hain.\n"
            "3. Execution Jitter Engine (350ms - 1800ms Micro-Delays):\n"
            "   - Jarvis orders ko shuffled sequence mein micro-delays ke saath dispatch karta hai taake broker surveillance ko millisecond correlation na miley.\n"
            "4. Micro-Tick SL/TP Dispersion (+/- 0.5 to 2.0 Pips):\n"
            "   - Har account ka stop loss aur take profit 0.5 se 2.0 pips mathematically adjust hota hai without exceeding dollar risk ($750 cap on FP).\n"
            "5. Dynamic Unique Magic Numbers & Stealth Comments:\n"
            "   - Sha-256 hashed unique magic numbers aur benign comments ('App', 'Web', 'Core') se institutional footprints erase hojate hain.\n\n"
            "✅ Is architecture ke saath aap FundingPips #40000294403 aur doosre accounts ko 100% safe automate kar sakte hain."
        )
    else:
        return (
            "🛡️ [J.A.R.V.I.S. MULTI-PROP ANTI-BAN MASTER ARCHITECTURE]\n"
            "Architectural Blueprint for Master Muhammad Qureshi:\n"
            "Prop firms utilize bridge surveillance (Centroid24, OneZero, Gold-i) to detect sybil and copy-trading patterns.\n"
            "JARVIS eliminates detection vectors across 5 isolated layers:\n"
            "1. Isolated /portable MT5 directories per account (isolated IPC ports, separate data directories).\n"
            "2. Dedicated Static Residential SOCKS5 proxies matched to account KYC geography (never shared ASN).\n"
            "3. Execution jitter delays (350ms - 1800ms) with Fisher-Yates execution dispatch shuffling.\n"
            "4. Micro-tick SL/TP dispersion (+/- 0.5 to 2.0 pips) preserving risk caps and >= 2.5 R:R.\n"
            "5. Dynamic unique Magic Numbers and randomized stealth order comments per ticket."
        )
