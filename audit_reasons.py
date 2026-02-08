import pandas as pd
import numpy as np
from core.technicals import TechnicalAnalyzer
from core.data import DataFetcher

def audit_reasons():
    test_tickers = ["GS", "BAX", "EXC", "MSFT", "ADI"]
    
    for symbol in test_tickers:
        print(f"\n--- AUDITANDO {symbol} ---")
        df = DataFetcher.get_history(symbol)
        if df.empty:
            print("No hay datos.")
            continue
            
        tech = TechnicalAnalyzer(df)
        tech.calculate_indicators()
        
        last = tech.df.iloc[-1]
        
        # 1. Consolidation
        recent_5d = tech.df.tail(5)
        price_change_5d = ((recent_5d['Close'].iloc[-1] - recent_5d['Close'].iloc[0]) / recent_5d['Close'].iloc[0]) * 100
        print(f"Price Change 5d: {price_change_5d:.2f}% (Limit: < 3.0%)")
        
        # 2. RVOL
        print(f"RVOL: {last['RVOL']:.2f} (Range: 1.2 - 2.5)")
        
        # 3. Progressive Volume
        vol_last_3 = tech.df['Volume'].tail(6).iloc[-3:].mean()
        vol_prior_3 = tech.df['Volume'].tail(6).iloc[:3].mean()
        print(f"Volume Trending up? {vol_last_3 > vol_prior_3} (Last3: {vol_last_3:.0f}, Prior3: {vol_prior_3:.0f})")
        
        # 4. OBV Slope
        obv_10d = tech.df['OBV'].tail(10)
        x = np.arange(len(obv_10d))
        obv_slope = np.polyfit(x, obv_10d.values, 1)[0]
        print(f"OBV Slope: {obv_slope:.2f} (Must be > 0)")
        
        # 5. Range Position
        high_100d = tech.df['High'].tail(100).max()
        low_100d = tech.df['Low'].tail(100).min()
        pos = ((last['Close'] - low_100d) / (high_100d - low_100d)) * 100
        print(f"Posición en Rango (100d): {pos:.2f}% (Limit: < 50%)")
        
        # 6. Support Prox
        dist_sma50 = ((last['Close'] - last['SMA_50']) / last['SMA_50']) * 100
        print(f"Distancia SMA50: {dist_sma50:.2f}% (Limit: < 20%)")

if __name__ == "__main__":
    audit_reasons()
