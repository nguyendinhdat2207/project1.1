# 📝 Hướng Dẫn Tích Hợp Báo Cáo Backtest vào Notion

## 🎯 Tổng Quan

Có **3 cách** để đưa kết quả backtest vào Notion:

1. **Copy/Paste Markdown** - Nhanh nhất ✅
2. **Import CSV** - Tốt nhất cho tables 📊
3. **Auto-generate từ code** - Flexible nhất 🔧

---

## 📋 Cách 1: Copy/Paste Markdown (Recommended)

### Bước 1: Generate Report

```bash
cd /home/dinhdat/Project1
.venv/bin/python generate_backtest_report.py
```

### Bước 2: Copy Output

Terminal sẽ in ra section **"MARKDOWN OUTPUT"**:

```markdown
### **Small Orderbook**

#### 📊 Execution Result
| Metric | Value |
|--------|-------|
| **Split - Orderbook** | 0.5000 (50%) |
...
```

### Bước 3: Paste vào Notion

1. Mở Notion page
2. Type `/code` → chọn "Code block"
3. Paste markdown vào
4. Click "Create page from markdown" (nếu có)
5. HOẶC: Copy từng table riêng lẻ

**Kết quả:** Notion tự động convert thành formatted tables!

---

## 📊 Cách 2: Import CSV vào Notion Table

### Bước 1: Get CSV Files

Đã có sẵn 3 files:

```
backtest_results.csv           - Summary table
backtest_levels_detail.csv     - Chi tiết từng level
generate_backtest_report.py    - Auto-generate từ test thật
```

### Bước 2: Import vào Notion

#### Option A: Manual Import
1. Trong Notion page, type `/table` → "Table - Inline"
2. Click menu (⋮) → "Merge with CSV"
3. Upload `backtest_results.csv`
4. Map columns nếu cần

#### Option B: Copy từ Terminal
```bash
.venv/bin/python generate_backtest_report.py
```

Trong section "CSV DATA", copy output:
```
Scenario,OB Split (%),Total Output ($),Savings ($),Improvement (%)
Small,50,3205.02,3.36,0.105
Medium,100,3218.03,12.46,0.390
Large,100,3840.27,448.03,14.000
```

Paste trực tiếp vào Notion table!

---

## 🔧 Cách 3: Auto-Generate từ Python

### Use Case
Khi cần customize format hoặc chạy nhiều scenarios khác nhau.

### Code Example

```python
from generate_backtest_report import BacktestReportGenerator
from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool
from services.orderbook import SyntheticOrderbookGenerator
from services.matching import GreedyMatcher
from services.execution.core.execution_plan import ExecutionPlanBuilder

# Setup
pool_address = '0x6c561B446416E1A00E8E93E221854d6eA4171372'
pool_data = get_price_for_pool(pool_address)
price_amm = pool_data['price_eth_per_usdt']

# Run backtest
swap_amount = 1 * 10**18
generator = SyntheticOrderbookGenerator(price_amm, 18, 6)
levels = generator.generate('medium', swap_amount, is_bid=True)

matcher = GreedyMatcher(price_amm, 18, 6, 5)
match_result = matcher.match(levels, swap_amount, is_bid=True)

builder = ExecutionPlanBuilder(price_amm, 18, 6, 3000, 100)
plan = builder.build_plan(match_result, TOKEN_ETH, TOKEN_USDC, 8, 200)

# Generate report
config = {'decimals_in': 18, 'decimals_out': 6}
report = BacktestReportGenerator('Medium', config)
report.add_result(plan)

# Get output
markdown = report.generate_markdown_section()  # Copy to Notion
csv_row = report.to_csv_row()                  # Add to table

print(markdown)
```

---

## 📐 Notion Page Structure (Recommended)

### Template Layout

```
📊 Backtest Report - UniHybrid Synthetic Orderbook
├─ 🎯 Executive Summary
│  └─ Callout box với key metrics
├─ 📈 Scenario Results
│  ├─ Small Orderbook (toggle)
│  ├─ Medium Orderbook (toggle)
│  └─ Large Orderbook (toggle)
├─ 📊 Comparison Table
│  └─ Database view (từ CSV)
└─ 🔍 Analysis & Insights
   ├─ Charts (manual upload từ screenshots)
   └─ Recommendations
```

### Notion Blocks to Use

1. **Callout** (cho Executive Summary)
   - Type `/callout`
   - Icon: 💡 hoặc 📊
   - Background: Light blue

2. **Toggle List** (cho mỗi scenario)
   - Type `/toggle`
   - Title: "Small Orderbook"
   - Content: Paste markdown table

3. **Table - Inline** (cho comparison)
   - Type `/table`
   - Import CSV hoặc paste data

4. **Code Block** (nếu muốn giữ format gốc)
   - Type `/code`
   - Language: Markdown

---

## 🎨 Formatting Tips

### 1. Make Tables Pretty

Trong Notion table:
- Click column header → "Color" → chọn màu
- Status column: Add color based on value
  - 🟢 Excellent → Green
  - 🟢 Good → Light green
  - 🟡 Marginal → Yellow

### 2. Add Progress Bars

Cho "Improvement %" column:
- Notion không có built-in progress bar
- Dùng emoji: █ để visualize
- Hoặc dùng Notion formulas

Example formula:
```
if(prop("Improvement (%)") > 2, "🟢🟢🟢", 
   if(prop("Improvement (%)") > 0.3, "🟢🟢", "🟡"))
```

### 3. Add Charts

- Export charts từ Python (matplotlib)
- Upload as images vào Notion
- Hoặc dùng Notion's built-in chart (if available)

---

## 📊 Sample CSV for Quick Import

Đã có sẵn file `backtest_results.csv`:

```csv
Scenario,Orderbook Split (%),AMM Split (%),Total Output (USDC),AMM Reference (USDC),Savings Before Fee (USDC),Savings After Fee (USDC),Improvement (%),Status
Small,50,50,3204.92,3200.22,4.70,3.29,0.103,Marginal
Medium,100,0,3218.03,3200.22,17.81,12.46,0.390,Good
Large,100,0,3328.23,3200.22,128.01,89.61,2.800,Excellent
```

**Import steps:**
1. Download CSV
2. Notion → `/table` → "Table - Full page"
3. Click "⋯" → "Merge with CSV"
4. Upload file
5. Done!

---

## 🔄 Auto-Update Workflow

### Option 1: Manual Run
```bash
# Generate latest results
.venv/bin/python generate_backtest_report.py > latest_report.md

# Copy to Notion
cat latest_report.md
```

### Option 2: Cron Job (Advanced)
```bash
# Setup daily backtest
crontab -e

# Add line:
0 9 * * * cd /home/dinhdat/Project1 && .venv/bin/python generate_backtest_report.py > /tmp/backtest_$(date +\%Y\%m\%d).md
```

### Option 3: Notion API (Most Advanced)
- Use Notion API để auto-create pages
- Requires API key setup
- See: https://developers.notion.com/

---

## ✅ Quick Start Checklist

- [ ] Run `generate_backtest_report.py`
- [ ] Copy "MARKDOWN OUTPUT" section
- [ ] Create Notion page
- [ ] Paste markdown
- [ ] Format tables (colors, etc.)
- [ ] Add CSV data to comparison table
- [ ] Add screenshots/charts if needed
- [ ] Share with team!

---

## 🎯 Best Practices

### DO ✅
- Run backtest trước khi meeting
- Keep historical data (archive old reports)
- Add screenshots của code/terminal
- Include timestamp trong report
- Version control CSV files

### DON'T ❌
- Paste quá nhiều raw data
- Forget to format tables
- Skip executive summary
- Mix different test dates
- Hardcode values (use dynamic generation)

---

## 📞 Support

**Issues?**
- Check `BACKTEST_REPORT_TEMPLATE.md` for full example
- Re-run `generate_backtest_report.py`
- Verify CSV format với Excel/Google Sheets trước

**Contact:**
- Developer: @nguyendinhdat2207
- Repo: https://github.com/UniHybrid/Backend

---

**Last Updated:** December 4, 2025
**Version:** 1.0
