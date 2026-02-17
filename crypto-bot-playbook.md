# Crypto Bot Strategy Playbook: Build, Test, Deploy

## Your Setup Context
- **Capital**: <$1K test → scale up
- **Markets**: CEX (Binance) + DEX (Uniswap/Raydium)
- **Assets**: BTC, ETH, mid-cap alts
- **Infra**: DigitalOcean droplet available
- **Goal**: Consistent monthly profit, low drawdown

---

## TECH STACK (Free/Open Source Core)

### The Stack at a Glance

| Layer | Tool | Cost | Why |
|-------|------|------|-----|
| **Backtesting** | VectorBT + Freqtrade | Free | VectorBT for fast research, Freqtrade for realistic simulation |
| **Exchange API** | CCXT (Python) | Free | 107+ exchanges, unified interface |
| **Data** | Binance API + CoinGlass Free | Free | OHLCV, funding rates, OI, liquidations |
| **On-chain** | Dune Analytics Free | Free | Token unlocks, whale flows, exchange balances |
| **Signals** | CoinGlass + Coingecko API | Free tier | Funding rates, liquidation data, Fear & Greed |
| **Execution** | Freqtrade | Free | Paper trade + live trade, Telegram alerts |
| **Hosting** | DigitalOcean $6/mo droplet | $6/mo | Already have this |
| **Monitoring** | Telegram Bot API | Free | Real-time alerts and kill switches |
| **Notebooks** | Jupyter Lab | Free | Strategy research and visualization |

### Initial Setup (Day 1)

```bash
# On your DigitalOcean droplet or local machine
# Create project directory
mkdir -p ~/crypto-bot && cd ~/crypto-bot

# Python environment
python3 -m venv venv
source venv/bin/activate

# Core dependencies
pip install ccxt freqtrade vectorbt pandas numpy \
    ta-lib requests python-telegram-bot jupyter \
    hmmlearn scikit-learn matplotlib seaborn

# Alternative if ta-lib fails to install:
pip install pandas-ta  # pure Python, no C dependency

# Verify CCXT works with Binance
python3 -c "import ccxt; print(ccxt.binance().fetch_ticker('BTC/USDT')['last'])"
```

---

## THE 6 STRATEGIES: Ranked by Build Speed + Edge Strength

I've distilled the research into 6 testable strategies, ordered by how fast you can build and validate them. Each has a clear hypothesis, data source, backtest approach, and deployment path.

---

## STRATEGY 1: Weekend Momentum Premium
**Build time: 1-2 days | Edge confidence: HIGH (academic paper)**

### The Hypothesis
Crypto returns on weekends (Sat-Sun) significantly exceed weekday returns, with higher Sharpe ratios and lower drawdowns. Academic data shows BTC weekend daily returns of 0.0023 vs 0.0012 weekdays. For DOGE, $1 weekend-only grew to $4.92 vs $2.13 weekday-only.

### Why It Works (First Principles)
- TradFi desks are closed → less institutional selling pressure
- Retail FOMO peaks on weekends → buying pressure
- Market makers widen spreads → momentum runs further before mean-reverting
- Lower liquidity = larger moves per unit of volume

### Data Needed
- BTC/ETH/alt OHLCV daily candles (Binance free API, 2+ years)
- Day-of-week labels

### Backtest Code (VectorBT)

```python
import vectorbt as vbt
import pandas as pd
import numpy as np
from datetime import datetime

# Fetch data
btc = vbt.CCXTData.download(
    symbols="BTC/USDT",
    exchange="binance",
    start="2022-01-01",
    end="2026-02-01",
    timeframe="1d"
).get("Close")

# Weekend filter: buy Friday close, sell Sunday close
is_friday = btc.index.dayofweek == 4   # Friday
is_monday = btc.index.dayofweek == 0   # Monday (exit)

entries = is_friday
exits = is_monday

# Run backtest
pf = vbt.Portfolio.from_signals(
    btc,
    entries=entries,
    exits=exits,
    init_cash=1000,
    fees=0.001,  # 0.1% per trade
    freq="1D"
)

print(f"Total Return: {pf.total_return():.2%}")
print(f"Sharpe Ratio: {pf.sharpe_ratio():.2f}")
print(f"Max Drawdown: {pf.max_drawdown():.2%}")
print(f"Win Rate: {pf.trades.win_rate():.2%}")
print(f"Trade Count: {pf.trades.count()}")

# Compare vs buy-and-hold
bh = vbt.Portfolio.from_holding(btc, init_cash=1000, freq="1D")
print(f"\nBuy & Hold Return: {bh.total_return():.2%}")
print(f"Buy & Hold Max DD: {bh.max_drawdown():.2%}")
```

### Enhanced Version: Weekend + Trend Filter

```python
# Only take weekend trades when trend is bullish (EMA50 > EMA200)
ema50 = btc.rolling(50).mean()
ema200 = btc.rolling(200).mean()
bullish_trend = ema50 > ema200

# Combined signal: weekend + trend alignment
entries_filtered = is_friday & bullish_trend
exits_filtered = is_monday

pf_filtered = vbt.Portfolio.from_signals(
    btc,
    entries=entries_filtered,
    exits=exits_filtered,
    init_cash=1000,
    fees=0.001,
    freq="1D"
)

print(f"Filtered Return: {pf_filtered.total_return():.2%}")
print(f"Filtered Sharpe: {pf_filtered.sharpe_ratio():.2f}")
print(f"Filtered Max DD: {pf_filtered.max_drawdown():.2%}")
print(f"Filtered Win Rate: {pf_filtered.trades.win_rate():.2%}")
```

### Deployment as Freqtrade Strategy

```python
# File: user_data/strategies/WeekendMomentum.py
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib

class WeekendMomentum(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1d'
    can_short = False
    
    # Risk management
    stoploss = -0.03          # 3% stop loss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    
    minimal_roi = {"0": 0.05, "3": 0.02}  # 5% immediate, 2% after 3 days

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50'] = talib.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema200'] = talib.EMA(dataframe['close'], timeperiod=200)
        dataframe['day_of_week'] = dataframe['date'].dt.dayofweek
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['day_of_week'] == 4) &          # Friday
            (dataframe['ema50'] > dataframe['ema200']), # Bullish trend
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['day_of_week'] == 0),  # Monday
            'exit_long'] = 1
        return dataframe
```

### Validation Status
> For full details, see **[EXP_001: Weekend Momentum Premium (BTC)](research/experiments/EXP_001_WeekendMomentum.md)**

- **Edge**: High Win Rate (77%), Low Frequency.
- **WFA**: +20.84% Return.
- **Monte Carlo**: Low Risk (<7% Prob of Loss).
- **Status**: **Approved** (Satellite Strategy).

---

## STRATEGY 2: Funding Rate Mean Reversion
**Build time: 2-3 days | Edge confidence: VERY HIGH (peer-reviewed)**

### The Hypothesis
When perpetual funding rates hit extremes (>0.05% or <-0.03% per 8hr), they mean-revert within 1-3 funding periods. Go long spot when funding is extremely negative (shorts paying longs), short perp when funding is extremely positive.

### Why It Works
- Extreme funding = crowded positioning
- Funding payments erode the crowded side's capital
- Position unwind creates predictable price reversal
- SSRN research confirms funding rates are partially predictable at extremes

### Data Collection Script

```python
import ccxt
import pandas as pd
from datetime import datetime, timedelta

exchange = ccxt.binance({
    'options': {'defaultType': 'future'}
})

def fetch_funding_history(symbol, days=365):
    """Fetch historical funding rates from Binance Futures"""
    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    all_funding = []
    
    while since < int(datetime.now().timestamp() * 1000):
        funding = exchange.fetch_funding_rate_history(symbol, since=since, limit=1000)
        if not funding:
            break
        all_funding.extend(funding)
        since = funding[-1]['timestamp'] + 1
    
    df = pd.DataFrame(all_funding)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

# Fetch for multiple assets
symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
funding_data = {}
for sym in symbols:
    funding_data[sym] = fetch_funding_history(sym, days=730)
    print(f"{sym}: {len(funding_data[sym])} records")
```

### Backtest Logic

```python
import numpy as np

def backtest_funding_mean_reversion(price_df, funding_df, 
                                     entry_threshold=0.05,
                                     exit_threshold=0.01,
                                     risk_per_trade=0.01):
    """
    When funding > entry_threshold: expect short squeeze → go long
    When funding < -entry_threshold: expect long squeeze → go short
    Exit when funding normalizes below exit_threshold
    """
    trades = []
    position = None
    
    # Merge price and funding data
    merged = price_df.join(funding_df['fundingRate'], how='left')
    merged['fundingRate'].fillna(method='ffill', inplace=True)
    
    for i in range(1, len(merged)):
        row = merged.iloc[i]
        prev = merged.iloc[i-1]
        fr = row['fundingRate']
        price = row['close']
        
        # ENTRY: Extreme negative funding → go long (shorts paying too much)
        if position is None and fr < -entry_threshold:
            position = {
                'side': 'long',
                'entry_price': price,
                'entry_time': row.name,
                'entry_funding': fr
            }
        
        # ENTRY: Extreme positive funding → go short (longs paying too much)  
        elif position is None and fr > entry_threshold:
            position = {
                'side': 'short',
                'entry_price': price,
                'entry_time': row.name,
                'entry_funding': fr
            }
        
        # EXIT: Funding normalized
        elif position is not None:
            should_exit = abs(fr) < exit_threshold
            # Also exit on stop loss (2% adverse move)
            if position['side'] == 'long':
                pnl = (price - position['entry_price']) / position['entry_price']
                should_exit = should_exit or pnl < -0.02
            else:
                pnl = (position['entry_price'] - price) / position['entry_price']
                should_exit = should_exit or pnl < -0.02
            
            if should_exit:
                position['exit_price'] = price
                position['exit_time'] = row.name
                position['pnl'] = pnl
                trades.append(position)
                position = None
    
    trades_df = pd.DataFrame(trades)
    if len(trades_df) > 0:
        print(f"Total trades: {len(trades_df)}")
        print(f"Win rate: {(trades_df['pnl'] > 0).mean():.2%}")
        print(f"Avg PnL: {trades_df['pnl'].mean():.4%}")
        print(f"Max DD: {trades_df['pnl'].min():.4%}")
        print(f"Total return: {(1 + trades_df['pnl']).prod() - 1:.2%}")
    
    return trades_df

# Usage:
# trades = backtest_funding_mean_reversion(btc_price, btc_funding)
```

### Validation Results (Feb 2026)
> For full details, see **[EXP_002: Funding Rate Mean Reversion (ETH)](research/experiments/EXP_002_FundingReversion_ETH.md)**

- **Granularity Issue**: Backtesting on daily data (1d candles) showed few trades and mixed results (ETH +4%, SOL -20%).
- **Recommendation**: This strategy requires higher granularity (1h or 4h) to capture intraday mean reversion.
- **Action**: Strategy implementation in `strategies/FundingReversion.py` set to `1h` timeframe. Live monitor `utils/telegram_alerts.py` polls continuously.
- **WFA & Monte Carlo**: Verified +20% Return (WFA), but High Volatility Risk (Monte Carlo). Use strict risk management.

### Live Signal Monitor (Telegram Alert)

```python
import ccxt
import asyncio
from telegram import Bot

TELEGRAM_TOKEN = "your_token"
CHAT_ID = "your_chat_id"
bot = Bot(token=TELEGRAM_TOKEN)

THRESHOLDS = {
    'BTC/USDT:USDT': 0.03,   # BTC threshold (lower vol)
    'ETH/USDT:USDT': 0.04,
    'SOL/USDT:USDT': 0.05,   # SOL threshold (higher vol)
}

async def check_funding_signals():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    
    while True:
        for symbol, threshold in THRESHOLDS.items():
            try:
                funding = exchange.fetch_funding_rate(symbol)
                rate = funding['fundingRate']
                
                if abs(rate) > threshold:
                    direction = "LONG" if rate < 0 else "SHORT"
                    msg = (
                        f"🚨 FUNDING SIGNAL: {symbol}\n"
                        f"Rate: {rate:.4%} per 8hr\n"
                        f"Signal: {direction}\n"
                        f"Threshold: ±{threshold:.4%}"
                    )
                    await bot.send_message(chat_id=CHAT_ID, text=msg)
            except Exception as e:
                print(f"Error {symbol}: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes

# asyncio.run(check_funding_signals())
```

---

## STRATEGY 3: Token Unlock Event Trading
**Build time: 1-2 days | Edge confidence: HIGH (16,000 event study)**

### The Hypothesis
90% of token unlocks cause negative price pressure starting 30 days before the event. Short/exit 30 days before large unlocks (>5% supply), re-enter 14 days after. Team unlocks are the most bearish (-25%); ecosystem unlocks are slightly bullish (+1.18%).

### Data Source (Free)

```python
import requests
import pandas as pd

def get_upcoming_unlocks():
    """
    Free sources for token unlock data:
    1. TokenUnlocks.app (limited free API)
    2. DeFiLlama unlocks endpoint
    3. Manual from CoinMarketCap calendar
    """
    # DeFiLlama emissions endpoint (free, no API key)
    url = "https://api.llama.fi/emissions/breakdown"
    
    # For manual tracking, maintain a CSV:
    # token, unlock_date, amount_usd, pct_supply, recipient_type
    unlocks = pd.DataFrame({
        'token': ['ARB', 'OP', 'APT', 'SUI', 'TIA'],
        'unlock_date': ['2026-03-16', '2026-03-01', '2026-04-12', '2026-03-03', '2026-02-28'],
        'pct_supply': [3.2, 2.1, 5.8, 4.1, 7.2],
        'recipient_type': ['team', 'ecosystem', 'investor', 'team', 'investor'],
        'symbol': ['ARB/USDT', 'OP/USDT', 'APT/USDT', 'SUI/USDT', 'TIA/USDT']
    })
    unlocks['unlock_date'] = pd.to_datetime(unlocks['unlock_date'])
    
    return unlocks

def score_unlock_impact(row):
    """Score expected impact based on Keyrock research"""
    score = 0
    
    # Size impact (larger = more negative)
    if row['pct_supply'] > 5:
        score -= 3
    elif row['pct_supply'] > 2:
        score -= 2
    else:
        score -= 1
    
    # Recipient type impact
    type_impact = {
        'team': -3,       # Worst: sell as compensation
        'investor': -2,   # Bad: VC selling via OTC
        'ecosystem': +1,  # Slightly positive: growth spend
        'community': 0    # Neutral
    }
    score += type_impact.get(row['recipient_type'], -1)
    
    return score

def generate_unlock_signals(unlocks_df):
    """Generate trading signals from upcoming unlocks"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    signals = []
    
    for _, row in unlocks_df.iterrows():
        days_until = (row['unlock_date'] - today).days
        impact = score_unlock_impact(row)
        
        # 30 days before: EXIT/SHORT signal
        if 25 <= days_until <= 35 and impact < -2:
            signals.append({
                'token': row['token'],
                'action': 'EXIT_OR_SHORT',
                'reason': f"Major unlock in {days_until}d ({row['pct_supply']:.1f}% supply, {row['recipient_type']})",
                'impact_score': impact,
                'unlock_date': row['unlock_date']
            })
        
        # 14 days after: RE-ENTRY signal
        if -20 <= days_until <= -10 and impact < -2:
            signals.append({
                'token': row['token'],
                'action': 'CONSIDER_ENTRY',
                'reason': f"Post-unlock stabilization ({abs(days_until)}d after {row['pct_supply']:.1f}% unlock)",
                'impact_score': impact,
                'unlock_date': row['unlock_date']
            })
    
    return pd.DataFrame(signals)
```

### Backtest Approach

```python
def backtest_unlock_strategy(token_symbol, unlock_dates, price_data):
    """
    For each unlock event:
    1. Short 30 days before (or exit long)
    2. Cover 14 days after
    3. Measure PnL
    """
    trades = []
    
    for unlock_date in unlock_dates:
        entry_date = unlock_date - pd.Timedelta(days=30)
        exit_date = unlock_date + pd.Timedelta(days=14)
        
        # Find nearest trading dates
        try:
            entry_price = price_data.loc[entry_date:entry_date + pd.Timedelta(days=3)].iloc[0]
            exit_price = price_data.loc[exit_date:exit_date + pd.Timedelta(days=3)].iloc[0]
            
            # Short trade PnL
            pnl = (entry_price - exit_price) / entry_price
            
            trades.append({
                'unlock_date': unlock_date,
                'entry_date': entry_date,
                'exit_date': exit_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl
            })
        except IndexError:
            continue
    
    return pd.DataFrame(trades)
```

---

## STRATEGY 4: Liquidation Cascade Bounce
**Build time: 2-3 days | Edge confidence: MEDIUM-HIGH**

### The Hypothesis
After massive liquidation events (>$500M in 24hr), price bounces 5-12% within 48 hours as selling pressure exhausts and bargain hunters enter. Enter long after cascade completion (identified by funding rate flipping negative after being extreme positive).

### Signal Detection

```python
import requests
import time

class LiquidationMonitor:
    def __init__(self):
        self.coinglass_base = "https://open-api.coinglass.com/public/v2"
        # CoinGlass free tier: 100 calls/day
        
    def get_liquidation_data(self):
        """Fetch 24hr liquidation data"""
        # Alternative free source: Binance futures API
        url = "https://fapi.binance.com/fapi/v1/allForceOrders"
        # Returns recent liquidation orders
        
        # For aggregate data, use CoinGlass or scrape from their site
        pass
    
    def detect_cascade(self, 
                       liq_threshold_24h=500_000_000,  # $500M
                       funding_flip=True):
        """
        Cascade detection criteria:
        1. 24hr liquidations > threshold
        2. Funding rate was positive, now negative (long squeeze completed)
        3. Open interest dropped >15% from peak
        4. Price dropped >8% in <4 hours
        """
        # Simplified check using Binance data
        exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        
        # Check funding rate
        btc_funding = exchange.fetch_funding_rate('BTC/USDT:USDT')
        current_rate = btc_funding['fundingRate']
        
        # Check 24hr price change
        ticker = exchange.fetch_ticker('BTC/USDT:USDT')
        price_change_24h = ticker['percentage'] / 100
        
        # Check open interest
        # (Binance doesn't expose OI history easily in free API)
        # Use: exchange.fetch_open_interest('BTC/USDT:USDT')
        
        signals = {
            'funding_negative': current_rate < 0,
            'large_dump': price_change_24h < -0.08,
            'funding_rate': current_rate,
            'price_change': price_change_24h,
        }
        
        # Combined cascade score
        cascade_score = 0
        if signals['funding_negative']:
            cascade_score += 1
        if signals['large_dump']:
            cascade_score += 1
        if current_rate < -0.02:  # Extremely negative funding
            cascade_score += 1
            
        signals['cascade_score'] = cascade_score
        signals['should_enter'] = cascade_score >= 2
        
        return signals

    def post_cascade_entry(self, symbol='BTC/USDT'):
        """
        Entry logic after cascade detected:
        - Wait for 4hr candle to close GREEN after cascade
        - Entry: close of first green 4hr candle
        - Stop: below cascade low - 1%
        - Target: 50% of the dump (measured from pre-cascade high)
        """
        pass
```

### Backtest (Historical Cascade Events)

```python
# Known major liquidation events to backtest against
HISTORICAL_CASCADES = [
    {'date': '2025-10-10', 'liq_usd': 19_000_000_000, 'btc_drop': -0.15},
    {'date': '2025-02-03', 'liq_usd': 2_200_000_000, 'btc_drop': -0.08},
    {'date': '2024-08-05', 'liq_usd': 1_100_000_000, 'btc_drop': -0.12},
    {'date': '2024-04-13', 'liq_usd': 1_600_000_000, 'btc_drop': -0.10},
    # Add more from CoinGlass historical data
]

def backtest_cascade_bounce(cascades, price_data):
    """
    For each cascade:
    - Entry: 4hr after cascade bottom (when first green candle appears)
    - Stop: 2% below cascade low
    - Target: 50% retracement of the dump
    """
    results = []
    
    for event in cascades:
        cascade_date = pd.Timestamp(event['date'])
        
        # Get prices around event
        window = price_data.loc[
            cascade_date - pd.Timedelta(days=1):
            cascade_date + pd.Timedelta(days=7)
        ]
        
        if len(window) < 10:
            continue
        
        cascade_low = window['low'].min()
        pre_cascade_high = price_data.loc[
            cascade_date - pd.Timedelta(days=3):cascade_date
        ]['high'].max()
        
        # Entry: first price 2% above cascade low
        entry_price = cascade_low * 1.02
        # Target: 50% retracement
        target = cascade_low + (pre_cascade_high - cascade_low) * 0.5
        # Stop: 2% below low
        stop = cascade_low * 0.98
        
        # Check if target or stop hit first in next 7 days
        post_cascade = price_data.loc[
            cascade_date + pd.Timedelta(hours=4):
            cascade_date + pd.Timedelta(days=7)
        ]
        
        hit_target = (post_cascade['high'] >= target).any()
        hit_stop = (post_cascade['low'] <= stop).any()
        
        if hit_target and not hit_stop:
            pnl = (target - entry_price) / entry_price
        elif hit_stop:
            pnl = (stop - entry_price) / entry_price
        else:
            # Time exit at day 7
            exit_price = post_cascade.iloc[-1]['close']
            pnl = (exit_price - entry_price) / entry_price
        
        results.append({
            'date': event['date'],
            'entry': entry_price,
            'target': target,
            'stop': stop,
            'pnl': pnl,
            'hit_target': hit_target,
            'hit_stop': hit_stop
        })
    
    df = pd.DataFrame(results)
    print(f"Events: {len(df)}")
    print(f"Win rate: {(df['pnl'] > 0).mean():.0%}")
    print(f"Avg PnL: {df['pnl'].mean():.2%}")
    return df
```

---

## STRATEGY 5: Regime-Adaptive Grid Bot (HMM-Filtered)
**Build time: 3-5 days | Edge confidence: MEDIUM**

### The Hypothesis
Grid bots print money in sideways markets but die in trends. Use a Hidden Markov Model to detect regimes (bull/bear/sideways/transition), and ONLY run the grid bot during "sideways" regime. Pause during trend regimes.

### HMM Regime Detector

```python
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd

class CryptoRegimeDetector:
    def __init__(self, n_regimes=4):
        self.n_regimes = n_regimes
        self.model = None
        
    def prepare_features(self, price_df):
        """
        Features for regime detection:
        1. Daily returns
        2. Rolling volatility (14d)
        3. Return momentum (7d cumulative return)
        """
        df = price_df.copy()
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(14).std()
        df['momentum'] = df['returns'].rolling(7).sum()
        df.dropna(inplace=True)
        
        features = df[['returns', 'volatility', 'momentum']].values
        return features, df
    
    def fit(self, price_df):
        """Train HMM on historical data"""
        features, df = self.prepare_features(price_df)
        
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=1000,
            random_state=42
        )
        self.model.fit(features)
        
        # Decode states
        states = self.model.predict(features)
        df['regime'] = states
        
        # Label regimes by characteristics
        regime_stats = df.groupby('regime').agg({
            'returns': ['mean', 'std'],
            'volatility': 'mean'
        })
        
        # Sort regimes: highest mean return = bull, lowest = bear,
        # lowest vol = sideways, remaining = transition
        mean_returns = regime_stats[('returns', 'mean')]
        mean_vol = regime_stats[('volatility', 'mean')]
        
        self.regime_labels = {}
        sorted_by_return = mean_returns.sort_values()
        self.regime_labels[sorted_by_return.index[0]] = 'BEAR'
        self.regime_labels[sorted_by_return.index[-1]] = 'BULL'
        
        remaining = [i for i in range(self.n_regimes) 
                    if i not in [sorted_by_return.index[0], sorted_by_return.index[-1]]]
        remaining_vols = mean_vol[remaining].sort_values()
        self.regime_labels[remaining_vols.index[0]] = 'SIDEWAYS'
        if len(remaining) > 1:
            self.regime_labels[remaining_vols.index[1]] = 'TRANSITION'
        
        df['regime_label'] = df['regime'].map(self.regime_labels)
        
        print("\nRegime Statistics:")
        for regime, label in self.regime_labels.items():
            mask = df['regime'] == regime
            r = df.loc[mask, 'returns']
            print(f"  {label}: mean={r.mean():.4f}, std={r.std():.4f}, "
                  f"days={mask.sum()}, pct={mask.mean():.1%}")
        
        return df
    
    def current_regime(self, recent_prices):
        """Detect current regime from recent price data"""
        features, _ = self.prepare_features(recent_prices)
        if len(features) < 1:
            return 'UNKNOWN'
        
        state = self.model.predict(features[-1:])
        return self.regime_labels.get(state[0], 'UNKNOWN')

# Usage:
# detector = CryptoRegimeDetector(n_regimes=4)
# df = detector.fit(btc_daily_prices)
# current = detector.current_regime(btc_last_30d)
# if current == 'SIDEWAYS': run_grid_bot()
```

### Grid Bot (Only Active in Sideways Regime)

```python
class RegimeFilteredGrid:
    def __init__(self, exchange, symbol, 
                 grid_levels=20, 
                 grid_spacing_pct=0.01,
                 total_investment=500):
        self.exchange = exchange
        self.symbol = symbol
        self.grid_levels = grid_levels
        self.grid_spacing = grid_spacing_pct
        self.investment_per_grid = total_investment / grid_levels
        self.regime_detector = CryptoRegimeDetector()
        self.is_active = False
        
    def calculate_grid(self, center_price):
        """Generate grid levels around current price"""
        grids = []
        for i in range(-self.grid_levels//2, self.grid_levels//2 + 1):
            price = center_price * (1 + i * self.grid_spacing)
            side = 'buy' if i < 0 else 'sell'
            grids.append({
                'price': round(price, 2),
                'side': side,
                'amount': self.investment_per_grid / price
            })
        return grids
    
    def check_regime_and_run(self, recent_prices):
        """Main loop: check regime before placing grid orders"""
        regime = self.regime_detector.current_regime(recent_prices)
        
        if regime == 'SIDEWAYS' and not self.is_active:
            print(f"✅ Regime: {regime} → Activating grid bot")
            self.activate_grid()
            self.is_active = True
            
        elif regime != 'SIDEWAYS' and self.is_active:
            print(f"⚠️ Regime: {regime} → Deactivating grid bot")
            self.deactivate_grid()
            self.is_active = False
            
        else:
            print(f"ℹ️ Regime: {regime} | Grid active: {self.is_active}")
    
    def activate_grid(self):
        """Place grid orders"""
        ticker = self.exchange.fetch_ticker(self.symbol)
        center = ticker['last']
        grids = self.calculate_grid(center)
        
        for grid in grids:
            try:
                if grid['side'] == 'buy':
                    self.exchange.create_limit_buy_order(
                        self.symbol, grid['amount'], grid['price']
                    )
                else:
                    self.exchange.create_limit_sell_order(
                        self.symbol, grid['amount'], grid['price']
                    )
            except Exception as e:
                print(f"Order error: {e}")
    
    def deactivate_grid(self):
        """Cancel all open orders"""
        try:
            self.exchange.cancel_all_orders(self.symbol)
        except Exception as e:
            print(f"Cancel error: {e}")
```

---

## STRATEGY 6: Cross-L2 DEX Arbitrage (Advanced)
**Build time: 5-7 days | Edge confidence: HIGH but complex**

### The Hypothesis
Price disparities between the same token on different L2 DEXes (Arbitrum, Base, Optimism, zkSync) persist for 10-20 blocks. zkSync has 5x less competition with 0.25% of volume exploitable as arb.

### Scanner Architecture

```python
from web3 import Web3
import json

# L2 RPC endpoints (free tiers)
RPCS = {
    'arbitrum': 'https://arb1.arbitrum.io/rpc',
    'base': 'https://mainnet.base.org',
    'optimism': 'https://mainnet.optimism.io',
    # zkSync has free RPC too
}

# Uniswap V3 quoter addresses per chain
QUOTERS = {
    'arbitrum': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
    'base': '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',
    'optimism': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
}

QUOTER_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]')

class CrossL2Scanner:
    def __init__(self):
        self.w3_connections = {
            chain: Web3(Web3.HTTPProvider(rpc)) 
            for chain, rpc in RPCS.items()
        }
    
    def get_price(self, chain, token_in, token_out, amount_in, fee=3000):
        """Get quote from Uniswap V3 on specific L2"""
        w3 = self.w3_connections[chain]
        quoter = w3.eth.contract(
            address=Web3.to_checksum_address(QUOTERS[chain]),
            abi=QUOTER_ABI
        )
        
        try:
            amount_out = quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                amount_in,
                0
            ).call()
            return amount_out
        except Exception as e:
            return None
    
    def scan_arb_opportunity(self, token_in, token_out, amount_in):
        """Scan all L2s for price differences"""
        prices = {}
        for chain in self.w3_connections:
            price = self.get_price(chain, token_in, token_out, amount_in)
            if price:
                prices[chain] = price
        
        if len(prices) < 2:
            return None
        
        best_buy = min(prices, key=prices.get)   # Cheapest to buy
        best_sell = max(prices, key=prices.get)   # Most expensive to sell
        
        spread = (prices[best_sell] - prices[best_buy]) / prices[best_buy]
        
        # Account for bridge costs (~0.05%) and gas (~$0.02 per L2)
        net_spread = spread - 0.001  # 0.1% total cost estimate
        
        if net_spread > 0.002:  # >0.2% net profit threshold
            return {
                'buy_chain': best_buy,
                'sell_chain': best_sell,
                'spread': spread,
                'net_spread': net_spread,
                'buy_price': prices[best_buy],
                'sell_price': prices[best_sell]
            }
        
        return None
```

---

## TESTING PIPELINE: The 5-Phase Validation Framework

### Phase 1: Historical Backtest (Week 1-2)

```bash
# Freqtrade backtest command
freqtrade backtesting \
    --strategy WeekendMomentum \
    --timeframe 1d \
    --timerange 20220101-20260201 \
    --config user_data/config.json \
    --export trades

# Key metrics to check:
# - Sharpe > 1.0
# - Max drawdown < 20%  
# - Win rate > 55% (for mean reversion) or R:R > 2:1 (for momentum)
# - Profit factor > 1.5
# - 100+ trades minimum
```

### Phase 2: Walk-Forward Analysis (Week 2-3)

```python
def walk_forward_test(strategy_func, data, 
                      train_months=6, test_months=1):
    """
    Train on 6 months, test on next 1 month, roll forward.
    This catches overfitting that simple backtests miss.
    """
    results = []
    start = data.index[0]
    
    while start + pd.DateOffset(months=train_months + test_months) < data.index[-1]:
        train_end = start + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        
        train_data = data.loc[start:train_end]
        test_data = data.loc[train_end:test_end]
        
        # Train strategy params on train_data
        params = strategy_func.optimize(train_data)
        
        # Test on unseen data
        test_result = strategy_func.backtest(test_data, params)
        
        results.append({
            'train_period': f"{start.date()} to {train_end.date()}",
            'test_period': f"{train_end.date()} to {test_end.date()}",
            'test_sharpe': test_result['sharpe'],
            'test_return': test_result['total_return'],
            'test_max_dd': test_result['max_drawdown']
        })
        
        start += pd.DateOffset(months=1)
    
    df = pd.DataFrame(results)
    print(f"Walk-Forward Results:")
    print(f"  Avg Sharpe: {df['test_sharpe'].mean():.2f}")
    print(f"  % Profitable Periods: {(df['test_return'] > 0).mean():.0%}")
    print(f"  Worst Period: {df['test_return'].min():.2%}")
    print(f"  Sharpe Degradation: check if test << train")
    
    return df
```

### Phase 3: Monte Carlo Validation (Week 3)

```python
def monte_carlo_validation(trades_df, n_simulations=1000):
    """
    Shuffle trade order to test if results are robust
    or depend on specific sequence.
    """
    original_return = (1 + trades_df['pnl']).prod() - 1
    original_dd = calculate_max_drawdown(trades_df['pnl'])
    
    sim_returns = []
    sim_drawdowns = []
    
    for _ in range(n_simulations):
        shuffled = trades_df['pnl'].sample(frac=1, replace=False)
        sim_return = (1 + shuffled).prod() - 1
        sim_dd = calculate_max_drawdown(shuffled.values)
        sim_returns.append(sim_return)
        sim_drawdowns.append(sim_dd)
    
    sim_returns = np.array(sim_returns)
    
    print(f"Original Return: {original_return:.2%}")
    print(f"Monte Carlo Median: {np.median(sim_returns):.2%}")
    print(f"5th percentile: {np.percentile(sim_returns, 5):.2%}")
    print(f"95th percentile: {np.percentile(sim_returns, 95):.2%}")
    print(f"% Profitable Sims: {(sim_returns > 0).mean():.0%}")
    print(f"Worst Case DD: {np.max(sim_drawdowns):.2%}")
    
    # PASS criteria:
    # - 5th percentile still positive
    # - >80% of simulations profitable
    # - Worst case DD < 2x original DD

def calculate_max_drawdown(returns_array):
    cumulative = np.cumprod(1 + returns_array)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return abs(drawdowns.min())
```

### Phase 4: Paper Trading (Week 4-8)

```bash
# Freqtrade dry-run (paper trading with real market data)
freqtrade trade \
    --strategy WeekendMomentum \
    --config user_data/config.json \
    --dry-run \
    --dry-run-wallet 1000

# This runs 24/7, making paper trades with Telegram notifications
# Run for minimum 4-8 weeks (capture different market conditions)
```

### Phase 5: Live Micro-Deployment (Week 9+)

```python
# Freqtrade config for live (conservative)
config = {
    "stake_currency": "USDT",
    "stake_amount": 50,          # $50 per trade (5% of $1K)
    "max_open_trades": 3,        # Max 3 concurrent ($150 total)
    "tradable_balance_ratio": 0.5,  # Only use 50% of balance
    
    "exchange": {
        "name": "binance",
        "key": "YOUR_KEY",
        "secret": "YOUR_SECRET",
    },
    
    # CRITICAL: Conservative risk settings
    "unfilledtimeout": {
        "entry": 10,
        "exit": 30
    },
    "order_types": {
        "entry": "limit",        # Always limit orders (save on fees)
        "exit": "limit",
        "stoploss": "market",    # Market stop for guaranteed fill
        "stoploss_on_exchange": True
    },
    
    # Kill switch: stop bot at 15% portfolio drawdown
    "trading_mode": "spot",      # NO leverage initially
}
```

---

## RISK MANAGEMENT: Non-Negotiable Rules

```python
class RiskManager:
    """Apply to ALL strategies"""
    
    def __init__(self, total_capital=1000):
        self.total_capital = total_capital
        self.max_risk_per_trade = 0.01      # 1% = $10
        self.max_daily_loss = 0.03           # 3% = $30
        self.max_total_drawdown = 0.15       # 15% = $150 → FULL STOP
        self.daily_pnl = 0
        self.peak_equity = total_capital
        
    def can_trade(self, current_equity):
        """Check if trading is allowed"""
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        if drawdown >= self.max_total_drawdown:
            return False, f"CIRCUIT BREAKER: {drawdown:.1%} drawdown"
        
        if abs(self.daily_pnl) >= self.max_daily_loss * self.total_capital:
            return False, f"DAILY LIMIT: ${self.daily_pnl:.2f} loss today"
        
        return True, "OK"
    
    def position_size(self, entry_price, stop_price):
        """Calculate position size based on risk budget"""
        risk_amount = self.total_capital * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_price) / entry_price
        
        if price_risk == 0:
            return 0
        
        position_value = risk_amount / price_risk
        # Cap at 10% of total capital per position
        position_value = min(position_value, self.total_capital * 0.10)
        
        return position_value / entry_price  # Return quantity
```

---

## QUICK START: Your First Week Action Plan

| Day | Task | Output |
|-----|------|--------|
| **1** | Install stack (Python, CCXT, VectorBT, Freqtrade) | Working environment |
| **2** | Download 2yr BTC/ETH daily data, run Weekend Momentum backtest | First backtest results |
| **3** | Add trend filter, test across multiple assets | Filtered strategy metrics |
| **4** | Build Funding Rate data collector, run mean-reversion backtest | Second strategy results |
| **5** | Set up Telegram alerts for funding extremes + unlock calendar | Live signal monitoring |
| **6** | Walk-forward analysis on best performing strategy | Validation results |
| **7** | Deploy Freqtrade dry-run for #1 performing strategy | Paper trading begins |

### Key Decision Gates

**After Week 2 backtesting:**
- If ANY strategy shows Sharpe > 1.5 and DD < 15% → proceed to walk-forward
- If none pass → iterate parameters or try different asset pairs

**After Week 4 paper trading:**
- If paper results within 70% of backtest → proceed to micro-live
- If >40% degradation → strategy is overfit, go back to research

**After Week 8 live:**
- If profitable with <10% DD → double position sizes
- If >15% DD → stop, analyze, fix or abandon
- If break-even → run longer, the strategy may need more sample size

---

## MONITORING DASHBOARD (Telegram Bot)

```python
# daily_report.py - Run via cron at 00:00 UTC
import json

def generate_daily_report(freqtrade_state):
    """Send daily strategy performance to Telegram"""
    report = f"""
📊 Daily Bot Report - {datetime.now().strftime('%Y-%m-%d')}

💰 Portfolio: ${freqtrade_state['equity']:.2f}
📈 Daily PnL: {freqtrade_state['daily_pnl']:+.2f}%
📉 Max Drawdown: {freqtrade_state['max_dd']:.2f}%
🎯 Open Trades: {freqtrade_state['open_trades']}

Strategy Performance (30d):
  Weekend Momentum: {freqtrade_state['strat1_return']:+.2f}%
  Funding Reversion: {freqtrade_state['strat2_return']:+.2f}%
  
⚡ Regime: {freqtrade_state['current_regime']}
📡 BTC Funding Rate: {freqtrade_state['btc_funding']:.4%}

{'🔴 CIRCUIT BREAKER ACTIVE' if freqtrade_state['max_dd'] > 15 else '🟢 All Systems Normal'}
"""
    return report
```

---

## FILE STRUCTURE

```
~/crypto-bot/
├── config/
│   ├── config.json              # Freqtrade config
│   └── pairs.json               # Trading pairs list
├── data/
│   ├── funding_rates/           # Historical funding data
│   ├── unlocks/                 # Token unlock calendar
│   └── ohlcv/                   # Price data cache
├── strategies/
│   ├── WeekendMomentum.py       # Strategy 1
│   ├── FundingReversion.py      # Strategy 2
│   ├── UnlockTrader.py          # Strategy 3
│   ├── CascadeBounce.py         # Strategy 4
│   └── RegimeGrid.py            # Strategy 5
├── research/
│   ├── notebooks/               # Jupyter research notebooks
│   ├── backtests/               # VectorBT analysis scripts
│   └── walk_forward/            # Validation scripts
├── utils/
│   ├── risk_manager.py          # Risk management module
│   ├── regime_detector.py       # HMM regime detection
│   ├── telegram_alerts.py       # Alert system
│   └── data_collector.py        # Data fetching utilities
└── README.md
```