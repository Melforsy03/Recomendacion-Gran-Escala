#!/usr/bin/env python3
import json, time, logging
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_producer():
    """Crear productor Kafka optimizado"""
    for attempt in range(5):
        try:
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                batch_size=16384,  # Aumentar batch size
                linger_ms=10,      # Reducir linger
                compression_type='gzip',  # Comprimir para mayor velocidad
                request_timeout_ms=30000,
                retries=3,
                api_version=(2, 5, 0)
            )
            
            # Test de conexión rápido
            future = producer.send('test-connection', value={'test': 'connection'})
            future.get(timeout=5)
            logger.info("✅ Productor Kafka creado y conectado exitosamente")
            return producer
        except Exception as e:
            logger.warning(f"⚠️ Intento {attempt+1}/5: Error conectando a Kafka - {str(e)}")
            time.sleep(3)
    raise Exception("❌ No se pudo conectar a Kafka")

if __name__ == "__main__":
    logger.info("📂 Cargando datasets de MovieLens...")
    
    try:
        # Cargar datasets
        movies = pd.read_csv("/app/films/movie.csv")
        ratings = pd.read_csv("/app/films/rating.csv") 
        tags = pd.read_csv("/app/films/tag.csv")
        links = pd.read_csv("/app/films/link.csv")
        genome_tags = pd.read_csv("/app/films/genome_tags.csv")
        genome_scores = pd.read_csv("/app/films/genome_scores.csv")
        
        logger.info(f"✅ Datasets cargados: {len(movies)} películas, {len(ratings)} ratings")
    except Exception as e:
        logger.error(f"❌ Error cargando datasets: {e}")
        exit(1)

    # Procesamiento de datos (mantener igual)
    rating_stats = ratings.groupby("movieId").agg(
        avg_rating=("rating", "mean"),
        rating_count=("rating", "count")
    ).reset_index()

    top_tags = tags.groupby("movieId")["tag"].apply(
        lambda x: list(x.value_counts().head(5).index)
    ).reset_index(name="top_tags")

    genome = genome_scores.merge(genome_tags, on="tagId")
    genome_relevance = genome.groupby("movieId").apply(
        lambda g: [{"tag": r["tag"], "relevance": float(r["relevance"])} for _, r in g.head(10).iterrows()]
    ).reset_index(name="genome_relevance")

    df = (movies
          .merge(links, on="movieId", how="left")
          .merge(rating_stats, on="movieId", how="left")
          .merge(top_tags, on="movieId", how="left")
          .merge(genome_relevance, on="movieId", how="left"))

    logger.info(f"📊 DataFrame preparado con {len(df)} filas")

    # Crear producer optimizado
    producer = create_producer()

    # Enviar datos MÁS RÁPIDO
    sent_count = 0
    batch_size = 200  # Batch más grande
    
    start_time = time.time()
    
    for _, row in df.iterrows():
        try:
            event = {
                "movieId": int(row["movieId"]),
                "title": row["title"],
                "genres": row["genres"].split("|") if isinstance(row["genres"], str) else [],
                "imdbId": int(row["imdbId"]) if pd.notna(row["imdbId"]) else None,
                "tmdbId": int(row.get("tmdbId", row.get("tmbdId", None)))
                          if pd.notna(row.get("tmdbId", row.get("tmbdId", float('nan')))) else None,
                "avg_rating": float(row["avg_rating"]) if pd.notna(row["avg_rating"]) else None,
                "rating_count": int(row["rating_count"]) if pd.notna(row["rating_count"]) else 0,
                "top_tags": row["top_tags"] if isinstance(row["top_tags"], list) else [],
                "genome_relevance": row["genome_relevance"] if isinstance(row["genome_relevance"], list) else []
            }
            
            # Envío asíncrono para mayor velocidad
            future = producer.send("movies", value=event)
            sent_count += 1
            
            if sent_count % batch_size == 0:
                elapsed = time.time() - start_time
                rate = sent_count / elapsed
                logger.info(f"📤 Enviadas {sent_count}/{len(df)} películas - {rate:.1f} películas/segundo")
                
            time.sleep(0.2)  # MUCHO más rápido - 100 películas/segundo
            
        except Exception as e:
            logger.error(f"❌ Error enviando película {row['movieId']}: {e}")
            break

    producer.flush()
    total_time = time.time() - start_time
    logger.info(f"✅ Envío completo: {sent_count} películas en {total_time:.1f} segundos "
                f"({sent_count/total_time:.1f} películas/segundo)")