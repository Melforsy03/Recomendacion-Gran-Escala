"""
API Routes - Recomendaciones
=============================

Endpoints REST para servir recomendaciones de películas.

Endpoints:
- GET /recommend/{user_id} - Top-N recomendaciones para usuario
- POST /predict - Predicción de rating para par usuario-película
- GET /similar/{movie_id} - Películas similares
- GET /health - Health check del servicio

Autor: Sistema de Recomendación a Gran Escala
Fecha: 8 de diciembre de 2025
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.recommender_service import get_recommender_service

# ==========================================
# Configuración
# ==========================================

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ==========================================
# Modelos de Request/Response
# ==========================================

class RecommendationItem(BaseModel):
    """Modelo de una recomendación individual"""
    movie_id: int = Field(..., description="ID de la película")
    title: Optional[str] = Field(None, description="Título de la película")
    genres: Optional[List[str]] = Field(None, description="Géneros de la película")
    predicted_rating: Optional[float] = Field(None, description="Rating predicho (1.0-5.0)")
    score: Optional[float] = Field(None, description="Score del modelo híbrido (0.0-1.0)")
    rank: int = Field(..., description="Posición en el ranking (1 = mejor)")


class RecommendationsResponse(BaseModel):
    """Respuesta de recomendaciones"""
    user_id: int = Field(..., description="ID del usuario")
    recommendations: List[RecommendationItem] = Field(..., description="Lista de recomendaciones")
    timestamp: str = Field(..., description="Timestamp de generación (ISO 8601)")
    model_version: str = Field(..., description="Versión del modelo usado")
    strategy: Optional[str] = Field(None, description="Estrategia híbrida usada")
    source: str = Field(..., description="Fuente: 'model', 'cache', 'fallback_popular'")


class PredictRequest(BaseModel):
    """Request para predicción de rating"""
    user_id: int = Field(..., description="ID del usuario", ge=1)
    movie_id: int = Field(..., description="ID de la película", ge=1)


class PredictResponse(BaseModel):
    """Respuesta de predicción de rating"""
    user_id: int
    movie_id: int
    title: Optional[str] = None
    genres: Optional[List[str]] = None
    predicted_rating: Optional[float] = Field(None, description="Rating predicho (1.0-5.0)")
    timestamp: str
    model_version: str


class SimilarMovie(BaseModel):
    """Modelo de película similar"""
    movie_id: int
    title: Optional[str] = None
    genres: Optional[List[str]] = None
    similarity: float = Field(..., description="Score de similitud (0.0-1.0)")
    rank: int


class SimilarMoviesResponse(BaseModel):
    """Respuesta de películas similares"""
    movie_id: int
    similar_movies: List[SimilarMovie]
    timestamp: str
    model_version: str


class HealthResponse(BaseModel):
    """Respuesta de health check"""
    status: str
    model_loaded: bool
    model_version: str
    strategy: Optional[str] = None
    models: Optional[dict] = None
    cache_stats: dict
    timestamp: str


# ==========================================
# Endpoints
# ==========================================

@router.get(
    "/recommend/{user_id}",
    response_model=RecommendationsResponse,
    summary="Obtener recomendaciones para usuario",
    description="""
    Genera top-N recomendaciones personalizadas para un usuario.
    
    **Características:**
    - Usa modelo ALS entrenado
    - Cache con TTL de 1 hora
    - Fallback a películas populares si usuario sin historial
    - Respuestas enriquecidas con metadata (título, géneros)
    
    **Parámetros:**
    - `user_id`: ID del usuario (debe existir en datos de entrenamiento)
    - `n`: Número de recomendaciones (default: 10, max: 100)
    - `use_cache`: Usar cache si está disponible (default: true)
    
    **Ejemplo:**
    ```
    GET /recommendations/recommend/123?n=10
    ```
    """
)
async def get_recommendations(
    user_id: int,
    n: int = Query(default=10, ge=1, le=100, description="Número de recomendaciones"),
    use_cache: bool = Query(default=True, description="Usar cache"),
    strategy: str = Query(default=None, description="Estrategia híbrida: als_heavy, balanced, content_heavy, cold_start")
):
    """Obtiene recomendaciones para un usuario"""
    try:
        logger.info(f"GET /recommend/{user_id}?n={n}&use_cache={use_cache}&strategy={strategy}")
        
        service = get_recommender_service()
        result = await service.get_recommendations(user_id, n, use_cache, strategy)
        
        return result
        
    except RuntimeError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Servicio de recomendaciones no disponible. Modelo no cargado."
        )
    except Exception as e:
        logger.error(f"Error al generar recomendaciones: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predecir rating para par usuario-película",
    description="""
    Predice qué rating daría un usuario a una película específica.
    
    **Características:**
    - Predicción usando modelo ALS
    - Útil para ranking de candidatos
    - Respuesta enriquecida con metadata
    
    **Request body:**
    ```json
    {
      "user_id": 123,
      "movie_id": 456
    }
    ```
    
    **Response:**
    ```json
    {
      "user_id": 123,
      "movie_id": 456,
      "title": "The Matrix",
      "genres": ["Action", "Sci-Fi"],
      "predicted_rating": 4.75,
      "timestamp": "2025-12-08T10:30:00Z",
      "model_version": "v1_20251208"
    }
    ```
    """
)
async def predict_rating(request: PredictRequest):
    """Predice rating para par usuario-película"""
    try:
        logger.info(f"POST /predict user_id={request.user_id} movie_id={request.movie_id}")
        
        service = get_recommender_service()
        result = await service.predict_rating(request.user_id, request.movie_id)
        
        return result
        
    except RuntimeError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Servicio de recomendaciones no disponible"
        )
    except Exception as e:
        logger.error(f"Error al predecir rating: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/similar/{movie_id}",
    response_model=SimilarMoviesResponse,
    summary="Obtener películas similares",
    description="""
    Encuentra películas similares basándose en factores latentes del modelo ALS.
    
    **Características:**
    - Similitud coseno en espacio latente
    - Útil para "más como esta"
    - Respuestas ordenadas por similitud
    
    **Parámetros:**
    - `movie_id`: ID de la película objetivo
    - `n`: Número de similares (default: 10, max: 50)
    
    **Ejemplo:**
    ```
    GET /recommendations/similar/1?n=10
    ```
    """
)
async def get_similar_movies(
    movie_id: int,
    n: int = Query(default=10, ge=1, le=50, description="Número de películas similares")
):
    """Obtiene películas similares"""
    try:
        logger.info(f"GET /similar/{movie_id}?n={n}")
        
        service = get_recommender_service()
        result = await service.get_similar_movies(movie_id, n)
        
        return result
        
    except RuntimeError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Servicio de recomendaciones no disponible"
        )
    except Exception as e:
        logger.error(f"Error al obtener películas similares: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check del servicio de recomendaciones",
    description="""
    Verifica el estado del servicio de recomendaciones.
    
    **Response:**
    ```json
    {
      "status": "healthy",
      "model_loaded": true,
      "model_version": "v1_20251208",
      "cache_stats": {
        "size": 42,
        "max_size": 1000,
        "ttl_hours": 1
      },
      "timestamp": "2025-12-08T10:30:00Z"
    }
    ```
    """
)
async def health_check():
    """Health check del servicio"""
    try:
        service = get_recommender_service()
        health = service.get_health()
        
        return health
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible"
        )


# ==========================================
# Endpoint raíz (documentación)
# ==========================================

@router.get(
    "/",
    summary="Información del servicio de recomendaciones",
    description="Información básica sobre los endpoints disponibles"
)
async def recommendations_info():
    """Información del servicio de recomendaciones"""
    return {
        "service": "Recommendations API",
        "version": "1.0.0",
        "endpoints": {
            "GET /recommend/{user_id}": "Top-N recomendaciones para usuario",
            "POST /predict": "Predecir rating para par usuario-película",
            "GET /similar/{movie_id}": "Películas similares",
            "GET /health": "Health check del servicio"
        },
        "documentation": "/docs",
        "timestamp": datetime.now().isoformat()
    }
