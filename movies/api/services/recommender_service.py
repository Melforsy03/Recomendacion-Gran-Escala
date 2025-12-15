"""
Servicio de Recomendaciones
============================

Servicio para cargar modelos entrenados y servir recomendaciones en tiempo real.
Implementa cache LRU para optimizar respuestas.

Características:
- Carga de modelos ALS desde trained_models/
- Cache LRU con TTL
- Enriquecimiento con metadata de películas
- Fallback para usuarios sin historial

Autor: Sistema de Recomendación a Gran Escala
Fecha: 8 de diciembre de 2025
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import asyncio

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Importar modelos
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from movies.src.recommendation.models.hybrid_recommender import HybridRecommender

logger = logging.getLogger(__name__)


# ==========================================
# Configuración
# ==========================================

class RecommenderConfig:
    """Configuración del servicio de recomendaciones"""
    
    # Paths
    TRAINED_MODELS_DIR = Path("/app/trained_models")  # En contenedor Docker
    ALS_MODEL_PATH = TRAINED_MODELS_DIR / "als" / "model_latest" / "spark_model"
    ITEM_CF_MODEL_PATH = TRAINED_MODELS_DIR / "item_cf" / "model_latest" / "similarity_matrix"
    CONTENT_MODEL_PATH = TRAINED_MODELS_DIR / "content_based" / "model_latest" / "movie_features"
    MOVIES_METADATA_CSV = Path("/app/movies_metadata.csv")  # CSV montado desde Dataset/movie.csv
    
    # Configuración de cache
    CACHE_MAX_SIZE = 1000
    CACHE_TTL_HOURS = 1
    
    # Configuración de Spark
    SPARK_MEMORY = "2g"
    SPARK_CORES = 2
    
    # Estrategia híbrida por defecto
    DEFAULT_STRATEGY = "balanced"  # als_heavy, balanced, content_heavy, cold_start
    
    # Fallback
    TOP_POPULAR_N = 100


# ==========================================
# Cache con TTL
# ==========================================

class CacheEntry:
    """Entrada de cache con TTL"""
    
    def __init__(self, data: List[Dict], ttl_hours: int = 1):
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = timedelta(hours=ttl_hours)
    
    def is_expired(self) -> bool:
        """Verifica si la entrada expiró"""
        return datetime.now() - self.timestamp > self.ttl


class RecommendationCache:
    """Cache LRU con TTL para recomendaciones"""
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 1):
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    def _make_key(self, user_id: int, n: int) -> str:
        """Genera key de cache"""
        return f"user_{user_id}_n_{n}"
    
    async def get(self, user_id: int, n: int) -> Optional[List[Dict]]:
        """Obtiene recomendaciones del cache"""
        async with self._lock:
            key = self._make_key(user_id, n)
            
            if key in self.cache:
                entry = self.cache[key]
                
                if not entry.is_expired():
                    logger.debug(f"Cache HIT: user={user_id}, n={n}")
                    return entry.data
                else:
                    # Entrada expirada, eliminar
                    logger.debug(f"Cache EXPIRED: user={user_id}, n={n}")
                    del self.cache[key]
            
            logger.debug(f"Cache MISS: user={user_id}, n={n}")
            return None
    
    async def set(self, user_id: int, n: int, recommendations: List[Dict]):
        """Guarda recomendaciones en cache"""
        async with self._lock:
            key = self._make_key(user_id, n)
            
            # Si cache lleno, eliminar entrada más antigua
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
                del self.cache[oldest_key]
                logger.debug(f"Cache EVICT: {oldest_key}")
            
            self.cache[key] = CacheEntry(recommendations, self.ttl_hours)
            logger.debug(f"Cache SET: user={user_id}, n={n}, size={len(self.cache)}")
    
    async def clear(self):
        """Limpia todo el cache"""
        async with self._lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del cache"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_hours": self.ttl_hours
        }


# ==========================================
# Servicio de Recomendaciones
# ==========================================

class RecommenderService:
    """
    Servicio principal para servir recomendaciones
    """
    
    def __init__(self):
        self.spark: Optional[SparkSession] = None
        self.hybrid_model: Optional[HybridRecommender] = None
        self.movies_metadata = None
        self.ratings_df = None  # Para content-based
        self.top_popular_movies: List[Dict] = []
        self.cache = RecommendationCache(
            max_size=RecommenderConfig.CACHE_MAX_SIZE,
            ttl_hours=RecommenderConfig.CACHE_TTL_HOURS
        )
        self.model_version = "hybrid_v1"
        self.default_strategy = RecommenderConfig.DEFAULT_STRATEGY
        self.loaded = False
    
    def initialize(self):
        """Inicializa el servicio (carga modelos y metadata)"""
        logger.info("="*80)
        logger.info("INICIALIZANDO SERVICIO DE RECOMENDACIONES")
        logger.info("="*80)
        
        try:
            # Crear SparkSession
            self._create_spark_session()
            
            # Cargar modelo híbrido
            self._load_hybrid_model()
            
            # Cargar metadata de películas
            self._load_movies_metadata()
            
            # Cargar ratings para content-based
            self._load_ratings()
            
            # Pre-calcular películas populares (fallback)
            self._compute_top_popular()
            
            self.loaded = True
            logger.info("="*80)
            logger.info("✅ SERVICIO DE RECOMENDACIONES LISTO")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ ERROR al inicializar servicio: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _create_spark_session(self):
        """Crea SparkSession local"""
        logger.info("Creando SparkSession...")
        
        self.spark = SparkSession.builder \
            .appName("RecommenderAPI") \
            .master(f"local[{RecommenderConfig.SPARK_CORES}]") \
            .config("spark.driver.memory", RecommenderConfig.SPARK_MEMORY) \
            .config("spark.sql.shuffle.partitions", "10") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("ERROR")
        
        logger.info(f"✓ Spark {self.spark.version} inicializado")
    
    def _load_hybrid_model(self):
        """Carga modelo híbrido con ALS, Item-CF y Content-Based"""
        logger.info("Cargando sistema de recomendación híbrido...")
        
        # Verificar que al menos ALS existe
        if not RecommenderConfig.ALS_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Modelo ALS no encontrado: {RecommenderConfig.ALS_MODEL_PATH}\n"
                "Ejecuta: ./scripts/train_all_models.sh"
            )
        
        # Crear instancia del híbrido
        self.hybrid_model = HybridRecommender(self.spark)
        
        # Cargar todos los modelos disponibles
        als_path = str(RecommenderConfig.ALS_MODEL_PATH) if RecommenderConfig.ALS_MODEL_PATH.exists() else None
        item_cf_path = str(RecommenderConfig.ITEM_CF_MODEL_PATH) if RecommenderConfig.ITEM_CF_MODEL_PATH.exists() else None
        content_path = str(RecommenderConfig.CONTENT_MODEL_PATH) if RecommenderConfig.CONTENT_MODEL_PATH.exists() else None
        
        self.hybrid_model.load_all_models(
            als_path=als_path,
            item_cf_path=item_cf_path,
            features_path=content_path
        )
        
        # Asignar ratings_df a Item-CF si está disponible (se carga después en _load_ratings)
        # Nota: Este paso se completará después de _load_ratings()
        
        # Leer versión del metadata
        metadata_file = RecommenderConfig.ALS_MODEL_PATH.parent / "metadata.json"
        if metadata_file.exists():
            import json
            with open(metadata_file) as f:
                metadata = json.load(f)
                self.model_version = f"hybrid_{metadata.get('version', 'v1')}"
        
        logger.info(f"✓ Modelo híbrido cargado (versión: {self.model_version})")
    
    def _load_movies_metadata(self):
        """Carga metadata de películas para enriquecer respuestas"""
        logger.info("Cargando metadata de películas...")
        
        # Cargar desde CSV
        if RecommenderConfig.MOVIES_METADATA_CSV.exists():
            self.movies_metadata = self.spark.read.csv(
                str(RecommenderConfig.MOVIES_METADATA_CSV),
                header=True,
                inferSchema=True
            )
            # Renombrar columnas si es necesario (el CSV de MovieLens usa movieId, title, genres)
            if "movieId" in self.movies_metadata.columns:
                self.movies_metadata = self.movies_metadata.withColumnRenamed("movieId", "movie_id")
            
            count = self.movies_metadata.count()
            logger.info(f"✓ Metadata cargada: {count:,} películas")
        else:
            logger.warning(f"⚠️  Metadata de películas no encontrada en {RecommenderConfig.MOVIES_METADATA_CSV}")
            logger.warning("Respuestas sin enriquecer")
            self.movies_metadata = None
    
    def _load_ratings(self):
        """Carga ratings para content-based y filtrado colaborativo"""
        logger.info("Cargando ratings...")
        
        ratings_path = Path("/app/Dataset/rating.csv")
        if ratings_path.exists():
            self.ratings_df = self.spark.read.csv(
                str(ratings_path),
                header=True,
                inferSchema=True
            )
            # Renombrar columnas si es necesario
            if "userId" in self.ratings_df.columns:
                self.ratings_df = self.ratings_df.withColumnRenamed("userId", "user_id")
            if "movieId" in self.ratings_df.columns:
                self.ratings_df = self.ratings_df.withColumnRenamed("movieId", "movie_id")
            
            count = self.ratings_df.count()
            logger.info(f"✓ Ratings cargados: {count:,} valoraciones")
            
            # Asignar ratings_df a Item-CF si el modelo está cargado
            if self.hybrid_model and self.hybrid_model.item_cf is not None:
                self.hybrid_model.item_cf.ratings_df = self.ratings_df
                logger.info("✓ Ratings asignados a Item-CF")
        else:
            logger.warning(f"⚠️  Ratings no encontrados en {ratings_path}")
            self.ratings_df = None
    
    def _compute_top_popular(self):
        """Pre-calcula top películas populares (fallback)"""
        logger.info("Calculando top películas populares...")
        
        try:
            if self.hybrid_model and self.hybrid_model.als and self.hybrid_model.als.model:
                # Obtener factores de items y calcular "popularidad" por norma del vector
                item_factors = self.hybrid_model.als.model.itemFactors
                
                # Calcular norma L2 de cada vector de factores
                from pyspark.ml.linalg import Vectors, VectorUDT
                from pyspark.sql.functions import udf
                from pyspark.sql.types import DoubleType
                import numpy as np
                
                def vector_norm(v):
                    """Calcula norma L2 del vector"""
                    # En PySpark 3.5+, v puede venir como lista o DenseVector
                    if isinstance(v, list):
                        return float(np.linalg.norm(v))
                    else:
                        # Para DenseVector/SparseVector
                        return float(np.linalg.norm(v.toArray()))
                
                norm_udf = udf(vector_norm, DoubleType())
                
                popular_items = item_factors \
                    .withColumn("popularity_score", norm_udf(F.col("features"))) \
                    .orderBy(F.desc("popularity_score")) \
                    .limit(RecommenderConfig.TOP_POPULAR_N) \
                    .select("id") \
                    .collect()
                
                self.top_popular_movies = [
                    {"movie_id": row["id"], "rank": idx + 1}
                    for idx, row in enumerate(popular_items)
                ]
                
                logger.info(f"✓ Top {len(self.top_popular_movies)} películas populares calculadas")
            else:
                logger.warning("⚠️  No se pudo calcular películas populares")
                self.top_popular_movies = []
                
        except Exception as e:
            logger.error(f"Error al calcular populares: {e}")
            self.top_popular_movies = []
    
    async def get_recommendations(
        self,
        user_id: int,
        n: int = 10,
        use_cache: bool = True,
        strategy: str = None
    ) -> Dict:
        """
        Obtiene recomendaciones para un usuario usando modelo híbrido
        
        Args:
            user_id: ID del usuario
            n: Número de recomendaciones
            use_cache: Usar cache si está disponible
            strategy: Estrategia híbrida (als_heavy, balanced, content_heavy, cold_start)
            
        Returns:
            Diccionario con recomendaciones y metadata
        """
        if not self.loaded:
            raise RuntimeError("Servicio no inicializado. Llama a initialize() primero.")
        
        # Usar estrategia por defecto si no se especifica
        if strategy is None:
            strategy = self.default_strategy
        
        # Intentar obtener del cache
        cache_key = f"{user_id}_{strategy}"
        if use_cache:
            cached = await self.cache.get(cache_key, n)
            if cached is not None:
                return {
                    "user_id": user_id,
                    "recommendations": cached,
                    "timestamp": datetime.now().isoformat(),
                    "model_version": self.model_version,
                    "strategy": strategy,
                    "source": "cache"
                }
        
        # Generar recomendaciones con el modelo híbrido
        try:
            # El modelo híbrido maneja internamente los ratings
            recommendations_df = self.hybrid_model.recommend(
                user_id=user_id,
                n=n,
                strategy=strategy,
                ratings_df=self.ratings_df
            )
            
            # Verificar si retorna DataFrame o lista
            if hasattr(recommendations_df, 'collect'):
                # Es un DataFrame de Spark
                recs = recommendations_df.collect()
            elif isinstance(recommendations_df, list):
                # Ya es una lista de diccionarios
                recs = recommendations_df
            else:
                # Usuario sin historial, usar fallback
                logger.info(f"Usuario {user_id} sin historial o modelo híbrido no disponible, usando fallback")
                return await self._get_fallback_recommendations(user_id, n)
            
            # Convertir a lista de diccionarios para la respuesta
            recommendations = []
            
            for idx, item in enumerate(recs):
                # Manejar tanto Row (DataFrame) como dict (lista)
                if hasattr(item, 'asDict'):
                    row = item.asDict()
                else:
                    row = item
                
                rec = {
                    "movie_id": int(row.get("movieId", row.get("movie_id"))),
                    "score": float(row.get("score", 0.0)),
                    "rank": idx + 1
                }
                
                # Enriquecer con metadata si está disponible
                if self.movies_metadata is not None:
                    metadata = self.movies_metadata.filter(
                        F.col("movie_id") == rec["movie_id"]
                    ).first()
                    
                    if metadata:
                        rec["title"] = metadata["title"]
                        rec["genres"] = metadata["genres"].split("|") if metadata["genres"] else []
                
                recommendations.append(rec)
            
            # Guardar en cache
            if use_cache:
                await self.cache.set(cache_key, n, recommendations)
            
            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat(),
                "model_version": self.model_version,
                "strategy": strategy,
                "source": "model"
            }
            
        except Exception as e:
            logger.error(f"Error al generar recomendaciones para user {user_id}: {e}")
            # Fallback en caso de error
            return await self._get_fallback_recommendations(user_id, n)
    
    async def _get_fallback_recommendations(self, user_id: int, n: int) -> Dict:
        """Recomendaciones de fallback (películas populares)"""
        recommendations = self.top_popular_movies[:n]
        
        # Enriquecer con metadata si está disponible
        if self.movies_metadata is not None:
            enriched = []
            for rec in recommendations:
                metadata = self.movies_metadata.filter(
                    F.col("movie_id") == rec["movie_id"]
                ).first()
                
                if metadata:
                    enriched.append({
                        "movie_id": rec["movie_id"],
                        "title": metadata["title"],
                        "genres": metadata["genres"].split("|") if metadata["genres"] else [],
                        "rank": rec["rank"],
                        "predicted_rating": None  # No hay predicción
                    })
                else:
                    enriched.append(rec)
            
            recommendations = enriched
        
        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "model_version": self.model_version,
            "source": "fallback_popular"
        }
    
    async def predict_rating(self, user_id: int, movie_id: int) -> Dict:
        """
        Predice rating para par usuario-película
        
        Args:
            user_id: ID del usuario
            movie_id: ID de la película
            
        Returns:
            Diccionario con predicción
        """
        if not self.loaded:
            raise RuntimeError("Servicio no inicializado")
        
        try:
            prediction = self.als_model.predict_rating(user_id, movie_id)
            
            result = {
                "user_id": user_id,
                "movie_id": movie_id,
                "predicted_rating": float(prediction) if prediction is not None else None,
                "timestamp": datetime.now().isoformat(),
                "model_version": self.model_version
            }
            
            # Enriquecer con metadata de película
            if self.movies_metadata is not None:
                metadata = self.movies_metadata.filter(
                    F.col("movie_id") == movie_id
                ).first()
                
                if metadata:
                    result["title"] = metadata["title"]
                    result["genres"] = metadata["genres"].split("|") if metadata["genres"] else []
            
            return result
            
        except Exception as e:
            logger.error(f"Error al predecir rating: {e}")
            raise
    
    async def get_similar_movies(self, movie_id: int, n: int = 10) -> Dict:
        """
        Obtiene películas similares basándose en factores latentes
        
        Args:
            movie_id: ID de la película
            n: Número de similares
            
        Returns:
            Diccionario con películas similares
        """
        if not self.loaded:
            raise RuntimeError("Servicio no inicializado")
        
        try:
            # Obtener factor de la película objetivo
            item_factors = self.als_model.model.itemFactors
            target_factor = item_factors.filter(F.col("id") == movie_id).first()
            
            if target_factor is None:
                return {
                    "movie_id": movie_id,
                    "similar_movies": [],
                    "message": "Película no encontrada en modelo",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calcular similitud coseno con todas las películas
            # (Simplificado: en producción usar ANN como FAISS)
            from pyspark.ml.linalg import Vectors
            from pyspark.sql.functions import udf
            from pyspark.sql.types import DoubleType
            import numpy as np
            
            target_vec = np.array(target_factor["features"].toArray())
            
            def cosine_similarity(features):
                vec = np.array(features.toArray())
                return float(np.dot(target_vec, vec) / (np.linalg.norm(target_vec) * np.linalg.norm(vec)))
            
            cosine_udf = udf(cosine_similarity, DoubleType())
            
            similar = item_factors \
                .filter(F.col("id") != movie_id) \
                .withColumn("similarity", cosine_udf(F.col("features"))) \
                .orderBy(F.desc("similarity")) \
                .limit(n) \
                .collect()
            
            similar_movies = []
            for idx, row in enumerate(similar):
                movie = {
                    "movie_id": int(row["id"]),
                    "similarity": float(row["similarity"]),
                    "rank": idx + 1
                }
                
                # Enriquecer con metadata
                if self.movies_metadata is not None:
                    metadata = self.movies_metadata.filter(
                        F.col("movie_id") == row["id"]
                    ).first()
                    
                    if metadata:
                        movie["title"] = metadata["title"]
                        movie["genres"] = metadata["genres"].split("|") if metadata["genres"] else []
                
                similar_movies.append(movie)
            
            return {
                "movie_id": movie_id,
                "similar_movies": similar_movies,
                "timestamp": datetime.now().isoformat(),
                "model_version": self.model_version
            }
            
        except Exception as e:
            logger.error(f"Error al obtener películas similares: {e}")
            raise
    
    def get_health(self) -> Dict:
        """Health check del servicio"""
        health_info = {
            "status": "healthy" if self.loaded else "not_initialized",
            "model_loaded": self.hybrid_model is not None,
            "model_version": self.model_version,
            "strategy": self.default_strategy,
            "cache_stats": self.cache.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Añadir estado de cada modelo
        if self.hybrid_model:
            health_info["models"] = {
                "als": self.hybrid_model.als is not None and self.hybrid_model.als.model is not None,
                "item_cf": self.hybrid_model.item_cf is not None and self.hybrid_model.item_cf.similarity_matrix is not None,
                "content_based": self.hybrid_model.content_based is not None and self.hybrid_model.content_based.movie_features is not None
            }
        
        return health_info
    
    def shutdown(self):
        """Limpia recursos"""
        logger.info("Shutting down RecommenderService...")
        if self.spark:
            self.spark.stop()
            logger.info("✓ SparkSession stopped")


# ==========================================
# Instancia global del servicio
# ==========================================

_service_instance: Optional[RecommenderService] = None


def get_recommender_service() -> RecommenderService:
    """Obtiene instancia global del servicio (singleton)"""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = RecommenderService()
    
    return _service_instance


def initialize_service():
    """Inicializa el servicio al startup de la aplicación"""
    service = get_recommender_service()
    service.initialize()


def shutdown_service():
    """Limpia el servicio al shutdown de la aplicación"""
    global _service_instance
    if _service_instance:
        _service_instance.shutdown()
        _service_instance = None
