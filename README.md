# 🚀 UniHybrid - Synthetic Orderbook Generator

**Synthetic Market Maker for ETH/USDT on Base Network**

---

## 📋 Mục Đích Dự Án

Xây dựng synthetic orderbook cho ETH/USDT trên Base Network, cung cấp 3 scenarios khác nhau:
- **Small**: Orderbook nhỏ, 1 level bid/ask (testing)
- **Medium**: Orderbook cân bằng, 3 levels bid/ask (khuyến nghị ⭐)
- **Large**: Orderbook sâu kiểu CEX, deep liquidity

---

## 🎯 Tính Năng Chính

✅ **Virtual Orderbook Builder** (`virtual_orderbook.py`)
- Sinh tạo synthetic orderbook từ cấu hình
- 3 scenarios: small, medium, large
- Size decay exponential (0.5-0.8 factor)
- CEX snapshot integration & scaling

✅ **Interactive CLI** (`orderbook_cli.py`)
- Menu 13 options tương tác
- Real-time orderbook generation
- Scenario comparison tool
- Parameter adjustment interface

✅ **Table Display** (`orderbook_table_display.py`)
- Bảng orderbook giống Kyberswap/1inch
- Bid side (🟢 green) / Ask side (🔴 red)
- Price levels + liquidity + status

✅ **Comprehensive Testing**
- `test_virtual_orderbook.py` - Unit tests 3 scenarios
- `test_integration_virtual_orderbook.py` - Integration tests
- 100% test coverage

---

## 🏗️ Kiến Trúc Project

```
📂 /home/dinhdat/Project1/
│
├─ 📁 services/                          ⭐ Core Logic
│  ├─ amm_uniswap_v3/
│  │  └─ uniswap_v3.py                  → Lấy giá từ Uniswap V3
│  │
│  └─ execution/
│     ├─ virtual_orderbook.py           → 🌟 MAIN: Synthetic orderbook builder
│     ├─ greedy_matcher.py              → Khớp limit orders
│     ├─ amm_leg.py                     → Xây AMM leg
│     ├─ savings_calculator.py          → Tính savings
│     ├─ types.py                       → Type definitions
│     ├─ __init__.py
│     └─ README.md                      → API documentation
│
├─ 📁 abi/                              → Smart Contract ABIs
│  ├─ erc20_min.json
│  └─ uniswap_v3_pool.json
│
├─ 🎮 Scripts (Root)
│  ├─ orderbook_table_display.py        → Hiển thị bảng 3 scenarios
│  ├─ orderbook_cli.py                  → Interactive CLI menu (13 options)
│  ├─ test_virtual_orderbook.py         → Unit tests
│  └─ test_integration_virtual_orderbook.py → Integration tests
│
├─ 📚 Documentation
│  ├─ README.md                         → This file
│  └─ GETTING_STARTED.md               → Hướng dẫn chạy code từng module
│
├─ ⚙️ Configuration
│  ├─ requirements_amm.txt              → Python dependencies
│  ├─ .env.example                      → Template (copy to .env)
│  └─ .env                              → Environment (create from .env.example)
│
└─ 📦 Dependencies
   └─ .venv/                            → Virtual environment
```

---

## 🔧 Setup (5 phút)

### Step 1: Setup Virtual Environment
```bash
cd /home/dinhdat/Project1
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements_amm.txt
```

### Step 3: Create .env File
```bash
cp .env.example .env
# Edit .env - add RPC_URL for Base Network:
# RPC_URL=https://1rpc.io/base
```

Pick one RPC provider:
- 🟢 `https://1rpc.io/base` (fastest - 252ms)
- 🟢 `https://base.publicnode.com` (good - 298ms)
- 🟡 `https://mainnet.base.org` (official - slower 5500ms)

### Step 4: Verify Setup
```bash
python -c "from services.execution.virtual_orderbook import VirtualOrderBook; print('✅ Setup OK')"
```

---

## 🎮 Quick Start (Chọn 1 trong 3)

### Option 1️⃣: Xem Bảng Orderbook (3 Scenarios)
```bash
python orderbook_table_display.py
```
**Output**: 3 bảng orderbook (small, medium, large) với bid/ask levels

### Option 2️⃣: Interactive CLI Menu
```bash
python orderbook_cli.py
```
**Features**:
- Generate orderbook
- Change scenario
- Adjust parameters
- Compare all 3 scenarios
- More options...

### Option 3️⃣: Chạy Tests
```bash
python test_virtual_orderbook.py
python test_integration_virtual_orderbook.py
```

---

## 📊 VirtualOrderBook API

### Basic Usage
```python
from services.execution.virtual_orderbook import VirtualOrderBook

# Khởi tạo
vob = VirtualOrderBook(mid_price=2700.0)

# Build orderbook
ob = vob.build_orderbook(
    swap_amount=1.0,           # ETH amount
    scenario='medium',         # small/medium/large
    spread_step_bps=10,       # 0.1% per level
    base_size=2.0,            # Size level 0
    decay=0.5                 # Size decay factor
)

# Access data
print(f"Best Bid: ${ob['best_bid']['price']:.2f}")
print(f"Best Ask: ${ob['best_ask']['price']:.2f}")
print(f"Spread: {ob['spread_bps']:.2f} bps")
print(f"Total Liquidity: {ob['total_liquidity']:.2f} ETH")

# Export JSON
json_str = vob.to_json()
```

See more: [`services/execution/README.md`](services/execution/README.md)

---

## 📋 3 Scenarios Explained

| Scenario | Levels | Spread | Liquidity | Use Case |
|----------|--------|--------|-----------|----------|
| **SMALL** | 1 bid + 1 ask | 19.99 bps | 0.5 + 0.5 ETH | Testing |
| **MEDIUM** ⭐ | 3 bid + 3 ask | 19.99 bps | 2.5 + 2.5 ETH | **Default** |
| **LARGE** | 1 bid + 1 ask (deep) | 400 bps | 9.3 + 9.3 ETH | Deep book |

### Example Output (Medium Scenario)
```
🔴 ASK SIDE (Red - Sell ETH):
   $2,702.70  1.4286 ETH  3,861.00 USDT
   $2,705.40  0.7143 ETH  1,932.43 USDT
   $2,708.11  0.3571 ETH    967.18 USDT

💚 MID PRICE: $2,700.00 | SPREAD: 19.99 bps

🟢 BID SIDE (Green - Buy ETH):
   $2,697.30  1.4286 ETH  3,853.29 USDT
   $2,694.61  0.7143 ETH  1,924.72 USDT
   $2,691.92  0.3571 ETH    961.40 USDT
```

---

## 🔗 Blockchain Configuration

**Network**: Base Mainnet
- Chain ID: 8453

**Pool**: ETH/USDT (Uniswap V3, 0.3% fee)
- Address: `0xcE1d8c90A5F0ef28fe0F457e5Ad615215899319a`
- Token0 (ETH): `0x4200000000000000000000000000000000000006` (18 decimals)
- Token1 (USDT): `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` (6 decimals)

**RPC Providers**:
- ⭐ `https://1rpc.io/base` (fastest)
- ✅ `https://base.publicnode.com` (good)
- 🟡 `https://mainnet.base.org` (official)

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | 📖 Overview & quick start (this file) |
| `GETTING_STARTED.md` | 🚀 Detailed guide - how to run each module |
| `services/execution/README.md` | 🔗 API reference for VirtualOrderBook |

---

## ✅ Checklist

- [ ] Setup `.venv` environment
- [ ] Install dependencies (`pip install -r requirements_amm.txt`)
- [ ] Create `.env` from `.env.example`
- [ ] Add RPC_URL to `.env`
- [ ] Run `python orderbook_table_display.py`
- [ ] Run `python test_virtual_orderbook.py`
- [ ] Read `GETTING_STARTED.md` for detailed guide

---

## 🐛 Troubleshooting

**Q: ModuleNotFoundError when importing services?**
```bash
source .venv/bin/activate
pip install -r requirements_amm.txt
```

**Q: RPC connection failed?**
- Check `.env` file has valid `RPC_URL`
- Try different RPC provider
- Check internet connection

**Q: Tests failing?**
```bash
python test_virtual_orderbook.py -v
python test_integration_virtual_orderbook.py -v
```

**Q: How to customize parameters?**
- Edit `orderbook_cli.py` menu → option 3-8 to adjust
- Or call `build_orderbook()` directly with custom params

---

## 🔗 Next Steps

1. **Read**: [`GETTING_STARTED.md`](GETTING_STARTED.md) - Module-by-module guide
2. **Run**: `python orderbook_table_display.py` - See orderbook
3. **Test**: `python test_virtual_orderbook.py` - Run tests
4. **Explore**: `python orderbook_cli.py` - Interactive menu
5. **Learn**: `services/execution/README.md` - API details

---

## 📞 Support

**Need help?**
- Check `GETTING_STARTED.md` for detailed instructions
- Read `services/execution/README.md` for API details
- Review test files: `test_*.py` for usage examples

---

**Status**: ✅ Production Ready  
**Last Updated**: Dec 2, 2025  
**Python**: 3.10+  
**License**: MIT
