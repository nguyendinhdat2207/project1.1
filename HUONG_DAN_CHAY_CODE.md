# Hướng Dẫn Chạy Code

## Yêu Cầu Hệ Thống

- Python 3.12.3 hoặc cao hơn
- pip (Python package manager)
- Git (tùy chọn, để quản lý version)

## Cài Đặt Môi Trường

### 1. Tạo Virtual Environment

```bash
python -m venv .venv
```

### 2. Kích Hoạt Virtual Environment

```bash
source .venv/bin/activate
```

### 3. Cài Đặt Dependencies

```bash
pip install -r requirements_amm.txt
```

Các package chính bao gồm:
- FastAPI: Framework API
- web3: Tương tác với blockchain
- uvicorn: ASGI server
- pytest: Testing framework
- pandas: Xử lý dữ liệu

## Chạy Các Thành Phần

### 1. Chạy API Server

Khởi động FastAPI server để sử dụng các API endpoints:

```bash
.venv/bin/uvicorn api.main:app --reload
```

Server sẽ chạy tại: `http://localhost:8000`

API Documentation (Swagger): `http://localhost:8000/docs`

### 2. Chạy Backtest

Để chạy backtest với synthetic orderbook và tạo báo cáo:

```bash
.venv/bin/python backtest_report.py
```

Script này sẽ:
- Tạo synthetic orderbook từ pool ETH/USDT trên Base
- Chạy 3 kịch bản: shallow, medium, deep orderbook
- Tính toán tiết kiệm chi phí cho từng kịch bản
- Hiển thị kết quả chi tiết

### 3. Chạy CLI Display

Để xem orderbook dạng CLI:

```bash
.venv/bin/python scripts/orderbook_cli.py
```

Hoặc dạng bảng:

```bash
.venv/bin/python scripts/orderbook_table.py
```

### 4. Chạy Test Suite

Chạy tất cả các test:

```bash
.venv/bin/python test_all.py
```

Hoặc chạy test cụ thể:

```bash
# Unit tests
.venv/bin/pytest tests/unit/

# Integration tests
.venv/bin/pytest tests/integration/

# API tests
.venv/bin/pytest tests/api/
```

## Cấu Trúc API Endpoints

### GET `/health`
Kiểm tra trạng thái server

```bash
curl http://localhost:8000/health
```

### POST `/api/v1/synthetic-orderbook`
Tạo synthetic orderbook từ AMM pool

Request body:
```json
{
  "pool_address": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
  "token_in": "0x4200000000000000000000000000000000000006",
  "token_out": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "amount_in": "33000000000000000000",
  "num_levels": 20
}
```

### POST `/api/v1/match`
Thực hiện greedy matching

Request body:
```json
{
  "external_bids": [...],
  "external_asks": [...],
  "amm_pool": {...}
}
```

### POST `/api/v1/execute`
Tạo execution plan

Request body:
```json
{
  "matched_orderbook": {...},
  "trade_amount": 33000000000000000000,
  "is_bid": false
}
```

## Ví Dụ Sử Dụng

### Ví Dụ 1: Tạo Synthetic Orderbook qua API

```bash
curl -X POST http://localhost:8000/api/v1/synthetic-orderbook \
  -H "Content-Type: application/json" \
  -d '{
    "pool_address": "0x6c561B446416E1A00E8E93E221854d6eA4171372",
    "token_in": "0x4200000000000000000000000000000000000006",
    "token_out": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "amount_in": "33000000000000000000",
    "num_levels": 20
  }'
```

### Ví Dụ 2: Chạy Backtest với Kịch Bản Tùy Chỉnh

Chỉnh sửa `backtest_report.py` và thay đổi các tham số:

```python
# Thay đổi số lượng ETH swap
amount_eth = 50  # Thay vì 33

# Thay đổi depth multiplier cho các kịch bản
scenarios = [
    ("Shallow", 0.3),   # Thay vì 0.5
    ("Medium", 5.0),    # Thay vì 2.5
    ("Deep", 200.0),    # Thay vì 100.0
]
```

### Ví Dụ 3: Test Module Riêng Lẻ

```bash
# Test Module 1 (Quoter Integration)
.venv/bin/pytest tests/integration/test_module1_quoter_integration.py -v

# Test Module 2 + 3 (Orderbook + Matching)
.venv/bin/pytest tests/integration/test_modules_m1_m2_m3.py -v

# Test Full Pipeline (4 modules)
.venv/bin/pytest tests/integration/test_4_modules_detailed.py -v
```

## Troubleshooting

### Lỗi: Module không tìm thấy

Đảm bảo bạn đã kích hoạt virtual environment:
```bash
source .venv/bin/activate
```

### Lỗi: Web3 connection failed

Kiểm tra kết nối internet và RPC endpoint. Mặc định sử dụng public RPC của Base network.

### Lỗi: Import error

Cài đặt lại dependencies:
```bash
pip install -r requirements_amm.txt --force-reinstall
```

### API không phản hồi

Kiểm tra port 8000 có bị chiếm dụng không:
```bash
lsof -i :8000
```

Kill process nếu cần:
```bash
kill -9 <PID>
```

## Cấu Trúc Thư Mục

```
Project1/
├── api/                    # FastAPI endpoints
├── services/               # Business logic
│   ├── amm_uniswap_v3/    # Uniswap V3 integration
│   ├── orderbook/         # Synthetic orderbook
│   ├── matching/          # Greedy matching
│   └── execution/         # Execution planning
├── scripts/               # CLI tools
├── tests/                 # Test suites
├── display/               # Display utilities
├── abi/                   # Smart contract ABIs
└── docs/                  # Documentation
```

## Tham Số Backtest Mặc Định

- **Pool**: ETH/USDT trên Base (0x6c561B446416E1A00E8E93E221854d6eA4171372)
- **Swap Amount**: 33 ETH (~$105,434 USD)
- **AMM Price**: ~3,194.98 USDT/ETH
- **Performance Fee**: 30%
- **Max Slippage**: 1%
- **Greedy Threshold**: 5 bps

## Kết Quả Mong Đợi

Khi chạy backtest thành công, bạn sẽ thấy:

```
=== CASE 1: SHALLOW ORDERBOOK ===
Orderbook depth: 0.5x AMM depth
Orderbook fill: 50.00%
Total cost: $105,323.63
AMM reference: $105,434.34
Gross savings: $110.71 (11 bps)
Net savings (after 30% fee): $77.50

=== CASE 2: MEDIUM ORDERBOOK ===
Orderbook depth: 2.5x AMM depth
Orderbook fill: 100.00%
Total cost: $105,023.67
AMM reference: $105,434.34
Gross savings: $410.67 (39 bps)
Net savings (after 30% fee): $287.47

=== CASE 3: LARGE ORDERBOOK ===
Orderbook depth: 100.0x AMM depth
Orderbook fill: 100.00%
Total cost: $90,673.52
AMM reference: $105,434.34
Gross savings: $14,760.82 (1400 bps)
Net savings (after 30% fee): $10,332.57
```

## Tài Liệu Tham Khảo

- [Tổng Quan Dự Án](_DOCUMENTATION/00_TỔNG_QUAN_DỰ_ÁN.md)
- [Cấu Hình Môi Trường](_DOCUMENTATION/01_CẤU_HÌnH_MÔI_TRƯỜNG.md)
- [Hướng Dẫn Test](_DOCUMENTATION/03_HƯỚNG_DẪN_TEST.md)
- [Báo Cáo Backtest](BAO_CAO_BACKTEST_SYNTHETIC_ORDERBOOK.md)
- [API Documentation](http://localhost:8000/docs) (khi server đang chạy)

## Liên Hệ & Hỗ Trợ

Nếu gặp vấn đề, vui lòng kiểm tra:
1. Log files trong terminal
2. API documentation tại `/docs`
3. Test results từ `test_all.py`
4. Các file báo cáo trong thư mục gốc
