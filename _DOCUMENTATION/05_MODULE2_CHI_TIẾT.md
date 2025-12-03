# 📦 Module 2: Tạo Orderbook Giả - Chi Tiết

**Ngày cập nhật**: 3 Tháng 12, 2025  
**File**: `services/orderbook/synthetic_orderbook.py`  
**Dòng code**: 350 lines  
**Thời gian đọc**: ~40 phút

---

## 🎯 Mục Đích Module 2

**Tạo orderbook ảo (synthetic) từ giá AMM** với 3 tình huống khác nhau

```
INPUT: Giá từ Module 1 + Swap amount
  ↓
XỬ LÝ: Tính giá các level + size từng level
  ↓
OUTPUT: Danh sách OrderbookLevel (price + amount_in + amount_out)
```

---

## 📊 3 Scenarios Có Gì Khác?

| Scenario | Độ Sâu | Levels | Spread | Trường Hợp | Savings |
|----------|--------|--------|--------|-----------|---------|
| **Small** | 0.5× | 1 | 30 bps | Thị trường xấu | +0.1% |
| **Medium** ⭐ | 2.5× | 3 | 10 bps | Bình thường | +0.4% |
| **Large** | Scaled $1M | 5-10 | 5 bps | Whale trade | +1.5% |

---

## 🏗️ Cấu Trúc Code

```
Module 2 (synthetic_orderbook.py)
│
├── Class: OrderbookLevel (dataclass)
│   └─ price, amount_in_available, amount_out_available
│
├── Class: SyntheticOrderbookGenerator
│   ├─ __init__()
│   │
│   ├─ generate_scenario_small()    ← 1 level (worst case)
│   ├─ generate_scenario_medium()   ← 3 levels (⭐ khuyến nghị)
│   ├─ generate_scenario_large()    ← 5-10 levels (best case)
│   │
│   ├─ generate()  [MAIN API - Router]
│   │
│   └─ Helper methods:
│       ├─ _calculate_amount_out()
│       ├─ _apply_exponential_decay()
│       └─ get_total_depth()
```

---

## 🔧 Phần 1: OrderbookLevel - Dataclass

### Cấu Trúc Dữ Liệu

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class OrderbookLevel:
    """Đơn vị dữ liệu: 1 mức giá trong orderbook"""
    price: Decimal              # Giá tại level (token_out/token_in)
    amount_in_available: int    # Lượng input available (base units)
    amount_out_available: int   # Lượng output available (base units)
```

### Ý Nghĩa Từng Field

| Field | Ý Nghĩa | Ví Dụ |
|-------|---------|-------|
| **price** | Giá giao dịch (Decimal) | 0.000358 ETH/USDT |
| **amount_in_available** | Lượng USDT có (base units) | 3000 × 10^6 |
| **amount_out_available** | Lượng ETH nhận (base units) | 1.057 × 10^18 |

### Ví Dụ Thực Tế

```python
level_1 = OrderbookLevel(
    price=Decimal("0.000358"),           # 1 USDT → 0.000358 ETH
    amount_in_available=3_000_000_000,   # 3000 USDT (6 decimals)
    amount_out_available=1_074_000_000_000_000_000  # 1.074 ETH (18 decimals)
)

# Ý nghĩa: Có thể swap 3000 USDT lấy 1.074 ETH tại giá 0.000358
```

---

## 🔧 Phần 2: Generator - Constructor

### Khởi Tạo

```python
from decimal import Decimal

# Từ Module 1, ta lấy mid_price
mid_price = Decimal("0.000357")  # ETH/USDT

# Tạo generator
generator = SyntheticOrderbookGenerator(
    mid_price=mid_price,
    decimals_in=6,   # USDT (6 decimals)
    decimals_out=18  # ETH (18 decimals)
)
```

### Constructor Code

```python
class SyntheticOrderbookGenerator:
    def __init__(self, mid_price: Decimal, decimals_in: int, decimals_out: int):
        """
        Khởi tạo generator
        
        Args:
            mid_price (Decimal): Giá từ Module 1
            decimals_in (int): Decimals input token (6 cho USDT)
            decimals_out (int): Decimals output token (18 cho ETH)
        """
        self.mid_price = mid_price
        self.decimals_in = decimals_in
        self.decimals_out = decimals_out
        self.decimal_scale = Decimal(10) ** Decimal(decimals_out - decimals_in)
```

---

## 🎯 Scenario 1: SMALL (Worst Case)

### Đặc Điểm

```
Tình huống:     Orderbook rất mỏng
Độ sâu:         ~0.5× swap_amount (50%)
Số levels:      1 (chỉ 1 mức giá)
Spread:         30 bps (0.3%) từ mid price
Khi nào dùng:   Thị trường xấu, ít liquidity
```

### Algorithm Tính Toán

```
BƯỚC 1: Tính giá
  Spread BPS = 30 bps = 0.003
  
  Bid side:  price_bid = mid_price × (1 - 0.003)
  Ask side:  price_ask = mid_price × (1 + 0.003)

BƯỚC 2: Tính size
  amount_in = 0.5 × swap_amount

BƯỚC 3: Tính output
  amount_out = amount_in × price × 10^(decimals_out - decimals_in)
             = amount_in × price × 10^12  (ETH/USDT case)
```

### Code Implementation

```python
def generate_scenario_small(self, swap_amount: int, is_bid: bool = False):
    """
    Generate Small scenario (worst case)
    
    Args:
        swap_amount (int): Số lượng input (base units)
        is_bid (bool): True = BID (sell ETH), False = ASK (buy ETH)
    
    Returns:
        list[OrderbookLevel]: 1 level only
    """
    DEPTH_MULTIPLIER = Decimal('0.5')    # 50% of swap_amount
    SPREAD_BPS = Decimal('30')           # 30 basis points
    
    # Tính giá
    if is_bid:
        # BID: người bán ETH, mua USDT → giá thấp hơn mid
        price = self.mid_price * (1 - SPREAD_BPS / Decimal('10000'))
    else:
        # ASK: người mua ETH, bán USDT → giá cao hơn mid
        price = self.mid_price * (1 + SPREAD_BPS / Decimal('10000'))
    
    # Tính size
    amount_in_available = int(Decimal(swap_amount) * DEPTH_MULTIPLIER)
    amount_out_available = self._calculate_amount_out(amount_in_available, price)
    
    return [OrderbookLevel(price, amount_in_available, amount_out_available)]
```

### Ví Dụ Tính Toán

```
INPUT:
  mid_price = 0.000357 ETH/USDT
  swap_amount = 3000 × 10^6 USDT (3000 USDT)
  is_bid = False (ASK side - buying ETH)

TÍNH TOÁN BƯỚC 1: Giá
  SPREAD_BPS = 30 bps = 30/10000 = 0.003
  price_ask = 0.000357 × (1 + 0.003)
            = 0.000357 × 1.003
            = 0.000358 ETH/USDT

TÍNH TOÁN BƯỚC 2: Size input
  DEPTH = 0.5
  amount_in = 3000 × 10^6 × 0.5
            = 1500 × 10^6 USDT

TÍNH TOÁN BƯỚC 3: Size output
  amount_out = 1500 × 10^6 × 0.000358 × 10^12
             = 1500 × 0.000358 × 10^18
             = 0.537 × 10^18 USDT
             = 0.537 ETH

OUTPUT:
[
  OrderbookLevel(
    price=Decimal("0.000358"),
    amount_in_available=1_500_000_000,        # 1500 USDT
    amount_out_available=537_000_000_000_000_000  # 0.537 ETH
  )
]

✅ Ý NGHĨA: Orderbook Small chỉ có 1 level:
   "Tôi bán 1500 USDT để mua 0.537 ETH tại giá 0.000358 ETH/USDT"
```

---

## 🎯 Scenario 2: MEDIUM (Realistic Case) ⭐

### Đặc Điểm

```
Tình huống:     Orderbook vừa phải
Độ sâu:         ~2.5× swap_amount (250%)
Số levels:      3 levels (⭐ khuyến nghị)
Spread:         10 bps (0.1%) từ mid price
Khi nào dùng:   Thị trường bình thường, production
```

### Ladder Pricing Algorithm

```
CÔNG THỨC CHUNG:
  price_at_level_n = mid_price × (1 ± n × 0.01%)

MEDIUM SCENARIO:
  BID side (sell ETH):
    Level 1: mid × (1 - 1×0.01%) = mid × 0.9999
    Level 2: mid × (1 - 2×0.01%) = mid × 0.9998
    Level 3: mid × (1 - 3×0.01%) = mid × 0.9997
  
  ASK side (buy ETH):
    Level 1: mid × (1 + 1×0.01%) = mid × 1.0001
    Level 2: mid × (1 + 2×0.01%) = mid × 1.0002
    Level 3: mid × (1 + 3×0.01%) = mid × 1.0003
```

### Exponential Decay Formula

```
Size tại level N = Size_level1 × (decay_factor ^ (N-1))

Với decay_factor = 0.8:
  Level 1: 1.0 × (0.8^0) = 1.0 (100%)
  Level 2: 1.0 × (0.8^1) = 0.8 (80%)
  Level 3: 1.0 × (0.8^2) = 0.64 (64%)
  
Total = 1.0 + 0.8 + 0.64 = 2.44 (≈ 2.5× target)
```

### Code Implementation

```python
def generate_scenario_medium(self, swap_amount: int, is_bid: bool = False):
    """
    Generate Medium scenario (realistic case)
    
    Args:
        swap_amount (int): Số lượng input
        is_bid (bool): BID or ASK side
    
    Returns:
        list[OrderbookLevel]: 3 levels with exponential decay
    """
    NUM_LEVELS = 3
    SPREAD_BPS = Decimal('10')           # 10 bps base spread
    DECAY_FACTOR = Decimal('0.8')        # Size decay 20% per level
    
    levels = []
    base_amount = int(Decimal(swap_amount) / Decimal('2.5'))  # Average size
    
    for level_idx in range(1, NUM_LEVELS + 1):
        # Tính giá (ladder pricing)
        spread_adjustment = Decimal(level_idx) * SPREAD_BPS / Decimal('10000')
        if is_bid:
            price = self.mid_price * (1 - spread_adjustment)
        else:
            price = self.mid_price * (1 + spread_adjustment)
        
        # Tính size (exponential decay)
        amount_in = int(Decimal(base_amount) * (DECAY_FACTOR ** (level_idx - 1)))
        amount_out = self._calculate_amount_out(amount_in, price)
        
        levels.append(OrderbookLevel(price, amount_in, amount_out))
    
    return levels
```

### Ví Dụ Tính Toán Chi Tiết

```
INPUT:
  mid_price = 0.000357 ETH/USDT
  swap_amount = 3000 × 10^6 USDT
  is_bid = False (ASK side)

TÍNH TOÁN:
  target_depth = 2.5
  base_amount = 3000 / 2.5 = 1200 USDT = 1200 × 10^6

LEVEL 1:
  spread = 1 × 10/10000 = 0.001 (1 bps × 1)
  price = 0.000357 × (1 + 0.001) = 0.000357357
  amount_in = 1200 × 10^6 × 0.8^0 = 1200 × 10^6
  amount_out = 1200 × 10^6 × 0.000357357 × 10^12 = 0.4288 × 10^18

LEVEL 2:
  spread = 2 × 10/10000 = 0.002 (2 bps)
  price = 0.000357 × (1 + 0.002) = 0.000357714
  amount_in = 1200 × 10^6 × 0.8^1 = 960 × 10^6
  amount_out = 960 × 10^6 × 0.000357714 × 10^12 = 0.3433 × 10^18

LEVEL 3:
  spread = 3 × 10/10000 = 0.003 (3 bps)
  price = 0.000357 × (1 + 0.003) = 0.000358071
  amount_in = 1200 × 10^6 × 0.8^2 = 768 × 10^6
  amount_out = 768 × 10^6 × 0.000358071 × 10^12 = 0.2750 × 10^18

OUTPUT (ASK side):
[
  OrderbookLevel(Decimal("0.000357357"), 1_200_000_000, 428_800_000_000_000_000),
  OrderbookLevel(Decimal("0.000357714"), 960_000_000, 343_326_000_000_000_000),
  OrderbookLevel(Decimal("0.000358071"), 768_000_000, 275_061_000_000_000_000)
]

TỔNG CỘNG:
  Total input: 1200 + 960 + 768 = 2928 USDT (≈ 2.5×)
  Total output: (0.4288 + 0.3433 + 0.2750) ETH = 1.047 ETH
```

---

## 🎯 Scenario 3: LARGE (Best Case)

### Đặc Điểm

```
Tình huống:     Orderbook sâu như CEX
Độ sâu:         Scaled từ $1M reference
Số levels:      5-10 levels
Spread:         5 bps (0.05%) từ mid price
Khi nào dùng:   Whale traders, best case scenario
```

### Algorithm

```
BƯỚC 1: Tính reference depth ($1,000,000)
  total_input_usd = 1,000,000
  each_level_size = 1,000,000 / 10 = 100,000 (nếu 10 levels)

BƯỚC 2: Scale theo actual swap amount
  scale_factor = swap_amount / 1,000,000
  actual_level_size = 100,000 × scale_factor × decay_factor^(n-1)

BƯỚC 3: Apply exponential decay
  Size = base × (0.8 ^ (level-1))
```

### Ví Dụ

```
INPUT:
  mid_price = 0.000357 ETH/USDT
  swap_amount = 100,000 × 10^6 USDT ($100K)
  is_bid = False

OUTPUT: 10 levels với exponential decay
  Level 1: 10,000 USDT @ 0.000357357 → 3.573 ETH
  Level 2: 8,000 USDT @ 0.000357714 → 2.862 ETH
  Level 3: 6,400 USDT @ 0.000358071 → 2.290 ETH
  ...
  Level 10: ~2,100 USDT @ ... → ...
  
Total: ~250,000 USDT depth
```

---

## 🔧 Helper Methods

### `_calculate_amount_out(amount_in, price)`

```python
def _calculate_amount_out(self, amount_in: int, price: Decimal) -> int:
    """
    Tính output amount từ input + price
    
    Formula: amount_out = amount_in × price × 10^(decimals_out - decimals_in)
    """
    return int(Decimal(amount_in) * price * self.decimal_scale)
```

### `get_total_depth(levels)`

```python
def get_total_depth(self, levels: list[OrderbookLevel]) -> Decimal:
    """
    Tính tổng depth của orderbook
    """
    return sum(Decimal(level.amount_in_available) for level in levels)
```

---

## ⭐ Main API: `generate(scenario, swap_amount)`

### Mục Đích

Router hàm - gọi scenario tương ứng

### Code

```python
def generate(self, scenario: str, swap_amount: int, is_bid: bool = False):
    """
    Main API - Router to different scenarios
    
    Args:
        scenario (str): "small", "medium", or "large"
        swap_amount (int): Input amount (base units)
        is_bid (bool): BID or ASK side
    
    Returns:
        list[OrderbookLevel]: Orderbook levels
    """
    if scenario == "small":
        return self.generate_scenario_small(swap_amount, is_bid)
    elif scenario == "medium":
        return self.generate_scenario_medium(swap_amount, is_bid)
    elif scenario == "large":
        return self.generate_scenario_large(swap_amount, is_bid)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
```

### Cách Sử Dụng

```python
# Từ Module 1
mid_price = Decimal("0.000357")
swap_amount = 3000 × 10^6  # 3000 USDT

# Tạo generator
generator = SyntheticOrderbookGenerator(
    mid_price=mid_price,
    decimals_in=6,
    decimals_out=18
)

# Generate Medium orderbook
ob_medium = generator.generate(
    scenario="medium",
    swap_amount=swap_amount,
    is_bid=False
)

# Output: 3 OrderbookLevel objects
for level in ob_medium:
    print(f"Price: {level.price}, Input: {level.amount_in_available}, Output: {level.amount_out_available}")
```

---

## 📈 Luồng Hoàn Chỉnh Module 2

```
STEP 1: Nhận giá từ Module 1
  mid_price = 0.000357 ETH/USDT
  
STEP 2: Tạo generator
  gen = SyntheticOrderbookGenerator(mid_price, 6, 18)
  
STEP 3: Chọn scenario
  scenario = "medium"  (khuyến nghị)
  
STEP 4: Generate orderbook
  ob = gen.generate(scenario, 3000×10^6, is_bid=False)
  
STEP 5: Output
  ├─ Level 1: 0.000357357 ETH/USDT, 1200 USDT → 0.429 ETH
  ├─ Level 2: 0.000357714 ETH/USDT, 960 USDT → 0.343 ETH
  └─ Level 3: 0.000358071 ETH/USDT, 768 USDT → 0.275 ETH
  
STEP 6: Pass to Module 3
  → Module 3 sẽ khớp lệnh từ orderbook này
```

---

## 💡 Ghi Nhớ

✅ **Module 2** tạo orderbook dựa trên giá AMM  
✅ **3 Scenarios** để test various market conditions  
✅ **Ladder pricing** làm giá thay đổi theo level  
✅ **Exponential decay** làm size giảm theo level  
✅ **Medium** khuyến nghị dùng trong production  

---

## 🎓 Bước Tiếp Theo

Sau khi hiểu Module 2:
- ✅ Biết tạo orderbook synthetic
- ✅ Hiểu ladder pricing
- ✅ Hiểu exponential decay

→ Tiếp theo: **06_MODULE3_CHI_TIẾT.md**
   - Sử dụng orderbook từ Module 2
   - Khớp lệnh (matching) để tìm best price

