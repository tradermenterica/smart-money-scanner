import asyncio
import os
import sys
import pandas as pd
import json
import numpy as np
from core.data import DataFetcher
from core.dip_detector import DipDetector

# Mock config
import config
config.DIP_DETECTION_ENABLED = True

async def test_batch_scan():
    print("--- Starting Debug Batch Scan ---")
    
    # 1. Mock Candidates (Use typical tickers)
    symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'BRK-B']
    # Add a potentially problematic one?
    symbols.append('HLT') 
    
    print(f"Fetching batch data for {len(symbols)} symbols...")
    try:
        batch_data = DataFetcher.get_batch_history(symbols, period="6mo")
        print("Batch fetch complete.")
        print(f"Columns type: {type(batch_data.columns)}")
        if isinstance(batch_data.columns, pd.MultiIndex):
            print("MultiIndex detected.")
            print(batch_data.columns[:5])
        else:
            print("Flat Index detected.")
            print(batch_data.columns[:5])
            
    except Exception as e:
        print(f"BATCH FETCH FAILED: {e}")
        return

    dip_detector = DipDetector()
    dip_opportunities = []

    print("\nProcessing symbols...")
    for symbol in symbols:
        try:
            ticker_df = pd.DataFrame()
            
            # COPY PASTE LOGIC FROM MAIN.PY
            if isinstance(batch_data.columns, pd.MultiIndex):
                try:
                    ticker_df = batch_data[symbol]
                except KeyError:
                    try:
                        ticker_df = batch_data.xs(symbol, axis=1, level=1)
                    except:
                        print(f"  Skipping {symbol} (xs failed)")
                        continue
            else:
                if len(symbols) == 1 and symbol == symbols[0]:
                    ticker_df = batch_data
                else:
                    print(f"  Skipping {symbol} (flat index mismatch)")
                    continue

            if ticker_df.empty:
                print(f"  Skipping {symbol} (empty df)")
                continue
            
            if not isinstance(ticker_df.index, pd.DatetimeIndex):
                ticker_df.index = pd.to_datetime(ticker_df.index)

            # Analyze
            # print(f"  Analyzing {symbol}...")
            dip_result = dip_detector.analyze_dip_opportunity(symbol, df=ticker_df)
            
            if dip_result:
                # print(f"  Result found for {symbol}: Score {dip_result['dip_score']}")
                dip_opportunities.append(dip_result)
            
        except Exception as e:
            print(f"  CRASH processing {symbol}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nFound {len(dip_opportunities)} opportunities.")
    
    # TEST JSON SERIALIZATION
    print("\nTesting JSON Serialization...")
    try:
        # Custom encoder to simulate FastAPI
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.bool_):
                    return bool(obj)
                return super(NpEncoder, self).default(obj)
        
        json_output = json.dumps(dip_opportunities, cls=NpEncoder)
        print("JSON Serialization: SUCCESS")
        # print("Output snippet:", json_output[:200])
        
        # Test standard json dumps to fail on simple errors
        # FastAPI uses logic that normally handles basic types but breaks on NaN/Inf if not allowed
        # Let's check for NaNs
        if "NaN" in json_output:
            print("WARNING: Output contains NaN (Standard JSON does not support this)")
        
    except Exception as e:
        print(f"JSON SERIALIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_scan())
