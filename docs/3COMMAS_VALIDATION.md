# 3Commas Backtester Fidelity Check

Compare PandaTrader bot simulation results with 3Commas built-in backtester to validate fidelity within 20%. **This is the most important validation step before any real money touches the system.**

## When to Run

- Before paper trading a new strategy
- After any parameter changes
- Quarterly as part of re-validation

## S-A RSI DCA Quick Checklist (~30 min)

1. **Create S-A RSI DCA bot in 3Commas** (paper mode)
   - Pair: BTC/USDT
   - TP 2.5%, SL 15%, BO $25, SO $30, 4 SOs
   - Trigger: RSI-7 < 20
2. **Run 3Commas backtester** for Feb 2024 – Feb 2026 (match PandaTrader period)
3. **Compare:** Win rate (expect within ±5%), deal count (expect within ±20%), total return
4. **Fill Section 4.5 table** in `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md` with PandaTrader vs 3Commas numbers

**Gate:** Within 20% on key metrics = simulation validated. If off by more, investigate fill logic or fee calculation before paper trading.

## Steps

### 1. Export Parameters from PandaTrader

```bash
# Run backtest or WFA to get optimized_params
python research/bot_backtests/backtest_dca_rsi.py
# or
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT
```

Use `optimized_params` from the result (or from `research/results/backtests/{dca|grid|signal}/*.json`).

### 2. Configure 3Commas Backtester

1. Log into 3Commas
2. Create a new bot (paper mode)
3. Paste the same parameters:
   - Pair: e.g. BTC/USDT
   - Period: match PandaTrader (e.g. 2024-02-18 to 2026-02-17)
   - All DCA/Grid/Signal params from `optimized_params`

### 3. Run 3Commas Backtest

- Use the same date range as PandaTrader
- Note: Total Return, Win Rate, Deals, Max Drawdown

### 4. Compare

| Metric | PandaTrader | 3Commas | Delta |
|--------|-------------|---------|-------|
| Total Return | X% | Y% | |
| Win Rate | X% | Y% | |
| Deals | N | M | |
| Max Drawdown | X% | Y% | |

**Gate:** Within 20% for return and win rate. If outside, investigate:
- Fee assumptions (Binance 0.1% default)
- Slippage (add `slippage_bps` if 3Commas uses different fill model)
- Order execution logic (limit vs market)

### 5. Document

Add comparison to `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md` under a "3Commas Fidelity" section.

## Known Differences

- **Grid:** 3Commas may use different level crossing logic; expect small variance.
- **DCA:** Safety order timing may differ by 1 bar.
- **Slippage:** PandaTrader adds `slippage_bps` for realism; 3Commas may model differently.
