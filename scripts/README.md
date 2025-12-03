# 🚀 Scripts & Entry Points

Thư mục chứa các entry points và CLI implementation.

## 📂 Structure

```
scripts/
├── orderbook_cli.py          # Interactive CLI entry point
├── orderbook_table.py        # Table display entry point
└── cli/                      # CLI implementation modules
    ├── __init__.py          # Exports
    ├── menu.py              # OrderbookCLIMenu class
    ├── display.py           # Display formatting logic
    └── utils.py             # Helper functions
```

## 🎯 Entry Points

### 1. Interactive CLI (`orderbook_cli.py`)
Interactive terminal interface với menu và real-time updates.

**Chạy:**
```bash
python scripts/orderbook_cli.py
```

**Features:**
- Interactive menu
- Change parameters (swap amount, scenario, etc.)
- Real-time orderbook updates
- Multiple display formats

### 2. Table Display (`orderbook_table.py`)
Hiển thị orderbook dưới dạng bảng tương tự Kyberswap/1inch.

**Chạy:**
```bash
python scripts/orderbook_table.py
```

**Features:**
- Clean table format
- Bid/Ask levels
- Price spread calculation
- Multiple scenarios (small/medium/large)

## 🛠️ CLI Implementation (`cli/`)

### `menu.py`
- `OrderbookCLIMenu` class (300 lines)
- 14 methods for menu handling
- Parameter input/validation
- Display coordination

### `display.py`
- Display formatting logic (180 lines)
- Table rendering
- Color/styling helpers
- Output formatting

### `utils.py`
- 13 helper functions (160 lines)
- Input validation
- Number formatting
- Utility functions

## 📝 Usage Examples

### Quick Start
```python
from scripts.cli import OrderbookCLIMenu

cli = OrderbookCLIMenu()
cli.run()
```

### Programmatic Use
```python
from scripts.cli.utils import validate_swap_amount, format_price
from scripts.cli.display import print_orderbook_table

# Use helper functions
amount = validate_swap_amount("1.5")
price = format_price(2700.50)
```

## 🔗 Related

- Display formatters: `../display/`
- Core services: `../services/`
- Tests: `../tests/`
