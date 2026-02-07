import yfinance as yf
import sys
sys.path.insert(0, 'c:\\Users\\pc\\.gemini\\antigravity\\scratch\\smart-money-scanner')

# Test HLT
print("="*50)
print("Testing HLT (Hilton) - Should REJECT")
print("="*50)

df = yf.download('HLT', period='90d', progress=False)

# Filter 1: Pullback
high_60d = df['High'].tail(60).max()
current_price = df['Close'].iloc[-1]
drawdown_pct = ((current_price - high_60d) / high_60d) * 100

print(f"\n✓ FILTER 1: PULLBACK DETECTION")
print(f"  High 60d: ${high_60d:.2f}")
print(f"  Current: ${current_price:.2f}")
print(f"  Drawdown: {drawdown_pct:.2f}%")
print(f"  Required: -50% < drawdown < -15%")
print(f"  Result: {'PASS ✅' if -50 < drawdown_pct < -15 else 'REJECT ❌'}")

# Filter 2: Price Action
recent_prices = df['Close'].tail(10)
price_start = recent_prices.iloc[0]
price_end = recent_prices.iloc[-1]
price_change = ((price_end - price_start) / price_start) * 100

print(f"\n✓ FILTER 2: PRICE ACTION")
print(f"  10 days ago: ${price_start:.2f}")
print(f"  Today: ${price_end:.2f}")
print(f"  Change: {price_change:.2f}%")
print(f"  Required: < 5% (not rallying)")
print(f"  Result: {'PASS ✅' if price_change < 5 else 'REJECT ❌ (RALLYING)'}")

# Filter 3: Support Zone
low_60d = df['Low'].tail(60).min()
range_60d = high_60d - low_60d
if range_60d > 0:
    position_60d = (current_price - low_60d) / range_60d
else:
    position_60d = 0.5

print(f"\n✓ FILTER 3: SUPPORT ZONE")
print(f"  Low 60d: ${low_60d:.2f}")
print(f"  Position in range: {position_60d*100:.1f}%")
print(f"  Required: < 40%")
print(f"  Result: {'PASS ✅' if position_60d < 0.40 else 'REJECT ❌ (TOO HIGH)'}")

# Final verdict
all_pass = (-50 < drawdown_pct < -15) and (price_change < 5) and (position_60d < 0.40)

print(f"\n{'='*50}")
print(f"FINAL VERDICT: {'✅ VALID SETUP' if all_pass else '❌ SHOULD BE REJECTED'}")
print(f"{'='*50}")
