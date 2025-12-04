from decimal import Decimal
from typing import List, Dict, Literal
from dataclasses import dataclass


@dataclass
class OrderbookLevel:
    price: Decimal
    amount_in_available: int
    amount_out_available: int


class SyntheticOrderbookGenerator:
    
    def __init__(
        self,
        mid_price: Decimal,
        decimals_in: int,
        decimals_out: int
    ):
        self.mid_price = mid_price
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
    
    def generate_scenario_small(
        self,
        swap_amount: int,
        is_bid: bool = False
    ) -> List[OrderbookLevel]:
        """
        Generate small (thin) orderbook scenario.
        
        - is_bid=False (ASK): price = mid * (1 - spread) → below mid
        - is_bid=True (BID): price = mid * (1 + spread) → above mid
        """
        
        DEPTH_MULTIPLIER = Decimal('0.5')
        SPREAD_BPS = Decimal('30')
        
        if is_bid:
            # BID: giá cao hơn mid
            price = self.mid_price * (1 + SPREAD_BPS / Decimal('10000'))
        else:
            # ASK: giá thấp hơn mid
            price = self.mid_price * (1 - SPREAD_BPS / Decimal('10000'))
        
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
        Generate medium scenario orderbook.
        
        - is_bid=False (ASK): User mua base (e.g., ETH) → cần giá THẤP
          → Generate levels: mid * (1 - spread), mid * (1 - 2*spread), ...
        
        - is_bid=True (BID): User bán base (e.g., ETH) → cần giá CAO  
          → Generate levels: mid * (1 + spread), mid * (1 + 2*spread), ...
        """
        
        levels: List[OrderbookLevel] = []
        total_unscaled = Decimal('0')
        
        for i in range(1, num_levels + 1):
            spread = spread_step_bps * i / Decimal('10000')
            if is_bid:
                # BID: User bán base → muốn giá CAO (above mid)
                price = self.mid_price * (1 + spread)
            else:
                # ASK: User mua base → muốn giá THẤP (below mid)
                price = self.mid_price * (1 - spread)
            
            size_multiplier = base_size_multiplier * (decay_factor ** (i - 1))
            amount_in_unscaled = Decimal(swap_amount) * size_multiplier
            total_unscaled += amount_in_unscaled
            
            levels.append({
                'price': price,
                'amount_in_unscaled': amount_in_unscaled
            })
        
        target_total = Decimal(swap_amount) * target_depth_multiplier
        scale_factor = target_total / total_unscaled if total_unscaled > 0 else Decimal('1')
        
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
        capital_usd: Decimal = Decimal('1000000'),
        is_bid: bool = False
    ) -> List[OrderbookLevel]:
        """
        Generate large (CEX-like) orderbook scenario.
        
        - is_bid=False (ASK): prices = mid * (1 - spread_i) → below mid
        - is_bid=True (BID): prices = mid * (1 + spread_i) → above mid
        """
        
        NUM_LEVELS = 5
        SPREAD_STEP_BPS = Decimal('400')
        
        SIZE_DISTRIBUTION = [
            Decimal('0.35'),
            Decimal('0.25'),
            Decimal('0.20'),
            Decimal('0.12'),
            Decimal('0.08'),
        ]
        
        levels: List[OrderbookLevel] = []
        
        if is_bid:
            capital_in_base = capital_usd * self.mid_price
            capital_in_base_units = int(
                capital_in_base * Decimal(10 ** self.decimals_in)
            )
        else:
            capital_in_quote = capital_usd
            capital_in_quote_units = int(
                capital_in_quote * Decimal(10 ** self.decimals_in)
            )
            capital_in_base_units = capital_in_quote_units
        
        for i in range(NUM_LEVELS):
            spread = SPREAD_STEP_BPS * (i + 1) / Decimal('10000')
            if is_bid:
                # BID: giá cao hơn mid (above)
                price = self.mid_price * (1 + spread)
            else:
                # ASK: giá thấp hơn mid (below)
                price = self.mid_price * (1 - spread)
            
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
        num_levels: int = 5,
        spread_step_bps: Decimal = Decimal('15'),
        base_size_multiplier: Decimal = Decimal('1.0'),
        decay_factor: Decimal = Decimal('0.7'),
        target_depth_multiplier: Decimal = Decimal('2.5')
    ) -> List[OrderbookLevel]:
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
            raise ValueError(f"Invalid scenario: {scenario}")
    
    def _calculate_amount_out(self, amount_in: int, price: Decimal) -> int:
        amount_in_human = Decimal(amount_in) / Decimal(10 ** self.decimals_in)
        amount_out_human = amount_in_human * price
        amount_out = int(amount_out_human * Decimal(10 ** self.decimals_out))
        return amount_out
    
    def get_total_depth(self, levels: List[OrderbookLevel]) -> Dict[str, int]:
        total_in = sum(level.amount_in_available for level in levels)
        total_out = sum(level.amount_out_available for level in levels)
        
        return {
            'total_amount_in': total_in,
            'total_amount_out': total_out
        }


if __name__ == "__main__":
    # Example: User wants to BUY ETH with USDT (swap USDC → ETH)
    # This is ASK side (user buying base asset)
    # Mid price from AMM: 2795.75 USDC per ETH
    # Price representation: token_out/token_in = ETH/USDC = 1/2795.75 = 0.0003577
    
    mid_price_usdt_per_eth = Decimal('2795.75')
    # For swap USDT→ETH, we need price as ETH/USDC
    mid_price = Decimal('1') / mid_price_usdt_per_eth
    
    decimals_in = 6   # USDC (input)
    decimals_out = 18  # ETH (output)
    swap_amount = 3000 * 10**6  # 3000 USDC (input)
    
    generator = SyntheticOrderbookGenerator(
        mid_price=mid_price,
        decimals_in=decimals_in,
        decimals_out=decimals_out
    )
    
    print("=" * 60)
    print("SYNTHETIC ORDERBOOK GENERATOR TEST")
    print("=" * 60)
    print(f"Direction: USDC → ETH (User buying ETH)")
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
