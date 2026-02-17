import sys
import os
import pandas as pd
import numpy as np
import talib.abstract as ta
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils.regime_detector import CryptoRegimeDetector

def load_data(symbol, limit=2000):
    # This function expects CSV data to be present in data/ohlcv and data/funding_rates
    # For this script, we will mock the loading or check if files exist.
    # If not, we might need to fetch data. 
    # Let's assume the user has the data from previous steps or we use ccxt to fetch if missing.
    
    # Check for local files first
    ohlcv_path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    funding_path = f"data/funding_rates/{symbol.replace('/', '_')}_funding.csv" # Standardized name
    
    if os.path.exists(ohlcv_path) and os.path.exists(funding_path):
        print(f"Loading local data for {symbol}...")
        price_df = pd.read_csv(ohlcv_path, parse_dates=['datetime'], index_col='datetime')
        funding_df = pd.read_csv(funding_path, parse_dates=['datetime'], index_col='datetime')
        return price_df, funding_df
    else:
        print(f"Local data not found for {symbol}. Fetching new data...")
        import ccxt
        exchange = ccxt.binance()
        
        # 1. Fetch Daily Data (1500 days) to cover 2022 Bear Market
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=1500)
        price_df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        price_df['datetime'] = pd.to_datetime(price_df['timestamp'], unit='ms')
        price_df.set_index('datetime', inplace=True)
        
        # 2. Synthetic Funding for Testing
        # Increased volatility to trigger Z-scores
        np.random.seed(42)
        volatility = price_df['close'].pct_change().rolling(14).std()
        # Noise increased to 0.0005 (0.05%)
        funding_rates = np.random.normal(0, 0.0005, len(price_df)) + (volatility * 0.5 * np.random.choice([1, -1], len(price_df)))
        funding_df = pd.DataFrame({'fundingRate': funding_rates}, index=price_df.index)
        
        return price_df, funding_df

class FundingBacktester:
    def __init__(self, use_regime_filter=False):
        self.detector = CryptoRegimeDetector()
        self.use_regime_filter = use_regime_filter
        self.stoploss = 0.05
        self.z_threshold = 1.5
        
    def prepare_data(self, price_df, funding_df):
        # Merge
        df = price_df.copy()
        df = df.join(funding_df[['fundingRate']])
        df['fundingRate'] = df['fundingRate'].ffill()
        
        # Indicators
        df['funding_mean'] = df['fundingRate'].rolling(window=20).mean()
        df['funding_std'] = df['fundingRate'].rolling(window=20).std()
        df['funding_zscore'] = (df['fundingRate'] - df['funding_mean']) / df['funding_std']
        
        # ADX
        try:
             df['adx'] = ta.ADX(df)
        except:
             df['adx'] = 0
        
        # Regime Detection features (On Daily Data)
        if self.use_regime_filter:
            if len(df) > 200:
                self.detector.fit(df)
                regime_df = self.detector.predict(df)
                df['regime'] = regime_df['regime_label']
                print(f"Regime Detection Complete. Counts:\n{df['regime'].value_counts()}")
            else:
                 df['regime'] = 'UNKNOWN'
        
        if self.use_regime_filter:
             print(f"Z-Score Stats:\n{df['funding_zscore'].describe()}")
                 
        return df

    def run(self, df):
        capital = 1000.0
        position = None
        trades = []
        equity_curve = [capital]
        
        for i in range(50, len(df)):
            curr_row = df.iloc[i]
            date = df.index[i]
            price = curr_row['close']
            z_score = curr_row['funding_zscore']
            regime = curr_row.get('regime', 'UNKNOWN')
            
            # EXIT
            if position:
                pnl = 0
                exit = False
                reason = ''
                
                if position['side'] == 'long':
                    pnl = (price - position['entry_price']) / position['entry_price']
                    if z_score > 0: # Mean reverted
                        exit = True
                        reason = 'Mean Rev'
                    elif pnl < -self.stoploss:
                        exit = True
                        reason = 'Stop Loss'
                else:
                    pnl = (position['entry_price'] - price) / position['entry_price']
                    if z_score < 0:
                        exit = True
                        reason = 'Mean Rev'
                    elif pnl < -self.stoploss:
                        exit = True
                        reason = 'Stop Loss'
                
                if exit:
                    capital_new = capital * (1 + pnl)
                    trades.append({'date': date, 'pnl': pnl, 'reason': reason, 'side': position['side']})
                    position = None
                    capital = capital_new
            
            # ENTRY (1D Logic)
            if not position:
                # LONG: Funding is negative (Z < -2)
                if z_score < -self.z_threshold:
                    if self.use_regime_filter and regime == 'BEAR':
                        continue 
                    position = {'side': 'long', 'entry_price': price}
                
                # SHORT
                elif z_score > self.z_threshold:
                    if self.use_regime_filter and regime == 'BULL':
                        continue
                    position = {'side': 'short', 'entry_price': price}
            
            equity_curve.append(capital)
            
        return capital, trades, equity_curve

def run_comparison():
    symbol = 'BTC/USDT'
    limit = 1500 
    
    print(f"\n--- Strategy 2 Optimization (v2): Regime Gating Test ({symbol}) ---")
    
    # Load Data (1D to ensure enough history for Regime)
    price, funding = load_data(symbol, limit)
    
    # 1. Baseline Run
    tester_base = FundingBacktester(use_regime_filter=False)
    df_base = tester_base.prepare_data(price, funding)
    cap_base, trades_base, eq_base = tester_base.run(df_base)
    
    # 2. Optimized Run
    tester_opt = FundingBacktester(use_regime_filter=True)
    df_opt = tester_opt.prepare_data(price, funding)
    cap_opt, trades_opt, eq_opt = tester_opt.run(df_opt)
    
    # Stats Calculation
    def get_max_dd(eq_curve):
        ts = pd.Series(eq_curve)
        cum_max = ts.cummax()
        dd = (ts - cum_max) / cum_max
        return dd.min()

    dd_base = get_max_dd(eq_base)
    dd_opt = get_max_dd(eq_opt)
    
    print("\n--- RESULTS ---")
    print(f"BASELINE (No Filter): Return={(cap_base-1000)/1000:.2%} | MaxDD={dd_base:.2%} | Trades={len(trades_base)}")
    print(f"OPTIMIZED (With Filter): Return={(cap_opt-1000)/1000:.2%} | MaxDD={dd_opt:.2%} | Trades={len(trades_opt)}")
    
    improvement = dd_opt - dd_base 
    print(f"Drawdown Improvement: {abs(dd_opt - dd_base):.2%} points")
    
    if dd_opt > dd_base: 
        print("SUCCESS: Optimized version has smaller drawdown.")
    else:
        print("FAIL: Optimized version did not reduce drawdown.")

if __name__ == "__main__":
    run_comparison()
