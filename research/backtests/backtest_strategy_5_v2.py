import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ccxt
import talib.abstract as ta
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utils.regime_detector import CryptoRegimeDetector

def fetch_data(symbol='BTC/USDT', timeframe='1d', since_days=1000):
    """Fetch historical data from Binance"""
    print(f"Fetching {symbol} data ({since_days} days)...")
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=since_days)).isoformat())
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def simulate_grid_v1_static(price_df, initial_capital=1000):
    """v1: Static 1% Grid in Sideways"""
    capital = initial_capital
    position = 0
    trades = []
    grid_size = 0.01 
    trade_size_usd = 100 
    
    df = price_df.copy()
    
    for i in range(1, len(df)):
        timestamp = df.index[i]
        price = df.iloc[i]['close']
        prev_price = df.iloc[i-1]['close']
        regime = df.iloc[i]['regime_label']
        
        if regime == 'SIDEWAYS':
            # buy dip 1%
            if price < prev_price * (1 - grid_size) and capital >= trade_size_usd:
                amount = trade_size_usd / price
                position += amount
                capital -= trade_size_usd
                trades.append({'time': timestamp, 'side': 'buy', 'price': price, 'type': 'grid_buy'})
            
            # sell rip 1%
            elif price > prev_price * (1 + grid_size) and position * price >= trade_size_usd:
                amount = trade_size_usd / price
                position -= amount
                capital += trade_size_usd
                trades.append({'time': timestamp, 'side': 'sell', 'price': price, 'type': 'grid_sell'})

        elif regime == 'BEAR':
            if position > 0:
                # Sell all
                capital += position * price
                position = 0
                trades.append({'time': timestamp, 'side': 'sell', 'price': price, 'type': 'panic_sell'})
                
    final_value = capital + (position * df.iloc[-1]['close'])
    return final_value, trades

def simulate_grid_v2_dynamic(price_df, initial_capital=1000):
    """v2: Dynamic ATR Grid"""
    capital = initial_capital
    position = 0
    trades = []
    trade_size_usd = 100 
    
    df = price_df.copy()
    # Calculate ATR
    df['atr'] = ta.ATR(df, timeperiod=14)
    # Center line (SMA 20)
    df['center'] = df['close'].rolling(20).mean()
    
    for i in range(20, len(df)):
        timestamp = df.index[i]
        price = df.iloc[i]['close']
        regime = df.iloc[i]['regime_label']
        atr = df.iloc[i]['atr']
        center = df.iloc[i]['center']
        
        # Dynamic Grid Spacing: 1x ATR
        lower_band = center - atr
        upper_band = center + atr
        
        if regime == 'SIDEWAYS':
            # Buy at Lower Band
            if price < lower_band and capital >= trade_size_usd:
                # Check if we already bought recently? (Simple logic for now: allows multiple buys)
                amount = trade_size_usd / price
                position += amount
                capital -= trade_size_usd
                trades.append({'time': timestamp, 'side': 'buy', 'price': price, 'type': 'grid_buy'})
            
            # Sell at Upper Band
            elif price > upper_band and position * price >= trade_size_usd:
                amount = trade_size_usd / price
                position -= amount
                capital += trade_size_usd
                trades.append({'time': timestamp, 'side': 'sell', 'price': price, 'type': 'grid_sell'})

        elif regime == 'BEAR':
            if position > 0:
                capital += position * price
                position = 0
                trades.append({'time': timestamp, 'side': 'sell', 'price': price, 'type': 'panic_sell'})
                
    final_value = capital + (position * df.iloc[-1]['close'])
    return final_value, trades

def run_comparison():
    # 1. Fetch Data
    df = fetch_data('BTC/USDT', '1d', 1000) # Longer period
    
    # 2. Train/Test Split
    train_size = int(len(df) * 0.6)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]
    
    print(f"Test Period: {test_df.index[0]} to {test_df.index[-1]}")
    
    # 3. Fit Regime Detector (v2)
    print("Training HMM (v2 metrics)...")
    detector = CryptoRegimeDetector()
    detector.fit(train_df)
    
    # 4. Predict
    test_df_labeled = detector.predict(test_df)
    
    # 5. Run Simulations
    print("Running v1 Static Grid...")
    val_v1, trades_v1 = simulate_grid_v1_static(test_df_labeled)
    
    print("Running v2 Dynamic ATR Grid...")
    val_v2, trades_v2 = simulate_grid_v2_dynamic(test_df_labeled)
    
    # 6. Metrics
    bh = (test_df.iloc[-1]['close'] - test_df.iloc[0]['close']) / test_df.iloc[0]['close']
    ret_v1 = (val_v1 - 1000) / 1000
    ret_v2 = (val_v2 - 1000) / 1000
    
    print("-" * 40)
    print(f"Buy & Hold:       {bh:.2%}")
    print(f"v1 Static Grid:   {ret_v1:.2%} ({len(trades_v1)} trades)")
    print(f"v2 Dynamic Grid:  {ret_v2:.2%} ({len(trades_v2)} trades)")
    print("-" * 40)
    
    # Save regime plot
    plot_regimes(test_df_labeled, 'research/experiments/regime_v2_plot.png')

def plot_regimes(df, output_file):
    plt.figure(figsize=(15, 7))
    plt.plot(df.index, df['close'], label='Price', color='black', alpha=0.5)
    
    colors = {'BEAR': 'red', 'BULL': 'green', 'SIDEWAYS': 'blue', 'TRANSITION': 'orange'}
    for regime, color in colors.items():
        mask = df['regime_label'] == regime
        if mask.any():
            plt.scatter(df[mask].index, df[mask]['close'], color=color, label=regime, s=10)
            
    plt.title('Market Regimes (v2 Features: ADX/ATR/LogRet)')
    plt.legend()
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    run_comparison()
