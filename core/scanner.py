from core.data import DataFetcher
from core.financials import FundamentalAnalyzer
from core.technicals import TechnicalAnalyzer
from core.institutional import InstitutionalDetector
from core.database import DatabaseManager
from core.money_flow import MoneyFlowDetector
from core.zones import ZoneDetector
import concurrent.futures
import time
import pandas as pd

class Scanner:
    def __init__(self):
        self.db = DatabaseManager()
        # Initialize DB tables
        self.db.init_db()

    def scan_ticker(self, symbol: str) -> dict:
        """
        Runs the full scan analysis on a single ticker.
        """
        result = {
            "symbol": symbol,
            "passed_financials": False,
            "potential_buy": False,
            "score": 0,
            "details": {}
        }
        
        try:
            # 1. Fundamental Check
            fund_analyzer = FundamentalAnalyzer(symbol)
            fund_res = fund_analyzer.is_financially_solid()
            result["details"]["fundamentals"] = fund_res
            
            # 2. Get Data
            df = DataFetcher.get_history(symbol)
            if df.empty:
                return result

            # 3. Technical Analysis
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            tech_res = tech.check_setup()
            
            # 4. Institutional Analysis
            inst = InstitutionalDetector(df)
            inst.analyze_flows()
            inst_res = inst.detect_smart_money()
            
            # Scoring Logic
            score = 0
            if fund_res["passed"]: score += 30
            if tech_res["trend"] == "Uptrend": score += 20
            if tech_res["rvol"] > 1.5: score += 15
            if inst_res["detected"]: score += 25
            if tech_res["squeeze"]: score += 10
            
            result["score"] = score
            result["potential_buy"] = score > 60
            result["passed_financials"] = fund_res["passed"]
            
            result["details"]["technicals"] = tech_res
            result["details"]["institutional"] = inst_res

            # Save to cleanup memory
            # Note: We return result for immediate usage if needed, but primary goal is DB save
            return result
            
        except Exception as e:
            # print(f"Error scanning {symbol}: {e}")
            return None

    def process_batch(self, batch_symbols: list):
        """
        Procesa un lote de tickers descargando sus precios a la vez.
        """
        # Descarga masiva de precios (Batch)
        batch_data = DataFetcher.get_batch_history(batch_symbols)
        if batch_data.empty: return

        for symbol in batch_symbols:
            try:
                # Extraer el DataFrame de este símbolo del objeto multi-ticker
                if isinstance(batch_data.columns, pd.MultiIndex):
                    try:
                        df = batch_data[symbol]
                    except KeyError:
                        try:
                            df = batch_data.xs(symbol, axis=1, level=1)
                        except:
                            continue
                else:
                    df = batch_data if len(batch_symbols) == 1 else pd.DataFrame()
                
                if df.empty or 'Close' not in df.columns or df['Close'].isnull().all():
                    continue

                print(f"    [CHECK] {symbol} (Drawdown/Volume)...")

                # 1. Filtro Técnico Rápido (Se hace en memoria, es instantáneo)
                tech = TechnicalAnalyzer(df)
                tech.calculate_indicators()
                tech_res = tech.check_setup()

                # Si no tiene tendencia o volumen, lo ignoramos para ahorrar peticiones fundamentales
                if tech_res["trend"] == "Neutral" and tech_res["rvol"] < 1.2:
                    continue

                # 2. Deep Dive (Solo para candidatos interesantes)
                # Aquí es donde descargamos los fundamentales (petición individual)
                fund_analyzer = FundamentalAnalyzer(symbol)
                fund_res = fund_analyzer.is_financially_solid()
                
                # 3. Institutional Analysis
                inst = InstitutionalDetector(df)
                inst.analyze_flows()
                inst_res = inst.detect_smart_money()

                # ========================================
                # COMPLETE REWRITE: SMART MONEY DIP BUY DETECTION
                # Pattern: CNC, APOV (pullback + accumulation)
                # Reject: XOM, CAT, COST (active rallies)
                # ========================================
                
                # ========================================
                # STRICT FILTER 1: PULLBACK DETECTION
                # Stock MUST be in -15% to -50% pullback from 60-day high
                # ========================================
                high_60d = float(df['High'].tail(60).max())
                current_price = float(df['Close'].iloc[-1])
                drawdown_pct = ((current_price - high_60d) / high_60d) * 100
                
                # REJECT if not in pullback range
                if not (-50 < drawdown_pct < -15):
                    continue  # Skip - No significant pullback (XOM/CAT/COST rejected here)
                
                # ========================================
                # STRICT FILTER 2: MONEY FLOW DURING PULLBACK
                # Signals MUST appear while price is NOT rallying
                # ========================================
                mf_detector = MoneyFlowDetector(df)
                pullback_acc = mf_detector.detect_pullback_accumulation(lookback=10)
                
                # REJECT if no accumulation during pullback
                if not pullback_acc['has_pullback_accumulation']:
                    continue  # Skip - No accumulation OR signals during rally
                
                # ========================================
                # STRICT FILTER 3: SUPPORT ZONE POSITION
                # Price MUST be in lower 40% of 60-day range
                # ========================================
                low_60d = float(df['Low'].tail(60).min())
                range_60d = high_60d - low_60d
                if range_60d > 0:
                    position_60d = (current_price - low_60d) / range_60d
                else:
                    position_60d = 0.5
                
                # REJECT if too high in range
                if position_60d > 0.40:
                    continue  # Skip - Not in support zone
                
                # ========================================
                # PASSED ALL 3 FILTERS - VALID SETUP
                # ========================================
                
                # Simple scoring for valid setups
                score = 70  # Base score for passing all filters
                
                # Bonus for setup strength
                if pullback_acc['signal_count'] >= 3:
                    score += 15  # Multiple signals
                if abs(drawdown_pct) > 30:
                    score += 10  # Deep pullback (more upside potential)
                if position_60d < 0.25:
                    score += 10  # Very low in range
                
                # Institutional confirmation
                if inst_res["detected"]:
                    score += 10
                
                # Fundamentals
                if fund_res["passed"]:
                    score += 5

                # Prepare result with detailed info
                tech_res['pullback_pct'] = round(drawdown_pct, 2)
                tech_res['mf_signals'] = pullback_acc['signal_count']
                tech_res['price_action'] = pullback_acc['price_action']
                tech_res['range_position_60d'] = round(position_60d, 2)
                
                result = {
                    "symbol": symbol,
                    "passed_financials": fund_res["passed"],
                    "score": min(score, 100),
                    "details": {
                        "fundamentals": fund_res,
                        "technicals": tech_res,
                        "institutional": inst_res,
                        "setup_type": "Smart Money Dip Buy"
                    }
                }
                self.db.save_result(result)
            except Exception as e:
                pass  # Silencioso para no ensuciar logs masivos

    def run_full_scan_to_db(self, tickers: list):
        """
        Ejecuta el escaneo por lotes de 100 en 100.
        """
        chunk_size = 100
        total = len(tickers)
        print(f"[SCANNER] Iniciando escaneo inteligente de {total} activos...")
        
        # Dividimos en chunks para no saturar la API de Yahoo
        for i in range(0, total, chunk_size):
            chunk = tickers[i : i + chunk_size]
            print(f"  -> Procesando lote {i//chunk_size + 1} ({i}/{total})...")
            # Update global status if possible (assuming worker_status is imported or accessible)
            # For now, print is the safest for logs
            self.process_batch(chunk)
            time.sleep(2) # Respiro más largo para evitar rate-limiting en la nube
            
        print(f"[SCANNER] Escaneo completo.")

    def get_results_from_db(self, min_score: int = 0, limit: int = 10) -> list:
        """
        Reads results directly from the database.
        """
        return self.db.get_top_stocks(min_score=min_score, limit=limit)
