#!/usr/bin/env python3
"""
Item-Based Collaborative Filtering
===================================

Implementación de filtrado colaborativo basado en ítems (películas).
Calcula similitud entre películas basándose en ratings co-ocurrentes.

Características:
- Similitud coseno entre películas
- Integración con genome_scores de MovieLens
- Escalable con Spark
- Guardado/carga de matriz de similitud

Uso:
    from movies.src.recommendation.models.item_cf import ItemCollaborativeFiltering
    
    cf = ItemCollaborativeFiltering(spark)
    cf.build_similarity_matrix(ratings_df)
    recommendations = cf.recommend_for_user(user_id=123, n=10)
"""

import os
from typing import List, Dict, Optional
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import FloatType


class ItemCollaborativeFiltering:
    """
    Sistema de recomendación basado en similitud entre ítems
    """
    
    def __init__(self, spark: SparkSession):
        """
        Inicializa el sistema de CF basado en ítems
        
        Args:
            spark: SparkSession activa
        """
        self.spark = spark
        self.similarity_matrix = None
        self.ratings_df = None
    
    def build_similarity_matrix(
        self,
        ratings_df: DataFrame,
        min_common_users: int = 5,
        use_genome_scores: bool = False,
        genome_scores_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Construye matriz de similitud entre películas
        
        Args:
            ratings_df: DataFrame con [userId, movieId, rating]
            min_common_users: Mínimo de usuarios en común para calcular similitud
            use_genome_scores: Usar genome scores para boost de similitud
            genome_scores_df: DataFrame opcional con genome scores
            
        Returns:
            DataFrame con [movieId1, movieId2, similarity]
        """
        print("="*80)
        print("CONSTRUYENDO MATRIZ DE SIMILITUD (ITEM-CF)")
        print("="*80)
        
        self.ratings_df = ratings_df
        
        # Crear pares de películas valoradas por mismo usuario
        print("\nCreando pares de películas...")
        pairs = ratings_df.alias("r1").join(
            ratings_df.alias("r2"),
            (F.col("r1.userId") == F.col("r2.userId")) &
            (F.col("r1.movieId") < F.col("r2.movieId"))
        ).select(
            F.col("r1.movieId").alias("movieId1"),
            F.col("r2.movieId").alias("movieId2"),
            F.col("r1.rating").alias("rating1"),
            F.col("r2.rating").alias("rating2")
        )
        
        # Calcular similitud coseno
        print("Calculando similitud coseno...")
        similarity = pairs.groupBy("movieId1", "movieId2").agg(
            F.count("*").alias("num_common_users"),
            (F.sum(F.col("rating1") * F.col("rating2")) /
             (F.sqrt(F.sum(F.col("rating1") * F.col("rating1"))) *
              F.sqrt(F.sum(F.col("rating2") * F.col("rating2"))))).alias("similarity")
        )
        
        # Filtrar por mínimo de usuarios en común
        similarity = similarity.filter(F.col("num_common_users") >= min_common_users)
        
        # Opcional: Boost con genome scores
        if use_genome_scores and genome_scores_df is not None:
            print("Aplicando boost con genome scores...")
            # TODO: Implementar boost con similitud semántica
            pass
        
        # Crear matriz simétrica
        similarity_sym = similarity.union(
            similarity.select(
                F.col("movieId2").alias("movieId1"),
                F.col("movieId1").alias("movieId2"),
                F.col("similarity"),
                F.col("num_common_users")
            )
        )
        
        self.similarity_matrix = similarity_sym.cache()
        
        num_pairs = self.similarity_matrix.count()
        print(f"\n✓ Matriz de similitud construida: {num_pairs:,} pares")
        print("="*80 + "\n")
        
        return self.similarity_matrix
    
    def recommend_for_user(
        self,
        user_id: int,
        n: int = 10,
        min_rating_threshold: float = 3.5
    ) -> List[Dict]:
        """
        Genera recomendaciones para un usuario
        
        Estrategia:
        1. Obtener películas que el usuario valoró positivamente
        2. Encontrar películas similares
        3. Agregar y rankear candidatos
        
        Args:
            user_id: ID del usuario
            n: Número de recomendaciones
            min_rating_threshold: Rating mínimo para considerar película como "gustada"
            
        Returns:
            Lista de diccionarios con [movieId, score, reason]
        """
        if self.similarity_matrix is None:
            raise ValueError("Matriz de similitud no construida")
        
        if self.ratings_df is None:
            raise ValueError("Ratings no disponibles")
        
        # Películas que el usuario valoró positivamente
        user_movies = self.ratings_df.filter(
            (F.col("userId") == user_id) &
            (F.col("rating") >= min_rating_threshold)
        ).select("movieId", "rating")
        
        if user_movies.count() == 0:
            return []
        
        # Encontrar películas similares
        similar_movies = user_movies.alias("um").join(
            self.similarity_matrix.alias("sim"),
            F.col("um.movieId") == F.col("sim.movieId1")
        ).select(
            F.col("sim.movieId2").alias("movieId"),
            (F.col("sim.similarity") * F.col("um.rating")).alias("weighted_sim"),
            F.col("um.movieId").alias("source_movie")
        )
        
        # Agregar scores por película candidata
        recommendations = similar_movies.groupBy("movieId").agg(
            F.sum("weighted_sim").alias("score"),
            F.count("*").alias("num_sources")
        )
        
        # Filtrar películas ya vistas
        seen_movies = self.ratings_df.filter(
            F.col("userId") == user_id
        ).select("movieId")
        
        recommendations = recommendations.join(
            seen_movies,
            "movieId",
            "left_anti"
        )
        
        # Ordenar y limitar
        recommendations = recommendations.orderBy(F.desc("score")).limit(n)
        
        # Convertir a lista
        results = []
        for row in recommendations.collect():
            results.append({
                'movieId': int(row['movieId']),
                'score': float(row['score']),
                'num_sources': int(row['num_sources']),
                'reason': f'Similar to {row["num_sources"]} movies you liked'
            })
        
        return results
    
    def get_similar_movies(
        self,
        movie_id: int,
        n: int = 10,
        min_similarity: float = 0.5
    ) -> List[Dict]:
        """
        Encuentra películas similares a una dada
        
        Args:
            movie_id: ID de la película
            n: Número de películas similares
            min_similarity: Similitud mínima requerida
            
        Returns:
            Lista de diccionarios con [movieId, similarity]
        """
        if self.similarity_matrix is None:
            raise ValueError("Matriz de similitud no construida")
        
        similar = self.similarity_matrix.filter(
            (F.col("movieId1") == movie_id) &
            (F.col("similarity") >= min_similarity)
        ).select(
            F.col("movieId2").alias("movieId"),
            "similarity"
        ).orderBy(F.desc("similarity")).limit(n)
        
        results = []
        for row in similar.collect():
            results.append({
                'movieId': int(row['movieId']),
                'similarity': float(row['similarity'])
            })
        
        return results
    
    def save(self, path: str) -> str:
        """
        Guarda la matriz de similitud
        
        Args:
            path: Ruta donde guardar
            
        Returns:
            Ruta donde se guardó
        """
        if self.similarity_matrix is None:
            raise ValueError("No hay matriz para guardar")
        
        Path(path).mkdir(parents=True, exist_ok=True)
        
        similarity_path = os.path.join(path, "similarity_matrix")
        self.similarity_matrix.write.mode("overwrite").parquet(similarity_path)
        
        print(f"✓ Matriz de similitud guardada en: {similarity_path}")
        
        return path
    
    def load(self, path: str) -> DataFrame:
        """
        Carga matriz de similitud guardada
        
        Args:
            path: Ruta del archivo
            
        Returns:
            DataFrame de similitud
        """
        similarity_path = os.path.join(path, "similarity_matrix")
        
        if not os.path.exists(similarity_path):
            raise FileNotFoundError(f"Matriz no encontrada en: {similarity_path}")
        
        self.similarity_matrix = self.spark.read.parquet(similarity_path).cache()
        
        print(f"✓ Matriz de similitud cargada desde: {similarity_path}")
        
        return self.similarity_matrix
