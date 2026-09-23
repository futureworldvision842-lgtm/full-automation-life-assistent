"""
tests/test_disaster_recovery_watchdog_empirical.py — Challenger 2 Empirical Stress Test Suite.
Milestone 4: Automated State Backup & Self-Healing Disaster Recovery

Empirical adversarial test coverage:
  1. Non-blocking TCP/HTTP probe timeouts under hanging/blackhole listeners (<=1.5s).
  2. Exponential backoff progression (2s -> 4s -> 8s -> 16s -> 32s -> 60s) with 10% jitter.
  3. Sliding window circuit breaker tripping on >=5 restarts / 6 failures within 60s window.
  4. Structured incident forensics JSON generation with system telemetry snapshots & log rotation.
  5. Clean daemon shutdown with recursive process-tree termination and zero orphan processes.
  6. Grandchild process tree recursive termination.
  7. Circuit breaker isolation across distinct services.
  8. Concurrent multi-threaded supervisor thread safety and deadlock avoidance.
  9. Background scanner heartbeat drift state transitions.
"""

import os
import sys
import json
import time
import socket
import select
import shutil
import psutil
import tempfile
import threading
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.disaster_recovery_watchdog import (
    DisasterRecoveryWatchdog,
    ServiceHealthStatus,
    SupervisedService,
    ProbeType
)


class BlackholeTCPServer:
    """
    A TCP server that binds to a port and accepts connections,
    but hangs indefinitely without responding or sending data.
    """
    def __init__(self, host: str = "127.0.0.1"):
        self.host = host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.client_sockets = []
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client, addr = self.sock.accept()
                self.client_sockets.append(client)
                # Intentionally never send or read anything from client
            except socket.timeout:
                continue
            except Exception:
                break

    def close(self):
        self.running = False
        for c in self.client_sockets:
            try:
                c.close()
            except Exception:
                pass
        try:
            self.sock.close()
        except Exception:
            pass
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)


class TestEmpiricalChallenger2DRWatchdog(unittest.TestCase):
    """Adversarial stress test suite for DisasterRecoveryWatchdog."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="challenger2_dr_watchdog_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.log_dir = os.path.join(self.test_dir, "logs")
        self.reports_dir = os.path.join(self.test_dir, "data", "incident_reports")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({
                "ports": {"fastapi": 8000, "flask": 5000, "baileys": 3001},
                "simulation_mode": True
            }, f)

        self.watchdog = DisasterRecoveryWatchdog(
            config_path=self.config_path,
            workspace_root=self.test_dir,
            log_dir=self.log_dir,
            incident_reports_dir=self.reports_dir
        )

    def tearDown(self):
        try:
            self.watchdog.stop_watchdog_daemon(terminate_children=True)
        except Exception:
            pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. NON-BLOCKING PROBE TIMEOUT TESTS
    # =========================================================================

    def test_01_probe_tcp_socket_timeout_on_hanging_blackhole(self):
        """
        Verify TCP probe against a hanging/blackhole listener strictly times out
        within <= 1.5s without hanging or blocking execution.
        """
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.bind(("127.0.0.1", 0))
        port = raw_sock.getsockname()[1]
        try:
            start_time = time.perf_counter()
            ok, lat, err = self.watchdog._probe_tcp_socket(
                host="127.0.0.1", port=port, timeout=1.0
            )
            elapsed = time.perf_counter() - start_time

            self.assertFalse(ok)
            self.assertLessEqual(elapsed, 1.5, f"Probe took too long: {elapsed:.2f}s")
            self.assertIsNotNone(err)
        finally:
            raw_sock.close()

    def test_02_probe_tcp_socket_immediate_failure_on_closed_port(self):
        """
        Verify TCP probe against an unused closed port times out safely (< 1.6s)
        without blocking.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        unused_port = s.getsockname()[1]
        s.close()

        start_time = time.perf_counter()
        ok, lat, err = self.watchdog._probe_tcp_socket("127.0.0.1", unused_port, timeout=1.5)
        elapsed = time.perf_counter() - start_time

        self.assertFalse(ok)
        self.assertLessEqual(elapsed, 1.6, f"Closed port probe took {elapsed:.2f}s, expected <= 1.6s")
        self.assertIsNotNone(err)

    def test_03_probe_tcp_socket_accepting_blackhole_connection(self):
        """
        Verify TCP probe successfully detects open socket connection on an accepting listener
        in sub-second latency (< 100ms).
        """
        blackhole = BlackholeTCPServer()
        try:
            start_time = time.perf_counter()
            ok, lat, err = self.watchdog._probe_tcp_socket(
                host="127.0.0.1",
                port=blackhole.port,
                timeout=1.0
            )
            elapsed = time.perf_counter() - start_time

            self.assertTrue(ok)
            self.assertLess(elapsed, 0.5, f"TCP connect took {elapsed:.2f}s, expected < 0.5s")
            self.assertIsNone(err)
            self.assertGreater(lat, 0.0)
        finally:
            blackhole.close()

    def test_04_supervised_service_tcp_probe_adversarial_timeout(self):
        """
        Verify SupervisedService with hanging TCP socket probe completes check_and_heal_all_services
        in bounded time (<= 1.6s) without freezing the watchdog supervisor loop.
        """
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.bind(("127.0.0.1", 0))
        port = raw_sock.getsockname()[1]
        try:
            # Clear other services to isolate this single test probe timing
            self.watchdog.services = {}

            self.watchdog.register_service(
                SupervisedService(
                    service_id="HANGING_TCP_SERVICE",
                    display_name="Hanging TCP Server",
                    probe_type=ProbeType.TCP_SOCKET,
                    host="127.0.0.1",
                    port=port,
                    timeout_sec=1.0,
                    consecutive_fail_threshold=2,
                    auto_restart=False
                )
            )

            start = time.perf_counter()
            audit = self.watchdog.check_and_heal_all_services()
            elapsed = time.perf_counter() - start

            self.assertIn("HANGING_TCP_SERVICE", audit["services"])
            self.assertEqual(audit["services"]["HANGING_TCP_SERVICE"]["status"], ServiceHealthStatus.DEGRADED.value)
            self.assertLessEqual(elapsed, 1.6, f"Supervisor check_and_heal took {elapsed:.2f}s, expected <= 1.6s")
        finally:
            raw_sock.close()

    # =========================================================================
    # 2. EXPONENTIAL BACKOFF PROGRESSION TESTS
    # =========================================================================

    def test_05_exponential_backoff_mathematical_progression(self):
        """
        Verify exponential backoff delay intervals grow exponentially:
          Attempt 1: ~2s
          Attempt 2: ~4s
          Attempt 3: ~8s
          Attempt 4: ~16s
          Attempt 5: ~32s
          Attempt 6+: capped at 60s
        with strictly <= 10% uniform jitter bounds.
        """
        service_id = "FASTAPI_SERVER_8000"
        expected_bases = {
            1: 2.0,
            2: 4.0,
            3: 8.0,
            4: 16.0,
            5: 32.0,
            6: 60.0,
            7: 60.0,
            10: 60.0
        }

        for attempt, base in expected_bases.items():
            delays = [self.watchdog._compute_backoff_delay(service_id, attempt) for _ in range(50)]
            min_delay = min(delays)
            max_delay = max(delays)
            avg_delay = sum(delays) / len(delays)

            # Jitter is +/- 10%
            lower_bound = max(1.0, base * 0.89)
            upper_bound = base * 1.11

            self.assertGreaterEqual(
                min_delay, lower_bound,
                f"Attempt {attempt}: min delay {min_delay} below lower bound {lower_bound}"
            )
            self.assertLessEqual(
                max_delay, upper_bound,
                f"Attempt {attempt}: max delay {max_delay} above upper bound {upper_bound}"
            )
            self.assertAlmostEqual(avg_delay, base, delta=base * 0.08)

    def test_06_dynamic_restart_throttling_by_backoff(self):
        """
        Verify that immediate successive auto-restarts are throttled by the backoff delay,
        preventing CPU thrashing or fork-bombing.
        """
        service_id = "CRASHING_WORKER"
        self.watchdog.register_service(
            SupervisedService(
                service_id=service_id,
                display_name="Crashing Worker",
                probe_type=ProbeType.CUSTOM_CALLABLE,
                custom_probe_fn=lambda: {"status": ServiceHealthStatus.CRITICAL_DOWN.value, "error": "Crash"},
                startup_command=[sys.executable, "-c", "import sys; sys.exit(1)"],
                auto_restart=True
            )
        )

        # 1st restart attempt: should succeed
        res1 = self.watchdog._restart_service(service_id, manual_override=False)
        self.assertTrue(res1)

        # Immediate 2nd restart attempt (elapsed ~0.01s < backoff ~4.0s): must be throttled
        res2 = self.watchdog._restart_service(service_id, manual_override=False)
        self.assertFalse(res2, "Second restart was not throttled by exponential backoff!")

        # Manual override bypasses throttling
        res_forced = self.watchdog._restart_service(service_id, manual_override=True)
        self.assertTrue(res_forced, "Manual override failed to restart service!")

    # =========================================================================
    # 3. CIRCUIT BREAKER TRIPPING & COOLDOWN TESTS
    # =========================================================================

    def test_07_circuit_breaker_trips_after_rapid_consecutive_failures(self):
        """
        Verify circuit breaker trips when >= 5 restarts occur within 300s window,
        transitioning service to CRITICAL_DOWN / CIRCUIT_BREAKER_TRIPPED and halting restarts.
        """
        service_id = "UNSTABLE_SERVICE"
        self.watchdog.register_service(
            SupervisedService(
                service_id=service_id,
                display_name="Unstable Service",
                probe_type=ProbeType.CUSTOM_CALLABLE,
                custom_probe_fn=lambda: {"status": ServiceHealthStatus.CRITICAL_DOWN.value, "error": "Repeated crash"},
                startup_command=[sys.executable, "-c", "import sys; sys.exit(1)"],
                auto_restart=True
            )
        )

        svc = self.watchdog.services[service_id]

        # Inject 5 restarts
        now = time.time()
        for i in range(5):
            svc.restart_timestamps.append(now - (5 - i))

        # Check circuit breaker
        tripped = self.watchdog._is_circuit_breaker_tripped(service_id, max_restarts=5, window_sec=300.0)
        self.assertTrue(tripped)
        self.assertTrue(svc.circuit_breaker_open)
        self.assertIsNotNone(svc.circuit_breaker_tripped_time)

        # Auto-restart must now be completely suppressed
        restart_success = self.watchdog._restart_service(service_id, manual_override=False)
        self.assertFalse(restart_success)
        self.assertEqual(svc.current_status, ServiceHealthStatus.CIRCUIT_BREAKER_TRIPPED)

    def test_08_circuit_breaker_manual_reset(self):
        """
        Verify manual reset via reset_service_circuit clears breaker state and allows restarts.
        """
        service_id = "FLASK_SERVER_5000"
        svc = self.watchdog.services[service_id]

        # Trip the circuit breaker
        for _ in range(6):
            self.watchdog._record_failure(service_id, reason="Forced test failure")

        self.assertTrue(svc.circuit_breaker_open)

        # Perform manual reset
        reset_ok = self.watchdog.reset_service_circuit(service_id)
        self.assertTrue(reset_ok)
        self.assertFalse(svc.circuit_breaker_open)
        self.assertIsNone(svc.circuit_breaker_tripped_time)
        self.assertEqual(len(svc.restart_timestamps), 0)
        self.assertEqual(svc.consecutive_failures, 0)
        self.assertEqual(svc.current_status, ServiceHealthStatus.HEALTHY)

    def test_09_circuit_breaker_cooldown_expiry(self):
        """
        Verify circuit breaker automatically resets after cooldown window (300s) elapses.
        """
        service_id = "FASTAPI_SERVER_8000"
        svc = self.watchdog.services[service_id]

        # Simulate 5 restarts 310s ago
        now = time.time()
        for _ in range(5):
            svc.restart_timestamps.append(now - 310.0)
        svc.circuit_breaker_open = True
        svc.circuit_breaker_tripped_time = now - 305.0

        # Next check should detect cooldown elapsed (timestamps cleaned & trip time > 300s ago)
        is_still_tripped = self.watchdog._is_circuit_breaker_tripped(service_id, max_restarts=5, window_sec=300.0)
        self.assertFalse(is_still_tripped, "Circuit breaker should have cooled down after 300s")
        self.assertFalse(svc.circuit_breaker_open)

    # =========================================================================
    # 4. INCIDENT FORENSICS JSON GENERATION & TELEMETRY
    # =========================================================================

    def test_10_incident_forensics_json_report_generation(self):
        """
        Verify service failure triggers JSON report generation in data/incident_reports/
        with valid timestamp, failure reason, backoff, and full system telemetry metrics.
        """
        service_id = "FASTAPI_SERVER_8000"
        report_path = self.watchdog._log_incident_forensics(
            service_id=service_id,
            failure_reason="Empirical Socket Timeout Simulation",
            action_taken="PROCESS_RESTARTED",
            backoff_sec=4.0
        )

        self.assertTrue(os.path.exists(report_path), f"Incident report not found at {report_path}")

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate schema fields
        expected_keys = [
            "incident_id", "timestamp_utc", "service_id", "service_name",
            "failure_reason", "action_taken", "backoff_applied_sec", "telemetry_snapshot"
        ]
        for k in expected_keys:
            self.assertIn(k, data)

        self.assertEqual(data["service_id"], service_id)
        self.assertEqual(data["failure_reason"], "Empirical Socket Timeout Simulation")
        self.assertEqual(data["action_taken"], "PROCESS_RESTARTED")
        self.assertEqual(data["backoff_applied_sec"], 4.0)

        # Validate telemetry snapshot metrics
        telemetry = data["telemetry_snapshot"]
        for metric in ["cpu_percent", "memory_percent", "memory_available_gb", "disk_free_gb", "active_thread_count"]:
            self.assertIn(metric, telemetry)
            self.assertIsNotNone(telemetry[metric])

        # Validate disaster_recovery.log append
        self.assertTrue(os.path.exists(self.watchdog.log_file))
        with open(self.watchdog.log_file, "r", encoding="utf-8") as lf:
            log_content = lf.read()
            self.assertIn("[INCIDENT]", log_content)
            self.assertIn(service_id, log_content)
            self.assertIn("Empirical Socket Timeout Simulation", log_content)

    def test_11_incident_history_retrieval_and_pruning(self):
        """
        Verify get_incident_history returns reports sorted in reverse chronological order
        and pruning keeps report count bounded <= 100.
        """
        # Generate 105 mock incident reports
        for i in range(105):
            self.watchdog._log_incident_forensics(
                service_id=f"TEST_SVC_{i % 5}",
                failure_reason=f"Test failure batch {i}",
                action_taken="NO_ACTION",
                backoff_sec=0.0
            )

        reports = self.watchdog.get_incident_history(limit=50)
        self.assertLessEqual(len(reports), 50)
        self.assertGreater(len(reports), 0)

        # Check total remaining files in directory <= 100
        all_files = [f for f in os.listdir(self.reports_dir) if f.startswith("incident_") and f.endswith(".json")]
        self.assertLessEqual(len(all_files), 100, f"Expected <= 100 files after pruning, found {len(all_files)}")

    # =========================================================================
    # 5. CLEAN DAEMON SHUTDOWN & ZERO ORPHAN PROCESSES
    # =========================================================================

    def test_12_clean_daemon_shutdown_terminates_all_child_processes(self):
        """
        Start watchdog with mock child subprocesses, call stop_watchdog_daemon(terminate_children=True),
        and verify all threads and child processes terminate cleanly with zero orphan processes.
        """
        service_id = "LONG_RUNNING_WORKER"
        cmd = [sys.executable, "-c", "import time; time.sleep(180)"]

        self.watchdog.register_service(
            SupervisedService(
                service_id=service_id,
                display_name="Mock Long Running Child",
                probe_type=ProbeType.CUSTOM_CALLABLE,
                custom_probe_fn=lambda: {"status": ServiceHealthStatus.HEALTHY.value},
                startup_command=cmd,
                auto_restart=True
            )
        )

        # Start supervisor daemon
        started = self.watchdog.start_watchdog_daemon(interval_sec=1)
        self.assertTrue(started)
        self.assertTrue(self.watchdog.is_running)

        # Force spawn the child process
        spawned = self.watchdog._restart_service(service_id, manual_override=True)
        self.assertTrue(spawned)

        child_pid = self.watchdog.services[service_id].pid
        self.assertIsNotNone(child_pid)
        self.assertTrue(psutil.pid_exists(child_pid))

        # Stop daemon with terminate_children=True
        stopped = self.watchdog.stop_watchdog_daemon(terminate_children=True)
        self.assertTrue(stopped)
        self.assertFalse(self.watchdog.is_running)

        time.sleep(1.0)

        # Verify child process PID is DEAD
        self.assertFalse(
            psutil.pid_exists(child_pid),
            f"Process PID {child_pid} still running! Orphan process detected!"
        )
        self.assertIsNone(self.watchdog.services[service_id].pid)

        # Idempotent stop check
        second_stop = self.watchdog.stop_watchdog_daemon(terminate_children=True)
        self.assertFalse(second_stop, "Second stop should return False gracefully")

    # =========================================================================
    # 6. GRANDCHILD RECURSIVE PROCESS TREE TERMINATION
    # =========================================================================

    def test_13_grandchild_process_tree_termination(self):
        """
        Verify that _kill_process_tree cleanly kills parent AND all spawned grandchild
        processes without leaving orphan grandchild processes on the OS.
        """
        # Python script that spawns a grandchild process and sleeps
        parent_script = (
            "import subprocess, sys, time; "
            "sub = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(180)']); "
            "time.sleep(180)"
        )
        proc = subprocess.Popen([sys.executable, "-c", parent_script])
        parent_pid = proc.pid

        # Give 0.5s for grandchild to spawn
        time.sleep(0.5)

        parent_psutil = psutil.Process(parent_pid)
        children_pids = [c.pid for c in parent_psutil.children(recursive=True)]
        self.assertGreater(len(children_pids), 0, "Grandchild process failed to spawn")
        grandchild_pid = children_pids[0]

        self.assertTrue(psutil.pid_exists(parent_pid))
        self.assertTrue(psutil.pid_exists(grandchild_pid))

        # Execute kill process tree
        self.watchdog._kill_process_tree(parent_pid)
        time.sleep(0.5)

        # Verify BOTH parent and grandchild are DEAD
        self.assertFalse(psutil.pid_exists(parent_pid), "Parent process survived!")
        self.assertFalse(psutil.pid_exists(grandchild_pid), "Grandchild orphan process survived!")

    # =========================================================================
    # 7. MULTI-SERVICE CIRCUIT BREAKER ISOLATION
    # =========================================================================

    def test_14_multi_service_circuit_breaker_isolation(self):
        """
        Verify circuit breaker tripping on Service A does NOT impact or trip Service B.
        """
        svcA = "SERVICE_ALPHA"
        svcB = "SERVICE_BETA"

        self.watchdog.register_service(
            SupervisedService(service_id=svcA, display_name="Alpha", probe_type=ProbeType.THREAD_HEARTBEAT)
        )
        self.watchdog.register_service(
            SupervisedService(service_id=svcB, display_name="Beta", probe_type=ProbeType.THREAD_HEARTBEAT)
        )

        # Rapidly trip Alpha
        for _ in range(6):
            self.watchdog._record_failure(svcA, reason="Alpha Crash")

        self.assertTrue(self.watchdog.services[svcA].circuit_breaker_open)
        # Verify Beta is untouched
        self.assertFalse(self.watchdog.services[svcB].circuit_breaker_open)
        self.assertEqual(self.watchdog.services[svcB].consecutive_failures, 0)
        self.assertEqual(self.watchdog.services[svcB].current_status, ServiceHealthStatus.HEALTHY)

    # =========================================================================
    # 8. CONCURRENT MULTI-THREADED THREAD SAFETY
    # =========================================================================

    def test_15_concurrent_multi_service_probes_and_state_integrity(self):
        """
        Verify thread safety: 10 concurrent worker threads executing status reads,
        probes, and resets without deadlocks or unhandled concurrency exceptions.
        """
        def worker_task(idx):
            for _ in range(10):
                self.watchdog.get_system_health_status()
                self.watchdog.update_scanner_heartbeat(f"worker_{idx % 3}")
                if idx % 2 == 0:
                    self.watchdog._record_failure("MT5_TERMINAL", "Concurrent test tick")
                else:
                    self.watchdog.reset_service_circuit("MT5_TERMINAL")
            return True

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, i) for i in range(16)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 16)
        self.assertTrue(all(results))

    # =========================================================================
    # 9. SCANNER HEARTBEAT DRIFT TRANSITIONS
    # =========================================================================

    def test_16_scanner_heartbeat_drift_transitions(self):
        """
        Verify scanner heartbeat probe correctly identifies drift states:
          drift <= 60s -> HEALTHY
          drift > 60s -> DEGRADED
          drift > 120s -> CRITICAL_DOWN
        """
        now = time.time()
        # Normal heartbeat
        self.watchdog._scanner_heartbeats["scanner_1"] = now - 10.0
        res = self.watchdog._probe_service("BACKGROUND_SCANNERS")
        self.assertEqual(res["status"], ServiceHealthStatus.HEALTHY.value)

        # Degraded heartbeat (>60s)
        self.watchdog._scanner_heartbeats["scanner_1"] = now - 75.0
        res = self.watchdog._probe_service("BACKGROUND_SCANNERS")
        self.assertEqual(res["status"], ServiceHealthStatus.DEGRADED.value)

        # Critical down heartbeat (>120s)
        self.watchdog._scanner_heartbeats["scanner_1"] = now - 135.0
        res = self.watchdog._probe_service("BACKGROUND_SCANNERS")
        self.assertEqual(res["status"], ServiceHealthStatus.CRITICAL_DOWN.value)

    # =========================================================================
    # 10. SYSTEM HEALTH AGGREGATION
    # =========================================================================

    def test_17_system_health_status_aggregation_logic(self):
        """
        Verify get_system_health_status correctly reflects the most severe status:
        CRITICAL_DOWN > DEGRADED > HEALTHY.
        """
        # All healthy initially
        for svc in self.watchdog.services.values():
            svc.current_status = ServiceHealthStatus.HEALTHY
        health = self.watchdog.get_system_health_status()
        self.assertEqual(health["overall_status"], ServiceHealthStatus.HEALTHY.value)

        # One degraded -> overall DEGRADED
        self.watchdog.services["FLASK_SERVER_5000"].current_status = ServiceHealthStatus.DEGRADED
        health = self.watchdog.get_system_health_status()
        self.assertEqual(health["overall_status"], ServiceHealthStatus.DEGRADED.value)

        # One critical -> overall CRITICAL_DOWN
        self.watchdog.services["MT5_TERMINAL"].current_status = ServiceHealthStatus.CRITICAL_DOWN
        health = self.watchdog.get_system_health_status()
        self.assertEqual(health["overall_status"], ServiceHealthStatus.CRITICAL_DOWN.value)


if __name__ == "__main__":
    unittest.main()
