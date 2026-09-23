"""
J.A.R.V.I.S. Master Command Center — Unified E2E Test Runner
========================================================================
Supports multi-tier test execution with comprehensive reporting:
  --tier 1 : Tier 1 Core Feature Coverage Tests (26 features, 130+ tests)
  --tier 2 : Tier 2 Boundary, Limit & Negative Tests
  --tier 3 : Tier 3 Cross-Subsystem Combination & Pairwise Tests
  --tier 4 : Tier 4 Real-World Application Workload Scenarios
  --tier all : Full E2E Test Suite (Tiers 1-4)
========================================================================
"""

import sys
import os
import time
import argparse
import unittest
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Ensure UTF-8 output on Windows if possible
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure jarvis root and MQ3 root are in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
MQ3_DIR = Path("P:/MQ3 TRADING BOT")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if MQ3_DIR.exists() and str(MQ3_DIR) not in sys.path:
    sys.path.insert(0, str(MQ3_DIR))


# ANSI Terminal Colors
CYAN = "\033[96m\033[1m"
GREEN = "\033[92m\033[1m"
YELLOW = "\033[93m\033[1m"
RED = "\033[91m\033[1m"
MAGENTA = "\033[95m\033[1m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class ColorTextTestResult(unittest.TextTestResult):
    """Custom test result collector tracking tier stats."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.showAll:
            self.stream.writeln(f" {GREEN}[PASS]{RESET}")

    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            self.stream.writeln(f" {RED}[ERROR]{RESET}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            self.stream.writeln(f" {RED}[FAIL]{RESET}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.showAll:
            self.stream.writeln(f" {YELLOW}[SKIP] ({reason}){RESET}")


class ColorTestRunner(unittest.TextTestRunner):
    resultclass = ColorTextTestResult


def load_module_from_file(module_name: str, file_path: Path):
    """Loads a Python module directly from an absolute file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_tier_suite(tier_num: int) -> unittest.TestSuite:
    """Loads test suite for a specific tier."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    tests_dir = BASE_DIR / "tests"

    if tier_num == 1:
        mod = load_module_from_file("jarvis_tier1_feature_tests", tests_dir / "tier1_feature_tests.py")
        suite.addTests(loader.loadTestsFromModule(mod))
    elif tier_num == 2:
        mod = load_module_from_file("jarvis_tier2_boundary_tests", tests_dir / "tier2_boundary_tests.py")
        suite.addTests(loader.loadTestsFromModule(mod))
    elif tier_num == 3:
        mod = load_module_from_file("jarvis_tier3_combination_tests", tests_dir / "tier3_combination_tests.py")
        suite.addTests(loader.loadTestsFromModule(mod))
    elif tier_num == 4:
        mod = load_module_from_file("jarvis_tier4_workload_tests", tests_dir / "tier4_workload_tests.py")
        suite.addTests(loader.loadTestsFromModule(mod))
    else:
        raise ValueError(f"Unknown tier number: {tier_num}")

    return suite


def print_banner():
    print(f"""
{CYAN}========================================================================
  J . A . R . V . I . S   M A S T E R   C O M M A N D   C E N T E R
             A U T O M A T E D   E 2 E   T E S T   H A R N E S S
========================================================================{RESET}
{DIM}Testing Framework: Multi-Tier Opaque-Box & Integration Suite
Tiers: Tier 1 (Features) | Tier 2 (Boundaries) | Tier 3 (Combinations) | Tier 4 (Workloads){RESET}
""")


def run_tests(tiers_to_run: List[int], verbosity: int = 1) -> bool:
    """Executes selected tiers and prints structured summary."""
    print_banner()

    overall_start = time.time()
    tier_results: Dict[int, Dict[str, Any]] = {}
    all_passed = True

    for t in tiers_to_run:
        tier_name = {
            1: "Tier 1: Core Feature Coverage Suite (26 Features)",
            2: "Tier 2: Boundary Value, Limit & Error Handling Suite",
            3: "Tier 3: Cross-Subsystem & Pairwise Combination Suite",
            4: "Tier 4: Real-World Operational Workload Scenarios"
        }.get(t, f"Tier {t}")

        print(f"\n{MAGENTA}>>> Running {tier_name}...{RESET}")
        print("-" * 72)

        try:
            suite = load_tier_suite(t)
        except Exception as e:
            print(f"{RED}Failed to load suite for Tier {t}: {e}{RESET}")
            tier_results[t] = {
                "name": tier_name,
                "total": 0, "passed": 0, "failures": 1, "errors": 0, "skipped": 0,
                "duration": 0.0, "error_msg": str(e), "passed_bool": False
            }
            all_passed = False
            continue

        runner = ColorTestRunner(verbosity=verbosity)
        t_start = time.time()
        result = runner.run(suite)
        t_duration = time.time() - t_start

        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        passed = getattr(result, "success_count", total_tests - failures - errors - skipped)

        tier_pass = (failures == 0 and errors == 0)
        if not tier_pass:
            all_passed = False

        tier_results[t] = {
            "name": tier_name,
            "total": total_tests,
            "passed": passed,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "duration": t_duration,
            "passed_bool": tier_pass
        }

    # Summary Report Table
    overall_duration = time.time() - overall_start
    print("\n" + "=" * 72)
    print(f"{BOLD}                    E2E TEST EXECUTION SUMMARY                    {RESET}")
    print("=" * 72)
    print(f"{'Tier':<8} {'Suite Name':<42} {'Tests':<7} {'Pass':<6} {'Fail':<6} {'Time':<8} {'Status'}")
    print("-" * 72)

    total_all = sum(r.get("total", 0) for r in tier_results.values())
    passed_all = sum(r.get("passed", 0) for r in tier_results.values())
    failed_all = sum(r.get("failures", 0) + r.get("errors", 0) for r in tier_results.values())

    for t, r in tier_results.items():
        status_str = f"{GREEN}PASS{RESET}" if r.get("passed_bool") else f"{RED}FAIL{RESET}"
        dur_str = f"{r.get('duration', 0):.2f}s"
        print(f"Tier {t:<3} {r.get('name')[:40]:<42} {r.get('total', 0):<7} {r.get('passed', 0):<6} {r.get('failures', 0) + r.get('errors', 0):<6} {dur_str:<8} {status_str}")

    print("-" * 72)
    print(f"{'TOTAL':<8} {'All Executed Tiers':<42} {total_all:<7} {passed_all:<6} {failed_all:<6} {overall_duration:.2f}s")
    print("=" * 72)

    if all_passed and total_all > 0:
        print(f"\n{GREEN}[+] ALL SYSTEMS VERIFIED: 100% OF TEST ASSERTIONS PASSED ({passed_all}/{total_all}){RESET}")
        return True
    else:
        print(f"\n{RED}[-] TEST SUITE FAILED: {failed_all} failures/errors encountered.{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Master Command Center E2E Test Runner")
    parser.add_argument("--tier", default="all", help="Tier to execute: 1, 2, 3, 4, or 'all'")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose test output")

    args = parser.parse_args()
    tier_arg = str(args.tier).lower().strip()
    verbosity = 2 if args.verbose else 1

    if tier_arg == "all":
        tiers = [1, 2, 3, 4]
    elif tier_arg in ("1", "tier1", "t1"):
        tiers = [1]
    elif tier_arg in ("2", "tier2", "t2"):
        tiers = [2]
    elif tier_arg in ("3", "tier3", "t3"):
        tiers = [3]
    elif tier_arg in ("4", "tier4", "t4"):
        tiers = [4]
    else:
        try:
            tiers = [int(tier_arg)]
        except ValueError:
            print(f"{RED}Invalid tier argument: {args.tier}. Choose from 1, 2, 3, 4, all.{RESET}")
            sys.exit(1)

    success = run_tests(tiers, verbosity=verbosity)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
