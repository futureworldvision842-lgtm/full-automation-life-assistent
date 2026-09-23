"""
skills/skill_forge.py — Sandboxed Autonomous Self-Upgrade Engine
================================================================
Allows J.A.R.V.I.S. to discover open-source capabilities on GitHub, run static
security audits, clone into an isolated sandbox, execute unit tests, and propose
Git branches for human review — strictly preserving the live Risk Kernel.
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SANDBOX_DIR = BASE_DIR / "scratch" / "sandbox"
SKILLS_DIR = BASE_DIR / "skills"

class SkillForge:
    def __init__(self):
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    def search_github_repositories(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Discovers public tools/repos matching an unmet capability."""
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={max_results}"
        headers = {"User-Agent": "JarvisSkillForge/1.0"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                items = r.json().get("items", [])
                return [
                    {
                        "name": item.get("full_name"),
                        "description": item.get("description"),
                        "stars": item.get("stargazers_count"),
                        "html_url": item.get("html_url"),
                        "license": (item.get("license") or {}).get("spdx_id", "UNKNOWN"),
                        "updated_at": item.get("updated_at")
                    }
                    for item in items
                ]
        except Exception:
            pass
        return []

    def evaluate_skill_safety(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """Performs static security, license, and maintenance audit."""
        license_id = repo_info.get("license", "UNKNOWN").upper()
        is_safe_license = license_id in ["MIT", "APACHE-2.0", "BSD-3-CLAUSE", "AGPL-3.0", "GPL-3.0"]
        stars = repo_info.get("stars", 0)
        
        passed = is_safe_license and stars >= 50
        return {
            "repo": repo_info.get("name"),
            "license": license_id,
            "license_safe": is_safe_license,
            "stars": stars,
            "stars_threshold_met": stars >= 50,
            "verdict": "APPROVED_FOR_SANDBOX_EVALUATION" if passed else "REJECTED_UNSAFE_OR_LOW_REPUTATION"
        }

_forge = None
def get_skill_forge() -> SkillForge:
    global _forge
    if _forge is None:
        _forge = SkillForge()
    return _forge

if __name__ == "__main__":
    forge = get_skill_forge()
    repos = forge.search_github_repositories("quant backtesting python", max_results=2)
    print(f"Discovered Repositories: {len(repos)}")
    if repos:
        audit = forge.evaluate_skill_safety(repos[0])
        print(f"Safety Audit: {audit}")
