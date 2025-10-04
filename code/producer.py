from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime
import os

class MovieInteractionProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # CARGAR PELÍCULAS DESDE ARCHIVO JSON
        self.movies = self.load_movies_from_json()
        print(f"✅ Cargadas {len(self.movies)} películas desde movies.json")
    
    def load_movies_from_json(self):
        """Carga las películas desde el archivo movies.json"""
        try:
            with open('movies.json', 'r') as f:
                movies_data = json.load(f)
            
            # Formatear los datos para nuestro uso
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
            print("❌ ERROR: No se encontró el archivo movies.json")
            print("   Asegúrate de que movies.json esté en el mismo directorio")
            return []
        except Exception as e:
            print(f"❌ ERROR cargando movies.json: {e}")
            return []
    
    def generate_interaction(self):
        """Genera una interacción aleatoria basada en las películas del JSON"""
        if not self.movies:
            print("❌ No hay películas cargadas. Verifica movies.json")
            return None
            
        movie = random.choice(self.movies)
        user_id = random.randint(1, 1000)
        interaction_type = random.choice(["click", "view", "rating", "purchase"])
        
        # Las películas con mayor puntuación tienen más probabilidad de rating alto
        base_rating = movie["puan"] / 2  # Convertir escala 0-10 a 0-5
        rating_variation = random.uniform(-1.0, 1.0)
        rating = round(max(1.0, min(5.0, base_rating + rating_variation)), 1)
        
        # Solo enviar rating para interacciones de tipo "rating"
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
            print("❌ No se pueden generar datos sin películas. Verifica movies.json")
            return
            
        print("🚀 Iniciando Movie Interaction Producer...")
        print(f"📊 Usando {len(self.movies)} películas desde movies.json")
        print("📤 Enviando datos a Kafka topic: movie-interactions")
        print("🛑 Presiona Ctrl+C para detener\n")
        
        count = 0
        try:
            while True:
                interaction = self.generate_interaction()
                if interaction:
                    self.producer.send('movie-interactions', interaction)
                    count += 1
                    
                    # Mostrar información detallada
                    rating_info = f" - Rating: {interaction['rating']}" if interaction['rating'] else ""
                    popularity_info = f" (Popularidad: {interaction['movie_pop']})"
                    print(f"📤 #{count}: User {interaction['user_id']:4d} → {interaction['movie_name']:20} ({interaction['interaction_type']:7}){rating_info}{popularity_info}")
                    
                    time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Producer detenido. Total de mensajes enviados: {count}")
            self.producer.close()

if __name__ == "__main__":
    producer = MovieInteractionProducer()
    producer.start_producing(interval=2)
