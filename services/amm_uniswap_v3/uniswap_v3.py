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

with open(POOL_ABI_PATH, "r") as f:
    POOL_ABI = json.load(f)
with open(ERC20_ABI_PATH, "r") as f:
    ERC20_ABI = json.load(f)


# ---------------------------------------
# Helper: load pool contract
# ---------------------------------------
def load_pool_contract(pool_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_ABI)


def load_erc20_contract(token_address: str):
    return web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)


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
    # ETH/USDT pool on Base (fee 0.3%)
    # Source: https://basescan.org/address/0xce1d8c90a5f0ef28fe0f457e5ad615215899319a
    POOL_ADDR = "0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a"
    print("Testing Uniswap V3 service, pool:", POOL_ADDR)
    print("Pool: ETH/USDT on Base (0.3% fee)")

    # Thêm in từng bước chi tiết
    try:
        tokens = get_pool_tokens_and_decimals(POOL_ADDR)
        print("Tokens:", tokens["token0"], "/", tokens["token1"])
        print("Symbols:", tokens["symbol0"], "/", tokens["symbol1"])
        print("Decimals:", tokens["decimals0"], "/", tokens["decimals1"])

        slot0 = get_slot0(POOL_ADDR)
        print("sqrtPriceX96:", slot0["sqrtPriceX96"])
        print("tick:", slot0["tick"])

        price = price_from_sqrtprice(slot0["sqrtPriceX96"], tokens["decimals0"], tokens["decimals1"])
        print("price (token1 per token0):", price)

        out = get_price_for_pool(POOL_ADDR)
        print("Full output dict:", out)

    except Exception as e:
        print("Error:", e)
