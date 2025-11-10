"""
Metrics Consumer - Kafka Consumer para Topic 'metrics'
=======================================================

Consume métricas en tiempo real desde Kafka y mantiene estado en memoria
para que la API pueda servirlas a través de endpoints REST y SSE.

Características:
- Consumer asíncrono (aiokafka)
- Estado en memoria con estructura optimizada
- Thread-safe para acceso concurrente
- Auto-commit de offsets
- Manejo de errores y reconexión

Fase 9: Sistema de Recomendación de Películas a Gran Escala
Fecha: 3 de noviembre de 2025
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque
from threading import Lock

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

# ==========================================
# Configuración
# ==========================================

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC = "metrics"
KAFKA_GROUP_ID = "api-metrics-consumer"
MAX_HISTORY_SIZE = 100  # Máximo de mensajes históricos en memoria

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# Estado Global (Thread-Safe)
# ==========================================

class MetricsState:
    """Estado global de métricas en memoria"""
    
    def __init__(self):
        self._lock = Lock()
        self._latest_summary: Optional[Dict[str, Any]] = None
        self._latest_topn: Optional[Dict[str, Any]] = None
        self._latest_genres: Optional[Dict[str, Any]] = None
        self._history: deque = deque(maxlen=MAX_HISTORY_SIZE)
        self._subscribers: List[asyncio.Queue] = []
        self._last_update: Optional[datetime] = None
    
    def update_summary(self, data: Dict[str, Any]):
        """Actualiza resumen de métricas"""
        with self._lock:
            self._latest_summary = data
            self._last_update = datetime.now()
            self._history.append({
                "type": "summary",
                "timestamp": self._last_update.isoformat(),
                "data": data
            })
            # Notificar a suscriptores
            self._notify_subscribers({"type": "summary", "data": data})
    
    def update_topn(self, data: Dict[str, Any]):
        """Actualiza top-N películas"""
        with self._lock:
            self._latest_topn = data
            self._last_update = datetime.now()
            self._history.append({
                "type": "topn",
                "timestamp": self._last_update.isoformat(),
                "data": data
            })
            self._notify_subscribers({"type": "topn", "data": data})
    
    def update_genres(self, data: Dict[str, Any]):
        """Actualiza métricas por género"""
        with self._lock:
            self._latest_genres = data
            self._last_update = datetime.now()
            self._history.append({
                "type": "genres",
                "timestamp": self._last_update.isoformat(),
                "data": data
            })
            self._notify_subscribers({"type": "genres", "data": data})
    
    def get_summary(self) -> Optional[Dict[str, Any]]:
        """Obtiene último resumen"""
        with self._lock:
            return self._latest_summary.copy() if self._latest_summary else None
    
    def get_topn(self) -> Optional[Dict[str, Any]]:
        """Obtiene último top-N"""
        with self._lock:
            return self._latest_topn.copy() if self._latest_topn else None
    
    def get_genres(self) -> Optional[Dict[str, Any]]:
        """Obtiene últimas métricas por género"""
        with self._lock:
            return self._latest_genres.copy() if self._latest_genres else None
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene historial de métricas"""
        with self._lock:
            return list(self._history)[-limit:]
    
    def get_last_update(self) -> Optional[datetime]:
        """Obtiene timestamp de última actualización"""
        with self._lock:
            return self._last_update
    
    def add_subscriber(self, queue: asyncio.Queue):
        """Agrega suscriptor para SSE"""
        with self._lock:
            self._subscribers.append(queue)
    
    def remove_subscriber(self, queue: asyncio.Queue):
        """Remueve suscriptor"""
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
    
    def _notify_subscribers(self, message: Dict[str, Any]):
        """Notifica a todos los suscriptores (no thread-safe, llamar dentro de lock)"""
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Queue full for subscriber, skipping message")

# Instancia global
metrics_state = MetricsState()

# ==========================================
# Kafka Consumer
# ==========================================

class MetricsKafkaConsumer:
    """Consumer de Kafka para métricas de streaming"""
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
    
    async def start(self):
        """Inicia el consumer de Kafka"""
        logger.info(f"Iniciando consumer de Kafka (topic: {KAFKA_TOPIC})...")
        
        self.consumer = AIOKafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset='earliest',  # Consumir desde el principio para testing
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        await self.consumer.start()
        logger.info("✅ Consumer de Kafka iniciado correctamente")
        
        self.running = True
        
        # Iniciar consumo en background
        asyncio.create_task(self._consume_loop())
    
    async def stop(self):
        """Detiene el consumer"""
        logger.info("Deteniendo consumer de Kafka...")
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        logger.info("✅ Consumer detenido")
    
    async def _consume_loop(self):
        """Loop principal de consumo"""
        logger.info("Iniciando loop de consumo de métricas...")
        
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    await self._process_message(message.value)
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
        
        except KafkaError as e:
            logger.error(f"Error de Kafka: {e}")
        except Exception as e:
            logger.error(f"Error inesperado en consumer: {e}")
        finally:
            logger.info("Loop de consumo finalizado")
    
    async def _process_message(self, message: Dict[str, Any]):
        """Procesa un mensaje de métricas"""
        
        # Los mensajes del topic 'metrics' pueden ser de diferentes tipos
        # Vienen del streaming processor con la siguiente estructura:
        # {
        #   "window_start": "...",
        #   "window_end": "...",
        #   "window_type": "tumbling|sliding",
        #   "count": ...,
        #   "avg_rating": ...,
        #   "p50_rating": ...,
        #   "p95_rating": ...,
        #   "top_movies": "[...]",  # String JSON
        #   "metrics_by_genre": "{...}"  # String JSON
        # }
        
        logger.debug(f"Procesando mensaje de métricas: {message.get('window_start', 'N/A')}")
        
        # Actualizar summary
        summary = {
            "window_start": message.get("window_start"),
            "window_end": message.get("window_end"),
            "window_type": message.get("window_type"),
            "total_ratings": message.get("count", 0),
            "avg_rating": message.get("avg_rating", 0.0),
            "p50_rating": message.get("p50_rating", 0.0),
            "p95_rating": message.get("p95_rating", 0.0),
            "timestamp": datetime.now().isoformat()
        }
        metrics_state.update_summary(summary)
        
        # Actualizar top-N si está presente
        # top_movies viene como string JSON, necesitamos deserializarlo
        top_movies_raw = message.get("top_movies")
        logger.info(f"DEBUG top_movies_raw: type={type(top_movies_raw)}, value={str(top_movies_raw)[:80] if top_movies_raw else 'None'}")
        
        if top_movies_raw and top_movies_raw not in ["null", "None", "", "[]"]:
            try:
                # Deserializar top_movies si es string
                top_movies_data = top_movies_raw
                
                if isinstance(top_movies_data, str):
                    logger.info(f"Deserializando top_movies string...")
                    top_movies_data = json.loads(top_movies_data)
                    logger.info(f"Deserializado: type={type(top_movies_data)}, len={len(top_movies_data) if isinstance(top_movies_data, list) else 'N/A'}")
                
                # Asegurarse de que es una lista
                if isinstance(top_movies_data, list) and len(top_movies_data) > 0:
                    topn = {
                        "window_start": message.get("window_start"),
                        "window_end": message.get("window_end"),
                        "movies": top_movies_data[:20],  # Top 20
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"✅ Top-N actualizado: {len(topn['movies'])} películas")
                    metrics_state.update_topn(topn)
                else:
                    logger.warning(f"top_movies no es una lista válida: type={type(top_movies_data)}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"ERROR deserializando top_movies: {e}, raw={str(top_movies_raw)[:100]}")
        
        # Actualizar métricas por género si está presente
        # metrics_by_genre viene como string JSON
        genre_raw = message.get("metrics_by_genre")
        if genre_raw and genre_raw not in ["null", "None", ""]:
            try:
                # Deserializar metrics_by_genre si es string
                genre_data = genre_raw
                if isinstance(genre_data, str):
                    genre_data = json.loads(genre_data)
                
                # Si viene como lista (lista de géneros), convertir a dict simple
                if isinstance(genre_data, list) and len(genre_data) > 0:
                    genre_data = {genre: {"count": 1} for genre in genre_data}
                
                # Solo actualizar si tenemos datos válidos
                if isinstance(genre_data, dict) and len(genre_data) > 0:
                    genres = {
                        "window_start": message.get("window_start"),
                        "window_end": message.get("window_end"),
                        "genres": genre_data,
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"✅ Géneros actualizados: {len(genre_data)} géneros")
                    metrics_state.update_genres(genres)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"No se pudo deserializar metrics_by_genre: {e}")
        
        logger.info(f"✅ Métricas actualizadas: {summary['total_ratings']} ratings, "
                   f"avg={summary['avg_rating']:.2f}")

# Instancia global del consumer
kafka_consumer = MetricsKafkaConsumer()

# ==========================================
# Funciones de Acceso (para usar en API)
# ==========================================

def get_latest_summary() -> Optional[Dict[str, Any]]:
    """Obtiene resumen más reciente de métricas"""
    return metrics_state.get_summary()

def get_latest_topn() -> Optional[Dict[str, Any]]:
    """Obtiene top-N más reciente"""
    return metrics_state.get_topn()

def get_latest_genres() -> Optional[Dict[str, Any]]:
    """Obtiene métricas por género más recientes"""
    return metrics_state.get_genres()

def get_metrics_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtiene historial de métricas"""
    return metrics_state.get_history(limit)

def get_last_update() -> Optional[datetime]:
    """Obtiene timestamp de última actualización"""
    return metrics_state.get_last_update()

async def subscribe_to_metrics() -> asyncio.Queue:
    """Crea una cola de suscripción para SSE"""
    queue = asyncio.Queue(maxsize=100)
    metrics_state.add_subscriber(queue)
    return queue

def unsubscribe_from_metrics(queue: asyncio.Queue):
    """Remueve suscripción"""
    metrics_state.remove_subscriber(queue)

# ==========================================
# Lifecycle Management
# ==========================================

async def start_consumer():
    """Inicia el consumer (llamar al inicio de la aplicación)"""
    await kafka_consumer.start()

async def stop_consumer():
    """Detiene el consumer (llamar al cerrar la aplicación)"""
    await kafka_consumer.stop()
