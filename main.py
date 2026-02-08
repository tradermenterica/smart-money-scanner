from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.scanner import Scanner
from core.tickers import TickerSource
from core.dip_detector import DipDetector
from core.data import DataFetcher
from config import WATCHLIST, DARWINEX_ONLY, DIP_DETECTION_ENABLED
from pydantic import BaseModel
import asyncio
import time
import os
import pandas as pd

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # This loads all API keys automatically

app = FastAPI(title="Smart Money Scanner API", version="3.2.1", debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler for debugging 500 errors
from fastapi.responses import JSONResponse
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    error_detail = traceback.format_exc()
    print(f"CRITICAL ERROR: {error_detail}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "traceback": error_detail}
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
    print("SMART MONEY API v3.2.1 (LuxAlgo Engine)")
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
        # Siempre limpiar al iniciar para asegurar frescura total
        print("\n[SISTEMA] Iniciando limpieza y actualización total para nuevos filtros...")
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
        # Pass a callback or just update status periodically?
        # Let's do a simpler approach: update progress as chunks are processed
        chunk_size = 100
        for i in range(0, len(full_list), chunk_size):
            chunk = full_list[i : i + chunk_size]
            worker_status["progress"] = int((i / len(full_list)) * 100)
            await asyncio.to_thread(scanner.process_batch, chunk)
            await asyncio.sleep(1)
        
        worker_status["progress"] = 100
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
        "version": "3.2.1 (LuxAlgo Optimized)", 
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
def get_dip_opportunities(limit: int = 10):
    """
    Scans for institutional dip buying opportunities.
    Returns stocks with significant price drops showing institutional accumulation.
    """
    if not DIP_DETECTION_ENABLED:
        return {"error": "Dip detection is disabled. Enable in config.py"}
    
    # Get ONLY candidates with "Smart Money Dip Buy" tag from DB
    db_results = scanner.db.get_top_stocks(min_score=0, limit=limit, setup_type="Smart Money Dip Buy")
    
    return {"conteo": len(db_results), "resultados": db_results}

@app.get("/api/scan-accumulation")
def get_accumulation_opportunities(limit: int = 10):
    """Scenario B: Early Accumulation (Silent flows)"""
    results = scanner.db.get_top_stocks(min_score=0, limit=limit, setup_type="Early Accumulation")
    return {"conteo": len(results), "resultados": results}

@app.get("/api/scan-breakouts")
def get_breakout_opportunities(limit: int = 10):
    """Scenario C: High Volume Breakouts"""
    results = scanner.db.get_top_stocks(min_score=0, limit=limit, setup_type="High Volume Breakout")
    return {"conteo": len(results), "resultados": results}

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
