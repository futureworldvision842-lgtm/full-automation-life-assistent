"""
tests/test_browser_vision.py — Comprehensive Test Suite for Milestone 2
========================================================================
Verifies:
1. Autonomous Web LLM Navigators (ChatGPT, Claude, DeepSeek, Google AI).
2. Developer Portal Scrapers (StackOverflow, GitHub).
3. Persistent browser profiles & cookies in data/browser_profile/.
4. Real-time streaming quiescence detection, reasoning traces, & code extraction.
5. Hybrid 3-tier desktop screen vision engine (UIA, OCR, Multimodal VL fallback).
6. Active window inspection, UI element coordinate locator, & desktop state.
7. Transparent API upgrade gateway hot-swapping and 429 rate-limit fallback.
========================================================================
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Base path setup
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from perception.web_navigator import (
    WebNavigator,
    extract_code_blocks,
    extract_reasoning_trace,
    sanitize_markdown,
    get_web_navigator
)
from perception.vision_engine import (
    ScreenVisionEngine,
    get_vision_engine
)
from core.api_upgrade_gateway import (
    APIUpgradeGateway,
    get_api_gateway
)


# ============================================================================
# 1. Web Navigator Tests
# ============================================================================

class TestWebNavigator(unittest.TestCase):
    """Verifies Playwright Web LLM & Developer Portal autonomous navigation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="jarvis_test_profile_")
        self.navigator = WebNavigator(profile_dir=Path(self.temp_dir), headless=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_code_blocks_multiple_languages(self):
        """Verifies parsing of python, javascript, bash, html, and untagged code blocks."""
        markdown = """
Here is the solution to your problem:

```python
def calculate_pnl(entry, exit_price, lots):
    return (exit_price - entry) * lots * 100
```

And in JavaScript:
```javascript
const calculatePnL = (entry, exit, lots) => (exit - entry) * lots * 100;
```

Run with:
```bash
python main.py --mode=live
```

Unspecified:
```
raw text code block
```
"""
        blocks = extract_code_blocks(markdown)
        self.assertEqual(len(blocks), 4)
        self.assertEqual(blocks[0]["language"], "python")
        self.assertIn("calculate_pnl", blocks[0]["code"])
        self.assertEqual(blocks[1]["language"], "javascript")
        self.assertIn("calculatePnL", blocks[1]["code"])
        self.assertEqual(blocks[2]["language"], "bash")
        self.assertIn("python main.py", blocks[2]["code"])
        self.assertEqual(blocks[3]["language"], "text")
        self.assertIn("raw text code block", blocks[3]["code"])

    def test_extract_reasoning_trace_deepseek_r1(self):
        """Verifies extraction of <think>...</think> tags and Thought Process headers."""
        # Test <think> tags
        deepseek_text = "<think>\nStep 1: Check MT5 risk buffers.\nStep 2: Calculate 1.5x ATR.\n</think>\n\nExecute BUY on XAUUSD at 2650.00."
        reasoning, clean_text = extract_reasoning_trace(deepseek_text)
        self.assertIsNotNone(reasoning)
        self.assertIn("Check MT5 risk buffers", reasoning)
        self.assertEqual(clean_text, "Execute BUY on XAUUSD at 2650.00.")

        # Test header reasoning format
        header_text = "Thinking Process:\n1. Verify Aladdin VaR limits.\n2. Confirm news blackout.\n\nFinal Answer:\nRisk check passed."
        reasoning2, clean_text2 = extract_reasoning_trace(header_text)
        self.assertIsNotNone(reasoning2)
        self.assertIn("Verify Aladdin VaR limits", reasoning2)
        self.assertEqual(clean_text2, "Risk check passed.")

    def test_sanitize_markdown(self):
        """Verifies clean conversion of HTML tags and pre/code blocks."""
        raw_html = "<p>Here is <b>bold</b> text &amp; &lt;code&gt; snippet:</p><pre><code class=\"language-python\">x = 42\nprint(x)</code></pre>"
        cleaned = sanitize_markdown(raw_html)
        self.assertIn("```python", cleaned)
        self.assertIn("x = 42", cleaned)
        self.assertIn("bold text & <code> snippet:", cleaned)

    def test_browser_profile_persistence(self):
        """Verifies persistent cookies and session storage in profile dir."""
        self.assertFalse(self.navigator.has_saved_session())
        
        mock_cookies = [
            {"name": "session_id", "value": "test_token_12345", "domain": "chatgpt.com", "path": "/"}
        ]
        self.navigator.save_session_cookies(mock_cookies)
        self.assertTrue(self.navigator.has_saved_session())
        
        state = self.navigator.load_session_state()
        self.assertIsNotNone(state)
        self.assertEqual(len(state["cookies"]), 1)
        self.assertEqual(state["cookies"][0]["name"], "session_id")
        self.assertEqual(state["cookies"][0]["value"], "test_token_12345")

    def test_quiescence_polling_settles_on_stable_dom(self):
        """Verifies streaming quiescence detection logic."""
        mock_page = MagicMock()
        # Mock stop button disappearing
        mock_page.query_selector.return_value = None
        
        # Mock elements returning text
        mock_elem = MagicMock()
        mock_elem.inner_text.return_value = "Completed streaming response."
        mock_page.query_selector_all.return_value = [mock_elem]

        content = self.navigator._wait_for_quiescence(
            page=mock_page,
            response_selectors=["div.markdown"],
            stop_selectors=["button[aria-label='Stop']"],
            timeout_seconds=5,
            poll_interval=0.1,
            min_stable_seconds=0.2
        )
        self.assertEqual(content, "Completed streaming response.")

    def test_chatgpt_navigator_mock_and_contract(self):
        """Verifies ChatGPT query execution and returned envelope contract."""
        self.navigator.set_mock_response("llm:chatgpt", {
            "ok": True,
            "provider": "chatgpt",
            "response_text": "Here is code:\n```python\nimport sys\nprint('ChatGPT Online')\n```",
            "code_blocks": [{"language": "python", "code": "import sys\nprint('ChatGPT Online')"}],
            "reasoning_trace": None,
            "duration_ms": 250.0,
            "error": None
        })

        res = self.navigator.query_web_llm("chatgpt", "Write a python script")
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "chatgpt")
        self.assertEqual(len(res["code_blocks"]), 1)
        self.assertEqual(res["code_blocks"][0]["language"], "python")
        self.assertIn("ChatGPT Online", res["code_blocks"][0]["code"])

    def test_claude_navigator_mock_and_contract(self):
        """Verifies Claude query execution and contract."""
        self.navigator.set_mock_response("llm:claude", {
            "ok": True,
            "provider": "claude",
            "response_text": "Claude autonomous response.",
            "code_blocks": [],
            "reasoning_trace": None,
            "duration_ms": 300.0,
            "error": None
        })

        res = self.navigator.query_web_llm("claude", "Explain async loops")
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "claude")
        self.assertIn("Claude autonomous response", res["response_text"])

    def test_deepseek_navigator_reasoning_and_code(self):
        """Verifies DeepSeek navigator reasoning trace extraction."""
        self.navigator.set_mock_response("llm:deepseek", {
            "ok": True,
            "provider": "deepseek",
            "response_text": "DeepSeek answer content.",
            "code_blocks": [{"language": "python", "code": "x = 10"}],
            "reasoning_trace": "R1 Thought: Analysed algorithm complexity.",
            "duration_ms": 400.0,
            "error": None
        })

        res = self.navigator.query_web_llm("deepseek", "Solve DP problem")
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "deepseek")
        self.assertEqual(res["reasoning_trace"], "R1 Thought: Analysed algorithm complexity.")

    def test_google_ai_navigator_contract(self):
        """Verifies Google AI Studio / Gemini web navigation contract."""
        self.navigator.set_mock_response("llm:google_ai", {
            "ok": True,
            "provider": "google_ai",
            "response_text": "Google AI synthesized output.",
            "code_blocks": [],
            "reasoning_trace": None,
            "duration_ms": 200.0,
            "error": None
        })

        res = self.navigator.query_web_llm("google_ai", "Generate summary")
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "google_ai")

    def test_stackoverflow_query_and_code_snippets(self):
        """Verifies developer portal query on StackOverflow."""
        self.navigator.set_mock_response("portal:stackoverflow", {
            "ok": True,
            "portal": "stackoverflow",
            "query": "python asyncio loop",
            "results": [
                {
                    "title": "How to run asyncio event loop in Python?",
                    "url": "https://stackoverflow.com/questions/12345",
                    "score": 45,
                    "is_answered": True,
                    "body": "Use `asyncio.run()`.\n```python\nimport asyncio\nasyncio.run(main())\n```",
                    "code_snippets": ["import asyncio\nasyncio.run(main())"]
                }
            ],
            "code_snippets": ["import asyncio\nasyncio.run(main())"],
            "duration_ms": 150.0,
            "error": None
        })

        res = self.navigator.query_technical_portal("stackoverflow", "python asyncio loop")
        self.assertTrue(res["ok"])
        self.assertEqual(res["portal"], "stackoverflow")
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(len(res["code_snippets"]), 1)
        self.assertIn("asyncio.run", res["code_snippets"][0])

    def test_github_query_and_code_snippets(self):
        """Verifies developer portal query on GitHub."""
        self.navigator.set_mock_response("portal:github", {
            "ok": True,
            "portal": "github",
            "query": "fastapi websocket",
            "results": [
                {
                    "name": "tiangolo/fastapi",
                    "url": "https://github.com/tiangolo/fastapi",
                    "description": "FastAPI framework, high performance",
                    "stars": 75000,
                    "language": "Python",
                    "body": "FastAPI framework repo",
                    "code_snippets": ["# tiangolo/fastapi\n# Stars: 75000"]
                }
            ],
            "code_snippets": ["# tiangolo/fastapi\n# Stars: 75000"],
            "duration_ms": 180.0,
            "error": None
        })

        res = self.navigator.query_technical_portal("github", "fastapi websocket")
        self.assertTrue(res["ok"])
        self.assertEqual(res["portal"], "github")
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["name"], "tiangolo/fastapi")

    def test_unsupported_provider_and_portal_errors(self):
        """Verifies clean error handling for invalid providers and portals."""
        res_llm = self.navigator.query_web_llm("unknown_llm", "test prompt")
        self.assertFalse(res_llm["ok"])
        self.assertIn("Unsupported", res_llm["error"])

        res_portal = self.navigator.query_technical_portal("unknown_portal", "test query")
        self.assertFalse(res_portal["ok"])
        self.assertIn("Unsupported", res_portal["error"])


# ============================================================================
# 2. Desktop Screen Vision Engine Tests
# ============================================================================

class TestScreenVisionEngine(unittest.TestCase):
    """Verifies Hybrid 3-Tier Desktop Screen Vision & State Inspection."""

    def setUp(self):
        self.engine = ScreenVisionEngine()

    def test_get_desktop_state_structure(self):
        """Verifies complete desktop state hierarchy and metrics."""
        state = self.engine.get_desktop_state()
        self.assertIn("active_window", state)
        self.assertIn("open_windows", state)
        self.assertIn("screen_resolution", state)
        self.assertIn("virtual_screen", state)
        self.assertIn("timestamp", state)

        active = state["active_window"]
        self.assertIn("title", active)
        self.assertIn("class_name", active)
        self.assertIn("hwnd", active)
        self.assertIn("rect", active)
        self.assertIn("process_id", active)
        self.assertIn("process_name", active)
        self.assertIn("is_maximized", active)

        rect = active["rect"]
        self.assertIn("left", rect)
        self.assertIn("top", rect)
        self.assertIn("right", rect)
        self.assertIn("bottom", rect)
        self.assertIn("width", rect)
        self.assertIn("height", rect)

    def test_screen_metrics_virtual_offsets(self):
        """Verifies virtual multi-monitor metrics retrieval."""
        metrics = self.engine.get_screen_metrics()
        self.assertIn("width", metrics)
        self.assertIn("height", metrics)
        self.assertIn("virtual_left", metrics)
        self.assertIn("virtual_top", metrics)
        self.assertIn("virtual_width", metrics)
        self.assertIn("virtual_height", metrics)
        self.assertGreater(metrics["width"], 0)
        self.assertGreater(metrics["height"], 0)

    def test_tier1_uia_coordinate_locator_mock(self):
        """Verifies Tier 1 Win32 UIA accessibility coordinate resolution."""
        with patch.object(self.engine, "_locate_tier1_uia", return_value=(450, 300)):
            coords = self.engine.locate_ui_element("Submit Button")
            self.assertEqual(coords, (450, 300))

    def test_tier2_ocr_template_coordinate_locator_mock(self):
        """Verifies Tier 2 OCR/template matching when Tier 1 returns None."""
        with patch.object(self.engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=(600, 400)):
            coords = self.engine.locate_ui_element("Chart Order Block")
            self.assertEqual(coords, (600, 400))

    def test_tier3_multimodal_vision_fallback(self):
        """Verifies Tier 3 Multimodal Vision Model coordinate parsing."""
        with patch.object(self.engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=None), \
             patch.object(self.engine, "_locate_tier3_multimodal", return_value=(800, 550)):
            coords = self.engine.locate_ui_element("Complex Ambiguous Pattern")
            self.assertEqual(coords, (800, 550))

    def test_locate_ui_element_priority_order(self):
        """Verifies Tier 1 -> Tier 2 -> Tier 3 -> None fallback chain."""
        # 1. Tier 1 matches
        with patch.object(self.engine, "_locate_tier1_uia", return_value=(100, 100)), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=(200, 200)), \
             patch.object(self.engine, "_locate_tier3_multimodal", return_value=(300, 300)):
            self.assertEqual(self.engine.locate_ui_element("Element"), (100, 100))

        # 2. Tier 1 fails, Tier 2 matches
        with patch.object(self.engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=(200, 200)), \
             patch.object(self.engine, "_locate_tier3_multimodal", return_value=(300, 300)):
            self.assertEqual(self.engine.locate_ui_element("Element"), (200, 200))

        # 3. Tier 1 & 2 fail, Tier 3 matches
        with patch.object(self.engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=None), \
             patch.object(self.engine, "_locate_tier3_multimodal", return_value=(300, 300)):
            self.assertEqual(self.engine.locate_ui_element("Element"), (300, 300))

        # 4. All fail
        with patch.object(self.engine, "_locate_tier1_uia", return_value=None), \
             patch.object(self.engine, "_locate_tier2_ocr", return_value=None), \
             patch.object(self.engine, "_locate_tier3_multimodal", return_value=None):
            self.assertIsNone(self.engine.locate_ui_element("Unfindable Element"))

    def test_analyze_active_window_summary(self):
        """Verifies structured window semantic analysis."""
        analysis = self.engine.analyze_active_window("Inspect status", include_screenshot=False)
        self.assertTrue(analysis["ok"])
        self.assertIn("active_window", analysis)
        self.assertIn("analysis", analysis)
        self.assertIn("controls_count", analysis)
        self.assertIn("duration_ms", analysis)

    def test_mock_element_injection_for_testing(self):
        """Verifies injection of mock coordinates for test automation."""
        self.engine.set_mock_element("test_button", (999, 888))
        coords = self.engine.locate_ui_element("test_button")
        self.assertEqual(coords, (999, 888))
        self.engine.clear_mock_elements()


# ============================================================================
# 3. API Upgrade Gateway Tests
# ============================================================================

class TestAPIUpgradeGateway(unittest.TestCase):
    """Verifies Dynamic REST API ↔ Browser Scraping Gateway & Hot-Swapping."""

    def setUp(self):
        self.temp_config_dir = tempfile.mkdtemp(prefix="jarvis_test_cfg_")
        self.config_file = Path(self.temp_config_dir) / "api_keys.json"
        self.config_file.write_text(json.dumps({
            "gemini_api_key": "test_gemini_key_123",
            "openai_api_key": "",
            "anthropic_api_key": "",
            "deepseek_api_key": "",
            "github_token": ""
        }), encoding="utf-8")

        self.gateway = APIUpgradeGateway(config_path=self.config_file)

    def tearDown(self):
        shutil.rmtree(self.temp_config_dir, ignore_errors=True)

    def test_get_provider_capabilities_introspection(self):
        """Verifies accurate detection of REST_API vs BROWSER_SCRAPING modes."""
        caps = self.gateway.get_provider_capabilities()
        self.assertEqual(caps["google"]["mode"], "REST_API")
        self.assertTrue(caps["google"]["key_configured"])
        self.assertEqual(caps["openai"]["mode"], "BROWSER_SCRAPING")
        self.assertFalse(caps["openai"]["key_configured"])
        self.assertEqual(caps["anthropic"]["mode"], "BROWSER_SCRAPING")
        self.assertEqual(caps["deepseek"]["mode"], "BROWSER_SCRAPING")
        self.assertEqual(caps["github"]["mode"], "BROWSER_SCRAPING")
        self.assertEqual(caps["stackoverflow"]["mode"], "BROWSER_SCRAPING")

    def test_hot_swapping_mode_transition(self):
        """Verifies that updating keys dynamically transitions modes immediately."""
        # Initial: OpenAI is BROWSER_SCRAPING
        caps1 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps1["openai"]["mode"], "BROWSER_SCRAPING")

        # Dynamically set OpenAI key
        self.gateway.set_provider_key("openai", "sk-proj-test-new-openai-key", persist=True)

        # Immediate check without restarts
        caps2 = self.gateway.get_provider_capabilities()
        self.assertEqual(caps2["openai"]["mode"], "REST_API")
        self.assertTrue(caps2["openai"]["key_configured"])

    def test_openai_rest_routing_success(self):
        """Verifies OpenAI direct REST routing on valid response."""
        with patch.object(self.gateway, "get_api_key", return_value=("sk-test-valid-key", "config")), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "OpenAI Solution:\n```python\nimport os\nprint('GPT-4o Online')\n```"
                    }
                }]
            }

            res = self.gateway.route_query("openai", "Write a python test")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "REST_API")
            self.assertFalse(res["fallback_used"])
            self.assertEqual(len(res["code_blocks"]), 1)
            self.assertIn("GPT-4o Online", res["code_blocks"][0]["code"])

    def test_anthropic_rest_routing_success(self):
        """Verifies Anthropic direct REST routing."""
        with patch.object(self.gateway, "get_api_key", return_value=("sk-ant-test-key", "config")), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "content": [{"text": "Anthropic Claude REST response."}]
            }

            res = self.gateway.route_query("anthropic", "Explain quantum state")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "REST_API")
            self.assertFalse(res["fallback_used"])
            self.assertIn("Anthropic Claude REST response", res["content"])

    def test_deepseek_rest_routing_with_reasoning(self):
        """Verifies DeepSeek REST routing and reasoning content extraction."""
        with patch.object(self.gateway, "get_api_key", return_value=("sk-ds-test-key", "config")), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "DeepSeek final answer.",
                        "reasoning_content": "DeepSeek R1 internal deliberation."
                    }
                }]
            }

            res = self.gateway.route_query("deepseek", "Prove mathematical theorem")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "REST_API")
            self.assertEqual(res["reasoning_trace"], "DeepSeek R1 internal deliberation.")
            self.assertEqual(res["content"], "DeepSeek final answer.")

    def test_google_rest_routing_success(self):
        """Verifies Google Gemini REST routing."""
        with patch.object(self.gateway, "get_api_key", return_value=("AIzaSy-test-key", "config")), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Google Gemini 2.0 Flash response."}]
                    }
                }]
            }

            res = self.gateway.route_query("google", "Summarize news")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "REST_API")
            self.assertIn("Google Gemini 2.0 Flash", res["content"])

    def test_rate_limit_429_automatic_browser_fallback(self):
        """
        CRITICAL TEST: Verifies that when a REST API key hits HTTP 429 Rate Limit,
        the gateway automatically hot-falls back to autonomous browser scraping.
        """
        with patch.object(self.gateway, "get_api_key", return_value=("sk-test-rate-limited-key", "config")), \
             patch("requests.post") as mock_post, \
             patch("perception.web_navigator.WebNavigator.query_web_llm") as mock_browser_llm:
            
            # Simulate 429 Rate Limit
            mock_post.return_value.status_code = 429
            mock_post.return_value.text = "Rate limit exceeded (429: Too Many Requests)"

            # Simulate autonomous browser scraping fallback
            mock_browser_llm.return_value = {
                "ok": True,
                "provider": "chatgpt",
                "response_text": "Autonomous Browser Fallback Response after 429",
                "code_blocks": [{"language": "python", "code": "print('Browser Scraping Activated')"}],
                "reasoning_trace": None,
                "duration_ms": 1200.0,
                "error": None
            }

            res = self.gateway.route_query("openai", "Emergency task execution")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "BROWSER_SCRAPING")
            self.assertTrue(res["fallback_used"], "fallback_used must be True when 429 triggered fallback")
            self.assertIn("Autonomous Browser Fallback Response", res["content"])
            self.assertEqual(len(res["code_blocks"]), 1)

    def test_quota_exceeded_402_and_403_fallback(self):
        """Verifies automatic browser fallback on HTTP 402/403 quota errors."""
        with patch.object(self.gateway, "get_api_key", return_value=("sk-test-quota-exhausted", "config")), \
             patch("requests.post") as mock_post, \
             patch("perception.web_navigator.WebNavigator.query_web_llm") as mock_browser_llm:
            
            mock_post.return_value.status_code = 402
            mock_post.return_value.text = "Payment Required: Quota exhausted"

            mock_browser_llm.return_value = {
                "ok": True,
                "provider": "claude",
                "response_text": "Claude Browser response on quota fallback",
                "code_blocks": [],
                "reasoning_trace": None,
                "duration_ms": 900.0,
                "error": None
            }

            res = self.gateway.route_query("anthropic", "Analyze code")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "BROWSER_SCRAPING")
            self.assertTrue(res["fallback_used"])

    def test_prefer_browser_flag_overrides_configured_key(self):
        """Verifies that prefer_browser=True routes to browser scraping directly."""
        with patch.object(self.gateway, "get_api_key", return_value=("sk-valid-key", "config")), \
             patch("requests.post") as mock_post, \
             patch("perception.web_navigator.WebNavigator.query_web_llm") as mock_browser_llm:
            
            mock_browser_llm.return_value = {
                "ok": True,
                "provider": "chatgpt",
                "response_text": "Browser scraping forced by prefer_browser flag.",
                "code_blocks": [],
                "reasoning_trace": None,
                "duration_ms": 800.0,
                "error": None
            }

            res = self.gateway.route_query("openai", "Test query", prefer_browser=True)
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "BROWSER_SCRAPING")
            self.assertFalse(res["fallback_used"])
            # Ensure REST API was never called
            mock_post.assert_not_called()

    def test_developer_portal_routing_and_fallback(self):
        """Verifies developer portal routing through gateway."""
        with patch("perception.web_navigator.WebNavigator.query_technical_portal") as mock_portal:
            mock_portal.return_value = {
                "ok": True,
                "portal": "stackoverflow",
                "query": "python playwright",
                "results": [{"title": "SO Title", "url": "https://so.com/1", "body": "SO answer body"}],
                "code_snippets": ["import playwright"],
                "duration_ms": 150.0,
                "error": None
            }

            res = self.gateway.route_query("stackoverflow", "python playwright")
            self.assertTrue(res["ok"])
            self.assertEqual(res["transport"], "BROWSER_SCRAPING")
            self.assertIn("Autonomous Developer Portal Scraping", res["content"])
            self.assertEqual(len(res["code_blocks"]), 1)


if __name__ == "__main__":
    unittest.main()
