"""
Modelos de Recomendación
========================

Este módulo contiene las implementaciones de diferentes algoritmos
de recomendación de películas.
"""

from .als_model import ALSRecommender
from .item_cf import ItemCollaborativeFiltering
from .content_based import ContentBasedRecommender
from .hybrid_recommender import HybridRecommender

__all__ = [
    'ALSRecommender',
    'ItemCollaborativeFiltering', 
    'ContentBasedRecommender',
    'HybridRecommender'
]
