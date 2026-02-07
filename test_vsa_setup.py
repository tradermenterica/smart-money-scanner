
import pandas as pd
import yfinance as yf
from core.technicals import TechnicalAnalyzer
import json

def test_vsa_detection():
    symbol = "PH"
    print(f"Fetching historical data for {symbol}...")
    
    # Fetch data around Dec 18-19 2024 (as mentioned in user image)
    # The image says "jue 18 Dic '25"? 
    # Wait, the system date is Feb 2026. "jue 18 Dic '25" would be Dec 18, 2025.
    df = yf.download(symbol, start="2025-11-01", end="2026-01-10", progress=False)
    
    if df.empty:
        print("Failed to fetch data.")
        return

    # Check MultiIndex (yfinance can return it)
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(symbol, axis=1, level=1) if symbol in df.columns.levels[1] else df[symbol]

    analyzer = TechnicalAnalyzer(df)
    analyzer.calculate_indicators()
    
    # Let's find the specific date: Dec 18, 2025
    target_date = "2025-12-18"
    if target_date in df.index.strftime('%Y-%m-%d'):
        print(f"\nAnalyzing data for {target_date}...")
        # To analyze a specific day, we slice the DF up to that day
        idx = df.index.get_loc(df[df.index.strftime('%Y-%m-%d') == target_date].index[0])
        sub_df = df.iloc[:idx+1].copy()
        
        test_analyzer = TechnicalAnalyzer(sub_df)
        test_analyzer.calculate_indicators()
        results = test_analyzer.check_setup()
        
        print(f"Results for {target_date}:")
        print(json.dumps(results, indent=4))
        
        print("\nDEBUG VALUES:")
        print(f"vsa_absorption in results: {results.get('vsa_absorption')}")
        
        if results.get("vsa_absorption"):
            print("\nSUCCESS: VSA Absorption detected on the target date!")
        else:
            print("\nWARNING: VSA Absorption NOT detected. Checking metrics...")
            last_row = sub_df.iloc[-1]
            avg_vol = sub_df['Volume'].rolling(20).mean().iloc[-1]
            avg_spread = (sub_df['High'] - sub_df['Low']).rolling(20).mean().iloc[-1]
            current_spread = last_row['High'] - last_row['Low']
            rvol = last_row['Volume'] / avg_vol
            
            print(f"RVOL: {rvol:.2f} (Threshold > 1.8)")
            print(f"Current Spread: {current_spread:.2f}")
            print(f"Avg Spread (20d): {avg_spread:.2f}")
            print(f"Spread Ratio: {current_spread/avg_spread:.2f} (Threshold < 0.9)")
    else:
        available_dates = df.index.strftime('%Y-%m-%d').tolist()
        print(f"Target date {target_date} not found. Available dates near it: {available_dates[idx-2:idx+3] if 'idx' in locals() else 'None'}")

if __name__ == "__main__":
    test_vsa_detection()
