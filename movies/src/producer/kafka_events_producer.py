"""
Productor de eventos para el sistema de recomendaciones.

Genera dos tipos de eventos enviados a Kafka (topic: 'events'):
- recommendation: { user_id, items:[item_id...], ts }
- interaction:   { user_id, item_id, action:'view|click|accept', ts, recommended:true/false }

Usa el dataset movies/data/raw/movies.json para construir el catálogo de ítems.

Ejecución local (host):
  - Kafka expone el puerto EXTERNAL 9093 para clientes fuera de Docker.

Requisitos:
  pip install kafka-python
"""
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import List, Dict

from kafka import KafkaProducer

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
MOVIES_PATH = os.path.join(ROOT_DIR, "movies/data/raw/movies.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_catalog() -> List[Dict]:
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Normalizamos claves a lo que usaremos en eventos
    catalog = [
        {
            "item_id": str(m.get("ID")),
            "name": m.get("name"),
            "genres": [g for g in [m.get("genre_1"), m.get("genre_2")] if g],
            "score": float(m.get("puan", 0.0)),
            "pop": int(m.get("pop", 0)),
        }
        for m in data
    ]
    # Ordenamos por popularidad para recomendaciones base
    catalog.sort(key=lambda x: (x["pop"], x["score"]), reverse=True)
    return catalog


def create_producer(bootstrap_servers: List[str]) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        linger_ms=10,
        acks="1",
    )


def simulate_user_preferences(num_users: int, catalog: List[Dict]) -> Dict[str, Dict]:
    # Asignamos gustos por género al usuario
    all_genres = sorted({g for m in catalog for g in m["genres"]})
    users = {}
    for i in range(1, num_users + 1):
        uid = f"user{i}"
        liked = set(random.sample(all_genres, k=min(2, max(1, len(all_genres)//5 or 1)))) if all_genres else set()
        users[uid] = {"liked_genres": liked}
    return users


def build_recommendation(catalog: List[Dict], user_profile: Dict, k: int = 5) -> List[str]:
    liked = user_profile.get("liked_genres", set())
    # Sesgo por géneros preferidos + popularidad
    scored = []
    for m in catalog[:500]:  # limitar universo para eficiencia
        base = m["pop"] / 100.0 + m["score"] / 10.0
        boost = 0.2 if liked and any(g in liked for g in m["genres"]) else 0.0
        scored.append((base + boost + random.uniform(-0.05, 0.05), m["item_id"]))
    scored.sort(reverse=True)
    return [iid for _, iid in scored[:k]]


def simulate_interactions(user_id: str, rec_items: List[str], accept_bias: float = 0.35):
    # Simulamos que el usuario ve los ítems recomendados; con cierta prob acepta 1-2
    events = []
    for iid in rec_items:
        events.append({
            "type": "interaction",
            "ts": utc_now_iso(),
            "user_id": user_id,
            "item_id": iid,
            "action": "view",
            "recommended": True,
        })
    # Probabilidad de aceptación global + ruido
    accepts = 0
    for iid in rec_items:
        if random.random() < accept_bias * (1.0 - accepts * 0.3):
            events.append({
                "type": "interaction",
                "ts": utc_now_iso(),
                "user_id": user_id,
                "item_id": iid,
                "action": "accept",
                "recommended": True,
            })
            accepts += 1
            if accepts >= 2:
                break
    return events


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9093")
    topic = os.environ.get("EVENTS_TOPIC", "events")
    num_users = int(os.environ.get("NUM_USERS", "50"))
    recs_per_cycle = int(os.environ.get("RECS_PER_CYCLE", "1"))
    sleep_sec = float(os.environ.get("SLEEP_SECONDS", "1.0"))

    print("Cargando catálogo de películas…")
    catalog = load_catalog()
    users = simulate_user_preferences(num_users, catalog)

    print(f"Conectando a Kafka: {bootstrap}")
    producer = create_producer([bootstrap])
    print(f"✓ Enviando eventos al topic '{topic}' (Ctrl+C para salir)")

    sent = 0
    try:
        while True:
            # Elegir usuarios activos aleatoriamente
            active_users = random.sample(list(users.keys()), k=random.randint(5, min(10, num_users)))
            for uid in active_users:
                profile = users[uid]
                for _ in range(recs_per_cycle):
                    items = build_recommendation(catalog, profile, k=random.choice([3, 5, 7]))
                    rec_event = {
                        "type": "recommendation",
                        "ts": utc_now_iso(),
                        "user_id": uid,
                        "items": items,
                    }
                    producer.send(topic, value=rec_event)
                    sent += 1
                    # Simular interacciones derivadas
                    for ev in simulate_interactions(uid, items):
                        producer.send(topic, value=ev)
                        sent += 1
            producer.flush()
            time.sleep(sleep_sec)
    except KeyboardInterrupt:
        pass
    finally:
        producer.close()
        print(f"Total eventos enviados: {sent}")


if __name__ == "__main__":
    main()
