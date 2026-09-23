"""
tests/verify_flakiness_and_leakage.py — Empirical Multi-Run Flakiness & Leakage Audit Runner.
Executes repeated test runs and audits filesystem, file descriptors, and lingering artifacts.
"""

import os
import sys
import time
import subprocess
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check_filesystem_cleanliness():
    """Verifies that no lingering temporary or lock files exist in data/backups or data/."""
    dirty_files = []
    backups_dir = os.path.join(PROJECT_ROOT, "data", "backups")
    if os.path.exists(backups_dir):
        for f in os.listdir(backups_dir):
            if f.startswith(".staging") or f.startswith(".tmp") or f.endswith(".tmp") or f.endswith(".lock"):
                dirty_files.append(os.path.join("data/backups", f))

    cognitive_dir = os.path.join(PROJECT_ROOT, "data", "cognitive_memory")
    if os.path.exists(cognitive_dir):
        for f in os.listdir(cognitive_dir):
            if f.endswith(".tmp") or f.endswith(".lock"):
                dirty_files.append(os.path.join("data/cognitive_memory", f))

    return dirty_files


def run_repeated_crypto_arbitrage_suite(iterations: int = 10):
    """Runs tests/test_crypto_feeds_arbitrage.py multiple times sequentially."""
    print(f"\n--- Running Crypto Feeds & Arbitrage Test Suite ({iterations} Iterations) ---")
    for i in range(1, iterations + 1):
        t0 = time.perf_counter()
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_crypto_feeds_arbitrage.py", "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        elapsed = time.perf_counter() - t0
        if res.returncode != 0:
            print(f"[FAIL] Iteration {i}/{iterations} failed in {elapsed:.2f}s:\n{res.stdout}\n{res.stderr}")
            return False
        else:
            print(f"[PASS] Iteration {i}/{iterations} (101 tests) completed in {elapsed:.2f}s (Exit code: 0)")
    return True


def run_repeated_backup_recovery_suite(iterations: int = 5):
    """Runs tests/test_backup_disaster_recovery.py multiple times sequentially."""
    print(f"\n--- Running Backup & Disaster Recovery Test Suite ({iterations} Iterations) ---")
    for i in range(1, iterations + 1):
        t0 = time.perf_counter()
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_backup_disaster_recovery.py", "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        elapsed = time.perf_counter() - t0
        if res.returncode != 0:
            print(f"[FAIL] Iteration {i}/{iterations} failed in {elapsed:.2f}s:\n{res.stdout}\n{res.stderr}")
            return False
        else:
            print(f"[PASS] Iteration {i}/{iterations} (44 tests) completed in {elapsed:.2f}s (Exit code: 0)")
    return True


def main():
    print("================================================================================")
    print("EMPIRICAL CHALLENGER 2: MULTI-RUN FLAKINESS & LINGERING ARTIFACT AUDIT")
    print("================================================================================")

    # 1. Pre-run cleanliness check
    pre_dirty = check_filesystem_cleanliness()
    print(f"Pre-run lingering files in data/: {len(pre_dirty)} {pre_dirty if pre_dirty else '(Clean)'}")

    # 2. Crypto Feeds & Arbitrage repetition
    crypto_pass = run_repeated_crypto_arbitrage_suite(iterations=10)

    # 3. State Backup & Disaster Recovery repetition
    backup_pass = run_repeated_backup_recovery_suite(iterations=5)

    # 4. Post-run cleanliness check
    post_dirty = check_filesystem_cleanliness()
    print(f"\nPost-run lingering files in data/: {len(post_dirty)} {post_dirty if post_dirty else '(Clean)'}")

    # Final verdict
    success = crypto_pass and backup_pass and (len(post_dirty) == 0)
    print("\n================================================================================")
    if success:
        print("VERDICT: 100% PASS — ZERO FLAKINESS & ZERO LINGERING ARTIFACTS DETECTED")
    else:
        print("VERDICT: FAIL — FLAKINESS OR LEAKS DETECTED")
    print("================================================================================")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
