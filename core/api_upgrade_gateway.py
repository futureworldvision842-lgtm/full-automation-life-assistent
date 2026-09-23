"""
core/api_upgrade_gateway.py — Dynamic REST API ↔ Browser Scraping Upgrade Gateway
==================================================================================
Provides transparent bidirectional hot-swapping between:
1. High-speed Direct REST APIs (OpenAI, Anthropic, DeepSeek, Google AI, GitHub).
2. Autonomous Web Scraping Engine (perception/web_navigator.py).
3. Instant hot-swapping when keys are configured in config/api_keys.json or .env.
4. Automatic fallback to browser scraping on rate limits (HTTP 429), quota errors (HTTP 402),
   auth errors (HTTP 401/403), or network outages.
==================================================================================
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Base paths
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _BASE_DIR / "config" / "api_keys.json"

logger = logging.getLogger("jarvis.core.api_upgrade_gateway")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Import WebNavigator for browser scraping fallback
try:
    from perception.web_navigator import extract_code_blocks, extract_reasoning_trace, get_web_navigator
    _HAS_NAVIGATOR = True
except ImportError:
    try:
        sys.path.insert(0, str(_BASE_DIR))
        from perception.web_navigator import extract_code_blocks, extract_reasoning_trace, get_web_navigator
        _HAS_NAVIGATOR = True
    except ImportError:
        _HAS_NAVIGATOR = False


# ============================================================================
# Provider Default Models & Endpoints
# ============================================================================

PROVIDER_DEFAULTS = {
    "openai": {
        "key_names": ["openai_api_key", "OPENAI_API_KEY"],
        "default_model": "gpt-4o",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "browser_url": "https://chatgpt.com",
        "navigator_provider": "chatgpt"
    },
    "anthropic": {
        "key_names": ["anthropic_api_key", "ANTHROPIC_API_KEY"],
        "default_model": "claude-3-5-sonnet-20241022",
        "api_url": "https://api.anthropic.com/v1/messages",
        "browser_url": "https://claude.ai",
        "navigator_provider": "claude"
    },
    "deepseek": {
        "key_names": ["deepseek_api_key", "DEEPSEEK_API_KEY"],
        "default_model": "deepseek-chat",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "browser_url": "https://chat.deepseek.com",
        "navigator_provider": "deepseek"
    },
    "google": {
        "key_names": ["gemini_api_key", "GEMINI_API_KEY", "google_api_key", "GOOGLE_API_KEY"],
        "default_model": "gemini-2.0-flash",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "browser_url": "https://aistudio.google.com",
        "navigator_provider": "google_ai"
    },
    "gemini": {
        "key_names": ["gemini_api_key", "GEMINI_API_KEY", "google_api_key", "GOOGLE_API_KEY"],
        "default_model": "gemini-2.0-flash",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "browser_url": "https://aistudio.google.com",
        "navigator_provider": "google_ai"
    },
    "github": {
        "key_names": ["github_token", "github_pat", "GITHUB_TOKEN", "GITHUB_PAT"],
        "default_model": "github-rest-v3",
        "api_url": "https://api.github.com/search/repositories",
        "browser_url": "https://github.com",
        "navigator_provider": "github"
    },
    "stackoverflow": {
        "key_names": ["stackoverflow_api_key", "stackexchange_api_key"],
        "default_model": "stackexchange-v2.3",
        "api_url": "https://api.stackexchange.com/2.3/search/advanced",
        "browser_url": "https://stackoverflow.com",
        "navigator_provider": "stackoverflow"
    }
}


# ============================================================================
# API Upgrade Gateway Class
# ============================================================================

class APIUpgradeGateway:
    """
    Transparent dynamic router between direct REST APIs and autonomous browser scraping.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path or _CONFIG_PATH)
        self._cached_config: Dict[str, Any] = {}
        self._config_mtime: float = 0.0
        self._mock_responses: Dict[str, Any] = {}

    def set_mock_response(self, key: str, response: Dict[str, Any]):
        """Injects mock response for unit tests / offline verification."""
        self._mock_responses[key.lower()] = response

    def clear_mock_responses(self):
        """Clears all mock responses."""
        self._mock_responses.clear()

    # ------------------------------------------------------------------------
    # Dynamic Configuration & Key Introspection
    # ------------------------------------------------------------------------

    def invalidate_cache(self):
        """Forces cache invalidation."""
        self._config_mtime = 0.0
        self._cached_config = {}

    def reload_config(self) -> Dict[str, Any]:
        """Explicitly reloads configuration from disk."""
        self.invalidate_cache()
        return self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads and caches API keys with mtime check for hot-reloading."""
        try:
            if self.config_path.exists():
                mtime = self.config_path.stat().st_mtime
                if mtime != self._config_mtime:
                    text = self.config_path.read_text(encoding="utf-8")
                    self._cached_config = json.loads(text) if text.strip() else {}
                    self._config_mtime = mtime
            else:
                self._cached_config = {}
        except Exception as e:
            logger.warning(f"[APIGateway] Failed to reload config: {e}")
            self._cached_config = {}
        return self._cached_config

    def get_api_key(self, provider: str) -> Tuple[Optional[str], str]:
        """
        Retrieves API key for a provider from config or os.environ.
        Returns: (api_key_or_None, key_source)
        """
        cfg = self._load_config()
        p_info = PROVIDER_DEFAULTS.get(provider.lower().strip(), {})
        key_names = p_info.get("key_names", [f"{provider.lower()}_api_key", f"{provider.upper()}_API_KEY"])

        # 1. Check config file
        for kn in key_names:
            val = cfg.get(kn) or cfg.get(kn.lower()) or cfg.get(kn.upper())
            if val and isinstance(val, str) and val.strip() and not val.startswith("your_"):
                return val.strip(), "config/api_keys.json"

        # 2. Check environment variables
        for kn in key_names:
            val = os.environ.get(kn) or os.environ.get(kn.upper()) or os.environ.get(kn.lower())
            if val and isinstance(val, str) and val.strip() and not val.startswith("your_"):
                return val.strip(), "env"

        return None, "none"

    def set_provider_key(self, provider: str, api_key: str, persist: bool = True) -> bool:
        """
        Updates and persists an API key dynamically without restarting the application.
        """
        provider_clean = provider.lower().strip()
        p_info = PROVIDER_DEFAULTS.get(provider_clean, {})
        key_names = p_info.get("key_names", [f"{provider_clean}_api_key"])
        primary_key = key_names[0]

        # Set environment variable
        os.environ[primary_key.upper()] = api_key

        if persist:
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                cfg = self._load_config()
                cfg[primary_key] = api_key
                self.config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                self._config_mtime = self.config_path.stat().st_mtime
                self._cached_config = cfg
                logger.info(f"[APIGateway] Persisted API key for '{provider_clean}' to {self.config_path}")
                return True
            except Exception as e:
                logger.error(f"[APIGateway] Failed to persist key: {e}")
                return False
        return True

    def get_provider_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns real-time capability status of all supported providers:
        {
            "openai": {"mode": "REST_API" | "BROWSER_SCRAPING", "key_configured": bool, ...},
            ...
        }
        """
        capabilities = {}
        for prov, info in PROVIDER_DEFAULTS.items():
            key, source = self.get_api_key(prov)
            has_key = bool(key is not None and len(key) > 4)
            mode = "REST_API" if has_key else "BROWSER_SCRAPING"
            capabilities[prov] = {
                "mode": mode,
                "key_configured": has_key,
                "key_source": source,
                "default_model": info.get("default_model", "unknown"),
                "browser_url": info.get("browser_url", "")
            }
        return capabilities

    # ------------------------------------------------------------------------
    # REST API Dispatchers
    # ------------------------------------------------------------------------

    def _call_openai_rest(
        self,
        api_key: str,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Dispatches request to OpenAI REST API."""
        target_model = model or PROVIDER_DEFAULTS["openai"]["default_model"]
        url = PROVIDER_DEFAULTS["openai"]["api_url"]
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.3
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        if resp.status_code != 200:
            return {"status_code": resp.status_code, "error": resp.text}

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"status_code": 200, "content": content, "model": target_model}

    def _call_anthropic_rest(
        self,
        api_key: str,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Dispatches request to Anthropic REST API."""
        target_model = model or PROVIDER_DEFAULTS["anthropic"]["default_model"]
        url = PROVIDER_DEFAULTS["anthropic"]["api_url"]

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        if resp.status_code != 200:
            return {"status_code": resp.status_code, "error": resp.text}

        data = resp.json()
        content = data["content"][0]["text"]
        return {"status_code": 200, "content": content, "model": target_model}

    def _call_deepseek_rest(
        self,
        api_key: str,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Dispatches request to DeepSeek REST API."""
        target_model = model or PROVIDER_DEFAULTS["deepseek"]["default_model"]
        url = PROVIDER_DEFAULTS["deepseek"]["api_url"]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.3
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        if resp.status_code != 200:
            return {"status_code": resp.status_code, "error": resp.text}

        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", None)
        return {"status_code": 200, "content": content, "reasoning": reasoning, "model": target_model}

    def _call_google_rest(
        self,
        api_key: str,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Dispatches request to Google Gemini REST API."""
        target_model = model or PROVIDER_DEFAULTS["google"]["default_model"]
        url_template = PROVIDER_DEFAULTS["google"]["api_url"]
        url = f"{url_template.format(model=target_model)}?key={api_key}"

        full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }]
        }
        headers = {"Content-Type": "application/json"}

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        if resp.status_code != 200:
            return {"status_code": resp.status_code, "error": resp.text}

        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"status_code": 200, "content": content, "model": target_model}

    def _call_github_rest(
        self,
        api_key: str,
        query: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Dispatches request to GitHub REST API."""
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page=5"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "JARVIS-Sovereign-Gateway/2.0"
        }

        resp = requests.get(url, headers=headers, timeout=timeout_seconds)
        if resp.status_code not in (200, 201):
            return {"status_code": resp.status_code, "error": resp.text}

        data = resp.json()
        items = data.get("items", [])
        content_lines = [f"Found {len(items)} GitHub repositories for query '{query}':"]
        for it in items:
            name = it.get("full_name")
            desc = it.get("description", "")
            stars = it.get("stargazers_count", 0)
            url_repo = it.get("html_url")
            content_lines.append(f"• {name} (⭐ {stars}): {desc}\n  URL: {url_repo}")

        content = "\n\n".join(content_lines)
        return {"status_code": 200, "content": content, "model": "github-rest-v3"}

    # ------------------------------------------------------------------------
    # Dynamic Query Router
    # ------------------------------------------------------------------------

    def route_query(
        self,
        provider: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        prefer_browser: bool = False,
        model: Optional[str] = None,
        timeout_seconds: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """
        1. Checks if valid API key is present in config/api_keys.json or env.
        2. If key exists & not prefer_browser: dispatches high-speed REST API request.
        3. If key missing, invalid, or rate-limited (HTTP 429/402): transparently delegates
           to WebNavigator autonomous browser scraping.
        4. Returns unified standard response format.
        """
        provider_clean = provider.lower().strip()
        start_time = time.time()

        # Check mock overrides first
        mock_key = f"route:{provider_clean}"
        if mock_key in self._mock_responses:
            mock_res = dict(self._mock_responses[mock_key])
            mock_res["provider"] = provider_clean
            mock_res["duration_ms"] = (time.time() - start_time) * 1000
            return mock_res

        api_key, key_source = self.get_api_key(provider_clean)
        p_info = PROVIDER_DEFAULTS.get(provider_clean, {})
        nav_provider = p_info.get("navigator_provider", provider_clean)

        # Mode A: Direct REST API (if key present and prefer_browser is False)
        if api_key and not prefer_browser:
            logger.info(f"[APIGateway] Routing query to direct REST API for '{provider_clean}' (key from {key_source})")
            rest_result: Optional[Dict[str, Any]] = None
            try:
                if provider_clean == "openai":
                    rest_result = self._call_openai_rest(api_key, prompt, system_prompt, model, timeout_seconds)
                elif provider_clean == "anthropic":
                    rest_result = self._call_anthropic_rest(api_key, prompt, system_prompt, model, timeout_seconds)
                elif provider_clean == "deepseek":
                    rest_result = self._call_deepseek_rest(api_key, prompt, system_prompt, model, timeout_seconds)
                elif provider_clean in ("google", "gemini"):
                    rest_result = self._call_google_rest(api_key, prompt, system_prompt, model, timeout_seconds)
                elif provider_clean == "github":
                    rest_result = self._call_github_rest(api_key, prompt, timeout_seconds)

            except Exception as e:
                logger.warning(f"[APIGateway] REST API connection exception for '{provider_clean}': {e}")
                rest_result = {"status_code": 500, "error": str(e)}

            if rest_result and rest_result.get("status_code") == 200:
                raw_content = rest_result.get("content", "")
                reasoning = rest_result.get("reasoning", None)
                if not reasoning:
                    reasoning, clean_content = extract_reasoning_trace(raw_content)
                else:
                    clean_content = raw_content

                code_blocks = extract_code_blocks(clean_content)

                return {
                    "ok": True,
                    "provider": provider_clean,
                    "transport": "REST_API",
                    "content": clean_content,
                    "code_blocks": code_blocks,
                    "reasoning_trace": reasoning,
                    "model_or_url": rest_result.get("model", "rest-endpoint"),
                    "duration_ms": (time.time() - start_time) * 1000,
                    "fallback_used": False,
                    "error": None
                }

            # If REST API returned rate limit (429), quota error (402), or server error, hot-fallback to browser
            err_code = rest_result.get("status_code", 500) if rest_result else 500
            err_msg = rest_result.get("error", "Unknown error") if rest_result else "No response"
            logger.warning(
                f"[APIGateway] ⚠️ REST API failed (HTTP {err_code}: {err_msg[:100]}). "
                f"Hot-falling back to autonomous browser scraping..."
            )

        # Mode B: Autonomous Browser Scraping (Key missing, prefer_browser=True, or REST failure)
        fallback_flag = bool(api_key and not prefer_browser)
        logger.info(f"[APIGateway] Executing autonomous browser navigation on '{nav_provider}'...")

        navigator = get_web_navigator()
        if provider_clean in ("stackoverflow", "github"):
            # Query technical portal
            portal_res = navigator.query_technical_portal(nav_provider, prompt)
            duration_ms = (time.time() - start_time) * 1000
            
            if portal_res.get("ok"):
                # Compile portal results into clean content
                results = portal_res.get("results", [])
                lines = [f"Autonomous Developer Portal Scraping ({nav_provider.upper()}):"]
                for r in results:
                    t = r.get("title") or r.get("name", "")
                    u = r.get("url", "")
                    b = r.get("body", "")
                    lines.append(f"### {t}\nURL: {u}\n\n{b}")
                compiled_content = "\n\n".join(lines)
                code_blocks = [{"language": "text", "code": s} for s in portal_res.get("code_snippets", [])]
                
                return {
                    "ok": True,
                    "provider": provider_clean,
                    "transport": "BROWSER_SCRAPING",
                    "content": compiled_content,
                    "code_blocks": code_blocks,
                    "reasoning_trace": None,
                    "model_or_url": p_info.get("browser_url", f"https://{provider_clean}.com"),
                    "duration_ms": duration_ms,
                    "fallback_used": fallback_flag,
                    "error": None
                }
            else:
                return {
                    "ok": False,
                    "provider": provider_clean,
                    "transport": "BROWSER_SCRAPING",
                    "content": "",
                    "code_blocks": [],
                    "reasoning_trace": None,
                    "model_or_url": p_info.get("browser_url", ""),
                    "duration_ms": duration_ms,
                    "fallback_used": fallback_flag,
                    "error": portal_res.get("error")
                }
        else:
            # Query Web LLM
            llm_res = navigator.query_web_llm(
                provider=nav_provider,
                prompt=prompt,
                system_instruction=system_prompt,
                timeout_seconds=timeout_seconds
            )
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                "ok": llm_res.get("ok", False),
                "provider": provider_clean,
                "transport": "BROWSER_SCRAPING",
                "content": llm_res.get("response_text", ""),
                "code_blocks": llm_res.get("code_blocks", []),
                "reasoning_trace": llm_res.get("reasoning_trace"),
                "model_or_url": p_info.get("browser_url", f"https://{provider_clean}.com"),
                "duration_ms": duration_ms,
                "fallback_used": fallback_flag,
                "error": llm_res.get("error")
            }


# ============================================================================
# Singleton Accessor
# ============================================================================

_api_gateway: Optional[APIUpgradeGateway] = None

def get_api_gateway() -> APIUpgradeGateway:
    """Returns the singleton APIUpgradeGateway instance."""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIUpgradeGateway()
    return _api_gateway


if __name__ == "__main__":
    gw = get_api_gateway()
    print("Testing APIUpgradeGateway capabilities...")
    caps = gw.get_provider_capabilities()
    for prov, cap in caps.items():
        print(f"• {prov.upper()}: Mode={cap['mode']} | KeyConfigured={cap['key_configured']} ({cap['key_source']})")
    
    # Test StackOverflow routing
    res = gw.route_query("stackoverflow", "python playwright headless")
    print(f"\nRoute result for StackOverflow: ok={res['ok']}, transport={res['transport']}, code_blocks={len(res['code_blocks'])}")
