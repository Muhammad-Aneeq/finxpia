"""The two release gates.

Gate A (attack validity) and Gate B (benign fairness) both measure the **corpus**, not a
guardrail, and both run against the vanilla/naive pipeline for that reason. Neither can pass in
mock mode: see decision D4 and BLOCKERS.md B1.
"""

from .attack_validity import REQUIRED_SUCCESS_RATE, GateAResult, run_gate_a
from .benign_fairness import MAX_FALSE_BLOCK_RATE, GateBResult, run_gate_b

__all__ = [
    "MAX_FALSE_BLOCK_RATE",
    "REQUIRED_SUCCESS_RATE",
    "GateAResult",
    "GateBResult",
    "run_gate_a",
    "run_gate_b",
]
