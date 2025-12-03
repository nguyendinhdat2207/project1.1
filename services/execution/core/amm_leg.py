"""
amm_leg.py - Build AMM execution leg and simulate swaps

Provides functions to:
1. Simulate swap via Uniswap V3
2. Build ExecutionLeg for AMM swap
3. Calculate expected output from AMM
"""

from decimal import Decimal
from typing import Optional, Tuple
from web3 import Web3

from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool, price_from_sqrtprice, get_pool_tokens_and_decimals
from .types import ExecutionLeg


def simulate_amm_swap(
    pool_address: str,
    amount_in: int,
    token_in_decimals: int,
    token_out_decimals: int,
) -> Decimal:
    """
    Simulate swap output amount via Uniswap V3 AMM.
    
    Uses current sqrtPriceX96 to estimate output.
    Note: This is an approximation; actual output may differ due to slippage.
    
    Args:
        pool_address: Uniswap V3 pool address
        amount_in: Input amount (raw, smallest units)
        token_in_decimals: Decimals of input token (must match one of the pool's tokens)
        token_out_decimals: Decimals of output token (must match the other pool's token)
    
    Returns:
        Estimated output amount (as Decimal, in raw units)
    
    Important:
        - Pool: token0=ETH (18 decimals), token1=USDT (6 decimals)
        - If token_in_decimals=6 (USDT) and token_out_decimals=18 (ETH):
          Swap USDT→ETH: amount_out = amount_in / price
        - If token_in_decimals=18 (ETH) and token_out_decimals=6 (USDT):
          Swap ETH→USDT: amount_out = amount_in * price
    """
    try:
        price_data = get_price_for_pool(pool_address)
        # price = token1 per token0 (e.g., USDT per ETH = 2793.33)
        # token0 = ETH (18 decimals), token1 = USDT (6 decimals)
        
        price = price_data['price_eth_per_usdt']
        
        # Get pool token decimals
        token0_decimals = price_data['decimals0']  # ETH = 18
        token1_decimals = price_data['decimals1']  # USDT = 6
        
        # Convert amount_in to human-readable
        amount_in_human = Decimal(amount_in) / Decimal(10) ** Decimal(token_in_decimals)
        
        # Determine swap direction based on token decimals
        if token_in_decimals == token0_decimals:
            # token_in = token0 (ETH), token_out = token1 (USDT)
            # amount_out = amount_in_human * price
            # Example: 1 ETH * 2793.33 = 2793.33 USDT
            amount_out_human = amount_in_human * price
        elif token_in_decimals == token1_decimals:
            # token_in = token1 (USDT), token_out = token0 (ETH)
            # amount_out = amount_in_human / price
            # Example: 5000 USDT / 2793.33 = 1.789 ETH
            amount_out_human = amount_in_human / price
        else:
            raise ValueError(
                f"token_in_decimals ({token_in_decimals}) does not match pool token decimals "
                f"(token0: {token0_decimals}, token1: {token1_decimals})"
            )
        
        # Convert back to raw
        amount_out_raw = amount_out_human * Decimal(10) ** Decimal(token_out_decimals)
        
        return amount_out_raw
    
    except Exception as e:
        print(f"❌ Error simulating AMM swap: {e}")
        raise


def build_amm_leg(
    pool_address: str,
    router_address: str,
    amount_in: int,
    min_amount_out: int,
    receiver: str,
    deadline: int,  # Block timestamp deadline
    token_in: str,
    token_out: str,
) -> ExecutionLeg:
    """
    Build AMM execution leg.
    
    For now, this creates a placeholder leg.
    In production, encode actual swap calldata (e.g., SwapRouter02.exactInputSingle).
    
    Args:
        pool_address: Uniswap V3 pool
        router_address: SwapRouter or SwapRouter02 address
        amount_in: Input amount (raw)
        min_amount_out: Min output (after slippage)
        receiver: Address to receive output
        deadline: Tx deadline
        token_in: Input token address
        token_out: Output token address
    
    Returns:
        ExecutionLeg for AMM swap
    """
    # TODO: In production, encode the actual Uniswap V3 swap calldata
    # For now, placeholder
    calldata = "0x414bf389"  # Placeholder: SwapRouter.exactInputSingle selector
    
    leg = ExecutionLeg(
        source='amm',
        to=router_address,
        calldata=calldata,
        value='0',
        sell_amount=str(amount_in),
        min_buy_amount=str(min_amount_out),
        meta={
            'pool_address': pool_address,
            'token_in': token_in,
            'token_out': token_out,
            'receiver': receiver,
            'deadline': deadline,
        }
    )
    
    return leg


def get_amm_reference_price(
    pool_address: str,
    amount_in: int,
    token_in_decimals: int,
    token_out_decimals: int,
) -> Tuple[Decimal, int]:
    """
    Get reference output if entire amountIn is swapped via AMM.
    
    Returns:
        (amount_out, decimals_out)
    """
    amount_out = simulate_amm_swap(
        pool_address=pool_address,
        amount_in=amount_in,
        token_in_decimals=token_in_decimals,
        token_out_decimals=token_out_decimals,
    )
    
    return amount_out, token_out_decimals
