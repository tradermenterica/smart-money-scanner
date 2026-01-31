# Test Alpha Vantage Integration
import os
os.environ["ALPHA_VANTAGE_API_KEY"] = "GM2XT52NJMY50YE0"
os.environ["FINNHUB_API_KEY"] = "d5grge9r01qll3dk6vtgd5grge9r01qll3dk6vu0"

from core.api_clients import AlphaVantageClient

print("="*60)
print("Testing Alpha Vantage API Integration")
print("="*60)

client = AlphaVantageClient()

# Test 1: Connection
print("\n[TEST 1] API Connection")
if client.test_connection():
    print("✅ Alpha Vantage API connection successful!")
else:
    print("❌ Alpha Vantage API connection failed!")
    exit(1)

# Test 2: News Sentiment
print("\n[TEST 2] News Sentiment Analysis (AAPL)")
print("-" * 60)
sentiment = client.get_news_sentiment("AAPL", limit=50)
if sentiment:
    print(f"✅ Sentiment retrieved successfully!")
    print(f"   Average Sentiment: {sentiment['average_sentiment']:.4f}")
    print(f"   Sentiment Label: {sentiment['sentiment_label']}")
    print(f"   Total Articles: {sentiment['total_articles']}")
    print(f"   Positive: {sentiment['positive_articles']}")
    print(f"   Negative: {sentiment['negative_articles']}")
    print(f"   Neutral: {sentiment['neutral_articles']}")
    print(f"\n   Recent Headlines:")
    for i, headline in enumerate(sentiment['recent_headlines'][:3], 1):
        print(f"   {i}. {headline['title'][:60]}...")
        print(f"      Sentiment: {headline['sentiment']:.3f}")
else:
    print("⚠️  No sentiment data available")

# Test 3: Company Overview
print("\n[TEST 3] Company Overview (NVDA)")
print("-" * 60)
overview = client.get_company_overview("NVDA")
if overview:
    print(f"✅ Company data retrieved!")
    print(f"   Name: {overview['name']}")
    print(f"   Sector: {overview['sector']}")
    print(f"   Industry: {overview['industry']}")
    print(f"   P/E Ratio: {overview['pe_ratio']:.2f}")
    print(f"   ROE: {overview['roe']*100:.2f}%")
    print(f"   Analyst Target: ${overview['analyst_target_price']:.2f}")
else:
    print("⚠️  No company data available")

print("\n" + "="*60)
print("Alpha Vantage Integration Test Complete!")
print(f"API Calls Used: {client.daily_calls}/25")
print("="*60)
