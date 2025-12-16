import asyncio
import json
import os
from collections import defaultdict
from typing import Dict, Any, List

try:
    import orjson
except Exception:
    # Fallback ligero cuando orjson no está instalado: usamos json y devolvemos bytes
    import json as _json

    class _OrjsonFallback:
        @staticmethod
        def dumps(obj):
            # orjson.dumps devuelve bytes; mantener ese contrato
            return _json.dumps(obj, default=str).encode("utf-8")

    orjson = _OrjsonFallback()
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer

# Importar servicios y rutas de métricas (intentar, si falla continuar sin ellas)
try:
    from services.metrics_consumer import start_consumer, stop_consumer
    from routes.metrics import router as metrics_router
    METRICS_AVAILABLE = True
    print("✅ Metrics modules imported successfully")
except ImportError as e:
    print(f"⚠️  Warning: Metrics module not available: {e}")
    METRICS_AVAILABLE = False
    start_consumer = None
    stop_consumer = None
    metrics_router = None

# Importar servicio y rutas de recomendaciones (intentar, si falla continuar sin ellas)
try:
    from services.recommender_service import initialize_service, shutdown_service
    from routes.recommendations import router as recommendations_router
    RECOMMENDATIONS_AVAILABLE = True
    print("✅ Recommendations modules imported successfully")
except ImportError as e:
    print(f"⚠️  Warning: Recommendations module not available: {e}")
    print(f"   Error details: {e}")
    RECOMMENDATIONS_AVAILABLE = False
    initialize_service = None
    shutdown_service = None
    recommendations_router = None


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
METRICS_TOPIC = os.getenv("METRICS_TOPIC", "metrics")

app = FastAPI(
    title="MovieLens Recommendation System API",
    description="API para recomendaciones de películas y métricas de streaming en tiempo real",
    version="3.0.0"
)

# Configurar CORS para permitir acceso desde dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de métricas si están disponibles
if METRICS_AVAILABLE and metrics_router:
    app.include_router(metrics_router)
    print("✅ Metrics router registered")
else:
    print("⚠️  Metrics router not available, using legacy endpoints only")

# Incluir rutas de recomendaciones si están disponibles
if RECOMMENDATIONS_AVAILABLE and recommendations_router:
    app.include_router(recommendations_router)
    print("✅ Recommendations router registered")
else:
    print("⚠️  Recommendations router not available, running without recommendation endpoints")

# Incluir ruta de ingest (ratings) si está disponible
try:
    from routes.ingest import router as ingest_router
    from services.ratings_producer import (
        start_producer,
        stop_producer,
        start_background_publisher,
        stop_background_publisher,
    )
    INGEST_AVAILABLE = True
    print("✅ Ratings ingest module imported")
except ImportError as e:
    INGEST_AVAILABLE = False
    start_producer = None
    stop_producer = None
    start_background_publisher = None
    stop_background_publisher = None
    ingest_router = None
    print(f"⚠️  Ratings ingest not available: {e}")

if INGEST_AVAILABLE and ingest_router:
    app.include_router(ingest_router)
    print("✅ Ratings ingest router registered")


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        data = orjson.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_bytes(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


# Estado en memoria con la última métrica por tipo
last_metrics: Dict[str, Dict[str, Any]] = {}


@app.get("/")
async def index():
    # Servimos el HTML del dashboard
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/metrics/last")
async def get_last_metrics():
    return last_metrics


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # No esperamos mensajes del cliente, solo mantenemos la conexión
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def consume_metrics():
    consumer = AIOKafkaConsumer(
        METRICS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda v: v.decode("utf-8") if v else None,
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            metric_name = msg.key or "unknown"
            payload = msg.value
            # Normalizamos estructura para el frontend: {metric, ...payload}
            event = {"metric": metric_name, **payload}
            last_metrics[metric_name] = event
            await manager.broadcast(event)
    finally:
        await consumer.stop()


@app.on_event("startup")
async def startup_event():
    print("\n" + "="*80)
    print("INICIANDO API - SISTEMA DE RECOMENDACIÓN")
    print("="*80)
    
    # Montamos estáticos
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Inicializar servicio de recomendaciones si está disponible
    if RECOMMENDATIONS_AVAILABLE and initialize_service:
        try:
            print("\n🎯 Inicializando servicio de recomendaciones...")
            initialize_service()
            print("✅ Servicio de recomendaciones listo")
        except Exception as e:
            print(f"❌ Error al inicializar servicio de recomendaciones: {e}")
            print("La API funcionará sin endpoints de recomendaciones")
    
    # Iniciar consumer de métricas del nuevo sistema si está disponible
    if METRICS_AVAILABLE and start_consumer:
        await start_consumer()
        print("✅ Metrics consumer started")
    else:
        print("⚠️  Metrics consumer not available, using legacy consumer only")
    
    # Iniciar producer de ratings si está disponible
    if INGEST_AVAILABLE and start_producer:
        try:
            await start_producer(bootstrap_servers=KAFKA_BOOTSTRAP)
            print("✅ Ratings producer started")
        except Exception as e:
            print(f"❌ Error iniciando ratings producer: {e}")

    # Iniciar publicador en background (cola) si está disponible
    if INGEST_AVAILABLE and start_background_publisher:
        try:
            await start_background_publisher()
            print("✅ Ratings background publisher started")
        except Exception as e:
            print(f"❌ Error iniciando background publisher de ratings: {e}")
    
    # Mantener consumidor legacy en background para compatibilidad
    asyncio.create_task(consume_metrics())
    
    print("\n" + "="*80)
    print("✅ API LISTA")
    print("="*80)
    print("Endpoints disponibles:")
    if RECOMMENDATIONS_AVAILABLE:
        print("  - GET  /recommendations/recommend/{user_id}")
        print("  - POST /recommendations/predict")
        print("  - GET  /recommendations/similar/{movie_id}")
        print("  - GET  /recommendations/health")
    if METRICS_AVAILABLE:
        print("  - GET  /metrics/summary")
        print("  - GET  /metrics/topn")
        print("  - GET  /metrics/genres")
    print("  - GET  /docs (OpenAPI documentation)")
    print("="*80 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    print("\n" + "="*80)
    print("DETENIENDO API")
    print("="*80)
    
    # Detener servicio de recomendaciones
    if RECOMMENDATIONS_AVAILABLE and shutdown_service:
        print("Deteniendo servicio de recomendaciones...")
        shutdown_service()
        print("✅ Servicio de recomendaciones detenido")
    
    # Detener consumer de métricas si está disponible
    if METRICS_AVAILABLE and stop_consumer:
        await stop_consumer()
        print("✅ Metrics consumer detenido")
    
    # Detener producer de ratings si está disponible
    if INGEST_AVAILABLE and stop_producer:
        await stop_producer()
        print("✅ Ratings producer detenido")

    # Detener publicador en background de ratings si está disponible
    if INGEST_AVAILABLE and stop_background_publisher:
        await stop_background_publisher()
        print("✅ Ratings background publisher detenido")
    
    print("="*80 + "\n")
