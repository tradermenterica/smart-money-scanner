import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('scanner.db')
cursor = conn.cursor()

# Get ALL stocks without filtering by score
cursor.execute('SELECT symbol, score, price, passed_financials, details FROM stocks ORDER BY symbol')
rows = cursor.fetchall()

print(f"\n{'='*80}")
print(f"Todos los activos en la base de datos ({len(rows)} total):")
print(f"{'='*80}\n")

for row in rows:
    symbol, score, price, passed_fin, details_json = row
    details = json.loads(details_json)
    
    print(f"\n{'─'*80}")
    print(f"Symbol: {symbol}")
    print(f"Score: {score}")
    print(f"Price: ${price:.2f}")
    print(f"Passed Financials: {'✓' if passed_fin else '✗'}")
    
    # Fundamentals
    fund = details.get('fundamentals', {})
    print(f"\nFundamentals:")
    print(f"  - Passed: {fund.get('passed', False)}")
    if 'details' in fund:
        print(f"  - P/E: {fund['details'].get('pe', 'N/A')}")
        print(f"  - Debt/Equity: {fund['details'].get('debt_to_equity', 'N/A')}")
        print(f"  - ROE: {fund['details'].get('roe', 'N/A')}")
    if 'failure_reasons' in fund:
        print(f"  - Failures: {', '.join(fund['failure_reasons'])}")
    
    # Technicals
    tech = details.get('technicals', {})
    print(f"\nTechnicals:")
    print(f"  - Trend: {tech.get('trend', 'N/A')}")
    print(f"  - RVOL: {tech.get('rvol', 'N/A')}")
    print(f"  - Squeeze: {tech.get('squeeze', False)}")
    print(f"  - VCP: {tech.get('vcp', False)}")
    
    # Institutional
    inst = details.get('institutional', {})
    print(f"\nInstitutional:")
    print(f"  - Detected: {inst.get('detected', False)}")
    print(f"  - Score: {inst.get('institutional_score', 0)}")
    print(f"  - Signals: {', '.join(inst.get('signals', [])) if inst.get('signals') else 'None'}")

print(f"\n{'='*80}\n")

conn.close()
