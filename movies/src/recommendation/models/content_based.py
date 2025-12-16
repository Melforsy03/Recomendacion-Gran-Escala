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
    
    def _detect_columns(self, df):
        """Devuelve (user_col, movie_col) compatibles con el DataFrame pasado"""
        user_col = "user_id" if "user_id" in df.columns else ("userId" if "userId" in df.columns else None)
        movie_col = "movie_id" if "movie_id" in df.columns else ("movieId" if "movieId" in df.columns else None)
        return user_col, movie_col
    
    def _get_movie_features_normalized(self):
        """Retorna movie_features con columna 'movieId' normalizada"""
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        if "movieId" not in self.movie_features.columns and "movie_id" in self.movie_features.columns:
            return self.movie_features.withColumnRenamed("movie_id", "movieId")
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
            Diccionario con perfil de usuario o None si sin ratings
        """
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        # detectar columnas dinámicamente
        user_col, movie_col = self._detect_columns(ratings_df)
        if user_col is None or movie_col is None:
            raise ValueError("Ratings DataFrame no tiene columnas userId/movieId ni user_id/movie_id")

        # Películas que el usuario valoró positivamente
        user_ratings = ratings_df.filter(
            (F.col(user_col) == user_id) &
            (F.col("rating") >= min_rating)
        )

        if user_ratings.count() == 0:
            return None

        # Normalizar nombre de columna para el join: renombrar columna de movie en user_ratings a 'movieId'
        if movie_col != "movieId":
            user_ratings = user_ratings.withColumnRenamed(movie_col, "movieId")

        # Asegurar que movie_features tenga 'movieId' para el join
        movie_features_local = self._get_movie_features_normalized()

        # Join con features
        user_movies = user_ratings.join(
            movie_features_local,
            "movieId"
        ).select(
            "movieId",
            "rating",
            # ajustar por si no existen
            *(["genres_vec"] if "genres_vec" in movie_features_local.columns else []),
            *(["tags_vec"] if "tags_vec" in movie_features_local.columns else [])
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
        
        Estrategia:
        1. Si usuario tiene ratings positivos → retornar películas similares
        2. Si NO tiene ratings → usar cold_start (películas populares por contenido)
        
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
        
        # ✅ CORREGIDO: Si no tiene ratings, usar cold_start en lugar de retornar []
        if user_profile is None:
            print(f"  ⚠ Usuario {user_id} sin ratings, usando cold_start para Content-Based")
            return self.recommend_for_cold_start(n=n)
        
        # adaptar detección de columnas para 'seen_movies'
        user_col, movie_col = self._detect_columns(ratings_df)
        if movie_col != "movieId":
            seen_movies = ratings_df.withColumnRenamed(movie_col, "movieId").filter(F.col(user_col) == user_id).select("movieId")
        else:
            seen_movies = ratings_df.filter(F.col(user_col) == user_id).select("movieId")
        
        # Filtrar películas no vistas
        movie_features_local = self._get_movie_features_normalized()
        candidate_movies = movie_features_local.join(
            seen_movies,
            "movieId",
            "left_anti"
        )
        
        # ✅ MEJORADO: Si no hay candidatos, usar cold_start como fallback
        if candidate_movies.count() == 0:
            print(f"  ⚠ No hay películas candidatas para usuario {user_id}, usando cold_start")
            return self.recommend_for_cold_start(n=n)
        
        # Calcular similitud con perfil de usuario (simplificado: primeras N)
        # En producción: calcular cosine similarity real entre perfil y features
        recommendations = candidate_movies.limit(n)
        
        results = []
        for row in recommendations.collect():
            results.append({
                'movieId': int(row['movieId']),
                'title': row.get('title', 'Unknown') if 'title' in row.asDict() else 'Unknown',
                'score': 0.8,  # Score placeholder (debe ser similitud real)
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
        
        movie_features_local = self._get_movie_features_normalized()
        
        # Obtener features de la película
        movie = movie_features_local.filter(F.col("movieId") == movie_id).collect()
        
        if not movie:
            return []
        
        # Calcular similitud con todas las películas
        # (Implementación simplificada)
        similar = movie_features_local.filter(
            F.col("movieId") != movie_id
        ).limit(n)
        
        results = []
        for row in similar.collect():
            results.append({
                'movieId': int(row['movieId']),
                'title': row.get('title', 'Unknown') if 'title' in row.asDict() else 'Unknown',
                'similarity': 0.75  # Placeholder
            })
        
        return results
    
    def recommend_for_cold_start(self, n: int = 10) -> List[Dict]:
        """
        Recomendaciones para usuarios nuevos (no requieren ratings).
        
        Estrategia:
        1. Si existe columna de popularidad → usarla (calificado por hits/vistas)
        2. Si NO → devolver películas aleatorias balanceadas (primeras N)
        
        Args:
            n: Número de recomendaciones
            
        Returns:
            Lista de recomendaciones de películas populares/representativas
        """
        if self.movie_features is None:
            raise ValueError("Features no cargadas")
        
        movie_features_local = self._get_movie_features_normalized()
        
        # Buscar columnas de popularidad (variantes comunes en datasets)
        pop_col_candidates = ["popularity", "pop_score", "popularity_score", "views", "num_ratings", "rating_count"]
        pop_col = None
        for c in pop_col_candidates:
            if c in movie_features_local.columns:
                pop_col = c
                print(f"  ℹ️  Usando columna de popularidad: {pop_col}")
                break
        
        # ✅ MEJORADO: Obtener películas con mejor score (no solo primeras N)
        if pop_col:
            # Ordenar por popularidad y limitar
            candidates = movie_features_local.orderBy(F.desc(pop_col)).limit(n)
        else:
            # Fallback: tomar muestra aleatoria distribuida (mejor que primeras N)
            total_count = movie_features_local.count()
            if total_count > n * 2:
                # Tomar muestra para variedád
                candidates = movie_features_local.sample(withReplacement=False, fraction=min(0.5, (n * 2) / total_count)).limit(n)
            else:
                candidates = movie_features_local.limit(n)
        
        results = []
        for row in candidates.collect():
            row_dict = row.asDict()
            results.append({
                'movieId': int(row_dict['movieId']),
                'title': row_dict.get('title', 'Unknown'),
                'score': float(row_dict.get(pop_col, 0.5)) if pop_col else 0.5,
                'reason': 'Cold-start: popular movie'
            })
        
        return results
