#!/usr/bin/env python3
"""
Generador Streaming de Ratings Sintéticos con Spark Structured Streaming
==========================================================================

Genera ratings realistas con sesgos por género usando:
- Spark Structured Streaming con fuente 'rate'
- Preferencias de usuario por género ~ Distribución Dirichlet
- Selección de películas por top-k géneros preferidos
- Rating = f(afinidad usuario-película) + ruido gaussiano

Fase 7: Sistema de Recomendación de Películas a Gran Escala
"""

import sys
import json
import random
from typing import Dict, List, Tuple
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    DoubleType, LongType, ArrayType
)

# ==========================================
# Configuración
# ==========================================

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC = "ratings"
HDFS_BASE = "hdfs://namenode:9000"

# Rangos de datos reales
USER_ID_MIN = 1
USER_ID_MAX = 138493
MOVIE_ID_MIN = 1
MOVIE_ID_MAX = 131262

# Configuración de generación
DEFAULT_ROWS_PER_SECOND = 50  # Throughput configurable
NUM_USERS = 10000  # Usuarios sintéticos
NUM_GENRES = 20     # Top-20 géneros más populares
TOP_K_GENRES = 3    # Top-3 géneros preferidos por usuario

# Parámetros de Dirichlet (sesgos realistas)
DIRICHLET_ALPHA = 0.5  # Menor valor = más sesgo

# Parámetros de rating
RATING_MIN = 0.5
RATING_MAX = 5.0
RATING_INCREMENT = 0.5
GAUSSIAN_NOISE_STD = 0.3


# ==========================================
# Esquema de Datos
# ==========================================

RATING_SCHEMA = StructType([
    StructField("userId", IntegerType(), False),
    StructField("movieId", IntegerType(), False),
    StructField("rating", DoubleType(), False),
    StructField("timestamp", LongType(), False)
])


# ==========================================
# Funciones de Utilidad
# ==========================================

def create_spark_session(app_name: str = "SyntheticRatingsGenerator") -> SparkSession:
    """Crear sesión Spark con configuración para Kafka"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.shuffle.partitions", "20") \
        .config("spark.streaming.backpressure.enabled", "true") \
        .config("spark.streaming.kafka.maxRatePerPartition", "100") \
        .getOrCreate()


def load_movies_metadata(spark: SparkSession) -> Tuple[DataFrame, DataFrame]:
    """
    Cargar metadata de películas desde HDFS
    
    Returns:
        (movies_df, genres_metadata_df)
    """
    movies_path = f"{HDFS_BASE}/data/content_features/movies_features"
    genres_path = f"{HDFS_BASE}/data/content_features/genres_metadata"
    
    print(f"📂 Cargando movies desde: {movies_path}")
    movies_df = spark.read.parquet(movies_path)
    
    print(f"📂 Cargando géneros desde: {genres_path}")
    genres_df = spark.read.parquet(genres_path)
    
    return movies_df, genres_df


def build_genre_index(genres_df: DataFrame) -> Dict[str, int]:
    """
    Construir índice de género → ID
    
    Args:
        genres_df: DataFrame con columnas (idx, genre)
        
    Returns:
        {genre_name: genre_id}
    """
    genre_list = genres_df.select("genre", "idx").collect()
    return {row["genre"]: row["idx"] for row in genre_list}


def build_movies_by_genre(movies_df: DataFrame, spark: SparkSession) -> Dict[str, List[int]]:
    """
    Construir índice género → [movieIds]
    
    Explode genres array y agrupa por género
    
    Args:
        movies_df: DataFrame con columnas (movieId, genres)
        
    Returns:
        {genre: [movieId1, movieId2, ...]}
    """
    # Explotar array de géneros
    movies_exploded = movies_df.select(
        "movieId",
        F.explode(F.split("genres", r"\|")).alias("genre")
    )
    
    # Agrupar por género
    genre_movies = movies_exploded.groupBy("genre").agg(
        F.collect_list("movieId").alias("movieIds")
    ).collect()
    
    return {row["genre"]: row["movieIds"] for row in genre_movies}


def generate_user_preferences(
    num_users: int,
    genres: List[str],
    top_k: int = 3,
    alpha: float = 0.5
) -> Dict[int, Dict[str, float]]:
    """
    Generar preferencias de usuarios por género usando Dirichlet
    
    Args:
        num_users: Número de usuarios sintéticos
        genres: Lista de nombres de géneros
        top_k: Top-k géneros con más peso
        alpha: Parámetro de Dirichlet (menor = más sesgo)
        
    Returns:
        {userId: {genre: weight, ...}}
    """
    import numpy as np
    
    user_prefs = {}
    num_genres = len(genres)
    
    print(f"🎲 Generando preferencias para {num_users} usuarios...")
    print(f"   Géneros: {num_genres}, Top-K: {top_k}, Alpha: {alpha}")
    
    for user_id in range(1, num_users + 1):
        # Distribución Dirichlet para pesos de géneros
        weights = np.random.dirichlet([alpha] * num_genres)
        
        # Seleccionar top-k géneros
        top_indices = np.argsort(weights)[-top_k:][::-1]
        
        # Normalizar pesos de top-k
        top_weights = weights[top_indices]
        top_weights = top_weights / top_weights.sum()
        
        # Crear diccionario de preferencias
        prefs = {
            genres[idx]: float(top_weights[i])
            for i, idx in enumerate(top_indices)
        }
        
        user_prefs[user_id] = prefs
        
        if user_id % 1000 == 0:
            print(f"   Generados {user_id}/{num_users} usuarios...")
    
    print(f"✅ Preferencias generadas para {num_users} usuarios")
    return user_prefs


def calculate_affinity(user_prefs: Dict[str, float], movie_genres: List[str]) -> float:
    """
    Calcular afinidad usuario-película basada en géneros
    
    Args:
        user_prefs: {genre: weight} del usuario
        movie_genres: Lista de géneros de la película
        
    Returns:
        Afinidad [0, 1]
    """
    if not movie_genres or not user_prefs:
        return 0.5  # Neutral
    
    # Suma de pesos de géneros coincidentes
    affinity = sum(user_prefs.get(genre, 0.0) for genre in movie_genres)
    
    # Normalizar a [0, 1]
    return min(1.0, affinity)


def affinity_to_rating(affinity: float, noise_std: float = GAUSSIAN_NOISE_STD) -> float:
    """
    Convertir afinidad a rating con ruido gaussiano
    
    Args:
        affinity: Afinidad [0, 1]
        noise_std: Desviación estándar del ruido
        
    Returns:
        Rating [0.5, 5.0] en incrementos de 0.5
    """
    import numpy as np
    
    # Mapear afinidad a rating base [1, 5]
    base_rating = 1.0 + (affinity * 4.0)
    
    # Agregar ruido gaussiano
    noise = np.random.normal(0, noise_std)
    rating = base_rating + noise
    
    # Acotar a [0.5, 5.0]
    rating = max(RATING_MIN, min(RATING_MAX, rating))
    
    # Redondear a incrementos de 0.5
    rating = round(rating * 2) / 2.0
    
    return rating


# ==========================================
# UDF para Generación de Ratings
# ==========================================

def create_rating_generator_udf(
    user_prefs: Dict[int, Dict[str, float]],
    movies_by_genre: Dict[str, List[int]],
    movies_genres_map: Dict[int, List[str]]
):
    """
    Crear UDF para generar rating desde tick del rate source
    
    Args:
        user_prefs: Preferencias de usuarios
        movies_by_genre: Índice género → [movieIds]
        movies_genres_map: Índice movieId → [genres]
        
    Returns:
        UDF que convierte (tick) → (userId, movieId, rating, timestamp)
    """
    def generate_rating(tick_value: int, tick_timestamp: int) -> Dict:
        """
        Generar rating sintético a partir de tick
        
        Args:
            tick_value: Valor del tick (incrementa por cada row)
            tick_timestamp: Timestamp del tick
            
        Returns:
            {userId, movieId, rating, timestamp}
        """
        # Seleccionar usuario aleatorio
        user_id = random.randint(1, len(user_prefs))
        user_preferences = user_prefs.get(user_id, {})
        
        # Seleccionar género preferido del usuario
        if user_preferences:
            preferred_genres = list(user_preferences.keys())
            weights = [user_preferences[g] for g in preferred_genres]
            genre = random.choices(preferred_genres, weights=weights, k=1)[0]
        else:
            # Fallback: seleccionar género aleatorio
            genre = random.choice(list(movies_by_genre.keys()))
        
        # Seleccionar película del género
        candidate_movies = movies_by_genre.get(genre, [])
        if not candidate_movies:
            # Fallback: película aleatoria
            movie_id = random.randint(MOVIE_ID_MIN, MOVIE_ID_MAX)
            movie_genres = []
        else:
            movie_id = random.choice(candidate_movies)
            movie_genres = movies_genres_map.get(movie_id, [])
        
        # Calcular afinidad y generar rating
        affinity = calculate_affinity(user_preferences, movie_genres)
        rating = affinity_to_rating(affinity)
        
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

def create_streaming_source(spark: SparkSession, rows_per_second: int) -> DataFrame:
    """
    Crear fuente de streaming con rate source
    
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
    user_prefs: Dict,
    movies_by_genre: Dict,
    movies_genres_map: Dict
) -> DataFrame:
    """
    Transformar rate stream a ratings sintéticos
    
    Args:
        rate_stream: DataFrame de rate source
        user_prefs: Preferencias de usuarios
        movies_by_genre: Índice género → movieIds
        movies_genres_map: Índice movieId → géneros
        
    Returns:
        DataFrame con ratings sintéticos
    """
    # Crear UDF de generación
    generate_udf = create_rating_generator_udf(
        user_prefs,
        movies_by_genre,
        movies_genres_map
    )
    
    # Aplicar transformación
    ratings_df = rate_stream.select(
        generate_udf(
            F.col("value"),
            F.unix_timestamp(F.col("timestamp")) * 1000
        ).alias("rating_struct")
    ).select("rating_struct.*")
    
    return ratings_df


def write_to_kafka(ratings_df: DataFrame, checkpoint_path: str):
    """
    Escribir ratings a Kafka con formato JSON
    
    Args:
        ratings_df: DataFrame de ratings
        checkpoint_path: Ruta para checkpointing
    """
    print(f"📤 Configurando Kafka sink → {KAFKA_TOPIC}")
    print(f"   Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"   Checkpoint: {checkpoint_path}")
    
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
    Ejecutar generador de ratings sintéticos
    
    Args:
        rows_per_second: Throughput deseado (ratings/segundo)
    """
    print("=" * 70)
    print("GENERADOR DE RATINGS SINTÉTICOS - SPARK STRUCTURED STREAMING")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Throughput objetivo: {rows_per_second} ratings/segundo")
    print("=" * 70)
    print()
    
    # 1. Crear SparkSession
    print("🔧 Inicializando Spark...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # 2. Cargar metadata de películas
    print("\n📚 Cargando metadata de películas desde HDFS...")
    movies_df, genres_df = load_movies_metadata(spark)
    
    print(f"   Movies: {movies_df.count()} registros")
    print(f"   Géneros: {genres_df.count()} registros")
    
    # 3. Construir índices
    print("\n🔨 Construyendo índices...")
    
    # Índice de géneros
    genre_index = build_genre_index(genres_df)
    all_genres = list(genre_index.keys())[:NUM_GENRES]  # Top-20 géneros
    print(f"   Géneros activos: {len(all_genres)}")
    print(f"   Ejemplos: {', '.join(all_genres[:5])}")
    
    # Índice películas por género
    print("\n   Construyendo índice género → películas...")
    movies_by_genre = build_movies_by_genre(movies_df, spark)
    print(f"   Géneros con películas: {len(movies_by_genre)}")
    
    # Índice movieId → géneros
    print("\n   Construyendo índice película → géneros...")
    movies_list = movies_df.select("movieId", "genres").collect()
    movies_genres_map = {
        row["movieId"]: row["genres"].split("|") if row["genres"] else []
        for row in movies_list
    }
    print(f"   Películas indexadas: {len(movies_genres_map)}")
    
    # 4. Generar preferencias de usuarios
    print(f"\n👥 Generando preferencias de usuarios...")
    user_prefs = generate_user_preferences(
        num_users=NUM_USERS,
        genres=all_genres,
        top_k=TOP_K_GENRES,
        alpha=DIRICHLET_ALPHA
    )
    
    # Mostrar ejemplo de usuario
    sample_user = random.choice(list(user_prefs.keys()))
    print(f"\n   Ejemplo - Usuario {sample_user}:")
    for genre, weight in sorted(user_prefs[sample_user].items(), key=lambda x: -x[1]):
        print(f"     {genre}: {weight:.3f}")
    
    # 5. Crear streaming source
    print(f"\n📡 Iniciando rate source ({rows_per_second} rows/s)...")
    rate_stream = create_streaming_source(spark, rows_per_second)
    
    # 6. Transformar a ratings
    print("\n🎬 Configurando pipeline de transformación...")
    ratings_stream = transform_to_ratings(
        rate_stream,
        user_prefs,
        movies_by_genre,
        movies_genres_map
    )
    
    # 7. Escribir a Kafka
    checkpoint_path = f"{HDFS_BASE}/checkpoints/synthetic_ratings"
    
    print("\n📤 Iniciando escritura a Kafka...")
    query = write_to_kafka(ratings_stream, checkpoint_path)
    
    # 8. Monitoreo
    print("\n" + "=" * 70)
    print("✅ STREAMING INICIADO")
    print("=" * 70)
    print(f"Topic Kafka: {KAFKA_TOPIC}")
    print(f"Throughput: {rows_per_second} ratings/segundo")
    print(f"Usuarios sintéticos: {NUM_USERS}")
    print(f"Géneros activos: {len(all_genres)}")
    print(f"Checkpoint: {checkpoint_path}")
    print("=" * 70)
    print("\nPresiona Ctrl+C para detener...")
    print()
    
    # Esperar terminación
    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deteniendo streaming...")
        query.stop()
        print("✅ Streaming detenido")
    
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
