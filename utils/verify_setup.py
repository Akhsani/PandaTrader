import sys
import importlib

def check_import(module_name):
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False

def main():
    print(f"Python version: {sys.version}")
    
    modules = [
        "ccxt",
        "pandas",
        "numpy",
        "vectorbt",
        "telegram",
        "hmmlearn",
        "sklearn",
        "matplotlib",
        "requests",
        "seaborn"
    ]

    # Optional modules that might fail
    optional_modules = ["talib", "pandas_ta", "freqtrade"]

    all_good = True
    for mod in modules:
        if not check_import(mod):
            all_good = False
            
    print("\nChecking optional modules:")
    for mod in optional_modules:
        check_import(mod)

    if all_good:
        print("\n🎉 Core environment setup complete!")
    else:
        print("\n⚠️  Some core modules failed to load.")

    # CCXT Test
    try:
        import ccxt
        print("\nTesting CCXT connection to Binance...")
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Binance BTC/USDT: {ticker['last']}")
    except Exception as e:
        print(f"❌ CCXT Test Failed: {e}")

if __name__ == "__main__":
    main()
