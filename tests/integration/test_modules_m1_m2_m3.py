"""
Integration Test: Module 1 + Module 2 + Module 3

Tests the complete flow:
1. Module 1: Fetch AMM price from Uniswap V3
2. Module 2: Generate synthetic orderbook
3. Module 3: Greedy match between orderbook and AMM

This demonstrates the core UniHybrid logic for answering:
"How much more does user get with UniHybrid vs 100% AMM swap?"
"""

from decimal import Decimal
from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher


def test_full_flow():
    """Test complete flow: AMM → Orderbook → Greedy Matching"""
    
    print("=" * 80)
    print("INTEGRATION TEST: MODULE 1 + MODULE 2 + MODULE 3")
    print("=" * 80)
    print()
    
    # Configuration
    pool_address = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    swap_amount_usdt = 10000  # 10,000 USDT
    swap_amount = swap_amount_usdt * 10**6  # Base units
    
    print(f"Test Swap: {swap_amount_usdt:,} USDT → ETH")
    print(f"Pool: {pool_address}")
    print()
    
    # ========================================
    # STEP 1: Fetch AMM price (Module 1)
    # ========================================
    print("=" * 80)
    print("STEP 1: FETCH AMM PRICE (Module 1)")
    print("=" * 80)
    print()
    
    pool_data = get_price_for_pool(pool_address)
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    
    print(f"✅ AMM Mid Price: {price_usdt_per_eth:.2f} USDT/ETH")
    print(f"   Token0: {pool_data['symbol0']} ({pool_data['decimals0']} decimals)")
    print(f"   Token1: {pool_data['symbol1']} ({pool_data['decimals1']} decimals)")
    print()
    
    # For USDT→ETH swap, we need ETH/USDT (inverse)
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    # Simulate AMM reference output (100% AMM swap)
    # In production, use Quoter.quoteExactInputSingle()
    amm_reference_out = int(
        Decimal(swap_amount) * price_eth_per_usdt * Decimal(10**18) / Decimal(10**6)
    )
    
    print(f"📊 AMM Reference (100% AMM):")
    print(f"   Input:  {swap_amount / 10**6:,.2f} USDT")
    print(f"   Output: {amm_reference_out / 10**18:.6f} ETH")
    print(f"   Avg Price: {price_usdt_per_eth:.2f} USDT/ETH")
    print()
    
    # ========================================
    # STEP 2 & 3: Test each scenario
    # ========================================
    
    scenarios_to_test = [
        ('small', None, "Worst Case - Thin Orderbook"),
        ('medium', None, "Realistic Case - Moderate Depth"),
        ('large', Decimal('1000000'), "Best Case - CEX-like Depth")
    ]
    
    for scenario_name, capital, description in scenarios_to_test:
        print("=" * 80)
        print(f"SCENARIO: {scenario_name.upper()} ({description})")
        print("=" * 80)
        print()
        
        # ========================================
        # STEP 2: Generate orderbook (Module 2)
        # ========================================
        print("STEP 2: GENERATE ORDERBOOK (Module 2)")
        print("-" * 80)
        
        generator = SyntheticOrderbookGenerator(
            mid_price=price_eth_per_usdt,
            decimals_in=6,   # USDT
            decimals_out=18  # ETH
        )
        
        levels = generator.generate(
            scenario_name,
            swap_amount,
            is_bid=False,
            capital_usd=capital
        )
        
        depth = generator.get_total_depth(levels)
        
        print(f"✅ Generated {len(levels)} orderbook levels")
        print(f"   Total Depth: {depth['total_amount_in'] / 10**6:,.2f} USDT")
        print(f"   Depth Ratio: {depth['total_amount_in'] / swap_amount:.2f}× swap amount")
        print()
        
        # Show first 3 levels
        print("   Top 3 Levels:")
        for i, level in enumerate(levels[:3], 1):
            price_display = Decimal('1') / level.price
            liq_in = level.amount_in_available / 10**6
            liq_out = level.amount_out_available / 10**18
            print(f"     Level {i}: {price_display:.2f} USDT/ETH | {liq_in:,.2f} USDT → {liq_out:.6f} ETH")
        
        if len(levels) > 3:
            print(f"     ... ({len(levels) - 3} more levels)")
        print()
        
        # ========================================
        # STEP 3: Greedy matching (Module 3)
        # ========================================
        print("STEP 3: GREEDY MATCHING (Module 3)")
        print("-" * 80)
        
        # Test with ob_min_improve_bps = 5 (0.05%)
        matcher = GreedyMatcher(
            price_amm=price_eth_per_usdt,
            decimals_in=6,
            decimals_out=18,
            ob_min_improve_bps=5
        )
        
        match_result = matcher.match(levels, swap_amount, is_bid=False)
        
        print(f"✅ Greedy matching completed")
        print(f"   Min Better Price: {Decimal('1')/match_result['min_better_price']:.2f} USDT/ETH")
        print(f"   Threshold: Orderbook must be {matcher.ob_min_improve_bps} bps better than AMM")
        print()
        
        ob_amount = match_result['amount_in_on_orderbook']
        amm_amount = match_result['amount_in_on_amm']
        ob_out = match_result['amount_out_from_orderbook']
        
        print(f"📊 Split Decision:")
        print(f"   Orderbook: {ob_amount / 10**6:,.2f} USDT ({ob_amount * 100 // swap_amount}%)")
        print(f"   AMM:       {amm_amount / 10**6:,.2f} USDT ({amm_amount * 100 // swap_amount}%)")
        print()
        
        print(f"   Output from OB: {ob_out / 10**18:.6f} ETH")
        print(f"   Levels used:    {len(match_result['levels_used'])} / {match_result['levels_better_than_amm']} better levels")
        print()
        
        # ========================================
        # STEP 4: Calculate savings
        # ========================================
        print("STEP 4: CALCULATE SAVINGS")
        print("-" * 80)
        
        savings = matcher.calculate_savings(match_result, amm_reference_out)
        
        expected_total_out = savings['expected_total_out']
        savings_before_fee = savings['savings_before_fee']
        savings_after_fee = savings['savings_after_fee']
        performance_fee = savings['performance_fee_amount']
        
        print(f"✅ Savings calculation:")
        print(f"   Expected Total Out: {expected_total_out / 10**18:.6f} ETH")
        print(f"   AMM Reference Out:  {amm_reference_out / 10**18:.6f} ETH")
        print()
        
        print(f"💰 Savings:")
        print(f"   Before Fee: {savings_before_fee / 10**18:.6f} ETH ({savings_before_fee * 10000 // expected_total_out} bps)")
        print(f"   Performance Fee (30%): {performance_fee / 10**18:.6f} ETH")
        print(f"   After Fee:  {savings_after_fee / 10**18:.6f} ETH ({savings_after_fee * 10000 // expected_total_out} bps)")
        print()
        
        # Improvement percentage
        if amm_reference_out > 0:
            improvement_pct = (savings_after_fee * 10000) / amm_reference_out
            print(f"📈 User gets {improvement_pct / 100:.2f}% MORE with UniHybrid vs 100% AMM")
        print()
    
    print("=" * 80)
    print("✅ INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print()
    print("Summary:")
    print("- Module 1 (AMM): ✅ Fetched real-time price from Uniswap V3")
    print("- Module 2 (Orderbook): ✅ Generated synthetic orderbook for 3 scenarios")
    print("- Module 3 (Greedy Matcher): ✅ Split swap between OB and AMM optimally")
    print("- Savings Calculation: ✅ Calculated improvement over 100% AMM")
    print()
    print("🎯 Ready for Module 4: Execution Plan Builder")
    print()


if __name__ == "__main__":
    test_full_flow()
