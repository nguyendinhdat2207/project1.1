"""
CLI Display Implementation - Orderbook display for CLI terminal

Extends OrderbookDisplayFormatter for CLI-specific formatting
"""

from .base import OrderbookDisplayFormatter
from scripts.cli.utils import clear_screen


class CLIOrderbookDisplay(OrderbookDisplayFormatter):
    """Display formatter for CLI terminal
    
    Extends base formatter to provide CLI-specific display methods
    with terminal colors, ASCII art, and interactive elements
    """
    
    def display_orderbook(self, orderbook: dict):
        """Display orderbook in Kyberswap-like CLI format
        
        Args:
            orderbook: Orderbook data dictionary
        """
        if not orderbook:
            print("❌ No orderbook data. Generate one first.\n")
            return
        
        self.print_section("📊 ORDERBOOK VIEW", width=80)
        
        # Header
        col_widths = [18, 20, 20, 20]
        headers = ["PRICE (USDT/ETH)", "AMOUNT (ETH)", "TOTAL (USDT)", "CUMULATIVE"]
        header_row = ""
        for h, w in zip(headers, col_widths):
            header_row += f"{h:>{w}} "
        print(header_row)
        self.print_divider(80)
        
        # ASK SIDE (Red) - Sell ETH, Buy USDT
        print("\n🔴 ASK SIDE (You Sell ETH - Higher Prices)")
        self.print_divider(80)
        
        ask_levels = self.get_ask_levels(orderbook)
        ask_cumulative = self.calculate_cumulative_amounts(ask_levels)
        
        for level, cumulative in zip(reversed(ask_levels), reversed(ask_cumulative)):
            price = float(level['price'])
            amount = float(level['amount_in_available'])
            total_usd = price * amount
            
            bar = self.create_bar_chart(amount, 2.0, 25)
            
            row_data = [
                f"${price:,.2f}",
                f"{amount:.6f}",
                f"${total_usd:,.2f}",
                f"{cumulative:.6f}"
            ]
            row_str = ""
            for data, width in zip(row_data, col_widths):
                row_str += f"{data:>{width}} "
            
            print(f"{row_str} {bar}")
        
        # MID PRICE
        self.print_divider(80)
        spread = self.get_spread_bps(orderbook)
        spread_color = self.get_spread_color_emoji(spread)
        spread_pct = spread / 100 if spread else 0
        
        mid_str = f"💚 MID PRICE: {self.format_price(self.mid_price)}/ETH"
        spread_str = f"SPREAD: {self.format_bps(spread)}"
        print(f"{mid_str:<40} | {spread_color} {spread_str}")
        self.print_divider(80)
        
        # BID SIDE (Green) - Buy ETH, Sell USDT
        print("\n🟢 BID SIDE (You Buy ETH - Lower Prices)")
        self.print_divider(80)
        
        bid_levels = self.get_bid_levels(orderbook)
        bid_cumulative = self.calculate_cumulative_amounts(bid_levels)
        
        for level, cumulative in zip(bid_levels, bid_cumulative):
            price = float(level['price'])
            amount = float(level['amount_in_available'])
            total_usd = price * amount
            
            bar = self.create_bar_chart(amount, 2.0, 25)
            
            row_data = [
                f"${price:,.2f}",
                f"{amount:.6f}",
                f"${total_usd:,.2f}",
                f"{cumulative:.6f}"
            ]
            row_str = ""
            for data, width in zip(row_data, col_widths):
                row_str += f"{data:>{width}} "
            
            print(f"{row_str} {bar}")
        
        self.print_divider(80)
        print()
    
    def display_summary(self, orderbook: dict):
        """Display CLI-formatted summary statistics
        
        Args:
            orderbook: Orderbook data dictionary
        """
        if not orderbook:
            return
        
        self.print_section("📈 ORDERBOOK SUMMARY", width=80)
        
        bid_levels = self.get_bid_levels(orderbook)
        ask_levels = self.get_ask_levels(orderbook)
        
        total_bid_liquidity = self.calculate_total_liquidity(bid_levels)
        total_ask_liquidity = self.calculate_total_liquidity(ask_levels)
        
        best_bid = self.get_best_bid(orderbook)
        best_ask = self.get_best_ask(orderbook)
        
        print(f"  Total Bid Liquidity: {self.format_amount(total_bid_liquidity, 6, 'ETH')}")
        print(f"  Total Ask Liquidity: {self.format_amount(total_ask_liquidity, 6, 'ETH')}")
        print(f"  Best Bid: {self.format_price(best_bid.get('price', 0))}/ETH, {self.format_amount(best_bid.get('amount_in_available', 0), 6, 'ETH')}")
        print(f"  Best Ask: {self.format_price(best_ask.get('price', 0))}/ETH, {self.format_amount(best_ask.get('amount_in_available', 0), 6, 'ETH')}")
        print(f"  Spread: {self.format_bps(self.get_spread_bps(orderbook))}")
        print()
    
    def display_settings(self, settings: dict):
        """Display CLI-formatted settings
        
        Args:
            settings: Settings dictionary
        """
        self.print_section("⚙️  CURRENT SETTINGS", width=80)
        
        print(f"  Mid Price:     {self.format_price(settings['mid_price'])}/ETH")
        print(f"  Swap Amount:   {self.format_amount(settings['swap_amount'], 4, 'ETH')}")
        print(f"  Scenario:      {settings['scenario'].upper()}")
        
        if settings['scenario'] != 'large':
            print(f"  Spread Step:   {self.format_bps(settings['spread_step_bps'])}")
            print(f"  Base Size:     {self.format_amount(settings['base_size'], 2, 'ETH')}")
            print(f"  Decay:         {settings['decay']:.2f}")
        else:
            print(f"  Capital (USD): ${self.format_currency(settings['capital_usd'], 0)}")
        
        print()
