"""
J.A.R.V.I.S. Quantum AI Operating System — E2E Test Runner
================================================================================
Unified 4-Tier Opaque-Box E2E Test Suite Runner
Executes Tiers 1 through 4 in isolated subprocesses, aggregates test results,
formats terminal output, and exports comprehensive JSON results.
================================================================================
"""

import sys
import os
import re
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Reconfigure stdout for UTF-8 safely
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def run_all_tiers():
    start_time = time.perf_counter()

    tier_scripts = [
        ("Tier 1 - Feature Coverage", BASE_DIR / "tests" / "e2e" / "test_tier1_features.py"),
        ("Tier 2 - Boundaries & Negatives", BASE_DIR / "tests" / "e2e" / "test_tier2_boundaries.py"),
        ("Tier 3 - Cross-Feature Combinations", BASE_DIR / "tests" / "e2e" / "test_tier3_cross_feature.py"),
        ("Tier 4 - Real-World Workloads", BASE_DIR / "tests" / "e2e" / "test_tier4_real_world.py"),
    ]

    print("\n" + "=" * 80)
    print("  J.A.R.V.I.S. Quantum AI Operating System - E2E Test Suite (All 4 Tiers)")
    print("=" * 80 + "\n")

    tier_results = []
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for tier_name, script_path in tier_scripts:
        tier_start = time.perf_counter()
        print(f"[Running] {tier_name} ({script_path.name})...")

        temp_log = BASE_DIR / "tests" / "e2e" / f"_temp_tier_{script_path.stem}.log"
        try:
            with open(temp_log, "w", encoding="utf-8", errors="replace") as log_f:
                proc = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(BASE_DIR),
                    stdout=log_f,
                    stderr=log_f,
                )
                proc.wait(timeout=180)
            returncode = proc.returncode
            combined_output = temp_log.read_text(encoding="utf-8", errors="replace") if temp_log.exists() else ""
        except subprocess.TimeoutExpired:
            proc.kill()
            returncode = 124
            combined_output = (temp_log.read_text(encoding="utf-8", errors="replace") if temp_log.exists() else "") + "\n[ERROR] Tier execution timed out."
        finally:
            if temp_log.exists():
                try:
                    temp_log.unlink()
                except Exception:
                    pass

        tier_elapsed = round(time.perf_counter() - tier_start, 2)

        # Parse test count and results from standard unittest output
        # Example: "Ran 183 tests in 62.339s\n\nOK" or "FAILED (failures=1, errors=2)"
        match_ran = re.search(r"Ran (\d+) tests in", combined_output)
        tests_run = int(match_ran.group(1)) if match_ran else 0

        match_fail = re.search(r"failures=(\d+)", combined_output)
        failures = int(match_fail.group(1)) if match_fail else 0

        match_err = re.search(r"errors=(\d+)", combined_output)
        errors = int(match_err.group(1)) if match_err else 0

        match_skip = re.search(r"skipped=(\d+)", combined_output)
        skipped = int(match_skip.group(1)) if match_skip else 0

        passed = tests_run - failures - errors - skipped
        status = "PASS" if returncode == 0 and failures == 0 and errors == 0 else "FAIL"

        print(f"  -> [{status}] {passed}/{tests_run} passed in {tier_elapsed}s\n")

        if status != "PASS":
            # Print last 20 lines of output for diagnostics
            lines = [l for l in combined_output.strip().splitlines() if l.strip()]
            for line in lines[-20:]:
                print(f"     {line}")
            print()

        tier_results.append({
            "tier": tier_name,
            "script": str(script_path.relative_to(BASE_DIR)),
            "tests_run": tests_run,
            "passed": passed,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "elapsed_seconds": tier_elapsed,
            "status": status,
        })

        total_tests += tests_run
        total_failures += failures
        total_errors += errors
        total_skipped += skipped

    total_elapsed = round(time.perf_counter() - start_time, 2)
    total_passed = total_tests - total_failures - total_errors - total_skipped
    overall_status = "PASS" if (total_failures == 0 and total_errors == 0 and total_tests > 0) else "FAIL"

    print("=" * 80)
    print(f"  TOTAL SUMMARY: [{overall_status}] {total_passed}/{total_tests} Passed in {total_elapsed}s")
    print("=" * 80)
    print(f"  * Total Tests: {total_tests}")
    print(f"  * Passed:      {total_passed}")
    print(f"  * Failures:    {total_failures}")
    print(f"  * Errors:      {total_errors}")
    print(f"  * Skipped:     {total_skipped}")
    print("=" * 80 + "\n")

    summary_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": overall_status,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failures": total_failures,
        "total_errors": total_errors,
        "total_skipped": total_skipped,
        "total_elapsed_seconds": total_elapsed,
        "tiers": tier_results,
    }

    results_file = BASE_DIR / "tests" / "e2e" / "test_results.json"
    results_file.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"Results written to: {results_file}\n")

    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    exit_code = run_all_tiers()
    sys.exit(exit_code)
