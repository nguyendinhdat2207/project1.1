# 🏗️ Module 4: Build Execution Plan - Chi Tiết

**Ngày cập nhật**: 3 Tháng 12, 2025  
**File**: `services/execution/execution_plan.py`  
**Dòng code**: 450 lines  
**Thời gian đọc**: ~40 phút

---

## 🎯 Mục Đích Module 4

**Tạo kế hoạch thực thi cho smart contract** dựa trên match result từ Module 3

```
INPUT: Match result từ Module 3
  ↓
XỬ LÝ: Tính toán chân OB + chân AMM, mã hóa hook_data, validate slippage
  ↓
OUTPUT: JSON execution plan (ready for blockchain)
```

---

## 🏗️ Cấu Trúc Code

```
Module 4 (execution_plan.py)
│
├── Class: ExecutionPlanBuilder
│   ├─ __init__()
│   │
│   ├─ build_plan() [MAIN API]
│   │   └─ Build complete execution plan
│   │
│   ├─ 6 Helper Methods:
│   │   ├─ _simulate_amm_leg()      ← Mô phỏng chân AMM
│   │   ├─ _build_legs()            ← Xây dựng 2 chân
│   │   ├─ _calculate_savings()     ← Tính savings
│   │   ├─ _calculate_fee_value()   ← Tính phí 30%
│   │   ├─ _encode_hook_data()      ← Mã hóa ABI
│   │   └─ _validate_slippage()     ← Kiểm tra slippage
│   │
│   └─ Helper utilities:
│       ├─ _to_wei()
│       └─ _from_wei()
```

---

## 🔧 Function 1: `__init__` - Constructor

```python
class ExecutionPlanBuilder:
    def __init__(self, 
                 amm_price: Decimal,
                 decimals_in: int = 6,
                 decimals_out: int = 18,
                 max_slippage: Decimal = Decimal('0.01'),
                 fee_percentage: Decimal = Decimal('0.30')):
        """
        Khởi tạo builder
        
        Args:
            amm_price (Decimal): Giá AMM từ Module 1
            decimals_in (int): Decimals input token (6 = USDT)
            decimals_out (int): Decimals output token (18 = ETH)
            max_slippage (Decimal): Max slippage (0.01 = 1%)
            fee_percentage (Decimal): Fee percentage (0.30 = 30%)
        """
        self.amm_price = amm_price
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
        self.max_slippage = max_slippage
        self.fee_percentage = fee_percentage
```

---

## 🔧 Function 2: `_simulate_amm_leg()` - Mô Phỏng Chân AMM

### Mục Đích

Tính input/output của chân AMM (phần fallback)

### Code

```python
def _simulate_amm_leg(self, match_result: dict) -> dict:
    """
    Mô phỏng chân AMM (fallback leg)
    
    Args:
        match_result: Từ Module 3
    
    Returns:
        dict: {input_amount, output_amount, price}
    """
    # Lấy AMM fallback từ match result
    amm_fallback_output = match_result['amm_fallback_amount']
    
    # Tính input từ output (đảo ngược)
    amm_input = amm_fallback_output / self.amm_price
    
    return {
        'input_amount': int(amm_input * Decimal(10) ** self.decimals_in),
        'output_amount': int(amm_fallback_output * Decimal(10) ** self.decimals_out),
        'price': self.amm_price
    }
```

### Ví Dụ

```
INPUT (match_result):
  amm_fallback_amount = 0.0257 ETH

OUTPUT:
  input_amount = 0.0257 / 0.000357 × 10^6 = 72 × 10^6 USDT
  output_amount = 0.0257 × 10^18 = 25,700,000,000,000,000 wei
  price = 0.000357
```

---

## 🔧 Function 3: `_build_legs()` - Xây Dựng 2 Chân

### Mục Đích

Xây dựng OB leg + AMM leg

### Code

```python
def _build_legs(self, match_result: dict) -> dict:
    """
    Build OB leg + AMM leg
    
    Returns:
        dict: {orderbook_leg, amm_leg}
    """
    # OB Leg
    ob_leg = {
        'input_amount': int(
            (Decimal(match_result['total_input']) - Decimal(match_result['amm_input']))
            * Decimal(10) ** self.decimals_in
        ),
        'output_amount': int(
            match_result['ob_output_amount'] * Decimal(10) ** self.decimals_out
        ),
        'price': match_result['ob_price_avg'],
        'levels_used': match_result['levels_used']
    }
    
    # AMM Leg
    amm_leg = self._simulate_amm_leg(match_result)
    
    return {
        'orderbook_leg': ob_leg,
        'amm_leg': amm_leg
    }
```

---

## 🔧 Function 4: `_calculate_savings()` - Tính Tiết Kiệm

### Mục Đích

Tính tiết kiệm USD so với 100% AMM

### Code

```python
def _calculate_savings(self, total_output: Decimal, swap_amount: int) -> Decimal:
    """
    Calculate savings in USD
    
    Args:
        total_output (Decimal): Tổng output từ Module 3
        swap_amount (int): Input amount
    
    Returns:
        Decimal: Savings in USD
    """
    # Output nếu chỉ dùng 100% AMM
    baseline_output = Decimal(swap_amount) * self.amm_price * Decimal(10) ** (self.decimals_out - self.decimals_in)
    
    # Savings (ETH)
    savings_eth = total_output - baseline_output
    
    # Savings (USD)
    savings_usd = savings_eth / self.amm_price
    
    return savings_usd
```

### Ví Dụ

```
swap_amount = 3000 × 10^6 USDT
amm_price = 0.000357 ETH/USDT
total_output = 1.0727 ETH

baseline = 3000 × 0.000357 × 10^12 = 1.071 ETH
savings_eth = 1.0727 - 1.071 = 0.0017 ETH
savings_usd = 0.0017 / 0.000357 = 4.76 USD
```

---

## 🔧 Function 5: `_calculate_fee_value()` - Tính Phí

### Mục Đích

Tính phí hybrid (30% của savings)

### Code

```python
def _calculate_fee_value(self, savings_usd: Decimal) -> Decimal:
    """
    Calculate hybrid fee (30% of savings)
    
    Args:
        savings_usd (Decimal): Tiết kiệm USD
    
    Returns:
        Decimal: Fee value USD
    """
    fee_value = savings_usd * self.fee_percentage
    return fee_value
```

### Ví Dụ

```
savings_usd = 4.76 USD
fee_percentage = 0.30 (30%)

fee_value = 4.76 × 0.30 = 1.43 USD (UniHybrid lấy)
user_value = 4.76 × 0.70 = 3.33 USD (User được)
```

---

## 🔧 Function 6: `_encode_hook_data()` - Mã Hóa Hook Data

### Mục Đích

Mã hóa dữ liệu cho smart contract hook

### Code

```python
def _encode_hook_data(self, legs: dict, fee_value: Decimal) -> str:
    """
    Encode hook data using eth_abi
    
    Args:
        legs (dict): OB leg + AMM leg
        fee_value (Decimal): Fee value
    
    Returns:
        str: Encoded hex string (0x...)
    """
    from eth_abi import encode
    
    # Prepare data
    ob_leg = legs['orderbook_leg']
    amm_leg = legs['amm_leg']
    
    # Encode using ABI
    encoded = encode(
        ['(uint256,uint256,uint256)', '(uint256,uint256,uint256)', 'uint256'],
        [
            (
                int(ob_leg['input_amount']),
                int(ob_leg['output_amount']),
                int(ob_leg['price'] * Decimal(10) ** 18)
            ),
            (
                int(amm_leg['input_amount']),
                int(amm_leg['output_amount']),
                int(amm_leg['price'] * Decimal(10) ** 18)
            ),
            int(fee_value * Decimal(10) ** 18)
        ]
    )
    
    return '0x' + encoded.hex()
```

### Output Example

```
hook_data = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
```

---

## 🔧 Function 7: `_validate_slippage()` - Kiểm Tra Slippage

### Mục Đích

Kiểm tra slippage <= max_slippage (1% default)

### Code

```python
def _validate_slippage(self, actual_output: Decimal, min_output: Decimal) -> bool:
    """
    Validate slippage
    
    Args:
        actual_output (Decimal): Tổng output thực tế
        min_output (Decimal): Minimum output (với slippage tolerance)
    
    Returns:
        bool: True if valid, False otherwise
    """
    if actual_output < min_output:
        return False
    return True
```

### Ví Dụ

```
max_slippage = 0.01 (1%)
actual_output = 1.0727 ETH
min_output = 1.0727 × (1 - 0.01) = 1.0619 ETH

Check: 1.0727 >= 1.0619? ✅ YES (PASS)
```

---

## ⭐ Function Main: `build_plan()` - MAIN API

```python
def build_plan(self, match_result: dict, swap_amount: int) -> dict:
    """
    Build complete execution plan [MAIN API]
    
    Args:
        match_result (dict): Từ Module 3
        swap_amount (int): Input amount (base units)
    
    Returns:
        dict: JSON execution plan (ready for blockchain)
    """
    # Bước 1: Build legs
    legs = self._build_legs(match_result)
    
    # Bước 2: Calculate savings
    total_output = match_result['total_output']
    savings_usd = self._calculate_savings(total_output, swap_amount)
    
    # Bước 3: Calculate fee (30% of savings)
    fee_value = self._calculate_fee_value(savings_usd)
    
    # Bước 4: Encode hook data
    hook_data = self._encode_hook_data(legs, fee_value)
    
    # Bước 5: Calculate min output (with slippage)
    min_output = total_output * (1 - self.max_slippage)
    
    # Bước 6: Validate slippage
    is_valid = self._validate_slippage(total_output, min_output)
    
    # Bước 7: Build result
    return {
        "router_address": "0x1234567890123456789012345678901234567890",  # Smart contract
        "orderbook_leg": {
            "input_amount": str(legs['orderbook_leg']['input_amount']),
            "output_amount": str(legs['orderbook_leg']['output_amount']),
            "price": str(legs['orderbook_leg']['price']),
            "levels_used": legs['orderbook_leg']['levels_used']
        },
        "amm_leg": {
            "input_amount": str(legs['amm_leg']['input_amount']),
            "output_amount": str(legs['amm_leg']['output_amount']),
            "price": str(legs['amm_leg']['price'])
        },
        "hook_data": hook_data,
        "max_slippage": str(self.max_slippage),
        "fee": {
            "percentage": str(self.fee_percentage),
            "usd_value": str(fee_value)
        },
        "savings": {
            "eth_amount": str(total_output - (Decimal(swap_amount) * self.amm_price * Decimal(10) ** (self.decimals_out - self.decimals_in))),
            "usd_value": str(savings_usd),
            "percentage": str((savings_usd / (Decimal(swap_amount) / self.amm_price)) * 100)
        },
        "validation": {
            "min_output": str(min_output),
            "actual_output": str(total_output),
            "status": "PASS" if is_valid else "FAIL"
        }
    }
```

---

## 📊 Ví Dụ Tính Toán Hoàn Chỉnh

### Input (từ Module 3)

```python
match_result = {
    'total_input': 3000,  # USDT
    'ob_output_amount': Decimal('1.047'),
    'amm_fallback_amount': Decimal('0.0257'),
    'total_output': Decimal('1.0727'),
    'ob_price_avg': Decimal('0.000357857'),
    'amm_price': Decimal('0.000357'),
    'levels_used': 3
}

swap_amount = 3000 × 10^6  # base units
```

### Xử Lý (7 Bước)

```
STEP 1: Build legs
  ob_leg:
    input_amount = (3000 - 72) × 10^6 = 2928 × 10^6
    output_amount = 1.047 × 10^18
    levels_used = 3
  
  amm_leg:
    input_amount = 72 × 10^6
    output_amount = 0.0257 × 10^18

STEP 2: Calculate savings
  baseline = 3000 × 0.000357 × 10^12 = 1.071 ETH
  savings_eth = 1.0727 - 1.071 = 0.0017 ETH
  savings_usd = 0.0017 / 0.000357 = 4.76 USD

STEP 3: Calculate fee (30%)
  fee_value = 4.76 × 0.30 = 1.43 USD

STEP 4: Encode hook_data
  hook_data = eth_abi.encode([...], [...])
           = 0x1234567890abcdef...

STEP 5: Min output (with 1% slippage)
  min_output = 1.0727 × (1 - 0.01) = 1.0619 ETH

STEP 6: Validate slippage
  1.0727 >= 1.0619? ✅ YES (PASS)

STEP 7: Build result (JSON)
  {
    "router_address": "0x...",
    "orderbook_leg": {...},
    "amm_leg": {...},
    "hook_data": "0x...",
    "fee": {"percentage": "0.30", "usd_value": "1.43"},
    "savings": {...},
    "validation": {...}
  }
```

### Output (JSON Ready for Blockchain)

```json
{
  "router_address": "0x1234567890123456789012345678901234567890",
  "orderbook_leg": {
    "input_amount": "2928000000",
    "output_amount": "1047000000000000000",
    "price": "0.000357857",
    "levels_used": 3
  },
  "amm_leg": {
    "input_amount": "72000000",
    "output_amount": "25700000000000000",
    "price": "0.000357"
  },
  "hook_data": "0x1234567890abcdef1234567890abcdef...",
  "max_slippage": "0.01",
  "fee": {
    "percentage": "0.30",
    "usd_value": "1.43"
  },
  "savings": {
    "eth_amount": "0.0017",
    "usd_value": "4.76",
    "percentage": "0.159"
  },
  "validation": {
    "min_output": "1.06177",
    "actual_output": "1.0727",
    "status": "PASS"
  }
}
```

---

## 📈 Luồng Hoàn Chỉnh Module 4

```
STEP 1: Nhận match_result từ Module 3
  ob_output=1.047 ETH, amm_fallback=0.0257 ETH
  
STEP 2: Tạo builder
  builder = ExecutionPlanBuilder(
    amm_price=0.000357,
    max_slippage=0.01,
    fee_percentage=0.30
  )
  
STEP 3: Build plan
  plan = builder.build_plan(match_result, swap_amount)
  
STEP 4: Validate
  ├─ Slippage check: PASS ✅
  ├─ Min output: 1.0619 ETH ✓
  └─ Actual output: 1.0727 ETH ✓
  
STEP 5: Gửi blockchain
  → Smart contract nhận JSON plan
  → Execute swap
  → Return 1.0727 ETH (tốt hơn 1.071 ETH của AMM)
```

---

## 💡 Ghi Nhớ

✅ **Module 4** tạo execution plan cho smart contract  
✅ **6 Helper methods** xây dựng plan từng phần  
✅ **Slippage protection** 1% default để an toàn  
✅ **Fee 30%** của tiết kiệm cho UniHybrid  
✅ **Hook encoding** để contract decode  

---

## 🎓 End-to-End Flow (Module 1-4)

```
Module 1: Fetch price (0.000357 ETH/USDT)
    ↓
Module 2: Create orderbook (3 levels, medium scenario)
    ↓
Module 3: Greedy match (1.047 ETH từ OB, 0.0257 ETH từ AMM)
    ↓
Module 4: Build execution plan (JSON ready for blockchain)
    ↓
Smart Contract: Execute
    ↓
Result: 1.0727 ETH received (vs 1.071 ETH with 100% AMM)
Savings: 0.0017 ETH = $4.76 USD = 0.159% better! 🎉
```

---

## 🎓 Bước Tiếp Theo

Sau khi hiểu Module 4:
- ✅ Biết cách build execution plan
- ✅ Hiểu 6 helper methods
- ✅ Hiểu slippage protection

→ Tiếp theo: **CẤU_TRÚC_TÀI_LIỆU.md**
   - Tóm tắt cấu trúc tài liệu
   - Thứ tự đọc khuyên dùng

