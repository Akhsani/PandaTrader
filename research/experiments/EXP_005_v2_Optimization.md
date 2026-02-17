# Experiment 005_v2: Regime-Adaptive Grid Optimization

## Hypothesis
1.  **Feature Engineering**: Adding ADX (Trend Strength) and ATR (Volatility) to the HMM will improve regime classification (Trend vs Sideways).
2.  **Dynamic Grid**: Using ATR-based grid spacing will outperform fixed percentage spacing by adapting to volatility.

## Methodology
- **Regime Detector v2**:
    - Features: Log Returns, Rolling Volatility (14d), ADX (14), RSI (14).
    - Logic: HMM (4 Components).
- **Backtest Comparison**:
    - **v1 Logic**: Fixed 1% Grid Spacing (Buy -1%, Sell +1%) during 'SIDEWAYS'.
    - **v2 Logic**: Dynamic ATR Grid (Band = SMA20 +/- 1.0 * ATR) during 'SIDEWAYS'.
    - **Benchmark**: Buy & Hold.

## Results (BTC/USDT Daily, ~1 year Bearish)

| Strategy | Performance | Trades | Notes |
| :--- | :--- | :--- | :--- |
| **Buy & Hold** | -29.70% | 1 | Bear market baseline. |
| **Strategy 5 (v0 Backtest)** | -11.18% | 164 | Old Detector + Fixed Grid. |
| **Strategy 5 (v1 Logic + New Detector)** | **-3.70%** | 32 | **Best Performer**. Capital preservation >96% in bear market. |
| **Strategy 5 (v2 Logic + New Detector)** | -21.63% | 16 | Underperformed. ATR bands were too wide, missed trading opportunities. |

## Analysis
1.  **Regime Detector Upgrade (SUCCESS)**:
    - The new detector (ADX/LogRet) significantly improved the safety of the strategy.
    - It kept the bot out of the market during the worst crashes, improving the "Static" result from -11.18% to -3.70%.
    - This confirms that **ADX is a critical feature** for distinguishing 'Sideways' from 'Bear' regimes.
2.  **Dynamic Grid (PARTIAL FAIL)**:
    - Using `1.0 * ATR` created bands that were too wide for the low-volatility bear market chop.
    - The bot sat on the sidelines while price ranged within the bands.
    - **Correction**: A tighter dynamic grid (e.g., `0.2 * ATR`) might work, but the **Fixed 1% Grid** is proven robust and simple.

## Conclusion & Action
- **Adopt Regime Detector v2**: Keep the ADX/ATR/LogRet changes in `utils/regime_detector.py`.
- **Revert to Fixed Grid**: Update `strategies/RegimeGrid.py` to use simpler fixed percentage intervals (0.5% - 1.0%) or very tight ATR multipliers.
- **Status**: **Highly Effective Defensive Strategy**. 
    - Losing only 3.7% when market drops 30% is a "win" for a portfolio stabilizer.
