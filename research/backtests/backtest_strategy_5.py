import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ccxt
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utils.regime_detector import CryptoRegimeDetector

def fetch_data(symbol='BTC/USDT', timeframe='1d', since_days=730):
    """Fetch historical data from Binance"""
    print(f"Fetching {symbol} data...")
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=since_days)).isoformat())
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
    
    # Needs loop for full history if > 1000 candles
    # For now, 1000 days is enough for initial test
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def simulate_grid_strategy(price_df, initial_capital=1000):
    """
    Simulate Grid Trading based on Regime:
    - SIDEWAYS: Active Grid (buy dips/sell rips)
    - TREND/BEAR: Cash (stop loss/take profit)
    """
    capital = initial_capital
    position = 0 # Amount of asset
    entry_price = 0
    trades = []
    
    # Grid parameters
    grid_size = 0.01 # 1% grid
    trade_size_usd = 100 
    
    df = price_df.copy()
    
    for i in range(1, len(df)):
        timestamp = df.index[i]
        price = df.iloc[i]['close']
        prev_price = df.iloc[i-1]['close']
        regime = df.iloc[i]['regime_label']
        
        # LOGIC:
        if regime == 'SIDEWAYS':
            # buy dip
            if price < prev_price * (1 - grid_size) and capital >= trade_size_usd:
                # Buy
                amount = trade_size_usd / price
                position += amount
                capital -= trade_size_usd
                trades.append({'time': timestamp, 'side': 'buy', 'price': price, 'amount': amount, 'regime': regime})
            
            # sell rip
            elif price > prev_price * (1 + grid_size) and position * price >= trade_size_usd:
                # Sell
                amount = trade_size_usd / price
                position -= amount
                capital += trade_size_usd
                trades.append({'time': timestamp, 'side': 'sell', 'price': price, 'amount': amount, 'regime': regime})

        elif regime == 'BEAR':
            # Panic sell/Close all positions to preserve capital
            if position > 0:
                # Sell all
                value = position * price
                capital += value
                trades.append({'time': timestamp, 'side': 'sell_all', 'price': price, 'amount': position, 'regime': regime})
                position = 0
                
        # BULL strategy? Maybe hold? For now, we just don't Grid. 
        # Ideally in BULL we hold, but let's stick to the "Regime Grid" definition.
        
    final_value = capital + (position * df.iloc[-1]['close'])
    return final_value, trades

def run_analysis():
    # 1. Fetch Data
    df = fetch_data('BTC/USDT', '1d', 730)
    
    # 2. Split Train/Test
    train_size = int(len(df) * 0.5)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]
    
    print(f"Train data: {len(train_df)} periods")
    print(f"Test data: {len(test_df)} periods")
    
    # 3. Fit Regime Detector
    detector = CryptoRegimeDetector()
    detector.fit(train_df)
    
    # 4. Predict on Test (Out-of-Sample)
    # Note: We are predicting whole test sequence at once here for speed.
    # In strict WFA, we would retrain or rolling predict.
    test_df_labeled = detector.predict(test_df)
    
    # 5. Simulate Strategy
    final_val, trades = simulate_grid_strategy(test_df_labeled)
    
    # 6. Metrics
    buy_hold_return = (test_df.iloc[-1]['close'] - test_df.iloc[0]['close']) / test_df.iloc[0]['close']
    strategy_return = (final_val - 1000) / 1000
    
    print("\nResults:")
    print(f"Buy & Hold Return: {buy_hold_return:.2%}")
    print(f"Strategy Return: {strategy_return:.2%}")
    print(f"Total Trades: {len(trades)}")
    
    # 7. Visualization (Optional - save to file)
    plot_regimes(test_df_labeled, output_file='research/experiments/regime_plot.png')

def plot_regimes(df, output_file):
    plt.figure(figsize=(15, 7))
    plt.plot(df.index, df['close'], label='Close Price', color='black', alpha=0.6)
    
    # Color background by regime
    colors = {'BEAR': 'red', 'BULL': 'green', 'SIDEWAYS': 'blue', 'TRANSITION': 'yellow'}
    
    # Iterate through segments to color background
    # This is slow for large DF, simplified approach:
    # Scatter plot on top?
    
    for regime, color in colors.items():
        mask = df['regime_label'] == regime
        plt.scatter(df[mask].index, df[mask]['close'], color=color, label=regime, s=10)
        
    plt.title('Market Regimes (Out-of-Sample)')
    plt.legend()
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    run_analysis()
