"""
Orderbook Service Package

This package provides synthetic orderbook generation for UniHybrid backtesting.
"""

from .synthetic_orderbook import (
    SyntheticOrderbookGenerator,
    OrderbookLevel
)

__all__ = [
    'SyntheticOrderbookGenerator',
    'OrderbookLevel'
]
