"""
perception/browser_engine.py — Headless/Headed Playwright Automation Engine
============================================================================
Allows J.A.R.V.I.S. to read live webpages, check prop-firm rules, and inspect
market documentation programmatically without brittle manual pixel-clicking.
"""

from typing import Dict, Any, Optional

try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False

class BrowserEngine:
    def __init__(self):
        pass

    def fetch_page_text(self, url: str, timeout_ms: int = 10000) -> Dict[str, Any]:
        """Loads a web page headlessly and extracts structured text and title."""
        if not _HAS_PLAYWRIGHT:
            return {"url": url, "error": "Playwright not available in environment"}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                title = page.title()
                content = page.inner_text("body")[:4000]
                browser.close()
                return {
                    "url": url,
                    "title": title,
                    "content": content,
                    "status": "SUCCESS"
                }
        except Exception as e:
            return {"url": url, "error": str(e), "status": "FAILED"}

_browser_engine = None
def get_browser_engine() -> BrowserEngine:
    global _browser_engine
    if _browser_engine is None:
        _browser_engine = BrowserEngine()
    return _browser_engine

if __name__ == "__main__":
    b = get_browser_engine()
    print("Browser Engine Initialized cleanly.")
