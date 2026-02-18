# EXP_BOT_SA: RSI Oversold DCA

**Status:** Validated | **Full results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## 1. Hypothesis
**Observation:** RSI-7 < 20 indicates oversold; mean reversion often follows.
**Hypothesis:** DCA entries on RSI oversold with TP 2.5% capture mean reversion.

## 2. Methodology
- **Bot Type**: DCA
- **Indicator**: RSI-7 < 20
- **Pairs**: BTC, ETH, SOL
- **Data**: 1h OHLCV

## 3. Results

| Metric | BTC | ETH | SOL |
|--------|-----|-----|-----|
| Sharpe | 4.00 | 3.14 | 3.50 |
| MDD | 0% | 0% | 0% |
| Win Rate | 100% | 100% | 100% |
| Deals | 59 | 35 | 47 |
| Gate | PASS | PASS | PASS |

**WFA (BTC):** OOS return 207.37%, 54 trades, 100% win rate.  
**Monte Carlo:** Median equity $3,074, 0% ruin. Gate PASS.

**Commands:**
- Backtest: `python research/bot_backtests/backtest_dca_rsi.py`
- WFA: `python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT`
- MC: `python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT`

## 4. Conclusion
**Validated.** Backtest, WFA, and MC gates passed. Ready for paper trading.

## 5. 3Commas Export
Use `bots.export_config.export_to_3commas(optimized_params, 'dca')`.

## 6. Next Steps
- Paper trade on 3Commas
- Re-optimize monthly
