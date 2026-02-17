# EXP_004: Liquidation Cascade Bounce

## 1. Hypothesis
**Observation:** Massive liquidation events (>$500M) often lead to price capitulation followed by a V-shaped recovery.
**Hypothesis:** Entering a long position after a "cascade" (defined by >5% drop and negative funding flip) will capture a 5-12% bounce.
**Assumptions:** Funding rates reliably flip negative at the bottom of a cascade.

## 2. Methodology
- **Strategy Code**: `strategies/CascadeBounce.py`
- **Data Source**: Binance Futures 1h OHLCV + Funding Rates (2024-2026).
- **Detection Logic**:
    - Price Drop: >5% in 24h.
    - Funding: Negative (< -0.01%).
    - Entry: Close of first GREEN 1h candle after signal.
    - Stop Loss: 2% below cascade low.
    - Target: 50% retracement of the dump.

## 3. Results (2024-2026)

### Performance by Token (With Filters)
| Token | Total Return | Win Rate | Trades | Notes |
|-------|--------------|----------|--------|-------|
| **BTC/USDT** | **0.00%** | 0% | 0 | Strict filters removed all trades. Without filters: 1 trade (+0.29%). |
| **ETH/USDT** | **0.00%** | 0% | 0 | Strict filters removed all trades. Without filters: 5 trades (-6%). |
| **SOL/USDT** | **-13.91%** | **0%** | 4 | All 4 trades hit stop loss. "Falling knife" scenario. |

### Observations
1.  **Rare Signal**: Genuine "Liquidation Cascades" with funding flips are rarer than expected in the 2024-2026 period using 1h data.
2.  **False Bottoms**: When signals did trigger (especially on SOL), the price often continued to drop, hitting the tight 2% stop loss immediately.
3.  **Funding Lag**: Funding rates often remained positive/neutral during the crash, only flipping negative *after* the bounce or not at all (on Binance USDT perps).

## 4. Conclusion
**STATUS: REJECTED / NEEDS REWORK**

The simple "Cascade Bounce" strategy failed to generate profit. The primary issues are:
- **Timing**: Entering on the first green candle often resulted in buying a "dead cat bounce" before further downside.
- **Stop Loss**: The 2% trailing stop is too tight for high-volatility cascade events.
- **Signal Quality**: Funding rate flips alone are insufficient to confirm the bottom.

## 5. Recommendations
- **Do not deploy** in current form.
- **Possible Improvements**:
    - Use **Open Interest (OI)** data to confirm capitulation (OI wipeout > 20%).
    - Widen Stop Loss to volatility-based (ATR) rather than fixed %.
    - Use lower timeframe (5m/15m) for more precise entry, or wait for a "higher low" market structure confirmation.
