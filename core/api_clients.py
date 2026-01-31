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


class AlphaVantageClient:
    """
    Client for Alpha Vantage API with rate limiting.
    Free tier: 25 calls/day (very limited, use sparingly)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.base_url = "https://www.alphavantage.co/query"
        self.last_call_time = 0
        self.min_interval = 12.0  # 12 seconds between calls (safe for 25/day = ~5/hour)
        self.daily_calls = 0
        self.max_daily_calls = 25
    
    def _rate_limit(self):
        """Ensures we don't exceed rate limits"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Makes a rate-limited request to Alpha Vantage API"""
        if not self.api_key:
            print("[ALPHA_VANTAGE] API key not configured")
            return None
        
        if self.daily_calls >= self.max_daily_calls:
            print(f"[ALPHA_VANTAGE] Daily limit reached ({self.max_daily_calls} calls)")
            return None
        
        self._rate_limit()
        
        try:
            params['apikey'] = self.api_key
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API limit message
                if 'Note' in data or 'Information' in data:
                    print(f"[ALPHA_VANTAGE] Rate limit warning: {data}")
                    return None
                
                self.daily_calls += 1
                return data
            else:
                print(f"[ALPHA_VANTAGE] Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"[ALPHA_VANTAGE] Request failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Tests if API key is valid"""
        result = self._make_request({
            "function": "GLOBAL_QUOTE",
            "symbol": "AAPL"
        })
        return result is not None and 'Global Quote' in result
    
    def get_news_sentiment(self, symbol: str, limit: int = 50) -> Optional[Dict]:
        """
        Gets news sentiment for a ticker.
        Returns aggregated sentiment score and article details.
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "limit": limit
        }
        
        data = self._make_request(params)
        if not data or 'feed' not in data:
            return None
        
        articles = data['feed']
        if not articles:
            return None
        
        # Calculate aggregated sentiment
        total_sentiment = 0
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for article in articles:
            # Get ticker-specific sentiment
            ticker_sentiments = article.get('ticker_sentiment', [])
            for ts in ticker_sentiments:
                if ts.get('ticker') == symbol:
                    sentiment_score = float(ts.get('ticker_sentiment_score', 0))
                    total_sentiment += sentiment_score
                    
                    if sentiment_score > 0.15:
                        positive_count += 1
                    elif sentiment_score < -0.15:
                        negative_count += 1
                    else:
                        neutral_count += 1
        
        total_articles = len(articles)
        avg_sentiment = total_sentiment / total_articles if total_articles > 0 else 0
        
        return {
            "average_sentiment": float(avg_sentiment),
            "total_articles": total_articles,
            "positive_articles": positive_count,
            "negative_articles": negative_count,
            "neutral_articles": neutral_count,
            "sentiment_label": self._get_sentiment_label(avg_sentiment),
            "recent_headlines": [
                {
                    "title": a.get('title', ''),
                    "source": a.get('source', ''),
                    "time_published": a.get('time_published', ''),
                    "sentiment": next((ts.get('ticker_sentiment_score', 0) 
                                     for ts in a.get('ticker_sentiment', []) 
                                     if ts.get('ticker') == symbol), 0)
                }
                for a in articles[:5]  # Top 5 recent articles
            ]
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """Converts sentiment score to label"""
        if score > 0.25:
            return "Bullish"
        elif score > 0.05:
            return "Somewhat-Bullish"
        elif score < -0.25:
            return "Bearish"
        elif score < -0.05:
            return "Somewhat-Bearish"
        else:
            return "Neutral"
    
    def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """
        Gets comprehensive company fundamentals.
        Better than yfinance for some metrics.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol
        }
        
        data = self._make_request(params)
        if not data or 'Symbol' not in data:
            return None
        
        return {
            "symbol": data.get('Symbol', ''),
            "name": data.get('Name', ''),
            "description": data.get('Description', ''),
            "sector": data.get('Sector', ''),
            "industry": data.get('Industry', ''),
            "market_cap": float(data.get('MarketCapitalization', 0)),
            "pe_ratio": float(data.get('PERatio', 0)),
            "peg_ratio": float(data.get('PEGRatio', 0)),
            "book_value": float(data.get('BookValue', 0)),
            "dividend_yield": float(data.get('DividendYield', 0)),
            "eps": float(data.get('EPS', 0)),
            "revenue_per_share": float(data.get('RevenuePerShareTTM', 0)),
            "profit_margin": float(data.get('ProfitMargin', 0)),
            "operating_margin": float(data.get('OperatingMarginTTM', 0)),
            "roe": float(data.get('ReturnOnEquityTTM', 0)),
            "roa": float(data.get('ReturnOnAssetsTTM', 0)),
            "analyst_target_price": float(data.get('AnalystTargetPrice', 0)),
            "52_week_high": float(data.get('52WeekHigh', 0)),
            "52_week_low": float(data.get('52WeekLow', 0))
        }

