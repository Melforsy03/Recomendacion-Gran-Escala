#!/usr/bin/env python3
"""
Productor API -> Kafka para ratings
===================================

Consume datos de ratings desde una API REST y los publica en el topic de Kafka
`ratings`, respetando el esquema esperado por el procesador de streaming
(`userId`, `movieId`, `rating`, `timestamp` en milisegundos).
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError


# Configuración por entorno
API_URL = os.getenv("RATINGS_API_URL")  # si no se define, se usa dataset local
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ratings")
API_POLL_INTERVAL = float(os.getenv("API_POLL_INTERVAL", "5"))  # segundos
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))  # segundos
MAX_MESSAGES_PER_BATCH = int(os.getenv("API_MAX_MESSAGES_PER_BATCH", "500"))

# Fuente local (fallback sin API externa)
LOCAL_DATASET_PATH = os.getenv("RATINGS_LOCAL_PATH", "Dataset/rating.csv")
LOCAL_CHUNK_SIZE = int(os.getenv("RATINGS_LOCAL_CHUNK", "1000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def normalize_records(payload: Any) -> List[Dict[str, Any]]:
    """
    Normaliza la respuesta de la API a una lista de ratings válidos.

    Se aceptan dos formatos:
    - Lista de diccionarios con las claves userId, movieId, rating, timestamp (ms).
    - Un diccionario con las mismas claves (se envuelve en lista).
    """
    if isinstance(payload, dict):
        # Permitir envolturas comunes como {"data": [...]} o {"results": [...]}
        container = None
        for key in ("data", "results", "items"):
            if key in payload:
                container = payload[key]
                break
        records = container if container is not None else payload
    else:
        records = payload

    if isinstance(records, dict):
        records = [records]

    if not isinstance(records, list):
        logger.warning("La API no devolvió una lista o diccionario de ratings.")
        return []

    normalized: List[Dict[str, Any]] = []
    for raw in records:
        try:
            user_id = int(raw["userId"])
            movie_id = int(raw["movieId"])
            rating = float(raw["rating"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Registro inválido recibido desde API, se omite: %s", raw)
            continue

        timestamp_ms = raw.get("timestamp")
        if isinstance(timestamp_ms, (int, float)):
            timestamp_ms = int(timestamp_ms)
        else:
            timestamp_ms = int(time.time() * 1000)

        normalized.append(
            {
                "userId": user_id,
                "movieId": movie_id,
                "rating": rating,
                "timestamp": timestamp_ms,
            }
        )

    return normalized


def fetch_ratings(session: requests.Session) -> List[Dict[str, Any]]:
    """Consulta la API y devuelve registros normalizados."""
    resp = session.get(API_URL, timeout=API_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    return normalize_records(payload)


def local_ratings_iterator(path: str, chunk_size: int) -> Iterable[List[Dict[str, Any]]]:
    """
    Iterador sobre el dataset local de ratings (MovieLens).
    Se reitera desde el principio cuando se acaba para producir indefinidamente.
    """
    while True:
        try:
            chunks = pd.read_csv(
                path,
                usecols=["userId", "movieId", "rating", "timestamp"],
                parse_dates=["timestamp"],
                chunksize=chunk_size,
            )
            for chunk in chunks:
                # Convertir a epoch ms si viene como datetime
                if pd.api.types.is_datetime64_any_dtype(chunk["timestamp"]):
                    chunk["timestamp"] = (chunk["timestamp"].astype("int64") // 10**6).astype(
                        "int64"
                    )
                else:
                    chunk["timestamp"] = chunk["timestamp"].astype("int64")
                yield chunk.to_dict(orient="records")
        except FileNotFoundError:
            logger.error("Dataset local no encontrado en %s", path)
            sys.exit(1)
        except Exception as exc:
            logger.error("Error leyendo dataset local: %s", exc)
            time.sleep(API_POLL_INTERVAL)


def create_producer() -> KafkaProducer:
    """Crea un productor Kafka JSON."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=500,
        max_in_flight_requests_per_connection=5,
    )


def produce_ratings() -> None:
    """Bucle principal: consulta API o dataset local y publica en Kafka."""
    session = requests.Session()
    producer = create_producer()

    source_desc = (
        f"API={API_URL}"
        if API_URL
        else f"DATASET={LOCAL_DATASET_PATH} (chunks {LOCAL_CHUNK_SIZE})"
    )
    logger.info(
        "Iniciando productor -> Kafka | %s | topic=%s | bootstrap=%s",
        source_desc,
        KAFKA_TOPIC,
        KAFKA_BOOTSTRAP_SERVERS,
    )

    local_iter: Optional[Iterable[List[Dict[str, Any]]]] = None
    if not API_URL:
        local_iter = local_ratings_iterator(LOCAL_DATASET_PATH, LOCAL_CHUNK_SIZE)

    try:
        while True:
            try:
                if API_URL:
                    ratings = fetch_ratings(session)
                else:
                    # Tomar siguiente chunk del dataset local
                    ratings = next(local_iter)  # type: ignore[arg-type]
            except StopIteration:
                # Reiniciar el iterador en caso de que se agote (loop infinito)
                local_iter = local_ratings_iterator(LOCAL_DATASET_PATH, LOCAL_CHUNK_SIZE)
                continue
            except Exception as exc:  # pragma: no cover - uso de red/IO
                logger.error("Error obteniendo datos: %s", exc)
                time.sleep(API_POLL_INTERVAL)
                continue

            if not ratings:
                logger.info("Fuente sin datos nuevos; esperando %ss", API_POLL_INTERVAL)
                time.sleep(API_POLL_INTERVAL)
                continue

            sent = 0
            for rating in ratings[:MAX_MESSAGES_PER_BATCH]:
                future = producer.send(KAFKA_TOPIC, rating)
                sent += 1
                try:
                    future.get(timeout=API_TIMEOUT)
                except KafkaError as exc:  # pragma: no cover - depende de runtime Kafka
                    logger.error("Error enviando a Kafka: %s", exc)
                    break

            producer.flush()
            logger.info(
                "Enviados %s mensajes a Kafka (%s). Esperando %ss.",
                sent,
                KAFKA_TOPIC,
                API_POLL_INTERVAL,
            )
            time.sleep(API_POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Interrumpido por el usuario, cerrando productor.")
    finally:
        try:
            producer.flush()
            producer.close()
        finally:
            session.close()
        logger.info("Productor detenido.")


if __name__ == "__main__":
    produce_ratings()
