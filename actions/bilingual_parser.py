"""
actions/bilingual_parser.py
===============================================================================
Bilingual Conversational Parser supporting Roman Urdu and English.
Parses natural language OS automation, application management, system controls,
and workspace commands into structured execution intents and receipts.
===============================================================================
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# Roman Urdu marker vocabulary for language classification
ROMAN_URDU_MARKERS = {
    "karo", "kardo", "kar do", "kariye", "karna", "kar",
    "chalao", "chala do", "chalana", "chalayein", "chala",
    "kholo", "khol do", "kholna", "kholein", "khol",
    "band", "roko", "rok do", "khatam", "hatao", "mitao",
    "barhao", "barha do", "badhao", "tez", "ziada", "zyada",
    "kam", "ghatao", "ahista", "dheema",
    "awaz", "awaaz", "sound",
    "dikhao", "dekho", "batao", "samjhao", "check",
    "tasveer", "tasweer", "tasver",
    "samne", "lao", "jao", "par", "pe", "se", "mein", "me",
    "ka", "ki", "ke", "ko", "kya", "konsi", "kaunsi", "hain", "hai",
    "nayee", "naya", "banao", "bana do", "parho", "parh do",
    "sehat", "halat", "bhejo", "rakho"
}

# English action verbs
ENGLISH_ACTION_VERBS = {
    "launch", "open", "start", "run",
    "close", "kill", "terminate", "stop", "quit", "exit", "shutdown",
    "switch", "focus", "bring",
    "inspect", "list", "show", "check", "status",
    "volume", "mute", "unmute", "increase", "decrease", "set",
    "capture", "screenshot", "snapshot",
    "diagnostics", "vitals", "monitor", "health",
    "search", "find", "create", "make", "edit", "backup", "organize", "delete"
}

# Known App Aliases mapping to canonical app names
APP_ALIASES_MAP = {
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


class BilingualParser:
    """
    Intelligent NLP parser for Roman Urdu and English computer automation commands.
    Extracts action, target, parameters, detected language, and English translation.
    """

    def __init__(self):
        pass

    def detect_language(self, text: str) -> str:
        """
        Detects if input is Roman Urdu ('ur') or English ('en').
        """
        if not text or not text.strip():
            return "en"

        tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
        urdu_matches = len(tokens.intersection(ROMAN_URDU_MARKERS))
        english_matches = len(tokens.intersection(ENGLISH_ACTION_VERBS))

        lower_text = text.lower()
        phrases = [
            "band karo", "band kar do", "band kardo", "chalao", "chala do",
            "kholo", "khol do", "samne lao", "barhao", "kam karo",
            "awaz barhao", "awaz kam", "backup banao", "repo backup",
            "screenshot lo", "tasveer lo", "check karo", "dikhao", "batao",
            "par jao", "pe jao", "khatam karo"
        ]
        for phrase in phrases:
            if phrase in lower_text:
                urdu_matches += 2

        if urdu_matches > 0 and urdu_matches >= english_matches:
            return "ur"
        return "en"

    def extract_app_target(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Extracts matched app alias and canonical name from text.
        Returns (alias, canonical_name) or None.
        """
        lower = text.lower()
        sorted_keys = sorted(APP_ALIASES_MAP.keys(), key=lambda k: len(k), reverse=True)
        for key in sorted_keys:
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, lower):
                return key, APP_ALIASES_MAP[key]
        return None

    def extract_volume_parameter(self, text: str) -> Dict[str, Any]:
        """
        Extracts volume operations, direction, and percentage values.
        """
        lower = text.lower()
        params: Dict[str, Any] = {}

        is_up = any(w in lower for w in ["up", "increase", "raise", "boost", "barhao", "barha", "badhao", "tez", "ziada", "zyada"])
        is_down = any(w in lower for w in ["down", "decrease", "lower", "reduce", "kam", "ghatao", "ahista", "dheema"])
        is_mute = any(w in lower for w in ["mute", "awaz band", "silent"])
        is_unmute = any(w in lower for w in ["unmute", "awaz kholo", "un-mute"])

        num_match = re.search(r"\b(?:to\s+)?(\d{1,3})\s*(?:%|percent)?\b", lower)

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

    def parse_command(self, command_str: str) -> Dict[str, Any]:
        """
        Parses raw text command into a structured intent representation.
        """
        raw_clean = (command_str or "").strip()
        if not raw_clean:
            return {
                "input_lang": "en",
                "intent": "unknown",
                "action": "diagnostics",
                "target": None,
                "parameters": {},
                "confidence": 0.0,
                "raw_text": "",
                "translated_intent": "Empty command received."
            }

        lang = self.detect_language(raw_clean)
        lower = raw_clean.lower()

        # 1. Screen Capture / Inspection
        if any(k in lower for k in [
            "screenshot", "screen capture", "capture screen", "screen snapshot",
            "tasveer lo", "tasweer lo", "screen ki tasveer", "screenshot lo",
            "screen inspect", "inspect screen", "screen dekho"
        ]):
            return {
                "input_lang": lang,
                "intent": "screen_capture",
                "action": "screen_capture",
                "target": "screen",
                "parameters": {"inspect_only": ("inspect" in lower or "dekho" in lower)},
                "confidence": 0.98,
                "raw_text": raw_clean,
                "translated_intent": "Capture screen image and inspect visual state"
            }

        # 2. System Volume Operations
        if any(k in lower for k in [
            "volume", "sound", "awaz", "awaaz", "mute", "unmute", "audio level"
        ]):
            vol_params = self.extract_volume_parameter(lower)
            return {
                "input_lang": lang,
                "intent": "system_vol",
                "action": "system_vol",
                "target": "system_volume",
                "parameters": vol_params,
                "confidence": 0.95,
                "raw_text": raw_clean,
                "translated_intent": f"Adjust system volume ({vol_params.get('mode', 'adjust')})"
            }

        # 3. System Power Operations
        if any(k in lower for k in [
            "lock pc", "pc lock", "computer lock", "lock screen", "lock kardo", "lock karo",
            "sleep pc", "pc sleep", "computer sleep", "standby",
            "restart pc", "system restart", "restart computer", "reboot",
            "shutdown pc", "computer shutdown", "pc band karo", "system band karo",
            "hibernate pc", "hibernate computer"
        ]) or (("pc" in lower or "computer" in lower or "system" in lower) and "lock" in lower):
            power_mode = "lock"
            if "sleep" in lower:
                power_mode = "sleep"
            elif "restart" in lower or "reboot" in lower:
                power_mode = "restart"
            elif "shutdown" in lower or "band karo" in lower:
                power_mode = "shutdown"
            elif "hibernate" in lower:
                power_mode = "hibernate"

            return {
                "input_lang": lang,
                "intent": "system_power",
                "action": "system_power",
                "target": power_mode,
                "parameters": {"mode": power_mode, "force": "force" in lower},
                "confidence": 0.96,
                "raw_text": raw_clean,
                "translated_intent": f"Execute system power state action: {power_mode}"
            }

        # 4. System Diagnostics & Process Monitoring
        if any(k in lower for k in [
            "diagnostics", "diagnostic", "vitals", "system health", "disk health",
            "cpu usage", "ram usage", "memory usage", "process monitor",
            "system status", "pc status", "hardware status", "sehat check",
            "halat check", "system ki sehat", "disk space", "disk usage",
            "active procs", "process list", "top processes"
        ]):
            return {
                "input_lang": lang,
                "intent": "diagnostics",
                "action": "diagnostics",
                "target": "hardware_and_processes",
                "parameters": {"detailed": True},
                "confidence": 0.95,
                "raw_text": raw_clean,
                "translated_intent": "Inspect system vitals, hardware diagnostics, and active processes"
            }

        # 5. Application Inspection / List Running Apps
        if any(k in lower for k in [
            "list running apps", "running apps", "open apps", "active windows",
            "apps status", "konsi apps chal", "active apps check", "kya mt5 chal",
            "check if running", "running processes", "list apps", "inspect apps",
            "open windows", "running desktop apps"
        ]):
            app_match = self.extract_app_target(lower)
            target_app = app_match[1] if app_match else None
            return {
                "input_lang": lang,
                "intent": "app_inspect",
                "action": "app_inspect",
                "target": target_app or "all_apps",
                "parameters": {"filter": target_app},
                "confidence": 0.94,
                "raw_text": raw_clean,
                "translated_intent": f"Inspect running applications (filter: {target_app or 'all'})"
            }

        # 6. File & Workspace Automation
        if any(k in lower for k in [
            "backup", "repo backup", "backup workspace", "workspace backup",
            "search file", "search files", "file search", "find file",
            "create file", "new file", "nayee file", "file banao",
            "edit file", "modify file", "read file", "file parho",
            "delete file", "organize workspace", "scratch folder", "scratch workspace"
        ]):
            file_mode = "search"
            if "backup" in lower:
                file_mode = "backup"
            elif any(w in lower for w in ["create", "new", "nayee", "banao"]):
                file_mode = "create"
            elif any(w in lower for w in ["edit", "modify"]):
                file_mode = "edit"
            elif any(w in lower for w in ["read", "parho", "cat", "view"]):
                file_mode = "read"
            elif any(w in lower for w in ["delete", "remove", "mitao", "hatao"]):
                file_mode = "delete"
            elif any(w in lower for w in ["organize", "clean", "cleanup"]):
                file_mode = "organize"
            elif "scratch" in lower:
                file_mode = "scratch"

            file_param = ""
            tokens = raw_clean.split()
            for t in tokens:
                if "." in t or "_" in t or "/" in t or "\\" in t:
                    file_param = t.strip('"\'')
                    break

            return {
                "input_lang": lang,
                "intent": "file_op",
                "action": "file_op",
                "target": file_mode,
                "parameters": {"mode": file_mode, "path_or_pattern": file_param},
                "confidence": 0.92,
                "raw_text": raw_clean,
                "translated_intent": f"Execute workspace file operation: {file_mode} (target: {file_param or 'workspace'})"
            }

        # 7. Application Termination / Close / Kill
        if any(k in lower for k in [
            "close", "kill", "terminate", "stop", "quit", "exit",
            "band karo", "band kar do", "band kardo", "roko", "rok do",
            "khatam karo", "close karo"
        ]):
            app_match = self.extract_app_target(lower)
            if app_match:
                alias, canonical = app_match
                return {
                    "input_lang": lang,
                    "intent": "app_kill",
                    "action": "app_kill",
                    "target": canonical,
                    "parameters": {"alias": alias, "canonical": canonical, "force": ("force" in lower or "kill" in lower)},
                    "confidence": 0.96,
                    "raw_text": raw_clean,
                    "translated_intent": f"Gracefully terminate desktop application: {canonical}"
                }

        # 8. Application Launch / Open
        if any(k in lower for k in [
            "open", "launch", "start", "run",
            "chalao", "chala do", "kholo", "khol do", "on karo",
            "shuru karo", "open karo", "run karo", "start karo"
        ]) and any(app in lower for app in APP_ALIASES_MAP.keys()):
            app_match = self.extract_app_target(lower)
            if app_match:
                alias, canonical = app_match
                return {
                    "input_lang": lang,
                    "intent": "app_launch",
                    "action": "app_launch",
                    "target": canonical,
                    "parameters": {"alias": alias, "canonical": canonical},
                    "confidence": 0.95,
                    "raw_text": raw_clean,
                    "translated_intent": f"Launch desktop application: {canonical}"
                }

        # 9. Application Switching / Focusing
        if any(k in lower for k in [
            "switch to", "switch", "focus on", "focus", "bring to front",
            "samne lao", "par jao", "pe jao", "dikhao"
        ]) and any(app in lower for app in APP_ALIASES_MAP.keys()):
            app_match = self.extract_app_target(lower)
            if app_match:
                alias, canonical = app_match
                return {
                    "input_lang": lang,
                    "intent": "app_switch",
                    "action": "app_switch",
                    "target": canonical,
                    "parameters": {"alias": alias, "canonical": canonical},
                    "confidence": 0.94,
                    "raw_text": raw_clean,
                    "translated_intent": f"Switch focus to desktop application: {canonical}"
                }

        # Fallback: General System Inspection / Action
        return {
            "input_lang": lang,
            "intent": "diagnostics",
            "action": "diagnostics",
            "target": "general",
            "parameters": {"query": raw_clean},
            "confidence": 0.60,
            "raw_text": raw_clean,
            "translated_intent": f"Inspect system state in response to query: {raw_clean}"
        }


# Global singleton instance for high-throughput zero-allocation parsing
bilingual_parser = BilingualParser()

def parse_bilingual_command(command_str: str) -> Dict[str, Any]:
    """Convenience function to parse Roman Urdu or English commands."""
    return bilingual_parser.parse_command(command_str)
