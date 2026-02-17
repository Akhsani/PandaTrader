import logging
from datetime import datetime, timedelta

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, config: dict):
        """
        Initialize RiskManager with configuration.
        config: dictionary containing risk parameters
            - max_risk_per_trade: float (e.g., 0.01 for 1%)
            - max_daily_loss: float (e.g., 0.03 for 3%)
            - max_portfolio_drawdown: float (e.g., 0.15 for 15%)
            - initial_capital: float
        """
        self.config = config
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.01)
        self.max_daily_loss = config.get('max_daily_loss', 0.03)
        self.max_drawdown = config.get('max_portfolio_drawdown', 0.15)
        self.initial_capital = config.get('initial_capital', 1000.0)
        
        # State
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.is_kill_switch_active = False
        
    def _reset_daily_metrics(self):
        """Reset daily PnL if a new day has started."""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info(f"New day detected. Resetting daily metrics. Previous Daily PnL: {self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.last_reset_date = today

    def update_capital(self, new_capital: float):
        """Update current capital and check for drawdown."""
        self.current_capital = new_capital
        self._reset_daily_metrics()
        
        # Update Peak Capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
            
        # Check Max Drawdown Kill Switch
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if drawdown >= self.max_drawdown:
            logger.critical(f"KILL SWITCH ACTIVATED: Max Portfolio Drawdown {drawdown:.2%} exceeds limit {self.max_drawdown:.2%}")
            self.is_kill_switch_active = True
        elif self.is_kill_switch_active and drawdown < self.max_drawdown * 0.8:
            # Optional: Auto-recover if drawdown significantly improves (e.g., via manual deposit)
            # For now, require manual intervention to reset kill switch
            pass

    def record_trade_result(self, pnl_amount: float):
        """Update daily PnL stats after a closed trade."""
        self._reset_daily_metrics()
        self.daily_pnl += pnl_amount
        
        # Update capital estimate (real capital should come from exchange sync in update_capital)
        # This is a fallback/simulation update
        self.update_capital(self.current_capital + pnl_amount)

    def check_trade_allowed(self, symbol: str, strategy_name: str) -> bool:
        """
        Check if a new trade is allowed based on risk rules.
        """
        self._reset_daily_metrics()
        
        # 1. Kill Switch
        if self.is_kill_switch_active:
            logger.warning(f"Trade Blocked: Kill Switch Active (Drawdown > {self.max_drawdown:.1%})")
            return False
            
        # 2. Daily Loss Limit
        # Calculate daily loss %
        current_daily_loss_pct = -self.daily_pnl / self.initial_capital # Approx
        if self.daily_pnl < 0 and current_daily_loss_pct >= self.max_daily_loss:
            logger.warning(f"Trade Blocked: Daily Loss limit reached ({current_daily_loss_pct:.2%} >= {self.max_daily_loss:.2%})")
            return False
            
        return True

    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> float:
        """
        Calculate safe position size based on risk per trade.
        Position Size = (Account Value * Risk %) / (Entry - Stop Loss)
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0
            
        risk_amount = self.current_capital * self.max_risk_per_trade
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff == 0:
            return 0.0
            
        # Quantity to buy
        quantity = risk_amount / price_diff
        
        # Configurable Max Limit (e.g. never use more than 20% of account on one trade)
        max_position_value = self.current_capital * 0.20
        if quantity * entry_price > max_position_value:
            quantity = max_position_value / entry_price
            
        return quantity

# Example Usage
if __name__ == "__main__":
    config = {
        'max_risk_per_trade': 0.01, # 1%
        'max_daily_loss': 0.03,     # 3%
        'max_portfolio_drawdown': 0.15, # 15%
        'initial_capital': 10000.0
    }
    
    rm = RiskManager(config)
    
    # Simulating
    print(f"Trade Allowed? {rm.check_trade_allowed('BTC/USDT', 'Strategy1')}")
    
    # Calculate Size
    entry = 50000
    stop = 49000 # 2% stop distance
    qty = rm.calculate_position_size(entry, stop)
    print(f"Entry: {entry}, Stop: {stop}. Size: {qty:.4f} BTC (Value: ${qty*entry:.2f})")
    
    # Simulate Loss
    rm.record_trade_result(-400) # -4% loss on $10k
    print(f"Daily PnL: {rm.daily_pnl}")
    print(f"Trade Allowed? {rm.check_trade_allowed('BTC/USDT', 'Strategy1')}") # Should be False (-400 > -300 limit)
