# UniHybrid Test Suite

Cấu trúc test được tổ chức theo pytest best practices.

## Cấu trúc

```
tests/
├── conftest.py                          # Pytest configuration (auto path setup)
├── integration/                         # Integration tests (multiple modules)
│   ├── test_full_pipeline.py           # M1+M2+M3+M4 (Full pipeline with assertions)
│   └── test_modules_m1_m2_m3.py        # M1+M2+M3 (AMM → Orderbook → Matching)
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

### Integration Tests

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
