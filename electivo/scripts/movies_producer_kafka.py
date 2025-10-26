#!/usr/bin/env python3
import json, time, logging
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_producer():
    """Crear productor Kafka con reintentos"""
    for attempt in range(5):
        try:
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=30000,
                api_version_auto_timeout_ms=20000,
                retries=5
            )
            logger.info("✅ Productor Kafka creado exitosamente")
            return producer
        except NoBrokersAvailable:
            logger.warning(f"⚠️  Intento {attempt + 1}/5: Kafka no disponible, reintentando...")
            time.sleep(5)
    raise Exception("❌ No se pudo conectar a Kafka después de 5 intentos")

try:
    producer = create_producer()
    
    with open("/app/data/movies.json", "r", encoding="utf-8") as f:
        movies = json.load(f)

    for movie in movies:
        producer.send("movies", movie)
        # logger.info(f"📤 Sent: {movie['name']}")
        time.sleep(1.0)  # Reducido para ser más rápido

    producer.flush()
    logger.info("✅ Done sending all movies.")

except Exception as e:
    logger.error(f"❌ Error: {e}")