# 📦 Tổng Quan Các Module

**Ngày cập nhật**: 3 Tháng 12, 2025  
**Thời gian đọc**: ~20 phút

---

## 🎯 Mục Đích

File này giúp bạn:
- ✅ Hiểu mục đích từng module
- ✅ Hiểu cách các module kết nối với nhau
- ✅ Theo dõi flow dữ liệu từ input đến output
- ✅ Biết input/output của mỗi module

---

## 📊 Sơ Đồ Luồng Hoàn Chỉnh

```
                    ┌─────────────────────────┐
                    │    NGƯỜI DÙNG SWAP      │
                    │  10,000 USDT → ETH      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     MODULE 1: LẤY      │
                    │      GIÁ TỪ AMM        │
                    │   uniswap_v3.py        │
                    │  (150 lines code)      │
                    └────────────┬────────────┘
                                 │
                    Input: Pool address
                    ├─ get_slot0()
                    ├─ get_pool_tokens_and_decimals()
                    ├─ price_from_sqrtprice()
                    └─ get_price_for_pool()
                    
                    Output: Giá AMM
                    └─ sqrtPrice = 1680399...
                       price = 2808.53 USDT/ETH
                                 │
                    ┌────────────▼────────────┐
                    │   MODULE 2: TẠO        │
                    │   ORDERBOOK GIẢ        │
                    │ synthetic_orderbook.py │
                    │  (350 lines code)      │
                    └────────────┬────────────┘
                                 │
                    Input: Giá AMM, quantity
                    ├─ generate_scenario_small()     (1 level)
                    ├─ generate_scenario_medium()    (3 levels) ⭐
                    └─ generate_scenario_large()     (5-10 levels)
                    
                    Công thức:
                    ├─ Ladder pricing
                    └─ Exponential decay (0.8 factor)
                    
                    Output: Orderbook levels
                    ├─ Level 1: 2810.50 USDT/ETH, 1.5 ETH
                    ├─ Level 2: 2809.00 USDT/ETH, 2.0 ETH
                    ├─ Level 3: 2807.00 USDT/ETH, 2.5 ETH
                    └─ ...
                                 │
                    ┌────────────▼────────────┐
                    │     MODULE 3: KHỚP     │
                    │      LỆNH THAM LẠM     │
                    │   greedy_matcher.py    │
                    │  (200 lines code)      │
                    └────────────┬────────────┘
                                 │
                    Input: Orderbook, swap amount
                    ├─ Duyệt từ giá tốt nhất
                    ├─ Chọn cho đến khi fill hết
                    ├─ Tính threshold (5 bps)
                    └─ Calculate savings
                    
                    Output: Match result
                    ├─ ob_output_amount: 3.56 ETH
                    ├─ amm_fallback_amount: 0.02 ETH
                    ├─ total_output: 3.5805 ETH
                    └─ savings: 0.39%
                                 │
                    ┌────────────▼────────────┐
                    │    MODULE 4: BUILD      │
                    │   EXECUTION PLAN       │
                    │  execution_plan.py    │
                    │  (450 lines code)      │
                    └────────────┬────────────┘
                                 │
                    Input: Match result
                    ├─ _simulate_amm_leg()
                    ├─ _build_legs()
                    ├─ _calculate_savings()
                    ├─ _calculate_fee_value()
                    ├─ _encode_hook_data()
                    └─ _validate_slippage()
                    
                    Output: JSON Execution Plan
                    {
                      "router": "0x...",
                      "orderbook_leg": { ... },
                      "amm_leg": { ... },
                      "hook_data": "0x...",
                      "max_slippage": "0.01",
                      "savings_usd": 56
                    }
                                 │
                    ┌────────────▼────────────┐
                    │  GỬI BLOCKCHAIN        │
                    │  Smart Contract        │
                    └────────────┬────────────┘
                                 │
                    ✅ KẾT QUẢ: 3.5805 ETH
                       (tốt hơn 3.5606 ETH của AMM)
```

---

## 🔍 Chi Tiết Từng Module

### **MODULE 1️⃣: Lấy Giá Từ AMM** 📊

**File**: `services/amm_uniswap_v3/uniswap_v3.py`  
**Dòng code**: 150 lines  
**Tác vụ**: Fetch giá real-time từ Uniswap V3

#### **Các Hàm Chính**

| Hàm | Mục Đích | Input | Output |
|-----|---------|-------|--------|
| `get_slot0()` | Lấy dữ liệu slot0 từ pool | pool_address | sqrtPrice, tick |
| `get_pool_tokens_and_decimals()` | Lấy token info | pool_address | token0, token1, decimals |
| `price_from_sqrtprice()` | Chuyển sqrt(P) → P | sqrtPrice | price (float) |
| `get_price_for_pool()` | Lấy giá cuối | pool_address | ETH/USDT price |

#### **Ví Dụ Thực Tế**

```
Input:
├─ Pool Address: 0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0
└─ Network: Base Mainnet

Xử lý:
├─ Gọi get_slot0() → sqrtPrice = 168039938...
├─ Gọi get_pool_tokens_and_decimals() → 
│  ├─ token0 = ETH (18 decimals)
│  └─ token1 = USDT (6 decimals)
├─ Gọi price_from_sqrtprice() → price = 2808.53
└─ Gọi get_price_for_pool() → final price

Output:
└─ 2808.53 USDT/ETH ✅
```

#### **Công Thức Chính**

```
sqrtPrice (raw) → sqrtPrice (scaled)
         ↓
  price = sqrtPrice² / 2^96
         ↓
  price = price × (10^decimals_token1 / 10^decimals_token0)
         ↓
  Final price: 2808.53 USDT/ETH
```

#### **Lưu Ý**
- ✅ Lấy giá trực tiếp từ blockchain (on-chain)
- ✅ Độ chính xác cao (Decimal type)
- ⚠️ Có thể slow nếu RPC chậm
- ⚠️ Phụ thuộc vào pool được cấu hình

---

### **MODULE 2️⃣: Tạo Orderbook Giả** 📚

**File**: `services/orderbook/synthetic_orderbook.py`  
**Dòng code**: 350 lines  
**Tác vụ**: Sinh tạo synthetic orderbook từ giá AMM

#### **3 Scenarios**

| Scenario | Mục Đích | Levels | Use Case |
|----------|----------|--------|----------|
| **Small** | Kiểm tra nhanh | 1 bid + 1 ask | Testing |
| **Medium** | ⭐ Khuyến nghị | 3 bid + 3 ask | Production |
| **Large** | Deep liquidity | 5-10 bid/ask | Whale traders |

#### **Ladder Pricing Algorithm**

```
Giá AMM: 2808.53 USDT/ETH

BID SIDE (Người muốn bán ETH, mua USDT):
├─ Level 1: 2808.53 × (1 - 0.01%) = 2807.82  (tốt nhất)
├─ Level 2: 2808.53 × (1 - 0.02%) = 2807.12
├─ Level 3: 2808.53 × (1 - 0.03%) = 2806.41

ASK SIDE (Người muốn mua ETH, bán USDT):
├─ Level 1: 2808.53 × (1 + 0.01%) = 2809.24  (tốt nhất)
├─ Level 2: 2808.53 × (1 + 0.02%) = 2809.95
├─ Level 3: 2808.53 × (1 + 0.03%) = 2810.66
```

#### **Exponential Decay Formula**

```
Size_at_level = Size_level1 × (decay_factor ^ (level - 1))

Ví dụ (Medium scenario):
decay_factor = 0.8

├─ Level 1: 2.0 ETH × (0.8^0) = 2.0 ETH
├─ Level 2: 2.0 ETH × (0.8^1) = 1.6 ETH
└─ Level 3: 2.0 ETH × (0.8^2) = 1.28 ETH

Total: 2.0 + 1.6 + 1.28 = 4.88 ETH ✅
```

#### **Ví Dụ Chi Tiết (Medium Scenario)**

```
Input:
├─ base_price: 2808.53 USDT/ETH
├─ user_amount: 10,000 USDT
└─ scenario: "medium"

Xử lý generate_scenario_medium():
├─ Tính 3 levels bid
│  ├─ BID-1: 2807.82 USDT/ETH, 2.0 ETH
│  ├─ BID-2: 2807.12 USDT/ETH, 1.6 ETH
│  └─ BID-3: 2806.41 USDT/ETH, 1.28 ETH
│
├─ Tính 3 levels ask
│  ├─ ASK-1: 2809.24 USDT/ETH, 2.0 ETH
│  ├─ ASK-2: 2809.95 USDT/ETH, 1.6 ETH
│  └─ ASK-3: 2810.66 USDT/ETH, 1.28 ETH
│
└─ Total liquidity: 4.88 ETH bid + 4.88 ETH ask

Output:
{
  "bid_levels": [
    {"price": 2807.82, "amount": 2.0},
    {"price": 2807.12, "amount": 1.6},
    {"price": 2806.41, "amount": 1.28}
  ],
  "ask_levels": [
    {"price": 2809.24, "amount": 2.0},
    {"price": 2809.95, "amount": 1.6},
    {"price": 2810.66, "amount": 1.28}
  ]
}
```

#### **Lưu Ý**
- ✅ Orderbook là giả tạo từ giá AMM
- ✅ 3 scenarios dễ so sánh
- ⚠️ Medium khuyến nghị để balance giữa size vs depth
- ⚠️ Size nhỏ → ít tiết kiệm, Size lớn → quá deep

---

### **MODULE 3️⃣: Khớp Lệnh Tham Lam** 🎯

**File**: `services/matching/greedy_matcher.py`  
**Dòng code**: 200 lines  
**Tác vụ**: Khớp lệnh từ orderbook với input của user

#### **Greedy Algorithm**

```
Thuật toán: THAM LẠM (Greedy)
├─ Bắt đầu từ giá tốt nhất
├─ Chọn lệnh ở giá tốt nhất
├─ Nếu hết lệnh, chuyển giá xấu hơn
├─ Tiếp tục cho đến khi fill hết input
└─ Đảm bảo: MAX SAVINGS

Ví dụ:
User swap: 10,000 USDT → ETH

Orderbook BID (người bán ETH):
├─ BID-1: 2807.82 USDT/ETH, 2.0 ETH  ← CHỌN TRƯỚC
├─ BID-2: 2807.12 USDT/ETH, 1.6 ETH  ← CHỌN THỨ 2
└─ BID-3: 2806.41 USDT/ETH, 1.28 ETH ← CHỌN THỨ 3

Xử lý:
├─ Fill BID-1: 2.0 ETH @ 2807.82 = 5,615.64 USDT (dùng 5,615.64)
├─ Fill BID-2: 1.6 ETH @ 2807.12 = 4,491.39 USDT (dùng 4,384.36)
└─ Còn lại: 10,000 - 5,615.64 - 4,384.36 = 0 USDT ✅ (chính xác)

Total từ OB: 3.56 ETH
Giá trung bình OB: 10,000 / 3.56 = 2809.41 USDT/ETH
```

#### **Threshold Filtering (5 bps default)**

```
5 bps = 5 basis points = 0.05%

Ví dụ:
├─ Giá AMM: 2808.53 USDT/ETH
├─ Threshold: 2808.53 × 0.05% = 1.40 USDT
├─ Price floor: 2808.53 - 1.40 = 2807.13 USDT/ETH
│
└─ BID chỉ được nhận nếu >= 2807.13
   ├─ BID-1 @ 2807.82: ✅ Accept
   ├─ BID-2 @ 2807.12: ❌ Reject (quá rẻ)
   └─ BID-3 @ 2806.41: ❌ Reject
```

#### **Match Result**

```
Output:
{
  "ob_output_amount": 3.56,          # ETH từ OB
  "amm_fallback_amount": 0.0199,     # ETH từ AMM fallback
  "total_output": 3.5805,            # Tổng ETH
  "ob_price_avg": 2809.41,           # Giá trung bình OB
  "amm_price": 2808.53,              # Giá AMM
  "savings": 0.0199,                 # ETH tiết kiệm
  "savings_percent": 0.39,           # % tiết kiệm
  "levels_used": 2                   # Số levels khớp
}
```

#### **Tính Savings**

```
Tiết Kiệm = (Total Output Khác) - (Total Output UniHybrid)
          = 3.5606 - 3.5805
          = -0.0199 ETH (âm = được thêm)
          
% Tiết Kiệm = -0.0199 / 3.5606 × 100%
            = 0.39%
            
USD Tiết Kiệm = 0.0199 × 2808.53
              = $55.93
```

#### **Lưu Ý**
- ✅ Chọn tốt nhất trước (Greedy)
- ✅ Threshold bảo vệ không quá rẻ
- ⚠️ Số levels khớp ảnh hưởng đến tiết kiệm
- ⚠️ Nếu quá nhiều levels → slippage tăng

---

### **MODULE 4️⃣: Build Execution Plan** 🏗️

**File**: `services/execution/execution_plan.py`  
**Dòng code**: 450 lines  
**Tác vụ**: Tạo kế hoạch thực thi cho smart contract

#### **6 Helper Methods**

| Method | Mục Đích | Input | Output |
|--------|---------|-------|--------|
| `_simulate_amm_leg()` | Mô phỏng chân AMM | match_result | amm_amounts |
| `_build_legs()` | Xây dựng chân swap | ob+amm amounts | legs array |
| `_calculate_savings()` | Tính savings | prices | savings_value |
| `_calculate_fee_value()` | Tính phí hybrid | savings | fee_amount |
| `_encode_hook_data()` | Mã hóa hook data | execution params | encoded hex |
| `_validate_slippage()` | Kiểm tra slippage | min_output | pass/fail |

#### **Ví Dụ Thực Tế**

```
Input (Match Result):
{
  "ob_output_amount": 3.56,
  "amm_fallback_amount": 0.0199,
  "total_output": 3.5805,
  "savings_percent": 0.39,
  "levels_used": 2
}

Xử lý:

1. _simulate_amm_leg():
   ├─ amm_input: 10,000 × 0.0199 / 3.56 = 55.90 USDT
   └─ amm_output: 0.0199 ETH

2. _build_legs():
   ├─ OB leg:
   │  ├─ input: 9,944.10 USDT
   │  └─ output: 3.5606 ETH
   └─ AMM leg:
      ├─ input: 55.90 USDT
      └─ output: 0.0199 ETH

3. _calculate_savings():
   ├─ baseline_output: 3.5606 ETH
   ├─ unihybrid_output: 3.5805 ETH
   └─ savings: $55.93

4. _calculate_fee_value():
   ├─ savings: $55.93
   ├─ fee_percentage: 30%
   └─ fee_amount: $16.78

5. _encode_hook_data():
   ├─ Mã hóa: ob_leg, amm_leg, fee
   └─ hook_data: 0x1234567890abcdef...

6. _validate_slippage():
   ├─ min_output: 3.5805 × (1 - 0.01) = 3.5446 ETH
   ├─ actual_output: 3.5805 ETH
   └─ Status: ✅ PASS (lớn hơn min)

Output (JSON Execution Plan):
{
  "router_address": "0x...",
  "orderbook_leg": {
    "input_amount": "9944100000000000000",
    "output_amount": "3560600000000000000",
    "price": 2809.41
  },
  "amm_leg": {
    "input_amount": "55900000000000",
    "output_amount": "19900000000000000",
    "path": [USDT → ETH]
  },
  "hook_data": "0x1234567890abcdef...",
  "max_slippage": "0.01",
  "fee": {
    "percentage": "0.30",
    "usd_value": 16.78
  },
  "savings": {
    "eth_amount": 0.0199,
    "usd_value": 55.93,
    "percentage": 0.39
  },
  "validation": {
    "min_output": "3544600000000000000",
    "actual_output": "3580500000000000000",
    "status": "PASS"
  }
}
```

#### **Lưu Ý**
- ✅ Output là JSON ready cho blockchain
- ✅ Mã hóa hook_data cho smart contract
- ✅ Kiểm tra slippage trước gửi
- ⚠️ Fee 30% trừ từ savings
- ⚠️ Decimal precision rất quan trọng

---

## 🔄 Flow Hoàn Chỉnh: Bước Theo Bước

```
STEP 1: User Initiate
├─ Input: 10,000 USDT → ETH
└─ Target: Swap tốt nhất

STEP 2: Module 1 Fetch Price
├─ Query: Uniswap V3 pool
└─ Output: price = 2808.53 USDT/ETH

STEP 3: Module 2 Create Orderbook
├─ Input: price, quantity
├─ Scenario: Medium (3 levels)
└─ Output: 6 levels (3 bid + 3 ask)

STEP 4: Module 3 Greedy Match
├─ Input: Orderbook, 10,000 USDT
├─ Algorithm: Pick best → fill → repeat
├─ Threshold: 5 bps filter
└─ Output: ob_amount=3.56 ETH, savings=0.39%

STEP 5: Module 4 Build Plan
├─ Input: Match result
├─ Calculate: Legs, fees, hook_data
├─ Validate: Slippage < 1%
└─ Output: JSON execution plan

STEP 6: Execute
├─ Send: Plan to smart contract
├─ Result: Swap executed
└─ Receive: 3.5805 ETH (tốt hơn 0.39%)
```

---

## 📊 Data Flow Diagram

```
User Input
  (10,000 USDT)
      │
      ▼
  Module 1 ─── sqrtPrice ───────────────────────┐
      │                                          │
      │  price = 2808.53 USDT/ETH                │
      │                                          │
      ▼                                          │
  Module 2 ◄─────────────────────────────────────┘
      │
      │  6 levels (3 bid + 3 ask)
      │
      ▼
  Module 3
      │
      │  Match algorithm
      │  ob_output = 3.56 ETH
      │  amm_fallback = 0.0199 ETH
      │
      ▼
  Module 4
      │
      │  Build legs
      │  Encode hook_data
      │  Validate slippage
      │
      ▼
JSON Plan
      │
      ▼
Smart Contract
      │
      ▼
✅ Result: 3.5805 ETH
   (Savings: 0.39% = $55.93)
```

---

## 🎓 Bước Tiếp Theo

Sau khi hiểu flow chung:

1. **03_HƯỚNG_DẪN_TEST.md** - Chạy test để thử
2. **04_MODULE1_CHI_TIẾT.md** - Học chi tiết Module 1
3. **05_MODULE2_CHI_TIẾT.md** - Học chi tiết Module 2
4. **06_MODULE3_CHI_TIẾT.md** - Học chi tiết Module 3
5. **07_MODULE4_CHI_TIẾT.md** - Học chi tiết Module 4

---

## 💡 Ghi Nhớ

✅ **Module 1** lấy giá
✅ **Module 2** tạo orderbook
✅ **Module 3** khớp lệnh (quan trọng nhất!)
✅ **Module 4** tạo execution plan

→ Tất cả kết hợp = **tiết kiệm 0.39%-1.59%**

