"""
verify_frontend_runner.py — Standalone Python test runner for M4 & M5 Frontend Verification.
"""

import sys
import os
import asyncio
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_m4_m5_frontend import (
    TestWebTerminalHTML,
    TestTerminalCSS,
    TestJavaScriptModules,
    TestMathematicalRiskVerification,
    TestVoiceNLPIntentParsing,
    TestServerHTMLServing
)

def run_sync_test(cls_obj, method_name):
    try:
        if hasattr(cls_obj, "setup_html"):
            cls_obj.setup_html()
        if hasattr(cls_obj, "setup_css"):
            cls_obj.setup_css()
        getattr(cls_obj, method_name)()
        return True, "PASSED"
    except Exception as e:
        return False, f"FAILED: {e}\n{traceback.format_exc()}"

async def run_async_test(cls_obj, method_name):
    try:
        await getattr(cls_obj, method_name)()
        return True, "PASSED"
    except Exception as e:
        return False, f"FAILED: {e}\n{traceback.format_exc()}"

def main():
    print("=" * 80)
    print("RUNNING FRONTEND & WEB TERMINAL AUTOMATED VERIFICATION SUITE")
    print("=" * 80)

    test_classes = [
        ("TestWebTerminalHTML", TestWebTerminalHTML, [
            "test_html_doctype_and_title",
            "test_css_stylesheet_link",
            "test_lightweight_charts_script_link",
            "test_header_elements_and_ids",
            "test_left_pane_elements_and_ids",
            "test_center_pane_elements_and_ids",
            "test_right_pane_risk_cockpit_elements_and_ids",
            "test_bottom_pane_positions_table_elements_and_ids",
            "test_modal_and_toast_elements",
            "test_all_javascript_scripts_loaded"
        ]),
        ("TestTerminalCSS", TestTerminalCSS, [
            "test_css_variables_defined",
            "test_action_button_styles_present",
            "test_badge_and_gauge_styles_present"
        ]),
        ("TestJavaScriptModules", TestJavaScriptModules, [
            "test_risk_cockpit_js_contract",
            "test_terminal_core_js_contract",
            "test_voice_copilot_js_contract",
            "test_terminal_app_js_contract"
        ]),
        ("TestMathematicalRiskVerification", TestMathematicalRiskVerification, [
            "test_aladdin_var_and_cvar_law",
            "test_prop_firm_hwm_ratchet_floor_25k",
            "test_consistency_rule_4_stage_derisking"
        ]),
        ("TestVoiceNLPIntentParsing", TestVoiceNLPIntentParsing, [
            "test_scale_out_intent",
            "test_lock_breakeven_intent",
            "test_kill_switch_intent"
        ]),
        ("TestServerHTMLServing", TestServerHTMLServing, [
            "test_terminal_route_serves_html"
        ])
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    results = []

    for suite_name, cls, methods in test_classes:
        print(f"\n--- Suite: {suite_name} ---")
        instance = cls()
        for m in methods:
            total_tests += 1
            if m == "test_terminal_route_serves_html":
                ok, status = asyncio.run(run_async_test(instance, m))
            else:
                ok, status = run_sync_test(instance, m)

            if ok:
                passed_tests += 1
                print(f"  [PASS] {m}")
                results.append((suite_name, m, "PASS", ""))
            else:
                failed_tests += 1
                print(f"  [FAIL] {m} -> {status}")
                results.append((suite_name, m, "FAIL", status))

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: Total={total_tests}, Passed={passed_tests}, Failed={failed_tests}")
    print("=" * 80)

    # Output verification file for auditing
    out_path = os.path.join(PROJECT_ROOT, ".agents", "sub_orch_m4_m5", "worker_1", "test_run_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"VERIFICATION SUMMARY: Total={total_tests}, Passed={passed_tests}, Failed={failed_tests}\n\n")
        for s, m, res, err in results:
            f.write(f"[{res}] {s}::{m}\n")
            if err:
                f.write(f"    {err}\n")

    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
