"""
Ejemplo de Spark Streaming con Kafka
Procesa ratings de usuarios en tiempo real
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, count, expr
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

def main():
    # Crear SparkSession con paquetes de Kafka
    spark = SparkSession.builder \
        .appName("StreamingRecommendation") \
        .master("spark://spark-master:7077") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1") \
        .config("spark.executor.memory", "1g") \
        .config("spark.executor.cores", "1") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 50)
    print("Spark Streaming con Kafka - Sistema de Recomendación")
    print("=" * 50)
    
    # Definir esquema de los datos
    schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("item_id", StringType(), True),
        StructField("rating", DoubleType(), True),
        StructField("timestamp", TimestampType(), True)
    ])
    
    # Leer stream desde Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "ratings") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parsear los mensajes JSON
    ratings_df = kafka_df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*")
    
    # Análisis 1: Rating promedio por item en ventanas de tiempo
    windowed_ratings = ratings_df \
        .withWatermark("timestamp", "1 minute") \
        .groupBy(
            window("timestamp", "30 seconds", "10 seconds"),
            "item_id"
        ) \
        .agg(
            avg("rating").alias("avg_rating"),
            count("*").alias("num_ratings")
        )
    
    # Query 1: Mostrar ratings en tiempo real
    query1 = ratings_df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .queryName("raw_ratings") \
        .start()
    
    # Query 2: Mostrar estadísticas por ventanas de tiempo
    query2 = windowed_ratings \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .queryName("windowed_stats") \
        .start()
    
    # Query 3: Detectar items trending (muchos ratings en poco tiempo)
    trending_items = ratings_df \
        .withWatermark("timestamp", "1 minute") \
        .groupBy(
            window("timestamp", "1 minute", "30 seconds"),
            "item_id"
        ) \
        .agg(count("*").alias("rating_count")) \
        .filter(col("rating_count") > 3) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "item_id",
            "rating_count"
        )
    
    query3 = trending_items \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .queryName("trending_items") \
        .start()
    
    print("\n✓ Streaming iniciado. Esperando datos...")
    print("Envía datos al topic 'ratings' en Kafka para verlos procesados")
    print("\nEjemplo de mensaje JSON:")
    print('{"user_id": "user1", "item_id": "item1", "rating": 4.5, "timestamp": "2025-10-22T10:00:00.000Z"}')
    print("\nPresiona Ctrl+C para detener...")
    
    # Esperar por las queries
    query1.awaitTermination()

if __name__ == "__main__":
    main()
