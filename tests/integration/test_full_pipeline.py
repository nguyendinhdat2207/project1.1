"""
Integration Test: Module 1 + 2 + 3 + 4 (Full Pipeline)
================================================================================

Test flow:
1. Module 1: Fetch AMM price từ Uniswap V3 pool
2. Module 2: Generate synthetic orderbook
3. Module 3: Greedy matching (split OB vs AMM)
4. Module 4: Build execution plan (complete JSON response)

Test tất cả 3 scenarios: Small, Medium, Large
"""

from decimal import Decimal
from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder
import json


def test_full_pipeline(scenario: str, swap_amount_usdt: int):
    """
    Test complete pipeline cho 1 scenario.
    
    Parameters:
    -----------
    scenario : str
        'small', 'medium', or 'large'
    swap_amount_usdt : int
        Swap amount in human units (vd: 10000 = 10k USDT)
    """
    print("=" * 90)
    print(f"SCENARIO: {scenario.upper()} (Swap: {swap_amount_usdt:,} USDT)")
    print("=" * 90)
    print()
    
    # Token addresses (Base mainnet)
    TOKEN_USDT = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
    TOKEN_ETH = "0x4200000000000000000000000000000000000006"
    
    # Step 1: Module 1 - AMM Price
    print("STEP 1: FETCH AMM PRICE (Module 1)")
    print("-" * 90)
    pool_address = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    pool_data = get_price_for_pool(pool_address)
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    print(f"✅ Pool: {pool_address}")
    print(f"   Pair: {pool_data['symbol0']}/{pool_data['symbol1']}")
    print(f"   AMM Price: {price_usdt_per_eth:.2f} USDT/ETH")
    print()
    
    # Step 2: Module 2 - Orderbook Generation
    print("STEP 2: GENERATE ORDERBOOK (Module 2)")
    print("-" * 90)
    swap_amount = swap_amount_usdt * 10**6  # Convert to base units
    generator = SyntheticOrderbookGenerator(price_eth_per_usdt, 6, 18)
    levels = generator.generate(scenario, swap_amount, is_bid=False)
    
    depth_info = generator.get_total_depth(levels)
    depth_ratio = depth_info['total_amount_in'] / swap_amount
    
    print(f"✅ Generated {len(levels)} orderbook levels")
    print(f"   Total Depth: {depth_info['total_amount_in'] / 10**6:,.2f} USDT")
    print(f"   Depth Ratio: {depth_ratio:.2f}× swap amount")
    print()
    
    # Print first 3 levels
    print("   Top 3 Levels:")
    for i, level in enumerate(levels[:3], 1):
        usdt_per_eth = Decimal('1') / level.price
        amt_in = level.amount_in_available / 10**6
        print(f"      Level {i}: {usdt_per_eth:.2f} USDT/ETH | {amt_in:,.2f} USDT available")
    print()
    
    # Step 3: Module 3 - Greedy Matching
    print("STEP 3: GREEDY MATCHING (Module 3)")
    print("-" * 90)
    matcher = GreedyMatcher(price_eth_per_usdt, 6, 18, ob_min_improve_bps=5)
    match_result = matcher.match(levels, swap_amount, is_bid=False)
    
    amt_ob = match_result['amount_in_on_orderbook'] / 10**6
    amt_amm = match_result['amount_in_on_amm'] / 10**6
    pct_ob = (match_result['amount_in_on_orderbook'] * 100) // swap_amount
    pct_amm = (match_result['amount_in_on_amm'] * 100) // swap_amount
    
    print(f"✅ Greedy matching completed")
    print(f"   Threshold: Orderbook must be ≥5 bps better than AMM")
    print()
    print(f"📊 Split Decision:")
    print(f"   Orderbook: {amt_ob:,.2f} USDT ({pct_ob}%)")
    print(f"   AMM:       {amt_amm:,.2f} USDT ({pct_amm}%)")
    print(f"   Levels used: {len(match_result['levels_used'])}")
    print()
    
    # Step 4: Module 4 - Build Execution Plan
    print("STEP 4: BUILD EXECUTION PLAN (Module 4)")
    print("-" * 90)
    
    builder = ExecutionPlanBuilder(
        price_amm=price_eth_per_usdt,
        decimals_in=6,
        decimals_out=18,
        performance_fee_bps=3000,  # 30%
        max_slippage_bps=100       # 1%
    )
    
    execution_plan = builder.build_plan(
        match_result=match_result,
        token_in_address=TOKEN_USDT,
        token_out_address=TOKEN_ETH,
        max_matches=8,
        me_slippage_limit=200
    )
    
    print("✅ Execution plan built")
    print()
    
    # Print execution plan summary
    print("=" * 90)
    print("EXECUTION PLAN SUMMARY")
    print("=" * 90)
    print()
    
    # Split
    split = execution_plan['split']
    print("📊 SPLIT:")
    print(f"   Total Input:      {int(split['amount_in_total']) / 10**6:,.2f} USDT")
    print(f"   → Orderbook:      {int(split['amount_in_on_orderbook']) / 10**6:,.2f} USDT ({pct_ob}%)")
    print(f"   → AMM:            {int(split['amount_in_on_amm']) / 10**6:,.2f} USDT ({pct_amm}%)")
    print()
    
    # Legs
    print("🔗 LEGS:")
    for i, leg in enumerate(execution_plan['legs'], 1):
        print(f"   Leg {i}: {leg['source']}")
        
        # Calculate in human units based on source
        if leg['source'] == 'internal_orderbook':
            amt_in = int(leg['amount_in']) / 10**6
            amt_out = int(leg['expected_amount_out']) / 10**18
            print(f"      Amount In:  {amt_in:,.2f} USDT")
            print(f"      Amount Out: {amt_out:.6f} ETH")
            
            if 'meta' in leg and 'levels_used' in leg['meta']:
                print(f"      Levels filled: {len(leg['meta']['levels_used'])}")
                # Print first level detail
                if len(leg['meta']['levels_used']) > 0:
                    first_level = leg['meta']['levels_used'][0]
                    level_price_usdt = Decimal('1') / Decimal(first_level['price'])
                    print(f"         Best level: {level_price_usdt:.2f} USDT/ETH")
        else:  # AMM
            amt_in = int(leg['amount_in']) / 10**6
            amt_out = int(leg['expected_amount_out']) / 10**18
            print(f"      Amount In:  {amt_in:,.2f} USDT")
            print(f"      Amount Out: {amt_out:.6f} ETH")
            print(f"      AMM Price:  {price_usdt_per_eth:.2f} USDT/ETH")
        print()
    
    # Savings
    print("💰 SAVINGS:")
    amm_ref = int(execution_plan['amm_reference_out']) / 10**18
    total_out = int(execution_plan['expected_total_out']) / 10**18
    sav_before = int(execution_plan['savings_before_fee']) / 10**18
    fee_amt = int(execution_plan['performance_fee_amount']) / 10**18
    sav_after = int(execution_plan['savings_after_fee']) / 10**18
    
    improvement_bps = (sav_after / amm_ref * 10000) if amm_ref > 0 else 0
    
    print(f"   AMM Reference Out:    {amm_ref:.6f} ETH (100% AMM baseline)")
    print(f"   Expected Total Out:   {total_out:.6f} ETH (UniHybrid)")
    print(f"   Savings Before Fee:   {sav_before:.6f} ETH")
    print(f"   Performance Fee (30%): {fee_amt:.6f} ETH")
    print(f"   Savings After Fee:    {sav_after:.6f} ETH")
    print()
    print(f"   📈 User gets {improvement_bps:.2f} bps MORE with UniHybrid!")
    print()
    
    # Slippage protection
    print("🔒 SLIPPAGE PROTECTION:")
    min_out = int(execution_plan['min_total_out']) / 10**18
    print(f"   Min Total Out (1% slippage): {min_out:.6f} ETH")
    print()
    
    # Hook data
    print("📦 HOOK DATA (for smart contract):")
    hook_args = execution_plan['hook_data_args']
    print(f"   tokenIn:  {hook_args['tokenIn'][:10]}...{hook_args['tokenIn'][-4:]}")
    print(f"   tokenOut: {hook_args['tokenOut'][:10]}...{hook_args['tokenOut'][-4:]}")
    print(f"   amountInOnOrderbook: {hook_args['amountInOnOrderbook']}")
    print(f"   maxMatches: {hook_args['maxMatches']}")
    print(f"   slippageLimit: {hook_args['slippageLimit']}")
    print(f"   Encoded: {execution_plan['hook_data'][:20]}...{execution_plan['hook_data'][-10:]}")
    print()
    
    # Validation checks
    print("✅ VALIDATION CHECKS:")
    
    # Check 1: Split adds up
    total_in = int(split['amount_in_total'])
    ob_in = int(split['amount_in_on_orderbook'])
    amm_in = int(split['amount_in_on_amm'])
    assert ob_in + amm_in == total_in, "Split doesn't add up!"
    print("   ✅ Split adds up correctly")
    
    # Check 2: Savings >= 0
    assert sav_after >= 0, "Negative savings!"
    print("   ✅ Savings non-negative")
    
    # Check 3: Performance fee = 30%
    if sav_before > 0:
        fee_pct = fee_amt / sav_before
        assert 0.29 <= fee_pct <= 0.31, f"Performance fee not 30%! Got {fee_pct:.2%}"
        print(f"   ✅ Performance fee correct: {fee_pct:.2%}")
    
    # Check 4: Expected output >= AMM reference (có savings)
    assert total_out >= amm_ref, "Expected output worse than AMM!"
    print("   ✅ UniHybrid output ≥ AMM baseline")
    
    # Check 5: Min output with slippage
    expected_min = amm_ref * 0.99  # 1% slippage
    assert abs(min_out - expected_min) / expected_min < 0.01, "Min output calculation wrong!"
    print("   ✅ Min output with 1% slippage correct")
    
    # Check 6: Hook data encoded
    assert execution_plan['hook_data'].startswith('0x'), "Hook data not hex!"
    assert len(execution_plan['hook_data']) > 20, "Hook data too short!"
    print("   ✅ Hook data properly encoded")
    
    print()
    print("=" * 90)
    print(f"✅ {scenario.upper()} SCENARIO TEST PASSED!")
    print("=" * 90)
    print()
    
    return execution_plan


if __name__ == "__main__":
    print()
    print("=" * 90)
    print("INTEGRATION TEST: MODULE 1 + 2 + 3 + 4 (FULL PIPELINE)")
    print("=" * 90)
    print()
    print("Test swap: 10,000 USDT → ETH")
    print("Pool: ETH/USDT on Base (0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a)")
    print()
    
    # Test all 3 scenarios
    scenarios_config = [
        ('small', 10000),   # 10k USDT
        ('medium', 10000),  # 10k USDT
        ('large', 10000),   # 10k USDT
    ]
    
    results = {}
    
    for scenario, amount in scenarios_config:
        execution_plan = test_full_pipeline(scenario, amount)
        results[scenario] = execution_plan
        print()
    
    # Final summary
    print("=" * 90)
    print("FINAL SUMMARY - ALL SCENARIOS")
    print("=" * 90)
    print()
    
    for scenario in ['small', 'medium', 'large']:
        plan = results[scenario]
        split = plan['split']
        
        pct_ob = int(split['amount_in_on_orderbook']) * 100 // int(split['amount_in_total'])
        amm_ref = int(plan['amm_reference_out']) / 10**18
        sav_after = int(plan['savings_after_fee']) / 10**18
        improvement = (sav_after / amm_ref * 10000) if amm_ref > 0 else 0
        
        print(f"{scenario.upper():6} | OB: {pct_ob:3}% | Savings: {sav_after:.6f} ETH | Improvement: {improvement:6.2f} bps")
    
    print()
    print("=" * 90)
    print("✅ ALL TESTS PASSED! MODULE 4 INTEGRATION COMPLETE!")
    print("=" * 90)
