#!/usr/bin/env python3
import threading, json, time, collections
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

import dash
from dash import dcc, html
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime

KAFKA_BOOTSTRAP = 'localhost:9092'
TOPICS = [
    'metrics.throughput', 
    'metrics.top_rated', 
    'metrics.genre_analytics',
    'metrics.popular_tags',
    'metrics.catalog_stats',
    'metrics.rating_dist'
]

# Buffers en memoria mejorados - TODAS INICIALIZADAS CORRECTAMENTE
throughput_data = collections.deque(maxlen=50)
top_rated_data = []
genre_analytics_data = {}
popular_tags_data = []  # ✅ INICIALIZADA CORRECTAMENTE
catalog_stats_data = {}
rating_dist_data = {}

print("🌐 Iniciando Dashboard MovieLens...")
print(f"📡 Conectando a Kafka: {KAFKA_BOOTSTRAP}")
print(f"🎯 Topics: {TOPICS}")

def consume_loop():
    global popular_tags_data  # ✅ CRÍTICO: Declarar como global
    
    consumer = None
    while True:
        try:
            if consumer is None:
                print("🔄 Conectando a Kafka...")
                consumer = KafkaConsumer(
                    *TOPICS,
                    bootstrap_servers=[KAFKA_BOOTSTRAP],
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id='dashboard-group',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    consumer_timeout_ms=5000
                )
                print("✅ Conectado a Kafka - Esperando datos...")
            
            for msg in consumer:
                topic = msg.topic
                try:
                    data = msg.value
                    print(f"📥 Recibido de {topic}: {type(data)}")
                    
                    if topic == 'metrics.throughput':
                        throughput_data.append({
                            'timestamp': datetime.now(),
                            'events_per_second': data.get('events_per_second', 0),
                            'total_events': data.get('total_events', 0),
                            'window_start': data.get('window_start')
                        })
                        print(f"📊 Throughput: {data.get('events_per_second', 0)} eventos/seg")
                        
                    elif topic == 'metrics.top_rated':
                        # ✅ CORREGIDO: Mejor manejo de top_rated_data
                        if isinstance(data, list):
                            # Si es una lista, reemplazar todo
                            top_rated_data.clear()
                            top_rated_data.extend([m for m in data if m.get('movieId')])
                        elif isinstance(data, dict) and data.get('movieId'):
                            # Si es un dict individual, agregarlo si no existe
                            existing_ids = [m.get('movieId') for m in top_rated_data]
                            if data.get('movieId') not in existing_ids:
                                top_rated_data.append(data)
                                # Mantener máximo 20 películas
                                if len(top_rated_data) > 20:
                                    top_rated_data.pop(0)
                        
                        print(f"🏆 Top rated: {len(top_rated_data)} películas")
                        if top_rated_data:
                            print(f"   Ejemplo: {top_rated_data[0].get('title', 'N/A')} - {top_rated_data[0].get('avg_rating', 0)}")
                        
                    elif topic == 'metrics.genre_analytics':
                        genre = data.get('genre')
                        if genre:
                            genre_analytics_data[genre] = {
                                'avg_rating': data.get('avg_rating', 0),
                                'total_votes': data.get('total_votes', 0),
                                'movie_count': data.get('movie_count', 0)
                            }
                        print(f"🎭 Género {genre}: rating {data.get('avg_rating', 0)}")
                        
                    elif topic == 'metrics.popular_tags':
                        # ✅ CORREGIDO: Usar la variable GLOBAL correctamente
                        try:
                            if data and isinstance(data, dict) and data.get('tag'):
                                # Agregar el nuevo tag a la lista global
                                popular_tags_data.append({
                                    'tag': data.get('tag', ''),
                                    'count': data.get('count', 0)
                                })
                                
                                # Mantener solo los últimos 50 tags para evitar memory leaks
                                if len(popular_tags_data) > 50:
                                    popular_tags_data = popular_tags_data[-50:]
                                
                                print(f"🏷️ Tag agregado: {data.get('tag', 'N/A')} - {data.get('count', 0)}")
                                print(f"📊 Total tags en memoria: {len(popular_tags_data)}")
                                
                        except Exception as e:
                            print(f"❌ Error procesando popular_tags: {e}")
                            # Reinicializar si hay error
                            popular_tags_data = []
                        
                    elif topic == 'metrics.catalog_stats':
                        if data:
                            catalog_stats_data.update(data)
                            print(f"📈 Catalog stats: {data.get('total_movies', 0)} películas")
                        
                    elif topic == 'metrics.rating_dist':
                        if data:
                            rating_dist_data.update(data)
                            print(f"⭐ Rating dist: avg {data.get('overall_avg', 0)}")
                        
                except Exception as e:
                    print(f"❌ Error procesando mensaje de {topic}: {e}")
                    # Log adicional para debugging
                    print(f"   Mensaje: {msg.value if msg else 'No message'}")
                    
        except NoBrokersAvailable:
            print("⚠️ Kafka no disponible, reintentando en 5 segundos...")
            consumer = None
            time.sleep(5)
        except Exception as e:
            print(f"❌ Error en consumer: {e}")
            consumer = None
            time.sleep(3)

# Iniciar consumer en segundo plano
consumer_thread = threading.Thread(target=consume_loop, daemon=True)
consumer_thread.start()

# Crear aplicación Dash
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("🎬 MovieLens Real-Time Analytics Dashboard", 
            style={'textAlign': 'center', 'color': '#2E86AB', 'marginBottom': 30}),
    
    html.Div(id="connection-status", style={'textAlign': 'center', 'marginBottom': 20}),
    
    dcc.Interval(id='tick', interval=3000, n_intervals=0),  # Actualizar cada 3 segundos
    
    # PRIMERA FILA: Throughput y Top Rated
    html.Div([
        html.Div([
            html.H3("🚀 Throughput en Tiempo Real", style={'color': '#A23B72'}),
            dcc.Graph(id='throughput-graph')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        html.Div([
            html.H3("🏆 Top Películas Mejor Valoradas", style={'color': '#F18F01'}),
            html.Div(id='top-rated-table')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ]),
    
    # SEGUNDA FILA: Géneros y Tags
    html.Div([
        html.Div([
            html.H3("🎭 Análisis por Género", style={'color': '#C73E1D'}),
            dcc.Graph(id='genre-analytics-graph')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        html.Div([
            html.H3("🏷️ Tags Más Populares", style={'color': '#3BB273'}),
            html.Div(id='popular-tags-list')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    ]),
    
    # TERCERA FILA: Estadísticas del Catálogo
    html.Div([
        html.Div([
            html.H3("📊 Estadísticas del Catálogo", style={'color': '#6A4C93'}),
            html.Div(id='catalog-stats')
        ], style={'width': '100%', 'textAlign': 'center'})
    ]),
    
], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# Callback para estado de conexión
@app.callback(
    dash.Output('connection-status', 'children'),
    dash.Input('tick', 'n_intervals')
)
def update_connection_status(_):
    total_messages = (len(throughput_data) + len(top_rated_data) + 
                     len(genre_analytics_data) + len(popular_tags_data))
    
    if total_messages == 0:
        return html.Div([
            html.H4("🔴 Conectando a Kafka...", style={'color': 'red'}),
            html.P("Esperando datos del pipeline de streaming...")
        ])
    else:
        return html.Div([
            html.H4("🟢 Conectado y recibiendo datos", style={'color': 'green'}),
            html.P(f"📊 {total_messages} métricas recibidas | " +
                   f"🎬 {len(top_rated_data)} películas | " +
                   f"🏷️ {len(popular_tags_data)} tags | " +
                   f"🎭 {len(genre_analytics_data)} géneros")
        ])

# Callbacks actualizados
@app.callback(
    dash.Output('throughput-graph', 'figure'),
    dash.Input('tick', 'n_intervals')
)
def update_throughput(_):
    if not throughput_data:
        return {
            'data': [],
            'layout': go.Layout(
                title='Esperando datos de throughput...',
                xaxis={'title': 'Tiempo'},
                yaxis={'title': 'Eventos por Segundo'},
                margin={'l': 50, 'r': 20, 't': 50, 'b': 50}
            )
        }
    
    times = list(range(len(throughput_data)))
    events_ps = [d['events_per_second'] for d in throughput_data]
    
    return {
        'data': [
            go.Scatter(
                x=times, 
                y=events_ps, 
                mode='lines+markers',
                line={'color': '#A23B72', 'width': 3},
                marker={'size': 8},
                name='Eventos/segundo'
            )
        ],
        'layout': go.Layout(
            xaxis={'title': 'Tiempo (últimos puntos)'},
            yaxis={'title': 'Eventos por Segundo'},
            margin={'l': 50, 'r': 20, 't': 30, 'b': 50},
            plot_bgcolor='#f9f9f9'
        )
    }

@app.callback(
    dash.Output('top-rated-table', 'children'),
    dash.Input('tick', 'n_intervals')
)
def update_top_rated(_):
    if not top_rated_data:
        return html.Div([
            html.P("⏳ Esperando datos de películas..."),
            html.P("El producer está enviando datos, el Gold layer los procesará pronto.")
        ])
    
    # Filtrar películas válidas y ordenar por rating
    valid_movies = [m for m in top_rated_data if m.get('avg_rating') and m.get('title')]
    sorted_movies = sorted(valid_movies, key=lambda x: x.get('avg_rating', 0), reverse=True)
    
    if not sorted_movies:
        return html.P("⏳ Procesando datos de películas...")
    
    rows = []
    for i, movie in enumerate(sorted_movies[:10]):  # Mostrar top 10
        rating = movie.get('avg_rating', 0)
        votes = movie.get('total_ratings', 0)
        title = movie.get('title', 'N/A')
        
        # Truncar títulos largos
        if len(title) > 50:
            title = title[:47] + "..."
        
        row = html.Div([
            html.B(f"{i+1}. {title}"),
            html.Br(),
            html.Span(f"⭐ {rating:.2f} | 👥 {votes:,} ratings", 
                     style={'color': '#666', 'fontSize': '12px'}),
            html.Hr(style={'margin': '8px 0'})
        ], style={'marginBottom': '10px'})
        rows.append(row)
    
    return html.Div(rows)

@app.callback(
    dash.Output('genre-analytics-graph', 'figure'),
    dash.Input('tick', 'n_intervals')
)
def update_genre_analytics(_):
    if not genre_analytics_data:
        return {
            'data': [],
            'layout': go.Layout(
                title='Esperando datos por género...',
                xaxis={'title': 'Género'},
                yaxis={'title': 'Rating Promedio'}
            )
        }
    
    # Filtrar géneros con datos válidos
    valid_genres = {k: v for k, v in genre_analytics_data.items() 
                   if v.get('avg_rating') and v.get('movie_count', 0) > 0}
    
    if not valid_genres:
        return {
            'data': [],
            'layout': go.Layout(
                title='Procesando datos por género...',
                xaxis={'title': 'Género'},
                yaxis={'title': 'Rating Promedio'}
            )
        }
    
    genres = list(valid_genres.keys())
    avg_ratings = [valid_genres[g]['avg_rating'] for g in genres]
    
    return {
        'data': [
            go.Bar(
                x=genres, 
                y=avg_ratings,
                name='Rating Promedio',
                marker={'color': '#C73E1D'}
            )
        ],
        'layout': go.Layout(
            xaxis={'title': 'Género', 'tickangle': 45},
            yaxis={'title': 'Rating Promedio'},
            margin={'l': 50, 'r': 20, 't': 30, 'b': 100},
            plot_bgcolor='#f9f9f9'
        )
    }

@app.callback(
    dash.Output('popular-tags-list', 'children'),
    dash.Input('tick', 'n_intervals')
)
def update_popular_tags(_):
    # ✅ USO SEGURO de popular_tags_data - siempre es una lista
    if not popular_tags_data:
        return html.P("⏳ Esperando datos de tags...")
    
    try:
        # Agrupar y sumar counts por tag
        tag_counts = {}
        for tag_data in popular_tags_data:
            if isinstance(tag_data, dict):
                tag = tag_data.get('tag')
                count = tag_data.get('count', 0)
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + count
        
        if not tag_counts:
            return html.P("⏳ Procesando tags...")
        
        # Ordenar por count
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        tags_list = []
        for i, (tag, count) in enumerate(sorted_tags[:15]):  # Mostrar hasta 15 tags
            tags_list.append(html.Li(
                f"{tag} ({count} películas)",
                style={'marginBottom': '8px', 'fontSize': '14px', 'textAlign': 'left'}
            ))
        
        return html.Ul(tags_list, style={'paddingLeft': '20px'})
        
    except Exception as e:
        print(f"❌ Error en update_popular_tags: {e}")
        return html.P("⚠️ Error cargando tags...")

@app.callback(
    dash.Output('catalog-stats', 'children'),
    dash.Input('tick', 'n_intervals')
)
def update_catalog_stats(_):
    stats_data = {
        'total_movies': catalog_stats_data.get('total_movies', 0),
        'catalog_avg_rating': catalog_stats_data.get('catalog_avg_rating', 0),
        'total_ratings': catalog_stats_data.get('total_ratings', 0),
        'unique_genres': catalog_stats_data.get('unique_genres', 0)
    }
    
    # Mostrar estadísticas incluso si son cero
    stats = [
        html.Div([
            html.H4("🎬 Películas Totales", style={'color': '#6A4C93'}),
            html.H2(f"{stats_data['total_movies']:,}")
        ], style={'display': 'inline-block', 'margin': '0 20px'}),
        
        html.Div([
            html.H4("⭐ Rating Promedio", style={'color': '#6A4C93'}),
            html.H2(f"{stats_data['catalog_avg_rating']:.2f}" if stats_data['catalog_avg_rating'] else "N/A")
        ], style={'display': 'inline-block', 'margin': '0 20px'}),
        
        html.Div([
            html.H4("👥 Total de Ratings", style={'color': '#6A4C93'}),
            html.H2(f"{stats_data['total_ratings']:,}")
        ], style={'display': 'inline-block', 'margin': '0 20px'}),
        
        html.Div([
            html.H4("🎭 Géneros Únicos", style={'color': '#6A4C93'}),
            html.H2(f"{stats_data['unique_genres']}")
        ], style={'display': 'inline-block', 'margin': '0 20px'})
    ]
    
    return html.Div(stats)

if __name__ == '__main__':
    print("📊 Monitoreando los siguientes topics:")
    for topic in TOPICS:
        print(f"   - {topic}")
    
    print("\n🎯 Dashboard listo en http://localhost:8050")
    print("⏳ Esperando datos del pipeline...")
    
    app.run(host='0.0.0.0', port=8050, debug=False)