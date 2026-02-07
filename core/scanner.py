from core.data import DataFetcher
from core.financials import FundamentalAnalyzer
from core.technicals import TechnicalAnalyzer
from core.institutional import InstitutionalDetector
from core.database import DatabaseManager
import concurrent.futures
import time

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
                if len(batch_symbols) > 1:
                    df = batch_data[symbol]
                else:
                    df = batch_data
                
                if df.empty or 'Close' not in df.columns or df['Close'].isnull().all():
                    continue

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
                # NEW SCORING LOGIC: "EARLY ACCUMULATION ONLY"
                # Goal: Detect BAX Image 2 (BEFORE explosion), reject AMGN Image 1 (AFTER explosion)
                # ========================================
                
                # STRICT FILTER: Reject if already in breakout
                # If price moved >3% above SMA10 in last 1 day, it's too late
                sma_10 = tech_res.get("sma_10", 0)
                if sma_10 > 0 and tech_res["last_close"] > (sma_10 * 1.03):
                    continue  # Skip - already breaking out
                
                # STRICT FILTER: Reject if already had breakout signal
                if tech_res.get("breakout"):
                    continue  # Skip - already exploded
                
                score = 0
                
                # === CORE SIGNAL: Early Accumulation (Image 2 Setup) ===
                if tech_res.get("early_accumulation"):
                    score += 60  # MASSIVE bonus - this is THE signal we want
                else:
                    # If no early accumulation, only proceed if other strong signals exist
                    # This ensures we don't get garbage results
                    if not (tech_res.get("vsa_absorption") or (tech_res.get("squeeze") and inst_res["detected"])):
                        continue  # Skip - no high-conviction setup
                
                # === Supporting Signals ===
                
                # A. Institutional Activity
                if inst_res["detected"]: 
                    score += 25
                if inst_res["institutional_score"] >= 6: 
                    score += 10  # LuxAlgo high conviction
                
                # B. Technical Setups (Lower priority than early accumulation)
                if tech_res.get("vsa_absorption"):
                    score += 20  # VSA is still valuable
                if tech_res.get("squeeze"):
                    score += 10  # Consolidation is good
                if tech_res.get("vcp"):
                    score += 5
                
                # C. Volume (But not explosive)
                if 1.2 <= tech_res["rvol"] <= 2.5:
                    score += 15  # Progressive accumulation range
                elif tech_res["rvol"] > 2.5:
                    score -= 10  # Penalize explosive volume (too late)
                
                # D. Trend (Slightly positive, but not required)
                if tech_res["trend"] == "Uptrend":
                    score += 5
                
                # E. Fundamentals
                if fund_res["passed"]: 
                    score += 10

                if score > 0:
                    result = {
                        "symbol": symbol,
                        "passed_financials": fund_res["passed"],
                        "score": min(score, 100), # Cap at 100
                        "details": {
                            "fundamentals": fund_res,
                            "technicals": tech_res,
                            "institutional": inst_res
                        }
                    }
                    self.db.save_result(result)
            except Exception as e:
                pass # Silencioso para no ensuciar logs masivos

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
            self.process_batch(chunk)
            time.sleep(1) # Pequeño respiro para evitar bloqueos
            
        print(f"[SCANNER] Escaneo completo.")

    def get_results_from_db(self, min_score: int = 0, limit: int = 10) -> list:
        """
        Reads results directly from the database.
        """
        return self.db.get_top_stocks(min_score=min_score, limit=limit)
