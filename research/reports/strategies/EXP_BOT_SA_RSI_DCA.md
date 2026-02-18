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

## 3. Results (Realistic — with stop_loss 15%)

| Metric | BTC | ETH | SOL |
|--------|-----|-----|-----|
| Sharpe | 0.26 | -0.95 | -1.20 |
| MDD | -1.9% | -3.9% | -4.6% |
| Win Rate | 95.1% | 90.5% | 90.0% |
| Deals | 82 | 116 | 130 |
| Gate | PASS | PASS | PASS |

**WFA (BTC):** OOS return 81.66%, 41 trades, 95.12% win rate.  
**Monte Carlo:** Median equity $1,433, 14.8% ruin, 40% prob DD>20%. Gate PASS (MC ruin < 20%).

**Commands:**
- Backtest: `python research/bot_backtests/backtest_dca_rsi.py`
- WFA: `python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT`
- MC: `python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT`

## 4. Conclusion
**Realistic.** Stop loss 15% added for realism; win rates 90–95% (was 100%). Backtest gate PASS (EV>0, WR>75%); WFA OOS 81.66%, MC ruin 14.8% (gate PASS with MC ruin < 20%). Paper trade candidate after 3Commas fidelity check.

## 5. 3Commas Export
Use `bots.export_config.export_to_3commas(optimized_params, 'dca')`.

## 6. Next Steps
- Paper trade on 3Commas
- Re-optimize monthly
