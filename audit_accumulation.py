import pandas as pd
import numpy as np
from core.scanner import Scanner
from core.data import DataFetcher
from core.tickers import TickerSource

def audit_accumulation():
    scanner = Scanner()
    # Let's take a few interesting ones
    test_tickers = ["GS", "ADI", "BAX", "EXC", "MSFT", "AAPL"]
    
    print(f"{'Ticker':<10} | {'Accum?':<10} | {'Score':<10}")
    print("-" * 40)
    
    for symbol in test_tickers:
        df = DataFetcher.get_history(symbol)
        if df.empty:
            print(f"{symbol:<10} | {'No Data':<10}")
            continue
            
        # We need fund_res and inst_res dummy or real
        # For audit, we'll use empty dicts or simple mocks
        evals = scanner.evaluate_setup(symbol, df, {"passed": True}, {"detected": True})
        
        acc_found = False
        score = 0
        for res in evals:
            if res['details'].get('setup_type') == "Early Accumulation":
                acc_found = True
                score = res['score']
                break
        
        print(f"{symbol:<10} | {str(acc_found):<10} | {score:<10}")

if __name__ == "__main__":
    audit_accumulation()
