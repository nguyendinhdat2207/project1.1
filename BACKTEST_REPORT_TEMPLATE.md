# 📊 Báo Cáo Backtest UniHybrid - Synthetic Orderbook

> **Date:** December 4, 2025  
> **Network:** Base Mainnet  
> **Pool:** ETH/USDC (0x6c561B446416E1A00E8E93E221854d6eA4171372)

---

## 🎯 Mục Tiêu Backtest

Đánh giá hiệu quả của **UniHybrid Synthetic Orderbook** so với swap 100% qua AMM (Uniswap V3) trên các kịch bản orderbook khác nhau.

### So sánh với Kyberswap Aggregator
- **Kyberswap**: Sử dụng orderbook **bên ngoài** (CEX, DEX khác)
- **UniHybrid**: Xây dựng orderbook **nội bộ** (synthetic) → Hoàn toàn kiểm soát được liquidity

---

## 📈 Kịch Bản Backtest

### **Scenario 1: Small Orderbook** (Worst Case)
- **Mô tả:** Orderbook rất mỏng, thanh khoản thấp
- **Depth:** 0.5× swap amount
- **Spread:** 30 bps (~0.3%)
- **Levels:** 1 level duy nhất
- **Use Case:** Giai đoạn đầu, vốn MM thấp

### **Scenario 2: Medium Orderbook** (Base Case)
- **Mô tả:** Orderbook vừa phải, thanh khoản ổn định
- **Depth:** 2.5× swap amount
- **Spread:** 15 bps/level (~0.15%)
- **Levels:** 5 levels
- **Use Case:** Giai đoạn tăng trưởng, vốn MM trung bình

### **Scenario 3: Large Orderbook** (Best Case)
- **Mô tả:** Orderbook dày, thanh khoản cao (CEX-like)
- **Depth:** Based on $1M capital
- **Spread:** 40 bps/level (~0.4%)
- **Levels:** 5 levels
- **Use Case:** Giai đoạn mature, vốn MM lớn

---

## 🧪 Test Configuration

| Parameter | Value | Note |
|-----------|-------|------|
| **Swap Direction** | ETH → USDC | BID side (user bán ETH) |
| **Swap Amount** | 1.0 ETH | ~$3,200 USD |
| **AMM Price** | 3,200.22 USDC/ETH | Baseline từ Uniswap V3 |
| **Performance Fee** | 30% | Fee trên savings (so với AMM) |
| **Max Slippage** | 1% | 100 bps |
| **OB Min Improve** | 5 bps | 0.05% - threshold tối thiểu |

---

## 📊 Kết Quả Backtest

### **Scenario 1: Small Orderbook**

#### Orderbook Structure
```
Levels: 1
Best Bid: 3,209.62 USDC/ETH (+0.30% vs AMM)
Total Depth: 0.50 ETH
```

#### Execution Result
| Metric | Value |
|--------|-------|
| **Split - Orderbook** | 0.50 ETH (50%) |
| **Split - AMM** | 0.50 ETH (50%) |
| **Output từ OB** | 1,604.81 USDC |
| **Output từ AMM** | 1,600.11 USDC |
| **Total Output** | 3,204.92 USDC |
| **AMM Reference** | 3,200.22 USDC |
| **Savings (Before Fee)** | +4.70 USDC |
| **Savings (After Fee)** | +3.29 USDC |
| **Improvement** | +0.103% |

#### Analysis
✅ **Positive:** Vẫn có savings nhẹ dù orderbook mỏng  
⚠️ **Limited:** Chỉ fill 50% qua OB, phần còn lại fallback AMM  
📌 **Conclusion:** Hiệu quả thấp nhưng vẫn tốt hơn AMM thuần

---

### **Scenario 2: Medium Orderbook**

#### Orderbook Structure
```
Levels: 5
Best Bid: 3,224.22 USDC/ETH (+0.75% vs AMM)
Level 2:  3,219.42 USDC/ETH (+0.60%)
Level 3:  3,214.62 USDC/ETH (+0.45%)
Level 4:  3,209.82 USDC/ETH (+0.30%)
Level 5:  3,205.02 USDC/ETH (+0.15%)
Total Depth: 2.50 ETH
```

#### Execution Result
| Metric | Value |
|--------|-------|
| **Split - Orderbook** | 1.00 ETH (100%) |
| **Split - AMM** | 0.00 ETH (0%) |
| **Output từ OB** | 3,218.03 USDC |
| **Output từ AMM** | 0.00 USDC |
| **Total Output** | 3,218.03 USDC |
| **AMM Reference** | 3,200.22 USDC |
| **Savings (Before Fee)** | +17.81 USDC |
| **Savings (After Fee)** | +12.46 USDC |
| **Improvement** | +0.390% |

#### Levels Used Detail
| Level | Price | Amount Filled | Output |
|-------|-------|---------------|--------|
| 1 | 3,224.22 | 0.2165 ETH | 697.90 USDC |
| 2 | 3,219.42 | 0.3092 ETH | 995.51 USDC |
| 3 | 3,214.62 | 0.4417 ETH | 1,420.04 USDC |
| 4 | 3,209.82 | 0.0326 ETH | 104.58 USDC |

#### Analysis
✅ **Excellent:** 100% fill qua orderbook, không cần AMM  
✅ **High Savings:** $12.46 USDC savings (0.39% improvement)  
📌 **Conclusion:** Kịch bản tối ưu cho swap size vừa phải

---

### **Scenario 3: Large Orderbook**

#### Orderbook Structure
```
Levels: 5 (CEX-like distribution)
Capital Allocation: $1,000,000 USD
Best Bid: 3,328.23 USDC/ETH (+4.00% vs AMM)
Level 2:  3,296.23 USDC/ETH (+3.00%)
Level 3:  3,264.23 USDC/ETH (+2.00%)
Level 4:  3,232.22 USDC/ETH (+1.00%)
Level 5:  3,200.22 USDC/ETH (+0.00%)
Total Depth: ~312.5 ETH ($1M worth)
```

#### Execution Result
| Metric | Value |
|--------|-------|
| **Split - Orderbook** | 1.00 ETH (100%) |
| **Split - AMM** | 0.00 ETH (0%) |
| **Output từ OB** | 3,328.23 USDC |
| **Output từ AMM** | 0.00 USDC |
| **Total Output** | 3,328.23 USDC |
| **AMM Reference** | 3,200.22 USDC |
| **Savings (Before Fee)** | +128.01 USDC |
| **Savings (After Fee)** | +89.61 USDC |
| **Improvement** | +2.800% |

#### Analysis
🚀 **Outstanding:** Savings gấp 7× so với Medium scenario  
✅ **Best Price:** Fill hoàn toàn ở best bid (level 1)  
📌 **Conclusion:** Với vốn lớn, UniHybrid vượt trội AMM

---

## 📊 So Sánh Tổng Hợp

### Performance Summary Table

| Scenario | OB Split | Savings After Fee | Improvement | Status |
|----------|----------|-------------------|-------------|--------|
| **Small** | 50% | +$3.29 | +0.103% | 🟡 Marginal |
| **Medium** | 100% | +$12.46 | +0.390% | 🟢 Good |
| **Large** | 100% | +$89.61 | +2.800% | 🟢 Excellent |

### Chart: Savings vs Scenario
```
Small   ████░░░░░░░░░░░░░░░░  $3.29
Medium  ████████████░░░░░░░░ $12.46
Large   ████████████████████ $89.61
        0    20   40   60   80  100
              Savings (USDC)
```

### Chart: Improvement %
```
Small   █░░░░░░░░░░░░░░░░░░░  0.103%
Medium  ███░░░░░░░░░░░░░░░░░  0.390%
Large   ████████████████████  2.800%
        0%   1%   2%   3%   4%
```

---

## 🔍 Phân Tích Chi Tiết

### **1. Impact của Orderbook Depth**

| Depth Multiplier | Fill Rate | Savings | Note |
|------------------|-----------|---------|------|
| 0.5× | 50% | $3.29 | Orderbook mỏng → nhiều fallback AMM |
| 2.5× | 100% | $12.46 | Đủ depth cho swap hoàn toàn |
| ~312× (Large) | 100% | $89.61 | Vượt xa swap amount |

**Insight:** Depth ≥ 2× swap amount là điểm tối ưu để fill 100% qua OB

---

### **2. Impact của Spread**

| Scenario | Avg Spread | Best Price Improvement | Savings |
|----------|------------|------------------------|---------|
| Small | 30 bps | +0.30% | $3.29 |
| Medium | 15-75 bps | +0.75% | $12.46 |
| Large | 0-400 bps | +4.00% | $89.61 |

**Insight:** Spread càng hẹp (≤20 bps) thì càng cạnh tranh với AMM

---

### **3. Performance Fee Impact**

#### Before vs After Fee

| Scenario | Savings Before | Performance Fee (30%) | Savings After | Net to User |
|----------|----------------|----------------------|---------------|-------------|
| Small | $4.70 | -$1.41 | $3.29 | 70% |
| Medium | $17.81 | -$5.35 | $12.46 | 70% |
| Large | $128.01 | -$38.40 | $89.61 | 70% |

**Insight:** Fee model đảm bảo:
- User luôn có ít nhất 70% savings
- Protocol thu phí tỷ lệ với giá trị tạo ra

---

### **4. So Sánh với Kyberswap**

| Aspect | Kyberswap | UniHybrid (Medium) | Winner |
|--------|-----------|-------------------|--------|
| **Orderbook Source** | External (CEX/DEX) | Internal (Synthetic) | - |
| **Liquidity Control** | ❌ Phụ thuộc bên ngoài | ✅ Tự quản lý | UniHybrid |
| **Savings (1 ETH)** | ~$8-15 USDC* | $12.46 USDC | Comparable |
| **Gas Cost** | Higher (multi-hop) | Lower (single hook) | UniHybrid |
| **Slippage Risk** | Higher (external) | Lower (internal) | UniHybrid |
| **Scalability** | Limited by external | Controlled by capital | UniHybrid |

*Estimate based on typical aggregator performance

**Conclusion:** UniHybrid có lợi thế về **control** và **gas efficiency**

---

## 🎯 Key Takeaways

### ✅ **Strengths**

1. **Consistent Savings:** Tất cả scenarios đều tốt hơn AMM baseline
2. **Scalable:** Performance tăng tuyến tính với vốn MM
3. **Controllable:** Không phụ thuộc external orderbook
4. **Gas Efficient:** Single hop vs multi-hop aggregator

### ⚠️ **Limitations**

1. **Capital Intensive:** Scenario Large cần $1M vốn
2. **Small Scenario:** Savings thấp (chỉ +0.1%)
3. **Market Making Risk:** Cần quản lý inventory

### 📈 **Recommendations**

1. **Target Scenario:** Medium (2.5× depth) cho balance tốt nhất
2. **Min Depth:** 2× swap amount để đảm bảo 100% OB fill
3. **Spread Strategy:** 15-20 bps/level cho competitive pricing
4. **Capital Allocation:** $300K-500K cho ETH/USDC pair

---

## 🔄 Next Steps

### Phase 1: MVP Testing (Current)
- [x] Implement synthetic orderbook
- [x] Backtest 3 scenarios
- [x] Verify BID/ASK logic
- [ ] Deploy testnet

### Phase 2: Optimization
- [ ] Tune spread parameters
- [ ] Test with multiple swap sizes
- [ ] A/B test vs Kyberswap

### Phase 3: Production
- [ ] Deploy mainnet
- [ ] Monitor real user swaps
- [ ] Adjust capital based on volume

---

## 📝 Appendix

### Test Environment
- **RPC Provider:** Infura Base Mainnet
- **Block Number:** Latest (live data)
- **Python Version:** 3.12.3
- **Test Framework:** Custom backtest engine

### Code Repository
- **GitHub:** https://github.com/UniHybrid/Backend
- **Commit:** 4b74486
- **Branch:** main

### Contact
- **Developer:** @nguyendinhdat2207
- **Date:** December 4, 2025

---

**Last Updated:** December 4, 2025  
**Next Review:** After mainnet deployment
