import requests
import time
from typing import Optional, Dict, List
import os

class FinnhubClient:
    """
    Client for Finnhub API with rate limiting and error handling.
    Free tier: 60 calls/minute
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")
        self.base_url = "https://finnhub.io/api/v1"
        self.last_call_time = 0
        self.min_interval = 1.0  # 1 second between calls (safe for 60/min limit)
        
    def _rate_limit(self):
        """Ensures we don't exceed rate limits"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Makes a rate-limited request to Finnhub API"""
        if not self.api_key:
            print("[FINNHUB] API key not configured")
            return None
            
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/{endpoint}"
            params = params or {}
            params['token'] = self.api_key
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"[FINNHUB] Rate limit exceeded, waiting...")
                time.sleep(60)  # Wait 1 minute
                return self._make_request(endpoint, params)
            else:
                print(f"[FINNHUB] Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"[FINNHUB] Request failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Tests if API key is valid"""
        result = self._make_request("quote", {"symbol": "AAPL"})
        return result is not None and 'c' in result
    
    def get_institutional_ownership(self, symbol: str) -> Optional[Dict]:
        """
        Gets institutional ownership data.
        Returns: List of institutional holders with shares and changes
        """
        data = self._make_request("stock/institutional-ownership", {"symbol": symbol})
        if not data or 'data' not in data:
            return None
            
        # Calculate total institutional ownership
        total_shares = sum(holder.get('share', 0) for holder in data['data'])
        total_change = sum(holder.get('change', 0) for holder in data['data'])
        
        return {
            "total_holders": len(data['data']),
            "total_shares": total_shares,
            "total_change": total_change,
            "change_percentage": (total_change / total_shares * 100) if total_shares > 0 else 0,
            "top_holders": data['data'][:5]  # Top 5 holders
        }
    
    def get_insider_transactions(self, symbol: str, days: int = 30) -> Optional[Dict]:
        """
        Gets insider transactions (buys/sells) for the last N days.
        """
        # Calculate date range
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "symbol": symbol,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        
        data = self._make_request("stock/insider-transactions", params)
        if not data or 'data' not in data:
            return None
        
        transactions = data['data']
        
        # Separate buys and sells
        buys = [t for t in transactions if t.get('transactionCode') in ['P', 'A']]  # P=Purchase, A=Award
        sells = [t for t in transactions if t.get('transactionCode') == 'S']  # S=Sale
        
        total_buy_shares = sum(t.get('share', 0) for t in buys)
        total_sell_shares = sum(t.get('share', 0) for t in sells)
        
        return {
            "buy_transactions": len(buys),
            "sell_transactions": len(sells),
            "total_buy_shares": total_buy_shares,
            "total_sell_shares": total_sell_shares,
            "net_shares": total_buy_shares - total_sell_shares,
            "insider_buying": total_buy_shares > total_sell_shares,
            "recent_transactions": transactions[:10]  # Last 10 transactions
        }
    
    def get_recommendation_trends(self, symbol: str) -> Optional[Dict]:
        """
        Gets analyst recommendation trends (buy/hold/sell).
        """
        data = self._make_request("stock/recommendation", {"symbol": symbol})
        if not data or len(data) == 0:
            return None
        
        # Get most recent recommendation
        latest = data[0]
        
        total = latest.get('buy', 0) + latest.get('hold', 0) + latest.get('sell', 0)
        if total == 0:
            return None
        
        buy_percentage = latest.get('buy', 0) / total * 100
        
        return {
            "buy": latest.get('buy', 0),
            "hold": latest.get('hold', 0),
            "sell": latest.get('sell', 0),
            "strong_buy": latest.get('strongBuy', 0),
            "strong_sell": latest.get('strongSell', 0),
            "buy_percentage": buy_percentage,
            "period": latest.get('period', 'N/A')
        }
    
    def get_price_target(self, symbol: str) -> Optional[Dict]:
        """
        Gets analyst price target consensus.
        """
        data = self._make_request("stock/price-target", {"symbol": symbol})
        if not data:
            return None
        
        return {
            "target_high": data.get('targetHigh', 0),
            "target_low": data.get('targetLow', 0),
            "target_mean": data.get('targetMean', 0),
            "target_median": data.get('targetMedian', 0),
            "last_updated": data.get('lastUpdated', 'N/A')
        }
    
    def get_news_sentiment(self, symbol: str) -> Optional[Dict]:
        """
        Gets news sentiment for a symbol.
        """
        data = self._make_request("news-sentiment", {"symbol": symbol})
        if not data:
            return None
        
        return {
            "sentiment_score": data.get('sentiment', {}).get('score', 0),
            "buzz": data.get('buzz', {}).get('buzz', 0),
            "articles_in_last_week": data.get('buzz', {}).get('articlesInLastWeek', 0),
            "positive_mentions": data.get('sentiment', {}).get('positive', 0),
            "negative_mentions": data.get('sentiment', {}).get('negative', 0)
        }
    
    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """
        Gets basic company information.
        """
        data = self._make_request("stock/profile2", {"symbol": symbol})
        if not data:
            return None
        
        return {
            "name": data.get('name', ''),
            "ticker": data.get('ticker', ''),
            "market_cap": data.get('marketCapitalization', 0),
            "shares_outstanding": data.get('shareOutstanding', 0),
            "industry": data.get('finnhubIndustry', 'N/A')
        }
