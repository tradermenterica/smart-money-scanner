import pandas as pd
import numpy as np

class MoneyFlowDetector:
    """
    Detects money flow signals (like LuxAlgo "E" marks) using MFI and CMF.
    Focuses on RECENT activity (last 3-5 days) instead of historical trends.
    """
    
    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()
        
    def calculate_mfi(self, period: int = 14) -> pd.Series:
        """
        Calculate Money Flow Index (MFI).
        MFI combines price and volume to measure buying/selling pressure.
        Range: 0-100 (similar to RSI but with volume)
        """
        # Typical Price = (High + Low + Close) / 3
        typical_price = (self.df['High'] + self.df['Low'] + self.df['Close']) / 3
        
        # Money Flow = Typical Price * Volume
        money_flow = typical_price * self.df['Volume']
        
        # Separate positive and negative money flow
        positive_flow = pd.Series(0.0, index=self.df.index)
        negative_flow = pd.Series(0.0, index=self.df.index)
        
        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                negative_flow.iloc[i] = money_flow.iloc[i]
        
        # Sum over period
        positive_mf_sum = positive_flow.rolling(window=period).sum()
        negative_mf_sum = negative_flow.rolling(window=period).sum()
        
        # Money Flow Ratio
        mf_ratio = positive_mf_sum / negative_mf_sum
        
        # MFI = 100 - (100 / (1 + MF Ratio))
        mfi = 100 - (100 / (1 + mf_ratio))
        
        return mfi
    
    def calculate_cmf(self, period: int = 20) -> pd.Series:
        """
        Calculate Chaikin Money Flow (CMF).
        More sensitive to recent changes than MFI.
        Range: -1 to +1 (positive = accumulation, negative = distribution)
        """
        # Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
        mf_multiplier = ((self.df['Close'] - self.df['Low']) - 
                        (self.df['High'] - self.df['Close'])) / (self.df['High'] - self.df['Low'])
        
        # Handle division by zero (days with no range)
        mf_multiplier = mf_multiplier.fillna(0)
        
        # Money Flow Volume = MF Multiplier * Volume
        mf_volume = mf_multiplier * self.df['Volume']
        
        # CMF = Sum of MF Volume over period / Sum of Volume over period
        cmf = mf_volume.rolling(window=period).sum() / self.df['Volume'].rolling(window=period).sum()
        
        return cmf
    
    def detect_signals(self, lookback: int = 5) -> dict:
        """
        Generate money flow signals for the last N days.
        Similar to LuxAlgo "E" marks - indicates money flowing into the stock.
        
        A signal is triggered when:
        1. CMF crosses above 0.05 (money inflow threshold)
        2. MFI > 50 AND increasing
        3. Volume > 1.3x average
        
        Returns:
            dict with:
            - signal_count: Number of signals in last N days
            - latest_signal_date: Most recent signal date
            - signal_strength: Average CMF during signals
            - has_recent_flow: True if 2+ signals in lookback period
        """
        if self.df.empty or len(self.df) < 20:
            return {
                'signal_count': 0,
                'latest_signal_date': None,
                'signal_strength': 0.0,
                'has_recent_flow': False
            }
        
        # Calculate indicators
        mfi = self.calculate_mfi(14)
        cmf = self.calculate_cmf(20)
        
        # Add to dataframe for analysis
        self.df['MFI'] = mfi
        self.df['CMF'] = cmf
        
        # Detect signals in recent data
        recent = self.df.tail(lookback)
        signals = []
        
        for i in range(len(recent)):
            idx = recent.index[i]
            
            # Skip if not enough data
            if pd.isnull(recent['MFI'].iloc[i]) or pd.isnull(recent['CMF'].iloc[i]):
                continue
            
            # Condition 1: CMF positive and above threshold
            cmf_positive = recent['CMF'].iloc[i] > 0.05
            
            # Condition 2: MFI above 50 (buying pressure)
            mfi_bullish = recent['MFI'].iloc[i] > 50
            
            # Condition 3: MFI increasing (if we have previous data)
            mfi_increasing = False
            if i > 0 and pd.notnull(recent['MFI'].iloc[i-1]):
                mfi_increasing = recent['MFI'].iloc[i] > recent['MFI'].iloc[i-1]
            
            # Condition 4: Volume elevated
            vol_avg = self.df['Volume'].tail(20).mean()
            volume_elevated = recent['Volume'].iloc[i] > (vol_avg * 1.3)
            
            # Signal triggered if at least 3 of 4 conditions met
            conditions_met = sum([cmf_positive, mfi_bullish, mfi_increasing, volume_elevated])
            
            if conditions_met >= 3:
                signals.append({
                    'date': idx,
                    'cmf': recent['CMF'].iloc[i],
                    'mfi': recent['MFI'].iloc[i]
                })
        
        # Compile results
        signal_count = len(signals)
        latest_signal = signals[-1]['date'] if signals else None
        avg_cmf = np.mean([s['cmf'] for s in signals]) if signals else 0.0
        
        return {
            'signal_count': signal_count,
            'latest_signal_date': latest_signal,
            'signal_strength': float(avg_cmf),
            'has_recent_flow': signal_count >= 2
        }
    
    def detect_pullback_accumulation(self, lookback: int = 10) -> dict:
        """
        CRITICAL METHOD: Detects money flow signals that occur DURING price pullback.
        This is the key to detecting CNC/APOV setups and rejecting XOM/CAT/COST.
        
        The difference:
        - CNC/APOV: MFI signals while price is consolidating/falling (accumulation)
        - XOM/CAT: MFI signals while price is rallying (momentum trading)
        
        Args:
            lookback: Days to analyze for price trend (default 10)
            
        Returns:
            dict with:
            - has_pullback_accumulation: True if money flowing in during pullback
            - signal_count: Number of money flow signals
            - price_action: 'pullback', 'consolidating', or 'rallying'
            - price_change_pct: Recent price change percentage
        """
        if self.df.empty or len(self.df) < 20:
            return {
                'has_pullback_accumulation': False,
                'signal_count': 0,
                'price_action': 'unknown',
                'price_change_pct': 0.0
            }
        
        # Get money flow signals
        signals = self.detect_signals(lookback=5)
        
        # Analyze recent price action
        recent_prices = self.df['Close'].tail(lookback)
        price_start = float(recent_prices.iloc[0])
        price_end = float(recent_prices.iloc[-1])
        price_change_pct = ((price_end - price_start) / price_start) * 100
        
        # Classify price action
        if price_change_pct > 5:
            price_action = 'rallying'
        elif price_change_pct < -5:
            price_action = 'pullback'
        else:
            price_action = 'consolidating'
        
        # RELAXED LOGIC: Accept even 1 strong signal if NOT rallying
        # (Changed from >= 2 to >= 1 to capture EXC-style early setups)
        has_accumulation = (signals['signal_count'] >= 1 and 
                           price_change_pct < 5)  # Not rallying
        
        return {
            'has_pullback_accumulation': has_accumulation,
            'signal_count': signals['signal_count'],
            'price_action': price_action,
            'price_change_pct': round(price_change_pct, 2)
        }
