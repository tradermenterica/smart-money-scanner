import os, sys
sys.path.append(os.getcwd())
from core.data import DataFetcher
from core.money_flow import MoneyFlowDetector
from config import DIP_THRESHOLDS

def debug_tsla_dip():
    print("--- DEBUG TSLA DIP ---")
    symbol = "TSLA"
    df = DataFetcher.get_history(symbol)
    if df.empty:
        print("Data empty")
        return

    lookback = DIP_THRESHOLDS.get("LOOKBACK_DAYS", 60)
    min_dd = DIP_THRESHOLDS.get("MIN_DRAWDOWN", -45)
    max_dd = DIP_THRESHOLDS.get("MAX_DRAWDOWN", -10)
    
    high_60d = float(df['High'].tail(lookback).max())
    current_price = float(df['Close'].iloc[-1])
    drawdown_pct = ((current_price - high_60d) / high_60d) * 100
    
    print(f"High 60d: {high_60d}")
    print(f"Current Price: {current_price}")
    print(f"Drawdown: {drawdown_pct:.2f}% (Limit: {min_dd}% to {max_dd}%)")
    
    if not (min_dd < drawdown_pct < max_dd):
        print("FAIL: Drawdown out of range")
        return

    mf_detector = MoneyFlowDetector(df)
    pullback_acc = mf_detector.detect_pullback_accumulation(lookback=lookback)
    print(f"Money Flow Acc: {pullback_acc['has_pullback_accumulation']} (Signals: {pullback_acc['signal_count']}, PriceChg: {pullback_acc['price_change_pct']}%)")
    
    if not pullback_acc['has_pullback_accumulation']:
        print("FAIL: No pullback accumulation (signals < 2 or price change >= 5%)")
        return

    low_60d = float(df['Low'].tail(lookback).min())
    range_60d = high_60d - low_60d
    position_60d = (current_price - low_60d) / range_60d if range_60d > 0 else 0.5
    print(f"Position 60d: {position_60d*100:.2f}% (Limit: < 40%)")
    
    if position_60d > 0.40:
        print("FAIL: Position too high in range")
        return

    print("SUCCESS: TSLA SHOULD PASS!")

if __name__ == "__main__":
    debug_tsla_dip()
