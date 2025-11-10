#!/usr/bin/env python3
"""
Análisis Batch sobre Datos en HDFS
===================================

Objetivo: Explorar y validar calidad/volúmenes, producir insights analíticos
         sobre los ratings almacenados en streaming.

Análisis implementados:
1. Distribución de ratings (global y por género)
2. Top-N películas por periodo temporal (día, hora)
3. Películas trending (delta de ranking entre ventanas temporales)

Salidas:
- /outputs/analytics/distributions/*.parquet
- /outputs/analytics/topn/*.parquet
- /outputs/analytics/trending/*.parquet

Fase 9: Sistema de Recomendación de Películas a Gran Escala
Fecha: 3 de noviembre de 2025
"""

import sys
from datetime import datetime, timedelta
from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, LongType, TimestampType, ArrayType
)

# ==========================================
# Configuración
# ==========================================

HDFS_BASE = "hdfs://namenode:9000"
RATINGS_RAW_PATH = f"{HDFS_BASE}/streams/ratings/raw"
RATINGS_AGG_PATH = f"{HDFS_BASE}/streams/ratings/agg/tumbling"
MOVIES_METADATA_PATH = f"{HDFS_BASE}/data/content_features/movies_features"
OUTPUT_BASE = f"{HDFS_BASE}/outputs/analytics"

# Configuración de análisis
TOP_N = 50
TRENDING_WINDOW_HOURS = 24  # Comparar ranking últimas 24h vs anteriores 24h

# ==========================================
# Funciones Auxiliares
# ==========================================

def print_section(title):
    """Imprime sección visual"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_subsection(title):
    """Imprime subsección"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")

def show_sample(df, name, n=10):
    """Muestra muestra de DataFrame"""
    print(f"\n📊 Muestra de {name}:")
    df.show(n, truncate=False)
    print(f"   Total registros: {df.count():,}")

# ==========================================
# Cargar Datos
# ==========================================

def load_data(spark):
    """Carga datos desde HDFS"""
    print_section("PASO 1: CARGA DE DATOS")
    
    print("📥 Cargando ratings raw desde streaming...")
    ratings_raw = spark.read.parquet(RATINGS_RAW_PATH)
    print(f"   ✅ {ratings_raw.count():,} ratings cargados")
    
    print("\n📥 Cargando metadata de películas...")
    movies = spark.read.parquet(MOVIES_METADATA_PATH)
    print(f"   ✅ {movies.count():,} películas cargadas")
    
    # Mostrar rango temporal de ratings
    time_range = ratings_raw.agg(
        F.min("timestamp").alias("min_ts"),
        F.max("timestamp").alias("max_ts")
    ).collect()[0]
    
    print(f"\n📅 Rango temporal de ratings:")
    print(f"   Desde: {time_range['min_ts']}")
    print(f"   Hasta: {time_range['max_ts']}")
    
    return ratings_raw, movies

# ==========================================
# Análisis 1: Distribución de Ratings
# ==========================================

def analyze_distributions(spark, ratings_raw, movies):
    """
    Analiza distribución de ratings global y por género
    
    Salida: /outputs/analytics/distributions/
    - global.parquet: Distribución global de ratings (0.5 a 5.0)
    - by_genre.parquet: Distribución por género
    - summary_stats.parquet: Estadísticas descriptivas
    """
    print_section("PASO 2: DISTRIBUCIÓN DE RATINGS")
    
    # 2.1 Distribución Global
    print_subsection("2.1 Distribución Global")
    
    global_dist = (ratings_raw
        .groupBy("rating")
        .agg(
            F.count("*").alias("count"),
            F.countDistinct("userId").alias("unique_users"),
            F.countDistinct("movieId").alias("unique_movies")
        )
        .withColumn("percentage", F.col("count") * 100.0 / F.sum("count").over(Window.partitionBy()))
        .orderBy("rating")
    )
    
    show_sample(global_dist, "Distribución Global", 20)
    
    # Guardar
    output_path = f"{OUTPUT_BASE}/distributions/global"
    (global_dist
        .coalesce(1)
        .write
        .mode("overwrite")
        .parquet(output_path, compression="snappy")
    )
    print(f"   ✅ Guardado en: {output_path}")
    
    # 2.2 Distribución por Género
    print_subsection("2.2 Distribución por Género")
    
    # Join con películas para obtener géneros
    ratings_with_genres = (ratings_raw
        .join(movies.select("movieId", "genres"), "movieId", "left")
    )
    
    # Normalizar/convertir 'genres' a array si viene como STRING (p. ej. "Action|Comedy")
    # Asumimos separador '|' típico de MovieLens; si ya es array, leave as is.
    # Normalizar: crear array a partir de la cadena (separador '|').
    # Si el campo es NULL, sustituimos por cadena vacía y split devuelve [''] que filtraremos.
    ratings_with_genres = ratings_with_genres.withColumn(
        "genres_arr",
        F.split(F.coalesce(F.col("genres"), F.lit("")), "\\\\|")
    )

    # Explotar géneros (cada género en una fila) usando la columna normalizada
    ratings_exploded = (ratings_with_genres
        .withColumn("genre", F.explode_outer("genres_arr"))
        .filter((F.col("genre").isNotNull()) & (F.col("genre") != ""))
    )
    
    genre_dist = (ratings_exploded
        .groupBy("genre", "rating")
        .agg(F.count("*").alias("count"))
        .withColumn("percentage", F.col("count") * 100.0 / F.sum("count").over(Window.partitionBy("genre")))
        .orderBy("genre", "rating")
    )
    
    # Mostrar algunos géneros
    for genre in ["Action", "Comedy", "Drama", "Horror", "Romance"]:
        genre_data = genre_dist.filter(F.col("genre") == genre)
        if genre_data.count() > 0:
            print(f"\n   {genre}:")
            genre_data.select("rating", "count", "percentage").show(10, truncate=False)
    
    # Guardar
    output_path = f"{OUTPUT_BASE}/distributions/by_genre"
    (genre_dist
        .write
        .mode("overwrite")
        .partitionBy("genre")
        .parquet(output_path, compression="snappy")
    )
    print(f"\n   ✅ Guardado en: {output_path}")
    
    # 2.3 Estadísticas Resumen
    print_subsection("2.3 Estadísticas Resumen")
    
    summary_stats = (ratings_raw
        .agg(
            F.count("*").alias("total_ratings"),
            F.countDistinct("userId").alias("unique_users"),
            F.countDistinct("movieId").alias("unique_movies"),
            F.avg("rating").alias("avg_rating"),
            F.stddev("rating").alias("stddev_rating"),
            F.min("rating").alias("min_rating"),
            F.max("rating").alias("max_rating"),
            F.expr("percentile_approx(rating, 0.25)").alias("p25_rating"),
            F.expr("percentile_approx(rating, 0.50)").alias("p50_rating"),
            F.expr("percentile_approx(rating, 0.75)").alias("p75_rating"),
            F.expr("percentile_approx(rating, 0.95)").alias("p95_rating")
        )
    )
    
    summary_stats.show(truncate=False, vertical=True)
    
    # Guardar
    output_path = f"{OUTPUT_BASE}/distributions/summary_stats"
    (summary_stats
        .coalesce(1)
        .write
        .mode("overwrite")
        .parquet(output_path, compression="snappy")
    )
    print(f"   ✅ Guardado en: {output_path}")

# ==========================================
# Análisis 2: Top-N por Periodo
# ==========================================

def analyze_topn_by_period(spark, ratings_raw, movies):
    """
    Top-N películas por periodo temporal (día, hora)
    
    Salida: /outputs/analytics/topn/
    - hourly.parquet: Top-N por hora
    - daily.parquet: Top-N por día
    """
    print_section("PASO 3: TOP-N POR PERIODO")
    
    # Agregar información de películas
    ratings_with_info = (ratings_raw
        .join(movies.select("movieId", "title", "genres"), "movieId", "left")
    )
    
    # 3.1 Top-N por Hora
    print_subsection("3.1 Top-N por Hora")
    
    hourly_stats = (ratings_with_info
        .withColumn("timestamp_dt", (F.col("timestamp") / 1000).cast(TimestampType()))
        .withColumn("hour", F.date_trunc("hour", "timestamp_dt"))
        .groupBy("hour", "movieId", "title")
        .agg(
            F.count("*").alias("rating_count"),
            F.avg("rating").alias("avg_rating"),
            F.countDistinct("userId").alias("unique_users")
        )
        # Calcular score: count * avg_rating
        .withColumn("score", F.col("rating_count") * F.col("avg_rating"))
    )
    
    # Ranking por hora
    window_hourly = Window.partitionBy("hour").orderBy(F.desc("score"))
    
    topn_hourly = (hourly_stats
        .withColumn("rank", F.row_number().over(window_hourly))
        .filter(F.col("rank") <= TOP_N)
        .orderBy("hour", "rank")
    )
    
    # Mostrar última hora disponible
    last_hour = topn_hourly.agg(F.max("hour").alias("max_hour")).collect()[0]["max_hour"]
    print(f"\n   Mostrando Top-10 de la hora: {last_hour}")
    (topn_hourly
        .filter(F.col("hour") == last_hour)
        .filter(F.col("rank") <= 10)
        .select("rank", "title", "rating_count", "avg_rating", "score")
        .show(10, truncate=False)
    )
    
    # Guardar
    output_path = f"{OUTPUT_BASE}/topn/hourly"
    (topn_hourly
        .write
        .mode("overwrite")
        .partitionBy("hour")
        .parquet(output_path, compression="snappy")
    )
    print(f"   ✅ Guardado en: {output_path}")
    
    # 3.2 Top-N por Día
    print_subsection("3.2 Top-N por Día")
    
    daily_stats = (ratings_with_info
        .withColumn("timestamp_dt", (F.col("timestamp") / 1000).cast(TimestampType()))
        .withColumn("day", F.date_trunc("day", "timestamp_dt"))
        .groupBy("day", "movieId", "title")
        .agg(
            F.count("*").alias("rating_count"),
            F.avg("rating").alias("avg_rating"),
            F.countDistinct("userId").alias("unique_users")
        )
        .withColumn("score", F.col("rating_count") * F.col("avg_rating"))
    )
    
    # Ranking por día
    window_daily = Window.partitionBy("day").orderBy(F.desc("score"))
    
    topn_daily = (daily_stats
        .withColumn("rank", F.row_number().over(window_daily))
        .filter(F.col("rank") <= TOP_N)
        .orderBy("day", "rank")
    )
    
    # Mostrar último día disponible
    last_day = topn_daily.agg(F.max("day").alias("max_day")).collect()[0]["max_day"]
    print(f"\n   Mostrando Top-10 del día: {last_day}")
    (topn_daily
        .filter(F.col("day") == last_day)
        .filter(F.col("rank") <= 10)
        .select("rank", "title", "rating_count", "avg_rating", "score")
        .show(10, truncate=False)
    )
    
    # Guardar
    output_path = f"{OUTPUT_BASE}/topn/daily"
    (topn_daily
        .write
        .mode("overwrite")
        .partitionBy("day")
        .parquet(output_path, compression="snappy")
    )
    print(f"   ✅ Guardado en: {output_path}")

# ==========================================
# Análisis 3: Películas Trending
# ==========================================

def analyze_trending(spark, ratings_raw, movies):
    """
    Identifica películas trending comparando ranking entre ventanas temporales
    
    Trending = películas que suben en ranking entre ventana anterior y actual
    
    Salida: /outputs/analytics/trending/
    - trending_movies.parquet: Películas con mayor cambio en ranking
    """
    print_section("PASO 4: PELÍCULAS TRENDING")
    
    # Obtener timestamp máximo (en milisegundos)
    max_ts = ratings_raw.agg(F.max("timestamp").alias("max_ts")).collect()[0]["max_ts"]
    
    # Definir ventanas temporales (en milisegundos)
    window_duration_ms = TRENDING_WINDOW_HOURS * 60 * 60 * 1000
    current_window_start = max_ts - window_duration_ms
    previous_window_start = max_ts - (window_duration_ms * 2)
    previous_window_end = current_window_start
    
    print(f"   Ventana actual: {current_window_start} - {max_ts}")
    print(f"   Ventana anterior: {previous_window_start} - {previous_window_end}")
    
    # Agregar información de películas
    ratings_with_info = (ratings_raw
        .join(movies.select("movieId", "title", "genres"), "movieId", "left")
    )
    
    # Estadísticas ventana actual
    current_stats = (ratings_with_info
        .filter((F.col("timestamp") >= current_window_start) & (F.col("timestamp") <= max_ts))
        .groupBy("movieId", "title")
        .agg(
            F.count("*").alias("current_count"),
            F.avg("rating").alias("current_avg_rating")
        )
        .withColumn("current_score", F.col("current_count") * F.col("current_avg_rating"))
    )
    
    # Ranking ventana actual
    window_current = Window.orderBy(F.desc("current_score"))
    current_ranked = (current_stats
        .withColumn("current_rank", F.row_number().over(window_current))
    )
    
    # Estadísticas ventana anterior
    previous_stats = (ratings_with_info
        .filter((F.col("timestamp") >= previous_window_start) & (F.col("timestamp") < previous_window_end))
        .groupBy("movieId", "title")
        .agg(
            F.count("*").alias("previous_count"),
            F.avg("rating").alias("previous_avg_rating")
        )
        .withColumn("previous_score", F.col("previous_count") * F.col("previous_avg_rating"))
    )
    
    # Ranking ventana anterior
    window_previous = Window.orderBy(F.desc("previous_score"))
    previous_ranked = (previous_stats
        .withColumn("previous_rank", F.row_number().over(window_previous))
    )
    
    # Join y calcular delta
    trending = (current_ranked
        .join(previous_ranked.select("movieId", "previous_rank", "previous_score"), "movieId", "left")
        .withColumn("previous_rank", F.coalesce("previous_rank", F.lit(9999)))
        .withColumn("rank_delta", F.col("previous_rank") - F.col("current_rank"))
        .withColumn("score_delta", F.col("current_score") - F.coalesce("previous_score", F.lit(0.0)))
        # Solo películas que aparecen en ambas ventanas o son nuevas
        .filter(F.col("current_count") >= 5)  # Mínimo 5 ratings
        .orderBy(F.desc("rank_delta"))
    )
    
    print_subsection("Top-20 Películas Trending (Mayor Subida en Ranking)")
    (trending
        .select(
            "current_rank",
            "previous_rank",
            "rank_delta",
            "title",
            "current_count",
            "current_avg_rating"
        )
        .show(20, truncate=False)
    )
    
    # Guardar todas las trending (top 200)
    output_path = f"{OUTPUT_BASE}/trending/trending_movies"
    (trending
        .filter(F.col("rank_delta") > 0)  # Solo las que subieron
        .orderBy(F.desc("rank_delta"))
        .limit(200)
        .coalesce(1)
        .write
        .mode("overwrite")
        .parquet(output_path, compression="snappy")
    )
    print(f"\n   ✅ Guardado en: {output_path}")

# ==========================================
# Main
# ==========================================

def main():
    """Punto de entrada principal"""
    
    print("\n" + "=" * 80)
    print("  ANÁLISIS BATCH SOBRE DATOS EN HDFS")
    print("  Fase 9: Dashboard y Analytics")
    print("=" * 80)
    print(f"\nInicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Crear Spark Session
    spark = (SparkSession.builder
        .appName("Batch_Analytics_FASE9")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )
    
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # 1. Cargar datos
        ratings_raw, movies = load_data(spark)
        
        # 2. Análisis de distribuciones
        analyze_distributions(spark, ratings_raw, movies)
        
        # 3. Top-N por periodo
        analyze_topn_by_period(spark, ratings_raw, movies)
        
        # 4. Trending
        analyze_trending(spark, ratings_raw, movies)
        
        print_section("✅ ANÁLISIS BATCH COMPLETADO")
        print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nResultados guardados en: {OUTPUT_BASE}")
        print("\nEstructura de salidas:")
        print("  📁 /outputs/analytics/")
        print("     ├── distributions/")
        print("     │   ├── global/")
        print("     │   ├── by_genre/")
        print("     │   └── summary_stats/")
        print("     ├── topn/")
        print("     │   ├── hourly/")
        print("     │   └── daily/")
        print("     └── trending/")
        print("         └── trending_movies/")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
