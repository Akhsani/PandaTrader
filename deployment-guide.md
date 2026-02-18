# PandaTrader: Paper Trading Deployment Guide

## Quick Answers

**Python or Rust?** Stay with Python. Your strategies run on 1h/daily candles. Rust's sub-millisecond advantage is irrelevant at your timeframe. Your entire stack (Freqtrade, hmmlearn, TA-Lib, pandas) is Python. Rewriting = months of work for zero benefit.

**Separate repo or existing?** Existing repo. Add a `deploy/` folder for Docker configs. One repo, one source of truth.

**Where to deploy?** Railway (easiest) or DigitalOcean droplet (most control). Guide covers both — Railway is the primary path.

---

## Option A: Railway (Recommended — Easiest)

Railway is "Vercel for backend." Connect GitHub, push code, it deploys. No SSH, no server management, no firewall config.

**Cost:** ~$5-7/month (Hobby plan $5/mo + usage-based compute included in credits)

### Step 1: Prep Your Repo (Local, ~20 min)

#### 1a. Create a Dockerfile in your repo root

```dockerfile
# PandaTrader Dockerfile
# Based on official Freqtrade image (includes TA-Lib, Python 3.11+)
FROM freqtradeorg/freqtrade:stable

# Copy your custom code into the container
COPY utils/ /freqtrade/utils/
COPY strategies/ /freqtrade/user_data/strategies/

# Copy config (non-secret parts only — secrets go in Railway env vars)
COPY deploy/config.json /freqtrade/user_data/config.json

# Default command: dry-run with Strategy 5 (override in Railway per-service)
CMD ["trade", \
     "--config", "/freqtrade/user_data/config.json", \
     "--strategy", "RegimeGrid", \
     "--dry-run-wallet", "500"]
```

#### 1b. Fix strategy imports for container paths

In each strategy file (`WeekendMomentum.py`, `FundingReversion.py`, `RegimeGrid.py`), make sure the base_strategy import works inside the container:

```python
# At the top of each strategy file, replace:
#   from strategies.base_strategy import BaseStrategy
# with:
from base_strategy import BaseStrategy
```

In `base_strategy.py`, fix the utils import:

```python
import sys
import os

# Add possible paths for utils module
for p in ['/freqtrade', os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]:
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.risk_manager import RiskManager
from utils.regime_detector import CryptoRegimeDetector
# ... rest of file unchanged
```

#### 1c. Create the config file (no secrets in this file)

Create `deploy/config.json`:

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.95,
    "dry_run": true,
    "dry_run_wallet": 1000,
    "cancel_open_orders_on_exit": false,
    "trading_mode": "spot",
    "margin_mode": "",

    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
    },

    "order_types": {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_exit": "market",
        "force_entry": "market",
        "stoploss": "market",
        "stoploss_on_exchange": false
    },

    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "pair_whitelist": [
            "BTC/USDT",
            "ETH/USDT"
        ],
        "pair_blacklist": []
    },

    "pairlists": [
        { "method": "StaticPairList" }
    ],

    "entry_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    },

    "telegram": {
        "enabled": true,
        "token": "",
        "chat_id": "",
        "notification_settings": {
            "status": "on",
            "warning": "on",
            "startup": "on",
            "entry": "on",
            "exit": "on"
        }
    },

    "api_server": {
        "enabled": false
    },

    "bot_name": "PandaTrader-Paper",
    "initial_state": "running",
    "force_entry_enable": false,
    "internals": {
        "process_throttle_secs": 5
    }
}
```

#### 1d. Create a config overlay script for secrets

Freqtrade reads config from JSON files, but Railway injects secrets as environment variables. Bridge the gap with a small entrypoint script.

Create `deploy/entrypoint.sh`:

```bash
#!/bin/bash
# Inject Railway environment variables into Freqtrade config
# This avoids putting secrets in config.json (which is in git)

CONFIG="/freqtrade/user_data/config.json"

# Use jq to inject secrets (jq is available in the Freqtrade image)
if [ -n "$BINANCE_KEY" ]; then
    TMP=$(mktemp)
    jq --arg key "$BINANCE_KEY" --arg secret "$BINANCE_SECRET" \
       '.exchange.key = $key | .exchange.secret = $secret' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"
fi

if [ -n "$TELEGRAM_TOKEN" ]; then
    TMP=$(mktemp)
    jq --arg token "$TELEGRAM_TOKEN" --arg chat "$TELEGRAM_CHAT_ID" \
       '.telegram.token = $token | .telegram.chat_id = $chat' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"
fi

# Execute the original Freqtrade command
exec freqtrade "$@"
```

Update the Dockerfile to use this entrypoint:

```dockerfile
FROM freqtradeorg/freqtrade:stable

# Install jq for config injection (small, ~1MB)
USER root
RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*
USER ftuser

COPY utils/ /freqtrade/utils/
COPY strategies/ /freqtrade/user_data/strategies/
COPY deploy/config.json /freqtrade/user_data/config.json
COPY deploy/entrypoint.sh /freqtrade/entrypoint.sh

ENTRYPOINT ["/freqtrade/entrypoint.sh"]
CMD ["trade", \
     "--config", "/freqtrade/user_data/config.json", \
     "--strategy", "RegimeGrid", \
     "--dry-run-wallet", "500"]
```

#### 1e. Update .gitignore and commit

```gitignore
# Add these
*.sqlite
user_data/logs/
deploy/.env
__pycache__/
```

```bash
git add Dockerfile deploy/ .gitignore
git commit -m "Add Railway deployment (paper trading)"
git push origin main
```

---

### Step 2: Deploy on Railway (~10 min)

#### 2a. Create Railway account and project

1. Go to [railway.com](https://railway.com) and sign up (GitHub OAuth)
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select `Akhsani/PandaTrader`
4. Railway auto-detects your Dockerfile and starts building

#### 2b. Add environment variables (secrets)

In the Railway dashboard for your service:

1. Click **"Variables"** tab
2. Add these variables:

| Variable | Value |
|----------|-------|
| `BINANCE_KEY` | Your Binance API key (read-only is fine for dry-run) |
| `BINANCE_SECRET` | Your Binance API secret |
| `TELEGRAM_TOKEN` | Your Telegram bot token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID (from @userinfobot) |

#### 2c. Set a hard spending limit

Go to **Settings** → **Usage** → Set spending limit to **$10/month**. Railway is the only cloud provider that actually enforces this — your bot will pause (not get billed more) if you hit the limit. This is a huge safety feature.

#### 2d. Verify it's running

- Check the **Logs** tab in Railway dashboard — you should see Freqtrade boot messages
- Send `/status` to your Telegram bot
- You should see "Dry run is enabled" in the logs

---

### Step 3: Add More Strategies (Week 2+)

On Railway, each strategy runs as a separate **service** within the same project.

#### 3a. Add Strategy 1 (Weekend Momentum)

1. In your Railway project, click **"+ New"** → **"Service"** → select same GitHub repo
2. Override the start command in **Settings → Deploy → Custom Start Command**:

```
trade --config /freqtrade/user_data/config.json --strategy WeekendMomentum --dry-run-wallet 300 --db-url sqlite:///user_data/tradesv3-weekend.sqlite
```

3. Add the same environment variables (copy from first service)
4. Deploy

#### 3b. Add Strategy 2 (Funding Reversion, ETH only)

Same process, but this one needs a different config for futures mode. Create `deploy/config-funding.json` in your repo:

```json
{
    "max_open_trades": 2,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "dry_run": true,
    "dry_run_wallet": 200,
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "exchange": {
        "name": "binance",
        "pair_whitelist": ["ETH/USDT:USDT"],
        "pair_blacklist": []
    },
    "pairlists": [{ "method": "StaticPairList" }],
    "entry_pricing": { "price_side": "same", "use_order_book": true, "order_book_top": 1 },
    "exit_pricing": { "price_side": "same", "use_order_book": true, "order_book_top": 1 },
    "telegram": { "enabled": true, "token": "", "chat_id": "" },
    "api_server": { "enabled": false },
    "bot_name": "PandaTrader-Funding-ETH",
    "initial_state": "running"
}
```

Update the Dockerfile to also copy this config:

```dockerfile
COPY deploy/config-funding.json /freqtrade/user_data/config-funding.json
```

Start command for this service:

```
trade --config /freqtrade/user_data/config-funding.json --strategy FundingReversion --dry-run-wallet 200 --db-url sqlite:///user_data/tradesv3-funding.sqlite
```

---

### Step 4: Updating Strategies

When you change strategy code:

```bash
# Local machine
git add -A && git commit -m "Tune Strategy 1 parameters" && git push
```

Railway automatically redeploys all services that use the repo. That's it. No SSH, no docker restart, no server management.

---

### Step 5: Monitoring

| Method | How |
|--------|-----|
| **Telegram** | `/status`, `/profit`, `/daily`, `/balance` — works 24/7 from your phone |
| **Railway Logs** | Dashboard → Service → Logs tab (real-time streaming) |
| **Railway Metrics** | Dashboard → Service → Metrics (CPU, RAM, network) |
| **Health alerts** | Railway sends email if a service crashes and can't restart |

---

## Option B: DigitalOcean Droplet (More Control)

Use this if you want SSH access, full filesystem control, or are already comfortable with Linux servers. The full DigitalOcean guide is in the previous version of this document — the core steps are:

1. Create $6/mo droplet (Ubuntu 24, 1 vCPU, 1GB RAM)
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Clone repo: `git clone https://github.com/Akhsani/PandaTrader.git`
4. Create `config-private.json` on server (never in git)
5. `docker compose up -d`
6. Multiple strategies = multiple services in `docker-compose.yml` with separate `--db-url` each

**When to choose DO over Railway:** You want to run FreqUI (web dashboard), you need persistent SQLite databases that survive redeploys, or you want fine-grained control over networking/firewall. Railway's ephemeral filesystem means SQLite databases reset on redeploy — you'd need to use Railway's Volume feature ($0.25/GB/month) to persist them, or accept that dry-run trade history resets when you push code.

---

## Comparison: Railway vs DigitalOcean for PandaTrader

| Concern | Railway | DigitalOcean |
|---------|---------|-------------|
| **Time to first deploy** | ~15 minutes | ~45 minutes |
| **Ongoing maintenance** | Zero (auto-restarts, auto-redeploy on push) | You manage updates, security, Docker |
| **Cost** | ~$5-7/mo | $6/mo fixed |
| **Deploy new code** | `git push` | `ssh` → `git pull` → `docker compose restart` |
| **Multiple strategies** | Add service in dashboard (click) | Edit docker-compose.yml (manual) |
| **Persistent trade data** | Needs Volume ($0.25/GB) or resets on redeploy | Always persists (it's your server) |
| **FreqUI web dashboard** | Possible but needs custom domain + port exposure | Easy (localhost:8080 via SSH tunnel) |
| **SSH debug access** | No (logs only) | Full SSH |
| **Security** | Managed by Railway | You manage firewall, SSH keys, updates |
| **Spending surprises** | Hard limit enforced | Fixed price, no surprises |

---

## Deployment Timeline

| Week | Action | Platform |
|------|--------|----------|
| **Day 1** | Prep repo (Dockerfile, config, entrypoint) | Local |
| **Day 1** | Deploy Strategy 5 (Regime Grid) on BTC | Railway/DO |
| **Day 1-5** | Monitor: regime labels correct? Grid entries in SIDEWAYS only? | Telegram |
| **Week 2** | Add Strategy 1 (Weekend Momentum) on BTC/ETH | Railway/DO |
| **Week 2** | Verify: Friday entries, Monday exits, regime filter blocking BEAR | Telegram |
| **Week 3** | Add Strategy 2 (Funding Reversion) on ETH only, futures mode | Railway/DO |
| **Week 4** | Compare paper results vs backtest expectations | Manual review |
| **Week 4** | Decision gate: pull any strategy >40% worse than backtest | — |
| **Week 8** | If portfolio profitable with <15% DD → ready for live ($200) | — |

---

## Decision Gates

| Condition | Action |
|-----------|--------|
| Any service crashes >3x/day | Stop, check logs, fix, redeploy |
| Strategy 1 takes a Friday trade | Verify entry matches backtest filters (EMA50>EMA200, not BEAR, low vol) |
| Any strategy >40% worse Sharpe than backtest after 4 weeks | Pull that strategy, investigate |
| All strategies within 70% of backtest after 4 weeks | Continue to week 8 |
| Portfolio profitable + <15% DD after 8 weeks | Ready for live micro-deploy ($200 total) |
| Portfolio break-even or losing after 8 weeks | Extend paper trading 4 more weeks |

---

## Transition to Live Trading

When paper results are satisfactory (week 8+):

```json
{
    "dry_run": false,
    "stake_amount": 50,
    "max_open_trades": 2
}
```

- Update Binance API key permissions to allow trading
- Restrict API key to your server/Railway IP
- Disable withdrawal permission
- Start with $200 total across all strategies
- Keep paper trading instances running in parallel for comparison

---

## Telegram Bot Quick Setup

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow prompts, save the **token**
3. Search for **@userinfobot**, send any message, note your **chat_id**
4. Add both as environment variables in Railway (or `config-private.json` on DO)

Useful bot commands once running:

| Command | What it does |
|---------|-------------|
| `/status` | Show open trades |
| `/profit` | Profit summary |
| `/balance` | Simulated balance |
| `/daily` | Daily P&L |
| `/performance` | Per-pair performance |
| `/stop` | Pause trading |
| `/start` | Resume trading |
| `/forceexit all` | Close all positions |

---

## Security Checklist

- [ ] Binance API key: read-only for paper trading (no trade/withdrawal permission)
- [ ] Binance API key: IP-restricted (Railway IPs or your droplet IP)
- [ ] No secrets in git (config-private.json in .gitignore, or use env vars on Railway)
- [ ] Railway: hard spending limit set ($10/month)
- [ ] Telegram bot token not shared publicly
- [ ] If using DO: SSH key auth (not password), UFW firewall enabled, FreqUI on localhost only