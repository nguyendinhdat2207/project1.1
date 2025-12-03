"""
services/execution - Execution plan building for UniHybrid

Module 4: Execution Plan Builder
- Build complete execution plan from greedy match results
- Encode hook_data for smart contract
- Calculate savings and performance fees

Submodules:
    - core: Core execution logic (execution_plan, amm_leg, savings_calculator)
    - ui: UI and CLI components (virtual_orderbook)
"""

from .core import ExecutionPlanBuilder, LevelUsed
from .ui import VirtualOrderBook, generate_sample_cex_snapshot

__all__ = [
    'ExecutionPlanBuilder',
    'LevelUsed',
    'VirtualOrderBook',
    'generate_sample_cex_snapshot',
]
