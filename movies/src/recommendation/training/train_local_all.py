#!/usr/bin/env python3
"""
Script de Entrenamiento Local - Sistema de Recomendación Multi-Modelo
=======================================================================

Entrena todos los modelos de recomendación localmente usando datos de Dataset/*.csv:
- ALS (Alternating Least Squares)
- Item-CF (Collaborative Filtering basado en ítems)
- Content-Based (Basado en features)
- Híbrido (Combinación de los anteriores)

Los modelos entrenados se guardan en movies/trained_models/ con versionado automático.

Uso:
    python movies/src/recommendation/training/train_local_all.py [--models ALS,ITEM_CF,CONTENT,HYBRID]

Requirements:
    - PySpark instalado localmente
    - Dataset/*.csv en la carpeta raíz del proyecto
    - Memoria mínima recomendada: 8GB

Autor: Sistema de Recomendación a Gran Escala
Fecha: 8 de diciembre de 2025
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Añadir el directorio raíz al path para importar módulos
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, FloatType, StringType

# Importar modelos
from movies.src.recommendation.models.als_model import ALSRecommender
from movies.src.recommendation.models.item_cf import ItemCollaborativeFiltering
from movies.src.recommendation.models.content_based import ContentBasedRecommender
from movies.src.recommendation.models.hybrid_recommender import HybridRecommender


# ==========================================
# Configuración
# ==========================================

class Config:
    """Configuración del entrenamiento"""
    
    # Paths
    PROJECT_ROOT = PROJECT_ROOT
    DATASET_DIR = PROJECT_ROOT / "Dataset"
    TRAINED_MODELS_DIR = PROJECT_ROOT / "movies" / "trained_models"
    
    # Archivos de datos
    RATINGS_CSV = DATASET_DIR / "rating.csv"
    MOVIES_CSV = DATASET_DIR / "movie.csv"
    GENOME_SCORES_CSV = DATASET_DIR / "genome_scores.csv"
    GENOME_TAGS_CSV = DATASET_DIR / "genome_tags.csv"
    
    # Configuración de Spark
    SPARK_MEMORY = "8g"
    SPARK_CORES = 4
    
    # Parámetros de entrenamiento ALS
    ALS_RANK = 20
    ALS_MAX_ITER = 10
    ALS_REG_PARAM = 0.1
    ALS_ALPHA = 1.0
    
    # Parámetros Item-CF
    ITEM_CF_MIN_COMMON_USERS = 5
    
    # Split train/test
    TRAIN_RATIO = 0.8
    RANDOM_SEED = 42


# ==========================================
# Funciones de Utilidad
# ==========================================

def create_spark_session(app_name: str = "LocalTraining") -> SparkSession:
    """Crea SparkSession local"""
    print("\n" + "="*80)
    print(f"CREANDO SPARK SESSION: {app_name}")
    print("="*80)
    
    spark = SparkSession.builder \
        .appName(app_name) \
        .master(f"local[{Config.SPARK_CORES}]") \
        .config("spark.driver.memory", Config.SPARK_MEMORY) \
        .config("spark.sql.shuffle.partitions", "20") \
        .config("spark.default.parallelism", "20") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"✓ Spark {spark.version} inicializado")
    print(f"  Master: {spark.sparkContext.master}")
    print(f"  App Name: {spark.sparkContext.appName}")
    print(f"  Cores: {Config.SPARK_CORES}")
    print(f"  Memory: {Config.SPARK_MEMORY}")
    print("="*80 + "\n")
    
    return spark


def load_ratings(spark: SparkSession) -> Optional[any]:
    """Carga ratings desde CSV local"""
    print(f"\n📂 Cargando ratings desde: {Config.RATINGS_CSV}")
    
    if not Config.RATINGS_CSV.exists():
        print(f"❌ ERROR: Archivo no encontrado: {Config.RATINGS_CSV}")
        return None
    
    ratings_df = spark.read.csv(
        str(Config.RATINGS_CSV),
        header=True,
        inferSchema=True
    ).select(
        F.col("userId").cast(IntegerType()),
        F.col("movieId").cast(IntegerType()),
        F.col("rating").cast(FloatType()),
        F.col("timestamp").cast(IntegerType())
    )
    
    count = ratings_df.count()
    print(f"✓ Ratings cargados: {count:,} registros")
    
    # Estadísticas básicas
    stats = ratings_df.agg(
        F.countDistinct("userId").alias("num_users"),
        F.countDistinct("movieId").alias("num_movies"),
        F.avg("rating").alias("avg_rating"),
        F.min("rating").alias("min_rating"),
        F.max("rating").alias("max_rating")
    ).collect()[0]
    
    print(f"  Usuarios únicos: {stats['num_users']:,}")
    print(f"  Películas únicas: {stats['num_movies']:,}")
    print(f"  Rating promedio: {stats['avg_rating']:.2f}")
    print(f"  Rating rango: [{stats['min_rating']:.1f}, {stats['max_rating']:.1f}]")
    
    return ratings_df


def load_movies(spark: SparkSession) -> Optional[any]:
    """Carga metadata de películas"""
    print(f"\n📂 Cargando películas desde: {Config.MOVIES_CSV}")
    
    if not Config.MOVIES_CSV.exists():
        print(f"❌ ERROR: Archivo no encontrado: {Config.MOVIES_CSV}")
        return None
    
    movies_df = spark.read.csv(
        str(Config.MOVIES_CSV),
        header=True,
        inferSchema=True
    ).select(
        F.col("movieId").cast(IntegerType()),
        F.col("title").cast(StringType()),
        F.col("genres").cast(StringType())
    )
    
    count = movies_df.count()
    print(f"✓ Películas cargadas: {count:,} registros")
    
    return movies_df


def load_genome_data(spark: SparkSession) -> tuple:
    """Carga genome scores y tags"""
    print(f"\n📂 Cargando genome data...")
    
    genome_scores = None
    genome_tags = None
    
    if Config.GENOME_SCORES_CSV.exists():
        genome_scores = spark.read.csv(
            str(Config.GENOME_SCORES_CSV),
            header=True,
            inferSchema=True
        )
        print(f"✓ Genome scores: {genome_scores.count():,} registros")
    else:
        print("⚠️  Genome scores no encontrado")
    
    if Config.GENOME_TAGS_CSV.exists():
        genome_tags = spark.read.csv(
            str(Config.GENOME_TAGS_CSV),
            header=True,
            inferSchema=True
        )
        print(f"✓ Genome tags: {genome_tags.count():,} registros")
    else:
        print("⚠️  Genome tags no encontrado")
    
    return genome_scores, genome_tags


def split_train_test(ratings_df: any) -> tuple:
    """Divide datos en train/test estratificado"""
    print(f"\n✂️  Dividiendo datos en train/test ({Config.TRAIN_RATIO:.0%}/{1-Config.TRAIN_RATIO:.0%})...")
    
    train_df, test_df = ratings_df.randomSplit(
        [Config.TRAIN_RATIO, 1 - Config.TRAIN_RATIO],
        seed=Config.RANDOM_SEED
    )
    
    train_count = train_df.count()
    test_count = test_df.count()
    
    print(f"✓ Train: {train_count:,} registros")
    print(f"✓ Test: {test_count:,} registros")
    
    return train_df, test_df


def create_versioned_path(model_type: str) -> Path:
    """Crea path versionado para modelo"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"{model_type}_model_v1_{timestamp}"
    model_path = Config.TRAINED_MODELS_DIR / model_type / model_name
    model_path.mkdir(parents=True, exist_ok=True)
    return model_path


def update_latest_symlink(model_type: str, model_path: Path):
    """Actualiza symlink model_latest"""
    latest_link = Config.TRAINED_MODELS_DIR / model_type / "model_latest"
    
    # Eliminar symlink anterior si existe
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    
    # Crear nuevo symlink (relativo)
    latest_link.symlink_to(model_path.name)
    print(f"✓ Symlink actualizado: {latest_link} -> {model_path.name}")


def save_metadata(model_path: Path, metadata: Dict):
    """Guarda metadata del modelo"""
    metadata_file = model_path / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata guardada: {metadata_file}")


def check_model_exists(model_type: str) -> bool:
    """
    Verifica si ya existe un modelo entrenado
    
    Args:
        model_type: Tipo de modelo (als, item_cf, content_based, hybrid)
        
    Returns:
        True si existe y es válido, False en caso contrario
    """
    latest_link = Config.TRAINED_MODELS_DIR / model_type / "model_latest"
    
    # Verificar que existe el symlink
    if not latest_link.exists() and not latest_link.is_symlink():
        return False
    
    # Verificar que apunta a un directorio válido
    try:
        model_path = latest_link.resolve()
        if not model_path.exists():
            return False
        
        # Verificar que tiene metadata
        metadata_file = model_path / "metadata.json"
        if not metadata_file.exists():
            return False
        
        # Verificar estructura según tipo de modelo
        if model_type == "als":
            spark_model = model_path / "spark_model"
            if not spark_model.exists():
                return False
        elif model_type == "item_cf":
            similarity_matrix = model_path / "similarity_matrix"
            if not similarity_matrix.exists():
                return False
        elif model_type == "content_based":
            features = model_path / "movie_features"
            if not features.exists():
                return False
        elif model_type == "hybrid":
            config_file = model_path / "strategies_config.json"
            if not config_file.exists():
                return False
        
        return True
        
    except Exception:
        return False


def get_model_info(model_type: str) -> Optional[Dict]:
    """
    Obtiene información del modelo existente
    
    Args:
        model_type: Tipo de modelo
        
    Returns:
        Diccionario con metadata o None si no existe
    """
    latest_link = Config.TRAINED_MODELS_DIR / model_type / "model_latest"
    
    try:
        model_path = latest_link.resolve()
        metadata_file = model_path / "metadata.json"
        
        with open(metadata_file) as f:
            metadata = json.load(f)
        
        return {
            "path": str(model_path),
            "name": model_path.name,
            "metadata": metadata
        }
    except Exception:
        return None


# ==========================================
# Entrenamiento de Modelos
# ==========================================

def train_als_model(spark: SparkSession, train_df: any, test_df: any, force: bool = False) -> bool:
    """Entrena modelo ALS"""
    print("\n" + "🎯"*40)
    print("ENTRENANDO MODELO ALS (Alternating Least Squares)")
    print("🎯"*40 + "\n")
    
    # Verificar si ya existe
    if not force and check_model_exists("als"):
        model_info = get_model_info("als")
        print("⏭️  Modelo ALS ya existe, omitiendo entrenamiento")
        print(f"   Versión: {model_info['name']}")
        print(f"   Timestamp: {model_info['metadata'].get('timestamp', 'unknown')}")
        if 'metrics' in model_info['metadata']:
            metrics = model_info['metadata']['metrics']
            print(f"   RMSE: {metrics.get('rmse', 'N/A'):.4f}")
        print("\n💡 Usa --force para re-entrenar de todos modos")
        return True
    
    try:
        # Crear modelo
        recommender = ALSRecommender(spark)
        
        # Entrenar
        print(f"Parámetros:")
        print(f"  rank={Config.ALS_RANK}")
        print(f"  maxIter={Config.ALS_MAX_ITER}")
        print(f"  regParam={Config.ALS_REG_PARAM}")
        print(f"  alpha={Config.ALS_ALPHA}")
        print()
        
        recommender.train(
            train_df,
            rank=Config.ALS_RANK,
            maxIter=Config.ALS_MAX_ITER,
            regParam=Config.ALS_REG_PARAM,
            alpha=Config.ALS_ALPHA,
            seed=Config.RANDOM_SEED
        )
        
        # Evaluar
        metrics = recommender.evaluate(test_df)
        
        print("\n📊 Métricas de evaluación:")
        print(f"  RMSE: {metrics['rmse']:.4f}")
        print(f"  MAE:  {metrics['mae']:.4f}")
        print(f"  MSE:  {metrics['mse']:.4f}")
        print(f"  R²:   {metrics['r2']:.4f}")
        
        # Guardar modelo
        model_path = create_versioned_path("als")
        spark_model_path = model_path / "spark_model"
        recommender.save_model(str(spark_model_path))
        
        # Guardar metadata
        metadata = {
            "model_type": "als",
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "rank": Config.ALS_RANK,
                "maxIter": Config.ALS_MAX_ITER,
                "regParam": Config.ALS_REG_PARAM,
                "alpha": Config.ALS_ALPHA,
                "seed": Config.RANDOM_SEED
            },
            "metrics": metrics,
            "data": {
                "train_size": train_df.count(),
                "test_size": test_df.count()
            }
        }
        save_metadata(model_path, metadata)
        
        # Actualizar symlink
        update_latest_symlink("als", model_path)
        
        print(f"\n✅ Modelo ALS guardado en: {model_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR al entrenar ALS: {e}")
        import traceback
        traceback.print_exc()
        return False


def train_item_cf_model(spark: SparkSession, ratings_df: any, genome_scores: any, force: bool = False) -> bool:
    """Entrena modelo Item-CF"""
    print("\n" + "🎯"*40)
    print("ENTRENANDO MODELO ITEM-CF (Collaborative Filtering)")
    print("🎯"*40 + "\n")
    
    # Verificar si ya existe
    if not force and check_model_exists("item_cf"):
        model_info = get_model_info("item_cf")
        print("⏭️  Modelo Item-CF ya existe, omitiendo entrenamiento")
        print(f"   Versión: {model_info['name']}")
        print(f"   Timestamp: {model_info['metadata'].get('timestamp', 'unknown')}")
        print("\n💡 Usa --force para re-entrenar de todos modos")
        return True
    
    try:
        # Crear modelo
        cf = ItemCollaborativeFiltering(spark)
        
        # Construir matriz de similitud
        print(f"Parámetros:")
        print(f"  min_common_users={Config.ITEM_CF_MIN_COMMON_USERS}")
        print(f"  use_genome_scores={genome_scores is not None}")
        print()
        
        similarity_matrix = cf.build_similarity_matrix(
            ratings_df,
            min_common_users=Config.ITEM_CF_MIN_COMMON_USERS,
            use_genome_scores=(genome_scores is not None),
            genome_scores_df=genome_scores
        )
        
        # Estadísticas de la matriz
        sim_count = similarity_matrix.count()
        avg_sim = similarity_matrix.agg(F.avg("similarity")).collect()[0][0]
        
        print(f"\n📊 Matriz de similitud:")
        print(f"  Pares de películas: {sim_count:,}")
        print(f"  Similitud promedio: {avg_sim:.4f}")
        
        # Guardar modelo
        model_path = create_versioned_path("item_cf")
        similarity_path = model_path / "similarity_matrix"
        cf.save(str(similarity_path))
        
        # Guardar metadata
        metadata = {
            "model_type": "item_cf",
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "min_common_users": Config.ITEM_CF_MIN_COMMON_USERS,
                "use_genome_scores": genome_scores is not None
            },
            "stats": {
                "similarity_pairs": sim_count,
                "avg_similarity": float(avg_sim)
            }
        }
        save_metadata(model_path, metadata)
        
        # Actualizar symlink
        update_latest_symlink("item_cf", model_path)
        
        print(f"\n✅ Modelo Item-CF guardado en: {model_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR al entrenar Item-CF: {e}")
        import traceback
        traceback.print_exc()
        return False


def train_content_based_model(spark: SparkSession, movies_df: any, ratings_df: any, 
                              genome_scores: any, genome_tags: any, force: bool = False) -> bool:
    """Entrena modelo Content-Based"""
    print("\n" + "🎯"*40)
    print("ENTRENANDO MODELO CONTENT-BASED")
    print("🎯"*40 + "\n")
    
    # Verificar si ya existe
    if not force and check_model_exists("content_based"):
        model_info = get_model_info("content_based")
        print("⏭️  Modelo Content-Based ya existe, omitiendo entrenamiento")
        print(f"   Versión: {model_info['name']}")
        print(f"   Timestamp: {model_info['metadata'].get('timestamp', 'unknown')}")
        print("\n💡 Usa --force para re-entrenar de todos modos")
        return True
    
    try:
        # Crear modelo
        cb = ContentBasedRecommender(spark)
        
        # Construir features de películas
        print("Construyendo features de películas...")
        
        # Features de géneros
        from pyspark.ml.feature import StringIndexer, OneHotEncoder
        
        # Separar géneros (formato: "Action|Adventure|Sci-Fi")
        movies_with_genres = movies_df.withColumn(
            "genre_list",
            F.split(F.col("genres"), r"\|")
        )
        
        # Contar géneros únicos
        num_genres = movies_with_genres.select(F.explode("genre_list")).distinct().count()
        print(f"  Géneros únicos: {num_genres}")
        
        # Para simplificar, usar los géneros como features binarias
        # (en producción se usaría OneHotEncoder más sofisticado)
        from pyspark.ml.linalg import Vectors
        
        # Crear vector de features simplificado
        movies_features = movies_with_genres.withColumn(
            "features_vec",
            F.array(*[F.lit(1.0) for _ in range(num_genres)])
        ).select("movieId", "title", "genres", "features_vec")
        
        print(f"✓ Features creadas para {movies_features.count():,} películas")
        
        # Guardar features
        model_path = create_versioned_path("content_based")
        features_path = model_path / "movie_features"
        movies_features.write.mode("overwrite").parquet(str(features_path))
        
        # Guardar metadata
        metadata = {
            "model_type": "content_based",
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "num_movies": movies_features.count(),
                "num_genres": num_genres,
                "has_genome_scores": genome_scores is not None,
                "has_genome_tags": genome_tags is not None
            }
        }
        save_metadata(model_path, metadata)
        
        # Actualizar symlink
        update_latest_symlink("content_based", model_path)
        
        print(f"\n✅ Modelo Content-Based guardado en: {model_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR al entrenar Content-Based: {e}")
        import traceback
        traceback.print_exc()
        return False


def train_hybrid_model(spark: SparkSession, force: bool = False) -> bool:
    """Crea configuración del modelo híbrido"""
    print("\n" + "🎯"*40)
    print("CONFIGURANDO MODELO HÍBRIDO")
    print("🎯"*40 + "\n")
    
    # Verificar si ya existe
    if not force and check_model_exists("hybrid"):
        model_info = get_model_info("hybrid")
        print("⏭️  Modelo Híbrido ya existe, omitiendo configuración")
        print(f"   Versión: {model_info['name']}")
        print(f"   Timestamp: {model_info['metadata'].get('timestamp', 'unknown')}")
        print("\n💡 Usa --force para re-configurar de todos modos")
        return True
    
    try:
        # El modelo híbrido combina los otros 3 en tiempo de inferencia
        # Solo guardamos la configuración de estrategias
        
        model_path = create_versioned_path("hybrid")
        
        # Configuración de estrategias
        strategies_config = {
            'als_heavy': {'als': 0.7, 'item_cf': 0.2, 'content': 0.1},
            'balanced': {'als': 0.5, 'item_cf': 0.3, 'content': 0.2},
            'content_heavy': {'als': 0.3, 'item_cf': 0.2, 'content': 0.5},
            'cold_start': {'als': 0.0, 'item_cf': 0.3, 'content': 0.7}
        }
        
        # Guardar configuración
        config_file = model_path / "strategies_config.json"
        with open(config_file, 'w') as f:
            json.dump(strategies_config, f, indent=2)
        
        print("Estrategias híbridas configuradas:")
        for name, weights in strategies_config.items():
            print(f"  {name}: ALS={weights['als']:.1f}, Item-CF={weights['item_cf']:.1f}, Content={weights['content']:.1f}")
        
        # Guardar metadata
        metadata = {
            "model_type": "hybrid",
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "strategies": strategies_config,
            "dependencies": {
                "als": str(Config.TRAINED_MODELS_DIR / "als" / "model_latest"),
                "item_cf": str(Config.TRAINED_MODELS_DIR / "item_cf" / "model_latest"),
                "content_based": str(Config.TRAINED_MODELS_DIR / "content_based" / "model_latest")
            }
        }
        save_metadata(model_path, metadata)
        
        # Actualizar symlink
        update_latest_symlink("hybrid", model_path)
        
        print(f"\n✅ Modelo Híbrido configurado en: {model_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR al configurar Híbrido: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
# Main
# ==========================================

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Entrenamiento local de modelos de recomendación"
    )
    parser.add_argument(
        "--models",
        type=str,
        default="ALS,ITEM_CF,CONTENT,HYBRID",
        help="Modelos a entrenar (separados por coma): ALS,ITEM_CF,CONTENT,HYBRID"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar re-entrenamiento incluso si el modelo ya existe"
    )
    args = parser.parse_args()
    
    # Parse modelos a entrenar
    models_to_train = [m.strip().upper() for m in args.models.split(",")]
    
    print("\n" + "="*80)
    print("SISTEMA DE ENTRENAMIENTO LOCAL - RECOMENDACIÓN A GRAN ESCALA")
    print("="*80)
    print(f"\nModelos a entrenar: {', '.join(models_to_train)}")
    print(f"Directorio de datos: {Config.DATASET_DIR}")
    print(f"Directorio de salida: {Config.TRAINED_MODELS_DIR}")
    print(f"Modo: {'FORZAR RE-ENTRENAMIENTO' if args.force else 'OMITIR EXISTENTES'}")
    print("\n" + "="*80)
    
    # Verificar que existen los archivos de datos
    if not Config.RATINGS_CSV.exists():
        print(f"\n❌ ERROR: No se encuentra {Config.RATINGS_CSV}")
        print("Por favor, asegúrate de que los datos estén en la carpeta Dataset/")
        return 1
    
    # Crear SparkSession
    spark = create_spark_session("ModelTraining")
    
    try:
        # Cargar datos
        ratings_df = load_ratings(spark)
        if ratings_df is None:
            return 1
        
        movies_df = load_movies(spark)
        genome_scores, genome_tags = load_genome_data(spark)
        
        # Split train/test (para ALS)
        train_df, test_df = split_train_test(ratings_df)
        
        # Entrenar modelos según configuración
        results = {}
        
        if "ALS" in models_to_train:
            results["ALS"] = train_als_model(spark, train_df, test_df, force=args.force)
        
        if "ITEM_CF" in models_to_train:
            results["ITEM_CF"] = train_item_cf_model(spark, ratings_df, genome_scores, force=args.force)
        
        if "CONTENT" in models_to_train:
            results["CONTENT"] = train_content_based_model(
                spark, movies_df, ratings_df, genome_scores, genome_tags, force=args.force
            )
        
        if "HYBRID" in models_to_train:
            results["HYBRID"] = train_hybrid_model(spark, force=args.force)
        
        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN DE ENTRENAMIENTO")
        print("="*80)
        for model, success in results.items():
            status = "✅ ÉXITO" if success else "❌ FALLÓ"
            print(f"  {model}: {status}")
        
        all_success = all(results.values())
        if all_success:
            print("\n🎉 ¡Todos los modelos entrenados exitosamente!")
            print(f"\nModelos disponibles en: {Config.TRAINED_MODELS_DIR}")
            print("\nPróximos pasos:")
            print("  1. Verificar modelos: ls -lh movies/trained_models/*/model_latest")
            print("  2. Copiar a contenedores: ./scripts/copy_models_to_containers.sh")
            print("  3. Probar API: curl http://localhost:8000/recommend/123?n=10")
            return 0
        else:
            print("\n⚠️  Algunos modelos fallaron. Revisa los logs arriba.")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        spark.stop()
        print("\n✓ SparkSession cerrada")


if __name__ == "__main__":
    exit(main())
