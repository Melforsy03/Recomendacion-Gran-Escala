#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 5: Entrenamiento de Modelo ALS (Collaborative Filtering)
==============================================================

Entrena un modelo de factorización matricial usando ALS (Alternating Least Squares)
sobre los ratings explícitos de MovieLens 20M.

Objetivos:
- Entrenar modelo ALS con hiperparámetros optimizados
- Generar factores latentes de usuarios e items
- Evaluar RMSE en test set
- Generar recomendaciones top-10 para todos los usuarios
- Guardar modelo y outputs en HDFS

Configuración:
- rank: 64 (dimensiones de factores latentes)
- regParam: 0.08 (regularización L2)
- maxIter: 12 (iteraciones de entrenamiento)
- coldStartStrategy: 'drop' (eliminar predicciones con NaN)
- nonnegative: True (factores no negativos)

Inputs:
- /data/movielens_parquet/ratings (20M ratings particionados por year/month)

Outputs:
- /models/als/model (modelo entrenado)
- /models/als/user_factors (factores latentes de usuarios)
- /models/als/item_factors (factores latentes de items)
- /outputs/als/rec_users_top10 (recomendaciones top-10 por usuario)
- /outputs/als/evaluation_metrics (RMSE, MAE, coverage)
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import time
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Hiperparámetros ALS (optimizados para entrenamiento rápido)
RANK = 10                     # Dimensiones de factores latentes (reducido de 64)
REG_PARAM = 0.1               # Regularización L2
MAX_ITER = 5                  # Iteraciones de entrenamiento (reducido de 12)
COLD_START = 'drop'           # Estrategia para cold-start (drop NaN)
NONNEGATIVE = True            # Factores no negativos

# Train/Test Split
TEST_RATIO = 0.3              # 30% test, 70% train (menos datos de entrenamiento)
RANDOM_SEED = 42
SAMPLE_FRACTION = 0.05        # Usar solo 5% de los datos (1M ratings aprox)

# Recomendaciones
TOP_N = 10                    # Top-10 recomendaciones por usuario

# Paths HDFS
RATINGS_PATH = "hdfs://namenode:9000/data/movielens_parquet/ratings"
MODEL_PATH = "hdfs://namenode:9000/models/als/model"
USER_FACTORS_PATH = "hdfs://namenode:9000/models/als/user_factors"
ITEM_FACTORS_PATH = "hdfs://namenode:9000/models/als/item_factors"
RECOMMENDATIONS_PATH = "hdfs://namenode:9000/outputs/als/rec_users_top10"
METRICS_PATH = "hdfs://namenode:9000/outputs/als/evaluation_metrics"

# ============================================================================
# FUNCIONES
# ============================================================================

def load_ratings(spark):
    """
    Carga ratings desde Parquet particionado.
    
    Returns:
        DataFrame con columnas: userId, movieId, rating, timestamp
    """
    print("📥 PASO 1: Cargando ratings desde HDFS...")
    
    ratings = spark.read.parquet(RATINGS_PATH)
    
    # Seleccionar solo columnas necesarias para ALS
    ratings_clean = ratings.select("userId", "movieId", "rating")
    
    # MUESTREO: Usar solo SAMPLE_FRACTION de los datos para entrenamiento rápido
    print(f"  🎲 Aplicando muestreo: {SAMPLE_FRACTION*100:.0f}% de los datos")
    ratings_sampled = ratings_clean.sample(withReplacement=False, fraction=SAMPLE_FRACTION, seed=RANDOM_SEED)
    
    total_ratings = ratings_sampled.count()
    n_users = ratings_sampled.select("userId").distinct().count()
    n_movies = ratings_sampled.select("movieId").distinct().count()
    
    print(f"  ✅ {total_ratings:,} ratings cargados (sample)")
    print(f"  ✅ {n_users:,} usuarios únicos")
    print(f"  ✅ {n_movies:,} películas únicas")
    print(f"  📊 Sparsity: {100 * (1 - total_ratings / (n_users * n_movies)):.2f}%")
    
    return ratings_sampled


def split_train_test(ratings, test_ratio=0.3, seed=42):
    """
    Divide ratings en train/test de forma aleatoria.
    
    Args:
        ratings: DataFrame de ratings
        test_ratio: Proporción para test (default 0.3)
        seed: Semilla para reproducibilidad
        
    Returns:
        (train_df, test_df)
    """
    print(f"\n📊 PASO 2: Dividiendo datos (train {100*(1-test_ratio):.0f}% / test {100*test_ratio:.0f}%)...")
    
    train, test = ratings.randomSplit([1.0 - test_ratio, test_ratio], seed=seed)
    
    # Cache para evitar recálculo
    train.cache()
    test.cache()
    
    n_train = train.count()
    n_test = test.count()
    
    print(f"  ✅ Train: {n_train:,} ratings ({100*n_train/(n_train+n_test):.1f}%)")
    print(f"  ✅ Test: {n_test:,} ratings ({100*n_test/(n_train+n_test):.1f}%)")
    
    return train, test


def train_als_model(train_df, rank=10, reg_param=0.1, max_iter=5, 
                    cold_start='drop', nonnegative=True):
    """
    Entrena modelo ALS con hiperparámetros especificados.
    
    Args:
        train_df: DataFrame de entrenamiento
        rank: Dimensiones de factores latentes
        reg_param: Parámetro de regularización
        max_iter: Número de iteraciones
        cold_start: Estrategia para cold-start ('drop' o 'nan')
        nonnegative: Si True, factores no negativos
        
    Returns:
        Modelo ALS entrenado
    """
    print(f"\n🔧 PASO 3: Entrenando modelo ALS...")
    print(f"  Hiperparámetros:")
    print(f"    - rank: {rank}")
    print(f"    - regParam: {reg_param}")
    print(f"    - maxIter: {max_iter}")
    print(f"    - coldStartStrategy: {cold_start}")
    print(f"    - nonnegative: {nonnegative}")
    
    start_time = time.time()
    
    # Configurar ALS
    als = ALS(
        rank=rank,
        maxIter=max_iter,
        regParam=reg_param,
        userCol="userId",
        itemCol="movieId",
        ratingCol="rating",
        coldStartStrategy=cold_start,
        nonnegative=nonnegative,
        seed=RANDOM_SEED,
        checkpointInterval=10  # Checkpoint cada 10 iteraciones
    )
    
    # Entrenar modelo
    print("  ⏳ Iniciando entrenamiento...")
    model = als.fit(train_df)
    
    elapsed_time = time.time() - start_time
    print(f"  ✅ Modelo entrenado en {elapsed_time:.1f} segundos ({elapsed_time/60:.1f} min)")
    
    return model


def evaluate_model(model, test_df):
    """
    Evalúa el modelo en test set calculando RMSE y MAE.
    
    Args:
        model: Modelo ALS entrenado
        test_df: DataFrame de test
        
    Returns:
        dict con métricas: {'rmse': float, 'mae': float}
    """
    print(f"\n📈 PASO 4: Evaluando modelo en test set...")
    
    # Generar predicciones
    predictions = model.transform(test_df)
    
    # Calcular RMSE
    evaluator_rmse = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction"
    )
    rmse = evaluator_rmse.evaluate(predictions)
    
    # Calcular MAE
    evaluator_mae = RegressionEvaluator(
        metricName="mae",
        labelCol="rating",
        predictionCol="prediction"
    )
    mae = evaluator_mae.evaluate(predictions)
    
    # Verificar estabilidad (no NaN)
    n_predictions = predictions.count()
    n_valid = predictions.filter(~F.isnan(F.col("prediction"))).count()
    coverage = 100 * n_valid / n_predictions if n_predictions > 0 else 0
    
    print(f"  ✅ RMSE: {rmse:.4f}")
    print(f"  ✅ MAE: {mae:.4f}")
    print(f"  ✅ Predicciones válidas: {n_valid:,} / {n_predictions:,} ({coverage:.1f}%)")
    
    # Verificar estabilidad
    if rmse != rmse:  # Check for NaN
        print("  ❌ ERROR: RMSE es NaN - modelo inestable")
        return None
    else:
        print("  ✅ Modelo estable (sin NaN)")
    
    return {
        'rmse': rmse,
        'mae': mae,
        'n_predictions': n_predictions,
        'n_valid': n_valid,
        'coverage': coverage
    }


def save_model(model, spark):
    """
    Guarda modelo completo y factores latentes en HDFS.
    
    Args:
        model: Modelo ALS entrenado
        spark: SparkSession
    """
    print(f"\n💾 PASO 5: Guardando modelo y factores...")
    
    # Guardar modelo completo
    print(f"  📁 Guardando modelo en {MODEL_PATH}")
    model.write().overwrite().save(MODEL_PATH)
    
    # Guardar factores de usuarios
    print(f"  📁 Guardando user factors en {USER_FACTORS_PATH}")
    user_factors = model.userFactors
    user_factors.write.mode("overwrite").parquet(USER_FACTORS_PATH)
    
    n_users = user_factors.count()
    print(f"    ✅ {n_users:,} usuarios con factores de {RANK} dimensiones")
    
    # Guardar factores de items
    print(f"  📁 Guardando item factors en {ITEM_FACTORS_PATH}")
    item_factors = model.itemFactors
    item_factors.write.mode("overwrite").parquet(ITEM_FACTORS_PATH)
    
    n_items = item_factors.count()
    print(f"    ✅ {n_items:,} películas con factores de {RANK} dimensiones")
    
    print("  ✅ Modelo y factores guardados exitosamente")


def generate_recommendations(model, spark, top_n=10):
    """
    Genera recomendaciones top-N para todos los usuarios.
    
    Args:
        model: Modelo ALS entrenado
        spark: SparkSession
        top_n: Número de recomendaciones por usuario
        
    Returns:
        DataFrame con recomendaciones
    """
    print(f"\n🎯 PASO 6: Generando recomendaciones top-{top_n} para usuarios...")
    
    start_time = time.time()
    
    # Generar top-N recomendaciones para todos los usuarios
    user_recs = model.recommendForAllUsers(top_n)
    
    # Explode recommendations array para tener una fila por recomendación
    user_recs_exploded = user_recs.select(
        "userId",
        F.posexplode("recommendations").alias("rank", "recommendation")
    ).select(
        "userId",
        (F.col("rank") + 1).alias("rank"),  # rank 1-based
        F.col("recommendation.movieId").alias("movieId"),
        F.col("recommendation.rating").alias("predicted_rating")
    )
    
    # Guardar en HDFS
    print(f"  📁 Guardando recomendaciones en {RECOMMENDATIONS_PATH}")
    user_recs_exploded.write.mode("overwrite").parquet(RECOMMENDATIONS_PATH)
    
    n_users = user_recs.count()
    n_recs = user_recs_exploded.count()
    
    elapsed_time = time.time() - start_time
    print(f"  ✅ {n_recs:,} recomendaciones generadas para {n_users:,} usuarios")
    print(f"  ✅ Generadas en {elapsed_time:.1f} segundos")
    
    # Mostrar sample
    print("\n  📋 Sample de recomendaciones (primeros 3 usuarios):")
    user_recs_exploded.filter(F.col("userId").isin([1, 2, 3])).orderBy("userId", "rank").show(30, truncate=False)
    
    return user_recs_exploded


def save_metrics(metrics, spark):
    """
    Guarda métricas de evaluación en HDFS.
    
    Args:
        metrics: dict con métricas
        spark: SparkSession
    """
    print(f"\n📊 PASO 7: Guardando métricas de evaluación...")
    
    # Crear DataFrame con métricas
    metrics_data = [
        ("rmse", metrics['rmse']),
        ("mae", metrics['mae']),
        ("n_predictions", float(metrics['n_predictions'])),
        ("n_valid", float(metrics['n_valid'])),
        ("coverage_pct", metrics['coverage']),
        ("rank", float(RANK)),
        ("reg_param", float(REG_PARAM)),
        ("max_iter", float(MAX_ITER)),
        ("test_ratio", float(TEST_RATIO)),
        ("timestamp", float(time.time()))
    ]
    
    metrics_df = spark.createDataFrame(metrics_data, ["metric", "value"])
    
    # Guardar en HDFS
    print(f"  📁 Guardando en {METRICS_PATH}")
    metrics_df.write.mode("overwrite").parquet(METRICS_PATH)
    
    print("  ✅ Métricas guardadas exitosamente")
    metrics_df.show(truncate=False)


def display_summary(metrics, train_count, test_count):
    """
    Muestra resumen final del entrenamiento.
    """
    print("\n" + "="*70)
    print("🏆 RESUMEN DE ENTRENAMIENTO ALS")
    print("="*70)
    print(f"\n📊 Configuración:")
    print(f"  - Rank: {RANK}")
    print(f"  - Regularización: {REG_PARAM}")
    print(f"  - Iteraciones: {MAX_ITER}")
    print(f"  - Cold Start: {COLD_START}")
    print(f"  - Non-negative: {NONNEGATIVE}")
    
    print(f"\n📈 Dataset:")
    print(f"  - Train: {train_count:,} ratings")
    print(f"  - Test: {test_count:,} ratings")
    
    print(f"\n🎯 Métricas de Evaluación:")
    print(f"  - RMSE: {metrics['rmse']:.4f}")
    print(f"  - MAE: {metrics['mae']:.4f}")
    print(f"  - Coverage: {metrics['coverage']:.1f}%")
    
    print(f"\n💾 Outputs guardados:")
    print(f"  - Modelo: {MODEL_PATH}")
    print(f"  - User Factors: {USER_FACTORS_PATH}")
    print(f"  - Item Factors: {ITEM_FACTORS_PATH}")
    print(f"  - Recomendaciones: {RECOMMENDATIONS_PATH}")
    print(f"  - Métricas: {METRICS_PATH}")
    
    print("\n" + "="*70)
    print("✅ FASE 5 COMPLETADA EXITOSAMENTE")
    print("="*70)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Pipeline completo de entrenamiento ALS"""
    
    print("="*70)
    print("FASE 5: ENTRENAMIENTO MODELO ALS (COLLABORATIVE FILTERING)")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Inicializar Spark
    spark = SparkSession.builder \
        .appName("MovieLens_ALS_Training") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # 1. Cargar ratings
        ratings = load_ratings(spark)
        
        # 2. Split train/test
        train_df, test_df = split_train_test(ratings, TEST_RATIO, RANDOM_SEED)
        
        # 3. Entrenar modelo
        model = train_als_model(
            train_df,
            rank=RANK,
            reg_param=REG_PARAM,
            max_iter=MAX_ITER,
            cold_start=COLD_START,
            nonnegative=NONNEGATIVE
        )
        
        # 4. Evaluar modelo
        metrics = evaluate_model(model, test_df)
        
        if metrics is None:
            print("\n❌ ERROR: Entrenamiento falló - métricas inválidas")
            return
        
        # 5. Guardar modelo y factores
        save_model(model, spark)
        
        # 6. Generar recomendaciones top-N
        recommendations = generate_recommendations(model, spark, TOP_N)
        
        # 7. Guardar métricas
        save_metrics(metrics, spark)
        
        # 8. Mostrar resumen
        display_summary(metrics, train_df.count(), test_df.count())
        
    except Exception as e:
        print(f"\n❌ ERROR durante el entrenamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
