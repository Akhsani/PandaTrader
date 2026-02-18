# EXP_006: Spot-Perp Basis Harvesting (Strategy 6)

## 1. Hypothesis
**Structural Edge:** Long spot + short perp captures funding rate yield (delta-neutral). Funding rates tend to be positive in bull markets; we receive as shorts. Basis inversion (3 consecutive negative funding) signals exit.

## 2. Methodology
- **Code**: `research/backtests/backtest_strategy_6.py`, `strategies/BasisHarvest.py`
- **Data**: Spot + perp OHLCV + funding rates (BTC, ETH, SOL), 8h resampled
- **Logic**: Enter when funding > 0; exit when 3 consecutive negative funding periods
- **Regime Guard**: Only BEAR or SIDEWAYS (never BULL — short gamma risk)

## 3. Results

### Backtest (2-year period)
| Asset | Return | APY | Max Drawdown |
|-------|--------|-----|--------------|
| BTC/USDT | 10.47% | 5.11% | -0.01% |
| ETH/USDT | 11.20% | 5.46% | -0.05% |
| SOL/USDT | 10.70% | 5.22% | -0.02% |
| **Avg** | **10.79%** | **5.22%** | **-0.03%** |

### Target vs Actual
- Target: 30%+ APY, <5% DD, Sharpe > 2.0
- Actual: ~5% APY, <0.1% DD — below yield target but very low drawdown

## 4. Conclusion
**STATUS: IMPLEMENTED**
Strategy 6 provides low-risk funding carry. Yield below target; suitable as portfolio diversifier. Regime guard (BEAR/SIDEWAYS only) implemented in BasisHarvest.py.
