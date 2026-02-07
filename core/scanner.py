from core.data import DataFetcher
from core.financials import FundamentalAnalyzer
from core.technicals import TechnicalAnalyzer
from core.institutional import InstitutionalDetector
from core.database import DatabaseManager
from core.money_flow import MoneyFlowDetector
from core.zones import ZoneDetector
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
                # NEW DETECTION: MONEY FLOW + SUPPLY/DEMAND ZONES
                # Goal: Detect stocks with RECENT money flow (last 5 days) in DEMAND zones
                # Reject: Stocks in supply zones or without recent signals
                # ========================================
                
                # 4. Money Flow Analysis (replaces OBV divergence)
                mf_detector = MoneyFlowDetector(df)
                mf_signals = mf_detector.detect_signals(lookback=5)
                
                # 5. Zone Analysis
                zone_detector = ZoneDetector(df)
                current_zone = zone_detector.get_current_zone_type()
                price_position = zone_detector.get_position_in_range()
                
                # STRICT FILTER 1: Must have recent money flow signals
                if not mf_signals['has_recent_flow']:
                    continue  # Skip - no money flow in last 5 days
                
                # STRICT FILTER 2: Cannot be in supply zone (resistance)
                if current_zone == 'supply':
                    continue  # Skip - in resistance/distribution zone
                
                # STRICT FILTER 3: Cannot be in upper range (too extended)
                if price_position > 0.65:
                    continue  # Skip - too high in range
                
                # STRICT FILTER 4: Reject if already had breakout
                if tech_res.get("breakout"):
                    continue  # Skip - already exploded
                
                # === NEW SCORING SYSTEM ===
                score = 0
                
                # A. Money Flow Signals (CORE - highest priority)
                if mf_signals['signal_count'] >= 3:
                    score += 60  # Multiple strong signals recently
                elif mf_signals['signal_count'] >= 2:
                    score += 45  # Minimum required signals
                
                # B. Zone Position (High priority)
                if current_zone == 'demand':
                    score += 30  # In demand zone (blue/support)
                
                if price_position < 0.4:
                    score += 20  # In lower 40% of range (ideal)
                elif price_position < 0.6:
                    score += 10  # In middle range (acceptable)
                
                # C. Institutional Activity
                if inst_res["detected"]: 
                    score += 20
                if inst_res["institutional_score"] >= 6: 
                    score += 10
                
                # D. Technical Confirmation (Lower weight)
                if tech_res.get("vsa_absorption"):
                    score += 15
                if tech_res.get("squeeze"):
                    score += 10
                if tech_res.get("vcp"):
                    score += 5
                
                # E. Volume (Progressive, not explosive)
                if 1.2 <= tech_res["rvol"] <= 2.5:
                    score += 10
                elif tech_res["rvol"] > 2.5:
                    score -= 15  # Penalize explosive volume
                
                # F. Fundamentals
                if fund_res["passed"]: 
                    score += 10

                if score > 0:
                    # Add money flow and zone info to result
                    tech_res['money_flow_signals'] = mf_signals['signal_count']
                    tech_res['current_zone'] = current_zone
                    tech_res['price_position'] = round(price_position, 2)
                    
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
