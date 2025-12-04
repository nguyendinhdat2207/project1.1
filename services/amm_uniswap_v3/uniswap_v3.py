import os
import json
import math
import time
from decimal import Decimal, getcontext

from web3 import Web3
from web3.exceptions import BadFunctionCallOutput
from dotenv import load_dotenv

load_dotenv()
RPC_URL = os.getenv("RPC_URL")
if not RPC_URL:
    raise RuntimeError("Missing RPC_URL in .env file")

web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
print(f"RPC connected: {web3.is_connected()}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
POOL_ABI_PATH = os.path.join(BASE_DIR, "abi", "uniswap_v3_pool.json")
ERC20_ABI_PATH = os.path.join(BASE_DIR, "abi", "erc20_min.json")
QUOTER_V2_ABI_PATH = os.path.join(BASE_DIR, "abi", "quoter_v2.json")

with open(POOL_ABI_PATH, "r") as f:
    POOL_ABI = json.load(f)
with open(ERC20_ABI_PATH, "r") as f:
    ERC20_ABI = json.load(f)
with open(QUOTER_V2_ABI_PATH, "r") as f:
    QUOTER_V2_ABI = json.load(f)

QUOTER_V2_ADDRESS = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"


def load_pool_contract(pool_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_ABI)


def load_erc20_contract(token_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

def load_quoter_v2_contract():
    return web3.eth.contract(
        address=Web3.to_checksum_address(QUOTER_V2_ADDRESS),
        abi=QUOTER_V2_ABI
    )


def get_slot0(pool_address: str):
    pool = load_pool_contract(pool_address)
    try:
        slot0 = pool.functions.slot0().call()
    except BadFunctionCallOutput as e:
        raise RuntimeError(f"Failed reading slot0 from pool {pool_address}: {e}")
    return {"sqrtPriceX96": int(slot0[0]), "tick": int(slot0[1])}


def get_pool_tokens_and_decimals(pool_address: str):
    pool = load_pool_contract(pool_address)
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()

    erc0 = load_erc20_contract(token0)
    erc1 = load_erc20_contract(token1)

    try:
        dec0 = erc0.functions.decimals().call()
    except Exception:
        dec0 = 18

    try:
        dec1 = erc1.functions.decimals().call()
    except Exception:
        dec1 = 18

    try:
        sym0 = erc0.functions.symbol().call()
    except Exception:
        sym0 = None
    try:
        sym1 = erc1.functions.symbol().call()
    except Exception:
        sym1 = None
    
    display_sym0 = "ETH" if sym0 in ["WETH", "weth"] else sym0
    display_sym1 = sym1

    return {
        "token0": Web3.to_checksum_address(token0),
        "token1": Web3.to_checksum_address(token1),
        "decimals0": int(dec0),
        "decimals1": int(dec1),
        "symbol0": display_sym0,
        "symbol1": display_sym1,
    }


def price_from_sqrtprice(sqrtPriceX96: int, decimals0: int, decimals1: int) -> Decimal:
    """
    Convert sqrtPriceX96 to human-readable price.
    Returns token1 per token0 (e.g., USDC per ETH for ETH/USDC pool).
    """
    sqrt_dec = Decimal(sqrtPriceX96)
    numerator = sqrt_dec * sqrt_dec
    denom = Decimal(2) ** Decimal(192)
    raw = numerator / denom
    scale = Decimal(10) ** Decimal(decimals0 - decimals1)
    price = raw * scale
    return price


def quote_exact_input_single_v2(
    token_in: str,
    token_out: str,
    fee: int,
    amount_in: int,
    sqrt_price_limit_x96: int = 0
) -> dict:
    quoter = load_quoter_v2_contract()
    
    params = (
        Web3.to_checksum_address(token_in),
        Web3.to_checksum_address(token_out),
        amount_in,
        fee,
        sqrt_price_limit_x96
    )
    
    try:
        result = quoter.functions.quoteExactInputSingle(params).call()
        
        return {
            'amountOut': int(result[0]),
            'sqrtPriceX96After': int(result[1]),
            'initializedTicksCrossed': int(result[2]),
            'gasEstimate': int(result[3])
        }
    except Exception as e:
        raise RuntimeError(f"QuoterV2 call failed: {e}")


def get_amm_output(
    token_in: str,
    token_out: str,
    amount_in: int,
    fee: int = 3000
) -> dict:
    
    quote_result = quote_exact_input_single_v2(
        token_in=token_in,
        token_out=token_out,
        fee=fee,
        amount_in=amount_in
    )
    
    return {
        'amountOut': quote_result['amountOut'],
        'sqrtPriceX96After': quote_result['sqrtPriceX96After'],
        'fee': fee,
        'token_in': Web3.to_checksum_address(token_in),
        'token_out': Web3.to_checksum_address(token_out),
        'amount_in': amount_in
    }


def get_price_for_pool(pool_address: str):
    
    tokens = get_pool_tokens_and_decimals(pool_address)
    slot0 = get_slot0(pool_address)
    sqrtP = slot0["sqrtPriceX96"]
    tick = slot0["tick"]
    price = price_from_sqrtprice(sqrtP, tokens["decimals0"], tokens["decimals1"])
    return {
        "pool": Web3.to_checksum_address(pool_address),
        "token0": tokens["token0"],
        "token1": tokens["token1"],
        "symbol0": tokens["symbol0"],
        "symbol1": tokens["symbol1"],
        "decimals0": tokens["decimals0"],
        "decimals1": tokens["decimals1"],
        "sqrtPriceX96": str(sqrtP),
        "tick": int(tick),
        "price_eth_per_usdt": price  # Decimal - token1 per token0 (USDC per ETH for ETH/USDC pool)
    }


# ============================================
# Simple test when run as script
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("TESTING UNISWAP V3 MODULE (with Quoter V2)")
    print("=" * 70)
    print()
    
    # ETH/USDC pool on Base (fee 0.3%)
    # Source: https://basescan.org/address/0xce1d8c90a5f0ef28fe0f457e5ad615215899319a
    POOL_ADDR = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    
    # Token addresses on Base
    WETH = "0x4200000000000000000000000000000000000006"
    USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    
    print("TEST 1: Get Pool Price")
    print("-" * 70)
    try:
        tokens = get_pool_tokens_and_decimals(POOL_ADDR)
        print(f"✅ Pool: {POOL_ADDR}")
        print(f"   Tokens: {tokens['token0']} / {tokens['token1']}")
        print(f"   Symbols: {tokens['symbol0']} / {tokens['symbol1']}")
        print(f"   Decimals: {tokens['decimals0']} / {tokens['decimals1']}")

        slot0 = get_slot0(POOL_ADDR)
        print(f"   sqrtPriceX96: {slot0['sqrtPriceX96']}")
        print(f"   tick: {slot0['tick']}")

        price = price_from_sqrtprice(slot0["sqrtPriceX96"], tokens["decimals0"], tokens["decimals1"])
        print(f"   Price (token1/token0): {price}")

        out = get_price_for_pool(POOL_ADDR)
        print(f"   Price ETH/USDC: {out['price_eth_per_usdt']:.2f} USDC/ETH")
        print()

    except Exception as e:
        print(f"❌ Error in TEST 1: {e}")
        print()
    
    print("TEST 2: Quote Exact Input (Quoter V2)")
    print("-" * 70)
    try:
        # Quote 1 ETH -> USDC
        amount_in = 1 * 10**18  # 1 ETH
        
        print(f"   Input: {amount_in / 10**18:.4f} ETH")
        print(f"   Token In:  {WETH}")
        print(f"   Token Out: {USDC}")
        print(f"   Fee: 3000 (0.3%)")
        print()
        
        quote_result = quote_exact_input_single_v2(
            token_in=WETH,
            token_out=USDC,
            fee=3000,
            amount_in=amount_in
        )
        
        amount_out = quote_result['amountOut']
        print(f"✅ Quoter V2 Result:")
        print(f"   Amount Out: {amount_out / 10**6:.2f} USDC")
        print(f"   Effective Price: {amount_out / amount_in * 10**12:.2f} USDC/ETH")
        print(f"   Gas Estimate: {quote_result['gasEstimate']:,}")
        print(f"   Ticks Crossed: {quote_result['initializedTicksCrossed']}")
        print()
        
    except Exception as e:
        print(f"❌ Error in TEST 2: {e}")
        print()
    
    print("TEST 3: Get AMM Output (Wrapper)")
    print("-" * 70)
    try:
        # Test với 5000 USDC -> ETH
        amount_in_usdc = 5000 * 10**6  # 5000 USDC
        
        print(f"   Input: {amount_in_usdc / 10**6:.2f} USDC")
        print(f"   Swap: USDC -> ETH")
        print()
        
        result = get_amm_output(
            token_in=USDC,
            token_out=WETH,
            amount_in=amount_in_usdc,
            fee=3000
        )
        
        print(f"✅ AMM Output:")
        print(f"   Amount Out: {result['amountOut'] / 10**18:.6f} ETH")
        print(f"   Effective Price: {amount_in_usdc / result['amountOut'] * 10**12:.2f} USDC/ETH")
        print()
        
    except Exception as e:
        print(f"❌ Error in TEST 3: {e}")
        print()
    
    print("=" * 70)
    print("✅ MODULE 1 TESTING COMPLETED!")
    print("=" * 70)
