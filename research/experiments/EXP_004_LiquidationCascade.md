# EXP_004: Liquidation Cascade Bounce (v2/v3)

## 1. Hypothesis
**Observation:** Massive liquidation events often lead to V-shaped recoveries, but "blindly" buying drops is dangerous in bear markets.
**Hypothesis v3:** Combining **RSI Oversold (<30)** with **High Volume** and an **Uptrend Filter (EMA200)** will capture safe dips while avoiding crashes.
**Assumptions:** A trailing stop (ATR-based) can lock in profits during the bounce better than fixed targets.

## 2. Methodology
- **Strategy Code**: `strategies/CascadeBounce.py`
- **Data Source**: Binance Futures 1h OHLCV (2024-2026).
- **Logic v3**:
    - **Setup**: RSI < 30 + Volume > 1.5x Avg.
    - **Filter**: Close > EMA(200) (Up-trend only).
    - **Trigger**: Close crosses above EMA(9).
    - **Exit**: Stop Loss at `2 * ATR`, Trailing Stop to Breakeven after `1 * ATR`, Take Profit at `6 * ATR`.

## 3. Results (2024-2026)

### Performance by Token (v3 Logic)
| Token | Total Return | Win Rate | Trades | Notes |
|-------|--------------|----------|--------|-------|
| **BTC/USDT** | **-3.74%** | 57.14% | 7 | Low frequency. Trend filter removed many trades. Breakdown: 4 wins, 3 losses. |
| **ETH/USDT** | **+3.84%** | **87.50%** | 8 | **Profitable**. High win rate confirms the "dip buying in uptrend" thesis works for ETH. |
| **SOL/USDT** | **-5.08%** | 60.00% | 5 | Losses were larger than gains due to volatility hitting stops before targets. |

### Observations
1.  **Safety Improved**: The EMA200 uptrend filter successfully prevented the "falling knife" losses seen in v1/v2 (where SOL lost -46%).
2.  **Trade Scarcity**: The strict filters resulted in very few trades (5-8 per asset over 2 years). This is not enough volume for a primary strategy.
3.  **Profitability**: Only ETH was profitable. The strategy is essentially a "safe dip buyer" but misses the massive V-reversals in bear markets (which was the original goal).

## 4. Conclusion
**STATUS: HOLD / LOW PRIORITY**

The strategy is safe but low-yield. It functions more as a "Conservative Dip Stick" than a "Liquidation Eater."
- **Pros**: High win rate potential (87% on ETH), limited drawdown.
- **Cons**: Extremely low frequency, requires strong uptrend (misses bottoms of bear markets).

## 5. Recommendations
- **Do not deploy as standalone bot.**
- **Consider as a 'Filter'**: Use this logic to *enable* other long strategies (e.g., Grid Bot) when these conditions are met.
- **Future Work**: Investigate lower timeframes (5m/15m) to increase signal frequency.
