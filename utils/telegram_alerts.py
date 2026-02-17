
import ccxt
import asyncio
import os
import sys
from telegram import Bot
import time
from datetime import datetime

# Add parent dir to path to find dns_patch or utils if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Apply DNS patch
try:
    import utils.dns_patch as dns_patch
    dns_patch.apply_patch()
except ImportError:
    pass

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

THRESHOLDS = {
    'BTC/USDT:USDT': 0.00015,   # 0.015% (Corresponding roughly to Z=1.5 on low vol)
    'ETH/USDT:USDT': 0.0002,    # 0.02%
    'SOL/USDT:USDT': 0.0003,    # 0.03%
}

async def send_telegram_message(bot, message):
    try:
        if TELEGRAM_TOKEN == "YOUR_TOKEN_HERE":
            print(f"Assign TELEGRAM_TOKEN env var to send: {message}")
            return
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Sent alert: {message}")
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

async def check_funding_signals():
    print("Starting Funding Rate Monitor...")
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    
    bot = Bot(token=TELEGRAM_TOKEN)
    
    while True:
        print(f"Checking funding rates at {datetime.now()}...")
        for symbol, threshold in THRESHOLDS.items():
            try:
                funding = exchange.fetch_funding_rate(symbol)
                rate = funding['fundingRate']
                
                print(f"  {symbol}: {rate:.4%}")
                
                if abs(rate) > threshold:
                    direction = "LONG (Shorts paying)" if rate < 0 else "SHORT (Longs paying)"
                    msg = (
                        f"🚨 FUNDING SIGNAL: {symbol}\n"
                        f"Rate: {rate:.4%} per 8hr\n"
                        f"Signal: {direction}\n"
                        f"Threshold: ±{threshold:.4%}"
                    )
                    await send_telegram_message(bot, msg)
            except Exception as e:
                print(f"Error {symbol}: {e}")
        
        # Sleep for 5 minutes
        await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(check_funding_signals())
    except KeyboardInterrupt:
        print("Monitor stopped.")
