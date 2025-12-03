# 📊 Module 1: Lấy Giá Từ AMM - Chi Tiết

**Ngày cập nhật**: 3 Tháng 12, 2025  
**File**: `services/amm_uniswap_v3/uniswap_v3.py`  
**Dòng code**: 150 lines  
**Thời gian đọc**: ~30 phút

---

## 🎯 Mục Đích Module 1

**Lấy giá thực tế từ Uniswap V3 pool** trên blockchain Base Mainnet

```
INPUT:  Pool Address
  ↓
XỬ LÝ: Đọc dữ liệu smart contract
  ↓
OUTPUT: Giá thực tế (ETH/USDT)
```

---

## 📍 Pool Target

| Thuộc tính | Giá trị |
|-----------|--------|
| **Blockchain** | Base Mainnet |
| **Pool Address** | 0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0 |
| **Pair** | ETH / USDT |
| **Token0 (ETH)** | 0x4200000000000000000000000000000000000006 |
| **Token1 (USDT)** | 0x833589fcd6edb6e08f4c7c32d4f71b1566469c3d |
| **Decimals** | 18 / 6 |
| **Pool Fee** | 0.01% (1 bps) |

---

## 🏗️ Cấu Trúc Code

```
Module 1 (uniswap_v3.py)
│
├── Helper Functions
│   ├── load_pool_contract()
│   │   └─ Tải pool contract từ ABI
│   │
│   └── load_erc20_contract()
│       └─ Tải ERC20 contract từ ABI
│
├── 🔧 Function 1: get_slot0()
│   └─ Đọc sqrtPriceX96 + tick
│
├── 🔧 Function 2: get_pool_tokens_and_decimals()
│   └─ Lấy token addresses + decimals
│
├── 🔧 Function 3: price_from_sqrtprice()
│   └─ Chuyển sqrtPrice → giá dễ đọc
│
└── ⭐ Function 4: get_price_for_pool()
    └─ MAIN API - kết hợp tất cả
```

---

## 🔧 Function 1: `get_slot0(pool_address)`

### Mục Đích
Đọc **sqrtPriceX96** (giá hiện tại) và **tick** từ pool

### Mã Nguồn
```python
def get_slot0(pool_address: str):
    """
    Gọi hàm slot0() từ Uniswap V3 pool contract
    
    Args:
        pool_address (str): Địa chỉ pool (0x...)
    
    Returns:
        dict: {"sqrtPriceX96": int, "tick": int}
    """
    pool = load_pool_contract(pool_address)
    slot0 = pool.functions.slot0().call()
    
    # slot0() trả về tuple dài, chỉ cần index 0 và 1
    return {
        "sqrtPriceX96": int(slot0[0]),      # Index 0: Giá căn bậc 2
        "tick": int(slot0[1])                # Index 1: Vị trí tick
    }
```

### Input/Output Example

```
INPUT:
  pool_address = "0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0"

XỬ LÝ:
  ├─ Kết nối Web3 → pool contract
  ├─ Gọi pool.functions.slot0().call()
  └─ slot0() trả về tuple: (sqrtPrice, tick, fee, ...)

OUTPUT:
{
  "sqrtPriceX96": 1680399938736813340,
  "tick": -261503
}
```

### Ý Nghĩa

**sqrtPriceX96**:
- = √(price) × 2^96
- Lý do dùng × 2^96: để tránh số thập phân (dùng số nguyên)
- Ví dụ: sqrtPrice = 1680399938736813340 (số đơn vị nhỏ)

**tick**:
- Giá được biểu diễn ở mỗi "tick" nhỏ
- 1 tick = 0.01% giá thay đổi
- tick = -261503 = giá rất thấp (1 ETH ≈ 2800 USDT)

---

## 🔧 Function 2: `get_pool_tokens_and_decimals(pool_address)`

### Mục Đích
Lấy **token addresses**, **decimals**, và **symbols**

### Mã Nguồn
```python
def get_pool_tokens_and_decimals(pool_address: str):
    """
    Lấy thông tin token từ pool
    
    Args:
        pool_address (str): Địa chỉ pool
    
    Returns:
        dict: Token addresses + decimals + symbols
    """
    pool = load_pool_contract(pool_address)
    
    # Bước 1: Lấy token addresses
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()
    
    # Bước 2: Tạo ERC20 contracts
    erc0 = load_erc20_contract(token0)
    erc1 = load_erc20_contract(token1)
    
    # Bước 3: Gọi decimals()
    decimals0 = erc0.functions.decimals().call()  # → 18
    decimals1 = erc1.functions.decimals().call()  # → 6
    
    # Bước 4: Gọi symbol()
    symbol0 = erc0.functions.symbol().call()      # → "WETH"
    symbol1 = erc1.functions.symbol().call()      # → "USDT"
    
    # Bước 5: Normalize symbols (WETH → ETH)
    display_symbol0 = "ETH" if symbol0 == "WETH" else symbol0
    
    return {
        "token0": token0,
        "token1": token1,
        "decimals0": decimals0,
        "decimals1": decimals1,
        "symbol0": display_symbol0,
        "symbol1": symbol1
    }
```

### Input/Output Example

```
INPUT:
  pool_address = "0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0"

XỬ LÝ:
  ├─ Lấy token0 từ pool → 0x4200...0006
  ├─ Lấy token1 từ pool → 0x8335...9bb2
  ├─ Gọi token0.decimals() → 18
  ├─ Gọi token1.decimals() → 6
  ├─ Gọi token0.symbol() → "WETH"
  ├─ Gọi token1.symbol() → "USDT"
  └─ Normalize WETH → ETH

OUTPUT:
{
  "token0": "0x4200000000000000000000000000000000000006",
  "token1": "0x833589fcd6edb6e08f4c7c32d4f71b1566469c3d",
  "decimals0": 18,
  "decimals1": 6,
  "symbol0": "ETH",
  "symbol1": "USDT"
}
```

### Tại Sao Decimals Quan Trọng?

```
ETH (Token0):
  1 ETH = 10^18 wei (smallest unit)
  Ví dụ: 1.5 ETH = 1.5 × 10^18 = 1,500,000,000,000,000,000 wei

USDT (Token1):
  1 USDT = 10^6 microUST (smallest unit)
  Ví dụ: 1.5 USDT = 1.5 × 10^6 = 1,500,000 microUST

Để chuyển đổi đúng:
  Phải nhân với 10^(decimals0 - decimals1) = 10^12
```

---

## 🔧 Function 3: `price_from_sqrtprice(sqrtPriceX96, decimals0, decimals1)`

### Mục Đích
**Chuyển đổi sqrtPrice → giá dễ đọc** (Decimal)

### ⭐ CÔNG THỨC QUAN TRỌNG

```
price = (sqrtPrice / 2^96)² × 10^(decimals0 - decimals1)

Hay chi tiết hơn:
  Bước 1: raw_ratio = (sqrtPrice)² / 2^192
  Bước 2: price = raw_ratio × 10^(decimals0 - decimals1)
```

### Ví Dụ Tính Toán Cụ Thể

```
INPUT:
  sqrtPriceX96 = 1680399938736813340  (raw value từ blockchain)
  decimals0 = 18 (ETH)
  decimals1 = 6 (USDT)

TÍNH TOÁN BƯỚC 1: raw_ratio
  sqrtPrice_squared = 1680399938736813340²
                    = 2.8235e+36
  
  raw_ratio = 2.8235e+36 / 2^192
            = 2.8235e+36 / 6.277e+57
            = 4.49e-12

TÍNH TOÁN BƯỚC 2: Điều chỉnh decimals
  decimals_adjustment = 10^(18-6) = 10^12
  price = 4.49e-12 × 10^12
        = 4.49 USDT/ETH
        
  ❌ SAI! Vì 1 ETH = ~2800 USDT, không phải 4.49!

GIẢI THÍCH SỰ KHÁC BIỆT:
  - Token0 (ETH) và Token1 (USDT) có đơn vị khác nhau
  - sqrtPrice được tính từ token0/token1
  - price_from_sqrtprice() tính: 1 unit token0 = ? unit token1
  - Nhưng từ dữ liệu thực → 1 ETH = 2800 USDT
  - → 4.49 ≈ 1/2800 (đảo ngược!)

KẾT LUẬN:
  Giá thực tế = 1 / price_from_sqrtprice()
             = 1 / 4.49
             = 0.000357 ETH/USDT
             = 1 USDT = 0.000357 ETH
             = 1 ETH = 2,800 USDT ✅
```

### Mã Nguồn

```python
def price_from_sqrtprice(sqrtPriceX96: int, decimals0: int, decimals1: int):
    """
    Chuyển đổi sqrtPrice thành giá dễ đọc
    
    Args:
        sqrtPriceX96 (int): sqrt(price) × 2^96
        decimals0 (int): Decimals của token0
        decimals1 (int): Decimals của token1
    
    Returns:
        Decimal: Giá (token0 / token1)
    """
    from decimal import Decimal, getcontext
    
    # Tăng precision để tránh rounding errors
    getcontext().prec = 100
    
    # Bước 1: Tính bình phương
    sqrt_dec = Decimal(sqrtPriceX96)
    numerator = sqrt_dec * sqrt_dec
    
    # Bước 2: Chia cho 2^192 (vì sqrtPrice × 2^96, bình phương = × 2^192)
    denominator = Decimal(2) ** Decimal(192)
    raw_ratio = numerator / denominator
    
    # Bước 3: Điều chỉnh decimals (QUAN TRỌNG!)
    decimal_scale = Decimal(10) ** Decimal(decimals0 - decimals1)
    price = raw_ratio * decimal_scale
    
    return price  # Decimal type
```

### Output Example

```
OUTPUT:
  price = Decimal('0.000356937...') ETH/USDT

GIẢI THÍCH:
  ✅ 0.000357 ETH/USDT
  ✅ = 1 USDT mua được 0.000357 ETH
  ✅ = 1 ETH = 2,800+ USDT
```

---

## ⭐ Function 4: `get_price_for_pool(pool_address)` [MAIN API]

### Mục Đích
**Hàm chính của Module 1** - kết hợp tất cả 3 hàm trên

### Mã Nguồn

```python
def get_price_for_pool(pool_address: str):
    """
    Lấy giá thực tế từ pool [MAIN API]
    
    Args:
        pool_address (str): Địa chỉ Uniswap V3 pool
    
    Returns:
        Decimal: Giá (token0 / token1)
    """
    # Bước 1: Lấy thông tin token + decimals
    token_info = get_pool_tokens_and_decimals(pool_address)
    
    # Bước 2: Lấy sqrtPrice + tick
    slot0_data = get_slot0(pool_address)
    
    # Bước 3: Tính giá từ sqrtPrice
    price = price_from_sqrtprice(
        sqrtPriceX96=slot0_data["sqrtPriceX96"],
        decimals0=token_info["decimals0"],
        decimals1=token_info["decimals1"]
    )
    
    # Bước 4: Return dict hoàn chỉnh
    return {
        "pool": pool_address,
        "symbol0": token_info["symbol0"],           # "ETH"
        "symbol1": token_info["symbol1"],           # "USDT"
        "price_raw": price,                         # Decimal
        "price_float": float(price),                # Float (dễ đọc)
        "price_formatted": f"{float(price):.6f}",  # Formatted
        "inverse_price": Decimal(1) / price,        # USDT/ETH
        "sqrtPriceX96": slot0_data["sqrtPriceX96"],
        "tick": slot0_data["tick"]
    }
```

### Input/Output Example (Thực Tế)

```
INPUT:
  pool_address = "0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0"
  (ETH/USDT pool on Base Mainnet)

XỬ LÝ:
  ├─ Bước 1: get_pool_tokens_and_decimals()
  │  └─ token0=ETH (18 dec), token1=USDT (6 dec)
  │
  ├─ Bước 2: get_slot0()
  │  └─ sqrtPriceX96 = 1680399938736813340
  │
  ├─ Bước 3: price_from_sqrtprice()
  │  └─ price = 0.000356937... ETH/USDT
  │
  └─ Bước 4: Return complete dict

OUTPUT:
{
  "pool": "0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0",
  "symbol0": "ETH",
  "symbol1": "USDT",
  "price_raw": Decimal("0.000356937123456789"),
  "price_float": 0.000356937,
  "price_formatted": "0.000357",
  "inverse_price": Decimal("2808.53"),        # ← USDT/ETH
  "sqrtPriceX96": 1680399938736813340,
  "tick": -261503
}

GIẢI THÍCH KẾT QUẢ:
  ✅ 0.000357 ETH/USDT = 1 USDT = 0.000357 ETH
  ✅ 2808.53 USDT/ETH = 1 ETH = 2808.53 USDT
  ✅ Cả hai là đúng, chỉ là đảo ngược!
```

---

## 📈 Luồng Hoạt Động Chi Tiết

```
STEP 1: User gọi get_price_for_pool(pool_address)
         ↓
STEP 2: Hàm tải pool contract từ ABI
         ├─ Web3.eth.contract(address=pool_address, abi=POOL_ABI)
         └─ pool object ready
         ↓
STEP 3: Gọi get_pool_tokens_and_decimals()
         ├─ pool.functions.token0().call() → 0x4200...
         ├─ pool.functions.token1().call() → 0x8335...
         ├─ token0_contract.functions.decimals().call() → 18
         ├─ token1_contract.functions.decimals().call() → 6
         └─ Return: {token0, token1, decimals0, decimals1, ...}
         ↓
STEP 4: Gọi get_slot0()
         ├─ pool.functions.slot0().call() → (sqrtPrice, tick, ...)
         └─ Return: {sqrtPriceX96, tick}
         ↓
STEP 5: Gọi price_from_sqrtprice()
         ├─ Tính: (sqrtPrice)² / 2^192 × 10^12
         └─ Return: Decimal('0.000356937...')
         ↓
STEP 6: Build result dictionary
         ├─ Thêm price thực tế
         ├─ Thêm price đảo ngược (USDT/ETH)
         └─ Return: Complete dict
         ↓
STEP 7: Return to caller
         └─ price = 0.000357 ETH/USDT (hoặc 2808.53 USDT/ETH)
```

---

## 🔬 Công Thức Toán Học Chi Tiết

### Công Thức Chuyển Đổi Giá

```
Công thức chung Uniswap V3:
  price = (sqrtPrice / 2^96)²
  
Điều chỉnh decimals:
  price_adjusted = price × 10^(decimals0 - decimals1)
  
Ví dụ ETH/USDT:
  decimals0 - decimals1 = 18 - 6 = 12
  price_adjusted = price × 10^12
```

### Tại Sao ÷ 2^192?

```
sqrtPrice = √(price) × 2^96

sqrtPrice² = [√(price) × 2^96]²
          = price × (2^96)²
          = price × 2^192

Nên: price = sqrtPrice² / 2^192
```

### Decimal Precision

```python
from decimal import Decimal, getcontext

# Để tránh rounding errors
getcontext().prec = 100  # 100 chữ số thập phân

# Sử dụng Decimal thay vì float
price = Decimal("0.000356937123456789")  # Exact
# Thay vì
price = 0.000356937  # Float (mất precision)
```

---

## 🎓 Bước Tiếp Theo

Hiểu xong Module 1:
- ✅ Biết lấy giá từ blockchain
- ✅ Biết cách chuyển đổi sqrtPrice
- ✅ Biết tầm quan trọng của decimals

→ Tiếp theo: **05_MODULE2_CHI_TIẾT.md**
   - Sử dụng giá từ Module 1
   - Tạo orderbook giả

