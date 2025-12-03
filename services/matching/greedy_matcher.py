"""
Module 3: Greedy Matcher

Implements the greedy matching algorithm to split swap between Orderbook and AMM.

Algorithm (per spec):
1. Calculate minBetterPrice = price_AMM * (1 + ob_min_improve_bps / 10_000)
2. Sort orderbook levels by price (best to worst)
3. Greedy fill levels that beat minBetterPrice
4. Fallback remaining amount to AMM

Author: UniHybrid Team
Date: 2025-12-02
"""

from decimal import Decimal
from typing import List, Dict, Literal
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from Module 2
from services.orderbook import OrderbookLevel


@dataclass
class LevelUsed:
    """
    Represents an orderbook level that was used in the greedy matching.
    
    Attributes:
        price: Price of this level (token_out / token_in)
        amount_in_from_level: Amount of token_in filled from this level (base units)
        amount_out_from_level: Amount of token_out received from this level (base units)
    """
    price: Decimal
    amount_in_from_level: int
    amount_out_from_level: int


class GreedyMatcher:
    """
    Greedy matching algorithm to split swap between Orderbook and AMM.
    
    Design Philosophy:
    - Only use orderbook levels that are better than AMM by at least ob_min_improve_bps
    - Greedy fill from best price to worst price
    - Fallback remaining amount to AMM
    
    This is the core logic for UniHybrid's hybrid routing strategy.
    """
    
    def __init__(
        self,
        price_amm: Decimal,
        decimals_in: int,
        decimals_out: int,
        ob_min_improve_bps: int = 5
    ):
        """
        Initialize greedy matcher.
        
        Args:
            price_amm: AMM mid price (token_out / token_in)
            decimals_in: Decimals of input token
            decimals_out: Decimals of output token
            ob_min_improve_bps: Minimum improvement orderbook must have over AMM (bps)
                              Default: 5 bps = 0.05%
        """
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
        Execute greedy matching algorithm.
        
        Algorithm (per spec):
        1. Calculate minBetterPrice threshold
        2. Sort levels by price (best to worst for user)
        3. Greedy fill levels that beat threshold
        4. Calculate AMM fallback for remaining amount
        
        Args:
            levels: List of orderbook levels from Module 2
            swap_amount: Total amount user wants to swap (base units of token_in)
            is_bid: True if user is selling base (bid side), False if buying (ask side)
            
        Returns:
            Dict with:
                - amount_in_on_orderbook: Amount going through orderbook
                - amount_out_from_orderbook: Amount received from orderbook
                - amount_in_on_amm: Amount going through AMM (fallback)
                - levels_used: List of LevelUsed showing which levels were filled
                - total_levels_available: Total number of levels considered
                - levels_better_than_amm: Number of levels that beat AMM threshold
        
        Example:
            For user buying ETH with 5000 USDT:
            - price_amm = 0.000357 ETH/USDT (2800 USDT/ETH inverted)
            - ob_min_improve_bps = 5
            - minBetterPrice = 0.000357 * 1.0005 = 0.000357178 ETH/USDT
            - Only use orderbook levels with price >= 0.000357178
            - Fill greedily from best to worst until swap_amount exhausted
        """
        # Step 1: Calculate minimum price threshold for orderbook
        # For ask side (user buying base): OB must give MORE output per input
        # For bid side (user selling base): OB must give MORE output per input
        # => In both cases, higher price is better for user
        min_better_price = self.price_amm * (
            Decimal('1') + Decimal(self.ob_min_improve_bps) / Decimal('10000')
        )
        
        # Step 2: Sort levels by price (best to worst for user)
        # Higher price = better for user (more token_out per token_in)
        sorted_levels = sorted(
            levels,
            key=lambda lvl: lvl.price,
            reverse=True  # Best price first
        )
        
        # Step 3: Greedy matching
        remaining_in = swap_amount
        amount_in_on_orderbook = 0
        amount_out_from_orderbook = 0
        levels_used: List[LevelUsed] = []
        levels_better_than_amm = 0
        
        for level in sorted_levels:
            # Check if this level beats AMM threshold
            if level.price < min_better_price:
                # This level and all subsequent levels are worse than AMM
                # Stop greedy matching
                break
            
            levels_better_than_amm += 1
            
            # Check if we still have amount to fill
            if remaining_in == 0:
                break
            
            # Calculate how much we can fill from this level
            fill_in = min(remaining_in, level.amount_in_available)
            
            if fill_in == 0:
                continue
            
            # Calculate output from this level
            fill_out = level.amount_out_available if fill_in == level.amount_in_available else int(
                Decimal(fill_in) * level.price * Decimal(10 ** self.decimals_out) / Decimal(10 ** self.decimals_in)
            )
            
            # Update totals
            amount_in_on_orderbook += fill_in
            amount_out_from_orderbook += fill_out
            remaining_in -= fill_in
            
            # Record this level usage
            levels_used.append(
                LevelUsed(
                    price=level.price,
                    amount_in_from_level=fill_in,
                    amount_out_from_level=fill_out
                )
            )
        
        # Step 4: Calculate AMM fallback
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
        """
        Calculate savings compared to 100% AMM swap.
        
        Args:
            match_result: Result from match() method
            amm_reference_out: Amount user would get from 100% AMM swap (from Module 1 Quoter)
            
        Returns:
            Dict with:
                - expected_total_out: Total output from UniHybrid (OB + AMM)
                - amm_reference_out: Output from 100% AMM (baseline)
                - savings_before_fee: expected_total_out - amm_reference_out
                - savings_after_fee: savings after performance fee (30% default)
                - performance_fee_amount: Fee charged (30% of savings)
                - performance_fee_bps: Fee as basis points of total output
        """
        # Calculate expected output from AMM leg
        amount_out_from_amm = 0
        if match_result['amount_in_on_amm'] > 0:
            # Simulate AMM swap for remaining amount
            # For simplicity, use linear approximation: out = in * price_amm
            # In production, should call Quoter for exact amount
            amount_out_from_amm = int(
                Decimal(match_result['amount_in_on_amm']) * 
                self.price_amm * 
                Decimal(10 ** self.decimals_out) / 
                Decimal(10 ** self.decimals_in)
            )
        
        # Total expected output
        expected_total_out = (
            match_result['amount_out_from_orderbook'] + 
            amount_out_from_amm
        )
        
        # Calculate savings
        savings_before_fee = expected_total_out - amm_reference_out
        
        # Performance fee: 30% of savings (per spec)
        PERFORMANCE_FEE_BPS = 3000  # 30%
        performance_fee_amount = savings_before_fee * PERFORMANCE_FEE_BPS // 10000
        savings_after_fee = savings_before_fee - performance_fee_amount
        
        # Calculate fee as bps of total output
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


# ============================================
# Test when run as script
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("GREEDY MATCHER TEST (Module 3)")
    print("=" * 70)
    print()
    
    # Test scenario: User wants to swap 5000 USDT → ETH
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
    
    # For USDT→ETH swap, we need ETH/USDT price
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    # Step 2: Generate orderbook (Module 2)
    print("STEP 2: Generate synthetic orderbook")
    print("-" * 70)
    swap_amount = 5000 * 10**6  # 5000 USDT
    
    generator = SyntheticOrderbookGenerator(
        mid_price=price_eth_per_usdt,
        decimals_in=6,   # USDT
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
