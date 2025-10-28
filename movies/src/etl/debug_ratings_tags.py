#!/usr/bin/env python3
"""Script de debug para ratings y tags ETL"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, DoubleType, LongType, TimestampType

HDFS_BASE = "hdfs://namenode:9000"
INPUT_PATH = f"{HDFS_BASE}/data/movielens/csv"

spark = (SparkSession.builder
         .appName("Debug_Ratings_Tags")
         .config("spark.sql.shuffle.partitions", "200")
         .getOrCreate())

print("\n" + "="*70)
print("DEBUG: RATINGS")
print("="*70)

# Leer CSV rating
ratings_raw = spark.read.option("header", "true").csv(f"{INPUT_PATH}/rating.csv")
print(f"📊 Registros raw: {ratings_raw.count():,}")
ratings_raw.printSchema()
ratings_raw.show(5)

# Tipado paso a paso
print("\n🔧 Tipando...")
ratings_typed = ratings_raw.select(
    F.col("userId").cast(IntegerType()).alias("userId"),
    F.col("movieId").cast(IntegerType()).alias("movieId"),
    F.col("rating").cast(DoubleType()).alias("rating"),
    F.col("timestamp").cast(LongType()).alias("timestamp")
)
print(f"📊 Registros después de tipado: {ratings_typed.count():,}")
ratings_typed.show(5)

# Filtros
print("\n🔧 Aplicando filtros...")
ratings_filtered = ratings_typed.filter(
    F.col("userId").isNotNull() &
    F.col("movieId").isNotNull() &
    F.col("rating").isNotNull() &
    F.col("timestamp").isNotNull()
)
print(f"📊 Registros después de filtrar nulos: {ratings_filtered.count():,}")

ratings_filtered = ratings_filtered.filter(
    (F.col("rating") >= 0.5) & (F.col("rating") <= 5.0)
)
print(f"📊 Registros después de validar rango: {ratings_filtered.count():,}")

#Conversión timestamp
print("\n🔧 Convirtiendo timestamp...")
ratings_final = (ratings_filtered
                 .withColumn("rated_at", F.from_unixtime(F.col("timestamp")).cast(TimestampType()))
                 .withColumn("date", F.to_date(F.col("rated_at")))
                 .withColumn("year", F.year(F.col("rated_at")))
                 .withColumn("month", F.month(F.col("rated_at"))))

print(f"📊 Registros finales: {ratings_final.count():,}")
ratings_final.printSchema()
ratings_final.show(10)

# Distribución temporal
print("\n📅 Distribución temporal:")
ratings_final.groupBy("year", "month").count().orderBy("year", "month").show(50)

print("\n" + "="*70)
print("DEBUG: TAGS")
print("="*70)

# Leer CSV tags
tags_raw = spark.read.option("header", "true").csv(f"{INPUT_PATH}/tag.csv")
print(f"📊 Registros raw: {tags_raw.count():,}")
tags_raw.printSchema()
tags_raw.show(5)

# Tipado
print("\n🔧 Tipando...")
tags_typed = tags_raw.select(
    F.col("userId").cast(IntegerType()).alias("userId"),
    F.col("movieId").cast(IntegerType()).alias("movieId"),
    F.trim(F.col("tag")).alias("tag_raw"),
    F.col("timestamp").cast(LongType()).alias("timestamp")
)
print(f"📊 Registros después de tipado: {tags_typed.count():,}")
tags_typed.show(5)

# Filtros
print("\n🔧 Aplicando filtros...")
tags_filtered = tags_typed.filter(
    F.col("userId").isNotNull() &
    F.col("movieId").isNotNull() &
    F.col("tag_raw").isNotNull() &
    F.col("timestamp").isNotNull() &
    (F.length(F.col("tag_raw")) > 0)
)
print(f"📊 Registros después de filtros: {tags_filtered.count():,}")
tags_filtered.show(10)

spark.stop()
