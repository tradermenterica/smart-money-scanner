
import asyncio
import json
import sys
import os
from core.dip_detector import DipDetector
from config import DIP_DETECTION_ENABLED

# Ensure DIP detection is enabled for analysis
import config
from dotenv import load_dotenv
load_dotenv()
config.DIP_DETECTION_ENABLED = True

async def analyze_candidates():
    candidates = ['NEM', 'RCL', 'AMD', 'LRCX', 'AMAT']
    detector = DipDetector()
    
    results = []
    print(f"Starting deep analysis for {len(candidates)} candidates...")
    
    for symbol in candidates:
        print(f"Analyzing {symbol}...")
        try:
            # Full scan using all APIs (Finnhub, AlphaVantage, SEC)
            # This is the same logic as the /api/institutional/{symbol} endpoint
            analysis = detector.analyze_dip_opportunity(symbol)
            if analysis:
                results.append(analysis)
            else:
                print(f"No results for {symbol}")
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            
    # Save to JSON for report generation
    with open('deep_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\nAnalysis complete. Results saved to deep_analysis_results.json")

if __name__ == "__main__":
    asyncio.run(analyze_candidates())
