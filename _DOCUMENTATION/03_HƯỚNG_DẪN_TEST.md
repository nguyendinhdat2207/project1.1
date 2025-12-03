# 🧪 Hướng Dẫn Test

**Ngày cập nhật**: 3 Tháng 12, 2025  
**Thời gian**: ~15 phút để chạy tất cả tests

---

## 📋 Mục Đích

File này hướng dẫn:
- ✅ Các test files có sẵn
- ✅ Cách chạy từng test
- ✅ Kỳ vọng kết quả
- ✅ Cách debug nếu có lỗi

---

## 📁 Test Files Hiện Có

| File | Loại | Lines | Status | Ghi chú |
|------|------|-------|--------|---------|
| `test_integration_full.py` | Integration | 206 | ✅ OK | Module 1+2+3 |
| `test_integration_modules.py` | Integration | 118 | ✅ OK | Module 1+2 |
| `test_integration_virtual_orderbook.py` | Integration | 331 | ⚠️ Needs fix | Virtual OB + Greedy |
| `test_module4_execution_plan.py` | Integration | 286 | ✅ OK | Full pipeline (Module 1-4) |
| `test_virtual_orderbook.py` | Demo | 252 | ✅ OK | 3 scenarios |
| **TOTAL** | - | **1,193** | - | - |

---

## ✨ NEW Structure (Priority 1 & 2 Complete)

**services/execution/** - Reorganized:
- ✅ `core/` - Core logic (execution_plan.py, amm_leg.py, savings_calculator.py, types.py)
- ✅ `ui/` - Display (virtual_orderbook.py)

**scripts/cli/** - NEW Modular CLI:
- ✅ `menu.py` - OrderbookCLIMenu (300 lines)
- ✅ `display.py` - Display formatting (180 lines)
- ✅ `utils.py` - Helper functions (160 lines, 13 functions)

**display/** - NEW Reusable formatters:
- ✅ `base.py` - OrderbookDisplayFormatter (270+ lines, 20+ methods)
- ✅ `cli_display.py` - CLI implementation (150+ lines)
- ✅ `table_display.py` - Table implementation (180+ lines)

---

## ✅ Test 1: Full Pipeline (Module 1-4)

**File**: `test_module4_execution_plan.py` (286 lines)  
**Mục đích**: Complete pipeline test  
**Status**: ✅ All PASS

```bash
python test_module4_execution_plan.py
```

---

## ✅ Test 2: Module 1-3 Integration

**File**: `test_integration_full.py` (206 lines)  
**Mục đích**: AMM → Orderbook → Matching  
**Status**: ✅ All PASS

```bash
python test_integration_full.py
```

---

## ✅ Test 3: Virtual Orderbook Scenarios

**File**: `test_virtual_orderbook.py` (252 lines)  
**Mục đích**: Demo 3 scenarios  
**Status**: ✅ All PASS

```bash
python test_virtual_orderbook.py
```

---

## 🔧 CLI & Display

**Interactive CLI**: `python orderbook_cli.py`  
**Table Display**: `python orderbook_table_display.py`

---

## ✨ Tất Cả 5 Test Files - Status

| File | Lines | Type | Status | Command |
|------|-------|------|--------|---------|
| test_module4_execution_plan.py | 286 | Integration | ✅ OK | `python test_module4_execution_plan.py` |
| test_integration_full.py | 206 | Integration | ✅ OK | `python test_integration_full.py` |
| test_virtual_orderbook.py | 252 | Demo | ✅ OK | `python test_virtual_orderbook.py` |
| test_integration_modules.py | 118 | Integration | ✅ OK | `python test_integration_modules.py` |
| test_integration_virtual_orderbook.py | 331 | Integration | ⚠️ Needs fix | KyberOrder import |

**Tổng: 1,193 lines, 4/5 fully working**

## 💡 Mẹo

- ✅ Test Module 4 là **MUST** (integration test chính)
- ✅ Nếu Module 4 PASS → tất cả modules OK
- ⚠️ Nếu có lỗi → kiểm tra lại .env file
- ⚠️ RPC chậm? → Thử RPC endpoint khác

