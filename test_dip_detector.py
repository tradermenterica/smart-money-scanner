# Test script for Dip Detector
import os
os.environ["FINNHUB_API_KEY"] = "d5grge9r01qll3dk6vtgd5grge9r01qll3dk6vu0"

from core.api_clients import FinnhubClient
from core.dip_detector import DipDetector

print("="*50)
print("Testing Finnhub API Connection")
print("="*50)

# Test 1: API Connection
client = FinnhubClient()
if client.test_connection():
    print("✅ Finnhub API connection successful!")
else:
    print("❌ Finnhub API connection failed!")
    exit(1)

# Test 2: Institutional Ownership
print("\n" + "="*50)
print("Testing Institutional Ownership (AAPL)")
print("="*50)
inst_data = client.get_institutional_ownership("AAPL")
if inst_data:
    print(f"✅ Total holders: {inst_data['total_holders']}")
    print(f"   Change: {inst_data['change_percentage']:.2f}%")
else:
    print("⚠️  No institutional data available")

# Test 3: Insider Transactions
print("\n" + "="*50)
print("Testing Insider Transactions (AAPL)")
print("="*50)
insider_data = client.get_insider_transactions("AAPL", days=30)
if insider_data:
    print(f"✅ Buy transactions: {insider_data['buy_transactions']}")
    print(f"   Sell transactions: {insider_data['sell_transactions']}")
    print(f"   Net shares: {insider_data['net_shares']:,}")
else:
    print("⚠️  No insider data available")

# Test 4: Recommendations
print("\n" + "="*50)
print("Testing Analyst Recommendations (AAPL)")
print("="*50)
rec_data = client.get_recommendation_trends("AAPL")
if rec_data:
    print(f"✅ Buy: {rec_data['buy']}, Hold: {rec_data['hold']}, Sell: {rec_data['sell']}")
    print(f"   Buy %: {rec_data['buy_percentage']:.1f}%")
else:
    print("⚠️  No recommendation data available")

# Test 5: Full Dip Analysis
print("\n" + "="*50)
print("Testing Full Dip Detection (NVDA)")
print("="*50)
detector = DipDetector()
result = detector.analyze_dip_opportunity("NVDA")
if result:
    print(f"✅ Dip Score: {result['dip_score']}/100")
    print(f"   Strong Dip: {result['is_strong_dip']}")
    print(f"   Current Price: ${result['current_price']:.2f}")
    if 'breakdown' in result and 'drawdown' in result['breakdown']:
        dd = result['breakdown']['drawdown']
        print(f"   Drawdown: {dd['drawdown_pct']:.2f}%")
else:
    print("⚠️  Could not analyze NVDA")

print("\n" + "="*50)
print("All tests completed!")
print("="*50)
