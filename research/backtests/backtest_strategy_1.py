import vectorbt as vbt
import pandas as pd
import numpy as np
import os
import talib
import matplotlib.pyplot as plt

def load_data(symbol, timeframe='1d'):
    """Load data from local CSV"""
    filename = f"data/ohlcv/{symbol.replace('/', '_')}_{timeframe}.csv"
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return None
    
    df = pd.read_csv(filename, index_col='datetime', parse_dates=True)
    return df

def run_strategy_1(symbol="BTC/USDT"):
    print(f"\nrunning Strategy 1: Weekend Momentum for {symbol}")
    
    # Load Data
    df = load_data(symbol)
    if df is None:
        return

    close = df['close']
    
    # --- BASIC STRATEGY: Buy Friday Close, Sell Sunday Close ---
    # In pandas/vectorbt, dayofweek: Monday=0, Sunday=6
    # Friday=4, Sunday=6 (Exit on Monday open equivalent to Sunday close often used in backtests, 
    # but let's stick to Playbook: Exit Monday Open/Close)
    
    # Playbook says: 
    # buy Friday close (entry at next open or close depending on execution)
    # sell Monday close (entry at next open or close)
    
    # VectorBT signals are typically "execute on next bar open" or "execute on close"
    # Let's assume we buy on Friday Close and sell on Monday Close.
    
    is_friday = close.index.dayofweek == 4
    is_monday = close.index.dayofweek == 0
    
    entries = is_friday
    exits = is_monday
    
    # Run Backtest
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=1000,
        fees=0.001,  # 0.1% per trade
        freq="1D"
    )
    
    print(f"--- Basic Strategy Results ---")
    print(f"Total Return: {pf.total_return():.2%}")
    print(f"Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Max Drawdown: {pf.max_drawdown():.2%}")
    print(f"Win Rate: {pf.trades.win_rate():.2%}")
    print(f"Trade Count: {pf.trades.count()}")
    
    # --- ENHANCED STRATEGY: Trend Filter (EMA50 > EMA200) ---
    # Using underlying TA-Lib for speed if available
    try:
        ema50 = talib.EMA(close.values, timeperiod=50)
        ema200 = talib.EMA(close.values, timeperiod=200)
    except:
        # Fallback to pandas rolling if talib fails (though we installed it)
        ema50 = close.rolling(50).mean()
        ema200 = close.rolling(200).mean()
        
    bullish_trend = ema50 > ema200
    
    # Entries only if Friday AND Bullish Trend
    entries_filtered = is_friday & bullish_trend
    exits_filtered = is_monday # Exit regardless of trend on Monday? Playbook implies standard exit.
    
    pf_filtered = vbt.Portfolio.from_signals(
        close,
        entries=entries_filtered,
        exits=exits_filtered, # Force exit on Monday
        init_cash=1000,
        fees=0.001,
        freq="1D"
    )
    
    print(f"--- Enhanced Strategy (Trend Filter) Results ---")
    print(f"Filtered Return: {pf_filtered.total_return():.2%}")
    print(f"Filtered Sharpe: {pf_filtered.sharpe_ratio():.2f}")
    print(f"Filtered Max Drawdown: {pf_filtered.max_drawdown():.2%}")
    print(f"Filtered Win Rate: {pf_filtered.trades.win_rate():.2%}")
    print(f"Filtered Trade Count: {pf_filtered.trades.count()}")

    # Compare vs Buy & Hold
    bh = vbt.Portfolio.from_holding(close, init_cash=1000, freq="1D")
    print(f"--- Benchmark (Buy & Hold) ---")
    print(f"Buy & Hold Return: {bh.total_return():.2%}")
    print(f"Buy & Hold Max DD: {bh.max_drawdown():.2%}")

    # --- ITERATION 1: Trend + ADX + Volatility + SL/TP ---
    print(f"--- Iteration 1 (Filters + SL/TP) ---")
    try:
        # Need High/Low for ADX/ATR
        high = df['high']
        low = df['low']
        adx = talib.ADX(high.values, low.values, close.values, timeperiod=14)
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=14)
        
        # Filters (Relaxed)
        adx_filter = adx > 15
        vol_filter = (atr / close) < 0.08
        
        entries_iter1 = is_friday & bullish_trend & adx_filter & vol_filter
        
        # Stop Loss: 3% (0.03), Take Profit: 5% (0.05)
        pf_iter1 = vbt.Portfolio.from_signals(
            close,
            entries=entries_iter1,
            exits=exits, # Exit on Monday if SL/TP didn't hit
            init_cash=1000,
            fees=0.001,
            freq="1D",
            sl_stop=0.03,
            tp_stop=0.05
        )
        
        print(f"Iter 1 Return: {pf_iter1.total_return():.2%}")
        print(f"Iter 1 Sharpe: {pf_iter1.sharpe_ratio():.2f}")
        print(f"Iter 1 Max DD: {pf_iter1.max_drawdown():.2%}")
        print(f"Iter 1 Win Rate: {pf_iter1.trades.win_rate():.2%}")
        print(f"Iter 1 Trade Count: {pf_iter1.trades.count()}")
        
    except Exception as e:
        print(f"Error in Iteration 1: {e}")

if __name__ == "__main__":
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LINK/USDT"]
    for sym in symbols:
        run_strategy_1(sym)
