# PandaTrader: Code Review & Test Results

**Date:** February 17, 2026  
**Scope:** Full codebase review, inaccuracy fixes, backtest execution, and documentation.

---

## 1. Code Review Summary

### 1.1 Issues Found & Fixed

#### **FundingReversion Strategy – Inheritance Bug (FIXED)**
- **Location:** `strategies/FundingReversion.py`
- **Issue:** `FundingReversion` inherited from `IStrategy` but used `dataframe['regime']` in entry logic. `IStrategy` does not add regime detection, so `regime` would be undefined and cause a `KeyError`.
- **Fix:** Changed inheritance from `IStrategy` to `BaseStrategy`, which provides regime detection via `populate_indicators()`.
- **Impact:** Strategy now correctly gates longs in BEAR regime and shorts in BULL regime.

#### **Correlation Analysis – Pandas Deprecation (FIXED)**
- **Location:** `research/backtests/correlation_analysis.py`
- **Issue:** `pd.concat(..., axis=1)` triggered `Pandas4Warning` about default sort behavior.
- **Fix:** Added explicit `sort=True` to `pd.concat()`.

### 1.2 Potential Issues (Not Fixed – Design Notes)

| Location | Issue | Notes |
|---------|------|-------|
| `strategies/UnlockTrader.py` | `short_start in results.index` check | Short signals are only applied if boundary dates exist in price index. For daily data with gaps, some short windows could be skipped. Consider using `(results.index >= short_start) & (results.index <= short_end).any()` instead. |
| `strategies/WeekendMomentum.py` | `dataframe['date']` | Uses Freqtrade’s `date` column. Works with Freqtrade; standalone backtests use `df.index`. |
| `strategies/CascadeBounce.py` | `index_col='datetime'` | Assumes OHLCV CSV has a `datetime` column. Matches output of `utils/fetch_1h_data.py`. |
| `research/walk_forward/run_wfa_strategy_1.py` | `load_data_daily` uses `parse_dates=['datetime']` | Some CSVs use `date` (e.g. Strategy 3). BTC 1d data uses `datetime`; verify column names per data source. |

### 1.3 Code Quality Notes

- **Risk Manager:** `risk_manager.py` correctly handles kill switch, daily loss limit, and position sizing.
- **Regime Detector:** HMM-based regime detection with `log_ret`, `volatility`, `adx`, `trend_pos` is implemented and used consistently.
- **Backtest Utils:** `calculate_net_returns` and `get_performance_metrics` handle fees and slippage correctly.

---

## 2. Test Execution Results

### 2.1 Strategy 1 – Weekend Momentum (v2)

**Script:** `research/backtests/backtest_strategy_1_v2.py`  
**Config:** StopLoss=3%, Regime Filter=ON

| Asset | Return | Trades |
|-------|--------|--------|
| BTC/USDT | 63.21% | 100 |
| ETH/USDT | 47.52% | 62 |
| SOL/USDT | 7.13% | 79 |

**Portfolio:** 241 trades, 56.02% win rate, 0.64% avg PnL per trade, Sharpe (trade-based) 0.12.  
**Status:** PASS

---

### 2.2 Strategy 2 – Funding Reversion (v2)

**Script:** `research/backtests/backtest_strategy_2_v2.py`  
**Config:** Regime Gating ON vs OFF

| Metric | Baseline (No Filter) | Optimized (With Filter) |
|--------|----------------------|--------------------------|
| Return | -35.28% | -18.88% |
| Max Drawdown | -39.00% | -22.73% |
| Trades | 45 | 37 |

**Drawdown improvement:** 16.26 percentage points.  
**Status:** PASS

---

### 2.3 Strategy 3 – Token Unlock (v3)

**Script:** `research/backtests/backtest_strategy_3_v3.py`  
**Config:** Baseline vs Optimized (graduated sizing + funding cost)

| Token | Baseline Return | Optimized Return | Max Drawdown (Opt) |
|-------|-----------------|------------------|--------------------|
| ARB/USDT | 15.76% | 14.73% | -18.01% |
| OP/USDT | 64.44% | 62.64% | -17.87% |
| APT/USDT | -39.56% | -41.09% | -45.34% |
| SUI/USDT | 33.68% | 32.49% | -27.95% |
| TIA/USDT | -2.56% | -4.30% | -37.51% |

**Average return change:** -1.46% (optimization did not improve returns).  
**Status:** Matches experiment EXP_003 conclusion (fixed sizing recommended).

---

### 2.4 CascadeBounce Strategy

**Script:** `strategies/CascadeBounce.py`

| Asset | Trades | Win Rate | Total Return |
|-------|--------|----------|--------------|
| BTC_USDT | 7 | 57.14% | -3.74% |
| ETH_USDT | 8 | 87.50% | 3.84% |
| SOL_USDT | 5 | 60.00% | -5.08% |

**Status:** PASS

---

### 2.5 Strategy 5 – Regime Grid (v2)

**Script:** `research/backtests/backtest_strategy_5_v2.py`

| Metric | Buy & Hold | v1 Static Grid | v2 Dynamic ATR Grid |
|--------|------------|----------------|---------------------|
| Return | -29.30% | 1.34% | 0.24% |
| Trades | 1 | 5 | 6 |

**Status:** PASS

---

### 2.6 Correlation Analysis

**Script:** `research/backtests/correlation_analysis.py`

**Pearson correlation matrix:**

|            | Strat1_BTC | Strat2_BTC | Strat3_ARB |
|------------|------------|------------|------------|
| Strat1_BTC | 1.000      | 0.004      | -0.020     |
| Strat2_BTC | 0.004      | 1.000      | 0.041      |
| Strat3_ARB | -0.020     | 0.041      | 1.000      |

**Combined portfolio (equal weight):** 13.54% total return, -13.66% max drawdown, Sharpe 0.53.  
**Status:** PASS

---

### 2.7 Monte Carlo Validation

**Script:** `research/monte_carlo/run_monte_carlo.py`  
**Input:** `research/walk_forward/results/wfa_ETH_USDT.csv`

| Metric | Value |
|--------|-------|
| Simulations | 1000 |
| Median Final Equity | $1,227.33 |
| Probability of Ruin | 29.10% |
| Probability of Drawdown > 20% | 86.90% |
| 95% VaR | $647.96 |
| Worst Case Drawdown | -72.09% |

**Status:** PASS

---

### 2.8 Walk Forward Analysis (Strategy 1)

**Script:** `research/walk_forward/run_wfa_strategy_1.py --symbol BTC/USDT`

| Metric | Value |
|--------|-------|
| Total Return | 20.84% |
| Win Rate | 77.78% |
| Trades | 9 |

**Status:** PASS

---

### 2.9 Risk Manager

**Script:** `utils/risk_manager.py` (built-in example)

- Trade allowed before loss: True  
- Position size calculation: correct  
- Daily loss limit after -$400: blocks trade correctly  
**Status:** PASS

---

## 3. Experiment Summary vs Documented Results

| Experiment | Documented | Current Run | Match |
|------------|------------|-------------|-------|
| EXP_001 (Strategy 1) | 223 trades, 56.05% win rate | 241 trades, 56.02% win rate | Yes (data period differs) |
| EXP_002 (Strategy 2) | DD -34.11% → -14.84% | DD -39.00% → -22.73% | Same trend (synthetic data) |
| EXP_003 (Strategy 3) | Avg -1.46% improvement | Avg -1.46% improvement | Yes |

---

## 4. Files Modified

1. `strategies/FundingReversion.py` – Inherit from `BaseStrategy` instead of `IStrategy`.
2. `research/backtests/correlation_analysis.py` – Add `sort=True` to `pd.concat()`.

---

## 5. Recommendations

1. **Freqtrade:** Uncomment `freqtrade` in `requirements.txt` if you plan to run Freqtrade strategies directly.
2. **UnlockTrader:** Revisit the `short_start in results.index` condition; consider using a date range mask.
3. **Data:** Ensure `data/ohlcv/` paths and column names match the scripts (e.g. `datetime` vs `date`).
4. **Tests:** Add pytest and unit tests for core logic (e.g. `risk_manager`, `regime_detector`, `backtest_utils`).

---

## 6. Run Commands

```bash
# Activate venv
source venv/bin/activate

# Strategy backtests
python research/backtests/backtest_strategy_1_v2.py
python research/backtests/backtest_strategy_2_v2.py
python research/backtests/backtest_strategy_3_v3.py
python strategies/CascadeBounce.py
python research/backtests/backtest_strategy_5_v2.py

# Analysis
python research/backtests/correlation_analysis.py
python research/monte_carlo/run_monte_carlo.py
python research/walk_forward/run_wfa_strategy_1.py --symbol BTC/USDT

# Utils
python utils/risk_manager.py
```
