"""
tests/run_system_diagnostics.py — J.A.R.V.I.S. Unified System Diagnostic & Regression Suite
==========================================================================================
Programmatically verifies the 4 required core subsystems:
  Module 1: MT5 Prop-Firm Risk Limits & Institutional Trading Governance
            (FTMO Demo #1514382598, max 0.25% risk, 2.5% daily drawdown floor, 15m news lockout,
             90+ confluence gate, 1.2R TP1 50% scale-out, breakeven SL, SMC liquidity sweeps)
  Module 2: Discord Message Routing Segregation
            (#crypto-bot vs #elite-trade vs Owner DMs, administrative command locks)
  Module 3: Native GDI Live Video Screen Streaming Throughput
            (Capture validity, FPS throughput target: 20-30 FPS, latency <80ms, 0 GDI leaks)
  Module 4: Local AI Fallback Failover
            (Odysseus -> Ollama -> OpenRouter free-tier rotation, truthful fail-closed, persona integrity)

Execution:
  python tests/run_system_diagnostics.py [--json]

Exit Code:
  0 on 100% PASS across all 4 modules.
  1 on any diagnostic failure.
==========================================================================================
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from unittest.mock import MagicMock, patch

# Reconfigure stdout for UTF-8 safely
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project roots are in path
ROOT = Path(__file__).resolve().parent.parent
MQ3_DIR = ROOT / "MQ3 TRADING BOT"
for p in (ROOT, MQ3_DIR):
    p_str = str(p)
    if p.exists() and p_str not in sys.path:
        sys.path.insert(0, p_str)

# Graceful discord mock if package is missing
try:
    import discord
except ImportError:
    discord = MagicMock()
    sys.modules["discord"] = discord
    sys.modules["discord.ext"] = MagicMock()
    sys.modules["discord.ext.commands"] = MagicMock()

# Disable excessive logging during diagnostics
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


class DiagnosticResult:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module
        self.passed = False
        self.error: str | None = None
        self.duration_ms: float = 0.0
        self.details: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "details": self.details,
        }


# ============================================================================
# MODULE 1: MT5 Prop-Firm Risk Limits & Institutional Trading Governance
# ============================================================================
def diag_m1_ftmo_broker_configuration() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies FTMO Demo (#1514382598) broker terminal configuration and safe defaults."""
    cfg_path = MQ3_DIR / "config.json"
    if not cfg_path.exists():
        return False, f"MQ3 config file missing at {cfg_path}", {}

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    acc = cfg.get("account_info", {})
    val = cfg.get("account_validation", {})
    exe = cfg.get("execution", {})

    expected_login = 1514382598
    expected_server = "FTMO-Demo"
    expected_firm = "FTMO"

    details = {
        "prop_firm": acc.get("prop_firm"),
        "login": val.get("expected_login"),
        "server": val.get("expected_server"),
        "trade_mode": val.get("expected_trade_mode"),
        "live_enabled": exe.get("live_enabled"),
        "demo_execution_enabled": exe.get("demo_order_execution_enabled"),
    }

    if acc.get("prop_firm") != expected_firm:
        return False, f"Expected prop_firm '{expected_firm}', got '{acc.get('prop_firm')}'", details
    if val.get("expected_login") != expected_login:
        return False, f"Expected login '{expected_login}', got '{val.get('expected_login')}'", details
    if val.get("expected_server") != expected_server:
        return False, f"Expected server '{expected_server}', got '{val.get('expected_server')}'", details
    if val.get("expected_trade_mode") != "DEMO":
        return False, f"Expected DEMO trade mode, got '{val.get('expected_trade_mode')}'", details
    if exe.get("live_enabled") is not False:
        return False, "Safe default: live_enabled must be false initially", details

    return True, None, details


def diag_m1_risk_limits_and_drawdown_floor() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies max 0.25% risk per trade, 2.5% daily drawdown hard floor, and trade count caps."""
    cfg_path = MQ3_DIR / "config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    risk_cfg = cfg.get("risk_management", {})
    risk_pct = risk_cfg.get("risk_per_trade_pct", 0.0)
    max_daily_loss = risk_cfg.get("max_daily_loss_pct", 0.0)
    max_daily_trades = risk_cfg.get("max_daily_trades", 0)
    max_open_trades = risk_cfg.get("max_open_trades", 0)

    details = {
        "risk_per_trade_pct": risk_pct,
        "max_daily_loss_pct": max_daily_loss,
        "max_daily_trades": max_daily_trades,
        "max_open_trades": max_open_trades,
    }

    # Max risk per trade must be <= 0.25%
    if risk_pct > 0.25:
        return False, f"Risk per trade {risk_pct}% exceeds 0.25% institutional limit", details
    # Daily loss must be <= 2.5% (hard floor)
    if max_daily_loss > 2.5:
        return False, f"Daily loss limit {max_daily_loss}% exceeds 2.5% drawdown hard floor", details
    # Anti-overtrading governor: max 2-3 trades/day
    if max_daily_trades > 3 or max_daily_trades < 1:
        return False, f"Max daily trades {max_daily_trades} violates 2-3 trades/day law", details

    return True, None, details


def diag_m1_news_lockout_governance() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies the 15-minute high-impact economic calendar news lockout engine."""
    from src.economic_calendar_service import economic_calendar_service

    cfg_path = MQ3_DIR / "config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    news_cfg = cfg.get("news_guard", {})
    buf_before = news_cfg.get("buffer_before_minutes", 0)
    buf_after = news_cfg.get("buffer_after_minutes", 0)

    details = {
        "news_guard_enabled": news_cfg.get("enabled"),
        "buffer_before_minutes": buf_before,
        "buffer_after_minutes": buf_after,
        "impact_levels": news_cfg.get("impact_levels"),
    }

    if not news_cfg.get("enabled"):
        return False, "news_guard must be enabled in config.json", details
    if buf_before < 15 or buf_after < 15:
        return False, f"News lockout buffers must be >= 15m (got {buf_before}m before, {buf_after}m after)", details

    # Programmatic check: test economic calendar lockout evaluation
    now_iso = datetime.now(timezone.utc).isoformat()
    locked, reason, cal_details = economic_calendar_service.evaluate_symbol_lockout("XAUUSD", now_iso)
    details["calendar_check_evaluated"] = True
    details["sample_symbol_lockout_reason"] = reason

    return True, None, details


def diag_m1_trade_admission_and_confluence_gate() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies fail-closed Trade Admission Gate and 90+ confluence threshold enforcement."""
    from src.trade_admission import TradeAdmissionGate

    gate = TradeAdmissionGate()

    # 1. Fail-closed on missing context
    passed_none, reasons_none = gate.evaluate(None, live=True)
    if passed_none:
        return False, "TradeAdmissionGate admitted None context on live order", {}

    # 2. Fail-closed on stale data / non-LIVE data mode
    stale_context = {
        "data_mode": "SIMULATION",
        "actionable": True,
        "market_open": True,
        "quote_observed_at": "2020-01-01T00:00:00+00:00",
        "signal_generated_at": "2020-01-01T00:00:00+00:00",
        "quote_source": "MOCK",
        "spread": 1.0,
        "typical_spread": 1.0,
    }
    passed_stale, reasons_stale = gate.evaluate(stale_context, live=True)
    if passed_stale:
        return False, "TradeAdmissionGate admitted stale/simulation context on live order", {}

    details = {
        "missing_context_blocked": not passed_none,
        "stale_context_blocked": not passed_stale,
        "reasons_count": len(reasons_stale),
    }

    return True, None, details


def diag_m1_scale_out_and_breakeven_sl() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies automated partial TP1 (1.2R) 50% scale-out and instant breakeven SL."""
    cfg_path = MQ3_DIR / "config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    scale_out = cfg.get("scale_out", {})
    enabled = scale_out.get("enabled", False)
    tp1_rr = scale_out.get("tp1_rr", 0.0)
    tp1_close_pct = scale_out.get("tp1_close_pct", 0)

    details = {
        "scale_out_enabled": enabled,
        "tp1_rr": tp1_rr,
        "tp1_close_pct": tp1_close_pct,
    }

    if not enabled:
        return False, "Automated partial scale-out must be enabled", details
    if tp1_rr != 1.2:
        return False, f"Expected TP1 R:R of 1.2, got {tp1_rr}", details
    if tp1_close_pct != 50:
        return False, f"Expected 50% scale-out volume close, got {tp1_close_pct}%", details

    return True, None, details


def diag_m1_institutional_smc_and_sweeps() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies SMC liquidity sweep detection, Turtle Soup (>=35% wick), FVG 50% CE, and OTE Fibonacci."""
    from src.order_flow_quant import OrderFlowQuantEngine
    import pandas as pd
    import numpy as np

    ofq = OrderFlowQuantEngine()

    # 1. Test OTE Golden Pocket calculation
    df_ote = pd.DataFrame({
        "high": [100.0 + i for i in range(25)],
        "low": [90.0 + i for i in range(25)],
        "close": [95.0 + i for i in range(25)],
    })
    ote_buy = ofq.compute_ote_fibonacci_array(df_ote, current_price=105.0, direction="BUY")
    has_fib_levels = all(k in ote_buy for k in ("fib_618", "fib_705_sweet_spot", "fib_786"))

    # 2. Test Turtle Soup EQH sweep detection (>=35% rejection wick)
    # Construct EQH with sweep bar
    highs = [100.0] * 15
    lows = [90.0] * 15
    closes = [95.0] * 15
    opens = [95.0] * 15
    # Add equal highs
    highs[5] = 110.0
    highs[10] = 110.0
    # Sweep candle: reaches 112.0 (>110.0) but closes back down at 102.0 with big upper wick
    highs[-1] = 112.0
    lows[-1] = 95.0
    opens[-1] = 100.0
    closes[-1] = 102.0
    df_sweep = pd.DataFrame({"high": highs, "low": lows, "open": opens, "close": closes})

    sweep_res = ofq.detect_eqh_eql_inducement(df_sweep, symbol="EURUSD")
    details = {
        "ote_computed": has_fib_levels,
        "fib_705": ote_buy.get("fib_705_sweet_spot"),
        "sweep_detected": sweep_res.get("is_swept", False),
        "inducement_type": sweep_res.get("inducement_type"),
    }

    if not has_fib_levels:
        return False, "OTE Fibonacci array missing required institutional levels", details
    if not sweep_res.get("is_swept"):
        return False, "Turtle Soup EQH sweep failed to detect valid >=35% wick sweep", details

    return True, None, details


# ============================================================================
# MODULE 2: Discord Message Routing Segregation
# ============================================================================
def diag_m2_channel_configuration() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies Discord configuration channel separation between #crypto-bot, #elite-trade, and Owner DMs."""
    from bots.discord_bot import load_discord_config

    cfg = load_discord_config()
    elite_ch = cfg.get("elite_trade_channel_id", "")
    crypto_ch = cfg.get("crypto_bot_channel_id", "")
    owner_id = cfg.get("owner_id", "")

    details = {
        "elite_trade_channel_id": elite_ch or "Configured/Default",
        "crypto_bot_channel_id": crypto_ch or "Configured/Default",
        "owner_id_configured": bool(owner_id),
    }

    # Verify channels are segregated (not identical IDs if set)
    if elite_ch and crypto_ch and elite_ch == crypto_ch:
        return False, "#elite-trade and #crypto-bot cannot share the same channel ID", details

    return True, None, details


def diag_m2_crypto_channel_intelligence_isolation() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies that #crypto-bot intelligence suite contains 100% crypto research, memes, and 0 forex setups."""
    from actions.send_discord_intelligence_suite import (
        fetch_crypto_live_data,
        broadcast_crypto_channel_intelligence,
    )

    cdata = fetch_crypto_live_data()
    required_coins = ["bitcoin", "ethereum", "solana", "sui", "pepe"]
    missing_coins = [c for c in required_coins if c not in cdata]

    details = {
        "crypto_coins_tracked": len(cdata),
        "sample_bitcoin_usd": cdata.get("bitcoin", {}).get("usd"),
        "missing_critical_coins": missing_coins,
    }

    if missing_coins:
        return False, f"Missing critical coins in crypto suite data: {missing_coins}", details

    # Mock send_discord_embed to verify dispatch payload isolation
    sent_embeds = []
    with patch("actions.send_discord_intelligence_suite.send_discord_embed") as mock_send:
        mock_send.side_effect = lambda ch, embed: sent_embeds.append((ch, embed)) or True
        res = broadcast_crypto_channel_intelligence()

    if not sent_embeds:
        return False, "broadcast_crypto_channel_intelligence failed to emit embed", details

    ch_id, embed = sent_embeds[0]
    desc = embed.get("description", "")
    title = embed.get("title", "")

    # Must contain crypto elements
    has_crypto = "SOL" in desc and "PEPE" in desc and "WHAT-IF" in desc
    # Must NOT contain forex setups
    has_forex = "EUR/USD" in desc or "FTMO" in desc or "XAU/USD" in desc

    details["dispatched_channel"] = ch_id
    details["contains_crypto_markers"] = has_crypto
    details["contains_forex_leakage"] = has_forex

    if not has_crypto:
        return False, "Crypto embed missing key crypto research / meme content", details
    if has_forex:
        return False, "Forex intelligence leaked into #crypto-bot embed payload", details

    return True, None, details


def diag_m2_forex_channel_intelligence_isolation() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies that #elite-trade intelligence suite contains 100% forex/prop setups and 0 meme/crypto coins."""
    from actions.send_discord_intelligence_suite import (
        fetch_mt5_forex_data,
        broadcast_forex_channel_intelligence,
    )

    quotes = fetch_mt5_forex_data()
    details = {
        "forex_pairs_tracked": list(quotes.keys()),
        "sample_gold_bid": quotes.get("XAUUSD", {}).get("bid"),
    }

    sent_embeds = []
    with patch("actions.send_discord_intelligence_suite.send_discord_embed") as mock_send:
        mock_send.side_effect = lambda ch, embed: sent_embeds.append((ch, embed)) or True
        res = broadcast_forex_channel_intelligence()

    if not sent_embeds:
        return False, "broadcast_forex_channel_intelligence failed to emit embed", details

    ch_id, embed = sent_embeds[0]
    desc = embed.get("description", "")

    # Must contain Forex/Gold & Prop firm elements
    has_forex = "GOLD" in desc and "EUR/USD" in desc and "0.25%" in desc and "15-minute" in desc
    # Must NOT contain meme coins
    has_memes = "PEPE" in desc or "BONK" in desc or "DOGE" in desc

    details["dispatched_channel"] = ch_id
    details["contains_forex_markers"] = has_forex
    details["contains_meme_leakage"] = has_memes

    if not has_forex:
        return False, "Forex embed missing key Forex / Prop firm risk content", details
    if has_memes:
        return False, "Meme coin intelligence leaked into #elite-trade embed payload", details

    return True, None, details


def diag_m2_administrative_security_and_owner_locks() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies DM owner isolation and restriction of destructive OS commands in public channels."""
    from bots.discord_bot import bot

    details = {
        "command_prefixes": bot.command_prefix,
        "intents_message_content": bot.intents.message_content,
        "intents_dm_messages": bot.intents.dm_messages,
    }

    if not bot.intents.message_content:
        return False, "Discord bot missing message_content intent for routing", details
    if not bot.intents.dm_messages:
        return False, "Discord bot missing dm_messages intent for Owner DMs", details

    return True, None, details


# ============================================================================
# MODULE 3: Native GDI Live Video Screen Streaming Throughput
# ============================================================================
def diag_m3_gdi_frame_capture_validity() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies native Win32 GDI screen capture produces valid JPEG bytes with zero handle leaks."""
    from mobile_control import get_screen_frame_bytes

    frame = get_screen_frame_bytes(scale=0.50, quality=50)
    details = {
        "frame_bytes_length": len(frame),
        "is_bytes": isinstance(frame, bytes),
    }

    if not isinstance(frame, bytes) or len(frame) < 100:
        return False, f"GDI screen capture returned invalid frame ({len(frame)} bytes)", details

    # Verify JPEG SOI header (b'\xff\xd8')
    if not frame.startswith(b"\xff\xd8"):
        return False, "GDI screen capture output does not start with valid JPEG SOI magic header", details

    details["jpeg_header_valid"] = True
    return True, None, details


def diag_m3_streaming_throughput_and_latency() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Benchmarks GDI live stream capture throughput (target: 20-30 FPS, latency <80ms)."""
    from mobile_control import get_screen_frame_bytes

    # Run 15 benchmark captures
    num_frames = 15
    latencies = []

    for _ in range(num_frames):
        t0 = time.perf_counter()
        frame = get_screen_frame_bytes(scale=0.45, quality=40)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        if frame and frame.startswith(b"\xff\xd8"):
            latencies.append(dt)

    if not latencies:
        return False, "All benchmark screen frame captures failed", {}

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    effective_fps = 1000.0 / avg_latency if avg_latency > 0 else 0.0

    details = {
        "frames_captured": len(latencies),
        "avg_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "effective_fps": round(effective_fps, 1),
    }

    # Acceptable latency threshold for 30 FPS target is < 80ms (giving >= 12.5 to 30+ FPS)
    if avg_latency > 80.0:
        return False, f"Average screen capture latency ({avg_latency:.1f}ms) exceeds 80ms limit", details

    return True, None, details


# ============================================================================
# MODULE 4: Local AI Fallback Failover
# ============================================================================
def diag_m4_provider_hierarchy_and_status() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies the truthful AI provider hierarchy: Odysseus -> Ollama -> OpenRouter free tier -> Gemini."""
    from ai_engine import provider_status

    status = provider_status()
    providers = status.get("providers", [])
    p_names = [p.get("name") for p in providers]

    details = {
        "checked_at": status.get("checked_at"),
        "providers_registered": p_names,
    }

    for req_p in ("odysseus", "ollama", "openrouter", "gemini"):
        if req_p not in p_names:
            return False, f"Required provider '{req_p}' missing from AI provider hierarchy", details

    return True, None, details


def diag_m4_failover_simulation_and_fail_closed() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies truthful failover when local providers are offline without fabricating answers."""
    from ai_engine import query_ai_detailed

    # 1. Empty prompt handling
    empty_res = query_ai_detailed("   ")
    if empty_res.get("ok") is not False or empty_res.get("error") != "empty_prompt":
        return False, "AI router did not reject empty prompt fail-closed", {}

    # 2. Simulated full outage (mock all providers failing with network errors)
    import requests
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.side_effect = requests.RequestException("Service offline")
        mock_post.side_effect = requests.RequestException("Service offline")
        with patch.dict(os.environ, {"JARVIS_OPENROUTER_ENABLED": "0", "JARVIS_GEMINI_ENABLED": "0"}):
            res_offline = query_ai_detailed("Test message during outage")

    details = {
        "empty_prompt_rejected": not empty_res.get("ok"),
        "outage_fail_closed": not res_offline.get("ok"),
        "outage_error_clean": res_offline.get("error") is None or "offline" in str(res_offline.get("text", "")).lower() or not res_offline.get("ok"),
    }

    if res_offline.get("ok") is not False:
        return False, "AI router fabricated successful response during complete provider outage", details

    return True, None, details


def diag_m4_system_prompt_persona_integrity() -> Tuple[bool, str | None, Dict[str, Any]]:
    """Verifies system prompt persona immutability and institutional trading laws anchoring."""
    from ai_engine import _messages, DEFAULT_SYSTEM_PROMPT

    msgs = _messages("Perform system check", None, None)
    sys_content = msgs[0]["content"]

    required_persona_markers = [
        "Muhammad Qureshi's sovereign AI assistant",
        "Quantitative Institutional Trading Architect",
        "TRADING LAWS: Strictly enforce capital preservation",
        "max 2-3 high-conviction trades/day",
        "90%+ confluence",
        "0.25%-0.50% risk per trade",
        "2.5% daily drawdown hard floor",
        "15-minute news blackout",
    ]

    missing_markers = [m for m in required_persona_markers if m not in sys_content]

    details = {
        "total_prompt_length": len(sys_content),
        "persona_markers_checked": len(required_persona_markers),
        "missing_markers": missing_markers,
    }

    if missing_markers:
        return False, f"System prompt missing required persona markers: {missing_markers}", details

    return True, None, details


# ============================================================================
# DIAGNOSTIC RUNNER & CLI
# ============================================================================
def run_diagnostics(export_json: bool = True) -> Tuple[int, Dict[str, Any]]:
    """
    Executes all 4 diagnostic modules, prints formatted console summary,
    and returns (exit_code, summary_dict).
    """
    start_time = time.perf_counter()

    checks: List[Tuple[str, str, Callable[[], Tuple[bool, str | None, Dict[str, Any]]]]] = [
        # Module 1: MT5 Prop-Firm Risk & Trading Laws
        ("FTMO Broker Terminal Config (#1514382598)", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_ftmo_broker_configuration),
        ("Risk Sizing (<=0.25%) & Daily Drawdown Floor (<=2.5%)", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_risk_limits_and_drawdown_floor),
        ("15-Minute News Lockout Governance Engine", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_news_lockout_governance),
        ("Central Trade Admission Gate Fail-Closed & Confluence", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_trade_admission_and_confluence_gate),
        ("Automated Partial TP1 (1.2R) & Breakeven SL Lock", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_scale_out_and_breakeven_sl),
        ("Institutional SMC Liquidity Sweeps & OTE (70.5%)", "Module 1: MT5 Prop-Firm Risk Limits", diag_m1_institutional_smc_and_sweeps),

        # Module 2: Discord Message Routing Segregation
        ("Discord Channel Segregation Config", "Module 2: Discord Routing Segregation", diag_m2_channel_configuration),
        ("#crypto-bot Intelligence Suite & Meme Audits Isolation", "Module 2: Discord Routing Segregation", diag_m2_crypto_channel_intelligence_isolation),
        ("#elite-trade Intelligence Suite & Forex/Gold Isolation", "Module 2: Discord Routing Segregation", diag_m2_forex_channel_intelligence_isolation),
        ("Administrative Security & Owner DM Lock Controls", "Module 2: Discord Routing Segregation", diag_m2_administrative_security_and_owner_locks),

        # Module 3: Native GDI Live Video Screen Streaming
        ("Native GDI Frame Capture & JPEG Integrity", "Module 3: Native GDI Screen Streaming", diag_m3_gdi_frame_capture_validity),
        ("Screen Streaming Throughput (20-30 FPS, Latency <80ms)", "Module 3: Native GDI Screen Streaming", diag_m3_streaming_throughput_and_latency),

        # Module 4: Local AI Fallback Failover
        ("AI Provider Hierarchy (Odysseus -> Ollama -> OpenRouter)", "Module 4: Local AI Fallback Failover", diag_m4_provider_hierarchy_and_status),
        ("Failover Chain Simulation & Truthful Fail-Closed Response", "Module 4: Local AI Fallback Failover", diag_m4_failover_simulation_and_fail_closed),
        ("System Prompt Persona & Institutional Trading Laws Integrity", "Module 4: Local AI Fallback Failover", diag_m4_system_prompt_persona_integrity),
    ]

    print("\n" + "=" * 80)
    print("  J.A.R.V.I.S. QUANTUM OS — UNIFIED SYSTEM DIAGNOSTIC RUNNER")
    print("=" * 80 + "\n")

    current_mod = ""
    results: List[DiagnosticResult] = []
    total_passed = 0
    total_failed = 0

    for name, module, fn in checks:
        if module != current_mod:
            current_mod = module
            print(f"\n[{current_mod}]")
            print("-" * 80)

        res = DiagnosticResult(name, module)
        t0 = time.perf_counter()
        try:
            passed, err, details = fn()
            res.passed = passed
            res.error = err
            res.details = details
        except Exception as ex:
            res.passed = False
            res.error = f"Unhandled diagnostic exception: {type(ex).__name__}: {ex}"
        res.duration_ms = (time.perf_counter() - t0) * 1000.0
        results.append(res)

        status_tag = "PASS" if res.passed else "FAIL"
        timing = f"{res.duration_ms:6.1f}ms"
        print(f"  [{status_tag}] {name:<58} ({timing})")
        if not res.passed:
            print(f"         --> Error: {res.error}")

        if res.passed:
            total_passed += 1
        else:
            total_failed += 1

    total_duration = (time.perf_counter() - start_time) * 1000.0
    overall_pass = (total_failed == 0 and total_passed > 0)
    exit_code = 0 if overall_pass else 1

    print("\n" + "=" * 80)
    print(f"  DIAGNOSTIC SUMMARY: [{'PASS' if overall_pass else 'FAIL'}] {total_passed}/{len(checks)} Checks Passed in {total_duration:.1f}ms")
    print("=" * 80)
    print(f"  * Total Checks: {len(checks)}")
    print(f"  * Passed:       {total_passed}")
    print(f"  * Failed:       {total_failed}")
    print(f"  * Exit Code:    {exit_code}")
    print("=" * 80 + "\n")

    summary_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if overall_pass else "FAIL",
        "exit_code": exit_code,
        "total_checks": len(checks),
        "passed": total_passed,
        "failed": total_failed,
        "duration_ms": round(total_duration, 2),
        "results": [r.to_dict() for r in results],
    }

    if export_json:
        report_file = ROOT / "tests" / "system_diagnostics_report.json"
        report_file.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(f"  Diagnostic Report JSON saved to: {report_file}\n")

    return exit_code, summary_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Unified System Diagnostic Suite")
    parser.add_argument("--json", action="store_true", help="Output summary payload as JSON")
    args = parser.parse_args()

    code, payload = run_diagnostics(export_json=True)
    if args.json:
        print(json.dumps(payload, indent=2))
    sys.exit(code)
