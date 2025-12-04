"""
Backtest Report Generator - Auto-generate Notion-ready reports
"""

from decimal import Decimal
from typing import Dict, Any, List
import json
from datetime import datetime


class BacktestReportGenerator:
    """Generate formatted backtest reports for Notion"""
    
    def __init__(self, scenario_name: str, config: Dict[str, Any]):
        self.scenario_name = scenario_name
        self.config = config
        self.results = {}
        
    def add_result(self, result: Dict[str, Any]):
        """Add backtest result"""
        self.results = result
        
    def generate_markdown_section(self) -> str:
        """Generate Markdown section for one scenario - Ready for Notion"""
        
        split = self.results.get('split', {})
        total_in = int(split.get('amount_in_total', 0))
        ob_in = int(split.get('amount_in_on_orderbook', 0))
        amm_in = int(split.get('amount_in_on_amm', 0))
        
        amm_ref = int(self.results.get('amm_reference_out', 0))
        total_out = int(self.results.get('expected_total_out', 0))
        sav_before = int(self.results.get('savings_before_fee', 0))
        sav_after = int(self.results.get('savings_after_fee', 0))
        
        decimals_in = self.config.get('decimals_in', 18)
        decimals_out = self.config.get('decimals_out', 6)
        
        # Calculate metrics
        ob_pct = (ob_in * 100 // total_in) if total_in > 0 else 0
        amm_pct = (amm_in * 100 // total_in) if total_in > 0 else 0
        improvement = (sav_after / amm_ref * 100) if amm_ref > 0 else 0
        
        # Status
        if improvement >= 2.0:
            status = "🟢 Excellent"
        elif improvement >= 0.3:
            status = "🟢 Good"
        elif improvement > 0:
            status = "🟡 Marginal"
        else:
            status = "🔴 Poor"
        
        md = f"""
### **{self.scenario_name} Orderbook**

#### 📊 Execution Result
| Metric | Value |
|--------|-------|
| **Split - Orderbook** | {ob_in / 10**decimals_in:.4f} ({ob_pct}%) |
| **Split - AMM** | {amm_in / 10**decimals_in:.4f} ({amm_pct}%) |
| **Total Output** | ${total_out / 10**decimals_out:,.2f} |
| **AMM Baseline** | ${amm_ref / 10**decimals_out:,.2f} |
| **Savings (Before Fee)** | +${sav_before / 10**decimals_out:.2f} |
| **Savings (After Fee)** | +${sav_after / 10**decimals_out:.2f} |
| **Improvement** | +{improvement:.3f}% |
| **Status** | {status} |

"""
        return md
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Generate dict for CSV export"""
        split = self.results.get('split', {})
        total_in = int(split.get('amount_in_total', 0))
        ob_in = int(split.get('amount_in_on_orderbook', 0))
        
        amm_ref = int(self.results.get('amm_reference_out', 0))
        total_out = int(self.results.get('expected_total_out', 0))
        sav_after = int(self.results.get('savings_after_fee', 0))
        
        decimals_out = self.config.get('decimals_out', 6)
        
        ob_pct = (ob_in * 100 // total_in) if total_in > 0 else 0
        improvement = (sav_after / amm_ref * 100) if amm_ref > 0 else 0
        
        return {
            'Scenario': self.scenario_name,
            'OB Split (%)': ob_pct,
            'Total Output ($)': f"{total_out/10**decimals_out:.2f}",
            'Savings ($)': f"{sav_after/10**decimals_out:.2f}",
            'Improvement (%)': f"{improvement:.3f}"
        }


# Example usage function
def run_backtest_and_generate_report():
    """Example: Run backtest and generate report"""
    
    print("\n" + "=" * 80)
    print("📊 BACKTEST REPORT GENERATOR EXAMPLE")
    print("=" * 80 + "\n")
    
    from services.amm_uniswap_v3.uniswap_v3 import get_price_for_pool, get_pool_tokens_and_decimals
    from services.orderbook import SyntheticOrderbookGenerator
    from services.matching import GreedyMatcher
    from services.execution.core.execution_plan import ExecutionPlanBuilder
    
    # Setup
    pool_address = '0x6c561B446416E1A00E8E93E221854d6eA4171372'
    pool_data = get_price_for_pool(pool_address)
    token_info = get_pool_tokens_and_decimals(pool_address)
    
    price_amm = pool_data['price_eth_per_usdt']
    decimals_in = token_info['decimals0']  # ETH
    decimals_out = token_info['decimals1']  # USDC
    swap_amount = 1 * 10**18  # 1 ETH
    
    scenarios = ['small', 'medium', 'large']
    all_results = []
    
    print("Running backtests...\n")
    
    for scenario in scenarios:
        print(f"Testing {scenario.upper()} scenario...")
        
        # Generate orderbook
        generator = SyntheticOrderbookGenerator(price_amm, decimals_in, decimals_out)
        levels = generator.generate(scenario, swap_amount, is_bid=True)
        
        # Match
        matcher = GreedyMatcher(price_amm, decimals_in, decimals_out, 5)
        match_result = matcher.match(levels, swap_amount, is_bid=True)
        
        # Build plan
        builder = ExecutionPlanBuilder(price_amm, decimals_in, decimals_out, 3000, 100)
        plan = builder.build_plan(
            match_result,
            '0x4200000000000000000000000000000000000006',  # ETH
            '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',  # USDC
            8, 200
        )
        
        # Generate report
        config = {
            'decimals_in': decimals_in,
            'decimals_out': decimals_out,
            'swap_amount': swap_amount,
            'price_amm': str(price_amm)
        }
        
        report_gen = BacktestReportGenerator(scenario.capitalize(), config)
        report_gen.add_result(plan)
        
        all_results.append({
            'name': scenario.capitalize(),
            'markdown': report_gen.generate_markdown_section(),
            'csv_row': report_gen.to_csv_row()
        })
    
    # Print Markdown (copy to Notion)
    print("\n" + "=" * 80)
    print("📄 MARKDOWN OUTPUT (Copy to Notion)")
    print("=" * 80 + "\n")
    
    for result in all_results:
        print(result['markdown'])
    
    # Print CSV data
    print("\n" + "=" * 80)
    print("📊 CSV DATA (Import to Notion Table)")
    print("=" * 80 + "\n")
    
    print("Scenario,OB Split (%),Total Output ($),Savings ($),Improvement (%)")
    for result in all_results:
        row = result['csv_row']
        print(f"{row['Scenario']},{row['OB Split (%)']},{row['Total Output ($)']},{row['Savings ($)']},{row['Improvement (%)']}")
    
    print("\n" + "=" * 80)
    print("✅ Report generation complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_backtest_and_generate_report()
