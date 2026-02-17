import sys
import os
import pandas as pd
import numpy as np
import talib.abstract as ta
import ccxt
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils.regime_detector import CryptoRegimeDetector

def fetch_data(symbol, timeframe, limit):
    print(f"Fetching {symbol} data ({limit} candles)...")
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    return df

class WeekendMomentumBacktester:
    def __init__(self, use_regime_filter=True):
        self.detector = CryptoRegimeDetector()
        self.use_regime_filter = use_regime_filter
        self.stoploss = 0.03 # 3%
        
    def prepare_data(self, df):
        dataframe = df.copy()
        # Indicators
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['day_of_week'] = dataframe.index.dayofweek
        
        # Fit Detector
        if self.use_regime_filter:
            if len(dataframe) > 200:
                self.detector.fit(dataframe)
                regime_df = self.detector.predict(dataframe)
                dataframe['regime'] = regime_df['regime_label']
            else:
                dataframe['regime'] = 'UNKNOWN'
                
        return dataframe

    def run_simulation(self, df):
        capital = 1000.0
        position = 0
        trades = []
        entry_price = 0
        equity_curve = [1000.0] * 200 # Initial gap
        
        for i in range(200, len(df)):
            curr_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = df.index[i]
            price = curr_row['close']
            
            # EXIT LOGIC
            if position > 0:
                # 1. Stop Loss
                if price <= entry_price * (1 - self.stoploss):
                    pnl = (price - entry_price) / entry_price
                    # Apply 0.10% Exit Cost
                    capital *= (1 + pnl) * (1 - 0.0010)
                    trades.append({'symbol': 'Asset', 'date': date, 'type': 'stop_loss', 'pnl': pnl - 0.0010})
                    position = 0
                    equity_curve.append(capital)
                    continue
                    
                # 2. Time Exit (Monday)
                if curr_row['day_of_week'] == 0: # Monday
                    pnl = (price - entry_price) / entry_price
                    # Apply 0.10% Exit Cost
                    capital *= (1 + pnl) * (1 - 0.0010)
                    trades.append({'symbol': 'Asset', 'date': date, 'type': 'exit_monday', 'pnl': pnl - 0.0010})
                    position = 0
                    equity_curve.append(capital)
                    continue
            
            # ENTRY LOGIC
            if position == 0:
                if curr_row['day_of_week'] == 4: # Friday
                    # Filters
                    is_bull_trend = curr_row['ema50'] > curr_row['ema200']
                    is_not_bear_regime = True
                    if self.use_regime_filter:
                        is_not_bear_regime = curr_row['regime'] != 'BEAR'
                        
                    if is_bull_trend and is_not_bear_regime:
                        # Apply 0.10% Entry Cost
                        capital *= (1 - 0.0010)
                        position = capital / price
                        entry_price = price

            # Track equity
            curr_equity = capital if position == 0 else position * price
            equity_curve.append(curr_equity)

        return capital, trades, pd.Series(equity_curve, index=df.index)

def run_portfolio_backtest():
    assets = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    limit = 1000 # Days
    
    total_trades = []
    
    print("\n--- Strategy 1 v2 Optimization Backtest ---")
    print(f"Config: StopLoss=3%, Regime Filter=ON")
    
    for asset in assets:
        try:
            df = fetch_data(asset, '1d', limit)
            tester = WeekendMomentumBacktester(use_regime_filter=True)
            df_processed = tester.prepare_data(df)
            final_cap, trades, equity_curve = tester.run_simulation(df_processed)
            
            # Tag trades with symbol
            for t in trades:
                t['symbol'] = asset
                
            total_trades.extend(trades)
            
            ret = (final_cap - 1000) / 1000
            print(f"{asset}: Return {ret:.2%} | Trades: {len(trades)}")

            # Save equity curve for correlation analysis
            os.makedirs("research/backtests", exist_ok=True)
            equity_curve.to_csv(f"research/backtests/equity_strat1_{asset.replace('/', '_')}.csv")
            
        except Exception as e:
            print(f"Error testing {asset}: {e}")

    # Aggregated Stats
    if not total_trades:
        print("No trades generated.")
        return

    trade_df = pd.DataFrame(total_trades)
    print("\n--- Portfolio Aggregated Stats ---")
    print(f"Total Trades: {len(trade_df)}")
    
    win_rate = len(trade_df[trade_df['pnl'] > 0]) / len(trade_df)
    avg_pnl = trade_df['pnl'].mean()
    total_return_sum = trade_df['pnl'].sum()
    
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Avg PnL per Trade: {avg_pnl:.2%}")
    
    # Sharpe Ratio (Approx Daily)
    # Group by date to see portfolio daily volatility
    # This is a simplification
    print(f"Sharpe (Trade-based): {trade_df['pnl'].mean() / trade_df['pnl'].std():.2f}")


if __name__ == "__main__":
    run_portfolio_backtest()
