# EXP_009: Cross-Asset Funding Rotation (Strategy 9)

## 1. Hypothesis
**Structural Edge:** Rotate basis positions across assets based on Z-score of funding rate. Enter highest Z every 8h; exit when Z < 0.5. Improves yield over single-asset S6.

## 2. Methodology
- **Code**: `research/backtests/backtest_strategy_9.py`
- **Data**: Funding rates for 10 assets (BTC, ETH, SOL, AVAX, APT, SUI, OP, ARB, TIA, BNB)
- **Logic**: Z-score ranking (rolling 30-day window); enter highest Z; exit when Z < 0.5
- **Universe**: 3 assets in initial run (BTC, ETH, SOL); expandable to 10

## 3. Results

### Backtest (available data)
| Metric | Value |
|--------|-------|
| Total Return | 0.76% |
| APY | 0.40% |
| Max Drawdown | -0.01% |
| Assets | BTC, ETH, SOL |

### Note
Yield lower than single-asset S6 in this run. Rotation logic may need tuning (entry threshold, window). Full 10-asset universe requires additional data fetch.

## 4. Conclusion
**STATUS: IMPLEMENTED**
Strategy 9 rotation engine implemented. Further optimization recommended: expand to 10 assets, tune Z thresholds.
