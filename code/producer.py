# producer.py
from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime
import os

class MovieInteractionProducer:
    def __init__(self):
        # Configuración más robusta de Kafka
        kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
        
        # Configuración con reintentos y timeout
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_broker],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            request_timeout_ms=30000,
            reconnect_backoff_ms=1000
        )
        
        self.movies = self.load_movies_from_json()
        print(f"✅ Cargadas {len(self.movies)} películas")
        print(f"📡 Conectado a Kafka en: {kafka_broker}")

    def load_movies_from_json(self):
        """Carga las películas desde el archivo movies.json"""
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
        except Exception as e:
            print(f"❌ ERROR cargando movies.json: {e}")
            return []
    
    def generate_interaction(self):
        """Genera una interacción aleatoria"""
        if not self.movies:
            print("❌ No hay películas cargadas")
            return None
            
        movie = random.choice(self.movies)
        user_id = random.randint(1, 1000)
        interaction_type = random.choice(["click", "view", "rating", "purchase"])
        
        base_rating = movie["puan"] / 2
        rating_variation = random.uniform(-1.0, 1.0)
        rating = round(max(1.0, min(5.0, base_rating + rating_variation)), 1)
        
        final_rating = rating if interaction_type == "rating" else None
        
        return {
            "user_id": user_id,
            "movie_id": movie["ID"],
            "movie_name": movie["name"],
            "movie_genre": movie["genre"],
            "movie_puan": movie["puan"],
            "movie_pop": movie["pop"],
            "interaction_type": interaction_type,
            "rating": final_rating,
            "timestamp": datetime.now().isoformat(),
            "session_id": f"sess_{random.randint(1000, 9999)}"
        }
    
    def start_producing(self, interval=2):
        """Inicia el envío de datos a Kafka"""
        if not self.movies:
            print("❌ No se pueden generar datos sin películas")
            return
            
        print("🚀 Iniciando Movie Interaction Producer...")
        print("📤 Enviando datos a Kafka topic: movie-interactions")
        print("🛑 Presiona Ctrl+C para detener\n")
        
        count = 0
        try:
            while True:
                interaction = self.generate_interaction()
                if interaction:
                    # Enviar con manejo de errores
                    try:
                        self.producer.send('movie-interactions', interaction)
                        count += 1
                        
                        rating_info = f" - Rating: {interaction['rating']}" if interaction['rating'] else ""
                        print(f"📤 #{count}: User {interaction['user_id']:4d} → {interaction['movie_name']:20} ({interaction['interaction_type']:7}){rating_info}")
                        
                    except Exception as e:
                        print(f"❌ Error enviando mensaje: {e}")
                    
                    time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Producer detenido. Total mensajes: {count}")
            self.producer.close()

if __name__ == "__main__":
    # Esperar un poco para que Kafka esté listo
    print("⏳ Esperando que Kafka esté listo...")
    time.sleep(10)
    
    producer = MovieInteractionProducer()
    producer.start_producing(interval=2)