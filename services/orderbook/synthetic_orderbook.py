"""
Module 2: Synthetic Orderbook Generator

Generates synthetic orderbook for 3 scenarios:
- Small: depth ~0.5× swapAmount, 1 level, spread 30 bps
- Medium: depth ~2.5× swapAmount, 3-5 levels, spread 10-20 bps  
- Large: CEX-like shape, scaled by capital (e.g., $1M)

Author: UniHybrid Team
Date: 2025-12-02
"""

from decimal import Decimal
from typing import List, Dict, Literal
from dataclasses import dataclass


@dataclass
class OrderbookLevel:
    """
    Represents a single price level in the orderbook.
    
    Attributes:
        price: Price in token_out/token_in (e.g., USDT per ETH)
        amount_in_available: Amount of token_in that can be filled at this level (base units)
        amount_out_available: Amount of token_out available at this level (base units)
    """
    price: Decimal
    amount_in_available: int
    amount_out_available: int


class SyntheticOrderbookGenerator:
    """
    Generates synthetic orderbook levels for different scenarios.
    
    Design Philosophy:
    - Scenario 1 (small): Worst case - orderbook very thin, UniHybrid barely better than AMM
    - Scenario 2 (medium): Realistic case - moderate depth, decent improvement over AMM
    - Scenario 3 (large): Best case - CEX-like depth, significant savings vs AMM
    """
    
    def __init__(
        self,
        mid_price: Decimal,
        decimals_in: int,
        decimals_out: int
    ):
        """
        Initialize orderbook generator.
        
        Args:
            mid_price: Mid price from AMM (token_out / token_in)
            decimals_in: Decimals of input token (e.g., 18 for ETH)
            decimals_out: Decimals of output token (e.g., 6 for USDT)
        """
        self.mid_price = mid_price
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
    
    def generate_scenario_small(
        self,
        swap_amount: int,
        is_bid: bool = False
    ) -> List[OrderbookLevel]:
        """
        Generate "small" orderbook scenario.
        
        Characteristics:
        - Total depth: ~0.5× swap_amount
        - Only 1 meaningful level
        - Spread: 30 bps from mid
        - Use case: Worst case testing
        
        Args:
            swap_amount: Amount user wants to swap (base units of token_in)
            is_bid: True if generating bid side (user selling base), False for ask side
            
        Returns:
            List of OrderbookLevel objects
        """
        # Configuration
        DEPTH_MULTIPLIER = Decimal('0.5')
        SPREAD_BPS = Decimal('30')  # 30 bps = 0.3%
        
        # Calculate price
        if is_bid:
            # Bid side: price below mid (user selling base asset)
            price = self.mid_price * (1 - SPREAD_BPS / Decimal('10000'))
        else:
            # Ask side: price above mid (user buying base asset)
            price = self.mid_price * (1 + SPREAD_BPS / Decimal('10000'))
        
        # Calculate size
        amount_in_available = int(Decimal(swap_amount) * DEPTH_MULTIPLIER)
        amount_out_available = self._calculate_amount_out(amount_in_available, price)
        
        return [
            OrderbookLevel(
                price=price,
                amount_in_available=amount_in_available,
                amount_out_available=amount_out_available
            )
        ]
    
    def generate_scenario_medium(
        self,
        swap_amount: int,
        is_bid: bool = False,
        num_levels: int = 5,
        spread_step_bps: Decimal = Decimal('15'),
        base_size_multiplier: Decimal = Decimal('1.0'),
        decay_factor: Decimal = Decimal('0.7'),
        target_depth_multiplier: Decimal = Decimal('2.5')
    ) -> List[OrderbookLevel]:
        """
        Generate "medium" orderbook scenario with ladder structure.
        
        Characteristics:
        - Default 5 levels (per spec: maxLevels ≈ 5)
        - Ladder pricing: each level spread_step_bps away from mid
        - Spread: 10-20 bps per level (default: 15 bps)
        - Base size: ~1× swapAmount at level 1 (per spec)
        - Exponential size decay: decay ≈ 0.7 (per spec)
        - Total depth: ~2-3× swapAmount after scaling
        - Use case: Realistic MM scenario
        
        Algorithm:
        1. Generate ladder prices: mid × (1 ± i × spread_step)
        2. Calculate sizes with decay: base_size × decay^(i-1)
        3. Scale all sizes to match target_depth_multiplier
        
        Args:
            swap_amount: Amount user wants to swap (base units)
            is_bid: True if bid side, False for ask side
            num_levels: Number of price levels (default: 5, per spec)
            spread_step_bps: Spread per level in bps (default: 15 bps, in 10-20 range)
            base_size_multiplier: Base size as multiplier of swap_amount (default: 1.0, per spec)
            decay_factor: Size decay between levels (default: 0.7, per spec)
            target_depth_multiplier: Target total depth as multiplier of swap_amount (default: 2.5)
            
        Returns:
            List of OrderbookLevel objects (sorted best to worst price)
            
        Example (per spec):
            For swap_amount = 1000 USDC, num_levels = 5:
            - Level 1: price = mid × 1.0015, size = 1.0 × 1000 = 1000 USDC
            - Level 2: price = mid × 1.0030, size = 1.0 × 1000 × 0.7 = 700 USDC
            - Level 3: price = mid × 1.0045, size = 1.0 × 1000 × 0.7² = 490 USDC
            - Level 4: price = mid × 1.0060, size = 343 USDC
            - Level 5: price = mid × 1.0075, size = 240 USDC
            Total unscaled = 2773 USDC → scale to 2500 USDC (2.5×)
        """
        levels: List[OrderbookLevel] = []
        total_unscaled = Decimal('0')
        
        # Step 1: Generate unscaled levels with ladder pricing + exponential decay
        for i in range(1, num_levels + 1):
            # Ladder pricing
            spread = spread_step_bps * i / Decimal('10000')
            if is_bid:
                price = self.mid_price * (1 - spread)
            else:
                price = self.mid_price * (1 + spread)
            
            # Exponential decay size
            size_multiplier = base_size_multiplier * (decay_factor ** (i - 1))
            amount_in_unscaled = Decimal(swap_amount) * size_multiplier
            total_unscaled += amount_in_unscaled
            
            levels.append({
                'price': price,
                'amount_in_unscaled': amount_in_unscaled
            })
        
        # Step 2: Scale to target depth
        target_total = Decimal(swap_amount) * target_depth_multiplier
        scale_factor = target_total / total_unscaled if total_unscaled > 0 else Decimal('1')
        
        # Step 3: Apply scaling and convert to OrderbookLevel
        result: List[OrderbookLevel] = []
        for level_data in levels:
            amount_in_available = int(level_data['amount_in_unscaled'] * scale_factor)
            amount_out_available = self._calculate_amount_out(
                amount_in_available, 
                level_data['price']
            )
            
            result.append(
                OrderbookLevel(
                    price=level_data['price'],
                    amount_in_available=amount_in_available,
                    amount_out_available=amount_out_available
                )
            )
        
        return result
    
    def generate_scenario_large(
        self,
        swap_amount: int,
        capital_usd: Decimal = Decimal('1000000'),  # $1M default
        is_bid: bool = False
    ) -> List[OrderbookLevel]:
        """
        Generate "large" orderbook scenario (CEX-like).
        
        Characteristics:
        - Deep orderbook scaled from CEX snapshot
        - Total depth: scaled by capital_usd
        - Tight spreads (similar to Binance/Coinbase)
        - 5+ levels with realistic distribution
        - Use case: Long-term best case scenario
        
        NOTE: capital_usd represents total capital allocated in USD terms.
              For ask side (user buying ETH with USDT), capital is in USDT.
              For bid side (user selling ETH for USDT), capital is in ETH.
        
        Args:
            swap_amount: Amount user wants to swap (base units)
            capital_usd: Capital allocated for market making (USD)
            is_bid: True if bid side, False for ask side
            
        Returns:
            List of OrderbookLevel objects
        """
        # CEX-inspired configuration
        # Simulating typical CEX orderbook shape for ETH/USDT
        NUM_LEVELS = 5
        SPREAD_STEP_BPS = Decimal('400')  # Deep liquidity: 400 bps = 4% spread total
        
        # Size distribution (inspired by real CEX data)
        # Level 1 has most liquidity, decay slower than medium scenario
        SIZE_DISTRIBUTION = [
            Decimal('0.35'),  # Level 1: 35% of capital
            Decimal('0.25'),  # Level 2: 25%
            Decimal('0.20'),  # Level 3: 20%
            Decimal('0.12'),  # Level 4: 12%
            Decimal('0.08'),  # Level 5: 8%
        ]
        
        levels: List[OrderbookLevel] = []
        
        # For ask side (user buying base with quote):
        #   capital is in quote currency (USDT)
        # For bid side (user selling base for quote):
        #   capital is in base currency (ETH), need to convert from USD
        
        if is_bid:
            # Bid side: capital in base asset (ETH)
            # Convert USD capital to ETH: capital_usd * mid_price (because mid_price = quote/base)
            capital_in_base = capital_usd * self.mid_price
            capital_in_base_units = int(
                capital_in_base * Decimal(10 ** self.decimals_in)
            )
        else:
            # Ask side: capital in quote asset (USDT)
            # capital_usd is already in quote terms
            capital_in_quote = capital_usd
            capital_in_quote_units = int(
                capital_in_quote * Decimal(10 ** self.decimals_in)
            )
            capital_in_base_units = capital_in_quote_units
        
        for i in range(NUM_LEVELS):
            # Price calculation
            spread = SPREAD_STEP_BPS * (i + 1) / Decimal('10000')
            if is_bid:
                price = self.mid_price * (1 - spread)
            else:
                price = self.mid_price * (1 + spread)
            
            # Size from capital distribution
            amount_in_available = int(
                Decimal(capital_in_base_units) * SIZE_DISTRIBUTION[i]
            )
            amount_out_available = self._calculate_amount_out(amount_in_available, price)
            
            levels.append(
                OrderbookLevel(
                    price=price,
                    amount_in_available=amount_in_available,
                    amount_out_available=amount_out_available
                )
            )
        
        return levels
    
    def generate(
        self,
        scenario: Literal['small', 'medium', 'large'],
        swap_amount: int,
        is_bid: bool = False,
        capital_usd: Decimal = Decimal('1000000'),
        # Medium scenario custom params (defaults now match spec)
        num_levels: int = 5,
        spread_step_bps: Decimal = Decimal('15'),
        base_size_multiplier: Decimal = Decimal('1.0'),
        decay_factor: Decimal = Decimal('0.7'),
        target_depth_multiplier: Decimal = Decimal('2.5')
    ) -> List[OrderbookLevel]:
        """
        Generate orderbook for specified scenario.
        
        Args:
            scenario: 'small', 'medium', or 'large'
            swap_amount: Amount to swap (base units of token_in)
            is_bid: True for bid side, False for ask side
            capital_usd: Capital for 'large' scenario (ignored for small/medium)
            
            Medium scenario params (ignored for small/large):
                num_levels: Number of ladder levels (default: 5, per spec)
                spread_step_bps: Spread per level in bps (default: 15, in 10-20 range)
                base_size_multiplier: Base size multiplier (default: 1.0, per spec)
                decay_factor: Size decay factor (default: 0.7, per spec)
                target_depth_multiplier: Target depth multiplier (default: 2.5)
            
        Returns:
            List of OrderbookLevel objects
            
        Raises:
            ValueError: If scenario is invalid
        """
        if scenario == 'small':
            return self.generate_scenario_small(swap_amount, is_bid)
        elif scenario == 'medium':
            return self.generate_scenario_medium(
                swap_amount=swap_amount,
                is_bid=is_bid,
                num_levels=num_levels,
                spread_step_bps=spread_step_bps,
                base_size_multiplier=base_size_multiplier,
                decay_factor=decay_factor,
                target_depth_multiplier=target_depth_multiplier
            )
        elif scenario == 'large':
            return self.generate_scenario_large(swap_amount, capital_usd, is_bid)
        else:
            raise ValueError(f"Invalid scenario: {scenario}. Must be 'small', 'medium', or 'large'.")
    
    def _calculate_amount_out(self, amount_in: int, price: Decimal) -> int:
        """
        Calculate amount_out from amount_in and price.
        
        Formula:
            amount_out = amount_in * price * 10^(decimals_out - decimals_in)
        
        Args:
            amount_in: Input amount (base units)
            price: Price (token_out / token_in)
            
        Returns:
            Output amount (base units)
        """
        # Convert to human units, apply price, convert back to base units
        amount_in_human = Decimal(amount_in) / Decimal(10 ** self.decimals_in)
        amount_out_human = amount_in_human * price
        amount_out = int(amount_out_human * Decimal(10 ** self.decimals_out))
        return amount_out
    
    def get_total_depth(self, levels: List[OrderbookLevel]) -> Dict[str, int]:
        """
        Calculate total depth from list of levels.
        
        Args:
            levels: List of OrderbookLevel objects
            
        Returns:
            Dict with 'total_amount_in' and 'total_amount_out'
        """
        total_in = sum(level.amount_in_available for level in levels)
        total_out = sum(level.amount_out_available for level in levels)
        
        return {
            'total_amount_in': total_in,
            'total_amount_out': total_out
        }


# ============================================
# Test when run as script
# ============================================
if __name__ == "__main__":
    # Example: User wants to BUY ETH with USDT (swap USDT → ETH)
    # This is ASK side (user buying base asset)
    # Mid price from AMM: 2795.75 USDT per ETH
    # Price representation: token_out/token_in = ETH/USDT = 1/2795.75 = 0.0003577
    
    mid_price_usdt_per_eth = Decimal('2795.75')
    # For swap USDT→ETH, we need price as ETH/USDT
    mid_price = Decimal('1') / mid_price_usdt_per_eth
    
    decimals_in = 6   # USDT (input)
    decimals_out = 18  # ETH (output)
    swap_amount = 3000 * 10**6  # 3000 USDT (input)
    
    generator = SyntheticOrderbookGenerator(
        mid_price=mid_price,
        decimals_in=decimals_in,
        decimals_out=decimals_out
    )
    
    print("=" * 60)
    print("SYNTHETIC ORDERBOOK GENERATOR TEST")
    print("=" * 60)
    print(f"Direction: USDT → ETH (User buying ETH)")
    print(f"Mid Price: {mid_price_usdt_per_eth} USDT/ETH")
    print(f"Swap Amount: {swap_amount / 10**6:.2f} USDT (input)")
    print()
    
    # Test Scenario 1: Small
    print("SCENARIO 1: SMALL (Worst Case)")
    print("-" * 60)
    levels_small = generator.generate('small', swap_amount, is_bid=False)
    for i, level in enumerate(levels_small, 1):
        print(f"Level {i}:")
        print(f"  Price: {Decimal('1')/level.price:.2f} USDT/ETH (inverse)")
        print(f"  Amount In:  {level.amount_in_available / 10**6:.2f} USDT")
        print(f"  Amount Out: {level.amount_out_available / 10**18:.6f} ETH")
    
    depth = generator.get_total_depth(levels_small)
    print(f"\nTotal Depth: {depth['total_amount_in'] / 10**6:.2f} USDT")
    print(f"Depth Ratio: {depth['total_amount_in'] / swap_amount:.2f}×")
    print()
    
    # Test Scenario 2A: Medium (default - per spec)
    print("SCENARIO 2A: MEDIUM (Default per spec: 5 levels, decay 0.7)")
    print("-" * 60)
    levels_medium = generator.generate('medium', swap_amount, is_bid=False)
    for i, level in enumerate(levels_medium, 1):
        print(f"Level {i}:")
        print(f"  Price: {Decimal('1')/level.price:.2f} USDT/ETH (inverse)")
        print(f"  Amount In:  {level.amount_in_available / 10**6:.2f} USDT")
        print(f"  Amount Out: {level.amount_out_available / 10**18:.6f} ETH")
    
    depth = generator.get_total_depth(levels_medium)
    print(f"\nTotal Depth: {depth['total_amount_in'] / 10**6:.2f} USDT")
    print(f"Depth Ratio: {depth['total_amount_in'] / swap_amount:.2f}×")
    print()
    
    # Test Scenario 2B: Medium (custom - tight spread, more levels)
    print("SCENARIO 2B: MEDIUM (Custom: 10 levels, spread 10 bps, decay 0.7)")
    print("-" * 60)
    levels_medium_custom = generator.generate(
        'medium',
        swap_amount,
        is_bid=False,
        num_levels=10,
        spread_step_bps=Decimal('10'),
        base_size_multiplier=Decimal('1.0'),
        decay_factor=Decimal('0.7'),
        target_depth_multiplier=Decimal('2.5')
    )
    
    # Only show first 5 levels for brevity
    for i, level in enumerate(levels_medium_custom[:5], 1):
        print(f"Level {i}:")
        print(f"  Price: {Decimal('1')/level.price:.2f} USDT/ETH (inverse)")
        print(f"  Amount In:  {level.amount_in_available / 10**6:.2f} USDT")
        print(f"  Amount Out: {level.amount_out_available / 10**18:.6f} ETH")
    print(f"... ({len(levels_medium_custom) - 5} more levels)")
    
    depth = generator.get_total_depth(levels_medium_custom)
    print(f"\nTotal Depth: {depth['total_amount_in'] / 10**6:.2f} USDT")
    print(f"Depth Ratio: {depth['total_amount_in'] / swap_amount:.2f}×")
    print()
    
    # Test Scenario 3: Large (CEX-like)
    print("SCENARIO 3: LARGE (CEX-like, $1M capital)")
    print("-" * 60)
    levels_large = generator.generate('large', swap_amount, is_bid=False, capital_usd=Decimal('1000000'))
    
    # Show first 5 levels
    for i, level in enumerate(levels_large[:5], 1):
        print(f"Level {i}:")
        print(f"  Price: {Decimal('1')/level.price:.2f} USDT/ETH (inverse)")
        print(f"  Amount In:  {level.amount_in_available / 10**6:.2f} USDT")
        print(f"  Amount Out: {level.amount_out_available / 10**18:.6f} ETH")
    
    depth = generator.get_total_depth(levels_large)
    print(f"\nTotal Depth: {depth['total_amount_in'] / 10**6:.2f} USDT")
    print(f"Depth Ratio: {depth['total_amount_in'] / swap_amount:.2f}×")
    print()
    
    print("=" * 60)
    print("✅ All 3 scenarios generated successfully!")
    print("=" * 60)
