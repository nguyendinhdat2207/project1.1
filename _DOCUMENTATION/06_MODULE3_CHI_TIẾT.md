# 🎯 Module 3: Khớp Lệnh Tham Lam - Chi Tiết

**Ngày cập nhật**: 3 Tháng 12, 2025  
**File**: `services/matching/greedy_matcher.py`  
**Dòng code**: 200 lines  
**Thời gian đọc**: ~30 phút

---

## 🎯 Mục Đích Module 3

**Khớp lệnh từ orderbook với input của user sử dụng thuật toán tham lam**

```
INPUT: Orderbook từ Module 2 + Swap amount
  ↓
XỬ LÝ: Greedy matching - chọn tốt nhất trước
  ↓
OUTPUT: Match result (ob_output, amm_fallback, savings)
```

---

## 💡 Thuật Toán Greedy Matching

### Ý Tưởng

```
"Chọn giá tốt nhất, fill hết, sau đó chọn tiếp"

Ví dụ: User muốn 10,000 USDT → ETH

Orderbook BID (người bán ETH):
├─ Level 1: 2807.82 USDT/ETH, 2.0 ETH ← CHỌN TRƯỚC (tốt nhất)
├─ Level 2: 2807.12 USDT/ETH, 1.6 ETH ← CHỌN THỨ 2
├─ Level 3: 2806.41 USDT/ETH, 1.28 ETH ← CHỌN THỨ 3
└─ Level 4: 2800.00 USDT/ETH, 1.0 ETH ← KHÔNG CHỌN (quá rẻ)

Xử lý:
├─ Level 1: 2.0 ETH @ 2807.82 = 5,615.64 USDT (dùng)
├─ Level 2: 1.6 ETH @ 2807.12 = 4,491.39 USDT (không đủ)
│          → Chỉ lấy (10,000 - 5,615.64) / 2807.12 = 1.56 ETH
├─ Hết input
└─ Phần còn (0.04 ETH) → dùng AMM fallback
```

---

## 🔧 Cấu Trúc Code

```
Module 3 (greedy_matcher.py)
│
├── Class: LevelUsed (dataclass)
│   └─ level_index, amount_used, price
│
├── Class: GreedyMatcher
│   ├─ __init__()
│   │
│   ├─ match() [MAIN API]
│   │   └─ Khớp lệnh main logic
│   │
│   ├─ _filter_by_threshold()
│   │   └─ Lọc theo threshold (5 bps default)
│   │
│   ├─ _sort_by_price()
│   │   └─ Sắp xếp theo giá
│   │
│   └─ _calculate_savings()
│       └─ Tính tiết kiệm so với AMM
```

---

## 📌 Data Structures

### LevelUsed (Dataclass)

```python
@dataclass
class LevelUsed:
    level_index: int       # Index của level trong orderbook
    amount_used: Decimal   # Lượng input dùng
    price: Decimal         # Giá tại level này
```

### MatchResult (Output Dict)

```python
{
    "ob_output_amount": Decimal,      # ETH từ OB
    "amm_fallback_amount": Decimal,   # ETH từ AMM fallback
    "total_output": Decimal,          # Tổng ETH
    "ob_price_avg": Decimal,          # Giá trung bình OB
    "amm_price": Decimal,             # Giá AMM
    "savings": Decimal,               # ETH tiết kiệm
    "savings_percent": Decimal,       # % tiết kiệm
    "levels_used": int,               # Số levels khớp
    "levels_detail": list[LevelUsed]  # Chi tiết từng level
}
```

---

## 🔧 Function 1: `__init__` - Constructor

```python
class GreedyMatcher:
    def __init__(self, amm_price: Decimal, threshold_bps: Decimal = Decimal('5')):
        """
        Khởi tạo matcher
        
        Args:
            amm_price (Decimal): Giá AMM từ Module 1
            threshold_bps (Decimal): Threshold filtering (basis points)
                                   5 bps = 0.05% = 0.0005
        """
        self.amm_price = amm_price
        self.threshold_bps = threshold_bps
        
        # Tính threshold value
        self.threshold_value = amm_price * (threshold_bps / Decimal('10000'))
        self.price_floor = amm_price - self.threshold_value
```

### Ví Dụ

```
amm_price = 0.000357 ETH/USDT
threshold_bps = 5 bps

threshold_value = 0.000357 × (5/10000) = 0.00000017850
price_floor = 0.000357 - 0.00000017850 = 0.00035682150

→ Chỉ accept BID prices >= 0.00035682150
```

---

## 🔧 Function 2: `_filter_by_threshold()`

```python
def _filter_by_threshold(self, orderbook: list[OrderbookLevel]) -> list[OrderbookLevel]:
    """
    Lọc orderbook theo threshold (5 bps)
    
    Chỉ giữ lại các level tốt hơn price_floor
    """
    filtered = []
    for level in orderbook:
        if level.price >= self.price_floor:
            filtered.append(level)
        # else: Reject level quá rẻ
    return filtered
```

### Ví Dụ Filtering

```
INPUT (Orderbook):
├─ Level 1: 2807.82 USDT/ETH (chuyển sang OB currency: 0.000357357)
├─ Level 2: 2807.12 USDT/ETH (0.000357714)
├─ Level 3: 2806.41 USDT/ETH (0.000357900)
└─ Level 4: 2800.00 USDT/ETH (0.000357000) ← REJECT!

price_floor = 2805 USDT/ETH (từ 5 bps threshold)

OUTPUT:
├─ Level 1: ✅ 2807.82 >= 2805
├─ Level 2: ✅ 2807.12 >= 2805
├─ Level 3: ✅ 2806.41 >= 2805
└─ Level 4: ❌ 2800.00 < 2805 (quá rẻ, loại)
```

---

## 🔧 Function 3: `match()` - MAIN API

```python
def match(self, orderbook: list[OrderbookLevel], swap_amount: int, amm_price: Decimal):
    """
    Khớp lệnh greedy (MAIN API)
    
    Args:
        orderbook (list): Từ Module 2
        swap_amount (int): Số lượng input (base units)
        amm_price (Decimal): Giá AMM từ Module 1
    
    Returns:
        dict: Match result (ob_output, amm_fallback, savings, ...)
    """
    # Bước 1: Lọc theo threshold
    filtered_ob = self._filter_by_threshold(orderbook)
    
    # Bước 2: Sắp xếp theo giá tốt nhất trước
    sorted_ob = sorted(filtered_ob, key=lambda x: x.price, reverse=True)
    
    # Bước 3: Greedy matching
    remaining_input = Decimal(swap_amount)
    ob_output = Decimal(0)
    levels_used = []
    
    for idx, level in enumerate(sorted_ob):
        if remaining_input <= 0:
            break
        
        # Tính lượng dùng từ level này
        amount_can_use = min(
            Decimal(level.amount_in_available),
            remaining_input
        )
        
        # Tính output
        level_output = amount_can_use * level.price * self.decimal_scale
        
        # Cập nhật
        ob_output += level_output
        remaining_input -= amount_can_use
        
        levels_used.append(LevelUsed(idx, amount_can_use, level.price))
    
    # Bước 4: Tính AMM fallback
    amm_fallback = remaining_input * amm_price * self.decimal_scale
    total_output = ob_output + amm_fallback
    
    # Bước 5: Tính savings
    baseline_output = Decimal(swap_amount) * amm_price * self.decimal_scale
    savings = total_output - baseline_output
    savings_percent = (savings / baseline_output) * 100
    
    # Bước 6: Return result
    return {
        "ob_output_amount": ob_output,
        "amm_fallback_amount": amm_fallback,
        "total_output": total_output,
        "ob_price_avg": ob_output / Decimal(swap_amount) if ob_output > 0 else Decimal(0),
        "amm_price": amm_price,
        "savings": savings,
        "savings_percent": savings_percent,
        "levels_used": len(levels_used),
        "levels_detail": levels_used
    }
```

---

## 📊 Ví Dụ Tính Toán Chi Tiết

### Input

```
Orderbook (Medium):
├─ Level 1: 0.000357357 ETH/USDT, 1200 USDT available
├─ Level 2: 0.000357714 ETH/USDT, 960 USDT available
└─ Level 3: 0.000358071 ETH/USDT, 768 USDT available

swap_amount = 3000 × 10^6 USDT (3000 USDT)
amm_price = 0.000357 ETH/USDT
threshold_bps = 5 bps
```

### Xử Lý

```
STEP 1: Filter by threshold
  price_floor = 0.000357 × (1 - 0.0005) = 0.00035682150
  
  Level 1: 0.000357357 >= 0.00035682150 ✅
  Level 2: 0.000357714 >= 0.00035682150 ✅
  Level 3: 0.000358071 >= 0.00035682150 ✅
  
  → Tất cả pass

STEP 2: Sort by price (best first)
  Level 3: 0.000358071 (tốt nhất) ← CHỌN TRƯỚC
  Level 2: 0.000357714
  Level 1: 0.000357357 (tệ nhất)

STEP 3: Greedy matching
  remaining = 3000 USDT
  
  Level 3 (0.000358071):
    ├─ amount_available = 768 USDT
    ├─ amount_can_use = min(768, 3000) = 768 USDT
    ├─ output = 768 × 0.000358071 × 10^12 = 0.275 ETH
    ├─ ob_output = 0.275 ETH
    └─ remaining = 3000 - 768 = 2232 USDT
  
  Level 2 (0.000357714):
    ├─ amount_available = 960 USDT
    ├─ amount_can_use = min(960, 2232) = 960 USDT
    ├─ output = 960 × 0.000357714 × 10^12 = 0.343 ETH
    ├─ ob_output = 0.275 + 0.343 = 0.618 ETH
    └─ remaining = 2232 - 960 = 1272 USDT
  
  Level 1 (0.000357357):
    ├─ amount_available = 1200 USDT
    ├─ amount_can_use = min(1200, 1272) = 1200 USDT
    ├─ output = 1200 × 0.000357357 × 10^12 = 0.429 ETH
    ├─ ob_output = 0.618 + 0.429 = 1.047 ETH
    └─ remaining = 1272 - 1200 = 72 USDT

STEP 4: AMM fallback
  amm_fallback = 72 × 0.000357 × 10^12 = 0.0257 ETH
  total_output = 1.047 + 0.0257 = 1.0727 ETH

STEP 5: Calculate savings
  baseline_output = 3000 × 0.000357 × 10^12 = 1.071 ETH
  savings = 1.0727 - 1.071 = 0.0017 ETH
  savings_percent = (0.0017 / 1.071) × 100 = 0.159%

Output:
{
  "ob_output_amount": Decimal("1.047"),
  "amm_fallback_amount": Decimal("0.0257"),
  "total_output": Decimal("1.0727"),
  "ob_price_avg": Decimal("0.000357857"),  # 1.047 / 3000
  "amm_price": Decimal("0.000357"),
  "savings": Decimal("0.0017"),
  "savings_percent": Decimal("0.159"),
  "levels_used": 3,
  "levels_detail": [
    LevelUsed(2, 768, 0.000358071),
    LevelUsed(1, 960, 0.000357714),
    LevelUsed(0, 1200, 0.000357357)
  ]
}
```

---

## 🔧 Function 4: `_calculate_savings()`

```python
def _calculate_savings(self, ob_output: Decimal, total_output: Decimal) -> dict:
    """
    Tính tiết kiệm so với AMM
    
    Returns:
        dict: savings_eth, savings_usd, savings_percent
    """
    baseline = self.swap_amount * self.amm_price * self.decimal_scale
    
    savings_eth = total_output - baseline
    savings_usd = savings_eth / self.amm_price  # Convert to USD
    savings_percent = (savings_eth / baseline) * 100
    
    return {
        "savings_eth": savings_eth,
        "savings_usd": savings_usd,
        "savings_percent": savings_percent
    }
```

---

## ⭐ Threshold Filtering

### Tại Sao Cần Threshold?

```
Vấn đề: Orderbook có thể có mức giá quá rẻ
  Level 1: 2807 USDT/ETH
  Level 2: 2806 USDT/ETH
  Level 3: 2700 USDT/ETH ← Quá rẻ! (suspicious)
  
Giải pháp: Lọc theo threshold (5 bps default)
  price_floor = 2808.53 × (1 - 0.0005) = 2808.53 - 1.40 = 2807.13
  
  Level 1: 2807 >= 2807.13? ✅ (borderline)
  Level 2: 2806 >= 2807.13? ❌ (reject)
  Level 3: 2700 >= 2807.13? ❌ (reject)
```

### Công Thức

```
threshold_value = amm_price × (threshold_bps / 10000)
price_floor = amm_price - threshold_value

Ví dụ:
  amm_price = 2808.53 USDT/ETH
  threshold_bps = 5 bps = 0.0005
  threshold_value = 2808.53 × 0.0005 = 1.40
  price_floor = 2808.53 - 1.40 = 2807.13
```

---

## 📈 Luồng Hoàn Chỉnh Module 3

```
STEP 1: Nhận orderbook từ Module 2
  ob = [Level1, Level2, Level3, ...]
  
STEP 2: Tạo matcher
  matcher = GreedyMatcher(amm_price=0.000357, threshold_bps=5)
  
STEP 3: Khớp lệnh
  result = matcher.match(ob, swap_amount=3000×10^6, amm_price=0.000357)
  
STEP 4: Output
  ├─ ob_output: 1.047 ETH
  ├─ amm_fallback: 0.0257 ETH
  ├─ total_output: 1.0727 ETH
  ├─ savings: 0.0017 ETH (0.159%)
  └─ levels_used: 3
  
STEP 5: Pass to Module 4
  → Module 4 sẽ build execution plan
```

---

## 💡 Ghi Nhớ

✅ **Greedy** = chọn tốt nhất trước  
✅ **Threshold** = bảo vệ không quá rẻ (5 bps default)  
✅ **Fallback** = phần còn dùng AMM  
✅ **Savings** = khác biệt so với 100% AMM  

---

## 🎓 Bước Tiếp Theo

Sau khi hiểu Module 3:
- ✅ Biết greedy matching algorithm
- ✅ Hiểu threshold filtering
- ✅ Tính toán savings

→ Tiếp theo: **07_MODULE4_CHI_TIẾT.md**
   - Build execution plan từ match result
   - Chuẩn bị gửi blockchain

