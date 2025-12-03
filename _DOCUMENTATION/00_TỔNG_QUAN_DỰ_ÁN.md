# 🚀 UniHybrid - Tổng Quan Dự Án

**Ngày cập nhật**: 3 Tháng 12, 2025  
**Phiên bản**: v4.1.0  
**Ngôn ngữ**: Python 3.8+

---

## 📋 Mục Đích Dự Án

**UniHybrid** là một **Hybrid DEX Aggregator** (Bộ gộp sàn giao dịch lai) kết hợp 2 nguồn thanh khoản:

1. **Orderbook Nội Bộ (CLOB)** - Sổ lệnh tập trung trên blockchain
2. **AMM (Uniswap V3)** - Thị trường tự động hoá

### 🎯 Mục Tiêu Chính

> Cho người dùng swap với **giá tốt hơn** so với chỉ dùng Uniswap V3 thuần

### 💡 Cách Hoạt Động (1 câu)

**Fill phần swap ở giá tốt từ Orderbook, phần còn lại fallback sang AMM**

---

## 📊 Ví Dụ Thực Tế

Giả sử người dùng muốn swap **10,000 USDT → ETH**:

| Phương án | Lượng Input | Lượng Output | Giá Trung Bình | Tiết Kiệm |
|-----------|-------------|--------------|----------------|-----------|
| **100% AMM** (baseline) | 10,000 USDT | 3.5606 ETH | 2808.53 USDT/ETH | - |
| **UniHybrid** (OB + AMM) | 10,000 USDT | **3.5805 ETH** | **2794.12 USDT/ETH** | +0.0199 ETH |
| **Tiết kiệm tương đối** | - | - | - | **+0.39%** (~$56) |

### ✅ Kết Quả

- User nhận được **thêm 0.0199 ETH** (~$56 USD)
- Giảm **14.41 USDT/ETH** so với AMM thuần

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                     NGƯỜI DÙNG                              │
│              (Input: 10,000 USDT → ETH)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   MODULE 1: FETCH     │  Lấy giá từ Uniswap V3
         │   PRICES (AMM)        │  Input: Điểm cuối cùng
         │   uniswap_v3.py       │  Output: Giá eth/usdt
         └───────────┬───────────┘
                     │
         ┌───────────▼──────────────────┐
         │   MODULE 2: SYNTHETIC        │  Tạo Orderbook giả
         │   ORDERBOOK GENERATOR        │  3 scenarios khác nhau
         │   synthetic_orderbook.py     │  Output: Các mức giá
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   MODULE 3: GREEDY           │  Khớp lệnh tham lam
         │   MATCHER                    │  Chọn tốt nhất
         │   greedy_matcher.py          │  Output: Kế hoạch khớp
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   MODULE 4: EXECUTION        │  Tạo kế hoạch thực thi
         │   PLAN BUILDER               │  Chuẩn bị cho blockchain
         │   execution_plan.py          │  Output: JSON plan
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │  ✅ KẾT QUẢ CUỐI CÙNG       │
         │  3.5805 ETH (tốt hơn 0.39%) │
         └──────────────────────────────┘
```

---

## 🔑 4 Module Chính

### **Module 1️⃣: Lấy Giá từ AMM**
- **File**: `services/amm_uniswap_v3/uniswap_v3.py`
- **Mục đích**: Lấy giá hiện tại từ pool Uniswap V3
- **Hàm chính**: 
  - `get_slot0()` - Lấy dữ liệu slot0
  - `get_pool_tokens_and_decimals()` - Lấy thông tin token
  - `price_from_sqrtprice()` - Chuyển đổi sqrt(price) → price
  - `get_price_for_pool()` - Lấy giá cuối cùng
- **Input**: Pool address
- **Output**: Giá ETH/USDT (ví dụ: 2808.53 USDT/ETH)

### **Module 2️⃣: Tạo Orderbook Giả**
- **File**: `services/orderbook/synthetic_orderbook.py`
- **Mục đích**: Sinh tạo synthetic orderbook từ giá AMM
- **3 Scenarios**:
  - **Small**: 1 level bid/ask (kiểm tra)
  - **Medium**: 3 levels bid/ask ⭐ khuyến nghị
  - **Large**: 5-10 levels (deep liquidity, kiểu CEX)
- **Công thức**: Ladder pricing + exponential decay
- **Input**: Giá AMM, quantity người dùng
- **Output**: Danh sách các mức giá + lượng ở mỗi mức

### **Module 3️⃣: Khớp Lệnh Tham Lam**
- **File**: `services/matching/greedy_matcher.py`
- **Mục đích**: Khớp lệnh từ orderbook với input của người dùng
- **Thuật toán**: Tham lam (Greedy) - chọn tốt nhất trước
- **Threshold**: 5 bps (basis points) mặc định
- **Input**: Orderbook, số lượng input
- **Output**: Kế hoạch khớp (match result), tiết kiệm

### **Module 4️⃣: Tạo Kế Hoạch Thực Thi**
- **File**: `services/execution/execution_plan.py`
- **Mục đích**: Tạo kế hoạch thực thi cho smart contract
- **6 Helper Methods**:
  - `_simulate_amm_leg()` - Mô phỏng chân AMM
  - `_build_legs()` - Xây dựng chân swap
  - `_calculate_savings()` - Tính tiết kiệm
  - `_calculate_fee_value()` - Tính phí
  - `_encode_hook_data()` - Mã hóa dữ liệu hook
  - `_validate_slippage()` - Kiểm tra slippage
- **Input**: Match result từ Module 3
- **Output**: JSON execution plan (sẵn sàng gửi blockchain)

---

## 🔄 Luồng Hoạt Động Hoàn Chỉnh

```
Bước 1: Người dùng nhập lệnh
├─ Input: 10,000 USDT → ETH
└─ Output: Orderbook yêu cầu

Bước 2: Module 1 lấy giá
├─ Query Uniswap V3 pool
└─ Output: Giá hiện tại 2808.53 USDT/ETH

Bước 3: Module 2 tạo orderbook
├─ Tính giá bid/ask từ giá AMM
├─ Áp dụng ladder pricing
└─ Output: ~5 mức giá bid/ask

Bước 4: Module 3 khớp lệnh
├─ Duyệt orderbook từ tốt nhất
├─ Chọn lệnh cho đến khi fill hết
└─ Output: Kế hoạch khớp + tiết kiệm 0.39%

Bước 5: Module 4 tạo execution plan
├─ Tính toán chân OB + chân AMM
├─ Mã hóa hook data
├─ Kiểm tra slippage
└─ Output: JSON ready để gửi blockchain

Bước 6: Gửi blockchain
├─ Gửi execution plan đến smart contract
└─ Nhận 3.5805 ETH (thay vì 3.5606 ETH)
```

---

## 📈 So Sánh: UniHybrid vs Không Dùng UniHybrid

### Trường Hợp 1: Swap 1,000 USDT

| Tiêu chí | Không UniHybrid | Với UniHybrid | Lợi ích |
|----------|-----------------|---------------|---------|
| Output ETH | 0.356 ETH | 0.358 ETH | +0.002 ETH |
| Giá trung bình | 2808.53 USDT/ETH | 2785.42 USDT/ETH | +23.11 USDT/ETH |
| Tiết kiệm (USD) | - | +$5.60 | 0.56% |

### Trường Hợp 2: Swap 100,000 USDT (Khách lớn)

| Tiêu chí | Không UniHybrid | Với UniHybrid | Lợi ích |
|----------|-----------------|---------------|---------|
| Output ETH | 35.60 ETH | 36.20 ETH | +0.60 ETH |
| Giá trung bình | 2808.53 USDT/ETH | 2763.74 USDT/ETH | +44.79 USDT/ETH |
| Tiết kiệm (USD) | - | +$1,688 | 1.59% |

**📌 Kết luận**: Khách càng lớn → tiết kiệm càng nhiều

---

## 🎨 Các Tính Năng Chính

✅ **4 Modules Độc Lập**
- Mỗi module làm 1 việc tốt
- Dễ test, dễ mở rộng, dễ bảo trì

✅ **3 Scenarios Orderbook**
- Small: kiểm tra nhanh
- Medium: ⭐ khuyến nghị dùng
- Large: deep liquidity kiểu sàn thực

✅ **Thuật Toán Tham Lam**
- Chọn tốt nhất trước
- Đảm bảo max savings

✅ **Bảo Vệ Slippage**
- Default 1% slippage tolerance
- Kiểm tra trước khi gửi blockchain

✅ **Phí 30% Hybrid**
- 70% giá tiết kiệm cho user
- 30% giá tiết kiệm cho UniHybrid
- Ví dụ: tiết kiệm $100 → user được $70, UniHybrid được $30

---

## 🛠️ Công Nghệ Sử Dụng

### **Backend**
- **Python 3.8+** - Ngôn ngữ chính
- **web3.py** - Tương tác blockchain
- **eth_abi** - Mã hóa ABI
- **decimal** - Tính toán chính xác

### **Blockchain**
- **Base Mainnet** - Mạng chính (OP Stack)
- **Uniswap V3** - AMM source
- **Smart Contract** - Execution layer

### **Dữ Liệu**
- **ETH/USDT Pool** - Cặp chính (0.01% fee)
- **Pool Address**: Tuỳ thuộc vào cấu hình

---

## 📁 Cấu Trúc Thư Mục

```
/home/dinhdat/Project1/
│
├─ services/                          ⭐ Core Business Logic
│  ├─ amm_uniswap_v3/
│  │  └─ uniswap_v3.py               → Module 1: Fetch AMM price
│  │
│  ├─ orderbook/
│  │  ├─ __init__.py
│  │  └─ synthetic_orderbook.py      → Module 2: Generate synthetic OB
│  │
│  ├─ matching/
│  │  ├─ __init__.py
│  │  └─ greedy_matcher.py           → Module 3: Greedy matching
│  │
│  └─ execution/
│     ├─ __init__.py
│     ├─ core/                       ✨ NEW: Execution logic
│     │  ├─ __init__.py
│     │  ├─ execution_plan.py        → Module 4: Build execution plan
│     │  ├─ amm_leg.py               → Simulate AMM swap
│     │  ├─ savings_calculator.py    → Calculate savings
│     │  └─ types.py                 ✨ NEW: Type definitions
│     │
│     └─ ui/                         ✨ NEW: Display components
│        ├─ __init__.py
│        └─ virtual_orderbook.py     → Virtual OB + VirtualOrderBook class
│
├─ scripts/                          ✨ NEW: CLI & scripts
│  ├─ __init__.py
│  └─ cli/                           ✨ NEW: Modular CLI
│     ├─ __init__.py
│     ├─ menu.py                     → OrderbookCLIMenu (300 lines, 14 methods)
│     ├─ display.py                  → Display formatting (180 lines)
│     └─ utils.py                    → Helper functions (160 lines, 13 functions)
│
├─ display/                          ✨ NEW: Reusable display formatters
│  ├─ __init__.py
│  ├─ base.py                        → Abstract OrderbookDisplayFormatter (270+ lines, 20+ methods)
│  ├─ cli_display.py                 → CLI implementation (150+ lines)
│  └─ table_display.py               → Table implementation (180+ lines)
│
├─ abi/                              ⭐ Smart Contract ABI
│  ├─ erc20_min.json                 → ERC20 interface
│  ├─ erc20_min.json                 → ERC20 interface
│  └─ uniswap_v3_pool.json           → Pool interface
│
├─ requirements_amm.txt              ⭐ Dependencies
│
├─ orderbook_cli.py                  ⭐ Entry point for interactive CLI
├─ orderbook_table_display.py        ⭐ Entry point for table display
│
├─ test_*.py                         ⭐ Test files (5 files, 1,193 lines)
│  ├─ test_integration_full.py       → Module 1+2+3 integration (206 lines)
│  ├─ test_integration_modules.py    → Module 1+2 integration (118 lines)
│  ├─ test_integration_virtual_orderbook.py → Virtual OB integration (331 lines)
│  ├─ test_module4_execution_plan.py → Full pipeline test (286 lines)
│  └─ test_virtual_orderbook.py      → 3 scenario demo (252 lines)
│
├─ README.md                         ⭐ Quick start guide
├─ CHANGELOG.md                      ⭐ Version history
├─ OPTIMIZATION_GUIDE.md             ✨ NEW: Optimization priorities
├─ PRIORITY_2_COMPLETE.md            ✨ NEW: Priority 2 summary
├─ TEST_ANALYSIS.md                  ✨ NEW: Test analysis & optimization
│
└─ _DOCUMENTATION/                   ⭐ Documentation
   ├─ 00_TỔNG_QUAN_DỰ_ÁN.md        → Bạn đang đọc
   ├─ 01_CẤU_HÌnH_MÔI_TRƯỜNG.md
   ├─ 02_TỔNG_QUAN_CÁC_MODULE.md
   ├─ 03_HƯỚNG_DẪN_TEST.md
   ├─ 04_MODULE1_CHI_TIẾT.md
   ├─ 05_MODULE2_CHI_TIẾT.md
   ├─ 06_MODULE3_CHI_TIẾT.md
   ├─ 07_MODULE4_CHI_TIẾT.md
   └─ CẤU_TRÚC_TÀI_LIỆU.md
```

---

## ✨ Các Tối Ưu Hóa Gần Đây (Priority 1 & 2)

### Priority 1: ✅ COMPLETE
**Refactored CLI từ 466 lines thành modular structure**
- Tách thành `scripts/cli/` với menu.py (300 lines), display.py (180 lines), utils.py (160 lines)
- Giảm entry point `orderbook_cli.py` xuống 15 lines
- **Lợi ích**: Dễ bảo trì, test riêng lẻ, tái sử dụng

### Priority 2: ✅ COMPLETE
**Created DisplayFormatter base class for code reuse**
- Tạo `display/base.py` với 20+ shared methods
- `display/cli_display.py` - CLI formatter
- `display/table_display.py` - Table formatter
- Giảm code duplication 200+ lines
- **Lợi ích**: Dễ thêm format mới (JSON, CSV, WebSocket, etc.)

### Priority 3: ⏳ TODO
**Pytest refactoring - Tối ưu test files**
- Sẽ cập nhật tài liệu TEST_ANALYSIS.md
- Convert test files to pytest format
- Tạo fixtures, parametrization, conftest.py

---

## 🎓 Cách Đọc Tài Liệu

### 👤 Bạn Là Ai?

**❓ Lần đầu tiên tìm hiểu project?**
→ Đọc theo thứ tự:
1. **00_TỔNG_QUAN_DỰ_ÁN.md** (bạn đang đọc) - 15 phút
2. **01_CẤU_HÌnH_MÔI_TRƯỜNG.md** - 10 phút
3. **02_TỔNG_QUAN_CÁC_MODULE.md** - 15 phút
4. **03_HƯỚNG_DẪN_TEST.md** - 5 phút

**⏱️ Tổng: ~45 phút**

**❓ Muốn hiểu chi tiết từng module?**
→ Đọc chi tiết module (30-60 phút mỗi module):
- **04_MODULE1_CHI_TIẾT.md** - Lấy giá
- **05_MODULE2_CHI_TIẾT.md** - Tạo Orderbook
- **06_MODULE3_CHI_TIẾT.md** - Khớp lệnh
- **07_MODULE4_CHI_TIẾT.md** - Execution plan

**❓ Muốn chạy code ngay?**
→ 
1. **01_CẤU_HÌnH_MÔI_TRƯỜNG.md** - Setup
2. **03_HƯỚNG_DẪN_TEST.md** - Chạy test
3. Chọn 1 module để chạy

**❓ Muốn tối ưu code?**
→
1. **OPTIMIZATION_GUIDE.md** - Tổng quan tối ưu (xong Priority 1 & 2)
2. **PRIORITY_2_COMPLETE.md** - Chi tiết Priority 2
3. **TEST_ANALYSIS.md** - Phân tích test (Priority 3)

---

## ❓ Câu Hỏi Thường Gặp

**Q1: Tại sao cần UniHybrid khi đã có Uniswap?**
> A: Vì UniHybrid kết hợp Orderbook + AMM → giá tốt hơn 0.39%-1.59% tùy size swap

**Q2: Orderbook ở đâu?**
> A: Synthetic (giả tạo) - được tạo từ giá AMM + ladder pricing

**Q3: Có rủi ro gì không?**
> A: Có slippage protection (1% default), kiểm tra trước khi gửi blockchain

**Q4: Module nào quan trọng nhất?**
> A: Module 3 (Greedy Matcher) - quyết định tiết kiệm bao nhiêu

**Q5: Có phí không?**
> A: Có - 30% phí hybrid (70% cho user, 30% cho UniHybrid)

---

## 🔗 Liên Kết Tài Liệu

- **01_CẤU_HÌnH_MÔI_TRƯỜNG.md** - Cách setup
- **02_TỔNG_QUAN_CÁC_MODULE.md** - Flow hoàn chỉnh
- **03_HƯỚNG_DẪN_TEST.md** - Cách test
- **04-07_MODULE*_CHI_TIẾT.md** - Chi tiết từng module

---

## 📞 Hỗ Trợ

Nếu có câu hỏi:
1. Xem **CẤU_TRÚC_TÀI_LIỆU.md** - Hướng dẫn đọc
2. Xem tài liệu chi tiết module tương ứng
3. Chạy test để hiểu hoạt động thực tế

---

**✅ Sẵn sàng để bước vào Module 1?**

→ Hãy đọc **01_CẤU_HÌnH_MÔI_TRƯỜNG.md** để setup!
