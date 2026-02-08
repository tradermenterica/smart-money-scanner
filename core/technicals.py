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
        self.df['SMA_10'] = self.df['Close'].rolling(window=10).mean()
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

        # VSA Indicators
        # 1. Spread (High - Low)
        self.df['SPREAD'] = self.df['High'] - self.df['Low']
        self.df['SPREAD_SMA_20'] = self.df['SPREAD'].rolling(window=20).mean()
        
        # 2. OBV (On-Balance Volume) - Critical for early accumulation
        self.df['OBV'] = 0.0
        obv = 0
        for i in range(len(self.df)):
            if i == 0:
                obv = self.df['Volume'].iloc[i]
            else:
                if self.df['Close'].iloc[i] > self.df['Close'].iloc[i-1]:
                    obv += self.df['Volume'].iloc[i]
                elif self.df['Close'].iloc[i] < self.df['Close'].iloc[i-1]:
                    obv -= self.df['Volume'].iloc[i]
            self.df.loc[self.df.index[i], 'OBV'] = obv


    def detect_early_accumulation(self) -> bool:
        """
        Detects 'Silent Accumulation' phase BEFORE breakout (BAX Image 2 setup).
        
        Criteria:
        1. Price consolidating (not trending up strongly)
        2. Volume progressively increasing (RVOL 1.2-2.5)
        3. OBV divergence (OBV rising while price flat/down)
        4. Price near support (SMA50), NOT at resistance
        """
        if self.df.empty or len(self.df) < 50:
            return False
            
        last = self.df.iloc[-1]
        
        # 1. CONSOLIDATION CHECK: Price NOT moving up strongly
        recent_5d = self.df.tail(5)
        price_change_5d = ((recent_5d['Close'].iloc[-1] - recent_5d['Close'].iloc[0]) / recent_5d['Close'].iloc[0]) * 100
        
        # If price moved >3% in last 5 days, it's already breaking out
        if price_change_5d > 3.0:
            return False
        
        # ATR check: Volatility should be low (consolidating)
        atr_20 = self.df['SPREAD'].rolling(20).mean().iloc[-1]
        atr_recent = self.df['SPREAD'].tail(20)
        if atr_20 > atr_recent.quantile(0.6):  # If ATR high, it's moving too much
            return False
        
        # 2. PROGRESSIVE VOLUME ACCUMULATION
        if pd.isnull(last['RVOL']) or last['RVOL'] < 1.2:
            return False  # Volume too low
        if last['RVOL'] > 2.5:
            return False  # Volume already explosive (too late)
        
        # Volume trending up? Last 3 days avg > prior 3 days avg
        vol_last_3 = self.df['Volume'].tail(6).iloc[-3:].mean()
        vol_prior_3 = self.df['Volume'].tail(6).iloc[:3].mean()
        progressive_volume = vol_last_3 > vol_prior_3
        
        if not progressive_volume:
            return False
        
        # No single-day volume spike > 3x (that would be explosion, not accumulation)
        recent_vols = self.df['RVOL'].tail(5)
        if (recent_vols > 3.0).any():
            return False
        
        # 3. OBV DIVERGENCE: Money flowing in while price flat/down
        if 'OBV' not in self.df.columns:
            return False
            
        obv_10d = self.df['OBV'].tail(10)
        price_10d = self.df['Close'].tail(10)
        
        # Calculate slopes
        x = np.arange(len(obv_10d))
        obv_slope = np.polyfit(x, obv_10d.values, 1)[0]
        price_slope = np.polyfit(x, price_10d.values, 1)[0]
        
        # RELAXED: OBV rising, price can rise slightly but less than OBV
        if obv_slope <= 0:
            return False
        
        # 4. SUPPORT PROXIMITY
        if pd.isnull(last['SMA_50']):
            return False
        
        distance_from_sma50 = ((last['Close'] - last['SMA_50']) / last['SMA_50']) * 100
        if distance_from_sma50 > 20.0: # Increased from 15%
            return False
        
        # 5. RANGE POSITION: Must be in the bottom 50% of last 100 days
        # This prevents picking tops (like ADI) and focuses on the base (like GS).
        high_100d = self.df['High'].tail(100).max()
        low_100d = self.df['Low'].tail(100).min()
        total_range = high_100d - low_100d
        
        position_in_range_100d = 0.0
        if total_range > 0:
            position_in_range_100d = ((last['Close'] - low_100d) / total_range) * 100
            
        if position_in_range_100d > 50.0:  # Must be in lower half
            return False

        # All checks passed - this is early accumulation!
        return True

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
        
        # 2. Consolidation / Squeeze (Tightening)
        is_squeezing = False
        bandwidth = 0
        if pd.notnull(last['BB_WIDTH']):
            bandwidth = last['BB_WIDTH']
            # Squeeze is true if bandwidth is in the bottom 25% of the last 100 days
            recent_widths = self.df['BB_WIDTH'].tail(100)
            is_squeezing = bandwidth < recent_widths.quantile(0.25)

        # 3. Volatility Contraction Pattern (VCP) Lite
        # We look for the High-Low range to be shrinking over the last 3-4 days
        ranges = (self.df['High'] - self.df['Low']).tail(4)
        vcp = False
        if len(ranges) >= 4:
            # Check if current range is smaller than 3 days ago
            vcp = ranges.iloc[-1] < ranges.iloc[-3] and ranges.iloc[-2] < ranges.iloc[-3]

        # 4. Momentum / Explosion
        breakout = False
        if pd.notnull(last['BBU_20_2.0']):
             breakout = last['Close'] > last['BBU_20_2.0']

        # 5. VSA Absorption (Effort vs Result)
        # High Volume + Narrow Spread = Institutional Absorption
        vsa_absorption = False
        if pd.notnull(last['RVOL']) and pd.notnull(last['SPREAD_SMA_20']):
            # Condition: Volume > 1.6x Average AND Spread < 0.9x Average
            # This captures high effort (volume) but little result (spread)
            is_high_volume = last['RVOL'] > 1.6
            is_narrow_spread = last['SPREAD'] < (last['SPREAD_SMA_20'] * 0.9)
            vsa_absorption = is_high_volume and is_narrow_spread
        
        # 6. EARLY ACCUMULATION (BAX Image 2 Setup)
        early_accumulation = self.detect_early_accumulation()

        return {
            "trend": "Uptrend" if bullish_trend else "Downtrend",
            "squeeze": bool(is_squeezing),
            "vcp": bool(vcp),
            "breakout": bool(breakout),
            "vsa_absorption": bool(vsa_absorption),
            "early_accumulation": bool(early_accumulation),
            "bandwidth": float(bandwidth),
            "rvol": float(last['RVOL']) if pd.notnull(last['RVOL']) else 0.0,
            "last_close": float(last['Close']),
            "sma_10": float(last.get('SMA_10', 0)) if pd.notnull(last.get('SMA_10')) else 0.0
        }
