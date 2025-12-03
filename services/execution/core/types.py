"""
Type definitions for Module 4: Execution Planning

Defines data classes and types used throughout the execution planning module.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from decimal import Decimal


@dataclass
class ExecutionLeg:
    """Single execution step (order or AMM swap)"""
    source: Literal['kyber', 'amm']  # Where to execute
    to: str  # Contract address to call
    calldata: str  # Encoded function call
    value: str  # ETH value sent (usually '0')
    sell_amount: str  # Input amount (raw, with decimals)
    min_buy_amount: str  # Minimum output amount (raw, with decimals)
    meta: Optional[Dict[str, Any]] = None  # Extra metadata (order_id, pool, slippage, etc.)


@dataclass
class MatchingResult:
    """Result from greedy matching algorithm"""
    legs: List[ExecutionLeg]  # List of execution steps
    remaining_in: str  # Unmatched amount
    kyber_amount: str  # Amount matched from Kyber/synthetic orderbook
    amm_amount: str  # Amount to swap via AMM
    total_out_from_matching: str  # Total output from matched legs


@dataclass
class SavingsData:
    """Savings calculation results"""
    amm_reference_out: Decimal  # Output if swapped 100% via AMM
    expected_total_out: Decimal  # Combined output (orderbook + AMM)
    savings_before_fee: Decimal  # Savings before performance fee
    performance_fee_bps: int  # Performance fee in basis points
    performance_fee_amount: Decimal  # Performance fee in token units
    savings_after_fee: Decimal  # Savings after performance fee
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'amm_reference_out': str(self.amm_reference_out),
            'expected_total_out': str(self.expected_total_out),
            'savings_before_fee': str(self.savings_before_fee),
            'performance_fee_bps': self.performance_fee_bps,
            'performance_fee_amount': str(self.performance_fee_amount),
            'savings_after_fee': str(self.savings_after_fee),
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan for UniHybrid API response"""
    split: Dict[str, Any]  # {amount_in_total, amount_in_on_orderbook, amount_in_on_amm}
    legs: List[ExecutionLeg]  # Execution steps
    hook_data_args: Dict[str, Any]  # Arguments for hook_data
    hook_data: str  # ABI encoded hook_data (hex string)
    savings: SavingsData  # Savings metrics
    min_total_out: str  # Minimum output with slippage tolerance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'split': self.split,
            'legs': [
                {
                    'source': leg.source,
                    'to': leg.to,
                    'calldata': leg.calldata,
                    'value': leg.value,
                    'sell_amount': leg.sell_amount,
                    'min_buy_amount': leg.min_buy_amount,
                    'meta': leg.meta or {},
                }
                for leg in self.legs
            ],
            'hook_data_args': self.hook_data_args,
            'hook_data': self.hook_data,
            'savings': self.savings.to_dict(),
            'min_total_out': self.min_total_out,
        }
