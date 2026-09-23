"""
tests/verify_challenger2_runner.py — Standalone Python test runner for Challenger 2.
"""

import sys
import os
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_empirical_challenger2 import (
    JSTranslatedVoiceNLPParser,
    TEST_VOICE_QUERIES,
    TestVoiceAIHarness,
    TestAudioChimeParameters,
    PythonEventBus,
    TestEventBusEmpirical,
    TestHTMLDOMCompleteVerification
)

def run_challenger2_tests():
    print("=" * 80)
    print("CHALLENGER 2: EMPIRICAL STRESS TEST & VERIFICATION HARNESS")
    print("=" * 80)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    failures = []

    # 1. Voice AI NLP Queries (35+)
    print("\n--- 1. Voice AI NLP Intent & Entity Parser (35+ Queries) ---")
    parser = JSTranslatedVoiceNLPParser()
    for idx, (query, exp_intent, exp_sym, exp_ratio) in enumerate(TEST_VOICE_QUERIES, 1):
        total_tests += 1
        try:
            res = parser.parse_intent(query, active_symbol="XAUUSD")
            if res["intent"] != exp_intent:
                raise AssertionError(f"Expected intent '{exp_intent}', got '{res['intent']}'")
            if exp_sym and res["actionPayload"].get("symbol") != exp_sym:
                raise AssertionError(f"Expected symbol '{exp_sym}', got '{res['actionPayload'].get('symbol')}'")
            if exp_ratio is not None and res["actionPayload"].get("ratio") != exp_ratio:
                raise AssertionError(f"Expected ratio '{exp_ratio}', got '{res['actionPayload'].get('ratio')}'")
            passed_tests += 1
            print(f"  [PASS] Query #{idx:02d}: \"{query}\" -> Intent: {res['intent']}")
        except Exception as e:
            failed_tests += 1
            print(f"  [FAIL] Query #{idx:02d}: \"{query}\" -> {e}")
            failures.append((f"VoiceQuery_{idx}", query, str(e)))

    # 2. Audio Chime Parameters
    print("\n--- 2. Procedural Web Audio API Sound Chime Mathematical Ranges ---")
    audio_test = TestAudioChimeParameters()
    for m in ["test_audio_frequencies_within_audible_range", "test_audio_gains_are_safe_and_sub_unity", "test_sound_durations_sub_second"]:
        total_tests += 1
        try:
            getattr(audio_test, m)()
            passed_tests += 1
            print(f"  [PASS] {m}")
        except Exception as e:
            failed_tests += 1
            print(f"  [FAIL] {m} -> {e}")
            failures.append(("AudioParams", m, str(e)))

    # 3. EventBus Empirical Tests
    print("\n--- 3. TerminalCore EventBus Pub/Sub & Error Resilience ---")
    eb_test = TestEventBusEmpirical()
    for m in [
        "test_multiple_listeners_receive_events_in_order",
        "test_once_listener_fires_exactly_once",
        "test_unsubscribe_function_removes_listener",
        "test_listener_throwing_error_does_not_crash_bus"
    ]:
        total_tests += 1
        try:
            getattr(eb_test, m)()
            passed_tests += 1
            print(f"  [PASS] {m}")
        except Exception as e:
            failed_tests += 1
            print(f"  [FAIL] {m} -> {e}")
            failures.append(("EventBus", m, str(e)))

    # 4. HTML DOM Verification
    print("\n--- 4. Master HTML DOM Layout, Controls, Tables & Gauges ---")
    dom_test = TestHTMLDOMCompleteVerification()
    dom_test.load_html()
    for m in ["test_essential_interactive_buttons", "test_essential_telemetry_gauges", "test_essential_tables_and_canvases"]:
        total_tests += 1
        try:
            getattr(dom_test, m)()
            passed_tests += 1
            print(f"  [PASS] {m}")
        except Exception as e:
            failed_tests += 1
            print(f"  [FAIL] {m} -> {e}")
            failures.append(("HTMLDOM", m, str(e)))

    print("\n" + "=" * 80)
    print(f"CHALLENGER 2 VERIFICATION SUMMARY: Total={total_tests}, Passed={passed_tests}, Failed={failed_tests}")
    print("=" * 80)

    # Write log to Challenger 2 agent directory
    out_file = os.path.join(PROJECT_ROOT, ".agents", "sub_orch_m4_m5", "challenger_2", "test_execution_log.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"CHALLENGER 2 VERIFICATION SUMMARY: Total={total_tests}, Passed={passed_tests}, Failed={failed_tests}\n\n")
        for f_type, name, err in failures:
            f.write(f"[FAILED] {f_type} :: {name} -> {err}\n")
        if not failures:
            f.write("ALL 47 EMPIRICAL VERIFICATION TESTS PASSED WITH ZERO ERRORS (100% SUCCESS RATE).\n")

    return failed_tests == 0

if __name__ == "__main__":
    success = run_challenger2_tests()
    sys.exit(0 if success else 1)
