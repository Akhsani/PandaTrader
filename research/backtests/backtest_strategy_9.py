"""
Strategy 9: Cross-Asset Funding Rotation
Phase 2C - Z-score ranking, enter highest Z every 8h, exit when Z < 0.5.
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

S9_UNIVERSE = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'APT/USDT',
               'SUI/USDT', 'OP/USDT', 'ARB/USDT', 'TIA/USDT', 'BNB/USDT']


def load_funding_multi(symbols, days=730):
    """Load funding for multiple symbols. Fetch if missing."""
    from utils.fetch_1h_data import fetch_funding
    
    data = {}
    for sym in symbols:
        base = sym.replace('/', '_')
        paths = [f"data/funding_rates/{base}_USDT_USDT_funding.csv",
                 f"data/funding_rates/{base}_USDT_funding.csv",
                 f"data/funding_rates/{base}_funding.csv"]
        loaded = False
        for p in paths:
            if os.path.exists(p):
                df = pd.read_csv(p, index_col=0, parse_dates=True)
                fr_col = [c for c in df.columns if 'funding' in c.lower() or 'rate' in c.lower()]
                data[sym] = df[fr_col[0]] if fr_col else df.iloc[:, 0]
                loaded = True
                break
        if not loaded:
            fd = fetch_funding(sym + ':USDT', days)
            if fd is not None and not fd.empty:
                fr_col = [c for c in fd.columns if 'funding' in c.lower() or 'rate' in c.lower()]
                data[sym] = fd[fr_col[0]] if fr_col else fd.iloc[:, 0]
                os.makedirs("data/funding_rates", exist_ok=True)
                fd.to_csv(f"data/funding_rates/{base}_USDT_USDT_funding.csv")
    return data


def compute_zscore_ranking(funding_dict, window=30*3):  # 30 days * 3 (8h per day) ~ 90 periods
    """Z-score of funding rate per asset, rolling window."""
    all_ts = set()
    for s in funding_dict.values():
        all_ts.update(s.index)
    index = sorted(all_ts)
    
    zscores = {}
    for sym, series in funding_dict.items():
        aligned = series.reindex(index).ffill().fillna(0)
        mean = aligned.rolling(window, min_periods=window//2).mean()
        std = aligned.rolling(window, min_periods=window//2).std().replace(0, 1e-8)
        zscores[sym] = (aligned - mean) / std
    return pd.DataFrame(zscores)


def backtest_rotation(funding_dict, init_capital=1000, window=90, z_entry=0.3, z_exit=0.3, capital_pct=1.0):
    """Enter basis position in highest Z every 8h; exit when Z < z_exit. Fine-tuned defaults per EXP_FineTuning_Results."""
    if len(funding_dict) < 2:
        return None
    
    zdf = compute_zscore_ranking(funding_dict, window)
    zdf = zdf.dropna(how='all')
    
    capital = init_capital
    position = None  # (symbol, entry_z)
    equity = [init_capital]
    
    for i in range(window, len(zdf)):
        row = zdf.iloc[i]
        valid = row.dropna()
        if valid.empty:
            equity.append(capital)
            continue
        
        if position is not None:
            sym, _ = position
            curr_z = row.get(sym, 0)
            if pd.isna(curr_z) or curr_z < z_exit:
                funding = funding_dict[sym].reindex(zdf.index).ffill().iloc[i]
                capital += capital * float(funding) * capital_pct
                position = None
            else:
                funding = funding_dict[sym].reindex(zdf.index).ffill().iloc[i]
                capital += capital * float(funding) * capital_pct
        else:
            best = valid.idxmax()
            best_z = valid[best]
            if best_z > z_entry:
                position = (best, best_z)
        
        equity.append(capital)
    
    total_return = (capital - init_capital) / init_capital
    days = (zdf.index[-1] - zdf.index[window]).days
    apy = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
    
    eq = pd.Series(equity, index=zdf.index[window-1:window-1+len(equity)])
    peak = eq.cummax()
    max_dd = ((eq - peak) / peak.replace(0, np.nan)).min()
    
    return {'total_return': total_return, 'apy': apy, 'max_drawdown': max_dd, 'days': days}


def run():
    print("Strategy 9: Cross-Asset Funding Rotation Backtest")
    # Use available symbols (may not have all 10)
    symbols = [s for s in S9_UNIVERSE if os.path.exists(f"data/funding_rates/{s.replace('/', '_')}_USDT_USDT_funding.csv")
               or os.path.exists(f"data/funding_rates/{s.replace('/', '_')}_funding.csv")]
    if len(symbols) < 2:
        print("Fetching funding for S9 universe...")
        funding_dict = load_funding_multi(S9_UNIVERSE[:5])  # Start with 5 to avoid long fetch
        symbols = list(funding_dict.keys())
    else:
        funding_dict = load_funding_multi(symbols)
    
    if len(funding_dict) < 2:
        print("Need at least 2 assets with funding data.")
        return
    
    print(f"Assets: {list(funding_dict.keys())}")
    result = backtest_rotation(funding_dict)
    if result:
        print(f"Return: {result['total_return']:.2%} | APY: {result['apy']:.2%} | MaxDD: {result['max_drawdown']:.2%}")
    return result


if __name__ == "__main__":
    run()
