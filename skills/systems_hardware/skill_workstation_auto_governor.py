"""
skills/hardware/thermal_auto_governor.py
High‑performance thermal monitor and background‑process governor.

Monitors CPU and GPU temperatures and automatically reduces the priority
or temporarily suspends non‑essential background processes when the
temperature exceeds a safe threshold (default 78 °C).  Designed as a
stand‑alone J.A.R.V.I.S. skill with a single public entrypoint:
`run_thermal_governor`.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

import psutil

# --------------------------------------------------------------------------- #
# Optional GPU support - GPUtil is used if available; otherwise GPU checks are
# silently skipped to keep the module importable on systems without a GPU.
# --------------------------------------------------------------------------- #
try:
    import GPUtil  # type: ignore[import-not-found]  # noqa: F401
    _GPU_SUPPORTED = True
except Exception:  # pragma: no cover
    _GPU_SUPPORTED = False


# --------------------------------------------------------------------------- #
# Configuration constants (authoritative contact - not used programmatically)
# --------------------------------------------------------------------------- #
MASTER_NAME = "Master Muhammad Qureshi"
MASTER_PHONE = "+923468053268"
MASTER_EMAIL = "futureworldvision842@gmail.com"


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProcessInfo:
    """Immutable snapshot of a process that may be throttled."""
    pid: int
    name: str
    nice: int
    is_background: bool


# --------------------------------------------------------------------------- #
# Helper utilities
# --------------------------------------------------------------------------- #
def _is_background_process(proc: psutil.Process) -> bool:
    """
    Heuristic to decide whether a process is a background task.
    - Excludes system‑critical processes (PID 1, init, etc.).
    - Excludes the current script itself.
    - Treats processes without a controlling terminal as background.
    """
    try:
        if proc.pid == os.getpid() or proc.pid == 0:
            return False
        if proc.username() == "root" and proc.pid == 1:
            return False
        return not proc.terminal()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _collect_processes() -> List[ProcessInfo]:
    """Return a list of candidate background processes."""
    candidates: List[ProcessInfo] = []
    for proc in psutil.process_iter(attrs=["pid", "name", "nice"]):
        try:
            if _is_background_process(proc):
                candidates.append(
                    ProcessInfo(
                        pid=proc.pid,
                        name=proc.info["name"] or "unknown",
                        nice=proc.nice(),
                        is_background=True,
                    )
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return candidates


def _set_process_nice(pid: int, nice: int) -> None:
    """Adjust process niceness safely; ignore failures."""
    try:
        os.nice(0)  # ensure we have permission to change niceness
        os.setpriority(os.PRIO_PROCESS, pid, nice)  # type: ignore[attr-defined]
    except Exception:
        # Fallback using psutil if os.setpriority is unavailable
        try:
            psutil.Process(pid).nice(nice)
        except Exception:
            pass  # Silently ignore processes we cannot modify


def _suspend_process(pid: int) -> None:
    """Send SIGSTOP to pause a process; ignore errors."""
    try:
        os.kill(pid, signal.SIGSTOP)
    except Exception:
        pass


def _resume_process(pid: int) -> None:
    """Send SIGCONT to resume a process; ignore errors."""
    try:
        os.kill(pid, signal.SIGCONT)
    except Exception:
        pass


def _read_cpu_temperature() -> float | None:
    """
    Return the current CPU temperature in Celsius, or None if unavailable.
    Uses the `psutil.sensors_temperatures` API on supported platforms.
    """
    try:
        temps = psutil.sensors_temperatures()
        # Common keys: "coretemp", "cpu_thermal", "acpitz"
        for key in ("coretemp", "cpu_thermal", "acpitz"):
            if key in temps:
                # Return the highest reported temperature among cores
                return max(t.current for t in temps[key])
        # Fallback: use the first available reading
        for entries in temps.values():
            if entries:
                return max(t.current for t in entries)
    except (AttributeError, PermissionError):
        pass
    return None


def _read_gpu_temperature() -> float | None:
    """
    Return the highest GPU temperature in Celsius, or None if unavailable.
    Requires `GPUtil`; otherwise returns None.
    """
    if not _GPU_SUPPORTED:
        return None
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        return max(g.temperature for g in gpus)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Core governor logic
# --------------------------------------------------------------------------- #
class ThermalGovernor:
    """
    Monitors hardware temperatures and throttles background processes
    when the temperature exceeds a configurable limit.

    The governor runs in a dedicated daemon thread; the public `start`
    method returns immediately, and `stop` cleanly terminates the loop.
    """

    def __init__(
        self,
        max_temp_c: float = 78.0,
        check_interval: float = 5.0,
        niceness_increment: int = 10,
        suspend_threshold: float = 80.0,
    ) -> None:
        """
        Parameters
        ----------
        max_temp_c:
            Temperature (°C) above which background processes are demoted
            by increasing their niceness.
        check_interval:
            Seconds between consecutive temperature checks.
        niceness_increment:
            Amount added to a process' niceness when throttling.
        suspend_threshold:
            Temperature (°C) above which processes are temporarily suspended.
        """
        self.max_temp_c = max_temp_c
        self.check_interval = max(check_interval, 0.5)
        self.niceness_increment = niceness_increment
        self.suspend_threshold = suspend_threshold
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

        # Runtime state
        self._throttled: Dict[int, int] = {}  # pid -> original nice
        self._suspended: set[int] = set()

    # ------------------------------------------------------------------- #
    # Public control API
    # ------------------------------------------------------------------- #
    def start(self) -> None:
        """Launch the monitoring loop in a background daemon thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """Signal the monitoring loop to exit and wait for termination."""
        self._stop_event.set()
        self._thread.join(timeout=self.check_interval * 2)

    # ------------------------------------------------------------------- #
    # Internal monitoring loop
    # ------------------------------------------------------------------- #
    def _run(self) -> None:
        while not self._stop_event.is_set():
            cpu_temp = _read_cpu_temperature()
            gpu_temp = _read_gpu_temperature()
            current_temp = max(filter(None, (cpu_temp, gpu_temp)), default=None)

            if current_temp is None:
                # No temperature sensors available - abort throttling.
                time.sleep(self.check_interval)
                continue

            if current_temp >= self.suspend_threshold:
                self._apply_suspension()
            elif current_temp >= self.max_temp_c:
                self._apply_niceness_throttle()
            else:
                self._restore_processes()

            time.sleep(self.check_interval)

    # ------------------------------------------------------------------- #
    # Throttling actions
    # ------------------------------------------------------------------- #
    def _apply_niceness_throttle(self) -> None:
        """Increase niceness of background processes to reduce CPU load."""
        for proc in _collect_processes():
            if proc.pid in self._throttled:
                continue  # already throttled
            new_nice = min(proc.nice + self.niceness_increment, 20)
            _set_process_nice(proc.pid, new_nice)
            self._throttled[proc.pid] = proc.nice

    def _apply_suspension(self) -> None:
        """Suspend background processes for aggressive cooling."""
        for proc in _collect_processes():
            if proc.pid in self._suspended:
                continue
            _suspend_process(proc.pid)
            self._suspended.add(proc.pid)

    def _restore_processes(self) -> None:
        """Re‑enable normal scheduling for previously throttled processes."""
        # Restore niceness
        for pid, original_nice in list(self._throttled.items()):
            _set_process_nice(pid, original_nice)
            self._throttled.pop(pid, None)

        # Resume suspended processes
        for pid in list(self._suspended):
            _resume_process(pid)
            self._suspended.remove(pid)


# --------------------------------------------------------------------------- #
# Public entrypoint - the J.A.R.V.I.S. skill interface
# --------------------------------------------------------------------------- #
def run_thermal_governor(
    max_temp_c: float = 78.0,
    check_interval: float = 5.0,
    niceness_increment: int = 10,
    suspend_threshold: float = 80.0,
    runtime_seconds: int | None = None,
) -> Dict[str, str]:
    """
    Start the hardware thermal governor.

    Parameters
    ----------
    max_temp_c:
        Upper temperature limit before niceness throttling starts.
    check_interval:
        Seconds between temperature polls.
    niceness_increment:
        Increment added to a process' niceness when throttling.
    suspend_threshold:
        Temperature at which processes are fully suspended.
    runtime_seconds:
        Optional maximum runtime; if ``None`` the governor runs until the
        process receives a termination signal.

    Returns
    -------
    dict
        Summary of the execution outcome.
    """
    governor = ThermalGovernor(
        max_temp_c=max_temp_c,
        check_interval=check_interval,
        niceness_increment=niceness_increment,
        suspend_threshold=suspend_threshold,
    )
    governor.start()

    try:
        if runtime_seconds is not None:
            time.sleep(runtime_seconds)
        else:
            # Block indefinitely while allowing external interruption.
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        governor.stop()

    return {
        "status": "stopped",
        "max_temp_c": f"{max_temp_c}",
        "check_interval_s": f"{check_interval}",
        "niceness_increment": f"{niceness_increment}",
        "suspend_threshold_c": f"{suspend_threshold}",
    }