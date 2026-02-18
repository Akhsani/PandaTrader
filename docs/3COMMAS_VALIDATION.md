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
4. **Fill Section 4.5 tables** in `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md` with 3Commas numbers (PandaTrader baseline already filled for S-A and S-C)

**Expected PandaTrader reference (S-A backtest, full period):** Run `python research/bot_backtests/backtest_dca_rsi.py` to get your numbers. Latest (2024-02-18 to 2026-02-17): 230% total return, 82 deals, 95.1% win rate, -1.9% max drawdown. Use the same date range in 3Commas as your `data/ohlcv/BTC_USDT_1h.csv` covers.

**Gate:** Within 20% on key metrics = simulation validated. If off by more, investigate fill logic or fee calculation before paper trading.

## Steps

### 1. Export Parameters from PandaTrader

For **full-period backtest** (same period as 3Commas):

```bash
python research/bot_backtests/backtest_dca_rsi.py
```

Use `optimized_params` from the result (or from `research/results/backtests/dca/sa_BTC_USDT_*.json`). The backtest uses the same period as your data file; use that same date range in 3Commas.

### 2. Configure 3Commas Backtester

1. Log into 3Commas
2. Create a new bot (paper mode)
3. Paste the same parameters:
   - Pair: BTC/USDT
   - Period: match PandaTrader (e.g. 2024-02-18 to 2026-02-17; use same range as your `data/ohlcv/BTC_USDT_1h.csv`)
   - TP 2.5%, SL 15%, BO $25, SO $30, 4 SOs, RSI-7 < 20 trigger

### 3. Run 3Commas Backtest

- Use the same date range as PandaTrader
- Note: Total Return, Win Rate, Deals, Max Drawdown

### 4. Compare

**S-A RSI DCA:**

| Metric | PandaTrader | 3Commas | Delta |
|--------|-------------|---------|-------|
| Total Return | 230.0% | - | Fill after 3Commas run |
| Win Rate | 95.1% | - | Compare within ±5% |
| Deals | 82 | - | Compare within ±20% |
| Max Drawdown | -1.9% | - | |

**S-C BB+RSI** (optional; trigger: Close <= BB lower AND RSI < 30):

| Metric | PandaTrader | 3Commas | Delta |
|--------|-------------|---------|-------|
| Total Return | 292.2% | - | Fill after 3Commas run |
| Win Rate | 93.8% | - | Compare within ±5% |
| Deals | 113 | - | Compare within ±20% |
| Max Drawdown | -2.4% | - | |

**Gate:** Within 20% for return and win rate. If outside, investigate:
- Fee assumptions (Binance 0.1% default)
- Slippage (add `slippage_bps` if 3Commas uses different fill model)
- Order execution logic (limit vs market)

### 5. Document

Add comparison to `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md` Section 4.5 (3Commas Fidelity Check table). PandaTrader baseline already filled; add 3Commas column and Delta.

## S-C BB+RSI Fidelity Check

Same process as S-A; use a separate 3Commas bot with BB+RSI trigger:

- **Params:** TP 2.5%, SL 15%, BO $25, SO $30, 4 SOs
- **Trigger:** Close <= BB lower band AND RSI < 30 (RSI-7, BB-20)
- **PandaTrader reference:** Run `python research/bot_backtests/backtest_dca_bb_rsi.py` — latest (2024-02-18 to 2026-02-17): 292.2% return, 113 deals, 93.8% WR, -2.4% MDD

## Known Differences

- **Grid:** 3Commas may use different level crossing logic; expect small variance.
- **DCA:** Safety order timing may differ by 1 bar.
- **Slippage:** PandaTrader adds `slippage_bps` for realism; 3Commas may model differently.
