# S2 Funding Reversion → 3Commas Signal Bot Webhook

Route validated S2 Funding Reversion signals (WFA +44.64% ETH) to 3Commas via Freqtrade webhook.

## Architecture

```
Freqtrade dry-run → populate_entry_trend fires → Freqtrade webhook → 3Commas Signal Bot → Binance
```

## Prerequisites

- Freqtrade with FundingReversion strategy
- 3Commas account with Signal Bot
- Binance API credentials (in 3Commas)

## Setup Steps

### 1. Create 3Commas Signal Bot

1. Log into 3Commas
2. Go to Signal Bots → Create Signal Bot
3. Select **Custom Signal** type
4. Choose Exchange: Binance
5. Direction: Long (or Long/Short)
6. Copy the **webhook URL** and **secret** from the 3Commas form

### 2. Configure deploy/config-s2.json

1. Open `deploy/config-s2.json`
2. Replace placeholders in the `webhook` section:
   - `{YOUR_3C_SECRET}` → paste your 3Commas webhook secret
   - `{YOUR_BOT_UUID}` → paste your Signal Bot UUID

3. Ensure `pair_whitelist` includes `ETH/USDT:USDT` (futures) or your target pair

### 3. Run Freqtrade

```bash
freqtrade trade --config deploy/config-s2.json --strategy FundingReversion
```

In dry-run mode, Freqtrade will execute locally and send webhooks to 3Commas on each entry/exit signal. The 3Commas Signal Bot receives the webhook and executes on Binance.

### 4. Verify

- Check Freqtrade logs for webhook POST requests
- Check 3Commas Signal Bot for received signals

## Webhook Payload Format

Freqtrade uses template variables in the webhook payload:

- `{pair}`: Trading pair (e.g. ETH/USDT:USDT)
- `{open_rate}`: Entry price
- `{secret}`: 3Commas secret
- `{bot_uuid}`: 3Commas Signal Bot UUID

## P3.5 Webhook E2E Test (Live/Dry-Run Only)

The webhook E2E test validates Freqtrade → webhook → 3Commas. **It cannot use historical backtest data.** Webhooks fire only in trade mode (`freqtrade trade --dry-run` or live), which uses live/delayed exchange data. Freqtrade backtest does not invoke webhooks. Use dry-run or paper trading to test the webhook pipeline.

## Troubleshooting

- **Webhook not firing:** Ensure `webhook.enabled` is `true` in config
- **3Commas not receiving:** Verify URL and secret; check 3Commas webhook logs
- **Wrong pair format:** 3Commas may expect `ETH/USDT` vs `ETH/USDT:USDT` for futures

## References

- [Freqtrade Webhook Config](https://www.freqtrade.io/en/stable/webhook-config/)
- [3Commas Custom Signal Type](https://help.3commas.io/en/articles/8529406-signal-bot-custom-signal-type)
- [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)
