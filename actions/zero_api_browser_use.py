"""
actions/zero_api_browser_use.py — Autonomous Web Agent Powered by browser-use & Local LLMs
==========================================================================================
Enables J.A.R.V.I.S. to:
1. Autonomously browse web portals, search engines, and developer sites without paid APIs.
2. Execute instructions via local Ollama models (Qwen 2.5 / Llama 3.2).
3. Extract structured research, scrape free web LLM completions, and solve coding tasks.
==========================================================================================
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ZeroAPIBrowserUse")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent


async def run_autonomous_browser_task(task_prompt: str, max_steps: int = 10) -> Dict[str, Any]:
    """
    Executes a web browsing task autonomously using browser-use and local Ollama.
    """
    start_t = time.perf_counter()
    logger.info("Starting autonomous browser task: '%s'", task_prompt)

    try:
        from browser_use import Agent
        from langchain_ollama import ChatOllama

        # 1. Connect to local Ollama (100% Free & Zero-API)
        llm = ChatOllama(
            model="qwen2.5:1.5b",
            base_url="http://127.0.0.1:11434",
            temperature=0.1
        )

        agent = Agent(
            task=task_prompt,
            llm=llm,
            use_vision=False
        )

        history = await agent.run(max_steps=max_steps)
        elapsed = (time.perf_counter() - start_t) * 1000.0

        return {
            "ok": True,
            "task": task_prompt,
            "result": str(history.final_result() if hasattr(history, 'final_result') else history),
            "execution_time_ms": round(elapsed, 1),
            "engine": "browser-use + local Ollama (qwen2.5)"
        }

    except Exception as e:
        logger.warning("browser-use local agent notice: %s. Using Playwright fallback...", e)
        # Resilient fallback: Direct Playwright web navigator
        from perception.web_navigator import get_web_navigator
        nav = get_web_navigator()
        res = nav.query_web_llm(provider="chatgpt", prompt=task_prompt)
        elapsed = (time.perf_counter() - start_t) * 1000.0
        content = res.get("response_text") or res.get("content") or ""
        return {
            "ok": bool(content),
            "task": task_prompt,
            "result": content or f"Fallback output: {res}",
            "execution_time_ms": round(elapsed, 1),
            "engine": "Playwright Free Web LLM Bridge"
        }


def execute_browser_task_sync(task_prompt: str, max_steps: int = 10) -> Dict[str, Any]:
    """Synchronous entry point for autonomous browser task execution."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(asyncio.run, run_autonomous_browser_task(task_prompt, max_steps=max_steps))
                return fut.result()
        else:
            return loop.run_until_complete(run_autonomous_browser_task(task_prompt, max_steps=max_steps))
    except Exception:
        return asyncio.run(run_autonomous_browser_task(task_prompt, max_steps=max_steps))
