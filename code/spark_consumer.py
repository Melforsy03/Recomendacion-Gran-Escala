# spark_consumer.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import os
import json
from datetime import datetime

class SparkStreamingProcessor:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("MovieRecommendationStreaming") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # Definir schema para los datos de Kafka
        self.schema = StructType([
            StructField("user_id", IntegerType()),
            StructField("movie_id", IntegerType()),
            StructField("movie_name", StringType()),
            StructField("movie_genre", StringType()),
            StructField("movie_puan", FloatType()),
            StructField("movie_pop", IntegerType()),
            StructField("interaction_type", StringType()),
            StructField("rating", FloatType()),
            StructField("timestamp", StringType()),
            StructField("session_id", StringType())
        ])
        
        print("✅ Spark Session inicializada")
        print(f"📡 Conectando a Kafka: {os.getenv('KAFKA_BROKER', 'kafka:9092')}")
    
    def start_streaming(self):
        """Inicia el procesamiento de streaming con Spark"""
        try:
            # Leer stream desde Kafka
            df = self.spark \
                .readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", os.getenv('KAFKA_BROKER', 'kafka:9092')) \
                .option("subscribe", "movie-interactions") \
                .option("startingOffsets", "latest") \
                .load()
            
            # Parsear JSON
            parsed_df = df.select(
                from_json(col("value").cast("string"), self.schema).alias("data")
            ).select("data.*")
            
            # Procesamiento en tiempo real
            self.process_realtime_metrics(parsed_df)
            self.process_batch_analytics(parsed_df)
            
        except Exception as e:
            print(f"❌ Error en Spark Streaming: {e}")
    
    def process_realtime_metrics(self, df):
        """Procesa métricas en tiempo real"""
        
        # Métricas por ventana de tiempo
        windowed_metrics = df \
            .withWatermark("timestamp", "1 minute") \
            .groupBy(
                window(col("timestamp"), "5 minutes"),
                "interaction_type"
            ) \
            .agg(
                count("*").alias("interaction_count"),
                approx_count_distinct("user_id").alias("unique_users")
            )
        
        # Escribir métricas a console (en producción sería HDFS/Redis)
        console_query = windowed_metrics \
            .writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", "false") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        return console_query
    
    def process_batch_analytics(self, df):
        """Procesa analytics por lotes para HDFS"""
        
        # Popularidad de películas
        movie_popularity = df \
            .groupBy("movie_id", "movie_name", "movie_genre") \
            .agg(
                count("*").alias("total_interactions"),
                avg("rating").alias("avg_rating"),
                approx_count_distinct("user_id").alias("unique_users"),
                sum(when(col("interaction_type") == "purchase", 1).otherwise(0)).alias("purchases")
            )
        
        # Escribir a HDFS
        hdfs_query = movie_popularity \
            .writeStream \
            .outputMode("update") \
            .format("parquet") \
            .option("path", "hdfs://namenode:9000/user/spark/movie_analytics") \
            .option("checkpointLocation", "hdfs://namenode:9000/user/spark/checkpoints") \
            .trigger(processingTime="5 minutes") \
            .start()
        
        return hdfs_query
    
    def run_mapreduce_job(self):
        """Ejecuta un trabajo MapReduce/Spark batch"""
        try:
            # Leer datos históricos de HDFS
            historical_df = self.spark.read \
                .parquet("hdfs://namenode:9000/user/spark/movie_analytics")
            
            # Análisis avanzado: recomendaciones por género
            genre_analysis = historical_df \
                .groupBy("movie_genre") \
                .agg(
                    avg("avg_rating").alias("genre_avg_rating"),
                    sum("total_interactions").alias("genre_total_interactions"),
                    avg("purchases").alias("avg_purchases_per_movie")
                ) \
                .orderBy(desc("genre_total_interactions"))
            
            # Guardar resultados
            genre_analysis.write \
                .mode("overwrite") \
                .parquet("hdfs://namenode:9000/user/spark/genre_analysis")
            
            print("✅ Análisis por género guardado en HDFS")
            
            # Mostrar resultados
            genre_analysis.show()
            
        except Exception as e:
            print(f"❌ Error en MapReduce job: {e}")
    
    def stop(self):
        """Detener Spark session"""
        self.spark.stop()

if __name__ == "__main__":
    processor = SparkStreamingProcessor()
    
    print("🚀 Iniciando Spark Streaming Processor...")
    print("📊 Procesando datos de Kafka -> Spark -> HDFS")
    
    try:
        # Iniciar streaming
        processor.start_streaming()
        
        # Ejecutar batch job cada 10 minutos
        while True:
            import time
            time.sleep(600)  # 10 minutos
            print("🔄 Ejecutando MapReduce batch job...")
            processor.run_mapreduce_job()
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo Spark Streaming Processor...")
        processor.stop()