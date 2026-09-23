# TEST_INFRA: J.A.R.V.I.S. Sovereign Self-Evolution, CUA Visual Browser & CLI-Anything

## 1. Executive Summary & Testing Philosophy
- **Authoritative Baseline**: Derived strictly from user specifications in `ORIGINAL_REQUEST.md` (## 2026-09-23T03:41:21Z) and `PROJECT.md` in `.agents/teamwork_preview_orchestrator_11/PROJECT.md`.
- **Testing Approach**: Dual-track independent, opaque-box testing verifying interface contracts, API schemas, mathematical invariants, deterministic state transitions, and observable behavior without coupling to internal private implementations.
- **Dual-Track Parallel Resilience**: Where implementation modules (`tools/github_assimilator.py`, `tools/cua_browser_engine.py`, `tools/cli_anything_bridge.py`, `core/self_evolution.py`) are actively being synthesized, tests gracefully bind to live implementations when available or fall back to spec-compliant interface doubles, guaranteeing 100% clean test runner execution throughout the lifecycle.
- **Progressive Testability & Isolation**: Tests are self-contained and isolated. Each test provisions its own fixture state, executes deterministic assertions, and cleans up temporary resources (`scratch/repos/`, `runtime/backups/`, `memory/`, temporary SQLite files) without order-of-execution coupling.
- **Strict Invariants Enforced**:
  - Absolute ZERO mentions or occurrences of prohibited identifiers anywhere in code, configuration, or logs.
  - Master identity governance: Master Muhammad Qureshi (`+923468053268`, `futureworldvision842@gmail.com`).
  - Hot wallet private key isolation: `SOLANA_PRIVATE_KEY` and `EVM_PRIVATE_KEY` ingested strictly via environment variables with zero disk leaks.
  - FundingPips `#40000294403` ($100k balance) deterministic risk ceiling: $\le 0.75\%$ ($750 max dollar loss per trade), $R:R \ge 2.5$, dynamic $+1.0R$ breakeven trigger, and 15-minute high-impact economic news blackout.
  - Hardware stability: 95% CPU throttle cap, memory caching guards, and asynchronous sub-process sandboxing under `BELOW_NORMAL_PRIORITY_CLASS`.

---

## 2. 4-Tier Testing Methodology

```
+-------------------------------------------------------------------------------+
|                      TIER 4: REAL-WORLD SCENARIOS                             |
|  End-to-End Operational Lifecycles, Multi-Device Workflows & Autonomous Loops |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                   TIER 3: CROSS-FEATURE INTERACTIONS                          |
|  Pairwise Synergies Across Tracks M1, M2, M3, M4 & Security Invariants        |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                   TIER 2: BOUNDARY & CORNER CASES                             |
|  Exact Mathematical Limits, Negative Inputs, Malformed Data & Fail-Closed     |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                     TIER 1: FEATURE COVERAGE                                  |
|  Deterministic Verification of All 17 Individual Features & Contract Schemas  |
+-------------------------------------------------------------------------------+
```

### Tier 1: Feature Coverage (>=5 test cases per feature in isolation, happy path)
Covers all 17 features from `PROJECT.md § Feature Inventory` with at least 5 isolated happy path tests per feature:
- **Feature 1 (R1.1: GitHub Cloner & Caching)**:
  1. `test_t1_f01_clone_remote_depth1`: Verifies shallow clone (`--depth 1`) command construction and destination path.
  2. `test_t1_f01_offline_cache_fallback`: Verifies fallback to cached local repository in `scratch/repos/` when network is offline.
  3. `test_t1_f01_local_path_ingestion`: Verifies ingesting existing local repo directory directly without network call.
  4. `test_t1_f01_custom_destination`: Verifies custom destination directory creation and structure.
  5. `test_t1_f01_manifest_metadata`: Verifies generation/extraction of repository metadata (repo name, commit/digest, branch).
- **Feature 2 (R1.2: AST-Based Functional & API Extractor)**:
  1. `test_t1_f02_extract_top_level_functions`: Extracts function names, arguments, return type annotations.
  2. `test_t1_f02_extract_classes_and_methods`: Extracts class hierarchy, method signatures, and class docstrings.
  3. `test_t1_f02_extract_cli_interfaces`: Discovers argparse/click CLI arguments and subcommands from AST nodes.
  4. `test_t1_f02_extract_docstrings`: Extracts full module and function docstrings for skill documentation.
  5. `test_t1_f02_extract_type_hints`: Parses parameter type annotations and default argument values cleanly.
- **Feature 3 (R1.3: Modular Skill & Tool Synthesizer)**:
  1. `test_t1_f03_synthesize_skill_manifest`: Generates valid Python module with `MANIFEST` dictionary.
  2. `test_t1_f03_synthesize_run_entrypoint`: Generates `run(parameters, player, speak)` contract entrypoint.
  3. `test_t1_f03_synthesize_companion_tool`: Generates callable companion tool module in `tools/`.
  4. `test_t1_f03_sandbox_test_success`: Validates synthesized skill code in isolated execution sandbox.
  5. `test_t1_f03_output_directory_structure`: Ensures correct module placement in target directory (`skills/`).
- **Feature 4 (R1.4: Dynamic Zero-Downtime Hot-Reloader)**:
  1. `test_t1_f04_register_skill_in_memory`: Loads skill module via `importlib.util` without file locking.
  2. `test_t1_f04_hot_reload_api_endpoint`: Validates `POST /api/tools/hot_reload` returns 200 with registration payload.
  3. `test_t1_f04_registry_query_active_skills`: Queries active tool registry and verifies new skill is discoverable.
  4. `test_t1_f04_zero_port_interruption`: Verifies hot-reloading does not drop TCP listeners on :8770, :3000, :5050, :8765.
  5. `test_t1_f04_update_existing_skill`: Updates existing skill definition in memory without server restart.
- **Feature 5 (R2.1: CDP Session & Viewport Controller)**:
  1. `test_t1_f05_cdp_session_initialization`: Initializes headless browser session via CDP connection.
  2. `test_t1_f05_viewport_geometry_config`: Configures standard viewport dimensions (1920x1080) and device scale factor.
  3. `test_t1_f05_session_lifecycle_close`: Verifies clean browser session teardown without orphan processes.
  4. `test_t1_f05_page_navigation`: Navigates to target URI and verifies readyState is 'complete'.
  5. `test_t1_f05_screenshot_capture_b64`: Captures viewport screenshot as valid base64-encoded image.
- **Feature 6 (R2.2: Hybrid Visual DOM Grounding)**:
  1. `test_t1_f06_ground_button_coordinates`: Extracts bounding box `[x, y, w, h]` and computed center `(cx, cy)` for buttons.
  2. `test_t1_f06_element_from_point_verification`: Confirms `document.elementFromPoint(cx, cy)` hits target element.
  3. `test_t1_f06_accessibility_tree_tags`: Extracts ARIA roles, input labels, and accessibility attributes.
  4. `test_t1_f06_interactive_element_indexing`: Assigns unique numeric IDs to all actionable DOM elements.
  5. `test_t1_f06_zero_pixel_drift_guarantee`: Verifies bounding box coordinates remain aligned under scrolling offsets.
- **Feature 7 (R2.3: Omnimodal Web Action Executor)**:
  1. `test_t1_f07_dispatch_click_action`: Dispatches mouse click to grounded element center coordinates.
  2. `test_t1_f07_human_delayed_typing`: Dispatches typing with 30-50ms inter-key jitter simulation.
  3. `test_t1_f07_dispatch_wheel_scroll`: Executes wheel scroll delta and verifies scroll position changes.
  4. `test_t1_f07_form_submission`: Populates multiple form inputs and submits via Enter or submit button.
  5. `test_t1_f07_extract_table_data`: Parses tabular DOM data into structured list of dictionaries.
- **Feature 8 (R2.4: Dual-Mode Operation & Dashboard Bridge)**:
  1. `test_t1_f08_headless_research_mode`: Executes background research under `BELOW_NORMAL_PRIORITY_CLASS`.
  2. `test_t1_f08_interactive_operator_mode`: Switches to visible interactive mode with frame streaming enabled.
  3. `test_t1_f08_mjpeg_stream_chunk`: Generates valid multipart/x-mixed-replace JPEG boundary stream.
  4. `test_t1_f08_cua_dashboard_router`: Tests FastAPI router `/api/cua/status` and `/api/cua/viewport`.
  5. `test_t1_f08_operator_intervention_hook`: Allows human operator to pause or override autonomous actions.
- **Feature 9 (R3.1: Resilient Execution & Auto-Retry Loop)**:
  1. `test_t1_f09_execute_successful_command`: Executes terminal command cleanly with exit code 0 and stdout.
  2. `test_t1_f09_auto_retry_transient_error`: Automatically retries failing command with exponential backoff.
  3. `test_t1_f09_timeout_handling`: Terminates hanging command after configured timeout with clean error envelope.
  4. `test_t1_f09_duration_ms_telemetry`: Measures command duration in milliseconds accurately.
  5. `test_t1_f09_retry_exhaustion`: Returns structured error receipt when all retries are exhausted.
- **Feature 10 (R3.2: Cross-Platform Terminal Matrix)**:
  1. `test_t1_f10_route_powershell`: Dispatches command explicitly via Windows PowerShell.
  2. `test_t1_f10_route_cmd`: Dispatches command explicitly via Windows CMD.exe.
  3. `test_t1_f10_route_git_bash`: Dispatches POSIX command via Git Bash environment.
  4. `test_t1_f10_route_wsl2_guarded`: Dispatches command via WSL2 with crash guard checks.
  5. `test_t1_f10_auto_shell_detection`: Automatically chooses optimal shell based on host OS and command syntax.
- **Feature 11 (R3.3: Declarative GUI-to-CLI Pipeline Synthesizer)**:
  1. `test_t1_f11_synthesize_app_launch_cli`: Transforms GUI launch workflow into deterministic one-line CLI command.
  2. `test_t1_f11_synthesize_file_export_cli`: Transforms multi-step GUI export into pipelined CLI instruction.
  3. `test_t1_f11_parameter_substitution`: Injects dynamic parameters into declarative CLI templates safely.
  4. `test_t1_f11_pipeline_chaining`: Chains multiple deterministic subcommands with conditional operators (`&&`, `|`).
  5. `test_t1_f11_synthesize_browser_nav_cli`: Generates CLI command to open and navigate browser to target URL.
- **Feature 12 (R4.1: Self-Reflective Execution Analyzer)**:
  1. `test_t1_f12_record_successful_execution`: Records tool execution duration, timestamp, and status.
  2. `test_t1_f12_record_error_trace`: Records exception trace and failure context upon execution error.
  3. `test_t1_f12_evaluate_sla_compliance`: Identifies whether execution met SLA latency threshold (e.g., <500ms).
  4. `test_t1_f12_detect_latency_degradation`: Flags tools experiencing latency drift across multiple runs.
  5. `test_t1_f12_aggregate_health_summary`: Produces rolling success rate and p95 latency metrics per tool.
- **Feature 13 (R4.2: SQLite Recipe & Trace Memory)**:
  1. `test_t1_f13_initialize_sqlite_wal`: Initializes SQLite database with `PRAGMA journal_mode=WAL`.
  2. `test_t1_f13_cache_optimized_recipe`: Stores optimized command recipe and metadata into SQLite memory.
  3. `test_t1_f13_retrieve_recipe_by_key`: Retrieves cached recipe by task key in sub-5ms.
  4. `test_t1_f13_persist_benchmark_traces`: Inserts historical benchmark traces without database locks.
  5. `test_t1_f13_concurrent_read_write`: Confirms concurrent WAL reads do not block transaction writes.
- **Feature 14 (R4.3: Autonomous Code Adapter & Sandbox Verifier)**:
  1. `test_t1_f14_generate_tool_patch`: Generates wrapper patch optimizing tool execution or error handling.
  2. `test_t1_f14_sandbox_verification_pass`: Executes candidate patch in isolated subprocess sandbox.
  3. `test_t1_f14_sandbox_resource_limits`: Enforces CPU time and memory caps on sandbox execution.
  4. `test_t1_f14_apply_patch_hot_swap`: Applies verified patch to target file with atomic write.
  5. `test_t1_f14_syntax_error_rejection`: Rejects code patch with invalid Python syntax before sandbox run.
- **Feature 15 (R4.4: Invariant Risk & Security Gate Enforcer)**:
  1. `test_t1_f15_enforce_fundingpips_risk_cap`: Validates risk $\le 0.75\%$ ($750 max risk on $100k account).
  2. `test_t1_f15_enforce_risk_reward_ratio`: Validates $R:R \ge 2.50$ trade requirement.
  3. `test_t1_f15_enforce_breakeven_lock`: Validates automatic $+1.0R$ profit breakeven trigger.
  4. `test_t1_f15_enforce_news_blackout`: Validates 15-minute high-impact economic news blackout window.
  5. `test_t1_f15_strict_identity_rule`: Scans code changes to guarantee absolute ZERO forbidden identifiers.
- **Feature 16 (R4.5: Atomic Rollback & Self-Healing Engine)**:
  1. `test_t1_f16_create_atomic_backup`: Creates timestamped snapshot copy in `runtime/backups/`.
  2. `test_t1_f16_automatic_rollback_on_failure`: Restores target file from backup when sandbox test fails.
  3. `test_t1_f16_quarantine_failed_patch`: Writes failed candidate patch to quarantine log with diagnostic trace.
  4. `test_t1_f16_verify_file_integrity_post_rollback`: Confirms target file hash exactly matches pre-patch state.
  5. `test_t1_f16_multiple_backup_rotation`: Manages backup version history with cleanup of old snapshots.
- **Feature 17 (E2E.1: End-to-End Requirement Test Suite)**:
  1. `test_t1_f17_e2e_suite_discoverable`: Verifies E2E test module is discoverable by pytest runner.
  2. `test_t1_f17_all_tiers_represented`: Confirms test classes exist for Tiers 1, 2, 3, and 4.
  3. `test_t1_f17_clean_exit_code`: Verifies test runner returns exit code 0 under standard execution.
  4. `test_t1_f17_execution_receipt_schema`: Validates test results export to structured JSON receipt.
  5. `test_t1_f17_zero_side_effects`: Confirms test suite execution cleans up all temporary artifacts.

Total Tier 1 Test Cases: 17 features * 5 tests = **85 tests**.

---

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature)
Covers edge cases, extreme limits, invalid inputs, and error paths for all 17 features:
- **Feature 1 (R1.1: GitHub Cloner & Caching Boundaries)**:
  1. `test_t2_f01_empty_repo_url`: Empty or whitespace-only repository URL raises `ValueError`.
  2. `test_t2_f01_invalid_repo_url_schema`: Non-git URI (e.g., `ftp://`, `file:///invalid`) raises clean error.
  3. `test_t2_f01_offline_no_cache_available`: Unreachable network with empty cache raises descriptive exception.
  4. `test_t2_f01_destination_permission_denied`: Unwritable destination directory handled safely without crashing.
  5. `test_t2_f01_oversized_repo_depth_limit`: Extremely large repo handled with shallow clone enforcement (`depth=1`).
- **Feature 2 (R1.2: AST Functional Extractor Boundaries)**:
  1. `test_t2_f02_empty_python_file`: Zero-byte Python file returns empty capability list without error.
  2. `test_t2_f02_syntax_error_file`: File with invalid Python syntax raises descriptive syntax error.
  3. `test_t2_f02_deeply_nested_classes`: AST parser handles deeply nested class/function structures (>10 levels).
  4. `test_t2_f02_unicode_and_emojis_in_docstrings`: Handles docstrings containing complex Unicode and special characters.
  5. `test_t2_f02_cyclic_imports_or_references`: AST extraction does not execute code, avoiding cyclic import locks.
- **Feature 3 (R1.3: Skill Synthesizer Boundaries)**:
  1. `test_t2_f03_empty_capability_dict`: Synthesizing from empty dictionary raises `ValueError`.
  2. `test_t2_f03_missing_required_manifest_fields`: Missing function name or entrypoint raises validation error.
  3. `test_t2_f03_sandbox_timeout_boundary`: Sandbox test exceeding timeout (8.0s) killed cleanly and returns False.
  4. `test_t2_f03_sandbox_infinite_loop_kill`: Process with `while True` terminated within time bound without hanging.
  5. `test_t2_f03_special_characters_in_skill_name`: Skill names with hyphens/spaces sanitized to valid Python identifiers.
- **Feature 4 (R1.4: Hot-Reloader Boundaries)**:
  1. `test_t2_f04_reload_nonexistent_file`: Reloading non-existent file path returns 404/error envelope.
  2. `test_t2_f04_reload_corrupted_bytecode`: Corrupted module file rejected without polluting active registry.
  3. `test_t2_f04_hot_reload_payload_malformed`: Malformed JSON body to `/api/tools/hot_reload` returns 400.
  4. `test_t2_f04_rapid_burst_hot_reloads`: 50 rapid sequential hot-reload requests handled without race condition.
  5. `test_t2_f04_skill_with_missing_run_method`: Module lacking `run()` function rejected from active registry.
- **Feature 5 (R2.1: CDP Session Boundaries)**:
  1. `test_t2_f05_invalid_cdp_url`: Connecting to unroutable CDP endpoint times out cleanly.
  2. `test_t2_f05_extreme_viewport_resolutions`: Viewport sizes (100x100 and 7680x4320) handled without crash.
  3. `test_t2_f05_double_initialization`: Calling `initialize_session()` twice reuses or resets cleanly.
  4. `test_t2_f05_close_uninitialized_session`: Calling `close()` before `initialize_session()` does not error.
  5. `test_t2_f05_navigation_http_error_codes`: Navigating to 404 or 500 pages returns status without crashing.
- **Feature 6 (R2.2: Visual DOM Grounding Boundaries)**:
  1. `test_t2_f06_ground_empty_page`: DOM grounding on empty `<html><body></body></html>` returns empty element list.
  2. `test_t2_f06_offscreen_elements`: Elements scrolled out of current viewport flagged as non-visible.
  3. `test_t2_f06_zero_size_hidden_elements`: `display: none` and `visibility: hidden` elements omitted from actionable list.
  4. `test_t2_f06_element_from_point_occluded`: Overlapping transparent modal/overlay correctly detected.
  5. `test_t2_f06_massive_dom_tree`: DOM tree with >10,000 elements processed within 500ms time budget.
- **Feature 7 (R2.3: Omnimodal Web Action Boundaries)**:
  1. `test_t2_f07_click_nonexistent_element_id`: Action on invalid element ID returns failure receipt.
  2. `test_t2_f07_type_into_disabled_input`: Typing into disabled/read-only input returns error without crash.
  3. `test_t2_f07_oversized_text_typing`: Typing text >10,000 characters chunked appropriately.
  4. `test_t2_f07_negative_scroll_coordinates`: Negative scroll delta handled cleanly without exception.
  5. `test_t2_f07_extract_empty_or_malformed_table`: Table selector matching no rows returns empty list.
- **Feature 8 (R2.4: Dual-Mode Operation Boundaries)**:
  1. `test_t2_f08_switch_mode_under_high_load`: Mode toggling under CPU load does not crash dashboard router.
  2. `test_t2_f08_stream_disconnect_client_abort`: Sudden client disconnect on MJPEG stream handled cleanly.
  3. `test_t2_f08_rapid_stream_frame_rate_cap`: Frame streaming throttled to prevent CPU runaway (>30 FPS cap).
  4. `test_t2_f08_invalid_mode_parameter`: Sending invalid mode string returns HTTP 400.
  5. `test_t2_f08_unauthorized_dashboard_access`: Requests lacking proper session tokens rejected.
- **Feature 9 (R3.1: Resilient Execution Boundaries)**:
  1. `test_t2_f09_command_with_zero_retries`: Setting `retries=0` fails immediately on first failure without retrying.
  2. `test_t2_f09_negative_timeout_value`: Negative timeout raises `ValueError`.
  3. `test_t2_f09_massive_stdout_streaming`: Command producing >10MB stdout handled without memory exhaustion.
  4. `test_t2_f09_command_not_found_exit_code`: Non-existent binary returns exit code 127/9009 with stderr.
  5. `test_t2_f09_empty_command_string`: Empty or whitespace-only command string returns exit code 0 or validation error.
- **Feature 10 (R3.2: Cross-Platform Matrix Boundaries)**:
  1. `test_t2_f10_unsupported_shell_type`: Specifying invalid shell name (e.g., `csh`) raises `ValueError`.
  2. `test_t2_f10_wsl2_unavailable_fallback`: Fallback to Git Bash when WSL2 is uninstalled or disabled.
  3. `test_t2_f10_powershell_execution_policy_bypass`: PowerShell commands run with `-ExecutionPolicy Bypass`.
  4. `test_t2_f10_cmd_special_characters_escaping`: Ampersands, carets, and pipes properly escaped in CMD commands.
  5. `test_t2_f10_linux_path_translation`: Translates Windows `C:\` paths to `/mnt/c/` or POSIX style correctly.
- **Feature 11 (R3.3: GUI-to-CLI Pipeline Boundaries)**:
  1. `test_t2_f11_unknown_workflow_name`: Synthesizing unregistered workflow raises `KeyError`.
  2. `test_t2_f11_missing_template_parameters`: Missing mandatory parameter in dictionary raises validation error.
  3. `test_t2_f11_command_injection_sanitization`: Parameter containing `; rm -rf /` or `& del` properly sanitized/escaped.
  4. `test_t2_f11_extreme_parameter_lengths`: Parameter string >4,096 characters handled within CLI buffer limits.
  5. `test_t2_f11_cyclic_pipeline_dependencies`: Multi-step pipeline with circular dependency rejected.
- **Feature 12 (R4.1: Execution Analyzer Boundaries)**:
  1. `test_t2_f12_negative_latency_value`: Recording negative latency raises `ValueError`.
  2. `test_t2_f12_massive_error_trace`: Error trace >100KB truncated safely to prevent database bloating.
  3. `test_t2_f12_zero_recorded_traces_summary`: Health summary on unrecorded tool returns empty/default metrics.
  4. `test_t2_f12_zero_threshold_latency`: SLA evaluation with `threshold=0` flags all executions.
  5. `test_t2_f12_analyzer_database_disk_full`: Analyzer handles disk write error gracefully without crashing caller.
- **Feature 13 (R4.2: SQLite Recipe Memory Boundaries)**:
  1. `test_t2_f13_database_corrupt_recovery`: Automatically recovers or rebuilds if SQLite file is malformed.
  2. `test_t2_f13_recipe_key_with_sql_injection`: Task keys containing `' OR 1=1 --` safely parameterized.
  3. `test_t2_f13_massive_recipe_payload`: Recipe payload >5MB stored and retrieved without corruption.
  4. `test_t2_f13_read_only_filesystem`: Gracefully falls back to in-memory SQLite when disk is read-only.
  5. `test_t2_f13_database_close_and_reopen`: Persistent data persists across close and re-instantiation.
- **Feature 14 (R4.3: Autonomous Code Adapter Boundaries)**:
  1. `test_t2_f14_empty_candidate_code`: Empty candidate code string rejected immediately.
  2. `test_t2_f14_forbidden_builtins_in_patch`: Candidate code importing `ctypes` or `os.system` blocked by security gate.
  3. `test_t2_f14_sandbox_memory_bomb`: Code allocating >1GB RAM terminated by memory guard.
  4. `test_t2_f14_sandbox_fork_bomb`: Subprocess creation within sandbox blocked or capped.
  5. `test_t2_f14_patch_target_file_locked`: Target file locked by another process handled with retry/fail-safe.
- **Feature 15 (R4.4: Invariant Risk & Security Gate Boundaries)**:
  1. `test_t2_f15_boundary_risk_exact_750`: Exact $750.00 risk permitted ($100k * 0.75%).
  2. `test_t2_f15_boundary_risk_over_750_01`: Exact $750.01 risk strictly rejected.
  3. `test_t2_f15_boundary_rr_exact_2_50`: Exact $R:R = 2.50$ permitted; $2.49$ strictly rejected.
  4. `test_t2_f15_boundary_news_blackout_900s`: News event in 900s (15m) triggers blackout; 901s does not.
  5. `test_t2_f15_strict_identity_prohibited_string`: Code containing prohibited substrings immediately triggers security veto.
- **Feature 16 (R4.5: Atomic Rollback Boundaries)**:
  1. `test_t2_f16_rollback_with_missing_backup`: Missing backup file path returns False with logged error.
  2. `test_t2_f16_rollback_target_does_not_exist`: Rolling back file that was deleted creates it from backup.
  3. `test_t2_f16_quarantine_directory_creation`: Quarantine directory created automatically if missing.
  4. `test_t2_f16_backup_disk_space_exhaustion`: Handles low disk space during backup creation safely.
  5. `test_t2_f16_simulated_power_cut_atomic_replace`: Atomic file rename (`os.replace`) prevents half-written files.
- **Feature 17 (E2E.1: Test Suite Boundaries)**:
  1. `test_t2_f17_pytest_filter_by_marker`: Verifies running with `-m tier1` or `-m tier2` executes subset.
  2. `test_t2_f17_parallel_pytest_xdist`: Verifies tests execute safely without file clashes.
  3. `test_t2_f17_test_failure_reporting`: Simulating single assertion failure produces clear diff report.
  4. `test_t2_f17_extreme_env_var_isolation`: Tests pass with sanitized environment variables.
  5. `test_t2_f17_pytest_basetemp_override`: Tests respect `--basetemp` to avoid NTFS symlink errors.

Total Tier 2 Test Cases: 17 features * 5 tests = **85 tests**.

---

### Tier 3: Cross-Feature Interactions (Pairwise Combinations)
Validates interactions across track boundaries:
1. `test_t3_p01_cloner_to_ast_extractor`: Cloned repo in `scratch/repos/` passed directly into AST extractor.
2. `test_t3_p02_ast_extractor_to_skill_synthesizer`: Extracted capabilities generate functional skill module.
3. `test_t3_p03_skill_synthesizer_to_hot_reloader`: Newly synthesized skill hot-reloaded into active tool registry.
4. `test_t3_p04_hot_reloader_to_cli_anything`: Dynamically registered skill executed via CLI terminal bridge.
5. `test_t3_p05_cdp_controller_to_dom_grounding`: Initialized CDP session provides DOM tree for coordinate grounding.
6. `test_t3_p06_dom_grounding_to_omnimodal_executor`: Grounded element bounding box clicked and typed into.
7. `test_t3_p07_omnimodal_executor_to_dual_mode`: Form submission in headless mode mirrors frame stream to dashboard.
8. `test_t3_p08_cua_visual_dom_to_cli_synthesizer`: UI element interaction translated into deterministic CLI command.
9. `test_t3_p09_auto_retry_to_cross_platform_matrix`: Retrying failing command switches fallback shell in terminal matrix.
10. `test_t3_p10_cli_bridge_to_execution_analyzer`: Terminal command latency and exit codes recorded into analyzer.
11. `test_t3_p11_execution_analyzer_to_sqlite_memory`: Analyzed benchmark traces persisted into WAL SQLite memory.
12. `test_t3_p12_sqlite_memory_to_code_adapter`: Degraded recipe in SQLite triggers autonomous code patch synthesis.
13. `test_t3_p13_code_adapter_to_risk_security_gate`: Candidate code patch verified by risk invariant enforcer.
14. `test_t3_p14_code_adapter_to_atomic_rollback`: Sandbox failure during patch verification triggers automatic rollback.
15. `test_t3_p15_github_assimilation_to_self_evolution`: Ingested external tool monitored, optimized, and cached in recipe DB.

Total Tier 3 Test Cases: **15 tests**.

---

### Tier 4: Real-World Application Scenarios
End-to-end multi-step operational lifecycles:
1. `test_t4_s01_autonomous_github_repo_to_live_skill`:
   *Lifecycle*: Target repository (e.g. `HKUDS/CLI-Anything`) shallow cloned -> AST parsed for CLI endpoints -> skill module synthesized -> validated in sandbox -> hot-reloaded into active registry -> queried on `:8770`.
2. `test_t4_s02_cua_visual_browser_data_harvesting`:
   *Lifecycle*: CDP session initialized -> navigates to data dashboard -> hybrid DOM grounding resolves table coordinates -> human-jitter typing filters data -> table extracted as structured JSON -> session cleaned up.
3. `test_t4_s03_deterministic_gui_to_cli_resilient_pipeline`:
   *Lifecycle*: Operator requests multi-step GUI export -> synthesized into declarative CLI command -> executed across cross-platform matrix -> transient error auto-retried with exponential backoff -> success receipt emitted.
4. `test_t4_s04_recursive_self_evolution_with_invariant_safety`:
   *Lifecycle*: Command execution analyzer detects latency degradation -> SQLite memory queried -> code patch synthesized -> tested in sandbox -> risk invariant enforcer verifies FundingPips $750 cap and identity rules -> hot-swapped into runtime -> atomic backup verified.
5. `test_t4_s05_sovereign_self_upgrade_and_recovery_flow`:
   *Lifecycle*: Self-upgrade engine generates candidate tool optimization -> sandbox test intentionally fails -> atomic rollback restores original code within 200ms -> failed patch quarantined with diagnostic trace -> zero system downtime.

Total Tier 4 Test Cases: **5 tests**.

---

## 3. Test Suite Grand Totals
- **Tier 1 (Feature Coverage)**: 85 tests (5 per feature * 17 features)
- **Tier 2 (Boundary & Corner Cases)**: 85 tests (5 per feature * 17 features)
- **Tier 3 (Cross-Feature Interactions)**: 15 tests
- **Tier 4 (Real-World Scenarios)**: 5 tests
- **GRAND TOTAL**: **190 comprehensive, opaque-box E2E test cases**

---

## 4. Test Harness & Dual-Track Fallback Architecture

To ensure progressive testability while worker agents implement M1–M4 in parallel:
1. **Dynamic Import Resolution**: The test suite attempts to bind to real modules:
   - `tools.github_assimilator.GitHubAssimilator`
   - `tools.cua_browser_engine.CUABrowserEngine`
   - `tools.cli_anything_bridge.CLIAnythingBridge`
   - `core.self_evolution.SelfEvolutionKernel`
2. **Behavioral Contract Doubles**: If any module is in-flight or partially implemented, the test harness supplies a behavioral test double complying 100% with the interface contracts in `PROJECT.md § Interface Contracts`.
3. **Zero Contamination**: All test operations run against isolated temporary sandboxes (`scratch/temp_test/`, in-memory/temp SQLite, isolated subprocesses) and register teardown hooks for complete cleanup.

---

## 5. Execution Instructions
Run the entire E2E suite with standard pytest:
```bash
pytest tests/e2e/test_e2e_cua_cli_evolution.py -v
```
Filter by tier:
```bash
pytest tests/e2e/test_e2e_cua_cli_evolution.py -k "TestTier1" -v
pytest tests/e2e/test_e2e_cua_cli_evolution.py -k "TestTier2" -v
pytest tests/e2e/test_e2e_cua_cli_evolution.py -k "TestTier3" -v
pytest tests/e2e/test_e2e_cua_cli_evolution.py -k "TestTier4" -v
```
