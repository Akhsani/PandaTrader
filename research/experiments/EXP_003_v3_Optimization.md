# Experiment 003 (v3): Token Unlock Optimization

## Hypothesis
1. **Funding Costs**: Subtracting simulated funding fees (0.03% daily) will reveal more realistic net profitability for Shorts.
2. **Graduated Sizing**: Scaling into Longs (Relief Bounces) at 1.5x during Bull Trends will capture more upside during market momentum.

## Methodology
- **Code**: `research/backtests/backtest_strategy_3_v3.py`
- **Scenarios**:
    - **Baseline**: Trend-gated, fixed sizing (Size=1.0), 0 funding cost.
    - **Optimized**: Graduated sizing (Size=1.5 for Longs in Bull), -0.03% daily funding cost for Shorts.

## Results

| Token | Baseline Return | Optimized Return | Max Drawdown (Opt) |
| :--- | :--- | :--- | :--- |
| **ARB/USDT** | 16.45% | 15.41% | -18.01% |
| **OP/USDT** | 66.13% | 64.31% | -17.53% |
| **APT/USDT** | -39.07% | -40.61% | -45.06% |
| **SUI/USDT** | 34.22% | 33.02% | -27.95% |
| **TIA/USDT** | -1.78% | -3.54% | -37.26% |
| **AVERAGE** | **15.18%** | **13.71%** | **-29.16%** |

## Analysis
1. **Funding Drag**: The consistent ~1-2% drop in returns confirms that funding costs are a non-negligible drag on the Short leg of the unlock strategy.
2. **Sizing Failure**: The 1.5x sizing multiplier for Longs in Bull trends did not provide enough outperformance to overcome the funding drag. This suggests that the "Relief Bounce" move might be too short-lived or the Bull trend filter on 1D data is not agile enough for these specific events.
3. **Altcoins Performance**: ARB, OP, and SUI remained profitable, while APT and TIA struggled.

## Conclusion
**STATUS: CAUTION / FIXED SIZING RECOMMENDED**
- **Action**: Do NOT implement 1.5x sizing for Strategy 3 for now. Keep sizing fixed at 1.0x.
- **Action**: Always assume a funding cost "buffer" when evaluating unlock short setups.
- **Logic Update**: `strategies/UnlockTrader.py` will revert to fixed sizing to prioritize safety.
