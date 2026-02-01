
import sqlite3
import pandas as pd
import sys
import os
import asyncio
from core.data import DataFetcher

# Add current directory to path to import core modules
sys.path.append(os.getcwd())

DB_NAME = "scanner.db"

def get_tickers_from_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM stocks")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

async def find_drops():
    print("Reading tickers from database...")
    tickers = get_tickers_from_db()
    
    if not tickers:
        print("No tickers found in database.")
        return

    print(f"Found {len(tickers)} tickers in DB. Fetching live data...")
    sys.stdout.flush()
    
    # Batch fetch data - fetching 5 days to ensure we have previous close
    batch_data = DataFetcher.get_batch_history(tickers, period="5d")
    sys.stdout.flush()
    
    if batch_data.empty:
        print("Could not fetch data.")
        return

    drops = []
    
    print("Analyzing daily performance...")
    
    print(f"Batch data columns: {batch_data.columns[:5]}")
    
    for symbol in tickers:
        try:
            df = pd.DataFrame()
            # Try to get data for symbol
            try:
                # Common yfinance structure: (Price, Ticker) -> access via level 1
                if isinstance(batch_data.columns, pd.MultiIndex):
                    try:
                        df = batch_data.xs(symbol, axis=1, level=1)
                    except KeyError:
                        try:
                            df = batch_data[symbol]
                        except KeyError:
                             # print(f"Ticker {symbol} not found in columns")
                             continue
                else:
                    # Flat index
                    if len(tickers) == 1 and symbol == tickers[0]:
                        df = batch_data
                    else:
                        continue
            except Exception as e:
                print(f"Extraction error {symbol}: {e}")
                continue
            
            if df.empty or len(df) < 2:
                continue
                
            # Get latest two candles
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            # Calculate daily change % based on Previous Close
            # (Current - PrevClose) / PrevClose
            prev_close = prev_candle['Close']
            current_price = last_candle['Close']
            
            if prev_close == 0:
                continue
                
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            if change_pct <= -5.0:
                drops.append({
                    "symbol": symbol,
                    "change_pct": change_pct,
                    "price": current_price,
                    "prev_close": prev_close
                })
                
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    # Sort by biggest drop
    drops.sort(key=lambda x: x['change_pct'])

    # Save to JSON for reliable reading
    import json
    with open('drops.json', 'w') as f:
        json.dump(drops, f, indent=4)

    print("\n" + "="*50)
    print(f"STOCKS WITH > 5% DROP TODAY (from {len(tickers)} examined)")
    print("="*50)
    
    if drops:
        print(f"{'SYMBOL':<10} {'DROP %':<10} {'PRICE':<10}")
        print("-" * 35)
        for d in drops:
            print(f"{d['symbol']:<10} {d['change_pct']:>6.2f}%    ${d['price']:.2f}")
    else:
        print("No stocks found with a 5% drop today.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(find_drops())
