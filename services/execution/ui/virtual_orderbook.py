"""
VirtualOrderBook - Synthetic orderbook builder cho UniHybrid

Tạo orderbook ảo dựa trên mid_price (từ AMM hoặc input),
hỗ trợ 3 scenarios (small, medium, large) với different depth/shape.

Classes:
    VirtualOrderBook: Main class để build và manage virtual orderbook

Usage:
    vob = VirtualOrderBook(
        mid_price=2700,
        token_in_decimals=18,
        token_out_decimals=6
    )
    
    orderbook_levels = vob.build_orderbook(
        swap_amount=1.0,  # 1 ETH
        scenario='medium',
        spread_step_bps=10,  # 10 bps = 0.001 = 0.1%
        base_size=2.0,
        decay=0.5
    )
"""

from typing import List, Dict, Union, Optional
from decimal import Decimal
import json
import math


class VirtualOrderBook:
    """
    Virtual orderbook builder dựa trên mid_price.
    
    Attributes:
        mid_price (Decimal): Giá trung bình (token_out / token_in)
        token_in_decimals (int): Decimals của token input
        token_out_decimals (int): Decimals của token output
        bid_levels (List[Dict]): Danh sách bid levels
        ask_levels (List[Dict]): Danh sách ask levels
    
    Methods:
        build_orderbook(): Xây dựng orderbook theo scenario
        get_best_bid(): Lấy mức bid tốt nhất (giá cao nhất)
        get_best_ask(): Lấy mức ask tốt nhất (giá thấp nhất)
        get_spread(): Tính spread (bps)
        snapshot(): Trả về toàn bộ orderbook dưới dạng JSON
    """
    
    def __init__(
        self,
        mid_price: Union[float, Decimal],
        token_in_decimals: int = 18,
        token_out_decimals: int = 6
    ):
        """
        Khởi tạo VirtualOrderBook.
        
        Args:
            mid_price: Giá trung bình (token_out / token_in)
            token_in_decimals: Decimals của token input (vd 18 cho ETH)
            token_out_decimals: Decimals của token output (vd 6 cho USDT)
        """
        self.mid_price = Decimal(str(mid_price))
        self.token_in_decimals = token_in_decimals
        self.token_out_decimals = token_out_decimals
        
        self.bid_levels: List[Dict] = []  # Bid side (price < mid)
        self.ask_levels: List[Dict] = []  # Ask side (price > mid)
    
    def build_orderbook(
        self,
        swap_amount: Union[float, Decimal],
        scenario: str = 'medium',
        spread_step_bps: int = 10,
        base_size: Optional[Union[float, Decimal]] = None,
        decay: float = 0.5,
        capital_usd: Optional[float] = None,
        cex_snapshot: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Xây dựng synthetic orderbook theo scenario.
        
        Args:
            swap_amount: Lượng token_in muốn swap
            scenario: 'small', 'medium', 'large'
                - small: 1 level duy nhất, depth ~ 0.5 × swap_amount
                - medium: 3-5 levels, spread 10-30 bps/level, size decay
                - large: Shape từ CEX snapshot, scale theo capital_usd
            spread_step_bps: Khoảng cách giữa các level (bps), vd 10 = 0.1%
            base_size: Size của level đầu tiên (token_in), default = 2 × swap_amount
            decay: Hệ số giảm size khi ra xa mid (0.5-0.7)
            capital_usd: Vốn UniHybrid cho scenario large (USD)
            cex_snapshot: List [{price, size}, ...] từ CEX (dùng cho large)
        
        Returns:
            Dict: {
                'bid_levels': [...],
                'ask_levels': [...],
                'best_bid': {...},
                'best_ask': {...},
                'spread_bps': float
            }
        
        Raises:
            ValueError: Nếu scenario không hợp lệ
        """
        swap_amount = Decimal(str(swap_amount))
        
        if base_size is None:
            base_size = swap_amount * 2
        else:
            base_size = Decimal(str(base_size))
        
        # Clear previous levels
        self.bid_levels = []
        self.ask_levels = []
        
        if scenario == 'small':
            self._build_small_orderbook(swap_amount, spread_step_bps)
        
        elif scenario == 'medium':
            self._build_medium_orderbook(
                swap_amount, spread_step_bps, base_size, decay
            )
        
        elif scenario == 'large':
            if capital_usd is None or cex_snapshot is None:
                raise ValueError(
                    "Scenario 'large' requires capital_usd and cex_snapshot"
                )
            self._build_large_orderbook(
                swap_amount, spread_step_bps, capital_usd, cex_snapshot
            )
        
        else:
            raise ValueError(
                f"Unknown scenario '{scenario}'. "
                f"Must be 'small', 'medium', or 'large'"
            )
        
        return self.snapshot()
    
    def _build_small_orderbook(
        self,
        swap_amount: Decimal,
        spread_step_bps: int
    ) -> None:
        """
        Scenario Small: 1 level duy nhất.
        
        - Depth ~ 0.5 × swap_amount
        - Price = mid ± spread_step bps
        - Dùng khi liquidity nhỏ hoặc test nhanh
        
        Args:
            swap_amount: Lượng token_in
            spread_step_bps: Spread (bps)
        """
        depth = swap_amount * Decimal('0.5')
        spread_multiplier = self._bps_to_multiplier(spread_step_bps)
        
        # Bid level (ask to buy): giá < mid
        bid_price = self.mid_price / spread_multiplier
        self.bid_levels.append({
            'price': float(bid_price),
            'amount_in_available': float(depth),
            'side': 'bid'
        })
        
        # Ask level (ask to sell): giá > mid
        ask_price = self.mid_price * spread_multiplier
        self.ask_levels.append({
            'price': float(ask_price),
            'amount_in_available': float(depth),
            'side': 'ask'
        })
    
    def _build_medium_orderbook(
        self,
        swap_amount: Decimal,
        spread_step_bps: int,
        base_size: Decimal,
        decay: float
    ) -> None:
        """
        Scenario Medium: 3-5 levels quanh mid.
        
        - Spread: 10-30 bps mỗi level
        - Size level 0 = base_size, levels sau = level trước × decay
        - Nếu tổng size > 2-3 × swap_amount → scale xuống theo tỉ lệ
        
        Args:
            swap_amount: Lượng token_in
            spread_step_bps: Spread per level (bps)
            base_size: Size của level đầu
            decay: Hệ số giảm size (0.5-0.7)
        """
        num_levels = 3  # 3-5, dùng 3 là default
        spread_multiplier = self._bps_to_multiplier(spread_step_bps)
        
        # Build bid side (price < mid)
        bid_levels_list = []
        ask_levels_list = []
        
        for i in range(num_levels):
            # Size tại level i: base_size * (decay ^ i)
            size_at_level = base_size * Decimal(str(decay ** i))
            
            # Bid: price < mid, cộng spread dần
            bid_price = self.mid_price / (spread_multiplier ** (i + 1))
            bid_levels_list.append({
                'level': i,
                'price': float(bid_price),
                'amount_in_available': float(size_at_level),
                'side': 'bid'
            })
            
            # Ask: price > mid, cộng spread dần
            ask_price = self.mid_price * (spread_multiplier ** (i + 1))
            ask_levels_list.append({
                'level': i,
                'price': float(ask_price),
                'amount_in_available': float(size_at_level),
                'side': 'ask'
            })
        
        # Tính tổng liquidity
        total_size = sum(
            Decimal(str(level['amount_in_available']))
            for level in bid_levels_list
        )
        
        # Nếu tổng > 2-3 × swap_amount → scale xuống
        target_total = swap_amount * Decimal('2.5')
        if total_size > target_total:
            scale_factor = float(target_total / total_size)
            for level in bid_levels_list:
                level['amount_in_available'] *= scale_factor
            for level in ask_levels_list:
                level['amount_in_available'] *= scale_factor
        
        self.bid_levels = bid_levels_list
        self.ask_levels = ask_levels_list
    
    def _build_large_orderbook(
        self,
        swap_amount: Decimal,
        spread_step_bps: int,
        capital_usd: float,
        cex_snapshot: List[Dict]
    ) -> None:
        """
        Scenario Large / Binance-like: Dùng shape từ CEX.
        
        - Lấy levels ±1-2% quanh mid
        - Tính tổng notional CEX → scale theo capital_usd
        - Size level = size_cex × scaleFactor → convert sang token_in
        - Giữ shape tương đối so với mid
        
        Args:
            swap_amount: Lượng token_in
            spread_step_bps: Spread per level (bps)
            capital_usd: Vốn UniHybrid (USD)
            cex_snapshot: List [{side, price, size}, ...] từ CEX
        
        Note:
            cex_snapshot format:
            [
                {'side': 'bid', 'price': 2698, 'size': 10.5},
                {'side': 'bid', 'price': 2695, 'size': 5.2},
                {'side': 'ask', 'price': 2702, 'size': 8.3},
                ...
            ]
        """
        # Filter levels trong ±1-2% quanh mid
        price_range_pct = Decimal('0.02')  # 2%
        price_min = self.mid_price * (Decimal('1') - price_range_pct)
        price_max = self.mid_price * (Decimal('1') + price_range_pct)
        
        filtered_bids = []
        filtered_asks = []
        bid_notional = Decimal('0')
        ask_notional = Decimal('0')
        
        for level in cex_snapshot:
            side = level.get('side', '').lower()
            price = Decimal(str(level['price']))
            size = Decimal(str(level['size']))
            
            # Check nếu price trong range
            if not (price_min <= price <= price_max):
                continue
            
            notional = price * size
            
            if side == 'bid':
                filtered_bids.append({
                    'price': price,
                    'size': size,
                    'notional': notional
                })
                bid_notional += notional
            elif side == 'ask':
                filtered_asks.append({
                    'price': price,
                    'size': size,
                    'notional': notional
                })
                ask_notional += notional
        
        # Tính scale factor dựa trên capital_usd
        capital_decimal = Decimal(str(capital_usd))
        total_cex_notional = bid_notional + ask_notional
        
        if total_cex_notional > 0:
            scale_factor = capital_decimal / total_cex_notional
        else:
            scale_factor = Decimal('1')
        
        # Build bid levels từ filtered_bids
        for level in sorted(filtered_bids, key=lambda x: x['price'], reverse=True):
            scaled_size_usd = level['notional'] * scale_factor
            # Convert USD size → token_in amount
            # amount_in = scaled_size_usd / price
            amount_in = scaled_size_usd / level['price']
            
            self.bid_levels.append({
                'price': float(level['price']),
                'amount_in_available': float(amount_in),
                'side': 'bid'
            })
        
        # Build ask levels từ filtered_asks
        for level in sorted(filtered_asks, key=lambda x: x['price']):
            scaled_size_usd = level['notional'] * scale_factor
            amount_in = scaled_size_usd / level['price']
            
            self.ask_levels.append({
                'price': float(level['price']),
                'amount_in_available': float(amount_in),
                'side': 'ask'
            })
    
    def get_best_bid(self) -> Optional[Dict]:
        """
        Lấy mức bid tốt nhất (giá cao nhất).
        
        Returns:
            Dict: {price, amount_in_available} hoặc None nếu không có bid
        """
        if not self.bid_levels:
            return None
        return max(self.bid_levels, key=lambda x: x['price'])
    
    def get_best_ask(self) -> Optional[Dict]:
        """
        Lấy mức ask tốt nhất (giá thấp nhất).
        
        Returns:
            Dict: {price, amount_in_available} hoặc None nếu không có ask
        """
        if not self.ask_levels:
            return None
        return min(self.ask_levels, key=lambda x: x['price'])
    
    def get_spread(self) -> Optional[float]:
        """
        Tính spread (bps) = (best_ask - best_bid) / mid_price * 10000.
        
        Returns:
            float: Spread trong bps, hoặc None nếu không đủ data
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        bid_price = Decimal(str(best_bid['price']))
        ask_price = Decimal(str(best_ask['price']))
        
        spread = (ask_price - bid_price) / self.mid_price * Decimal('10000')
        return float(spread)
    
    def get_total_bid_liquidity(self) -> Decimal:
        """
        Tính tổng liquidity (token_in) trên bid side.
        
        Returns:
            Decimal: Tổng amount_in_available từ tất cả bid levels
        """
        return sum(
            Decimal(str(level['amount_in_available']))
            for level in self.bid_levels
        )
    
    def get_total_ask_liquidity(self) -> Decimal:
        """
        Tính tổng liquidity (token_in) trên ask side.
        
        Returns:
            Decimal: Tổng amount_in_available từ tất cả ask levels
        """
        return sum(
            Decimal(str(level['amount_in_available']))
            for level in self.ask_levels
        )
    
    def snapshot(self) -> Dict:
        """
        Trả về toàn bộ orderbook dưới dạng dict (JSON-compatible).
        
        Returns:
            Dict: {
                'bid_levels': [...],
                'ask_levels': [...],
                'best_bid': {...},
                'best_ask': {...},
                'spread_bps': float,
                'mid_price': float,
                'total_bid_liquidity': float,
                'total_ask_liquidity': float
            }
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        spread = self.get_spread()
        
        return {
            'mid_price': float(self.mid_price),
            'bid_levels': self.bid_levels,
            'ask_levels': self.ask_levels,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread_bps': spread,
            'total_bid_liquidity': float(self.get_total_bid_liquidity()),
            'total_ask_liquidity': float(self.get_total_ask_liquidity())
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Serialize orderbook thành JSON string.
        
        Args:
            indent: Indentation level (None = compact)
        
        Returns:
            str: JSON string
        """
        return json.dumps(self.snapshot(), indent=indent)
    
    @staticmethod
    def _bps_to_multiplier(bps: int) -> Decimal:
        """
        Convert basis points (bps) thành multiplier.
        
        Công thức: multiplier = 1 + (bps / 10000)
        
        Args:
            bps: Basis points (vd 10 = 0.1% = 0.001 multiplier)
        
        Returns:
            Decimal: 1 + (bps / 10000)
        
        Examples:
            >>> _bps_to_multiplier(10)
            Decimal('1.001')
            
            >>> _bps_to_multiplier(100)
            Decimal('1.01')
        """
        return Decimal('1') + (Decimal(str(bps)) / Decimal('10000'))


# ============================================================================
# HELPER: Sample CEX snapshot generator (dùng cho testing)
# ============================================================================

def generate_sample_cex_snapshot(
    mid_price: float,
    num_levels: int = 5,
    depth_percent: float = 0.02,
    base_size: float = 10.0,
    decay: float = 0.7
) -> List[Dict]:
    """
    Tạo sample CEX snapshot xung quanh mid_price.
    
    Args:
        mid_price: Giá trung bình
        num_levels: Số levels mỗi phía (default 5)
        depth_percent: Độ sâu tính từ mid (vd 0.02 = ±2%)
        base_size: Size của level đầu tiên
        decay: Hệ số giảm size (0.6-0.8)
    
    Returns:
        List[Dict]: Sample orderbook [{side, price, size}, ...]
    
    Example:
        >>> snapshot = generate_sample_cex_snapshot(2700, num_levels=3)
        >>> print(snapshot)
        [
            {'side': 'bid', 'price': 2700.0, 'size': 10.0},
            {'side': 'bid', 'price': 2691.0, 'size': 7.0},
            {'side': 'bid', 'price': 2682.0, 'size': 4.9},
            {'side': 'ask', 'price': 2700.0, 'size': 10.0},
            ...
        ]
    """
    snapshot = []
    decay_decimal = Decimal(str(decay))
    
    # Bid side
    for i in range(num_levels):
        price_offset = mid_price * depth_percent * (i + 1)
        bid_price = mid_price - price_offset
        bid_size = base_size * (decay ** i)
        
        snapshot.append({
            'side': 'bid',
            'price': bid_price,
            'size': bid_size
        })
    
    # Ask side
    for i in range(num_levels):
        price_offset = mid_price * depth_percent * (i + 1)
        ask_price = mid_price + price_offset
        ask_size = base_size * (decay ** i)
        
        snapshot.append({
            'side': 'ask',
            'price': ask_price,
            'size': ask_size
        })
    
    return snapshot
