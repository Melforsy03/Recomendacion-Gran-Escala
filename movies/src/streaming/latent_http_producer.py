#!/usr/bin/env python3
"""
Latent HTTP Producer
=====================

Generador de ratings sintéticos (misma lógica que `latent_generator.py`) pero
en lugar de escribir en Kafka envía los eventos por HTTP a un endpoint configurable
que debería encargarse de publicarlos en el topic `ratings` dentro del sistema
multicontenedor.

Uso:
  python latent_http_producer.py [THROUGHPUT]

Variables de entorno:
  RATINGS_HTTP_URL      URL destino para POST (default: http://api:8000/ratings)
  THROUGHPUT            ratings por segundo (argumento o env)
  BATCH_SIZE            número de ratings por petición HTTP (default: 50)
  TIMEOUT               timeout HTTP en segundos (default: 5)

El script intenta importar `LatentFactorGenerator` desde
`movies.src.streaming.latent_generator` para mantener la misma lógica; si falla
usa una versión interna mínima compatible.
"""

import os
import sys
import time
import json
import random
from typing import List, Dict

import requests
import numpy as np

# Configuración por defecto y lectura de entorno
DEFAULT_HTTP_URL = os.getenv("RATINGS_HTTP_URL", "http://api:8000/ratings")
DEFAULT_THROUGHPUT = int(os.getenv("THROUGHPUT", "100"))
DEFAULT_BATCH = int(os.getenv("BATCH_SIZE", "50"))
DEFAULT_TIMEOUT = float(os.getenv("TIMEOUT", "5"))

# Intentar reutilizar el generador latente existente
try:
    # Intentar import relativo dentro del paquete
    from movies.src.streaming.latent_generator import (
        LatentFactorGenerator,
        USER_ID_MIN,
        USER_ID_MAX,
        MOVIE_ID_MIN,
        MOVIE_ID_MAX,
        RATING_MIN,
        RATING_MAX,
    )
    print("✅ Usando LatentFactorGenerator importado de latent_generator.py")
except Exception:
    # Fallback: versión ligera compatible
    print("⚠️  No se pudo importar LatentFactorGenerator, usando fallback interno")

    USER_ID_MIN = 1
    USER_ID_MAX = 138493
    MOVIE_ID_MIN = 1
    MOVIE_ID_MAX = 131262
    RATING_MIN = 0.5
    RATING_MAX = 5.0

    class LatentFactorGenerator:
        def __init__(self, rank=20, global_mean=3.5, user_bias_std=0.15, item_bias_std=0.10, latent_std=None, seed=None):
            self.rank = rank
            self.global_mean = global_mean
            self.user_bias_std = user_bias_std
            self.item_bias_std = item_bias_std
            self.latent_std = latent_std if latent_std is not None else 1.0 / (rank ** 0.5)
            self.user_cache = {}
            self.item_cache = {}
            if seed is not None:
                np.random.seed(seed)
                random.seed(seed)

        def get_user_factors(self, user_id):
            if user_id in self.user_cache:
                return self.user_cache[user_id]
            factors = np.random.normal(0, self.latent_std, self.rank)
            bias = np.random.normal(0, self.user_bias_std)
            self.user_cache[user_id] = (factors, bias)
            return factors, bias

        def get_item_factors(self, item_id):
            if item_id in self.item_cache:
                return self.item_cache[item_id]
            factors = np.random.normal(0, self.latent_std, self.rank)
            bias = np.random.normal(0, self.item_bias_std)
            self.item_cache[item_id] = (factors, bias)
            return factors, bias

        def predict_rating(self, user_id, item_id, noise_std=0.4):
            uf, ub = self.get_user_factors(user_id)
            vf, vb = self.get_item_factors(item_id)
            dot = float(np.dot(uf, vf))
            rating = dot + ub + vb + self.global_mean + np.random.normal(0, noise_std)
            rating = max(RATING_MIN, min(RATING_MAX, rating))
            rating = round(rating * 2) / 2.0
            return float(rating)


def generate_rating_record(generator: LatentFactorGenerator) -> Dict:
    """Genera un rating sintético con timestamp en ms"""
    user_id = random.randint(USER_ID_MIN, USER_ID_MAX)
    movie_id = random.randint(MOVIE_ID_MIN, MOVIE_ID_MAX)
    rating = generator.predict_rating(user_id, movie_id)
    timestamp_ms = int(time.time() * 1000)
    return {
        "userId": int(user_id),
        "movieId": int(movie_id),
        "rating": float(rating),
        "timestamp": int(timestamp_ms),
    }


def post_batch(session: requests.Session, url: str, batch: List[Dict], timeout: float) -> bool:
    """Envía un batch por POST; acepta lista JSON. Retorna True si OK."""
    try:
        resp = session.post(url, json=batch, timeout=timeout)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error enviando batch HTTP: {e}")
        return False


def run(throughput: int, url: str, batch_size: int, timeout: float):
    """Bucle principal: genera ratings y envía por HTTP manteniendo throughput."""
    print(f"▶️  Iniciando Latent HTTP Producer → {url} | throughput={throughput} r/s | batch={batch_size}")

    generator = LatentFactorGenerator(seed=42)
    session = requests.Session()

    # Calcular intervalo entre batches
    if throughput <= 0:
        raise ValueError("throughput debe ser mayor que 0")

    per_batch = batch_size
    interval = per_batch / float(throughput)  # segundos por batch

    total_sent = 0
    try:
        while True:
            start = time.time()
            batch = [generate_rating_record(generator) for _ in range(per_batch)]

            ok = post_batch(session, url, batch, timeout=timeout)
            if ok:
                total_sent += len(batch)
                print(f"✅ Enviados {len(batch)} ratings (total {total_sent})")
            else:
                print("⚠️  Falló envío batch -> reintentando en 2s")
                time.sleep(2)

            # Control de ritmo
            elapsed = time.time() - start
            sleep_for = interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            # si el envío tomó más que el interval, seguimos inmediatamente

    except KeyboardInterrupt:
        print("\n⏹️  Interrumpido por el usuario. Saliendo...")
    finally:
        session.close()


if __name__ == "__main__":
    # Argumento posicional opcional para throughput
    arg_throughput = None
    if len(sys.argv) > 1:
        try:
            arg_throughput = int(sys.argv[1])
        except ValueError:
            print(f"Argumento inválido: {sys.argv[1]} (esperado int)")
            sys.exit(1)

    throughput = arg_throughput or DEFAULT_THROUGHPUT
    url = os.getenv("RATINGS_HTTP_URL", DEFAULT_HTTP_URL)
    batch = int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH)))
    timeout = float(os.getenv("TIMEOUT", str(DEFAULT_TIMEOUT)))

    run(throughput=throughput, url=url, batch_size=batch, timeout=timeout)
