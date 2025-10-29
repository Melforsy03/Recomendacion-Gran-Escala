#!/usr/bin/env python3
"""Verificación de Content Features"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

HDFS_BASE = "hdfs://namenode:9000"
FEATURES_PATH = f"{HDFS_BASE}/data/content_features"

spark = (SparkSession.builder
         .appName("Verify_Content_Features")
         .config("spark.sql.adaptive.enabled", "true")
         .getOrCreate())

print("\n" + "="*70)
print("  VERIFICACIÓN CONTENT FEATURES - FASE 4")
print("="*70 + "\n")

# Cargar features
print("📥 Cargando features...")
features = spark.read.parquet(f"{FEATURES_PATH}/movies_features")

print(f"\n✅ {features.count():,} películas con features")
print(f"✅ Columnas: {features.columns}\n")

# Schema
print("📋 Schema:")
features.printSchema()

# Estadísticas
print("\n📊 Estadísticas:")
stats = features.select(
    F.count("*").alias("total_movies"),
    F.avg("n_genres").alias("avg_genres"),
    F.avg("n_tags").alias("avg_tags"),
    F.min("n_tags").alias("min_tags"),
    F.max("n_tags").alias("max_tags"),
    F.avg("avg_tag_relevance").alias("avg_relevance")
).collect()[0]

print(f"  Total películas: {stats.total_movies:,}")
print(f"  Géneros promedio: {stats.avg_genres:.2f}")
print(f"  Tags promedio: {stats.avg_tags:.2f}")
print(f"  Tags min/max: {stats.min_tags} / {stats.max_tags}")
print(f"  Relevancia promedio: {stats.avg_relevance:.3f}")

# Distribución de tags
print("\n📈 Distribución de número de tags:")
dist = features.groupBy("n_tags").count().orderBy("n_tags")
dist.show(30)

# Películas con más tags
print("\n🏆 Top 10 películas con más tags:")
features.select("movieId", "title", "n_tags", "avg_tag_relevance").orderBy(F.desc("n_tags")).show(10, truncate=False)

# Películas sin tags
print(f"\n⚠️  Películas sin tags (n_tags = 0): {features.filter(F.col('n_tags') == 0).count():,}")

# Muestra de features
print("\n📋 Muestra de features (5 películas):")
features.select("movieId", "title", "genres", "n_genres", "n_tags").show(5, truncate=False)

# Cargar metadatos
print("\n📚 Metadatos de Géneros:")
genres_meta = spark.read.parquet(f"{FEATURES_PATH}/genres_metadata")
genres_meta.orderBy("idx").show(20, truncate=False)

print("\n📚 Top 10 Tags Metadata:")
tags_meta = spark.read.parquet(f"{FEATURES_PATH}/tags_metadata")
tags_meta.select("tagId", "tag", "avg_relevance", "n_movies").orderBy(F.desc("avg_relevance")).show(10, truncate=False)

# Verificar nulos
print("\n🔍 Verificación de nulos:")
null_check = features.select(
    F.sum(F.when(F.col("movieId").isNull(), 1).otherwise(0)).alias("null_movieId"),
    F.sum(F.when(F.col("genres_vec").isNull(), 1).otherwise(0)).alias("null_genres_vec"),
    F.sum(F.when(F.col("tags_vec").isNull(), 1).otherwise(0)).alias("null_tags_vec"),
    F.sum(F.when(F.col("n_genres").isNull(), 1).otherwise(0)).alias("null_n_genres"),
    F.sum(F.when(F.col("n_tags").isNull(), 1).otherwise(0)).alias("null_n_tags")
).collect()[0]

print(f"  movieId nulos: {null_check.null_movieId}")
print(f"  genres_vec nulos: {null_check.null_genres_vec}")
print(f"  tags_vec nulos: {null_check.null_tags_vec}")
print(f"  n_genres nulos: {null_check.null_n_genres}")
print(f"  n_tags nulos: {null_check.null_n_tags}")

if (null_check.null_movieId == 0 and 
    null_check.null_genres_vec == 0 and 
    null_check.null_tags_vec == 0):
    print("\n✅ VERIFICACIÓN EXITOSA - FEATURES VÁLIDAS")
else:
    print("\n❌ HAY NULOS CRÍTICOS")

print("\n" + "="*70)
print("  Dimensiones de Vectores:")
print("="*70)
print(f"  Genres Vector: 19 dimensiones (one-hot)")
print(f"  Tags Vector: 50 dimensiones (dense, top-50 tags)")
print(f"  Total features por película: 69 dimensiones")
print()

spark.stop()
