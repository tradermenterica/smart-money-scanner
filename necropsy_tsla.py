import os, sys
sys.path.append(os.getcwd())
from core.data import DataFetcher
from core.money_flow import MoneyFlowDetector
from config import DIP_THRESHOLDS

def necropsy_tsla():
    print("--- TSLA DIP NECROPSY ---")
    df = DataFetcher.get_history("TSLA")
    lookback = DIP_THRESHOLDS.get("LOOKBACK_DAYS", 60)
    min_dd = DIP_THRESHOLDS.get("MIN_DRAWDOWN", -45)
    max_dd = DIP_THRESHOLDS.get("MAX_DRAWDOWN", -10)
    
    high_60d = float(df['High'].tail(lookback).max())
    current_price = float(df['Close'].iloc[-1])
    drawdown_pct = ((current_price - high_60d) / high_60d) * 100
    
    print(f"Step 1: Drawdown Check")
    print(f"   DD: {drawdown_pct:.2f}%")
    print(f"   Limits: {min_dd} to {max_dd}")
    print(f"   Result: {min_dd < drawdown_pct < max_dd}")

    print(f"Step 2: Money Flow Check")
    mf_detector = MoneyFlowDetector(df)
    res = mf_detector.detect_pullback_accumulation(lookback=lookback)
    print(f"   MF Signals: {res['signal_count']}")
    print(f"   Price Action: {res['price_action']}")
    print(f"   Has Acc: {res['has_pullback_accumulation']}")

    print(f"Step 3: Position Check")
    low_60d = float(df['Low'].tail(lookback).min())
    range_60d = high_60d - low_60d
    pos = (current_price - low_60d) / range_60d if range_60d > 0 else 0.5
    print(f"   Pos: {pos*100:.2f}%")
    print(f"   Limit: 40.00%")
    print(f"   Result: {pos <= 0.40}")

if __name__ == "__main__":
    necropsy_tsla()
