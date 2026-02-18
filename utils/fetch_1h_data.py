
import ccxt
import pandas as pd
import os
import time
from datetime import datetime, timedelta

def fetch_history(symbol, timeframe='1h', days=730):
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    
    all_ohlcv = []
    while since < exchange.milliseconds():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            break
            
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def fetch_perp_ohlcv(symbol, timeframe='1h', days=730):
    """Fetch perpetual futures OHLCV (for basis calculation: spot - perp)."""
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    all_ohlcv = []
    while since < exchange.milliseconds():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"Error fetching perp {symbol}: {e}")
            break
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df


def fetch_spot_perp_basis_data(symbol, timeframe='1h', days=730):
    """
    Fetch spot + perp OHLCV + funding for basis harvesting (S6).
    Returns (merged_df with spot_close, perp_close, basis, funding_rate).
    """
    spot = fetch_history(symbol, timeframe, days)
    perp = fetch_perp_ohlcv(symbol, timeframe, days)
    funding_sym = symbol + ':USDT' if ':' not in symbol else symbol
    funding = fetch_funding(funding_sym, days)
    
    if spot is None or spot.empty or perp is None or perp.empty:
        return None
    
    # Align on index (resample to 8h for funding if needed - Binance funding every 8h)
    spot = spot[['close']].rename(columns={'close': 'spot_close'})
    perp = perp[['close']].rename(columns={'close': 'perp_close'})
    
    merged = spot.join(perp, how='inner')
    merged['basis'] = (merged['spot_close'] - merged['perp_close']) / merged['perp_close']
    
    if funding is not None and not funding.empty:
        fr_col = 'fundingRate' if 'fundingRate' in funding.columns else funding.columns[0]
        funding_series = funding[fr_col]
        merged = merged.join(funding_series.rename('funding_rate'), how='left')
        merged['funding_rate'] = merged['funding_rate'].fillna(0)
    else:
        merged['funding_rate'] = 0.0
    
    return merged


def fetch_funding(symbol, days=730):
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    # Funding rate history
    # Note: fetch_funding_rate_history might vary by exchange support in CCXT free
    # Binance supports it.
    
    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    all_funding = []
    
    while since < int(datetime.now().timestamp() * 1000):
        try:
            funding = exchange.fetch_funding_rate_history(symbol, since=since, limit=1000)
            if not funding:
                break
            all_funding.extend(funding)
            since = funding[-1]['timestamp'] + 1
            time.sleep(0.5)
        except Exception as e:
             print(f"Error fetching funding {symbol}: {e}")
             break
             
    df = pd.DataFrame(all_funding)
    if not df.empty:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
    return df

def fetch_funding_multi(symbols, days=730):
    """Fetch funding for multiple assets (S9 Cross-Asset). Returns dict symbol -> DataFrame."""
    result = {}
    for sym in symbols:
        s = sym + ':USDT' if ':' not in sym else sym
        df = fetch_funding(s, days)
        if df is not None and not df.empty:
            result[sym] = df
    return result


if __name__ == "__main__":
    # Ensure data dirs exist
    os.makedirs("data/ohlcv", exist_ok=True)
    os.makedirs("data/funding_rates", exist_ok=True)
    
    symbols_spot = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    symbols_future = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
    # S9 universe: BTC, ETH, SOL, AVAX, APT, SUI, OP, ARB, TIA, BNB
    symbols_s9 = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'APT/USDT',
                  'SUI/USDT', 'OP/USDT', 'ARB/USDT', 'TIA/USDT', 'BNB/USDT']
    
    # 1. Fetch OHLCV (Spot prices are fine for signal, but often we trade perps. Let's use Spot for price data as proxy or Perps?)
    # Strategy says: "Go long spot ... short perp". 
    # Usually simplest to use Perp price for backtest if trading perps.
    # But let's stick to the existing pattern: fetch OHLCV.
    
    for sym in symbols_spot:
        print(f"Fetching 1h OHLCV for {sym}...")
        df = fetch_history(sym, timeframe='1h')
        filename = f"data/ohlcv/{sym.replace('/', '_')}_1h.csv"
        df.to_csv(filename)
        print(f"Saved {len(df)} rows to {filename}")
        
    # 2. Fetch Funding
    # Binance Future symbols: usually we pass 'BTC/USDT' to fetch_funding_rate_history with defaultType='future'
    for sym in symbols_future:
        print(f"Fetching Funding Rate for {sym}...")
        df = fetch_funding(sym)
        if not df.empty:
            filename = f"data/funding_rates/{sym.replace('/', '_').replace(':', '_')}_funding.csv"
            df.to_csv(filename)
            print(f"Saved {len(df)} rows to {filename}")
