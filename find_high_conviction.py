
from core.scanner import Scanner
from core.tickers import TickerSource
from core.dip_detector import DipDetector
from core.data import DataFetcher
import json
import pandas as pd

def find_high_conviction_dip():
    dip_detector = DipDetector()
    tickers = TickerSource.get_darwinex_tickers()
    
    print(f"Scanning {len(tickers)} Darwinex tickers for Dip + VSA setups...")
    
    # Use batch fetch to be fast
    batch_data = DataFetcher.get_batch_history(tickers, period="6mo")
    
    candidates = []
    
    for symbol in tickers:
        try:
            # Extract ticker DF
            if isinstance(batch_data.columns, pd.MultiIndex):
                ticker_df = batch_data[symbol]
            else:
                ticker_df = batch_data if len(tickers) == 1 else pd.DataFrame()
            
            if ticker_df.empty: continue
            
            # Analyze
            res = dip_detector.analyze_dip_opportunity(symbol, df=ticker_df)
            
            if res and res.get('breakdown', {}).get('vsa_absorption'):
                # We found one with VSA!
                candidates.append(res)
                print(f"  [FOUND VSA DIP] {symbol} - Score: {res['dip_score']}")
            elif res and res['dip_score'] > 75:
                # High score but maybe not VSA (OBV or support instead)
                candidates.append(res)
                print(f"  [FOUND HIGH SCORE] {symbol} - Score: {res['dip_score']}")
                
        except Exception as e:
            continue

    # Sort candidates by dip_score
    candidates.sort(key=lambda x: x['dip_score'], reverse=True)
    
    with open('high_conviction_results.json', 'w') as f:
        json.dump(candidates, f, indent=4)
        
    print(f"\nScan complete. Found {len(candidates)} candidates.")

if __name__ == "__main__":
    find_high_conviction_dip()
