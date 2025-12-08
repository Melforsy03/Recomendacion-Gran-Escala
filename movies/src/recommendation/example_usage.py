#!/usr/bin/env python3
"""
Ejemplo de Uso del Sistema de Recomendación
============================================

Script de ejemplo mostrando cómo usar los diferentes modelos.
"""

from pyspark.sql import SparkSession
from movies.src.recommendation.models.als_model import ALSRecommender
from movies.src.recommendation.models.hybrid_recommender import HybridRecommender


def main():
    """Ejemplo de uso del sistema"""
    
    # 1. Crear SparkSession
    print("Creando SparkSession...")
    spark = SparkSession.builder \
        .appName("RecommendationSystemExample") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    # 2. Cargar modelo ALS
    print("\nCargando modelo ALS...")
    als_recommender = ALSRecommender(
        spark,
        model_path="/opt/spark-apps/movies/trained_models/als/model_latest"
    )
    
    # 3. Generar recomendaciones para un usuario
    user_id = 123
    print(f"\nGenerando recomendaciones para usuario {user_id}...")
    
    recommendations = als_recommender.recommend_for_user(
        user_id=user_id,
        n=10
    )
    
    print(f"\nTop 10 recomendaciones:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. Película {rec['movieId']}: Score {rec['score']:.2f}")
    
    # 4. Predecir rating específico
    movie_id = 356
    print(f"\nPrediciendo rating de usuario {user_id} para película {movie_id}...")
    
    predicted_rating = als_recommender.predict_rating(user_id, movie_id)
    
    if predicted_rating:
        print(f"  Rating predicho: {predicted_rating:.2f}/5.0")
    else:
        print("  No se pudo predecir (cold start)")
    
    # 5. Usar sistema híbrido (si está disponible)
    print("\n" + "="*60)
    print("SISTEMA HÍBRIDO")
    print("="*60)
    
    try:
        hybrid = HybridRecommender(spark)
        hybrid.load_all_models(
            als_path="/opt/spark-apps/movies/trained_models/als/model_latest",
            item_cf_path="/opt/spark-apps/movies/trained_models/item_cf",
            features_path="hdfs://namenode:9000/data/content_features/movies_features"
        )
        
        hybrid_recs = hybrid.recommend(
            user_id=user_id,
            n=10,
            strategy='balanced'
        )
        
        print(f"\nRecomendaciones híbridas:")
        for i, rec in enumerate(hybrid_recs, 1):
            print(f"  {i}. Película {rec['movieId']}: Score {rec['score']:.2f}")
            print(f"      {rec['reason']}")
    
    except Exception as e:
        print(f"Sistema híbrido no disponible: {e}")
    
    spark.stop()
    print("\n✓ Ejemplo completado")


if __name__ == "__main__":
    main()
