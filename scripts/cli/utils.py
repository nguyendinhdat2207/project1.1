import os
from decimal import Decimal


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def format_currency(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def format_amount(value: float, decimals: int = 6, unit: str = "") -> str:
    formatted = f"{value:.{decimals}f}"
    return f"{formatted} {unit}".strip()


def format_price(value: float) -> str:
    return f"${format_currency(value, 2)}"


def format_percentage(value: float, decimals: int = 4) -> str:
    return f"{value * 100:.{decimals}f}%"


def format_bps(value: float) -> str:
    return f"{value:.2f} bps ({format_percentage(value/10000)})"


def print_header(title: str, width: int = 80):
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width + "\n")


def print_section(title: str, width: int = 80):
    print("\n" + title)
    print("─"*width)


def print_divider(width: int = 80):
    print("─"*width)


def print_footer(width: int = 80):
    print("="*width + "\n")


def create_bar_chart(value: float, max_value: float, width: int = 30, char: str = "█") -> str:
    if max_value == 0:
        return ""
    filled = min(int((value / max_value) * width), width)
    return char * filled


def format_table_row(columns: list, widths: list, separator: str = " | ") -> str:
    formatted_cols = []
    for col, width in zip(columns, widths):
        formatted_cols.append(f"{str(col):>{width}}")
    return separator.join(formatted_cols)


def get_spread_color(spread_bps: float) -> str:
    if spread_bps < 10:
        return "🟢"
    elif spread_bps < 50:
        return "🟡"
    else:
        return "🔴"
