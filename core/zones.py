import pandas as pd
import numpy as np

class ZoneDetector:
    """
    Detects Supply and Demand zones based on price action patterns.
    - Demand Zones (Blue/Support): Drop-Base-Rally (DBR) patterns
    - Supply Zones (Red/Resistance): Rally-Base-Drop (RBD) patterns
    """
    
    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()
        
    def detect_demand_zones(self) -> list:
        """
        Find Drop-Base-Rally (DBR) patterns that indicate demand zones.
        
        Pattern:
        1. Strong drop (>5% decline in 1-3 days)
        2. Consolidation base (tight range, 2-5 days)
        3. Strong rally (>3% move up)
        
        Returns list of demand zones with zone_low, zone_high, strength
        """
        zones = []
        
        if len(self.df) < 10:
            return zones
        
        # Calculate ATR for volatility reference
        atr = (self.df['High'] - self.df['Low']).rolling(14).mean()
        
        for i in range(10, len(self.df) - 5):
            # Look for drop phase (1-3 days back)
            drop_start = i - 3
            drop_end = i
            
            if drop_start < 0:
                continue
                
            drop_pct = ((self.df['Close'].iloc[drop_end] - self.df['Close'].iloc[drop_start]) / 
                       self.df['Close'].iloc[drop_start]) * 100
            
            # Must be a significant drop
            if drop_pct > -5:
                continue
            
            # Look for consolidation base (next 2-5 days)
            base_start = i
            base_end = min(i + 5, len(self.df) - 1)
            base_range = self.df.iloc[base_start:base_end]
            
            if len(base_range) < 2:
                continue
            
            # Base should have low volatility
            base_atr = (base_range['High'] - base_range['Low']).mean()
            avg_atr = atr.iloc[i]
            
            if pd.isnull(avg_atr) or base_atr > (avg_atr * 0.6):
                continue  # Too volatile for a base
            
            # Look for rally after base
            rally_start = base_end
            rally_end = min(rally_start + 3, len(self.df))
            
            if rally_end >= len(self.df):
                continue
            
            rally_pct = ((self.df['Close'].iloc[rally_end] - self.df['Close'].iloc[rally_start]) / 
                        self.df['Close'].iloc[rally_start]) * 100
            
            # Must rally at least 3%
            if rally_pct < 3:
                continue
            
            # Zone found - the base is the demand zone
            zone_low = base_range['Low'].min()
            zone_high = base_range['High'].max()
            
            # Calculate zone strength based on volume and freshness
            base_volume = base_range['Volume'].mean()
            avg_volume = self.df['Volume'].tail(20).mean()
            volume_strength = base_volume / avg_volume if avg_volume > 0 else 1.0
            
            zones.append({
                'zone_low': float(zone_low),
                'zone_high': float(zone_high),
                'formation_index': base_start,
                'strength': float(volume_strength),
                'type': 'demand'
            })
        
        return zones
    
    def detect_supply_zones(self) -> list:
        """
        Find Rally-Base-Drop (RBD) patterns that indicate supply zones.
        
        Pattern:
        1. Strong rally (>5% gain in 1-3 days)
        2. Consolidation base (tight range, 2-5 days)
        3. Strong drop (>3% move down)
        
        Returns list of supply zones
        """
        zones = []
        
        if len(self.df) < 10:
            return zones
        
        atr = (self.df['High'] - self.df['Low']).rolling(14).mean()
        
        for i in range(10, len(self.df) - 5):
            # Look for rally phase
            rally_start = i - 3
            rally_end = i
            
            if rally_start < 0:
                continue
                
            rally_pct = ((self.df['Close'].iloc[rally_end] - self.df['Close'].iloc[rally_start]) / 
                        self.df['Close'].iloc[rally_start]) * 100
            
            if rally_pct < 5:
                continue
            
            # Look for consolidation base
            base_start = i
            base_end = min(i + 5, len(self.df) - 1)
            base_range = self.df.iloc[base_start:base_end]
            
            if len(base_range) < 2:
                continue
            
            base_atr = (base_range['High'] - base_range['Low']).mean()
            avg_atr = atr.iloc[i]
            
            if pd.isnull(avg_atr) or base_atr > (avg_atr * 0.6):
                continue
            
            # Look for drop after base
            drop_start = base_end
            drop_end = min(drop_start + 3, len(self.df))
            
            if drop_end >= len(self.df):
                continue
            
            drop_pct = ((self.df['Close'].iloc[drop_end] - self.df['Close'].iloc[drop_start]) / 
                       self.df['Close'].iloc[drop_start]) * 100
            
            if drop_pct > -3:
                continue
            
            zone_low = base_range['Low'].min()
            zone_high = base_range['High'].max()
            
            base_volume = base_range['Volume'].mean()
            avg_volume = self.df['Volume'].tail(20).mean()
            volume_strength = base_volume / avg_volume if avg_volume > 0 else 1.0
            
            zones.append({
                'zone_low': float(zone_low),
                'zone_high': float(zone_high),
                'formation_index': base_start,
                'strength': float(volume_strength),
                'type': 'supply'
            })
        
        return zones
    
    def get_current_zone_type(self) -> str:
        """
        Determine if current price is in a demand zone, supply zone, or neutral.
        
        Returns:
            'demand' - Price in demand zone (good for buying)
            'supply' - Price in supply zone (avoid)
            'neutral' - Not in any clear zone
        """
        if len(self.df) < 20:
            return 'neutral'
        
        current_price = float(self.df['Close'].iloc[-1])
        
        # Get recent zones (last 50 bars)
        demand_zones = self.detect_demand_zones()
        supply_zones = self.detect_supply_zones()
        
        # Filter to recent zones only
        recent_cutoff = len(self.df) - 50
        demand_zones = [z for z in demand_zones if z['formation_index'] > recent_cutoff]
        supply_zones = [z for z in supply_zones if z['formation_index'] > recent_cutoff]
        
        # Check if current price is in any demand zone
        for zone in demand_zones:
            if zone['zone_low'] <= current_price <= zone['zone_high']:
                return 'demand'
            # Also check if price is slightly above zone (within 2%)
            if zone['zone_high'] < current_price <= zone['zone_high'] * 1.02:
                return 'demand'
        
        # Check if in supply zone
        for zone in supply_zones:
            if zone['zone_low'] <= current_price <= zone['zone_high']:
                return 'supply'
            # Also check if price is slightly below zone
            if zone['zone_low'] * 0.98 <= current_price < zone['zone_low']:
                return 'supply'
        
        return 'neutral'
    
    def get_position_in_range(self, period: int = 20) -> float:
        """
        Calculate current price position in recent range.
        
        Returns:
            0.0 = At the low of range (good for buying)
            1.0 = At the high of range (avoid)
            0.5 = Middle of range
        """
        if len(self.df) < period:
            return 0.5
        
        recent = self.df.tail(period)
        range_high = recent['High'].max()
        range_low = recent['Low'].min()
        current_price = float(self.df['Close'].iloc[-1])
        
        if range_high == range_low:
            return 0.5
        
        position = (current_price - range_low) / (range_high - range_low)
        return float(position)
