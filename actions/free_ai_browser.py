"""
actions/free_ai_browser.py — Zero-Cost AI Assistant with Human CAPTCHA Resolver
================================================================================
Enables J.A.R.V.I.S. to:
1. Provide instant free AI intelligence using local sovereign LLMs (Qwen2.5 / Ollama :11434, Odysseus :7000)
   and browser-based Web LLMs without any paid API dependencies.
2. If browser navigation encounters Cloudflare Turnstile, anti-bot checks, or CAPTCHAs:
   - Brings Chrome/browser window to the front on the PC screen.
   - Alerts Master Muhammad Qureshi with audio chime and top-most J.A.R.V.I.S. assistance modal.
   - Resumes data extraction once resolved.
3. Completely free, robust, and lightning-fast.
================================================================================
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("FreeAIBrowser")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))


def query_free_ai(prompt: str, portal: str = "local", timeout_seconds: int = 30) -> Dict[str, Any]:
    """
    Executes a free AI query using zero-cost sovereign and browser channels.
    """
    t0 = time.time()
    clean_prompt = prompt.strip()
    logger.info("Executing free AI query: '%s' (channel: %s)", clean_prompt[:60], portal)

    # Priority 1 (If browser or ChatGPT requested): Autonomous Web Navigator with Human CAPTCHA Assist
    if portal.lower() in {"browser", "chatgpt", "claude", "deepseek"}:
        target_portal = "chatgpt" if portal.lower() in {"browser", "chatgpt"} else portal.lower()
        try:
            from perception.web_navigator import get_web_navigator
            nav = get_web_navigator()
            res = nav.query_web_llm(provider=target_portal, prompt=clean_prompt, timeout_seconds=timeout_seconds)

            if res.get("ok") and res.get("response_text"):
                elapsed = round(time.time() - t0, 2)
                return {
                    "ok": True,
                    "provider": f"Browser Web LLM ({target_portal.upper()})",
                    "answer": res.get("response_text", ""),
                    "code_blocks": res.get("code_blocks", []),
                    "execution_time_s": elapsed,
                    "captcha_intervened": False
                }
            elif "captcha" in str(res).lower() or "challenge" in str(res).lower() or "cloudflare" in str(res).lower():
                from actions.human_intervention import request_human_intervention
                dialog_res = request_human_intervention(
                    task_name=f"Web AI Query ({target_portal.upper()})",
                    reason=f"Cloudflare Turnstile or security challenge on {target_portal}.",
                    window_title_pattern="Chrome",
                    timeout_seconds=90
                )
                if dialog_res.get("resolved"):
                    retry_res = nav.query_web_llm(provider=target_portal, prompt=clean_prompt)
                    if retry_res.get("response_text"):
                        return {
                            "ok": True,
                            "provider": f"Browser Web LLM ({target_portal.upper()}) [Post-Verification]",
                            "answer": retry_res.get("response_text", ""),
                            "execution_time_s": round(time.time() - t0, 2),
                            "captcha_intervened": True
                        }
        except Exception as e:
            logger.info("Browser web navigator unavailable or timed out: %s — falling back to sovereign local LLM", e)

    # Priority 2: Sovereign Local Ollama Node (Qwen 2.5) — Fast, Private, Zero-Cost
    try:
        import requests
        resp = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "qwen2.5:0.5b", "prompt": clean_prompt, "stream": False},
            timeout=10
        )
        if resp.status_code == 200:
            local_ans = resp.json().get("response", "").strip()
            if local_ans and len(local_ans) > 5:
                elapsed = round(time.time() - t0, 2)
                return {
                    "ok": True,
                    "provider": "Sovereign Local Ollama (Qwen 2.5:0.5b Offline)",
                    "answer": local_ans,
                    "execution_time_s": elapsed,
                    "captcha_intervened": False
                }
    except Exception as e:
        logger.debug("Local Ollama query notice: %s", e)

    # Priority 3: Odysseus AI Sovereign Engine (Port 7000)
    try:
        import requests
        resp = requests.post(
            "http://127.0.0.1:7000/api/chat",
            json={"prompt": clean_prompt},
            timeout=8
        )
        if resp.status_code == 200:
            body = resp.json()
            ans = body.get("response") or body.get("text") or body.get("output") or ""
            if ans and len(ans.strip()) > 5:
                elapsed = round(time.time() - t0, 2)
                return {
                    "ok": True,
                    "provider": "Odysseus AI Sovereign Engine (:7000)",
                    "answer": ans.strip(),
                    "execution_time_s": elapsed,
                    "captcha_intervened": False
                }
    except Exception as e:
        logger.debug("Odysseus engine query notice: %s", e)

    # Priority 4: Browser Web Navigator as Fallback if not already attempted
    if portal.lower() not in {"browser", "chatgpt", "claude", "deepseek"}:
        try:
            from perception.web_navigator import get_web_navigator
            nav = get_web_navigator()
            res = nav.query_web_llm(provider="chatgpt", prompt=clean_prompt, timeout_seconds=timeout_seconds)
            if res.get("ok") and res.get("response_text"):
                elapsed = round(time.time() - t0, 2)
                return {
                    "ok": True,
                    "provider": "Browser Web LLM (CHATGPT)",
                    "answer": res.get("response_text", ""),
                    "code_blocks": res.get("code_blocks", []),
                    "execution_time_s": elapsed,
                    "captcha_intervened": False
                }
        except Exception as e:
            logger.debug("Fallback web navigator notice: %s", e)

    # 4. Fallback: Unified AI Engine
    try:
        from ai_engine import query_ai
        ans = query_ai(clean_prompt)
        if ans and len(ans) > 5:
            return {
                "ok": True,
                "provider": "J.A.R.V.I.S. Core Cognitive Engine",
                "answer": ans,
                "execution_time_s": round(time.time() - t0, 2),
                "captcha_intervened": False
            }
    except Exception:
        pass

    return {
        "ok": False,
        "provider": "Free AI Hub",
        "answer": "Sir, free AI channels se rabta nahi ho saka. Barah-e-karam apna network ya local Ollama node check farmayein.",
        "execution_time_s": round(time.time() - t0, 2),
        "captcha_intervened": False
    }


if __name__ == "__main__":
    res = query_free_ai("What is the capital of France?")
    print("AI Response:", res["answer"], f"({res['provider']} in {res['execution_time_s']}s)")
