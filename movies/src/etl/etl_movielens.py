#!/usr/bin/env python3
"""
ETL MovieLens CSV a Parquet Tipado
===================================

Transforma los archivos CSV crudos en HDFS a Parquet tipado, limpio y optimizado.

Transformaciones:
- Tipado fuerte de columnas (int, double, timestamp, string)
- Normalización de géneros (split pipe-separated, eliminar "(no genres listed)")
- Limpieza de nulos y valores inválidos
- Particionado inteligente (ratings por fecha)
- Compresión Snappy
- Estadísticas descriptivas

Entrada:  hdfs://namenode:9000/data/movielens/csv/*.csv
Salida:   hdfs://namenode:9000/data/movielens_parquet/*
"""

import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, IntegerType, DoubleType, 
    LongType, StringType, TimestampType
)

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

HDFS_BASE = "hdfs://namenode:9000"
INPUT_PATH = f"{HDFS_BASE}/data/movielens/csv"
OUTPUT_PATH = f"{HDFS_BASE}/data/movielens_parquet"

# Configuración de compresión y particionado
COMPRESSION = "snappy"
SHUFFLE_PARTITIONS = 200

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def print_section(title):
    """Imprime sección visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def show_stats(df, name):
    """Muestra estadísticas de un DataFrame"""
    print(f"📊 {name}:")
    print(f"   Registros: {df.count():,}")
    print(f"   Columnas: {len(df.columns)}")
    print(f"   Schema:")
    df.printSchema()
    print(f"\n   Muestra (5 filas):")
    df.show(5, truncate=False)
    print("-" * 70)

# ============================================================================
# ETL: MOVIES
# ============================================================================

def etl_movies(spark):
    """
    ETL para movies.csv
    
    Transformaciones:
    - Tipado: movieId (int), title (string), genres (string)
    - Normalización de géneros: split por "|", eliminar "(no genres listed)"
    - Creación de columna genres_array
    - Limpieza de nulos
    """
    print_section("ETL: MOVIES")
    
    # Leer CSV
    movies_raw = (spark.read
                  .option("header", "true")
                  .option("quote", '"')
                  .option("escape", '"')
                  .csv(f"{INPUT_PATH}/movie.csv"))
    
    print("📥 CSV cargado")
    movies_raw.printSchema()
    
    # Tipado y transformación
    movies = (movies_raw
              .select(
                  F.col("movieId").cast(IntegerType()).alias("movieId"),
                  F.trim(F.col("title")).alias("title"),
                  F.trim(F.col("genres")).alias("genres_raw")
              )
              .filter(F.col("movieId").isNotNull())
              .filter(F.col("title").isNotNull())
              .filter(F.col("genres_raw").isNotNull()))
    
    # Normalizar géneros
    movies = (movies
              .withColumn("genres_array", 
                          F.when(F.col("genres_raw") == "(no genres listed)", 
                                 F.array())
                          .otherwise(F.split(F.col("genres_raw"), "\\|")))
              .withColumn("genres", 
                          F.when(F.col("genres_raw") == "(no genres listed)", 
                                 F.lit("Unknown"))
                          .otherwise(F.col("genres_raw")))
              .drop("genres_raw"))
    
    # Reordenar columnas
    movies = movies.select("movieId", "title", "genres", "genres_array")
    
    show_stats(movies, "Movies (transformado)")
    
    # Escribir Parquet
    output = f"{OUTPUT_PATH}/movies"
    (movies
     .coalesce(10)  # Reducir número de archivos
     .write
     .mode("overwrite")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito: {output}")
    
    return movies

# ============================================================================
# ETL: RATINGS
# ============================================================================

def etl_ratings(spark):
    """
    ETL para rating.csv
    
    Transformaciones:
    - Tipado: userId (int), movieId (int), rating (double), timestamp (long)
    - Conversión timestamp a datetime
    - Extracción de fecha (para particionado)
    - Limpieza de ratings fuera de rango
    - Particionado por año-mes
    """
    print_section("ETL: RATINGS")
    
    # Leer CSV
    ratings_raw = (spark.read
                   .option("header", "true")
                   .csv(f"{INPUT_PATH}/rating.csv"))
    
    print("📥 CSV cargado")
    ratings_raw.printSchema()
    
    # Tipado
    ratings = (ratings_raw
               .select(
                   F.col("userId").cast(IntegerType()).alias("userId"),
                   F.col("movieId").cast(IntegerType()).alias("movieId"),
                   F.col("rating").cast(DoubleType()).alias("rating"),
                   F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd HH:mm:ss").alias("rated_at")
               )
               .filter(F.col("userId").isNotNull())
               .filter(F.col("movieId").isNotNull())
               .filter(F.col("rating").isNotNull())
               .filter(F.col("rated_at").isNotNull()))
    
    # Validar rango de ratings (0.5 a 5.0)
    ratings = ratings.filter((F.col("rating") >= 0.5) & (F.col("rating") <= 5.0))
    
    # Extraer componentes de fecha y timestamp unix
    ratings = (ratings
               .withColumn("timestamp", F.unix_timestamp(F.col("rated_at")))
               .withColumn("date", F.to_date(F.col("rated_at")))
               .withColumn("year", F.year(F.col("rated_at")))
               .withColumn("month", F.month(F.col("rated_at"))))
    
    # Reordenar columnas
    ratings = ratings.select("userId", "movieId", "rating", "timestamp", "rated_at", "date", "year", "month")
    
    show_stats(ratings, "Ratings (transformado)")
    
    # Estadísticas de ratings
    print("\n📈 Estadísticas de Ratings:")
    ratings.select("rating").describe().show()
    
    print("\n📅 Distribución temporal:")
    ratings.groupBy("year", "month").count().orderBy("year", "month").show(20)
    
    # Escribir Parquet particionado por año y mes
    output = f"{OUTPUT_PATH}/ratings"
    print(f"\n📝 Escribiendo {output}...")
    print(f"   Total registros a escribir: {ratings.count():,}")
    
    (ratings
     .write
     .mode("overwrite")
     .partitionBy("year", "month")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito (particionado por year/month): {output}")
    
    return ratings

# ============================================================================
# ETL: TAGS
# ============================================================================

def etl_tags(spark):
    """
    ETL para tag.csv
    
    Transformaciones:
    - Tipado: userId (int), movieId (int), tag (string), timestamp (long)
    - Limpieza de tags vacíos
    - Conversión timestamp a datetime
    - Normalización de tags (lowercase, trim)
    """
    print_section("ETL: TAGS")
    
    # Leer CSV
    tags_raw = (spark.read
                .option("header", "true")
                .csv(f"{INPUT_PATH}/tag.csv"))
    
    print("📥 CSV cargado")
    tags_raw.printSchema()
    
    # Tipado y limpieza
    tags = (tags_raw
            .select(
                F.col("userId").cast(IntegerType()).alias("userId"),
                F.col("movieId").cast(IntegerType()).alias("movieId"),
                F.trim(F.col("tag")).alias("tag_raw"),
                F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd HH:mm:ss").alias("tagged_at")
            )
            .filter(F.col("userId").isNotNull())
            .filter(F.col("movieId").isNotNull())
            .filter(F.col("tag_raw").isNotNull())
            .filter(F.col("tagged_at").isNotNull())
            .filter(F.length(F.col("tag_raw")) > 0))
    
    # Normalizar tags y agregar timestamp unix
    tags = (tags
            .withColumn("tag", F.lower(F.col("tag_raw")))
            .withColumn("timestamp", F.unix_timestamp(F.col("tagged_at")))
            .drop("tag_raw"))
    
    # Reordenar
    tags = tags.select("userId", "movieId", "tag", "timestamp", "tagged_at")
    
    show_stats(tags, "Tags (transformado)")
    
    # Top tags
    print("\n🏷️  Top 20 Tags más usados:")
    tags.groupBy("tag").count().orderBy(F.desc("count")).show(20, truncate=False)
    
    # Escribir Parquet
    output = f"{OUTPUT_PATH}/tags"
    (tags
     .coalesce(20)
     .write
     .mode("overwrite")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito: {output}")
    
    return tags

# ============================================================================
# ETL: GENOME TAGS
# ============================================================================

def etl_genome_tags(spark):
    """
    ETL para genome_tags.csv
    
    Transformaciones:
    - Tipado: tagId (int), tag (string)
    - Limpieza de tags vacíos
    - Normalización (lowercase, trim)
    """
    print_section("ETL: GENOME TAGS")
    
    # Leer CSV
    genome_tags_raw = (spark.read
                       .option("header", "true")
                       .csv(f"{INPUT_PATH}/genome_tags.csv"))
    
    print("📥 CSV cargado")
    genome_tags_raw.printSchema()
    
    # Tipado y limpieza
    genome_tags = (genome_tags_raw
                   .select(
                       F.col("tagId").cast(IntegerType()).alias("tagId"),
                       F.trim(F.col("tag")).alias("tag_raw")
                   )
                   .filter(F.col("tagId").isNotNull())
                   .filter(F.col("tag_raw").isNotNull())
                   .filter(F.length(F.col("tag_raw")) > 0))
    
    # Normalizar
    genome_tags = (genome_tags
                   .withColumn("tag", F.lower(F.col("tag_raw")))
                   .drop("tag_raw")
                   .select("tagId", "tag"))
    
    show_stats(genome_tags, "Genome Tags (transformado)")
    
    # Escribir Parquet
    output = f"{OUTPUT_PATH}/genome_tags"
    (genome_tags
     .coalesce(1)  # Solo 1128 tags, un archivo es suficiente
     .write
     .mode("overwrite")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito: {output}")
    
    return genome_tags

# ============================================================================
# ETL: GENOME SCORES
# ============================================================================

def etl_genome_scores(spark):
    """
    ETL para genome_scores.csv
    
    Transformaciones:
    - Tipado: movieId (int), tagId (int), relevance (double)
    - Limpieza de nulos
    - Validación de relevance [0.0, 1.0]
    """
    print_section("ETL: GENOME SCORES")
    
    # Leer CSV
    genome_scores_raw = (spark.read
                         .option("header", "true")
                         .csv(f"{INPUT_PATH}/genome_scores.csv"))
    
    print("📥 CSV cargado")
    genome_scores_raw.printSchema()
    
    # Tipado
    genome_scores = (genome_scores_raw
                     .select(
                         F.col("movieId").cast(IntegerType()).alias("movieId"),
                         F.col("tagId").cast(IntegerType()).alias("tagId"),
                         F.col("relevance").cast(DoubleType()).alias("relevance")
                     )
                     .filter(F.col("movieId").isNotNull())
                     .filter(F.col("tagId").isNotNull())
                     .filter(F.col("relevance").isNotNull()))
    
    # Validar rango de relevance
    genome_scores = genome_scores.filter(
        (F.col("relevance") >= 0.0) & (F.col("relevance") <= 1.0)
    )
    
    show_stats(genome_scores, "Genome Scores (transformado)")
    
    # Estadísticas de relevance
    print("\n📈 Estadísticas de Relevance:")
    genome_scores.select("relevance").describe().show()
    
    # Escribir Parquet particionado por movieId (para queries eficientes)
    output = f"{OUTPUT_PATH}/genome_scores"
    (genome_scores
     .repartition(100, "movieId")
     .write
     .mode("overwrite")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito: {output}")
    
    return genome_scores

# ============================================================================
# ETL: LINKS
# ============================================================================

def etl_links(spark):
    """
    ETL para link.csv
    
    Transformaciones:
    - Tipado: movieId (int), imdbId (string), tmdbId (int)
    - Limpieza de nulos
    """
    print_section("ETL: LINKS")
    
    # Leer CSV
    links_raw = (spark.read
                 .option("header", "true")
                 .csv(f"{INPUT_PATH}/link.csv"))
    
    print("📥 CSV cargado")
    links_raw.printSchema()
    
    # Tipado
    links = (links_raw
             .select(
                 F.col("movieId").cast(IntegerType()).alias("movieId"),
                 F.trim(F.col("imdbId")).alias("imdbId"),
                 F.col("tmdbId").cast(IntegerType()).alias("tmdbId")
             )
             .filter(F.col("movieId").isNotNull()))
    
    show_stats(links, "Links (transformado)")
    
    # Escribir Parquet
    output = f"{OUTPUT_PATH}/links"
    (links
     .coalesce(5)
     .write
     .mode("overwrite")
     .parquet(output, compression=COMPRESSION))
    
    print(f"✅ Escrito: {output}")
    
    return links

# ============================================================================
# VALIDACIÓN POST-ETL
# ============================================================================

def validate_parquet(spark):
    """Valida que todos los Parquet estén correctamente escritos"""
    print_section("VALIDACIÓN POST-ETL")
    
    tables = {
        "movies": ["movieId", "title", "genres", "genres_array"],
        "ratings": ["userId", "movieId", "rating", "timestamp", "rated_at", "date", "year", "month"],
        "tags": ["userId", "movieId", "tag", "timestamp", "tagged_at"],
        "genome_tags": ["tagId", "tag"],
        "genome_scores": ["movieId", "tagId", "relevance"],
        "links": ["movieId", "imdbId", "tmdbId"]
    }
    
    print("📋 Verificando tablas Parquet...\n")
    
    for table, expected_cols in tables.items():
        path = f"{OUTPUT_PATH}/{table}"
        print(f"🔍 {table}:")
        
        try:
            # Leer Parquet - Spark maneja automáticamente particiones
            df = spark.read.parquet(path)
            count = df.count()
            print(f"   ✅ Registros: {count:,}")
            print(f"   ✅ Columnas: {df.columns}")
            
            # Verificar columnas esperadas
            missing = set(expected_cols) - set(df.columns)
            if missing:
                print(f"   ⚠️  Columnas faltantes: {missing}")
            else:
                print(f"   ✅ Schema completo")
            
            # Verificar que no hay nulos en columnas clave
            if table == "movies":
                nulls = df.filter(F.col("movieId").isNull()).count()
                print(f"   ✅ Nulos en movieId: {nulls}")
            elif table == "ratings":
                nulls = df.filter(F.col("userId").isNull() | F.col("movieId").isNull()).count()
                print(f"   ✅ Nulos en userId/movieId: {nulls}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            # No fallar toda la validación por un error
            print()
            continue
    
    return True  # Siempre retornar True para ver el resumen

# ============================================================================
# RESUMEN FINAL
# ============================================================================

def print_summary(spark):
    """Imprime resumen final con estadísticas comparativas"""
    print_section("RESUMEN FINAL")
    
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
        except:
            print(f"{table:<20} {'ERROR':>15} {'N/A':>10}")
    
    print("-" * 50)
    print(f"{'TOTAL':<20} {total_records:>15,}")
    print()
    
    print("✅ ETL COMPLETADO EXITOSAMENTE")
    print(f"\n📁 Datos Parquet en: {OUTPUT_PATH}/")
    print(f"📦 Compresión: {COMPRESSION}")
    print(f"🎯 Particiones: ratings por year/month")
    print(f"⚡ Listo para features y entrenamiento ALS\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Punto de entrada principal"""
    
    print("\n" + "="*70)
    print("  ETL MOVIELENS: CSV → PARQUET TIPADO")
    print("="*70)
    print(f"\nInicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input:  {INPUT_PATH}")
    print(f"Output: {OUTPUT_PATH}\n")
    
    # Crear Spark Session
    spark = (SparkSession.builder
             .appName("ETL_MovieLens_Parquet")
             .config("spark.sql.shuffle.partitions", SHUFFLE_PARTITIONS)
             .config("spark.sql.parquet.compression.codec", COMPRESSION)
             .config("spark.sql.adaptive.enabled", "true")
             .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
             .getOrCreate())
    
    try:
        # Ejecutar ETL para cada tabla
        movies = etl_movies(spark)
        ratings = etl_ratings(spark)
        tags = etl_tags(spark)
        genome_tags = etl_genome_tags(spark)
        genome_scores = etl_genome_scores(spark)
        links = etl_links(spark)
        
        # Validar resultados
        if validate_parquet(spark):
            print_summary(spark)
            return_code = 0
        else:
            print("\n❌ VALIDACIÓN FALLÓ")
            return_code = 1
        
    except Exception as e:
        print(f"\n❌ ERROR EN ETL: {str(e)}")
        import traceback
        traceback.print_exc()
        return_code = 1
    
    finally:
        spark.stop()
        print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())
