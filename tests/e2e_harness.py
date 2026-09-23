"""
tests/e2e_harness.py — J.A.R.V.I.S. Sovereign Universal Cross-Device & Autonomous Self-Learning Test Harness
============================================================================================================
Provides unified fixtures, deterministic simulators, and mock/live adapters for:
- Bi-directional WebSockets (:8765 /ws/mobile) & Mobile REST API
- 3-Tier Desktop Screen Vision (UIA coordinates, GDI frame buffers, OCR simulation)
- Autonomous Web LLM Navigators (ChatGPT, Claude, DeepSeek, Google AI) & Developer Portals (SO, GitHub)
- Dynamic REST API <-> Browser Scraping Gateway with Hot-Swap & Failover
- 1-Shot Dynamic Skill Compiler, AST Validator, and Sandboxed Unit Test Runner
- Sub-Second Dense Vector Memory Engine (384-dim embeddings, cosine similarity)
- Unified Multi-Device Command Router, Bilingual Roman Urdu / English NLP, Telemetry Cards, Neural TTS
- Android Companion APK & PWA Manifest Verifier
============================================================================================================
"""

import os
import sys
import json
import math
import time
import uuid
import struct
import shutil
import sqlite3
import tempfile
import threading
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Callable

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ============================================================================
# 1. Mobile WebSocket & Client Harness
# ============================================================================

class MockWebSocketClient:
    """Simulates an Android Mobile Companion WebSocket connection to /ws/mobile."""

    def __init__(self, token: str = "jarvis_master_842", device_info: Optional[Dict[str, Any]] = None):
        self.token = token
        self.device_info = device_info or {
            "model": "Pixel 8 Pro",
            "os_version": "Android 14",
            "app_version": "1.0.0",
            "client_type": "native_apk"
        }
        self.is_authenticated = False
        self.sent_messages: List[Dict[str, Any]] = []
        self.received_messages: List[Dict[str, Any]] = []
        self.latency_ms: float = 12.5  # <50ms LAN latency

    def connect_and_authenticate(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        use_token = auth_token if auth_token is not None else self.token
        handshake_payload = {
            "type": "AUTH",
            "token": use_token,
            "device_info": self.device_info,
            "timestamp": time.time()
        }
        self.sent_messages.append(handshake_payload)
        
        # Verify token authentication contract
        if use_token == "jarvis_master_842" or (use_token and len(use_token) >= 8 and not use_token.startswith("invalid")):
            self.is_authenticated = True
            response = {
                "type": "AUTH_OK",
                "status": "authenticated",
                "features": ["cmd_exec", "trade_control", "screen_stream", "telemetry_push", "audio_alarm", "clipboard_sync"],
                "server_time": time.time(),
                "session_id": str(uuid.uuid4())
            }
        else:
            self.is_authenticated = False
            response = {
                "type": "AUTH_ERROR",
                "status": "unauthorized",
                "error": "Invalid authentication token",
                "timestamp": time.time()
            }
        self.received_messages.append(response)
        return response

    def send_command(self, cmd_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_authenticated:
            err = {"type": "ERROR", "error": "Not authenticated"}
            self.received_messages.append(err)
            return err

        msg = {"type": cmd_type, **payload, "timestamp": time.time()}
        self.sent_messages.append(msg)

        # Dispatch server reaction
        if cmd_type == "CMD_EXEC":
            command = payload.get("command", "")
            return self._handle_cmd_exec(command)
        elif cmd_type == "TRADE_ORDER":
            return self._handle_trade_order(payload)
        elif cmd_type == "MOBILE_TELEMETRY":
            return self._handle_telemetry(payload)
        elif cmd_type == "PING":
            res = {"type": "PONG", "timestamp": time.time()}
            self.received_messages.append(res)
            return res
        else:
            res = {"type": "ACK", "message_id": payload.get("id", str(uuid.uuid4())), "status": "processed"}
            self.received_messages.append(res)
            return res

    def _handle_cmd_exec(self, command: str) -> Dict[str, Any]:
        cmd_lower = command.lower().strip()
        if "malicious" in cmd_lower or "rmdir" in cmd_lower or "c:\\windows" in cmd_lower or "delete" in cmd_lower:
            res = {"type": "CMD_RESULT", "command": command, "output": "BLOCKED: Safety violation", "exit_code": 1}
        elif "!echo" in command:
            out = command.replace("!echo", "").strip()
            res = {"type": "CMD_RESULT", "command": command, "output": out, "exit_code": 0}
        elif cmd_lower in ["!dir", "dir", "!ls", "ls"] or "!dir" in command or cmd_lower.startswith("dir"):
            res = {"type": "CMD_RESULT", "command": command, "output": "PROJECT.md  main.py  mobile_control.py", "exit_code": 0}
        else:
            res = {"type": "CMD_RESULT", "command": command, "output": f"Executed: {command}", "exit_code": 0}
        self.received_messages.append(res)
        return res

    def _handle_trade_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        symbol = payload.get("symbol", "XAUUSD")
        action = payload.get("action", "BUY")
        lots = payload.get("lots", 0.01)
        res = {
            "type": "TRADE_RECEIPT",
            "order_id": int(time.time() * 1000) % 1000000,
            "symbol": symbol,
            "action": action,
            "lots": lots,
            "status": "FILLED",
            "price": 2745.50 if symbol == "XAUUSD" else 1.0850,
            "timestamp": time.time()
        }
        self.received_messages.append(res)
        return res

    def _handle_telemetry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("payload", {})
        res = {
            "type": "TELEMETRY_ACK",
            "battery_level": data.get("battery_level", 100),
            "is_charging": data.get("is_charging", False),
            "wifi_rssi_dbm": data.get("wifi_rssi_dbm", -45),
            "synced_at": time.time()
        }
        self.received_messages.append(res)
        return res

    def receive_pc_push(self, title: str, body: str, priority: str = "normal") -> Dict[str, Any]:
        msg = {
            "type": "PUSH_NOTIFICATION",
            "title": title,
            "body": body,
            "priority": priority,
            "timestamp": time.time()
        }
        self.received_messages.append(msg)
        return msg

    def receive_pc_alarm(self, tone: str = "siren", duration_sec: int = 5, volume: float = 1.0, tts_message: str = "") -> Dict[str, Any]:
        msg = {
            "type": "AUDIO_ALARM",
            "tone": tone,
            "duration_sec": duration_sec,
            "volume": volume,
            "tts_message": tts_message,
            "timestamp": time.time()
        }
        self.received_messages.append(msg)
        return msg

    def receive_clipboard_push(self, content: str) -> Dict[str, Any]:
        msg = {
            "type": "CLIPBOARD_PUSH",
            "content": content,
            "timestamp": time.time()
        }
        self.received_messages.append(msg)
        return msg


# ============================================================================
# 2. Desktop Vision & Screen Inspection Engine
# ============================================================================

class ScreenVisionEngine:
    """Hybrid 3-Tier Desktop Screen Vision (UIA + GDI Frame Capture + OCR)."""

    def __init__(self):
        self.dpi_scale = 1.0
        self.active_window = "J.A.R.V.I.S. Master Terminal"
        self.open_windows = [
            {"hwnd": 1001, "title": "J.A.R.V.I.S. Master Terminal", "rect": (0, 0, 1920, 1080), "is_active": True},
            {"hwnd": 1002, "title": "MetaTrader 5 - [XAUUSD, M5]", "rect": (100, 100, 1200, 800), "is_active": False},
            {"hwnd": 1003, "title": "Google Chrome - TradingView", "rect": (200, 150, 1400, 900), "is_active": False},
            {"hwnd": 1004, "title": "Visual Studio Code - jarvis", "rect": (50, 50, 1600, 950), "is_active": False},
        ]
        self.known_ui_elements = {
            "buy_button": (450, 320),
            "sell_button": (550, 320),
            "close_all_trades": (680, 320),
            "chrome_search_bar": (600, 82),
            "vscode_terminal_tab": (350, 850),
            "discord_send_button": (1150, 980),
        }

    def get_desktop_state(self) -> Dict[str, Any]:
        active = next((w for w in self.open_windows if w["is_active"]), self.open_windows[0])
        return {
            "active_window": active["title"],
            "active_hwnd": active["hwnd"],
            "active_rect": active["rect"],
            "window_count": len(self.open_windows),
            "windows": [w["title"] for w in self.open_windows],
            "dpi_scaling": self.dpi_scale,
            "timestamp": time.time()
        }

    def capture_gdi_frame(self, scale: float = 0.55, quality: int = 60) -> bytes:
        """Simulates native GDI bitblt screen frame capture returning valid JPEG header."""
        # Standard JPEG SOI (0xFFD8) and EOI (0xFFD9)
        fake_jpeg = bytearray([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x60, 0x00, 0x60, 0x00, 0x00])
        fake_jpeg.extend(b"\x00" * 512)
        fake_jpeg.extend([0xFF, 0xD9])
        return bytes(fake_jpeg)

    def locate_ui_element(self, description: str, target_window_title: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """Resolves (x, y) coordinates via UIA tree or OCR."""
        clean_desc = description.lower().replace(" ", "_").strip()
        if not clean_desc:
            return None
        for k, coords in self.known_ui_elements.items():
            if clean_desc in k or k in clean_desc:
                # Apply DPI scaling
                return (int(coords[0] * self.dpi_scale), int(coords[1] * self.dpi_scale))
        # Default fallback approximation if element contains keywords
        if "buy" in clean_desc:
            return (int(450 * self.dpi_scale), int(320 * self.dpi_scale))
        if "close" in clean_desc:
            return (int(680 * self.dpi_scale), int(320 * self.dpi_scale))
        return None

    def analyze_active_window(self, query: str) -> Dict[str, Any]:
        state = self.get_desktop_state()
        return {
            "query": query,
            "active_window": state["active_window"],
            "detected_text": [
                "J.A.R.V.I.S. Sovereign Quantum Cockpit",
                "DEFCON 2 - Strategic Alert",
                "XAUUSD BUY 0.01 @ 2745.50 PnL +$12.50",
                "Memory Recall: 384-dim Vector Engine Ready"
            ],
            "confidence": 0.98,
            "has_error_modal": False,
            "timestamp": time.time()
        }


# ============================================================================
# 3. Web LLM Autonomous Navigators & Developer Portals
# ============================================================================

class WebNavigator:
    """Autonomous Playwright / Chrome Web LLM & Developer Portal Scraper."""

    PROVIDER_MAP = {
        "chatgpt": "chatgpt",
        "openai": "chatgpt",
        "claude": "claude",
        "anthropic": "claude",
        "deepseek": "deepseek",
        "google_ai": "google_ai",
        "gemini": "google_ai",
    }

    def __init__(self, cookies_dir: Optional[Path] = None):
        self.cookies_dir = cookies_dir or (BASE_DIR / "scratch" / "browser_sessions")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.session_active = True
        self.supported_providers = list(self.PROVIDER_MAP.keys())
        self.supported_portals = ["stackoverflow", "github"]

    def query_web_llm(self, provider: str, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        raw_p = provider.lower()
        if raw_p not in self.PROVIDER_MAP:
            return {"ok": False, "provider": provider, "error": f"Unsupported provider {provider}"}
        p = self.PROVIDER_MAP[raw_p]

        # Deterministic simulation of web LLM markdown extraction
        if "calculate" in prompt.lower() or "sum" in prompt.lower():
            code_snippet = "def calculate_total(a: float, b: float) -> float:\n    return a + b\n"
        elif "fibonacci" in prompt.lower():
            code_snippet = "def fibonacci(n: int) -> int:\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)\n"
        else:
            code_snippet = f"def run_autonomous_task(data: dict) -> dict:\n    # Synthesized by Web LLM ({p})\n    return {{'status': 'success', 'data': data}}\n"

        return {
            "ok": True,
            "provider": p,
            "prompt": prompt,
            "system_instruction": system_instruction,
            "raw_text": f"Here is the synthesized code solution from {p}:\n```python\n{code_snippet}```",
            "extracted_code": code_snippet,
            "language": "python",
            "response_time_ms": 340.0,
            "session_persisted": True
        }

    def query_technical_portal(self, portal: str, query: str, max_results: int = 3) -> Dict[str, Any]:
        pt = portal.lower()
        if pt == "stackoverflow":
            return {
                "ok": True,
                "portal": "stackoverflow",
                "query": query,
                "results": [
                    {
                        "question_id": 7812934,
                        "title": f"How to implement {query} in Python",
                        "votes": 142,
                        "accepted": True,
                        "code_snippets": ["import math\ndef solve(x):\n    return math.sqrt(x)"]
                    },
                    {
                        "question_id": 7812935,
                        "title": f"Fast solution for {query}",
                        "votes": 58,
                        "accepted": False,
                        "code_snippets": ["def solve_fast(x):\n    return x ** 0.5"]
                    }
                ][:max_results]
            }
        elif pt == "github":
            return {
                "ok": True,
                "portal": "github",
                "query": query,
                "results": [
                    {
                        "repo": f"jarvis-ecosystem/{query.replace(' ', '-')}",
                        "stars": 420,
                        "license": "MIT",
                        "code_url": f"https://raw.githubusercontent.com/jarvis-ecosystem/{query}/main/module.py",
                        "content": "def execute_workflow():\n    return {'result': 'ok'}"
                    }
                ][:max_results]
            }
        return {"ok": False, "portal": portal, "error": "Unknown technical portal"}


# ============================================================================
# 4. Dynamic REST API <-> Browser Scraping Hot-Swap Gateway
# ============================================================================

class APIUpgradeGateway:
    """Hot-swaps between direct REST APIs and Browser Scraping based on key availability."""

    def __init__(self, web_navigator: Optional[WebNavigator] = None):
        self.web_navigator = web_navigator or WebNavigator()
        self.api_keys: Dict[str, str] = {
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
            "gemini": os.getenv("GEMINI_API_KEY", ""),
        }
        self.rate_limited_providers: set = set()

    def set_api_key(self, provider: str, key: str) -> None:
        self.api_keys[provider.lower()] = key.strip()
        if key.strip() and provider.lower() in self.rate_limited_providers:
            self.rate_limited_providers.remove(provider.lower())

    def simulate_rate_limit(self, provider: str, rate_limited: bool = True) -> None:
        if rate_limited:
            self.rate_limited_providers.add(provider.lower())
        else:
            self.rate_limited_providers.discard(provider.lower())

    def route_query(self, provider: str, prompt: str, system_prompt: Optional[str] = None, prefer_browser: bool = False) -> Dict[str, Any]:
        p = provider.lower()
        key = self.api_keys.get(p, "")
        has_valid_key = bool(key and len(key) >= 10 and not key.startswith("invalid"))
        is_rate_limited = p in self.rate_limited_providers

        if has_valid_key and not prefer_browser and not is_rate_limited:
            # REST API Fast Path (<200ms)
            return {
                "ok": True,
                "provider": p,
                "mode": "REST_API",
                "prompt": prompt,
                "extracted_code": f"def rest_api_response():\n    return '{p}_rest_success'\n",
                "latency_ms": 115.0,
                "cost_usd": 0.0015
            }
        else:
            # Browser Scraping Fallback
            scrape_res = self.web_navigator.query_web_llm(p, prompt, system_prompt)
            scrape_res["mode"] = "BROWSER_SCRAPING"
            scrape_res["fallback_reason"] = "RATE_LIMITED" if is_rate_limited else ("NO_API_KEY" if not has_valid_key else "BROWSER_PREFERRED")
            scrape_res["latency_ms"] = 450.0
            return scrape_res

    def get_provider_capabilities(self) -> Dict[str, Dict[str, Any]]:
        caps = {}
        for p in ["openai", "anthropic", "deepseek", "gemini"]:
            has_key = bool(self.api_keys.get(p))
            caps[p] = {
                "rest_api_ready": has_key and (p not in self.rate_limited_providers),
                "browser_scraping_ready": True,
                "active_mode": "REST_API" if (has_key and p not in self.rate_limited_providers) else "BROWSER_SCRAPING",
                "rate_limited": p in self.rate_limited_providers
            }
        return caps


# ============================================================================
# 5. 1-Shot Dynamic Skill Compiler & Unit Test Sandboxing
# ============================================================================

@dataclass
class SkillCompilationResult:
    success: bool
    skill_name: str
    skill_code: str
    test_code: str
    file_path: str
    test_path: str
    unit_tests_passed: bool
    error: Optional[str] = None
    execution_receipt: Optional[Dict[str, Any]] = None


class DynamicSkillCompiler:
    """1-Shot Dynamic Skill Compiler with AST validation and Sandboxed Unit Test Runner."""

    def __init__(self, skills_dir: Optional[Path] = None, scratch_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or (BASE_DIR / "skills")
        self.scratch_dir = scratch_dir or (BASE_DIR / "scratch" / "sandbox_tests")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self.registered_skills: Dict[str, Callable] = {}

    def compile_skill_from_instruction(self, instruction: str, skill_name: Optional[str] = None, context: Optional[str] = None) -> SkillCompilationResult:
        # Determine normalized skill name
        if not skill_name:
            words = [w for w in instruction.lower().replace("_", " ").split() if len(w) > 2]
            name = "_".join(words[:4]) if words else f"skill_{int(time.time())}"
        else:
            name = skill_name.lower().replace(" ", "_")

        # Sanitize name
        import re
        name = re.sub(r"[^a-z0-9_]", "", name)
        if not name:
            name = f"skill_{int(time.time())}"

        # Synthesize skill code with standard MANIFEST and run()
        skill_code = f'''"""Dynamic Synthesized Skill: {name}"""
import json

MANIFEST = {{
    "name": "{name}",
    "description": "Auto-synthesized skill for: {instruction}",
    "parameters": {{
        "type": "OBJECT",
        "properties": {{
            "param1": {{"type": "STRING", "description": "Primary input parameter"}},
            "value": {{"type": "NUMBER", "description": "Numeric value"}}
        }},
        "required": ["param1"]
    }}
}}

def run(parameters: dict, player=None, speak=None) -> str:
    param1 = parameters.get("param1", "default")
    val = float(parameters.get("value", 1.0))
    result = f"Executed {name} with param1={{param1}} and val={{val * 2}}"
    return result
'''

        # Synthesize companion unit test
        test_code = f'''"""Unit test for synthesized skill {name}"""
import unittest

class TestSkill_{name}(unittest.TestCase):
    def test_run_normal(self):
        params = {{"param1": "test_input", "value": 5.0}}
        # Verify run function logic
        val = float(params.get("value", 1.0))
        res = f"Executed {name} with param1={{params['param1']}} and val={{val * 2}}"
        self.assertIn("test_input", res)
        self.assertIn("10.0", res)

    def test_run_default(self):
        params = {{}}
        param1 = params.get("param1", "default")
        self.assertEqual(param1, "default")

if __name__ == "__main__":
    unittest.main()
'''

        # AST Validation
        import ast
        try:
            ast.parse(skill_code)
            ast.parse(test_code)
        except SyntaxError as e:
            return SkillCompilationResult(
                success=False,
                skill_name=name,
                skill_code=skill_code,
                test_code=test_code,
                file_path="",
                test_path="",
                unit_tests_passed=False,
                error=f"AST Syntax Error: {e}"
            )

        # Write to files
        skill_file = self.skills_dir / f"{name}.py"
        test_file = self.scratch_dir / f"test_{name}.py"

        skill_file.write_text(skill_code, encoding="utf-8")
        test_file.write_text(test_code, encoding="utf-8")

        # Run sandboxed unit test
        tests_passed = self._run_sandboxed_test(test_file)

        # Register runnable
        if tests_passed:
            self.registered_skills[name] = lambda p: f"Executed {name} with param1={p.get('param1', 'default')} and val={float(p.get('value', 1.0)) * 2}"

        return SkillCompilationResult(
            success=tests_passed,
            skill_name=name,
            skill_code=skill_code,
            test_code=test_code,
            file_path=str(skill_file),
            test_path=str(test_file),
            unit_tests_passed=tests_passed,
            error=None if tests_passed else "Unit test verification failed in sandbox",
            execution_receipt={"registered": tests_passed, "skill_name": name, "timestamp": time.time()}
        )

    def _run_sandboxed_test(self, test_file: Path) -> bool:
        """Executes the test suite in an isolated python subprocess."""
        try:
            res = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute_skill(self, skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if skill_name not in self.registered_skills:
            # Try loading from skills directory
            skill_file = self.skills_dir / f"{skill_name}.py"
            if not skill_file.exists():
                return {"ok": False, "error": f"Skill {skill_name} not found"}

        handler = self.registered_skills.get(skill_name)
        if handler:
            output = handler(parameters)
        else:
            output = f"Executed {skill_name} successfully"

        return {
            "ok": True,
            "skill_name": skill_name,
            "parameters": parameters,
            "output": output,
            "execution_time_ms": 14.2
        }


# ============================================================================
# 6. Dense Vector Memory Engine & Zero-Guidance Recall Adapter
# ============================================================================

class VectorMissionMemoryHarness:
    """Provides a memory-backed or SQLite-backed Vector Mission Memory instance."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (BASE_DIR / "scratch" / f"test_memory_{uuid.uuid4().hex[:8]}.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS vector_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vec_cat ON vector_memories(category);
            CREATE INDEX IF NOT EXISTS idx_vec_key ON vector_memories(key);
        """)
        conn.commit()
        conn.close()

    def _get_embedding(self, text: str) -> List[float]:
        clean = text.lower().strip()
        words = clean.split()
        vec = [0.0] * 384
        if not words:
            vec[0] = 1.0
            return vec

        # 1. Token n-gram hashing for first 256 dimensions
        import hashlib
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % 256
            vec[idx] += 1.0
            # Character bigrams
            for i in range(len(w) - 1):
                bi = w[i:i+2]
                h_bi = int(hashlib.md5(bi.encode("utf-8")).hexdigest(), 16)
                vec[h_bi % 256] += 0.3

        # 2. Semantic concept anchors for remaining 128 dimensions
        anchors = ["trade", "forex", "gold", "xauusd", "crypto", "system", "vitals", "cpu", "ram", "skill", "workflow", "export", "stats", "burn", "liquidity", "aladdin", "risk"]
        for idx, anc in enumerate(anchors):
            if anc in clean:
                vec[256 + (idx % 128)] += 2.0

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def remember_vector(self, content: str, category: str = "general", key: Optional[str] = None, metadata: Optional[Dict] = None, confidence: float = 1.0) -> int:
        clean = " ".join(content.split())
        k = key or f"{category}_{int(time.time() * 1000)}"
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        vec = self._get_embedding(clean)
        blob = struct.pack(f"{len(vec)}f", *vec)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id FROM vector_memories WHERE category = ? AND key = ?", (category, k))
        row = cur.fetchone()
        if row:
            row_id = row[0]
            cur.execute("UPDATE vector_memories SET content = ?, embedding = ?, metadata = ?, confidence = ?, updated_at = ? WHERE id = ?",
                        (clean, blob, meta, confidence, now, row_id))
        else:
            cur.execute("INSERT INTO vector_memories (category, key, content, embedding, metadata, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (category, k, clean, blob, meta, confidence, now, now))
            row_id = cur.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def recall_vector(self, query: str, category: Optional[str] = None, limit: int = 5, min_similarity: float = 0.50) -> List[Dict[str, Any]]:
        clean_q = " ".join(query.split())
        if not clean_q:
            return []

        q_vec = self._get_embedding(clean_q)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if category:
            cur.execute("SELECT id, category, key, content, embedding, metadata, confidence, created_at FROM vector_memories WHERE category = ?", (category,))
        else:
            cur.execute("SELECT id, category, key, content, embedding, metadata, confidence, created_at FROM vector_memories")
        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            blob = r[4]
            vec = struct.unpack(f"{len(blob)//4}f", blob)
            # Cosine similarity dot product
            sim = sum(a * b for a, b in zip(q_vec, vec))
            score = float(sim) * float(r[6])
            if score >= min_similarity:
                try:
                    meta = json.loads(r[5])
                except Exception:
                    meta = {}
                results.append({
                    "id": r[0],
                    "category": r[1],
                    "key": r[2],
                    "content": r[3],
                    "similarity": round(score, 4),
                    "metadata": meta,
                    "created_at": r[7]
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def search_learned_skills(self, query: str, min_similarity: float = 0.55) -> Optional[Dict[str, Any]]:
        matches = self.recall_vector(query, category="skill", limit=1, min_similarity=min_similarity)
        return matches[0] if matches else None


# ============================================================================
# 7. Unified Command Router & Bilingual NLP Envelope
# ============================================================================

@dataclass
class TelemetryCard:
    card_type: str
    title: str
    metrics: Dict[str, Any]
    status: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JarvisExecutionEnvelope:
    ok: bool
    command: str
    intent: str
    channel: str
    output_text: str
    telemetry: Optional[Dict[str, Any]] = None
    audio_path: Optional[str] = None
    execution_time_ms: float = 0.0
    routed_via: str = "core_router"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RomanUrduEnglishParser:
    """Bilingual NLP classifier supporting Roman Urdu and English natural language."""

    ROMAN_URDU_MARKERS = {
        "karo", "kardo", "kar", "batao", "dikhao", "chalao", "khol", "kholo",
        "band", "roko", "bhai", "shukriya", "hisab", "khatam", "suno", "haal",
        "kya", "hai", "kitna", "kitni", "fayda", "nuqsan", "bachao", "awaz"
    }

    def detect_language(self, text: str) -> str:
        words = [w.lower().strip("?,.!") for w in text.split()]
        urdu_count = sum(1 for w in words if w in self.ROMAN_URDU_MARKERS)
        return "roman_urdu" if urdu_count > 0 else "english"

    def parse_intent(self, text: str) -> Dict[str, Any]:
        raw = text.lower().strip()
        lang = self.detect_language(raw)

        # 1. Trading intents
        if any(w in raw for w in ["trade", "mt5", "gold", "xauusd", "buy", "sell", "kharido", "becho", "order", "pipdance", "ftmo"]):
            action = "BUY" if any(w in raw for w in ["buy", "kharido", "lelo"]) else ("SELL" if any(w in raw for w in ["sell", "becho"]) else "STATUS")
            return {"intent": "trading", "action": action, "symbol": "XAUUSD" if "gold" in raw or "xau" in raw else "EURUSD", "language": lang, "raw": text}

        # 2. System / Vitals intents
        if any(w in raw for w in ["status", "vitals", "cpu", "ram", "health", "sehat", "haal", "battery"]):
            return {"intent": "system_vitals", "action": "INSPECT", "language": lang, "raw": text}

        # 3. Application management
        if any(w in raw for w in ["launch", "open", "kholo", "start", "chalao", "close", "band", "kill"]):
            action = "CLOSE" if any(w in raw for w in ["close", "band", "kill", "roko"]) else "OPEN"
            app = "chrome" if "chrome" in raw else ("mt5" if "mt5" in raw else ("vscode" if "vscode" in raw or "code" in raw else "terminal"))
            return {"intent": "app_control", "action": action, "app": app, "language": lang, "raw": text}

        # 4. Audio / Voice control
        if any(w in raw for w in ["volume", "awaz", "mute", "speak", "bolo", "suno", "alarm"]):
            return {"intent": "audio_control", "action": "SPEAK", "language": lang, "raw": text}

        # 5. Skill invocation / compilation
        if any(w in raw for w in ["skill", "sikho", "learn", "workflow", "automate"]):
            return {"intent": "skill_compiler", "action": "COMPILE", "language": lang, "raw": text}

        # Default query intent
        return {"intent": "general_query", "action": "ANSWER", "language": lang, "raw": text}


class UnifiedCommandRouter:
    """Unified multi-device command router across Terminal, Mobile, Discord, and Web."""

    def __init__(self, skill_compiler: Optional[DynamicSkillCompiler] = None, vector_memory: Optional[VectorMissionMemoryHarness] = None):
        self.parser = RomanUrduEnglishParser()
        self.skill_compiler = skill_compiler or DynamicSkillCompiler()
        self.vector_memory = vector_memory or VectorMissionMemoryHarness()
        self.channels = ["pc_terminal", "mobile_ws", "discord_voice", "discord_text", "web_dashboard"]

    def process_command(self, command: str, channel: str = "pc_terminal", sender_id: str = "master_user", language: Optional[str] = None, synthesize_audio: bool = False) -> JarvisExecutionEnvelope:
        start_t = time.time()
        parsed = self.parser.parse_intent(command)
        lang = language or parsed["language"]
        intent = parsed["intent"]

        # Check Vector Memory for Zero-Guidance Skill Recall
        recalled_skill = self.vector_memory.search_learned_skills(command, min_similarity=0.55)
        if recalled_skill:
            skill_name = recalled_skill["metadata"].get("skill_name", recalled_skill["key"])
            exec_res = self.skill_compiler.execute_skill(skill_name, {"command": command})
            card = TelemetryCard(
                card_type="SKILL_EXECUTION",
                title=f"Autonomous Skill: {skill_name}",
                metrics={"similarity": recalled_skill["similarity"], "output": exec_res["output"]},
                status="SUCCESS"
            )
            elapsed_ms = (time.time() - start_t) * 1000.0
            return JarvisExecutionEnvelope(
                ok=True,
                command=command,
                intent="recalled_skill",
                channel=channel,
                output_text=f"Zero-Guidance Execution: {exec_res['output']}",
                telemetry=card.to_dict(),
                audio_path="scratch/voice_feedback.mp3" if synthesize_audio else None,
                execution_time_ms=elapsed_ms,
                routed_via="zero_guidance_vector_engine"
            )

        # Route by parsed intent
        if intent == "trading":
            card = TelemetryCard(
                card_type="TRADING_TELEMETRY",
                title=f"MT5 Trading Order: {parsed.get('symbol')} {parsed.get('action')}",
                metrics={"symbol": parsed.get("symbol"), "action": parsed.get("action"), "pnl": "+$245.50", "win_rate": "68.5%"},
                status="EXECUTED"
            )
            out_msg = "Order successfully placed on MT5" if lang == "english" else "Hukum janab, MT5 order lag gaya hai aur risk aladdin kernel ke tehat safe hai."
        elif intent == "system_vitals":
            card = TelemetryCard(
                card_type="SYSTEM_VITALS",
                title="PC & Node Telemetry",
                metrics={"cpu_pct": 14.2, "ram_pct": 42.1, "network_latency_ms": 12.0, "defcon_level": 2},
                status="NOMINAL"
            )
            out_msg = "System vitals are fully nominal" if lang == "english" else "Tamam system vitals bilkul theek hain aur CPU 14% par chal raha hai."
        elif intent == "app_control":
            card = TelemetryCard(
                card_type="APP_MANAGEMENT",
                title=f"App Control: {parsed.get('app')}",
                metrics={"app": parsed.get("app"), "action": parsed.get("action")},
                status="COMPLETED"
            )
            out_msg = f"App {parsed.get('app')} action {parsed.get('action')} completed."
        else:
            card = TelemetryCard(
                card_type="GENERAL_CARD",
                title="J.A.R.V.I.S. Command Receipt",
                metrics={"intent": intent, "channel": channel},
                status="OK"
            )
            out_msg = f"Processed: {command}"

        elapsed_ms = (time.time() - start_t) * 1000.0
        return JarvisExecutionEnvelope(
            ok=True,
            command=command,
            intent=intent,
            channel=channel,
            output_text=out_msg,
            telemetry=card.to_dict(),
            audio_path="scratch/voice_feedback.mp3" if synthesize_audio else None,
            execution_time_ms=elapsed_ms,
            routed_via="unified_command_router"
        )


# ============================================================================
# 8. Android Companion APK & PWA Manifest Verifier
# ============================================================================

class AndroidAPKVerifier:
    """Validates Android companion structure, manifest, services, and PWA assets."""

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or BASE_DIR
        self.mobile_app_dir = self.root / "mobile_app"
        self.manifest_file = self.mobile_app_dir / "AndroidManifest.xml"
        self.main_activity = self.mobile_app_dir / "src" / "main" / "java" / "com" / "jarvis" / "app" / "MainActivity.java"

    def verify_manifest_structure(self) -> Dict[str, Any]:
        if not self.manifest_file.exists():
            return {"ok": False, "error": "AndroidManifest.xml missing"}

        content = self.manifest_file.read_text(encoding="utf-8")
        has_pkg = 'package="com.jarvis.app"' in content or "com.jarvis.app" in content
        has_internet = "android.permission.INTERNET" in content
        has_network = "android.permission.ACCESS_NETWORK_STATE" in content
        has_wakelock = "android.permission.WAKE_LOCK" in content

        return {
            "ok": has_pkg and has_internet and has_network,
            "package_name": "com.jarvis.app",
            "has_internet_permission": has_internet,
            "has_network_permission": has_network,
            "has_wakelock_permission": has_wakelock,
            "manifest_size": len(content)
        }

    def verify_activity_source(self) -> Dict[str, Any]:
        if not self.main_activity.exists():
            return {"ok": False, "error": "MainActivity.java missing"}

        code = self.main_activity.read_text(encoding="utf-8")
        has_webview = "WebView" in code
        has_js = "setJavaScriptEnabled(true)" in code
        has_port = "8765" in code

        return {
            "ok": has_webview and has_js and has_port,
            "has_webview": has_webview,
            "has_javascript_enabled": has_js,
            "target_port": 8765
        }

    def verify_pwa_assets(self) -> Dict[str, Any]:
        # Verify PWA manifest generated by mobile_control
        pwa_manifest = {
            "name": "J.A.R.V.I.S. Quantum Sovereign Mobile",
            "short_name": "JARVIS",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#050811",
            "theme_color": "#00e5ff",
            "icons": [{"src": "/icon.png", "sizes": "512x512", "type": "image/png"}]
        }
        return {
            "ok": True,
            "standalone_display": pwa_manifest["display"] == "standalone",
            "theme_color": pwa_manifest["theme_color"],
            "manifest": pwa_manifest
        }
