"""
Test Early Accumulation Detection with BAX (Feb 7, 2026)
This script verifies that the new filter detects BAX Image 2 setup correctly.
"""
import pandas as pd
import yfinance as yf
from core.technicals import TechnicalAnalyzer
from datetime import datetime

def test_bax_early_accumulation():
    print("Testing Early Accumulation Detection on BAX (Baxter International)")
    print("="*70)
    
    # Fetch BAX data up to Feb 7, 2026 at 13:09 (before explosion)
    # We'll use Feb 7 as the "current" date
    symbol = "BAX"
    raw_df = yf.download(symbol, start="2025-08-01", end="2026-02-08", progress=False)
    
    if raw_df.empty:
        print("ERROR: Could not fetch BAX data")
        return
    
    # Handle MultiIndex from yfinance
    if isinstance(raw_df.columns, pd.MultiIndex):
        df = raw_df.xs(symbol, axis=1, level=1)
    else:
        df = raw_df
    
    # Truncate to Feb 7 13:00 to simulate "before explosion"
    # Since we only have daily data, we use Feb 7 as last day
    df_feb7 = df[df.index <= "2026-02-07"]
    
    if len(df_feb7) < 50:
        print(f"ERROR: Not enough data. Got {len(df_feb7)} days")
        return
        
    last_close = float(df_feb7['Close'].iloc[-1])
    last_volume = int(df_feb7['Volume'].iloc[-1])
    
    print(f"\nData Points: {len(df_feb7)} days")
    print(f"Last Close (Feb 7): ${last_close:.2f}")
    print(f"Last Volume: {last_volume:,}")
    
    # Run technical analysis
    tech = TechnicalAnalyzer(df_feb7)
    tech.calculate_indicators()
    results = tech.check_setup()
    
    print("\n" + "="*70)
    print("TECHNICAL ANALYSIS RESULTS")
    print("="*70)
    
    print(f"\n✓ Trend: {results['trend']}")
    print(f"✓ RVOL: {results['rvol']:.2f}x")
    print(f"✓ Squeeze: {results['squeeze']}")
    print(f"✓ VCP: {results['vcp']}")
    print(f"✓ Breakout: {results['breakout']}")
    print(f"✓ VSA Absorption: {results['vsa_absorption']}")
    print(f"\n🎯 EARLY ACCUMULATION: {results['early_accumulation']}")
    
    print("\n" + "="*70)
    
    if results['early_accumulation']:
        print("✅ SUCCESS: BAX Image 2 setup detected!")
        print("   The scanner would have flagged this BEFORE the explosion.")
    else:
        print("❌ FAILED: Did not detect early accumulation")
        print("   Debugging info:")
        
        # Show why it failed
        last = df_feb7.iloc[-1]
        recent_5d = df_feb7.tail(5)
        price_change_5d = ((recent_5d['Close'].iloc[-1] - recent_5d['Close'].iloc[0]) / recent_5d['Close'].iloc[0]) * 100
        
        print(f"   - 5-day price change: {price_change_5d:.2f}% (threshold: <3%)")
        print(f"   - RVOL: {results['rvol']:.2f} (threshold: 1.2-2.5)")
        print(f"   - Last Close: ${last['Close']:.2f}")
        if 'SMA_50' in df_feb7.columns:
            sma50 = last['SMA_50']
            dist_sma50 = ((last['Close'] - sma50) / sma50) * 100
            print(f"   - Distance from SMA50: {dist_sma50:.2f}% (threshold: <5%)")

if __name__ == "__main__":
    test_bax_early_accumulation()
