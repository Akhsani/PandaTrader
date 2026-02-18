
import pandas as pd
import numpy as np
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from utils.data_loader import load_ohlcv

def strategy_logic_1(price_df, funding_df=None, ma_fast=50, ma_slow=200, stop_loss=0.03,
                     entry_day=4, exit_day=0, symbol=''):
    """
    Strategy 1: Weekend Momentum with Trend Filter (or Mon-Wed variant)
    Default: Entries Friday Close, Exits Monday Close (entry_day=4, exit_day=0)
    Mon-Wed variant: Entries Monday Close, Exits Wednesday Close (entry_day=0, exit_day=2)
    """
    if price_df.empty:
        return None
        
    df = price_df.copy()
    close = df['close']
    
    # Calculate Indicators
    if len(close) < ma_slow + 10:
        return None

    df['ma_fast'] = close.rolling(window=ma_fast).mean()
    df['ma_slow'] = close.rolling(window=ma_slow).mean()
    
    trades = []
    position = None 
    start_idx = ma_slow
    
    for i in range(start_idx, len(df)-1):
        curr_date = df.index[i]
        curr_close = close.iloc[i]
        
        # Check Exit first (exit_day or SL)
        if position:
            pnl_pct = (curr_close - position['entry_price']) / position['entry_price']
            should_exit = False
            exit_reason = ''
            
            if pnl_pct < -stop_loss:
                should_exit = True
                exit_reason = 'Stop Loss'
            elif curr_date.dayofweek == exit_day:
                should_exit = True
                exit_reason = 'Time Exit'
                
            if should_exit:
                row = {
                    'exit_time': curr_date,
                    'pnl': pnl_pct,
                    'exit_reason': exit_reason
                }
                if symbol:
                    row['symbol'] = symbol
                trades.append(row)
                position = None
        
        # Check Entry (entry_day + Trend)
        if position is None and curr_date.dayofweek == entry_day:
            ma_f = df['ma_fast'].iloc[i]
            ma_s = df['ma_slow'].iloc[i]
            if ma_f > ma_s:
                position = {
                    'side': 'long',
                    'entry_price': curr_close,
                    'entry_time': curr_date
                }

    out = pd.DataFrame(trades)
    if not out.empty and symbol:
        out['symbol'] = symbol
    return out

def load_data_daily(symbol):
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1d.csv"
    try:
        return load_ohlcv(path)
    except FileNotFoundError:
        print(f"Data not found: {path}")
        return None

def run_wfa_for_symbol(symbol, variant='fri-mon', param_grid_base=None):
    """Run WFA for a single symbol. Returns (results_df, symbol)."""
    price = load_data_daily(symbol)
    if price is None:
        return None, symbol
    
    # Variant: fri-mon (Fri->Mon) or mon-wed (Mon->Wed)
    if variant == 'mon-wed':
        entry_day, exit_day = 0, 2
    else:
        entry_day, exit_day = 4, 0
    
    param_grid = param_grid_base or {
        'ma_fast': [10, 20, 50],
        'ma_slow': [50, 100, 200],
        'stop_loss': [0.03, 0.05, 0.10]
    }
    param_grid['entry_day'] = [entry_day]
    param_grid['exit_day'] = [exit_day]
    param_grid['symbol'] = [symbol]
    
    analyzer = WalkForwardAnalyzer(
        strategy_logic_1,
        param_grid,
        price,
        funding_df=None,
        train_window_days=365,
        test_window_days=90
    )
    return analyzer.run(), symbol


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='BTC/USDT', help='Single symbol or use --pool for all')
    parser.add_argument('--pool', action='store_true', help='Run WFA on BTC, ETH, SOL and pool results')
    parser.add_argument('--variant', choices=['fri-mon', 'mon-wed'], default='fri-mon',
                        help='fri-mon: Friday->Monday (default). mon-wed: Monday->Wednesday')
    args = parser.parse_args()

    param_grid_base = {
        'ma_fast': [10, 20, 50],
        'ma_slow': [50, 100, 200],
        'stop_loss': [0.03, 0.05, 0.10]
    }
    
    all_results = []
    
    if args.pool:
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        print(f"Running WFA for {symbols} (variant={args.variant}), pooling OOS trades...")
        for sym in symbols:
            print(f"\n--- {sym} ---")
            results, _ = run_wfa_for_symbol(sym, variant=args.variant, param_grid_base=param_grid_base)
            if results is not None and not results.empty:
                results['symbol'] = sym
                all_results.append(results)
        if all_results:
            results = pd.concat(all_results, ignore_index=True)
            results = results.sort_values('exit_time')
        else:
            results = pd.DataFrame()
    else:
        print(f"Loading daily data for {args.symbol} (variant={args.variant})...")
        results, _ = run_wfa_for_symbol(args.symbol, variant=args.variant, param_grid_base=param_grid_base)
        if results is None:
            results = pd.DataFrame()
    
    if not results.empty:
        total_return = (results['pnl'] + 1).prod() - 1
        win_rate = (results['pnl'] > 0).mean()
        
        print("\n=== Walk-Forward Result (Strategy 1) ===")
        print(f"Variant: {args.variant}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        if 'symbol' in results.columns:
            print(f"By symbol: {results.groupby('symbol').size().to_dict()}")
        
        os.makedirs("research/walk_forward/results", exist_ok=True)
        if args.pool:
            filename = f"research/walk_forward/results/wfa_strat1_pooled_{args.variant}.csv"
        else:
            filename = f"research/walk_forward/results/wfa_strat1_{args.symbol.replace('/','_')}_{args.variant}.csv"
        results.to_csv(filename)
        print(f"Saved trades to {filename}")
    else:
        print("No trades generated in WFA.")
