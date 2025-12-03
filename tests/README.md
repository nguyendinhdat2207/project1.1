# UniHybrid Test Suite

Cấu trúc test được tổ chức theo pytest best practices.

## Cấu trúc

```
tests/
├── conftest.py                          # Pytest configuration (auto path setup)
├── api/                                 # API endpoint tests
│   ├── README.md                        # API tests documentation
│   ├── test_api_client.py              # Python client test for FastAPI
│   └── test_api.sh                      # Bash script test for API endpoints
├── integration/                         # Integration tests (multiple modules)
│   ├── test_full_pipeline.py           # M1+M2+M3+M4 (Full pipeline with assertions)
│   ├── test_modules_m1_m2_m3.py        # M1+M2+M3 (AMM → Orderbook → Matching)
│   ├── test_module1_quoter_integration.py  # M1 Quoter V2 + M2+M3+M4
│   └── test_4_modules_detailed.py      # Detailed test for all 4 modules + API
└── unit/                                # Unit tests (single components)
    └── test_virtual_orderbook.py       # VirtualOrderBook (3 scenarios: Small/Medium/Large)
```

## Chạy Tests

### Chạy tất cả tests
```bash
pytest tests/ -v
```

### Chạy chỉ integration tests
```bash
pytest tests/integration/ -v
```

### Chạy chỉ unit tests
```bash
pytest tests/unit/ -v
```

### Chạy 1 file cụ thể
```bash
pytest tests/integration/test_full_pipeline.py -v
```

### Chạy với output chi tiết
```bash
pytest tests/ -v -s
```

## Mô tả Tests

### API Tests

#### `test_api_client.py`
- **Endpoint**: GET /api/unihybrid/execution-plan
- **Framework**: Python requests
- **Tests**:
  1. Health check (GET /health)
  2. Root endpoint (GET /)
  3. Execution plan (GET /api/unihybrid/execution-plan)
- **Validates**: All 36 response fields
- **Output**: Detailed savings, split, hook data
- **Status**: ✅ PASSED - Production ready

#### `test_api.sh`
- **Endpoint**: GET /api/unihybrid/execution-plan
- **Framework**: Bash + curl
- **Tests**: Same as test_api_client.py
- **Output**: JSON response
- **Status**: ✅ PASSED

**Requirements:**
- API server running: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- Run: `python tests/api/test_api_client.py` or `./tests/api/test_api.sh`

### Integration Tests

#### `test_4_modules_detailed.py` ⭐ **COMPREHENSIVE TEST**
- **Modules**: M1 + M2 + M3 + M4 + API
- **Coverage**: All 5 components
- **Tests**:
  1. Module 1: AMM Quoter V2 (4 sub-tests)
  2. Module 2: Synthetic Orderbook (3 scenarios)
  3. Module 3: Greedy Matching (3 swap sizes)
  4. Module 4: Execution Plan Builder
  5. API Integration (compare direct vs API)
- **Output**: Detailed analysis of each module
- **Status**: ✅ ALL PASSED (5/5)
- **Run**: `python tests/integration/test_4_modules_detailed.py`

#### `test_module1_quoter_integration.py`
- **Modules**: M1 (Quoter V2) + M2 + M3 + M4
- **Focus**: Quoter V2 integration with full pipeline
- **Tests**:
  - Real on-chain quote from Quoter V2
  - Synthetic orderbook generation
  - Greedy matching with real AMM price
  - Execution plan with savings calculation
- **Results**: 
  - AMM: 3,085.03 USDC
  - UniHybrid: 3,116.84 USDC
  - Savings: +12.07 USDC after fee
- **Status**: ✅ PASSED
- **Run**: `python tests/integration/test_module1_quoter_integration.py`

#### `test_full_pipeline.py`
- **Modules**: M1 + M2 + M3 + M4
- **Flow**: 
  1. Fetch AMM price (Uniswap V3)
  2. Generate synthetic orderbook
  3. Greedy matching
  4. Build execution plan (JSON response)
- **Scenarios**: Small, Medium, Large
- **Có assertions**: ✅ Yes

#### `test_modules_m1_m2_m3.py`
- **Modules**: M1 + M2 + M3
- **Flow**: AMM → Orderbook → Greedy Matching
- **Purpose**: Demo cách các module kết nối với nhau
- **Có assertions**: ❌ No (demo only)

### Unit Tests

#### `test_virtual_orderbook.py`
- **Component**: VirtualOrderBook
- **Test cases**: 3 scenarios (Small, Medium, Large)
- **Purpose**: Test virtual orderbook generation logic
- **Có assertions**: ❌ No (demo only)

## Lưu ý

- File `conftest.py` tự động thêm project root vào `sys.path`
- Không cần `sys.path.insert()` trong các file test
- Import trực tiếp: `from services.xxx import yyy`
