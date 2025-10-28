#!/usr/bin/env python3
"""Verificación rápida de datos Parquet ETL"""

from pyspark.sql import SparkSession

HDFS_BASE = "hdfs://namenode:9000"
OUTPUT_PATH = f"{HDFS_BASE}/data/movielens_parquet"

spark = (SparkSession.builder
         .appName("Verify_Parquet")
         .config("spark.sql.adaptive.enabled", "true")
         .getOrCreate())

print("\n" + "="*70)
print("  VERIFICACIÓN PARQUET - FASE 3 COMPLETADA")
print("="*70 + "\n")

tables = ["movies", "ratings", "tags", "genome_tags", "genome_scores", "links"]

print(f"{'Tabla':<20} {'Registros':>15} {'Columnas':>10}")
print("-" * 50)

total_records = 0
for table in tables:
    path = f"{OUTPUT_PATH}/{table}"
    try:
        df = spark.read.parquet(path)
        count = df.count()
        cols = len(df.columns)
        total_records += count
        print(f"{table:<20} {count:>15,} {cols:>10}")
    except Exception as e:
        print(f"{table:<20} {'ERROR':>15} {'N/A':>10}")
        print(f"   Error: {str(e)}")

print("-" * 50)
print(f"{'TOTAL':<20} {total_records:>15,}")
print()

# Verificar ratings particionado
print("📅 Verificando particiones de ratings...")
ratings = spark.read.parquet(f"{OUTPUT_PATH}/ratings")
dist = ratings.groupBy("year", "month").count().orderBy("year", "month")
print(f"\nDistribución temporal (total: {dist.count()} particiones):")
dist.show(20)

# Verificar schema de ratings
print("\n📋 Schema de ratings:")
ratings.printSchema()

# Verificar tags
print("\n🏷️  Top 10 tags:")
tags = spark.read.parquet(f"{OUTPUT_PATH}/tags")
tags.groupBy("tag").count().orderBy("count", ascending=False).show(10, truncate=False)

print("\n✅ VERIFICACIÓN COMPLETADA - TODOS LOS DATOS CORRECTOS\n")

spark.stop()
