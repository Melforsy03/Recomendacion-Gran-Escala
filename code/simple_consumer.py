# simple_consumer.py - VERSIÓN CORREGIDA
from kafka import KafkaConsumer
import json
import redis
import os
from datetime import datetime
import pyarrow as pa
import pyarrow.hdfs as hdfs

class SimpleMetricsCollector:
    def __init__(self):
        kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
        
        # Conectar a Redis
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ Conectado a Redis")
        except Exception as e:
            print(f"❌ Error conectando a Redis: {e}")
            self.redis_client = None
        
        # Conectar a HDFS
        try:
            self.fs = hdfs.connect(host='namenode', port=9000)
            print("✅ Conectado a HDFS")
        except Exception as e:
            print(f"❌ Error conectando a HDFS: {e}")
            self.fs = None
        
        # Configurar Kafka Consumer
        self.consumer = KafkaConsumer(
            'movie-interactions',
            bootstrap_servers=[kafka_broker],
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            group_id='metrics-consumer'
        )
        
        self.hdfs_buffer = []
        self.start_time = datetime.now()
        
        print("📊 Inicializando sistema de métricas con Redis y HDFS...")

    def update_redis_metrics(self, data):
        """Actualizar métricas en Redis"""
        if not self.redis_client:
            return
            
        try:
            # Métricas por película
            movie_key = f"movie:{data['movie_id']}"
            self.redis_client.hincrby(movie_key, f"{data['interaction_type']}_count", 1)
            self.redis_client.hincrby(movie_key, "total_interactions", 1)
            
            # Métricas globales
            self.redis_client.incr(f"total_{data['interaction_type']}")
            self.redis_client.incr("total_interactions")
            
            # Usuarios activos (usar sorted set con timestamp)
            user_key = "active_users"
            self.redis_client.zadd(user_key, {str(data['user_id']): datetime.now().timestamp()})
            
            # Ratings
            if data.get('rating'):
                rating_key = f"ratings:{data['movie_id']}"
                self.redis_client.rpush(rating_key, data['rating'])
                # Mantener solo últimos 100 ratings
                self.redis_client.ltrim(rating_key, -100, -1)
                
        except Exception as e:
            print(f"❌ Error actualizando Redis: {e}")

    def save_to_hdfs(self):
        """Guardar datos acumulados en HDFS"""
        if not self.fs or not self.hdfs_buffer:
            return
            
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"/data/interactions_batch_{timestamp}.json"
            
            # Convertir a JSON y guardar
            json_data = json.dumps(self.hdfs_buffer)
            with self.fs.open(file_path, 'wb') as f:
                f.write(json_data.encode())
            
            print(f"✅ Datos guardados en HDFS: {file_path} ({len(self.hdfs_buffer)} registros)")
            self.hdfs_buffer = []  # Limpiar buffer
            
        except Exception as e:
            print(f"❌ Error guardando en HDFS: {e}")

    def start_consuming(self):
        """Inicia el consumo y procesamiento de datos"""
        print("🚀 Iniciando Consumer con Redis y HDFS...")
        
        message_count = 0
        try:
            for message in self.consumer:
                data = message.value
                message_count += 1
                
                # 1. Actualizar Redis
                self.update_redis_metrics(data)
                
                # 2. Acumular para HDFS
                self.hdfs_buffer.append(data)
                
                # 3. Guardar en HDFS cada 10 mensajes
                if len(self.hdfs_buffer) >= 10:
                    self.save_to_hdfs()
                
                # Mostrar progreso
                if message_count % 5 == 0:
                    rating_info = f" - Rating: {data['rating']}" if data.get('rating') else ""
                    print(f"📥 #{message_count}: User {data['user_id']} → {data['movie_name']} ({data['interaction_type']}){rating_info}")
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Consumer detenido. Total mensajes: {message_count}")
            # Guardar datos pendientes
            if self.hdfs_buffer:
                self.save_to_hdfs()
            self.consumer.close()

if __name__ == "__main__":
    print("⏳ Esperando que servicios estén listos...")
    import time
    time.sleep(15)
    
    collector = SimpleMetricsCollector()
    collector.start_consuming()