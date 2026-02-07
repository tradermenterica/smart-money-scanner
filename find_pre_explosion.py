
from core.scanner import Scanner
from core.tickers import TickerSource
import json
import pandas as pd
import yfinance as yf

def find_pre_explosion_candidate():
    scanner = Scanner()
    tickers = TickerSource.get_darwinex_tickers()
    
    print(f"Scanning {len(tickers)} tickers for pre-explosion setups...")
    
    candidates = []
    
    # Let's check a good chunk of them
    for symbol in tickers[:80]:
        try:
            # We use scan_ticker which does the full analysis
            result = scanner.scan_ticker(symbol)
            if not result or result.get('score', 0) < 70:
                continue
                
            tech = result['details']['technicals']
            
            # Criteria for "Pre-Explosion":
            # 1. High score
            # 2. In a Squeeze or VSA Absorption
            # 3. Hasn't moved too much TODAY (Price change < 2.5%)
            
            # Calculate today's change manually to be sure
            df = yf.download(symbol, period="2d", progress=False)
            if len(df) < 2: continue
            
            # Handle MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(symbol, axis=1, level=1)
                
            prev_close = df['Close'].iloc[-2]
            curr_close = df['Close'].iloc[-1]
            change = ((curr_close - prev_close) / prev_close) * 100
            
            is_pre_explosion = tech.get('vsa_absorption')
            
            if is_pre_explosion and change < 3.0:
                candidates.append({
                    "symbol": symbol,
                    "score": result['score'],
                    "change": change,
                    "tech": tech,
                    "inst": result['details']['institutional'],
                    "conclusion": result['details'].get('fundamentals', {}).get('passed', False)
                })
                print(f"  [FOUND VSA] {symbol} - Score: {result['score']} - Change: {change:.2f}%")
        except Exception as e:
            continue

    # Sort candidates by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    if candidates:
        with open('pre_explosion_results.json', 'w') as f:
            json.dump(candidates, f, indent=4)
        print(f"\nFinished. Found {len(candidates)} candidates.")
    else:
        print("\nNo candidates found in this batch.")

if __name__ == "__main__":
    find_pre_explosion_candidate()
