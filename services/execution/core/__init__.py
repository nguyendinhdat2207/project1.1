"""
services.execution.core - Core execution logic

Modules:
    - execution_plan: Build execution plan from greedy matching result
    - amm_leg: Build and simulate AMM leg
    - savings_calculator: Calculate savings from optimal routing
"""

from .execution_plan import ExecutionPlanBuilder, LevelUsed
from .amm_leg import (
    simulate_amm_swap,
    build_amm_leg,
    get_amm_reference_price,
)
from .savings_calculator import (
    calculate_savings,
    format_savings_summary,
    validate_output,
)

__all__ = [
    "ExecutionPlanBuilder",
    "LevelUsed",
    "simulate_amm_swap",
    "build_amm_leg",
    "get_amm_reference_price",
    "calculate_savings",
    "format_savings_summary",
    "validate_output",
]
