"""
UniHybrid API - Main FastAPI Application
=========================================

API endpoint cho UniHybrid execution plan.
Spec: GET /api/unihybrid/execution-plan

Author: UniHybrid Team
Date: 2025-12-03
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from decimal import Decimal
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.amm_uniswap_v3.uniswap_v3 import (
    get_price_for_pool,
    get_amm_output,
    get_pool_tokens_and_decimals
)
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="UniHybrid API",
    description="API for hybrid orderbook + AMM execution planning",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pool Registry - Hardcoded for Base mainnet
# ============================================================================

POOL_REGISTRY = {
    # WETH/USDT pool (0.3% fee) - ETH/USDT on Base
    ("0x4200000000000000000000000000000000000006", "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2"): {
        "pool": "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a",
        "fee": 3000
    },
    # Reverse direction (USDT/WETH)
    ("0xfde4c96c8593536e31f229ea8f37b2ada2699bb2", "0x4200000000000000000000000000000000000006"): {
        "pool": "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a",
        "fee": 3000
    },
    # WETH/USDC pool (0.3% fee) - Real pool on Base
    ("0x4200000000000000000000000000000000000006", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"): {
        "pool": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
        "fee": 3000
    },
    # Reverse direction (USDC/WETH)
    ("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "0x4200000000000000000000000000000000000006"): {
        "pool": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
        "fee": 3000
    },
}


def get_pool_for_pair(token_in: str, token_out: str) -> dict:
    """
    Lookup pool address for token pair.
    
    Args:
        token_in: Token input address
        token_out: Token output address
    
    Returns:
        dict: {'pool': address, 'fee': int}
    
    Raises:
        HTTPException: If pool not found
    """
    key = (token_in.lower(), token_out.lower())
    if key in POOL_REGISTRY:
        return POOL_REGISTRY[key]
    
    raise HTTPException(
        status_code=404,
        detail=f"Pool not found for pair {token_in}/{token_out}"
    )


# ============================================================================
# Main API Endpoint
# ============================================================================

@app.get("/api/unihybrid/execution-plan")
async def get_execution_plan(
    chain_id: int = Query(8453, description="Chain ID (Base mainnet = 8453)"),
    token_in: str = Query(..., description="Token input address (checksummed)"),
    token_out: str = Query(..., description="Token output address (checksummed)"),
    amount_in: str = Query(..., description="Amount to swap in base units (e.g., '1000000000000000000' for 1 ETH)"),
    receiver: str = Query(..., description="Receiver address"),
    max_slippage_bps: int = Query(100, description="Max slippage tolerance (bps). Default: 100 = 1%"),
    performance_fee_bps: int = Query(3000, description="Performance fee (bps). Default: 3000 = 30%"),
    max_matches: int = Query(8, description="Max matches in MatchingEngine. Default: 8"),
    ob_min_improve_bps: int = Query(5, description="Min orderbook improvement over AMM (bps). Default: 5"),
    me_slippage_limit: int = Query(200, description="MatchingEngine slippage limit (bps). Default: 200"),
    scenario: Optional[str] = Query("medium", description="Orderbook scenario: small, medium, large. Default: medium")
):
    """
    Get execution plan for a swap.
    
    Returns JSON with:
    - split: {amount_in_total, amount_in_on_orderbook, amount_in_on_amm}
    - legs: [{source, amount_in, expected_amount_out, effective_price, meta}, ...]
    - hook_data_args: {tokenIn, tokenOut, amountInOnOrderbook, maxMatches, slippageLimit}
    - hook_data: hex string (ABI encoded)
    - amm_reference_out: baseline output if 100% AMM
    - expected_total_out: total output from OB + AMM
    - savings_before_fee, performance_fee_amount, savings_after_fee
    - min_total_out: minimum output with slippage tolerance
    
    Example:
        GET /api/unihybrid/execution-plan?
            chain_id=8453&
            token_in=0x4200000000000000000000000000000000000006&
            token_out=0x833589fcd6edb6e08f4c7c32d4f71b54bda02913&
            amount_in=1000000000000000000&
            receiver=0x1234567890abcdef1234567890abcdef12345678&
            max_slippage_bps=100&
            performance_fee_bps=3000
    """
    try:
        # ====================================================================
        # Step 1: Validate inputs
        # ====================================================================
        
        if chain_id != 8453:
            raise HTTPException(
                status_code=400,
                detail=f"Only Base mainnet (8453) is supported. Got: {chain_id}"
            )
        
        # Parse amount_in
        try:
            swap_amount = int(amount_in)
            if swap_amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid amount_in: {e}"
            )
        
        # Validate scenario
        if scenario not in ["small", "medium", "large"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scenario: {scenario}. Must be 'small', 'medium', or 'large'"
            )
        
        # ====================================================================
        # Step 2: Get pool info
        # ====================================================================
        
        pool_info = get_pool_for_pair(token_in, token_out)
        pool_address = pool_info["pool"]
        fee = pool_info["fee"]
        
        # Get pool data and token info
        pool_data = get_price_for_pool(pool_address)
        token_info = get_pool_tokens_and_decimals(pool_address)
        
        # Determine token order and decimals
        token_in_lower = token_in.lower()
        token_out_lower = token_out.lower()
        token0_lower = token_info["token0"].lower()
        token1_lower = token_info["token1"].lower()
        
        if token_in_lower == token0_lower and token_out_lower == token1_lower:
            # Swapping token0 → token1
            decimals_in = token_info["decimals0"]
            decimals_out = token_info["decimals1"]
            # Price: token1/token0
            price_amm = pool_data["price_eth_per_usdt"]
        elif token_in_lower == token1_lower and token_out_lower == token0_lower:
            # Swapping token1 → token0
            decimals_in = token_info["decimals1"]
            decimals_out = token_info["decimals0"]
            # Price: token0/token1 = 1 / (token1/token0)
            price_amm = Decimal('1') / pool_data["price_eth_per_usdt"]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Token pair mismatch. Pool has {token_info['token0']}/{token_info['token1']}, requested {token_in}/{token_out}"
            )
        
        # ====================================================================
        # Step 3: Get AMM baseline quote (Quoter V2)
        # ====================================================================
        
        amm_quote = get_amm_output(
            token_in=token_in,
            token_out=token_out,
            amount_in=swap_amount,
            fee=fee
        )
        amm_reference_out = amm_quote['amountOut']
        
        # ====================================================================
        # Step 4: Generate synthetic orderbook (Module 2)
        # ====================================================================
        
        generator = SyntheticOrderbookGenerator(
            mid_price=price_amm,
            decimals_in=decimals_in,
            decimals_out=decimals_out
        )
        
        # Determine is_bid (user selling base asset?)
        # If token_in is token0 (base), then is_bid = False (user buying quote with base)
        # If token_in is token1 (quote), then is_bid = True (user selling quote for base)
        is_bid = (token_in_lower == token1_lower)
        
        levels = generator.generate(
            scenario=scenario,
            swap_amount=swap_amount,
            is_bid=is_bid
        )
        
        # ====================================================================
        # Step 5: Greedy matching (Module 3)
        # ====================================================================
        
        matcher = GreedyMatcher(
            price_amm=price_amm,
            decimals_in=decimals_in,
            decimals_out=decimals_out,
            ob_min_improve_bps=ob_min_improve_bps
        )
        
        match_result = matcher.match(
            levels=levels,
            swap_amount=swap_amount,
            is_bid=is_bid
        )
        
        # ====================================================================
        # Step 6: Build execution plan (Module 4)
        # ====================================================================
        
        builder = ExecutionPlanBuilder(
            price_amm=price_amm,
            decimals_in=decimals_in,
            decimals_out=decimals_out,
            performance_fee_bps=performance_fee_bps,
            max_slippage_bps=max_slippage_bps
        )
        
        execution_plan = builder.build_plan(
            match_result=match_result,
            token_in_address=token_in,
            token_out_address=token_out,
            max_matches=max_matches,
            me_slippage_limit=me_slippage_limit
        )
        
        # ====================================================================
        # Step 7: Add metadata
        # ====================================================================
        
        execution_plan["metadata"] = {
            "chain_id": chain_id,
            "pool_address": pool_address,
            "fee": fee,
            "receiver": receiver,
            "scenario": scenario,
            "decimals_in": decimals_in,
            "decimals_out": decimals_out,
            "token_in_symbol": token_info["symbol0"] if token_in_lower == token0_lower else token_info["symbol1"],
            "token_out_symbol": token_info["symbol1"] if token_in_lower == token0_lower else token_info["symbol0"],
        }
        
        return execution_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# Health check endpoint
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "UniHybrid API",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "service": "UniHybrid API",
        "version": "1.0.0",
        "endpoints": {
            "execution_plan": "/api/unihybrid/execution-plan",
            "health": "/health",
            "docs": "/docs"
        }
    }


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
