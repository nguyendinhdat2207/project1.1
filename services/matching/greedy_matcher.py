from decimal import Decimal
from typing import List, Dict, Literal
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.orderbook import OrderbookLevel


@dataclass
class LevelUsed:
    price: Decimal
    amount_in_from_level: int
    amount_out_from_level: int


class GreedyMatcher:
    
    def __init__(
        self,
        price_amm: Decimal,
        decimals_in: int,
        decimals_out: int,
        ob_min_improve_bps: int = 5
    ):
        self.price_amm = price_amm
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
        self.ob_min_improve_bps = ob_min_improve_bps
    
    def match(
        self,
        levels: List[OrderbookLevel],
        swap_amount: int,
        is_bid: bool = False
    ) -> Dict:
        """
        Greedy matching algorithm.
        
        - is_bid=False (ASK): User mua tokenOut bằng tokenIn
          → Muốn giá THẤP (mua rẻ hơn AMM)
          → Sort levels từ THẤP → CAO
          → Dùng levels có price < AMM * (1 + margin)
        
        - is_bid=True (BID): User bán tokenIn lấy tokenOut  
          → Muốn giá CAO (bán đắt hơn AMM)
          → Sort levels từ CAO → THẤP
          → Dùng levels có price > AMM * (1 - margin)
        """
        
        # Calculate price threshold based on direction
        if is_bid:
            # BID: User bán tokenIn → muốn giá CAO hơn AMM
            # Chỉ dùng levels có price >= AMM * (1 - margin)
            min_better_price = self.price_amm * (
                Decimal('1') - Decimal(self.ob_min_improve_bps) / Decimal('10000')
            )
        else:
            # ASK: User mua tokenOut → muốn giá THẤP hơn AMM
            # Chỉ dùng levels có price <= AMM * (1 + margin)
            min_better_price = self.price_amm * (
                Decimal('1') + Decimal(self.ob_min_improve_bps) / Decimal('10000')
            )
        
        # Sort levels based on direction
        # BID: cao → thấp (reverse=True) - bán với giá cao nhất trước
        # ASK: thấp → cao (reverse=False) - mua với giá thấp nhất trước
        sorted_levels = sorted(
            levels,
            key=lambda lvl: lvl.price,
            reverse=is_bid
        )
        
        remaining_in = swap_amount
        amount_in_on_orderbook = 0
        amount_out_from_orderbook = 0
        levels_used: List[LevelUsed] = []
        levels_better_than_amm = 0
        
        for level in sorted_levels:
            # Check if level price is still better than AMM
            if is_bid:
                # BID: Dừng nếu giá quá thấp (< threshold)
                if level.price < min_better_price:
                    break
            else:
                # ASK: Dừng nếu giá quá cao (> threshold)
                if level.price > min_better_price:
                    break
            
            levels_better_than_amm += 1
            
            if remaining_in == 0:
                break
            
            fill_in = min(remaining_in, level.amount_in_available)
            
            if fill_in == 0:
                continue
            
            fill_out = level.amount_out_available if fill_in == level.amount_in_available else int(
                Decimal(fill_in) * level.price * Decimal(10 ** self.decimals_out) / Decimal(10 ** self.decimals_in)
            )
            
            amount_in_on_orderbook += fill_in
            amount_out_from_orderbook += fill_out
            remaining_in -= fill_in
            
            levels_used.append(
                LevelUsed(
                    price=level.price,
                    amount_in_from_level=fill_in,
                    amount_out_from_level=fill_out
                )
            )
        
        amount_in_on_amm = remaining_in
        
        return {
            'amount_in_on_orderbook': amount_in_on_orderbook,
            'amount_out_from_orderbook': amount_out_from_orderbook,
            'amount_in_on_amm': amount_in_on_amm,
            'levels_used': levels_used,
            'total_levels_available': len(sorted_levels),
            'levels_better_than_amm': levels_better_than_amm,
            'min_better_price': min_better_price,
            'price_amm': self.price_amm
        }
    
    def calculate_savings(
        self,
        match_result: Dict,
        amm_reference_out: int
    ) -> Dict:
        
        amount_out_from_amm = 0
        if match_result['amount_in_on_amm'] > 0:
            amount_out_from_amm = int(
                Decimal(match_result['amount_in_on_amm']) * 
                self.price_amm * 
                Decimal(10 ** self.decimals_out) / 
                Decimal(10 ** self.decimals_in)
            )
        
        expected_total_out = (
            match_result['amount_out_from_orderbook'] + 
            amount_out_from_amm
        )
        
        savings_before_fee = expected_total_out - amm_reference_out
        
        PERFORMANCE_FEE_BPS = 3000
        performance_fee_amount = savings_before_fee * PERFORMANCE_FEE_BPS // 10000
        savings_after_fee = savings_before_fee - performance_fee_amount
        
        performance_fee_bps = 0
        if expected_total_out > 0:
            performance_fee_bps = (performance_fee_amount * 10000) // expected_total_out
        
        return {
            'expected_total_out': expected_total_out,
            'amount_out_from_amm': amount_out_from_amm,
            'amm_reference_out': amm_reference_out,
            'savings_before_fee': savings_before_fee,
            'savings_after_fee': savings_after_fee,
            'performance_fee_amount': performance_fee_amount,
            'performance_fee_bps': performance_fee_bps
        }


if __name__ == "__main__":
    print("=" * 70)
    print("GREEDY MATCHER TEST (Module 3)")
    print("=" * 70)
    print()
    
    # Test scenario: User wants to swap 5000 USDC → ETH
    # Using synthetic orderbook from Module 2
    
    from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
    from services.orderbook import SyntheticOrderbookGenerator
    
    # Step 1: Get AMM price (Module 1)
    print("STEP 1: Fetch AMM price from Uniswap V3")
    print("-" * 70)
    pool_address = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    pool_data = get_price_for_pool(pool_address)
    
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    print(f"Pool: {pool_address}")
    print(f"Mid Price: {price_usdt_per_eth} USDT/ETH")
    print()
    
    # For USDT→ETH swap, we need ETH/USDC price
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    # Step 2: Generate orderbook (Module 2)
    print("STEP 2: Generate synthetic orderbook")
    print("-" * 70)
    swap_amount = 5000 * 10**6  # 5000 USDC
    
    generator = SyntheticOrderbookGenerator(
        mid_price=price_eth_per_usdt,
        decimals_in=6,   # USDC
        decimals_out=18  # ETH
    )
    
    print(f"Swap Amount: {swap_amount / 10**6:.2f} USDT")
    print()
    
    # Test all 3 scenarios
    for scenario_name in ['small', 'medium', 'large']:
        print("=" * 70)
        print(f"SCENARIO: {scenario_name.upper()}")
        print("=" * 70)
        print()
        
        # Generate orderbook
        capital = Decimal('1000000') if scenario_name == 'large' else None
        levels = generator.generate(
            scenario_name, 
            swap_amount, 
            is_bid=False,
            capital_usd=capital
        )
        
        print(f"Generated {len(levels)} orderbook levels")
        print()
        
        # Step 3: Greedy matching (Module 3)
        print("STEP 3: Execute greedy matching")
        print("-" * 70)
        
        # Test with different ob_min_improve_bps values
        for improve_bps in [5, 10, 20]:
            print(f"\n📊 ob_min_improve_bps = {improve_bps} bps:")
            print()
            
            matcher = GreedyMatcher(
                price_amm=price_eth_per_usdt,
                decimals_in=6,
                decimals_out=18,
                ob_min_improve_bps=improve_bps
            )
            
            result = matcher.match(levels, swap_amount, is_bid=False)
            
            # Display results
            print(f"  Min Better Price: {Decimal('1')/result['min_better_price']:.2f} USDT/ETH")
            print(f"  AMM Price:        {Decimal('1')/result['price_amm']:.2f} USDT/ETH")
            print()
            
            print(f"  Levels available:      {result['total_levels_available']}")
            print(f"  Levels better than AMM: {result['levels_better_than_amm']}")
            print(f"  Levels used:           {len(result['levels_used'])}")
            print()
            
            ob_amount = result['amount_in_on_orderbook']
            amm_amount = result['amount_in_on_amm']
            ob_out = result['amount_out_from_orderbook']
            
            print(f"  Amount on Orderbook: {ob_amount / 10**6:,.2f} USDT ({ob_amount * 100 // swap_amount}%)")
            print(f"  Amount on AMM:       {amm_amount / 10**6:,.2f} USDT ({amm_amount * 100 // swap_amount}%)")
            print(f"  Output from OB:      {ob_out / 10**18:.6f} ETH")
            print()
            
            # Show levels used
            if len(result['levels_used']) > 0:
                print(f"  Levels filled:")
                for i, level_used in enumerate(result['levels_used'][:5], 1):
                    price_display = Decimal('1') / level_used.price
                    amt_in = level_used.amount_in_from_level / 10**6
                    amt_out = level_used.amount_out_from_level / 10**18
                    print(f"    Level {i}: {price_display:.2f} USDT/ETH | {amt_in:.2f} USDT → {amt_out:.6f} ETH")
                
                if len(result['levels_used']) > 5:
                    print(f"    ... ({len(result['levels_used']) - 5} more levels)")
            
            print()
        
        print()
    
    print("=" * 70)
    print("✅ Greedy Matcher test completed!")
    print("=" * 70)
