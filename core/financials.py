import yfinance as yf
import pandas as pd
from config import THRESHOLDS

class FundamentalAnalyzer:
    def __init__(self, ticker_symbol: str):
        self.symbol = ticker_symbol
        self.ticker = yf.Ticker(ticker_symbol)
        self.info = {}

    def fetch_fundamentals(self):
        """Fetches necessary fundamental data."""
        try:
            self.info = self.ticker.info
            return True
        except Exception as e:
            print(f"Error fetching fundamentals for {self.symbol}: {e}")
            return False

    def is_financially_solid(self) -> dict:
        """
        Checks if the company meets financial stability criteria.
        Returns a dict with 'passed' (bool) and 'reasons' (list).
        """
        if not self.info:
            self.fetch_fundamentals()
        
        reasons = []
        is_solid = True
        
        # 1. P/E Ratio
        pe = self.info.get('trailingPE')
        if pe is None or pe > THRESHOLDS['MAX_PE_RATIO']:
            # Allow None for growth companies sometimes, but strict for "solid"
             # If it's none, it might be unprofitable.
            if pe is None:
                is_solid = False
                reasons.append("P/E Not available (Unprofitable?)")
            else:
                is_solid = False
                reasons.append(f"P/E Too High ({pe})")
        
        # 2. Debt to Equity
        de = self.info.get('debtToEquity')
        # yfinance returns debtToEquity as percentage sometimes (e.g., 150 for 1.5)
        # We handle both cases just to be safe, assuming commonly it's a ratio > 100 if %
        if de:
            ratio = de / 100.0 if de > 10 else de # heuristic adjustment
            if ratio > THRESHOLDS['MAX_DEBT_TO_EQUITY']:
                is_solid = False
                reasons.append(f"High Debt/Equity ({ratio:.2f})")

        # 3. Return on Equity
        roe = self.info.get('returnOnEquity')
        if roe and roe < THRESHOLDS['MIN_ROE']:
            is_solid = False
            reasons.append(f"Low ROE ({roe:.2%})")

        return {
            "passed": is_solid,
            "details": {
                "pe": pe,
                "debt_to_equity": de,
                "roe": roe
            },
            "failure_reasons": reasons
        }

    def get_market_cap(self):
        return self.info.get('marketCap', 0)
