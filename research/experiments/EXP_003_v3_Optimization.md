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

## Phase 2B Narrative Scoring (Feb 2026)

### Implementation
- Do not short if 30-day momentum > +50%
- Do not short if ADX > 40 on daily (strong directional trend)

### Backtest with Narrative Filter (ARB, OP, SUI; APT, TIA excluded)
| Token | Baseline Return | Optimized Return | Max DD (Opt) |
|-------|-----------------|------------------|--------------|
| ARB/USDT | 15.76% | 14.73% | -18.01% |
| OP/USDT | 64.44% | 62.64% | -17.87% |
| SUI/USDT | 33.68% | 32.49% | -27.95% |

**Note:** Narrative filter reduces shorts in strong momentum; optimization did not improve returns. Fixed sizing recommended.

See `EXP_Phase2B_Improvements.md` for full test report.

## Conclusion
**STATUS: CAUTION / FIXED SIZING RECOMMENDED**
- **Action**: Do NOT implement 1.5x sizing for Strategy 3 for now. Keep sizing fixed at 1.0x.
- **Action**: Always assume a funding cost "buffer" when evaluating unlock short setups.
- **Phase 2B**: Narrative filter added to avoid shorting during strong momentum/trend.
