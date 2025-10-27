import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, to_json, struct, window, current_timestamp, expr,
    collect_list, slice, sum as _sum, count, sort_array, approx_count_distinct,
    max as _max, min as _min, avg as _avg, collect_set, row_number, desc
)
from pyspark.sql.types import ArrayType, StringType
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType
from pyspark.sql.window import Window

# spark_streaming_gold.py - VERSIÓN CORREGIDA SIN ORDERBY EN STREAMING
bronze_schema = StructType([
    StructField("movieId", IntegerType(), True),
    StructField("title", StringType(), True),
    StructField("genres", ArrayType(StringType()), True),
    StructField("imdbId", IntegerType(), True),
    StructField("tmdbId", IntegerType(), True),
    StructField("avg_rating", FloatType(), True),
    StructField("rating_count", IntegerType(), True),
    StructField("top_tags", ArrayType(StringType()), True),
    StructField("genome_relevance", ArrayType(
        StructType([
            StructField("tag", StringType(), True),
            StructField("relevance", FloatType(), True)
        ])
    ), True)
])

os.environ["PYSPARK_SUBMIT_ARGS"] = (
    "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 pyspark-shell"
)
# CONFIGURACIONES DE PERFORMANCE CRÍTICAS
spark = (SparkSession.builder
    .appName("Movies-STREAM-GOLD")
    .master("local[*]")
    .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false")
    .config("spark.sql.streaming.metricsEnabled", "true")
    .config("spark.sql.adaptive.enabled", "false")
    # NUEVAS CONFIGURACIONES PARA VELOCIDAD:
    .config("spark.sql.shuffle.partitions", "2")  # Reducir shuffles
    .config("spark.default.parallelism", "2")     # Reducir paralelismo
    .config("spark.streaming.backpressure.enabled", "true")  # Controlar flujo
    .config("spark.streaming.blockInterval", "500ms")  # Bloques más pequeños
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
    .getOrCreate())
spark.sparkContext.setLogLevel("WARN")

bronze_path = "hdfs://localhost:9000/user/movies/bronze/movies"

print("📖 Leyendo datos BRONZE...")
bronze = (spark.readStream
          .format("parquet")
          .schema(bronze_schema)
          .load(bronze_path))

# Agregar timestamp de procesamiento
with_ts = bronze.withColumn("processing_ts", current_timestamp())

print("🔧 Configurando métricas en tiempo real...")

# 1) MÉTRICAS DE THROUGHPUT - MÁS RÁPIDAS
throughput = (with_ts
    .withWatermark("processing_ts", "5 seconds")
    .groupBy(window(col("processing_ts"), "5 seconds"))
    .count()
    .withColumn("events_per_second", col("count") / 5)
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('window_start', window.start, " 
                "'window_end', window.end, "
                "'total_events', count, "
                "'events_per_second', events_per_second)) AS value"))

# 2) TOP PELÍCULAS POR RATING - VERSIÓN CORREGIDA (sin orderBy)
top_rated = (with_ts
    .filter(col("avg_rating").isNotNull())
    .withWatermark("processing_ts", "10 seconds")
    .groupBy(col("movieId"), col("title"))
    .agg(
        _avg("avg_rating").alias("current_avg_rating"),
        _sum("rating_count").alias("total_ratings"),
        _max("processing_ts").alias("last_update")
    )
    .filter(col("total_ratings") > 100)
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('movieId', movieId, "
                "'title', title, "
                "'avg_rating', current_avg_rating, "
                "'total_ratings', total_ratings)) AS value"))

# 3) ESTADÍSTICAS POR GÉNERO - MÁS DETALLADAS
genre_analytics = (with_ts
    .withColumn("genre", explode("genres"))
    .withWatermark("processing_ts", "10 seconds")
    .groupBy(window(col("processing_ts"), "30 seconds"), col("genre"))
    .agg(
        _avg("avg_rating").alias("avg_rating"),
        _sum("rating_count").alias("total_votes"),
        count("movieId").alias("movie_count"),
        _max("avg_rating").alias("max_rating"),
        _min("avg_rating").alias("min_rating")
    )
    .filter(col("avg_rating").isNotNull())
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('window_start', window.start, "
                "'genre', genre, "
                "'avg_rating', avg_rating, "
                "'total_votes', total_votes, "
                "'movie_count', movie_count, "
                "'max_rating', max_rating, "
                "'min_rating', min_rating)) AS value"))

# 4) TAGS MÁS POPULARES - VERSIÓN CORREGIDA (sin orderBy)
popular_tags = (with_ts
    .withColumn("tag", explode("top_tags"))
    .withWatermark("processing_ts", "10 seconds")
    .groupBy(window(col("processing_ts"), "20 seconds"), col("tag"))
    .agg(count("movieId").alias("tag_count"))
    # En lugar de orderBy, usamos collect_list y sort_array en el dashboard
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('window_start', window.start, "
                "'tag', tag, "
                "'count', tag_count)) AS value"))

# 5) ESTADÍSTICAS GENERALES DEL CATÁLOGO
catalog_stats = (with_ts
    .withWatermark("processing_ts", "15 seconds")
    .groupBy(window(col("processing_ts"), "15 seconds"))
    .agg(
        count("movieId").alias("total_movies"),
        _avg("avg_rating").alias("catalog_avg_rating"),
        _sum("rating_count").alias("total_catalog_ratings"),
        approx_count_distinct("movieId").alias("unique_movies"),
        collect_set("genres").alias("all_genres")
    )
    .withColumn("unique_genres", expr("size(flatten(all_genres))"))
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('window_start', window.start, "
                "'total_movies', total_movies, "
                "'catalog_avg_rating', catalog_avg_rating, "
                "'total_ratings', total_catalog_ratings, "
                "'unique_genres', unique_genres)) AS value"))

# 6) DISTRIBUCIÓN DE RATINGS - NUEVA MÉTRICA
rating_distribution = (with_ts
    .filter(col("avg_rating").isNotNull())
    .withWatermark("processing_ts", "10 seconds")
    .groupBy(window(col("processing_ts"), "20 seconds"))
    .agg(
        _avg("avg_rating").alias("overall_avg"),
        _min("avg_rating").alias("min_rating"),
        _max("avg_rating").alias("max_rating"),
        expr("percentile_approx(avg_rating, 0.5)").alias("median_rating"),
        expr("percentile_approx(avg_rating, 0.25)").alias("q1_rating"),
        expr("percentile_approx(avg_rating, 0.75)").alias("q3_rating")
    )
    .selectExpr("CAST(null AS STRING) AS key",
                "to_json(named_struct('window_start', window.start, "
                "'overall_avg', overall_avg, "
                "'min_rating', min_rating, "
                "'max_rating', max_rating, "
                "'median_rating', median_rating, "
                "'q1_rating', q1_rating, "
                "'q3_rating', q3_rating)) AS value"))

# CONFIGURACIÓN KAFKA
kafka_server = "localhost:9092"

print("🚀 Iniciando queries de streaming GOLD...")

# Iniciar todas las queries con configuraciones optimizadas
queries = []

# Throughput
throughput_q = (throughput.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.throughput")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_throughput")
    .outputMode("update")
    .trigger(processingTime="5 seconds")
    .start())
queries.append(throughput_q)
print("✅ Throughput metrics iniciado")

# Top Rated Movies (usando complete mode para permitir ordenamiento)
top_rated_q = (top_rated.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.top_rated")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_top_rated")
    .outputMode("complete")  # Complete mode permite más operaciones
    .trigger(processingTime="10 seconds")
    .start())
queries.append(top_rated_q)
print("✅ Top rated movies iniciado")

# Genre Analytics
genre_q = (genre_analytics.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.genre_analytics")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_genre")
    .outputMode("update")
    .trigger(processingTime="10 seconds")
    .start())
queries.append(genre_q)
print("✅ Genre analytics iniciado")

# Popular Tags (corregido - sin orderBy)
tags_q = (popular_tags.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.popular_tags")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_tags")
    .outputMode("update")
    .trigger(processingTime="10 seconds")
    .start())
queries.append(tags_q)
print("✅ Popular tags iniciado")

# Catalog Stats
catalog_q = (catalog_stats.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.catalog_stats")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_catalog")
    .outputMode("update")
    .trigger(processingTime="10 seconds")
    .start())
queries.append(catalog_q)
print("✅ Catalog stats iniciado")

# Rating Distribution
rating_dist_q = (rating_distribution.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_server)
    .option("topic", "metrics.rating_dist")
    .option("checkpointLocation", "hdfs://localhost:9000/user/movies/checkpoints/gold_rating_dist")
    .outputMode("update")
    .trigger(processingTime="10 seconds")
    .start())
queries.append(rating_dist_q)
print("✅ Rating distribution iniciado")

print("🎯 Todas las queries GOLD iniciadas - Datos fluyendo!")

# Monitor de progreso mejorado
def monitor_queries():
    import time
    while True:
        try:
            print("\n" + "="*60)
            print("📊 ESTADO ACTUAL DE LAS QUERIES GOLD:")
            total_rows = 0
            for i, q in enumerate(queries):
                progress = q.lastProgress
                if progress and 'numInputRows' in progress:
                    rows = progress['numInputRows']
                    total_rows += rows
                    status = "🟢 ACTIVA" if progress['isActive'] else "🔴 INACTIVA"
                    print(f"Query {i+1}: {progress.get('name', 'N/A')} - {rows} filas - {status}")
            
            print(f"📈 TOTAL: {total_rows} filas procesadas")
            print("="*60)
            time.sleep(20)  # Menos frecuente para reducir logs
        except Exception as e:
            print(f"⚠️ Error en monitor: {e}")
            time.sleep(20)

import threading
monitor_thread = threading.Thread(target=monitor_queries, daemon=True)
monitor_thread.start()

# Esperar a que haya datos antes de mostrar el mensaje final
import time
time.sleep(10)
print("🔥 Pipeline GOLD completamente operativo!")
print("📊 Los datos deberían aparecer en el dashboard pronto...")

spark.streams.awaitAnyTermination()