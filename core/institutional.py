import pandas as pd
import numpy as np
from config import THRESHOLDS

class InstitutionalDetector:
    def __init__(self, data: pd.DataFrame):
        self.df = data

    def calculate_mfi(self, period=14):
        """Money Flow Index manual calculation"""
        # Typical Price
        tp = (self.df['High'] + self.df['Low'] + self.df['Close']) / 3
        # Raw Money Flow
        rmf = tp * self.df['Volume']
        
        # Positive/Negative Flow
        # Compare current TP with previous TP
        # We need to shift TP by 1 to compare
        prev_tp = tp.shift(1)
        
        positive_flow = np.where(tp > prev_tp, rmf, 0)
        negative_flow = np.where(tp < prev_tp, rmf, 0)
        
        # Sum over period
        pos_mf = pd.Series(positive_flow, index=self.df.index).rolling(window=period).sum()
        neg_mf = pd.Series(negative_flow, index=self.df.index).rolling(window=period).sum()
        
        # MFI
        mfi = 100 - (100 / (1 + (pos_mf / neg_mf)))
        self.df['MFI_14'] = mfi

    def calculate_obv(self):
        """On Balance Volume manual calculation"""
        # If Close > Prev Close, add volume. If <, subtract.
        change = self.df['Close'].diff()
        direction = np.where(change > 0, 1, -1)
        direction[change == 0] = 0
        
        # Multiply Direction by Volume
        adj_vol = direction * self.df['Volume']
        self.df['OBV'] = adj_vol.cumsum()

    def analyze_flows(self):
        """Calculates flow indicators like MFI, OBV, ADL."""
        if self.df.empty:
            return

        self.calculate_mfi(14)
        self.calculate_obv()

    def detect_smart_money(self) -> dict:
        """
        Looks for divergence and high volume accumulation.
        """
        if self.df.empty or len(self.df) < 20:
             return {"detected": False, "score": 0}

        last = self.df.iloc[-1]
        
        score = 0
        reasons = []

        # 1. High Relative Volume + Price Up
        rvol = last.get('RVOL', 0)
        if rvol > THRESHOLDS['RVOL_THRESHOLD'] and last['Close'] > last['Open']:
            score += 3
            reasons.append("High VOL Accumulation")

        # 2. MFI Divergence check (Oversold but turning up)
        mfi = last.get('MFI_14')
        if mfi and not np.isnan(mfi) and mfi < THRESHOLDS['MFI_OVERSOLD']:
             score += 1
             reasons.append("MFI Oversold (Potential Reversal)")
        
        # 3. Institutional "Footprint" (Wicks)
        high_low = last['High'] - last['Low']
        if high_low > 0:
            lower_wick = min(last['Open'], last['Close']) - last['Low']
            if lower_wick / high_low > 0.6: 
                score += 2
                reasons.append("Strong Rejection of Lows (Buying wick)")

        detected = score >= 3
        
        # OBV Trend Check
        obv_trend = "Unknown"
        if 'OBV' in self.df:
            obv_trend = "Rising" if last['OBV'] > self.df['OBV'].iloc[-5] else "Flat/Falling"

        return {
            "detected": detected,
            "institutional_score": score,
            "signals": reasons,
            "mfi": float(mfi) if mfi and not np.isnan(mfi) else 0.0,
            "obv_trend": obv_trend
        }
