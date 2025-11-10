"""
Metrics API Routes
==================

Endpoints REST y SSE para servir métricas de streaming en tiempo real.

Endpoints:
- GET /metrics/summary - Resumen actual de métricas
- GET /metrics/topn - Top-N películas más populares
- GET /metrics/genres - Métricas agregadas por género
- GET /metrics/history - Historial de métricas
- GET /metrics/stream - Server-Sent Events para actualizaciones en tiempo real

Fase 9: Sistema de Recomendación de Películas a Gran Escala
Fecha: 3 de noviembre de 2025
"""

import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.metrics_consumer import (
    get_latest_summary,
    get_latest_topn,
    get_latest_genres,
    get_metrics_history,
    get_last_update,
    subscribe_to_metrics,
    unsubscribe_from_metrics
)

# ==========================================
# Configuración
# ==========================================

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["metrics"])

# ==========================================
# Modelos de Respuesta
# ==========================================

class MetricsSummary(BaseModel):
    """Modelo de resumen de métricas"""
    window_start: Optional[str]
    window_end: Optional[str]
    window_type: Optional[str]
    total_ratings: int
    avg_rating: float
    p50_rating: float
    p95_rating: float
    timestamp: str
    last_update: Optional[str]

class TopNMovie(BaseModel):
    """Modelo de película en top-N"""
    movieId: int
    title: Optional[str] = None
    rating_count: Optional[int] = None
    avg_rating: Optional[float] = None
    score: Optional[float] = None

class TopNResponse(BaseModel):
    """Modelo de respuesta top-N"""
    window_start: Optional[str]
    window_end: Optional[str]
    movies: list  # Puede ser list[int] o list[dict]
    timestamp: str
    count: int

class GenreMetrics(BaseModel):
    """Modelo de métricas por género"""
    window_start: Optional[str]
    window_end: Optional[str]
    genres: dict
    timestamp: str

class HealthResponse(BaseModel):
    """Modelo de respuesta de salud"""
    status: str
    last_update: Optional[str]
    metrics_available: bool

# ==========================================
# Endpoints REST
# ==========================================

@router.get("/health", response_model=HealthResponse)
async def get_metrics_health():
    """
    Verifica el estado del sistema de métricas
    
    Returns:
        Estado del consumer y última actualización
    """
    last_update = get_last_update()
    
    return HealthResponse(
        status="healthy" if last_update else "no_data",
        last_update=last_update.isoformat() if last_update else None,
        metrics_available=last_update is not None
    )

@router.get("/summary", response_model=MetricsSummary)
async def get_summary():
    """
    Obtiene resumen actual de métricas de streaming
    
    Returns:
        Resumen con métricas agregadas de la ventana más reciente
    
    Raises:
        HTTPException: Si no hay datos disponibles
    """
    summary = get_latest_summary()
    
    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No hay métricas disponibles. El procesador de streaming podría no estar activo."
        )
    
    last_update = get_last_update()
    
    return MetricsSummary(
        window_start=summary.get("window_start"),
        window_end=summary.get("window_end"),
        window_type=summary.get("window_type"),
        total_ratings=summary.get("total_ratings", 0),
        avg_rating=summary.get("avg_rating", 0.0),
        p50_rating=summary.get("p50_rating", 0.0),
        p95_rating=summary.get("p95_rating", 0.0),
        timestamp=summary.get("timestamp", ""),
        last_update=last_update.isoformat() if last_update else None
    )

@router.get("/topn", response_model=TopNResponse)
async def get_topn(limit: int = Query(default=10, ge=1, le=50)):
    """
    Obtiene top-N películas más populares
    
    Args:
        limit: Número de películas a retornar (1-50)
    
    Returns:
        Lista de películas ordenadas por popularidad
    
    Raises:
        HTTPException: Si no hay datos disponibles
    """
    topn = get_latest_topn()
    
    if not topn:
        raise HTTPException(
            status_code=404,
            detail="No hay datos de top-N disponibles"
        )
    
    movies = topn.get("movies", [])[:limit]
    
    return TopNResponse(
        window_start=topn.get("window_start"),
        window_end=topn.get("window_end"),
        movies=movies,
        timestamp=topn.get("timestamp", ""),
        count=len(movies)
    )

@router.get("/genres", response_model=GenreMetrics)
async def get_genres():
    """
    Obtiene métricas agregadas por género
    
    Returns:
        Estadísticas de ratings por género
    
    Raises:
        HTTPException: Si no hay datos disponibles
    """
    genres = get_latest_genres()
    
    if not genres:
        raise HTTPException(
            status_code=404,
            detail="No hay métricas por género disponibles"
        )
    
    return GenreMetrics(
        window_start=genres.get("window_start"),
        window_end=genres.get("window_end"),
        genres=genres.get("genres", {}),
        timestamp=genres.get("timestamp", "")
    )

@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=100)):
    """
    Obtiene historial de métricas
    
    Args:
        limit: Número de registros históricos (1-100)
    
    Returns:
        Lista de métricas históricas ordenadas por tiempo
    """
    history = get_metrics_history(limit)
    
    return {
        "count": len(history),
        "history": history
    }

# ==========================================
# Server-Sent Events (SSE)
# ==========================================

@router.get("/stream")
async def stream_metrics():
    """
    Stream de métricas en tiempo real usando Server-Sent Events (SSE)
    
    El cliente debe mantener la conexión abierta para recibir actualizaciones.
    Formato SSE estándar con eventos `data:` seguidos de JSON.
    
    Ejemplo de uso (JavaScript):
    ```javascript
    const eventSource = new EventSource('/metrics/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Nueva métrica:', data);
    };
    ```
    
    Returns:
        StreamingResponse con eventos SSE
    """
    
    async def event_generator():
        """Generador de eventos SSE"""
        
        # Crear cola de suscripción
        queue = await subscribe_to_metrics()
        
        try:
            # Enviar métricas actuales inmediatamente
            summary = get_latest_summary()
            if summary:
                yield f"data: {json.dumps({'type': 'summary', 'data': summary})}\n\n"
            
            topn = get_latest_topn()
            if topn:
                yield f"data: {json.dumps({'type': 'topn', 'data': topn})}\n\n"
            
            genres = get_latest_genres()
            if genres:
                yield f"data: {json.dumps({'type': 'genres', 'data': genres})}\n\n"
            
            # Enviar heartbeat inicial
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Loop de eventos
            while True:
                try:
                    # Esperar evento con timeout para heartbeats
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Enviar evento
                    yield f"data: {json.dumps(message)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Enviar heartbeat cada 30 segundos
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                
        except asyncio.CancelledError:
            logger.info("Cliente desconectado del stream de métricas")
        except Exception as e:
            logger.error(f"Error en stream de métricas: {e}")
        finally:
            # Limpiar suscripción
            unsubscribe_from_metrics(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Deshabilitar buffering en nginx
        }
    )
