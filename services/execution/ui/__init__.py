"""
services.execution.ui - UI and CLI components

Modules:
    - virtual_orderbook: Virtual orderbook builder for UI/CLI display
"""

from .virtual_orderbook import (
    VirtualOrderBook,
    generate_sample_cex_snapshot,
)

__all__ = [
    "VirtualOrderBook",
    "generate_sample_cex_snapshot",
]
