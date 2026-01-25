import sqlite3
import json
import os
from datetime import datetime

DB_NAME = "scanner.db"

class DatabaseManager:
    def __init__(self):
        self.conn = None

    def get_connection(self):
        # Check if we need to create thread-local connection or new connection
        return sqlite3.connect(DB_NAME, check_same_thread=False)

    def init_db(self):
        """Creates the necessary tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Table for storing scan results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                score INTEGER,
                price REAL,
                last_updated DATETIME,
                details TEXT,
                signals TEXT,
                passed_financials BOOLEAN
            )
        ''')
        
        # Index on score for fast retrieval
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON stocks (score)')
        
        conn.commit()
        conn.close()

    def save_result(self, result: dict):
        """Saves or updates a single scan result."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (symbol, score, price, last_updated, details, signals, passed_financials)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['symbol'],
                result['score'],
                result.get('details', {}).get('technicals', {}).get('last_close', 0),
                datetime.now(),
                json.dumps(result['details']),
                json.dumps(result.get('details', {}).get('institutional', {}).get('signals', [])),
                result['passed_financials']
            ))
            conn.commit()
        except Exception as e:
            print(f"DB Error saving {result['symbol']}: {e}")
        finally:
            conn.close()

    def get_top_stocks(self, limit=10, min_score=0):
        """Retrieves top stocks from DB."""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stocks 
            WHERE score >= ? 
            ORDER BY score DESC 
            LIMIT ?
        ''', (min_score, limit))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "symbol": row['symbol'],
                "score": row['score'],
                "price": row['price'],
                "passed_financials": bool(row['passed_financials']),
                "details": json.loads(row['details']),
                "signals": json.loads(row['signals'])
            })
            
        conn.close()
        return results

    def clear_all(self):
        """Borra todos los registros de la tabla de acciones."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM stocks')
            conn.commit()
            print("[INFO] Base de datos limpiada correctamente.")
        except Exception as e:
            print(f"[ERROR] No se pudo limpiar la base de datos: {e}")
        finally:
            conn.close()

    def count_stocks(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM stocks')
        count = cursor.fetchone()[0]
        conn.close()
        return count
