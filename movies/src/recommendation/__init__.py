"""
Sistema de Recomendación de Películas a Gran Escala
===================================================

Módulo principal que integra múltiples algoritmos de recomendación:
- ALS (Alternating Least Squares)
- Item-Based Collaborative Filtering
- Content-Based Filtering
- Hybrid Recommender

Autor: Sistema de Recomendación PGVD
Fecha: 2025
"""

__version__ = "1.0.0"

from .models.als_model import ALSRecommender
from .models.item_cf import ItemCollaborativeFiltering
from .models.content_based import ContentBasedRecommender
from .models.hybrid_recommender import HybridRecommender

__all__ = [
    'ALSRecommender',
    'ItemCollaborativeFiltering',
    'ContentBasedRecommender',
    'HybridRecommender'
]
