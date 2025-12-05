"""
Backtest với Synthetic Orderbook - Sinh kết quả cho báo cáo

So sánh hiệu quả routing giữa:
- 100% AMM (baseline)
- UniHybrid (AMM + Synthetic Orderbook)
"""

from decimal import Decimal
from services.amm_uniswap_v3.uniswap_v3 import (
    get_price_for_pool,
    get_slot0,
    price_from_sqrtprice,
    get_pool_tokens_and_decimals,
    get_amm_output
)
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_bps(value: float) -> str:
    return f"{value:.2f} bps"


def run_backtest_scenario(scenario_name: str, swap_amount_eth: float, scenario_type: str):
    """
    Chạy một scenario backtest
    
    Args:
        scenario_name: Tên scenario để hiển thị
        swap_amount_eth: Khối lượng swap (ETH)
        scenario_type: 'small', 'medium', hoặc 'large'
    """
    print(f"\n{'='*100}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*100}\n")
    
    # Pool ETH/USDC trên Base
    POOL_ADDRESS = "0x6c561B446416E1A00E8E93E221854d6eA4171372"
    TOKEN_ETH = "0x4200000000000000000000000000000000000006"
    TOKEN_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    
    # Fetch pool data
    print("📊 Bước 1: Lấy giá từ AMM Pool")
    pool_data = get_price_for_pool(POOL_ADDRESS)
    
    # Lấy sqrtPriceX96 để tính giá spot (giá TRƯỚC khi swap)
    slot0 = get_slot0(POOL_ADDRESS)
    token_info = get_pool_tokens_and_decimals(POOL_ADDRESS)
    price_spot = price_from_sqrtprice(
        slot0['sqrtPriceX96'],
        token_info['decimals0'],  # ETH = 18
        token_info['decimals1']   # USDC = 6
    )
    
    # Convert swap amount
    swap_amount_base = int(swap_amount_eth * 10**18)  # WETH có 18 decimals
    
    # Lấy giá SAU khi swap qua AMM để tính slippage
    amm_quote = get_amm_output(
        token_in=TOKEN_ETH,
        token_out=TOKEN_USDC,
        amount_in=swap_amount_base,
        fee=3000
    )
    price_after_swap = price_from_sqrtprice(
        amm_quote['sqrtPriceX96After'],
        token_info['decimals0'],
        token_info['decimals1']
    )
    
    print(f"   Pool: ETH/USDC")
    print(f"   Spot Price (before swap):  {float(price_spot):,.4f} USDC/ETH")
    print(f"   Price After Swap:          {float(price_after_swap):,.4f} USDC/ETH")
    print(f"   Price Impact:              {float((price_after_swap - price_spot) / price_spot * 100):+.4f}%\n")
    
    # Tính ideal output (theo giá spot) và actual output (theo giá sau swap)
    ideal_output = swap_amount_eth * float(price_spot)  # Giá spot (không có slippage)
    swap_amount_usd = swap_amount_eth * float(price_spot)  # Dùng spot price cho consistency
    
    print(f"💰 Swap Amount: {swap_amount_eth} ETH")
    print(f"   Value at spot price: {format_currency(ideal_output)}")
    print(f"   Actual AMM output:   {format_currency(float(amm_quote['amountOut']) / 10**6)}\n")
    
    # Baseline: 100% AMM - dùng actual AMM output
    print(f"\n📈 Bước 2: Tính baseline (100% AMM)")
    amm_reference_output = float(amm_quote['amountOut']) / 10**6  # USDC
    print(f"   Nếu swap 100% qua AMM: {amm_reference_output:,.2f} USDC")
    
    # Generate synthetic orderbook
    # Swap ETH → USDC: ta bán ETH, mua USDC
    # User bán ETH → ASK side (is_bid=False) 
    # ASK price < mid price (worse for seller, có spread)
    # Input: ETH (18 decimals), Output: USDC (6 decimals)
    print(f"\n📚 Bước 3: Generate Synthetic Orderbook ({scenario_type})")
    generator = SyntheticOrderbookGenerator(
        price_spot,  # Mid price = Spot price (theo góp ý leader)
        decimals_in=18,  # ETH input
        decimals_out=6   # USDC output
    )
    # is_bid=False → ASK side (giá THẤP hơn mid do spread)
    levels = generator.generate(scenario_type, swap_amount_base, is_bid=False)
    print(f"   Generated {len(levels)} orderbook levels")
    
    # Show top 3 levels
    if levels:
        print(f"   Top 3 levels:")
        for i, level in enumerate(levels[:3], 1):
            price = float(level.price)
            amount_eth = float(level.amount_in_available) / 10**18
            amount_usdc = float(level.amount_out_available) / 10**6
            print(f"      Level {i}: {price:,.2f} USDC/ETH | {amount_eth:.4f} ETH available | {amount_usdc:,.2f} USDC output")
    
    # Calculate AMM effective price (sau slippage)
    # AMM effective price = amount_out / amount_in
    # Đây là giá THỰC TẾ sau khi swap qua AMM (đã bao gồm slippage)
    amm_amount_out_usdc = float(amm_quote['amountOut']) / 10**6
    amm_effective_price = Decimal(str(amm_amount_out_usdc / swap_amount_eth))
    
    print(f"\n💡 AMM Effective Price (sau slippage): {float(amm_effective_price):,.4f} USDC/ETH")
    print(f"   Slippage vs spot: {float((amm_effective_price - price_spot) / price_spot * 10000):+.2f} bps")
    
    # Greedy matching
    print(f"\n🎯 Bước 4: Greedy Matching")
    matcher = GreedyMatcher(
        amm_effective_price,  # ✅ Dùng AMM effective price (SAU slippage) làm baseline
        decimals_in=18,
        decimals_out=6,
        ob_min_improve_bps=10  # ✅ OPTIMIZED: Threshold 10 bps (safety margin hợp lý)
    )
    # is_bid=False vì ta đang bán ETH (match với ask side)
    match_result = matcher.match(levels, swap_amount_base, is_bid=False)
    
    ob_amount_eth = float(match_result['amount_in_on_orderbook']) / 10**18
    amm_amount_eth = float(match_result['amount_in_on_amm']) / 10**18
    ob_percentage = (ob_amount_eth / swap_amount_eth * 100) if swap_amount_eth > 0 else 0
    amm_percentage = (amm_amount_eth / swap_amount_eth * 100) if swap_amount_eth > 0 else 0
    
    print(f"   Route qua Orderbook: {ob_amount_eth:.4f} ETH ({ob_percentage:.2f}%)")
    print(f"   Route qua AMM: {amm_amount_eth:.4f} ETH ({amm_percentage:.2f}%)")
    print(f"   Levels used: {len(match_result['levels_used'])}")
    
    # Build execution plan
    print(f"\n⚙️  Bước 5: Build Execution Plan")
    builder = ExecutionPlanBuilder(
        price_amm=amm_effective_price,  # Dùng AMM effective price (post-slippage) để tính savings
        decimals_in=18,
        decimals_out=6,
        performance_fee_bps=3000,  # 30%
        max_slippage_bps=100       # 1%
    )
    
    execution_plan = builder.build_plan(
        match_result=match_result,
        token_in_address=TOKEN_ETH,
        token_out_address=TOKEN_USDC,
        max_matches=8,
        me_slippage_limit=200
    )
    
    # Calculate results
    # Override AMM reference với actual output từ quoter
    amm_reference = amm_reference_output  # Đã tính ở trên từ get_amm_output()
    expected_total = float(execution_plan['expected_total_out']) / 10**6  # USDC
    savings_before = float(execution_plan['savings_before_fee']) / 10**6
    savings_after = float(execution_plan['savings_after_fee']) / 10**6
    perf_fee = float(execution_plan['performance_fee_amount']) / 10**6
    
    # Calculate slippage so với giá spot (sqrtPriceX96)
    # ideal_output = giá spot × amount (không có slippage)
    # amm_reference = actual AMM output (có slippage do price impact)
    slippage_original_usd = ideal_output - amm_reference
    slippage_original_bps = (slippage_original_usd / ideal_output * 10000) if ideal_output > 0 else 0
    
    slippage_optimized_usd = ideal_output - (expected_total - perf_fee)  # Sau khi trừ performance fee
    slippage_optimized_bps = (slippage_optimized_usd / ideal_output * 10000) if ideal_output > 0 else 0
    
    savings_bps = (savings_after / amm_reference * 10000) if amm_reference > 0 else 0
    
    # Print results
    print(f"\n{'='*100}")
    print(f"📊 KẾT QUẢ BACKTEST - {scenario_name}")
    print(f"{'='*100}\n")
    
    print(f"💵 Output Comparison:")
    print(f"   Ideal (no slippage):     {format_currency(ideal_output)} USDC")
    print(f"   AMM Reference (100%):    {format_currency(amm_reference)} USDC")
    print(f"   UniHybrid Total Output:  {format_currency(expected_total)} USDC")
    print(f"   Performance Fee (30%):   {format_currency(perf_fee)} USDC")
    print(f"   Net to User:             {format_currency(expected_total - perf_fee)} USDC\n")
    
    print(f"📈 Savings:")
    print(f"   Savings Before Fee:      {format_currency(savings_before)} ({savings_bps:.2f} bps)")
    print(f"   Savings After Fee:       {format_currency(savings_after)} ({savings_bps:.2f} bps)\n")
    
    print(f"📉 Slippage:")
    print(f"   Slippage gốc (AMM):      {format_bps(slippage_original_bps)} (~{format_currency(slippage_original_usd)})")
    print(f"   Slippage sau tối ưu:     {format_bps(slippage_optimized_bps)} (~{format_currency(slippage_optimized_usd)})")
    print(f"   Improvement:             {format_bps(slippage_original_bps - slippage_optimized_bps)}\n")
    
    # Table row for report
    print(f"{'='*100}")
    print(f"📋 DÒNG CHO BẢNG BÁO CÁO:")
    print(f"{'='*100}\n")
    
    pair_description = f"ETH-USDC ({scenario_type} liquidity)"
    
    print(f"| {pair_description:50s} | {ob_percentage:6.2f}% | {amm_percentage:6.2f}% | "
          f"{format_bps(slippage_original_bps):15s} | "
          f"{format_currency(savings_after):12s} ({savings_bps:.0f} bps) | "
          f"{format_bps(slippage_optimized_bps):15s} |")
    
    return {
        'scenario': scenario_name,
        'ob_percentage': ob_percentage,
        'amm_percentage': amm_percentage,
        'slippage_original_bps': slippage_original_bps,
        'slippage_original_usd': slippage_original_usd,
        'savings_usd': savings_after,
        'savings_bps': savings_bps,
        'slippage_optimized_bps': slippage_optimized_bps,
        'slippage_optimized_usd': slippage_optimized_usd
    }


def main():
    print("\n" + "="*100)
    print("🔬 BACKTEST: UNIHYBRID vs 100% AMM")
    print("="*100)
    print("\nSwap: ETH → USDC trên Base network")
    print("Khối lượng: ~$100,000 USD")
    print("="*100)
    
    # Run scenarios
    results = []
    
    # Scenario 1: Small liquidity (shallow orderbook)
    results.append(run_backtest_scenario(
        "Case 1: Shallow Orderbook",
        swap_amount_eth=33.0,
        scenario_type='small'
    ))
    
    # Scenario 2: Medium liquidity
    results.append(run_backtest_scenario(
        "Case 2: Medium Orderbook", 
        swap_amount_eth=33.0,
        scenario_type='medium'
    ))
    
    # Scenario 3: Deep liquidity
    results.append(run_backtest_scenario(
        "Case 3: Deep Orderbook",
        swap_amount_eth=33.0,
        scenario_type='large'
    ))
    
    # Summary table
    print(f"\n\n{'='*100}")
    print("📊 BẢNG TỔNG HỢP KẾT QUẢ")
    print(f"{'='*100}\n")
    
    print("| Trường hợp lệnh $100,000 | Tỷ lệ qua OB | Tỷ lệ vào AMM | Slippage gốc* | Savings | Slippage sau tối ưu* |")
    print("|" + "-"*25 + "|" + "-"*14 + "|" + "-"*15 + "|" + "-"*15 + "|" + "-"*25 + "|" + "-"*22 + "|")
    
    for r in results:
        pair_desc = f"ETH-USDC ({r['scenario']})"
        print(f"| {pair_desc:50s} | {r['ob_percentage']:6.2f}% | {r['amm_percentage']:6.2f}% | "
              f"{format_bps(r['slippage_original_bps']):15s} | "
              f"{format_currency(r['savings_usd']):12s} ({r['savings_bps']:.0f} bps) | "
              f"{format_bps(r['slippage_optimized_bps']):15s} |")
    
    print(f"\n{'='*100}")
    print("✅ BACKTEST HOÀN TẤT!")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
