from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.scanner import Scanner
from core.tickers import TickerSource
from config import WATCHLIST
from pydantic import BaseModel
import asyncio
import time
import os

app = FastAPI(title="Smart Money Scanner API", version="2.7")

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
    print("SMART MONEY API v2.7 (Smart Batch Engine)")
    print("Servidor operativo e instantáneo.")
    print("="*40)
    # NO bloqueamos el inicio. El trabajador se lanzará después de que el servidor esté arriba.
    asyncio.create_task(deferred_worker_start())

async def deferred_worker_start():
    # Esperamos 5 segundos para asegurar que el servidor responde peticiones
    await asyncio.sleep(5)
    await run_background_worker()

async def run_background_worker():
    global worker_status
    if worker_status["is_running"]:
        return
    
    worker_status["is_running"] = True
    try:
        # PROTECCIÓN NUBE: Si ya hay datos, no borramos al arrancar (para evitar el 502 por carga pesada)
        # Solo borramos si el usuario lo pide explícitamente vía API o si está en desarrollo local.
        is_prod = os.getenv("RENDER") is not None
        count = scanner.db.count_stocks()
        
        if is_prod and count > 0:
            print(f"[SISTEMA] Modo Producción: Saltando limpieza inicial. {count} activos cargados.")
        else:
            print("\n[SISTEMA] Iniciando limpieza y actualización total...")
            scanner.db.clear_all()
        
        # Descarga rápida de la lista de tickers
        tickers = TickerSource.get_all_tickers()
        worker_status["tickers_found"] = len(tickers)
        
        full_list = list(set(tickers + WATCHLIST))
        print(f"[SISTEMA] Escaneando {len(full_list)} activos en segundo plano (No bloqueante)...")
        
        # IMPORTANTE: Ejecutamos en un hilo separado para que FastAPI pueda responder (Evita el 502)
        await asyncio.to_thread(scanner.run_full_scan_to_db, full_list)
        
        worker_status["last_run"] = time.ctime()
        print(f"[SISTEMA] Tarea de fondo completada.")
    except Exception as e:
        print(f"[SISTEMA] Error en proceso de fondo: {e}")
    finally:
        worker_status["is_running"] = False

@app.get("/api/status")
def get_status():
    count = scanner.db.count_stocks()
    return {
        "metodo": "GET",
        "version": "2.5 (Massive Engine)", 
        "estado_base_datos": f"{count} activos indexados",
        "trabajador": worker_status,
        "puntos_de_entrada": ["/api/scan", "/api/analyze/{symbol}", "/api/update-db"]
    }

@app.get("/api/scan")
def get_top_stocks(limit: int = 10, min_score: int = 0):
    results = scanner.get_results_from_db(min_score=min_score, limit=limit)
    return {"conteo": len(results), "resultados": results}

@app.post("/api/update-db")
def force_update(background_tasks: BackgroundTasks):
    if worker_status["is_running"]:
        return {"mensaje": "Ya hay un escaneo en progreso."}
    background_tasks.add_task(run_background_worker)
    return {"mensaje": "Actualización en segundo plano iniciada."}

@app.get("/api/analyze/{symbol}")
def analyze_one(symbol: str):
    result = scanner.scan_ticker(symbol.upper())
    return result

if __name__ == "__main__":
    import uvicorn
    # Swagger docs available at /docs
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
