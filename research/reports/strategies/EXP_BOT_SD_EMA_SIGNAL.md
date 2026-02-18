# EXP_BOT_SD: EMA 12/26 Trend Signal

**Status:** Gate Failed (improved) | **Full results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## 1. Hypothesis
**Observation:** EMA12 > EMA26 indicates uptrend.
**Hypothesis:** Long entries on trend confirmation with TP/SL capture trend moves.

## 2. Methodology
- **Bot Type**: Signal
- **Indicator**: EMA 12/26 (sustained above or crossover)
- **Trend Filter**: Optional SMA200 (only long when close > SMA200)
- **Entry Modes**: `sustained` (default) or `crossover`
- **Pair**: BTC/USDT
- **Data**: 1h OHLCV

## 3. Results

| Metric | Before | After (trend filter + TP/SL 2.5%) |
|--------|--------|-----------------------------------|
| Sharpe | -1.05 | -0.38 |
| MDD | -0.8% | -0.5% |
| Win Rate | 51.8% | 52.4% |
| Deals | 548 | 288 |
| Gate | **FAIL** | **FAIL** |

**Commands:**
- Backtest: `python research/bot_backtests/backtest_signal_ema.py`
- WFA: `python research/walk_forward/run_wfa_signal.py --strategy sd --symbol BTC/USDT`
- MC: `python research/monte_carlo/run_mc_signal.py --strategy sd --symbol BTC/USDT`

## 4. Conclusion
**Gate failed.** Trend filter (SMA200) and TP/SL 2.5% improved Sharpe from -1.05 to -0.38 and reduced chop (288 vs 548 deals). WFA param grid includes `trend_filter_sma` (0, 200), `entry_mode` (sustained, crossover). Further tuning or different indicators may be needed to pass gate.

## 5. 3Commas Export
Signal bot params map to 3Commas Signal Bot / SmartTrade.

## 6. Next Steps
- Connect TradingView webhook
- Paper trade
