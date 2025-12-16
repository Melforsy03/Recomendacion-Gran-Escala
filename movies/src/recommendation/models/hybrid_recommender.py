#!/usr/bin/env python3
"""
Hybrid Recommender System
==========================

Combina múltiples estrategias de recomendación:
- ALS (Collaborative Filtering matricial)
- Item-CF (Collaborative Filtering basado en ítems)
- Content-Based (Basado en features de películas)

Uso:
    from movies.src.recommendation.models.hybrid_recommender import HybridRecommender
    
    recommender = HybridRecommender(spark)
    recommender.load_all_models(als_path, item_cf_path, features_path)
    recommendations = recommender.recommend(user_id=123, n=10, strategy='balanced')
"""

from typing import List, Dict, Optional
from pyspark.sql import SparkSession

from .als_model import ALSRecommender
from .item_cf import ItemCollaborativeFiltering
from .content_based import ContentBasedRecommender


class HybridRecommender:
    """
    Sistema híbrido que combina múltiples algoritmos de recomendación
    """
    
    def __init__(self, spark: SparkSession):
        """
        Inicializa el sistema híbrido
        
        Args:
            spark: SparkSession activa
        """
        self.spark = spark
        self.als = None
        self.item_cf = None
        self.content_based = None
        
        # Pesos por estrategia
        self.strategies = {
            'als_heavy': {'als': 0.7, 'item_cf': 0.2, 'content': 0.1},
            'balanced': {'als': 0.5, 'item_cf': 0.3, 'content': 0.2},
            'content_heavy': {'als': 0.3, 'item_cf': 0.2, 'content': 0.5},
            'cold_start': {'als': 0.0, 'item_cf': 0.3, 'content': 0.7}
        }
    
    def load_all_models(
        self,
        als_path: Optional[str] = None,
        item_cf_path: Optional[str] = None,
        features_path: Optional[str] = None
    ):
        """
        Carga todos los modelos disponibles
        
        Args:
            als_path: Ruta al modelo ALS
            item_cf_path: Ruta a matriz de similitud Item-CF
            features_path: Ruta a features de películas
        """
        print("="*80)
        print("CARGANDO MODELOS DEL SISTEMA HÍBRIDO")
        print("="*80)
        
        # Cargar ALS
        if als_path:
            print("\n1. Cargando modelo ALS...")
            self.als = ALSRecommender(self.spark, model_path=als_path)
        
        # Cargar Item-CF
        if item_cf_path:
            print("\n2. Cargando Item-CF...")
            self.item_cf = ItemCollaborativeFiltering(self.spark)
            self.item_cf.load(item_cf_path)
        
        # Cargar Content-Based
        if features_path:
            print("\n3. Cargando Content-Based...")
            self.content_based = ContentBasedRecommender(self.spark)
            self.content_based.load_movie_features(features_path)
        
        print("\n" + "="*80)
        print("✓ Sistema híbrido listo")
        print("="*80 + "\n")
    
    def recommend(
        self,
        user_id: int,
        n: int = 10,
        strategy: str = 'balanced',
        ratings_df: Optional[any] = None
    ) -> List[Dict]:
        """
        Genera recomendaciones híbridas para un usuario
        
        Args:
            user_id: ID del usuario
            n: Número de recomendaciones
            strategy: 'als_heavy', 'balanced', 'content_heavy', 'cold_start'
            ratings_df: DataFrame opcional con ratings del usuario
            
        Returns:
            Lista de diccionarios con [movieId, score, reason, sources]
        """
        if strategy not in self.strategies:
            raise ValueError(f"Estrategia inválida: {strategy}")
        
        weights = self.strategies[strategy]
        all_recommendations = {}
        
        # Obtener recomendaciones de cada modelo
        print(f"Generando recomendaciones con estrategia: {strategy}")
        
        # ALS
        if self.als and weights['als'] > 0:
            try:
                als_recs = self.als.recommend_for_user(user_id, n=n*2)
                for rec in als_recs:
                    movie_id = rec['movieId']
                    if movie_id not in all_recommendations:
                        all_recommendations[movie_id] = {
                            'movieId': movie_id,
                            'score': 0.0,
                            'sources': []
                        }
                    all_recommendations[movie_id]['score'] += rec['score'] * weights['als']
                    all_recommendations[movie_id]['sources'].append('ALS')
                print(f"  ✓ ALS: {len(als_recs)} recomendaciones")
            except Exception as e:
                print(f"  ⚠ ALS falló: {e}")
        
        # Item-CF
        if self.item_cf and weights['item_cf'] > 0:
            try:
                cf_recs = self.item_cf.recommend_for_user(user_id, n=n*2)
                for rec in cf_recs:
                    movie_id = rec['movieId']
                    if movie_id not in all_recommendations:
                        all_recommendations[movie_id] = {
                            'movieId': movie_id,
                            'score': 0.0,
                            'sources': []
                        }
                    all_recommendations[movie_id]['score'] += rec['score'] * weights['item_cf']
                    all_recommendations[movie_id]['sources'].append('Item-CF')
                print(f"  ✓ Item-CF: {len(cf_recs)} recomendaciones")
            except Exception as e:
                print(f"  ⚠ Item-CF falló: {e}")
        
        # Content-Based
        if self.content_based and weights['content'] > 0:
            try:
                # ✅ MEJORADO: Content-based SIEMPRE intenta con usuario primero
                # Si usuario no tiene ratings, el método internally usa cold_start
                if ratings_df is not None:
                    content_recs = self.content_based.recommend_for_user(
                        user_id, ratings_df, n=n*2
                    )
                else:
                    # Sin ratings_df disponible, usar direct cold-start
                    content_recs = self.content_based.recommend_for_cold_start(n=n*2)

                for rec in content_recs:
                    movie_id = rec['movieId']
                    if movie_id not in all_recommendations:
                        all_recommendations[movie_id] = {
                            'movieId': movie_id,
                            'score': 0.0,
                            'sources': []
                        }
                    # nota: los recs pueden tener 'score' o no; usar 1.0 por defecto
                    rec_score = rec.get('score', 1.0)
                    all_recommendations[movie_id]['score'] += rec_score * weights['content']
                    all_recommendations[movie_id]['sources'].append('Content')
                print(f"  ✓ Content-Based: {len(content_recs)} recomendaciones")
            except Exception as e:
                print(f"  ⚠ Content-Based falló: {e}")
        
        # ✅ NUEVO: Fallback si todos los modelos retornan vacío
        if not all_recommendations:
            print(f"  ⚠ Ningún modelo generó candidatos, usando cold_start universal")
            if self.content_based:
                fallback = self.content_based.recommend_for_cold_start(n=n)
                return fallback
        
        # Ordenar por score y retornar top-N
        sorted_recs = sorted(
            all_recommendations.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:n]
        
        # Agregar razón
        for rec in sorted_recs:
            sources_str = ' + '.join(rec['sources'])
            rec['reason'] = f"Recommended by: {sources_str}"
        
        print(f"\n✓ Generadas {len(sorted_recs)} recomendaciones híbridas")
        
        return sorted_recs
    
    def explain_recommendation(
        self,
        user_id: int,
        movie_id: int
    ) -> Dict:
        """
        Explica por qué se recomendó una película
        
        Args:
            user_id: ID del usuario
            movie_id: ID de la película
            
        Returns:
            Diccionario con explicación detallada
        """
        explanation = {
            'userId': user_id,
            'movieId': movie_id,
            'sources': []
        }
        
        # Ver score de ALS
        if self.als:
            try:
                rating = self.als.predict_rating(user_id, movie_id)
                if rating:
                    explanation['sources'].append({
                        'model': 'ALS',
                        'score': rating,
                        'reason': f'Predicted rating: {rating:.2f}/5.0'
                    })
            except:
                pass
        
        # Ver similitud en Item-CF
        if self.item_cf:
            try:
                similar = self.item_cf.get_similar_movies(movie_id, n=5)
                if similar:
                    explanation['sources'].append({
                        'model': 'Item-CF',
                        'reason': f'Similar to {len(similar)} movies you liked'
                    })
            except:
                pass
        
        return explanation
    
    def get_model_weights(self, strategy: str) -> Dict[str, float]:
        """Retorna los pesos de cada modelo para una estrategia"""
        return self.strategies.get(strategy, self.strategies['balanced'])
    
    def set_custom_weights(
        self,
        strategy_name: str,
        als_weight: float,
        item_cf_weight: float,
        content_weight: float
    ):
        """
        Define una estrategia personalizada de pesos
        
        Args:
            strategy_name: Nombre de la estrategia
            als_weight: Peso para ALS (0.0-1.0)
            item_cf_weight: Peso para Item-CF (0.0-1.0)
            content_weight: Peso para Content-Based (0.0-1.0)
        """
        total = als_weight + item_cf_weight + content_weight
        
        if abs(total - 1.0) > 0.01:
            raise ValueError("Los pesos deben sumar 1.0")
        
        self.strategies[strategy_name] = {
            'als': als_weight,
            'item_cf': item_cf_weight,
            'content': content_weight
        }
        
        print(f"✓ Estrategia '{strategy_name}' creada con pesos:")
        print(f"  - ALS: {als_weight}")
        print(f"  - Item-CF: {item_cf_weight}")
        print(f"  - Content: {content_weight}")
