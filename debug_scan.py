from core.tickers import TickerSource
from core.scanner import Scanner
import sys

def debug():
    print("--- START DEBUG ---")
    try:
        tickers = TickerSource.get_all_tickers()
        print(f"Total Tickers Found: {len(tickers)}")
        print(f"Sample: {tickers[:10]}")
        
        if len(tickers) > 20:
            print("SUCCESS: Ticker source is working.")
        else:
            print("FAILURE: Ticker source returned too few items.")
            
        # Test 1 scan
        s = Scanner()
        print(f"Testing scan for {tickers[0]}...")
        res = s.scan_ticker(tickers[0])
        print(f"Result: {res}")
        
    except Exception as e:
        print(f"CRITICAL ERROR IN DEBUG: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()
