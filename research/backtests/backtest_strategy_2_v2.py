import sys
import os
import pandas as pd
import numpy as np
import talib.abstract as ta
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils.regime_detector import CryptoRegimeDetector
from utils.data_loader import find_funding_path


def load_data(symbol, limit=2000):
    """
    Load 1h OHLCV and funding data. Tries local files first, then fetches via fetch_1h_data.
    Always returns 1h data to match WFA methodology (funding rate mean reversion is intraday).
    """
    ohlcv_path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    funding_path = find_funding_path(symbol)

    if os.path.exists(ohlcv_path) and funding_path:
        print(f"Loading local 1h data for {symbol}...")
        price_df = pd.read_csv(ohlcv_path, parse_dates=['datetime'], index_col='datetime')
        funding_df = pd.read_csv(funding_path, parse_dates=['datetime'], index_col='datetime')
        if 'fundingRate' not in funding_df.columns and 'funding_rate' in funding_df.columns:
            funding_df = funding_df.rename(columns={'funding_rate': 'fundingRate'})
        return price_df, funding_df

    print(f"Local 1h data not found for {symbol}. Fetching via fetch_1h_data...")
    from utils.fetch_1h_data import fetch_history, fetch_funding

    os.makedirs("data/ohlcv", exist_ok=True)
    os.makedirs("data/funding_rates", exist_ok=True)

    # Fetch 1h OHLCV (730 days to cover regime history)
    price_df = fetch_history(symbol, timeframe='1h', days=730)
    price_df.to_csv(ohlcv_path)
    print(f"Saved {len(price_df)} rows to {ohlcv_path}")

    # Fetch real funding rates (Binance Futures)
    funding_df = fetch_funding(symbol, days=730)
    if funding_df.empty or 'fundingRate' not in funding_df.columns:
        if 'funding_rate' in funding_df.columns:
            funding_df = funding_df.rename(columns={'funding_rate': 'fundingRate'})
        else:
            raise FileNotFoundError(
                f"Funding data for {symbol} is empty or missing 'fundingRate' column. "
                "Run: python utils/fetch_1h_data.py"
            )
    funding_path_out = f"data/funding_rates/{symbol.replace('/', '_')}_funding.csv"
    funding_df.to_csv(funding_path_out)
    print(f"Saved funding to {funding_path_out}")

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
        
        # Indicators (24-bar window for 1h data, matches WFA methodology)
        df['funding_mean'] = df['fundingRate'].rolling(window=24).mean()
        df['funding_std'] = df['fundingRate'].rolling(window=24).std()
        df['funding_zscore'] = (df['fundingRate'] - df['funding_mean']) / df['funding_std']
        
        # ADX
        try:
             df['adx'] = ta.ADX(df)
        except:
             df['adx'] = 0
        
        # Regime Detection (HMM on 1h data)
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
                    # Apply Exit Fee/Slippage (0.10%)
                    fee_slippage = 0.0010
                    capital_new = capital * (1 + pnl) * (1 - fee_slippage)
                    
                    trades.append({'date': date, 'pnl': pnl - fee_slippage, 'reason': reason, 'side': position['side']})
                    position = None
                    capital = capital_new
            
            # ENTRY (1h Logic)
            if not position:
                # LONG: Funding is negative (Z < -1.5)
                if z_score < -self.z_threshold:
                    if self.use_regime_filter and regime == 'BEAR':
                        continue 
                    
                    # Apply Entry Fee/Slippage (0.10%)
                    capital = capital * (1 - 0.0010)
                    position = {'side': 'long', 'entry_price': price}
                
                # SHORT
                elif z_score > self.z_threshold:
                    if self.use_regime_filter and regime == 'BULL':
                        continue
                    
                    # Apply Entry Fee/Slippage (0.10%)
                    capital = capital * (1 - 0.0010)
                    position = {'side': 'short', 'entry_price': price}
            
            equity_curve.append(capital)
            
        return capital, trades, equity_curve

def run_comparison(symbol='BTC/USDT'):
    limit = 1500

    print(f"\n--- Strategy 2 Optimization (v2): Regime Gating Test ({symbol}) ---")

    # Load Data (1h to match WFA methodology - funding reversion is intraday)
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

    # Save equity curve for correlation analysis
    safe_name = symbol.replace('/', '_')
    pd.Series(eq_opt, index=df_opt.index[-len(eq_opt):]).to_csv(f"research/backtests/equity_strat2_{safe_name}.csv")

    return {
        'symbol': symbol,
        'cap_base': cap_base,
        'cap_opt': cap_opt,
        'dd_base': dd_base,
        'dd_opt': dd_opt,
        'trades_base': len(trades_base),
        'trades_opt': len(trades_opt),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='BTC/USDT', help='Symbol to test (e.g. BTC/USDT, ETH/USDT)')
    parser.add_argument('--both', action='store_true', help='Run on both BTC and ETH (WFA showed +20%% on ETH)')
    args = parser.parse_args()

    if args.both:
        results = []
        for sym in ['BTC/USDT', 'ETH/USDT']:
            r = run_comparison(sym)
            results.append(r)
        print("\n--- MULTI-ASSET SUMMARY ---")
        for r in results:
            ret_base = (r['cap_base'] - 1000) / 1000
            ret_opt = (r['cap_opt'] - 1000) / 1000
            print(f"{r['symbol']}: Baseline {ret_base:.1%} / {r['trades_base']} trades | "
                  f"Filtered {ret_opt:.1%} / {r['trades_opt']} trades | DD {r['dd_base']:.1%} -> {r['dd_opt']:.1%}")
    else:
        run_comparison(args.symbol)
