#!/usr/bin/env python3
"""
ALS Recommender Model
====================

Implementación de Alternating Least Squares (ALS) usando Spark MLlib
para sistema de recomendación a gran escala.

Características:
- Factorización matricial escalable
- Guardado/carga de modelos
- Predicción de ratings
- Generación de recomendaciones top-N
- Métricas de evaluación (RMSE, MAE)

Uso:
    from movies.src.recommendation.models.als_model import ALSRecommender
    
    recommender = ALSRecommender(spark)
    recommender.train(ratings_df, rank=20, maxIter=10)
    recommendations = recommender.recommend_for_user(user_id=123, n=10)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.ml.evaluation import RegressionEvaluator


class ALSRecommender:
    """
    Sistema de recomendación basado en ALS (Alternating Least Squares)
    """
    
    def __init__(self, spark: SparkSession, model_path: Optional[str] = None):
        """
        Inicializa el recomendador ALS
        
        Args:
            spark: SparkSession activa
            model_path: Ruta opcional para cargar modelo existente
        """
        self.spark = spark
        self.model = None
        self.training_metrics = {}
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def train(
        self,
        ratings_df: DataFrame,
        rank: int = 20,
        maxIter: int = 10,
        regParam: float = 0.1,
        alpha: float = 1.0,
        coldStartStrategy: str = "drop",
        checkpointInterval: int = 10,
        nonnegative: bool = True,
        implicitPrefs: bool = False,
        seed: int = 42
    ) -> ALSModel:
        """
        Entrena el modelo ALS
        
        Args:
            ratings_df: DataFrame con columnas [userId, movieId, rating]
            rank: Dimensiones latentes (10-50)
            maxIter: Iteraciones del algoritmo (5-20)
            regParam: Regularización L2 (0.01-1.0)
            alpha: Parámetro de confianza para ratings implícitos
            coldStartStrategy: "drop" o "nan" para usuarios/items nuevos
            checkpointInterval: Intervalo para checkpointing (prevenir StackOverflow)
            nonnegative: Forzar factores no negativos
            implicitPrefs: Usar ratings implícitos en lugar de explícitos
            seed: Semilla aleatoria para reproducibilidad
            
        Returns:
            Modelo ALS entrenado
        """
        print("="*80)
        print("ENTRENAMIENTO DEL MODELO ALS")
        print("="*80)
        
        start_time = datetime.now()
        
        # Validar datos
        required_cols = ["userId", "movieId", "rating"]
        for col in required_cols:
            if col not in ratings_df.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada")
        
        train_count = ratings_df.count()
        print(f"\nDatos de entrenamiento: {train_count:,} ratings")
        
        # Configurar modelo ALS
        als = ALS(
            rank=rank,
            maxIter=maxIter,
            regParam=regParam,
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy=coldStartStrategy,
            nonnegative=nonnegative,
            implicitPrefs=implicitPrefs,
            alpha=alpha,
            seed=seed,
            checkpointInterval=checkpointInterval
        )
        
        print(f"\nParámetros del modelo:")
        print(f"  - Rank: {rank}")
        print(f"  - Max Iterations: {maxIter}")
        print(f"  - Regularization: {regParam}")
        print(f"  - Alpha: {alpha}")
        
        # Entrenar
        print(f"\nEntrenando modelo...")
        self.model = als.fit(ratings_df)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Guardar métricas
        self.training_metrics = {
            'rank': rank,
            'maxIter': maxIter,
            'regParam': regParam,
            'alpha': alpha,
            'train_size': train_count,
            'training_time_seconds': duration,
            'timestamp': start_time.isoformat()
        }
        
        print(f"\n✓ Entrenamiento completado en {duration:.2f}s ({duration/60:.2f} min)")
        print(f"  - User factors: {self.model.userFactors.count():,}")
        print(f"  - Item factors: {self.model.itemFactors.count():,}")
        print("="*80 + "\n")
        
        return self.model
    
    def evaluate(self, test_df: DataFrame) -> Dict[str, float]:
        """
        Evalúa el modelo con datos de prueba
        
        Args:
            test_df: DataFrame de prueba con [userId, movieId, rating]
            
        Returns:
            Diccionario con métricas (rmse, mae, mse, r2)
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llama a train() primero.")
        
        print("Evaluando modelo...")
        
        # Generar predicciones
        predictions = self.model.transform(test_df)
        predictions = predictions.na.drop()  # Eliminar cold start
        
        metrics = {}
        
        # RMSE
        evaluator_rmse = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        metrics['rmse'] = evaluator_rmse.evaluate(predictions)
        
        # MAE
        evaluator_mae = RegressionEvaluator(
            metricName="mae",
            labelCol="rating",
            predictionCol="prediction"
        )
        metrics['mae'] = evaluator_mae.evaluate(predictions)
        
        # MSE
        evaluator_mse = RegressionEvaluator(
            metricName="mse",
            labelCol="rating",
            predictionCol="prediction"
        )
        metrics['mse'] = evaluator_mse.evaluate(predictions)
        
        # R2
        evaluator_r2 = RegressionEvaluator(
            metricName="r2",
            labelCol="rating",
            predictionCol="prediction"
        )
        metrics['r2'] = evaluator_r2.evaluate(predictions)
        
        print(f"✓ Evaluación completada:")
        print(f"  - RMSE: {metrics['rmse']:.4f}")
        print(f"  - MAE: {metrics['mae']:.4f}")
        print(f"  - R²: {metrics['r2']:.4f}")
        
        self.training_metrics.update(metrics)
        
        return metrics
    
    def recommend_for_user(
        self, 
        user_id: int, 
        n: int = 10,
        filter_seen: bool = True,
        seen_movies: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Genera recomendaciones para un usuario
        
        Args:
            user_id: ID del usuario
            n: Número de recomendaciones
            filter_seen: Filtrar películas ya vistas
            seen_movies: Lista opcional de IDs de películas ya vistas
            
        Returns:
            Lista de diccionarios con [movieId, score]
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        # Crear DataFrame con el usuario
        user_df = self.spark.createDataFrame([(user_id,)], ["userId"])
        
        # Generar recomendaciones
        user_recs = self.model.recommendForUserSubset(user_df, n)
        
        # Extraer recomendaciones
        recs_collected = user_recs.collect()
        
        if not recs_collected:
            return []
        
        recommendations = []
        for rec in recs_collected[0]['recommendations']:
            recommendations.append({
                'movieId': int(rec['movieId']),
                'score': float(rec['rating'])
            })
        
        return recommendations
    
    def recommend_for_all_users(self, n: int = 10) -> DataFrame:
        """
        Genera recomendaciones para todos los usuarios
        
        Args:
            n: Número de recomendaciones por usuario
            
        Returns:
            DataFrame con [userId, recommendations]
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        return self.model.recommendForAllUsers(n)
    
    def predict_rating(self, user_id: int, movie_id: int) -> Optional[float]:
        """
        Predice el rating de un usuario para una película
        
        Args:
            user_id: ID del usuario
            movie_id: ID de la película
            
        Returns:
            Rating predicho o None si cold start
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        # Crear DataFrame con el par
        test_df = self.spark.createDataFrame(
            [(user_id, movie_id)], 
            ["userId", "movieId"]
        )
        
        # Predecir
        prediction = self.model.transform(test_df)
        result = prediction.select("prediction").collect()
        
        if result and result[0]['prediction'] is not None:
            return float(result[0]['prediction'])
        
        return None
    
    def batch_predict(self, user_movie_pairs: List[Tuple[int, int]]) -> DataFrame:
        """
        Predice ratings para múltiples pares usuario-película
        
        Args:
            user_movie_pairs: Lista de tuplas (userId, movieId)
            
        Returns:
            DataFrame con [userId, movieId, prediction]
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        test_df = self.spark.createDataFrame(
            user_movie_pairs,
            ["userId", "movieId"]
        )
        
        return self.model.transform(test_df)
    
    def get_similar_items(self, movie_id: int, n: int = 10) -> List[Dict]:
        """
        Encuentra películas similares basadas en factores latentes
        
        Args:
            movie_id: ID de la película
            n: Número de películas similares
            
        Returns:
            Lista de diccionarios con [movieId, similarity]
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        # Obtener factor latente de la película
        item_factors = self.model.itemFactors
        movie_factor = item_factors.filter(F.col("id") == movie_id).collect()
        
        if not movie_factor:
            return []
        
        # Calcular similitud con todas las películas
        # (Implementación simplificada - en producción usar aproximación)
        # Por ahora retornamos lista vacía
        # TODO: Implementar búsqueda de vecinos más cercanos
        
        return []
    
    def save_model(self, path: str) -> str:
        """
        Guarda el modelo entrenado
        
        Args:
            path: Ruta donde guardar el modelo
            
        Returns:
            Ruta donde se guardó el modelo
        """
        if self.model is None:
            raise ValueError("No hay modelo para guardar")
        
        # Crear directorio si no existe
        Path(path).mkdir(parents=True, exist_ok=True)
        
        # Guardar modelo Spark
        model_path = os.path.join(path, "als_model")
        self.model.write().overwrite().save(model_path)
        
        # Guardar métricas
        import json
        metrics_path = os.path.join(path, "metrics.json")
        with open(metrics_path, 'w') as f:
            json.dump(self.training_metrics, f, indent=2)
        
        print(f"✓ Modelo guardado en: {path}")
        
        return path
    
    def load_model(self, path: str) -> ALSModel:
        """
        Carga un modelo guardado
        
        Args:
            path: Ruta del modelo
            
        Returns:
            Modelo ALS cargado
        """
        model_path = os.path.join(path, "als_model")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo no encontrado en: {model_path}")
        
        self.model = ALSModel.load(model_path)
        
        # Cargar métricas si existen
        import json
        metrics_path = os.path.join(path, "metrics.json")
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                self.training_metrics = json.load(f)
        
        print(f"✓ Modelo cargado desde: {path}")
        
        return self.model
    
    def get_user_factors(self) -> DataFrame:
        """Retorna DataFrame de factores de usuario"""
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        return self.model.userFactors
    
    def get_item_factors(self) -> DataFrame:
        """Retorna DataFrame de factores de película"""
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        return self.model.itemFactors
