"""
Ratings Producer Service
========================

Servicio ligero para producir mensajes al topic `ratings` usando aiokafka.

Funciones:
- start_producer(): inicia el productor y lo deja listo
- stop_producer(): detiene el productor
- produce_ratings(records): publica una lista de registros (dicts) en el topic

El service mantiene una instancia global `producer` reutilizable.
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "kafka:9092"
KAFKA_TOPIC = "ratings"

producer: Optional[AIOKafkaProducer] = None

# Parámetros de publicación y backpressure
import os

QUEUE_MAXSIZE = int(os.getenv("RATINGS_QUEUE_MAXSIZE", "10000"))
PUBLISH_BATCH_SIZE = int(os.getenv("RATINGS_PUBLISH_BATCH", "200"))
PUBLISH_INTERVAL = float(os.getenv("RATINGS_PUBLISH_INTERVAL", "0.5"))  # segundos

_queue: Optional[asyncio.Queue] = None
_worker_task: Optional[asyncio.Task] = None


async def start_producer(bootstrap_servers: str = KAFKA_BOOTSTRAP):
    global producer
    if producer is not None:
        logger.info("Ratings producer already started")
        return

    # Ajustes básicos de rendimiento/fiabilidad
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        linger_ms=20,
        compression_type="lz4",
        retries=5,
    )
    await producer.start()
    logger.info("✅ Ratings producer started")


async def stop_producer():
    global producer
    if producer is None:
        return
    try:
        await producer.stop()
        logger.info("✅ Ratings producer stopped")
    finally:
        producer = None


async def produce_ratings(records: List[Dict[str, Any]], topic: str = KAFKA_TOPIC) -> None:
    """Produce una lista de registros al topic. No hace reintentos extensos."""
    global producer
    if producer is None:
        raise RuntimeError("Producer no inicializado. Llama a start_producer().")

    # Añadir key para particionado estable (por userId si existe)
    async def _send_one(rec: Dict[str, Any]):
        key = None
        if isinstance(rec, dict) and "userId" in rec:
            try:
                key = str(int(rec["userId"]))
            except Exception:
                key = str(rec["userId"])  # fallback
        fut = producer.send(topic, value=rec, key=(key.encode("utf-8") if key else None))
        # Esperar confirmación de envío del broker
        await fut

    # Enviar por chunks para limitar la concurrencia y favorecer batching
    total = 0
    for i in range(0, len(records), PUBLISH_BATCH_SIZE):
        chunk = records[i:i + PUBLISH_BATCH_SIZE]
        await asyncio.gather(*[_send_one(r) for r in chunk])
        total += len(chunk)
    logger.debug(f"Publicado {total} registros en {topic}")


# ---- Publicador en background mediante cola ----

async def start_background_publisher():
    """Inicializa la cola y arranca el worker en background."""
    global _queue, _worker_task
    if _queue is None:
        _queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        logger.info(
            "Ratings queue creada (maxsize=%s, batch=%s, interval=%ss)",
            QUEUE_MAXSIZE,
            PUBLISH_BATCH_SIZE,
            PUBLISH_INTERVAL,
        )
    if _worker_task is None:
        _worker_task = asyncio.create_task(_worker_loop())
        logger.info("✅ Ratings background publisher started")


async def stop_background_publisher():
    """Detiene el worker y vacía la cola publicando lo pendiente."""
    global _queue, _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None

    # Drenar elementos restantes, si los hay
    if _queue is not None and not _queue.empty():
        pending: List[Dict[str, Any]] = []
        try:
            while True:
                pending.append(_queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        if pending:
            try:
                await produce_ratings(pending)
                logger.info("🔄 Publicados %s registros pendientes al detener worker", len(pending))
            except Exception as e:
                logger.error("❌ Error publicando pendientes en shutdown: %s", e)
    _queue = None
    logger.info("✅ Ratings background publisher stopped")


async def enqueue_ratings(records: List[Dict[str, Any]]) -> int:
    """Encola registros para publicación asíncrona. Retorna cuántos se encolaron."""
    if _queue is None:
        raise RuntimeError("Ratings queue no inicializada")
    enq = 0
    for rec in records:
        try:
            _queue.put_nowait(rec)
            enq += 1
        except asyncio.QueueFull:
            logger.warning("⚠️ Cola de ratings llena. Encolados=%s, descartados=%s", enq, len(records) - enq)
            break
    return enq


async def _worker_loop():
    """Consume de la cola y publica en Kafka en lotes."""
    assert _queue is not None
    batch: List[Dict[str, Any]] = []
    try:
        while True:
            try:
                item = await asyncio.wait_for(_queue.get(), timeout=PUBLISH_INTERVAL)
                batch.append(item)
                if len(batch) >= PUBLISH_BATCH_SIZE:
                    await _publish_batch(batch)
                    batch.clear()
            except asyncio.TimeoutError:
                if batch:
                    await _publish_batch(batch)
                    batch.clear()
    except asyncio.CancelledError:
        # Salida ordenada del worker
        if batch:
            try:
                await _publish_batch(batch)
                logger.info("🔄 Publicado batch final de %s registros (cancel)", len(batch))
            except Exception as e:
                logger.error("❌ Error publicando batch final tras cancelación: %s", e)
        raise
    except Exception as e:
        logger.exception("❌ Error en worker de ratings: %s", e)


async def _publish_batch(batch: List[Dict[str, Any]]):
    """Publica un lote usando produce_ratings con reintentos simples."""
    attempts = 0
    while True:
        try:
            await produce_ratings(batch)
            logger.info("📤 Publicado batch de %s registros", len(batch))
            return
        except Exception as e:
            attempts += 1
            wait = min(2 ** attempts, 10)
            logger.warning("Reintento %s publicando batch (%s). Esperando %ss", attempts, e, wait)
            await asyncio.sleep(wait)
