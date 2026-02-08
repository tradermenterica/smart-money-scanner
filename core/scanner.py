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
from config import DIP_THRESHOLDS

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
                
                # 2. Institutional Analysis
                inst = InstitutionalDetector(df)
                inst.analyze_flows()
                inst_res = inst.detect_smart_money()

                # Evaluate ALL setups (Dips, Accumulation, etc.)
                evaluations = self.evaluate_setup(symbol, df, fund_res, inst_res)
                
                for eval_res in evaluations:
                    self.db.save_result(eval_res)
            except Exception as e:
                pass  # Silencioso para no ensuciar logs masivos

    def evaluate_setup(self, symbol: str, df: pd.DataFrame, fund_res: dict = None, inst_res: dict = None) -> list:
        """
        Runs all available setup evaluators and returns a list of matching results.
        """
        results = []
        
        # Scenario A: Smart Money Dip Buy (EXC Style)
        dip_res = self.evaluate_dip_buy(symbol, df, fund_res, inst_res)
        if dip_res: results.append(dip_res)
        
        # Scenario B: Early Accumulation (BAX Style)
        acc_res = self.evaluate_early_accumulation(symbol, df, fund_res, inst_res)
        if acc_res: results.append(acc_res)
        
        # Scenario C: High Volume Breakout
        breakout_res = self.evaluate_breakout(symbol, df, fund_res, inst_res)
        if breakout_res: results.append(breakout_res)
        
        return results

    def evaluate_dip_buy(self, symbol: str, df: pd.DataFrame, fund_res: dict = None, inst_res: dict = None) -> dict:
        """Scenario A: Detects Smart Money Dips (EXC Style)"""
        try:
            if df.empty or len(df) < 50: return None

            # Pullback logic
            lookback = DIP_THRESHOLDS.get("LOOKBACK_DAYS", 60)
            min_dd = DIP_THRESHOLDS.get("MIN_DRAWDOWN", -45)
            max_dd = DIP_THRESHOLDS.get("MAX_DRAWDOWN", -10)
            
            high_60d = float(df['High'].tail(lookback).max())
            current_price = float(df['Close'].iloc[-1])
            drawdown_pct = ((current_price - high_60d) / high_60d) * 100
            
            if not (min_dd < drawdown_pct < max_dd):
                return None
            
            # Money Flow during pullback
            from core.money_flow import MoneyFlowDetector
            mf_detector = MoneyFlowDetector(df)
            pullback_acc = mf_detector.detect_pullback_accumulation(lookback=10)
            if not pullback_acc['has_pullback_accumulation']:
                return None
            
            # Support zone (40% bottom)
            low_60d = float(df['Low'].tail(lookback).min())
            range_60d = high_60d - low_60d
            position_60d = (current_price - low_60d) / range_60d if range_60d > 0 else 0.5
            if position_60d > 0.40:
                return None

            # Score & Result
            score = 70
            if pullback_acc['signal_count'] >= 3: score += 15
            if inst_res and inst_res["detected"]: score += 10
            if fund_res and fund_res["passed"]: score += 5

            # Base technicals
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            tech_res = tech.check_setup()
            tech_res.update({
                'pullback_pct': round(drawdown_pct, 2),
                'range_position_60d': round(position_60d, 2),
                'setup_type': 'Smart Money Dip Buy'
            })

            return {
                "symbol": symbol,
                "passed_financials": fund_res["passed"] if fund_res else False,
                "score": min(score, 100),
                "details": {
                    "setup_type": "Smart Money Dip Buy",
                    "description": "Caída técnica con acumulación institucional en zona de soporte.",
                    "fundamentals": fund_res,
                    "technicals": tech_res,
                    "institutional": inst_res
                }
            }
        except: return None

    def evaluate_early_accumulation(self, symbol: str, df: pd.DataFrame, fund_res: dict = None, inst_res: dict = None) -> dict:
        """Scenario B: Detects Silent/Early Accumulation (BAX Style)"""
        try:
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            if not tech.detect_early_accumulation():
                return None
            
            score = 75
            if inst_res and inst_res["detected"]: score += 15
            if fund_res and fund_res["passed"]: score += 10
            
            tech_res = tech.check_setup()
            tech_res['setup_type'] = 'Early Accumulation'

            return {
                "symbol": symbol,
                "passed_financials": fund_res["passed"] if fund_res else False,
                "score": min(score, 100),
                "details": {
                    "setup_type": "Early Accumulation",
                    "description": "Acumulación silenciosa: volumen progresivo con precio lateral cerca de soporte.",
                    "fundamentals": fund_res,
                    "technicals": tech_res,
                    "institutional": inst_res
                }
            }
        except: return None

    def evaluate_breakout(self, symbol: str, df: pd.DataFrame, fund_res: dict = None, inst_res: dict = None) -> dict:
        """Scenario C: Detects High Volume Breakouts"""
        try:
            tech = TechnicalAnalyzer(df)
            tech.calculate_indicators()
            tech_res = tech.check_setup()
            
            if not tech_res.get('breakout') or tech_res.get('rvol', 0) < 1.8:
                return None
            
            score = 80
            if tech_res.get('rvol') > 2.5: score += 10
            if inst_res and inst_res["detected"]: score += 10
            
            return {
                "symbol": symbol,
                "passed_financials": fund_res["passed"] if fund_res else False,
                "score": min(score, 100),
                "details": {
                    "setup_type": "High Volume Breakout",
                    "description": "Rompimiento de resistencia con volumen institucional explosivo.",
                    "fundamentals": fund_res,
                    "technicals": tech_res,
                    "institutional": inst_res
                }
            }
        except: return None

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
