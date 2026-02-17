import pandas as pd
import numpy as np

def calculate_net_returns(returns: pd.Series, signals: pd.Series, fee_per_side=0.0005, slippage_per_side=0.0005):
    """
    Adjusts returns for execution costs (fees and slippage).
    - fee_per_side: 0.05% default
    - slippage_per_side: 0.05% default
    - Total round trip drag: 0.20%
    """
    total_cost_per_trade = fee_per_side + slippage_per_side
    
    # Calculate transitions (trades)
    # 0 -> 1 (Buy), 1 -> 0 (Sell), 0 -> -1 (Short), -1 -> 0 (Cover)
    # We identify a "trade" whenever the signal changes value from non-zero or to non-zero.
    # A more robust way: abs(diff) of signals.
    
    trades = signals.diff().abs().fillna(0)
    # If signals goes from 1 to -1, that's 2 sides (exit long + enter short).
    # If signals goes from 0 to 1, that's 1 side.
    # The diff().abs() naturally handles this: 1-0=1, -1-1=2, etc.
    
    costs = trades * total_cost_per_trade
    
    # We apply costs specifically when trades occur. 
    # Usually, fees are paid at the moment of trade execution.
    # In daily data vector backtests, we usually subtract them from that day's return or 
    # simulate them as a flat drag.
    
    net_returns = returns - costs
    return net_returns

def get_performance_metrics(returns: pd.Series, annual_factor=365):
    """
    Standard performance stats.
    """
    if len(returns) == 0:
        return {}
    
    cum_returns = (1 + returns).cumprod()
    total_return = cum_returns.iloc[-1] - 1
    
    # Sharpe (daily)
    std = returns.std()
    sharpe = (returns.mean() / std * np.sqrt(annual_factor)) if std != 0 else 0
    
    # Drawdown
    cum_max = cum_returns.cummax()
    drawdown = (cum_returns - cum_max) / cum_max
    max_drawdown = drawdown.min()
    
    return {
        'total_return': total_return,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'cum_returns': cum_returns
    }
