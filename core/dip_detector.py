import pandas as pd
import numpy as np
from typing import Dict, Optional
from core.api_clients import FinnhubClient
from core.data import DataFetcher
from core.technicals import TechnicalAnalyzer
from core.financials import FundamentalAnalyzer

class DipDetector:
    """
    Detects institutional dip buying opportunities.
    Looks for stocks with significant price drops showing institutional accumulation.
    """
    
    def __init__(self):
        self.finnhub = FinnhubClient()
        from core.api_clients import AlphaVantageClient
        self.alpha_vantage = AlphaVantageClient()
    
    def calculate_drawdown(self, df: pd.DataFrame, period: int = 20) -> Dict:
        """
        Calculates drawdown from recent high.
        Returns drawdown percentage and days from high.
        """
        if df.empty or len(df) < period:
            return {"drawdown_pct": 0, "days_from_high": 0, "is_dip": False}
        
        # Calculate rolling maximum
        rolling_max = df['Close'].rolling(window=period).max()
        current_price = df['Close'].iloc[-1]
        recent_high = rolling_max.iloc[-1]
        
        # Drawdown percentage
        drawdown_pct = ((current_price - recent_high) / recent_high) * 100
        
        # Days since high
        high_indices = df[df['Close'] == rolling_max.iloc[-1]].index
        if len(high_indices) > 0:
            days_from_high = len(df) - df.index.get_loc(high_indices[-1]) - 1
        else:
            days_from_high = 0
        
        # Is this a "dip" we're interested in? (-10% to -30%)
        is_dip = -30 <= drawdown_pct <= -10
        
        return {
            "drawdown_pct": float(drawdown_pct),
            "recent_high": float(recent_high),
            "current_price": float(current_price),
            "days_from_high": int(days_from_high),
            "is_dip": bool(is_dip)
        }
    
    def detect_obv_divergence(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """
        Detects bullish divergence: price down but OBV up.
        This indicates institutional accumulation during the dip.
        """
        if df.empty or len(df) < lookback or 'OBV' not in df.columns:
            return False
        
        # Price trend (last 5 days)
        price_change = df['Close'].pct_change(lookback).iloc[-1]
        
        # OBV trend (last 5 days)
        obv_change = df['OBV'].pct_change(lookback).iloc[-1]
        
        # Bullish divergence: price down, OBV up
        divergence = (price_change < 0) and (obv_change > 0)
        
        return bool(divergence)
    
    def check_support_level(self, df: pd.DataFrame) -> Dict:
        """
        Checks if price is near key support levels (SMA 50/200).
        """
        if df.empty or len(df) < 50:
            return {"near_sma50": False, "near_sma200": False}
        
        last = df.iloc[-1]
        current_price = last['Close']
        
        # Check if price is within 5% of SMA 50 or 200
        near_sma50 = False
        near_sma200 = False
        
        if 'SMA_50' in df.columns and pd.notnull(last['SMA_50']):
            distance_50 = abs(current_price - last['SMA_50']) / last['SMA_50']
            near_sma50 = distance_50 < 0.05
        
        if 'SMA_200' in df.columns and pd.notnull(last['SMA_200']):
            distance_200 = abs(current_price - last['SMA_200']) / last['SMA_200']
            near_sma200 = distance_200 < 0.05
        
        return {
            "near_sma50": bool(near_sma50),
            "near_sma200": bool(near_sma200),
            "at_support": near_sma50 or near_sma200
        }
    
    def score_institutional_data(self, symbol: str, current_price: float) -> Dict:
        """
        Fetches and scores institutional data from Finnhub.
        Returns institutional score (0-40 points) and details.
        """
        score = 0
        details = {}
        
        # 1. Institutional Ownership (0-10 pts)
        inst_ownership = self.finnhub.get_institutional_ownership(symbol)
        if inst_ownership:
            ownership_pct = inst_ownership.get('change_percentage', 0)
            
            # High institutional ownership is good
            if ownership_pct > 60:
                score += 10
            elif ownership_pct > 40:
                score += 5
            
            # Institutional buying (positive change) is very good
            if inst_ownership.get('total_change', 0) > 0:
                score += 15
            
            details['institutional_ownership'] = inst_ownership
        
        # 2. Insider Transactions (0-15 pts)
        insider_data = self.finnhub.get_insider_transactions(symbol, days=30)
        if insider_data:
            # Insider buying is a strong signal
            if insider_data.get('insider_buying', False):
                score += 15
            
            # No insider selling is a bonus
            if insider_data.get('sell_transactions', 0) == 0 and insider_data.get('buy_transactions', 0) > 0:
                score += 5
            
            details['insider_transactions'] = insider_data
        
        # 3. Analyst Recommendations (0-10 pts)
        recommendations = self.finnhub.get_recommendation_trends(symbol)
        if recommendations:
            buy_pct = recommendations.get('buy_percentage', 0)
            
            if buy_pct > 60:
                score += 10
            elif buy_pct > 40:
                score += 5
            
            details['recommendations'] = recommendations
        
        # 4. Price Target (0-10 pts)
        price_target = self.finnhub.get_price_target(symbol)
        if price_target and current_price > 0:
            target_mean = price_target.get('target_mean', 0)
            upside = ((target_mean - current_price) / current_price) * 100
            
            if upside > 15:
                score += 10
            elif upside > 5:
                score += 5
            
            details['price_target'] = price_target
            details['upside_potential'] = float(upside)
        
        return {
            "institutional_score": min(score, 40),  # Cap at 40
            "details": details
        }
    
    def score_sentiment(self, symbol: str) -> Dict:
        """
        Scores news sentiment (0-15 pts).
        Uses Alpha Vantage (primary) with Finnhub fallback.
        Negative sentiment during a dip can be noise, but we want to avoid disasters.
        """
        score = 0
        details = {}
        
        # Try Alpha Vantage first (better sentiment analysis)
        av_sentiment = self.alpha_vantage.get_news_sentiment(symbol)
        if av_sentiment:
            avg_sentiment = av_sentiment.get('average_sentiment', 0)
            sentiment_label = av_sentiment.get('sentiment_label', 'Neutral')
            
            # Alpha Vantage scoring (more granular)
            if avg_sentiment > 0.15:  # Bullish
                score += 15
            elif avg_sentiment > 0.05:  # Somewhat bullish
                score += 10
            elif avg_sentiment > -0.15:  # Neutral (okay for dips)
                score += 7
            elif avg_sentiment > -0.3:  # Slightly bearish (acceptable)
                score += 5
            # Below -0.3 = 0 points (avoid)
            
            details['source'] = 'AlphaVantage'
            details['sentiment_data'] = av_sentiment
            details['sentiment_label'] = sentiment_label
            
        else:
            # Fallback to Finnhub
            sentiment_data = self.finnhub.get_news_sentiment(symbol)
            if sentiment_data:
                sentiment_score = sentiment_data.get('sentiment_score', 0)
                
                # Finnhub scoring (original logic)
                if sentiment_score > -0.3:
                    score += 10
                elif sentiment_score > -0.5:
                    score += 5
                
                details['source'] = 'Finnhub'
                details['sentiment_data'] = sentiment_data
        
        return {
            "sentiment_score": score,
            "details": details
        }
    
    def analyze_dip_opportunity(self, symbol: str) -> Optional[Dict]:
        """
        Full analysis of a potential dip buying opportunity.
        Returns score (0-100) and detailed breakdown.
        """
        try:
            # Get price data
            df = DataFetcher.get_history(symbol)
            if df.empty or len(df) < 50:
                return None
            
            # Calculate technical indicators
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            
            # Calculate OBV for divergence detection
            from core.institutional import InstitutionalDetector
            inst_detector = InstitutionalDetector(df)
            inst_detector.analyze_flows()
            
            current_price = df['Close'].iloc[-1]
            
            # === SCORING SYSTEM ===
            total_score = 0
            breakdown = {}
            
            # A. Technical Dip Analysis (0-30 pts)
            drawdown = self.calculate_drawdown(df, period=20)
            breakdown['drawdown'] = drawdown
            
            if drawdown['is_dip']:
                total_score += 15
            
            # OBV Divergence (bullish signal)
            obv_divergence = self.detect_obv_divergence(df, lookback=5)
            breakdown['obv_divergence'] = obv_divergence
            if obv_divergence:
                total_score += 10
            
            # Near support level
            support = self.check_support_level(df)
            breakdown['support'] = support
            if support['at_support']:
                total_score += 5
            
            # B. Institutional Conviction (0-40 pts)
            institutional = self.score_institutional_data(symbol, current_price)
            breakdown['institutional'] = institutional
            total_score += institutional['institutional_score']
            
            # C. Sentiment Filter (0-10 pts)
            sentiment = self.score_sentiment(symbol)
            breakdown['sentiment'] = sentiment
            total_score += sentiment['sentiment_score']
            
            # D. Fundamental Quality Check
            fund_analyzer = FundamentalAnalyzer(symbol)
            fund_res = fund_analyzer.is_financially_solid()
            breakdown['fundamentals'] = fund_res
            
            # Bonus points for solid fundamentals
            if fund_res['passed']:
                total_score += 10
            
            # E. Bonus: Strong combo signals
            if drawdown['is_dip'] and obv_divergence and institutional['institutional_score'] > 20:
                total_score += 10  # "Perfect Dip" bonus
            
            return {
                "symbol": symbol,
                "dip_score": min(total_score, 100),
                "is_strong_dip": total_score >= 70,
                "current_price": float(current_price),
                "breakdown": breakdown
            }
            
        except Exception as e:
            print(f"[DIP] Error analyzing {symbol}: {e}")
            return None
