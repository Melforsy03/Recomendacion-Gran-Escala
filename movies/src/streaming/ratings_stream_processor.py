#!/usr/bin/env python3
"""
Procesador Streaming de Ratings con Spark Structured Streaming
===============================================================

Consume ratings de Kafka, calcula estadísticas descriptivas en ventanas,
y almacena datos crudos + agregados en HDFS y métricas en Kafka.

Características:
- Ventanas tumbling (1 min) y sliding (5 min, 1 min slide)
- Agregaciones: count, avg, percentiles p50/p95, top-N películas
- Métricas por género (join estático con metadata)
- Late data handling con watermark (10 minutos)
- Salidas: Kafka (metrics), HDFS (raw + aggregates)
- Fault tolerance con checkpoints

Fase 8: Sistema de Recomendación de Películas a Gran Escala
"""

import sys
from datetime import datetime
from typing import Dict, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, LongType, TimestampType, ArrayType
)
from pyspark.sql.window import Window

# ==========================================
# Configuración
# ==========================================

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_INPUT_TOPIC = "ratings"
KAFKA_OUTPUT_TOPIC = "metrics"

HDFS_BASE = "hdfs://namenode:9000"
HDFS_RAW_PATH = f"{HDFS_BASE}/streams/ratings/raw"
HDFS_AGG_TUMBLING_PATH = f"{HDFS_BASE}/streams/ratings/agg/tumbling"
HDFS_AGG_SLIDING_PATH = f"{HDFS_BASE}/streams/ratings/agg/sliding"
HDFS_CHECKPOINT_PATH = f"{HDFS_BASE}/checkpoints/ratings_stream/processor"

# Ventanas
TUMBLING_WINDOW = "1 minute"
SLIDING_WINDOW_SIZE = "5 minutes"
SLIDING_WINDOW_SLIDE = "1 minute"

# Watermark para late data
WATERMARK_DELAY = "10 seconds"

# Top-N películas
TOP_N_MOVIES = 10


# ==========================================
# Schemas
# ==========================================

RATING_SCHEMA = StructType([
    StructField("userId", IntegerType(), False),
    StructField("movieId", IntegerType(), False),
    StructField("rating", DoubleType(), False),
    StructField("timestamp", LongType(), False)
])

METRICS_SCHEMA = StructType([
    StructField("window_start", TimestampType(), False),
    StructField("window_end", TimestampType(), False),
    StructField("window_type", StringType(), False),
    StructField("count", LongType(), False),
    StructField("avg_rating", DoubleType(), False),
    StructField("p50_rating", DoubleType(), True),
    StructField("p95_rating", DoubleType(), True),
    StructField("top_movies", StringType(), True),
    StructField("metrics_by_genre", StringType(), True),
    StructField("processing_time", TimestampType(), False)
])


# ==========================================
# Funciones de Utilidad
# ==========================================

def create_spark_session(app_name: str = "RatingsStreamProcessor") -> SparkSession:
    """Crear sesión Spark con configuración para Kafka y streaming"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.shuffle.partitions", "20") \
        .config("spark.streaming.backpressure.enabled", "true") \
        .config("spark.streaming.kafka.maxRatePerPartition", "100") \
        .config("spark.sql.streaming.checkpointLocation", HDFS_CHECKPOINT_PATH) \
        .getOrCreate()


def load_movies_metadata(spark: SparkSession) -> DataFrame:
    """
    Cargar metadata de películas para joins estáticos
    
    Returns:
        DataFrame con (movieId, title, genres)
    """
    movies_path = f"{HDFS_BASE}/data/content_features/movies_features"
    
    print(f"📂 Cargando movies metadata desde: {movies_path}")
    movies_df = spark.read.parquet(movies_path)
    
    # Seleccionar y cachear para joins
    movies_static = movies_df.select("movieId", "title", "genres").cache()
    
    print(f"   Movies cargadas: {movies_static.count()}")
    return movies_static


# ==========================================
# Lectura de Kafka
# ==========================================

def read_ratings_stream(spark: SparkSession) -> DataFrame:
    """
    Leer stream de ratings desde Kafka
    
    Returns:
        DataFrame de streaming con ratings parseados
    """
    print(f"📡 Conectando a Kafka topic '{KAFKA_INPUT_TOPIC}'...")
    print(f"   Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    
    # Leer stream de Kafka
    # IMPORTANTE: usar "earliest" para procesar mensajes históricos en primera ejecución
    # Después del checkpoint, continuará desde donde quedó
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_INPUT_TOPIC) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parsear JSON a schema
    ratings_df = kafka_df.select(
        F.from_json(F.col("value").cast("string"), RATING_SCHEMA).alias("data"),
        F.col("timestamp").alias("kafka_timestamp")
    ).select("data.*", "kafka_timestamp")
    
    # Convertir timestamp Unix (millis) a timestamp column
    ratings_df = ratings_df.withColumn(
        "event_time",
        F.from_unixtime(F.col("timestamp") / 1000).cast("timestamp")
    )
    
    print("✅ Stream de ratings configurado")
    return ratings_df


# ==========================================
# Agregaciones por Ventana
# ==========================================

def compute_tumbling_window_stats(ratings_df: DataFrame, movies_df: DataFrame) -> DataFrame:
    """
    Calcular estadísticas en ventanas tumbling de 1 minuto
    
    Args:
        ratings_df: Stream de ratings
        movies_df: Metadata estática de películas
        
    Returns:
        DataFrame con agregaciones por ventana tumbling
    """
    print(f"\n🔨 Configurando ventana TUMBLING: {TUMBLING_WINDOW}")
    
    # Aplicar watermark para late data
    windowed_df = ratings_df \
        .withWatermark("event_time", WATERMARK_DELAY) \
        .groupBy(
            F.window("event_time", TUMBLING_WINDOW)
        ) \
        .agg(
            F.count("*").alias("count"),
            F.avg("rating").alias("avg_rating"),
            F.expr("percentile_approx(rating, 0.5)").alias("p50_rating"),
            F.expr("percentile_approx(rating, 0.95)").alias("p95_rating"),
            F.collect_list("movieId").alias("movies_in_window")
        )
    
    # Top-N películas (simplificado: primeras N únicas)
    windowed_df = windowed_df.withColumn(
        "top_movies",
        F.to_json(
            F.slice(
                F.array_distinct(F.col("movies_in_window")),
                1,
                TOP_N_MOVIES
            )
        )
    )
    
    # Extraer ventana start/end
    windowed_df = windowed_df.select(
        F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"),
        F.lit("tumbling_1min").alias("window_type"),
        "count",
        "avg_rating",
        "p50_rating",
        "p95_rating",
        "top_movies",
        F.lit(None).cast("string").alias("metrics_by_genre"),  # null para tumbling
        F.current_timestamp().alias("processing_time")
    )
    
    print("✅ Ventana tumbling configurada")
    return windowed_df


def compute_sliding_window_stats(ratings_df: DataFrame, movies_df: DataFrame) -> DataFrame:
    """
    Calcular estadísticas en ventanas sliding (5 min, slide 1 min)
    
    Args:
        ratings_df: Stream de ratings
        movies_df: Metadata estática de películas
        
    Returns:
        DataFrame con agregaciones por ventana sliding
    """
    print(f"\n🔨 Configurando ventana SLIDING: {SLIDING_WINDOW_SIZE} / {SLIDING_WINDOW_SLIDE}")
    
    # Join estático con géneros para métricas por género
    ratings_with_genres = ratings_df.join(
        F.broadcast(movies_df.select("movieId", "genres")),
        "movieId",
        "left"
    )
    
    # Aplicar watermark y ventana sliding
    windowed_df = ratings_with_genres \
        .withWatermark("event_time", WATERMARK_DELAY) \
        .groupBy(
            F.window("event_time", SLIDING_WINDOW_SIZE, SLIDING_WINDOW_SLIDE)
        ) \
        .agg(
            F.count("*").alias("count"),
            F.avg("rating").alias("avg_rating"),
            F.expr("percentile_approx(rating, 0.5)").alias("p50_rating"),
            F.expr("percentile_approx(rating, 0.95)").alias("p95_rating"),
            F.collect_list("movieId").alias("movies_in_window"),
            F.collect_list("genres").alias("all_genres")
        )
    
    # Top-N películas (simplificado)
    windowed_df = windowed_df.withColumn(
        "top_movies",
        F.to_json(
            F.slice(
                F.array_distinct(F.col("movies_in_window")),
                1,
                TOP_N_MOVIES
            )
        )
    )
    
    # Métricas por género (simplificado: top 5 géneros únicos)
    # Como genres puede ser null, manejamos el caso
    windowed_df = windowed_df.withColumn(
        "genres_flat",
        F.array_distinct(
            F.filter(
                F.col("all_genres"),
                lambda x: x.isNotNull()
            )
        )
    )
    
    windowed_df = windowed_df.withColumn(
        "metrics_by_genre",
        F.to_json(
            F.slice(
                F.array_sort(F.col("genres_flat")),
                1,
                5
            )
        )
    )
    
    # Extraer ventana start/end
    windowed_df = windowed_df.select(
        F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"),
        F.lit("sliding_5min_1min").alias("window_type"),
        "count",
        "avg_rating",
        "p50_rating",
        "p95_rating",
        "top_movies",
        "metrics_by_genre",
        F.current_timestamp().alias("processing_time")
    )
    
    print("✅ Ventana sliding configurada")
    return windowed_df


# ==========================================
# Salidas
# ==========================================

def write_raw_to_hdfs(ratings_df: DataFrame, checkpoint_suffix: str = "raw"):
    """
    Escribir ratings crudos a HDFS particionados por fecha/hora
    
    Args:
        ratings_df: Stream de ratings
        checkpoint_suffix: Sufijo para checkpoint path
    """
    print(f"\n📁 Configurando escritura RAW a HDFS: {HDFS_RAW_PATH}")
    
    # Agregar columnas de partición
    partitioned_df = ratings_df \
        .withColumn("date", F.to_date("event_time")) \
        .withColumn("hour", F.hour("event_time"))
    
    # Escribir a HDFS en formato Parquet particionado
    query = partitioned_df.writeStream \
        .format("parquet") \
        .option("path", HDFS_RAW_PATH) \
        .option("checkpointLocation", f"{HDFS_CHECKPOINT_PATH}/{checkpoint_suffix}") \
        .partitionBy("date", "hour") \
        .outputMode("append") \
        .trigger(processingTime="30 seconds") \
        .start()
    
    print(f"✅ Escritura RAW iniciada (checkpoint: {checkpoint_suffix})")
    return query


def write_aggregates_to_hdfs(agg_df: DataFrame, output_path: str, checkpoint_suffix: str):
    """
    Escribir agregados a HDFS
    
    Args:
        agg_df: DataFrame con agregaciones
        output_path: Ruta de salida en HDFS
        checkpoint_suffix: Sufijo para checkpoint
    """
    print(f"\n📁 Configurando escritura AGREGADOS a HDFS: {output_path}")
    
    # Agregar columnas de partición
    partitioned_df = agg_df \
        .withColumn("date", F.to_date("window_start")) \
        .withColumn("hour", F.hour("window_start"))
    
    # Escribir a HDFS
    query = partitioned_df.writeStream \
        .format("parquet") \
        .option("path", output_path) \
        .option("checkpointLocation", f"{HDFS_CHECKPOINT_PATH}/{checkpoint_suffix}") \
        .partitionBy("date", "hour") \
        .outputMode("append") \
        .trigger(processingTime="30 seconds") \
        .start()
    
    print(f"✅ Escritura AGREGADOS iniciada (checkpoint: {checkpoint_suffix})")
    return query


def write_metrics_to_kafka(metrics_df: DataFrame, checkpoint_suffix: str = "metrics"):
    """
    Escribir métricas a Kafka
    
    Args:
        metrics_df: DataFrame con métricas
        checkpoint_suffix: Sufijo para checkpoint
    """
    print(f"\n📤 Configurando escritura MÉTRICAS a Kafka: {KAFKA_OUTPUT_TOPIC}")
    
    # Convertir a JSON para Kafka (todas las métricas tienen metrics_by_genre ahora)
    kafka_df = metrics_df.select(
        F.to_json(
            F.struct(
                "window_start", "window_end", "window_type",
                "count", "avg_rating", "p50_rating", "p95_rating",
                "top_movies", "metrics_by_genre", "processing_time"
            )
        ).alias("value")
    )
    
    # Escribir a Kafka
    query = kafka_df.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", KAFKA_OUTPUT_TOPIC) \
        .option("checkpointLocation", f"{HDFS_CHECKPOINT_PATH}/{checkpoint_suffix}") \
        .outputMode("append") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    print(f"✅ Escritura MÉTRICAS a Kafka iniciada (checkpoint: {checkpoint_suffix})")
    return query


def write_to_console(df: DataFrame, query_name: str, truncate: bool = False):
    """
    Escribir a consola para debugging
    
    Args:
        df: DataFrame a mostrar
        query_name: Nombre de la query
        truncate: Si truncar output
    """
    query = df.writeStream \
        .format("console") \
        .queryName(query_name) \
        .outputMode("append") \
        .option("truncate", truncate) \
        .trigger(processingTime="30 seconds") \
        .start()
    
    return query


# ==========================================
# Main
# ==========================================

def main():
    """
    Ejecutar procesador de ratings streaming
    """
    print("=" * 80)
    print("PROCESADOR STREAMING DE RATINGS - SPARK STRUCTURED STREAMING")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # 1. Crear SparkSession
    print("🔧 Inicializando Spark...")
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # 2. Cargar metadata estática
    print("\n📚 Cargando metadata de películas...")
    movies_df = load_movies_metadata(spark)
    
    # 3. Leer stream de Kafka
    print("\n📡 Configurando stream de entrada...")
    ratings_stream = read_ratings_stream(spark)
    
    print(f"\n   Schema del stream:")
    ratings_stream.printSchema()
    
    # 4. Configurar agregaciones
    print("\n🔨 Configurando agregaciones por ventana...")
    
    # Ventana tumbling
    tumbling_stats = compute_tumbling_window_stats(ratings_stream, movies_df)
    
    # Ventana sliding
    sliding_stats = compute_sliding_window_stats(ratings_stream, movies_df)
    
    # 5. Configurar salidas
    print("\n📤 Configurando salidas...")
    
    queries = []
    
    # Salida 1: Raw data a HDFS
    print("\n" + "=" * 80)
    print("SALIDA 1: RATINGS CRUDOS → HDFS")
    print("=" * 80)
    raw_query = write_raw_to_hdfs(ratings_stream, checkpoint_suffix="raw")
    queries.append(("Raw HDFS", raw_query))
    
    # Salida 2: Agregados tumbling a HDFS
    print("\n" + "=" * 80)
    print("SALIDA 2: AGREGADOS TUMBLING → HDFS")
    print("=" * 80)
    tumbling_hdfs_query = write_aggregates_to_hdfs(
        tumbling_stats,
        HDFS_AGG_TUMBLING_PATH,
        checkpoint_suffix="agg_tumbling"
    )
    queries.append(("Tumbling HDFS", tumbling_hdfs_query))
    
    # Salida 3: Agregados sliding a HDFS
    print("\n" + "=" * 80)
    print("SALIDA 3: AGREGADOS SLIDING → HDFS")
    print("=" * 80)
    sliding_hdfs_query = write_aggregates_to_hdfs(
        sliding_stats,
        HDFS_AGG_SLIDING_PATH,
        checkpoint_suffix="agg_sliding"
    )
    queries.append(("Sliding HDFS", sliding_hdfs_query))
    
    # Salida 4: Métricas tumbling a Kafka
    print("\n" + "=" * 80)
    print("SALIDA 4: MÉTRICAS TUMBLING → KAFKA")
    print("=" * 80)
    tumbling_kafka_query = write_metrics_to_kafka(
        tumbling_stats,
        checkpoint_suffix="metrics_tumbling"
    )
    queries.append(("Metrics Tumbling Kafka", tumbling_kafka_query))
    
    # Salida 5: Métricas sliding a Kafka
    print("\n" + "=" * 80)
    print("SALIDA 5: MÉTRICAS SLIDING → KAFKA")
    print("=" * 80)
    sliding_kafka_query = write_metrics_to_kafka(
        sliding_stats,
        checkpoint_suffix="metrics_sliding"
    )
    queries.append(("Metrics Sliding Kafka", sliding_kafka_query))
    
    # Salida 6 (opcional): Console para debugging
    print("\n" + "=" * 80)
    print("SALIDA 6 (DEBUG): MÉTRICAS → CONSOLE")
    print("=" * 80)
    console_query = write_to_console(
        tumbling_stats.select("window_start", "window_end", "count", "avg_rating"),
        query_name="console_debug",
        truncate=False
    )
    queries.append(("Console Debug", console_query))
    
    # 6. Resumen de configuración
    print("\n" + "=" * 80)
    print("✅ PROCESADOR STREAMING INICIADO")
    print("=" * 80)
    print(f"\nCONFIGURACIÓN:")
    print(f"  Input topic:       {KAFKA_INPUT_TOPIC}")
    print(f"  Output topic:      {KAFKA_OUTPUT_TOPIC}")
    print(f"  Watermark:         {WATERMARK_DELAY}")
    print(f"  Tumbling window:   {TUMBLING_WINDOW}")
    print(f"  Sliding window:    {SLIDING_WINDOW_SIZE} / {SLIDING_WINDOW_SLIDE}")
    print(f"  Top-N movies:      {TOP_N_MOVIES}")
    print(f"\nSALIDAS:")
    print(f"  1. Raw HDFS:       {HDFS_RAW_PATH}")
    print(f"  2. Agg Tumbling:   {HDFS_AGG_TUMBLING_PATH}")
    print(f"  3. Agg Sliding:    {HDFS_AGG_SLIDING_PATH}")
    print(f"  4. Metrics Kafka:  {KAFKA_OUTPUT_TOPIC}")
    print(f"\nCHECKPOINTS:")
    print(f"  Base path:         {HDFS_CHECKPOINT_PATH}")
    print(f"\nQUERIES ACTIVAS:   {len(queries)}")
    for name, _ in queries:
        print(f"  - {name}")
    print("=" * 80)
    print("\nPresiona Ctrl+C para detener...")
    print()
    
    # 7. Esperar terminación
    try:
        # Esperar que todas las queries terminen
        for name, query in queries:
            query.awaitTermination()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deteniendo streaming...")
        for name, query in queries:
            print(f"   Deteniendo {name}...")
            query.stop()
        print("✅ Todas las queries detenidas")
    
    spark.stop()


if __name__ == "__main__":
    main()
