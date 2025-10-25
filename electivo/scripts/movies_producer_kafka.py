#!/usr/bin/env python3
import json, time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['172.17.0.1:9092'],  # o 'host.docker.internal:9092' si te funciona
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    request_timeout_ms=20000,
    api_version_auto_timeout_ms=15000,
    retries=5
)

with open("/app/data/movies.json", "r", encoding="utf-8") as f:
    movies = json.load(f)

for movie in movies:
    producer.send("movies", movie)
    print(f"📤 Sent: {movie['name']}")
    time.sleep(0.5)

producer.flush()
print("✅ Done sending all movies.")
