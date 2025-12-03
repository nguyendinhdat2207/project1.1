from decimal import Decimal
from .utils import (
    format_price, format_amount, format_bps, format_currency,
    print_section, print_divider, create_bar_chart, get_spread_color
)


class OrderbookDisplay:

    def __init__(self, mid_price: float):
        self.mid_price = mid_price
    
    def display_current_settings(self, settings: dict):
        print_section("⚙️  CURRENT SETTINGS")
        
        print(f"  Mid Price:     {format_price(settings['mid_price'])}/ETH")
        print(f"  Swap Amount:   {format_amount(settings['swap_amount'], 4, 'ETH')}")
        print(f"  Scenario:      {settings['scenario'].upper()}")
        
        if settings['scenario'] != 'large':
            print(f"  Spread Step:   {format_bps(settings['spread_step_bps'])}")
            print(f"  Base Size:     {format_amount(settings['base_size'], 2, 'ETH')}")
            print(f"  Decay:         {settings['decay']:.2f}")
        else:
            print(f"  Capital (USD): ${format_currency(settings['capital_usd'], 0)}")
        
        print()
    
    def display_orderbook(self, orderbook: dict):
        if not orderbook:
            print("❌ No orderbook data. Generate one first.\n")
            return
        
        ob = orderbook
        
        # Header
        print_section("📊 ORDERBOOK VIEW")
        
        col_widths = [18, 20, 20, 20]
        headers = ["PRICE (USDT/ETH)", "AMOUNT (ETH)", "TOTAL (USDT)", "CUMULATIVE"]
        header_row = ""
        for h, w in zip(headers, col_widths):
            header_row += f"{h:>{w}} "
        print(header_row)
        print_divider(80)
        
        # ASK SIDE (Red) - Sell ETH, Buy USDT
        print("\n🔴 ASK SIDE (You Sell ETH - Higher Prices)")
        print_divider(80)
        
        cumulative_ask = 0
        ask_levels = ob.get('ask_levels', [])
        for level in reversed(ask_levels):
            price = float(level['price'])
            amount = float(level['amount_in_available'])
            total_usd = price * amount
            cumulative_ask += amount
            
            bar = create_bar_chart(amount, 2.0, 25)
            
            row_data = [
                f"${price:,.2f}",
                f"{amount:.6f}",
                f"${total_usd:,.2f}",
                f"{cumulative_ask:.6f}"
            ]
            row_str = ""
            for data, width in zip(row_data, col_widths):
                row_str += f"{data:>{width}} "
            
            print(f"{row_str} {bar}")
        
        # MID PRICE
        print_divider(80)
        spread = ob.get('spread_bps', 0)
        spread_color = get_spread_color(spread)
        spread_pct = spread / 100 if spread else 0
        
        mid_str = f"💚 MID PRICE: {format_price(self.mid_price)}/ETH"
        spread_str = f"SPREAD: {spread:.2f} bps ({spread_pct:.4f}%)"
        print(f"{mid_str:<40} | {spread_color} {spread_str}")
        print_divider(80)
        
        # BID SIDE (Green) - Buy ETH, Sell USDT
        print("\n🟢 BID SIDE (You Buy ETH - Lower Prices)")
        print_divider(80)
        
        cumulative_bid = 0
        bid_levels = ob.get('bid_levels', [])
        for level in bid_levels:
            price = float(level['price'])
            amount = float(level['amount_in_available'])
            total_usd = price * amount
            cumulative_bid += amount
            
            bar = create_bar_chart(amount, 2.0, 25)
            
            row_data = [
                f"${price:,.2f}",
                f"{amount:.6f}",
                f"${total_usd:,.2f}",
                f"{cumulative_bid:.6f}"
            ]
            row_str = ""
            for data, width in zip(row_data, col_widths):
                row_str += f"{data:>{width}} "
            
            print(f"{row_str} {bar}")
        
        print_divider(80)
        print()
    
    def display_summary(self, orderbook: dict):
        if not orderbook:
            return
        
        ob = orderbook
        
        print_section("📈 ORDERBOOK SUMMARY")
        
        total_bid_liquidity = sum(
            float(level['amount_in_available']) 
            for level in ob.get('bid_levels', [])
        )
        total_ask_liquidity = sum(
            float(level['amount_in_available']) 
            for level in ob.get('ask_levels', [])
        )
        
        print(f"  Total Bid Liquidity: {total_bid_liquidity:.6f} ETH")
        print(f"  Total Ask Liquidity: {total_ask_liquidity:.6f} ETH")
        print(f"  Best Bid: {format_price(ob['best_bid']['price'])}/ETH, {format_amount(ob['best_bid']['amount_in_available'], 6, 'ETH')}")
        print(f"  Best Ask: {format_price(ob['best_ask']['price'])}/ETH, {format_amount(ob['best_ask']['amount_in_available'], 6, 'ETH')}")
        print(f"  Spread: {format_bps(ob['spread_bps'])}")
        print()
