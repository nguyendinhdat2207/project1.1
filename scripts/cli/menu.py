"""
CLI Menu Handler - Interactive menu for orderbook management

Handles user input and menu navigation
"""

from decimal import Decimal
from services.execution.ui import VirtualOrderBook, generate_sample_cex_snapshot
from .display import OrderbookDisplay
from .utils import clear_screen, print_header, print_footer


class OrderbookCLIMenu:
    """Interactive menu for virtual orderbook CLI"""
    
    def __init__(self):
        """Initialize CLI menu"""
        self.mid_price = 2700.0
        self.swap_amount = 1.0
        self.scenario = 'medium'
        self.spread_step_bps = 10
        self.base_size = 2.0
        self.decay = 0.5
        self.capital_usd = 50000
        self.orderbook = None
        self.vob = VirtualOrderBook(mid_price=self.mid_price)
        self.display = OrderbookDisplay(self.mid_price)
    
    def print_menu(self):
        """Print main menu options"""
        print("\n" + "="*80)
        print("📊 VIRTUAL ORDERBOOK - INTERACTIVE CLI")
        print("="*80)
        print("\nMAIN MENU:")
        print("  1. Generate Orderbook")
        print("  2. View Orderbook")
        print("  3. Change Mid Price")
        print("  4. Change Swap Amount")
        print("  5. Change Scenario (small/medium/large)")
        print("  6. Change Spread Step")
        print("  7. Change Base Size")
        print("  8. Change Decay")
        print("  9. Change Capital (USD)")
        print("  10. View Settings")
        print("  11. View Summary")
        print("  12. Clear Screen")
        print("  0. Exit")
        print("\n" + "="*80)
    
    def get_menu_choice(self) -> str:
        """Get user menu choice"""
        choice = input("Enter choice (0-12): ").strip()
        return choice
    
    def generate_orderbook(self):
        """Generate orderbook based on current settings"""
        print("\n⏳ Generating orderbook...")
        
        try:
            if self.scenario == 'large':
                cex_snapshot = generate_sample_cex_snapshot(self.mid_price, num_levels=10)
                self.orderbook = self.vob.build_orderbook(
                    swap_amount=self.swap_amount,
                    scenario=self.scenario,
                    spread_step_bps=self.spread_step_bps,
                    base_size=self.base_size,
                    decay=self.decay,
                    capital_usd=self.capital_usd,
                    cex_snapshot=cex_snapshot
                )
            else:
                self.orderbook = self.vob.build_orderbook(
                    swap_amount=self.swap_amount,
                    scenario=self.scenario,
                    spread_step_bps=self.spread_step_bps,
                    base_size=self.base_size,
                    decay=self.decay
                )
            
            print("✅ Orderbook generated successfully!")
            
        except Exception as e:
            print(f"❌ Error generating orderbook: {e}")
            self.orderbook = None
    
    def view_orderbook(self):
        """Display current orderbook"""
        if not self.orderbook:
            print("\n❌ No orderbook generated. Please generate one first.")
            return
        
        self.display.display_orderbook(self.orderbook)
    
    def view_summary(self):
        """Display orderbook summary"""
        if not self.orderbook:
            print("\n❌ No orderbook generated. Please generate one first.")
            return
        
        self.display.display_summary(self.orderbook)
    
    def view_settings(self):
        """Display current settings"""
        settings = {
            'mid_price': self.mid_price,
            'swap_amount': self.swap_amount,
            'scenario': self.scenario,
            'spread_step_bps': self.spread_step_bps,
            'base_size': self.base_size,
            'decay': self.decay,
            'capital_usd': self.capital_usd
        }
        self.display.display_current_settings(settings)
    
    def change_mid_price(self):
        """Change mid price"""
        try:
            new_price = float(input("Enter new mid price (USDT/ETH): "))
            if new_price <= 0:
                print("❌ Price must be positive")
                return
            
            self.mid_price = new_price
            self.vob = VirtualOrderBook(mid_price=self.mid_price)
            self.display = OrderbookDisplay(self.mid_price)
            print(f"✅ Mid price updated to ${self.mid_price:,.2f}")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def change_swap_amount(self):
        """Change swap amount"""
        try:
            new_amount = float(input("Enter new swap amount (ETH): "))
            if new_amount <= 0:
                print("❌ Amount must be positive")
                return
            
            self.swap_amount = new_amount
            print(f"✅ Swap amount updated to {self.swap_amount:.6f} ETH")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def change_scenario(self):
        """Change scenario"""
        print("Available scenarios: small, medium, large")
        new_scenario = input("Enter scenario: ").strip().lower()
        
        if new_scenario in ['small', 'medium', 'large']:
            self.scenario = new_scenario
            print(f"✅ Scenario updated to {self.scenario}")
            self.orderbook = None  # Reset orderbook
        else:
            print("❌ Invalid scenario. Please enter: small, medium, or large")
    
    def change_spread_step(self):
        """Change spread step"""
        try:
            new_step = int(input("Enter new spread step (bps): "))
            if new_step <= 0:
                print("❌ Spread step must be positive")
                return
            
            self.spread_step_bps = new_step
            print(f"✅ Spread step updated to {self.spread_step_bps} bps")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def change_base_size(self):
        """Change base size"""
        try:
            new_size = float(input("Enter new base size (ETH): "))
            if new_size <= 0:
                print("❌ Base size must be positive")
                return
            
            self.base_size = new_size
            print(f"✅ Base size updated to {self.base_size:.2f} ETH")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def change_decay(self):
        """Change decay factor"""
        try:
            new_decay = float(input("Enter new decay factor (0-1): "))
            if not 0 < new_decay <= 1:
                print("❌ Decay must be between 0 and 1")
                return
            
            self.decay = new_decay
            print(f"✅ Decay updated to {self.decay:.2f}")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def change_capital(self):
        """Change capital (for large scenario)"""
        try:
            new_capital = float(input("Enter new capital (USD): "))
            if new_capital <= 0:
                print("❌ Capital must be positive")
                return
            
            self.capital_usd = new_capital
            print(f"✅ Capital updated to ${self.capital_usd:,.0f}")
            self.orderbook = None  # Reset orderbook
            
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    def run(self):
        """Run the interactive CLI menu"""
        while True:
            clear_screen()
            print_header("📊 VIRTUAL ORDERBOOK - INTERACTIVE CLI")
            self.print_menu()
            
            choice = self.get_menu_choice()
            
            if choice == '0':
                print("\n👋 Goodbye!")
                break
            elif choice == '1':
                self.generate_orderbook()
            elif choice == '2':
                self.view_orderbook()
            elif choice == '3':
                self.change_mid_price()
            elif choice == '4':
                self.change_swap_amount()
            elif choice == '5':
                self.change_scenario()
            elif choice == '6':
                self.change_spread_step()
            elif choice == '7':
                self.change_base_size()
            elif choice == '8':
                self.change_decay()
            elif choice == '9':
                self.change_capital()
            elif choice == '10':
                self.view_settings()
            elif choice == '11':
                self.view_summary()
            elif choice == '12':
                continue  # Clear screen happens at loop start
            else:
                print("❌ Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
