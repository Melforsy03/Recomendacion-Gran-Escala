#!/usr/bin/env python3
"""
Script para convertir el archivo JSON de películas a múltiples archivos CSV
para comparación con el dataset real de MovieLens.

Autor: Sistema de Recomendación Gran Escala
Fecha: 2025-10-29
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

def load_json_data(json_file):
    """Carga el archivo JSON de películas."""
    print(f"📂 Cargando archivo JSON: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Archivo cargado: {len(data)} películas encontradas")
        return data
    except FileNotFoundError:
        print(f"✗ Error: Archivo no encontrado: {json_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error al decodificar JSON: {e}")
        sys.exit(1)

def create_movies_csv(data, output_dir):
    """Crea el archivo CSV de películas (synthetic_movies.csv)."""
    print("\n📊 Generando synthetic_movies.csv...")
    
    movies_data = []
    for movie in data:
        # Unir géneros con pipe (|)
        genres = '|'.join(movie.get('genres', []))
        
        movies_data.append({
            'movieId': movie.get('movieId'),
            'title': movie.get('title', ''),
            'genres': genres
        })
    
    df_movies = pd.DataFrame(movies_data)
    
    # Extraer año del título
    df_movies['year'] = df_movies['title'].str.extract(r'\((\d{4})\)')
    df_movies['year'] = pd.to_numeric(df_movies['year'], errors='coerce')
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_movies.csv')
    df_movies.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_movies)}")
    print(f"  - Columnas: {list(df_movies.columns)}")
    
    return df_movies

def create_ratings_csv(data, output_dir, n_ratings_per_movie=100):
    """
    Crea el archivo CSV de ratings sintéticos (synthetic_ratings.csv).
    
    Genera ratings sintéticos basados en:
    - avg_rating: promedio de rating de la película
    - rating_count: número de ratings reales
    """
    print(f"\n📊 Generando synthetic_ratings.csv...")
    print(f"  Estrategia: ~{n_ratings_per_movie} ratings por película")
    
    ratings_data = []
    user_id_counter = 1
    
    for movie in data:
        movie_id = movie.get('movieId')
        avg_rating = movie.get('avg_rating', 3.5)
        rating_count = movie.get('rating_count', n_ratings_per_movie)
        
        # Limitar número de ratings por película para mantener tamaño manejable
        num_ratings = min(rating_count, n_ratings_per_movie)
        
        # Generar ratings con distribución normal centrada en avg_rating
        std_dev = 1.0  # Desviación estándar típica de ratings
        
        for _ in range(num_ratings):
            # Generar rating con distribución normal
            rating = np.random.normal(avg_rating, std_dev)
            
            # Redondear a valores válidos (0.5 - 5.0) con incrementos de 0.5
            rating = max(0.5, min(5.0, rating))
            rating = round(rating * 2) / 2  # Redondear a 0.5 más cercano
            
            # Generar timestamp aleatorio (últimos 10 años)
            days_ago = np.random.randint(0, 365 * 10)
            timestamp = datetime.now() - pd.Timedelta(days=days_ago)
            
            ratings_data.append({
                'userId': user_id_counter,
                'movieId': movie_id,
                'rating': rating,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Incrementar userId (simular diferentes usuarios)
            user_id_counter += 1
            if user_id_counter > 10000:  # Resetear para reutilizar usuarios
                user_id_counter = 1
    
    df_ratings = pd.DataFrame(ratings_data)
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_ratings.csv')
    df_ratings.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_ratings)}")
    print(f"  - Columnas: {list(df_ratings.columns)}")
    print(f"  - Usuarios únicos: {df_ratings['userId'].nunique()}")
    print(f"  - Películas únicas: {df_ratings['movieId'].nunique()}")
    print(f"  - Rating promedio: {df_ratings['rating'].mean():.4f}")
    
    return df_ratings

def create_tags_csv(data, output_dir, tags_per_movie=5):
    """
    Crea el archivo CSV de tags sintéticos (synthetic_tags.csv).
    
    Utiliza los top_tags del JSON original.
    """
    print(f"\n📊 Generando synthetic_tags.csv...")
    print(f"  Estrategia: hasta {tags_per_movie} tags por película")
    
    tags_data = []
    user_id_counter = 1
    
    for movie in data:
        movie_id = movie.get('movieId')
        top_tags = movie.get('top_tags', [])
        
        # Tomar hasta tags_per_movie
        tags_to_use = top_tags[:tags_per_movie]
        
        for tag in tags_to_use:
            # Generar timestamp aleatorio
            days_ago = np.random.randint(0, 365 * 10)
            timestamp = datetime.now() - pd.Timedelta(days=days_ago)
            
            tags_data.append({
                'userId': user_id_counter,
                'movieId': movie_id,
                'tag': tag,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Incrementar userId
            user_id_counter += 1
            if user_id_counter > 5000:  # Resetear
                user_id_counter = 1
    
    df_tags = pd.DataFrame(tags_data)
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_tags.csv')
    df_tags.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_tags)}")
    print(f"  - Columnas: {list(df_tags.columns)}")
    print(f"  - Tags únicos: {df_tags['tag'].nunique()}")
    print(f"  - Usuarios únicos: {df_tags['userId'].nunique()}")
    
    return df_tags

def create_links_csv(data, output_dir):
    """Crea el archivo CSV de links (synthetic_links.csv)."""
    print("\n📊 Generando synthetic_links.csv...")
    
    links_data = []
    for movie in data:
        links_data.append({
            'movieId': movie.get('movieId'),
            'imdbId': movie.get('imdbId'),
            'tmdbId': movie.get('tmdbId')
        })
    
    df_links = pd.DataFrame(links_data)
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_links.csv')
    df_links.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_links)}")
    print(f"  - Columnas: {list(df_links.columns)}")
    
    return df_links

def create_genome_scores_csv(data, output_dir, max_movies=1000):
    """
    Crea el archivo CSV de genome scores (synthetic_genome_scores.csv).
    
    Nota: Este archivo puede ser muy grande, se limita a max_movies películas.
    """
    print(f"\n📊 Generando synthetic_genome_scores.csv...")
    print(f"  ⚠ Limitado a {max_movies} películas para evitar archivo muy grande")
    
    genome_data = []
    tag_id_map = {}
    current_tag_id = 1
    
    # Procesar solo las primeras max_movies películas
    for i, movie in enumerate(data[:max_movies]):
        movie_id = movie.get('movieId')
        genome_relevance = movie.get('genome_relevance', [])
        
        for tag_name, relevance in genome_relevance:
            # Asignar ID único a cada tag
            if tag_name not in tag_id_map:
                tag_id_map[tag_name] = current_tag_id
                current_tag_id += 1
            
            tag_id = tag_id_map[tag_name]
            
            genome_data.append({
                'movieId': movie_id,
                'tagId': tag_id,
                'relevance': relevance
            })
        
        # Mostrar progreso
        if (i + 1) % 100 == 0:
            print(f"  Procesadas: {i + 1}/{max_movies} películas")
    
    df_genome_scores = pd.DataFrame(genome_data)
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_genome_scores.csv')
    df_genome_scores.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_genome_scores)}")
    print(f"  - Columnas: {list(df_genome_scores.columns)}")
    print(f"  - Tags únicos: {df_genome_scores['tagId'].nunique()}")
    
    return df_genome_scores, tag_id_map

def create_genome_tags_csv(tag_id_map, output_dir):
    """Crea el archivo CSV de genome tags (synthetic_genome_tags.csv)."""
    print("\n📊 Generando synthetic_genome_tags.csv...")
    
    genome_tags_data = [
        {'tagId': tag_id, 'tag': tag_name}
        for tag_name, tag_id in tag_id_map.items()
    ]
    
    df_genome_tags = pd.DataFrame(genome_tags_data)
    df_genome_tags = df_genome_tags.sort_values('tagId')
    
    # Guardar CSV
    output_file = os.path.join(output_dir, 'synthetic_genome_tags.csv')
    df_genome_tags.to_csv(output_file, index=False)
    
    print(f"✓ Archivo creado: {output_file}")
    print(f"  - Registros: {len(df_genome_tags)}")
    print(f"  - Columnas: {list(df_genome_tags.columns)}")
    
    return df_genome_tags

def main():
    """Función principal."""
    print("=" * 80)
    print("CONVERTIDOR JSON A CSV - DATASET SINTÉTICO")
    print("=" * 80)
    
    # Configuración
    json_file = '/home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala/electivo/exports/movies_data_20251029_212350.json'
    output_dir = '/home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala/electivo/outputs/eda/'
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Cargar datos JSON
    data = load_json_data(json_file)
    
    # Generar CSVs
    df_movies = create_movies_csv(data, output_dir)
    df_ratings = create_ratings_csv(data, output_dir, n_ratings_per_movie=50)
    df_tags = create_tags_csv(data, output_dir, tags_per_movie=3)
    df_links = create_links_csv(data, output_dir)
    df_genome_scores, tag_id_map = create_genome_scores_csv(data, output_dir, max_movies=500)
    df_genome_tags = create_genome_tags_csv(tag_id_map, output_dir)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE ARCHIVOS GENERADOS")
    print("=" * 80)
    print(f"\n📁 Directorio de salida: {output_dir}")
    print("\n📊 Archivos CSV creados:")
    print(f"  1. synthetic_movies.csv        - {len(df_movies):,} registros")
    print(f"  2. synthetic_ratings.csv       - {len(df_ratings):,} registros")
    print(f"  3. synthetic_tags.csv          - {len(df_tags):,} registros")
    print(f"  4. synthetic_links.csv         - {len(df_links):,} registros")
    print(f"  5. synthetic_genome_scores.csv - {len(df_genome_scores):,} registros")
    print(f"  6. synthetic_genome_tags.csv   - {len(df_genome_tags):,} registros")
    
    print("\n✓ Conversión completada exitosamente")
    print("\n💡 Siguiente paso:")
    print("   Ejecutar notebook: comparacion_datasets_real_vs_sintetico.ipynb")
    print("=" * 80)

if __name__ == "__main__":
    main()
