"""
Test VirtualOrderBook - Ví dụ và test cases cho 3 scenarios

Chạy: python -m pytest tests/unit/test_virtual_orderbook.py -v
"""

import json
from decimal import Decimal
from services.execution.ui.virtual_orderbook import (
    VirtualOrderBook,
    generate_sample_cex_snapshot
)


def test_scenario_small():
    """
    Test Scenario 1 - Small:
    1 level duy nhất quanh mid, depth ~ 0.5 × swap_amount
    """
    print("\n" + "="*80)
    print("📦 TEST SCENARIO 1: SMALL")
    print("="*80)
    
    mid_price = 2700.0  # USDC per ETH
    swap_amount = 1.0   # 1 ETH
    
    vob = VirtualOrderBook(mid_price=mid_price)
    
    orderbook = vob.build_orderbook(
        swap_amount=swap_amount,
        scenario='small',
        spread_step_bps=10  # 0.1%
    )
    
    print(f"\n💱 Mid Price: ${mid_price} USDC/ETH")
    print(f"📥 Swap Amount: {swap_amount} ETH")
    print(f"\n📊 ORDERBOOK SNAPSHOT:")
    print(json.dumps(orderbook, indent=2))
    
    print(f"\n✅ Best Bid: ${orderbook['best_bid']['price']:.2f}, {orderbook['best_bid']['amount_in_available']:.4f} ETH")
    print(f"✅ Best Ask: ${orderbook['best_ask']['price']:.2f}, {orderbook['best_ask']['amount_in_available']:.4f} ETH")
    print(f"✅ Spread: {orderbook['spread_bps']:.2f} bps ({orderbook['spread_bps']/100:.4f}%)")
    print(f"✅ Total Bid Liquidity: {orderbook['total_bid_liquidity']:.4f} ETH")
    print(f"✅ Total Ask Liquidity: {orderbook['total_ask_liquidity']:.4f} ETH")


def test_scenario_medium():
    """
    Test Scenario 2 - Medium:
    3-5 levels quanh mid, spread 10-30 bps/level, size decay
    """
    print("\n" + "="*80)
    print("📦 TEST SCENARIO 2: MEDIUM")
    print("="*80)
    
    mid_price = 2700.0
    swap_amount = 1.0
    
    vob = VirtualOrderBook(mid_price=mid_price)
    
    orderbook = vob.build_orderbook(
        swap_amount=swap_amount,
        scenario='medium',
        spread_step_bps=10,      # 10 bps = 0.1% per level
        base_size=2.0,           # 2 × swap_amount
        decay=0.5                # Size giảm 50% mỗi level
    )
    
    print(f"\n💱 Mid Price: ${mid_price} USDC/ETH")
    print(f"📥 Swap Amount: {swap_amount} ETH")
    print(f"📊 Config: base_size=2.0 ETH, decay=0.5, spread_step=10 bps")
    
    print(f"\n📋 BID LEVELS (Price < Mid):")
    for level in orderbook['bid_levels']:
        print(f"   Level {level.get('level', '?')}: ${level['price']:.4f} | "
              f"{level['amount_in_available']:.4f} ETH")
    
    print(f"\n📋 ASK LEVELS (Price > Mid):")
    for level in orderbook['ask_levels']:
        print(f"   Level {level.get('level', '?')}: ${level['price']:.4f} | "
              f"{level['amount_in_available']:.4f} ETH")
    
    print(f"\n✅ Best Bid: ${orderbook['best_bid']['price']:.4f}, {orderbook['best_bid']['amount_in_available']:.4f} ETH")
    print(f"✅ Best Ask: ${orderbook['best_ask']['price']:.4f}, {orderbook['best_ask']['amount_in_available']:.4f} ETH")
    print(f"✅ Spread: {orderbook['spread_bps']:.2f} bps ({orderbook['spread_bps']/100:.4f}%)")
    print(f"✅ Total Bid Liquidity: {orderbook['total_bid_liquidity']:.4f} ETH")
    print(f"✅ Total Ask Liquidity: {orderbook['total_ask_liquidity']:.4f} ETH")


def test_scenario_large():
    """
    Test Scenario 3 - Large / Binance-like:
    Shape từ CEX snapshot, scale theo capital_usd
    """
    print("\n" + "="*80)
    print("📦 TEST SCENARIO 3: LARGE / CEX-LIKE")
    print("="*80)
    
    mid_price = 2700.0
    capital_usd = 50000  # UniHybrid capital
    
    # Generate sample CEX snapshot
    cex_snapshot = generate_sample_cex_snapshot(
        mid_price=mid_price,
        num_levels=5,
        depth_percent=0.02,
        base_size=10.0,
        decay=0.7
    )
    
    print(f"\n💱 Mid Price: ${mid_price} USDC/ETH")
    print(f"💰 UniHybrid Capital: ${capital_usd:,.0f}")
    print(f"📊 CEX Snapshot: {len(cex_snapshot)} levels")
    
    print(f"\n📋 CEX SNAPSHOT (input):")
    for level in sorted(cex_snapshot, key=lambda x: x['price'], reverse=True)[:3]:
        print(f"   {level['side'].upper()}: ${level['price']:.2f} | {level['size']:.2f} ETH")
    print(f"   ...")
    
    vob = VirtualOrderBook(mid_price=mid_price)
    
    orderbook = vob.build_orderbook(
        swap_amount=1.0,  # Not used directly in large, but for context
        scenario='large',
        capital_usd=capital_usd,
        cex_snapshot=cex_snapshot
    )
    
    print(f"\n📋 VIRTUAL ORDERBOOK (output, scaled to ${capital_usd:,.0f}):")
    
    print(f"\n   BID LEVELS (Price < Mid):")
    for i, level in enumerate(orderbook['bid_levels'][:3]):
        print(f"      [{i}] ${level['price']:.4f} | {level['amount_in_available']:.4f} ETH")
    if len(orderbook['bid_levels']) > 3:
        print(f"      ... ({len(orderbook['bid_levels']) - 3} more)")
    
    print(f"\n   ASK LEVELS (Price > Mid):")
    for i, level in enumerate(orderbook['ask_levels'][:3]):
        print(f"      [{i}] ${level['price']:.4f} | {level['amount_in_available']:.4f} ETH")
    if len(orderbook['ask_levels']) > 3:
        print(f"      ... ({len(orderbook['ask_levels']) - 3} more)")
    
    print(f"\n✅ Best Bid: ${orderbook['best_bid']['price']:.4f}, {orderbook['best_bid']['amount_in_available']:.4f} ETH")
    print(f"✅ Best Ask: ${orderbook['best_ask']['price']:.4f}, {orderbook['best_ask']['amount_in_available']:.4f} ETH")
    print(f"✅ Spread: {orderbook['spread_bps']:.2f} bps ({orderbook['spread_bps']/100:.4f}%)")
    print(f"✅ Total Bid Liquidity: {orderbook['total_bid_liquidity']:.4f} ETH")
    print(f"✅ Total Ask Liquidity: {orderbook['total_ask_liquidity']:.4f} ETH")


def test_scenario_comparison():
    """
    So sánh 3 scenarios với cùng mid_price
    """
    print("\n" + "="*80)
    print("🔍 SO SÁNH 3 SCENARIOS")
    print("="*80)
    
    mid_price = 2700.0
    swap_amount = 1.0
    
    results = {}
    
    # Small
    vob_small = VirtualOrderBook(mid_price=mid_price)
    results['small'] = vob_small.build_orderbook(
        swap_amount=swap_amount,
        scenario='small',
        spread_step_bps=10
    )
    
    # Medium
    vob_medium = VirtualOrderBook(mid_price=mid_price)
    results['medium'] = vob_medium.build_orderbook(
        swap_amount=swap_amount,
        scenario='medium',
        spread_step_bps=10,
        base_size=2.0,
        decay=0.5
    )
    
    # Large
    cex_snapshot = generate_sample_cex_snapshot(mid_price=mid_price, num_levels=5)
    vob_large = VirtualOrderBook(mid_price=mid_price)
    results['large'] = vob_large.build_orderbook(
        swap_amount=swap_amount,
        scenario='large',
        capital_usd=50000,
        cex_snapshot=cex_snapshot
    )
    
    print(f"\n{'Scenario':<15} {'Levels':<10} {'Spread (bps)':<15} {'Total Liquidity':<20}")
    print("-" * 60)
    
    for scenario, ob in results.items():
        num_levels = len(ob['bid_levels']) + len(ob['ask_levels'])
        spread = ob['spread_bps'] or 0
        total_liq = ob['total_bid_liquidity'] + ob['total_ask_liquidity']
        
        print(f"{scenario:<15} {num_levels:<10} {spread:<15.2f} {total_liq:<20.4f} ETH")
    
    print("\n📌 Observations:")
    print("   - Small: Minimal levels, high spread (test/low liquidity scenarios)")
    print("   - Medium: Balanced liquidity with size decay (typical DEX scenarios)")
    print("   - Large: Deep book with CEX shape, scaled to capital (competitive scenarios)")


def test_decimal_precision():
    """
    Test tính toán với Decimal để đảm bảo precision
    """
    print("\n" + "="*80)
    print("🔬 TEST DECIMAL PRECISION")
    print("="*80)
    
    mid_price = Decimal('2700.123456789')
    swap_amount = Decimal('1.5')
    
    vob = VirtualOrderBook(mid_price=mid_price)
    
    orderbook = vob.build_orderbook(
        swap_amount=swap_amount,
        scenario='medium',
        spread_step_bps=10,
        base_size=Decimal('3.5'),
        decay=0.5
    )
    
    print(f"\n✅ Mid Price (Decimal): {mid_price}")
    print(f"✅ Swap Amount (Decimal): {swap_amount}")
    print(f"✅ Best Bid Price: {orderbook['best_bid']['price']}")
    print(f"✅ Best Ask Price: {orderbook['best_ask']['price']}")
    print(f"✅ Spread (bps): {orderbook['spread_bps']}")


if __name__ == '__main__':
    print("\n🚀 VIRTUAL ORDERBOOK TEST SUITE\n")
    
    try:
        test_scenario_small()
        test_scenario_medium()
        test_scenario_large()
        test_scenario_comparison()
        test_decimal_precision()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
