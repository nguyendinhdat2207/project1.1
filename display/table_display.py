"""
Table Display Implementation - Orderbook display for tabular format

Extends OrderbookDisplayFormatter for table-specific formatting
"""

from .base import OrderbookDisplayFormatter


class TableOrderbookDisplay(OrderbookDisplayFormatter):
    """Display formatter for table/matrix format
    
    Extends base formatter to provide table-specific display methods
    for displaying orderbook in a structured table format
    """
    
    def display_orderbook(self, orderbook: dict):
        """Display orderbook in table format (Kyberswap-like)
        
        Args:
            orderbook: Orderbook data dictionary
        """
        if not orderbook:
            print("❌ No orderbook generated.")
            return
        
        print("\n" + "="*130)
        print("📊 ORDERBOOK - SYNTHETIC MARKET MAKER")
        print("="*130)
        
        # Header
        header = f"{'CHAIN':<8} | {'RATE (ETH/USDT)':<20} | {'AMOUNT (ETH)':<18} | {'AMOUNT (USDT)':<20} | {'ORDER STATUS':<15}"
        print(header)
        print("-"*130)
        
        # ASK LEVELS (Red) - giá bán cao hơn mid
        ask_levels = self.get_ask_levels(orderbook)
        for level in ask_levels:
            price = float(level['price'])
            amount_eth = float(level['amount_in_available'])
            amount_usdt = price * amount_eth
            
            chain_icon = "🔴"
            rate_display = f"{price:,.2f}"
            amount_eth_display = f"{amount_eth:.4f} ETH"
            amount_usdt_display = f"{amount_usdt:,.2f} USDT"
            status = "Filled 0%"
            
            print(f"{chain_icon:<8} | {rate_display:>18} | {amount_eth_display:>16} | {amount_usdt_display:>18} | {status:<15}")
        
        # MID PRICE LINE
        print("-"*130)
        spread_bps = self.get_spread_bps(orderbook)
        print(f"{'💚':<8} | MID PRICE: ${self.mid_price:,.2f} ETH/USDT  |  SPREAD: {self.format_bps(spread_bps)}")
        print("-"*130)
        
        # BID LEVELS (Green) - giá mua thấp hơn mid
        bid_levels = self.get_bid_levels(orderbook)
        for level in bid_levels:
            price = float(level['price'])
            amount_eth = float(level['amount_in_available'])
            amount_usdt = price * amount_eth
            
            chain_icon = "🟢"
            rate_display = f"{price:,.2f}"
            amount_eth_display = f"{amount_eth:.4f} ETH"
            amount_usdt_display = f"{amount_usdt:,.2f} USDT"
            status = "Filled 0%"
            
            print(f"{chain_icon:<8} | {rate_display:>18} | {amount_eth_display:>16} | {amount_usdt_display:>18} | {status:<15}")
        
        print("="*130 + "\n")
    
    def display_summary(self, orderbook: dict):
        """Display table-formatted summary statistics
        
        Args:
            orderbook: Orderbook data dictionary
        """
        if not orderbook:
            return
        
        print("\n" + "="*130)
        print("📈 ORDERBOOK SUMMARY")
        print("="*130 + "\n")
        
        bid_levels = self.get_bid_levels(orderbook)
        ask_levels = self.get_ask_levels(orderbook)
        
        total_bid_liquidity = self.calculate_total_liquidity(bid_levels)
        total_ask_liquidity = self.calculate_total_liquidity(ask_levels)
        
        # Create summary table
        print(f"{'Metric':<30} | {'Bid Side':<20} | {'Ask Side':<20}")
        print("-"*130)
        print(f"{'Total Liquidity':<30} | {total_bid_liquidity:>18.6f} ETH | {total_ask_liquidity:>18.6f} ETH")
        
        if bid_levels:
            best_bid_price = float(bid_levels[-1]['price'])  # Last (best) bid
            best_bid_amount = float(bid_levels[-1]['amount_in_available'])
            print(f"{'Best Level':<30} | ${best_bid_price:>16,.2f} | ", end="")
        else:
            print(f"{'Best Level':<30} | {'N/A':>18} | ", end="")
        
        if ask_levels:
            best_ask_price = float(ask_levels[0]['price'])  # First (best) ask
            best_ask_amount = float(ask_levels[0]['amount_in_available'])
            print(f"${best_ask_price:>16,.2f}")
        else:
            print(f"{'N/A':>18}")
        
        print(f"{'Spread (BPS)':<30} | {self.get_spread_bps(orderbook):>18.2f} | ")
        print("-"*130 + "\n")
    
    def display_detailed_levels(self, orderbook: dict):
        """Display detailed level-by-level breakdown
        
        Args:
            orderbook: Orderbook data dictionary
        """
        if not orderbook:
            return
        
        print("\n" + "="*150)
        print("📋 DETAILED LEVEL BREAKDOWN")
        print("="*150 + "\n")
        
        # BID LEVELS
        print("🟢 BID LEVELS (Prices at which buyers will buy)")
        print("-"*150)
        bid_levels = self.get_bid_levels(orderbook)
        
        if bid_levels:
            print(f"{'Level':<8} | {'Price (USDT)':<18} | {'Amount (ETH)':<18} | {'Value (USDT)':<18} | {'% of Total':<15}")
            print("-"*150)
            
            total_bid_liquidity = self.calculate_total_liquidity(bid_levels)
            
            for i, level in enumerate(bid_levels, 1):
                price = float(level['price'])
                amount = float(level['amount_in_available'])
                value = price * amount
                pct = (amount / total_bid_liquidity * 100) if total_bid_liquidity > 0 else 0
                
                print(f"{i:<8} | ${price:>16,.2f} | {amount:>16.6f} ETH | ${value:>16,.2f} | {pct:>13.2f}%")
        else:
            print("No bid levels")
        
        # ASK LEVELS
        print("\n🔴 ASK LEVELS (Prices at which sellers will sell)")
        print("-"*150)
        ask_levels = self.get_ask_levels(orderbook)
        
        if ask_levels:
            print(f"{'Level':<8} | {'Price (USDT)':<18} | {'Amount (ETH)':<18} | {'Value (USDT)':<18} | {'% of Total':<15}")
            print("-"*150)
            
            total_ask_liquidity = self.calculate_total_liquidity(ask_levels)
            
            for i, level in enumerate(ask_levels, 1):
                price = float(level['price'])
                amount = float(level['amount_in_available'])
                value = price * amount
                pct = (amount / total_ask_liquidity * 100) if total_ask_liquidity > 0 else 0
                
                print(f"{i:<8} | ${price:>16,.2f} | {amount:>16.6f} ETH | ${value:>16,.2f} | {pct:>13.2f}%")
        else:
            print("No ask levels")
        
        print("="*150 + "\n")
