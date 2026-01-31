from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.scanner import Scanner
from core.tickers import TickerSource
from core.dip_detector import DipDetector
from config import WATCHLIST, DARWINEX_ONLY, DIP_DETECTION_ENABLED
from pydantic import BaseModel
import asyncio
import time
import os

app = FastAPI(title="Smart Money Scanner API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/", include_in_schema=False)
async def serve_spa():
    return FileResponse("public/index.html")

scanner = Scanner()
dip_detector = DipDetector()

# Global state to track worker
worker_status = {
    "is_running": False,
    "last_run": "Nunca",
    "tickers_found": 0,
    "progress": 0
}

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*40)
    print("SMART MONEY API v2.9.2 (LuxAlgo Engine)")
    print("Servidor operativo e instantáneo.")
    print("="*40)
    # NO bloqueamos el inicio. El trabajador se lanzará después de que el servidor esté arriba.
    asyncio.create_task(deferred_worker_start())

async def deferred_worker_start():
    # Esperamos 5 segundos para asegurar que el servidor responde peticiones
    await asyncio.sleep(5)
    await run_background_worker()

async def run_background_worker(force_clean: bool = False):
    global worker_status
    if worker_status["is_running"]:
        return
    
    worker_status["is_running"] = True
    try:
        # Lógica inteligente de limpieza
        if force_clean:
            print("[SISTEMA] Limpieza forzada solicitada por el usuario.")
            scanner.db.clear_all()
        else:
            is_prod = os.getenv("RENDER") is not None
            count = scanner.db.count_stocks()
            if is_prod and count > 0:
                print(f"[SISTEMA] Modo Producción: Manteniendo {count} activos precargados para rapidez.")
            else:
                print("\n[SISTEMA] Iniciando limpieza y actualización total...")
                scanner.db.clear_all()
        
        # Descarga de la lista de tickers
        if DARWINEX_ONLY:
            print("[SISTEMA] Modo DARWINEX_ONLY activo. Saltando búsqueda masiva.")
            tickers = []
        else:
            tickers = TickerSource.get_all_tickers()
            
        darwinex_tickers = TickerSource.get_darwinex_tickers()
        worker_status["tickers_found"] = len(tickers) if not DARWINEX_ONLY else len(darwinex_tickers)
        
        full_list = list(set(tickers + WATCHLIST + darwinex_tickers))
        print(f"[SISTEMA] Escaneando {len(full_list)} activos en segundo plano (Modo: {'Darwinex' if DARWINEX_ONLY else 'Total'})...")
        
        # Ejecución en hilo separado para no bloquear la API
        await asyncio.to_thread(scanner.run_full_scan_to_db, full_list)
        
        worker_status["last_run"] = time.ctime()
        print(f"[SISTEMA] Actualización completa terminada.")
    except Exception as e:
        print(f"[SISTEMA] Error en proceso de fondo: {e}")
    finally:
        worker_status["is_running"] = False

@app.get("/api/status")
def get_status():
    count = scanner.db.count_stocks()
    return {
        "metodo": "GET",
        "version": "2.9.2 (LuxAlgo Optimized)", 
        "estado_base_datos": f"{count} activos indexados",
        "trabajador": worker_status,
        "puntos_de_entrada": ["/api/scan", "/api/analyze/{symbol}", "/api/update-db"]
    }

@app.get("/api/scan")
def get_top_stocks(limit: int = 10, min_score: int = 0):
    results = scanner.get_results_from_db(min_score=min_score, limit=limit)
    return {"conteo": len(results), "resultados": results}

@app.get("/api/scan-darwinex")
def get_darwinex_stocks(limit: int = 10, min_score: int = 0):
    darwinex_list = TickerSource.get_darwinex_tickers()
    results = scanner.db.get_stocks_by_list(darwinex_list, min_score=min_score, limit=limit)
    return {"conteo": len(results), "resultados": results}

@app.post("/api/update-db")
def force_update(background_tasks: BackgroundTasks):
    if worker_status["is_running"]:
        return {"mensaje": "Ya hay un escaneo en progreso."}
    # Forzamos la limpieza cuando se pide manualmente
    background_tasks.add_task(run_background_worker, force_clean=True)
    return {"mensaje": "Actualización MANUAL con limpieza iniciada en segundo plano."}

@app.get("/api/analyze/{symbol}")
def analyze_one(symbol: str):
    result = scanner.scan_ticker(symbol.upper())
    return result

@app.get("/api/scan-dips")
def get_dip_opportunities(limit: int = 10, min_score: int = 70):
    """
    Scans for institutional dip buying opportunities.
    Returns stocks with significant price drops showing institutional accumulation.
    """
    if not DIP_DETECTION_ENABLED:
        return {"error": "Dip detection is disabled. Enable in config.py"}
    
    # Get top candidates from main scanner first (pre-filter)
    candidates = scanner.get_results_from_db(min_score=50, limit=100)
    
    dip_opportunities = []
    for candidate in candidates:
        symbol = candidate['symbol']
        dip_result = dip_detector.analyze_dip_opportunity(symbol)
        
        if dip_result and dip_result['dip_score'] >= min_score:
            dip_opportunities.append(dip_result)
    
    # Sort by dip score
    dip_opportunities.sort(key=lambda x: x['dip_score'], reverse=True)
    
    return {
        "conteo": len(dip_opportunities[:limit]),
        "resultados": dip_opportunities[:limit]
    }

@app.get("/api/institutional/{symbol}")
def get_institutional_analysis(symbol: str):
    """
    Returns detailed institutional analysis for a single stock.
    Includes ownership, insider transactions, analyst recommendations, and dip score.
    """
    if not DIP_DETECTION_ENABLED:
        return {"error": "Dip detection is disabled. Enable in config.py"}
    
    result = dip_detector.analyze_dip_opportunity(symbol.upper())
    if not result:
        return {"error": f"Could not analyze {symbol}"}
    
    return result

if __name__ == "__main__":
    import uvicorn
    # Swagger docs available at /docs
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
