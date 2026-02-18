# Strategy 8: Deep Analysis & Improvement Plan

## 1. Code & Logic Audit

### 1.1 Signal Source Inconsistency
| Component | Signal Source | Notes |
|-----------|---------------|------|
| **Backtest** | Nansen TGM flows (BTC/ETH) or synthetic (SOL) | TGM flows 422 for SOL native; always synthetic for SOL |
| **WFA** | 100% synthetic | Historical Nansen flows not fetched per window |
| **Live (WhaleAccumulation)** | Nansen Smart Money netflow (real-time) | Different API than TGM flows |

**Implication:** SOL's +144% backtest return is from **synthetic momentum proxy**, not whale data. WFA's 150% is also synthetic. We are validating a momentum strategy, not true whale accumulation for SOL.

### 1.2 Parameter Mismatch
- **Backtest default:** hold_days=7, threshold=0.5
- **WFA best:** hold_days=5, threshold=0.3
- **WhaleAccumulation:** accumulation_threshold=0.5

Backtest and live strategy use suboptimal params vs WFA-validated best.

### 1.3 Nansen Flows Column Mapping
- TGM Flows API returns: `date`, `total_inflows_count`, `total_outflows_count` (per Nansen docs)
- Code correctly checks these columns; fallback to synthetic when missing
- SOL native (`So11111...`) returns 422 — unsupported; we skip and use synthetic

### 1.4 Equity Curve / Drawdown
- During hold, equity is flat (no mark-to-market)
- Understates intra-trade drawdown; max_dd may be optimistic
- Monte Carlo uses trade-level pnl, so path-dependent DD is captured

### 1.5 Synthetic Signal Logic
- `(ret > 0) & vol_spike` — pure momentum + volume
- No trend filter (e.g. EMA50 > EMA200) — unlike S1 Weekend Momentum
- In bear markets, momentum can whipsaw; trend filter could reduce false signals

---

## 2. Improvement Plan

### 2.1 Align Params with WFA (High Impact)
- Backtest: use hold_days=5, threshold=0.3
- WhaleAccumulation: accumulation_threshold=0.3
- Add `S8_WFA_PARAMS` constant for single source of truth

### 2.2 Optional Trend Filter for Synthetic (Medium Impact)
- Add `use_trend_filter` to synthetic signal
- When True: require close > EMA200 (or EMA50 > EMA200) for signal=1
- Reduces entries in bear regimes; aligns with S1 approach

### 2.3 Asset-Specific Params (Medium Impact)
- WFA shows different assets prefer different lookbacks (5 vs 14)
- Add per-symbol override in backtest/strategy (future)

### 2.4 SOL Wrapped Token (Low Priority)
- Investigate wSOL (wrapped SOL) for Nansen TGM flows — may avoid 422
- Token address: Solana wSOL contract

### 2.5 Mark-to-Market Equity (Low Priority)
- During hold, equity = position_value + cash
- More accurate max_dd; higher implementation cost

---

## 3. Implemented Changes (This Iteration)

1. **S8_WFA_PARAMS** — hold_days=5, threshold=0.3, lookback=7
2. **Backtest** — use WFA params; add `--trend-filter`, `--allow-synthetic`
3. **WhaleAccumulation** — accumulation_threshold=0.3
4. **Synthetic signal** — optional trend filter (close > EMA200)
5. **Real data by default** — backtest uses Nansen TGM flows only; skips assets when unavailable
6. **Nansen auth** — header `apikey` (lowercase) per docs
7. **WFA** — uses Nansen when available per window; falls back to synthetic
8. **Tests** — verify load_nansen_flows_or_synthetic return (signal, source) and require_nansen behavior
