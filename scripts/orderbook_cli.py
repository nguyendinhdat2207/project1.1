#!/usr/bin/env python3
"""
Interactive Orderbook CLI - Main Entry Point

Hiển thị virtual orderbook trong terminal giống Kyberswap orderbook view
Người dùng có thể thay đổi parameters và xem orderbook cập nhật real-time

Chạy: python scripts/orderbook_cli.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.cli import OrderbookCLIMenu


if __name__ == '__main__':
    cli = OrderbookCLIMenu()
    cli.run()
    cli.run()
