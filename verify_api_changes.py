
import pandas as pd
import numpy as np
from core.dip_detector import DipDetector
import json

def test_response_format():
    detector = DipDetector()
    
    # Create mock data
    dates = pd.date_range(start='2024-01-01', periods=100)
    data = {
        'Open': np.random.uniform(100, 150, 100),
        'High': np.random.uniform(150, 160, 100),
        'Low': np.random.uniform(90, 100, 100),
        'Close': np.random.uniform(105, 110, 100),
        'Volume': np.random.uniform(100000, 200000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    
    # Calculate indicators needed for analyze_dip_opportunity
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=100).mean() # Mock 200 with 100
    df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['VOL_SMA_20']
    
    # Mock technicals
    sma20 = df['Close'].rolling(window=20).mean()
    std20 = df['Close'].rolling(window=20).std()
    df['BBU_20_2.0'] = sma20 + (std20 * 2)
    df['BBL_20_2.0'] = sma20 - (std20 * 2)
    df['BB_WIDTH'] = (df['BBU_20_2.0'] - df['BBL_20_2.0']) / sma20
    
    # Mock OBV
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()

    print("Running analyze_dip_opportunity...")
    result = detector.analyze_dip_opportunity("TEST", df=df)
    
    if result:
        print("Success! Result structure:")
        print(json.dumps(result, indent=4, default=str))
        
        # Verify new fields
        expected_fields = ["dip_score", "conviccion_institucional", "conclusion"]
        for field in expected_fields:
            if field in result:
                print(f"VERIFIED: Field '{field}' exists and has value: {result[field]}")
            else:
                print(f"FAILED: Field '{field}' is missing!")
    else:
        print("FAILED: No result returned (check technical filters)")

if __name__ == "__main__":
    test_response_format()
