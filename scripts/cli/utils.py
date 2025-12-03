"""
CLI Utilities - Helper functions for orderbook CLI

Provides:
- Terminal clearing
- Table formatting
- Number formatting
"""

import os
from decimal import Decimal


def clear_screen():
    """Clear terminal screen (cross-platform)"""
    os.system('clear' if os.name == 'posix' else 'cls')


def format_currency(value: float, decimals: int = 2) -> str:
    """Format number as currency with separators
    
    Args:
        value: Number to format
        decimals: Decimal places
        
    Returns:
        Formatted string with commas
    """
    return f"{value:,.{decimals}f}"


def format_amount(value: float, decimals: int = 6, unit: str = "") -> str:
    """Format amount with unit
    
    Args:
        value: Amount value
        decimals: Decimal places
        unit: Unit symbol (ETH, USDT, etc)
        
    Returns:
        Formatted string
    """
    formatted = f"{value:.{decimals}f}"
    return f"{formatted} {unit}".strip()


def format_price(value: float) -> str:
    """Format price with 2 decimals and comma separators
    
    Args:
        value: Price value
        
    Returns:
        Formatted price string
    """
    return f"${format_currency(value, 2)}"


def format_percentage(value: float, decimals: int = 4) -> str:
    """Format percentage value
    
    Args:
        value: Decimal value (e.g., 0.001 for 0.1%)
        decimals: Decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_bps(value: float) -> str:
    """Format basis points
    
    Args:
        value: BPS value
        
    Returns:
        Formatted BPS string
    """
    return f"{value:.2f} bps ({format_percentage(value/10000)})"


def print_header(title: str, width: int = 80):
    """Print formatted header
    
    Args:
        title: Header title
        width: Total width
    """
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width + "\n")


def print_section(title: str, width: int = 80):
    """Print formatted section title
    
    Args:
        title: Section title
        width: Total width
    """
    print("\n" + title)
    print("─"*width)


def print_divider(width: int = 80):
    """Print divider line"""
    print("─"*width)


def print_footer(width: int = 80):
    """Print footer line"""
    print("="*width + "\n")


def create_bar_chart(value: float, max_value: float, width: int = 30, char: str = "█") -> str:
    """Create simple bar chart
    
    Args:
        value: Current value
        max_value: Maximum value
        width: Bar width in characters
        char: Character to use for bar
        
    Returns:
        Bar string
    """
    if max_value == 0:
        return ""
    
    filled = min(int((value / max_value) * width), width)
    return char * filled


def format_table_row(columns: list, widths: list, separator: str = " | ") -> str:
    """Format a table row with specified column widths
    
    Args:
        columns: List of column values
        widths: List of column widths
        separator: Column separator
        
    Returns:
        Formatted row string
    """
    formatted_cols = []
    for col, width in zip(columns, widths):
        formatted_cols.append(f"{str(col):>{width}}")
    
    return separator.join(formatted_cols)


def get_spread_color(spread_bps: float) -> str:
    """Get color indicator for spread (emoji)
    
    Args:
        spread_bps: Spread in basis points
        
    Returns:
        Emoji indicator
    """
    if spread_bps < 10:
        return "🟢"  # Green - tight
    elif spread_bps < 50:
        return "🟡"  # Yellow - normal
    else:
        return "🔴"  # Red - wide
