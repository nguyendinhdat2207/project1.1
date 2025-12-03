"""
Display Base Formatter - Abstract base class for orderbook display

Provides common formatting methods for different display implementations (CLI, Table, Web, etc)
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Tuple


class OrderbookDisplayFormatter(ABC):
    """
    Abstract base class for orderbook display formatting
    
    Provides common formatting methods that can be reused across different
    display implementations (CLI, Table, Web, etc).
    
    Subclasses must implement:
    - display_orderbook()
    - display_summary()
    """
    
    def __init__(self, mid_price: float):
        """
        Initialize formatter
        
        Args:
            mid_price: Market mid price (for reference)
        """
        self.mid_price = mid_price
    
    # ============================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # ============================================================================
    
    @abstractmethod
    def display_orderbook(self, orderbook: dict):
        """Display orderbook in format-specific way
        
        Args:
            orderbook: Orderbook data dictionary
        """
        pass
    
    @abstractmethod
    def display_summary(self, orderbook: dict):
        """Display summary statistics in format-specific way
        
        Args:
            orderbook: Orderbook data dictionary
        """
        pass
    
    # ============================================================================
    # SHARED FORMATTING METHODS - Can be used by all subclasses
    # ============================================================================
    
    def format_price(self, value: float) -> str:
        """Format price with currency symbol
        
        Args:
            value: Price value
            
        Returns:
            Formatted price (e.g., "$2700.00")
        """
        return f"${value:,.2f}"
    
    def format_amount(self, value: float, decimals: int = 6, unit: str = "") -> str:
        """Format amount with optional unit
        
        Args:
            value: Amount value
            decimals: Decimal places
            unit: Unit suffix (ETH, USDT, etc)
            
        Returns:
            Formatted amount
        """
        formatted = f"{value:.{decimals}f}"
        return f"{formatted} {unit}".strip()
    
    def format_currency(self, value: float, decimals: int = 2) -> str:
        """Format number with currency formatting (commas)
        
        Args:
            value: Numeric value
            decimals: Decimal places
            
        Returns:
            Formatted number
        """
        return f"{value:,.{decimals}f}"
    
    def format_percentage(self, value: float, decimals: int = 4) -> str:
        """Format as percentage
        
        Args:
            value: Decimal value (0.001 = 0.1%)
            decimals: Decimal places
            
        Returns:
            Formatted percentage (e.g., "0.1000%")
        """
        return f"{value * 100:.{decimals}f}%"
    
    def format_bps(self, value: float) -> str:
        """Format basis points
        
        Args:
            value: BPS value
            
        Returns:
            Formatted BPS (e.g., "10.00 bps (0.1000%)")
        """
        pct = self.format_percentage(value / 10000)
        return f"{value:.2f} bps ({pct})"
    
    def get_spread_color_emoji(self, spread_bps: float) -> str:
        """Get emoji color indicator for spread tightness
        
        Args:
            spread_bps: Spread in basis points
            
        Returns:
            Emoji indicator (🟢 tight, 🟡 normal, 🔴 wide)
        """
        if spread_bps < 10:
            return "🟢"  # Green - tight spread
        elif spread_bps < 50:
            return "🟡"  # Yellow - normal spread
        else:
            return "🔴"  # Red - wide spread
    
    def create_bar_chart(self, value: float, max_value: float, width: int = 30, char: str = "█") -> str:
        """Create ASCII bar chart
        
        Args:
            value: Current value
            max_value: Maximum value (100%)
            width: Bar width in characters
            char: Character to use for bar
            
        Returns:
            Bar string (e.g., "████████░░░░░░░░")
        """
        if max_value == 0:
            return ""
        
        filled = min(int((value / max_value) * width), width)
        return char * filled
    
    # ============================================================================
    # SHARED DATA EXTRACTION METHODS
    # ============================================================================
    
    def get_bid_levels(self, orderbook: dict) -> list:
        """Extract bid levels from orderbook
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            List of bid level dictionaries
        """
        return orderbook.get('bid_levels', [])
    
    def get_ask_levels(self, orderbook: dict) -> list:
        """Extract ask levels from orderbook
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            List of ask level dictionaries
        """
        return orderbook.get('ask_levels', [])
    
    def get_best_bid(self, orderbook: dict) -> dict:
        """Get best bid level
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            Best bid level or empty dict
        """
        return orderbook.get('best_bid', {})
    
    def get_best_ask(self, orderbook: dict) -> dict:
        """Get best ask level
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            Best ask level or empty dict
        """
        return orderbook.get('best_ask', {})
    
    def get_spread_bps(self, orderbook: dict) -> float:
        """Get spread in basis points
        
        Args:
            orderbook: Orderbook data
            
        Returns:
            Spread in BPS
        """
        return orderbook.get('spread_bps', 0)
    
    def calculate_total_liquidity(self, levels: list, key: str = 'amount_in_available') -> float:
        """Calculate total liquidity from levels
        
        Args:
            levels: List of orderbook levels
            key: Key to sum (default: 'amount_in_available')
            
        Returns:
            Total liquidity
        """
        return sum(float(level.get(key, 0)) for level in levels)
    
    def calculate_cumulative_amounts(self, levels: list, key: str = 'amount_in_available') -> List[float]:
        """Calculate cumulative amounts
        
        Args:
            levels: List of orderbook levels
            key: Key to accumulate
            
        Returns:
            List of cumulative amounts
        """
        cumulative = []
        total = 0.0
        
        for level in levels:
            total += float(level.get(key, 0))
            cumulative.append(total)
        
        return cumulative
    
    # ============================================================================
    # SHARED DISPLAY HELPER METHODS
    # ============================================================================
    
    def print_header(self, title: str, width: int = 80):
        """Print formatted header
        
        Args:
            title: Header title
            width: Total width
        """
        print("\n" + "="*width)
        print(title.center(width))
        print("="*width + "\n")
    
    def print_section(self, title: str, width: int = 80):
        """Print formatted section title
        
        Args:
            title: Section title
            width: Total width
        """
        print("\n" + title)
        print("─"*width)
    
    def print_divider(self, width: int = 80):
        """Print divider line"""
        print("─"*width)
    
    def print_footer(self, width: int = 80):
        """Print footer line"""
        print("="*width + "\n")
    
    def format_table_row(self, columns: list, widths: list, separator: str = " | ") -> str:
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
