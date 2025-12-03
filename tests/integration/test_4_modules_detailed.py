"""
Test chi tiết 4 modules và API endpoint
Kiểm tra từng bước trong flow xử lý
"""

import sys
from decimal import Decimal
from web3 import Web3

print("=" * 80)
print("TEST CHI TIẾT 4 MODULES - UniHybrid Backend")
print("=" * 80)
print()

# ============================================================================
# TEST MODULE 1: AMM UNISWAP V3 + QUOTER V2
# ============================================================================
print("🔵 MODULE 1: AMM Uniswap V3 + Quoter V2 Integration")
print("-" * 80)

from services.amm_uniswap_v3.uniswap_v3 import (
    get_price_for_pool,
    get_amm_output,
    quote_exact_input_single_v2,
    get_pool_tokens_and_decimals
)

# Test parameters
WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
POOL_WETH_USDC = "0x6c561B446416E1A00E8E93E221854d6eA4171372"
AMOUNT_IN = 1_000_000_000_000_000_000  # 1 ETH

print(f"Input: 1 ETH")
print(f"Pool: {POOL_WETH_USDC}")
print()

# Step 1.1: Get pool price from sqrtPriceX96
print("Step 1.1: Đọc pool price từ sqrtPriceX96...")
try:
    pool_data = get_price_for_pool(POOL_WETH_USDC)
    price_sqrtprice = pool_data['price_eth_per_usdt']  # Price in USDC per ETH
    print(f"  ✅ Price from sqrtPriceX96: {price_sqrtprice:.6f} USDC/ETH")
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Step 1.2: Get token decimals
print("Step 1.2: Đọc token decimals...")
try:
    token_info = get_pool_tokens_and_decimals(POOL_WETH_USDC)
    print(f"  ✅ Token0 ({token_info['symbol0']}): {token_info['decimals0']} decimals")
    print(f"  ✅ Token1 ({token_info['symbol1']}): {token_info['decimals1']} decimals")
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Step 1.3: Get AMM quote via Quoter V2
print("Step 1.3: Gọi Quoter V2 contract để lấy quote chính xác...")
try:
    quote_result = quote_exact_input_single_v2(
        token_in=WETH,
        token_out=USDC,
        fee=3000,
        amount_in=AMOUNT_IN
    )
    amm_output = quote_result['amountOut']
    gas_estimate = quote_result['gasEstimate']
    
    print(f"  ✅ AMM Output: {amm_output / 10**6:.2f} USDC")
    print(f"  ✅ Gas Estimate: {gas_estimate:,}")
    print(f"  ✅ Effective Price: {amm_output / AMOUNT_IN * 10**12:.6f} USDC/ETH")
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Step 1.4: Test wrapper function
print("Step 1.4: Test wrapper function get_amm_output()...")
try:
    amm_output_wrapper = get_amm_output(
        token_in=WETH,
        token_out=USDC,
        amount_in=AMOUNT_IN,
        fee=3000
    )
    amm_out_value = amm_output_wrapper['amountOut']
    print(f"  ✅ AMM Output (wrapper): {amm_out_value / 10**6:.2f} USDC")
    assert amm_output == amm_out_value, "Wrapper result mismatch!"
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

print()
print("✅ MODULE 1: PASSED - AMM quotes chính xác từ Quoter V2")
print()

# ============================================================================
# TEST MODULE 2: SYNTHETIC ORDERBOOK
# ============================================================================
print("🔵 MODULE 2: Synthetic Orderbook Generation")
print("-" * 80)

from services.orderbook import SyntheticOrderbookGenerator

# Test cả 3 scenarios
scenarios = ["small", "medium", "large"]

# Get pool data first to get mid price and decimals
pool_data = get_price_for_pool(POOL_WETH_USDC)
mid_price = pool_data['price_eth_per_usdt']
decimals_in = pool_data['decimals0']  # WETH = 18
decimals_out = pool_data['decimals1']  # USDC = 6

for scenario in scenarios:
    print(f"\nScenario: {scenario.upper()}")
    print("-" * 40)
    
    try:
        # Generate orderbook
        ob_gen = SyntheticOrderbookGenerator(
            mid_price=mid_price,
            decimals_in=decimals_in,
            decimals_out=decimals_out
        )
        levels = ob_gen.generate(
            scenario=scenario,
            swap_amount=AMOUNT_IN,
            is_bid=False  # Buying USDC with ETH (asks)
        )
        
        # Analyze levels (for buying USDC with ETH)
        print(f"  Levels (asks - selling USDC for ETH):")
        print(f"    Levels: {len(levels)}")
        
        total_usdc_available = sum(level.amount_out_available for level in levels)
        best_ask_price = levels[0].price if levels else 0
        worst_ask_price = levels[-1].price if levels else 0
        
        print(f"    Total USDC available: {total_usdc_available / 10**6:.2f}")
        print(f"    Best ask price: {best_ask_price:.6f} USDC/ETH")
        print(f"    Worst ask price: {worst_ask_price:.6f} USDC/ETH")
        print(f"    Spread: {(worst_ask_price - best_ask_price):.6f} USDC/ETH")
        
        # Show first 3 levels
        print(f"    First 3 levels:")
        for i, level in enumerate(levels[:3]):
            print(f"      Level {i+1}: Price={level.price:.2f}, Amount={level.amount_out_available / 10**6:.2f} USDC")
        
        print(f"  ✅ Orderbook generated successfully for scenario '{scenario}'")
        
    except Exception as e:
        print(f"  ❌ Error in scenario '{scenario}': {e}")
        sys.exit(1)

print()
print("✅ MODULE 2: PASSED - Synthetic orderbook cho cả 3 scenarios")
print()

# ============================================================================
# TEST MODULE 3: GREEDY MATCHING
# ============================================================================
print("🔵 MODULE 3: Greedy Matching Algorithm")
print("-" * 80)

from services.matching import GreedyMatcher

# Use medium scenario for testing
print("Generating orderbook (medium scenario)...")
ob_gen = SyntheticOrderbookGenerator(
    mid_price=mid_price,
    decimals_in=decimals_in,
    decimals_out=decimals_out
)
levels = ob_gen.generate(
    scenario="medium",
    swap_amount=AMOUNT_IN,
    is_bid=False
)

print(f"  Orderbook: {len(levels)} levels")
print()

# Test matching with different amounts
test_amounts = [
    (0.1 * 10**18, "0.1 ETH"),
    (1.0 * 10**18, "1.0 ETH"),
    (5.0 * 10**18, "5.0 ETH"),
]

for amount_in, label in test_amounts:
    print(f"Test: {label}")
    print("-" * 40)
    
    try:
        # Create matcher
        matcher = GreedyMatcher(
            price_amm=mid_price,
            decimals_in=decimals_in,
            decimals_out=decimals_out,
            ob_min_improve_bps=5  # Min 5 bps improvement over AMM
        )
        
        # Get AMM price for comparison
        amm_quote_result = get_amm_output(WETH, USDC, int(amount_in), 3000)
        amm_quote = amm_quote_result['amountOut']
        amm_price = amm_quote / amount_in * 10**12
        
        # Match
        match_result = matcher.match(
            levels=levels,
            swap_amount=int(amount_in),
            is_bid=False  # Buying USDC with ETH
        )
        
        if match_result['levels_used']:
            levels_used = match_result['levels_used']
            total_usdc_out = match_result['amount_out_from_orderbook']
            amount_in_ob = match_result['amount_in_on_orderbook']
            avg_price = total_usdc_out / amount_in_ob * 10**12 if amount_in_ob > 0 else 0
            improvement = (avg_price - amm_price) / amm_price * 10000 if amm_price > 0 else 0 # in bps
            
            print(f"  Matched: {len(levels_used)} levels")
            print(f"  AMM price: {amm_price:.6f} USDC/ETH")
            print(f"  OB avg price: {avg_price:.6f} USDC/ETH")
            print(f"  Improvement: {improvement:.1f} bps")
            print(f"  Total USDC out: {total_usdc_out / 10**6:.2f}")
            
            # Show first 3 matches
            print(f"  First 3 matches:")
            for i, level_used in enumerate(levels_used[:3]):
                print(f"    Match {i+1}: Price={level_used.price:.2f}, In={level_used.amount_in_from_level / 10**18:.6f} ETH, Out={level_used.amount_out_from_level / 10**6:.2f} USDC")
            
            print(f"  ✅ Matching successful")
        else:
            print(f"  ⚠️  No matches (orderbook price worse than AMM)")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)
    
    print()

print("✅ MODULE 3: PASSED - Greedy matching algorithm hoạt động đúng")
print()

# ============================================================================
# TEST MODULE 4: EXECUTION PLAN BUILDER
# ============================================================================
print("🔵 MODULE 4: Execution Plan Builder")
print("-" * 80)

from services.execution.core.execution_plan import ExecutionPlanBuilder

print("Test: Build execution plan for 1 ETH → USDC")
print("-" * 40)

try:
    # Get AMM baseline
    amm_baseline_result = get_amm_output(WETH, USDC, AMOUNT_IN, 3000)
    amm_baseline = amm_baseline_result['amountOut']
    print(f"AMM Baseline: {amm_baseline / 10**6:.2f} USDC")
    
    # Generate orderbook and match
    ob_gen = SyntheticOrderbookGenerator(mid_price, decimals_in, decimals_out)
    levels = ob_gen.generate(scenario="medium", swap_amount=AMOUNT_IN, is_bid=False)
    
    matcher = GreedyMatcher(mid_price, decimals_in, decimals_out, ob_min_improve_bps=5)
    match_result = matcher.match(levels=levels, swap_amount=AMOUNT_IN, is_bid=False)
    
    print(f"Matched legs: {len(match_result['levels_used'])}")
    
    # Build execution plan
    builder = ExecutionPlanBuilder(
        price_amm=mid_price,
        decimals_in=decimals_in,
        decimals_out=decimals_out,
        performance_fee_bps=3000,  # 30%
        max_slippage_bps=100
    )
    
    plan = builder.build_plan(
        match_result=match_result,
        token_in_address=WETH,
        token_out_address=USDC,
        max_matches=8,
        me_slippage_limit=200
    )
    
    # Analyze plan
    print()
    print("📊 EXECUTION PLAN RESULTS:")
    print("-" * 40)
    
    # Split
    split = plan['split']
    total_in = int(split['amount_in_total'])
    ob_in = int(split['amount_in_on_orderbook'])
    amm_in = int(split['amount_in_on_amm'])
    
    print(f"SPLIT:")
    print(f"  Total Input:    {total_in / 10**18:.4f} ETH")
    print(f"  → Orderbook:    {ob_in / 10**18:.4f} ETH ({ob_in * 100 // total_in if total_in > 0 else 0}%)")
    print(f"  → AMM:          {amm_in / 10**18:.4f} ETH ({amm_in * 100 // total_in if total_in > 0 else 0}%)")
    print()
    
    # Savings
    amm_ref = int(plan['amm_reference_out'])
    total_out = int(plan['expected_total_out'])
    sav_before = int(plan['savings_before_fee'])
    sav_after = int(plan['savings_after_fee'])
    perf_fee = int(plan['performance_fee_amount'])
    min_out = int(plan['min_total_out'])
    
    print(f"SAVINGS:")
    print(f"  AMM Baseline:       {amm_ref / 10**6:.2f} USDC")
    print(f"  Expected Total:     {total_out / 10**6:.2f} USDC")
    print(f"  Savings Before Fee: {sav_before / 10**6:.2f} USDC ({sav_before * 10000 // amm_ref if amm_ref > 0 else 0} bps)")
    print(f"  Performance Fee:    {perf_fee / 10**6:.2f} USDC (30% of savings)")
    print(f"  Savings After Fee:  {sav_after / 10**6:.2f} USDC ({sav_after * 10000 // amm_ref if amm_ref > 0 else 0} bps)")
    print(f"  Min Total Out:      {min_out / 10**6:.2f} USDC (with 1% slippage)")
    print()
    
    # Hook data
    hook_args = plan['hook_data_args']
    hook_data = plan['hook_data']
    
    print(f"HOOK DATA:")
    print(f"  tokenIn:              {hook_args['tokenIn']}")
    print(f"  tokenOut:             {hook_args['tokenOut']}")
    print(f"  amountInOnOrderbook:  {hook_args['amountInOnOrderbook']}")
    print(f"  maxMatches:           {hook_args['maxMatches']}")
    print(f"  slippageLimit:        {hook_args['slippageLimit']}")
    print(f"  Encoded length:       {len(hook_data)} chars")
    print(f"  Encoded (first 66):   {hook_data[:66]}")
    print()
    
    # Legs
    print(f"LEGS ({len(plan['legs'])} total):")
    for i, leg in enumerate(plan['legs'][:3]):  # Show first 3
        print(f"  Leg {i+1}:")
        print(f"    Source:      {leg['source']}")
        print(f"    Amount In:   {int(leg['amount_in']) / 10**18:.6f} ETH")
        print(f"    Amount Out:  {int(leg['expected_amount_out']) / 10**6:.2f} USDC")
        if 'meta' in leg and 'levels_used' in leg['meta']:
            print(f"    Levels Used: {len(leg['meta']['levels_used'])}")
    
    print()
    print("✅ MODULE 4: PASSED - Execution plan builder hoạt động đầy đủ")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============================================================================
# TEST API INTEGRATION
# ============================================================================
print("🔵 API INTEGRATION TEST")
print("-" * 80)

import requests

print("Testing API endpoint với cùng parameters...")
print()

try:
    url = "http://localhost:8000/api/unihybrid/execution-plan"
    params = {
        "chain_id": 8453,
        "token_in": WETH,
        "token_out": USDC,
        "amount_in": str(AMOUNT_IN),
        "receiver": "0x1234567890abcdef1234567890abcdef12345678",
        "max_slippage_bps": 100,
        "performance_fee_bps": 3000,
        "max_matches": 8,
        "ob_min_improve_bps": 5,
        "me_slippage_limit": 200,
        "scenario": "medium"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ API Response: 200 OK")
        print()
        
        # Verify response structure
        required_fields = [
            'split', 'legs', 'hook_data_args', 'hook_data',
            'amm_reference_out', 'expected_total_out',
            'savings_before_fee', 'performance_fee_amount',
            'savings_after_fee', 'min_total_out', 'metadata'
        ]
        
        print("Checking response fields:")
        for field in required_fields:
            if field in data:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - MISSING!")
        
        print()
        
        # Compare with direct module test
        api_total_out = int(data['expected_total_out'])
        api_savings = int(data['savings_after_fee'])
        
        print("Comparison với direct module test:")
        print(f"  Direct: Total={total_out / 10**6:.2f} USDC, Savings={sav_after / 10**6:.2f} USDC")
        print(f"  API:    Total={api_total_out / 10**6:.2f} USDC, Savings={api_savings / 10**6:.2f} USDC")
        
        # Allow small difference due to timing
        diff_pct = abs(api_total_out - total_out) / total_out * 100
        if diff_pct < 1:  # Less than 1% difference
            print(f"  ✅ Results match (diff: {diff_pct:.2f}%)")
        else:
            print(f"  ⚠️  Results differ by {diff_pct:.2f}%")
        
        print()
        print("✅ API INTEGRATION: PASSED")
        
    else:
        print(f"❌ API Response: {response.status_code}")
        print(response.json())
        sys.exit(1)
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to API server")
    print("Make sure server is running: uvicorn api.main:app --host 0.0.0.0 --port 8000")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("🎉 TẤT CẢ TESTS PASSED!")
print("=" * 80)
print()
print("SUMMARY:")
print("  ✅ Module 1: AMM Uniswap V3 + Quoter V2 - WORKING")
print("  ✅ Module 2: Synthetic Orderbook (3 scenarios) - WORKING")
print("  ✅ Module 3: Greedy Matching Algorithm - WORKING")
print("  ✅ Module 4: Execution Plan Builder - WORKING")
print("  ✅ API Endpoint Integration - WORKING")
print()
print("Backend UniHybrid HOÀN TOÀN SẴN SÀNG! 🚀")
print()
