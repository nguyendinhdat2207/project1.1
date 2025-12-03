from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.amm_uniswap_v3.uniswap_v3 import (
    get_price_for_pool,
    get_amm_output,
    get_pool_tokens_and_decimals
)
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder


app = FastAPI(
    title="UniHybrid API",
    description="Hybrid orderbook + AMM execution planning",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded pools on Base - would normally fetch this from subgraph or registry
POOL_REGISTRY = {
    ("0x4200000000000000000000000000000000000006", "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2"): {
        "pool": "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a",
        "fee": 3000
    },
    ("0xfde4c96c8593536e31f229ea8f37b2ada2699bb2", "0x4200000000000000000000000000000000000006"): {
        "pool": "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a",
        "fee": 3000
    },
    ("0x4200000000000000000000000000000000000006", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"): {
        "pool": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
        "fee": 3000
    },
    ("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "0x4200000000000000000000000000000000000006"): {
        "pool": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
        "fee": 3000
    },
}


def get_pool_for_pair(token_in: str, token_out: str) -> dict:
    key = (token_in.lower(), token_out.lower())
    if key in POOL_REGISTRY:
        return POOL_REGISTRY[key]
    
    raise HTTPException(
        status_code=404,
        detail=f"Pool not found for {token_in}/{token_out}"
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
    try:
        if chain_id != 8453:
            raise HTTPException(
                status_code=400,
                detail=f"Only Base mainnet (8453) is supported. Got: {chain_id}"
            )
        
        try:
            swap_amount = int(amount_in)
            if swap_amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid amount_in: {e}"
            )
        
        if scenario not in ["small", "medium", "large"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scenario: {scenario}. Must be 'small', 'medium', or 'large'"
            )
        
        pool_info = get_pool_for_pair(token_in, token_out)
        pool_address = pool_info["pool"]
        fee = pool_info["fee"]
        
        pool_data = get_price_for_pool(pool_address)
        token_info = get_pool_tokens_and_decimals(pool_address)
        
        token_in_lower = token_in.lower()
        token_out_lower = token_out.lower()
        token0_lower = token_info["token0"].lower()
        token1_lower = token_info["token1"].lower()
        
        if token_in_lower == token0_lower and token_out_lower == token1_lower:
            decimals_in = token_info["decimals0"]
            decimals_out = token_info["decimals1"]
            price_amm = pool_data["price_eth_per_usdt"]
        elif token_in_lower == token1_lower and token_out_lower == token0_lower:
            decimals_in = token_info["decimals1"]
            decimals_out = token_info["decimals0"]
            price_amm = Decimal('1') / pool_data["price_eth_per_usdt"]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Token pair mismatch. Pool has {token_info['token0']}/{token_info['token1']}, requested {token_in}/{token_out}"
            )
        
        # Get quote from Quoter V2
        amm_quote = get_amm_output(
            token_in=token_in,
            token_out=token_out,
            amount_in=swap_amount,
            fee=fee
        )
        amm_reference_out = amm_quote['amountOut']
        
        # Generate orderbook
        generator = SyntheticOrderbookGenerator(
            mid_price=price_amm,
            decimals_in=decimals_in,
            decimals_out=decimals_out
        )
        
        is_bid = (token_in_lower == token1_lower)
        
        levels = generator.generate(
            scenario=scenario,
            swap_amount=swap_amount,
            is_bid=is_bid
        )
        
        # Match against orderbook
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
        
        # Build execution plan
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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "UniHybrid API",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {
        "service": "UniHybrid API",
        "version": "1.0.0",
        "endpoints": {
            "execution_plan": "/api/unihybrid/execution-plan",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
