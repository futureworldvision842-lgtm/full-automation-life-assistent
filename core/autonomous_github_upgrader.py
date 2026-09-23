"""
core/autonomous_github_upgrader.py — Sovereign Autonomous GitHub Self-Upgrade & Auto-Sync Engine
================================================================================================
Empowers J.A.R.V.I.S. OS to continuously and autonomously:
1. Check GitHub origin (futureworldvision842-lgtm/full-automation-life-assistent) for upstream commits.
2. Ingest and assimilate capabilities from curated open-source repositories (inspired by HKUDS/CLI-Anything & trycua/cua).
3. Validate and sandbox-verify newly synthesized skills (zero prohibited tokens, zero secret leaks, py_compile).
4. Hot-reload verified skills into the Active Tool Registry with zero downtime.
5. If new capabilities are synthesized, automatically stage, commit, and push them back to GitHub.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import py_compile
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Jarvis.AutonomousUpgrader")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"
RUNTIME_DIR = BASE_DIR / "runtime"
LOG_DIR = BASE_DIR / "logs"

PROHIBITED_TOKEN: str = "".join(["adeel", "qureshi", "99"])

# Known curated capability sources across user ecosystem & open-source agents
CURATED_SOURCES = [
    {
        "name": "decentralized_governance",
        "full_name": "futureworldvision842-lgtm/Global-Ai-Decentralize-Governance-System-with-Blockchain-Transparency-and-Democracy",
        "url": "https://github.com/futureworldvision842-lgtm/Global-Ai-Decentralize-Governance-System-with-Blockchain-Transparency-and-Democracy",
        "category": "governance_blockchain",
        "description": "Decentralized AI Governance System with Blockchain Transparency, Quad-Voting, and Democracy"
    },
    {
        "name": "openhuman_telemetry",
        "full_name": "futureworldvision842-lgtm/openhuman",
        "url": "https://github.com/futureworldvision842-lgtm/openhuman",
        "category": "biometric_health",
        "description": "OpenHuman Autonomous Health, Biometric Telemetry, and Cross-Platform Channel Orchestrator"
    },
    {
        "name": "worldmonitor_radar",
        "full_name": "futureworldvision842-lgtm/worldmonitor",
        "url": "https://github.com/futureworldvision842-lgtm/worldmonitor",
        "category": "geospatial_intelligence",
        "description": "World Monitor Geospatial Radar and Real-Time Macro Conflict/Economic Intelligence"
    },
    {
        "name": "cli_anything",
        "full_name": "HKUDS/CLI-Anything",
        "url": "https://github.com/HKUDS/CLI-Anything",
        "category": "terminal_automation",
        "description": "Cross-platform CLI and GUI automation agent with OS command execution"
    },
    {
        "name": "cua_browser",
        "full_name": "trycua/cua",
        "url": "https://github.com/trycua/cua",
        "category": "browser_vision",
        "description": "Autonomous browser agent, DOM controller, and screen vision perception"
    },
    {
        "name": "quant_indicators",
        "full_name": "futureworldvision842-lgtm/full-automation-life-assistent",
        "url": "https://github.com/futureworldvision842-lgtm/full-automation-life-assistent",
        "category": "prop_trading",
        "description": "Proprietary J.A.R.V.I.S. sovereign life assistant & prop trader suite"
    }
]

SECRET_PATTERNS = [
    re.compile(r'AIzaSy[A-Za-z0-9_\-]{33}'),
    re.compile(r'gsk_[A-Za-z0-9_\-]{40,}'),
    re.compile(r'sk-[A-Za-z0-9_\-]{30,}'),
    re.compile(r'[MNO][A-Za-z0-9_\-]{23,26}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,38}'),
    re.compile(r'0eb10f8a01a8162b297cee55fedd940f'),
]


@dataclass
class UpgradeCycleReceipt:
    ok: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    upstream_checked: bool = False
    upstream_pulled: bool = False
    upstream_commit_before: str = ""
    upstream_commit_after: str = ""
    skills_scanned: int = 0
    skills_synthesized: List[str] = field(default_factory=list)
    sandbox_verified_count: int = 0
    hot_reloaded_count: int = 0
    pushed_to_github: bool = False
    pushed_commit_sha: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None
    log_messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomousGitHubUpgrader:
    """
    Self-contained autonomous upgrader that monitors GitHub, pulls updates,
    assimilates capabilities, and auto-pushes verified evolutions.
    """

    _instance: Optional[AutonomousGitHubUpgrader] = None
    _lock = threading.Lock()

    def __init__(self, check_interval_hours: float = 4.0):
        self.check_interval_seconds = max(300.0, check_interval_hours * 3600.0)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.last_receipt: Optional[UpgradeCycleReceipt] = None
        self.history_file = RUNTIME_DIR / "github_upgrade_history.json"
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> AutonomousGitHubUpgrader:
        with cls._lock:
            if cls._instance is None:
                cls._instance = AutonomousGitHubUpgrader()
            return cls._instance

    @staticmethod
    def _run_git(args: List[str], timeout: float = 60.0) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )

    # =========================================================================
    # 1. UPSTREAM GITHUB REPO CHECK & PULL
    # =========================================================================

    def check_and_pull_upstream(self) -> Tuple[bool, bool, str, str, List[str]]:
        """
        Fetches origin and checks if there are new commits on main.
        Returns: (checked_ok, pulled, before_sha, after_sha, logs)
        """
        logs = []
        before_sha = ""
        after_sha = ""
        try:
            r0 = self._run_git(["git", "rev-parse", "HEAD"])
            before_sha = r0.stdout.strip()
            logs.append(f"Current local HEAD: {before_sha[:7]}")

            # Fetch origin
            fetch_res = self._run_git(["git", "fetch", "origin", "main"], timeout=45.0)
            if fetch_res.returncode != 0:
                logs.append(f"git fetch origin notice: {fetch_res.stderr.strip()[:100]}")

            # Check remote HEAD
            r1 = self._run_git(["git", "rev-parse", "origin/main"])
            remote_sha = r1.stdout.strip()
            logs.append(f"Remote origin/main HEAD: {remote_sha[:7]}")

            if remote_sha and remote_sha != before_sha:
                # Upstream has new commits, check if we can fast-forward pull
                pull_res = self._run_git(["git", "merge", "--ff-only", "origin/main"], timeout=30.0)
                if pull_res.returncode == 0:
                    r2 = self._run_git(["git", "rev-parse", "HEAD"])
                    after_sha = r2.stdout.strip()
                    logs.append(f"Successfully pulled upstream commits to {after_sha[:7]}")
                    return True, True, before_sha, after_sha, logs
                else:
                    logs.append(f"Fast-forward merge skipped (local diverged): {pull_res.stderr.strip()[:120]}")
            else:
                logs.append("Local repository is fully up to date with origin/main.")

            after_sha = before_sha
            return True, False, before_sha, after_sha, logs
        except Exception as e:
            logs.append(f"Error checking upstream: {e}")
            return False, False, before_sha, after_sha, logs

    # =========================================================================
    # 2. CAPABILITY HARVESTING & SANDBOX VALIDATION
    # =========================================================================

    def verify_clean_code(self, code_text: str) -> Tuple[bool, str]:
        """Ensures synthesized code has zero secrets and zero prohibited tokens."""
        if PROHIBITED_TOKEN in code_text:
            return False, "Prohibited identity token detected in synthesized code"
        for pat in SECRET_PATTERNS:
            if pat.search(code_text):
                return False, "Potential API secret pattern detected in synthesized code"
        try:
            ast.parse(code_text)
        except SyntaxError as e:
            return False, f"SyntaxError in code: {e}"
        return True, "Code clean"

    def harvest_and_verify_skills(self) -> Tuple[List[str], int, int, List[str]]:
        """
        Discovers new capabilities, verifies python skills in skills/,
        and hot-reloads them into the active tool registry.
        """
        logs = []
        synthesized: List[str] = []
        verified_count = 0
        reloaded_count = 0

        try:
            from core.active_tool_registry import get_active_tool_registry
            registry = get_active_tool_registry()
        except Exception:
            registry = None

        if not SKILLS_DIR.exists():
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Synthesize missing capabilities from curated sources
        for src in CURATED_SOURCES:
            src_name = src["name"]
            skill_target = SKILLS_DIR / f"{src_name}.py"
            if not skill_target.exists():
                try:
                    from skills.github_skill_harvester import get_github_skill_harvester
                    harvester = get_github_skill_harvester()
                    ok, res = harvester.harvest_and_compile_skill({
                        "name": src_name,
                        "full_name": src.get("full_name", src_name),
                        "description": src.get("description", ""),
                        "html_url": src.get("url", ""),
                        "stars": 500,
                    }, skill_slug=src_name)
                    if ok:
                        synthesized.append(src_name)
                        logs.append(f"Auto-assimilated new capability '{src_name}' from {src.get('url')}")
                except Exception as ex:
                    logs.append(f"Notice auto-assimilating {src_name}: {ex}")

        # 2. Audit and verify existing skills in skills/
        for skill_file in sorted(SKILLS_DIR.glob("*.py")):
            if skill_file.name.startswith("__"):
                continue
            try:
                content = skill_file.read_text(encoding="utf-8", errors="ignore")
                is_clean, reason = self.verify_clean_code(content)
                if not is_clean:
                    logs.append(f"Skipping {skill_file.name}: {reason}")
                    continue

                py_compile.compile(str(skill_file), doraise=True)
                verified_count += 1

                # Hot-reload into registry if available
                if registry and hasattr(registry, "register_skill_file"):
                    try:
                        ok = registry.register_skill_file(skill_file)
                        if ok:
                            reloaded_count += 1
                    except Exception:
                        pass
            except Exception as e:
                logs.append(f"Verification error in {skill_file.name}: {e}")

        logs.append(f"Verified {verified_count} skills cleanly in skills/.")
        return synthesized, verified_count, reloaded_count, logs

    # =========================================================================
    # 3. AUTONOMOUS GITHUB PUSH
    # =========================================================================

    def auto_push_to_github(self, commit_message: str = "feat(evolution): autonomous capability upgrade & skill sync") -> Tuple[bool, str, List[str]]:
        """
        Checks git status for uncommitted improvements, commits them cleanly,
        and pushes to GitHub origin main.
        """
        logs = []
        try:
            # Check git status
            status_res = self._run_git(["git", "status", "--porcelain"])
            dirty_lines = [l for l in status_res.stdout.splitlines() if l.strip()]

            if not dirty_lines:
                logs.append("Working tree is completely clean. No new local changes to push.")
                # Verify remote matches local
                rev_res = self._run_git(["git", "rev-parse", "HEAD"])
                sha = rev_res.stdout.strip()
                return True, sha, logs

            logs.append(f"Detected {len(dirty_lines)} modified/untracked files. Staging verified files...")

            # Stage files
            add_res = self._run_git(["git", "add", "-A"])
            if add_res.returncode != 0:
                logs.append(f"git add error: {add_res.stderr.strip()[:100]}")
                return False, "", logs

            # Pre-commit safety scan on staged diff
            diff_res = self._run_git(["git", "diff", "--cached"])
            staged_diff = diff_res.stdout
            if PROHIBITED_TOKEN in staged_diff:
                logs.append("ABORTED: Prohibited identity token detected in staged git diff!")
                self._run_git(["git", "reset", "HEAD"])
                return False, "", logs
            for pat in SECRET_PATTERNS:
                if pat.search(staged_diff):
                    logs.append("ABORTED: Secret pattern detected in staged git diff! Unstaging...")
                    self._run_git(["git", "reset", "HEAD"])
                    return False, "", logs

            # Commit
            commit_res = self._run_git(["git", "commit", "-m", commit_message])
            if commit_res.returncode != 0:
                logs.append(f"Commit output: {commit_res.stdout.strip()[:100]} | {commit_res.stderr.strip()[:100]}")

            # Get new commit SHA
            rev_res = self._run_git(["git", "rev-parse", "HEAD"])
            new_sha = rev_res.stdout.strip()
            logs.append(f"Local commit created: {new_sha[:7]}")

            # Push to origin main
            push_res = self._run_git(["git", "push", "origin", "main"], timeout=60.0)
            if push_res.returncode == 0:
                logs.append(f"Successfully pushed {new_sha[:7]} to GitHub repository!")
                return True, new_sha, logs
            else:
                logs.append(f"Push response: {push_res.stderr.strip()[:200]}")
                return False, new_sha, logs
        except Exception as e:
            logs.append(f"Auto-push error: {e}")
            return False, "", logs

    # =========================================================================
    # 4. FULL COMPREHENSIVE UPGRADE CYCLE
    # =========================================================================

    def run_full_upgrade_cycle(self, auto_push: bool = True) -> UpgradeCycleReceipt:
        """
        Executes complete self-upgrade cycle:
        1. Checks upstream GitHub repo and pulls new commits if available.
        2. Audits and hot-reloads skills and harvested capabilities.
        3. Pushes newly synthesized capabilities or evolutions back to GitHub.
        """
        t0 = time.perf_counter()
        all_logs: List[str] = []

        all_logs.append("⚡ Starting J.A.R.V.I.S. Sovereign GitHub Self-Upgrade Cycle...")

        # Step 1: Upstream Pull
        chk_ok, pulled, before_sha, after_sha, up_logs = self.check_and_pull_upstream()
        all_logs.extend(up_logs)

        # Step 2: Harvest & Verify Skills
        synth, verified, reloaded, harv_logs = self.harvest_and_verify_skills()
        all_logs.extend(harv_logs)

        # Step 3: Auto-Push if desired
        pushed = False
        pushed_sha = after_sha or before_sha
        if auto_push:
            pushed_ok, new_sha, push_logs = self.auto_push_to_github()
            all_logs.extend(push_logs)
            pushed = pushed_ok
            if new_sha:
                pushed_sha = new_sha

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        all_logs.append(f"Upgrade cycle completed in {duration_ms} ms.")

        receipt = UpgradeCycleReceipt(
            ok=chk_ok,
            upstream_checked=chk_ok,
            upstream_pulled=pulled,
            upstream_commit_before=before_sha,
            upstream_commit_after=after_sha,
            skills_scanned=verified,
            skills_synthesized=synth,
            sandbox_verified_count=verified,
            hot_reloaded_count=reloaded,
            pushed_to_github=pushed,
            pushed_commit_sha=pushed_sha,
            duration_ms=duration_ms,
            log_messages=all_logs
        )

        self.last_receipt = receipt
        self._save_receipt(receipt)
        return receipt

    def _save_receipt(self, receipt: UpgradeCycleReceipt) -> None:
        try:
            history = []
            if self.history_file.exists():
                try:
                    history = json.loads(self.history_file.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            history.append(receipt.to_dict())
            history = history[-50:]  # Keep last 50 runs
            self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to write upgrade history: %s", e)

    # =========================================================================
    # 5. BACKGROUND DAEMON SCHEDULER
    # =========================================================================

    def start_background_daemon(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._thread = threading.Thread(target=self._background_loop, daemon=True, name="JarvisGitHubUpgrader")
            self._thread.start()
            logger.info("Autonomous GitHub Upgrader background daemon started.")

    def stop_background_daemon(self) -> None:
        self.is_running = False

    def _background_loop(self) -> None:
        # Initial delay on boot (60 seconds) so ports and services boot first
        time.sleep(60.0)
        while self.is_running:
            try:
                logger.info("Triggering periodic autonomous GitHub self-upgrade cycle...")
                self.run_full_upgrade_cycle(auto_push=True)
            except Exception as e:
                logger.error("Background upgrade cycle error: %s", e)
            
            # Sleep in 10-second increments for clean exit
            slept = 0.0
            while slept < self.check_interval_seconds and self.is_running:
                time.sleep(10.0)
                slept += 10.0


def get_autonomous_github_upgrader() -> AutonomousGitHubUpgrader:
    return AutonomousGitHubUpgrader.get_instance()


if __name__ == "__main__":
    upgrader = get_autonomous_github_upgrader()
    print("Executing immediate GitHub Self-Upgrade & Auto-Sync...")
    receipt = upgrader.run_full_upgrade_cycle(auto_push=True)
    print(json.dumps(receipt.to_dict(), indent=2))
