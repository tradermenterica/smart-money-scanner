import os, sys
sys.path.append(os.getcwd())
from core.scanner import Scanner
from core.data import DataFetcher
from core.financials import FundamentalAnalyzer
from core.institutional import InstitutionalDetector

def full_debug_tsla():
    print("--- FULL SCANNER DEBUG TSLA ---")
    symbol = "TSLA"
    df = DataFetcher.get_history(symbol)
    if df.empty:
        print("Data empty")
        return

    # Mock fund and inst res like process_batch does
    fund_res = FundamentalAnalyzer(symbol).is_financially_solid()
    inst = InstitutionalDetector(df)
    inst.analyze_flows()
    inst_res = inst.detect_smart_money()

    scanner = Scanner()
    print("Calling evaluate_setup...")
    evals = scanner.evaluate_setup(symbol, df, fund_res, inst_res)
    
    print(f"Results list: {evals}")
    
    if not evals:
        print("No matches. Checking why evaluate_dip_buy failed...")
        # Since we can't easily see inside the try/except of evaluate_dip_buy, Let's re-run manually
        res = scanner.evaluate_dip_buy(symbol, df, fund_res, inst_res, {})
        print(f"Direct evaluate_dip_buy call: {res}")

if __name__ == "__main__":
    full_debug_tsla()
