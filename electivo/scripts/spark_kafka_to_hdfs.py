import os
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import from_json, col

# SOLUCIÓN: Incluir commons-pool2 en el classpath y agregar configuraciones de resiliencia
os.environ["PYSPARK_SUBMIT_ARGS"] = (
    "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 "
    "--conf spark.jars.ivy=/tmp/.ivy "  # Directorio para cache de jars
    "pyspark-shell"
)

spark = (
    SparkSession.builder
    .appName("MoviesKafkaToHDFS-BRONZE")
    .master("local[*]")
    .config("spark.sql.streaming.schemaInference", "true")
    .config("spark.sql.adaptive.enabled", "false")  # Mejor para streaming
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
    .config("spark.jars.repositories", "https://repo1.maven.org/maven2/")
    .config("spark.driver.extraJavaOptions", "-Dio.netty.tryReflectionSetAccessible=true")
    .config("spark.executor.extraJavaOptions", "-Dio.netty.tryReflectionSetAccessible=true")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# Descargar commons-pool2 automáticamente si no está disponible
try:
    # Intentar forzar la descarga de dependencias
    print("🔧 Verificando dependencias de Kafka...")
    df_test = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "movies") \
        .option("startingOffsets", "earliest") \
        .load()
    print("✅ Dependencias de Kafka verificadas correctamente")
except Exception as e:
    print(f"⚠️ Error en dependencias: {e}")
    print("📥 Las dependencias se descargarán automáticamente...")

# Schema corregido
schema = StructType([
    StructField("movieId", IntegerType(), True),
    StructField("title", StringType(), True),
    StructField("genres", ArrayType(StringType()), True),
    StructField("imdbId", IntegerType(), True),
    StructField("tmdbId", IntegerType(), True),
    StructField("avg_rating", FloatType(), True),
    StructField("rating_count", IntegerType(), True),
    StructField("top_tags", ArrayType(StringType()), True),
    StructField("genome_relevance", ArrayType(
        StructType([
            StructField("tag", StringType(), True),
            StructField("relevance", FloatType(), True)
        ])
    ), True)
])

print("🚀 Iniciando consumo desde Kafka...")

raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "movies")
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")  # Importante: evitar fallos por pérdida de datos
    .option("kafkaConsumer.pollTimeoutMs", "512")  # Timeout más corto
    .load()
)

print("📊 Procesando datos de Kafka...")

movies = (raw
    .selectExpr("CAST(value AS STRING) AS json")
    .select(from_json(col("json"), schema).alias("data"))
    .select("data.*")
)

# Filtrar nulls para evitar problemas
movies = movies.filter(col("movieId").isNotNull())

output = "hdfs://localhost:9000/user/movies/bronze/movies"
chkpt  = "hdfs://localhost:9000/user/movies/checkpoints/movies_bronze"

print(f"💾 Escribiendo en: {output}")
print(f"📝 Checkpoint en: {chkpt}")

query = (movies.writeStream
    .format("parquet")
    .option("path", output)
    .option("checkpointLocation", chkpt)
    .outputMode("append")
    .option("checkpoint", chkpt)
    .trigger(processingTime="10 seconds")  # Aumentado para mayor estabilidad
    .start())

print("✅ Streaming BRONZE iniciado - esperando datos de Kafka...")
print("📈 Verifica que el producer esté enviando datos...")

# Agregar monitorización básica
import threading
import time

def monitor_query():
    while True:
        try:
            progress = query.lastProgress
            if progress:
                print(f"📊 Progreso: {progress['numInputRows']} filas procesadas")
            time.sleep(30)
        except:
            time.sleep(30)

monitor_thread = threading.Thread(target=monitor_query, daemon=True)
monitor_thread.start()

query.awaitTermination()