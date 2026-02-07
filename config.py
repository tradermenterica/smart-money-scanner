# config.py

# List of tickers to scan.
# This can be expanded to include all S&P 500 or other indices.
# For MVP, we start with a mix of solid companies and some potentially volatile ones to test.

WATCHLIST = ["AAPL", "TSLA", "NVDA", "BTC-USD"]
DARWINEX_ONLY = True  # Si es True, solo escanea activos de Darwinex para velocidad extrema

# Dip Detection Settings
DIP_DETECTION_ENABLED = True  # Enable institutional dip detection
DIP_SCORE_THRESHOLD = 70      # Minimum score for "strong dip" classification
USE_ALPHA_VANTAGE = True      # Use Alpha Vantage for enhanced sentiment (25 calls/day limit)
USE_SEC_API = True            # Use sec-api.io for real SEC filings data (13F, Form 4)

# Dip Detection Thresholds
DIP_THRESHOLDS = {
    "MIN_DRAWDOWN": -25,      # Maximum acceptable drawdown (%) - Changed to -25 per user request
    "MAX_DRAWDOWN": -3,       # Minimum drawdown to qualify as "dip" (%) - Changed to -3 per user request
    "LOOKBACK_DAYS": 60,      # Days to look back for high
    "DIVERGENCE_PERIOD": 10,  # Days to check for OBV divergence
}

# Criteria Thresholds
THRESHOLDS = {
    "MAX_PE_RATIO": 35.0,        # Maximum Price to Earnings
    "MAX_DEBT_TO_EQUITY": 2.0,   # Maximum Debt to Equity
    "MIN_ROE": 0.08,             # Minimum Return on Equity (8%)
    "RVOL_THRESHOLD": 1.5,       # Minimum Relative Volume for 'High Volume'
    "MFI_OVERSOLD": 30,          # Money Flow Index Oversold
    "MFI_OVERBOUGHT": 70         # Money Flow Index Overbought
}
