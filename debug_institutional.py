import os
import sys
import traceback
from dotenv import load_dotenv

# Load env vars
load_dotenv()

print("Environment Variables:")
print(f"FINNHUB: {'Set' if os.getenv('FINNHUB_API_KEY') else 'Missing'}")
print(f"ALPHA: {'Set' if os.getenv('ALPHA_VANTAGE_API_KEY') else 'Missing'}")
print(f"SEC: {'Set' if os.getenv('SEC_API_KEY') else 'Missing'}")

try:
    print("\nInitializing DipDetector...")
    from core.dip_detector import DipDetector
    detector = DipDetector()
    
    symbol = "HLT"
    print(f"\nAnalyzing {symbol}...")
    
    # Enable full debug output by printing whatever exception happens
    try:
        result = detector.analyze_dip_opportunity(symbol)
        print("\nAnalysis Result:")
        import json
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"\nCRASH DURING ANALYSIS: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"\nCRASH DURING INIT: {e}")
    traceback.print_exc()
