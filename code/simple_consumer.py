from kafka import KafkaConsumer
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
import time
import os 
class SimpleMetricsCollector:
    def __init__(self):
        # Obtener el broker de Kafka desde variable de entorno
        kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')  # <-- Cambiar aquí
        
        self.consumer = KafkaConsumer(
            'movie-interactions',
            bootstrap_servers=kafka_broker,  # <-- Usar la variable aquí
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000
        )
        
        # Estructuras para métricas
        self.interaction_counts = defaultdict(int)
        self.user_activity = deque(maxlen=200)
        self.movie_popularity = defaultdict(int)
        self.movie_details = {}
        self.ratings = defaultdict(list)
        self.genre_popularity = defaultdict(int)
        self.start_time = datetime.now()
        
        print("📊 Inicializando sistema de métricas...")
        print(f"📡 Conectado a Kafka en: {kafka_broker}")  # <-- Para debug
        
    def calculate_metrics(self):
        """Calcular métricas en tiempo real"""
        current_time = datetime.now()
        
        # Usuarios activos (últimos 5 minutos)
        active_threshold = current_time - timedelta(minutes=5)
        active_users = len(set(user for user, timestamp in self.user_activity 
                             if timestamp > active_threshold))
        
        # Métricas básicas
        total_interactions = sum(self.interaction_counts.values())
        most_popular_movie = max(self.movie_popularity.items(), key=lambda x: x[1], default=("N/A", 0))
        
        # Rating promedio por película
        avg_ratings = {}
        for movie, ratings_list in self.ratings.items():
            if ratings_list:
                avg_ratings[movie] = sum(ratings_list) / len(ratings_list)
        
        # Género más popular
        most_popular_genre = max(self.genre_popularity.items(), key=lambda x: x[1], default=("N/A", 0))
        
        # Efectividad de recomendaciones (ratio de purchases vs clicks)
        total_clicks = self.interaction_counts.get('click', 0)
        total_purchases = self.interaction_counts.get('purchase', 0)
        conversion_rate = (total_purchases / total_clicks * 100) if total_clicks > 0 else 0
        
        return {
            'active_users': active_users,
            'total_interactions': total_interactions,
            'most_popular_movie': most_popular_movie[0],
            'popular_movie_count': most_popular_movie[1],
            'most_popular_genre': most_popular_genre[0],
            'popular_genre_count': most_popular_genre[1],
            'interaction_breakdown': dict(self.interaction_counts),
            'avg_ratings': avg_ratings,
            'conversion_rate': conversion_rate,
            'uptime_minutes': (current_time - self.start_time).total_seconds() / 60,
            'unique_movies': len(self.movie_popularity),
            'unique_users': len(set(user for user, _ in self.user_activity))
        }
    
    def print_metrics(self, metrics):
        """Mostrar métricas en consola con formato mejorado"""
        print("\n" + "="*70)
        print(f"📊 MÉTRICAS EN TIEMPO REAL - {datetime.now().strftime('%H:%M:%S')}")
        print("="*70)
        
        # Métricas principales
        print(f"👥 Usuarios activos (5min): {metrics['active_users']:3d} | Únicos totales: {metrics['unique_users']:3d}")
        print(f"📈 Total interacciones: {metrics['total_interactions']:4d} | Películas únicas: {metrics['unique_movies']:2d}")
        print(f"🎬 Película más popular: {metrics['most_popular_movie']:20} ({metrics['popular_movie_count']:3d} interacciones)")
        print(f"🎭 Género más popular: {metrics['most_popular_genre']:15} ({metrics['popular_genre_count']:3d} interacciones)")
        print(f"💰 Tasa de conversión: {metrics['conversion_rate']:5.1f}% | Uptime: {metrics['uptime_minutes']:5.1f} min")
        
        # Breakdown de interacciones
        print(f"\n📋 Breakdown de interacciones:")
        for interaction_type in ["click", "view", "rating", "purchase"]:
            count = metrics['interaction_breakdown'].get(interaction_type, 0)
            print(f"   - {interaction_type:7}: {count:3d}")
        
        # Ratings promedio
        print(f"\n⭐ Ratings promedio (basado en {sum(len(self.ratings[m]) for m in self.ratings)} ratings):")
        for movie, avg_rating in sorted(metrics['avg_ratings'].items(), key=lambda x: x[1], reverse=True)[:5]:
            interactions = self.movie_popularity.get(movie, 0)
            print(f"   - {movie:20}: {avg_rating:.2f}/5.0 ({interactions:2d} interacciones)")
    
    def start_consuming(self):
        """Inicia el consumo y procesamiento de datos"""
        print("🚀 Iniciando Simple Metrics Collector...")
        print("📊 Monitoreando topic: movie-interactions")
        print("🛑 Presiona Ctrl+C para detener\n")
        
        try:
            message_count = 0
            last_metrics_time = time.time()
            
            for message in self.consumer:
                data = message.value
                message_count += 1
                
                # Actualizar métricas
                self.interaction_counts[data['interaction_type']] += 1
                self.user_activity.append((data['user_id'], datetime.now()))
                self.movie_popularity[data['movie_name']] += 1
                self.genre_popularity[data['movie_genre']] += 1
                
                # Guardar detalles de la película
                if data['movie_name'] not in self.movie_details:
                    self.movie_details[data['movie_name']] = {
                        'genre': data['movie_genre'],
                        'puan': data.get('movie_puan', 0),
                        'pop': data.get('movie_pop', 0)
                    }
                
                if data.get('rating'):
                    self.ratings[data['movie_name']].append(data['rating'])
                    # Mantener solo últimos 100 ratings por película
                    if len(self.ratings[data['movie_name']]) > 100:
                        self.ratings[data['movie_name']].pop(0)
                
                # Mostrar métricas cada 5 segundos
                current_time = time.time()
                if current_time - last_metrics_time >= 5:
                    metrics = self.calculate_metrics()
                    self.print_metrics(metrics)
                    last_metrics_time = current_time
                    
                    # Mostrar último mensaje procesado
                    rating_display = f" - Rating: {data['rating']}" if data.get('rating') else ""
                    print(f"\n📨 Último mensaje (#{message_count}): User {data['user_id']} → {data['movie_name']} ({data['interaction_type']}){rating_display}")
                    print("-" * 70)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Consumer detenido. Total mensajes procesados: {message_count}")
            
            # Mostrar resumen final
            if message_count > 0:
                final_metrics = self.calculate_metrics()
                print("\n" + "="*70)
                print("📈 RESUMEN FINAL DEL PROCESAMIENTO")
                print("="*70)
                self.print_metrics(final_metrics)
            
            self.consumer.close()

if __name__ == "__main__":
    collector = SimpleMetricsCollector()
    collector.start_consuming()
