# config.py
import os

class Config:
    # Kafka
    KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
    KAFKA_TOPIC = 'movie-interactions'
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = 6379
    
    # HDFS
    HDFS_NAMENODE = os.getenv('HDFS_NAMENODE', 'hdfs://namenode:9000')
    
    # Spark
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'spark://spark-master:7077')
    
    # Rutas HDFS
    HDFS_ANALYTICS_PATH = f"{HDFS_NAMENODE}/user/spark/movie_analytics"
    HDFS_CHECKPOINT_PATH = f"{HDFS_NAMENODE}/user/spark/checkpoints"
    
    # Configuración de ventanas de tiempo
    STREAMING_WINDOW = "5 minutes"
    WATERMARK_DELAY = "1 minute"
    BATCH_INTERVAL = "5 minutes"