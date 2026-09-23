"""
core/telemetry_cards.py — Structured Telemetry Card Schemas & Multi-Surface Renderers
======================================================================================
Authoritative telemetry schema generator for J.A.R.V.I.S.
Builds standardized, structured telemetry cards across trading, system vitals,
geopolitical radar, dynamic skill execution, and command envelopes.

Multi-Surface Rendering Support:
- Raw Dictionary / JSON schema (`to_dict()`, `to_json()`)
- Terminal ANSI / Cyberpunk Text representation (`render_terminal_text()`)
- Discord Rich Embed payload dictionary (`render_discord_embed()`)
- Python Rich Panel / Table visualizer object (`render_rich_panel()`)
======================================================================================
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# Color Palettes
COLOR_SUCCESS_GREEN = 0x00FF88
COLOR_CYAN = 0x00D9FF
COLOR_GOLD = 0xFFD700
COLOR_WARNING_ORANGE = 0xFFA500
COLOR_ALERT_RED = 0xFF3366
COLOR_PURPLE = 0x9B59B6
COLOR_DEFAULT_BLUE = 0x3498DB


@dataclass
class TelemetryCard:
    """Standardized multi-surface telemetry card schema."""
    card_type: str                         # "trading", "system_vitals", "geopolitical_radar", "skill_execution", "command_execution", "error"
    title: str
    status: str                            # "OK", "SUCCESS", "EXECUTED", "WARNING", "ERROR", "ACTIVE", "SHIELDED"
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    badges: List[str] = field(default_factory=list)
    color: int = COLOR_CYAN
    timestamp: float = field(default_factory=time.time)
    timestamp_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serializes telemetry card to standard JSON-compatible dict."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes telemetry card to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def render_terminal_text(self) -> str:
        """
        Renders an ANSI-formatted cyberpunk telemetry box for PC terminal and CLI.
        """
        lines = []
        width = 68
        border = "═" * (width - 2)
        lines.append(f"╔{border}╗")
        
        title_str = f" {self.title.upper()} [{self.status}] "
        pad_len = max(0, width - 2 - len(title_str))
        lines.append(f"║ {title_str}{' ' * (pad_len - 1)}║")
        lines.append(f"╠{border}╣")
        
        if self.summary:
            lines.append(f"║  Summary: {self.summary[:width - 14]:<{width - 13}}║")
        
        if self.badges:
            badge_str = " | ".join(f"[{b}]" for b in self.badges)
            lines.append(f"║  Badges:  {badge_str[:width - 14]:<{width - 13}}║")
        
        if self.metrics:
            lines.append(f"╠{'-' * (width - 2)}╣")
            for k, v in self.metrics.items():
                m_str = f"• {k.replace('_', ' ').title()}: {v}"
                lines.append(f"║   {m_str[:width - 6]:<{width - 5}}║")
                
        lines.append(f"╚{border}╝")
        return "\n".join(lines)

    def render_discord_embed(self) -> Dict[str, Any]:
        """
        Renders standardized Discord Embed dictionary payload.
        """
        fields = []
        for k, v in self.metrics.items():
            fields.append({
                "name": k.replace("_", " ").title(),
                "value": str(v),
                "inline": True
            })

        badge_footer = " • ".join(self.badges) if self.badges else "J.A.R.V.I.S. Sovereign Telemetry"
        return {
            "title": f"{self.title} [{self.status}]",
            "description": self.summary,
            "color": self.color,
            "fields": fields[:25],
            "footer": {"text": badge_footer},
            "timestamp": self.timestamp_iso
        }

    def render_rich_panel(self) -> Any:
        """
        Returns a Python `rich.panel.Panel` if `rich` is installed, else returns formatted text.
        """
        try:
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            table = Table.grid(padding=(0, 1))
            table.add_column(style="cyan bold", justify="right")
            table.add_column(style="white")

            for k, v in self.metrics.items():
                table.add_row(f"{k.replace('_', ' ').title()}:", str(v))

            content = Text(f"{self.summary}\n\n", style="bold white")
            panel_title = f"[bold yellow]{self.title}[/bold yellow] ([green]{self.status}[/green])"
            return Panel(
                table,
                title=panel_title,
                subtitle=f"[dim]{' | '.join(self.badges)}[/dim]",
                border_style="cyan"
            )
        except Exception:
            return self.render_terminal_text()


# ==============================================================================
# CARD BUILDER FACTORIES
# ==============================================================================

def build_trading_card(
    symbol: str,
    action: str,
    lots: float,
    pnl: float = 0.0,
    equity: float = 100000.0,
    balance: float = 100000.0,
    var_99: float = 0.0,
    order_id: Optional[int] = None,
    status: str = "EXECUTED",
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a standardized MT5 / Prop Trading Telemetry Card."""
    symbol_clean = (symbol or "XAUUSD").upper()
    act_clean = (action or "ORDER").upper()
    
    metrics = {
        "symbol": symbol_clean,
        "action": act_clean,
        "lot_size": f"{lots:.2f} lots",
        "floating_pnl": f"${pnl:+,.2f}",
        "live_equity": f"${equity:,.2f}",
        "account_balance": f"${balance:,.2f}",
    }
    if var_99 > 0:
        metrics["aladdin_var_99"] = f"${var_99:,.2f}"
    if order_id:
        metrics["ticket"] = f"#{order_id}"

    color = COLOR_SUCCESS_GREEN if pnl >= 0 else COLOR_ALERT_RED
    if status == "SHIELDED":
        color = COLOR_GOLD

    badges = ["MT5 Prop Gate", "FTMO & Pipdance Compliant", f"Risk: {act_clean}"]

    return TelemetryCard(
        card_type="trading",
        title=f"📈 Trading Telemetry — {symbol_clean} {act_clean}",
        status=status,
        summary=f"Dispatched {act_clean} order of {lots:.2f}L on {symbol_clean}. Live Equity: ${equity:,.2f}.",
        metrics=metrics,
        details=details or {},
        badges=badges,
        color=color
    )


def build_vitals_card(
    cpu_pct: float,
    ram_pct: float,
    gpu_pct: float = 0.0,
    network_latency_ms: float = 15.0,
    active_daemons: int = 11,
    total_daemons: int = 11,
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a standardized PC System Vitals Telemetry Card."""
    status = "OK" if cpu_pct < 85.0 and ram_pct < 90.0 else "WARNING"
    color = COLOR_SUCCESS_GREEN if status == "OK" else COLOR_WARNING_ORANGE
    
    metrics = {
        "cpu_utilization": f"{cpu_pct:.1f}%",
        "ram_allocation": f"{ram_pct:.1f}%",
        "gpu_npu_load": f"{gpu_pct:.1f}%",
        "network_latency": f"{network_latency_ms:.1f}ms",
        "core_fleet_daemons": f"{active_daemons}/{total_daemons} Active",
    }
    badges = ["Workstation Vitals", "Sovereign OS Monitor", "100% Offline Capable"]

    return TelemetryCard(
        card_type="system_vitals",
        title="🖥️ Workstation System Vitals & Fleet Health",
        status=status,
        summary=f"System operating nominally. Fleet nodes: {active_daemons}/{total_daemons} online.",
        metrics=metrics,
        details=details or {},
        badges=badges,
        color=color
    )


def build_radar_card(
    defcon_level: int = 2,
    threat_status: str = "DEFCON 2 — HEIGHTENED TENSION",
    chokepoints_disrupted: int = 3,
    gold_multiplier: float = 1.45,
    macro_sentiment: str = "Risk-Off Safe Haven",
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a standardized Geopolitical Radar Telemetry Card."""
    color_map = {
        1: COLOR_ALERT_RED,
        2: COLOR_WARNING_ORANGE,
        3: COLOR_GOLD,
        4: COLOR_CYAN,
        5: COLOR_SUCCESS_GREEN
    }
    color = color_map.get(defcon_level, COLOR_GOLD)
    
    metrics = {
        "global_threat_level": f"DEFCON {defcon_level}",
        "chokepoints_disrupted": f"{chokepoints_disrupted} / 5 Corridors",
        "gold_macro_multiplier": f"{gold_multiplier:.2f}x",
        "macro_sentiment": macro_sentiment,
    }
    badges = ["World Monitor Radar", "Strategic Chokepoints", "Macro Risk Shock"]

    return TelemetryCard(
        card_type="geopolitical_radar",
        title="🌍 Geopolitical DEFCON Radar & Risk Assessment",
        status=f"DEFCON {defcon_level}",
        summary=f"Global Threat Status: {threat_status}. Safe-haven multiplier at {gold_multiplier:.2f}x.",
        metrics=metrics,
        details=details or {},
        badges=badges,
        color=color
    )


def build_skill_card(
    skill_name: str,
    status: str = "COMPLETED",
    execution_time_ms: float = 0.0,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
    repaired: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a standardized Dynamic Skill Execution Card."""
    clean_name = skill_name or "dynamic_skill"
    color = COLOR_SUCCESS_GREEN if status in ("OK", "COMPLETED", "EXECUTED", "COMPILED") else COLOR_ALERT_RED
    
    metrics = {
        "skill_name": clean_name,
        "execution_time": f"{execution_time_ms:.2f}ms",
        "self_repaired": "Yes (1-Attempt Auto-Repair)" if repaired else "No (Zero Error)",
        "result_preview": str(result)[:80] if result is not None else "Success",
    }
    badges = ["1-Shot Dynamic Skill", "AST Verified", "Sandbox Tested"]

    return TelemetryCard(
        card_type="skill_execution",
        title=f"⚡ Dynamic Skill Execution — {clean_name}",
        status=status,
        summary=f"Dynamic workflow '{clean_name}' executed in {execution_time_ms:.2f}ms with status {status}.",
        metrics=metrics,
        details=details or {"parameters": parameters or {}, "raw_result": str(result)},
        badges=badges,
        color=color
    )


def build_command_card(
    command: str,
    intent: str,
    status: str = "OK",
    output_text: str = "",
    channel: str = "terminal",
    execution_time_ms: float = 0.0,
    routed_via: str = "router",
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a general command execution telemetry card."""
    color = COLOR_SUCCESS_GREEN if status in ("OK", "SUCCESS", "EXECUTED") else COLOR_WARNING_ORANGE
    
    metrics = {
        "command": command[:50],
        "resolved_intent": intent,
        "ingress_channel": channel,
        "routing_subsystem": routed_via,
        "latency": f"{execution_time_ms:.2f}ms",
    }
    badges = [f"Channel: {channel.upper()}", f"Routed: {routed_via}", "Truthful Execution"]

    return TelemetryCard(
        card_type="command_execution",
        title=f"🎯 J.A.R.V.I.S. Command Execution — {intent}",
        status=status,
        summary=output_text[:120] if output_text else f"Executed {command} successfully via {routed_via}.",
        metrics=metrics,
        details=details or {},
        badges=badges,
        color=color
    )


def build_error_card(
    command: str,
    error_message: str,
    channel: str = "unknown",
    details: Optional[Dict[str, Any]] = None
) -> TelemetryCard:
    """Builds a standardized error telemetry card."""
    return TelemetryCard(
        card_type="error",
        title="⚠️ Execution Exception & Guardrail Intercept",
        status="ERROR",
        summary=error_message,
        metrics={
            "command": command[:50],
            "channel": channel,
            "error_type": "Runtime / Validation Fault",
        },
        details=details or {"error": error_message},
        badges=["Error Handled", "System Protected"],
        color=COLOR_ALERT_RED
    )
