
from core.data import DataFetcher
from core.technicals import TechnicalAnalyzer
from core.tickers import TickerSource
import json
import pandas as pd

def find_any_vsa():
    tickers = TickerSource.get_darwinex_tickers()
    print(f"Fast scanning {len(tickers)} tickers for VSA Absorption...")
    
    # 6 months of data for indicators
    batch_data = DataFetcher.get_batch_history(tickers, period="6mo")
    
    vsa_tickers = []
    
    for symbol in tickers:
        try:
            if isinstance(batch_data.columns, pd.MultiIndex):
                df = batch_data[symbol]
            else:
                df = batch_data if len(tickers) == 1 else pd.DataFrame()
            
            if df.empty or len(df) < 50:
                continue
                
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            res = tech.check_setup()
            
            if res.get('vsa_absorption'):
                vsa_tickers.append({
                    "symbol": symbol,
                    "rvol": res['rvol'],
                    "last_close": res['last_close'],
                    "trend": res['trend']
                })
                print(f"  [VSA FOUND] {symbol} - RVOL: {res['rvol']:.2f}")
        except Exception as e:
            continue
            
    with open('fast_vsa_results.json', 'w') as f:
        json.dump(vsa_tickers, f, indent=4)
    print(f"\nDone. Found {len(vsa_tickers)} VSA candidates.")

if __name__ == "__main__":
    find_any_vsa()
