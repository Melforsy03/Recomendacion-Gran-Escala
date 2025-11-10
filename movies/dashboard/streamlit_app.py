"""
Dashboard de Métricas en Tiempo Real con Streamlit
==================================================

Dashboard interactivo para visualizar métricas de streaming del sistema
de recomendación de películas.

Características:
- Métricas en tiempo real (throughput, avg rating, percentiles)
- Top-N películas trending
- Distribución por género
- Gráficos temporales
- Auto-refresh

Fase 9: Sistema de Recomendación de Películas a Gran Escala
Fecha: 3 de noviembre de 2025
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json

# ==========================================
# Configuración
# ==========================================

API_BASE_URL = "http://api:8000"  # Dentro de Docker network
# API_BASE_URL = "http://localhost:8000"  # Para desarrollo local

REFRESH_INTERVAL = 5  # Segundos entre actualizaciones
TOP_N_DISPLAY = 20  # Películas a mostrar en top-N

# Configuración de página
st.set_page_config(
    page_title="Dashboard - Sistema de Recomendación",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# Funciones de API
# ==========================================

@st.cache_data(ttl=REFRESH_INTERVAL)
def get_metrics_summary():
    """Obtiene resumen de métricas"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/summary", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error obteniendo resumen: {e}")
        return None

@st.cache_data(ttl=REFRESH_INTERVAL)
def get_topn_movies(limit=20):
    """Obtiene top-N películas"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/metrics/topn",
            params={"limit": limit},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error obteniendo top-N: {e}")
        return None

@st.cache_data(ttl=REFRESH_INTERVAL)
def get_genres_metrics():
    """Obtiene métricas por género"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/genres", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error obteniendo métricas por género: {e}")
        return None

@st.cache_data(ttl=REFRESH_INTERVAL)
def get_metrics_history(limit=50):
    """Obtiene historial de métricas"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/metrics/history",
            params={"limit": limit},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error obteniendo historial: {e}")
        return None

def check_api_health():
    """Verifica salud de la API"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/health", timeout=2)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# Layout Principal
# ==========================================

def main():
    """Función principal del dashboard"""
    
    # Header
    st.title("🎬 Dashboard de Métricas en Tiempo Real")
    st.markdown("Sistema de Recomendación de Películas a Gran Escala - **Fase 9**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Verificar salud de la API
        health = check_api_health()
        if health.get("status") == "healthy":
            st.success("✅ API Conectada")
            if health.get("last_update"):
                st.info(f"Última actualización: {health['last_update']}")
        elif health.get("status") == "no_data":
            st.warning("⚠️ API conectada pero sin datos")
            st.info("Ejecuta el procesador de streaming")
        else:
            st.error("❌ API no disponible")
            st.stop()
        
        st.divider()
        
        # Controles
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        
        if auto_refresh:
            refresh_rate = st.slider(
                "Intervalo de actualización (seg)",
                min_value=2,
                max_value=30,
                value=REFRESH_INTERVAL
            )
        
        st.divider()
        
        st.markdown("### 📊 Secciones")
        st.markdown("""
        - **Métricas Globales**: Resumen en tiempo real
        - **Top Películas**: Más populares
        - **Análisis por Género**: Distribución
        - **Historial**: Tendencias temporales
        """)
        
        st.divider()
        
        if st.button("🔄 Refrescar Ahora"):
            st.cache_data.clear()
            st.rerun()
    
    # ==========================================
    # Sección 1: Métricas Globales
    # ==========================================
    
    st.header("📊 Métricas Globales")
    
    summary = get_metrics_summary()
    
    if summary:
        # KPIs en columnas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Ratings",
                value=f"{summary['total_ratings']:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Rating Promedio",
                value=f"{summary['avg_rating']:.2f}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Mediana (P50)",
                value=f"{summary['p50_rating']:.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Percentil 95",
                value=f"{summary['p95_rating']:.2f}",
                delta=None
            )
        
        # Información de ventana
        if summary.get('window_start') and summary.get('window_end'):
            st.caption(
                f"**Ventana {summary.get('window_type', 'N/A')}**: "
                f"{summary['window_start']} → {summary['window_end']}"
            )
    else:
        st.warning("No hay métricas globales disponibles")
    
    st.divider()
    
    # ==========================================
    # Sección 2: Top-N Películas
    # ==========================================
    
    st.header("🏆 Top Películas Trending")
    
    topn_data = get_topn_movies(TOP_N_DISPLAY)
    
    if topn_data and topn_data.get('movies'):
        movies = topn_data['movies']
        
        # Verificar si movies es una lista de IDs o de objetos
        if movies and isinstance(movies[0], (int, str)):
            # Es una lista de IDs - crear estructura simple
            movie_list = [{"movieId": mid, "title": f"Movie {mid}", "rank": i+1} 
                         for i, mid in enumerate(movies[:TOP_N_DISPLAY])]
            df_movies = pd.DataFrame(movie_list)
            
            # Gráfico de barras simple mostrando ranking
            fig = px.bar(
                df_movies.head(10),
                x='rank',
                y='title',
                orientation='h',
                title=f"Top 10 Películas Más Frecuentes",
                labels={'rank': 'Posición en Ranking', 'title': 'Película'},
                color='rank',
                color_continuous_scale='Viridis_r'
            )
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla simple con IDs
            st.subheader(f"Top {len(movies)} Películas (IDs)")
            
            df_display = df_movies[['rank', 'movieId']].copy()
            df_display.columns = ['Posición', 'Movie ID']
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
        else:
            # Es una lista de objetos completos - usar visualización original
            df_movies = pd.DataFrame(movies)
            
            # Gráfico de barras horizontal
            fig = px.bar(
                df_movies.head(10),
                x='score',
                y='title',
                orientation='h',
                title=f"Top 10 Películas por Score",
                labels={'score': 'Score (Count × Avg Rating)', 'title': 'Película'},
                color='avg_rating',
                color_continuous_scale='Viridis'
            )
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla detallada
            st.subheader(f"Top {len(movies)} Películas (Detalles)")
            
            df_display = df_movies[['title', 'rating_count', 'avg_rating', 'score']].copy()
            df_display.columns = ['Película', 'Num. Ratings', 'Rating Promedio', 'Score']
            df_display['Rating Promedio'] = df_display['Rating Promedio'].round(2)
            df_display['Score'] = df_display['Score'].round(2)
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("No hay datos de top-N disponibles")
    
    st.divider()
    
    # ==========================================
    # Sección 3: Análisis por Género
    # ==========================================
    
    st.header("🎭 Análisis por Género")
    
    genres_data = get_genres_metrics()
    
    if genres_data and genres_data.get('genres'):
        genres = genres_data['genres']
        
        # Convertir a DataFrame
        genre_list = []
        for genre_name, stats in genres.items():
            genre_list.append({
                'Género': genre_name,
                'Total Ratings': stats.get('count', 0),
                'Rating Promedio': stats.get('avg_rating', 0),
                'Películas Únicas': stats.get('unique_movies', 0)
            })
        
        df_genres = pd.DataFrame(genre_list)
        df_genres = df_genres.sort_values('Total Ratings', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de pastel - Distribución de ratings
            fig_pie = px.pie(
                df_genres.head(10),
                values='Total Ratings',
                names='Género',
                title='Distribución de Ratings por Género (Top 10)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Gráfico de barras - Rating promedio
            fig_bar = px.bar(
                df_genres.head(10),
                x='Género',
                y='Rating Promedio',
                title='Rating Promedio por Género (Top 10)',
                color='Rating Promedio',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tabla completa
        st.subheader("Estadísticas Completas por Género")
        df_genres['Rating Promedio'] = df_genres['Rating Promedio'].round(2)
        st.dataframe(df_genres, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay métricas por género disponibles")
    
    st.divider()
    
    # ==========================================
    # Sección 4: Historial Temporal
    # ==========================================
    
    st.header("📈 Historial Temporal")
    
    history_data = get_metrics_history(100)
    
    if history_data and history_data.get('history'):
        history = history_data['history']
        
        # Filtrar solo eventos de tipo summary
        summary_events = [
            h for h in history 
            if h.get('type') == 'summary' and h.get('data')
        ]
        
        if summary_events:
            # Convertir a DataFrame
            df_history = pd.DataFrame([
                {
                    'timestamp': h['timestamp'],
                    'total_ratings': h['data'].get('total_ratings', 0),
                    'avg_rating': h['data'].get('avg_rating', 0),
                    'p50_rating': h['data'].get('p50_rating', 0),
                    'p95_rating': h['data'].get('p95_rating', 0)
                }
                for h in summary_events
            ])
            
            df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
            df_history = df_history.sort_values('timestamp')
            
            # Gráfico de línea - Throughput
            fig_throughput = go.Figure()
            fig_throughput.add_trace(go.Scatter(
                x=df_history['timestamp'],
                y=df_history['total_ratings'],
                mode='lines+markers',
                name='Total Ratings',
                line=dict(color='#1f77b4', width=2)
            ))
            fig_throughput.update_layout(
                title='Throughput de Ratings en el Tiempo',
                xaxis_title='Timestamp',
                yaxis_title='Total Ratings',
                hovermode='x unified'
            )
            st.plotly_chart(fig_throughput, use_container_width=True)
            
            # Gráfico de línea - Ratings y percentiles
            fig_ratings = go.Figure()
            fig_ratings.add_trace(go.Scatter(
                x=df_history['timestamp'],
                y=df_history['avg_rating'],
                mode='lines+markers',
                name='Promedio',
                line=dict(color='#2ca02c', width=2)
            ))
            fig_ratings.add_trace(go.Scatter(
                x=df_history['timestamp'],
                y=df_history['p50_rating'],
                mode='lines',
                name='P50 (Mediana)',
                line=dict(color='#ff7f0e', width=1, dash='dash')
            ))
            fig_ratings.add_trace(go.Scatter(
                x=df_history['timestamp'],
                y=df_history['p95_rating'],
                mode='lines',
                name='P95',
                line=dict(color='#d62728', width=1, dash='dot')
            ))
            fig_ratings.update_layout(
                title='Evolución de Ratings en el Tiempo',
                xaxis_title='Timestamp',
                yaxis_title='Rating',
                hovermode='x unified',
                yaxis=dict(range=[0, 5])
            )
            st.plotly_chart(fig_ratings, use_container_width=True)
        else:
            st.info("No hay suficiente historial de métricas aún")
    else:
        st.warning("No hay datos de historial disponibles")
    
    # ==========================================
    # Auto-refresh
    # ==========================================
    
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

# ==========================================
# Entry Point
# ==========================================

if __name__ == "__main__":
    main()
