#!/usr/bin/env python3
"""
Generador Latente Analítico de Ratings Sintéticos
==================================================

Enfoque: Generador basado en factorización matricial sin entrenamiento previo.
Muestrea factores latentes para usuarios y películas, y calcula ratings con
un modelo simple: rating = dot_product(user, item) + bias + noise

Ventajas sobre el enfoque anterior:
- ✅ Más rápido: No carga metadata ni construye índices complejos
- ✅ Más simple: Solo algebra lineal básica
- ✅ Más realista: Usa la misma matemática que ALS
- ✅ Sin entrenamiento: Genera factores on-the-fly

Modelo:
    rating(u, i) = dot(U[u], I[i]) + b_u + b_i + μ + ε
    
    Donde:
    - U[u] ~ N(0, 1/√rank) : factores latentes de usuario
    - I[i] ~ N(0, 1/√rank) : factores latentes de película
    - b_u ~ N(0, 0.1)      : sesgo de usuario
    - b_i ~ N(0, 0.1)      : sesgo de película
    - μ = 3.5              : rating global promedio
    - ε ~ N(0, σ)          : ruido gaussiano

Fase 7 Mejorada: Sistema de Recomendación de Películas a Gran Escala
"""

import sys
import json
import random
import numpy as np
from typing import Dict, Tuple
from datetime import datetime

# Hacer los imports de PySpark opcionales para permitir importar el módulo
# incluso cuando PySpark no está instalado (útil para entornos ligeros)
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, IntegerType,
        DoubleType, LongType
    )
    SPARK_AVAILABLE = True
except Exception:
    SPARK_AVAILABLE = False
    SparkSession = None
    DataFrame = None
    F = None
    StructType = None
    StructField = None
    IntegerType = None
    DoubleType = None
    LongType = None

# ==========================================
# Configuración
# ==========================================

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC = "ratings"
HDFS_BASE = "hdfs://namenode:9000"

# Rangos de IDs (basados en MovieLens 20M)
USER_ID_MIN = 1
USER_ID_MAX = 138493
MOVIE_ID_MIN = 1
MOVIE_ID_MAX = 131262

# Configuración de generación
DEFAULT_ROWS_PER_SECOND = 100  # Throughput más alto por ser más rápido

# Parámetros del modelo latente
LATENT_RANK = 20               # Dimensión de factores latentes
GLOBAL_MEAN = 3.5              # Rating promedio global
USER_BIAS_STD = 0.15           # Desviación estándar de sesgo de usuario
ITEM_BIAS_STD = 0.10           # Desviación estándar de sesgo de película
NOISE_STD = 0.4                # Ruido gaussiano en rating final
LATENT_STD = 1.0 / np.sqrt(LATENT_RANK)  # Desviación para factores latentes

# Rangos de rating
RATING_MIN = 0.5
RATING_MAX = 5.0

# Cache de factores (para eficiencia)
CACHE_SIZE_USERS = 5000        # Cachear factores de 5k usuarios
CACHE_SIZE_ITEMS = 10000       # Cachear factores de 10k películas

# ==========================================
# Esquema de Datos
# ==========================================

if SPARK_AVAILABLE:
    RATING_SCHEMA = StructType([
        StructField("userId", IntegerType(), False),
        StructField("movieId", IntegerType(), False),
        StructField("rating", DoubleType(), False),
        StructField("timestamp", LongType(), False)
    ])
else:
    RATING_SCHEMA = None


# ==========================================
# Generador de Factores Latentes
# ==========================================

class LatentFactorGenerator:
    """
    Generador de factores latentes y sesgos para usuarios y películas.
    
    Usa caché LRU para evitar regenerar factores frecuentemente.
    """
    
    def __init__(
        self,
        rank: int = LATENT_RANK,
        global_mean: float = GLOBAL_MEAN,
        user_bias_std: float = USER_BIAS_STD,
        item_bias_std: float = ITEM_BIAS_STD,
        latent_std: float = LATENT_STD,
        cache_users: int = CACHE_SIZE_USERS,
        cache_items: int = CACHE_SIZE_ITEMS,
        seed: int = None
    ):
        """
        Args:
            rank: Dimensión de factores latentes
            global_mean: Rating promedio global
            user_bias_std: Desviación de sesgos de usuario
            item_bias_std: Desviación de sesgos de película
            latent_std: Desviación de factores latentes
            cache_users: Tamaño de caché para usuarios
            cache_items: Tamaño de caché para películas
            seed: Semilla para reproducibilidad
        """
        self.rank = rank
        self.global_mean = global_mean
        self.user_bias_std = user_bias_std
        self.item_bias_std = item_bias_std
        self.latent_std = latent_std
        
        # Cachés (diccionarios simples - LRU real sería más complejo)
        self.user_cache = {}
        self.item_cache = {}
        self.cache_users = cache_users
        self.cache_items = cache_items
        
        # RNG con seed para reproducibilidad
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
    
    def get_user_factors(self, user_id: int) -> Tuple[np.ndarray, float]:
        """
        Obtener factores latentes y sesgo para un usuario.
        
        Args:
            user_id: ID de usuario
            
        Returns:
            (factors, bias) donde factors es array de shape (rank,)
        """
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        # Generar factores latentes ~ N(0, latent_std)
        factors = np.random.normal(0, self.latent_std, self.rank)
        
        # Generar sesgo ~ N(0, user_bias_std)
        bias = np.random.normal(0, self.user_bias_std)
        
        # Cachear si hay espacio
        if len(self.user_cache) < self.cache_users:
            self.user_cache[user_id] = (factors, bias)
        
        return factors, bias
    
    def get_item_factors(self, item_id: int) -> Tuple[np.ndarray, float]:
        """
        Obtener factores latentes y sesgo para una película.
        
        Args:
            item_id: ID de película
            
        Returns:
            (factors, bias) donde factors es array de shape (rank,)
        """
        if item_id in self.item_cache:
            return self.item_cache[item_id]
        
        # Generar factores latentes ~ N(0, latent_std)
        factors = np.random.normal(0, self.latent_std, self.rank)
        
        # Generar sesgo ~ N(0, item_bias_std)
        bias = np.random.normal(0, self.item_bias_std)
        
        # Cachear si hay espacio
        if len(self.item_cache) < self.cache_items:
            self.item_cache[item_id] = (factors, bias)
        
        return factors, bias
    
    def predict_rating(self, user_id: int, item_id: int, noise_std: float = NOISE_STD) -> float:
        """
        Predecir rating usando factorización matricial.
        
        rating = dot(user_factors, item_factors) + user_bias + item_bias + global_mean + noise
        
        Args:
            user_id: ID de usuario
            item_id: ID de película
            noise_std: Desviación del ruido gaussiano
            
        Returns:
            Rating predicho en [0.5, 5.0]
        """
        # Obtener factores y sesgos
        user_factors, user_bias = self.get_user_factors(user_id)
        item_factors, item_bias = self.get_item_factors(item_id)
        
        # Producto punto de factores latentes
        dot_product = np.dot(user_factors, item_factors)
        
        # Rating base = dot_product + sesgos + media global
        base_rating = dot_product + user_bias + item_bias + self.global_mean
        
        # Agregar ruido gaussiano
        noise = np.random.normal(0, noise_std)
        rating = base_rating + noise
        
        # Acotar a [0.5, 5.0]
        rating = max(RATING_MIN, min(RATING_MAX, rating))
        
        # Redondear a incrementos de 0.5
        rating = round(rating * 2) / 2.0
        
        return float(rating)
    
    def get_cache_stats(self) -> Dict:
        """Obtener estadísticas de caché"""
        return {
            "users_cached": len(self.user_cache),
            "items_cached": len(self.item_cache),
            "cache_users_max": self.cache_users,
            "cache_items_max": self.cache_items
        }


# ==========================================
# UDF para Generación de Ratings
# ==========================================

def create_rating_generator_udf(generator: LatentFactorGenerator):
    """
    Crear UDF para generar rating desde tick del rate source.
    
    Args:
        generator: Instancia de LatentFactorGenerator
        
    Returns:
        UDF que convierte (tick_value, tick_timestamp) → rating_struct
    """
    def generate_rating(tick_value: int, tick_timestamp: int) -> Dict:
        """
        Generar rating sintético a partir de tick.
        
        Args:
            tick_value: Valor del tick (no usado, solo para variabilidad)
            tick_timestamp: Timestamp del tick
            
        Returns:
            {userId, movieId, rating, timestamp}
        """
        # Seleccionar usuario y película aleatorios
        user_id = random.randint(USER_ID_MIN, USER_ID_MAX)
        movie_id = random.randint(MOVIE_ID_MIN, MOVIE_ID_MAX)
        
        # Predecir rating usando modelo latente
        rating = generator.predict_rating(user_id, movie_id)
        
        return {
            "userId": int(user_id),
            "movieId": int(movie_id),
            "rating": float(rating),
            "timestamp": int(tick_timestamp)
        }
    
    return F.udf(generate_rating, RATING_SCHEMA)


# ==========================================
# Pipeline de Streaming
# ==========================================

def create_spark_session(app_name: str = "LatentRatingsGenerator") -> SparkSession:
    """Crear sesión Spark con configuración para Kafka"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.streaming.backpressure.enabled", "true") \
        .config("spark.streaming.kafka.maxRatePerPartition", "200") \
        .getOrCreate()


def create_streaming_source(spark: SparkSession, rows_per_second: int) -> DataFrame:
    """
    Crear fuente de streaming con rate source.
    
    Args:
        spark: SparkSession
        rows_per_second: Throughput deseado
        
    Returns:
        DataFrame de streaming con columnas (timestamp, value)
    """
    print(f"📡 Creando rate source: {rows_per_second} rows/second")
    
    return spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", rows_per_second) \
        .load()


def transform_to_ratings(
    rate_stream: DataFrame,
    generator: LatentFactorGenerator
) -> DataFrame:
    """
    Transformar rate stream a ratings sintéticos.
    
    Args:
        rate_stream: DataFrame de rate source
        generator: Generador de factores latentes
        
    Returns:
        DataFrame con ratings sintéticos
    """
    # Crear UDF de generación
    generate_udf = create_rating_generator_udf(generator)
    
    # Aplicar transformación
    ratings_df = rate_stream.select(
        generate_udf(
            F.col("value"),
            (F.unix_timestamp(F.col("timestamp")) * 1000).cast("long")
        ).alias("rating_struct")
    ).select("rating_struct.*")
    
    return ratings_df


def write_to_kafka(ratings_df: DataFrame, checkpoint_path: str, spark: SparkSession):
    """
    Escribir ratings a Kafka con formato JSON.
    
    Args:
        ratings_df: DataFrame de ratings
        checkpoint_path: Ruta para checkpointing
        spark: SparkSession para limpiar checkpoint si es necesario
    """
    print(f"📤 Configurando Kafka sink → {KAFKA_TOPIC}")
    print(f"   Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"   Checkpoint: {checkpoint_path}")
    print(f"   💡 Si hay errores de checkpoint, ejecuta: ./scripts/clean-checkpoints.sh latent")
    
    # Convertir a JSON
    kafka_df = ratings_df.select(
        F.to_json(F.struct(
            "userId", "movieId", "rating", "timestamp"
        )).alias("value")
    )
    
    # Escribir a Kafka
    query = kafka_df.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", KAFKA_TOPIC) \
        .option("checkpointLocation", checkpoint_path) \
        .outputMode("append") \
        .start()
    
    return query


# ==========================================
# Main
# ==========================================

def main(rows_per_second: int = DEFAULT_ROWS_PER_SECOND):
    """
    Ejecutar generador de ratings sintéticos con modelo latente.
    
    Args:
        rows_per_second: Throughput deseado (ratings/segundo)
    """
    print("=" * 80)
    print("GENERADOR LATENTE ANALÍTICO DE RATINGS SINTÉTICOS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Throughput objetivo: {rows_per_second} ratings/segundo")
    print("=" * 80)
    print()
    
    # 1. Crear SparkSession
    print("🔧 Inicializando Spark...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # 2. Crear generador de factores latentes
    print("\n🎲 Inicializando generador de factores latentes...")
    print(f"   Rank: {LATENT_RANK}")
    print(f"   Global mean: {GLOBAL_MEAN}")
    print(f"   User bias std: {USER_BIAS_STD}")
    print(f"   Item bias std: {ITEM_BIAS_STD}")
    print(f"   Noise std: {NOISE_STD}")
    print(f"   Caché usuarios: {CACHE_SIZE_USERS}")
    print(f"   Caché películas: {CACHE_SIZE_ITEMS}")
    
    generator = LatentFactorGenerator(
        rank=LATENT_RANK,
        global_mean=GLOBAL_MEAN,
        user_bias_std=USER_BIAS_STD,
        item_bias_std=ITEM_BIAS_STD,
        latent_std=LATENT_STD,
        cache_users=CACHE_SIZE_USERS,
        cache_items=CACHE_SIZE_ITEMS,
        seed=42  # Para reproducibilidad en desarrollo
    )
    
    # 3. Generar algunos ratings de ejemplo
    print("\n📊 Generando ratings de ejemplo:")
    for i in range(3):
        u = random.randint(1, 1000)
        m = random.randint(1, 1000)
        r = generator.predict_rating(u, m)
        print(f"   Usuario {u:5d} → Película {m:5d} : Rating {r:.1f}")
    
    # 4. Crear streaming source
    print(f"\n📡 Iniciando rate source ({rows_per_second} rows/s)...")
    rate_stream = create_streaming_source(spark, rows_per_second)
    
    # 5. Transformar a ratings
    print("\n🎬 Configurando pipeline de transformación...")
    ratings_stream = transform_to_ratings(rate_stream, generator)
    
    # 6. Escribir a Kafka
    checkpoint_path = f"{HDFS_BASE}/checkpoints/latent_ratings"
    
    print("\n📤 Iniciando escritura a Kafka...")
    query = write_to_kafka(ratings_stream, checkpoint_path, spark)
    
    # 7. Monitoreo
    print("\n" + "=" * 80)
    print("✅ STREAMING INICIADO")
    print("=" * 80)
    print(f"Topic Kafka: {KAFKA_TOPIC}")
    print(f"Throughput: {rows_per_second} ratings/segundo")
    print(f"Modelo: Factorización Matricial (rank={LATENT_RANK})")
    print(f"Rango usuarios: [{USER_ID_MIN}, {USER_ID_MAX}]")
    print(f"Rango películas: [{MOVIE_ID_MIN}, {MOVIE_ID_MAX}]")
    print(f"Checkpoint: {checkpoint_path}")
    print("=" * 80)
    print("\nPresiona Ctrl+C para detener...")
    print()
    
    # Esperar terminación
    try:
        # Mostrar stats de caché cada 60 segundos
        import time
        start_time = time.time()
        while query.isActive:
            time.sleep(60)
            elapsed = time.time() - start_time
            stats = generator.get_cache_stats()
            print(f"\n[{elapsed:.0f}s] Caché stats: "
                  f"Users={stats['users_cached']}/{stats['cache_users_max']}, "
                  f"Items={stats['items_cached']}/{stats['cache_items_max']}")
    except KeyboardInterrupt:
        print("\n\n⚠️  Deteniendo streaming...")
        query.stop()
        print("✅ Streaming detenido")
    
    # Mostrar estadísticas finales
    final_stats = generator.get_cache_stats()
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS FINALES DE CACHÉ")
    print("=" * 80)
    print(f"Usuarios cacheados: {final_stats['users_cached']:,}")
    print(f"Películas cacheadas: {final_stats['items_cached']:,}")
    print("=" * 80)
    
    spark.stop()


if __name__ == "__main__":
    # Parsear argumentos
    if len(sys.argv) > 1:
        try:
            rows_per_second = int(sys.argv[1])
        except ValueError:
            print(f"❌ Error: '{sys.argv[1]}' no es un número válido")
            print(f"Uso: {sys.argv[0]} [rows_per_second]")
            sys.exit(1)
    else:
        rows_per_second = DEFAULT_ROWS_PER_SECOND
    
    main(rows_per_second)
