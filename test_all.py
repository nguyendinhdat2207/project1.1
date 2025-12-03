#!/usr/bin/env python3
"""
Test tổng hợp toàn bộ chức năng UniHybrid
"""

import sys
sys.path.insert(0, '.')

from decimal import Decimal


def test_1_imports():
    """Test 1: Kiểm tra imports"""
    print('=' * 80)
    print('TEST 1: Kiểm tra imports')
    print('=' * 80)
    
    modules = [
        ('services.orderbook', 'SyntheticOrderbookGenerator'),
        ('services.matching', 'GreedyMatcher'),
        ('services.execution.core.types', 'ExecutionLeg, MatchingResult'),
        ('services.execution.core.execution_plan', 'ExecutionPlanBuilder'),
        ('services.execution.ui', 'VirtualOrderBook'),
        ('display', 'OrderbookDisplayFormatter, CLIOrderbookDisplay, TableOrderbookDisplay'),
        ('scripts.cli', 'OrderbookCLIMenu'),
    ]
    
    passed = 0
    for module, items in modules:
        try:
            exec(f'from {module} import {items}')
            print(f'✅ {module}')
            passed += 1
        except Exception as e:
            print(f'❌ {module}: {e}')
    
    print(f'\n📊 Result: {passed}/{len(modules)} passed')
    return passed == len(modules)


def test_2_virtual_orderbook():
    """Test 2: VirtualOrderBook"""
    print('\n' + '=' * 80)
    print('TEST 2: VirtualOrderBook - 3 Scenarios')
    print('=' * 80)
    
    from services.execution.ui import VirtualOrderBook
    from services.execution.ui.virtual_orderbook import generate_sample_cex_snapshot
    
    mid_price = 2700.0
    passed = 0
    
    for scenario in ['small', 'medium', 'large']:
        print(f'\n📦 Scenario: {scenario.upper()}')
        print('-' * 40)
        
        try:
            vob = VirtualOrderBook(mid_price=mid_price)
            
            if scenario == 'large':
                cex_snapshot = generate_sample_cex_snapshot(mid_price, num_levels=10)
                orderbook = vob.build_orderbook(
                    swap_amount=2.5,
                    scenario=scenario,
                    capital_usd=50000,
                    cex_snapshot=cex_snapshot
                )
            else:
                orderbook = vob.build_orderbook(
                    swap_amount=1.0 if scenario == 'small' else 2.0,
                    scenario=scenario
                )
            
            bid_levels = orderbook.get('bid_levels', [])
            ask_levels = orderbook.get('ask_levels', [])
            
            print(f'   ✅ Bid levels: {len(bid_levels):2d}')
            print(f'   ✅ Ask levels: {len(ask_levels):2d}')
            print(f'   ✅ Mid price: ${orderbook["mid_price"]:,.2f}')
            print(f'   ✅ Spread: {orderbook.get("spread_bps", 0):.2f} bps')
            
            passed += 1
        except Exception as e:
            print(f'   ❌ Error: {e}')
            import traceback
            traceback.print_exc()
    
    print(f'\n📊 Result: {passed}/3 scenarios passed')
    return passed == 3


def test_3_display_formatters():
    """Test 3: Display Formatters"""
    print('\n' + '=' * 80)
    print('TEST 3: Display Formatters')
    print('=' * 80)
    
    try:
        from display import CLIOrderbookDisplay, TableOrderbookDisplay
        from services.execution.ui import VirtualOrderBook
        
        vob = VirtualOrderBook(mid_price=2700.0)
        orderbook = vob.build_orderbook(swap_amount=1.0, scenario='small')
        
        # Test CLI Display
        print('\n📱 CLIOrderbookDisplay:')
        cli_display = CLIOrderbookDisplay(mid_price=2700.0)
        print('   ✅ Created CLIOrderbookDisplay')
        print(f'   ✅ Has {len([m for m in dir(cli_display) if not m.startswith("_")])} public methods')
        
        # Test Table Display
        print('\n📊 TableOrderbookDisplay:')
        table_display = TableOrderbookDisplay(mid_price=2700.0)
        print('   ✅ Created TableOrderbookDisplay')
        print(f'   ✅ Has {len([m for m in dir(table_display) if not m.startswith("_")])} public methods')
        
        print('\n✅ TEST 3 PASSED')
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False


def test_4_cli_menu():
    """Test 4: CLI Menu"""
    print('\n' + '=' * 80)
    print('TEST 4: CLI Menu')
    print('=' * 80)
    
    try:
        from scripts.cli import OrderbookCLIMenu
        
        cli = OrderbookCLIMenu()
        print('✅ Created OrderbookCLIMenu instance')
        
        methods = [m for m in dir(cli) if not m.startswith('_') and callable(getattr(cli, m))]
        print(f'✅ Has {len(methods)} public methods')
        print(f'✅ Methods: {", ".join(methods[:5])}...')
        
        print('\n✅ TEST 4 PASSED')
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Chạy tất cả tests"""
    print('\n' + '🧪' * 40)
    print('UniHybrid - FULL FUNCTIONALITY TEST')
    print('🧪' * 40 + '\n')
    
    results = {
        'Imports': test_1_imports(),
        'VirtualOrderBook': test_2_virtual_orderbook(),
        'Display Formatters': test_3_display_formatters(),
        'CLI Menu': test_4_cli_menu(),
    }
    
    print('\n' + '=' * 80)
    print('📊 FINAL SUMMARY')
    print('=' * 80)
    
    for test_name, passed in results.items():
        status = '✅ PASSED' if passed else '❌ FAILED'
        print(f'{test_name:25s} {status}')
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f'\n📊 Overall: {total_passed}/{total_tests} tests passed')
    
    if total_passed == total_tests:
        print('\n🎉 ALL TESTS PASSED! 🎉')
    else:
        print(f'\n⚠️  {total_tests - total_passed} test(s) failed')
    
    return total_passed == total_tests


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
