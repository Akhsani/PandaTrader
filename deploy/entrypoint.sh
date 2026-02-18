#!/bin/bash
# Inject Railway environment variables into Freqtrade config
# This avoids putting secrets in config.json (which is in git)

CONFIGS=("/freqtrade/user_data/config.json" "/freqtrade/user_data/config-funding.json")

for CONFIG in "${CONFIGS[@]}"; do
    [ -f "$CONFIG" ] || continue

    # Use jq to inject secrets (jq is installed in the Dockerfile)
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
done

# Execute the original Freqtrade command
exec freqtrade "$@"
