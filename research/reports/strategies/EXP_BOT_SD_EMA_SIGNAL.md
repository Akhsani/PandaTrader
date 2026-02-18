# EXP_BOT_SD: EMA 12/26 Trend Signal

**Status:** Gate Failed | **Full results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## 1. Hypothesis
**Observation:** EMA12 > EMA26 indicates uptrend.
**Hypothesis:** Long entries on trend confirmation with TP/SL capture trend moves.

## 2. Methodology
- **Bot Type**: Signal
- **Indicator**: EMA 12/26 crossover
- **Pair**: BTC/USDT
- **Data**: 1h OHLCV

## 3. Results

| Metric | Value |
|--------|-------|
| Sharpe | -1.05 |
| MDD | -0.8% |
| Win Rate | 51.8% |
| Deals | 548 |
| Gate | **FAIL** |

**Commands:**
- Backtest: `python research/bot_backtests/backtest_signal_ema.py`
- WFA: `python research/walk_forward/run_wfa_signal.py --strategy sd --symbol BTC/USDT`
- MC: `python research/monte_carlo/run_mc_signal.py --strategy sd --symbol BTC/USDT`

## 4. Conclusion
**Gate failed.** Negative Sharpe, marginal win rate. Needs: parameter tuning, trend filter (e.g. price > SMA200), or different entry logic (e.g. EMA crossover instead of sustained above).

## 5. 3Commas Export
Signal bot params map to 3Commas Signal Bot / SmartTrade.

## 6. Next Steps
- Connect TradingView webhook
- Paper trade
