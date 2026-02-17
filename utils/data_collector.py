import ccxt
import pandas as pd
import os
import time
from datetime import datetime
import sys

# Apply DNS patch for Binance
try:
    import dns_patch
    dns_patch.apply_patch()
except ImportError:
    # If run from different directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import dns_patch
    dns_patch.apply_patch()

def fetch_ohlcv(symbol, timeframe='1d', since='2020-01-01', limit=1000):
    """
    Fetch OHLCV data from Binance and save to CSV.
    """
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'} # Use futures data
    })

    # Convert since to timestamp
    since_ts = exchange.parse8601(f"{since}T00:00:00Z")
    
    print(f"Fetching {symbol} {timeframe} data from {since}...")
    
    all_ohlcv = []
    while since_ts < exchange.milliseconds():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since_ts, limit=limit)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            since_ts = ohlcv[-1][0] + 1  # Next timestamp
            
            # Progress update
            last_date = datetime.fromtimestamp(ohlcv[-1][0]/1000)
            print(f"  Fetched up to {last_date}")
            
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            time.sleep(5)
            continue

    if not all_ohlcv:
        print("No data fetched.")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    
    # Save to CSV
    safe_symbol = symbol.replace('/', '_')
    filename = f"data/ohlcv/{safe_symbol}_{timeframe}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename)
    print(f"✅ Saved {len(df)} rows to {filename}")
    return df

if __name__ == "__main__":
    # Test fetch
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'LINK/USDT']
    for sym in symbols:
        fetch_ohlcv(sym, since='2022-01-01')
