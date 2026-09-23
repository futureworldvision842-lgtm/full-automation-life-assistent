"""Typed provenance and execution gating for all market intelligence.

Every value shown to a trader should say where it came from, when it was
observed, whether it is synthetic, and whether it is safe to use in an order
decision.  This module deliberately contains no networking code; feed adapters
wrap their own payloads in :class:`DataEnvelope` objects.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple


class DataMode(str, Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    HISTORICAL = "HISTORICAL"
    PAPER = "PAPER"
    SYNTHETIC = "SYNTHETIC"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class DataEnvelope:
    source: str
    mode: DataMode
    observed_at: datetime
    received_at: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    actionable: bool = False
    license_note: str = ""
    disclaimer: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source is required")
        for value in (self.observed_at, self.received_at):
            if value.tzinfo is None:
                raise ValueError("timestamps must be timezone-aware")
        if self.confidence is not None and (
            not math.isfinite(float(self.confidence)) or not 0.0 <= float(self.confidence) <= 1.0
        ):
            raise ValueError("confidence must be a finite value from 0.0 to 1.0")
        if self.mode in {DataMode.PAPER, DataMode.SYNTHETIC, DataMode.UNAVAILABLE} and self.actionable:
            raise ValueError(f"{self.mode.value} data cannot be marked actionable")

    @property
    def age_seconds(self) -> float:
        return max(0.0, (datetime.now(timezone.utc) - self.observed_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["mode"] = self.mode.value
        result["observed_at"] = self.observed_at.isoformat()
        result["received_at"] = self.received_at.isoformat()
        result["age_seconds"] = round(self.age_seconds, 3)
        return result


def execution_data_gate(
    envelopes: Iterable[DataEnvelope],
    *,
    max_age_seconds: float,
    required_sources: Optional[Iterable[str]] = None,
) -> Tuple[bool, List[str]]:
    """Fail closed unless all required inputs are observed, fresh, and actionable."""
    items = list(envelopes)
    reasons: List[str] = []
    if not items:
        return False, ["No provenance envelopes were supplied"]

    by_source = {item.source: item for item in items}
    for source in required_sources or []:
        if source not in by_source:
            reasons.append(f"Required source missing: {source}")

    for item in items:
        if item.mode not in {DataMode.LIVE, DataMode.DELAYED}:
            reasons.append(f"{item.source} is {item.mode.value}, not live/delayed observed data")
        if not item.actionable:
            reasons.append(f"{item.source} is explicitly non-actionable")
        if item.age_seconds > max_age_seconds:
            reasons.append(f"{item.source} is stale ({item.age_seconds:.1f}s > {max_age_seconds:.1f}s)")

    return not reasons, reasons
