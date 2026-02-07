"""
Test Money Flow + Zone Detection with BAX (Feb 7, 2026)
Verify the new system detects BAX Image 2 setup correctly.
"""
import pandas as pd
import yfinance as yf
from core.money_flow import MoneyFlowDetector
from core.zones import ZoneDetector

def test_bax_money_flow_zones():
    print("Testing Money Flow + Zone Detection on BAX (Baxter International)")
    print("="*80)
    
    # Fetch BAX data up to Feb 7, 2026
    symbol = "BAX"
    raw_df = yf.download(symbol, start="2025-08-01", end="2026-02-08", progress=False)
    
    if raw_df.empty:
        print("ERROR: Could not fetch BAX data")
        return
    
    # Handle MultiIndex
    if isinstance(raw_df.columns, pd.MultiIndex):
        df = raw_df.xs(symbol, axis=1, level=1)
    else:
        df = raw_df
    
    # Truncate to Feb 7 (before explosion)
    df_feb7 = df[df.index <= "2026-02-07"]
    
    if len(df_feb7) < 50:
        print(f"ERROR: Not enough data. Got {len(df_feb7)} days")
        return
        
    last_close = float(df_feb7['Close'].iloc[-1])
    
    print(f"\nData Points: {len(df_feb7)} days")
    print(f"Last Close (Feb 7): ${last_close:.2f}")
    
    # === MONEY FLOW ANALYSIS ===
    print("\n" + "="*80)
    print("MONEY FLOW ANALYSIS (LuxAlgo-style signals)")
    print("="*80)
    
    mf_detector = MoneyFlowDetector(df_feb7)
    mf_signals = mf_detector.detect_signals(lookback=5)
    
    print(f"\n✓ Signal Count (last 5 days): {mf_signals['signal_count']}")
    print(f"✓ Latest Signal Date: {mf_signals['latest_signal_date']}")
    print(f"✓ Signal Strength (avg CMF): {mf_signals['signal_strength']:.4f}")
    print(f"✓ Has Recent Flow (2+ signals): {mf_signals['has_recent_flow']}")
    
    # === ZONE ANALYSIS ===
    print("\n" + "="*80)
    print("ZONE ANALYSIS (Supply/Demand Detection)")
    print("="*80)
    
    zone_detector = ZoneDetector(df_feb7)
    current_zone = zone_detector.get_current_zone_type()
    price_position = zone_detector.get_position_in_range()
    
    print(f"\n✓ Current Zone Type: {current_zone.upper()}")
    if current_zone == 'demand':
        print("  → In DEMAND zone (blue/support) ✅ GOOD for entry")
    elif current_zone == 'supply':
        print("  → In SUPPLY zone (red/resistance) ❌ AVOID")
    else:
        print("  → In NEUTRAL zone (no clear zone)")
    
    print(f"\n✓ Price Position in Range: {price_position:.2%}")
    if price_position < 0.4:
        print("  → Lower 40% of range ✅ IDEAL")
    elif price_position < 0.6:
        print("  → Middle of range ⚠️ ACCEPTABLE")
    else:
        print("  → Upper range ❌ TOO HIGH")
    
    # === FINAL VERDICT ===
    print("\n" + "="*80)
    print("SCANNER DECISION")
    print("="*80)
    
    passes_filters = True
    
    # Filter 1: Money Flow
    if not mf_signals['has_recent_flow']:
        print("\n❌ REJECTED: No recent money flow signals")
        passes_filters = False
    else:
        print(f"\n✅ PASS: {mf_signals['signal_count']} money flow signals detected")
    
    # Filter 2: Zone
    if current_zone == 'supply':
        print("❌ REJECTED: In supply (resistance) zone")
        passes_filters = False
    else:
        print(f"✅ PASS: Zone type is '{current_zone}'")
    
    # Filter 3: Price Position
    if price_position > 0.65:
        print(f"❌ REJECTED: Price too high in range ({price_position:.1%})")
        passes_filters = False
    else:
        print(f"✅ PASS: Price position acceptable ({price_position:.1%})")
    
    # Calculate score
    score = 0
    if mf_signals['signal_count'] >= 3:
        score += 60
    elif mf_signals['signal_count'] >= 2:
        score += 45
    
    if current_zone == 'demand':
        score += 30
    
    if price_position < 0.4:
        score += 20
    elif price_position < 0.6:
        score += 10
    
    print(f"\n{'='*80}")
    if passes_filters:
        print(f"✅ SUCCESS: BAX would be detected with score: {score}")
        print("   This matches the BAX Image 2 setup!")
    else:
        print("❌ FAILED: BAX would be filtered out")
        print("   The detection logic needs adjustment")
    print("="*80)

if __name__ == "__main__":
    test_bax_money_flow_zones()
