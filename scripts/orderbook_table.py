#!/usr/bin/env python3
"""
Orderbook Table Display - Hiển thị bảng giá orderbook
Tương tự Kyberswap/1inch với nhiều levels (bid/ask)

Entry point for table display using TableOrderbookDisplay formatter

Chạy: python scripts/orderbook_table.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.execution.ui import VirtualOrderBook, generate_sample_cex_snapshot
from display import TableOrderbookDisplay


class OrderbookTableDisplay:
    """Hiển thị orderbook dưới dạng bảng using reusable display formatter"""
    
    def __init__(self, mid_price=2700.0):
        self.vob = VirtualOrderBook(mid_price=mid_price)
        self.orderbook = None
        self.mid_price = mid_price
        self.formatter = TableOrderbookDisplay(mid_price=mid_price)
        
    def generate_and_display(self, scenario='medium', swap_amount=1.0, capital_usd=50000):
        """Generate orderbook và hiển thị bảng"""
        if scenario == 'large':
            # For large scenario, need CEX snapshot
            cex_snapshot = generate_sample_cex_snapshot(self.mid_price, num_levels=10)
            
            self.orderbook = self.vob.build_orderbook(
                swap_amount=swap_amount,
                scenario=scenario,
                spread_step_bps=10,
                base_size=2.0,
                decay=0.5,
                capital_usd=capital_usd,
                cex_snapshot=cex_snapshot
            )
        else:
            self.orderbook = self.vob.build_orderbook(
                swap_amount=swap_amount,
                scenario=scenario,
                spread_step_bps=10,
                base_size=2.0,
                decay=0.5
            )
        self.formatter.mid_price = self.mid_price
        self.display_table()
    
    def display_table(self):
        """Hiển thị bảng orderbook kiểu Kyberswap"""
        self.formatter.display_orderbook(self.orderbook)
    
    def display_summary(self):
        """Hiển thị thống kê tóm tắt"""
        self.formatter.display_summary(self.orderbook)


def main():
    """Hiển thị 3 scenarios"""
    
    print("\n" + "🎮 ORDERBOOK TABLE DISPLAY - 3 SCENARIOS".center(130))
    print()
    
    display = OrderbookTableDisplay(mid_price=2700.0)
    
    # Scenario 1: Small
    print("\n" + "="*130)
    print("📌 SCENARIO 1: SMALL".center(130))
    print("="*130)
    display.generate_and_display(scenario='small', swap_amount=1.0)
    display.display_summary()
    
    # Scenario 2: Medium
    print("\n" + "="*130)
    print("📌 SCENARIO 2: MEDIUM (Default - Recommended)".center(130))
    print("="*130)
    display.generate_and_display(scenario='medium', swap_amount=1.0)
    display.display_summary()
    
    # Scenario 3: Large
    print("\n" + "="*130)
    print("📌 SCENARIO 3: LARGE (Deep book - CEX-like)".center(130))
    print("="*130)
    display.generate_and_display(scenario='large', swap_amount=1.0)
    display.display_summary()
    
    print("\n✅ Done! Bảng orderbook đã được hiển thị.\n")


if __name__ == '__main__':
    main()
