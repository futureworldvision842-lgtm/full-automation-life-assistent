"""
core/roman_urdu_parser.py — High-Speed Bilingual NLP Engine (English & Roman Urdu)
==================================================================================
Authoritative bilingual natural language processing module for J.A.R.V.I.S.
Parses natural language commands in English and Roman Urdu into structured execution
intents, extracting domain entities, parameters, and translations.

Capabilities:
1. High-speed Language Detection ('en' vs 'ur') with phoneme & marker vocabulary.
2. Phonetic normalizer harmonizing Roman Urdu spelling variations and suffixes.
3. Accurate intent classification covering:
   - MT5 Forex & Prop Trading ("bhai gold ka status batao", "trade close kardo", "buy 0.01 lot xauusd")
   - OS Sovereign Computer Control ("workstation lock kardo", "volume barhao", "chrome kholo")
   - 1-Shot Dynamic Skill Teaching ("jab bhi main kahoon X to Y karo", "whenever I say X then Y")
   - Zero-Guidance Skill Execution ("run backup skill", "calculate risk")
   - Autonomous Browser & Desktop Vision ("search web for X", "screen dekho", "chatgpt se poocho")
   - Geopolitical / DEFCON Radar & Aladdin Risk
   - Crypto & On-Chain Meme Audits
   - General Truthful AI Queries
==================================================================================
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# VOCABULARY & PHONETIC DICTIONARIES
# ==============================================================================

ROMAN_URDU_MARKERS = {
    # Pronouns & Connectors
    "main", "hum", "tum", "aap", "mera", "meri", "mere", "apna", "apni", "apne",
    "ka", "ki", "ke", "ko", "se", "mein", "par", "pe", "tak", "aur", "ya",
    "kya", "kyun", "kyu", "kab", "kahan", "kaise", "konsa", "kaunsi", "kitna", "kitni", "kitne",
    "hai", "hain", "tha", "thay", "thi", "hoga", "hogi", "honge", "karo", "kardo", "kar do",
    "karna", "kariye", "kar", "karen", "kardena", "karke", "kijiye", "karlo", "kar lo",
    
    # Demonstratives & Directions
    "ye", "yeh", "wo", "woh", "is", "us", "in", "un", "inka", "unka", "iske", "uske",
    "idhar", "udhar", "upar", "neeche", "aage", "peeche", "andar", "bahar", "yahan", "wahan",
    
    # Temporal & Quantifiers
    "aaj", "kal", "parson", "abhi", "fauran", "jaldi", "hamesha", "kabhi", "pehle", "baad",
    "sirf", "sab", "sara", "sari", "sare", "kuch", "thora", "thori", "thore", "bohot", "bahut",
    
    # Affirmations, Negations & Conditionals
    "nahi", "nahin", "mat", "na", "haan", "jee", "ji", "theek", "bilkul", "sahi",
    "agar", "magar", "lekin", "kyunke", "kyunki", "warna", "chunke",
    
    # Common Salutations & Honorifics
    "bhai", "bhae", "bhaiya", "bhaijan", "yar", "yaar", "janab", "sahib", "sahab",
    "boss", "ustad", "shukriya", "meherbani", "suno", "sunen", "dekho", "dekhein",
    
    # Action Verbs (Urdu)
    "chalao", "chalado", "chala do", "chalana", "chalayein", "chala",
    "kholo", "kholdo", "khol do", "kholna", "kholein", "khol",
    "band", "roko", "rok do", "rokna", "khatam", "hatao", "mitao", "chhoro",
    "barhao", "barha do", "badhao", "tez", "ziada", "zyada",
    "kam", "ghatao", "ahista", "dheema", "dheeme", "halka", "slow",
    "dikhao", "batao", "samjhao", "bataiye", "dikhayein",
    "banao", "bana do", "likho", "likh do", "parho", "parh do",
    "bhejo", "rakho", "le aao", "lao", "pakro", "dhoondo", "khojo",
    "khareedo", "becho", "rok do", "band karo", "shuru", "shuru karo",
    
    # Domain & Trading Terms
    "awaz", "awaaz", "tasveer", "tasweer", "tasver", "photo", "khabar", "halat",
    "sehat", "fayda", "munafa", "nuqsan", "hisab", "paisa", "rakam",
    "sona", "sone", "chandi", "keemat", "bhao", "daam", "safai",
    "jab", "tab", "toh", "jab bhi", "naya", "nayi", "nayee"
}

ENGLISH_COMMON_WORDS = {
    "the", "is", "are", "was", "were", "to", "and", "of", "for", "in", "at", "on",
    "with", "immediately", "show", "what", "how", "all", "please", "can", "you",
    "my", "your", "this", "that", "from", "by", "as", "an", "be", "have", "has",
    "workstation", "computer", "system", "command", "process", "status", "vitals",
    "search", "web", "browser", "look", "inspect", "diagnostics", "capture", "balance",
    "equity", "positions", "trades", "price", "analysis", "orders", "archive", "size"
}

ENGLISH_ACTION_VERBS = {
    "launch", "open", "start", "run", "execute", "trigger",
    "close", "kill", "terminate", "stop", "quit", "exit", "shutdown", "restart", "reboot", "lock",
    "switch", "focus", "bring", "inspect", "list", "show", "check", "status", "display",
    "volume", "mute", "unmute", "increase", "decrease", "raise", "lower", "boost",
    "capture", "screenshot", "snapshot", "diagnostics", "vitals", "monitor", "health",
    "search", "find", "create", "make", "compile", "teach", "learn", "backup", "organize",
    "buy", "sell", "trade", "close trade", "orders", "positions", "equity", "balance", "profit"
}

# Known App Aliases mapping to canonical app names
APP_ALIASES_MAP: Dict[str, str] = {
    # MetaTrader / Trading
    "mt5": "MetaTrader 5",
    "metatrader": "MetaTrader 5",
    "metatrader 5": "MetaTrader 5",
    "metatrader5": "MetaTrader 5",
    "mt4": "MetaTrader 4",
    "tradingview": "TradingView",

    # Browsers
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "googlechrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "edge": "Microsoft Edge",
    "msedge": "Microsoft Edge",
    "brave": "Brave Browser",
    "opera": "Opera Browser",

    # Dev & Tools
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "cursor": "Cursor",
    "terminal": "Terminal",
    "cmd": "Command Prompt",
    "powershell": "PowerShell",
    "pwsh": "PowerShell",
    "git": "Git Bash",
    "postman": "Postman",
    "pycharm": "PyCharm",
    "docker": "Docker Desktop",

    # Communication & Social
    "discord": "Discord",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "slack": "Slack",
    "zoom": "Zoom",
    "teams": "Microsoft Teams",

    # Utilities & Media
    "spotify": "Spotify",
    "vlc": "VLC Media Player",
    "capcut": "CapCut",
    "tor": "Tor Browser",
    "tor browser": "Tor Browser",
    "urbanvpn": "UrbanVPN",
    "urban vpn": "UrbanVPN",
    "opera": "Opera Air Browser",
    "opera air": "Opera Air Browser",
    "comet": "Comet",
    "antigravity": "Antigravity IDE",
    "metaeditor": "MetaEditor 5",
    "notepad": "Notepad",
    "notepad++": "Notepad++",
    "calculator": "Calculator",
    "calc": "Calculator",
    "explorer": "File Explorer",
    "file explorer": "File Explorer",
    "task manager": "Task Manager",
    "taskmgr": "Task Manager",
    "settings": "Windows Settings",
    "paint": "Paint",
    "obsidian": "Obsidian",
    "notion": "Notion",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
}

# Standard Forex / Crypto Symbol Normalization
SYMBOL_ALIASES_MAP: Dict[str, str] = {
    "gold": "XAUUSD",
    "sona": "XAUUSD",
    "xau": "XAUUSD",
    "xauusd": "XAUUSD",
    "xau/usd": "XAUUSD",
    "eurusd": "EURUSD",
    "eur/usd": "EURUSD",
    "euro": "EURUSD",
    "gbpusd": "GBPUSD",
    "gbp/usd": "GBPUSD",
    "pound": "GBPUSD",
    "cable": "GBPUSD",
    "usdjpy": "USDJPY",
    "usd/jpy": "USDJPY",
    "yen": "USDJPY",
    "btc": "BTCUSD",
    "bitcoin": "BTCUSD",
    "btcusd": "BTCUSD",
    "eth": "ETHUSD",
    "ethereum": "ETHUSD",
    "ethusd": "ETHUSD",
    "sol": "SOLUSD",
    "solana": "SOLUSD",
    "solusd": "SOLUSD",
    "oil": "USOUSD",
    "crude": "USOUSD",
    "wti": "USOUSD",
}


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class BilingualIntent:
    """Standardized representation of a parsed natural language command."""
    intent: str
    category: str
    language: str
    action: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""
    normalized_text: str = ""
    translated_intent: str = ""
    requires_confirmation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_trading(self) -> bool:
        return self.category == "trading"

    def is_os(self) -> bool:
        return self.category in ("os", "system")

    def is_teaching(self) -> bool:
        return self.intent == "teach_skill"

    def is_browser_vision(self) -> bool:
        return self.category in ("browser", "vision")

    def is_radar(self) -> bool:
        return self.category == "radar"

    def is_crypto(self) -> bool:
        return self.category == "crypto"

    def is_linux(self) -> bool:
        return self.category == "linux"

    def is_android(self) -> bool:
        return self.category == "android"


# ==============================================================================
# BILINGUAL PARSER ENGINE
# ==============================================================================

class RomanUrduParser:
    """
    Unified Bilingual (Roman Urdu & English) NLP Normalizer & Intent Classifier.
    """

    def __init__(self) -> None:
        self.urdu_markers = ROMAN_URDU_MARKERS
        self.english_verbs = ENGLISH_ACTION_VERBS
        self.app_aliases = APP_ALIASES_MAP
        self.symbol_aliases = SYMBOL_ALIASES_MAP

    def detect_language(self, text: str) -> str:
        """
        High-accuracy detector classifying input as Roman Urdu ('ur') or English ('en').
        """
        if not text or not text.strip():
            return "en"

        cleaned = text.lower().strip()
        tokens = set(re.findall(r"[a-zA-Z]+", cleaned))

        urdu_hits = len(tokens.intersection(self.urdu_markers))
        english_hits = len(tokens.intersection(self.english_verbs | ENGLISH_COMMON_WORDS))

        # Explicit strong Roman Urdu grammatical predicates & markers
        strong_urdu_markers = [
            "kardo", "kar do", "khatam karo", "chala do", "chalao", "khol do", "kholo",
            "band karo", "band kardo", "rok do", "roko", "barhao", "barha do", "badhao",
            "kam karo", "awaz barhao", "awaz kam", "tasveer lo", "screenshot lo",
            "dikhao", "batao", "samjhao", "kya hai", "kitna hai", "kitni hai",
            "jab bhi", "naya skill", "nayi capability", "se poocho", "dhoondo",
            "bhai", "bhae", "sunen", "banao", "bana do", "parho", "tamam", "kholna"
        ]
        for phrase in strong_urdu_markers:
            if re.search(r"\b" + re.escape(phrase) + r"\b", cleaned):
                urdu_hits += 6

        # Explicit English phrases
        english_phrases = [
            "open ", "close all", "launch ", "shut down", "lock the", "take screenshot",
            "what is ", "show me ", "tell me ", "check status", "whenever i say",
            "teach skill", "create skill", "search web for", "ask chatgpt",
            "increase volume", "decrease volume", "inspect vitals"
        ]
        for phrase in english_phrases:
            if cleaned.startswith(phrase) or phrase in cleaned:
                english_hits += 4

        if urdu_hits > 0 and urdu_hits >= english_hits:
            return "ur"
        return "en"

    def normalize_text(self, text: str) -> str:
        """
        Normalizes phonetic variations, compound words, and removes noisy punctuation.
        """
        if not text:
            return ""

        s = text.strip()
        
        # Replace multiple spaces
        s = re.sub(r"\s+", " ", s)

        # Compound verb normalization
        compound_normalizations = [
            (r"\bkar\s+do\b", "kardo"),
            (r"\bkhol\s+do\b", "kholdo"),
            (r"\bchala\s+do\b", "chalado"),
            (r"\bband\s+kar\s*do\b", "band kardo"),
            (r"\brok\s+do\b", "rokdo"),
            (r"\bbarha\s+do\b", "barhao"),
            (r"\bbadha\s+do\b", "barhao"),
            (r"\bbadhao\b", "barhao"),
            (r"\bkam\s+kar\s*do\b", "kam karo"),
            (r"\bbana\s+do\b", "banao"),
            (r"\bparh\s+do\b", "parho"),
            (r"\blikh\s+do\b", "likho"),
            (r"\btasweer\b", "tasveer"),
            (r"\btasver\b", "tasveer"),
            (r"\bawaaz\b", "awaz"),
            (r"\bbhae\b", "bhai"),
            (r"\byaar\b", "yar"),
            (r"\bdekhein\b", "dekho"),
            (r"\bdikhayein\b", "dikhao"),
            (r"\bbataiye\b", "batao"),
            (r"\bkholein\b", "kholo"),
            (r"\bchalayein\b", "chalao"),
            (r"\bvolume\s+up\b", "volume up"),
            (r"\bvolume\s+down\b", "volume down"),
            (r"\bscreen\s+shot\b", "screenshot"),
        ]
        
        lower_s = s.lower()
        for pat, repl in compound_normalizations:
            lower_s = re.sub(pat, repl, lower_s, flags=re.IGNORECASE)

        return lower_s

    def extract_app_target(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Extracts matched app alias and canonical name. Returns (alias, canonical_name).
        """
        lower = text.lower()
        sorted_keys = sorted(self.app_aliases.keys(), key=lambda k: len(k), reverse=True)
        for key in sorted_keys:
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, lower):
                return key, self.app_aliases[key]
        return None

    def extract_trading_parameters(self, text: str) -> Dict[str, Any]:
        """
        Extracts symbol, action, lot size, stop loss, and take profit.
        """
        lower = text.lower()
        params: Dict[str, Any] = {
            "symbol": "XAUUSD",
            "action": "status",
            "lots": 0.01,
            "sl": 0.0,
            "tp": 0.0,
        }

        # 1. Symbol Extraction
        for alias, canonical in self.symbol_aliases.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", lower):
                params["symbol"] = canonical
                break

        # 2. Lot Size Extraction (e.g., 0.01 lot, 0.5 lots, 1 lot, 0.02)
        lot_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:lots?|lot\s*size|l)\b", lower)
        if lot_match:
            try:
                params["lots"] = float(lot_match.group(1))
            except ValueError:
                pass
        else:
            # Look for stand-alone float after buy/sell
            float_match = re.search(r"\b(?:buy|sell)\s+(\d+\.\d+)\b", lower)
            if float_match:
                try:
                    params["lots"] = float(float_match.group(1))
                except ValueError:
                    pass

        # 3. Action Extraction
        if any(w in lower for w in ["buy", "long", "khareedo", "khareedna", "kharid"]):
            params["action"] = "buy"
        elif any(w in lower for w in ["sell", "short", "becho", "bechna"]):
            params["action"] = "sell"
        elif any(w in lower for w in ["close all", "close trade", "close positions", "trade close", "band kardo", "tamam trades close", "exit trade", "liquidate"]):
            params["action"] = "close"
        elif any(w in lower for w in ["breakeven", "break even", "be karo", "be kardo", "lock be", "lock breakeven"]):
            params["action"] = "breakeven"
        elif any(w in lower for w in ["positions", "open positions", "trades dikhao", "open trades"]):
            params["action"] = "positions"
        elif any(w in lower for w in ["calendar", "news", "economic news", "khabrein"]):
            params["action"] = "calendar"
        elif any(w in lower for w in ["audit", "ledger", "aladdin var", "var test", "risk radar"]):
            params["action"] = "audit"
        elif any(w in lower for w in ["strategies", "models", "walk forward"]):
            params["action"] = "strategies"
        elif any(w in lower for w in ["balance", "equity", "pnl", "profit", "loss", "status", "batao", "haal", "analysis"]):
            params["action"] = "status"

        # 4. SL / TP Extraction
        sl_match = re.search(r"\bsl\s*(?:=|:|\s+)?\s*(\d+(?:\.\d+)?)\b", lower)
        if sl_match:
            try:
                params["sl"] = float(sl_match.group(1))
            except ValueError:
                pass

        tp_match = re.search(r"\btp\s*(?:=|:|\s+)?\s*(\d+(?:\.\d+)?)\b", lower)
        if tp_match:
            try:
                params["tp"] = float(tp_match.group(1))
            except ValueError:
                pass

        return params

    def extract_volume_parameter(self, text: str) -> Dict[str, Any]:
        """
        Extracts volume mode (up, down, set, mute, unmute, query) and numeric values.
        """
        lower = text.lower()
        params: Dict[str, Any] = {}

        is_up = any(w in lower for w in ["up", "increase", "raise", "boost", "barhao", "tez", "ziada", "zyada"])
        is_down = any(w in lower for w in ["down", "decrease", "lower", "reduce", "kam", "ghatao", "ahista", "dheema", "halka"])
        is_mute = any(w in lower for w in ["mute", "awaz band", "silent", "khamosh"])
        is_unmute = any(w in lower for w in ["unmute", "awaz kholo", "un-mute", "awaz khol"])

        num_match = re.search(r"\b(?:to\s+|par\s+|pe\s+)?(\d{1,3})\s*(?:%|percent|prcnt)?\b", lower)

        if is_unmute:
            params["mode"] = "unmute"
        elif is_mute:
            params["mode"] = "mute"
        elif is_up:
            params["mode"] = "up"
            params["step"] = int(num_match.group(1)) if num_match else 5
        elif is_down:
            params["mode"] = "down"
            params["step"] = int(num_match.group(1)) if num_match else 5
        elif num_match:
            val = int(num_match.group(1))
            if 0 <= val <= 100:
                params["value"] = val
                params["mode"] = "set"
        else:
            params["mode"] = "query"

        return params

    def extract_skill_teaching(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detects 1-Shot dynamic skill compilation instructions in Urdu and English.
        Examples:
        - "jab bhi main kahoon X to Y karo"
        - "whenever I say X do Y" / "whenever I say X then Y"
        - "teach: when I say X do Y"
        - "naya skill banao X jo Y kare"
        - "learn skill X: Y"
        """
        lower = text.strip()

        # 1. Roman Urdu Pattern: "jab bhi main kaho(on) X to Y karo/kardo"
        ur_match1 = re.search(
            r"jab\s+bhi\s+(?:main\s+)?(?:kahoon|kaho|boloon|bolon)\s+(?:ke\s+|['\"]?)(.+?)['\"]?\s+(?:to|tab|phir)\s+(.+)",
            lower,
            re.IGNORECASE
        )
        if ur_match1:
            trigger = ur_match1.group(1).strip(" '\"")
            action = ur_match1.group(2).strip(" '\"")
            # clean trailing 'karo' or 'kardo'
            action_clean = re.sub(r"\s+(?:karo|kardo|karna|chalana)$", "", action, flags=re.IGNORECASE).strip()
            name_slug = re.sub(r"[^a-z0-9_]+", "_", trigger.lower()).strip("_")[:40] or "custom_learned_skill"
            return {
                "trigger": trigger,
                "action": action_clean,
                "skill_name": name_slug,
                "raw_instruction": text,
                "language": "ur"
            }

        # 2. Roman Urdu Pattern: "naya skill banao X jo Y kare" / "nayi capability banao ..."
        ur_match2 = re.search(
            r"nay[ai]\s+(?:skill|capability|task)\s+(?:banao\s+)?['\"]?([a-zA-Z0-9_\s]+?)['\"]?\s+(?:jo|ke)\s+(.+)",
            lower,
            re.IGNORECASE
        )
        if ur_match2:
            raw_name = ur_match2.group(1).strip()
            action = ur_match2.group(2).strip()
            name_slug = re.sub(r"[^a-z0-9_]+", "_", raw_name.lower()).strip("_")[:40] or "custom_skill"
            return {
                "trigger": raw_name,
                "action": action,
                "skill_name": name_slug,
                "raw_instruction": text,
                "language": "ur"
            }

        # 3. English Pattern: "whenever I say X (then) do Y" / "when I say X do Y"
        en_match1 = re.search(
            r"(?:whenever|when)\s+(?:i\s+say|user\s+says)\s+['\"]?(.+?)['\"]?\s+(?:then\s+|,?\s*)(?:do\s+|run\s+|execute\s+|perform\s+|)(.+)",
            lower,
            re.IGNORECASE
        )
        if en_match1:
            trigger = en_match1.group(1).strip(" '\"")
            action = en_match1.group(2).strip(" '\"")
            name_slug = re.sub(r"[^a-z0-9_]+", "_", trigger.lower()).strip("_")[:40] or "custom_learned_skill"
            return {
                "trigger": trigger,
                "action": action,
                "skill_name": name_slug,
                "raw_instruction": text,
                "language": "en"
            }

        # 4. English Pattern: "teach: when I say X do Y" or "teach skill X: Y"
        en_match2 = re.search(
            r"teach(?:\s+skill|\s+me)?\s*[:\-]?\s*(?:when\s+i\s+say\s+)?['\"]?(.+?)['\"]?\s*(?:to|:|->|=>|does)\s*(.+)",
            lower,
            re.IGNORECASE
        )
        if en_match2:
            trigger = en_match2.group(1).strip(" '\"")
            action = en_match2.group(2).strip(" '\"")
            name_slug = re.sub(r"[^a-z0-9_]+", "_", trigger.lower()).strip("_")[:40] or "custom_learned_skill"
            return {
                "trigger": trigger,
                "action": action,
                "skill_name": name_slug,
                "raw_instruction": text,
                "language": "en"
            }

        return None

    def parse_command(self, raw_command: str) -> BilingualIntent:
        """
        Parses raw text command into a structured `BilingualIntent`.
        """
        raw_clean = (raw_command or "").strip()
        if not raw_clean:
            return BilingualIntent(
                intent="empty",
                category="general",
                language="en",
                action="none",
                confidence=0.0,
                raw_text="",
                normalized_text="",
                translated_intent="Empty command received."
            )

        lang = self.detect_language(raw_clean)
        norm = self.normalize_text(raw_clean)

        # -------------------------------------------------------------
        # 1. 1-Shot Skill Teaching Trigger Detection
        # -------------------------------------------------------------
        skill_teach = self.extract_skill_teaching(raw_clean)
        if skill_teach:
            return BilingualIntent(
                intent="teach_skill",
                category="skill",
                language=lang,
                action="compile_skill",
                target=skill_teach["skill_name"],
                parameters=skill_teach,
                confidence=0.99,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Teach novel dynamic skill '{skill_teach['skill_name']}' triggered on '{skill_teach['trigger']}'"
            )

        # -------------------------------------------------------------
        # 2. Explicit Skill Execution Trigger
        # -------------------------------------------------------------
        skill_exec_match = re.search(r"\b(?:run|execute|chalao)\s+skill\s+([a-zA-Z0-9_-]+)\b", norm)
        if skill_exec_match:
            s_name = skill_exec_match.group(1)
            return BilingualIntent(
                intent="execute_skill",
                category="skill",
                language=lang,
                action="execute_skill",
                target=s_name,
                parameters={"skill_name": s_name},
                confidence=0.98,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Execute learned dynamic skill '{s_name}'"
            )

        # -------------------------------------------------------------
        # 2A. Linux / WSL2 Subsystem Operations
        # -------------------------------------------------------------
        if (norm.startswith("wsl ") or norm.startswith("bash ") or 
            any(k in norm for k in [
                "run linux", "ubuntu command", "linux command", "wsl command",
                "ubuntu mein chalao", "linux pe chalao", "run wsl", "run bash",
                "linux terminal", "ubuntu terminal"
            ])):
            linux_cmd = raw_clean
            for pfx in [
                "run linux command", "run linux", "linux command", "ubuntu command",
                "wsl command", "run wsl", "run bash", "ubuntu mein chalao",
                "linux pe chalao", "wsl", "bash"
            ]:
                if linux_cmd.lower().startswith(pfx):
                    linux_cmd = linux_cmd[len(pfx):].strip(" :")
                    break

            return BilingualIntent(
                intent="linux_execution",
                category="linux",
                language=lang,
                action="execute_wsl",
                target="wsl_ubuntu",
                parameters={"command": linux_cmd or "uname -a", "subsystem": "WSL2"},
                confidence=0.97,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Execute command inside Linux/WSL environment: {linux_cmd or 'uname -a'}"
            )

        # -------------------------------------------------------------
        # 2B. Android / OpenDroid Mobile Bridge (ADB)
        # -------------------------------------------------------------
        if (norm.startswith("adb ") or any(k in norm for k in [
            "adb devices", "adb shell", "android phone", "mobile phone", "phone status",
            "mobile status", "mobile battery", "phone battery", "open mobile app",
            "phone pe app", "mobile pe app", "android tap", "phone screen", "yeh dabao"
        ])):
            if "device" in norm or "status" in norm or "battery" in norm:
                m_action = "device_status"
            elif "tap" in norm:
                m_action = "tap"
            elif "swipe" in norm:
                m_action = "swipe"
            elif any(w in norm for w in ["open", "kholo", "launch"]):
                m_action = "open_app"
            else:
                m_action = "execute_adb"

            adb_args = raw_clean
            for pfx in ["adb shell", "adb"]:
                if adb_args.lower().startswith(pfx):
                    adb_args = adb_args[len(pfx):].strip()
                    break

            return BilingualIntent(
                intent="android_mobile_control",
                category="android",
                language=lang,
                action=m_action,
                target="opendroid_bridge",
                parameters={"raw_command": raw_clean, "adb_args": adb_args, "subsystem": "OpenDroidBridge"},
                confidence=0.96,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Dispatch OpenDroid mobile control directive ({m_action})"
            )

        # -------------------------------------------------------------
        # 3. Workstation & System Power Operations
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "lock pc", "pc lock", "computer lock", "workstation lock",
            "lock workstation", "pc lock kardo", "computer lock kardo", "workstation lock kardo",
            "screen lock"
        ]):
            return BilingualIntent(
                intent="os_power",
                category="os",
                language=lang,
                action="lock",
                target="workstation",
                parameters={"mode": "lock"},
                confidence=0.99,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent="Lock workstation immediately"
            )

        if any(k in norm for k in [
            "restart pc", "system restart", "restart computer", "reboot pc",
            "pc restart kardo", "computer restart kardo"
        ]):
            return BilingualIntent(
                intent="os_power",
                category="os",
                language=lang,
                action="restart",
                target="workstation",
                parameters={"mode": "restart"},
                confidence=0.95,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent="Restart PC workstation",
                requires_confirmation=True
            )

        if any(k in norm for k in [
            "shutdown pc", "computer shutdown", "pc band kardo", "system band kardo",
            "turn off pc", "power off"
        ]):
            return BilingualIntent(
                intent="os_power",
                category="os",
                language=lang,
                action="shutdown",
                target="workstation",
                parameters={"mode": "shutdown"},
                confidence=0.95,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent="Shut down PC workstation",
                requires_confirmation=True
            )

        # -------------------------------------------------------------
        # 4. System Volume Operations
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "volume", "sound", "awaz", "mute", "unmute", "audio level", "volume up", "volume down"
        ]):
            vol_params = self.extract_volume_parameter(norm)
            return BilingualIntent(
                intent="os_volume",
                category="os",
                language=lang,
                action=f"volume_{vol_params.get('mode', 'adjust')}",
                target="system_volume",
                parameters=vol_params,
                confidence=0.96,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Adjust workstation volume ({vol_params.get('mode', 'adjust')})"
            )

        # -------------------------------------------------------------
        # 5. Screen Capture / Inspection
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "screenshot", "screen capture", "capture screen", "snapshot",
            "tasveer lo", "screen ki tasveer", "screenshot lo", "tasveer kheencho",
            "screen dekho", "look at screen", "screen inspect"
        ]):
            inspect_only = any(w in norm for w in ["dekho", "look", "inspect", "samjhao"])
            return BilingualIntent(
                intent="os_screenshot",
                category="vision" if inspect_only else "os",
                language=lang,
                action="capture_and_inspect" if inspect_only else "screen_capture",
                target="screen",
                parameters={"inspect_only": inspect_only},
                confidence=0.97,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent="Capture workstation screen state and inspect visually"
            )

        # -------------------------------------------------------------
        # 6. Desktop Application Launch / Close / Switch
        # -------------------------------------------------------------
        app_target = self.extract_app_target(norm)
        if app_target:
            alias, canonical = app_target

            # Check if command is to close/kill
            is_close = any(w in norm for w in ["band", "close", "kill", "terminate", "stop", "quit", "exit", "hatao", "rok do", "khatam"])
            # Check if command is to switch/focus
            is_switch = any(w in norm for w in ["switch", "focus", "bring", "samne lao", "lao", "dikhao"])
            # Check if command is to launch/open
            is_launch = any(w in norm for w in ["kholo", "kholdo", "khol", "open", "launch", "start", "run", "chalao", "chalado", "chala", "edit", "use", "kholna", "shuru"])

            if is_close:
                return BilingualIntent(
                    intent="os_app_control",
                    category="os",
                    language=lang,
                    action="terminate_app",
                    target=canonical,
                    parameters={"app_name": canonical, "alias": alias},
                    confidence=0.95,
                    raw_text=raw_clean,
                    normalized_text=norm,
                    translated_intent=f"Close application {canonical}"
                )
            elif is_switch:
                return BilingualIntent(
                    intent="os_app_control",
                    category="os",
                    language=lang,
                    action="switch_app",
                    target=canonical,
                    parameters={"app_name": canonical, "alias": alias},
                    confidence=0.94,
                    raw_text=raw_clean,
                    normalized_text=norm,
                    translated_intent=f"Bring {canonical} to foreground"
                )
            elif is_launch or norm.startswith(alias) or norm.endswith(alias) or f" {alias} " in f" {norm} ":
                return BilingualIntent(
                    intent="os_app_control",
                    category="os",
                    language=lang,
                    action="launch_app",
                    target=canonical,
                    parameters={"app_name": canonical, "alias": alias},
                    confidence=0.93,
                    raw_text=raw_clean,
                    normalized_text=norm,
                    translated_intent=f"Launch application {canonical}"
                )

        # -------------------------------------------------------------
        # 7. MT5 Forex & Prop Firm Trading Actions
        # -------------------------------------------------------------
        trading_keywords = [
            "trade", "trading", "gold", "sona", "xauusd", "eurusd", "gbpusd", "usdjpy",
            "pipdance", "ftmo", "lot", "lots", "pnl", "equity", "balance", "drawdown",
            "positions", "open positions", "sl", "tp", "order", "buy", "sell", "close trade",
            "aladdin var", "economic calendar", "prop account", "breakeven", "break even", "be karo", "liquidate"
        ]
        if any(k in norm for k in trading_keywords):
            t_params = self.extract_trading_parameters(norm)
            action = t_params.get("action", "status")
            return BilingualIntent(
                intent="trading_operation",
                category="trading",
                language=lang,
                action=action,
                target=t_params.get("symbol", "XAUUSD"),
                parameters=t_params,
                confidence=0.96,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Execute trading operation {action.upper()} for {t_params.get('symbol')} ({t_params.get('lots')} lots)"
            )

        # -------------------------------------------------------------
        # 8. Geopolitical Radar & World Monitor
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "world", "defcon", "geopolitical", "chokepoint", "chokepoints",
            "shock level", "earthquake", "earthquakes", "briefing", "sitrep",
            "hormuz", "bab el mandeb", "suez"
        ]):
            cat = "world"
            for c in ["shock", "chokepoints", "earthquakes", "briefing", "sitrep"]:
                if c in norm:
                    cat = c
                    break
            return BilingualIntent(
                intent="geopolitical_radar",
                category="radar",
                language=lang,
                action="radar_query",
                target=cat,
                parameters={"category": cat},
                confidence=0.95,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Query geopolitical radar category '{cat}'"
            )

        # -------------------------------------------------------------
        # 9. Crypto & Meme Coin Analytics
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
            "meme coin", "memecoin", "pepe", "bonk", "wif", "sui", "tao", "ondo",
            "honeypot", "liquidity lock", "anti rug"
        ]):
            return BilingualIntent(
                intent="crypto_analytics",
                category="crypto",
                language=lang,
                action="crypto_query",
                target="crypto_matrix",
                parameters={"query": raw_clean},
                confidence=0.94,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Perform crypto market analysis for query: {raw_clean}"
            )

        # -------------------------------------------------------------
        # 10. Autonomous Browser & Vision Actions
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "search web", "web search", "internet pe dhoondo", "google search",
            "chatgpt se poocho", "claude se poocho", "deepseek se poocho",
            "find on github", "find on stackoverflow"
        ]):
            provider = "web"
            if "chatgpt" in norm: provider = "chatgpt"
            elif "claude" in norm: provider = "claude"
            elif "deepseek" in norm: provider = "deepseek"
            elif "github" in norm: provider = "github"
            elif "stackoverflow" in norm: provider = "stackoverflow"

            query_clean = raw_clean
            for pfx in ["search web for", "web search", "google search", "chatgpt se poocho", "claude se poocho", "deepseek se poocho", "search on"]:
                if query_clean.lower().startswith(pfx):
                    query_clean = query_clean[len(pfx):].strip(" :")

            return BilingualIntent(
                intent="browser_navigation",
                category="browser",
                language=lang,
                action="query_web_provider",
                target=provider,
                parameters={"provider": provider, "query": query_clean},
                confidence=0.92,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent=f"Execute autonomous web query on {provider}: {query_clean}"
            )

        # -------------------------------------------------------------
        # 11. System Vitals & Diagnostics
        # -------------------------------------------------------------
        if any(k in norm for k in [
            "system vitals", "vitals", "diagnostics", "pc health", "sehat",
            "cpu ram", "hardware status", "ports check", "daemons status", "status"
        ]):
            return BilingualIntent(
                intent="system_diagnostics",
                category="system",
                language=lang,
                action="diagnostics",
                target="workstation_vitals",
                parameters={},
                confidence=0.91,
                raw_text=raw_clean,
                normalized_text=norm,
                translated_intent="Report comprehensive workstation health and system vitals"
            )

        # -------------------------------------------------------------
        # 12. General Conversational AI Fallback
        # -------------------------------------------------------------
        return BilingualIntent(
            intent="conversational_query",
            category="general",
            language=lang,
            action="query_llm",
            target="ai_gateway",
            parameters={"query": raw_clean},
            confidence=0.85,
            raw_text=raw_clean,
            normalized_text=norm,
            translated_intent=f"Conversational AI query: {raw_clean}"
        )


# Singleton Instance
_PARSER_INSTANCE: Optional[RomanUrduParser] = None

def get_roman_urdu_parser() -> RomanUrduParser:
    """Returns the shared singleton RomanUrduParser instance."""
    global _PARSER_INSTANCE
    if _PARSER_INSTANCE is None:
        _PARSER_INSTANCE = RomanUrduParser()
    return _PARSER_INSTANCE

def parse_bilingual_command(text: str) -> BilingualIntent:
    """Helper entrypoint to parse bilingual command into a BilingualIntent."""
    return get_roman_urdu_parser().parse_command(text)
