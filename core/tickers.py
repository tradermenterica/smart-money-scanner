import pandas as pd
import io
import requests

class TickerSource:
    @staticmethod
    def get_all_tickers():
        """
        Fetches tickers from NASDAQ, NYSE, AMEX, and ARCA (approx 8000+ total).
        """
    @staticmethod
    def get_all_tickers():
        """
        Obtiene tickers desde una fuente confiable y masiva (NASDAQ, NYSE, AMEX).
        Aproximadamente 6000-8000 activos.
        """
        all_tickers = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Fuente: rreichel3/US-Stock-Symbols (actualizado diariamente)
        sources = [
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.txt",
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nyse/nyse_tickers.txt",
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/amex/amex_tickers.txt"
        ]
        
        print("\n--- Descubrimiento Masivo de Tickers ---")
        
        for url in sources:
            try:
                exchange = url.split('/')[-2].upper()
                print(f"  Consultando {exchange}...")
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    # El formato es una lista de tickers, uno por línea
                    tickers = [t.strip().upper() for t in r.text.split('\n') if t.strip()]
                    all_tickers.extend(tickers)
                    print(f"    [OK] Agregados {len(tickers)} activos.")
                else:
                    print(f"    [FAIL] Error {r.status_code} en {exchange}")
            except Exception as e:
                print(f"    [ERROR] {url}: {e}")

        # Limpieza y filtrado básico para asegurar "Empresas Serias" (longitud de ticker estándar)
        unique = list(set([t for t in all_tickers if 1 <= len(t) <= 5]))
        
        print(f"--- Resultado: {len(unique)} tickers totales encontrados ---")
        
        if len(unique) < 1000:
             print("    [WARNING] Se encontraron pocos tickers, usando fallback...")
             return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
             
        return sorted(unique)
