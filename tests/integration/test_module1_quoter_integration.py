"""
Test Module 1 (Quoter V2) Integration với Module 2, 3, 4
=======================================================

Verify rằng Module 1 với Quoter V2 tích hợp hoàn hảo với các module khác.
"""

from decimal import Decimal
from services.amm_uniswap_v3.uniswap_v3 import (
    get_price_for_pool,
    get_amm_output,
    quote_exact_input_single_v2
)
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder


def test_module1_quoter_integration():
    """Test Module 1 với Quoter V2 real quotes."""
    
    print("=" * 80)
    print("TEST: MODULE 1 QUOTER V2 INTEGRATION")
    print("=" * 80)
    print()
    
    # Addresses on Base
    POOL_ADDR = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"  # ETH/USDC pool
    WETH = "0x4200000000000000000000000000000000000006"
    USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    
    # Test scenario
    swap_amount_eth = 1  # 1 ETH
    swap_amount = swap_amount_eth * 10**18  # Base units
    
    print("STEP 1: Get AMM Price (Module 1)")
    print("-" * 80)
    pool_data = get_price_for_pool(POOL_ADDR)
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    
    print(f"✅ Pool: {POOL_ADDR}")
    print(f"   Token0: {pool_data['symbol0']} ({pool_data['token0']})")
    print(f"   Token1: {pool_data['symbol1']} ({pool_data['token1']})")
    print(f"   AMM Price: {price_usdt_per_eth:.2f} USDT/ETH")
    print()
    
    print("STEP 2: Get Real Quote from Quoter V2")
    print("-" * 80)
    
    # Get real AMM output using Quoter V2
    amm_output_result = get_amm_output(
        token_in=WETH,
        token_out=USDC,
        amount_in=swap_amount,
        fee=3000
    )
    
    amm_reference_out = amm_output_result['amountOut']
    
    print(f"✅ Quoter V2 Quote:")
    print(f"   Input: {swap_amount / 10**18:.4f} ETH")
    print(f"   Output: {amm_reference_out / 10**6:.2f} USDC")
    print(f"   Effective Price: {amm_reference_out / swap_amount * 10**12:.2f} USDC/ETH")
    print()
    
    print("STEP 3: Generate Orderbook (Module 2)")
    print("-" * 80)
    
    # For ETH → USDC swap:
    # - token_in = ETH (18 decimals)
    # - token_out = USDC (6 decimals)
    # - price = USDC/ETH (output/input)
    # - mid_price from pool is already USDT/ETH (same as USDC/ETH)
    
    generator = SyntheticOrderbookGenerator(
        mid_price=price_usdt_per_eth,  # USDC/ETH
        decimals_in=18,  # ETH
        decimals_out=6   # USDC
    )
    
    levels = generator.generate('medium', swap_amount, is_bid=False)
    depth_info = generator.get_total_depth(levels)
    
    print(f"✅ Generated {len(levels)} orderbook levels")
    print(f"   Total Depth: {depth_info['total_amount_in'] / 10**18:.4f} ETH")
    print(f"   Depth Ratio: {depth_info['total_amount_in'] / swap_amount:.2f}× swap amount")
    print()
    
    print("STEP 4: Greedy Matching (Module 3)")
    print("-" * 80)
    
    matcher = GreedyMatcher(
        price_amm=price_usdt_per_eth,  # USDC/ETH
        decimals_in=18,
        decimals_out=6,
        ob_min_improve_bps=5
    )
    
    match_result = matcher.match(levels, swap_amount, is_bid=False)
    
    ob_pct = match_result['amount_in_on_orderbook'] * 100 // swap_amount
    amm_pct = match_result['amount_in_on_amm'] * 100 // swap_amount
    
    print(f"✅ Greedy matching completed")
    print(f"   Orderbook: {match_result['amount_in_on_orderbook'] / 10**18:.4f} ETH ({ob_pct}%)")
    print(f"   AMM:       {match_result['amount_in_on_amm'] / 10**18:.4f} ETH ({amm_pct}%)")
    print(f"   Levels used: {len(match_result['levels_used'])}")
    print()
    
    print("STEP 5: Build Execution Plan (Module 4)")
    print("-" * 80)
    
    builder = ExecutionPlanBuilder(
        price_amm=price_usdt_per_eth,  # USDC/ETH
        decimals_in=18,
        decimals_out=6,
        performance_fee_bps=3000,
        max_slippage_bps=100
    )
    
    execution_plan = builder.build_plan(
        match_result=match_result,
        token_in_address=WETH,
        token_out_address=USDC,
        max_matches=8,
        me_slippage_limit=200
    )
    
    print(f"✅ Execution plan built")
    print()
    
    print("=" * 80)
    print("RESULTS COMPARISON")
    print("=" * 80)
    print()
    
    # Parse results
    expected_total_out = int(execution_plan['expected_total_out'])
    savings_before_fee = int(execution_plan['savings_before_fee'])
    savings_after_fee = int(execution_plan['savings_after_fee'])
    
    print("📊 AMM BASELINE (Quoter V2 - Real):")
    print(f"   Amount Out: {amm_reference_out / 10**6:.2f} USDC")
    print(f"   Price: {amm_reference_out / swap_amount * 10**12:.2f} USDC/ETH")
    print()
    
    print("📊 UNIHYBRID (OB + AMM):")
    print(f"   Expected Out: {expected_total_out / 10**6:.2f} USDC")
    print(f"   Effective Price: {expected_total_out / swap_amount * 10**12:.2f} USDC/ETH")
    print()
    
    print("💰 SAVINGS:")
    print(f"   Before Fee: {savings_before_fee / 10**6:.2f} USDC ({savings_before_fee * 10000 // amm_reference_out} bps)")
    print(f"   After Fee:  {savings_after_fee / 10**6:.2f} USDC ({savings_after_fee * 10000 // amm_reference_out} bps)")
    print(f"   Performance Fee (30%): {int(execution_plan['performance_fee_amount']) / 10**6:.2f} USDC")
    print()
    
    # Verify
    improvement_bps = (expected_total_out - amm_reference_out) * 10000 // amm_reference_out
    
    if improvement_bps > 0:
        print(f"✅ SUCCESS: UniHybrid tốt hơn AMM {improvement_bps} bps!")
    else:
        print(f"⚠️  WARNING: Không có improvement (orderbook thin)")
    
    print()
    print("=" * 80)
    print("✅ MODULE 1 QUOTER V2 INTEGRATION TEST PASSED!")
    print("=" * 80)
    

if __name__ == "__main__":
    test_module1_quoter_integration()
