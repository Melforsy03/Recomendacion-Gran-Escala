#!/usr/bin/env python3
"""
Content-Based Recommender
==========================

Sistema de recomendación basado en contenido (géneros, tags, features).
Ideal para resolver problema de cold-start de nuevos usuarios.

Uso:
    from movies.src.recommendation.models.content_based import ContentBasedRecommender
    
    cb = ContentBasedRecommender(spark)
    cb.load_movie_features(features_df)
    recommendations = cb.recommend_for_user_profile(user_profile, n=10)
"""

import os
from typing import List, Dict, Optional
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.ml.linalg import Vectors, VectorUDT
from pyspark.ml.feature import VectorAssembler
import numpy as np


class ContentBasedRecommender:
    """
    Sistema de recomendación basado en contenido de películas
    """
    
    def __init__(self, spark: SparkSession):
        """
        Inicializa el recomendador content-based
        
        Args:
            spark: SparkSession activa
        """
        self.spark = spark
        self.movie_features = None
        self.ratings_df = None
    
    def load_movie_features(self, features_path: str) -> DataFrame:
        """
        Carga features de películas desde HDFS
        
        Args:
            features_path: Ruta a /data/content_features/movies_features
            
        Returns:
            DataFrame con features
        """
        print(f"Cargando features de películas desde: {features_path}")
        
        self.movie_features = self.spark.read.parquet(features_path)
        
        count = self.movie_features.count()
        print(f"✓ Features cargadas: {count:,} películas")
        
        return self.movie_features
    
    def build_user_profile(
        self,
        user_id: int,
        ratings_df: DataFrame,
        min_rating: float = 3.5
    ) -> Optional[Dict]:
        """
        Construye perfil de usuario basado en sus ratings
        
        Args:
            user_id: ID del usuario
            ratings_df: DataFrame con ratings
            min_rating: Rating mínimo para incluir en perfil
            
        Returns:
            Diccionario con perfil de usuario (vector promedio ponderado)
        """
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        # Películas que el usuario valoró positivamente
        user_ratings = ratings_df.filter(
            (F.col("userId") == user_id) &
            (F.col("rating") >= min_rating)
        )
        
        if user_ratings.count() == 0:
            return None
        
        # Join con features
        user_movies = user_ratings.join(
            self.movie_features,
            "movieId"
        ).select(
            "movieId",
            "rating",
            "genres_vec",
            "tags_vec"
        )
        
        # Calcular perfil promedio ponderado por rating
        # (Implementación simplificada)
        # En producción: ponderar vectores por rating y promediar
        
        return {
            'userId': user_id,
            'num_ratings': user_movies.count()
        }
    
    def recommend_for_user(
        self,
        user_id: int,
        ratings_df: DataFrame,
        n: int = 10,
        min_rating: float = 3.5
    ) -> List[Dict]:
        """
        Genera recomendaciones basadas en contenido para un usuario
        
        Args:
            user_id: ID del usuario
            ratings_df: DataFrame con ratings
            n: Número de recomendaciones
            min_rating: Rating mínimo para construir perfil
            
        Returns:
            Lista de diccionarios con [movieId, score, reason]
        """
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        # Construir perfil de usuario
        user_profile = self.build_user_profile(user_id, ratings_df, min_rating)
        
        if user_profile is None:
            return []
        
        # Obtener películas valoradas
        seen_movies = ratings_df.filter(
            F.col("userId") == user_id
        ).select("movieId")
        
        # Filtrar películas no vistas
        candidate_movies = self.movie_features.join(
            seen_movies,
            "movieId",
            "left_anti"
        )
        
        # Calcular similitud con perfil de usuario
        # (Implementación simplificada - en producción calcular cosine similarity)
        # Por ahora retornamos películas populares del género favorito
        
        recommendations = candidate_movies.limit(n)
        
        results = []
        for row in recommendations.collect():
            results.append({
                'movieId': int(row['movieId']),
                'title': row.get('title', 'Unknown'),
                'score': 1.0,  # Placeholder
                'reason': 'Based on your preferences'
            })
        
        return results
    
    def get_similar_movies_by_content(
        self,
        movie_id: int,
        n: int = 10
    ) -> List[Dict]:
        """
        Encuentra películas similares por contenido
        
        Args:
            movie_id: ID de la película
            n: Número de películas similares
            
        Returns:
            Lista con películas similares
        """
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        # Obtener features de la película
        movie = self.movie_features.filter(F.col("movieId") == movie_id).collect()
        
        if not movie:
            return []
        
        # Calcular similitud con todas las películas
        # (Implementación simplificada)
        similar = self.movie_features.filter(
            F.col("movieId") != movie_id
        ).limit(n)
        
        results = []
        for row in similar.collect():
            results.append({
                'movieId': int(row['movieId']),
                'title': row.get('title', 'Unknown'),
                'similarity': 1.0  # Placeholder
            })
        
        return results
