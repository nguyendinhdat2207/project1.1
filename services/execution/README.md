# 🚀 Execution Module - Greedy Matching & Savings

This module implements the complete order matching and execution flow:
- **Greedy Matching**: Match user input against available orderbook
- **AMM Leg**: Build fallback swap for remaining amount
- **Savings Calculation**: Compare vs reference and apply fees

## Architecture

```
services/execution/
├── types.py                 # Data structures (KyberOrder, ExecutionLeg, etc.)
├── greedy_matcher.py        # Greedy matching algorithm
├── amm_leg.py              # AMM execution and simulation
├── savings_calculator.py    # Savings and fee calculation
└── __init__.py             # Module exports
```

## Quick Start

### 1. Define Orders

```python
from services.execution import KyberOrder

orders = [
    KyberOrder(
        id='order_1',
        makingAmount='1000000000000000000',  # 1 WETH (18 decimals)
        takingAmount='2900000000',  # 2900 USDT (6 decimals)
        availableMakingAmount='1000000000000000000',  # Remaining fillable
        makerToken='0x4200...',  # WETH
        takerToken='0xfde4...',  # USDT
        price='2900',  # USDT per WETH
    ),
    # ... more orders
]
```

### 2. Greedy Match

```python
from services.execution import greedy_match_kyber_only

matching = greedy_match_kyber_only(
    amount_in=5_000_000_000,  # 5000 USDT (raw)
    kyber_orders=orders,
    kyber_limit_order_contract='0x...',
    receiver='0x...',
)

print(f"Kyber matched: {matching.kyberAmount}")
print(f"Remaining for AMM: {matching.ammAmount}")
```

### 3. AMM Simulation (for remaining)

```python
from services.execution import simulate_amm_swap

amm_out = simulate_amm_swap(
    pool_address='0x11b815efB8f581194ae79006d24E0d814B7697F6',
    amount_in=int(matching.ammAmount),
    token_in_decimals=6,
    token_out_decimals=18,
)
```

### 4. Calculate Savings

```python
from services.execution import calculate_savings, format_savings_summary

# Get reference price (pure AMM)
amm_reference = simulate_amm_swap(
    pool_address=pool,
    amount_in=total_amount,
    token_in_decimals=6,
    token_out_decimals=18,
)

# Calculate savings
savings = calculate_savings(
    amount_in=total_amount,
    amm_reference_out=int(amm_reference),
    matching_result=matching,
    amm_out_for_remaining=int(amm_out),
    performance_fee_bps=50,  # 0.5% fee
    max_slippage_bps=100,  # 1% slippage
)

print(format_savings_summary(savings))
```

## Data Structures

### KyberOrder
```python
@dataclass
class KyberOrder:
    id: str
    makingAmount: str  # Total maker amount (token_out)
    takingAmount: str  # Total taker amount (token_in)
    availableMakingAmount: str  # Remaining fillable
    makerToken: str  # Address
    takerToken: str  # Address
    price: str  # token_in per token_out
    orderHash: Optional[str]
    signature: Optional[str]
```

### ExecutionLeg
```python
@dataclass
class ExecutionLeg:
    source: Literal['kyber', 'amm']  # Where to execute
    to: str  # Contract address
    calldata: str  # Encoded function call
    value: str  # ETH value (usually '0')
    sell_amount: str  # Input amount
    min_buy_amount: str  # Min output
    meta: Optional[dict]  # Extra data (order id, pool, etc.)
```

### MatchingResult
```python
@dataclass
class MatchingResult:
    legs: List[ExecutionLeg]  # Execution steps
    remainingIn: str  # Unmatched amount
    kyberAmount: str  # Matched from Kyber
    ammAmount: str  # For AMM leg
```

### SavingsData
```python
@dataclass
class SavingsData:
    amm_reference_out: str  # Pure AMM output
    expected_total_out: str  # Combined route output
    savings_before_fee: str  # expected - reference
    performance_fee_bps: int  # Fee in basis points
    performance_fee: str  # Actual fee
    savings_after_fee: str  # savings - fee
    min_total_out: str  # With slippage protection
    max_slippage_bps: int
```

## Algorithm: Greedy Matching

```
greedy_match_kyber_only(amountIn, orders):
  remainingIn = amountIn
  legs = []
  
  for order in orders (sorted by price, best → worst):
    if remainingIn == 0:
      break
    
    maxFillTaker = remainingMaker * takingTotal / makingTotal
    fillTaker = min(remainingIn, maxFillTaker)
    fillMaker = makingTotal * fillTaker / takingTotal
    
    legs.append(ExecutionLeg(
      source='kyber',
      to=contract,
      calldata=kyberEncode(...),
      sell_amount=fillTaker,
      min_buy_amount=fillMaker,
    ))
    
    remainingIn -= fillTaker
  
  return MatchingResult(
    legs=legs,
    remainingIn=remainingIn,
    kyberAmount=amountIn - remainingIn,
    ammAmount=remainingIn,
  )
```

## Algorithm: Savings Calculation

```
expected_total_out = sum(leg.min_buy_amount for leg in legs)
if remainingIn > 0:
  expected_total_out += amm_out_for_remaining

amm_reference_out = simulate_full_amm_swap(amountIn)

savings_before_fee = expected_total_out - amm_reference_out
performance_fee = max(0, savings_before_fee * fee_bps / 10000)
savings_after_fee = savings_before_fee - performance_fee

min_total_out = amm_reference_out * (1 - slippage_bps / 10000)
```

## Example Output

```
================================================================================
💰 SAVINGS ANALYSIS
================================================================================

📊 Reference (Pure AMM):
   Expected Output: 1,711,864,406,779,661,017 (if entire amountIn swapped via AMM)

📊 Optimized Route (Kyber + AMM):
   Expected Output: 1,711,864,406,779,661,017

📈 Savings Calculation:
   Savings (before fee):  +15,000 (0.0009%)
   Performance Fee (50 bps): 750
   Savings (after fee):   +14,250

🛡️  Slippage Protection:
   Max Slippage (100 bps): 17,118,644
   Min Output to Accept: 1,694,745,762,372,881,373

================================================================================
```

## Next Steps

- [ ] Implement Kyber API calldata encoding (currently placeholder)
- [ ] Implement Uniswap V3 swap calldata generation
- [ ] Add quote validation (compare vs on-chain)
- [ ] Add batch order execution
- [ ] Add MEV protection (ordering, splitting, etc.)

## Testing

Run the full integration test:
```bash
python test_execution_flow.py
```

This test demonstrates:
1. Parsing sample orders
2. Greedy matching
3. AMM simulation
4. Savings calculation

## Important Notes

⚠️ **Pool Token Order**: Make sure your pool token0 and token1 are in the correct order. For USDT→WETH swap on pool with token0=WETH, token1=USDT:
- price_token1_per_token0 = USDT per WETH ✅
- To swap USDT→WETH, divide by this price
- To swap WETH→USDT, multiply by this price

⚠️ **Decimals**: Always handle decimal conversions carefully:
```python
amount_human = Decimal(amount_raw) / Decimal(10) ** Decimal(decimals)
amount_raw = amount_human * Decimal(10) ** Decimal(decimals)
```

⚠️ **Calldata Generation**: Currently using placeholders. In production:
- Use Kyber's `encode-fill-order` API
- Use Uniswap V3 Router2's encoded swaps
- Validate with quote APIs before execution

---

**Last Updated**: November 26, 2025
