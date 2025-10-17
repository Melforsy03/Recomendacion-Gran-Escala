from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import json
import redis
import os

class DockerDataStream:
    def __init__(self):
        # Conectar a Redis si está disponible
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ Conectado a Redis")
            self.use_redis = True
        except:
            print("❌ Redis no disponible, usando datos simulados")
            self.use_redis = False
        
        # Cargar películas reales desde JSON
        self.movies = self.load_movies_from_json()
        self.interaction_types = ["click", "view", "rating", "purchase"]
        
        # Estructuras para datos
        self.data = {
            'timestamps': [],
            'active_users': [],
            'interactions_by_type': {itype: [] for itype in self.interaction_types},
            'movie_popularity': {movie['name']: [] for movie in self.movies},
            'avg_ratings': {movie['name']: [] for movie in self.movies},
            'genre_popularity': {},
            'conversion_rates': []
        }
        
        # Inicializar géneros
        all_genres = set()
        for movie in self.movies:
            genres = movie['genre'].split('/')
            for genre in genres:
                all_genres.add(genre)
                self.data['genre_popularity'][genre] = []
        
        print(f"✅ Dashboard cargó {len(self.movies)} películas y {len(all_genres)} géneros")
        print(f"🎯 Modo: {'Redis' if self.use_redis else 'Simulado'}")
    
    def load_movies_from_json(self):
        """Carga películas desde el archivo JSON"""
        try:
            with open('movies.json', 'r') as f:
                movies_data = json.load(f)
            
            formatted_movies = []
            for movie in movies_data:
                formatted_movies.append({
                    "ID": movie["ID"],
                    "name": movie["name"],
                    "genre": f"{movie['genre_1']}/{movie['genre_2']}",
                    "puan": movie["puan"],
                    "pop": movie["pop"],
                    "description": movie["description"]
                })
            
            return formatted_movies
            
        except FileNotFoundError:
            print("❌ ERROR: No se encontró movies.json")
            return []
    
    def get_redis_metrics(self):
        """Obtiene métricas desde Redis"""
        try:
            # Aquí iría la lógica para obtener métricas reales desde Redis
            # Por ahora simulamos datos realistas
            return self.generate_realistic_data()
        except:
            return self.generate_realistic_data()
    
    def generate_realistic_data(self):
        """Genera datos realistas basados en las películas del JSON"""
        current_time = datetime.now()
        
        # Simular datos basados en popularidad real de las películas
        active_users = random.randint(40, 120)
        
        # Las películas más populares tienen más interacciones
        interactions_by_type = {}
        total_interactions = 0
        
        for itype in self.interaction_types:
            base_count = random.randint(3, 15)
            if itype == "click":
                base_count = random.randint(10, 25)
            elif itype == "view":
                base_count = random.randint(8, 20)
            interactions_by_type[itype] = base_count
            total_interactions += base_count
        
        # Distribuir interacciones entre películas según su popularidad
        movie_interactions = {}
        for movie in self.movies:
            popularity_factor = movie['pop'] / 100.0
            base_interactions = max(1, int(total_interactions * popularity_factor * 0.3))
            variation = random.randint(-2, 2)
            movie_interactions[movie['name']] = max(0, base_interactions + variation)
        
        # Ratings realistas
        movie_ratings = {}
        for movie in self.movies:
            base_rating = movie['puan'] / 2
            variation = random.uniform(-0.3, 0.3)
            movie_ratings[movie['name']] = round(max(1.0, min(5.0, base_rating + variation)), 2)
        
        # Popularidad de géneros
        genre_interactions = {}
        for movie in self.movies:
            genres = movie['genre'].split('/')
            interactions = movie_interactions.get(movie['name'], 0)
            for genre in genres:
                genre_interactions[genre] = genre_interactions.get(genre, 0) + interactions
        
        # Agregar a datos históricos
        self.data['timestamps'].append(current_time)
        self.data['active_users'].append(active_users)
        
        for itype in self.interaction_types:
            self.data['interactions_by_type'][itype].append(interactions_by_type[itype])
            if len(self.data['interactions_by_type'][itype]) > 20:
                self.data['interactions_by_type'][itype].pop(0)
        
        for movie_name in movie_interactions:
            self.data['movie_popularity'][movie_name].append(movie_interactions[movie_name])
            self.data['avg_ratings'][movie_name].append(movie_ratings[movie_name])
            
            if len(self.data['movie_popularity'][movie_name]) > 20:
                self.data['movie_popularity'][movie_name].pop(0)
            if len(self.data['avg_ratings'][movie_name]) > 20:
                self.data['avg_ratings'][movie_name].pop(0)
        
        for genre in genre_interactions:
            if genre in self.data['genre_popularity']:
                self.data['genre_popularity'][genre].append(genre_interactions[genre])
                if len(self.data['genre_popularity'][genre]) > 20:
                    self.data['genre_popularity'][genre].pop(0)
        
        # Calcular tasa de conversión
        clicks = interactions_by_type.get('click', 1)
        purchases = interactions_by_type.get('purchase', 0)
        conversion_rate = (purchases / clicks) * 100
        self.data['conversion_rates'].append(conversion_rate)
        if len(self.data['conversion_rates']) > 20:
            self.data['conversion_rates'].pop(0)
        
        # Mantener sólo últimos 20 timestamps
        if len(self.data['timestamps']) > 20:
            self.data['timestamps'].pop(0)
            self.data['active_users'].pop(0)
            # dashboard.py - AGREGAR ESTE MÉTODO A LA CLASE DockerDataStream

    def get_real_redis_metrics(self):
        """Obtener métricas reales desde Redis"""
        try:
            if not self.redis_client:
                return self.generate_realistic_data()
            
            # Obtener métricas de Redis
            total_interactions = int(self.redis_client.get('total_interactions') or 0)
            active_users = self.redis_client.zcount('active_users', 
                                                    datetime.now().timestamp() - 300, 
                                                    '+inf')
            
            # Obtener interacciones por tipo
            interactions_by_type = {}
            for itype in self.interaction_types:
                count = self.redis_client.get(f'total_{itype}') or 0
                interactions_by_type[itype] = int(count)
            
            # Obtener popularidad de películas
            movie_interactions = {}
            for movie in self.movies:
                movie_key = f"movie:{movie['ID']}"
                total = self.redis_client.hget(movie_key, 'total_interactions')
                movie_interactions[movie['name']] = int(total) if total else 0
            
            # Ratings promedio
            movie_ratings = {}
            for movie in self.movies:
                rating_key = f"ratings:{movie['ID']}"
                ratings = self.redis_client.lrange(rating_key, 0, -1)
                if ratings:
                    avg_rating = sum(float(r) for r in ratings) / len(ratings)
                    movie_ratings[movie['name']] = round(avg_rating, 2)
                else:
                    movie_ratings[movie['name']] = movie['puan'] / 2
            
            # Actualizar estructura de datos
            current_time = datetime.now()
            self.data['timestamps'].append(current_time)
            self.data['active_users'].append(active_users)
            
            for itype in self.interaction_types:
                self.data['interactions_by_type'][itype].append(interactions_by_type.get(itype, 0))
                if len(self.data['interactions_by_type'][itype]) > 20:
                    self.data['interactions_by_type'][itype].pop(0)
            
            for movie_name in movie_interactions:
                self.data['movie_popularity'][movie_name].append(movie_interactions[movie_name])
                self.data['avg_ratings'][movie_name].append(movie_ratings.get(movie_name, 3.0))
                
                if len(self.data['movie_popularity'][movie_name]) > 20:
                    self.data['movie_popularity'][movie_name].pop(0)
                if len(self.data['avg_ratings'][movie_name]) > 20:
                    self.data['avg_ratings'][movie_name].pop(0)
            
            # Limitar historial
            if len(self.data['timestamps']) > 20:
                self.data['timestamps'].pop(0)
                self.data['active_users'].pop(0)
                
        except Exception as e:
            print(f"❌ Error obteniendo métricas de Redis: {e}")
            self.generate_realistic_data()

# Crear aplicación Dash
app = Dash(__name__)
data_stream = DockerDataStream()

# Layout del dashboard
app.layout = html.Div([
    html.H1("🎬 Sistema de Recomendación ", 
            style={'textAlign': 'center', 'color': '#2E86AB', 'marginBottom': '20px'}),
    
    
    # Métricas instantáneas
    html.Div([
        html.Div(id='live-metrics', style={
            'display': 'flex', 
            'justifyContent': 'space-around',
            'margin': '20px',
            'flexWrap': 'wrap'
        })
    ]),
    
    # Primera fila de gráficas
    html.Div([
        html.Div([
            dcc.Graph(id='active-users-chart'),
            dcc.Interval(id='interval-update', interval=3000, n_intervals=0)
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        html.Div([
            dcc.Graph(id='interactions-chart'),
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'}),
    ], style={'marginBottom': '20px'}),
    
    # Segunda fila de gráficas
    html.Div([
        html.Div([
            dcc.Graph(id='movie-popularity-chart'),
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        html.Div([
            dcc.Graph(id='ratings-chart'),
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'}),
    ], style={'marginBottom': '20px'}),
    
    # Información del sistema
    html.Div([
        html.Div([
            html.H4("📊 Información del Sistema", style={'color': '#2E86AB'}),
            html.P(f"• 🎬 {len(data_stream.movies)} películas cargadas"),
           
            html.P("• 📡 Kafka para streaming en tiempo real"),
            html.P(f"• 🔴 Redis: {'Conectado' if data_stream.use_redis else 'Simulado'}"),
            html.P("• ⚡ Actualización cada 3 segundos"),
        ], style={'padding': '15px', 'background': '#f8f9fa', 'borderRadius': '10px', 'width': '100%'})
    ]),
    
], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# Callback para actualizar todas las gráficas
@app.callback(
    [Output('active-users-chart', 'figure'),
     Output('interactions-chart', 'figure'),
     Output('movie-popularity-chart', 'figure'),
     Output('ratings-chart', 'figure'),
     Output('live-metrics', 'children')],
    Input('interval-update', 'n_intervals')
)
def update_dashboard(n):
    # Generar nuevos datos
    if data_stream.use_redis:
        data_stream.get_real_redis_metrics()
    else:
        data_stream.generate_realistic_data()
    
    # 1. Gráfica de usuarios activos
    active_users_fig = {
        'data': [go.Scatter(
            x=data_stream.data['timestamps'],
            y=data_stream.data['active_users'],
            mode='lines+markers',
            name='Usuarios Activos',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=6)
        )],
        'layout': go.Layout(
            title='👥 Usuarios Activos',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Número de Usuarios'},
            height=300,
            plot_bgcolor='rgba(240,240,240,0.8)'
        )
    }
    
    # 2. Gráfica de interacciones por tipo
    interactions_data = []
    colors = ['#A23B72', '#F18F01', '#C73E1D', '#3F7CAC']
    for i, itype in enumerate(data_stream.interaction_types):
        interactions_data.append(go.Bar(
            name=itype.capitalize(),
            x=data_stream.data['timestamps'][-8:],
            y=data_stream.data['interactions_by_type'][itype][-8:],
            marker_color=colors[i % len(colors)]
        ))
    
    interactions_fig = {
        'data': interactions_data,
        'layout': go.Layout(
            title='📊 Interacciones por Tipo',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Número de Interacciones'},
            barmode='stack',
            height=300,
            plot_bgcolor='rgba(240,240,240,0.8)'
        )
    }
    
    # 3. Gráfica de popularidad de películas (top 5)
    popularity_data = []
    movie_colors = ['#2E86AB', '#A23B72', '#F18F01', '#3F7CAC', '#C73E1D']
    
    current_popularity = {}
    for movie in data_stream.movies:
        movie_name = movie['name']
        if data_stream.data['movie_popularity'][movie_name]:
            current_popularity[movie_name] = data_stream.data['movie_popularity'][movie_name][-1]
    
    top_movies = sorted(current_popularity.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for i, (movie_name, _) in enumerate(top_movies):
        popularity_data.append(go.Scatter(
            name=movie_name,
            x=data_stream.data['timestamps'],
            y=data_stream.data['movie_popularity'][movie_name],
            mode='lines+markers',
            line=dict(color=movie_colors[i % len(movie_colors)], width=2),
            marker=dict(size=4)
        ))
    
    popularity_fig = {
        'data': popularity_data,
        'layout': go.Layout(
            title='🎬 Top 5 Películas Más Populares',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Interacciones'},
            height=300,
            plot_bgcolor='rgba(240,240,240,0.8)'
        )
    }
    
    # 4. Gráfica de ratings (primeras 5 películas)
    ratings_data = []
    for i, movie in enumerate(data_stream.movies[:5]):
        movie_name = movie['name']
        if data_stream.data['avg_ratings'][movie_name]:
            ratings_data.append(go.Scatter(
                name=movie_name,
                x=data_stream.data['timestamps'],
                y=data_stream.data['avg_ratings'][movie_name],
                mode='lines+markers',
                line=dict(color=movie_colors[i % len(movie_colors)], width=2),
                marker=dict(size=4)
            ))
    
    ratings_fig = {
        'data': ratings_data,
        'layout': go.Layout(
            title='⭐ Ratings Promedio',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Rating', 'range': [3, 5]},
            height=300,
            plot_bgcolor='rgba(240,240,240,0.8)'
        )
    }
    
    # Métricas instantáneas
    current_active = data_stream.data['active_users'][-1] if data_stream.data['active_users'] else 0
    total_interactions = sum(data_stream.data['interactions_by_type'][itype][-1] for itype in data_stream.interaction_types)
    
    current_movie_pop = {}
    for movie in data_stream.movies:
        movie_name = movie['name']
        if data_stream.data['movie_popularity'][movie_name]:
            current_movie_pop[movie_name] = data_stream.data['movie_popularity'][movie_name][-1]
    
    most_popular_movie = max(current_movie_pop.items(), key=lambda x: x[1], default=("N/A", 0))[0]
    
    metrics = [
        html.Div([
            html.H4("👥 Usuarios", style={'color': '#2E86AB', 'textAlign': 'center'}),
            html.H2(f"{current_active}", style={'color': '#2E86AB', 'textAlign': 'center'}),
            html.P("activos", style={'textAlign': 'center', 'color': '#666', 'margin': 0, 'fontSize': '0.9em'})
        ], style={'textAlign': 'center', 'padding': '15px', 'border': '2px solid #2E86AB', 'borderRadius': '10px', 'width': '23%', 'margin': '5px'}),
        
        html.Div([
            html.H4("📊 Interacciones", style={'color': '#A23B72', 'textAlign': 'center'}),
            html.H2(f"{total_interactions}", style={'color': '#A23B72', 'textAlign': 'center'}),
            html.P("totales", style={'textAlign': 'center', 'color': '#666', 'margin': 0, 'fontSize': '0.9em'})
        ], style={'textAlign': 'center', 'padding': '15px', 'border': '2px solid #A23B72', 'borderRadius': '10px', 'width': '23%', 'margin': '5px'}),
        
        html.Div([
            html.H4("🎬 Top Movie", style={'color': '#F18F01', 'textAlign': 'center'}),
            html.H2(f"{most_popular_movie[:10]}...", style={'color': '#F18F01', 'textAlign': 'center', 'fontSize': '1.3em'}),
            html.P("más popular", style={'textAlign': 'center', 'color': '#666', 'margin': 0, 'fontSize': '0.9em'})
        ], style={'textAlign': 'center', 'padding': '15px', 'border': '2px solid #F18F01', 'borderRadius': '10px', 'width': '23%', 'margin': '5px'}),
        
        html.Div([
            html.H4("Sistema", style={'color': '#34C759', 'textAlign': 'center'}),
            html.H2(f"{len(data_stream.movies)}", style={'color': '#34C759', 'textAlign': 'center'}),
            html.P("películas", style={'textAlign': 'center', 'color': '#666', 'margin': 0, 'fontSize': '0.9em'})
        ], style={'textAlign': 'center', 'padding': '15px', 'border': '2px solid #34C759', 'borderRadius': '10px', 'width': '23%', 'margin': '5px'})
    ]
    
    return active_users_fig, interactions_fig, popularity_fig, ratings_fig, metrics

if __name__ == '__main__':
    print("🐳 Iniciando Dashboard  en http://localhost:8050")
    print("📊 Abre tu navegador y ve a: http://localhost:8050")
    print(f"🎬 Usando dataset real con {len(data_stream.movies)} películas")
    print("🛑 Presiona Ctrl+C para detener")
    app.run(debug=False, host='0.0.0.0', port=8050)
