
from core.data import DataFetcher
from core.dip_detector import DipDetector
from core.tickers import TickerSource
import json
import pandas as pd

def find_obv_divergence():
    detector = DipDetector()
    tickers = TickerSource.get_darwinex_tickers()
    print(f"Scanning {len(tickers)} tickers for OBV Divergence...")
    
    batch_data = DataFetcher.get_batch_history(tickers, period="6mo")
    
    candidates = []
    
    for symbol in tickers:
        try:
            if isinstance(batch_data.columns, pd.MultiIndex):
                df = batch_data[symbol]
            else:
                df = batch_data if len(tickers) == 1 else pd.DataFrame()
            
            if df.empty or len(df) < 50:
                continue
            
            # Use detector's OBV divergence logic
            has_divergence = detector.detect_obv_divergence(df, lookback=10)
            
            if has_divergence:
                # Check current price vs 50SMA (we want them at support or consolidating)
                current_price = df['Close'].iloc[-1]
                sma50 = df['Close'].rolling(50).mean().iloc[-1]
                
                # We want them near SMA50 or in a dip, not overextended
                if current_price < (sma50 * 1.05):
                    candidates.append({
                        "symbol": symbol,
                        "current_price": current_price,
                        "sma50": sma50,
                        "divergence": True
                    })
                    print(f"  [OBV DIV FOUND] {symbol}")
        except Exception as e:
            continue
            
    with open('obv_div_results.json', 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"\nDone. Found {len(candidates)} OBV Divergence candidates.")

if __name__ == "__main__":
    find_obv_divergence()
