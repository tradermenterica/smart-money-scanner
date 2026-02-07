import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('scanner.db')
cursor = conn.cursor()

# Get total count
cursor.execute('SELECT COUNT(*) FROM stocks')
total = cursor.fetchone()[0]
print(f"\n{'='*60}")
print(f"Total de activos en la DB: {total}")
print(f"{'='*60}\n")

# Get all stocks ordered by score
cursor.execute('SELECT symbol, score, price, passed_financials, signals FROM stocks ORDER BY score DESC LIMIT 50')
rows = cursor.fetchall()

if len(rows) == 0:
    print("❌ No hay resultados en la base de datos!")
else:
    print(f"Top {len(rows)} activos encontrados:\n")
    print(f"{'SYMBOL':<10} {'SCORE':<8} {'PRICE':<12} {'PASSED FIN':<12} {'SIGNALS'}")
    print("-" * 80)
    
    for row in rows:
        symbol, score, price, passed_fin, signals_json = row
        signals = json.loads(signals_json) if signals_json else []
        signals_str = ', '.join(signals[:3]) if signals else "No signals"
        print(f"{symbol:<10} {score:<8} ${price:<11.2f} {'✓' if passed_fin else '✗':<12} {signals_str}")

# Check for specific statistics
cursor.execute('SELECT COUNT(*) FROM stocks WHERE score > 0')
with_score = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM stocks WHERE passed_financials = 1')
passed = cursor.fetchone()[0]

cursor.execute('SELECT AVG(score) FROM stocks')
avg_score = cursor.fetchone()[0] or 0

print(f"\n{'='*60}")
print(f"Estadísticas:")
print(f"  - Activos con score > 0: {with_score}")
print(f"  - Activos que pasaron financials: {passed}")
print(f"  - Score promedio: {avg_score:.2f}")
print(f"{'='*60}\n")

conn.close()
