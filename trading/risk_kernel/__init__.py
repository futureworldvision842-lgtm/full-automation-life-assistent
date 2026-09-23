"""
trading.risk_kernel package — Deterministic Institutional Risk Kernel.
"""

from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel

__all__ = ["DeterministicRiskKernel", "get_risk_kernel"]
