"""
Module 4: Execution Plan Builder
================================================================================

Chức năng:
- Tổng hợp kết quả từ Module 3 (Greedy Matcher)
- Simulate AMM leg cho phần còn lại
- Tính savings (before/after performance fee)
- Encode hook_data theo ABI của UniHybridHookData
- Build complete JSON response theo spec API

API Response Structure:
- split: {amount_in_total, amount_in_on_orderbook, amount_in_on_amm}
- legs: [{source, amount_in, expected_amount_out, effective_price, meta}, ...]
- hook_data_args: {tokenIn, tokenOut, amountInOnOrderbook, maxMatches, slippageLimit}
- hook_data: hex string (ABI encoded)
- amm_reference_out: baseline nếu swap 100% qua AMM
- expected_total_out: tổng output từ OB + AMM
- savings_before_fee, performance_fee_amount, savings_after_fee
- min_total_out: minimum output với slippage tolerance
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from eth_abi import encode

from .types import ExecutionLeg, MatchingResult, SavingsData, ExecutionPlan


@dataclass
class LevelUsed:
    """Level được sử dụng trong greedy matching (from Module 3)"""
    price: Decimal
    amount_in_from_level: int
    amount_out_from_level: int


class ExecutionPlanBuilder:
    """
    Xây dựng execution plan hoàn chỉnh cho UniHybrid API.
    
    Input: Kết quả từ Module 3 (greedy matching result)
    Output: Complete execution plan JSON theo spec
    """
    
    def __init__(
        self,
        price_amm: Decimal,
        decimals_in: int,
        decimals_out: int,
        performance_fee_bps: int = 3000,  # 30% default
        max_slippage_bps: int = 100,       # 1% default
    ):
        """
        Parameters:
        -----------
        price_amm : Decimal
            AMM mid price (token_out / token_in) từ Module 1
        decimals_in : int
            Decimals của token input (vd: USDT = 6)
        decimals_out : int
            Decimals của token output (vd: ETH = 18)
        performance_fee_bps : int
            Performance fee (bps), default = 3000 (30%)
        max_slippage_bps : int
            Max slippage tolerance (bps), default = 100 (1%)
        """
        self.price_amm = price_amm
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
        self.performance_fee_bps = performance_fee_bps
        self.max_slippage_bps = max_slippage_bps
    
    def build_plan(
        self,
        match_result: Dict[str, Any],
        token_in_address: str,
        token_out_address: str,
        max_matches: int = 8,
        me_slippage_limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Build complete execution plan từ greedy match result.
        
        Parameters:
        -----------
        match_result : dict
            Kết quả từ Module 3 GreedyMatcher.match()
            Expected keys:
            - amount_in_on_orderbook (int)
            - amount_in_on_amm (int)
            - amount_out_from_orderbook (int)
            - levels_used (List[LevelUsed])
            - min_better_price (Decimal)
        token_in_address : str
            Địa chỉ token input (vd: USDT address)
        token_out_address : str
            Địa chỉ token output (vd: ETH address)
        max_matches : int
            Max số lệnh match trong MatchingEngine (default: 8)
        me_slippage_limit : int
            Slippage limit cho MatchingEngine (bps, default: 200)
        
        Returns:
        --------
        dict : Complete execution plan theo spec API
        """
        # Extract từ match_result
        amount_in_total = match_result['amount_in_on_orderbook'] + match_result['amount_in_on_amm']
        amount_in_on_orderbook = match_result['amount_in_on_orderbook']
        amount_in_on_amm = match_result['amount_in_on_amm']
        amount_out_from_orderbook = match_result['amount_out_from_orderbook']
        levels_used = match_result['levels_used']
        
        # Step 1: Simulate AMM leg (nếu có)
        amount_out_from_amm = self._simulate_amm_leg(amount_in_on_amm)
        
        # Step 2: Build legs array
        legs = self._build_legs(
            amount_in_on_orderbook,
            amount_out_from_orderbook,
            amount_in_on_amm,
            amount_out_from_amm,
            levels_used
        )
        
        # Step 3: Calculate savings
        amm_reference_out = self._calculate_amm_reference(amount_in_total)
        expected_total_out = amount_out_from_orderbook + amount_out_from_amm
        savings_data = self._calculate_savings(expected_total_out, amm_reference_out)
        
        # Step 4: Build hook_data
        hook_data_args = {
            "tokenIn": token_in_address,
            "tokenOut": token_out_address,
            "amountInOnOrderbook": str(amount_in_on_orderbook),
            "maxMatches": max_matches,
            "slippageLimit": me_slippage_limit
        }
        hook_data = self._encode_hook_data(hook_data_args)
        
        # Step 5: Calculate min_total_out (với slippage tolerance)
        min_total_out = self._calculate_min_total_out(amm_reference_out)
        
        # Step 6: Build complete response
        execution_plan = {
            "split": {
                "amount_in_total": str(amount_in_total),
                "amount_in_on_orderbook": str(amount_in_on_orderbook),
                "amount_in_on_amm": str(amount_in_on_amm)
            },
            "legs": legs,
            "hook_data_args": hook_data_args,
            "hook_data": hook_data,
            "amm_reference_out": str(amm_reference_out),
            "expected_total_out": str(expected_total_out),
            "savings_before_fee": str(savings_data['savings_before_fee']),
            "performance_fee_amount": str(savings_data['performance_fee_amount']),
            "savings_after_fee": str(savings_data['savings_after_fee']),
            "min_total_out": str(min_total_out)
        }
        
        return execution_plan
    
    def _simulate_amm_leg(self, amount_in_on_amm: int) -> int:
        """
        Simulate swap trên AMM cho phần fallback.
        
        Simplification: Giả sử swap pro-rata theo giá AMM hiện tại.
        Production: Nên dùng Quoter V3/V4 cho chính xác.
        
        Formula:
        amount_out (base units) = amount_in (base units) * price_amm * 10^(decimals_out - decimals_in)
        
        Parameters:
        -----------
        amount_in_on_amm : int
            Lượng input đi qua AMM (base units)
        
        Returns:
        --------
        int : Expected amount_out từ AMM (base units)
        """
        if amount_in_on_amm == 0:
            return 0
        
        # Decimal adjustment for token decimals
        # price_amm is normalized (1 token_out / 1 token_in)
        # Must scale by 10^(decimals_out - decimals_in)
        decimals_adjustment = Decimal(10) ** (self.decimals_out - self.decimals_in)
        
        amount_in_decimal = Decimal(amount_in_on_amm)
        amount_out_decimal = amount_in_decimal * self.price_amm * decimals_adjustment
        amount_out = int(amount_out_decimal)
        
        return amount_out
    
    def _calculate_amm_reference(self, amount_in_total: int) -> int:
        """
        Tính baseline: lượng output nếu swap 100% qua AMM.
        
        Formula:
        amount_out (base units) = amount_in (base units) * price_amm * 10^(decimals_out - decimals_in)
        
        Parameters:
        -----------
        amount_in_total : int
            Tổng lượng input (base units)
        
        Returns:
        --------
        int : AMM reference output (base units)
        """
        # Same calculation as _simulate_amm_leg but for total amount
        decimals_adjustment = Decimal(10) ** (self.decimals_out - self.decimals_in)
        
        amount_in_decimal = Decimal(amount_in_total)
        amount_out_decimal = amount_in_decimal * self.price_amm * decimals_adjustment
        amount_out = int(amount_out_decimal)
        
        return amount_out
    
    def _build_legs(
        self,
        amount_in_on_orderbook: int,
        amount_out_from_orderbook: int,
        amount_in_on_amm: int,
        amount_out_from_amm: int,
        levels_used: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Build legs array theo spec API.
        
        Returns:
        --------
        list : Array of legs
            [
                {
                    "source": "internal_orderbook",
                    "amount_in": "...",
                    "expected_amount_out": "...",
                    "effective_price": "...",
                    "meta": {
                        "levels_used": [...]
                    }
                },
                {
                    "source": "amm",
                    "amount_in": "...",
                    "expected_amount_out": "...",
                    "effective_price": "..."
                }
            ]
        """
        legs = []
        
        # Leg 1: Internal Orderbook (nếu có)
        if amount_in_on_orderbook > 0:
            effective_price_ob = (
                Decimal(amount_out_from_orderbook) / Decimal(amount_in_on_orderbook)
                if amount_in_on_orderbook > 0 else Decimal('0')
            )
            
            # Build levels_used meta
            levels_meta = []
            for level in levels_used:
                levels_meta.append({
                    "price": str(level.price),
                    "amount_in_from_level": str(level.amount_in_from_level),
                    "amount_out_from_level": str(level.amount_out_from_level)
                })
            
            legs.append({
                "source": "internal_orderbook",
                "amount_in": str(amount_in_on_orderbook),
                "expected_amount_out": str(amount_out_from_orderbook),
                "effective_price": str(effective_price_ob),
                "meta": {
                    "levels_used": levels_meta
                }
            })
        
        # Leg 2: AMM (nếu có)
        if amount_in_on_amm > 0:
            effective_price_amm = (
                Decimal(amount_out_from_amm) / Decimal(amount_in_on_amm)
                if amount_in_on_amm > 0 else Decimal('0')
            )
            
            legs.append({
                "source": "amm",
                "amount_in": str(amount_in_on_amm),
                "expected_amount_out": str(amount_out_from_amm),
                "effective_price": str(effective_price_amm)
            })
        
        return legs
    
    def _calculate_savings(
        self,
        expected_total_out: int,
        amm_reference_out: int
    ) -> Dict[str, int]:
        """
        Tính savings (before fee, performance fee, after fee).
        
        Parameters:
        -----------
        expected_total_out : int
            Tổng output từ OB + AMM
        amm_reference_out : int
            Baseline output nếu 100% AMM
        
        Returns:
        --------
        dict : {
            'savings_before_fee': int,
            'performance_fee_amount': int,
            'savings_after_fee': int
        }
        """
        # Savings before fee
        savings_before_fee = expected_total_out - amm_reference_out
        
        # Clamp negative savings to 0
        if savings_before_fee < 0:
            savings_before_fee = 0
        
        # Performance fee (30% of savings)
        if savings_before_fee > 0:
            performance_fee_amount = (savings_before_fee * self.performance_fee_bps) // 10000
            savings_after_fee = savings_before_fee - performance_fee_amount
        else:
            performance_fee_amount = 0
            savings_after_fee = 0
        
        return {
            'savings_before_fee': savings_before_fee,
            'performance_fee_amount': performance_fee_amount,
            'savings_after_fee': savings_after_fee
        }
    
    def _calculate_min_total_out(self, amm_reference_out: int) -> int:
        """
        Tính min_total_out với slippage tolerance.
        
        Formula: min_total_out = amm_reference_out * (1 - max_slippage_bps / 10_000)
        
        Parameters:
        -----------
        amm_reference_out : int
            AMM reference output
        
        Returns:
        --------
        int : Minimum total output với slippage
        """
        min_total_out = (amm_reference_out * (10000 - self.max_slippage_bps)) // 10000
        return min_total_out
    
    def _encode_hook_data(self, hook_data_args: Dict[str, Any]) -> str:
        """
        Encode hook_data theo ABI của UniHybridHookData struct.
        
        Solidity struct:
        struct UniHybridHookData {
            address tokenIn;
            address tokenOut;
            uint256 amountInOnOrderbook;
            uint32 maxMatches;
            uint32 slippageLimit;
        }
        
        Parameters:
        -----------
        hook_data_args : dict
            {
                "tokenIn": "0x...",
                "tokenOut": "0x...",
                "amountInOnOrderbook": "...",
                "maxMatches": int,
                "slippageLimit": int
            }
        
        Returns:
        --------
        str : Hex string "0x..." (ABI encoded)
        """
        # ABI types
        types = ["address", "address", "uint256", "uint32", "uint32"]
        
        # Values
        values = [
            hook_data_args["tokenIn"],
            hook_data_args["tokenOut"],
            int(hook_data_args["amountInOnOrderbook"]),
            hook_data_args["maxMatches"],
            hook_data_args["slippageLimit"]
        ]
        
        # Encode
        encoded = encode(types, values)
        
        # Return as hex string
        return "0x" + encoded.hex()


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
    from services.orderbook import SyntheticOrderbookGenerator
    from services.matching import GreedyMatcher
    
    print("=" * 80)
    print("MODULE 4: EXECUTION PLAN BUILDER TEST")
    print("=" * 80)
    print()
    
    # Step 1: Fetch AMM price (Module 1)
    print("STEP 1: FETCH AMM PRICE (Module 1)")
    print("-" * 80)
    pool_address = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    pool_data = get_price_for_pool(pool_address)
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    print(f"✅ Pool: {pool_address}")
    print(f"   Pair: {pool_data['symbol0']}/{pool_data['symbol1']}")
    print(f"   Price: {price_usdt_per_eth:.2f} USDT/ETH")
    print()
    
    # Step 2: Generate orderbook (Module 2)
    print("STEP 2: GENERATE ORDERBOOK (Module 2)")
    print("-" * 80)
    swap_amount = 10000 * 10**6  # 10,000 USDT
    generator = SyntheticOrderbookGenerator(price_eth_per_usdt, 6, 18)
    levels = generator.generate('medium', swap_amount, False)
    
    print(f"✅ Generated {len(levels)} orderbook levels")
    print(f"   Swap Amount: {swap_amount / 10**6:,.2f} USDT")
    print()
    
    # Step 3: Greedy matching (Module 3)
    print("STEP 3: GREEDY MATCHING (Module 3)")
    print("-" * 80)
    matcher = GreedyMatcher(price_eth_per_usdt, 6, 18, ob_min_improve_bps=5)
    match_result = matcher.match(levels, swap_amount, False)
    
    print(f"✅ Greedy matching completed")
    print(f"   Orderbook: {match_result['amount_in_on_orderbook'] / 10**6:,.2f} USDT")
    print(f"   AMM:       {match_result['amount_in_on_amm'] / 10**6:,.2f} USDT")
    print(f"   Levels used: {len(match_result['levels_used'])}")
    print()
    
    # Step 4: Build execution plan (Module 4)
    print("STEP 4: BUILD EXECUTION PLAN (Module 4)")
    print("-" * 80)
    
    # Token addresses (Base mainnet)
    TOKEN_USDT = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
    TOKEN_ETH = "0x4200000000000000000000000000000000000006"
    
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
    
    print("✅ Execution plan built successfully")
    print()
    
    # Print results
    print("=" * 80)
    print("EXECUTION PLAN SUMMARY")
    print("=" * 80)
    print()
    
    print("📊 SPLIT:")
    split = execution_plan['split']
    print(f"   Total Input:      {int(split['amount_in_total']) / 10**6:,.2f} USDT")
    print(f"   → Orderbook:      {int(split['amount_in_on_orderbook']) / 10**6:,.2f} USDT ({int(split['amount_in_on_orderbook']) * 100 // int(split['amount_in_total'])}%)")
    print(f"   → AMM:            {int(split['amount_in_on_amm']) / 10**6:,.2f} USDT ({int(split['amount_in_on_amm']) * 100 // int(split['amount_in_total'])}%)")
    print()
    
    print("🔗 LEGS:")
    for i, leg in enumerate(execution_plan['legs'], 1):
        print(f"   Leg {i}: {leg['source']}")
        print(f"      Amount In:  {int(leg['amount_in']) / 10**6:,.2f} USDT")
        print(f"      Amount Out: {int(leg['expected_amount_out']) / 10**18:.6f} ETH")
        print(f"      Price:      {float(leg['effective_price']):.10f} ETH/USDT")
        
        if 'meta' in leg and 'levels_used' in leg['meta']:
            print(f"      Levels used: {len(leg['meta']['levels_used'])}")
        print()
    
    print("💰 SAVINGS:")
    amm_ref = int(execution_plan['amm_reference_out']) / 10**18
    total_out = int(execution_plan['expected_total_out']) / 10**18
    sav_before = int(execution_plan['savings_before_fee']) / 10**18
    fee_amt = int(execution_plan['performance_fee_amount']) / 10**18
    sav_after = int(execution_plan['savings_after_fee']) / 10**18
    
    print(f"   AMM Reference Out:    {amm_ref:.6f} ETH")
    print(f"   Expected Total Out:   {total_out:.6f} ETH")
    print(f"   Savings Before Fee:   {sav_before:.6f} ETH ({sav_before / amm_ref * 10000:.2f} bps)")
    print(f"   Performance Fee (30%): {fee_amt:.6f} ETH")
    print(f"   Savings After Fee:    {sav_after:.6f} ETH ({sav_after / amm_ref * 10000:.2f} bps)")
    print()
    
    print("🔒 SLIPPAGE PROTECTION:")
    min_out = int(execution_plan['min_total_out']) / 10**18
    print(f"   Min Total Out (1% slippage): {min_out:.6f} ETH")
    print()
    
    print("📦 HOOK DATA:")
    print(f"   tokenIn:  {execution_plan['hook_data_args']['tokenIn']}")
    print(f"   tokenOut: {execution_plan['hook_data_args']['tokenOut']}")
    print(f"   amountInOnOrderbook: {execution_plan['hook_data_args']['amountInOnOrderbook']}")
    print(f"   maxMatches: {execution_plan['hook_data_args']['maxMatches']}")
    print(f"   slippageLimit: {execution_plan['hook_data_args']['slippageLimit']}")
    print(f"   Encoded (hex): {execution_plan['hook_data'][:66]}...")
    print()
    
    print("=" * 80)
    print("✅ MODULE 4 TEST COMPLETED!")
    print("=" * 80)
