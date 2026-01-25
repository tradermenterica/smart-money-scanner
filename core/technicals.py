import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.df = data

    def calculate_indicators(self):
        """Adds technical indicators to the dataframe using custom pandas logic."""
        if self.df.empty:
            return

        # Simple Moving Averages
        self.df['SMA_50'] = self.df['Close'].rolling(window=50).mean()
        self.df['SMA_200'] = self.df['Close'].rolling(window=200).mean()
        
        # Exponential Moving Average
        self.df['EMA_20'] = self.df['Close'].ewm(span=20, adjust=False).mean()

        # Average Volume (for RVOL)
        self.df['VOL_SMA_20'] = self.df['Volume'].rolling(window=20).mean()
        
        # Relative Volume
        self.df['RVOL'] = self.df['Volume'] / self.df['VOL_SMA_20']

        # Bollinger Bands (20, 2)
        sma20 = self.df['Close'].rolling(window=20).mean()
        std20 = self.df['Close'].rolling(window=20).std()
        self.df['BBU_20_2.0'] = sma20 + (std20 * 2)
        self.df['BBL_20_2.0'] = sma20 - (std20 * 2)
        
        # Bandwidth
        self.df['BB_WIDTH'] = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0']) / sma20

    def check_setup(self) -> dict:
        """
        Detects if the stock is in a bullish setup.
        """
        if self.df.empty or len(self.df) < 50:
            return {"bullish": False, "reason": "Not enough data"}

        last = self.df.iloc[-1]
        
        # 1. Trend Filter
        bullish_trend = False
        if pd.notnull(last['SMA_50']):
            bullish_trend = last['Close'] > last['SMA_50']
        
        # 2. Consolidation / Squeeze
        is_squeezing = False
        if pd.notnull(last['BB_WIDTH']):
            recent_widths = self.df['BB_WIDTH'].tail(50)
            is_squeezing = last['BB_WIDTH'] < recent_widths.quantile(0.20)

        # 3. Momentum / Explosion
        breakout = False
        if pd.notnull(last['BBU_20_2.0']):
             breakout = last['Close'] > last['BBU_20_2.0']

        return {
            "trend": "Uptrend" if bullish_trend else "Downtrend",
            "squeeze": bool(is_squeezing),
            "breakout": bool(breakout),
            "rvol": float(last['RVOL']) if pd.notnull(last['RVOL']) else 0.0,
            "last_close": float(last['Close'])
        }
