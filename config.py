# config.py

# List of tickers to scan.
# This can be expanded to include all S&P 500 or other indices.
# For MVP, we start with a mix of solid companies and some potentially volatile ones to test.

WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD", "META",
    "NFLX", "INTC", "CSCO", "PEP", "KO", "JPM", "BAC",
    "PLTR", "SOFI", "AMD", "F", "GM", "XOM", "CVX", "NIO", "BABA"
]

# Criteria Thresholds
THRESHOLDS = {
    "MAX_PE_RATIO": 35.0,        # Maximum Price to Earnings
    "MAX_DEBT_TO_EQUITY": 2.0,   # Maximum Debt to Equity
    "MIN_ROE": 0.08,             # Minimum Return on Equity (8%)
    "RVOL_THRESHOLD": 1.5,       # Minimum Relative Volume for 'High Volume'
    "MFI_OVERSOLD": 30,          # Money Flow Index Oversold
    "MFI_OVERBOUGHT": 70         # Money Flow Index Overbought
}
