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
        
        Kịch bản 1: Shallow orderbook (OPTIMIZED)
        - 1 level
        - Spread: 35 bps (wide spread cho shallow liquidity)
        - Decay: 0.5 (50% coverage)
        
        Optimized: -35 bps vs AMM -43 bps = +8 bps margin < threshold 10 (edge case)
        Realistic: Shallow OB thường có spread rộng (30-50 bps)
        
        - is_bid=False (ASK): price = mid * (1 - spread) → below mid
        - is_bid=True (BID): price = mid * (1 + spread) → above mid
        """
        
        DEPTH_MULTIPLIER = Decimal('0.5')  # 50% coverage
        SPREAD_BPS = Decimal('35')  # ✅ 35 bps below spot = ~8 bps better than AMM effective (~-43 bps)
        
        if is_bid:
            # BID: giá cao hơn mid
            price = self.mid_price * (1 + SPREAD_BPS / Decimal('10000'))
        else:
            # ASK: giá thấp hơn mid BUT better than AMM effective
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
        spread_step_bps: Decimal = Decimal('8'),  # 8 bps step (OPTIMIZED!)
        base_size_multiplier: Decimal = Decimal('1.0'),
        decay_factor: Decimal = Decimal('0.7'),  # 0.7 decay
        target_depth_multiplier: Decimal = Decimal('2.5')
    ) -> List[OrderbookLevel]:
        """
        Generate medium scenario orderbook.
        
        Kịch bản 2: Medium orderbook (OPTIMIZED)
        - 5 levels
        - Spread step: 8 bps (levels at -8, -16, -24, -32, -40 bps from spot)
        - Decay: 0.7 (level size giảm dần)
        - Target depth: 2.5x swap amount
        
        Optimized: Deeper levels để beat AMM effective (~-43 bps):
        - Levels 4-5 (-32, -40 bps) có margin ~3-11 bps vs AMM ✅
        - Matcher sẽ accept levels tốt, skip levels tệ
        
        - is_bid=False (ASK): User bán ETH → prices = mid * (1 - spread) → below mid
        - is_bid=True (BID): User mua ETH → prices = mid * (1 + spread) → above mid
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
        is_bid: bool = False,
        num_levels: int = 10,
        spread_step_bps: Decimal = Decimal('10'),  # ✅ 10 bps step
        base_size_multiplier: Decimal = Decimal('1.0'),
        decay_factor: Decimal = Decimal('0.5'),  # ✅ 0.5 decay (size giảm nhanh, best levels lớn)
        target_depth_multiplier: Decimal = Decimal('2.5')
    ) -> List[OrderbookLevel]:
        """
        Generate large (deep) orderbook scenario - CEX-like.
        
        Kịch bản 3: Deep orderbook (OPTIMIZED)
        - 10 levels
        - Spread step: 10 bps (levels at -10, -20, -30, -40, -50, -60, -70, -80, -90, -100 bps)
        - Decay: 0.5 (size giảm nhanh → best levels có size lớn nhất)
        - Target depth: 2.5x swap amount
        
        Optimized strategy:
        - Many levels nhưng BEST levels (tốt nhất) có SIZE LỚN NHẤT
        - Levels 1-4 (-10 đến -40 bps): Tệ hơn AMM → Skip
        - Levels 5-10 (-50 đến -100 bps): Tốt hơn AMM → Match
        - Với decay 0.5: Levels xa (tốt) có size NHỎ, levels gần (tệ) có size LỚN
        - → Cần đảo ngược: Levels tốt cần size lớn!
        
        - is_bid=False (ASK): User bán ETH → prices = mid * (1 - spread) → below mid
        - is_bid=True (BID): User mua ETH → prices = mid * (1 + spread) → above mid
        """
        
        levels: List[OrderbookLevel] = []
        total_unscaled = Decimal('0')
        
        for i in range(1, num_levels + 1):
            spread = spread_step_bps * i / Decimal('10000')
            if is_bid:
                # BID: User mua ETH → muốn giá CAO (above mid)
                price = self.mid_price * (1 + spread)
            else:
                # ASK: User bán ETH → muốn giá THẤP (below mid)
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
    
    def generate(
        self,
        scenario: Literal['small', 'medium', 'large'],
        swap_amount: int,
        is_bid: bool = False,
        capital_usd: Decimal = Decimal('1000000'),
        num_levels: int = 5,
        spread_step_bps: Decimal = Decimal('8'),  # ✅ OPTIMIZED: 8 bps default
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
            # ✅ STRATEGY: Deep OB với nhiều levels GẦN SPOT, spread hẹp
            # Giống CEX orderbook: nhiều levels, spread nhỏ, liquidity sâu
            return self.generate_scenario_medium(
                swap_amount=swap_amount,
                is_bid=is_bid,
                num_levels=10,  # 10 levels (deep orderbook)
                spread_step_bps=Decimal('5'),  # ✅ 5 bps step: -5, -10, -15... -50 bps
                base_size_multiplier=Decimal('1.0'),
                decay_factor=Decimal('0.85'),  # 0.85 decay (distribution khá đều)
                target_depth_multiplier=Decimal('3.0')  # Depth lớn (3x)
            )
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
