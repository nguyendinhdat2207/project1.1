# services/uniswap_v3.py
import os
import json
import math
import time
from decimal import Decimal, getcontext

from web3 import Web3
from web3.exceptions import BadFunctionCallOutput
from dotenv import load_dotenv

# Load ENV trước
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
if not RPC_URL:
    raise RuntimeError("RPC_URL không được cấu hình trong .env")

# Tạo web3 sau
web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
print("Connected to RPC:", web3.is_connected())

# Load ABI
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

# Quoter V2 address on Base mainnet
# Source: https://docs.uniswap.org/contracts/v3/reference/deployments
QUOTER_V2_ADDRESS = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"


# ---------------------------------------
# Helper: load pool contract
# ---------------------------------------
def load_pool_contract(pool_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_ABI)


def load_erc20_contract(token_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)


def load_quoter_v2_contract():
    """Load Quoter V2 contract."""
    return web3.eth.contract(
        address=Web3.to_checksum_address(QUOTER_V2_ADDRESS),
        abi=QUOTER_V2_ABI
    )


# ---------------------------------------
# Read slot0 safely
# ---------------------------------------
def get_slot0(pool_address: str):
    """
    Trả về dict: { sqrtPriceX96: int, tick: int }
    """
    pool = load_pool_contract(pool_address)
    try:
        slot0 = pool.functions.slot0().call()
    except BadFunctionCallOutput as e:
        raise RuntimeError(f"Lỗi đọc slot0 từ pool {pool_address}: {e}")
    # slot0[0] = sqrtPriceX96, slot0[1] = tick
    return {"sqrtPriceX96": int(slot0[0]), "tick": int(slot0[1])}


# ---------------------------------------
# Read token0/token1 and decimals
# ---------------------------------------
def get_pool_tokens_and_decimals(pool_address: str):
    pool = load_pool_contract(pool_address)
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()

    erc0 = load_erc20_contract(token0)
    erc1 = load_erc20_contract(token1)

    try:
        dec0 = erc0.functions.decimals().call()
    except Exception:
        dec0 = 18  # fallback

    try:
        dec1 = erc1.functions.decimals().call()
    except Exception:
        dec1 = 18

    # try to get symbols (best-effort)
    try:
        sym0 = erc0.functions.symbol().call()
    except Exception:
        sym0 = None
    try:
        sym1 = erc1.functions.symbol().call()
    except Exception:
        sym1 = None
    
    # Normalize WETH to ETH for display purposes
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


# ---------------------------------------
# Convert sqrtPriceX96 -> price (token1 per token0)
# 
# IMPORTANT: token0 = Base Asset, token1 = Quote Asset
# Example: ETH/USDT pool -> token0=ETH, token1=USDT
#   price_from_sqrtprice(...) returns USDT per ETH (token1 per token0)
#
# Formula:
#   raw = (sqrtPriceX96 ** 2) / 2**192
#   price_adjusted = raw * 10**(decimals0 - decimals1)
# Explanation:
#   raw gives ratio in token's raw units; we adjust to human decimals.
#   Với ETH (18 decimals) / USDT (6 decimals):
#   price_adjusted = raw * 10^(18 - 6) = raw * 10^12
# ---------------------------------------
def price_from_sqrtprice(sqrtPriceX96: int, decimals0: int, decimals1: int) -> Decimal:
    """
    Return price token1 per token0 as Decimal.
    
    Args:
        sqrtPriceX96: sqrtPrice from pool.slot0()
        decimals0: decimals of token0 (base asset, ETH = 18)
        decimals1: decimals of token1 (quote asset, USDT = 6)
    
    Returns:
        Price of token1 per token0 as Decimal
        Example: For ETH/USDT pool (token0=ETH, token1=USDT):
                 returns USDT per ETH = 3032.28 (bao nhiêu USDT cho 1 ETH)
    """
    # use Decimal for high precision
    sqrt_dec = Decimal(sqrtPriceX96)
    numerator = sqrt_dec * sqrt_dec  # sqrtPriceX96 ** 2
    denom = Decimal(2) ** Decimal(192)
    raw = numerator / denom  # raw token1/token0 in smallest units ratio
    # adjust by decimals: token1/token0 human = raw * 10^(decimals0 - decimals1)
    scale = Decimal(10) ** Decimal(decimals0 - decimals1)
    price = raw * scale
    return price


# ---------------------------------------
# Quoter V2: Quote exact input single
# ---------------------------------------
def quote_exact_input_single_v2(
    token_in: str,
    token_out: str,
    fee: int,
    amount_in: int,
    sqrt_price_limit_x96: int = 0
) -> dict:
    """
    Gọi QuoterV2.quoteExactInputSingle() để lấy output chính xác từ AMM.
    
    Args:
        token_in: Address của token input
        token_out: Address của token output
        fee: Pool fee tier (500 = 0.05%, 3000 = 0.3%, 10000 = 1%)
        amount_in: Lượng token input (base units)
        sqrt_price_limit_x96: Price limit (0 = no limit)
    
    Returns:
        dict: {
            'amountOut': int - Lượng token output (base units),
            'sqrtPriceX96After': int - SqrtPrice sau swap,
            'initializedTicksCrossed': int - Số tick crossed,
            'gasEstimate': int - Gas estimate
        }
    
    Example:
        # Quote 1 ETH -> USDT swap
        result = quote_exact_input_single_v2(
            token_in="0x4200000000000000000000000000000000000006",  # WETH
            token_out="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", # USDC
            fee=3000,
            amount_in=1000000000000000000  # 1 ETH
        )
        # result['amountOut'] = 3032280000  # ~3032 USDC
    """
    quoter = load_quoter_v2_contract()
    
    # Prepare params tuple
    params = (
        Web3.to_checksum_address(token_in),
        Web3.to_checksum_address(token_out),
        amount_in,
        fee,
        sqrt_price_limit_x96
    )
    
    try:
        # Call quoter (static call, no gas cost)
        result = quoter.functions.quoteExactInputSingle(params).call()
        
        return {
            'amountOut': int(result[0]),
            'sqrtPriceX96After': int(result[1]),
            'initializedTicksCrossed': int(result[2]),
            'gasEstimate': int(result[3])
        }
    except Exception as e:
        raise RuntimeError(f"Lỗi gọi QuoterV2: {e}")


# ---------------------------------------
# Get AMM output with automatic pool detection
# ---------------------------------------
def get_amm_output(
    token_in: str,
    token_out: str,
    amount_in: int,
    fee: int = 3000
) -> dict:
    """
    Lấy output từ AMM với Quoter V2.
    Wrapper function để dễ sử dụng.
    
    Args:
        token_in: Token input address
        token_out: Token output address
        amount_in: Amount to swap (base units)
        fee: Pool fee tier (default: 3000 = 0.3%)
    
    Returns:
        dict: {
            'amountOut': int,
            'fee': int,
            'token_in': str,
            'token_out': str,
            'amount_in': int
        }
    
    Example:
        result = get_amm_output(
            token_in="0x4200000000000000000000000000000000000006",  # WETH
            token_out="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", # USDC
            amount_in=1000000000000000000,  # 1 ETH
            fee=3000
        )
        print(f"Output: {result['amountOut']} USDC")
    """
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


# ---------------------------------------
# Public: get price for a pool address
# Returns dict with helpful fields
# ---------------------------------------
def get_price_for_pool(pool_address: str):
    """
    Trả về thông tin giá từ pool dưới dạng ETH/USDT.
    
    Returns:
      {
        "pool": pool_address,
        "token0": ..., "token1": ...,  (token0 = ETH, token1 = USDT)
        "symbol0": ..., "symbol1": ...,
        "decimals0": .., "decimals1": ..,
        "sqrtPriceX96": ..,
        "tick": ..,
        "price_eth_per_usdt": Decimal  (giá ETH/USDT - bao nhiêu USDT cho 1 ETH)
      }
    
    Example for ETH/USDT pool on Base:
      - token0 = ETH (0x420000...), token1 = USDT (0xfde4C9...)
      - price_eth_per_usdt = 3032.28 USDT per ETH
    """
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
        "price_eth_per_usdt": price  # Decimal - USDT per ETH
    }


# ============================================
# Simple test when run as script
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("TESTING UNISWAP V3 MODULE (with Quoter V2)")
    print("=" * 70)
    print()
    
    # ETH/USDT pool on Base (fee 0.3%)
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
        print(f"   Price ETH/USDT: {out['price_eth_per_usdt']:.2f} USDT/ETH")
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
