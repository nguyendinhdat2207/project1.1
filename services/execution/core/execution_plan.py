from decimal import Decimal
from typing import Dict, Any, List
from dataclasses import dataclass
from eth_abi import encode


@dataclass
class LevelUsed:
    price: Decimal
    amount_in_from_level: int
    amount_out_from_level: int


class ExecutionPlanBuilder:

    def __init__(
        self,
        price_amm: Decimal,
        decimals_in: int,
        decimals_out: int,
        performance_fee_bps: int = 3000,
        max_slippage_bps: int = 100
    ):
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
        me_slippage_limit: int = 200
    ) -> Dict[str, Any]:
        amount_in_total = match_result['amount_in_on_orderbook'] + match_result['amount_in_on_amm']
        amount_in_on_orderbook = match_result['amount_in_on_orderbook']
        amount_in_on_amm = match_result['amount_in_on_amm']
        amount_out_from_orderbook = match_result['amount_out_from_orderbook']
        levels_used = match_result['levels_used']
        
        amount_out_from_amm = self._simulate_amm_leg(amount_in_on_amm)
        
        legs = self._build_legs(
            amount_in_on_orderbook,
            amount_out_from_orderbook,
            amount_in_on_amm,
            amount_out_from_amm,
            levels_used
        )
        
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
        if amount_in_on_amm == 0:
            return 0
        
        decimals_adjustment = Decimal(10) ** (self.decimals_out - self.decimals_in)
        amount_in_decimal = Decimal(amount_in_on_amm)
        amount_out_decimal = amount_in_decimal * self.price_amm * decimals_adjustment
        return int(amount_out_decimal)
    
    def _calculate_amm_reference(self, amount_in_total: int) -> int:
        decimals_adjustment = Decimal(10) ** (self.decimals_out - self.decimals_in)
        amount_in_decimal = Decimal(amount_in_total)
        amount_out_decimal = amount_in_decimal * self.price_amm * decimals_adjustment
        return int(amount_out_decimal)
    
    def _build_legs(
        self,
        amount_in_on_orderbook: int,
        amount_out_from_orderbook: int,
        amount_in_on_amm: int,
        amount_out_from_amm: int,
        levels_used: List[Any]
    ) -> List[Dict[str, Any]]:
        legs = []
        
        if amount_in_on_orderbook > 0:
            effective_price_ob = (
                Decimal(amount_out_from_orderbook) / Decimal(amount_in_on_orderbook)
                if amount_in_on_orderbook > 0 else Decimal('0')
            )
            
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
        savings_before_fee = expected_total_out - amm_reference_out
        
        if savings_before_fee < 0:
            savings_before_fee = 0
        
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
        return (amm_reference_out * (10000 - self.max_slippage_bps)) // 10000
    
    def _encode_hook_data(self, hook_data_args: Dict[str, Any]) -> str:
        types = ["address", "address", "uint256", "uint32", "uint32"]
        values = [
            hook_data_args["tokenIn"],
            hook_data_args["tokenOut"],
            int(hook_data_args["amountInOnOrderbook"]),
            hook_data_args["maxMatches"],
            hook_data_args["slippageLimit"]
        ]
        encoded = encode(types, values)
        return "0x" + encoded.hex()


if __name__ == "__main__":
    from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
    from services.orderbook import SyntheticOrderbookGenerator
    from services.matching import GreedyMatcher
    
    print("\n" + "=" * 80)
    print("MODULE 4: EXECUTION PLAN BUILDER TEST")
    print("=" * 80 + "\n")
    
    print("STEP 1: FETCH AMM PRICE")
    print("-" * 80)
    pool_address = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    pool_data = get_price_for_pool(pool_address)
    price_usdt_per_eth = pool_data['price_eth_per_usdt']
    price_eth_per_usdt = Decimal('1') / price_usdt_per_eth
    
    print(f"✅ Pool: {pool_address}")
    print(f"   Pair: {pool_data['symbol0']}/{pool_data['symbol1']}")
    print(f"   Price: {price_usdt_per_eth:.2f} USDT/ETH\n")
    
    print("STEP 2: GENERATE ORDERBOOK")
    print("-" * 80)
    swap_amount = 10000 * 10**6  # 10,000 USDT
    generator = SyntheticOrderbookGenerator(price_eth_per_usdt, 6, 18)
    levels = generator.generate('medium', swap_amount, False)
    
    print(f"✅ Generated {len(levels)} orderbook levels")
    print(f"   Swap Amount: {swap_amount / 10**6:,.2f} USDT\n")
    
    print("STEP 3: GREEDY MATCHING")
    print("-" * 80)
    matcher = GreedyMatcher(price_eth_per_usdt, 6, 18, ob_min_improve_bps=5)
    match_result = matcher.match(levels, swap_amount, False)
    
    print(f"✅ Greedy matching completed")
    print(f"   Orderbook: {match_result['amount_in_on_orderbook'] / 10**6:,.2f} USDT")
    print(f"   AMM:       {match_result['amount_in_on_amm'] / 10**6:,.2f} USDT")
    print(f"   Levels used: {len(match_result['levels_used'])}\n")
    
    print("STEP 4: BUILD EXECUTION PLAN")
    print("-" * 80)
    
    TOKEN_USDT = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
    TOKEN_ETH = "0x4200000000000000000000000000000000000006"
    
    builder = ExecutionPlanBuilder(
        price_amm=price_eth_per_usdt,
        decimals_in=6,
        decimals_out=18,
        performance_fee_bps=3000,
        max_slippage_bps=100
    )
    
    execution_plan = builder.build_plan(
        match_result=match_result,
        token_in_address=TOKEN_USDT,
        token_out_address=TOKEN_ETH,
        max_matches=8,
        me_slippage_limit=200
    )
    
    print("✅ Execution plan built successfully\n")
    
    print("=" * 80)
    print("EXECUTION PLAN SUMMARY")
    print("=" * 80 + "\n")
    
    print("📊 SPLIT:")
    split = execution_plan['split']
    print(f"   Total Input:      {int(split['amount_in_total']) / 10**6:,.2f} USDT")
    print(f"   → Orderbook:      {int(split['amount_in_on_orderbook']) / 10**6:,.2f} USDT ({int(split['amount_in_on_orderbook']) * 100 // int(split['amount_in_total'])}%)")
    print(f"   → AMM:            {int(split['amount_in_on_amm']) / 10**6:,.2f} USDT ({int(split['amount_in_on_amm']) * 100 // int(split['amount_in_total'])}%)\n")
    
    print("🔗 LEGS:")
    for i, leg in enumerate(execution_plan['legs'], 1):
        print(f"   Leg {i}: {leg['source']}")
        print(f"      Amount In:  {int(leg['amount_in']) / 10**6:,.2f} USDT")
        print(f"      Amount Out: {int(leg['expected_amount_out']) / 10**18:.6f} ETH")
        print(f"      Price:      {float(leg['effective_price']):.10f} ETH/USDC")
        
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
    print(f"   Performance Fee:      {fee_amt:.6f} ETH")
    print(f"   Savings After Fee:    {sav_after:.6f} ETH ({sav_after / amm_ref * 10000:.2f} bps)\n")
    
    print("🔒 SLIPPAGE PROTECTION:")
    min_out = int(execution_plan['min_total_out']) / 10**18
    print(f"   Min Total Out: {min_out:.6f} ETH\n")
    
    print("📦 HOOK DATA:")
    print(f"   tokenIn:  {execution_plan['hook_data_args']['tokenIn']}")
    print(f"   tokenOut: {execution_plan['hook_data_args']['tokenOut']}")
    print(f"   amountInOnOrderbook: {execution_plan['hook_data_args']['amountInOnOrderbook']}")
    print(f"   maxMatches: {execution_plan['hook_data_args']['maxMatches']}")
    print(f"   slippageLimit: {execution_plan['hook_data_args']['slippageLimit']}")
    print(f"   Encoded (hex): {execution_plan['hook_data'][:66]}...\n")
    
    print("=" * 80)
    print("✅ MODULE 4 TEST COMPLETED!")
    print("=" * 80)
