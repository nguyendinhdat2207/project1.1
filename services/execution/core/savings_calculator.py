"""
savings_calculator.py - Calculate savings from optimal routing

Compares Kyber+AMM route vs pure AMM reference.
Applies performance fee and calculates final min_out with slippage.
"""

from decimal import Decimal
from typing import Optional

from .types import MatchingResult, SavingsData


def calculate_savings(
    amount_in: int,
    amm_reference_out: int,  # Output if swapped entire amount via AMM
    matching_result: MatchingResult,  # Greedy matching result with legs
    amm_out_for_remaining: Optional[int] = None,  # Output from AMM leg (if any)
    performance_fee_bps: int = 0,  # Fee in basis points (e.g., 50 = 0.5%)
    max_slippage_bps: int = 100,  # Max allowed slippage in basis points (1% default)
) -> SavingsData:
    """
    Calculate savings and fees.
    
    Logic:
    1. expected_total_out = sum of all leg min_buy_amounts
    2. savings_before_fee = expected_total_out - amm_reference_out
    3. performance_fee = max(0, savings_before_fee * performance_fee_bps / 10000)
    4. savings_after_fee = max(0, savings_before_fee - performance_fee)
    5. min_total_out = amm_reference_out * (1 - max_slippage_bps / 10000)
    
    Args:
        amount_in: Total input amount (raw)
        amm_reference_out: Reference output (pure AMM swap)
        matching_result: Result from greedy matching
        amm_out_for_remaining: Output from AMM leg if remainingIn > 0
        performance_fee_bps: Fee in basis points
        max_slippage_bps: Max slippage in basis points
    
    Returns:
        SavingsData with full calculation
    """
    # Sum all leg min_buy_amounts for expected output
    expected_total_out = Decimal(0)
    for leg in matching_result.legs:
        expected_total_out += Decimal(leg.min_buy_amount)
    
    # If there's an AMM leg for remaining amount
    if amm_out_for_remaining is not None and amm_out_for_remaining > 0:
        expected_total_out += Decimal(amm_out_for_remaining)
    
    # Reference output
    amm_ref_out_decimal = Decimal(amm_reference_out)
    
    # Savings before fee (can be negative if worse than AMM)
    savings_before_fee = expected_total_out - amm_ref_out_decimal
    
    # Calculate performance fee (only on positive savings)
    if savings_before_fee > 0:
        performance_fee = (savings_before_fee * Decimal(performance_fee_bps)) / Decimal(10000)
    else:
        performance_fee = Decimal(0)
    
    # Savings after fee
    savings_after_fee = savings_before_fee - performance_fee
    
    # Min output with slippage protection (based on AMM reference)
    slippage_factor = 1 - (Decimal(max_slippage_bps) / Decimal(10000))
    min_total_out = amm_ref_out_decimal * slippage_factor
    
    result = SavingsData(
        amm_reference_out=str(int(amm_ref_out_decimal)),
        expected_total_out=str(int(expected_total_out)),
        savings_before_fee=str(int(savings_before_fee)),
        performance_fee_bps=performance_fee_bps,
        performance_fee=str(int(performance_fee)),
        savings_after_fee=str(int(savings_after_fee)),
        min_total_out=str(int(min_total_out)),
        max_slippage_bps=max_slippage_bps,
    )
    
    return result


def format_savings_summary(savings: SavingsData) -> str:
    """
    Format savings data for pretty printing.
    
    Args:
        savings: SavingsData object
    
    Returns:
        Formatted string summary
    """
    amm_ref = int(savings.amm_reference_out)
    expected = int(savings.expected_total_out)
    savings_bf = int(savings.savings_before_fee)
    fee = int(savings.performance_fee)
    savings_af = int(savings.savings_after_fee)
    min_out = int(savings.min_total_out)
    
    summary = f"""
    ================================================================================
    💰 SAVINGS ANALYSIS
    ================================================================================
    
    📊 Reference (Pure AMM):
       Expected Output: {amm_ref:,} (if entire amountIn swapped via AMM)
    
    📊 Optimized Route (Kyber + AMM):
       Expected Output: {expected:,}
    
    📈 Savings Calculation:
       Savings (before fee):  {savings_bf:+,}
       Performance Fee ({savings.performance_fee_bps} bps): {fee:,}
       Savings (after fee):   {savings_af:+,}
    
    🛡️  Slippage Protection:
       Max Slippage ({savings.max_slippage_bps} bps): {int(amm_ref - int(savings.min_total_out)):,}
       Min Output to Accept: {min_out:,}
    
    ================================================================================
    """
    
    return summary


def validate_output(
    expected_out: int,
    min_out: int,
    received_out: Optional[int] = None,
) -> bool:
    """
    Validate if output meets minimum requirements.
    
    Args:
        expected_out: Expected output amount
        min_out: Minimum acceptable output (with slippage)
        received_out: Actually received amount (if execution already done)
    
    Returns:
        True if valid, False otherwise
    """
    if received_out is not None:
        return received_out >= min_out
    
    # If not executed yet, check if expected meets minimum
    return expected_out >= min_out
