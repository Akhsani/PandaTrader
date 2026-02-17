
import ccxt
import pandas as pd
from datetime import datetime, timedelta

def check_oi_history():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    symbol = 'BTC/USDT:USDT'
    
    # Try to fetch from 1 year ago
    since = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
    
    print(f"Attempting to fetch Open Interest for {symbol} since {datetime.fromtimestamp(since/1000)}...")
    
    try:
        # Note: Method name in CCXT might vary, using what's common or generic
        # generic: fetch_open_interest_history
        oi = exchange.fetch_open_interest_history(symbol, timeframe='1h', since=since, limit=100)
        
        if oi:
            print(f"Success! Fetched {len(oi)} records.")
            print("First record:", oi[0])
            print("Last record:", oi[-1])
            
            df = pd.DataFrame(oi)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            print("\nDataFrame Head:")
            print(df[['datetime', 'openInterestValue', 'sumOpenInterestValue']].head())
        else:
            print("No data returned.")
            
    except Exception as e:
        print(f"Error: {e}")
        # Try finding the specific method if generic fails
        if hasattr(exchange, 'fetch_open_interest_history'):
            print("Method exists but failed.")
        else:
            print("Method fetch_open_interest_history does not exist on this exchange instance.")

if __name__ == "__main__":
    check_oi_history()
