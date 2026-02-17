import ccxt
import pandas as pd
import os
import time
from datetime import datetime

def fetch_data(symbol, timeframe='1d', since_str='2023-01-01'):
    exchange = ccxt.binance()
    since = exchange.parse8601(f'{since_str}T00:00:00Z')
    
    all_ohlcv = []
    print(f"Fetching {symbol}...")
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            
            # Check if we've reached today
            if since > exchange.milliseconds():
                break
                
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            break
            
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Save to CSV
    filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
    path = os.path.join('data', 'ohlcv', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows to {path}")

if __name__ == "__main__":
    tokens = ['ARB/USDT', 'OP/USDT', 'APT/USDT', 'SUI/USDT', 'TIA/USDT']
    for token in tokens:
        fetch_data(token)
