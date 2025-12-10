#!/usr/bin/env python3
"""
Build Content Features - MovieLens
===================================

Genera vectores de features de contenido para cada película:
1. Genres Vector (one-hot encoding de géneros)
2. Tags Vector (genome scores - vector denso de relevancia top-50 tags)

Output: /data/content_features/movies_features (Parquet)

Schema final:
- movieId: int
- title: string
- genres: string
- genres_array: array<string>
- genres_vec: vector (sparse) - one-hot de géneros
- tags_vec: vector (dense) - top-50 genome tags
- n_genres: int
- n_tags: int
- avg_tag_relevance: double
"""

import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, ArrayType, DoubleType
from pyspark.ml.linalg import Vectors, VectorUDT
import numpy as np
from pyspark.ml.feature import StringIndexer, OneHotEncoder
import numpy as np


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

HDFS_BASE = "hdfs://namenode:9000"
INPUT_PATH = f"{HDFS_BASE}/data/movielens_parquet"
OUTPUT_PATH = f"{HDFS_BASE}/data/content_features"

# Configuración de features
TOP_N_TAGS = 50  # Top N tags más relevantes del genome
MIN_RELEVANCE = 0.3  # Umbral mínimo de relevance para considerar un tag
SHUFFLE_PARTITIONS = 200

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def print_section(title):
    """Imprime sección visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def show_stats(df, name, n=5):
    """Muestra estadísticas de un DataFrame"""
    print(f"📊 {name}:")
    print(f"   Registros: {df.count():,}")
    print(f"   Columnas: {len(df.columns)}")
    print(f"\n   Muestra ({n} filas):")
    df.show(n, truncate=False)
    print("-" * 70)

# ============================================================================
# PASO 1: CARGAR DATOS
# ============================================================================

def load_data(spark):
    """Carga los datos necesarios desde Parquet"""
    print_section("PASO 1: CARGAR DATOS")
    
    print("📥 Cargando movies...")
    movies = spark.read.parquet(f"{INPUT_PATH}/movies")
    print(f"   ✅ {movies.count():,} películas cargadas")
    
    print("\n📥 Cargando genome_tags...")
    genome_tags = spark.read.parquet(f"{INPUT_PATH}/genome_tags")
    print(f"   ✅ {genome_tags.count():,} tags cargados")
    
    print("\n📥 Cargando genome_scores...")
    genome_scores = spark.read.parquet(f"{INPUT_PATH}/genome_scores")
    print(f"   ✅ {genome_scores.count():,} scores cargados")
    
    return movies, genome_tags, genome_scores

# ============================================================================
# PASO 2: IDENTIFICAR TOP TAGS
# ============================================================================

def identify_top_tags(genome_scores, genome_tags, top_n=TOP_N_TAGS):
    """
    Identifica los top N tags más relevantes globalmente.
    
    Estrategia:
    1. Calcular relevancia promedio por tag
    2. Tomar top N tags con mayor relevancia promedio
    3. Esto asegura que seleccionamos los tags más descriptivos
    """
    print_section(f"PASO 2: IDENTIFICAR TOP {top_n} TAGS")
    
    # Calcular relevancia promedio por tagId
    print("🔍 Calculando relevancia promedio por tag...")
    tag_stats = (genome_scores
                 .groupBy("tagId")
                 .agg(
                     F.avg("relevance").alias("avg_relevance"),
                     F.stddev("relevance").alias("std_relevance"),
                     F.count("*").alias("n_movies")
                 ))
    
    # Unir con nombres de tags
    tag_stats = tag_stats.join(genome_tags, "tagId")
    
    # Ordenar por relevancia promedio y tomar top N
    top_tags = (tag_stats
                .orderBy(F.desc("avg_relevance"))
                .limit(top_n)
                .select("tagId", "tag", "avg_relevance", "std_relevance", "n_movies"))
    
    print(f"\n📋 Top {top_n} Tags Seleccionados:")
    top_tags.show(20, truncate=False)
    
    # Crear lista de tagIds para usar como filtro
    top_tag_ids = [row.tagId for row in top_tags.collect()]
    print(f"\n✅ Tag IDs seleccionados: {top_tag_ids[:10]}... (total: {len(top_tag_ids)})")
    
    return top_tag_ids, top_tags

# ============================================================================
# PASO 3: GENERAR GENRES VECTORS (ONE-HOT)
# ============================================================================

def build_genres_features(movies, spark):
    """
    Genera one-hot encoding para géneros.
    
    Estrategia:
    1. Explotar genres_array para tener una fila por género
    2. Crear columna de índice único por género
    3. Generar one-hot vector sparse
    """
    print_section("PASO 3: GENERAR GENRES VECTORS (ONE-HOT)")
    
    # Primero, obtener todos los géneros únicos
    print("🔍 Identificando géneros únicos...")
    genres_exploded = movies.select(
        "movieId",
        F.explode("genres_array").alias("genre")
    ).filter(F.col("genre") != "")  # Filtrar géneros vacíos
    
    all_genres = (genres_exploded
                  .select("genre")
                  .distinct()
                  .orderBy("genre")
                  .collect())
    
    genre_list = [row.genre for row in all_genres]
    print(f"   ✅ {len(genre_list)} géneros únicos encontrados")
    print(f"   Géneros: {genre_list}")
    
    # Crear un diccionario de índices para cada género
    genre_to_idx = {genre: idx for idx, genre in enumerate(genre_list)}
    n_genres = len(genre_list)
    
    # Broadcast del diccionario
    genre_to_idx_bc = spark.sparkContext.broadcast(genre_to_idx)
    
    # UDF para crear vector one-hot sparse
    def create_genres_vector(genres_arr):
        """Crea un vector sparse one-hot para los géneros"""
        if not genres_arr or len(genres_arr) == 0:
            return Vectors.sparse(n_genres, {})
        
        genre_idx_map = genre_to_idx_bc.value
        # Usar set para evitar duplicados y ordenar para cumplir requisito de índices crecientes
        indices = sorted({genre_idx_map[g] for g in genres_arr if g in genre_idx_map})
        
        if not indices:
            return Vectors.sparse(n_genres, {})
        
        values = [1.0] * len(indices)
        return Vectors.sparse(n_genres, indices, values)
    
    create_genres_vector_udf = F.udf(create_genres_vector, VectorUDT())
    
    # Aplicar UDF para crear el vector
    print("\n🔧 Generando vectores one-hot...")
    movies_with_genres_vec = movies.withColumn(
        "genres_vec",
        create_genres_vector_udf(F.col("genres_array"))
    )
    
    # Añadir conteo de géneros
    movies_with_genres_vec = movies_with_genres_vec.withColumn(
        "n_genres",
        F.size(F.col("genres_array"))
    )
    
    show_stats(movies_with_genres_vec.select("movieId", "title", "genres", "n_genres", "genres_vec"), 
               "Movies con genres_vec", 3)
    
    return movies_with_genres_vec, genre_list

# ============================================================================
# PASO 4: GENERAR TAGS VECTORS (GENOME DENSE)
# ============================================================================

def build_tags_features(movies_with_genres, genome_scores, top_tag_ids, spark):
    """
    Genera vectores densos de relevancia para top N tags.
    
    Estrategia:
    1. Filtrar genome_scores para solo top tags
    2. Pivotar para tener una columna por tag
    3. Crear vector denso con relevancia normalizada
    """
    print_section(f"PASO 4: GENERAR TAGS VECTORS (TOP {len(top_tag_ids)} TAGS)")
    
    # Broadcast de top_tag_ids para filtrado eficiente
    top_tag_ids_bc = spark.sparkContext.broadcast(set(top_tag_ids))
    
    # Filtrar scores solo para top tags
    print(f"🔍 Filtrando genome_scores para top {len(top_tag_ids)} tags...")
    top_scores = genome_scores.filter(F.col("tagId").isin(top_tag_ids))
    
    print(f"   ✅ {top_scores.count():,} scores filtrados")
    
    # Aplicar umbral de relevancia
    top_scores = top_scores.filter(F.col("relevance") >= MIN_RELEVANCE)
    print(f"   ✅ {top_scores.count():,} scores después de filtrar por relevance >= {MIN_RELEVANCE}")
    
    # Crear un índice ordenado de tags para el vector
    tag_idx_map = {tag_id: idx for idx, tag_id in enumerate(sorted(top_tag_ids))}
    tag_idx_map_bc = spark.sparkContext.broadcast(tag_idx_map)
    n_tags_dim = len(top_tag_ids)
    
    # Agrupar por movieId y crear array de (tagId, relevance)
    print("\n🔧 Agrupando scores por película...")
    movie_tags = (top_scores
                  .groupBy("movieId")
                  .agg(
                      F.collect_list(
                          F.struct("tagId", "relevance")
                      ).alias("tag_scores"),
                      F.count("*").alias("n_tags"),
                      F.avg("relevance").alias("avg_tag_relevance")
                  ))
    
    # UDF para crear vector denso de tags
    def create_tags_vector(tag_scores):
        """Crea un vector denso con relevancia de top tags"""
        if not tag_scores or len(tag_scores) == 0:
            return Vectors.dense([0.0] * n_tags_dim)
        
        tag_idx = tag_idx_map_bc.value
        vector = np.zeros(n_tags_dim)
        
        for score in tag_scores:
            tag_id = score.tagId
            relevance = score.relevance
            
            if tag_id in tag_idx:
                idx = tag_idx[tag_id]
                vector[idx] = float(relevance)
        
        return Vectors.dense(vector.tolist())
    
    create_tags_vector_udf = F.udf(create_tags_vector, VectorUDT())
    
    # Aplicar UDF
    print("🔧 Generando vectores de tags...")
    movie_tags = movie_tags.withColumn(
        "tags_vec",
        create_tags_vector_udf(F.col("tag_scores"))
    ).drop("tag_scores")
    
    show_stats(movie_tags.select("movieId", "n_tags", "avg_tag_relevance", "tags_vec"), 
               "Movie Tags Vectors", 3)
    
    # Join con movies que ya tienen genres_vec
    print("\n🔗 Uniendo con datos de películas...")
    movies_full = movies_with_genres.join(movie_tags, "movieId", "left")
    
    # Llenar nulos para películas sin genome scores
    movies_full = movies_full.fillna({
        "n_tags": 0,
        "avg_tag_relevance": 0.0
    })
    
    # Para películas sin tags_vec, crear vector de ceros
    def zero_vector():
        return Vectors.dense([0.0] * n_tags_dim)
    
    zero_vector_udf = F.udf(zero_vector, VectorUDT())
    
    movies_full = movies_full.withColumn(
        "tags_vec",
        F.when(F.col("tags_vec").isNull(), zero_vector_udf())
          .otherwise(F.col("tags_vec"))
    )
    
    return movies_full

# ============================================================================
# PASO 5: GUARDAR FEATURES
# ============================================================================

def save_features(movies_features, genre_list, top_tags, spark):
    """Guarda las features en HDFS y metadatos"""
    print_section("PASO 5: GUARDAR FEATURES")
    
    # Seleccionar columnas finales
    final_cols = [
        "movieId",
        "title",
        "genres",
        "genres_array",
        "genres_vec",
        "tags_vec",
        "n_genres",
        "n_tags",
        "avg_tag_relevance"
    ]
    
    movies_features_final = movies_features.select(*final_cols)
    
    # Mostrar estadísticas finales
    print("📊 Estadísticas Finales:")
    print(f"   Total películas: {movies_features_final.count():,}")
    
    stats = movies_features_final.select(
        F.avg("n_genres").alias("avg_genres"),
        F.avg("n_tags").alias("avg_tags"),
        F.avg("avg_tag_relevance").alias("avg_relevance")
    ).collect()[0]
    
    print(f"   Promedio géneros por película: {stats.avg_genres:.2f}")
    print(f"   Promedio tags por película: {stats.avg_tags:.2f}")
    print(f"   Relevancia promedio: {stats.avg_relevance:.3f}")
    
    # Distribución de n_tags
    print("\n📈 Distribución de número de tags:")
    movies_features_final.groupBy("n_tags").count().orderBy("n_tags").show(20)
    
    # Guardar features
    output_features = f"{OUTPUT_PATH}/movies_features"
    print(f"\n💾 Guardando features en: {output_features}")
    
    (movies_features_final
     .coalesce(20)  # Reducir número de archivos
     .write
     .mode("overwrite")
     .parquet(output_features, compression="snappy"))
    
    print(f"✅ Features guardadas correctamente")
    
    # Guardar metadatos de géneros
    output_genres_meta = f"{OUTPUT_PATH}/genres_metadata"
    print(f"\n💾 Guardando metadatos de géneros en: {output_genres_meta}")
    
    genres_df = spark.createDataFrame(
        [(i, genre) for i, genre in enumerate(genre_list)],
        ["idx", "genre"]
    )
    
    (genres_df
     .coalesce(1)
     .write
     .mode("overwrite")
     .parquet(output_genres_meta, compression="snappy"))
    
    print(f"✅ Metadatos de géneros guardados")
    
    # Guardar metadatos de tags
    output_tags_meta = f"{OUTPUT_PATH}/tags_metadata"
    print(f"\n💾 Guardando metadatos de tags en: {output_tags_meta}")
    
    (top_tags
     .coalesce(1)
     .write
     .mode("overwrite")
     .parquet(output_tags_meta, compression="snappy"))
    
    print(f"✅ Metadatos de tags guardados")
    
    return movies_features_final

# ============================================================================
# PASO 6: VALIDACIÓN
# ============================================================================

def validate_features(spark):
    """Valida que las features se guardaron correctamente"""
    print_section("PASO 6: VALIDACIÓN")
    
    output_features = f"{OUTPUT_PATH}/movies_features"
    
    print(f"🔍 Verificando features en: {output_features}")
    
    features = spark.read.parquet(output_features)
    
    print(f"   ✅ {features.count():,} películas con features")
    print(f"   ✅ Columnas: {features.columns}")
    
    features.printSchema()
    
    print("\n📋 Muestra de features:")
    features.select("movieId", "title", "n_genres", "n_tags", "avg_tag_relevance").show(10, truncate=False)
    
    # Verificar que no hay nulos críticos
    null_check = features.select(
        F.sum(F.when(F.col("movieId").isNull(), 1).otherwise(0)).alias("null_movieId"),
        F.sum(F.when(F.col("genres_vec").isNull(), 1).otherwise(0)).alias("null_genres_vec"),
        F.sum(F.when(F.col("tags_vec").isNull(), 1).otherwise(0)).alias("null_tags_vec")
    ).collect()[0]
    
    print("\n🔍 Verificación de nulos:")
    print(f"   movieId nulos: {null_check.null_movieId}")
    print(f"   genres_vec nulos: {null_check.null_genres_vec}")
    print(f"   tags_vec nulos: {null_check.null_tags_vec}")
    
    if null_check.null_movieId == 0 and null_check.null_genres_vec == 0 and null_check.null_tags_vec == 0:
        print("\n✅ VALIDACIÓN EXITOSA - NO HAY NULOS CRÍTICOS")
        return True
    else:
        print("\n❌ VALIDACIÓN FALLÓ - HAY NULOS CRÍTICOS")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Punto de entrada principal"""
    
    print("\n" + "="*70)
    print("  BUILD CONTENT FEATURES - MOVIELENS")
    print("="*70)
    print(f"\nInicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input:  {INPUT_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"\nConfiguración:")
    print(f"  - Top Tags: {TOP_N_TAGS}")
    print(f"  - Min Relevance: {MIN_RELEVANCE}")
    print()
    
    # Crear Spark Session
    spark = (SparkSession.builder
             .appName("Build_Content_Features")
             .config("spark.sql.shuffle.partitions", SHUFFLE_PARTITIONS)
             .config("spark.sql.adaptive.enabled", "true")
             .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
             .getOrCreate())
    
    try:
        # Paso 1: Cargar datos
        movies, genome_tags, genome_scores = load_data(spark)
        
        # Paso 2: Identificar top tags
        top_tag_ids, top_tags = identify_top_tags(genome_scores, genome_tags, TOP_N_TAGS)
        
        # Paso 3: Generar genres features
        movies_with_genres, genre_list = build_genres_features(movies, spark)
        
        # Paso 4: Generar tags features
        movies_features = build_tags_features(movies_with_genres, genome_scores, top_tag_ids, spark)
        
        # Paso 5: Guardar features
        movies_features_final = save_features(movies_features, genre_list, top_tags, spark)
        
        # Paso 6: Validar
        if validate_features(spark):
            print_section("✅ BUILD FEATURES COMPLETADO EXITOSAMENTE")
            print(f"📁 Features disponibles en: {OUTPUT_PATH}/movies_features")
            print(f"📁 Metadatos en: {OUTPUT_PATH}/genres_metadata, {OUTPUT_PATH}/tags_metadata")
            print()
            return_code = 0
        else:
            print_section("❌ BUILD FEATURES FALLÓ EN VALIDACIÓN")
            return_code = 1
        
    except Exception as e:
        print(f"\n❌ ERROR EN BUILD FEATURES: {str(e)}")
        import traceback
        traceback.print_exc()
        return_code = 1
    
    finally:
        spark.stop()
        print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())
